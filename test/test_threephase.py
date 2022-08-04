# import pytest as pt
import cmath
from math import radians
import math
from logic.powerflow import FilePowerFlow
from logic.powerflowresults import PowerFlowResults
from logic.powerflowsettings import PowerFlowSettings
import os
import numpy as np
import csv

CURR_DIR = os.path.realpath(os.path.dirname(__file__))
DATA_DIR = os.path.join(CURR_DIR, "data")

def get_glm_case_file(casename, glm_file_name = "node.glm"):
    return os.path.join(DATA_DIR, casename, glm_file_name)

def get_gridlabd_csv_voltdump(casename):
    return os.path.join(DATA_DIR, casename, "result.csv")

def execute_glm_case(casename, glm_file_name = "node.glm", debug = False):
    filepath = get_glm_case_file(casename, glm_file_name)
    powerflow = FilePowerFlow(filepath, PowerFlowSettings(debug=debug))
    return powerflow.execute()

def load_gridlabd_csv(casename):
    filepath = get_gridlabd_csv_voltdump(casename)
    with open(filepath, newline='\r\n') as csvfile:
        spamreader = csv.DictReader(filter(lambda row: row[0]!='#', csvfile), delimiter=',', quotechar='|')
        lookup = {}
        for row in spamreader:
            nodeName = row["node_name"]

            vA = complex(float(row["voltA_real"]), float(row["voltA_imag"]))
            vB = complex(float(row["voltB_real"]), float(row["voltB_imag"]))
            vC = complex(float(row["voltC_real"]), float(row["voltC_imag"]))

            lookup[nodeName] = (vA, vB, vC)
        
        return lookup

atol=1e-4
rtol=1e-3

def assert_busresults_gridlabdvoltdump(results: PowerFlowResults, gridlab_vdump):
    result = []
    expected = []
    node_idx = []

    for busresult in results.bus_results:
        result.append(busresult.V_r)
        node_idx.append((f"{busresult.bus.NodeName}:{busresult.bus.NodePhase}:r", len(result)))
        result.append(busresult.V_i)
        node_idx.append((f"{busresult.bus.NodeName}:{busresult.bus.NodePhase}:i", len(result)))

        (vA, vB, vC) = gridlab_vdump[busresult.bus.NodeName]

        bus_expected = None
        if busresult.bus.NodePhase == "A":
            bus_expected = vA
        elif busresult.bus.NodePhase == "B":
            bus_expected = vB
        elif busresult.bus.NodePhase == "C":
            bus_expected = vC
        elif busresult.bus.NodePhase == "1":
            bus_expected = vA
        elif busresult.bus.NodePhase == "2":
            bus_expected = -vB
        else:
            raise Exception("Unknown phase")
        
        expected.append(bus_expected.real)
        expected.append(bus_expected.imag)

    assert_v_tolerance(np.array(result), np.array(expected))

def assert_v_tolerance(result, expected):
    diff = np.abs(result - expected)
    tol = atol + rtol * np.abs(expected)

    variance = diff - tol

    max_variance = np.max(variance)
    max_idx = np.argmax(variance)

    assert max_variance <= 0, f"Results outside tolerance. (result: {result[max_idx]:.5g}, expected: {expected[max_idx]:.5g}, tol: {tol[max_idx]:.5g}, pct of tol: {math.ceil(100*abs(variance[max_idx] / tol[max_idx])) + 100}%, index: {max_idx})"

def test_powerflowrunner_ieee_four_bus():
    results = execute_glm_case("ieee_four_bus")

    expected_v = np.array([
        7199.558000,
        0.000000,
        -3599.779000,
        -6235.000000,
        -3599.779000,
        6235.000000,
        7106.422287,
        -42.067600,
        -3606.903032,
        -6161.628479,
        -3520.343705,
        6189.706477,
        2242.742683,
        -144.807987,
        -1251.271366,
        -1892.203540,
        -1002.844346,
        2020.691679,
        1893.763615,
        -302.435080,
        -1277.965079,
        -1617.280802,
        -705.200678,
        1850.977065
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])

# Check that disconnected swing buses just return the nominal voltage.
def test_powerflowrunner_just_swing():
    results = execute_glm_case("just_swing")
    
    expected_v = np.array([2.40000000e+03,
                           0.00000000e+00,
                           -1.20000000e+03,
                           -2.07846097e+03,
                           -1.20000000e+03,
                           2.07846097e+03], dtype=float)
    assert np.allclose(results.v_final[:6], expected_v, rtol=1e-5, atol=1e-7)

def test_powerflowrunner_swing_and_line_to_pq():
    results = execute_glm_case("swing_and_line_to_pq")
    
    # Voltages at node 1, voltages at node 2
    expected_v = np.array([
         2400.        ,
            0.        ,
        -1200.        ,
        -2078.46096908,
        -1200.        ,
         2078.46096908,
         2167.809212  ,
         -129.459975  ,
        -1233.209355  ,
        -1873.096501  ,
         -973.394008  ,
         1981.430136], dtype=float)
    assert_v_tolerance(results.v_final[:12], expected_v[:12])

def test_powerflowrunner_swing_and_long_line_to_pq():
    results = execute_glm_case("swing_and_long_line_to_pq")

    # Voltages at node 1, voltages at node 2
    expected_v = np.array([
        2400.000000,
        0.000000,
        -1200.000000,
        -2078.460969,
        -1200.000000,
        2078.460969,
        1481.787249,
        -285.484828,
        -829.767885,
        -704.110354,
        -129.228599,
        1266.560786], dtype=float)
    assert_v_tolerance(results.v_final[:12], expected_v[:12])

def test_powerflowrunner_swing_and_long_ul_to_pq():
    results = execute_glm_case("swing_and_long_ul_to_pq")
    
    # Voltages at node 1, voltages at node 2
    expected_v = np.array([
        2400.000000,
        0.000000,
        -1200.000000,
        -2078.460969,
        -1200.000000,
        2078.460969,
        2159.677659,
        -118.040650,
        -1182.065031,
        -1811.315391,
        -977.612628,
        1929.356042
    ], dtype=float)
    assert_v_tolerance(results.v_final[:12], expected_v[:12])
    
def test_powerflowrunner_swing_and_underground_lines_to_pq():
    results = execute_glm_case("swing_and_underground_lines_to_pq")
    
    # Voltages at node 1, voltages at node 2
    expected_v = np.array([
        2400.000000,
        0.000000,
        -1200.000000,
        -2078.460969,
        -1200.000000,
        2078.460969,
        2309.597715,
        -39.346883,
        -1188.874258,
        -1980.496852,
        -1120.723457,
        2019.843736,
        2219.195430,
        -78.693767,
        -1177.748516,
        -1882.532735,
        -1041.446914,
        1961.226502,
        2128.793145,
        -118.040650,
        -1166.622775,
        -1784.568618,
        -962.170371,
        1902.609268,
        2038.390861,
        -157.387534,
        -1155.497033,
        -1686.604501,
        -882.893828,
        1843.992035,
        1947.988576,
        -196.734417,
        -1144.371291,
        -1588.640384,
        -803.617285,
        1785.374801
    ], dtype=float)
    assert_v_tolerance(results.v_final[:36], expected_v[:36])

def test_powerflowrunner_swing_2lines_load():
    results = execute_glm_case("swing_2lines_load")

    expected_v = np.array([
        7199.558000,
        0.000000,
        -3599.779000,
        -6235.000000,
        -3599.779000,
        6235.000000,
        7129.179318,
        -41.923931,
        -3612.334859,
        -6168.662777,
        -3526.732960,
        6208.670790,
        7058.800636,
        -83.847862,
        -3624.890719,
        -6102.325553,
        -3453.686920,
        6182.341580,
        6970.827284,
        -136.252776,
        -3640.585543,
        -6019.404024,
        -3362.379369,
        6149.430068
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])

def test_powerflowrunner_ieee_four_bus_resistive():
    results = execute_glm_case("ieee_four_bus_resistive")

    expected_v = np.array([
        7199.56,
        0.00,
        -3599.78,
        -6235.00,
        -3599.78,
        6235.00,
        7199.39,
        -0.26,
        -3599.93,
        -6234.80,
        -3599.49,
        6235.04,
        2401.63,
        -0.64,
        -1201.37,
        -2079.57,
        -1200.27,
        2080.21
    ], dtype=float)
    assert np.allclose(results.v_final[:18], expected_v[:18], rtol=1e-1)
    
def test_powerflowrunner_balanced_stepdown_grY_grY():
    results = execute_glm_case("balanced_stepdown_grY_grY")

    expected_v = np.array([
        7199.558000,
        0.000000,
        -3599.779000,
        -6235.000000,
        -3599.779000,
        6235.000000,
        7106.422287,
        -42.067600,
        -3606.903032,
        -6161.628479,
        -3520.343705,
        6189.706477,
        2242.742683,
        -144.807987,
        -1251.271366,
        -1892.203540,
        -1002.844346,
        2020.691679,
        1893.763615,
        -302.435080,
        -1277.965079,
        -1617.280802,
        -705.200678,
        1850.977065
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])
    
