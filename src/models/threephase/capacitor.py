from collections import defaultdict

class Capacitor():

    def __init__(self):
        self.phase_capacitors = []

    def stamp_primal(self, Y, J, v_estimate, tx_factor, state):
        for phase_capacitor in self.phase_capacitors:
            phase_capacitor.stamp_primal(Y, J, v_estimate, tx_factor, state)
        
    def calculate_residuals(self, state, v):
        residual_contributions = defaultdict(lambda: 0)
        for phase_capacitor in self.phase_capacitors:
            phase_capacitor.calculate_residuals(state, v, residual_contributions)
        return residual_contributions

    def set_initial_voltages(self, state, v):
        for phase_capacitor in self.phase_capacitors:
            phase_capacitor.set_initial_voltages(state, v)