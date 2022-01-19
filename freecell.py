#!/usr/bin/python3
# -*- coding: utf-8 -*

"""
Simple freecell game
"""

import sys
import random
import os

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

    @staticmethod
    def remove_from_str(str):
        res = str.replace(TermColor.GREEN, '')
        res = res.replace(TermColor.RED, '')
        res = res.replace(TermColor.ENDC, '')
        return res

class Card(object):
    def __init__(self, suit, num):
        self.num = num
        self.suit = suit
        self.color = "RED" if suit in RED else "BLACK"

        self.uid = SUITS.index(suit) * len(CARD_VALUE) + num

    def __str__(self):
        s = "%s%s" % (str(CARD_VALUE[self.num-1]), self.suit)
        if self.color == "RED":
            s = TermColor.RED + s + TermColor.ENDC
        return s
    
    def uncolored(self):
        return "%s%s" % (str(CARD_VALUE[self.num-1]), self.suit)
    
    def __eq__(self, other):
        if isinstance(other, Card):
            return self.uid == other.uid
        else:
            return False

    def __hash__(self):
        return self.uid

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
        
class FreecellGame(object):
    def __init__(self, deck):
        self.base = dict((k, []) for k in SUITS)
        self.freecell = []
        self.column = [[] for i in range(0, COLUMN)]

        i = 0
        for c in deck:
            self.column[i].append(c)
            i = i+1 if i < COLUMN-1 else 0
            
    def __str__(self):
        game_line = []
        # Print freecell and bases
        headline = []
        for a in range(0, FREECELL):
            c = ""
            if a < len(self.freecell):
                c = str(self.freecell[a])
            headline.append(c)
        for bk, b in self.base.items():
            c = b[-1] if len(b) > 0 else "0%s" % bk
            headline.append(str(c))
        game_line.append("\t".join(headline))
        game_line.append("")

        # Print columns
        maxl = max([len(col) for col in self.column])
        for l in range(0, maxl):
            line = []
            for col in self.column:
                if l < len(col):
                    line.append(str(col[l]))
                else:
                    line.append("")
            game_line.append("\t".join(line))
        
        return "\n".join(game_line)

    def _list_available_dest(self, card, cur_col=None, last_from_col=True):
        dest = []
        # To base
        b = self.base.get(card.suit)
        if last_from_col and card.num - len(b) == 1:
            dest.append(COL_BASE)

        # To other columns
        for i in range(0, COLUMN):
            if i != cur_col:
                col = self.column[i]
                if len(col) > 0:
                    last_c = col[-1]
                    if last_c.color != card.color and last_c.num - card.num == 1:
                        dest.append(i)
                else:
                    dest.append(i)

        # To freecell
        if last_from_col and cur_col is not None and len(self.freecell) < FREECELL:
            dest.append(COL_FC)

        return dest

    def count_serie_max(self):
        freecol = 0
        for col in self.column:
            if len(col) == 0:
                freecol += 1
        max = (1 + FREECELL - len(self.freecell)) * (1 + freecol)
        max_freecol_dst =  (1 + FREECELL - len(self.freecell)) * freecol
        return (max, max_freecol_dst)

    def list_choices(self):
        choices = []
        # Freecell
        for card in self.freecell:
            for dst in self._list_available_dest(card):
                choices.append(Choice([card], COL_FC, dst))

        # Columns
        serie_max, serie_max_freecol_dst  = self.count_serie_max()
        for i in range(0, COLUMN):
            col = self.column[i]
            col_serie = []
            last_card = None
            for card in reversed(col):
                # End serie over the maximum
                if len(col_serie) >= serie_max:
                    break
                # End serie if last card doesn't match
                if last_card is not None:
                    if last_card.color == card.color or card.num - last_card.num != 1:
                        break
                col_serie.append(card)
                last_card = card
            col_serie.reverse()
            for j in range(0, len(col_serie)):
                card = col_serie[j]
                for dst in self._list_available_dest(card, i, j+1==len(col_serie)):
                    if dst in range(0, COLUMN) and len(self.column[dst]) == 0 \
                        and len(col_serie) - j > serie_max_freecol_dst:
                        continue
                    choices.append(Choice(col_serie[j:], i, dst))

        return choices

    def apply(self, choice):
        # From origin
        if choice.col_orig == COL_FC:
            self.freecell.remove(choice.cards[0])
        else:
            for _ in choice.cards:
                self.column[choice.col_orig].pop()
        
        # To dest
        if choice.col_dest == COL_BASE:
            card = choice.cards[0]
            self.base.get(card.suit).append(card)
        elif choice.col_dest == COL_FC:
            self.freecell.append(choice.cards[0])
        else:
            self.column[choice.col_dest].extend(choice.cards)

    def reverse_apply(self, choice):
        # To orig
        if choice.col_orig == COL_FC:
            self.freecell.append(choice.cards[0])
        else:
            self.column[choice.col_orig].extend(choice.cards)
        
        # From dest
        if choice.col_dest == COL_BASE:
            card = choice.cards[0]
            self.base.get(card.suit).remove(card)
        elif choice.col_dest == COL_FC:
            self.freecell.remove(choice.cards[0])
        else:
            for _ in choice.cards:
                self.column[choice.col_dest].pop()
    
    def is_won(self):
        return min([len(b) for _, b in self.base.items()]) == len(CARD_VALUE)

