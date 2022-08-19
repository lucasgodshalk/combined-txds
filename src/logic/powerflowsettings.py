class PowerFlowSettings:
    def __init__(
        self, 
        tolerance = 1E-05, 
        max_iters = 50, 
        voltage_limiting = False, 
        debug = False, 
        flat_start = False, 
        tx_stepping = False, 
        infeasibility_analysis = False,
        dump_matrix = False,
        device_control = True,
        loadfile_name = None,
        loadfile_start = 0
        ) -> None:
        self.tolerance = tolerance
        self.max_iters = max_iters
        self.voltage_limiting = voltage_limiting
        self.debug = debug
        self.flat_start = flat_start
        self.tx_stepping = tx_stepping
        self.infeasibility_analysis = infeasibility_analysis
        self.dump_matrix = dump_matrix
        self.device_control = device_control
        self.loadfile_name = loadfile_name
        self.loadfile_start = loadfile_start