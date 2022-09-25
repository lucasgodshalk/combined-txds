from typing import List
from sympy import symbols
from logic.lagrangesegment import LagrangeSegment
from logic.lagrangestamper import LagrangeStamper
from logic.matrixbuilder import MatrixBuilder
from models.helpers import merge_residuals
from models.singlephase.bus import Bus

class L2InfeasibilityOptimization:
    def __init__(self, buses: List[Bus]) -> None:
        self.is_linear = True
        self.infeasibility_currents = []

        for bus in buses:
            current = L2InfeasibilityCurrent(bus)
            self.infeasibility_currents.append(current)

    def assign_nodes(self, node_index, optimization_enabled):
        for infeas_current in self.infeasibility_currents:
            infeas_current.assign_nodes(node_index, optimization_enabled)

    def stamp(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        for inf_current in self.infeasibility_currents:
            inf_current.stamp_primal(Y, J, v_previous, tx_factor, network)
            inf_current.stamp_dual(Y, J, v_previous, tx_factor, network)

    def calculate_residuals(self, network, v):
        residuals = {}
        for inf_current in self.infeasibility_currents:
            merge_residuals(residuals, inf_current.calculate_residuals(network, v))
        
        return residuals

constants = ()
primals = [Iir, Iii] = symbols("Iir Iii")
duals = [Lr, Li] = symbols("lambda_Vr lambda_Vi")

lagrange = Iir ** 2 + Iii ** 2 + Iir * Lr + Iii * Li

lh = LagrangeSegment(lagrange, constants, primals, duals)

class L2InfeasibilityCurrent:
    def __init__(self, bus: Bus) -> None:
        self.bus = bus

    def assign_nodes(self, node_index, optimization_enabled):
        if not optimization_enabled:
            raise Exception("Cannot use infeasibility currents when optimization is not enabled")

        self.node_Ir_inf = next(node_index)
        self.node_Ii_inf = next(node_index)

        index_map = {}
        index_map[Iir] = self.node_Ir_inf
        index_map[Iii] = self.node_Ii_inf
        index_map[Lr] = self.bus.node_lambda_Vr
        index_map[Li] = self.bus.node_lambda_Vi

        self.stamper = LagrangeStamper(lh, index_map, optimization_enabled=True)

    def get_connections(self):
        return []

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        self.stamper.stamp_primal(Y, J, [], v_previous)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        self.stamper.stamp_dual(Y, J, [], v_previous)

    def calculate_residuals(self, network, v):
        return self.stamper.calc_residuals([], v)