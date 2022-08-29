import os
from logic.networkmodel import NetworkModel, TxNetworkModel
from logic.parsers.raw.parser import parse_raw
from logic.powerflowsettings import PowerFlowSettings
from logic.parsers.threephase.threephaseparser import ThreePhaseParser
from models.singlephase.L2infeasibility import L2InfeasibilityCurrent
import urllib.request
import tempfile

def pull_network_file(network_uri: str):
    #If it's a local file, we're all good.
    if os.path.isfile(network_uri):
        return network_uri
    
    #Otherwise, we attempt to download it as a url.
    if not (network_uri.startswith("http://") or network_uri.startswith("https://")):
        raise Exception("Unkonwn network file location")
    
    status_code = urllib.request.urlopen(network_uri).getcode()
    if status_code != 200:
        raise Exception("Network request for network file failed.")

    tmpdir = tempfile.gettempdir()

    filepath = os.path.join(tmpdir, network_uri.split("/")[-1]) #Assume the network file name is at the end of the url.

    try:
        os.remove(filepath)
    except:
        pass

    filepath, _ = urllib.request.urlretrieve(network_uri, filepath)

    return filepath


class NetworkLoader:
    def __init__(self, settings: PowerFlowSettings):
        self.settings = settings
        
    def from_file(self, network_uri: str) -> NetworkModel:
        print(f"Loading network file: {network_uri}")
        network_file = pull_network_file(network_uri)

        if ".glm" in network_file:
            return self.__create_three_phase_network(network_file)
        elif ".RAW" in network_file:
            return self.__create_positive_seq_network(network_file)
        else:
            raise Exception("Unknown network file format")

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