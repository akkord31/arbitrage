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
        // Добавляем случайный параметр для избежания кеширования
        const url = `/api/processed-data?_=${Date.now()}`;
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (!data || !data.btc || !data.eth) {
            throw new Error("Invalid data format received");
        }

        localStorage.setItem('avg_ratio_24h', String(data.avg_ratio_24h));
        localStorage.setItem('avg_ratio_180d', String(data.avg_ratio_180d));
        localStorage.setItem('btcMin', String(data.btc_as_eth_min));
        localStorage.setItem('btcMax', String(data.btc_as_eth_max));
        localStorage.setItem('ethMin', String(data.eth_min));
        localStorage.setItem('ethMax', String(data.eth_max));

        return data;

    } catch (error) {
        console.error('Data fetch error:', error);

        // Показываем пользователю сообщение об ошибке
        showError('Ошибка загрузки данных. Попробуйте обновить страницу.');

        // Возвращаем null вместо выброса ошибки
        return null;
    }
}
