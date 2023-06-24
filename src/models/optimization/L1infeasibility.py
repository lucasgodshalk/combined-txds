from typing import List
from sympy import symbols
from logic.stamping.lagrangesegment import LagrangeSegment
from logic.stamping.lagrangestampdetails import LagrangeStampDetails
from models.components.bus import Bus
from logic.stamping.matrixstamper import build_stamps_from_stamper

def load_infeasibility_analysis(network):
    return L1InfeasibilityOptimization(network.buses)

class L1InfeasibilityOptimization:
    def __init__(self, buses: List[Bus]) -> None:
        self.is_linear = True
        self.infeasibility_currents = []
        self.infeasibility_currents: List[L1InfeasibilityCurrent]

        for bus in buses:
            current = L1InfeasibilityCurrent(bus)
            self.infeasibility_currents.append(current)

    def assign_nodes(self, node_index, optimization_enabled):
        if not optimization_enabled:
            raise Exception("Cannot use infeasibility currents when optimization is not enabled")

        for infeas_current in self.infeasibility_currents:
            infeas_current.assign_nodes(node_index)

    def get_stamps(self):
        stamps = []
        for infeas_current in self.infeasibility_currents:
            stamps += infeas_current.get_stamps()
        return stamps

constants = ()
primals = [Vr, Vi, Iir_plus, Iii_plus, Iir_minus, Iii_minus] = symbols("Vr Vi Iir_plus Iii_plus Iir_minus Iii_minus")
duals = [Lr, Li, mu_Vr_plus, mu_Vi_plus, mu_Vr_minus, mu_Vi_minus] = symbols("lambda_Vr lambda_Vi mu_Vr_plus mu_Vi_plus mu_Vr_minus mu_Vi_minus")

lagrange = Iir_plus + Iii_plus + Iir_minus + Iii_minus \
    - Lr * (Iir_plus - Iir_minus) - Li * (Iii_plus - Iii_minus) \
    + mu_Vr_plus * Iir_plus + mu_Vr_minus * Iir_minus \
    + mu_Vi_plus * Iii_plus + mu_Vi_minus * Iii_minus

lh = LagrangeSegment(lagrange, constants, primals, duals)

class L1InfeasibilityCurrent:
    def __init__(self, bus: Bus) -> None:
        self.bus = bus

    def assign_nodes(self, node_index):

        self.node_Ir_plus_inf = next(node_index)
        self.node_Ii_plus_inf = next(node_index)
        self.node_Ir_minus_inf = next(node_index)
        self.node_Ii_minus_inf = next(node_index)

        index_map = {}
        index_map[Iir_plus] = self.node_Ir_plus_inf
        index_map[Iii_plus] = self.node_Ii_plus_inf
        index_map[Iir_minus] = self.node_Ir_minus_inf
        index_map[Iii_minus] = self.node_Ii_minus_inf
        index_map[mu_Vr_plus] = self.node_Ir_plus_inf
        index_map[mu_Vi_plus] = self.node_Ii_plus_inf
        index_map[mu_Vr_minus] = self.node_Ir_minus_inf
        index_map[mu_Vi_minus] = self.node_Ii_minus_inf
        index_map[Lr] = self.bus.node_lambda_Vr
        index_map[Li] = self.bus.node_lambda_Vi
        index_map[Vr] = self.bus.node_Vr
        index_map[Vi] = self.bus.node_Vi

        self.stamper = LagrangeStampDetails(lh, index_map, optimization_enabled=True)

    def get_stamps(self):
        return build_stamps_from_stamper(self, self.stamper, [])

    def get_connections(self):
        return []