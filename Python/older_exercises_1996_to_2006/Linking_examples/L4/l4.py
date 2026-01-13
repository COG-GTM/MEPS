import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_freq

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP (LINKING) -- NOV/DEC 2004")
print("Link 2001 Household File and 2001 Conditions File")
print("=" * 80)

overall_labels = {
    1: 'Very Serious',
    2: 'Somewhat Serious',
    3: 'Not Very Serious',
    4: 'Not at All',
    5: 'Missing',
    6: 'Not Have Asthma'
}
asthma_labels = {1: 'Has Asthma', 2: 'No Asthma'}
agecat_labels = {1: '0-17', 2: '18+'}

print("\n" + "-" * 80)
print("Persons with Asthma")
print("-" * 80)

cond = load_sas_data(f'{data_path}/h61.sas7bdat', columns=[
    'DUPERSID', 'PANEL01', 'CONDRN', 'ICD9CODX',
    'OVRALL1', 'OVRALL2', 'OVRALL3', 'OVRALL4', 'OVRALL5'
])

asthma_cond = cond[cond['ICD9CODX'] == '493'].copy()

print(f"\nTotal asthma condition records: {len(asthma_cond):,}")

asthma_cond_sorted = asthma_cond.sort_values(['DUPERSID', 'CONDRN'])
asthma_first = asthma_cond_sorted.groupby('DUPERSID').first().reset_index()

print(f"Unique persons with asthma: {len(asthma_first):,}")

def get_overall(row):
    for var in ['OVRALL1', 'OVRALL2', 'OVRALL3', 'OVRALL4', 'OVRALL5']:
        if row[var] > -1:
            return row[var]
    return 5

asthma_first['OVERALL'] = asthma_first.apply(get_overall, axis=1)

print("\nHow Asthma Affects Overall Health:")
for val in [1, 2, 3, 4, 5]:
    count = len(asthma_first[asthma_first['OVERALL'] == val])
    if count > 0:
        print(f"  {overall_labels[val]}: {count:,}")

print("\n" + "-" * 80)
print("All Persons (with Positive Weight)")
print("-" * 80)

fyc = load_sas_data(f'{data_path}/h60.sas7bdat', columns=[
    'DUPERSID', 'PERWT01F', 'VARSTR01', 'VARPSU01',
    'AGE31X', 'AGE42X', 'AGE53X'
])

fyc = fyc[fyc['PERWT01F'] > 0].copy()

asthma_pers = asthma_first[['DUPERSID', 'OVERALL']].copy()

pers = fyc.merge(asthma_pers, on='DUPERSID', how='left')

pers['ASTHMA'] = np.where(pers['OVERALL'].notna(), 1, 2)
pers['OVERALL'] = pers['OVERALL'].fillna(6).astype(int)

def get_age(row):
    if row['AGE53X'] >= 0:
        return row['AGE53X']
    elif row['AGE42X'] >= 0:
        return row['AGE42X']
    elif row['AGE31X'] >= 0:
        return row['AGE31X']
    return np.nan

pers['AGE'] = pers.apply(get_age, axis=1)

def age_category(age):
    if pd.isna(age) or age < 0:
        return 0
    elif age < 18:
        return 1
    else:
        return 2

pers['AGECAT'] = pers['AGE'].apply(age_category)

print(f"\nTotal persons: {len(pers):,}")
print(f"Persons with asthma: {len(pers[pers['ASTHMA'] == 1]):,}")
print(f"Persons without asthma: {len(pers[pers['ASTHMA'] == 2]):,}")

print("\n" + "-" * 80)
print("Asthma Prevalence")
print("-" * 80)

design = SurveyDesign(pers, strata='VARSTR01', cluster='VARPSU01', weight='PERWT01F')

total_pop = pers['PERWT01F'].sum()
asthma_pop = pers[pers['ASTHMA'] == 1]['PERWT01F'].sum()
asthma_pct = (asthma_pop / total_pop * 100) if total_pop > 0 else 0

print(f"\nTotal Population: {total_pop:,.0f}")
print(f"Population with Asthma: {asthma_pop:,.0f} ({asthma_pct:.1f}%)")

print("\n" + "-" * 80)
print("How Asthma Affects Health (Among Persons with Asthma)")
print("-" * 80)

asthma_pers_only = pers[pers['ASTHMA'] == 1].copy()

design_asthma = SurveyDesign(asthma_pers_only, strata='VARSTR01', cluster='VARPSU01', weight='PERWT01F')

asthma_total = asthma_pers_only['PERWT01F'].sum()

print("\nOverall Health Impact:")
for val in [1, 2, 3, 4, 5]:
    subset = asthma_pers_only[asthma_pers_only['OVERALL'] == val]
    n = len(subset)
    pop = subset['PERWT01F'].sum()
    pct = (pop / asthma_total * 100) if asthma_total > 0 else 0
    print(f"  {overall_labels[val]}: n={n:,}, {pop:,.0f} ({pct:.1f}%)")

print("\n" + "-" * 80)
print("How Asthma Affects Health by Age Group")
print("-" * 80)

for agecat in [1, 2]:
    subset = asthma_pers_only[asthma_pers_only['AGECAT'] == agecat]
    if len(subset) > 0:
        print(f"\nAge Group: {agecat_labels[agecat]}")
        age_total = subset['PERWT01F'].sum()
        for val in [1, 2, 3, 4, 5]:
            sub_val = subset[subset['OVERALL'] == val]
            n = len(sub_val)
            pop = sub_val['PERWT01F'].sum()
            pct = (pop / age_total * 100) if age_total > 0 else 0
            if n > 0:
                print(f"  {overall_labels[val]}: n={n:,}, {pct:.1f}%")
