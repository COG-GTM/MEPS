# MEPS Python Examples

This directory contains Python examples for analyzing Medical Expenditure Panel Survey (MEPS) data, converted from the original SAS code.

## Requirements

Install the required Python packages:

```bash
pip install pandas numpy pyreadstat statsmodels scipy
```

## Directory Structure

The Python examples mirror the SAS directory structure:

- `workshop_exercises/` - Workshop exercises demonstrating various MEPS analysis techniques
- `summary_tables_examples/` - Examples for replicating MEPS-HC Data Tools summary tables
- `older_exercises_1996_to_2006/` - Historical examples using older MEPS data files

## Utility Module

The `meps_utils.py` module provides core functionality for MEPS analysis:

### Data Loading

```python
from meps_utils import load_sas_data

# Load SAS7BDAT file (2017+)
df = load_sas_data('path/to/file.sas7bdat')

# Load SSP/XPT file (1996-2016)
df = load_sas_data('path/to/file.ssp')
```

### Survey Design

```python
from meps_utils import SurveyDesign

# Create survey design object (equivalent to SAS PROC SURVEY statements)
design = SurveyDesign(
    data=df,
    strata='VARSTR',    # Stratification variable
    cluster='VARPSU',   # Cluster/PSU variable
    weight='PERWT21F'   # Weight variable
)
```

### Survey Statistics

```python
from meps_utils import survey_mean, survey_total, survey_freq, survey_reg

# Calculate survey-weighted mean (equivalent to PROC SURVEYMEANS)
result = survey_mean(design, 'TOTEXP21')
print(f"Mean: {result['mean']:.2f}, SE: {result['se']:.4f}")

# Calculate survey-weighted total
result = survey_total(design, 'TOTEXP21')
print(f"Total: {result['total']:,.0f}")

# Calculate survey-weighted frequencies (equivalent to PROC SURVEYFREQ)
freq_table = survey_freq(design, 'INSCOV21')

# Fit survey-weighted regression (equivalent to PROC SURVEYREG)
reg_result = survey_reg(design, 'TOTEXP21', ['AGE', 'SEX'])
```

## Key Survey Design Variables

MEPS uses a complex survey design with stratification and clustering:

- `VARSTR` - Variance stratum (stratification variable)
- `VARPSU` - Variance PSU (primary sampling unit/cluster variable)
- `PERWT##F` - Person-level weight (e.g., `PERWT21F` for 2021)

Always use these variables when calculating population estimates to account for the survey design.

## Example Usage

### Basic Analysis

```python
import pandas as pd
from meps_utils import load_sas_data, SurveyDesign, survey_mean

# Load 2021 full-year consolidated file
fyc = load_sas_data('data/h233.sas7bdat')

# Filter to persons with positive weight
fyc = fyc[fyc['PERWT21F'] > 0]

# Create survey design
design = SurveyDesign(fyc, strata='VARSTR', cluster='VARPSU', weight='PERWT21F')

# Calculate mean total expenditure
result = survey_mean(design, 'TOTEXP21')
print(f"Mean Total Expenditure: ${result['mean']:,.2f}")
print(f"Standard Error: ${result['se']:,.2f}")
```

### Domain Analysis (Subpopulation Estimates)

```python
# Analyze expenditures for specific age groups
for age_group in ['0-17', '18-64', '65+']:
    subset = fyc[fyc['AGECAT'] == age_group]
    design_sub = SurveyDesign(subset, strata='VARSTR', cluster='VARPSU', weight='PERWT21F')
    result = survey_mean(design_sub, 'TOTEXP21')
    print(f"{age_group}: ${result['mean']:,.2f}")
```

### Condition-Event Linking

```python
# Load conditions and events files
cond = load_sas_data('data/h231.sas7bdat')
clnk = load_sas_data('data/h229if1.sas7bdat')
rx = load_sas_data('data/h229a.sas7bdat')

# Filter to specific condition (e.g., diabetes)
diabetes = cond[cond['CCSR1X'].str.startswith('END002', na=False)]

# Link conditions to events via CLNK file
cond_events = diabetes.merge(clnk, on='CONDIDX')
cond_rx = cond_events.merge(rx, left_on='EVNTIDX', right_on='LINKIDX')
```

## Workshop Exercises

The `workshop_exercises/` directory contains examples covering:

- Exercise 1: Loading MEPS data files
- Exercise 2: Analyzing healthcare expenditures
- Exercise 3: Prescribed medicine analysis
- Exercise 4: Pooling multiple years of data
- Exercise 5: Condition-event linking
- Exercise 6: Regression analysis

## Summary Tables Examples

The `summary_tables_examples/` directory contains examples for replicating statistics from the MEPS-HC Data Tools:

- Healthcare utilization and expenditures
- Insurance coverage
- Access to care
- Quality of care
- Prescribed medicines by drug name and therapeutic class
- Medical conditions and expenditures

## Older Exercises (1996-2006)

The `older_exercises_1996_to_2006/` directory contains historical examples:

- `Employment_examples/` - Employment and health status analyses
- `Estimation_examples/` - Basic estimation, pooling, longitudinal analysis
- `Linking_examples/` - File linking and merging techniques
- `Misc_examples/` - Various analytical techniques

## Data Files

MEPS public use files can be downloaded from:
https://meps.ahrq.gov/mepsweb/data_stats/download_data_files.jsp

Place downloaded files in a `data/` directory relative to the Python scripts.

## Notes

- All examples use proper complex survey design handling to produce unbiased national estimates
- Standard errors are calculated using Taylor series linearization
- Domain analysis preserves the full sample for correct variance estimation
- Weight variables should always be used for population estimates
