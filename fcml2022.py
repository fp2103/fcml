#!/usr/bin/python3
# -*- coding: utf-8 -*

"""
Solve Freecell with tree search and evolutionary algorithm on best solvers
"""

import sys
import random
import freecell as fc

MAX_ITER = 2000
PARAMS = 14
DBFILE = "solvers.db"
KIDS_SIGMA = 2.0

MAX_SOLVERS = 1000
NKIDS = 10

def vector_multiply(v1, v2):
    ret = 0
    for i in range(min(len(v1), len(v2))):
        ret += v1[i]*v2[i]
    return ret

class Solver(object):
    def __init__(self, name, coeffs):
        self.name = name
        self.coeffs = coeffs

        self.played_data = dict()
    
    def _weight_state(self, len_bases, game, all_choices):
        in_bases = sum(len_bases) / 52.0
        gap_bases = (min(len_bases) - max(len_bases)) / 13.0
        in_serie = sum([len(game._column_series[i]) for i in range(fc.COLUMN)]) / (52.0 - sum(len_bases))
        mvt_max = min(game._get_mvt_max()[0] / 13.0, 1.0)
        choices_coeff = min(len(all_choices) / 30.0, 1.0)

        v = (in_bases, gap_bases, in_serie, mvt_max, choices_coeff)
        v2 = (52, 7, 52, 13, 30)
        return vector_multiply(v, self.coeffs[0:5]), v
        #return vector_multiply(v, v2), v
        
    def _hash_choice(self, choice, fcboard):
        ret = ",".join([c.name for c in choice.cards]) + ":"
        col_orig_str = choice.col_orig
        if choice.col_orig != fc.COL_FC:
            col_orig_str = ",".join([c.name for c in fcboard.columns[choice.col_orig][:-len(choice.cards)]])
        col_dest_str = choice.col_dest
        if choice.col_dest != fc.COL_BASE and choice.col_dest != fc.COL_FC:
            col_dest_str = ",".join([c.name for c in fcboard.columns[choice.col_dest]])
        ret += "-".join(sorted([col_orig_str, col_dest_str]))
        return ret

    def _weight_choice(self, choice, game, in_serie, mvt_max):
        to_base = choice.col_dest == fc.COL_BASE
        to_base_p = to_base * 300 * (in_serie**5)
        to_fc = choice.col_dest == fc.COL_BASE
        to_fc_p = to_fc * mvt_max
        to_serie = choice.col_dest != fc.COL_BASE and choice.col_dest != fc.COL_FC and len(game._column_series[choice.col_dest]) > 0
        to_emptycol = choice.col_dest != fc.COL_BASE and choice.col_dest != fc.COL_FC and len(game._column_series[choice.col_dest]) == 0

        from_fc = choice.col_orig == fc.COL_FC
        split_serie = choice.col_orig != fc.COL_FC and len(game._column_series[choice.col_orig]) > len(choice.cards)
        empty_col = choice.col_orig != fc.COL_FC and len(game.fcboard.columns[choice.col_orig]) == len(choice.cards)

        discover_base = False
        if not from_fc and not empty_col:
            next_c = game.fcboard.columns[choice.col_orig][-(len(choice.cards)+1)]
            discover_base = next_c.num == len(game.fcboard.bases.get(next_c.suit))+1

        v = (to_base, to_fc, to_fc_p, to_serie, to_emptycol, from_fc, split_serie, empty_col, discover_base)
        w = vector_multiply(v, self.coeffs[5:]) + to_base_p
        return w
    
    def solve(self, game): # -> (True/False, max_in_bases, moves, iter)
        ngame = game
        # Return to last best weigthed state 
        # (board, n moves, list of moves done on that state, last best weight)
        best_states = []
        last_best_weight = -10000
        state_moves_done = []    

        moves = []
        moves_hash = []
        max_in_base = 0
        global_iter = 0
        while global_iter < MAX_ITER:
            global_iter += 1

            # Verifiy won
            len_bases = [len(ngame.fcboard.bases.get(k)) for k in fc.SUITS]
            if sum(len_bases) == 52:
                return (True, 52, moves, global_iter)
            max_in_base = max(sum(len_bases), max_in_base)

            all_choices = ngame.list_choices()
            state_weight, swv = self._weight_state(len_bases, ngame, all_choices)

            # list & sort choices
            # (choice, hash, weight)
            choices_weighted = []
            for c in all_choices:
                chash = self._hash_choice(c, ngame.fcboard)
                if chash in moves_hash or chash in state_moves_done:
                    continue

                cweight = self._weight_choice(c, ngame, swv[2], swv[3])
                #cweight = random.randint(0, 100)
                choices_weighted.append((c, chash, cweight))
            choices_weighted.sort(key=lambda x: x[2], reverse=True)

            # go to next state
            if len(choices_weighted) > 0:
                c = choices_weighted[0][0]
                ch = choices_weighted[0][1]

                # Save current if best
                state_moves_done.append(ch)
                if state_weight >= last_best_weight:
                    best_states.append((ngame.fcboard.clone(), len(moves), state_moves_done, last_best_weight))
                    last_best_weight = state_weight
                state_moves_done = []

                moves.append(c)
                moves_hash.append(ch)
                ngame.apply(c)
            else:
                # return to last best state
                if len(best_states) > 0:
                    board, last_move_id, state_moves_done, last_best_weight = best_states.pop()
                    ngame = fc.FCGame(ngame.name, board)
                    moves = moves[:last_move_id]
                    moves_hash = moves_hash[:last_move_id]
                else:
                    break
        
        return (False, max_in_base, [], global_iter)
    
    # ---- Training methods ----
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
            coeffs = [(c + random.gauss(0.0, KIDS_SIGMA)) for c in self.coeffs]
            ret.append(Solver("%s:%d" % (self.name, i), coeffs))
        return ret

        
