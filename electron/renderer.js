const { ipcRenderer } = require('electron');
const path = require('path');

// --- STATE ---
let currentBundle = null;

// --- DOM ELEMENTS ---
// Views
const welcomeScreen = document.getElementById('welcome-screen');
const bundleView = document.getElementById('bundle-view');
const createBundleForm = document.getElementById('create-bundle-form'); // This will be a modal later

// Sidebar buttons
const openBundleBtn = document.getElementById('open-bundle-btn');
const createBundleBtn = document.getElementById('create-bundle-btn');

// Bundle action buttons
const editBundleBtn = document.getElementById('edit-bundle-btn');
const signBundleBtn = document.getElementById('sign-bundle-btn');
const validateBundleBtn = document.getElementById('validate-bundle-btn');
const fillBundleBtn = document.getElementById('fill-bundle-btn');
const clearBundleBtn = document.getElementById('clear-bundle-btn');

// Bundle display
const bundleTitle = document.getElementById('bundle-title');
const manifestDetails = document.getElementById('manifest-details');
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

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', async () => {
  // Set initial view
  showView('welcome-screen');

  // Set initial theme
  const isDarkMode = await ipcRenderer.invoke('get-dark-mode');
  document.body.classList.toggle('dark-mode', isDarkMode);

  // Setup event listeners
  setupEventListeners();
});

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
  fillBundleBtn.addEventListener('click', async () => {
    if (!currentBundlePath) {
      showModal('Error', 'No bundle is currently open.');
      return;
    }
    showSpinner();
    const result = await ipcRenderer.invoke('get-fillable-targets', currentBundlePath);
    hideSpinner();

    if (!result.success) {
      showModal('Error', `Failed to get fillable targets: ${result.error}`);
      return;
    }

    const targets = result.data;
    if (Object.keys(targets).length === 0) {
      showModal('Info', 'The bundle is already full. No new targets to build.');
      return;
    }

    populateFillTargetsList(targets);
    fillModal.style.display = 'block';
  });

  closeFillModalButton.addEventListener('click', () => {
    fillModal.style.display = 'none';
  });

  function populateFillTargetsList(plugins) {
    fillTargetsList.innerHTML = '';
    for (const [pluginName, targets] of Object.entries(plugins)) {
      if (targets.length > 0) {
        const pluginHeader = document.createElement('h4');
        pluginHeader.textContent = `Plugin: ${pluginName}`;
        fillTargetsList.appendChild(pluginHeader);

        targets.forEach(target => {
          const item = document.createElement('div');
          item.className = 'fill-target-item';
          const checkbox = document.createElement('input');
          checkbox.type = 'checkbox';
          checkbox.checked = true;
          checkbox.id = `target-${pluginName}-${target.triplet}`;
          checkbox.dataset.pluginName = pluginName;
          checkbox.dataset.targetTriplet = target.triplet;
          checkbox.dataset.targetInfo = JSON.stringify(target);

          const label = document.createElement('label');
          label.htmlFor = checkbox.id;
          label.textContent = `${target.triplet} (${target.type})`;

          item.appendChild(checkbox);
          item.appendChild(label);
          fillTargetsList.appendChild(item);
        });
      }
    }
    // Reset view
    fillModalBody.style.display = 'block';
    fillProgressView.style.display = 'none';
  }

  startFillButton.addEventListener('click', async () => {
    const selectedTargets = {};
    const checkboxes = fillTargetsList.querySelectorAll('input[type="checkbox"]:checked');

    if (checkboxes.length === 0) {
      showModal('Info', 'No targets selected to fill.');
      return;
    }

    checkboxes.forEach(cb => {
      const pluginName = cb.dataset.pluginName;
      if (!selectedTargets[pluginName]) {
        selectedTargets[pluginName] = [];
      }
      selectedTargets[pluginName].push(JSON.parse(cb.dataset.targetInfo));
    });

    fillModalBody.style.display = 'none';
    fillProgressView.style.display = 'block';
    fillModalTitle.textContent = 'Filling Bundle...';
    populateFillProgressList(selectedTargets);

    const result = await ipcRenderer.invoke('fill-bundle', { 
      bundlePath: currentBundlePath, 
      targetsToBuild: selectedTargets 
    });

    fillModalTitle.textContent = 'Fill Complete';
    if (!result.success) {
      // A final error message if the whole process fails.
      const p = document.createElement('p');
      p.style.color = 'var(--error-color)';
      p.textContent = `Error: ${result.error}`;
      fillProgressList.appendChild(p);
    }
  });

  function populateFillProgressList(plugins) {
    fillProgressList.innerHTML = '';
    for (const [pluginName, targets] of Object.entries(plugins)) {
      targets.forEach(target => {
        const item = document.createElement('div');
        item.className = 'fill-target-item';
        item.id = `progress-${pluginName}-${target.triplet}`;

        const indicator = document.createElement('div');
        indicator.className = 'progress-indicator';
        
        const label = document.createElement('span');
        label.textContent = `${pluginName} - ${target.triplet}`;

        item.appendChild(indicator);
        item.appendChild(label);
        fillProgressList.appendChild(item);
      });
    }
  }

  ipcRenderer.on('fill-bundle-progress', (event, progress) => {
    console.log('Progress update:', progress);
    if (typeof progress === 'object' && progress.status) {
      const { status, plugin, target, message } = progress;
      const progressItem = document.getElementById(`progress-${plugin}-${target}`);
      if (progressItem) {
        const indicator = progressItem.querySelector('.progress-indicator');
        indicator.className = 'progress-indicator'; // Reset classes
        switch (status) {
          case 'building':
            indicator.classList.add('spinner-icon');
            break;
          case 'success':
            indicator.classList.add('success-icon');
            break;
          case 'failure':
            indicator.classList.add('failure-icon');
            break;
        }
        const label = progressItem.querySelector('span');
        if (message) {
          label.textContent = `${plugin} - ${target}: ${message}`;
        }
      }
    } else if (typeof progress === 'object' && progress.message) {
      // Handle final completion message
      if (progress.message.includes('✅')) {
        fillModalTitle.textContent = 'Fill Complete!';
      }
    } else {
      // Handle simple string progress messages
      const p = document.createElement('p');
      p.textContent = progress;
      fillProgressList.appendChild(p);
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

  const result = await ipcRenderer.invoke('select-private-key');
  if (result.canceled || !result.filePaths.length) {
    return; // User canceled the dialog
  }
  const privateKeyPath = result.filePaths[0];

  showSpinner();
  const signResult = await ipcRenderer.invoke('sign-bundle', { bundlePath: currentBundlePath, privateKey: privateKeyPath });
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
            <p><strong>Version:</strong> ${manifest.bundleVersion || 'N/A'}</p>
            <p><strong>Author:</strong> ${manifest.bundleAuthor || 'N/A'}</p>
            <p><strong>Bundled On:</strong> ${manifest.bundledOn || 'N/A'}</p>
            <p><strong>Comment:</strong> ${manifest.bundleComment || 'N/A'}</p>
            ${manifest.bundleAuthorKeyFingerprint ? `<p><strong>Author Key:</strong> ${manifest.bundleAuthorKeyFingerprint}</p>` : ''}
            ${manifest.bundleSignature ? `<p><strong>Signature:</strong> <span class="signature">${manifest.bundleSignature}</span></p>` : ''}
        </div>
    </div>
  `;

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
  
  // Reset to overview tab by default
  switchTab('overview-tab');
}
