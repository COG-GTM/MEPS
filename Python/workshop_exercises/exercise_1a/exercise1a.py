"""
DESCRIPTION: THIS PROGRAM GENERATES THE FOLLOWING ESTIMATES ON NATIONAL HEALTH CARE EXPENSES, 2016:

           (1) OVERALL EXPENSES
           (2) PERCENTAGE OF PERSONS WITH AN EXPENSE
           (3) MEAN EXPENSE PER PERSON WITH AN EXPENSE

INPUT FILE: H192.SAS7BDAT (2016 FULL-YEAR FILE)
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meps_utils import (load_sas_data, SurveyDesign, survey_mean, survey_total, 
                        print_results, get_age_from_multiple_vars)


def main(meps_data_path: str = "C:/MEPS/SAS/DATA"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    print("2018 AHRQ MEPS DATA USERS WORKSHOP")
    print("EXERCISE1.SAS: NATIONAL HEALTH CARE EXPENSES, 2016")
    print("="*60)
    
    # Read in data from 2016 consolidated data file (HC-192)
    print("\nLoading 2016 Full-Year Consolidated file...")
    puf192 = load_sas_data(os.path.join(meps_data_path, "H192.sas7bdat"))
    
    # Keep only needed variables
    keep_vars = ['TOTEXP16', 'AGE16X', 'AGE42X', 'AGE31X', 'VARSTR', 'VARPSU', 'PERWT16F']
    puf192 = puf192[[c for c in keep_vars if c in puf192.columns]].copy()
    
    # Create TOTAL variable
    puf192['TOTAL'] = puf192['TOTEXP16']
    
    # Create flag (1/0) variables for persons with an expense
    puf192['X_ANYSVCE'] = (puf192['TOTAL'] > 0).astype(int)
    
    # Create a summary variable from end of year, 42, and 31 variables
    puf192['AGE'] = get_age_from_multiple_vars(puf192, ['AGE16X', 'AGE42X', 'AGE31X'])
    
    # Create age category
    puf192['AGECAT'] = np.where(puf192['AGE'] <= 64, 1, 2)
    puf192['AGECAT'] = np.where(puf192['AGE'].isna(), np.nan, puf192['AGECAT'])
    
    # Age category labels
    agecat_labels = {1: '0-64', 2: '65+'}
    
    # Supporting crosstabs for the flag variables
    print("\nSupporting crosstabs for the flag variables:")
    print("\nX_ANYSVCE * TOTAL crosstab:")
    puf192['TOTAL_cat'] = np.where(puf192['TOTAL'] == 0, '$0', '>$0')
    print(pd.crosstab(puf192['X_ANYSVCE'], puf192['TOTAL_cat']))
    
    print("\nAGECAT * AGE crosstab:")
    puf192['AGE_cat'] = np.where(puf192['AGE'] <= 64, '0-64', '65+')
    print(pd.crosstab(puf192['AGECAT'].map(agecat_labels), puf192['AGE_cat']))
    
    # Create survey design
    design = SurveyDesign(
        data=puf192,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT16F'
    )
    
    # PERCENTAGE OF PERSONS WITH AN EXPENSE & OVERALL EXPENSES
    print("\n" + "="*60)
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE & OVERALL EXPENSES")
    print("="*60)
    
    overall_results = survey_mean(design, ['X_ANYSVCE', 'TOTAL'])
    overall_totals = survey_total(design, ['X_ANYSVCE', 'TOTAL'])
    
    # Combine results
    combined = pd.merge(
        overall_results[['Variable', 'N', 'SumWgt', 'Mean', 'StdErr']],
        overall_totals[['Variable', 'Sum', 'StdDev']],
        on='Variable'
    )
    
    print("\nPERCENTAGE OF PERSONS WITH AN EXPENSE:")
    pct_result = combined[combined['Variable'] == 'X_ANYSVCE'].copy()
    print(f"  N: {pct_result['N'].values[0]:,.0f}")
    print(f"  Population Size: {pct_result['SumWgt'].values[0]:,.0f}")
    print(f"  Proportion: {pct_result['Mean'].values[0]:.4f}")
    print(f"  SE of Proportion: {pct_result['StdErr'].values[0]:.5f}")
    print(f"  Persons with Any Expense: {pct_result['Sum'].values[0]:,.0f}")
    print(f"  SE of Number Persons with Any Expense: {pct_result['StdDev'].values[0]:,.0f}")
    
    print("\nOVERALL EXPENSES:")
    exp_result = combined[combined['Variable'] == 'TOTAL'].copy()
    print(f"  N: {exp_result['N'].values[0]:,.0f}")
    print(f"  Population Size: {exp_result['SumWgt'].values[0]:,.0f}")
    print(f"  Mean($): {exp_result['Mean'].values[0]:,.2f}")
    print(f"  SE of Mean($): {exp_result['StdErr'].values[0]:.5f}")
    print(f"  Total Expense ($): {exp_result['Sum'].values[0]:,.0f}")
    print(f"  SE of Total Expense($): {exp_result['StdDev'].values[0]:,.0f}")
    
    # MEAN EXPENSE PER PERSON WITH AN EXPENSE, FOR OVERALL, AGE 0-64, AND AGE 65+
    print("\n" + "="*60)
    print("MEAN EXPENSE PER PERSON WITH AN EXPENSE, FOR OVERALL, AGE 0-64, AND AGE 65+")
    print("="*60)
    
    # Filter to persons with expense
    puf192_expense = puf192[puf192['X_ANYSVCE'] == 1].copy()
    
    design_expense = SurveyDesign(
        data=puf192_expense,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT16F'
    )
    
    # Overall mean for persons with expense
    overall_expense = survey_mean(design_expense, 'TOTAL')
    overall_expense_total = survey_total(design_expense, 'TOTAL')
    
    print("\nOverall (persons with expense):")
    print(f"  N: {overall_expense['N'].values[0]:,.0f}")
    print(f"  Population Size: {overall_expense['SumWgt'].values[0]:,.0f}")
    print(f"  Mean($): {overall_expense['Mean'].values[0]:,.1f}")
    print(f"  SE of Mean($): {overall_expense['StdErr'].values[0]:.4f}")
    print(f"  Total Expense ($): {overall_expense_total['Sum'].values[0]:,.0f}")
    print(f"  SE of Total Expense($): {overall_expense_total['StdDev'].values[0]:,.0f}")
    
    # By age category
    for agecat_val, agecat_label in agecat_labels.items():
        puf192_age = puf192_expense[puf192_expense['AGECAT'] == agecat_val].copy()
        
        if len(puf192_age) == 0:
            continue
            
        design_age = SurveyDesign(
            data=puf192_age,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWT16F'
        )
        
        age_expense = survey_mean(design_age, 'TOTAL')
        age_expense_total = survey_total(design_age, 'TOTAL')
        
        print(f"\nAge Group: {agecat_label}")
        print(f"  N: {age_expense['N'].values[0]:,.0f}")
        print(f"  Population Size: {age_expense['SumWgt'].values[0]:,.0f}")
        print(f"  Mean($): {age_expense['Mean'].values[0]:,.1f}")
        print(f"  SE of Mean($): {age_expense['StdErr'].values[0]:.4f}")
        print(f"  Total Expense ($): {age_expense_total['Sum'].values[0]:,.0f}")
        print(f"  SE of Total Expense($): {age_expense_total['StdDev'].values[0]:,.0f}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Exercise 1a - National Health Care Expenses 2016')
    parser.add_argument('--data-path', type=str, default='C:/MEPS/SAS/DATA',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
