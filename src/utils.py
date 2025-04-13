import configparser
import os
import sys

config_filename = 'config.txt'

def load_config():
    config = configparser.ConfigParser()
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(os.path.dirname(application_path), config_filename)
    try:
        config.read(config_file_path)
        server_host = config['SERVER']['host']
        server_port = int(config['SERVER']['port'])
        return server_host, server_port
    except (FileNotFoundError, KeyError, ValueError) as e:
        print(f"[ОШИБКА КОНФИГУРАЦИИ СЕРВЕРА]: Не удалось загрузить конфигурацию из config.txt: {e}")
        print("Используются значения по умолчанию.")
        return "0.0.0.0", 54321