import unittest
from lib.MatrixBuilder import MatrixBuilder
from lib.Solve import solve
from lib.process_results import assert_mat_comparison
from lib.settings import Settings
from models.Branches import Branches
from models.Buses import Bus
from models.Generators import Generators
from models.Loads import Loads
from models.Shunts import Shunts
from models.Slack import Slack
from models.Transformers import Transformers
from parsers.parser import parse_raw
from scipy.io import loadmat

class PowerFlowTests(unittest.TestCase):
    def test_GS_4_prior_solution(self):
        casename = 'testcases/GS-4_prior_solution.RAW'
        raw_data = parse_raw(casename)
        is_success, results = solve(raw_data)
        self.assertTrue(is_success)

        mat_result = loadmat("testcases/output-GS-4.mat")

        assert_mat_comparison(mat_result, results)

    def test_IEEE_14_prior_solution(self):
        casename = 'testcases/IEEE-14_prior_solution.RAW'
        raw_data = parse_raw(casename)
        is_success, results = solve(raw_data)
        self.assertTrue(is_success)

        mat_result = loadmat("testcases/output-IEEE-14.mat")

        assert_mat_comparison(mat_result, results)