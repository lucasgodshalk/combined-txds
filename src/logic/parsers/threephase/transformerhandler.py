import math
import typing
from logic.networkmodel import DxNetworkModel
from models.shared.bus import Bus, GROUND
from models.shared.transformer import Transformer
from models.threephase.center_tap_transformer import CenterTapTransformer
from models.threephase.center_tap_transformer_coil import CenterTapTransformerCoil
from models.threephase.primary_transformer_coil import PrimaryTransformerCoil
from models.threephase.secondary_transformer_coil import SecondaryTransformerCoil
from ditto.models.powertransformer import PowerTransformer

NEUTRAL = "N"

CONNECTION_TYPE_WYE = "Y"
CONNECTION_TYPE_DELTA = "D"
CONNECTION_TYPE_GWYE = None

class TransformerHandler:
    def __init__(self, parser) -> None:
        self.parser = parser

    def create_transformers(self, ditto_store, simulation_state: DxNetworkModel):
        # Go through the ditto store for each transformer object
        for model in ditto_store.models:
            if isinstance(model, PowerTransformer):
                if model.is_center_tap:
                    self.create_center_tap_transformer(model, simulation_state)
                elif len(model.windings) != 2:
                    raise Exception("Only 2 winding or center-tap transformers currently supported")
                else:
                    self.create_three_phase_transformer(model, simulation_state)

    def create_center_tap_transformer(self, model, simulation_state: DxNetworkModel):
        phase = model.phases[0].default_value
        
        winding0 = model.windings[0]
        transformer_coil_0 = CenterTapTransformerCoil(winding0.nominal_voltage, winding0.rated_power, winding0.connection_type, winding0.voltage_limit, winding0.resistance, model.reactances[0])
        winding1 = model.windings[1]
        transformer_coil_1 = CenterTapTransformerCoil(winding1.nominal_voltage, winding1.rated_power, winding1.connection_type, winding1.voltage_limit, winding1.resistance, model.reactances[1])
        winding2 = model.windings[2]
        transformer_coil_2 = CenterTapTransformerCoil(winding2.nominal_voltage, winding2.rated_power, winding2.connection_type, winding2.voltage_limit, winding2.resistance, model.reactances[2])
        
        turn_ratio = winding0.nominal_voltage / (winding1.nominal_voltage)
        
        if hasattr(model, "shunt_impedance") and model.shunt_impedance != 0:
            shunt_impedance = model.shunt_impedance
            r_shunt, x_shunt = shunt_impedance.real, shunt_impedance.imag
            r_shunt = (r_shunt  * (transformer_coil_0.nominal_voltage ** 2))  / (transformer_coil_2.rated_power)
            x_shunt = (x_shunt * (transformer_coil_0.nominal_voltage ** 2))  / (transformer_coil_2.rated_power)
            g_shunt = r_shunt / (r_shunt ** 2 + x_shunt ** 2)
            b_shunt = -x_shunt / (r_shunt ** 2 + x_shunt ** 2)
        else:
            g_shunt = 0
            b_shunt = 0
        
        # Add the transformer's from bus to the primary coil
        from_bus = simulation_state.bus_name_map[model.from_element + '_' + phase]
        transformer_coil_0.from_node = from_bus

        # Create a new bus on the primary coil, for KCL
        primary_bus = self.parser.create_bus(simulation_state, 0.1, 0.1, model.name + "_primary", phase, True)
        
        transformer_coil_0.primary_node = primary_bus

        # Create a new bus on the first triplex coil, for KCL
        secondary1_bus = self.parser.create_bus(simulation_state, 0.1, 0.1, model.name + "_sending_1", phase, True)
        
        transformer_coil_1.sending_node = secondary1_bus
        
        # Add the transformer's first from node to the first triplex coil
        to1_bus = simulation_state.bus_name_map[model.to_element + '_1']
        transformer_coil_1.to_node = to1_bus

        # Create a new bus on the second triplex coil, for KCL
        secondary2_bus = self.parser.create_bus(simulation_state, 0.1, 0.1, model.name + "_sending_2", phase, True)
        
        transformer_coil_2.sending_node = secondary2_bus
        
        # Add the transformer's second from node to the second triplex coil
        to2_bus = simulation_state.bus_name_map[model.to_element + '_2']
        transformer_coil_2.to_node = to2_bus

        transformer = CenterTapTransformer(transformer_coil_0, transformer_coil_1, transformer_coil_2, phase, turn_ratio, winding0.rated_power, g_shunt, b_shunt)

        simulation_state.transformers.append(transformer)

    def create_three_phase_transformer(self, model, simulation_state: DxNetworkModel):
        winding1 = model.windings[0]
        primary_coil = PrimaryTransformerCoil(winding1.nominal_voltage, winding1.rated_power, winding1.connection_type, winding1.voltage_limit)
        winding2 = model.windings[1]
        secondary_coil = SecondaryTransformerCoil(winding2.nominal_voltage, winding2.rated_power, winding2.connection_type, winding2.voltage_limit, winding2.resistance * 2, sum(model.reactances))

        if primary_coil.connection_type == "D":
            nominal_voltage_primary = primary_coil.nominal_voltage * math.sqrt(3)
        else:
            nominal_voltage_primary = primary_coil.nominal_voltage
        if secondary_coil.connection_type == "D": 
            nominal_voltage_secondary = secondary_coil.nominal_voltage * math.sqrt(3)
        else:
            nominal_voltage_secondary = secondary_coil.nominal_voltage

        turn_ratio = nominal_voltage_primary / nominal_voltage_secondary

        # Assume the same set of phases on primary and secondary windings
        phases = []
        for phase_winding in winding1.phase_windings:
            phases.append(phase_winding.phase)
            
            from_bus = simulation_state.bus_name_map[model.from_element + '_' + phase_winding.phase]
            primary_coil.phase_connections[phase_winding.phase] = from_bus

            to_bus = simulation_state.bus_name_map[model.to_element + '_' + phase_winding.phase]
            secondary_coil.phase_connections[phase_winding.phase] = to_bus

        phase_shift = 0 if model.phase_shift is None else model.phase_shift # TODO is this in degrees or radians
        if hasattr(model, "shunt_impedance") and model.shunt_impedance != 0:
            shunt_impedance = (model.shunt_impedance * (nominal_voltage_secondary ** 2))  / (secondary_coil.rated_power)
            r_shunt, x_shunt = shunt_impedance.real, shunt_impedance.imag
            g_shunt = r_shunt / (r_shunt ** 2 + x_shunt ** 2)
            b_shunt = -x_shunt / (r_shunt ** 2 + x_shunt ** 2)
        else:
            g_shunt = 0
            b_shunt = 0

        phase_list = get_phase_list(primary_coil, secondary_coil, phases)

        for (pos_phase_1, neg_phase_1, pos_phase_2, neg_phase_2) in phase_list:
            from_bus_pos = primary_coil.phase_connections[pos_phase_1]
            if neg_phase_1 == NEUTRAL:
                #Todo: grounded vs ungrounded wye.
                from_bus_neg = GROUND 
            else:
                from_bus_neg = primary_coil.phase_connections[neg_phase_1]
            to_bus_pos = secondary_coil.phase_connections[pos_phase_2]
            if neg_phase_2 == NEUTRAL:
                #Todo: grounded vs ungrounded wye.
                to_bus_neg = GROUND 
            else:
                to_bus_neg = secondary_coil.phase_connections[neg_phase_2]

            # Values for the secondary coil stamps, converted out of per-unit
            r = secondary_coil.resistance * nominal_voltage_secondary ** 2  / secondary_coil.rated_power
            x = secondary_coil.reactance * nominal_voltage_secondary ** 2  / secondary_coil.rated_power

            xfmr = Transformer(
                from_bus_pos, 
                from_bus_neg, 
                to_bus_pos, 
                to_bus_neg, 
                r, 
                x, 
                True, 
                turn_ratio,
                phase_shift, 
                g_shunt,
                b_shunt,
                None
                )
            
            simulation_state.transformers.append(xfmr)

def get_phase_list(primary_coil, secondary_coil, phases):
    rotated_phases = phases[1:] + phases[:1]
    phase_list: typing.List[str]
    phase_list = list.copy(phases)
    if primary_coil.connection_type == "D":
        for i in range(len(phase_list)):
            phase_list[i] += rotated_phases[i]
    else:
        for i in range(len(phase_list)):
            phase_list[i] += NEUTRAL
            
    for i in range(len(phase_list)):
        phase_list[i] += phases[i]

    if secondary_coil.connection_type == "D":
        for i in range(len(phase_list)):
            phase_list[i] += rotated_phases[i]
    else:
        for i in range(len(phase_list)):
            phase_list[i] += NEUTRAL
    return phase_list