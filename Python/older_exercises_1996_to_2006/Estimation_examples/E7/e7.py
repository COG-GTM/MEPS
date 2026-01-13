import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_freq

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP -- SEPTEMBER 2008")
print("COLONOSCOPY SCREENING AMONG ADULTS 50 AND OLDER, 2005")
print("(MEPS STAT BRIEF #188)")
print("=" * 80)

fyc = load_sas_data(f'{data_path}/h97.sas7bdat', columns=[
    'DUPERSID', 'VARSTR', 'VARPSU', 'AGE05X', 'AGE53X', 'AGE42X', 'AGE31X',
    'RACEX', 'HISPANX', 'EDUCYR', 'BOWEL53', 'WHNBWL53', 'PERWT05F'
])

fyc['BOWELYES'] = np.where(fyc['BOWEL53'] == 1, 1, 0)

def get_age(row):
    for var in ['AGE05X', 'AGE53X', 'AGE42X', 'AGE31X']:
        if row[var] >= 0:
            return row[var]
    return -1

fyc['AGE'] = fyc.apply(get_age, axis=1)

def age_category_3(age):
    if 0 <= age <= 49:
        return 1
    elif 50 <= age <= 64:
        return 2
    elif age >= 65:
        return 3
    else:
        return -1

def age_category_2(age):
    if 0 <= age <= 49:
        return 1
    elif age >= 50:
        return 2
    else:
        return -1

fyc['AGECAT'] = fyc['AGE'].apply(age_category_3)
fyc['AGE50PLUS'] = fyc['AGE'].apply(age_category_2)

def get_raceth(row):
    if row['HISPANX'] == 1:
        return 1
    elif row['HISPANX'] == 2:
        if row['RACEX'] == 1:
            return 2
        elif row['RACEX'] == 2:
            return 3
        elif row['RACEX'] == 3:
            return 4
        elif row['RACEX'] == 4:
            return 5
        elif row['RACEX'] == 5:
            return 6
        elif row['RACEX'] == 6:
            return 7
    return np.nan

fyc['RACETH'] = fyc.apply(get_raceth, axis=1)

def get_newrace(raceth):
    if raceth == 1:
        return 1
    elif raceth == 2:
        return 2
    elif raceth == 3:
        return 3
    elif raceth == 5:
        return 4
    elif raceth in [4, 6, 7]:
        return 5
    return np.nan

fyc['NEWRACE'] = fyc['RACETH'].apply(get_newrace)

def get_higheduc(row):
    if row['AGE'] < 16:
        return 5
    elif row['EDUCYR'] < 0:
        return 4
    elif row['EDUCYR'] < 12:
        return 1
    elif row['EDUCYR'] == 12:
        return 2
    elif row['EDUCYR'] > 12:
        return 3
    return -1

fyc['HIGHEDUC'] = fyc.apply(get_higheduc, axis=1)

agecat_labels = {1: '0-49', 2: '50-64', 3: '65+'}
age50plus_labels = {1: '0-49', 2: '50+'}
bowel_labels = {0: 'No', 1: 'Yes'}
race_labels = {1: 'Hispanic', 2: 'White Non-Hispanic', 3: 'Black Non-Hispanic', 
               4: 'Asian Non-Hispanic', 5: 'Other Non-Hispanic'}
educ_labels = {1: 'Less than High School', 2: 'High School Grad', 
               3: 'At Least Some College', 4: 'Unknown', 5: 'Younger than 16'}

design = SurveyDesign(fyc, strata='VARSTR', cluster='VARPSU', weight='PERWT05F')

print("\n" + "-" * 80)
print("FIGURE 1: COLONOSCOPY SCREENING BY AGE GROUP (TOTAL)")
print("-" * 80)

print("\nBy 3-Level Age Category:")
for agecat in [1, 2, 3]:
    subset = fyc[fyc['AGECAT'] == agecat]
    if len(subset) > 0:
        n_yes = subset[subset['BOWEL53'] == 1]['PERWT05F'].sum()
        n_total = subset['PERWT05F'].sum()
        pct = (n_yes / n_total * 100) if n_total > 0 else 0
        print(f"  {agecat_labels[agecat]:10s}: {pct:5.1f}% had colonoscopy (n={len(subset):,})")

print("\nBy 2-Level Age Category:")
for age50 in [1, 2]:
    subset = fyc[fyc['AGE50PLUS'] == age50]
    if len(subset) > 0:
        n_yes = subset[subset['BOWEL53'] == 1]['PERWT05F'].sum()
        n_total = subset['PERWT05F'].sum()
        pct = (n_yes / n_total * 100) if n_total > 0 else 0
        print(f"  {age50plus_labels[age50]:10s}: {pct:5.1f}% had colonoscopy (n={len(subset):,})")

print("\n" + "-" * 80)
print("FIGURE 2: COLONOSCOPY SCREENING BY RACE/ETHNICITY (AGE 50+)")
print("-" * 80)

subset_50plus = fyc[fyc['AGE50PLUS'] == 2]

for race in [1, 2, 3, 4, 5]:
    subset = subset_50plus[subset_50plus['NEWRACE'] == race]
    if len(subset) > 0:
        n_yes = subset[subset['BOWEL53'] == 1]['PERWT05F'].sum()
        n_total = subset['PERWT05F'].sum()
        pct = (n_yes / n_total * 100) if n_total > 0 else 0
        print(f"  {race_labels[race]:25s}: {pct:5.1f}% (n={len(subset):,})")

print("\n" + "-" * 80)
print("FIGURE 3: COLONOSCOPY SCREENING BY EDUCATION (AGE 50+)")
print("-" * 80)

for educ in [1, 2, 3, 4]:
    subset = subset_50plus[subset_50plus['HIGHEDUC'] == educ]
    if len(subset) > 0:
        n_yes = subset[subset['BOWEL53'] == 1]['PERWT05F'].sum()
        n_total = subset['PERWT05F'].sum()
        pct = (n_yes / n_total * 100) if n_total > 0 else 0
        print(f"  {educ_labels[educ]:25s}: {pct:5.1f}% (n={len(subset):,})")
