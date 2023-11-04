#!/usr/bin/python3
# -*- coding: utf-8 -*

import random

import src.model as fc
import conf as p

def vector_multiply(v1, v2):
    ret = 0
    for i in range(min(len(v1), len(v2))):
        ret += v1[i]*v2[i]
    return ret

def get_state_status(game):
    len_bases = [len(b) for b in game.fcboard.bases.values()]
    in_bases = sum(len_bases)
    gap_bases = max(len_bases) - min(len_bases)
    in_series = sum([len(c) for c in game._column_series]) + in_bases
    return (in_bases, gap_bases, in_series)

def hash_state(game):
    ret = ".".join(sorted([str(c.uid) for c in game.fcboard.freecells]))
    ret += ":"
    cols = []
    for i in range(fc.COLUMN):
        cols.append(".".join([str(c.uid) for c in game.fcboard.columns[i]]))
    ret += ":".join(sorted(cols))
    return ret

def hash_choice(game, choice):
    ret = ",".join([c.name for c in choice.cards]) + ":"
    col_orig_str = choice.col_orig
    if choice.col_orig != fc.COL_FC:
        col_orig_str = ",".join([c.name for c in game.fcboard.columns[choice.col_orig][:-len(choice.cards)]])
    col_dest_str = choice.col_dest
    if choice.col_dest != fc.COL_BASE and choice.col_dest != fc.COL_FC:
        col_dest_str = ",".join([c.name for c in game.fcboard.columns[choice.col_dest]])
    ret += "-".join(sorted([col_orig_str, col_dest_str]))
    return ret

def non_stop_func():
    return False

class SolverCoeff(object):
    """
    Navigate tree by weighting state and choice using coeff
    """
    PARAMS = 22

    def __init__(self, name, coeffs):
        self.name = name
        self.coeffs = coeffs
        self.coeffs_state = coeffs[:5]
        self.coeffs_choice = coeffs[5:]
            
    def _weight_choice(self, game, choice, mvt_max, in_series, gap_bases):
        to_base = choice.col_dest == fc.COL_BASE
        to_base_g = to_base * gap_bases

        to_fc = choice.col_dest == fc.COL_FC
        to_fc_p = to_fc * (1 - mvt_max)
        
        to_serie = choice.col_dest != fc.COL_BASE and choice.col_dest != fc.COL_FC and len(game._column_series[choice.col_dest]) > 0
        
        to_emptycol = choice.col_dest != fc.COL_BASE and choice.col_dest != fc.COL_FC and len(game._column_series[choice.col_dest]) == 0
        to_emptycol_p = to_emptycol * (1 - mvt_max)

        from_fc = choice.col_orig == fc.COL_FC
        split_serie = choice.col_orig != fc.COL_FC and len(game._column_series[choice.col_orig]) > len(choice.cards)
        empty_col = choice.col_orig != fc.COL_FC and len(game.fcboard.columns[choice.col_orig]) == len(choice.cards)

        discover_base = False
        if not from_fc and not empty_col:
            next_c = game.fcboard.columns[choice.col_orig][-(len(choice.cards)+1)]
            discover_base = next_c.num == len(game.fcboard.bases.get(next_c.suit))+1
        
        if from_fc:
            v = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.0, 1-mvt_max, to_base, to_base_g, to_serie, to_emptycol)
        else:
            v = (1.0, to_base, to_base_g, to_fc, to_fc_p, to_serie, to_emptycol, to_emptycol_p, split_serie, empty_col, discover_base, \
                 0, 0, 0, 0, 0, 0)
        
        to_base_force = to_base * 1000 * (in_series**3)
        return vector_multiply(v, self.coeffs_choice) + to_base_force
    
    def solve(self, game, stop_func=non_stop_func): # -> (True/False, max_in_bases, moves, iter)
        ngame = game
        # Return to last best weigthed state 
        best_states = [] # (board, n moves, list of moves done on that state, last best weight)
        last_best_weight = -10000
        state_moves_done = set()

        moves = [] # (move, hash)
        moves_hash = set()
        max_in_base = 0
        global_iter = 0
        while global_iter < p.MAX_ITER and not stop_func():
            global_iter += 1

            # State status
            in_bases, gap_bases, in_series = get_state_status(ngame)
            if in_bases == 52:
                return (True, 52, [m[0] for m in moves], global_iter)
            max_in_base = max(in_bases, max_in_base)
            
            # get all choices
            all_choices = ngame.list_choices()
            
            # compute state weight
            in_series_coeff = in_series/52.0
            gap_bases_coeff = gap_bases/13.0
            mvt_max_coeff = min(ngame._last_max_mvt/13.0, 1.0)

            sv = (in_bases/52.0, gap_bases_coeff, in_series_coeff, mvt_max_coeff, min(len(all_choices)/15.0, 1.0))
            state_weight = vector_multiply(sv, self.coeffs_state)            

            # list & sort choices
            choices_weighted = [] # (choice, hash, weight)
            for c in all_choices:
                chash = hash_choice(ngame, c)
                if chash in moves_hash or chash in state_moves_done:
                    continue

                cweight = self._weight_choice(ngame, c, mvt_max_coeff, in_series_coeff, gap_bases_coeff)
                choices_weighted.append((c, chash, cweight))
            choices_weighted.sort(key=lambda x: x[2], reverse=True)

            # go to next state
            if len(choices_weighted) > 0:
                c = choices_weighted[0][0]
                ch = choices_weighted[0][1]

                # Save current if best
                state_moves_done.add(ch)
                if state_weight >= last_best_weight:
                    best_states.append((ngame.fcboard.clone(), len(moves), state_moves_done, last_best_weight))
                    last_best_weight = state_weight
                state_moves_done = set()

                moves.append((c, ch))
                moves_hash.add(ch)
                ngame.apply(c)
            else:
                # return to last best state
                if len(best_states) > 0:
                    board, last_move_id, state_moves_done, last_best_weight = best_states.pop()
                    ngame = fc.FCGame(ngame.name, board)
                    while len(moves) > last_move_id:
                        m = moves.pop()
                        moves_hash.discard(m[1])
                else:
                    break
        
        return (False, max_in_base, [], global_iter)

