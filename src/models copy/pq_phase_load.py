from collections import defaultdict
from anoeds.models.bus import Bus
from anoeds.global_vars import global_vars
from sympy import symbols, diff


class PQPhaseLoad(Bus):

    def __init__(self, P, Q, Vr_init, Vi_init, phase, bus_id):
        self.bus_id = bus_id if bus_id is not None else Bus._bus_ids.__next__()
        self.phase = phase
        
        # Known values for this node
        self.P = P
        self.Q = Q

        self.Vr_init = Vr_init
        self.Vi_init = Vi_init

        # Equivalent circuit formulations of apparent power equation
        self.V_R, self.V_I = symbols('V_R V_I')
        self.I_R = (self.P * self.V_R + self.Q * self.V_I) / (self.V_R**2 + self.V_I**2)
        self.I_I = (self.P * self.V_I - self.Q * self.V_R) / (self.V_R**2 + self.V_I**2)

        # Partial derivatives of equivalent circuit formulations
        self.dI_R__dV_R = diff(self.I_R, self.V_R)
        self.dI_R__dV_I = diff(self.I_R, self.V_I)
        self.dI_I__dV_R = diff(self.I_I, self.V_R)
        self.dI_I__dV_I = diff(self.I_I, self.V_I)
        
    def collect_Y_stamps(self, state, v):
        # Indices in J of the real and imaginary voltage variables for this bus
        v_r_idx = state.bus_map[self.bus_id][0]
        v_i_idx = state.bus_map[self.bus_id][1]
        
        # Collect equations to stamp onto the Admittance matrix Y
        
        # derivative of real current over real voltage
        global_vars.add_nonlinear_Y_stamp(state, v_r_idx, v_r_idx, self.dI_R__dV_R.evalf(subs={self.V_R: v[v_r_idx], self.V_I: v[v_i_idx]}))
        
        # derivative of real current over imaginary voltage
        global_vars.add_nonlinear_Y_stamp(state, v_r_idx, v_i_idx, self.dI_R__dV_I.evalf(subs={self.V_R: v[v_r_idx], self.V_I: v[v_i_idx]}))
        
        # derivative of imaginary current over real voltage
        global_vars.add_nonlinear_Y_stamp(state, v_i_idx, v_r_idx, self.dI_I__dV_R.evalf(subs={self.V_R: v[v_r_idx], self.V_I: v[v_i_idx]}))
        
        # derivative of imaginary current over imaginary voltage
        global_vars.add_nonlinear_Y_stamp(state, v_i_idx, v_i_idx, self.dI_I__dV_I.evalf(subs={self.V_R: v[v_r_idx], self.V_I: v[v_i_idx]}))

    def collect_J_stamps(self, state, v):
        # Indices in J of the real and imaginary voltage variables for this bus
        v_r_idx = state.bus_map[self.bus_id][0]
        v_i_idx = state.bus_map[self.bus_id][1]

        # Collect equations to stamp onto the vector J

        # real circuit independent current source
        real_current_source_val = -(self.I_R.evalf(subs={self.V_R: v[v_r_idx], self.V_I: v[v_i_idx]}) - self.dI_R__dV_R.evalf(subs={self.V_R: v[v_r_idx], self.V_I: v[v_i_idx]})*v[v_r_idx] - self.dI_R__dV_I.evalf(subs={self.V_R: v[v_r_idx], self.V_I: v[v_i_idx]})*v[v_i_idx])
        global_vars.add_nonlinear_J_stamp(state, v_r_idx, real_current_source_val)
        
        # imaginary circuit independent current source
        imag_current_source_val = -(self.I_I.evalf(subs={self.V_R: v[v_r_idx], self.V_I: v[v_i_idx]}) - self.dI_I__dV_R.evalf(subs={self.V_R: v[v_r_idx], self.V_I: v[v_i_idx]})*v[v_r_idx] - self.dI_I__dV_I.evalf(subs={self.V_R: v[v_r_idx], self.V_I: v[v_i_idx]})*v[v_i_idx])
        global_vars.add_nonlinear_J_stamp(state, v_i_idx, imag_current_source_val)
        
    def set_initial_voltages(self, state, v):
        # Indices in J of the real and imaginary voltage variables for this bus
        v_r, v_i = state.bus_map[self.bus_id]
        v[v_r] = self.Vr_init
        v[v_i] = self.Vi_init

    def calculate_residuals(self, state, v, residual_contributions):
        v_r, v_i = state.bus_map[self.bus_id]
        residual_contributions[v_r] += self.I_R.evalf(subs={self.V_R: v[v_r], self.V_I: v[v_i]})
        residual_contributions[v_i] += self.I_I.evalf(subs={self.V_R: v[v_r], self.V_I: v[v_i]})
        return residual_contributions
