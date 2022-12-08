from itertools import count
from typing import List
from sympy import symbols
from sympy.functions.elementary.exponential import log
from logic.stamping.lagrangesegment import LagrangeSegment
from logic.stamping.lagrangestampdetails import LagrangeStampDetails
from models.components.bus import Bus, Lambda_init
from logic.stamping.matrixstamper import build_stamps_from_stamper
from logic.network.networkmodel import NetworkModel
import numpy as np

def load_econ_dispatch(network: NetworkModel, econ_dispatch_csv: str):
    data = np.genfromtxt(econ_dispatch_csv,delimiter=',',skip_header=1)
    network.generators.clear()
    network.slack.clear()
    for bus in network.buses:
        bus.Type = 1

    list_of_gens = []
    v_limits = []
    reference_gen = True
    for row in data:
        bus_index, V_min, V_max, PG_min, PG_max, QG_min, QG_max, C1, C2 = row
        gen_bus = [bus for bus in network.buses if bus.Bus==bus_index][0]
        if np.isnan(PG_min) or np.isnan(PG_max):
            continue
        econ_gen = EconGenerator(gen_bus, PG_min / 100, PG_max / 100, QG_min / 100, QG_max / 100, C1, C2, reference_gen)
        list_of_gens.append(econ_gen)

        # v_limit = VLimiter(gen_bus, V_min, V_max)
        # v_limits.append(v_limit)

        reference_gen = False
    
    return EconomicDispatch(list_of_gens, v_limits)

def convert_inequality_to_barrier(F_ieq):
    t = 1
    return -1/t*log(F_ieq)

constants = C1, C2, P_min, P_max, Q_min, Q_max = symbols('C1 C2 P_min P_max Q_min Q_max')
primals = Vr, Vi, P, Q = symbols('V_r V_i P Q')
duals = Lr, Li = symbols('lambda_r lambda_i')

obj_F = C1 * P**2 + C2 * P

F_Ir = (P * Vr + Q * Vi) / (Vr ** 2 + Vi ** 2)
F_Ii = (P * Vi - Q * Vr) / (Vr ** 2 + Vi ** 2)

F_P_max = P - P_max
F_P_min = P_min - P

F_Q_max = Q - Q_max
F_Q_min = Q_min - Q

lagrange = obj_F + (Lr * -F_Ir + Li * -F_Ii)
# lagrange += convert_inequality_to_barrier(F_P_max)
# lagrange += convert_inequality_to_barrier(F_P_min)
# lagrange += convert_inequality_to_barrier(F_Q_max)
# lagrange += convert_inequality_to_barrier(F_Q_min)

lh = LagrangeSegment(lagrange, constants, primals, duals)

L_Vi_set = symbols('lambda_Vi_set')

lagrange_bus_ref = L_Vi_set * Vi #V_i = 0 for a reference bus.

primals = (Vi,)
duals = (L_Vi_set,)

lh_bus_ref = LagrangeSegment(lagrange_bus_ref, (), primals, duals)

V_min, V_max = symbols('V_min V_max')

F_V_max = (Vr**2 + Vi**2) ** 0.5 - V_max
F_V_min = V_min - (Vr**2 + Vi**2) ** 0.5

lagrange_v_limit = convert_inequality_to_barrier(F_V_max) + convert_inequality_to_barrier(F_V_min)

lh_v_limit = LagrangeSegment(lagrange_v_limit, (V_min, V_max), (Vr, Vi), ())

class VLimiter:
    _ids = count(0)

    def __init__(self, bus: Bus, V_min: float, V_max: float):
        self.id = self._ids.__next__()

        self.bus = bus
        self.V_min = V_min
        self.V_max = V_max

    def assign_nodes(self, node_index):
        index_map = {}
        index_map[Vr] = self.bus.node_Vr
        index_map[Vi] = self.bus.node_Vi

        self.stamper = LagrangeStampDetails(lh_v_limit, index_map, optimization_enabled=True)

    def get_stamps(self):
        return build_stamps_from_stamper(self, self.stamper, [self.V_min, self.V_max]) 

    def get_connections(self):
        return []