class SolverRandom(object):
    """
    Navigate tree randomly
    """
    def __init__(self, id):
        self.id = id
        self.noexit = set()

    def solve(self, game, stop_func, noexit_queue): # -> (True/False, max_in_bases, moves, iter)
        moves = [] # (move, hash)
        moves_hash = set()
        global_iter = 0
        previous_chs = [] # list of hash made on a move
        current_ch = set()
        max_in_base = 0
        while global_iter < p.MAX_ITER and not stop_func():
            global_iter += 1

            hashst = hash_state(game)
            goback = hashst in self.noexit

            if not goback:
                # State status
                in_bases = sum([len(b) for b in game.fcboard.bases.values()])
                if in_bases == 52:
                    return (True, 52, [m[0] for m in moves], global_iter)
                max_in_base = max(in_bases, max_in_base)
                
                # get all choices
                all_choices = game.list_choices()

                remaining_choices = [] # (choice, hash)
                for c in all_choices:
                    chash = hash_choice(game, c)
                    if chash in current_ch or chash in moves_hash:
                        continue
                    else:
                        remaining_choices.append((c, chash))
                
                # go to next state
                if len(remaining_choices) > 0:
                    choice = random.choice(remaining_choices)
                    game.apply(choice[0])
                    moves.append(choice)
                    moves_hash.add(choice[1])
                    current_ch.add(choice[1])
                    previous_chs.append(current_ch)
                    current_ch = set()
                    
                # go to previous state
                else:
                    self.noexit.add(hashst)
                    noexit_queue.put((id, hashst))
                    goback = True
            
            if goback and len(moves) > 0:            
                choice = moves.pop()
                game.apply(choice[0].get_reverse())
                moves_hash.discard(choice[1])
                current_ch = previous_chs.pop()
        
        return (False, max_in_base, [], global_iter)  


#######
# - move reducer
#   ex: (1,2,3) colA ; (1,2,3) -> colB ; (3) -> fc ; (1,2) -> colA ; something else ; (3) -> colA
#   => maybe get that from hash functions
# 
#
# - navigate graph (weight state vs weight choice)
#    -> weight state => apply move and compute state weight
#           > go to next max weight (implies to go down on all choices, possible only if choices are not recomputed)
#    -> weight choice (+ some state info) => tell program what to look for
#           > go to choice w max weight
#    
# pb random is quite efficient too,
# so my guess is that it'll be hard to find too many coeff,
# reduce coeff and use a 3d matrix instead, (dest 4 x orig 4 x state 3)
# 
# 
# 
#    
#
