from enum import Enum
import math
from logic.matrixbuilder import MatrixBuilder
from models.helpers import merge_residuals
from models.shared.bus import GROUND, Bus
from models.shared.transformer import Transformer
from models.shared.voltagesource import CurrentSensor

class RegType(Enum):
    A = "A"
    B = "B"

class RegControl(Enum):
    MANUAL = "MANUAL"
    REMOTE_NODE = "REMOTE_NODE"
    OUTPUT_VOLTAGE = "OUTPUT_VOLTAGE"
    LINE_DROP_COMP = "LINE_DROP_COMP"

class Regulator():
    
    def __init__(self
                , from_node: Bus 
                , to_node: Bus
                , current_node: Bus
                , tap_position: int
                , ar_step
                , reg_type: RegType
                , reg_control: RegControl
                , vlow: float
                , vhigh: float
                , raise_taps: int
                , lower_taps: int
                ):
        self.from_node = from_node
        self.to_node = to_node
        self.current_node = current_node
        self.tap_position = tap_position
        self.ar_step = ar_step
        self.reg_type = reg_type
        self.reg_control = reg_control
        self.vlow = vlow
        self.vhigh = vhigh
        self.raise_taps = raise_taps
        self.lower_taps = lower_taps

        #this is temporary before we update the tap position for the first time.
        self.turn_ratio = 0

        #todo: is this correct?
        self.phase_shift = 0 

        #todo: pull better values?
        r = 1e-4
        x = 0

        self.transformer = Transformer(
            self.from_node, 
            GROUND, 
            self.current_node, 
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

        #Some control modes require a current measurement on the output of the reg.
        self.current_sensor = CurrentSensor(self.current_node, self.to_node)

        self.try_increment_tap_position(0)

    def try_increment_tap_position(self, increment):
        old_position = self.tap_position
        if self.tap_position + increment >= self.raise_taps:
            self.tap_position = self.raise_taps
        elif self.tap_position + increment <= -self.lower_taps:
            self.tap_position = -self.lower_taps
        else:
            self.tap_position += increment

        if self.reg_type == RegType.A:
            self.turn_ratio = (1 + (self.ar_step * self.tap_position)) ** -1
        elif self.reg_type == RegType.B:
            self.turn_ratio = 1 - (self.ar_step * self.tap_position)
        else:
            raise Exception(f"Unknown regulator type {self.reg_type}")
        
        self.transformer.tr = self.turn_ratio

        return old_position == self.tap_position

    def assign_nodes(self, node_index, optimization_enabled):
        self.transformer.assign_nodes(node_index, optimization_enabled)
        self.current_sensor.assign_nodes(node_index, optimization_enabled)

    def get_connections(self):
        return [(self.from_node, self.to_node)]

    def stamp_primal(self, Y, J, v, tx_factor, state):
        self.transformer.stamp_primal(Y, J, v, tx_factor, state)
        self.current_sensor.stamp_primal(Y, J, v, tx_factor, state)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, state):
        self.transformer.stamp_dual(Y, J, v_previous, tx_factor, state)
        self.current_sensor.stamp_dual(Y, J, v_previous, tx_factor, state)

    def calculate_residuals(self, network, v):
        xfrmr_residuals = self.transformer.calculate_residuals(network, v)
        sensor_residuals = self.current_sensor.calculate_residuals(network, v)

        return merge_residuals({}, xfrmr_residuals, sensor_residuals)