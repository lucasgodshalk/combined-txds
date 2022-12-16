from sympy import symbols
import math
from logic.stamping.lagrangesegment import ModelEquations, KCL_r, KCL_i, Eq
from logic.stamping.lagrangestampdetails import build_model_stamp_details
from models.components.bus import GROUND, Bus
from logic.stamping.matrixstamper import build_stamps_from_stamper
from models.wellknownvariables import Vr_from, Vi_from, Vr_to, Vi_to

constants = Vrset, Viset = symbols("Vrset Viset")

I_sr, I_si = symbols("I_Sr I_Si")
variables = Vr_from, Vi_from, Vr_to, Vi_to, I_sr, I_si

Vr = Vr_from - Vr_to
Vi = Vi_from - Vi_to

kcl_r = KCL_r(I_sr)
kcl_i = KCL_i(I_si)
Vrset_eqn = Eq(Vr - Vrset)
Viset_eqn = Eq(Vi - Viset)

lh = ModelEquations(variables, constants, kcl_r, kcl_i, equalities=[Vrset_eqn, Viset_eqn])

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
        self.stamper = build_model_stamp_details(lh, self.bus, GROUND, node_index, optimization_enabled)

    def get_stamps(self):
        return build_stamps_from_stamper(self, self.stamper, [self.Vr_set, self.Vi_set])

    def get_slack_Ir_index(self):
        return self.stamper.get_var_col_index(I_sr)

    def get_slack_Ii_index(self):
        return self.stamper.get_var_col_index(I_si)

    def get_connections(self):
        return [(self.bus, GROUND)]
