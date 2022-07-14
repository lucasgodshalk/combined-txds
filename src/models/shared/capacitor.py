


from logic.matrixbuilder import MatrixBuilder
from models.shared.line import build_line_stamper


class Capacitor:
    def __init__(self, from_bus, to_bus, var, v_nominal, high_voltage, low_voltage) -> None:
        self.from_bus = from_bus
        self.to_bus = to_bus
        self.var = var
        self.v_nominal = v_nominal
        self.high_voltage = high_voltage
        self.low_voltage = low_voltage

        self.B = var / (v_nominal ** 2)

        self.on = True
    
    def assign_nodes(self, node_index, optimization_enabled):
        self.line_stamper = build_line_stamper(
            self.from_bus.node_Vr, 
            self.from_bus.node_Vi, 
            self.to_bus.node_Vr, 
            self.to_bus.node_Vi,
            self.from_bus.node_lambda_Vr, 
            self.from_bus.node_lambda_Vi, 
            self.to_bus.node_lambda_Vr, 
            self.to_bus.node_lambda_Vi,
            optimization_enabled
            )

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        if not self.is_enabled(v_previous):
            return

        self.line_stamper.stamp_primal(Y, J, [0, self.B, tx_factor], v_previous)
    
    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        if not self.is_enabled(v_previous):
            return
        
        self.line_stamper.stamp_dual(Y, J, [0, self.B, tx_factor], v_previous)
    
    def calculate_residuals(self, network_model, v):
        return self.line_stamper.calc_residuals([0, self.B, 0], v)

    def is_enabled(self, v_previous):
        f_r, f_i = (self.from_bus.node_Vr, self.from_bus.node_Vi)
        v_r = v_previous[f_r]
        v_i = v_previous[f_i]

        v_magnitude = abs(complex(v_r,v_i))
        if v_magnitude > self.high_voltage:
            self.on = False
            return False
        if v_magnitude < self.low_voltage:
            self.on = True
            return True
        
        return self.on