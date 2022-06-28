from models.threephase.edge import Edge

import numpy as np

class TransmissionLinePhase(Edge):

    def __init__(self
                , from_element
                , to_element
                , phase
                , edge_id = None
                ):
        super().__init__(edge_id)
        self.from_element = from_element
        self.to_element = to_element
        self.phase = phase
    
    def get_nodes(self, state):
        from_bus = state.bus_name_map[self.from_element + "_" + self.phase]
        to_bus = state.bus_name_map[self.to_element + "_" + self.phase]
        return from_bus.node_Vr, from_bus.node_Vi, to_bus.node_Vr, to_bus.node_Vi

    def collect_Y_stamps(self, state, g, b, B):
        line_r_f, line_i_f, line_r_t, line_i_t = self.get_nodes(state)

        # Collect stamps for self susceptance

        # For the KCL at one node of the line
        Y.stamp(line_r_f, line_r_f, g)
        Y.stamp(line_r_f, line_r_t, -g)
        Y.stamp(line_r_f, line_i_f, -b - B/2)
        Y.stamp(line_r_f, line_i_t, b)
        
        Y.stamp(line_i_f, line_r_f, b + B/2)
        Y.stamp(line_i_f, line_r_t, -b)
        Y.stamp(line_i_f, line_i_f, g)
        Y.stamp(line_i_f, line_i_t, -g)

        # For the KCL at the other node of the line
        Y.stamp(line_r_t, line_r_f, -g)
        Y.stamp(line_r_t, line_r_t, g)
        Y.stamp(line_r_t, line_i_f, b)
        Y.stamp(line_r_t, line_i_t, -b - B/2)

        Y.stamp(line_i_t, line_r_f, -b)
        Y.stamp(line_i_t, line_r_t, b + B/2)
        Y.stamp(line_i_t, line_i_f, -g)
        Y.stamp(line_i_t, line_i_t, g)