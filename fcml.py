#!/usr/bin/python3
# -*- coding: utf-8 -*

"""
Solve Freecell with tree search and evolutionary algorithm on best solvers
"""

import sys
import random

import freecell as fc
import conf as p
from train import train
from solvers import SolverCoeff, SolverRandom

def get_strategies():
    ret = []
    print("Getting best known solvers from", p.DBFILE)
    with open(p.DBFILE, "r") as f:
        i = 0
        for line in f.readlines():
            coeffs = [float(c) for c in line.replace('[', '').replace(']', '').split(',')]
            ret.append(SolverCoeff("f%d"%i, coeffs))
            i += 1
    print("Retrieved %d strategies" % len(ret))
    return ret

    
# ------ Main Solver script --------    
if __name__ == "__main__":

    usage = "./fcml2022.py solve <game file>\n" + \
            "              train <games_range> <loop> <nkids>\n" + \
            "games_range: 1-100 or 1,2,3 or 1-10,20,30-32"

    if len(sys.argv) < 2:
        print(usage)
        exit(1)

    # Training mode
    if sys.argv[1] == "train":
        if len(sys.argv) < 5:
            print(usage)
            exit(1)

        # Read parameters
        games_id = set()
        loop = 0
        nkids = 0
        try:
            # games range
            for gr in sys.argv[2].split(','):
                r = gr.split('-')
                sg = int(r[0])
                eg = int(r[1])+1 if len(r) > 1 else sg+1
                for i in range(sg, eg):
                    games_id.add(i)
            
            # loop
            loop = int(sys.argv[3])

            # n kids
            nkids = int(sys.argv[4])
            
        except ValueError as v:
            print(v)
            print(usage)
            exit(1)
        
        # Retreive strategies
        known_strategies = []
        try:
            known_strategies = get_strategies()
        except FileNotFoundError:
            print("File", p.DBFILE, "doesn't exist, continue without known solvers")

        train(known_strategies, loop, games_id, nkids)

    # Solving mode
    elif sys.argv[1] == "solve":
        if len(sys.argv) < 3:
            print(usage)
            exit(1)

        filename = int(sys.argv[2])
        try:
            deck = fc.DECK[:]
            randgen = random.Random(filename)
            randgen.shuffle(deck)
            #games_init_board[gid] = fc.FCBoard.init_from_deck(deck)
            #game = fc.FCGame("lala", fc.FCBoard.init_from_file(filename))
            game = fc.FCGame(filename, fc.FCBoard.init_from_deck(deck))
        except:
            print("Please give a valid game file")
            exit(1)
        

        sr = SolverRandom()
        #sr.solve(game)
        
        hard = []
        for a in [14, 18, 23, 37, 63, 73, 87, 100]:
            print()
            print(a)
            deck = fc.DECK[:]
            randgen = random.Random(a)
            randgen.shuffle(deck)
            ret = sr.solve(fc.FCGame(filename, fc.FCBoard.init_from_deck(deck)))
            if ret >= 10:
                hard.append(a)
        
        print(hard)

       
    else:
        print(usage)
        exit(1)
    
    exit(0)


# TODO:
# b. multiprocess N
# c. solve (random + multiprocessed)
# d. UI
# 