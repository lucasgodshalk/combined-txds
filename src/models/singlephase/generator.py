from __future__ import division
from itertools import count
from sympy import symbols
from logic.stamping.lagrangesegment import LagrangeSegment
from logic.stamping.lagrangestamper import LagrangeStamper
from logic.stamping.matrixbuilder import MatrixBuilder
from models.singlephase.bus import Bus

constants = P, Vset = symbols('P V_set')
primals = Vr, Vi, Q = symbols('V_r V_i Q')
duals = Lr, Li, LQ = symbols('lambda_r lambda_i lambda_Q')

F_Vr = (P * Vr + Q * Vi) / (Vr ** 2 + Vi ** 2)
F_Vi = (P * Vi - Q * Vr) / (Vr ** 2 + Vi ** 2)
F_Q = Vset ** 2 - Vr ** 2 - Vi ** 2

lagrange = Lr * F_Vr + Li * F_Vi + LQ * F_Q

lh = LagrangeSegment(lagrange, constants, primals, duals)

class Generator:
    _ids = count(0)

    def __init__(self,
                 bus: Bus,
                 P,
                 Vset,
                 Qmax,
                 Qmin,
                 Pmax,
                 Pmin,
                 Qinit,
                 RemoteBus,
                 RMPCT,
                 gen_type):
        """Initialize an instance of a generator in the power grid.

        Args:
            Bus (int): the bus number where the generator is located.
            P (float): the current amount of active power the generator is providing.
            Vset (float): the voltage setpoint that the generator must remain fixed at.
            Qmax (float): maximum reactive power
            Qmin (float): minimum reactive power
            Pmax (float): maximum active power
            Pmin (float): minimum active power
            Qinit (float): the initial amount of reactive power that the generator is supplying or absorbing.
            RemoteBus (int): the remote bus that the generator is controlling
            RMPCT (float): the percent of total MVAR required to hand the voltage at the controlled bus
            gen_type (str): the type of generator
        """

        self.id = self._ids.__next__()

        self.bus = bus
        self.P = -P
        self.Vset = Vset

        self.Qinit = -Qinit

        self.Qmax = -Qmax
        self.Qmin = -Qmin

    def assign_nodes(self, node_index, optimization_enabled):
        index_map = {}
        index_map[Vr] = self.bus.node_Vr
        index_map[Vi] = self.bus.node_Vi
        index_map[Q] = self.bus.node_Q
        index_map[Lr] = self.bus.node_lambda_Vr
        index_map[Li] = self.bus.node_lambda_Vi
        index_map[LQ] = self.bus.node_lambda_Q

        self.stamper = LagrangeStamper(lh, index_map, optimization_enabled)

    def get_connections(self):
        return []

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        self.stamper.stamp_primal(Y, J, [self.P, self.Vset], v_previous)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        self.stamper.stamp_dual(Y, J, [self.P, self.Vset], v_previous)

    def calculate_residuals(self, network, v):
        return self.stamper.calc_residuals([self.P, self.Vset], v)