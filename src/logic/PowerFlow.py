import math
import time
from logic.NRSolver import NRSolver
from logic.NetworkModel import TxNetworkModel
from logic.initialize import initialize_postive_seq
from logic.PowerFlowSettings import PowerFlowSettings
from logic.parsers.parser import parse_raw
from itertools import count
from logic.parsers.anoeds_parser import Parser
from logic.powerflowrunner import PowerFlowRunner

class PowerFlow:
    def __init__(self, netlist, settings: PowerFlowSettings = PowerFlowSettings()) -> None:
        self.netlist = netlist
        self.settings = settings

    def execute(self):
        print("Running power flow solver...")

        start_time = time.perf_counter_ns()

        node_index = count(0)

        (network_model, v_init, size_Y) = self.create_network(node_index)

        powerflow = NRSolver(self.settings, network_model, size_Y)

        is_success, v_final, iteration_num, tx_factor = powerflow.run_powerflow(v_init)

        if is_success:
            print(f'Power flow solver converged after {iteration_num} iterations.')
        else:
            print(f'Power flow solver FAILED after {iteration_num} iterations (tx-factor {tx_factor}).')

        end_time = time.perf_counter_ns()

        duration_seconds = (end_time * 1.0 - start_time * 1.0) / math.pow(10, 9)

        print(f'Ran for {"{:.3f}".format(duration_seconds)} seconds')

        #results = process_results(raw_data, v_final, duration_seconds, settings)

        #return (is_success, results)
    
    def create_network(self, node_index):
        if ".glm" in self.netlist:
            return self.create_three_phase_network(node_index)
        elif ".RAW" in self.netlist:
            return self.create_positive_seq_network(node_index)
        else:
            raise Exception("Invalid netlist file format")

    def create_three_phase_network(self, node_index):
        parser = Parser(self.netlist)

        network_model = parser.parse()

        powerflowrunner = PowerFlowRunner(self.netlist, self.settings)
        powerflowrunner.reset_v_estimate(network_model)

        v_init = powerflowrunner.v_estimate

        return (network_model, v_init, network_model.J_length)


    def create_positive_seq_network(self, node_index):
        raw_data = parse_raw(self.netlist)

        buses = raw_data['buses']
        slack = raw_data['slack']
        transformers = raw_data['xfmrs']
        generators = raw_data['generators']

        for ele in buses + slack + transformers:
            ele.assign_nodes(node_index, self.settings.infeasibility_analysis)
        
        size_Y = next(node_index)

        v_init = initialize_postive_seq(size_Y, buses, generators, slack, self.settings)

        network_model = TxNetworkModel(raw_data, self.settings.infeasibility_analysis)

        return (network_model, v_init, size_Y)


    
    
