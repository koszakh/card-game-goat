import socket
import threading

HOST = '127.0.0.1'  # Адрес сервера (локальный хост)
PORT = 12345        # Порт сервера

def handle_client(conn, addr):
    print(f"[НОВОЕ СОЕДИНЕНИЕ] {addr} подключился.")
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            message = data.decode('utf-8')
            print(f"[{addr}] Получено: {message}")
            conn.sendall(f"Сервер получил твое сообщение: {message}".encode('utf-8'))
    except Exception as e:
        print(f"[ОШИБКА] Соединение с {addr} разорвано: {e}")
    finally:
        conn.close()
        print(f"[ОТКЛЮЧЕНИЕ] Соединение с {addr} закрыто.")

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"[СЕРВЕР ЗАПУЩЕН] Слушает на {HOST}:{PORT}")
        while True:
            conn, addr = server_socket.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()
            print(f"[АКТИВНЫЕ СОЕДИНЕНИЯ] {threading.active_count() - 1}")
    except Exception as e:
        print(f"[ОШИБКА СЕРВЕРА] {e}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    print("Стартуем!")
    start_server()