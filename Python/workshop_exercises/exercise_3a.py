"""
Exercise 3a: Estimates for Persons with Diabetes, 2015

This program illustrates how to identify persons with a condition and
calculate estimates on use and expenditures for persons with the condition.

The condition used in this exercise is Diabetes (CCS CODE=049 or 050)

Input files:
    - 2015 Condition file (h180)
    - 2015 Full-Year Consolidated file (h181)

Python equivalent of: SAS/workshop_exercises/exercise_3a/Exercise3a.sas
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
    print("EXERCISE 3a: ESTIMATES FOR PERSONS WITH DIABETES, 2015")
    print("=" * 80)
    
    # 1) Pull out conditions with Diabetes (CCS CODE='049', '050')
    cond_file = data_dir / "h180.sas7bdat"
    print(f"\nLoading conditions data from: {cond_file}")
    
    cond = load_sas_data(cond_file)
    
    # Filter to diabetes conditions
    diab = cond[cond['CCCODEX'].isin(['049', '050'])].copy()
    
    print("\nCCS codes for diabetic conditions:")
    print(diab['CCCODEX'].value_counts())
    
    # 2) Identify persons who reported diabetes
    diabpers = diab[['DUPERSID']].drop_duplicates()
    print(f"\nNumber of persons with diabetes: {len(diabpers):,}")
    
    # 3) Create a flag for persons with diabetes in the FY data
    fyc_file = data_dir / "h181.sas7bdat"
    print(f"\nLoading full-year consolidated data from: {fyc_file}")
    
    fyc = load_sas_data(fyc_file)
    
    # Merge to create diabetes flag
    fyc['DIABPERS'] = fyc['DUPERSID'].isin(diabpers['DUPERSID']).astype(int)
    fyc['DIABPERS'] = fyc['DIABPERS'].replace({1: 1, 0: 2})  # 1=Yes, 2=No
    
    # Supporting crosstabs
    print("\n" + "-" * 60)
    print("Supporting crosstabs for the flag variables")
    print("-" * 60)
    
    print("\nUnweighted # of persons who reported diabetes, 2015:")
    print(fyc['DIABPERS'].value_counts().sort_index().rename({1: 'Yes', 2: 'No'}))
    
    print("\nBy Sex:")
    sex_diab = pd.crosstab(
        fyc['SEX'].map({1: 'Male', 2: 'Female'}),
        fyc['DIABPERS'].map({1: 'Yes', 2: 'No'}),
        margins=True
    )
    print(sex_diab)
    
    print("\nWeighted # of persons who reported diabetes, 2015:")
    for diab_val, label in [(1, 'Yes'), (2, 'No')]:
        weighted_count = fyc.loc[fyc['DIABPERS'] == diab_val, 'PERWT15F'].sum()
        print(f"  {label}: {weighted_count:,.0f}")
    
    # 4) Calculate estimates on use and expenditures for persons with diabetes
    print("\n" + "=" * 60)
    print("ESTIMATES ON USE AND EXPENDITURES")
    print("FOR PERSONS WHO REPORTED DIABETES, 2015")
    print("=" * 60)
    
    # Subset to persons with diabetes
    fy_diab = fyc[fyc['DIABPERS'] == 1].copy()
    
    design = SurveyDesign(
        data=fy_diab,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT15F'
    )
    
    # Variables to analyze
    variables = ['TOTEXP15', 'TOTSLF15', 'OBTOTV15']
    labels = [
        'Total Expenditures',
        'Total Self/Family Payments',
        'Office-Based Visits'
    ]
    
    print(f"\nN (unweighted): {len(fy_diab):,}")
    print(f"Population Size: {fy_diab['PERWT15F'].sum():,.0f}")
    
    print("\nOverall (Persons with Diabetes):")
    for var, label in zip(variables, labels):
        if var in fy_diab.columns:
            mean_result = survey_mean(design, var)
            total_result = survey_total(design, var)
            
            print(f"\n  {label}:")
            print(f"    Mean: {mean_result['mean'].values[0]:,.2f}")
            print(f"    SE of Mean: {mean_result['se'].values[0]:.2f}")
            print(f"    Total: {total_result['total'].values[0]:,.0f}")
            print(f"    SE of Total: {total_result['se'].values[0]:,.0f}")
    
    # By Sex
    print("\n" + "-" * 40)
    print("By Sex (Persons with Diabetes):")
    print("-" * 40)
    
    for sex_val, sex_label in [(1, 'Male'), (2, 'Female')]:
        subset = fy_diab[fy_diab['SEX'] == sex_val].copy()
        if len(subset) > 0:
            design_sex = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT15F'
            )
            
            print(f"\n{sex_label}:")
            print(f"  N: {len(subset):,}")
            print(f"  Population Size: {subset['PERWT15F'].sum():,.0f}")
            
            for var, label in zip(variables, labels):
                if var in subset.columns:
                    mean_result = survey_mean(design_sex, var)
                    total_result = survey_total(design_sex, var)
                    print(f"  {label}: Mean=${mean_result['mean'].values[0]:,.2f}, Total=${total_result['total'].values[0]:,.0f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
