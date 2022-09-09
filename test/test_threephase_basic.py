# import pytest as pt
import cmath
import math
from logic.powerflow import FilePowerFlow
from logic.powerflowresults import PowerFlowResults
from logic.powerflowsettings import PowerFlowSettings
import os
import numpy as np
import csv

CURR_DIR = os.path.realpath(os.path.dirname(__file__))
DATA_DIR = os.path.join(CURR_DIR, "data", "three_phase")

def get_glm_case_file(casename, glm_file_name = "node.glm"):
    return os.path.join(DATA_DIR, casename, glm_file_name)

def get_gridlabd_csv_voltdump(casename):
    return os.path.join(DATA_DIR, casename, "result.csv")

def execute_glm_case(filepath, settings):
    powerflow = FilePowerFlow(filepath, settings)
    return powerflow.execute()

def load_gridlabd_csv(casename):
    filepath = get_gridlabd_csv_voltdump(casename)
    with open(filepath, newline=None) as csvfile:
        spamreader = csv.DictReader(filter(lambda row: row[0]!='#', csvfile), delimiter=',', quotechar='|')
        lookup = {}
        for row in spamreader:
            nodeName = row["node_name"]

            vA = complex(float(row["voltA_real"]), float(row["voltA_imag"]))
            vB = complex(float(row["voltB_real"]), float(row["voltB_imag"]))
            vC = complex(float(row["voltC_real"]), float(row["voltC_imag"]))

            lookup[nodeName] = (vA, vB, vC)
        
        return lookup

atol=1e-2
rtol=1e-3

def assert_busresults_gridlabdvoltdump(results: PowerFlowResults, gridlab_vdump):
    variances = []

    for busresult in results.bus_results:
        if busresult.bus.IsVirtual:
            continue

        (vA, vB, vC) = gridlab_vdump[busresult.bus.NodeName]

        expected = None
        if busresult.bus.NodePhase == "A":
            expected = vA
        elif busresult.bus.NodePhase == "B":
            expected = vB
        elif busresult.bus.NodePhase == "C":
            expected = vC
        elif busresult.bus.NodePhase == "1":
            expected = vA
        elif busresult.bus.NodePhase == "2":
            expected = -vB
        else:
            raise Exception("Unknown phase")
        
        result_mag, expected_mag = busresult.V_mag, abs(expected)
        result_ang, expected_ang = busresult.V_deg, math.degrees(cmath.phase(expected))

        diff_mag = abs(result_mag - expected_mag)
        diff_ang = abs(result_ang - expected_ang)
        if diff_ang > 180:
            diff_ang = abs(diff_ang - 360)

        tol_mag = atol + rtol * np.abs(expected_mag)
        tol_ang = atol + rtol * np.abs(expected_ang)

        variance_mag = diff_mag - tol_mag
        variance_ang = diff_ang - tol_ang

        variance_mag_pct = math.ceil(100*variance_mag / tol_mag)
        variance_ang_pct = math.ceil(100*variance_ang / tol_ang)

        if variance_mag_pct >= variance_ang_pct:
            largest_variance = variance_mag_pct
        else:
            largest_variance = variance_ang_pct

        variances.append((largest_variance, busresult.bus, result_mag, expected_mag, result_ang, expected_ang, variance_mag_pct, variance_ang_pct))

    sorted_variances = sorted(variances, key=lambda x: x[0], reverse=True)

    largest = sorted_variances[0]

    if largest[0] > 0:
        assert False, f"Bus \"{largest[1].NodeName}:{largest[1].NodePhase}\" is at {largest[0] + 100}% of tolerance. (magnitude: {largest[2]:.5g}, {largest[3]:.5g}) (degrees: {largest[4]:.5g}, {largest[5]:.5g})"

def assert_glm_case_gridlabd_results(casename, settings = PowerFlowSettings()):
    filepath = get_glm_case_file(casename)
    results = execute_glm_case(filepath, settings)
    if not results.is_success:
        raise Exception(f"Failed to converge (iterations: {results.iterations}, tx_percent: {results.tx_percent}")
    comparison = load_gridlabd_csv(casename)
    assert_busresults_gridlabdvoltdump(results, comparison)

def test_balanced_stepdown_D_D():
    assert_glm_case_gridlabd_results("balanced_stepdown_D-D")

def test_balanced_stepdown_D_D_cap():
    assert_glm_case_gridlabd_results("balanced_stepdown_D-D_cap")

def test_ieee_four_bus():
    assert_glm_case_gridlabd_results("ieee_four_bus")

def test_just_swing():
    assert_glm_case_gridlabd_results("just_swing")

def test_swing_and_line_to_pq():
    assert_glm_case_gridlabd_results("swing_and_line_to_pq")

def test_swing_and_long_line_to_pq():
    assert_glm_case_gridlabd_results("swing_and_long_line_to_pq")

