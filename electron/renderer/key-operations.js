// Key operations module for the 4DSTAR Bundle Manager
// Handles all key management operations (list, generate, add, remove, sync)

const { ipcRenderer } = require('electron');

// Dependencies (injected by renderer-refactored.js)
let stateManager, domManager, uiComponents;

// Initialize dependencies
function initializeDependencies(deps) {
  stateManager = deps.stateManager;
  domManager = deps.domManager;
  uiComponents = deps.uiComponents;
  console.log('[KEY_OPERATIONS] Dependencies initialized');
}

// === KEY LISTING ===
async function loadKeys() {
  try {
    domManager.showSpinner();
    const result = await ipcRenderer.invoke('list-keys');
    domManager.hideSpinner();

    if (result.success) {
      stateManager.setKeysState(result);
      displayKeys(result);
      return result;
    } else {
      domManager.showModal('Error', `Failed to load keys: ${result.error}`);
      return null;
    }
  } catch (error) {
    domManager.hideSpinner();
    domManager.showModal('Error', `Failed to load keys: ${error.message}`);
    return null;
  }
}

function displayKeys(keysData) {
  const keysContainer = document.getElementById('keys-list-container');
  if (!keysContainer) return;

  if (keysData.total_count === 0) {
    keysContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🔑</div>
        <h3>No Keys Found</h3>
        <p>No trusted keys are currently installed. Generate or add keys to get started.</p>
      </div>
    `;
    return;
  }

  // Update the main header with count and add action buttons
  const mainHeader = document.querySelector('#keys-list-view .keys-header h3');
  if (mainHeader) {
    mainHeader.textContent = `Trusted Keys (${keysData.total_count})`;
  }
  
  // Add action buttons to the header if they don't exist
  let keysHeader = document.querySelector('#keys-list-view .keys-header');
  if (keysHeader && !keysHeader.querySelector('.keys-actions')) {
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'keys-actions';
    actionsDiv.innerHTML = `
      <button id="refresh-keys-btn" class="action-button secondary">
        <span class="icon">🔄</span> Refresh
      </button>
      <button id="sync-remotes-btn" class="action-button primary">
        <span class="icon">🔄</span> Sync Remotes
      </button>
    `;
    keysHeader.appendChild(actionsDiv);
  }

  let html = '';

  for (const [sourceName, keys] of Object.entries(keysData.keys)) {
    html += `
      <div class="key-source-section">
        <div class="source-header">
          <h4>${sourceName}</h4>
          <span class="key-count">${keys.length} keys</span>
        </div>
        <div class="keys-table">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Fingerprint</th>
                <th>Size</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
    `;

    for (const key of keys) {
      const shortFingerprint = key.fingerprint.substring(0, 16) + '...';
      html += `
        <tr data-key-fingerprint="${key.fingerprint}">
          <td class="key-name">${key.name}</td>
          <td class="key-fingerprint" title="${key.fingerprint}">${shortFingerprint}</td>
          <td class="key-size">${key.size_bytes} bytes</td>
          <td class="key-actions">
            <button class="btn btn-small btn-danger remove-key-btn" 
                    data-key-fingerprint="${key.fingerprint}" 
                    data-key-name="${key.name}">
              Remove
            </button>
          </td>
        </tr>
      `;
    }

    html += `
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  keysContainer.innerHTML = html;

  // Add event listeners for dynamically generated content
  setupKeyListEventListeners();
}

function setupKeyListEventListeners() {
  // Refresh keys button
  const refreshBtn = document.getElementById('refresh-keys-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', loadKeys);
  }

  // Sync remotes button
  const syncBtn = document.getElementById('sync-remotes-btn');
  if (syncBtn) {
    syncBtn.addEventListener('click', handleSyncRemotes);
  }

  // Remove key buttons - now handled exclusively here (removed from event-handlers.js)
  const removeButtons = document.querySelectorAll('.remove-key-btn');
  removeButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      const fingerprint = e.target.dataset.keyFingerprint;
      const keyName = e.target.dataset.keyName;
      handleRemoveKey(fingerprint, keyName);
    });
  });
}

