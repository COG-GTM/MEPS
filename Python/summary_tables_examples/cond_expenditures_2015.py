"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Medical Conditions, 2015:
    - Number of people with care
    - Number of events
    - Total expenditures
    - Mean expenditure per person

Note: For 2015 and earlier, conditions use ICD-9 and CCS codes
(Starting in 2016, conditions were converted to ICD-10 and CCSR codes)

Input files:
    - h178a.ssp (2015 RX event file)
    - h178d.ssp (2015 IP event file)
    - h178e.ssp (2015 ER event file)
    - h178f.ssp (2015 OP event file)
    - h178g.ssp (2015 OB event file)
    - h178h.ssp (2015 HH event file)
    - h178if1.ssp (2015 CLNK: Condition-event link file)
    - h180.ssp (2015 Conditions file)

Python equivalent of: SAS/summary_tables_examples/cond_expenditures_2015.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total


# CCS code to collapsed condition mapping
CCS_TO_CONDITION = {
    range(-9, 0): '',
    range(1, 10): 'Infectious diseases',
    range(11, 46): 'Cancer',
    (46, 47): 'Non-malignant neoplasm',
    (48,): 'Thyroid disease',
    (49, 50): 'Diabetes mellitus',
    (51, 52, 54, 55, 56, 57, 58): 'Other endocrine, nutritional & immune disorder',
    (53,): 'Hyperlipidemia',
    (59,): 'Anemia and other deficiencies',
    range(60, 65): 'Hemorrhagic, coagulation, and disorders of White Blood cells',
    tuple(range(65, 76)) + tuple(range(650, 671)): 'Mental disorders',
    range(76, 79): 'CNS infection',
    range(79, 82): 'Hereditary, degenerative and other nervous system disorders',
    (82,): 'Paralysis',
    (84,): 'Headache',
    (83,): 'Epilepsy and convulsions',
    (85,): 'Coma, brain damage',
    (86,): 'Cataract',
    (88,): 'Glaucoma',
    (87, 89, 90, 91): 'Other eye disorders',
    (92,): 'Otitis media',
    range(93, 96): 'Other CNS disorders',
    (98, 99): 'Hypertension',
    (96, 97) + tuple(range(100, 109)): 'Heart disease',
    range(109, 114): 'Cerebrovascular disease',
    range(114, 122): 'Other circulatory conditions arteries, veins, and lymphatics',
    (122,): 'Pneumonia',
    (123,): 'Influenza',
    (124,): 'Tonsillitis',
    (125, 126): 'Acute Bronchitis and URI',
    range(127, 135): 'COPD, asthma',
    (135,): 'Intestinal infection',
    (136,): 'Disorders of teeth and jaws',
    (137,): 'Disorders of mouth and esophagus',
    range(138, 142): 'Disorders of the upper GI',
    (142,): 'Appendicitis',
    (143,): 'Hernias',
    range(144, 149): 'Other stomach and intestinal disorders',
    range(153, 156): 'Other GI',
    range(149, 153): 'Gallbladder, pancreatic, and liver disease',
    (156, 157, 158, 160, 161): 'Kidney Disease',
    (159,): 'Urinary tract infections',
    (162, 163): 'Other urinary',
    range(164, 167): 'Male genital disorders',
    (167,): 'Non-malignant breast disease',
    range(168, 177): 'Female genital disorders, and contraception',
    range(177, 196): 'Complications of pregnancy and birth',
    (196, 218): 'Normal birth/live born',
    range(197, 201): 'Skin disorders',
    range(201, 205): 'Osteoarthritis and other non-traumatic joint disorders',
    (205,): 'Back problems',
    (206, 207, 208, 209, 212): 'Other bone and musculoskeletal disease',
    (210, 211): 'Systemic lupus and connective tissues disorders',
    range(213, 218): 'Congenital anomalies',
    range(219, 225): 'Perinatal Conditions',
    tuple(range(225, 237)) + (239, 240, 244): 'Trauma-related disorders',
    (237, 238): 'Complications of surgery or device',
    range(241, 244): 'Poisoning by medical and non-medical substances',
    (259,): 'Residual Codes',
    (10,) + tuple(range(254, 259)): 'Other care and screening',
    range(245, 253): 'Symptoms',
    (253,): 'Allergic reactions',
}


