// OPAT plotting module for the 4DSTAR Bundle Manager
// Handles interactive plotting functionality using Plotly.js

// Import dependencies (these will be injected when integrated)
let stateManager, domManager;

// Plotting UI elements
let plotIndexSelector, plotTableSelector, plotXAxis, plotYAxis, plotType, plotTitle;
let createPlotBtn, savePlotBtn, clearPlotBtn;
let plotContainer, plotPlaceholder, plotDisplay;

// Current plot state
let currentPlotData = null;
let currentPlotLayout = null;

// Initialize plotting UI elements
function initializePlottingElements() {
    plotIndexSelector = document.getElementById('plot-index-selector');
    plotTableSelector = document.getElementById('plot-table-selector');
    plotXAxis = document.getElementById('plot-x-axis');
    plotYAxis = document.getElementById('plot-y-axis');
    plotType = document.getElementById('plot-type');
    plotTitle = document.getElementById('plot-title');
    
    createPlotBtn = document.getElementById('create-plot-btn');
    savePlotBtn = document.getElementById('save-plot-btn');
    clearPlotBtn = document.getElementById('clear-plot-btn');
    
    plotContainer = document.getElementById('plot-container');
    plotPlaceholder = document.getElementById('plot-placeholder');
    plotDisplay = document.getElementById('plot-display');

    // Check if elements were found
    const elements = {
        plotIndexSelector, plotTableSelector, plotXAxis, plotYAxis, plotType, plotTitle,
        createPlotBtn, savePlotBtn, clearPlotBtn, plotContainer, plotPlaceholder, plotDisplay
    };
    
    const missingElements = Object.entries(elements)
        .filter(([name, element]) => !element)
        .map(([name]) => name);
    
    if (missingElements.length > 0) {
        console.warn('[OPAT_PLOTTING] Missing elements:', missingElements);
        console.warn('[OPAT_PLOTTING] Will retry initialization when needed');
        return; // Don't add event listeners if elements are missing
    }

    // Event listeners (only add if all elements are present)
    plotIndexSelector.addEventListener('change', handlePlotIndexChange);
    plotTableSelector.addEventListener('change', handlePlotTableChange);
    createPlotBtn.addEventListener('click', handleCreatePlot);
    savePlotBtn.addEventListener('click', handleSavePlot);
    clearPlotBtn.addEventListener('click', handleClearPlot);
    
    // Set up a backup event listener setup function for later use
    setupEventListenersIfNeeded();

    console.log('[OPAT_PLOTTING] All plotting elements found and initialized successfully');
}

// Setup event listeners if they weren't set up during initial initialization
function setupEventListenersIfNeeded() {
    // This function can be called later to ensure event listeners are properly set up
    // even if elements weren't available during initial setup
    
    const selectElements = {
        'plot-index-selector': handlePlotIndexChange,
        'plot-table-selector': handlePlotTableChange
    };
    
    const buttonElements = {
        'create-plot-btn': handleCreatePlot,
        'save-plot-btn': handleSavePlot,
        'clear-plot-btn': handleClearPlot
    };
    
    // Add change listeners to select elements
    for (const [elementId, handler] of Object.entries(selectElements)) {
        const element = document.getElementById(elementId);
        if (element && !element.hasAttribute('data-plotting-change-listener')) {
            element.addEventListener('change', handler);
            element.setAttribute('data-plotting-change-listener', 'true');
            console.log(`[OPAT_PLOTTING] Added change listener to ${elementId}`);
        }
    }
    
    // Add click listeners to button elements
    for (const [elementId, handler] of Object.entries(buttonElements)) {
        const element = document.getElementById(elementId);
        if (element && !element.hasAttribute('data-plotting-click-listener')) {
            element.addEventListener('click', handler);
            element.setAttribute('data-plotting-click-listener', 'true');
            console.log(`[OPAT_PLOTTING] Added click listener to ${elementId}`);
        }
    }
}

