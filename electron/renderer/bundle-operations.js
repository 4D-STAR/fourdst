// Bundle operations module for the 4DSTAR Bundle Manager
// Extracted from renderer.js to centralize bundle-specific business logic

const { ipcRenderer } = require('electron');
const path = require('path');

// Import dependencies (these will be injected or imported when integrated)
let stateManager, domManager, uiComponents;

// --- BUNDLE ACTIONS HANDLERS ---
async function handleOpenBundle() {
  const bundlePath = await ipcRenderer.invoke('select-file');
  if (!bundlePath) return;

  // Small delay to ensure file dialog closes properly
  await new Promise(resolve => setTimeout(resolve, 100));

  domManager.showSpinner();
  domManager.showModal('Opening...', `Opening bundle: ${path.basename(bundlePath)}`);
  const result = await ipcRenderer.invoke('open-bundle', bundlePath);
  domManager.hideSpinner();

  if (result.success) {
    stateManager.setBundleState(result, bundlePath);
    displayBundleInfo(result.report);
    domManager.showView('bundle-view');
    domManager.hideModal();
  } else {
    domManager.showModal('Error Opening Bundle', `Failed to open bundle: ${result ? result.error : 'Unknown error'}`);
  }
}

async function handleSignBundle() {
  const currentBundlePath = stateManager.getCurrentBundlePath();
  if (!currentBundlePath) return;

  domManager.showSpinner();
  const signResult = await ipcRenderer.invoke('sign-bundle', currentBundlePath);
  domManager.hideSpinner();

  if (signResult.success) {
    domManager.showModal('Success', 'Bundle signed successfully.');
    await reloadCurrentBundle();
    domManager.hideModal();
  } else {
    domManager.showModal('Sign Error', `Failed to sign bundle: ${signResult.error}`);
  }
}

async function handleValidateBundle() {
  const currentBundlePath = stateManager.getCurrentBundlePath();
  if (!currentBundlePath) return;

  domManager.showSpinner();
  const result = await ipcRenderer.invoke('validate-bundle', currentBundlePath);
  domManager.hideSpinner();

  if (result.success) {
    // With the new JSON architecture, validation data is directly in result
    const errors = result.errors || [];
    const warnings = result.warnings || [];
    const validationIssues = errors.concat(warnings);
    
    const elements = domManager.getElements();
    if (validationIssues.length > 0) {
      elements.validationResults.textContent = validationIssues.join('\n');
      elements.validationTabLink.classList.remove('hidden');
    } else {
      elements.validationResults.textContent = 'Bundle is valid.';
      elements.validationTabLink.classList.add('hidden');
    }
    
    // Switch to the validation tab to show the results
    domManager.switchTab('validation-tab');
    
    // Show summary in modal
    const summary = result.summary || { errors: errors.length, warnings: warnings.length };
    const message = `Validation finished with ${summary.errors} errors and ${summary.warnings} warnings.`;
    domManager.showModal('Validation Complete', message);

  } else {
    domManager.showModal('Validation Error', `Failed to validate bundle: ${result.error}`);
  }
}

async function handleClearBundle() {
  const currentBundlePath = stateManager.getCurrentBundlePath();
  if (!currentBundlePath) return;

  domManager.showSpinner();
  const result = await ipcRenderer.invoke('clear-bundle', currentBundlePath);
  domManager.hideSpinner();

  if (result.success) {
    domManager.showModal('Success', 'All binaries have been cleared. Reloading...');
    await reloadCurrentBundle();
    domManager.hideModal();
  } else {
    domManager.showModal('Clear Error', `Failed to clear binaries: ${result.error}`);
  }
}

async function handleFillBundle() {
  const currentBundle = stateManager.getCurrentBundle();
  if (!currentBundle) return domManager.showModal('Action Canceled', 'Please open a bundle first.');

  domManager.showSpinner();
  domManager.showModal('Filling Bundle...', 'Adding local binaries to bundle.');
  const result = await ipcRenderer.invoke('fill-bundle', currentBundle.bundlePath);
  domManager.hideSpinner();

  if (result.success) {
    domManager.showModal('Success', 'Binaries filled successfully. Reloading...');
    await reloadCurrentBundle();
    domManager.hideModal();
  } else {
    domManager.showModal('Fill Error', `Failed to fill bundle: ${result.error}`);
  }
}

