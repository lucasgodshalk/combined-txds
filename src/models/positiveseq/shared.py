import numpy as np
from sympy import symbols
from logic.lagrangehandler import LagrangeHandler
from logic.lagrangestamper import LagrangeStamper
from logic.matrixbuilder import MatrixBuilder

TX_LARGE_G = 20
TX_LARGE_B = 20

constants = G, B, tx_factor = symbols('G B tx_factor')
primals = [Vr_from, Vi_from, Vr_to, Vi_to] = symbols('V_from\,r V_from\,i V_to\,r V_to\,i')
duals = [Lr_from, Li_from, Lr_to, Li_to] = symbols('lambda_from\,r lambda_from\,i lambda_to\,r lambda_to\,i')

scaled_G = G + TX_LARGE_G * G * tx_factor
scaled_B = B + TX_LARGE_B * B * tx_factor

eqns = [
    scaled_G * Vr_from - scaled_G * Vr_to + scaled_B * Vi_from - scaled_B * Vi_to,
    scaled_G * Vi_from - scaled_G * Vi_to - scaled_B * Vr_from + scaled_B * Vr_to,
    scaled_G * Vr_to - scaled_G * Vr_from + scaled_B * Vi_to - scaled_B * Vi_from,
    scaled_G * Vi_to - scaled_G * Vi_from - scaled_B * Vr_to + scaled_B * Vr_from   
]

lagrange = np.dot(duals, eqns)

lh = LagrangeHandler(lagrange, constants, primals, duals)

def build_line_stamper(Vr_from_idx, Vi_from_idx, Vr_to_idx, Vi_to_idx, Lr_from_idx, Li_from_idx, Lr_to_idx, Li_to_idx):
    index_map = {}
    index_map[Vr_from] = Vr_from_idx
    index_map[Vi_from] = Vi_from_idx
    index_map[Vr_to] = Vr_to_idx
    index_map[Vi_to] = Vi_to_idx
    index_map[Lr_from] = Lr_from_idx
    index_map[Li_from] = Li_from_idx
    index_map[Lr_to] = Lr_to_idx
    index_map[Li_to] = Li_to_idx

    return LagrangeStamper(lh, index_map)


def stamp_line(Y: MatrixBuilder, Vr_from, Vr_to, Vi_from, Vi_to, G, B):
    #From Bus - Real
    Y.stamp(Vr_from, Vr_from, G)
    Y.stamp(Vr_from, Vr_to, -G)
    Y.stamp(Vr_from, Vi_from, B)
    Y.stamp(Vr_from, Vi_to, -B)

    #From Bus - Imaginary
    Y.stamp(Vi_from, Vi_from, G)
    Y.stamp(Vi_from, Vi_to, -G)
    Y.stamp(Vi_from, Vr_from, -B)
    Y.stamp(Vi_from, Vr_to, B)

    #To Bus - Real
    Y.stamp(Vr_to, Vr_to, G)
    Y.stamp(Vr_to, Vr_from, -G)
    Y.stamp(Vr_to, Vi_to, B)
    Y.stamp(Vr_to, Vi_from, -B)

    #To Bus - Imaginary
    Y.stamp(Vi_to, Vi_to, G)
    Y.stamp(Vi_to, Vi_from, -G)
    Y.stamp(Vi_to, Vr_to, -B)
    Y.stamp(Vi_to, Vr_from, B)

def dump_index_map(buses, slacks):
    map = {}

    for bus in buses:
        map[f'bus-{bus.Bus}-Vr'] = bus.node_Vr
        map[f'bus-{bus.Bus}-Vi'] = bus.node_Vi
        if bus.node_Q != None:
            map[f'bus-{bus.Bus}-Q'] = bus.node_Q
    
    for slack in slacks:
        map[f'slack-{slack.bus.Bus}-Ir'] = slack.slack_Ir
        map[f'slack-{slack.bus.Bus}-Ii'] = slack.slack_Ii

    return map

def dump_Y(Y):
    for idx_row in range(len(Y)):
        for idx_col in range(len(Y)):
            if Y[idx_row, idx_col] > 0:
                print(f'row: {idx_row}, col: {idx_col}, val:{Y[idx_row, idx_col]}')
