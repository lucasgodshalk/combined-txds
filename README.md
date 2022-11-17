# Positive Sequence Transmisison or Three-Phase Distribution Power Flow Analysis
Perform steady state power flow analysis of electrical transmission & distribution systems.

Project documentation with both a user guide and developer information can be found [here](https://github.com/lucasgodshalk/combined-txds/wiki).

## Quick Start

Assuming you cloned the repository and you are in the root of the repository, first install all of the python modules as listed in `requirements.txt`:

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