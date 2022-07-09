import numpy as np
from sympy import symbols
from logic.lagrangehandler import LagrangeHandler

def test_line_eqn():
    constants = a, b = symbols("a b")
    primals = x, y = symbols("x y")
    duals = Lx, Ly = symbols("Lx Ly")

    eqns = [
        a * x - b * y,
        -a * x + b * y
    ]

    lagrange = np.dot(duals, eqns)

    lh = LagrangeHandler(lagrange, constants, primals, duals)

    assert 4 == len(lh.derivatives)

    assert (Lx * a - Ly * a) == lh.derivatives[x].derivative
    assert (-Lx * b + Ly * b) == lh.derivatives[y].derivative
    assert (a * x - b * y) == lh.derivatives[Lx].derivative
    assert (-a * x + b * y) == lh.derivatives[Ly].derivative