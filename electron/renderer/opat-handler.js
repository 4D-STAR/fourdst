// OPAT file handler module for the 4DSTAR Bundle Manager
// Extracted from renderer.js to centralize OPAT file parsing and display logic

// Import dependencies (these will be injected when integrated)
let stateManager, domManager, opatPlotting;

// OPAT File Inspector variables
let opatFileInput, opatBrowseBtn, opatView, opatCloseBtn;
let opatHeaderInfo, opatAllTagsList, opatIndexSelector, opatTablesDisplay, opatTableDataContent;
let opatElementsInitialized = false;

// Initialize OPAT UI elements
function initializeOPATElements() {
    console.log('[OPAT_HANDLER] initializeOPATElements called, already initialized:', opatElementsInitialized);
    
    // Prevent duplicate initialization
    if (opatElementsInitialized) {
        console.log('[OPAT_HANDLER] OPAT elements already initialized, skipping...');
        return;
    }
    
    opatFileInput = document.getElementById('opat-file-input');
    opatBrowseBtn = document.getElementById('opat-browse-btn');
    opatView = document.getElementById('opat-view');
    opatCloseBtn = document.getElementById('opat-close-btn');
    opatHeaderInfo = document.getElementById('opat-header-info');
    opatAllTagsList = document.getElementById('opat-all-tags-list');
    opatIndexSelector = document.getElementById('opat-index-selector');
    opatTablesDisplay = document.getElementById('opat-tables-display');
    opatTableDataContent = document.getElementById('opat-table-data-content');

    console.log('[OPAT_HANDLER] Found elements:', {
        opatFileInput: !!opatFileInput,
        opatBrowseBtn: !!opatBrowseBtn,
        opatView: !!opatView,
        opatCloseBtn: !!opatCloseBtn
    });

    // Event listeners
    if (opatBrowseBtn) {
        console.log('[OPAT_HANDLER] Adding click listener to browse button');
        opatBrowseBtn.addEventListener('click', () => {
            console.log('[OPAT_HANDLER] Browse button clicked, triggering file input');
            if (opatFileInput) {
                opatFileInput.click();
            } else {
                console.error('[OPAT_HANDLER] File input element not found!');
            }
        });
    }
    
    if (opatFileInput) {
        console.log('[OPAT_HANDLER] Adding change listener to file input');
        opatFileInput.addEventListener('change', handleOPATFileSelection);
    }
    
    if (opatIndexSelector) {
        opatIndexSelector.addEventListener('change', handleIndexVectorChange);
    }
    
    if (opatCloseBtn) {
        opatCloseBtn.addEventListener('click', closeOPATFile);
    }
    
    opatElementsInitialized = true;
    console.log('[OPAT_HANDLER] OPAT elements initialization complete');

    // Initialize OPAT tab navigation
    initializeOPATTabs();
    
    // Initialize plotting elements if module is available
    if (opatPlotting) {
        opatPlotting.initializePlottingElements();
    }
    
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
    
    // Reset plotting state if module is available
    if (opatPlotting) {
        opatPlotting.resetPlottingState();
    }
}

