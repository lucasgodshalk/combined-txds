from logic.powerflowsettings import PowerFlowSettings
from test_threephase_basic import assert_glm_case_gridlabd_results, get_glm_case_file
from logic.network.loadfactor import modify_load_factor
from logic.powerflow import PowerFlow
from logic.network.networkloader import NetworkLoader
from logic.powerflowresults import PowerFlowResults
from logic.powerflowsettings import PowerFlowSettings

def test_network_model():
    assert_glm_case_gridlabd_results("network_model")

def test_network_model_case1():
    assert_glm_case_gridlabd_results("network_model_case1")

def test_network_model_case1_342():
    assert_glm_case_gridlabd_results("network_model_case1_342")

def test_network_model_case2():
    assert_glm_case_gridlabd_results("network_model_case2")

def test_infeasibility_r1_12_47_1():
    filepath = get_glm_case_file("r1_12_47_1")
    settings = PowerFlowSettings(max_iters=10, tx_stepping=True)
    network = NetworkLoader(settings).from_file(filepath)
    modify_load_factor(network, 10, 10)
    powerflow = PowerFlow(network, settings)
    results = powerflow.execute()

    assert results.is_success