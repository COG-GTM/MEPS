"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Prescribed Drugs, 2016:
 - Number of people with purchase
 - Total purchases
 - Total expenditures
 - By generic drug name (RXDRGNAM)

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


def main(meps_data_path: str = "C:/MEPS"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    print("MEPS-HC Data Tools: Prescribed Drugs, 2016")
    print("Purchases and expenditures by generic drug name")
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
    
    # Aggregate to person-level by drug name
    rx_pers = rx.groupby(['DUPERSID', 'VARSTR', 'VARPSU', 'PERWT16F', 'RXDRGNAM']).agg({
        'RXXP16X': 'sum',
        'RXRECIDX': 'count'
    }).reset_index()
    rx_pers.columns = ['DUPERSID', 'VARSTR', 'VARPSU', 'PERWT16F', 'RXDRGNAM', 'PERS_XP', 'N_PURCHASES']
    rx_pers['PERSON'] = 1
    
    # Calculate estimates
    print("\n" + "="*80)
    print("PRESCRIBED DRUG PURCHASES AND EXPENDITURES BY GENERIC DRUG NAME, 2016")
    print("="*80)
    
    # Get top 20 drugs by total expenditures
    drug_totals = rx_pers.groupby('RXDRGNAM').agg({
        'PERS_XP': lambda x: (x * rx_pers.loc[x.index, 'PERWT16F']).sum()
    }).reset_index()
    drug_totals.columns = ['RXDRGNAM', 'TOTAL_XP']
    top_drugs = drug_totals.nlargest(20, 'TOTAL_XP')['RXDRGNAM'].tolist()
    
    # By drug name (top 20)
    for drug_name in top_drugs:
        if pd.isna(drug_name) or drug_name == '':
            continue
        
        drug_data = rx_pers[rx_pers['RXDRGNAM'] == drug_name].copy()
        
        if len(drug_data) == 0:
            continue
        
        design = SurveyDesign(
            data=drug_data,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWT16F'
        )
        
        person_total = survey_total(design, 'PERSON')
        purchases_total = survey_total(design, 'N_PURCHASES')
        exp_total = survey_total(design, 'PERS_XP')
        
        print(f"\n{drug_name}")
        print("-" * 60)
        print(f"  Number of people with purchase: {person_total['Sum'].values[0]:,.0f} (SE: {person_total['StdDev'].values[0]:,.0f})")
        print(f"  Total purchases: {purchases_total['Sum'].values[0]:,.0f} (SE: {purchases_total['StdDev'].values[0]:,.0f})")
        print(f"  Total expenditures: ${exp_total['Sum'].values[0]:,.0f} (SE: ${exp_total['StdDev'].values[0]:,.0f})")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Summary Tables - Prescribed Drugs 2016')
    parser.add_argument('--data-path', type=str, default='C:/MEPS',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
