// Глобальные переменные для хранения экземпляров графиков
const chartInstances = {};

// Инициализация приложения
async function initApp() {
    try {
        // 1. Проверяем наличие всех контейнеров для графиков
        const requiredContainers = ['chart-btc', 'chart-eth', 'chart-btc-eth', 'chart-diff'];
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
        chartInstances.btc = createSafeChart('chart-btc', [], '#F7931A');
        chartInstances.eth = createSafeChart('chart-eth', [], '#627EEA');
        chartInstances.btcEth = createSafeChart('chart-btc-eth', [], '#ED4B9E');
        chartInstances.diff = createSafeChart('chart-diff', [], '#2EC973');

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
        // Показываем индикатор загрузки
        const loader = document.getElementById('loading-indicator');
        if (loader) loader.style.display = 'block';

        // Получаем данные
        const data = await fetchData();
        if (!data) {
            throw new Error('Данные не получены');
        }

        // Обновляем каждый график
        updateChartIfValid('btc', data.btc);
        updateChartIfValid('eth', data.eth);
        updateChartIfValid('btcEth', data.btc_as_eth);
        updateChartIfValid('diff', data.percentage_diff);

        // Обновляем статистику
        updateStats(data);

        // Обновляем время последнего обновления
        const lastUpdateEl = document.getElementById('last-update');
        if (lastUpdateEl) {
            lastUpdateEl.textContent = `Последнее обновление: ${new Date().toLocaleString()}`;
        }

    } catch (error) {
        console.error('Ошибка обновления графиков:', error);
        showError(`Ошибка обновления: ${error.message}`);
    } finally {
        // Скрываем индикатор загрузки
        const loader = document.getElementById('loading-indicator');
        if (loader) loader.style.display = 'none';
    }
}

// Обновление конкретного графика с проверкой данных
function updateChartIfValid(chartName, data) {
    if (!chartInstances[chartName]) {
        console.warn(`График ${chartName} не инициализирован`);
        return;
    }

    if (!Array.isArray(data)) {
        console.warn(`Некорректные данные для графика ${chartName}`);
        return;
    }

    try {
        // Фильтруем и форматируем данные
        const validData = data
            .map(item => {
                if (!item) return null;

                // Преобразуем время в Unix timestamp
                const time = typeof item.time === 'number' ? item.time :
                            new Date(item.time).getTime() / 1000;

                const value = parseFloat(item.value);

                if (isNaN(time) || isNaN(value)) return null;

                return { time, value };
            })
            .filter(item => item !== null)
            .sort((a, b) => a.time - b.time);

        if (validData.length > 0) {
            chartInstances[chartName].series.setData(validData);
        } else {
            console.warn(`Нет валидных данных для графика ${chartName}`);
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