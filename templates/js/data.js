// Конфигурация API
const API_CONFIG = {
    baseUrl: window.location.origin,
    endpoints: {
        marketData: '/api/market-data',
    },
    defaultTable: '24h'
};

// Кэш последних данных
let lastMarketData = null;

// Основная функция загрузки данных
async function fetchData() {
    try {
        const startTime = performance.now();

        const url = new URL(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.marketData}`);
        url.searchParams.set('table', API_CONFIG.defaultTable);

        const response = await fetch(url, {
            cache: 'no-store',
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const marketData = await response.json();
        console.debug(`Data fetched in ${(performance.now() - startTime).toFixed(1)}ms`);

        if (!Array.isArray(marketData) || marketData.length === 0) {
            throw new Error('Empty or invalid data received');
        }

        // Обработка данных
        const processed = processMarketData(marketData);
        lastMarketData = processed; // Сохраняем в кэш

        return processed;

    } catch (error) {
        console.error('Data fetch error:', error);

        // Пробуем вернуть кэшированные данные, если есть
        if (lastMarketData) {
            console.warn('Using cached data due to error');
            return lastMarketData;
        }

        // Показываем ошибку пользователю
        showError(`Data load failed: ${error.message}`);
        return null;
    }
}

// Функция расчета процентной разницы (добавлена)
function calculatePercentageDiff(data) {
    if (!Array.isArray(data) || data.length === 0) return [];

    // Вычисляем среднее значение для нормализации
    const sum = data.reduce((total, item) => total + item.value, 0);
    const average = sum / data.length;

    return data.map(item => ({
        time: item.time,
        value: ((item.value - average) / average) * 100
    }));
}

// Обработка рыночных данных
function processMarketData(rawData) {
    const result = {
        btc: [],
        eth: [],
        btc_as_eth: [],
        percentage_diff: []
    };

    // Первый проход: сбор основных данных
    rawData.forEach(item => {
        const time = Math.floor(new Date(item.timestamp).getTime() / 1000);
        const btc = Number(item.close_btc);
        const eth = Number(item.close_eth);

        if (!isNaN(btc)) {
            result.btc.push({ time, value: btc });
        }

        if (!isNaN(eth)) {
            result.eth.push({ time, value: eth });
        }

        if (!isNaN(btc) && !isNaN(eth) && eth !== 0) {
            result.btc_as_eth.push({ time, value: btc / eth });
        }
    });

    // Второй проход: расчет разницы
    if (result.btc_as_eth.length > 0) {
        result.percentage_diff = calculatePercentageDiff(result.btc_as_eth);
    }

    return result;
}

// Показ ошибок пользователю
function showError(message) {
    const errorEl = document.getElementById('error-message') || createErrorElement();
    errorEl.textContent = message;
    errorEl.style.display = 'block';

    setTimeout(() => {
        errorEl.style.display = 'none';
    }, 5000);
}

// Создание элемента для отображения ошибок
function createErrorElement() {
    const el = document.createElement('div');
    el.id = 'error-message';
    el.style = 'position:fixed; top:10px; right:10px; padding:15px; background:#ffebee; color:#c62828; border-radius:4px; z-index:1000;';
    document.body.appendChild(el);
    return el;
}