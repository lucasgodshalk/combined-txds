from collections import defaultdict


class PQLoad():

    def __init__(self):
        # The phase loads associated with this PQ load
        self.phase_loads = []
        
    def stamp_primal(self, Y, J, v, tx_factor, state):
        for phase_load in self.phase_loads:
            phase_load.stamp_primal(Y, J, v, tx_factor, state)

    def stamp_dual(self, Y, J, v, tx_factor, state):
        for phase_load in self.phase_loads:
            phase_load.stamp_dual(Y, J, v, tx_factor, state)

    def set_initial_voltages(self, state, v):
        for phase_load in self.phase_loads:
            phase_load.set_initial_voltages(state, v)
        
    def calculate_residuals(self, state, v):
        residual_contributions = {}
        for phase_load in self.phase_loads:
            residual_contributions.update(phase_load.calculate_residuals(state, v))
        return residual_contributions

