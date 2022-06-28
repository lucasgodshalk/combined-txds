import math
import numpy as np

# A toy class which models a load as a simple resistor
class ResistivePhaseLoad():

    def __init__(self, V_r, V_i, Z, phase, bus_id):
        self.bus_id = bus_id
        self.phase = phase

        self.V_r = V_r
        self.V_i = V_i
        self.Z = Z
        self.R = np.real(self.Z)
        self.X = np.imag(self.Z)
        self.G = self.R / (self.R**2 + self.X**2)
        self.B = -self.X / (self.R**2 + self.X**2)
        
    def stamp_primal(self, Y, J, v_previous, tx_factor, state):
        # Indices in J of the real and imaginary voltage variables for this bus
        v_r_idx = state.bus_map[self.bus_id][0]
        v_i_idx = state.bus_map[self.bus_id][1]
        
        # Collect equations to stamp onto the Admittance matrix Y
        Y.stamp(v_r_idx, v_r_idx, self.G)
        # Y.stamp(v_r_idx, ground, -self.G)
        # Y.stamp(ground, v_r_idx, -self.G)
        # Y.stamp(ground, ground, self.G)

        Y.stamp(v_i_idx, v_i_idx, self.G)
        # Y.stamp(v_i_idx, ground, -self.G)
        # Y.stamp(ground, v_i_idx, -self.G)
        # Y.stamp(ground, ground, self.G)
        
    # def collect_J_stamps(self, state):
    #     # Do nothing
    #     pass

    def set_initial_voltages(self, state, v):
        # Indices in J of the real and imaginary voltage variables for this bus
        v_r_idx = state.bus_map[self.bus_id][0]
        v_i_idx = state.bus_map[self.bus_id][1]

        v[v_r_idx] = self.V_r
        v[v_i_idx] = self.V_i

