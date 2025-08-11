#!/usr/bin/env node

/**
 * Debug script to test the packaged app backend in isolation
 * This helps identify issues with the backend executable in different user environments
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

function testBackendExecutable(backendPath, testBundlePath) {
    console.log(`\n=== Testing Backend Executable ===`);
    console.log(`Backend path: ${backendPath}`);
    console.log(`Test bundle: ${testBundlePath}`);
    console.log(`Backend exists: ${fs.existsSync(backendPath)}`);
    
    if (!fs.existsSync(backendPath)) {
        console.error(`❌ Backend executable not found at: ${backendPath}`);
        return Promise.resolve(false);
    }
    
    // Test with inspect_bundle command (same as open-bundle)
    const args = ['inspect_bundle', JSON.stringify({ bundle_path: testBundlePath })];
    console.log(`Command: ${backendPath} ${args.join(' ')}`);
    
    return new Promise((resolve) => {
        const process = spawn(backendPath, args);
        let stdoutBuffer = '';
        let stderrBuffer = '';
        
        process.stdout.on('data', (data) => {
            stdoutBuffer += data.toString();
        });
        
        process.stderr.on('data', (data) => {
            stderrBuffer += data.toString();
        });
        
        process.on('close', (code) => {
            console.log(`\n--- Backend Test Results ---`);
            console.log(`Exit code: ${code}`);
            console.log(`Stdout length: ${stdoutBuffer.length}`);
            console.log(`Stderr length: ${stderrBuffer.length}`);
            
            if (stdoutBuffer.length > 0) {
                console.log(`\nStdout first 500 chars:`);
                console.log(`"${stdoutBuffer.substring(0, 500)}"`);
                
                try {
                    const parsed = JSON.parse(stdoutBuffer.trim());
                    console.log(`✅ JSON parsing successful`);
                    console.log(`Success: ${parsed.success}`);
                } catch (e) {
                    console.log(`❌ JSON parsing failed: ${e.message}`);
                    console.log(`First problematic character: "${stdoutBuffer.charAt(0)}" (${stdoutBuffer.charCodeAt(0)})`);
                }
            }
            
            if (stderrBuffer.length > 0) {
                console.log(`\nStderr output:`);
                console.log(stderrBuffer);
            }
            
            resolve(code === 0);
        });
        
        process.on('error', (err) => {
            console.error(`❌ Failed to start backend process: ${err.message}`);
            resolve(false);
        });
    });
}

async function main() {
    console.log('=== 4DSTAR Packaged App Debug Tool ===');
    console.log(`Platform: ${process.platform}`);
    console.log(`Architecture: ${process.arch}`);
    console.log(`Node version: ${process.version}`);
    console.log(`Working directory: ${process.cwd()}`);
    
    // Get test bundle path from command line or use default
    const testBundlePath = process.argv[2] || '/path/to/test.fbundle';
    
    if (!fs.existsSync(testBundlePath)) {
        console.error(`❌ Test bundle not found: ${testBundlePath}`);
        console.log(`Usage: node debug-packaged-app.js <path-to-test-bundle>`);
        process.exit(1);
    }
    
    // Test different backend paths
    const backendPaths = [
        // Development path
        path.resolve(__dirname, '..', 'build', 'electron', 'dist', 'fourdst-backend', 'fourdst-backend'),
        // Packaged app path (if running from within app)
        path.join(process.resourcesPath || '', 'backend', 'fourdst-backend'),
        // Alternative packaged paths
        path.join(__dirname, '..', 'resources', 'backend', 'fourdst-backend'),
        path.join(__dirname, 'backend', 'fourdst-backend'),
    ];
    
    console.log(`\n=== Testing Backend Paths ===`);
    for (const backendPath of backendPaths) {
        console.log(`\nTesting: ${backendPath}`);
        const success = await testBackendExecutable(backendPath, testBundlePath);
        if (success) {
            console.log(`✅ Backend test successful!`);
            break;
        } else {
            console.log(`❌ Backend test failed`);
        }
    }
    
    // Environment diagnostics
    console.log(`\n=== Environment Diagnostics ===`);
    console.log(`USER: ${process.env.USER || 'unknown'}`);
    console.log(`HOME: ${process.env.HOME || 'unknown'}`);
    console.log(`PATH: ${process.env.PATH || 'unknown'}`);
    console.log(`PYTHONPATH: ${process.env.PYTHONPATH || 'not set'}`);
    
    // Check permissions
    console.log(`\n=== Permission Check ===`);
    for (const backendPath of backendPaths) {
        if (fs.existsSync(backendPath)) {
            try {
                const stats = fs.statSync(backendPath);
                console.log(`${backendPath}:`);
                console.log(`  Executable: ${!!(stats.mode & parseInt('111', 8))}`);
                console.log(`  Mode: ${stats.mode.toString(8)}`);
                console.log(`  Size: ${stats.size} bytes`);
            } catch (e) {
                console.log(`${backendPath}: Permission error - ${e.message}`);
            }
        }
    }
}

if (require.main === module) {
    main().catch(console.error);
}

module.exports = { testBackendExecutable };
