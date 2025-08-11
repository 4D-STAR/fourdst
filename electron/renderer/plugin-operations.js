// Plugin Operations Module
// Handles all plugin-related functionality in the GUI

const { ipcRenderer } = require('electron');

class PluginOperations {
  constructor() {
    this.parsedInterfaces = null;
    this.headerFilePath = null;
    this.deps = null;
    this.currentView = 'plugin-init-view';
  }

  initializeDependencies(deps) {
    this.deps = deps;
    console.log('[PLUGIN_OPERATIONS] Dependencies initialized');
    console.log('[PLUGIN_OPERATIONS] Available deps:', Object.keys(deps));
  }

  // Show specific plugin view
  showPluginView(viewId) {
    // Show the main plugin view container first
    this.deps.domManager.showView('plugin-view');
    
    // Ensure plugin button event listeners are set up now that buttons are visible
    this.ensurePluginButtonListeners();
    
    // Hide all plugin views
    const pluginViews = document.querySelectorAll('.plugin-management-view');
    pluginViews.forEach(view => view.classList.add('hidden'));
    
    // Show the requested view
    const targetView = document.getElementById(viewId);
    if (targetView) {
      targetView.classList.remove('hidden');
      this.currentView = viewId;
    }
  }

  // Parse interface header file and populate interface selection
  async parseInterfaceHeader(headerFile) {
    try {
      this.showPluginLoading('Parsing interface header file...');

      // Read header file content
      const headerContent = await this.readFileAsText(headerFile);

      // Call backend to parse interfaces using specific IPC handler
      const result = await ipcRenderer.invoke('parse-cpp-interface', {
        headerContent: headerContent,
        fileName: headerFile.name
      });

      if (result.success) {
        this.populateInterfaceSelection(result.data);
        this.headerFilePath = headerFile.path; // Store the header file path for later use
        this.hidePluginResults();
      } else {
        this.showPluginError(`Failed to parse header file: ${result.error}`);
      }
    } catch (error) {
      this.showPluginError(`Failed to parse header file: ${error.message}`);
    }
  }

  // Populate interface selection dropdown
  populateInterfaceSelection(interfaces) {
    const interfaceSelection = document.getElementById('plugin-interface-selection');
    const interfaceSelect = document.getElementById('plugin-interface-select');
    const methodsPreview = document.getElementById('plugin-interface-methods');
    const methodsList = document.getElementById('plugin-methods-list');

    // Clear existing options
    interfaceSelect.innerHTML = '<option value="">-- Select an Interface --</option>';

    // Add interfaces to dropdown
    Object.keys(interfaces).forEach(interfaceName => {
      const option = document.createElement('option');
      option.value = interfaceName;
      option.textContent = interfaceName;
      interfaceSelect.appendChild(option);
    });

    // Show interface selection
    interfaceSelection.style.display = 'block';

    // Store interfaces data for later use
    this.parsedInterfaces = interfaces;

    // Setup interface selection change handler
    interfaceSelect.onchange = () => {
      const selectedInterface = interfaceSelect.value;
      if (selectedInterface && interfaces[selectedInterface]) {
        // Show methods preview
        methodsList.innerHTML = '';
        interfaces[selectedInterface].forEach(method => {
          const li = document.createElement('li');
          li.textContent = method.signature;
          methodsList.appendChild(li);
        });
        methodsPreview.style.display = 'block';
      } else {
        methodsPreview.style.display = 'none';
      }
      this.updateInitButtonState();
    };

    this.updateInitButtonState();
  }

