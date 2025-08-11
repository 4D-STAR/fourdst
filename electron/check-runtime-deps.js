#!/usr/bin/env node

/**
 * Runtime Dependency Checker for Packaged 4DSTAR App
 * 
 * This script can be run inside a packaged app to verify all dependencies
 * are available at runtime. Useful for testing the .dmg on different user accounts.
 */

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

class RuntimeDependencyChecker {
    constructor() {
        this.isPackaged = process.env.NODE_ENV === 'production' || process.resourcesPath;
        this.appPath = this.isPackaged ? process.resourcesPath : __dirname;
        this.results = {
            environment: {},
            backend: {},
            nodeModules: {},
            permissions: {},
            errors: [],
            warnings: []
        };
    }

    log(message, type = 'info') {
        const prefix = {
            'info': '📋',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌'
        }[type] || 'ℹ️';
        
        console.log(`${prefix} ${message}`);
    }

    checkEnvironment() {
        this.log('Checking runtime environment...', 'info');
        
        this.results.environment = {
            platform: process.platform,
            arch: process.arch,
            nodeVersion: process.version,
            electronVersion: process.versions.electron,
            isPackaged: this.isPackaged,
            appPath: this.appPath,
            resourcesPath: process.resourcesPath || 'N/A',
            execPath: process.execPath,
            cwd: process.cwd(),
            user: process.env.USER || process.env.USERNAME || 'unknown',
            home: process.env.HOME || process.env.USERPROFILE || 'unknown'
        };

        this.log(`Platform: ${this.results.environment.platform}`, 'info');
        this.log(`Architecture: ${this.results.environment.arch}`, 'info');
        this.log(`Packaged: ${this.results.environment.isPackaged}`, 'info');
        this.log(`User: ${this.results.environment.user}`, 'info');
        this.log(`App Path: ${this.results.environment.appPath}`, 'info');
    }

    checkBackendExecutable() {
        this.log('Checking Python backend executable...', 'info');
        
        const executableName = process.platform === 'win32' ? 'fourdst-backend.exe' : 'fourdst-backend';
        let backendPath;
        
        if (this.isPackaged) {
            backendPath = path.join(this.appPath, 'backend', executableName);
        } else {
            backendPath = path.join(__dirname, '..', 'build', 'electron', 'dist', 'fourdst-backend', executableName);
        }
        
        this.results.backend.expectedPath = backendPath;
        this.results.backend.exists = fs.existsSync(backendPath);
        
        if (!this.results.backend.exists) {
            this.results.errors.push(`Backend executable not found: ${backendPath}`);
            this.log(`Backend executable not found: ${backendPath}`, 'error');
            return false;
        }
        
        this.log(`Backend executable found: ${backendPath}`, 'success');
        
        // Check permissions
        try {
            const stats = fs.statSync(backendPath);
            this.results.backend.size = stats.size;
            this.results.backend.mode = stats.mode.toString(8);
            this.results.backend.isExecutable = !!(stats.mode & parseInt('111', 8));
            
            if (!this.results.backend.isExecutable) {
                this.results.errors.push('Backend executable lacks execute permissions');
                this.log('Backend executable lacks execute permissions', 'error');
                return false;
            }
            
            this.log(`Backend size: ${this.results.backend.size} bytes`, 'info');
            this.log(`Backend permissions: ${this.results.backend.mode}`, 'info');
            
        } catch (e) {
            this.results.errors.push(`Failed to check backend stats: ${e.message}`);
            this.log(`Failed to check backend stats: ${e.message}`, 'error');
            return false;
        }
        
        return true;
    }

    async testBackendExecution() {
        if (!this.results.backend.exists) {
            return false;
        }
        
        this.log('Testing backend execution...', 'info');
        
        return new Promise((resolve) => {
            const testArgs = ['inspect_bundle', JSON.stringify({ bundle_path: '/nonexistent/test.fbundle' })];
            const backendProcess = spawn(this.results.backend.expectedPath, testArgs, { 
                timeout: 15000,
                env: { ...process.env, PYTHONPATH: '' } // Clear PYTHONPATH to test self-containment
            });
            
            let stdout = '';
            let stderr = '';
            
            backendProcess.stdout.on('data', (data) => {
                stdout += data.toString();
            });
            
            backendProcess.stderr.on('data', (data) => {
                stderr += data.toString();
            });
            
            backendProcess.on('close', (code) => {
                this.results.backend.testExecution = {
                    exitCode: code,
                    stdoutLength: stdout.length,
                    stderrLength: stderr.length,
                    stdout: stdout.substring(0, 500), // First 500 chars
                    stderr: stderr.substring(0, 500)
                };
                
                if (stdout.length > 0) {
                    try {
                        const result = JSON.parse(stdout.trim());
                        this.results.backend.producesValidJSON = true;
                        this.results.backend.jsonResponse = result;
                        
                        if (result.success === false && result.error) {
                            this.log('Backend produces valid JSON error responses', 'success');
                            resolve(true);
                        } else {
                            this.log('Backend JSON response format unexpected', 'warning');
                            this.results.warnings.push('Backend JSON response format unexpected');
                            resolve(true);
                        }
                    } catch (e) {
                        this.results.backend.producesValidJSON = false;
                        this.results.errors.push(`Backend output is not valid JSON: ${e.message}`);
                        this.log(`Backend output is not valid JSON: ${e.message}`, 'error');
                        this.log(`Raw stdout (first 200 chars): "${stdout.substring(0, 200)}"`, 'error');
                        resolve(false);
                    }
                } else {
                    this.results.backend.producesValidJSON = false;
                    this.results.errors.push('Backend produced no stdout output');
                    this.log('Backend produced no stdout output', 'error');
                    if (stderr.length > 0) {
                        this.log(`Stderr: ${stderr.substring(0, 200)}`, 'error');
                    }
                    resolve(false);
                }
            });
            
            backendProcess.on('error', (err) => {
                this.results.backend.executionError = err.message;
                this.results.errors.push(`Failed to execute backend: ${err.message}`);
                this.log(`Failed to execute backend: ${err.message}`, 'error');
                resolve(false);
            });
        });
    }

