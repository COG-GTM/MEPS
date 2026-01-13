"""
This program generates National Totals and Per-person Averages for Narcotic
analgesics and Narcotic analgesic combos care for the U.S. civilian
non-institutionalized population (2018), including:
  - Number of purchases (fills)
  - Total expenditures
  - Out-of-pocket payments
  - Third-party payments

Input files:
   - 2018 Prescribed medicines file
   - 2018 Full-year consolidated file
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, print_results


def main(meps_data_path: str = "C:/MEPS_Data"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    print("PERSON-LEVEL ESTIMATES ON EXPENDITURES AND USE FOR")
    print("NARCOTIC ANALGESICS OR NARCOTIC COMBOS, 2018")
    print("="*60)
    
    # Load prescribed medicines file and filter for narcotic analgesics
    print("\nLoading 2018 Prescribed Medicines file...")
    h206a = load_sas_data(os.path.join(meps_data_path, "H206A.sas7bdat"))
    
    # Keep specified variables and filter for narcotic analgesics (TC1S1_1 IN (60, 191))
    keep_vars = ['DUPERSID', 'RXRECIDX', 'LINKIDX', 'TC1S1_1', 'RXXP18X', 'RXSF18X']
    drug = h206a[[c for c in keep_vars if c in h206a.columns]].copy()
    drug = drug[drug['TC1S1_1'].isin([60, 191])]
    
    print(f"\nNumber of narcotic analgesic drug records: {len(drug)}")
    
    # A SAMPLE DUMP FOR PMED RECORDS
    print("\nA SAMPLE DUMP FOR PMED RECORDS WITH Narcotic analgesics or Narcotic analgesic combos, 2018:")
    print(drug.head(12))
    
    # SUM "RXXP18X and RXSF18X" DATA TO PERSON-LEVEL
    perdrug = drug.groupby('DUPERSID').agg({
        'RXXP18X': 'sum',
        'RXSF18X': 'sum',
        'RXRECIDX': 'count'
    }).reset_index()
    perdrug.columns = ['DUPERSID', 'TOT', 'OOP', 'N_PHRCHASE']
    
    print("\nA SAMPLE DUMP FOR PERSON-LEVEL EXPENDITURES FOR NARCOTIC ANALGESICS OR NARCOTIC ANALGESIC COMBOS:")
    print(perdrug.head(3))
    print(f"\nTotal purchases: {perdrug['N_PHRCHASE'].sum()}")
    
    # Create third party payer variable
    perdrug['THIRD_PAYER'] = perdrug['TOT'] - perdrug['OOP']
    
    # Sort and prepare for merge
    perdrug = perdrug.sort_values('DUPERSID')
    
    # Load and sort the full-year consolidated file
    print("\nLoading 2018 Full-Year Consolidated file...")
    h209 = load_sas_data(os.path.join(meps_data_path, "H209.sas7bdat"))
    h209 = h209[['DUPERSID', 'VARSTR', 'VARPSU', 'PERWT18F']].copy()
    h209 = h209.sort_values('DUPERSID')
    
    # Merge the person-level expenditures to the FY PUF
    fy = pd.merge(h209, perdrug[['DUPERSID', 'N_PHRCHASE', 'TOT', 'OOP', 'THIRD_PAYER']], 
                  on='DUPERSID', how='left')
    
    # Create SUBPOP flag
    fy['SUBPOP'] = np.where(fy['TOT'].notna() & (fy['TOT'] > 0), 1, 2)
    
    # Fill missing values with 0 for persons without purchases
    for col in ['N_PHRCHASE', 'TOT', 'OOP', 'THIRD_PAYER']:
        fy[col] = fy[col].fillna(0)
    
    # Labels
    subpop_labels = {1: 'OnePlusNarcoticEtc', 2: 'OTHERS'}
    
    print("\nSUBPOP distribution:")
    print(fy['SUBPOP'].map(subpop_labels).value_counts())
    
    # CALCULATE ESTIMATES ON USE AND EXPENDITURES
    print("\n" + "="*60)
    print("PERSON-LEVEL ESTIMATES ON EXPENDITURES AND USE FOR")
    print("NARCOTIC ANALGESICS or NARCOTIC COMBOS, 2018")
    print("="*60)
    
    # Filter to persons with purchases (SUBPOP = 1)
    fy_sub = fy[fy['SUBPOP'] == 1].copy()
    
    design = SurveyDesign(
        data=fy_sub,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT18F'
    )
    
    # Calculate means and totals
    vars_to_analyze = ['N_PHRCHASE', 'TOT', 'OOP', 'THIRD_PAYER']
    var_labels = {
        'N_PHRCHASE': '# OF PURCHASES PER PERSON',
        'TOT': 'TOTAL EXPENSES FOR NARCOTIC ETC',
        'OOP': 'OUT-OF-POCKET EXPENSES',
        'THIRD_PAYER': 'TOTAL EXPENSES MINUS OUT-OF-POCKET EXPENSES'
    }
    
    means = survey_mean(design, vars_to_analyze)
    totals = survey_total(design, vars_to_analyze)
    
    # Combine results
    results = pd.merge(
        means[['Variable', 'N', 'SumWgt', 'Mean', 'StdErr']],
        totals[['Variable', 'Sum', 'StdDev']],
        on='Variable'
    )
    
    print("\nDomain: OnePlusNarcoticEtc (persons with 1+ narcotic analgesic purchases)")
    print("-" * 100)
    
    # Print formatted results
    print(f"\n{'Variable Label':<50} {'N':>8} {'Pop Size':>12} {'Mean':>10} {'SE Mean':>10} {'Total':>15} {'SE Total':>12}")
    print("-" * 120)
    
    for _, row in results.iterrows():
        var = row['Variable']
        label = var_labels.get(var, var)
        print(f"{label:<50} {row['N']:>8,.0f} {row['SumWgt']:>12,.0f} {row['Mean']:>10,.1f} {row['StdErr']:>10,.4f} {row['Sum']:>15,.0f} {row['StdDev']:>12,.0f}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Exercise 2c - Narcotic Analgesics Purchases and Expenses 2018')
    parser.add_argument('--data-path', type=str, default='C:/MEPS_Data',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
