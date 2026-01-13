"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Medical Conditions, 2015:
 - Number of people with care
 - Number of events
 - Total expenditures
 - Mean expenditure per person

Note: Starting in 2016, conditions were converted from ICD-9 and CCS codes
 to ICD-10 and CCSR codes

Input files:
 - H178A.ssp (2015 RX event file)
 - H178D.ssp (2015 IP event file)
 - H178E.ssp (2015 ER event file)
 - H178F.ssp (2015 OP event file)
 - H178G.ssp (2015 OB event file)
 - H178H.ssp (2015 HH event file)
 - H178IF1.ssp (2015 CLNK: Condition-event link file)
 - H180.ssp (2015 Conditions file)
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, print_results


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


def get_condition_from_ccs(ccs_code):
    """Map CCS code to collapsed condition category."""
    if pd.isna(ccs_code):
        return ''
    try:
        ccs_int = int(float(ccs_code))
    except (ValueError, TypeError):
        return ''
    
    for key, condition in CCS_TO_CONDITION.items():
        if isinstance(key, range):
            if ccs_int in key:
                return condition
        elif isinstance(key, tuple):
            if ccs_int in key:
                return condition
    return 'Other'


def main(meps_data_path: str = "C:/MEPS"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    print("MEPS-HC Data Tools: Medical Conditions, 2015")
    print("="*80)
    
    # Load event files
    print("\nLoading event files...")
    
    # RX events
    h178a = load_sas_data(os.path.join(meps_data_path, "H178A.sas7bdat"))
    rx = h178a.groupby(['DUPERSID', 'LINKIDX', 'VARSTR', 'VARPSU', 'PERWT15F']).agg({
        'RXXP15X': ['sum', 'count']
    }).reset_index()
    rx.columns = ['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT15F', 'XP15X', 'N_FILLS']
    rx['DATA'] = 'RX'
    rx['N_EVENTS'] = rx['N_FILLS']
    
    # IP events
    h178d = load_sas_data(os.path.join(meps_data_path, "H178D.sas7bdat"))
    ip = h178d[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT15F', 'IPXP15X']].copy()
    ip = ip.rename(columns={'IPXP15X': 'XP15X'})
    ip['DATA'] = 'IP'
    ip['N_EVENTS'] = 1
    
    # ER events
    h178e = load_sas_data(os.path.join(meps_data_path, "H178E.sas7bdat"))
    er = h178e[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT15F', 'ERXP15X']].copy()
    er = er.rename(columns={'ERXP15X': 'XP15X'})
    er['DATA'] = 'ER'
    er['N_EVENTS'] = 1
    
    # OP events
    h178f = load_sas_data(os.path.join(meps_data_path, "H178F.sas7bdat"))
    op = h178f[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT15F', 'OPXP15X']].copy()
    op = op.rename(columns={'OPXP15X': 'XP15X'})
    op['DATA'] = 'OP'
    op['N_EVENTS'] = 1
    
    # OB events
    h178g = load_sas_data(os.path.join(meps_data_path, "H178G.sas7bdat"))
    ob = h178g[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT15F', 'OBXP15X']].copy()
    ob = ob.rename(columns={'OBXP15X': 'XP15X'})
    ob['DATA'] = 'OB'
    ob['N_EVENTS'] = 1
    
    # HH events
    h178h = load_sas_data(os.path.join(meps_data_path, "H178H.sas7bdat"))
    hh = h178h[['DUPERSID', 'EVNTIDX', 'VARSTR', 'VARPSU', 'PERWT15F', 'HHXP15X']].copy()
    hh = hh.rename(columns={'HHXP15X': 'XP15X'})
    hh['DATA'] = 'HH'
    hh['N_EVENTS'] = 1
    
    # Stack event files
    stacked_events = pd.concat([rx, ip, er, op, ob, hh], ignore_index=True)
    stacked_events = stacked_events[['DATA', 'EVNTIDX', 'DUPERSID', 'N_EVENTS', 'XP15X', 'VARSTR', 'VARPSU', 'PERWT15F']]
    
    # Load condition-event link file
    print("Loading condition-event link file...")
    h178if1 = load_sas_data(os.path.join(meps_data_path, "H178IF1.sas7bdat"))
    
    # Load conditions file
    print("Loading conditions file...")
    h180 = load_sas_data(os.path.join(meps_data_path, "H180.sas7bdat"))
    
    # Merge conditions with CLNK
    cond_clink = pd.merge(
        h178if1[['DUPERSID', 'CONDIDX', 'EVNTIDX']],
        h180[['DUPERSID', 'CONDIDX', 'CCCODEX']],
        on=['DUPERSID', 'CONDIDX'],
        how='inner'
    )
    
    # Map CCS codes to collapsed conditions
    cond_clink['CONDITION'] = cond_clink['CCCODEX'].apply(get_condition_from_ccs)
    
    # De-duplicate by event ID and collapsed code
    cond_clink = cond_clink.drop_duplicates(subset=['DUPERSID', 'EVNTIDX', 'CONDITION'])
    
    # Merge events with linked conditions
    all_events = pd.merge(stacked_events, cond_clink[['DUPERSID', 'EVNTIDX', 'CONDITION']], 
                          on=['DUPERSID', 'EVNTIDX'], how='inner')
    all_events = all_events[(all_events['CONDITION'] != '') & (all_events['XP15X'] >= 0)]
    
    # Aggregate to person-level by condition
    all_pers = all_events.groupby(['DUPERSID', 'VARSTR', 'VARPSU', 'CONDITION']).agg({
        'XP15X': 'sum',
        'N_EVENTS': 'sum',
        'PERWT15F': 'first'
    }).reset_index()
    all_pers.columns = ['DUPERSID', 'VARSTR', 'VARPSU', 'CONDITION', 'PERS_XP', 'N_EVENTS', 'PERWT15F']
    all_pers['PERSON'] = 1
    
    # Calculate estimates
    print("\n" + "="*80)
    print("MEDICAL CONDITIONS EXPENDITURES, 2015")
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
            weight='PERWT15F'
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
    parser = argparse.ArgumentParser(description='MEPS Summary Tables - Medical Conditions 2015')
    parser.add_argument('--data-path', type=str, default='C:/MEPS',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