# ----- Program functions -----
def get_strategies():
    ret = []
    print("Getting best known solvers from", DBFILE)
    with open(DBFILE, "r") as f:
        i = 0
        for line in f.readlines():
            coeffs = [float(c) for c in line.replace('[', '').replace(']', '').split(',')]
            ret.append(Solver("f%d"%i, coeffs))
            i += 1
    print(len(ret), "solvers retreived")
    return ret

def solve_game(game):
    pass

def solve_game_evol(game):
    print("Find solver for game", game.name)

    new_solvers = []
    for r in range(NKIDS):
        new_solvers.append(Solver("%sr%d"%(game.name, r), [200*random.random()-100 for _ in range(PARAMS)]))
    
    past_bests = []
    solvers_sorter = []
    l = 0
    solved_l = 0
    while r < MAX_SOLVERS:
        print("iter %d"%l)
        l += 1

        solvers_sorter = past_bests[:]
        for s in new_solvers:
            print(s.name, "...", end="", flush=True)
            ret, mib, m, q = s.solve_w_stats(fc.FCGame(game.name, game.fcboard.clone()))
            if ret:
                print(fc.TermColor.GREEN + "True" + fc.TermColor.ENDC, m, q)
            else:
                print(fc.TermColor.RED + "False" + fc.TermColor.ENDC, mib)
            solvers_sorter.append((s, (mib, -m, -q)))
        
        solvers_sorter.sort(key=lambda x: x[1], reverse=True)

        # Stop algo if no evolution or 3 iter
        b = solvers_sorter[0]
        bests = [b]
        solved = b[1][0] == 52
        if len(past_bests) > 0 and not solved and bests[0][1][0] == past_bests[0][1][0]:
            bests = [past_bests[0]]
        if len(past_bests) > 0 and solved and b[0].name == past_bests[0][0].name:
            print("No evolution on solved game")
            return b[0]
        solved_l += int(solved)
        if solved_l > 3:
            print("Improved on 3 iter")
            return b[0]
    
        # Take 3 bests when >3 solved, 1 otherwise
        for b in solvers_sorter[1:3]:
            if b[1][0] != 52:
                break
            bests.append(b)

        # Add randoms if unsolved
        new_solvers = []
        nk = NKIDS
        if not solved:
            nk = int(nk/2)
            print("Add", NKIDS, "randoms")
            for _ in range(NKIDS):
                r += 1
                new_solvers.append(Solver("%sr%d"%(game.name, r), [200*random.random()-100 for _ in range(PARAMS)]))
        for b in bests:
            r += nk
            new_solvers.extend(b[0].make_kids(nk))
        past_bests = bests
    ret = None
    b = past_bests[0]
    if b[1][0] == 52:
        ret = b[0]
    return ret

