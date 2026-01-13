"""
AHRQ MEPS Data Users Workshop - Misc Example M6

This example shows the use of the Diabetes Care Supplement (DCS) weight
variable (DIABW05F) for generating estimates for analyses using questions
from the DCS.

Two DCS variables are used:
(1) DSA1C53 - Number of times tested for Hemoglobin A1C
(2) DSINSU53 - Diabetes treated with insulin injections?

Input file: h97.sas7bdat (2005 Full-Year Data File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Misc_examples/M6/M6.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_freq


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS/DATA")
    
    print("=" * 80)
    print("AHRQ MEPS DATA USERS WORKSHOP")
    print("DIABETES CARE SUPPLEMENT ESTIMATES")
    print("=" * 80)
    
    # Labels
    a1c_labels = {
        -9: 'Not Ascertained',
        -8: 'DK',
        -1: 'Inapplicable'
    }
    
    insulin_labels = {
        -9: 'Not Ascertained',
        -8: 'DK',
        -1: 'Inapplicable',
        1: 'Yes',
        0: 'No'
    }
    
    # Load FYC file
    fyc_file = data_dir / "h97.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    fy2005 = load_sas_data(fyc_file, columns=[
        'DUPERSID', 'DIABW05F', 'VARSTR', 'VARPSU', 'DSA1C53', 'DSINSU53'
    ])
    
    print(f"Total records: {len(fy2005):,}")
    
    # Subset to persons with positive DCS weight
    dcs_pop = fy2005[fy2005['DIABW05F'] > 0].copy()
    print(f"Persons with positive DCS weight: {len(dcs_pop):,}")
    
    # Create survey design with DCS weight
    design = SurveyDesign(
        data=dcs_pop,
        strata='VARSTR',
        cluster='VARPSU',
        weight='DIABW05F'
    )
    
    # DSA1C53 - Number of times tested for Hemoglobin A1C
    print("\n" + "=" * 80)
    print("DSA1C53: NUMBER OF TIMES TESTED FOR HEMOGLOBIN A1C")
    print("=" * 80)
    
    # Create bins for A1C tests
    def bin_a1c(x):
        if x < 0:
            if x == -9:
                return 'Not Ascertained'
            elif x == -8:
                return 'DK'
            else:
                return 'Inapplicable'
        elif x <= 20:
            return '1-20 times'
        elif x <= 50:
            return '21-50 times'
        else:
            return '51+ times'
    
    dcs_pop['A1C_BIN'] = dcs_pop['DSA1C53'].apply(bin_a1c)
    
    print("\nDistribution of A1C tests:")
    total_wt = dcs_pop['DIABW05F'].sum()
    
    for bin_val in ['Inapplicable', 'Not Ascertained', 'DK', '1-20 times', '21-50 times', '51+ times']:
        subset = dcs_pop[dcs_pop['A1C_BIN'] == bin_val]
        if len(subset) > 0:
            wt = subset['DIABW05F'].sum()
            pct = wt / total_wt * 100
            print(f"  {bin_val}: {len(subset):,} ({pct:.1f}%)")
    
    # DSINSU53 - Diabetes treated with insulin injections
    print("\n" + "=" * 80)
    print("DSINSU53: DIABETES TREATED WITH INSULIN INJECTIONS")
    print("=" * 80)
    
    # Recode for display
    dcs_pop['INSULIN_LABEL'] = dcs_pop['DSINSU53'].map(insulin_labels)
    
    print("\nDistribution of insulin treatment:")
    for val, label in insulin_labels.items():
        subset = dcs_pop[dcs_pop['DSINSU53'] == val]
        if len(subset) > 0:
            wt = subset['DIABW05F'].sum()
            pct = wt / total_wt * 100
            print(f"  {label}: {len(subset):,} ({pct:.1f}%)")
    
    # Among those with valid responses
    print("\n" + "-" * 60)
    print("AMONG THOSE WITH VALID RESPONSES")
    print("-" * 60)
    
    valid_insulin = dcs_pop[dcs_pop['DSINSU53'].isin([0, 1])]
    valid_total = valid_insulin['DIABW05F'].sum()
    
    for val, label in [(1, 'Yes'), (0, 'No')]:
        subset = valid_insulin[valid_insulin['DSINSU53'] == val]
        if len(subset) > 0:
            wt = subset['DIABW05F'].sum()
            pct = wt / valid_total * 100
            print(f"  {label}: {wt:,.0f} ({pct:.1f}%)")
    
    print("\n" + "=" * 80)
    print("KEY TAKEAWAY")
    print("=" * 80)
    print("""
The Diabetes Care Supplement (DCS) weight variable (DIABW05F) should be
used when analyzing DCS questions. This weight:

1. Is specific to the DCS population (persons with diabetes)
2. Accounts for the DCS sampling design
3. Produces nationally representative estimates for the diabetic population

Using the standard person weight (PERWT05F) instead of DIABW05F would
produce incorrect estimates for DCS analyses.
""")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
