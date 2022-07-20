import cmath
import os
from itertools import count
import math
import numpy as np
from logic.networkmodel import DxNetworkModel

from ditto.readers.gridlabd.read import Reader
from ditto.store import Store
import ditto.models.load
from logic.powerflowsettings import PowerFlowSettings
from models.shared.L2infeasibility import L2InfeasibilityCurrent
from models.threephase.capacitor import Capacitor
from models.shared.slack import Slack

from models.shared.pqload import PQLoad
from models.shared.bus import GROUND, Bus
from models.threephase.three_phase_transformer import ThreePhaseTransformer
from models.threephase.center_tap_transformer import CenterTapTransformer
from models.threephase.center_tap_transformer_coil import CenterTapTransformerCoil
from models.threephase.transmission_line import TransmissionLine
from models.threephase.transmission_line_triplex import TriplexTransmissionLine
from models.threephase.primary_transformer_coil import PrimaryTransformerCoil
from models.threephase.secondary_transformer_coil import SecondaryTransformerCoil
from models.threephase.fuse import Fuse
from models.threephase.fuse_phase import FusePhase

from models.threephase.resistive_load import ResistiveLoad
from models.threephase.resistive_phase_load import ResistivePhaseLoad
from models.threephase.switch import Switch
from models.threephase.switch_phase import SwitchPhase
from models.threephase.regulator import Regulator
from models.threephase.regulator_phase import RegulatorPhase
from models.threephase.transmission_line_phase import TransmissionLinePhase

