import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_reg

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP -- JULY 2006")
print("HOSPITAL INPATIENT STAY EXPENDITURES:")
print("COMPARING STAYS WITH AND WITHOUT PRECEDING ER FACILITY EXPENDITURES")
print("=" * 80)

er_exp_labels = {0: 'ER_YES (Includes ER Facility Exp)', 1: 'ER_NO (No ER Facility Exp)'}

print("\n" + "-" * 80)
print("2003 Hospital Inpatient Stays")
print("-" * 80)

ip2003 = load_sas_data(f'{data_path}/h77d.sas7bdat', columns=[
    'DUPERSID', 'ERHEVIDX', 'IPXP03X', 'IPFXP03X', 'IPDXP03X',
    'PERWT03F', 'VARSTR', 'VARPSU'
])

ip2003['ER_FACEX'] = np.where(ip2003['ERHEVIDX'] != -1, 0, 1)

print(f"\nTotal IP stays: {len(ip2003):,}")
print(f"Stays with ER facility exp: {len(ip2003[ip2003['ER_FACEX'] == 0]):,}")
print(f"Stays without ER facility exp: {len(ip2003[ip2003['ER_FACEX'] == 1]):,}")

print("\n" + "-" * 80)
print("TOTAL 2003 IP EXPENDITURES (IPXP03X)")
print("-" * 80)

design = SurveyDesign(ip2003, strata='VARSTR', cluster='VARPSU', weight='PERWT03F')

result_overall = survey_mean(design, 'IPXP03X')
print(f"\nOverall:")
print(f"  N: {len(ip2003):,}")
print(f"  Sum of Weights: {ip2003['PERWT03F'].sum():,.0f}")
print(f"  Mean: ${result_overall['mean']:,.2f}")
print(f"  Std Error: ${result_overall['se']:,.2f}")

print("\nBy ER Facility Expense Status:")
for er_facex in [0, 1]:
    subset = ip2003[ip2003['ER_FACEX'] == er_facex]
    if len(subset) > 0:
        design_sub = SurveyDesign(subset, strata='VARSTR', cluster='VARPSU', weight='PERWT03F')
        result = survey_mean(design_sub, 'IPXP03X')
        print(f"\n  {er_exp_labels[er_facex]}:")
        print(f"    N: {len(subset):,}")
        print(f"    Sum of Weights: {subset['PERWT03F'].sum():,.0f}")
        print(f"    Mean: ${result['mean']:,.2f}")
        print(f"    Std Error: ${result['se']:,.2f}")

print("\nRegression: IPXP03X = ER_FACEX")
reg_result = survey_reg(design, 'IPXP03X', ['ER_FACEX'])
print(f"  Intercept: ${reg_result['coefficients']['Intercept']:,.2f}")
print(f"  ER_FACEX coefficient: ${reg_result['coefficients']['ER_FACEX']:,.2f}")

print("\n" + "-" * 80)
print("FACILITY IP EXPENDITURES (IPFXP03X)")
print("-" * 80)

print("\nBy ER Facility Expense Status:")
for er_facex in [0, 1]:
    subset = ip2003[ip2003['ER_FACEX'] == er_facex]
    if len(subset) > 0:
        design_sub = SurveyDesign(subset, strata='VARSTR', cluster='VARPSU', weight='PERWT03F')
        result = survey_mean(design_sub, 'IPFXP03X')
        print(f"\n  {er_exp_labels[er_facex]}:")
        print(f"    N: {len(subset):,}")
        print(f"    Mean: ${result['mean']:,.2f}")
        print(f"    Std Error: ${result['se']:,.2f}")

print("\nRegression: IPFXP03X = ER_FACEX")
reg_result = survey_reg(design, 'IPFXP03X', ['ER_FACEX'])
print(f"  Intercept: ${reg_result['coefficients']['Intercept']:,.2f}")
print(f"  ER_FACEX coefficient: ${reg_result['coefficients']['ER_FACEX']:,.2f}")

print("\n" + "-" * 80)
print("PHYSICIAN IP EXPENDITURES (IPDXP03X)")
print("-" * 80)

print("\nBy ER Facility Expense Status:")
for er_facex in [0, 1]:
    subset = ip2003[ip2003['ER_FACEX'] == er_facex]
    if len(subset) > 0:
        design_sub = SurveyDesign(subset, strata='VARSTR', cluster='VARPSU', weight='PERWT03F')
        result = survey_mean(design_sub, 'IPDXP03X')
        print(f"\n  {er_exp_labels[er_facex]}:")
        print(f"    N: {len(subset):,}")
        print(f"    Mean: ${result['mean']:,.2f}")
        print(f"    Std Error: ${result['se']:,.2f}")

print("\nRegression: IPDXP03X = ER_FACEX")
reg_result = survey_reg(design, 'IPDXP03X', ['ER_FACEX'])
print(f"  Intercept: ${reg_result['coefficients']['Intercept']:,.2f}")
print(f"  ER_FACEX coefficient: ${reg_result['coefficients']['ER_FACEX']:,.2f}")
