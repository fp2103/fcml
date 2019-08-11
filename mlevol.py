#!/usr/local/bin/python3
# -*- coding: utf-8 -*

""" 
Small library to define Neural Networks and Evolution algorithm
"""

import threading
import random
import math

ZERO_PRECISION = 6

class NeuralNetwork(object):
    """ Represent a neural network with:
            * nin entry
            * nout output
            * nnodes list of number of nodes per intermediate layer
    """

    def __init__(self, nin, nout, nnodes, weights, bias):
        self.nin = nin
        self.nout = nout
        self.nnodes = nnodes
        
        self.weights = weights
        self.bias = bias

        assert len(self.weights) == NeuralNetwork.count_weights(nin, nout, nnodes)
        assert len(self.bias) == NeuralNetwork.count_bias(nout, nnodes)

    @staticmethod            
    def count_weights(nin, nout, nnodes):
        res = 0
        s = nin
        for nn in nnodes + [nout]:
            res += s * nn
            s = nn
        return res
    
    @staticmethod
    def count_bias(nout, nnodes):
        res = 0
        for nn in nnodes + [nout]:
            res += nn
        return res

    def activation(self, value):
        raise NotImplementedError()
    
    def compute(self, params):
        """ From nin entry return nout output
            compute starting from the entry to accelerate computation of zeros
        """
        entry = params[:]
        
        w = 0
        b = 0
        for nstep in self.nnodes + [self.nout]:
            next_step = [0.0 for _ in range(nstep)]
            for e in entry:
                if round(e, ZERO_PRECISION) != 0.0:
                    for s in range(nstep):
                        next_step[s] += e * self.weights[w]
                        w += 1
                else:
                    w += nstep

            # apply activation function for each node of this step
            for s in range(nstep):
                next_step[s] = self.activation(next_step[s] + self.bias[b])
                b += 1

            entry = next_step

        return entry[:]

# --------------------------------------------------

class MLEvolObject(object):
    """ Interface for an evolutionary object """

    def play(self):
        """ What the object should do """
        raise NotImplementedError()

    def score(self):
        """ How does it measure its success """
        raise NotImplementedError()

    def make_kids(self, nkids):
        """ How does it create its offspring """
        raise NotImplementedError()


class MLEvolAlgo(object):
    """ Simple evolution algorithm based on MLEvolObject as evolutionary object """

    def __init__(self):
        self.repo = []
        self.last_best = []

    def find_best(self):
        """ Return list of objects with the best score available """
        # get score function
        def o_score(o):
            return o.score()

        # From repo, get object(s) with best score
        res = []
        if len(self.repo) > 0:
            best_score = 0
            best_score = max(self.repo, key=o_score).score()
            print("Best score found:", best_score)
            for o in self.repo:
                if o.score() == best_score:
                    res.append(o)
        return res

    def run(self, max_kids, strictly_better=True):
        """ Evolution algorithm on one generation
            Return True if progress was made, False otherwise
        """
        # Play EvolObject
        for o in self.repo:
            o.play()

        # Find best and verify its better than last run
        run_result = True
        best = self.find_best()
        parents = best
        if len(self.last_best) > 0 and len(best) > 0:
            lb = self.last_best[0].score()
            nb = best[0].score() 
            if nb < lb or (strictly_better and nb == lb):
                print("No progress, keep parents with score:", lb)
                parents = self.last_best
                run_result = False

        # Generate offsprings (at most max_kids)
        kids = []
        for p in parents:
            nk = int(max_kids/len(parents))
            nk = max(1, nk)
            kids.extend(p.make_kids(nk))
        
        # Update repo for next run
        self.last_best = parents
        self.repo.clear()
        self.repo.extend(kids)

        return run_result