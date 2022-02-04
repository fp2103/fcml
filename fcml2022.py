#!/usr/bin/python3
# -*- coding: utf-8 -*

"""
Solve Freecell with tree search and evolutionary algorithm on best solvers
"""

import sys
import random
import freecell as fc


MAX_ITER = 2000
MAX_MOVES = 500
MAX_MOVES_WO_PROGRESS = 100

PARAMS = 15

DBFILE = "solvers.db"
#KIDS_SIGMA = 2

def vector_multiply(v1, v2):
    ret = 0
    for i in range(min(len(v1), len(v2))):
        ret += v1[i]*v2[i]
    return ret

class Solver(object):
    def __init__(self, coeffs):
        self.coeffs = coeffs
    
    def _weight_state(self, len_bases, game, all_choices):
        in_bases = sum(len_bases) / 52.0
        gap_bases = (min(len_bases) - max(len_bases)) / 13.0
        in_serie = sum([len(game._column_series[i]) for i in range(fc.COLUMN)]) / (52.0 - sum(len_bases))
        mvt_max = min(game._get_mvt_max()[0] / 13.0, 1.0)
        choices_coeff = min(len(all_choices) / 30.0, 1.0)

        v = (in_bases, gap_bases, in_serie, mvt_max, choices_coeff)
        return vector_multiply(v, self.coeffs[0:5]), v
        
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
        to_fc = choice.col_dest == fc.COL_BASE
        to_serie = choice.col_dest != fc.COL_BASE and choice.col_dest != fc.COL_FC and len(game._column_series[choice.col_dest]) > 0
        to_emptycol = choice.col_dest != fc.COL_BASE and choice.col_dest != fc.COL_FC and len(game._column_series[choice.col_dest]) == 0

        from_fc = choice.col_orig == fc.COL_FC
        split_serie = choice.col_orig != fc.COL_FC and len(game._column_series[choice.col_orig]) > len(choice.cards)
        empty_col = choice.col_orig != fc.COL_FC and len(game.fcboard.columns[choice.col_orig]) == len(choice.cards)

        discover_base = False
        if not from_fc and not empty_col:
            next_c = game.fcboard.columns[choice.col_orig][-(len(choice.cards)+1)]
            discover_base = next_c.num == len(game.fcboard.bases.get(next_c.suit))+1

        v = (to_base, to_fc, to_serie, to_emptycol, from_fc, split_serie, empty_col, discover_base)
        return vector_multiply(v, self.coeffs[5:])

    def solve(self, game):
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
            #print(global_iter)
            #print(ngame.fcboard)
            #input()

            global_iter += 1

            # Verifiy won
            len_bases = [len(ngame.fcboard.bases.get(k)) for k in fc.SUITS]
            if sum(len_bases) == 52:
                return (True, moves, global_iter)
            max_in_base = max(sum(len_bases), max_in_base)

            all_choices = ngame.list_choices()
            state_weight, swv = self._weight_state(len_bases, ngame, all_choices)
            #print(state_weight)

            # list & sort choices
            # (choice, hash, weight)
            choices_weighted = []
            for c in all_choices:
                chash = self._hash_choice(c, ngame.fcboard)
                if chash in moves_hash or chash in state_moves_done:
                    continue

                cweight = self._weight_choice(c, ngame, swv[2], swv[3])
                choices_weighted.append((c, chash, cweight))
            choices_weighted.sort(key=lambda x: x[2], reverse=True)

            # go to next state
            if len(choices_weighted) > 0:
                c = choices_weighted[0][0]
                ch = choices_weighted[0][1]
                #print("MOVE:", c)

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
                    #print("JUMP BACK!")
                    board, last_move_id, state_moves_done, last_best_weight = best_states.pop()
                    ngame = fc.FCGame("", board)
                    moves = moves[:last_move_id]
                    moves_hash = moves_hash[:last_move_id]
                else:
                    break
        
        return (False, max_in_base, None)
            
    def make_kids(self, nkids):
        pass

        
# ----- Program functions -----
def get_strategies():
    ret = []
    print("Getting best known solvers from", DBFILE)
    with open(DBFILE, "r") as f:
        i = 0
        for line in f.readlines():
            ret.append(Solver.from_string("f%d"%i, line))
            i += 1
    print(len(ret), "solvers retreived")
    return ret

