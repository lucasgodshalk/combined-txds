from collections import defaultdict


class InfiniteSource():

    def __init__(self):
        self.phase_slack_buses = []

    def stamp_primal(self, Y, J, v_previous, tx_factor, state):
        for phase_slack_bus in self.phase_slack_buses:
            phase_slack_bus.stamp_primal(Y, J, v_previous, tx_factor, state)

    def set_initial_voltages(self, state, v):
        for phase_slack_bus in self.phase_slack_buses:
            phase_slack_bus.set_initial_voltages(state, v)

    def calculate_residuals(self, state, v):
        residual_contributions = {}
        for phase_slack_bus in self.phase_slack_buses:
            residual_contributions.update(phase_slack_bus.calculate_residuals(state, v))
        return residual_contributions
