import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_freq

data_path = '../../../data'

jobs = load_sas_data(f'{data_path}/h63.sas7bdat', columns=[
    'DUPERSID', 'PANEL', 'RN', 'SUBTYPE', 'JOBSN', 'STILLAT'
])

fyc = load_sas_data(f'{data_path}/h62.sas7bdat', columns=[
    'DUPERSID', 'PERWT02P', 'VARSTR', 'VARPSU', 'AGE31X', 'AGE42X', 'AGE53X'
])

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP (EMPLOYMENT) -- NOV/DEC 2004")
print("JOB CHANGES AMONG PERSONS WITH CURRENT JOB AT START OF 2002")
print("=" * 80)

jobs_start = jobs[
    ((jobs['PANEL'] == 6) & (jobs['RN'] == 3)) |
    ((jobs['PANEL'] == 7) & (jobs['RN'] == 1))
].copy()

jobs_start_cmj = jobs_start[jobs_start['SUBTYPE'] == 1].copy()

print(f"\nNumber of current main jobs at start of 2002: {len(jobs_start_cmj):,}")

jobs_end = jobs[
    ((jobs['PANEL'] == 6) & (jobs['RN'] == 5)) |
    ((jobs['PANEL'] == 7) & (jobs['RN'] == 3))
].copy()

jobs_start_cmj['START_JOB'] = 1

job_changes = jobs_start_cmj.merge(
    jobs_end[['DUPERSID', 'JOBSN', 'STILLAT']],
    on=['DUPERSID', 'JOBSN'],
    how='left',
    suffixes=('_start', '_end')
)

job_changes['JOB_CHANGE'] = np.where(
    job_changes['STILLAT'].isna() | (job_changes['STILLAT'] != 1),
    1,
    0
)

person_jobs = job_changes.groupby('DUPERSID').agg({
    'START_JOB': 'sum',
    'JOB_CHANGE': 'sum'
}).reset_index()

person_jobs.columns = ['DUPERSID', 'N_START_JOBS', 'N_JOB_CHANGES']

merged = person_jobs.merge(fyc, on='DUPERSID', how='inner')
merged = merged[merged['PERWT02P'] > 0].copy()

def get_age(row):
    for var in ['AGE53X', 'AGE42X', 'AGE31X']:
        if row[var] >= 0:
            return row[var]
    return np.nan

merged['AGE'] = merged.apply(get_age, axis=1)

def age_category(age):
    if pd.isna(age) or age < 0:
        return 'Unknown'
    elif age < 25:
        return '16-24'
    elif age < 45:
        return '25-44'
    elif age < 65:
        return '45-64'
    else:
        return '65+'

merged['AGECAT'] = merged['AGE'].apply(age_category)

merged['HAD_JOB_CHANGE'] = np.where(merged['N_JOB_CHANGES'] > 0, 1, 0)

print("\n" + "=" * 80)
print("JOB CHANGES BY AGE GROUP")
print("=" * 80)

design = SurveyDesign(merged, strata='VARSTR', cluster='VARPSU', weight='PERWT02P')

for agecat in ['16-24', '25-44', '45-64', '65+']:
    subset = merged[merged['AGECAT'] == agecat]
    if len(subset) > 0:
        n_with_change = subset[subset['HAD_JOB_CHANGE'] == 1]['PERWT02P'].sum()
        n_without_change = subset[subset['HAD_JOB_CHANGE'] == 0]['PERWT02P'].sum()
        total = n_with_change + n_without_change
        pct_with_change = (n_with_change / total * 100) if total > 0 else 0
        
        print(f"\nAge Group: {agecat}")
        print(f"  Sample Size: {len(subset):,}")
        print(f"  Weighted Population: {total:,.0f}")
        print(f"  Had Job Change: {n_with_change:,.0f} ({pct_with_change:.1f}%)")
        print(f"  No Job Change: {n_without_change:,.0f} ({100-pct_with_change:.1f}%)")

print("\n" + "=" * 80)
print("OVERALL JOB CHANGES")
print("=" * 80)

total_pop = merged['PERWT02P'].sum()
pop_with_change = merged[merged['HAD_JOB_CHANGE'] == 1]['PERWT02P'].sum()
pct_overall = (pop_with_change / total_pop * 100) if total_pop > 0 else 0

print(f"\nTotal Sample Size: {len(merged):,}")
print(f"Total Weighted Population: {total_pop:,.0f}")
print(f"Had Job Change: {pop_with_change:,.0f} ({pct_overall:.1f}%)")
print(f"No Job Change: {total_pop - pop_with_change:,.0f} ({100-pct_overall:.1f}%)")