// === KEY GENERATION ===
async function handleGenerateKey() {
  const keyName = document.getElementById('generate-key-name')?.value || 'author_key';
  const keyType = document.getElementById('generate-key-type')?.value || 'ed25519';
  const outputDir = document.getElementById('generate-output-dir')?.value || '.';

  if (!keyName.trim()) {
    domManager.showModal('Error', 'Please enter a key name.');
    return;
  }

  try {
    domManager.showSpinner();
    const result = await ipcRenderer.invoke('generate-key', {
      keyName: keyName.trim(),
      keyType: keyType,
      outputDir: outputDir
    });
    domManager.hideSpinner();

    if (result.success) {
      domManager.showModal('Success', `
        <div class="key-generation-success">
          <h4>Key Generated Successfully!</h4>
          <div class="key-details">
            <p><strong>Key Type:</strong> ${result.key_type.toUpperCase()}</p>
            <p><strong>Fingerprint:</strong> <code>${result.fingerprint}</code></p>
            <p><strong>Private Key:</strong> <code>${result.private_key_path}</code></p>
            <p><strong>Public Key:</strong> <code>${result.public_key_path}</code></p>
          </div>
          <div class="warning">
            <strong>⚠️ Important:</strong> Keep your private key secure and never share it!
          </div>
        </div>
      `);
      
      // Clear form
      document.getElementById('generate-key-name').value = '';
      document.getElementById('generate-output-dir').value = '.';
    } else {
      domManager.showModal('Error', `Failed to generate key: ${result.error}`);
    }
  } catch (error) {
    domManager.hideSpinner();
    domManager.showModal('Error', `Failed to generate key: ${error.message}`);
  }
}

// === KEY ADDITION ===
async function handleAddKey() {
  try {
    // Use IPC-based file dialog instead of @electron/remote
    const keyPath = await ipcRenderer.invoke('select-key-file');
    
    if (!keyPath) {
      return; // User canceled dialog
    }
    
    domManager.showSpinner();
    const addResult = await ipcRenderer.invoke('add-key', keyPath);
    domManager.hideSpinner();

    if (addResult.success) {
      if (addResult.already_existed) {
        domManager.showModal('Info', `Key '${addResult.key_name}' already exists in trust store.`);
      } else {
        domManager.showModal('Success', `
          <div class="key-add-success-modern">
            <div class="success-header">
              <div class="success-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="12" cy="12" r="10" fill="#10b981" stroke="#059669" stroke-width="2"/>
                  <path d="m9 12 2 2 4-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <h3>Key Added Successfully!</h3>
              <p class="success-subtitle">Your public key has been added to the trust store</p>
            </div>
            
            <div class="key-details-card">
              <div class="detail-row">
                <div class="detail-label">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  Key Name
                </div>
                <div class="detail-value">${addResult.key_name}</div>
              </div>
              
              <div class="detail-row">
                <div class="detail-label">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 15a3 3 0 100-6 3 3 0 000 6z" stroke="currentColor" stroke-width="2"/>
                    <path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" stroke="currentColor" stroke-width="2"/>
                  </svg>
                  Fingerprint
                </div>
                <div class="detail-value fingerprint-value">
                  <code>${addResult.fingerprint}</code>
                  <button class="copy-btn" onclick="navigator.clipboard.writeText('${addResult.fingerprint}'); this.innerHTML='✓ Copied'; setTimeout(() => this.innerHTML='Copy', 2000)">Copy</button>
                </div>
              </div>
            </div>
            
            <div class="success-footer">
              <div class="info-banner">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                  <path d="m9 9 1.5 1.5L16 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span>This key can now be used to verify signed bundles</span>
              </div>
            </div>
          </div>
        `);
      }
      
      // Refresh keys list
      await loadKeys();
    } else {
      domManager.showModal('Error', `Failed to add key: ${addResult.error}`);
    }
  } catch (error) {
    domManager.hideSpinner();
    domManager.showModal('Error', `Failed to add key: ${error.message}`);
  }
}

// === KEY REMOVAL ===
async function handleRemoveKey(fingerprint, keyName) {
  const confirmed = await uiComponents.showConfirmDialog(
    'Remove Key',
    `Are you sure you want to remove the key "${keyName}"?\n\nThis action cannot be undone.`
  );

  if (!confirmed) return;

  try {
    domManager.showSpinner();
    const result = await ipcRenderer.invoke('remove-key', fingerprint);
    domManager.hideSpinner();

    if (result.success) {
      domManager.showModal('Success', `Removed ${result.removed_count} key(s) successfully.`);
      
      // Refresh keys list
      await loadKeys();
    } else {
      domManager.showModal('Error', `Failed to remove key: ${result.error}`);
    }
  } catch (error) {
    domManager.hideSpinner();
    domManager.showModal('Error', `Failed to remove key: ${error.message}`);
  }
}

// === REMOTE SYNC ===
async function handleSyncRemotes() {
  try {
    domManager.showSpinner();
    const result = await ipcRenderer.invoke('sync-remotes');
    domManager.hideSpinner();

    if (result.success) {
      const successCount = result.synced_remotes.filter(r => r.status === 'success').length;
      const failedCount = result.synced_remotes.filter(r => r.status === 'failed').length;
      
      let message = `
        <div class="sync-results">
          <h4>Remote Sync Completed</h4>
          <p>✅ Successful: ${successCount}</p>
          <p>❌ Failed: ${failedCount}</p>
          <p>📦 Total keys synced: ${result.total_keys_synced}</p>
        </div>
      `;

      if (result.removed_remotes.length > 0) {
        message += `<p><strong>Removed failing remotes:</strong> ${result.removed_remotes.join(', ')}</p>`;
      }

      domManager.showModal('Sync Results', message);
      
      // Refresh keys list
      await loadKeys();
    } else {
      domManager.showModal('Error', `Failed to sync remotes: ${result.error}`);
    }
  } catch (error) {
    domManager.hideSpinner();
    domManager.showModal('Error', `Failed to sync remotes: ${error.message}`);
  }
}

