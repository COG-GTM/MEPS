"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Accessibility and quality of care: Access to Care, 2019

Did not receive treatment because couldn't afford it:
    - Number/percent of people
    - By poverty status

Input file: h216.sas7bdat (2019 full-year consolidated)

Python equivalent of: SAS/summary_tables_examples/care_access_2019.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS")
    
    print("=" * 80)
    print("ACCESSIBILITY AND QUALITY OF CARE: ACCESS TO CARE, 2019")
    print("Did Not Receive Treatment Because Couldn't Afford It")
    print("=" * 80)
    
    # Load FYC file
    fyc_file = data_dir / "h216.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    meps = load_sas_data(fyc_file)
    
    # Define variables
    # Didn't receive care because couldn't afford it
    meps['AFFORD_MD'] = (meps['AFRDCA42'] == 1).astype(int)  # medical care
    meps['AFFORD_DN'] = (meps['AFRDDN42'] == 1).astype(int)  # dental care
    meps['AFFORD_PM'] = (meps['AFRDPM42'] == 1).astype(int)  # prescribed medicines
    meps['AFFORD_ANY'] = ((meps['AFFORD_MD'] == 1) | 
                          (meps['AFFORD_DN'] == 1) | 
                          (meps['AFFORD_PM'] == 1)).astype(int)  # any care
    
    # Define domain - persons eligible to receive the 'access to care' supplement
    meps['DOMAIN'] = (meps['ACCELI42'] == 1).astype(int)
    
    # Adjust weights so observations aren't dropped
    meps.loc[(meps['DOMAIN'] == 0) & (meps['PERWT19F'] == 0), 'PERWT19F'] = 1
    
    # QC new variables
    print("\n" + "-" * 60)
    print("QC: NEW VARIABLES")
    print("-" * 60)
    
    print("\nAFRDCA42 vs AFFORD_MD:")
    print(pd.crosstab(meps['AFRDCA42'], meps['AFFORD_MD'], margins=True))
    
    print("\nAFFORD_ANY distribution:")
    print(meps['AFFORD_ANY'].value_counts())
    
    # Calculate estimates
    print("\n" + "=" * 80)
    print("DID NOT RECEIVE TREATMENT BECAUSE COULDN'T AFFORD IT")
    print("By Poverty Status")
    print("=" * 80)
    
    # Subset to domain (persons eligible for access to care supplement)
    domain_data = meps[meps['DOMAIN'] == 1].copy()
    
    poverty_labels = {
        1: 'Negative or poor',
        2: 'Near-poor',
        3: 'Low income',
        4: 'Middle Income',
        5: 'High Income'
    }
    
    afford_vars = [
        ('AFFORD_ANY', 'Any care'),
        ('AFFORD_MD', 'Medical care'),
        ('AFFORD_DN', 'Dental care'),
        ('AFFORD_PM', 'Prescribed medicines')
    ]
    
    # Overall estimates
    print("\n" + "-" * 60)
    print("OVERALL (All Poverty Levels)")
    print("-" * 60)
    
    design = SurveyDesign(
        data=domain_data,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT19F'
    )
    
    print(f"\nN (unweighted): {len(domain_data):,}")
    
    for var, label in afford_vars:
        total_result = survey_total(design, var)
        mean_result = survey_mean(design, var)
        print(f"\n{label}:")
        print(f"  Number of people: {total_result['total'].values[0]:,.0f}")
        print(f"  Percent of people: {mean_result['mean'].values[0] * 100:.2f}%")
    
    # By poverty status
    print("\n" + "-" * 60)
    print("BY POVERTY STATUS")
    print("-" * 60)
    
    for pov_val, pov_label in poverty_labels.items():
        subset = domain_data[domain_data['POVCAT19'] == pov_val].copy()
        if len(subset) > 0:
            design_pov = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT19F'
            )
            
            print(f"\n{pov_label}:")
            print(f"  N: {len(subset):,}")
            
            for var, label in afford_vars:
                total_result = survey_total(design_pov, var)
                mean_result = survey_mean(design_pov, var)
                print(f"  {label}: {total_result['total'].values[0]:,.0f} ({mean_result['mean'].values[0] * 100:.2f}%)")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
