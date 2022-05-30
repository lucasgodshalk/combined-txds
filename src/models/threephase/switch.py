from collections import defaultdict

class Switch():
    def __init__(self, status):
        self.phase_switches = []
        self.status = status

    def stamp_primal(self, Y, J, v_previous, tx_factor, state):
        if self.status is "CLOSED":
            for phase_switch in self.phase_switches:
                phase_switch.stamp_primal(Y, J, v_previous, tx_factor, state)
        
    def calculate_residuals(self, state, v):
        residual_contributions = defaultdict(lambda: 0)
        for phase_switch in self.phase_switches:
            phase_switch.calculate_residuals(state, v, residual_contributions)
        return residual_contributions