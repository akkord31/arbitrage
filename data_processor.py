import sqlite3
from pathlib import Path
import json
from datetime import datetime
import logging
import numpy as np
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
	def process_market_data(raw_data):
		"""Основная обработка рыночных данных с нормализацией"""
		result = {
			'btc': [],
			'eth': [],
			'btc_as_eth': [],
			'btc_norm': [],  # Нормализованный BTC
			'eth_norm': [],  # Нормализованный ETH
			'percentage_diff': []
		}

		for item in raw_data:
			try:
				time = int(datetime.fromisoformat(item['timestamp']).timestamp())
				btc = float(item['close_btc'])
				eth = float(item['close_eth'])

				result['btc'].append({'time': time, 'value': btc})
				result['eth'].append({'time': time, 'value': eth})

				if eth != 0:
					btc_eth = btc / eth
				result['btc_as_eth'].append({'time': time, 'value': btc_eth})

			except (ValueError, KeyError) as e:
				logger.warning(f"Ошибка обработки записи: {e}")

		# Нормализация данных и расчет разницы
		if result['btc_as_eth'] and result['eth']:
			try:
				# Преобразуем в numpy массивы
				btc_eth_values = np.array([x['value'] for x in result['btc_as_eth']]).reshape(-1, 1)
				eth_values = np.array([x['value'] for x in result['eth']]).reshape(-1, 1)

				# Нормализуем данные
				scaler = MinMaxScaler()
				btc_norm = scaler.fit_transform(btc_eth_values).flatten()
				eth_norm = scaler.fit_transform(eth_values).flatten()

				# Добавляем нормализованные данные
				for i, (btc_item, eth_item) in enumerate(zip(result['btc_as_eth'], result['eth'])):
					result['btc_norm'].append({
						'time': btc_item['time'],
						'value': float(btc_norm[i])
					})
					result['eth_norm'].append({
						'time': eth_item['time'],
						'value': float(eth_norm[i])
					})

					# Рассчитываем разницу
					result['percentage_diff'].append({
						'time': btc_item['time'],
						'value': (btc_norm[i] - eth_norm[i]) * 100  # В процентах
					})

			except Exception as e:
				logger.error(f"Ошибка нормализации данных: {e}")

		return result

	@staticmethod
	def get_processed_data(table_name='24h'):
		"""Получение и обработка данных из БД"""
		conn = sqlite3.connect(DB_PATH)
		conn.row_factory = sqlite3.Row
		cursor = conn.cursor()

		try:
			# Проверяем существование таблицы
			cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",
			               (f'market_data_{table_name}',))
			if not cursor.fetchone():
				return None

			# Получаем данные
			cursor.execute(f"""
                SELECT timestamp, close_btc, close_eth 
                FROM market_data_{table_name}
                ORDER BY timestamp
            """)

			raw_data = [dict(row) for row in cursor.fetchall()]
			return DataProcessor.process_market_data(raw_data)

		except sqlite3.Error as e:
			logger.error(f"Ошибка БД: {e}")
			return None
		finally:
			conn.close()
