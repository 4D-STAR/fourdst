// Event handlers module for the 4DSTAR Bundle Manager
// Extracted from renderer.js to centralize event listener setup and management

const { ipcRenderer } = require('electron');

// Import dependencies (these will be injected when integrated)
let stateManager, domManager, bundleOperations, fillWorkflow, uiComponents, opatHandler;

// --- EVENT LISTENERS SETUP ---
function setupEventListeners() {
  const elements = domManager.getElements();
  
  // Theme updates
  ipcRenderer.on('theme-updated', (event, { shouldUseDarkColors }) => {
    document.body.classList.toggle('dark-mode', shouldUseDarkColors);
  });

  // File association handlers
  ipcRenderer.on('open-bundle-file', async (event, filePath) => {
    console.log(`[RENDERER] Opening .fbundle file via association: ${filePath}`);
    try {
      // Switch to libplugin category if not already there
      const libpluginCategory = document.querySelector('.category-item[data-category="libplugin"]');
      if (libpluginCategory && !libpluginCategory.classList.contains('active')) {
        libpluginCategory.click();
      }
      
      // Open the bundle
      await bundleOperations.openBundleFromPath(filePath);
    } catch (error) {
      console.error('[RENDERER] Error opening bundle file:', error);
      domManager.showModal('File Open Error', `Failed to open bundle file: ${error.message}`);
    }
  });

  ipcRenderer.on('open-opat-file', async (event, filePath) => {
    console.log(`[RENDERER] Opening .opat file via association: ${filePath}`);
    try {
      // Switch to OPAT Core category
      const opatCategory = document.querySelector('.category-item[data-category="opat"]');
      if (opatCategory) {
        opatCategory.click();
      }
      
      // Wait a moment for category switching to complete
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Open the OPAT file using the OPAT handler
      if (opatHandler && opatHandler.openOpatFromPath) {
        await opatHandler.openOpatFromPath(filePath);
      } else {
        console.warn('[RENDERER] OPAT file opening not available');
        domManager.showModal('Error', 'OPAT file opening functionality is not available.');
      }
    } catch (error) {
      console.error('[RENDERER] Error opening OPAT file:', error);
      domManager.showModal('File Open Error', `Failed to open OPAT file: ${error.message}`);
    }
  });

  // Sidebar navigation
  elements.openBundleBtn.addEventListener('click', bundleOperations.handleOpenBundle);
  elements.createBundleBtn.addEventListener('click', () => {
    // TODO: Replace with modal
    domManager.showView('create-bundle-form');
    domManager.showModal('Not Implemented', 'The create bundle form will be moved to a modal dialog.');
  });

  // Tab navigation
  elements.tabLinks.forEach(link => {
    link.addEventListener('click', () => domManager.switchTab(link.dataset.tab));
  });

  // Modal close button
  elements.modalCloseBtn.addEventListener('click', domManager.hideModal);

  // Bundle actions
  elements.signBundleBtn.addEventListener('click', () => {
    checkSignatureAndWarn(bundleOperations.handleSignBundle, 'signing');
  });
  elements.validateBundleBtn.addEventListener('click', bundleOperations.handleValidateBundle);
  elements.clearBundleBtn.addEventListener('click', () => {
    checkSignatureAndWarn(bundleOperations.handleClearBundle, 'clearing binaries');
  });
  elements.saveMetadataBtn.addEventListener('click', uiComponents.showSaveOptionsModal);
  elements.overwriteBundleBtn.addEventListener('click', () => handleSaveMetadata(false));
  elements.saveAsNewBtn.addEventListener('click', () => handleSaveMetadata(true));
  
  // Signature warning modal event listeners
  elements.signatureWarningCancel.addEventListener('click', () => {
    elements.signatureWarningModal.classList.add('hidden');
    stateManager.clearPendingOperation();
  });
  
  elements.signatureWarningContinue.addEventListener('click', () => {
    elements.signatureWarningModal.classList.add('hidden');
    const pendingOperation = stateManager.getPendingOperation();
    if (pendingOperation) {
      pendingOperation();
      stateManager.clearPendingOperation();
    }
  });
  
  // Load fillable targets button
  elements.loadFillableTargetsBtn.addEventListener('click', async () => {
    await fillWorkflow.loadFillableTargets();
  });

  // Category navigation
  setupCategoryNavigation();
  
  // Info modal setup
  setupInfoModal();
}

// Check if bundle is signed and show warning before bundle-modifying operations
function checkSignatureAndWarn(operation, operationName = 'operation') {
  const currentBundle = stateManager.getCurrentBundle();
  const elements = domManager.getElements();
  
  if (currentBundle && 
      currentBundle.report && 
      currentBundle.report.signature && 
      currentBundle.report.signature.status && 
      ['TRUSTED', 'UNTRUSTED'].includes(currentBundle.report.signature.status)) {
    
    // Bundle is signed, show warning
    stateManager.setPendingOperation(operation);
    elements.signatureWarningModal.classList.remove('hidden');
  } else {
    // Bundle is not signed, proceed directly
    operation();
  }
}

