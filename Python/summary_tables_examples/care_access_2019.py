"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Accessibility and quality of care: Access to Care, 2019

Did not receive treatment because couldn't afford it
 - Number/percent of people
 - By poverty status

Input file: H216.sas7bdat (2019 full-year consolidated)
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, print_results


def main(meps_data_path: str = "C:/MEPS"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    print("MEPS-HC Data Tools: Access to Care, 2019")
    print("Did not receive treatment because couldn't afford it")
    print("="*80)
    
    # Format labels
    poverty_labels = {
        1: '1 Negative or poor',
        2: '2 Near-poor',
        3: '3 Low income',
        4: '4 Middle Income',
        5: '5 High Income'
    }
    
    # Load FYC file
    print("\nLoading 2019 Full-Year Consolidated file...")
    h216 = load_sas_data(os.path.join(meps_data_path, "H216.sas7bdat"))
    
    # Define variables
    meps = h216.copy()
    
    # Didn't receive care because couldn't afford it
    meps['AFFORD_MD'] = (meps['AFRDCA42'] == 1).astype(int)  # medical care
    meps['AFFORD_DN'] = (meps['AFRDDN42'] == 1).astype(int)  # dental care
    meps['AFFORD_PM'] = (meps['AFRDPM42'] == 1).astype(int)  # prescribed medicines
    meps['AFFORD_ANY'] = ((meps['AFFORD_MD'] == 1) | (meps['AFFORD_DN'] == 1) | (meps['AFFORD_PM'] == 1)).astype(int)
    
    # Define domain: persons eligible to receive the 'access to care' supplement
    meps['DOMAIN'] = (meps['ACCELI42'] == 1).astype(int)
    
    # Adjust weights so we don't drop observations
    meps.loc[(meps['DOMAIN'] == 0) & (meps['PERWT19F'] == 0), 'PERWT19F'] = 1
    
    # QC new variables
    print("\nQC: AFFORD_ANY distribution:")
    print(meps['AFFORD_ANY'].value_counts())
    
    # Calculate estimates
    print("\n" + "="*80)
    print("DID NOT RECEIVE TREATMENT BECAUSE COULDN'T AFFORD IT, BY POVERTY STATUS")
    print("="*80)
    
    # Filter to domain
    meps_domain = meps[meps['DOMAIN'] == 1].copy()
    
    vars_to_analyze = ['AFFORD_ANY', 'AFFORD_MD', 'AFFORD_DN', 'AFFORD_PM']
    var_labels = {
        'AFFORD_ANY': 'Any care',
        'AFFORD_MD': 'Medical care',
        'AFFORD_DN': 'Dental care',
        'AFFORD_PM': 'Prescribed medicines'
    }
    
    # By poverty status
    for povcat_val in sorted(meps_domain['POVCAT19'].unique()):
        if pd.isna(povcat_val):
            continue
        
        meps_pov = meps_domain[meps_domain['POVCAT19'] == povcat_val].copy()
        
        if len(meps_pov) == 0:
            continue
        
        design = SurveyDesign(
            data=meps_pov,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWT19F'
        )
        
        means = survey_mean(design, vars_to_analyze)
        totals = survey_total(design, vars_to_analyze)
        
        pov_label = poverty_labels.get(int(povcat_val), str(povcat_val))
        print(f"\nPoverty Status: {pov_label}")
        print("-" * 60)
        
        for var in vars_to_analyze:
            mean_row = means[means['Variable'] == var].iloc[0]
            total_row = totals[totals['Variable'] == var].iloc[0]
            label = var_labels.get(var, var)
            print(f"  {label}:")
            print(f"    Number of people: {total_row['Sum']:,.0f} (SE: {total_row['StdDev']:,.0f})")
            print(f"    Percent of people: {mean_row['Mean']*100:.2f}% (SE: {mean_row['StdErr']*100:.2f}%)")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Summary Tables - Access to Care 2019')
    parser.add_argument('--data-path', type=str, default='C:/MEPS',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
