#!/usr/bin/python3
# -*- coding: utf-8 -*

"""
Functions to read and write game files
"""

import re
import src.model as m

def read_card(scard):
    try:
        ma = re.match("(\d+|[ajqk])([hdsc])", scard.lower())
        suit = ma.group(2).upper()
        num = int({"a": 1, "j": 11, "q": 12, "k": 13}.get(ma.group(1), ma.group(1)))
        return m.Card(suit, num)
    except IndexError:
        raise ValueError("wrong format for card: %s" % scard)

def load_from_file(filename):
    print("Load board from file:", filename)
    freecells = list()
    bases = dict((k, []) for k in m.SUITS)
    columns = [list() for _ in range(m.COLUMN)]

    verification_deck = m.DECK[:]
    def remove_from_verification(card):
        try:
            verification_deck.remove(card)
        except ValueError:
            raise ValueError("Card %s is present twice" % str(card))
    
    column_space = "    "
    def split_line(line, header=False):
        l = line.replace('\n', '')

        # measure column space from headline:
        global column_space
        if header:
            try:
                lsplited = l.split()
                s = l.index(lsplited[-4])
                e = l.rindex(lsplited[-1])
                column_space = ""
                for _ in range(int((e - s)/3)):
                    column_space += " "
            except:
                raise ValueError("Headline must contains 4 bases")

        # split cards from a line, col spaces empty or tab = col
        ret = []
        i = 0
        j = 1
        r = ""
        while j <= len(l):
            r = l[i:j]
            if r == column_space:
                ret.append('')
                i = j
            elif '\t' in r:
                ret.append(r.strip())
                i = j
            elif len(r.strip()) > 0 and r[-1] == " ":
                ret.append(r.strip())
                i = j-1
            j += 1
        ret.append(r.strip())
        # pad column so that it contains 8 cards
        ret = ret[:8]
        for _ in range(len(ret), 8):
            ret.append('')
        return ret
    
    with open(filename, 'r') as f:
        line = f.readline()
        headline_split = split_line(line, True)
        assert all([hs for hs in headline_split[4:]]), "Headline must be containing the 4 bases, spaced accordingly after the freecells"
        # Freecells
        fcstr = headline_split[:4]
        for sc in fcstr:
            if sc:
                c = read_card(sc)
                freecells.append(c)
                remove_from_verification(c)
        # Bases
        bstr = headline_split[4:]
        for bs in bstr:
            if not bs.startswith('0'):
                lbc = read_card(bs)
                for n in range(1, lbc.num+1):
                    c = m.Card(lbc.suit, n)
                    bases[lbc.suit].append(c)
                    remove_from_verification(c)

        # Second line must be empty
        line = f.readline()
        assert len(line.strip()) == 0, "line after freecells & bases must be empty"
        print("freecell & bases, ok")

        # Columns
        line = f.readline()
        while line:
            cid = 0
            for sc in split_line(line):
                if sc:
                    c = read_card(sc)
                    columns[cid].append(c)
                    remove_from_verification(c)
                cid += 1
            line = f.readline()
    
    assert len(verification_deck) == 0, "Missing some cards: %s" % ",".join([c.name for c in verification_deck])
    print("Loaded Game is OK")   
    return m.FCBoard(freecells, bases, columns)

def save_to_file(filename, fcboard):

    def padCard(c_str):
        # pad card to take 4characters
        return c_str + (" " if len(c_str) > 2 else "  ")

    with open(filename, 'w') as f:
        headline = ""
        # Print Freecells
        for a in range(0, m.FREECELL):
            c = "    "
            if a < len(fcboard.freecells):
                c = padCard(fcboard.freecells[a].name)
            headline += c
        
        # Print Bases
        for bk, b in fcboard.bases.items():
            c = b[-1].name if len(b) > 0 else "0%s" % bk
            headline += padCard(c)
        
        f.write(headline + "\n")
        # line between freecell/base and columns must be empty
        f.write("\n") 

        # Print columns
        maxl = max([len(col) for col in fcboard.columns])
        for l in range(0, maxl):
            line = ""
            for col in fcboard.columns:
                if l < len(col):
                    line += padCard(col[l].name)
                else:
                    line += "    "
            f.write(line + "\n")

        f.write('\n')
    print("Game saved in", filename)
    print("WARNING: can't reset previous move at reload")
