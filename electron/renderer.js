const { ipcRenderer } = require('electron');
const path = require('path');

// --- STATE ---
let currentBundle = null;

// --- DOM ELEMENTS (will be initialized in DOMContentLoaded) ---
let welcomeScreen, bundleView, createBundleForm;
let openBundleBtn, createBundleBtn;
let signBundleBtn, validateBundleBtn, clearBundleBtn, saveMetadataBtn;
let saveOptionsModal, overwriteBundleBtn, saveAsNewBtn;
let signatureWarningModal, signatureWarningCancel, signatureWarningContinue;
let fillTabLink, loadFillableTargetsBtn, fillLoading, fillPluginsTables, fillNoTargets, fillTargetsContent;
let selectAllTargetsBtn, deselectAllTargetsBtn, startFillProcessBtn, fillProgressContainer, fillProgressContent;
let bundleTitle, manifestDetails;
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

let currentBundlePath = null;
let hasUnsavedChanges = false;
let originalMetadata = {};

let pendingOperation = null; // Store the operation to execute after warning confirmation

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', async () => {
  // Initialize DOM elements
  initializeDOMElements();
  
  // Initialize OPAT tab navigation
  initializeOPATTabs();

  // Initialize OPAT UI elements
  initializeOPATElements();

  // Initialize home screen - set home as default active category
  const homeCategory = document.querySelector('.category-item[data-category="home"]');
  const secondarySidebar = document.getElementById('secondary-sidebar');
  
  if (homeCategory) {
    homeCategory.classList.add('active');
    showCategoryHomeScreen('home');
    
    // Hide secondary sidebar on initial load since we start with home
    if (secondarySidebar) {
      secondarySidebar.style.display = 'none';
    }
  }
  
  // Set initial view
  showView('welcome-screen');

  // Set initial theme
  const isDarkMode = await ipcRenderer.invoke('get-dark-mode');
  document.body.classList.toggle('dark-mode', isDarkMode);

  // Setup event listeners
  setupEventListeners();
});

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

