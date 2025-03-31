// Загрузка данных из API
async function fetchData(interval) {
    try {
        const response = await fetch(`/api/data?interval=${interval}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching data:', error);
        return null;
    }
}

// Обновление статистики
function updateStats(data) {
    if (!data || !data.percentage_diff) return;

    const diffs = data.percentage_diff.map(item => item.value);
    const currentDiff = diffs[diffs.length - 1];
    const maxDiff = Math.max(...diffs);
    const minDiff = Math.min(...diffs);

    document.getElementById('spread-value').textContent = currentDiff ? `${currentDiff.toFixed(2)}%` : 'N/A';
    document.getElementById('max-spread-value').textContent = maxDiff ? `${maxDiff.toFixed(2)}%` : 'N/A';
    document.getElementById('min-spread-value').textContent = minDiff ? `${minDiff.toFixed(2)}%` : 'N/A';

    // Цветовая индикация
    const spreadElement = document.getElementById('spread-value');
    spreadElement.style.color = currentDiff > 0 ? '#27ae60' : currentDiff < 0 ? '#e74c3c' : '#333';
}

// Сохранение данных
function saveHistory(data) {
    try {
        const history = loadHistory();
        const newEntry = {
            timestamp: new Date().toISOString(),
            data: data
        };
        history.push(newEntry);
        localStorage.setItem('spreadHistory', JSON.stringify(history.slice(-100)));
    } catch (e) {
        console.error('Failed to save history:', e);
    }
}

// Загрузка истории
function loadHistory() {
    try {
        const stored = localStorage.getItem('spreadHistory');
        return stored ? JSON.parse(stored) : [];
    } catch (e) {
        console.error('Failed to load history:', e);
        return [];
    }
}