def save_game(filename, game):
    with open(filename, 'w') as f:
        str_game = str(game)
        for l in str_game.splitlines():
            f.write(TermColor.remove_from_str(l)+'\n')
        f.write('\n')
    print("Game saved in", filename)
    print("WARNING: can't reset previous move at reload")

def read_card(scard):
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
    if value < 0 or value > 13:
        raise ValueError("Value in %s is not correct" % scard)
    
    return Card(suit, value)
    
def load_game(filename):
    print("Load game file:", filename)
    freecell = list()
    bases = dict((k, []) for k in SUITS)
    columns = [list() for _ in range(COLUMN)]
    with open(filename, 'r') as f:
        # First line must be Freecell and bases
        line = f.readline()
        line = TermColor.remove_from_str(line)

        # Freecell
        fcstr = line.split()[:-4]
        for sc in fcstr:
            freecell.append(read_card(sc))
        
        # Bases
        bstr = line.split()[-4:]
        for bs in bstr:
            if not bs.startswith('0'):
                lbc = read_card(bs)
                for n in range(1, lbc.num+1):
                    bases[lbc.suit].append(Card(lbc.suit, n))

        # Second line must be empty
        line = f.readline()
        assert len(line.strip()) == 0
        print("freecell & bases, ok")

        # Start of column
        line = f.readline()
        while line:
            line = TermColor.remove_from_str(line)
            line = line.replace('\n', '')
            cid = 0
            for sc in line.split("\t"):
                if len(sc) > 0:
                    columns[cid].append(read_card(sc))
                cid += 1
            line = f.readline()
    
    # Initialize game
    game = FreecellGame([])
    game.freecell = freecell
    game.base = bases
    game.column = columns
    
    # Check we have 52 cards total
    count = len(game.freecell)
    for _, b in game.base.items():
        count += len(b)
    for col in game.column:
        count += len(col)
    assert count == 52
    print("52 cards, ok")

    # Check all cards are somewhere
    standard_deck = [Card(j, i) for i in range(1, len(CARD_VALUE)+1) for j in SUITS]
    for c in standard_deck:
        #print(c)
        found = c in game.base.get(c.suit) or c in game.freecell
        cid = 0
        while not found and cid < COLUMN:
            found = c in game.column[cid]
            cid += 1
        assert found
    print("Loaded Game is OK")
    
    return game

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
                game = load_game(gid)
            except:
                print("Please give a valid file game or game id")
                exit(1) 
    
    if game is None:
        print("Game seed:", gid)  
        deck = [Card(j, i) for i in range(1, len(CARD_VALUE)+1) for j in SUITS]
        randgen = random.Random(gid)
        randgen.shuffle(deck)
        game = FreecellGame(deck)

    run = True
    moves = []
    while run:
        print()
        if game.is_won():
            print("Success !")
            break

        print()
        print(game)
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
        if choice_id in ["S", "s"]:
            save_game("game_%d.save" % gid, game)
        elif choice_id in ["Z", "z"] and len(moves) > 0:
            game.reverse_apply(moves.pop())
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