def test_powerflowrunner_ieee_four_bus_higher_transformer_impedance():
    results = execute_glm_case("ieee_four_bus_higher_transformer_impedance")
    
    expected_v = np.array([
        7199.558000,
        0.000000,
        -3599.779000,
        -6235.000000,
        -3599.779000,
        6235.000000,
        7080.865336,
        -47.086731,
        -3609.013913,
        -6158.078310,
        -3513.606680,
        6175.443283,
        1992.960195,
        -183.902648,
        -1185.758929,
        -1710.711509,
        -860.294668,
        1848.877763,
        1548.219353,
        -360.336403,
        -1220.362104,
        -1422.486308,
        -537.407399,
        1625.719030
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])
    
def test_powerflowrunner_ieee_four_bus_transformer_shunt_impedance():
    results = execute_glm_case("ieee_four_bus_transformer_shunt_impedance")
    
    expected_v = np.array([
        7199.558000,
        0.000000,
        -3599.779000,
        -6235.000000,
        -3599.779000,
        6235.000000,
        7106.422287,
        -42.067600,
        -3606.903032,
        -6161.628479,
        -3520.343705,
        6189.706477,
        2242.742683,
        -144.807987,
        -1251.271366,
        -1892.203540,
        -1002.844346,
        2020.691679,
        1893.763615,
        -302.435080,
        -1277.965079,
        -1617.280802,
        -705.200678,
        1850.977065
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])

# This is known to not be as close as desired, but it is in agreement with Amrit's code.
def test_powerflowrunner_ieee_four_bus_long_lines():
    results = execute_glm_case("ieee_four_bus_long_lines")
    
    expected_v = np.array([
        7199.558000,
        0.000000,
        -3599.779000,
        -6235.000000,
        -3599.779000,
        6235.000000,
        6668.356234,
        -186.590938,
        -3662.041811,
        -5961.269772,
        -3288.195936,
        5997.013899,
        2042.215385,
        -207.724889,
        -1261.767465,
        -1819.182589,
        -906.780392,
        1942.733479,
        1445.092247,
        -417.471493,
        -1331.757002,
        -1511.482836,
        -556.530319,
        1675.213647
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])

def test_powerflowrunner_connected_transformer():
    results = execute_glm_case("connected_transformer")
    
    expected_v = np.array([
        7200.000000,
        0.000000,
        -3600.000000,
        -6235.382907,
        -3600.000000,
        6235.382907,
        2307.901173,
        -119.219539,
        -1257.197736,
        -1939.091276,
        -1050.703437,
        2058.310815
    ], dtype=float)
    assert_v_tolerance(results.v_final[:12], expected_v[:12])

def test_powerflowrunner_just_two_transformers():
    results = execute_glm_case("just_two_transformers")
    
    expected_v = np.array([
        7200.000000,
        0.000000,
        -3600.000000,
        -6235.382907,
        -3600.000000,
        6235.382907,
        2296.390489,
        -119.219539,
        -1251.442394,
        -1929.122731,
        -1044.948095,
        2048.342270,
        6567.302594,
        -714.744064,
        -3902.637814,
        -5330.078849,
        -2664.664781,
        6044.822913
    ], dtype=float)
    assert_v_tolerance(results.v_final[:18], expected_v[:18])

def test_powerflowrunner_two_transformers():
    results = execute_glm_case("two_transformers")
    
    expected_v = np.array([
        7200.000000,
        0.000000,
        -3600.000000,
        -6235.382907,
        -3600.000000,
        6235.382907,
        2274.258070,
        -123.228147,
        -1241.297185,
        -1912.673556,
        -1029.335407,
        2028.738078,
        2070.748189,
        -244.244753,
        -1300.253660,
        -1701.342391,
        -797.465641,
        1907.264129,
        5824.574052,
        -1101.535349,
        -4018.543039,
        -4597.977395,
        -1876.011796,
        5563.162167
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])

def test_powerflowrunner_three_transformers_with_lines():
    results = execute_glm_case("three_transformers_with_lines")
    
    expected_v = np.array([
        7200.000000,
        0.000000,
        -3600.000000,
        -6235.382907,
        -3600.000000,
        6235.382907,
        2239.272578,
        -124.254013,
        -1227.692967,
        -1890.221059,
        -1006.386752,
        1994.867780,
        1989.662450,
        -248.037406,
        -1272.730345,
        -1660.554932,
        -750.896079,
        1808.958923,
        5476.639373,
        -1115.979326,
        -3895.259304,
        -4408.409548,
        -1667.624257,
        5166.953388,
        5393.369274,
        -1157.273545,
        -3910.283802,
        -4331.792781,
        -1582.392405,
        5104.934074,
        1636.579409,
        -510.321210,
        -1331.203843,
        -1255.182172,
        -333.311564,
        1617.749324
    ], dtype=float)
    assert_v_tolerance(results.v_final[:36], expected_v[:36])

def test_powerflowrunner_three_transformers():
    results = execute_glm_case("three_transformers")
    
    expected_v = np.array([
        7200.000000,
        0.000000,
        -3600.000000,
        -6235.382907,
        -3600.000000,
        6235.382907,
        2401.077177,
        -1.192195,
        -1201.571060,
        -2078.797734,
        -1199.506117,
        2079.989929,
        4801.590227,
        -3.178012,
        -2403.547353,
        -4156.710109,
        -2398.042875,
        4159.888121,
        1600.543435,
        -2.847047,
        -802.737333,
        -1384.687751,
        -797.806103,
        1387.534798
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])
    
def test_powerflowrunner_kersting_example_4_1():
    results = execute_glm_case("kersting_example_4_1")
    
    expected_v = np.array([
        7199.558000,
        0.000000,
        -3599.779000,
        -6235.000000,
        -3599.779000,
        6235.000000,
        7130.382343,
        -38.873965,
        -3613.920169,
        -6166.804123,
        -3528.624337,
        6213.353304
    ])
    assert_v_tolerance(results.v_final[:12], expected_v[:12])

def test_powerflowrunner_kersting_example_4_2():
    results = execute_glm_case("kersting_example_4_2")
    
    expected_v = np.array([
        7199.558000,
        0.000000,
        -3599.779000,
        -6235.000000,
        -3599.779000,
        6235.000000,
        7129.241844,
        -13.956357,
        -3580.596805,
        -6174.425925,
        -3547.070648,
        6190.201114
    ])
    assert_v_tolerance(results.v_final[:12], expected_v[:12])

def test_powerflowrunner_underground_lines_and_transformers():
    results = execute_glm_case("underground_lines_and_transformers")
    
    expected_v = np.array([
        2400.000000,
        0.000000,
        -1200.000000,
        -2078.460969,
        -1200.000000,
        2078.460969,
        2174.081956,
        -60.902588,
        -1139.784166,
        -1852.358910,
        -1034.297790,
        1913.261497,
        6032.255040,
        -596.518325,
        -3532.727543,
        -4925.826944,
        -2499.527497,
        5522.345269,
        5956.888635,
        -616.835467,
        -3512.639502,
        -4850.399152,
        -2444.249133,
        5467.234619,
        1825.504066,
        -343.873016,
        -1210.554800,
        -1408.996388,
        -614.949266,
        1752.869404,
        1599.586022,
        -404.775603,
        -1150.338966,
        -1182.894329,
        -449.247056,
        1587.669932
    ], dtype=float)
    assert_v_tolerance(results.v_final[:36], expected_v[:36])

def test_powerflowrunner_ieee_four_bus_underground_spaced():
    results = execute_glm_case("ieee_four_bus_underground_spaced")
    
    expected_v = np.array([
        7199.558000,
        0.000000,
        -3599.779000,
        -6235.000000,
        -3599.779000,
        6235.000000,
        7172.955032,
        -12.280743,
        -3597.112950,
        -6205.820782,
        -3575.842080,
        6218.101524,
        2290.680068,
        -126.733830,
        -1255.094749,
        -1920.420171,
        -1035.585314,
        2047.154004,
        2190.998873,
        -172.749713,
        -1245.105073,
        -1811.085782,
        -945.893791,
        1983.835497
    ], dtype=float)
    assert_v_tolerance(results.v_final[:18], expected_v[:18])

def test_powerflowrunner_ieee_four_bus_underground():
    results = execute_glm_case("ieee_four_bus_underground")
    
    expected_v = np.array([
        7199.558000,
        0.000000,
        -3599.779000,
        -6235.000000,
        -3599.779000,
        6235.000000,
        7172.955032,
        -12.280743,
        -3597.112950,
        -6205.820782,
        -3575.842080,
        6218.101524,
        2290.680068,
        -126.733830,
        -1255.094749,
        -1920.420171,
        -1035.585314,
        2047.154005,
        2190.998873,
        -172.749713,
        -1245.105073,
        -1811.085781,
        -945.893791,
        1983.835498
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])
    
def test_powerflowrunner_ieee_four_bus_underground_step_up():
    results = execute_glm_case("ieee_four_bus_underground_step_up")
    
    expected_v = np.array([
        2401.777000,
        0.000000,
        -1200.889000,
        -2080.000000,
        -1200.889000,
        2080.000000,
        2309.151299,
        -49.139274,
        -1197.131990,
        -1975.214170,
        -1112.020293,
        2024.353446,
        6921.118981,
        -148.333012,
        -3589.021088,
        -5919.698718,
        -3332.100841,
        6068.031735,
        6896.398987,
        -161.447327,
        -3588.018415,
        -5891.733422,
        -3308.383515,
        6053.180755
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])

