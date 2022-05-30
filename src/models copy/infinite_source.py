from collections import defaultdict


class InfiniteSource():

    def __init__(self):
        self.phase_slack_buses = []

    def collect_Y_stamps(self, state):
        for phase_slack_bus in self.phase_slack_buses:
            phase_slack_bus.collect_Y_stamps(state)

    def collect_J_stamps(self, state):
        for phase_slack_bus in self.phase_slack_buses:
            phase_slack_bus.collect_J_stamps(state)

    def set_initial_voltages(self, state, v):
        for phase_slack_bus in self.phase_slack_buses:
            phase_slack_bus.set_initial_voltages(state, v)

    def calculate_residuals(self, state, v):
        residual_contributions = defaultdict(lambda: 0)
        for phase_slack_bus in self.phase_slack_buses:
            phase_slack_bus.calculate_residuals(state, v, residual_contributions)
        return residual_contributions
