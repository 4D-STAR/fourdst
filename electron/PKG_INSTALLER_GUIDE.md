# 4DSTAR Bundle Manager .pkg Installer Guide

## Overview

The 4DSTAR Bundle Manager now includes a professional macOS `.pkg` installer that provides a seamless installation experience with automatic file association setup and dependency guidance.

## What's Included

### 📦 **Professional Installer Package**
- Native macOS `.pkg` installer format
- Automatic Launch Services refresh
- File association setup
- Custom icon registration
- Dependency information dialogs

### 🔧 **Automatic Post-Install Setup**
- Launch Services database refresh
- File association registration
- Icon cache clearing
- Finder restart for immediate functionality

### 📋 **User Guidance**
- Welcome dialog explaining system requirements
- Clear distinction between basic and advanced usage
- Optional dependency installation instructions
- Conclusion dialog with next steps

## Installation Experience

### 1. **Welcome Screen**
Users see a comprehensive welcome dialog that explains:
- **Basic Usage**: No dependencies required for bundle management
- **Advanced Usage**: Docker and Meson needed for plugin building
- **System Requirements**: macOS 10.12+ minimum
- **What's Included**: App, file associations, custom icons

### 2. **Standard macOS Installation**
- License agreement (if configured)
- Installation destination (defaults to /Applications)
- Administrator password prompt
- Installation progress

### 3. **Automatic Post-Install**
The installer automatically:
- Refreshes Launch Services database
- Registers file associations for .fbundle and .opat files
- Clears icon caches
- Restarts Finder
- Logs all operations to `/tmp/4dstar-postinstall.log`

### 4. **Conclusion Screen**
Users see a success dialog with:
- Installation confirmation
- Getting started instructions
- Optional dependency installation commands
- Troubleshooting information

## File Associations

### Supported File Types
- **`.fbundle`**: 4DSTAR Plugin Bundle Files
- **`.opat`**: OPAT Data Files

### What Works After Installation
- ✅ Double-click files to open in 4DSTAR Bundle Manager
- ✅ Right-click → "Open with 4DSTAR Bundle Manager"
- ✅ Custom file icons in Finder
- ✅ Proper file type descriptions
- ✅ Immediate functionality (no restart required)

## Dependencies

### Required (Always)
- macOS 10.12 or later
- No additional dependencies for basic bundle management

### Optional (Advanced Features)
- **Docker Desktop**: For cross-platform plugin builds
- **Meson Build System**: For native plugin compilation
- **Xcode Command Line Tools**: For C++ compilation

### Installation Commands (Optional)
```bash
# Install Xcode Command Line Tools
xcode-select --install

# Install Meson via Homebrew
brew install meson

# Download Docker Desktop
# Visit: https://docker.com/products/docker-desktop
```

## Build Configuration

### Package.json Configuration
```json
{
  "build": {
    "mac": {
      "target": [
        { "target": "dmg", "arch": ["x64", "arm64"] },
        { "target": "pkg", "arch": ["x64", "arm64"] },
        { "target": "zip", "arch": ["x64", "arm64"] }
      ]
    },
    "pkg": {
      "scripts": "installer-scripts",
      "welcome": "installer-resources/welcome.html",
      "conclusion": "installer-resources/conclusion.html",
      "installLocation": "/Applications",
      "mustClose": ["com.fourdst.bundlemanager"]
    }
  }
}
```

### File Structure
```
electron/
├── installer-scripts/
│   └── postinstall              # Post-install script
├── installer-resources/
│   ├── welcome.html            # Welcome dialog
│   └── conclusion.html         # Conclusion dialog
├── icons/
│   ├── app-icon.icns          # Main app icon
│   ├── fbundle-icon.icns      # .fbundle file icon
│   └── opat-icon.icns         # .opat file icon
└── package.json               # Build configuration
```

## Building the Installer

### Generate All Installers
```bash
npm run build
```

### Generate Only .pkg
```bash
npx electron-builder --mac pkg
```

### Output Files
- `dist/4DSTAR Bundle Manager-1.0.0.pkg` (x64)
- `dist/4DSTAR Bundle Manager-1.0.0-arm64.pkg` (ARM64)
- Plus traditional .dmg and .zip files

## Post-Install Script Details

### What It Does
```bash
#!/bin/bash
# Reset Launch Services database
lsregister -kill -r -domain local -domain system -domain user

# Register the app bundle
lsregister -f "/Applications/4DSTAR Bundle Manager.app"

# Clear icon caches
rm -rf ~/Library/Caches/com.apple.iconservices.store
rm -rf /Library/Caches/com.apple.iconservices.store

# Restart Finder
killall Finder
```

### Logging
All operations are logged to `/tmp/4dstar-postinstall.log` for troubleshooting.

## Troubleshooting

### If File Associations Don't Work
1. Check post-install log: `cat /tmp/4dstar-postinstall.log`
2. Manually refresh: `npm run refresh-icons`
3. Right-click file → Get Info → Change default app

### If Icons Don't Appear
1. Wait 2-3 minutes for macOS to update
2. Log out and back in
3. Restart the Mac
4. Check icon cache clearing in post-install log

### If Installation Fails
1. Ensure you have administrator privileges
2. Close any running instances of the app
3. Check available disk space (>200MB required)
4. Try installing from a different location

## Developer Notes

### Testing the Installer
1. Build the .pkg installer
2. Test on a clean macOS system or VM
3. Verify file associations work immediately
4. Check that icons appear in Finder
5. Test with both .fbundle and .opat files

### Customizing Dialogs
- Edit `installer-resources/welcome.html` for welcome content
- Edit `installer-resources/conclusion.html` for conclusion content
- HTML/CSS styling is supported
- Keep content concise and user-friendly

### Modifying Post-Install Script
- Edit `installer-scripts/postinstall`
- Ensure script remains executable: `chmod +x postinstall`
- Test thoroughly on different macOS versions
- Add logging for all operations

## Distribution

### Recommended Distribution Method
1. **Primary**: `.pkg` installer for best user experience
2. **Alternative**: `.dmg` for users who prefer disk images
3. **Developer**: `.zip` for automated deployment

### Code Signing (Production)
For production distribution:
1. Obtain Apple Developer ID certificate
2. Configure code signing in package.json
3. Notarize the installer with Apple
4. Test on systems with Gatekeeper enabled

## User Support

### Common User Questions

**Q: Do I need Docker to use the app?**
A: No, Docker is only needed for building plugins. Basic bundle management works without any additional software.

**Q: Why do I need administrator privileges?**
A: The installer needs to install the app to /Applications and register file associations system-wide.

**Q: Can I install to a different location?**
A: The .pkg installer installs to /Applications by default. Use the .dmg version for custom locations.

**Q: Will this work on older Macs?**
A: Yes, the app supports macOS 10.12 and later on both Intel and Apple Silicon Macs.

This comprehensive installer solution provides a professional, user-friendly installation experience that handles all technical setup automatically while clearly communicating optional dependencies to users.
