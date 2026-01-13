import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP -- SEPTEMBER 2008")
print("PRESCRIBED MEDICINES EXPENDITURES FOR CANCER CONDITIONS")
print("=" * 80)

agecat_labels = {1: '< 18', 2: '18-64', 3: '65+'}
racethn_labels = {1: 'HISPANIC', 2: 'BLACK', 3: 'ASIAN', 4: 'OTHER'}

print("\n" + "-" * 80)
print("Select People with Cancer from 2005 Condition File")
print("-" * 80)

cond = load_sas_data(f'{data_path}/h96.sas7bdat', columns=[
    'DUPERSID', 'CCCODEX', 'CONDIDX'
])

cond_cancer = cond[(cond['CCCODEX'] >= '011') & (cond['CCCODEX'] <= '045')][['DUPERSID', 'CONDIDX']].copy()

print(f"\nCancer condition records: {len(cond_cancer):,}")

print("\n" + "-" * 80)
print("Get Prescribed Medicines Expenses from 2005 PMED File")
print("-" * 80)

pmed = load_sas_data(f'{data_path}/h94a.sas7bdat', columns=[
    'DUPERSID', 'RXRECIDX', 'LINKIDX', 'RXSF05X', 'RXMD05X', 
    'RXPV05X', 'RXMR05X', 'RXXP05X', 'RXNDC'
])

pmed_sorted = pmed.sort_values(['LINKIDX', 'RXRECIDX'])

print(f"\nTotal PMED acquisition records: {len(pmed):,}")

pmedevnt = pmed_sorted.groupby('LINKIDX').agg({
    'DUPERSID': 'first',
    'RXSF05X': 'sum',
    'RXMD05X': 'sum',
    'RXPV05X': 'sum',
    'RXMR05X': 'sum',
    'RXXP05X': 'sum',
    'RXNDC': 'first'
}).reset_index()

pmedevnt = pmedevnt.rename(columns={
    'LINKIDX': 'EVNTIDX',
    'RXSF05X': 'OOP',
    'RXMD05X': 'MEDICAID',
    'RXPV05X': 'PRIVATE',
    'RXMR05X': 'MEDICARE',
    'RXXP05X': 'TOTRX05'
})

pmedevnt['OTHER'] = np.round(pmedevnt['TOTRX05'] - (pmedevnt['MEDICARE'] + pmedevnt['MEDICAID'] + 
                                                     pmedevnt['PRIVATE'] + pmedevnt['OOP']))

print(f"PMED event records: {len(pmedevnt):,}")

print("\n" + "-" * 80)
print("Merge Conditions to PMED Events through CLNK File")
print("-" * 80)

clnk = load_sas_data(f'{data_path}/h94i1.sas7bdat', columns=[
    'CONDIDX', 'EVNTIDX'
])

condclnk = cond_cancer.merge(clnk, on='CONDIDX', how='left')

print(f"Cancer conditions with event links: {len(condclnk):,}")

condpmed = condclnk.merge(pmedevnt, on='EVNTIDX', how='inner')

print(f"Cancer PMED events (before dedup): {len(condpmed):,}")

condpmed_sorted = condpmed.sort_values(['EVNTIDX', 'CONDIDX'])

condpmed_dedup = condpmed_sorted.drop_duplicates(subset=['EVNTIDX'])

print(f"Cancer PMED events (after dedup): {len(condpmed_dedup):,}")

print("\n" + "-" * 80)
print("Add Age and Race/Ethnicity from Full-Year File")
print("-" * 80)

fyc = load_sas_data(f'{data_path}/h97.sas7bdat', columns=[
    'DUPERSID', 'AGE05X', 'AGE53X', 'AGE42X', 'AGE31X',
    'RACETHNX', 'RACEX', 'PERWT05F'
])

def get_age(row):
    if row['AGE05X'] >= 0:
        return row['AGE05X']
    elif row['AGE53X'] >= 0:
        return row['AGE53X']
    elif row['AGE42X'] >= 0:
        return row['AGE42X']
    elif row['AGE31X'] >= 0:
        return row['AGE31X']
    return row['AGE05X']

