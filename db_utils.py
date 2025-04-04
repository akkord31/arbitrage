import sys
from pathlib import Path

import ccxt
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import time
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_exchange_instance = None  # Глобальная переменная для хранения экземпляра биржи


def initialize_exchange():
    """Инициализация подключения к бирже (Singleton)"""
    global _exchange_instance
    if _exchange_instance is None:  # Если объект ещё не создан, создаём его
        _exchange_instance = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
    return _exchange_instance  # Возвращаем существующий экземпляр

def get_db_path():
    """Получает правильный путь к базе данных, учитывая запуск как EXE и удаляет 'lib\\library.zip' из пути"""
    if hasattr(sys, '_MEIPASS'):
        # Если программа упакована в EXE, извлекаем базу данных из архивированного файла
        base_path = sys._MEIPASS
    else:
        # Если запущено как скрипт, используем текущую директорию
        base_path = Path(__file__).parent

    # Преобразуем путь в строку для дальнейших манипуляций
    base_path_str = str(base_path)

    # Удаляем 'lib\library.zip' из пути, если она там есть
    if 'lib\\library.zip' in base_path_str:
        base_path_str = base_path_str.replace('lib\\library.zip', '')

    # Возвращаем путь, добавив 'market_data.db'
    db_path = Path(base_path_str) / 'market_data.db'

    return db_path

def create_tables():
    """Создание таблиц в SQLite"""
    conn = sqlite3.connect("market_data.db")
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_data_24h (
            timestamp TEXT  PRIMARY KEY,
            close_btc REAL,
            close_eth REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_data_180d (
            timestamp TEXT PRIMARY KEY,
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
        since = int((datetime.utcnow() - timedelta(hours=hours - 3)).timestamp() * 1000)  # Время начала (за последние часы)
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
        if len(df) < 1000:  # Если Binance вернул меньше 1000 свечей, значит данные закончились
            break

    # Объединяем все части данных
    full_df = pd.concat(all_data, ignore_index=True)
    full_df['timestamp'] = pd.to_datetime(full_df['timestamp'], unit='ms')

    full_df['timestamp'] = full_df['timestamp'].dt.tz_localize('UTC').dt.tz_convert(
        'Europe/Moscow')  # Преобразуем в Москву (UTC+3)

    return full_df[['timestamp', 'close']]


def save_data_in_db(btc_data, eth_data, table_name):
    """Вычисление метрик и сохранение в базу"""
    if btc_data.empty or eth_data.empty:
        logger.error("Ошибка: пустые данные")
        return

    merged = pd.merge(btc_data, eth_data, on='timestamp', suffixes=('_btc', '_eth'))

    # Преобразуем типы данных
    merged['timestamp'] = pd.to_datetime(merged['timestamp'])
    merged['close_btc'] = pd.to_numeric(merged['close_btc'], errors='coerce')
    merged['close_eth'] = pd.to_numeric(merged['close_eth'], errors='coerce')

    conn = sqlite3.connect("market_data.db")

    # Проверяем существующие данные
    existing = pd.read_sql(f"SELECT timestamp FROM {table_name}", conn)

    # Фильтруем только новые данные
    if not existing.empty:
        merged = merged[~merged['timestamp'].isin(existing['timestamp'])]

    if not merged.empty:
        try:
            # Добавляем только новые данные
            merged[['timestamp', 'close_btc', 'close_eth']].to_sql(
                table_name,
                conn,
                if_exists='append',
                index=False
            )
            logger.info(f"Добавлено {len(merged)} записей в {table_name}")
        except sqlite3.IntegrityError as e:
            logger.error(f"Ошибка при вставке данных: {e}")
    else:
        logger.info(f"Нет новых данных для {table_name}")

    conn.close()


def main():
    """Основная функция"""
    exchange = initialize_exchange()

    create_tables()

    btc_data_24h = get_data(exchange, 'BTC/USDT', '1m', hours=24)
    eth_data_24h = get_data(exchange, 'ETH/USDT', '1m', hours=24)
    btc_data_180d = get_data(exchange, 'BTC/USDT', '12h', days=180)
    eth_data_180d = get_data(exchange, 'ETH/USDT', '12h', days=180)

    save_data_in_db(btc_data_24h, eth_data_24h, "market_data_24h")
    save_data_in_db(btc_data_180d, eth_data_180d, "market_data_180d")


if __name__ == "__main__":
    main()
