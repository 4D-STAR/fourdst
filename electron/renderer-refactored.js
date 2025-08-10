// === REGENERATED CODE START ===
// This file was regenerated during refactoring to use modular components
// Original functionality preserved in modular structure

const { ipcRenderer } = require('electron');

// Import all modular components
const stateManager = require('./renderer/state-manager');
const domManager = require('./renderer/dom-manager');
const bundleOperations = require('./renderer/bundle-operations');
const uiComponents = require('./renderer/ui-components');
const eventHandlers = require('./renderer/event-handlers');
const opatHandler = require('./renderer/opat-handler');
const fillWorkflow = require('./renderer/fill-workflow');

// Initialize all modules with their dependencies
function initializeModules() {
  // Create dependency object
  const deps = {
    stateManager,
    domManager,
    bundleOperations,
    uiComponents,
    eventHandlers,
    opatHandler,
    fillWorkflow
  };
  
  // Initialize each module with its dependencies
  bundleOperations.initializeDependencies(deps);
  uiComponents.initializeDependencies(deps);
  eventHandlers.initializeDependencies(deps);
  opatHandler.initializeDependencies(deps);
  fillWorkflow.initializeDependencies(deps);
  
  console.log('[RENDERER] All modules initialized with dependencies');
}

// Main initialization function
document.addEventListener('DOMContentLoaded', async () => {
  console.log('[RENDERER] Starting modular initialization...');
  
  // Initialize DOM elements first
  domManager.initializeDOMElements();
  
  // Initialize OPAT components
  opatHandler.initializeOPATElements();
  
  // Initialize all module dependencies
  initializeModules();
  
  // Initialize home screen - set home as default active category
  const homeCategory = document.querySelector('.category-item[data-category="home"]');
  const secondarySidebar = document.getElementById('secondary-sidebar');
  
  if (homeCategory) {
    homeCategory.classList.add('active');
    opatHandler.showCategoryHomeScreen('home');
    
    // Hide secondary sidebar on initial load since we start with home
    if (secondarySidebar) {
      secondarySidebar.style.display = 'none';
    }
  }
  
  // Set initial view
  domManager.showView('welcome-screen');

  // Set initial theme
  const isDarkMode = await ipcRenderer.invoke('get-dark-mode');
  document.body.classList.toggle('dark-mode', isDarkMode);

  // Setup all event listeners
  eventHandlers.setupEventListeners();
  
  console.log('[RENDERER] Modular initialization complete');
});

// Export modules for global access (for compatibility with existing code)
window.stateManager = stateManager;
window.domManager = domManager;
window.bundleOperations = bundleOperations;
window.uiComponents = uiComponents;
window.eventHandlers = eventHandlers;
window.opatHandler = opatHandler;
window.fillWorkflow = fillWorkflow;

// === REGENERATED CODE END ===
