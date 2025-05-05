/**
 * Trades filtering and management JavaScript
 */
document.addEventListener('DOMContentLoaded', function() {
    // Trade type filtering 
    const tradeTypeButtons = document.querySelectorAll('#tradeTypeFilter button');
    const tradingModeButtons = document.querySelectorAll('#tradingModeFilter button');
    const exchangeFilter = document.getElementById('exchangeFilter');
    const tradeRows = document.querySelectorAll('.trade-row');
    
    // Add click event listeners to trade type buttons
    tradeTypeButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            tradeTypeButtons.forEach(btn => btn.classList.remove('active'));
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Get the filter value
            const filterValue = this.getAttribute('data-filter');
            
            // Apply filtering
            applyFilters(
                filterValue, 
                document.querySelector('#tradingModeFilter button.active').getAttribute('data-filter'),
                exchangeFilter.value
            );
        });
    });
    
    // Add click event listeners to trading mode buttons
    tradingModeButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            tradingModeButtons.forEach(btn => btn.classList.remove('active'));
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Get the filter value
            const filterValue = this.getAttribute('data-filter');
            
            // Apply filtering
            applyFilters(
                document.querySelector('#tradeTypeFilter button.active').getAttribute('data-filter'),
                filterValue,
                exchangeFilter.value
            );
        });
    });
    
    // Add change event listener to exchange filter
    if (exchangeFilter) {
        exchangeFilter.addEventListener('change', function() {
            // Get current filters
            const tradeTypeFilter = document.querySelector('#tradeTypeFilter button.active').getAttribute('data-filter');
            const tradingModeFilter = document.querySelector('#tradingModeFilter button.active').getAttribute('data-filter');
            
            // Apply filtering
            applyFilters(tradeTypeFilter, tradingModeFilter, this.value);
        });
    }
    
    // Function to apply all filters
    function applyFilters(tradeType, tradingMode, exchange) {
        tradeRows.forEach(row => {
            const rowSide = row.getAttribute('data-side');
            const rowMode = row.getAttribute('data-mode');
            const rowExchange = row.getAttribute('data-exchange');
            
            // Check if row matches all filters
            const matchesTradeType = tradeType === 'all' || rowSide === tradeType;
            const matchesTradingMode = tradingMode === 'all' || rowMode === tradingMode;
            const matchesExchange = exchange === 'all' || rowExchange === exchange;
            
            // Show or hide the row
            if (matchesTradeType && matchesTradingMode && matchesExchange) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }
});
