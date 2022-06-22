import math
import time
from logic.homotopycontroller import HomotopyController
from logic.nrsolver import NRSolver
from logic.networkmodel import TxNetworkModel
from logic.initialize import initialize_postive_seq
from logic.powerflowsettings import PowerFlowSettings
from logic.parsers.parser import parse_raw
from itertools import count
from logic.parsers.anoeds_parser import Parser
from logic.powerflowrunner import PowerFlowRunner
from logic.v_limiting import PositiveSeqVoltageLimiting
from models.positiveseq.infeasibility import InfeasibilityCurrent

class PowerFlow:
    def __init__(self, netlist, settings: PowerFlowSettings = PowerFlowSettings()) -> None:
        self.netlist = netlist
        self.settings = settings

    def execute(self):
        print("Running power flow solver...")

        start_time = time.perf_counter_ns()

        (network_model, v_init, size_Y) = self.create_network()

        v_limiting = None
        if not network_model.is_three_phase and self.settings.voltage_limiting:
            v_limiting = PositiveSeqVoltageLimiting(network_model.buses, size_Y)

        nrsolver = NRSolver(self.settings, network_model, v_limiting)

        homotopy_controller = HomotopyController(self.settings, nrsolver)

        is_success, v_final, iteration_num, tx_factor = homotopy_controller.run_powerflow(v_init)

        if is_success:
            print(f'Power flow solver converged after {iteration_num} iterations.')
        else:
            print(f'Power flow solver FAILED after {iteration_num} iterations (tx-factor {tx_factor}).')

        end_time = time.perf_counter_ns()

        duration_seconds = (end_time * 1.0 - start_time * 1.0) / math.pow(10, 9)

        print(f'Ran for {"{:.3f}".format(duration_seconds)} seconds')

        #results = process_results(raw_data, v_final, duration_seconds, settings)

        #return (is_success, results)
    
    def create_network(self):
        if ".glm" in self.netlist:
            return self.create_three_phase_network()
        elif ".RAW" in self.netlist:
            return self.create_positive_seq_network()
        else:
            raise Exception("Invalid netlist file format")

    def create_three_phase_network(self):
        parser = Parser(self.netlist)

        network_model = parser.parse()

        powerflowrunner = PowerFlowRunner(self.netlist, self.settings)
        powerflowrunner.reset_v_estimate(network_model)

        v_init = powerflowrunner.v_estimate

        return (network_model, v_init, network_model.J_length)


    def create_positive_seq_network(self):
        node_index = count(0)

        raw_data = parse_raw(self.netlist)

        buses = raw_data['buses']
        slack = raw_data['slack']
        transformers = raw_data['xfmrs']
        generators = raw_data['generators']

        optimization_enabled = False
        infeasibility_currents = []
        if self.settings.infeasibility_analysis:
            optimization_enabled = True
            for bus in buses:
                inf_current = InfeasibilityCurrent(bus)
                infeasibility_currents.append(inf_current)

        network_model = TxNetworkModel(raw_data, infeasibility_currents)

        for ele in network_model.get_all_elements():
            ele.assign_nodes(node_index, optimization_enabled)

        size_Y = next(node_index)

        v_init = initialize_postive_seq(size_Y, buses, generators, slack, self.settings)

        return (network_model, v_init, size_Y)


    
    
