from collections import defaultdict

class Switch():
    def __init__(self, status):
        self.phase_switches = []
        self.status = status

    def collect_Y_stamps(self, state):
        if self.status is "CLOSED":
            for phase_switch in self.phase_switches:
                phase_switch.collect_Y_stamps(state)
        
    def calculate_residuals(self, state, v):
        residual_contributions = defaultdict(lambda: 0)
        for phase_switch in self.phase_switches:
            phase_switch.calculate_residuals(state, v, residual_contributions)
        return residual_contributions