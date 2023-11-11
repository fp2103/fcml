#!/usr/bin/python3
# -*- coding: utf-8 -*

"""
Find best coeff to solve most games
"""

# ----- Config -----

GID=0
NGAME=5
NGAME_MAX=10

STRATS_FILE="aya"

NRANDOM=10
NKIDS=10

NRANDOM_START=20
NOIMPROVMENT_STOP=5

COEFF_RANGE = 100
KIDS_SIGMA = 3.0

# ---------

import src.model as model
import src.solvers as solver

import random

class Game(object):
    def __init__(self, name, board):
        self.name = str(name)
        self.board = board

class Strat(object):
    def __init__(self, name, coeffs):
        self.name = name
        self.coeffs = coeffs

        self.played = dict()
    
    def solve(self, game):
        print(self.name, "on game", game.name, end=" ")
        res = self.played.get(game.name, None)
        
        if res is None:
            s = solver.SolverCoeff(game.board, self.coeffs)
            res = s.solve()
            if res[0]:
                self.played[game.name] = (True, 52.0, len(res[1]), res[2])
            else:
                self.played[game.name] = (False, res[1], 0.0, res[2])
            res = self.played[game.name]

        if res[0]:
            print("found", res[2], res[3])
        else:
            print("notfound", res[1])
    
    def has_solved(self, gname):
        res = self.played.get(gname, [False])
        return res[0]

    def get_stats(self, gnames):

        tot_played = 0.0
        tot_solved = 0.0
        tot_in_bases = 0.0
        tot_moves = 0.0
        tot_iter = 0.0

        for gname in gnames:
            res = self.played.get(gname, None)
            if res is not None:
                tot_played += 1.0
                tot_solved += float(res[0])
                tot_in_bases += float(res[1])
                tot_moves += float(res[2])
                tot_iter += float(res[3])
        mib = 0
        mi = 0
        if tot_played > 0:
            mib = tot_in_bases/tot_played
            mi = tot_iter/tot_played
        mm = 0
        if tot_solved > 0:
            mm = tot_moves/tot_solved
        # moves and iter negative, because we want smallest possible
        return (tot_solved, mib, -mm, -mi)

    def make_random_kid_coeffs(self):
        return [(c + random.gauss(0.0, KIDS_SIGMA)) for c in self.coeffs]
    
    def make_converging_kid_coeffs(self, converging_coeffs):
        ret = []
        for i in range(solver.SolverCoeff.COEFFS_SIZE):
            sigma = (converging_coeffs[i]-self.coeffs[i])/2.0
            signe = 1.0 if converging_coeffs[i] >= self.coeffs[i] else -1.0
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
        print("--- Game %s -- Gen %d ---" % (game.name, gen))
        gen += 1
        
        for s in strats:
            s.solve(game)
        
        strats.sort(key=lambda x: x.get_stats([game.name]), reverse=True)
        if best is not None and strats[0].name == best.name:
            print("No improvement")
            no_improvement_count += 1
        else:
            print("Best strat is %s" % strats[0].name, strats[0].get_stats([game.name]))
            no_improvement_count = 0
        best = strats[0]

        strats = [best]
        # Create random kids
        for k in range(NKIDS):
            strats.append(Strat("%s:r%d" % (best.name, k), best.make_random_kid_coeffs()))
        
        if not best.has_solved(game.name):
            print("Still no solution, adding random games")
            for _ in range(NRANDOM):
                coeffs = [2*100*random.random()-100 for _ in range(solver.SolverCoeff.COEFFS_SIZE)]
                strats.append(Strat("g%sr%d" % (game.name, rid), coeffs))
                rid += 1

    ret = None
    if best.has_solved(game.name):
        ret = best
        ret.name = "g%sbs" % game.name
        print("Solution found for game", game.name, ret.name, ret.get_stats([game.name]))
    return ret

def get_best_covering_strats(strats, games):
    ret = []

    remaining_games = set([g.name for g in games])
    remaining_strats = strats[:]
    while len(remaining_games) > 0 and len(remaining_strats) > 0:
        remaining_strats.sort(key=lambda x: x.get_stats(remaining_games))
        best = remaining_strats.pop()
        ret.append(best)

        for gn, res in best.played.items():
            if res[0]:
                remaining_games.discard(gn)

        nremaining_strats = []
        for s in remaining_strats:
            if s.get_stats(remaining_games)[0] > 0: # solve some remaining games
                nremaining_strats.append(s)
        remaining_strats = nremaining_strats

    return ret

# create games
games = []
for gid in range(GID, GID+NGAME_MAX):
    deck = model.DECK[:]
    randgen = random.Random(gid)
    randgen.shuffle(deck)
    games.append(Game(gid, model.FCBoard.init_from_deck(deck)))


