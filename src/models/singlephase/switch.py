from enum import Enum
from models.singlephase.bus import Bus
from models.singlephase.voltagesource import VoltageSource
from models.threephase.edge import Edge

class SwitchStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class Switch(Edge):

    def __init__(self
                , from_node: Bus
                , to_node: Bus
                , status: SwitchStatus
                , phase
                , edge_id = Edge._edge_ids.__next__()
                ):
        self.edge_id = edge_id
        self.status = status
        self.from_node = from_node
        self.to_node = to_node
        self.phase = phase

        self.vs = VoltageSource(from_node, to_node, 0, 0)
        
    def assign_nodes(self, node_index, optimization_enabled):
        if self.status == SwitchStatus.OPEN:
            return

        self.vs.assign_nodes(node_index, optimization_enabled)

    def get_connections(self):
        if self.status == SwitchStatus.OPEN:
            return []

        return [(self.from_node, self.to_node)]

    def stamp_primal(self, Y, J, v_previous, tx_factor, state):
        # Don't stamp values if the switch is open
        if self.status == SwitchStatus.OPEN:
            return

        self.vs.stamp_primal(Y, J, v_previous, tx_factor, state)

    def stamp_dual(self, Y, J, v_previous, tx_factor, state):
        if self.status == SwitchStatus.OPEN:
            return

        self.vs.stamp_dual(Y, J, v_previous, tx_factor, state)
    
    def calculate_residuals(self, state, v):
        if self.status == SwitchStatus.OPEN:
            return {}
            
        return self.vs.calculate_residuals(state, v)