// --- EVENT LISTENERS ---
function setupEventListeners() {
  // Theme updates
  ipcRenderer.on('theme-updated', (event, { shouldUseDarkColors }) => {
    document.body.classList.toggle('dark-mode', shouldUseDarkColors);
  });

  // Sidebar navigation
  openBundleBtn.addEventListener('click', handleOpenBundle);
  createBundleBtn.addEventListener('click', () => {
    // TODO: Replace with modal
    showView('create-bundle-form');
    showModal('Not Implemented', 'The create bundle form will be moved to a modal dialog.');
  });

  // Tab navigation
  tabLinks.forEach(link => {
    link.addEventListener('click', () => switchTab(link.dataset.tab));
  });

  // Modal close button
  modalCloseBtn.addEventListener('click', hideModal);

  // Bundle actions
  signBundleBtn.addEventListener('click', handleSignBundle);
  validateBundleBtn.addEventListener('click', handleValidateBundle);
  clearBundleBtn.addEventListener('click', handleClearBundle);
  saveMetadataBtn.addEventListener('click', showSaveOptionsModal);
  overwriteBundleBtn.addEventListener('click', () => handleSaveMetadata(false));
  saveAsNewBtn.addEventListener('click', () => handleSaveMetadata(true));
  
  // Signature warning modal event listeners
  signatureWarningCancel.addEventListener('click', () => {
    signatureWarningModal.classList.add('hidden');
    pendingOperation = null;
  });
  
  signatureWarningContinue.addEventListener('click', () => {
    signatureWarningModal.classList.add('hidden');
    if (pendingOperation) {
      pendingOperation();
      pendingOperation = null;
    }
  });
  
  // Load fillable targets button
  loadFillableTargetsBtn.addEventListener('click', async () => {
    await loadFillableTargets();
  });
  // Load fillable targets for the Fill tab
  async function loadFillableTargets() {
    console.log('loadFillableTargets called, currentBundlePath:', currentBundlePath);
    
    // Check if required DOM elements exist
    if (!fillNoTargets || !fillTargetsContent || !fillLoading) {
      console.error('Fill tab DOM elements not found');
      showModal('Error', 'Fill tab interface not properly initialized.');
      return;
    }
    
    if (!currentBundlePath) {
      console.log('No bundle path, showing no targets message');
      hideAllFillStates();
      fillNoTargets.classList.remove('hidden');
      return;
    }
    
    try {
      // Show loading state
      hideAllFillStates();
      fillLoading.classList.remove('hidden');
      loadFillableTargetsBtn.disabled = true;
      
      console.log('Calling get-fillable-targets...');
      const result = await ipcRenderer.invoke('get-fillable-targets', currentBundlePath);
      console.log('get-fillable-targets result:', result);

      if (!result.success) {
        console.log('get-fillable-targets failed:', result.error);
        hideAllFillStates();
        showModal('Error', `Failed to load fillable targets: ${result.error}`);
        return;
      }

      const targets = result.data;
      console.log('Fillable targets:', targets);
      
      hideAllFillStates();
      
      if (!targets || Object.keys(targets).length === 0) {
        console.log('No fillable targets found');
        fillNoTargets.classList.remove('hidden');
      } else {
        console.log('Populating fillable targets table');
        fillTargetsContent.classList.remove('hidden');
        populateFillTargetsTable(targets);
        // Hide the Load Available Targets button after successful load
        loadFillableTargetsBtn.style.display = 'none';
      }
    } catch (error) {
      console.error('Error in loadFillableTargets:', error);
      hideAllFillStates();
      showModal('Error', `Error loading fillable targets: ${error.message}`);
    } finally {
      loadFillableTargetsBtn.disabled = false;
    }
  }
  
  // Helper function to hide all fill tab states
  function hideAllFillStates() {
    fillLoading.classList.add('hidden');
    fillNoTargets.classList.add('hidden');
    fillTargetsContent.classList.add('hidden');
  }



  // Check if bundle is signed and show warning before bundle-modifying operations
  function checkSignatureAndWarn(operation, operationName = 'operation') {
    const isSigned = currentBundle && 
                    currentBundle.report && 
                    currentBundle.report.signature && 
                    currentBundle.report.signature.status && 
                    ['TRUSTED', 'UNTRUSTED'].includes(currentBundle.report.signature.status);
    
    if (isSigned) {
      pendingOperation = operation;
      signatureWarningModal.classList.remove('hidden');
      return false; // Don't execute operation immediately
    } else {
      operation();
      return true; // Operation executed
    }
  }

  // Info Modal functionality
  const infoBtn = document.getElementById('info-btn');
  const infoModal = document.getElementById('info-modal');
  const infoTabLinks = document.querySelectorAll('.info-tab-link');
  const infoTabPanes = document.querySelectorAll('.info-tab-pane');
  const githubLink = document.getElementById('github-link');

  // Show info modal
  infoBtn.addEventListener('click', () => {
    infoModal.classList.remove('hidden');
  });

  // Hide info modal - make it globally accessible
  window.hideInfoModal = function() {
    infoModal.classList.add('hidden');
  };

  // Tab switching functionality
  infoTabLinks.forEach(tabLink => {
    tabLink.addEventListener('click', () => {
      const targetTab = tabLink.getAttribute('data-tab');
      
      // Remove active class from all tabs and panes
      infoTabLinks.forEach(link => link.classList.remove('active'));
      infoTabPanes.forEach(pane => pane.classList.remove('active'));
      
      // Add active class to clicked tab and corresponding pane
      tabLink.classList.add('active');
      document.getElementById(targetTab).classList.add('active');
    });
  });

  // GitHub link functionality
  githubLink.addEventListener('click', (e) => {
    e.preventDefault();
    // You can update this URL to the actual GitHub repository
    const { ipcRenderer } = require('electron');
    ipcRenderer.invoke('open-external', 'https://github.com/tboudreaux/4DSTAR');
  });

  // Two-Tiered Sidebar functionality
  const categoryItems = document.querySelectorAll('.category-item');
  const sidebarContents = document.querySelectorAll('.sidebar-content');

  // Category switching functionality
  categoryItems.forEach(categoryItem => {
    categoryItem.addEventListener('click', () => {
      const selectedCategory = categoryItem.getAttribute('data-category');
      const secondarySidebar = document.getElementById('secondary-sidebar');
      
      // Remove active class from all category items
      categoryItems.forEach(item => item.classList.remove('active'));
      
      // Add active class to clicked category
      categoryItem.classList.add('active');
      
      // Hide all sidebar contents
      sidebarContents.forEach(content => content.classList.add('hidden'));
      
      // Show/hide secondary sidebar based on category
      if (selectedCategory === 'home') {
        // Hide the entire secondary sidebar on home screen
        if (secondarySidebar) {
          secondarySidebar.style.display = 'none';
        }
      } else {
        // Show secondary sidebar and its content for other categories
        if (secondarySidebar) {
          secondarySidebar.style.display = 'flex';
        }
        const selectedContent = document.querySelector(`.sidebar-content[data-category="${selectedCategory}"]`);
        if (selectedContent) {
          selectedContent.classList.remove('hidden');
        }
      }
      
      // Show appropriate home screen
      showCategoryHomeScreen(selectedCategory);
    });
  });



  // Update welcome screen based on selected category
  function updateWelcomeScreen(category) {
    const welcomeTitle = document.querySelector('#welcome-screen h1');
    const welcomeMessage = document.querySelector('#welcome-screen p');
    
    const categoryTitles = {
      'libplugin': 'Welcome to 4DSTAR Bundle Manager',
      'libconstants': 'Welcome to 4DSTAR Constants',
      'opat': 'Welcome to OPAT Core',
      'serif': 'Welcome to SERiF Libraries'
    };
    
    const categoryMessages = {
      'libplugin': 'Open or create a bundle to get started.',
      'libconstants': 'Constants tools coming soon...',
      'opat': 'OPAT tools coming soon...',
      'serif': 'SERiF tools coming soon...'
    };
    
    if (welcomeTitle) welcomeTitle.textContent = categoryTitles[category] || 'Welcome to 4DSTAR';
    if (welcomeMessage) welcomeMessage.textContent = categoryMessages[category] || 'Select a category to get started.';
  }

  // Old modal code removed - now using tab-based interface

  // Create modern table-based interface for fillable targets
  function populateFillTargetsTable(plugins) {
    fillPluginsTables.innerHTML = '';
    
    for (const [pluginName, targets] of Object.entries(plugins)) {
      if (targets.length > 0) {
        // Create plugin table container
        const pluginTable = document.createElement('div');
        pluginTable.className = 'fill-plugin-table';
        
        // Plugin header
        const pluginHeader = document.createElement('div');
        pluginHeader.className = 'fill-plugin-header';
        pluginHeader.textContent = `${pluginName} (${targets.length} target${targets.length > 1 ? 's' : ''})`;
        pluginTable.appendChild(pluginHeader);
        
        // Create table
        const table = document.createElement('table');
        table.className = 'fill-targets-table';
        
        // Table header
        const thead = document.createElement('thead');
        thead.innerHTML = `
          <tr>
            <th style="width: 50px;">
              <input type="checkbox" class="plugin-select-all" data-plugin="${pluginName}" checked>
            </th>
            <th>Target Platform</th>
            <th>Architecture</th>
            <th>Type</th>
            <th>Compiler</th>
          </tr>
        `;
        table.appendChild(thead);
        
        // Table body
        const tbody = document.createElement('tbody');
        targets.forEach(target => {
          const row = document.createElement('tr');
          row.innerHTML = `
            <td>
              <input type="checkbox" class="fill-target-checkbox" 
                     data-plugin="${pluginName}" 
                     data-target='${JSON.stringify(target)}' 
                     checked>
            </td>
            <td><strong>${target.triplet}</strong></td>
            <td>${target.arch}</td>
            <td><span class="target-type ${target.type}">${target.type}</span></td>
            <td>${target.type === 'docker' ? 'GCC' : (target.details?.compiler || 'N/A')} ${target.details?.compiler_version || ''}</td>
          `;
          tbody.appendChild(row);
        });
        table.appendChild(tbody);
        
        pluginTable.appendChild(table);
        fillPluginsTables.appendChild(pluginTable);
      }
    }
    
    // Add event listeners for select all functionality
    setupFillTargetEventListeners();
  }

  // Setup event listeners for Fill tab functionality
  function setupFillTargetEventListeners() {
    // Plugin-level select all checkboxes
    document.querySelectorAll('.plugin-select-all').forEach(checkbox => {
      checkbox.addEventListener('change', (e) => {
        const pluginName = e.target.dataset.plugin;
        const pluginCheckboxes = document.querySelectorAll(`.fill-target-checkbox[data-plugin="${pluginName}"]`);
        pluginCheckboxes.forEach(cb => cb.checked = e.target.checked);
      });
    });

    // Global select/deselect all buttons
    selectAllTargetsBtn.addEventListener('click', () => {
      document.querySelectorAll('.fill-target-checkbox, .plugin-select-all').forEach(cb => cb.checked = true);
    });

    deselectAllTargetsBtn.addEventListener('click', () => {
      document.querySelectorAll('.fill-target-checkbox, .plugin-select-all').forEach(cb => cb.checked = false);
    });

    // Start fill process button
    startFillProcessBtn.addEventListener('click', async () => {
      const selectedTargets = {};
      const checkboxes = document.querySelectorAll('.fill-target-checkbox:checked');

      if (checkboxes.length === 0) {
        showModal('Info', 'No targets selected to fill.');
        return;
      }

      checkboxes.forEach(cb => {
        const pluginName = cb.dataset.plugin;
        const target = JSON.parse(cb.dataset.target);
        if (!selectedTargets[pluginName]) {
          selectedTargets[pluginName] = [];
        }
        selectedTargets[pluginName].push(target);
      });

      // Check for signature and warn before starting fill process
      checkSignatureAndWarn(async () => {
        // Hide target selection and show progress
        fillTargetsContent.classList.add('hidden');
        fillProgressContainer.classList.remove('hidden');
        populateFillProgress(selectedTargets);

        const result = await ipcRenderer.invoke('fill-bundle', { 
          bundlePath: currentBundlePath, 
          targetsToBuild: selectedTargets 
        });

        if (!result.success) {
          const errorItem = document.createElement('div');
          errorItem.className = 'progress-item';
          errorItem.innerHTML = `
            <span class="progress-status failure">Error</span>
            <span>Fill process failed: ${result.error}</span>
          `;
          fillProgressContent.appendChild(errorItem);
        }
      }, 'fill bundle');
    });
  }

  // Create progress display for fill process
  function populateFillProgress(selectedTargets) {
    fillProgressContent.innerHTML = '';
    
    for (const [pluginName, targets] of Object.entries(selectedTargets)) {
      targets.forEach(target => {
        const progressItem = document.createElement('div');
        progressItem.className = 'progress-item';
        progressItem.id = `progress-${pluginName}-${target.triplet}`;
        progressItem.innerHTML = `
          <span class="progress-status building">Building</span>
          <span>${pluginName} - ${target.triplet}</span>
        `;
        fillProgressContent.appendChild(progressItem);
      });
    }
  }

  // Handle progress updates from backend
  ipcRenderer.on('fill-bundle-progress', (event, progress) => {
    if (typeof progress === 'object' && progress.status) {
      const { status, plugin, target } = progress;
      const progressItem = document.getElementById(`progress-${plugin}-${target}`);
      if (progressItem) {
        const statusSpan = progressItem.querySelector('.progress-status');
        statusSpan.className = `progress-status ${status}`;
        statusSpan.textContent = status.charAt(0).toUpperCase() + status.slice(1);
      }
    }
  });
}

