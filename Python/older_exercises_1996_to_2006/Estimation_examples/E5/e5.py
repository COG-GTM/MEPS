import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_mean

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP (ESTIMATION) -- NOV/DEC 2004")
print("COMPUTING EVENT-LEVEL ESTIMATES")
print("=" * 80)

print("\n" + "-" * 80)
print("MEAN FACILITY EXPENSE PER INPATIENT STAY")
print("-" * 80)

ip2001 = load_sas_data(f'{data_path}/h59d.sas7bdat', columns=[
    'DUPERSID', 'IPFXP01X', 'PERWT01F', 'VARSTR01', 'VARPSU01'
])

ip2001 = ip2001[ip2001['PERWT01F'] > 0].copy()

print(f"\nNumber of Inpatient Stays: {len(ip2001):,}")
print(f"Sum of Weights: {ip2001['PERWT01F'].sum():,.0f}")

design_ip = SurveyDesign(ip2001, strata='VARSTR01', cluster='VARPSU01', weight='PERWT01F')
result_ip = survey_mean(design_ip, 'IPFXP01X')

print(f"\nMean Facility Expense per Stay: ${result_ip['mean']:,.2f}")
print(f"Std Error: ${result_ip['se']:,.2f}")
print(f"95% CI: (${result_ip['ci_low']:,.2f}, ${result_ip['ci_high']:,.2f})")

print("\n" + "-" * 80)
print("MEAN EXPENSE PER OFFICE VISIT TO A MEDICAL PROVIDER")
print("-" * 80)

ob2001 = load_sas_data(f'{data_path}/h59g.sas7bdat', columns=[
    'DUPERSID', 'OBXP01X', 'PERWT01F', 'VARSTR01', 'VARPSU01'
])

ob2001 = ob2001[ob2001['PERWT01F'] > 0].copy()

print(f"\nNumber of Office-Based Visits: {len(ob2001):,}")
print(f"Sum of Weights: {ob2001['PERWT01F'].sum():,.0f}")

design_ob = SurveyDesign(ob2001, strata='VARSTR01', cluster='VARPSU01', weight='PERWT01F')
result_ob = survey_mean(design_ob, 'OBXP01X')

print(f"\nMean Expense per Office Visit: ${result_ob['mean']:,.2f}")
print(f"Std Error: ${result_ob['se']:,.2f}")
print(f"95% CI: (${result_ob['ci_low']:,.2f}, ${result_ob['ci_high']:,.2f})")
