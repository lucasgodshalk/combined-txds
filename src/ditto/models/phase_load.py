class PhaseLoad():
    def __init__(self):
        self.phase = None
        self.p = None
        self.q = None
        self.z = None
        self.i_const = complex(0, 0)

        # Modification: Nicolas (August 2017)
        # OpenDSS has 8 different load models. Without this field there is no way to capture
        # this information in DiTTo ==> Only constant P&Q and Zipload would be considered
        # Note: use_zip can probably be removed since it is equivalent to model=8
        self.model = 1

        # TO REMOVE??
        self.use_zip = 0

        # Modification: Nicolas Gensollen (December 2017)
        # Drop flag is used if we created objects in the reader that we do not want to output.
        # This is much faster than looping over objects to remove them in a pre/post-processing step
        self.drop = False

        self.ppercentcurrent = None
        self.qpercentcurrent = None
        self.ppercentpower = None
        self.qpercentpower = None
        self.ppercentimpedance = None
        self.qpercentimpedance = None

    def build(self, model):
        self._model = model