def test_powerflowrunner_ieee_four_bus_underground_long_lines():
    results = execute_glm_case("ieee_four_bus_underground_long_lines")
    
    expected_v = np.array([
        7199.558000,
        0.000000,
        -3599.779000,
        -6235.000000,
        -3599.779000,
        6235.000000,
        7089.869661,
        -48.954675,
        -3587.330820,
        -6115.529773,
        -3502.538836,
        6164.484448,
        2258.832889,
        -140.676188,
        -1251.245595,
        -1885.868525,
        -1007.587288,
        2026.544717,
        2135.532386,
        -195.706067,
        -1237.252614,
        -1751.572216,
        -898.279760,
        1947.278286
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])

def test_powerflowrunner_ieee_four_bus_switch():
    results = execute_glm_case("ieee_four_bus_switch")
    
    expected_v = np.array([
        7199.558000,
        0.000000,
        -3599.779000,
        -6235.000000,
        -3599.779000,
        6235.000000,
        7126.409318,
        -39.482195,
        -3609.893079,
        -6166.230282,
        -3526.071228,
        6205.759921,
        2281.499622,
        -133.094021,
        -1259.992399,
        -1914.461013,
        -1024.788331,
        2047.035826,
        2281.482751,
        -133.034484,
        -1259.932576,
        -1914.476141,
        -1024.831436,
        2046.991573
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])

def test_powerflowrunner_ieee_four_bus_fuse():
    results = execute_glm_case("ieee_four_bus_fuse")
    
    expected_v = np.array([
        7199.558000,
        0.000000,
        -3599.779000,
        -6235.000000,
        -3599.779000,
        6235.000000,
        7126.409318,
        -39.482195,
        -3609.893079,
        -6166.230282,
        -3526.071228,
        6205.759921,
        2281.499622,
        -133.094021,
        -1259.992399,
        -1914.461013,
        -1024.788331,
        2047.035826,
        2281.482751,
        -133.034484,
        -1259.932576,
        -1914.476141,
        -1024.831436,
        2046.991573
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])

def test_powerflowrunner_ieee_four_bus_cap():
    results = execute_glm_case("ieee_four_bus_cap")
    output = load_gridlabd_csv("ieee_four_bus_cap")
    assert_busresults_gridlabdvoltdump(results, output)

def test_powerflowrunner_ieee_four_bus_unbalanced_pq_load():
    results = execute_glm_case("ieee_four_bus_unbalanced_pq_load")
    
    expected_v = np.array([
        7199.558000,
        0.000000,
        -3599.779000,
        -6235.000000,
        -3599.779000,
        6235.000000,
        7173.191420,
        -11.570974,
        -3601.439533,
        -6210.615924,
        -3574.944688,
        6222.889390,
        2356.580806,
        -42.759078,
        -1217.089634,
        -2020.616179,
        -1140.578125,
        2063.713774,
        2257.785357,
        -86.115461,
        -1223.311644,
        -1929.249164,
        -1047.524077,
        2018.335376
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])

def test_powerflowrunner_load_within_meter():
    results = execute_glm_case("load_within_meter")
    
    expected_v = np.array([
        7199.558000,
        0.000000,
        -3599.779000,
        -6235.000000,
        -3599.779000,
        6235.000000,
        7106.422287,
        -42.067600,
        -3606.903032,
        -6161.628479,
        -3520.343705,
        6189.706477,
        2242.742683,
        -144.807987,
        -1251.271366,
        -1892.203540,
        -1002.844346,
        2020.691679,
        1893.763615,
        -302.435080,
        -1277.965079,
        -1617.280802,
        -705.200678,
        1850.977065,
        1893.763615,
        -302.435080,
        -1277.965079,
        -1617.280802,
        -705.200678,
        1850.977065
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])

def test_powerflowrunner_transformer_to_meter():
    results = execute_glm_case("transformer_to_meter")
    
    expected_v = np.array([
        7199.558000,
        0.000000,
        -3599.779000,
        -6235.000000,
        -3599.779000,
        6235.000000,
        7106.422287,
        -42.067600,
        -3606.903032,
        -6161.628479,
        -3520.343705,
        6189.706477,
        2242.742683,
        -144.807987,
        -1251.271366,
        -1892.203540,
        -1002.844346,
        2020.691679,
        1893.763615,
        -302.435080,
        -1277.965079,
        -1617.280802,
        -705.200678,
        1850.977065
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])

def test_powerflowrunner_regulator_node_load():
    results = execute_glm_case("regulator_node_load")
    
    expected_v = np.array([
        2401.777100,
        0.000000,
        -1200.888600,
        -2080.000000,
        -1200.888600,
        2080.000000,
        2551.887725,
        0.000261,
        -1260.931282,
        -2183.998989,
        -1283.449719,
        2222.996472,
        2555.056809,
        0.395674,
        -1258.339662,
        -2178.549073,
        -1270.796020,
        2220.907824,
        2555.849080,
        0.494527,
        -1257.691757,
        -2177.186593,
        -1267.632595,
        2220.385662
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])

def test_powerflowrunner_regulatorB_node_load():
    results = execute_glm_case("regulatorB_node_load")
    
    expected_v = np.array([
        2401.777100,
        0.000000,
        -1200.888600,
        -2080.000000,
        -1200.888600,
        2080.000000,
        2561.895122,
        0.000260,
        -1264.091439,
        -2189.472536,
        -1289.544569,
        2233.553066,
        2534.299786,
        18.840223,
        -1133.952479,
        -2103.385857,
        -1258.435472,
        1954.540239,
        2527.400952,
        23.550213,
        -1101.417739,
        -2081.864187,
        -1250.658198,
        1884.787032,
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])

def test_powerflowrunner_ieee_thirteen_bus_pq_top_right():
    results = execute_glm_case("ieee_thirteen_bus_pq_top_right")
    
    expected_v = np.array([
        2530.112678,
        -13.609827,
        -1263.866463,
        -2162.289985,
        -1256.518525,
        2206.969617,
        2551.881331,
        0.004815,
        -1260.925636,
        -2183.996674,
        -1283.450527,
        2222.990498,
        2537.135365,
        -11.050963,
        -1264.496605,
        -2167.288150,
        -1259.653691,
        2212.053750,
        2401.777100,
        0.000000,
        -1200.888600,
        -2080.000000,
        -1200.888600,
        2080.000000,
        285.493565,
        -4.676781,
        -145.207385,
        -243.973164,
        -140.577891,
        251.394710,
        2537.933201,
        -10.954905,
        -1263.837409,
        -2165.924034,
        -1256.473486,
        2211.520676
    ], dtype=float)
    assert_v_tolerance(results.v_final[:36], expected_v[:36])

def test_powerflowrunner_two_regulators():
    results = execute_glm_case("two_regulators")
    
    expected_v = np.array([
        2401.777100,
        0.000000,
        -1200.888600,
        -2080.000000,
        -1200.888600,
        2080.000000,
        2401.776629,
        0.000277,
        -1200.886766,
        -2079.998938,
        -1200.888628,
        2079.996230,
        2405.188993,
        0.359629,
        -1198.079747,
        -2074.324519,
        -1187.354883,
        2077.715301,
        2405.188522,
        0.359907,
        -1198.077913,
        -2074.323457,
        -1187.354911,
        2077.711531
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])

def test_powerflowrunner_regulator_lower_impedance_transformer_load():
    results = execute_glm_case("regulator_lower_impedance_transformer_load")
    
    # Lower series impedance of the xfmr
    expected_v = np.array([
        2401.777100,
        0.000000,
        -1200.888600,
        -2080.000000,
        -1200.888600,
        2080.000000,
        2401.776628,
        0.000278,
        -1200.886770,
        -2079.998941,
        -1200.888611,
        2079.996243,
        92.448879,
        -0.001424,
        -46.227489,
        -80.057274,
        -46.212328,
        80.061723
    ])

    assert_v_tolerance(results.v_final[:18], expected_v[:18])

def test_powerflowrunner_regulator_higher_impedance_transformer_load():
    results = execute_glm_case("regulator_higher_impedance_transformer_load")
    
    # Higher impedance
    expected_v = np.array([
        2401.777100,
        0.000000,
        -1200.888600,
        -2080.000000,
        -1200.888600,
        2080.000000,
        2401.776627,
        0.000281,
        -1200.886714,
        -2079.998962,
        -1200.888764,
        2079.996118,
        92.018848,
        -0.509496,
        -47.090983,
        -77.598759,
        -41.610269,
        79.093291
    ])

    assert_v_tolerance(results.v_final[:18], expected_v[:18])

def test_powerflowrunner_regulator_ol():
    results = execute_glm_case("regulator_ol")
    
    expected_v = np.array([
        2401.777100,
        0.000000,
        -1200.888600,
        -2080.000000,
        -1200.888600,
        2080.000000,
        2401.776629,
        0.000277,
        -1200.886766,
        -2079.998938,
        -1200.888628,
        2079.996230,
        2405.188986,
        0.359626,
        -1198.079751,
        -2074.324526,
        -1187.354905,
        2077.715294
    ], dtype=float)
    assert_v_tolerance(results.v_final[:18], expected_v[:18])

