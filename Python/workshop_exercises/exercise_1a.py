"""
Exercise 1a: National Health Care Expenses, 2016

This program generates the following estimates on national health care expenses, 2016:
    (1) Overall expenses
    (2) Percentage of persons with an expense
    (3) Mean expense per person with an expense

Input file: 2016 Full-Year Consolidated file (h192)

Python equivalent of: SAS/workshop_exercises/exercise_1a/Exercise1a.sas
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
    print("EXERCISE 1a: NATIONAL HEALTH CARE EXPENSES, 2016")
    print("=" * 80)
    
    # Load 2016 Full-Year Consolidated file (HC-192)
    fyc_file = data_dir / "h192.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    fyc = load_sas_data(
        fyc_file,
        columns=['TOTEXP16', 'AGE16X', 'AGE42X', 'AGE31X', 'VARSTR', 'VARPSU', 'PERWT16F']
    )
    
    # Create analysis variables
    fyc['TOTAL'] = fyc['TOTEXP16']
    
    # Create flag (1/0) variable for persons with an expense
    fyc['X_ANYSVCE'] = (fyc['TOTAL'] > 0).astype(int)
    
    # Create age variable from end of year, 42, and 31 variables
    fyc['AGE'] = np.where(
        fyc['AGE16X'] >= 0, fyc['AGE16X'],
        np.where(
            fyc['AGE42X'] >= 0, fyc['AGE42X'],
            np.where(fyc['AGE31X'] >= 0, fyc['AGE31X'], fyc['AGE16X'])
        )
    )
    
    # Create age category
    fyc['AGECAT'] = np.where(
        (fyc['AGE'] >= 0) & (fyc['AGE'] <= 64), 1,
        np.where(fyc['AGE'] > 64, 2, np.nan)
    )
    
    # Supporting crosstabs for flag variables
    print("\n" + "-" * 60)
    print("Supporting crosstabs for the flag variables")
    print("-" * 60)
    
    print("\nX_ANYSVCE by TOTAL (>0 vs 0):")
    crosstab = pd.crosstab(
        fyc['X_ANYSVCE'],
        fyc['TOTAL'].apply(lambda x: '>0' if x > 0 else '0'),
        margins=True
    )
    print(crosstab)
    
    print("\nAGECAT by AGE:")
    age_crosstab = pd.crosstab(
        fyc['AGECAT'].map({1: '0-64', 2: '65+'}),
        fyc['AGE'].apply(lambda x: '0-64' if 0 <= x <= 64 else ('65+' if x > 64 else 'Missing')),
        margins=True
    )
    print(age_crosstab)
    
    # Define survey design
    design = SurveyDesign(
        data=fyc,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT16F'
    )
    
    # Calculate overall estimates
    print("\n" + "=" * 60)
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE & OVERALL EXPENSES")
    print("=" * 60)
    
    # Percentage of persons with an expense
    pct_results = survey_mean(design, 'X_ANYSVCE')
    print("\nPERCENTAGE OF PERSONS WITH AN EXPENSE:")
    print(f"  N: {len(fyc):,}")
    print(f"  Population Size: {fyc['PERWT16F'].sum():,.0f}")
    print(f"  Proportion: {pct_results['mean'].values[0]:.4f}")
    print(f"  SE of Proportion: {pct_results['se'].values[0]:.5f}")
    
    total_with_expense = survey_total(design, 'X_ANYSVCE')
    print(f"  Persons with Any Expense: {total_with_expense['total'].values[0]:,.0f}")
    print(f"  SE of Number: {total_with_expense['se'].values[0]:,.0f}")
    
    # Overall expenses
    print("\nOVERALL EXPENSES:")
    mean_exp = survey_mean(design, 'TOTAL')
    total_exp = survey_total(design, 'TOTAL')
    print(f"  N: {len(fyc):,}")
    print(f"  Population Size: {fyc['PERWT16F'].sum():,.0f}")
    print(f"  Mean ($): {mean_exp['mean'].values[0]:,.2f}")
    print(f"  SE of Mean ($): {mean_exp['se'].values[0]:.5f}")
    print(f"  Total Expense ($): {total_exp['total'].values[0]:,.0f}")
    print(f"  SE of Total Expense ($): {total_exp['se'].values[0]:,.0f}")
    
    # Mean expense per person with an expense, by age group
    print("\n" + "=" * 60)
    print("MEAN EXPENSE PER PERSON WITH AN EXPENSE")
    print("For Overall, Age 0-64, and Age 65+")
    print("=" * 60)
    
    # Subset to persons with expense
    fyc_with_expense = fyc[fyc['X_ANYSVCE'] == 1].copy()
    design_expense = SurveyDesign(
        data=fyc_with_expense,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT16F'
    )
    
    # Overall (persons with expense)
    overall_mean = survey_mean(design_expense, 'TOTAL')
    overall_total = survey_total(design_expense, 'TOTAL')
    print("\nOverall (Persons with Any Expense):")
    print(f"  N: {len(fyc_with_expense):,}")
    print(f"  Population Size: {fyc_with_expense['PERWT16F'].sum():,.0f}")
    print(f"  Mean ($): {overall_mean['mean'].values[0]:,.1f}")
    print(f"  SE of Mean ($): {overall_mean['se'].values[0]:.4f}")
    print(f"  Total Expense ($): {overall_total['total'].values[0]:,.0f}")
    print(f"  SE of Total Expense ($): {overall_total['se'].values[0]:,.0f}")
    
    # By age group
    for agecat, label in [(1, '0-64'), (2, '65+')]:
        subset = fyc_with_expense[fyc_with_expense['AGECAT'] == agecat].copy()
        if len(subset) > 0:
            design_age = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT16F'
            )
            age_mean = survey_mean(design_age, 'TOTAL')
            age_total = survey_total(design_age, 'TOTAL')
            print(f"\nAge Group {label} (Persons with Any Expense):")
            print(f"  N: {len(subset):,}")
            print(f"  Population Size: {subset['PERWT16F'].sum():,.0f}")
            print(f"  Mean ($): {age_mean['mean'].values[0]:,.1f}")
            print(f"  SE of Mean ($): {age_mean['se'].values[0]:.4f}")
            print(f"  Total Expense ($): {age_total['total'].values[0]:,.0f}")
            print(f"  SE of Total Expense ($): {age_total['se'].values[0]:,.0f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
