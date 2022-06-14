from __future__ import division
from itertools import count

from logic.matrixbuilder import MatrixBuilder
from models.positiveseq.buses import _all_bus_key
from models.positiveseq.shared import stamp_line

TX_LARGE_G = 20
TX_LARGE_B = 20

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

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        if not self.status:
            return

        (scaled_G, scaled_B, scaled_B_line) = self.get_scaled_conductances(tx_factor)
        
        Vr_from = self.from_bus.node_Vr
        Vi_from = self.from_bus.node_Vi

        Vr_to = self.to_bus.node_Vr
        Vi_to = self.to_bus.node_Vi

        stamp_line(Y, Vr_from, Vr_to, Vi_from, Vi_to, scaled_G, scaled_B)

        ###Shunt Current

        #From Bus - Real/Imaginary
        Y.stamp(Vr_from, Vi_from, -scaled_B_line)
        Y.stamp(Vi_from, Vr_from, scaled_B_line)

        #To Bus - Real/Imaginary
        Y.stamp(Vr_to, Vi_to, -scaled_B_line)
        Y.stamp(Vi_to, Vr_to, scaled_B_line)
    
    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        if not self.status:
            return
        
        (scaled_G, scaled_B, scaled_B_line) = self.get_scaled_conductances(tx_factor)

        Lambr_from = self.from_bus.node_lambda_Vr
        Lambi_from = self.from_bus.node_lambda_Vi

        Lambr_to = self.to_bus.node_lambda_Vr
        Lambi_to = self.to_bus.node_lambda_Vi

        stamp_line(Y, Lambr_from, Lambr_to, Lambi_from, Lambi_to, scaled_G, -scaled_B)

        #From Bus - Real/Imaginary
        Y.stamp(Lambr_from, Lambi_from, scaled_B_line)
        Y.stamp(Lambi_from, Lambr_from, -scaled_B_line)

        #To Bus - Real/Imaginary
        Y.stamp(Lambr_to, Lambi_to, scaled_B_line)
        Y.stamp(Lambi_to, Lambr_to, -scaled_B_line)
    
    def get_scaled_conductances(self, tx_factor):
        scaled_G = self.G + TX_LARGE_G * self.G * tx_factor
        scaled_B = self.B + TX_LARGE_B * self.B * tx_factor
        scaled_B_line = self.B_line * (1 - tx_factor)

        return (scaled_G, scaled_B, scaled_B_line)
    
    def calculate_residuals(self, network_model, v):
        return {}
        



