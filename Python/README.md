# Analyzing MEPS data using Python

- [Loading MEPS data](#loading-meps-data)
- [Python packages for survey analysis](#python-packages-for-survey-analysis)
- [Python examples](#python-examples)
  - [Workshop exercises](#workshop-exercises)

# Loading MEPS data

For data years 2017 and later (and also for the 2016 Medical Conditions file), .zip files for multiple file formats are available, including ASCII (.dat), SAS V9 (.sas7bdat), Stata (.dta), and Excel (.xlsx). Prior to 2017, ASCII (.dat) and SAS transport (.ssp) files are provided for all datasets.

The recommended file formats for Python are the Stata (.dta) or Excel (.xlsx) formats for data years 2017 and later.

## Data years 2017 and later: Stata or Excel files

```python
import pandas as pd

# Using Stata format
data = pd.read_stata("C:/MEPS/h206b.dta")

# Using Excel format
data = pd.read_excel("C:/MEPS/h206b.xlsx")

# View first 10 rows of data
print(data.head(10))
```

## Data years 1996-2016: SAS XPORT format

For data years prior to 2017, you can use the `pyreadstat` package to read SAS transport files:

```python
import pyreadstat

# Read SAS transport file
data, meta = pyreadstat.read_xport("C:/MEPS/h188b.ssp")

# View first 10 rows of data
print(data.head(10))
```

# Python packages for survey analysis

To analyze MEPS data using Python, you need to account for the complex survey design. There are several options for handling survey data in Python:

## Option 1: Using `statsmodels`

The `statsmodels` package provides functionality for analyzing survey data:

```python
import pandas as pd
import statsmodels.api as sm

# Load data
data = pd.read_stata("C:/MEPS/h206b.dta")

# For newer versions of statsmodels, import the survey module directly
from statsmodels.survey import design

# Define survey design
design = design.SurveyDesign(
    strata=data['VARSTR'],
    weights=data['PERWT18F'],
    cluster=data['VARPSU'],
    nest=True
)

# Calculate statistics
result = design.mean('DVXP18X')
print(result)
```

## Option 2: Using `pysurvey`

The `pysurvey` package is specifically designed for complex survey analysis:

```python
import pandas as pd
import pysurvey as ps

# Load data
data = pd.read_stata("C:/MEPS/h206b.dta")

# Define survey design
design = ps.SurveyDesign(
    data=data,
    strata='VARSTR',
    weights='PERWT18F',
    cluster='VARPSU',
    nest=True
)

# Calculate statistics
result = design.mean('DVXP18X')
print(result)
```

## Important considerations for survey analysis

When analyzing MEPS data using Python, the following steps are recommended to ensure unbiased estimates and proper standard errors:

1. Always use survey analysis packages that account for the complex survey design
2. Always include the cluster (e.g., VARPSU), strata (e.g., VARSTR), and appropriate weights (e.g., PERWT18F)
3. Use domain analysis for subpopulations rather than subsetting the data
4. Handle non-positive weights appropriately

# Python examples

## Workshop exercises

Example codes converted from SAS to Python are provided in the [workshop_exercises](workshop_exercises) folder:

### 1. National health care expenses
[exercise_1c](workshop_exercises/exercise_1c): National health care expenses by age group, 2018
- Demonstrates how to calculate national health care expenses statistics using Python
- Includes code for calculating percentages, means, and medians by age group
- Provides a comparison script to verify the Python output against the SAS output