def test_powerflowrunner_regulator_overhead_line_transformer_load():
    results = execute_glm_case("regulator_overhead_line_transformer_load")
    
    
    
    # Overhead
    expected_v = np.array([
        2401.777100,
        0.000000,
        -1200.888600,
        -2080.000000,
        -1200.888600,
        2080.000000,
        2401.776629,
        0.000277,
        -1200.886765,
        -2079.998938,
        -1200.888628,
        2079.996230,
        2405.189448,
        0.359038,
        -1198.079083,
        -2074.324765,
        -1187.353933,
        2077.713449,
        92.580248,
        0.012388,
        -46.119420,
        -79.838843,
        -45.691310,
        79.973788
    ])

    assert_v_tolerance(results.v_final[:24], expected_v[:24])
    
def test_powerflowrunner_regulator_overhead_lines():
    results = execute_glm_case("regulator_overhead_lines")
    
    
    
    expected_v = np.array([
        2401.777100,
        0.000000,
        -1200.888600,
        -2080.000000,
        -1200.888600,
        2080.000000,
        2401.776631,
        0.000275,
        -1200.886745,
        -2079.998928,
        -1200.888697,
        2079.996174,
        2405.241199,
        0.266838,
        -1198.047236,
        -2074.361348,
        -1187.221368,
        2077.409612,
        2408.705766,
        0.533400,
        -1195.207726,
        -2068.723768,
        -1173.554039,
        2074.823051,
        2412.170333,
        0.799963,
        -1192.368216,
        -2063.086188,
        -1159.886710,
        2072.236489,
        2415.634900,
        1.066525,
        -1189.528707,
        -2057.448608,
        -1146.219381,
        2069.649928,
        2419.099467,
        1.333088,
        -1186.689197,
        -2051.811028,
        -1132.552052,
        2067.063367
    ])

    assert_v_tolerance(results.v_final[:42], expected_v[:42])
    
def test_powerflowrunner_gc_12_47_1_only_overhead_lines():
    results = execute_glm_case("gc_12_47_1_only_overhead_lines")
    
    
    
    expected_v_file_path = os.path.join("data", "gc_12_47_1_only_overhead_lines", "expected_output.txt")
    expected_v_full_file_path = os.path.join(CURR_DIR, expected_v_file_path)
    expected_v = np.loadtxt(expected_v_full_file_path)
    assert_v_tolerance(results.v_final[:186], expected_v[:186])

def test_powerflowrunner_regulator_overhead_line_underground_line():
    results = execute_glm_case("regulator_overhead_line_underground_line")
    
    
    
    expected_v = np.array([
        2401.777100,
        0.000000,
        -1200.888600,
        -2080.000000,
        -1200.888600,
        2080.000000,
        2401.776629,
        0.000277,
        -1200.886764,
        -2079.998938,
        -1200.888630,
        2079.996224,
        2405.196916,
        0.355429,
        -1198.071941,
        -2074.325479,
        -1187.334063,
        2077.700919,
        2404.838447,
        -0.379325,
        -1197.778668,
        -2072.800374,
        -1184.239291,
        2075.079133
    ])

    assert_v_tolerance(results.v_final[:24], expected_v[:24])

def test_powerflowrunner_regulator_ul():
    results = execute_glm_case("regulator_ul")
    
    
    
    expected_v = np.array([
        2401.777100,
        0.000000,
        -1200.888600,
        -2080.000000,
        -1200.888600,
        2080.000000,
        2401.776628,
        0.000278,
        -1200.886769,
        -2079.998941,
        -1200.888613,
        2079.996238,
        2401.420077,
        -0.733144,
        -1200.591660,
        -2078.477605,
        -1197.792792,
        2077.396864
    ], dtype=float)
    assert_v_tolerance(results.v_final[:18], expected_v[:18])

def test_powerflowrunner_regulator_ul_xfmr():
    results = execute_glm_case("regulator_ul_xfmr")
    
    
    
    expected_v = np.array([
        2401.777100,
        0.000000,
        -1200.888600,
        -2080.000000,
        -1200.888600,
        2080.000000,
        2401.776628,
        0.000278,
        -1200.886769,
        -2079.998941,
        -1200.888613,
        2079.996238,
        2401.420077,
        -0.733145,
        -1200.591660,
        -2078.477605,
        -1197.792792,
        2077.396864,
        62386.891191,
        -19.047917,
        -31190.373322,
        -53997.109269,
        -31117.645823,
        53969.037055
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])

def test_powerflowrunner_regulator_ul_xfmr_ul():
    results = execute_glm_case("regulator_ul_xfmr_ul")
    
    
    
    expected_v = np.array([
        2401.777100,
        0.000000,
        -1200.888600,
        -2080.000000,
        -1200.888600,
        2080.000000,
        2401.776628,
        0.000278,
        -1200.886769,
        -2079.998941,
        -1200.888613,
        2079.996238,
        2401.420076,
        -0.733146,
        -1200.591660,
        -2078.477605,
        -1197.792787,
        2077.396855,
        62386.891169,
        -19.047950,
        -31190.373318,
        -53997.109260,
        -31117.645705,
        53969.036824,
        62386.877444,
        -19.076182,
        -31190.361959,
        -53997.050700,
        -31117.526539,
        53968.936767
    ], dtype=float)
    assert_v_tolerance(results.v_final[:30], expected_v[:30])

def test_powerflowrunner_gc_12_47_1_pared_down_no_regulator():
    results = execute_glm_case("gc_12_47_1_pared_down_no_regulator")
    
    
    
    expected_v = np.array([
        276.922391,
        -0.056781,
        -138.509431,
        -239.773729,
        -138.408503,
        239.834182,
        7199.434875,
        -0.639372,
        -3600.279635,
        -6234.178443,
        -3599.154835,
        6234.832172,
        7194.778063,
        -0.835743,
        -3598.079946,
        -6229.943215,
        -3596.582731,
        6230.860004,
        7197.357018,
        -1.554187,
        -3600.027471,
        -6231.876784,
        -3597.289563,
        6233.476837,
        7200.000000,
        0.000000,
        -3600.000000,
        -6235.000000,
        -3600.000000,
        6235.000000
    ])
    assert_v_tolerance(results.v_final[:30], expected_v[:30])

def test_powerflowrunner_gc_12_47_1_somewhat_pared_down_no_regulator():
    results = execute_glm_case("gc_12_47_1_somewhat_pared_down_no_regulator")
    
    
    
    expected_v = np.array([
        276.591613,
        -0.206985,
        -138.473418,
        -239.405045,
        -138.107659,
        239.620803,
        7199.433852,
        -0.639829,
        -3600.279520,
        -6234.177286,
        -3599.153905,
        6234.831498,
        7197.162323,
        -1.638448,
        -3600.002513,
        -6231.661794,
        -3597.116047,
        6233.349020,
        7195.540530,
        -2.351428,
        -3599.804740,
        -6229.865819,
        -3595.661087,
        6232.290583,
        7194.604545,
        -2.762910,
        -3599.690600,
        -6228.829308,
        -3594.821386,
        6231.679727,
        7194.170064,
        -3.083036,
        -3599.754297,
        -6228.284041,
        -3594.321135,
        6231.463643,
        7192.282064,
        -3.913047,
        -3599.524061,
        -6226.193268,
        -3592.627352,
        6230.231470,
        7190.848235,
        -4.543393,
        -3599.349210,
        -6224.605445,
        -3591.341021,
        6229.295704,
        7186.185765,
        -4.737481,
        -3597.144474,
        -6220.366289,
        -3588.767997,
        6225.317275,
        7188.767401,
        -5.458178,
        -3599.095458,
        -6222.301128,
        -3589.474240,
        6227.937680,
        7198.851553,
        -0.895822,
        -3600.208510,
        -6233.532448,
        -3598.631507,
        6234.451470,
        7200.000000,
        0.000000,
        -3600.000000,
        -6235.000000,
        -3600.000000,
        6235.000000
    ])
    assert_v_tolerance(results.v_final[:72], expected_v[:72])

