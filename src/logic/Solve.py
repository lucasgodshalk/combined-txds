import math
import time
from lib.settings import Settings
from parsers.parser import parse_raw
from lib.PowerFlow import PowerFlow
from lib.process_results import process_results
from lib.initialize import initialize
from itertools import count

class PowerFlow:
    def __init__(self, netlist, settings: Settings = Settings()) -> None:
        self.netlist = netlist
        self.settings = settings

    def execute():
        print("Running power flow solver...")

        start_time = time.perf_counter_ns()

        buses = raw_data['buses']
        slack = raw_data['slack']
        transformers = raw_data['xfmrs']
        generators = raw_data['generators']

        node_index = count(0)

        for ele in buses + slack + transformers:
            ele.assign_nodes(node_index, settings.infeasibility_analysis)

        size_Y = next(node_index)

        v_init = initialize(size_Y, buses, generators, slack, settings)

        powerflow = PowerFlow(settings, raw_data, size_Y)

        is_success, v_final, iteration_num, tx_factor = powerflow.run_powerflow(v_init)

        if is_success:
            print(f'Power flow solver converged after {iteration_num} iterations.')
        else:
            print(f'Power flow solver FAILED after {iteration_num} iterations (tx-factor {tx_factor}).')

        end_time = time.perf_counter_ns()

        duration_seconds = (end_time * 1.0 - start_time * 1.0) / math.pow(10, 9)

        print(f'Ran for {"{:.3f}".format(duration_seconds)} seconds')

        results = process_results(raw_data, v_final, duration_seconds, settings)

        return (is_success, results)
