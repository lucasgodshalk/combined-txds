
import cmath
from ditto.readers.gridlabd.read import compute_secondary_matrix

class WireTest:
    def __init__(self, resistance, gmr, phase, diameter, insulation_thickness) -> None:
        self.resistance = resistance
        self.gmr = gmr
        self.phase = phase
        self.diameter = diameter
        self.insulation_thickness = insulation_thickness

def test_compute_secondary_matrix_r1_12_47_3():
    wire_list = [
        WireTest(resistance=0.48, gmr=0.0158, phase="1", diameter=0.522, insulation_thickness=0.08),
        WireTest(resistance=0.48, gmr=0.0158, phase="2", diameter=0.522, insulation_thickness=0.08),
        WireTest(resistance=0.48, gmr=0.0158, phase="N", diameter=0.522, insulation_thickness=0.08),
    ]

    impedence = compute_secondary_matrix(wire_list, kron_reduce=False)

    assert cmath.isclose(impedence[0][0], complex(0.5753, 1.4660), abs_tol=1e-3)
    assert cmath.isclose(impedence[0][1], complex(0.0953, 1.31067), abs_tol=1e-3)
    assert cmath.isclose(impedence[0][2], complex(0.0953, 1.32581), abs_tol=1e-3)
