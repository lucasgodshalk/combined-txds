from collections import defaultdict
import networkx as nx

from logic.networkmodel import DxNetworkModel, NetworkModel

class GraphAnalyzer:
    def __init__(self):
        self.G = nx.Graph()
        self.node_labels = {}
        self.edge_labels = defaultdict(lambda: "")

    def load_network(self, network: NetworkModel):
        for bus in network.buses:
            if bus.IsVirtual:
                continue
            self.node_labels[bus.NodeName] = f"{bus.NodeName}"
            self.G.add_node(bus.NodeName)
        
        for element in network.get_all_elements():
            for (from_bus, to_bus) in element.get_connections():
                self.G.add_edge(from_bus.NodeName, to_bus.NodeName, type="none")
                self.edge_labels[(from_bus.NodeName, to_bus.NodeName)] += from_bus.NodePhase