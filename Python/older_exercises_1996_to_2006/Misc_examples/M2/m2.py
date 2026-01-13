import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_total

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP -- SEPTEMBER 2008")
print("EFFECT OF STRATA AND PSU VARIABLES ON COMPUTING")
print("STANDARD ERRORS FOR TOTAL HEALTH-CARE EXPENDITURES")
print("=" * 80)

fyc = load_sas_data(f'{data_path}/h97.sas7bdat', columns=[
    'TOTEXP05', 'VARPSU', 'VARSTR', 'PERWT05F'
])

print("\n" + "-" * 80)
print("ASSUME SIMPLE RANDOM SAMPLE (SRS)")
print("-" * 80)

weighted_total = (fyc['TOTEXP05'] * fyc['PERWT05F']).sum()

n = len(fyc)
weighted_mean = weighted_total / fyc['PERWT05F'].sum()
weighted_var = np.average((fyc['TOTEXP05'] - weighted_mean)**2, weights=fyc['PERWT05F'])
srs_se = np.sqrt(weighted_var / n) * fyc['PERWT05F'].sum()

print(f"\nSRS Total: ${weighted_total:,.2f}")
print(f"SRS SE Total: ${srs_se:,.2f}")

print("\n" + "-" * 80)
print("ACCOUNT FOR MEPS COMPLEX SAMPLE DESIGN")
print("-" * 80)

design = SurveyDesign(fyc, strata='VARSTR', cluster='VARPSU', weight='PERWT05F')
result = survey_total(design, 'TOTEXP05')

print(f"\nComplex Design Total: ${result['total']:,.2f}")
print(f"Complex Design Total SE: ${result['se']:,.2f}")

print("\n" + "-" * 80)
print("COMPARISON")
print("-" * 80)

print(f"\n{'Method':<30} {'Total':>20} {'SE':>20}")
print("-" * 70)
print(f"{'Simple Random Sample':<30} ${weighted_total:>19,.2f} ${srs_se:>19,.2f}")
print(f"{'Complex Design':<30} ${result['total']:>19,.2f} ${result['se']:>19,.2f}")

ratio = result['se'] / srs_se if srs_se > 0 else 0
print(f"\nDesign Effect (SE ratio): {ratio:.2f}")

print("\n" + "-" * 80)
print("Note: The complex design standard error accounts for the stratification")
print("and clustering in the MEPS sample design. Using SRS assumptions would")
print("underestimate the true standard error.")
print("-" * 80)
