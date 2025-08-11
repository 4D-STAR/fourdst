#!/usr/bin/env node

/**
 * Icon Generation Script for 4DSTAR Bundle Manager
 * 
 * Generates all required macOS icon formats from the SVG source
 * and creates the proper .icns file for the app bundle.
 */

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

class IconGenerator {
    constructor() {
        this.projectRoot = path.resolve(__dirname, '..');
        this.iconOutputDir = path.join(__dirname, 'icons');
        this.tempDir = path.join(__dirname, 'temp-icons');
        
        // Icon source paths
        this.appIconSvg = path.join(this.projectRoot, 'assets', 'toolkit', 'appicon', 'toolkitIcon.svg');
        this.bundleIconSvg = path.join(this.projectRoot, 'assets', 'bundle', 'fourdst_bundle_icon.svg');
        this.opatIconSvg = path.join(this.projectRoot, 'assets', 'opat', 'fourdst_opat_icon.svg');
        
        // macOS app icon sizes (for .icns)
        this.appIconSizes = [
            { size: 16, scale: 1 },
            { size: 16, scale: 2 },
            { size: 32, scale: 1 },
            { size: 32, scale: 2 },
            { size: 128, scale: 1 },
            { size: 128, scale: 2 },
            { size: 256, scale: 1 },
            { size: 256, scale: 2 },
            { size: 512, scale: 1 },
            { size: 512, scale: 2 }
        ];
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

    async runCommand(command, args, options = {}) {
        return new Promise((resolve, reject) => {
            const process = spawn(command, args, { 
                stdio: 'pipe',
                ...options 
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
                    resolve({ stdout, stderr });
                } else {
                    reject(new Error(`Command failed with exit code ${code}: ${stderr}`));
                }
            });
            
            process.on('error', (err) => {
                reject(err);
            });
        });
    }

    checkDependencies() {
        this.log('Checking dependencies...', 'info');
        
        // Check if all SVG sources exist
        const svgSources = [
            { name: 'App icon', path: this.appIconSvg },
            { name: 'Bundle icon', path: this.bundleIconSvg },
            { name: 'OPAT icon', path: this.opatIconSvg }
        ];
        
        for (const source of svgSources) {
            if (!fs.existsSync(source.path)) {
                throw new Error(`${source.name} SVG not found: ${source.path}`);
            }
            this.log(`✓ ${source.name} SVG found: ${source.path}`, 'success');
        }
        
        // Check for required tools
        const requiredTools = ['rsvg-convert', 'iconutil'];
        const missingTools = [];
        
        for (const tool of requiredTools) {
            try {
                this.runCommand('which', [tool]);
                this.log(`✓ ${tool} available`, 'success');
            } catch (e) {
                missingTools.push(tool);
            }
        }
        
        if (missingTools.length > 0) {
            this.log('Missing required tools. Installing...', 'warning');
            this.installDependencies(missingTools);
        }
    }

    async installDependencies(missingTools) {
        if (missingTools.includes('rsvg-convert')) {
            this.log('Installing librsvg (for rsvg-convert)...', 'info');
            try {
                await this.runCommand('brew', ['install', 'librsvg']);
                this.log('✓ librsvg installed', 'success');
            } catch (e) {
                throw new Error('Failed to install librsvg. Please install manually: brew install librsvg');
            }
        }
        
        // iconutil is part of Xcode command line tools
        if (missingTools.includes('iconutil')) {
            this.log('iconutil not found. Installing Xcode command line tools...', 'info');
            try {
                await this.runCommand('xcode-select', ['--install']);
                this.log('✓ Xcode command line tools installation started', 'success');
                this.log('Please complete the installation and run this script again', 'warning');
                process.exit(0);
            } catch (e) {
                throw new Error('Failed to install Xcode command line tools. Please install manually.');
            }
        }
    }

    async generatePNGIcons() {
        this.log('Generating PNG icons from SVG...', 'info');
        
        // Create temp directory
        if (fs.existsSync(this.tempDir)) {
            fs.rmSync(this.tempDir, { recursive: true });
        }
        fs.mkdirSync(this.tempDir, { recursive: true });
        
        // Generate app icons
        this.log('  Generating app icons...', 'info');
        for (const iconSpec of this.appIconSizes) {
            const fileName = iconSpec.scale === 1 
                ? `app_icon_${iconSpec.size}x${iconSpec.size}.png`
                : `app_icon_${iconSpec.size}x${iconSpec.size}@${iconSpec.scale}x.png`;
            
            const outputPath = path.join(this.tempDir, fileName);
            const actualSize = iconSpec.size * iconSpec.scale;
            
            this.log(`    Generating ${fileName} (${actualSize}x${actualSize})...`, 'info');
            
            try {
                await this.runCommand('rsvg-convert', [
                    '--width', actualSize.toString(),
                    '--height', actualSize.toString(),
                    '--format', 'png',
                    '--output', outputPath,
                    this.appIconSvg
                ]);
                
                this.log(`      ✓ ${fileName}`, 'success');
            } catch (error) {
                throw new Error(`Failed to generate ${fileName}: ${error.message}`);
            }
        }
    }