    checkNodeModules() {
        this.log('Checking Node.js modules...', 'info');
        
        const requiredModules = [
            'fs-extra',
            'js-yaml', 
            'adm-zip',
            '@electron/remote',
            'python-shell',
            'plotly.js-dist',
            'electron-squirrel-startup'
        ];
        
        this.results.nodeModules.checked = {};
        
        for (const moduleName of requiredModules) {
            try {
                const modulePath = require.resolve(moduleName);
                this.results.nodeModules.checked[moduleName] = {
                    available: true,
                    path: modulePath
                };
                this.log(`✓ ${moduleName}`, 'success');
            } catch (e) {
                this.results.nodeModules.checked[moduleName] = {
                    available: false,
                    error: e.message
                };
                this.results.errors.push(`Module ${moduleName} not available: ${e.message}`);
                this.log(`✗ ${moduleName}: ${e.message}`, 'error');
            }
        }
        
        return Object.values(this.results.nodeModules.checked).every(mod => mod.available);
    }

    checkFilePermissions() {
        this.log('Checking file permissions...', 'info');
        
        const testPaths = [
            this.appPath,
            path.join(this.appPath, 'backend'),
            this.results.backend.expectedPath
        ];
        
        this.results.permissions.paths = {};
        
        for (const testPath of testPaths) {
            try {
                if (fs.existsSync(testPath)) {
                    const stats = fs.statSync(testPath);
                    this.results.permissions.paths[testPath] = {
                        readable: true,
                        mode: stats.mode.toString(8),
                        isDirectory: stats.isDirectory(),
                        isFile: stats.isFile()
                    };
                    this.log(`✓ ${testPath} (${stats.mode.toString(8)})`, 'success');
                } else {
                    this.results.permissions.paths[testPath] = {
                        readable: false,
                        exists: false
                    };
                    this.log(`✗ ${testPath} does not exist`, 'warning');
                }
            } catch (e) {
                this.results.permissions.paths[testPath] = {
                    readable: false,
                    error: e.message
                };
                this.results.errors.push(`Cannot access ${testPath}: ${e.message}`);
                this.log(`✗ ${testPath}: ${e.message}`, 'error');
            }
        }
    }

    async runFullCheck() {
        this.log('Starting runtime dependency check...', 'info');
        
        this.checkEnvironment();
        const backendExists = this.checkBackendExecutable();
        const backendWorks = backendExists ? await this.testBackendExecution() : false;
        const nodeModulesOk = this.checkNodeModules();
        this.checkFilePermissions();
        
        // Generate summary
        this.log('\n=== RUNTIME DEPENDENCY CHECK SUMMARY ===', 'info');
        
        const checks = {
            'Environment': true, // Always passes
            'Backend Executable': backendExists,
            'Backend Execution': backendWorks,
            'Node Modules': nodeModulesOk,
            'File Permissions': this.results.errors.filter(e => e.includes('Cannot access')).length === 0
        };
        
        let allPassed = true;
        for (const [check, passed] of Object.entries(checks)) {
            const status = passed ? '✅ PASS' : '❌ FAIL';
            this.log(`${check}: ${status}`, passed ? 'success' : 'error');
            if (!passed) allPassed = false;
        }
        
        if (this.results.warnings.length > 0) {
            this.log(`\n⚠️  ${this.results.warnings.length} warnings:`, 'warning');
            this.results.warnings.forEach(warning => this.log(`  - ${warning}`, 'warning'));
        }
        
        if (this.results.errors.length > 0) {
            this.log(`\n❌ ${this.results.errors.length} errors:`, 'error');
            this.results.errors.forEach(error => this.log(`  - ${error}`, 'error'));
        }
        
        if (allPassed && this.results.errors.length === 0) {
            this.log('\n🎉 All runtime dependencies are available! App should work correctly.', 'success');
        } else {
            this.log('\n💥 Runtime dependency issues found. App may not work correctly.', 'error');
        }
        
        // Save results to file for debugging
        const resultsPath = path.join(process.cwd(), 'runtime-check-results.json');
        try {
            fs.writeFileSync(resultsPath, JSON.stringify(this.results, null, 2));
            this.log(`\n📄 Detailed results saved to: ${resultsPath}`, 'info');
        } catch (e) {
            this.log(`Failed to save results: ${e.message}`, 'warning');
        }
        
        return allPassed && this.results.errors.length === 0;
    }
}

// Run check if called directly
if (require.main === module) {
    const checker = new RuntimeDependencyChecker();
    checker.runFullCheck().then(success => {
        process.exit(success ? 0 : 1);
    }).catch(error => {
        console.error('Runtime check failed with error:', error);
        process.exit(1);
    });
}

module.exports = { RuntimeDependencyChecker };