  // Initialize Plugin Project
  async initializePlugin() {
    const projectName = document.getElementById('plugin-project-name').value.trim();
    const headerFile = document.getElementById('plugin-header-file').files[0];
    const selectedInterface = document.getElementById('plugin-interface-select').value;
    const outputDir = document.getElementById('plugin-directory').value.trim();
    const version = document.getElementById('plugin-version').value.trim();
    const libpluginRev = document.getElementById('plugin-libplugin-rev').value.trim();

    if (!projectName || !headerFile || !selectedInterface || !outputDir) {
      this.showPluginError('Please fill in all required fields and select an interface.');
      return;
    }

    try {
      this.showPluginLoading('Initializing plugin project...');

      // Call backend to initialize plugin using specific IPC handler
      const result = await ipcRenderer.invoke('generate-plugin-project', {
        project_name: projectName,
        chosen_interface: selectedInterface,
        interfaces: this.parsedInterfaces,
        output_directory: outputDir,
        version: version,
        libplugin_revision: libpluginRev,
        header_path: this.headerFilePath
      });

      this.handlePluginResult(result, 'Plugin project initialized successfully!');
    } catch (error) {
      this.showPluginError(`Failed to initialize plugin: ${error.message}`);
    }
  }

  // Validate Plugin Project
  async validatePlugin() {
    const pluginPath = document.getElementById('validate-plugin-path').value.trim();

    if (!pluginPath) {
      this.showPluginError('Please select a plugin directory.');
      return;
    }

    try {
      this.showPluginLoading('Validating plugin project...');

      const result = await ipcRenderer.invoke('validate-plugin-project', {
        plugin_directory: pluginPath
      });

      this.handlePluginResult(result, 'Plugin validation completed!');
    } catch (error) {
      this.showPluginError(`Failed to validate plugin: ${error.message}`);
    }
  }



  // Extract Plugin from Bundle
  async extractPlugin() {
    const pluginName = document.getElementById('extract-plugin-name').value.trim();
    const bundleFile = document.getElementById('extract-bundle-file').files[0];
    const outputDir = document.getElementById('extract-output-dir').value.trim();

    if (!pluginName || !bundleFile || !outputDir) {
      this.showPluginError('Please fill in all required fields.');
      return;
    }

    try {
      this.showPluginLoading('Extracting plugin from bundle...');

      const result = await ipcRenderer.invoke('extract-plugin-from-bundle', {
        plugin_name: pluginName,
        bundle_path: bundleFile.path,
        output_directory: outputDir
      });

      this.handlePluginResult(result, 'Plugin extracted successfully!');
    } catch (error) {
      this.showPluginError(`Failed to extract plugin: ${error.message}`);
    }
  }

  // Compare Plugin Sources
  async comparePlugins() {
    const pluginName = document.getElementById('diff-plugin-name').value.trim();
    const bundleA = document.getElementById('diff-bundle-a').files[0];
    const bundleB = document.getElementById('diff-bundle-b').files[0];

    if (!pluginName || !bundleA || !bundleB) {
      this.showPluginError('Please fill in all required fields.');
      return;
    }

    try {
      this.showPluginLoading('Comparing plugin sources...');

      const result = await ipcRenderer.invoke('compare-plugin-sources', {
        plugin_name: pluginName,
        bundle_a_path: bundleA.path,
        bundle_b_path: bundleB.path
      });

      this.handlePluginResult(result, 'Plugin comparison completed!');
    } catch (error) {
      this.showPluginError(`Failed to compare plugins: ${error.message}`);
    }
  }