class ThreePhaseParser:
    # Angles in degrees associated with different phases
    _phase_to_degrees = {'A': 0, 'B': 240, 'C': 120, '1': 0, '2': 90}

    # Angles in radians associated with different phases
    _phase_to_radians = {'A': 0, 'B': 4*math.pi/3, 'C': 2*math.pi/3, '1': 0, '2': math.pi}

    _phase_to_angle = _phase_to_radians

    def __init__(self, input_file, settings: PowerFlowSettings, optimization_enabled: bool):
        self.input_file_path = os.path.abspath(input_file)
        self.settings = settings
        self.optimization_enabled = optimization_enabled

    def parse(self):
        self._bus_index = count(0)
        
        self.ditto_store = Store()
        gld_reader = Reader(input_file = self.input_file_path)

        # Parse the file and keep the grid_data_objects in the Store
        gld_reader.parse(self.ditto_store)
        self.all_gld_objects = gld_reader.all_gld_objects

        # Create a SimulationState object to populate and return
        simulation_state = DxNetworkModel()

        self.create_buses(simulation_state)

        self.create_loads(simulation_state)
        self.create_transformers(simulation_state)
        self.create_capacitors(simulation_state)
        self.create_regulators(simulation_state)
        # TODO add and call methods to create other objects


        self.create_transmission_lines(simulation_state)

        if self.settings.infeasibility_analysis:
            self.setup_infeasibility(simulation_state)

        return simulation_state
    
    # GridlabD buses default to being "PQ" constant power buses (aka loads)
    # They could also be "PV" voltage-controlled magnitude buses (aka generators)
    def create_buses(self, simulation_state: DxNetworkModel):
        for model in self.ditto_store.models:

            if isinstance(model, ditto.models.node.Node) or isinstance(model, ditto.models.power_source.PowerSource):
                isSlack = False
                if isinstance(model, ditto.models.power_source.PowerSource) or (hasattr(model, "bustype") and model._bustype == "SWING"):
                    isSlack = True

                for phase in model.phases:
                    if phase.default_value in self._phase_to_angle:
                        if hasattr(model, "parent"):
                            #For now, just map any child nodes back to their parent.
                            bus = simulation_state.bus_name_map[model.parent + "_" + phase.default_value]
                            simulation_state.bus_name_map[model.name + "_" + phase.default_value] = bus
                        elif hasattr(model, "_connecting_element"):
                            bus = simulation_state.bus_name_map[model._connecting_element + "_" + phase]
                        else:
                            try:
                                voltage = getattr(model, "voltage_" + phase.default_value)
                                v_mag = abs(voltage)
                                v_ang = cmath.phase(voltage)
                            except:
                                v_mag = model.nominal_voltage
                                v_ang = self._phase_to_angle[phase.default_value]

                            bus = self.create_bus(simulation_state, v_mag, v_ang, model.name, phase.default_value)
                            simulation_state.buses.append(bus)

                        if isSlack:
                            # Create this phase of the slack bus
                            slack = Slack(bus, v_mag, v_ang, 0, 0)
                            simulation_state.slack.append(slack)
        
        #Match index assignment for the old anoeds codebase.
        for slack in simulation_state.slack:
            slack.assign_nodes(simulation_state.next_var_idx, self.optimization_enabled)

    def create_bus(self, simulation_state, v_mag, v_ang, node_name, node_phase):
        bus_id = next(self._bus_index)
        bus = Bus(bus_id, 1, v_mag, v_ang, None, node_name, node_phase)
        bus.assign_nodes(simulation_state.next_var_idx, self.optimization_enabled)
        simulation_state.bus_name_map[node_name + "_" + node_phase] = bus
        return bus            

    def create_loads(self, simulation_state: DxNetworkModel):
        # Go through the ditto store for each load object
        for model in self.ditto_store.models:
            if isinstance(model, ditto.models.load.Load):
                if any(phaseload.model == 2 for phaseload in model.phase_loads):
                    # Model a simple Resistive load
                    resistive_load = ResistiveLoad()
                    # Loop through each phase associated with this load
                    for phase_load in model.phase_loads:
                        if (not hasattr(phase_load, "z") or phase_load.z == 0):
                            continue

                        # Get the existing bus id for each phase load of this PQ load
                        bus_id = simulation_state.bus_name_map[model.connecting_element + "_" + phase_load.phase]

                        # Get the initial voltage values for this 
                        try:
                            v_complex = complex(getattr(self.all_gld_objects[model.connecting_element],'_voltage_' + phase_load.phase))
                            v_r = v_complex.real
                            v_i = v_complex.imag
                        except Exception:
                            nominal_v = float(getattr(self.all_gld_objects[model.connecting_element],'_nominal_voltage'))
                            v_angle = self._phase_to_angle[phase_load.phase]
                            v_r = nominal_v * math.cos(v_angle)
                            v_i = nominal_v * math.sin(v_angle)
                            v_complex = complex(v_r,v_i)
                        
                        # Get relevant attributes, create and save an object
                        resistive_load.phase_loads.append(ResistivePhaseLoad(v_r, v_i, phase_load.z, phase_load.phase, bus_id))
                    simulation_state.loads.append(resistive_load)
                elif any(phaseload.model == 1 for phaseload in model.phase_loads): #model.bustype == "PQ":
                    # Loop through each phase associated with this load
                    for phase_load in model.phase_loads:
                        if (not hasattr(phase_load, "p") or not hasattr(phase_load, "q") or (phase_load.p == 0 and phase_load.q == 0)):
                            continue

                        # Get the existing bus id for each phase load of this PQ load
                        if hasattr(model, "connecting_element"):
                            bus = simulation_state.bus_name_map[model.connecting_element + "_" + phase_load.phase]
                        elif hasattr(model, "_parent"):
                            bus = simulation_state.bus_name_map[model._parent + "_" + phase_load.phase]
                        else:
                            # Get relevant attributes, create and save an object
                            # Get the initial voltage values for this 
                            try:
                                v_complex = complex(getattr(self.all_gld_objects[model.name],'_voltage_' + phase_load.phase))
                            except Exception:
                                try:
                                    v_complex = complex(getattr(self.all_gld_objects[model.name],'_nominal_voltage'))
                                except Exception:
                                    try:
                                        v_complex = complex(getattr(self.all_gld_objects[model.connecting_element],'_voltage_' + phase_load.phase))
                                    except Exception:
                                        nominal_v = float(getattr(self.all_gld_objects[model.connecting_element],'_nominal_voltage'))
                                        v_angle = self._phase_to_angle[phase_load.phase]
                                        v_r = nominal_v * math.cos(v_angle)
                                        v_i = nominal_v * math.sin(v_angle)
                                        v_complex = complex(v_r,v_i)

                            
                            v_mag = abs(v_complex)
                            v_ang = cmath.phase(v_complex)

                            bus = self.create_bus(simulation_state, v_mag, v_ang, model.name, phase_load.phase)

                        phase_load = PQLoad(bus, phase_load.p, phase_load.q, 0, 0, 0, 0, None, None)
                        phase_load.assign_nodes(simulation_state.next_var_idx, self.optimization_enabled)
                        simulation_state.loads.append(phase_load)
                # TODO add cases for other types (ZIP, etc)
                
                    
    def create_transformers(self, simulation_state):
        # Go through the ditto store for each transformer object
        for model in self.ditto_store.models:
            if isinstance(model, ditto.models.powertransformer.PowerTransformer):
                if model.is_center_tap:
                    self.create_center_tap_transformer(model, simulation_state)
                elif len(model.windings) != 2:
                    raise Exception("Only 2 winding or center-tap transformers currently supported")
                else:
                    self.create_three_phase_transformer(model, simulation_state)

    def create_center_tap_transformer(self, model, simulation_state):
        phase = model.phases[0].default_value
        
        winding0 = model.windings[0]
        transformer_coil_0 = CenterTapTransformerCoil(winding0.nominal_voltage, winding0.rated_power, winding0.connection_type, winding0.voltage_limit, winding0.resistance, model.reactances[0])
        winding1 = model.windings[1]
        transformer_coil_1 = CenterTapTransformerCoil(winding1.nominal_voltage, winding1.rated_power, winding1.connection_type, winding1.voltage_limit, winding1.resistance, model.reactances[1])
        winding2 = model.windings[2]
        transformer_coil_2 = CenterTapTransformerCoil(winding2.nominal_voltage, winding2.rated_power, winding2.connection_type, winding2.voltage_limit, winding2.resistance, model.reactances[2])
        
        turn_ratio = winding0.nominal_voltage / winding1.nominal_voltage
        
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
        primary_bus = Bus()
        simulation_state.bus_name_map[model.name + "_primary_" + phase] = primary_bus.bus_id
        real_voltage_idx = simulation_state.next_var_idx.__next__()
        imag_voltage_idx = simulation_state.next_var_idx.__next__()
        simulation_state.bus_map[primary_bus.bus_id] = (real_voltage_idx, imag_voltage_idx)
        
        transformer_coil_0.primary_node = primary_bus.bus_id

        # Create a new bus on the first triplex coil, for KCL
        secondary1_bus = Bus()
        simulation_state.bus_name_map[model.name + "_sending_1"] = secondary1_bus.bus_id
        real_voltage_idx = simulation_state.next_var_idx.__next__()
        imag_voltage_idx = simulation_state.next_var_idx.__next__()
        simulation_state.bus_map[secondary1_bus.bus_id] = (real_voltage_idx, imag_voltage_idx)
        
        transformer_coil_1.sending_node = secondary1_bus.bus_id
        
        # Create a new variable for the voltage equations on the first triplex coil (not an actual node)
        real_voltage_idx = simulation_state.next_var_idx.__next__()
        imag_voltage_idx = simulation_state.next_var_idx.__next__()
        
        transformer_coil_1.real_voltage_idx = real_voltage_idx
        transformer_coil_1.imag_voltage_idx = imag_voltage_idx
        
        # Add the transformer's first from node to the first triplex coil
        to1_bus = simulation_state.bus_name_map[model.to_element + '_1']
        transformer_coil_1.to_node = to1_bus

        # Create a new bus on the second triplex coil, for KCL
        secondary2_bus = Bus()
        simulation_state.bus_name_map[model.name + "_sending_2"] = secondary2_bus.bus_id
        real_voltage_idx = simulation_state.next_var_idx.__next__()
        imag_voltage_idx = simulation_state.next_var_idx.__next__()
        simulation_state.bus_map[secondary2_bus.bus_id] = (real_voltage_idx, imag_voltage_idx)
        
        transformer_coil_2.sending_node = secondary2_bus.bus_id
        
        # Create a new variable for the voltage equations on the second triplex coil (not an actual node)
        real_voltage_idx = simulation_state.next_var_idx.__next__()
        imag_voltage_idx = simulation_state.next_var_idx.__next__()
        
        transformer_coil_2.real_voltage_idx = real_voltage_idx
        transformer_coil_2.imag_voltage_idx = imag_voltage_idx
        
        # Add the transformer's second from node to the second triplex coil
        to2_bus = simulation_state.bus_name_map[model.to_element + '_2']
        transformer_coil_2.to_node = to2_bus

        transformer = CenterTapTransformer(transformer_coil_0, transformer_coil_1, transformer_coil_2, phase, turn_ratio, model.power_ratings[0], g_shunt, b_shunt)
        
        simulation_state.transformers.append(transformer)
    
    def create_three_phase_transformer(self, model, simulation_state: DxNetworkModel):
        winding1 = model.windings[0]
        primary_transformer_coil = PrimaryTransformerCoil(winding1.nominal_voltage, winding1.rated_power, winding1.connection_type, winding1.voltage_limit)
        winding2 = model.windings[1]
        secondary_transformer_coil = SecondaryTransformerCoil(winding2.nominal_voltage, winding2.rated_power, winding2.connection_type, winding2.voltage_limit, winding2.resistance * 2, sum(model.reactances))

        turn_ratio = winding1.nominal_voltage / winding2.nominal_voltage

        # Assume the same set of phases on primary and secondary windings
        phases = []
        for phase_winding in winding1.phase_windings:
            phases.append(phase_winding.phase)
            
            from_bus = simulation_state.bus_name_map[model.from_element + '_' + phase_winding.phase]
            primary_transformer_coil.phase_connections[phase_winding.phase] = from_bus

            to_bus = simulation_state.bus_name_map[model.to_element + '_' + phase_winding.phase]
            secondary_transformer_coil.phase_connections[phase_winding.phase] = to_bus

        phase_shift = 0 if model.phase_shift is None else model.phase_shift # TODO is this in degrees or radians
        if hasattr(model, "shunt_impedance") and model.shunt_impedance != 0:
            shunt_impedance = (model.shunt_impedance * (secondary_transformer_coil.nominal_voltage ** 2))  / (secondary_transformer_coil.rated_power)
            r_shunt, x_shunt = shunt_impedance.real, shunt_impedance.imag
            g_shunt = r_shunt / (r_shunt ** 2 + x_shunt ** 2)
            b_shunt = -x_shunt / (r_shunt ** 2 + x_shunt ** 2)
        else:
            g_shunt = 0
            b_shunt = 0
        transformer = ThreePhaseTransformer(
            primary_transformer_coil, 
            secondary_transformer_coil, 
            phases, 
            turn_ratio, 
            phase_shift, 
            g_shunt, 
            b_shunt, 
            self.optimization_enabled,
            simulation_state.next_var_idx
            )
        simulation_state.transformers.append(transformer)
    
    def create_capacitors(self, simulation_state: DxNetworkModel):
        for model in self.ditto_store.models:
            if isinstance(model, ditto.models.capacitor.Capacitor):
                gld_cap = self.all_gld_objects[model.name]
                for phase_capacitor in model.phase_capacitors:
                    parent_bus = simulation_state.bus_name_map[gld_cap._parent + '_' + phase_capacitor.phase]
                    capacitor = Capacitor(parent_bus, GROUND, phase_capacitor.var, model.nominal_voltage, model.high, model.low)
                    capacitor.assign_nodes(simulation_state.next_var_idx, self.optimization_enabled)
                    simulation_state.capacitors.append(capacitor)

    def create_regulators(self, simulation_state):
        for model in self.ditto_store.models:
            if isinstance(model, ditto.models.regulator.Regulator):
                if len(model.windings) != 2:
                    raise Exception("Only 2 windings currently supported")
                if not (len(model.windings[0].phase_windings) == len(model.windings[1].phase_windings) == 3):
                    raise Exception("Only 3-phase currently supported")
                if not (model.windings[0].connection_type == model.windings[1].connection_type == 'Y'):
                    # gridlabD only supports a Wye-Wye connected regulator as of Jan 20 2022, so do we
                    raise Exception("Only wye-wye currently supported")
                
                ar_step = (model.regulation * 2) / (model.highstep + model.lowstep)
                reg_type = model.type if hasattr(model, "type") else "B"
                regulator = Regulator('ABC', ar_step, reg_type)
                for phase in regulator.phases:
                    from_bus = simulation_state.bus_name_map[model.high_from + '_' + phase]
                    to_bus = simulation_state.bus_name_map[model.low_to + '_' + phase]

                    # Create a new variable for the voltage equations on the primary coil (not an actual node)
                    real_voltage_idx = simulation_state.next_var_idx.__next__()
                    imag_voltage_idx = simulation_state.next_var_idx.__next__()

                    # Create a new bus on the secondary coil, for KCL
                    secondary_bus = self.create_bus(simulation_state, 0, 0, model.name + "_secondary", phase)

                    tap_position = float(getattr(self.all_gld_objects[self.all_gld_objects[model.name]['configuration']],'_tap_pos_' + phase))
                                      
                    single_regulator_phase = RegulatorPhase(from_bus, real_voltage_idx, imag_voltage_idx, secondary_bus, to_bus, phase, tap_position)
                    regulator.regulator_phases.append(single_regulator_phase)
                simulation_state.regulators.append(regulator)
    
    def create_transmission_lines(self, simulation_state):
        # Go through the ditto store for each line object
        for model in self.ditto_store.models:
            if isinstance(model, ditto.models.line.Line):
                # Check for fuses, some are encoded as zero-length lines with no features
                if model.is_fuse:
                    fuse = Fuse("CLOSED")
                    for wire in model.wires:
                        from_bus = simulation_state.bus_name_map[model.from_element + "_" + wire.phase]
                        to_bus = simulation_state.bus_name_map[model.to_element + "_" + wire.phase]
                        current_limit = float(model._current_limit)
                        phase_status = getattr(model, "phase_" + wire.phase + "_status") if hasattr(model, "phase_" + wire.phase + "_status") else "GOOD"
                        phase_fuse = FusePhase(from_bus, to_bus, current_limit, phase_status, wire.phase)#, real_voltage_idx, imag_voltage_idx)
                        fuse.phase_fuses.append(phase_fuse)
                    simulation_state.fuses.append(fuse)
                    continue
                # Check for switches, some are encoded as 1-length lines with no features
                elif model.is_switch:
                    switch = Switch("CLOSED")
                    for wire in model.wires:
                        from_bus = simulation_state.bus_name_map[model.from_element + "_" + wire.phase]
                        to_bus = simulation_state.bus_name_map[model.to_element + "_" + wire.phase]
                        phase_switch = SwitchPhase(from_bus, to_bus, ("OPEN" if (hasattr(wire, "is_open") and wire.is_open) else "CLOSED"), wire.phase)#, real_voltage_idx, imag_voltage_idx)
                        switch.phase_switches.append(phase_switch)
                    simulation_state.switches.append(switch)
                    continue
                else:
                    impedances = np.array(model.impedance_matrix)
                    # if model.line_type == 'underground':
                    #     # Calculate shunt admittance
                    #     # Note: this assumes symmetrical spacing between lines. TODO update if testing with systems where this is not the case
                    #     # Note: this assumes an insulation material such as cross-linked polyethylene
                    #     # Note: this assumes all wires are identical
                    #     # See Kersting 2007 Section 5.4 for the derivation of the following equation
                    #     wire = model.wires[0]
                    #     R_b = (wire.outer_diameter - wire.conductor_diameter) / 2 # in inches # not concentric_neutral_diameter in denom?
                    #     conductor_radius = wire.conductor_diameter / 2 # in inches 
                    #     neutral_radius = wire.concentric_neutral_diameter / 2 # in inches 
                    #     k = wire.concentric_neutral_nstrand
                    #     y = complex(0,77.3619*1e-6/(math.log(R_b / conductor_radius)))# not - 1/k*math.log(k*neutral_radius/R_b))) # Siemens of admittance per mile
                    #     y = y / 1609.34 # per meter
                    #     shunt_admittances = [[0]*3 for i in range(3)]
                    #     for i in range(3):
                    #         shunt_admittances[i][i] = y
                    # else:
                    shunt_admittances = model.capacitance_matrix

                    phases = [wire.phase for wire in model.wires if wire.phase != 'N']
                    
                    transmission_line = TransmissionLine(simulation_state, self.optimization_enabled, impedances, shunt_admittances, model.from_element, model.to_element, model.length, phases)
                    simulation_state.transmission_lines.append(transmission_line)


    def setup_infeasibility(self, simulation_state: DxNetworkModel):
        for bus in simulation_state.buses:
            current = L2InfeasibilityCurrent(bus)
            current.assign_nodes(simulation_state.next_var_idx, self.optimization_enabled)
            simulation_state.infeasibility_currents.append(current)


if __name__ == "__main__":
    print("starting script")
    glm_file_path = "test/data/ieee_4_node/node.glm"
    test_parser = ThreePhaseParser(glm_file_path)
    returned_generators = test_parser.parse()
    print(returned_generators)
    