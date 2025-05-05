/**
 * Signal filtering and management JavaScript
 */
document.addEventListener('DOMContentLoaded', function() {
    // Signal type filtering
    const signalTypeButtons = document.querySelectorAll('#signalTypeFilter button');
    const strategyFilter = document.getElementById('strategyFilter');
    const signalRows = document.querySelectorAll('.signal-row');
    
    // Add click event listeners to signal type buttons
    signalTypeButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            signalTypeButtons.forEach(btn => btn.classList.remove('active'));
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Get the filter value
            const filterValue = this.getAttribute('data-filter');
            
            // Apply filtering
            applyFilters(filterValue, strategyFilter.value);
        });
    });
    
    // Add change event listener to strategy filter
    if (strategyFilter) {
        strategyFilter.addEventListener('change', function() {
            // Get current signal type filter
            const activeButton = document.querySelector('#signalTypeFilter button.active');
            const signalTypeFilter = activeButton ? activeButton.getAttribute('data-filter') : 'all';
            
            // Apply filtering
            applyFilters(signalTypeFilter, this.value);
        });
    }
    
    // Function to apply both filters
    function applyFilters(signalType, strategy) {
        signalRows.forEach(row => {
            const rowSignalType = row.getAttribute('data-signal-type');
            const rowStrategy = row.getAttribute('data-strategy');
            
            // Check if row matches both filters
            const matchesSignalType = signalType === 'all' || rowSignalType === signalType;
            const matchesStrategy = strategy === 'all' || rowStrategy === strategy;
            
            // Show or hide the row
            if (matchesSignalType && matchesStrategy) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }
});
