#!/usr/bin/python3
# -*- coding: utf-8 -*

"""
Simple freecell game
"""

import sys
import random

RED = ["H", "D"]
BLACK = ["S", "C"]
SUITS = RED + BLACK
FREECELL = 4
COLUMN = 8
CARD_VALUE = ["a", 2, 3, 4, 5, 6, 7, 8, 9, 10, "j", "q", "k"]
COL_BASE = "B"
COL_FC = "FC"

class TermColor:
    GREEN = '\033[92m'
    RED = '\033[91m'
    ENDC = '\033[0m'

class Card(object):
    def __init__(self, suit, num):
        self.num = num
        self.suit = suit
        self.color = "RED" if suit in RED else "BLACK"

        self.uid = SUITS.index(suit) * len(CARD_VALUE) + num

    def __str__(self):
        return self.display()

    def display(self, colorize=True):
        s = "%s%s" % (str(CARD_VALUE[self.num-1]), self.suit)
        if colorize and self.color == "RED":
            s = TermColor.RED + s + TermColor.ENDC
        return s
    
    def __eq__(self, other):
        if isinstance(other, Card):
            return self.uid == other.uid
        else:
            return False

    def __hash__(self):
        return self.uid

    @classmethod
    def read_card(cls, scard):
        suit = None
        for s in SUITS:
            if scard.endswith(s):
                suit = s
                break
        if suit is None:
            raise ValueError("No suit found in: %s" % scard)
        
        sval = scard.replace(suit, '')
        reverse_card_value = {"a": 1, "j": 11, "q": 12, "k": 13}
        value = reverse_card_value.get(sval, sval)
        value = int(value)
        if value < 1 or value > 13:
            raise ValueError("Value in %s is not correct" % scard)
        
        return cls(suit, value)

class Choice(object):
    def __init__(self, cards, col_orig, col_dest):
        self.cards = cards
        self.col_orig = col_orig
        self.col_dest = col_dest

    def __str__(self):
        list_card = [str(c) for c in self.cards]
        col_dest_s = str(self.col_dest)
        if self.col_dest == COL_BASE:
            col_dest_s = TermColor.GREEN + col_dest_s + TermColor.ENDC
        return ",".join(list_card) + " from %s to %s" % (str(self.col_orig), col_dest_s)

