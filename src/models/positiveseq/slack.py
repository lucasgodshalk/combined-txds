from __future__ import division
import numpy as np
from sympy import symbols
from logic.lagrangehandler import LagrangeHandler
from logic.lagrangestamper import LagrangeStamper
from logic.matrixbuilder import MatrixBuilder
from models.positiveseq.buses import _all_bus_key
import math

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

lh = LagrangeHandler(lagrange, constants, primals, duals)

class Slack:

    def __init__(self,
                 bus,
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

        self.bus = _all_bus_key[bus]
        self.Vset = Vset
        self.ang_rad = ang * math.pi / 180

        self.Vr_set = self.Vset * math.cos(self.ang_rad)
        self.Vi_set = self.Vset * math.sin(self.ang_rad)

        self.Pinit = Pinit / 100
        self.Qinit = Qinit / 100

        self.stamper = None

    def try_build_stamper(self):
        if self.stamper != None:
            return
        
        #Somewhat counter-intuitive, but the row mapping is swapped for primals <-> duals
        row_map = {}
        row_map[Vr] = self.bus.node_lambda_Vr
        row_map[Vi] = self.bus.node_lambda_Vi
        row_map[Isr] = self.slack_lambda_Ir
        row_map[Isi] = self.slack_lambda_Ii
        row_map[Lr] = self.bus.node_Vr
        row_map[Li] = self.bus.node_Vi
        row_map[Lsr] = self.slack_Ir
        row_map[Lsi] = self.slack_Ii

        col_map = {}
        col_map[Vr] = self.bus.node_Vr
        col_map[Vi] = self.bus.node_Vi
        col_map[Isr] = self.slack_Ir
        col_map[Isi] = self.slack_Ii
        col_map[Lr] = self.bus.node_lambda_Vr
        col_map[Li] = self.bus.node_lambda_Vi
        col_map[Lsr] = self.slack_lambda_Ir
        col_map[Lsi] = self.slack_lambda_Ii

        self.stamper = LagrangeStamper(lh, row_map, col_map)

    def assign_nodes(self, node_index, optimization_enabled):
        self.slack_Ir = next(node_index)
        self.slack_Ii = next(node_index)

        if optimization_enabled:
            self.slack_lambda_Ir = next(node_index)
            self.slack_lambda_Ii = next(node_index)

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        self.try_build_stamper()
        self.stamper.stamp_primal(Y, J, [self.Vr_set, self.Vi_set], v_previous)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        self.try_build_stamper()
        self.stamper.stamp_dual(Y, J, [self.Vr_set, self.Vi_set], v_previous)

    def calculate_residuals(self, network_model, v):
        return {}