// --- VIEW AND UI LOGIC ---
function showView(viewId) {
  [welcomeScreen, bundleView, createBundleForm].forEach(view => {
    view.classList.toggle('hidden', view.id !== viewId);
  });
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

// --- BUNDLE ACTIONS HANDLERS ---
async function handleOpenBundle() {
  const bundlePath = await ipcRenderer.invoke('select-file');
  if (!bundlePath) return;

  // Small delay to ensure file dialog closes properly
  await new Promise(resolve => setTimeout(resolve, 100));

  showSpinner();
  showModal('Opening...', `Opening bundle: ${path.basename(bundlePath)}`);
  const result = await ipcRenderer.invoke('open-bundle', bundlePath);
  hideSpinner();

  if (result.success) {
    currentBundle = result;
    currentBundlePath = bundlePath;
    displayBundleInfo(result.report);
    showView('bundle-view');
    hideModal();
  } else {
    showModal('Error Opening Bundle', `Failed to open bundle: ${result ? result.error : 'Unknown error'}`);
  }
}

async function handleSignBundle() {
  if (!currentBundlePath) return;

  showSpinner();
  const signResult = await ipcRenderer.invoke('sign-bundle', currentBundlePath);
  hideSpinner();

  if (signResult.success) {
    showModal('Success', 'Bundle signed successfully. Reloading...');
    await reloadCurrentBundle();
    hideModal();
  } else {
    showModal('Sign Error', `Failed to sign bundle: ${signResult.error}`);
  }
}

async function handleValidateBundle() {
  if (!currentBundlePath) return;

  showSpinner();
  const result = await ipcRenderer.invoke('validate-bundle', currentBundlePath);
  hideSpinner();

  if (result.success) {
    // With the new JSON architecture, validation data is directly in result
    const errors = result.errors || [];
    const warnings = result.warnings || [];
    const validationIssues = errors.concat(warnings);
    
    if (validationIssues.length > 0) {
      validationResults.textContent = validationIssues.join('\n');
      validationTabLink.classList.remove('hidden');
    } else {
      validationResults.textContent = 'Bundle is valid.';
      validationTabLink.classList.add('hidden');
    }
    
    // Switch to the validation tab to show the results
    switchTab('validation-tab');
    
    // Show summary in modal
    const summary = result.summary || { errors: errors.length, warnings: warnings.length };
    const message = `Validation finished with ${summary.errors} errors and ${summary.warnings} warnings.`;
    showModal('Validation Complete', message);

  } else {
    showModal('Validation Error', `Failed to validate bundle: ${result.error}`);
  }
}

async function handleClearBundle() {
  if (!currentBundlePath) return;

  showSpinner();
  const result = await ipcRenderer.invoke('clear-bundle', currentBundlePath);
  hideSpinner();

  if (result.success) {
    showModal('Success', 'All binaries have been cleared. Reloading...');
    await reloadCurrentBundle();
    hideModal();
  } else {
    showModal('Clear Error', `Failed to clear binaries: ${result.error}`);
  }
}

async function handleFillBundle() {
  if (!currentBundle) return showModal('Action Canceled', 'Please open a bundle first.');

  showSpinner();
  showModal('Filling Bundle...', 'Adding local binaries to bundle.');
  const result = await ipcRenderer.invoke('fill-bundle', currentBundle.bundlePath);
  hideSpinner();

  if (result.success) {
    showModal('Success', 'Binaries filled successfully. Reloading...');
    await reloadCurrentBundle();
    hideModal();
  } else {
    showModal('Fill Error', `Failed to fill bundle: ${result.error}`);
  }
}

// --- DATA DISPLAY ---
async function reloadCurrentBundle() {
  if (!currentBundle) return;
  const reloadResult = await ipcRenderer.invoke('open-bundle', currentBundle.bundlePath);
  if (reloadResult.success) {
    currentBundle = reloadResult;
    displayBundleInfo(reloadResult.report);
  } else {
    showModal('Reload Error', `Failed to reload bundle details: ${reloadResult.error}`);
  }
}

function displayBundleInfo(report) {
  if (!report) {
    showModal('Display Error', 'Could not load bundle information.');
    return;
  }

  const { manifest, signature, validation, plugins } = report;

  // Store original metadata for comparison
  originalMetadata = {
    bundleVersion: manifest.bundleVersion || '',
    bundleAuthor: manifest.bundleAuthor || '',
    bundleComment: manifest.bundleComment || ''
  };
  hasUnsavedChanges = false;
  updateSaveButtonVisibility();

  // Set bundle title
  bundleTitle.textContent = manifest.bundleName || 'Untitled Bundle';

  // --- Overview Tab ---
  const trustStatus = signature.status || 'UNSIGNED';
  const trustColorClass = {
    'TRUSTED': 'trusted',
    'UNTRUSTED': 'untrusted',
    'INVALID': 'untrusted',
    'TAMPERED': 'untrusted',
    'UNSIGNED': 'unsigned',
    'ERROR': 'untrusted',
    'UNSUPPORTED': 'warning'
  }[trustStatus] || 'unsigned';

  manifestDetails.innerHTML = `
    <div class="card">
        <div class="card-header">
            <h3>Trust Status</h3>
            <div class="trust-indicator-container">
                <div class="trust-indicator ${trustColorClass}"></div>
                <span>${trustStatus}</span>
            </div>
        </div>
    </div>
    <div class="card">
        <div class="card-header"><h3>Manifest Details</h3></div>
        <div class="card-content">
            ${createEditableField('Version', 'bundleVersion', manifest.bundleVersion || 'N/A')}
            ${createEditableField('Author', 'bundleAuthor', manifest.bundleAuthor || 'N/A')}
            <p><strong>Bundled On:</strong> ${manifest.bundledOn || 'N/A'}</p>
            ${createEditableField('Comment', 'bundleComment', manifest.bundleComment || 'N/A')}
            ${manifest.bundleAuthorKeyFingerprint ? `<p><strong>Author Key:</strong> ${manifest.bundleAuthorKeyFingerprint}</p>` : ''}
            ${manifest.bundleSignature ? `<p><strong>Signature:</strong> <span class="signature">${manifest.bundleSignature}</span></p>` : ''}
        </div>
    </div>
  `;

  // Add event listeners for edit functionality
  setupEditableFieldListeners();

  // --- Plugins Tab ---
  pluginsList.innerHTML = '';
  if (plugins && Object.keys(plugins).length > 0) {
    Object.entries(plugins).forEach(([pluginName, pluginData]) => {
      const binariesInfo = pluginData.binaries.map(b => {
        const compatClass = b.is_compatible ? 'compatible' : 'incompatible';
        const compatText = b.is_compatible ? 'Compatible' : 'Incompatible';
        const platformTriplet = b.platform && b.platform.triplet ? `(${b.platform.triplet})` : '';
        return `<li class="binary-info ${compatClass}"><strong>${b.path}</strong> ${platformTriplet} - ${compatText}</li>`;
      }).join('');

      const pluginCard = document.createElement('div');
      pluginCard.className = 'card';
      pluginCard.innerHTML = `
        <div class="card-header"><h4>${pluginName}</h4></div>
        <div class="card-content">
            <p><strong>Source:</strong> ${pluginData.sdist_path}</p>
            <p><strong>Binaries:</strong></p>
            <ul>${binariesInfo.length > 0 ? binariesInfo : '<li>No binaries found.</li>'}</ul>
        </div>
      `;
      pluginsList.appendChild(pluginCard);
    });
  } else {
    pluginsList.innerHTML = '<div class="card"><div class="card-content"><p>No plugins found in this bundle.</p></div></div>';
  }

  // --- Validation Tab ---
  const validationIssues = validation.errors.concat(validation.warnings);
  if (validationIssues.length > 0) {
    validationResults.textContent = validationIssues.join('\n');
    validationTabLink.classList.remove('hidden');
  } else {
    validationResults.textContent = 'Bundle is valid.';
    validationTabLink.classList.add('hidden');
  }
  
  // Temporarily disabled to fix bundle opening hang
  // TODO: Re-enable after debugging fillable targets functionality
  // loadFillableTargets().catch(error => {
  //   console.error('Failed to load fillable targets:', error);
  //   // Don't block bundle opening if fill targets fail to load
  // });
  
  // Reset to overview tab by default
  switchTab('overview-tab');
}

// Helper function to create editable fields with pencil icons
function createEditableField(label, fieldName, value) {
  const displayValue = value === 'N/A' ? '' : value;
  return `
    <p class="editable-field">
      <strong>${label}:</strong> 
      <span class="field-display" data-field="${fieldName}">${value}</span>
      <span class="field-edit hidden" data-field="${fieldName}">
        <input type="text" class="field-input" data-field="${fieldName}" value="${displayValue}">
      </span>
      <button class="edit-icon" data-field="${fieldName}" title="Edit ${label}">✏️</button>
    </p>
  `;
}

// Setup event listeners for editable fields
function setupEditableFieldListeners() {
  const editIcons = document.querySelectorAll('.edit-icon');
  const fieldInputs = document.querySelectorAll('.field-input');

  editIcons.forEach(icon => {
    icon.addEventListener('click', (e) => {
      const fieldName = e.target.dataset.field;
      toggleFieldEdit(fieldName, true);
    });
  });

  fieldInputs.forEach(input => {
    input.addEventListener('blur', (e) => {
      const fieldName = e.target.dataset.field;
      saveFieldEdit(fieldName);
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const fieldName = e.target.dataset.field;
        saveFieldEdit(fieldName);
      } else if (e.key === 'Escape') {
        const fieldName = e.target.dataset.field;
        cancelFieldEdit(fieldName);
      }
    });

    input.addEventListener('input', () => {
      checkForChanges();
    });
  });
}

