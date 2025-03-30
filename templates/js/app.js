// Глобальные переменные для хранения экземпляров
const chartInstances = {};

// Инициализация приложения
async function initApp() {
    // 1. Проверяем наличие контейнеров
    const requiredContainers = ['chart-btc', 'chart-eth', 'chart-btc-eth', 'chart-diff'];
    const containersReady = requiredContainers.every(id => document.getElementById(id));

    if (!containersReady) {
        console.error('Not all chart containers found!');
        return;
    }

    // 2. Создаем графики с пустыми данными
    chartInstances.btc = createSafeChart('chart-btc', [], '#F7931A');
    chartInstances.eth = createSafeChart('chart-eth', [], '#627EEA');
    chartInstances.btcEth = createSafeChart('chart-btc-eth', [], '#ED4B9E');
    chartInstances.diff = createSafeChart('chart-diff', [], '#2EC973');

    // 3. Загружаем данные
    await updateCharts();
}

// Обновление данных
async function updateCharts() {
    try {
        const data = await fetchData();
        if (!data) return;

        // Обновляем каждый график
        if (chartInstances.btc) {
            chartInstances.btc.series.setData(formatChartData(data.btc));
        }

        if (chartInstances.eth) {
            chartInstances.eth.series.setData(formatChartData(data.eth));
        }

        if (chartInstances.btcEth) {
            chartInstances.btcEth.series.setData(formatChartData(data.btc_as_eth));
        }

        if (chartInstances.diff) {
            chartInstances.diff.series.setData(formatChartData(data.percentage_diff));
        }

        updateStats(data);
        document.getElementById('last-update').textContent = `Last updated: ${new Date().toLocaleString()}`;

    } catch (error) {
        console.error('Error updating charts:', error);
    }
}

// Запуск приложения
document.addEventListener('DOMContentLoaded', () => {
    // Проверяем загружена ли библиотека
    if (typeof LightweightCharts === 'undefined') {
        console.error('Lightweight Charts library not loaded!');
        return;
    }

    initApp();
});