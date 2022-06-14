class PowerFlowSettings:
    def __init__(self, tolerance = 1E-05, max_iters = 1000, voltage_limiting = False, debug = False, flat_start = False, tx_stepping = False, infeasibility_analysis = False) -> None:
        self.tolerance = tolerance
        self.max_iters = max_iters
        self.voltage_limiting = voltage_limiting
        self.debug = debug
        self.flat_start = flat_start
        self.tx_stepping = tx_stepping
        self.infeasibility_analysis = infeasibility_analysis