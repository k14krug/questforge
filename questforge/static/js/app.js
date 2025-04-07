// Core application JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize loading overlay
    const loadingOverlay = document.getElementById('loading-overlay');
    
    // Show loading overlay
    window.showLoading = function() {
        loadingOverlay.classList.remove('d-none');
    };
    
    // Hide loading overlay
    window.hideLoading = function() {
        loadingOverlay.classList.add('d-none');
    };
    
    // Handle form submissions
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            showLoading();
        });
    });
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});
