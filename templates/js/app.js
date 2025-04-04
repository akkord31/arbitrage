// Глобальные переменные для хранения экземпляров графиков
const chartInstances = {};
let autoRefreshTimer = null;
const BTC_COLOR = "#FF9900"
const ETH_COLOR = "#627EEA"
async function initApp() {
    try {
        // 1. Проверяем наличие всех контейнеров для графиков
        const requiredContainers = [
            'chart-btc', 'chart-eth', 'chart-btc-eth',
            'chart-normalized', 'chart-diff-norm',
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
            title: 'BTC Price'
        }]);

        chartInstances.ethUsdt = createMultiSeriesChart('chart-eth', [{
            id: 'eth_usdt',
            seriesType: 'addLineSeries',
            color: ETH_COLOR,
            title: 'ETH Price'
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

        chartInstances.priceDiffNorm = createMultiSeriesChart('chart-diff-norm', [
            {
            id: 'price_difference_norm',
            seriesType: 'addLineSeries',
            color: '#ED4B9E',
            title: 'Price Difference (%)'
            },
            {
                id: 'relative_spread',
                seriesType: 'addLineSeries',
                color: '#01df31',
                title: 'relative_spread (%)'
            }
        ]);

        chartInstances.priceDiff = createMultiSeriesChart('chart-diff', [
            {
            id: 'price_difference',
            seriesType: 'addLineSeries',
            color: '#ED4B9E',
            title: 'Price Difference (%)'
            }
        ]);

        // 3. Загружаем данные
        await updateCharts();

        initAutoRefresh(60);
        setTimeout(() => initAutoRefresh(), 2000);
    } catch (error) {
        console.error('Ошибка инициализации приложения:', error);
        showError('Ошибка при запуске приложения');
    }
}

function initAutoRefresh() {
    startAutoRefresh(60);
}

function startAutoRefresh(intervalSeconds) {
    // Останавливаем предыдущий таймер, если есть
    if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
    }

    // Запускаем новый таймер
    autoRefreshTimer = setInterval(async () => {
        try {
            console.log('Автоматическое обновление данных...');
            await updateCharts();
        } catch (error) {
            console.error('Ошибка при автоматическом обновлении:', error);
        }
    }, intervalSeconds * 1000);
}

// Остановка автообновления
function stopAutoRefresh() {
    if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
        autoRefreshTimer = null;
    }
}
// Обновление данных графиков
async function updateCharts() {
    try {
        const loader = document.getElementById('loading-indicator');
        if (loader) loader.style.display = 'block';

        const data = await fetchData();
        if (!data) {
            console.log("No data received, skipping chart update");
            return;
        }

        // Обновляем все графики
        updateChartIfValid('btcUsdt', 'btc_usdt', data.btc);
        updateChartIfValid('ethUsdt', 'eth_usdt', data.eth);

        updateChartIfValid('btcInEth', 'btc_in_eth', data.btc_as_eth);
        updateChartIfValid('btcInEth', 'eth_usdt', data.eth);

        if (data.btc_as_eth_norm && data.eth_norm) {
            updateChartIfValid('normalized', 'btc_normalized', data.btc_as_eth_norm);
            updateChartIfValid('normalized', 'eth_normalized', data.eth_norm);
        }

        updateChartIfValid('priceDiffNorm', 'price_difference_norm', data.percentage_diff_norm);
        updateChartIfValid('priceDiffNorm', 'relative_spread', data.relative_spread);

        updateChartIfValid('priceDiff', 'price_difference', data.percentage_diff);

        updateStats(data);

        calculateInput();

        const lastUpdateEl = document.getElementById('last-update');
        if (lastUpdateEl) {
            const now = new Date();
            lastUpdateEl.textContent = `Последнее обновление: ${now.toLocaleTimeString()}`;
            lastUpdateEl.title = now.toString();
        }

    } catch (error) {
        console.error('Ошибка обновления графиков:', error);
        showError(`Ошибка обновления: ${error.message}`);
    } finally {
        const loader = document.getElementById('loading-indicator');
        if (loader) loader.style.display = 'none';
    }
}
window.addEventListener('beforeunload', () => {
    if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
    }
});

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