// Handle OPAT file selection
async function handleOPATFileSelection(event) {
    console.log('[OPAT_HANDLER] ===== FILE SELECTION EVENT TRIGGERED =====');
    console.log('[OPAT_HANDLER] Event target:', event.target);
    console.log('[OPAT_HANDLER] Files array:', event.target.files);
    console.log('[OPAT_HANDLER] Number of files:', event.target.files ? event.target.files.length : 0);
    
    const file = event.target.files[0];
    if (!file) {
        console.log('[OPAT_HANDLER] No file selected - event fired but no file found');
        return;
    }

    console.log('[OPAT_HANDLER] File selected:', {
        name: file.name,
        size: file.size,
        type: file.type,
        lastModified: new Date(file.lastModified)
    });

    try {
        console.log('[OPAT_HANDLER] Starting file processing...');
        
        // Reset the viewer state
        console.log('[OPAT_HANDLER] Resetting viewer state...');
        resetOPATViewerState();
        
        // Show the OPAT view first to ensure UI is visible
        console.log('[OPAT_HANDLER] Showing OPAT view...');
        domManager.showView('opat-view');
        
        // Read and parse the file
        console.log('[OPAT_HANDLER] Reading file as ArrayBuffer...');
        const arrayBuffer = await file.arrayBuffer();
        console.log('[OPAT_HANDLER] File read successfully, arrayBuffer size:', arrayBuffer.byteLength);
        
        // Check if parseOPAT is available
        console.log('[OPAT_HANDLER] Checking parseOPAT availability...');
        console.log('[OPAT_HANDLER] typeof parseOPAT:', typeof parseOPAT);
        console.log('[OPAT_HANDLER] window.parseOPAT:', typeof window.parseOPAT);
        
        if (typeof parseOPAT === 'undefined' && typeof window.parseOPAT === 'undefined') {
            throw new Error('parseOPAT function is not available. Make sure opatParser.js is loaded.');
        }
        
        // Use global parseOPAT if local one is undefined
        const parseFunction = typeof parseOPAT !== 'undefined' ? parseOPAT : window.parseOPAT;
        console.log('[OPAT_HANDLER] Using parse function:', typeof parseFunction);
        
        console.log('[OPAT_HANDLER] Calling parseOPAT...');
        const currentOPATFile = parseFunction(arrayBuffer);
        console.log('[OPAT_HANDLER] Parse result:', currentOPATFile ? 'SUCCESS' : 'FAILED');
        console.log('[OPAT_HANDLER] Parsed file object:', currentOPATFile);
        
        if (currentOPATFile) {
            console.log('[OPAT_HANDLER] Setting file in state manager...');
            stateManager.setOPATFile(currentOPATFile);
            
            // Display file information
            console.log('[OPAT_HANDLER] Displaying file information...');
            displayOPATFileInfo();
            displayAllTableTags();
            populateIndexSelector();
            
            console.log('[OPAT_HANDLER] ===== OPAT FILE LOADED SUCCESSFULLY =====');
        } else {
            console.error('[OPAT_HANDLER] parseOPAT returned null/undefined');
            domManager.showModal('Error', 'Failed to parse OPAT file. Please check the file format.');
        }
    } catch (error) {
        console.error('[OPAT_HANDLER] ===== ERROR IN FILE PROCESSING =====');
        console.error('[OPAT_HANDLER] Error details:', error);
        console.error('[OPAT_HANDLER] Error stack:', error.stack);
        domManager.showModal('Error', `Failed to load OPAT file: ${error.message}`);
    } finally {
        console.log('[OPAT_HANDLER] Cleaning up file input...');
        // Clear the file input to prevent issues with reopening the same file
        if (event.target) {
            event.target.value = '';
            console.log('[OPAT_HANDLER] File input cleared');
        }
        console.log('[OPAT_HANDLER] ===== FILE SELECTION HANDLER COMPLETE =====');
    }
}

// Open OPAT file from file path (for file associations)
async function openOpatFromPath(filePath) {
    if (!filePath) {
        console.log('[OPAT_HANDLER] openOpatFromPath: No file path provided');
        return;
    }

    try {
        console.log('[OPAT_HANDLER] Opening OPAT file from path:', filePath);
        
        // Ensure OPAT UI elements are initialized
        console.log('[OPAT_HANDLER] Initializing OPAT UI elements...');
        initializeOPATElements();
        initializeOPATTabs();
        
        // Reset the viewer state
        resetOPATViewerState();
        
        // Show the OPAT view first to ensure UI is visible
        console.log('[OPAT_HANDLER] Showing OPAT view...');
        domManager.showView('opat-view');
        
        // Read the file using Node.js fs
        const fs = require('fs');
        console.log('[OPAT_HANDLER] Reading file from disk...');
        const fileBuffer = fs.readFileSync(filePath);
        const arrayBuffer = fileBuffer.buffer.slice(fileBuffer.byteOffset, fileBuffer.byteOffset + fileBuffer.byteLength);
        console.log('[OPAT_HANDLER] File read successfully, arrayBuffer size:', arrayBuffer.byteLength);
        
        // Parse the OPAT file
        console.log('[OPAT_HANDLER] Parsing OPAT file...');
        if (typeof parseOPAT === 'undefined') {
            throw new Error('parseOPAT function is not available. Make sure opatParser.js is loaded.');
        }
        const currentOPATFile = parseOPAT(arrayBuffer);
        console.log('[OPAT_HANDLER] Parse result:', currentOPATFile ? 'SUCCESS' : 'FAILED');
        
        if (currentOPATFile) {
            console.log('[OPAT_HANDLER] Setting file in state manager...');
            stateManager.setOPATFile(currentOPATFile);
            
            // Display file information
            console.log('[OPAT_HANDLER] Displaying file information...');
            displayOPATFileInfo();
            displayAllTableTags();
            populateIndexSelector();
            
            console.log('[OPAT_HANDLER] OPAT file opened successfully via file association');
        } else {
            console.error('[OPAT_HANDLER] parseOPAT returned null/undefined for file association');
            throw new Error('Failed to parse OPAT file. Please check the file format.');
        }
    } catch (error) {
        console.error('[OPAT_HANDLER] Error opening OPAT file via file association:', error);
        domManager.showModal('Error', `Failed to open OPAT file: ${error.message}`);
    }
}

