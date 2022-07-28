from collections import defaultdict
import numpy as np
from sympy import symbols
from logic.lagrangehandler import LagrangeHandler
from logic.lagrangestamper import SKIP, LagrangeStamper
from models.shared.line import build_line_stamper_bus
from models.helpers import merge_residuals

constants = tr, tx_factor = symbols('tr tx_factor')
primals = [Vr_pri, Vi_pri, Ir_L1, Ii_L1, Vr_L1, Vi_L1, Ir_L2, Ii_L2, Vr_L2, Vi_L2] = symbols('Vr_pri, Vi_pri, Ir_L1, Ii_L1, Vr_L1, Vi_L1, Ir_L2, Ii_L2, Vr_L2, Vi_L2')
duals = [Lr_pri, Li_pri, Lir_L1, Lii_L1, Lr_L1, Li_L1, Lir_L2, Lii_L2, Lr_L2, Li_L2] = symbols('Lr_pri, Li_pri, Lir_L1, Lii_L1, Lr_L1, Li_L1, Lir_L2, Lii_L2, Lr_L2, Li_L2')

scaled_tr = tr + (1 - tr) * tx_factor 

eqns = [
    -1/scaled_tr * Ir_L1 - 1/scaled_tr * Ir_L2,
    -1/scaled_tr * Ii_L1 - 1/scaled_tr * Ii_L2,
    Vr_L1 - 1/scaled_tr * Vr_pri,
    Vi_L1 - 1/scaled_tr * Vi_pri,
    Ir_L1,
    Ii_L1,
    Vr_L2 - 1/scaled_tr * Vr_pri,
    Vi_L2 - 1/scaled_tr * Vi_pri,
    Ir_L2,
    Ii_L2
]

lagrange = np.dot(duals, eqns)

center_tap_xfmr_lh = LagrangeHandler(lagrange, constants, primals, duals)

