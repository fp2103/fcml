#!/usr/bin/python3
# -*- coding: utf-8 -*

"""
solve a freecell game
"""


import sys
import time

import src.solvers as solver
import play


if __name__ == "__main__":

    game, _ = play.create_game(sys.argv)

    start_time = time.time()
    
    solv = solver.Solver(game.fcboard)
    
    print(play.printBoard(game.fcboard))
    print("Finding solution...")
    continu = True
    while continu:
        try:
            res = solv.solve()
            if res[0]:
                print("iter %d:" % solv.called, "found", "in %d moves" % len(res[1]))
                reduced = solver.moves_reducer(game.fcboard, res[1])
                print("reduced to %d moves" % len(reduced))
                continu = False

                for m in reduced:
                    print(play.printChoice(m))

            else:
                print("iter %d:" % solv.called, "notfound")
        except IndexError:
            print("Not solvable!")
            continu = False
    
timespend = time.time() - start_time
print("--- runtime: %s seconds ---" % str(timespend))






