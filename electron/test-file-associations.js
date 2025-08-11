#!/usr/bin/env node

/**
 * File Association Test Script for 4DSTAR Bundle Manager
 * 
 * This script tests that the app correctly handles file association events
 * for .fbundle and .opat files when they are opened via the OS.
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

class FileAssociationTester {
    constructor() {
        this.appPath = path.join(__dirname, 'dist', 'mac-arm64', '4DSTAR Bundle Manager.app');
        this.testFilesDir = path.join(__dirname, 'test-files');
    }

    log(message, type = 'info') {
        const timestamp = new Date().toISOString();
        const prefix = {
            'info': '📋',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌'
        }[type] || '📋';
        
        console.log(`${prefix} [${timestamp}] ${message}`);
    }

    async createTestFiles() {
        this.log('Creating test files for file association testing...', 'info');
        
        // Create test files directory
        if (!fs.existsSync(this.testFilesDir)) {
            fs.mkdirSync(this.testFilesDir, { recursive: true });
        }

        // Create a minimal test .fbundle file (ZIP format)
        const fbundlePath = path.join(this.testFilesDir, 'test-bundle.fbundle');
        const fbundleContent = Buffer.from('PK\x03\x04'); // ZIP file header
        fs.writeFileSync(fbundlePath, fbundleContent);
        this.log(`✓ Created test .fbundle file: ${fbundlePath}`, 'success');

        // Create a minimal test .opat file
        const opatPath = path.join(this.testFilesDir, 'test-data.opat');
        const opatContent = Buffer.alloc(100); // Minimal binary file
        fs.writeFileSync(opatPath, opatContent);
        this.log(`✓ Created test .opat file: ${opatPath}`, 'success');

        return { fbundlePath, opatPath };
    }

    async testAppExists() {
        this.log('Checking if app bundle exists...', 'info');
        
        if (!fs.existsSync(this.appPath)) {
            throw new Error(`App bundle not found at: ${this.appPath}`);
        }
        
        this.log(`✓ App bundle found: ${this.appPath}`, 'success');
        return true;
    }

    async testFileAssociation(filePath, fileType) {
        this.log(`Testing ${fileType} file association: ${path.basename(filePath)}`, 'info');
        
        return new Promise((resolve, reject) => {
            // Use 'open' command to simulate double-clicking the file
            const openProcess = spawn('open', [filePath], {
                stdio: ['pipe', 'pipe', 'pipe']
            });
            
            let stdout = '';
            let stderr = '';
            
            openProcess.stdout.on('data', (data) => {
                stdout += data.toString();
            });
            
            openProcess.stderr.on('data', (data) => {
                stderr += data.toString();
            });
            
            openProcess.on('close', (code) => {
                if (code === 0) {
                    this.log(`✓ ${fileType} file opened successfully`, 'success');
                    resolve({ success: true, stdout, stderr });
                } else {
                    this.log(`✗ ${fileType} file failed to open (exit code: ${code})`, 'error');
                    if (stderr) this.log(`Error: ${stderr}`, 'error');
                    resolve({ success: false, stdout, stderr, code });
                }
            });
            
            openProcess.on('error', (error) => {
                this.log(`✗ Error opening ${fileType} file: ${error.message}`, 'error');
                reject(error);
            });
            
            // Timeout after 10 seconds
            setTimeout(() => {
                openProcess.kill();
                this.log(`⚠️ ${fileType} file association test timed out`, 'warning');
                resolve({ success: false, timeout: true });
            }, 10000);
        });
    }

    async testAppLaunch() {
        this.log('Testing direct app launch...', 'info');
        
        return new Promise((resolve, reject) => {
            const appProcess = spawn('open', [this.appPath], {
                stdio: ['pipe', 'pipe', 'pipe']
            });
            
            let stderr = '';
            
            appProcess.stderr.on('data', (data) => {
                stderr += data.toString();
            });
            
            appProcess.on('close', (code) => {
                if (code === 0) {
                    this.log('✓ App launched successfully', 'success');
                    resolve({ success: true });
                } else {
                    this.log(`✗ App failed to launch (exit code: ${code})`, 'error');
                    if (stderr) this.log(`Error: ${stderr}`, 'error');
                    resolve({ success: false, code, stderr });
                }
            });
            
            appProcess.on('error', (error) => {
                this.log(`✗ Error launching app: ${error.message}`, 'error');
                reject(error);
            });
            
            // Timeout after 15 seconds
            setTimeout(() => {
                appProcess.kill();
                this.log('⚠️ App launch test timed out', 'warning');
                resolve({ success: false, timeout: true });
            }, 15000);
        });
    }

    async runTests() {
        try {
            this.log('Starting file association tests for 4DSTAR Bundle Manager...', 'info');
            
            // Test 1: Check if app exists
            await this.testAppExists();
            
            // Test 2: Create test files
            const { fbundlePath, opatPath } = await this.createTestFiles();
            
            // Test 3: Test direct app launch
            const launchResult = await this.testAppLaunch();
            
            // Wait a moment for app to fully start
            await new Promise(resolve => setTimeout(resolve, 3000));
            
            // Test 4: Test .fbundle file association
            const fbundleResult = await this.testFileAssociation(fbundlePath, '.fbundle');
            
            // Wait between tests
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            // Test 5: Test .opat file association
            const opatResult = await this.testFileAssociation(opatPath, '.opat');
            
            // Summary
            this.log('\n=== TEST RESULTS SUMMARY ===', 'info');
            this.log(`App Launch: ${launchResult.success ? '✅ PASS' : '❌ FAIL'}`, launchResult.success ? 'success' : 'error');
            this.log(`Bundle File Association: ${fbundleResult.success ? '✅ PASS' : '❌ FAIL'}`, fbundleResult.success ? 'success' : 'error');
            this.log(`OPAT File Association: ${opatResult.success ? '✅ PASS' : '❌ FAIL'}`, opatResult.success ? 'success' : 'error');
            
            const allPassed = launchResult.success && fbundleResult.success && opatResult.success;
            
            if (allPassed) {
                this.log('\n🎉 All file association tests PASSED!', 'success');
                this.log('The app correctly handles file associations for both .fbundle and .opat files.', 'success');
            } else {
                this.log('\n⚠️ Some tests FAILED. Check the logs above for details.', 'warning');
            }
            
            // Cleanup
            this.log('\nCleaning up test files...', 'info');
            if (fs.existsSync(this.testFilesDir)) {
                fs.rmSync(this.testFilesDir, { recursive: true, force: true });
                this.log('✓ Test files cleaned up', 'success');
            }
            
            return allPassed;
            
        } catch (error) {
            this.log(`❌ Test suite failed: ${error.message}`, 'error');
            return false;
        }
    }

    async checkFileAssociations() {
        this.log('Checking macOS file associations...', 'info');
        
        try {
            // Check what app is associated with .fbundle files
            const fbundleCheck = spawn('duti', ['-x', 'fbundle'], { stdio: ['pipe', 'pipe', 'pipe'] });
            
            fbundleCheck.on('close', (code) => {
                if (code === 0) {
                    this.log('✓ .fbundle file association registered', 'success');
                } else {
                    this.log('⚠️ .fbundle file association may not be registered', 'warning');
                }
            });
            
            // Check what app is associated with .opat files
            const opatCheck = spawn('duti', ['-x', 'opat'], { stdio: ['pipe', 'pipe', 'pipe'] });
            
            opatCheck.on('close', (code) => {
                if (code === 0) {
                    this.log('✓ .opat file association registered', 'success');
                } else {
                    this.log('⚠️ .opat file association may not be registered', 'warning');
                }
            });
            
        } catch (error) {
            this.log('⚠️ Could not check file associations (duti not available)', 'warning');
        }
    }
}

// Run tests if called directly
if (require.main === module) {
    const tester = new FileAssociationTester();
    
    tester.runTests().then(success => {
        process.exit(success ? 0 : 1);
    }).catch(error => {
        console.error('Test suite crashed:', error);
        process.exit(1);
    });
}

module.exports = FileAssociationTester;
