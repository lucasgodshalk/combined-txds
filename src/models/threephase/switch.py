from enum import Enum
from models.shared.bus import Bus
from models.shared.line import build_line_stamper_bus
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

        self.G = 1e4
        self.B = 1e4
        
    def assign_nodes(self, node_index, optimization_enabled):
        self.stamper = build_line_stamper_bus(self.from_node, self.to_node, optimization_enabled)

    def stamp_primal(self, Y, J, v_previous, tx_factor, state):
        # Don't stamp values if the switch is open
        if self.status == SwitchStatus.OPEN:
            return

        self.stamper.stamp_primal(Y, J, [self.G, self.B, tx_factor], v_previous)

    def stamp_dual(self, Y, J, v_previous, tx_factor, state):
        if self.status == SwitchStatus.OPEN:
            return

        self.stamper.stamp_dual(Y, J, [self.G, self.B, tx_factor], v_previous)
    
    def calculate_residuals(self, state, v):
        if self.status == SwitchStatus.OPEN:
            return {}
            
        return self.stamper.calc_residuals([self.G, self.B, 0], v)

