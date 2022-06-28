from logic.lagrangestamper import LagrangeStamper
from logic.matrixbuilder import MatrixBuilder
from logic.networkmodel import DxNetworkModel
from models.threephase.bus import Bus
from models.positiveseq.infeasibility import Iir, Iii, Lr, Li, lh

#Injects infeasibility currents at a bus (note that each bus represents a single phase)
class InfeasibilityCurrent:
    def __init__(self, bus: Bus) -> None:
        self.bus = bus
    
    def assign_nodes(self, network_model: DxNetworkModel, optimization_enabled):
        if not optimization_enabled:
            raise Exception("Cannot use infeasibility currents when optimization is not enabled")

        self.node_Ir_inf = next(network_model.next_var_idx)
        self.node_Ii_inf = next(network_model.next_var_idx)
        network_model.J_length += 2

        index_map = {}
        index_map[Iir] = self.node_Ir_inf
        index_map[Iii] = self.node_Ii_inf
        index_map[Lr] = self.bus.node_lambda_Vr
        index_map[Li] = self.bus.node_lambda_Vi

        self.stamper = LagrangeStamper(lh, index_map, optimization_enabled=True)

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        self.stamper.stamp_primal(Y, J, [], v_previous)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        self.stamper.stamp_dual(Y, J, [], v_previous)

    def calculate_residuals(self, network_model, v):
        return {}