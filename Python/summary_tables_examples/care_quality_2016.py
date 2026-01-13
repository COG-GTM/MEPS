"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Accessibility and quality of care: Quality of Care, 2016

Self-administered questionnaire (SAQ):
 - Number/percent of adults by ability to schedule a routine appointment
 - By insurance coverage status

Input file: H192.ssp (2016 full-year consolidated)
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from meps_utils import load_sas_data, SurveyDesign, survey_freq, print_results


def main(meps_data_path: str = "C:/MEPS"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    print("MEPS-HC Data Tools: Quality of Care, 2016")
    print("Ability to schedule a routine appointment (adults)")
    print("="*80)
    
    # Format labels
    freq_labels = {
        4: 'Always',
        3: 'Usually',
        1: 'Sometimes/Never',
        2: 'Sometimes/Never',
        -7: "Don't know/Non-response",
        -8: "Don't know/Non-response",
        -9: "Don't know/Non-response",
        -1: 'Inapplicable'
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
    
    # Define domain: adults who made an appointment
    meps['DOMAIN'] = ((meps['ADRTCR42'] == 1) & (meps['AGELAST'] >= 18)).astype(int)
    
    # Adjust weights so we don't drop observations
    meps.loc[(meps['DOMAIN'] == 0) & (meps['SAQWT16F'] == 0), 'SAQWT16F'] = 1
    
    # Calculate estimates
    print("\n" + "="*80)
    print("ABILITY TO SCHEDULE A ROUTINE APPOINTMENT (ADULTS), BY INSURANCE COVERAGE")
    print("="*80)
    
    # Filter to domain
    meps_domain = meps[meps['DOMAIN'] == 1].copy()
    
    # By insurance coverage
    for insurc_val in sorted(meps_domain['INSURC16'].unique()):
        if pd.isna(insurc_val):
            continue
        
        meps_ins = meps_domain[meps_domain['INSURC16'] == insurc_val].copy()
        
        if len(meps_ins) == 0:
            continue
        
        ins_label = insurance_labels.get(int(insurc_val), str(insurc_val))
        print(f"\nInsurance Coverage: {ins_label}")
        print("-" * 60)
        
        # Calculate frequencies for appointment scheduling ability
        total_weight = meps_ins['SAQWT16F'].sum()
        
        for adrtww_val in [4, 3, 1, 2]:  # Always, Usually, Sometimes/Never
            subset = meps_ins[meps_ins['ADRTWW42'] == adrtww_val]
            n = len(subset)
            weighted_n = subset['SAQWT16F'].sum()
            proportion = weighted_n / total_weight if total_weight > 0 else 0
            
            label = freq_labels.get(adrtww_val, str(adrtww_val))
            if adrtww_val in [1, 2] and adrtww_val == 2:
                continue  # Skip duplicate for Sometimes/Never
            
            print(f"  {label}:")
            print(f"    Frequency: {n:,.0f}")
            print(f"    Weighted Frequency: {weighted_n:,.0f}")
            print(f"    Row Percent: {proportion*100:.2f}%")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Summary Tables - Quality of Care 2016')
    parser.add_argument('--data-path', type=str, default='C:/MEPS',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
