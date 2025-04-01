import http.server
import socketserver
import webbrowser
import os
import time
import threading
import sqlite3
import json
from pathlib import Path
import logging

from data_processor import DataProcessor
import db_utils


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Путь к базе данных SQLite (создастся рядом с сервером)
DB_PATH = Path(__file__).parent / "market_data.db"


class AutoRefreshHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
	def __init__(self, *args, **kwargs):
		# Указываем базовую директорию как корень проекта
		self.base_directory = os.path.dirname(__file__)
		self.templates_dir = os.path.join(self.base_directory, 'templates')
		super().__init__(*args, directory=self.templates_dir, **kwargs)  # Указываем директорию templates

	def translate_path(self, path):
		# Обрабатываем API запросы
		if path.startswith('/api/'):
			return os.path.join(self.base_directory, path[1:])

		# Перенаправляем корневой запрос на index.html
		if path == '/' or path == '':
			path = '/index.html'

		# Полный путь к файлу
		full_path = os.path.join(self.templates_dir, path.lstrip('/'))

		# Проверяем существование файла
		if not os.path.exists(full_path):
			# Пробуем добавить .html если файл не найден
			if not os.path.exists(full_path + '.html'):
				return super().translate_path('/404.html')
			return full_path + '.html'

		return full_path

	def end_headers(self):
		# Добавляем необходимые заголовки
		self.send_header('Access-Control-Allow-Origin', '*')
		self.send_header('Cache-Control', 'no-store, max-age=0')
		super().end_headers()

	def do_GET(self):
		try:
			if self.path.startswith('/api/market-data'):
				return self.handle_market_data()
			elif self.path.startswith('/api/processed-data'):  # Новый эндпоинт
				return self.handle_processed_data()

			return super().do_GET()
		except Exception as e:
			logger.error(f"Request handling error: {e}")
			self.send_error(500, "Internal Server Error")

	def handle_processed_data(self):
		"""Отдает полностью обработанные данные для фронтенда"""
		try:
			# Получаем параметр table из запроса
			table_name = '24h'
			if '?' in self.path:
				query = self.path.split('?')[1]
				params = dict(p.split('=') for p in query.split('&'))
				table_name = params.get('table', '24h')

			# Получаем обработанные данные
			processed_data = DataProcessor.get_processed_data(table_name)
			if not processed_data:
				self.send_error(404, "Data not found")
				return

			# Отправляем ответ
			self.send_response(200)
			self.send_header('Content-Type', 'application/json')
			self.end_headers()
			self.wfile.write(json.dumps(processed_data).encode())

		except Exception as e:
			logger.error(f"Processed data error: {e}")
			self.send_error(500, "Internal Server Error")

	def handle_market_data(self):
		"""Оптимизированный обработчик API"""
		try:
			# Проверяем параметры запроса
			if '?' not in self.path:
				table_name = "market_data_24h"
			else:
				query = self.path.split('?')[1]
				params = dict(p.split('=') for p in query.split('&'))
				table_name = f"market_data_{params.get('table', '24h')}"

			# Быстрая проверка существования таблицы
			conn = sqlite3.connect(DB_PATH)
			cursor = conn.cursor()
			cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
			if not cursor.fetchone():
				self.send_error(404, f"Table {table_name} not found")
				return

			# Оптимизированный запрос с лимитом
			cursor.execute(f"""
                SELECT timestamp, close_btc, close_eth, btc_as_eth
                FROM {table_name} 
                ORDER BY timestamp DESC 
            """)

			# Быстрое формирование ответа
			self.send_response(200)
			self.send_header('Content-Type', 'application/json')
			self.send_header('X-Data-Source', table_name)
			self.end_headers()

			# Потоковая передача данных
			self.wfile.write(b'[')
			first = True
			for row in cursor:
				if not first:
					self.wfile.write(b',')
				first = False
				self.wfile.write(json.dumps({
					"timestamp": row[0],
					"close_btc": row[1],
					"close_eth": row[2],
					"btc_as_eth": row[3]
				}).encode())
			self.wfile.write(b']')

		except sqlite3.Error as e:
			logger.error(f"Database error: {e}")
			self.send_error(500, "Database operation failed")
		except Exception as e:
			logger.error(f"API error: {e}")
			self.send_error(500, "Internal Server Error")
		finally:
			conn.close()


def fetch_from_sqlite(table_name):
	"""Получаем данные из SQLite"""
	conn = sqlite3.connect(DB_PATH)
	cursor = conn.cursor()

	try:
		# Проверяем существование таблицы
		cursor.execute(f"""
            SELECT timestamp, close_btc, close_eth, btc_as_eth
            FROM {table_name} 
            ORDER BY timestamp DESC
        """)
		rows = cursor.fetchall()
		return [{
			"timestamp": row[0],
			"close_btc": row[1],
			"close_eth": row[2]
		} for row in rows]
	finally:
		conn.close()


def init_database():
	"""Инициализация БД (если не существует)"""
	if not DB_PATH.exists():
		logger.info("Создаем новую базу данных...")
		conn = sqlite3.connect(DB_PATH)
		try:
			# Создаем таблицы (пример структуры)
			conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data_24h (
                    timestamp TEXT PRIMARY KEY,
                    close_btc REAL,
                    close_eth REAL
                )
            """)
			conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data_180d (
                    timestamp TEXT PRIMARY KEY,
                    close_btc REAL,
                    close_eth REAL
                )
            """)
			conn.commit()
		finally:
			conn.close()


def check_database():
	"""Проверяем наличие таблиц и данных"""
	conn = sqlite3.connect(DB_PATH)
	try:
		cursor = conn.cursor()
		for table in ['market_data_24h', 'market_data_180d']:
			cursor.execute(f"SELECT COUNT(*) FROM {table}")
			count = cursor.fetchone()[0]
			logger.info(f"Table {table} contains {count} records")
	finally:
		conn.close()


def run_server(port=8000):
	"""Запуск HTTP сервера"""
	db_utils.main()

	init_database()
	check_database()  # Добавляем проверку

	try:
		with socketserver.TCPServer(("", port), AutoRefreshHTTPRequestHandler) as httpd:
			logger.info(f"Сервер запущен на порту {port}")
			logger.info(f"API доступно: http://localhost:{port}/api/market-data?table=24h")
			logger.info(f"Пример данных: http://localhost:{port}/api/market-data?table=180d")

			threading.Thread(
				target=lambda: (time.sleep(1), webbrowser.open(f'http://localhost:{port}/index.html')),
				daemon=True
			).start()

			httpd.serve_forever()
	except Exception as e:
		logger.error(f"Ошибка сервера: {e}")



if __name__ == "__main__":
	run_server(8080)