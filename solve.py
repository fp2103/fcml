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
    #reset deck
    deck = model.DECK[:]

    print("game:", j)
    randgen = random.Random(j)
    randgen.shuffle(deck)

    b = model.FCBoard.init_from_deck(deck)
    #b = save.load_from_file("impossible")
    
    #print(play.printBoard(b))

    solv = solver.SolverRandom(b)

    i = 0
    continu = True
    while continu:
        try:
            print(i, end=" ")
            i += 1
            moves = solv.solve()
            if type(moves) is list:
                print("found", len(moves))
                continu = False
            else:
                print("not found", len(solv.noexit))
        except IndexError:
            print("Not solvable!")
            continu = False
    
timespend = time.time() - start_time
print("--- %s seconds ---" % str(timespend))
print("--- per game %s --- " % str(timespend/100.0))

# TODO:
# - compute hash in set of bits!





