"""
DESCRIPTION: THIS PROGRAM ILLUSTRATES HOW TO CONSTRUCT FAMILY-LEVEL VARIABLES FROM PERSON-LEVEL DATA

             THERE ARE TWO DEFINITIONS OF FAMILY UNIT IN MEPS.
                1) CPS FAMILY:  ID IS DUID + CPSFAMID.  CORRESPONDING WEIGHT IS FAMWT15C.
                2) MEPS FAMILY: ID IS DUID + FAMIDYR.   CORRESPONDING WEIGHT IS FAMWT15F.

             THE CPS FAMILY IS USED IN THIS EXERCISE.

INPUT FILE:   H181.SAS7BDAT (2015 FY PUF DATA)
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, print_results


def main(meps_data_path: str = "C:/MEPS/SAS/DATA"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    print("2018 AHRQ MEPS DATA USERS WORKSHOP")
    print("EXERCISE3.SAS: CALCULATE FAMILY-LEVEL ESTIMATES")
    print("="*80)
    
    # Load 2015 Full-Year Consolidated file
    print("\nLoading 2015 Full-Year Consolidated file...")
    h181 = load_sas_data(os.path.join(meps_data_path, "H181.sas7bdat"))
    
    # Sample dump for family IDs
    print("\nSAMPLE DUMP FOR FAMILY IDS:")
    sample_cols = ['DUID', 'PID', 'AGE15X', 'SEX', 'CPSFAMID', 'FAMWT15C', 'FAMIDYR', 'FAMWT15F']
    sample_cols = [c for c in sample_cols if c in h181.columns]
    print(h181[sample_cols].head(20))
    
    # Keep needed variables
    keep_vars = ['DUPERSID', 'DUID', 'CPSFAMID', 'FAMWT15C', 'VARSTR', 'VARPSU', 'TOTSLF15', 'TTLP15X']
    pers = h181[[c for c in keep_vars if c in h181.columns]].copy()
    
    # Sort by DUID and CPSFAMID
    pers = pers.sort_values(['DUID', 'CPSFAMID'])
    
    # Create family-level variables
    fam = pers.groupby(['DUID', 'CPSFAMID']).agg({
        'DUPERSID': 'count',
        'TOTSLF15': 'sum',
        'TTLP15X': 'sum'
    }).reset_index()
    
    fam.columns = ['DUID', 'CPSFAMID', 'FAMSIZE', 'FAMOOP', 'FAMINC']
    
    # Labels
    fam_labels = {
        'FAMSIZE': '# OF PERSONS PER CPS FAMILY',
        'FAMOOP': 'TOTAL OUT-OF-POCKET EXP (TOTSLF15) PER CPS FAMILY',
        'FAMINC': 'TOTAL INCOME (TTLP15X) PER CPS FAMILY'
    }
    
    # Sample dump to check family-level variables
    print("\nA SAMPLE DUMP TO CHECK THE CREATION OF THE FAMILY-LEVEL VARIABLES:")
    
    # Merge back to person level to show
    pers2 = pd.merge(pers, fam, on=['DUID', 'CPSFAMID'], how='left')
    print(pers2.head(20))
    
    # Add weight, VARSTR, and VARPSU to the family-level analytic data
    # Get one record per family with positive weight
    famwt = pers[pers['FAMWT15C'] > 0][['DUID', 'CPSFAMID', 'FAMWT15C', 'VARSTR', 'VARPSU']].drop_duplicates(subset=['DUID', 'CPSFAMID'])
    
    # Merge
    fam2 = pd.merge(fam, famwt, on=['DUID', 'CPSFAMID'], how='inner')
    
    print(f"\nNumber of CPS families: {len(fam2)}")
    
    # Calculate family-level estimates
    print("\n" + "="*80)
    print("CPS FAMILY-LEVEL ESTIMATES ON FAMILY SIZE, OUT-OF-POCKET EXP, AND INCOME, 2015")
    print("="*80)
    
    design = SurveyDesign(
        data=fam2,
        strata='VARSTR',
        cluster='VARPSU',
        weight='FAMWT15C'
    )
    
    vars_to_analyze = ['FAMSIZE', 'FAMOOP', 'FAMINC']
    
    means = survey_mean(design, vars_to_analyze)
    
    print(f"\n{'Variable':<15} {'N':>10} {'Sum of Wgt':>15} {'Mean':>15} {'SE of Mean':>12}")
    print("-" * 70)
    
    for _, row in means.iterrows():
        var = row['Variable']
        label = fam_labels.get(var, var)
        print(f"{var:<15} {row['N']:>10,.0f} {row['SumWgt']:>15,.0f} {row['Mean']:>15,.2f} {row['StdErr']:>12,.4f}")
        print(f"  ({label})")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Exercise 5a - Family-Level Estimates 2015')
    parser.add_argument('--data-path', type=str, default='C:/MEPS/SAS/DATA',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
