from collections import defaultdict
from anoeds.global_vars import global_vars
from anoeds.models.bus import Bus

class SlackBus(Bus):

    def __init__(self, voltage_magnitude, voltage_angle, bus_id = None):
        super().__init__(voltage_magnitude, voltage_angle, bus_id)
        self.real_current_idx = None
        self.imag_current_idx = None
        
    def collect_Y_stamps(self, state):
        # Treat a slack bus as an independent voltage source, going from its node, to neutral
        f_r, f_i = state.bus_map[self.bus_id]

        # Incorporating the new variables into existing KCL equations
        global_vars.add_linear_Y_stamp(state, f_r, self.real_current_idx, 1)
        global_vars.add_linear_Y_stamp(state, f_i, self.imag_current_idx, 1)

        # Adding two new equations
        global_vars.add_linear_Y_stamp(state, self.real_current_idx, f_r, 1)
        global_vars.add_linear_Y_stamp(state, self.imag_current_idx, f_i, 1)
        
    def collect_J_stamps(self, state):
        # Put in the voltage value of the independent voltage source to the two new equations
        global_vars.add_linear_J_stamp(state, self.real_current_idx, self.v_r)
        global_vars.add_linear_J_stamp(state, self.imag_current_idx, self.v_i)

    def calculate_residuals(self, state, v, residual_contributions):
        f_r, f_i = state.bus_map[self.bus_id]
        residual_contributions[f_r] = v[self.real_current_idx]
        residual_contributions[f_i] = v[self.imag_current_idx]
        return residual_contributions