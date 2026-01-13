"""
Exercise 5a: Calculate Family-Level Estimates

This program illustrates how to construct family-level variables from
person-level data.

There are two definitions of family unit in MEPS:
    1) CPS Family: ID is DUID + CPSFAMID. Corresponding weight is FAMWT##C.
    2) MEPS Family: ID is DUID + FAMIDYR. Corresponding weight is FAMWT##F.

The CPS Family is used in this exercise.

Input files:
    - 2015 Full-Year file (h181)

Python equivalent of: SAS/workshop_exercises/exercise_5a/Exercise5a.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_mean


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS")
    
    print("=" * 80)
    print("2018 AHRQ MEPS DATA USERS WORKSHOP")
    print("EXERCISE 5a: CALCULATE FAMILY-LEVEL ESTIMATES")
    print("=" * 80)
    
    # Load 2015 Full-Year file
    fyc_file = data_dir / "h181.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    fyc = load_sas_data(fyc_file)
    
    # Sample dump for family IDs
    print("\n" + "-" * 60)
    print("SAMPLE DUMP FOR FAMILY IDS")
    print("-" * 60)
    
    sample_cols = ['PID', 'AGE15X', 'SEX', 'CPSFAMID', 'FAMWT15C', 'FAMIDYR', 'FAMWT15F']
    available_cols = [c for c in sample_cols if c in fyc.columns]
    print(fyc[['DUID'] + available_cols].head(20).to_string())
    
    # Keep needed variables
    pers = fyc[['DUPERSID', 'DUID', 'CPSFAMID', 'FAMWT15C', 'VARSTR', 'VARPSU', 'TOTSLF15', 'TTLP15X']].copy()
    
    # Sort by DUID and CPSFAMID
    pers = pers.sort_values(['DUID', 'CPSFAMID'])
    
    # Create family-level variables by aggregating person-level data
    fam = pers.groupby(['DUID', 'CPSFAMID']).agg(
        FAMSIZE=('DUPERSID', 'count'),
        FAMOOP=('TOTSLF15', 'sum'),
        FAMINC=('TTLP15X', 'sum')
    ).reset_index()
    
    # Add labels
    print("\n" + "-" * 60)
    print("FAMILY-LEVEL VARIABLES CREATED")
    print("-" * 60)
    print(f"  FAMSIZE = # of persons per CPS family")
    print(f"  FAMOOP = Total out-of-pocket exp (TOTSLF15) per CPS family")
    print(f"  FAMINC = Total income (TTLP15X) per CPS family")
    
    # Sample dump to check creation of family-level variables
    print("\n" + "-" * 60)
    print("SAMPLE DUMP TO CHECK FAMILY-LEVEL VARIABLES")
    print("-" * 60)
    
    # Merge back to person level to show
    pers2 = pers.merge(fam, on=['DUID', 'CPSFAMID'], how='left')
    print(pers2.head(20).to_string())
    
    # Add weight, VARSTR, and VARPSU to family-level analytic data
    # Get unique family weights (one per family)
    famwt = pers[pers['FAMWT15C'] > 0][['DUID', 'CPSFAMID', 'FAMWT15C', 'VARSTR', 'VARPSU']].drop_duplicates(
        subset=['DUID', 'CPSFAMID']
    )
    
    # Merge family data with weights
    fam2 = fam.merge(famwt, on=['DUID', 'CPSFAMID'], how='inner')
    
    print(f"\nNumber of CPS families with positive weight: {len(fam2):,}")
    
    # Calculate family-level estimates
    print("\n" + "=" * 60)
    print("CPS FAMILY-LEVEL ESTIMATES ON FAMILY SIZE,")
    print("OUT-OF-POCKET EXP, AND INCOME, 2015")
    print("=" * 60)
    
    design = SurveyDesign(
        data=fam2,
        strata='VARSTR',
        cluster='VARPSU',
        weight='FAMWT15C'
    )
    
    variables = ['FAMSIZE', 'FAMOOP', 'FAMINC']
    labels = [
        '# of Persons per CPS Family',
        'Total Out-of-Pocket Exp per CPS Family',
        'Total Income per CPS Family'
    ]
    
    print(f"\nN (unweighted families): {len(fam2):,}")
    print(f"Sum of Weights: {fam2['FAMWT15C'].sum():,.0f}")
    
    for var, label in zip(variables, labels):
        mean_result = survey_mean(design, var)
        print(f"\n{label}:")
        print(f"  Mean: {mean_result['mean'].values[0]:,.2f}")
        print(f"  SE: {mean_result['se'].values[0]:.4f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