class FreecellState(object):
    """
        A current state of a game of Freecell
    """
    def __init__(self, freecells, bases, columns, computed_column_series=None):
        self.freecells = freecells
        self.bases = bases
        self.columns = columns
    
        # Compute state data
        self.is_won = min([len(b) for _, b in self.bases.items()]) == len(CARD_VALUE)
        freecol = sum([len(col) == 0 for col in self.columns])
        self.max_mvt = (1 + FREECELL - len(self.freecells)) * (1 + freecol)
        self.max_mvt_freecol_dst =  (1 + FREECELL - len(self.freecells)) * freecol

        # Compute current series
        self.column_series = computed_column_series
        if self.column_series is None:
            self.column_series = [self._get_column_serie(i) for i in range(0, COLUMN)]
  
    def _clone(self):
        f = list(self.freecells)
        b = dict((k, list(self.bases.get(k))) for k in SUITS)
        c = [list(self.columns[i]) for i in range(0, COLUMN)]
        sc = [list(self.column_series[i]) for i in range(0, COLUMN)]
        return (f, b, c, sc)

    def _available_dest(self, head_card, cur_col, serie_size):
        dest = []

        if serie_size <= self.max_mvt:
            # To other columns
            for i in range(0, COLUMN):
                if i != cur_col:
                    col = self.columns[i]
                    if len(col) > 0:
                        last_c = col[-1]
                        if last_c.color != head_card.color and last_c.num - head_card.num == 1:
                            dest.append(i)
                    elif serie_size <= self.max_mvt_freecol_dst:
                        dest.append(i)

        if serie_size == 1:
            # To base
            b = self.bases.get(head_card.suit)
            if head_card.num - len(b) == 1:
                dest.append(COL_BASE)

            # To freecell
            if cur_col is not None and len(self.freecells) < FREECELL:
                dest.append(COL_FC)

        return dest
    
    def _get_column_serie(self, col_id):
        col = self.columns[col_id]
        serie = []
        last_card = None
        for card in reversed(col):
            # End serie if last card doesn't match
            if last_card is not None:
                if last_card.color == card.color or card.num - last_card.num != 1:
                    break
            serie.append(card)
            last_card = card
        serie.reverse()
        return serie
    
    def update_column_serie(self, col_id):
        if col_id != COL_FC and col_id != COL_BASE:
            self.column_series[col_id] = self._get_column_serie(col_id)

    def list_choices(self):
        """ Compute all choices for this state, 
            column_series MUST be up to date
        """
        choices = []

        # Freecell
        for card in self.freecells:
            for dst in self._available_dest(card, None, 1):
                choices.append(Choice([card], COL_FC, dst))

        # Columns
        for i in range(0, COLUMN):
            col_serie = self.column_series[i]
            for j in range(0, len(col_serie)):
                sub_serie = col_serie[j:]
                for dst in self._available_dest(sub_serie[0], i, len(sub_serie)):
                    choices.append(Choice(sub_serie, i, dst))

        return choices
    
    def apply(self, choice):
        f, b, c, sc = self._clone()

        # From origin
        if choice.col_orig == COL_FC:
            f.remove(choice.cards[0])
        else:
            for _ in choice.cards:
                c[choice.col_orig].pop()
        
        # To dest
        if choice.col_dest == COL_BASE:
            card = choice.cards[0]
            b.get(card.suit).append(card)
        elif choice.col_dest == COL_FC:
            f.append(choice.cards[0])
        else:
            c[choice.col_dest].extend(choice.cards)

        # Create new state
        ret = FreecellState(f, b, c, sc)
        ret.update_column_serie(choice.col_orig)
        ret.update_column_serie(choice.col_dest)
        return ret
                
    def __str__(self):
        return self.display()

    def display(self, colorize=True):
        game_line = []

        # Print freecell and bases
        headline = []
        for a in range(0, FREECELL):
            c = ""
            if a < len(self.freecells):
                c = self.freecells[a].display(colorize)
            headline.append(c)
        for bk, b in self.bases.items():
            c = b[-1].display(colorize) if len(b) > 0 else "0%s" % bk
            headline.append(c)
        game_line.append("\t".join(headline))
        game_line.append("")

        # Print columns
        maxl = max([len(col) for col in self.columns])
        for l in range(0, maxl):
            line = []
            for col in self.columns:
                if l < len(col):
                    line.append(col[l].display(colorize))
                else:
                    line.append("")
            game_line.append("\t".join(line))
        
        return "\n".join(game_line)
    
    @classmethod
    def init_from_deck(cls, deck):
        columns = [[] for i in range(0, COLUMN)]
        i = 0
        for c in deck:
            columns[i].append(c)
            i = i+1 if i < COLUMN-1 else 0
        
        return cls([], dict((k, []) for k in SUITS), columns)

