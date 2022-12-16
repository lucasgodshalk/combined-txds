from itertools import count
from sympy import symbols
from logic.stamping.lagrangesegment import SKIP, ModelEquations, KCL_r, KCL_i, Eq
from logic.stamping.lagrangestampdetails import build_model_stamp_details
from models.components.bus import GROUND, Bus
from logic.stamping.matrixstamper import build_stamps_from_stamper
from models.wellknownvariables import Vr_from, Vi_from, Vr_to, Vi_to

constants = P, Vset = symbols('P V_set')
Q = symbols('Q')
variables = Vr_from, Vi_from, Vr_to, Vi_to, Q

Vr = Vr_from - Vr_to
Vi = Vi_from - Vi_to

kcl_r = KCL_r((P * Vr + Q * Vi) / (Vr ** 2 + Vi ** 2))
kcl_i = KCL_i((P * Vi - Q * Vr) / (Vr ** 2 + Vi ** 2))
F_Q = Eq(Vset ** 2 - Vr ** 2 - Vi ** 2)

lh = ModelEquations(variables, constants, kcl_r, kcl_i, equalities=[F_Q])

class Generator:
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
        self.P = -P
        self.Vset = Vset

        self.Qinit = -Qinit

        self.Qmax = -Qmax
        self.Qmin = -Qmin

    def assign_nodes(self, node_index, optimization_enabled):
        self.stamper = build_model_stamp_details(lh, self.bus, GROUND, node_index, optimization_enabled)

    def get_LQ_init(self):
        return (self.stamper.get_lambda_index(4), 1e-4)

    def get_stamps(self):
        return build_stamps_from_stamper(self, self.stamper, [self.P, self.Vset])

    def get_connections(self):
        return []
    
    def get_Q_index(self):
        return self.stamper.get_var_col_index(Q)

