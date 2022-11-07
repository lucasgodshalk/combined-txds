from enum import Enum
from models.singlephase.bus import Bus
from models.singlephase.line import build_line_stamper_bus
from models.singlephase.voltagesource import CurrentSensor
from logic.stamping.matrixstamper import build_stamps_from_stamper

import numpy as np

class FuseStatus(Enum):
    GOOD = "GOOD"
    BLOWN = "BLOWN"

class Fuse():

    def __init__(self
                , from_node: Bus
                , to_node: Bus
                , interior_node: Bus
                , current_limit
                , status: FuseStatus
                , phase
                ):
        self.current_limit = current_limit
        self.status = status
        self.from_node = from_node
        self.to_node = to_node
        self.interior_node = interior_node
        self.phase = phase
        self.G = 1e4
        self.B = 1e4
    
    def assign_nodes(self, node_index, optimization_enabled):
        self.line_stamper = build_line_stamper_bus(self.from_node, self.interior_node, optimization_enabled, no_tx_factor=False)

        self.current_sensor = CurrentSensor(self.interior_node, self.to_node)
        self.current_sensor.assign_nodes(node_index, optimization_enabled)

    def get_connections(self):
        if self.status == FuseStatus.BLOWN:
            return []

        return [(self.from_node, self.to_node)]

    def get_stamps(self):
        if self.status == FuseStatus.BLOWN:
            raise Exception("Blown fuses are not supported")

        return build_stamps_from_stamper(self, self.line_stamper, [self.G, self.B, 0]) + self.current_sensor.get_stamps()

    def get_current(self, v):
        if self.status == FuseStatus.BLOWN:
            raise Exception("No current available for blown fuse")
        
        return self.current_sensor.get_current(v)

    def try_adjust_device(self, v):
        if self.status == FuseStatus.BLOWN:
            #We assume that once a fuse is blown, we will never un-blow it.
            return False

        i_r, i_i = self.get_current(v)
        i = complex(i_r, i_i)
        if abs(i) > self.current_limit:
            self.status = FuseStatus.BLOWN
            return True
    
        return False
