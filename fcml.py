#!/usr/bin/python3
# -*- coding: utf-8 -*

"""
Using evolutionary algorithm to find a solution to Freecell games
Keep a clean list of all players that are knonw to solve some freecell game
"""

import random
import json
import sys

from freecell import Card, Choice, FreecellGame, TermColor, \
                     FREECELL, COLUMN, CARD_VALUE, RED, BLACK, SUITS, COL_BASE, COL_FC, \
                     load_game                         
from mlevol import MLEvolObject, MLEvolAlgo, NeuralNetwork

DBFILE = "kplayers.json"
NKIDS = 20
NKIDS_IMPROVE = 10
MAX_GEN = 20

AUTOTRAIN = 100
AUTOTRAIN_MAX = 100

ITER_MAX = 2000
PARAMS = 14

AUTO_BASE_WEIGHT = 10**10
MAX_ITER_DEPTH = 500
CIH_WON = len(CARD_VALUE) * len(SUITS)
SCORE_WON = CIH_WON*2

MY_PLAYER = [1, 0, 2, 0.25, 0.5, 3, -0.5, 5, -0.5, -1, -0.25, -1, 0, 1]

class ChoiceParametrized(Choice):
    def __init__(self, parent, game):
        super().__init__(parent.cards, parent.col_orig, parent.col_dest)

        self.col_orig_copy = self.col_orig
        self.col_dest_copy = self.col_dest
        if self.col_orig in range(0, COLUMN):
            self.col_orig_copy = game.column[self.col_orig][:]
        if self.col_dest in range(0, COLUMN):
            self.col_dest_copy = game.column[self.col_dest][:]

    def equals(self, other, check_col_num=False):
        equal = self.cards == other.cards and \
                self.col_orig_copy == other.col_orig_copy and \
                self.col_dest_copy == other.col_dest_copy
        if check_col_num:
            equal = equal and self.col_dest == other.col_dest and \
                    self.col_orig == other.col_orig
        return equal

    def get_opposite(self, game):
        # Apply change and create the opposite choice from this new game state
        game.apply(self)
        o = Choice(self.cards, self.col_dest, self.col_orig)
        op = ChoiceParametrized(o, game)
        game.reverse_apply(self)
        return op

    def list_possibilities(self, game, from_col_id, cid, include_dest=True):
        """ For a card from a column (cid in from_col_id) list:
                * destination (other col or base) available for this card
                * or if it can be the head of a serie from another col (and len of this serie)
        """
        c = game.column[from_col_id][cid]

        avail_dest = []
        if include_dest:
            # To base
            cb = game.base.get(c.suit)
            if c.num - len(cb) == 1:
                avail_dest.append(COL_BASE)

            # To a non empty col
            for col_id in range(COLUMN):
                if col_id != from_col_id:
                    col = game.column[col_id]
                    if len(col) > 0:
                        lc = col[-1]
                        if lc.color != c.color and lc.num - c.num == 1:
                            avail_dest.append(col_id)

        head_for = []
        # From a freecell
        for cfc in game.freecell:
            if cfc not in self.cards:
                if cfc.color != c.color and c.num - cfc.num == 1:
                    head_for.append((COL_FC,1))
        
        # From a col
        serie_max, _ = game.count_serie_max()
        for col_id in range(COLUMN):
            if col_id != from_col_id:
                col = game.column[col_id]
                seriesize = min(game.get_serie_len(col_id), serie_max)
                for ocid in range(len(col) - seriesize, len(col)):
                    oc = col[ocid]
                    if oc.color != c.color and c.num - oc.num == 1:
                        head_for.append((col_id,seriesize-ocid))
                        break

        return head_for, avail_dest

    def get_params(self, game):
        """ Compute parameters for this choice, with value in [0, 1]
                * nb cards moved / maximum of cards that can be moved
                * last card value
                * is From Freecell
                * is From Freecell and size of freecell
                * is origin column freed
                * interest of origin column (compute possibilites of remaining cards in column)
                * is a serie broken in orig column
                * is going to Base
                * is going to Base and base difference (highest - lowest value card in bases)
                * is going to Freecell
                * is going to Freecell and size of freecell
                * is going to an empty column
                * size of the serie in the destination column (over size of column)
                * can last card be the head of another serie
        """
        params = list()

        # Nb cards moved (max 1 for FC and Base)
        nbmax = 1
        if self.col_dest not in [COL_FC, COL_BASE]:
            nbmax = game.count_serie_max()[int(len(self.col_dest_copy) == 0)]
        params.append(len(self.cards) / nbmax)

        # last card value
        lc = self.cards[-1]
        params.append(lc.num / len(CARD_VALUE))

        # Source
        # from Freecell
        params.append(float(self.col_orig == COL_FC))
        params.append(float(self.col_orig == COL_FC) * (len(game.freecell) / FREECELL))
        # from a Column
        freed = False
        interest = 0.0
        break_serie = False
        if self.col_orig in range(0, COLUMN):
            remaining_size = len(self.col_orig_copy) - len(self.cards)
            freed = remaining_size == 0
            if not freed:
                break_serie = game.get_serie_len(self.col_orig) > len(self.cards)

                # compute interest by listing possibilities of cards remaining in column
                game.apply(self)
                freespace = (FREECELL - len(game.freecell)) + \
                             + sum([int(len(c) == 0) for c in game.column])
                cid = remaining_size - 1
                while cid >= 0 and freespace >= 0:
                    h, d = self.list_possibilities(game, self.col_orig, cid)
                    # remove opposite direction possibility
                    if cid == remaining_size-1:
                        if (self.col_dest, len(self.cards)) in h:
                            h.remove((self.col_dest, len(self.cards)))
                    ci = 0
                    for p in h + d:
                        ci += 0.5 + 0.5 * int(p == COL_BASE)
                    interest += min(1, ci)/remaining_size
                    if len(d) == 0:
                        freespace -= 1
                    cid -= 1 
                game.reverse_apply(self)              
        params.append(float(freed))
        params.append(interest)
        params.append(float(break_serie))
        
        # Destination
        # to Base
        params.append(float(self.col_dest == COL_BASE))
        params.append(float(self.col_dest == COL_BASE) * (game.get_base_diff()/len(CARD_VALUE)))
        # to Freecell
        params.append(float(self.col_dest == COL_FC))
        params.append(float(self.col_dest == COL_FC) * (len(game.freecell)/FREECELL))
        # to Column
        empty = False
        serie_len = 0.0
        nice_last_card = False
        if self.col_dest in range(0, COLUMN):
            empty = len(self.col_dest_copy) == 0
            size = len(self.col_dest_copy) + len(self.cards)
            serie_len = (game.get_serie_len(self.col_dest) + len(self.cards)) / size
            
            game.apply(self)
            h, _ = self.list_possibilities(game, self.col_dest, -1, False)
            nice_last_card = len(h) > 0
            game.reverse_apply(self)
        params.append(float(empty))
        params.append(serie_len)
        params.append(float(nice_last_card))

        return params