// Display OPAT file information
function displayOPATFileInfo() {
    console.log('[OPAT_HANDLER] displayOPATFileInfo called');
    const currentOPATFile = stateManager.getOPATFile();
    console.log('[OPAT_HANDLER] Current OPAT file from state:', currentOPATFile);
    
    if (!currentOPATFile) {
        console.error('[OPAT_HANDLER] No OPAT file in state manager!');
        return;
    }
    
    console.log('[OPAT_HANDLER] opatHeaderInfo element:', opatHeaderInfo);
    console.log('[OPAT_HANDLER] opatHeaderInfo exists:', !!opatHeaderInfo);
    
    if (!opatHeaderInfo) {
        console.error('[OPAT_HANDLER] opatHeaderInfo element not found! Re-initializing...');
        opatHeaderInfo = document.getElementById('opat-header-info');
        console.log('[OPAT_HANDLER] After re-init, opatHeaderInfo:', !!opatHeaderInfo);
    }
    
    const header = currentOPATFile.header;
    console.log('[OPAT_HANDLER] Header object:', header);
    
    const headerHTML = `
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
    
    console.log('[OPAT_HANDLER] Generated header HTML length:', headerHTML.length);
    
    if (opatHeaderInfo) {
        opatHeaderInfo.innerHTML = headerHTML;
        console.log('[OPAT_HANDLER] Header info updated successfully');
        console.log('[OPAT_HANDLER] opatHeaderInfo.innerHTML length:', opatHeaderInfo.innerHTML.length);
    } else {
        console.error('[OPAT_HANDLER] Cannot update header info - element still not found');
    }
    
    // Display all unique table tags
    console.log('[OPAT_HANDLER] Calling displayAllTableTags...');
    displayAllTableTags();
}

// Display all table tags
function displayAllTableTags() {
    console.log('[OPAT_HANDLER] displayAllTableTags called');
    const currentOPATFile = stateManager.getOPATFile();
    console.log('[OPAT_HANDLER] Current OPAT file in displayAllTableTags:', currentOPATFile);
    
    if (!currentOPATFile) {
        console.error('[OPAT_HANDLER] No OPAT file in displayAllTableTags!');
        return;
    }
    
    console.log('[OPAT_HANDLER] opatAllTagsList element:', opatAllTagsList);
    console.log('[OPAT_HANDLER] opatAllTagsList exists:', !!opatAllTagsList);
    
    if (!opatAllTagsList) {
        console.error('[OPAT_HANDLER] opatAllTagsList element not found! Re-initializing...');
        opatAllTagsList = document.getElementById('opat-all-tags-list');
        console.log('[OPAT_HANDLER] After re-init, opatAllTagsList:', !!opatAllTagsList);
    }
    
    console.log('[OPAT_HANDLER] Number of cards:', currentOPATFile.cards.size);
    
    const allTags = new Set();
    for (const card of currentOPATFile.cards.values()) {
        for (const tag of card.tableIndex.keys()) {
            allTags.add(tag);
        }
    }
    
    console.log('[OPAT_HANDLER] Found', allTags.size, 'unique tags:', Array.from(allTags));
    
    if (opatAllTagsList) {
        opatAllTagsList.innerHTML = '';
        Array.from(allTags).sort().forEach(tag => {
            const li = document.createElement('li');
            li.textContent = tag;
            opatAllTagsList.appendChild(li);
        });
        console.log('[OPAT_HANDLER] Tags list updated successfully');
    } else {
        console.error('[OPAT_HANDLER] Cannot update tags list - element still not found');
    }
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
    opatPlotting = deps.opatPlotting;
}

module.exports = {
    initializeDependencies,
    initializeOPATElements,
    initializeOPATTabs,
    resetOPATViewerState,
    handleOPATFileSelection,
    openOpatFromPath,
    displayOPATFileInfo,
    displayAllTableTags,
    populateIndexSelector,
    handleIndexVectorChange,
    displayTableData,
    closeOPATFile,
    hideAllViews,
    showCategoryHomeScreen
};
