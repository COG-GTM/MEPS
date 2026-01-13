"""
AHRQ MEPS Data Users Workshop - Estimation Example E1

This example shows how to compute person-level estimates for person-level
healthcare expenditures. Estimates include: means, proportions, totals.

Input file: h60.sas7bdat (2001 Full-Year Data File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Estimation_examples/E1/E1.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, survey_glm


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS/DATA")
    
    print("=" * 80)
    print("AHRQ MEPS DATA USERS WORKSHOP (ESTIMATION)")
    print("HEALTHCARE EXPENDITURES, 2001")
    print("=" * 80)
    
    # Load FYC file
    fyc_file = data_dir / "h60.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    h60 = load_sas_data(fyc_file, columns=[
        'TOTEXP01', 'SEX', 'AGE01X', 'AGE42X', 'AGE31X',
        'PERWT01F', 'VARPSU01', 'VARSTR01'
    ])
    
    # Create AGE variable
    h60['AGE'] = np.where(h60['AGE01X'] >= 0, h60['AGE01X'],
                 np.where(h60['AGE42X'] >= 0, h60['AGE42X'],
                 np.where(h60['AGE31X'] >= 0, h60['AGE31X'], h60['AGE01X'])))
    
    # Create ANY_EXP variable (100 if has expense, 0 otherwise)
    h60['ANY_EXP'] = np.where(h60['TOTEXP01'] == 0, 0, 100)
    
    # Create age groups
    h60['AGEGRP'] = np.where(h60['AGE'] <= 64, '0-64', '65-90')
    
    # Create sex labels
    h60['SEX_LABEL'] = np.where(h60['SEX'] == 1, 'MALE', 'FEMALE')
    
    print(f"Total records: {len(h60):,}")
    
    # Calculate estimates
    design = SurveyDesign(
        data=h60,
        strata='VARSTR01',
        cluster='VARPSU01',
        weight='PERWT01F'
    )
    
    # MEANS
    print("\n" + "=" * 80)
    print("WEIGHTED MEAN FOR PERSON-LEVEL TOTAL EXPENDITURES")
    print("=" * 80)
    
    mean_result = survey_mean(design, 'TOTEXP01')
    print(f"\nOverall Mean Expenditure: ${mean_result['mean'].values[0]:,.2f}")
    print(f"  SE: ${mean_result['se'].values[0]:.2f}")
    
    # By Age Group
    print("\n" + "-" * 60)
    print("BY AGE GROUP")
    print("-" * 60)
    
    for age_grp in ['0-64', '65-90']:
        subset = h60[h60['AGEGRP'] == age_grp].copy()
        design_sub = SurveyDesign(
            data=subset,
            strata='VARSTR01',
            cluster='VARPSU01',
            weight='PERWT01F'
        )
        mean_result = survey_mean(design_sub, 'TOTEXP01')
        print(f"\n{age_grp}:")
        print(f"  Mean: ${mean_result['mean'].values[0]:,.2f}")
        print(f"  SE: ${mean_result['se'].values[0]:.2f}")
    
    # By Sex
    print("\n" + "-" * 60)
    print("BY SEX")
    print("-" * 60)
    
    for sex_val, sex_label in [(1, 'MALE'), (2, 'FEMALE')]:
        subset = h60[h60['SEX'] == sex_val].copy()
        design_sub = SurveyDesign(
            data=subset,
            strata='VARSTR01',
            cluster='VARPSU01',
            weight='PERWT01F'
        )
        mean_result = survey_mean(design_sub, 'TOTEXP01')
        print(f"\n{sex_label}:")
        print(f"  Mean: ${mean_result['mean'].values[0]:,.2f}")
        print(f"  SE: ${mean_result['se'].values[0]:.2f}")
    
    # Comparing mean expenditure differences (Male vs Female)
    print("\n" + "=" * 80)
    print("COMPARING MEAN EXPENDITURE DIFFERENCES")
    print("MALE [1] VERSUS FEMALE [0]")
    print("=" * 80)
    
    h60_reg = h60.copy()
    h60_reg['SEX_BINARY'] = np.where(h60_reg['SEX'] == 2, 0, 1)  # Female=0, Male=1
    
    design_reg = SurveyDesign(
        data=h60_reg,
        strata='VARSTR01',
        cluster='VARPSU01',
        weight='PERWT01F'
    )
    
    reg_result = survey_glm(design_reg, 'TOTEXP01', ['SEX_BINARY'])
    print("\nRegression Results:")
    print(reg_result)
    
    # PROPORTIONS
    print("\n" + "=" * 80)
    print("MEAN OF THE DICHOTOMOUS VARIABLE ANY_EXP")
    print("(Proportion with some healthcare expenses)")
    print("=" * 80)
    
    mean_any = survey_mean(design, 'ANY_EXP')
    print(f"\nPercent with any expense: {mean_any['mean'].values[0]:.2f}%")
    print(f"  SE: {mean_any['se'].values[0]:.2f}")
    
    # By Age Group
    print("\n" + "-" * 60)
    print("BY AGE GROUP")
    print("-" * 60)
    
    for age_grp in ['0-64', '65-90']:
        subset = h60[h60['AGEGRP'] == age_grp].copy()
        design_sub = SurveyDesign(
            data=subset,
            strata='VARSTR01',
            cluster='VARPSU01',
            weight='PERWT01F'
        )
        mean_result = survey_mean(design_sub, 'ANY_EXP')
        print(f"\n{age_grp}: {mean_result['mean'].values[0]:.2f}%")
    
    # TOTALS
    print("\n" + "=" * 80)
    print("OVERALL TOTAL HEALTHCARE EXPENDITURES")
    print("=" * 80)
    
    total_result = survey_total(design, 'TOTEXP01')
    print(f"\nTotal Expenditures: ${total_result['total'].values[0]:,.0f}")
    print(f"  SE: ${total_result['se'].values[0]:,.0f}")
    
    # Population estimate (sum of weights)
    pop_estimate = h60['PERWT01F'].sum()
    print(f"\nPopulation Estimate: {pop_estimate:,.0f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
