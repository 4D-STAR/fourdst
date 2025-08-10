// UI components module for the 4DSTAR Bundle Manager
// Extracted from renderer.js to centralize reusable UI component logic

// Import dependencies (these will be injected when integrated)
let stateManager, domManager;

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
  const originalMetadata = stateManager.getOriginalMetadata();
  const originalValue = originalMetadata[fieldName] || '';
  
  input.value = originalValue;
  toggleFieldEdit(fieldName, false);
}

// Check if any fields have been modified
function checkForChanges() {
  const inputs = document.querySelectorAll('.field-input');
  const originalMetadata = stateManager.getOriginalMetadata();
  let hasChanges = false;

  inputs.forEach(input => {
    const fieldName = input.dataset.field;
    const currentValue = input.value.trim();
    const originalValue = originalMetadata[fieldName] || '';
    
    if (currentValue !== originalValue) {
      hasChanges = true;
    }
  });

  stateManager.markUnsavedChanges(hasChanges);
  updateSaveButtonVisibility();
}

// Show/hide save button based on changes
function updateSaveButtonVisibility() {
  const elements = domManager.getElements();
  const hasUnsavedChanges = stateManager.getHasUnsavedChanges();
  
  if (hasUnsavedChanges) {
    elements.saveMetadataBtn.classList.remove('hidden');
  } else {
    elements.saveMetadataBtn.classList.add('hidden');
  }
}

// Show save options modal
function showSaveOptionsModal() {
  const hasUnsavedChanges = stateManager.getHasUnsavedChanges();
  if (!hasUnsavedChanges) {
    return;
  }
  
  const elements = domManager.getElements();
  const currentBundle = stateManager.getCurrentBundle();
  
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
  
  elements.saveOptionsModal.classList.remove('hidden');
}

// Hide save options modal
function hideSaveOptionsModal() {
  const elements = domManager.getElements();
  elements.saveOptionsModal.classList.add('hidden');
}

// Initialize dependencies (called when module is loaded)
function initializeDependencies(deps) {
  stateManager = deps.stateManager;
  domManager = deps.domManager;
}

module.exports = {
  initializeDependencies,
  createEditableField,
  setupEditableFieldListeners,
  toggleFieldEdit,
  saveFieldEdit,
  cancelFieldEdit,
  checkForChanges,
  updateSaveButtonVisibility,
  showSaveOptionsModal,
  hideSaveOptionsModal
};
