"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Accessibility and quality of care: Diabetes Care, 2016

Diabetes care survey (DCS):
 - Number/percent of adults with diabetes receiving hemoglobin A1c blood test
 - By race/ethnicity

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
    
    print("MEPS-HC Data Tools: Diabetes Care, 2016")
    print("Adults with diabetes receiving hemoglobin A1c blood test")
    print("="*80)
    
    # Format labels
    race_labels = {
        1: '1 Hispanic',
        2: '2 White',
        3: '3 Black',
        4: '4 Amer. Indian, AK Native, or mult. races',
        5: '5 Asian, Hawaiian, or Pacific Islander'
    }
    
    diab_a1c_labels = {
        'dk_nonresp': "Don't know/Non-response",
        'inapplicable': 'Inapplicable',
        'no_measurement': 'Did not have measurement',
        'had_measurement': 'Had measurement'
    }
    
    # Load FYC file
    print("\nLoading 2016 Full-Year Consolidated file...")
    h192 = load_sas_data(os.path.join(meps_data_path, "H192.sas7bdat"))
    
    # Define variables
    meps = h192.copy()
    
    # Define domain: persons with positive diabetes weight
    meps['DOMAIN'] = (meps['DIABW16F'] > 0).astype(int)
    
    # Adjust weights so we don't drop observations
    meps.loc[meps['DOMAIN'] == 0, 'DIABW16F'] = 1
    
    # Race/ethnicity (for 2012 and later, use RACETHX and RACEV1X)
    meps['HISP'] = (meps['RACETHX'] == 1).astype(int)
    meps['WHITE'] = (meps['RACETHX'] == 2).astype(int)
    meps['BLACK'] = (meps['RACETHX'] == 3).astype(int)
    meps['NATIVE'] = ((meps['RACETHX'] > 3) & (meps['RACEV1X'].isin([3, 6]))).astype(int)
    meps['ASIAN'] = ((meps['RACETHX'] > 3) & (meps['RACEV1X'].isin([4, 5]))).astype(int)
    
    meps['RACE'] = (1 * meps['HISP'] + 2 * meps['WHITE'] + 3 * meps['BLACK'] + 
                   4 * meps['NATIVE'] + 5 * meps['ASIAN'])
    
    # Categorize A1C measurement
    def categorize_a1c(val):
        if val in [-9, -8, -7]:
            return 'dk_nonresp'
        elif val == -1:
            return 'inapplicable'
        elif val in [0, 96]:
            return 'no_measurement'
        elif 1 <= val <= 95:
            return 'had_measurement'
        else:
            return np.nan
    
    meps['A1C_CAT'] = meps['DSA1C53'].apply(categorize_a1c)
    
    # QC new variables
    print("\nQC: RACE distribution:")
    print(meps['RACE'].value_counts())
    
    # Calculate estimates
    print("\n" + "="*80)
    print("ADULTS WITH DIABETES WITH HEMOGLOBIN A1C MEASUREMENT IN 2016, BY RACE")
    print("="*80)
    
    # Filter to domain
    meps_domain = meps[meps['DOMAIN'] == 1].copy()
    
    # By race
    for race_val in sorted(meps_domain['RACE'].unique()):
        if pd.isna(race_val) or race_val == 0:
            continue
        
        meps_race = meps_domain[meps_domain['RACE'] == race_val].copy()
        
        if len(meps_race) == 0:
            continue
        
        design = SurveyDesign(
            data=meps_race,
            strata='VARSTR',
            cluster='VARPSU',
            weight='DIABW16F'
        )
        
        race_label = race_labels.get(int(race_val), str(race_val))
        print(f"\nRace: {race_label}")
        print("-" * 60)
        
        # Calculate frequencies for A1C categories
        for a1c_cat in ['had_measurement', 'no_measurement']:
            subset = meps_race[meps_race['A1C_CAT'] == a1c_cat]
            n = len(subset)
            weighted_n = subset['DIABW16F'].sum()
            total_weight = meps_race['DIABW16F'].sum()
            proportion = weighted_n / total_weight if total_weight > 0 else 0
            
            label = diab_a1c_labels.get(a1c_cat, a1c_cat)
            print(f"  {label}:")
            print(f"    Frequency: {n:,.0f}")
            print(f"    Weighted Frequency: {weighted_n:,.0f}")
            print(f"    Row Percent: {proportion*100:.2f}%")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Summary Tables - Diabetes Care 2016')
    parser.add_argument('--data-path', type=str, default='C:/MEPS',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
