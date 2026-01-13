import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_mean

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP -- SEPTEMBER 2008")
print("HEALTH INSURANCE STATUS AND HEALTHCARE UTILIZATION")
print("=" * 80)

unins_labels = {1: 'UNINSURED', 2: 'INSURED'}
inscov_labels = {1: 'ANY PRIVATE', 2: 'PUBLIC ONLY', 3: 'UNINSURED'}

fyc = load_sas_data(f'{data_path}/h97.sas7bdat', columns=[
    'UNINS05', 'INSCOV05', 'RXTOT05', 'OBTOTV05', 'ERTOT05',
    'VARPSU', 'VARSTR', 'PERWT05F'
])

design = SurveyDesign(fyc, strata='VARSTR', cluster='VARPSU', weight='PERWT05F')

print("\n" + "-" * 80)
print("MEAN NUMBER OF PRESCRIPTIONS AND REFILLS BY INSURANCE COVERAGE STATUS")
print("-" * 80)

print("\nBy Uninsured Status (UNINS05):")
for unins in [1, 2]:
    subset = fyc[fyc['UNINS05'] == unins]
    if len(subset) > 0:
        design_sub = SurveyDesign(subset, strata='VARSTR', cluster='VARPSU', weight='PERWT05F')
        result = survey_mean(design_sub, 'RXTOT05')
        print(f"  {unins_labels.get(unins, str(unins))}:")
        print(f"    N: {len(subset):,}")
        print(f"    Sum of Weights: {subset['PERWT05F'].sum():,.0f}")
        print(f"    Mean: {result['mean']:.4f}")
        print(f"    Std Error: {result['se']:.4f}")

print("\nBy Insurance Coverage (INSCOV05):")
for inscov in [1, 2, 3]:
    subset = fyc[fyc['INSCOV05'] == inscov]
    if len(subset) > 0:
        design_sub = SurveyDesign(subset, strata='VARSTR', cluster='VARPSU', weight='PERWT05F')
        result = survey_mean(design_sub, 'RXTOT05')
        print(f"  {inscov_labels.get(inscov, str(inscov))}:")
        print(f"    N: {len(subset):,}")
        print(f"    Sum of Weights: {subset['PERWT05F'].sum():,.0f}")
        print(f"    Mean: {result['mean']:.4f}")
        print(f"    Std Error: {result['se']:.4f}")

print("\n" + "-" * 80)
print("MEAN NUMBER OF OFFICE VISITS BY INSURANCE COVERAGE STATUS")
print("-" * 80)

print("\nBy Uninsured Status (UNINS05):")
for unins in [1, 2]:
    subset = fyc[fyc['UNINS05'] == unins]
    if len(subset) > 0:
        design_sub = SurveyDesign(subset, strata='VARSTR', cluster='VARPSU', weight='PERWT05F')
        result = survey_mean(design_sub, 'OBTOTV05')
        print(f"  {unins_labels.get(unins, str(unins))}:")
        print(f"    N: {len(subset):,}")
        print(f"    Mean: {result['mean']:.4f}")
        print(f"    Std Error: {result['se']:.4f}")

print("\nBy Insurance Coverage (INSCOV05):")
for inscov in [1, 2, 3]:
    subset = fyc[fyc['INSCOV05'] == inscov]
    if len(subset) > 0:
        design_sub = SurveyDesign(subset, strata='VARSTR', cluster='VARPSU', weight='PERWT05F')
        result = survey_mean(design_sub, 'OBTOTV05')
        print(f"  {inscov_labels.get(inscov, str(inscov))}:")
        print(f"    N: {len(subset):,}")
        print(f"    Mean: {result['mean']:.4f}")
        print(f"    Std Error: {result['se']:.4f}")

print("\n" + "-" * 80)
print("MEAN NUMBER OF EMERGENCY DEPT. VISITS BY INSURANCE COVERAGE STATUS")
print("-" * 80)

print("\nBy Uninsured Status (UNINS05):")
for unins in [1, 2]:
    subset = fyc[fyc['UNINS05'] == unins]
    if len(subset) > 0:
        design_sub = SurveyDesign(subset, strata='VARSTR', cluster='VARPSU', weight='PERWT05F')
        result = survey_mean(design_sub, 'ERTOT05')
        print(f"  {unins_labels.get(unins, str(unins))}:")
        print(f"    N: {len(subset):,}")
        print(f"    Mean: {result['mean']:.4f}")
        print(f"    Std Error: {result['se']:.4f}")

print("\nBy Insurance Coverage (INSCOV05):")
for inscov in [1, 2, 3]:
    subset = fyc[fyc['INSCOV05'] == inscov]
    if len(subset) > 0:
        design_sub = SurveyDesign(subset, strata='VARSTR', cluster='VARPSU', weight='PERWT05F')
        result = survey_mean(design_sub, 'ERTOT05')
        print(f"  {inscov_labels.get(inscov, str(inscov))}:")
        print(f"    N: {len(subset):,}")
        print(f"    Mean: {result['mean']:.4f}")
        print(f"    Std Error: {result['se']:.4f}")