def test_powerflowrunner_gc_12_47_1_no_reg():
    results = execute_glm_case("gc_12_47_1_no_reg")
    
    
    
    expected_v = np.array([
        275.779525,
        -0.554492,
        -138.366001,
        -238.510494,
        -137.387453,
        239.085928,
        275.779918,
        -0.554602,
        -138.366298,
        -238.510788,
        -137.387560,
        239.086326,
        275.777913,
        -0.563516,
        -138.373137,
        -238.504571,
        -137.378795,
        239.089066,
        7199.995281,
        0.019758,
        -3599.980169,
        -6235.005799,
        -3600.014838,
        6234.985835,
        7193.156842,
        -2.976276,
        -3599.136797,
        -6227.437801,
        -3593.888810,
        6230.517066,
        7188.274433,
        -5.115340,
        -3598.534659,
        -6222.034512,
        -3589.515038,
        6227.326519,
        7185.456649,
        -6.349858,
        -3598.187147,
        -6218.916113,
        -3586.990803,
        6225.485159,
        7184.148142,
        -7.311401,
        -3598.376682,
        -6217.275149,
        -3585.486418,
        6224.833009,
        7178.464317,
        -9.801579,
        -3597.675707,
        -6210.984945,
        -3580.394720,
        6221.118754,
        7174.147774,
        -11.692728,
        -3597.143355,
        -6206.207892,
        -3576.527863,
        6218.297988,
        7165.049014,
        -13.998702,
        -3594.539510,
        -6196.975556,
        -3569.835024,
        6211.504822,
        7165.090874,
        -13.764240,
        -3594.354102,
        -6197.129409,
        -3570.059931,
        6211.423270,
        7165.101070,
        -13.767099,
        -3594.361820,
        -6197.137044,
        -3570.062709,
        6211.433626,
        7167.327956,
        -14.644218,
        -3596.270190,
        -6198.678875,
        -3570.450300,
        6213.822914,
        7167.327956,
        -14.644218,
        -3596.270190,
        -6198.678875,
        -3570.450300,
        6213.822914,
        7167.326384,
        -14.637632,
        -3596.263580,
        -6198.680808,
        -3570.455246,
        6213.818192,
        7167.382651,
        -14.620257,
        -3596.276937,
        -6198.739404,
        -3570.499295,
        6213.858656,
        7167.384224,
        -14.626843,
        -3596.283547,
        -6198.737471,
        -3570.494349,
        6213.863378,
        7167.689354,
        -14.493168,
        -3596.321185,
        -6199.075150,
        -3570.767685,
        6214.062778,
        7167.690927,
        -14.499754,
        -3596.327796,
        -6199.073217,
        -3570.762739,
        6214.067500,
        7167.689354,
        -14.493168,
        -3596.321185,
        -6199.075150,
        -3570.767685,
        6214.062778,
        7167.636698,
        -14.516236,
        -3596.314690,
        -6199.016878,
        -3570.720516,
        6214.028368,
        7167.638271,
        -14.522823,
        -3596.321300,
        -6199.014944,
        -3570.715570,
        6214.033089,
        7167.878701,
        -14.417488,
        -3596.350953,
        -6199.281024,
        -3570.930951,
        6214.190206,
        7167.883419,
        -14.437246,
        -3596.370784,
        -6199.275224,
        -3570.916113,
        6214.204370,
        7167.327956,
        -14.644218,
        -3596.270190,
        -6198.678875,
        -3570.450300,
        6213.822914,
        7167.327956,
        -14.644218,
        -3596.270190,
        -6198.678875,
        -3570.450300,
        6213.822914,
        7185.456649,
        -6.349858,
        -3598.187147,
        -6218.916113,
        -3586.990803,
        6225.485159,
        7167.327956,
        -14.644218,
        -3596.270190,
        -6198.678875,
        -3570.450300,
        6213.822914,
        7198.242271,
        -0.748265,
        -3599.763974,
        -6233.065768,
        -3598.444451,
        6233.840281,
        7200.000000,
        0.000000,
        -3600.000000,
        -6235.000000,
        -3600.000000,
        6235.000000
    ])
    assert_v_tolerance(results.v_final[:186], expected_v[:186])
    
def test_powerflowrunner_gc_12_47_1_xfmr_as_reg():
    results = execute_glm_case("gc_12_47_1_xfmr_as_reg")
    
    
    
    expected_v = np.array([
        275.713531,
        -0.629036,
        -138.398535,
        -238.414605,
        -137.288859,
        239.066251,
        275.713923,
        -0.629146,
        -138.398832,
        -238.414899,
        -137.288966,
        239.066650,
        275.711916,
        -0.638062,
        -138.405671,
        -238.408679,
        -137.280199,
        239.069387,
        7198.293176,
        -1.922965,
        -3600.837380,
        -6232.522525,
        -3597.454330,
        6234.488840,
        7191.452292,
        -4.917870,
        -3599.991710,
        -6224.952940,
        -3591.328058,
        6230.017308,
        7186.568139,
        -7.056128,
        -3599.387931,
        -6219.548518,
        -3586.954112,
        6226.824789,
        7183.749347,
        -8.290180,
        -3599.039472,
        -6216.429464,
        -3584.429778,
        6224.982291,
        7182.440268,
        -9.251598,
        -3599.228599,
        -6214.788051,
        -3582.925211,
        6224.329571,
        7176.754411,
        -11.740837,
        -3598.525714,
        -6208.496528,
        -3577.833309,
        6220.613020,
        7172.436326,
        -13.631273,
        -3597.991912,
        -6203.718473,
        -3573.966300,
        6217.790511,
        7163.334771,
        -15.935343,
        -3595.384880,
        -6194.484638,
        -3567.273717,
        6210.993867,
        7163.376705,
        -15.700836,
        -3595.199471,
        -6194.638579,
        -3567.498700,
        6210.912356,
        7163.386902,
        -15.703699,
        -3595.207192,
        -6194.646213,
        -3567.501476,
        6210.922716,
        7165.614080,
        -16.581628,
        -3597.116452,
        -6196.187886,
        -3567.888506,
        6213.312686,
        7165.614080,
        -16.581628,
        -3597.116452,
        -6196.187886,
        -3567.888506,
        6213.312686,
        7165.612509,
        -16.575040,
        -3597.109841,
        -6196.189822,
        -3567.893455,
        6213.307965,
        7165.668795,
        -16.557676,
        -3597.123217,
        -6196.248428,
        -3567.937503,
        6213.348451,
        7165.670366,
        -16.564264,
        -3597.129829,
        -6196.246493,
        -3567.932555,
        6213.353172,
        7165.975606,
        -16.430639,
        -3597.167569,
        -6196.584243,
        -3568.205902,
        6213.552696,
        7165.977177,
        -16.437228,
        -3597.174181,
        -6196.582307,
        -3568.200953,
        6213.557417,
        7165.975606,
        -16.430639,
        -3597.167569,
        -6196.584243,
        -3568.205902,
        6213.552696,
        7165.922931,
        -16.453699,
        -3597.161056,
        -6196.525958,
        -3568.158731,
        6213.518264,
        7165.924502,
        -16.460287,
        -3597.167668,
        -6196.524022,
        -3568.153782,
        6213.522985,
        7166.165018,
        -16.354992,
        -3597.197402,
        -6196.790157,
        -3568.369172,
        6213.680199,
        7166.169732,
        -16.374756,
        -3597.217236,
        -6196.784351,
        -3568.354326,
        6213.694363,
        7165.614080,
        -16.581628,
        -3597.116452,
        -6196.187886,
        -3567.888506,
        6213.312686,
        7165.614080,
        -16.581628,
        -3597.116452,
        -6196.187886,
        -3567.888506,
        6213.312686,
        7183.749347,
        -8.290180,
        -3599.039472,
        -6216.429464,
        -3584.429778,
        6224.982291,
        7165.614080,
        -16.581628,
        -3597.116452,
        -6196.187886,
        -3567.888506,
        6213.312686,
        7196.539538,
        -2.690699,
        -3600.620596,
        -6230.582087,
        -3595.883881,
        6233.342578,
        7200.000000,
        0.000000,
        -3600.000000,
        -6235.000000,
        -3600.000000,
        6235.000000
    ])
    assert_v_tolerance(results.v_final[:186], expected_v[:186])

def test_powerflowrunner_gc_12_47_1_further_simplified():
    results = execute_glm_case("gc_12_47_1_further_simplified")
    
    
    
    expected_v = np.array([
        276.943849,
        -0.031994,
        -138.498363,
        -239.805181,
        -138.441039,
        239.840296,
        7199.991866,
        0.004977,
        -3599.991502,
        -6234.995326,
        -3600.000205,
        6234.990373,
        7195.335431,
        -0.191794,
        -3597.792374,
        -6230.760228,
        -3597.427941,
        6231.018749,
        7197.914252,
        -0.909952,
        -3599.739569,
        -6232.693824,
        -3598.134955,
        6233.635314,
        7200.000000,
        0.000000,
        -3600.000000,
        -6235.000000,
        -3600.000000,
        6235.000000
    ])
    assert_v_tolerance(results.v_final[:30], expected_v[:30])

def test_powerflowrunner_gc_12_47_1_simplified():
    results = execute_glm_case("gc_12_47_1_simplified")
    
    
    
    expected_v = np.array([
        276.941328,
        -0.032544,
        -138.497564,
        -239.802671,
        -138.439264,
        239.838368,
        7199.991866,
        0.004977,
        -3599.991502,
        -6234.995326,
        -3600.000205,
        6234.990373,
        7195.269954,
        -0.206101,
        -3597.771621,
        -6230.695029,
        -3597.381846,
        6230.968666,
        7197.850375,
        -0.930826,
        -3599.725424,
        -6232.626727,
        -3598.083945,
        6233.589968,
        7197.848797,
        -0.924270,
        -3599.718838,
        -6232.628639,
        -3598.088861,
        6233.585256,
        7197.912652,
        -0.903401,
        -3599.732976,
        -6232.695715,
        -3598.139856,
        6233.630586,
        7197.914231,
        -0.909956,
        -3599.739561,
        -6232.693803,
        -3598.134941,
        6233.635297,
        7200.000000,
        0.000000,
        -3600.000000,
        -6235.000000,
        -3600.000000,
        6235.000000,
    ])
    assert_v_tolerance(results.v_final[:48], expected_v[:48])