def solve_game(game):
    solvers = []
    for _ in range(99):
        r = []
        for _ in range(PARAMS):
            r.append(200*random.random()-100)
        solvers.append(r)

    for s in solvers:
        ngame = fc.FCGame("", game.fcboard.clone())
        #print(s)
        solver = Solver(s)
        res, m, b = solver.solve(ngame)
        if res:
            print(True, len(m), b)
            #for a in m:
            #    print(a)
        else:
            print(False, m)

def train(loop, games_id, nrandom, nkids):
    known_strategies = []
    try:
        known_strategies = get_strategies()
    except FileNotFoundError:
        print("File", DBFILE, "doesn't exist, continue without known solvers")
    
    # Create games
    print()
    print("Create", len(games_id), "games")
    games_init_state = {}
    for gid in games_id:
        deck = SORTED_DECK[:]
        randgen = random.Random(gid)
        randgen.shuffle(deck)
        games_init_state[gid] = fc.FreecellState.init_from_deck(deck)

    # Loop
    best_solvers = known_strategies
    nnrandom = nrandom
    for liter in range(loop):
        print()
        print("Iterartion:", liter+1, "/", loop)

        print("Creating new solvers:")
        solvers = []

        print(nnrandom, "random solvers")
        for i in range(nnrandom):
            r = []
            for _ in range((PRIMARY_PARAMS+1)*PARAMS):
                r.append(random.random()*100)
            solvers.append(Solver("r%d"%i, r))

        i = 0
        for nk in nkids:
            if i < len(best_solvers):
                print(nk, "kids", "(including itself)" if liter==0 else "", "for solver", best_solvers[i].name)
                solvers.extend(best_solvers[i].make_kids(nk, liter==0))
            else:
                break
            i += 1
   
        # Make them play games
        for s in solvers:
            print()
            print("Solver", s.name)
            for gid, init_state in games_init_state.items():
                print("Game", gid, end=", ")
                s.solve(init_state)
            print(s)

        # Save best & update strategies
        print()
        if liter > 0: #past best already included in 1st iteration
            solvers.extend(best_solvers)
        best_solvers = sorted(solvers, reverse=True)
        print("Best solver this round was", best_solvers[0])

        nnrandom = int(nnrandom/2)

    with open(DBFILE, 'a+') as f:
        f.write(str(best_solvers[0].strategy_coeffs) + "\n")
    print("Best solver added to database!")

# ------ Main Solver script --------    
if __name__ == "__main__":

    usage = "./fcml2022.py solve <game file>\n" + \
            "              train <loop> <games_range> <nrandom> [nkidbest1 nkidbest2...]\n" + \
            "games_range: 1-100 or 1,2,3 or 1-10,20,30-32" + \
            "nrandom gets cut in half at each loop iteration"

    if len(sys.argv) < 2:
        print(usage)
        exit(1)

    # Training mode
    if sys.argv[1] == "train":
        print("TODO")
        exit(1)
        if len(sys.argv) < 5:
            print(usage)
            exit(1)

        # Read parameters
        loop = 0
        games_id = set()
        nrandom = 0
        nkids = []
        try:
            # loop
            loop = int(sys.argv[2])

            # games range
            for gr in sys.argv[3].split(','):
                r = gr.split('-')
                sg = int(r[0])
                eg = int(r[1])+1 if len(r) > 1 else sg+1
                for i in range(sg, eg):
                    games_id.add(i)

            # n random
            nrandom = int(sys.argv[4])

            # n kids best
            for a in sys.argv[5:]:
                nkids.append(int(a))
            
        except ValueError as v:
            print(v)
            print(usage)
            exit(1)

        train(loop, games_id, nrandom, nkids)

    # Solving mode
    elif sys.argv[1] == "solve":
        if len(sys.argv) < 3:
            print(usage)
            exit(1)

        filename = sys.argv[2]
        try:
            game = fc.FCGame("lala", fc.FCBoard.init_from_file(filename))
        except:
            print("Please give a valid game file")
            exit(1)
        
        solve_game(game)

    else:
        print(usage)
        exit(1)
    
    exit(0)