// Toggle between display and edit mode for a field
function toggleFieldEdit(fieldName, editMode) {
  const displaySpan = document.querySelector(`.field-display[data-field="${fieldName}"]`);
  const editSpan = document.querySelector(`.field-edit[data-field="${fieldName}"]`);
  const input = document.querySelector(`.field-input[data-field="${fieldName}"]`);
  const icon = document.querySelector(`.edit-icon[data-field="${fieldName}"]`);

  if (editMode) {
    displaySpan.classList.add('hidden');
    editSpan.classList.remove('hidden');
    icon.textContent = '✅';
    icon.title = 'Save';
    input.focus();
    input.select();
  } else {
    displaySpan.classList.remove('hidden');
    editSpan.classList.add('hidden');
    icon.textContent = '✏️';
    icon.title = `Edit ${fieldName}`;
  }
}

// Save field edit and update display
function saveFieldEdit(fieldName) {
  const input = document.querySelector(`.field-input[data-field="${fieldName}"]`);
  const displaySpan = document.querySelector(`.field-display[data-field="${fieldName}"]`);
  
  const newValue = input.value.trim();
  const displayValue = newValue || 'N/A';
  
  displaySpan.textContent = displayValue;
  toggleFieldEdit(fieldName, false);
  checkForChanges();
}

