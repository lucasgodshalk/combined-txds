from anoeds.models.edge import Edge
from anoeds.global_vars import global_vars
import numpy as np

class SwitchPhase(Edge):

    def __init__(self
                , from_node
                , to_node
                , status
                , phase
                , edge_id = Edge._edge_ids.__next__()
                ):
        self.edge_id = edge_id
        self.status = status
        self.from_node = from_node
        self.to_node = to_node
        self.phase = phase
        # Don't stamp values if the switch is open
        if self.status == 'OPEN':
            self.G = 0
            self.B = 0
        else:
            self.G = 1e4
            self.B = 1e4
    
    def get_nodes(self, state):
        f_r, f_i = state.bus_map[self.from_node]
        t_r, t_i = state.bus_map[self.to_node]
        return f_r, f_i, t_r, t_i

    def stamp_primal(self, Y, J, v_previous, tx_factor, state):
        line_r_f, line_i_f, line_r_t, line_i_t = self.get_nodes(state)
        # For the KCL at one node of the line
        Y.stamp(line_r_f, line_r_f, self.G)
        Y.stamp(line_r_f, line_r_t, -self.G)
        Y.stamp(line_r_f, line_i_f, -self.B)
        Y.stamp(line_r_f, line_i_t, self.B)
        
        Y.stamp(line_i_f, line_r_f, self.B)
        Y.stamp(line_i_f, line_r_t, -self.B)
        Y.stamp(line_i_f, line_i_f, self.G)
        Y.stamp(line_i_f, line_i_t, -self.G)

        # For the KCL at the other node of the line
        Y.stamp(line_r_t, line_r_f, -self.G)
        Y.stamp(line_r_t, line_r_t, self.G)
        Y.stamp(line_r_t, line_i_f, self.B)
        Y.stamp(line_r_t, line_i_t, -self.B)

        Y.stamp(line_i_t, line_r_f, -self.B)
        Y.stamp(line_i_t, line_r_t, self.B)
        Y.stamp(line_i_t, line_i_f, -self.G)
        Y.stamp(line_i_t, line_i_t, self.G)
    
    def calculate_residuals(self, state, v, residual_contributions):
        line_r_f, line_i_f, line_r_t, line_i_t = self.get_nodes(state)

        # For the KCL at one node of the line
        residual_contributions[line_r_f] += v[line_r_f] * (self.G)
        residual_contributions[line_r_f] += v[line_r_t] * (-self.G)
        residual_contributions[line_r_f] += v[line_i_f] * (-self.B)
        residual_contributions[line_r_f] += v[line_i_t] * (self.B)
        
        residual_contributions[line_i_f] += v[line_r_f] * (self.B)
        residual_contributions[line_i_f] += v[line_r_t] * (-self.B)
        residual_contributions[line_i_f] += v[line_i_f] * (self.G)
        residual_contributions[line_i_f] += v[line_i_t] * (-self.G)

        # For the KCL at the other node of the line
        residual_contributions[line_r_t] += v[line_r_f] * (-self.G)
        residual_contributions[line_r_t] += v[line_r_t] * (self.G)
        residual_contributions[line_r_t] += v[line_i_f] * (self.B)
        residual_contributions[line_r_t] += v[line_i_t] * (-self.B)

        residual_contributions[line_i_t] += v[line_r_f] * (-self.B)
        residual_contributions[line_i_t] += v[line_r_t] * (self.B)
        residual_contributions[line_i_t] += v[line_i_f] * (-self.G)
        residual_contributions[line_i_t] += v[line_i_t] * (self.G)

        return residual_contributions
