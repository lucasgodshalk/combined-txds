from __future__ import division
from itertools import count
import numpy as np
from sympy import symbols
from logic.lagrangehandler import LagrangeHandler
from logic.lagrangestamper import LagrangeStamper
from logic.matrixbuilder import MatrixBuilder
from models.shared.bus import Bus

constants = P, Q = symbols('P Q')
primals = Vr_from, Vi_from, Ir, Ii, Vr_to, Vi_to = symbols('Vr_from, Vi_from, Ir, Ii, Vr_to, Vi_to')
duals = Lr_from, Li_from, Lir, Lii, Lr_to, Li_to = symbols('Lr_from, Li_from, Lir, Lii, Lr_to, Li_to')

Vr = Vr_from - Vr_to
Vi = Vi_from - Vi_to

Fir_pq = (P * Vr + Q * Vi) / (Vr ** 2 + Vi ** 2)
Fii_pq = (P * Vi - Q * Vr) / (Vr ** 2 + Vi ** 2)

eqns = [
    Ir,
    Ii,
    Ir - Fir_pq,
    Ii - Fii_pq,
    -Ir,
    -Ii
]

lagrange = np.dot(duals, eqns)

lh = LagrangeHandler(lagrange, constants, primals, duals)

#Represents a positive sequence or single phase load.
class PQLoad:
    _ids = count(0)

    def __init__(self,
                 from_bus: Bus,
                 to_bus: Bus,
                 P,
                 Q,
                 IP,
                 IQ,
                 ZP,
                 ZQ,
                 area,
                 status):
        """Initialize an instance of a PQ or ZIP load in the power grid.

        Args:
            Bus (int): the bus where the load is located
            P (float): the active power of a constant power (PQ) load.
            Q (float): the reactive power of a constant power (PQ) load.
            IP (float): the active power component of a constant current load.
            IQ (float): the reactive power component of a constant current load.
            ZP (float): the active power component of a constant admittance load.
            ZQ (float): the reactive power component of a constant admittance load.
            area (int): location where the load is assigned to.
            status (bool): indicates if the load is in-service or out-of-service.
        """
        self.id = PQLoad._ids.__next__()

        self.from_bus = from_bus
        self.to_bus = to_bus
        self.P = P
        self.Q = Q

    def assign_nodes(self, node_index, optimization_enabled):
        index_map = {}
        index_map[Vr_from] = self.from_bus.node_Vr
        index_map[Vi_from] = self.from_bus.node_Vi
        index_map[Lr_from] = self.from_bus.node_lambda_Vr
        index_map[Li_from] = self.from_bus.node_lambda_Vi
        index_map[Vr_to] = self.to_bus.node_Vr
        index_map[Vi_to] = self.to_bus.node_Vi
        index_map[Lr_to] = self.to_bus.node_lambda_Vr
        index_map[Li_to] = self.to_bus.node_lambda_Vi
        index_map[Ir] = next(node_index)
        index_map[Ii] = next(node_index)

        self.stamper = LagrangeStamper(lh, index_map, optimization_enabled)

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        self.stamper.stamp_primal(Y, J, [self.P, self.Q], v_previous)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        self.stamper.stamp_dual(Y, J, [self.P, self.Q], v_previous)

    def calculate_residuals(self, network, v):
        return self.stamper.calc_residuals([self.P, self.Q], v)