def test_powerflowrunner_gc_12_47_1_subset():
    results = execute_glm_case("gc_12_47_1_subset")
    
    
    
    expected_v = np.array([
        276.610623,
        -0.182749,
        -138.461589,
        -239.434052,
        -138.138458,
        239.625053,
        7199.991859,
        0.004987,
        -3599.991489,
        -6234.995325,
        -3600.000210,
        6234.990361,
        7197.720574,
        -0.993762,
        -3599.714727,
        -6232.479982,
        -3597.962361,
        6233.508168,
        7196.098955,
        -1.706834,
        -3599.517129,
        -6230.684113,
        -3596.507407,
        6232.449933,
        7195.163070,
        -2.118369,
        -3599.403089,
        -6229.647664,
        -3595.667710,
        6231.839194,
        7194.728647,
        -2.438512,
        -3599.466831,
        -6229.102440,
        -3595.167474,
        6231.623170,
        7192.840849,
        -3.268631,
        -3599.236798,
        -6227.011791,
        -3593.473699,
        6230.391232,
        7191.407174,
        -3.899058,
        -3599.062101,
        -6225.424063,
        -3592.187373,
        6229.455646,
        7186.679520,
        -4.107836,
        -3596.837113,
        -6221.119770,
        -3589.568067,
        6225.427594,
        7189.262619,
        -4.834823,
        -3598.794381,
        -6223.052731,
        -3590.269569,
        6228.052469,
        7189.261042,
        -4.828259,
        -3598.787788,
        -6223.054649,
        -3590.274493,
        6228.047755,
        7189.324986,
        -4.807399,
        -3598.801980,
        -6223.121799,
        -3590.325525,
        6228.093168,
        7189.326563,
        -4.813963,
        -3598.808573,
        -6223.119881,
        -3590.320601,
        6228.097882,
        7195.163070,
        -2.118369,
        -3599.403089,
        -6229.647664,
        -3595.667710,
        6231.839194,
        7199.409622,
        -0.251039,
        -3599.920542,
        -6234.350525,
        -3599.477815,
        6234.610406,
        7200.000000,
        0.000000,
        -3600.000000,
        -6235.000000,
        -3600.000000,
        6235.000000
    ])
    assert_v_tolerance(results.v_final[:96], expected_v[:96])

# def test_powerflowrunner_gc_12_no_shunt_impedances():
#     results = execute_glm_case("gc-12.47-1_no_shunt_impedances")
#     
#     
#     
#     expected_v = np.array([])
#     assert_v_tolerance(results.v_final[:216], expected_v[:216])

def test_powerflowrunner_gc_12_47_1_no_cap():
    results = execute_glm_case("gc_12_47_1_no_cap")
    comparison = load_gridlabd_csv("gc_12_47_1_no_cap")
    assert_busresults_gridlabdvoltdump(results, comparison)

def test_powerflowrunner_gc_12_47_1():
    results = execute_glm_case("gc_12_47_1")
    comparison = load_gridlabd_csv("gc_12_47_1")
    assert_busresults_gridlabdvoltdump(results, comparison)

def test_powerflowrunner_center_tap_xfmr():
    results = execute_glm_case("center_tap_xfmr")
    
    expected_v = np.array([
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        7216.880000,
        -0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        -60,
        103.923,
        -60,
        103.923
    ])
    assert_v_tolerance(results.v_final[:22], expected_v[:22])

def test_powerflowrunner_regulator_center_tap_xfmr():
    results = execute_glm_case("regulator_center_tap_xfmr")
    
    
    
    expected_v = np.array([
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        7216.880000,
        -0.000000,
        -3608.440000,
        -6250.000000,
        -3608.439997,
        6249.999927,
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440032,
        6249.999889,
        7216.902410,
        -0.006016,
        -3608.417590,
        -6250.006016,
        -3608.375623,
        6249.976295,
        -58.6513,
        102.07,
        -58.6513,
        102.07,
        -58.6254,
        101.95,
        -58.6254,
        101.95
    ])
    assert_v_tolerance(results.v_final[:32], expected_v[:32])
    
def test_powerflowrunner_triplex_load_class():
    results = execute_glm_case("triplex_load_class")
    
    
    
    expected_v = np.array([
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        7216.880000,
        -0.000000,
        -3608.440000,
        -6250.000000,
        -3608.439998,
        6249.999964,
        7216.880000,
        -0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440016,
        6249.999945,
        7216.891155,
        -0.002974,
        -3608.428845,
        -6250.002974,
        -3608.407948,
        6249.988262,
        -59.1807,
        102.534,
        -59.4739,
        103.471,
        -59.0964,
        102.347,
        -59.5323,
        103.538
    ])
    assert_v_tolerance(results.v_final[:32], expected_v[:32])

def test_powerflowrunner_basic_triplex_network():
    results = execute_glm_case("basic_triplex_network")
    
    
    
    expected_v = np.array([
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        7216.880000,
        -0.000000,
        -3608.440000,
        -6250.000000,
        -3608.439998,
        6249.999961,
        7216.880000,
        -0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440017,
        6249.999941,
        7216.891891,
        -0.003095,
        -3608.428109,
        -6250.003095,
        -3608.405814,
        6249.987708,
        -59.1194,
        102.45,
        -59.4373,
        103.445,
        -56.0874,
        95.8343,
        -61.5221,
        105.81
    ])
    assert_v_tolerance(results.v_final[:32], expected_v[:32])

def test_powerflowrunner_r1_12_47_1():
    results = execute_glm_case("r1_12_47_1")
    comparison = load_gridlabd_csv("r1_12_47_1")
    assert_busresults_gridlabdvoltdump(results, comparison)

def test_powerflowrunner_r1_12_47_3():
    results = execute_glm_case("r1_12_47_3")
    comparison = load_gridlabd_csv("r1_12_47_3")
    assert_busresults_gridlabdvoltdump(results, comparison)

# Requires support for delta connected transformers (not yet supported)
def test_powerflowrunner_ieee_four_bus_delta_delta_transformer():
    results = execute_glm_case("ieee_four_bus_delta_delta_transformer")
    
    
    
    expected_v = np.array([
        7199.558000,
        0.000000,
        -3599.779000,
        -6235.000000,
        -3599.779000,
        6235.000000,
        7106.277773,
        -42.075713,
        -3607.171149,
        -6161.519929,
        -3521.244627,
        6189.669412,
        2245.404924,
        -143.257842,
        -1248.933296,
        -1890.408631,
        -996.471628,
        2033.666474,
        1895.884360,
        -300.915338,
        -1276.631641,
        -1615.079159,
        -702.203709,
        1863.812979
    ], dtype=float)
    assert_v_tolerance(results.v_final[:24], expected_v[:24])

def test_powerflowrunner_ieee_thirteen_bus_Y_Y_pq_loads_top_half():
    results = execute_glm_case("ieee_thirteen_bus_Y_Y_pq_loads_top_half")
    
    
    
    expected_v = np.array([
        2527.413813,
        21.026001,
        -1268.879030,
        -2088.712286,
        -1256.924681,
        2234.586792,
        2551.881259,
        0.004726,
        -1260.909210,
        -2183.990082,
        -1283.450566,
        2222.990594,
        2534.381281,
        23.653699,
        -1269.684238,
        -2093.853157,
        -1260.044125,
        2239.635343,
        2401.777100,
        0.000000,
        -1200.888600,
        -2080.000000,
        -1200.888600,
        2080.000000,
        285.218224,
        -0.771645,
        -145.671425,
        -235.353183,
        -140.684165,
        254.591193,
        -1257.783878,
        -2064.856440,
        -1259.765544,
        2247.968781,
        -1254.204220,
        -2056.141749,
        -1259.681042,
        2250.473607,
        2535.178957,
        23.769788,
        -1269.012592,
        -2092.435081,
        -1256.890030,
        2239.114466
    ], dtype=float)
    assert_v_tolerance(results.v_final[:44], expected_v[:44])

# Requires support for delta-connected loads, (not yet supported)
def test_powerflowrunner_ieee_thirteen_bus_core():
    results = execute_glm_case("ieee_13_core")
    
    
    
    expected_v = np.array([
        2551.872178,
        0.009692,
        -1260.914633,
        -2183.989885,
        -1283.450224,
        2222.976678,
        2522.264067,
        -22.808067,
        -1271.713885,
        -2137.041419,
        -1221.895080,
        2203.573395,
        2514.862040,
        -28.512507,
        -1274.413697,
        -2125.304302,
        -1206.506294,
        2198.722574,
        2401.777100,
        0.000000,
        -1200.888600,
        -2080.000000,
        -1200.888600,
        2080.000000,
        2490.217532,
        -45.869289,
        -1284.571692,
        -2094.193728,
        -1169.990388,
        2185.943230
    ], dtype=float)
    assert_v_tolerance(results.v_final[:30], expected_v[:30])

