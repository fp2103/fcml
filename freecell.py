#!/usr/bin/python3
# -*- coding: utf-8 -*

"""
Simple freecell game
"""

import sys
import re
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
        if num < 1 or num > len(CARD_VALUE):
            raise ValueError("Incorrect card number")
        if suit not in SUITS:
            raise ValueError("Incorrect suit")
        
        self.num = num
        self.suit = suit
        self.is_red = suit in RED
        self.name = "%s%s" % (str(CARD_VALUE[num-1]), suit)
        self.uid = SUITS.index(suit) * len(CARD_VALUE) + num

    def __str__(self):
        if self.is_red:
            return TermColor.RED + self.name + TermColor.ENDC
        return self.name

    def __eq__(self, other):
        if isinstance(other, Card):
            return self.uid == other.uid
        return False

    def __hash__(self):
        return self.uid

    @classmethod
    def read_card(cls, scard):
        try:
            m = re.match("(\d+|[ajqk])([hdsc])", scard.lower())
            suit = m.group(2).upper()
            num = int({"a": 1, "j": 11, "q": 12, "k": 13}.get(m.group(1), m.group(1)))
            return cls(suit, num)
        except IndexError:
            raise ValueError("wrong format for card: %s" % scard)

DECK = [Card(j, i) for i in range(1, len(CARD_VALUE)+1) for j in SUITS]

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
    
    def get_reverse(self):
        return Choice(self.cards, self.col_dest, self.col_orig)

class FCBoard(object):
    def __init__(self, freecells, bases, columns):
        self.freecells = freecells  # list[4]
        self.bases = bases          # dict {suit: [cards]}
        self.columns = columns      # list[8][cards]
    
    def __str__(self):
        return self.to_string(True)
    
    def to_string(self, colorize):
        game_line = []
        headline = []
        # Print Freecells
        for a in range(0, FREECELL):
            c = ""
            if a < len(self.freecells):
                c = str(self.freecells[a]) if colorize else self.freecells[a].name
            headline.append(c)
        # Print Bases
        for bk, b in self.bases.items():
            c = (str(b[-1]) if colorize else b[-1].name) if len(b) > 0 else "0%s" % bk
            headline.append(c)
        game_line.append("\t".join(headline))
        game_line.append("")
        # Print columns
        maxl = max([len(col) for col in self.columns])
        for l in range(0, maxl):
            line = []
            for col in self.columns:
                if l < len(col):
                    line.append(str(col[l]) if colorize else col[l].name)
                else:
                    line.append("")
            game_line.append("\t".join(line))
        return "\n".join(game_line)
    
    def clone(self):
        f = list(self.freecells)
        b = dict((k, list(self.bases.get(k))) for k in SUITS)
        c = [list(self.columns[i]) for i in range(COLUMN)]
        return FCBoard(f, b, c)
    
    def is_won(self):
        return sum([len(self.bases.get(k)) for k in SUITS]) == 52

    def apply(self, choice):
        c0 = choice.cards[0]

        # From origin
        if choice.col_orig == COL_FC:
            self.freecells.remove(c0)
        elif choice.col_orig == COL_BASE:
            self.bases.get(c0.suit).remove(c0)
        else:
            for _ in choice.cards:
                self.columns[choice.col_orig].pop()
        
        # To dest
        if choice.col_dest == COL_BASE:
            self.bases.get(c0.suit).append(c0)
        elif choice.col_dest == COL_FC:
            self.freecells.append(c0)
        else:
            self.columns[choice.col_dest].extend(choice.cards)
    
    @classmethod
    def init_from_deck(cls, deck):
        columns = [[] for _ in range(0, COLUMN)]
        i = 0
        for c in deck:
            columns[i].append(c)
            i = i+1 if i < COLUMN-1 else 0
        
        return cls([], dict((k, []) for k in SUITS), columns)
    
    @classmethod
    def init_from_file(cls, filename):
        print("Load board from file:", filename)
        freecells = list()
        bases = dict((k, []) for k in SUITS)
        columns = [list() for _ in range(COLUMN)]

        verification_deck = DECK[:]
        def remove_from_verification(card):
            try:
                verification_deck.remove(card)
            except ValueError:
                raise ValueError("Card %s is present twice" % str(card))
        
        with open(filename, 'r') as f:
            line = f.readline()
            # Freecells
            fcstr = line.split()[:-4]
            for sc in fcstr:
                c = Card.read_card(sc)
                freecells.append(c)
                remove_from_verification(c)
            # Bases
            bstr = line.split()[-4:]
            for bs in bstr:
                if not bs.startswith('0'):
                    lbc = Card.read_card(bs)
                    for n in range(1, lbc.num+1):
                        c = Card(lbc.suit, n)
                        bases[lbc.suit].append(c)
                        remove_from_verification(c)

            # Second line must be empty
            line = f.readline()
            assert len(line.strip()) == 0, "line after freecells & bases must be empty"
            print("freecell & bases, ok")

            # Columns
            line = f.readline()
            while line:
                line = line.replace('\n', '')
                cid = 0
                for sc in line.split("\t"):
                    if len(sc) > 0:
                        c = Card.read_card(sc)
                        columns[cid].append(c)
                        remove_from_verification(c)
                    cid += 1
                line = f.readline()
        
        assert len(verification_deck) == 0, "Missing some cards: %s" % str(verification_deck)
        print("Loaded Game is OK")   
        return cls(freecells, bases, columns)

