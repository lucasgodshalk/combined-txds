import os
from logic.powerflow import PowerFlow
from logic.powerflowresults import PowerFlowResults
from scipy.io import loadmat

CURR_DIR = os.path.realpath(os.path.dirname(__file__))

def get_positiveseq_raw(casename):
    file_path = os.path.join("data", "positiveseq", f"{casename}.RAW")
    full_file_path = os.path.join(CURR_DIR, file_path)
    return full_file_path

def get_positiveseq_mat_result(casename):
    file_path = os.path.join("result_comparison", f"{casename}.mat")
    full_file_path = os.path.join(CURR_DIR, file_path)
    return full_file_path

def assert_mat_comparison(mat, results: PowerFlowResults):
    for idx in range(len(mat['sol']['bus'][0][0])):
        bus = mat['sol']['bus'][0][0][idx][0]
        V_mag = mat['sol']['bus'][0][0][idx][7]
        V_ang = mat['sol']['bus'][0][0][idx][8]

        simulator_V_mag = results.bus_results[idx].V_mag
        simulator_V_ang = results.bus_results[idx].V_ang
        
        mag_diff = abs(V_mag - simulator_V_mag)
        ang_diff = abs(V_ang - simulator_V_ang)

        assert mag_diff < 1e-4
        assert ang_diff < 1e-4

def test_GS_4_prior_solution():
    filepath = get_positiveseq_raw("GS-4_prior_solution")
    test_runner = PowerFlow(filepath)
    results = test_runner.execute()
    assert results.is_success
    mat_result = loadmat(get_positiveseq_mat_result("GS-4_prior_solution"))
    assert_mat_comparison(mat_result, results)

def test_IEEE_14_prior_solution():
    filepath = get_positiveseq_raw("IEEE-14_prior_solution")
    test_runner = PowerFlow(filepath)
    results = test_runner.execute()
    assert results.is_success
    mat_result = loadmat(get_positiveseq_mat_result("IEEE-14_prior_solution"))
    assert_mat_comparison(mat_result, results)

    

