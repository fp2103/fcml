#!/usr/bin/python3
# -*- coding: utf-8 -*

"""
Simple in terminal freecell game
"""

import src.model as m
import src.save as save

class TermColor:
    GREEN = '\033[92m'
    RED = '\033[91m'
    ENDC = '\033[0m'

def printCard(card):
    if card.is_red:
        return TermColor.RED + card.name + TermColor.ENDC
    return card.name

def printBoard(fcboard):
    game_line = []
    headline = []
    # Print Freecells
    for a in range(0, m.FREECELL):
        c = ""
        if a < len(fcboard.freecells):
            c = printCard(fcboard.freecells[a])
        headline.append(c)
    # Print Bases
    for bk, b in fcboard.bases.items():
        c = printCard(b[-1]) if len(b) > 0 else "0%s" % bk
        headline.append(c)
    game_line.append("\t".join(headline))
    game_line.append("")
    # Print columns
    maxl = max([len(col) for col in fcboard.columns])
    for l in range(0, maxl):
        line = []
        for col in fcboard.columns:
            if l < len(col):
                line.append(printCard(col[l]))
            else:
                line.append("")
        game_line.append("\t".join(line))
    return "\n".join(game_line)

def printChoice(choice):
    list_card = [printCard(c) for c in choice.cards]
    col_dest_s = str(choice.col_dest)
    if choice.col_dest == m.COL_BASE:
        col_dest_s = TermColor.GREEN + col_dest_s + TermColor.ENDC
    return ",".join(list_card) + " from %s to %s" % (str(choice.col_orig), col_dest_s)


# -------- Main freecell game --------

import sys
import random

if __name__ == "__main__":

    # Read game id or game file
    game = None
    game_filename = ""
    gid = random.randint(0, 1000000)
    if len(sys.argv) > 1:
        game_file = False
        arg1 = sys.argv[1]
        try:
            gid = int(arg1)
        except ValueError as v:
            game = m.FCGame(save.load_from_file(arg1))
            game_filename = arg1
            
    if game is None:
        print("Game seed:", gid)
        deck = m.DECK[:]
        randgen = random.Random(gid)
        randgen.shuffle(deck)
        game = m.FCGame(m.FCBoard.init_from_deck(deck))
        game_filename = "game_%d.save" % gid

    run = True
    moves = []
    while run:
        print()
        if game.fcboard.is_won():
            print("Success !")
            break

        print()
        print(printBoard(game.fcboard))
        print()
        choices = game.list_choices()
        base_available = False
        i = 0
        for choice in choices:
            print("%d)" % i, printChoice(choice))
            i += 1
            if not base_available and choice.col_dest == m.COL_BASE:
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
            save.save_to_file(game_filename, game.fcboard)
        elif choice_id in ["Z", "z"] and len(moves) > 0:
            last = moves.pop()
            game.apply(last.get_reverse())
        elif choice_id in ["B", "b"] and base_available:
            auto = True
            while auto:
                auto = False
                choices = game.list_choices()
                for c in choices:
                    if c.col_dest == m.COL_BASE:
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


