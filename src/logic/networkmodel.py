from cmath import pi
from itertools import count
from typing import Dict, List
from models.positiveseq.generator import Generator
from models.shared.L2infeasibility import L2InfeasibilityCurrent
from models.shared.bus import Bus
from models.shared.pqload import PQLoad
from models.shared.slack import Slack

class NetworkModel():
    def __init__(
        self, 
        is_three_phase: bool, 
        buses: List[Bus], 
        loads: List[PQLoad], 
        generators: List[Generator],
        slack: List[Slack],
        infeasibility_currents: List[L2InfeasibilityCurrent]
        ):
        self.is_three_phase = is_three_phase
        self.buses = buses
        self.loads = loads
        self.slack = slack
        self.generators = generators
        self.infeasibility_currents = infeasibility_currents

class TxNetworkModel(NetworkModel):
    def __init__(self, raw_data, infeasibility_currents):
        NetworkModel.__init__(
            self, 
            is_three_phase=False, 
            buses=raw_data['buses'],
            loads=raw_data['loads'],
            generators=raw_data['generators'],
            slack=raw_data['slack'],
            infeasibility_currents=infeasibility_currents
            )

        self.transformer = raw_data['xfmrs']
        self.branch = raw_data['branches']
        self.shunt = raw_data['shunts']

        self.linear_elments = self.branch + self.shunt + self.transformer + self.slack + self.infeasibility_currents

        self.nonlinear_elements = self.generators + self.loads

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
        NetworkModel.__init__(
            self, 
            is_three_phase=True, 
            buses=[],
            loads=[],
            generators=[],
            slack=[],
            infeasibility_currents=[]
            )

        # The next index of J to use
        self.next_var_idx = count(0)
        self.J_length = 0
        # The map from each bus id to the location of its (real, imaginary) state variables in J
        self.bus_map = {}
        # The map from a bus name to its bus id
        self.bus_name_map: Dict[str, Bus]
        self.bus_name_map = {}

        # All of the transmission lines
        self.transmission_lines = []
        # All of the transformers
        self.transformers = []
        # All of the capacitors
        self.capacitors = []
        # All of the fuses
        self.fuses = []
        # All of the switches
        self.switches = []
        # All of the regulators
        self.regulators = []

        self.infeasibility_currents = []

        # Reference nodes to be removed from the set of equations
        self.reference_r = None
        self.reference_i = None
    
    def get_NR_invariant_elements(self):
        return self.transmission_lines + self.slack + self.transformers + self.regulators + self.switches + self.infeasibility_currents

    def get_NR_variable_elements(self):
        return self.loads + self.capacitors + self.fuses
