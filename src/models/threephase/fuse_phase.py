from models.threephase.edge import Edge

import numpy as np

class FusePhase(Edge):

    def __init__(self
                , from_node
                , to_node
                , current_limit
                , status
                , phase
                , edge_id = Edge._edge_ids.__next__()
                ):
        self.edge_id = edge_id
        self.current_limit = current_limit
        self.status = status
        self.from_node = from_node
        self.to_node = to_node
        self.phase = phase
        self.G = 1e4
        self.B = 1e4
    
    def get_nodes(self, state):
        f_r, f_i = (self.from_node.node_Vr, self.from_node.node_Vi)
        t_r, t_i = (self.to_node.node_Vr, self.to_node.node_Vi)
        return f_r, f_i, t_r, t_i

    def stamp_primal(self, Y, J, v_estimate, tx_factor, state):
        v_r_f, v_i_f, v_r_t, v_i_t = self.get_nodes(state)

        # TODO Check if the fuse has blown
        i_r = self.G*(v_estimate[v_r_f]-v_estimate[v_r_t])
        i_i = self.B*(v_estimate[v_i_f]-v_estimate[v_i_t])
        i = complex(i_r, i_i)
        if abs(i) > self.current_limit:
            self.status = 'BLOWN'
            self.G = 0
            self.B = 0
        else:
            self.status = 'GOOD'
            self.G = 1e4
            self.B = 1e4

        # For the KCL at one node of the line
        Y.stamp(v_r_f, v_r_f, self.G)
        Y.stamp(v_r_f, v_r_t, -self.G)
        Y.stamp(v_r_f, v_i_f, -self.B)
        Y.stamp(v_r_f, v_i_t, self.B)
        
        Y.stamp(v_i_f, v_r_f, self.B)
        Y.stamp(v_i_f, v_r_t, -self.B)
        Y.stamp(v_i_f, v_i_f, self.G)
        Y.stamp(v_i_f, v_i_t, -self.G)

        # For the KCL at the other node of the line
        Y.stamp(v_r_t, v_r_f, -self.G)
        Y.stamp(v_r_t, v_r_t, self.G)
        Y.stamp(v_r_t, v_i_f, self.B)
        Y.stamp(v_r_t, v_i_t, -self.B)

        Y.stamp(v_i_t, v_r_f, -self.B)
        Y.stamp(v_i_t, v_r_t, self.B)
        Y.stamp(v_i_t, v_i_f, -self.G)
        Y.stamp(v_i_t, v_i_t, self.G)
    
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
