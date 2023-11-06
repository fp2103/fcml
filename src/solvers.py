#!/usr/bin/python3
# -*- coding: utf-8 -*

import random
import src.model as model

MAX_ITER = 5000

class SolverRandom(object):
    def __init__(self, fcboard):
        self.fcboard = fcboard
        self.noexit = set()

    def solve(self):
        # reset game
        game = model.FCGame(self.fcboard.clone())

        moves = [] # (choice, hash)
        moves_done = set()
        states_choices = [] # [(hashst, [(choice, hash)])]: for each visited states, keep list of sorted choices
        current_state = None
        state_seen = set()
        
        giter = 0
        while giter < MAX_ITER:
            giter += 1        

            # new state
            seen = False
            if current_state is None:

                if game.fcboard.is_won():
                    return [m[0] for m in moves]
                
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
                    random.shuffle(viable_choices)
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

        return False
