#!/usr/bin/python3
# -*- coding: utf-8 -*

import random
import src.model as model

MAX_ITER = 5000

class Solver(object):
    def __init__(self, fcboard):
        self.fcboard = fcboard
        self.noexit = set()
    
    def sort_choices(self, choices_list, game):
        raise NotImplementedError()

    def solve(self):
        """
        Navigate state to solution
        return: True, list of moves
                False, max in base
        """
        # reset game
        game = model.FCGame(self.fcboard.clone())

        moves = [] # (choice, hash)
        moves_done = set()
        states_choices = [] # [(hashst, [(choice, hash)])]: for each visited states, keep list of sorted choices
        current_state = None
        state_seen = set()

        max_in_base = 0
        
        giter = 0
        while giter < MAX_ITER:
            giter += 1        

            # new state
            seen = False
            if current_state is None:

                in_base = sum([len(game.fcboard.bases.get(k)) for k in model.SUITS])
                if in_base == len(model.DECK):
                    return True, [m[0] for m in moves]
                max_in_base = max(max_in_base, in_base)
                
                hashst = game.fcboard.compute_hash()
                if hashst in state_seen or hashst in self.noexit: # go back when state has already been seen 
                    current_state = (hashst, [])
                    seen = True
                else:
                    state_seen.add(hashst)

                    all_choices = game.list_choices()
                    viable_choices = [] # (choice, hash)
                    for c in all_choices:
                        chash = c.compute_hash(game.fcboard)
                        if chash in moves_done:
                            continue
                        else:
                            viable_choices.append((c, chash))
                    
                    # random
                    self.sort_choices(viable_choices, game)
                    current_state = (hashst, viable_choices)
            
            # go to next state
            if len(current_state[1]) > 0:
                choice = current_state[1].pop()
                game.apply(choice[0])
                moves.append(choice)
                moves_done.add(choice[1])
                states_choices.append(current_state)
                current_state = None
                
            # go back
            else:
                choice = moves.pop()
                game.apply(choice[0].get_reverse())
                moves_done.discard(choice[1])
                if not seen: #go back but was not seen before, so no exit
                    self.noexit.add(current_state[0])
                current_state = states_choices.pop()

        return False, max_in_base

class SolverRandom(Solver):
    def sort_choices(self, choices_list, game):
        random.shuffle(choices_list)

def vector_multiply(v1, v2):
    ret = 0
    for i in range(len(v1)):
        ret += v1[i]*v2[i]
    return ret

class SolverCoeff(Solver):
    def __init__(self, fcboard, coeffs):
        self.coeffs = coeffs # 56 coeffs
        super().__init__(fcboard)

    def sort_choices(self, choices_list, game):
        # state coeffs:
        # constant, max_mvt, ratio(sorted/ingame), bases diff => 4
        # choice coeffs matrix:
        # from/to:        (fc,   empty col,   split serie,   default)     
        # (base,            0/1      0/1         0/1            1
        # (fc,              na       0/1         0/1            1
        # (empty col,       0/1       na         0/1            1
        # (size unsorted    0/1      0/1         0/1           0~1 (1->all sorted)
        # ==> 14 
        # => 4*14 = 56: (4,1)*(1,56)
        
        # State coeffs
        max_mvt_coeff = min(game._last_max_mvt/10.0, 1.0)
        bases_len = [len(game.fcboard.bases[k]) for k in model.SUITS]
        sorted = sum([len(c) for c in game._column_series]) \
                 + len(game.fcboard.freecells) \
                 + sum(bases_len)
        sorted_coeff = sorted/52.0
        bases_diff_coeff = (max(bases_len) - min(bases_len))/13.0

        # compute choice matrix coeffs
        weight_coeffs = []
        i = 0
        while i < len(self.coeffs):
            w = 0
            if not (len(weight_coeffs) == 4 or len(weight_coeffs) == 9): # coeff 4 & 9 are NA
                w = vector_multiply(self.coeffs[i:i+4], (1.0, max_mvt_coeff, sorted_coeff, bases_diff_coeff))
                i += 4
            weight_coeffs.append(w)

        # compute weight for each choice
        for xchoice in choices_list:
            choice = xchoice[0]

            from_fc = int(choice.col_orig == model.COL_FC)
            from_emptycol = int(choice.col_orig != model.COL_FC \
                                and len(game.fcboard.columns[choice.col_orig]) == len(choice.cards))
            from_split_serie = int(choice.col_orig != model.COL_FC \
                                   and len(game._column_series[choice.col_orig]) > len(choice.cards))
            
            to_coeff = 1.0
            i = 0 # cold_dest == COL_BASE
            if choice.col_dest == model.COL_FC:
                i = 4
            elif choice.col_dest != model.COL_BASE and len(game.fcboard.columns[choice.col_dest]) == 0:
                i = 8
            elif choice.col_dest != model.COL_BASE:
                i = 12
                ratio = 6.0 if choice.col_dest < 4 else 5.0
                to_coeff = 1.0 - ((len(game.fcboard.columns[choice.col_dest]) - len(game._column_series[choice.col_dest]))/ratio)
            
            choice.weight = vector_multiply(weight_coeffs[i:i+4], (from_fc, from_emptycol, from_split_serie, to_coeff))
        
        # sort
        choices_list.sort(key=lambda x: x[0].weight)

