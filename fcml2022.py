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
PARAMS = 6
PRIMARY_PARAMS = 4
WINNING_STATE = (1.0, 0.0, 1.0, 1.0, 0.0, 0.0)
ZERO_STATE = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
MIN_WEIGHT = -10000
MAX_WEIGHT = 10000
SORTED_DECK = [fc.Card(j, i) for j in fc.SUITS for i in range(1, len(fc.CARD_VALUE)+1)]
DBFILE = "solvers.db"
KIDS_SIGMA = 3

class StateData(object):
    """ Struct-like object to store state + weight data """
    def __init__(self, state, weight, choice, choice_hash, weight_vector):
        self.state = state
        self.weight = weight
        self.choice = choice
        self.choice_hash = choice_hash
        self.weight_vector = weight_vector

class SolverStats(object):
    """ Struct-like object to store Solver stats """
    def __init__(self, nplayed, in_base_mean, nsuccess, move_mean, iter_mean):
        self.nplayed = nplayed
        self.in_base_mean = in_base_mean
        self.nsuccess = nsuccess
        self.move_mean = move_mean
        self.iter_mean = iter_mean
    
    @classmethod
    def zeros(cls):
        return cls(0, 0.0, 0, 0.0, 0.0)
    
    def __str__(self):
        success_rate = self.nsuccess / self.nplayed if self.nplayed > 0 else 0.0
        return "played: %d, in_base_mean: %f, success: %d (%f), move_mean: %f, iter_mean: %f" \
                % (self.nplayed, self.in_base_mean, self.nsuccess, success_rate, self.move_mean, self.iter_mean)
    
    def __eq__(self, other):
        return self.nplayed == other.nplayed and \
               self.in_base_mean == other.in_base_mean and \
               self.nsuccess == other.nsuccess and \
               self.move_mean == other.move_mean and \
               self.iter_mean == other.iter_mean

    def __lt__(self, other):
        success_rate = self.nsuccess / self.nplayed if self.nplayed > 0 else 0.0
        other_success_rate = other.nsuccess / other.nplayed if other.nplayed > 0 else 0.0
        return self.in_base_mean < other.in_base_mean or \
               (self.in_base_mean == other.in_base_mean and success_rate < other_success_rate) or \
               (self.in_base_mean == other.in_base_mean and success_rate == other_success_rate and self.move_mean > other.move_mean) or \
               (self.in_base_mean == other.in_base_mean and success_rate == other_success_rate and self.move_mean == other.move_mean and \
                   self.iter_mean > other.iter_mean) or \
               (self.in_base_mean == other.in_base_mean and success_rate == other_success_rate and self.move_mean == other.move_mean and \
                   self.iter_mean == other.iter_mean and self.nplayed < other.nplayed)

