#!/usr/bin/env node

/**
 * Build script to ensure PyInstaller backend is built before Electron packaging
 * This script is called by electron-builder before packaging
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

function runCommand(command, args, cwd) {
    return new Promise((resolve, reject) => {
        console.log(`Running: ${command} ${args.join(' ')} in ${cwd}`);
        const process = spawn(command, args, { 
            cwd, 
            stdio: 'inherit',
            shell: true 
        });
        
        process.on('close', (code) => {
            if (code === 0) {
                resolve();
            } else {
                reject(new Error(`Command failed with exit code ${code}`));
            }
        });
        
        process.on('error', (err) => {
            reject(err);
        });
    });
}

async function buildBackend() {
    const projectRoot = path.resolve(__dirname, '..');
    const buildDir = path.join(projectRoot, 'build');
    const backendDistPath = path.join(buildDir, 'electron', 'dist', 'fourdst-backend');
    
    console.log('Building PyInstaller backend...');
    console.log(`Project root: ${projectRoot}`);
    console.log(`Build directory: ${buildDir}`);
    console.log(`Target platform: ${process.platform}`);
    
    try {
        // Check if meson build directory exists
        if (!fs.existsSync(buildDir)) {
            console.log('Meson build directory not found. Setting up build...');
            await runCommand('meson', ['setup', 'build', '--buildtype=release', '-Dbuild-py-backend=true'], projectRoot);
        } else {
            // Ensure py-backend option is enabled
            console.log('Reconfiguring meson build with py-backend enabled...');
            await runCommand('meson', ['configure', 'build', '-Dbuild-py-backend=true'], projectRoot);
        }
        
        // Build the backend using meson
        console.log('Building backend with meson...');
        await runCommand('meson', ['compile', '-C', 'build'], projectRoot);
        
        // Verify the backend executable was created
        const executableName = process.platform === 'win32' ? 'fourdst-backend.exe' : 'fourdst-backend';
        const backendExecutable = path.join(backendDistPath, executableName);
        
        if (fs.existsSync(backendExecutable)) {
            console.log(`✅ Backend executable built successfully: ${backendExecutable}`);
            
            // Make executable on Unix systems
            if (process.platform !== 'win32') {
                const { execSync } = require('child_process');
                execSync(`chmod +x "${backendExecutable}"`);
                console.log('✅ Backend executable permissions set');
            }
            
            // Validate backend dependencies
            console.log('🔍 Validating backend dependencies...');
            const { DependencyValidator } = require('./validate-dependencies.js');
            const validator = new DependencyValidator();
            
            // Test backend execution to ensure all dependencies are embedded
            const testResult = await validator.validatePythonBackend();
            if (!testResult) {
                throw new Error('Backend dependency validation failed. Check that all Python dependencies are properly bundled.');
            }
            console.log('✅ Backend dependency validation passed');
            
        } else {
            throw new Error(`Backend executable not found at: ${backendExecutable}`);
        }
        
    } catch (error) {
        console.error('❌ Failed to build backend:', error.message);
        process.exit(1);
    }
}

// Run the build if this script is called directly
if (require.main === module) {
    buildBackend().catch(error => {
        console.error('Build failed:', error);
        process.exit(1);
    });
}

module.exports = { buildBackend };
