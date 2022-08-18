import math
from logic.networkmodel import DxNetworkModel, NetworkModel
from pandas import read_csv

from logic.powerflowsettings import PowerFlowSettings

class NetworkPostProcessor:
    def __init__(self, settings: PowerFlowSettings):
        self.settings = settings
    
    def run(self, network: NetworkModel):
        if self.settings.loadfile_name is not None and network.is_three_phase:
            self.initialize_load_values(network)
        
    def initialize_load_values(self, network: DxNetworkModel):
        if not network.is_three_phase:
            raise Exception("Initializing load files from separate file currently supported for three-phase networks")
        load_data = read_csv(self.settings.loadfile_name)
        load_data = load_data.loc[:,(load_data != 0).any(axis=0)]
        for load_name in load_data.columns:
            load_obj = network.load_name_map[load_name]
            angle = math.atan(load_obj.Q/load_obj.P)
            magnitude = load_data[load_name][0]
            load_obj.P = magnitude * math.cos(angle)
            load_obj.Q = magnitude * math.sin(angle)