class FreecellGame(object):
    def __init__(self, name, state):
        self.name = name
        self.state = state
        self.past_states = []
    
    def __str__(self):
        return self.state.display()

    def apply(self, choice):
        self.past_states.append(self.state)
        self.state = self.state.apply(choice)
    
    def reverse_apply(self, choice):
        if len(self.past_states) > 0:
            self.state = self.past_states.pop()
            self.state.update_column_serie(choice.col_dest)
            self.state.update_column_serie(choice.col_orig)

    def save_game(self):
        filename = self.name
        with open(filename, 'w') as f:
            f.write(self.state.display(False))
            f.write('\n')
        print("Game saved in", filename)
        print("WARNING: can't reset previous move at reload")

    @classmethod
    def from_file(cls, filename):
        print("Load game file:", filename)
        freecells = list()
        bases = dict((k, []) for k in SUITS)
        columns = [list() for _ in range(COLUMN)]
        with open(filename, 'r') as f:
            # First line must be Freecell and bases
            line = f.readline()
            # Freecell
            fcstr = line.split()[:-4]
            for sc in fcstr:
                freecells.append(Card.read_card(sc))
            
            # Bases
            bstr = line.split()[-4:]
            for bs in bstr:
                if not bs.startswith('0'):
                    lbc = Card.read_card(bs)
                    for n in range(1, lbc.num+1):
                        bases[lbc.suit].append(Card(lbc.suit, n))

            # Second line must be empty
            line = f.readline()
            assert len(line.strip()) == 0
            print("freecell & bases, ok")

            # Start of column
            line = f.readline()
            while line:
                line = line.replace('\n', '')
                cid = 0
                for sc in line.split("\t"):
                    if len(sc) > 0:
                        columns[cid].append(Card.read_card(sc))
                    cid += 1
                line = f.readline()

        # Check we have 52 cards total
        count = len(freecells)
        for _, b in bases.items():
            count += len(b)
        for col in columns:
            count += len(col)
        assert count == 52
        print("52 cards, ok")

        # Check all cards are somewhere
        standard_deck = [Card(j, i) for i in range(1, len(CARD_VALUE)+1) for j in SUITS]
        for c in standard_deck:
            found = c in bases.get(c.suit) or c in freecells
            cid = 0
            while not found and cid < COLUMN:
                found = c in columns[cid]
                cid += 1
            assert found, "Card: %s is missing" % str(c)
        print("Loaded Game is OK")
        
        return FreecellGame(filename, FreecellState(freecells, bases, columns))

# -------- Main freecell game --------

if __name__ == "__main__":

    # Read game id or game file
    game = None
    gid = random.randint(0, 1000000)
    if len(sys.argv) > 1:
        game_file = False
        gid = sys.argv[1]
        try:
            gid = int(gid)
        except ValueError as v:
            game_file = True
    
        if game_file:
            try:
                game = FreecellGame.from_file(gid)
            except:
                print("Please give a valid file game or game id")
                exit(1) 
    
    if game is None:
        print("Game seed:", gid)  
        deck = [Card(j, i) for i in range(1, len(CARD_VALUE)+1) for j in SUITS]
        randgen = random.Random(gid)
        randgen.shuffle(deck)
        game = FreecellGame("game_%d.save" % gid, FreecellState.init_from_deck(deck))

    run = True
    moves = []
    while run:
        print()
        if game.state.is_won:
            print("Success !")
            break

        print()
        print(game)
        print()
        choices = game.state.list_choices()
        base_available = False
        i = 0
        for choice in choices:
            print("%d)" % i, choice)
            i += 1
            if not base_available and choice.col_dest == COL_BASE:
                base_available = True
        if base_available:
            print("B) Automatic to base")
        if len(moves) > 0:
            print("Z) cancel last move")
        print("S) save")
        print("Q) quit")
        choice_id = input("Move id? ")
        if choice_id in ["Q", "q"]:
            run = False
        elif choice_id in ["S", "s"]:
            game.save_game()
        elif choice_id in ["Z", "z"] and len(moves) > 0:
            game.reverse_apply(moves.pop())
        elif choice_id in ["B", "b"] and base_available:
            auto = True
            while auto:
                auto = False
                choices = game.state.list_choices()
                for c in choices:
                    if c.col_dest == COL_BASE:
                        game.apply(c)
                        moves.append(c)
                        auto = True
        else:
            try:
                choice_id = int(choice_id)
            except ValueError:
                choice_id = -1

            if choice_id >= 0 and choice_id < len(choices):
                game.apply(choices[choice_id])
                moves.append(choices[choice_id])
            else:
                print("Wrong move id")
