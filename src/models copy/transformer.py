from collections import defaultdict
from anoeds.global_vars import global_vars
import math

class Transformer():
    
    def __init__(self
                , primary_coil
                , secondary_coil
                , phases
                , turn_ratio
                , phase_shift
                , g_shunt
                , b_shunt
                ):
        self.primary_coil = primary_coil
        self.secondary_coil = secondary_coil
        self.phases = phases
        self.turn_ratio = turn_ratio
        self.phase_shift = phase_shift
        self.g_shunt = g_shunt
        self.b_shunt = b_shunt
        
    def collect_Y_stamps(self, state):
        phase_list = self.get_phase_list()

        for (pos_phase_1, neg_phase_1, pos_phase_2, neg_phase_2) in phase_list:
            v_r_f, v_i_f = state.bus_map[self.primary_coil.phase_coils[pos_phase_1].from_node]
            v_r_p = self.primary_coil.phase_coils[pos_phase_1].real_voltage_idx
            v_i_p = self.primary_coil.phase_coils[pos_phase_1].imag_voltage_idx
            v_r_s, v_i_s = state.bus_map[self.secondary_coil.phase_coils[pos_phase_2].secondary_node]
            v_r_t, v_i_t = state.bus_map[self.secondary_coil.phase_coils[pos_phase_2].to_node]

            # Stamps for the voltage equations for the primary coil
            global_vars.add_linear_Y_stamp(state, v_r_p, v_r_f, 1)
            global_vars.add_linear_Y_stamp(state, v_r_p, v_r_s, -self.turn_ratio * math.cos(self.phase_shift))
            global_vars.add_linear_Y_stamp(state, v_r_p, v_i_s, self.turn_ratio * math.sin(self.phase_shift))
            global_vars.add_linear_Y_stamp(state, v_i_p, v_i_f, 1)
            global_vars.add_linear_Y_stamp(state, v_i_p, v_r_s, -self.turn_ratio * math.sin(self.phase_shift))
            global_vars.add_linear_Y_stamp(state, v_i_p, v_i_s, -self.turn_ratio * math.cos(self.phase_shift))

            # Stamps for the new state variables (current at the voltage source)
            global_vars.add_linear_Y_stamp(state, v_r_f, v_r_p, 1)
            global_vars.add_linear_Y_stamp(state, v_i_f, v_i_p, 1)

            # Stamps for the current sources on the secondary coil (KCL)
            global_vars.add_linear_Y_stamp(state, v_r_s, v_r_p, -self.turn_ratio * math.cos(self.phase_shift))
            global_vars.add_linear_Y_stamp(state, v_r_s, v_i_p, -self.turn_ratio * math.sin(self.phase_shift))
            global_vars.add_linear_Y_stamp(state, v_i_s, v_r_p, self.turn_ratio * math.sin(self.phase_shift))
            global_vars.add_linear_Y_stamp(state, v_i_s, v_i_p, -self.turn_ratio * math.cos(self.phase_shift))
            
    
            # Values for the secondary coil stamps, converted out of per-unit
            r = self.secondary_coil.resistance * self.secondary_coil.nominal_voltage ** 2  / self.secondary_coil.rated_power
            x = self.secondary_coil.reactance * self.secondary_coil.nominal_voltage ** 2  / self.secondary_coil.rated_power
            g = r / (r**2 + x**2)
            b = -x / (r**2 + x**2)

            # Stamps for the current equations for the secondary coil at the to node
            global_vars.add_linear_Y_stamp(state, v_r_t, v_r_t, g)
            global_vars.add_linear_Y_stamp(state, v_r_t, v_r_s, -g)
            global_vars.add_linear_Y_stamp(state, v_r_t, v_i_t, -b)
            global_vars.add_linear_Y_stamp(state, v_r_t, v_i_s, b)

            global_vars.add_linear_Y_stamp(state, v_i_t, v_r_t, b)
            global_vars.add_linear_Y_stamp(state, v_i_t, v_r_s, -b)
            global_vars.add_linear_Y_stamp(state, v_i_t, v_i_t, g)
            global_vars.add_linear_Y_stamp(state, v_i_t, v_i_s, -g)

            # And for the secondary node
            global_vars.add_linear_Y_stamp(state, v_r_s, v_r_t, -g)
            global_vars.add_linear_Y_stamp(state, v_r_s, v_r_s, g)
            global_vars.add_linear_Y_stamp(state, v_r_s, v_i_t, b)
            global_vars.add_linear_Y_stamp(state, v_r_s, v_i_s, -b)

            global_vars.add_linear_Y_stamp(state, v_i_s, v_r_t, -b)
            global_vars.add_linear_Y_stamp(state, v_i_s, v_r_s, b)
            global_vars.add_linear_Y_stamp(state, v_i_s, v_i_t, -g)
            global_vars.add_linear_Y_stamp(state, v_i_s, v_i_s, g)

            # Stamps for the shunt impedance
            # global_vars.add_linear_Y_stamp(state, v_r_t, v_r_t, self.g_shunt)
            # global_vars.add_linear_Y_stamp(state, v_r_t, v_i_t, -self.b_shunt)
            # global_vars.add_linear_Y_stamp(state, v_i_t, v_r_t, self.b_shunt)
            # global_vars.add_linear_Y_stamp(state, v_i_t, v_i_t, self.g_shunt)



            # Stamps to the negative terminal (neutral when wye, not neutral when delta)
            if neg_phase_1 is not "N" and neg_phase_2 is not "N":
                v_r_fn, v_i_fn = state.bus_map[self.primary_coil.phase_coils[neg_phase_1].from_node]
                v_r_tn, v_i_tn = state.bus_map[self.secondary_coil.phase_coils[neg_phase_2].to_node]

                # Voltage equations
                global_vars.add_linear_Y_stamp(state, v_r_p, v_r_fn, -1)
                global_vars.add_linear_Y_stamp(state, v_r_p, v_r_tn, self.turn_ratio * math.cos(self.phase_shift))
                global_vars.add_linear_Y_stamp(state, v_r_p, v_i_tn, -self.turn_ratio * math.sin(self.phase_shift))
                global_vars.add_linear_Y_stamp(state, v_i_p, v_i_fn, -1)
                global_vars.add_linear_Y_stamp(state, v_i_p, v_r_tn, self.turn_ratio * math.sin(self.phase_shift))
                global_vars.add_linear_Y_stamp(state, v_i_p, v_i_tn, self.turn_ratio * math.cos(self.phase_shift))

                # Stamps for the new state variables (current at the voltage source)
                global_vars.add_linear_Y_stamp(state, v_r_fn, v_r_p, -1)
                global_vars.add_linear_Y_stamp(state, v_i_fn, v_i_p, -1)
                
                # Stamps for the state variables (current across the neutral line)
                global_vars.add_linear_Y_stamp(state, v_r_tn, v_r_p, self.turn_ratio * math.cos(self.phase_shift))
                global_vars.add_linear_Y_stamp(state, v_r_tn, v_i_p, self.turn_ratio * math.sin(self.phase_shift))
                global_vars.add_linear_Y_stamp(state, v_i_tn, v_r_p, -self.turn_ratio * math.sin(self.phase_shift))
                global_vars.add_linear_Y_stamp(state, v_i_tn, v_i_p, self.turn_ratio * math.cos(self.phase_shift))
        
    def calculate_residuals(self, state, v):
        phase_list = self.get_phase_list()
        residual_contributions = defaultdict(lambda: 0)

        for (pos_phase_1, neg_phase_1, pos_phase_2, neg_phase_2) in phase_list:
            v_r_f, v_i_f = state.bus_map[self.primary_coil.phase_coils[pos_phase_1].from_node]
            v_r_p = self.primary_coil.phase_coils[pos_phase_1].real_voltage_idx
            v_i_p = self.primary_coil.phase_coils[pos_phase_1].imag_voltage_idx
            v_r_s, v_i_s = state.bus_map[self.secondary_coil.phase_coils[pos_phase_2].secondary_node]
            v_r_t, v_i_t = state.bus_map[self.secondary_coil.phase_coils[pos_phase_2].to_node]

            # # Residual calculations for the voltage equations for the primary coil
            # residual_contributions[v_r_p] += v[v_r_f] * (1)
            # residual_contributions[v_r_p] += v[v_r_s] * (-self.turn_ratio * math.cos(self.phase_shift))
            # residual_contributions[v_r_p] += v[v_i_s] * (self.turn_ratio * math.sin(self.phase_shift))
            # residual_contributions[v_i_p] += v[v_i_f] * (1)
            # residual_contributions[v_i_p] += v[v_r_s] * (-self.turn_ratio * math.sin(self.phase_shift))
            # residual_contributions[v_i_p] += v[v_i_s] * (-self.turn_ratio * math.cos(self.phase_shift))

            # Residual calculations for the new state variables (current at the voltage source)
            residual_contributions[v_r_f] += v[v_r_p] * (1)
            residual_contributions[v_i_f] += v[v_i_p] * (1)

            # Residual calculations for the current sources on the secondary coil (KCL)
            residual_contributions[v_r_s] += v[v_r_p] * (-self.turn_ratio * math.cos(self.phase_shift))
            residual_contributions[v_r_s] += v[v_i_p] * (-self.turn_ratio * math.sin(self.phase_shift))
            residual_contributions[v_i_s] += v[v_r_p] * (self.turn_ratio * math.sin(self.phase_shift))
            residual_contributions[v_i_s] += v[v_i_p] * (-self.turn_ratio * math.cos(self.phase_shift))
            
    
            # Values for the secondary coil Residual calculations, converted out of per-unit
            r = self.secondary_coil.resistance * self.secondary_coil.nominal_voltage ** 2  / self.secondary_coil.rated_power
            x = self.secondary_coil.reactance * self.secondary_coil.nominal_voltage ** 2  / self.secondary_coil.rated_power
            g = r / (r**2 + x**2)
            b = -x / (r**2 + x**2)

            # Residual calculations for the current equations for the secondary coil at the to node
            residual_contributions[v_r_t] += v[v_r_t] * (g)
            residual_contributions[v_r_t] += v[v_r_s] * (-g)
            residual_contributions[v_r_t] += v[v_i_t] * (-b)
            residual_contributions[v_r_t] += v[v_i_s] * (b)

            residual_contributions[v_i_t] += v[v_r_t] * (b)
            residual_contributions[v_i_t] += v[v_r_s] * (-b)
            residual_contributions[v_i_t] += v[v_i_t] * (g)
            residual_contributions[v_i_t] += v[v_i_s] * (-g)

            # And for the secondary node
            residual_contributions[v_r_s] += v[v_r_t] * (-g)
            residual_contributions[v_r_s] += v[v_r_s] * (g)
            residual_contributions[v_r_s] += v[v_i_t] * (b)
            residual_contributions[v_r_s] += v[v_i_s] * (-b)

            residual_contributions[v_i_s] += v[v_r_t] * (-b)
            residual_contributions[v_i_s] += v[v_r_s] * (b)
            residual_contributions[v_i_s] += v[v_i_t] * (-g)
            residual_contributions[v_i_s] += v[v_i_s] * (g)

            # Residual calculations for the shunt impedance
            residual_contributions[v_r_t] += v[v_r_t] * (self.g_shunt)
            residual_contributions[v_r_t] += v[v_i_t] * (-self.b_shunt)
            residual_contributions[v_i_t] += v[v_r_t] * (self.b_shunt)
            residual_contributions[v_i_t] += v[v_i_t] * (self.g_shunt)



            # Residual calculations to the negative terminal (neutral when wye, not neutral when delta)
            if neg_phase_1 is not "N" and neg_phase_2 is not "N":
                v_r_fn, v_i_fn = state.bus_map[self.primary_coil.phase_coils[neg_phase_1].from_node]
                v_r_tn, v_i_tn = state.bus_map[self.secondary_coil.phase_coils[neg_phase_2].to_node]

                # # Voltage equations
                # residual_contributions[v_r_p] += v[v_r_fn] * (-1)
                # residual_contributions[v_r_p] += v[v_r_tn] * (self.turn_ratio * math.cos(self.phase_shift))
                # residual_contributions[v_r_p] += v[v_i_tn] * (-self.turn_ratio * math.sin(self.phase_shift))
                # residual_contributions[v_i_p] += v[v_i_fn] * (-1)
                # residual_contributions[v_i_p] += v[v_r_tn] * (self.turn_ratio * math.sin(self.phase_shift))
                # residual_contributions[v_i_p] += v[v_i_tn] * (self.turn_ratio * math.cos(self.phase_shift))

                # Residual calculations for the new state variables (current at the voltage source)
                residual_contributions[v_r_fn] += v[v_r_p] * (-1)
                residual_contributions[v_i_fn] += v[v_i_p] * (-1)
                
                # Residual calculations for the state variables (current across the neutral line)
                residual_contributions[v_r_tn] += v[v_r_p] * (self.turn_ratio * math.cos(self.phase_shift))
                residual_contributions[v_r_tn] += v[v_i_p] * (self.turn_ratio * math.sin(self.phase_shift))
                residual_contributions[v_i_tn] += v[v_r_p] * (-self.turn_ratio * math.sin(self.phase_shift))
                residual_contributions[v_i_tn] += v[v_i_p] * (self.turn_ratio * math.cos(self.phase_shift))
        
        return residual_contributions

    def get_phase_list(self):
        rotated_phases = self.phases[1:] + self.phases[:1]
        phase_list = list.copy(self.phases)
        if self.primary_coil.connection_type == "D":
            for i in range(len(phase_list)):
                phase_list[i] += rotated_phases[i]
        else:
            for i in range(len(phase_list)):
                phase_list[i] += "N"
                
        for i in range(len(phase_list)):
            phase_list[i] += self.phases[i]

        if self.secondary_coil.connection_type == "D":
            for i in range(len(phase_list)):
                phase_list[i] += rotated_phases[i]
        else:
            for i in range(len(phase_list)):
                phase_list[i] += "N"
        return phase_list

