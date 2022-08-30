from logic.powerflowsettings import PowerFlowSettings
from test_threephase_basic import assert_glm_case_gridlabd_results

def test_gc_12_47_1():
    assert_glm_case_gridlabd_results("gc_12_47_1")

def test_r1_12_47_1():
    assert_glm_case_gridlabd_results("r1_12_47_1")

def test_r1_12_47_2():
    assert_glm_case_gridlabd_results("r1_12_47_2")

def test_r1_12_47_3():
    assert_glm_case_gridlabd_results("r1_12_47_3")

def test_r1_12_47_4():
    assert_glm_case_gridlabd_results("r1_12_47_4")

def test_r1_25_00_1():
    assert_glm_case_gridlabd_results("r1_25_00_1")

def test_r2_12_47_1():
    assert_glm_case_gridlabd_results("r2_12_47_1")

def test_r2_12_47_3():
    assert_glm_case_gridlabd_results("r2_12_47_3")

def test_r2_25_00_1():
    assert_glm_case_gridlabd_results("r2_25_00_1", settings=PowerFlowSettings(tolerance=1e-4))

def test_r2_35_00_1():
    assert_glm_case_gridlabd_results("r2_35_00_1")

def test_r3_12_47_1():
    assert_glm_case_gridlabd_results("r3_12_47_1")

def test_r3_12_47_2():
    assert_glm_case_gridlabd_results("r3_12_47_2")

def test_r3_12_47_3():
    assert_glm_case_gridlabd_results("r3_12_47_3")

def test_r4_12_47_1():
    assert_glm_case_gridlabd_results("r4_12_47_1")

def test_r4_12_47_2():
    assert_glm_case_gridlabd_results("r4_12_47_2")

def test_r4_25_00_1():
    assert_glm_case_gridlabd_results("r4_25_00_1")

def test_r5_12_47_1():
    assert_glm_case_gridlabd_results("r5_12_47_1")

def test_r5_12_47_2():
    assert_glm_case_gridlabd_results("r5_12_47_2")

def test_r5_12_47_3():
    assert_glm_case_gridlabd_results("r5_12_47_3")

def test_r5_12_47_4():
    assert_glm_case_gridlabd_results("r5_12_47_4")

def test_r5_12_47_5():
    assert_glm_case_gridlabd_results("r5_12_47_5")

def test_r5_25_00_1():
    assert_glm_case_gridlabd_results("r5_25_00_1", settings=PowerFlowSettings(tolerance=1e-4))

def test_r5_35_00_1():
    assert_glm_case_gridlabd_results("r5_35_00_1", settings=PowerFlowSettings(tolerance=1e-3))