  // Helper Methods
  async readFileAsText(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = e => resolve(e.target.result);
      reader.onerror = e => reject(new Error('Failed to read file'));
      reader.readAsText(file);
    });
  }

  showPluginLoading(message) {
    const resultsDiv = document.querySelector(`#${this.currentView} .plugin-results`);
    if (resultsDiv) {
      resultsDiv.classList.remove('hidden');
      resultsDiv.innerHTML = `
        <div class="loading-state">
          <div class="loading-spinner"></div>
          <p>${message}</p>
        </div>
      `;
    }
  }

  showPluginError(message) {
    const resultsDiv = document.querySelector(`#${this.currentView} .plugin-results`);
    if (resultsDiv) {
      resultsDiv.classList.remove('hidden');
      resultsDiv.innerHTML = `
        <div class="error-state">
          <h4>Error</h4>
          <p>${message}</p>
        </div>
      `;
    }
  }

  hidePluginResults() {
    const resultsDiv = document.querySelector(`#${this.currentView} .plugin-results`);
    if (resultsDiv) {
      resultsDiv.classList.add('hidden');
    }
  }

  handlePluginResult(result, successMessage) {
    const resultsDiv = document.querySelector(`#${this.currentView} .plugin-results`);
    if (!resultsDiv) return;

    resultsDiv.classList.remove('hidden');

    if (result.success) {
      let content = `<div class="success-state"><h4>${successMessage}</h4>`;
      
      if (result.data) {
        if (result.data.output) {
          content += `<pre class="command-output">${result.data.output}</pre>`;
        }
        if (result.data.diff) {
          content += `<pre class="diff-output">${result.data.diff}</pre>`;
        }
        if (result.data.validation_results) {
          content += `<div class="validation-results">`;
          result.data.validation_results.forEach(item => {
            content += `<p><strong>${item.check}:</strong> ${item.status}</p>`;
          });
          content += `</div>`;
        }
      }
      
      content += `</div>`;
      resultsDiv.innerHTML = content;
    } else {
      resultsDiv.innerHTML = `
        <div class="error-state">
          <h4>Operation Failed</h4>
          <p>${result.error}</p>
        </div>
      `;
    }
  }

  // Setup event listeners for plugin operations (called when plugin buttons are visible)
  setupPluginEventListeners() {
    // Don't set up listeners during initial app startup - wait until plugin buttons are visible
    // This method will be called from showPluginView() when needed
  }

  // Setup plugin button event listeners when they're actually in the DOM
  ensurePluginButtonListeners() {
    if (this.listenersSetup) return; // Avoid duplicate setup
    
    // Plugin navigation buttons with active state management
    const pluginButtons = [
      { id: 'init-plugin-btn', view: 'plugin-init-view' },
      { id: 'validate-plugin-btn', view: 'plugin-validate-view' },
      { id: 'extract-plugin-btn', view: 'plugin-extract-view' },
      { id: 'diff-plugin-btn', view: 'plugin-diff-view' }
    ];

    let allButtonsFound = true;
    pluginButtons.forEach(({ id, view }) => {
      const button = document.getElementById(id);
      
      if (button) {
        button.addEventListener('click', () => {
          // Remove active class from all plugin buttons
          pluginButtons.forEach(({ id: btnId }) => {
            document.getElementById(btnId)?.classList.remove('active');
          });
          
          // Add active class to clicked button
          button.classList.add('active');
          
          // Show the plugin view
          this.showPluginView(view);
        });
      } else {
        allButtonsFound = false;
      }
    });

    if (allButtonsFound) {
      this.listenersSetup = true;
    }

    // Plugin Initialize form
    document.getElementById('plugin-header-browse-btn')?.addEventListener('click', () => {
      document.getElementById('plugin-header-file').click();
    });

    document.getElementById('plugin-header-file')?.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      const filename = file?.name || 'No file selected';
      document.getElementById('plugin-header-filename').textContent = filename;
      
      // Hide interface selection and reset state when new file is selected
      const interfaceSelection = document.getElementById('plugin-interface-selection');
      const interfaceSelect = document.getElementById('plugin-interface-select');
      const methodsPreview = document.getElementById('plugin-interface-methods');
      
      if (interfaceSelection) interfaceSelection.style.display = 'none';
      if (interfaceSelect) interfaceSelect.value = '';
      if (methodsPreview) methodsPreview.style.display = 'none';
      
      this.parsedInterfaces = null;
      this.updateInitButtonState();
      
      // Parse interface file if one was selected
      if (file) {
        await this.parseInterfaceHeader(file);
      }
    });

    document.getElementById('plugin-directory-browse-btn')?.addEventListener('click', async () => {
      const result = await ipcRenderer.invoke('select-directory');
      if (result) {
        document.getElementById('plugin-directory').value = result;
        this.updateInitButtonState();
      }
    });

    document.getElementById('plugin-project-name')?.addEventListener('input', () => {
      this.updateInitButtonState();
    });

    document.getElementById('plugin-init-execute-btn')?.addEventListener('click', () => {
      this.initializePlugin();
    });

    // Plugin Validate form
    document.getElementById('validate-plugin-browse-btn')?.addEventListener('click', async () => {
      const result = await ipcRenderer.invoke('select-directory');
      if (result) {
        document.getElementById('validate-plugin-path').value = result;
      }
    });

    document.getElementById('plugin-validate-execute-btn')?.addEventListener('click', () => {
      this.validatePlugin();
    });

    // Plugin Pack form
    document.getElementById('pack-plugin-browse-btn')?.addEventListener('click', async () => {
      const result = await ipcRenderer.invoke('select-directory');
      if (result) {
        document.getElementById('pack-plugin-path').value = result;
      }
    });

    document.getElementById('plugin-pack-execute-btn')?.addEventListener('click', () => {
      this.packPlugin();
    });

    // Plugin Extract form
    document.getElementById('extract-bundle-browse-btn')?.addEventListener('click', () => {
      document.getElementById('extract-bundle-file').click();
    });

    document.getElementById('extract-bundle-file')?.addEventListener('change', (e) => {
      const filename = e.target.files[0]?.name || 'No file selected';
      document.getElementById('extract-bundle-filename').textContent = filename;
      this.updateExtractButtonState();
    });

    document.getElementById('extract-output-browse-btn')?.addEventListener('click', async () => {
      const result = await ipcRenderer.invoke('select-directory');
      if (result) {
        document.getElementById('extract-output-dir').value = result;
        this.updateExtractButtonState();
      }
    });

    document.getElementById('extract-plugin-name')?.addEventListener('input', () => {
      this.updateExtractButtonState();
    });

    document.getElementById('plugin-extract-execute-btn')?.addEventListener('click', () => {
      this.extractPlugin();
    });

    // Plugin Diff form
    document.getElementById('diff-bundle-a-browse-btn')?.addEventListener('click', () => {
      document.getElementById('diff-bundle-a').click();
    });

    document.getElementById('diff-bundle-a')?.addEventListener('change', (e) => {
      const filename = e.target.files[0]?.name || 'No file selected';
      document.getElementById('diff-bundle-a-filename').textContent = filename;
      this.updateDiffButtonState();
    });

    document.getElementById('diff-bundle-b-browse-btn')?.addEventListener('click', () => {
      document.getElementById('diff-bundle-b').click();
    });

    document.getElementById('diff-bundle-b')?.addEventListener('change', (e) => {
      const filename = e.target.files[0]?.name || 'No file selected';
      document.getElementById('diff-bundle-b-filename').textContent = filename;
      this.updateDiffButtonState();
    });

    document.getElementById('diff-plugin-name')?.addEventListener('input', () => {
      this.updateDiffButtonState();
    });

    document.getElementById('plugin-diff-execute-btn')?.addEventListener('click', () => {
      this.comparePlugins();
    });

    console.log('[PLUGIN_OPERATIONS] Event listeners setup complete');
  }

  // Button state management
  updateInitButtonState() {
    const projectName = document.getElementById('plugin-project-name').value.trim();
    const headerFile = document.getElementById('plugin-header-file').files[0];
    const selectedInterface = document.getElementById('plugin-interface-select').value;
    const outputDir = document.getElementById('plugin-directory').value.trim();
    const button = document.getElementById('plugin-init-execute-btn');
    
    if (button) {
      // Button is enabled only when all required fields are filled AND an interface is selected
      button.disabled = !projectName || !headerFile || !selectedInterface || !outputDir;
    }
  }

  updateExtractButtonState() {
    const pluginName = document.getElementById('extract-plugin-name').value.trim();
    const bundleFile = document.getElementById('extract-bundle-file').files[0];
    const outputDir = document.getElementById('extract-output-dir').value.trim();
    const button = document.getElementById('plugin-extract-execute-btn');
    
    if (button) {
      button.disabled = !pluginName || !bundleFile || !outputDir;
    }
  }

  updateDiffButtonState() {
    const pluginName = document.getElementById('diff-plugin-name').value.trim();
    const bundleA = document.getElementById('diff-bundle-a').files[0];
    const bundleB = document.getElementById('diff-bundle-b').files[0];
    const button = document.getElementById('plugin-diff-execute-btn');
    
    if (button) {
      button.disabled = !pluginName || !bundleA || !bundleB;
    }
  }
}

module.exports = new PluginOperations();
