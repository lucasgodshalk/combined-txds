from enum import Enum
import math
from logic.matrixbuilder import MatrixBuilder
from models.shared.bus import GROUND, Bus
from models.shared.transformer import Transformer

class RegControl(Enum):
    MANUAL = "MANUAL"
    REMOTE_NODE = "REMOTE_NODE"
    OUTPUT_VOLTAGE = "OUTPUT_VOLTAGE"
    LINE_DROP_COMP = "LINE_DROP_COMP"

class Regulator():
    
    def __init__(self
                , from_node: Bus 
                , to_node: Bus
                , phase
                , tap_position
                , ar_step
                , reg_type
                , reg_control: RegControl
                ):
        self.from_node = from_node
        self.to_node = to_node
        self.phase = phase
        self.ar_step = ar_step
        self.reg_type = reg_type
        self.reg_control = reg_control

        #this is temporary before we update the tap position for the first time.
        self.turn_ratio = 0

        #todo: is this correct?
        self.phase_shift = 0 

        #todo: pull better values?
        r = 1e4
        x = 0

        self.transformer = Transformer(
            self.from_node, 
            GROUND, 
            self.to_node, 
            GROUND,
            r,
            x,
            True,
            self.turn_ratio,
            self.phase_shift,
            0,
            0,
            None
            )

        self.update_tap_position(tap_position)

    def update_tap_position(self, tap_position):
        #todo: the regulator position needs to be updated by the device controller according to reg behavior.

        self.tap_position = tap_position

        if self.reg_type == "A":
            self.turn_ratio = (1 + (self.ar_step * self.tap_position)) ** -1
        else:
            self.turn_ratio = 1 - (self.ar_step * self.tap_position)
        
        self.transformer.tr = self.turn_ratio

    def assign_nodes(self, node_index, optimization_enabled):
        self.transformer.assign_nodes(node_index, optimization_enabled)

    def stamp_primal(self, Y, J, v, tx_factor, state):
        self.transformer.stamp_primal(Y, J, v, tx_factor, state)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, state):
        self.transformer.stamp_dual(Y, J, v_previous, tx_factor, state)

    def calculate_residuals(self, network_model, v):
        return self.transformer.calculate_residuals(network_model, v)