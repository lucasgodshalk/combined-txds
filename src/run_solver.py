from logic.powerflowsettings import PowerFlowSettings
from logic.powerflow import PowerFlow

# path to the grid network RAW file
#casename = 'test/testcases/GS-4_prior_solution.RAW'
#casename = 'testcases/IEEE-14_prior_solution.RAW'
#casename = 'test/testcases/IEEE-118_prior_solution.RAW'
#casename = 'test/testcases/ACTIVSg500_prior_solution_fixed.RAW'
#casename = 'test/testcases/PEGASE-9241_flat_start.RAW'
#casename = 'testcases/PEGASE-13659_flat_start.RAW'
#casename = 'test/testcases/GS-4_stressed.RAW'
#casename = 'testcases/IEEE-14_stressed_1.RAW'
#casename = 'testcases/IEEE-14_stressed_2_fixed.RAW'
#casename = 'test/data/gc_12_47_1/node.glm'
casename = 'test/data/ieee_four_bus/node.glm'

print(f'Testcase: {casename.replace("testcases/", "")}')

settings = PowerFlowSettings(debug=False, max_iters=50, flat_start=False, infeasibility_analysis=False, tx_stepping=False, voltage_limiting=False)

powerflow = PowerFlow(casename, settings)

powerflow.execute()

#results.display(verbose=True)

#if not is_success:
#    print("SOLVER FAILED")
