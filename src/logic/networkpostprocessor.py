import math
import os
import typing
from logic.networkmodel import DxNetworkModel, NetworkModel
from pandas import read_csv

from logic.postprocessingsettings import PostProcessingSettings
from logic.powerflow import PowerFlow
from logic.powerflowresults import PowerFlowResults, QuasiTimeSeriesResults

class NetworkPostProcessor:
    THRESHOLD = 1e-1
    def __init__(self, settings: PostProcessingSettings, powerflow: PowerFlow):
        self.settings = settings
        self.powerflow = powerflow
        if self.settings.loadfile_name is not None:
            self.load_data = read_csv(self.settings.loadfile_name)

    def set_load_names(self, network:DxNetworkModel):
        for phase_load in network.loads:
            load_name = self.get_load_name(phase_load)
            network.load_name_map[load_name] = phase_load

    def get_load_name(self, phase_load):
        if phase_load.phase.isalpha():
            load_name = f"cl_{phase_load.load_num}{phase_load.phase}"
        elif phase_load.phase.isnumeric():
            load_name = f"rl_{phase_load.load_num}_{phase_load.phase[0]}"
        else:
            load_name = f"{phase_load.load_num}_{phase_load.phase}"
        return load_name
    
    def set_load_values(self, network: DxNetworkModel, hour: int=0):
        if not network.is_three_phase:
            raise Exception("Initializing load files from separate file currently supported for three-phase networks")
        if self.load_data is None:
            raise Exception("NetworkPostProcessor needs a valid load file upon initialization")

        for load_name in self.load_data.columns:
            try:
                load_obj = network.load_name_map[load_name]
            except:
                continue
            try:
                magnitude = self.load_data[load_name][hour]
            except:
                continue
            angle = math.atan2(load_obj.Q,load_obj.P)
            load_obj.P = magnitude * math.cos(angle)
            load_obj.Q = magnitude * math.sin(angle)
    
    # Automatically determine the level of generation needed at the microgrid
    def adjust_generator_output(self, network: DxNetworkModel, snapshot_results: PowerFlowResults):
        if self.settings.artificialswingbus is None or self.settings.negativeload is None:
            return False
        
        swingbusoutputs = [(gen_result.generator.bus.NodePhase, gen_result.P, gen_result.Q) for gen_result in snapshot_results.generator_results if gen_result.generator.bus.NodeName == self.settings.artificialswingbus]
        if sum(abs(complex(p, q)) for phase,p,q in swingbusoutputs) < self.THRESHOLD:
            # The artificial swing bus is emitting and absorbing essentially zero power, so the adjustment is complete
            return False
        
        # Adjust the negative load to lower its output by the appropriate amount (akin to it generating that same amount of power)
        negativeload_num = self.settings.negativeload.split("_")[-1]
        negativeload_objs = {(load.phase if load.triplex_phase is None else load.triplex_phase):load for load in network.loads if load.load_num == negativeload_num}
        for phase, p, q in swingbusoutputs:
            phase_load = negativeload_objs[phase]
            phase_load.P += p
            phase_load.Q += q
        return True

    # Run for multiple snapshots of load values
    def execute_quasi_time_series(self) -> QuasiTimeSeriesResults:
        if not os.path.isfile(self.settings.loadfile_name):
            raise Exception("Load file does not exist.")
        
        quasi_time_series_results = QuasiTimeSeriesResults()
        self.set_load_names(self.powerflow.network)
        for hour in range(self.settings.loadfile_start, self.settings.loadfile_end):
            self.set_load_values(self.powerflow.network, hour)
            snapshot_results = self.execute_powerflow()
            quasi_time_series_results.add_powerflow_snapshot_results(hour, snapshot_results)

        return quasi_time_series_results

    # Wrapper for the PowerFlow.execute() method, with additional functionality for generator adjustment
    def execute_powerflow(self) -> PowerFlowResults:
        snapshot_results = self.powerflow.execute()
        # If requested, adjust a specific negative load until the specified swing bus is within a threshold of zero power in/out
        while self.adjust_generator_output(self.powerflow.network, snapshot_results):
            snapshot_results = self.powerflow.execute()
        return snapshot_results

    # Execute all applicable post-processing steps
    def execute(self) -> typing.Union[PowerFlowResults, QuasiTimeSeriesResults]:
        if self.settings.loadfile_name is not None:
            return self.execute_quasi_time_series()
        elif self.settings.artificialswingbus is not None and self.settings.negativeload is not None:
            return self.execute_powerflow()
        else:
            return None