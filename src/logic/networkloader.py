from itertools import count
import os
from typing import Tuple
from logic.networkmodel import NetworkModel, TxNetworkModel
from logic.parsers.raw.parser import parse_raw
from logic.powerflowsettings import PowerFlowSettings
from logic.parsers.threephase.threephaseparser import ThreePhaseParser
from models.shared.L2infeasibility import L2InfeasibilityCurrent

class NetworkLoader:
    def __init__(self, settings: PowerFlowSettings):
        self.settings = settings
        
    def from_file(self, network_file: str) -> NetworkModel:
        if not os.path.isfile(network_file):
            raise Exception("Network file does not exist.")

        if ".glm" in network_file:
            return self.__create_three_phase_network(network_file)
        elif ".RAW" in network_file:
            return self.__create_positive_seq_network(network_file)
        else:
            raise Exception("Invalid netlist file format")

    def __create_three_phase_network(self, network_file: str):
        parser = ThreePhaseParser(network_file, self.settings)

        network = parser.parse()

        return network

    def __create_positive_seq_network(self, network_file: str):
        raw_data = parse_raw(network_file)

        buses = raw_data['buses']

        infeasibility_currents = []
        if self.settings.infeasibility_analysis:
            for bus in buses:
                inf_current = L2InfeasibilityCurrent(bus)
                infeasibility_currents.append(inf_current)

        loads = raw_data['loads']
        slack = raw_data['slack']
        generators = raw_data['generators']
        transformers = raw_data['xfmrs']
        branches = raw_data['branches']
        shunts = raw_data['shunts']

        network = TxNetworkModel(
            buses=buses, 
            loads=loads, 
            slack=slack, 
            generators=generators, 
            infeasibility_currents=infeasibility_currents,
            transformers=transformers,
            branches=branches,
            shunts=shunts
            )

        return network