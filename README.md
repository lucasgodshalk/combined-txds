# Positive Sequence Transmisison or Three-Phase Distribution Power Flow Analysis
Perform steady state power flow analysis of electrical transmission & distribution systems.

Project documentation can be found [here](https://github.com/lucasgodshalk/combined-txds/wiki).

## Get Started

Assuming you are on the command line in the root of the repository, first install all of the python modules as listed in `requirements.txt`:

```
python -m pip install -r ./requirements.txt
```

This library can be executed with arguments to target a particular network case (either three-phase or positive sequence):

Note! This may take a while to execute the first time as everything gets derived/compiled. Subsequent executions should be much faster.

```
For three-phase distribution cases, run:
python src/run_solver.py $PATH-TO-GLM-FILE$
For transmission cases, run:
python src/run_solver.py $PATH-TO-RAW-FILE$
```

In order to save network simulation results (in the same folder) in output_voltage.csv and output_power.csv use:
```
--outputfile ./output  
```

In order to run tests:
```
export PYTHONPATH="./src:./test"

python -m pytest test/test_positiveseq.py
```

If you are using VS Code with the Python extension and want to run unit tests, you can add a `.env` file to the root of the repository with:

```
PYTHONPATH="./src:./test"
```

The codebase is based on the following papers:
```
1. Pandey, A., Jereminov, M., Wagner, M. R., Bromberg, D. M., Hug, G., & Pileggi, L. (2018). Robust power flow and three-phase power flow analyses. IEEE Transactions on Power Systems, 34(1), 616-626.
2. Jereminov, M., Bromberg, D. M., Pandey, A., Wagner, M. R., & Pileggi, L. (2020). Evaluating feasibility within power flow. IEEE Transactions on Smart Grid, 11(4), 3522-3534.
3. Foster, E., Pandey, A., & Pileggi, L. (2022). Three-phase infeasibility analysis for distribution grid studies. Electric Power Systems Research, 212, 108486.
```

In addition, three phase component modeling references Distribution System Modeling and Analysis 3rd ed by W. Kersting.
