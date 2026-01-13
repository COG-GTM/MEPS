"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Medical Conditions, 2018:
 - Number of people with care
 - Number of events
 - Total expenditures
 - Mean expenditure per person

Note: Starting in 2016, conditions were converted from ICD-9 and CCS codes
 to ICD-10 and CCSR codes

Input files:
 - H206A.sas7bdat (2018 RX event file)
 - H206D.sas7bdat (2018 IP event file)
 - H206E.sas7bdat (2018 ER event file)
 - H206F.sas7bdat (2018 OP event file)
 - H206G.sas7bdat (2018 OB event file)
 - H206H.sas7bdat (2018 HH event file)
 - H206IF1.sas7bdat (2018 CLNK: Condition-event link file)
 - H207.sas7bdat (2018 Conditions file)
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, print_results


def load_ccsr_crosswalk():
    """Load CCSR to collapsed condition crosswalk from GitHub."""
    url = "https://raw.githubusercontent.com/HHS-AHRQ/MEPS/master/Quick_Reference_Guides/meps_ccsr_conditions.csv"
    try:
        crosswalk = pd.read_csv(url)
        crosswalk = crosswalk.rename(columns={
            'CCSR_Code': 'CCSR',
            'MEPS_collapsed_condition_categor': 'CONDITION'
        })
        return crosswalk[['CCSR', 'CONDITION']]
    except Exception as e:
        print(f"Warning: Could not load CCSR crosswalk from GitHub: {e}")
        return None