class FCGameParamatrized(FreecellGame): 
    def hash_state(self):
        """ For each sorted cards, get their position in the game """
        state = []
        standard_deck = [Card(j, i)  for i in range(1, len(CARD_VALUE)+1) for j in SUITS]
        for c in standard_deck:
            if c in self.base.get(c.suit):
                state.append(COL_BASE)
            elif c in self.freecell:
                state.append(COL_FC)
            else:
                for col in self.column:
                    if c in col:
                        state.append((col[0].uid, col.index(c)))
        return hash(tuple(state))
    
    def get_cih(self):
        return sum([len(b) for b in self.base.values()])
    
    def get_base_diff(self):
        bmax = max([len(b) for b in self.base.values()])
        bmin = min([len(b) for b in self.base.values()])
        return bmax - bmin

    def get_serie_len(self, cid):
        serie_len = 0
        last_c = None
        for c in reversed(self.column[cid]):
            if last_c is not None:
                if last_c.color == c.color or c.num - last_c.num != 1:
                    break
            serie_len += 1
            last_c = c
        return serie_len

    def count_sorted_card(self):
        cih = self.get_cih()
        sorted_count = 0
        for cid in range(COLUMN):
            sorted_count += self.get_serie_len(cid)
        return cih + sorted_count

    def list_choices(self, previous_moves):
        available_choices = []
        for c in super().list_choices():
            cp = ChoiceParametrized(c, self)
            # Check move hasn't been done or doesn't reverse a previous one
            oc = cp.get_opposite(self)
            available = True
            for m in reversed(previous_moves):
                if cp.equals(m) or oc.equals(m):
                    available = False
            if available:
                available_choices.append(cp)

        return available_choices


