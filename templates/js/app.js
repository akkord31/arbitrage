// Глобальные переменные для хранения экземпляров графиков
const chartInstances = {};
const BTC_COLOR = "#FF9900"
const ETH_COLOR = "#627EEA"
async function initApp() {
    try {
        // 1. Проверяем наличие всех контейнеров для графиков
        const requiredContainers = [
            'chart-btc', 'chart-eth', 'chart-btc-eth',
            'chart-normalized', 'chart-diff'
        ];

        const containersReady = requiredContainers.every(id => {
            const element = document.getElementById(id);
            if (!element) console.error(`Контейнер #${id} не найден`);
            return element;
        });

        if (!containersReady) {
            showError('Не все контейнеры для графиков найдены!');
            return;
        }

        // 2. Создаем графики с начальными пустыми данными
        chartInstances.btcUsdt = createMultiSeriesChart('chart-btc', [{
            id: 'btc_usdt',
            seriesType: 'addLineSeries',
            color: BTC_COLOR,
            title: 'BTC/USDT Price'
        }]);

        chartInstances.ethUsdt = createMultiSeriesChart('chart-eth', [{
            id: 'eth_usdt',
            seriesType: 'addLineSeries',
            color: ETH_COLOR,
            title: 'ETH/USDT Price'
        }]);

        chartInstances.btcInEth = createMultiSeriesChart('chart-btc-eth', [
            {
            id: 'btc_in_eth',
            seriesType: 'addLineSeries',
            color: BTC_COLOR,
            title: 'BTC in ETH Units'
            },
            {
               id: 'eth_usdt',
                seriesType: 'addLineSeries',
                color: ETH_COLOR,
                title: 'ETH Units'
            }
        ]);

        chartInstances.normalized = createMultiSeriesChart('chart-normalized', [
            {
                id: 'btc_normalized',
                seriesType: 'addLineSeries',
                color: BTC_COLOR,
                title: 'BTC Normalized'
            },
            {
                id: 'eth_normalized',
                seriesType: 'addLineSeries',
                color: ETH_COLOR,
                title: 'ETH Normalized'
            }
        ]);

        chartInstances.priceDiff = createMultiSeriesChart('chart-diff', [{
            id: 'price_difference',
            seriesType: 'addLineSeries',
            color: '#ED4B9E',
            title: 'Price Difference (%)'
        }]);

        // 3. Загружаем данные
        await updateCharts();

        // 4. Настраиваем кнопку обновления
        document.getElementById('refresh-btn')?.addEventListener('click', updateCharts);

    } catch (error) {
        console.error('Ошибка инициализации приложения:', error);
        showError('Ошибка при запуске приложения');
    }
}

// Обновление данных графиков
async function updateCharts() {
    try {
        const loader = document.getElementById('loading-indicator');
        if (loader) loader.style.display = 'block';

        const data = await fetchData();
        if (!data) throw new Error('Данные не получены');

        // Обновляем все графики
        updateChartIfValid('btcUsdt', 'btc_usdt', data.btc);
        updateChartIfValid('ethUsdt', 'eth_usdt', data.eth);

        updateChartIfValid('btcInEth', 'btc_in_eth', data.btc_as_eth);
        updateChartIfValid('btcInEth', 'eth_usdt', data.eth);

        if (data.btc_as_eth_norm && data.eth_norm) {
            updateChartIfValid('normalized', 'btc_normalized', data.btc_as_eth_norm);
            updateChartIfValid('normalized', 'eth_normalized', data.eth_norm);
        }

        updateChartIfValid('priceDiff', 'price_difference', data.percentage_diff);

        updateStats(data);

        const lastUpdateEl = document.getElementById('last-update');
        if (lastUpdateEl) {
            lastUpdateEl.textContent = `Последнее обновление: ${new Date().toLocaleString()}`;
        }

    } catch (error) {
        console.error('Ошибка обновления графиков:', error);
        showError(`Ошибка обновления: ${error.message}`);
    } finally {
        const loader = document.getElementById('loading-indicator');
        if (loader) loader.style.display = 'none';
    }
}

// Вспомогательная функция для создания простого графика с одной серией
function createSingleChart(containerId, initialData, color, title) {
    return createMultiSeriesChart(containerId, [
        {
            id: 'main',
            seriesType: 'addLineSeries',
            color: color,
            title: title,
            data: formatChartData(initialData)
        }
    ]);
}


function updateChartIfValid(chartName, seriesName, data) {
    if (!chartInstances[chartName]) {
        console.warn(`График ${chartName} не инициализирован`);
        return;
    }

    if (!chartInstances[chartName].series[seriesName]) {
        console.warn(`Серия ${seriesName} не найдена в графике ${chartName}`);
        return;
    }

    if (!Array.isArray(data)) {
        console.warn(`Некорректные данные для графика ${chartName}`);
        return;
    }

    try {
        const validData = formatChartData(data);
        if (validData.length > 0) {
            chartInstances[chartName].series[seriesName].setData(validData);
        }
    } catch (error) {
        console.error(`Ошибка обновления графика ${chartName}:`, error);
    }
}

// Обновление статистики
function updateStats(data) {
    if (!data?.percentage_diff || !Array.isArray(data.percentage_diff)) {
        console.warn('Нет данных для статистики');
        return;
    }

    try {
        const diffs = data.percentage_diff
            .map(item => parseFloat(item?.value))
            .filter(value => !isNaN(value));

        if (diffs.length === 0) return;

        const currentDiff = diffs[diffs.length - 1];
        const maxDiff = Math.max(...diffs);
        const minDiff = Math.min(...diffs);

        // Устанавливаем значения
        setStatValue('spread-value', currentDiff);
        setStatValue('max-spread-value', maxDiff);
        setStatValue('min-spread-value', minDiff);

    } catch (error) {
        console.error('Ошибка обновления статистики:', error);
    }
}

// Установка значения статистики с форматированием
function setStatValue(elementId, value) {
    const element = document.getElementById(elementId);
    if (!element) return;

    element.textContent = !isNaN(value) ? `${value.toFixed(2)}%` : 'N/A';

    // Цвет в зависимости от значения
    if (value > 0) {
        element.style.color = '#27ae60'; // Зеленый
    } else if (value < 0) {
        element.style.color = '#e74c3c'; // Красный
    } else {
        element.style.color = '#333'; // Серый
    }
}

// Показать сообщение об ошибке
function showError(message) {
    let errorEl = document.getElementById('error-message');

    if (!errorEl) {
        errorEl = document.createElement('div');
        errorEl.id = 'error-message';
        errorEl.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px;
            background: #ffebee;
            color: #c62828;
            border-radius: 4px;
            z-index: 1000;
            max-width: 300px;
        `;
        document.body.appendChild(errorEl);
    }

    errorEl.textContent = message;
    errorEl.style.display = 'block';

    // Скрываем через 5 секунд
    setTimeout(() => {
        errorEl.style.display = 'none';
    }, 5000);
}

// Запуск приложения после загрузки DOM
document.addEventListener('DOMContentLoaded', () => {
    // Проверяем загружена ли библиотека графиков
    if (typeof LightweightCharts === 'undefined') {
        showError('Библиотека графиков не загружена!');
        return;
    }

    initApp();
});