def main(meps_data_path: str = "C:/MEPS"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    print("MEPS-HC Data Tools: Medical Conditions, 2018")
    print("="*80)
    
    # Load event files
    print("\nLoading event files...")
    
    # RX events
    rx = load_sas_data(os.path.join(meps_data_path, "H206A.sas7bdat"))
    rx_pers = rx.groupby(['DUPERSID', 'LINKIDX', 'VARSTR', 'VARPSU', 'PERWT18F']).agg({
        'RXXP18X': ['sum', 'count']
    }).reset_index()
    rx_pers.columns = ['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT18F', 'XP18X', 'N_FILLS']
    rx_pers['DATA'] = 'RX'
    rx_pers['N_EVENTS'] = rx_pers['N_FILLS']
    
    # IP events
    ip = load_sas_data(os.path.join(meps_data_path, "H206D.sas7bdat"))
    ip = ip[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT18F', 'IPXP18X']].copy()
    ip = ip.rename(columns={'IPXP18X': 'XP18X'})
    ip['DATA'] = 'IP'
    ip['N_EVENTS'] = 1
    
    # ER events
    er = load_sas_data(os.path.join(meps_data_path, "H206E.sas7bdat"))
    er = er[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT18F', 'ERXP18X']].copy()
    er = er.rename(columns={'ERXP18X': 'XP18X'})
    er['DATA'] = 'ER'
    er['N_EVENTS'] = 1
    
    # OP events
    op = load_sas_data(os.path.join(meps_data_path, "H206F.sas7bdat"))
    op = op[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT18F', 'OPXP18X']].copy()
    op = op.rename(columns={'OPXP18X': 'XP18X'})
    op['DATA'] = 'OP'
    op['N_EVENTS'] = 1
    
    # OB events
    ob = load_sas_data(os.path.join(meps_data_path, "H206G.sas7bdat"))
    ob = ob[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT18F', 'OBXP18X']].copy()
    ob = ob.rename(columns={'OBXP18X': 'XP18X'})
    ob['DATA'] = 'OB'
    ob['N_EVENTS'] = 1
    
    # HH events
    hh = load_sas_data(os.path.join(meps_data_path, "H206H.sas7bdat"))
    hh = hh[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT18F', 'HHXP18X']].copy()
    hh = hh.rename(columns={'HHXP18X': 'XP18X'})
    hh['DATA'] = 'HH'
    hh['N_EVENTS'] = 1
    
    # Stack event files
    stacked_events = pd.concat([rx_pers, ip, er, op, ob, hh], ignore_index=True)
    stacked_events = stacked_events[['DATA', 'EVNTIDX', 'DUPERSID', 'N_EVENTS', 'XP18X', 'VARSTR', 'VARPSU', 'PERWT18F']]
    
    # Load condition-event link file
    print("Loading condition-event link file...")
    clnk = load_sas_data(os.path.join(meps_data_path, "H206IF1.sas7bdat"))
    
    # Load conditions file
    print("Loading conditions file...")
    cond_puf = load_sas_data(os.path.join(meps_data_path, "H207.sas7bdat"))
    
    # Load CCSR crosswalk
    print("Loading CCSR crosswalk...")
    condition_codes = load_ccsr_crosswalk()
    
    # Merge conditions with CLNK
    cond_clink = pd.merge(
        clnk[['DUPERSID', 'CONDIDX', 'EVNTIDX']],
        cond_puf[['DUPERSID', 'CONDIDX'] + [c for c in cond_puf.columns if c.startswith('CCSR')]],
        on=['DUPERSID', 'CONDIDX'],
        how='inner'
    )
    
    # Convert multiple CCSRs to separate lines (wide to long)
    ccsr_cols = [c for c in cond_clink.columns if c.startswith('CCSR')]
    cond_long = pd.melt(
        cond_clink,
        id_vars=['DUPERSID', 'CONDIDX', 'EVNTIDX'],
        value_vars=ccsr_cols,
        var_name='CCSR_VAR',
        value_name='CCSR'
    )
    cond_long = cond_long[cond_long['CCSR'] != '-1']
    cond_long = cond_long[cond_long['CCSR'].notna()]
    
    # Merge on collapsed condition codes
    if condition_codes is not None:
        cond = pd.merge(cond_long, condition_codes, on='CCSR', how='left')
        cond = cond[cond['CONDITION'].notna() & (cond['CONDITION'] != '')]
    else:
        cond = cond_long.copy()
        cond['CONDITION'] = 'Unknown'
    
    # De-duplicate by event ID and collapsed code
    cond = cond.drop_duplicates(subset=['DUPERSID', 'EVNTIDX', 'CONDITION'])
    
    # Merge events with linked conditions
    all_events = pd.merge(
        stacked_events, 
        cond[['DUPERSID', 'EVNTIDX', 'CONDITION']], 
        on=['DUPERSID', 'EVNTIDX'], 
        how='inner'
    )
    all_events = all_events[(all_events['CONDITION'] != '') & (all_events['XP18X'] >= 0)]
    
    # Aggregate to person-level by condition
    all_pers = all_events.groupby(['DUPERSID', 'VARSTR', 'VARPSU', 'CONDITION']).agg({
        'XP18X': 'sum',
        'N_EVENTS': 'sum',
        'PERWT18F': 'first'
    }).reset_index()
    all_pers.columns = ['DUPERSID', 'VARSTR', 'VARPSU', 'CONDITION', 'PERS_XP', 'N_EVENTS', 'PERWT18F']
    all_pers['PERSON'] = 1
    
    # Calculate estimates
    print("\n" + "="*80)
    print("MEDICAL CONDITIONS EXPENDITURES, 2018")
    print("="*80)
    
    # By condition
    for condition in sorted(all_pers['CONDITION'].unique()):
        if condition == '':
            continue
        
        cond_data = all_pers[all_pers['CONDITION'] == condition].copy()
        
        if len(cond_data) == 0:
            continue
        
        design = SurveyDesign(
            data=cond_data,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWT18F'
        )
        
        person_total = survey_total(design, 'PERSON')
        events_total = survey_total(design, 'N_EVENTS')
        exp_results = survey_mean(design, 'PERS_XP')
        exp_total = survey_total(design, 'PERS_XP')
        
        print(f"\n{condition}")
        print("-" * 60)
        print(f"  Number of people with care: {person_total['Sum'].values[0]:,.0f} (SE: {person_total['StdDev'].values[0]:,.0f})")
        print(f"  Number of events: {events_total['Sum'].values[0]:,.0f} (SE: {events_total['StdDev'].values[0]:,.0f})")
        print(f"  Total expenditures: ${exp_total['Sum'].values[0]:,.0f} (SE: ${exp_total['StdDev'].values[0]:,.0f})")
        print(f"  Mean expenditure per person: ${exp_results['Mean'].values[0]:,.2f} (SE: ${exp_results['StdErr'].values[0]:,.2f})")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Summary Tables - Medical Conditions 2018')
    parser.add_argument('--data-path', type=str, default='C:/MEPS',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
