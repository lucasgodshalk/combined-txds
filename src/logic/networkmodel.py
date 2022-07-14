from cmath import pi
from itertools import count
from typing import Dict, List

import numpy as np
from logic.powerflowsettings import PowerFlowSettings
from models.positiveseq.generator import Generator
from models.shared.L2infeasibility import L2InfeasibilityCurrent
from models.shared.bus import Bus
from models.shared.pqload import PQLoad
from models.shared.slack import Slack

BUS_Vr_FLAT = 1
BUS_Vi_FLAT = 0
BUS_Q_FLAT = -1

class NetworkModel():
    def __init__(
        self, 
        is_three_phase: bool, 
        ):
        self.is_three_phase = is_three_phase

        self.buses: List[Bus]
        self.buses = []
        self.loads: List[PQLoad]
        self.loads = []
        self.slack: List[Slack]
        self.slack = []
        self.generators: List[Generator]
        self.generators = []
        self.infeasibility_currents: List[L2InfeasibilityCurrent]
        self.infeasibility_currents = []
        self.size_Y = None

class TxNetworkModel(NetworkModel):
    def __init__(self, buses=[], loads=[], slack=[], generators=[], infeasibility_currents=[], transformers=[], branches=[], shunts=[]):
        NetworkModel.__init__(self, is_three_phase=False)

        self.buses = buses
        self.loads = loads
        self.slack = slack
        self.generators = generators
        self.infeasibility_currents = infeasibility_currents
        self.transformer = transformers
        self.branch = branches
        self.shunt = shunts

    def get_NR_invariant_elements(self):
        return self.branch + self.shunt + self.transformer + self.slack + self.infeasibility_currents

    def get_NR_variable_elements(self):
        return self.generators + self.loads
    
    def get_all_elements(self):
        return self.buses + self.get_NR_invariant_elements() + self.get_NR_variable_elements()

    def generate_v_init(self, settings: PowerFlowSettings):
        v_init = np.zeros(self.size_Y)

        for bus in self.buses:
            (vr_idx, vr_init) = bus.get_Vr_init()
            v_init[vr_idx] = BUS_Vr_FLAT if settings.flat_start else vr_init

            (vi_idx, vi_init) = bus.get_Vi_init()
            v_init[vi_idx] = BUS_Vi_FLAT if settings.flat_start else vi_init

            if settings.infeasibility_analysis:
                Lr_idx, Lr_init = bus.get_Lr_init()
                v_init[Lr_idx] = Lr_init

                Li_idx, Li_init = bus.get_Li_init()
                v_init[Li_idx] = Li_init

                LQ_idx, LQ_init = bus.get_LQ_init()
                if LQ_idx is not None:
                    v_init[LQ_idx] = LQ_init

        for generator in self.generators:
            v_init[generator.bus.node_Q] = (generator.Qmin + generator.Qmax) / 2 if settings.flat_start else generator.Qinit

        for slack in self.slack:
            v_init[slack.slack_Ir] = 0 if settings.flat_start else slack.Pinit
            v_init[slack.slack_Ii] = 0 if settings.flat_start else slack.Qinit

        return v_init

class DxNetworkModel(NetworkModel):
    # The id of the node connected to ground
    GROUND_NODE = -1
    OMEGA = 2 * pi * 60

    def __init__(self):
        NetworkModel.__init__(self, is_three_phase=True)

        # The next index of J to use
        self.next_var_idx = count(0)
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

    def generate_v_init(self, settings: PowerFlowSettings):
        v_init = np.zeros(self.size_Y)

        # Set initial voltage values for all other buses (one object per phase)
        for bus in self.buses:
            bus.set_initial_voltages(v_init)
        
        return v_init