// === REMOTE MANAGEMENT ===
async function loadRemoteSources() {
  try {
    const result = await ipcRenderer.invoke('get-remote-sources');
    
    if (result.success) {
      displayRemoteSources(result.remotes);
      return result.remotes;
    } else {
      domManager.showModal('Error', `Failed to load remote sources: ${result.error}`);
      return [];
    }
  } catch (error) {
    domManager.showModal('Error', `Failed to load remote sources: ${error.message}`);
    return [];
  }
}

function displayRemoteSources(remotes) {
  const remotesContainer = document.getElementById('remotes-list-container');
  if (!remotesContainer) return;

  if (remotes.length === 0) {
    remotesContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🌐</div>
        <h3>No Remote Sources</h3>
        <p>No remote key sources are configured. Add remote repositories to sync keys automatically.</p>
      </div>
    `;
    return;
  }

  let html = `
    <div class="remotes-header">
      <h3>Remote Key Sources (${remotes.length})</h3>
    </div>
    <div class="remotes-table">
      <table>
        <thead>
          <tr>
            <th>Status</th>
            <th>Name</th>
            <th>URL</th>
            <th>Keys</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
  `;

  for (const remote of remotes) {
    const status = remote.exists ? '✅' : '❌';
    const statusText = remote.exists ? 'Synced' : 'Not synced';
    
    html += `
      <tr>
        <td class="remote-status" title="${statusText}">${status}</td>
        <td class="remote-name">${remote.name}</td>
        <td class="remote-url" title="${remote.url}">${remote.url}</td>
        <td class="remote-keys">${remote.keys_count}</td>
        <td class="remote-actions">
          <button class="btn btn-small btn-danger remove-remote-btn" 
                  data-remote-name="${remote.name}">
            Remove
          </button>
        </td>
      </tr>
    `;
  }

  html += `
        </tbody>
      </table>
    </div>
  `;

  remotesContainer.innerHTML = html;

  // Add event listeners for remove buttons
  const removeButtons = document.querySelectorAll('.remove-remote-btn');
  removeButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      const remoteName = e.target.dataset.remoteName;
      handleRemoveRemoteSource(remoteName);
    });
  });
}

async function handleAddRemoteSource() {
  const name = document.getElementById('remote-name')?.value;
  const url = document.getElementById('remote-url')?.value;

  if (!name || !url) {
    domManager.showModal('Error', 'Please enter both name and URL for the remote source.');
    return;
  }

  try {
    domManager.showSpinner();
    const result = await ipcRenderer.invoke('add-remote-source', { name: name.trim(), url: url.trim() });
    domManager.hideSpinner();

    if (result.success) {
      domManager.showModal('Success', `Remote source '${result.name}' added successfully.`);
      
      // Clear form
      document.getElementById('remote-name').value = '';
      document.getElementById('remote-url').value = '';
      
      // Refresh remotes list
      await loadRemoteSources();
    } else {
      domManager.showModal('Error', `Failed to add remote source: ${result.error}`);
    }
  } catch (error) {
    domManager.hideSpinner();
    domManager.showModal('Error', `Failed to add remote source: ${error.message}`);
  }
}

async function handleRemoveRemoteSource(remoteName) {
  const confirmed = await uiComponents.showConfirmDialog(
    'Remove Remote Source',
    `Are you sure you want to remove the remote source "${remoteName}"?\n\nThis will also remove all keys synced from this source.`
  );

  if (!confirmed) return;

  try {
    domManager.showSpinner();
    const result = await ipcRenderer.invoke('remove-remote-source', remoteName);
    domManager.hideSpinner();

    if (result.success) {
      domManager.showModal('Success', `Remote source '${result.name}' removed successfully.`);
      
      // Refresh remotes list and keys list
      await loadRemoteSources();
      await loadKeys();
    } else {
      domManager.showModal('Error', `Failed to remove remote source: ${result.error}`);
    }
  } catch (error) {
    domManager.hideSpinner();
    domManager.showModal('Error', `Failed to remove remote source: ${error.message}`);
  }
}

// Export functions
module.exports = {
  initializeDependencies,
  loadKeys,
  loadTrustedKeys: loadKeys, // Alias for compatibility
  handleGenerateKey,
  handleAddKey,
  handleRemoveKey,
  handleSyncRemotes,
  loadRemoteSources,
  handleAddRemoteSource,
  handleRemoveRemoteSource
};
