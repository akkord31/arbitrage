from datetime import datetime, timedelta
import ccxt
import matplotlib
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler

matplotlib.use("TkAgg")

# Инициализация Binance API
binance = ccxt.binance()

# Функция загрузки данных с учетом ограничения по количеству свечей
def get_data(symbol, timeframe='1d', days=180):  # Изменено на 180 дней и 1 час
    all_data = []
    since = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)  # Время начала (180 дней назад)

    while True:
        ohlcv = binance.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)  # Binance ограничение в 1000
        if not ohlcv:
            break

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        all_data.append(df)

        since = int(df['timestamp'].iloc[-1]) + 1  # Сдвигаем начало запроса на последнюю загруженную свечу
        if len(df) < 1000:  # Если Binance вернул меньше 1000 свечей, значит данные закончились
            break

    # Объединяем все части данных
    full_df = pd.concat(all_data, ignore_index=True)
    full_df['timestamp'] = pd.to_datetime(full_df['timestamp'], unit='ms')
    return full_df[['timestamp', 'close']]

# Загружаем данные BTC и ETH за 180 дней
btc_data = get_data('BTC/USDT', '1d', days=180)  # Изменено на 180 дней и 1 час
eth_data = get_data('ETH/USDT', '1d', days=180)  # Изменено на 180 дней и 1 час

# Объединяем данные по времени
merged = pd.merge(btc_data, eth_data, on='timestamp', suffixes=('_btc', '_eth'))

# **Пересчет BTC в "ETH-единицах"**
merged['btc_to_eth'] = merged['close_btc'] / merged['close_eth']

# **Средний коэффициент BTC/ETH за 180 дней**
average_ratio = merged['btc_to_eth'].mean()

# **BTC, приведенный к ETH по среднему коэффициенту**
merged['btc_as_eth'] = merged['close_btc'] / average_ratio

# Нормализуем данные для графика
scaler = MinMaxScaler()
merged[['btc_as_eth_norm', 'close_eth_norm']] = scaler.fit_transform(merged[['btc_as_eth', 'close_eth']])

# **Процентная разница между нормализованным BTC и ETH**
merged['percentage_diff_normalized'] = (merged['btc_as_eth_norm'] - merged['close_eth_norm']) * average_ratio

# **Графики**
fig, axes = plt.subplots(3, 2, figsize=(14, 12))

# 1. График цены BTC
axes[0, 0].plot(merged['timestamp'], merged['close_btc'], color='orange', label='Цена BTC')
axes[0, 0].set_xlabel('Время')
axes[0, 0].set_ylabel('Цена (USDT)')
axes[0, 0].set_title('Цена Bitcoin (180 дней, 1ч)')
axes[0, 0].legend()
axes[0, 0].grid(True)

# 2. График цены ETH
axes[0, 1].plot(merged['timestamp'], merged['close_eth'], color='blue', label='Цена ETH')
axes[0, 1].set_xlabel('Время')
axes[0, 1].set_ylabel('Цена (USDT)')
axes[0, 1].set_title('Цена Ethereum (180 дней, 1ч)')
axes[0, 1].legend()
axes[0, 1].grid(True)

# 3. BTC и ETH в "ETH-единицах"
axes[1, 0].plot(merged['timestamp'], merged['btc_as_eth'], color='orange', label='BTC в ETH-единицах')
axes[1, 0].plot(merged['timestamp'], merged['close_eth'], color='blue', label='ETH')
axes[1, 0].set_xlabel('Время')
axes[1, 0].set_ylabel('Цена (ETH)')
axes[1, 0].set_title('BTC в ETH-единицах и ETH (180 дней, 1ч)')
axes[1, 0].legend()
axes[1, 0].grid(True)

# 4. Нормализованный график BTC и ETH
axes[1, 1].plot(merged['timestamp'], merged['btc_as_eth_norm'], color='orange', label='BTC в ETH-единицах (норм.)')
axes[1, 1].plot(merged['timestamp'], merged['close_eth_norm'], color='blue', label='ETH (норм.)')
axes[1, 1].set_xlabel('Время')
axes[1, 1].set_ylabel('Нормализованное значение')
axes[1, 1].set_title('Нормализованные данные BTC и ETH (180 дней, 1ч)')
axes[1, 1].legend()
axes[1, 1].grid(True)

# 5. Процентная разница между нормализованными данными BTC и ETH
axes[2, 0].plot(merged['timestamp'], merged['percentage_diff_normalized'], color='red', label='Процентная разница (норм.)')
axes[2, 0].axhline(0, color='black', linestyle='--', linewidth=1)  # Линия 0% для ориентира
# Добавляем линейную зеленую линию от первого до последнего значения
axes[2, 0].plot([merged['timestamp'].iloc[0], merged['timestamp'].iloc[-1]],
                [merged['percentage_diff_normalized'].iloc[0], merged['percentage_diff_normalized'].iloc[-1]],
                color='green', label='Относительный нулевой спред')
axes[2, 0].set_xlabel('Время')
axes[2, 0].set_ylabel('Изменение (%)')
axes[2, 0].set_title('Процентная разница BTC (норм.) и ETH (норм.) (180 дней, 1ч)')
axes[2, 0].legend()
axes[2, 0].grid(True)

# **Отображаем коэффициент масштабирования на графике**
plt.text(0.95, 0.95, f'Коэффициент масштабирования BTC/ETH: {average_ratio:.6f}', ha='right', va='top',
         transform=fig.transFigure, fontsize=12, color='black', bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.5'))

# Финальные настройки
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
