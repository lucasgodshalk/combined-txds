from typing import List
import numpy as np
from logic.networkmodel import NetworkModel

V_DIFF_MAX = 1
V_MAX = 2
V_MIN = -2

class PositiveSeqVoltageLimiting:
    def __init__(self, network: NetworkModel) -> None:
        self.network = network
        self.version = None

    def try_create_mask(self):
        if self.version == self.network.matrix_version:
            return

        self.bus_mask = [False] * self.network.size_Y
        for bus in self.network.buses:
           self.bus_mask[bus.node_Vr] = True
           self.bus_mask[bus.node_Vi] = True
    
    def apply_limiting(self, v_next, v_previous, diff):
        self.try_create_mask()

        diff_clip = np.clip(diff, -V_DIFF_MAX, V_DIFF_MAX)
        v_next_clip = np.clip(v_previous + diff_clip, V_MIN, V_MAX)

        v_next[self.bus_mask] = v_next_clip[self.bus_mask]

        return v_next