"""
AHRQ MEPS Data Users Workshop - Linking Example L5

This example shows how to:
(1) Use condition file to identify events for asthma
(2) Link conditions to events
(3) Merge the condition-event linked file to event files
(4) For each event, construct variables with the same name across events
(5) Combine facility and doctor expenditures
(6) Combine event files, identify type of event
(7) Aggregate event-level records to person level

Input files:
    - h61.sas7bdat (2001 Conditions)
    - h59if1.sas7bdat (2001 Condition-Event Link File)
    - h59a.sas7bdat (2001 Prescribed Medicines)
    - h59e.sas7bdat (2001 Emergency Room Visits)
    - h59f.sas7bdat (2001 Outpatient Visits)
    - h59g.sas7bdat (2001 Office-Based Medical Provider Visits)
    - h60.sas7bdat (2001 Full-Year Persons)

Python equivalent of: SAS/older_exercises_1996_to_2006/Linking_examples/L5/L5.sas
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
    print("AHRQ MEPS DATA USERS WORKSHOP (LINKING)")
    print("Link 2001 Conditions and Event Files")
    print("=" * 80)
    
    # Labels
    inscov_labels = {1: 'Any Private', 2: 'Public Only', 3: 'Uninsured'}
    vistype_labels = {'ob': 'Office-Based', 'op': 'Outpatient', 'er': 'Emergency', 'pm': 'Drug Purchase'}
    sex_labels = {1: 'Male', 2: 'Female'}
    racethnx_labels = {1: 'Hispanic', 2: 'Black, not Hispanic', 3: 'Other'}
    
    # Load Conditions file - identify asthma conditions
    print("\n" + "-" * 60)
    print("IDENTIFY ASTHMA CONDITIONS")
    print("-" * 60)
    
    cond_file = data_dir / "h61.sas7bdat"
    print(f"Loading conditions data from: {cond_file}")
    
    h61 = load_sas_data(cond_file, columns=['CONDIDX', 'ICD9CODX', 'DUPERSID'])
    
    # Filter for asthma (ICD-9 code 493)
    cond = h61[h61['ICD9CODX'] == '493'][['CONDIDX', 'DUPERSID']].copy()
    print(f"Asthma condition records: {len(cond):,}")
    
    # Load Condition-Event Link file
    clnk_file = data_dir / "h59if1.sas7bdat"
    print(f"Loading CLNK data from: {clnk_file}")
    
    clnk = load_sas_data(clnk_file)
    print(f"CLNK records: {len(clnk):,}")
    
    # Merge conditions with link file
    condev = cond.merge(clnk, on='CONDIDX', how='inner')
    condev = condev.drop_duplicates(subset=['EVNTIDX'])
    print(f"Condition-event linked records: {len(condev):,}")
    
    # Load Prescribed Medicines file
    print("\n" + "-" * 60)
    print("PRESCRIBED MEDICINES FOR ASTHMA")
    print("-" * 60)
    
    rx_file = data_dir / "h59a.sas7bdat"
    print(f"Loading RX data from: {rx_file}")
    
    h59a = load_sas_data(rx_file, columns=['RXRECIDX', 'LINKIDX', 'RXSF01X', 'RXXP01X'])
    h59a = h59a.rename(columns={'LINKIDX': 'EVNTIDX'})
    
    # Merge with asthma conditions
    pm = condev.merge(h59a, on='EVNTIDX', how='inner')
    pm['AMBTOTEV'] = pm['RXXP01X']
    pm['AMBFAMEV'] = pm['RXSF01X']
    pm['VISTYPE'] = 'pm'
    print(f"Asthma prescription records: {len(pm):,}")
    
    # Aggregate PMED events to person level
    perpmed = pm.groupby('DUPERSID').agg(
        AMBTOTPD=('AMBTOTEV', 'sum'),
        AMBFAMPD=('AMBFAMEV', 'sum')
    ).reset_index()
    
    print(f"Persons with asthma prescriptions: {len(perpmed):,}")
    
    # Load FYC file for person characteristics
    fyc_file = data_dir / "h60.sas7bdat"
    h60 = load_sas_data(fyc_file, columns=[
        'DUPERSID', 'INSCOV01', 'PERWT01F', 'AGE31X', 'AGE42X', 'AGE53X', 'SEX', 'RACETHNX'
    ])
    
    # Merge with person characteristics
    pers1 = perpmed.merge(h60[['DUPERSID', 'INSCOV01', 'PERWT01F']], on='DUPERSID', how='left')
    
    print("\n" + "=" * 80)
    print("AVERAGE PRESCRIPTION EXPENDITURES PER PERSON FOR ASTHMA")
    print("Total and Paid by Family")
    print("=" * 80)
    
    for inscov in [1, 2, 3]:
        subset = pers1[pers1['INSCOV01'] == inscov]
        if len(subset) > 0:
            wt_sum = subset['PERWT01F'].sum()
            mean_tot = (subset['AMBTOTPD'] * subset['PERWT01F']).sum() / wt_sum if wt_sum > 0 else 0
            mean_fam = (subset['AMBFAMPD'] * subset['PERWT01F']).sum() / wt_sum if wt_sum > 0 else 0
            print(f"\n{inscov_labels[inscov]}:")
            print(f"  N: {len(subset):,}")
            print(f"  Mean Total Paid: ${mean_tot:,.2f}")
            print(f"  Mean Family Paid: ${mean_fam:,.2f}")
    
    # Load Office-Based visits
    print("\n" + "-" * 60)
    print("OFFICE-BASED VISITS FOR ASTHMA")
    print("-" * 60)
    
    ob_file = data_dir / "h59g.sas7bdat"
    h59g = load_sas_data(ob_file, columns=['EVNTIDX', 'OBXP01X', 'OBSF01X'])
    
    ob = condev.merge(h59g, on='EVNTIDX', how='inner')
    ob['AMBTOTEV'] = ob['OBXP01X']
    ob['AMBFAMEV'] = ob['OBSF01X']
    ob['VISTYPE'] = 'ob'
    print(f"Office-based visit records: {len(ob):,}")
    
    # Load Outpatient visits
    print("\n" + "-" * 60)
    print("OUTPATIENT VISITS FOR ASTHMA")
    print("-" * 60)
    
    op_file = data_dir / "h59f.sas7bdat"
    h59f = load_sas_data(op_file, columns=['EVNTIDX', 'OPXP01X', 'OPFSF01X', 'OPDSF01X'])
    
    op = condev.merge(h59f, on='EVNTIDX', how='inner')
    op['AMBTOTEV'] = op['OPXP01X']
    op['AMBFAMEV'] = op['OPFSF01X'].fillna(0) + op['OPDSF01X'].fillna(0)
    op['VISTYPE'] = 'op'
    print(f"Outpatient visit records: {len(op):,}")
    
    # Load Emergency Room visits
    print("\n" + "-" * 60)
    print("EMERGENCY ROOM VISITS FOR ASTHMA")
    print("-" * 60)
    
    er_file = data_dir / "h59e.sas7bdat"
    h59e = load_sas_data(er_file, columns=['EVNTIDX', 'ERXP01X', 'ERFSF01X', 'ERDSF01X'])
    
    er = condev.merge(h59e, on='EVNTIDX', how='inner')
    er['AMBTOTEV'] = er['ERXP01X']
    er['AMBFAMEV'] = er['ERFSF01X'].fillna(0) + er['ERDSF01X'].fillna(0)
    er['VISTYPE'] = 'er'
    print(f"Emergency room visit records: {len(er):,}")
    
    # Combine all event files
    print("\n" + "=" * 80)
    print("FREQUENCY OF AMBULATORY VISITS FOR ASTHMA, BY TYPE OF EVENT")
    print("=" * 80)
    
    allevnt = pd.concat([
        ob[['DUPERSID', 'EVNTIDX', 'AMBTOTEV', 'AMBFAMEV', 'VISTYPE']],
        op[['DUPERSID', 'EVNTIDX', 'AMBTOTEV', 'AMBFAMEV', 'VISTYPE']],
        er[['DUPERSID', 'EVNTIDX', 'AMBTOTEV', 'AMBFAMEV', 'VISTYPE']],
        pm[['DUPERSID', 'EVNTIDX', 'AMBTOTEV', 'AMBFAMEV', 'VISTYPE']]
    ], ignore_index=True)
    
    print(f"\nTotal ambulatory events for asthma: {len(allevnt):,}")
    print("\nBy type of event:")
    for vistype, label in vistype_labels.items():
        count = len(allevnt[allevnt['VISTYPE'] == vistype])
        pct = count / len(allevnt) * 100 if len(allevnt) > 0 else 0
        print(f"  {label}: {count:,} ({pct:.1f}%)")
    
    # Aggregate events to person level
    perev = allevnt.groupby('DUPERSID').agg(
        AMBTOTPD=('AMBTOTEV', 'sum'),
        AMBFAMPD=('AMBFAMEV', 'sum')
    ).reset_index()
    
    # Merge with person characteristics
    pers = perev.merge(h60, on='DUPERSID', how='left')
    
    # Create AGE variable
    pers['AGE'] = np.where(pers['AGE53X'] >= 0, pers['AGE53X'],
                  np.where(pers['AGE42X'] >= 0, pers['AGE42X'],
                  np.where(pers['AGE31X'] >= 0, pers['AGE31X'], -1)))
    
    # Create age groups
    pers['AGEGRP'] = pd.cut(pers['AGE'], bins=[-1, 4, 17, 24, 44, 64, 90], 
                           labels=['0-4', '5-17', '18-24', '25-44', '45-64', '65-90'])
    
    print("\n" + "=" * 80)
    print("AVERAGE EXPENDITURES PER PERSON -- TOTAL AND PAID BY FAMILY")
    print("=" * 80)
    
    # By age group
    print("\n" + "-" * 60)
    print("BY AGE GROUP")
    print("-" * 60)
    
    for agegrp in ['0-4', '5-17', '18-24', '25-44', '45-64', '65-90']:
        subset = pers[pers['AGEGRP'] == agegrp]
        if len(subset) > 0:
            wt_sum = subset['PERWT01F'].sum()
            mean_tot = (subset['AMBTOTPD'] * subset['PERWT01F']).sum() / wt_sum if wt_sum > 0 else 0
            mean_fam = (subset['AMBFAMPD'] * subset['PERWT01F']).sum() / wt_sum if wt_sum > 0 else 0
            print(f"\n{agegrp}:")
            print(f"  N: {len(subset):,}")
            print(f"  Mean Total Paid: ${mean_tot:,.2f}")
            print(f"  Mean Family Paid: ${mean_fam:,.2f}")
    
    # By sex
    print("\n" + "-" * 60)
    print("BY SEX")
    print("-" * 60)
    
    for sex in [1, 2]:
        subset = pers[pers['SEX'] == sex]
        if len(subset) > 0:
            wt_sum = subset['PERWT01F'].sum()
            mean_tot = (subset['AMBTOTPD'] * subset['PERWT01F']).sum() / wt_sum if wt_sum > 0 else 0
            mean_fam = (subset['AMBFAMPD'] * subset['PERWT01F']).sum() / wt_sum if wt_sum > 0 else 0
            print(f"\n{sex_labels[sex]}:")
            print(f"  N: {len(subset):,}")
            print(f"  Mean Total Paid: ${mean_tot:,.2f}")
            print(f"  Mean Family Paid: ${mean_fam:,.2f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
