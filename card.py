class Card:
    RANKS = {
        '6': 0,
        '7': 0,
        '8': 0,
        '9': 0,
        'J': 2,
        'Q': 3,
        'K': 4,
        '10': 10,
        'A': 11
    }
    SUITS = ['♣', '♦', '♥', '♠']

    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def __str__(self):
        return f"{self.rank}{self.suit}"

    def __repr__(self):
        return str(self)

    def value(self):
        return self.RANKS[self.rank]