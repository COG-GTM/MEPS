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
    - h206a.sas7bdat (2018 RX event file)
    - h206d.sas7bdat (2018 IP event file)
    - h206e.sas7bdat (2018 ER event file)
    - h206f.sas7bdat (2018 OP event file)
    - h206g.sas7bdat (2018 OB event file)
    - h206h.sas7bdat (2018 HH event file)
    - h206if1.sas7bdat (2018 CLNK: Condition-event link file)
    - h207.sas7bdat (2018 Conditions file)

Python equivalent of: SAS/summary_tables_examples/cond_expenditures_2018.sas
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
    print("MEDICAL CONDITIONS, 2018")
    print("Expenditures by Condition Category")
    print("=" * 80)
    
    # Load datasets
    print("\nLoading data files...")
    
    # Event files
    rx = load_sas_data(data_dir / "h206a.sas7bdat")
    ip = load_sas_data(data_dir / "h206d.sas7bdat")
    er = load_sas_data(data_dir / "h206e.sas7bdat")
    op = load_sas_data(data_dir / "h206f.sas7bdat")
    ob = load_sas_data(data_dir / "h206g.sas7bdat")
    hh = load_sas_data(data_dir / "h206h.sas7bdat")
    
    print(f"  RX records: {len(rx):,}")
    print(f"  IP records: {len(ip):,}")
    print(f"  ER records: {len(er):,}")
    print(f"  OP records: {len(op):,}")
    print(f"  OB records: {len(ob):,}")
    print(f"  HH records: {len(hh):,}")
    
    # For RX events, count number of fills per event
    rx_pers = rx.groupby(['DUPERSID', 'LINKIDX', 'VARSTR', 'VARPSU', 'PERWT18F']).agg(
        XP18X=('RXXP18X', 'sum'),
        n_fills=('RXXP18X', 'count')
    ).reset_index()
    rx_pers = rx_pers.rename(columns={'LINKIDX': 'EVNTIDX'})
    rx_pers['DATA'] = 'RX'
    
    # Process other event files
    ip_proc = ip[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT18F', 'IPXP18X']].copy()
    ip_proc = ip_proc.rename(columns={'IPXP18X': 'XP18X'})
    ip_proc['DATA'] = 'IP'
    ip_proc['n_fills'] = 1
    
    er_proc = er[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT18F', 'ERXP18X']].copy()
    er_proc = er_proc.rename(columns={'ERXP18X': 'XP18X'})
    er_proc['DATA'] = 'ER'
    er_proc['n_fills'] = 1
    
    op_proc = op[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT18F', 'OPXP18X']].copy()
    op_proc = op_proc.rename(columns={'OPXP18X': 'XP18X'})
    op_proc['DATA'] = 'OP'
    op_proc['n_fills'] = 1
    
    ob_proc = ob[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT18F', 'OBXP18X']].copy()
    ob_proc = ob_proc.rename(columns={'OBXP18X': 'XP18X'})
    ob_proc['DATA'] = 'OB'
    ob_proc['n_fills'] = 1
    
    hh_proc = hh[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT18F', 'HHXP18X']].copy()
    hh_proc = hh_proc.rename(columns={'HHXP18X': 'XP18X'})
    hh_proc['DATA'] = 'HH'
    hh_proc['n_fills'] = 1
    
    # Stack event files
    stacked_events = pd.concat([
        rx_pers[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT18F', 'XP18X', 'n_fills', 'DATA']],
        ip_proc, er_proc, op_proc, ob_proc, hh_proc
    ], ignore_index=True)
    
    # Count events (for RX, each fill is an event)
    stacked_events['n_events'] = stacked_events['n_fills'].apply(lambda x: max(x, 1))
    
    print(f"\nTotal stacked events: {len(stacked_events):,}")
    
    # Load condition-event linking file
    clnk = load_sas_data(data_dir / "h206if1.sas7bdat")
    print(f"CLNK records: {len(clnk):,}")
    
    # Load conditions file
    cond_puf = load_sas_data(data_dir / "h207.sas7bdat")
    print(f"Conditions records: {len(cond_puf):,}")
    
    # Load crosswalk for CCSR and collapsed conditions codes
    try:
        ccsr_url = "https://raw.githubusercontent.com/HHS-AHRQ/MEPS/master/Quick_Reference_Guides/meps_ccsr_conditions.csv"
        condition_codes = pd.read_csv(ccsr_url)
        condition_codes = condition_codes.rename(columns={
            'CCSR_Code': 'CCSR',
            'MEPS_collapsed_condition_categor': 'Condition'
        })
        condition_codes = condition_codes[['CCSR', 'Condition']]
        print(f"Condition codes loaded: {len(condition_codes):,}")
    except Exception as e:
        print(f"Warning: Could not load condition codes from URL: {e}")
        # Create a simple mapping
        condition_codes = pd.DataFrame({'CCSR': [], 'Condition': []})
    
    # Merge conditions file with CLNK
    clnk = clnk[['DUPERSID', 'CONDIDX', 'EVNTIDX']]
    cond_puf = cond_puf[['DUPERSID', 'CONDIDX', 'CCSR1X', 'CCSR2X', 'CCSR3X']]
    
    cond_clnk = clnk.merge(cond_puf, on=['DUPERSID', 'CONDIDX'], how='left')
    
    # Convert multiple CCSRs to separate lines (wide to long)
    cond_long = pd.melt(
        cond_clnk,
        id_vars=['DUPERSID', 'CONDIDX', 'EVNTIDX'],
        value_vars=['CCSR1X', 'CCSR2X', 'CCSR3X'],
        var_name='CCSR_VAR',
        value_name='CCSR'
    )
    cond_long = cond_long[cond_long['CCSR'] != '-1']
    cond_long = cond_long.dropna(subset=['CCSR'])
    
    # Merge on collapsed condition codes
    cond = cond_long.merge(condition_codes, on='CCSR', how='left')
    cond = cond[cond['Condition'].notna() & (cond['Condition'] != '')]
    
    # De-duplicate by event ID and collapsed code
    cond = cond[['DUPERSID', 'EVNTIDX', 'Condition']].drop_duplicates()
    
    print(f"Condition-event links after processing: {len(cond):,}")
    
    # Merge conditions and event files
    all_events = stacked_events.merge(cond, on=['DUPERSID', 'EVNTIDX'], how='inner')
    all_events = all_events[(all_events['Condition'].notna()) & (all_events['XP18X'] >= 0)]
    
    print(f"Events with conditions: {len(all_events):,}")
    
    # Aggregate to person-level by Condition
    all_pers = all_events.groupby(['DUPERSID', 'VARSTR', 'VARPSU', 'Condition']).agg(
        PERWT18F=('PERWT18F', 'mean'),
        pers_XP=('XP18X', 'sum'),
        n_events=('n_events', 'sum')
    ).reset_index()
    
    all_pers['PERSON'] = 1
    
    print(f"Person-condition records: {len(all_pers):,}")
    
    # Calculate estimates by condition
    print("\n" + "=" * 80)
    print("ESTIMATES BY CONDITION CATEGORY")
    print("=" * 80)
    
    # Get unique conditions
    conditions = sorted(all_pers['Condition'].unique())
    
    results = []
    for condition in conditions:
        cond_data = all_pers[all_pers['Condition'] == condition].copy()
        
        if len(cond_data) > 0:
            design = SurveyDesign(
                data=cond_data,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT18F'
            )
            
            # Number of people with care
            people_result = survey_total(design, 'PERSON')
            
            # Number of events
            events_result = survey_total(design, 'n_events')
            
            # Total expenditures
            exp_total = survey_total(design, 'pers_XP')
            
            # Mean expenditure per person
            exp_mean = survey_mean(design, 'pers_XP')
            
            results.append({
                'Condition': condition,
                'People': people_result['total'].values[0],
                'Events': events_result['total'].values[0],
                'Total_Exp': exp_total['total'].values[0],
                'Mean_Exp': exp_mean['mean'].values[0]
            })
    
    # Sort by total expenditures
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('Total_Exp', ascending=False)
    
    print("\n" + "-" * 100)
    print(f"{'Condition':<40} {'# People':>12} {'# Events':>12} {'Total Exp':>15} {'Mean Exp':>12}")
    print("-" * 100)
    
    for idx, row in results_df.head(20).iterrows():
        print(f"{row['Condition'][:40]:<40} {row['People']:>12,.0f} {row['Events']:>12,.0f} ${row['Total_Exp']:>14,.0f} ${row['Mean_Exp']:>11,.2f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
