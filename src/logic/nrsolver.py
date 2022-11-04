import os
import numpy as np
from scipy.sparse.linalg import spsolve
from logic.stamping.matrixbuilder import MatrixBuilder
from logic.network.networkmodel import NetworkModel
from logic.powerflowsettings import PowerFlowSettings
from pathlib import Path
from colorama import init
from termcolor import colored
from logic.stamping.matrixstamper import MatrixStamper
from models.singlephase.bus import Bus
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

    def stamp_linear(self, Y: MatrixBuilder, J, tx_factor):
        self.matrix_stamper.stamp_linear(Y, J, tx_factor)

    def stamp_nonlinear(self, Y: MatrixBuilder, J, v_previous, tx_factor):
        self.matrix_stamper.stamp_nonlinear(Y, J, v_previous)

    def run_powerflow(self, v_init, tx_factor):
        self.matrix_stamper = MatrixStamper(self.settings.infeasibility_analysis)

        stamps = []
        for element in self.network.get_all_elements():
            if type(element) == Bus:
                continue
            
            stamps += element.get_stamps()
        
        if self.network.optimization != None:
            stamps += self.network.optimization.get_stamps()

        self.matrix_stamper.register_stamps(stamps)

        if self.settings.dump_matrix:
            dump_matrix_map(self.network.matrix_map)

        v_previous = np.copy(v_init)

        Y = MatrixBuilder(self.settings)
        J_linear = np.zeros(len(v_init))

        self.stamp_linear(Y, J_linear, tx_factor)

        linear_index = Y.get_usage()

        max_error_history = []

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

            diff_mask = self.get_or_create_diff_mask()

            err = abs(diff[diff_mask])

            err_max = err.max()
            err_arg_max = np.argmax(err)

            if err_arg_max in self.network.matrix_map:
                err_max_attr = self.network.matrix_map[err_arg_max]
            else:
                err_max_attr = "other"

            print(colored("The maximum error for this iteration is %f at %s"%(err_max, err_max_attr), 'green')) 
            max_error_history.append(err_max)

            if len(max_error_history) % 50 == 0:
                #We check regularly if the solver is making progress and bail if not.
                x = np.array(range(len(max_error_history)))
                A = np.vstack([x, np.ones(len(x))]).T
                y = np.array(max_error_history)
                m, _ = np.linalg.lstsq(A, y, rcond=None)[0]
                if m > 0:
                    return (False, v_next, iteration_num)
            
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