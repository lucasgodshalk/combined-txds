import numpy as np
from logic.nrsolver import NRSolver
from logic.powerflowsettings import PowerFlowSettings

TX_ITERATIONS = 1000
TX_SCALE = 1.0 / TX_ITERATIONS

class HomotopyController:
    def __init__(self, settings: PowerFlowSettings, nrsolver: NRSolver) -> None:
        self.settings = settings
        self.nrsolver = nrsolver

    def run_powerflow(self, v_init):
        tx_factor = TX_ITERATIONS if self.settings.tx_stepping else 0

        iterations = 0
        v_next = np.copy(v_init)
        is_success = False

        while tx_factor >= 0:
            if tx_factor % 10 == 0:
                print(f'Tx factor: {tx_factor}')

            is_success, v_final, iteration_num = self.nrsolver.run_powerflow(v_next, tx_factor * TX_SCALE)
            iterations = iteration_num + 1
            tx_factor -= 1
            v_next = v_final

            if not is_success:
                break

        return (is_success, v_next, iterations, tx_factor * TX_SCALE)
