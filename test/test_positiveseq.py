from itertools import count
import os
from logic.network.networkmodel import TxNetworkModel
from logic.powerflow import PowerFlow
from logic.powerflowresults import PowerFlowResults
from scipy.io import loadmat
from logic.powerflowsettings import PowerFlowSettings
from logic.network.networkloader import NetworkLoader
from models.optimization.L2infeasibility import load_infeasibility_analysis
from models.components.bus import GROUND, Bus
from models.components.transformer import Transformer
from models.components.slack import Slack
from models.components.voltagesource import VoltageSource

CURR_DIR = os.path.realpath(os.path.dirname(__file__))

def get_positiveseq_raw(casename):
    file_path = os.path.join("data", "positive_seq", f"{casename}.RAW")
    full_file_path = os.path.join(CURR_DIR, file_path)
    return full_file_path

def get_positiveseq_mat_result(casename):
    file_path = os.path.join("data", "positive_seq", "result_comparison", f"{casename}.mat")
    full_file_path = os.path.join(CURR_DIR, file_path)
    return full_file_path

def assert_mat_comparison(mat, results: PowerFlowResults):
    for idx in range(len(mat['sol']['bus'][0][0])):
        bus = mat['sol']['bus'][0][0][idx][0]
        V_mag = mat['sol']['bus'][0][0][idx][7]
        V_ang = mat['sol']['bus'][0][0][idx][8]

        simulator_V_mag = results.bus_results[idx].V_mag
        simulator_V_ang = results.bus_results[idx].V_deg
        
        mag_diff = abs(V_mag - simulator_V_mag)
        ang_diff = abs(V_ang - simulator_V_ang)

        assert mag_diff < 1e-4
        assert ang_diff < 1e-4

def execute_positiveseq_raw(casename, settings = PowerFlowSettings(), infeasibility_analysis = False):
    filepath = get_positiveseq_raw(casename)
    network = NetworkLoader(settings).from_file(filepath)
    if infeasibility_analysis:
        network.optimization = load_infeasibility_analysis(network)
    powerflow = PowerFlow(network, settings)
    return powerflow.execute()

def test_GS_4_prior_solution():
    results = execute_positiveseq_raw("GS-4_prior_solution")
    assert results.is_success
    assert results.max_residual < 1e-8
    mat_result = loadmat(get_positiveseq_mat_result("GS-4_prior_solution"))
    assert_mat_comparison(mat_result, results)

def test_infeasibility_analysis_GS_4_prior_solution():
    results = execute_positiveseq_raw("GS-4_prior_solution", PowerFlowSettings(), infeasibility_analysis=True)
    assert results.is_success
    assert results.max_residual < 1e-8
    assert results.infeasibility_totals == (0, 0)

def test_infeasibility_analysis_GS_4_stressed():
    results = execute_positiveseq_raw("GS-4_stressed", PowerFlowSettings(voltage_limiting=True), infeasibility_analysis=True)
    assert results.is_success
    assert results.max_residual < 1e-6
    P, Q = results.infeasibility_totals
    assert P > 0
    assert Q > 0

def test_voltage_limiting():
    results = execute_positiveseq_raw("GS-4_prior_solution", PowerFlowSettings(voltage_limiting=True))
    assert results.is_success
    assert results.max_residual < 1e-8
    mat_result = loadmat(get_positiveseq_mat_result("GS-4_prior_solution"))
    assert_mat_comparison(mat_result, results)

def test_IEEE_14_prior_solution():
    results = execute_positiveseq_raw("IEEE-14_prior_solution")
    assert results.is_success
    assert results.max_residual < 1e-8
    mat_result = loadmat(get_positiveseq_mat_result("IEEE-14_prior_solution"))
    assert_mat_comparison(mat_result, results)

def test_isolated_grnded_xfmr_network():
    from_bus_pos = Bus(1, 1, 0.1, 0.1, None, None, None)

    from_bus_neg = Bus(2, 1, 0.1, 0.1, None, None, None)

    to_bus = Bus(3, 1, 0.1, 0.1, None, None, None)

    xfrmr = Transformer(from_bus_pos, from_bus_neg, to_bus, GROUND, 1.1, 1.2, True, 1.1, 1.3, 0, 0, None)

    slack = Slack(from_bus_pos, 1, 0, 0.1, 0.1)

    vs = VoltageSource(from_bus_neg, GROUND, 0, 0)

    network = TxNetworkModel()
    network.buses = [from_bus_pos, from_bus_neg, to_bus]
    network.transformers = [xfrmr]
    network.slack = [slack]
    network.voltage_sources = [vs]

    powerflow = PowerFlow(network, PowerFlowSettings(debug=True))

    results = powerflow.execute()

    assert results.is_success
    assert results.max_residual < 1e-10
