import traceback
import os
import socket
import threading
import random
from src.game import Game
from src.player import Player
from src.deck import Deck
from src.card import Card
from dotenv import load_dotenv

load_dotenv()



# HOST = os.getenv('HOST')
# PORT = int(os.getenv('PORT'))
HAND_SIZE = Game.HAND_SIZE
PLAYERS_COUNT = Game.PLAYERS_COUNT

game = Game()
clients = []
client_addresses = {}
ui_loaded = 0

def broadcast(message, sender_conn=None):
    print(f"[ОТПРАВКА СООБЩЕНИЯ] {message}")
    message_bytes = message.encode('utf-8')
    for client in clients:
        if sender_conn is None or client != sender_conn:
            try:
                client.sendall(message_bytes)
            except Exception as e:
                print(f"[ОШИБКА ШИРОКОВЕЩАНИЯ] {e}")

def handle_client(conn, addr):
    global ui_loaded
    print(f"[НОВОЕ СОЕДИНЕНИЕ] {addr} подключился.")
    client_addresses[conn] = addr
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            message = data.decode('utf-8')
            print(f"[{addr}] Получено: {message}")
            if message.startswith("CONNECT"):
                name = message.split()[1]
                player = Player(name)
                player.client = conn
                game.add_player(player)
                print(f"[СЕРВЕР]: Создан игрок {name} ({player}) для {addr}")
                if len(game.players) == 2:
                    print("[СЕРВЕР]: Оба игрока подключены")
            elif message.startswith("UI_LOADED"):
                ui_loaded += 1
                if ui_loaded == 2:
                    print("[СЕРВЕР]: Интерфейсы обоих игроков загружены. Начало раунда")
                    start_game()
            else:
                process_client_message(conn, message)
    except Exception as e:
        print(f"[ОШИБКА КЛИЕНТА] Соединение с {addr} разорвано: {e}")
    finally:
        remove_client(conn)
        conn.close()
        print(f"[ОТКЛЮЧЕНИЕ] Соединение с {addr} закрыто.")

def remove_client(conn):
    if conn in clients:
        addr = client_addresses.get(conn)
        name = game.get_player_by_client(conn).name
        print(f"[ОТКЛЮЧЕНИЕ] Клиент {addr} ({name}) отключился.")
        clients.remove(conn)
        del client_addresses[conn]
        print(f"[АКТИВНЫЕ СОЕДИНЕНИЯ] {len(clients)}")

def process_client_message(conn, message):
    print(f"[СЕРВЕР]: Обработка сообщения от {client_addresses.get(conn)}: {message}")
    try:
        if message.startswith("PLAY"):
            parts = message.split()
            played_cards_str = parts[1:]
            played_cards = [Card.from_str(card_str) for card_str in played_cards_str]

            player = game.get_player_by_client(conn)

            if not player:
                print(f"[СЕРВЕР ОШИБКА]: Не найден игрок для соединения {conn}")
                return

            print(f"current_player_index: {game.current_player_index}")
            if game.players[game.current_player_index].client != conn:
                print(f"[СЕРВЕР]: Сейчас не ход игрока {player.name}")
                conn.sendall("NOT_YOUR_TURN\n".encode('utf-8'))
                return

            # Проверка наличия карт в руке игрока
            for card in played_cards:
                if card not in player.hand:
                    print(f"[СЕРВЕР ОШИБКА]: У игрока {player.name} нет карты {card} в руке.")
                    conn.sendall("INVALID_CARD\n".encode('utf-8'))
                    return

            for card in played_cards:
                player.hand.remove(card)

            index = game.get_player_index(player.name)
            game.update_played_cards_dict(played_cards, index)

            opponent_socket = None
            for client in clients:
                if client != conn:
                    opponent_socket = client
                    break
            if opponent_socket:
                broadcast(f"OPPONENT_PLAYED {' '.join(played_cards_str)}\n", conn)

            game.pass_the_turn()
            # game_state['current_player_socket'] = opponent_socket

        elif message.startswith("TRICK"):
            winner_conn = get_other_client(conn)
            winner = game.get_player_by_client(winner_conn)
            looser = game.get_player_by_client(conn)
            print(f"\n >>> Получил взятку {winner.name}. Отдал взятку {looser.name}")
            print(f"[СЕРВЕР]: Получена команда TRICK от {client_addresses.get(conn)} ({looser.name}).")

            parts = message.split()
            last_selected_cards_str = parts[1:]
            last_selected_cards = [Card.from_str(card) for card in last_selected_cards_str]

            broadcast(f"TRICK {winner.name} {' '.join(last_selected_cards_str)}\n")
            print(f"[СЕРВЕР]: Игрок {winner.name} забирает взятку.")
            taken_cards_this_trick = []
            taken_moves = game.played_cards
            taken_cards_this_trick.extend(last_selected_cards)
            for moves in taken_moves.values():
                for move in moves:
                    taken_cards_this_trick.extend(move)
            game.played_cards = {}
            if winner:
                winner.taken_cards.extend(taken_cards_this_trick)
            if looser:
                for card in last_selected_cards:
                    looser.hand.remove(card)

            game.pass_the_turn()
            if is_the_round_over():
                game.calculate_and_update_table_scores()
                print(f"[СЕРВЕР] Раунд завершен. У {game.players[0].name} {game.players[0].points} очков. У {game.players[1].name} {game.players[1].points} очков")
                if is_the_game_over():
                    winner = game.players[0] if game.players[0].table_scores < 12 else game.players[1]
                    print(f"[СЕРВЕР] Игра завершена. Победил {winner.name}!")
                    broadcast(f"GAME_OVER\n")
                else:
                    game.pass_the_turn()
                    print(f"\n >>> Последний взял взятку: {winner.name}. Следующим ходит: {game.players[game.current_player_index].name} | conn: {game.get_player_by_client(conn).name}")
                    broadcast(f"ROUND_OVER\n")
                    start_round(conn)
            else:
                _take_cards_phase(winner_conn)
    except Exception as e:
        traceback.print_exc()
        raise e

