from logic.matrixbuilder import MatrixBuilder
from models.positiveseq.buses import Bus


class InfeasibilityCurrent:
    def __init__(self, bus: Bus) -> None:
        self.bus = bus

    def assign_nodes(self, node_index, infeasibility_analysis):
        if not infeasibility_analysis:
            return

        self.node_Ir_inf = next(node_index)
        self.node_Ii_inf = next(node_index)

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        #Infeasibility current KCL contribution
        Y.stamp(self.bus.node_Vr, self.node_Ir_inf, 1)
        Y.stamp(self.bus.node_Vi, self.node_Ii_inf, 1)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        #dX portion
        Y.stamp(self.node_Ir_inf, self.bus.node_lambda_Vr, 1)
        Y.stamp(self.node_Ii_inf, self.bus.node_lambda_Vi, 1)

        #Objective function portion
        Y.stamp(self.node_Ir_inf, self.node_Ir_inf, 2)
        Y.stamp(self.node_Ii_inf, self.node_Ii_inf, 2)

    def calculate_residuals(self, network_model, v):
        return {}