import sqlite3
import logging
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import db_utils
from zoneinfo import ZoneInfo


DB_PATH = db_utils.get_db_path()
logger = logging.getLogger(__name__)


class DataProcessor:
    """
    Класс для обработки рыночных данных, извлечённых из базы данных, и подготовки их
    к визуализации или дальнейшему анализу.
    """
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
        """Обрабатывает рыночные данные и вычисляет метрики."""
        result = {
            'btc': [],
            'eth': [],
            'btc_as_eth': [],
            'btc_as_eth_norm': [],
            'eth_norm': [],
            'percentage_diff_norm': [],
            'percentage_diff': [],
            'relative_spread': [],
            "avg_ratio": 0,
            'btc_as_eth_min': 0,
            'btc_as_eth_max': 0,
            'eth_min': 0,
            'eth_max': 0
        }

        data_24h, avg_24h = calculate_metrics(raw_data_24h)
        data_180d, avg_180d = calculate_metrics(raw_data_180d)

        # Вычисляем min и max
        btc_as_eth_min = data_24h['btc_as_eth'].min()
        btc_as_eth_max = data_24h['btc_as_eth'].max()
        eth_min = data_24h['close_eth'].min()
        eth_max = data_24h['close_eth'].max()
        result['btc_as_eth_min'] = btc_as_eth_min
        result['btc_as_eth_max'] = btc_as_eth_max
        result['eth_min'] = eth_min
        result['eth_max'] = eth_max
        result['avg_ratio'] = avg_180d

        for row in data_24h.itertuples(index=False):
            try:
                time = int(pd.to_datetime(row.timestamp).timestamp())
                btc = float(row.close_btc)
                eth = float(row.close_eth)
                btc_as_eth = float(row.btc_as_eth)
                btc_as_eth_norm = float(row.btc_as_eth_norm)
                eth_norm = float(row.eth_norm)
                percentage_diff_normalized = float(row.percentage_diff_normalized)
                percentage_diff = float(row.percentage_diff)

                result['btc'].append({'time': time, 'value': btc})
                result['eth'].append({'time': time, 'value': eth})
                result['btc_as_eth'].append({'time': time, 'value': btc_as_eth})
                result['btc_as_eth_norm'].append({'time': time, 'value': btc_as_eth_norm})
                result['eth_norm'].append({'time': time, 'value': eth_norm})
                result['percentage_diff_norm'].append({'time': time, 'value': percentage_diff_normalized})
                result['percentage_diff'].append({'time': time, 'value': percentage_diff})

            except (ValueError, KeyError) as e:
                logger.warning(f"Ошибка обработки записи: {e}")
            except Exception as e:
                logger.error(f"Ошибка нормализации данных: {e}")

        # --- Первая точка: среднее за первый месяц в data_180d ---
        start_time_180d = pd.to_datetime(data_180d['timestamp'].iloc[0])
        end_time_180d = start_time_180d + pd.DateOffset(days=7)

        # Фильтруем первые 30 дней
        first_month_data = data_180d[(pd.to_datetime(data_180d['timestamp']) >= start_time_180d) &
                                     (pd.to_datetime(data_180d['timestamp']) < end_time_180d)]

        avg_180d = first_month_data['percentage_diff_normalized'].mean()

        result['relative_spread'].append({
            'time': start_time_180d.timestamp(),
            'value': avg_180d
        })

        # --- Вторая точка: среднее за последние 24 часа в data_24h ---
        # Предполагаем, что data_24h уже содержит данные только за последние 24 часа
        avg_24h = data_24h['percentage_diff_normalized'].mean()
        last_timestamp = pd.to_datetime(data_24h['timestamp'].iloc[-1])

        result['relative_spread'].append({
            'time': last_timestamp.timestamp(),
            'value': avg_24h
        })

        return result

    @staticmethod
    def get_processed_data():
        """Получение и обработка данных из БД с улучшенной обработкой ошибок"""
        conn = None
        try:
            logger.info(f"Путь к бд: {DB_PATH}")
            conn = sqlite3.connect(DB_PATH, timeout=30)
            conn.row_factory = sqlite3.Row

            # Проверяем существование таблиц
            cursor = conn.cursor()
            for table in ['market_data_24h', 'market_data_180d']:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if not cursor.fetchone():
                    logger.error(f"Таблица {table} не найдена в базе данных")
                    return None

            # Получаем данные с обработкой возможных ошибок
            try:
                cursor.execute("""
                    SELECT timestamp, close_btc, close_eth 
                    FROM market_data_24h 
                    ORDER BY timestamp
                """)
                raw_data_24h = [dict(row) for row in cursor.fetchall()]

                cursor.execute("""
                    SELECT timestamp, close_btc, close_eth 
                    FROM market_data_180d 
                    ORDER BY timestamp
                """)
                raw_data_180d = [dict(row) for row in cursor.fetchall()]

                if not raw_data_24h or not raw_data_180d:
                    logger.error("Одна из таблиц не содержит данных")
                    return None

                return DataProcessor.process_market_data(raw_data_24h, raw_data_180d)

            except sqlite3.Error as e:
                logger.error(f"Ошибка при выполнении SQL-запроса: {e}")
                return None

        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении данных: {e}")
            return None
        finally:
            if conn:
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
    avg_ratio = round(df['btc_to_eth'].mean(), 2)

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

    df['percentage_diff'] = df['btc_as_eth'] - df['close_eth']

    return df, avg_ratio