class FCGameAutoSolve(object):
    """ Solve freecell games by iterate over available weighted choices """

    def __init__(self, deck, scale):
        self.game = FCGameParamatrized(deck)
        self.scale = scale

        self.iter = 0
        self.max_status = 0
        self.winning_moves = None
                
    def _iter_play(self, depth, moves, visited_state):
        # Stop when Game solved
        if self.game.is_won():
            return True

        self.iter += 1
        # Stop when iter limit is reached
        if self.iter > ITER_MAX:
            return False

        # Protect from too deep iteration
        if depth > MAX_ITER_DEPTH:
            return False

        # Get state and avoid loop
        hash = self.game.hash_state()
        if hash in visited_state:
            return False
        visited_state.append(hash)

        # measure game status
        cards_in_home = self.game.get_cih()
        sorted_card = self.game.count_sorted_card()
        status = cards_in_home + sorted_card
        if status > self.max_status:
            self.max_status = status

        # Force sending card to base when they are all sorted
        auto_base = sorted_card == CIH_WON
        
        # List choices and weight them
        choices = self.game.list_choices(moves)
        def weight_choice(choice):
            choice_params = choice.get_params(self.game)
            w = self.scale.compute(choice_params)[0]
            return w + (int(auto_base and choice.col_dest == COL_BASE) * AUTO_BASE_WEIGHT)
        choices.sort(key=weight_choice, reverse=True)

        # Iterate over each choice
        for choice in choices:
            if self.iter > ITER_MAX:
                break
            moves.append(choice)
            self.game.apply(choice)
            if self._iter_play(depth+1, moves, visited_state):
                return True
            moves.pop()
            self.game.reverse_apply(choice)
                            
        return False

    def solve(self, msg=""):
        moves = []
        succ = self._iter_play(0, moves, [])

        if succ:
            self.winning_moves = moves
            print(msg, TermColor.GREEN + "True" + TermColor.ENDC, "moves: %d" %  len(moves),
                  "(%d)" % self.iter)
        else:
            print(msg, TermColor.RED + "False" + TermColor.ENDC, self.max_status)

        return succ
    
class SimpleNN(NeuralNetwork):
    def __init__(self, weights):
        super().__init__(PARAMS, 1, [], weights, [0])
        
    def activation(self, value):
        return value

