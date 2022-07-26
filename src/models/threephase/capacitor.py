


import math
from logic.matrixbuilder import MatrixBuilder
from models.shared.bus import Bus
from models.shared.line import build_line_stamper_bus


class Capacitor:
    def __init__(self, from_bus: Bus, to_bus: Bus, var, nominal_voltage, high_voltage, low_voltage) -> None:
        self.from_bus = from_bus
        self.to_bus = to_bus
        self.var = var
        self.high_voltage = high_voltage
        self.low_voltage = low_voltage

        self.G = 0
        #https://github.com/gridlab-d/gridlab-d/blob/62dec057ab340ac100c4ae38a47b7400da975156/powerflow/capacitor.cpp#L316
        self.B = var / (nominal_voltage * nominal_voltage)

        self.on = True
    
    def assign_nodes(self, node_index, optimization_enabled):
        self.line_stamper = build_line_stamper_bus(self.from_bus, self.to_bus, optimization_enabled)

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        self.line_stamper.stamp_primal(Y, J, [self.G, self.B, tx_factor], v_previous)
    
    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        self.line_stamper.stamp_dual(Y, J, [self.G, self.B, tx_factor], v_previous)
    
    def calculate_residuals(self, network_model, v):
        return self.line_stamper.calc_residuals([self.G, self.B, 0], v)

    def is_enabled(self, v_previous):
        #Update: this doesn't work because the matrix builder expects the same set of index stamps every time.

        #This operation is discontinuous. Also, need to account for different control methods.

        f_r, f_i = (self.from_bus.node_Vr, self.from_bus.node_Vi)
        v_r = v_previous[f_r]
        v_i = v_previous[f_i]

        v_magnitude = abs(complex(v_r,v_i))
        if v_magnitude > self.high_voltage:
            self.on = False
        if v_magnitude < self.low_voltage:
            self.on = True
        
        return self.on