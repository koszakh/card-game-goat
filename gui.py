
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from card import Card
import itertools

class GameGUI:
    def __init__(self, master, game):
        self.master = master
        self.master.title("Козел")
        self.master.config(bg="#1B6134")
        self.master.geometry("800x600")

        self.style = ttk.Style()
        self.style.configure("TFrame", background="#1B6134")
        self.style.configure("TLabelframe", background="#1B6134", foreground="white")
        self.style.configure("TLabelframe.Label", background="#1B6134", foreground="white")
        self.style.configure("TLabel", background="#1B6134", foreground="white")
        self.style.configure("TButton", background="#d9d9d9")

        self.game = game
        self.card_images = self._load_card_images()
        self.player_hand_frames = [ttk.LabelFrame(self.master, text=f"Рука {player.name}", style="TLabelframe") for player in self.game.players]
        for i, frame in enumerate(self.player_hand_frames):
            frame.grid(row=i, column=0, padx=5, pady=5, sticky="ew")
        self.table_frame = ttk.LabelFrame(self.master, text="Стол", style="TLabelframe")
        self.table_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew", columnspan=2)
        self.info_frame = ttk.LabelFrame(self.master, text="Информация", style="TLabelframe")
        self.info_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nw", rowspan=2)
        ttk.Label(self.info_frame, text="Колода:", style="TLabel").pack(anchor="nw")
        self.deck_count_label = ttk.Label(self.info_frame, text="", style="TLabel")
        self.deck_count_label.pack(anchor="nw")
        ttk.Label(self.info_frame, text="Козырь:", style="TLabel").pack(anchor="nw")
        self.trump_label = ttk.Label(self.info_frame, text="", style="TLabel")
        self.trump_label.pack(anchor="nw")
        self.turn_info_label = ttk.Label(self.info_frame, text="", style="TLabel")
        self.turn_info_label.pack(anchor="nw")

        self.taken_cards_labels = {}
        for i, player in enumerate(self.game.players):
            label = ttk.Label(self.info_frame, text=f"{player.name} взял(а): 0 карт (0 очков)", style="TLabel")
            label.pack(anchor="nw")
            self.taken_cards_labels[player.name] = label

        self.table_score_labels = {}
        for i, player in enumerate(self.game.players):
            label = ttk.Label(self.info_frame, text=f"{player.name}: {player.table_scores} очков", style="TLabel")
            label.pack(anchor="nw")
            self.table_score_labels[player.name] = label

        self.action_frame = ttk.Frame(self.master, style="TFrame")
        self.action_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        self.play_button = ttk.Button(self.action_frame, text="Сделать ход", command=self._play_selected_cards, state=tk.DISABLED)
        self.play_button.pack(side=tk.LEFT, padx=5)
        self.take_button = ttk.Button(self.action_frame, text="Отдать взятку", command=self._force_take_trick, state=tk.DISABLED) # Переименовано
        self.take_button.pack(side=tk.LEFT, padx=5)

        self.selected_cards = []
        self.card_labels = {}
        self.cur_card_new_trump = False
        self._update_gui()

    def _load_card_images(self):
        images = {}
        for suit in Card.SUITS:
            for rank in list(Card.RANKS.keys()):
                filename = f"cards/{rank}{suit}.png"
                try:
                    img = Image.open(filename)
                    img = img.resize((60, 90))
                    images[f"{rank}{suit}"] = ImageTk.PhotoImage(img)
                except FileNotFoundError:
                    print(f"Не удалось загрузить изображение: {filename}")
        return images

    def _create_card_label(self, frame, card, is_opponent=False):
        if str(card) in self.card_images:
            label = ttk.Label(frame, image=self.card_images[str(card)])
        else:
            label = ttk.Label(frame, text=str(card), style="TLabel")
        label.card = card # Для отслеживания выбранной карты
        if not is_opponent:
            label.bind("<Button-1>", self._toggle_card_selection)
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
        for i, player in enumerate(self.game.players):
            frame = self.player_hand_frames[i]
            for widget in frame.winfo_children():
                widget.destroy()
            self.card_labels[player.name] = {}
            sorted_hand = sorted(player.hand, key=lambda card: (Card.SUITS.index(card.suit), list(Card.RANKS.keys()).index(card.rank)))
            for card in sorted_hand:
                label = self._create_card_label(frame, card, is_opponent=(i != self.game.current_player_index))
                label.pack(side=tk.LEFT, padx=2)
                self.card_labels[player.name][card] = label

    def _update_table(self):
        frame = self.table_frame
        for widget in frame.winfo_children():
            widget.destroy()
        player_label_displayed = {}
        for player in self.game.players:
            player_label_displayed[player.name] = False

        for player_index_str in self.game.played_cards.keys():
            moves = self.get_player_played_cards(player_index_str)
            # print(player_index_str, moves)
            player_index = int(player_index_str)
            player = self.game.players[player_index]
            for move in moves:
                if not player_label_displayed[player.name]:
                    label_text = f"{player.name}:"
                    ttk.Label(frame, text=label_text, style="TLabel").pack(side=tk.LEFT, padx=2)
                    player_label_displayed[player.name] = True
                for card in move:
                    card_label = self._create_card_label(frame, card, is_opponent=True)
                    card_label.pack(side=tk.LEFT, padx=2)

    def _update_info(self):
        self.deck_count_label.config(text=f"{len(self.game.deck.cards)}")
        if self.game.trump_suit and self.game.trump_card:
            self.trump_label.config(text=f"{self.game.trump_suit} ({self.game.trump_card})")
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
                self.table_score_labels[player.name].config(text=f"{player.name}: {player.table_scores} очков")

    def _update_gui(self):
        self._update_hands()
        self._update_table()
        self._update_info()
        self._update_action_buttons()

    def _update_action_buttons(self):
        if self.game.current_player_index is not None:
            is_my_turn = True # Для тестирования даем управлять обоими: current_player_name == "Игрок 1"

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

    def _can_beat_all_selected(self, selected_cards, played_cards):
        if len(selected_cards) != len(played_cards) or not played_cards:
            return False

        played_cards_only = [pc for pc in played_cards]
        from itertools import permutations

        for perm in permutations(selected_cards):
            can_beat_all = True
            for i in range(len(played_cards_only)):
                if not self._can_beat_single(perm[i], played_cards_only[i]):
                    can_beat_all = False
                    break
            if can_beat_all:
                return True
        return False

    def _find_beating_pairs(self, available_cards, played_cards):
        """Находит возможные пары для отбития."""
        pairs = []
        from itertools import permutations
        for perm in permutations(available_cards, len(played_cards)):
            can_beat_all = True
            current_beat = {}
            temp_available = list(available_cards)
            temp_perm = list(perm)
            possible = True
            for i in range(len(played_cards)):
                played_card = played_cards[i]
                beating_card = temp_perm[i]
                if not self._can_beat_single(beating_card, played_card):
                    possible = False
                    break
            if possible:
                pairs.append(list(perm))
        return pairs

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

        current_player_index = self.game.current_player_index
        opponent_index = (self.game.current_player_index + 1) % self.game.PLAYERS_COUNT
        current_player = self.game.players[current_player_index]
        num_selected = len(self.selected_cards)
        played_by_current = self.get_player_last_played_cards(current_player_index)
        played_by_opponent = self.get_player_last_played_cards(opponent_index)
        played_by_opponent_count = len(played_by_opponent)

        if not self.game.played_cards:  # Первый ход игрока
            first_suit = self.selected_cards[0].suit
            if all(card.suit == first_suit for card in self.selected_cards):
                if self.game.make_move(current_player, self.selected_cards):
                    self._after_player_move()
                else:
                    self._handle_invalid_move()
            else:
                messagebox.showerror("Ошибка хода", "Для первого хода все выбранные карты должны быть одной масти.")
                self._clear_selection()
        else:  # Ответ или перебитие
            if num_selected == played_by_opponent_count:
                can_beat_all = self._can_beat_all_selected(self.selected_cards, played_by_opponent)
                if can_beat_all:
                    if self.game.make_move(current_player, self.selected_cards):
                        self._after_opponent_move()  # Теперь это может быть и перебитие
                    else:
                        self._handle_invalid_move()
                else:
                    messagebox.showerror("Ошибка хода", "Выбранные карты не могут побить все выложенные карты.")
                    self._clear_selection()
            else:
                messagebox.showerror("Ошибка хода", f"Нужно выбрать {played_by_opponent_count} карты для отбития.")
                self._clear_selection()

    def _after_player_move(self):
        current_player = self.game.players[self.game.current_player_index]
        print(f"{current_player.name} ходит картами: {self.selected_cards}")
        # self.update_played_cards_dict(self.selected_cards)
        self.selected_cards = []
        self._clear_card_selection_ui()
        self.game.current_player_index = (self.game.current_player_index + 1) % len(self.game.players)
        self._update_gui()

    def _after_opponent_move(self):
        current_player_index = self.game.current_player_index
        opponent_index = (self.game.current_player_index + 1) % self.game.PLAYERS_COUNT

        current_player = self.game.players[current_player_index]
        opponent = self.game.players[opponent_index]

        current_player_played_cards = self.get_player_played_cards(current_player_index)
        opponent_played_cards = self.get_player_played_cards(opponent_index)

        current_player_cards_count = sum(len(move) for move in current_player_played_cards)
        opponent_cards_count = sum(len(move) for move in opponent_played_cards)

        turn_cards_count = len(current_player_played_cards[-1])

        if turn_cards_count > 0:
            if len(opponent.hand) >= turn_cards_count:
                # Игрок 2 ответил на ход игрока 1
                # Теперь ход снова переходит к игроку 1 для возможного перебития или сброса
                self.game.current_player_index = self.game.players.index(opponent)
                self._update_action_buttons()
            else:
                trick_cards = [card for _, card in self.game.played_cards] + [card for _, card in self.game.beat_cards]
                current_player.taken_cards.extend(trick_cards)
                print(f"\nИгрок 2 забирает взятку: {trick_cards}")
                self.game.current_player_index = self.game.players.index(current_player)
                self._take_cards_phase()
        else:
            # Какой-то непредвиденный случай
            print("Непредвиденное состояние в _after_opponent_move")

        self.selected_cards = []
        self._clear_card_selection_ui()
        self._update_gui()

    def _handle_invalid_move(self):
        messagebox.showerror("Ошибка хода", "Некорректный ход.")
        self._clear_selection()

    def _clear_selection(self):
        self.selected_cards = []
        self._clear_card_selection_ui()
        self._update_action_buttons()

    def _clear_card_selection_ui(self):
        for hand_labels in self.card_labels.values():
            for label in hand_labels.values():
                label.config(relief=tk.FLAT)

    def _force_take_trick(self):
        """Обрабатывает случай, когда игрок забирает взятку (кнопка или по правилам)."""
        if self.game.played_cards:
            taking_player = self.game.players[(self.game.current_player_index + 1) % len(self.game.players)]
            giving_player = self.game.players[self.game.current_player_index]
            taken_cards = list(itertools.chain.from_iterable(itertools.chain.from_iterable(self.game.played_cards.values())))
            taken_cards += self.selected_cards
            print(f"Отданные карты: {taken_cards}")
            taking_player.taken_cards.extend(taken_cards)
            print(f"{taking_player.name} забирает взятку: {taken_cards}")

            for card_to_remove in list(self.selected_cards):
                if card_to_remove in giving_player.hand:
                    giving_player.hand.remove(card_to_remove)

            self.game.played_cards = {}
            self.game.cards_to_take = 0
            self.game.current_player_index = self.game.players.index(taking_player)  # Следующим ходит забравший взятку
            self._update_gui()
            self._take_cards_phase()
            self._clear_selection()
            self._check_round_end()
        self.take_button.config(state=tk.DISABLED)

    def _finish_trick_gui(self):
        """Завершает взятку в GUI."""
        trick_winner = self._determine_trick_winner()
        if trick_winner:
            trick_cards = [card for _, card in self.game.played_cards]
            trick_winner.taken_cards.extend(trick_cards)
            print(f"\nВзятку забрал {trick_winner.name} с картами: {trick_cards}")
            self.game.last_trick_winner = trick_winner
            self.game.played_cards = {}
            self.game.current_player_index = self.game.players.index(trick_winner)
            self._update_gui()
            self._take_cards_phase()
            self._check_round_end()
        else:
            print("Ошибка при определении победителя взятки.")

    def _determine_trick_winner(self):
        """Определяет победителя текущей взятки."""
        if not self.game.played_cards:
            return None

        first_player, first_card = self.game.played_cards[0]
        winning_player = first_player
        winning_card = first_card

        for player, card in self.game.beat_cards:
            if card.suit == winning_card.suit:
                if list(Card.RANKS.keys()).index(card.rank) > list(Card.RANKS.keys()).index(winning_card.rank):
                    winning_card = card
                    winning_player = player
            elif card.suit == self.game.trump_suit and winning_card.suit != self.game.trump_suit:
                winning_card = card
                winning_player = player
            elif card.suit == self.game.trump_suit and winning_card.suit == self.game.trump_suit:
                if list(Card.RANKS.keys()).index(card.rank) > list(Card.RANKS.keys()).index(winning_card.rank):
                    winning_card = card
                    winning_player = player

        return winning_player

    def _take_cards_phase(self):
        """Фаза взятия карт после хода."""
        print("\n >>> Набор карт")
        num_players = len(self.game.players)
        while any(len(player.hand) < self.game.HAND_SIZE for player in self.game.players) and self.game.deck.cards:
            current_player_index = self.game.current_player_index
            current_player = self.game.players[current_player_index]
            print(f"{current_player.name} берет карту. У него сейчас {len(current_player.hand)} карт")
            if len(current_player.hand) < 6 and self.game.deck.cards:
                drawn_card = self.game.deck.deal(1)[0]
                current_player.add_cards([drawn_card])

                if self.game.deck.cards and self.cur_card_new_trump:
                    self.game.trump_suit = drawn_card.suit
                    self.game.trump_card = drawn_card
                    print(f" >>> Взята козырная карта! Новый козырь: {self.game.trump_suit} ({drawn_card})")
                    self.cur_card_new_trump = False

                if drawn_card == self.game.first_trump_card:
                    self.cur_card_new_trump = True

            self.game.current_player_index = (self.game.current_player_index + 1) % num_players
            self._update_gui()
        # self.game.current_player_index = self.game.current_player_index + 1 % num_players  # Возвращаем индекс к текущему игроку для следующего хода
        # print(f"Индекс: {self.game.current_player_index}")
        self._update_action_buttons()

    def update_game_state(self):
        """Обновляет отображение всех элементов интерфейса."""
        self._update_gui()

    def get_current_player_name(self):
        return self.game.players[self.game.current_player_index].name

    def get_player_played_cards(self, index):
        return self.game.played_cards.get(str(index), [])

    def get_player_last_played_cards(self, index):
        played_cards = self.get_player_played_cards(index)

        if played_cards:
            return played_cards[-1]
        else:
            return []

    def update_played_cards_dict(self, cards):
        index = self.game.current_player_index
        played_cards = self.get_player_played_cards(index)

        if played_cards:
            self.game.played_cards[str(index)].append(cards)
        else:
            self.game.played_cards[str(index)] = [cards]

        print(f"current_played_cards: {self.get_player_last_played_cards(index)}")

    def is_take_button_must_be_active(self):
        current_player_index = self.game.current_player_index
        opponent_index = (self.game.current_player_index + 1) % self.game.PLAYERS_COUNT

        current_player_played_cards = self.get_player_played_cards(current_player_index)
        opponent_played_cards = self.get_player_played_cards(opponent_index)
        
        current_player_cards_count = sum(len(move) for move in current_player_played_cards)
        opponent_cards_count = sum(len(move) for move in opponent_played_cards)
        selected_cards_count = len(self.selected_cards)

        # print(f"\ncurrent_player_played_cards: {current_player_played_cards} | opponent_played_cards: {opponent_played_cards}")
        # print(f"current_player_cards_count: {current_player_cards_count} | opponent_cards_count: {opponent_cards_count}")

        if self.game.played_cards and ((self.game.played_cards and current_player_cards_count == opponent_cards_count \
                                        and not self.selected_cards)
            or current_player_cards_count + selected_cards_count == opponent_cards_count):
            return True
        return False
        
    def is_play_button_must_be_active(self):
        opponent_player_index = (self.game.current_player_index + 1) % self.game.PLAYERS_COUNT

        last_opponent_played_cards = self.get_player_last_played_cards(opponent_player_index)
        turn_cards_count = len(last_opponent_played_cards)
        selected_cards_count = len(self.selected_cards)

        if not self.game.played_cards:  # Первый ход
            if self.selected_cards:
                first_suit = self.selected_cards[0].suit
                if all(card.suit == first_suit for card in self.selected_cards):
                    return True
        else:  # Ответ на ход
            # print(f"Отбивка. selected_cards: {self.selected_cards} | selected_cards_count: {selected_cards_count} | turn_cards_count: {turn_cards_count}")
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
            self.game.start_round()
            self.selected_cards = []
            self._update_gui()