// Setup category navigation
function setupCategoryNavigation() {
  const categoryItems = document.querySelectorAll('.category-item');
  const secondarySidebar = document.getElementById('secondary-sidebar');
  
  categoryItems.forEach(item => {
    item.addEventListener('click', () => {
      const category = item.dataset.category;
      
      // Update active states
      categoryItems.forEach(cat => cat.classList.remove('active'));
      item.classList.add('active');
      
      // Show/hide secondary sidebar based on category
      if (category === 'home') {
        if (secondarySidebar) {
          secondarySidebar.style.display = 'none';
        }
        showCategoryHomeScreen('home');
      } else {
        if (secondarySidebar) {
          secondarySidebar.style.display = 'block';
        }
        
        // Show appropriate sidebar content
        const sidebarContents = document.querySelectorAll('.sidebar-content');
        sidebarContents.forEach(content => {
          if (content.dataset.category === category) {
            content.classList.remove('hidden');
          } else {
            content.classList.add('hidden');
          }
        });
        
        // Show category home screen
        showCategoryHomeScreen(category);
      }
      
      // Update welcome screen
      updateWelcomeScreen(category);
    });
  });
}

// Update welcome screen based on selected category
function updateWelcomeScreen(category) {
  const welcomeTitles = {
    'home': 'Welcome to 4DSTAR',
    'libplugin': 'Welcome to libplugin',
    'libconstants': 'Welcome to libconstants',
    'opat': 'Welcome to OPAT Core',
    'serif': 'Welcome to SERiF Libraries'
  };
  
  const welcomeMessages = {
    'home': 'Select a category from the sidebar to get started.',
    'libplugin': 'Bundle management tools for 4DSTAR plugins.',
    'libconstants': 'Constants tools coming soon...',
    'opat': 'OPAT tools coming soon...',
    'serif': 'SERiF tools coming soon...'
  };
  
  const welcomeTitle = document.querySelector('.welcome-title');
  const welcomeMessage = document.querySelector('.welcome-message');
  
  if (welcomeTitle) welcomeTitle.textContent = welcomeTitles[category] || welcomeTitles['home'];
  if (welcomeMessage) welcomeMessage.textContent = welcomeMessages[category] || welcomeMessages['home'];
}

// Show appropriate home screen based on selected category
function showCategoryHomeScreen(category) {
  const views = [
    'welcome-screen', 'libplugin-home', 'opat-home', 
    'libconstants-home', 'serif-home', 'opat-view', 'libplugin-view',
    'bundle-view', 'create-bundle-form'
  ];
  
  // Hide all views
  views.forEach(viewId => {
    const view = document.getElementById(viewId);
    if (view) view.classList.add('hidden');
  });
  
  // Show appropriate view
  const viewMap = {
    'home': 'welcome-screen',
    'libplugin': 'libplugin-home',
    'opat': 'opat-home',
    'libconstants': 'libconstants-home',
    'serif': 'serif-home'
  };
  
  const viewId = viewMap[category] || 'welcome-screen';
  const view = document.getElementById(viewId);
  if (view) view.classList.remove('hidden');
}

// Setup info modal
function setupInfoModal() {
  const infoBtn = document.getElementById('info-btn');
  const infoModal = document.getElementById('info-modal');
  const closeInfoModalBtn = document.getElementById('close-info-modal');
  const infoTabLinks = document.querySelectorAll('.info-tab-link');
  const infoTabPanes = document.querySelectorAll('.info-tab-pane');
  
  if (infoBtn) {
    infoBtn.addEventListener('click', () => {
      if (infoModal) infoModal.classList.remove('hidden');
    });
  }
  
  if (closeInfoModalBtn) {
    closeInfoModalBtn.addEventListener('click', hideInfoModal);
  }
  
  // Info tab navigation
  infoTabLinks.forEach(link => {
    link.addEventListener('click', async (e) => {
      e.preventDefault();
      const targetTab = link.dataset.tab;
      
      // Update active states
      infoTabLinks.forEach(l => l.classList.remove('active'));
      infoTabPanes.forEach(p => p.classList.remove('active'));
      
      link.classList.add('active');
      const targetPane = document.getElementById(targetTab);
      if (targetPane) targetPane.classList.add('active');
      
      // Load license content when license tab is clicked
      if (targetTab === 'license-info-tab') {
        console.log('[FRONTEND] License tab clicked, loading content...');
        await loadLicenseContent();
      } else {
        console.log(`[FRONTEND] Tab clicked: ${targetTab}`);
      }
    });
  });
  
  // External link handling
  const githubLink = document.getElementById('github-link');
  if (githubLink) {
    githubLink.addEventListener('click', (e) => {
      e.preventDefault();
      // Get the URL from the href attribute instead of hardcoding
      const url = githubLink.getAttribute('href');
      ipcRenderer.invoke('open-external-url', url);
    });
  }
}

