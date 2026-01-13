import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_mean

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP (LINKING) -- NOV/DEC 2004")
print("Link 2001 Conditions and Event Files")
print("=" * 80)

inscov_labels = {1: 'Any private', 2: 'Public only', 3: 'Uninsured'}
vistype_labels = {'ob': 'Office-Based', 'op': 'Outpatient', 'er': 'Emergency', 'pm': 'Drug Purchase'}
sex_labels = {1: 'Male', 2: 'Female'}
racethnx_labels = {1: 'Hispanic', 2: 'Black, not Hispanic', 3: 'Other'}

print("\n" + "-" * 80)
print("Identify Asthma Conditions")
print("-" * 80)

cond = load_sas_data(f'{data_path}/h61.sas7bdat', columns=[
    'CONDIDX', 'ICD9CODX', 'DUPERSID'
])

asthma_cond = cond[cond['ICD9CODX'] == '493'][['CONDIDX', 'DUPERSID']].copy()
print(f"\nAsthma conditions: {len(asthma_cond):,}")

clnk = load_sas_data(f'{data_path}/h59if1.sas7bdat', columns=[
    'CONDIDX', 'EVNTIDX'
])

condev = asthma_cond.merge(clnk, on='CONDIDX', how='inner')
condev = condev.drop_duplicates(subset=['EVNTIDX'])
print(f"Asthma-related events (via CLNK): {len(condev):,}")

print("\n" + "-" * 80)
print("Prescribed Medicines for Asthma")
print("-" * 80)

rx = load_sas_data(f'{data_path}/h59a.sas7bdat', columns=[
    'RXRECIDX', 'LINKIDX', 'RXSF01X', 'RXXP01X'
])
rx = rx.rename(columns={'LINKIDX': 'EVNTIDX'})

pm = condev.merge(rx, on='EVNTIDX', how='inner')
pm['AMBTOTEV'] = pm['RXXP01X']
pm['AMBFAMEV'] = pm['RXSF01X']

print(f"Prescribed medicine events for asthma: {len(pm):,}")

perpmed = pm.groupby('DUPERSID').agg({
    'AMBTOTEV': 'sum',
    'AMBFAMEV': 'sum'
}).reset_index()
perpmed.columns = ['DUPERSID', 'AMBTOTPD', 'AMBFAMPD']

fyc = load_sas_data(f'{data_path}/h60.sas7bdat', columns=[
    'DUPERSID', 'INSCOV01', 'PERWT01F', 'AGE31X', 'AGE42X', 'AGE53X',
    'SEX', 'RACETHNX'
])

pers1 = perpmed.merge(fyc, on='DUPERSID', how='inner')

print("\nAverage Prescription Expenditures per Person, for Persons with Asthma:")
print("-" * 60)

for inscov in [1, 2, 3]:
    subset = pers1[pers1['INSCOV01'] == inscov]
    if len(subset) > 0:
        mean_tot = np.average(subset['AMBTOTPD'], weights=subset['PERWT01F'])
        mean_fam = np.average(subset['AMBFAMPD'], weights=subset['PERWT01F'])
        print(f"  {inscov_labels[inscov]}:")
        print(f"    Total Paid: ${mean_tot:,.2f}")
        print(f"    Family Paid: ${mean_fam:,.2f}")

print("\n" + "-" * 80)
print("All Ambulatory Events for Asthma")
print("-" * 80)

ob = load_sas_data(f'{data_path}/h59g.sas7bdat', columns=[
    'EVNTIDX', 'OBXP01X', 'OBSF01X'
])
ob_asthma = condev.merge(ob, on='EVNTIDX', how='inner')
ob_asthma['AMBTOTEV'] = ob_asthma['OBXP01X']
ob_asthma['AMBFAMEV'] = ob_asthma['OBSF01X']
ob_asthma['VISTYPE'] = 'ob'

op = load_sas_data(f'{data_path}/h59f.sas7bdat', columns=[
    'EVNTIDX', 'OPXP01X', 'OPFSF01X', 'OPDSF01X'
])
op_asthma = condev.merge(op, on='EVNTIDX', how='inner')
op_asthma['AMBTOTEV'] = op_asthma['OPXP01X']
op_asthma['AMBFAMEV'] = op_asthma['OPFSF01X'].fillna(0) + op_asthma['OPDSF01X'].fillna(0)
op_asthma['VISTYPE'] = 'op'

