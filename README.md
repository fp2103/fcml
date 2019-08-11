# fcml
Freecell auto solver

freecell.py : simple freecell game.

fcml.py : Solve freecell games by using an evolutionary alogrithm.
          Create a list of player strategy to solve most of freecell games.



# Solver algorithm
For each step:
    compute hash state to avoid loop,
    list possibilities (and don't include moves alredy done or reversed moves, also to avoid loop),
    compute a weight for these possibilities and sort them,
    iter over them until a maximum of iteration or the Solution is found 

each choice have a set of parameters and coefficients are applied to it to compute the weight of the choice
Evolution alogrithm is done over these coefficients.

Each set of coefficient is called a Player,
multiple players are kept in a file in order to solve the most variety of Freecell games.
