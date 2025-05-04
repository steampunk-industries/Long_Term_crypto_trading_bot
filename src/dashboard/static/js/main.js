/**
 * Main JavaScript file for the Crypto Trading Bot Dashboard
 */

// Global error handler to log errors to console and show user-friendly messages
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    showErrorMessage('An error occurred. Please check the console for details.');
    return false;
});

// Utility function to show error messages
function showErrorMessage(message, duration = 5000) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Find alert container or create one if it doesn't exist
    let alertContainer = document.getElementById('alert-container');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.id = 'alert-container';
        alertContainer.className = 'container mt-3';
        const mainContent = document.querySelector('main') || document.body;
        mainContent.prepend(alertContainer);
    }
    
    alertContainer.appendChild(alertDiv);
    
    // Auto dismiss after duration
    if (duration > 0) {
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.classList.remove('show');
                setTimeout(() => alertDiv.parentNode.removeChild(alertDiv), 300);
            }
        }, duration);
    }
}

// Initialize Bootstrap components
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    const popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    console.log('Dashboard initialized successfully');
});

// API utilities
const API = {
    /**
     * Make an API request with error handling
     * @param {string} endpoint - API endpoint to call
     * @param {Object} options - Fetch options
     * @returns {Promise<Object>} - Promise resolving to response JSON
     */
    async fetch(endpoint, options = {}) {
        try {
            // Add default options for API requests
            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            };
            
            const response = await fetch(endpoint, {...defaultOptions, ...options});
            
            if (!response.ok) {
                throw new Error(`API request failed: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            return data;
        } catch (error) {
            console.error(`Error fetching ${endpoint}:`, error);
            showErrorMessage(`API Error: ${error.message}`);
            throw error;
        }
    },
    
    /**
     * Get portfolio data
     * @returns {Promise<Object>} - Promise resolving to portfolio data
     */
    async getPortfolioData() {
        return this.fetch('/api/portfolio_data');
    },
    
    /**
     * Get recent trades
     * @returns {Promise<Object>} - Promise resolving to recent trades
     */
    async getRecentTrades() {
        return this.fetch('/api/recent_trades');
    },
    
    /**
     * Get recent signals
     * @returns {Promise<Object>} - Promise resolving to recent signals
     */
    async getRecentSignals() {
        return this.fetch('/api/recent_signals');
    },
    
    /**
     * Get asset data
     * @returns {Promise<Object>} - Promise resolving to asset data
     */
    async getAssets() {
        return this.fetch('/api/assets');
    },
    
    /**
     * Get exchange info
     * @returns {Promise<Object>} - Promise resolving to exchange info
     */
    async getExchangeInfo() {
        return this.fetch('/api/exchange_info');
    },
    
    /**
     * Get available strategies
     * @returns {Promise<Object>} - Promise resolving to available strategies
     */
    async getStrategies() {
        return this.fetch('/api/strategies');
    }
};

// Data refresh functions
function setupDataRefresh() {
    // Refresh portfolio data
    function refreshPortfolioData() {
        const portfolioChart = document.getElementById('portfolioChart');
        if (portfolioChart) {
            API.getPortfolioData()
                .then(data => {
                    // Update chart if applicable
                    console.log('Portfolio data refreshed:', data);
                })
                .catch(error => {
                    console.error('Failed to refresh portfolio data:', error);
                });
        }
    }
    
    // Refresh recent trades
    function refreshRecentTrades() {
        const tradesTable = document.getElementById('recentTradesTable');
        if (tradesTable) {
            API.getRecentTrades()
                .then(data => {
                    const tbody = tradesTable.querySelector('tbody');
                    if (!tbody) return;
                    
                    // Clear existing rows
                    tbody.innerHTML = '';
                    
                    // Add new rows
                    data.forEach(trade => {
                        const date = new Date(trade.timestamp);
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${date.toLocaleString()}</td>
                            <td>${trade.symbol}</td>
                            <td class="${trade.side === 'buy' ? 'text-success' : 'text-danger'}">${trade.side.toUpperCase()}</td>
                            <td>${parseFloat(trade.amount).toFixed(4)}</td>
                            <td>$${parseFloat(trade.price).toFixed(2)}</td>
                            <td>$${parseFloat(trade.value).toFixed(2)}</td>
                            <td>${trade.strategy}</td>
                        `;
                        tbody.appendChild(row);
                    });
                    
                    console.log('Recent trades refreshed:', data);
                })
                .catch(error => {
                    console.error('Failed to refresh recent trades:', error);
                });
        }
    }
    
    // Refresh recent signals
    function refreshRecentSignals() {
        const signalsTable = document.getElementById('recentSignalsTable');
        if (signalsTable) {
            API.getRecentSignals()
                .then(data => {
                    const tbody = signalsTable.querySelector('tbody');
                    if (!tbody) return;
                    
                    // Clear existing rows
                    tbody.innerHTML = '';
                    
                    // Add new rows
                    data.forEach(signal => {
                        const date = new Date(signal.timestamp);
                        const row = document.createElement('tr');
                        
                        // Set signal type color
                        let signalTypeClass = 'text-secondary';
                        if (signal.signal_type === 'buy') signalTypeClass = 'text-success';
                        if (signal.signal_type === 'sell') signalTypeClass = 'text-danger';
                        
                        row.innerHTML = `
                            <td>${date.toLocaleString()}</td>
                            <td>${signal.symbol}</td>
                            <td class="${signalTypeClass}">${signal.signal_type.toUpperCase()}</td>
                            <td>${parseFloat(signal.confidence * 100).toFixed(0)}%</td>
                            <td>$${parseFloat(signal.price).toFixed(2)}</td>
                            <td>${signal.strategy}</td>
                            <td>${signal.executed ? '<span class="badge bg-success">Yes</span>' : '<span class="badge bg-secondary">No</span>'}</td>
                        `;
                        tbody.appendChild(row);
                    });
                    
                    console.log('Recent signals refreshed:', data);
                })
                .catch(error => {
                    console.error('Failed to refresh recent signals:', error);
                });
        }
    }
    
    // Initialize all refreshes
    function initializeRefreshes() {
        refreshPortfolioData();
        refreshRecentTrades();
        refreshRecentSignals();
        
        // Set up periodic refreshes
        setInterval(refreshPortfolioData, 60000); // Every 1 minute
        setInterval(refreshRecentTrades, 30000);  // Every 30 seconds
        setInterval(refreshRecentSignals, 30000); // Every 30 seconds
        
        console.log('Data refresh initialized');
    }
    
    // Call initialize if DOM is already loaded, otherwise wait for DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeRefreshes);
    } else {
        initializeRefreshes();
    }
}

// Initialize data refresh if on dashboard pages
if (window.location.pathname === '/' || window.location.pathname === '/index') {
    setupDataRefresh();
}

// Console welcome message
console.log('✨ Crypto Trading Bot Dashboard loaded ✨');
console.log('Version: 1.0.0');
console.log('Environment:', window.location.hostname === 'localhost' ? 'Development' : 'Production');
