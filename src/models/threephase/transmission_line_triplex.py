import numpy as np
from anoeds.models.transmission_line_phase import TransmissionLinePhase
from anoeds.models.edge import Edge

class TriplexTransmissionLine():
    
    def __init__(self, impedances, capacitances, from_element, to_element):
        self.lines = []

        self.impedances = np.array(impedances)
        if self.impedances.shape != (2,2):
            raise Exception("incorrect impedances matrix size, expected 2 by 2")
        self.admittances = np.linalg.inv(self.impedances)
        self.capacitances = capacitances
        self.from_element = from_element
        self.to_element = to_element
        self.phases = "12"

        for i in range(len(self.phases)):
            self.lines.append(TransmissionLinePhase(self.from_element, self.to_element, self.phases[i], self.admittances[i]))


    def stamp_primal(self, Y, J, v_previous, tx_factor, state):
        # Collect stamps here, where we have access to all phases at once
        line_1, line_2  = self.lines
        line1_r_idx, line1_i_idx = line_1.get_nodes(state)
        line2_r_idx, line2_i_idx = line_2.get_nodes(state)

        # Stamp equations for phase 1 current
        Edge.add_linear_Y_stamp(state, line1_r_idx, line1_r_idx, line_1.g[0])
        Edge.add_linear_Y_stamp(state, line1_r_idx, line1_i_idx, -line_1.b[0])
        Edge.add_linear_Y_stamp(state, line1_r_idx, line2_r_idx, line_1.g[1])
        Edge.add_linear_Y_stamp(state, line1_r_idx, line2_i_idx, -line_1.b[1])
        
        Edge.add_linear_Y_stamp(state, line1_i_idx, line1_r_idx, line_1.b[0])
        Edge.add_linear_Y_stamp(state, line1_i_idx, line1_i_idx, line_1.g[0])
        Edge.add_linear_Y_stamp(state, line1_i_idx, line2_r_idx, line_1.b[1])
        Edge.add_linear_Y_stamp(state, line1_i_idx, line2_i_idx, line_1.g[1])
        
        # Stamp equations for phase 2 current
        Edge.add_linear_Y_stamp(state, line2_r_idx, line1_r_idx, line_2.g[0])
        Edge.add_linear_Y_stamp(state, line2_r_idx, line1_i_idx, -line_2.b[0])
        Edge.add_linear_Y_stamp(state, line2_r_idx, line2_r_idx, line_2.g[1])
        Edge.add_linear_Y_stamp(state, line2_r_idx, line2_i_idx, -line_2.b[1])
        
        Edge.add_linear_Y_stamp(state, line2_i_idx, line1_r_idx, line_2.b[0])
        Edge.add_linear_Y_stamp(state, line2_i_idx, line1_i_idx, line_2.g[0])
        Edge.add_linear_Y_stamp(state, line2_i_idx, line2_r_idx, line_2.b[1])
        Edge.add_linear_Y_stamp(state, line2_i_idx, line2_i_idx, line_2.g[1])