from collections import defaultdict
import typing
import numpy as np
from logic.lagrangestamper import SKIP, LagrangeStamper
from logic.matrixbuilder import MatrixBuilder
from models.positiveseq.shared import build_line_stamper
from models.positiveseq.branches import shunt_lh, Vr_from, Vr_to, Vi_from, Vi_to, Lr_from, Lr_to, Li_from, Li_to
from models.threephase.transmission_line_phase import TransmissionLinePhase
from models.threephase.edge import Edge

class TransmissionLine():
    
    def __init__(self, simulation_state, optimization_enabled, impedances, shunt_admittances, from_element, to_element, length, phases="ABC"):
        self.lines: typing.List[TransmissionLinePhase]
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

        self.stampers = {}

        # Go through all phases and build lagrange stamper for each line combination (including the line with itself)
        for i in range(len(self.lines)):
            # Get the line
            line1 = self.lines[i]

            # Collect the line's nodes for mutual susceptance calculation
            line1_from, _ = line1.get_nodes(simulation_state)
            line1_r_f, line1_i_f, line1_Lr_f, line1_Li_f = (line1_from.node_Vr, line1_from.node_Vi, line1_from.node_lambda_Vr, line1_from.node_lambda_Vi)

            # Go through all lines
            for j in range(len(self.lines)):
                line2 = self.lines[j]
                _, line2_to = line2.get_nodes(simulation_state)
                line2_r_t, line2_i_t, line2_Lr_t, line2_Li_t = (line2_to.node_Vr, line2_to.node_Vi, line2_to.node_lambda_Vr, line2_to.node_lambda_Vi)

                line_stamper = build_line_stamper(
                    line1_r_f, 
                    line1_i_f, 
                    line2_r_t, 
                    line2_i_t,
                    line1_Lr_f, 
                    line1_Li_f, 
                    line2_Lr_t, 
                    line2_Li_t,
                    optimization_enabled
                    )
                
                index_map = {}
                index_map[Vr_from] = line1_r_f
                index_map[Vi_from] = line1_i_f
                index_map[Vr_to] = line2_r_t
                index_map[Vi_to] = line2_i_t
                index_map[Lr_from] = line1_Lr_f
                index_map[Li_from] = line1_Li_f
                index_map[Lr_to] = line2_Lr_t
                index_map[Li_to] = line2_Li_t

                shunt_stamper = LagrangeStamper(shunt_lh, index_map, optimization_enabled)

                self.stampers[(line1_from, line2_to)] = (line_stamper, shunt_stamper)


    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, state):
        # Go through all phases
        for i in range(len(self.lines)):
            # Get the line
            line = self.lines[i]

            # Collect the line's nodes for mutual susceptance calculation
            line1_from, _ = line.get_nodes(state)

            # Go through all lines
            for j in range(len(self.lines)):
                g = np.real(self.admittances[i][j])
                b = np.imag(self.admittances[i][j])
                try:
                    B = np.imag(self.shunt_admittances[i][j])
                except IndexError:
                    B = 0


                line2 = self.lines[j]
                _, line2_to = line2.get_nodes(state)

                (line_stamper, shunt_stamper) = self.stampers[(line1_from, line2_to)]

                line_stamper.stamp_primal(Y, J, [g, b, tx_factor], v_previous)
                shunt_stamper.stamp_primal(Y, J, [B/2, tx_factor], v_previous)

                # # Collect stamps for mutual susceptance

                # # For the KCL at one node of the line
                # Y.stamp(line_r_f, line2_r_f, g)
                # Y.stamp(line_r_f, line2_r_t, -g)
                # Y.stamp(line_r_f, line2_i_f, -b - B/2)
                # Y.stamp(line_r_f, line2_i_t, b)
                
                # Y.stamp(line_i_f, line2_r_f, b + B/2)
                # Y.stamp(line_i_f, line2_r_t, -b)
                # Y.stamp(line_i_f, line2_i_f, g)
                # Y.stamp(line_i_f, line2_i_t, -g)

                # # For the KCL at the other node of the line
                # Y.stamp(line_r_t, line2_r_f, -g)
                # Y.stamp(line_r_t, line2_r_t, g)
                # Y.stamp(line_r_t, line2_i_f, b)
                # Y.stamp(line_r_t, line2_i_t, -b - B/2)

                # Y.stamp(line_i_t, line2_r_f, -b)
                # Y.stamp(line_i_t, line2_r_t, b + B/2)
                # Y.stamp(line_i_t, line2_i_f, -g)
                # Y.stamp(line_i_t, line2_i_t, g)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        # Go through all phases
        for i in range(len(self.lines)):
            # Get the line
            line = self.lines[i]

            # Collect the line's nodes for mutual susceptance calculation
            line1_from, _ = line.get_nodes(network_model)

            # Go through all lines
            for j in range(len(self.lines)):
                g = np.real(self.admittances[i][j])
                b = np.imag(self.admittances[i][j])
                try:
                    B = np.imag(self.shunt_admittances[i][j])
                except IndexError:
                    B = 0


                line2 = self.lines[j]
                _, line2_to = line2.get_nodes(network_model)

                (line_stamper, shunt_stamper) = self.stampers[(line1_from, line2_to)]

                line_stamper.stamp_dual(Y, J, [g, b, tx_factor], v_previous)
                shunt_stamper.stamp_dual(Y, J, [B/2, tx_factor], v_previous)


    def calculate_residuals(self, state, v):
        return {}

        residual_contributions = defaultdict(lambda: 0)
        # Go through all phases
        for i in range(len(self.lines)):
            # Get the line
            line1 = self.lines[i]

            # Collect the line's nodes
            line1_from, line1_to = line1.get_nodes(state)
            line1_r_f, line1_i_f, line1_r_t, line1_i_t = (line1_from.node_Vr, line1_from.node_Vi, line1_to.node_Vr, line1_to.node_Vi)

            # Go through all lines
            for j in range(len(self.lines)):
                g = np.real(self.admittances[i][j])
                b = np.imag(self.admittances[i][j])
                try:
                    B = np.imag(self.shunt_admittances[i][j])
                except IndexError:
                    B = 0


                line2 = self.lines[j]

                line2_from, line2_to = line2.get_nodes(state)
                line2_r_f, line2_i_f, line2_r_t, line2_i_t = (line2_from.node_Vr, line2_from.node_Vi, line2_to.node_Vr, line2_to.node_Vi)

                # For the KCL at one node of the line
                residual_contributions[line1_r_f] += v[line2_r_f] * (g)
                residual_contributions[line1_r_f] += v[line2_r_t] * (-g)
                residual_contributions[line1_r_f] += v[line2_i_f] * (-b - B/2)
                residual_contributions[line1_r_f] += v[line2_i_t] * (b)
                
                residual_contributions[line1_i_f] += v[line2_r_f] * (b + B/2)
                residual_contributions[line1_i_f] += v[line2_r_t] * (-b)
                residual_contributions[line1_i_f] += v[line2_i_f] * (g)
                residual_contributions[line1_i_f] += v[line2_i_t] * (-g)

                # For the KCL at the other node of the line
                residual_contributions[line1_r_t] += v[line2_r_f] * (-g)
                residual_contributions[line1_r_t] += v[line2_r_t] * (g)
                residual_contributions[line1_r_t] += v[line2_i_f] * (b)
                residual_contributions[line1_r_t] += v[line2_i_t] * (-b - B/2)

                residual_contributions[line1_i_t] += v[line2_r_f] * (-b)
                residual_contributions[line1_i_t] += v[line2_r_t] * (b + B/2)
                residual_contributions[line1_i_t] += v[line2_i_f] * (-g)
                residual_contributions[line1_i_t] += v[line2_i_t] * (g)

        return residual_contributions