// Populate plot index selector when OPAT file is loaded
function populatePlotIndexSelector() {
    console.log('[OPAT_PLOTTING] populatePlotIndexSelector called');
    
    // Always try to find the element fresh, in case it wasn't available during initial setup
    const selector = document.getElementById('plot-index-selector');
    if (!selector) {
        console.error('[OPAT_PLOTTING] Could not find plot-index-selector element in DOM');
        return;
    }
    
    // Update our reference
    plotIndexSelector = selector;

    const opatFile = stateManager.getOPATFile();
    if (!opatFile) {
        console.warn('[OPAT_PLOTTING] No OPAT file available');
        plotIndexSelector.innerHTML = '<option value="">-- No OPAT file loaded --</option>';
        return;
    }

    console.log('[OPAT_PLOTTING] OPAT file found with', opatFile.cards.size, 'cards');
    plotIndexSelector.innerHTML = '<option value="">-- Select an Index Vector --</option>';
    
    let optionCount = 0;
    for (const [indexName, card] of opatFile.cards) {
        const option = document.createElement('option');
        option.value = indexName;
        option.textContent = `${indexName} (${card.tableData.size} tables)`;
        plotIndexSelector.appendChild(option);
        optionCount++;
        console.log('[OPAT_PLOTTING] Added option:', indexName);
    }

    console.log(`[OPAT_PLOTTING] Successfully populated ${optionCount} index vectors`);
    
    // Also initialize other selectors if they weren't found during initial setup
    if (!plotTableSelector) {
        plotTableSelector = document.getElementById('plot-table-selector');
    }
    if (!plotXAxis) {
        plotXAxis = document.getElementById('plot-x-axis');
    }
    if (!plotYAxis) {
        plotYAxis = document.getElementById('plot-y-axis');
    }
    
    // Ensure event listeners are set up
    ensureEventListenersAreSetup();
}

// Ensure event listeners are properly set up (called when needed)
function ensureEventListenersAreSetup() {
    console.log('[OPAT_PLOTTING] Ensuring event listeners are set up');
    
    // Check and set up index selector listener
    const indexSelector = document.getElementById('plot-index-selector');
    if (indexSelector && !indexSelector.hasAttribute('data-plotting-change-listener')) {
        indexSelector.addEventListener('change', handlePlotIndexChange);
        indexSelector.setAttribute('data-plotting-change-listener', 'true');
        console.log('[OPAT_PLOTTING] Added change listener to plot-index-selector');
    }
    
    // Check and set up table selector listener
    const tableSelector = document.getElementById('plot-table-selector');
    if (tableSelector && !tableSelector.hasAttribute('data-plotting-change-listener')) {
        tableSelector.addEventListener('change', handlePlotTableChange);
        tableSelector.setAttribute('data-plotting-change-listener', 'true');
        console.log('[OPAT_PLOTTING] Added change listener to plot-table-selector');
    }
    
    // Check and set up create plot button listener
    const createPlotBtn = document.getElementById('create-plot-btn');
    if (createPlotBtn && !createPlotBtn.hasAttribute('data-plotting-click-listener')) {
        createPlotBtn.addEventListener('click', handleCreatePlot);
        createPlotBtn.setAttribute('data-plotting-click-listener', 'true');
        console.log('[OPAT_PLOTTING] Added click listener to create-plot-btn');
    }
    
    // Check and set up save plot button listener
    const savePlotBtn = document.getElementById('save-plot-btn');
    if (savePlotBtn && !savePlotBtn.hasAttribute('data-plotting-click-listener')) {
        savePlotBtn.addEventListener('click', handleSavePlot);
        savePlotBtn.setAttribute('data-plotting-click-listener', 'true');
        console.log('[OPAT_PLOTTING] Added click listener to save-plot-btn');
    }
    
    // Update our references
    if (indexSelector) plotIndexSelector = indexSelector;
    if (tableSelector) plotTableSelector = tableSelector;
    if (createPlotBtn) createPlotButton = createPlotBtn;
    if (savePlotBtn) savePlotButton = savePlotBtn;
}

