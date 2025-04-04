function createMultiSeriesChart(containerId, seriesConfig) {
    // Проверка библиотеки
    if (typeof LightweightCharts === 'undefined') {
        console.error('LightweightCharts library not loaded!');
        return null;
    }

    // Получаем контейнер
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Chart container #${containerId} not found`);
        return null;
    }

    // Настройки контейнера
    container.style.position = 'relative';
    container.style.width = '100%';
    container.style.minHeight = '300px';

    try {
        // Создаем график
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
                timeVisible: true,
                secondsVisible: true,
                barSpacing: 1,
            }
        });

        // Создаем серии согласно конфигурации
        const series = {};
        seriesConfig.forEach(config => {
            series[config.id] = chart[config.seriesType]({
                color: config.color,
                lineWidth: config.lineWidth || 2,
                title: config.title
            });

            if (config.data) {
                series[config.id].setData(config.data);
            }
        });

        // Настройка ресайза
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
        console.error('Error creating multi-series chart:', error);
        return null;
    }
}


function formatChartData(data) {
    if (!Array.isArray(data)) return [];

    return data.map(item => {
        if (!item || typeof item !== 'object') return null;

        const time = Number(item.time);
        const value = Number(item.value);

        // Сдвигаем на UTC+3 (в секундах: 3 * 60 * 60 = 10800)
        const timeShifted = isNaN(time) ? Math.floor(Date.now() / 1000) : time + 10800;

        return {
            time: timeShifted,
            value: isNaN(value) ? 0 : value
        };
    }).filter(Boolean);
}

