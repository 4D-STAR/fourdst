/**
 * Documentation Handler Module
 * Manages documentation viewing functionality for the 4DSTAR Electron app
 */

class DocsHandler {
    constructor(domManager, stateManager) {
        this.domManager = domManager;
        this.stateManager = stateManager;
        this.docsConfig = null;
        this.currentDoc = null;
        this.filteredDocs = [];
        
        console.log('[DOCS_HANDLER] Documentation handler initialized');
    }

    /**
     * Initialize the documentation handler
     */
    async initialize() {
        try {
            await this.loadDocsConfig();
            this.setupEventListeners();
            this.populateDocsGrid();
            this.populateDocsList();
            console.log('[DOCS_HANDLER] Documentation handler ready');
        } catch (error) {
            console.error('[DOCS_HANDLER] Failed to initialize:', error);
        }
    }

    /**
     * Load documentation configuration from docs.json
     */
    async loadDocsConfig() {
        try {
            const response = await fetch('./docs.json');
            if (!response.ok) {
                throw new Error(`Failed to load docs.json: ${response.status}`);
            }
            this.docsConfig = await response.json();
            console.log('[DOCS_HANDLER] Loaded documentation config:', Object.keys(this.docsConfig));
        } catch (error) {
            console.error('[DOCS_HANDLER] Error loading docs config:', error);
            // Fallback to empty config
            this.docsConfig = {};
        }
    }

