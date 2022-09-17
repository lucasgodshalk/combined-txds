from builtins import super, range
from datetime import datetime
from datetime import timedelta
from croniter import croniter
import logging
import math
import re
import numpy as np
from ditto.models.node import Node
from ditto.models.power_source import PowerSource
from ditto.models.line import Line
from ditto.models.regulator import Regulator
from ditto.models.wire import Wire
from ditto.models.capacitor import Capacitor
from ditto.models.phase_capacitor import PhaseCapacitor
from ditto.models.powertransformer import PowerTransformer
from ditto.models.winding import Winding
from ditto.models.phase_winding import PhaseWinding
from ditto.formats.gridlabd import gridlabd
from ditto.formats.gridlabd import base
from ditto.models.base import Unicode
from ditto.readers.gridlabd.line_impedance import compute_overhead_impedance, compute_underground_impedance, compute_triplex_impedance, compute_overhead_spacing, compute_underground_spacing, try_load_direct_line_impedance, try_load_direct_line_capacitance, compute_underground_capacitance
from ditto.readers.gridlabd.load_parser import LoadParser
from ditto.readers.abstract_reader import AbstractReader
from ditto.readers.gridlabd.helpers import parse_phases, triplex_phases

logger = logging.getLogger(__name__)

remove_nonnum = re.compile(r'[^\d.]+')

meters_per_mile = 1609.344

#These objects we ignore entirely for the purpose of the simulator.
skipped_objects = [
    "house",
    "solar",
    "inverter",
    "waterheater",
    "climate",
    "ZIPload",
    "tape.recorder",
    "player",
    "tape.collector",
    "tape.group_recorder",
    "recorder",
    "voltdump",
    "currdump",
    "collector",
    "metrics",
    "eventgen",
    "fault_check",
    "power_metrics"
]

#These objects are any shared configuration objects that are only consumed by others.
shared_config_objects = [
    'regulator_configuration',
    'line_configuration',
    'line_spacing',
    'transformer_configuration',
    'triplex_line_conductor',
    'triplex_line_configuration',
    'underground_line_conductor',
    'overhead_line_conductor'
]

def read_gld_objects_and_schedules(input_file, origin_datetime="2017 Jun 1 2:00PM"):
    all_gld_objects = {}

    origin_datetime = datetime.strptime(origin_datetime, "%Y %b %d %I:%M%p")
    delta_datetime = timedelta(minutes=1)
    sub_datetime = origin_datetime - delta_datetime

    curr_object = None
    curr_schedule = None
    ignore_elements = False
    found_schedule = False
    all_includes = []
    all_schedules = {}

    inputfile = open(input_file, "r")
    all_rows = inputfile.readlines()

    for row in all_rows:
        if row[:8] == "#include":
            entries = row.split()
            location = entries[1].strip('";')
            include_file = open(location, "r")
            include_rows = include_file.readlines()
            all_includes = all_includes + include_rows
    all_rows = all_rows + all_includes

    for row in all_rows:
        row = row.strip()
        units = None

        # Deal with comments
        if row[:2] == "//":
            continue
        if row.find("//") != -1:
            row = row[:row.find("//")]

        entries = row.split()
        if len(entries) > 0 and entries[0] == "object":
            if curr_object is None:
                obj = entries[1].split(":")
                obj_class = obj[0]
                if obj_class in skipped_objects:
                    continue
                curr_object = getattr(gridlabd, obj_class)()
                if len(obj) > 1:
                    curr_object["name"] = obj_class + ":" + obj[1]
            else:
                ignore_elements = True

        elif len(entries) > 0 and entries[0] == "schedule":
            if curr_schedule is None:
                schedule = entries[1]
                schedule_bracket_cnt = 1
            curr_schedule = schedule

        else:
            if curr_object == None and curr_schedule == None:
                continue
            if curr_object != None:
                if len(row) > 0 and row.find(";") != -1:	
                    row = row[:row.find(";")]
                entries = row.split()
                if len(entries) > 1:
                    element = entries[0]
                    value = entries[1].replace('"', "")

                    if len(entries) > 2:
                        units = entries[2]
                        # TODO: Deal with units correctly
                        if obj_class == "line_spacing" and units == "in":
                            value = str(float(value) / 12)
                        if obj_class == "capacitor" and units == "MVAr":
                            value = str(float(value) * 1e6)
                        # print element,value,units
                        # if units[0] =='k':
                        #    value = value/1000.0

                    # Assuming no nested objects for now.
                    curr_object[element] = value

                if len(row) >= 1:
                    if row[-1] == "}" or row[-2:] == "};":
                        if ignore_elements:  # Assumes only one layer of nesting
                            ignore_elements = False
                        else:
                            try:
                                all_gld_objects[
                                    curr_object["name"]
                                ] = curr_object
                                curr_object = None
                            except:

                                if (
                                    curr_object["from"] != None
                                    and curr_object["to"] != None
                                ):
                                    curr_object["name"] = (
                                        curr_object["from"]
                                        + "-"
                                        + curr_object["to"]
                                    )
                                    all_gld_objects[
                                        curr_object["name"]
                                    ] = curr_object

                                else:
                                    logger.debug("Warning object missing a name")
                                curr_object = None

            if curr_schedule != None:
                row = row.strip(";")
                entries = row.split()
                if len(entries) > 5 and not found_schedule:
                    cron = " ".join(entries[:-1])
                    value = entries[-1]
                    iter = croniter(cron, sub_datetime)
                    if iter.get_next(datetime) == origin_datetime:
                        found_schedule = True
                        all_schedules[curr_schedule] = value

                if len(row) >= 1:
                    if row[-1] == "}":
                        schedule_bracket_cnt = schedule_bracket_cnt - 1
                    if row[0] == "{":
                        schedule_bracket_cnt = schedule_bracket_cnt + 1
                    if schedule_bracket_cnt == 0:
                        curr_schedule = None
                        found_schedule = False

    return (all_gld_objects, all_schedules)

