import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_mean

data_path = '../../../data'

cpi_factors = {
    1996: 1.0000 / 0.9231,
    1997: 1.0000 / 0.9449,
    1998: 1.0000 / 0.9593,
    1999: 1.0000
}

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP (ESTIMATION) -- NOV/DEC 2004")
print("MULTI-YEAR POOLING EXAMPLE: HEALTHCARE EXPENDITURES FOR CHILDREN 0-5")
print("=" * 80)

fyc96 = load_sas_data(f'{data_path}/h12.sas7bdat', columns=[
    'DUPERSID', 'WTDPER96', 'VARSTR96', 'VARPSU96', 'TOTEXP96', 'AGE96X'
])
fyc96['YEAR'] = 1996
fyc96 = fyc96.rename(columns={
    'WTDPER96': 'PERWT', 'VARSTR96': 'VARSTR', 'VARPSU96': 'VARPSU',
    'TOTEXP96': 'TOTEXP', 'AGE96X': 'AGE'
})

fyc97 = load_sas_data(f'{data_path}/h20.sas7bdat', columns=[
    'DUPERSID', 'WTDPER97', 'VARSTR97', 'VARPSU97', 'TOTEXP97', 'AGE97X'
])
fyc97['YEAR'] = 1997
fyc97 = fyc97.rename(columns={
    'WTDPER97': 'PERWT', 'VARSTR97': 'VARSTR', 'VARPSU97': 'VARPSU',
    'TOTEXP97': 'TOTEXP', 'AGE97X': 'AGE'
})

fyc98 = load_sas_data(f'{data_path}/h28.sas7bdat', columns=[
    'DUPERSID', 'WTDPER98', 'VARSTR98', 'VARPSU98', 'TOTEXP98', 'AGE98X'
])
fyc98['YEAR'] = 1998
fyc98 = fyc98.rename(columns={
    'WTDPER98': 'PERWT', 'VARSTR98': 'VARSTR', 'VARPSU98': 'VARPSU',
    'TOTEXP98': 'TOTEXP', 'AGE98X': 'AGE'
})

fyc99 = load_sas_data(f'{data_path}/h38.sas7bdat', columns=[
    'DUPERSID', 'PERWT99F', 'VARSTR99', 'VARPSU99', 'TOTEXP99', 'AGE99X'
])
fyc99['YEAR'] = 1999
fyc99 = fyc99.rename(columns={
    'PERWT99F': 'PERWT', 'VARSTR99': 'VARSTR', 'VARPSU99': 'VARPSU',
    'TOTEXP99': 'TOTEXP', 'AGE99X': 'AGE'
})

for df, year in [(fyc96, 1996), (fyc97, 1997), (fyc98, 1998), (fyc99, 1999)]:
    df['TOTEXP_ADJ'] = df['TOTEXP'] * cpi_factors[year]

pool_96_97 = pd.concat([fyc96, fyc97], ignore_index=True)
pool_96_97 = pool_96_97[pool_96_97['PERWT'] > 0].copy()
pool_96_97['POOLWT'] = pool_96_97['PERWT'] / 2

pool_98_99 = pd.concat([fyc98, fyc99], ignore_index=True)
pool_98_99 = pool_98_99[pool_98_99['PERWT'] > 0].copy()
pool_98_99['POOLWT'] = pool_98_99['PERWT'] / 2

def age_category(age):
    if pd.isna(age) or age < 0:
        return 'Unknown'
    elif age <= 1:
        return '0-1'
    elif age <= 3:
        return '2-3'
    elif age <= 5:
        return '4-5'
    else:
        return '6+'

pool_96_97['AGECAT'] = pool_96_97['AGE'].apply(age_category)
pool_98_99['AGECAT'] = pool_98_99['AGE'].apply(age_category)

children_96_97 = pool_96_97[pool_96_97['AGE'].between(0, 5)].copy()
children_98_99 = pool_98_99[pool_98_99['AGE'].between(0, 5)].copy()

print("\n" + "-" * 80)
print("POOLED 1996-1997 DATA: CHILDREN AGES 0-5")
print("(Expenditures adjusted to 1999 dollars)")
print("-" * 80)

print(f"\nSample Size: {len(children_96_97):,}")

design_96_97 = SurveyDesign(children_96_97, strata='VARSTR', cluster='VARPSU', weight='POOLWT')
result_96_97 = survey_mean(design_96_97, 'TOTEXP_ADJ')

print(f"Mean Expenditure: ${result_96_97['mean']:,.2f}")
print(f"Std Error: ${result_96_97['se']:,.2f}")
print(f"95% CI: (${result_96_97['ci_low']:,.2f}, ${result_96_97['ci_high']:,.2f})")

print("\nBy Age Group:")
for agecat in ['0-1', '2-3', '4-5']:
    subset = children_96_97[children_96_97['AGECAT'] == agecat]
    if len(subset) > 0:
        design_age = SurveyDesign(subset, strata='VARSTR', cluster='VARPSU', weight='POOLWT')
        result_age = survey_mean(design_age, 'TOTEXP_ADJ')
        print(f"  {agecat}: n={len(subset):,}, Mean=${result_age['mean']:,.2f}, SE=${result_age['se']:,.2f}")

print("\n" + "-" * 80)
print("POOLED 1998-1999 DATA: CHILDREN AGES 0-5")
print("(Expenditures adjusted to 1999 dollars)")
print("-" * 80)

print(f"\nSample Size: {len(children_98_99):,}")

design_98_99 = SurveyDesign(children_98_99, strata='VARSTR', cluster='VARPSU', weight='POOLWT')
result_98_99 = survey_mean(design_98_99, 'TOTEXP_ADJ')

print(f"Mean Expenditure: ${result_98_99['mean']:,.2f}")
print(f"Std Error: ${result_98_99['se']:,.2f}")
print(f"95% CI: (${result_98_99['ci_low']:,.2f}, ${result_98_99['ci_high']:,.2f})")

print("\nBy Age Group:")
for agecat in ['0-1', '2-3', '4-5']:
    subset = children_98_99[children_98_99['AGECAT'] == agecat]
    if len(subset) > 0:
        design_age = SurveyDesign(subset, strata='VARSTR', cluster='VARPSU', weight='POOLWT')
        result_age = survey_mean(design_age, 'TOTEXP_ADJ')
        print(f"  {agecat}: n={len(subset):,}, Mean=${result_age['mean']:,.2f}, SE=${result_age['se']:,.2f}")

print("\n" + "-" * 80)
print("COMPARISON: 1996-1997 vs 1998-1999")
print("-" * 80)

diff = result_98_99['mean'] - result_96_97['mean']
print(f"\nDifference in Mean Expenditure: ${diff:,.2f}")
print(f"  1996-1997: ${result_96_97['mean']:,.2f}")
print(f"  1998-1999: ${result_98_99['mean']:,.2f}")
