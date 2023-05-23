class TimeSeriesSettings:
    def __init__(
        self,
        loadfile_name = None,
        loadfile_start = None,
        loadfile_end = None,
        artificialswingbus = None,
        negativeloads = None,
        loadfactor = None,
        select_island = False,
        outputfile = None
        ) -> None:
        self.loadfile_name = loadfile_name
        self.loadfile_start = int(loadfile_start or 0)
        self.loadfile_end = int(loadfile_end or 0)
        self.artificialswingbus = artificialswingbus
        self.negativeloads = negativeloads
        self.loadfactor = loadfactor
        self.select_island = select_island
        self.outputfile = outputfile