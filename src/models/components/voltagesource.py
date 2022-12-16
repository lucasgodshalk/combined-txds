from sympy import symbols
from logic.stamping.lagrangesegment import Eq, KCL_i, KCL_r, TwoTerminalModelDefinition
from logic.stamping.lagrangestampdetails import build_two_terminal_stamp_details
from models.components.bus import Bus
from logic.stamping.matrixstamper import build_stamps_from_stamper
from models.wellknownvariables import Vr_from, Vi_from, Vr_to, Vi_to

Ir, Ii = symbols('Ir Ii')
Lir, Lii = symbols('Lir Lii')

constants = Vr_set, Vi_set = symbols("Vr_set Vi_set")
variables = Vr_from, Vi_from, Vr_to, Vi_to, Ir, Ii

kcl_r = KCL_r(Ir)
kcl_i = KCL_i(Ii)

Vset_r_eqn = Eq(Vr_set - (Vr_from - Vr_to))
Vset_i_eqn = Eq(Vi_set - (Vi_from - Vi_to))

lh = TwoTerminalModelDefinition(variables, constants, kcl_r, kcl_i, equalities=[Vset_r_eqn, Vset_i_eqn])

class VoltageSource:
    def __init__(self, from_bus: Bus, to_bus: Bus, Vr_set, Vi_set) -> None:
        self.from_bus = from_bus
        self.to_bus = to_bus
        self.Vr_set = Vr_set
        self.Vi_set = Vi_set

    def assign_nodes(self, node_index, optimization_enabled):
        self.stamper = build_two_terminal_stamp_details(lh, self.from_bus, self.to_bus, node_index, optimization_enabled)

    def get_connections(self):
        return [(self.from_bus, self.to_bus)]

    def get_stamps(self):
        return build_stamps_from_stamper(self, self.stamper, [self.Vr_set, self.Vi_set])

    def get_current(self, v):
        return (self.stamper.get_var_value(v, Ir), self.stamper.get_var_value(v, Ii))
    
#Glorified voltage source, just a better name for readability sometimes.
class CurrentSensor(VoltageSource):
    def __init__(self, from_bus: Bus, to_bus: Bus) -> None:
        VoltageSource.__init__(self, from_bus, to_bus, 0, 0)