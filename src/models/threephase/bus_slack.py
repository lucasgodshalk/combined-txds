from collections import defaultdict
from models.threephase.bus import Bus

class SlackBus(Bus):

    def __init__(self, voltage_magnitude, voltage_angle, bus_id = None):
        super().__init__(voltage_magnitude, voltage_angle, bus_id)
        self.real_current_idx = None
        self.imag_current_idx = None
        
    def stamp_primal(self, Y, J, v_previous, tx_factor, state):
        # Treat a slack bus as an independent voltage source, going from its node, to neutral
        f_r, f_i = state.bus_map[self.bus_id]

        # Incorporating the new variables into existing KCL equations
        Y.stamp(f_r, self.real_current_idx, 1)
        Y.stamp(f_i, self.imag_current_idx, 1)

        # Adding two new equations
        Y.stamp(self.real_current_idx, f_r, 1)
        Y.stamp(self.imag_current_idx, f_i, 1)
        
        # Put in the voltage value of the independent voltage source to the two new equations
        J[self.real_current_idx] += self.v_r
        J[self.imag_current_idx] += self.v_i

    def calculate_residuals(self, state, v, residual_contributions):
        f_r, f_i = state.bus_map[self.bus_id]
        residual_contributions[f_r] = v[self.real_current_idx]
        residual_contributions[f_i] = v[self.imag_current_idx]
        return residual_contributions