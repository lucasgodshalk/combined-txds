from __future__ import division
from itertools import count
from logic.matrixbuilder import MatrixBuilder
from models.positiveseq.buses import _all_bus_key
from models.positiveseq.loads import calculate_PQ_dIr_dVi, calculate_PQ_dIr_dVr

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

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        Q_k = v_previous[self.bus.node_Q]
        Vr_k = v_previous[self.bus.node_Vr]
        Vi_k = v_previous[self.bus.node_Vi]

        #Real current
        dIr_dQ_k = Vi_k / (Vr_k ** 2 + Vi_k ** 2)
        dIr_dVr_k = calculate_PQ_dIr_dVr(Vr_k, Vi_k, self.P, Q_k)
        dIr_dVi_k = calculate_PQ_dIr_dVi(Vr_k, Vi_k, self.P, Q_k)

        Y.stamp(self.bus.node_Vr, self.bus.node_Q, dIr_dQ_k)
        Y.stamp(self.bus.node_Vr, self.bus.node_Vr, dIr_dVr_k)
        Y.stamp(self.bus.node_Vr, self.bus.node_Vi, dIr_dVi_k)

        Ir_k = (self.P * Vr_k + Q_k * Vi_k) / (Vr_k ** 2 + Vi_k ** 2)

        J[self.bus.node_Vr] += -Ir_k + dIr_dQ_k * Q_k + dIr_dVr_k * Vr_k + dIr_dVi_k * Vi_k

        #Imaginary current
        dIi_dQ_k = -Vr_k / (Vr_k ** 2 + Vi_k ** 2)
        dIi_dVr_k = dIr_dVi_k
        dIi_dVi_k = -dIr_dVr_k

        Y.stamp(self.bus.node_Vi, self.bus.node_Q, dIi_dQ_k)
        Y.stamp(self.bus.node_Vi, self.bus.node_Vr, dIi_dVr_k)
        Y.stamp(self.bus.node_Vi, self.bus.node_Vi, dIi_dVi_k)

        Ii_k = (self.P * Vi_k - Q_k * Vr_k) / (Vr_k ** 2 + Vi_k ** 2)

        J[self.bus.node_Vi] += -Ii_k + dIi_dQ_k * Q_k + dIi_dVr_k * Vr_k + dIi_dVi_k * Vi_k

        #Vset equation
        dVset_dVr = -2 * Vr_k
        dVset_dVi = -2 * Vi_k

        Y.stamp(self.bus.node_Q, self.bus.node_Vr, dVset_dVr)
        Y.stamp(self.bus.node_Q, self.bus.node_Vi, dVset_dVi)

        VSet_k = self.Vset ** 2 - Vr_k ** 2 - Vi_k ** 2

        J[self.bus.node_Q] += -VSet_k + dVset_dVr * Vr_k + dVset_dVi * Vi_k

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        Q = v_previous[self.bus.node_Q]
        V_r = v_previous[self.bus.node_Vr]
        V_i = v_previous[self.bus.node_Vi]
        lambda_r = v_previous[self.bus.node_lambda_Vr]
        lambda_i = v_previous[self.bus.node_lambda_Vi]
        lambda_Q = v_previous[self.bus.node_lambda_Q]

        #Real Lambda

        dVr_k = -Q*lambda_i/(V_i**2 + V_r**2) - 2*V_r*lambda_Q - 2*V_r*lambda_i*(-Q*V_r + V_i*self.P)/(V_i**2 + V_r**2)**2 - 2*V_r*lambda_r*(Q*V_i + V_r*self.P)/(V_i**2 + V_r**2)**2 + lambda_r*self.P/(V_i**2 + V_r**2)

        dVr_dVr_k = 4*Q*V_r*lambda_i/(V_i**2 + V_r**2)**2 + 8*V_r**2*lambda_i*(-Q*V_r + V_i*self.P)/(V_i**2 + V_r**2)**3 + 8*V_r**2*lambda_r*(Q*V_i + V_r*self.P)/(V_i**2 + V_r**2)**3 - 4*V_r*lambda_r*self.P/(V_i**2 + V_r**2)**2 - 2*lambda_Q - 2*lambda_i*(-Q*V_r + V_i*self.P)/(V_i**2 + V_r**2)**2 - 2*lambda_r*(Q*V_i + V_r*self.P)/(V_i**2 + V_r**2)**2

        dVr_dVi_k = 2*Q*V_i*lambda_i/(V_i**2 + V_r**2)**2 - 2*Q*V_r*lambda_r/(V_i**2 + V_r**2)**2 + 8*V_i*V_r*lambda_i*(-Q*V_r + V_i*self.P)/(V_i**2 + V_r**2)**3 + 8*V_i*V_r*lambda_r*(Q*V_i + V_r*self.P)/(V_i**2 + V_r**2)**3 - 2*V_i*lambda_r*self.P/(V_i**2 + V_r**2)**2 - 2*V_r*lambda_i*self.P/(V_i**2 + V_r**2)**2

        dVr_dQ_k = -2*V_i*V_r*lambda_r/(V_i**2 + V_r**2)**2 + 2*V_r**2*lambda_i/(V_i**2 + V_r**2)**2 - lambda_i/(V_i**2 + V_r**2)

        dVr_dLr_k = -2*V_r*(Q*V_i + V_r*self.P)/(V_i**2 + V_r**2)**2 + self.P/(V_i**2 + V_r**2)

        dVr_dLi_k = -Q/(V_i**2 + V_r**2) - 2*V_r*(-Q*V_r + V_i*self.P)/(V_i**2 + V_r**2)**2

        dVr_dLQ_k = -2*V_r

        Y.stamp(self.bus.node_lambda_Vr, self.bus.node_Vr, dVr_dVr_k)
        Y.stamp(self.bus.node_lambda_Vr, self.bus.node_Vi, dVr_dVi_k)
        Y.stamp(self.bus.node_lambda_Vr, self.bus.node_Q, dVr_dQ_k)
        Y.stamp(self.bus.node_lambda_Vr, self.bus.node_lambda_Vr, dVr_dLr_k)
        Y.stamp(self.bus.node_lambda_Vr, self.bus.node_lambda_Vi, dVr_dLi_k)
        Y.stamp(self.bus.node_lambda_Vr, self.bus.node_lambda_Q, dVr_dLQ_k)

        J[self.bus.node_lambda_Vr] += -dVr_k + dVr_dVr_k * V_r + dVr_dVi_k * V_i + dVr_dQ_k * Q + dVr_dLr_k * lambda_r + dVr_dLi_k * lambda_i + dVr_dLQ_k * lambda_Q

        #Imaginary Lambda
        
        dVi_k = Q*lambda_r/(V_i**2 + V_r**2) - 2*V_i*lambda_Q - 2*V_i*lambda_i*(-Q*V_r + V_i*self.P)/(V_i**2 + V_r**2)**2 - 2*V_i*lambda_r*(Q*V_i + V_r*self.P)/(V_i**2 + V_r**2)**2 + lambda_i*self.P/(V_i**2 + V_r**2)

        dVi_dVr_k = 2*Q*V_i*lambda_i/(V_i**2 + V_r**2)**2 - 2*Q*V_r*lambda_r/(V_i**2 + V_r**2)**2 + 8*V_i*V_r*lambda_i*(-Q*V_r + V_i*self.P)/(V_i**2 + V_r**2)**3 + 8*V_i*V_r*lambda_r*(Q*V_i + V_r*self.P)/(V_i**2 + V_r**2)**3 - 2*V_i*lambda_r*self.P/(V_i**2 + V_r**2)**2 - 2*V_r*lambda_i*self.P/(V_i**2 + V_r**2)**2

        dVi_dVi_k = -4*Q*V_i*lambda_r/(V_i**2 + V_r**2)**2 + 8*V_i**2*lambda_i*(-Q*V_r + V_i*self.P)/(V_i**2 + V_r**2)**3 + 8*V_i**2*lambda_r*(Q*V_i + V_r*self.P)/(V_i**2 + V_r**2)**3 - 4*V_i*lambda_i*self.P/(V_i**2 + V_r**2)**2 - 2*lambda_Q - 2*lambda_i*(-Q*V_r + V_i*self.P)/(V_i**2 + V_r**2)**2 - 2*lambda_r*(Q*V_i + V_r*self.P)/(V_i**2 + V_r**2)**2

        dVi_dQ_k = -2*V_i**2*lambda_r/(V_i**2 + V_r**2)**2 + 2*V_i*V_r*lambda_i/(V_i**2 + V_r**2)**2 + lambda_r/(V_i**2 + V_r**2)

        dVi_dLr_k = Q/(V_i**2 + V_r**2) - 2*V_i*(Q*V_i + V_r*self.P)/(V_i**2 + V_r**2)**2

        dVi_dLi_k = -2*V_i*(-Q*V_r + V_i*self.P)/(V_i**2 + V_r**2)**2 + self.P/(V_i**2 + V_r**2)

        dVi_dLQ_k = -2*V_i

        Y.stamp(self.bus.node_lambda_Vi, self.bus.node_Vr, dVi_dVr_k)
        Y.stamp(self.bus.node_lambda_Vi, self.bus.node_Vi, dVi_dVi_k)
        Y.stamp(self.bus.node_lambda_Vi, self.bus.node_Q, dVi_dQ_k)
        Y.stamp(self.bus.node_lambda_Vi, self.bus.node_lambda_Vr, dVi_dLr_k)
        Y.stamp(self.bus.node_lambda_Vi, self.bus.node_lambda_Vi, dVi_dLi_k)
        Y.stamp(self.bus.node_lambda_Vi, self.bus.node_lambda_Q, dVi_dLQ_k)

        J[self.bus.node_lambda_Vi] += -dVi_k + dVi_dVr_k * V_r + dVi_dVi_k * V_i + dVi_dQ_k * Q + dVi_dLr_k * lambda_r + dVi_dLi_k * lambda_i + dVi_dLQ_k * lambda_Q

        # Vset Lambda

        dQ_k = V_i*lambda_r/(V_i**2 + V_r**2) - V_r*lambda_i/(V_i**2 + V_r**2)

        dQ_dVr_k = -2*V_i*V_r*lambda_r/(V_i**2 + V_r**2)**2 + 2*V_r**2*lambda_i/(V_i**2 + V_r**2)**2 - lambda_i/(V_i**2 + V_r**2)

        dQ_dVi_k = -2*V_i**2*lambda_r/(V_i**2 + V_r**2)**2 + 2*V_i*V_r*lambda_i/(V_i**2 + V_r**2)**2 + lambda_r/(V_i**2 + V_r**2)

        dQ_dLr_k = V_i/(V_i**2 + V_r**2)

        dQ_dLi_k = -V_r/(V_i**2 + V_r**2)

        Y.stamp(self.bus.node_lambda_Q, self.bus.node_Vr, dQ_dVr_k)
        Y.stamp(self.bus.node_lambda_Q, self.bus.node_Vi, dQ_dVi_k)
        Y.stamp(self.bus.node_lambda_Q, self.bus.node_lambda_Vr, dQ_dLr_k)
        Y.stamp(self.bus.node_lambda_Q, self.bus.node_lambda_Vi, dQ_dLi_k)

        J[self.bus.node_lambda_Q] += -dQ_k + dQ_dVr_k * V_r + dQ_dVi_k * V_i + dQ_dLr_k * lambda_r + dQ_dLi_k * lambda_i

    def calculate_residuals(self, network_model, v):
        return {}
