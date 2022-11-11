
from .base import (
    DiTToHasTraits,
    Float,
    Complex,
    Unicode,
    Any,
    Int,
    List,
    observe,
    Instance,
    Bool,
)

from .position import Position


class Line(DiTToHasTraits):
    def __init__(self, model, *args, **kwargs):
        super().__init__(model, *args, **kwargs)

        self.name = None
        self.phases = None
        self.nominal_voltage = None
        self.line_type = None
        self.length = None

        self.from_element = None
        self.to_element = None

        self.is_fuse = None
        self.is_switch = None

        self.wires = None

        self.impedance_matrix = None
        self.capacitance_matrix = None

        self.current_limit = None

    from_element_connection_index = Int(
        help="""Index of the position in the node that the 'from' end of the line connects to (e.g. for a long bus)""",
        default_value=None,
    )
    to_element_connection_index = Int(
        help="""Index of the position in the node that the 'to' end of the line connects to (e.g. for a long bus)""",
        default_value=None,
    )

    is_banked = Bool(
        help="""This flag indicates whether or not the switch is banked. If this is true, the switch objects are controlled together""",
        default_value=None,
    )
    faultrate = Float(
        help="""The number of faults that occur per year""", default_value=None
    )
    positions = List(
        Instance(Position),
        help="""This parameter is a list of positional points describing the line. The positions are objects containing elements of long, lat and elevation. The points can be used to map the position of the line.  """,
        default_value=None,
    )

    # Modification: Nicolas (December 2017)
    # Multiple feeder support. Each element keeps track of the name of the substation it is connected to, as well as the name of the feeder.
    # I think we need both since a substation might have multiple feeders attached to it.
    # These attributes are filled once the DiTTo model has been created using the Network module
    substation_name = Unicode(
        help="""The name of the substation to which the object is connected.""",
        default_value=None,
    )
    feeder_name = Unicode(
        help="""The name of the feeder the object is on.""", default_value=None
    )

    # Modification: Nicolas (December 2017)
    # Add a is_recloser attribute as an easy and quick way to handle reclosers in DiTTo
    is_recloser = Bool(
        help="""This flag indicates whether or not the line is also a recloser""",
        default_value=None,
    )

    # Modification: Nicolas (January 2018)
    is_breaker = Bool(
        help="""This flag indicates whether or not the line is also a breaker""",
        default_value=None,
    )

    # Modification: Nicolas (March 2018)
    is_sectionalizer = Bool(
        help="""This flag indicates whether or not the line is also a sectionalizer""",
        default_value=None,
    )

    # Modification: Nicolas (March 2018)
    nameclass = Unicode(help="""Nameclass of the line object.""", default_value=None)

    # Modification: Nicolas (May 2018)
    is_substation = Bool(
        help="""Flag that indicates wheter the element is inside a substation or not.""",
        default_value=False,
    )

    # Modification: Nicolas (June 2018)
    is_network_protector = Bool(
        help="""This flag indicates whether or not the line is also a network protector.""",
        default_value=None,
    )

    def build(
        self,
        model,
        Asset=None,
        Line=None,
        ACLineSegment=None,
        PSRType=None,
        baseVoltage=None,
        wireSpacingInfo=None,
        Location=None,
        Terminal1=None,
        Terminal2=None,
    ):

        pass


