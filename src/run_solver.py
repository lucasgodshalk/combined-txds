from logic.networkpostprocessor import NetworkPostProcessor
from logic.powerflowsettings import PowerFlowSettings
from logic.powerflow import FilePowerFlow
import argparse

from logic.postprocessingsettings import PostProcessingSettings

parser = argparse.ArgumentParser()

parser.add_argument("case")
parser.add_argument("--loadfile", required=False)
parser.add_argument("--loadstart", required=False)
parser.add_argument("--loadend", required=False)
parser.add_argument("--negativeload", required=False)
parser.add_argument("--artificialswingbus", required=False)
parser.add_argument("--outputfile", required=False)
parser.add_argument("--debug", required=False, action='store_true')
parser.add_argument("--verbose", required=False, action='store_true')
args = parser.parse_args()

case = args.case
loadfile = args.loadfile
loadstart = args.loadstart
loadend = args.loadend
negativeload = args.negativeload
artificialswingbus = args.artificialswingbus
outputfile = args.outputfile
debug = args.debug
verbose = args.verbose

print("Running power flow solver...")

settings = PowerFlowSettings(
    debug=debug, 
    max_iters=50, 
    flat_start=False, 
    infeasibility_analysis=False, 
    tx_stepping=False, 
    voltage_limiting=False,
    dump_matrix=False
    )

powerflow = FilePowerFlow(case, settings)

powerflow.network.display()

results = powerflow.execute()

results.display(verbose=verbose)
results.output(outputfile)

try:
    postprocessingsettings = PostProcessingSettings(
        loadfile_name = loadfile,
        loadfile_start = loadstart,
        loadfile_end = loadend,
        artificialswingbus = artificialswingbus,
        negativeload = negativeload
    )
    postprocessor = NetworkPostProcessor(postprocessingsettings, powerflow)
    results = postprocessor.execute()

    if results is not None:
        results.display(verbose=False)
        results.output(outputfile)
except Exception as e:
    print(e)
    pass