#!/usr/bin/env node

/**
 * Dependency Validation Script for 4DSTAR Electron App
 * 
 * This script validates that all runtime dependencies are properly embedded
 * and available in the packaged application.
 */

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

class DependencyValidator {
    constructor() {
        this.errors = [];
        this.warnings = [];
        this.projectRoot = path.resolve(__dirname, '..');
        this.buildDir = path.join(this.projectRoot, 'build');
        this.electronDir = __dirname;
    }

    log(message, type = 'info') {
        const timestamp = new Date().toISOString();
        const prefix = {
            'info': '📋',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌'
        }[type] || 'ℹ️';
        
        console.log(`${prefix} [${timestamp}] ${message}`);
        
        if (type === 'error') {
            this.errors.push(message);
        } else if (type === 'warning') {
            this.warnings.push(message);
        }
    }

    async validatePythonBackend() {
        this.log('Validating Python backend dependencies...', 'info');
        
        // Check if backend executable exists
        const executableName = process.platform === 'win32' ? 'fourdst-backend.exe' : 'fourdst-backend';
        const backendPath = path.join(this.buildDir, 'electron', 'dist', 'fourdst-backend', executableName);
        
        if (!fs.existsSync(backendPath)) {
            this.log(`Backend executable not found: ${backendPath}`, 'error');
            return false;
        }
        
        this.log(`Backend executable found: ${backendPath}`, 'success');
        
        // Check backend executable permissions
        try {
            const stats = fs.statSync(backendPath);
            const isExecutable = !!(stats.mode & parseInt('111', 8));
            if (!isExecutable) {
                this.log('Backend executable lacks execute permissions', 'error');
                return false;
            }
            this.log('Backend executable has proper permissions', 'success');
        } catch (e) {
            this.log(`Failed to check backend permissions: ${e.message}`, 'error');
            return false;
        }
        
        // Test backend execution
        return new Promise((resolve) => {
            this.log('Testing backend execution...', 'info');
            
            const testArgs = ['inspect_bundle', JSON.stringify({ bundle_path: '/nonexistent/test.fbundle' })];
            const process = spawn(backendPath, testArgs, { timeout: 10000 });
            
            let stdout = '';
            let stderr = '';
            
            process.stdout.on('data', (data) => {
                stdout += data.toString();
            });
            
            process.stderr.on('data', (data) => {
                stderr += data.toString();
            });
            
            process.on('close', (code) => {
                // We expect this to fail since the bundle doesn't exist,
                // but it should fail gracefully with JSON output
                if (stdout.length > 0) {
                    try {
                        const result = JSON.parse(stdout.trim());
                        if (result.success === false && result.error) {
                            this.log('Backend produces valid JSON error responses', 'success');
                            resolve(true);
                        } else {
                            this.log('Backend JSON response format unexpected', 'warning');
                            resolve(true);
                        }
                    } catch (e) {
                        this.log(`Backend output is not valid JSON: ${e.message}`, 'error');
                        this.log(`Raw stdout: "${stdout.substring(0, 200)}"`, 'error');
                        resolve(false);
                    }
                } else {
                    this.log('Backend produced no stdout output', 'error');
                    this.log(`Stderr: ${stderr}`, 'error');
                    resolve(false);
                }
            });
            
            process.on('error', (err) => {
                this.log(`Failed to execute backend: ${err.message}`, 'error');
                resolve(false);
            });
        });
    }

    validateNodeDependencies() {
        this.log('Validating Node.js dependencies...', 'info');
        
        const packageJsonPath = path.join(this.electronDir, 'package.json');
        if (!fs.existsSync(packageJsonPath)) {
            this.log('package.json not found', 'error');
            return false;
        }
        
        const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
        const dependencies = { ...packageJson.dependencies, ...packageJson.devDependencies };
        
        let allFound = true;
        
        for (const [dep, version] of Object.entries(dependencies)) {
            const depPath = path.join(this.electronDir, 'node_modules', dep);
            if (fs.existsSync(depPath)) {
                this.log(`✓ ${dep}@${version}`, 'success');
            } else {
                this.log(`✗ ${dep}@${version} not found in node_modules`, 'error');
                allFound = false;
            }
        }
        
        // Check for native modules that might need special handling
        const nativeModules = ['@electron/remote', 'python-shell'];
        for (const mod of nativeModules) {
            if (dependencies[mod]) {
                const modPath = path.join(this.electronDir, 'node_modules', mod);
                if (fs.existsSync(modPath)) {
                    // Check for native binaries
                    const hasNativeBinaries = this.findNativeBinaries(modPath);
                    if (hasNativeBinaries.length > 0) {
                        this.log(`Native binaries found in ${mod}: ${hasNativeBinaries.join(', ')}`, 'info');
                    }
                }
            }
        }
        
        return allFound;
    }

    findNativeBinaries(dir) {
        const nativeExtensions = ['.node', '.so', '.dylib', '.dll'];
        const binaries = [];
        
        try {
            const files = fs.readdirSync(dir, { recursive: true });
            for (const file of files) {
                const ext = path.extname(file);
                if (nativeExtensions.includes(ext)) {
                    binaries.push(file);
                }
            }
        } catch (e) {
            // Directory might not exist or be accessible
        }
        
        return binaries;
    }

