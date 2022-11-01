import numpy as np
from logic.nrsolver import NRSolver
from logic.powerflowsettings import PowerFlowSettings

TX_ITERATIONS = 1000
TX_SCALE = 1.0 / TX_ITERATIONS

#Simplistic homotopy process, where we just linearly modify the homotopy factor
#(referred to as the 'tx_factor') until we hit the original solution.
class HomotopyController:
    def __init__(self, settings: PowerFlowSettings, solver: NRSolver) -> None:
        self.settings = settings
        self.nrsolver = solver

    def run_powerflow(self, v_init):
        #optimistically try to solve without homotopy first.
        is_success, v_final, iteration_num = self.nrsolver.run_powerflow(v_init, 0)
        if is_success or not self.settings.tx_stepping:
            return (is_success, v_final, iteration_num, 0)

        tx_factor = TX_ITERATIONS
        iterations = 0
        v_next = v_init
        is_success = False

        while tx_factor >= 0:
            if tx_factor % 10 == 0:
                print(f'Tx factor: {tx_factor}')

            is_success, v_final, iteration_num = self.nrsolver.run_powerflow(v_next, tx_factor * TX_SCALE)
            iterations = iteration_num + 1
            v_next = v_final

            if not is_success:
                break

            tx_factor -= 1

        return (is_success, v_next, iterations, tx_factor * TX_SCALE)
