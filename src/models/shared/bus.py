from __future__ import division
from itertools import count
import math
import typing
from logic.lagrangestamper import SKIP

class Bus:
    def __init__(self,
                 Bus,
                 Type,
                 Vm_init,
                 Va_init,
                 Area,
                 NodeName = None,
                 NodePhase = None):
        """Initialize an instance of the Buses class.

        Args:
            Bus (int): The bus number.
            Type (int): The type of bus (e.g., PV, PQ, of Slack)
            Vm_init (float): The initial voltage magnitude at the bus.
            Va_init (float): The initial voltage angle at the bus.
            Area (int): The zone that the bus is in.
        """

        self.Bus = Bus
        self.Type = Type
        self.NodeName = NodeName
        self.NodePhase = NodePhase

        # initialize all nodes
        self.node_Vr: int # real voltage node at a bus
        self.node_Vi: int # imaginary voltage node at a bus
        self.node_Q: int # reactive power or voltage contstraint node at a bus

        self.node_Vr = None
        self.node_Vi = None
        self.node_Q = None

        self.Vr_init = Vm_init * math.cos(Va_init * math.pi / 180)
        self.Vi_init = Vm_init * math.sin(Va_init * math.pi / 180)

    def set_initial_voltages(self, v_estimate):
        f_r, f_i = (self.node_Vr, self.node_Vi)
        v_estimate[f_r] = self.Vr_init if v_estimate[f_r] == 0 else v_estimate[f_r]
        v_estimate[f_i] = self.Vi_init if v_estimate[f_i] == 0 else v_estimate[f_i]

    def __str__(self):
        return_string = 'The bus number is : {} with Vr node as: {} and Vi node as {} '.format(self.Bus,
                                                                                               self.node_Vr,
                                                                                               self.node_Vi)
        return return_string

    def get_Vr_init(self):
        return (self.node_Vr, self.Vr_init)

    def get_Vi_init(self):
        return (self.node_Vi, self.Vi_init)

    def get_Lr_init(self):
        return (self.node_lambda_Vr, 1e-4)

    def get_Li_init(self):
        return (self.node_lambda_Vr, 1e-4)

    def get_LQ_init(self):
        if self.Type == 2:
            return (self.node_lambda_Q, 1e-4)
        else:
            return (None, None)

    def assign_nodes(self, node_index, optimization_enabled):
        self.node_Vr = next(node_index)
        self.node_Vi = next(node_index)

        # If PV Bus
        if self.Type == 2:
            self.node_Q = next(node_index)

        if optimization_enabled:
            self.node_lambda_Vr = next(node_index)
            self.node_lambda_Vi = next(node_index)

            # If PV Bus
            if self.Type == 2:
                self.node_lambda_Q = next(node_index)
        else:
            self.node_lambda_Vr = SKIP
            self.node_lambda_Vi = SKIP
            self.node_lambda_Q = SKIP

