import sys
from logic.network.loadfactor import modify_load_factor
from logic.network.timeseriesprocessor import TimeSeriesProcessor
from logic.powerflowsettings import PowerFlowSettings
from logic.powerflow import PowerFlow
from logic.network.networkloader import NetworkLoader
import argparse
from logic.network.timeseriessettings import TimeSeriesSettings
from models.optimization.L2infeasibility import load_infeasibility_analysis

from colorama import init
from termcolor import colored
# use Colorama to make Termcolor work on Windows too
init()

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("case")
    parser.add_argument("--loadfile", required=False)
    parser.add_argument("--loadstart", required=False)
    parser.add_argument("--loadend", required=False)
    parser.add_argument("--negativeloads", required=False, nargs='+')
    parser.add_argument("--artificialswingbus", required=False, default = None)
    parser.add_argument("--outputfile", required=False)
    parser.add_argument("--debug", required=False, action='store_true')
    parser.add_argument("--verbose", required=False, action='store_true')
    parser.add_argument("--infeasibility", required=False, default=False, action='store_true')
    parser.add_argument("--load_factor", required=False, default=-1)
    parser.add_argument("--tx_stepping", required=False, default=False, action='store_true')
    parser.add_argument("--select_island", required=False, default=False)
    args = parser.parse_args()

    case = args.case
    loadfile = args.loadfile
    loadstart = args.loadstart
    loadend = args.loadend
    negativeloads = args.negativeloads
    artificialswingbus = args.artificialswingbus
    outputfile = args.outputfile
    debug = args.debug
    verbose = args.verbose
    infeasibility = args.infeasibility
    tx_stepping = args.tx_stepping
    load_factor = float(args.load_factor)
    select_island = args.select_island
    print(colored("Starting power flow solver...",'green'))
    print(colored(f"Can run power deficient networks: {infeasibility}", 'green'))

    settings = PowerFlowSettings(
        debug=debug, 
        max_iters=50, 
        flat_start=False, 
        tx_stepping=tx_stepping, 
        voltage_limiting=False,
        dump_matrix=False,
        load_factor=load_factor
        )

    network = NetworkLoader(settings).from_file(case)

    if infeasibility:
        network.optimization = load_infeasibility_analysis(network)

    modify_load_factor(network, load_factor, load_factor)

    network.display()

    powerflow = PowerFlow(network, settings)

    try:
        postprocessingsettings = TimeSeriesSettings(
            loadfile_name = loadfile,
            loadfile_start = loadstart,
            loadfile_end = loadend,
            artificialswingbus = artificialswingbus,
            negativeloads = negativeloads,
            select_island = select_island,
            outputfile = outputfile,
        )
        postprocessor = TimeSeriesProcessor(postprocessingsettings, powerflow)
        results = postprocessor.execute()

        if results is not None:
            results.display(verbose=False)
            # results.output(outputfile)
            return
    except Exception as e:
        print(e)
        pass


    results = powerflow.execute()

    results.display(verbose=verbose)
    results.output(outputfile)

if __name__ == "__main__":
    main()