// Handle index vector selection change
function handlePlotIndexChange() {
    console.log('[OPAT_PLOTTING] handlePlotIndexChange called');
    
    // Ensure we have references to the elements
    if (!plotIndexSelector) plotIndexSelector = document.getElementById('plot-index-selector');
    if (!plotTableSelector) plotTableSelector = document.getElementById('plot-table-selector');
    if (!plotXAxis) plotXAxis = document.getElementById('plot-x-axis');
    if (!plotYAxis) plotYAxis = document.getElementById('plot-y-axis');
    
    if (!plotIndexSelector || !plotTableSelector || !plotXAxis || !plotYAxis) {
        console.error('[OPAT_PLOTTING] Missing required elements for index change');
        return;
    }

    const selectedIndex = plotIndexSelector.value;
    console.log('[OPAT_PLOTTING] Selected index:', selectedIndex);
    
    plotTableSelector.innerHTML = '<option value="">-- Select a Table --</option>';
    plotXAxis.innerHTML = '<option value="">-- Select X Variable --</option>';
    plotYAxis.innerHTML = '<option value="">-- Select Y Variable --</option>';

    if (!selectedIndex) {
        console.log('[OPAT_PLOTTING] No index selected, returning');
        return;
    }

    const opatFile = stateManager.getOPATFile();
    if (!opatFile) return;

    const card = opatFile.cards.get(selectedIndex);
    if (!card) return;

    // Populate table selector
    for (const [tableName, tableData] of card.tableData) {
        const option = document.createElement('option');
        option.value = tableName;
        option.textContent = `${tableName} (${tableData.N_R}×${tableData.N_C})`;
        plotTableSelector.appendChild(option);
    }

    console.log(`[OPAT_PLOTTING] Populated ${card.tableData.size} tables for index ${selectedIndex}`);
}

