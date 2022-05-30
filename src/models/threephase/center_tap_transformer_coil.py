from anoeds.models.edge import Edge

class CenterTapTransformerCoil(Edge):
    
    def __init__(self
                , nominal_voltage
                , rated_power
                , connection_type
                , voltage_limit
                , resistance = None
                , reactance = None
                , edge_id = None
                ):
        super().__init__(edge_id)
        self.nominal_voltage = nominal_voltage
        self.rated_power = rated_power
        self.connection_type = connection_type
        self.voltage_limit = voltage_limit
        self.resistance = resistance
        self.reactance = reactance