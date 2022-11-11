
from .base import (
    DiTToHasTraits,
    Float,
    Unicode,
    Any,
    Int,
    List,
    Bool,
    observe,
    Instance,
)



class Wire(DiTToHasTraits):
    def __init__(self, model, *args, **kwargs):
        super().__init__(model, *args, **kwargs)

        self.phase = None
        self.diameter = None
        self.gmr = None
        self.resistance = None
        self.insulation_thickness = None
        self.ampacity = None
        self.emergency_ampacity = None

        # Concentric Neutral Specific
        # This section should be used to model the Wire object as a concentric neutral cable
        # If the wire is a basic bare conductor, leave undefined.
        self.concentric_neutral_gmr = None
        self.concentric_neutral_resistance = None
        self.concentric_neutral_diameter = None
        self.concentric_neutral_outside_diameter = None
        self.concentric_neutral_nstrand = None

    nameclass = Unicode(
        help="""The nameclass (e.g. 1/0_ACSR) of the wire""", default_value=None
    )
    X = Float(
        help="""The horizontal placement of the wire on a cross section of the line w.r.t. some point of reference (typically one wire on the configuration)""",
        default_value=None,
    )
    Y = Float(
        help="""The vertical placement above (or below) ground of the wire on a cross section of the line w.r.t. some point of reference (typically one wire on the configuration)""",
        default_value=None,
    )
    is_fuse = Bool(
        help="""This flag indicates whether or not this wire is also a fuse""",
        default_value=None,
    )
    is_switch = Bool(
        help="""This flag indicates whether or not this wire is also a switch""",
        default_value=None,
    )
    is_open = Bool(
        help="""This flag indicates whether or not the line is open (if it is a switch/fuse/breaker/recloser/sectionalizer/network protector).""",
        default_value=None,
    )
    # Modification: Nicolas Gensollen (June 2018)
    # fuse_limit --> interrupting_rating (more generic)
    interrupting_rating = Float(
        help="""The maximum current that can pass through the wire before the equipment disconnects.""",
        default_value=None,
    )

    ###############################################################

    # Modification: Nicolas Gensollen (December 2017)
    # Drop flag is used if we created objects in the reader that we do not want to output.
    # This is much faster than looping over objects to remove them in a pre/post-processing step
    drop = Bool(
        help="""Set to 1 if the object should be dropped in the writing process. Otherwise leave 0.""",
        default_value=False,
    )

    # Modification: Nicolas (December 2017)
    # Add a is_recloser attribute as an easy and quick way to handle reclosers in DiTTo
    is_recloser = Bool(
        help="""This flag indicates whether or not this wire is also a recloser""",
        default_value=None,
    )

    # Modification: Nicolas (January 2018)
    is_breaker = Bool(
        help="""This flag indicates whether or not this wire is also a recloser""",
        default_value=None,
    )

    # Modification: Nicolas (June 2018)
    is_network_protector = Bool(
        help="""This flag indicates whether or not this wire is also a network protector.""",
        default_value=None,
    )

    # Modification: Nicolas (August 2018)
    is_sectionalizer = Bool(
        help="""This flag indicates whether or not this wire is also a sectionalizer.""",
        default_value=None,
    )

    def build(self, model):
        self._model = model
        pass
