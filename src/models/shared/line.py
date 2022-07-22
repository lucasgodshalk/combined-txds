import numpy as np
from sympy import symbols
from logic.lagrangehandler import LagrangeHandler
from logic.lagrangestamper import LagrangeStamper
from models.shared.bus import Bus

TX_LARGE_G = 20
TX_LARGE_B = 20

constants = G_orig, B_orig, tx_factor = symbols('G B tx_factor')
primals = [Vr_from, Vi_from, Vr_to, Vi_to] = symbols('V_from\,r V_from\,i V_to\,r V_to\,i')
duals = [Lr_from, Li_from, Lr_to, Li_to] = symbols('lambda_from\,r lambda_from\,i lambda_to\,r lambda_to\,i')

G = G_orig + TX_LARGE_G * G_orig * tx_factor
B = B_orig + TX_LARGE_B * B_orig * tx_factor

eqns = [
    G * Vr_from - G * Vr_to - B * Vi_from + B * Vi_to,
    G * Vi_from - G * Vi_to + B * Vr_from - B * Vr_to,
    G * Vr_to - G * Vr_from - B * Vi_to + B * Vi_from,
    G * Vi_to - G * Vi_from + B * Vr_to - B * Vr_from   
]

lagrange = np.dot(duals, eqns)

line_lh = LagrangeHandler(lagrange, constants, primals, duals)

def build_line_stamper_bus(from_bus: Bus, to_bus: Bus, optimization_enabled):
    return build_line_stamper(
        from_bus.node_Vr,
        from_bus.node_Vi,
        to_bus.node_Vr,
        to_bus.node_Vi,
        from_bus.node_lambda_Vr,
        from_bus.node_lambda_Vi,
        to_bus.node_lambda_Vr,
        to_bus.node_lambda_Vi,
        optimization_enabled
        )

def build_line_stamper(Vr_from_idx, Vi_from_idx, Vr_to_idx, Vi_to_idx, Lr_from_idx, Li_from_idx, Lr_to_idx, Li_to_idx, optimization_enabled):
    index_map = {}
    index_map[Vr_from] = Vr_from_idx
    index_map[Vi_from] = Vi_from_idx
    index_map[Vr_to] = Vr_to_idx
    index_map[Vi_to] = Vi_to_idx
    index_map[Lr_from] = Lr_from_idx
    index_map[Li_from] = Li_from_idx
    index_map[Lr_to] = Lr_to_idx
    index_map[Li_to] = Li_to_idx

    return LagrangeStamper(line_lh, index_map, optimization_enabled)

