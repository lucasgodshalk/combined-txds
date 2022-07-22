import cmath
import os
from itertools import count
import math
import numpy as np
from logic.networkmodel import DxNetworkModel

from ditto.readers.gridlabd.read import Reader
from ditto.store import Store
import ditto.models.load
from logic.parsers.threephase.transformerhandler import TransformerHandler
from logic.powerflowsettings import PowerFlowSettings
from models.shared.L2infeasibility import L2InfeasibilityCurrent
from models.threephase.capacitor import Capacitor
from models.shared.slack import Slack

from models.shared.pqload import PQLoad
from models.shared.bus import GROUND, Bus
from models.threephase.transmission_line import TransmissionLine
from models.threephase.fuse import Fuse
from models.threephase.fuse_phase import FusePhase

from models.threephase.resistive_load import ResistiveLoad
from models.threephase.resistive_phase_load import ResistivePhaseLoad
from models.threephase.switch import Switch
from models.threephase.switch_phase import SwitchPhase
from models.threephase.regulator import Regulator
from models.threephase.regulator_phase import RegulatorPhase

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
        transformerhandler = TransformerHandler(self.optimization_enabled, self)
        transformerhandler.create_transformers(self.ditto_store, simulation_state)
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
                
    def create_capacitors(self, simulation_state: DxNetworkModel):
        for model in self.ditto_store.models:
            if isinstance(model, ditto.models.capacitor.Capacitor):
                gld_cap = self.all_gld_objects[model.name]
                for phase_capacitor in model.phase_capacitors:
                    parent_bus = simulation_state.bus_name_map[gld_cap._parent + '_' + phase_capacitor.phase]
                    nominal_voltage = float(gld_cap._cap_nominal_voltage) #Or could use model.nominal_voltage?
                    voltage_angle = self._phase_to_angle[phase_capacitor.phase]
                    v_r_nom = abs(nominal_voltage)*math.cos(voltage_angle)
                    v_i_nom = abs(nominal_voltage)*math.sin(voltage_angle)
                    capacitor = Capacitor(parent_bus, GROUND, phase_capacitor.var, v_r_nom, v_i_nom, model.high, model.low)
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
                    simulation_state.branches.append(transmission_line)


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
    