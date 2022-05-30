from anoeds.models.edge import Edge
from anoeds.global_vars import global_vars
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
        self.from_node = state.bus_name_map[self.from_element + '_' + self.phase]
        self.to_node = state.bus_name_map[self.to_element + '_' + self.phase]
        f_r, f_i = state.bus_map[self.from_node]
        t_r, t_i = state.bus_map[self.to_node]
        return f_r, f_i, t_r, t_i

    def collect_Y_stamps(self, state, g, b, B):
        line_r_f, line_i_f, line_r_t, line_i_t = self.get_nodes(state)

        # Collect stamps for self susceptance

        # For the KCL at one node of the line
        global_vars.add_linear_Y_stamp(state, line_r_f, line_r_f, g)
        global_vars.add_linear_Y_stamp(state, line_r_f, line_r_t, -g)
        global_vars.add_linear_Y_stamp(state, line_r_f, line_i_f, -b - B/2)
        global_vars.add_linear_Y_stamp(state, line_r_f, line_i_t, b)
        
        global_vars.add_linear_Y_stamp(state, line_i_f, line_r_f, b + B/2)
        global_vars.add_linear_Y_stamp(state, line_i_f, line_r_t, -b)
        global_vars.add_linear_Y_stamp(state, line_i_f, line_i_f, g)
        global_vars.add_linear_Y_stamp(state, line_i_f, line_i_t, -g)

        # For the KCL at the other node of the line
        global_vars.add_linear_Y_stamp(state, line_r_t, line_r_f, -g)
        global_vars.add_linear_Y_stamp(state, line_r_t, line_r_t, g)
        global_vars.add_linear_Y_stamp(state, line_r_t, line_i_f, b)
        global_vars.add_linear_Y_stamp(state, line_r_t, line_i_t, -b - B/2)

        global_vars.add_linear_Y_stamp(state, line_i_t, line_r_f, -b)
        global_vars.add_linear_Y_stamp(state, line_i_t, line_r_t, b + B/2)
        global_vars.add_linear_Y_stamp(state, line_i_t, line_i_f, -g)
        global_vars.add_linear_Y_stamp(state, line_i_t, line_i_t, g)