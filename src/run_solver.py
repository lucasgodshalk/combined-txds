from logic.networkpostprocessor import NetworkPostProcessor
from logic.powerflowsettings import PowerFlowSettings
from logic.powerflow import PowerFlow
from logic.networkloader import NetworkLoader
import argparse

from logic.postprocessingsettings import PostProcessingSettings

from colorama import init
from termcolor import colored
# use Colorama to make Termcolor work on Windows too
init()


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
parser.add_argument("--infeas", required=False, default='False')
parser.add_argument("--load_factor", required=False, default=-1)
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
infeas = args.infeas
load_factor = float(args.load_factor)
print(colored("Running power flow solver...",'red'))
print(colored("Infeasibility option is %s" % infeas, 'green'))

settings = PowerFlowSettings(
    debug=debug, 
    max_iters=50, 
    flat_start=False, 
    infeasibility_analysis=infeas, 
    tx_stepping=False, 
    voltage_limiting=False,
    dump_matrix=False,
    load_factor=load_factor
    )

network = NetworkLoader(settings).from_file(case)

network.display()

powerflow = PowerFlow(network, settings)

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