    validateElectronBuild() {
        this.log('Validating Electron build configuration...', 'info');
        
        const packageJsonPath = path.join(this.electronDir, 'package.json');
        const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
        
        const buildConfig = packageJson.build;
        if (!buildConfig) {
            this.log('No build configuration found in package.json', 'error');
            return false;
        }
        
        // Check extraResources configuration
        if (!buildConfig.extraResources || !Array.isArray(buildConfig.extraResources)) {
            this.log('No extraResources configuration found', 'error');
            return false;
        }
        
        // Validate backend resource mapping
        const backendResource = buildConfig.extraResources.find(res => res.to === 'backend/');
        if (!backendResource) {
            this.log('Backend resource mapping not found in extraResources', 'error');
            return false;
        }
        
        // Check if source directory exists
        const backendSourcePath = path.resolve(this.electronDir, backendResource.from);
        if (!fs.existsSync(backendSourcePath)) {
            this.log(`Backend source directory not found: ${backendSourcePath}`, 'error');
            return false;
        }
        
        this.log('Electron build configuration validated', 'success');
        return true;
    }

    validatePyInstallerSpec() {
        this.log('Validating PyInstaller spec file...', 'info');
        
        const specPath = path.join(this.electronDir, 'fourdst-backend.spec');
        if (!fs.existsSync(specPath)) {
            this.log('PyInstaller spec file not found', 'error');
            return false;
        }
        
        const specContent = fs.readFileSync(specPath, 'utf8');
        
        // Check for essential hidden imports
        const requiredImports = [
            'docker',
            'cryptography',
            'yaml',
            'fourdst.core'
        ];
        
        for (const imp of requiredImports) {
            if (!specContent.includes(`'${imp}'`)) {
                this.log(`Missing hidden import in spec: ${imp}`, 'warning');
            } else {
                this.log(`✓ Hidden import found: ${imp}`, 'success');
            }
        }
        
        return true;
    }

    validateFileStructure() {
        this.log('Validating project file structure...', 'info');
        
        const requiredFiles = [
            'package.json',
            'main-refactored.js',
            'bridge.py',
            'fourdst-backend.spec',
            'entitlements.mac.plist'
        ];
        
        let allFound = true;
        
        for (const file of requiredFiles) {
            const filePath = path.join(this.electronDir, file);
            if (fs.existsSync(filePath)) {
                this.log(`✓ ${file}`, 'success');
            } else {
                this.log(`✗ ${file} not found`, 'error');
                allFound = false;
            }
        }
        
        // Check for main modules
        const mainModulesDir = path.join(this.electronDir, 'main');
        if (fs.existsSync(mainModulesDir)) {
            this.log('✓ Main process modules directory found', 'success');
        } else {
            this.log('✗ Main process modules directory not found', 'error');
            allFound = false;
        }
        
        // Check for renderer modules
        const rendererModulesDir = path.join(this.electronDir, 'renderer');
        if (fs.existsSync(rendererModulesDir)) {
            this.log('✓ Renderer process modules directory found', 'success');
        } else {
            this.log('✗ Renderer process modules directory not found', 'error');
            allFound = false;
        }
        
        return allFound;
    }

    async runValidation() {
        this.log('Starting comprehensive dependency validation...', 'info');
        this.log(`Project root: ${this.projectRoot}`, 'info');
        this.log(`Electron directory: ${this.electronDir}`, 'info');
        this.log(`Build directory: ${this.buildDir}`, 'info');
        
        const results = {
            fileStructure: this.validateFileStructure(),
            nodeDependencies: this.validateNodeDependencies(),
            electronBuild: this.validateElectronBuild(),
            pyinstallerSpec: this.validatePyInstallerSpec(),
            pythonBackend: await this.validatePythonBackend()
        };
        
        this.log('\n=== VALIDATION SUMMARY ===', 'info');
        
        let allPassed = true;
        for (const [test, passed] of Object.entries(results)) {
            const status = passed ? '✅ PASS' : '❌ FAIL';
            this.log(`${test}: ${status}`, passed ? 'success' : 'error');
            if (!passed) allPassed = false;
        }
        
        if (this.warnings.length > 0) {
            this.log(`\n⚠️  ${this.warnings.length} warnings found:`, 'warning');
            this.warnings.forEach(warning => this.log(`  - ${warning}`, 'warning'));
        }
        
        if (this.errors.length > 0) {
            this.log(`\n❌ ${this.errors.length} errors found:`, 'error');
            this.errors.forEach(error => this.log(`  - ${error}`, 'error'));
        }
        
        if (allPassed && this.errors.length === 0) {
            this.log('\n🎉 All validations passed! The app should be fully self-contained.', 'success');
            return true;
        } else {
            this.log('\n💥 Validation failed. Please fix the issues above before packaging.', 'error');
            return false;
        }
    }
}

// Run validation if called directly
if (require.main === module) {
    const validator = new DependencyValidator();
    validator.runValidation().then(success => {
        process.exit(success ? 0 : 1);
    }).catch(error => {
        console.error('Validation failed with error:', error);
        process.exit(1);
    });
}

module.exports = { DependencyValidator };
