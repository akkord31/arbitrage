import http.server
import socketserver
import webbrowser
import os
import time
import threading
from generate_json import main as update_chart_data
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutoRefreshHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
	def __init__(self, *args, **kwargs):
		# Указываем базовую директорию как папку templates
		self.base_directory = os.path.dirname(__file__)
		super().__init__(*args, directory=self.base_directory, **kwargs)

	def end_headers(self):
		self.send_header('Access-Control-Allow-Origin', '*')
		super().end_headers()

	def translate_path(self, path):
		# Обрабатываем запросы к данным (игнорируем параметры после ?)
		if path.startswith('/data/'):
			# Удаляем параметры запроса (всё, что после ?)
			clean_path = path.split('?')[0]
			# Формируем полный путь к файлу
			file_path = os.path.join(os.path.dirname(__file__), clean_path[1:])
			logger.info(f"Requested data path: {path} -> {file_path}")
			return file_path

		# Обрабатываем корневой запрос
		if path in ('/', '/index.html'):
			path = '/index.html'

		# Обрабатываем статические файлы (css, js)
		if path.startswith(('/css/', '/js/')):
			return os.path.join(os.path.dirname(__file__), 'templates', path[1:])

		# Все остальные запросы направляем в templates
		return os.path.join(os.path.dirname(__file__), 'templates', path[1:] if path != '/' else 'index.html')

def run_server(port=8000):
	"""Запуск HTTP сервера"""
	try:
		with socketserver.TCPServer(("", port), AutoRefreshHTTPRequestHandler) as httpd:
			logger.info(f"Сервер запущен на порту {port}")
			logger.info(f"Доступно по адресу: http://localhost:{port}/index.html")

			# Открываем браузер
			threading.Thread(
				target=lambda: (
					time.sleep(1),
					webbrowser.open(f'http://localhost:{port}/index.html')
				),
				daemon=True
			).start()

			logger.info("Для остановки сервера нажмите Ctrl+C")
			httpd.serve_forever()
	except OSError as e:
		logger.error(f"Ошибка запуска сервера: {e}")
		if "Address already in use" in str(e):
			logger.error(f"Порт {port} уже занят. Попробуйте другой порт.")
	except KeyboardInterrupt:
		logger.info("Сервер остановлен")
	except Exception as e:
		logger.error(f"Неожиданная ошибка: {e}")


def background_data_updater(interval=300):
	"""Фоновая задача для обновления данных"""
	while True:
		try:
			logger.info("Обновление данных...")
			update_chart_data()
			time.sleep(interval)
		except Exception as e:
			logger.error(f"Ошибка при обновлении данных: {e}")
			time.sleep(60)


if __name__ == "__main__":
	# Запускаем обновление данных в фоне
	updater_thread = threading.Thread(
		target=background_data_updater,
		daemon=True
	)
	updater_thread.start()

	# Запускаем сервер
	run_server(port=8000)
