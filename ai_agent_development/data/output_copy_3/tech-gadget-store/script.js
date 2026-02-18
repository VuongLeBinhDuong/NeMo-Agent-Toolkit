// script.js for tech-gadget-store

// Function to initialize shared components
function initializeSharedComponents() {
    // Example: Initialize navigation bar
    const navBar = document.querySelector('.navbar');
    if (navBar) {
        navBar.addEventListener('click', handleNavBarClick);
    }

    // Example: Initialize footer
    const footer = document.querySelector('.footer');
    if (footer) {
        footer.addEventListener('click', handleFooterClick);
    }

    // Example: Initialize modal dialogs
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('click', handleModalClick);
    });
}

// Event handler for navigation bar clicks
function handleNavBarClick(event) {
    // Example: Handle navigation links
    if (event.target.tagName === 'A') {
        event.preventDefault();
        console.log(`Navigating to: ${event.target.href}`);
        // Implement navigation logic here
    }
}

// Event handler for footer clicks
function handleFooterClick(event) {
    // Example: Handle footer links
    if (event.target.tagName === 'A') {
        event.preventDefault();
        console.log(`Navigating to: ${event.target.href}`);
        // Implement navigation logic here
    }
}

// Event handler for modal clicks
function handleModalClick(event) {
    // Example: Handle modal actions
    if (event.target.classList.contains('close-modal')) {
        event.preventDefault();
        console.log('Closing modal');
        // Implement modal closing logic here
    }
}

// Function to load shared assets
function loadSharedAssets() {
    // Example: Load CSS
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = '/assets/css/shared-styles.css';
    document.head.appendChild(link);

    // Example: Load JavaScript
    const script = document.createElement('script');
    script.src = '/assets/js/shared-utils.js';
    document.body.appendChild(script);
}

// Initialize the script
document.addEventListener('DOMContentLoaded', () => {
    initializeSharedComponents();
    loadSharedAssets();
});