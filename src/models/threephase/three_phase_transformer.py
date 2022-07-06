from collections import defaultdict
import typing
from logic.matrixbuilder import MatrixBuilder
from models.shared.bus import GROUND
from models.shared.single_phase_transformer import SinglePhaseTransformer
from models.threephase.primary_transformer_coil import PrimaryTransformerCoil
from models.threephase.secondary_transformer_coil import SecondaryTransformerCoil

NEUTRAL = "N"

class ThreePhaseTransformer():
    
    def __init__(self
                , primary_coil: PrimaryTransformerCoil
                , secondary_coil: SecondaryTransformerCoil
                , phases: typing.List[str]
                , turn_ratio
                , phase_shift
                , g_shunt
                , b_shunt
                , optimization_enabled
                , next_var_idx
                ):
        self.primary_coil = primary_coil
        self.secondary_coil = secondary_coil
        self.phases = phases
        self.turn_ratio = turn_ratio
        self.phase_shift = phase_shift
        self.g_shunt = g_shunt
        self.b_shunt = b_shunt

        phase_list = self.get_phase_list()

        self.xfmrs: typing.Dict[any, SinglePhaseTransformer]
        self.xfmrs = {}

        for (pos_phase_1, neg_phase_1, pos_phase_2, neg_phase_2) in phase_list:
            from_bus_pos = self.primary_coil.phase_connections[pos_phase_1]
            if neg_phase_1 == NEUTRAL:
                from_bus_neg = GROUND
            else:
                from_bus_neg = self.primary_coil.phase_connections[neg_phase_1]
            to_bus_pos = self.secondary_coil.phase_connections[pos_phase_2]
            if neg_phase_2 == NEUTRAL:
                to_bus_neg = GROUND
            else:
                to_bus_neg = self.secondary_coil.phase_connections[neg_phase_2]

            # Values for the secondary coil stamps, converted out of per-unit
            r = self.secondary_coil.resistance * self.secondary_coil.nominal_voltage ** 2  / self.secondary_coil.rated_power
            x = self.secondary_coil.reactance * self.secondary_coil.nominal_voltage ** 2  / self.secondary_coil.rated_power

            xfmr = SinglePhaseTransformer(
                from_bus_pos, 
                from_bus_neg, 
                to_bus_pos, 
                to_bus_neg, 
                r, 
                x, 
                True, 
                self.turn_ratio,
                self.phase_shift, 
                self.g_shunt,
                self.b_shunt,
                None
                )
            
            xfmr.assign_nodes(next_var_idx, optimization_enabled)

            self.xfmrs[(pos_phase_1, pos_phase_2)] = xfmr

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, state):
        phase_list = self.get_phase_list()
        for (pos_phase_1, _, pos_phase_2, _) in phase_list:
            xfmr = self.xfmrs[(pos_phase_1, pos_phase_2)]
            xfmr.stamp_primal(Y, J, v_previous, tx_factor, state)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, state):
        phase_list = self.get_phase_list()
        for (pos_phase_1, _, pos_phase_2, _) in phase_list:
            xfmr = self.xfmrs[(pos_phase_1, pos_phase_2)]
            xfmr.stamp_dual(Y, J, v_previous, tx_factor, state)

    def calculate_residuals(self, state, v):
        residuals = defaultdict(lambda: 0)
        phase_list = self.get_phase_list()

        for (pos_phase_1, _, pos_phase_2, _) in phase_list:
            xfmr = self.xfmrs[(pos_phase_1, pos_phase_2)]
            for (key, value) in xfmr.calculate_residuals(state, v).items():
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

