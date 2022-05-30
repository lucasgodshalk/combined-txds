from __future__ import division
from itertools import count
from lib.MatrixBuilder import MatrixBuilder
from models.Buses import _all_bus_key

class Shunts:
    _ids = count(0)

    def __init__(self,
                 bus,
                 G_MW,
                 B_MVAR,
                 shunt_type,
                 Vhi,
                 Vlo,
                 Bmax,
                 Bmin,
                 Binit,
                 controlBus,
                 flag_control_shunt_bus=False,
                 Nsteps=[0],
                 Bstep=[0]):

        """ Initialize a shunt in the power grid.
        Args:
            Bus (int): the bus where the shunt is located
            G_MW (float): the active component of the shunt admittance as MW per unit voltage
            B_MVAR (float): reactive component of the shunt admittance as  MVar per unit voltage
            shunt_type (int): the shunt control mode, if switched shunt
            Vhi (float): if switched shunt, the upper voltage limit
            Vlo (float): if switched shunt, the lower voltage limit
            Bmax (float): the maximum shunt susceptance possible if it is a switched shunt
            Bmin (float): the minimum shunt susceptance possible if it is a switched shunt
            Binit (float): the initial switched shunt susceptance
            controlBus (int): the bus that the shunt controls if applicable
            flag_control_shunt_bus (bool): flag that indicates if the shunt should be controlling another bus
            Nsteps (list): the number of steps by which the switched shunt should adjust itself
            Bstep (list): the admittance increase for each step in Nstep as MVar at unity voltage
        """
        self.id = self._ids.__next__()
        self.bus = _all_bus_key[bus]

        self.G = G_MW / 100
        self.B = B_MVAR / 100

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        (scaled_G, scaled_B) = self.get_scaled_conductances(tx_factor)

        #Real
        Y.stamp(self.bus.node_Vr, self.bus.node_Vr, scaled_G)
        Y.stamp(self.bus.node_Vr, self.bus.node_Vi, -scaled_B)

        #Imaginary
        Y.stamp(self.bus.node_Vi, self.bus.node_Vr, scaled_B)
        Y.stamp(self.bus.node_Vi, self.bus.node_Vi, scaled_G)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        (scaled_G, scaled_B) = self.get_scaled_conductances(tx_factor)

        #Real
        Y.stamp(self.bus.node_lambda_Vr, self.bus.node_lambda_Vr, scaled_G)
        Y.stamp(self.bus.node_lambda_Vr, self.bus.node_lambda_Vi, scaled_B)

        #Imaginary
        Y.stamp(self.bus.node_lambda_Vi, self.bus.node_lambda_Vr, -scaled_B)
        Y.stamp(self.bus.node_lambda_Vi, self.bus.node_lambda_Vi, scaled_G)

    def get_scaled_conductances(self, tx_factor):
        scaled_G = self.G * (1 - tx_factor)
        scaled_B = self.B * (1 - tx_factor)

        return (scaled_G, scaled_B)
