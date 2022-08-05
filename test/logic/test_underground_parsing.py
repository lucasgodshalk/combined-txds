
import numpy as np
from logic.powerflow import FilePowerFlow
from logic.powerflowsettings import PowerFlowSettings
from test_threephase import get_glm_case_file


def test_underground_Z_GC_12_47_1_ul_1():
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