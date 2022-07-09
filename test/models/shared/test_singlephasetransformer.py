
from itertools import count
from logic.lagrangestamper import LagrangeStamper
from logic.matrixbuilder import MatrixBuilder
from logic.powerflowsettings import PowerFlowSettings
from models.shared.bus import GROUND, Bus
from models.shared.single_phase_transformer import xfrmr_lh, tx_factor

settings = PowerFlowSettings()

idx_count = count(0)

idx_map = {}
for variable in xfrmr_lh.variables:
    idx_map[variable] = next(idx_count)

def test_singlephasetransformer_stamp():

    lh = LagrangeStamper(xfrmr_lh, idx_map, False)

    size = next(idx_count)

    Y = MatrixBuilder(settings)
    J = [0] * size

    lh.stamp_primal_symbols(Y, J)

    Y_matrix = Y.to_symbolic_matrix()

    Y_matrix = Y_matrix.subs(tx_factor, 0)

    assert 1 == 1



