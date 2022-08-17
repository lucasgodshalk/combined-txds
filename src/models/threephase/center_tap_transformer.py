from collections import defaultdict
from typing import List
import numpy as np
from sympy import symbols
from logic.lagrangehandler import LagrangeHandler
from logic.lagrangestamper import SKIP, LagrangeStamper
from models.shared.bus import GROUND
from models.shared.line import build_line_stamper_bus
from models.helpers import merge_residuals
from models.threephase.center_tap_transformer_coil import CenterTapTransformerCoil

constants = tr_orig, tx_factor = symbols('tr tx_factor')
primals = [Vr_pri, Vi_pri, Ir_L1, Ii_L1, Vr_L1, Vi_L1, Ir_L2, Ii_L2, Vr_L2, Vi_L2] = symbols('Vr_pri, Vi_pri, Ir_L1, Ii_L1, Vr_L1, Vi_L1, Ir_L2, Ii_L2, Vr_L2, Vi_L2')
duals = [Lr_pri, Li_pri, Lir_L1, Lii_L1, Lr_L1, Li_L1, Lir_L2, Lii_L2, Lr_L2, Li_L2] = symbols('Lr_pri, Li_pri, Lir_L1, Lii_L1, Lr_L1, Li_L1, Lir_L2, Lii_L2, Lr_L2, Li_L2')

tr = tr_orig + (1 - tr_orig) * tx_factor 

#Kersting:
#E_0 = 1/tr * Vt_1
#E_0 = -1/tr * Vt_2
#I_0 = 1/tr * (I_1 - I_2)
#I_0 => Leaving primary (positive), I_1, I_2 => Entering secondary (negative). 

eqns = [
    1 / tr * (-Ir_L1 + Ir_L2),
    1 / tr * (-Ii_L1 + Ii_L2),
    Vr_L1 - 1 / tr * Vr_pri,
    Vi_L1 - 1 / tr * Vi_pri,
    Ir_L1,
    Ii_L1,
    Vr_L2 + 1 / tr * Vr_pri,
    Vi_L2 + 1 / tr * Vi_pri,
    Ir_L2,
    Ii_L2
]

lagrange = np.dot(duals, eqns)

center_tap_xfmr_lh = LagrangeHandler(lagrange, constants, primals, duals)

