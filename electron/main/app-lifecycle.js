const { app, BrowserWindow, ipcMain, nativeTheme } = require('electron');
const path = require('path');

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
try {
  if (require('electron-squirrel-startup')) {
    app.quit();
  }
} catch (error) {
  // electron-squirrel-startup is not available or not needed on this platform
  console.log('electron-squirrel-startup not available, continuing...');
}

let mainWindow;
let themeUpdateListener;
let pendingFileToOpen = null;

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
  app.on('ready', () => {
    createWindow();
    
    // Handle any queued file open requests
    if (pendingFileToOpen) {
      console.log(`[MAIN_PROCESS] Processing queued file: ${pendingFileToOpen}`);
      const filePath = pendingFileToOpen;
      pendingFileToOpen = null;
      
      // Wait for window to be ready, then open the file
      if (mainWindow.webContents.isLoading()) {
        mainWindow.webContents.once('did-finish-load', () => {
          handleFileOpen(filePath);
        });
      } else {
        handleFileOpen(filePath);
      }
    }
  });

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

  // Handle file associations on macOS
  app.on('open-file', (event, filePath) => {
    event.preventDefault();
    console.log(`[MAIN_PROCESS] Opening file via association: ${filePath}`);
    
    // If app is not ready yet, queue the file to open later
    if (!app.isReady()) {
      console.log(`[MAIN_PROCESS] App not ready, queuing file: ${filePath}`);
      pendingFileToOpen = filePath;
      return;
    }
    
    // If no window exists, create one first
    if (!mainWindow) {
      createWindow();
    }
    
    // Wait for window to be ready, then send the file path
    if (mainWindow.webContents.isLoading()) {
      mainWindow.webContents.once('did-finish-load', () => {
        handleFileOpen(filePath);
      });
    } else {
      handleFileOpen(filePath);
    }
  });

  // Handle file associations on Windows/Linux via command line args
  if (process.platform !== 'darwin') {
    // Check if app was launched with a file argument
    const fileArg = process.argv.find(arg => arg.endsWith('.fbundle') || arg.endsWith('.opat'));
    if (fileArg && mainWindow) {
      handleFileOpen(fileArg);
    }
  }
};

// Helper function to handle file opening
const handleFileOpen = (filePath) => {
  if (!mainWindow || mainWindow.isDestroyed()) {
    console.warn('[MAIN_PROCESS] Cannot open file - main window not available');
    return;
  }

  const fileExtension = path.extname(filePath).toLowerCase();
  
  if (fileExtension === '.fbundle') {
    console.log(`[MAIN_PROCESS] Opening .fbundle file: ${filePath}`);
    mainWindow.webContents.send('open-bundle-file', filePath);
  } else if (fileExtension === '.opat') {
    console.log(`[MAIN_PROCESS] Opening .opat file: ${filePath}`);
    mainWindow.webContents.send('open-opat-file', filePath);
  } else {
    console.warn(`[MAIN_PROCESS] Unknown file type: ${filePath}`);
  }
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
