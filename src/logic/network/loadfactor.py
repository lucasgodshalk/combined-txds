from logic.network.networkmodel import NetworkModel

def modify_load_factor(network: NetworkModel, loadfactor_P: float=1, loadfactor_Q: float=1):
    for load in network.loads:
        load.P *= loadfactor_P
        load.Q *= loadfactor_Q