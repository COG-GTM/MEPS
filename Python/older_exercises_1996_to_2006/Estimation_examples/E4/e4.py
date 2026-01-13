import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_mean

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP (ESTIMATION) -- NOV/DEC 2004")
print("FAMILY-LEVEL ESTIMATION EXAMPLE")
print("=" * 80)

fyc = load_sas_data(f'{data_path}/h60.sas7bdat', columns=[
    'DUPERSID', 'DUID', 'FAMIDYR', 'PERWT01F', 'VARSTR01', 'VARPSU01',
    'TOTEXP01', 'FAMWT01F'
])

fyc['FAMID'] = fyc['DUID'].astype(str) + fyc['FAMIDYR'].astype(str)

fyc_sorted = fyc.sort_values(['FAMID', 'DUPERSID'])

family_agg = fyc_sorted.groupby('FAMID').agg({
    'TOTEXP01': 'sum',
    'DUPERSID': 'count',
    'FAMWT01F': 'first',
    'VARSTR01': 'first',
    'VARPSU01': 'first'
}).reset_index()

family_agg.columns = ['FAMID', 'FAM_TOTEXP', 'FAM_SIZE', 'FAMWT01F', 'VARSTR01', 'VARPSU01']

family_agg = family_agg[family_agg['FAMWT01F'] > 0].copy()

print(f"\nNumber of families with positive weight: {len(family_agg):,}")

print("\n" + "-" * 80)
print("FAMILY SIZE DISTRIBUTION")
print("-" * 80)

for size in range(1, 8):
    if size < 7:
        subset = family_agg[family_agg['FAM_SIZE'] == size]
        label = str(size)
    else:
        subset = family_agg[family_agg['FAM_SIZE'] >= 7]
        label = '7+'
    
    if len(subset) > 0:
        n_families = len(subset)
        weighted_n = subset['FAMWT01F'].sum()
        pct = weighted_n / family_agg['FAMWT01F'].sum() * 100
        print(f"  Size {label}: {n_families:,} families ({pct:.1f}%)")

print("\n" + "-" * 80)
print("MEAN FAMILY SIZE")
print("-" * 80)

design = SurveyDesign(family_agg, strata='VARSTR01', cluster='VARPSU01', weight='FAMWT01F')
result_size = survey_mean(design, 'FAM_SIZE')

print(f"\nMean Family Size: {result_size['mean']:.2f}")
print(f"Std Error: {result_size['se']:.4f}")
print(f"95% CI: ({result_size['ci_low']:.2f}, {result_size['ci_high']:.2f})")

print("\n" + "-" * 80)
print("MEAN TOTAL FAMILY EXPENDITURES")
print("-" * 80)

result_exp = survey_mean(design, 'FAM_TOTEXP')

print(f"\nMean Family Expenditure: ${result_exp['mean']:,.2f}")
print(f"Std Error: ${result_exp['se']:,.2f}")
print(f"95% CI: (${result_exp['ci_low']:,.2f}, ${result_exp['ci_high']:,.2f})")

print("\n" + "-" * 80)
print("MEAN FAMILY EXPENDITURES BY FAMILY SIZE")
print("-" * 80)

for size in range(1, 8):
    if size < 7:
        subset = family_agg[family_agg['FAM_SIZE'] == size]
        label = str(size)
    else:
        subset = family_agg[family_agg['FAM_SIZE'] >= 7]
        label = '7+'
    
    if len(subset) > 0:
        design_size = SurveyDesign(subset, strata='VARSTR01', cluster='VARPSU01', weight='FAMWT01F')
        result_size_exp = survey_mean(design_size, 'FAM_TOTEXP')
        print(f"\nFamily Size {label}:")
        print(f"  Sample Size: {len(subset):,}")
        print(f"  Mean Expenditure: ${result_size_exp['mean']:,.2f}")
        print(f"  Std Error: ${result_size_exp['se']:,.2f}")

print("\n" + "-" * 80)
print("PER-CAPITA FAMILY EXPENDITURES BY FAMILY SIZE")
print("-" * 80)

family_agg['PER_CAPITA_EXP'] = family_agg['FAM_TOTEXP'] / family_agg['FAM_SIZE']

for size in range(1, 8):
    if size < 7:
        subset = family_agg[family_agg['FAM_SIZE'] == size]
        label = str(size)
    else:
        subset = family_agg[family_agg['FAM_SIZE'] >= 7]
        label = '7+'
    
    if len(subset) > 0:
        design_size = SurveyDesign(subset, strata='VARSTR01', cluster='VARPSU01', weight='FAMWT01F')
        result_pc = survey_mean(design_size, 'PER_CAPITA_EXP')
        print(f"\nFamily Size {label}:")
        print(f"  Mean Per-Capita Expenditure: ${result_pc['mean']:,.2f}")
        print(f"  Std Error: ${result_pc['se']:,.2f}")