function updateStats(data) {
    if (!data?.percentage_diff_norm || !Array.isArray(data.percentage_diff_norm)) {
        console.warn('Нет данных для статистики');
        return;
    }

    try {
        const diffs = data.percentage_diff_norm
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

        const avg = localStorage.getItem('avg_ratio_180d')
        setValue('avg_ratio', avg);
        setValue('avg_ratio_stat', avg);

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

function setValue(elementId, value) {
    const element = document.getElementById(elementId);
    if (!element) return;

    element.textContent = value;
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

document.addEventListener('DOMContentLoaded', () => {
    const entryButton = document.getElementById('entry-button');
    if (entryButton) {
        entryButton.addEventListener('click', calculateInput);
    }

    calculateInput();
});

function calculateInput() {
    const btcInputEl = document.getElementById('btc-input');
    const ethInputEl = document.getElementById('eth-input');

    let btcInput = parseFloat(btcInputEl.value);
    let ethInput = parseFloat(ethInputEl.value);

    // Если поля пустые, пробуем загрузить из localStorage
    if (isNaN(btcInput)) {
        const storedBtc = localStorage.getItem('btcInput');
        if (storedBtc !== null) {
            btcInput = parseFloat(storedBtc);
        }
    } else {
        localStorage.setItem('btcInput', btcInput);
    }

    if (isNaN(ethInput)) {
        const storedEth = localStorage.getItem('ethInput');
        if (storedEth !== null) {
            ethInput = parseFloat(storedEth);
        }
    } else {
        localStorage.setItem('ethInput', ethInput);
    }

    // Проверяем: если после этого значения всё ещё NaN — выходим
    if (isNaN(btcInput) || isNaN(ethInput)) {
        return; // Ничего не делаем
    }

    // Получаем сохранённое среднее соотношение BTC/ETH
    const avg_ratio = parseFloat(localStorage.getItem('avg_ratio_24h'));
    if (isNaN(avg_ratio)) {
        alert("Среднее соотношение BTC/ETH не найдено. Загрузите данные.");
        return;
    }

    // Рассчитываем btc_as_eth
    const btcAsEth = btcInput / avg_ratio;

    // Получаем min и max значений
    const btcMin = parseFloat(localStorage.getItem('btcMin'));
    const btcMax = parseFloat(localStorage.getItem('btcMax'));
    const ethMin = parseFloat(localStorage.getItem('ethMin'));
    const ethMax = parseFloat(localStorage.getItem('ethMax'));

    if ([btcMin, btcMax, ethMin, ethMax].some(isNaN)) {
        alert("Нет данных для нормализации. Загрузите данные.");
        return;
    }

    // Нормализуем
    const btcAsEthNorm = (btcAsEth - btcMin) / (btcMax - btcMin);
    const ethNorm = (ethInput - ethMin) / (ethMax - ethMin);

    // Вычисляем разницу
    const entryLevel = btcAsEthNorm - ethNorm;

    drawEntryLine(entryLevel);
}

function drawEntryLine(level) {
    if (!chartInstances.priceDiffNorm) return;

    const chart = chartInstances.priceDiffNorm.chart;

    // Удаляем старую линию, если она существует
    if (chartInstances.priceDiffNorm.entryLine) {
        chartInstances.priceDiffNorm.entryLine.setData([]); // Очищаем данные старой линии
    }

    // Добавление серии для горизонтальной линии
    const lineSeries = chart.addLineSeries({
        color: 'red',
        lineWidth: 2,
        lineStyle: LightweightCharts.LineStyle.Dotted,
        title: 'Вход'
    });

    // Получаем границы временного диапазона графика
    const timeScale = chart.timeScale();
    const visibleRange = timeScale.getVisibleRange();
    if (!visibleRange) return;

    // Данные для горизонтальной линии (фиксированное значение по оси Y)
    const data = [
        { time: visibleRange.from, value: level }, // Начало линии (по видимому диапазону)
        { time: visibleRange.to, value: level }   // Конец линии (по видимому диапазону)
    ];

    // Устанавливаем данные для линии
    lineSeries.setData(data);

    // Сохраняем серию линии для возможности удаления или обновления
    chartInstances.priceDiffNorm.entryLine = lineSeries;
}

document.getElementById('calculate-price-btn').addEventListener('click', function () {
    const btcSum = parseFloat(document.getElementById('btc-sum-input').value);
    const avgRatio = parseFloat(localStorage.getItem('avg_ratio_180d'));

    if (!btcSum || !avgRatio) {
        document.getElementById('calculated-price').innerText = "Введите сумму BTC и убедитесь, что avg_ratio доступен.";
        return;
    }

    const calculatedPrice = btcSum * ( 1 + avgRatio / 100);
    document.getElementById('calculated-price').innerText = calculatedPrice.toFixed(4);
});

// сворачивание графика
document.addEventListener("DOMContentLoaded", () => {
    const toggleButtons = document.querySelectorAll(".toggle-chart");

    toggleButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const container = btn.closest(".chart-container");
            const chartBody = container.querySelector(".chart-body");

            if (!chartBody) return;

            // Переключаем класс collapsed для анимации
            container.classList.toggle("collapsed");

            // Скрываем или показываем содержимое графика
            chartBody.classList.toggle("hidden");

            // Обновляем текст кнопки
            const isCollapsed = container.classList.contains("collapsed");
            btn.textContent = isCollapsed ? "Развернуть" : "Свернуть";
        });
    });
});




