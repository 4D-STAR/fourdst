// === REGENERATED CODE START ===
// This file was regenerated during refactoring to use modular components
// Original functionality preserved in modular structure

// Import modular components
const { setupAppEventHandlers, setupThemeHandlers } = require('./main/app-lifecycle');
const { setupFileDialogHandlers } = require('./main/file-dialogs');
const { setupBundleIPCHandlers, setupKeyIPCHandlers } = require('./main/ipc-handlers');

// Initialize all modules in the correct order
function initializeMainProcess() {
  // Setup app lifecycle and window management
  setupAppEventHandlers();
  
  // Setup theme handling
  setupThemeHandlers();
  
  // Setup file dialog handlers
  setupFileDialogHandlers();
  
  // Setup bundle operation IPC handlers
  setupBundleIPCHandlers();
  
  // Setup key management IPC handlers
  setupKeyIPCHandlers();
  
  console.log('[MAIN_PROCESS] All modules initialized successfully');
}

// Start the application
initializeMainProcess();

// === REGENERATED CODE END ===
