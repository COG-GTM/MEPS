import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_freq

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP (LINKING) -- NOV/DEC 2004")
print("2001 JOBS")
print("Types and Numbers of Jobs at Beginning of Year")
print("=" * 80)

jobs = load_sas_data(f'{data_path}/h56.sas7bdat', columns=[
    'DUPERSID', 'PANEL', 'RN', 'SUBTYPE', 'JOBSN'
])

subtype_labels = {
    1: 'Current Main',
    2: 'Current Miscellaneous',
    3: 'Former Main',
    4: 'Former Miscellaneous',
    5: 'Last Job Outside Rn',
    6: 'Retirement'
}

jobs_first_round = jobs[
    ((jobs['PANEL'] == 5) & (jobs['RN'] == 3)) |
    ((jobs['PANEL'] == 6) & (jobs['RN'] == 1))
].copy()

print("\n" + "-" * 80)
print("All Jobs at Beginning of Year")
print("-" * 80)

print("\nJob Type Distribution:")
for subtype, label in subtype_labels.items():
    count = len(jobs_first_round[jobs_first_round['SUBTYPE'] == subtype])
    print(f"  {subtype} {label}: {count:,}")

jobs_per = jobs_first_round.groupby('DUPERSID').apply(
    lambda x: pd.Series({
        'n1': (x['SUBTYPE'] == 1).sum(),
        'n2': (x['SUBTYPE'] == 2).sum(),
        'n3': (x['SUBTYPE'] == 3).sum(),
        'n4': (x['SUBTYPE'] == 4).sum(),
        'n5': (x['SUBTYPE'] == 5).sum(),
        'n6': (x['SUBTYPE'] == 6).sum(),
        'totjobs': len(x)
    })
).reset_index()

print("\n" + "-" * 80)
print("Persons with a First-Round JOBS Record")
print("-" * 80)

print(f"\nTotal persons with jobs: {len(jobs_per):,}")

print("\nTotal Jobs per Person:")
for n in range(1, 6):
    count = len(jobs_per[jobs_per['totjobs'] == n])
    if count > 0:
        print(f"  {n} jobs: {count:,}")
count_5plus = len(jobs_per[jobs_per['totjobs'] >= 5])
if count_5plus > 0:
    print(f"  5+ jobs: {count_5plus:,}")

fyc = load_sas_data(f'{data_path}/h60.sas7bdat', columns=[
    'DUPERSID', 'PANEL01', 'AGE31X', 'PERWT01F', 'VARSTR01', 'VARPSU01'
])

allper = fyc.merge(jobs_per, on='DUPERSID', how='left')

for col in ['n1', 'n2', 'n3', 'n4', 'n5', 'n6', 'totjobs']:
    allper[col] = allper[col].fillna(0).astype(int)

print("\n" + "-" * 80)
print("Persons Age 18+: # of Current Main & Miscellaneous Jobs at Beginning of Year")
print("-" * 80)

curr = allper[allper['AGE31X'] >= 18].copy()
curr['numcurr'] = curr['n1'] + curr['n2']
curr['ncurr'] = curr['numcurr'] + 1
curr['ncurr'] = curr['ncurr'].apply(lambda x: 4 if x > 3 else x)

curr = curr[curr['PERWT01F'] > 0].copy()

ncurr_labels = {1: 'None', 2: '1', 3: '2', 4: '3+'}

print("\nNumber of Current Jobs (Main + Miscellaneous):")

design = SurveyDesign(curr, strata='VARSTR01', cluster='VARPSU01', weight='PERWT01F')

total_pop = curr['PERWT01F'].sum()
total_n = len(curr)

print(f"\n{'# Curr Jobs':<12} {'Sample':>10} {'Population':>15} {'Col %':>10}")
print("-" * 50)

for ncurr_val in [1, 2, 3, 4]:
    subset = curr[curr['ncurr'] == ncurr_val]
    n_sample = len(subset)
    pop = subset['PERWT01F'].sum()
    pct = (pop / total_pop * 100) if total_pop > 0 else 0
    print(f"{ncurr_labels[ncurr_val]:<12} {n_sample:>10,} {pop:>15,.0f} {pct:>10.2f}")

print("-" * 50)
print(f"{'TOTAL':<12} {total_n:>10,} {total_pop:>15,.0f} {100.00:>10.2f}")
