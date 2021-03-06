from collections import defaultdict
import typing
import numpy as np
from logic.lagrangestamper import SKIP, LagrangeStamper
from logic.matrixbuilder import MatrixBuilder
from models.shared.line import line_lh
from models.positiveseq.branch import shunt_lh, Vr_from, Vr_to, Vi_from, Vi_to, Lr_from, Lr_to, Li_from, Li_to
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
        self.simulation_state = simulation_state

        for phase in phases:
            self.lines.append(TransmissionLinePhase(self.from_element, self.to_element, phase))

        self.stampers = {}

        # Go through all phases and build lagrange stamper for each line combination.
        for i in range(len(self.lines)):
            # Get the line
            line1 = self.lines[i]
            line1_from, line1_to = line1.get_nodes(simulation_state)

            # Go through all lines
            for j in range(len(self.lines)):
                line2 = self.lines[j]
                line2_from, line2_to = line2.get_nodes(simulation_state)

                var_map = {}
                var_map[Vr_from] = line2_from.node_Vr
                var_map[Vi_from] = line2_from.node_Vi
                var_map[Vr_to] = line2_to.node_Vr
                var_map[Vi_to] = line2_to.node_Vi
                var_map[Lr_from] = line2_from.node_lambda_Vr
                var_map[Li_from] = line2_from.node_lambda_Vi
                var_map[Lr_to] = line2_to.node_lambda_Vr
                var_map[Li_to] = line2_to.node_lambda_Vi

                eqn_map = {}
                eqn_map[Vr_from] = line1_from.node_Vr
                eqn_map[Vi_from] = line1_from.node_Vi
                eqn_map[Vr_to] = line1_to.node_Vr
                eqn_map[Vi_to] = line1_to.node_Vi
                eqn_map[Lr_from] = line1_from.node_lambda_Vr
                eqn_map[Li_from] = line1_from.node_lambda_Vi
                eqn_map[Lr_to] = line1_to.node_lambda_Vr
                eqn_map[Li_to] = line1_to.node_lambda_Vi

                line_stamper = LagrangeStamper(line_lh, var_map, optimization_enabled, eqn_map)

                shunt_stamper = LagrangeStamper(shunt_lh, var_map, optimization_enabled, eqn_map)

                self.stampers[(line1_from, line2_to)] = (line_stamper, shunt_stamper)

    def get_connections(self):
        for line in self.lines:
            from_bus, to_bus = line.get_nodes(self.simulation_state)
            yield (from_bus, to_bus)

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, state):
        for (line_stamper, shunt_stamper, g, b, B) in self.__loop_line_stampers(state):
            line_stamper.stamp_primal(Y, J, [g, b, tx_factor], v_previous)
            shunt_stamper.stamp_primal(Y, J, [B/2, tx_factor], v_previous)

    def stamp_primal_symbols(self, Y: MatrixBuilder, J, state):
        for (line_stamper, shunt_stamper, g, b, B) in self.__loop_line_stampers(state):
            line_stamper.stamp_primal_symbols(Y, J)
            shunt_stamper.stamp_primal_symbols(Y, J)    

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        for (line_stamper, shunt_stamper, g, b, B) in self.__loop_line_stampers(network_model):
            line_stamper.stamp_dual(Y, J, [g, b, tx_factor], v_previous)
            shunt_stamper.stamp_dual(Y, J, [B/2, tx_factor], v_previous)

    def calculate_residuals(self, state, v):
        residuals = defaultdict(lambda:0)

        for (line_stamper, shunt_stamper, g, b, B) in self.__loop_line_stampers(state):
            for (key, value) in line_stamper.calc_residuals([g, b, 1], v).items():
                residuals[key] += value
            for (key, value) in shunt_stamper.calc_residuals([B/2, 1], v).items():
                residuals[key] += value

        return residuals

    def __loop_line_stampers(self, state):
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

                yield (line_stamper, shunt_stamper, g, b, B)
