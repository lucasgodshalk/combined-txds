from lib.Solve import solve
from lib.settings import Settings
from parsers.parser import parse_raw
from scipy.io import loadmat
from lib.process_results import display_mat_comparison

# path to the grid network RAW file
#casename = 'testcases/GS-4_prior_solution.RAW'
#casename = 'testcases/IEEE-14_prior_solution.RAW'
#casename = 'testcases/IEEE-118_prior_solution.RAW'
#casename = 'testcases/ACTIVSg500_prior_solution_fixed.RAW'
#casename = 'testcases/PEGASE-9241_flat_start.RAW'
#casename = 'testcases/PEGASE-13659_flat_start.RAW'
casename = 'testcases/GS-4_stressed.RAW'
#casename = 'testcases/IEEE-14_stressed_1.RAW'
#casename = 'testcases/IEEE-14_stressed_2_fixed.RAW'

print(f'Testcase: {casename.replace("testcases/", "").replace(".RAW", "")}')

raw_data = parse_raw(casename)

settings = Settings(max_iters=100, flat_start=False, infeasibility_analysis=True, tx_stepping=False, V_limiting=False)

is_success, results = solve(raw_data, settings)

results.display(verbose=True)

if not is_success:
    print("SOLVER FAILED")
