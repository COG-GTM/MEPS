import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, survey_reg

data_path = '../../../data'

fyc = load_sas_data(f'{data_path}/h60.sas7bdat', columns=[
    'DUPERSID', 'PERWT01F', 'VARSTR01', 'VARPSU01',
    'TOTEXP01', 'AGE31X', 'AGE42X', 'AGE53X', 'SEX'
])

fyc = fyc[fyc['PERWT01F'] > 0].copy()

def get_age(row):
    for var in ['AGE53X', 'AGE42X', 'AGE31X']:
        if row[var] >= 0:
            return row[var]
    return np.nan

fyc['AGE'] = fyc.apply(get_age, axis=1)

fyc['ANY_EXP'] = np.where(fyc['TOTEXP01'] > 0, 1, 0)

def age_category(age):
    if pd.isna(age) or age < 0:
        return 'Unknown'
    elif age < 18:
        return '0-17'
    elif age < 45:
        return '18-44'
    elif age < 65:
        return '45-64'
    else:
        return '65+'

fyc['AGECAT'] = fyc['AGE'].apply(age_category)

sex_labels = {1: 'Male', 2: 'Female'}
fyc['SEX_LABEL'] = fyc['SEX'].map(sex_labels)

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP (ESTIMATION) -- NOV/DEC 2004")
print("BASIC ESTIMATION EXAMPLE: MEANS, PROPORTIONS, TOTALS")
print("=" * 80)

design = SurveyDesign(fyc, strata='VARSTR01', cluster='VARPSU01', weight='PERWT01F')

print("\n" + "-" * 80)
print("MEAN TOTAL EXPENDITURES - OVERALL")
print("-" * 80)

result = survey_mean(design, 'TOTEXP01')
print(f"\nSample Size: {len(fyc):,}")
print(f"Mean Expenditure: ${result['mean']:,.2f}")
print(f"Std Error: ${result['se']:,.2f}")
print(f"95% CI: (${result['ci_low']:,.2f}, ${result['ci_high']:,.2f})")

print("\n" + "-" * 80)
print("TOTAL EXPENDITURES - OVERALL")
print("-" * 80)

result_total = survey_total(design, 'TOTEXP01')
print(f"\nTotal Expenditure: ${result_total['total']:,.0f}")
print(f"Std Error: ${result_total['se']:,.0f}")

print("\n" + "-" * 80)
print("PROPORTION WITH ANY EXPENSE")
print("-" * 80)

result_prop = survey_mean(design, 'ANY_EXP')
print(f"\nProportion with Expense: {result_prop['mean']:.4f} ({result_prop['mean']*100:.1f}%)")
print(f"Std Error: {result_prop['se']:.4f}")
print(f"95% CI: ({result_prop['ci_low']:.4f}, {result_prop['ci_high']:.4f})")

print("\n" + "-" * 80)
print("MEAN TOTAL EXPENDITURES BY AGE GROUP")
print("-" * 80)

for agecat in ['0-17', '18-44', '45-64', '65+']:
    subset = fyc[fyc['AGECAT'] == agecat]
    if len(subset) > 0:
        design_age = SurveyDesign(subset, strata='VARSTR01', cluster='VARPSU01', weight='PERWT01F')
        result_age = survey_mean(design_age, 'TOTEXP01')
        print(f"\nAge Group: {agecat}")
        print(f"  Sample Size: {len(subset):,}")
        print(f"  Mean Expenditure: ${result_age['mean']:,.2f}")
        print(f"  Std Error: ${result_age['se']:,.2f}")

print("\n" + "-" * 80)
print("MEAN TOTAL EXPENDITURES BY SEX")
print("-" * 80)

for sex in [1, 2]:
    subset = fyc[fyc['SEX'] == sex]
    if len(subset) > 0:
        design_sex = SurveyDesign(subset, strata='VARSTR01', cluster='VARPSU01', weight='PERWT01F')
        result_sex = survey_mean(design_sex, 'TOTEXP01')
        print(f"\n{sex_labels[sex]}:")
        print(f"  Sample Size: {len(subset):,}")
        print(f"  Mean Expenditure: ${result_sex['mean']:,.2f}")
        print(f"  Std Error: ${result_sex['se']:,.2f}")

print("\n" + "-" * 80)
print("REGRESSION: COMPARING MEAN EXPENDITURES BETWEEN MALES AND FEMALES")
print("-" * 80)

fyc['FEMALE'] = np.where(fyc['SEX'] == 2, 1, 0)

reg_result = survey_reg(design, 'TOTEXP01', ['FEMALE'])
print("\nDependent Variable: TOTEXP01")
print("Independent Variable: FEMALE (1=Female, 0=Male)")
print(f"\nIntercept (Male Mean): ${reg_result['coefficients']['Intercept']:,.2f}")
print(f"Female Coefficient: ${reg_result['coefficients']['FEMALE']:,.2f}")
print(f"  (Difference in mean expenditure for females vs males)")
print(f"\nR-squared: {reg_result['r_squared']:.4f}")
