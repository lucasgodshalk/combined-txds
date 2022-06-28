from typing import List
import numpy as np
from models.shared.bus import Bus

V_DIFF_MAX = 1
V_MAX = 2
V_MIN = -2

class PositiveSeqVoltageLimiting:
    def __init__(self, buses: List[Bus], size_Y) -> None:
        self.buses = buses
        self.size_Y = size_Y

        self.bus_mask = [False] * size_Y
        for bus in self.buses:
           self.bus_mask[bus.node_Vr] = True
           self.bus_mask[bus.node_Vi] = True
    
    def apply_limiting(self, v_next, v_previous, diff):
        diff_clip = np.clip(diff, -V_DIFF_MAX, V_DIFF_MAX)
        v_next_clip = np.clip(v_previous + diff_clip, V_MIN, V_MAX)

        v_next[self.bus_mask] = v_next_clip[self.bus_mask]

        return v_next