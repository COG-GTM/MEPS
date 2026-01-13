"""
DESCRIPTION: THIS PROGRAM GENERATES THE FOLLOWING ESTIMATES ON NATIONAL HEALTH CARE EXPENSES BY TYPE OF SERVICE, 2015:

           (1) PERCENTAGE DISTRIBUTION OF EXPENSES BY TYPE OF SERVICE
           (2) PERCENTAGE OF PERSONS WITH AN EXPENSE, BY TYPE OF SERVICE
           (3) MEAN EXPENSE PER PERSON WITH AN EXPENSE, BY TYPE OF SERVICE

          DEFINED SERVICE CATEGORIES ARE:
             HOSPITAL INPATIENT
             AMBULATORY SERVICE: OFFICE-BASED & HOSPITAL OUTPATIENT VISITS
             PRESCRIBED MEDICINES
             DENTAL VISITS
             EMERGENCY ROOM
             HOME HEALTH CARE (AGENCY & NON-AGENCY) AND OTHER

         NOTE: EXPENSES INCLUDE BOTH FACILITY AND PHYSICIAN EXPENSES.

INPUT FILE: H181.SAS7BDAT (2015 FULL-YEAR FILE)
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
    print("EXERCISE1.SAS: NATIONAL HEALTH CARE EXPENSES, 2015")
    print("="*60)
    
    # Read in data from 2015 consolidated data file (HC-181)
    print("\nLoading 2015 Full-Year Consolidated file...")
    puf181 = load_sas_data(os.path.join(meps_data_path, "H181.sas7bdat"))
    
    # Keep only needed variables
    keep_vars = ['TOTEXP15', 'IPDEXP15', 'IPFEXP15', 'OBVEXP15', 'RXEXP15',
                 'OPDEXP15', 'OPFEXP15', 'DVTEXP15', 'ERDEXP15', 'ERFEXP15',
                 'HHAEXP15', 'HHNEXP15', 'OTHEXP15', 'VISEXP15', 'AGE15X', 'AGE42X', 'AGE31X',
                 'VARSTR', 'VARPSU', 'PERWT15F']
    puf181 = puf181[[c for c in keep_vars if c in puf181.columns]].copy()
    
    # Define expenditure variables by type of service
    puf181['TOTAL'] = puf181['TOTEXP15']
    puf181['HOSPITAL_INPATIENT'] = puf181['IPDEXP15'].fillna(0) + puf181['IPFEXP15'].fillna(0)
    puf181['AMBULATORY'] = (puf181['OBVEXP15'].fillna(0) + puf181['OPDEXP15'].fillna(0) + 
                           puf181['OPFEXP15'].fillna(0) + puf181['ERDEXP15'].fillna(0) + 
                           puf181['ERFEXP15'].fillna(0))
    puf181['PRESCRIBED_MEDICINES'] = puf181['RXEXP15'].fillna(0)
    puf181['DENTAL'] = puf181['DVTEXP15'].fillna(0)
    puf181['HOME_HEALTH_OTHER'] = (puf181['HHAEXP15'].fillna(0) + puf181['HHNEXP15'].fillna(0) + 
                                   puf181['OTHEXP15'].fillna(0) + puf181['VISEXP15'].fillna(0))
    
    # QC CHECK IF THE SUM OF EXPENDITURES BY TYPE OF SERVICE IS EQUAL TO TOTAL
    puf181['DIFF'] = (puf181['TOTAL'] - puf181['HOSPITAL_INPATIENT'] - puf181['AMBULATORY'] - 
                      puf181['PRESCRIBED_MEDICINES'] - puf181['DENTAL'] - puf181['HOME_HEALTH_OTHER'])
    
    # Create flag (1/0) variables for persons with an expense, by type of service
    expense_vars = ['TOTAL', 'HOSPITAL_INPATIENT', 'AMBULATORY', 'PRESCRIBED_MEDICINES', 
                    'DENTAL', 'HOME_HEALTH_OTHER']
    flag_vars = ['X_ANYSVCE', 'X_HOSPITAL_INPATIENT', 'X_AMBULATORY', 'X_PRESCRIBED_MEDICINES',
                 'X_DENTAL', 'X_HOME_HEALTH_OTHER']
    
    for exp_var, flag_var in zip(expense_vars, flag_vars):
        puf181[flag_var] = (puf181[exp_var] > 0).astype(int)
    
    # Create a summary variable from end of year, 42, and 31 variables
    puf181['AGE'] = get_age_from_multiple_vars(puf181, ['AGE15X', 'AGE42X', 'AGE31X'])
    
    # Create age category
    puf181['AGECAT'] = np.where(puf181['AGE'] <= 64, 1, 2)
    puf181['AGECAT'] = np.where(puf181['AGE'].isna(), np.nan, puf181['AGECAT'])
    
    # Age category labels
    agecat_labels = {1: '0-64', 2: '65+'}
    
    # Supporting crosstabs for the flag variables
    print("\nSupporting crosstabs for the flag variables:")
    print("\nDIFF distribution (should be 0 for all):")
    print(puf181['DIFF'].value_counts().head())
    
    # Create survey design
    design = SurveyDesign(
        data=puf181,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT15F'
    )
    
    # PERCENTAGE DISTRIBUTION OF EXPENSES BY TYPE OF SERVICE
    print("\n" + "="*60)
    print("PERCENTAGE DISTRIBUTION OF EXPENSES BY TYPE OF SERVICE")
    print("(STAT BRIEF #491 FIGURE 1)")
    print("="*60)
    
    service_vars = ['HOSPITAL_INPATIENT', 'AMBULATORY', 'PRESCRIBED_MEDICINES', 
                    'DENTAL', 'HOME_HEALTH_OTHER', 'TOTAL']
    
    totals = survey_total(design, service_vars)
    
    total_exp = totals[totals['Variable'] == 'TOTAL']['Sum'].values[0]
    
    print("\nExpenditure totals and percentages:")
    for var in service_vars[:-1]:
        var_total = totals[totals['Variable'] == var]['Sum'].values[0]
        var_se = totals[totals['Variable'] == var]['StdDev'].values[0]
        pct = 100 * var_total / total_exp if total_exp > 0 else 0
        print(f"  {var}: ${var_total:,.0f} ({pct:.1f}%)")
    
    print(f"\n  TOTAL: ${total_exp:,.0f}")
    
    # PERCENTAGE OF PERSONS WITH AN EXPENSE, BY TYPE OF SERVICE
    print("\n" + "="*60)
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE, BY TYPE OF SERVICE")
    print("="*60)
    
    pct_results = survey_mean(design, flag_vars)
    pct_totals = survey_total(design, flag_vars)
    
    print("\nPercentage with expense by service type:")
    for i, (flag_var, exp_var) in enumerate(zip(flag_vars, expense_vars)):
        mean_val = pct_results[pct_results['Variable'] == flag_var]['Mean'].values[0]
        se_val = pct_results[pct_results['Variable'] == flag_var]['StdErr'].values[0]
        sum_val = pct_totals[pct_totals['Variable'] == flag_var]['Sum'].values[0]
        print(f"  {exp_var}: {mean_val*100:.2f}% (SE: {se_val*100:.3f}%), N with expense: {sum_val:,.0f}")
    
    # MEAN EXPENSE PER PERSON WITH AN EXPENSE, BY TYPE OF SERVICE AND AGE
    print("\n" + "="*60)
    print("MEAN EXPENSE PER PERSON WITH AN EXPENSE, BY TYPE OF SERVICE")
    print("="*60)
    
    # For each service type
    service_pairs = [
        ('TOTAL', 'X_ANYSVCE'),
        ('HOSPITAL_INPATIENT', 'X_HOSPITAL_INPATIENT'),
        ('AMBULATORY', 'X_AMBULATORY'),
        ('PRESCRIBED_MEDICINES', 'X_PRESCRIBED_MEDICINES'),
        ('DENTAL', 'X_DENTAL'),
        ('HOME_HEALTH_OTHER', 'X_HOME_HEALTH_OTHER')
    ]
    
    for exp_var, flag_var in service_pairs:
        print(f"\n{exp_var}:")
        
        # Filter to persons with expense
        puf181_expense = puf181[puf181[flag_var] == 1].copy()
        
        if len(puf181_expense) == 0:
            print("  No persons with expense")
            continue
        
        design_expense = SurveyDesign(
            data=puf181_expense,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWT15F'
        )
        
        # Overall
        overall = survey_mean(design_expense, exp_var)
        overall_total = survey_total(design_expense, exp_var)
        print(f"  Overall: Mean=${overall['Mean'].values[0]:,.0f} (SE: ${overall['StdErr'].values[0]:,.0f})")
        print(f"           Total=${overall_total['Sum'].values[0]:,.0f}")
        
        # By age category
        for agecat_val, agecat_label in agecat_labels.items():
            puf181_age = puf181_expense[puf181_expense['AGECAT'] == agecat_val].copy()
            
            if len(puf181_age) == 0:
                continue
            
            design_age = SurveyDesign(
                data=puf181_age,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT15F'
            )
            
            age_result = survey_mean(design_age, exp_var)
            age_total = survey_total(design_age, exp_var)
            print(f"  Age {agecat_label}: Mean=${age_result['Mean'].values[0]:,.0f} (SE: ${age_result['StdErr'].values[0]:,.0f})")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Exercise 1b - National Health Care Expenses by Service Type 2015')
    parser.add_argument('--data-path', type=str, default='C:/MEPS/SAS/DATA',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
