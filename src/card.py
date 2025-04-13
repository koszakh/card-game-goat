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
    SUIT_STRS = {"♥": "Hearts", "♦": "Diamonds", "♣": "Clubs", "♠": "Spades"}

    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def __str__(self):
        return f"{self.rank}{self.suit}"

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if isinstance(other, Card):
            return self.rank == other.rank and self.suit == other.suit
        return False

    def __hash__(self):
        return hash((self.rank, self.suit))

    def value(self):
        return self.RANKS[self.rank]

    @classmethod
    def get_cards_value(cls, cards):
        value = 0
        for card in cards:
            value += card.value()

        return value

    @classmethod
    def from_str(cls, card_str):
        if len(card_str) < 2 or len(card_str) > 3:
            raise ValueError(f"Неверный формат карты: {card_str}")
        if len(card_str) == 2:
            rank_str = card_str[0]
        elif len(card_str) == 3:
            rank_str = card_str[:-1]
        suit = card_str[-1]

        if rank_str not in cls.RANKS:
            raise ValueError(f"Неверный ранг карты: {rank_str}")
        if suit not in cls.SUITS:
            raise ValueError(f"Неверная масть карты: {suit}")

        return cls(rank_str, suit)

    @classmethod
    def get_suit_mark(cls, suit_str):
        return next((k for k, v in cls.SUIT_STRS.items() if v == suit_str), None)