// Handle table selection change
function handlePlotTableChange() {
    console.log('[OPAT_PLOTTING] handlePlotTableChange called');
    
    // Ensure we have references to the elements
    if (!plotIndexSelector) plotIndexSelector = document.getElementById('plot-index-selector');
    if (!plotTableSelector) plotTableSelector = document.getElementById('plot-table-selector');
    if (!plotXAxis) plotXAxis = document.getElementById('plot-x-axis');
    if (!plotYAxis) plotYAxis = document.getElementById('plot-y-axis');
    
    if (!plotIndexSelector || !plotTableSelector || !plotXAxis || !plotYAxis) {
        console.error('[OPAT_PLOTTING] Missing required elements for table change');
        return;
    }

    const selectedIndex = plotIndexSelector.value;
    const selectedTable = plotTableSelector.value;
    
    console.log('[OPAT_PLOTTING] Selected index:', selectedIndex, 'Selected table:', selectedTable);
    
    plotXAxis.innerHTML = '<option value="">-- Select X Variable --</option>';
    plotYAxis.innerHTML = '<option value="">-- Select Y Variable --</option>';

    if (!selectedIndex || !selectedTable) {
        console.log('[OPAT_PLOTTING] No index or table selected, returning');
        return;
    }

    const opatFile = stateManager.getOPATFile();
    if (!opatFile) {
        console.error('[OPAT_PLOTTING] No OPAT file available');
        return;
    }

    const card = opatFile.cards.get(selectedIndex);
    if (!card) {
        console.error('[OPAT_PLOTTING] Card not found for index:', selectedIndex);
        return;
    }

    const tableData = card.tableData.get(selectedTable);
    if (!tableData) {
        console.error('[OPAT_PLOTTING] Table data not found for table:', selectedTable);
        return;
    }

    // Get the table index entry for names
    const tableIndexEntry = card.tableIndex.get(selectedTable);
    if (!tableIndexEntry) {
        console.error('[OPAT_PLOTTING] Table index entry not found for table:', selectedTable);
        return;
    }

    console.log('[OPAT_PLOTTING] Table info:', {
        rowName: tableIndexEntry.rowName,
        columnName: tableIndexEntry.columnName,
        numRows: tableData.N_R,
        numColumns: tableData.N_C,
        rowValuesLength: tableData.rowValues?.length,
        columnValuesLength: tableData.columnValues?.length
    });

    // Populate axis selectors with row and column values
    const variables = [];
    
    // Add row values as the primary option (typically the independent variable)
    if (tableData.rowValues && tableData.rowValues.length > 0) {
        const rowName = tableIndexEntry.rowName.trim() || 'Row Values';
        variables.push({ 
            name: rowName, 
            value: '__row_values__',
            isDefault: true,
            type: 'row'
        });
    }
    
    // Add column values as the secondary option
    if (tableData.columnValues && tableData.columnValues.length > 0) {
        const columnName = tableIndexEntry.columnName.trim() || 'Column Values';
        variables.push({ 
            name: columnName, 
            value: '__column_values__',
            isDefault: true,
            type: 'column'
        });
    }
    
    // Add individual row options with their actual values
    if (tableData.rowValues && tableData.rowValues.length > 0) {
        const rowName = tableIndexEntry.rowName.trim() || 'Row';
        for (let i = 0; i < Math.min(tableData.rowValues.length, 20); i++) { // Limit to 20 for UI performance
            const value = tableData.rowValues[i];
            const displayValue = typeof value === 'number' ? value.toPrecision(4) : value;
            variables.push({
                name: `Data Row ${i + 1} (${rowName} = ${displayValue})`,
                value: `row_${i}`,
                isDefault: false,
                type: 'row_data',
                index: i
            });
        }
    }
    
    // Add individual column options with their actual values
    if (tableData.columnValues && tableData.columnValues.length > 0) {
        const columnName = tableIndexEntry.columnName.trim() || 'Column';
        for (let i = 0; i < Math.min(tableData.columnValues.length, 20); i++) { // Limit to 20 for UI performance
            const value = tableData.columnValues[i];
            const displayValue = typeof value === 'number' ? value.toPrecision(4) : value;
            variables.push({
                name: `Data Column ${i + 1} (${columnName} = ${displayValue})`,
                value: `col_${i}`,
                isDefault: false,
                type: 'column_data',
                index: i
            });
        }
    }
    
    // Add data columns as additional options (for accessing the actual table data)
    for (let i = 0; i < Math.min(tableData.N_C, 10); i++) { // Limit for UI performance
        variables.push({ 
            name: `Table Data Column ${i + 1}`, 
            value: `data_col_${i}`,
            isDefault: false,
            type: 'data'
        });
    }

    // Populate the select elements
    variables.forEach((variable, index) => {
        const xOption = document.createElement('option');
        xOption.value = variable.value;
        xOption.textContent = variable.name;
        plotXAxis.appendChild(xOption);

        const yOption = document.createElement('option');
        yOption.value = variable.value;
        yOption.textContent = variable.name;
        plotYAxis.appendChild(yOption);
    });

    // Set default selections: row values for X-axis, column values for Y-axis
    const rowVariable = variables.find(v => v.type === 'row');
    const columnVariable = variables.find(v => v.type === 'column');
    
    if (rowVariable) {
        plotXAxis.value = rowVariable.value;
        console.log('[OPAT_PLOTTING] Set default X-axis to:', rowVariable.name);
    }
    
    if (columnVariable) {
        plotYAxis.value = columnVariable.value;
        console.log('[OPAT_PLOTTING] Set default Y-axis to:', columnVariable.name);
    }

    console.log(`[OPAT_PLOTTING] Populated ${variables.length} variables for table ${selectedTable}`);
}

