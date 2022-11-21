from typing import List
from sympy import symbols
from logic.stamping.lagrangesegment import LagrangeSegment
from logic.stamping.lagrangestampdetails import LagrangeStampDetails
from models.components.bus import Bus
from logic.stamping.matrixstamper import build_stamps_from_stamper

def load_infeasibility_analysis(network):
    return L2InfeasibilityOptimization(network.buses)

class L2InfeasibilityOptimization:
    def __init__(self, buses: List[Bus]) -> None:
        self.is_linear = True
        self.infeasibility_currents = []
        self.infeasibility_currents: List[L2InfeasibilityCurrent]

        for bus in buses:
            current = L2InfeasibilityCurrent(bus)
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
primals = [Iir, Iii] = symbols("Iir Iii")
duals = [Lr, Li] = symbols("lambda_Vr lambda_Vi")

lagrange = Iir ** 2 + Iii ** 2 + Iir * Lr + Iii * Li

lh = LagrangeSegment(lagrange, constants, primals, duals)

class L2InfeasibilityCurrent:
    def __init__(self, bus: Bus) -> None:
        self.bus = bus

    def assign_nodes(self, node_index):

        self.node_Ir_inf = next(node_index)
        self.node_Ii_inf = next(node_index)

        index_map = {}
        index_map[Iir] = self.node_Ir_inf
        index_map[Iii] = self.node_Ii_inf
        index_map[Lr] = self.bus.node_lambda_Vr
        index_map[Li] = self.bus.node_lambda_Vi

        self.stamper = LagrangeStampDetails(lh, index_map, optimization_enabled=True)

    def get_stamps(self):
        return build_stamps_from_stamper(self, self.stamper, [])

    def get_connections(self):
        return []