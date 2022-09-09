import numpy as np
from sympy import symbols
from logic.lagrangesegment import LagrangeSegment
from logic.lagrangestamper import SKIP, LagrangeStamper
from logic.matrixbuilder import MatrixBuilder
from models.singlephase.bus import Bus

constants = Vr_set, Vi_set = symbols("Vr_set Vi_set")
primals = Vr_from, Vi_from, Vr_to, Vi_to, Ir, Ii = symbols('Vr_from Vi_from Vr_to Vi_to Ir Ii')
duals = Lr_from, Li_from, Lr_to, Li_to, Lir, Lii = symbols('Lr_from Li_from Lr_to Li_to Lir Lii')

eqns = [
    Ir,
    Ii,
    -Ir,
    -Ii,
    Vr_set - (Vr_from - Vr_to),
    Vi_set - (Vi_from - Vi_to)
]

lagrange = np.dot(duals, eqns)

lh = LagrangeSegment(lagrange, constants, primals, duals)

class VoltageSource:
    def __init__(self, from_bus: Bus, to_bus: Bus, Vr_set, Vi_set) -> None:
        self.from_bus = from_bus
        self.to_bus = to_bus
        self.Vr_set = Vr_set
        self.Vi_set = Vi_set

    def assign_nodes(self, node_index, optimization_enabled):
        self.Ir_index = next(node_index)
        self.Ii_index = next(node_index)

        if optimization_enabled:
            self.Lir_index = next(node_index)
            self.Lii_index = next(node_index)
        else:
            self.Lir_index = SKIP
            self.Lii_index = SKIP

        index_map = {}

        index_map[Vr_from] = self.from_bus.node_Vr
        index_map[Vi_from] = self.from_bus.node_Vi
        index_map[Vr_to] = self.to_bus.node_Vr
        index_map[Vi_to] = self.to_bus.node_Vi
        index_map[Ir] = self.Ir_index
        index_map[Ii] = self.Ii_index

        index_map[Lr_from] = self.from_bus.node_lambda_Vr
        index_map[Li_from] = self.from_bus.node_lambda_Vi
        index_map[Lr_to] = self.to_bus.node_lambda_Vr
        index_map[Li_to] = self.to_bus.node_lambda_Vi
        index_map[Lir] = self.Lir_index
        index_map[Lii] = self.Lii_index

        self.stamper = LagrangeStamper(lh, index_map, optimization_enabled)

    def get_connections(self):
        return [(self.from_bus, self.to_bus)]

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, state):
        self.stamper.stamp_primal(Y, J, [self.Vr_set, self.Vi_set], v_previous)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        self.stamper.stamp_dual(Y, J, [self.Vr_set, self.Vi_set], v_previous)

    def calculate_residuals(self, state, v):
        return self.stamper.calc_residuals([self.Vr_set, self.Vi_set], v)
    
    def get_current(self, v):
        return (v[self.Ir_index], v[self.Ii_index])
    
#Glorified voltage source, just a better name for readability sometimes.
class CurrentSensor(VoltageSource):
    def __init__(self, from_bus: Bus, to_bus: Bus) -> None:
        VoltageSource.__init__(self, from_bus, to_bus, 0, 0)