"""
DESCRIPTION: THIS PROGRAM ILLUSTRATES HOW TO POOL MEPS DATA FILES FROM DIFFERENT YEARS
             THE EXAMPLE USED IS POPULATION AGE 26-30 WHO ARE UNINSURED BUT HAVE HIGH INCOME

             DATA FROM 2015 AND 2016 ARE POOLED.

             VARIABLES WITH YEAR-SPECIFIC NAMES MUST BE RENAMED BEFORE COMBINING FILES.
             IN THIS PROGRAM THE INSURANCE COVERAGE VARIABLES 'INSCOV15' AND 'INSCOV16' ARE RENAMED TO 'INSCOV'.

INPUT FILE:     (1) H192.SAS7BDAT (2016 FULL-YEAR FILE)
                (2) H181.SAS7BDAT (2015 FULL-YEAR FILE)
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
    print("EXERCISE6.SAS: POOL MEPS DATA FILES FROM DIFFERENT YEARS (2015 and 2016)")
    print("="*80)
    
    # Format labels
    povcat_labels = {
        1: '1 POOR/NEGATIVE',
        2: '2 NEAR POOR',
        3: '3 LOW INCOME',
        4: '4 MIDDLE INCOME',
        5: '5 HIGH INCOME'
    }
    
    ins_labels = {
        1: '1 ANY PRIVATE',
        2: '2 PUBLIC ONLY',
        3: '3 UNINSURED'
    }
    
    # Load 2015 data
    print("\nLoading 2015 Full-Year Consolidated file...")
    h181 = load_sas_data(os.path.join(meps_data_path, "H181.sas7bdat"))
    yr1 = h181[['DUPERSID', 'INSCOV15', 'PERWT15F', 'VARSTR', 'VARPSU', 'POVCAT15', 'AGELAST', 'TOTSLF15']].copy()
    yr1 = yr1[yr1['PERWT15F'] > 0]
    
    # Frequency for 2015
    print("\nUNWEIGHTED FREQUENCY FOR 2015 FY PERSONS WITH AGE 26-30:")
    yr1_age = yr1[(yr1['AGELAST'] >= 26) & (yr1['AGELAST'] <= 30)]
    print(pd.crosstab(yr1_age['POVCAT15'].map(povcat_labels), yr1_age['INSCOV15'].map(ins_labels)))
    
    # Load 2016 data
    print("\nLoading 2016 Full-Year Consolidated file...")
    h192 = load_sas_data(os.path.join(meps_data_path, "H192.sas7bdat"))
    yr2 = h192[['DUPERSID', 'INSCOV16', 'PERWT16F', 'VARSTR', 'VARPSU', 'POVCAT16', 'AGELAST', 'TOTSLF16']].copy()
    yr2 = yr2[yr2['PERWT16F'] > 0]
    
    # Frequency for 2016
    print("\nUNWEIGHTED FREQUENCY FOR 2016 FY PERSONS WITH AGE 26-30:")
    yr2_age = yr2[(yr2['AGELAST'] >= 26) & (yr2['AGELAST'] <= 30)]
    print(pd.crosstab(yr2_age['POVCAT16'].map(povcat_labels), yr2_age['INSCOV16'].map(ins_labels)))
    
    # Rename year-specific variables prior to combining files
    yr1x = yr1.rename(columns={
        'INSCOV15': 'INSCOV',
        'PERWT15F': 'PERWT',
        'POVCAT15': 'POVCAT',
        'TOTSLF15': 'TOTSLF'
    })
    
    yr2x = yr2.rename(columns={
        'INSCOV16': 'INSCOV',
        'PERWT16F': 'PERWT',
        'POVCAT16': 'POVCAT',
        'TOTSLF16': 'TOTSLF'
    })
    
    # Pool data
    pool = pd.concat([yr1x, yr2x], ignore_index=True)
    
    # Create pooled weight (divide by number of years)
    pool['POOLWT'] = pool['PERWT'] / 2
    
    # Create subpopulation flag
    pool['SUBPOP'] = np.where(
        (pool['AGELAST'] >= 26) & (pool['AGELAST'] <= 30) & 
        (pool['POVCAT'] == 5) & (pool['INSCOV'] == 3),
        1, 2
    )
    
    # Check missing values
    print("\nCHECK MISSING VALUES ON THE COMBINED DATA:")
    print(pool.isnull().sum())
    
    # Supporting crosstab for the creation of the subpop flag
    print("\nSUPPORTING CROSSTAB FOR THE CREATION OF THE SUBPOP FLAG:")
    print(f"\nSUBPOP distribution:")
    print(pool['SUBPOP'].value_counts())
    
    print("\nSUBPOP * AGELAST * POVCAT * INSCOV crosstab:")
    subpop1 = pool[pool['SUBPOP'] == 1]
    print(f"SUBPOP=1: {len(subpop1)} records")
    print(f"  Age range: {subpop1['AGELAST'].min()}-{subpop1['AGELAST'].max()}")
    print(f"  POVCAT: {subpop1['POVCAT'].unique()}")
    print(f"  INSCOV: {subpop1['INSCOV'].unique()}")
    
    # Calculate estimates
    print("\n" + "="*80)
    print("WEIGHTED ESTIMATE ON TOTSLF FOR COMBINED DATA")
    print("W/AGE=26-30, UNINSURED WHOLE YEAR, AND HIGH INCOME")
    print("="*80)
    
    # Filter to subpopulation
    pool_sub = pool[pool['SUBPOP'] == 1].copy()
    
    design = SurveyDesign(
        data=pool_sub,
        strata='VARSTR',
        cluster='VARPSU',
        weight='POOLWT'
    )
    
    means = survey_mean(design, 'TOTSLF')
    
    print(f"\nVariable: TOTSLF (TOTAL AMT PAID BY SELF/FAMILY)")
    print(f"  N: {means['N'].values[0]:,.0f}")
    print(f"  Mean: {means['Mean'].values[0]:,.1f}")
    print(f"  SE of Mean: {means['StdErr'].values[0]:.4f}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Exercise 4a - Pool MEPS Data Files 2015-2016')
    parser.add_argument('--data-path', type=str, default='C:/MEPS/SAS/DATA',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
