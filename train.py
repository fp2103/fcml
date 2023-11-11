#!/usr/bin/python3
# -*- coding: utf-8 -*

"""
Find best coeff to solve most games
"""

# ----- Config -----

GID=0
NGAME=1
NGAME_MAX=1

NRANDOM=1
NBEST=1
NCHILD=10

NRANDOM_START=20
NOIMPROVMENT_STOP=5
#STRATS_FILE="aya"

COEFF_RANGE = 100
KIDS_SIGMA = 3.0

MAX_STRAT_TRIED = 200

# ---------

import src.model as model
import src.solvers as solver

import play

import random

class Game(object):
    def __init__(self, name, board):
        self.name = str(name)
        self.board = board

class Strat(object):
    def __init__(self, name, coeffs):
        self.name = name
        self.coeffs = coeffs

        self.played = set()
        self.solved = set()
        self.tot_in_bases = 0
        self.tot_moves = 0
        self.tot_iter = 0
    
    def solve(self, game):
        print(self.name, "on game", game.name, end=" ")
        if game.name in self.played:
            print("found" if game.name in self.solved else "notfound")
            return
        
        s = solver.SolverCoeff(game.board, self.coeffs)
        res = s.solve()
        self.played.add(game.name)
        if res[0]:
            print("found", len(res[1]), res[2])
            self.solved.add(game.name)
            self.tot_in_bases += 52
            self.tot_moves += len(res[1])
            self.tot_iter += res[2]
        else:
            print("notfound", res[1])
            self.tot_in_bases += res[1]
            self.tot_iter += res[2]

    def get_stats(self):
        pf = float(len(self.played))
        mib = self.tot_in_bases/pf
        mm = 0
        if len(self.solved) > 0:
            mm = self.tot_moves/float(len(self.solved))
        mi = self.tot_iter/pf
        # moves and iter negative, because we want smallest possible
        return (len(self.solved), mib, -mm, -mi)

    def make_random_kid_coeffs(self):
        return [(c + random.gauss(0.0, KIDS_SIGMA)) for c in self.coeffs]
    
    def make_converging_kid_coeffs(self, converging_coeffs):
        ret = []
        for i in range(solver.SolverCoeff.COEFFS_SIZE):
            sigma = (converging_coeffs[i]-self.coeffs[i])/2.0
            signe = 1.0 if converging_coeffs[i] >= self.coeffs else -1.0
            ret.append(self.coeffs[i] + signe*abs(random.gauss(0.0, sigma)))
        return ret

def solve_specific_game(game):
    print("Finding strat for game", game.name)

    # create strategies
    rid = 0
    strats = []
    for _ in range(NRANDOM_START):
        coeffs = [2*100*random.random()-100 for _ in range(solver.SolverCoeff.COEFFS_SIZE)]
        strats.append(Strat("g%sr%d" % (game.name, rid), coeffs))
        rid += 1

    best = None
    no_improvement_count = 0
    gen = 0
    while no_improvement_count < NOIMPROVMENT_STOP:
        print("--- Gen %d ---" % gen)
        gen += 1
        
        for s in strats:
            s.solve(game)
        
        strats.sort(key=lambda x: x.get_stats(), reverse=True)
        if best is not None and strats[0].name == best.name:
            print("No improvement")
            no_improvement_count += 1
        else:
            print("Best strat is %s" % strats[0].name, strats[0].get_stats())
            no_improvement_count = 0
        best = strats[0]

        strats = [best]
        # Create random kids
        for k in range(NCHILD):
            strats.append(Strat("%s:r%d" % (best.name, k), best.make_random_kid_coeffs()))
        
        if len(best.solved) == 0:
            print("Still no solution, adding random games")
            for _ in range(NRANDOM):
                coeffs = [2*100*random.random()-100 for _ in range(solver.SolverCoeff.COEFFS_SIZE)]
                strats.append(Strat("g%sr%d" % (game.name, rid), coeffs))
                rid += 1

    ret = None
    if len(best.solved) > 0:
        ret = best
        ret.name = "g%sbs" % game.name
        print("Solution found for game", game.name, ret.name, ret.get_stats())
    return ret


deck = model.DECK[:]
randgen = random.Random(4)
randgen.shuffle(deck)
g = Game(4, model.FCBoard.init_from_deck(deck))

a = solve_specific_game(g)


solv = solver.SolverCoeff(g.board, a.coeffs)
res = solv.solve()
print(play.printBoard(g.board))
moves = res[1]
for m in moves:
    print(play.printChoice(m))


def get_best_covering_strats(strats, games):
    ret = []

    # TODO: keeps stats for each games played

    return ret


###
# create/read strats
# 
# play them on games
# 
# if all solved -> add new game (play it by all) until unsolved or maxgames
# if unsolved -> solve_specific_game(), play all other games 
#                until all solved
#
# find best coverage
# 
# compute mean convergent
# 
# create kids random and converging
#
# restart to play
