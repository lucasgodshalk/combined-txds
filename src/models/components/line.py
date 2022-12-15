import numpy as np
from sympy import symbols
from itertools import count
from logic.stamping.lagrangesegment import LagrangeSegment, ModelEquations, KCL_r, KCL_i
from logic.stamping.lagrangestampdetails import LagrangeStampDetails
from logic.stamping.matrixstamper import build_stamps_from_stampers
from models.components.bus import Bus, GROUND
from models.wellknownvariables import tx_factor, Vr_from, Vi_from, Vr_to, Vi_to, Lr_from, Li_from, Lr_to, Li_to

TX_LARGE_G = 20
TX_LARGE_B = 20

G_orig, B_orig = symbols('G B')
constants = G_orig, B_orig, tx_factor
variables = Vr_from, Vi_from, Vr_to, Vi_to

G = G_orig + TX_LARGE_G * G_orig * tx_factor
B = B_orig + TX_LARGE_B * B_orig * tx_factor

kcl_r = KCL_r(G * Vr_from - G * Vr_to - B * Vi_from + B * Vi_to)
kcl_i = KCL_i(G * Vi_from - G * Vi_to + B * Vr_from - B * Vr_to)  

line_lh = ModelEquations(variables, constants, kcl_r, kcl_i)

# The only distinction between shunt and line impedance behavior
# is that when the homotopy factor is at 1,
# we expect line impedance to go to [large number]
# and the shunt impedance to go to 0

G = G_orig * (1 - tx_factor)
B = B_orig * (1 - tx_factor)

kcl_r = KCL_r(G * Vr_from - G * Vr_to - B * Vi_from + B * Vi_to)
kcl_i = KCL_i(G * Vi_from - G * Vi_to + B * Vr_from - B * Vr_to)  

shunt_lh = ModelEquations(variables, constants, kcl_r, kcl_i)

def build_line_stamper_bus(
    from_bus: Bus, 
    to_bus: Bus, 
    optimization_enabled,
    is_shunt = False
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
        is_shunt
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
    is_shunt = False
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

    if is_shunt:
        return LagrangeStampDetails(shunt_lh, index_map, optimization_enabled)
    else:
        return LagrangeStampDetails(line_lh, index_map, optimization_enabled)

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

        self.shunt_stamper_from = build_line_stamper_bus(
            self.from_bus,
            GROUND,
            optimization_enabled,
            is_shunt=True
            )

        self.shunt_stamper_to = build_line_stamper_bus(
            self.to_bus,
            GROUND,
            optimization_enabled,
            is_shunt=True
            )

    def get_connections(self):
        return [(self.from_bus, self.to_bus)]

    def get_stamps(self):
        return build_stamps_from_stampers(self, 
            (self.line_stamper, [self.G, self.B, 0]), 
            (self.shunt_stamper_from, [0, self.B_line, 0]),
            (self.shunt_stamper_to, [0, self.B_line, 0])
            )
