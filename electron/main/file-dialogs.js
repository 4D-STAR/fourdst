const { ipcMain, dialog, BrowserWindow } = require('electron');

const setupFileDialogHandlers = () => {
  // File selection dialog
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

  // Directory selection dialog
  ipcMain.handle('select-directory', async () => {
    const result = await dialog.showOpenDialog({
      properties: ['openDirectory']
    });
    
    if (!result.canceled && result.filePaths.length > 0) {
      return result.filePaths[0];
    }
    return null;
  });

  // Save file dialog
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

  // Generic save dialog with options
  ipcMain.handle('show-save-dialog', async (event, options) => {
    const result = await dialog.showSaveDialog(BrowserWindow.fromWebContents(event.sender), options);
    return result;
  });

  // Error dialog
  ipcMain.on('show-error-dialog', (event, { title, content }) => {
    dialog.showErrorBox(title, content);
  });
};

module.exports = {
  setupFileDialogHandlers
};
