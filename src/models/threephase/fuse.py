from collections import defaultdict
from enum import Enum
from logic.matrixbuilder import MatrixBuilder
from models.shared.bus import Bus
from models.shared.line import build_line_stamper_bus
from models.threephase.edge import Edge
from models.shared.voltagesource import VoltageSource

import numpy as np

class FuseStatus(Enum):
    GOOD = "GOOD"
    BLOWN = "BLOWN"

class Fuse(Edge):

    def __init__(self
                , from_node: Bus
                , to_node: Bus
                , interior_node: Bus
                , current_limit
                , status: FuseStatus
                , phase
                , edge_id = Edge._edge_ids.__next__()
                ):
        self.edge_id = edge_id
        self.current_limit = current_limit
        self.status = status
        self.from_node = from_node
        self.to_node = to_node
        self.interior_node = interior_node
        self.phase = phase
        self.G = 1e4
        self.B = 1e4
    
    def assign_nodes(self, node_index, optimization_enabled):
        self.line_stamper = build_line_stamper_bus(self.from_node, self.interior_node, optimization_enabled)

        self.interior_vs = VoltageSource(self.interior_node, self.to_node, 0, 0)
        self.interior_vs.assign_nodes(node_index, optimization_enabled)

    def get_current(self, v):
        if self.status == FuseStatus.BLOWN:
            raise Exception("No current available for blown fuse")
        
        return self.interior_vs.get_current(v)

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        if self.status == FuseStatus.BLOWN:
            raise Exception("Blown fuses are not supported")

        self.line_stamper.stamp_primal(Y, J, [self.G, self.B, tx_factor], v_previous)
        self.interior_vs.stamp_primal(Y, J, v_previous, tx_factor, network_model)
    
    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        if self.status == FuseStatus.BLOWN:
            raise Exception("Blown fuses are not supported")

        self.line_stamper.stamp_dual(Y, J, [self.G, self.B, tx_factor], v_previous)
        self.interior_vs.stamp_dual(Y, J, v_previous, tx_factor, network_model)

    def calculate_residuals(self, state, v):
        if self.status == FuseStatus.BLOWN:
            raise Exception("Blown fuses are not supported")

        residuals = defaultdict(lambda: 0)

        for (key, value) in self.line_stamper.calc_residuals([self.G, self.B, 0], v).items():
            residuals[key] += value
        
        for (key, value) in self.interior_vs.calculate_residuals(state, v).items():
            residuals[key] += value

        return residuals