// Cancel field edit and restore original value
function cancelFieldEdit(fieldName) {
  const input = document.querySelector(`.field-input[data-field="${fieldName}"]`);
  const originalValue = originalMetadata[fieldName] || '';
  
  input.value = originalValue;
  toggleFieldEdit(fieldName, false);
}

// Check if any fields have been modified
function checkForChanges() {
  const inputs = document.querySelectorAll('.field-input');
  let hasChanges = false;

  inputs.forEach(input => {
    const fieldName = input.dataset.field;
    const currentValue = input.value.trim();
    const originalValue = originalMetadata[fieldName] || '';
    
    if (currentValue !== originalValue) {
      hasChanges = true;
    }
  });

  hasUnsavedChanges = hasChanges;
  updateSaveButtonVisibility();
}

// Show/hide save button based on changes
function updateSaveButtonVisibility() {
  if (hasUnsavedChanges) {
    saveMetadataBtn.classList.remove('hidden');
  } else {
    saveMetadataBtn.classList.add('hidden');
  }
}

// Show save options modal
function showSaveOptionsModal() {
  if (!hasUnsavedChanges) {
    return;
  }
  
  // Check if bundle is signed and show warning banner
  const signatureWarningSection = document.getElementById('signature-warning-section');
  const isSigned = currentBundle && 
                  currentBundle.report && 
                  currentBundle.report.signature && 
                  currentBundle.report.signature.status && 
                  ['TRUSTED', 'UNTRUSTED'].includes(currentBundle.report.signature.status);
  
  if (isSigned) {
    signatureWarningSection.classList.remove('hidden');
  } else {
    signatureWarningSection.classList.add('hidden');
  }
  
  saveOptionsModal.classList.remove('hidden');
}

