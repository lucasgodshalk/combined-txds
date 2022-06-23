from itertools import count
import math

# A Bus represents one node of the real circuit, and one node of the imaginary circuit, of a single phase.
class Bus():

    _bus_ids = count(0)

    def __init__(self, voltage_magnitude=0, voltage_angle=0, bus_id = None, node_name = None, node_phase = None):
        self.bus_id = bus_id if bus_id is not None else self._bus_ids.__next__()
        self.voltage_magnitude = voltage_magnitude
        self.voltage_angle = voltage_angle
        self.v_r = abs(self.voltage_magnitude)*math.cos(self.voltage_angle)
        self.v_i = abs(self.voltage_magnitude)*math.sin(self.voltage_angle)
        self.node_name = node_name
        self.node_phase = node_phase

    def set_initial_voltages(self, state, v):
        f_r, f_i = state.bus_map[self.bus_id]
        v[f_r] = self.v_r if v[f_r] == 0 else v[f_r]
        v[f_i] = self.v_i if v[f_i] == 0 else v[f_i]
    
    def __repr__(self) -> str:
        return f'Id: {self.bus_id} Node: {self.node_name} Phase: {self.node_phase}'
