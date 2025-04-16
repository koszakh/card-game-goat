import traceback
import os
import sys
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import pygame
from PIL import Image, ImageTk
from itertools import permutations, chain
from src.card import Card
from src.deck import Deck
import socket
import threading
from dotenv import load_dotenv
import logging

logging.basicConfig(filename='gui_app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("GUI application started.")

load_dotenv()

INIT_OPPONENT_NAME = 'Оппонент'
SOUNDS_DIR = 'sounds'

class GameGUI:
    CARD_SIZE = (90, 135)
    CARD_OFFSET_X = 30  # Горизонтальное смещение между картами
    BASE_Y = 10  # Базовая Y координата для карт в руке
    SELECTED_OFFSET_Y = -10  # Вертикальное смещение ВВЕРХ при выборе (отрицательное)
    SELECTED_BORDER_WIDTH = 3
    def __init__(self, master, game, host, port):
        super().__init__()
        self.sounds_path = SOUNDS_DIR
        pygame.mixer.init()
        if hasattr(sys, '_MEIPASS'):
            self.sounds_path = os.path.join(sys._MEIPASS, SOUNDS_DIR)
            logging.info(f"Загрузка звуковых эффектов из временой папки: {self.sounds_path}")
        self.card_click_sound = pygame.mixer.Sound(os.path.join(self.sounds_path, 'click1.wav'))
        self.cards_play_sound = pygame.mixer.Sound(os.path.join(self.sounds_path, 'cards_on_table.wav'))
        self.card_take_sound = pygame.mixer.Sound(os.path.join(self.sounds_path, 'mb_card_deal_08.wav'))

        self.host = host
        self.port = port
        self.style = ttk.Style()
        self.style.configure("TFrame", background="#1B6134")
        self.style.configure("TLabelframe", background="#1B6134", foreground="white")
        self.style.configure("TLabelframe.Label", background="#1B6134", foreground="white")
        self.style.configure("TLabel", background="#1B6134", foreground="white")

        self.style.configure("Play.TButton",
                             font=("Arial", 14),
                             foreground="black",
                             # background="#4CAF50",  # Зеленый цвет
                             padding=10,
                             relief="raised",
                             borderradius=12)  # Атрибут borderradius не стандартный для ttk

        # Создаем новый стиль для кнопки "Отдать взятку"
        self.style.configure("Take.TButton",
                             font=("Arial", 14),
                             foreground="black",
                             # background="#F44336",
                             padding=10,
                             relief="raised",
                             borderradius=12)

        self.master = master
        self.master.title("Козел - Введите имя")
        self.master.config(bg="#1B6134")
        self.screen_width = self.master.winfo_screenwidth()
        self.screen_height = self.master.winfo_screenheight()

        window_width = 300
        window_height = 150

        # Рассчитайте координаты для центрирования окна
        center_x = int((self.screen_width - window_width) / 2)
        center_y = int((self.screen_height - window_height) / 2)

        # Установите геометрию окна с рассчитанными координатами
        self.master.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")

        self.game = game
        self.player_name = tk.StringVar()

        self.login_frame = ttk.Frame(self.master, style="TFrame")
        self.login_frame.pack(pady=20)

        name_label = ttk.Label(self.login_frame, text="Ваше имя:", style="TLabel")
        name_label.pack()

        name_entry = ttk.Entry(self.login_frame, textvariable=self.player_name)
        name_entry.pack(pady=5, padx=20)
        name_entry.focus_set()

        # Привязываем нажатие Enter к функции _connect_with_name
        name_entry.bind("<Return>", lambda event: self._connect_with_name())

        connect_button = ttk.Button(self.login_frame, text="Подключиться", command=self._connect_with_name)
        connect_button.pack(pady=10)

        self.game_frame = tk.Frame(self.master, bg="#1B6134")
        self.card_images = self._load_card_images()
        from src.player import Player
        self.game.players = [Player(''), Player(INIT_OPPONENT_NAME)]
        self.client_socket = None
        self.receive_thread = None
        self.game_elements_created = False

    def _connect_with_name(self):
        name = self.player_name.get().strip()
        if name:
            # Деактивируем кнопку сразу после начала попытки подключения
            for widget in self.login_frame.winfo_children():
                if isinstance(widget, ttk.Button) and widget.cget("text") == "Подключиться":
                    widget.config(state=tk.DISABLED)
                    break
            if not self.game_elements_created:
                self._connect_to_server(name)
                if self.client_socket:
                    self._create_game_ui(name)
                    self.login_frame.pack_forget() # Скрываем фрейм логина
                    self.game_frame.pack(fill=tk.BOTH, expand=True) # Отображаем фрейм игры
                    self.master.title("Козел")
                    # self.master.geometry(f"{self.screen_width}x{self.screen_height}+0+0")
                    self.master.attributes('-fullscreen', True)
                    self.master.resizable(False, False)
                    self._send_message(f"UI_LOADED")
        else:
            messagebox.showerror("Ошибка", "Имя не может быть пустым.")

    def _connect_to_server(self, player_name):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            logging.info(f"[КЛИЕНТ GUI ПОДКЛЮЧЕН] К серверу {self.host}:{self.port} под именем: {player_name}")
            self._send_message(f"CONNECT {player_name}")

            # Обновляем имя локального игрока
            self.game.players[0].name = player_name

            self.receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self.receive_thread.start()
        except Exception as e:
            messagebox.showerror("Ошибка подключения", f"Не удалось подключиться к серверу: {e}")
            self.master.destroy()

    def _create_game_ui(self, player_name):
        self.take_cards_phase_active = True
        self.deck_size = Deck.SIZE
        self.player_hand_frames = [
            ttk.LabelFrame(self.game_frame, text=f"Ваша рука ({player_name})", style="TLabelframe"),
            ttk.LabelFrame(self.game_frame, text=f"Рука Оппонента", style="TLabelframe")
        ]
        self.table_frame = ttk.LabelFrame(self.game_frame, text="Стол", style="TLabelframe")
        self.info_frame = ttk.LabelFrame(self.game_frame, text="Информация", style="TLabelframe")
        self.action_frame = ttk.Frame(self.game_frame, style="TFrame")

        self.game_frame.grid_columnconfigure(0, weight=1)
        self.game_frame.grid_columnconfigure(1, weight=0)

        # 4 строки: 0 - рука опп, 1 - стол (растяг.), 2 - рука игрока, 3 - кнопки
        self.game_frame.grid_rowconfigure(0, weight=0)
        self.game_frame.grid_rowconfigure(1, weight=1)  # Стол занимает основное верт. пространство
        self.game_frame.grid_rowconfigure(2, weight=0)
        self.game_frame.grid_rowconfigure(3, weight=0)

        std_padx = 10
        std_pady = 5

        self.player_hand_frames[1].grid(row=0, column=0, padx=std_padx, pady=std_pady, sticky="ew")
        self.player_hand_frames[1].grid_propagate(False)
        self.player_hand_frames[1].config(height=self.CARD_SIZE[1] + 35)

        self.table_frame.grid(row=1, column=0, padx=std_padx, pady=std_pady, sticky="nsew")
        self.table_frame.grid_propagate(False)  # Т.к. _update_table использует place

        self.player_hand_frames[0].grid(row=2, column=0, padx=std_padx, pady=std_pady, sticky="ew")
        self.player_hand_frames[0].grid_propagate(False)
        self.player_hand_frames[0].config(height=self.CARD_SIZE[1] + abs(self.SELECTED_OFFSET_Y) + 25)

        self.info_frame.grid(row=0, column=1, rowspan=4, padx=(0, std_padx), pady=std_pady, sticky="ne")
        # ttk.Label(self.info_frame, text="Колода:", style="TLabel").pack(anchor="nw", padx=5, pady=2)
        self.deck_count_label = ttk.Label(self.info_frame, text=f"{self.deck_size}", style="TLabel")
        self.deck_count_label.pack(anchor="nw", padx=5, pady=2)
        # ttk.Label(self.info_frame, text="Козырь:", style="TLabel").pack(anchor="nw", padx=5, pady=2)
        self.trump_label = ttk.Label(self.info_frame, text="", style="TLabel")
        self.trump_label.pack(anchor="nw", padx=5, pady=2)
        # ttk.Label(self.info_frame, text="Ход:", style="TLabel").pack(anchor="nw", padx=5, pady=2)
        self.turn_info_label = ttk.Label(self.info_frame, text="", style="TLabel")
        self.turn_info_label.pack(anchor="nw", padx=5, pady=2)

        ttk.Label(self.info_frame, text="Взятки:", style="TLabel").pack(anchor="nw", padx=5, pady=(10, 2))
        self.taken_cards_labels = {}
        for i, player in enumerate(self.game.players):
            name_to_use = player.name if player.name else (player_name if i == 0 else INIT_OPPONENT_NAME)
            label = ttk.Label(self.info_frame, text=f"{name_to_use}: 0 карт (0 очков)", style="TLabel")
            label.pack(anchor="nw", padx=5, pady=1)
            self.taken_cards_labels[name_to_use] = label

        ttk.Label(self.info_frame, text="Счет (голы):", style="TLabel").pack(anchor="nw", padx=5, pady=(10, 2))
        self.table_score_labels = {}
        for i, player in enumerate(self.game.players):
            name_to_use = player.name if player.name else (player_name if i == 0 else INIT_OPPONENT_NAME)
            label = ttk.Label(self.info_frame, text=f"{name_to_use}: 0", style="TLabel")
            label.pack(anchor="nw", padx=5, pady=1)
            self.table_score_labels[name_to_use] = label

        # Кнопки действий (строка 3, колонка 0)
        self.action_frame.grid(row=3, column=0, padx=std_padx, pady=std_pady, sticky="ew")
        # Центрирование кнопок внутри action_frame с помощью весов колонок
        self.action_frame.grid_columnconfigure(0, weight=1)
        self.action_frame.grid_columnconfigure(1, weight=0)  # Кнопка 1
        self.action_frame.grid_columnconfigure(2, weight=0)  # Кнопка 2
        self.action_frame.grid_columnconfigure(3, weight=1)

        self.play_button = ttk.Button(self.action_frame, text="Сделать ход", command=self._play_selected_cards,
                                      state=tk.DISABLED, style='Play.TButton')
        self.play_button.grid(row=0, column=1, padx=5, pady=5)  # Размещаем в колонке 1

        self.take_button = ttk.Button(self.action_frame, text="Отдать взятку", command=self._force_take_trick,
                                      state=tk.DISABLED, style='Take.TButton')
        self.take_button.grid(row=0, column=2, padx=5, pady=5)  # Размещаем в колонке 2

        # --- Финальные шаги ---
        self.selected_cards = []
        self.card_labels = {}
        self.cur_card_new_trump = False # Убедись, что этот флаг нужен
        self.game_elements_created = True

    def _receive_messages(self):
        buffer = ""
        try:
            while self.client_socket:
                data = self.client_socket.recv(1024)
                if not data:
                    break
                received_data = data.decode('utf-8')
                buffer += received_data
                while '\n' in buffer:
                    try:
                        newline_index = buffer.find('\n')
                        if newline_index != -1:
                            message = buffer[:newline_index]
                            buffer = buffer[newline_index + 1:]
                            if message:
                                logging.info(f"[КЛИЕНТ {self.game.players[0].name} GUI ОБРАБОТКА СООБЩЕНИЯ]: '{message}'")
                                self._process_message(message)
                        else:
                            break # No more complete messages in the buffer
                    except Exception as e:
                        traceback.print_exc()
                        logging.error(f"[КЛИЕНТ {self.game.players[0].name} GUI ОШИБКА РАЗБОРКИ]: {e}")
                        logging.info(f"[КЛИЕНТ {self.game.players[0].name} GUI БУФЕР ПЕРЕД ОШИБКОЙ]: '{buffer}'")
                        break
        except Exception as e:
            logging.error(f"[КЛИЕНТ GUI ОШИБКА ПРИЕМА]: {e}")
        finally:
            if self.client_socket:
                self.client_socket.close()
                logging.info("[КЛИЕНТ GUI ОТКЛЮЧЕН ОТ СЕРВЕРА]")

    def _process_message(self, message):
        logging.info(f"[КЛИЕНТ GUI ПОЛУЧИЛ] {message}")
        if message.startswith("TRUMP_SUIT"):
            trump_suit = message.split()[1]
            self.game.trump_suit = trump_suit
            if self.game_elements_created:
                self._update_info()
        elif message.startswith("TRUMP_CARD"):
            trump_card_str = message.split()[1]
            self.game.trump_card = Card.from_str(trump_card_str)
            if self.game_elements_created:
                self._update_info()
        elif message.startswith("OPPONENT_NAME"):
            opponent_name = message.split()[1]
            self.game.players[1].name = opponent_name
            self.taken_cards_labels[opponent_name] = self.taken_cards_labels[INIT_OPPONENT_NAME]
            self.taken_cards_labels.pop(INIT_OPPONENT_NAME)
            self.table_score_labels[opponent_name] = self.table_score_labels[INIT_OPPONENT_NAME]
            self.table_score_labels.pop(INIT_OPPONENT_NAME)
            if self.game_elements_created:
                self.player_hand_frames[1].config(text=f"Рука {opponent_name}")
                self._update_info()
                self._update_hands()
        elif message.startswith("FIRST_PLAYER"):
            first_player_name = message.split()[1]
            first_player_index = self.game.get_player_index(first_player_name)
            self.game.current_player_index = first_player_index
            if self.game_elements_created:
                self._update_info()
                self._update_action_buttons()
        elif message.startswith("OPPONENT_PLAYED"):
            cards_str = message.split()[1:]
            opponent_played_cards = [Card.from_str(card_str) for card_str in cards_str]
            self.game.current_player_index = 0
            self.game.update_played_cards_dict(opponent_played_cards, 1)
            self.game.ordered_played_cards.append(opponent_played_cards)
            self.game.players[1].hand = self.game.players[1].hand[len(opponent_played_cards):]
            if self.game_elements_created:
                self._update_gui()
        elif message.startswith("PLAY"):
            parts = message.split()
            player_name = parts[1]
            played_cards_str = parts[2:]
            played_cards = [Card.from_str(card_str) for card_str in played_cards_str]
            self.game.update_played_cards_dict(played_cards, 0)
            self.game.ordered_played_cards.append(played_cards)
            logging.info(f"[КЛИЕНТ GUI]: Игрок {player_name} сыграл карты: {played_cards}")
            self.cards_play_sound.play()
            self._update_table()
            self._update_hands()
        elif message.startswith("TAKE_CARD"):
            parts = message.split()
            name = parts[1]
            card_str = parts[2]
            card = Card.from_str(card_str)

            player, index = self.get_player_by_name(name)
            self.decrease_deck_size()
            if index == 0:
                logging.info(f"[КЛИЕНТ GUI]: Вы взяли карту {card}.")
                player.add_cards([card])
            else:
                player.add_cards([None])
            self.card_take_sound.play()
            self._update_hands()
            self._update_info()
        elif message.startswith("TRICK"):
            parts = message.split()
            name = parts[1]
            last_selected_cards_str = parts[2:]
            last_selected_cards = [Card.from_str(card_str) for card_str in last_selected_cards_str]

            winner, winner_index = self.get_player_by_name(name)
            looser, looser_index = self.get_other_player(name)

            if looser_index == 0:
                for card_to_remove in list(self.selected_cards):
                    if card_to_remove in looser.hand:
                        looser.hand.remove(card_to_remove)
            else:
                winner_turns_count = len(self.game.get_player_played_cards(winner_index))
                looser_turns_count = len(self.game.get_player_played_cards(looser_index))
                if winner_turns_count != looser_turns_count:
                    looser.hand = looser.hand[len(self.game.get_player_last_played_cards(winner_index)):]

            taken_cards = list(
                chain.from_iterable(chain.from_iterable(self.game.played_cards.values())))
            taken_cards += last_selected_cards
            winner.taken_cards.extend(taken_cards)

            self.game.played_cards = {}
            self.game.ordered_played_cards = []
            self.game.current_player_index = winner_index
            self._clear_table()
            self._update_gui()
            self._clear_selection()
            # self._check_round_end()
        elif message.startswith('ROUND_OVER'):
            self.game.calculate_and_update_table_scores()
            player1 = self.game.players[0]
            player2 = self.game.players[1]

            player1_points = player1.points
            player2_points = player2.points

            if player1_points > player2_points:
                message = f"В этом раунде победил {self.game.players[0].name}!\nУ {self.game.players[0].name}: {player1_points} очков.\nУ {self.game.players[1].name}: {player2_points} очков."
            elif player2_points > player1_points:
                message = f"В этом раунде победил {self.game.players[1].name}!\nУ {self.game.players[0].name}: {player1_points} очков.\nУ {self.game.players[1].name}: {player2_points} очков."
            else:
                message = "В этом раунде ничья! У обоих игроков по {player1_points} очков."

            self.deck_size = len(self.game.deck.cards)

            messagebox.showinfo("Конец раунда", message)
        elif message.startswith('GAME_OVER'):
            self.game.calculate_and_update_table_scores()
            player1 = self.game.players[0]
            player2 = self.game.players[1]

            winner = player1 if player1.table_scores < 12 else player2
            message = f"Игра завершена. Победил {winner.name}!"
            messagebox.showinfo("Конец раунда", message)

    def _send_message(self, message):
        logging.info(f"[КЛИЕНТ GUI]: Попытка отправки сообщения: '{message}'")
        try:
            if self.client_socket:
                self.client_socket.sendall(message.encode('utf-8'))
                logging.info(f"[КЛИЕНТ GUI]: Сообщение успешно отправлено: '{message}'")
            else:
                logging.info("[КЛИЕНТ GUI ОШИБКА]: Нет подключения к серверу, сообщение не отправлено.")
        except Exception as e:
            logging.error(
                f"[ОШИБКА ОТПРАВКИ] {e}")
            messagebox.showerror("Ошибка отправки", f"Не удалось отправить сообщение на сервер: {e}")
            self.master.destroy()

    def _load_card_images(self):
        images = {}
        cards_dir = "cards"  # Исходное имя директории
        if hasattr(sys, '_MEIPASS'):
            cards_dir = os.path.join(sys._MEIPASS, 'cards')
            logging.info(f"Загрузка изображений из временной директории: {cards_dir}")
        else:
            logging.info(f"Загрузка изображений из локальной директории: {cards_dir}")

        try:
            for filename in os.listdir(cards_dir):
                if filename.endswith(".png"):
                    try:
                        image_path = os.path.join(cards_dir, filename)
                        image = Image.open(image_path)
                        image = image.resize(self.CARD_SIZE)
                        photo = ImageTk.PhotoImage(image)
                        card_name = os.path.splitext(filename)[0]
                        if card_name != 'back':
                            rank, suit_str = card_name.split('_')
                            key = f"{rank}{Card.get_suit_mark(suit_str)}"
                        else:
                            key = 'back'
                        images[key] = photo
                        logging.info(f"Успешно загружено изображение: {image_path}")
                    except Exception as e:
                        traceback.print_exc()
                        logging.error(f"Ошибка при загрузке изображения {filename}: {e}")
        except FileNotFoundError:
            traceback.print_exc()
            logging.error(f"Директория с картами не найдена: {cards_dir}")
        except Exception as e:
            logging.error(f"Ошибка при доступе к директории с картами: {e}")
        return images

    def _create_card_label(self, frame, card, background='#1B6134'):
        if str(card) in self.card_images:
            label = ttk.Label(frame, image=self.card_images[str(card)], background=background)
        else:
            label = ttk.Label(frame, image=self.card_images['back'], background=background)
        label.card = card # Для отслеживания выбранной карты
        return label

    def _toggle_card_selection(self, event):
        label = event.widget
        card = label.card
        if card in self.selected_cards:
            self.selected_cards.remove(card)
            label.config(relief=tk.FLAT)
        else:
            self.selected_cards.append(card)
            label.config(relief=tk.SUNKEN)
        self._update_action_buttons()

    def _update_hands(self):
        """Обновляет отображение карт в руках игроков. Использует place для игрока."""
        if not self.game_elements_created or not self.game.players:
            return

        logging.debug("Вызван _update_hands (с использованием place для игрока)")
        player = self.game.players[0]
        opponent = self.game.players[1]

        player_frame = self.player_hand_frames[0]
        opponent_frame = self.player_hand_frames[1]

        # --- Очистка и подготовка ---
        for widget in player_frame.winfo_children():
            widget.destroy()
        for widget in opponent_frame.winfo_children():
            widget.destroy()

        # Пересоздаем словари ссылок на виджеты
        self.card_labels = {}
        if player.name:
            self.card_labels[player.name] = {}
        if opponent.name:
            self.card_labels[opponent.name] = {}

        # --- Отрисовка руки игрока (используем place) ---
        if player.name and player.hand:
            x_offset = 10  # Начальный отступ слева
            player_hand_dict = self.card_labels[player.name]

            # Сортируем карты для консистентного отображения (опционально, но рекомендуется)
            try:
                 sorted_hand = sorted(player.hand, key=lambda c: (Card.SUITS.index(c.suit) if c.suit in Card.SUITS else 99, list(Card.RANKS.keys()).index(c.rank) if c.rank in Card.RANKS else 99))
            except Exception as sort_e:
                 logging.error(f"Ошибка сортировки карт игрока: {sort_e}.", exc_info=True)
                 sorted_hand = player.hand

            for card in sorted_hand:
                if card is None: continue
                card_str = str(card)
                card_image = self.card_images.get(card_str)
                if card_image:
                    label = ttk.Label(player_frame, image=card_image, borderwidth=0)
                    label.image = card_image
                    label.card = card
                    # Сохраняем базовые координаты для place и смещения
                    label.base_x = x_offset
                    label.base_y = self.BASE_Y

                    label.bind("<Button-1>", lambda event, c=card: self._on_card_click(c))

                    # Размещаем карту с помощью place
                    label.place(x=x_offset, y=self.BASE_Y)
                    player_hand_dict[card] = label
                    x_offset += self.CARD_OFFSET_X
                else:
                    logging.warning(f"Изображение для карты игрока {card_str} не найдено.")
                    # Можно добавить запасной вариант (текст)

        # --- Отрисовка руки оппонента (используем pack) ---
        if opponent.name and opponent.hand:
            opponent_hand_dict = self.card_labels[opponent.name]  # Получаем словарь для виджетов оппонента
            back_image = self.card_images.get('back')
            x_offset_opponent = 10  # Начальный X для карт оппонента

            if back_image:
                # Рисуем столько рубашек, сколько карт у оппонента (предполагается, что opponent.hand содержит нужное кол-во элементов, например None)
                for i in range(len(opponent.hand)):
                    label = ttk.Label(opponent_frame, image=back_image, borderwidth=0)
                    label.image = back_image
                    # label.card = None # Не обязательно хранить карту для рубашки

                    # --- Используем place вместо pack ---
                    label.place(x=x_offset_opponent, y=self.BASE_Y)  # Размещаем по X и базовому Y
                    x_offset_opponent += self.CARD_OFFSET_X  # Сдвигаем X для следующей карты

                    # Сохраняем виджеты рубашек, если нужно (например, для анимации удаления)
                    # opponent_hand_dict[i] = label # Ключом может быть индекс или другой идентификатор
            else:
                logging.warning("Изображение рубашки 'back' не найдено для руки оппонента.")
                # Запасной вариант - текстовые метки с place
                for i in range(len(opponent.hand)):
                    label = ttk.Label(opponent_frame, text="?", relief="solid", borderwidth=1)
                    label.place(x=x_offset_opponent, y=self.BASE_Y, width=self.CARD_SIZE[0] - 10,
                                height=self.CARD_SIZE[1] - 10)
                    x_offset_opponent += self.CARD_OFFSET_X

        # --- Восстановление выделения для карт игрока ---
        self._restore_selection_highlight()

    def _update_table(self):
        if self.game_elements_created and self.game.played_cards:
            frame = self.table_frame
            for widget in frame.winfo_children():
                widget.destroy()

            x_start = 15  # Фиксированная x-координата для карт игрока
            y_start = 10
            card_spacing_x = self.CARD_OFFSET_X
            turn_spacing_y = 32

            for i, played_cards in enumerate(self.game.ordered_played_cards):
                player_current_x = x_start
                current_y_player = y_start + i * turn_spacing_y
                for card in played_cards:
                    card_label_player = self._create_card_label(frame, card)
                    card_label_player.place(x=player_current_x, y=current_y_player)
                    player_current_x += card_spacing_x

    def _update_info(self):
        if self.game_elements_created:
            self.deck_count_label.config(text=f"Колода: {self.deck_size}")
            if self.game.trump_suit and self.game.trump_card:
                self.trump_label.config(text=f"Козырь: {self.game.trump_suit} ({self.game.trump_card})")
            else:
                self.trump_label.config(text="")
            if self.game.current_player_index is not None:
                self.turn_info_label.config(text=f"Ходит: {self.game.players[self.game.current_player_index].name}")
            elif self.game.cards_to_take > 0:
                taking_player = self.game.players[(self.game.current_player_index + 1) % len(self.game.players)]
                self.turn_info_label.config(text=f"{taking_player.name} берет карты.")
            else:
                self.turn_info_label.config(text="")

            for player in self.game.players:
                if player.name in self.taken_cards_labels:
                    cards_count = len(player.taken_cards)
                    player_points = player.calc_points()
                    self.taken_cards_labels[player.name].config(
                        text=f"{player.name} взял(а): {cards_count} карт ({player_points} очков)")
                if player.name in self.table_score_labels:

                    self.table_score_labels[player.name].config(text=f"{player.name}: {player.table_scores} баллов")

    def _update_gui(self):
        if self.game_elements_created:
            self._update_hands()
            self._update_table()
            self._update_info()
            self._update_action_buttons()

    def _update_action_buttons(self):
        if self.game_elements_created:
            if self.game.current_player_index is not None:
                is_my_turn = self.game.current_player_index == 0

                self.play_button.config(state=tk.DISABLED)
                self.take_button.config(state=tk.DISABLED)

                if is_my_turn:
                    if self.is_play_button_must_be_active():
                        self.play_button.config(state=tk.NORMAL)

                    if self.is_take_button_must_be_active():
                        self.take_button.config(state=tk.NORMAL)
            else:
                self.play_button.config(state=tk.DISABLED)
                self.take_button.config(state=tk.DISABLED)


    def _on_card_click(self, card):
        """Обрабатывает клик по карте в руке игрока."""
        if self.game.current_player_index != 0:
            return # Игнорируем клик не в свой ход

        player_name = self.game.players[0].name
        widget = self.card_labels.get(player_name, {}).get(card)
        if not widget: return # Виджет не найден

        logging.debug(f"Клик по карте: {card}. Выбрана: {card in self.selected_cards}")

        self.card_click_sound.play()
        if card in self.selected_cards:
            self.selected_cards.remove(card)
            self._move_card(0, card, 0)
        else:
            self.selected_cards.append(card)
            self._move_card(0, card, self.SELECTED_OFFSET_Y)

        self._update_action_buttons()

    def _move_card(self, player_index, card, offset_y):
        """Перемещает виджет карты игрока по оси Y, используя place."""
        if player_index != 0: return  # Работает только для игрока 0

        player_name = self.game.players[player_index].name
        widget = self.card_labels.get(player_name, {}).get(card)

        # Проверяем наличие виджета и сохраненных базовых координат
        if widget and hasattr(widget, 'base_x') and hasattr(widget, 'base_y'):
            try:
                current_x = widget.base_x  # Используем сохраненную X
                new_y = widget.base_y + offset_y  # Рассчитываем новую Y от базовой
                widget.place(x=current_x, y=new_y)  # Перемещаем виджет
                logging.debug(f"Карта {card} игрока {player_name} перемещена в y={new_y}")
            except Exception as e:
                logging.error(f"Ошибка при перемещении карты {card}: {e}", exc_info=True)
        else:
            logging.warning(
                f"Не удалось переместить карту {card} игрока {player_name}: виджет или base_x/base_y не найдены.")

    def _draw_border(self, player_index, card, selected):
        """Рисует или убирает рамку/рельеф у виджета карты игрока."""
        if player_index != 0: return # Работает только для игрока 0

        player_name = self.game.players[player_index].name
        widget = self.card_labels.get(player_name, {}).get(card)

        if widget:
            try:
                if selected:
                    # Применяем рельеф и толщину рамки для выделения
                    widget.config(relief="raised", borderwidth=self.SELECTED_BORDER_WIDTH)
                else:
                    # Возвращаем стандартный вид
                    widget.config(relief="flat", borderwidth=0)
                logging.debug(f"Рамка/рельеф для карты {card} игрока {player_name} установлена в selected={selected}")
            except Exception as e:
                 logging.error(f"Ошибка при отрисовке рамки/рельефа для карты {card}: {e}", exc_info=True)

    def _restore_selection_highlight(self):
        """Восстанавливает визуальное выделение (рамка и подъем)
           для выбранных карт игрока после перерисовки руки."""
        if not self.game_elements_created or not hasattr(self, 'selected_cards'):
            return
        logging.debug("Вызван _restore_selection_highlight")

        player_name = self.game.players[0].name
        widgets_dict = self.card_labels.get(player_name, {}) # Виджеты текущей руки игрока

        for card_widget in widgets_dict.values():
             if hasattr(card_widget, 'base_x') and hasattr(card_widget, 'base_y'):
                 try:
                     card_widget.place(x=card_widget.base_x, y=card_widget.base_y) # Возвращаем на место
                     card_widget.config(relief="flat", borderwidth=0) # Снимаем рельеф
                 except Exception as e:
                      # Логируем ошибку, если виджет уже удален или недоступен
                      logging.error(f"Ошибка сброса карты {getattr(card_widget, 'card', '??')} при восстановлении: {e}", exc_info=False)


        if self.selected_cards:
             logging.debug(f"Восстановление выделения для: {self.selected_cards}")
             for card in self.selected_cards:
                 widget_to_highlight = widgets_dict.get(card) # Ищем виджет для выбранной карты
                 if widget_to_highlight:
                      # self._draw_border(0, card, True)
                      self._move_card(0, card, self.SELECTED_OFFSET_Y)
                 else:
                      logging.warning(f"Карта {card} из selected_cards не найдена в текущих виджетах {player_name} при восстановлении.")

    def _can_beat_all_selected(self, selected_cards, played_cards):
        if len(selected_cards) != len(played_cards) or not played_cards:
            return False

        played_cards_only = [pc for pc in played_cards]

        for perm in permutations(selected_cards):
            can_beat_all = True
            for i in range(len(played_cards_only)):
                if not self._can_beat_single(perm[i], played_cards_only[i]):
                    can_beat_all = False
                    break
            if can_beat_all:
                return True
        return False

    def _can_beat_single(self, beating_card, played_card):
        """Проверяет, может ли одна карта побить другую."""
        if beating_card.suit == played_card.suit and list(Card.RANKS.keys()).index(beating_card.rank) > list(Card.RANKS.keys()).index(played_card.rank):
            return True
        elif beating_card.suit == self.game.trump_suit and played_card.suit != self.game.trump_suit:
            return True
        elif beating_card.suit == self.game.trump_suit and played_card.suit == self.game.trump_suit and list(Card.RANKS.keys()).index(beating_card.rank) > list(Card.RANKS.keys()).index(played_card.rank):
            return True
        return False

    def _play_selected_cards(self):
        if not self.selected_cards:
            return

        self.cards_play_sound.play()
        card_strings = [str(card) for card in self.selected_cards]
        message = f"PLAY {' '.join(card_strings)}"
        logging.info(f"[КЛИЕНТ GUI]: Отправляется сообщение: {message}")
        self._send_message(message)
        self.game.update_played_cards_dict(self.selected_cards, 0)
        self.game.ordered_played_cards.append(self.selected_cards)
        self.game.current_player_index = 1
        for card in self.selected_cards:
            self.game.players[0].hand.remove(card)

        self.selected_cards = []
        self._clear_card_selection_ui()

        self._update_gui()

    def _clear_table(self):
        if self.game_elements_created:
            logging.info("[КЛИЕНТ GUI]: Очистка стола.")
            self.game.played_cards = {}  # Очищаем словарь сыгранных карт
            self.game.ordered_played_cards = []
            for widget in self.table_frame.winfo_children():
                widget.destroy()  # Уничтожаем все виджеты на фрейме стола

    def _clear_selection(self):
        self.selected_cards = []
        self._clear_card_selection_ui()
        self._update_action_buttons()

    def _clear_card_selection_ui(self):
        # Проходим по всем виджетам карт в руках (только игрок 0 может выбирать)
        player_name = self.game.players[0].name
        if player_name in self.card_labels:
            for label in self.card_labels[player_name].values():
                # Сбрасываем рамку и рельеф
                label.config(relief="flat", borderwidth=0)
                # Сбрасываем фон, если меняли его
                # label.config(background=self.style.lookup("TFrame", "background"))

    def _force_take_trick(self):
        selected_cards_str = [str(card) for card in self.selected_cards]
        self._send_message(f"TRICK {' '.join(selected_cards_str)}")

    def update_game_state(self):
        """Обновляет отображение всех элементов интерфейса."""
        self._update_gui()

    def is_take_button_must_be_active(self):
        current_player_index = self.game.current_player_index
        opponent_index = (self.game.current_player_index + 1) % self.game.PLAYERS_COUNT

        current_player_played_cards = self.game.get_player_played_cards(current_player_index)
        opponent_played_cards = self.game.get_player_played_cards(opponent_index)
        
        current_player_cards_count = sum(len(move) for move in current_player_played_cards)
        opponent_cards_count = sum(len(move) for move in opponent_played_cards)
        selected_cards_count = len(self.selected_cards)

        if self.game.played_cards and ((self.game.played_cards and current_player_cards_count == opponent_cards_count \
                                        and not self.selected_cards)
            or current_player_cards_count + selected_cards_count == opponent_cards_count):
            return True
        return False
        
    def is_play_button_must_be_active(self):
        opponent_player_index = (self.game.current_player_index + 1) % self.game.PLAYERS_COUNT

        last_opponent_played_cards = self.game.get_player_last_played_cards(opponent_player_index)
        turn_cards_count = len(last_opponent_played_cards)
        selected_cards_count = len(self.selected_cards)

        if not self.game.played_cards:
            if self.selected_cards:
                first_suit = self.selected_cards[0].suit
                if all(card.suit == first_suit for card in self.selected_cards):
                    return True
        else:
            if self.selected_cards and selected_cards_count == turn_cards_count:
                can_beat_all = self._can_beat_all_selected(self.selected_cards, last_opponent_played_cards)
                if can_beat_all:
                    return True
        return False

    def _check_round_end(self):
        if not self.game.deck.cards and not self.game.players[0].hand and not self.game.players[1].hand:
            self.game.calculate_and_update_table_scores()  # Подсчитываем очки за раунд
            player1 = self.game.players[0]
            player2 = self.game.players[1]

            player1_points = player1.points
            player2_points = player2.points

            if player1_points > player2_points:
                message = f"В этом раунде победил {self.game.players[0].name}!\nУ {self.game.players[0].name}: {player1_points} очков.\nУ {self.game.players[1].name}: {player2_points} очков."
            elif player2_points > player1_points:
                message = f"В этом раунде победил {self.game.players[1].name}!\nУ {self.game.players[0].name}: {player1_points} очков.\nУ {self.game.players[1].name}: {player2_points} очков."
            else:
                message = "В этом раунде ничья! У обоих игроков по {player1_points} очков."

            messagebox.showinfo("Конец раунда", message)
            self._start_new_round()  # Предложим начать новый раунд

    def _start_new_round(self):
        if messagebox.askyesno("Новый раунд", "Хотите начать новый раунд?"):
            self.game.start_game()
            self.selected_cards = []
            self._update_gui()

    def get_player_by_name(self, name):
        return (self.game.players[0], 0) if self.game.players[0].name == name else (self.game.players[1], 1)

    def get_other_player(self, name):
        return (self.game.players[0], 0) if self.game.players[1].name == name else (self.game.players[1], 1)

    def decrease_deck_size(self, cards_count = 1):
        self.deck_size -= cards_count