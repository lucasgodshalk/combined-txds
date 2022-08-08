import math
import numpy as np

from logic.matrixbuilder import MatrixBuilder
from models.shared.line import build_line_stamper_bus

# A toy class which models a load as a simple resistor
class ResistiveLoad():
    def __init__(self, from_bus, to_bus, Z):
        self.from_bus = from_bus
        self.to_bus = to_bus

        self.Z = Z
        self.R = np.real(self.Z)
        self.X = np.imag(self.Z)
        self.G = self.R / (self.R**2 + self.X**2)
        self.B = -self.X / (self.R**2 + self.X**2)
        
    def assign_nodes(self, node_index, optimization_enabled):
        self.stamper = build_line_stamper_bus(self.from_bus, self.to_bus, optimization_enabled)

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        self.stamper.stamp_primal(Y, J, [self.G, self.B, tx_factor], v_previous)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        self.stamper.stamp_dual(Y, J, [self.G, self.B, tx_factor], v_previous)

    def calculate_residuals(self, network, v):
        return self.stamper.calc_residuals([self.G, self.B, 0], v)

