import networkx as nx

from logic.networkmodel import NetworkModel

class GraphAnalyzer:
    def __init__(self):
        self.G = nx.Graph()

    def load_network(self, network: NetworkModel):
        for bus in network.buses:
            self.G.add_node(bus)

