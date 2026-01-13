"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Health insurance, 2016:
    - Number/percent of people
    - By insurance coverage and age groups

Input file: h192.ssp (2016 full-year consolidated)

Python equivalent of: SAS/summary_tables_examples/ins_age_2016.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_freq, survey_total


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS")
    
    print("=" * 80)
    print("HEALTH INSURANCE, 2016")
    print("Number/Percent of People by Insurance Coverage and Age Groups")
    print("=" * 80)
    
    # Load FYC file
    fyc_file = data_dir / "h192.ssp"
    print(f"\nLoading data from: {fyc_file}")
    
    meps = load_sas_data(fyc_file)
    
    # Create age groups
    def age_group(age):
        if pd.isna(age):
            return np.nan
        elif age < 5:
            return 1  # Under 5
        elif age <= 17:
            return 2  # 5-17
        elif age <= 44:
            return 3  # 18-44
        elif age <= 64:
            return 4  # 45-64
        else:
            return 5  # 65+
    
    meps['AGEGRP'] = meps['AGELAST'].apply(age_group)
    
    # Define labels
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
    
    # Calculate estimates
    print("\n" + "=" * 80)
    print("INSURANCE COVERAGE STATUS BY AGE GROUPS")
    print("=" * 80)
    
    design = SurveyDesign(
        data=meps,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT16F'
    )
    
    # By age group
    for age_val, age_label in age_labels.items():
        subset = meps[meps['AGEGRP'] == age_val].copy()
        
        if len(subset) > 0:
            design_age = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT16F'
            )
            
            print(f"\n{age_label}:")
            print("-" * 60)
            print(f"  N (unweighted): {len(subset):,}")
            
            # Get insurance distribution
            freq_result = survey_freq(design_age, 'INSURC16')
            
            print(f"\n  {'Insurance Status':<35} {'Count':>12} {'Percent':>10}")
            print("  " + "-" * 60)
            
            for idx, row in freq_result.iterrows():
                level = row['level']
                if pd.notna(level) and int(level) > 0:
                    ins_label = insurance_labels.get(int(level), f'Insurance {int(level)}')
                    print(f"  {ins_label:<35} {row['count']:>12,.0f} {row['proportion']*100:>9.2f}%")
    
    # Summary by insurance type across all ages
    print("\n" + "=" * 80)
    print("SUMMARY BY INSURANCE TYPE (ALL AGES)")
    print("=" * 80)
    
    freq_result = survey_freq(design, 'INSURC16')
    
    print(f"\n{'Insurance Status':<40} {'Count':>15} {'Percent':>10}")
    print("-" * 70)
    
    for idx, row in freq_result.iterrows():
        level = row['level']
        if pd.notna(level) and int(level) > 0:
            ins_label = insurance_labels.get(int(level), f'Insurance {int(level)}')
            print(f"{ins_label:<40} {row['count']:>15,.0f} {row['proportion']*100:>9.2f}%")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
