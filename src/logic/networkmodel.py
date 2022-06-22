from cmath import pi
from itertools import count

class NetworkModel():
    def __init__(self, is_three_phase: bool) -> None:
        self.is_three_phase = is_three_phase

class TxNetworkModel(NetworkModel):
    def __init__(self, raw_data, extra_linear_elements):
        NetworkModel.__init__(self, is_three_phase=False)

        self.buses = raw_data['buses']
        self.slack = raw_data['slack']
        self.generator = raw_data['generators']
        self.transformer = raw_data['xfmrs']
        self.branch = raw_data['branches']
        self.shunt = raw_data['shunts']
        self.load = raw_data['loads']

        self.linear_elments = self.branch + self.shunt + self.transformer + self.slack + extra_linear_elements

        self.nonlinear_elements = self.generator + self.load

    def get_NR_invariant_elements(self):
        return self.linear_elments

    def get_NR_variable_elements(self):
        return self.nonlinear_elements
    
    def get_all_elements(self):
        return self.buses + self.get_NR_invariant_elements() + self.get_NR_variable_elements()

class DxNetworkModel(NetworkModel):
    # The id of the node connected to ground
    GROUND_NODE = -1
    OMEGA = 2 * pi * 60

    def __init__(self):
        NetworkModel.__init__(self, is_three_phase=True)

        # The next index of J to use
        self.next_var_idx = count(0)
        self.J_length = 0
        # The map from each bus id to the location of its (real, imaginary) state variables in J
        self.bus_map = {}
        # The map from a bus name to its bus id
        self.bus_name_map = {}

        # All of the loads    
        self.loads = []
        # All of the transmission lines
        self.transmission_lines = []
        # All of the infinite sources (multi-phase slack buses)
        self.infinite_sources = []
        # All of the transformers
        self.transformers = []
        # All of the other buses
        self.buses = []
        # All of the capacitors
        self.capacitors = []
        # All of the fuses
        self.fuses = []
        # All of the switches
        self.switches = []
        # All of the regulators
        self.regulators = []

        # Reference nodes to be removed from the set of equations
        self.reference_r = None
        self.reference_i = None
    
    def get_NR_invariant_elements(self):
        return self.transmission_lines + self.infinite_sources + self.transformers + self.regulators + self.switches

    def get_NR_variable_elements(self):
        return self.loads + self.capacitors + self.fuses
