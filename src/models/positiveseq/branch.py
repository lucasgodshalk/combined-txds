from __future__ import division
from collections import defaultdict
from itertools import count
import numpy as np
from sympy import symbols
from logic.lagrangehandler import LagrangeHandler
from logic.lagrangestamper import LagrangeStamper
from logic.matrixbuilder import MatrixBuilder
from models.shared.line import build_line_stamper_bus
from models.shared.bus import Bus

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

shunt_lh = LagrangeHandler(lagrange, constants, primals, duals)

class Branch:
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

        self.shunt_stamper = LagrangeStamper(shunt_lh, index_map, optimization_enabled)

    def get_connections(self):
        return [(self.from_bus, self.to_bus)]

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        if not self.status:
            return

        self.line_stamper.stamp_primal(Y, J, [self.G, self.B, tx_factor], v_previous)
        self.shunt_stamper.stamp_primal(Y, J, [self.B_line, tx_factor], v_previous)
    
    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        if not self.status:
            return
        
        self.line_stamper.stamp_dual(Y, J, [self.G, self.B, tx_factor], v_previous)
        self.shunt_stamper.stamp_dual(Y, J, [self.B_line, tx_factor], v_previous)
    
    def calculate_residuals(self, network_model, v):
        residuals = defaultdict(lambda: 0)

        for (key, value) in self.line_stamper.calc_residuals([self.G, self.B, 0], v).items():
            residuals[key] += value

        for (key, value) in self.shunt_stamper.calc_residuals([self.B_line, 0], v).items():
            residuals[key] += value
        
        return residuals
        

