
from ditto.readers.gridlabd.read import compute_secondary_matrix

class WireTest:
    def __init__(self, resistance, gmr, phase, diameter, insulation_thickness) -> None:
        self.resistance = resistance
        self.gmr = gmr
        self.phase = phase
        self.diameter = diameter
        self.insulation_thickness = insulation_thickness

def test_compute_secondary_matrix():
    wire_list = [
        WireTest(0.973, 0.0111, "1", 0.368, 0.08),
        WireTest(0.973, 0.0111, "2", 0.368, 0.08),
        WireTest(0.973, 0.0111, "N", 0.368, 0.08)
    ]

    impedence_matrix = compute_secondary_matrix(wire_list, kron_reduce=False)

    assert True
