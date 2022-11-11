import cmath
import os
from itertools import count
import math
import numpy as np
from logic.network.networkmodel import DxNetworkModel

from ditto.readers.gridlabd.read import Reader
from ditto.store import Store
import ditto.models.load
from logic.network.parsers.threephase.transformerparser import TransformerParser
from logic.powerflowsettings import PowerFlowSettings
from models.singlephase.capacitor import Capacitor, CapacitorMode, CapSwitchState
from models.singlephase.slack import Slack

from models.singlephase.load import Load
from models.singlephase.bus import GROUND, Bus
from models.threephase.unbalanced_line import UnbalancedLine
from models.singlephase.fuse import Fuse, FuseStatus
from models.singlephase.fuse import Fuse

from models.singlephase.switch import Switch, SwitchStatus
from models.singlephase.switch import Switch
from models.singlephase.regulator import RegControl, RegType, Regulator

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
        network_model = DxNetworkModel()
        transformerhandler = TransformerParser(self)

        self.create_buses(network_model)
        
        for model in self.ditto_store.models:
            if isinstance(model, ditto.models.powertransformer.PowerTransformer):
                transformerhandler.create_transformer(model, network_model)
            elif isinstance(model, ditto.models.capacitor.Capacitor):
                self.create_capacitor(model, network_model)
            elif isinstance(model, ditto.models.regulator.Regulator):
                self.create_regulator(model, network_model)
            elif isinstance(model, ditto.models.line.Line):
                self.create_transmission_line(model, network_model)
            elif isinstance(model, ditto.models.load.Load):
                self.create_load(model, network_model)
            elif self.ignoremodel(model):
                continue
            else:
                raise Exception(f"Unknown model type {model}")

        return network_model
    
    def ignoremodel(self, model):
        ignored_models = [
            ditto.models.winding.Winding,
            ditto.models.phase_winding.PhaseWinding,
            ditto.models.phase_capacitor.PhaseCapacitor,
            ditto.models.wire.Wire,
            ditto.models.phase_load.PhaseLoad,
            ditto.models.node.Node,
            ditto.models.power_source.PowerSource
        ]

        for ignored_model in ignored_models:
            if isinstance(model, ignored_model):
                return True

        return False

    # GridlabD buses default to being "PQ" constant power buses (aka loads)
    # They could also be "PV" voltage-controlled magnitude buses (aka generators)
    def create_buses(self, network_model: DxNetworkModel):
        for model in self.ditto_store.models:

            if isinstance(model, ditto.models.node.Node) or isinstance(model, ditto.models.power_source.PowerSource):
                isSlack = False
                if isinstance(model, ditto.models.power_source.PowerSource) or (hasattr(model, "bustype") and model._bustype == "SWING"):
                    isSlack = True

                for phase in model.phases:
                    if phase.default_value in self._phase_to_angle:
                        if hasattr(model, "parent"):
                            #For now, just map any child nodes back to their parent.
                            bus = network_model.bus_name_map[model.parent + "_" + phase.default_value]
                            network_model.bus_name_map[model.name + "_" + phase.default_value] = bus
                        elif hasattr(model, "_connecting_element"):
                            bus = network_model.bus_name_map[model._connecting_element + "_" + phase]
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

                            bus = self.create_bus(network_model, v_mag, v_ang, model.name, phase.default_value, False)

                            if phase.default_value == "1":
                                bus.Vr_init = -60.0
                                bus.Vi_init = 103.92
                            elif phase.default_value == "2":
                                bus.Vr_init = 60.0
                                bus.Vi_init = -103.92

                        if isSlack:
                            # Create this phase of the slack bus
                            slack = Slack(bus, v_mag, v_ang, 0, 0)
                            network_model.slack.append(slack)

    def create_bus(self, network_model, v_mag, v_ang, node_name, node_phase, is_virtual):
        bus_id = next(self._bus_index)
        bus = Bus(bus_id, 1, v_mag, v_ang, None, node_name, node_phase, is_virtual)
        network_model.bus_name_map[node_name + "_" + node_phase] = bus
        network_model.buses.append(bus)
        return bus            

    def create_load(self, model, network_model: DxNetworkModel):
        load_num = model.name.split("_")[-1]
        triplex_phase = model.triplex_phase
        for phase_load in model.phase_loads:
            from_bus = self.get_load_connection(model, network_model, phase_load.phase[0])

            if len(phase_load.phase) == 1:
                to_bus = GROUND
            else:
                to_bus = self.get_load_connection(model, network_model, phase_load.phase[1])

            ip = phase_load.i_const.real
            iq = phase_load.i_const.imag

            pq_load = Load(from_bus, to_bus, phase_load.p, phase_load.q, phase_load.z, ip, iq, load_num, phase_load.phase, triplex_phase)
            network_model.loads.append(pq_load)

    def get_load_connection(self, model, network_model, phase):
        # Get the existing bus id for each phase load of this PQ load
        if hasattr(model, "connecting_element"):
            bus = network_model.bus_name_map[model.connecting_element + "_" + phase]
        elif hasattr(model, "_parent"):
            bus = network_model.bus_name_map[model._parent + "_" + phase]
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

                        bus = self.create_bus(network_model, v_mag, v_ang, model.name, phase, False)

        return bus


    def create_capacitor(self, model: ditto.models.capacitor.Capacitor, network_model: DxNetworkModel):
        gld_cap = self.all_gld_objects[model.name]
        for phase_capacitor in model.phase_capacitors:
            if not phase_capacitor.phase in model.connected_phases:
                continue

            mode = CapacitorMode[gld_cap._control]
            if mode == CapacitorMode.VOLT and (model.high == None or model.low == None):
                #https://github.com/gridlab-d/gridlab-d/blob/9f0a09853280bb3515f8236b8af3192304759650/powerflow/capacitor.cpp#L320-L325
                mode = CapacitorMode.MANUAL

            parent_bus = network_model.bus_name_map[gld_cap._parent + '_' + phase_capacitor.phase]
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
            
            network_model.capacitors.append(capacitor)

    def create_regulator(self, model: ditto.models.regulator.Regulator, network_model: DxNetworkModel):
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
            from_bus = network_model.bus_name_map[model.high_from + '_' + winding.phase]
            to_bus = network_model.bus_name_map[model.low_to + '_' + winding.phase]

            tap_position = int(getattr(reg_config, '_tap_pos_' + winding.phase))

            current_bus = self.create_bus(network_model, 0.1, 0.1, f"{from_bus.NodeName}-Reg", winding.phase, True)

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

            network_model.regulators.append(regulator)
    
    def create_transmission_line(self, model: ditto.models.line.Line, network_model: DxNetworkModel):
        # Check for fuses, some are encoded as zero-length lines with no features
        if model.is_fuse:
            for wire in model.wires:
                from_bus = network_model.bus_name_map[model.from_element + "_" + wire.phase]
                to_bus = network_model.bus_name_map[model.to_element + "_" + wire.phase]

                current_limit = float(model._current_limit)

                fuse_status = FuseStatus.GOOD
                if hasattr(model, "phase_" + wire.phase + "_status"):
                    fuse_status = FuseStatus[getattr(model, "phase_" + wire.phase + "_status")]

                fuse_bus = self.create_bus(network_model, 0.1, 0.1, f"{from_bus.NodeName}-Fuse", wire.phase, True)

                fuse = Fuse(from_bus, to_bus, fuse_bus, current_limit, fuse_status, wire.phase)

                network_model.fuses.append(fuse)
        # Check for switches, some are encoded as 1-length lines with no features
        elif model.is_switch:
            for wire in model.wires:
                if not wire.phase in model.phases:
                    continue

                from_bus = network_model.bus_name_map[model.from_element + "_" + wire.phase]
                to_bus = network_model.bus_name_map[model.to_element + "_" + wire.phase]

                status = SwitchStatus[("OPEN" if (hasattr(wire, "is_open") and wire.is_open) else "CLOSED")]

                switch = Switch(from_bus, to_bus, status, wire.phase)
                
                network_model.switches.append(switch)
        else:
            impedances = np.array(model.impedance_matrix)

            if self.settings.enable_line_capacitance:
                shunt_admittances = model.capacitance_matrix
            else:
                shunt_admittances = None

            phases = [wire.phase for wire in model.wires if wire.phase != 'N']
            
            transmission_line = UnbalancedLine(network_model, impedances, shunt_admittances, model.from_element, model.to_element, model.length, phases)
            network_model.lines.append(transmission_line)

