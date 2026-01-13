# MEPS Python Examples

This directory contains Python equivalents of the SAS example code for analyzing Medical Expenditure Panel Survey (MEPS) data. All 52 SAS files have been converted to Python with proper survey analysis handling.

## Directory Structure

```
Python/
├── meps_utils.py                    # Shared utility module for survey analysis
├── workshop_exercises/              # 18 workshop exercise examples
├── summary_tables_examples/         # 13 summary table examples
└── older_exercises_1996_to_2006/    # 27 older exercise examples
    ├── Estimation_examples/         # E1-E8: Estimation examples
    ├── Employment_examples/         # EM1-EM2: Employment analysis
    ├── Linking_examples/            # L1-L5, L1A: File linking examples
    └── Misc_examples/               # M1-M11: Miscellaneous examples
```

## Dependencies

Install the required packages:

```bash
pip install pandas numpy scipy statsmodels pyreadstat
```

## Key Features

### Survey Design Handling

The `meps_utils.py` module provides proper complex survey design handling with:

- **Stratification** (VARSTR): Groups similar sampling units together
- **Clustering** (VARPSU): Primary sampling units within strata
- **Weighting** (PERWT##F): Survey weights for national estimates
- **Taylor Series Linearization**: Proper variance estimation for complex surveys

### Core Functions

```python
from meps_utils import (
    load_sas_data,      # Load SAS7BDAT or SSP files
    SurveyDesign,       # Define survey design
    survey_mean,        # Weighted means with proper SEs
    survey_total,       # Weighted totals with proper SEs
    survey_freq,        # Weighted frequencies
    survey_by,          # Domain/subpopulation analysis
    survey_glm,         # Survey-weighted regression
    pool_data,          # Pool multiple years of data
    create_age_groups   # Create age categories
)
```

### Example Usage

```python
from pathlib import Path
from meps_utils import load_sas_data, SurveyDesign, survey_mean

# Load data
data_dir = Path("C:/MEPS/DATA")
fyc = load_sas_data(data_dir / "h224.sas7bdat")

# Define survey design
design = SurveyDesign(
    data=fyc,
    strata='VARSTR',
    cluster='VARPSU',
    weight='PERWT21F'
)

# Calculate mean total expenditure
result = survey_mean(design, 'TOTEXP21')
print(f"Mean: ${result['mean'].values[0]:,.2f}")
print(f"SE: ${result['se'].values[0]:.2f}")
```

## Data Sources

MEPS data files can be downloaded from:
https://meps.ahrq.gov/mepsweb/data_stats/download_data_files.jsp

## File Naming Convention

- Workshop exercises: Named by topic (e.g., `exercise1.py`, `cond_pmed_2020.py`)
- Summary tables: Named by analysis type and year (e.g., `care_access_2019.py`)
- Older exercises: Named by category code (e.g., `E1.py`, `L3.py`, `M5.py`)

## Important Notes

1. **Always use weights**: MEPS oversamples certain populations. Using weights produces nationally representative estimates.

2. **Always use survey design variables**: The VARSTR and VARPSU variables account for the complex survey design and produce correct standard errors.

3. **Data file paths**: Update the `data_dir` variable in each script to point to your local MEPS data directory.

4. **Variable naming**: MEPS variable names include year suffixes (e.g., `TOTEXP21` for 2021, `PERWT18F` for 2018 weights).

## Conversion from SAS

The Python scripts maintain functional equivalence with the original SAS code:

| SAS Procedure | Python Equivalent |
|---------------|-------------------|
| `PROC SURVEYMEANS` | `survey_mean()`, `survey_total()` |
| `PROC SURVEYFREQ` | `survey_freq()` |
| `PROC SURVEYREG` | `survey_glm()` |
| `PROC SORT + PROC MEANS` | `pandas.groupby().agg()` |
| `DATA step` | `pandas` operations |
| `DOMAIN` statement | `domain` parameter or subset filtering |

## References

- [MEPS Homepage](https://meps.ahrq.gov/)
- [MEPS GitHub Repository](https://github.com/HHS-AHRQ/MEPS)
- [Survey Analysis in Python](https://www.statsmodels.org/stable/stats.html)
