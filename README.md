# Freecell solver

play.py : simple freecell game.

solve.py : solve a specific freecell game (from file or number)

impossible : one of the impossible game

# Solver algorithm
For each step:
    compute hash state to avoid loop,
    list possibilities (and don't include moves alredy done or reversed moves, also to avoid loop),
    compute a weight for these possibilities and sort them,
        weight is computed with a mix of random and a priority given the type of move (if it help sorting cards, if it increase max mvt...) 
    iter over them until a maximum of iteration or the Solution is found 

# context, previously FCML
Tried to find a way of sorting the choices using coeffs found by ML algo, but random sort seems the most efficient for the most games anyway
