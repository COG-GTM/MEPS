"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Accessibility and quality of care: Access to Care, 2017

Reasons for difficulty receiving needed care:
    - Number/percent of people
    - By poverty status

Input file: h201.sas7bdat (2017 full-year consolidated)

Python equivalent of: SAS/summary_tables_examples/care_access_2017.sas
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
    print("ACCESSIBILITY AND QUALITY OF CARE: ACCESS TO CARE, 2017")
    print("Reasons for Difficulty Receiving Needed Care")
    print("=" * 80)
    
    # Load FYC file
    fyc_file = data_dir / "h201.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    meps = load_sas_data(fyc_file)
    
    # Define variables
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
    
    # Combined variables
    meps['DELAY_ANY'] = ((meps['DELAY_MD'] == 1) | (meps['DELAY_DN'] == 1) | (meps['DELAY_PM'] == 1)).astype(int)
    meps['AFFORD_ANY'] = ((meps['AFFORD_MD'] == 1) | (meps['AFFORD_DN'] == 1) | (meps['AFFORD_PM'] == 1)).astype(int)
    meps['INSURE_ANY'] = ((meps['INSURE_MD'] == 1) | (meps['INSURE_DN'] == 1) | (meps['INSURE_PM'] == 1)).astype(int)
    meps['OTHER_ANY'] = ((meps['OTHER_MD'] == 1) | (meps['OTHER_DN'] == 1) | (meps['OTHER_PM'] == 1)).astype(int)
    
    # Define domain - persons eligible for access to care supplement who experienced difficulty
    meps['DOMAIN'] = ((meps['ACCELI42'] == 1) & (meps['DELAY_ANY'] == 1)).astype(int)
    
    # Adjust weights so observations aren't dropped
    meps.loc[(meps['DOMAIN'] == 0) & (meps['PERWT17F'] == 0), 'PERWT17F'] = 1
    
    # Define labels
    poverty_labels = {
        1: 'Negative or poor',
        2: 'Near-poor',
        3: 'Low income',
        4: 'Middle Income',
        5: 'High Income'
    }
    
    # QC new variables
    print("\n" + "-" * 60)
    print("QC: DELAY VARIABLES")
    print("-" * 60)
    print(f"DELAY_ANY: {meps['DELAY_ANY'].sum():,}")
    print(f"DOMAIN (eligible + delayed): {meps['DOMAIN'].sum():,}")
    
    # Calculate estimates
    print("\n" + "=" * 80)
    print("REASONS FOR DIFFICULTY RECEIVING NEEDED CARE")
    print("Among Persons Who Experienced Difficulty")
    print("=" * 80)
    
    # Subset to domain
    domain_data = meps[meps['DOMAIN'] == 1].copy()
    
    print(f"\nN (unweighted): {len(domain_data):,}")
    
    reason_vars = [
        ('AFFORD_ANY', "Couldn't afford"),
        ('INSURE_ANY', 'Insurance problems'),
        ('OTHER_ANY', 'Other reasons')
    ]
    
    # Overall estimates
    print("\n" + "-" * 60)
    print("OVERALL")
    print("-" * 60)
    
    design = SurveyDesign(
        data=domain_data,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT17F'
    )
    
    for var, label in reason_vars:
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
        subset = domain_data[domain_data['POVCAT17'] == pov_val].copy()
        if len(subset) > 0:
            design_pov = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT17F'
            )
            
            print(f"\n{pov_label}:")
            print(f"  N: {len(subset):,}")
            
            for var, label in reason_vars:
                total_result = survey_total(design_pov, var)
                mean_result = survey_mean(design_pov, var)
                print(f"  {label}: {total_result['total'].values[0]:,.0f} ({mean_result['mean'].values[0] * 100:.2f}%)")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
