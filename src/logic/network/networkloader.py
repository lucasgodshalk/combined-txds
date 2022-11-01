import os
from logic.network.networkmodel import NetworkModel, TxNetworkModel
from logic.network.parsers.raw.parser import parse_raw
from logic.powerflowsettings import PowerFlowSettings
from logic.network.parsers.threephase.threephaseparser import ThreePhaseParser
from models.optimization.L2infeasibility import L2InfeasibilityCurrent, L2InfeasibilityOptimization
import urllib.request
import tempfile

def pull_network_file(network_uri: str):
    #If it's a local file, we're all good.
    if os.path.isfile(network_uri):
        return network_uri
    
    #Otherwise, we attempt to download it as a url.
    if not (network_uri.startswith("http://") or network_uri.startswith("https://")):
        raise Exception("Unknown file location")
    
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
            network = self.__parse_glm_network(network_file)
        elif ".RAW" in network_file:
            network =  self.__parse_RAW_network(network_file)
        else:
            raise Exception("Unknown network file format")

        network.optimization = self.__load_optimization(network)

        return network

    def __parse_glm_network(self, network_file: str):
        parser = ThreePhaseParser(network_file, self.settings)

        network = parser.parse()

        return network

    def __parse_RAW_network(self, network_file: str):
        raw_data = parse_raw(network_file)

        buses = raw_data['buses']

        loads = raw_data['loads']
        slack = raw_data['slack']
        generators = raw_data['generators']
        transformers = raw_data['xfmrs']
        lines = raw_data['branches']
        shunts = raw_data['shunts']

        network = TxNetworkModel(
            buses=buses, 
            loads=loads, 
            slack=slack, 
            generators=generators, 
            transformers=transformers,
            lines=lines,
            shunts=shunts
            )

        return network
    
    def __load_optimization(self, network):
        if self.settings.infeasibility_analysis:
            return L2InfeasibilityOptimization(network.buses)

        return None