#!/usr/bin/python3
# -*- coding: utf-8 -*

"""
solve a freecell game
"""

import src.model as model
import src.solvers as solver
import play
import src.save as save

import random
import sys
import time

gid = random.randint(0, 1000000)
if len(sys.argv) > 1:
    arg1 = sys.argv[1]
    try:
       gid = int(arg1)
    except ValueError as v:
        pass

#print("Game seed:", gid)
deck = model.DECK[:]
#randgen = random.Random(gid)
#randgen.shuffle(deck)
#game = model.FCGame(model.FCBoard.init_from_deck(deck))
#print(play.printBoard(game.fcboard))
#save.save_to_file("aya", game.fcboard)

start_time = time.time()

for j in range(0, 100):
    print("game:", j)
    randgen = random.Random(j)
    randgen.shuffle(deck)

    solv = solver.SolverRandom(model.FCBoard.init_from_deck(deck))

    for i in range(20):
        print(i, end=" ")
        moves = solv.solve()
        if type(moves) is list:
            print("found", len(moves))
            break
        else:
            print("not found", len(solv.noexit))

print("--- %s seconds ---" % (time.time() - start_time))

# TODO:
# - compute hash in set of bits!





