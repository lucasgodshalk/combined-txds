import numpy as np
from scipy.sparse.linalg import spsolve
from logic.matrixbuilder import MatrixBuilder
from logic.powerflowsettings import PowerFlowSettings

class NRSolver:

    def __init__(self, settings: PowerFlowSettings, network_model, v_limiting):
        self.settings = settings
        self.network_model = network_model
        self.v_limiting = v_limiting

    def stamp_linear(self, Y: MatrixBuilder, J, tx_factor):
        for element in self.network_model.get_NR_invariant_elements():
            element.stamp_primal(Y, J, None, tx_factor, self.network_model)

        if self.settings.infeasibility_analysis:
            for element in self.network_model.get_NR_invariant_elements():
                element.stamp_dual(Y, J, None, tx_factor, self.network_model)

    def stamp_nonlinear(self, Y: MatrixBuilder, J, v_previous, tx_factor):
        for element in self.network_model.get_NR_variable_elements():
            element.stamp_primal(Y, J, v_previous, tx_factor, self.network_model)

        if self.settings.infeasibility_analysis:
            for element in self.network_model.get_NR_variable_elements():
                element.stamp_dual(Y, J, v_previous, tx_factor, self.network_model)

    def run_powerflow(self, v_init, tx_factor):
        v_previous = np.copy(v_init)

        Y = MatrixBuilder(self.settings)
        J_linear = [0] * len(v_init)

        self.stamp_linear(Y, J_linear, tx_factor)

        linear_index = Y.get_usage()

        for iteration_num in range(self.settings.max_iters):
            J = J_linear.copy()

            self.stamp_nonlinear(Y, J, v_previous, tx_factor)

            Y.assert_valid(check_zeros=True)

            v_next = spsolve(Y.to_matrix(), np.asarray(J, dtype=np.float64))

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


def dump_Y(Y):
    with open('Y_output.txt', 'a') as outputfile:
        for i in range(Y.shape[0]):
            for j in range(Y.shape[0]):
                outputfile.write(f"{i}, {j}: {Y[i, j]:.5g}\r")