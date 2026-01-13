"""
AHRQ MEPS Data Users Workshop - Misc Example M7

This example shows how to compute person-level prescribed medicine
expenditures for persons with at least one PMED event.

Input files:
    - h77a.sas7bdat (2003 PMED Events File)
    - h79.sas7bdat (2003 Full-Year Data File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Misc_examples/M7/M7.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS/DATA")
    
    print("=" * 80)
    print("AHRQ MEPS DATA USERS WORKSHOP")
    print("PERSON LEVEL PRESCRIBED MEDICINE EXPENDITURES")
    print("=" * 80)
    
    # Labels
    agecat_labels = {1: 'Under 18', 2: '18-64', 3: '65 and Older'}
    racethn_labels = {1: 'Hispanic', 2: 'Black', 3: 'Asian', 4: 'Other'}
    inscov_labels = {1: 'Any Private', 2: 'Public Only', 3: 'Uninsured'}
    
    # Load PMED Events file to identify persons with at least one PMED event
    print("\n" + "-" * 60)
    print("IDENTIFY PERSONS WITH AT LEAST ONE PMED EVENT")
    print("-" * 60)
    
    pmed_file = data_dir / "h77a.sas7bdat"
    print(f"Loading PMED events data from: {pmed_file}")
    
    puf77a = load_sas_data(pmed_file, columns=['DUPERSID'])
    pmed_persons = puf77a['DUPERSID'].drop_duplicates()
    print(f"Persons with PMED events: {len(pmed_persons):,}")
    
    # Load Full-Year file
    print("\n" + "-" * 60)
    print("LOAD FULL-YEAR FILE")
    print("-" * 60)
    
    fyc_file = data_dir / "h79.sas7bdat"
    print(f"Loading FYC data from: {fyc_file}")
    
    puf79 = load_sas_data(fyc_file, columns=[
        'DUPERSID', 'AGE03X', 'AGE53X', 'AGE42X', 'AGE31X',
        'RXEXP03', 'RXMCD03', 'RXMCR03', 'RXPRV03', 'RXSLF03',
        'RACETHNX', 'PERWT03F', 'VARSTR', 'VARPSU', 'INSCOV03'
    ])
    
    # Create AGE variable
    puf79['AGE'] = np.where(puf79['AGE03X'] >= 0, puf79['AGE03X'],
                   np.where(puf79['AGE53X'] >= 0, puf79['AGE53X'],
                   np.where(puf79['AGE42X'] >= 0, puf79['AGE42X'],
                   np.where(puf79['AGE31X'] >= 0, puf79['AGE31X'], puf79['AGE03X']))))
    
    # Create age categories
    puf79['AGECAT'] = np.where((puf79['AGE'] >= 0) & (puf79['AGE'] < 18), 1,
                     np.where((puf79['AGE'] >= 18) & (puf79['AGE'] < 65), 2,
                     np.where(puf79['AGE'] >= 65, 3, np.nan)))
    
    # Calculate OTHER payment source
    puf79['OTHER'] = puf79['RXEXP03'] - (puf79['RXMCD03'] + puf79['RXMCR03'] + 
                                          puf79['RXPRV03'] + puf79['RXSLF03'])
    
    # Filter to persons with PMED events
    puf79 = puf79[puf79['DUPERSID'].isin(pmed_persons)].copy()
    print(f"Persons with PMED events in FYC: {len(puf79):,}")
    
    # Survey estimates
    print("\n" + "=" * 80)
    print("TOTAL PMED EXPENDITURES")
    print("=" * 80)
    
    design = SurveyDesign(
        data=puf79,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT03F'
    )
    
    total_result = survey_total(design, 'RXEXP03')
    mean_result = survey_mean(design, 'RXEXP03')
    
    print(f"\nTotal PMED Expenditures: ${total_result['total'].values[0]:,.0f}")
    print(f"Mean PMED Expenditures: ${mean_result['mean'].values[0]:,.2f}")
    print(f"SE: ${mean_result['se'].values[0]:.2f}")
    
    # Total expenditures by category (in thousands)
    print("\n" + "=" * 80)
    print("2003 TOTAL PMED EXPENDITURES (DOLLARS IN THOUSANDS)")
    print("=" * 80)
    
    exp_vars = [
        ('RXEXP03', 'Total PMED'),
        ('RXSLF03', 'Out-of-Pocket'),
        ('RXPRV03', 'Private'),
        ('RXMCR03', 'Medicare'),
        ('RXMCD03', 'Medicaid'),
        ('OTHER', 'Other')
    ]
    
    # By Age Category
    print("\n" + "-" * 60)
    print("BY AGE CATEGORY")
    print("-" * 60)
    
    print(f"\n{'Category':<20}", end='')
    for var, label in exp_vars:
        print(f"{label:>15}", end='')
    print()
    print("-" * 110)
    
    # Total
    print(f"{'TOTAL':<20}", end='')
    for var, label in exp_vars:
        total = (puf79[var] * puf79['PERWT03F']).sum() / 1000
        print(f"${total:>13,.0f}", end='')
    print()
    
    for agecat in [1, 2, 3]:
        subset = puf79[puf79['AGECAT'] == agecat]
        if len(subset) > 0:
            print(f"{agecat_labels[agecat]:<20}", end='')
            for var, label in exp_vars:
                total = (subset[var] * subset['PERWT03F']).sum() / 1000
                print(f"${total:>13,.0f}", end='')
            print()
    
    # By Race/Ethnicity
    print("\n" + "-" * 60)
    print("BY RACE/ETHNICITY")
    print("-" * 60)
    
    print(f"\n{'Category':<20}", end='')
    for var, label in exp_vars:
        print(f"{label:>15}", end='')
    print()
    print("-" * 110)
    
    for racethn in [1, 2, 3, 4]:
        subset = puf79[puf79['RACETHNX'] == racethn]
        if len(subset) > 0:
            print(f"{racethn_labels[racethn]:<20}", end='')
            for var, label in exp_vars:
                total = (subset[var] * subset['PERWT03F']).sum() / 1000
                print(f"${total:>13,.0f}", end='')
            print()
    
    # By Insurance Status
    print("\n" + "-" * 60)
    print("BY INSURANCE STATUS")
    print("-" * 60)
    
    print(f"\n{'Category':<20}", end='')
    for var, label in exp_vars:
        print(f"{label:>15}", end='')
    print()
    print("-" * 110)
    
    for inscov in [1, 2, 3]:
        subset = puf79[puf79['INSCOV03'] == inscov]
        if len(subset) > 0:
            print(f"{inscov_labels[inscov]:<20}", end='')
            for var, label in exp_vars:
                total = (subset[var] * subset['PERWT03F']).sum() / 1000
                print(f"${total:>13,.0f}", end='')
            print()
    
    # Mean expenditures
    print("\n" + "=" * 80)
    print("2003 MEAN PMED EXPENDITURES")
    print("=" * 80)
    
    print(f"\n{'Category':<20}", end='')
    for var, label in exp_vars:
        print(f"{label:>15}", end='')
    print()
    print("-" * 110)
    
    # Total
    print(f"{'TOTAL':<20}", end='')
    for var, label in exp_vars:
        wt_sum = puf79['PERWT03F'].sum()
        mean = (puf79[var] * puf79['PERWT03F']).sum() / wt_sum if wt_sum > 0 else 0
        print(f"${mean:>13,.0f}", end='')
    print()
    
    for agecat in [1, 2, 3]:
        subset = puf79[puf79['AGECAT'] == agecat]
        if len(subset) > 0:
            print(f"{agecat_labels[agecat]:<20}", end='')
            for var, label in exp_vars:
                wt_sum = subset['PERWT03F'].sum()
                mean = (subset[var] * subset['PERWT03F']).sum() / wt_sum if wt_sum > 0 else 0
                print(f"${mean:>13,.0f}", end='')
            print()
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