class CenterTapTransformer():
    def __init__(self
                , coil_1
                , coil_2
                , coil_3
                , phase
                , turn_ratio
                , power_rating
                , g_shunt
                , b_shunt
                ):
        self.coils: List[CenterTapTransformerCoil]
        self.coils = [coil_1, coil_2, coil_3]
        self.phases = phase
        self.turn_ratio = turn_ratio
        self.power_rating = power_rating
        self.g_shunt = g_shunt
        self.b_shunt = b_shunt

        # Values for the primary coil impedance stamps, converted out of per-unit
        r0 = self.coils[0].resistance * self.coils[0].nominal_voltage ** 2  / self.power_rating
        x0 = self.coils[0].reactance * self.coils[0].nominal_voltage ** 2  / self.power_rating
        self.g0 = r0 / (r0**2 + x0**2) if not (r0 == 0 and x0 == 0) else 0
        self.b0 = -x0 / (r0**2 + x0**2) if not (r0 == 0 and x0 == 0) else 0

        # Values for the first triplex coil impedance stamps, converted out of per-unit
        r1 = self.coils[1].resistance * self.coils[1].nominal_voltage ** 2  / self.power_rating
        x1 = self.coils[1].reactance * self.coils[1].nominal_voltage ** 2  / self.power_rating
        self.g1 = r1 / (r1**2 + x1**2) if not (r1 == 0 and x1 == 0) else 0
        self.b1 = -x1 / (r1**2 + x1**2) if not (r1 == 0 and x1 == 0) else 0

        # Values for the second triplex coil impedance stamps, converted out of per-unit
        r2 = self.coils[2].resistance * self.coils[2].nominal_voltage ** 2  / self.power_rating
        x2 = self.coils[2].reactance * self.coils[2].nominal_voltage ** 2  / self.power_rating
        self.g2 = r2 / (r2**2 + x2**2) if not (r2 == 0 and x2 == 0) else 0
        self.b2 = -x2 / (r2**2 + x2**2) if not (r2 == 0 and x2 == 0) else 0

    def assign_nodes(self, node_index, optimization_enabled):
        self.primary_impedance_stamper = build_line_stamper_bus(self.coils[0].from_node, self.coils[0].primary_node, optimization_enabled)
        
        self.L1_impedance_stamper = build_line_stamper_bus(self.coils[1].sending_node, self.coils[1].to_node, optimization_enabled)

        self.L2_impedance_stamper = build_line_stamper_bus(self.coils[2].sending_node, self.coils[2].to_node, optimization_enabled)

        from_bus = self.coils[0].primary_node
        L1_bus = self.coils[1].sending_node
        L2_bus = self.coils[2].sending_node

        self.node_L1_Ir = next(node_index)
        self.node_L1_Ii = next(node_index)
        self.node_L2_Ir = next(node_index)
        self.node_L2_Ii = next(node_index)

        index_map = {}
        index_map[Vr_pri] = from_bus.node_Vr
        index_map[Vi_pri] = from_bus.node_Vi
        index_map[Ir_L1] = self.node_L1_Ir
        index_map[Ii_L1] = self.node_L1_Ii
        index_map[Ir_L2] = self.node_L2_Ir
        index_map[Ii_L2] = self.node_L2_Ii
        index_map[Vr_L1] = L1_bus.node_Vr
        index_map[Vi_L1] = L1_bus.node_Vi
        index_map[Vr_L2] = L2_bus.node_Vr
        index_map[Vi_L2] = L2_bus.node_Vi

        if optimization_enabled:
            index_map[Lr_pri] = from_bus.node_lambda_Vr
            index_map[Li_pri] = from_bus.node_lambda_Vi
            index_map[Lir_L1] = next(node_index)
            index_map[Lii_L1] = next(node_index)
            index_map[Lir_L2] = next(node_index)
            index_map[Lii_L2] = next(node_index)
            index_map[Lr_L1] = L1_bus.node_lambda_Vr
            index_map[Li_L1] = L1_bus.node_lambda_Vi
            index_map[Lr_L2] = L2_bus.node_lambda_Vr
            index_map[Li_L2] = L2_bus.node_lambda_Vi
        else:
            index_map[Lr_pri] = SKIP
            index_map[Li_pri] = SKIP
            index_map[Lir_L1] = SKIP
            index_map[Lii_L1] = SKIP
            index_map[Lir_L2] = SKIP
            index_map[Lii_L2] = SKIP
            index_map[Lr_L1] = SKIP
            index_map[Li_L1] = SKIP
            index_map[Lr_L2] = SKIP
            index_map[Li_L2] = SKIP

        self.center_tap_xfmr_stamper = LagrangeStamper(center_tap_xfmr_lh, index_map, optimization_enabled)

    def get_connections(self):
        return [
            (self.coils[0].primary_node, self.coils[1].sending_node), 
            (self.coils[0].primary_node, self.coils[2].sending_node)
        ]

    def stamp_primal(self, Y, J, v_previous, tx_factor, state):
        self.center_tap_xfmr_stamper.stamp_primal(Y, J, [self.turn_ratio, tx_factor], v_previous)
        self.primary_impedance_stamper.stamp_primal(Y, J, [self.g0, self.b0, tx_factor], v_previous)
        self.L1_impedance_stamper.stamp_primal(Y, J, [self.g1, self.b1, tx_factor], v_previous)
        self.L2_impedance_stamper.stamp_primal(Y, J, [self.g2, self.b2, tx_factor], v_previous)

    def stamp_dual(self, Y, J, v_previous, tx_factor, state):
        raise Exception("Not implemented")

    def calculate_residuals(self, state, v):
        center_tap_xfmr_resid = self.center_tap_xfmr_stamper.calc_residuals([self.turn_ratio, 0], v)
        pri_imp_resid = self.primary_impedance_stamper.calc_residuals([self.g0, self.b0, 0], v)
        L1_imp_resid = self.L1_impedance_stamper.calc_residuals([self.g1, self.b1, 0], v)
        L2_imp_resid = self.L2_impedance_stamper.calc_residuals([self.g2, self.b2, 0], v)

        return merge_residuals({}, center_tap_xfmr_resid, pri_imp_resid, L1_imp_resid, L2_imp_resid)

