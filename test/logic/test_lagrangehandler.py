import numpy as np
from sympy import symbols
from logic.lagrangehandler import LagrangeHandler

def test_linear_eqn():
    constants = a, b = symbols("a b")
    primals = x, y = symbols("x y")
    duals = Lx, Ly = symbols("Lx Ly")

    eqns = [
        a * x - b * y,
        -a * x + b * y + 5
    ]

    lagrange = np.dot(duals, eqns)

    lh = LagrangeHandler(lagrange, constants, primals, duals)

    assert 4 == len(lh.derivatives)

    dxentry = lh.derivatives[x]
    assert (Lx * a - Ly * a) == dxentry.expr
    assert 2 == len(dxentry.variable_exprs)
    assert a == dxentry.variable_exprs[Lx]
    assert -a == dxentry.variable_exprs[Ly]

    dyentry = lh.derivatives[y]
    assert (-Lx * b + Ly * b) == dyentry.expr
    assert 2 == len(dyentry.variable_exprs)
    assert -b == dyentry.variable_exprs[Lx]
    assert b == dyentry.variable_exprs[Ly]    

    dLxentry = lh.derivatives[Lx]
    assert (a * x - b * y) == dLxentry.expr
    assert 2 == len(dLxentry.variable_exprs)
    assert a == dLxentry.variable_exprs[x]
    assert -b == dLxentry.variable_exprs[y]  

    dLyentry = lh.derivatives[Ly]
    assert (-a * x + b * y + 5) == dLyentry.expr
    assert 2 == len(dLyentry.variable_exprs)
    assert -a == dLyentry.variable_exprs[x]
    assert b == dLyentry.variable_exprs[y]
    assert -5 == dLyentry.constant_expr


def test_nonlinear_eqn():
    constants = a, b = symbols("a b")
    primals = x, y = symbols("x y")
    duals = Lx, Ly = symbols("Lx Ly")

    eqns = [
        a * x ** 2 - b * y,
        -a * x + b * x * y + 5
    ]

    lagrange = np.dot(duals, eqns)

    lh = LagrangeHandler(lagrange, constants, primals, duals)

    assert 4 == len(lh.derivatives)

    dxentry = lh.derivatives[x]
    assert (2 * a * x * Lx + (- a + b * y) * Ly) == dxentry.expr
    assert 4 == len(dxentry.variable_exprs)
    assert 2 * a * Lx == dxentry.variable_exprs[x]
    assert b * Ly == dxentry.variable_exprs[y]
    assert 2 * a * x == dxentry.variable_exprs[Lx]
    assert -a + b * y == dxentry.variable_exprs[Ly]
    assert 2 * a * x * Lx + b * y * Ly == dxentry.constant_expr

    dyentry = lh.derivatives[y]
    assert (-b * Lx + b * x * Ly) == dyentry.expr
    assert 4 == len(dyentry.variable_exprs)
    assert b * Ly == dyentry.variable_exprs[x]
    assert 0 == dyentry.variable_exprs[y]
    assert -b == dyentry.variable_exprs[Lx]
    assert b * x == dyentry.variable_exprs[Ly]
    assert b * x * Ly == dyentry.constant_expr  

    dLxentry = lh.derivatives[Lx]
    assert (a * x ** 2 - b * y) == dLxentry.expr
    assert 4 == len(dLxentry.variable_exprs)
    assert 2 * a * x == dLxentry.variable_exprs[x]
    assert -b == dLxentry.variable_exprs[y]
    assert 0 == dLxentry.variable_exprs[Lx]
    assert 0 == dLxentry.variable_exprs[Ly]
    assert a * x ** 2 == dLxentry.constant_expr  

    dLyentry = lh.derivatives[Ly]
    assert (-a * x + b * x * y + 5) == dLyentry.expr
    assert 4 == len(dLyentry.variable_exprs)
    assert -a + b * y == dLyentry.variable_exprs[x]
    assert b * x == dLyentry.variable_exprs[y]
    assert 0 == dLyentry.variable_exprs[Lx]
    assert 0 == dLyentry.variable_exprs[Ly]
    assert b * x * y - 5 == dLyentry.constant_expr  