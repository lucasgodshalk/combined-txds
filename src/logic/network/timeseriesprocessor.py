import math
import os
import typing
from logic.graphanalyzer import GraphAnalyzer
from logic.network.networkmodel import DxNetworkModel
from pandas import DataFrame, read_csv
import networkx as nx

from logic.network.timeseriessettings import TimeSeriesSettings
from logic.powerflow import PowerFlow
from logic.powerflowresults import CenterTapTransformerResult, LineResult, PowerFlowResults, QuasiTimeSeriesResults, TransformerResult
from models.components.center_tap_transformer import CenterTapTransformer
from models.components.switch import Switch
from models.components.transformer import Transformer

VOLTAGE_DEVIATION_THRESHOLD = 0.05

class TimeSeriesProcessor:
    THRESHOLD = 1e-1
    def __init__(self, settings: TimeSeriesSettings, powerflow: PowerFlow):
        self.settings = settings
        self.powerflow = powerflow
        if self.settings.loadfile_name is not None:
            self.load_data = read_csv(self.settings.loadfile_name)
        if self.settings.select_island and self.settings.artificialswingbus is not None:
            self.select_island()
    
    def select_island(self):
        ga = GraphAnalyzer(self.powerflow.network)
        if ga.get_island_count() == 0:
            pass
        desired_island = nx.node_connected_component(ga.G, self.settings.artificialswingbus)
        for island in ga.get_islands():
            if island == desired_island:
                # self.powerflow.network.buses = []
                # for node in island:
                #     for bus in ga.G.nodes[node]['bus_list']:
                #         self.powerflow.network.buses.append(bus)
                continue
            for node in island:
                node_edges = ga.G.edges(node)
                for edge_from, edge_to in node_edges:
                    edge = ga.G.edges[edge_from, edge_to]
                    for element in edge["element_list"]:
                        if type(element) == CenterTapTransformer or type(element) == Transformer:
                            try:
                                self.powerflow.network.transformers.remove(element)
                            except:
                                pass
                            if type(element) == CenterTapTransformer:    
                                try:
                                    self.powerflow.network.buses.remove(element.coils[0].primary_node)
                                except:
                                    pass
                                try:
                                    self.powerflow.network.buses.remove(element.coils[1].sending_node)
                                except:
                                    pass
                                try:
                                    self.powerflow.network.buses.remove(element.coils[2].sending_node)
                                except:
                                    pass
                        elif type(element) == Switch:
                            try:
                                self.powerflow.network.switches.remove(element)
                            except:
                                pass
                        else:
                            try:
                                self.powerflow.network.lines.remove(element)
                            except:
                                pass
                for bus in ga.G.nodes[node]['bus_list']:
                    self.powerflow.network.buses.remove(bus)
        slack_to_remove = []
        for idx, slack in enumerate(self.powerflow.network.slack):
            if slack.bus not in self.powerflow.network.buses:
                slack_to_remove.insert(0, idx)
        for idx in slack_to_remove:
            del self.powerflow.network.slack[idx]
        
        generator_to_remove = []
        for idx, generator in enumerate(self.powerflow.network.generators):
            if generator.bus not in self.powerflow.network.buses:
                generator_to_remove.insert(0, idx)
        for idx in generator_to_remove:
            del self.powerflow.network.generators[idx]

        load_to_remove = []
        for idx, load in enumerate(self.powerflow.network.loads):
            if load.from_bus not in self.powerflow.network.buses or load.to_bus not in self.powerflow.network.buses:
                load_to_remove.insert(0, idx)
        for idx in load_to_remove:
            del self.powerflow.network.loads[idx]

        fuse_to_remove = []
        for idx, fuse in enumerate(self.powerflow.network.fuses):
            if fuse.from_node not in self.powerflow.network.buses or fuse.to_node not in self.powerflow.network.buses:
                try:
                    self.powerflow.network.buses.remove(fuse.interior_node)
                except:
                    pass
                fuse_to_remove.insert(0, idx)
        for idx in fuse_to_remove:
            del self.powerflow.network.fuses[idx]

        regulator_to_remove = []
        for idx, regulator in enumerate(self.powerflow.network.regulators):
            if regulator.from_node not in self.powerflow.network.buses or regulator.to_node not in self.powerflow.network.buses:
                try:
                    self.powerflow.network.buses.remove(regulator.current_node)
                except:
                    pass
                regulator_to_remove.insert(0, idx)
        for idx in regulator_to_remove:
            del self.powerflow.network.regulators[idx]

        capacitor_to_remove = []
        for idx, capacitor in enumerate(self.powerflow.network.capacitors):
            if capacitor.from_bus not in self.powerflow.network.buses or capacitor.to_bus not in self.powerflow.network.buses:
                capacitor_to_remove.insert(0, idx)
        for idx in capacitor_to_remove:
            del self.powerflow.network.capacitors[idx]

    def set_load_names(self):
        for phase_load in self.powerflow.network.loads:
            load_name = self.get_load_name(phase_load)
            self.powerflow.network.load_name_map[load_name] = phase_load

    def get_load_name(self, phase_load):
        if phase_load.phase.isalpha():
            load_name = f"cl_{phase_load.load_num}{phase_load.phase}"
        elif phase_load.phase.isnumeric():
            load_name = f"rl_{phase_load.load_num}_{phase_load.phase[0]}"
        else:
            load_name = f"{phase_load.load_num}_{phase_load.phase}"
        return load_name
    
    def set_load_values(self, hour: int=0):
        if not (self.powerflow.network.is_three_phase):
            raise Exception("Initializing load files from separate file currently supported for three-phase networks")
        if self.load_data is None:
            raise Exception("NetworkPostProcessor needs a valid load file upon initialization")

        for load_name in self.load_data.columns:
            try:
                load_obj = self.powerflow.network.load_name_map[load_name]
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
    def adjust_generator_output(self, snapshot_results: PowerFlowResults):
        if self.settings.artificialswingbus is None or self.settings.negativeloads is None:
            return False
        
        swingbusoutputs = [(gen_result.generator.bus.NodePhase, gen_result.P, gen_result.Q) for gen_result in snapshot_results.generator_results if gen_result.generator.bus.NodeName == self.settings.artificialswingbus]
        if sum(abs(complex(p, q)) for phase,p,q in swingbusoutputs) < self.THRESHOLD:
            # The artificial swing bus is emitting and absorbing essentially zero power, so the adjustment is complete
            return False
        
        # Adjust the negative load to lower its output by the appropriate amount (akin to it generating that same amount of power)
        negativeload_nums = [negativeload.split("_")[-1] for negativeload in self.settings.negativeloads]
        negativeload_objs = {(load.phase if load.triplex_phase is None else load.triplex_phase):load for load in self.powerflow.network.loads if load.load_num in negativeload_nums}
        for phase, p, q in swingbusoutputs:
            phase_load = negativeload_objs[phase]
            phase_load.P += p
            phase_load.Q += q
        return True

    # Determine whether the current or power flowing through any piece of equipment exceeds its rated capacity
    def violates_equipment_ratings(self, snapshot_results: PowerFlowResults) -> bool:
        exceeds_rating = False
        # Ensure that no lines have current flowing through them that exceeds their rating
        for line in self.powerflow.network.lines:
            for (idx, g, b, phase_line) in line.loop_lines():
                line_result = LineResult(phase_line, snapshot_results, g, b)
                line_current = complex(line_result.get_Ir(), line_result.get_Ii())
                if (line.ampacities[idx] is not None and abs(line_current) > line.ampacities[idx]):
                    print(f"Line current {line_current} exceeds emergency ampacity {line.ampacities[idx]}")
                    exceeds_rating = True

        # Ensure that no transformers have power flowing through them that exceeds their power_rating
        for xfmr in self.powerflow.network.transformers:
            if isinstance(xfmr, CenterTapTransformer):
                xfmr_result = CenterTapTransformerResult(xfmr, snapshot_results)
            else:
                xfmr_result = TransformerResult(xfmr, snapshot_results)
            xfmr_power = complex(xfmr_result.get_P(), xfmr_result.get_Q())
            if (xfmr.power_rating is not None and abs(xfmr_power) > xfmr.power_rating):
                print(f"Transformer power {xfmr_result} exceeds rated power {xfmr.power_rating}")
                exceeds_rating = True

        # Ensure that no nodes have voltages that are outside acceptable bounds
        for bus_result in snapshot_results.bus_results:
            if (abs(bus_result.V_mag - bus_result.bus.V_Nominal) / bus_result.bus.V_Nominal >= VOLTAGE_DEVIATION_THRESHOLD):
                print(f"Bus voltage magnitude {bus_result.V_mag} is outside acceptable range of expected voltage magnitude {bus_result.bus.V_Nominal}")
                exceeds_rating = True
        
        return exceeds_rating

    # Run for multiple snapshots of load values
    def execute_quasi_time_series(self) -> QuasiTimeSeriesResults:
        if not os.path.isfile(self.settings.loadfile_name):
            raise Exception("Load file does not exist.")
        
        quasi_time_series_results = QuasiTimeSeriesResults()
        self.set_load_names()
        for hour in range(self.settings.loadfile_start, self.settings.loadfile_end):
            self.set_load_values(hour)
            snapshot_results = self.execute_powerflow()
            quasi_time_series_results.add_powerflow_snapshot_results(hour, snapshot_results)

            if self.settings.outputfile is not None:
                snapshot_results.output(f"{self.settings.outputfile}_{hour}")

        return quasi_time_series_results

    # Wrapper for the PowerFlow.execute() method, with additional functionality for generator adjustment
    def execute_powerflow(self) -> PowerFlowResults:
        snapshot_results = self.powerflow.execute()
        # If requested, adjust a specific negative load until the specified swing bus is within a threshold of zero power in/out
        while self.adjust_generator_output(snapshot_results):
            snapshot_results = self.powerflow.execute()
        if snapshot_results.is_success and self.violates_equipment_ratings(snapshot_results):
            snapshot_results.violates_equipment_ratings = True
        return snapshot_results

    # Execute all applicable post-processing steps
    def execute(self) -> typing.Union[PowerFlowResults, QuasiTimeSeriesResults]:
        if not self.powerflow.network.is_three_phase:
            raise Exception("Post-processing options only currently supported for distribution networks")
        if self.settings.loadfile_name is not None:
            return self.execute_quasi_time_series()
        elif self.settings.artificialswingbus is not None:
            return self.execute_powerflow()
        else:
            return None

    def save_load_names(self, load_name_filepath):
        DataFrame([bus.NodeName for bus in self.powerflow.network.buses]).to_csv(load_name_filepath)
    