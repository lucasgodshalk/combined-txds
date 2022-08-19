from logic.powerflowsettings import PowerFlowSettings
from logic.powerflow import FilePowerFlow
import argparse

from logic.postprocessingsettings import PostProcessingSettings

parser = argparse.ArgumentParser()

parser.add_argument("case")
parser.add_argument("--loadfile", required=False)
parser.add_argument("--loadstart", required=False)
parser.add_argument("--loadend", required=False)
args = parser.parse_args()

case = args.case
loadfile = args.loadfile
loadstart = args.loadstart
loadend = args.loadend

print("Running power flow solver...")
print(f'Testcase: {case}')

settings = PowerFlowSettings(
    debug=True, 
    max_iters=50, 
    flat_start=False, 
    infeasibility_analysis=False, 
    tx_stepping=False, 
    voltage_limiting=False,
    dump_matrix=False
    )

powerflow = FilePowerFlow(case, settings)

results = powerflow.execute()

results.display(verbose=True)
results.output()

if loadfile is not None:
    postprocessingsettings = PostProcessingSettings(
        loadfile_name = loadfile,
        loadfile_start = loadstart,
        loadfile_end = loadend
    )
    results = powerflow.execute_quasi_time_series(postprocessingsettings)

    results.display(verbose=False)
    results.output()