import math
import time
from logic.homotopycontroller import HomotopyController
from logic.nrsolver import NRSolver
from logic.networkmodel import TxNetworkModel
from logic.powerflowsettings import PowerFlowSettings
from logic.parsers.parser import parse_raw
from itertools import count
from logic.parsers.anoeds_parser import Parser
from logic.powerflowresults import PowerFlowResults
from logic.v_limiting import PositiveSeqVoltageLimiting
from models.shared.L2infeasibility import L2InfeasibilityCurrent

class PowerFlow:
    def __init__(self, netlist, settings: PowerFlowSettings = PowerFlowSettings()) -> None:
        self.netlist = netlist
        self.settings = settings

    def execute(self) -> PowerFlowResults:
        start_time = time.perf_counter_ns()

        (network_model, v_init, size_Y) = self.create_network()

        v_limiting = None
        if not network_model.is_three_phase and self.settings.voltage_limiting:
            v_limiting = PositiveSeqVoltageLimiting(network_model.buses, size_Y)

        nrsolver = NRSolver(self.settings, network_model, v_limiting)

        homotopy_controller = HomotopyController(self.settings, nrsolver)

        is_success, v_final, iteration_num, tx_factor = homotopy_controller.run_powerflow(v_init)

        end_time = time.perf_counter_ns()

        duration_seconds = (end_time * 1.0 - start_time * 1.0) / math.pow(10, 9)

        return PowerFlowResults(is_success, iteration_num, duration_seconds, network_model, v_final, self.settings)
    
    def create_network(self):
        optimization_enabled = self.settings.infeasibility_analysis

        if ".glm" in self.netlist:
            return self.create_three_phase_network(optimization_enabled)
        elif ".RAW" in self.netlist:
            return self.create_positive_seq_network(optimization_enabled)
        else:
            raise Exception("Invalid netlist file format")

    def create_three_phase_network(self, optimization_enabled):
        parser = Parser(self.netlist, self.settings, optimization_enabled)

        network_model = parser.parse()

        size_Y = next(network_model.next_var_idx)

        v_init = network_model.generate_v_init(size_Y, self.settings)

        return (network_model, v_init, size_Y)


    def create_positive_seq_network(self, optimization_enabled):
        node_index = count(0)

        raw_data = parse_raw(self.netlist)

        buses = raw_data['buses']

        infeasibility_currents = []
        if self.settings.infeasibility_analysis:
            for bus in buses:
                inf_current = L2InfeasibilityCurrent(bus)
                infeasibility_currents.append(inf_current)

        network_model = TxNetworkModel(raw_data, infeasibility_currents)

        for ele in network_model.get_all_elements():
            ele.assign_nodes(node_index, optimization_enabled)

        size_Y = next(node_index)

        v_init = network_model.generate_v_init(size_Y, self.settings)

        return (network_model, v_init, size_Y)


    
    
