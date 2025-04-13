import os
from src.card import Card
import itertools

def func(a):
    return (1, 'a') if a > 5 else (2, 'b')

if __name__ == "__main__":
    # club_Q = Card('Q', '♣')
    # club_10 = Card('10', '♣')
    # club_A = Card('A', '♣')
    # card1 = club_Q
    # card2 = club_10
    # print(list(Card.RANKS.keys()))
    # if list(Card.RANKS.keys()).index(card1.rank) > list(Card.RANKS.keys()).index(card2.rank):
    #     print(f"{card1} > {card2}")
    # else:
    #     print(f"{card1} <= {card2}")

    cards = [Card('Q', '♣'), Card('6', '♣'), Card('10', '♥'), Card('J', '♥'), Card('7', '♠'), Card('A', '♠')]
    print(Card.get_cards_value(cards))
    # card = Card('6', '♠')
    # print(card in cards)
    script_path = os.path.abspath(__file__)
    script_directory = os.path.dirname(script_path)
    print(script_directory + '\\sounds')