class Player(MLEvolObject):
    """ Evolutionary object to solve freecell games.
        Use a SimpleNN to compute weights from the choices parameters.

        Before each play, game_data must be loaded in Player
    """

    DEFAULT_GAME_DATA = (-1, [])

    def __init__(self, name, coeffs=None, games_result=None):
        self.name = name
        self.coeffs = coeffs
        if self.coeffs is None:
            self.coeffs = [random.uniform(-5, 5) for _ in range(PARAMS)]
        
        self.nn = SimpleNN(self.coeffs)

        self.games_result = games_result
        if self.games_result is None:
            self.games_result = dict()

        self.game_data = Player.DEFAULT_GAME_DATA
        self.game_moves = MAX_ITER_DEPTH
        self.game_status = 0

    def play(self):
        assert self.game_data != Player.DEFAULT_GAME_DATA
        gsid = self.game_data[0]
        g = self.game_data[1]
    
        if gsid in self.games_result.keys():
            mres = self.games_result.get(gsid)
            if mres > 0:
                self.game_moves = mres
                self.game_status = SCORE_WON
            else:
                self.game_moves = MAX_ITER_DEPTH
                self.game_status = 0
            return

        fcgas = FCGameAutoSolve(g, self.nn)
        if fcgas.solve(self.name + " play game %d: " % gsid):
            self.games_result[gsid] = len(fcgas.winning_moves)
            self.game_moves = len(fcgas.winning_moves)
            self.game_status = SCORE_WON
        else:
            self.games_result[gsid] = 0
            self.game_moves = MAX_ITER_DEPTH
            self.game_status = fcgas.max_status
                    
    def score(self):
        return (self.game_status, MAX_ITER_DEPTH - self.game_moves)

    def make_kids(self, nkids):
        kids = []
        for kid in range(nkids):
            kname = self.name + "_" + str(kid)
            kc = self.coeffs[:]
            for cid in range(PARAMS):
                kc[cid] += random.gauss(0, 0.1) 
            k = Player(kname, coeffs=kc)
            k.game_data = self.game_data
            kids.append(k)

        return kids

    def cumulated_score(self, games_id):
        solved = 0
        cumulated_moves = 0
        for gid in games_id:
            moves = self.games_result.get(gid, 0)
            if moves > 0:
                solved += 1
                cumulated_moves += moves
        mean_moves = MAX_ITER_DEPTH
        if solved > 0:
            mean_moves = cumulated_moves/solved
        return (solved, MAX_ITER_DEPTH - mean_moves)

    def jsonize(self):
        serial_obj = {"coeffs": self.coeffs,
                      "results": self.games_result}
        return serial_obj

def load_file(filename):
    players = []
    games_played = set()

    print("Reading file", filename)
    try:
        serial_obj_list = None
        with open(filename, "r") as f:
            serial_obj_list = json.load(f)

        pid = 0
        for obj in serial_obj_list:
            coeffs = obj.get("coeffs", [])
            str_res = obj.get("results")

            assert len(coeffs) == PARAMS
            assert str_res is not None

            results = dict()
            for str_gid, res in str_res.items():
                gid = int(str_gid)
                games_played.add(gid)
                results[gid] = res

            players.append(Player("f"+str(pid), coeffs=coeffs, games_result=results))
            pid += 1
    except (IOError, AssertionError, AttributeError, ValueError) as e:
        print(e)
        print("Wrong configuration, ignoring file")
    
    if len(players) == 0:
        players.append(Player("my", coeffs=MY_PLAYER))

    return (players, games_played)


def save(filename, players):
    print("Save in file", filename)
    serial_p_list = [p.jsonize() for p in players]
    with open(filename, 'w') as f:
        json.dump(serial_p_list, f)

def sort_players(players, games):
    print("Sort players")
    
    sorted_players = []
    trepo = players[:]
    remaining_games = set(games.keys())

    # Look for each players the one who solve the most remaining games
    while len(trepo) > 0 and len(remaining_games) > 0:
        def sort_p(p):
            return p.cumulated_score(remaining_games)
        trepo.sort(key=sort_p, reverse=True)
        best_p = trepo[0]
        sorted_players.append(best_p)

        ng = 0
        for gid, m in best_p.games_result.items():
            if m > 0 and gid in remaining_games:
                remaining_games.remove(gid)
                ng += 1
        ng_pc = (ng/len(games)) * 100
        print(best_p.name, "solve:", ng_pc, "%")

        trepo = trepo[1:]

    return sorted_players
    

