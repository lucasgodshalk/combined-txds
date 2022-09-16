
import math
import numpy as np
from logic.powerflow import FilePowerFlow
from logic.powerflowsettings import PowerFlowSettings
from test_threephase_basic import get_glm_case_file
import cmath
from ditto.readers.gridlabd.read import compute_triplex_impedance_matrix, compute_underground_capacitance

def test_ieee_four_bus_overhead_4_wire():
    glmpath = get_glm_case_file("ieee_four_bus")
    powerflow = FilePowerFlow(glmpath, PowerFlowSettings())

    branch = powerflow.network.lines[0]

    Z_expected = np.array([
        [0.4576+1.0780j, 0.1559+0.5017j, 0.1535+0.3849j],
        [0.1559+0.5017j, 0.4666+1.0482j, 0.1580+0.4236j],
        [0.1535+0.3849j, 0.1580+0.4236j, 0.4615+1.0651j]
    ])

    #need to convert impedances to ohm/mile
    assert np.allclose(np.abs(branch.impedances / .3787879), np.abs(Z_expected), atol=1e-3)

def test_ieee_four_bus_overhead_3_wire():
    glmpath = get_glm_case_file("ieee_four_bus_delta_delta_transformer")
    powerflow = FilePowerFlow(glmpath, PowerFlowSettings())

    branch = powerflow.network.lines[0]

    Z_expected = np.array([
        [0.4013+1.4133j, 0.0953+0.8515j, 0.0953+0.7266j],
        [0.0953+0.8515j, 0.4013+1.4133j, 0.0953+0.7802j],
        [0.0953+0.7266j, 0.0953+0.7802j, 0.4013+1.4133j]
    ])

    #need to convert impedances to ohm/mile
    #todo: tighten tolerance on this. still slightly off.
    assert np.allclose(np.abs(branch.impedances / .3787879), np.abs(Z_expected), atol=2e-3)

class WireTest:
    def __init__(
        self, 
        phase, 
        resistance=None, 
        gmr=None, 
        overhead_diameter=None, 
        insulation_thickness=None,
        outer_diameter=None,
        concentric_neutral_diameter=None,
        shield_gmr=None,
        conductor_diameter=None,
        concentric_neutral_nstrand=None,
        num_strands=None
        ):
        self.phase = phase

        self.resistance = resistance
        self.gmr = gmr
        self.diameter = overhead_diameter
        self.insulation_thickness = insulation_thickness
        self.outer_diameter = outer_diameter
        self.concentric_neutral_diameter = concentric_neutral_diameter
        self.shield_gmr = shield_gmr
        self.conductor_diameter = conductor_diameter
        self.concentric_neutral_nstrand = concentric_neutral_nstrand
        self.concentric_neutral_nstrand = num_strands

def test_compute_triplex_impedance_matrix():
    wire_list = [
        WireTest(phase="1", resistance=0.48, gmr=0.0158, overhead_diameter=0.522, insulation_thickness=0.08),
        WireTest(phase="2", resistance=0.48, gmr=0.0158, overhead_diameter=0.522, insulation_thickness=0.08),
        WireTest(phase="N", resistance=0.48, gmr=0.0158, overhead_diameter=0.522, insulation_thickness=0.08),
    ]

    impedence = compute_triplex_impedance_matrix(wire_list, kron_reduce=False)

    assert cmath.isclose(impedence[0][0], complex(0.5753, 1.4660), abs_tol=1e-3)
    assert cmath.isclose(impedence[0][1], complex(0.0953, 1.31067), abs_tol=1e-3)
    assert cmath.isclose(impedence[0][2], complex(0.0953, 1.32581), abs_tol=1e-3)

def test_computer_underground_capacitance():
    R_b = 0.631
    neutral_diameter = 0.0641
    phase_diameter = 0.567
    outer_diameter = R_b*2 + neutral_diameter
    num_strands = 13

    wire_list = [
        WireTest(phase="A", shield_gmr=0, concentric_neutral_diameter=neutral_diameter, conductor_diameter=phase_diameter, outer_diameter=outer_diameter, num_strands=num_strands),
        WireTest(phase="B", shield_gmr=0, concentric_neutral_diameter=neutral_diameter, conductor_diameter=phase_diameter, outer_diameter=outer_diameter, num_strands=num_strands),
        WireTest(phase="C", shield_gmr=0, concentric_neutral_diameter=neutral_diameter, conductor_diameter=phase_diameter, outer_diameter=outer_diameter, num_strands=num_strands),
        WireTest(phase="N", shield_gmr=0, concentric_neutral_diameter=neutral_diameter, conductor_diameter=phase_diameter, outer_diameter=outer_diameter, num_strands=num_strands)
    ]

    capacitance = compute_underground_capacitance(wire_list)

    compare = [[9.2980664e-5j, 0j, 0j], [0j, 9.2980664e-5j, 0j], [0j, 0j, 9.2980664e-5j]]

    assert np.allclose(capacitance, compare, atol=1e-4)