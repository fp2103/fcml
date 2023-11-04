# fcml
Freecell solver

play.py : simple freecell game.

solve.py : solve a specific freecell game (from file or number)

train.py : find best coeff to improve solver using machine learning evolution algorithm


# Solver algorithm
For each step:
    compute hash state to avoid loop,
    list possibilities (and don't include moves alredy done or reversed moves, also to avoid loop),
    compute a weight for these possibilities and sort them,
    iter over them until a maximum of iteration or the Solution is found 

each choice have a set of parameters and coefficients are applied to it to compute the weight of the choice
Evolution alogrithm is done over these coefficients.
