from itertools import count
import os
from logic.networkmodel import TxNetworkModel
from logic.powerflow import FilePowerFlow, PowerFlow
from logic.powerflowresults import PowerFlowResults
from scipy.io import loadmat
from logic.powerflowsettings import PowerFlowSettings
from models.positiveseq.branch import Branch

from models.shared.bus import GROUND, Bus
from models.shared.single_phase_transformer import SinglePhaseTransformer
from models.shared.slack import Slack

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
    test_runner = FilePowerFlow(filepath)
    results = test_runner.execute()
    assert results.is_success
    mat_result = loadmat(get_positiveseq_mat_result("GS-4_prior_solution"))
    assert_mat_comparison(mat_result, results)

def test_IEEE_14_prior_solution():
    filepath = get_positiveseq_raw("IEEE-14_prior_solution")
    test_runner = FilePowerFlow(filepath)
    results = test_runner.execute()
    assert results.is_success
    mat_result = loadmat(get_positiveseq_mat_result("IEEE-14_prior_solution"))
    assert_mat_comparison(mat_result, results)

def test_isolated_xfmr_network():
    next_idx = count()

    from_bus = Bus(1, 1, 0.1, 0.1, None, None, None)
    from_bus.assign_nodes(next_idx, False)
    to_bus = Bus(2, 1, 0.1, 0.1, None, None, None)
    to_bus.assign_nodes(next_idx, False)

    xfrmr = SinglePhaseTransformer(from_bus, GROUND, to_bus, GROUND, 1.1, 1.2, True, 1.1, 1.3, 0, 0, None)
    xfrmr.assign_nodes(next_idx, False)

    slack = Slack(from_bus, 1, 0, 0.1, 0.1)
    slack.assign_nodes(next_idx, False)

    network = TxNetworkModel(buses=[from_bus, to_bus], transformers=[xfrmr], slack=[slack])
    network.size_Y = next(next_idx)

    powerflow = PowerFlow(network, PowerFlowSettings())

    result = powerflow.execute()

    assert result.is_success
    assert result.max_residual < 1e-10