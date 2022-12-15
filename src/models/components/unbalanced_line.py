import typing
import numpy as np
from logic.stamping.lagrangestampdetails import LagrangeStampDetails
from models.components.bus import GROUND
from models.components.line import line_lh, shunt_lh
from logic.network.networkmodel import DxNetworkModel
from logic.stamping.matrixstamper import build_stamps_from_stampers
from models.wellknownvariables import Vr_from, Vr_to, Vi_from, Vi_to, Lr_from, Lr_to, Li_from, Li_to

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
    
    def __init__(self, network_model, impedances, shunt_admittances, from_element, to_element, length, phases="ABC"):
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
        self.network_model = network_model

        for phase in phases:
            self.lines.append(UnbalancedLinePhase(self.from_element, self.to_element, phase))

    def assign_nodes(self, node_index, optimization_enabled):
        self.stampers = {}

        # Go through all phases and build lagrange stamper for each line combination.
        for i in range(len(self.lines)):
            # Get the line
            line1 = self.lines[i]
            line1_from, line1_to = line1.get_nodes(self.network_model)

            eqn_map = {}
            eqn_map[Vr_from] = line1_from.node_Vr
            eqn_map[Vi_from] = line1_from.node_Vi
            eqn_map[Vr_to] = line1_to.node_Vr
            eqn_map[Vi_to] = line1_to.node_Vi
            eqn_map[Lr_from] = line1_from.node_lambda_Vr
            eqn_map[Li_from] = line1_from.node_lambda_Vi
            eqn_map[Lr_to] = line1_to.node_lambda_Vr
            eqn_map[Li_to] = line1_to.node_lambda_Vi

            eqn_map_shunt_from = {}
            eqn_map_shunt_from[Vr_from] = line1_from.node_Vr
            eqn_map_shunt_from[Vi_from] = line1_from.node_Vi
            eqn_map_shunt_from[Vr_to] = GROUND.node_Vr
            eqn_map_shunt_from[Vi_to] = GROUND.node_Vi
            eqn_map_shunt_from[Lr_from] = line1_from.node_lambda_Vr
            eqn_map_shunt_from[Li_from] = line1_from.node_lambda_Vi
            eqn_map_shunt_from[Lr_to] = GROUND.node_lambda_Vr
            eqn_map_shunt_from[Li_to] = GROUND.node_lambda_Vi

            eqn_map_shunt_to = {}
            eqn_map_shunt_to[Vr_from] = line1_to.node_Vr
            eqn_map_shunt_to[Vi_from] = line1_to.node_Vi
            eqn_map_shunt_to[Vr_to] = GROUND.node_Vr
            eqn_map_shunt_to[Vi_to] = GROUND.node_Vi
            eqn_map_shunt_to[Lr_from] = line1_to.node_lambda_Vr
            eqn_map_shunt_to[Li_from] = line1_to.node_lambda_Vi
            eqn_map_shunt_to[Lr_to] = GROUND.node_lambda_Vr
            eqn_map_shunt_to[Li_to] = GROUND.node_lambda_Vi

            # Go through all lines
            for j in range(len(self.lines)):
                line2 = self.lines[j]
                line2_from, line2_to = line2.get_nodes(self.network_model)

                var_map = {}
                var_map[Vr_from] = line2_from.node_Vr
                var_map[Vi_from] = line2_from.node_Vi
                var_map[Vr_to] = line2_to.node_Vr
                var_map[Vi_to] = line2_to.node_Vi
                var_map[Lr_from] = line2_from.node_lambda_Vr
                var_map[Li_from] = line2_from.node_lambda_Vi
                var_map[Lr_to] = line2_to.node_lambda_Vr
                var_map[Li_to] = line2_to.node_lambda_Vi

                if i == j:
                    segment = line_lh
                else:
                    segment = shunt_lh

                line_stamper = LagrangeStampDetails(segment, var_map, optimization_enabled, eqn_map)

                var_map_shunt_from = {}
                var_map_shunt_from[Vr_from] = line2_from.node_Vr
                var_map_shunt_from[Vi_from] = line2_from.node_Vi
                var_map_shunt_from[Vr_to] = GROUND.node_Vr
                var_map_shunt_from[Vi_to] = GROUND.node_Vi
                var_map_shunt_from[Lr_from] = line2_from.node_lambda_Vr
                var_map_shunt_from[Li_from] = line2_from.node_lambda_Vi
                var_map_shunt_from[Lr_to] = GROUND.node_lambda_Vr
                var_map_shunt_from[Li_to] = GROUND.node_lambda_Vi

                var_map_shunt_to = {}
                var_map_shunt_to[Vr_from] = line2_to.node_Vr
                var_map_shunt_to[Vi_from] = line2_to.node_Vi
                var_map_shunt_to[Vr_to] = GROUND.node_Vr
                var_map_shunt_to[Vi_to] = GROUND.node_Vi
                var_map_shunt_to[Lr_from] = line2_to.node_lambda_Vr
                var_map_shunt_to[Li_from] = line2_to.node_lambda_Vi
                var_map_shunt_to[Lr_to] = GROUND.node_lambda_Vr
                var_map_shunt_to[Li_to] = GROUND.node_lambda_Vi

                shunt_stamper_from = LagrangeStampDetails(shunt_lh, var_map_shunt_from, optimization_enabled, eqn_map_shunt_from)
                shunt_stamper_to = LagrangeStampDetails(shunt_lh, var_map_shunt_to, optimization_enabled, eqn_map_shunt_to)

                self.stampers[(line1_from, line2_to)] = (line_stamper, shunt_stamper_from, shunt_stamper_to)

    def get_connections(self):
        for line in self.lines:
            from_bus, to_bus = line.get_nodes(self.network_model)
            yield (from_bus, to_bus)

    def get_stamps(self):
        stamps = []
        for (is_own_phase, line_stamper, shunt_stamper_from, shunt_stamper_to, g, b, B) in self.__loop_line_stampers(self.network_model):
            stamps += build_stamps_from_stampers(self, 
                (line_stamper, [g, b, 0]),
                (shunt_stamper_from, [0, B/2, 0]),
                (shunt_stamper_to, [0, B/2, 0])
                )
        
        return stamps

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

                (line_stamper, shunt_stamper_from, shunt_stamper_to) = self.stampers[(line1_from, line2_to)]

                is_own_phase = i == j

                yield (is_own_phase, line_stamper, shunt_stamper_from, shunt_stamper_to, g, b, B)