class FCGame(object):
    def __init__(self, name, fcboard):
        self.name = name
        self.fcboard = fcboard

        self._column_series = [self._get_column_series(i) for i in range(COLUMN)]
    
    def _get_column_series(self, col_id):
        col = self.fcboard.columns[col_id]
        serie = []
        last_card = None
        for card in reversed(col):
            # End serie if last card doesn't match
            if last_card is not None:
                if last_card.is_red == card.is_red or card.num - last_card.num != 1:
                    break
            serie.append(card)
            last_card = card
        serie.reverse()
        return serie
    
    def _update_column_series(self, col_id):
        if col_id != COL_FC and col_id != COL_BASE:
            self._column_series[col_id] = self._get_column_series(col_id)
    
    def _get_mvt_max(self):
        freecol = sum([len(col) == 0 for col in self.fcboard.columns])
        max_mvt = (1 + FREECELL - len(self.fcboard.freecells)) * (1 + freecol)
        max_mvt_freecol_dst =  (1 + FREECELL - len(self.fcboard.freecells)) * freecol
        return (max_mvt, max_mvt_freecol_dst)
    
    def _find_choice_from_cards(self, num, suits, height_max, col_dest):
        ret = []
        wanted_cards = [Card(s, num) for s in suits]
        i = 0
        while i < len(wanted_cards):
            card = wanted_cards[i]
            i += 1

            # Continue if already in bases
            if card in self.fcboard.bases.get(card.suit):
                continue

            # Look in freecells
            if card in self.fcboard.freecells:
                ret.append(Choice([card], COL_FC, col_dest))
                continue

            # Look in columns
            for cid in range(COLUMN):
                if cid == col_dest:
                    continue
                col = self._column_series[cid]
                if card in col:
                    idx = col.index(card)
                    if (len(col) - idx) <= height_max+1:
                        ret.append(Choice(col[idx:], cid, col_dest))
                        break
        return ret  
    
    def list_choices(self):
        """ Compute choice from destination """
        choices = []
        max_mvt, max_mvt_empty = self._get_mvt_max()

        # Bases
        for suit, base in self.fcboard.bases.items():
            if len(base) < 13:
                choices.extend(self._find_choice_from_cards(len(base)+1, [suit], 0, COL_BASE))
        
        for cid in range(COLUMN):
            col = self._column_series[cid]
            if len(col) > 0:
                # Search specific cards
                last_card = col[-1]
                if last_card.num > 1:
                    choices.extend(self._find_choice_from_cards(last_card.num-1, BLACK if last_card.is_red else RED, max_mvt, cid))
                
                # to Freecell
                if len(self.fcboard.freecells) < FREECELL:
                    choices.append(Choice([col[-1]], cid, COL_FC))
            else:
                # from Freecell
                for c in self.fcboard.freecells:
                    choices.append(Choice([c], COL_FC, cid))

                # from other columns
                for cid2 in range(COLUMN):
                    if cid == cid2:
                        continue
                    col2 = self._column_series[cid2]
                    for j in range(max(0, len(col2)-max_mvt_empty), len(col2)):
                        choices.append(Choice(col2[j:], cid2, cid))
        
        return choices

    def apply(self, choice):
        self.fcboard.apply(choice)
        self._update_column_series(choice.col_orig)
        self._update_column_series(choice.col_dest)
        
    def save(self, filename):
        with open(filename, 'w') as f:
            f.write(self.fcboard.to_string(False))
            f.write('\n')
        print("Game saved in", filename)
        print("WARNING: can't reset previous move at reload")

# -------- Main freecell game --------
if __name__ == "__main__":

    # Read game id or game file
    game = None
    game_filename = ""
    gid = random.randint(0, 1000000)
    if len(sys.argv) > 1:
        game_file = False
        gid = sys.argv[1]
        try:
            gid = int(gid)
        except ValueError as v:
            game_file = True
    
        if game_file:
            game = FCGame(gid, FCBoard.init_from_file(gid))
            game_filename = gid
            
    if game is None:
        print("Game seed:", gid)
        deck = DECK[:]
        randgen = random.Random(gid)
        randgen.shuffle(deck)
        game = FCGame(str(gid), FCBoard.init_from_deck(deck))
        game_filename = "game_%d.save" % gid

    run = True
    moves = []
    while run:
        print()
        if game.fcboard.is_won():
            print("Success !")
            break

        print()
        print(game.fcboard)
        print()
        choices = game.list_choices()
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
            game.save(game_filename)
        elif choice_id in ["Z", "z"] and len(moves) > 0:
            last = moves.pop()
            game.apply(last.get_reverse())
        elif choice_id in ["B", "b"] and base_available:
            auto = True
            while auto:
                auto = False
                choices = game.list_choices()
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
