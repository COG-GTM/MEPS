"""
PURPOSE: THIS PROGRAM GENERATES SELECTED ESTIMATES FOR A 2015 VERSION OF THE
         MEPS STATISTICS BRIEF # 275: "Trends in Antipsychotics Purchases and Expenses for the U.S. Civilian
                                       Noninstitutionalized Population, 1997 and 2007"

    (1) FIGURE 1: TOTAL EXPENSE FOR ANTIPSYCHOTICS
    (2) FIGURE 2: TOTAL NUMBER OF PURCHASES OF ANTIPSYCHOTICS
    (3) FIGURE 3: TOTAL NUMBER OF PERSONS PURCHASING ONE OR MORE ANTIPSYCHOTICS
    (4) FIGURE 4: AVERAGE TOTAL, OUT OF POCKET, AND THIRD PARTY PAYER EXPENSE
                  FOR ANTIPSYCHOTICS PER PERSON WITH AN ANTIPSYCHOTIC MEDICINE PURCHASE

INPUT FILES:  (1) H181.SAS7BDAT (2015 FULL-YEAR CONSOLIDATED PUF)
              (2) H178A.SAS7BDAT (2015 PRESCRIBED MEDICINES PUF)
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
    print("EXERCISE2.SAS: Antipsychotics Purchases and Expenses, 2015")
    print("="*60)
    
    # 1) IDENTIFY ANTIPSYCHOTIC DRUGS USING THERAPEUTIC CLASSIFICATION (TC) CODES
    print("\nLoading 2015 Prescribed Medicines file...")
    h178a = load_sas_data(os.path.join(meps_data_path, "H178A.sas7bdat"))
    
    # Filter for antipsychotic drugs (TC1=242 AND TC1S1=251)
    drug = h178a[(h178a['TC1'] == 242) & (h178a['TC1S1'] == 251)].copy()
    
    print(f"\nNumber of antipsychotic drug records: {len(drug)}")
    
    # A SAMPLE DUMP FOR PMED RECORDS WITH ANTIPSYCHOTIC DRUGS
    print("\nA SAMPLE DUMP FOR PMED RECORDS WITH ANTIPSYCHOTIC DRUGS:")
    sample_cols = ['DUPERSID', 'RXRECIDX', 'LINKIDX', 'TC1', 'TC1S1', 'RXXP15X', 'RXSF15X']
    sample_cols = [c for c in sample_cols if c in drug.columns]
    print(drug[sample_cols].head(30))
    
    # 2) SUM DATA TO PERSON-LEVEL
    perdrug = drug.groupby('DUPERSID').agg({
        'RXXP15X': 'sum',
        'RXSF15X': 'sum',
        'RXRECIDX': 'count'
    }).reset_index()
    perdrug.columns = ['DUPERSID', 'TOT', 'OOP', 'N_PHRCHASE']
    
    # Calculate third party payer
    perdrug['THIRD_PAYER'] = perdrug['TOT'] - perdrug['OOP']
    
    print("\nA SAMPLE DUMP FOR PERSON-LEVEL EXPENDITURES FOR ANTIPSYCHOTIC DRUGS:")
    print(perdrug.head(30))
    
    # 3) MERGE THE PERSON-LEVEL EXPENDITURES TO THE FY PUF
    print("\nLoading 2015 Full-Year Consolidated file...")
    h181 = load_sas_data(os.path.join(meps_data_path, "H181.sas7bdat"))
    h181 = h181[['DUPERSID', 'VARSTR', 'VARPSU', 'PERWT15F']].copy()
    
    # Merge
    fy = pd.merge(h181, perdrug, on='DUPERSID', how='left')
    
    # Create SUB flag
    fy['SUB'] = np.where(fy['TOT'].notna(), 1, 2)
    
    # Fill missing values with 0 for persons without antipsychotic purchases
    for col in ['N_PHRCHASE', 'TOT', 'OOP', 'THIRD_PAYER']:
        fy[col] = fy[col].fillna(0)
    
    # SUPPORTING CROSSTABS FOR NEW VARIABLES
    print("\nSUPPORTING CROSSTABS FOR NEW VARIABLES:")
    print("\nSUB distribution:")
    print(fy['SUB'].value_counts())
    
    print("\nCrosstab of SUB * N_PHRCHASE (>0 vs 0):")
    fy['N_PHRCHASE_cat'] = np.where(fy['N_PHRCHASE'] > 0, '>0', '0')
    print(pd.crosstab(fy['SUB'], fy['N_PHRCHASE_cat']))
    
    # 4) CALCULATE ESTIMATES ON EXPENDITURES AND USE
    print("\n" + "="*60)
    print("PERSON-LEVEL ESTIMATES ON EXPENDITURES AND USE FOR ANTIPSYCHOTIC DRUGS, 2015")
    print("="*60)
    
    # Filter to persons with antipsychotic purchases (SUB = 1)
    fy_sub = fy[fy['SUB'] == 1].copy()
    
    design = SurveyDesign(
        data=fy_sub,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT15F'
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
    
    print("\nEstimates for persons with 1+ antipsychotic drug purchases:")
    print("-" * 80)
    
    for _, row in results.iterrows():
        var = row['Variable']
        print(f"\n{var}:")
        print(f"  N: {row['N']:,.0f}")
        print(f"  Population Size: {row['SumWgt']:,.0f}")
        print(f"  Mean: {row['Mean']:,.2f}")
        print(f"  SE of Mean: {row['StdErr']:,.4f}")
        print(f"  Total: {row['Sum']:,.0f}")
        print(f"  SE of Total: {row['StdDev']:,.0f}")
    
    # Summary statistics
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    tot_row = results[results['Variable'] == 'TOT'].iloc[0]
    n_row = results[results['Variable'] == 'N_PHRCHASE'].iloc[0]
    
    print(f"\nFIGURE 1: Total Expense for Antipsychotics: ${tot_row['Sum']:,.0f}")
    print(f"FIGURE 2: Total Number of Purchases: {n_row['Sum']:,.0f}")
    print(f"FIGURE 3: Total Number of Persons with 1+ Purchase: {tot_row['SumWgt']:,.0f}")
    print(f"FIGURE 4: Average Total Expense per Person: ${tot_row['Mean']:,.2f}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Exercise 2a - Antipsychotics Purchases and Expenses 2015')
    parser.add_argument('--data-path', type=str, default='C:/MEPS/SAS/DATA',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
