"""
Exercise 2c: Narcotic Analgesics Purchases and Expenses, 2018

This program generates National Totals and Per-person Averages for Narcotic
analgesics and Narcotic analgesic combos care for the U.S. civilian
non-institutionalized population (2018), including:
    - Number of purchases (fills)
    - Total expenditures
    - Out-of-pocket payments
    - Third-party payments

Input files:
    - 2018 Prescribed medicines file (h206a)
    - 2018 Full-year consolidated file (h209)

Python equivalent of: SAS/workshop_exercises/exercise_2c/Exercise2c.sas
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
    print("PERSON-LEVEL ESTIMATES ON EXPENDITURES AND USE")
    print("FOR NARCOTIC ANALGESICS OR NARCOTIC COMBOS, 2018")
    print("=" * 80)
    
    # Load 2018 Prescribed Medicines file (HC-206A)
    pmed_file = data_dir / "h206a.sas7bdat"
    print(f"\nLoading prescribed medicines data from: {pmed_file}")
    
    # Keep specified variables and restrict to narcotic analgesics
    pmed = load_sas_data(pmed_file)
    
    # Filter to narcotic analgesics or narcotic analgesic combos
    # TC1S1_1 IN (60, 191)
    drug = pmed[pmed['TC1S1_1'].isin([60, 191])].copy()
    
    print(f"\nNumber of narcotic analgesic drug records: {len(drug):,}")
    
    # Sample dump
    print("\nSample PMED records with narcotic analgesics (2018):")
    sample_cols = ['DUPERSID', 'RXRECIDX', 'LINKIDX', 'TC1S1_1', 'RXXP18X', 'RXSF18X']
    available_cols = [c for c in sample_cols if c in drug.columns]
    print(drug[available_cols].head(12).to_string(index=False))
    
    # Sum RXXP18X and RXSF18X to person-level
    perdrug = drug.groupby('DUPERSID').agg(
        TOT=('RXXP18X', 'sum'),
        OOP=('RXSF18X', 'sum'),
        N_PHRCHASE=('RXXP18X', 'count')
    ).reset_index()
    
    # Create third party payer variable
    perdrug['THIRD_PAYER'] = perdrug['TOT'] - perdrug['OOP']
    
    print(f"\nNumber of persons with narcotic analgesic purchases: {len(perdrug):,}")
    print(f"Total purchases: {perdrug['N_PHRCHASE'].sum():,}")
    
    print("\nSample person-level expenditures:")
    print(perdrug.head(3).to_string())
    
    # Sort and load FY consolidated file
    fyc_file = data_dir / "h209.sas7bdat"
    print(f"\nLoading full-year consolidated data from: {fyc_file}")
    
    fyc = load_sas_data(
        fyc_file,
        columns=['DUPERSID', 'VARSTR', 'VARPSU', 'PERWT18F']
    )
    
    # Merge person-level expenditures to FY PUF
    fy = fyc.merge(
        perdrug[['DUPERSID', 'N_PHRCHASE', 'TOT', 'OOP', 'THIRD_PAYER']],
        on='DUPERSID',
        how='left'
    )
    
    # Create subpopulation flag
    # SUBPOP = 1 for persons with 1+ narcotic analgesics
    # SUBPOP = 2 for others
    fy['SUBPOP'] = np.where(fy['TOT'].notna() & (fy['TOT'] > 0), 1, 2)
    
    # Fill missing values for persons without purchases
    fy['N_PHRCHASE'] = fy['N_PHRCHASE'].fillna(0)
    fy['TOT'] = fy['TOT'].fillna(0)
    fy['OOP'] = fy['OOP'].fillna(0)
    fy['THIRD_PAYER'] = fy['THIRD_PAYER'].fillna(0)
    
    # Calculate estimates on use and expenditures
    print("\n" + "=" * 60)
    print("ESTIMATES FOR PERSONS WITH 1+ NARCOTIC ANALGESICS")
    print("=" * 60)
    
    # Subset to persons with purchases (SUBPOP = 1)
    fy_sub = fy[fy['SUBPOP'] == 1].copy()
    
    design = SurveyDesign(
        data=fy_sub,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT18F'
    )
    
    # Calculate estimates
    variables = ['N_PHRCHASE', 'TOT', 'OOP', 'THIRD_PAYER']
    labels = [
        '# of Purchases per Person',
        'Total Expenses for Narcotic etc',
        'Out-of-Pocket Expenses',
        'Total Expenses minus Out-of-Pocket'
    ]
    
    print(f"\nN (unweighted): {len(fy_sub):,}")
    print(f"Population Size: {fy_sub['PERWT18F'].sum():,.0f}")
    
    for var, label in zip(variables, labels):
        mean_result = survey_mean(design, var)
        total_result = survey_total(design, var)
        
        print(f"\n{label}:")
        print(f"  Mean: {mean_result['mean'].values[0]:,.2f}")
        print(f"  SE of Mean: {mean_result['se'].values[0]:.4f}")
        print(f"  Total: {total_result['total'].values[0]:,.0f}")
        print(f"  SE of Total: {total_result['se'].values[0]:,.0f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
