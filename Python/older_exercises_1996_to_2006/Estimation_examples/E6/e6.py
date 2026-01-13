import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP -- SEPTEMBER 2008")
print("HEALTHCARE SPENDING, 2005 (MEPS STAT BRIEF #193)")
print("DISTRIBUTION BY TYPE OF SERVICE")
print("=" * 80)

fyc = load_sas_data(f'{data_path}/h97.sas7bdat', columns=[
    'TOTEXP05', 'IPDEXP05', 'IPFEXP05', 'OBVEXP05', 'RXEXP05',
    'OPDEXP05', 'OPFEXP05', 'DVTEXP05', 'ERDEXP05', 'ERFEXP05',
    'HHAEXP05', 'HHNEXP05', 'OTHEXP05', 'VARSTR', 'VARPSU', 'PERWT05F'
])

fyc = fyc[fyc['PERWT05F'] > 0].copy()

fyc['TOTAL'] = fyc['TOTEXP05']
fyc['HOSPITAL_INPATIENT'] = fyc['IPDEXP05'] + fyc['IPFEXP05']
fyc['OFFICE_BASED'] = fyc['OBVEXP05']
fyc['PRESCRIBED_MEDICINES'] = fyc['RXEXP05']
fyc['HOSPITAL_OUTPATIENT'] = fyc['OPDEXP05'] + fyc['OPFEXP05']
fyc['DENTAL'] = fyc['DVTEXP05']
fyc['EMERGENCY_ROOM'] = fyc['ERDEXP05'] + fyc['ERFEXP05']
fyc['HOME_HEALTH'] = fyc['HHAEXP05'] + fyc['HHNEXP05']
fyc['OTHER'] = fyc['TOTAL'] - (fyc['HOSPITAL_INPATIENT'] + fyc['OFFICE_BASED'] + 
                               fyc['PRESCRIBED_MEDICINES'] + fyc['HOSPITAL_OUTPATIENT'] + 
                               fyc['DENTAL'] + fyc['EMERGENCY_ROOM'] + fyc['HOME_HEALTH'])

expense_vars = ['HOSPITAL_INPATIENT', 'OFFICE_BASED', 'PRESCRIBED_MEDICINES', 
                'HOSPITAL_OUTPATIENT', 'DENTAL', 'EMERGENCY_ROOM', 'HOME_HEALTH', 'OTHER']

for var in expense_vars:
    fyc[f'X_{var}'] = np.where(fyc[var] > 0, 1, 0)

fyc['X_ANYSVCE'] = np.where(fyc['TOTAL'] > 0, 1, 0)

design = SurveyDesign(fyc, strata='VARSTR', cluster='VARPSU', weight='PERWT05F')

print("\n" + "-" * 80)
print("FIGURE 1: DISTRIBUTION BY TYPE OF SERVICE")
print("-" * 80)

result_total = survey_total(design, 'TOTAL')
total_exp = result_total['total']

print(f"\nTotal Healthcare Expenditures: ${total_exp:,.0f}")

print("\nDistribution by Type of Service:")
print("-" * 50)

for var in expense_vars:
    result = survey_total(design, var)
    pct = (result['total'] / total_exp) * 100
    print(f"  {var:25s}: ${result['total']:>15,.0f} ({pct:5.1f}%)")

print("\n" + "-" * 80)
print("FIGURE 2: PERCENTAGE OF PERSONS WITH AN EXPENSE, BY TYPE OF SERVICE")
print("-" * 80)

result_any = survey_mean(design, 'X_ANYSVCE')
print(f"\nAny Service: {result_any['mean']*100:.1f}% (SE: {result_any['se']*100:.2f}%)")

for var in expense_vars:
    result = survey_mean(design, f'X_{var}')
    print(f"  {var:25s}: {result['mean']*100:5.1f}% (SE: {result['se']*100:.2f}%)")
