// OPAT file handler module for the 4DSTAR Bundle Manager
// Extracted from renderer.js to centralize OPAT file parsing and display logic

// Import dependencies (these will be injected when integrated)
let stateManager, domManager;

// OPAT File Inspector variables
let opatFileInput, opatBrowseBtn, opatView, opatCloseBtn;
let opatHeaderInfo, opatAllTagsList, opatIndexSelector, opatTablesDisplay, opatTableDataContent;

// Initialize OPAT UI elements
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
    };
    
    window.addEventListener('resize', window.updateTableHeights);
}

// Initialize OPAT tab navigation
function initializeOPATTabs() {
    // Use the correct class name that matches the HTML
    const opatTabLinks = document.querySelectorAll('#opat-view .tab-link');
    const opatTabPanes = document.querySelectorAll('#opat-view .tab-pane');
    
    console.log(`[OPAT_HANDLER] Found ${opatTabLinks.length} OPAT tab links`);
    
    opatTabLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetTab = link.dataset.tab;
            console.log(`[OPAT_HANDLER] Tab clicked: ${targetTab}`);
            
            // Update active states
            opatTabLinks.forEach(l => l.classList.remove('active'));
            opatTabPanes.forEach(p => {
                p.classList.remove('active');
                p.classList.add('hidden');
            });
            
            link.classList.add('active');
            const targetPane = document.getElementById(targetTab);
            if (targetPane) {
                targetPane.classList.add('active');
                targetPane.classList.remove('hidden');
                console.log(`[OPAT_HANDLER] Switched to tab: ${targetTab}`);
            }
        });
    });
}

// Reset OPAT viewer state
function resetOPATViewerState() {
    if (opatHeaderInfo) opatHeaderInfo.innerHTML = '';
    if (opatAllTagsList) opatAllTagsList.innerHTML = '';
    if (opatIndexSelector) opatIndexSelector.innerHTML = '<option value="">-- Select an index vector --</option>';
    if (opatTablesDisplay) opatTablesDisplay.innerHTML = '';
    if (opatTableDataContent) opatTableDataContent.innerHTML = '';
}

// Handle OPAT file selection
async function handleOPATFileSelection(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    try {
        console.log('Loading OPAT file:', file.name);
        domManager.showSpinner();
        
        resetOPATViewerState();
        
        const arrayBuffer = await file.arrayBuffer();
        const currentOPATFile = parseOPAT(arrayBuffer);
        stateManager.setOPATFile(currentOPATFile);
        
        displayOPATFileInfo();
        populateIndexSelector();
        
        // Show OPAT view and hide other views
        hideAllViews();
        opatView.classList.remove('hidden');
        
        // Update title with filename
        document.getElementById('opat-title').textContent = `OPAT File Inspector - ${file.name}`;
        
        domManager.hideSpinner();
        
    } catch (error) {
        console.error('Error parsing OPAT file:', error);
        domManager.hideSpinner();
        domManager.showModal('Error', `Failed to parse OPAT file: ${error.message}`);
    }
}

// Display OPAT file information
function displayOPATFileInfo() {
    const currentOPATFile = stateManager.getOPATFile();
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

// Display all table tags
function displayAllTableTags() {
    const currentOPATFile = stateManager.getOPATFile();
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

// Populate index selector
function populateIndexSelector() {
    const currentOPATFile = stateManager.getOPATFile();
    if (!currentOPATFile) return;
    
    opatIndexSelector.innerHTML = '<option value="">-- Select an index vector --</option>';
    
    for (const [key, entry] of currentOPATFile.cardCatalog.entries()) {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = `[${entry.index.join(', ')}]`;
        opatIndexSelector.appendChild(option);
    }
}

// Handle index vector change
function handleIndexVectorChange() {
    const selectedKey = opatIndexSelector.value;
    const currentOPATFile = stateManager.getOPATFile();
    
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

// Display table data
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
                    html += `<button class="show-all-btn" data-tag="${tag}" data-show-all="true">Show All ${table.N_R} Rows</button>`;
                } else {
                    html += `<button class="show-less-btn" data-tag="${tag}" data-show-all="false">Show First 50 Rows</button>`;
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
    
    // Add event listeners for show all/show less buttons
    const showAllBtns = opatTableDataContent.querySelectorAll('.show-all-btn');
    const showLessBtns = opatTableDataContent.querySelectorAll('.show-less-btn');
    
    showAllBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tag = btn.dataset.tag;
            console.log(`[OPAT_HANDLER] Show all rows clicked for tag: ${tag}`);
            const currentIndexValue = opatIndexSelector.value;
            if (currentIndexValue && stateManager.getOPATFile()) {
                const tableData = stateManager.getOPATFile().cards.get(currentIndexValue).tableData.get(tag);
                displayTableData(tableData, tag, true);
            }
        });
    });
    
    showLessBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tag = btn.dataset.tag;
            console.log(`[OPAT_HANDLER] Show less rows clicked for tag: ${tag}`);
            const currentIndexValue = opatIndexSelector.value;
            if (currentIndexValue && stateManager.getOPATFile()) {
                const tableData = stateManager.getOPATFile().cards.get(currentIndexValue).tableData.get(tag);
                displayTableData(tableData, tag, false);
            }
        });
    });
    
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

// Close OPAT file
function closeOPATFile() {
    stateManager.clearOPATFile();
    resetOPATViewerState();
    
    // Reset file input
    if (opatFileInput) {
        opatFileInput.value = '';
    }
    
    // Hide OPAT view and show appropriate home screen
    hideAllViews();
    showCategoryHomeScreen('opat');
}

// Helper function to hide all views
function hideAllViews() {
    const views = [
        'welcome-screen', 'libplugin-home', 'opat-home', 
        'libconstants-home', 'serif-home', 'opat-view', 'libplugin-view'
    ];
    
    views.forEach(viewId => {
        const view = document.getElementById(viewId);
        if (view) view.classList.add('hidden');
    });
}

// Show appropriate home screen based on selected category
function showCategoryHomeScreen(category) {
    hideAllViews();
    
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

// Initialize dependencies (called when module is loaded)
function initializeDependencies(deps) {
    stateManager = deps.stateManager;
    domManager = deps.domManager;
}

module.exports = {
    initializeDependencies,
    initializeOPATElements,
    initializeOPATTabs,
    resetOPATViewerState,
    handleOPATFileSelection,
    displayOPATFileInfo,
    displayAllTableTags,
    populateIndexSelector,
    handleIndexVectorChange,
    displayTableData,
    closeOPATFile,
    hideAllViews,
    showCategoryHomeScreen
};
