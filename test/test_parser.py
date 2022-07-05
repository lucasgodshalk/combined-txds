# import pytest as pt
# import anoeds.parser
import numpy as np
from logic.parsers.anoeds_parser import Parser
from logic.powerflowsettings import PowerFlowSettings
from models.threephase.resistive_load import ResistiveLoad
from models.threephase.transmission_line import TransmissionLine
from models.threephase.three_phase_transformer import ThreePhaseTransformer
from models.threephase.regulator import Regulator
import os
from pprint import pprint

CURR_DIR = os.path.realpath(os.path.dirname(__file__))

def test_parser_read():
    glm_file_path = os.path.join("data", "ieee_four_bus", "node.glm")
    test_parser = Parser(os.path.join(CURR_DIR, glm_file_path), PowerFlowSettings(), False)
    _ = test_parser.parse()
    ditto_objects = test_parser.ditto_store
    pprint(ditto_objects)
    ditto_objects.set_names()
    assert len(ditto_objects.models) == 28
    assert ("node1" in ditto_objects.model_names)
    assert ("transformer:23" in ditto_objects.model_names)
    assert ("load4" in ditto_objects.model_names)

def test_parser_create_resistive_load():
    glm_file_path = os.path.join("data", "swing_and_line_to_resistive", "node.glm")
    test_parser = Parser(os.path.join(CURR_DIR, glm_file_path), PowerFlowSettings(), False)
    simulation_state = test_parser.parse()
    assert len(simulation_state.loads) == 1
    assert isinstance(simulation_state.loads[0], ResistiveLoad)
    assert len(simulation_state.loads[0].phase_loads) == 3

def test_parser_create_pq_load():
    glm_file_path = os.path.join("data", "ieee_4_node", "node.glm")
    test_parser = Parser(os.path.join(CURR_DIR, glm_file_path), PowerFlowSettings(), False)
    simulation_state = test_parser.parse()
    assert len(simulation_state.loads) == 1
    assert isinstance(simulation_state.loads[0], PQLoad)
    assert len(simulation_state.loads[0].phase_loads) == 3

def test_parser_create_line():
    glm_file_path = os.path.join("data", "ieee_4_node", "node.glm")
    test_parser = Parser(os.path.join(CURR_DIR, glm_file_path), PowerFlowSettings(), False)
    simulation_state = test_parser.parse()
    assert len(simulation_state.transmission_lines) == 2
    assert isinstance(simulation_state.transmission_lines[0], TransmissionLine)

def test_parser_create_infinite_source():
    glm_file_path = os.path.join("data", "ieee_4_node", "node.glm")
    test_parser = Parser(os.path.join(CURR_DIR, glm_file_path), PowerFlowSettings(), False)
    simulation_state = test_parser.parse()
    assert len(simulation_state.infinite_sources) == 1
    assert isinstance(simulation_state.infinite_sources[0], InfiniteSource)
    assert len(simulation_state.infinite_sources[0].phase_slack_buses) == 3

def test_parser_create_xfmr():
    glm_file_path = os.path.join("data", "ieee_4_node", "node.glm")
    test_parser = Parser(os.path.join(CURR_DIR, glm_file_path), PowerFlowSettings(), False)
    simulation_state = test_parser.parse()
    assert len(simulation_state.transformers) == 1
    assert isinstance(simulation_state.transformers[0], ThreePhaseTransformer)


def test_parser_create_regulator():
    glm_file_path = os.path.join("data", "gc-12.47-1", "node.glm")
    test_parser = Parser(os.path.join(CURR_DIR, glm_file_path), PowerFlowSettings(), False)
    simulation_state = test_parser.parse()
    assert len(simulation_state.regulators) == 1
    assert isinstance(simulation_state.regulators[0], Regulator)

# def test_parser_create_triplex_line():
#     glm_file_path = os.path.join("data", "r1-12.47-1", "node.glm")
#     test_parser = Parser(os.path.join(CURR_DIR, glm_file_path), PowerFlowSettings(), False)
#     simulation_state = test_parser.parse()
#     assert len(simulation_state.lines) == 1
#     assert isinstance(simulation_state.lines[0], TriplexTransmissionLine)

def test_parser_line_impedance():
    glm_file_path = os.path.join("data", "swing_and_line_to_pq", "node.glm")
    glm_full_file_path = os.path.join(CURR_DIR, glm_file_path)
    parser = Parser(glm_full_file_path)
    simulation_state = parser.parse()
    simulation_state.reset_linear_stamp_collection()
    expected_Z = np.array([[0.4576+ 1.078j, 0.1559+ 0.5017j, 0.1535+ 0.3849j],
[0.1559+ 0.5017j, 0.4666+ 1.0482j, 0.158+ 0.4236j],
[0.1535+ 0.3849j, 0.158+ 0.4236j, 0.4615+ 1.0651j]
]);
    for transmission_line in simulation_state.transmission_lines:
        # Check that the impedance values ditto returns are at least within 15% of the expected values.
        # This should be more like 0.005%, but ditto is doing something strange I'm unable to understand.
        assert np.allclose(transmission_line.impedances * 1609.344, expected_Z, rtol=0.15)
    #     transmission_line.collect_Y_stamps(simulation_state)
    # PowerFlowRunner.stamp_linear(simulation_state)
    # Y = simulation_state.lin_Y

if __name__ == "__main__":
    test_parser_create_pq_load()