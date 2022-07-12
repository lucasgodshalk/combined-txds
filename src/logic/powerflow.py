import math
import time
from logic.homotopycontroller import HomotopyController
from logic.networkbuilder import NetworkBuilder
from logic.nrsolver import NRSolver
from logic.powerflowsettings import PowerFlowSettings
from logic.powerflowresults import PowerFlowResults
from logic.v_limiting import PositiveSeqVoltageLimiting

class PowerFlow:
    def __init__(self, network_model, settings: PowerFlowSettings = PowerFlowSettings()) -> None:
        self.network_model = network_model
        self.settings = settings

    def execute(self) -> PowerFlowResults:
        start_time = time.perf_counter_ns()

        v_init = self.network_model.generate_v_init(self.settings)

        v_limiting = None
        if not self.network_model.is_three_phase and self.settings.voltage_limiting:
            v_limiting = PositiveSeqVoltageLimiting(self.network_model.buses, self.network_model.size_Y)

        nrsolver = NRSolver(self.settings, self.network_model, v_limiting)

        homotopy_controller = HomotopyController(self.settings, nrsolver)

        is_success, v_final, iteration_num, tx_factor = homotopy_controller.run_powerflow(v_init)

        end_time = time.perf_counter_ns()

        duration_seconds = (end_time * 1.0 - start_time * 1.0) / math.pow(10, 9)

        return PowerFlowResults(is_success, iteration_num, duration_seconds, self.network_model, v_final, self.settings)
    
class FilePowerFlow(PowerFlow):
    def __init__(self, networkfile: str, settings: PowerFlowSettings):
        builder = NetworkBuilder(settings)

        network = builder.from_file(networkfile)

        PowerFlow.__init__(self, network, settings)



    
    
