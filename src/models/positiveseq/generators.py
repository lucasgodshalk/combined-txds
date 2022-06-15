from __future__ import division
from itertools import count
from sympy import symbols
from logic.lagrangehandler import LagrangeHandler
from logic.lagrangestamper import LagrangeStamper
from logic.matrixbuilder import MatrixBuilder
from models.positiveseq.buses import _all_bus_key

constants = P, Vset = symbols('P V_set')
primals = Vr, Vi, Q = symbols('V_r V_i Q')
duals = Lr, Li, LQ = symbols('lambda_r lambda_i lambda_Q')

F_Vr = (P * Vr + Q * Vi) / (Vr ** 2 + Vi ** 2)
F_Vi = (P * Vi - Q * Vr) / (Vr ** 2 + Vi ** 2)
F_Q = Vset ** 2 - Vr ** 2 - Vi ** 2

lagrange = Lr * F_Vr + Li * F_Vi + LQ * F_Q

lh = LagrangeHandler(lagrange, constants, primals, duals)

class Generators:
    _ids = count(0)

    def __init__(self,
                 bus,
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

        self.bus = _all_bus_key[bus]
        self.P = -P / 100
        self.Vset = Vset

        self.Qinit = -Qinit / 100

        self.Qmax = -Qmax / 100
        self.Qmin = -Qmin / 100

        self.stamper = None

    def build_stamper(self):
        if self.stamper != None:
            return
        
        #Somewhat counter-intuitive, but the row mapping is swapped for primals <-> duals
        row_map = {}
        row_map[Vr] = self.bus.node_lambda_Vr
        row_map[Vi] = self.bus.node_lambda_Vi
        row_map[Q] = self.bus.node_lambda_Q
        row_map[Lr] = self.bus.node_Vr
        row_map[Li] = self.bus.node_Vi
        row_map[LQ] = self.bus.node_Q

        col_map = {}
        col_map[Vr] = self.bus.node_Vr
        col_map[Vi] = self.bus.node_Vi
        col_map[Q] = self.bus.node_Q
        col_map[Lr] = self.bus.node_lambda_Vr
        col_map[Li] = self.bus.node_lambda_Vi
        col_map[LQ] = self.bus.node_lambda_Q

        self.stamper = LagrangeStamper(lh, row_map, col_map)

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        self.build_stamper()

        Q_k = v_previous[self.bus.node_Q]
        Vr_k = v_previous[self.bus.node_Vr]
        Vi_k = v_previous[self.bus.node_Vi]

        self.stamper.stamp_primal(Y, J, (self.P, self.Vset), (Vr_k, Vi_k, Q_k), (0, 0, 0))

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        self.build_stamper()

        Q_k = v_previous[self.bus.node_Q]
        V_r = v_previous[self.bus.node_Vr]
        V_i = v_previous[self.bus.node_Vi]
        lambda_r = v_previous[self.bus.node_lambda_Vr]
        lambda_i = v_previous[self.bus.node_lambda_Vi]
        lambda_Q = v_previous[self.bus.node_lambda_Q]

        self.stamper.stamp_dual(Y, J, (self.P, self.Vset), (V_r, V_i, Q_k), (lambda_r, lambda_i, lambda_Q))

    def calculate_residuals(self, network_model, v):
        return {}

