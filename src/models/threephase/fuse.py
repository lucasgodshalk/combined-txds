from collections import defaultdict
from enum import Enum
from logic.matrixbuilder import MatrixBuilder
from models.helpers import merge_residuals
from models.singlephase.bus import Bus
from models.singlephase.line import build_line_stamper_bus
from models.threephase.edge import Edge
from models.singlephase.voltagesource import CurrentSensor

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

        self.current_sensor = CurrentSensor(self.interior_node, self.to_node)
        self.current_sensor.assign_nodes(node_index, optimization_enabled)

    def get_connections(self):
        if self.status == FuseStatus.BLOWN:
            return []

        return [(self.from_node, self.to_node)]

    def get_current(self, v):
        if self.status == FuseStatus.BLOWN:
            raise Exception("No current available for blown fuse")
        
        return self.current_sensor.get_current(v)

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        if self.status == FuseStatus.BLOWN:
            raise Exception("Blown fuses are not supported")

        self.line_stamper.stamp_primal(Y, J, [self.G, self.B, tx_factor], v_previous)
        self.current_sensor.stamp_primal(Y, J, v_previous, tx_factor, network)
    
    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        if self.status == FuseStatus.BLOWN:
            raise Exception("Blown fuses are not supported")

        self.line_stamper.stamp_dual(Y, J, [self.G, self.B, tx_factor], v_previous)
        self.current_sensor.stamp_dual(Y, J, v_previous, tx_factor, network)

    def calculate_residuals(self, state, v):
        if self.status == FuseStatus.BLOWN:
            raise Exception("Blown fuses are not supported")

        line_residuals = self.line_stamper.calc_residuals([self.G, self.B, 0], v)
        sensor_residuals = self.current_sensor.calculate_residuals(state, v)

        return merge_residuals({}, line_residuals, sensor_residuals)