# Requires support for delta loads (not yet supported)
def test_powerflowrunner_ieee_thirteen_bus_pq_loads_top_half():
    results = execute_glm_case("ieee_thirteen_bus_pq_loads_top_half")
    
    
    
    expected_v = np.array([
        2527.687894,
        4.211254,
        -1274.057147,
        -2116.020375,
        -1248.896569,
        2210.436074,
        2551.881291,
        0.004772,
        -1260.914623,
        -2183.989494,
        -1283.453478,
        2222.986561,
        2534.66223,
        6.812269,
        -1274.822183,
        -2121.087845,
        -1252.062088,
        2215.531639,
        2401.7771,
        0,
        -1200.8886,
        -2080,
        -1200.8886,
        2080,
        285.229227,
        -2.668878,
        -146.300047,
        -238.563007,
        -139.707831,
        251.779222,
        -1269.230772,
        -2100.167368,
        -1251.682983,
        2212.982423,
        -1269.354083,
        -2096.182817,
        -1251.528341,
        2208.994121,
        2535.470654,
        6.916907,
        -1274.142133,
        -2119.695189,
        -1248.875136,
        2214.99793
    ], dtype=float)
    assert_v_tolerance(results.v_final[:44], expected_v[:44])

# Requires support for delta loads (not yet supported)
def test_powerflowrunner_ieee_thirteen_bus_pq():
    results = execute_glm_case("ieee_13_pq_loads")
    
    
    
    expected_v = np.array([
        2407.799947,
        -146.086205,
        -1289.592686,
        -2092.236160,
        -1094.392832,
        2086.873323,
        2551.822886,
        0.041211,
        -1260.877945,
        -2183.977170,
        -1283.460616,
        2222.921820,
        2415.302999,
        -143.751381,
        -1290.313926,
        -2097.256911,
        -1097.595409,
        2092.496088,
        2401.777100,
        0.000000,
        -1200.888600,
        -2080.000000,
        -1200.888600,
        2080.000000,
        2298.244587,
        -294.322508,
        -1305.505431,
        -2072.527484,
        -941.181913,
        1971.576267,
        2292.279676,
        -297.437603,
        -933.395523,
        1955.796218,
        270.876777,
        -19.735288,
        -148.030026,
        -235.797550,
        -121.644192,
        237.105897,
        -1284.271006,
        -2076.091569,
        -1097.444394,
        2089.732588,
        -1284.230560,
        -2071.967906,
        -1097.452643,
        2085.603750,
        2279.413447,
        -288.535397,
        2298.244414,
        -294.322424,
        -1305.505281,
        -2072.527363,
        -941.181880,
        1971.576093,
        2278.613714,
        -298.334481,
        -1309.988345,
        -2072.712391,
        -940.787032,
        1961.661167,
        2298.235778,
        -294.295354,
        -1305.494402,
        -2072.534569,
        -941.195915,
        1971.563762,
        -923.177945,
        1941.010818,
        2386.700105,
        -181.385380,
        -1293.526138,
        -2090.093030,
        -1055.898256,
        2061.674605
    ], dtype=float)
    assert_v_tolerance(results.v_final[:76], expected_v[:76])

def test_powerflowrunner_ieee_thirteen_bus_overhead():
    results = execute_glm_case("ieee_13_node_overhead_nr", "test_IEEE_13_NR_overhead.glm")
    
    
    
    expected_v = np.array([
        
    ], dtype=float)
    assert_v_tolerance(results.v_final[:18], expected_v[:18])

# Requires resistive loads, current loads, and IP loads
def test_powerflowrunner_ieee_thirteen_bus():
    results = execute_glm_case("ieee_13_node_nr", "test_IEEE_13_NR.glm")
    
    expected_v = np.array([
        2442.766782,
        -108.916789,
        -1314.775436,
        -2123.156359,
        -1137.361833,
        2159.061304,
        2551.838732,
        0.026586,
        -1260.900822,
        -2183.973852,
        -1283.445032,
        2222.941672,
        2450.159062,
        -106.480827,
        -1315.483449,
        -2128.069895,
        -1140.432894,
        2164.524602,
        2401.777100,
        0.000000,
        -1200.888600,
        -2080.000000,
        -1200.888600,
        2080.000000,
        2368.071362,
        -219.430952,
        -1352.200812,
        -2135.101781,
        -1029.628252,
        2117.238224,
        2363.393048,
        -219.797727,
        -1023.361479,
        2115.173477,
        275.057129,
        -15.517488,
        -150.938282,
        -239.458838,
        -126.758858,
        245.578067,
        -1310.510972,
        -2105.222586,
        -1139.239687,
        2159.781233,
        -1311.080781,
        -2099.946317,
        -1138.627939,
        2154.503202,
        2354.092425,
        -214.377082,
        2368.071183,
        -219.430874,
        -1352.200657,
        -2135.101659,
        -1029.628215,
        2117.238035,
        2351.548001,
        -228.228718,
        -1361.834443,
        -2135.753512,
        -1028.161791,
        2112.874103,
        2368.063607,
        -219.416279,
        -1352.199784,
        -2135.096820,
        -1029.633379,
        2117.226532,
        -1015.480115,
        2113.920787,
        2430.265602,
        -134.701751,
        -1324.106564,
        -2128.854086,
        -1110.249873,
        2152.154125
    ], dtype=float)
    assert_v_tolerance(results.v_final[:82], expected_v[:82])


def test_powerflowrunner_kersting_example_11_1():
    results = execute_glm_case("kersting_example_11_1")
    expected_v = np.array([
        -3599.779000,
        6235.000000,
        -59.9952,
        103.916,
        -59.9951,
        103.916
        ])
    assert_v_tolerance(results.v_final[:6], expected_v[:6])

def test_powerflowrunner_kersting_example_11_1_altered():
    results = execute_glm_case("kersting_example_11_1_altered")
    expected_v = np.array([
        -3599.779000,
        6235.000000,
        -59.9963,
        103.917,
        -59.9963,
        103.917,
        -59.9963,
        103.917,
        -59.9963,
        103.917
        ])
    assert_v_tolerance(results.v_final[:10], expected_v[:10])

def test_powerflowrunner_kersting_example_11_1_altered_more():
    results = execute_glm_case("kersting_example_11_1_altered_more")
    expected_v = np.array([
        -3599.779000,
        6235.000000,
        -119.532,
        207.578,
        -119.532,
        207.578
        ])
    assert_v_tolerance(results.v_final[:6], expected_v[:6])

def test_powerflowrunner_kersting_example_11_2():
    results = execute_glm_case("kersting_example_11_2")
    expected_v = np.array([
        -3599.779000,
        6235.000000,
        -59.9952,
        103.916,
        -59.9951,
        103.916,
        -59.9953,
        103.915,
        -59.995,
        103.913
        ])
    assert_v_tolerance(results.v_final[:10], expected_v[:10])

def test_powerflowrunner_kersting_example_11_2_altered():
    results = execute_glm_case("kersting_example_11_2_altered")
    expected_v = np.array([
        -3599.779000,
        6235.000000,
        -59.9952,
        103.916,
        -59.9951,
        103.916,
        -59.9953,
        103.915,
        -59.995,
        103.913,
        -59.9953,
        103.915,
        -59.995,
        103.912,
        -59.9953,
        103.915,
        -59.995,
        103.911
        ])
    assert_v_tolerance(results.v_final[:18], expected_v[:18])

def test_powerflowrunner_kersting_example_11_2_altered_more():
    results = execute_glm_case("kersting_example_11_2_altered_more")
    expected_v = np.array([
        -3599.779000,
        6235.000000,
        -59.7648,
        103.789,
        -59.7648,
        103.789,
        -59.7932,
        103.388,
        -59.7932,
        103.388,
        -59.8017,
        103.267,
        -59.8017,
        103.267,
        -59.8103,
        103.147,
        -59.8103,
        103.147
        ])
    assert_v_tolerance(results.v_final[:18], expected_v[:18])

def test_powerflowrunner_3phasesource_CT_line_load():
    results = execute_glm_case("3phasesource_CT_line_load")
    expected_v = np.array([
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        -58.6478,
        102.067,
        -58.6478,
        102.067,
        -58.5609,
        101.664,
        -58.5609,
        101.664
        ])
    assert_v_tolerance(results.v_final[:14], expected_v[:14])

def test_powerflowrunner_center_tap_xfmr_and_triplex_line():
    results = execute_glm_case("center_tap_xfmr_and_triplex_line")
    expected_v = np.array([
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        7216.880000,
        -0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        -60,
        103.923,
        -60,
        103.923,
        -60,
        103.923,
        -60,
        103.923,
        -60,
        103.923,
        -60,
        103.923,
        -60,
        103.923,
        -60,
        103.923
        ])
    assert_v_tolerance(results.v_final[:34], expected_v[:34])

def test_powerflowrunner_regulator_center_tap_xfmr_and_triplex_line():
    results = execute_glm_case("regulator_center_tap_xfmr_and_triplex_line")
    expected_v = np.array([
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        7216.880000,
        -0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        7216.880000,
        -0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        7216.880000,
        -0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        -60,
        103.923,
        -60,
        103.923,
        -60,
        103.923,
        -60,
        103.923
    ])
    assert_v_tolerance(results.v_final[:32], expected_v[:32])

