"""
Exercise 2a: Antipsychotic Purchases and Expenses, 2015

This program generates selected estimates for antipsychotic drug purchases and expenses:
    (1) Total expense for antipsychotics
    (2) Total number of purchases of antipsychotics
    (3) Total number of persons purchasing one or more antipsychotics
    (4) Average total, out of pocket, and third party payer expense
        for antipsychotics per person with an antipsychotic medicine purchase

Input files:
    - 2015 Full-Year Consolidated file (h181)
    - 2015 Prescribed Medicines file (h178a)

Python equivalent of: SAS/workshop_exercises/exercise_2a/Exercise2a.sas
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
    print("EXERCISE 2a: Antipsychotic Purchases and Expenses, 2015")
    print("=" * 80)
    
    # Load 2015 Prescribed Medicines file (HC-178A)
    pmed_file = data_dir / "h178a.sas7bdat"
    print(f"\nLoading prescribed medicines data from: {pmed_file}")
    
    pmed = load_sas_data(pmed_file)
    
    # 1) Identify antipsychotic drugs using therapeutic classification (TC) codes
    # Definition: TC1=242 AND TC1S1=251
    drug = pmed[(pmed['TC1'] == 242) & (pmed['TC1S1'] == 251)].copy()
    
    print(f"\nNumber of antipsychotic drug records: {len(drug):,}")
    
    # Sample dump for PMED records with antipsychotic drugs
    print("\nSample PMED records with antipsychotic drugs:")
    sample_cols = ['DUPERSID', 'RXRECIDX', 'LINKIDX', 'TC1', 'TC1S1', 'RXXP15X', 'RXSF15X']
    available_cols = [c for c in sample_cols if c in drug.columns]
    print(drug[available_cols].head(30).to_string())
    
    # 2) Sum data to person-level
    perdrug = drug.groupby('DUPERSID').agg(
        TOT=('RXXP15X', 'sum'),
        OOP=('RXSF15X', 'sum'),
        N_PHRCHASE=('RXXP15X', 'count')
    ).reset_index()
    
    # Calculate third party payer expense
    perdrug['THIRD_PAYER'] = perdrug['TOT'] - perdrug['OOP']
    
    print(f"\nNumber of persons with antipsychotic purchases: {len(perdrug):,}")
    print("\nSample person-level expenditures:")
    print(perdrug.head(30).to_string())
    
    # 3) Merge person-level expenditures to the FY PUF
    fyc_file = data_dir / "h181.sas7bdat"
    print(f"\nLoading full-year consolidated data from: {fyc_file}")
    
    fyc = load_sas_data(
        fyc_file,
        columns=['DUPERSID', 'VARSTR', 'VARPSU', 'PERWT15F']
    )
    
    # Merge
    fy = fyc.merge(
        perdrug[['DUPERSID', 'N_PHRCHASE', 'TOT', 'OOP', 'THIRD_PAYER']],
        on='DUPERSID',
        how='left'
    )
    
    # Create subpopulation flag
    fy['SUB'] = np.where(fy['TOT'].notna(), 1, 2)
    
    # Fill missing values for persons without antipsychotic purchases
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
    
    print("\nPersons with purchases (SUB=1):")
    print(f"  Count: {(fy['SUB'] == 1).sum():,}")
    print(f"  Total purchases: {fy.loc[fy['SUB'] == 1, 'N_PHRCHASE'].sum():,.0f}")
    
    # 4) Calculate estimates on expenditures and use
    print("\n" + "=" * 60)
    print("PERSON-LEVEL ESTIMATES ON EXPENDITURES AND USE")
    print("FOR ANTIPSYCHOTIC DRUGS, 2015")
    print("(Domain: Persons with 1+ antipsychotic drug purchases)")
    print("=" * 60)
    
    # Subset to persons with antipsychotic purchases
    fy_sub = fy[fy['SUB'] == 1].copy()
    
    design = SurveyDesign(
        data=fy_sub,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT15F'
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
    print(f"Population Size: {fy_sub['PERWT15F'].sum():,.0f}")
    
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
