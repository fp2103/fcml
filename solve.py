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

coeffs = [2*100*random.random()-100 for _ in range(solver.SolverCoeff.COEFFS_SIZE)]


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
    #solv = solver.SolverCoeff(b, coeffs)

    i = 0
    continu = True
    while continu and i < 50:
        try:
            print(i, end=" ")
            i += 1
            res = solv.solve()
            if res[0]:
                a = solver.moves_reducer(b, res[1])
                print("found", len(res[1]), len(a))
                continu = False

                ga = model.FCGame(b)
                for m in a:
                    #print(play.printBoard(ga.fcboard))
                    #print(play.printChoice(m))
                    #print()
                    #print()
                    assert m.compute_hash(ga.fcboard) in set([hl.compute_hash(ga.fcboard) for hl in ga.list_choices()]), play.printBoard(ga.fcboard) +'\n'+ play.printChoice(m)
                    ga.apply(m)
                    #input()

                assert ga.fcboard.is_won()

            else:
                print("notfound", res[1], len(solv.noexit))
                #continu = False
                pass
        except IndexError:
            print("Not solvable!")
            continu = False
    
timespend = time.time() - start_time
print("--- %s seconds ---" % str(timespend))
print("--- per game %s --- " % str(timespend/100.0))