def test_powerflowrunner_center_tap_xfmr_and_triplex_load():
    results = execute_glm_case("center_tap_xfmr_and_triplex_load")
    expected_v = np.array([

        # # load power imag = 25000
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440000,
        # 6250.000000,
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440577,
        # 6250.000002,
        # 7216.998714,
        # -0.229153,
        # -3608.321286,
        # -6250.229153,
        # -3608.151120,
        # 6249.294101,
        # -65.0952,
        # 78.9498,
        # -65.0952,
        # 78.9498

        # # load power imag = 0.000001
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440000,
        # 6250.000000,
        # 7216.880000,
        # -0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440012,
        # 6249.999956,
        # 7216.899995,
        # 0.004283,
        # -3608.420005,
        # -6249.995717,
        # -3608.380013,
        # 6250.007322,
        # -58.1979,
        # 103.012,
        # -58.1979,
        # 103.012

        # # load power real = 30000
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440000,
        # 6250.000000,
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440351,
        # 6249.999284,
        # 7217.236665,
        # 0.009524,
        # -3608.083335,
        # -6249.990476,
        # -3607.387618,
        # 6249.933772,
        # -32.0032,
        # 82.5265,
        # -32.0032,
        # 82.5265

        # # load power real = 1
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440000,
        # 6250.000000,
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440023,
        # 6250.000006,
        # 7216.882393,
        # -0.010296,
        # -3608.437607,
        # -6250.010296,
        # -3608.435676,
        # 6249.969062,
        # -60.4549,
        # 102.983,
        # -60.4549,
        # 102.983
        
        # # xfmr power = 0.5
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440000,
        # 6250.000000,
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440047,
        # 6249.999951,
        # 7216.908984,
        # -0.008559,
        # -3608.411016,
        # -6250.008559,
        # -3608.356946,
        # 6249.967146,
        # -43.0514,
        # 79.3687,
        # -43.0514,
        # 79.3687

        # # xfmr power = 5000
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440000,
        # 6250.000000,
        # 7216.880000,
        # -0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440034,
        # 6249.999963,
        # 7216.901973,
        # -0.005858,
        # -3608.418027,
        # -6250.005858,
        # -3608.376870,
        # 6249.976948,
        # -59.9976,
        # 103.921,
        # -59.9976,
        # 103.921

        # # xfmr reactance = 0.00000000001
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440000,
        # 6250.000000,
        # 7216.880000,
        # -0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440035,
        # 6249.999962,
        # 7216.902328,
        # -0.005779,
        # -3608.417672,
        # -6250.005779,
        # -3608.375804,
        # 6249.977089,
        # -59.9042,
        # 102.031,
        # -59.9042,
        # 102.031

        # # xfmr reactance = 0.2
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440000,
        # 6250.000000,
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440049,
        # 6249.999965,
        # 7216.903884,
        # -0.012145,
        # -3608.416116,
        # -6250.012145,
        # -3608.372905,
        # 6249.957938,
        # -31.4288,
        # 96.8696,
        # -31.4288,
        # 96.8696

        
        # # xfmr resistance = 0.25
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440000,
        # 6250.000000,
        # 7216.880000,
        # -0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440047,
        # 6249.999923,
        # 7216.920168,
        # -0.002541,
        # -3608.399832,
        # -6250.002541,
        # -3608.322434,
        # 6249.981905,
        # -44.7551,
        # 50.9276,
        # -44.7551,
        # 50.9276

        # Original
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        7216.880000,
        -0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440035,
        6249.999962,
        7216.902385,
        -0.006017,
        -3608.417615,
        -6250.006017,
        -3608.375699,
        6249.976372,
        -58.6533,
        102.072,
        -58.6533,
        102.072
        ])
    assert_v_tolerance(results.v_final[:22], expected_v[:22])

def test_powerflowrunner_center_tap_xfmr_and_single_line_to_load():
    results = execute_glm_case("center_tap_xfmr_and_single_line_to_load")
    expected_v = np.array([

        # # insulation thickness = 800 and gmr = 0.0000000001
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440000,
        # 6250.000000,
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440035,
        # 6249.999962,
        # 7216.902428,
        # -0.006093,
        # -3608.417572,
        # -6250.006093,
        # -3608.375592,
        # 6249.976137,
        # -58.6547,
        # 102.063,
        # -58.6547,
        # 102.063,
        # -58.2251,
        # 101.958,
        # -58.2251,
        # 101.958

        # # insulation thickness = 800
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440000,
        # 6250.000000,
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440035,
        # 6249.999962,
        # 7216.902415,
        # -0.006039,
        # -3608.417585,
        # -6250.006039,
        # -3608.375616,
        # 6249.976298,
        # -58.6523,
        # 102.068,
        # -58.6523,
        # 102.068,
        # -58.5046,
        # 101.952,
        # -58.5046,
        # 101.952

        # # insulation thickness = 0.00000008
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440000,
        # 6250.000000,
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440035,
        # 6249.999962,
        # 7216.902409,
        # -0.006015,
        # -3608.417591,
        # -6250.006015,
        # -3608.375626,
        # 6249.976371,
        # -58.6513,
        # 102.07,
        # -58.6513,
        # 102.07,
        # -58.6308,
        # 101.95,
        # -58.6308,
        # 101.95

        # # gmr = 0.0000000001
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440000,
        # 6250.000000,
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440035,
        # 6249.999962,
        # 7216.902423,
        # -0.006070,
        # -3608.417577,
        # -6250.006070,
        # -3608.375602,
        # 6249.976207,
        # -58.6537,
        # 102.065,
        # -58.6537,
        # 102.065,
        # -58.3461,
        # 101.956,
        # -58.3461,
        # 101.956

        # # gmr = 0.0000111
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440000,
        # 6250.000000,
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440035,
        # 6249.999962,
        # 7216.902414,
        # -0.006036,
        # -3608.417586,
        # -6250.006036,
        # -3608.375617,
        # 6249.976308,
        # -58.6522,
        # 102.069,
        # -58.6522,
        # 102.069,
        # -58.5213,
        # 101.952,
        # -58.5213,
        # 101.952

        # # gmr = 100
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440000,
        # 6250.000000,
        # 7216.880000,
        # 0.000000,
        # -3608.440000,
        # -6250.000000,
        # -3608.440035,
        # 6249.999962,
        # 7216.902403,
        # -0.005990,
        # -3608.417597,
        # -6250.005990,
        # -3608.375638,
        # 6249.976447,
        # -58.6502,
        # 102.073,
        # -58.6502,
        # 102.073,
        # -58.7624,
        # 101.946,
        # -58.7624,
        # 101.946

        # Original
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440035,
        6249.999962,
        7216.902410,
        -0.006016,
        -3608.417590,
        -6250.006016,
        -3608.375626,
        6249.976368,
        -58.6513,
        102.07,
        -58.6513,
        102.07,
        -58.6254,
        101.95,
        -58.6254,
        101.95
    ])
    assert_v_tolerance(results.v_final[:26], expected_v[:26])

def test_powerflowrunner_center_tap_xfmr_and_line_to_load():
    results = execute_glm_case("center_tap_xfmr_and_line_to_load")
    expected_v = np.array([
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440035,
        6249.999962,
        7216.902459,
        -0.006015,
        -3608.417541,
        -6250.006015,
        -3608.375479,
        6249.976360,
        -58.6474,
        102.067,
        -58.6474,
        102.067,
        -58.6214,
        101.947,
        -58.6214,
        101.947,
        -58.5953,
        101.826,
        -58.5953,
        101.826,
        -58.5693,
        101.705,
        -58.5693,
        101.705
    ])
    assert_v_tolerance(results.v_final[:34], expected_v[:34])

def test_powerflowrunner_regulator_center_tap_xfmr_and_line_to_load():
    results = execute_glm_case("regulator_center_tap_xfmr_and_line_to_load")
    expected_v = np.array([
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        7216.880000,
        -0.000000,
        -3608.440000,
        -6250.000000,
        -3608.439997,
        6249.999927,
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440032,
        6249.999889,
        7216.902410,
        -0.006016,
        -3608.417590,
        -6250.006016,
        -3608.375623,
        6249.976295,
        -58.6513,
        102.07,
        -58.6513,
        102.07,
        -58.6254,
        101.95,
        -58.6254,
        101.95
    ])
    assert_v_tolerance(results.v_final[:32], expected_v[:32])
    
def test_powerflowrunner_triplex_load_class():
    results = execute_glm_case("triplex_load_class")
    expected_v = np.array([
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        7216.880000,
        -0.000000,
        -3608.440000,
        -6250.000000,
        -3608.439998,
        6249.999964,
        7216.880000,
        -0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440016,
        6249.999945,
        7216.891155,
        -0.002974,
        -3608.428845,
        -6250.002974,
        -3608.407948,
        6249.988262,
        -59.1807,
        102.534,
        -59.4739,
        103.471,
        -59.0964,
        102.347,
        -59.5323,
        103.538
    ])
    assert_v_tolerance(results.v_final[:32], expected_v[:32])

def test_powerflowrunner_unbalanced_triplex_load():
    results = execute_glm_case("unbalanced_triplex_load")
    expected_v = np.array([
        7216.880000,
        0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440000,
        6250.000000,
        7216.880000,
        -0.000000,
        -3608.440000,
        -6250.000000,
        -3608.439998,
        6249.999961,
        7216.880000,
        -0.000000,
        -3608.440000,
        -6250.000000,
        -3608.440017,
        6249.999941,
        7216.891891,
        -0.003095,
        -3608.428109,
        -6250.003095,
        -3608.405814,
        6249.987708,
        -59.4373,
        103.445,
        -59.1194,
        102.45,
        -61.5221,
        105.81,
        -56.0874,
        95.8343
    ])
    assert_v_tolerance(results.v_final[:32], expected_v[:32])
