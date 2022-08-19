from logic.powerflowsettings import PowerFlowSettings
from logic.powerflow import FilePowerFlow
import argparse

parser = argparse.ArgumentParser()

parser.add_argument("case")
parser.add_argument("loadfile")
parser.add_argument("loadstart")
args = parser.parse_args()

case = args.case
loadfile = args.loadfile
loadstart = args.loadstart

print("Running power flow solver...")
print(f'Testcase: {case}')

settings = PowerFlowSettings(
    debug=True, 
    max_iters=50, 
    flat_start=False, 
    infeasibility_analysis=False, 
    tx_stepping=False, 
    voltage_limiting=False,
    dump_matrix=False,
    loadfile_name = loadfile,
    loadfile_start = loadstart
    )

powerflow = FilePowerFlow(case, settings)

results = powerflow.execute()

results.display(verbose=True)
