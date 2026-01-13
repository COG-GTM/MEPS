"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Health Insurance, 2016:
 - Number/percent of people by insurance coverage status
 - By age groups

Input file: H192.ssp (2016 full-year consolidated)
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from meps_utils import load_sas_data, SurveyDesign, survey_freq, survey_total, print_results


def main(meps_data_path: str = "C:/MEPS"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    print("MEPS-HC Data Tools: Health Insurance, 2016")
    print("Insurance coverage status by age groups")
    print("="*80)
    
    # Format labels
    age_labels = {
        1: 'Under 5',
        2: '5-17',
        3: '18-44',
        4: '45-64',
        5: '65+'
    }
    
    insurance_labels = {
        1: '<65, Any private',
        2: '<65, Public only',
        3: '<65, Uninsured',
        4: '65+, Medicare only',
        5: '65+, Medicare and private',
        6: '65+, Medicare and other public',
        7: '65+, No medicare',
        8: '65+, No medicare'
    }
    
    # Load FYC file
    print("\nLoading 2016 Full-Year Consolidated file...")
    h192 = load_sas_data(os.path.join(meps_data_path, "H192.sas7bdat"))
    
    # Define variables
    meps = h192.copy()
    
    # Create age groups
    def age_group(age):
        if pd.isna(age):
            return np.nan
        if age < 5:
            return 1
        elif age < 18:
            return 2
        elif age < 45:
            return 3
        elif age < 65:
            return 4
        else:
            return 5
    
    meps['AGECAT'] = meps['AGELAST'].apply(age_group)
    
    # QC new variables
    print("\nQC: AGECAT distribution:")
    print(meps['AGECAT'].value_counts())
    
    # Calculate estimates
    print("\n" + "="*80)
    print("INSURANCE COVERAGE STATUS BY AGE GROUP, 2016")
    print("="*80)
    
    # By age group
    for age_val in sorted(meps['AGECAT'].dropna().unique()):
        meps_age = meps[meps['AGECAT'] == age_val].copy()
        
        if len(meps_age) == 0:
            continue
        
        age_label = age_labels.get(int(age_val), str(age_val))
        print(f"\nAge Group: {age_label}")
        print("-" * 60)
        
        total_weight = meps_age['PERWT16F'].sum()
        
        # By insurance coverage
        for insurc_val in sorted(meps_age['INSURC16'].dropna().unique()):
            subset = meps_age[meps_age['INSURC16'] == insurc_val]
            n = len(subset)
            weighted_n = subset['PERWT16F'].sum()
            proportion = weighted_n / total_weight if total_weight > 0 else 0
            
            ins_label = insurance_labels.get(int(insurc_val), str(insurc_val))
            print(f"  {ins_label}:")
            print(f"    Frequency: {n:,.0f}")
            print(f"    Weighted Frequency: {weighted_n:,.0f}")
            print(f"    Row Percent: {proportion*100:.2f}%")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Summary Tables - Health Insurance 2016')
    parser.add_argument('--data-path', type=str, default='C:/MEPS',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
