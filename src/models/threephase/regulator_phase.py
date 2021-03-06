import math
from models.shared.bus import Bus
from models.threephase.edge import Edge

class RegulatorPhase(Edge):
    
    def __init__(self
                , from_node: Bus 
                , real_voltage_idx
                , imag_voltage_idx
                , secondary_node: Bus
                , to_node: Bus
                , phase
                , tap_position
                , edge_id = Edge._edge_ids.__next__()):
        self.edge_id = edge_id
        self.from_node = from_node
        self.real_voltage_idx = real_voltage_idx
        self.imag_voltage_idx = imag_voltage_idx
        self.secondary_node = secondary_node
        self.to_node = to_node
        self.phase = phase
        self.tap_position = tap_position
        
    def stamp_primal(self, Y, J, v, tx_factor, state):
        # f_r, f_i = state.bus_map[self.from_node]
        # t_r, t_i = state.bus_map[self.to_node]

        # TODO add linear Y stamps
        # Y.stamp(f_r, f_r, 0)

        v_r_f, v_i_f = (self.from_node.node_Vr, self.from_node.node_Vi)
        v_r_p = self.real_voltage_idx
        v_i_p = self.imag_voltage_idx
        v_r_s, v_i_s = (self.secondary_node.node_Vr, self.secondary_node.node_Vi)
        v_r_t, v_i_t = (self.to_node.node_Vr, self.to_node.node_Vi)

        # Stamps for the voltage equations for the primary coil
        Y.stamp(v_r_p, v_r_f, 1)
        Y.stamp(v_r_p, v_r_s, -self.turn_ratio * math.cos(self.phase_shift))
        Y.stamp(v_r_p, v_i_s, self.turn_ratio * math.sin(self.phase_shift))
        Y.stamp(v_i_p, v_i_f, 1)
        Y.stamp(v_i_p, v_r_s, -self.turn_ratio * math.sin(self.phase_shift))
        Y.stamp(v_i_p, v_i_s, -self.turn_ratio * math.cos(self.phase_shift))

        # Stamps for the new state variables (current at the voltage source)
        Y.stamp(v_r_f, v_r_p, 1)
        Y.stamp(v_i_f, v_i_p, 1)

        # Stamps for the current sources on the secondary coil (KCL)
        Y.stamp(v_r_s, v_r_p, -self.turn_ratio * math.cos(self.phase_shift))
        Y.stamp(v_r_s, v_i_p, -self.turn_ratio * math.sin(self.phase_shift))
        Y.stamp(v_i_s, v_r_p, self.turn_ratio * math.sin(self.phase_shift))
        Y.stamp(v_i_s, v_i_p, -self.turn_ratio * math.cos(self.phase_shift))
        

        # Values for the secondary coil stamps
        r = self.secondary_coil.resistance * self.secondary_coil.nominal_voltage ** 2  / self.secondary_coil.rated_power
        x = self.secondary_coil.reactance * self.secondary_coil.nominal_voltage ** 2  / self.secondary_coil.rated_power
        g = r / (r**2 + x**2)
        b = -x / (r**2 + x**2)

        # Stamps for the current equations for the secondary coil at the to node
        Y.stamp(v_r_t, v_r_t, g)
        Y.stamp(v_r_t, v_r_s, -g)
        Y.stamp(v_r_t, v_i_t, -b)
        Y.stamp(v_r_t, v_i_s, b)

        Y.stamp(v_i_t, v_r_t, b)
        Y.stamp(v_i_t, v_r_s, -b)
        Y.stamp(v_i_t, v_i_t, g)
        Y.stamp(v_i_t, v_i_s, -g)

        # And for the secondary node
        Y.stamp(v_r_s, v_r_t, -g)
        Y.stamp(v_r_s, v_r_s, g)
        Y.stamp(v_r_s, v_i_t, b)
        Y.stamp(v_r_s, v_i_s, -b)

        Y.stamp(v_i_s, v_r_t, -b)
        Y.stamp(v_i_s, v_r_s, b)
        Y.stamp(v_i_s, v_i_t, -g)
        Y.stamp(v_i_s, v_i_s, g)