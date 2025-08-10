const { app, BrowserWindow, ipcMain, nativeTheme } = require('electron');
const path = require('path');

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (require('electron-squirrel-startup')) {
  app.quit();
}

let mainWindow;
let themeUpdateListener;

const createWindow = () => {
  // Create the browser window.
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    icon: path.join(__dirname, '..', 'toolkitIcon.png'),
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true,
    },
  });

  // and load the index.html of the app.
  mainWindow.loadFile(path.join(__dirname, '..', 'index.html'));

  // Open the DevTools for debugging
  // mainWindow.webContents.openDevTools();

  // Clean up any existing theme listener
  if (themeUpdateListener) {
    nativeTheme.removeListener('updated', themeUpdateListener);
  }

  // Create new theme listener with proper safety checks
  themeUpdateListener = () => {
    if (mainWindow && !mainWindow.isDestroyed() && mainWindow.webContents) {
      try {
        mainWindow.webContents.send('theme-updated', { shouldUseDarkColors: nativeTheme.shouldUseDarkColors });
      } catch (error) {
        console.warn('Failed to send theme update:', error.message);
        // Remove the listener if sending fails
        nativeTheme.removeListener('updated', themeUpdateListener);
        themeUpdateListener = null;
      }
    }
  };

  nativeTheme.on('updated', themeUpdateListener);

  // Clean up when window is closed
  mainWindow.on('closed', () => {
    if (themeUpdateListener) {
      nativeTheme.removeListener('updated', themeUpdateListener);
      themeUpdateListener = null;
    }
    mainWindow = null;
  });
};

const setupAppEventHandlers = () => {
  // This method will be called when Electron has finished
  // initialization and is ready to create browser windows.
  // Some APIs can only be used after this event occurs.
  app.on('ready', createWindow);

  // Quit when all windows are closed, except on macOS. There, it's common
  // for applications and their menu bar to stay active until the user quits
  // explicitly with Cmd + Q.
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
};

const setupThemeHandlers = () => {
  ipcMain.handle('get-dark-mode', () => {
    return nativeTheme.shouldUseDarkColors;
  });
};

const getMainWindow = () => {
  return mainWindow;
};

module.exports = {
  setupAppEventHandlers,
  setupThemeHandlers,
  getMainWindow,
  createWindow
};
