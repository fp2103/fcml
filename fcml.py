#!/usr/bin/python3
# -*- coding: utf-8 -*

"""
Solve Freecell with tree search and evolutionary algorithm on best solvers
"""

import queue
import sys
import random
import multiprocessing as mp

import freecell as fc
import conf as p
from train import train
from solvers import SolverCoeff, SolverRandom

def get_strategies():
    ret = []
    print("Getting best known solvers from", p.DBFILE)
    with open(p.DBFILE, "r") as f:
        i = 0
        for line in f.readlines():
            coeffs = [float(c) for c in line.replace('[', '').replace(']', '').split(',')]
            ret.append(SolverCoeff("f%d"%i, coeffs))
            i += 1
    print("Retrieved %d strategies" % len(ret))
    return ret

def master_process(stop_event, noexit_que, noexit_udt_ques):
    while not stop_event.is_set():
        try:
            ne_msg = noexit_que.get(True, 0.1)
            for i in range(p.NPROCESS):
                if i != ne_msg[0]:
                    noexit_udt_ques[i].put(ne_msg[1])
        except queue.Empty:
            pass
    
    # flush queues
    for neuq in [noexit_que] + noexit_udt_ques:
        empty = False
        while not empty:
            try:
                neuq.get(True, 0.1)
            except queue.Empty:
                empty = True

def worker_process(pid, stop_event, ret_que, solvers_coeff, game, noexit_queue, noexit_udt_que):
    workername = "p%d" % pid

    # Use solvers coeff
    for s in solvers_coeff:
        g = fc.FCGame(game.name, game.fcboard.clone())
        ret = s.solve(g, stop_event.is_set)
        print(workername, s.name, ret[0], ret[3])
        if ret[0]:
            stop_event.set()
            ret_que.put((True, ret[2]))
        if stop_event.is_set():
            return
    
    # Use random solver
    sr = SolverRandom(pid)
    for i in range(p.MAX_SOLVERS):

        # Update noexit set
        updated = False
        while not updated:
            try:
                hash = noexit_udt_que.get(False)
                sr.noexit.add(hash)
            except queue.Empty:
                updated = True

        g = fc.FCGame(game.name, game.fcboard.clone())
        ret = sr.solve(g, stop_event.is_set, noexit_queue)
        print(workername, "r%d"%i, ret[0], ret[3], len(sr.noexit))
        if ret[0]:
            stop_event.set()
            ret_que.put((True, ret[2]))
        if stop_event.is_set():
            return
    
    ret_que.put((False, []))
    
def solve(game):
    # Retreive strategies
    known_strategies = []
    try:
        known_strategies = get_strategies()
    except FileNotFoundError:
        print("File", p.DBFILE, "doesn't exist, continue without known solvers")
    
    # Separate solver
    sc_list = [[] for _ in range(p.NPROCESS)]
    j = 0
    nomoreone = False
    for ks in known_strategies:
        sc_list[j].append(ks)
        if j == 0 and len(sc_list[j]) == p.MAX_STRATEGIES_ONE:
            nomoreone = True
            if p.NPROCESS == 1:
                break
        j += 1
        if j >= p.NPROCESS:
            j = 1 if nomoreone else 0

    # create & start Processes
    stop_event = mp.Event()
    return_queue = mp.Queue()
    noexit_queue = mp.Queue()
    noexit_update_queues = [mp.Queue() for _ in range(p.NPROCESS)]

    master_proc = mp.Process(target=master_process, args=(stop_event, noexit_queue, noexit_update_queues))
    master_proc.start()

    ps = []
    for i in range(p.NPROCESS):
        proc = mp.Process(target=worker_process, args=(i, stop_event, return_queue, sc_list[i], game, noexit_queue, noexit_update_queues[i]))
        ps.append(proc)
        proc.start()
    
    ret = (False, [])
    for _ in range(p.NPROCESS):
        ret = return_queue.get()
        if ret[0]:
            print("Found, moves:", len(ret[1]))
            break
    stop_event.set()

    for i in range(p.NPROCESS):
        ps[i].join()
    master_proc.join()

    # Print moves
    print()
    #for m in ret[1]:
        #print(str(m))

    
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
        
        # Retreive strategies
        known_strategies = []
        try:
            known_strategies = get_strategies()
        except FileNotFoundError:
            print("File", p.DBFILE, "doesn't exist, continue without known solvers")

        train(known_strategies, loop, games_id, nkids)

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
            game = fc.FCGame(filename, fc.FCBoard.init_from_deck(deck))
        except:
            print("Please give a valid game file")
            exit(1)
        
        solve(game)
       
    else:
        print(usage)
        exit(1)
    
    exit(0)


# TODO:
# d. UI
