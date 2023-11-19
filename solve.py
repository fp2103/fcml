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



start_time = time.time()

hard = []

CONST_HARD = [0, 14, 41, 63, 87, 103, 106, 108, 113, 116,
              129, 141, 171, 173, 175, 210, 221, 231, 234, 
           236, 242, 245, 251, 286, 302, 306, 316, 335, 
           340, 344, 353, 354, 384, 388, 392, 406, 425, 
           429, 453, 457, 491, 507, 514, 516, 528, 529, 
           538, 580, 583, 602, 611, 635, 638, 644, 654, 
           673, 674, 705, 732, 738, 750, 754, 757, 774, 
           780, 781, 789, 801, 820, 826, 828, 831, 847, 
           888, 905, 908, 914, 915, 933, 965]
print(len(CONST_HARD))

for j in range(0, 100):
    #reset deck
    deck = model.DECK[:]

    print("game:", j)
    randgen = random.Random(j)
    randgen.shuffle(deck)

    b = model.FCBoard.init_from_deck(deck)
    #b = save.load_from_file("impossible")
    
    solv = solver.Solver(b)

    i = 0
    continu = True
    while continu: # and i < 50:
        try:
            i += 1
            res = solv.solve()
            if res[0]:
                a = [] # solver.moves_reducer(b, res[1])
                print(solv.called, "found", len(res[1]), len(a), res[2])
                continu = False

                #ga = model.FCGame(b)
                #for m in a:
                    #print(play.printBoard(ga.fcboard))
                    #print(play.printChoice(m))
                    #print()
                    #print()
                #    assert m.compute_hash(ga.fcboard) in set([hl.compute_hash(ga.fcboard) for hl in ga.list_choices()]), play.printBoard(ga.fcboard) +'\n'+ play.printChoice(m)
                #    ga.apply(m)
                    #input()

                #assert ga.fcboard.is_won()

            else:
                print(solv.called, "notfound", res[1], len(solv.noexit))
                #continu = False
                pass
        except IndexError:
            print("Not solvable!")
            continu = False
    if i >= 5:
        hard.append(j)

print(str(hard))
    
timespend = time.time() - start_time
print("--- %s seconds ---" % str(timespend))
print("--- per game %s --- " % str(timespend/100.0))