def train(starting_seed, ngames):
    """ Find players that solve freecell games and store them in a file """

    # create games
    print("Creating %d games, starting on seed %d" % (ngames, starting_seed))
    print()
    deck = [Card(j, i)  for i in range(1, len(CARD_VALUE)+1) for j in SUITS]
    games = dict()
    for gsid in range(starting_seed, starting_seed + ngames):
        rgenerator = random.Random(gsid)
        d = deck[:]
        rgenerator.shuffle(d)
        games[gsid] = d
    
    # Load players
    players, file_gsid = load_file(DBFILE)

    # load games from file
    print("Load previous games from file")
    for gsid in file_gsid:
        if gsid not in games.keys():
            rgenerator = random.Random(gsid)
            d = deck[:]
            rgenerator.shuffle(d)
            games[gsid] = d

    print()
    gameid_played = []
    unsolved_games = []
    for gsid in sorted(games.keys()):
        g = games.get(gsid)
        print("Solve game", gsid)
        solved = False

        evol_algo = MLEvolAlgo()
    
        print("Try all known players:")
        for p in players:
            p.game_data = (gsid, g)
            evol_algo.repo.append(p)
        evol_algo.run(NKIDS)
    
        best_known_p = evol_algo.last_best[0]
        solved = best_known_p.score() > (SCORE_WON, 0)

        if not solved:
            print("Try new players:")

            gid = 0
            kid = 0
            reset = best_known_p.score()[0] <= SCORE_WON/2
            while  not solved and gid < MAX_GEN:
                if reset:
                    print("Reset evol algo to random kids")
                    evol_algo.last_best.clear()
                    evol_algo.repo.clear()
                    for _ in range(NKIDS):
                        p = Player(str(gsid)+"."+str(kid))
                        p.game_data = (gsid, g)
                        evol_algo.repo.append(p)
                        kid += 1

                print("Generation", gid+1)
                reset = not evol_algo.run(NKIDS)
                gid += 1
                solved = evol_algo.last_best[0].score() > (SCORE_WON, 0)
            
            if solved:
                print("Improve solution by running the evol algo")
                evol_algo.repo = evol_algo.repo[0:NKIDS_IMPROVE]
                while evol_algo.run(NKIDS_IMPROVE):
                    pass
                best_p = evol_algo.last_best[0]

                print("Play previous games:")
                for gid in gameid_played:
                    best_p.game_data = (gid, games[gid])
                    best_p.play()
                    if gid in unsolved_games and best_p.score()[0] == SCORE_WON:
                        unsolved_games.remove(gid)
                players.append(best_p)

        if not solved:
            print("No solution found!")
            unsolved_games.append(gsid)
        
        print("solved!")
        gameid_played.append(gsid)
        print()

    for gid in unsolved_games:
        games.pop(gid)
    sorted_p = sort_players(players, games)
    
    print("Unsolved:", unsolved_games)
    save(DBFILE, sorted_p)

def solve_game(game):
    """ Solve one game from file using known players """
    
    gamep = FCGameParamatrized([])
    gamep.column = game.column
    gamep.base = game.base
    gamep.freecell = gamep.freecell

    players, _ = load_file(DBFILE)

    solved = False

    pid = 0
    for p in players:
        fcgas = FCGameAutoSolve([], p.nn)
        fcgas.game = gamep

        solved = fcgas.solve("Player %d plays" % pid)
        if solved:
            print()
            for m in fcgas.winning_moves:
                print(m)
            break
        pid += 1
    
    if not solved:
        print("No solution found")

if __name__ == "__main__":

    usage = "./fcml.py train <starting_seed> <number of games>\n" + \
            "          autotrain\n" + \
            "          solve <game file>"

    if len(sys.argv) < 2:
        print(usage)
        exit(1)

    # Training mode
    if sys.argv[1] == "train":
        if len(sys.argv) < 4:
            print(usage)
            exit(1)

        # Read parameter
        starting_seed = 0
        ngames = 0
        try:
            starting_seed = int(sys.argv[2])
            ngames = int(sys.argv[3])
        except ValueError as v:
            print(v)
            print(usage)
            exit(1)

        train(starting_seed, ngames)

    elif sys.argv[1] == "autotrain":
        # Run train algorithm multiple times
        for i in range(0, AUTOTRAIN_MAX):
            print("Step %d/%d" % (i+1, AUTOTRAIN_MAX))
            train(i*AUTOTRAIN, AUTOTRAIN)
            print()
            print()

    # Solving mode
    elif sys.argv[1] == "solve":
        if len(sys.argv) < 3:
            print(usage)
            exit(1)

        filename = sys.argv[2]
        try:
            game = load_game(filename)
        except:
            print("Please give a valid game file")
            exit(1)
        
        solve_game(game)

    else:
        print(usage)
        exit(1)
    
    exit(0)
