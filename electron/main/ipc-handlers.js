const { ipcMain, dialog, shell } = require('electron');
const { runPythonCommand } = require('./backend-bridge');
const fs = require('fs-extra');
const path = require('path');

const setupBundleIPCHandlers = () => {
  // Create bundle handler
  ipcMain.handle('create-bundle', async (event, bundleData) => {
    const kwargs = {
      plugin_dirs: bundleData.pluginDirs,
      output_path: bundleData.outputPath,
      bundle_name: bundleData.bundleName,
      bundle_version: bundleData.bundleVersion,
      bundle_author: bundleData.bundleAuthor,
      bundle_comment: bundleData.bundleComment,
    };

    const result = await runPythonCommand('create_bundle', kwargs, event);

    // The renderer expects a 'path' property on success
    if (result.success) {
      result.path = bundleData.outputPath;
    }

    return result;
  });

  // Sign bundle handler
  ipcMain.handle('sign-bundle', async (event, bundlePath) => {
    // Prompt for private key
    const result = await dialog.showOpenDialog({
      properties: ['openFile'],
      title: 'Select Private Key',
      filters: [{ name: 'PEM Private Key', extensions: ['pem'] }],
    });

    if (result.canceled || !result.filePaths || result.filePaths.length === 0) {
      return { success: false, error: 'Private key selection was canceled.' };
    }

    const privateKeyPath = result.filePaths[0];

    const kwargs = {
      bundle_path: bundlePath,
      private_key: privateKeyPath,
    };

    return runPythonCommand('sign_bundle', kwargs, event);
  });

  // Validate bundle handler
  ipcMain.handle('validate-bundle', async (event, bundlePath) => {
    const kwargs = {
      bundle_path: bundlePath
    };
    return runPythonCommand('validate_bundle', kwargs, event);
  });

  // Clear bundle handler
  ipcMain.handle('clear-bundle', async (event, bundlePath) => {
    const kwargs = { bundle_path: bundlePath };
    return runPythonCommand('clear_bundle', kwargs, event);
  });

  // Get fillable targets handler
  ipcMain.handle('get-fillable-targets', async (event, bundlePath) => {
    const kwargs = { bundle_path: bundlePath };
    return runPythonCommand('get_fillable_targets', kwargs, event);
  });

  // Fill bundle handler
  ipcMain.handle('fill-bundle', async (event, { bundlePath, targetsToBuild }) => {
    const kwargs = {
      bundle_path: bundlePath,
      targets_to_build: targetsToBuild
    };
    
    // Pass event to stream progress
    return runPythonCommand('fill_bundle', kwargs, event);
  });

  // Edit bundle metadata handler
  ipcMain.handle('edit-bundle', async (event, { bundlePath, updatedManifest }) => {
    const kwargs = {
      bundle_path: bundlePath,
      metadata: updatedManifest
    };
    return runPythonCommand('edit_bundle_metadata', kwargs, event);
  });

  // Open bundle handler
  ipcMain.handle('open-bundle', async (event, bundlePath) => {
    console.log(`[IPC_HANDLER] Opening bundle: ${bundlePath}`);
    const kwargs = { bundle_path: bundlePath };
    const result = await runPythonCommand('inspect_bundle', kwargs, event);
    
    console.log(`[IPC_HANDLER] inspect_bundle result:`, result);

    // Core functions now return consistent JSON structure directly
    if (result && result.success) {
      // The core inspect_bundle function returns the data directly
      // We just need to add the bundlePath for the renderer
      return {
        success: true,
        manifest: result.manifest,
        report: result,  // The entire result is the report
        bundlePath: bundlePath
      };
    }
    
    // Return error as-is since it's already in the correct format
    return result || { success: false, error: 'An unknown error occurred while opening the bundle.' };
  });

  // File copying handler
  ipcMain.handle('copy-file', async (event, { source, destination }) => {
    try {
      const fs = require('fs-extra');
      await fs.copy(source, destination);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  // Read license file handler
  ipcMain.handle('read-license', async () => {
    try {
      const licensePath = path.join(__dirname, '..', 'LICENSE.txt');
      console.log(`[IPC_HANDLER] Reading license from: ${licensePath}`);
      
      // Check if file exists
      const exists = await fs.pathExists(licensePath);
      console.log(`[IPC_HANDLER] License file exists: ${exists}`);
      
      if (!exists) {
        return { 
          success: false, 
          error: 'License file not found',
          content: `License file not found at: ${licensePath}`
        };
      }
      
      const licenseContent = await fs.readFile(licensePath, 'utf8');
      console.log(`[IPC_HANDLER] License content length: ${licenseContent.length} characters`);
      console.log(`[IPC_HANDLER] License starts with: "${licenseContent.substring(0, 100)}..."`);
      console.log(`[IPC_HANDLER] License ends with: "...${licenseContent.substring(licenseContent.length - 100)}"`);
      
      return { success: true, content: licenseContent };
    } catch (error) {
      console.error('Failed to read LICENSE.txt:', error);
      return { 
        success: false, 
        error: 'Could not load license file',
        content: 'GPL v3 license text could not be loaded. Please check that LICENSE.txt exists in the application directory.'
      };
    }
  });

  // Open external URL handler
  ipcMain.handle('open-external-url', async (event, url) => {
    try {
      console.log(`[IPC_HANDLER] Opening external URL: ${url}`);
      await shell.openExternal(url);
      return { success: true };
    } catch (error) {
      console.error('Failed to open external URL:', error);
      return { success: false, error: error.message };
    }
  });
};

module.exports = {
  setupBundleIPCHandlers
};
