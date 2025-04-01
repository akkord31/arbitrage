import sqlite3
from pathlib import Path
import json
from datetime import datetime
import logging
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

DB_PATH = Path(__file__).parent / "market_data.db"
logger = logging.getLogger(__name__)


class DataProcessor:
    @staticmethod
    def calculate_percentage_diff(data):
        """Расчет процентной разницы от среднего"""
        if not data or len(data) == 0:
            return []

        values = [item['value'] for item in data]
        avg = sum(values) / len(values)

        return [
            {
                'time': item['time'],
                'value': ((item['value'] - avg) / avg) * 100
            }
            for item in data
        ]

    @staticmethod
    def process_market_data(raw_data_24h, raw_data_180d):
        """Основная обработка рыночных данных с нормализацией"""
        result = {
            'btc': [],
            'eth': [],
            'btc_as_eth': [],
            'btc_as_eth_norm': [],  # Нормализованный BTC
            'eth_norm': [],  # Нормализованный ETH
            'percentage_diff': []
        }

        data_24h, avg_24h = calculate_metrics(raw_data_24h)
        data_180d, avg_180d = calculate_metrics(raw_data_180d)

        for row in data_24h.itertuples(index=False):
            try:
                time = int(pd.to_datetime(row.timestamp).timestamp())
                btc = float(row.close_btc)
                eth = float(row.close_eth)
                btc_as_eth = float(row.btc_as_eth)
                btc_as_eth_norm = float(row.btc_as_eth_norm)
                eth_norm = float(row.eth_norm)
                percentage_diff_normalized = float(row.percentage_diff_normalized)

                result['btc'].append({'time': time, 'value': btc})
                result['eth'].append({'time': time, 'value': eth})
                result['btc_as_eth'].append({'time': time, 'value': btc_as_eth})
                result['btc_as_eth_norm'].append({'time': time, 'value': btc_as_eth_norm})
                result['eth_norm'].append({'time': time, 'value': eth_norm})
                result['percentage_diff'].append({'time': time, 'value': percentage_diff_normalized})

            except (ValueError, KeyError) as e:
                logger.warning(f"Ошибка обработки записи: {e}")
            except Exception as e:
                logger.error(f"Ошибка нормализации данных: {e}")

        return result

    @staticmethod
    def get_processed_data():
        """Получение и обработка данных из БД"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Проверяем существование таблицы 24h
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                           (f'market_data_24h',))
            if not cursor.fetchone():
                return None

            # Проверяем существование таблицы 180d
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                           (f'market_data_180d',))
            if not cursor.fetchone():
                return None

            # Получаем данные
            cursor.execute(f"""
                SELECT timestamp, close_btc, close_eth
                FROM market_data_24h
                ORDER BY timestamp
            """)

            raw_data_24h = [dict(row) for row in cursor.fetchall()]

            # Получаем данные
            cursor.execute(f"""
                SELECT timestamp, close_btc, close_eth
                FROM market_data_180d
                ORDER BY timestamp
            """)
            raw_data_180d = [dict(row) for row in cursor.fetchall()]


            return DataProcessor.process_market_data(raw_data_24h, raw_data_180d)

        except sqlite3.Error as e:
            logger.error(f"Ошибка БД: {e}")
            return None
        finally:
            conn.close()


def calculate_metrics(raw_data):
    """Вычисление метрик и сохранение в базу"""
    if not raw_data:
        logger.error("Ошибка: пустые данные")
        return

    # Преобразуем список словарей в DataFrame
    df = pd.DataFrame(raw_data)

    # Проверяем, есть ли все нужные колонки
    required_columns = {'timestamp', 'close_btc', 'close_eth'}
    if not required_columns.issubset(df.columns):
        logger.error("Ошибка: отсутствуют необходимые столбцы")
        return

    # Преобразуем timestamp в datetime для удобства
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Сортируем по времени
    df = df.sort_values('timestamp')

    # Вычисляем соотношение BTC/ETH
    df['btc_to_eth'] = df['close_btc'] / df['close_eth']
    avg_ratio = df['btc_to_eth'].mean()

    df = df.drop(columns=['btc_to_eth'])

    # Вычисляем btc_as_eth
    df['btc_as_eth'] = round(df['close_btc'] / avg_ratio, 2)

    # Нормализация
    scaler = MinMaxScaler()
    df[['btc_as_eth_norm', 'eth_norm']] = scaler.fit_transform(
        df[['btc_as_eth', 'close_eth']]
    )

    # Вычисляем разницу нормализованных значений
    df['percentage_diff_normalized'] = df['btc_as_eth_norm'] - df['eth_norm']

    return df, avg_ratio