def parse_line_length(line, name):
    #we always return meters

    if not hasattr(line, "_length"):
        raise Exception(f"Line {name} does not have a length specified")

    if line["length"].find('km') != -1:
        # If it's given in km, change to meters
        line["length"] = remove_nonnum.sub('', line["length"])
        return float(line["length"]) * 1e3
    else:
        # Change feet to meters
        return float(line["length"]) * 0.3048

def convert_Z_matrix_per_mile_to_per_meter(z_matrix):
    for i in range(len(z_matrix)):
        for j in range(len(z_matrix[0])):
            z_matrix[i][j] = z_matrix[i][j] / meters_per_mile
    
    return z_matrix

class Reader(AbstractReader):
    """
    The schema is read in gridlabd.py which is imported as a module here.
    The class objects are stored in the global space of the gridlabd module
    """
    register_names = ["glm", "gridlabd"]

    def __init__(self, **kwargs):
        self.all_gld_objects = {}

        """Gridlabd class CONSTRUCTOR."""

        self.input_file = kwargs.get("input_file", "./input.glm")
        super(Reader, self).__init__(**kwargs)

    
    def parse(self, model, origin_datetime="2017 Jun 1 2:00PM"):
        self.all_gld_objects, all_schedules = read_gld_objects_and_schedules(self.input_file, origin_datetime)

        for name, obj in self.all_gld_objects.items():
            obj_type = type(obj).__name__

            if obj_type in shared_config_objects:
                continue

            if obj_type == "triplex_node" or obj_type == "triplex_meter" and hasattr(obj, "_power_12") or hasattr(obj, "_power_1") or hasattr(obj, "_power_2"):
                # Actually a triplex load. Change obj_type and skip "triplex_node" code, to pick up at "triplex_load" code
                obj_type = "triplex_load"

            phases, is_delta, is_triplex = parse_phases(obj["phases"], name)

            if obj_type == "node" or obj_type == "meter":
                # Using "easier to ask for forgiveness than permission" (EAFP) rather than "look before you leap" (LBYL) which would use if has_attr(obj,'_name').

                api_node = None
                try:
                    bustype = obj["bustype"]
                    if bustype == "SWING":
                        api_node = PowerSource(model)
                    else:
                        api_node = Node(model)
                except AttributeError:
                    api_node = Node(model)

                api_node.name = name

                if is_triplex:
                    raise Exception(f"Triplex is indicated on a non-triplex node. {api_node.name}")

                api_node.phases = [Unicode(x) for x in phases]
                api_node.is_delta = is_delta
                api_node.is_triplex = is_triplex
                api_node.triplex_phase = None
       
                try:
                    api_node.nominal_voltage = float(obj["nominal_voltage"])
                except AttributeError:
                    pass

                try:
                    api_node.voltage_A = complex(obj["voltage_A"])
                except AttributeError:
                    pass
                try:
                    api_node.voltage_B = complex(obj["voltage_B"])
                except AttributeError:
                    pass
                try:
                    api_node.voltage_C = complex(obj["voltage_C"])
                except AttributeError:
                    pass

                has_parent = None
                try:
                    api_node.parent = obj["parent"]
                    has_parent = True
                except AttributeError:
                    has_parent = False

            elif obj_type == "triplex_node" or obj_type == "triplex_meter":
                api_node = Node(model)

                api_node.name = name

                if not is_triplex:
                    raise Exception(f"Triplex is not indicated in phase information on a triplex node or meter. (obj:{name})")

                api_node.phases = triplex_phases
                api_node.is_delta = is_delta
                api_node.is_triplex = is_triplex
                api_node.triplex_phase = Unicode(phases[0])

                try:
                    api_node.nominal_voltage = float(obj["nominal_voltage"])
                except AttributeError:
                    pass

                try:
                    api_node.voltage_1 = complex(obj["voltage_1"])
                    api_node.voltage_2 = complex(obj["voltage_2"])
                except AttributeError:
                    pass

                try:
                    api_node.parent = obj["parent"]
                except AttributeError:
                    pass

            elif obj_type == "transformer":

                api_transformer = PowerTransformer(model)
                api_transformer.name = name

                try:
                    api_transformer.from_element = obj["from"]
                except AttributeError:
                    pass

                try:
                    api_transformer.to_element = obj["to"]
                except AttributeError:
                    pass

                api_transformer.phases = phases

                winding1 = Winding(model)
                winding2 = Winding(model)
                winding3 = Winding(model)
                num_windings = 2
                winding1.voltage_type = 0
                winding2.voltage_type = 2
                winding3.voltage_type = 2

                try:
                    winding1.phase_windings = []
                    winding2.phase_windings = []
                    winding3.phase_windings = []
                    for p in phases:
                        pw1 = PhaseWinding(model)
                        pw1.phase = p
                        winding1.phase_windings.append(pw1)
                        pw2 = PhaseWinding(model)
                        pw2.phase = p
                        winding2.phase_windings.append(pw2)

                except AttributeError:
                    pass

                try:
                    # Even though the transformer may be ABCN, (ie there's a neutral on the wire) we assume a delta primary doesn't connect the the neutral wire.
                    config_name1 = obj["configuration"]
                    for config_name, config in self.all_gld_objects.items():
                        if config_name == config_name1:
                            try:
                                conn = str(config["connect_type"])
                                # Assume a grounded Wye - Wye connection has a neutral on both sides
                                if conn == '1' or conn == "WYE_WYE":
                                    winding1.connection_type = "Y"
                                    winding2.connection_type = "Y"

                                # Assume that the secondary on a delta-delta has a grounding neutral, but the high side doesn't
                                if conn == '2' or conn == "DELTA_DELTA":
                                    winding1.connection_type = "D"
                                    winding2.connection_type = "D"

                                # Assume that the secondary on a delta-wye has a grounding neutral, but the high side doesn't
                                if conn == '3' or conn == "DELTA_GWYE":
                                    winding1.connection_type = "D"
                                    winding2.connection_type = "Y"

                                # For a single phase transformer, no connection type is specified. It steps from a single phase and neutral to a single phase and neutral
                                if conn == '4' or conn == "SINGLE_PHASE":
                                    pass  # The phase is already covered by the "phases" attribute

                                # For a single phase center tapped transformer no connection type is specified. Its steps from a single phase and neutral to a neutral and two low voltage lines
                                if conn == '5' or conn == "SINGLE_PHASE_CENTER_TAPPED":
                                    api_transformer.is_center_tap = True
                                    num_windings = 3
                                    winding2.phase_windings[
                                        0
                                    ].phase = (
                                        "1"
                                    )  # TODO understand the reason this was A

                                    pw3 = PhaseWinding(model)
                                    pw3.phase = (
                                        "2"
                                    )  # TODO understand the reason this was B
                                    winding3.phase_windings.append(pw3)
                            except AttributeError:
                                pass

                            try:
                                install_type = config["install_type"]
                                api_transformer.install_type = install_type
                            except AttributeError:
                                pass

                            try:
                                noloadloss = config["no_load_loss"]
                                api_transformer.noload_loss = float(noloadloss)
                            except AttributeError:
                                pass

                            try:
                                shunt_impedance = complex(
                                    config["shunt_impedance"])
                                api_transformer.shunt_impedance = shunt_impedance
                            except AttributeError:
                                pass

                            try:
                                high_voltage = config["primary_voltage"]
                                if high_voltage.find('kV') != -1:
                                    high_voltage = remove_nonnum.sub(
                                        '', high_voltage)
                                    winding1.nominal_voltage = float(
                                        high_voltage) * 1e3
                                else:
                                    high_voltage = remove_nonnum.sub(
                                        '', high_voltage)
                                    winding1.nominal_voltage = float(
                                        high_voltage)
                            except AttributeError:
                                pass

                            try:
                                low_voltage = config["secondary_voltage"]
                                if low_voltage.find('kV') != -1:
                                    low_voltage = remove_nonnum.sub(
                                        '', low_voltage)
                                    winding2.nominal_voltage = float(
                                        low_voltage) * 1e3
                                else:
                                    low_voltage = remove_nonnum.sub(
                                        '', low_voltage)
                                    winding2.nominal_voltage = float(
                                        low_voltage)
                                if num_windings == 3:
                                    winding3.nominal_voltage = -float(low_voltage) # To indicate the 180 degree phase shift
                            except AttributeError:
                                pass

                            try:
                                resistance = float(config["resistance"])
                                if num_windings == 2:
                                    winding1.resistance = resistance / 2.0
                                    winding2.resistance = resistance / 2.0
                                if num_windings == 3:
                                    winding1.resistance = resistance / 2.0
                                    winding2.resistance = (
                                        resistance
                                    )  # Using power flow approximation from "Electric Power Distribution Handbook" by Short page 188
                                    winding3.resistance = resistance

                            except AttributeError:
                                pass

                            failed_reactance = True

                            reactances = []
                            try:
                                reactance = float(config["reactance"])
                                failed_reactance = False
                                reactance1 = reactance
                                reactances.append(
                                    reactance1
                                )  # TODO: Change documentation to reflect that we aren't indicating the from-to relation in reactances.
                                # reactances.append((0,1,reactance1))
                                if (
                                    num_windings == 3
                                ):  # TODO: Change documentation to reflect that we aren't indicating the from-to relation in reactances.
                                    reactance2 = complex(config["impedance1"])
                                    reactances.append(reactance2.imag)
                                    reactance3 = complex(config["impedance2"])
                                    reactances.append(reactance3.imag)

                            except AttributeError:
                                if (
                                    not failed_reactance
                                ):  # Should only fail if there are three windings in the system
                                    reactance = float(config["reactance"])
                                    reactances[0] = 0.8 * reactance
                                    reactances.append(
                                        0.4 * reactance
                                    )  # Using power flow approximation from "Electric Power Distribution Handbook" by Short page 188 of transformer with no center tap
                                    reactances.append(0.4 * reactance)

                            if failed_reactance:
                                try:
                                    impedance = complex(config["impedance"])
                                    resistance = impedance.real
                                    reactance = impedance.imag
                                    if num_windings == 2:
                                        winding1.resistance
                                        winding1.resistance = resistance / 2.0
                                        winding2.resistance = resistance / 2.0
                                        reactances.append(reactance)

                                    if num_windings == 3:
                                        winding1.resistance = resistance / 2.0
                                        winding2.resistance = (
                                            resistance
                                        )  # Using power flow approximation from "Electric Power Distribution Handbook" by Short page 188
                                        winding3.resistance = resistance
                                        reactances.append(0.8 * reactance)
                                        reactances.append(
                                            0.4 * reactance
                                        )  # Using power flow approximation from "Electric Power Distribution Handbook" by Short page 188 of transformer with no center tap
                                        reactances.append(0.4 * reactance)
                                except AttributeError:
                                    pass

                            if len(reactances) > 0:
                                for x in reactances:
                                    api_transformer.reactances.append(x)

                            power_rating = 0

                            if num_windings == 3:
                                power_ratings = []
                                try:
                                    if config["powerA_rating"].find(
                                            'kVA') != -1:
                                        config[
                                            "powerA_rating"] = remove_nonnum.sub(
                                                '', config["powerA_rating"])
                                        power_ratings.append(
                                            float(config["powerA_rating"]) *
                                            1000)
                                    else:
                                        power_ratings.append(
                                            float(config["powerA_rating"]) *
                                            1000)
                                except AttributeError:
                                    pass
                                try:
                                    if config["powerB_rating"].find(
                                            'kVA') != -1:
                                        config[
                                            "powerB_rating"] = remove_nonnum.sub(
                                                '', config["powerB_rating"])
                                        power_ratings.append(
                                            float(config["powerB_rating"]) *
                                            1000)
                                    else:
                                        power_ratings.append(
                                            float(config["powerB_rating"]) *
                                            1000)
                                except AttributeError:
                                    pass
                                try:
                                    if config["powerC_rating"].find(
                                            'kVA') != -1:
                                        config[
                                            "powerC_rating"] = remove_nonnum.sub(
                                                '', config["powerC_rating"])
                                        power_ratings.append(
                                            float(config["powerC_rating"]) *
                                            1000)
                                    else:
                                        power_ratings.append(
                                            float(config["powerC_rating"]) *
                                            1000)
                                except AttributeError:
                                    pass
                                api_transformer.power_ratings = power_ratings

                            power_rating_found = False
                            try:
                                if config["power_rating"].find('kVA') != -1:
                                    config["power_rating"] = remove_nonnum.sub(
                                        '', config["power_rating"])
                                    power_rating = float(
                                        config["power_rating"]) * 1e3
                                else:
                                    config["power_rating"] = remove_nonnum.sub(
                                        '', config["power_rating"])
                                    power_rating = float(
                                        config["power_rating"]) * 1e3
                                winding1.rated_power = power_rating
                                if num_windings == 3:
                                    winding2.rated_power = power_rating / 2.0
                                    winding3.rated_power = power_rating / 2.0
                                else:
                                    winding2.rated_power = power_rating
                                
                                power_rating_found = True
                            except AttributeError:
                                pass

                            if not power_rating_found:
                                #Todo: why do we add up all the powers for A, B, and C?
                                try:
                                    if config["powerA_rating"].find('kVA') != -1:
                                        config["powerA_rating"] = remove_nonnum.sub(
                                            '', config["powerA_rating"])
                                        power_rating = float(
                                            config["powerA_rating"]) * 1000
                                    else:
                                        power_rating = float(
                                            config["powerA_rating"]) * 1000
                                    winding1.rated_power = power_rating
                                    if num_windings == 3:
                                        winding2.rated_power = power_rating / 2.0
                                        winding3.rated_power = power_rating / 2.0
                                    else:
                                        winding2.rated_power = power_rating
                                except AttributeError:
                                    pass

                                try:
                                    if config["powerB_rating"].find('kVA') != -1:
                                        config["powerB_rating"] = remove_nonnum.sub(
                                            '', config["powerB_rating"])
                                        power_rating += float(
                                            config["powerB_rating"]) * 1000
                                    else:
                                        power_rating += float(
                                            config["powerB_rating"]) * 1000
                                    winding1.rated_power = power_rating
                                    if num_windings == 3:
                                        winding2.rated_power = power_rating / 2.0
                                        winding3.rated_power = power_rating / 2.0
                                    else:
                                        winding2.rated_power = power_rating
                                except AttributeError:
                                    pass
                                try:
                                    if config["powerC_rating"].find('kVA') != -1:
                                        config["powerC_rating"] = remove_nonnum.sub(
                                            '', config["powerC_rating"])
                                        power_rating += float(
                                            config["powerC_rating"]) * 1000
                                    else:
                                        power_rating += float(
                                            config["powerC_rating"]) * 1000
                                    winding1.rated_power = power_rating
                                    if num_windings == 3:
                                        winding2.rated_power = power_rating / 2.0
                                        winding3.rated_power = power_rating / 2.0
                                    else:
                                        winding2.rated_power = power_rating
                                except AttributeError:
                                    pass

                except AttributeError:
                    pass

                windings = [winding1, winding2]
                if num_windings == 3:
                    windings.append(winding3)
                api_transformer.windings = windings

            elif obj_type == "load" or obj_type == "triplex_load":

                load_parser = LoadParser()
                load_parser.parse(all_schedules, model, obj)

            elif obj_type == "fuse":
                api_line = Line(model)
                api_line.is_fuse = True
                api_line.name = name
                api_line.phases = phases

                try:
                    api_line._current_limit = remove_nonnum.sub('', obj["current_limit"])
                except AttributeError:
                    pass

                try:
                    api_line.from_element = obj["from"]
                except AttributeError:
                    pass

                try:
                    api_line.to_element = obj["to"]
                except AttributeError:
                    pass

                wires = []
                try:
                    status = obj["phase_A_status"]
                    api_wire = Wire(model)
                    api_wire.phase = "A"
                    if status == "BLOWN" or status == "OPEN":
                        api_wire.is_open = True
                    else:
                        api_wire.is_open = False
                    wires.append(api_wire)
                except AttributeError:
                    pass

                try:
                    status = obj["phase_B_status"]
                    api_wire = Wire(model)
                    api_wire.phase = "B"
                    if status == "BLOWN" or status == "OPEN":
                        api_wire.is_open = True
                    else:
                        api_wire.is_open = False
                    wires.append(api_wire)
                except AttributeError:
                    pass

                try:
                    status = obj["phase_C_status"]
                    api_wire = Wire(model)
                    api_wire.phase = "C"
                    if status == "BLOWN" or status == "OPEN":
                        api_wire.is_open = True
                    else:
                        api_wire.is_open = False
                    wires.append(api_wire)
                except AttributeError:
                    pass

                try:
                    if len(wires) == 0:
                        for p in phases:
                            api_wire = Wire(model)
                            api_wire.phase = p
                            wires.append(api_wire)
                            if obj["status"] == "OPEN":
                                wires[-1].is_open = True
                            else:
                                wires[-1].is_open = False
                except AttributeError:
                    pass

                api_line.wires = wires

            elif obj_type == "switch" or obj_type == "recloser":
                #todo: implement recloser operations.

                api_line = Line(model)
                api_line.is_switch = True
                api_line.length = 1
                api_line.name = name
                api_line.phases = phases

                try:
                    api_line.from_element = obj["from"]
                except AttributeError:
                    pass

                try:
                    api_line.to_element = obj["to"]
                except AttributeError:
                    pass

                wires = []
                try:
                    status = obj["phase_A_state"]
                    api_wire = Wire(model)
                    api_wire.phase = "A"
                    if status == "OPEN":
                        api_wire.is_open = True
                    else:
                        api_wire.is_open = False
                    wires.append(api_wire)
                except AttributeError:
                    pass
                try:
                    status = obj["phase_B_state"]
                    api_wire = Wire(model)
                    api_wire.phase = "B"
                    if status == "OPEN":
                        api_wire.is_open = True
                    else:
                        api_wire.is_open = False
                    wires.append(api_wire)
                except AttributeError:
                    pass

                try:
                    status = obj["phase_C_state"]
                    api_wire = Wire(model)
                    api_wire.phase = "C"
                    if status == "OPEN":
                        api_wire.is_open = True
                    else:
                        api_wire.is_open = False
                    wires.append(api_wire)
                except AttributeError:
                    pass

                try:
                    if len(wires) == 0:
                        for p in phases:
                            api_wire = Wire(model)
                            api_wire.phase = p
                            wires.append(api_wire)
                            if obj["status"] == "OPEN":
                                wires[-1].is_open = True
                            else:
                                wires[-1].is_open = False
                except AttributeError:
                    pass

                api_line.wires = wires

            elif obj_type == "overhead_line":

                api_line = Line(model)
                api_line.line_type = "overhead"
                try:
                    api_line.name = obj["name"]
                except AttributeError:
                    pass

                api_line.length = parse_line_length(obj, name)

                try:
                    api_line.from_element = obj["from"]
                except AttributeError:
                    pass

                try:
                    api_line.to_element = obj["to"]
                except AttributeError:
                    pass

                try:
                    config_name = obj["configuration"]
                    config = self.all_gld_objects[config_name]
                    conductors = {}
                    num_phases = 0
                    try:
                        conna = config["conductor_A"]
                        api_wire = Wire(model)
                        api_wire.phase = "A"
                        conductors[api_wire] = conna
                    except AttributeError:
                        pass
                    try:
                        connb = config["conductor_B"]
                        api_wire = Wire(model)
                        api_wire.phase = "B"
                        conductors[api_wire] = connb
                    except AttributeError:
                        pass
                    try:
                        connc = config["conductor_C"]
                        api_wire = Wire(model)
                        api_wire.phase = "C"
                        conductors[api_wire] = connc
                    except AttributeError:
                        pass
                    try:
                        connn = config["conductor_N"]
                        api_wire = Wire(model)
                        api_wire.phase = "N"
                        conductors[api_wire] = connn
                    except AttributeError:
                        pass

                    # Pass by reference so the conductors are updated in dictionary when api_wire is changed
                    for api_wire in conductors:
                        cond_name = conductors[api_wire]
                        conductor = self.all_gld_objects[cond_name]
                        try:
                            api_wire.diameter = float(conductor["diameter"])
                        except AttributeError:
                            pass
                        try:
                            if conductor["geometric_mean_radius"].find('cm') != -1:
                                conductor["geometric_mean_radius"] = remove_nonnum.sub('', conductor["geometric_mean_radius"])
                                api_wire.gmr = float(conductor["geometric_mean_radius"]) / 30.48 # convert cm to feet
                            else:
                                api_wire.gmr = float(conductor["geometric_mean_radius"])
                        except AttributeError:
                            pass
                        try:
                            if conductor["resistance"].find('Ohm/km') != -1:
                                # Convert Ohm/km into Ohm/mi
                                conductor["resistance"] = remove_nonnum.sub(
                                    '', conductor["resistance"])
                                api_wire.resistance = float(
                                    conductor["resistance"]) * 1.609344
                            else:
                                api_wire.resistance = float(conductor["resistance"])
                        except AttributeError:
                            pass
                        try:
                            api_wire.ampacity = float(
                                conductor["rating.summer.continuous"]
                            )
                        except AttributeError:
                            pass
                        try:
                            api_wire.emergency_ampacity = float(
                                conductor["rating.summer.emergency"]
                            )
                        except AttributeError:
                            pass

                    spacing_name = None
                    try:
                        spacing_name = config["spacing"]
                    except AttributeError:
                        pass
                    if spacing_name is not None:
                        spacing_config = self.all_gld_objects[spacing_name]
                        distances = compute_overhead_spacing(spacing_config, conductors) # sets conductor.X and Y values in meters for 4 wire setups
                except AttributeError:
                    pass

                wire_list = list(conductors.keys())

                impedance_matrix = try_load_direct_line_impedance(config)

                if impedance_matrix == None:
                    striped_distances = distances[:,~np.all(distances, axis=0, where=[-1])][~np.all(distances, axis=1, where=[-1]),:]
                    impedance_matrix = compute_overhead_impedance(wire_list, striped_distances)

                api_line.impedance_matrix = convert_Z_matrix_per_mile_to_per_meter(impedance_matrix)

                capacitance_matrix = try_load_direct_line_capacitance(config)

                if capacitance_matrix != None:
                    api_line.capacitance_matrix = capacitance_matrix

                # Calculate the shunt admittance of the line, based on the capacitance matrix.
                # Incorporating line capacitance is an option in GridlabD which is not enabled by default
                # Would we want to similarly limit it in such a way?

                api_line.wires = wire_list
                for api_wire in conductors:
                    try:
                        if api_wire.diameter is not None:
                            api_wire.diameter = (
                                api_wire.diameter * 0.0254 # / 12 * 0.3048 # convert from inches to meters
                            )  # i.e. the same for all the wires.
                    except AttributeError:
                        pass
                    try:
                        if api_wire.gmr is not None:
                            api_wire.gmr = api_wire.gmr * 0.3048
                    except AttributeError:
                        pass
                    try:
                        if api_wire.resistance is not None:
                            api_wire.resistance = (
                                api_wire.resistance / meters_per_mile
                            )  # Convert Ohms/mile into Ohms per meter
                    except AttributeError:
                        pass

            elif obj_type == "triplex_line":
                api_line = Line(model)
                try:
                    api_line.name = obj["name"]
                except AttributeError:
                    pass

                api_line.length = parse_line_length(obj, name)

                try:
                    api_line.from_element = obj["from"]
                except AttributeError:
                    pass

                try:
                    api_line.to_element = obj["to"]
                except AttributeError:
                    pass

                try:
                    config_name = obj["configuration"]
                    config = self.all_gld_objects[config_name]
                    conductors = {}
                    num_phases = 0
                    try:
                        conn1 = config["conductor_1"]
                        num_phases = num_phases + 1
                        api_wire = Wire(model)
                        api_wire.phase='1'
                        # api_wire.phase = "A"
                        conductors[api_wire] = conn1
                    except AttributeError:
                        pass
                    try:
                        conn2 = config["conductor_2"]
                        num_phases = num_phases + 1
                        api_wire = Wire(model)
                        api_wire.phase='2'
                        # api_wire.phase = "B"
                        conductors[api_wire] = conn2
                    except AttributeError:
                        pass

                    try:
                        conn3 = config["conductor_N"]
                        num_phases = num_phases + 1
                        api_wire = Wire(model)
                        api_wire.phase = "N"
                        conductors[api_wire] = conn3
                    except AttributeError:
                        pass

                    try:
                        api_wire.insulation_thickness = (
                            float(config["insulation_thickness"])
                        )
                    except AttributeError:
                        pass

                    try:
                        api_wire.diameter = float(config["diameter"])
                    except AttributeError:
                        pass

                    for api_wire in conductors:
                        cond_name = conductors[api_wire]
                        conductor = self.all_gld_objects[cond_name]
                        try:
                            api_wire.gmr = (
                                float(conductor["geometric_mean_radius"]) # * 0.3048 to convert feet to meters
                            )
                        except AttributeError:
                            pass
                        try:
                            api_wire.resistance = (
                                    float(conductor["resistance"]))
                            # if api_line.length is not None:
                            #     api_wire.resistance = (
                            #         float(conductor["resistance"])
                            #         * api_line.length
                            #         / meters_per_mile
                            #     )  # since we converted the length to m already
                        except AttributeError:
                            pass
                except AttributeError:
                    pass

                wire_list = list(conductors.keys())

                impedance_matrix = try_load_direct_line_impedance(config)

                if impedance_matrix == None:
                    impedance_matrix = compute_triplex_impedance(wire_list)

                api_line.impedance_matrix = convert_Z_matrix_per_mile_to_per_meter(impedance_matrix)

                api_line.wires = wire_list

            elif obj_type == "underground_line":

                api_line = Line(model)
                api_line.line_type = "underground"
                api_line.name = name
                api_line.phases = phases

                api_line.length = parse_line_length(obj, name)

                try:
                    api_line.from_element = obj["from"]
                except AttributeError:
                    pass

                try:
                    api_line.to_element = obj["to"]
                except AttributeError:
                    pass

                try:
                    config_name = obj["configuration"]
                    config = self.all_gld_objects[config_name]
                    conductors = {}
                    num_phases = 0
                    try:
                        conna = config["conductor_A"]
                        num_phases = num_phases + 1
                        api_wire = Wire(model)
                        api_wire.phase = "A"
                        conductors[api_wire] = conna
                    except AttributeError:
                        pass
                    try:
                        connb = config["conductor_B"]
                        num_phases = num_phases + 1
                        api_wire = Wire(model)
                        api_wire.phase = "B"
                        conductors[api_wire] = connb
                    except AttributeError:
                        pass
                    try:
                        connc = config["conductor_C"]
                        num_phases = num_phases + 1
                        api_wire = Wire(model)
                        api_wire.phase = "C"
                        conductors[api_wire] = connc
                    except AttributeError:
                        pass
                    try:
                        connn = config["conductor_N"]
                        api_wire = Wire(model)
                        api_wire.phase = "N"
                        conductors[api_wire] = connn
                    except AttributeError:
                        pass

                    # Neutral may be concentric for underground cables or may be a separate wire
                    # TODO: consider other attributes of underground cables?
                    for api_wire in conductors:
                        cond_name = conductors[api_wire]
                        conductor = self.all_gld_objects[cond_name]
                        try:
                            api_wire.outer_diameter = float(
                                conductor["outer_diameter"]) # inches
                        except AttributeError:
                            pass
                        try:
                            api_wire.concentric_neutral_diameter = float(
                                conductor["neutral_diameter"]) # inches
                        except AttributeError:
                            pass

                        try:
                            api_wire.concentric_neutral_nstrand = int(
                                float(conductor["neutral_strands"])) # count
                        except AttributeError:
                            pass

                        try:
                            api_wire.conductor_diameter = float(
                                conductor["conductor_diameter"]) # inches
                        except AttributeError:
                            pass

                        # set gmr to be the conductor gmr for underground cables
                        try:
                            api_wire.gmr = float(conductor["conductor_gmr"])
                        except AttributeError:
                            pass
                        # set resistance to be the conductor resistance for underground cables
                        try:
                            if conductor["conductor_resistance"].find('Ohm/km') != -1:
                                conductor["conductor_resistance"] = remove_nonnum.sub(
                                    '', conductor["conductor_resistance"])
                                api_wire.resistance = float(
                                    conductor["conductor_resistance"]) * 1.609344
                            else:
                                # NOTE: There doesn't seem to be inclusion of taped shielding GMR or resistance here
                                # They seem to be assumed to be zero
                                api_wire.resistance = float(conductor["conductor_resistance"])
                        except AttributeError:
                            pass

                        # if concentric gmr in not None set it for the underground cables
                        try:
                            api_wire.concentric_neutral_gmr = float(
                                conductor["neutral_gmr"]
                            )
                        except AttributeError:
                            pass
                        # if concentric resistances is not None set it for underground cables
                        try:
                            api_wire.concentric_neutral_resistance = float(
                                conductor["neutral_resistance"]
                            )
                        except AttributeError:
                            pass

                    spacing_name = None
                    try:
                        spacing_name = config["spacing"]
                    except AttributeError:
                        pass
                    if spacing_name is not None:
                        spacing_config = self.all_gld_objects[spacing_name]

                        distances = compute_underground_spacing([api_wire.outer_diameter for api_wire in conductors], spacing_config, conductors)

                        api_line.spacing = spacing_config
                except AttributeError:
                    pass

                wire_list = list(conductors.keys())

                impedance_matrix = try_load_direct_line_impedance(config)

                if impedance_matrix == None:
                    striped_distances = distances[:,~np.all(distances, axis=0, where=[-1])][~np.all(distances, axis=1, where=[-1]),:]
                    impedance_matrix = compute_underground_impedance(wire_list, striped_distances)

                api_line.impedance_matrix = convert_Z_matrix_per_mile_to_per_meter(impedance_matrix)

                # capacitance_matrix = try_load_direct_line_capacitance(config)

                # if capacitance_matrix == None:
                #     capacitance_matrix = compute_underground_capacitance(wire_list)
                
                # api_line.capacitance_matrix = convert_Z_matrix_per_mile_to_per_meter(capacitance_matrix)

                api_line.wires = wire_list

            elif obj_type == "capacitor":

                api_capacitor = Capacitor(model)
                api_capacitor.name = name

                try:
                    connected_phases, is_delta, _ = parse_phases(str(obj["phases_connected"]), name)
                except AttributeError:
                    connected_phases = phases         

                api_capacitor.is_delta = is_delta
                api_capacitor.connected_phases = connected_phases

                try:
                    api_capacitor.nominal_voltage = float(obj["nominal_voltage"])
                except AttributeError:
                    pass

                try:
                    api_capacitor.delay = float(obj["time_delay"])
                except AttributeError:
                    pass

                try:
                    control = obj["control"].upper()
                    if control == "VOLT":
                        api_capacitor.mode = "voltage"
                    if control == "VAR":
                        api_capacitor.mode = "reactivePower"
                    if control == "MANUAL":
                        api_capacitor.mode = "none"
                except AttributeError:
                    pass

                try:
                    api_capacitor.connecting_element = obj["parent"]
                except AttributeError:
                    pass

                # If both volt and Var limits are set use the Volt ones. Therefore we set the Var values first and overwrite high and low if there are volt ones as well
                try:
                    api_capacitor.high = float(obj["VAr_set_high"])
                    api_capacitor.low = float(obj["VAr_set_low"])
                except AttributeError:
                    pass

                try:
                    api_capacitor.high = float(obj["voltage_set_high"])
                    api_capacitor.low = float(obj["voltage_set_low"])
                except AttributeError:
                    pass

                try:
                    api_capacitor.pt_phase = obj["pt_phase"]
                except AttributeError:
                    pass

                phase_capacitors = []
                try:
                    varA = float(obj["capacitor_A"])
                    pc = PhaseCapacitor(model)
                    pc.phase = "A"
                    pc.var = varA
                    phase_capacitors.append(pc)  
                    # in case there is no switching attribute
                    phase_capacitors[-1].switch = obj["switch_A"]
                except AttributeError:
                    pass

                try:
                    varB = float(obj["capacitor_B"])
                    pc = PhaseCapacitor(model)
                    pc.phase = "B"
                    pc.var = varB
                    phase_capacitors.append(pc)
                    # in case there is no switching attribute
                    phase_capacitors[-1].switch = obj["switch_B"]
                except AttributeError:
                    pass

                try:
                    varC = float(obj["capacitor_C"])
                    pc = PhaseCapacitor(model)
                    pc.phase = "C"
                    pc.var = varC
                    phase_capacitors.append(pc)  
                    # in case there is no switching attribute
                    phase_capacitors[-1].switch = obj["switch_C"]
                except AttributeError:
                    pass

                api_capacitor.phase_capacitors = phase_capacitors

            elif obj_type == "regulator":
                api_regulator = Regulator(model)
                try:
                    api_regulator.name = obj["name"]
                except AttributeError:
                    pass

                try:
                    api_regulator.high_from = obj["from"]
                except AttributeError:
                    pass

                try:
                    api_regulator.low_to = obj["to"]
                except AttributeError:
                    pass

                winding1 = Winding(model)
                winding1.voltage_type = 0
                winding2 = Winding(model)
                winding2.voltage_type = 2

                try:
                    if hasattr(obj,"nominal_voltage"):
                        nominal_voltage = obj["nominal_voltage"]
                        winding1.nominal_voltage = float(nominal_voltage)
                        winding2.nominal_voltage = float(nominal_voltage)
                    else:
                        from_element = obj["from"]
                        from_nominal_voltage = self.all_gld_objects[from_element]["nominal_voltage"]
                        winding1.nominal_voltage = float(from_nominal_voltage)
                        winding2.nominal_voltage = float(from_nominal_voltage)
                        
                except AttributeError:
                    pass

                try:
                    winding1.phase_windings = []
                    winding2.phase_windings = []
                    for p in phases:
                        pw1 = PhaseWinding(model)
                        pw1.phase = p
                        winding1.phase_windings.append(pw1)
                        pw2 = PhaseWinding(model)
                        pw2.phase = p
                        winding2.phase_windings.append(pw2)

                except AttributeError:
                    pass

                try:
                    config_name1 = obj["configuration"]
                    for config_name, config in self.all_gld_objects.items():
                        if config_name == config_name1:# or config._configuration == config_name1:

                            for tap_phase in ["A", "B", "C"]:
                                try:
                                    tap = config["tap_pos_%s" % tap_phase]
                                    if (
                                        winding2.phase_windings is None
                                    ):  # i.e. no phases were listed even though they are there. Should only need to check winding2 (not both windings) since the phases are populated at the same time.
                                        winding1.phase_windings = []
                                        winding2.phase_windings = []

                                    index = None
                                    for i in range(len(winding2.phase_windings)):
                                        if (
                                            winding2.phase_windings[i].phase
                                            == tap_phase
                                        ):
                                            index = i
                                            break
                                    if index is None:
                                        pw1 = PhaseWinding(model)
                                        pw1.phase = tap_phase
                                        winding1.phase_windings.append(pw1)
                                        pw2 = PhaseWinding(model)
                                        pw2.phase = tap_phase
                                        winding2.phase_windings.append(pw2)
                                        index = len(winding2.phase_windings) - 1

                                    winding2.phase_windings[index].tap_position = int(
                                        tap
                                    )

                                except AttributeError:
                                    pass

                            for r_comp_phase in ["A", "B", "C"]:
                                try:
                                    r_comp = config[
                                        "compensator_r_setting_%s" % r_comp_phase
                                    ]
                                    if (
                                        winding2.phase_windings is None
                                    ):  # i.e. no phases were listed even though they are there. Should only need to check winding2 (not both windings) since the phases are populated at the same time.
                                        winding1.phase_windings = []
                                        winding2.phase_windings = []

                                    index = None
                                    for i in range(len(winding2.phase_windings)):
                                        if (
                                            winding2.phase_windings[i].phase
                                            == r_comp_phase
                                        ):
                                            index = i
                                            break
                                    if index is None:
                                        pw1 = PhaseWinding(model)
                                        pw1.phase = r_comp_phase
                                        winding1.phase_windings.append(pw1)
                                        pw2 = PhaseWinding(model)
                                        pw2.phase = r_comp_phase
                                        winding2.phase_windings.append(
                                            pw2
                                        )  # Add the phase in for winding 1 as well
                                        index = len(winding2.phase_windings) - 1

                                    winding2.phase_windings[
                                        index
                                    ].compensator_r = float(r_comp)

                                except AttributeError:
                                    pass

                            for x_comp_phase in ["A", "B", "C"]:
                                try:
                                    x_comp = config[
                                        "compensator_x_setting_%s" % x_comp_phase
                                    ]
                                    if (
                                        winding2.phase_windings is None
                                    ):  # i.e. no phases were listed even though they are there. Should only need to check winding2 (not both windings) since the phases are populated at the same time.
                                        winding1.phase_windings = []
                                        winding2.phase_windings = []

                                    index = None
                                    for i in range(len(winding2.phase_windings)):
                                        if (
                                            winding2.phase_windings[i].phase
                                            == x_comp_phase
                                        ):
                                            index = i
                                            break
                                    if index is None:
                                        pw1 = PhaseWinding(model)
                                        pw1.phase = x_comp_phase
                                        winding1.phase_windings.append(pw1)
                                        pw2 = PhaseWinding(model)
                                        pw2.phase = x_comp_phase
                                        winding2.phase_windings.append(
                                            pw2
                                        )  # Add the phase in for winding 1 as well
                                        index = len(winding2.phase_windings) - 1

                                    winding2.phase_windings[
                                        index
                                    ].compensator_x = float(x_comp)

                                except AttributeError:
                                    pass

                            try:
                                conn = str(config["connect_type"])

                                if not (conn == "1" or conn == "WYE_WYE"):
                                    raise Exception
                                
                                # Version of GLD this is based on only has Wye-Wye regulators
                                # So we always set this to be Y
                                winding1.connection_type = "Y"
                                winding2.connection_type = "Y"

                            except AttributeError:
                                pass

                            try:
                                api_regulator.type = config["Type"]
                            except AttributeError:
                                pass

                            try:
                                api_regulator.delay = float(config["time_delay"])
                            except AttributeError:
                                pass

                            try:
                                api_regulator.bandwidth = float(config["band_width"])
                            except AttributeError:
                                pass

                            try:
                                api_regulator.bandcenter = float(config["band_center"])
                            except AttributeError:
                                pass

                            try:
                                api_regulator.highstep = int(config["raise_taps"])
                            except AttributeError:
                                pass

                            try:
                                api_regulator.lowstep = int(config["lower_taps"])
                            except AttributeError:
                                pass

                            try:
                                api_regulator.pt_ratio = float(
                                    config["power_transducer_ratio"]
                                )
                            except AttributeError:
                                pass

                            try:
                                api_regulator.ct_ratio = float(
                                    config["current_transducer_ratio"]
                                )
                            except AttributeError:
                                pass

                            try:
                                # wire_map = {'A':1,'B':2,'C':3} #Only take one phase (GLD seems to have 3 sometimes)
                                api_regulator.pt_phase = config["PT_phase"].strip('"')[
                                    0
                                ]  # wire_map[config['PT_phase'].strip('"')[0]]
                            except AttributeError:
                                pass

                            try:
                                api_regulator.regulation = float(
                                    config["regulation"]
                                )
                            except AttributeError:
                                pass

                except AttributeError:
                    pass

                windings = [winding1, winding2]
                api_regulator.windings = windings

            else:
                raise Exception(f"Unhandled object type {obj_type}!")

