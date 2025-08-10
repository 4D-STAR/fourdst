// State management module for the 4DSTAR Bundle Manager
// Extracted from renderer.js to centralize state handling

// --- GLOBAL STATE ---
let currentBundle = null;
let currentBundlePath = null;
let hasUnsavedChanges = false;
let originalMetadata = {};
let pendingOperation = null; // Store the operation to execute after warning confirmation

// Current OPAT file state
let currentOPATFile = null;

// Bundle state management
const getBundleState = () => ({
  currentBundle,
  currentBundlePath,
  hasUnsavedChanges,
  originalMetadata
});

const setBundleState = (bundle, bundlePath) => {
  currentBundle = bundle;
  currentBundlePath = bundlePath;
  hasUnsavedChanges = false;
  originalMetadata = bundle ? { ...bundle.manifest } : {};
};

const clearBundleState = () => {
  currentBundle = null;
  currentBundlePath = null;
  hasUnsavedChanges = false;
  originalMetadata = {};
};

const markUnsavedChanges = (hasChanges = true) => {
  hasUnsavedChanges = hasChanges;
};

const updateOriginalMetadata = (metadata) => {
  originalMetadata = { ...metadata };
};

// Pending operation management
const setPendingOperation = (operation) => {
  pendingOperation = operation;
};

const getPendingOperation = () => {
  return pendingOperation;
};

const clearPendingOperation = () => {
  pendingOperation = null;
};

// OPAT file state management
const setOPATFile = (opatFile) => {
  currentOPATFile = opatFile;
};

const getOPATFile = () => {
  return currentOPATFile;
};

const clearOPATFile = () => {
  currentOPATFile = null;
};

// Export state management functions
module.exports = {
  // Bundle state
  getBundleState,
  setBundleState,
  clearBundleState,
  markUnsavedChanges,
  updateOriginalMetadata,
  
  // Pending operations
  setPendingOperation,
  getPendingOperation,
  clearPendingOperation,
  
  // OPAT file state
  setOPATFile,
  getOPATFile,
  clearOPATFile,
  
  // Direct state access (for compatibility)
  getCurrentBundle: () => currentBundle,
  getCurrentBundlePath: () => currentBundlePath,
  getHasUnsavedChanges: () => hasUnsavedChanges,
  getOriginalMetadata: () => originalMetadata
};
