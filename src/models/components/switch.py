from enum import Enum
from models.components.bus import Bus
from models.components.voltagesource import VoltageSource

class SwitchStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class Switch():

    def __init__(self
                , from_node: Bus
                , to_node: Bus
                , status: SwitchStatus
                , phase
                ):
        self.status = status
        self.from_node = from_node
        self.to_node = to_node
        self.phase = phase

        self.vs = VoltageSource(from_node, to_node, 0, 0)
        
    def assign_nodes(self, node_index, optimization_enabled):
        if self.status == SwitchStatus.OPEN:
            return

        self.vs.assign_nodes(node_index, optimization_enabled)

    def get_stamps(self):
        if self.status == SwitchStatus.OPEN:
            return []
            
        return self.vs.get_stamps()

    def get_connections(self):
        if self.status == SwitchStatus.OPEN:
            return []

        return [(self.from_node, self.to_node)]