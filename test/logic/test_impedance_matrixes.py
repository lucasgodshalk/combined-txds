
import itertools
import math
import os
import numpy as np
from logic.powerflow import PowerFlow
from logic.networkloader import NetworkLoader
from logic.powerflowsettings import PowerFlowSettings
from test_threephase_basic import get_glm_case_file, DATA_DIR
import cmath
from ditto.readers.gridlabd.read import compute_triplex_impedance, compute_underground_capacitance
import xml.etree.ElementTree as ET

def test_ieee_four_bus_impedances():
    glmpath = get_glm_case_file("ieee_four_bus")
    settings = PowerFlowSettings()
    network = NetworkLoader(settings).from_file(glmpath)
    powerflow = PowerFlow(network, settings)

    lines = parse_gridlabd_impedance_xml("ieee_four_bus")

    compare_line_impedances(powerflow.network.lines, lines)

def test_ieee_thirteen_bus_overhead_impedances():
    glmpath = get_glm_case_file("ieee_13_node_overhead_nr")
    settings = PowerFlowSettings()
    network = NetworkLoader(settings).from_file(glmpath)
    powerflow = PowerFlow(network, settings)

    lines = parse_gridlabd_impedance_xml("ieee_13_node_overhead_nr")

    compare_line_impedances(powerflow.network.lines, lines)

def test_gc_12_47_1_impedances():
    glmpath = get_glm_case_file("gc_12_47_1")
    settings = PowerFlowSettings()
    network = NetworkLoader(settings).from_file(glmpath)
    powerflow = PowerFlow(network, settings)

    lines = parse_gridlabd_impedance_xml("gc_12_47_1")

    compare_line_impedances(powerflow.network.lines, lines)

def test_r1_12_47_1_impedances():
    glmpath = get_glm_case_file("r1_12_47_1")
    settings = PowerFlowSettings()
    network = NetworkLoader(settings).from_file(glmpath)
    powerflow = PowerFlow(network, settings)

    lines = parse_gridlabd_impedance_xml("r1_12_47_1")

    compare_line_impedances(powerflow.network.lines, lines)


def test_network_model_case1_impedances():
    glmpath = get_glm_case_file("network_model_case1")
    settings = PowerFlowSettings()
    network = NetworkLoader(settings).from_file(glmpath)
    powerflow = PowerFlow(network, settings)

    lines = parse_gridlabd_impedance_xml("network_model_case1")

    compare_line_impedances(powerflow.network.lines, lines)

def test_ieee_four_bus_overhead_3_wire():
    glmpath = get_glm_case_file("ieee_four_bus_delta_delta_transformer")
    settings = PowerFlowSettings()
    network = NetworkLoader(settings).from_file(glmpath)
    powerflow = PowerFlow(network, settings)

    branch = powerflow.network.lines[0]

    Z_expected = np.array([
        [0.4013+1.4133j, 0.0953+0.8515j, 0.0953+0.7266j],
        [0.0953+0.8515j, 0.4013+1.4133j, 0.0953+0.7802j],
        [0.0953+0.7266j, 0.0953+0.7802j, 0.4013+1.4133j]
    ])

    #need to convert impedances to ohm/mile
    assert np.allclose(np.abs(branch.impedances / .3787879), np.abs(Z_expected), atol=1e-3)

class WireTest:
    def __init__(
        self, 
        phase, 
        resistance=None, 
        gmr=None, 
        overhead_diameter=None, 
        insulation_thickness=None,
        outer_diameter=None,
        concentric_neutral_diameter=None,
        shield_gmr=None,
        conductor_diameter=None,
        concentric_neutral_nstrand=None,
        num_strands=None
        ):
        self.phase = phase

        self.resistance = resistance
        self.gmr = gmr
        self.diameter = overhead_diameter
        self.insulation_thickness = insulation_thickness
        self.outer_diameter = outer_diameter
        self.concentric_neutral_diameter = concentric_neutral_diameter
        self.shield_gmr = shield_gmr
        self.conductor_diameter = conductor_diameter
        self.concentric_neutral_nstrand = concentric_neutral_nstrand
        self.concentric_neutral_nstrand = num_strands

