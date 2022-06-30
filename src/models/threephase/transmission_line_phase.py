from logic.networkmodel import DxNetworkModel
from models.threephase.edge import Edge

import numpy as np

class TransmissionLinePhase(Edge):

    def __init__(self
                , from_element
                , to_element
                , phase
                , edge_id = None
                ):
        super().__init__(edge_id)
        self.from_element = from_element
        self.to_element = to_element
        self.phase = phase
    
    def get_nodes(self, state: DxNetworkModel):
        from_bus = state.bus_name_map[self.from_element + "_" + self.phase]
        to_bus = state.bus_name_map[self.to_element + "_" + self.phase]
        return from_bus, to_bus
