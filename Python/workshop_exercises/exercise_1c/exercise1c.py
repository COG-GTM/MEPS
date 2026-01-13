"""
This program generates the following estimates on national health care expenses
for the civilian noninstitutionized population, 2018:
  - Overall expenses (National totals)
  - Percentage of persons with an expense
  - Mean expense per person
  - Mean/median expense per person with an expense:
    - Mean expense per person with an expense
    - Mean expense per person with an expense, by age group
    - Median expense per person with an expense, by age group

Input file:
 - 2018 Full-year consolidated file
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meps_utils import (load_sas_data, SurveyDesign, survey_mean, survey_total, 
                        survey_freq, print_results)


def weighted_median(data: pd.DataFrame, var: str, weight: str) -> float:
    """Calculate weighted median."""
    df = data[[var, weight]].dropna().copy()
    df = df.sort_values(var)
    cumsum = df[weight].cumsum()
    cutoff = df[weight].sum() / 2.0
    return df[var][cumsum >= cutoff].iloc[0]


def main(meps_data_path: str = "C:/MEPS_Data"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    print("MEPS FULL-YEAR CONSOLIDATED FILE, 2018")
    print("="*60)
    
    # Read in data from 2018 consolidated data file (HC-209)
    print("\nLoading 2018 Full-Year Consolidated file...")
    puf209 = load_sas_data(os.path.join(meps_data_path, "H209.sas7bdat"))
    
    # Keep only needed variables
    keep_vars = ['TOTEXP18', 'AGELAST', 'VARSTR', 'VARPSU', 'PERWT18F', 'PANEL']
    puf209 = puf209[[c for c in keep_vars if c in puf209.columns]].copy()
    
    # Create another version of the TOTEXP18 variable
    puf209['WITH_AN_EXPENSE'] = puf209['TOTEXP18']
    
    # Create a character variable based on a numeric variable
    puf209['CHAR_WITH_AN_EXPENSE'] = np.where(
        puf209['TOTEXP18'] == 0, 'No Expense', 'Any Expense'
    )
    
    # Create age category
    puf209['AGECAT'] = np.where(puf209['AGELAST'] <= 64, '0-64', '65+')
    
    print("\nDataset contents:")
    print(puf209.info())
    
    # Create survey design
    design = SurveyDesign(
        data=puf209,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT18F'
    )
    
    # PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 1
    print("\n" + "="*60)
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 1")
    print("="*60)
    
    # Create binary expense flag
    puf209['expense_flag'] = (puf209['WITH_AN_EXPENSE'] > 0).astype(int)
    design_m1 = SurveyDesign(
        data=puf209,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT18F'
    )
    
    pct_expense = survey_mean(design_m1, 'expense_flag')
    print("\nPercentage with expense:")
    print(f"  Mean (proportion): {pct_expense['Mean'].values[0]:.4f}")
    print(f"  SE: {pct_expense['StdErr'].values[0]:.5f}")
    
    # PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 2
    print("\n" + "="*60)
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 2")
    print("="*60)
    
    # Using character variable
    freq_results = survey_freq(design, 'CHAR_WITH_AN_EXPENSE')
    print("\nFrequency of expense status:")
    print_results(freq_results)
    
    # PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 3
    print("\n" + "="*60)
    print("PERCENTAGE OF PERSONS WITH AN EXPENSE, 2018 - Method 3")
    print("="*60)
    
    # Using SURVEYFREQ equivalent
    print("\nSurvey frequency of expense status:")
    print_results(freq_results)
    
    # MEAN AND MEDIAN EXPENSE PER PERSON WITH AN EXPENSE
    print("\n" + "="*60)
    print("MEAN AND MEDIAN EXPENSE PER PERSON WITH AN EXPENSE")
    print("OVERALL AND FOR AGES 0-64, AND 65+, 2018")
    print("="*60)
    
    # Filter to persons with expense
    puf209_expense = puf209[puf209['CHAR_WITH_AN_EXPENSE'] == 'Any Expense'].copy()
    
    design_expense = SurveyDesign(
        data=puf209_expense,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT18F'
    )
    
    # Overall
    overall_mean = survey_mean(design_expense, 'TOTEXP18')
    overall_total = survey_total(design_expense, 'TOTEXP18')
    overall_median = weighted_median(puf209_expense, 'TOTEXP18', 'PERWT18F')
    
    print("\nOverall (persons with expense):")
    print(f"  N: {overall_mean['N'].values[0]:,.0f}")
    print(f"  Sum of Weights: {overall_mean['SumWgt'].values[0]:,.0f}")
    print(f"  Mean: ${overall_mean['Mean'].values[0]:,.2f}")
    print(f"  SE of Mean: ${overall_mean['StdErr'].values[0]:,.2f}")
    print(f"  Total: ${overall_total['Sum'].values[0]:,.0f}")
    print(f"  Median: ${overall_median:,.2f}")
    
    # By age category
    for agecat in ['0-64', '65+']:
        puf209_age = puf209_expense[puf209_expense['AGECAT'] == agecat].copy()
        
        if len(puf209_age) == 0:
            continue
        
        design_age = SurveyDesign(
            data=puf209_age,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWT18F'
        )
        
        age_mean = survey_mean(design_age, 'TOTEXP18')
        age_total = survey_total(design_age, 'TOTEXP18')
        age_median = weighted_median(puf209_age, 'TOTEXP18', 'PERWT18F')
        
        print(f"\nAge {agecat} (persons with expense):")
        print(f"  N: {age_mean['N'].values[0]:,.0f}")
        print(f"  Sum of Weights: {age_mean['SumWgt'].values[0]:,.0f}")
        print(f"  Mean: ${age_mean['Mean'].values[0]:,.2f}")
        print(f"  SE of Mean: ${age_mean['StdErr'].values[0]:,.2f}")
        print(f"  Total: ${age_total['Sum'].values[0]:,.0f}")
        print(f"  Median: ${age_median:,.2f}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Exercise 1c - National Health Care Expenses 2018')
    parser.add_argument('--data-path', type=str, default='C:/MEPS_Data',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
