import ccxt
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import time
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_exchange():
    """Инициализация подключения к бирже"""
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    return exchange


def create_tables():
    """Создание таблиц в SQLite"""
    conn = sqlite3.connect("market_data.db")
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_data_24h (
            timestamp INTEGER PRIMARY KEY,
            close_btc REAL,
            close_eth REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_data_180d (
            timestamp INTEGER PRIMARY KEY,
            close_btc REAL,
            close_eth REAL
        )
    ''')

    # Очистка данных при запуске
    cursor.execute("DELETE FROM market_data_24h")
    cursor.execute("DELETE FROM market_data_180d")

    conn.commit()
    conn.close()


def get_data(exchange, symbol, timeframe='1m', hours=None, days=None):
    all_data = []
    if hours:
        since = int((datetime.utcnow() - timedelta(hours=hours)).timestamp() * 1000)  # Время начала (за последние часы)
    elif days:
        since = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)  # Время начала (за последние дни)

    while True:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since,
                                    limit=1000)  # Binance ограничение в 1000 свечей
        if not ohlcv:
            break

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        all_data.append(df)

        since = int(df['timestamp'].iloc[-1]) + 1  # Сдвигаем начало запроса на последнюю загруженную свечу
        if len(df) < 999:  # Если Binance вернул меньше 1000 свечей, значит данные закончились
            break

    # Объединяем все части данных
    full_df = pd.concat(all_data, ignore_index=True)
    full_df['timestamp'] = pd.to_datetime(full_df['timestamp'], unit='ms')

    full_df['timestamp'] = full_df['timestamp'].dt.tz_localize('UTC').dt.tz_convert('Europe/Moscow')  # Преобразуем в Москву (UTC+3)

    return full_df[['timestamp', 'close']]

def save_data_in_db(btc_data, eth_data, table_name):
    """Вычисление метрик и сохранение в базу"""
    if btc_data.empty or eth_data.empty:
        logger.error("Ошибка: пустые данные")
        return

    merged = pd.merge(btc_data, eth_data, on='timestamp', suffixes=('_btc', '_eth'))
    conn = sqlite3.connect("market_data.db")
    merged[['timestamp', 'close_btc', 'close_eth']].to_sql(table_name, conn, if_exists='replace',
                                                                         index=False)
    conn.close()
    logger.info(f"Данные сохранены в {table_name}")

def main():
    """Основная функция"""
    exchange = initialize_exchange()

    create_tables()

    btc_data_24h = get_data(exchange, 'BTC/USDT', '1m', hours=24)
    eth_data_24h = get_data(exchange, 'ETH/USDT', '1m', hours=24)
    btc_data_180d = get_data(exchange, 'BTC/USDT', '1d', days=180)
    eth_data_180d = get_data(exchange, 'ETH/USDT', '1d', days=180)

    save_data_in_db(btc_data_24h, eth_data_24h, "market_data_24h")
    save_data_in_db(btc_data_180d, eth_data_180d, "market_data_180d")


if __name__ == "__main__":
    main()