er = load_sas_data(f'{data_path}/h59e.sas7bdat', columns=[
    'EVNTIDX', 'ERXP01X', 'ERFSF01X', 'ERDSF01X'
])
er_asthma = condev.merge(er, on='EVNTIDX', how='inner')
er_asthma['AMBTOTEV'] = er_asthma['ERXP01X']
er_asthma['AMBFAMEV'] = er_asthma['ERFSF01X'].fillna(0) + er_asthma['ERDSF01X'].fillna(0)
er_asthma['VISTYPE'] = 'er'

pm['VISTYPE'] = 'pm'

allevnt = pd.concat([
    ob_asthma[['DUPERSID', 'EVNTIDX', 'AMBTOTEV', 'AMBFAMEV', 'VISTYPE']],
    op_asthma[['DUPERSID', 'EVNTIDX', 'AMBTOTEV', 'AMBFAMEV', 'VISTYPE']],
    er_asthma[['DUPERSID', 'EVNTIDX', 'AMBTOTEV', 'AMBFAMEV', 'VISTYPE']],
    pm[['DUPERSID', 'EVNTIDX', 'AMBTOTEV', 'AMBFAMEV', 'VISTYPE']]
], ignore_index=True)

print("\nFrequency of Ambulatory Visits for Asthma, by Type of Event:")
for vistype in ['ob', 'op', 'er', 'pm']:
    count = len(allevnt[allevnt['VISTYPE'] == vistype])
    print(f"  {vistype_labels[vistype]}: {count:,}")

print(f"\nTotal events: {len(allevnt):,}")

perev = allevnt.groupby('DUPERSID').agg({
    'AMBTOTEV': 'sum',
    'AMBFAMEV': 'sum'
}).reset_index()
perev.columns = ['DUPERSID', 'AMBTOTPD', 'AMBFAMPD']

pers = perev.merge(fyc, on='DUPERSID', how='inner')

def get_age(row):
    if row['AGE53X'] >= 0:
        return row['AGE53X']
    elif row['AGE42X'] >= 0:
        return row['AGE42X']
    elif row['AGE31X'] >= 0:
        return row['AGE31X']
    return np.nan

pers['AGE'] = pers.apply(get_age, axis=1)

print("\n" + "-" * 80)
print("Average Expenditures per Person -- Total and Paid by Family")
print("-" * 80)

def age_category(age):
    if pd.isna(age) or age < 0:
        return 'Unknown'
    elif age <= 4:
        return '0-4'
    elif age <= 17:
        return '5-17'
    elif age <= 24:
        return '18-24'
    elif age <= 44:
        return '25-44'
    elif age <= 64:
        return '45-64'
    else:
        return '65-90'

pers['AGECAT'] = pers['AGE'].apply(age_category)

print("\nBy Age Group:")
for agecat in ['0-4', '5-17', '18-24', '25-44', '45-64', '65-90']:
    subset = pers[pers['AGECAT'] == agecat]
    if len(subset) > 0:
        mean_tot = np.average(subset['AMBTOTPD'], weights=subset['PERWT01F'])
        mean_fam = np.average(subset['AMBFAMPD'], weights=subset['PERWT01F'])
        print(f"  {agecat}: Total=${mean_tot:,.2f}, Family=${mean_fam:,.2f}")

print("\nBy Sex:")
for sex in [1, 2]:
    subset = pers[pers['SEX'] == sex]
    if len(subset) > 0:
        mean_tot = np.average(subset['AMBTOTPD'], weights=subset['PERWT01F'])
        mean_fam = np.average(subset['AMBFAMPD'], weights=subset['PERWT01F'])
        print(f"  {sex_labels[sex]}: Total=${mean_tot:,.2f}, Family=${mean_fam:,.2f}")

print("\nBy Race/Ethnicity:")
for race in [1, 2, 3]:
    subset = pers[pers['RACETHNX'] == race]
    if len(subset) > 0:
        mean_tot = np.average(subset['AMBTOTPD'], weights=subset['PERWT01F'])
        mean_fam = np.average(subset['AMBFAMPD'], weights=subset['PERWT01F'])
        print(f"  {racethnx_labels.get(race, 'Other')}: Total=${mean_tot:,.2f}, Family=${mean_fam:,.2f}")
