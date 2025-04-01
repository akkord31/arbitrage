const API_CONFIG = {
    baseUrl: window.location.origin,
    endpoints: {
        processedData: '/api/processed-data',
    },
    defaultTable: '24h'
};

let lastMarketData = null;

async function fetchData() {
    try {
        const url = new URL(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.processedData}`);
        url.searchParams.set('table', API_CONFIG.defaultTable);

        const response = await fetch(url, {
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        if (!data || typeof data !== 'object') {
            throw new Error('Invalid data structure');
        }

        lastMarketData = data;
        return data;

    } catch (error) {
        console.error('Data fetch error:', error);

        if (lastMarketData) {
            console.warn('Using cached data');
            return lastMarketData;
        }
        
        showError(`Data load failed: ${error.message}`);
        return null;
    }
}