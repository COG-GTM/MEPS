"""
This program includes an example of 3 logistic regression models, each with a
separate dependent variable.

cvdlayca53 - delay med care for covid r5/3 - recoded to yes/no (1,0)
cvdlaypm53 - delay getting pmed for covid r5/3 - recoded to yes/no (1,0)
cvdlaydn53 - delay getting dental for covid r5/3 - recoded to yes/no (1,0)

covariates: age, gender, race/ethnicity, health insurance coverage status, and region

The program also estimates the proportion of persons with delayed care events
in the civilian noninstitutionized population.

Input file: 2020 full-year consolidated file
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
    
    print("2020 MEPS: COVID-19 DELAYED CARE ANALYSIS")
    print("="*80)
    
    # Format labels
    sex_labels = {1: '1. Male', 2: '2. Female'}
    region_labels = {
        1: '1. Northeast',
        2: '2. Midwest',
        3: '3. South',
        4: '4. West'
    }
    inscov_labels = {
        1: '1. Any Private',
        2: '2. Public Only',
        3: '3. Uninsured'
    }
    racethx_labels = {
        1: '1. Hispanic',
        2: '2. NH White only',
        3: '3. NH Black only',
        4: '4. NH Asian only',
        5: '5. NH Other etc'
    }
    
    # Load 2020 data
    print("\nLoading 2020 Full-Year Consolidated file...")
    h224 = load_sas_data(os.path.join(meps_data_path, "H224.sas7bdat"))
    
    keep_vars = ['VARSTR', 'VARPSU', 'PERWT20F', 'CVDLAYCA53', 'CVDLAYPM53', 'CVDLAYDN53',
                 'AGELAST', 'SEX', 'RACETHX', 'POVCAT20', 'INSCOV20', 'REGION53']
    meps_2020 = h224[[c for c in keep_vars if c in h224.columns]].copy()
    
    # Recode region
    meps_2020['REGION'] = meps_2020['REGION53']
    meps_2020.loc[meps_2020['REGION53'] == -1, 'REGION'] = np.nan
    
    # Create delayed care variables
    delay_vars = {
        'CVDLAYCA53': 'DELAYED_CARE_MED',
        'CVDLAYDN53': 'DELAYED_CARE_DENTAL',
        'CVDLAYPM53': 'DELAYED_CARE_PMEDS'
    }
    
    for orig_var, new_var in delay_vars.items():
        if orig_var in meps_2020.columns:
            meps_2020[new_var] = np.nan
            meps_2020.loc[meps_2020[orig_var] == 1, new_var] = 1
            meps_2020.loc[meps_2020[orig_var] == 2, new_var] = 0
    
    # Calculate proportion of persons with delayed care events
    print("\n" + "="*80)
    print("PROPORTION OF PERSONS WITH DELAYED CARE EVENTS")
    print("="*80)
    
    # Filter to persons with positive weight
    meps_valid = meps_2020[meps_2020['PERWT20F'] > 0].copy()
    
    design = SurveyDesign(
        data=meps_valid,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT20F'
    )
    
    delay_outcome_vars = ['DELAYED_CARE_MED', 'DELAYED_CARE_DENTAL', 'DELAYED_CARE_PMEDS']
    delay_labels = {
        'DELAYED_CARE_MED': 'Delayed Medical Care',
        'DELAYED_CARE_DENTAL': 'Delayed Dental Care',
        'DELAYED_CARE_PMEDS': 'Delayed Prescribed Medicines'
    }
    
    means = survey_mean(design, delay_outcome_vars)
    
    print(f"\n{'Variable':<30} {'N':>10} {'Mean':>12} {'Std Error':>12}")
    print("-" * 70)
    
    for _, row in means.iterrows():
        var = row['Variable']
        label = delay_labels.get(var, var)
        print(f"{label:<30} {row['N']:>10,.0f} {row['Mean']:>12.4f} {row['StdErr']:>12.5f}")
    
    # Logistic regression models
    print("\n" + "="*80)
    print("LOGISTIC REGRESSION MODELS")
    print("="*80)
    
    # Prepare data for regression
    meps_reg = meps_valid.copy()
    
    # Sex (reference: Male)
    meps_reg['SEX_FEMALE'] = (meps_reg['SEX'] == 2).astype(int)
    
    # Race/ethnicity (reference: Hispanic)
    meps_reg['RACE_NH_WHITE'] = (meps_reg['RACETHX'] == 2).astype(int)
    meps_reg['RACE_NH_BLACK'] = (meps_reg['RACETHX'] == 3).astype(int)
    meps_reg['RACE_NH_ASIAN'] = (meps_reg['RACETHX'] == 4).astype(int)
    meps_reg['RACE_NH_OTHER'] = (meps_reg['RACETHX'] == 5).astype(int)
    
    # Insurance coverage (reference: Any Private)
    meps_reg['INSCOV_PUBLIC'] = (meps_reg['INSCOV20'] == 2).astype(int)
    meps_reg['INSCOV_UNINSURED'] = (meps_reg['INSCOV20'] == 3).astype(int)
    
    # Region (reference: Northeast)
    meps_reg['REGION_MIDWEST'] = (meps_reg['REGION'] == 2).astype(int)
    meps_reg['REGION_SOUTH'] = (meps_reg['REGION'] == 3).astype(int)
    meps_reg['REGION_WEST'] = (meps_reg['REGION'] == 4).astype(int)
    
    predictors = ['AGELAST', 'SEX_FEMALE', 'RACE_NH_WHITE', 'RACE_NH_BLACK', 
                  'RACE_NH_ASIAN', 'RACE_NH_OTHER', 'INSCOV_PUBLIC', 'INSCOV_UNINSURED',
                  'REGION_MIDWEST', 'REGION_SOUTH', 'REGION_WEST']
    
    print("\nReference categories:")
    print("  SEX: 1. Male")
    print("  RACETHX: 1. Hispanic")
    print("  INSCOV20: 1. Any Private")
    print("  REGION: 1. Northeast")
    
    # Run logistic regression for each outcome
    for outcome_var, outcome_label in delay_labels.items():
        print(f"\n{'='*80}")
        print(f"DEPENDENT VARIABLE: {outcome_label.upper()}")
        print("="*80)
        
        # Drop rows with missing values
        meps_model = meps_reg.dropna(subset=[outcome_var, 'AGELAST', 'SEX', 'RACETHX', 'INSCOV20', 'REGION'])
        
        if len(meps_model) == 0:
            print(f"No valid observations for {outcome_var}")
            continue
        
        design_reg = SurveyDesign(
            data=meps_model,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWT20F'
        )
        
        try:
            reg_results = survey_reg(design_reg, outcome_var, predictors, logistic=True)
            
            print(f"\nLogistic Regression Results:")
            print("-" * 80)
            print(f"{'Parameter':<30} {'Estimate':>12} {'Std Error':>12} {'Pr > |t|':>12}")
            print("-" * 80)
            
            for _, row in reg_results.iterrows():
                param = row['Parameter']
                est = row['Estimate']
                se = row['StdErr']
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
                elif param == 'REGION_MIDWEST':
                    param_label = 'REGION: Midwest vs Northeast'
                elif param == 'REGION_SOUTH':
                    param_label = 'REGION: South vs Northeast'
                elif param == 'REGION_WEST':
                    param_label = 'REGION: West vs Northeast'
                
                print(f"{param_label:<30} {est:>12.4f} {se:>12.4f} {p_val:>12.4f}")
            
        except Exception as e:
            print(f"\nNote: Logistic regression requires statsmodels. Error: {e}")
            print("Please install statsmodels: pip install statsmodels")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Exercise 6b - COVID-19 Delayed Care Logistic Regression 2020')
    parser.add_argument('--data-path', type=str, default='C:/MEPS_Data',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
