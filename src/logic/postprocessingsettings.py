class PostProcessingSettings:
    def __init__(
        self,
        loadfile_name = None,
        loadfile_start = None,
        loadfile_end = None
        ) -> None:
        self.loadfile_name = loadfile_name
        self.loadfile_start = int(loadfile_start or 0)
        self.loadfile_end = int(loadfile_end or 0)