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

not_founds = []
for j in range(0, 100):
    print("game:", j)
    randgen = random.Random(j)
    randgen.shuffle(deck)

    solv = solver.SolverRandom(model.FCBoard.init_from_deck(deck))
    #solv = solver.SolverRandom(save.load_from_file("impossible"))

    found = False
    for i in range(20):
        print(i, end=" ")
        moves = solv.solve()
        if type(moves) is list:
            print("found", len(moves))
            found = True
            break
        else:
            print("not found", len(solv.noexit))
    if not found:
        not_founds.append(j)

timespend = time.time() - start_time
print("--- %s seconds ---" % str(timespend))
print("--- per game %s --- " % str(timespend/100.0))
print("Not founds:", str(not_founds))

# TODO:
# - compute hash in set of bits!





