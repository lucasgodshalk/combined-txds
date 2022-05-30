from logic.PowerFlow import PowerFlow
from logic.PowerFlowSettings import PowerFlowSettings

# path to the grid network RAW file
#casename = 'testcases/GS-4_prior_solution.RAW'
#casename = 'testcases/IEEE-14_prior_solution.RAW'
#casename = 'testcases/IEEE-118_prior_solution.RAW'
#casename = 'testcases/ACTIVSg500_prior_solution_fixed.RAW'
#casename = 'testcases/PEGASE-9241_flat_start.RAW'
#casename = 'testcases/PEGASE-13659_flat_start.RAW'
casename = 'test/testcases/GS-4_stressed.RAW'
#casename = 'testcases/IEEE-14_stressed_1.RAW'
#casename = 'testcases/IEEE-14_stressed_2_fixed.RAW'

print(f'Testcase: {casename.replace("testcases/", "")}')

settings = PowerFlowSettings(max_iters=100, flat_start=False, infeasibility_analysis=True, tx_stepping=False, V_limiting=False)

powerflow = PowerFlow(casename, settings)

powerflow.execute()

#results.display(verbose=True)

#if not is_success:
#    print("SOLVER FAILED")
