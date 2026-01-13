"""
Exercise 2b: Narcotic Analgesics Purchases and Expenses, 2016

This program generates selected estimates for narcotic analgesics or narcotic
analgesic combos purchases and expenses:
    (1) Total expense for narcotic analgesics
    (2) Total number of purchases
    (3) Total number of persons purchasing one or more
    (4) Average total, out of pocket, and third party payer expense
        per person with a purchase

Input files:
    - 2016 Full-Year Consolidated file (h192)
    - 2016 Prescribed Medicines file (h188a)

Python equivalent of: SAS/workshop_exercises/exercise_2b/Exercise2b.sas
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
    print("2018 AHRQ MEPS DATA USERS WORKSHOP")
    print("EXERCISE 2b: Narcotic Analgesics or Narcotic Analgesic Combos, 2016")
    print("=" * 80)
    
    # Load 2016 Prescribed Medicines file (HC-188A)
    pmed_file = data_dir / "h188a.sas7bdat"
    print(f"\nLoading prescribed medicines data from: {pmed_file}")
    
    pmed = load_sas_data(pmed_file)
    
    # 1) Identify narcotic analgesics using therapeutic classification (TC) codes
    # Definition: TC1S1_1 IN (60, 191)
    drug = pmed[pmed['TC1S1_1'].isin([60, 191])].copy()
    
    print(f"\nNumber of narcotic analgesic drug records: {len(drug):,}")
    
    # Sample dump
    print("\nSample PMED records with narcotic analgesics:")
    sample_cols = ['DUPERSID', 'RXRECIDX', 'LINKIDX', 'TC1S1_1', 'RXXP16X', 'RXSF16X']
    available_cols = [c for c in sample_cols if c in drug.columns]
    print(drug[available_cols].head(30).to_string())
    
    # 2) Sum data to person-level
    perdrug = drug.groupby('DUPERSID').agg(
        TOT=('RXXP16X', 'sum'),
        OOP=('RXSF16X', 'sum'),
        N_PHRCHASE=('RXXP16X', 'count')
    ).reset_index()
    
    # Calculate third party payer expense
    perdrug['THIRD_PAYER'] = perdrug['TOT'] - perdrug['OOP']
    
    print(f"\nNumber of persons with narcotic analgesic purchases: {len(perdrug):,}")
    print("\nSample person-level expenditures:")
    print(perdrug.head(30).to_string())
    
    # 3) Merge person-level expenditures to the FY PUF
    fyc_file = data_dir / "h192.sas7bdat"
    print(f"\nLoading full-year consolidated data from: {fyc_file}")
    
    fyc = load_sas_data(
        fyc_file,
        columns=['DUPERSID', 'VARSTR', 'VARPSU', 'PERWT16F']
    )
    
    # Merge
    fy = fyc.merge(
        perdrug[['DUPERSID', 'N_PHRCHASE', 'TOT', 'OOP', 'THIRD_PAYER']],
        on='DUPERSID',
        how='left'
    )
    
    # Create subpopulation flag
    fy['SUB'] = np.where(fy['TOT'].notna(), 1, 2)
    
    # Fill missing values
    fy['N_PHRCHASE'] = fy['N_PHRCHASE'].fillna(0)
    fy['TOT'] = fy['TOT'].fillna(0)
    fy['OOP'] = fy['OOP'].fillna(0)
    fy['THIRD_PAYER'] = fy['THIRD_PAYER'].fillna(0)
    
    # Supporting crosstabs
    print("\n" + "-" * 60)
    print("Supporting crosstabs for new variables")
    print("-" * 60)
    
    print("\nSUB (Population flag):")
    print(fy['SUB'].value_counts().sort_index())
    
    # 4) Calculate estimates on use and expenditures
    print("\n" + "=" * 60)
    print("PERSON-LEVEL ESTIMATES ON EXPENDITURES AND USE")
    print("FOR NARCOTIC ANALGESICS OR NARCOTIC ANALGESIC COMBOS, 2016")
    print("(Domain: Persons with 1+ purchases)")
    print("=" * 60)
    
    # Subset to persons with purchases
    fy_sub = fy[fy['SUB'] == 1].copy()
    
    design = SurveyDesign(
        data=fy_sub,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT16F'
    )
    
    # Calculate estimates
    variables = ['TOT', 'N_PHRCHASE', 'OOP', 'THIRD_PAYER']
    labels = [
        'Total Expense ($)',
        'Number of Purchases',
        'Out-of-Pocket Expense ($)',
        'Third Party Payer Expense ($)'
    ]
    
    print(f"\nN (unweighted): {len(fy_sub):,}")
    print(f"Population Size: {fy_sub['PERWT16F'].sum():,.0f}")
    
    for var, label in zip(variables, labels):
        mean_result = survey_mean(design, var)
        total_result = survey_total(design, var)
        
        print(f"\n{label}:")
        print(f"  Mean: {mean_result['mean'].values[0]:,.1f}")
        print(f"  SE of Mean: {mean_result['se'].values[0]:.4f}")
        print(f"  Total: {total_result['total'].values[0]:,.0f}")
        print(f"  SE of Total: {total_result['se'].values[0]:,.0f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