// Hide save options modal
function hideSaveOptionsModal() {
  saveOptionsModal.classList.add('hidden');
}

// Handle save metadata with option for save as new
async function handleSaveMetadata(saveAsNew = false) {
  if (!currentBundlePath || !hasUnsavedChanges) return;

  // Hide the modal first
  hideSaveOptionsModal();

  const inputs = document.querySelectorAll('.field-input');
  const updatedMetadata = {};

  inputs.forEach(input => {
    const fieldName = input.dataset.field;
    const value = input.value.trim();
    if (value !== originalMetadata[fieldName]) {
      // Convert camelCase to snake_case for backend
      const backendFieldName = fieldName.replace(/([A-Z])/g, '_$1').toLowerCase();
      updatedMetadata[backendFieldName] = value;
    }
  });

  if (Object.keys(updatedMetadata).length === 0) {
    hasUnsavedChanges = false;
    updateSaveButtonVisibility();
    return;
  }

  let targetPath = currentBundlePath;
  
  if (saveAsNew) {
    // Show file save dialog for new bundle
    const result = await ipcRenderer.invoke('show-save-dialog', {
      defaultPath: currentBundlePath.replace('.fbundle', '_edited.fbundle'),
      filters: [{ name: 'Bundle Files', extensions: ['fbundle'] }]
    });
    
    if (result.canceled) {
      return; // User canceled the save dialog
    }
    
    targetPath = result.filePath;
    
    // Copy the original bundle to the new location first
    try {
      await ipcRenderer.invoke('copy-file', {
        source: currentBundlePath,
        destination: targetPath
      });
    } catch (error) {
      showModal('Copy Error', `Failed to copy bundle: ${error.message}`);
      return;
    }
  }

  showSpinner();
  const result = await ipcRenderer.invoke('edit-bundle', {
    bundlePath: targetPath,
    updatedManifest: updatedMetadata
  });
  hideSpinner();

  if (result.success) {
    // Update original metadata to reflect saved changes
    Object.keys(updatedMetadata).forEach(backendKey => {
      const frontendKey = backendKey.replace(/_([a-z])/g, (match, letter) => letter.toUpperCase());
      originalMetadata[frontendKey] = updatedMetadata[backendKey];
    });
    
    hasUnsavedChanges = false;
    updateSaveButtonVisibility();
    
    if (saveAsNew) {
      showModal('Success', `New bundle created successfully at: ${targetPath}`);
      // Open the new bundle
      currentBundlePath = targetPath;
      await reloadCurrentBundle();
    } else {
      showModal('Success', 'Metadata updated successfully!');
      // Reload current bundle to reflect changes
      await reloadCurrentBundle();
    }
  } else {
    showModal('Save Error', `Failed to save metadata: ${result.error}`);
  }
}

// Helper function to reload current bundle
async function reloadCurrentBundle() {
  if (!currentBundlePath) return;
  
  const result = await ipcRenderer.invoke('open-bundle', currentBundlePath);
  if (result.success) {
    displayBundleInfo(result.report);
  }
}

// ===== OPAT FILE INSPECTOR LOGIC =====
// OPAT File Inspector variables
let currentOPATFile = null;
let opatFileInput, opatBrowseBtn, opatView, opatCloseBtn;
let opatHeaderInfo, opatAllTagsList, opatIndexSelector, opatTablesDisplay, opatTableDataContent;

// Helper function to hide all views
function hideAllViews() {
  const welcomeScreen = document.getElementById('welcome-screen');
  const libpluginHome = document.getElementById('libplugin-home');
  const opatHome = document.getElementById('opat-home');
  const libconstantsHome = document.getElementById('libconstants-home');
  const serifHome = document.getElementById('serif-home');
  const opatView = document.getElementById('opat-view');
  const libpluginView = document.getElementById('libplugin-view');

  if (welcomeScreen) welcomeScreen.classList.add('hidden');
  if (libpluginHome) libpluginHome.classList.add('hidden');
  if (opatHome) opatHome.classList.add('hidden');
  if (libconstantsHome) libconstantsHome.classList.add('hidden');
  if (serifHome) serifHome.classList.add('hidden');
  if (opatView) opatView.classList.add('hidden');
  if (libpluginView) libpluginView.classList.add('hidden');
}

// Show appropriate home screen based on selected category
function showCategoryHomeScreen(category) {
  hideAllViews();
  
  switch (category) {
    case 'home':
      const welcomeScreen = document.getElementById('welcome-screen');
      if (welcomeScreen) welcomeScreen.classList.remove('hidden');
      break;
    case 'libplugin':
      const libpluginHome = document.getElementById('libplugin-home');
      if (libpluginHome) libpluginHome.classList.remove('hidden');
      break;
    case 'opat':
      const opatHome = document.getElementById('opat-home');
      if (opatHome) opatHome.classList.remove('hidden');
      break;
    case 'libconstants':
      const libconstantsHome = document.getElementById('libconstants-home');
      if (libconstantsHome) libconstantsHome.classList.remove('hidden');
      break;
    case 'serif':
      const serifHome = document.getElementById('serif-home');
      if (serifHome) serifHome.classList.remove('hidden');
      break;
    default:
      const defaultWelcome = document.getElementById('welcome-screen');
      if (defaultWelcome) defaultWelcome.classList.remove('hidden');
  }
}

