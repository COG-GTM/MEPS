# MEPS Python Implementation

This directory contains Python implementations of the MEPS workshop exercises.

## Requirements

- Python 3.6+
- pandas
- numpy
- statsmodels
- pyreadstat (for reading SAS data files)

## Installation

```bash
pip install pandas numpy statsmodels pyreadstat
```

## Usage

Each exercise is contained in its own directory. To run an exercise, navigate to the directory and run the Python script:

```bash
cd workshop_exercises/exercise_1c
python Exercise1c.py
```

## Comparing with SAS Output

To compare the Python output with the SAS output, run the comparison script:

```bash
python compare_outputs.py
```

This will extract key statistics from both outputs and compare them to ensure the Python implementation produces similar results to the SAS implementation.