class EconGenerator:
    _ids = count(0)

    def __init__(self,
                 bus: Bus,
                 P_min,
                 P_max,
                 Q_min,
                 Q_max,
                 C1,
                 C2,
                 reference_gen: bool
        ):

        self.id = self._ids.__next__()

        self.bus = bus
        self.P_max = P_max
        self.P_min = P_min
        self.C1 = C1
        self.C2 = C2
        self.Q_max = Q_max
        self.Q_min = Q_min
        self.reference_gen = reference_gen

    def assign_nodes(self, node_index):
        self.node_P = next(node_index)
        self.node_Q = next(node_index)
        index_map = {}
        index_map[Vr] = self.bus.node_Vr
        index_map[Vi] = self.bus.node_Vi
        index_map[Q] = self.node_Q
        index_map[P] = self.node_P
        index_map[Lr] = self.bus.node_lambda_Vr
        index_map[Li] = self.bus.node_lambda_Vi

        self.stamper = LagrangeStampDetails(lh, index_map, optimization_enabled=True)

        if self.reference_gen:
            self.node_L_Vi_set = next(node_index)
            index_map = {}
            index_map[Vi] = self.bus.node_Vi
            index_map[L_Vi_set] = self.node_L_Vi_set

            self.reference_stamper = LagrangeStampDetails(lh_bus_ref, index_map, optimization_enabled=True)

    def get_stamps(self):
        stamps = build_stamps_from_stamper(self, self.stamper, [self.C1, self.C2, self.P_min, self.P_max, self.Q_min, self.Q_max]) 

        if self.reference_gen:
            stamps += build_stamps_from_stamper(self, self.reference_stamper, []) 

        return stamps

    def get_connections(self):
        return []

class EconomicDispatch():
    def __init__(self, list_of_gens: List[EconGenerator], v_limits: List[VLimiter]):
        self.list_of_gens = list_of_gens
        self.v_limiters = v_limits

    def assign_nodes(self, node_index, optimization_enabled):
        if not optimization_enabled:
            raise Exception("Cannot use infeasibility currents when optimization is not enabled")

        for econ_gen in self.list_of_gens:
            econ_gen.assign_nodes(node_index)

        for v_limiter in self.v_limiters:
            v_limiter.assign_nodes(node_index)      

    def get_stamps(self):
        stamps = []
        for econ_gen in self.list_of_gens + self.v_limiters:
            stamps += econ_gen.get_stamps()
        return stamps

    def set_v_init(self, v_init):
        for econ_gen in self.list_of_gens:
            v_init[econ_gen.node_P] = 0.1#(econ_gen.P_max + econ_gen.P_min) / 2
            v_init[econ_gen.node_Q] = 0.1#(econ_gen.Q_max + econ_gen.Q_min) / 2
            if econ_gen.reference_gen:
                v_init[econ_gen.node_L_Vi_set] = Lambda_init

    def try_limit_v(self, v_next):
        buffer = 0.001
        for econ_gen in self.list_of_gens:
            P = v_next[econ_gen.node_P]
            Q = v_next[econ_gen.node_Q]

            #P is actually a negative range, so signs are flipped.
            # if P < econ_gen.P_max + buffer:
            #     print(f"{econ_gen.bus.Bus}: P_max hit")
            #     v_next[econ_gen.node_P] = econ_gen.P_max + buffer
            # elif P > econ_gen.P_min - buffer:
            #     print(f"{econ_gen.bus.Bus}: P_min hit")
            #     v_next[econ_gen.node_P] = econ_gen.P_min - buffer
            
            # if Q > econ_gen.Q_max - buffer:
            #     print(f"{econ_gen.bus.Bus}: Q_max hit")
            #     v_next[econ_gen.node_Q] = econ_gen.Q_max - buffer
            # elif Q < econ_gen.Q_min + buffer:
            #     print(f"{econ_gen.bus.Bus}: Q_min hit")
            #     v_next[econ_gen.node_Q] = econ_gen.Q_min + buffer
        
        for v_limiter in self.v_limiters:
            V_mag = np.sqrt(v_next[v_limiter.bus.node_Vr]**2 + v_next[v_limiter.bus.node_Vi]**2)

            if V_mag > v_limiter.V_max - buffer:
                print(f"{v_limiter.bus.Bus}: V_max hit")
                v_next[econ_gen.node_Q] = v_limiter.V_max - buffer
            elif V_mag < v_limiter.V_min + buffer:
                print(f"{v_limiter.bus.Bus}: V_min hit")
                v_next[econ_gen.node_Q] = v_limiter.V_min + buffer
        return v_next