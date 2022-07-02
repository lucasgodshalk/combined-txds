from __future__ import division
from itertools import count

from sympy import symbols
from logic.lagrangehandler import LagrangeHandler
from logic.lagrangestamper import LagrangeStamper
from logic.matrixbuilder import MatrixBuilder
from models.shared.bus import Bus

constants = P, Q = symbols('P Q')
primals = Vr, Vi = symbols('V_r V_i')
duals = Lr, Li = symbols('lambda_r lambda_i')

F_Ir = (P * Vr + Q * Vi) / (Vr ** 2 + Vi ** 2)
F_Ii = (P * Vi - Q * Vr) / (Vr ** 2 + Vi ** 2)

lagrange = Lr * F_Ir + Li * F_Ii

lh = LagrangeHandler(lagrange, constants, primals, duals)

#Represents a positive sequence or single phase load.
class PQLoad:
    _ids = count(0)

    def __init__(self,
                 bus: Bus,
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

        self.bus = bus
        self.P = P / 100
        self.Q = Q / 100

    def assign_nodes(self, node_index, optimization_enabled):
        index_map = {}
        index_map[Vr] = self.bus.node_Vr
        index_map[Vi] = self.bus.node_Vi
        index_map[Lr] = self.bus.node_lambda_Vr
        index_map[Li] = self.bus.node_lambda_Vi

        self.stamper = LagrangeStamper(lh, index_map, optimization_enabled)

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        self.stamper.stamp_primal(Y, J, [self.P, self.Q], v_previous)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        self.stamper.stamp_dual(Y, J, [self.P, self.Q], v_previous)

    def calculate_residuals(self, network_model, v):
        return self.stamper.calc_residuals([self.P, self.Q], v)