// Handle create plot button click
async function handleCreatePlot() {
    console.log('[OPAT_PLOTTING] handleCreatePlot called');
    
    // Ensure we have references to all elements
    if (!plotIndexSelector) plotIndexSelector = document.getElementById('plot-index-selector');
    if (!plotTableSelector) plotTableSelector = document.getElementById('plot-table-selector');
    if (!plotXAxis) plotXAxis = document.getElementById('plot-x-axis');
    if (!plotYAxis) plotYAxis = document.getElementById('plot-y-axis');
    if (!plotType) plotType = document.getElementById('plot-type');
    if (!plotTitle) plotTitle = document.getElementById('plot-title');
    
    if (!plotIndexSelector || !plotTableSelector || !plotXAxis || !plotYAxis || !plotType || !plotTitle) {
        console.error('[OPAT_PLOTTING] Missing required elements for plot creation');
        return;
    }

    const selectedIndex = plotIndexSelector.value;
    const selectedTable = plotTableSelector.value;
    const xVariable = plotXAxis.value;
    const yVariable = plotYAxis.value;
    const plotTypeValue = plotType.value;
    const titleText = plotTitle.value || 'OPAT Data Plot';

    console.log('[OPAT_PLOTTING] Plot parameters:', {
        selectedIndex, selectedTable, xVariable, yVariable, plotTypeValue, titleText
    });

    if (!selectedIndex || !selectedTable || !xVariable || !yVariable) {
        console.warn('[OPAT_PLOTTING] Missing required fields');
        alert('Please select all required fields (Index Vector, Table, X-Axis, Y-Axis)');
        return;
    }

    try {
        domManager.showSpinner();
        
        // Get button references
        const createBtn = document.getElementById('create-plot-btn');
        const saveBtn = document.getElementById('save-plot-btn');
        const clearBtn = document.getElementById('clear-plot-btn');
        
        if (createBtn) createBtn.disabled = true;

        const plotData = await generatePlotData(selectedIndex, selectedTable, xVariable, yVariable, plotTypeValue);
        const layout = generatePlotLayout(titleText, xVariable, yVariable);

        await createPlotlyPlot(plotData, layout);

        // Enable save and clear buttons
        if (saveBtn) saveBtn.disabled = false;
        if (clearBtn) clearBtn.disabled = false;

        console.log('[OPAT_PLOTTING] Plot created successfully');
    } catch (error) {
        console.error('[OPAT_PLOTTING] Error creating plot:', error);
        alert('Error creating plot: ' + error.message);
    } finally {
        domManager.hideSpinner();
        const createBtn = document.getElementById('create-plot-btn');
        if (createBtn) createBtn.disabled = false;
    }
}

// Generate plot data from OPAT table
async function generatePlotData(indexName, tableName, xVariable, yVariable, plotTypeValue) {
    const opatFile = stateManager.getOPATFile();
    const card = opatFile.cards.get(indexName);
    const tableData = card.tableData.get(tableName);

    const xData = extractVariableData(tableData, xVariable);
    const yData = extractVariableData(tableData, yVariable);

    let trace;
    
    switch (plotTypeValue) {
        case 'scatter':
            trace = {
                x: xData,
                y: yData,
                mode: 'markers',
                type: 'scatter',
                marker: {
                    color: '#3b82f6',
                    size: 6,
                    opacity: 0.7
                },
                name: `${tableName}`
            };
            break;
            
        case 'line':
            trace = {
                x: xData,
                y: yData,
                mode: 'lines+markers',
                type: 'scatter',
                line: {
                    color: '#3b82f6',
                    width: 2
                },
                marker: {
                    color: '#3b82f6',
                    size: 4
                },
                name: `${tableName}`
            };
            break;
            
        case 'heatmap':
            // For heatmap, we need 2D data
            const zData = reshapeDataForHeatmap(tableData);
            trace = {
                z: zData,
                type: 'heatmap',
                colorscale: 'Viridis',
                name: `${tableName}`
            };
            break;
            
        case 'contour':
            // For contour, we need 2D data
            const contourData = reshapeDataForHeatmap(tableData);
            trace = {
                z: contourData,
                type: 'contour',
                colorscale: 'Viridis',
                name: `${tableName}`
            };
            break;
            
        default:
            throw new Error(`Unsupported plot type: ${plotTypeValue}`);
    }

    return [trace];
}

