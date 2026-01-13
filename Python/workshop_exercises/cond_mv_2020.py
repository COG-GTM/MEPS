"""
MEPS-HC: Linking Medical Conditions to Office-Based Medical Visits

This example code shows how to link the MEPS-HC Medical Conditions file to the
Office-based medical visits file for data year 2020 in order to estimate:

Event-level estimates:
    - Number of office-based visits for mental health
    - Total expenditures for office-based mental health treatment
    - Mean expenditure per office-based mental health visit

Person-level estimates:
    - Number of people with office-based mental health visits
    - Percent of people with office-based mental health visits
    - Mean expenditure per person for office-based mental health visits

Input files:
    - h220g.sas7bdat (2020 Office-based event file)
    - h222.sas7bdat (2020 Conditions file)
    - h220if1.sas7bdat (2020 CLNK: Condition-event link file)
    - h224.sas7bdat (2020 Full-Year Consolidated file)

Resources:
    - CCSR codes: https://github.com/HHS-AHRQ/MEPS/blob/master/Quick_Reference_Guides/meps_ccsr_conditions.csv
    - MEPS-HC Public Use Files: https://meps.ahrq.gov/mepsweb/data_stats/download_data_files.jsp

Python equivalent of: SAS/workshop_exercises/cond_mv_2020.sas
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
    print("MEPS-HC: LINKING MEDICAL CONDITIONS TO OFFICE-BASED VISITS")
    print("MENTAL HEALTH ANALYSIS, 2020")
    print("=" * 80)
    
    # Load datasets
    print("\nLoading data files...")
    
    # Office-based medical visits
    ob_file = data_dir / "h220g.sas7bdat"
    ob20 = load_sas_data(ob_file)
    print(f"  Office-based visit records: {len(ob20):,}")
    
    # Medical conditions
    cond_file = data_dir / "h222.sas7bdat"
    cond20 = load_sas_data(cond_file)
    print(f"  Condition records: {len(cond20):,}")
    
    # Condition-event linkage file
    clnk_file = data_dir / "h220if1.sas7bdat"
    clnk20 = load_sas_data(clnk_file)
    print(f"  CLNK records: {len(clnk20):,}")
    
    # Person-level full-year file
    fyc_file = data_dir / "h224.sas7bdat"
    fyc20 = load_sas_data(fyc_file, columns=['DUPERSID', 'PERWT20F', 'VARSTR', 'VARPSU'])
    print(f"  FYC records: {len(fyc20):,}")
    
    # Keep only needed variables
    ob20x = ob20[['PANEL', 'DUPERSID', 'EVNTIDX', 'EVENTRN', 'OBXP20X', 'PERWT20F', 'VARSTR', 'VARPSU']].copy()
    cond20x = cond20[['DUPERSID', 'CONDIDX', 'ICD10CDX', 'CCSR1X', 'CCSR2X', 'CCSR3X']].copy()
    
    # Filter COND file to only people with Mental Disorders
    # Mental health CCSR codes: MBD*, FAC002, FAC007, NVS011, SYM008, SYM009
    print("\n" + "-" * 60)
    print("FILTER TO MENTAL HEALTH CONDITIONS")
    print("-" * 60)
    
    cond20x['ALL_CCSR'] = cond20x['CCSR1X'].fillna('') + cond20x['CCSR2X'].fillna('') + cond20x['CCSR3X'].fillna('')
    
    mental_health = cond20x[
        cond20x['ALL_CCSR'].str.contains('MBD', na=False) |
        cond20x['ALL_CCSR'].str.contains('FAC002', na=False) |
        cond20x['ALL_CCSR'].str.contains('FAC007', na=False) |
        cond20x['ALL_CCSR'].str.contains('NVS011', na=False) |
        cond20x['ALL_CCSR'].str.contains('SYM008', na=False) |
        cond20x['ALL_CCSR'].str.contains('SYM009', na=False)
    ].copy()
    
    print(f"\nMental health condition records: {len(mental_health):,}")
    print("\nMental health conditions by CCSR1X:")
    print(mental_health['CCSR1X'].value_counts().head(10))
    
    # Filter CLNK file to only office-based visits (EVENTYPE = 1)
    print("\n" + "-" * 60)
    print("FILTER CLNK TO OFFICE-BASED VISITS")
    print("-" * 60)
    
    clnk_ob = clnk20[clnk20['EVENTYPE'] == 1].copy()
    print(f"\nOffice-based event links: {len(clnk_ob):,}")
    
    # Merge conditions with CLNK
    mental_health = mental_health.sort_values(['DUPERSID', 'CONDIDX'])
    clnk_ob = clnk_ob.sort_values(['DUPERSID', 'CONDIDX'])
    
    mh_clnk = mental_health[['DUPERSID', 'CONDIDX']].merge(
        clnk_ob[['DUPERSID', 'CONDIDX', 'EVNTIDX', 'EVENTYPE']],
        on=['DUPERSID', 'CONDIDX'],
        how='inner'
    )
    print(f"\nMental health condition-event links: {len(mh_clnk):,}")
    
    # De-duplicate by event ID
    mh_clnk_nodup = mh_clnk.drop_duplicates(subset=['DUPERSID', 'EVNTIDX', 'EVENTYPE'])
    print(f"Unique mental health events: {len(mh_clnk_nodup):,}")
    
    # Merge with office-based events
    ob20x = ob20x.sort_values(['DUPERSID', 'EVNTIDX'])
    
    ob_mental_health = mh_clnk_nodup.merge(
        ob20x,
        on=['DUPERSID', 'EVNTIDX'],
        how='inner'
    )
    ob_mental_health['MH_OB_VISIT'] = 1
    
    print(f"\nOffice-based mental health visits: {len(ob_mental_health):,}")
    
    # QC: Check event types
    print("\nEvent types (should all be 1=Office-based):")
    print(ob_mental_health['EVENTYPE'].value_counts())
    
    # Merge with FYC for complete strata/PSU
    print("\n" + "-" * 60)
    print("MERGE WITH FYC FOR COMPLETE VARIANCE STRUCTURE")
    print("-" * 60)
    
    ob_mental_health = ob_mental_health.sort_values('DUPERSID')
    fyc20 = fyc20.sort_values('DUPERSID')
    
    ob_mh_fyc = fyc20.merge(
        ob_mental_health[['DUPERSID', 'EVNTIDX', 'OBXP20X', 'MH_OB_VISIT']],
        on='DUPERSID',
        how='left'
    )
    
    # Create indicator for persons with MH office visits
    ob_mh_fyc['MH_OB'] = np.where(ob_mh_fyc['MH_OB_VISIT'].notna(), 1, 0)
    ob_mh_fyc['MH_OB_VISIT'] = ob_mh_fyc['MH_OB_VISIT'].fillna(0)
    ob_mh_fyc['OBXP20X'] = ob_mh_fyc['OBXP20X'].fillna(0)
    
    print(f"\nTotal records after merge: {len(ob_mh_fyc):,}")
    print(f"Records with MH office visits: {ob_mh_fyc['MH_OB'].sum():,}")
    
    # EVENT-LEVEL ESTIMATES
    print("\n" + "=" * 60)
    print("EVENT-LEVEL ESTIMATES")
    print("=" * 60)
    
    # Filter to records with MH office visits for proper domain analysis
    ob_mh_events = ob_mh_fyc[ob_mh_fyc['MH_OB'] == 1].copy()
    
    design_events = SurveyDesign(
        data=ob_mh_events,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT20F'
    )
    
    # Number of office-based visits for mental health
    total_visits = survey_total(design_events, 'MH_OB_VISIT')
    print(f"\nNumber of office-based visits for mental health:")
    print(f"  Total: {total_visits['total'].values[0]:,.0f}")
    print(f"  SE: {total_visits['se'].values[0]:,.0f}")
    
    # Total expenditures for office-based mental health treatment
    total_exp = survey_total(design_events, 'OBXP20X')
    print(f"\nTotal expenditures for office-based mental health visits:")
    print(f"  Total: ${total_exp['total'].values[0]:,.0f}")
    print(f"  SE: ${total_exp['se'].values[0]:,.0f}")
    
    # Mean expenditure per visit
    mean_exp = survey_mean(design_events, 'OBXP20X')
    print(f"\nMean expenditure per office-based mental health visit:")
    print(f"  Mean: ${mean_exp['mean'].values[0]:,.2f}")
    print(f"  SE: ${mean_exp['se'].values[0]:.2f}")
    
    # PERSON-LEVEL ESTIMATES
    print("\n" + "=" * 60)
    print("PERSON-LEVEL ESTIMATES")
    print("=" * 60)
    
    # Aggregate to person level
    pers_mh = ob_mh_fyc.groupby(['DUPERSID', 'VARSTR', 'VARPSU']).agg(
        PERWT20F=('PERWT20F', 'mean'),
        PERSXP=('OBXP20X', 'sum'),
        PERS_NEVENTS=('MH_OB_VISIT', 'sum'),
        MH_OB_VISIT_PERS=('MH_OB_VISIT', 'mean'),
        MH_OB_PERS=('MH_OB', 'mean')
    ).reset_index()
    
    # Convert to binary indicators
    pers_mh['MH_OB_VISIT_PERS'] = (pers_mh['MH_OB_VISIT_PERS'] > 0).astype(int)
    pers_mh['MH_OB_PERS'] = (pers_mh['MH_OB_PERS'] > 0).astype(int)
    
    print(f"\nPerson-level records: {len(pers_mh):,}")
    print(f"Persons with MH office visits: {pers_mh['MH_OB_PERS'].sum():,}")
    
    # QC
    print("\nQC: MH_OB_PERS distribution:")
    print(pers_mh['MH_OB_PERS'].value_counts())
    
    design_pers = SurveyDesign(
        data=pers_mh,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT20F'
    )
    
    # Number of people with office visit for MH
    total_people = survey_total(design_pers, 'MH_OB_VISIT_PERS')
    print(f"\nNumber of people with office visit for mental health:")
    print(f"  Total: {total_people['total'].values[0]:,.0f}")
    print(f"  SE: {total_people['se'].values[0]:,.0f}")
    
    # Percent of people with office visit for MH
    pct_people = survey_mean(design_pers, 'MH_OB_VISIT_PERS')
    print(f"\nPercent of people with office visit for mental health:")
    print(f"  Percent: {pct_people['mean'].values[0] * 100:.2f}%")
    print(f"  SE: {pct_people['se'].values[0] * 100:.2f}%")
    
    # Mean expenditure per person (among those with MH visits)
    pers_mh_sub = pers_mh[pers_mh['MH_OB_PERS'] == 1].copy()
    
    design_pers_sub = SurveyDesign(
        data=pers_mh_sub,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT20F'
    )
    
    mean_exp_pers = survey_mean(design_pers_sub, 'PERSXP')
    print(f"\nMean expenditure per person for office visits for MH:")
    print(f"  Mean: ${mean_exp_pers['mean'].values[0]:,.2f}")
    print(f"  SE: ${mean_exp_pers['se'].values[0]:.2f}")
    
    # QC: Total visits and expenditures from person-level data
    total_visits_qc = survey_total(design_pers_sub, 'PERS_NEVENTS')
    total_exp_qc = survey_total(design_pers_sub, 'PERSXP')
    print(f"\nQC - Total visits (from person-level): {total_visits_qc['total'].values[0]:,.0f}")
    print(f"QC - Total expenditures (from person-level): ${total_exp_qc['total'].values[0]:,.0f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
