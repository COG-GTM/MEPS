"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Accessibility and quality of care: Access to Care, 2017

Reasons for difficulty receiving needed care
 - Number/percent of people
 - By poverty status

Input file: H201.sas7bdat (2017 full-year consolidated)
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
    
    print("MEPS-HC Data Tools: Access to Care, 2017")
    print("Reasons for difficulty receiving needed care")
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
    print("\nLoading 2017 Full-Year Consolidated file...")
    h201 = load_sas_data(os.path.join(meps_data_path, "H201.sas7bdat"))
    
    # Define variables
    meps = h201.copy()
    
    # Reasons for difficulty receiving needed care
    # Any delay / unable to receive needed care
    meps['DELAY_MD'] = ((meps['MDUNAB42'] == 1) | (meps['MDDLAY42'] == 1)).astype(int)
    meps['DELAY_DN'] = ((meps['DNUNAB42'] == 1) | (meps['DNDLAY42'] == 1)).astype(int)
    meps['DELAY_PM'] = ((meps['PMUNAB42'] == 1) | (meps['PMDLAY42'] == 1)).astype(int)
    
    # Among people unable or delayed, how many...
    # ...couldn't afford
    meps['AFFORD_MD'] = ((meps['MDDLRS42'] == 1) | (meps['MDUNRS42'] == 1)).astype(int)
    meps['AFFORD_DN'] = ((meps['DNDLRS42'] == 1) | (meps['DNUNRS42'] == 1)).astype(int)
    meps['AFFORD_PM'] = ((meps['PMDLRS42'] == 1) | (meps['PMUNRS42'] == 1)).astype(int)
    
    # ...had insurance problems
    meps['INSURE_MD'] = ((meps['MDDLRS42'].isin([2, 3])) | (meps['MDUNRS42'].isin([2, 3]))).astype(int)
    meps['INSURE_DN'] = ((meps['DNDLRS42'].isin([2, 3])) | (meps['DNUNRS42'].isin([2, 3]))).astype(int)
    meps['INSURE_PM'] = ((meps['PMDLRS42'].isin([2, 3])) | (meps['PMUNRS42'].isin([2, 3]))).astype(int)
    
    # ...other
    meps['OTHER_MD'] = ((meps['MDDLRS42'] > 3) | (meps['MDUNRS42'] > 3)).astype(int)
    meps['OTHER_DN'] = ((meps['DNDLRS42'] > 3) | (meps['DNUNRS42'] > 3)).astype(int)
    meps['OTHER_PM'] = ((meps['PMDLRS42'] > 3) | (meps['PMUNRS42'] > 3)).astype(int)
    
    meps['DELAY_ANY'] = ((meps['DELAY_MD'] == 1) | (meps['DELAY_DN'] == 1) | (meps['DELAY_PM'] == 1)).astype(int)
    meps['AFFORD_ANY'] = ((meps['AFFORD_MD'] == 1) | (meps['AFFORD_DN'] == 1) | (meps['AFFORD_PM'] == 1)).astype(int)
    meps['INSURE_ANY'] = ((meps['INSURE_MD'] == 1) | (meps['INSURE_DN'] == 1) | (meps['INSURE_PM'] == 1)).astype(int)
    meps['OTHER_ANY'] = ((meps['OTHER_MD'] == 1) | (meps['OTHER_DN'] == 1) | (meps['OTHER_PM'] == 1)).astype(int)
    
    # Define domain: persons eligible to receive the 'access to care' supplement
    # and who experienced difficulty receiving needed care
    meps['DOMAIN'] = ((meps['ACCELI42'] == 1) & (meps['DELAY_ANY'] == 1)).astype(int)
    
    # Adjust weights so we don't drop observations
    meps.loc[(meps['DOMAIN'] == 0) & (meps['PERWT17F'] == 0), 'PERWT17F'] = 1
    
    # QC new variables
    print("\nQC: DELAY_ANY distribution:")
    print(meps['DELAY_ANY'].value_counts())
    
    # Calculate estimates
    print("\n" + "="*80)
    print("REASONS FOR DIFFICULTY RECEIVING ANY NEEDED CARE, BY POVERTY STATUS")
    print("="*80)
    
    # Filter to domain
    meps_domain = meps[meps['DOMAIN'] == 1].copy()
    
    vars_to_analyze = ['AFFORD_ANY', 'INSURE_ANY', 'OTHER_ANY']
    var_labels = {
        'AFFORD_ANY': "Couldn't afford",
        'INSURE_ANY': 'Insurance problems',
        'OTHER_ANY': 'Other'
    }
    
    # By poverty status
    for povcat_val in sorted(meps_domain['POVCAT17'].unique()):
        if pd.isna(povcat_val):
            continue
        
        meps_pov = meps_domain[meps_domain['POVCAT17'] == povcat_val].copy()
        
        if len(meps_pov) == 0:
            continue
        
        design = SurveyDesign(
            data=meps_pov,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWT17F'
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
    parser = argparse.ArgumentParser(description='MEPS Summary Tables - Access to Care 2017')
    parser.add_argument('--data-path', type=str, default='C:/MEPS',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
