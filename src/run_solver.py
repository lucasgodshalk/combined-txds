from logic.powerflowsettings import PowerFlowSettings
from logic.powerflow import PowerFlow

# path to the grid network RAW file
casename = 'test/data/positiveseq/GS-4_prior_solution.RAW'
#casename = 'test/data/positiveseq/IEEE-14_prior_solution.RAW'
#casename = 'test/data/positiveseq/IEEE-118_prior_solution.RAW'
#casename = 'test/data/positiveseq/ACTIVSg500_prior_solution_fixed.RAW'
#casename = 'test/data/positiveseq/PEGASE-9241_flat_start.RAW'
#casename = 'test/data/positiveseq/PEGASE-13659_flat_start.RAW'
#casename = 'test/data/positiveseq/GS-4_stressed.RAW'
#casename = 'test/data/positiveseq/IEEE-14_stressed_1.RAW'
#casename = 'test/data/positiveseq/IEEE-14_stressed_2_fixed.RAW'
#casename = 'test/data/gc_12_47_1/node.glm'
#casename = 'test/data/ieee_four_bus/node.glm'

print("Running power flow solver...")
print(f'Testcase: {casename}')

settings = PowerFlowSettings(debug=False, max_iters=50, flat_start=False, infeasibility_analysis=False, tx_stepping=False, voltage_limiting=False)

powerflow = PowerFlow(casename, settings)

results = powerflow.execute()

results.display(verbose=True)
