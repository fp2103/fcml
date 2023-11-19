#!/usr/bin/python3
# -*- coding: utf-8 -*

import random
import src.model as model

MAX_ITER = 5000

class Solver(object):
    def __init__(self, fcboard):
        self.fcboard = fcboard
        self.noexit = set()
        self.called = -1
    
    def sort_choices(self, choices_list, game):
        # Priorities categories:
        # 1) base & reduce base diff
        # 2) sorted inc & mvt_max (= or inc)
        # 3) other
        # 4) sorted = & mvt_max dec

        CAT1 = 10000
        CAT2 = 5
        CAT3 = 1
        CAT4 = 0
        rfactor = self.called if self.called > 0 else 0.4
        
        for xchoice in choices_list:
            choice = xchoice[0]
            crand = (2*rfactor*random.random())-rfactor

            # From 
            from_fc = choice.col_orig == model.COL_FC
            empty_col = not from_fc and len(game.fcboard.columns[choice.col_orig]) == len(choice.cards)
            split_serie = not from_fc and len(game._column_series[choice.col_orig]) > len(choice.cards)

            # To
            if choice.col_dest == model.COL_BASE:
                bases_len = [len(game.fcboard.bases[k]) for k in model.SUITS]
                diff_bases = max(bases_len) - min(bases_len)

                i = model.SUITS.index(choice.cards[0].suit)
                bases_len[i] += 1
                new_diff_bases = max(bases_len) - min(bases_len)

                if new_diff_bases < diff_bases:
                    choice.weight = CAT1 + crand
                else:
                    choice.weight = CAT2 + crand
            elif choice.col_dest == model.COL_FC:
                if empty_col or split_serie:
                    choice.weight = CAT4 + crand
                else:
                    choice.weight = CAT3 + crand
            elif len(game.fcboard.columns[choice.col_dest]) == 0: # to empty col
                if from_fc or split_serie:
                    choice.weight = CAT4 + crand
                else:
                    choice.weight = CAT3 + crand
            else: # to not empty col
                if split_serie: # sorted =
                    choice.weight = CAT3 + crand
                else: # sorted inc or max_mvt inc
                    choice.weight = CAT2 + crand
        
        choices_list.sort(key=lambda x: x[0].weight)

    def solve(self):
        """
        Navigate state to solution
        return: True, list of moves
                False, max in base
        """
        self.called += 1
        # reset game
        game = model.FCGame(self.fcboard.clone())

        moves = [] # [(choice, hash)]
        moves_done = set()
        states_choices = [] # [(hashst, [(choice, hash)])]: for each visited states, keep list of sorted choices
        current_state = None # (hashst, [(choice, hash)])
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
                    return True, [m[0] for m in moves], giter
                max_in_base = max(max_in_base, in_base)
                
                hashst = game.fcboard.compute_hash()
                if hashst in state_seen or hashst in self.noexit: # go back when state has already been seen 
                    current_state = (hashst, [])
                    seen = True
                else:
                    state_seen.add(hashst)

                    all_choices = game.list_choices()
                    viable_choices = [] # [(choice, hash)]
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
                if not seen: # go back cause no more choice
                    self.noexit.add(current_state[0])
                current_state = states_choices.pop()

        return False, max_in_base, giter

def moves_reducer(fcboard, moves):
    game = model.FCGame(fcboard.clone())

    nmoves = moves[:]
    i = 0
    while i < len(nmoves):
        mvt = nmoves[i]

        # searching next moves with same cards
        j = i+1
        while j < len(nmoves):
            if nmoves[j].cards == mvt.cards: # found possible replacement
                nmvt = model.Choice(mvt.cards, mvt.col_orig, nmoves[j].col_dest)

                ngame = model.FCGame(game.fcboard.clone())
                impact = False
                m = nmvt
                k = i
                while not impact and k < len(nmoves):
                    possible = False
                    for choice in ngame.list_choices():
                        if choice.equals(m):
                            possible = True
                            break
                    if possible:
                        ngame.apply(m)
                        k += 1
                        if k == j: k += 1 # skip possible replacement
                        if k < len(nmoves):
                            m = nmoves[k]
                    else:
                        impact = True
                
                if not impact:
                    nmoves[i] = nmvt
                    del nmoves[j]
                else:
                    break
            j += 1
        
        game.apply(nmoves[i])
        i += 1

    return nmoves
    

