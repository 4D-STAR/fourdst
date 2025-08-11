// DOM management module for the 4DSTAR Bundle Manager
// Extracted from renderer.js to centralize DOM element handling and view management

// --- DOM ELEMENTS (will be initialized in initializeDOMElements) ---
let welcomeScreen, bundleView, createBundleForm;
let openBundleBtn, createBundleBtn;
let signBundleBtn, validateBundleBtn, clearBundleBtn, saveMetadataBtn;
let saveOptionsModal, overwriteBundleBtn, saveAsNewBtn;
let signatureWarningModal, signatureWarningCancel, signatureWarningContinue;
let fillTabLink, loadFillableTargetsBtn, fillLoading, fillPluginsTables, fillNoTargets, fillTargetsContent;
let selectAllTargetsBtn, deselectAllTargetsBtn, startFillProcessBtn, fillProgressContainer, fillProgressContent;
let bundleTitle, manifestDetails;

// Static DOM elements (can be accessed immediately)
const pluginsList = document.getElementById('plugins-list');
const validationResults = document.getElementById('validation-results');

// Tabs
const tabLinks = document.querySelectorAll('.tab-link');
const tabPanes = document.querySelectorAll('.tab-pane');
const validationTabLink = document.querySelector('button[data-tab="validation-tab"]');

// Modal
const modal = document.getElementById('modal');
const modalTitle = document.getElementById('modal-title');
const modalMessage = document.getElementById('modal-message');
const modalCloseBtn = document.getElementById('modal-close-btn');

// Spinner
const spinner = document.getElementById('spinner');

// Fill Modal elements
const fillModal = document.getElementById('fill-modal');
const closeFillModalButton = document.querySelector('.close-fill-modal-button');
const fillModalTitle = document.getElementById('fill-modal-title');
const fillModalBody = document.getElementById('fill-modal-body');
const fillTargetsList = document.getElementById('fill-targets-list');
const startFillButton = document.getElementById('start-fill-button');
const fillProgressView = document.getElementById('fill-progress-view');
const fillProgressList = document.getElementById('fill-progress-list');

function initializeDOMElements() {
  // Views
  welcomeScreen = document.getElementById('welcome-screen');
  bundleView = document.getElementById('bundle-view');
  createBundleForm = document.getElementById('create-bundle-form');

  // Sidebar buttons
  openBundleBtn = document.getElementById('open-bundle-btn');
  createBundleBtn = document.getElementById('create-bundle-btn');

  // Bundle action buttons
  signBundleBtn = document.getElementById('sign-bundle-btn');
  validateBundleBtn = document.getElementById('validate-bundle-btn');
  clearBundleBtn = document.getElementById('clear-bundle-btn');
  saveMetadataBtn = document.getElementById('save-metadata-btn');

  // Save options modal elements
  saveOptionsModal = document.getElementById('save-options-modal');
  overwriteBundleBtn = document.getElementById('overwrite-bundle-btn');
  saveAsNewBtn = document.getElementById('save-as-new-btn');

  // Signature warning modal elements
  signatureWarningModal = document.getElementById('signature-warning-modal');
  signatureWarningCancel = document.getElementById('signature-warning-cancel');
  signatureWarningContinue = document.getElementById('signature-warning-continue');

  // Fill tab elements
  fillTabLink = document.getElementById('fill-tab-link');
  loadFillableTargetsBtn = document.getElementById('load-fillable-targets-btn');
  fillLoading = document.getElementById('fill-loading');
  fillPluginsTables = document.getElementById('fill-plugins-tables');
  fillNoTargets = document.getElementById('fill-no-targets');
  fillTargetsContent = document.getElementById('fill-targets-content');
  selectAllTargetsBtn = document.getElementById('select-all-targets');
  deselectAllTargetsBtn = document.getElementById('deselect-all-targets');
  startFillProcessBtn = document.getElementById('start-fill-process');
  fillProgressContainer = document.getElementById('fill-progress-container');
  fillProgressContent = document.getElementById('fill-progress-content');

  // Bundle display
  bundleTitle = document.getElementById('bundle-title');
  manifestDetails = document.getElementById('manifest-details');
}

// --- VIEW AND UI LOGIC ---
function showView(viewId) {
  // Get the OPAT view element
  const opatView = document.getElementById('opat-view');
  
  // Hide main content views
  [welcomeScreen, bundleView, createBundleForm].forEach(view => {
    view.classList.toggle('hidden', view.id !== viewId);
  });
  
  // Handle OPAT view separately since it's not in the main views array
  if (opatView) {
    opatView.classList.toggle('hidden', viewId !== 'opat-view');
  }
  
  // Also hide all category home screens when showing main content
  const categoryHomeScreens = [
    'libplugin-home', 'opat-home', 'libconstants-home', 'serif-home'
  ];
  
  categoryHomeScreens.forEach(screenId => {
    const screen = document.getElementById(screenId);
    if (screen) {
      screen.classList.add('hidden');
    }
  });
  
  // Show the appropriate category view if we're showing bundle-view or other content
  if (viewId === 'bundle-view') {
    const libpluginView = document.getElementById('libplugin-view');
    if (libpluginView) {
      libpluginView.classList.remove('hidden');
    }
  } else if (viewId === 'opat-view') {
    // Ensure OPAT view is visible and properly initialized
    if (opatView) {
      opatView.classList.remove('hidden');
      console.log('[DOM_MANAGER] OPAT view shown successfully');
    } else {
      console.error('[DOM_MANAGER] OPAT view element not found!');
    }
  }
}

function switchTab(tabId) {
  tabPanes.forEach(pane => {
    pane.classList.toggle('active', pane.id === tabId);
  });
  tabLinks.forEach(link => {
    link.classList.toggle('active', link.dataset.tab === tabId);
  });
}

function showSpinner() {
  spinner.classList.remove('hidden');
}

function hideSpinner() {
  spinner.classList.add('hidden');
}

function showModal(title, message, type = 'info') {
  modalTitle.textContent = title;
  modalMessage.innerHTML = message; // Use innerHTML to allow for formatted messages
  modal.classList.remove('hidden');
}

function hideModal() {
  modal.classList.add('hidden');
}

// Export DOM management functions and elements
module.exports = {
  // Initialization
  initializeDOMElements,
  
  // View management
  showView,
  switchTab,
  showSpinner,
  hideSpinner,
  showModal,
  hideModal,
  
  // DOM element getters (for other modules to access)
  getElements: () => ({
    welcomeScreen,
    bundleView,
    createBundleForm,
    openBundleBtn,
    createBundleBtn,
    signBundleBtn,
    validateBundleBtn,
    clearBundleBtn,
    saveMetadataBtn,
    saveOptionsModal,
    overwriteBundleBtn,
    saveAsNewBtn,
    signatureWarningModal,
    signatureWarningCancel,
    signatureWarningContinue,
    fillTabLink,
    loadFillableTargetsBtn,
    fillLoading,
    fillPluginsTables,
    fillNoTargets,
    fillTargetsContent,
    selectAllTargetsBtn,
    deselectAllTargetsBtn,
    startFillProcessBtn,
    fillProgressContainer,
    fillProgressContent,
    bundleTitle,
    manifestDetails,
    pluginsList,
    validationResults,
    tabLinks,
    tabPanes,
    validationTabLink,
    modal,
    modalTitle,
    modalMessage,
    modalCloseBtn,
    spinner,
    fillModal,
    closeFillModalButton,
    fillModalTitle,
    fillModalBody,
    fillTargetsList,
    startFillButton,
    fillProgressView,
    fillProgressList
  })
};