USE_SYMBOLIC = True

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
        self.coils = [coil_1, coil_2, coil_3]
        self.phases = phase
        self.turn_ratio = turn_ratio
        self.power_rating = power_rating
        self.g_shunt = g_shunt
        self.b_shunt = b_shunt

    def assign_nodes(self, node_index, optimization_enabled):
        # Values for the primary coil impedance stamps, converted out of per-unit
        r0 = self.coils[0].resistance * self.coils[0].nominal_voltage ** 2  / self.power_rating
        x0 = self.coils[0].reactance * self.coils[0].nominal_voltage ** 2  / self.power_rating
        self.g0 = r0 / (r0**2 + x0**2) if not (r0 == 0 and x0 == 0) else 0
        self.b0 = -x0 / (r0**2 + x0**2) if not (r0 == 0 and x0 == 0) else 0
        self.primary_impedance_stamper = build_line_stamper_bus(self.coils[0].from_node, self.coils[0].primary_node, optimization_enabled)
                
        # Values for the first triplex coil impedance stamps, converted out of per-unit
        r1 = self.coils[1].resistance * self.coils[1].nominal_voltage ** 2  / self.power_rating
        x1 = self.coils[1].reactance * self.coils[1].nominal_voltage ** 2  / self.power_rating
        self.g1 = r1 / (r1**2 + x1**2) if not (r1 == 0 and x1 == 0) else 0
        self.b1 = -x1 / (r1**2 + x1**2) if not (r1 == 0 and x1 == 0) else 0
        self.L1_impedance_stamper = build_line_stamper_bus(self.coils[1].sending_node, self.coils[1].to_node, optimization_enabled)
                
        # Values for the second triplex coil impedance stamps, converted out of per-unit
        r2 = self.coils[2].resistance * self.coils[2].nominal_voltage ** 2  / self.power_rating
        x2 = self.coils[2].reactance * self.coils[2].nominal_voltage ** 2  / self.power_rating
        self.g2 = r2 / (r2**2 + x2**2) if not (r2 == 0 and x2 == 0) else 0
        self.b2 = -x2 / (r2**2 + x2**2) if not (r2 == 0 and x2 == 0) else 0
        self.L2_impedance_stamper = build_line_stamper_bus(self.coils[2].sending_node, self.coils[2].to_node, optimization_enabled)

        index_map = {}
        index_map[Vr_pri] = self.coils[0].primary_node.node_Vr
        index_map[Vi_pri] = self.coils[0].primary_node.node_Vi
        index_map[Ir_L1] = self.coils[1].real_voltage_idx
        index_map[Ii_L1] = self.coils[1].imag_voltage_idx
        index_map[Ir_L2] = self.coils[2].real_voltage_idx
        index_map[Ii_L2] = self.coils[2].imag_voltage_idx
        index_map[Vr_L1] = self.coils[1].sending_node.node_Vr
        index_map[Vi_L1] = self.coils[1].sending_node.node_Vi
        index_map[Vr_L2] = self.coils[2].sending_node.node_Vr
        index_map[Vi_L2] = self.coils[2].sending_node.node_Vi
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
        return []

    def stamp_primal(self, Y, J, v_previous, tx_factor, state):
        if not USE_SYMBOLIC:
            v_r_p, v_i_p = self.coils[0].primary_node.node_Vr, self.coils[0].primary_node.node_Vi
            v_r_1x, v_i_1x = self.coils[1].sending_node.node_Vr, self.coils[1].sending_node.node_Vi
            v_r_2x, v_i_2x = self.coils[2].sending_node.node_Vr, self.coils[2].sending_node.node_Vi
            v_r_1s = self.coils[1].real_voltage_idx
            v_i_1s = self.coils[1].imag_voltage_idx
            v_r_2s = self.coils[2].real_voltage_idx
            v_i_2s = self.coils[2].imag_voltage_idx

            # Stamps for the current sources on the primary coil
            Y.stamp(v_r_p, v_r_1s, -1/self.turn_ratio)
            Y.stamp(v_r_p, v_r_2s, -1/self.turn_ratio)
            Y.stamp(v_i_p, v_i_1s, -1/self.turn_ratio)
            Y.stamp(v_i_p, v_i_2s, -1/self.turn_ratio)

            # Stamps for the voltage sources
            Y.stamp(v_r_1s, v_r_1x, 1)
            Y.stamp(v_r_1s, v_r_p, -1/self.turn_ratio)

            Y.stamp(v_r_2s, v_r_2x, 1)
            Y.stamp(v_r_2s, v_r_p, -1/self.turn_ratio)

            Y.stamp(v_i_1s, v_i_1x, 1)
            Y.stamp(v_i_1s, v_i_p, -1/self.turn_ratio)

            Y.stamp(v_i_2s, v_i_2x, 1)
            Y.stamp(v_i_2s, v_i_p, -1/self.turn_ratio)
            
            # Stamps for the new state variables (current at the voltage source)
            Y.stamp(v_r_1x, v_r_1s, 1)
            Y.stamp(v_i_1x, v_i_1s, 1)
            Y.stamp(v_r_2x, v_r_2s, 1)
            Y.stamp(v_i_2x, v_i_2s, 1)
        else:
            self.center_tap_xfmr_stamper.stamp_primal(Y, J, [self.turn_ratio, tx_factor], v_previous)
                
        self.primary_impedance_stamper.stamp_primal(Y, J, [self.g0, self.b0, tx_factor], v_previous)
        self.L1_impedance_stamper.stamp_primal(Y, J, [self.g1, self.b1, tx_factor], v_previous)
        self.L2_impedance_stamper.stamp_primal(Y, J, [self.g2, self.b2, tx_factor], v_previous)

    def stamp_dual(self, Y, J, v_previous, tx_factor, state):
        raise Exception("Not implemented")

    def calculate_residuals(self, state, v):
        if USE_SYMBOLIC:
            center_tap_xfmr_resid = self.center_tap_xfmr_stamper.calc_residuals([self.turn_ratio, 0], v)
            pri_imp_resid = self.primary_impedance_stamper.calc_residuals([self.g0, self.b0, 0], v)
            L1_imp_resid = self.L1_impedance_stamper.calc_residuals([self.g1, self.b1, 0], v)
            L2_imp_resid = self.L2_impedance_stamper.calc_residuals([self.g2, self.b2, 0], v)

            return merge_residuals({}, center_tap_xfmr_resid, pri_imp_resid, L1_imp_resid, L2_imp_resid)
        else:
            return {}

