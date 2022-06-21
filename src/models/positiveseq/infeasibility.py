from sympy import symbols
from logic.lagrangehandler import LagrangeHandler
from logic.lagrangestamper import LagrangeStamper
from logic.matrixbuilder import MatrixBuilder
from models.positiveseq.buses import Bus

constants = ()
primals = [Iir, Iii] = symbols("Iir Iii")
duals = [Lr, Li] = symbols("lambda_Vr lambda_Vi")

lagrange = Iir ** 2 + Iii ** 2 + Iir * Lr + Iii * Li

lh = LagrangeHandler(lagrange, constants, primals, duals)

class InfeasibilityCurrent:
    def __init__(self, bus: Bus) -> None:
        self.bus = bus

        self.stamper = None

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

        self.stamper = LagrangeStamper(lh, index_map)

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        self.stamper.stamp_primal(Y, J, [], v_previous)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        self.stamper.stamp_dual(Y, J, [], v_previous)

    def calculate_residuals(self, network_model, v):
        return {}