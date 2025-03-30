/**
 * Надежная инициализация графиков Lightweight Charts
 */

// Проверка загрузки библиотеки
function checkLibraryLoaded() {
    if (typeof LightweightCharts === 'undefined') {
        console.error('LightweightCharts library not loaded!');
        return false;
    }
    return true;
}

// Создание графика с полной обработкой ошибок
function createSafeChart(containerId, initialData, lineColor) {
    // 1. Проверяем загружена ли библиотека
    if (!checkLibraryLoaded()) return null;

    // 2. Получаем контейнер
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Chart container #${containerId} not found`);
        return null;
    }

    // 3. Устанавливаем обязательные стили контейнера
    container.style.position = 'relative';
    container.style.width = '100%';
    container.style.minHeight = '300px';

    try {
        // 4. Создаем график
        const chart = LightweightCharts.createChart(container, {
            layout: {
                backgroundColor: '#ffffff',
                textColor: '#2B2B43',
                fontSize: 12,
                fontFamily: 'Arial'
            },
            grid: {
                vertLines: { color: 'rgba(43, 43, 67, 0.1)' },
                horzLines: { color: 'rgba(43, 43, 67, 0.1)' }
            },
            timeScale: {
                borderColor: 'rgba(43, 43, 67, 0.15)',
                timeVisible: true
            },
            rightPriceScale: {
                borderColor: 'rgba(43, 43, 67, 0.15)'
            }
        });

        // 5. Добавляем линейный график (самая надежная серия)
        const series = chart.addLineSeries({
            color: lineColor,
            lineWidth: 2,
            priceFormat: {
                type: 'price',
                precision: 2,
                minMove: 0.01
            }
        });

        // 6. Устанавливаем данные, если они есть
        if (initialData && initialData.length > 0) {
            const validData = initialData
                .map(item => ({
                    time: item.time,
                    value: Number(item.value)
                }))
                .filter(item => !isNaN(item.value));

            series.setData(validData);
        }

        // 7. Настраиваем автоматический ресайз
        const resizeObserver = new ResizeObserver(entries => {
            for (const entry of entries) {
                if (entry.target === container) {
                    chart.applyOptions({
                        width: entry.contentRect.width,
                        height: entry.contentRect.height
                    });
                }
            }
        });
        resizeObserver.observe(container);

        return {
            chart: chart,
            series: series,
            destroy: () => {
                resizeObserver.disconnect();
                chart.remove();
            }
        };

    } catch (error) {
        console.error('Error creating chart:', error);
        return null;
    }
}

// Форматирование данных с валидацией
function formatChartData(data) {
    if (!Array.isArray(data)) return [];

    return data.map(item => {
        if (!item || typeof item !== 'object') return null;

        const time = Number(item.time);
        const value = Number(item.value);

        return {
            time: isNaN(time) ? Math.floor(Date.now() / 1000) : time,
            value: isNaN(value) ? 0 : value
        };
    }).filter(Boolean);
}