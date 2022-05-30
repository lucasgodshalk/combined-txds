class SecondaryTransformerCoil():
    
    def __init__(self
                , nominal_voltage
                , rated_power
                , connection_type
                , voltage_limit
                , resistance
                , reactance
                # , I1 # The current which controls voltage of CCVS
                # , I2 # The current which flows through the node
                ):
        self.nominal_voltage = nominal_voltage
        self.rated_power = rated_power
        self.connection_type = connection_type
        self.voltage_limit = voltage_limit

        self.phase_coils = {}
        
        self.resistance = resistance
        self.reactance = reactance

    # def collect_Y_stamps(self, state):
    #     for phase_coil in self.phase_coils:
    #         phase_coil.collect_Y_stamps(state, self.resistance, self.reactance)