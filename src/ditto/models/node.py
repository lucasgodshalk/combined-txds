from .base import (
    DiTToHasTraits,
)

class Node(DiTToHasTraits):
    def __init__(self, model, *args, **kwargs):
        super().__init__(model, *args, **kwargs)

        self.name = None
        self.nominal_voltage = None
        self.phases = None
        self.is_delta = None
        self.is_triplex = None
        self.triplex_phase = None
        self.parent = None
        self.connecting_element = None

        self.positions = None

        # Modification: Nicolas (December 2017)
        # Multiple feeder support. Each element keeps track of the name of the substation it is connected to, as well as the name of the feeder.
        # I think we need both since a substation might have multiple feeders attached to it.
        # These attributes are filled once the DiTTo model has been created using the Network module
        self.substation_name = None

        self.feeder_name = None

        # Modification: Tarek (April 2018)
        # Support for substation connection points. These identify if the node connects the substation to a feeder or high voltage source
        self.is_substation_connection = None

        # Modification: Nicolas (May 2018)
        self.is_substation = False

        self.setpoint = None

    def build(self, model):
        self._model = model