from datetime import datetime, timedelta
import ccxt
import matplotlib
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
import pytz  # Для работы с часовыми поясами

matplotlib.use("TkAgg")

# Инициализация Binance API
binance = ccxt.binance()


# Функция загрузки данных с учетом ограничения по количеству свечей
def get_data(symbol, timeframe='1m', hours=None, days=None):
    all_data = []
    if hours:
        since = int((datetime.utcnow() - timedelta(hours=hours)).timestamp() * 1000)  # Время начала (за последние часы)
    elif days:
        since = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)  # Время начала (за последние дни)

    while True:
        ohlcv = binance.fetch_ohlcv(symbol, timeframe=timeframe, since=since,
                                    limit=1000)  # Binance ограничение в 1000 свечей
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

    full_df['timestamp'] = full_df['timestamp'].dt.tz_localize('UTC').dt.tz_convert('Europe/Moscow')  # Преобразуем в Москву (UTC+3)

    return full_df[['timestamp', 'close']]


# Загружаем данные BTC и ETH за последние сутки (1 минута)
btc_data_24h = get_data('BTC/USDT', '1m', hours=24)
eth_data_24h = get_data('ETH/USDT', '1m', hours=24)

# Загружаем данные BTC и ETH за последние 180 дней (1 день)
btc_data_180d = get_data('BTC/USDT', '1d', days=180)
eth_data_180d = get_data('ETH/USDT', '1d', days=180)

# Объединяем данные по времени (для 24 часов)
merged_24h = pd.merge(btc_data_24h, eth_data_24h, on='timestamp', suffixes=('_btc', '_eth'))

# Объединяем данные по времени (для 180 дней)
merged_180d = pd.merge(btc_data_180d, eth_data_180d, on='timestamp', suffixes=('_btc', '_eth'))

# **Пересчет BTC в "ETH-единицах" для 24 часов**
merged_24h['btc_to_eth'] = merged_24h['close_btc'] / merged_24h['close_eth']

# **Пересчет BTC в "ETH-единицах" для 180 дней**
merged_180d['btc_to_eth'] = merged_180d['close_btc'] / merged_180d['close_eth']

# **Средний коэффициент BTC/ETH за 24 часа**
average_ratio_24h = merged_24h['btc_to_eth'].mean()

# **Средний коэффициент BTC/ETH за 180 дней**
average_ratio_180d = merged_180d['btc_to_eth'].mean()

# **BTC, приведенный к ETH по среднему коэффициенту за 24 часа**
merged_24h['btc_as_eth'] = merged_24h['close_btc'] / average_ratio_24h

# **BTC, приведенный к ETH по среднему коэффициенту за 180 дней**
merged_180d['btc_as_eth'] = merged_180d['close_btc'] / average_ratio_180d

# Нормализуем данные для графика (для 24 часов)
scaler_24h = MinMaxScaler()
merged_24h[['btc_as_eth_norm', 'close_eth_norm']] = scaler_24h.fit_transform(merged_24h[['btc_as_eth', 'close_eth']])

# Нормализуем данные для графика (для 180 дней)
scaler_180d = MinMaxScaler()
merged_180d[['btc_as_eth_norm', 'close_eth_norm']] = scaler_180d.fit_transform(merged_180d[['btc_as_eth', 'close_eth']])

# **Процентная разница между нормализованным BTC и ETH для 24 часов**
merged_24h['percentage_diff_normalized'] = (merged_24h['btc_as_eth_norm'] - merged_24h[
    'close_eth_norm'])

# **Процентная разница между нормализованным BTC и ETH для 180 дней**
merged_180d['percentage_diff_normalized'] = (merged_180d['btc_as_eth_norm'] - merged_180d[
    'close_eth_norm'])

# **Графики**
fig, axes = plt.subplots(3, 2, figsize=(14, 12))

# 1. График цены BTC за 24 часа
axes[0, 0].plot(merged_24h['timestamp'], merged_24h['close_btc'], color='orange', label='Цена BTC (24 часа)')
axes[0, 0].set_xlabel('Время')
axes[0, 0].set_ylabel('Цена (USDT)')
axes[0, 0].set_title('Цена Bitcoin (24 часа, 1м)')
axes[0, 0].legend()
axes[0, 0].grid(True)

# 2. График цены ETH за 24 часа
axes[0, 1].plot(merged_24h['timestamp'], merged_24h['close_eth'], color='blue', label='Цена ETH (24 часа)')
axes[0, 1].set_xlabel('Время')
axes[0, 1].set_ylabel('Цена (USDT)')
axes[0, 1].set_title('Цена Ethereum (24 часа, 1м)')
axes[0, 1].legend()
axes[0, 1].grid(True)

# 3. BTC и ETH в "ETH-единицах" за 24 часа
axes[1, 0].plot(merged_24h['timestamp'], merged_24h['btc_as_eth'], color='orange', label='BTC в ETH-единицах (24 часа)')
axes[1, 0].plot(merged_24h['timestamp'], merged_24h['close_eth'], color='blue', label='ETH (24 часа)')
axes[1, 0].set_xlabel('Время')
axes[1, 0].set_ylabel('Цена (ETH)')
axes[1, 0].set_title('BTC в ETH-единицах и ETH (24 часа, 1м)')
axes[1, 0].legend()
axes[1, 0].grid(True)

# 4. Нормализованный график BTC и ETH за 24 часа
axes[1, 1].plot(merged_24h['timestamp'], merged_24h['btc_as_eth_norm'], color='orange',
                label='BTC в ETH-единицах (норм.)')
axes[1, 1].plot(merged_24h['timestamp'], merged_24h['close_eth_norm'], color='blue', label='ETH (норм.)')
axes[1, 1].set_xlabel('Время')
axes[1, 1].set_ylabel('Нормализованное значение')
axes[1, 1].set_title('Нормализованные данные BTC и ETH (24 часа, 1м)')
axes[1, 1].legend()
axes[1, 1].grid(True)

# 5. Процентная разница между нормализованными данными BTC и ETH для 24 часов
axes[2, 0].plot(merged_24h['timestamp'], merged_24h['percentage_diff_normalized'], color='red',
                label='Процентная разница (норм.)')
# Зеленая линия: начало — значение за 180 дней, конец — последнее значение за 24 часа
start_value_180d = merged_180d['percentage_diff_normalized'].iloc[0]
end_value_24h = merged_24h['percentage_diff_normalized'].iloc[-1]
axes[2, 0].plot([merged_24h['timestamp'].iloc[0], merged_24h['timestamp'].iloc[-1]], [start_value_180d, end_value_24h],
                color='green', label='Относительный нулевой спред')
axes[2, 0].axhline(0, color='black', linestyle='--', linewidth=1)  # Линия 0% для ориентира
axes[2, 0].set_xlabel('Время')
axes[2, 0].set_ylabel('Изменение (%)')
axes[2, 0].set_title('Процентная разница BTC (норм.) и ETH (норм.) (24 часа, 1м)')
axes[2, 0].legend()
axes[2, 0].grid(True)

# Отображаем коэффициент масштабирования для 24 часов
plt.text(0.95, 0.95, f'Коэффициент масштабирования BTC/ETH (24h): {average_ratio_24h:.6f}', ha='right', va='top',
         transform=fig.transFigure, fontsize=12, color='black',
         bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.5'))

# Отображаем коэффициент масштабирования для 180 дней
plt.text(0.55, 0.95, f'Коэффициент масштабирования BTC/ETH (180d): {average_ratio_180d:.6f}', ha='right', va='top',
         transform=fig.transFigure, fontsize=12, color='black',
         bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.5'))

# Финальные настройки
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
