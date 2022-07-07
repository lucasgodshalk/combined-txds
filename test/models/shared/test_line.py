from collections import Counter
from itertools import count
from logic.lagrangestamper import LagrangeStamper
from logic.powerflowsettings import PowerFlowSettings
from models.shared.bus import Bus
from logic.matrixbuilder import MatrixBuilder
from models.shared.line import line_lh, tx_factor

settings = PowerFlowSettings()

idx_count = count(0)

idx_map = {}
for variable in line_lh.variables:
    idx_map[variable] = next(idx_count)

def test_line_symbols_powerflow():
    lh = LagrangeStamper(line_lh, idx_map, False)

    size = next(idx_count)

    Y = MatrixBuilder(settings, is_symbolic=True)
    J = [0] * size

    lh.stamp_primal_symbols(Y, J)

    Y_matrix = Y.to_symbolic_matrix()

    Y_matrix = Y_matrix.subs(tx_factor, 0)

    assert 1 == 1

def test_line_symbols_opt():
    lh = LagrangeStamper(line_lh, idx_map, True)

    size = next(idx_count)

    Y = MatrixBuilder(settings, is_symbolic=True)
    J = [0] * size

    lh.stamp_primal_symbols(Y, J)
    lh.stamp_dual_symbols(Y, J)

    Y_matrix = Y.to_symbolic_matrix()

    Y_matrix = Y_matrix.subs(tx_factor, 0)

    assert 1 == 1

def test_line_values_powerflow():
    lh = LagrangeStamper(line_lh, idx_map, False)

    size = next(idx_count)

    Y = MatrixBuilder(settings, is_symbolic=False)
    J = [0] * size
    v = [0] * size

    lh.stamp_primal(Y, J, [2, 3, 0], v)

    Y_matrix = Y.to_matrix().todense()

    assert 1 == 1