class Solver(object):
    def __init__(self, name, coeffs):
        self.name = name
        self.strategy_coeffs = coeffs
        self.stats = SolverStats.zeros()

        # Recurse var
        self._iter = 0
        self._max_in_bases = 0
        self._path = []
        self._path_hash = set()
    
    @classmethod
    def from_string(cls, name, s):
        coeffs_str = s.replace('[', '').replace(']', '')
        coeffs = []
        for c in coeffs_str.split(','):
            coeffs.append(float(c))
        assert len(coeffs) == (PRIMARY_PARAMS+1)*PARAMS, "len(coeffs) is wrong"
        return cls(name, coeffs)
    
    def __str__(self):
        return self.name + ", " + str(self.stats)

    # ------ Static data compute helpers ------
    @staticmethod
    def hash_choice(choice, state):
        ret = ",".join([str(c.uid) for c in choice.cards]) + ":"
        col_orig_str = choice.col_orig
        if choice.col_orig != fc.COL_FC:
            col_orig_str = ",".join([str(c.uid) for c in state.columns[choice.col_orig][:-len(choice.cards)]])
        col_dest_str = choice.col_dest
        if choice.col_dest != fc.COL_BASE and choice.col_dest != fc.COL_FC:
            col_dest_str = ",".join([str(c.uid) for c in state.columns[choice.col_dest]])
        ret += "-".join(sorted([col_orig_str, col_dest_str]))
        return ret
    
    @staticmethod
    def compute_state_weight(state):
        """ # primary measures:
            .in base/52
            .gap between bases
            .in serie/remaining
            .max_mvt/13 (max 1)
            # secondary measures:
            .to base/choices
            .from fc/choices
        """
        if state.is_won:
            return WINNING_STATE

        in_base_norm = state.in_base / 52.0

        # negative value, as high value = bad
        gap_bases = (min(state.bases_len) - max(state.bases_len)) / 13.0

        in_serie = sum([len(state.column_series[i]) for i in range(0, fc.COLUMN)]) / (52.0 - state.in_base)

        mvt = min(state.max_mvt / 13.0, 1.0)

        choices = state.compute_choices()
        to_base = 0.0
        from_fc = 0.0
        for c in choices:
            if c.col_dest == fc.COL_BASE:
                to_base += 1.0
            if c.col_orig == fc.COL_FC:
                from_fc += 1.0
        if len(choices) > 0:
            to_base = to_base / len(choices)
            from_fc = from_fc / len(choices)

        return (in_base_norm, gap_bases, in_serie, mvt, to_base, from_fc)

    # ---- Main methods ----        
    def solve(self, init_state):
        # reset
        self._iter = 0
        self._max_in_bases = 0
        self._path = []
        self._path_hash = set()
        self._moves_wo_progress = 0

        # Play
        print(self.name, "playing...", end="", flush=True)
        swv = Solver.compute_state_weight(init_state)
        sw = self._weight_state(swv, ZERO_STATE)
        ret = False
        try:
            ret = self._play(StateData(init_state, sw, None, "", swv), MIN_WEIGHT)
        except RecursionError:
            pass
        
        # Update stats
        in_base_mean_sum = self.stats.in_base_mean*self.stats.nplayed
        move_mean_sum = self.stats.move_mean*self.stats.nsuccess
        iter_mean_sum = self.stats.iter_mean*self.stats.nsuccess
        self.stats.nplayed += 1
        self.stats.in_base_mean = (in_base_mean_sum + self._max_in_bases) / self.stats.nplayed
        if ret:
            print(fc.TermColor.GREEN + "true" + fc.TermColor.ENDC, len(self._path), self._iter)
            self.stats.nsuccess += 1
            self.stats.move_mean = (move_mean_sum + len(self._path)) / self.stats.nsuccess
            self.stats.iter_mean = (iter_mean_sum + self._iter) / self.stats.nsuccess
        else:
            print(fc.TermColor.RED + "false" + fc.TermColor.ENDC, self._max_in_bases, self._iter)

        return self._path
    
    # --- Recurse methods ---
    def _weight_state(self, weight_vector, curr_state_wv):
        """ curr_state -> coeff
            coeff*weight_vector -> weight
        """
        # Won
        if weight_vector == WINNING_STATE:
            return MAX_WEIGHT

        # Compute coeffs
        coeffs = []
        for i in range(PARAMS):
            c = 0
            for j in range(PRIMARY_PARAMS):
                c += self.strategy_coeffs[(i*PRIMARY_PARAMS+1)+j]*curr_state_wv[j]
            # add constant
            c += self.strategy_coeffs[(i*PRIMARY_PARAMS+1)+PRIMARY_PARAMS]
            coeffs.append(c)

        # Compute weight
        ret = 0
        for i in range(PARAMS):
            ret += weight_vector[i]*coeffs[i]
        return ret

    def _play(self, state_data, best_weight):
        #print(self._iter, len(self._path), state_data.state.in_base, move_wo_progress)
        self._iter += 1
        if self._iter > MAX_ITER or len(self._path) > MAX_MOVES:
            raise RecursionError()
        
        self._max_in_bases = max(state_data.state.in_base, self._max_in_bases)

        self._path.append(state_data.choice)
        self._path_hash.add(state_data.choice_hash)

        if state_data.state.is_won:
            return True
        
        # keep knowledge of best visited state
        not_better = state_data.weight < best_weight
        nbw = max(state_data.weight, best_weight)
        
        # Compute & sort list of next accessible state
        next_states_data = []
        for c in state_data.state.compute_choices():
            # skip choice that we already did/revert past ones
            hc = Solver.hash_choice(c, state_data.state)
            if hc in self._path_hash:
                continue
          
            ns = state_data.state.apply(c)
            swv = Solver.compute_state_weight(ns)
            sw = self._weight_state(swv, state_data.weight_vector)
            next_states_data.append(StateData(ns, sw, c, hc, swv))
        next_states_data.sort(key=lambda x: x.weight, reverse=True)

        # recurse on next states, stop when won or if state is not best
        ret = False
        for nsd in next_states_data:
            ret = self._play(nsd, nbw)
            if ret or not_better:
                break

        if not ret:
            self._path.pop()
            self._path_hash.remove(state_data.choice_hash)
        return ret
    
    # ---- Evolution algo methods ----
    def make_kids(self, nk, include_itself):
        # return nk kids 
        ret = []
        if nk > 0:
            mk = nk
            if include_itself:
                ret = [self]
                mk -= 1

            for i in range(mk):
                ncoeffs = []
                for c in self.strategy_coeffs:
                    nc = c + random.gauss(0, KIDS_SIGMA)
                    nc = max(0, nc)
                    nc = min(100,nc)
                    ncoeffs.append(nc)
                ret.append(Solver(self.name + ":%d"%i, ncoeffs))
        return ret
    
    def __eq__(self, other):
        return self.stats.__eq__(other.stats)

    def __lt__(self, other):
        return self.stats.__lt__(other.stats)
        
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
    # TODO
    
    for s in solvers:
        print(s)
        solver = Solver(game.state, s)
        res = solver.solve()
        if len(res) > 0:
            for c in res:
                print(c)
            break

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
            game = fc.FreecellGame.from_file(filename)
        except:
            print("Please give a valid game file")
            exit(1)
        
        solve_game(game)

    else:
        print(usage)
        exit(1)
    
    exit(0)
