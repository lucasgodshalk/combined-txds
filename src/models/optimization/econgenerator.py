from itertools import count
from sympy import symbols
from logic.stamping.lagrangesegment import LagrangeSegment
from logic.stamping.lagrangestampdetails import LagrangeStampDetails
from models.singlephase.bus import Bus
from logic.stamping.matrixstamper import build_stamps_from_stamper
from logic.network.networkmodel import NetworkModel
import numpy as np

def load_econ_dispatch(network: NetworkModel, econ_dispatch_csv: str):
    data = np.loadtxt(econ_dispatch_csv,delimiter=',',skiprows=1)
    network.generators.clear()
    network.slack.clear()
    list_of_gens = []
    for row in data:
        bus_index, V_min, V_max, PG_min, PG_max, QG_min, QG_max, C1, C2 = row
        gen_bus = [bus for bus in network.buses if bus.Bus==bus_index][0]
        temp = EconGenerator(gen_bus, PG_min, PG_max, QG_min, QG_max, C1, C2)
        list_of_gens.append(temp)
    
    return EconomicDispatch(list_of_gens)

def convert_inequality_to_barrier(F_ieq, mu_variable):
    return 1

constants = C1, C2, P_min, P_max, Q_min, Q_max = symbols('C1 C2 P_min P_max Q_min Q_max')
primals = Vr, Vi, P, Q = symbols('V_r V_i P Q')
duals = Lr, Li = symbols('lambda_r lambda_i')
mus = Mu_P_max, Mu_P_min = symbols('Mu_P_max Mu_P_min') 

obj_F = C1 * P**2 + C2 * P

F_Ir = (-P * Vr - Q * Vi) / (Vr ** 2 + Vi ** 2)
F_Ii = (-P * Vi + Q * Vr) / (Vr ** 2 + Vi ** 2)

F_P_max = P - P_max
F_P_min = P_min - P

lagrange = obj_F + (Lr * F_Ir + Li * F_Ii) + (convert_inequality_to_barrier(F_P_max, Mu_P_max) + convert_inequality_to_barrier(F_P_min, Mu_P_min))

lh = LagrangeSegment(lagrange, constants, primals, duals, mus)

class EconGenerator:
    _ids = count(0)

    def __init__(self,
                 bus: Bus,
                 P_min,
                 P_max,
                 Q_min,
                 Q_max,
                 C1,
                 C2
        ):

        self.id = self._ids.__next__()

        self.bus = bus
        self.P_max = P_max
        self.P_min = P_min
        self.C1 = C1
        self.C2 = C2
        self.Q_max = Q_max
        self.Q_min = Q_min

    def assign_nodes(self, node_index):
        self.node_P = next(node_index)
        index_map = {}
        index_map[Vr] = self.bus.node_Vr
        index_map[Vi] = self.bus.node_Vi
        index_map[Q] = self.bus.node_Q
        index_map[P] = self.node_P
        index_map[Lr] = self.bus.node_lambda_Vr
        index_map[Li] = self.bus.node_lambda_Vi

        self.stamper = LagrangeStampDetails(lh, index_map, optimization_enabled=True)

    def get_stamps(self):
        return build_stamps_from_stamper(self, self.stamper, [self.C1, self.C2, self.P_min, self.P_max, self.Q_min, self.Q_max]) 

    def get_connections(self):
        return []

class EconomicDispatch():
    def __init__(self,list_of_gens) -> None:
        self.list_of_gens = list_of_gens

    def assign_nodes(self, node_index, optimization_enabled):
        if not optimization_enabled:
            raise Exception("Cannot use infeasibility currents when optimization is not enabled")

        for infeas_current in self.list_of_gens:
            infeas_current.assign_nodes(node_index)

    def get_stamps(self):
        stamps = []
        for infeas_current in self.list_of_gens:
            stamps += infeas_current.get_stamps()
        return stamps