    async createAppIconsFile() {
        this.log('Creating .icns file for macOS app bundle...', 'info');
        
        const iconsetDir = path.join(this.tempDir, 'app-icon.iconset');
        if (!fs.existsSync(iconsetDir)) {
            fs.mkdirSync(iconsetDir, { recursive: true });
        }
        
        // Copy PNG files to iconset with proper naming
        for (const iconSpec of this.appIconSizes) {
            const sourceFileName = iconSpec.scale === 1 
                ? `app_icon_${iconSpec.size}x${iconSpec.size}.png`
                : `app_icon_${iconSpec.size}x${iconSpec.size}@${iconSpec.scale}x.png`;
            
            const targetFileName = iconSpec.scale === 1 
                ? `icon_${iconSpec.size}x${iconSpec.size}.png`
                : `icon_${iconSpec.size}x${iconSpec.size}@${iconSpec.scale}x.png`;
            
            const sourcePath = path.join(this.tempDir, sourceFileName);
            const targetPath = path.join(iconsetDir, targetFileName);
            
            fs.copyFileSync(sourcePath, targetPath);
        }
        
        // Create .icns file
        const icnsPath = path.join(this.iconOutputDir, 'app-icon.icns');
        await this.runCommand('iconutil', [
            '--convert', 'icns',
            '--output', icnsPath,
            iconsetDir
        ]);
        
        this.log(`✓ Created app-icon.icns: ${icnsPath}`, 'success');
        
        // Clean up iconset directory
        fs.rmSync(iconsetDir, { recursive: true, force: true });
    }

    async createDocumentIcons() {
        this.log('Generating document type icons...', 'info');
        
        const documentTypes = [
            { name: 'fbundle', filename: 'fbundle-icon.icns', svgSource: this.bundleIconSvg },
            { name: 'opat', filename: 'opat-icon.icns', svgSource: this.opatIconSvg }
        ];
        
        for (const docType of documentTypes) {
            this.log(`  Creating ${docType.name} document icon...`, 'info');
            
            const iconsetDir = path.join(this.tempDir, `${docType.name}-icon.iconset`);
            if (!fs.existsSync(iconsetDir)) {
                fs.mkdirSync(iconsetDir, { recursive: true });
            }
            
            // Generate document icons using the specific SVG for each type
            for (const iconSpec of this.appIconSizes) {
                const fileName = iconSpec.scale === 1 
                    ? `icon_${iconSpec.size}x${iconSpec.size}.png`
                    : `icon_${iconSpec.size}x${iconSpec.size}@${iconSpec.scale}x.png`;
                
                const outputPath = path.join(iconsetDir, fileName);
                const actualSize = iconSpec.size * iconSpec.scale;
                
                try {
                    await this.runCommand('rsvg-convert', [
                        '--width', actualSize.toString(),
                        '--height', actualSize.toString(),
                        '--format', 'png',
                        '--output', outputPath,
                        docType.svgSource
                    ]);
                } catch (error) {
                    throw new Error(`Failed to generate ${docType.name} icon ${fileName}: ${error.message}`);
                }
            }
            
            // Create .icns file
            const icnsPath = path.join(this.iconOutputDir, docType.filename);
            await this.runCommand('iconutil', [
                '--convert', 'icns',
                '--output', icnsPath,
                iconsetDir
            ]);
            
            this.log(`    ✓ Created ${docType.filename}`, 'success');
            
            // Clean up iconset directory
            fs.rmSync(iconsetDir, { recursive: true, force: true });
        }
    }

    cleanup() {
        this.log('Cleaning up temporary files...', 'info');
        if (fs.existsSync(this.tempDir)) {
            fs.rmSync(this.tempDir, { recursive: true });
        }
    }

    async generate() {
        try {
            this.log('Starting icon generation for 4DSTAR Bundle Manager...', 'info');
            
            // Create output directory
            if (!fs.existsSync(this.iconOutputDir)) {
                fs.mkdirSync(this.iconOutputDir, { recursive: true });
            }
            
            // Check dependencies
            this.checkDependencies();
            
            // Generate PNG icons
            await this.generatePNGIcons();
            
            // Generate .icns files
            await this.createAppIconsFile();
            await this.createDocumentIcons();
            
            // Cleanup
            this.cleanup();
            
            this.log('\n🎉 Icon generation completed successfully!', 'success');
            this.log(`Generated icons in: ${this.iconOutputDir}`, 'info');
            this.log('Files created:', 'info');
            this.log('  - app-icon.icns (main app icon)', 'info');
            this.log('  - fbundle-icon.icns (for .fbundle files)', 'info');
            this.log('  - opat-icon.icns (for .opat files)', 'info');
            
            return true;
            
        } catch (error) {
            this.log(`❌ Icon generation failed: ${error.message}`, 'error');
            this.cleanup();
            return false;
        }
    }
}

// Run icon generation if called directly
if (require.main === module) {
    const generator = new IconGenerator();
    generator.generate().then(success => {
        process.exit(success ? 0 : 1);
    }).catch(error => {
        console.error('Icon generation failed:', error);
        process.exit(1);
    });
}

module.exports = { IconGenerator };
