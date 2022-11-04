from __future__ import division
import numpy as np
from sympy import symbols
from logic.stamping.lagrangesegment import LagrangeSegment
from logic.stamping.lagrangestamper import SKIP, LagrangeStamper
from logic.stamping.matrixbuilder import MatrixBuilder
import math
from models.singlephase.bus import GROUND, Bus
from logic.stamping.matrixstamper import build_stamps_from_stampers

constants = [Vrset, Viset] = symbols("Vrset Viset")

primals = [Vr, Vi, Isr, Isi] = symbols("Vr Vi I_Sr I_Si")

duals = [Lr, Li, Lsr, Lsi] = symbols("lambda_Vr lambda_Vi lambda_Sr lambda_Si")

eqns = [
    Isr,
    Isi,
    Vr - Vrset,
    Vi - Viset,
]

lagrange = np.dot(duals, eqns)

lh = LagrangeSegment(lagrange, constants, primals, duals)

class Slack:

    def __init__(self,
                 bus: Bus,
                 Vset,
                 ang,
                 Pinit,
                 Qinit):
        """Initialize slack bus in the power grid.

        Args:
            Bus (int): the bus number corresponding to the slack bus.
            Vset (float): the voltage setpoint that the slack bus must remain fixed at.
            ang (float): the slack bus voltage angle that it remains fixed at.
            Pinit (float): the initial active power that the slack bus is supplying
            Qinit (float): the initial reactive power that the slack bus is supplying
        """

        self.bus = bus
        self.bus.Type = 0
        self.Vset = Vset
        self.ang_rad = ang

        self.Vr_set = self.Vset * math.cos(self.ang_rad)
        self.Vi_set = self.Vset * math.sin(self.ang_rad)

        self.Pinit = Pinit / 100
        self.Qinit = Qinit / 100

    def assign_nodes(self, node_index, optimization_enabled):
        self.slack_Ir = next(node_index)
        self.slack_Ii = next(node_index)

        if optimization_enabled:
            self.slack_lambda_Ir = next(node_index)
            self.slack_lambda_Ii = next(node_index)
        else:
            self.slack_lambda_Ir = SKIP
            self.slack_lambda_Ii = SKIP

        index_map = {}
        index_map[Vr] = self.bus.node_Vr
        index_map[Vi] = self.bus.node_Vi
        index_map[Isr] = self.slack_Ir
        index_map[Isi] = self.slack_Ii
        index_map[Lr] = self.bus.node_lambda_Vr
        index_map[Li] = self.bus.node_lambda_Vi
        index_map[Lsr] = self.slack_lambda_Ir
        index_map[Lsi] = self.slack_lambda_Ii

        self.stamper = LagrangeStamper(lh, index_map, optimization_enabled)

    def get_stamps(self):
        return build_stamps_from_stampers(self, 
            (self.stamper, [self.Vr_set, self.Vi_set])
            )

    def get_connections(self):
        return [(self.bus, GROUND)]

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        self.stamper.stamp_primal(Y, J, [self.Vr_set, self.Vi_set], v_previous)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        self.stamper.stamp_dual(Y, J, [self.Vr_set, self.Vi_set], v_previous)

    def calculate_residuals(self, network, v):
        return self.stamper.calc_residuals([self.Vr_set, self.Vi_set], v)
