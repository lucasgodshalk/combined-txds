from collections import defaultdict
import typing
import numpy as np
from logic.lagrangestamper import LagrangeStamper
from logic.matrixbuilder import MatrixBuilder
from models.singlephase.line import line_lh
from models.singlephase.line import shunt_lh, Vr_from, Vr_to, Vi_from, Vi_to, Lr_from, Lr_to, Li_from, Li_to
from logic.networkmodel import DxNetworkModel
from models.helpers import merge_residuals

def calcInverse(Zmatrix):
    num_nnz = np.count_nonzero(Zmatrix)
    if num_nnz == 1:
        Zmatrix[Zmatrix == 0 + 0j] = np.inf  # Division in the next step will result in 0 + 0j in Y
        Ymatrix = np.divide(np.ones(np.shape(Zmatrix), dtype=complex), Zmatrix)
        return Ymatrix
    # Convert Matrix to Ymatrix
    # Find the rows of zero
    _rowZeroIdx = np.all(Zmatrix == 0, axis=1)
    Zmatrix_red = Zmatrix[~_rowZeroIdx]
    # Find the cols of zero
    _colZeroIdx = np.all(Zmatrix_red == 0, axis=0)
    Zmatrix_red = Zmatrix_red[:, ~_colZeroIdx]
    # Find the inverse of reduced matrix
    Ymatrix_red = np.linalg.inv(Zmatrix_red)
    # Remap to original format
    if len(Ymatrix_red) == 2:
        _rowIdx = list(_rowZeroIdx).index(True)
        _colIdx = list(_colZeroIdx).index(True)
        Ymatrix = np.insert(Ymatrix_red, _rowIdx, 0 + 1j * 0, axis=0)
        Ymatrix = np.insert(Ymatrix, _colIdx, 0 + 1j * 0, axis=1)
    else:
        Ymatrix = Ymatrix_red
    return Ymatrix

class UnbalancedLinePhase():

    def __init__(self
                , from_element
                , to_element
                , phase
                ):
        self.from_element = from_element
        self.to_element = to_element
        self.phase = phase
    
    def get_nodes(self, state: DxNetworkModel):
        from_bus = state.bus_name_map[self.from_element + "_" + self.phase]
        to_bus = state.bus_name_map[self.to_element + "_" + self.phase]
        return from_bus, to_bus

#Line where we have a collection of unbalanced phases (or a neutral wire) with admittance effects across wires.
class UnbalancedLine():
    
    def __init__(self, simulation_state, impedances, shunt_admittances, from_element, to_element, length, phases="ABC"):
        self.lines: typing.List[UnbalancedLinePhase]
        self.lines = []

        self.impedances = np.array(impedances)
        if not (self.impedances.shape == (3,3) or self.impedances.shape == (2,2) or self.impedances.shape == (1,1)):
            raise Exception("incorrect impedances matrix size, expected a square matrix at most size 3 by 3")
        # Convert the per-meter impedance values to absolute, based on line length (in meters)
        self.impedances *= length
        try:
            self.admittances = calcInverse(self.impedances)
        except Exception:
            try:
                self.admittances = np.linalg.inv(self.impedances)
            except Exception:    
                raise Exception("Transmission line was provided with a noninvertible matrix")
        if not np.allclose(np.dot(self.impedances, self.admittances), np.identity(len(phases))):
            raise Exception("np.linalg.inv was unable to find a good inverse to the impedance matrix")
        
        # Convert the per-meter shunt admittance values to absolute, based on line length (in meters)

        if shunt_admittances is None:
            self.shunt_admittances = None
        else:
            self.shunt_admittances = np.array(shunt_admittances)
            self.shunt_admittances *= length

        self.from_element = from_element
        self.to_element = to_element
        self.length = length
        self.simulation_state = simulation_state

        for phase in phases:
            self.lines.append(UnbalancedLinePhase(self.from_element, self.to_element, phase))

    def assign_nodes(self, node_index, optimization_enabled):
        self.stampers = {}

        # Go through all phases and build lagrange stamper for each line combination.
        for i in range(len(self.lines)):
            # Get the line
            line1 = self.lines[i]
            line1_from, line1_to = line1.get_nodes(self.simulation_state)

            eqn_map = {}
            eqn_map[Vr_from] = line1_from.node_Vr
            eqn_map[Vi_from] = line1_from.node_Vi
            eqn_map[Vr_to] = line1_to.node_Vr
            eqn_map[Vi_to] = line1_to.node_Vi
            eqn_map[Lr_from] = line1_from.node_lambda_Vr
            eqn_map[Li_from] = line1_from.node_lambda_Vi
            eqn_map[Lr_to] = line1_to.node_lambda_Vr
            eqn_map[Li_to] = line1_to.node_lambda_Vi

            # Go through all lines
            for j in range(len(self.lines)):
                line2 = self.lines[j]
                line2_from, line2_to = line2.get_nodes(self.simulation_state)

                var_map = {}
                var_map[Vr_from] = line2_from.node_Vr
                var_map[Vi_from] = line2_from.node_Vi
                var_map[Vr_to] = line2_to.node_Vr
                var_map[Vi_to] = line2_to.node_Vi
                var_map[Lr_from] = line2_from.node_lambda_Vr
                var_map[Li_from] = line2_from.node_lambda_Vi
                var_map[Lr_to] = line2_to.node_lambda_Vr
                var_map[Li_to] = line2_to.node_lambda_Vi

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

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network):
        for (line_stamper, shunt_stamper, g, b, B) in self.__loop_line_stampers(network):
            line_stamper.stamp_dual(Y, J, [g, b, tx_factor], v_previous)
            shunt_stamper.stamp_dual(Y, J, [B/2, tx_factor], v_previous)

    def calculate_residuals(self, state, v):
        residuals = {}

        for (line_stamper, shunt_stamper, g, b, B) in self.__loop_line_stampers(state):
            line_residuals = line_stamper.calc_residuals([g, b, 0], v)
            shunt_residuals = shunt_stamper.calc_residuals([B/2, 0], v)
            merge_residuals(residuals, line_residuals, shunt_residuals)

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

                B = 0
                if self.shunt_admittances is not None:
                    try:
                        B = np.imag(self.shunt_admittances[i][j])
                    except IndexError:
                        pass

                line2 = self.lines[j]
                _, line2_to = line2.get_nodes(state)

                (line_stamper, shunt_stamper) = self.stampers[(line1_from, line2_to)]

                yield (line_stamper, shunt_stamper, g, b, B)
