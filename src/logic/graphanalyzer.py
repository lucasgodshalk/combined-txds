from collections import defaultdict
import networkx as nx
from logic.network.networkmodel import NetworkModel
from models.singlephase.bus import GROUND
from models.singlephase.load import Load
from models.threephase.center_tap_transformer import CenterTapTransformer
from models.singlephase.switch import Switch
from models.singlephase.transformer import Transformer
from models.singlephase.regulator import Regulator

#Class for performing graph-based analysis of the network, generally
#as a set of validations before attempting to solve power flow or
#in order to provide visualizations.
class GraphAnalyzer:
    NODE_TYPE_COLOR_MAP = {0:"magenta", 1:"gray", 2:"darkred", 3:"orange"} # For Slack, Inf, PQ, and PV
    def __init__(self, network: NetworkModel):
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
            self.G.add_node(bus.NodeName, bus=bus)
            self.node_color[bus.NodeName] = self.NODE_TYPE_COLOR_MAP[bus.Type]
        
        for element in network.get_all_elements():
            for (from_bus, to_bus) in element.get_connections():
                if type(element) == Load:
                    self.node_color[from_bus.NodeName]="darkred"
                elif from_bus == GROUND or to_bus == GROUND or from_bus.NodeName == to_bus.NodeName:
                    continue
                else:
                    self.G.add_edge(from_bus.NodeName, to_bus.NodeName, type="none", from_bus=from_bus, to_bus=to_bus, element=element)
                    
                    self.edge_labels[(from_bus.NodeName, to_bus.NodeName)] += from_bus.NodePhase
                    
                    if type(element) == CenterTapTransformer or type(element) == Transformer:
                        self.edge_color[(from_bus.NodeName, to_bus.NodeName)] = "green"
                    elif type(element) == Switch:
                        self.edge_color[(from_bus.NodeName, to_bus.NodeName)] = "orange"
                    else:
                        self.edge_color[(from_bus.NodeName, to_bus.NodeName)] = "gray"

    def get_island_count(self):
        return len(list(nx.connected_components(self.G)))

    def validate_voltage_islands(self):
        vnom_islands = self.get_nominal_voltage_islands()

        for vnom_island in vnom_islands:
            vnom = None
            for node_idx in vnom_island:
                bus = self.G.nodes[node_idx]["bus"]
                if vnom == None:
                    vnom = round(bus.V_Nominal)
                else:
                    if abs(bus.V_Nominal - vnom) > 10:
                        raise Exception(f"Node {bus.NodeName} nominal voltage is not consistent with other nominal voltages in voltage region.")

    def get_nominal_voltage_islands(self):
        non_xfmr_edges = [(u,v) for u,v,e in self.G.edges(data=True) if type(e['element']) not in [CenterTapTransformer, Transformer, Regulator]]

        xfmr_islands = self.G.edge_subgraph(non_xfmr_edges)

        return list(nx.connected_components(xfmr_islands))