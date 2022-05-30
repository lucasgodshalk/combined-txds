from collections import defaultdict
import numpy as np
from anoeds.models.transmission_line_phase import TransmissionLinePhase
from anoeds.models.edge import Edge
from anoeds.global_vars import global_vars
from copy import copy

class TransmissionLine():
    
    def __init__(self, impedances, shunt_admittances, from_element, to_element, length, phases="ABC"):
        self.lines = []

        self.impedances = np.array(impedances)
        if not (self.impedances.shape == (3,3) or self.impedances.shape == (2,2) or self.impedances.shape == (1,1)):
            raise Exception("incorrect impedances matrix size, expected a square matrix at most size 3 by 3")
        # Convert the per-meter impedance values to absolute, based on line length (in meters)
        self.impedances *= length
        try:
            self.admittances = np.linalg.inv(self.impedances)
        except Exception:
            raise Exception("Transmission line was provided with a noninvertible matrix")
        if not np.allclose(np.dot(self.impedances, self.admittances), np.identity(len(phases))):
            raise Exception("np.linalg.inv was unable to find a good inverse to the impedance matrix")
        
        # Convert the per-meter shunt admittance values to absolute, based on line length (in meters)
        self.shunt_admittances = np.array(shunt_admittances)
        self.shunt_admittances *= length
        self.from_element = from_element
        self.to_element = to_element
        self.length = length

        for phase in phases:
            self.lines.append(TransmissionLinePhase(self.from_element, self.to_element, phase))


    def collect_Y_stamps(self, state):
        # Go through all phases
        for i in range(len(self.lines)):
            # Get the line
            line = self.lines[i]

            # Collect the line's nodes for mutual susceptance calculation
            line_r_f, line_i_f, line_r_t, line_i_t = line.get_nodes(state)

            # Go through all lines
            for j in range(len(self.lines)):
                g = np.real(self.admittances[i][j])
                b = np.imag(self.admittances[i][j])
                try:
                    B = np.imag(self.shunt_admittances[i][j])
                except IndexError:
                    B = 0


                line2 = self.lines[j]
                line2_r_f, line2_i_f, line2_r_t, line2_i_t = line2.get_nodes(state)

                # Collect stamps for mutual susceptance

                # For the KCL at one node of the line
                global_vars.add_linear_Y_stamp(state, line_r_f, line2_r_f, g)
                global_vars.add_linear_Y_stamp(state, line_r_f, line2_r_t, -g)
                global_vars.add_linear_Y_stamp(state, line_r_f, line2_i_f, -b - B/2)
                global_vars.add_linear_Y_stamp(state, line_r_f, line2_i_t, b)
                
                global_vars.add_linear_Y_stamp(state, line_i_f, line2_r_f, b + B/2)
                global_vars.add_linear_Y_stamp(state, line_i_f, line2_r_t, -b)
                global_vars.add_linear_Y_stamp(state, line_i_f, line2_i_f, g)
                global_vars.add_linear_Y_stamp(state, line_i_f, line2_i_t, -g)

                # For the KCL at the other node of the line
                global_vars.add_linear_Y_stamp(state, line_r_t, line2_r_f, -g)
                global_vars.add_linear_Y_stamp(state, line_r_t, line2_r_t, g)
                global_vars.add_linear_Y_stamp(state, line_r_t, line2_i_f, b)
                global_vars.add_linear_Y_stamp(state, line_r_t, line2_i_t, -b - B/2)

                global_vars.add_linear_Y_stamp(state, line_i_t, line2_r_f, -b)
                global_vars.add_linear_Y_stamp(state, line_i_t, line2_r_t, b + B/2)
                global_vars.add_linear_Y_stamp(state, line_i_t, line2_i_f, -g)
                global_vars.add_linear_Y_stamp(state, line_i_t, line2_i_t, g)
    
    def calculate_residuals(self, state, v):
        residual_contributions = defaultdict(lambda: 0)
        # Go through all phases
        for i in range(len(self.lines)):
            # Get the line
            line = self.lines[i]

            # Collect the line's nodes
            line_r_f, line_i_f, line_r_t, line_i_t = line.get_nodes(state)

            # Go through all lines
            for j in range(len(self.lines)):
                g = np.real(self.admittances[i][j])
                b = np.imag(self.admittances[i][j])
                try:
                    B = np.imag(self.shunt_admittances[i][j])
                except IndexError:
                    B = 0


                line2 = self.lines[j]
                line2_r_f, line2_i_f, line2_r_t, line2_i_t = line2.get_nodes(state)

                # For the KCL at one node of the line
                residual_contributions[line_r_f] += v[line2_r_f] * (g)
                residual_contributions[line_r_f] += v[line2_r_t] * (-g)
                residual_contributions[line_r_f] += v[line2_i_f] * (-b - B/2)
                residual_contributions[line_r_f] += v[line2_i_t] * (b)
                
                residual_contributions[line_i_f] += v[line2_r_f] * (b + B/2)
                residual_contributions[line_i_f] += v[line2_r_t] * (-b)
                residual_contributions[line_i_f] += v[line2_i_f] * (g)
                residual_contributions[line_i_f] += v[line2_i_t] * (-g)

                # For the KCL at the other node of the line
                residual_contributions[line_r_t] += v[line2_r_f] * (-g)
                residual_contributions[line_r_t] += v[line2_r_t] * (g)
                residual_contributions[line_r_t] += v[line2_i_f] * (b)
                residual_contributions[line_r_t] += v[line2_i_t] * (-b - B/2)

                residual_contributions[line_i_t] += v[line2_r_f] * (-b)
                residual_contributions[line_i_t] += v[line2_r_t] * (b + B/2)
                residual_contributions[line_i_t] += v[line2_i_f] * (-g)
                residual_contributions[line_i_t] += v[line2_i_t] * (g)

        return residual_contributions

