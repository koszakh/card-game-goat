from src.deck import Deck
from src.card import Card
from src.player import Player
import random
from itertools import permutations

class Game:
    HAND_SIZE = 6
    PLAYERS_COUNT = 2
    def __init__(self, players = []):
        self.players = players
        self.deck = Deck()
        self.trump_card = None
        self.trump_suit = None
        self.current_player_index = None
        self.ordered_played_cards = []
        self.dealer_index = None
        self.played_cards = {}
        self.round_over = False
        self.last_trick_winner = None
        self.cards_to_take = 0

    def add_player(self, player):
        self.players.append(player)

    def start_round(self):
        """Начинает новый раунд игры."""
        self.deck = Deck()
        for player in self.players:
            player.hand = []
            player.taken_cards = []
        self.trump_card = None
        self.trump_suit = None
        self.dealer_index = random.randint(0, self.PLAYERS_COUNT - 1)
        self.current_player_index = (self.dealer_index + 1) % self.PLAYERS_COUNT if self.dealer_index is not None else 0
        self.played_cards = {}
        self.round_over = False
        self.last_trick_winner = None
        self.cards_to_take = 0
        self._deal_cards()
        self._determine_trump()

    def _deal_cards(self):
        """Раздает карты игрокам."""
        dealer = self.players[self.dealer_index]
        other_player_index = (self.dealer_index + 1) % 2
        other_player = self.players[other_player_index]

        for _ in range(self.HAND_SIZE):
            other_player.add_cards([self.deck.deal(1)[0]])
            dealer.add_cards([self.deck.deal(1)[0]])

    def _determine_trump(self):
        """Определяет козырную масть."""
        if self.deck.cards:
            self.trump_card = self.deck.deal(1)[0]
            self.first_trump_card = self.trump_card
            self.trump_suit = self.trump_card.suit
            print(f"Козырная масть: {self.trump_suit} ({self.trump_card})")
            insert_index = len(self.deck.cards) // 2 + random.randint(-3, 3)
            self.deck.cards.insert(insert_index, self.trump_card)
        else:
            self.trump_suit = random.choice(Card.SUITS)
            print(f"Козырная масть определена случайно: {self.trump_suit}")

    def play_round(self):
        """Игровой цикл одного раунда."""
        while not self.round_over:
            current_player = self.players[self.current_player_index]
            opponent_index = (self.current_player_index + 1) % 2
            opponent = self.players[opponent_index]

            print(f"\nХод игрока: {current_player.name}")
            print(f"Ваши карты: ")
            sorted_hand = sorted(current_player.hand, key=lambda card: (Card.SUITS.index(card.suit), list(Card.RANKS.keys()).index(card.rank)))
            for i, card in enumerate(sorted_hand):
                print(f"{i + 1}. {card}")

            if not self.played_cards:  # Первый ход в взятке
                while True:
                    try:
                        card_indices_str = input("Выберите номера карт для хода (через пробел): ").split()
                        card_indices = [int(i) - 1 for i in card_indices_str]
                        if not card_indices:
                            print("Пожалуйста, выберите хотя бы одну карту.")
                            continue
                        selected_cards = [sorted_hand[i] for i in card_indices]
                        first_card_suit = selected_cards[0].suit
                        if not all(card.suit == first_card_suit for card in selected_cards):
                            print("Выбранные карты должны быть одной масти для первого хода.")
                            continue
                        if self.make_move(current_player, selected_cards):
                            break
                    except (ValueError, IndexError):
                        print("Некорректный ввод. Пожалуйста, введите номера карт из списка.")
            else:
                # TODO: Реализовать ответ на ход противника (через GUI)
                print(f"Противник походил: {[(p.name, c) for p, c in self.played_cards]}")
                opponent_hand_sorted = sorted(opponent.hand, key=lambda card: (Card.SUITS.index(card.suit), list(Card.RANKS.keys()).index(card.rank)))
                print(f"Карты противника (примерно): {len(opponent.hand)} карт")

                num_played = len(self.played_cards)
                can_beat_count = self._can_beat_multiple(opponent.hand, [card for _, card in self.played_cards])

                if can_beat_count >= num_played:
                    print(f"{opponent.name} должен отбиться {num_played} картами.")
                    # TODO: Реализовать логику выбора карт для отбития нескольких карт у второго игрока (через GUI)
                    # Пока временная автоматическая реализация
                    beating_combinations = self._find_beating_combinations(opponent.hand, [card for _, card in self.played_cards])
                    if beating_combinations:
                        beating_cards = random.choice(beating_combinations)
                        self.beat_cards = {opponent: card for card in beating_cards}
                        for card in beating_cards:
                            opponent.hand.remove(card)
                        print(f"{opponent.name} отбивается картами: {[card for card in self.beat_cards.values()]}")
                        self.current_player_index = self.players.index(current_player) # Ход снова к первому игроку (для возможного перебивания)
                    else:
                        print(f"{opponent.name} нечем отбиться от {num_played} карт.")
                        self.cards_to_take = num_played
                        self.current_player_index = opponent_index
                else:
                    print(f"{opponent.name} не может отбиться от {num_played} карт.")
                    self.cards_to_take = num_played
                    self.current_player_index = opponent_index

            if self.cards_to_take > 0:
                print(f"{opponent.name} берет {self.cards_to_take} карт.")
                taken_cards = self.deck.deal(self.cards_to_take)
                opponent.add_cards(taken_cards)
                opponent.taken_cards.extend([card for _, card in self.played_cards])
                self.played_cards = []
                self.beat_cards = {}
                self.cards_to_take = 0
            elif self.played_cards and self.beat_cards and len(self.played_cards) == len(self.beat_cards):
                trick_winner = self._determine_trick_winner()
                print(f"Взятку забрал {trick_winner.name} с картами: {[card for _, card in self.played_cards] + list(self.beat_cards.values())}")
                trick_winner.taken_cards.extend([card for _, card in self.played_cards] + list(self.beat_cards.values()))
                self.last_trick_winner = trick_winner
                self.played_cards = []
                self.beat_cards = {}
                self.current_player_index = self.players.index(trick_winner)

            if not self.players[0].hand and not self.players[1].hand and not self.deck.cards:
                self.round_over = True
            elif not self.deck.cards and not (self.players[0].hand or self.players[1].hand):
                self.round_over = True

            if not self.round_over:
                self._take_cards()

    def make_move(self, player, cards):
        """Игрок делает ход, выкладывая карты."""
        if not cards:
            return False
        suit = cards[0].suit
        for card in cards:
            if card.suit != suit and not self.played_cards:
                print("Нельзя ходить разными мастями (кроме первого хода).")
                return False
            if card not in player.hand:
                print(f"Карты {card} нет у игрока {player.name}.")
                return False
            player.hand.remove(card)

        player_index = self.players.index(player)
        player_index_str = str(player_index)
        if player_index_str not in self.played_cards.keys():
            self.played_cards[player_index_str] = []
        self.played_cards[player_index_str].append(cards)
        return True

    def _can_beat(self, hand, played_cards):
        """Проверяет, может ли игрок отбить выложенные карты."""
        if not played_cards:
            return True # Первый ход всегда принимается

        first_played_suit = played_cards[0][1].suit
        num_played = len(played_cards)
        beating_options = [[] for _ in range(num_played)]

        for card in hand:
            for i in range(num_played):
                played_card = played_cards[i][1]
                if card.suit == played_card.suit and list(Card.RANKS.keys()).index(card.rank) > list(Card.RANKS.keys()).index(played_card.rank):
                    beating_options[i].append(card)
                elif card.suit == self.trump_suit and played_card.suit != self.trump_suit:
                    beating_options[i].append(card)
                elif card.suit == self.trump_suit and played_card.suit == self.trump_suit and list(Card.RANKS.keys()).index(card.rank) > list(Card.RANKS.keys()).index(played_card.rank):
                    beating_options[i].append(card)

        # Проверяем, есть ли хотя бы один вариант отбития для каждой выложенной карты
        return all(options for options in beating_options)

    def _find_beating_cards(self, hand, played_cards):
        """Находит возможные варианты отбития выложенных карт."""
        if not played_cards:
            return [hand] * len(played_cards) # Первый ход, можно ходить чем угодно

        first_played_suit = played_cards[0][1].suit
        num_played = len(played_cards)
        beating_options = [[] for _ in range(num_played)]

        for card in hand:
            for i in range(num_played):
                played_card = played_cards[i][1]
                if card.suit == played_card.suit and list(Card.RANKS.keys()).index(card.rank) > list(Card.RANKS.keys()).index(played_card.rank):
                    beating_options[i].append(card)
                elif card.suit == self.trump_suit and played_card.suit != self.trump_suit:
                    beating_options[i].append(card)
                elif card.suit == self.trump_suit and played_card.suit == self.trump_suit and list(Card.RANKS.keys()).index(card.rank) > list(Card.RANKS.keys()).index(played_card.rank):
                    beating_options[i].append(card)

        # Возвращаем возможные карты для отбития каждой выложенной карты
        return beating_options

    def _can_overbeat(self, hand, played_cards, beat_cards):
        """Проверяет, может ли первый игрок перебить карты, которыми отбились."""
        if not played_cards or not beat_cards:
            return False

        overbeating_options = []
        first_played_player, first_played_card = played_cards[0]
        first_played_suit = first_played_card.suit

        for i, beat_card in enumerate(beat_cards):
            possible_overbeats = []
            original_played_card = played_cards[i][1]

            for card in hand:
                # Перебиваем по масти
                if card.suit == original_played_card.suit and list(Card.RANKS.keys()).index(card.rank) > list(Card.RANKS.keys()).index(beat_card.rank):
                    possible_overbeats.append(card)
                # Перебиваем козырем
                elif card.suit == self.trump_suit and beat_card.suit != self.trump_suit:
                    possible_overbeats.append(card)
                elif card.suit == self.trump_suit and beat_card.suit == self.trump_suit and list(Card.RANKS.keys()).index(card.rank) > list(Card.RANKS.keys()).index(beat_card.rank):
                    possible_overbeats.append(card)
            overbeating_options.append(possible_overbeats)

        # Должен быть хотя бы один вариант перебития для каждой отбитой карты
        return all(options for options in overbeating_options)

    def _finish_trick(self, trick_winner):
        """Завершает взятку, определяет победителя и дает право хода."""
        trick_cards = []
        for moves in self.played_cards.values():
            for move in moves:
                trick_cards.extend(move)
        trick_winner.taken_cards.extend(trick_cards)
        print(f"\nВзятку забрал {trick_winner.name} с картами: {trick_cards}")
        self.last_trick_winner = trick_winner
        self.played_cards = {}
        self.current_player_index = self.players.index(trick_winner)

    def _take_cards(self):
        """Игроки берут карты из колоды по одной по очереди до 6 штук."""
        num_players = len(self.players)
        while any(len(player.hand) < 6 for player in self.players) and self.deck.cards:
            current_player = self.players[self.current_player_index]
            if len(current_player.hand) < 6 and self.deck.cards:
                drawn_card = self.deck.deal(1)[0]
                current_player.add_cards([drawn_card])
                print(f"{current_player.name} берет карту.")
                if drawn_card == self.trump_card:
                    new_trump = self.deck.deal(1)[0]
                    self.trump_suit = new_trump.suit
                    print(f"Взята козырная карта! Новый козырь: {self.trump_suit} ({new_trump})")
                    current_player.hand.append(new_trump) # Игрок берет и новую козырную карту
                    self.trump_card = new_trump # Обновляем козырную карту
                    # break # После взятия козырной карты текущим игроком, цикл взятия прерывается
            self.current_player_index = (self.current_player_index + 1) % num_players
            print("player_index: ", self.current_player_index)


    def calculate_and_update_table_scores(self):
        """Подсчитывает очки за раунд и обновляет табличные очки игроков."""
        player1 = self.players[0]
        player2 = self.players[1]

        player1_points = player1.calc_points()
        player2_points = player2.calc_points()

        print("\n--- Очки за раунд ---")
        print(f"{player1.name}: {player1.points} очков")
        print(f"{player2.name}: {player2.points} очков")

        for player in self.players:
            if player.points == 0:
                player.table_scores += 6
            elif player.points < 42:
                player.table_scores += 4
            elif player.points < 60:
                player.table_scores += 2

        player1.taken_cards = []
        player2.taken_cards = []
        self.deck = Deck()

    def _can_beat_multiple(self, hand, played_cards):
        """Проверяет, сколько карт из выложенных может побить игрок."""
        if not played_cards:
            return len(hand)

        first_played_suit = played_cards[0].suit
        beating_count = 0

        for played_card in played_cards:
            can_beat_this = False
            for card in hand:
                if card.suit == played_card.suit and list(Card.RANKS.keys()).index(card.rank) > list(Card.RANKS.keys()).index(played_card.rank):
                    can_beat_this = True
                    break
                elif card.suit == self.trump_suit and played_card.suit != self.trump_suit:
                    can_beat_this = True
                    break
                elif card.suit == self.trump_suit and played_card.suit == self.trump_suit and list(Card.RANKS.keys()).index(
                        card.rank) > list(Card.RANKS.keys()).index(played_card.rank):
                    can_beat_this = True
                    break
            if can_beat_this:
                beating_count += 1
        return beating_count

    def _find_beating_combinations(self, hand, played_cards):
        """Находит возможные комбинации карт для отбития выложенных карт."""
        possible_beats = []

        def find_combinations(current_hand, current_beat, played):
            if not played:
                possible_beats.append(list(current_beat))
                return

            played_card = played[0]
            remaining_played = played[1:]

            for i, card in enumerate(current_hand):
                can_beat_this = False
                if card.suit == played_card.suit and list(Card.RANKS.keys()).index(card.rank) > list(Card.RANKS.keys()).index(played_card.rank):
                    can_beat_this = True
                elif card.suit == self.trump_suit and played_card.suit != self.trump_suit:
                    can_beat_this = True
                elif card.suit == self.trump_suit and played_card.suit == self.trump_suit and list(Card.RANKS.keys()).index(
                        card.rank) > list(Card.RANKS.keys()).index(played_card.rank):
                    can_beat_this = True

                if can_beat_this:
                    new_hand = current_hand[:i] + current_hand[i + 1:]
                    new_beat = list(current_beat) + [card]
                    find_combinations(new_hand, new_beat, remaining_played)

        find_combinations(sorted(hand, key=lambda c: list(Card.RANKS.keys()).index(c.rank)), [], played_cards)
        return possible_beats

    def _can_beat_all_selected(self, selected_cards, played_cards):
        if len(selected_cards) != len(played_cards) or not played_cards:
            return False

        for perm in permutations(selected_cards):
            can_beat_all = True
            for i in range(len(played_cards)):
                if not self._can_beat_single(perm[i], played_cards[i]):
                    can_beat_all = False
                    break
            if can_beat_all:
                return True
        return False

    def _can_beat_single(self, beating_card, played_card):
        """Проверяет, может ли одна карта побить другую."""
        if beating_card.suit == played_card.suit and list(Card.RANKS.keys()).index(beating_card.rank) > list(
                Card.RANKS.keys()).index(played_card.rank):
            return True
        elif beating_card.suit == self.trump_suit and played_card.suit != self.trump_suit:
            return True
        elif beating_card.suit == self.trump_suit and played_card.suit == self.trump_suit and list(
                Card.RANKS.keys()).index(beating_card.rank) > list(Card.RANKS.keys()).index(played_card.rank):
            return True
        return False

    def _determine_trick_winner(self):
        """Определяет победителя текущей взятки."""
        if not self.played_cards:
            return None

        first_player_index = list(self.played_cards.keys())[0]
        first_player = self.players[int(first_player_index)]
        first_card = self.played_cards[first_player_index][0][0]  # Первая карта первого хода
        winning_player = first_player
        winning_card = first_card

        for player_index_str, moves in self.played_cards.items():
            player_index = int(player_index_str)
            player = self.players[player_index]
            for move in moves:
                played_card = move[0]  # Берем первую карту из хода (масть хода задается первой картой)
                if player != first_player:  # Сравниваем с картами не первого ходившего игрока
                    if played_card.suit == winning_card.suit:
                        if list(Card.RANKS.keys()).index(played_card.rank) > list(Card.RANKS.keys()).index(
                                winning_card.rank):
                            winning_card = played_card
                            winning_player = player
                    elif played_card.suit == self.trump_suit and winning_card.suit != self.trump_suit:
                        winning_card = played_card
                        winning_player = player
                    elif played_card.suit == self.trump_suit and winning_card.suit == self.trump_suit:
                        if list(Card.RANKS.keys()).index(played_card.rank) > list(Card.RANKS.keys()).index(
                                winning_card.rank):
                            winning_card = played_card
                            winning_player = player

        return winning_player

    def get_player_played_cards(self, index):
        return self.played_cards.get(str(index), [])

    def get_player_last_played_cards(self, index):
        played_cards = self.get_player_played_cards(index)

        if played_cards:
            return played_cards[-1]
        else:
            return []

    def update_played_cards_dict(self, cards, index):
        played_cards = self.get_player_played_cards(index)

        if played_cards:
            self.played_cards[str(index)].append(cards)
        else:
            self.played_cards[str(index)] = [cards]

    def get_player_by_client(self, client):
        return self.players[0] if self.players[0].client == client else self.players[1]

    def pass_the_turn(self):
        self.current_player_index = (self.current_player_index + 1) % self.PLAYERS_COUNT

    def get_player_index(self, name):
        return 0 if self.players[0].name == name else 1