from enum import Enum
from models.singlephase.bus import GROUND, Bus
from models.singlephase.transformer import Transformer
from models.singlephase.voltagesource import CurrentSensor

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

        return old_position != self.tap_position

    def try_adjust_device(self, v):
        #Still a work in progress. Disabling for now.
        return False

        adjustment_made = False
        if self.reg_control == RegControl.MANUAL:
            return False
        elif self.reg_control == RegControl.OUTPUT_VOLTAGE:
            v_r, v_i = v[self.to_node.node_Vr], v[self.to_node.node_Vi]
            v_mag = abs(complex(v_r, v_i))

            if v_mag < self.vlow:
                if self.try_increment_tap_position(1):
                    adjustment_made = True
            elif v_mag > self.vhigh:
                if self.try_increment_tap_position(-1):
                    adjustment_made = True
        else:
            raise Exception(f"{self.reg_control} mode for regulator not implemented")
    
        return adjustment_made

    def assign_nodes(self, node_index, optimization_enabled):
        self.transformer.assign_nodes(node_index, optimization_enabled)
        self.current_sensor.assign_nodes(node_index, optimization_enabled)

    def get_stamps(self):
        return self.transformer.get_stamps() + self.current_sensor.get_stamps()

    def get_connections(self):
        return [(self.from_node, self.to_node)]