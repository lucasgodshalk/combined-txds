from cmath import pi
from itertools import count
import numpy as np

class SimulationState():
    # The id of the node connected to ground
    GROUND_NODE = -1
    OMEGA = 2 * pi * 60

    def __init__(self):
        # The next index of J to use
        self.next_var_idx = count(0)
        self.J_length = 0
        # The map from each bus id to the location of its (real, imaginary) state variables in J
        self.bus_map = {}
        # The map from a bus name to its bus id
        self.bus_name_map = {}

        # All of the loads    
        self.loads = []
        # All of the transmission lines
        self.transmission_lines = []
        # All of the infinite sources (multi-phase slack buses)
        self.infinite_sources = []
        # All of the transformers
        self.transformers = []
        # All of the other buses
        self.buses = []
        # All of the capacitors
        self.capacitors = []
        # All of the fuses
        self.fuses = []
        # All of the switches
        self.switches = []
        # All of the regulators
        self.regulators = []

        # Reference nodes to be removed from the set of equations
        self.reference_r = None
        self.reference_i = None

        self.reset_linear_stamp_collection()
        self.reset_nonlinear_stamp_collection()

    def reset_linear_stamp_collection(self):
        # To collect information for linear Y stamps
        self.lin_Y_stamp_coord1 = []
        self.lin_Y_stamp_coord2 = []
        self.lin_Y_stamp_val = []

        # The actual stamp
        self.lin_Y = None

        # To collect information for linear J stamps
        self.lin_J_stamp_coord = []
        self.lin_J_stamp_val = []

        # The actual stamp
        self.lin_J = None

    def reset_nonlinear_stamp_collection(self):
        # To collect information for nonlinear Y stamps
        self.nonlin_Y_stamp_coord1 = []
        self.nonlin_Y_stamp_coord2 = []
        self.nonlin_Y_stamp_val = []

        # The actual stamp
        self.nonlin_Y = None

        # To collect information for nonlinear J stamps
        self.nonlin_J_stamp_coord = []
        self.nonlin_J_stamp_val = []

        # The actual stamp
        self.nonlin_J = None
