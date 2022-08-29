from collections import defaultdict
import networkx as nx
from models.singlephase.bus import GROUND
from logic.networkmodel import DxNetworkModel, NetworkModel
from logic.powerflowresults import GENTYPE
from models.singlephase.load import Load
from models.threephase.center_tap_transformer import CenterTapTransformer
from models.threephase.transmission_line import TransmissionLine
from models.singlephase.switch import Switch

class GraphAnalyzer:
    NODE_TYPE_COLOR_MAP = {0:"magenta", 1:"gray", 2:"darkred", 3:"orange"} # For Slack, Inf, PQ, and PV
    def __init__(self, network):
        self.network = network
        self.G = nx.Graph()
        self.node_labels = {}
        self.edge_labels = defaultdict(lambda: "")
        self.node_color = {}
        self.edge_color = defaultdict(lambda: "gray")

        for bus in network.buses:
            if bus.IsVirtual:
                continue
            self.node_labels[bus.NodeName] = f"{bus.NodeName}"
            self.G.add_node(bus.NodeName)
            self.node_color[bus.NodeName] = self.NODE_TYPE_COLOR_MAP[bus.Type]
        
        for element in network.get_all_elements():
            for (from_bus, to_bus) in element.get_connections():
                if type(element) == Load:
                    self.node_color[from_bus.NodeName]="darkred"
                elif from_bus == GROUND or to_bus == GROUND:
                    continue
                else:
                    self.G.add_edge(from_bus.NodeName, to_bus.NodeName, type="none")
                    self.edge_labels[(from_bus.NodeName, to_bus.NodeName)] += from_bus.NodePhase
                    if type(element) == CenterTapTransformer:
                        self.edge_color[(from_bus.NodeName, to_bus.NodeName)] = "green"
                    elif type(element) == Switch:
                        self.edge_color[(from_bus.NodeName, to_bus.NodeName)] = "orange"
                    else:
                        self.edge_color[(from_bus.NodeName, to_bus.NodeName)] = "gray"

    def get_island_count(self):
        return len(list(nx.connected_components(self.G)))