// Initialize OPAT UI elements in DOMContentLoaded
function initializeOPATElements() {
    opatFileInput = document.getElementById('opat-file-input');
    opatBrowseBtn = document.getElementById('opat-browse-btn');
    opatView = document.getElementById('opat-view');
    opatCloseBtn = document.getElementById('opat-close-btn');
    opatHeaderInfo = document.getElementById('opat-header-info');
    opatAllTagsList = document.getElementById('opat-all-tags-list');
    opatIndexSelector = document.getElementById('opat-index-selector');
    opatTablesDisplay = document.getElementById('opat-tables-display');
    opatTableDataContent = document.getElementById('opat-table-data-content');

    // Event listeners
    opatBrowseBtn.addEventListener('click', () => opatFileInput.click());
    opatFileInput.addEventListener('change', handleOPATFileSelection);
    opatIndexSelector.addEventListener('change', handleIndexVectorChange);
    opatCloseBtn.addEventListener('click', closeOPATFile);

    // Initialize OPAT tab navigation
    initializeOPATTabs();
    
    // Add window resize listener to update table heights
    window.updateTableHeights = function() {
        const newHeight = Math.max(300, window.innerHeight - 450);
        
        // Target the main table containers
        const containers = document.querySelectorAll('.opat-table-container');
        containers.forEach((container, index) => {
            container.style.setProperty('height', newHeight + 'px', 'important');
        });
        
        // Also target the scroll wrappers
        const scrollWrappers = document.querySelectorAll('.table-scroll-wrapper');
        scrollWrappers.forEach((wrapper, index) => {
            wrapper.style.setProperty('height', '100%', 'important');
        });
    };
    
    window.addEventListener('resize', () => {
        console.log('Window resize event fired');
        window.updateTableHeights();
    });
    
    // Also update on initial load and when tables are displayed
    setTimeout(window.updateTableHeights, 100);
}

function closeOPATFile() {
    currentOPATFile = null;
    opatFileInput.value = '';
    resetOPATViewerState();
    hideAllViews();
    document.getElementById('welcome-screen').classList.remove('hidden');
}

function resetOPATViewerState() {
    // Clear all OPAT content areas
    if (opatHeaderInfo) opatHeaderInfo.innerHTML = '';
    if (opatAllTagsList) opatAllTagsList.innerHTML = '';
    if (opatIndexSelector) {
        opatIndexSelector.innerHTML = '<option value="">-- Select an Index Vector --</option>';
    }
    if (opatTablesDisplay) opatTablesDisplay.innerHTML = '';
    if (opatTableDataContent) {
        opatTableDataContent.innerHTML = '<p class="opat-placeholder">Click on a table from the \'Data Card Explorer\' above to view its data here.</p>';
    }
    
    // Reset to File Information tab
    const opatTabLinks = document.querySelectorAll('#opat-view .tab-link');
    const opatTabPanes = document.querySelectorAll('#opat-tab-content .tab-pane');
    
    opatTabLinks.forEach(link => link.classList.remove('active'));
    opatTabPanes.forEach(pane => pane.classList.add('hidden'));
    
    // Activate File Information tab
    const fileInfoTab = document.querySelector('[data-tab="opat-overview-tab"]');
    const fileInfoPane = document.getElementById('opat-overview-tab');
    if (fileInfoTab) fileInfoTab.classList.add('active');
    if (fileInfoPane) fileInfoPane.classList.remove('hidden');
}

function initializeOPATTabs() {
    const opatTabLinks = document.querySelectorAll('#opat-view .tab-link');
    const opatTabPanes = document.querySelectorAll('#opat-tab-content .tab-pane');
    
    opatTabLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetTab = link.getAttribute('data-tab');
            
            // Remove active class from all tabs and panes
            opatTabLinks.forEach(l => l.classList.remove('active'));
            opatTabPanes.forEach(p => p.classList.add('hidden'));
            
            // Add active class to clicked tab and show corresponding pane
            link.classList.add('active');
            document.getElementById(targetTab).classList.remove('hidden');
        });
    });
}



async function handleOPATFileSelection(event) {
    const file = event.target.files[0];
    if (!file) return;

    try {
        // Reset viewer state before loading new file
        resetOPATViewerState();
        
        const arrayBuffer = await file.arrayBuffer();
        currentOPATFile = parseOPAT(arrayBuffer);
        
        displayOPATFileInfo();
        populateIndexSelector();
        
        // Show OPAT view and hide other views
        hideAllViews();
        opatView.classList.remove('hidden');
        
        // Update title with filename
        document.getElementById('opat-title').textContent = `OPAT File Inspector - ${file.name}`;
        
    } catch (error) {
        console.error('Error parsing OPAT file:', error);
        showModal('Error', `Failed to parse OPAT file: ${error.message}`);
    }
}

function displayOPATFileInfo() {
    if (!currentOPATFile) return;
    
    const header = currentOPATFile.header;
    opatHeaderInfo.innerHTML = `
        <div class="opat-info-section">
            <h4 class="opat-section-title">Header Information</h4>
            <div class="info-grid">
                <p><strong>Magic:</strong> ${header.magic}</p>
                <p><strong>Version:</strong> ${header.version}</p>
                <p><strong>Number of Tables:</strong> ${header.numTables}</p>
                <p><strong>Header Size:</strong> ${header.headerSize} bytes</p>
                <p><strong>Index Offset:</strong> ${header.indexOffset}</p>
                <p><strong>Creation Date:</strong> ${header.creationDate}</p>
                <p><strong>Source Info:</strong> ${header.sourceInfo}</p>
                <p><strong>Comment:</strong> ${header.comment || 'None'}</p>
                <p><strong>Number of Indices:</strong> ${header.numIndex}</p>
                <p><strong>Hash Precision:</strong> ${header.hashPrecision}</p>
            </div>
        </div>
    `;
    
    // Display all unique table tags
    displayAllTableTags();
}

