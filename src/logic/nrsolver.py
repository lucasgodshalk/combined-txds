import os
import numpy as np
from scipy.sparse.linalg import spsolve
from logic.matrixbuilder import MatrixBuilder
from logic.networkmodel import NetworkModel
from logic.powerflowsettings import PowerFlowSettings
from pathlib import Path

class NRSolver:

    def __init__(self, settings: PowerFlowSettings, network: NetworkModel, v_limiting):
        self.settings = settings
        self.network = network
        self.v_limiting = v_limiting

    def stamp_linear(self, Y: MatrixBuilder, J, tx_factor):
        for element in self.network.get_NR_invariant_elements():
            element.stamp_primal(Y, J, None, tx_factor, self.network)

        if self.settings.infeasibility_analysis:
            for element in self.network.get_NR_invariant_elements():
                element.stamp_dual(Y, J, None, tx_factor, self.network)

    def stamp_nonlinear(self, Y: MatrixBuilder, J, v_previous, tx_factor):
        for element in self.network.get_NR_variable_elements():
            element.stamp_primal(Y, J, v_previous, tx_factor, self.network)

        if self.settings.infeasibility_analysis:
            for element in self.network.get_NR_variable_elements():
                element.stamp_dual(Y, J, v_previous, tx_factor, self.network)

    def run_powerflow(self, v_init, tx_factor):
        if self.settings.dump_matrix:
            dump_matrix_map(self.network.matrix_map)

        v_previous = np.copy(v_init)

        Y = MatrixBuilder(self.settings)
        J_linear = [0] * len(v_init)

        self.stamp_linear(Y, J_linear, tx_factor)

        linear_index = Y.get_usage()

        for iteration_num in range(self.settings.max_iters):
            J = J_linear.copy()

            self.stamp_nonlinear(Y, J, v_previous, tx_factor)

            Y.assert_valid(check_zeros=True)

            Y_matrix = Y.to_matrix()

            if self.settings.dump_matrix:
                dump_Y(Y_matrix, iteration_num)
                dump_J(J, iteration_num)

            v_next = spsolve(Y_matrix, np.asarray(J, dtype=np.float64))

            if np.isnan(v_next).any():
                raise Exception("Error solving linear system")

            diff = v_next - v_previous

            err = abs(diff)

            err_max = err.max()
            
            if err_max < self.settings.tolerance:
                return (True, v_next, iteration_num)
            elif self.v_limiting != None and err_max > self.settings.tolerance:
                v_next = self.v_limiting.apply_limiting(v_next, v_previous, diff)

            v_previous = v_next
            Y.clear(retain_idx=linear_index)

        return (False, v_next, iteration_num)

def dump_matrix_map(map):
    Path("./dumps").mkdir(parents=True, exist_ok=True)

    filename = f'./dumps/lookup.txt'

    try:
        os.remove(filename)
    except OSError:
        pass

    with open(filename, 'a') as outputfile:
        for key in map.keys():
            outputfile.write(f"{key}: {map[key]}\r")

def dump_J(J, iteration):
    Path("./dumps").mkdir(parents=True, exist_ok=True)

    filename = f'./dumps/J{iteration + 1}_output.txt'

    try:
        os.remove(filename)
    except OSError:
        pass

    with open(filename, 'a') as outputfile:
        for i in range(len(J)):
            if J[i] != 0:
                outputfile.write(f"{i}: {J[i]:.5g}\r")

def dump_Y(Y, iteration):
    Path("./dumps").mkdir(parents=True, exist_ok=True)

    filename = f'./dumps/Y{iteration + 1}_output.txt'

    try:
        os.remove(filename)
    except OSError:
        pass

    with open(filename, 'a') as outputfile:
        for i in range(Y.shape[0]):
            for j in range(Y.shape[0]):
                if Y[i, j] != 0:
                    outputfile.write(f"{i}, {j}: {Y[i, j]:.5g}\r")