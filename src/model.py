#!/usr/bin/python3
# -*- coding: utf-8 -*

"""
Describe a freecell game
"""

RED = ["H", "D"]
BLACK = ["S", "C"]
SUITS = RED + BLACK
CARD_VALUE = ["a", 2, 3, 4, 5, 6, 7, 8, 9, 10, "j", "q", "k"]
FREECELL = 4
COLUMN = 8
COL_BASE = "B"
COL_FC = "FC"

class Card(object):
    def __init__(self, suit, num):
        if num < 1 or num > len(CARD_VALUE):
            raise ValueError("Incorrect card number")
        if suit not in SUITS:
            raise ValueError("Incorrect suit")
        
        self.num = num
        self.suit = suit
        self.name = "%s%s" % (str(CARD_VALUE[num-1]), suit)

        self.is_red = suit in RED
        self.uid = (num << 2) + SUITS.index(suit)
 
    def __eq__(self, other):
        if isinstance(other, Card):
            return self.uid == other.uid
        return False

    def __hash__(self):
        return self.uid

DECK = [Card(j, i) for i in range(1, len(CARD_VALUE)+1) for j in SUITS]

class FCBoard(object):
    def __init__(self, freecells, bases, columns):
        self.freecells = freecells  # list[4]
        self.bases = bases          # dict {suit: [cards]}
        self.columns = columns      # list[8][cards]
        
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
    
    def compute_hash(self):
        fc_bits = 0
        for c in self.freecells:
            fc_bits += 1 << c.uid
        
        cols = []
        for i in range(COLUMN):
            col_bits = 0
            j = 0
            for c in self.columns[i]:
                col_bits += c.uid << (j*6)
                j += 1
            cols.append(col_bits)
        cols.sort()

        return (fc_bits, *cols)
    
    
class Choice(object):
    def __init__(self, cards, col_orig, col_dest):
        self.cards = cards
        self.col_orig = col_orig
        self.col_dest = col_dest

        self.weight = 0
    
    def get_reverse(self):
        return Choice(self.cards, self.col_dest, self.col_orig)
    
    def compute_hash(self, fcboard):
        cards_bit = 0
        for c in self.cards:
            cards_bit += 1 << c.uid
        
        orig_bit = 0
        if self.col_orig == COL_FC:
            orig_bit = 2
        else:
            i = 0
            for c in fcboard.columns[self.col_orig][:-len(self.cards)]:
                orig_bit += c.uid << (i*6)
                i += 1
        
        dest_bit = 0
        if self.col_dest == COL_BASE:
            dest_bit = 1
        elif self.col_dest == COL_FC:
            dest_bit = 2
        else:
            i = 0
            for c in fcboard.columns[self.col_dest]:
                dest_bit += c.uid << (i*6)
                i += 1
        
        if dest_bit > orig_bit:
            return (cards_bit, dest_bit, orig_bit)
        else:
            return (cards_bit, orig_bit, dest_bit)
    
    def equals(self, other):
        return other.cards == self.cards and other.col_orig == self.col_orig and other.col_dest == self.col_dest


class FCGame(object):
    def __init__(self, fcboard):
        self.fcboard = fcboard

        # pre-compute columns serie, to not compute them every time!
        self._column_series = [self._get_column_series(i) for i in range(COLUMN)]
        self._last_max_mvt = 0
    
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
    
    def _compute_mvt_max(self):
        freecol = sum([len(col) == 0 for col in self.fcboard.columns])
        max_mvt = (1 + FREECELL - len(self.fcboard.freecells)) * (1 + freecol)
        max_mvt_empty =  (1 + FREECELL - len(self.fcboard.freecells)) * freecol
        self._last_max_mvt = max_mvt
        return max_mvt, max_mvt_empty

    def list_choices(self):
        """ Compute choice from destination (except for bases) """
        choices = []
        # compute size of mvt allowed:
        max_mvt, max_mvt_empty = self._compute_mvt_max()

        # Bases from freecell
        for c in self.fcboard.freecells:
            if c.num == len(self.fcboard.bases[c.suit]) + 1:
                choices.append(Choice([c], COL_FC, COL_BASE))
        
        # Columns
        for cid in range(COLUMN):
            col = self._column_series[cid]
            if len(col) > 0:
                last_card = col[-1]

                # to Base
                if last_card.num == len(self.fcboard.bases[last_card.suit]) + 1:
                    choices.append(Choice([last_card], cid, COL_BASE))

                # Search specific cards
                if last_card.num > 1:
                    wanted_is_red = not last_card.is_red
                    wanted_num = last_card.num-1
                    
                    # from freecell
                    for c in self.fcboard.freecells:
                        if c.num == wanted_num and c.is_red == wanted_is_red:
                            choices.append(Choice([c], COL_FC, cid))
                            
                    # from other col
                    for cid2 in range(COLUMN):
                        if cid == cid2:
                            continue
                        col2 = self._column_series[cid2]
                        idx = 0
                        for c in col2:
                            if c.num == wanted_num and c.is_red == wanted_is_red:
                                if (len(col2) - idx) <= max_mvt:
                                    choices.append(Choice(col2[idx:], cid2, cid))
                                break
                            idx += 1
                
                # to Freecell
                if len(self.fcboard.freecells) < FREECELL:
                    choices.append(Choice([last_card], cid, COL_FC))
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
