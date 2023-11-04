#!/usr/bin/python3
# -*- coding: utf-8 -*

"""
Functions to read and write game files
"""


# Cards
"""
    @classmethod
    def read_card(cls, scard):
        try:
            m = re.match("(\d+|[ajqk])([hdsc])", scard.lower())
            suit = m.group(2).upper()
            num = int({"a": 1, "j": 11, "q": 12, "k": 13}.get(m.group(1), m.group(1)))
            return cls(suit, num)
        except IndexError:
            raise ValueError("wrong format for card: %s" % scard)

"""
# Board

def load_from_file(filename):
    pass
"""
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
"""

def save_to_file(filename, fcboard):
    pass

"""
# fcgame

    def save(self, filename):
        with open(filename, 'w') as f:
            f.write(self.fcboard.to_string(False))
            f.write('\n')
        print("Game saved in", filename)
        print("WARNING: can't reset previous move at reload")
"""