fyc['AGE'] = fyc.apply(get_age, axis=1)

def age_category(age):
    if 0 <= age < 18:
        return 1
    elif 18 <= age < 65:
        return 2
    elif age >= 65:
        return 3
    return np.nan

fyc['AGECAT'] = fyc['AGE'].apply(age_category)

fyc_subset = fyc[['DUPERSID', 'AGECAT', 'RACETHNX', 'PERWT05F']].copy()

temp = condpmed_dedup.merge(fyc_subset, on='DUPERSID', how='inner')

temp['OOP'] = temp['OOP'] / 1000
temp['PRIVATE'] = temp['PRIVATE'] / 1000
temp['MEDICARE'] = temp['MEDICARE'] / 1000
temp['MEDICAID'] = temp['MEDICAID'] / 1000
temp['OTHER'] = temp['OTHER'] / 1000
temp['TOTRX05'] = temp['TOTRX05'] / 1000

print(f"\nFinal dataset records: {len(temp):,}")

print("\n" + "-" * 80)
print("PMED EXPENDITURES FOR CANCER CONDITIONS (Dollars in Thousands)")
print("-" * 80)

print("\n{:<20} {:>12} {:>12} {:>12} {:>12} {:>12} {:>12}".format(
    'Category', 'Total', 'OOP', 'Private', 'Medicare', 'Medicaid', 'Other'))
print("-" * 100)

total_exp = (temp['TOTRX05'] * temp['PERWT05F']).sum()
total_oop = (temp['OOP'] * temp['PERWT05F']).sum()
total_prv = (temp['PRIVATE'] * temp['PERWT05F']).sum()
total_mcr = (temp['MEDICARE'] * temp['PERWT05F']).sum()
total_mcd = (temp['MEDICAID'] * temp['PERWT05F']).sum()
total_oth = (temp['OTHER'] * temp['PERWT05F']).sum()

print("{:<20} {:>12,.0f} {:>12,.0f} {:>12,.0f} {:>12,.0f} {:>12,.0f} {:>12,.0f}".format(
    'TOTAL', total_exp, total_oop, total_prv, total_mcr, total_mcd, total_oth))

for agecat in [1, 2, 3]:
    subset = temp[temp['AGECAT'] == agecat]
    if len(subset) > 0:
        exp = (subset['TOTRX05'] * subset['PERWT05F']).sum()
        oop = (subset['OOP'] * subset['PERWT05F']).sum()
        prv = (subset['PRIVATE'] * subset['PERWT05F']).sum()
        mcr = (subset['MEDICARE'] * subset['PERWT05F']).sum()
        mcd = (subset['MEDICAID'] * subset['PERWT05F']).sum()
        oth = (subset['OTHER'] * subset['PERWT05F']).sum()
        print("{:<20} {:>12,.0f} {:>12,.0f} {:>12,.0f} {:>12,.0f} {:>12,.0f} {:>12,.0f}".format(
            agecat_labels[agecat], exp, oop, prv, mcr, mcd, oth))

for race in [1, 2, 3, 4]:
    subset = temp[temp['RACETHNX'] == race]
    if len(subset) > 0:
        exp = (subset['TOTRX05'] * subset['PERWT05F']).sum()
        oop = (subset['OOP'] * subset['PERWT05F']).sum()
        prv = (subset['PRIVATE'] * subset['PERWT05F']).sum()
        mcr = (subset['MEDICARE'] * subset['PERWT05F']).sum()
        mcd = (subset['MEDICAID'] * subset['PERWT05F']).sum()
        oth = (subset['OTHER'] * subset['PERWT05F']).sum()
        print("{:<20} {:>12,.0f} {:>12,.0f} {:>12,.0f} {:>12,.0f} {:>12,.0f} {:>12,.0f}".format(
            racethn_labels[race], exp, oop, prv, mcr, mcd, oth))
