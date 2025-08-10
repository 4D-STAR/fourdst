const { app, BrowserWindow, ipcMain, dialog, nativeTheme } = require('electron');
const path = require('path');
const fs = require('fs-extra');
const yaml = require('js-yaml');
const AdmZip = require('adm-zip');
const { spawn } = require('child_process');

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (require('electron-squirrel-startup')) {
  app.quit();
}

let mainWindow;

const createWindow = () => {
  // Create the browser window.
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true,
    },
  });

  // and load the index.html of the app.
  mainWindow.loadFile(path.join(__dirname, 'index.html'));

  // Open the DevTools for debugging
  // mainWindow.webContents.openDevTools();

  nativeTheme.on('updated', () => {
    if (mainWindow) {
      mainWindow.webContents.send('theme-updated', { shouldUseDarkColors: nativeTheme.shouldUseDarkColors });
    }
  });
};

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.on('ready', createWindow);

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
ipcMain.handle('get-dark-mode', () => {
  return nativeTheme.shouldUseDarkColors;
});

ipcMain.on('show-error-dialog', (event, { title, content }) => {
  dialog.showErrorBox(title, content);
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  // On OS X it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// IPC handlers
ipcMain.handle('select-file', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openFile'],
    filters: [
      { name: 'Fbundle Archives', extensions: ['fbundle'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  });
  
  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

ipcMain.handle('select-directory', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory']
  });
  
  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

ipcMain.handle('select-save-file', async () => {
  const result = await dialog.showSaveDialog({
    filters: [
      { name: 'Fbundle Archives', extensions: ['fbundle'] }
    ]
  });
  
  if (!result.canceled) {
    return result.filePath;
  }
  return null;
});

// Helper function to run python commands via the bundled backend
function runPythonCommand(command, kwargs, event) {
    const buildDir = path.resolve(__dirname, '..', 'build');
    let backendPath;
    if (app.isPackaged) {
        backendPath = path.join(process.resourcesPath, 'fourdst-backend');
    } else {
        backendPath = path.join(buildDir, 'electron', 'dist', 'fourdst-backend', 'fourdst-backend');
    }

    console.log(`[MAIN_PROCESS] Spawning backend: ${backendPath}`);
    const args = [command, JSON.stringify(kwargs)];
    console.log(`[MAIN_PROCESS] With args: [${args.join(', ')}]`);

    return new Promise((resolve) => {
        const process = spawn(backendPath, args);
        let stdoutBuffer = '';
        let errorOutput = '';

        process.stderr.on('data', (data) => {
            errorOutput += data.toString();
            console.error('Backend STDERR:', data.toString().trim());
        });

        const isStreaming = command === 'fill_bundle';

        process.stdout.on('data', (data) => {
            const chunk = data.toString();
            stdoutBuffer += chunk;

            if (isStreaming && event) {
                // Process buffer line by line for streaming commands
                let newlineIndex;
                while ((newlineIndex = stdoutBuffer.indexOf('\n')) >= 0) {
                    const line = stdoutBuffer.substring(0, newlineIndex).trim();
                    stdoutBuffer = stdoutBuffer.substring(newlineIndex + 1);

                    if (line) {
                        try {
                            const parsed = JSON.parse(line);
                            if (parsed.type === 'progress') {
                                event.sender.send('fill-bundle-progress', parsed.data);
                            } else {
                                // Not a progress update, put it back in the buffer for final processing
                                stdoutBuffer = line + '\n' + stdoutBuffer;
                                break; // Stop processing lines
                            }
                        } catch (e) {
                            // Ignore parsing errors for intermediate lines in a stream
                        }
                    }
                }
            }
        });

        process.on('close', (code) => {
            console.log(`[MAIN_PROCESS] Backend process exited with code ${code}`);
            let resultData = null;

            try {
                // Core functions now return clean JSON directly
                const finalJson = JSON.parse(stdoutBuffer.trim());
                resultData = finalJson;  // Use the JSON response directly
            } catch (e) {
                console.error(`[MAIN_PROCESS] Could not parse backend output as JSON: ${e}`);
                console.error(`[MAIN_PROCESS] Raw output: "${stdoutBuffer}"`);
                // If parsing fails, return a structured error response
                resultData = { 
                    success: false, 
                    error: `JSON parsing failed: ${e.message}`,
                    raw_output: stdoutBuffer 
                };
            }

            const finalError = errorOutput.trim();
            if (finalError && !resultData) {
                resolve({ success: false, error: finalError });
            } else if (resultData) {
                resolve(resultData);
            } else {
                const errorMessage = finalError || `The script finished without returning a result (exit code: ${code})`;
                resolve({ success: false, error: errorMessage });
            }
        });

        process.on('error', (err) => {
            resolve({ success: false, error: `Failed to start backend process: ${err.message}` });
        });
    });
}

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

ipcMain.handle('validate-bundle', async (event, bundlePath) => {
    const kwargs = {
        bundle_path: bundlePath
    };
    return runPythonCommand('validate_bundle', kwargs, event);
});

ipcMain.handle('clear-bundle', async (event, bundlePath) => {
    const kwargs = { bundle_path: bundlePath };
    return runPythonCommand('clear_bundle', kwargs, event);
});

ipcMain.handle('get-fillable-targets', async (event, bundlePath) => {
    const kwargs = { bundle_path: bundlePath };
    return runPythonCommand('get_fillable_targets', kwargs, event);
});

ipcMain.handle('fill-bundle', async (event, { bundlePath, targetsToBuild }) => {
    const kwargs = {
        bundle_path: bundlePath,
        targets_to_build: targetsToBuild
    };
    
    // Pass event to stream progress
    return runPythonCommand('fill_bundle', kwargs, event);
});

ipcMain.handle('edit-bundle', async (event, { bundlePath, updatedManifest }) => {
    const kwargs = {
        bundle_path: bundlePath,
        metadata: updatedManifest
    };
    return runPythonCommand('edit_bundle_metadata', kwargs, event);
});

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

// Handle show save dialog
ipcMain.handle('show-save-dialog', async (event, options) => {
    const result = await dialog.showSaveDialog(BrowserWindow.fromWebContents(event.sender), options);
    return result;
});

// Handle file copying
ipcMain.handle('copy-file', async (event, { source, destination }) => {
    try {
        await fs.copy(source, destination);
        return { success: true };
    } catch (error) {
        return { success: false, error: error.message };
    }
});
