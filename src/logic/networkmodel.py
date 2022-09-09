from cmath import pi
from itertools import count
from typing import Dict, List

import numpy as np
from logic.powerflowsettings import PowerFlowSettings
from models.singlephase.generator import Generator
from models.singlephase.bus import Bus
from models.singlephase.load import Load
from models.singlephase.slack import Slack
from models.singlephase.transformer import Transformer
from models.threephase.center_tap_transformer import CenterTapTransformer
from models.singlephase.switch import Switch, SwitchStatus

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
        self.loads: List[Load]
        self.loads = []
        self.slack: List[Slack]
        self.slack = []
        self.generators: List[Generator]
        self.generators = []
        self.transformers: List[Transformer]
        self.transformers = []
        self.switches: List[Switch]
        self.switches = []

        self.optimization = None

        self.size_Y = None
        self.matrix_version = -1

    def assign_matrix(self, optimization_enabled):
        node_index = count(0)

        for ele in self.get_all_elements():
            ele.assign_nodes(node_index, optimization_enabled)

        self.size_Y = next(node_index)

        self.matrix_map = {}
        for bus in self.buses:
            self.matrix_map[f"bus:{bus.NodeName}:{bus.NodePhase}:Vr"] = bus.node_Vr
            self.matrix_map[f"bus:{bus.NodeName}:{bus.NodePhase}:Vi"] = bus.node_Vi

        for slack in self.slack:
            self.matrix_map[f"slack:{slack.bus.NodeName}:{slack.bus.NodePhase}:Ir"] = slack.slack_Ir
            self.matrix_map[f"slack:{slack.bus.NodeName}:{slack.bus.NodePhase}:Ii"] = slack.slack_Ii

        for xfmr in self.transformers:
            if isinstance(xfmr, CenterTapTransformer):
                self.matrix_map[f"xfmr-ct:{xfmr.coils[0].from_node.NodeName}:{xfmr.coils[0].from_node.NodePhase}:L1_Ir"] = xfmr.node_L1_Ir
                self.matrix_map[f"xfmr-ct:{xfmr.coils[0].from_node.NodeName}:{xfmr.coils[0].from_node.NodePhase}:L1-Ii"] = xfmr.node_L1_Ii
                self.matrix_map[f"xfmr-ct:{xfmr.coils[0].from_node.NodeName}:{xfmr.coils[0].from_node.NodePhase}:L2-Ir"] = xfmr.node_L2_Ir
                self.matrix_map[f"xfmr-ct:{xfmr.coils[0].from_node.NodeName}:{xfmr.coils[0].from_node.NodePhase}:L2-Ii"] = xfmr.node_L2_Ii
            else:
                self.matrix_map[f"xfmr:{xfmr.from_bus_pos.NodeName}:{xfmr.from_bus_pos.NodePhase}:Ir-pri"] = xfmr.node_primary_Ir
                self.matrix_map[f"xfmr:{xfmr.from_bus_pos.NodeName}:{xfmr.from_bus_pos.NodePhase}:Ii-pri"] = xfmr.node_primary_Ii
                self.matrix_map[f"xfmr:{xfmr.from_bus_pos.NodeName}:{xfmr.from_bus_pos.NodePhase}:Vr-sec"] = xfmr.node_secondary_Vr
                self.matrix_map[f"xfmr:{xfmr.from_bus_pos.NodeName}:{xfmr.from_bus_pos.NodePhase}:Vi-sec"] = xfmr.node_secondary_Vi

        for switch in self.switches:
            if switch.status == SwitchStatus.OPEN:
                continue

            self.matrix_map[f"switch:{switch.from_node.NodeName}:{switch.to_node.NodePhase}:Ir"] = switch.vs.Ir_index
            self.matrix_map[f"switch:{switch.from_node.NodeName}:{switch.to_node.NodePhase}:Ii"] = switch.vs.Ii_index

        for load in self.loads:
            self.matrix_map[f"load:{load.from_bus.NodeName}:{load.from_bus.NodePhase}:Ir"] = load.node_Ir
            self.matrix_map[f"load:{load.from_bus.NodeName}:{load.from_bus.NodePhase}:Ii"] = load.node_Ii

        self.matrix_version += 1


class TxNetworkModel(NetworkModel):
    def __init__(
        self, 
        buses=[], 
        loads=[], 
        slack=[], 
        generators=[], 
        transformers=[], 
        branches=[], 
        shunts=[],
        voltage_sources=[]
        ):
        NetworkModel.__init__(self, is_three_phase=False)
        
        self.buses = buses
        self.loads = loads
        self.slack = slack
        self.generators = generators
        self.transformers = transformers
        self.branches = branches
        self.shunts = shunts
        self.voltage_sources = voltage_sources

    def get_NR_invariant_elements(self):
        return self.branches + self.shunts + self.transformers + self.slack + self.switches + self.voltage_sources

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

        # The map from each bus id to the location of its (real, imaginary) state variables in J
        self.bus_map = {}
        # The map from a bus name to its bus id
        self.bus_name_map: Dict[str, Bus]
        self.bus_name_map = {}
        
        # The map from a load name to its Load object
        self.load_name_map: Dict[str, Load]
        self.load_name_map = {}

        # All of the transmission lines
        self.branches = []
        # All of the capacitors
        self.capacitors = []
        # All of the fuses
        self.fuses = []
        # All of the regulators
        self.regulators = []

        # Reference nodes to be removed from the set of equations
        self.reference_r = None
        self.reference_i = None
    
    def get_NR_invariant_elements(self):
        return self.slack + self.branches + self.transformers + self.regulators + self.switches + self.fuses + self.capacitors

    def get_NR_variable_elements(self):
        return self.loads

    def get_all_elements(self):
        return self.buses + self.get_NR_invariant_elements() + self.get_NR_variable_elements()

    def generate_v_init(self, settings: PowerFlowSettings):
        v_init = np.zeros(self.size_Y)

        # Set initial voltage values for all other buses (one object per phase)
        for bus in self.buses:
            bus.set_initial_voltages(v_init)
        
        return v_init