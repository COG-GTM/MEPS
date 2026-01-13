"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Prescribed Drugs, 2016:
 - Number of people with purchase
 - Total purchases
 - Total expenditures
 - By therapeutic class (TC1)

Input files:
 - H188A.ssp (2016 RX event file)
 - H192.ssp (2016 full-year consolidated)
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, print_results


TC1_LABELS = {
    -9: 'Not ascertained',
    -1: 'Inapplicable',
    1: 'Anti-infectives',
    2: 'Antineoplastics',
    3: 'Antiparasitics',
    4: 'Autonomic drugs',
    5: 'Blood formation/coagulation',
    6: 'Cardiovascular agents',
    7: 'Central nervous system agents',
    8: 'Contraceptives',
    9: 'Diagnostic agents',
    10: 'Electrolytic, caloric, water balance',
    11: 'Eye, ear, nose, throat preparations',
    12: 'Gastrointestinal agents',
    13: 'Genitourinary agents',
    14: 'Hormones/hormone modifiers',
    15: 'Immunologic agents',
    16: 'Miscellaneous agents',
    17: 'Nutritional products',
    18: 'Respiratory agents',
    19: 'Skin and mucous membrane agents',
    20: 'Unclassified/unknown',
    91: 'Radiopharmaceuticals',
    92: 'Metabolic bone disease agents',
    93: 'Smoking cessation agents',
    94: 'Alternative medicines',
    95: 'Psychotherapeutic agents',
    96: 'Anticoagulants',
    97: 'Antihyperglycemics',
    98: 'Antihyperlipidemics',
    99: 'Antihypertensives',
    242: 'Analgesics',
    249: 'Anticonvulsants',
    251: 'Antiemetics',
    253: 'Antiparkinson agents',
    358: 'Antidepressants',
    359: 'Antipsychotics',
    360: 'Anxiolytics, sedatives, and hypnotics',
    361: 'CNS stimulants',
}


def main(meps_data_path: str = "C:/MEPS"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    print("MEPS-HC Data Tools: Prescribed Drugs, 2016")
    print("Purchases and expenditures by therapeutic class")
    print("="*80)
    
    # Load RX event file
    print("\nLoading 2016 RX event file...")
    h188a = load_sas_data(os.path.join(meps_data_path, "H188A.sas7bdat"))
    
    # Load FYC file for survey design variables
    print("Loading 2016 Full-Year Consolidated file...")
    h192 = load_sas_data(os.path.join(meps_data_path, "H192.sas7bdat"))
    
    # Keep only needed variables from FYC
    fyc = h192[['DUPERSID', 'VARSTR', 'VARPSU', 'PERWT16F']].drop_duplicates()
    
    # Merge RX with FYC to get survey design variables
    rx = pd.merge(h188a, fyc, on='DUPERSID', how='left')
    
    # Aggregate to person-level by therapeutic class
    rx_pers = rx.groupby(['DUPERSID', 'VARSTR', 'VARPSU', 'PERWT16F', 'TC1']).agg({
        'RXXP16X': 'sum',
        'RXRECIDX': 'count'
    }).reset_index()
    rx_pers.columns = ['DUPERSID', 'VARSTR', 'VARPSU', 'PERWT16F', 'TC1', 'PERS_XP', 'N_PURCHASES']
    rx_pers['PERSON'] = 1
    
    # Calculate estimates
    print("\n" + "="*80)
    print("PRESCRIBED DRUG PURCHASES AND EXPENDITURES BY THERAPEUTIC CLASS, 2016")
    print("="*80)
    
    # By therapeutic class
    for tc1_val in sorted(rx_pers['TC1'].dropna().unique()):
        if tc1_val < 0:
            continue
        
        tc1_data = rx_pers[rx_pers['TC1'] == tc1_val].copy()
        
        if len(tc1_data) == 0:
            continue
        
        design = SurveyDesign(
            data=tc1_data,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWT16F'
        )
        
        person_total = survey_total(design, 'PERSON')
        purchases_total = survey_total(design, 'N_PURCHASES')
        exp_total = survey_total(design, 'PERS_XP')
        
        tc1_label = TC1_LABELS.get(int(tc1_val), f'TC1={int(tc1_val)}')
        print(f"\n{tc1_label}")
        print("-" * 60)
        print(f"  Number of people with purchase: {person_total['Sum'].values[0]:,.0f} (SE: {person_total['StdDev'].values[0]:,.0f})")
        print(f"  Total purchases: {purchases_total['Sum'].values[0]:,.0f} (SE: {purchases_total['StdDev'].values[0]:,.0f})")
        print(f"  Total expenditures: ${exp_total['Sum'].values[0]:,.0f} (SE: ${exp_total['StdDev'].values[0]:,.0f})")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Summary Tables - Prescribed Drugs by Therapeutic Class 2016')
    parser.add_argument('--data-path', type=str, default='C:/MEPS',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
