import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_mean

data_path = '../../../data'

fyc = load_sas_data(f'{data_path}/h62.sas7bdat', columns=[
    'DUPERSID', 'PERWT02P', 'VARSTR', 'VARPSU',
    'RTHLTH31', 'RTHLTH42', 'RTHLTH53',
    'HRWG31X', 'HRWG42X', 'HRWG53X',
    'HOUR31', 'HOUR42', 'HOUR53'
])

fyc = fyc[fyc['PERWT02P'] > 0].copy()

def get_latest_value(row, vars_list):
    for var in reversed(vars_list):
        if row[var] >= 0:
            return row[var]
    return np.nan

fyc['HRWAGE'] = fyc.apply(lambda row: get_latest_value(row, ['HRWG31X', 'HRWG42X', 'HRWG53X']), axis=1)
fyc['HOURS'] = fyc.apply(lambda row: get_latest_value(row, ['HOUR31', 'HOUR42', 'HOUR53']), axis=1)
fyc['RTHLTH'] = fyc.apply(lambda row: get_latest_value(row, ['RTHLTH31', 'RTHLTH42', 'RTHLTH53']), axis=1)

fyc['WKLYEARN'] = fyc['HRWAGE'] * fyc['HOURS']

fyc_valid = fyc[(fyc['WKLYEARN'] > 0) & (fyc['RTHLTH'] > 0)].copy()

weighted_quantiles = []
fyc_sorted = fyc_valid.sort_values('WKLYEARN')
fyc_sorted['cum_weight'] = fyc_sorted['PERWT02P'].cumsum()
total_weight = fyc_sorted['PERWT02P'].sum()

q25 = fyc_sorted[fyc_sorted['cum_weight'] >= total_weight * 0.25]['WKLYEARN'].iloc[0]
q50 = fyc_sorted[fyc_sorted['cum_weight'] >= total_weight * 0.50]['WKLYEARN'].iloc[0]
q75 = fyc_sorted[fyc_sorted['cum_weight'] >= total_weight * 0.75]['WKLYEARN'].iloc[0]

def assign_quartile(wklyearn):
    if wklyearn <= q25:
        return 1
    elif wklyearn <= q50:
        return 2
    elif wklyearn <= q75:
        return 3
    else:
        return 4

fyc_valid['QUARTILE'] = fyc_valid['WKLYEARN'].apply(assign_quartile)

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP (EMPLOYMENT) -- NOV/DEC 2004")
print("RELATIONSHIP BETWEEN PERCEIVED HEALTH STATUS AND WEEKLY EARNINGS")
print("=" * 80)

print("\nWeekly Earnings Quartile Cutpoints:")
print(f"  Q1 (25th percentile): ${q25:,.2f}")
print(f"  Q2 (50th percentile): ${q50:,.2f}")
print(f"  Q3 (75th percentile): ${q75:,.2f}")

health_labels = {
    1: 'Excellent',
    2: 'Very Good',
    3: 'Good',
    4: 'Fair',
    5: 'Poor'
}

print("\n" + "=" * 80)
print("MEAN PERCEIVED HEALTH STATUS BY WEEKLY EARNINGS QUARTILE")
print("=" * 80)

design = SurveyDesign(fyc_valid, strata='VARSTR', cluster='VARPSU', weight='PERWT02P')

for quartile in range(1, 5):
    subset = fyc_valid[fyc_valid['QUARTILE'] == quartile]
    if len(subset) > 0:
        design_q = SurveyDesign(subset, strata='VARSTR', cluster='VARPSU', weight='PERWT02P')
        result = survey_mean(design_q, 'RTHLTH')
        print(f"\nQuartile {quartile}:")
        print(f"  Sample Size: {len(subset):,}")
        print(f"  Mean Health Status: {result['mean']:.4f}")
        print(f"  Std Error: {result['se']:.4f}")
        print(f"  95% CI: ({result['ci_low']:.4f}, {result['ci_high']:.4f})")

print("\n" + "=" * 80)
print("OVERALL MEAN PERCEIVED HEALTH STATUS")
print("=" * 80)

result_overall = survey_mean(design, 'RTHLTH')
print(f"\nOverall:")
print(f"  Sample Size: {len(fyc_valid):,}")
print(f"  Mean Health Status: {result_overall['mean']:.4f}")
print(f"  Std Error: {result_overall['se']:.4f}")
print(f"  95% CI: ({result_overall['ci_low']:.4f}, {result_overall['ci_high']:.4f})")

print("\nNote: Health Status Scale: 1=Excellent, 2=Very Good, 3=Good, 4=Fair, 5=Poor")
print("Lower values indicate better perceived health status.")
