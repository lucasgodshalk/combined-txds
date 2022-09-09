from __future__ import division
from itertools import count
import numpy as np
from sympy import symbols
from logic.lagrangesegment import LagrangeSegment
from logic.lagrangestamper import SKIP, LagrangeStamper
from logic.matrixbuilder import MatrixBuilder
from models.helpers import merge_residuals
from models.singlephase.bus import Bus
from models.singlephase.line import build_line_stamper_bus

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

lh = LagrangeSegment(lagrange, constants, primals, duals)

#Represents a positive sequence or single phase load.
class Load:
    _ids = count(0)

    def __init__(self,
                 from_bus: Bus,
                 to_bus: Bus,
                 P,
                 Q,
                 Z,
                 IP,
                 IQ,
                 ZP,
                 ZQ,
                 load_num=None,
                 phase=None,
                 triplex_phase=None
                 ):
        """Initialize an instance of a PQ or ZIP load in the power grid.

        Args:
            Bus (int): the bus where the load is located
            P (float): the active power of a constant power (PQ) load.
            Q (float): the reactive power of a constant power (PQ) load.
            Z (complex): the linear impedance of the load.
            IP (float): the active power component of a constant current load. [Not implemented]
            IQ (float): the reactive power component of a constant current load. [Not implemented]
            ZP (float): the active power component of a constant admittance load. [Not implemented]
            ZQ (float): the reactive power component of a constant admittance load. [Not implemented]
        """
        self.id = Load._ids.__next__()
        self.load_num = load_num
        self.phase = phase
        self.triplex_phase = triplex_phase

        self.from_bus = from_bus
        self.to_bus = to_bus
        self.P = P
        self.Q = Q
        self.Z = Z

        if not self.Z == 0:
            r = np.real(self.Z)
            x = np.imag(self.Z)
            self.G = r / (r**2 + x**2)
            self.B = -x / (r**2 + x**2)
        else:
            self.G = 0
            self.B = 0

    def assign_nodes(self, node_index, optimization_enabled):
        self.node_Ir = next(node_index)
        self.node_Ii = next(node_index)

        index_map = {}
        index_map[Vr_from] = self.from_bus.node_Vr
        index_map[Vi_from] = self.from_bus.node_Vi
        index_map[Lr_from] = self.from_bus.node_lambda_Vr
        index_map[Li_from] = self.from_bus.node_lambda_Vi
        index_map[Vr_to] = self.to_bus.node_Vr
        index_map[Vi_to] = self.to_bus.node_Vi
        index_map[Lr_to] = self.to_bus.node_lambda_Vr
        index_map[Li_to] = self.to_bus.node_lambda_Vi
        index_map[Ir] = self.node_Ir
        index_map[Ii] = self.node_Ii
        if optimization_enabled:
            index_map[Lir] = next(node_index)
            index_map[Lii] = next(node_index)
        else:
            index_map[Lir] = SKIP
            index_map[Lii] = SKIP

        self.stamper = LagrangeStamper(lh, index_map, optimization_enabled)

        if self.Z == 0:
            self.resistive_stamper = None
        else:
            self.resistive_stamper = build_line_stamper_bus(self.from_bus, self.to_bus, optimization_enabled)

    def get_connections(self):
        return [(self.from_bus, self.to_bus)]

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        self.stamper.stamp_primal(Y, J, [self.P, self.Q], v_previous)

        if self.resistive_stamper != None:
            self.resistive_stamper.stamp_primal(Y, J, [self.G, self.B, tx_factor], v_previous)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        self.stamper.stamp_dual(Y, J, [self.P, self.Q], v_previous)

        if self.resistive_stamper != None:
            self.resistive_stamper.stamp_dual(Y, J, [self.G, self.B, tx_factor], v_previous)

    def calculate_residuals(self, network, v):
        pq_residuals = self.stamper.calc_residuals([self.P, self.Q], v)

        if self.resistive_stamper == None:
            resistive_residuals = {}
        else:
            resistive_residuals = self.resistive_stamper.calc_residuals([self.G, self.B, 0], v)

        return merge_residuals({}, pq_residuals, resistive_residuals)