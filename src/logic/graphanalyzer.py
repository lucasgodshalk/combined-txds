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
            self.node_labels[bus.NodeName] = f"{bus.NodeName}"
            self.G.add_node(bus.NodeName)
        
        for transformer in network.transformers:
            for (from_pos, from_neg, to_pos, to_neg) in transformer.get_connections():
                self.G.add_edge(from_pos.NodeName, to_pos.NodeName, type="transformer")
                self.edge_labels[(from_pos.NodeName, to_pos.NodeName)] += from_pos.NodePhase
        
        for branch in network.branches:
            for (from_bus, to_bus) in branch.get_connections():
                self.G.add_edge(from_bus.NodeName, to_bus.NodeName, type="branch")
                self.edge_labels[(from_bus.NodeName, to_bus.NodeName)] += from_bus.NodePhase