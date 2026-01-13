"""
Exercise 6a: Regression Example - Flu Shot Analysis

This program includes a regression example for persons receiving a flu shot
in the last 12 months for the civilian noninstitutionalized population, including:
    - Percentage of people with a flu shot (civilian noninstitutionalized population), 2018
    - Logistic regression: to identify demographic factors associated with receiving a flu shot

Input files:
    - 2018 Full-year consolidated file (h209)

Python equivalent of: SAS/workshop_exercises/exercise_6a/Exercise6.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_glm


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS")
    
    print("=" * 80)
    print("2018 MEPS: FLU SHOT ANALYSIS")
    print("=" * 80)
    
    # Load 2018 Full-Year file
    fyc_file = data_dir / "h209.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    meps_2018 = load_sas_data(
        fyc_file,
        columns=['VARSTR', 'VARPSU', 'PERWT18F', 'SAQWT18F', 'ADFLST42', 'AGELAST', 'RACETHX', 'POVCAT18', 'INSCOV18', 'SEX']
    )
    
    # Create flu shot variable
    # ADFLST42: 1=Yes, 2=No
    meps_2018['FLUSHOT'] = np.where(meps_2018['ADFLST42'] == 1, 1,
                                    np.where(meps_2018['ADFLST42'] == 2, 0, np.nan))
    
    # Create age group indicator for adults 18+
    meps_2018['ADULT'] = (meps_2018['AGELAST'] >= 18).astype(int)
    
    print(f"\nTotal records: {len(meps_2018):,}")
    print(f"Adults 18+: {meps_2018['ADULT'].sum():,}")
    
    # Percentage of adults with flu shot
    print("\n" + "=" * 60)
    print("PERCENTAGE OF ADULTS (18+) WITH FLU SHOT, 2018")
    print("=" * 60)
    
    # Subset to adults with valid flu shot response and positive SAQ weight
    adults = meps_2018[(meps_2018['ADULT'] == 1) & 
                       (meps_2018['FLUSHOT'].notna()) & 
                       (meps_2018['SAQWT18F'] > 0)].copy()
    
    design = SurveyDesign(
        data=adults,
        strata='VARSTR',
        cluster='VARPSU',
        weight='SAQWT18F'
    )
    
    mean_result = survey_mean(design, 'FLUSHOT')
    
    print(f"\nN (unweighted): {len(adults):,}")
    print(f"Proportion with Flu Shot: {mean_result['mean'].values[0]:.4f}")
    print(f"SE: {mean_result['se'].values[0]:.6f}")
    
    # Logistic regression
    print("\n" + "=" * 60)
    print("LOGISTIC REGRESSION: FACTORS ASSOCIATED WITH FLU SHOT")
    print("=" * 60)
    
    # Prepare data for regression
    # Create dummy variables for categorical predictors
    reg_data = adults.copy()
    
    # Sex: Reference = Male (1)
    reg_data['FEMALE'] = (reg_data['SEX'] == 2).astype(int)
    
    # Race/Ethnicity: Reference = Hispanic (1)
    reg_data['NH_WHITE'] = (reg_data['RACETHX'] == 2).astype(int)
    reg_data['NH_BLACK'] = (reg_data['RACETHX'] == 3).astype(int)
    reg_data['NH_ASIAN'] = (reg_data['RACETHX'] == 4).astype(int)
    reg_data['NH_OTHER'] = (reg_data['RACETHX'] == 5).astype(int)
    
    # Insurance Coverage: Reference = Any Private (1)
    reg_data['PUBLIC_ONLY'] = (reg_data['INSCOV18'] == 2).astype(int)
    reg_data['UNINSURED'] = (reg_data['INSCOV18'] == 3).astype(int)
    
    # Drop rows with missing values in predictors
    reg_data = reg_data.dropna(subset=['FLUSHOT', 'AGELAST', 'SEX', 'RACETHX', 'INSCOV18'])
    
    print(f"\nN for regression: {len(reg_data):,}")
    
    # Define predictors
    predictors = ['AGELAST', 'FEMALE', 'NH_WHITE', 'NH_BLACK', 'NH_ASIAN', 'NH_OTHER', 'PUBLIC_ONLY', 'UNINSURED']
    
    # Fit logistic regression
    design_reg = SurveyDesign(
        data=reg_data,
        strata='VARSTR',
        cluster='VARPSU',
        weight='SAQWT18F'
    )
    
    try:
        results = survey_glm(design_reg, 'FLUSHOT', predictors, family='binomial')
        
        print("\nLogistic Regression Results:")
        print("-" * 60)
        print(f"{'Variable':<20} {'Coefficient':>12} {'Std Error':>12} {'P-value':>10}")
        print("-" * 60)
        
        for var in ['Intercept'] + predictors:
            if var in results.index:
                coef = results.loc[var, 'coef']
                se = results.loc[var, 'se']
                pval = results.loc[var, 'pvalue']
                print(f"{var:<20} {coef:>12.4f} {se:>12.4f} {pval:>10.4f}")
        
        print("\n" + "-" * 60)
        print("Reference categories:")
        print("  Sex: Male")
        print("  Race/Ethnicity: Hispanic")
        print("  Insurance: Any Private")
        
    except Exception as e:
        print(f"\nNote: Logistic regression requires statsmodels with survey support.")
        print(f"Error: {e}")
        print("\nDescriptive statistics by group:")
        
        # Show descriptive statistics instead
        print("\nFlu Shot Rate by Sex:")
        for sex_val, sex_label in [(1, 'Male'), (2, 'Female')]:
            subset = reg_data[reg_data['SEX'] == sex_val]
            if len(subset) > 0:
                rate = subset['FLUSHOT'].mean()
                print(f"  {sex_label}: {rate:.4f}")
        
        print("\nFlu Shot Rate by Race/Ethnicity:")
        race_labels = {1: 'Hispanic', 2: 'NH White', 3: 'NH Black', 4: 'NH Asian', 5: 'NH Other'}
        for race_val, race_label in race_labels.items():
            subset = reg_data[reg_data['RACETHX'] == race_val]
            if len(subset) > 0:
                rate = subset['FLUSHOT'].mean()
                print(f"  {race_label}: {rate:.4f}")
        
        print("\nFlu Shot Rate by Insurance Coverage:")
        ins_labels = {1: 'Any Private', 2: 'Public Only', 3: 'Uninsured'}
        for ins_val, ins_label in ins_labels.items():
            subset = reg_data[reg_data['INSCOV18'] == ins_val]
            if len(subset) > 0:
                rate = subset['FLUSHOT'].mean()
                print(f"  {ins_label}: {rate:.4f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
