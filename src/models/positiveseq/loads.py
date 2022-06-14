from __future__ import division
from itertools import count
from logic.matrixbuilder import MatrixBuilder
from models.positiveseq.buses import _all_bus_key

def calculate_PQ_dIr_dVr(Vr, Vi, P, Q):
    return (P * (Vi**2 - Vr**2) - 2 * Q * Vr * Vi) / (Vr**2 + Vi**2)**2

def calculate_PQ_dIr_dVi(Vr, Vi, P, Q):
    return (Q * (Vr**2 - Vi**2) - 2 * P * Vr * Vi) / (Vr**2 + Vi**2)**2

class Loads:
    _ids = count(0)

    def __init__(self,
                 bus,
                 P,
                 Q,
                 IP,
                 IQ,
                 ZP,
                 ZQ,
                 area,
                 status):
        """Initialize an instance of a PQ or ZIP load in the power grid.

        Args:
            Bus (int): the bus where the load is located
            P (float): the active power of a constant power (PQ) load.
            Q (float): the reactive power of a constant power (PQ) load.
            IP (float): the active power component of a constant current load.
            IQ (float): the reactive power component of a constant current load.
            ZP (float): the active power component of a constant admittance load.
            ZQ (float): the reactive power component of a constant admittance load.
            area (int): location where the load is assigned to.
            status (bool): indicates if the load is in-service or out-of-service.
        """
        self.id = Loads._ids.__next__()

        self.bus = _all_bus_key[bus]
        self.P = P / 100
        self.Q = Q / 100
    
    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        Vr_k = v_previous[self.bus.node_Vr]
        Vi_k = v_previous[self.bus.node_Vi]

        # Real current
        dIr_dVr_k = calculate_PQ_dIr_dVr(Vr_k, Vi_k, self.P, self.Q)
        dIr_dVi_k = calculate_PQ_dIr_dVi(Vr_k, Vi_k, self.P, self.Q)

        Y.stamp(self.bus.node_Vr, self.bus.node_Vr, dIr_dVr_k)
        Y.stamp(self.bus.node_Vr, self.bus.node_Vi, dIr_dVi_k)

        Ir_k = (self.P * Vr_k + self.Q * Vi_k) / (Vr_k**2 + Vi_k**2)

        J[self.bus.node_Vr] += -Ir_k + dIr_dVr_k * Vr_k + dIr_dVi_k * Vi_k

        #Imaginary current
        dIi_dVr_k = dIr_dVi_k
        dIi_dVi_k = -dIr_dVr_k

        Ii_k = (self.P * Vi_k - self.Q * Vr_k) / (Vr_k**2 + Vi_k**2)

        Y.stamp(self.bus.node_Vi, self.bus.node_Vr, dIi_dVr_k)
        Y.stamp(self.bus.node_Vi, self.bus.node_Vi, dIi_dVi_k)

        J[self.bus.node_Vi] += -Ii_k + dIi_dVr_k * Vr_k + dIi_dVi_k * Vi_k
    
    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        V_r = v_previous[self.bus.node_Vr]
        V_i = v_previous[self.bus.node_Vi]
        lambda_r = v_previous[self.bus.node_lambda_Vr]
        lambda_i = v_previous[self.bus.node_lambda_Vi]

        #Real Lambda

        dVr_k = -2*V_r*lambda_i*(V_i*self.P - V_r*self.Q)/(V_i**2 + V_r**2)**2 - 2*V_r*lambda_r*(V_i*self.Q + V_r*self.P)/(V_i**2 + V_r**2)**2 - lambda_i*self.Q/(V_i**2 + V_r**2) + lambda_r*self.P/(V_i**2 + V_r**2)

        dVr_dVr_k = 8*V_r**2*lambda_i*(V_i*self.P - V_r*self.Q)/(V_i**2 + V_r**2)**3 + 8*V_r**2*lambda_r*(V_i*self.Q + V_r*self.P)/(V_i**2 + V_r**2)**3 + 4*V_r*lambda_i*self.Q/(V_i**2 + V_r**2)**2 - 4*V_r*lambda_r*self.P/(V_i**2 + V_r**2)**2 - 2*lambda_i*(V_i*self.P - V_r*self.Q)/(V_i**2 + V_r**2)**2 - 2*lambda_r*(V_i*self.Q + V_r*self.P)/(V_i**2 + V_r**2)**2

        dVr_dVi_k = 8*V_i*V_r*lambda_i*(V_i*self.P - V_r*self.Q)/(V_i**2 + V_r**2)**3 + 8*V_i*V_r*lambda_r*(V_i*self.Q + V_r*self.P)/(V_i**2 + V_r**2)**3 + 2*V_i*lambda_i*self.Q/(V_i**2 + V_r**2)**2 - 2*V_i*lambda_r*self.P/(V_i**2 + V_r**2)**2 - 2*V_r*lambda_i*self.P/(V_i**2 + V_r**2)**2 - 2*V_r*lambda_r*self.Q/(V_i**2 + V_r**2)**2

        dVr_dLr_k = -2*V_r*(V_i*self.Q + V_r*self.P)/(V_i**2 + V_r**2)**2 + self.P/(V_i**2 + V_r**2)

        dVr_dLi_k = -2*V_r*(V_i*self.P - V_r*self.Q)/(V_i**2 + V_r**2)**2 - self.Q/(V_i**2 + V_r**2)

        Y.stamp(self.bus.node_lambda_Vr, self.bus.node_Vr, dVr_dVr_k)
        Y.stamp(self.bus.node_lambda_Vr, self.bus.node_Vi, dVr_dVi_k)
        Y.stamp(self.bus.node_lambda_Vr, self.bus.node_lambda_Vr, dVr_dLr_k)
        Y.stamp(self.bus.node_lambda_Vr, self.bus.node_lambda_Vi, dVr_dLi_k)

        J[self.bus.node_lambda_Vr] += -dVr_k + dVr_dVr_k * V_r + dVr_dVi_k * V_i + dVr_dLr_k * lambda_r + dVr_dLi_k * lambda_i

        #Imaginary Lambda

        dVi_k = -2*V_i*lambda_i*(V_i*self.P - V_r*self.Q)/(V_i**2 + V_r**2)**2 - 2*V_i*lambda_r*(V_i*self.Q + V_r*self.P)/(V_i**2 + V_r**2)**2 + lambda_i*self.P/(V_i**2 + V_r**2) + lambda_r*self.Q/(V_i**2 + V_r**2)

        dVi_dVr_k = 8*V_i*V_r*lambda_i*(V_i*self.P - V_r*self.Q)/(V_i**2 + V_r**2)**3 + 8*V_i*V_r*lambda_r*(V_i*self.Q + V_r*self.P)/(V_i**2 + V_r**2)**3 + 2*V_i*lambda_i*self.Q/(V_i**2 + V_r**2)**2 - 2*V_i*lambda_r*self.P/(V_i**2 + V_r**2)**2 - 2*V_r*lambda_i*self.P/(V_i**2 + V_r**2)**2 - 2*V_r*lambda_r*self.Q/(V_i**2 + V_r**2)**2

        dVi_dVi_k = 8*V_i**2*lambda_i*(V_i*self.P - V_r*self.Q)/(V_i**2 + V_r**2)**3 + 8*V_i**2*lambda_r*(V_i*self.Q + V_r*self.P)/(V_i**2 + V_r**2)**3 - 4*V_i*lambda_i*self.P/(V_i**2 + V_r**2)**2 - 4*V_i*lambda_r*self.Q/(V_i**2 + V_r**2)**2 - 2*lambda_i*(V_i*self.P - V_r*self.Q)/(V_i**2 + V_r**2)**2 - 2*lambda_r*(V_i*self.Q + V_r*self.P)/(V_i**2 + V_r**2)**2

        dVi_dLr_k = -2*V_i*(V_i*self.Q + V_r*self.P)/(V_i**2 + V_r**2)**2 + self.Q/(V_i**2 + V_r**2)

        dVi_dLi_k = -2*V_i*(V_i*self.P - V_r*self.Q)/(V_i**2 + V_r**2)**2 + self.P/(V_i**2 + V_r**2)

        Y.stamp(self.bus.node_lambda_Vi, self.bus.node_Vr, dVi_dVr_k)
        Y.stamp(self.bus.node_lambda_Vi, self.bus.node_Vi, dVi_dVi_k)
        Y.stamp(self.bus.node_lambda_Vi, self.bus.node_lambda_Vr, dVi_dLr_k)
        Y.stamp(self.bus.node_lambda_Vi, self.bus.node_lambda_Vi, dVi_dLi_k)

        J[self.bus.node_lambda_Vi] += -dVi_k + dVi_dVr_k * V_r + dVi_dVi_k * V_i + dVi_dLr_k * lambda_r + dVi_dLi_k * lambda_i
