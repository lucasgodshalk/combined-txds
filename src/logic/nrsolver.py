import os
import numpy as np
from scipy.sparse.linalg import spsolve
from logic.stamping.matrixbuilder import MatrixBuilder
from logic.network.networkmodel import NetworkModel
from logic.powerflowsettings import PowerFlowSettings
from logic.stamping.matrixstamper import MatrixStamper
from pathlib import Path
from colorama import init
from termcolor import colored
# use Colorama to make Termcolor work on Windows too
init()

class NRSolver:

    def __init__(self, settings: PowerFlowSettings, network: NetworkModel, v_limiting):
        self.settings = settings
        self.network = network
        self.v_limiting = v_limiting
        self.diff_mask = None

    def get_or_create_diff_mask(self):
        if self.diff_mask != None:
            return self.diff_mask

        self.diff_mask = [False] * self.network.size_Y
        for bus in self.network.buses:
           self.diff_mask[bus.node_Vr] = True
           self.diff_mask[bus.node_Vi] = True

        return self.diff_mask

    def stamp_linear(self, matrix_stamper, Y: MatrixBuilder, J, tx_factor):
        matrix_stamper.stamp_linear(Y, J, tx_factor)

    def stamp_nonlinear(self, matrix_stamper, Y: MatrixBuilder, J, v_previous):
        matrix_stamper.stamp_nonlinear(Y, J, v_previous)

    def run_powerflow(self, matrix_stamper: MatrixStamper, v_init, tx_factor):
        if self.settings.dump_matrix:
            dump_matrix_map(self.network.matrix_map)

        v_previous = np.copy(v_init)

        Y = MatrixBuilder(self.settings)
        J_linear = np.zeros(len(v_init))

        self.stamp_linear(matrix_stamper, Y, J_linear, tx_factor)

        linear_index = Y.get_usage()

        max_residual_history = []

        for iteration_num in range(self.settings.max_iters):
            J = J_linear.copy()

            self.stamp_nonlinear(matrix_stamper, Y, J, v_previous)

            Y.assert_valid(check_zeros=True)

            Y_matrix = Y.to_matrix()

            if self.settings.dump_matrix:
                dump_Y(Y_matrix, iteration_num)
                dump_J(J, iteration_num)

            v_next = spsolve(Y_matrix, np.asarray(J, dtype=np.float64))

            if np.isnan(v_next).any():
                raise Exception("Error solving linear system")

            residuals = matrix_stamper.calc_residuals(tx_factor, v_next)
            residual_max = residuals.max_residual
            residual_max_idx = residuals.max_residual_idx

            if residual_max_idx in self.network.matrix_map:
                residual_max_attr = self.network.matrix_map[residual_max_idx]
            else:
                residual_max_attr = "other"

            print(colored(f"The maximum residual for iteration {iteration_num} is {residual_max} at {residual_max_attr}", 'green')) 
            max_residual_history.append(residual_max)

            if len(max_residual_history) % 50 == 0:
                #We check regularly if the solver is making progress and bail if not.
                x = np.array(range(len(max_residual_history)))
                A = np.vstack([x, np.ones(len(x))]).T
                y = np.array(max_residual_history)
                m, _ = np.linalg.lstsq(A, y, rcond=None)[0]
                if m > 0:
                    return (False, v_next, iteration_num)
            
            if residual_max < self.settings.tolerance:
                if self.settings.dump_matrix:
                    dump_v(v_next)

                return (True, v_next, iteration_num)
            elif self.v_limiting != None and residual_max > self.settings.tolerance:
                v_next = self.v_limiting.apply_limiting(v_next, v_previous)

            v_previous = v_next
            Y.clear(retain_idx=linear_index)

        if self.settings.dump_matrix:
            dump_v(v_next)

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

def dump_v(v):
    Path("./dumps").mkdir(parents=True, exist_ok=True)

    filename = f'./dumps/v_output.txt'

    try:
        os.remove(filename)
    except OSError:
        pass

    with open(filename, 'a') as outputfile:
        for i in range(len(v)):
            if v[i] != 0:
                outputfile.write(f"{i}: {v[i]:.5g}\r") 

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