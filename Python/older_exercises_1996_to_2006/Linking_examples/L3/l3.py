import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_mean

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP (LINKING) -- NOV/DEC 2004")
print("Link 2001 Household File and 2001 Events File")
print("=" * 80)

inscov_labels = {1: 'Any Private', 2: 'Public Only', 3: 'Uninsured'}
insured_labels = {1: 'Insured', 2: 'Uninsured'}
agecat_labels = {1: '0-3', 2: '4-7', 3: '8-11', 4: '12-15', 5: '16-17', 6: '18+'}
genckup_labels = {1: 'General Checkup', 2: 'No General Checkup'}

print("\n" + "-" * 80)
print("# Persons with a General Checkup in a Provider's Office")
print("-" * 80)

ob = load_sas_data(f'{data_path}/h59g.sas7bdat', columns=[
    'DUPERSID', 'VSTCTGRY', 'OBXP01X', 'OBSF01X'
])

ob_checkup = ob[ob['VSTCTGRY'] == 1].copy()

ob_pers = ob_checkup.groupby('DUPERSID').agg({
    'OBXP01X': 'sum',
    'OBSF01X': 'sum'
}).reset_index()

ob_pers.columns = ['DUPERSID', 'AMBTOTPD', 'AMBFAMPD']
ob_pers['GENCKUP'] = 1

print(f"\nPersons with general checkup: {len(ob_pers):,}")

print("\n" + "-" * 80)
print("Variables from Full-Year File (Persons w/ Positive Weight)")
print("-" * 80)

fyc = load_sas_data(f'{data_path}/h60.sas7bdat', columns=[
    'DUPERSID', 'PERWT01F', 'VARSTR01', 'VARPSU01',
    'AGE31X', 'AGE42X', 'AGE53X', 'INSCOV01'
])

fyc = fyc[fyc['PERWT01F'] > 0].copy()

def get_age(row):
    if row['AGE53X'] >= 0:
        return row['AGE53X']
    elif row['AGE42X'] >= 0:
        return row['AGE42X']
    elif row['AGE31X'] >= 0:
        return row['AGE31X']
    return np.nan

fyc['AGE'] = fyc.apply(get_age, axis=1)

def age_category(age):
    if pd.isna(age) or age < 0:
        return 0
    elif age <= 3:
        return 1
    elif age <= 7:
        return 2
    elif age <= 11:
        return 3
    elif age <= 15:
        return 4
    elif age <= 17:
        return 5
    else:
        return 6

fyc['AGECAT'] = fyc['AGE'].apply(age_category)

fyc['INSURED'] = np.where(fyc['INSCOV01'] > 2, 2, 1)

print(f"\nPersons with positive weight: {len(fyc):,}")

print("\n" + "-" * 80)
print("Link Person-Level File from Events File with Full-Year Person File")
print("-" * 80)

pers = fyc.merge(ob_pers, on='DUPERSID', how='left')

pers['GENCKUP'] = pers['GENCKUP'].fillna(2).astype(int)
pers['AMBTOTPD'] = pers['AMBTOTPD'].fillna(0)
pers['AMBFAMPD'] = pers['AMBFAMPD'].fillna(0)

print(f"\nTotal persons: {len(pers):,}")
print(f"Persons with checkup: {len(pers[pers['GENCKUP'] == 1]):,}")
print(f"Persons without checkup: {len(pers[pers['GENCKUP'] == 2]):,}")

print("\n" + "-" * 80)
print("Persons Age 18+")
print("-" * 80)

adults = pers[pers['AGECAT'] == 6].copy()

design = SurveyDesign(adults, strata='VARSTR01', cluster='VARPSU01', weight='PERWT01F')

total_pop = adults['PERWT01F'].sum()

print(f"\nTotal adults (18+): {len(adults):,}")
print(f"Weighted population: {total_pop:,.0f}")

print("\nGeneral Checkup by Insurance Status:")
print("-" * 60)

for insured in [1, 2]:
    subset = adults[adults['INSURED'] == insured]
    for genckup in [1, 2]:
        sub_genckup = subset[subset['GENCKUP'] == genckup]
        n = len(sub_genckup)
        pop = sub_genckup['PERWT01F'].sum()
        pct = (pop / subset['PERWT01F'].sum() * 100) if subset['PERWT01F'].sum() > 0 else 0
        print(f"  {insured_labels[insured]}, {genckup_labels[genckup]}: n={n:,}, {pct:.1f}%")

print("\n" + "-" * 80)
print("Persons Age 18+ with a General Checkup")
print("-" * 80)

adults_checkup = adults[adults['GENCKUP'] == 1].copy()

print("\nMean Expenditures by Insurance Status:")
for insured in [1, 2]:
    subset = adults_checkup[adults_checkup['INSURED'] == insured]
    if len(subset) > 0:
        design_ins = SurveyDesign(subset, strata='VARSTR01', cluster='VARPSU01', weight='PERWT01F')
        result_tot = survey_mean(design_ins, 'AMBTOTPD')
        result_fam = survey_mean(design_ins, 'AMBFAMPD')
        print(f"\n  {insured_labels[insured]}:")
        print(f"    Sample Size: {len(subset):,}")
        print(f"    Mean Total Paid: ${result_tot['mean']:,.2f}")
        print(f"    Mean Family Paid: ${result_fam['mean']:,.2f}")
