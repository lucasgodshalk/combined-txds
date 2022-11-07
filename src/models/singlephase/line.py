import numpy as np
from sympy import symbols
from itertools import count
from logic.stamping.lagrangesegment import LagrangeSegment
from logic.stamping.lagrangestampdetails import LagrangeStampDetails
from logic.stamping.matrixstamper import build_stamps_from_stampers
from models.singlephase.bus import Bus
from models.wellknownvariables import tx_factor

TX_LARGE_G = 20
TX_LARGE_B = 20

G_orig, B_orig = symbols('G B')
constants = G_orig, B_orig, tx_factor
primals = Vr_from, Vi_from, Vr_to, Vi_to = symbols('V_from\,r V_from\,i V_to\,r V_to\,i')
duals = Lr_from, Li_from, Lr_to, Li_to = symbols('lambda_from\,r lambda_from\,i lambda_to\,r lambda_to\,i')

G = G_orig + TX_LARGE_G * G_orig * tx_factor
B = B_orig + TX_LARGE_B * B_orig * tx_factor

eqns = [
    G * Vr_from - G * Vr_to - B * Vi_from + B * Vi_to,
    G * Vi_from - G * Vi_to + B * Vr_from - B * Vr_to,
    G * Vr_to - G * Vr_from - B * Vi_to + B * Vi_from,
    G * Vi_to - G * Vi_from + B * Vr_to - B * Vr_from   
]

lagrange = np.dot(duals, eqns)

line_lh = LagrangeSegment(lagrange, constants, primals, duals)

lagrange_no_tx_factor = lagrange.subs(tx_factor, 0)

line_lh_no_tx_factor = LagrangeSegment(lagrange_no_tx_factor, constants, primals, duals)

def build_line_stamper_bus(
    from_bus: Bus, 
    to_bus: Bus, 
    optimization_enabled,
    no_tx_factor = True
    ):
    return build_line_stamper(
        from_bus.node_Vr,
        from_bus.node_Vi,
        to_bus.node_Vr,
        to_bus.node_Vi,
        from_bus.node_lambda_Vr,
        from_bus.node_lambda_Vi,
        to_bus.node_lambda_Vr,
        to_bus.node_lambda_Vi,
        optimization_enabled,
        no_tx_factor
        )

def build_line_stamper(
    Vr_from_idx, 
    Vi_from_idx, 
    Vr_to_idx, 
    Vi_to_idx, 
    Lr_from_idx, 
    Li_from_idx, 
    Lr_to_idx, 
    Li_to_idx, 
    optimization_enabled,
    no_tx_factor = True
    ):
    index_map = {}
    index_map[Vr_from] = Vr_from_idx
    index_map[Vi_from] = Vi_from_idx
    index_map[Vr_to] = Vr_to_idx
    index_map[Vi_to] = Vi_to_idx
    index_map[Lr_from] = Lr_from_idx
    index_map[Li_from] = Li_from_idx
    index_map[Lr_to] = Lr_to_idx
    index_map[Li_to] = Li_to_idx

    if no_tx_factor:
        return LagrangeStampDetails(line_lh, index_map, optimization_enabled)
    else:
        return LagrangeStampDetails(line_lh_no_tx_factor, index_map, optimization_enabled)

constants = B_shunt, tx_factor = symbols('B_sh tx_factor')
primals = [Vr_from, Vi_from, Vr_to, Vi_to] = symbols('V_from\,r V_from\,i V_to\,r V_to\,i')
duals = [Lr_from, Li_from, Lr_to, Li_to] = symbols('lambda_from\,r lambda_from\,i lambda_to\,r lambda_to\,i')

scaled_B_line = B_shunt * (1 - tx_factor)

shunt_eqns = [
    -scaled_B_line * Vi_from,
    scaled_B_line * Vr_from,
    -scaled_B_line * Vi_to,
    scaled_B_line * Vr_to,    
]

lagrange = np.dot(duals, shunt_eqns)

shunt_lh = LagrangeSegment(lagrange, constants, primals, duals)

class Line:
    _ids = count(0)

    def __init__(self,
                 from_bus: Bus,
                 to_bus: Bus,
                 r,
                 x,
                 b,
                 status,
                 rateA,
                 rateB,
                 rateC):
                 
        self.id = self._ids.__next__()

        self.from_bus = from_bus
        self.to_bus = to_bus

        self.r = r
        self.x = x
        self.b = b

        self.G = r / (x ** 2 + r ** 2)
        self.B = -x / (x ** 2 + r ** 2)

        self.B_line = b / 2

        self.status = status

    def assign_nodes(self, node_index, optimization_enabled):
        self.line_stamper = build_line_stamper_bus(
            self.from_bus, 
            self.to_bus, 
            optimization_enabled
            )

        index_map = {}
        index_map[Vr_from] = self.from_bus.node_Vr
        index_map[Vi_from] = self.from_bus.node_Vi
        index_map[Vr_to] = self.to_bus.node_Vr
        index_map[Vi_to] = self.to_bus.node_Vi
        index_map[Lr_from] = self.from_bus.node_lambda_Vr
        index_map[Li_from] = self.from_bus.node_lambda_Vi
        index_map[Lr_to] = self.to_bus.node_lambda_Vr
        index_map[Li_to] = self.to_bus.node_lambda_Vi

        self.shunt_stamper = LagrangeStampDetails(shunt_lh, index_map, optimization_enabled)

    def get_connections(self):
        return [(self.from_bus, self.to_bus)]

    def get_stamps(self):
        return build_stamps_from_stampers(self, 
            (self.line_stamper, [self.G, self.B, 0]), 
            (self.shunt_stamper, [self.B_line, 0])
            )