function displayAllTableTags() {
    if (!currentOPATFile) return;
    
    const allTags = new Set();
    for (const card of currentOPATFile.cards.values()) {
        for (const tag of card.tableIndex.keys()) {
            allTags.add(tag);
        }
    }
    
    opatAllTagsList.innerHTML = '';
    Array.from(allTags).sort().forEach(tag => {
        const li = document.createElement('li');
        li.textContent = tag;
        opatAllTagsList.appendChild(li);
    });
}

function populateIndexSelector() {
    if (!currentOPATFile) return;
    
    opatIndexSelector.innerHTML = '<option value="">-- Select an index vector --</option>';
    
    for (const [key, entry] of currentOPATFile.cardCatalog.entries()) {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = `[${entry.index.join(', ')}]`;
        opatIndexSelector.appendChild(option);
    }
}

function handleIndexVectorChange() {
    const selectedKey = opatIndexSelector.value;
    if (!selectedKey || !currentOPATFile) {
        opatTablesDisplay.innerHTML = '';
        return;
    }
    
    const card = currentOPATFile.cards.get(selectedKey);
    if (!card) return;
    
    opatTablesDisplay.innerHTML = '';
    
    for (const [tag, tableEntry] of card.tableIndex.entries()) {
        const tableInfo = document.createElement('div');
        tableInfo.className = 'opat-table-info';
        tableInfo.innerHTML = `
            <div class="opat-table-tag">${tag}</div>
            <div class="opat-table-details">
                Rows: ${tableEntry.numRows}, Columns: ${tableEntry.numColumns}<br>
                Row Name: ${tableEntry.rowName}, Column Name: ${tableEntry.columnName}
            </div>
        `;
        
        tableInfo.addEventListener('click', () => {
            const table = card.tableData.get(tag);
            displayTableData(table, tag);
        });
        
        opatTablesDisplay.appendChild(tableInfo);
    }
}

function displayTableData(table, tag, showAll = false) {
    if (!table) {
        opatTableDataContent.innerHTML = '<p class="opat-placeholder">Table not found.</p>';
        return;
    }

    let html = `<div class="opat-table-title"><span class="opat-table-tag-highlight">${tag}</span> Table Data</div>`;
    html += `<p><strong>Dimensions:</strong> ${table.N_R} rows × ${table.N_C} columns × ${table.m_vsize} values per cell</p>`;
    
    if (table.N_R > 0 && table.N_C > 0) {
        if (table.m_vsize === 0 || table.data.length === 0) {
            html += '<p><strong>Note:</strong> This table has no data values (m_vsize = 0 or empty data array).</p>';
            html += '<p>The table structure exists but contains no numerical data to display.</p>';
        } else {
            // Add show all/show less toggle buttons
            if (table.N_R > 50) {
                html += '<div class="table-controls">';
                if (!showAll) {
                    html += `<button class="show-all-btn" onclick="displayTableData(currentOPATFile.cards.get('${opatIndexSelector.value}').tableData.get('${tag}'), '${tag}', true)">Show All ${table.N_R} Rows</button>`;
                } else {
                    html += `<button class="show-less-btn" onclick="displayTableData(currentOPATFile.cards.get('${opatIndexSelector.value}').tableData.get('${tag}'), '${tag}', false)">Show First 50 Rows</button>`;
                }
                html += '</div>';
            }
            
            html += '<div class="opat-table-container">';
            html += '<div class="table-scroll-wrapper">';
            html += '<table class="opat-data-table">';
            
            // Header row
            html += '<thead><tr><th class="corner-cell"></th>';
            for (let c = 0; c < table.N_C; c++) {
                html += `<th>${table.columnValues[c].toFixed(3)}</th>`;
            }
            html += '</tr></thead>';
            
            // Data rows
            html += '<tbody>';
            const rowsToShow = showAll ? table.N_R : Math.min(table.N_R, 50);
            for (let r = 0; r < rowsToShow; r++) {
                html += '<tr>';
                html += `<th class="row-header">${table.rowValues[r].toFixed(3)}</th>`;
                for (let c = 0; c < table.N_C; c++) {
                    try {
                        const value = table.getValue(r, c, 0); // Get first value in cell
                        html += `<td>${value.toFixed(6)}</td>`;
                    } catch (error) {
                        html += `<td>N/A</td>`;
                    }
                }
                html += '</tr>';
            }
            html += '</tbody>';
            html += '</table>';
            html += '</div></div>';
            
            if (table.N_R > 50 && !showAll) {
                html += `<p><em>Showing first 50 rows of ${table.N_R} total rows.</em></p>`;
            } else if (showAll && table.N_R > 50) {
                html += `<p><em>Showing all ${table.N_R} rows.</em></p>`;
            }
        }
    } else {
        html += '<p>No data to display.</p>';
    }
    
    opatTableDataContent.innerHTML = html;
    
    // Auto-switch to Data Explorer tab when displaying data
    const explorerTab = document.querySelector('[data-tab="opat-explorer-tab"]');
    if (explorerTab) {
        explorerTab.click();
    }
    
    // Update table heights after table is rendered
    setTimeout(() => {
        if (window.updateTableHeights) {
            window.updateTableHeights();
        }
    }, 50);
}
