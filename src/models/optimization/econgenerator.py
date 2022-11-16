from __future__ import division
from itertools import count
from sympy import symbols
from logic.stamping.lagrangesegment import LagrangeSegment
from logic.stamping.lagrangestampdetails import LagrangeStampDetails
from models.singlephase.bus import Bus
from logic.stamping.matrixstamper import build_stamps_from_stamper

def convert_inequality_to_barrier(F_ieq, mu_variable):
    return None

constants = c1, c2, Vset, P_min, P_max = symbols('c1 c2 V_set P_min P_max')
primals = Vr, Vi, P, Q = symbols('V_r V_i P Q')
duals = Lr, Li, LQ = symbols('lambda_r lambda_i lambda_Q')
mus = Mu_P_max, Mu_P_min = symbols('Mu_P_max Mu_P_min') 

F_Ir = (-P * Vr - Q * Vi) / (Vr ** 2 + Vi ** 2)
F_Ii = (-P * Vi + Q * Vr) / (Vr ** 2 + Vi ** 2)
F_Q = Vset ** 2 - Vr ** 2 - Vi ** 2

F_P_max = P - P_max
F_P_min = P_min - P

lagrange = c1 * P**2 + c2 * P + Lr * F_Ir + Li * F_Ii + LQ * F_Q + convert_inequality_to_barrier(F_P_max, Mu_P_max) + convert_inequality_to_barrier(F_P_min, Mu_P_min)

lh = LagrangeSegment(lagrange, constants, primals, duals, mus)

class EconGenerator:
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
        self.P = P
        self.Vset = Vset

        self.Qinit = Qinit

        self.Qmax = Qmax
        self.Qmin = Qmin

    def assign_nodes(self, node_index, optimization_enabled):
        index_map = {}
        index_map[Vr] = self.bus.node_Vr
        index_map[Vi] = self.bus.node_Vi
        index_map[Q] = self.bus.node_Q
        index_map[Lr] = self.bus.node_lambda_Vr
        index_map[Li] = self.bus.node_lambda_Vi
        index_map[LQ] = self.bus.node_lambda_Q

        self.stamper = LagrangeStampDetails(lh, index_map, optimization_enabled)

    def get_stamps(self):
        return build_stamps_from_stamper(self, self.stamper, [self.P, self.Vset])

    def get_connections(self):
        return []

