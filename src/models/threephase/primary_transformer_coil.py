class PrimaryTransformerCoil():
    
    def __init__(self
                , nominal_voltage
                , rated_power
                , connection_type
                , voltage_limit
                # , I1 # The current which controls voltage of CCVS
                # , I2 # The current which flows through the node
                ):
        self.nominal_voltage = nominal_voltage
        self.rated_power = rated_power
        self.connection_type = connection_type
        self.voltage_limit = voltage_limit

        self.phase_coils = {}

    # def stamp_primal(self, Y, J, v_previous, tx_factor, state):
    #     for phase_coil in self.phase_coils:
    #         phase_coil.collect_Y_stamps(state)
            