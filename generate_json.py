import ccxt
import pandas as pd
import json
from datetime import datetime, timedelta
import time
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_exchange():
	"""Инициализация подключения к бирже"""
	exchange = ccxt.binance({
		'enableRateLimit': True,  # Включение лимита запросов
		'options': {
			'defaultType': 'spot',  # Торговля на спотовом рынке
		}
	})
	return exchange


def fetch_data(exchange, symbol, timeframe='1h', days=3, max_retries=3):
    """Загрузка данных с обработкой ошибок и повторными попытками"""
    since = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)
    data = None

    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching data for {symbol} (attempt {attempt + 1})")
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)

            if not ohlcv:
                logger.warning(f"No data received for {symbol}")
                return pd.DataFrame()

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df[['timestamp', 'close']]

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Задержка перед повторной попыткой
            else:
                logger.error(f"Max retries reached for {symbol}")
                return pd.DataFrame()


def calculate_metrics(btc_data, eth_data):
	"""Вычисление метрик спреда между BTC и ETH"""
	if btc_data.empty or eth_data.empty:
		raise ValueError("Empty data received for BTC or ETH")

	merged = pd.merge(btc_data, eth_data, on='timestamp', suffixes=('_btc', '_eth'))

	# Рассчитываем соотношение BTC/ETH
	merged['btc_to_eth'] = merged['close_btc'] / merged['close_eth']

	# Исключаем нулевые и аномальные значения
	merged = merged[merged['close_eth'] > 0]

	avg_ratio = merged['btc_to_eth'].mean()
	merged['btc_as_eth'] = merged['close_btc'] / avg_ratio

	# Процентная разница с защитой от деления на ноль
	merged['percentage_diff'] = merged.apply(
		lambda row: ((row['btc_as_eth'] - row['close_eth']) / row['close_eth']) * 100,
		axis=1
	)

	return merged


def format_data(df, col_name):
	"""Форматирование данных для Lightweight Charts"""
	return [
		{
			"time": int(row["timestamp"].timestamp()),  # Unix timestamp в секундах
			"value": float(row[col_name])  # Явное преобразование к float
		}
		for _, row in df.iterrows()
	]


def save_to_json(data, filename="chart_data.json"):
	"""Сохранение данных в JSON файл"""
	try:
		with open(filename, "w") as f:
			json.dump(data, f, indent=4)
		logger.info(f"✅ JSON файл {filename} успешно сохранен!")
		return True
	except Exception as e:
		logger.error(f"Error saving JSON file: {str(e)}")
		return False


def main():
	"""Основная функция"""
	exchange = initialize_exchange()

	# Загружаем данные
	btc_data = fetch_data(exchange, 'BTC/USDT', '1h', days=3)
	eth_data = fetch_data(exchange, 'ETH/USDT', '1h', days=3)

	if btc_data.empty or eth_data.empty:
		logger.error("Не удалось загрузить данные для BTC или ETH")
		return

	# Вычисляем метрики
	try:
		merged = calculate_metrics(btc_data, eth_data)
	except ValueError as e:
		logger.error(str(e))
		return

	# Форматируем данные для графиков
	chart_data = {
		"btc": format_data(merged, "close_btc"),
		"eth": format_data(merged, "close_eth"),
		"btc_as_eth": format_data(merged, "btc_as_eth"),
		"percentage_diff": format_data(merged, "percentage_diff"),
	}

	# Сохраняем в файл
	save_to_json(chart_data, filename="data/chart_data.json")


if __name__ == "__main__":
	main()