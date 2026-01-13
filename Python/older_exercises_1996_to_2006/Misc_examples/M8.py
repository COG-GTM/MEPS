"""
AHRQ MEPS Data Users Workshop - Misc Example M8

This example shows how to compute prescribed medicine expenditures
associated with cancer conditions.

In addition to the Medical Conditions and Full-Year files, the Prescribed
Medicines Event file and the CLNK file are used. The PMED expenditures are
summed to the event level. Modified source of payment (SOP) categories are
created as column categories. Row categories are age and race/ethnicity.

Input files:
    - h97.sas7bdat (2005 Full-Year Data File)
    - h96.sas7bdat (2005 Medical Conditions File)
    - h94i1.sas7bdat (2005 CLNK File)
    - h94a.sas7bdat (2005 Prescribed Medicines File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Misc_examples/M8/M8.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from meps_utils import load_sas_data


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS/DATA")
    
    print("=" * 80)
    print("AHRQ MEPS DATA USERS WORKSHOP")
    print("PRESCRIBED MEDICINES EXPENDITURES FOR CANCER CONDITIONS")
    print("=" * 80)
    
    # Labels
    agecat_labels = {1: '< 18', 2: '18-64', 3: '65+'}
    racethn_labels = {1: 'Hispanic', 2: 'Black', 3: 'Asian', 4: 'Other'}
    
    # Load Conditions file - select cancer conditions (CCCODEX 011-045)
    print("\n" + "-" * 60)
    print("SELECT CANCER CONDITIONS FROM 2005 CONDITIONS FILE")
    print("-" * 60)
    
    cond_file = data_dir / "h96.sas7bdat"
    print(f"Loading conditions data from: {cond_file}")
    
    cond05 = load_sas_data(cond_file, columns=['DUPERSID', 'CCCODEX', 'CONDIDX'])
    
    # Filter for cancer conditions (CCCODEX 011-045)
    cond05 = cond05[(cond05['CCCODEX'] >= '011') & (cond05['CCCODEX'] <= '045')].copy()
    cond05 = cond05[['DUPERSID', 'CONDIDX']]
    print(f"Cancer condition records: {len(cond05):,}")
    
    # Load Prescribed Medicines file
    print("\n" + "-" * 60)
    print("GET PRESCRIBED MEDICINES EXPENSES FROM 2005 PMED FILE")
    print("-" * 60)
    
    pmed_file = data_dir / "h94a.sas7bdat"
    print(f"Loading PMED data from: {pmed_file}")
    
    pmedacq = load_sas_data(pmed_file, columns=[
        'DUPERSID', 'RXRECIDX', 'LINKIDX', 'RXSF05X', 'RXMD05X', 
        'RXPV05X', 'RXMR05X', 'RXXP05X', 'RXNDC'
    ])
    pmedacq = pmedacq.sort_values(['LINKIDX', 'RXRECIDX'])
    print(f"Total PMED acquisition records: {len(pmedacq):,}")
    
    # Sum PMED expenses to event level
    print("\n" + "-" * 60)
    print("SUM PMED EXPENSES TO EVENT LEVEL")
    print("-" * 60)
    
    pmedevnt = pmedacq.groupby('LINKIDX').agg(
        DUPERSID=('DUPERSID', 'first'),
        OOP=('RXSF05X', 'sum'),
        MEDICARE=('RXMR05X', 'sum'),
        MEDICAID=('RXMD05X', 'sum'),
        PRIVATE=('RXPV05X', 'sum'),
        TOTRX05=('RXXP05X', 'sum'),
        RXNDC=('RXNDC', 'first')
    ).reset_index()
    
    pmedevnt = pmedevnt.rename(columns={'LINKIDX': 'EVNTIDX'})
    pmedevnt['OTHER'] = (pmedevnt['TOTRX05'] - 
                         (pmedevnt['MEDICARE'] + pmedevnt['MEDICAID'] + 
                          pmedevnt['PRIVATE'] + pmedevnt['OOP'])).round()
    
    print(f"PMED event records: {len(pmedevnt):,}")
    
    # Load CLNK file
    print("\n" + "-" * 60)
    print("MERGE CONDITIONS TO PMED EVENTS THROUGH CLNK FILE")
    print("-" * 60)
    
    clnk_file = data_dir / "h94i1.sas7bdat"
    print(f"Loading CLNK data from: {clnk_file}")
    
    clnk = load_sas_data(clnk_file, columns=['CONDIDX', 'EVNTIDX'])
    print(f"CLNK records: {len(clnk):,}")
    
    # Merge conditions with CLNK by CONDIDX
    condclnk = cond05.merge(clnk, on='CONDIDX', how='left')
    print(f"Conditions with event links: {len(condclnk):,}")
    
    # Merge with PMED events
    condpmed = condclnk.merge(pmedevnt, on='EVNTIDX', how='inner')
    print(f"Cancer PMED events: {len(condpmed):,}")
    
    # De-duplicate expenditures (one event can be linked to multiple conditions)
    condpmed = condpmed.drop_duplicates(subset=['EVNTIDX'])
    print(f"De-duplicated cancer PMED events: {len(condpmed):,}")
    
    # Load Full-Year file for demographics
    print("\n" + "-" * 60)
    print("GET AGE AND RACE/ETHNICITY FROM FULL-YEAR FILE")
    print("-" * 60)
    
    fyc_file = data_dir / "h97.sas7bdat"
    print(f"Loading FYC data from: {fyc_file}")
    
    puf97 = load_sas_data(fyc_file, columns=[
        'DUPERSID', 'AGE05X', 'AGE53X', 'AGE42X', 'AGE31X', 
        'RACETHNX', 'PERWT05F'
    ])
    
    # Create AGE variable
    puf97['AGE'] = np.where(puf97['AGE05X'] >= 0, puf97['AGE05X'],
                   np.where(puf97['AGE53X'] >= 0, puf97['AGE53X'],
                   np.where(puf97['AGE42X'] >= 0, puf97['AGE42X'],
                   np.where(puf97['AGE31X'] >= 0, puf97['AGE31X'], puf97['AGE05X']))))
    
    # Create age categories
    puf97['AGECAT'] = np.where((puf97['AGE'] >= 0) & (puf97['AGE'] < 18), 1,
                     np.where((puf97['AGE'] >= 18) & (puf97['AGE'] < 65), 2,
                     np.where(puf97['AGE'] >= 65, 3, np.nan)))
    
    puf97 = puf97[['DUPERSID', 'AGECAT', 'RACETHNX', 'PERWT05F']]
    
    # Merge demographics onto condition/PMED file
    temp = condpmed.merge(puf97, on='DUPERSID', how='left')
    
    # Convert to thousands
    for col in ['OOP', 'PRIVATE', 'MEDICARE', 'MEDICAID', 'OTHER', 'TOTRX05']:
        temp[col] = temp[col] / 1000
    
    print(f"\nFinal analysis records: {len(temp):,}")
    
    # Output results
    print("\n" + "=" * 80)
    print("CANCER PMED EXPENDITURES (DOLLARS IN THOUSANDS)")
    print("=" * 80)
    
    exp_vars = [
        ('TOTRX05', 'Total'),
        ('OOP', 'OOP'),
        ('PRIVATE', 'Private'),
        ('MEDICARE', 'Medicare'),
        ('MEDICAID', 'Medicaid'),
        ('OTHER', 'Other')
    ]
    
    # Header
    print(f"\n{'Category':<20}", end='')
    for var, label in exp_vars:
        print(f"{label:>12}", end='')
    print()
    print("-" * 92)
    
    # Total
    print(f"{'TOTAL':<20}", end='')
    for var, label in exp_vars:
        total = (temp[var] * temp['PERWT05F']).sum()
        print(f"${total:>10,.0f}", end='')
    print()
    
    # By Age Category
    print("\nBy Age:")
    for agecat in [1, 2, 3]:
        subset = temp[temp['AGECAT'] == agecat]
        if len(subset) > 0:
            print(f"  {agecat_labels[agecat]:<18}", end='')
            for var, label in exp_vars:
                total = (subset[var] * subset['PERWT05F']).sum()
                print(f"${total:>10,.0f}", end='')
            print()
    
    # By Race/Ethnicity
    print("\nBy Race/Ethnicity:")
    for racethn in [1, 2, 3, 4]:
        subset = temp[temp['RACETHNX'] == racethn]
        if len(subset) > 0:
            print(f"  {racethn_labels[racethn]:<18}", end='')
            for var, label in exp_vars:
                total = (subset[var] * subset['PERWT05F']).sum()
                print(f"${total:>10,.0f}", end='')
            print()
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