    /**
     * Setup event listeners for documentation interface
     */
    setupEventListeners() {
        // Search functionality
        const searchInput = document.getElementById('docs-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterDocs(e.target.value);
            });
        }

        // Category filter
        const categoryFilter = document.getElementById('docs-category-filter');
        if (categoryFilter) {
            categoryFilter.addEventListener('change', (e) => {
                this.filterDocsByCategory(e.target.value);
            });
        }

        // Documentation viewer controls
        const backBtn = document.getElementById('docs-back-btn');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                this.showDocsHome();
            });
        }

        const externalBtn = document.getElementById('docs-open-external-btn');
        if (externalBtn) {
            externalBtn.addEventListener('click', () => {
                this.openExternalDoc();
            });
        }

        const githubBtn = document.getElementById('docs-github-btn');
        if (githubBtn) {
            githubBtn.addEventListener('click', () => {
                this.openGitHub();
            });
        }
    }

    /**
     * Populate the documentation grid on the home screen
     */
    populateDocsGrid() {
        const docsGrid = document.getElementById('docs-grid');
        if (!docsGrid || !this.docsConfig) return;

        docsGrid.innerHTML = '';

        Object.entries(this.docsConfig).forEach(([key, doc]) => {
            const card = this.createDocCard(key, doc);
            docsGrid.appendChild(card);
        });
    }

    /**
     * Populate the documentation list in the sidebar
     */
    populateDocsList() {
        const docsList = document.getElementById('docs-list');
        if (!docsList || !this.docsConfig) return;

        this.filteredDocs = Object.entries(this.docsConfig);
        this.renderDocsList();
    }

    /**
     * Create a documentation card for the grid
     */
    createDocCard(key, doc) {
        const card = document.createElement('div');
        card.className = 'docs-card';
        card.dataset.docKey = key;

        card.innerHTML = `
            <div class="docs-card-header">
                <div class="docs-card-icon">📚</div>
                <h3 class="docs-card-title">${doc.name}</h3>
            </div>
            <p class="docs-card-desc">${doc.desc}</p>
            <div class="docs-card-meta">
                <span class="docs-card-version">v${doc.version}</span>
                <span class="docs-card-category">${doc.category}</span>
            </div>
        `;

        card.addEventListener('click', () => {
            this.openDocumentation(key, doc);
        });

        return card;
    }

    /**
     * Create a documentation item for the sidebar list
     */
    createDocItem(key, doc) {
        const item = document.createElement('div');
        item.className = 'docs-item';
        item.dataset.docKey = key;

        item.innerHTML = `
            <div class="docs-item-name">${doc.name}</div>
            <div class="docs-item-desc">${doc.desc}</div>
            <div class="docs-item-meta">
                <span>v${doc.version}</span>
                <span class="docs-item-category">${doc.category}</span>
            </div>
        `;

        item.addEventListener('click', () => {
            this.openDocumentation(key, doc);
        });

        return item;
    }

    /**
     * Render the filtered documentation list
     */
    renderDocsList() {
        const docsList = document.getElementById('docs-list');
        if (!docsList) return;

        docsList.innerHTML = '';

        if (this.filteredDocs.length === 0) {
            docsList.innerHTML = '<div class="empty-state">No documentation found</div>';
            return;
        }

        this.filteredDocs.forEach(([key, doc]) => {
            const item = this.createDocItem(key, doc);
            docsList.appendChild(item);
        });
    }

    /**
     * Filter documentation by search term
     */
    filterDocs(searchTerm) {
        const term = searchTerm.toLowerCase().trim();
        
        if (!term) {
            this.filteredDocs = Object.entries(this.docsConfig);
        } else {
            this.filteredDocs = Object.entries(this.docsConfig).filter(([key, doc]) => {
                return doc.name.toLowerCase().includes(term) ||
                       doc.desc.toLowerCase().includes(term) ||
                       doc.category.toLowerCase().includes(term);
            });
        }

        this.renderDocsList();
    }

    /**
     * Filter documentation by category
     */
    filterDocsByCategory(category) {
        if (!category) {
            this.filteredDocs = Object.entries(this.docsConfig);
        } else {
            this.filteredDocs = Object.entries(this.docsConfig).filter(([key, doc]) => {
                return doc.category === category;
            });
        }

        this.renderDocsList();
    }

    /**
     * Open documentation in the viewer
     */
    async openDocumentation(key, doc) {
        try {
            console.log('[DOCS_HANDLER] Opening documentation:', doc.name);
            
            this.currentDoc = { key, ...doc };
            
            // Update viewer title and info
            const titleEl = document.getElementById('docs-viewer-title');
            if (titleEl) {
                titleEl.textContent = `${doc.name} Documentation`;
            }

            const libEl = document.getElementById('docs-current-lib');
            if (libEl) {
                libEl.textContent = doc.name;
            }

            const versionEl = document.getElementById('docs-current-version');
            if (versionEl) {
                versionEl.textContent = `v${doc.version}`;
            }

            // Load documentation in iframe
            await this.loadDocInIframe(doc);

            // Show the documentation viewer
            this.domManager.showView('docs-viewer');

        } catch (error) {
            console.error('[DOCS_HANDLER] Error opening documentation:', error);
            this.showError('Failed to load documentation');
        }
    }

    /**
     * Load documentation in the iframe
     */
    async loadDocInIframe(doc) {
        const iframe = document.getElementById('docs-iframe');
        if (!iframe) return;

        // Try to load local documentation first
        const localPath = `./${doc.path}/index.html`;
        
        try {
            // Check if local documentation exists
            const response = await fetch(localPath, { method: 'HEAD' });
            if (response.ok) {
                iframe.src = localPath;
                console.log('[DOCS_HANDLER] Loaded local documentation:', localPath);
                return;
            }
        } catch (error) {
            console.log('[DOCS_HANDLER] Local documentation not found, trying hosted version');
        }

        // Fallback to hosted documentation
        if (doc.hostDocURL) {
            iframe.src = doc.hostDocURL;
            console.log('[DOCS_HANDLER] Loaded hosted documentation:', doc.hostDocURL);
        } else {
            throw new Error('No documentation source available');
        }
    }

    /**
     * Show the documentation home screen
     */
    showDocsHome() {
        this.currentDoc = null;
        this.domManager.showView('docs-home');
    }

    /**
     * Open current documentation in external browser
     */
    openExternalDoc() {
        if (!this.currentDoc) return;

        const url = this.currentDoc.hostDocURL;
        if (url) {
            // Use IPC to open in external browser
            if (window.electronAPI && window.electronAPI.openExternal) {
                window.electronAPI.openExternal(url);
            } else {
                window.open(url, '_blank');
            }
        }
    }

    /**
     * Open current documentation's GitHub repository
     */
    openGitHub() {
        if (!this.currentDoc) return;

        const url = this.currentDoc.githubURL;
        if (url) {
            // Use IPC to open in external browser
            if (window.electronAPI && window.electronAPI.openExternal) {
                window.electronAPI.openExternal(url);
            } else {
                window.open(url, '_blank');
            }
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        console.error('[DOCS_HANDLER] Error:', message);
        // You could implement a toast notification or modal here
        alert(`Documentation Error: ${message}`);
    }

    /**
     * Get available documentation categories
     */
    getCategories() {
        if (!this.docsConfig) return [];
        
        const categories = new Set();
        Object.values(this.docsConfig).forEach(doc => {
            categories.add(doc.category);
        });
        
        return Array.from(categories).sort();
    }

    /**
     * Refresh documentation configuration
     */
    async refresh() {
        await this.loadDocsConfig();
        this.populateDocsGrid();
        this.populateDocsList();
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DocsHandler;
}
