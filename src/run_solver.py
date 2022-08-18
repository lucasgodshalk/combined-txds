from logic.powerflowsettings import PowerFlowSettings
from logic.powerflow import FilePowerFlow

# path to the grid network RAW file
#casename = 'test/data/positiveseq/GS-4_prior_solution.RAW'
#casename = 'test/data/positiveseq/IEEE-14_prior_solution.RAW'
#casename = 'test/data/positiveseq/IEEE-118_prior_solution.RAW'
#casename = 'test/data/positiveseq/ACTIVSg500_prior_solution_fixed.RAW'
#casename = 'test/data/positiveseq/PEGASE-9241_flat_start.RAW'
#casename = 'test/data/positiveseq/PEGASE-13659_flat_start.RAW'
#casename = 'test/data/positiveseq/GS-4_stressed.RAW'
#casename = 'test/data/positiveseq/IEEE-14_stressed_1.RAW'
#casename = 'test/data/positiveseq/IEEE-14_stressed_2_fixed.RAW'
# casename = 'test/data/Taxonomy_Feeders/GC-12.47-1.glm'
# casename = 'test/data/three_phase/ieee_four_bus/node.glm'
# casename = 'test/data/Taxonomy_Feeders/R1-12.47-3.glm'
# casename = 'test/data/three_phase/center_tap_xfmr_and_single_line_to_load/node.glm'
casename = 'test/data/Taxonomy_Feeders/R1-12.47-2.glm'

print("Running power flow solver...")
print(f'Testcase: {casename}')

settings = PowerFlowSettings(
    debug=True, 
    max_iters=50, 
    flat_start=False, 
    infeasibility_analysis=False, 
    tx_stepping=False, 
    voltage_limiting=False,
    dump_matrix=True
    )

powerflow = FilePowerFlow(casename, settings)

results = powerflow.execute()

results.display(verbose=True)
