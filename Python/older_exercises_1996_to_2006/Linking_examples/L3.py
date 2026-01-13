"""
AHRQ MEPS Data Users Workshop - Linking Example L3

This example shows how to:
(1) Aggregate event records to the person level
(2) Make 1 annual variable from 3 round variables
(3) Make a categorical variable from a continuous variable
(4) Calculate standard errors for survey estimates

Input files:
    - h59g.sas7bdat (2001 Office-Based Visits)
    - h60.sas7bdat (2001 Full-Year File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Linking_examples/L3/L3.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_freq, survey_mean


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS/DATA")
    
    print("=" * 80)
    print("AHRQ MEPS DATA USERS WORKSHOP (LINKING)")
    print("Link 2001 Household File and 2001 Events File")
    print("=" * 80)
    
    # Labels
    inscov_labels = {1: 'Any Private', 2: 'Public Only', 3: 'Uninsured'}
    insured_labels = {1: 'Insured', 2: 'Uninsured'}
    agecat_labels = {1: '0-3', 2: '4-7', 3: '8-11', 4: '12-15', 5: '16-17', 6: '18+'}
    genckup_labels = {1: 'General Checkup', 2: 'No General Checkup'}
    
    # Load Office-Based Visits file
    print("\n" + "-" * 60)
    print("# PERSONS WITH A GENERAL CHECKUP IN A PROVIDER'S OFFICE")
    print("-" * 60)
    
    ob_file = data_dir / "h59g.sas7bdat"
    print(f"Loading OB visits data from: {ob_file}")
    
    h59g = load_sas_data(ob_file, columns=['DUPERSID', 'VSTCTGRY', 'OBXP01X', 'OBSF01X'])
    print(f"Total OB visit records: {len(h59g):,}")
    
    # Identify persons with a visit for general checkup and their expenditures
    # VSTCTGRY = 1 indicates general checkup
    
    # Aggregate to person level
    checkup_visits = h59g[h59g['VSTCTGRY'] == 1].copy()
    
    person_checkup = checkup_visits.groupby('DUPERSID').agg(
        AMBTOTPD=('OBXP01X', 'sum'),
        AMBFAMPD=('OBSF01X', 'sum')
    ).reset_index()
    person_checkup['GENCKUP'] = 1
    
    print(f"Persons with general checkup: {len(person_checkup):,}")
    
    # Load Full-Year file
    print("\n" + "-" * 60)
    print("VARIABLES FROM FULL-YEAR FILE (PERSONS WITH POSITIVE WEIGHT)")
    print("-" * 60)
    
    fyc_file = data_dir / "h60.sas7bdat"
    print(f"Loading FYC data from: {fyc_file}")
    
    h60 = load_sas_data(fyc_file, columns=[
        'DUPERSID', 'PERWT01F', 'VARSTR01', 'VARPSU01',
        'AGE31X', 'AGE42X', 'AGE53X', 'INSCOV01'
    ])
    
    # Subset to positive weight persons
    h60 = h60[h60['PERWT01F'] > 0].copy()
    print(f"Persons with positive weight: {len(h60):,}")
    
    # Define AGE as last nonmissing age in 2001
    h60['AGE'] = np.where(h60['AGE53X'] >= 0, h60['AGE53X'],
                 np.where(h60['AGE42X'] >= 0, h60['AGE42X'],
                 np.where(h60['AGE31X'] >= 0, h60['AGE31X'], -1)))
    
    # Make age category variable
    h60['AGECAT'] = np.where(h60['AGE'] < 0, 0,
                   np.where(h60['AGE'] <= 3, 1,
                   np.where(h60['AGE'] <= 7, 2,
                   np.where(h60['AGE'] <= 11, 3,
                   np.where(h60['AGE'] <= 15, 4,
                   np.where(h60['AGE'] <= 17, 5, 6))))))
    
    # Make insurance status variable
    h60['INSURED'] = np.where(h60['INSCOV01'] > 2, 2, 1)
    
    print("\nInsurance status distribution:")
    print(pd.crosstab(h60['INSURED'].map(insured_labels), 
                      h60['INSCOV01'].map(inscov_labels), margins=True))
    
    print("\nAge category distribution:")
    print(h60['AGECAT'].map(agecat_labels).value_counts().sort_index())
    
    # Link person-level file from events file with full-year person file
    print("\n" + "-" * 60)
    print("LINK PERSON-LEVEL FILE FROM EVENTS FILE WITH FULL-YEAR PERSON FILE")
    print("-" * 60)
    
    pers = h60.merge(person_checkup, on='DUPERSID', how='left')
    
    # Fill missing checkup values
    pers['GENCKUP'] = pers['GENCKUP'].fillna(2)
    pers['AMBTOTPD'] = pers['AMBTOTPD'].fillna(0)
    pers['AMBFAMPD'] = pers['AMBFAMPD'].fillna(0)
    
    print(f"\nTotal persons: {len(pers):,}")
    print("\nGeneral checkup distribution:")
    print(pers['GENCKUP'].map(genckup_labels).value_counts())
    
    # Persons Age 18+
    print("\n" + "=" * 80)
    print("PERSONS AGE 18+")
    print("=" * 80)
    
    pers_18plus = pers[pers['AGECAT'] == 6].copy()
    print(f"\nPersons age 18+: {len(pers_18plus):,}")
    
    design = SurveyDesign(
        data=pers_18plus,
        strata='VARSTR01',
        cluster='VARPSU01',
        weight='PERWT01F'
    )
    
    # General checkup by insurance status
    print("\n" + "-" * 60)
    print("GENERAL CHECKUP BY INSURANCE STATUS")
    print("-" * 60)
    
    for genckup in [1, 2]:
        subset = pers_18plus[pers_18plus['GENCKUP'] == genckup]
        total_wt = subset['PERWT01F'].sum()
        pct = total_wt / pers_18plus['PERWT01F'].sum() * 100
        print(f"\n{genckup_labels[genckup]}:")
        print(f"  N: {len(subset):,}")
        print(f"  Weighted: {total_wt:,.0f} ({pct:.1f}%)")
        
        # By insurance status
        for insured in [1, 2]:
            sub_ins = subset[subset['INSURED'] == insured]
            sub_wt = sub_ins['PERWT01F'].sum()
            sub_pct = sub_wt / total_wt * 100 if total_wt > 0 else 0
            print(f"    {insured_labels[insured]}: {sub_wt:,.0f} ({sub_pct:.1f}%)")
    
    # Persons Age 18+ with a General Checkup - Mean expenditures
    print("\n" + "=" * 80)
    print("PERSONS AGE 18+ WITH A GENERAL CHECKUP")
    print("Mean Expenditures by Insurance Status")
    print("=" * 80)
    
    checkup_18plus = pers_18plus[pers_18plus['GENCKUP'] == 1].copy()
    
    for insured in [1, 2]:
        subset = checkup_18plus[checkup_18plus['INSURED'] == insured].copy()
        
        if len(subset) > 0:
            design_sub = SurveyDesign(
                data=subset,
                strata='VARSTR01',
                cluster='VARPSU01',
                weight='PERWT01F'
            )
            
            mean_tot = survey_mean(design_sub, 'AMBTOTPD')
            mean_fam = survey_mean(design_sub, 'AMBFAMPD')
            
            print(f"\n{insured_labels[insured]}:")
            print(f"  N: {len(subset):,}")
            print(f"  Mean Total Paid: ${mean_tot['mean'].values[0]:,.2f}")
            print(f"  Mean Family Paid: ${mean_fam['mean'].values[0]:,.2f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
