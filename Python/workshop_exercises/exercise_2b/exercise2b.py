"""
PURPOSE: THIS PROGRAM GENERATES SELECTED ESTIMATES FOR A 2016 VERSION OF THE 
         Purchases and Expenses for Narcotic analgesics or Narcotic analgesic combos

    (1) FIGURE 1: TOTAL EXPENSE FOR Narcotic analgesics or Narcotic analgesic combos
    (2) FIGURE 2: TOTAL NUMBER OF PURCHASES OF Narcotic analgesics or Narcotic analgesic combos
    (3) FIGURE 3: TOTAL NUMBER OF PERSONS PURCHASING ONE OR MORE Narcotic analgesics or Narcotic analgesic combos
    (4) FIGURE 4: AVERAGE TOTAL, OUT OF POCKET, AND THIRD PARTY PAYER EXPENSE
                  FOR Narcotic analgesics or Narcotic analgesic combos PER PERSON WITH A PURCHASE

INPUT FILES:  (1) H192.SAS7BDAT (2016 FULL-YEAR CONSOLIDATED PUF)
              (2) H188A.SAS7BDAT (2016 PRESCRIBED MEDICINES PUF)
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, print_results


def main(meps_data_path: str = "C:/MEPS/SAS/DATA"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    print("2018 AHRQ MEPS DATA USERS WORKSHOP")
    print("EXERCISE2.SAS: Narcotic analgesics or Narcotic analgesic combos, 2016")
    print("="*60)
    
    # 1) IDENTIFY Narcotic analgesics or Narcotic analgesic combos USING THERAPEUTIC CLASSIFICATION (TC) CODES
    print("\nLoading 2016 Prescribed Medicines file...")
    h188a = load_sas_data(os.path.join(meps_data_path, "H188A.sas7bdat"))
    
    # Filter for narcotic analgesics or narcotic analgesic combos (TC1S1_1 IN (60, 191))
    drug = h188a[h188a['TC1S1_1'].isin([60, 191])].copy()
    
    print(f"\nNumber of narcotic analgesic drug records: {len(drug)}")
    
    # A SAMPLE DUMP FOR PMED RECORDS
    print("\nA SAMPLE DUMP FOR PMED RECORDS WITH Narcotic analgesics or Narcotic analgesic combos:")
    sample_cols = ['DUPERSID', 'RXRECIDX', 'LINKIDX', 'TC1S1_1', 'RXXP16X', 'RXSF16X']
    sample_cols = [c for c in sample_cols if c in drug.columns]
    print(drug[sample_cols].head(30))
    
    # 2) SUM DATA TO PERSON-LEVEL
    perdrug = drug.groupby('DUPERSID').agg({
        'RXXP16X': 'sum',
        'RXSF16X': 'sum',
        'RXRECIDX': 'count'
    }).reset_index()
    perdrug.columns = ['DUPERSID', 'TOT', 'OOP', 'N_PHRCHASE']
    
    # Calculate third party payer
    perdrug['THIRD_PAYER'] = perdrug['TOT'] - perdrug['OOP']
    
    print("\nA SAMPLE DUMP FOR PERSON-LEVEL EXPENDITURES:")
    print(perdrug.head(30))
    
    # 3) MERGE THE PERSON-LEVEL EXPENDITURES TO THE FY PUF
    print("\nLoading 2016 Full-Year Consolidated file...")
    h192 = load_sas_data(os.path.join(meps_data_path, "H192.sas7bdat"))
    h192 = h192[['DUPERSID', 'VARSTR', 'VARPSU', 'PERWT16F']].copy()
    
    # Merge
    fy = pd.merge(h192, perdrug, on='DUPERSID', how='left')
    
    # Create SUB flag
    fy['SUB'] = np.where(fy['TOT'].notna(), 1, 2)
    
    # Fill missing values with 0 for persons without purchases
    for col in ['N_PHRCHASE', 'TOT', 'OOP', 'THIRD_PAYER']:
        fy[col] = fy[col].fillna(0)
    
    # SUPPORTING CROSSTABS FOR NEW VARIABLES
    print("\nSUPPORTING CROSSTABS FOR NEW VARIABLES:")
    print("\nSUB distribution:")
    print(fy['SUB'].value_counts())
    
    # 4) CALCULATE ESTIMATES ON USE AND EXPENDITURES
    print("\n" + "="*60)
    print("PERSON-LEVEL ESTIMATES ON EXPENDITURES AND USE FOR")
    print("Narcotic analgesics or Narcotic analgesic combos, 2016")
    print("="*60)
    
    # Filter to persons with purchases (SUB = 1)
    fy_sub = fy[fy['SUB'] == 1].copy()
    
    design = SurveyDesign(
        data=fy_sub,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT16F'
    )
    
    # Calculate means and totals
    vars_to_analyze = ['TOT', 'N_PHRCHASE', 'OOP', 'THIRD_PAYER']
    
    means = survey_mean(design, vars_to_analyze)
    totals = survey_total(design, vars_to_analyze)
    
    # Combine results
    results = pd.merge(
        means[['Variable', 'N', 'SumWgt', 'Mean', 'StdErr']],
        totals[['Variable', 'Sum', 'StdDev']],
        on='Variable'
    )
    
    print("\nSUBSET THE ESTIMATES FOR PERSONS ONLY WITH 1+ Narcotic analgesics or Narcotic analgesic combos:")
    print("-" * 80)
    
    # Print formatted results
    print(f"\n{'Variable':<15} {'N':>10} {'Population':>15} {'Mean':>12} {'SE of Mean':>12} {'Total':>18} {'SE of Total':>15}")
    print("-" * 100)
    
    for _, row in results.iterrows():
        print(f"{row['Variable']:<15} {row['N']:>10,.0f} {row['SumWgt']:>15,.0f} {row['Mean']:>12,.1f} {row['StdErr']:>12,.4f} {row['Sum']:>18,.0f} {row['StdDev']:>15,.0f}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Exercise 2b - Narcotic Analgesics Purchases and Expenses 2016')
    parser.add_argument('--data-path', type=str, default='C:/MEPS/SAS/DATA',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