def test_swing_and_long_ul_to_pq():
    assert_glm_case_gridlabd_results("swing_and_long_ul_to_pq")
    
def test_swing_and_underground_lines_to_pq():
    assert_glm_case_gridlabd_results("swing_and_underground_lines_to_pq")

def test_swing_2lines_load():
    assert_glm_case_gridlabd_results("swing_2lines_load")

def test_ieee_four_bus_resistive():
    assert_glm_case_gridlabd_results("ieee_four_bus_resistive")
    
def test_balanced_stepdown_grY_grY():
    assert_glm_case_gridlabd_results("balanced_stepdown_grY_grY")
    
def test_ieee_four_bus_higher_transformer_impedance():
    assert_glm_case_gridlabd_results("ieee_four_bus_higher_transformer_impedance")
    
def test_ieee_four_bus_transformer_shunt_impedance():
    assert_glm_case_gridlabd_results("ieee_four_bus_transformer_shunt_impedance")

# This is known to not be as close as desired, but it is in agreement with Amrit's code.
def test_ieee_four_bus_long_lines():
    assert_glm_case_gridlabd_results("ieee_four_bus_long_lines")

def test_connected_transformer():
    assert_glm_case_gridlabd_results("connected_transformer")

def test_just_two_transformers():
    assert_glm_case_gridlabd_results("just_two_transformers")

def test_two_transformers():
    assert_glm_case_gridlabd_results("two_transformers")

def test_three_transformers_with_lines():
    assert_glm_case_gridlabd_results("three_transformers_with_lines")

def test_three_transformers():
    assert_glm_case_gridlabd_results("three_transformers")
    
def test_kersting_example_4_1():
    assert_glm_case_gridlabd_results("kersting_example_4_1")

def test_kersting_example_4_2():
    assert_glm_case_gridlabd_results("kersting_example_4_2")

def test_underground_lines_and_transformers():
    assert_glm_case_gridlabd_results("underground_lines_and_transformers")

def test_ieee_four_bus_underground_spaced():
    assert_glm_case_gridlabd_results("ieee_four_bus_underground_spaced")

def test_ieee_four_bus_underground():
    assert_glm_case_gridlabd_results("ieee_four_bus_underground")
    
def test_ieee_four_bus_underground_step_up():
    assert_glm_case_gridlabd_results("ieee_four_bus_underground_step_up")

def test_ieee_four_bus_underground_long_lines():
    assert_glm_case_gridlabd_results("ieee_four_bus_underground_long_lines")

def test_ieee_four_bus_switch():
    assert_glm_case_gridlabd_results("ieee_four_bus_switch")

def test_ieee_four_bus_fuse():
    assert_glm_case_gridlabd_results("ieee_four_bus_fuse")

def test_ieee_four_bus_cap():
    assert_glm_case_gridlabd_results("ieee_four_bus_cap")

def test_ieee_four_bus_unbalanced_pq_load():
    assert_glm_case_gridlabd_results("ieee_four_bus_unbalanced_pq_load")

def test_load_within_meter():
    assert_glm_case_gridlabd_results("load_within_meter")

def test_transformer_to_meter():
    assert_glm_case_gridlabd_results("transformer_to_meter")

def test_regulator_node_load():
    assert_glm_case_gridlabd_results("regulator_node_load")

def test_regulatorB_node_load():
    assert_glm_case_gridlabd_results("regulatorB_node_load")

def test_ieee_thirteen_bus_pq_top_right():
    assert_glm_case_gridlabd_results("ieee_thirteen_bus_pq_top_right")

def test_two_regulators():
    assert_glm_case_gridlabd_results("two_regulators")

def test_regulator_lower_impedance_transformer_load():
    assert_glm_case_gridlabd_results("regulator_lower_impedance_transformer_load")

def test_regulator_higher_impedance_transformer_load():
    assert_glm_case_gridlabd_results("regulator_higher_impedance_transformer_load")

def test_regulator_ol():
    assert_glm_case_gridlabd_results("regulator_ol")

def test_regulator_overhead_line_transformer_load():
    assert_glm_case_gridlabd_results("regulator_overhead_line_transformer_load")
    
def test_regulator_overhead_lines():
    assert_glm_case_gridlabd_results("regulator_overhead_lines")
    
def test_gc_12_47_1_only_overhead_lines():
    assert_glm_case_gridlabd_results("gc_12_47_1_only_overhead_lines")

def test_regulator_overhead_line_underground_line():
    assert_glm_case_gridlabd_results("regulator_overhead_line_underground_line")

def test_regulator_ul():
    assert_glm_case_gridlabd_results("regulator_ul")

def test_regulator_ul_xfmr():
    assert_glm_case_gridlabd_results("regulator_ul_xfmr")

def test_regulator_ul_xfmr_ul():
    assert_glm_case_gridlabd_results("regulator_ul_xfmr_ul")

