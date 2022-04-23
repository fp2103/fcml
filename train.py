#!/usr/bin/python3
# -*- coding: utf-8 -*

import random
import multiprocessing as mp

import freecell as fc
import conf as p
from solvers import SolverCoeff


class SolverCoeffTrain(SolverCoeff):
    def __init__(self, name, coeffs):
        super().__init__(name, coeffs)

        # {gameid: (True/False, max_in_bases, len(moves), iter)}
        self.played_data = dict()

    def solve_w_stats(self, game):
        if game.name in self.played_data.keys():
            return self.played_data.get(game.name)
        else:
            r, mib, m, q = self.solve(game)
            self.played_data[game.name] = (r, mib, len(m), q)
            return (r, mib, len(m), q)
    
    def get_stats(self, games_id): # -> (win, in_base mean, -moves mean, -iter mean), [solved]
        win = 0
        mib_sum = 0
        m_sum = 0
        q_sum = 0
        solved = []
        for a in games_id:
            r, mib, m, q = self.played_data.get(str(a), (False, 0, 0, 0))
            mib_sum += mib
            if r:
                win += 1
                m_sum += m
                q_sum += q
                solved.append(a)
        stats = (win, mib_sum/len(games_id), -(m_sum/win) if win > 0 else 0, -(q_sum/win) if win > 0 else 0)
        return stats, solved
    
    def make_kids(self, nkids):
        print("Create", nkids, "kids for", self.name)
        ret = []
        for i in range(nkids):
            coeffs = [(c + random.gauss(0.0, p.KIDS_SIGMA)) for c in self.coeffs]
            ret.append(SolverCoeffTrain("%s:%d" % (self.name, i), coeffs))
        return ret

def solve_game_evol(game):
    print("Find Solver coeffs for game", game.name)

    new_solvers = []
    for r in range(p.NKIDS):
        ran_coeff = [2*p.COEFF_RANGE*random.random()-p.COEFF_RANGE for _ in range(SolverCoeff.PARAMS)]
        new_solvers.append(SolverCoeffTrain("%sr%d"%(game.name, r), ran_coeff))
    
    past_bests = []
    solvers_sorter = []
    l = 0
    solved_l = 0
    while r < p.MAX_SOLVERS:
        print("iter %d"%l)
        l += 1

        solvers_sorter = past_bests[:]
        for s in new_solvers:
            print("%s, %s"%(s.name, game.name), "...", end="", flush=True)
            ret, mib, m, q = s.solve_w_stats(fc.FCGame(game.name, game.fcboard.clone()))
            if ret:
                print(fc.TermColor.GREEN + "True" + fc.TermColor.ENDC, m, q)
            else:
                print(fc.TermColor.RED + "False" + fc.TermColor.ENDC, mib)
            solvers_sorter.append((s, (mib, -m, -q)))
        
        solvers_sorter.sort(key=lambda x: x[1], reverse=True)

        # Stop algo if no evolution or NLOOP iter
        b = solvers_sorter[0]
        bests = [b]
        solved = b[1][0] == 52
        if len(past_bests) > 0 and not solved and bests[0][1][0] == past_bests[0][1][0]:
            bests = [past_bests[0]]
        if len(past_bests) > 0 and solved and b[0].name == past_bests[0][0].name:
            print("No evolution on solved game")
            return b[0]
        solved_l += int(solved)
        if solved_l > p.NLOOP:
            print("Improved on %d iter" % p.NLOOP)
            return b[0]
    
        # Take NBEST bests when solved, 1 otherwise
        for b in solvers_sorter[1:p.NBEST]:
            if b[1][0] != 52:
                break
            bests.append(b)

        # Add randoms if unsolved
        new_solvers = []
        nk = p.NKIDS
        if not solved:
            nk = int(nk/2)
            print("Add", p.NKIDS, "randoms")
            for _ in range(p.NKIDS):
                r += 1
                ran_coeff = [2*p.COEFF_RANGE*random.random()-p.COEFF_RANGE for _ in range(SolverCoeff.PARAMS)]
                new_solvers.append(SolverCoeffTrain("%sr%d"%(game.name, r), ran_coeff))
        for b in bests:
            r += nk
            new_solvers.extend(b[0].make_kids(nk))
        past_bests = bests
    ret = None
    b = past_bests[0]
    if b[1][0] == 52:
        ret = b[0]
    return ret

def play_multiprocessed(que, solver, games_board):
    i = 0
    for gid, gb in games_board.items():
        ret, mib, m, q = solver.solve_w_stats(fc.FCGame(gid, gb.clone()))
        if ret:
            print("%s, %d/%d, %s"%(solver.name, i, len(games_board), str(gid)), "...", fc.TermColor.GREEN + "True" + fc.TermColor.ENDC, m, q)
        else:
            print("%s, %d/%d, %s"%(solver.name, i, len(games_board), str(gid)), "...", fc.TermColor.RED + "False" + fc.TermColor.ENDC, mib)
        que.put((gid, ret, mib, m, q))
        i += 1

