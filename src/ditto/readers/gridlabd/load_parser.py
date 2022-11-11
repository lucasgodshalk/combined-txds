from ditto.models.node import Node
from ditto.models.load import Load
from ditto.models.phase_load import PhaseLoad

class LoadParser:
    def parse(self, all_schedules, model, obj):
        api_load = Load(model)
        api_node = None
        has_parent = None

        try:
            api_load.connecting_element = obj["parent"]
            has_parent = True
        except AttributeError:
            has_parent = False
            api_node = Node(model)

        api_load.name = None
        try:
            if has_parent:
                api_load.name = obj["name"]
            else:
                api_load.name = "load_" + obj["name"]
                api_load.connecting_element = obj["name"]
                api_node.name = obj["name"]
        except AttributeError:
            pass

        try:
            api_load.nominal_voltage = float(obj["nominal_voltage"])
            if not has_parent:
                api_node.nominal_voltage = float(obj["nominal_voltage"])

        except AttributeError:
            pass

        try:	
            api_load.voltage_1 = complex(obj["voltage_1"])	
        except AttributeError:	
            pass
        try:
            api_load.voltage_2 = complex(obj["voltage_2"])	
        except AttributeError:	
            pass

        phases = []
        is_delta = False

        try:

            phase_str = obj["phases"].strip('"').strip('|')

            if "S" in phase_str:
                #S means that it's split phase/triplex
                api_load.triplex_phase = phase_str[0]
                phase_str = "12"
            elif "D" in phase_str:
                is_delta = True

            for i in phase_str:
                if i == "A" or i == "B" or i == "C" or i == "1" or i == "2":
                    phases.append(i)

            if not has_parent:
                api_node.phases = phases
        except AttributeError:
            pass

        phaseloads = self.__parse_phase_loads(model, obj, all_schedules, is_delta)

        api_load.phase_loads = phaseloads
        
    def __parse_phase_loads(self, model, obj, all_schedules, is_delta):
        #Note that it is possible to have line-to-line loads on a
        #4 wire connection. For a delta wire configuration, a load on phase "A" 
        #really means line-to-line "AB", but we need to distinguish if it is 4 wire.
        # http://gridlab-d.shoutwiki.com/wiki/Power_Flow_User_Guide#Load
        load_connections = ["A", "B", "C", "AB", "BC", "CA", "1", "2", "12"]

        phaseloads = []
        for connection in load_connections:
            parsed_loads = list(self.__parse_phase_load(model, obj, all_schedules, connection, is_delta))
            for phase_load in parsed_loads:
                phaseloads.append(phase_load)
        
        return phaseloads

    def __parse_phase_load(self, model, obj, all_schedules, phase, is_delta):
        # Assume that unless ZIP is specifically specified only one of constant_power, constant_current and constant_impedance is used. A real part of 0 means that I or Z is being used instead.

        try:
            #The spec says `constant_power_X`...but a bunch of files don't conform. Who needs a spec anyway?
            phaseload = self.__create_phaseload(model, phase, is_delta)
            complex_power = complex(obj[f"power_{phase}"])
            p = complex_power.real
            q = complex_power.imag
            if p != 0 or q != 0:
                phaseload.p = p
                phaseload.q = q
                phaseload.model = 1 # The opendss model number (specifying constant power)
                yield phaseload
        except AttributeError:
            pass

        try:
            phaseload = self.__create_phaseload(model, phase, is_delta)
            complex_power = complex(obj[f"constant_power_{phase}"])
            p = complex_power.real
            q = complex_power.imag
            if p != 0 or q != 0:
                phaseload.p = p
                phaseload.q = q
                phaseload.model = 1 # The opendss model number (specifying constant power)
                yield phaseload
        except AttributeError:
            pass

        try:
            phaseload = self.__create_phaseload(model, phase, is_delta)
            complex_impedance = complex(obj[f"impedance_{phase}"])
            if abs(complex_impedance) != 0:
                phaseload.z = complex_impedance
                phaseload.model = 2  # The opendss model number (specifying constant impedance)
                yield phaseload
        except AttributeError:
            pass

        try:
            phaseload = self.__create_phaseload(model, phase, is_delta)
            complex_impedance = complex(obj[f"constant_impedance_{phase}"])
            if abs(complex_impedance) != 0:
                phaseload.z = complex_impedance
                phaseload.model = 2  # The opendss model number (specifying constant impedance)
                yield phaseload
        except AttributeError:
            pass

        try:
            phaseload = self.__create_phaseload(model, phase, is_delta)
            complex_current = complex(obj[f"constant_current_{phase}"])
            if abs(complex_current) != 0:  
                phaseload.i_const = complex_current
                phaseload.model = 5  # The opendss model number (specifying constant current)
                yield phaseload
        except AttributeError:
            pass

        try:
            try:
                phaseload = self.__create_phaseload(model, phase, is_delta)
                base_power = float(obj[f"base_power_{phase}"])
                p = base_power
                phaseload.p = p
            except ValueError:
                data = obj[f"base_power_{phase}"].split("*")
                if data[0] in all_schedules:
                    phaseload.p = float(all_schedules[data[0]]) * float(
                        data[1]
                    )
                if data[1] in all_schedules:
                    phaseload.p = float(all_schedules[data[1]]) * float(
                        data[0]
                    )

            # Require all six elements to compute the ZIP load model
            current_fraction = float(obj[f"current_fraction_{phase}"])
            current_pf = float(obj[f"current_pf_{phase}"])
            power_fraction = float(obj[f"power_fraction_{phase}"])
            power_pf = float(obj[f"power_pf_{phase}"])
            impedance_fraction = float(obj[f"impedance_fraction_{phase}"])
            impedance_pf = float(obj[f"impedance_pf_{phase}"])

            phaseload.ppercentcurrent = current_fraction * current_pf
            phaseload.qpercentcurrent = current_fraction * (
                1 - current_pf
            )
            phaseload.ppercentpower = power_fraction * power_pf
            phaseload.qpercentpower = power_fraction * (1 - power_pf)
            phaseload.ppercentimpedance = (
                impedance_fraction * impedance_pf
            )
            phaseload.qpercentimpedance = impedance_fraction * (
                1 - impedance_pf
            )
            phaseload.use_zip = 1
            yield phaseload
        except AttributeError:
            pass

    def __create_phaseload(self, _, phase, is_delta):
        phaseload = PhaseLoad()
        if is_delta:
            if phase == "A":
                phaseload.phase = "AB"
            elif phase == "B":
                phaseload.phase = "BC"
            elif phase == "C":
                phaseload.phase = "CA"
        else:
            phaseload.phase = phase
        phaseload.p = 0  # Default value
        phaseload.q = 0
        phaseload.z = complex(0, 0)
        phaseload.use_zip = 0
        return phaseload
