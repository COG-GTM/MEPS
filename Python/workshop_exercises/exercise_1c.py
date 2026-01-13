"""
Exercise 1c: National Health Care Expenses, 2018

This program generates the following estimates on national health care expenses
for the civilian noninstitutionalized population, 2018:
    - Overall expenses (National totals)
    - Percentage of persons with an expense
    - Mean expense per person
    - Mean/median expense per person with an expense
    - Mean expense per person with an expense, by age group
    - Median expense per person with an expense, by age group

Input file: 2018 Full-year consolidated file (h209)

Python equivalent of: SAS/workshop_exercises/exercise_1c/Exercise1c.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, survey_freq


def weighted_median(data, values, weights):
    """Calculate weighted median."""
    df = pd.DataFrame({'values': values, 'weights': weights}).dropna()
    df = df.sort_values('values')
    cumsum = df['weights'].cumsum()
    cutoff = df['weights'].sum() / 2.0
    return df[cumsum >= cutoff]['values'].iloc[0]


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS")
    
    print("=" * 80)
    print("MEPS FULL-YEAR CONSOLIDATED FILE, 2018")
    print("Exercise 1c: National Health Care Expenses")
    print("=" * 80)
    
    # Load 2018 Full-Year Consolidated file (HC-209)
    fyc_file = data_dir / "h209.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    fyc = load_sas_data(
        fyc_file,
        columns=['TOTEXP18', 'AGELAST', 'VARSTR', 'VARPSU', 'PERWT18F', 'PANEL']
    )
    
    # Create analysis variables
    fyc['WITH_AN_EXPENSE'] = fyc['TOTEXP18']
    
    # Create character variable for expense category
    fyc['CHAR_WITH_AN_EXPENSE'] = fyc['TOTEXP18'].apply(
        lambda x: 'Any Expense' if x > 0 else 'No Expense'
    )
    
    # Create age category
    fyc['AGECAT'] = fyc['AGELAST'].apply(
        lambda x: '0-64' if x <= 64 else '65+'
    )
    
    print("\nDataset contents:")
    print(f"  Number of observations: {len(fyc):,}")
    print(f"  Variables: {list(fyc.columns)}")
    
    # Define survey design
    design = SurveyDesign(
        data=fyc,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT18F'
    )
    
    # Method 1: Percentage of persons with an expense using formatted variable
    print("\n" + "=" * 60)
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 1")
    print("(Using formatted numeric variable)")
    print("=" * 60)
    
    # Create indicator for any expense
    fyc['ANY_EXPENSE_FLAG'] = (fyc['WITH_AN_EXPENSE'] > 0).astype(int)
    design = SurveyDesign(
        data=fyc,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT18F'
    )
    
    pct_result = survey_mean(design, 'ANY_EXPENSE_FLAG')
    total_result = survey_total(design, 'ANY_EXPENSE_FLAG')
    
    print(f"\nN: {len(fyc):,}")
    print(f"Proportion with expense: {pct_result['mean'].values[0]:.4f}")
    print(f"SE: {pct_result['se'].values[0]:.5f}")
    print(f"Number with expense: {total_result['total'].values[0]:,.0f}")
    
    # Method 2: Using character variable
    print("\n" + "=" * 60)
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 2")
    print("(Using character variable)")
    print("=" * 60)
    
    freq_result = survey_freq(design, 'CHAR_WITH_AN_EXPENSE')
    print("\nFrequency distribution:")
    for _, row in freq_result.iterrows():
        print(f"  {row['value']}: {row['count']:,.0f} ({row['proportion']*100:.2f}%)")
    
    # Method 3: Using SURVEYFREQ equivalent
    print("\n" + "=" * 60)
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 3")
    print("(Survey frequency table)")
    print("=" * 60)
    
    print("\nExpense Category Distribution:")
    for category in ['No Expense', 'Any Expense']:
        subset = fyc[fyc['CHAR_WITH_AN_EXPENSE'] == category]
        weighted_count = subset['PERWT18F'].sum()
        pct = weighted_count / fyc['PERWT18F'].sum() * 100
        print(f"  {category}: {weighted_count:,.0f} ({pct:.2f}%)")
    
    # Mean and median expense per person with an expense
    print("\n" + "=" * 60)
    print("MEAN AND MEDIAN EXPENSE PER PERSON WITH AN EXPENSE")
    print("Overall and by Age Group, 2018")
    print("=" * 60)
    
    # Subset to persons with expense
    fyc_expense = fyc[fyc['CHAR_WITH_AN_EXPENSE'] == 'Any Expense'].copy()
    
    # Overall
    design_expense = SurveyDesign(
        data=fyc_expense,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT18F'
    )
    
    mean_result = survey_mean(design_expense, 'TOTEXP18')
    total_result = survey_total(design_expense, 'TOTEXP18')
    median_val = weighted_median(
        fyc_expense, 
        fyc_expense['TOTEXP18'].values, 
        fyc_expense['PERWT18F'].values
    )
    
    print("\nOverall (Persons with Any Expense):")
    print(f"  N: {len(fyc_expense):,}")
    print(f"  Population Size: {fyc_expense['PERWT18F'].sum():,.0f}")
    print(f"  Mean ($): {mean_result['mean'].values[0]:,.2f}")
    print(f"  SE of Mean ($): {mean_result['se'].values[0]:.4f}")
    print(f"  Median ($): {median_val:,.2f}")
    print(f"  Total ($): {total_result['total'].values[0]:,.0f}")
    
    # By age group
    for agecat in ['0-64', '65+']:
        subset = fyc_expense[fyc_expense['AGECAT'] == agecat].copy()
        if len(subset) > 0:
            design_age = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT18F'
            )
            age_mean = survey_mean(design_age, 'TOTEXP18')
            age_total = survey_total(design_age, 'TOTEXP18')
            age_median = weighted_median(
                subset,
                subset['TOTEXP18'].values,
                subset['PERWT18F'].values
            )
            
            print(f"\nAge Group {agecat} (Persons with Any Expense):")
            print(f"  N: {len(subset):,}")
            print(f"  Population Size: {subset['PERWT18F'].sum():,.0f}")
            print(f"  Mean ($): {age_mean['mean'].values[0]:,.2f}")
            print(f"  SE of Mean ($): {age_mean['se'].values[0]:.4f}")
            print(f"  Median ($): {age_median:,.2f}")
            print(f"  Total ($): {age_total['total'].values[0]:,.0f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
