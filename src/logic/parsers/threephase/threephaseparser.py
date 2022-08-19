import cmath
import os
from itertools import count
import math
import numpy as np
from logic.networkmodel import DxNetworkModel

from ditto.readers.gridlabd.read import Reader
from ditto.store import Store
import ditto.models.load
from logic.parsers.threephase.transformerparser import TransformerParser
from logic.powerflowsettings import PowerFlowSettings
from models.shared.L2infeasibility import L2InfeasibilityCurrent
from models.threephase.capacitor import Capacitor, CapacitorMode, CapSwitchState
from models.shared.slack import Slack

from models.shared.load import Load
from models.shared.bus import GROUND, Bus
from models.threephase.transmission_line import TransmissionLine
from models.threephase.fuse import Fuse, FuseStatus
from models.threephase.fuse import Fuse

from models.shared.switch import Switch, SwitchStatus
from models.shared.switch import Switch
from models.threephase.regulator import RegControl, RegType, Regulator

class ThreePhaseParser:
    def rad(degrees):
        return math.radians(degrees)

    # Angles in radians associated with different phases
    _phase_to_angle = {'A': rad(0), 'B': rad(240), 'C': rad(120), '1': rad(0), '2': rad(180)}

    def __init__(self, input_file, settings: PowerFlowSettings):
        self.input_file_path = os.path.abspath(input_file)
        self.settings = settings

    def parse(self):
        self._bus_index = count(0)
        
        self.ditto_store = Store()
        gld_reader = Reader(input_file = self.input_file_path)

        # Parse the file and keep the grid_data_objects in the Store
        gld_reader.parse(self.ditto_store)
        self.all_gld_objects = gld_reader.all_gld_objects

        # Create a SimulationState object to populate and return
        simulation_state = DxNetworkModel()
        transformerhandler = TransformerParser(self)

        self.create_buses(simulation_state)
        
        self.create_loads(simulation_state)

        for model in self.ditto_store.models:
            if isinstance(model, ditto.models.powertransformer.PowerTransformer):
                transformerhandler.create_transformer(model, simulation_state)
            if isinstance(model, ditto.models.capacitor.Capacitor):
                self.create_capacitor(model, simulation_state)
            if isinstance(model, ditto.models.regulator.Regulator):
                self.create_regulator(model, simulation_state)
            if isinstance(model, ditto.models.line.Line):
                self.create_transmission_line(model, simulation_state)

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
                            v_mag = model.nominal_voltage
                            v_ang = self._phase_to_angle[phase.default_value]

                            try:
                                #For L1 and L2 on triplex, we always use the nominal magnitude and phase for v_init.
                                if not phase.default_value in ["1", "2"]:
                                    voltage = getattr(model, "voltage_" + phase.default_value)
                                    v_mag = abs(voltage)
                                    v_ang = cmath.phase(voltage)
                            except:
                                pass

                            bus = self.create_bus(simulation_state, v_mag, v_ang, model.name, phase.default_value, False)

                            if phase.default_value == "1":
                                bus.Vr_init = -60.0
                                bus.Vi_init = 103.92
                            elif phase.default_value == "2":
                                bus.Vr_init = 60.0
                                bus.Vi_init = -103.92

                        if isSlack:
                            # Create this phase of the slack bus
                            slack = Slack(bus, v_mag, v_ang, 0, 0)
                            simulation_state.slack.append(slack)

    def create_bus(self, simulation_state, v_mag, v_ang, node_name, node_phase, is_virtual):
        bus_id = next(self._bus_index)
        bus = Bus(bus_id, 1, v_mag, v_ang, None, node_name, node_phase, is_virtual)
        simulation_state.bus_name_map[node_name + "_" + node_phase] = bus
        simulation_state.buses.append(bus)
        return bus            

    def create_loads(self, simulation_state: DxNetworkModel):
        # Go through the ditto store for each load object
        for model in self.ditto_store.models:
            if isinstance(model, ditto.models.load.Load):
                for phase_load in model.phase_loads:
                    from_bus = self.get_load_connection(model, simulation_state, phase_load.phase[0])

                    if len(phase_load.phase) == 1:
                        to_bus = GROUND
                    else:
                        to_bus = self.get_load_connection(model, simulation_state, phase_load.phase[1])

                    if phase_load.model == 1 and phase_load.p == 0 and phase_load.q == 0:
                        continue
                    elif phase_load.model == 2 and phase_load.z == 0:
                        continue

                    pq_load = Load(from_bus, to_bus, phase_load.p, phase_load.q, phase_load.z, 0, 0, 0, 0)
                    simulation_state.loads.append(pq_load)
                    
                    load_name = self.get_load_name(model, phase_load)
                    simulation_state.load_name_map[load_name] = pq_load

    def get_load_connection(self, model, simulation_state, phase):
        # Get the existing bus id for each phase load of this PQ load
        if hasattr(model, "connecting_element"):
            bus = simulation_state.bus_name_map[model.connecting_element + "_" + phase]
        elif hasattr(model, "_parent"):
            bus = simulation_state.bus_name_map[model._parent + "_" + phase]
        else:
            # Get relevant attributes, create and save an object
            # Get the initial voltage values for this 
            try:
                v_complex = complex(getattr(self.all_gld_objects[model.name],'_voltage_' + phase))
            except Exception:
                try:
                    v_complex = complex(getattr(self.all_gld_objects[model.name],'_nominal_voltage'))
                except Exception:
                    try:
                        v_complex = complex(getattr(self.all_gld_objects[model.connecting_element],'_voltage_' + phase))
                    except Exception:
                        nominal_v = float(getattr(self.all_gld_objects[model.connecting_element],'_nominal_voltage'))
                        v_angle = self._phase_to_angle[phase]
                        v_r = nominal_v * math.cos(v_angle)
                        v_i = nominal_v * math.sin(v_angle)
                        v_complex = complex(v_r,v_i)
        
                        v_mag = abs(v_complex)
                        v_ang = cmath.phase(v_complex)

                        bus = self.create_bus(simulation_state, v_mag, v_ang, model.name, phase, False)

        return bus

    def get_load_name(self, model: ditto.models.load.Load, phase_load):
        load_num = model.name.split("_")[-1]
        if phase_load.phase.isalpha():
            load_name = f"cl_{load_num}{phase_load.phase}"
        elif phase_load.phase.isnumeric():
            load_name = f"rl_{load_num}_{phase_load.phase[0]}"
        else:
            load_name = f"{load_num}_{phase_load.phase}"
        return load_name


    def create_capacitor(self, model: ditto.models.capacitor.Capacitor, simulation_state: DxNetworkModel):
        gld_cap = self.all_gld_objects[model.name]
        for phase_capacitor in model.phase_capacitors:
            if not phase_capacitor.phase in model.connected_phases:
                continue

            mode = CapacitorMode[gld_cap._control]
            if mode == CapacitorMode.VOLT and (model.high == None or model.low == None):
                #https://github.com/gridlab-d/gridlab-d/blob/9f0a09853280bb3515f8236b8af3192304759650/powerflow/capacitor.cpp#L320-L325
                mode = CapacitorMode.MANUAL

            parent_bus = simulation_state.bus_name_map[gld_cap._parent + '_' + phase_capacitor.phase]
            nominal_voltage = float(gld_cap._cap_nominal_voltage) #Or could use model.nominal_voltage?
            voltage_angle = self._phase_to_angle[phase_capacitor.phase]
            v_r_nom = abs(nominal_voltage)*math.cos(voltage_angle)
            v_i_nom = abs(nominal_voltage)*math.sin(voltage_angle)
            parent_bus.Vr_init = v_r_nom
            parent_bus.Vi_init = v_i_nom
            capacitor = Capacitor(parent_bus, GROUND, phase_capacitor.var, nominal_voltage, mode, model.high, model.low)
            if mode == CapacitorMode.MANUAL:
                #Todo: implement ControlLevel

                #https://github.com/gridlab-d/gridlab-d/blob/9f0a09853280bb3515f8236b8af3192304759650/powerflow/capacitor.cpp#L116-L118
                #Gridlabd defaults to open.
                capacitor.switch = CapSwitchState.OPEN

                if phase_capacitor.phase == "A" and hasattr(gld_cap, "_switchA"):
                    capacitor.switch = CapSwitchState[gld_cap._switchA]
                elif phase_capacitor.phase == "B" and hasattr(gld_cap, "_switchB"):
                    capacitor.switch = CapSwitchState[gld_cap._switchB]
                elif phase_capacitor.phase == "C" and hasattr(gld_cap, "_switchC"):
                    capacitor.switch = CapSwitchState[gld_cap._switchC]
            
            simulation_state.capacitors.append(capacitor)

    def create_regulator(self, model: ditto.models.regulator.Regulator, simulation_state: DxNetworkModel):
        if len(model.windings) != 2:
            raise Exception("Only 2 windings currently supported")
        if not (len(model.windings[0].phase_windings) == len(model.windings[1].phase_windings) == 3):
            raise Exception("Only 3-phase currently supported")
        if not (model.windings[0].connection_type == model.windings[1].connection_type == 'Y'):
            # gridlabD only supports a Wye-Wye connected regulator as of Jan 20 2022, so do we
            raise Exception("Only wye-wye currently supported")
        
        reg_config = self.all_gld_objects[self.all_gld_objects[model.name]['configuration']]

        ar_step = (model.regulation * 2) / (model.highstep + model.lowstep)
        reg_type = RegType[model.type if hasattr(model, "type") else "B"]
        reg_control = RegControl[reg_config._Control]

        #https://github.com/gridlab-d/gridlab-d/blob/9f0a09853280bb3515f8236b8af3192304759650/powerflow/regulator.cpp#L251
        band_center = float(reg_config._band_center)
        band_width = float(reg_config._band_width)

        vlow = band_center - band_width / 2.0;
        vhigh = band_center + band_width / 2.0;

        raise_taps = int(reg_config._raise_taps)
        lower_taps = int(reg_config._lower_taps)

        tap_change_per = float(reg_config._regulation) / float(reg_config._raise_taps)
        v_tap_change = band_center * tap_change_per

        for winding in model.windings[0].phase_windings:
            from_bus = simulation_state.bus_name_map[model.high_from + '_' + winding.phase]
            to_bus = simulation_state.bus_name_map[model.low_to + '_' + winding.phase]

            tap_position = int(getattr(reg_config, '_tap_pos_' + winding.phase))

            current_bus = self.create_bus(simulation_state, 0.1, 0.1, f"{from_bus.NodeName}-Reg", winding.phase, True)

            regulator = Regulator(
                from_bus, 
                to_bus, 
                current_bus, 
                tap_position, 
                ar_step, 
                reg_type, 
                reg_control,
                vlow,
                vhigh,
                raise_taps,
                lower_taps
                )

            v_mag = abs(complex(to_bus.Vr_init, to_bus.Vi_init))

            tap_guess = math.ceil((band_center - v_mag)/v_tap_change)
            #regulator.try_increment_tap_position(tap_guess)

            simulation_state.regulators.append(regulator)
    
    def create_transmission_line(self, model: ditto.models.line.Line, simulation_state: DxNetworkModel):
        # Check for fuses, some are encoded as zero-length lines with no features
        if model.is_fuse:
            for wire in model.wires:
                from_bus = simulation_state.bus_name_map[model.from_element + "_" + wire.phase]
                to_bus = simulation_state.bus_name_map[model.to_element + "_" + wire.phase]

                current_limit = float(model._current_limit)

                fuse_status = FuseStatus.GOOD
                if hasattr(model, "phase_" + wire.phase + "_status"):
                    fuse_status = FuseStatus[getattr(model, "phase_" + wire.phase + "_status")]

                fuse_bus = self.create_bus(simulation_state, 0.1, 0.1, f"{from_bus.NodeName}-Fuse", wire.phase, True)

                fuse = Fuse(from_bus, to_bus, fuse_bus, current_limit, fuse_status, wire.phase)

                simulation_state.fuses.append(fuse)
        # Check for switches, some are encoded as 1-length lines with no features
        elif model.is_switch:
            for wire in model.wires:
                from_bus = simulation_state.bus_name_map[model.from_element + "_" + wire.phase]
                to_bus = simulation_state.bus_name_map[model.to_element + "_" + wire.phase]

                status = SwitchStatus[("OPEN" if (hasattr(wire, "is_open") and wire.is_open) else "CLOSED")]

                switch = Switch(from_bus, to_bus, status, wire.phase)
                
                simulation_state.switches.append(switch)
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
            
            transmission_line = TransmissionLine(simulation_state, impedances, shunt_admittances, model.from_element, model.to_element, model.length, phases)
            simulation_state.branches.append(transmission_line)

    def setup_infeasibility(self, simulation_state: DxNetworkModel):
        for bus in simulation_state.buses:
            current = L2InfeasibilityCurrent(bus)
            simulation_state.infeasibility_currents.append(current)


if __name__ == "__main__":
    print("starting script")
    glm_file_path = "test/data/ieee_4_node/node.glm"
    test_parser = ThreePhaseParser(glm_file_path)
    returned_generators = test_parser.parse()
    print(returned_generators)
    