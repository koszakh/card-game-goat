from tkinter import Tk
from src.game import Game
from src.gui import GameGUI
from src.utils import load_config

if __name__ == "__main__":
    root = Tk()
    game = Game()
    host, port = load_config()
    gui = GameGUI(root, game, host, port)

    def on_connect():
        if gui.client_socket:
            name = "Игрок GUI"  # Или запросите имя у пользователя
            gui._send_message(f"CONNECT {name}")


    # Вызываем on_connect после успешного подключения (можно привязать к событию)
    root.after(100, on_connect)  # Задержка, чтобы дать время на подключение

    root.mainloop()