import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_mean

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP (ESTIMATION) -- NOV/DEC 2004")
print("LONGITUDINAL FILE CREATION FOR PANEL 4 (1999-2000)")
print("=" * 80)

fyc99 = load_sas_data(f'{data_path}/h38.sas7bdat', columns=[
    'DUPERSID', 'PANEL99', 'INSCOV99', 'TOTEXP99'
])
fyc99 = fyc99.rename(columns={
    'PANEL99': 'PANEL', 'INSCOV99': 'INSCOV99', 'TOTEXP99': 'TOTEXP99'
})

fyc00 = load_sas_data(f'{data_path}/h50.sas7bdat', columns=[
    'DUPERSID', 'PANEL00', 'INSCOV00', 'TOTEXP00'
])
fyc00 = fyc00.rename(columns={
    'PANEL00': 'PANEL', 'INSCOV00': 'INSCOV00', 'TOTEXP00': 'TOTEXP00'
})

panel4_99 = fyc99[fyc99['PANEL'] == 4].copy()
panel4_00 = fyc00[fyc00['PANEL'] == 4].copy()

print(f"\nPanel 4 persons in 1999: {len(panel4_99):,}")
print(f"Panel 4 persons in 2000: {len(panel4_00):,}")

longwt = load_sas_data(f'{data_path}/h58.sas7bdat', columns=[
    'DUPERSID', 'LONGWTP4', 'VARSTRP4', 'VARPSUP4', 'YRINDP4'
])

longwt_valid = longwt[longwt['YRINDP4'] == 1].copy()
print(f"Persons in both 1999 and 2000 (YRINDP4=1): {len(longwt_valid):,}")

panel4 = panel4_99.merge(panel4_00, on='DUPERSID', how='inner', suffixes=('_99', '_00'))
panel4 = panel4.merge(longwt_valid, on='DUPERSID', how='inner')

panel4 = panel4[panel4['LONGWTP4'] > 0].copy()
print(f"Panel 4 persons with positive longitudinal weight: {len(panel4):,}")

panel4['UNINS99'] = np.where(panel4['INSCOV99'] == 3, 1, 0)
panel4['UNINS00'] = np.where(panel4['INSCOV00'] == 3, 1, 0)

panel4['ANY_EXP99'] = np.where(panel4['TOTEXP99'] > 0, 1, 0)
panel4['ANY_EXP00'] = np.where(panel4['TOTEXP00'] > 0, 1, 0)

panel4['INS_CHANGE'] = np.where(panel4['UNINS99'] != panel4['UNINS00'], 1, 0)

print("\n" + "-" * 80)
print("INSURANCE STATUS IN 1999 AND 2000")
print("-" * 80)

design = SurveyDesign(panel4, strata='VARSTRP4', cluster='VARPSUP4', weight='LONGWTP4')

result_unins99 = survey_mean(design, 'UNINS99')
result_unins00 = survey_mean(design, 'UNINS00')

print(f"\nUninsured in 1999: {result_unins99['mean']*100:.1f}% (SE: {result_unins99['se']*100:.2f}%)")
print(f"Uninsured in 2000: {result_unins00['mean']*100:.1f}% (SE: {result_unins00['se']*100:.2f}%)")

result_change = survey_mean(design, 'INS_CHANGE')
print(f"\nChanged Insurance Status: {result_change['mean']*100:.1f}% (SE: {result_change['se']*100:.2f}%)")

print("\n" + "-" * 80)
print("EXPENDITURES IN 1999 AND 2000")
print("-" * 80)

result_exp99 = survey_mean(design, 'TOTEXP99')
result_exp00 = survey_mean(design, 'TOTEXP00')

print(f"\nMean Expenditure 1999: ${result_exp99['mean']:,.2f} (SE: ${result_exp99['se']:,.2f})")
print(f"Mean Expenditure 2000: ${result_exp00['mean']:,.2f} (SE: ${result_exp00['se']:,.2f})")

result_anyexp99 = survey_mean(design, 'ANY_EXP99')
result_anyexp00 = survey_mean(design, 'ANY_EXP00')

print(f"\nHad Any Expense 1999: {result_anyexp99['mean']*100:.1f}% (SE: {result_anyexp99['se']*100:.2f}%)")
print(f"Had Any Expense 2000: {result_anyexp00['mean']*100:.1f}% (SE: {result_anyexp00['se']*100:.2f}%)")

print("\n" + "-" * 80)
print("EXPENDITURES BY INSURANCE STATUS IN 1999")
print("-" * 80)

for ins_status, label in [(0, 'Insured'), (1, 'Uninsured')]:
    subset = panel4[panel4['UNINS99'] == ins_status]
    if len(subset) > 0:
        design_ins = SurveyDesign(subset, strata='VARSTRP4', cluster='VARPSUP4', weight='LONGWTP4')
        result_ins = survey_mean(design_ins, 'TOTEXP99')
        print(f"\n{label} in 1999:")
        print(f"  Sample Size: {len(subset):,}")
        print(f"  Mean Expenditure: ${result_ins['mean']:,.2f}")
        print(f"  Std Error: ${result_ins['se']:,.2f}")
