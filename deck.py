from card import Card
import random

class Deck:
    def __init__(self):
        self.cards = [Card(rank, suit) for suit in Card.SUITS for rank in Card.RANKS.keys()]
        random.shuffle(self.cards)

    def deal(self, num_cards = 6):
        dealt_cards = []
        for _ in range(num_cards):
            if self.cards:
                dealt_cards.append(self.cards.pop())
        return dealt_cards