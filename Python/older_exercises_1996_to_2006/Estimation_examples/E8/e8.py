import pandas as pd
import numpy as np
import sys
sys.path.append('../../../')
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total

data_path = '../../../data'

print("=" * 80)
print("AHRQ MEPS DATA USERS WORKSHOP -- SEPTEMBER 2008")
print("HEALTHCARE EXPENSES, 2005 (CF. MEPS STAT BRIEF #164)")
print("=" * 80)

fyc = load_sas_data(f'{data_path}/h97.sas7bdat', columns=[
    'TOTEXP05', 'RXEXP05', 'OBVEXP05', 'OPDEXP05', 'OPFEXP05',
    'ERDEXP05', 'ERFEXP05', 'IPDEXP05', 'IPFEXP05',
    'IPDPRV05', 'IPFPRV05', 'IPDTRI05', 'IPFTRI05',
    'IPDMCR05', 'IPFMCR05', 'IPDMCD05', 'IPFMCD05',
    'IPDSLF05', 'IPFSLF05',
    'VARSTR', 'VARPSU', 'PERWT05F'
])

fyc['TOTAL'] = fyc['TOTEXP05']
fyc['PRESCRIBED_MEDICINES'] = fyc['RXEXP05']
fyc['HOSPITAL_INPATIENT'] = fyc['IPDEXP05'] + fyc['IPFEXP05']
fyc['AMBULATORY_CARE'] = fyc['OBVEXP05'] + fyc['OPDEXP05'] + fyc['OPFEXP05'] + fyc['ERDEXP05'] + fyc['ERFEXP05']
fyc['OTHER'] = fyc['TOTAL'] - (fyc['PRESCRIBED_MEDICINES'] + fyc['HOSPITAL_INPATIENT'] + fyc['AMBULATORY_CARE'])

fyc['IP_TOTAL'] = fyc['HOSPITAL_INPATIENT']
fyc['IP_PRIVATE_INS'] = (fyc['IPDPRV05'] + fyc['IPFPRV05']) + (fyc['IPDTRI05'] + fyc['IPFTRI05'])
fyc['IP_MEDICARE'] = fyc['IPDMCR05'] + fyc['IPFMCR05']
fyc['IP_MEDICAID'] = fyc['IPDMCD05'] + fyc['IPFMCD05']
fyc['IP_OUT_OF_POCKET'] = fyc['IPDSLF05'] + fyc['IPFSLF05']
fyc['IP_OTHER'] = fyc['IP_TOTAL'] - (fyc['IP_PRIVATE_INS'] + fyc['IP_MEDICARE'] + fyc['IP_MEDICAID'] + fyc['IP_OUT_OF_POCKET'])

design = SurveyDesign(fyc, strata='VARSTR', cluster='VARPSU', weight='PERWT05F')

print("\n" + "-" * 80)
print("FIGURE 1: DISTRIBUTION BY EVENT TYPE")
print("-" * 80)

result_total = survey_total(design, 'TOTAL')
total_exp = result_total['total']

print(f"\nTotal Healthcare Expenditures: ${total_exp:,.0f}")

event_vars = ['PRESCRIBED_MEDICINES', 'HOSPITAL_INPATIENT', 'AMBULATORY_CARE', 'OTHER']
event_labels = {
    'PRESCRIBED_MEDICINES': 'Prescribed Medicines',
    'HOSPITAL_INPATIENT': 'Hospital Inpatient',
    'AMBULATORY_CARE': 'Ambulatory Care',
    'OTHER': 'Other'
}

print("\nDistribution by Event Type:")
print("-" * 50)

for var in event_vars:
    result = survey_total(design, var)
    pct = (result['total'] / total_exp) * 100
    print(f"  {event_labels[var]:25s}: ${result['total']:>15,.0f} ({pct:5.1f}%)")

