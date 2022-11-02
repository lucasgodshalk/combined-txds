from collections import Counter
from itertools import count
from logic.stamping.lagrangestamper import LagrangeStamper
from logic.powerflowsettings import PowerFlowSettings
from models.singlephase.bus import Bus
from logic.stamping.matrixbuilder import MatrixBuilder
from models.singlephase.line import line_lh, tx_factor

settings = PowerFlowSettings()

idx_count = count(0)

idx_map = {}
for variable in line_lh.variables:
    idx_map[variable] = next(idx_count)

def test_line_symbols_powerflow():
    lh = LagrangeStamper(line_lh, idx_map, False)

    size = next(idx_count)

    Y = MatrixBuilder(settings)
    J = [0] * size

    lh.stamp_primal_symbols(Y, J)

    Y_matrix = Y.to_symbolic_matrix()

    Y_matrix = Y_matrix.subs(tx_factor, 0)

    assert 1 == 1

def test_line_symbols_opt():
    lh = LagrangeStamper(line_lh, idx_map, True)

    size = next(idx_count)

    Y = MatrixBuilder(settings)
    J = [0] * size

    lh.stamp_primal_symbols(Y, J)
    lh.stamp_dual_symbols(Y, J)

    Y_matrix = Y.to_symbolic_matrix()

    Y_matrix = Y_matrix.subs(tx_factor, 0)

    assert 1 == 1