// --- DATA DISPLAY ---
async function reloadCurrentBundle() {
  const currentBundle = stateManager.getCurrentBundle();
  if (!currentBundle) return;
  
  const reloadResult = await ipcRenderer.invoke('open-bundle', currentBundle.bundlePath);
  if (reloadResult.success) {
    stateManager.setBundleState(reloadResult, currentBundle.bundlePath);
    displayBundleInfo(reloadResult.report);
  } else {
    domManager.showModal('Reload Error', `Failed to reload bundle details: ${reloadResult.error}`);
  }
}

function displayBundleInfo(report) {
  if (!report) {
    domManager.showModal('Display Error', 'Could not load bundle information.');
    return;
  }

  const { manifest, signature, validation, plugins } = report;
  const elements = domManager.getElements();

  // Store original metadata for comparison
  stateManager.updateOriginalMetadata({
    bundleVersion: manifest.bundleVersion || '',
    bundleAuthor: manifest.bundleAuthor || '',
    bundleComment: manifest.bundleComment || ''
  });
  stateManager.markUnsavedChanges(false);
  updateSaveButtonVisibility();

  // Set bundle title
  elements.bundleTitle.textContent = manifest.bundleName || 'Untitled Bundle';

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

  elements.manifestDetails.innerHTML = `
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
            ${uiComponents.createEditableField('Version', 'bundleVersion', manifest.bundleVersion || 'N/A')}
            ${uiComponents.createEditableField('Author', 'bundleAuthor', manifest.bundleAuthor || 'N/A')}
            <p><strong>Bundled On:</strong> ${manifest.bundledOn || 'N/A'}</p>
            ${uiComponents.createEditableField('Comment', 'bundleComment', manifest.bundleComment || 'N/A')}
            ${manifest.bundleAuthorKeyFingerprint ? `<p><strong>Author Key:</strong> ${manifest.bundleAuthorKeyFingerprint}</p>` : ''}
            ${manifest.bundleSignature ? `<p><strong>Signature:</strong> <span class="signature">${manifest.bundleSignature}</span></p>` : ''}
        </div>
    </div>
  `;

  // Add event listeners for edit functionality
  uiComponents.setupEditableFieldListeners();

  // --- Plugins Tab ---
  elements.pluginsList.innerHTML = '';
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
      elements.pluginsList.appendChild(pluginCard);
    });
  } else {
    elements.pluginsList.innerHTML = '<div class="card"><div class="card-content"><p>No plugins found in this bundle.</p></div></div>';
  }

  // --- Validation Tab ---
  const validationIssues = validation.errors.concat(validation.warnings);
  if (validationIssues.length > 0) {
    elements.validationResults.textContent = validationIssues.join('\n');
    elements.validationTabLink.classList.remove('hidden');
  } else {
    elements.validationResults.textContent = 'Bundle is valid.';
    elements.validationTabLink.classList.add('hidden');
  }
  
  // Reset to overview tab by default
  domManager.switchTab('overview-tab');
}

// Helper function that calls ui-components
function updateSaveButtonVisibility() {
  if (uiComponents && uiComponents.updateSaveButtonVisibility) {
    uiComponents.updateSaveButtonVisibility();
  }
}

// Initialize dependencies (called when module is loaded)
function initializeDependencies(deps) {
  stateManager = deps.stateManager;
  domManager = deps.domManager;
  uiComponents = deps.uiComponents;
}

module.exports = {
  initializeDependencies,
  handleOpenBundle,
  handleSignBundle,
  handleValidateBundle,
  handleClearBundle,
  handleFillBundle,
  reloadCurrentBundle,
  displayBundleInfo
};