# create 1st startegies
strategies = []
for i in range(NRANDOM_START):
    coeffs = [2*100*random.random()-100 for _ in range(solver.SolverCoeff.COEFFS_SIZE)]
    strategies.append(Strat("r%d" % i, coeffs))

# read the ones from file
try:
    print("Getting strats from", STRATS_FILE)
    with open(STRATS_FILE, "r") as f:
        i = 0
        for line in f.readlines():
            coeffs = [float(c) for c in line.replace('[', '').replace(']', '').split(',')]
            strategies.append(Strat("f%d"%i, coeffs))
            i += 1
except FileNotFoundError:
    print("File", STRATS_FILE, "doesn't exist, continue without known solvers")

unsolvable = set()
bests = []
ngame = NGAME
noimprove_count = 0
genid = 0
while noimprove_count < NOIMPROVMENT_STOP:
    print()
    print("--- Gen %d ---" % genid, "playing with %d strategies" % len(strategies))
    genid += 1

    games_unsolved = set([g.name for g in games[:ngame]])

    # Play games with all strategies
    for i, s in enumerate(strategies):
        print("Playing with", s.name, "%d/%d" % (i+1, len(strategies)))
        for g in games[:ngame]:
            s.solve(g)
            if s.has_solved(g.name):
                games_unsolved.discard(g.name)
                unsolvable.discard(g.name)
            elif len(bests) == 1:
                print("no need play other")
                break
    
    # all solved -> add new games
    while len(games_unsolved) == 0 and ngame < NGAME_MAX:
        new_game = games[ngame]
        ngame += 1
        print()
        print("All games solved, adding new game", new_game.name)

        games_unsolved.add(new_game.name)
        
        for s in strategies:
            print("Playing with", s.name)
            s.solve(new_game)
            if s.has_solved(new_game.name):
                 games_unsolved.discard(new_game.name)
    
    # find new coeffs for unsolved games
    while len(games_unsolved) > 0:
        
        gunsolved_name = games_unsolved.pop()

        # finding game object
        game_to_solve = None
        for g in games[:ngame]:
            if g.name == gunsolved_name:
                game_to_solve = g
                break
        
        # finding solution
        new_strat = solve_specific_game(game_to_solve)
        if new_strat is None: # no solution found
            unsolvable.add(game_to_solve)
            continue
        strategies.append(new_strat)
        games_unsolved.discard(game_to_solve.name)
        unsolvable.discard(game_to_solve.name)
        
        # make it plays all the games
        print("Play all current games with", new_strat.name)
        for g in games[:ngame]:
            new_strat.solve(g)
            if new_strat.has_solved(g.name):
                games_unsolved.discard(g.name)
                unsolvable.discard(g.name)
    
    old_bests = bests[:]
    # find best coverage
    bests = get_best_covering_strats(strategies, games[:ngame])

    print("Bests:")
    for b in bests:
        solvedl = []
        for g in games[:ngame]:
            if b.has_solved(g.name):
                solvedl.append(g.name)   
        print(b.name, b.get_stats([g.name for g in games]), "solved:", ",".join(solvedl))
    
    no_improvement = False
    if len(old_bests) > 0:
        no_improvement = len(old_bests) == len(bests) and \
                         all([bests[i].name == old_bests[i].name for i in range(len(bests))])
    if no_improvement:
        print("No improvements")
        noimprove_count += 1
    else:
        # save to file
        with open(STRATS_FILE, 'w') as f:
            for b in bests:
                f.write(str(b.coeffs) + "\n")
    old_bests = bests

    strategies = []
    if len(bests) > 1:
        # Create convergent
        convergent_coeffs = []
        bests_weights = [s.get_stats([g.name for g in games])[0] for s in bests]
        for i in range(solver.SolverCoeff.COEFFS_SIZE):
            sum_c = 0
            for j in range(len(bests)):
                sum_c += bests_weights[j]*bests[j].coeffs[i]
            convergent_coeffs.append(sum_c/float(sum(bests_weights)))
        convergent = Strat("c%d" % genid, convergent_coeffs)
        
        # Create kids 1/2 conv, 1/2 random
        for b in bests:
            strategies.append(b)
            for i in range(int(NKIDS/2)):
                strategies.append(Strat("%sc%d"%(b.name, i), b.make_converging_kid_coeffs(convergent_coeffs)))
            for i in range(int(NKIDS/2)):
                strategies.append(Strat("%sr%d"%(b.name, i), b.make_random_kid_coeffs()))
        
        strategies.append(convergent)
        for i in range(NKIDS):
            strategies.append(Strat("%sr%d"%(convergent.name, i), convergent.make_random_kid_coeffs()))
    
    else: # only one strats left, no need to converge
        strategies.append(bests[0])
        for i in range(NKIDS):
            strategies.append(Strat("%sr%d"%(b.name, i), b.make_random_kid_coeffs()))
            
    