import math
import time
from logic.devicecontroller import DeviceController
from logic.graphanalyzer import GraphAnalyzer
from logic.homotopycontroller import HomotopyController
from logic.networkloader import NetworkLoader
from logic.networkmodel import NetworkModel
from logic.nrsolver import NRSolver
from logic.powerflowsettings import PowerFlowSettings
from logic.powerflowresults import PowerFlowResults
from logic.v_limiting import PositiveSeqVoltageLimiting

class PowerFlow:
    def __init__(self, network: NetworkModel, settings: PowerFlowSettings = PowerFlowSettings()) -> None:
        self.network = network
        self.settings = settings

    def execute(self) -> PowerFlowResults:
        start_time = time.perf_counter_ns()

        ga = GraphAnalyzer(self.network)
        island_count = ga.get_island_count() 
        if island_count != 1:
            raise Exception(f"Detected multiple network islands. (Count: {island_count})")

        ga.validate_voltage_islands()

        v_limiting = None
        if not self.network.is_three_phase and self.settings.voltage_limiting:
            v_limiting = PositiveSeqVoltageLimiting(self.network)

        nrsolver = NRSolver(self.settings, self.network, v_limiting)

        homotopy_controller = HomotopyController(self.settings, nrsolver)

        device_controller = DeviceController(self.settings, homotopy_controller)

        is_success, v_final, iteration_num, tx_percent = device_controller.run_powerflow()

        end_time = time.perf_counter_ns()

        duration_seconds = (end_time * 1.0 - start_time * 1.0) / math.pow(10, 9)

        return PowerFlowResults(
            is_success, 
            iteration_num, 
            tx_percent,
            duration_seconds,
            self.network, 
            v_final, 
            self.settings
            )

    
    
