"""
Example code linking MEPS-HC Medical Conditions file to the Office-based
medical visits file, data year 2020:

Event-level estimates:
  - Number of office-based visits for mental health
  - Total expenditures for office-based mental health treatment
  - Mean expenditure per office-based mental health visit

Person-level estimates:
  - Number of people with office-based mental health visits
  - Percent of people with office-based mental health visits
  - Mean expenditure per person for office-based mental health visits

Input files:
  - h220g.sas7bdat   (2020 Office-based event file)
  - h222.sas7bdat    (2020 Conditions file)
  - h220if1.sas7bdat (2020 CLNK: Condition-event link file)
  - h224.sas7bdat    (2020 Full-Year Consolidated file)

Resources:
 - CCSR codes:
    https://github.com/HHS-AHRQ/MEPS/blob/master/Quick_Reference_Guides/meps_ccsr_conditions.csv

 - MEPS-HC Public Use Files:
    https://meps.ahrq.gov/mepsweb/data_stats/download_data_files.jsp

 - MEPS-HC data tools:
    https://datatools.ahrq.gov/meps-hc
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, print_results


def main(meps_data_path: str = "C:/MEPS"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    # Load datasets
    print("Loading datasets...")
    ob20 = load_sas_data(os.path.join(meps_data_path, "h220g.sas7bdat"))
    cond20 = load_sas_data(os.path.join(meps_data_path, "h222.sas7bdat"))
    clnk20 = load_sas_data(os.path.join(meps_data_path, "h220if1.sas7bdat"))
    fyc20 = load_sas_data(os.path.join(meps_data_path, "h224.sas7bdat"))
    
    # Preview files
    print("\nOffice-based visits (first 5 rows):")
    print(ob20.head())
    print("\nConditions (first 5 rows):")
    print(cond20.head())
    print("\nCondition-event link (first 5 rows):")
    print(clnk20.head())
    
    # Keep only needed variables
    ob20_cols = ['PANEL', 'DUPERSID', 'EVNTIDX', 'EVENTRN', 'OBXP20X', 'PERWT20F', 'VARSTR', 'VARPSU']
    ob20_cols += [c for c in ob20.columns if c.startswith('OBDATE') or c.startswith('TELE')]
    ob20x = ob20[[c for c in ob20_cols if c in ob20.columns]].copy()
    
    cond20_cols = ['DUPERSID', 'CONDIDX'] + [c for c in cond20.columns if c.startswith('ICD10') or c.startswith('CCSR')]
    cond20x = cond20[[c for c in cond20_cols if c in cond20.columns]].copy()
    
    fyc20x = fyc20[['DUPERSID', 'PERWT20F', 'VARSTR', 'VARPSU']].copy()
    
    # Filter COND file to only people with Mental Disorders
    # Concatenate CCSR codes
    cond20x['all_CCSR'] = ''
    for col in ['CCSR1X', 'CCSR2X', 'CCSR3X']:
        if col in cond20x.columns:
            cond20x['all_CCSR'] = cond20x['all_CCSR'] + cond20x[col].fillna('').astype(str)
    
    # Filter for mental health conditions
    mental_health_codes = ['MBD', 'FAC002', 'FAC007', 'NVS011', 'SYM008', 'SYM009']
    mental_health_mask = cond20x['all_CCSR'].apply(
        lambda x: any(code in str(x) for code in mental_health_codes)
    )
    mental_health = cond20x[mental_health_mask].copy()
    
    print("\nMental health conditions:")
    if 'ICD10CDX' in mental_health.columns:
        print(mental_health[['ICD10CDX', 'CCSR1X', 'CCSR2X', 'CCSR3X']].value_counts())
    
    # Filter CLNK file to only office-based visits (EVENTYPE = 1)
    clnk_ob = clnk20[clnk20['EVENTYPE'] == 1].copy()
    
    print("\nCLNK Office-based visits only:")
    print(clnk_ob['EVENTYPE'].value_counts())
    
    # Merge conditions file with the conditions-event link file (CLNK)
    mental_health = mental_health.sort_values(['DUPERSID', 'CONDIDX'])
    clnk_ob = clnk_ob.sort_values(['DUPERSID', 'CONDIDX'])
    
    mh_clnk = pd.merge(
        mental_health,
        clnk_ob,
        on=['DUPERSID', 'CONDIDX'],
        how='inner'
    )
    
    # Example of one condition treated in different events
    print("\nExample of one condition treated in different events:")
    print(mh_clnk[mh_clnk['CONDIDX'] == '2320109103009'])
    
    # Example of one event treating multiple Mental Health conditions
    print("\nExample of one event treating multiple Mental Health conditions:")
    print(mh_clnk[mh_clnk['EVNTIDX'] == '2320051101205101'])
    
    # De-duplicate by event ID ('EVNTIDX')
    mh_clnk_nodup = mh_clnk[['DUPERSID', 'EVNTIDX', 'EVENTYPE']].drop_duplicates()
    
    # Merge on event files
    print("\nmh_clnk (first 5 rows):")
    print(mh_clnk_nodup.head())
    print("\nob20x (first 5 rows):")
    print(ob20x.head())
    
    ob20x = ob20x.sort_values(['DUPERSID', 'EVNTIDX'])
    ob_mental_health = pd.merge(
        mh_clnk_nodup,
        ob20x,
        on=['DUPERSID', 'EVNTIDX'],
        how='inner'
    )
    
    # Set indicator variable for all visits
    ob_mental_health['mh_ob_visit'] = 1
    
    # QC
    print("\nob_mental_health (first 5 rows):")
    print(ob_mental_health.head())
    print("\nEVENTYPE and mh_ob_visit frequency:")
    print(ob_mental_health[['EVENTYPE', 'mh_ob_visit']].value_counts())
    
    # Merge on FYC file for complete Strata, PSUs
    ob_mental_health = ob_mental_health.sort_values('DUPERSID')
    fyc20x = fyc20x.sort_values('DUPERSID')
    
    ob_mh_fyc = pd.merge(
        fyc20x,
        ob_mental_health,
        on='DUPERSID',
        how='left'
    )
    
    # Create indicator variables
    ob_mh_fyc['mh_ob'] = ob_mh_fyc['mh_ob_visit'].notna().astype(int)
    ob_mh_fyc['mh_ob_visit'] = ob_mh_fyc['mh_ob_visit'].fillna(0).astype(int)
    
    # Reset missing OBXP20X to 0
    ob_mh_fyc['OBXP20X'] = ob_mh_fyc['OBXP20X'].fillna(0)
    
    # QC
    print("\nob_mh_fyc frequency:")
    print(ob_mh_fyc[['mh_ob', 'mh_ob_visit']].value_counts())
    
    print("\nob_mh_fyc where mh_ob = 0 (first 5 rows):")
    print(ob_mh_fyc[ob_mh_fyc['mh_ob'] == 0].head())
    print("\nob_mh_fyc where mh_ob = 1 (first 5 rows):")
    print(ob_mh_fyc[ob_mh_fyc['mh_ob'] == 1].head())
    
    # Event-level estimates
    # Expected results:
    #  - Number of office-based visits for mental health:       343,810,085 (SE: 22,252,863)
    #  - Total exp. for office-based mental health visits:  $60,209,392,314 (SE: 4,437,433,004)
    #  - Mean exp. per visit:                                       $175.12 (SE: 6.46)
    
    print("\n" + "="*80)
    print("EVENT-LEVEL ESTIMATES")
    print("="*80)
    
    # Create survey design for event-level analysis
    # Need to use domain for correct SEs
    design_event = SurveyDesign(
        data=ob_mh_fyc,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT20F'
    )
    
    # Filter to mh_ob = 1 for domain analysis
    ob_mh_fyc_domain = ob_mh_fyc[ob_mh_fyc['mh_ob'] == 1].copy()
    design_event_domain = SurveyDesign(
        data=ob_mh_fyc_domain,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT20F'
    )
    
    # Number of office-based visits for mental health (sum of mh_ob_visit)
    event_totals = survey_total(design_event_domain, ['mh_ob_visit', 'OBXP20X'])
    print("\nEvent-level totals (domain: mh_ob = 1):")
    print_results(event_totals, format_dict={
        'Sum': '{:,.0f}',
        'StdDev': '{:,.0f}'
    })
    
    # Mean expenditure per visit
    event_means = survey_mean(design_event_domain, 'OBXP20X')
    print("\nMean expenditure per office-based mental health visit:")
    print_results(event_means, format_dict={
        'Mean': '${:,.2f}',
        'StdErr': '${:,.2f}'
    })
    
    # Person-level estimates
    # Expected results:
    #  - Number of people with office visit for MH:  29,816,984 (SE: 1,192,676)
    #  - Percent of people with office visit for MH:      9.08% (SE: 0.29%)
    #  - Mean exp per person for office visits for MH: $2019.30 (SE: 126.16)
    
    print("\n" + "="*80)
    print("PERSON-LEVEL ESTIMATES")
    print("="*80)
    
    # Aggregate to person-level
    pers_mh = ob_mh_fyc.groupby(['DUPERSID', 'VARSTR', 'VARPSU']).agg({
        'PERWT20F': 'mean',
        'OBXP20X': 'sum',
        'mh_ob_visit': 'sum',
        'mh_ob': 'mean'
    }).reset_index()
    
    pers_mh.columns = ['DUPERSID', 'VARSTR', 'VARPSU', 'PERWT20F', 'persXP', 'pers_nevents', 'mh_ob_pers']
    
    # Create indicator for person with MH visit
    pers_mh['mh_ob_visit_pers'] = (pers_mh['pers_nevents'] > 0).astype(int)
    
    # QC: same number of records as fyc file
    print("\npers_mh vs. fyc:")
    print(f"pers_mh records: {len(pers_mh)}")
    print(f"fyc20 records: {len(fyc20)}")
    print(pers_mh['mh_ob_pers'].value_counts())
    
    # QC: mh_pers and mh_ob_visit_pers consistency
    print("\npers_mh QC:")
    print(pd.crosstab(pers_mh['mh_ob_pers'] > 0, pers_mh['mh_ob_visit_pers'] > 0))
    
    # Create survey design for person-level analysis
    design_pers = SurveyDesign(
        data=pers_mh,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT20F'
    )
    
    # Person-level estimates with domain
    pers_mh_domain = pers_mh[pers_mh['mh_ob_pers'] > 0].copy()
    design_pers_domain = SurveyDesign(
        data=pers_mh_domain,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT20F'
    )
    
    # Number of people with office visit for MH (sum)
    # Percent of people with office visit for MH (mean)
    print("\nPerson-level estimates:")
    
    # Total people with MH visits
    pers_totals = survey_total(design_pers, 'mh_ob_visit_pers')
    print("\nNumber of people with office-based mental health visits:")
    print_results(pers_totals, format_dict={
        'Sum': '{:,.0f}',
        'StdDev': '{:,.0f}'
    })
    
    # Percent of people with MH visits
    pers_means = survey_mean(design_pers, 'mh_ob_visit_pers')
    print("\nPercent of people with office-based mental health visits:")
    print_results(pers_means, format_dict={
        'Mean': '{:.2%}',
        'StdErr': '{:.2%}'
    })
    
    # Mean expenditure per person with MH visits (domain: mh_ob_pers = 1)
    pers_exp_means = survey_mean(design_pers_domain, 'persXP')
    print("\nMean expenditure per person for office-based mental health visits:")
    print_results(pers_exp_means, format_dict={
        'Mean': '${:,.2f}',
        'StdErr': '${:,.2f}'
    })
    
    # QC: Number of visits and total expenditures
    pers_qc_totals = survey_total(design_pers_domain, ['pers_nevents', 'persXP'])
    print("\nQC - Total visits and expenditures:")
    print_results(pers_qc_totals, format_dict={
        'Sum': '{:,.0f}',
        'StdDev': '{:,.0f}'
    })


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Mental Health Office Visits Analysis')
    parser.add_argument('--data-path', type=str, default='C:/MEPS',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
