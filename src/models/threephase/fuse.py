from collections import defaultdict

class Fuse():
    def __init__(self, status):
        self.phase_fuses = []
        self.status = status

    def stamp_primal(self, Y, J, v_estimate, tx_factor, state):
        if self.status is "CLOSED":
            for phase_fuse in self.phase_fuses:
                phase_fuse.stamp_primal(Y, J, v_estimate, tx_factor, state)
        
    def calculate_residuals(self, state, v):
        residual_contributions = defaultdict(lambda: 0)
        for phase_fuse in self.phase_fuses:
            phase_fuse.calculate_residuals(state, v, residual_contributions)
        return residual_contributions