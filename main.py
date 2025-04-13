import tkinter as tk
from src.game import Game
from src.player import Player
from src.gui import GameGUI

if __name__ == "__main__":
    player1 = Player("Игрок 1")
    player2 = Player("Игрок 2")
    players = [player1, player2]
    game = Game(players)
    game.current_dealer_index = 0
    game.current_player_index = (game.current_dealer_index + 1) % len(players)

    root = tk.Tk()
    gui = GameGUI(root, game)

    def start_game():
        game.start_round()
        gui.update_game_state()
        print(f"Козырь при раздаче: {game.trump_suit} ({game.trump_card})")


    start_game()
    root.mainloop()

    # print("\n--- Игра окончена! ---")
    # if player1.scores >= 12:
    #     print(f"Победил {player2.name}!")
    # else:
    #     print(f"Победил {player1.name}!")