#
#        self._model = model
#
#        if Line is None:
#            self._line = self._model.env.Line()
#        else:
#            self._line = Line
#
#        if Asset is None:
#            self._asset = self._model.env.Asset()
#        else:
#            self._asset=Asset
#        self._asset.PowerSystemResources = self._asset.PowerSystemResources + (self._line, )
#
#        if ACLineSegment is None:
#            self._acls = self._model.env.ACLineSegment()
#        else:
#            self._acls = ACLineSegment
#        self._line.Equipments = self._line.Equipments + (self._acls, )
#        self._acls.EquipmentContainer = self._line
#
#        if baseVoltage is None:
#            self._bv = self._model.env.BaseVoltage()
#        else:
#            self._bv = baseVoltage
#        self._acls.BaseVoltage = self._bv
#        self._bv.ConductingEquipment = self._bv.ConductingEquipment + (self._acls, )
#
#        if PSRType is None:
#            self._psr = self._model.env.PSRType()
#        else:
#            self._psr = PSRType
#        self._acls.PSRType = self._psr
#        self._psr.PowerSystemResources = self._psr.PowerSystemResources + (self._acls, )
#
#        if wireSpacingInfo is None:
#            self._wsi = self._model.env.WireSpacingInfo()
#        else:
#            self._wsi = wireSpacingInfo
#        self._asset.AssetInfo = self._wsi
#        self._wsi.Assets = self._wsi.Assets + (self._asset, )
#
#        if Location is None:
#            self._loc = self._model.env.Location()
#        else:
#            self._loc = Location
#        self._asset.Location = self._loc
#        self._loc.Assets = self._loc.Assets + (self._asset, )
#
#        if Terminal1 is None:
#            self._t1 = self._model.env.Terminal()
#        else:
#            self._t1 = Terminal1
#
#        if Terminal2 is None:
#            self._t2 = self._model.env.Terminal()
#        else:
#            self._t2 = Terminal2
#
#        self._model.model_store[self.name] = self
#        self._model.model_store[self.name] = self
#
#    @observe('name', type='change')
#    def _set_name(self, bunch):
#        self._line.name = bunch['new']
#
#    @observe('name', type='fetch')
#    def _get_name(self, bunch):
#        return self._line.name
#
#    @observe('line_type', type='change')
#    def _set_line_type(self, bunch):
#        self._psr.aliasName = bunch['new']
#
#    @observe('line_type', type='fetch')
#    def _get_line_type(self, bunch):
#        return self._psr.aliasName
#
#    @observe('nominal_voltage', type='change')
#    def _set_nominal_voltage(self, bunch):
#        self._bv.nominal_voltage = self._model.env.Voltage(value=bunch['new'])
#
#    @observe('nominal_voltage', type='fetch')
#    def _get_nominal_voltage(self, bunch):
#        if self._bv.nominal_voltage is None:
#            return None
#        return self._bv.nominalVoltage.value
#
#    @observe('length', type='change')
#    def _set_length(self, bunch):
#        self._acls.length = self._model.env.Length(value=bunch['new'])
#
#    @observe('length', type='fetch')
#    def _get_length(self, bunch):
#        if self._acls.length is None:
#            return None
#        return self._acls.length.value
#
#    @observe('resistance', type='change')
#    def _set_resistance(self, bunch):
#        self._acls.r = self._model.env.Resistance(value=bunch['new'])
#
#    @observe('resistance', type='fetch')
#    def _get_resistance(self, bunch):
#        if self._acls.r is None:
#            return None
#        return self._acls.r.value
#
#    @observe('resistance0', type='change')
#    def _set_resistance0(self, bunch):
#        self._acls.r0 = self._model.env.Resistance(value=bunch['new'])
#
#    @observe('resistance0', type='fetch')
#    def _get_resistance0(self, bunch):
#        if self._acls.r0 is None:
#            return None
#        return self._acls.r0.value
#
#    @observe('reactance', type='change')
#    def _set_reactance(self, bunch):
#        self._acls.x = self._model.env.Reactance(value=bunch['new'])
#
#    @observe('reactance', type='fetch')
#    def _get_reactance(self, bunch):
#        if self._acls.x is None:
#            return None
#        return self._acls.x.value
#
#    @observe('reactance0', type='change')
#    def _set_reactance0(self, bunch):
#        self._acls.x0 = self._model.env.Reactance(value=bunch['new'])
#
#    @observe('reactance0', type='fetch')
#    def _get_reactance0(self, bunch):
#        if self._acls.x0 is None:
#            return None
#        return self._acls.x0.value
#
#    @observe('susceptance', type='change')
#    def _set_susceptance(self, bunch):
#        self._acls.bch = self._model.env.Susceptance(value=bunch['new'])
#
#    @observe('susceptance', type='fetch')
#    def _get_susceptance(self, bunch):
#        if self._acls.bch is None:
#            return None
#        return self._acls.bch.value
#
#    @observe('susceptance0', type='change')
#    def _set_susceptance0(self, bunch):
#        self._acls.b0ch = self._model.env.Susceptance(value=bunch['new'])
#
#    @observe('susceptance0', type='fetch')
#    def _get_susceptance0(self, bunch):
#        if self._acls.b0ch is None:
#            return None
#        return self._acls.b0ch.value
#
#    @observe('conductance', type='change')
#    def _set_conductance(self, bunch):
#        self._acls.gch = self._model.env.Conductance(value=bunch['new'])
#
#    @observe('conductance', type='fetch')
#    def _get_conductance(self, bunch):
#        if self._acls.gch is None:
#            return None
#        return self._acls.gch.value
#
#    @observe('conductance0', type='change')
#    def _set_conductance0(self, bunch):
#        self._acls.g0ch = self._model.env.Conductance(value=bunch['new'])
#
#    @observe('conductance0', type='fetch')
#    def _get_conductance0(self, bunch):
#        if self._acls.g0ch is None:
#            return None
#        return self._acls.g0ch.value
#
#    @observe('max_temperature', type='change')
#    def _set_max_temperature(self, bunch):
#        self._acls.shortCircuitEndTemperature = self._model.env.Temperature(value=bunch['new'])
#
#    @observe('max_temperature', type='fetch')
#    def _get_max_temperature(self, bunch):
#        if self._acls.shortCircuitEndTemperature is None:
#            return None
#        return self._acls.shortCircuitEndTemperature.value
#
#    @observe('wires', type='change')
#    def _set_wires(self, bunch):
#        wire_list = bunch['new']
#        self._wsi.WirePositions=[]
#        for wire in wire_list:
#            wp = self._model.env.WirePosition()
#            wp.phase = wire.phase
#            wp.xCoord = self._model.Displacement(value=wire.X)
#            wp.yCoord = self._model.Displacement(value=wire.Y)
#            wp.WireSpacingInfo = self._wsi
#            self._wsi.WirePositions = self._wsi.WirePositions + (wp, )
#
#    @observe('wires', type='fetch')
#    def _get_wires(self, bunch):
#        wires = []
#        for wp in self._wsi.WirePositions:
#            wire = Wire()
#            wire.phase = wp.phase
#            wire.X = wp.XCoord.value
#            wire.Y = wp.YCoord.value
#            wires.append(wire)
#        return wires
#
#    @observe('positions', type='change')
#    def _set_positions(self, bunch):
#        position_list = bunch['new']
#        self._loc.PositionPoints=[]
#        for position in position_list:
#            p = self._model.env.PositionPoint()
#            p.xPosition = position.long
#            p.yPosition = position.lat
#            p.zPosition = position.elevation
#            p.Location = self._loc
#            self._loc.PositionPoints = self._loc.PositionPoints + (p, )
#
#    @observe('positions', type='fetch')
#    def _get_positions(self, bunch):
#        positions = []
#        for p in self._loc.PositionPoints:
#            position = Position()
#            position.lat = p.xPosition
#            position.long = p.yPosition
#            position.elevation = p.zPosition
#            positions.append(position)
#        return positions
#
#    @observe('from_element', type='change')
#    def _set_from_element(self, bunch):
#        self._t1.ConnectivityNode = bunch['new']
#        self._t1.ConductingEquipment = self._acls
#
#    @observe('from_element', type='fetch')
#    def _get_from_element(self, bunch):
#        return self._t1.ConnectivityNode
#
#    @observe('to_element', type='change')
#    def _set_to_element(self, bunch):
#        self._t2.ConnectivityNode = bunch['new']
#        self._t2.ConductingEquipment = self._acls
#
#    @observe('to_element', type='fetch')
#    def _get_to_element(self, bunch):
#        return self._t2.ConnectivityNode
