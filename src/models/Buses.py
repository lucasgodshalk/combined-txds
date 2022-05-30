from __future__ import division
from itertools import count
import math
import typing
from lib.MatrixBuilder import MatrixBuilder

class Bus:
    def __init__(self,
                 Bus,
                 Type,
                 Vm_init,
                 Va_init,
                 Area):
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

        # initialize all nodes
        self.node_Vr: int # real voltage node at a bus
        self.node_Vi: int # imaginary voltage node at a bus
        self.node_Q: int # reactive power or voltage contstraint node at a bus

        self.node_Vr = None
        self.node_Vi = None
        self.node_Q = None

        self.Vr_init = Vm_init * math.cos(Va_init * math.pi / 180)
        self.Vi_init = Vm_init * math.sin(Va_init * math.pi / 180)

        # initialize the bus key
        self.idAllBuses = _idsAllBuses.__next__()
        _all_bus_key[self.Bus] = self

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

    def assign_nodes(self, node_index, infeasibility_analysis):
        self.node_Vr = next(node_index)
        self.node_Vi = next(node_index)

        # If PV Bus
        if self.Type == 2:
            self.node_Q = next(node_index)

        if not infeasibility_analysis:
            return

        self.node_lambda_Vr = next(node_index)
        self.node_lambda_Vi = next(node_index)

        self.node_Ir_inf = next(node_index)
        self.node_Ii_inf = next(node_index)

        # If PV Bus
        if self.Type == 2:
            self.node_lambda_Q = next(node_index)

    def stamp_primal_linear(self, Y: MatrixBuilder, J, tx_factor):
        #Infeasibility current KCL contribution
        Y.stamp(self.node_Vr, self.node_Ir_inf, 1)
        Y.stamp(self.node_Vi, self.node_Ii_inf, 1)

    def stamp_dual_linear(self, Y: MatrixBuilder, J, tx_factor):
        #dX portion
        Y.stamp(self.node_Ir_inf, self.node_lambda_Vr, 1)
        Y.stamp(self.node_Ii_inf, self.node_lambda_Vi, 1)

        #Objective function portion
        Y.stamp(self.node_Ir_inf, self.node_Ir_inf, 2)
        Y.stamp(self.node_Ii_inf, self.node_Ii_inf, 2)

_all_bus_key: typing.Dict[int, Bus]
_all_bus_key = {}
_idsAllBuses = count(1)
