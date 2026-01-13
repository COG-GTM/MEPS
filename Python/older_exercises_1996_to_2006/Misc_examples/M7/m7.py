import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP -- JULY 2006")
print("PERSON LEVEL PRESCRIBED MEDICINE EXPENDITURES")
print("=" * 80)

agecat_labels = {1: 'UNDER 18', 2: '18 - 64', 3: '65 AND OLDER'}
racethn_labels = {1: 'HISPANIC', 2: 'BLACK', 3: 'ASIAN', 4: 'OTHER'}
inscov_labels = {1: 'ANY PRIVATE', 2: 'PUBLIC ONLY', 3: 'UNINSURED'}

print("\n" + "-" * 80)
print("Identify Persons with at Least One PMED Event")
print("-" * 80)

rx = load_sas_data(f'{data_path}/h77a.sas7bdat', columns=['DUPERSID'])
rx_pers = rx.drop_duplicates(subset=['DUPERSID'])

print(f"\nPersons with PMED events: {len(rx_pers):,}")

fyc = load_sas_data(f'{data_path}/h79.sas7bdat', columns=[
    'DUPERSID', 'AGE03X', 'AGE53X', 'AGE42X', 'AGE31X',
    'RXEXP03', 'RXMCD03', 'RXMCR03', 'RXPRV03', 'RXSLF03',
    'RACETHNX', 'PERWT03F', 'VARSTR', 'VARPSU', 'INSCOV03'
])

def get_age(row):
    if row['AGE03X'] >= 0:
        return row['AGE03X']
    elif row['AGE53X'] >= 0:
        return row['AGE53X']
    elif row['AGE42X'] >= 0:
        return row['AGE42X']
    elif row['AGE31X'] >= 0:
        return row['AGE31X']
    return row['AGE03X']

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

fyc['OTHER'] = fyc['RXEXP03'] - (fyc['RXMCD03'] + fyc['RXMCR03'] + fyc['RXPRV03'] + fyc['RXSLF03'])

fyc['RXEXP03X'] = fyc['RXEXP03'] / 1000
fyc['RXMCD03X'] = fyc['RXMCD03'] / 1000
fyc['RXMCR03X'] = fyc['RXMCR03'] / 1000
fyc['RXPRV03X'] = fyc['RXPRV03'] / 1000
fyc['RXSLF03X'] = fyc['RXSLF03'] / 1000
fyc['OTHERX'] = fyc['OTHER'] / 1000

puf79 = fyc.merge(rx_pers, on='DUPERSID', how='inner')

print(f"Persons with PMED events in FYC: {len(puf79):,}")

print("\n" + "-" * 80)
print("Total PMED Expenditures")
print("-" * 80)

design = SurveyDesign(puf79, strata='VARSTR', cluster='VARPSU', weight='PERWT03F')

result = survey_mean(design, 'RXEXP03')
result_total = survey_total(design, 'RXEXP03')

print(f"\nMean PMED Expenditure: ${result['mean']:,.2f}")
print(f"Std Error: ${result['se']:,.2f}")
print(f"Total PMED Expenditure: ${result_total['total']:,.0f}")

print("\n" + "-" * 80)
print("2003 TOTAL PMED EXPENDITURES (Dollars in Thousands)")
print("-" * 80)

print("\n{:<25} {:>12} {:>12} {:>12} {:>12} {:>12} {:>12}".format(
    'Category', 'Total', 'OOP', 'Private', 'Medicare', 'Medicaid', 'Other'))
print("-" * 100)

total_exp = (puf79['RXEXP03X'] * puf79['PERWT03F']).sum()
total_slf = (puf79['RXSLF03X'] * puf79['PERWT03F']).sum()
total_prv = (puf79['RXPRV03X'] * puf79['PERWT03F']).sum()
total_mcr = (puf79['RXMCR03X'] * puf79['PERWT03F']).sum()
total_mcd = (puf79['RXMCD03X'] * puf79['PERWT03F']).sum()
total_oth = (puf79['OTHERX'] * puf79['PERWT03F']).sum()

print("{:<25} ${:>11,.0f} ${:>11,.0f} ${:>11,.0f} ${:>11,.0f} ${:>11,.0f} ${:>11,.0f}".format(
    'TOTAL', total_exp, total_slf, total_prv, total_mcr, total_mcd, total_oth))

for agecat in [1, 2, 3]:
    subset = puf79[puf79['AGECAT'] == agecat]
    if len(subset) > 0:
        exp = (subset['RXEXP03X'] * subset['PERWT03F']).sum()
        slf = (subset['RXSLF03X'] * subset['PERWT03F']).sum()
        prv = (subset['RXPRV03X'] * subset['PERWT03F']).sum()
        mcr = (subset['RXMCR03X'] * subset['PERWT03F']).sum()
        mcd = (subset['RXMCD03X'] * subset['PERWT03F']).sum()
        oth = (subset['OTHERX'] * subset['PERWT03F']).sum()
        print("{:<25} ${:>11,.0f} ${:>11,.0f} ${:>11,.0f} ${:>11,.0f} ${:>11,.0f} ${:>11,.0f}".format(
            agecat_labels[agecat], exp, slf, prv, mcr, mcd, oth))

print("\n" + "-" * 80)
print("2003 MEAN PMED EXPENDITURES")
print("-" * 80)

print("\n{:<25} {:>12} {:>12} {:>12} {:>12} {:>12} {:>12}".format(
    'Category', 'Total', 'OOP', 'Private', 'Medicare', 'Medicaid', 'Other'))
print("-" * 100)

for var, label in [('RXEXP03', 'Total'), ('RXSLF03', 'OOP'), ('RXPRV03', 'Private'), 
                   ('RXMCR03', 'Medicare'), ('RXMCD03', 'Medicaid'), ('OTHER', 'Other')]:
    mean_val = np.average(puf79[var], weights=puf79['PERWT03F'])
    print(f"  {label}: ${mean_val:,.2f}")

print("\nBy Age Category:")
for agecat in [1, 2, 3]:
    subset = puf79[puf79['AGECAT'] == agecat]
    if len(subset) > 0:
        mean_exp = np.average(subset['RXEXP03'], weights=subset['PERWT03F'])
        print(f"  {agecat_labels[agecat]}: ${mean_exp:,.2f}")