def play_multiple_games(solver, games_board):
    print("Solve with", solver.name, "(%d games)"%len(games_board))

    # Separate games list
    gids = list(games_board.keys())
    random.shuffle(gids)
    gba = dict()
    gbb = dict()
    while len(gids) > 0:
        a = gids.pop()
        gba[a] = games_board.get(a)
        if len(gids) > 0:
            b = gids.pop()
            gbb[b] = games_board.get(b)
    
    # Solve in Process
    que = mp.Queue()
    p1 = mp.Process(target=play_multiprocessed, args=(que, solver, gba))
    p2 = mp.Process(target=play_multiprocessed, args=(que, solver, gbb))
    p1.start()
    p2.start()
    for _ in range(len(games_board)):
        g = que.get()
        solver.played_data[str(g[0])] = (g[1], g[2], g[3], g[4])
    p1.join()
    p2.join()

    stats, solved = solver.get_stats(games_board.keys())
    print("Win:", stats[0], "in_bases mean:", stats[1], "moves mean:", -stats[2], "iter mean:", -stats[3])
    return solved

def sort_single_solvers(solvers, games_id):
    solvers_w_stats = []
    for s in solvers:
        stat, _ = s.get_stats(games_id)
        solvers_w_stats.append((s, stat))
    solvers_w_stats.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in solvers_w_stats]

def sort_solvers(solvers, games_id):
    """
    Find best solvers association
    """
    max_starts = min(len(solvers), p.MAX_STRATEGIES)
    print("Best %d solvers:" % max_starts)

    solvers_associations = [] # [solvers], stats, unsolved
    cursors = list(range(max_starts))
    endcursors = False
    while not endcursors:
        ss = []
        for c in cursors:
            ss.append(solvers[c])

        gids = set(games_id)
        winsum = 0
        inbasesum = 0
        movessum = 0
        itersum = 0
        for s in ss:
            stat, solved = s.get_stats(games_id)
            winsum += stat[0]
            inbasesum += stat[1]*len(games_id)
            movessum += -stat[2]*stat[0]
            itersum += -stat[3]*stat[0]
            for g in solved:
                gids.discard(g)
        stats = (len(games_id)-len(gids), inbasesum/(max_starts*len(games_id)), 
                    -movessum/winsum if winsum > 0 else 0, -itersum/winsum if winsum > 0 else 0)
        solvers_associations.append((ss, stats, gids))
        
        endcursors = True
        for i in range(max_starts-1, -1, -1):
            if cursors[i] < len(solvers)-(max_starts-i):
                cursors[i] += 1
                for j in range(i+1, max_starts):
                    cursors[j] = cursors[j-1]+1
                endcursors = False
                break
    solvers_associations.sort(key=lambda x: x[1], reverse=True)

    best_association = solvers_associations[0]
    ret = sort_single_solvers(best_association[0], games_id)
    for s in ret:
        st, _ = s.get_stats(games_id)
        print(s.name, st)
    print("Bests total win:", best_association[1][0], "doesn't solve:", str(best_association[2]))

    with open(p.DBFILE, 'w+') as f:
        for s in ret:
            f.write(str(s.coeffs) + "\n")
    print("Saved!")

    return ret

def train(known_strategies, loop, games_id, nkids):
    # Create games
    print()
    print("Create", len(games_id), "games")
    games_init_board = {}
    for gid in games_id:
        deck = fc.DECK[:]
        randgen = random.Random(gid)
        randgen.shuffle(deck)
        games_init_board[gid] = fc.FCBoard.init_from_deck(deck)

    # Loop
    unsolved_games = set(games_id)
    solvers = [SolverCoeffTrain(s.name, s.coeffs) for s in known_strategies]
    print()
    # iteration 0: play all games and find unsolved ones
    print("Iteration: 0/%d" % (max(0, loop-1)))
    for s in solvers:
        solved = play_multiple_games(s, games_init_board)
        for gid in solved:
            unsolved_games.discard(gid)

    sort_solvers(solvers, games_id)
    if loop <= 0:
        return
    
    # solve unsolved
    while len(unsolved_games) > 0:
        print(len(unsolved_games), "still unsolved", str(unsolved_games))
        g = unsolved_games.pop()
        print()
        s_found = solve_game_evol(fc.FCGame(g, games_init_board.get(g).clone()))
        if s_found is None:
            print("Solver not found for", g)
        else:
            print("Solver for game", g, "found, save it then make it play all other games")
            solvers.append(s_found)
            with open(p.DBFILE, 'a+') as f:
                f.write(str(s_found.coeffs) + "\n")
            solved = play_multiple_games(s_found, games_init_board)
            for g2 in solved:
                unsolved_games.discard(g2)

    solvers_diverse = sort_solvers(solvers, games_id)

    # iteration n:
    for l in range(1, loop):
        print()
        print()
        print("Iteration: %d/%d" % (l, loop-1))
        new_solvers = []
        for s in solvers_diverse:
            new_solvers.extend(s.make_kids(nkids))
        
        ni = 0
        for n in new_solvers:
            print()
            print("%d/%d"%(ni, len(new_solvers)))
            ni += 1
            play_multiple_games(n, games_init_board)
        
        solvers_diverse = sort_solvers(solvers_diverse+new_solvers, games_id)
