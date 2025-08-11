#!/usr/bin/env node

/**
 * macOS Icon Refresh Script for 4DSTAR Bundle Manager
 * 
 * This script helps refresh macOS Launch Services database to ensure
 * file associations and custom icons are properly recognized after
 * app installation.
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

class MacOSIconRefresher {
    constructor() {
        this.appName = '4DSTAR Bundle Manager';
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

    async runCommand(command, args = []) {
        return new Promise((resolve, reject) => {
            const process = spawn(command, args, { 
                stdio: ['pipe', 'pipe', 'pipe'],
                shell: true 
            });
            
            let stdout = '';
            let stderr = '';
            
            process.stdout.on('data', (data) => {
                stdout += data.toString();
            });
            
            process.stderr.on('data', (data) => {
                stderr += data.toString();
            });
            
            process.on('close', (code) => {
                if (code === 0) {
                    resolve({ stdout: stdout.trim(), stderr: stderr.trim() });
                } else {
                    reject(new Error(`Command failed with code ${code}: ${stderr || stdout}`));
                }
            });
            
            process.on('error', (error) => {
                reject(error);
            });
        });
    }

    async checkIfMacOS() {
        if (process.platform !== 'darwin') {
            throw new Error('This script is only for macOS systems');
        }
        this.log('✓ Running on macOS', 'success');
    }

    async findAppBundle() {
        const possiblePaths = [
            `/Applications/${this.appName}.app`,
            path.join(process.env.HOME, 'Applications', `${this.appName}.app`),
            path.join(__dirname, 'dist', 'mac', `${this.appName}.app`),
            path.join(__dirname, 'dist', 'mac-arm64', `${this.appName}.app`)
        ];

        for (const appPath of possiblePaths) {
            if (fs.existsSync(appPath)) {
                this.log(`✓ Found app bundle: ${appPath}`, 'success');
                return appPath;
            }
        }

        throw new Error(`Could not find ${this.appName}.app in common locations. Please install the app first.`);
    }

    async refreshLaunchServices() {
        this.log('Refreshing Launch Services database...', 'info');
        
        try {
            // Reset Launch Services database
            await this.runCommand('/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister', [
                '-kill',
                '-r',
                '-domain', 'local',
                '-domain', 'system',
                '-domain', 'user'
            ]);
            
            this.log('✓ Launch Services database reset', 'success');
        } catch (error) {
            this.log(`Warning: Could not reset Launch Services database: ${error.message}`, 'warning');
        }
    }

    async registerAppBundle(appPath) {
        this.log(`Registering app bundle: ${appPath}`, 'info');
        
        try {
            // Register the specific app bundle
            await this.runCommand('/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister', [
                '-f', appPath
            ]);
            
            this.log('✓ App bundle registered with Launch Services', 'success');
        } catch (error) {
            this.log(`Warning: Could not register app bundle: ${error.message}`, 'warning');
        }
    }

    async touchDesktop() {
        this.log('Refreshing desktop and Finder...', 'info');
        
        try {
            // Touch the desktop to refresh Finder
            await this.runCommand('touch', [path.join(process.env.HOME, 'Desktop')]);
            
            // Kill and restart Finder to refresh file associations
            await this.runCommand('killall', ['Finder']);
            
            this.log('✓ Desktop and Finder refreshed', 'success');
        } catch (error) {
            this.log(`Warning: Could not refresh Finder: ${error.message}`, 'warning');
        }
    }

    async clearIconCache() {
        this.log('Clearing icon cache...', 'info');
        
        try {
            // Clear icon cache
            const iconCachePaths = [
                path.join(process.env.HOME, 'Library/Caches/com.apple.iconservices.store'),
                '/Library/Caches/com.apple.iconservices.store',
                '/System/Library/Caches/com.apple.iconservices.store'
            ];

            for (const cachePath of iconCachePaths) {
                if (fs.existsSync(cachePath)) {
                    try {
                        await this.runCommand('sudo', ['rm', '-rf', cachePath]);
                        this.log(`✓ Cleared icon cache: ${cachePath}`, 'success');
                    } catch (error) {
                        this.log(`Could not clear ${cachePath}: ${error.message}`, 'warning');
                    }
                }
            }
        } catch (error) {
            this.log(`Warning: Could not clear all icon caches: ${error.message}`, 'warning');
        }
    }

    async refresh() {
        try {
            this.log(`Starting macOS icon refresh for ${this.appName}...`, 'info');
            
            // Check if we're on macOS
            await this.checkIfMacOS();
            
            // Find the app bundle
            const appPath = await this.findAppBundle();
            
            // Refresh Launch Services
            await this.refreshLaunchServices();
            
            // Register the app bundle
            await this.registerAppBundle(appPath);
            
            // Clear icon cache (requires sudo)
            this.log('Note: Icon cache clearing may require sudo password', 'info');
            await this.clearIconCache();
            
            // Refresh desktop and Finder
            await this.touchDesktop();
            
            this.log('\n🎉 macOS icon refresh completed!', 'success');
            this.log('File associations and icons should now be updated.', 'info');
            this.log('If icons still don\'t appear, try logging out and back in.', 'info');
            
            return true;
            
        } catch (error) {
            this.log(`❌ Icon refresh failed: ${error.message}`, 'error');
            return false;
        }
    }
}

// Run icon refresh if called directly
if (require.main === module) {
    const refresher = new MacOSIconRefresher();
    refresher.refresh().then(success => {
        process.exit(success ? 0 : 1);
    });
}

module.exports = MacOSIconRefresher;
