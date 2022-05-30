from typing import List
import numpy as np
from lib.settings import Settings
from models.Buses import Bus
from models.Generators import Generators
from models.Slack import Slack

BUS_Vr_FLAT = 1
BUS_Vi_FLAT = 0
BUS_Q_FLAT = -1

def initialize(Y_size, buses: List[Bus], generators: List[Generators], slacks: List[Slack], settings: Settings):
    v_init = np.zeros(Y_size)

    for bus in buses:
        (vr_idx, vr_init) = bus.get_Vr_init()
        v_init[vr_idx] = BUS_Vr_FLAT if settings.flat_start else vr_init

        (vi_idx, vi_init) = bus.get_Vi_init()
        v_init[vi_idx] = BUS_Vi_FLAT if settings.flat_start else vi_init

        if settings.infeasibility_analysis:
            Lr_idx, Lr_init = bus.get_Lr_init()
            v_init[Lr_idx] = Lr_init

            Li_idx, Li_init = bus.get_Li_init()
            v_init[Li_idx] = Li_init

            LQ_idx, LQ_init = bus.get_LQ_init()
            if LQ_idx is not None:
                v_init[LQ_idx] = LQ_init

    for generator in generators:
        v_init[generator.bus.node_Q] = (generator.Qmin + generator.Qmax) / 2 if settings.flat_start else generator.Qinit

    for slack in slacks:
        v_init[slack.slack_Ir] = 0 if settings.flat_start else slack.Pinit
        v_init[slack.slack_Ii] = 0 if settings.flat_start else slack.Qinit

    return v_init

