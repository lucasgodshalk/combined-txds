from itertools import count
import numpy as np
from sympy import symbols
from logic.stamping.lagrangesegment import TwoTerminalModelDefinition, KCL_r, KCL_i
from logic.stamping.lagrangestampdetails import build_two_terminal_stamp_details
from models.components.bus import Bus
from models.components.line import build_line_stamper_bus
from logic.stamping.matrixstamper import build_stamps_from_stampers
from models.wellknownvariables import Vr_from, Vi_from, Vr_to, Vi_to, Lr_from, Li_from, Lr_to, Li_to

#Eqns reference:
# Pandey, A. (2018). 
# Robust Steady-State Analysis of Power Grid using Equivalent Circuit Formulation with Circuit Simulation Methods

#Constant real & reactive power loads
#Eqn 25 & 26, pg 45
constants = P, Q = symbols('P, Q')
variables = Vr_from, Vi_from, Vr_to, Vi_to

Vr = Vr_from - Vr_to
Vi = Vi_from - Vi_to

kcl_r = KCL_r((P * Vr + Q * Vi) / (Vr ** 2 + Vi ** 2))
kcl_i = KCL_i((P * Vi - Q * Vr) / (Vr ** 2 + Vi ** 2))

lh_pq = TwoTerminalModelDefinition(variables, constants, kcl_r, kcl_i)

#Constant Current loads
constants = IP, IQ = symbols('IP, IQ')

kcl_r = KCL_r(IP)
kcl_i = KCL_i(IQ)

lh_Ic = TwoTerminalModelDefinition(variables, constants, kcl_r, kcl_i)

#Zip loads (partially implemented)
#Eqn 31 & 32, pg 47

constants = Ic_mag, cos_Ipf, sin_Ipf = symbols('Ic_mag, cos_Ipf, sin_Ipf')

V_ratio = Vi/Vr
cos_arctan_V = 1 / (V_ratio**2 + 1)**0.5
sin_arctan_V = V_ratio / (V_ratio**2 + 1)**0.5

#Only have the constant current component for now.
kcl_r = KCL_r(Ic_mag * (cos_arctan_V * cos_Ipf - sin_arctan_V * sin_Ipf))
kcl_i = KCL_i(Ic_mag * (sin_arctan_V * cos_Ipf + cos_arctan_V * sin_Ipf))

lh_zip = TwoTerminalModelDefinition(variables, constants, kcl_r, kcl_i)

#Represents a two-terminal load. Can be used for positive sequence or three phase.
class Load:
    _ids = count(0)

    def __init__(self,
                 from_bus: Bus,
                 to_bus: Bus,
                 P,
                 Q,
                 Z,
                 IP,
                 IQ,
                 load_num=None,
                 phase=None,
                 triplex_phase=None
                 ):
        """Initialize an instance of a PQ or ZIP load in the power grid.

        Args:
            Bus (int): the bus where the load is located
            P (float): the active power of a constant power (PQ) load.
            Q (float): the reactive power of a constant power (PQ) load.
            Z (complex): the linear impedance of the load.
            IP (float): the active power component of a constant current load.
            IQ (float): the reactive power component of a constant current load.
        """

        self.id = Load._ids.__next__()
        self.load_num = load_num if load_num != None else str(self.id)
        self.phase = phase
        self.triplex_phase = triplex_phase

        self.from_bus = from_bus
        self.to_bus = to_bus
        self.P = P
        self.Q = Q
        self.Z = Z

        self.IP = IP
        self.IQ = IQ

        # self.Ic_mag = np.sqrt(IP**2 + IQ**2)
        # if IP == 0:
        #     self.cos_Ipf = 0
        #     self.sin_Ipf = 1
        # else:
        #     self.cos_Ipf = np.cos(np.arctan(IQ/IP))
        #     self.sin_Ipf = np.sin(np.arctan(IQ/IP))

        if not self.Z == 0:
            r = np.real(self.Z)
            x = np.imag(self.Z)
            self.G = r / (r**2 + x**2)
            self.B = -x / (r**2 + x**2)
        else:
            self.G = 0
            self.B = 0

    def assign_nodes(self, node_index, optimization_enabled):
        if self.P == 0 and self.Q == 0:
            self.stamper_pq = None
        else:
            self.stamper_pq = build_two_terminal_stamp_details(lh_pq, self.from_bus, self.to_bus, node_index, optimization_enabled)

        if self.IP == 0 and self.IQ == 0:
            self.stamper_Ic = None
        else:
            self.stamper_Ic = build_two_terminal_stamp_details(lh_Ic, self.from_bus, self.to_bus, node_index, optimization_enabled)

        if self.Z == 0:
            self.stamper_z = None
        else:
            self.stamper_z = build_line_stamper_bus(self.from_bus, self.to_bus, optimization_enabled, is_shunt=True)

    def get_stamps(self):
        return build_stamps_from_stampers(self, 
            (self.stamper_pq, [self.P, self.Q]),
            (self.stamper_Ic, [self.IP, self.IQ]),
            (self.stamper_z, [self.G, self.B, 0]),
            )

    def get_connections(self):
        return [(self.from_bus, self.to_bus)]