// Hide info modal - make it globally accessible
function hideInfoModal() {
  const infoModal = document.getElementById('info-modal');
  if (infoModal) infoModal.classList.add('hidden');
}

// Load license content from LICENSE.txt file
async function loadLicenseContent() {
  console.log('[FRONTEND] loadLicenseContent() called');
  const licenseTextarea = document.querySelector('.license-text');
  console.log('[FRONTEND] License textarea found:', licenseTextarea);
  if (!licenseTextarea) {
    console.error('[FRONTEND] License textarea not found!');
    return;
  }
  
  // Don't reload if already loaded (not placeholder)
  if (licenseTextarea.value && !licenseTextarea.value.includes('GPL v3 license text will be pasted here')) {
    return;
  }
  
  try {
    console.log('[FRONTEND] Requesting license content...');
    const result = await ipcRenderer.invoke('read-license');
    console.log('[FRONTEND] License result:', result);
    
    if (result.success) {
      console.log(`[FRONTEND] License content length: ${result.content.length} characters`);
      console.log(`[FRONTEND] License starts with: "${result.content.substring(0, 100)}..."`);
      console.log(`[FRONTEND] License ends with: "...${result.content.substring(result.content.length - 100)}"`);
      
      licenseTextarea.value = result.content;
      licenseTextarea.placeholder = '';
      // Scroll to the top to show the beginning of the license
      licenseTextarea.scrollTop = 0;
    } else {
      licenseTextarea.value = result.content; // Fallback error message
      licenseTextarea.placeholder = '';
      console.error('Failed to load license:', result.error);
    }
  } catch (error) {
    console.error('Error loading license content:', error);
    licenseTextarea.value = 'Error loading license content. Please check that LICENSE.txt exists in the application directory.';
    licenseTextarea.placeholder = '';
  }
}

// Handle save metadata with option for save as new
async function handleSaveMetadata(saveAsNew = false) {
  const currentBundlePath = stateManager.getCurrentBundlePath();
  if (!currentBundlePath) return;
  
  const elements = domManager.getElements();
  
  // Collect updated metadata from form fields
  const inputs = document.querySelectorAll('.field-input');
  const updatedManifest = {};
  
  inputs.forEach(input => {
    const fieldName = input.dataset.field;
    const value = input.value.trim();
    if (value) {
      updatedManifest[fieldName] = value;
    }
  });
  
  let targetPath = currentBundlePath;
  
  if (saveAsNew) {
    // Show save dialog for new bundle
    const saveResult = await ipcRenderer.invoke('show-save-dialog', {
      filters: [{ name: 'Fbundle Archives', extensions: ['fbundle'] }],
      defaultPath: currentBundlePath.replace(/\.fbundle$/, '_modified.fbundle')
    });
    
    if (saveResult.canceled || !saveResult.filePath) {
      uiComponents.hideSaveOptionsModal();
      return;
    }
    
    targetPath = saveResult.filePath;
    
    // Copy original bundle to new location first
    try {
      const copyResult = await ipcRenderer.invoke('copy-file', {
        source: currentBundlePath,
        destination: targetPath
      });
      
      if (!copyResult.success) {
        domManager.showModal('Copy Error', `Failed to copy bundle: ${copyResult.error}`);
        uiComponents.hideSaveOptionsModal();
        return;
      }
    } catch (error) {
      domManager.showModal('Copy Error', `Failed to copy bundle: ${error.message}`);
      uiComponents.hideSaveOptionsModal();
      return;
    }
  }
  
  // Save metadata to target bundle
  domManager.showSpinner();
  const result = await ipcRenderer.invoke('edit-bundle', {
    bundlePath: targetPath,
    updatedManifest: updatedManifest
  });
  domManager.hideSpinner();
  
  if (result.success) {
    domManager.showModal('Success', 'Bundle metadata saved successfully. Reloading...');
    
    // Update current bundle path if we saved as new
    if (saveAsNew) {
      stateManager.setBundleState(stateManager.getCurrentBundle(), targetPath);
    }
    
    await bundleOperations.reloadCurrentBundle();
    uiComponents.hideSaveOptionsModal();
    domManager.hideModal();
  } else {
    domManager.showModal('Save Error', `Failed to save metadata: ${result.error}`);
  }
  
  uiComponents.hideSaveOptionsModal();
}

// Initialize dependencies (called when module is loaded)
function initializeDependencies(deps) {
  stateManager = deps.stateManager;
  domManager = deps.domManager;
  bundleOperations = deps.bundleOperations;
  fillWorkflow = deps.fillWorkflow;
  uiComponents = deps.uiComponents;
  opatHandler = deps.opatHandler;
}

module.exports = {
  initializeDependencies,
  setupEventListeners,
  checkSignatureAndWarn,
  setupCategoryNavigation,
  updateWelcomeScreen,
  showCategoryHomeScreen,
  setupInfoModal,
  hideInfoModal,
  handleSaveMetadata
};
