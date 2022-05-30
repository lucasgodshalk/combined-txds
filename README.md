# anoeds
Analyze Network Operations of Electrical Distribution Systems

## Get Started

To get started with ANOEDS, you may install the code as a local Python package. This can be done by navigating to the root directory in your terminal (or WSL terminal on Windows), and running the following command:

`python3 -m pip install -e .`

This will install the ANOEDS package, as well as its dependencies, in your Python environment.

To run the entire suite of tests, you can run the following command from the same location:

`pytest`

To run a single test, you can run the following command:

`pytest anoeds/test/<file>::<test name>`

e.g.

`pytest anoeds/test/test_powerflowrunner.py::test_powerflowrunner_ieee_four_bus`