// Extract variable data from table
function extractVariableData(tableData, variable) {
    console.log('[OPAT_PLOTTING] Extracting variable data for:', variable);
    
    // Extract row values (the actual row axis values from the OPAT table)
    if (variable === '__row_values__') {
        if (tableData.rowValues && tableData.rowValues.length > 0) {
            console.log('[OPAT_PLOTTING] Using row values, length:', tableData.rowValues.length);
            return Array.from(tableData.rowValues);
        } else {
            console.warn('[OPAT_PLOTTING] No row values available, using indices');
            return Array.from({ length: tableData.N_R }, (_, i) => i);
        }
    }
    
    // Extract column values (the actual column axis values from the OPAT table)
    if (variable === '__column_values__') {
        if (tableData.columnValues && tableData.columnValues.length > 0) {
            console.log('[OPAT_PLOTTING] Using column values, length:', tableData.columnValues.length);
            return Array.from(tableData.columnValues);
        } else {
            console.warn('[OPAT_PLOTTING] No column values available, using indices');
            return Array.from({ length: tableData.N_C }, (_, i) => i);
        }
    }
    
    // Legacy support for row/column indices
    if (variable === '__row_index__') {
        return Array.from({ length: tableData.N_R }, (_, i) => i);
    }
    
    if (variable === '__col_index__') {
        return Array.from({ length: tableData.N_C }, (_, i) => i);
    }
    
    // Extract data from a specific row (all columns for that row)
    if (variable.startsWith('row_')) {
        const rowIndex = parseInt(variable.split('_')[1]);
        console.log('[OPAT_PLOTTING] Extracting data from row:', rowIndex);
        const data = [];
        
        for (let col = 0; col < tableData.N_C; col++) {
            try {
                const value = tableData.getValue(rowIndex, col, 0); // Use getValue method like OPAT explorer
                data.push(typeof value === 'number' ? value : parseFloat(value) || 0);
            } catch (error) {
                console.warn('[OPAT_PLOTTING] Error extracting data at row', rowIndex, 'col', col, ':', error);
                data.push(0);
            }
        }
        
        return data;
    }
    
    // Extract data from a specific column (all rows for that column)
    if (variable.startsWith('col_')) {
        const colIndex = parseInt(variable.split('_')[1]);
        console.log('[OPAT_PLOTTING] Extracting data from column:', colIndex);
        const data = [];
        
        for (let row = 0; row < tableData.N_R; row++) {
            try {
                const value = tableData.getValue(row, colIndex, 0); // Use getValue method like OPAT explorer
                data.push(typeof value === 'number' ? value : parseFloat(value) || 0);
            } catch (error) {
                console.warn('[OPAT_PLOTTING] Error extracting data at row', row, 'col', colIndex, ':', error);
                data.push(0);
            }
        }
        
        return data;
    }

    // Extract data from specific data columns (legacy table data access)
    if (variable.startsWith('data_col_')) {
        const colIndex = parseInt(variable.split('_')[2]);
        console.log('[OPAT_PLOTTING] Extracting data column:', colIndex);
        const data = [];
        
        for (let row = 0; row < tableData.N_R; row++) {
            try {
                const value = tableData.getValue(row, colIndex, 0); // Use getValue method like OPAT explorer
                data.push(typeof value === 'number' ? value : parseFloat(value) || 0);
            } catch (error) {
                console.warn('[OPAT_PLOTTING] Error extracting data at row', row, 'col', colIndex, ':', error);
                data.push(0);
            }
        }
        
        return data;
    }
    
    throw new Error(`Unknown variable: ${variable}`);
}

// Reshape data for heatmap/contour plots
function reshapeDataForHeatmap(tableData) {
    const data = [];
    for (let row = 0; row < Math.min(tableData.N_R, 50); row++) { // Limit for performance
        const rowData = [];
        for (let col = 0; col < Math.min(tableData.N_C, 50); col++) {
            try {
                const value = tableData.getValue(row, col, 0); // Use getValue method like OPAT explorer
                rowData.push(typeof value === 'number' ? value : parseFloat(value) || 0);
            } catch (error) {
                rowData.push(0);
            }
        }
        data.push(rowData);
    }
    return data;
}

// Generate plot layout
function generatePlotLayout(title, xVariable, yVariable) {
    const isDarkMode = document.body.classList.contains('dark-mode');
    
    return {
        title: {
            text: title,
            font: {
                color: isDarkMode ? '#f3f4f6' : '#1f2937',
                size: 16
            }
        },
        xaxis: {
            title: {
                text: formatVariableName(xVariable),
                font: {
                    color: isDarkMode ? '#d1d5db' : '#374151'
                }
            },
            tickfont: {
                color: isDarkMode ? '#9ca3af' : '#6b7280'
            },
            gridcolor: isDarkMode ? '#4b5563' : '#e5e7eb'
        },
        yaxis: {
            title: {
                text: formatVariableName(yVariable),
                font: {
                    color: isDarkMode ? '#d1d5db' : '#374151'
                }
            },
            tickfont: {
                color: isDarkMode ? '#9ca3af' : '#6b7280'
            },
            gridcolor: isDarkMode ? '#4b5563' : '#e5e7eb'
        },
        plot_bgcolor: isDarkMode ? '#374151' : 'white',
        paper_bgcolor: isDarkMode ? '#374151' : 'white',
        font: {
            color: isDarkMode ? '#f3f4f6' : '#1f2937'
        },
        margin: { t: 50, r: 50, b: 50, l: 50 }
    };
}

