from enum import Enum
import math
from logic.matrixbuilder import MatrixBuilder
from models.shared.bus import Bus
from models.shared.line import build_line_stamper_bus

class CapSwitchState(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class CapacitorMode(Enum):
    MANUAL = "MANUAL"
    VOLT = "VOLT"
    VAR = "VAR"
    VARVOLT = "VARVOLT"

class Capacitor:
    def __init__(self, from_bus: Bus, to_bus: Bus, var, nominal_voltage, mode: CapacitorMode, high_voltage, low_voltage) -> None:
        self.from_bus = from_bus
        self.to_bus = to_bus
        self.var = var
        self.mode = mode
        self.high_voltage = high_voltage
        self.low_voltage = low_voltage

        self.G = 0
        #https://github.com/gridlab-d/gridlab-d/blob/62dec057ab340ac100c4ae38a47b7400da975156/powerflow/capacitor.cpp#L316
        self.B = var / (nominal_voltage * nominal_voltage)

        #we expect this to be set as part of device control
        self.switch: CapSwitchState
        self.switch = CapSwitchState.CLOSED
    
    def assign_nodes(self, node_index, optimization_enabled):
        self.line_stamper = build_line_stamper_bus(self.from_bus, self.to_bus, optimization_enabled)

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        if self.switch == CapSwitchState.OPEN:
            return

        self.line_stamper.stamp_primal(Y, J, [self.G, self.B, tx_factor], v_previous)
    
    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        if self.switch == CapSwitchState.OPEN:
            return
    
        self.line_stamper.stamp_dual(Y, J, [self.G, self.B, tx_factor], v_previous)
    
    def calculate_residuals(self, network, v):
        if self.switch == CapSwitchState.OPEN:
            return {}

        return self.line_stamper.calc_residuals([self.G, self.B, 0], v)