def get_condition(ccs_code):
    """Map CCS code to collapsed condition category."""
    if pd.isna(ccs_code) or ccs_code < 0:
        return ''
    
    ccs_int = int(ccs_code)
    
    # Check each mapping
    for key, condition in CCS_TO_CONDITION.items():
        if isinstance(key, range):
            if ccs_int in key:
                return condition
        elif isinstance(key, tuple):
            if ccs_int in key:
                return condition
    
    return 'Other'


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS")
    
    print("=" * 80)
    print("MEDICAL CONDITIONS, 2015")
    print("Expenditures by Condition Category (ICD-9/CCS)")
    print("=" * 80)
    
    # Load datasets
    print("\nLoading data files...")
    
    # Event files
    rx = load_sas_data(data_dir / "h178a.ssp")
    ip = load_sas_data(data_dir / "h178d.ssp")
    er = load_sas_data(data_dir / "h178e.ssp")
    op = load_sas_data(data_dir / "h178f.ssp")
    ob = load_sas_data(data_dir / "h178g.ssp")
    hh = load_sas_data(data_dir / "h178h.ssp")
    
    print(f"  RX records: {len(rx):,}")
    print(f"  IP records: {len(ip):,}")
    print(f"  ER records: {len(er):,}")
    print(f"  OP records: {len(op):,}")
    print(f"  OB records: {len(ob):,}")
    print(f"  HH records: {len(hh):,}")
    
    # For RX events, count number of fills per event
    rx_pers = rx.groupby(['DUPERSID', 'LINKIDX', 'VARSTR', 'VARPSU', 'PERWT15F']).agg(
        XP15X=('RXXP15X', 'sum'),
        n_fills=('RXXP15X', 'count')
    ).reset_index()
    rx_pers = rx_pers.rename(columns={'LINKIDX': 'EVNTIDX'})
    rx_pers['DATA'] = 'RX'
    
    # Process other event files
    ip_proc = ip[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT15F', 'IPXP15X']].copy()
    ip_proc = ip_proc.rename(columns={'IPXP15X': 'XP15X'})
    ip_proc['DATA'] = 'IP'
    ip_proc['n_fills'] = 1
    
    er_proc = er[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT15F', 'ERXP15X']].copy()
    er_proc = er_proc.rename(columns={'ERXP15X': 'XP15X'})
    er_proc['DATA'] = 'ER'
    er_proc['n_fills'] = 1
    
    op_proc = op[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT15F', 'OPXP15X']].copy()
    op_proc = op_proc.rename(columns={'OPXP15X': 'XP15X'})
    op_proc['DATA'] = 'OP'
    op_proc['n_fills'] = 1
    
    ob_proc = ob[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT15F', 'OBXP15X']].copy()
    ob_proc = ob_proc.rename(columns={'OBXP15X': 'XP15X'})
    ob_proc['DATA'] = 'OB'
    ob_proc['n_fills'] = 1
    
    hh_proc = hh[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT15F', 'HHXP15X']].copy()
    hh_proc = hh_proc.rename(columns={'HHXP15X': 'XP15X'})
    hh_proc['DATA'] = 'HH'
    hh_proc['n_fills'] = 1
    
    # Stack event files
    stacked_events = pd.concat([
        rx_pers[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT15F', 'XP15X', 'n_fills', 'DATA']],
        ip_proc, er_proc, op_proc, ob_proc, hh_proc
    ], ignore_index=True)
    
    # Count events (for RX, each fill is an event)
    stacked_events['n_events'] = stacked_events['n_fills'].apply(lambda x: max(x, 1))
    
    print(f"\nTotal stacked events: {len(stacked_events):,}")
    
    # Load condition-event linking file
    clnk = load_sas_data(data_dir / "h178if1.ssp")
    print(f"CLNK records: {len(clnk):,}")
    
    # Load conditions file
    cond_puf = load_sas_data(data_dir / "h180.ssp")
    print(f"Conditions records: {len(cond_puf):,}")
    
    # Merge conditions file with CLNK
    clnk = clnk[['DUPERSID', 'CONDIDX', 'EVNTIDX']]
    cond_puf = cond_puf[['DUPERSID', 'CONDIDX', 'CCCODEX']]
    
    cond_clnk = clnk.merge(cond_puf, on=['DUPERSID', 'CONDIDX'], how='left')
    
    # Map CCS codes to collapsed conditions
    cond_clnk['Condition'] = cond_clnk['CCCODEX'].apply(get_condition)
    
    # De-duplicate by event ID and collapsed code
    cond = cond_clnk[['DUPERSID', 'EVNTIDX', 'Condition']].drop_duplicates()
    cond = cond[cond['Condition'] != '']
    
    print(f"Condition-event links after processing: {len(cond):,}")
    
    # Merge conditions and event files
    all_events = stacked_events.merge(cond, on=['DUPERSID', 'EVNTIDX'], how='inner')
    all_events = all_events[(all_events['Condition'].notna()) & 
                            (all_events['Condition'] != '') & 
                            (all_events['XP15X'] >= 0)]
    
    print(f"Events with conditions: {len(all_events):,}")
    
    # Aggregate to person-level by Condition
    all_pers = all_events.groupby(['DUPERSID', 'VARSTR', 'VARPSU', 'Condition']).agg(
        PERWT15F=('PERWT15F', 'mean'),
        pers_XP=('XP15X', 'sum'),
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
                weight='PERWT15F'
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
    print(f"{'Condition':<50} {'# People':>12} {'# Events':>12} {'Total Exp':>15} {'Mean Exp':>12}")
    print("-" * 100)
    
    for idx, row in results_df.head(25).iterrows():
        print(f"{row['Condition'][:50]:<50} {row['People']:>12,.0f} {row['Events']:>12,.0f} ${row['Total_Exp']:>14,.0f} ${row['Mean_Exp']:>11,.2f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