print("\n" + "-" * 80)
print("FIGURE 1: DISTRIBUTION OF INPATIENT (IP) EXPENSES BY SOURCE OF PAYMENT")
print("-" * 80)

result_ip_total = survey_total(design, 'IP_TOTAL')
ip_total_exp = result_ip_total['total']

print(f"\nTotal IP Expenditures: ${ip_total_exp:,.0f}")

ip_sop_vars = ['IP_PRIVATE_INS', 'IP_MEDICARE', 'IP_MEDICAID', 'IP_OUT_OF_POCKET', 'IP_OTHER']
ip_sop_labels = {
    'IP_PRIVATE_INS': 'Private Insurance',
    'IP_MEDICARE': 'Medicare',
    'IP_MEDICAID': 'Medicaid',
    'IP_OUT_OF_POCKET': 'Out-of-Pocket',
    'IP_OTHER': 'Other'
}

print("\nDistribution by Source of Payment:")
print("-" * 50)

for var in ip_sop_vars:
    result = survey_total(design, var)
    pct = (result['total'] / ip_total_exp) * 100 if ip_total_exp > 0 else 0
    print(f"  {ip_sop_labels[var]:25s}: ${result['total']:>15,.0f} ({pct:5.1f}%)")

print("\n" + "-" * 80)
print("FIGURE 5: AVERAGE IP EXPENSES PER STAY WITH AND WITHOUT SURGERY")
print("-" * 80)

ip2005 = load_sas_data(f'{data_path}/h94d.sas7bdat', columns=[
    'DUPERSID', 'EVNTIDX', 'RSNINHOS', 'IPXP05X', 'NUMNIGHX',
    'PERWT05F', 'VARSTR', 'VARPSU'
])

ip2005['NUMNIGHX'] = ip2005['NUMNIGHX'].apply(lambda x: 1 if x == 0 else x)
ip2005['PERDIEM'] = np.round(ip2005['IPXP05X'] / ip2005['NUMNIGHX'])

surg_labels = {1: 'With Surgery', 'other': 'Without Surgery'}

print("\nAverage IP Expenses per Stay:")
for rsn in [1]:
    subset_surg = ip2005[ip2005['RSNINHOS'] == rsn]
    subset_other = ip2005[ip2005['RSNINHOS'] != rsn]
    
    if len(subset_surg) > 0:
        design_surg = SurveyDesign(subset_surg, strata='VARSTR', cluster='VARPSU', weight='PERWT05F')
        result_surg = survey_mean(design_surg, 'IPXP05X')
        print(f"  With Surgery: ${result_surg['mean']:,.0f} (SE: ${result_surg['se']:,.0f})")
    
    if len(subset_other) > 0:
        design_other = SurveyDesign(subset_other, strata='VARSTR', cluster='VARPSU', weight='PERWT05F')
        result_other = survey_mean(design_other, 'IPXP05X')
        print(f"  Without Surgery: ${result_other['mean']:,.0f} (SE: ${result_other['se']:,.0f})")

print("\nAverage IP Expenses per Diem:")
for rsn in [1]:
    subset_surg = ip2005[ip2005['RSNINHOS'] == rsn]
    subset_other = ip2005[ip2005['RSNINHOS'] != rsn]
    
    if len(subset_surg) > 0:
        design_surg = SurveyDesign(subset_surg, strata='VARSTR', cluster='VARPSU', weight='PERWT05F')
        result_surg = survey_mean(design_surg, 'PERDIEM')
        print(f"  With Surgery: ${result_surg['mean']:,.0f} (SE: ${result_surg['se']:,.0f})")
    
    if len(subset_other) > 0:
        design_other = SurveyDesign(subset_other, strata='VARSTR', cluster='VARPSU', weight='PERWT05F')
        result_other = survey_mean(design_other, 'PERDIEM')
        print(f"  Without Surgery: ${result_other['mean']:,.0f} (SE: ${result_other['se']:,.0f})")
