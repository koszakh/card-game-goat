import socket

HOST = '127.0.0.1'  # Адрес сервера
PORT = 12345        # Порт сервера

def start_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((HOST, PORT))
        print(f"[КЛИЕНТ ПОДКЛЮЧЕН] К серверу {HOST}:{PORT}")
        while True:
            message = input("Введите сообщение серверу (или 'exit' для выхода): ")
            if message.lower() == 'exit':
                break
            client_socket.sendall(message.encode('utf-8'))
            data = client_socket.recv(1024)
            response = data.decode('utf-8')
            print(f"[ОТВЕТ СЕРВЕРА] {response}")
    except Exception as e:
        print(f"[ОШИБКА КЛИЕНТА] {e}")
    finally:
        client_socket.close()
        print("[КЛИЕНТ ОТКЛЮЧЕН]")

if __name__ == "__main__":
    print()
    start_client()