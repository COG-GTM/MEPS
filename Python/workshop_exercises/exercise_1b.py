"""
Exercise 1b: National Health Care Expenses by Type of Service, 2015

This program generates the following estimates on national health care expenses
by type of service, 2015:
    (1) Percentage distribution of expenses by type of service
    (2) Percentage of persons with an expense, by type of service
    (3) Mean expense per person with an expense, by type of service

Service categories:
    - Hospital Inpatient
    - Ambulatory (Office-based & Hospital Outpatient visits)
    - Prescribed Medicines
    - Dental Visits
    - Emergency Room
    - Home Health Care and Other

Input file: 2015 Full-Year Consolidated file (h181)

Python equivalent of: SAS/workshop_exercises/exercise_1b/Exercise1b.sas
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
    print("EXERCISE 1b: NATIONAL HEALTH CARE EXPENSES BY TYPE OF SERVICE, 2015")
    print("=" * 80)
    
    # Load 2015 Full-Year Consolidated file (HC-181)
    fyc_file = data_dir / "h181.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    columns = [
        'TOTEXP15', 'IPDEXP15', 'IPFEXP15', 'OBVEXP15', 'RXEXP15',
        'OPDEXP15', 'OPFEXP15', 'DVTEXP15', 'ERDEXP15', 'ERFEXP15',
        'HHAEXP15', 'HHNEXP15', 'OTHEXP15', 'VISEXP15',
        'AGE15X', 'AGE42X', 'AGE31X', 'VARSTR', 'VARPSU', 'PERWT15F'
    ]
    
    fyc = load_sas_data(fyc_file, columns=columns)
    
    # Define expenditure variables by type of service
    fyc['TOTAL'] = fyc['TOTEXP15']
    fyc['HOSPITAL_INPATIENT'] = fyc['IPDEXP15'] + fyc['IPFEXP15']
    fyc['AMBULATORY'] = fyc['OBVEXP15'] + fyc['OPDEXP15'] + fyc['OPFEXP15'] + fyc['ERDEXP15'] + fyc['ERFEXP15']
    fyc['PRESCRIBED_MEDICINES'] = fyc['RXEXP15']
    fyc['DENTAL'] = fyc['DVTEXP15']
    fyc['HOME_HEALTH_OTHER'] = fyc['HHAEXP15'] + fyc['HHNEXP15'] + fyc['OTHEXP15'] + fyc['VISEXP15']
    
    # QC: Check if sum of expenditures by type equals total
    fyc['DIFF'] = (fyc['TOTAL'] - fyc['HOSPITAL_INPATIENT'] - fyc['AMBULATORY'] - 
                  fyc['PRESCRIBED_MEDICINES'] - fyc['DENTAL'] - fyc['HOME_HEALTH_OTHER'])
    
    # Create flag (1/0) variables for persons with an expense by type of service
    expense_vars = ['TOTAL', 'HOSPITAL_INPATIENT', 'AMBULATORY', 
                   'PRESCRIBED_MEDICINES', 'DENTAL', 'HOME_HEALTH_OTHER']
    flag_vars = ['X_ANYSVCE', 'X_HOSPITAL_INPATIENT', 'X_AMBULATORY',
                'X_PRESCRIBED_MEDICINES', 'X_DENTAL', 'X_HOME_HEALTH_OTHER']
    
    for exp_var, flag_var in zip(expense_vars, flag_vars):
        fyc[flag_var] = (fyc[exp_var] > 0).astype(int)
    
    # Create age variable
    fyc['AGE'] = np.where(
        fyc['AGE15X'] >= 0, fyc['AGE15X'],
        np.where(
            fyc['AGE42X'] >= 0, fyc['AGE42X'],
            np.where(fyc['AGE31X'] >= 0, fyc['AGE31X'], fyc['AGE15X'])
        )
    )
    
    # Create age category
    fyc['AGECAT'] = np.where(
        (fyc['AGE'] >= 0) & (fyc['AGE'] <= 64), 1,
        np.where(fyc['AGE'] > 64, 2, np.nan)
    )
    
    # Supporting crosstabs
    print("\n" + "-" * 60)
    print("Supporting crosstabs for the flag variables")
    print("-" * 60)
    
    print("\nQC: DIFF should be 0 for all records")
    print(fyc['DIFF'].value_counts())
    
    # Define survey design
    design = SurveyDesign(
        data=fyc,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT15F'
    )
    
    # Percentage distribution of expenses by type of service
    print("\n" + "=" * 60)
    print("PERCENTAGE DISTRIBUTION OF EXPENSES BY TYPE OF SERVICE")
    print("=" * 60)
    
    total_exp = survey_total(design, 'TOTAL')
    total_value = total_exp['total'].values[0]
    
    print(f"\nTotal Expenses: ${total_value:,.0f}")
    print("\nDistribution by Type of Service:")
    
    for exp_var in ['HOSPITAL_INPATIENT', 'AMBULATORY', 'PRESCRIBED_MEDICINES', 'DENTAL', 'HOME_HEALTH_OTHER']:
        exp_total = survey_total(design, exp_var)
        exp_value = exp_total['total'].values[0]
        pct = (exp_value / total_value) * 100 if total_value > 0 else 0
        print(f"  {exp_var}: ${exp_value:,.0f} ({pct:.1f}%)")
    
    # Percentage of persons with an expense by type of service
    print("\n" + "=" * 60)
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE, BY TYPE OF SERVICE")
    print("=" * 60)
    
    for flag_var, label in zip(flag_vars, expense_vars):
        pct_result = survey_mean(design, flag_var)
        total_result = survey_total(design, flag_var)
        print(f"\n{label}:")
        print(f"  N: {len(fyc):,}")
        print(f"  Proportion: {pct_result['mean'].values[0]:.4f}")
        print(f"  SE: {pct_result['se'].values[0]:.5f}")
        print(f"  Number with expense: {total_result['total'].values[0]:,.0f}")
    
    # Mean expense per person with an expense by type of service
    print("\n" + "=" * 60)
    print("MEAN EXPENSE PER PERSON WITH AN EXPENSE, BY TYPE OF SERVICE")
    print("=" * 60)
    
    service_types = [
        ('TOTAL', 'X_ANYSVCE', 'Total'),
        ('HOSPITAL_INPATIENT', 'X_HOSPITAL_INPATIENT', 'Hospital Inpatient'),
        ('AMBULATORY', 'X_AMBULATORY', 'Ambulatory'),
        ('PRESCRIBED_MEDICINES', 'X_PRESCRIBED_MEDICINES', 'Prescribed Medicines'),
        ('DENTAL', 'X_DENTAL', 'Dental'),
        ('HOME_HEALTH_OTHER', 'X_HOME_HEALTH_OTHER', 'Home Health/Other')
    ]
    
    for exp_var, flag_var, label in service_types:
        print(f"\n{label}:")
        
        # Overall (persons with expense)
        subset = fyc[fyc[flag_var] == 1].copy()
        if len(subset) > 0:
            design_sub = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT15F'
            )
            mean_result = survey_mean(design_sub, exp_var)
            total_result = survey_total(design_sub, exp_var)
            print(f"  Overall: N={len(subset):,}, Mean=${mean_result['mean'].values[0]:,.1f}, SE=${mean_result['se'].values[0]:.2f}")
            
            # By age group
            for agecat, age_label in [(1, '0-64'), (2, '65+')]:
                age_subset = subset[subset['AGECAT'] == agecat].copy()
                if len(age_subset) > 0:
                    design_age = SurveyDesign(
                        data=age_subset,
                        strata='VARSTR',
                        cluster='VARPSU',
                        weight='PERWT15F'
                    )
                    age_mean = survey_mean(design_age, exp_var)
                    print(f"  Age {age_label}: N={len(age_subset):,}, Mean=${age_mean['mean'].values[0]:,.1f}, SE=${age_mean['se'].values[0]:.2f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
