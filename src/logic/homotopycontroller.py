import numpy as np
from logic.network.networkmodel import NetworkModel
from logic.nrsolver import NRSolver
from logic.powerflowsettings import PowerFlowSettings
from logic.stamping.matrixstamper import build_matrix_stamper

TX_ITERATIONS = 100
TX_SCALE = 1.0 / TX_ITERATIONS

#Simplistic homotopy process, where we just linearly modify the homotopy factor
#(referred to as the 'tx_factor') until we hit the original solution.
class HomotopyController:
    def __init__(self, settings: PowerFlowSettings, network: NetworkModel, solver: NRSolver) -> None:
        self.network = network
        self.settings = settings
        self.nrsolver = solver

    def run_powerflow(self, v_init):
        matrix_stamper = build_matrix_stamper(self.network)

        #optimistically try to solve without homotopy first.
        is_success, v_final, iteration_num = self.nrsolver.run_powerflow(matrix_stamper, v_init, 0)
        if is_success or not self.settings.tx_stepping:
            return (is_success, v_final, iteration_num, 0, matrix_stamper.calc_residuals(0, v_final, iteration_num))

        tx_factor = TX_ITERATIONS
        iterations = 0
        v_next = v_init
        is_success = False

        while tx_factor >= 0:
            if tx_factor % 10 == 0:
                print(f'Tx factor: {tx_factor}')

            is_success, v_final, iteration_num = self.nrsolver.run_powerflow(matrix_stamper, v_next, tx_factor * TX_SCALE)
            iterations = iteration_num + 1
            v_next = v_final

            if not is_success:
                break

            tx_factor -= 1

        return (is_success, v_next, iterations, tx_factor * TX_SCALE, matrix_stamper.calc_residuals(0, v_final, iteration_num))