def test_gc_12_47_1_pared_down_no_regulator():
    assert_glm_case_gridlabd_results("gc_12_47_1_pared_down_no_regulator")

def test_gc_12_47_1_somewhat_pared_down_no_regulator():
    assert_glm_case_gridlabd_results("gc_12_47_1_somewhat_pared_down_no_regulator")

def test_gc_12_47_1_no_reg():
    assert_glm_case_gridlabd_results("gc_12_47_1_no_reg")
    
def test_gc_12_47_1_xfmr_as_reg():
    assert_glm_case_gridlabd_results("gc_12_47_1_xfmr_as_reg")

def test_gc_12_47_1_further_simplified():
    assert_glm_case_gridlabd_results("gc_12_47_1_further_simplified")

def test_gc_12_47_1_simplified():
    assert_glm_case_gridlabd_results("gc_12_47_1_simplified")

def test_gc_12_47_1_subset():
    assert_glm_case_gridlabd_results("gc_12_47_1_subset")

def test_gc_12_47_1_no_cap():
    assert_glm_case_gridlabd_results("gc_12_47_1_no_cap")

def test_center_tap_xfmr():
    assert_glm_case_gridlabd_results("center_tap_xfmr")

def test_regulator_center_tap_xfmr():
    assert_glm_case_gridlabd_results("regulator_center_tap_xfmr")
    
def test_triplex_load_class():
    assert_glm_case_gridlabd_results("triplex_load_class")

def test_basic_triplex_network():
    assert_glm_case_gridlabd_results("basic_triplex_network")

# Requires support for delta connected transformers (not yet supported)
def test_ieee_four_bus_delta_delta_transformer():
    assert_glm_case_gridlabd_results("ieee_four_bus_delta_delta_transformer")

def test_ieee_thirteen_bus_Y_Y_pq_loads_top_half():
    assert_glm_case_gridlabd_results("ieee_thirteen_bus_Y_Y_pq_loads_top_half")

# Requires support for delta-connected loads, (not yet supported)
def test_ieee_thirteen_bus_core():
    assert_glm_case_gridlabd_results("ieee_13_core")

# Requires support for delta loads (not yet supported)
def test_ieee_thirteen_bus_pq_loads_top_half():
    assert_glm_case_gridlabd_results("ieee_thirteen_bus_pq_loads_top_half")

# Requires support for delta loads (not yet supported)
def test_ieee_thirteen_bus_pq():
    assert_glm_case_gridlabd_results("ieee_13_pq_loads")

def test_ieee_thirteen_bus_overhead():
    assert_glm_case_gridlabd_results("ieee_13_node_overhead_nr")

# Requires resistive loads, current loads, and IP loads
def test_ieee_thirteen_bus():
    assert_glm_case_gridlabd_results("ieee_13_node_nr")

def test_kersting_example_11_1():
    assert_glm_case_gridlabd_results("kersting_example_11_1")

def test_kersting_example_11_1_altered():
    assert_glm_case_gridlabd_results("kersting_example_11_1_altered")

def test_kersting_example_11_1_altered_more():
    assert_glm_case_gridlabd_results("kersting_example_11_1_altered_more")

def test_kersting_example_11_2():
    assert_glm_case_gridlabd_results("kersting_example_11_2")

def test_kersting_example_11_2_altered():
    assert_glm_case_gridlabd_results("kersting_example_11_2_altered")

def test_kersting_example_11_2_altered_more():
    assert_glm_case_gridlabd_results("kersting_example_11_2_altered_more")

def test_3phasesource_CT_line_load():
    assert_glm_case_gridlabd_results("3phasesource_CT_line_load")

def test_center_tap_xfmr_and_triplex_line():
    assert_glm_case_gridlabd_results("center_tap_xfmr_and_triplex_line")

def test_regulator_center_tap_xfmr_and_triplex_line():
    assert_glm_case_gridlabd_results("regulator_center_tap_xfmr_and_triplex_line")

def test_center_tap_xfmr_and_triplex_load():
    assert_glm_case_gridlabd_results("center_tap_xfmr_and_triplex_load")

def test_center_tap_xfmr_and_single_line_to_load():
    assert_glm_case_gridlabd_results("center_tap_xfmr_and_single_line_to_load")

def test_center_tap_xfmr_and_line_to_load():
    assert_glm_case_gridlabd_results("center_tap_xfmr_and_line_to_load")

def test_regulator_center_tap_xfmr_and_line_to_load():
    assert_glm_case_gridlabd_results("regulator_center_tap_xfmr_and_line_to_load")
    
def test_triplex_load_class():
    assert_glm_case_gridlabd_results("triplex_load_class")

def test_unbalanced_triplex_load():
    assert_glm_case_gridlabd_results("unbalanced_triplex_load")