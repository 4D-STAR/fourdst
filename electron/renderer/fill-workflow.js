// Fill workflow module for the 4DSTAR Bundle Manager
// Extracted from renderer.js to centralize fill process management

const { ipcRenderer } = require('electron');

// Import dependencies (these will be injected when integrated)
let stateManager, domManager;

// Load fillable targets for the Fill tab
async function loadFillableTargets() {
  const currentBundlePath = stateManager.getCurrentBundlePath();
  const elements = domManager.getElements();
  
  console.log('loadFillableTargets called, currentBundlePath:', currentBundlePath);
  
  // Check if required DOM elements exist
  if (!elements.fillNoTargets || !elements.fillTargetsContent || !elements.fillLoading) {
    console.error('Fill tab DOM elements not found');
    domManager.showModal('Error', 'Fill tab interface not properly initialized.');
    return;
  }
  
  if (!currentBundlePath) {
    console.log('No bundle path, showing no targets message');
    hideAllFillStates();
    elements.fillNoTargets.classList.remove('hidden');
    return;
  }
  
  try {
    // Show loading state
    hideAllFillStates();
    elements.fillLoading.classList.remove('hidden');
    elements.loadFillableTargetsBtn.disabled = true;
    
    console.log('Requesting fillable targets for:', currentBundlePath);
    const result = await ipcRenderer.invoke('get-fillable-targets', currentBundlePath);
    console.log('Fillable targets result:', result);
    
    if (result && result.success && result.data) {
      const hasTargets = Object.values(result.data).some(targets => targets.length > 0);
      
      if (hasTargets) {
        console.log('Found fillable targets, populating table');
        hideAllFillStates();
        elements.fillTargetsContent.classList.remove('hidden');
        populateFillTargetsTable(result.data);
      } else {
        console.log('No fillable targets found');
        hideAllFillStates();
        elements.fillNoTargets.classList.remove('hidden');
      }
    } else {
      console.error('Failed to get fillable targets:', result.error);
      hideAllFillStates();
      elements.fillNoTargets.classList.remove('hidden');
      domManager.showModal('Error', `Failed to load fillable targets: ${result.error || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Exception in loadFillableTargets:', error);
    hideAllFillStates();
    elements.fillNoTargets.classList.remove('hidden');
    domManager.showModal('Error', `Failed to load fillable targets: ${error.message}`);
  } finally {
    elements.loadFillableTargetsBtn.disabled = false;
  }
}

// Helper function to hide all fill tab states
function hideAllFillStates() {
  const elements = domManager.getElements();
  elements.fillLoading.classList.add('hidden');
  elements.fillNoTargets.classList.add('hidden');
  elements.fillTargetsContent.classList.add('hidden');
  elements.fillProgressContainer.classList.add('hidden');
}

// Create modern table-based interface for fillable targets
function populateFillTargetsTable(plugins) {
  const elements = domManager.getElements();
  elements.fillPluginsTables.innerHTML = '';
  
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
      elements.fillPluginsTables.appendChild(pluginTable);
    }
  }
  
  // Add event listeners for select all functionality
  setupFillTargetEventListeners();
}

// Setup event listeners for Fill tab functionality
function setupFillTargetEventListeners() {
  const elements = domManager.getElements();
  
  // Plugin-level select all checkboxes
  document.querySelectorAll('.plugin-select-all').forEach(checkbox => {
    checkbox.addEventListener('change', (e) => {
      const pluginName = e.target.dataset.plugin;
      const pluginCheckboxes = document.querySelectorAll(`.fill-target-checkbox[data-plugin="${pluginName}"]`);
      pluginCheckboxes.forEach(cb => cb.checked = e.target.checked);
    });
  });

  // Global select/deselect all buttons
  elements.selectAllTargetsBtn.addEventListener('click', () => {
    document.querySelectorAll('.fill-target-checkbox, .plugin-select-all').forEach(cb => cb.checked = true);
  });

  elements.deselectAllTargetsBtn.addEventListener('click', () => {
    document.querySelectorAll('.fill-target-checkbox, .plugin-select-all').forEach(cb => cb.checked = false);
  });

  // Start fill process button
  elements.startFillProcessBtn.addEventListener('click', async () => {
    const selectedTargetsByPlugin = {};
    
    document.querySelectorAll('.fill-target-checkbox:checked').forEach(checkbox => {
      try {
        const target = JSON.parse(checkbox.dataset.target);
        const pluginName = checkbox.dataset.plugin;
        
        if (!selectedTargetsByPlugin[pluginName]) {
          selectedTargetsByPlugin[pluginName] = [];
        }
        selectedTargetsByPlugin[pluginName].push(target);
      } catch (error) {
        console.error('Error parsing target data:', error);
      }
    });
    
    if (Object.keys(selectedTargetsByPlugin).length === 0) {
      domManager.showModal('No Targets Selected', 'Please select at least one target to build.');
      return;
    }
    
    // Show signature warning before starting fill process
    const currentBundle = stateManager.getCurrentBundle();
    console.log('[FRONTEND] Checking signature for modal:', currentBundle);
    console.log('[FRONTEND] Bundle report:', currentBundle?.report);
    console.log('[FRONTEND] Signature info:', currentBundle?.report?.signature);
    console.log('[FRONTEND] Full signature object:', JSON.stringify(currentBundle?.report?.signature, null, 2));
    
    // Check multiple possible signature indicators
    const signature = currentBundle?.report?.signature;
    const isSignedBundle = signature && (
      signature.valid === true ||
      signature.status === 'VALID' ||
      signature.status === 'SIGNED' ||
      (signature.fingerprint && signature.fingerprint !== '') ||
      (signature.publicKeyFingerprint && signature.publicKeyFingerprint !== '') ||
      signature.verified === true
    );
    
    console.log('[FRONTEND] Signature check result:', isSignedBundle);
    console.log('[FRONTEND] Signature properties:', {
      valid: signature?.valid,
      status: signature?.status,
      fingerprint: signature?.fingerprint,
      publicKeyFingerprint: signature?.publicKeyFingerprint,
      verified: signature?.verified
    });
    
    if (currentBundle && currentBundle.report && isSignedBundle) {
      console.log('[FRONTEND] Bundle is signed, showing confirmation dialog');
      const confirmed = confirm('Warning: Signature Will Be Invalidated\n\nBuilding new binaries will invalidate the current bundle signature. The bundle will need to be re-signed after the fill process completes.\n\nDo you want to continue?');
      if (confirmed) {
        console.log('[FRONTEND] User confirmed, starting fill process');
        await startFillProcess(selectedTargetsByPlugin);
      } else {
        console.log('[FRONTEND] User cancelled fill process due to signature warning');
      }
    } else {
      console.log('[FRONTEND] Bundle is not signed or signature is invalid, proceeding without warning');
      await startFillProcess(selectedTargetsByPlugin);
    }
  });
}

// Create progress display for fill process
function populateFillProgress(selectedTargetsByPlugin) {
  const elements = domManager.getElements();
  elements.fillProgressContent.innerHTML = '';
  
  Object.entries(selectedTargetsByPlugin).forEach(([pluginName, targets]) => {
    targets.forEach(target => {
      const progressItem = document.createElement('div');
      progressItem.className = 'fill-progress-item';
      // Create unique ID using both plugin and target to avoid duplicates
      progressItem.id = `progress-${pluginName}-${target.triplet}`;
      progressItem.innerHTML = `
        <div class="progress-target">${pluginName}: ${target.triplet}</div>
        <div class="progress-status building">
          <span class="spinner"></span>
          Building...
        </div>
        <div class="progress-bar">
          <div class="progress-fill" style="width: 0%"></div>
        </div>
        <div class="progress-logs">
          <button class="toggle-logs-btn">Hide Build Output</button>
          <div class="logs-content">
            <pre class="terminal-output">Starting build...\n</pre>
          </div>
        </div>
      `;
      elements.fillProgressContent.appendChild(progressItem);
      
      // Add toggle functionality for logs
      const toggleBtn = progressItem.querySelector('.toggle-logs-btn');
      const logsContent = progressItem.querySelector('.logs-content');
      
      toggleBtn.addEventListener('click', () => {
        const isVisible = !logsContent.classList.contains('hidden');
        logsContent.classList.toggle('hidden', isVisible);
        toggleBtn.textContent = isVisible ? 'Show Build Output' : 'Hide Build Output';
      });
    });
  });
}

// Start the fill process
async function startFillProcess(selectedTargetsByPlugin) {
  const currentBundlePath = stateManager.getCurrentBundlePath();
  const elements = domManager.getElements();
  
  if (!currentBundlePath) {
    domManager.showModal('Error', 'No bundle is currently open.');
    return;
  }
  
  try {
    // Show progress view
    hideAllFillStates();
    elements.fillProgressContainer.classList.remove('hidden');
    populateFillProgress(selectedTargetsByPlugin);
    
    // Set up progress listener
    const progressHandler = (event, progressData) => {
      updateFillProgress(progressData);
    };
    
    ipcRenderer.on('fill-bundle-progress', progressHandler);
    
    // Start the fill process
    const result = await ipcRenderer.invoke('fill-bundle', {
      bundlePath: currentBundlePath,
      targetsToBuild: selectedTargetsByPlugin
    });
    
    // Clean up progress listener
    ipcRenderer.removeListener('fill-bundle-progress', progressHandler);
    
    if (result.success) {
      domManager.showModal('Fill Complete', 'Bundle fill process completed successfully. Reloading bundle...');
      // Reload the bundle to show updated information
      // Note: This will be handled by the parent module that has access to bundleOperations
      if (window.bundleOperations) {
        await window.bundleOperations.reloadCurrentBundle();
      }
      domManager.hideModal();
    } else {
      domManager.showModal('Fill Error', `Fill process failed: ${result.error}`);
    }
    
  } catch (error) {
    console.error('Fill process error:', error);
    domManager.showModal('Fill Error', `Fill process failed: ${error.message}`);
  }
}

// Track current building target for stderr routing
let currentBuildingTarget = null;

// Update progress display during fill process
function updateFillProgress(progressData) {
  console.log('Fill progress update:', progressData);
  
  // Handle stderr output - route to current building target
  if (progressData.type === 'stderr' && progressData.stderr) {
    console.log(`[FRONTEND] Received stderr: ${progressData.stderr}`);
    console.log(`[FRONTEND] Current building target: ${currentBuildingTarget}`);
    
    // Route stderr to the currently building target's terminal
    if (currentBuildingTarget) {
      const targetTerminal = document.querySelector(`#progress-${currentBuildingTarget} .terminal-output`);
      console.log(`[FRONTEND] Found target terminal:`, targetTerminal);
      if (targetTerminal) {
        const currentOutput = targetTerminal.textContent;
        targetTerminal.textContent = currentOutput + progressData.stderr + '\n';
        
        // Auto-scroll to bottom
        targetTerminal.scrollTop = targetTerminal.scrollHeight;
      } else {
        console.warn(`[FRONTEND] Could not find terminal for target: ${currentBuildingTarget}`);
      }
    } else {
      console.warn(`[FRONTEND] No current building target, adding stderr to all terminals`);
      // Fallback: add to all terminals if no current target
      document.querySelectorAll('.terminal-output').forEach(terminalOutput => {
        const currentOutput = terminalOutput.textContent;
        terminalOutput.textContent = currentOutput + progressData.stderr + '\n';
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
      });
    }
    return;
  }
  
  if (progressData.target && progressData.plugin) {
    console.log(`[FRONTEND] Processing target update for: ${progressData.plugin}-${progressData.target}, status: ${progressData.status}`);
    console.log(`[FRONTEND] Looking for element with ID: progress-${progressData.plugin}-${progressData.target}`);
    
    // Debug: list all existing progress item IDs
    const allProgressItems = document.querySelectorAll('[id^="progress-"]');
    console.log(`[FRONTEND] Existing progress item IDs:`, Array.from(allProgressItems).map(item => item.id));
    
    const progressItem = document.getElementById(`progress-${progressData.plugin}-${progressData.target}`);
    console.log(`[FRONTEND] Found progress item:`, progressItem);
    
    if (progressItem) {
      const statusElement = progressItem.querySelector('.progress-status');
      const progressBar = progressItem.querySelector('.progress-fill');
      const logsContainer = progressItem.querySelector('.progress-logs');
      const terminalOutput = progressItem.querySelector('.terminal-output');
      
      if (progressData.status) {
        console.log(`[FRONTEND] Updating status to: ${progressData.status}`);
        // Update progress bar and status based on status
        let percentage = 0;
        switch (progressData.status.toLowerCase()) {
          case 'building':
            percentage = 50;
            statusElement.className = 'progress-status building';
            statusElement.innerHTML = '<span class="spinner"></span> Building...';
            progressItem.className = 'fill-progress-item building';
            // Track this target as currently building for stderr routing
            currentBuildingTarget = progressData.target;
            console.log(`[FRONTEND] Now building target: ${currentBuildingTarget}`);
            break;
          case 'success':
            percentage = 100;
            statusElement.className = 'progress-status success';
            statusElement.innerHTML = '✓ Built';
            progressItem.className = 'fill-progress-item success';
            if (logsContainer) logsContainer.style.display = 'block';
            // Clear current building target when done
            if (currentBuildingTarget === progressData.target) {
              currentBuildingTarget = null;
              console.log(`[FRONTEND] Cleared building target after success`);
            }
            break;
          case 'failure':
          case 'failed':
            percentage = 100;
            statusElement.className = 'progress-status failed';
            statusElement.innerHTML = '✗ Failed';
            progressItem.className = 'fill-progress-item failed';
            if (logsContainer) logsContainer.style.display = 'block';
            // Clear current building target when done
            if (currentBuildingTarget === progressData.target) {
              currentBuildingTarget = null;
              console.log(`[FRONTEND] Cleared building target after failure`);
            }
            break;
        }
        
        if (progressBar) {
          progressBar.style.width = `${percentage}%`;
        }
      }
      
      // Add stderr output if available (for target-specific messages)
      if (progressData.stderr && terminalOutput) {
        const currentOutput = terminalOutput.textContent;
        terminalOutput.textContent = currentOutput + progressData.stderr + '\n';
        
        // Auto-scroll to bottom
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
      }
    }
  }
}

// Initialize dependencies (called when module is loaded)
function initializeDependencies(deps) {
  stateManager = deps.stateManager;
  domManager = deps.domManager;
}

module.exports = {
  initializeDependencies,
  loadFillableTargets,
  hideAllFillStates,
  populateFillTargetsTable,
  setupFillTargetEventListeners,
  populateFillProgress,
  startFillProcess,
  updateFillProgress
};
