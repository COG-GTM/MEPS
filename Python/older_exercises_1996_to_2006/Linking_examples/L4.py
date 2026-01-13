"""
AHRQ MEPS Data Users Workshop - Linking Example L4

This example shows how to:
(1) Identify persons with specific condition(s)
(2) Subset condition file to person level
(3) Make one variable from five variables
(4) Calculate standard errors for survey estimates

Input files:
    - h61.sas7bdat (2001 Conditions)
    - h60.sas7bdat (2001 Full-Year Persons)

Python equivalent of: SAS/older_exercises_1996_to_2006/Linking_examples/L4/L4.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_freq, survey_total


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS/DATA")
    
    print("=" * 80)
    print("AHRQ MEPS DATA USERS WORKSHOP (LINKING)")
    print("Link 2001 Household File and 2001 Conditions File")
    print("=" * 80)
    
    # Labels
    overall_labels = {
        1: 'Very Serious',
        2: 'Somewhat Serious',
        3: 'Not Very Serious',
        4: 'Not at All',
        5: 'Missing',
        6: 'Not Have Asthma'
    }
    asthma_labels = {1: 'Has Asthma', 2: 'No Asthma'}
    agecat_labels = {1: '0-17', 2: '18+'}
    
    # Load Conditions file
    print("\n" + "-" * 60)
    print("PERSONS WITH ASTHMA")
    print("-" * 60)
    
    cond_file = data_dir / "h61.sas7bdat"
    print(f"Loading conditions data from: {cond_file}")
    
    h61 = load_sas_data(cond_file)
    print(f"Total condition records: {len(h61):,}")
    
    # Identify persons with asthma (ICD-9 code 493)
    asthma_cond = h61[h61['ICD9CODX'] == '493'].copy()
    print(f"Asthma condition records: {len(asthma_cond):,}")
    
    # Keep first-reported asthma record for person
    asthma_cond = asthma_cond.sort_values(['DUPERSID', 'CONDRN'])
    asthma_first = asthma_cond.groupby('DUPERSID').first().reset_index()
    
    print(f"Persons with asthma: {len(asthma_first):,}")
    
    # Assign first-reported OVRALLi to OVERALL
    # OVRALL1-OVRALL5 are round-specific variables
    ovrall_cols = ['OVRALL1', 'OVRALL2', 'OVRALL3', 'OVRALL4', 'OVRALL5']
    
    def get_overall(row):
        for col in ovrall_cols:
            if col in row and row[col] > -1:
                return row[col]
        return 5  # Missing
    
    if all(col in asthma_first.columns for col in ovrall_cols):
        asthma_first['OVERALL'] = asthma_first.apply(get_overall, axis=1)
    else:
        asthma_first['OVERALL'] = 5
    
    print("\nOVERALL (How Asthma Affects Health) distribution:")
    print(asthma_first['OVERALL'].map(overall_labels).value_counts().sort_index())
    
    # Load Full-Year file
    print("\n" + "-" * 60)
    print("ALL PERSONS (WITH POSITIVE WEIGHT)")
    print("-" * 60)
    
    fyc_file = data_dir / "h60.sas7bdat"
    print(f"Loading FYC data from: {fyc_file}")
    
    h60 = load_sas_data(fyc_file, columns=[
        'DUPERSID', 'PERWT01F', 'VARSTR01', 'VARPSU01',
        'AGE31X', 'AGE42X', 'AGE53X'
    ])
    
    # Merge with asthma data
    asthma_subset = asthma_first[['DUPERSID', 'OVERALL']].copy()
    
    pers = h60.merge(asthma_subset, on='DUPERSID', how='left')
    
    # Subset to positive weight
    pers = pers[pers['PERWT01F'] > 0].copy()
    
    # Create asthma indicator
    pers['ASTHMA'] = np.where(pers['OVERALL'].notna(), 1, 2)
    
    # Fill missing OVERALL
    pers['OVERALL'] = pers['OVERALL'].fillna(6)
    
    # Create AGE variable
    pers['AGE'] = np.where(pers['AGE53X'] >= 0, pers['AGE53X'],
                  np.where(pers['AGE42X'] >= 0, pers['AGE42X'],
                  np.where(pers['AGE31X'] >= 0, pers['AGE31X'], -1)))
    
    # Create age category
    pers['AGECAT'] = np.where((pers['AGE'] >= 0) & (pers['AGE'] < 18), 1,
                    np.where(pers['AGE'] >= 18, 2, 0))
    
    print(f"\nTotal persons with positive weight: {len(pers):,}")
    
    print("\nAsthma distribution:")
    print(pers['ASTHMA'].map(asthma_labels).value_counts())
    
    print("\nAsthma by age category:")
    print(pd.crosstab(pers['ASTHMA'].map(asthma_labels), 
                      pers['AGECAT'].map(agecat_labels), margins=True))
    
    # Survey estimates - Asthma prevalence
    print("\n" + "=" * 80)
    print("ASTHMA PREVALENCE")
    print("=" * 80)
    
    design = SurveyDesign(
        data=pers,
        strata='VARSTR01',
        cluster='VARPSU01',
        weight='PERWT01F'
    )
    
    total_pop = pers['PERWT01F'].sum()
    
    for asthma_val in [1, 2]:
        subset = pers[pers['ASTHMA'] == asthma_val]
        wt = subset['PERWT01F'].sum()
        pct = wt / total_pop * 100
        print(f"\n{asthma_labels[asthma_val]}:")
        print(f"  N: {len(subset):,}")
        print(f"  Population: {wt:,.0f} ({pct:.1f}%)")
    
    # How asthma affects health (among those with asthma)
    print("\n" + "=" * 80)
    print("HOW ASTHMA AFFECTS OVERALL HEALTH")
    print("(Among persons with asthma)")
    print("=" * 80)
    
    asthma_pers = pers[pers['ASTHMA'] == 1].copy()
    asthma_total = asthma_pers['PERWT01F'].sum()
    
    print(f"\nTotal persons with asthma: {len(asthma_pers):,}")
    
    for overall_val in [1, 2, 3, 4, 5]:
        subset = asthma_pers[asthma_pers['OVERALL'] == overall_val]
        if len(subset) > 0:
            wt = subset['PERWT01F'].sum()
            pct = wt / asthma_total * 100
            print(f"\n{overall_labels[overall_val]}:")
            print(f"  N: {len(subset):,}")
            print(f"  Population: {wt:,.0f} ({pct:.1f}%)")
    
    # By age category
    print("\n" + "-" * 60)
    print("BY AGE CATEGORY")
    print("-" * 60)
    
    for agecat in [1, 2]:
        subset_age = asthma_pers[asthma_pers['AGECAT'] == agecat]
        age_total = subset_age['PERWT01F'].sum()
        
        print(f"\n{agecat_labels[agecat]}:")
        print(f"  Total with asthma: {len(subset_age):,}")
        
        for overall_val in [1, 2, 3, 4]:
            subset = subset_age[subset_age['OVERALL'] == overall_val]
            if len(subset) > 0:
                wt = subset['PERWT01F'].sum()
                pct = wt / age_total * 100 if age_total > 0 else 0
                print(f"    {overall_labels[overall_val]}: {wt:,.0f} ({pct:.1f}%)")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