def start_game():
    for client in clients:
        client.sendall(f"OPPONENT_NAME {game.get_player_by_client(get_other_client(client)).name}\n".encode('utf-8'))
    start_round()

def start_round(first_player_socket = None):
    game.cur_card_new_trump = False
    game.trump_card = game.deck.deal(1)[0]
    game.trump_suit = game.trump_card.suit
    game.first_trump_card = game.trump_card
    insert_index = len(game.deck.cards) // 2 + random.randint(-3, 3)
    game.deck.cards.insert(insert_index, game.trump_card)
    print(f"[СЕРВЕР]: Козырь: {game.trump_suit} ({game.trump_card})")

    broadcast(f"TRUMP_SUIT {game.trump_suit}\n", None)
    broadcast(f"TRUMP_CARD {str(game.trump_card)}\n", None)

    if not first_player_socket:
        first_player_socket = random.choice(clients)
    first_player_name = game.get_player_by_client(first_player_socket).name
    print(f"[СЕРВЕР]: Первый ходит игрок {first_player_name}")
    broadcast(f"FIRST_PLAYER {first_player_name}\n", None)
    game.current_player_index = game.get_player_index(first_player_name)
    _take_cards_phase(first_player_socket)

def _take_cards_phase(winner_conn):
    print('[СЕРВЕР] Раздача карт')
    looser_conn = get_other_client(winner_conn)
    current_players_seq = [game.get_player_by_client(winner_conn), game.get_player_by_client(looser_conn)]

    while any(len(player.hand) < HAND_SIZE for player in game.players) and game.deck.cards:
        for player in current_players_seq:
            if len(player.hand) < 6 and game.deck.cards:
                drawn_card = game.deck.deal(1)[0]
                player.add_cards([drawn_card])
                broadcast(f"TAKE_CARD {player.name} {str(drawn_card)}\n")
                if game.deck.cards and game.cur_card_new_trump:
                    game.trump_card = drawn_card
                    game.trump_suit = game.trump_card.suit
                    print(f"[СЕРВЕР]: Козырь: {game.trump_suit} ({game.trump_card})")
                    broadcast(f"TRUMP_SUIT {game.trump_suit}\n", None)
                    broadcast(f"TRUMP_CARD {str(game.trump_card)}\n", None)
                    game.cur_card_new_trump = False

                if drawn_card == game.first_trump_card:
                    game.cur_card_new_trump = True

def is_the_round_over():
    if len(game.players[0].hand) == 0 and len(game.players[1].hand) == 0 and len(game.deck.cards) == 0:
        return True
    return False

def is_the_game_over():
    if game.players[0].table_scores >= 12 or game.players[0].table_scores >= 12:
        return True
    return False

def start_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.bind((host, port))
        server_socket.listen(2)
        print(f"[СЕРВЕР ЗАПУЩЕН] Слушает на {host}:{port}")
        while len(clients) < 2:
            conn, addr = server_socket.accept()
            clients.append(conn)
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()
            print(f"[АКТИВНЫЕ СОЕДИНЕНИЯ] {len(clients)}")
        print("[ВСЕ ИГРОКИ ПОДКЛЮЧЕНЫ]")
    except Exception as e:
        print(f"[ОШИБКА СЕРВЕРА] {e}")
    finally:
        server_socket.close()

def get_other_client(client):
    if client not in clients:
        raise ValueError(f"{client} не найден в массиве")
    return clients[0] if clients[1] == client else clients[1]