def test_compute_triplex_impedance_matrix():
    wire_list = [
        WireTest(phase="1", resistance=0.48, gmr=0.0158, overhead_diameter=0.522, insulation_thickness=0.08),
        WireTest(phase="2", resistance=0.48, gmr=0.0158, overhead_diameter=0.522, insulation_thickness=0.08),
        WireTest(phase="N", resistance=0.48, gmr=0.0158, overhead_diameter=0.522, insulation_thickness=0.08),
    ]

    impedence = compute_triplex_impedance(wire_list, kron_reduce=False)

    assert cmath.isclose(impedence[0][0], complex(0.5753, 1.4660), abs_tol=1e-3)
    assert cmath.isclose(impedence[0][1], complex(0.0953, 1.31067), abs_tol=1e-3)
    assert cmath.isclose(impedence[0][2], complex(0.0953, 1.32581), abs_tol=1e-3)

def test_computer_underground_capacitance():
    R_b = 0.631
    neutral_diameter = 0.0641
    phase_diameter = 0.567
    outer_diameter = R_b*2 + neutral_diameter
    num_strands = 13

    wire_list = [
        WireTest(phase="A", shield_gmr=0, concentric_neutral_diameter=neutral_diameter, conductor_diameter=phase_diameter, outer_diameter=outer_diameter, num_strands=num_strands),
        WireTest(phase="B", shield_gmr=0, concentric_neutral_diameter=neutral_diameter, conductor_diameter=phase_diameter, outer_diameter=outer_diameter, num_strands=num_strands),
        WireTest(phase="C", shield_gmr=0, concentric_neutral_diameter=neutral_diameter, conductor_diameter=phase_diameter, outer_diameter=outer_diameter, num_strands=num_strands),
        WireTest(phase="N", shield_gmr=0, concentric_neutral_diameter=neutral_diameter, conductor_diameter=phase_diameter, outer_diameter=outer_diameter, num_strands=num_strands)
    ]

    capacitance = compute_underground_capacitance(wire_list)

    compare = [[9.2980664e-5j, 0j, 0j], [0j, 9.2980664e-5j, 0j], [0j, 0j, 9.2980664e-5j]]

    assert np.allclose(capacitance, compare, atol=1e-4)

def parse_gridlabd_impedance_xml(casename):
    impedance_xml = get_gridlabd_impedance_file(casename)
    tree = ET.parse(impedance_xml)
    root = tree.getroot()

    lines = []

    for line in itertools.chain(root.iter('overhead_line'), root.iter('underground_line'), root.iter('triplex_line')):
        id = line.find("name").text
        from_node = line.find("from_node").text.split(":")[1]
        to_node = line.find("to_node").text.split(":")[1]
        phases = line.find("phases").text
        length = line.find("length").text

        b_matrix_xml = line.find("b_matrix")

        b_matrix = np.zeros((3, 3)).astype(complex)

        for entry in b_matrix_xml:
            tag = entry.tag
            row = int(tag[1])
            col = int(tag[2])
            val_str = entry.text
            val = complex(val_str)

            b_matrix[row - 1, col - 1] = val
        
        b_matrix = b_matrix[~np.all(b_matrix == 0, axis=1), :]
        b_matrix = b_matrix[:, ~np.all(b_matrix == 0, axis=0)]

        lines.append((id, phases, length, from_node, to_node, b_matrix))
    
    return lines

def get_gridlabd_impedance_file(casename, impedance_file_name = "impedance.xml"):
    return os.path.join(DATA_DIR, casename, impedance_file_name)

def compare_line_impedances(powerflow_lines, gridlabd_lines):
    for name, phases, length, from_node, to_node, b_matrix in gridlabd_lines:
        for line in powerflow_lines:
            if from_node == line.from_element and to_node == line.to_element:
                assert np.allclose(np.abs(line.impedances), np.abs(b_matrix), atol=1e-3), f"Line impedance mismatch at {name} ({from_node}:{to_node})"
                break
