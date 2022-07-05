from collections import defaultdict

import math
import typing
from logic.lagrangestamper import SKIP, LagrangeStamper
from logic.matrixbuilder import MatrixBuilder
from models.positiveseq.shared import build_line_stamper
from models.shared.bus import GROUND
from models.shared.transformer import xfrmr_lh
from models.shared.transformer import Vr_pri_pos, Vr_pri_neg, Vi_pri_pos, Vi_pri_neg, Ir_prim, Ii_prim, Vr_sec_pos, Vr_sec_neg, Vi_sec_pos, Vi_sec_neg, Lr_pri_pos, Lr_pri_neg, Li_pri_pos, Li_pri_neg, Lir_prim, Lii_prim, Lr_sec_pos, Lr_sec_neg, Li_sec_pos, Li_sec_neg
from models.threephase.primary_transformer_coil import PrimaryTransformerCoil
from models.threephase.secondary_transformer_coil import SecondaryTransformerCoil


NEUTRAL = "N"

class Transformer():
    
    def __init__(self
                , primary_coil: PrimaryTransformerCoil
                , secondary_coil: SecondaryTransformerCoil
                , phases: typing.List[str]
                , turn_ratio
                , phase_shift
                , g_shunt
                , b_shunt
                , optimization_enabled
                ):
        self.primary_coil = primary_coil
        self.secondary_coil = secondary_coil
        self.phases = phases
        self.turn_ratio = turn_ratio
        self.phase_shift = phase_shift
        self.g_shunt = g_shunt
        self.b_shunt = b_shunt

        phase_list = self.get_phase_list()

        self.stampers = {}

        for (pos_phase_1, neg_phase_1, pos_phase_2, neg_phase_2) in phase_list:
            from_bus_pos = self.primary_coil.phase_coils[pos_phase_1].from_node
            if neg_phase_1 == NEUTRAL:
                from_bus_neg = GROUND
            else:
                from_bus_neg = self.primary_coil.phase_coils[neg_phase_1].from_node
            v_r_p = self.primary_coil.phase_coils[pos_phase_1].real_voltage_idx
            v_i_p = self.primary_coil.phase_coils[pos_phase_1].imag_voltage_idx
            L_r_p = self.primary_coil.phase_coils[pos_phase_1].real_lambda_idx
            L_i_p = self.primary_coil.phase_coils[pos_phase_1].imag_lambda_idx
            secondary_bus = self.secondary_coil.phase_coils[pos_phase_2].secondary_node
            to_bus_pos = self.secondary_coil.phase_coils[pos_phase_2].to_node
            if neg_phase_2 == NEUTRAL:
                to_bus_neg = GROUND
            else:
                to_bus_neg = self.secondary_coil.phase_coils[neg_phase_2].to_node

            index_map = {}
            index_map[Vr_pri_pos] = from_bus_pos.node_Vr
            index_map[Vi_pri_pos] = from_bus_pos.node_Vi
            index_map[Vr_pri_neg] = from_bus_neg.node_Vr
            index_map[Vi_pri_neg] = from_bus_neg.node_Vi
            index_map[Ir_prim] = v_r_p
            index_map[Ii_prim] = v_i_p
            index_map[Vr_sec_pos] = secondary_bus.node_Vr
            index_map[Vi_sec_pos] = secondary_bus.node_Vi
            index_map[Vr_sec_neg] = to_bus_neg.node_Vr
            index_map[Vi_sec_neg] = to_bus_neg.node_Vi

            index_map[Lr_pri_pos] = from_bus_pos.node_lambda_Vr
            index_map[Li_pri_pos] = from_bus_pos.node_lambda_Vi
            index_map[Lr_pri_neg] = from_bus_neg.node_lambda_Vr
            index_map[Li_pri_neg] = from_bus_neg.node_lambda_Vi
            index_map[Lir_prim] = L_r_p
            index_map[Lii_prim] = L_i_p
            index_map[Lr_sec_pos] = secondary_bus.node_lambda_Vr
            index_map[Li_sec_pos] = secondary_bus.node_lambda_Vi
            index_map[Lr_sec_neg] = to_bus_neg.node_lambda_Vr
            index_map[Li_sec_neg] = to_bus_neg.node_lambda_Vi

            xfrmr_stamper = LagrangeStamper(xfrmr_lh, index_map, optimization_enabled)

            losses_stamper = build_line_stamper(
                secondary_bus.node_Vr, 
                secondary_bus.node_Vi, 
                to_bus_pos.node_Vr, 
                to_bus_pos.node_Vi,
                secondary_bus.node_lambda_Vr, 
                secondary_bus.node_lambda_Vi, 
                to_bus_pos.node_lambda_Vr, 
                to_bus_pos.node_lambda_Vi,
                optimization_enabled
                )

            self.stampers[(pos_phase_1, pos_phase_2)] = (xfrmr_stamper, losses_stamper)
        
    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, state):
        phase_list = self.get_phase_list()

        for (pos_phase_1, neg_phase_1, pos_phase_2, neg_phase_2) in phase_list:

            xfrmr_stamper, losses_stamper = self.stampers[(pos_phase_1, pos_phase_2)]

            # Values for the secondary coil stamps, converted out of per-unit
            r = self.secondary_coil.resistance * self.secondary_coil.nominal_voltage ** 2  / self.secondary_coil.rated_power
            x = self.secondary_coil.reactance * self.secondary_coil.nominal_voltage ** 2  / self.secondary_coil.rated_power
            g = r / (r**2 + x**2)
            b = -x / (r**2 + x**2)

            xfrmr_stamper.stamp_primal(Y, J, [self.turn_ratio, self.phase_shift, tx_factor], v_previous)
            losses_stamper.stamp_primal(Y, J, [g, -b, tx_factor], v_previous)


    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        phase_list = self.get_phase_list()

        for (pos_phase_1, neg_phase_1, pos_phase_2, neg_phase_2) in phase_list:

            xfrmr_stamper, losses_stamper = self.stampers[(pos_phase_1, pos_phase_2)]

            # Values for the secondary coil stamps, converted out of per-unit
            r = self.secondary_coil.resistance * self.secondary_coil.nominal_voltage ** 2  / self.secondary_coil.rated_power
            x = self.secondary_coil.reactance * self.secondary_coil.nominal_voltage ** 2  / self.secondary_coil.rated_power
            g = r / (r**2 + x**2)
            b = -x / (r**2 + x**2)

            xfrmr_stamper.stamp_dual(Y, J, [self.turn_ratio, self.phase_shift, tx_factor], v_previous)
            losses_stamper.stamp_dual(Y, J, [g, -b, tx_factor], v_previous)

    def calculate_residuals(self, state, v):
        residuals = defaultdict(lambda: 0)
        phase_list = self.get_phase_list()

        for (pos_phase_1, neg_phase_1, pos_phase_2, neg_phase_2) in phase_list:

            # Values for the secondary coil stamps, converted out of per-unit
            r = self.secondary_coil.resistance * self.secondary_coil.nominal_voltage ** 2  / self.secondary_coil.rated_power
            x = self.secondary_coil.reactance * self.secondary_coil.nominal_voltage ** 2  / self.secondary_coil.rated_power
            g = r / (r**2 + x**2)
            b = -x / (r**2 + x**2)

            xfrmr_stamper, losses_stamper = self.stampers[(pos_phase_1, pos_phase_2)]
            for (key, value) in xfrmr_stamper.calc_residuals([self.turn_ratio, self.phase_shift, 1], v).items():
                residuals[key] += value
            for (key, value) in losses_stamper.calc_residuals([g, -b, 1], v).items():
                residuals[key] += value

        return residuals

    def get_phase_list(self):
        rotated_phases = self.phases[1:] + self.phases[:1]
        phase_list: typing.List[str]
        phase_list = list.copy(self.phases)
        if self.primary_coil.connection_type == "D":
            for i in range(len(phase_list)):
                phase_list[i] += rotated_phases[i]
        else:
            for i in range(len(phase_list)):
                phase_list[i] += NEUTRAL
                
        for i in range(len(phase_list)):
            phase_list[i] += self.phases[i]

        if self.secondary_coil.connection_type == "D":
            for i in range(len(phase_list)):
                phase_list[i] += rotated_phases[i]
        else:
            for i in range(len(phase_list)):
                phase_list[i] += NEUTRAL
        return phase_list

