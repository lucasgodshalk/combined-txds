from __future__ import division
from itertools import count
import numpy as np
from sympy import symbols
from logic.lagrangehandler import LagrangeHandler
from logic.lagrangestamper import LagrangeStamper
from logic.matrixbuilder import MatrixBuilder
from models.positiveseq.buses import _all_bus_key
from models.positiveseq.shared import stamp_line

TX_LARGE_G = 20
TX_LARGE_B = 20

constants = G, B, B_line = symbols('G B B_line')
primals = [Vr_from, Vi_from, Vr_to, Vi_to] = symbols('V_from\,r V_from\,i V_to\,r V_to\,i')
duals = [Lr_from, Li_from, Lr_to, Li_to] = symbols('lambda_from\,r lambda_from\,i lambda_to\,r lambda_to\,i')

branch_eqns = [
    G * Vr_from - G * Vr_to + B * Vi_from - B * Vi_to,
    G * Vi_from - G * Vi_to - B * Vr_from + B * Vr_to,
    G * Vr_to - G * Vr_from + B * Vi_to - B * Vi_from,
    G * Vi_to - G * Vi_from - B * Vr_to + B * Vr_from   
]

lagrange = np.dot(duals, branch_eqns)

shunt_eqns = [
    -B_line * Vi_from,
    B_line * Vr_from,
    -B_line * Vi_to,
    B_line * Vr_to,    
]

lagrange += np.dot(duals, shunt_eqns)

lh = LagrangeHandler(lagrange, constants, primals, duals)

class Branches:
    _ids = count(0)

    def __init__(self,
                 from_bus,
                 to_bus,
                 r,
                 x,
                 b,
                 status,
                 rateA,
                 rateB,
                 rateC):
                 
        self.id = self._ids.__next__()

        self.from_bus = _all_bus_key[from_bus]
        self.to_bus = _all_bus_key[to_bus]

        self.r = r
        self.x = x
        self.b = b

        self.G = r / (x ** 2 + r ** 2)
        self.B = x / (x ** 2 + r ** 2)

        self.B_line = b / 2

        self.status = status

        self.stamper = None

    def try_build_stamper(self):
        if self.stamper != None:
            return
        
        #Somewhat counter-intuitive, but the row mapping is swapped for primals <-> duals
        row_map = {}
        row_map[Vr_from] = self.from_bus.node_lambda_Vr
        row_map[Vi_from] = self.from_bus.node_lambda_Vi
        row_map[Vr_to] = self.to_bus.node_lambda_Vr
        row_map[Vi_to] = self.to_bus.node_lambda_Vi
        row_map[Lr_from] = self.from_bus.node_Vr
        row_map[Li_from] = self.from_bus.node_Vi
        row_map[Lr_to] = self.to_bus.node_Vr
        row_map[Li_to] = self.to_bus.node_Vi

        col_map = {}
        col_map[Vr_from] = self.from_bus.node_Vr
        col_map[Vi_from] = self.from_bus.node_Vi
        col_map[Vr_to] = self.to_bus.node_Vr
        col_map[Vi_to] = self.to_bus.node_Vi
        col_map[Lr_from] = self.from_bus.node_lambda_Vr
        col_map[Li_from] = self.from_bus.node_lambda_Vi
        col_map[Lr_to] = self.to_bus.node_lambda_Vr
        col_map[Li_to] = self.to_bus.node_lambda_Vi

        self.stamper = LagrangeStamper(lh, row_map, col_map)

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        if not self.status:
            return

        (scaled_G, scaled_B, scaled_B_line) = self.get_scaled_conductances(tx_factor)
        
        self.try_build_stamper()
        self.stamper.stamp_primal(Y, J, [scaled_G, scaled_B, scaled_B_line], v_previous)
    
    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        if not self.status:
            return
        
        (scaled_G, scaled_B, scaled_B_line) = self.get_scaled_conductances(tx_factor)

        self.try_build_stamper()
        self.stamper.stamp_dual(Y, J, [scaled_G, scaled_B, scaled_B_line], v_previous)
    
    def get_scaled_conductances(self, tx_factor):
        scaled_G = self.G + TX_LARGE_G * self.G * tx_factor
        scaled_B = self.B + TX_LARGE_B * self.B * tx_factor
        scaled_B_line = self.B_line * (1 - tx_factor)

        return (scaled_G, scaled_B, scaled_B_line)
    
    def calculate_residuals(self, network_model, v):
        return {}
        



