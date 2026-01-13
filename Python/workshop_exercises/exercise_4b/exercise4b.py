"""
DESCRIPTION: THIS PROGRAM ILLUSTRATES HOW TO POOL MEPS LONGITUDINAL DATA FILES FROM DIFFERENT PANELS
             THE EXAMPLE USED IS PANELS 17-19 POPULATION AGE 26-30 WHO ARE UNINSURED BUT HAVE HIGH INCOME IN THE FIRST YEAR

             DATA FROM PANELS 17, 18, AND 19 ARE POOLED.

INPUT FILE:     (1) H183.SAS7BDAT (PANEL 19 LONGITUDINAL FILE)
                (2) H172.SAS7BDAT (PANEL 18 LONGITUDINAL FILE)
                (3) H164.SAS7BDAT (PANEL 17 LONGITUDINAL FILE)
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
    print("EXERCISE8.SAS: POOL MEPS DATA FILES FROM DIFFERENT PANELS (PANELS 17, 18, 19)")
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
        -1: '-1 INAPPLICABLE',
        1: '1 ANY PRIVATE',
        2: '2 PUBLIC ONLY',
        3: '3 UNINSURED'
    }
    
    # Load longitudinal files
    print("\nLoading Panel 17 Longitudinal file...")
    h164 = load_sas_data(os.path.join(meps_data_path, "H164.sas7bdat"))
    h164 = h164[['DUPERSID', 'INSCOVY1', 'INSCOVY2', 'LONGWT', 'VARSTR', 'VARPSU', 'POVCATY1', 'AGEY1X', 'PANEL']].copy()
    
    print("\nLoading Panel 18 Longitudinal file...")
    h172 = load_sas_data(os.path.join(meps_data_path, "H172.sas7bdat"))
    h172 = h172[['DUPERSID', 'INSCOVY1', 'INSCOVY2', 'LONGWT', 'VARSTR', 'VARPSU', 'POVCATY1', 'AGEY1X', 'PANEL']].copy()
    
    print("\nLoading Panel 19 Longitudinal file...")
    h183 = load_sas_data(os.path.join(meps_data_path, "H183.sas7bdat"))
    h183 = h183[['DUPERSID', 'INSCOVY1', 'INSCOVY2', 'LONGWT', 'VARSTR', 'VARPSU', 'POVCATY1', 'AGEY1X', 'PANEL']].copy()
    
    # Pool data
    pool = pd.concat([h164, h172, h183], ignore_index=True)
    
    # Create pooled weight (divide by number of panels)
    pool['POOLWT'] = pool['LONGWT'] / 3
    
    # Create subpopulation flag
    pool['SUBPOP'] = np.where(
        (pool['INSCOVY1'] == 3) & 
        (pool['AGEY1X'] >= 26) & (pool['AGEY1X'] <= 30) & 
        (pool['POVCATY1'] == 5),
        1, 2
    )
    
    # Check missing values
    print("\nCHECK MISSING VALUES ON THE COMBINED DATA:")
    print(pool.isnull().sum())
    
    # Supporting crosstab for the creation of the subpop flag
    print("\nSUPPORTING CROSSTAB FOR THE CREATION OF THE SUBPOP FLAG:")
    print(f"\nSUBPOP distribution:")
    print(pool['SUBPOP'].value_counts())
    
    print("\nSUBPOP * PANEL crosstab:")
    print(pd.crosstab(pool['SUBPOP'], pool['PANEL']))
    
    print("\nSUBPOP * INSCOVY1 * AGEY1X * POVCATY1 crosstab (SUBPOP=1):")
    subpop1 = pool[pool['SUBPOP'] == 1]
    print(f"SUBPOP=1: {len(subpop1)} records")
    print(f"  INSCOVY1: {subpop1['INSCOVY1'].unique()}")
    print(f"  Age range: {subpop1['AGEY1X'].min()}-{subpop1['AGEY1X'].max()}")
    print(f"  POVCATY1: {subpop1['POVCATY1'].unique()}")
    
    # Calculate estimates
    print("\n" + "="*80)
    print("INSURANCE STATUS IN THE SECOND YEAR FOR THOSE")
    print("W/ AGE=26-30, UNINSURED WHOLE YEAR, AND HIGH INCOME IN THE FIRST YEAR")
    print("="*80)
    
    # Filter to subpopulation
    pool_sub = pool[pool['SUBPOP'] == 1].copy()
    
    design = SurveyDesign(
        data=pool_sub,
        strata='VARSTR',
        cluster='VARPSU',
        weight='POOLWT'
    )
    
    # Calculate proportions for each insurance status in year 2
    print("\nINSCOVY2 (Health Insurance Coverage Indicator in Year 2):")
    print("-" * 60)
    
    total_weight = pool_sub['POOLWT'].sum()
    
    for inscov_val in sorted(pool_sub['INSCOVY2'].unique()):
        subset = pool_sub[pool_sub['INSCOVY2'] == inscov_val]
        n = len(subset)
        weighted_n = subset['POOLWT'].sum()
        proportion = weighted_n / total_weight if total_weight > 0 else 0
        
        label = ins_labels.get(int(inscov_val), str(inscov_val))
        print(f"  {label}:")
        print(f"    N: {n:,.0f}")
        print(f"    Proportion: {proportion:.3f}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Exercise 4b - Pool MEPS Longitudinal Data Panels 17-19')
    parser.add_argument('--data-path', type=str, default='C:/MEPS/SAS/DATA',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
