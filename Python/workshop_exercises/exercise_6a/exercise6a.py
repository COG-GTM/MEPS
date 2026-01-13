"""
This program includes a regression example for persons receiving a flu shot
in the last 12 months for the civilian noninstitutionized population, including:
- Percentage of people with a flu shot (civilian noninstitutionized population), 2018:
- Logistic regression: to identify demographic factors associated with receiving a flu shot

Input file:
 - 2018 Full-year consolidated file
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_reg, print_results


def main(meps_data_path: str = "C:/MEPS_Data"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    print("2018 MEPS: FLU SHOT ANALYSIS")
    print("="*80)
    
    # Format labels
    sex_labels = {1: 'Male', 2: 'Female'}
    racethx_labels = {
        1: 'Hispanic',
        2: 'NH White only',
        3: 'NH Black only',
        4: 'NH Asian only',
        5: 'NH Other etc'
    }
    inscov_labels = {
        1: 'Any Private',
        2: 'Public Only',
        3: 'Uninsured'
    }
    
    # Load 2018 data
    print("\nLoading 2018 Full-Year Consolidated file...")
    h209 = load_sas_data(os.path.join(meps_data_path, "H209.sas7bdat"))
    
    keep_vars = ['VARSTR', 'VARPSU', 'PERWT18F', 'SAQWT18F', 'ADFLST42', 'AGELAST', 'RACETHX', 'POVCAT18', 'INSCOV18', 'SEX']
    meps_2018 = h209[[c for c in keep_vars if c in h209.columns]].copy()
    
    # Create flu shot variable
    meps_2018['FLUSHOT'] = np.nan
    meps_2018.loc[meps_2018['ADFLST42'] == 1, 'FLUSHOT'] = 1
    meps_2018.loc[meps_2018['ADFLST42'] == 2, 'FLUSHOT'] = 0
    
    # Calculate percentage with flu shot (adults 18+)
    print("\n" + "="*80)
    print("PERCENTAGE OF PEOPLE WITH A FLU SHOT (AGE 18+), 2018")
    print("="*80)
    
    # Filter to adults with valid flu shot response and positive SAQ weight
    meps_adult = meps_2018[(meps_2018['AGELAST'] >= 18) & 
                           (meps_2018['FLUSHOT'].notna()) & 
                           (meps_2018['SAQWT18F'] > 0)].copy()
    
    design = SurveyDesign(
        data=meps_adult,
        strata='VARSTR',
        cluster='VARPSU',
        weight='SAQWT18F'
    )
    
    means = survey_mean(design, 'FLUSHOT')
    print(f"\nFlu Shot Prevalence (Age 18+):")
    print(f"  N: {means['N'].values[0]:,.0f}")
    print(f"  Proportion: {means['Mean'].values[0]:.4f}")
    print(f"  SE: {means['StdErr'].values[0]:.5f}")
    print(f"  Percentage: {means['Mean'].values[0]*100:.2f}%")
    
    # Logistic regression
    print("\n" + "="*80)
    print("LOGISTIC REGRESSION: FACTORS ASSOCIATED WITH RECEIVING A FLU SHOT")
    print("="*80)
    
    # Prepare data for regression
    # Create dummy variables for categorical predictors
    meps_reg = meps_adult.copy()
    
    # Sex (reference: Male)
    meps_reg['SEX_FEMALE'] = (meps_reg['SEX'] == 2).astype(int)
    
    # Race/ethnicity (reference: Hispanic)
    meps_reg['RACE_NH_WHITE'] = (meps_reg['RACETHX'] == 2).astype(int)
    meps_reg['RACE_NH_BLACK'] = (meps_reg['RACETHX'] == 3).astype(int)
    meps_reg['RACE_NH_ASIAN'] = (meps_reg['RACETHX'] == 4).astype(int)
    meps_reg['RACE_NH_OTHER'] = (meps_reg['RACETHX'] == 5).astype(int)
    
    # Insurance coverage (reference: Any Private)
    meps_reg['INSCOV_PUBLIC'] = (meps_reg['INSCOV18'] == 2).astype(int)
    meps_reg['INSCOV_UNINSURED'] = (meps_reg['INSCOV18'] == 3).astype(int)
    
    # Drop rows with missing values in predictors
    meps_reg = meps_reg.dropna(subset=['AGELAST', 'SEX', 'RACETHX', 'INSCOV18', 'FLUSHOT'])
    
    design_reg = SurveyDesign(
        data=meps_reg,
        strata='VARSTR',
        cluster='VARPSU',
        weight='SAQWT18F'
    )
    
    # Run logistic regression
    predictors = ['AGELAST', 'SEX_FEMALE', 'RACE_NH_WHITE', 'RACE_NH_BLACK', 
                  'RACE_NH_ASIAN', 'RACE_NH_OTHER', 'INSCOV_PUBLIC', 'INSCOV_UNINSURED']
    
    print("\nModel: FLUSHOT ~ AGELAST + SEX + RACETHX + INSCOV18")
    print("\nReference categories:")
    print("  SEX: Male")
    print("  RACETHX: Hispanic")
    print("  INSCOV18: Any Private")
    
    try:
        reg_results = survey_reg(design_reg, 'FLUSHOT', predictors, logistic=True)
        
        print("\nLogistic Regression Results:")
        print("-" * 80)
        print(f"{'Parameter':<25} {'Estimate':>12} {'Std Error':>12} {'t Value':>10} {'Pr > |t|':>12}")
        print("-" * 80)
        
        for _, row in reg_results.iterrows():
            param = row['Parameter']
            est = row['Estimate']
            se = row['StdErr']
            t_val = row.get('tValue', est/se if se > 0 else np.nan)
            p_val = row.get('pValue', np.nan)
            
            # Map parameter names to labels
            param_label = param
            if param == 'SEX_FEMALE':
                param_label = 'SEX: Female vs Male'
            elif param == 'RACE_NH_WHITE':
                param_label = 'RACETHX: NH White vs Hispanic'
            elif param == 'RACE_NH_BLACK':
                param_label = 'RACETHX: NH Black vs Hispanic'
            elif param == 'RACE_NH_ASIAN':
                param_label = 'RACETHX: NH Asian vs Hispanic'
            elif param == 'RACE_NH_OTHER':
                param_label = 'RACETHX: NH Other vs Hispanic'
            elif param == 'INSCOV_PUBLIC':
                param_label = 'INSCOV: Public vs Private'
            elif param == 'INSCOV_UNINSURED':
                param_label = 'INSCOV: Uninsured vs Private'
            
            print(f"{param_label:<25} {est:>12.4f} {se:>12.4f} {t_val:>10.2f} {p_val:>12.4f}")
        
        # Calculate odds ratios
        print("\nOdds Ratios:")
        print("-" * 60)
        for _, row in reg_results.iterrows():
            if row['Parameter'] != 'Intercept':
                or_val = np.exp(row['Estimate'])
                print(f"  {row['Parameter']}: {or_val:.3f}")
                
    except Exception as e:
        print(f"\nNote: Logistic regression requires statsmodels. Error: {e}")
        print("Please install statsmodels: pip install statsmodels")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Exercise 6a - Flu Shot Logistic Regression 2018')
    parser.add_argument('--data-path', type=str, default='C:/MEPS_Data',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