def play_multiple_games(solver, games_board):
    print("Solve with", solver.name)
    for gid, gb in games_board.items():
        print(gid, "...", end="", flush=True)
        ret, mib, m, q = solver.solve_w_stats(fc.FCGame(gid, gb.clone()))
        if ret:
            print(fc.TermColor.GREEN + "True" + fc.TermColor.ENDC, m, q)
        else:
            print(fc.TermColor.RED + "False" + fc.TermColor.ENDC, mib)
    stats, solved = solver.get_stats(games_board.keys())
    print("Win:", stats[0], "in_bases mean:", stats[1], "moves mean:", -stats[2], "iter mean:", -stats[3])
    return solved

def sort_solvers(solvers, games_id, unsolvables):
    print("Best solvers:")

    solvers_diverse = []
    solvers_remaining = solvers[:]
    all_gids = set(games_id)
    for u in unsolvables:
        all_gids.remove(u)
    while len(all_gids) > 0 and len(solvers_remaining) > 0:
        # compute stats on games
        solvers_sorter = []
        for s in solvers_remaining:
            stats, solved = s.get_stats(all_gids)
            solvers_sorter.append((s, stats, solved))
        solvers_sorter.sort(key=lambda x: x[1], reverse=True)

        best = solvers_sorter[0][0]
        print(best.name, solvers_sorter[0][2])
        for b in solvers_sorter[0][2]:
            all_gids.remove(b)

        solvers_diverse.append(best)
        nsolvers_remaining = []
        for s in solvers_remaining:
            if s.name != best.name:
                nsolvers_remaining.append(s)
        solvers_remaining = nsolvers_remaining

    with open(DBFILE, 'w+') as f:
        for s in solvers_diverse:
            f.write(str(s.coeffs) + "\n")
        print("Saved!")

    return solvers_diverse

def train(loop, games_id, nkids):
    known_strategies = []
    try:
        known_strategies = get_strategies()
    except FileNotFoundError:
        print("File", DBFILE, "doesn't exist, continue without known solvers")
    
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
    unsolvable_games = set()
    solvers = known_strategies
    print()
    print("Iteration: 0/%d" % (loop-1))
    for s in solvers:
        solved = play_multiple_games(s, games_init_board)
        for gid in solved:
            unsolved_games.discard(gid)
    
    while len(unsolved_games) > 0:
        g = unsolved_games.pop()
        print()
        s_found = solve_game_evol(fc.FCGame(g, games_init_board.get(g).clone()))
        if s_found is None:
            print("Game", g, "seems unsolvable")
            unsolvable_games.add(g)
        else:
            print("Solver for game", g, "found, save it then make it play other games")
            solvers.append(s_found)
            with open(DBFILE, 'a+') as f:
                f.write(str(s_found.coeffs) + "\n")
            solved = play_multiple_games(s_found, games_init_board)
            for g2 in solved:
                unsolved_games.discard(g2)
                unsolvable_games.discard(g2)

    print("Games still unsolved:", unsolvable_games)
    solvers_diverse = sort_solvers(solvers, games_id, unsolvable_games)

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
            solved = play_multiple_games(n, games_init_board)
            for g2 in solved:
                unsolvable_games.discard(g2)
        
        print("Games still unsolved:", unsolvable_games)
        solvers_diverse = sort_solvers(solvers_diverse+new_solvers, games_id, unsolvable_games)

    
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

        train(loop, games_id, nkids)

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
        
        #solve_game(game)
        a = solve_game_evol(game)
        print(a.played_data)

    else:
        print(usage)
        exit(1)
    
    exit(0)

# 353,425