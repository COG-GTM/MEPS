"""
AHRQ MEPS Data Users Workshop - Estimation Example E8

This program generates two sets of expenditure data for 2005 inpatient stays,
similar to those reported in MEPS Stat Brief #164 (Figures 1 and 5).

Estimates include:
- Distribution by event type (Ambulatory, Hospital, Prescribed Medicines, Other)
- Distribution of inpatient expenses by source of payment
- Average IP expenses per stay with and without surgery
- Average IP expenses per diem with and without surgery

Input files:
    - h97.sas7bdat (2005 Full-Year File)
    - h94d.sas7bdat (2005 Hospital IP Stays)

Python equivalent of: SAS/older_exercises_1996_to_2006/Estimation_examples/E8/E8.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS/DATA")
    
    print("=" * 80)
    print("AHRQ MEPS DATA USERS WORKSHOP")
    print("HEALTHCARE EXPENSES, 2005 (CF. MEPS STAT BRIEF #164)")
    print("=" * 80)
    
    # Load FYC file
    fyc_file = data_dir / "h97.sas7bdat"
    print(f"\nLoading FYC data from: {fyc_file}")
    
    puf97 = load_sas_data(fyc_file, columns=[
        'TOTEXP05', 'RXEXP05', 'OBVEXP05', 'OPDEXP05', 'OPFEXP05',
        'ERDEXP05', 'ERFEXP05', 'IPDEXP05', 'IPFEXP05',
        'IPDPRV05', 'IPFPRV05', 'IPDTRI05', 'IPFTRI05',
        'IPDMCR05', 'IPFMCR05', 'IPDMCD05', 'IPFMCD05',
        'IPDSLF05', 'IPFSLF05', 'VARSTR', 'VARPSU', 'PERWT05F'
    ])
    
    print(f"Total records: {len(puf97):,}")
    
    # Define expenditure variables by event type
    puf97['TOTAL'] = puf97['TOTEXP05']
    puf97['PRESCRIBED_MEDICINES'] = puf97['RXEXP05']
    puf97['HOSPITAL_INPATIENT'] = puf97['IPDEXP05'] + puf97['IPFEXP05']
    puf97['AMBULATORY_CARE'] = (puf97['OBVEXP05'] + puf97['OPDEXP05'] + 
                                puf97['OPFEXP05'] + puf97['ERDEXP05'] + puf97['ERFEXP05'])
    puf97['OTHER'] = puf97['TOTAL'] - (puf97['PRESCRIBED_MEDICINES'] + 
                                        puf97['HOSPITAL_INPATIENT'] + puf97['AMBULATORY_CARE'])
    
    # Define IP expenses by source of payment
    puf97['IP_TOTAL'] = puf97['HOSPITAL_INPATIENT']
    puf97['IP_PRIVATE_INS'] = (puf97['IPDPRV05'] + puf97['IPFPRV05'] + 
                               puf97['IPDTRI05'] + puf97['IPFTRI05'])
    puf97['IP_MEDICARE'] = puf97['IPDMCR05'] + puf97['IPFMCR05']
    puf97['IP_MEDICAID'] = puf97['IPDMCD05'] + puf97['IPFMCD05']
    puf97['IP_OUT_OF_POCKET'] = puf97['IPDSLF05'] + puf97['IPFSLF05']
    puf97['IP_OTHER'] = puf97['IP_TOTAL'] - (puf97['IP_PRIVATE_INS'] + puf97['IP_MEDICARE'] + 
                                              puf97['IP_MEDICAID'] + puf97['IP_OUT_OF_POCKET'])
    
    # Calculate estimates
    design = SurveyDesign(
        data=puf97,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT05F'
    )
    
    # Figure 1: Distribution by event type
    print("\n" + "=" * 80)
    print("FIGURE 1: DISTRIBUTION BY EVENT TYPE")
    print("=" * 80)
    
    total_result = survey_total(design, 'TOTAL')
    total_exp = total_result['total'].values[0]
    
    print(f"\nTotal Healthcare Expenditures: ${total_exp:,.0f}")
    
    event_vars = [
        ('PRESCRIBED_MEDICINES', 'Prescribed Medicines'),
        ('HOSPITAL_INPATIENT', 'Hospital Inpatient'),
        ('AMBULATORY_CARE', 'Ambulatory Care'),
        ('OTHER', 'Other')
    ]
    
    print(f"\n{'Event Type':<25} {'Total Exp':>18} {'% of Total':>12}")
    print("-" * 60)
    
    for var, label in event_vars:
        result = survey_total(design, var)
        exp = result['total'].values[0]
        pct = exp / total_exp * 100 if total_exp > 0 else 0
        print(f"{label:<25} ${exp:>17,.0f} {pct:>11.1f}%")
    
    # Figure 1: Distribution of IP expenses by source of payment
    print("\n" + "=" * 80)
    print("FIGURE 1: DISTRIBUTION OF INPATIENT EXPENSES BY SOURCE OF PAYMENT")
    print("=" * 80)
    
    ip_total_result = survey_total(design, 'IP_TOTAL')
    ip_total = ip_total_result['total'].values[0]
    
    print(f"\nTotal IP Expenditures: ${ip_total:,.0f}")
    
    sop_vars = [
        ('IP_PRIVATE_INS', 'Private Insurance'),
        ('IP_MEDICARE', 'Medicare'),
        ('IP_MEDICAID', 'Medicaid'),
        ('IP_OUT_OF_POCKET', 'Out-of-Pocket'),
        ('IP_OTHER', 'Other')
    ]
    
    print(f"\n{'Source of Payment':<25} {'Total Exp':>18} {'% of Total':>12}")
    print("-" * 60)
    
    for var, label in sop_vars:
        result = survey_total(design, var)
        exp = result['total'].values[0]
        pct = exp / ip_total * 100 if ip_total > 0 else 0
        print(f"{label:<25} ${exp:>17,.0f} {pct:>11.1f}%")
    
    # Load IP stays file
    print("\n" + "=" * 80)
    print("FIGURE 5: AVERAGE IP EXPENSES PER STAY AND PER DIEM")
    print("=" * 80)
    
    ip_file = data_dir / "h94d.sas7bdat"
    print(f"\nLoading IP stays data from: {ip_file}")
    
    ip2005 = load_sas_data(ip_file, columns=[
        'DUPERSID', 'EVNTIDX', 'RSNINHOS', 'IPXP05X', 'NUMNIGHX',
        'PERWT05F', 'VARSTR', 'VARPSU'
    ])
    
    print(f"Total IP stay records: {len(ip2005):,}")
    
    # For zero night stays, consider length of stay as 1
    ip2005['NUMNIGHX'] = np.where(ip2005['NUMNIGHX'] == 0, 1, ip2005['NUMNIGHX'])
    
    # Calculate per diem
    ip2005['PERDIEM'] = np.round(ip2005['IPXP05X'] / ip2005['NUMNIGHX'])
    
    # Average IP expenses per stay with and without surgery
    print("\n" + "-" * 60)
    print("AVERAGE IP EXPENSES PER STAY")
    print("-" * 60)
    
    for rsn, label in [(1, 'With Surgery'), (2, 'Without Surgery')]:
        if rsn == 1:
            subset = ip2005[ip2005['RSNINHOS'] == 1].copy()
        else:
            subset = ip2005[ip2005['RSNINHOS'] != 1].copy()
        
        if len(subset) > 0:
            design_ip = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT05F'
            )
            
            mean_result = survey_mean(design_ip, 'IPXP05X')
            print(f"\n{label}:")
            print(f"  N: {len(subset):,}")
            print(f"  Mean expense per stay: ${mean_result['mean'].values[0]:,.0f}")
            print(f"  SE: ${mean_result['se'].values[0]:.0f}")
    
    # Average IP expenses per diem with and without surgery
    print("\n" + "-" * 60)
    print("AVERAGE IP EXPENSES PER DIEM")
    print("-" * 60)
    
    for rsn, label in [(1, 'With Surgery'), (2, 'Without Surgery')]:
        if rsn == 1:
            subset = ip2005[ip2005['RSNINHOS'] == 1].copy()
        else:
            subset = ip2005[ip2005['RSNINHOS'] != 1].copy()
        
        if len(subset) > 0:
            design_ip = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT05F'
            )
            
            mean_result = survey_mean(design_ip, 'PERDIEM')
            print(f"\n{label}:")
            print(f"  N: {len(subset):,}")
            print(f"  Mean expense per diem: ${mean_result['mean'].values[0]:,.0f}")
            print(f"  SE: ${mean_result['se'].values[0]:.0f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
