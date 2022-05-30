from collections import defaultdict

import math

class CenterTapTransformer():
    
    def __init__(self
                , coil_1
                , coil_2
                , coil_3
                , phase
                , turn_ratio
                , power_rating
                , g_shunt
                , b_shunt
                ):
        self.coils = [coil_1, coil_2, coil_3]
        self.phases = phase
        self.turn_ratio = turn_ratio
        self.power_rating = power_rating
        self.g_shunt = g_shunt
        self.b_shunt = b_shunt
        
    def stamp_primal(self, Y, J, v_previous, tx_factor, state):
        v_r_f, v_i_f = state.bus_map[self.coils[0].from_node]
        v_r_p, v_i_p = state.bus_map[self.coils[0].primary_node]
        v_r_1x, v_i_1x = state.bus_map[self.coils[1].sending_node]
        v_r_2x, v_i_2x = state.bus_map[self.coils[2].sending_node]
        v_r_1s = self.coils[1].real_voltage_idx
        v_i_1s = self.coils[1].imag_voltage_idx
        v_r_2s = self.coils[2].real_voltage_idx
        v_i_2s = self.coils[2].imag_voltage_idx
        v_r_1t, v_i_1t = state.bus_map[self.coils[1].to_node]
        v_r_2t, v_i_2t = state.bus_map[self.coils[2].to_node]

        # Stamps for the current sources on the primary coil
        Y.stamp(v_r_p, v_r_1s, -1/self.turn_ratio)
        Y.stamp(v_r_p, v_r_2s, -1/self.turn_ratio)
        Y.stamp(v_i_p, v_i_1s, -1/self.turn_ratio)
        Y.stamp(v_i_p, v_i_2s, -1/self.turn_ratio)

        # Stamps for the voltage sources
        Y.stamp(v_r_1s, v_r_1x, 1)
        Y.stamp(v_r_1s, v_r_p, -1/self.turn_ratio)

        Y.stamp(v_r_2s, v_r_2x, 1)
        Y.stamp(v_r_2s, v_r_p, -1/self.turn_ratio)

        Y.stamp(v_i_1s, v_i_1x, 1)
        Y.stamp(v_i_1s, v_i_p, -1/self.turn_ratio)

        Y.stamp(v_i_2s, v_i_2x, 1)
        Y.stamp(v_i_2s, v_i_p, -1/self.turn_ratio)
        
        # Stamps for the new state variables (current at the voltage source)
        Y.stamp(v_r_1x, v_r_1s, 1)
        Y.stamp(v_i_1x, v_i_1s, 1)
        Y.stamp(v_r_2x, v_r_2s, 1)
        Y.stamp(v_i_2x, v_i_2s, 1)
                
        # Values for the primary coil impedance stamps, converted out of per-unit
        r0 = self.coils[0].resistance * self.coils[0].nominal_voltage ** 2  / self.power_rating
        x0 = self.coils[0].reactance * self.coils[0].nominal_voltage ** 2  / self.power_rating
        g0 = r0 / (r0**2 + x0**2) if not (r0 == 0 and x0 == 0) else 0
        b0 = -x0 / (r0**2 + x0**2) if not (r0 == 0 and x0 == 0) else 0
        self.stamp_series_impedance(state, g0, b0, v_r_f, v_i_f, v_r_p, v_i_p)
                
        # Values for the first triplex coil impedance stamps, converted out of per-unit
        r1 = self.coils[1].resistance * self.coils[1].nominal_voltage ** 2  / self.power_rating
        x1 = self.coils[1].reactance * self.coils[1].nominal_voltage ** 2  / self.power_rating
        g1 = r1 / (r1**2 + x1**2) if not (r1 == 0 and x1 == 0) else 0
        b1 = -x1 / (r1**2 + x1**2) if not (r1 == 0 and x1 == 0) else 0
        self.stamp_series_impedance(state, g1, b1, v_r_1x, v_i_1x, v_r_1t, v_i_1t)
                
        # Values for the first triplex coil impedance stamps, converted out of per-unit
        r2 = self.coils[2].resistance * self.coils[2].nominal_voltage ** 2  / self.power_rating
        x2 = self.coils[2].reactance * self.coils[2].nominal_voltage ** 2  / self.power_rating
        g2 = r2 / (r2**2 + x2**2) if not (r2 == 0 and x2 == 0) else 0
        b2 = -x2 / (r2**2 + x2**2) if not (r2 == 0 and x2 == 0) else 0
        self.stamp_series_impedance(state, g2, b2, v_r_2x, v_i_2x, v_r_2t, v_i_2t)


    def stamp_series_impedance(self, state, g, b, impedance_r_f, impedance_i_f, impedance_r_t, impedance_i_t):
        # Stamps for the current equations for the secondary coil at the to node
        Y.stamp(impedance_r_t, impedance_r_t, g)
        Y.stamp(impedance_r_t, impedance_r_f, -g)
        Y.stamp(impedance_r_t, impedance_i_t, -b)
        Y.stamp(impedance_r_t, impedance_i_f, b)

        Y.stamp(impedance_i_t, impedance_r_t, b)
        Y.stamp(impedance_i_t, impedance_r_f, -b)
        Y.stamp(impedance_i_t, impedance_i_t, g)
        Y.stamp(impedance_i_t, impedance_i_f, -g)

        # And for the secondary node
        Y.stamp(impedance_r_f, impedance_r_t, -g)
        Y.stamp(impedance_r_f, impedance_r_f, g)
        Y.stamp(impedance_r_f, impedance_i_t, b)
        Y.stamp(impedance_r_f, impedance_i_f, -b)

        Y.stamp(impedance_i_f, impedance_r_t, -b)
        Y.stamp(impedance_i_f, impedance_r_f, b)
        Y.stamp(impedance_i_f, impedance_i_t, -g)
        Y.stamp(impedance_i_f, impedance_i_f, g)

        # # Values for shunt impedance TODO: debug this
        # Y.stamp(v_r_1t, v_r_1t, self.g_shunt)
        # Y.stamp(v_r_1t, v_i_1t, -self.b_shunt)
        # Y.stamp(v_i_1t, v_r_1t, self.b_shunt)
        # Y.stamp(v_i_1t, v_i_1t, self.g_shunt)
        
        # Y.stamp(v_r_2t, v_r_2t, self.g_shunt)
        # Y.stamp(v_r_2t, v_i_2t, -self.b_shunt)
        # Y.stamp(v_i_2t, v_r_2t, self.b_shunt)
        # Y.stamp(v_i_2t, v_i_2t, self.g_shunt)


    def calculate_residuals(self, state, v):
        residual_contributions = defaultdict(lambda: 0)
        v_r_f, v_i_f = state.bus_map[self.coils[0].from_node]
        v_r_p, v_i_p = state.bus_map[self.coils[0].primary_node]
        v_r_1x, v_i_1x = state.bus_map[self.coils[1].sending_node]
        v_r_2x, v_i_2x = state.bus_map[self.coils[2].sending_node]
        v_r_1s = self.coils[1].real_voltage_idx
        v_i_1s = self.coils[1].imag_voltage_idx
        v_r_2s = self.coils[2].real_voltage_idx
        v_i_2s = self.coils[2].imag_voltage_idx
        v_r_1t, v_i_1t = state.bus_map[self.coils[1].to_node]
        v_r_2t, v_i_2t = state.bus_map[self.coils[2].to_node]

        # Stamps for the current sources on the primary coil
        residual_contributions[v_r_p] += v[v_r_1s] * -1/self.turn_ratio
        residual_contributions[v_r_p] += v[v_r_2s] * -1/self.turn_ratio
        residual_contributions[v_i_p] += v[v_i_1s] * -1/self.turn_ratio
        residual_contributions[v_i_p] += v[v_i_2s] * -1/self.turn_ratio

        # # Stamps for the voltage sources
        # residual_contributions[v_r_1s] += v[v_r_1x] * 1
        # residual_contributions[v_r_1s] += v[v_r_p] * -1/self.turn_ratio

        # residual_contributions[v_r_2s] += v[v_r_2x] * 1
        # residual_contributions[v_r_2s] += v[v_r_p] * -1/self.turn_ratio

        # residual_contributions[v_i_1s] += v[v_i_1x] * 1
        # residual_contributions[v_i_1s] += v[v_i_p] * -1/self.turn_ratio

        # residual_contributions[v_i_2s] += v[v_i_2x] * 1
        # residual_contributions[v_i_2s] += v[v_i_p] * -1/self.turn_ratio
        
        # Stamps for the new state variables (current at the voltage source)
        residual_contributions[v_r_1x] += v[v_r_1s] * 1
        residual_contributions[v_i_1x] += v[v_i_1s] * 1
        residual_contributions[v_r_2x] += v[v_r_2s] * 1
        residual_contributions[v_i_2x] += v[v_i_2s] * 1
                
        # Values for the primary coil impedance stamps, converted out of per-unit
        r0 = self.coils[0].resistance * self.coils[0].nominal_voltage ** 2  / self.power_rating
        x0 = self.coils[0].reactance * self.coils[0].nominal_voltage ** 2  / self.power_rating
        g0 = r0 / (r0**2 + x0**2) if not (r0 == 0 and x0 == 0) else 0
        b0 = -x0 / (r0**2 + x0**2) if not (r0 == 0 and x0 == 0) else 0
        self.add_series_impedance_residual_contribution(residual_contributions, v, g0, b0, v_r_f, v_i_f, v_r_p, v_i_p)
                
        # Values for the first triplex coil impedance stamps, converted out of per-unit
        r1 = self.coils[1].resistance * self.coils[1].nominal_voltage ** 2  / self.power_rating
        x1 = self.coils[1].reactance * self.coils[1].nominal_voltage ** 2  / self.power_rating
        g1 = r1 / (r1**2 + x1**2) if not (r1 == 0 and x1 == 0) else 0
        b1 = -x1 / (r1**2 + x1**2) if not (r1 == 0 and x1 == 0) else 0
        self.add_series_impedance_residual_contribution(residual_contributions, v, g1, b1, v_r_1x, v_i_1x, v_r_1t, v_i_1t)
                
        # Values for the first triplex coil impedance stamps, converted out of per-unit
        r2 = self.coils[2].resistance * self.coils[2].nominal_voltage ** 2  / self.power_rating
        x2 = self.coils[2].reactance * self.coils[2].nominal_voltage ** 2  / self.power_rating
        g2 = r2 / (r2**2 + x2**2) if not (r2 == 0 and x2 == 0) else 0
        b2 = -x2 / (r2**2 + x2**2) if not (r2 == 0 and x2 == 0) else 0
        self.add_series_impedance_residual_contribution(residual_contributions, v, g2, b2, v_r_2x, v_i_2x, v_r_2t, v_i_2t)

        return residual_contributions


    def add_series_impedance_residual_contribution(self, residual_contributions, v, g, b, impedance_r_f, impedance_i_f, impedance_r_t, impedance_i_t):
        # Stamps for the current equations for the secondary coil at the to node
        residual_contributions[impedance_r_t] += v[impedance_r_t] * g
        residual_contributions[impedance_r_t] += v[impedance_r_f] * -g
        residual_contributions[impedance_r_t] += v[impedance_i_t] * -b
        residual_contributions[impedance_r_t] += v[impedance_i_f] * b

        residual_contributions[impedance_i_t] += v[impedance_r_t] * b
        residual_contributions[impedance_i_t] += v[impedance_r_f] * -b
        residual_contributions[impedance_i_t] += v[impedance_i_t] * g
        residual_contributions[impedance_i_t] += v[impedance_i_f] * -g

        # And for the secondary node
        residual_contributions[impedance_r_f] += v[impedance_r_t] * -g
        residual_contributions[impedance_r_f] += v[impedance_r_f] * g
        residual_contributions[impedance_r_f] += v[impedance_i_t] * b
        residual_contributions[impedance_r_f] += v[impedance_i_f] * -b

        residual_contributions[impedance_i_f] += v[impedance_r_t] * -b
        residual_contributions[impedance_i_f] += v[impedance_r_f] * b
        residual_contributions[impedance_i_f] += v[impedance_i_t] * -g
        residual_contributions[impedance_i_f] += v[impedance_i_f] * g

        # # Values for shunt impedance TODO: debug this
        # Y.stamp(v_r_1t, v_r_1t, self.g_shunt)
        # Y.stamp(v_r_1t, v_i_1t, -self.b_shunt)
        # Y.stamp(v_i_1t, v_r_1t, self.b_shunt)
        # Y.stamp(v_i_1t, v_i_1t, self.g_shunt)
        
        # Y.stamp(v_r_2t, v_r_2t, self.g_shunt)
        # Y.stamp(v_r_2t, v_i_2t, -self.b_shunt)
        # Y.stamp(v_i_2t, v_r_2t, self.b_shunt)
        # Y.stamp(v_i_2t, v_i_2t, self.g_shunt)

