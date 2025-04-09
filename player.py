class Player:
    def __init__(self, name):
        self.name = name
        self.hand = []
        self.taken_cards = []
        self.table_scores = 0
        self.points = 0

    def add_cards(self, cards):
        self.hand.extend(cards)

    def play_cards(self, cards):
        if set(cards).issubset(self.hand):
            self.hand = [card for card in self.hand if card not in cards]
            return cards
        else:
            return []

    def calc_points(self):
        self.points = sum(card.value() for card in self.taken_cards)
        return self.points