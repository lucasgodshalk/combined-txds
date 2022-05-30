from collections import defaultdict

class Capacitor():

    def __init__(self):
        self.phase_capacitors = []

    def collect_Y_stamps(self, state, v_estimate):
        for phase_capacitor in self.phase_capacitors:
            phase_capacitor.collect_Y_stamps(state, v_estimate)
        
    def calculate_residuals(self, state, v):
        residual_contributions = defaultdict(lambda: 0)
        for phase_capacitor in self.phase_capacitors:
            phase_capacitor.calculate_residuals(state, v, residual_contributions)
        return residual_contributions

    def set_initial_voltages(self, state, v):
        for phase_capacitor in self.phase_capacitors:
            phase_capacitor.set_initial_voltages(state, v)