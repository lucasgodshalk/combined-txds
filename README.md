# Combined Transmisison & Distribution Analysis
Perform steady state power flow analysis of electrical transmission & distribution systems.

## Get Started

Assuming you are on the command line in the root of the repository, first install all of the python modules as listed in `requirements.txt`:

```
python -m pip install -r ./requirements.txt
```

This library can be executed with arguments to target a particular network case (either three-phase or positive sequence):

```
python src/run_solver.py test/data/positive_seq/GS-4_prior_solution.RAW
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