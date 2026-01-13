"""
Exercise 6b: Logistic Regression - COVID-19 Delayed Care Analysis

This program includes an example of 3 logistic regression models, each with a
separate dependent variable:
    - CVDLAYCA53: Delay med care for COVID R5/3 - recoded to yes/no (1,0)
    - CVDLAYPM53: Delay getting PMED for COVID R5/3 - recoded to yes/no (1,0)
    - CVDLAYDN53: Delay getting dental for COVID R5/3 - recoded to yes/no (1,0)

Covariates: age, gender, race/ethnicity, health insurance coverage status, and region

The program also estimates the proportion of persons with delayed care events
in the civilian noninstitutionalized population.

Input files:
    - 2020 Full-year consolidated file (h224)

Python equivalent of: SAS/workshop_exercises/exercise_6b/exercise6.sas
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
    print("2020 MEPS: COVID-19 DELAYED CARE ANALYSIS")
    print("=" * 80)
    
    # Load 2020 Full-Year file
    fyc_file = data_dir / "h224.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    meps_2020 = load_sas_data(
        fyc_file,
        columns=['VARSTR', 'VARPSU', 'PERWT20F', 'CVDLAYCA53', 'CVDLAYPM53', 'CVDLAYDN53',
                 'AGELAST', 'SEX', 'RACETHX', 'POVCAT20', 'INSCOV20', 'REGION53']
    )
    
    # Recode region (set -1 to missing)
    meps_2020['REGION'] = np.where(meps_2020['REGION53'] == -1, np.nan, meps_2020['REGION53'])
    
    # Recode delayed care variables
    # 1 = Yes, 2 = No, negative values = missing
    meps_2020['DELAYED_CARE_MED'] = np.where(meps_2020['CVDLAYCA53'] == 1, 1,
                                              np.where(meps_2020['CVDLAYCA53'] == 2, 0, np.nan))
    meps_2020['DELAYED_CARE_DENTAL'] = np.where(meps_2020['CVDLAYDN53'] == 1, 1,
                                                 np.where(meps_2020['CVDLAYDN53'] == 2, 0, np.nan))
    meps_2020['DELAYED_CARE_PMEDS'] = np.where(meps_2020['CVDLAYPM53'] == 1, 1,
                                                np.where(meps_2020['CVDLAYPM53'] == 2, 0, np.nan))
    
    print(f"\nTotal records: {len(meps_2020):,}")
    
    # Proportion of persons with delayed care events
    print("\n" + "=" * 60)
    print("PROPORTION OF PERSONS WITH DELAYED CARE EVENTS")
    print("=" * 60)
    
    # Filter to persons with positive weight
    analysis_data = meps_2020[meps_2020['PERWT20F'] > 0].copy()
    
    design = SurveyDesign(
        data=analysis_data,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT20F'
    )
    
    delayed_vars = ['DELAYED_CARE_MED', 'DELAYED_CARE_DENTAL', 'DELAYED_CARE_PMEDS']
    labels = ['Delayed Medical Care', 'Delayed Dental Care', 'Delayed Prescribed Medicines']
    
    print(f"\nN (unweighted): {len(analysis_data):,}")
    
    for var, label in zip(delayed_vars, labels):
        # Filter to non-missing values for this variable
        valid_data = analysis_data[analysis_data[var].notna()].copy()
        if len(valid_data) > 0:
            design_var = SurveyDesign(
                data=valid_data,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT20F'
            )
            mean_result = survey_mean(design_var, var)
            print(f"\n{label}:")
            print(f"  N: {len(valid_data):,}")
            print(f"  Proportion: {mean_result['mean'].values[0]:.4f}")
            print(f"  SE: {mean_result['se'].values[0]:.6f}")
    
    # Logistic regression for each outcome
    def run_logistic_regression(data, outcome_var, outcome_label):
        print(f"\n" + "=" * 60)
        print(f"LOGISTIC REGRESSION: {outcome_label.upper()}")
        print("=" * 60)
        
        # Prepare data for regression
        reg_data = data[data[outcome_var].notna()].copy()
        
        # Create dummy variables for categorical predictors
        # Sex: Reference = Male (1)
        reg_data['FEMALE'] = (reg_data['SEX'] == 2).astype(int)
        
        # Race/Ethnicity: Reference = Hispanic (1)
        reg_data['NH_WHITE'] = (reg_data['RACETHX'] == 2).astype(int)
        reg_data['NH_BLACK'] = (reg_data['RACETHX'] == 3).astype(int)
        reg_data['NH_ASIAN'] = (reg_data['RACETHX'] == 4).astype(int)
        reg_data['NH_OTHER'] = (reg_data['RACETHX'] == 5).astype(int)
        
        # Insurance Coverage: Reference = Any Private (1)
        reg_data['PUBLIC_ONLY'] = (reg_data['INSCOV20'] == 2).astype(int)
        reg_data['UNINSURED'] = (reg_data['INSCOV20'] == 3).astype(int)
        
        # Region: Reference = Northeast (1)
        reg_data['MIDWEST'] = (reg_data['REGION'] == 2).astype(int)
        reg_data['SOUTH'] = (reg_data['REGION'] == 3).astype(int)
        reg_data['WEST'] = (reg_data['REGION'] == 4).astype(int)
        
        # Drop rows with missing values in predictors
        reg_data = reg_data.dropna(subset=[outcome_var, 'AGELAST', 'SEX', 'RACETHX', 'INSCOV20', 'REGION'])
        
        print(f"\nN for regression: {len(reg_data):,}")
        
        # Define predictors
        predictors = ['AGELAST', 'FEMALE', 'NH_WHITE', 'NH_BLACK', 'NH_ASIAN', 'NH_OTHER',
                      'PUBLIC_ONLY', 'UNINSURED', 'MIDWEST', 'SOUTH', 'WEST']
        
        # Fit logistic regression
        design_reg = SurveyDesign(
            data=reg_data,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWT20F'
        )
        
        try:
            results = survey_glm(design_reg, outcome_var, predictors, family='binomial')
            
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
            
        except Exception as e:
            print(f"\nNote: Logistic regression requires statsmodels with survey support.")
            print(f"Error: {e}")
            
            # Show descriptive statistics instead
            print("\nDescriptive statistics (unweighted proportions):")
            print(f"\nOverall rate: {reg_data[outcome_var].mean():.4f}")
            
            print("\nBy Sex:")
            for sex_val, sex_label in [(1, 'Male'), (2, 'Female')]:
                subset = reg_data[reg_data['SEX'] == sex_val]
                if len(subset) > 0:
                    rate = subset[outcome_var].mean()
                    print(f"  {sex_label}: {rate:.4f}")
    
    # Run logistic regression for each outcome
    for var, label in zip(delayed_vars, labels):
        run_logistic_regression(analysis_data, var, label)
    
    print("\n" + "-" * 60)
    print("Reference categories:")
    print("  Sex: Male")
    print("  Race/Ethnicity: Hispanic")
    print("  Insurance: Any Private")
    print("  Region: Northeast")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