// Format variable name for display
function formatVariableName(variable) {
    if (variable === '__row_index__') return 'Row Index';
    if (variable === '__col_index__') return 'Column Index';
    if (variable.startsWith('col_')) {
        const colIndex = parseInt(variable.split('_')[1]);
        return `Column ${colIndex + 1}`;
    }
    return variable;
}

// Create Plotly plot
async function createPlotlyPlot(data, layout) {
    console.log('[OPAT_PLOTTING] createPlotlyPlot called');
    
    currentPlotData = data;
    currentPlotLayout = layout;

    // Get DOM elements
    const placeholder = document.getElementById('plot-placeholder');
    const display = document.getElementById('plot-display');
    
    if (!placeholder || !display) {
        console.error('[OPAT_PLOTTING] Missing plot container elements');
        throw new Error('Plot container elements not found');
    }

    // Hide placeholder and show plot display
    placeholder.classList.add('hidden');
    display.classList.remove('hidden');

    // Create the plot
    await Plotly.newPlot(display, data, layout, {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToAdd: ['downloadImage'],
        toImageButtonOptions: {
            format: 'png',
            filename: 'opat_plot',
            height: 500,
            width: 700,
            scale: 2
        }
    });
}

// Handle save plot button click
async function handleSavePlot() {
    if (!currentPlotData || !currentPlotLayout) {
        alert('No plot to save');
        return;
    }

    try {
        // Use Plotly's built-in download functionality
        const filename = plotTitle.value ? 
            plotTitle.value.replace(/[^a-z0-9]/gi, '_').toLowerCase() : 
            'opat_plot';

        await Plotly.downloadImage(plotDisplay, {
            format: 'png',
            width: 1200,
            height: 800,
            filename: filename
        });

        console.log('[OPAT_PLOTTING] Plot saved as PNG');
    } catch (error) {
        console.error('[OPAT_PLOTTING] Error saving plot:', error);
        alert('Error saving plot: ' + error.message);
    }
}

// Handle clear plot button click
function handleClearPlot() {
    if (plotDisplay && currentPlotData) {
        Plotly.purge(plotDisplay);
    }

    currentPlotData = null;
    currentPlotLayout = null;

    // Show placeholder and hide plot display (with null checks)
    if (plotDisplay) {
        plotDisplay.classList.add('hidden');
    }
    if (plotPlaceholder) {
        plotPlaceholder.classList.remove('hidden');
    }

    // Disable save and clear buttons (with null checks)
    if (savePlotBtn) {
        savePlotBtn.disabled = true;
    }
    if (clearPlotBtn) {
        clearPlotBtn.disabled = true;
    }

    console.log('[OPAT_PLOTTING] Plot cleared');
}

// Reset plotting state when OPAT file changes
function resetPlottingState() {
    handleClearPlot();
    
    // Reset selectors with null checks
    if (plotIndexSelector) {
        plotIndexSelector.innerHTML = '<option value="">-- Select an Index Vector --</option>';
    }
    if (plotTableSelector) {
        plotTableSelector.innerHTML = '<option value="">-- Select a Table --</option>';
    }
    if (plotXAxis) {
        plotXAxis.innerHTML = '<option value="">-- Select X Variable --</option>';
    }
    if (plotYAxis) {
        plotYAxis.innerHTML = '<option value="">-- Select Y Variable --</option>';
    }
    if (plotTitle) {
        plotTitle.value = '';
    }

    console.log('[OPAT_PLOTTING] Plotting state reset');
}

// Initialize dependencies (called when module is loaded)
function initializePlottingDependencies(deps) {
    stateManager = deps.stateManager;
    domManager = deps.domManager;
}

module.exports = {
    initializePlottingDependencies,
    initializePlottingElements,
    populatePlotIndexSelector,
    handlePlotIndexChange,
    handlePlotTableChange,
    handleCreatePlot,
    handleSavePlot,
    handleClearPlot,
    resetPlottingState
};
