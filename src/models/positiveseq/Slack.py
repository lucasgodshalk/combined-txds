from __future__ import division
from logic.MatrixBuilder import MatrixBuilder
from models.positiveseq.Buses import _all_bus_key
import math

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

    def assign_nodes(self, node_index, infeasibility_analysis):
        self.slack_Ir = next(node_index)
        self.slack_Ii = next(node_index)

        if infeasibility_analysis:
            self.slack_lambda_Ir = next(node_index)
            self.slack_lambda_Ii = next(node_index)

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        #Slack currents in KCL
        Y.stamp(self.bus.node_Vr, self.slack_Ir, 1)
        Y.stamp(self.bus.node_Vi, self.slack_Ii, 1)

        #Vset eqns
        Y.stamp(self.slack_Ir, self.bus.node_Vr, 1)
        J[self.slack_Ir] = self.Vr_set

        Y.stamp(self.slack_Ii, self.bus.node_Vi, 1)
        J[self.slack_Ii] = self.Vi_set

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        #dVr & dVi
        Y.stamp(self.bus.node_lambda_Vr, self.slack_lambda_Ir, 1)
        Y.stamp(self.bus.node_lambda_Vi, self.slack_lambda_Ii, 1)

        #dIsr & dIsi
        Y.stamp(self.slack_lambda_Ir, self.bus.node_lambda_Vr, 1)
        Y.stamp(self.slack_lambda_Ii, self.bus.node_lambda_Vi, 1)


