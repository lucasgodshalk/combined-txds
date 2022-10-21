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

#Eqns reference:
# Pandey, A. (2018). 
# Robust Steady-State Analysis of Power Grid using Equivalent Circuit Formulation with Circuit Simulation Methods

constants = P, Q = symbols('P, Q')
primals = Vr_from, Vi_from, Vr_to, Vi_to = symbols('Vr_from, Vi_from, Vr_to, Vi_to')
duals = Lr_from, Li_from, Lr_to, Li_to = symbols('Lr_from, Li_from, Lr_to, Li_to')

Vr = Vr_from - Vr_to
Vi = Vi_from - Vi_to

#Constant real & reactive power loads
#Eqn 25 & 26, pg 45
Fir_pq = (P * Vr + Q * Vi) / (Vr ** 2 + Vi ** 2)
Fii_pq = (P * Vi - Q * Vr) / (Vr ** 2 + Vi ** 2)

eqns = [
    Fir_pq,
    Fii_pq,
    -Fir_pq,
    -Fii_pq
]

lagrange_pq = np.dot(duals, eqns)

lh_pq = LagrangeSegment(lagrange_pq, constants, primals, duals)

#Constant current loads
#Eqn 31 & 32, pg 47

constants = Ic_mag, cos_Ipf, sin_Ipf = symbols('Ic_mag, cos_Ipf, sin_Ipf')

V_ratio = Vi/Vr
cos_arctan_V = 1 / (V_ratio**2 + 1)**0.5
sin_arctan_V = V_ratio / (V_ratio**2 + 1)**0.5

Fir_Ir = Ic_mag * (cos_arctan_V * cos_Ipf - sin_arctan_V * sin_Ipf)
Fir_Ii = Ic_mag * (sin_arctan_V * cos_Ipf + cos_arctan_V * sin_Ipf)

eqns = [
    Fir_Ir,
    Fir_Ii,
    -Fir_Ir,
    -Fir_Ii
]

lagrange_i = np.dot(duals, eqns)

lh_i = LagrangeSegment(lagrange_i, constants, primals, duals)

#Represents a two-terminal load. Can be used for positive sequence or three phase.
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
            IP (float): the active power component of a constant current load.
            IQ (float): the reactive power component of a constant current load.
        """

        self.id = Load._ids.__next__()
        self.load_num = load_num if load_num != None else str(self.id)
        self.phase = phase
        self.triplex_phase = triplex_phase

        self.from_bus = from_bus
        self.to_bus = to_bus
        self.P = P
        self.Q = Q
        self.Z = Z

        self.Ic_mag = np.sqrt(IP**2 + IQ**2)
        if IP == 0:
            self.cos_Ipf = 0
            self.sin_Ipf = 1
        else:
            self.cos_Ipf = np.cos(np.arctan(IQ/IP))
            self.sin_Ipf = np.sin(np.arctan(IQ/IP))

        if not self.Z == 0:
            r = np.real(self.Z)
            x = np.imag(self.Z)
            self.G = r / (r**2 + x**2)
            self.B = -x / (r**2 + x**2)
        else:
            self.G = 0
            self.B = 0

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

        if self.P == 0 and self.Q == 0:
            self.stamper_pq = None
        else:
            self.stamper_pq = LagrangeStamper(lh_pq, index_map, optimization_enabled)

        if self.Ic_mag == 0:
            self.stamper_i = None
        else:
            self.stamper_i = LagrangeStamper(lh_i, index_map, optimization_enabled)

        if self.Z == 0:
            self.stamper_z = None
        else:
            self.stamper_z = build_line_stamper_bus(self.from_bus, self.to_bus, optimization_enabled)

    def get_connections(self):
        return [(self.from_bus, self.to_bus)]

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        if self.stamper_pq != None:
            self.stamper_pq.stamp_primal(Y, J, [self.P, self.Q], v_previous)

        if self.stamper_i != None:
            self.stamper_i.stamp_primal(Y, J, [self.Ic_mag, self.cos_Ipf, self.sin_Ipf], v_previous)

        if self.stamper_z != None:
            self.stamper_z.stamp_primal(Y, J, [self.G, self.B, tx_factor], v_previous)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        if self.stamper_pq != None:
            self.stamper_pq.stamp_dual(Y, J, [self.P, self.Q], v_previous)

        if self.stamper_i != None:
            self.stamper_i.stamp_dual(Y, J, [self.Ic_mag, self.cos_Ipf, self.sin_Ipf], v_previous)

        if self.stamper_z != None:
            self.stamper_z.stamp_dual(Y, J, [self.G, self.B, tx_factor], v_previous)

    def calculate_residuals(self, network, v):
        if self.stamper_pq == None:
            pq_residuals = {}
        else:
            pq_residuals = self.stamper_pq.calc_residuals([self.P, self.Q], v)

        if self.stamper_i == None:
            zip_residuals = {}
        else:
            zip_residuals = self.stamper_i.calc_residuals([self.Ic_mag, self.cos_Ipf, self.sin_Ipf], v)

        if self.stamper_z == None:
            resistive_residuals = {}
        else:
            resistive_residuals = self.stamper_z.calc_residuals([self.G, self.B, 0], v)

        return merge_residuals({}, pq_residuals, zip_residuals, resistive_residuals)