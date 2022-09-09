from logic.powerflowsettings import PowerFlowSettings
from test_threephase_basic import assert_glm_case_gridlabd_results

def test_network_model():
    assert_glm_case_gridlabd_results("network_model")

def test_network_model_case1():
    assert_glm_case_gridlabd_results("network_model_case1")

def test_network_model_case1_342():
    assert_glm_case_gridlabd_results("network_model_case1_342")

def test_network_model_case2():
    assert_glm_case_gridlabd_results("network_model_case2")