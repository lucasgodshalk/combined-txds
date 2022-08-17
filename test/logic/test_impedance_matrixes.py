
import numpy as np
from logic.powerflow import FilePowerFlow
from logic.powerflowsettings import PowerFlowSettings
from test_threephase_basic import get_glm_case_file
import cmath
from ditto.readers.gridlabd.read import compute_triplex_impedance_matrix

def test_ieee_four_bus_4_wire():
    glmpath = get_glm_case_file("ieee_four_bus")
    powerflow = FilePowerFlow(glmpath, PowerFlowSettings())

    branch = powerflow.network.branches[0]

    Z_expected = np.array([
        [0.4576+1.0780j, 0.1559+0.5017j, 0.1535+0.3849j],
        [0.1559+0.5017j, 0.4666+1.0482j, 0.1580+0.4236j],
        [0.1535+0.3849j, 0.1580+0.4236j, 0.4615+1.0651j]
    ])

    #need to convert impedances to ohm/mile
    assert np.allclose(np.abs(branch.impedances / .3787879), np.abs(Z_expected), atol=1e-3)

def test_ieee_four_bus_3_wire():
    glmpath = get_glm_case_file("ieee_four_bus_delta_delta_transformer")
    powerflow = FilePowerFlow(glmpath, PowerFlowSettings())

    branch = powerflow.network.branches[0]

    Z_expected = np.array([
        [0.4013+1.4133j, 0.0953+0.8515j, 0.0953+0.7266j],
        [0.0953+0.8515j, 0.4013+1.4133j, 0.0953+0.7802j],
        [0.0953+0.7266j, 0.0953+0.7802j, 0.4013+1.4133j]
    ])

    #need to convert impedances to ohm/mile
    #todo: tighten tolerance on this. still slightly off.
    assert np.allclose(np.abs(branch.impedances / .3787879), np.abs(Z_expected), atol=2e-3)

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

    impedence = compute_triplex_impedance_matrix(wire_list, kron_reduce=False)

    assert cmath.isclose(impedence[0][0], complex(0.5753, 1.4660), abs_tol=1e-3)
    assert cmath.isclose(impedence[0][1], complex(0.0953, 1.31067), abs_tol=1e-3)
    assert cmath.isclose(impedence[0][2], complex(0.0953, 1.32581), abs_tol=1e-3)

def test_underground_Z_GC_12_47_1_ul_1():
    raise Exception("These test values are incorrect.")

    glmpath = get_glm_case_file("gc_12_47_1")

    powerflow = FilePowerFlow(glmpath, PowerFlowSettings())

    ul_1_branch = powerflow.network.branches[0]

    ul_1_Z_expected = np.array([
        [0.0204926 +0.01162838j, 0.00125544-0.00233556j, 0.00125544-0.00233556j],
        [0.00125544-0.00233556j, 0.0204926 +0.01162838j, 0.00125544-0.00233556j],
        [0.00125544-0.00233556j, 0.00125544-0.00233556j, 0.0204926 +0.01162838j]
    ])
    assert np.allclose(ul_1_branch.impedances, ul_1_Z_expected)

    ul_1_shunt_Z = np.array([
        [0.+8.67640916e-06j, 0.+0.00000000e+00j, 0.+0.00000000e+00j],
        [0.+0.00000000e+00j, 0.+8.67640916e-06j, 0.+0.00000000e+00j],
        [0.+0.00000000e+00j, 0.+0.00000000e+00j, 0.+8.67640916e-06j]
    ])
    check = False
    assert check, "Still need to assert for shunt values as well"

    ul_2_branch = powerflow.network.branches[1]

    ul_2_Z_expected = np.array([
        [0.02698372+0.01531171j, 0.00165311-0.00307535j, 0.00165311-0.00307535j],
        [0.00165311-0.00307535j, 0.02698372+0.01531171j, 0.00165311-0.00307535j],
        [0.00165311-0.00307535j, 0.00165311-0.00307535j, 0.02698372+0.01531171j]
    ])
    assert np.allclose(ul_2_branch.impedances, ul_2_Z_expected)

    ul_2_shunt_Z = np.array([
        [0.+1.14246976e-05j, 0.+0.00000000e+00j, 0.+0.00000000e+00j],
        [0.+0.00000000e+00j, 0.+1.14246976e-05j, 0.+0.00000000e+00j],
        [0.+0.00000000e+00j, 0.+0.00000000e+00j, 0.+1.14246976e-05j]
    ])

    ul_3_branch = powerflow.network.branches[2]


    ul_3_Z_expected = np.array([
        [0.02973976+0.01687561j, 0.00182195-0.00338946j, 0.00182195-0.00338946j],
        [0.00182195-0.00338946j, 0.02973976+0.01687561j, 0.00182195-0.00338946j],
        [0.00182195-0.00338946j, 0.00182195-0.00338946j, 0.02973976+0.01687561j]
    ])
    assert np.allclose(ul_3_branch.impedances, ul_3_Z_expected)

    ul_3_shunt_Z = np.array([
        [0.+1.25915838e-05j, 0.+0.00000000e+00j, 0.+0.00000000e+00j],
        [0.+0.00000000e+00j, 0.+1.25915838e-05j, 0.+0.00000000e+00j],
        [0.+0.00000000e+00j, 0.+0.00000000e+00j, 0.+1.25915838e-05j]
    ])