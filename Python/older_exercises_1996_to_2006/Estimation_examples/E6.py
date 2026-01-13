"""
AHRQ MEPS Data Users Workshop - Estimation Example E6

This program generates estimates for 2005 percentage distribution of health
care spending, by type of service, for the U.S. civilian noninstitutionalized
population (as referenced in MEPS Stat Brief #193).

Type of service categories:
    - Hospital Inpatient
    - Office-Based Visits
    - Prescribed Medicines
    - Hospital Outpatient
    - Dental Visits
    - Emergency Room
    - Home Health Care (Agency & Non-Agency)
    - Other

Note: Expenses include both facility and physician expenses.

Input file: h97.sas7bdat (2005 Full-Year File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Estimation_examples/E6/E6.sas
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
    print("HEALTHCARE SPENDING, 2005 (MEPS STAT BRIEF #193)")
    print("=" * 80)
    
    # Load FYC file
    fyc_file = data_dir / "h97.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    puf97 = load_sas_data(fyc_file, columns=[
        'TOTEXP05', 'IPDEXP05', 'IPFEXP05', 'OBVEXP05', 'RXEXP05',
        'OPDEXP05', 'OPFEXP05', 'DVTEXP05', 'ERDEXP05', 'ERFEXP05',
        'HHAEXP05', 'HHNEXP05', 'OTHEXP05', 'VARSTR', 'VARPSU', 'PERWT05F'
    ])
    
    # Subset to persons with positive weight
    puf97 = puf97[puf97['PERWT05F'] > 0].copy()
    
    print(f"Total records with positive weight: {len(puf97):,}")
    
    # Define expenditure variables by type of service
    puf97['TOTAL'] = puf97['TOTEXP05']
    puf97['HOSPITAL_INPATIENT'] = puf97['IPDEXP05'] + puf97['IPFEXP05']
    puf97['OFFICE_BASED'] = puf97['OBVEXP05']
    puf97['PRESCRIBED_MEDICINES'] = puf97['RXEXP05']
    puf97['HOSPITAL_OUTPATIENT'] = puf97['OPDEXP05'] + puf97['OPFEXP05']
    puf97['DENTAL'] = puf97['DVTEXP05']
    puf97['EMERGENCY_ROOM'] = puf97['ERDEXP05'] + puf97['ERFEXP05']
    puf97['HOME_HEALTH'] = puf97['HHAEXP05'] + puf97['HHNEXP05']
    puf97['OTHER'] = (puf97['TOTAL'] - puf97['HOSPITAL_INPATIENT'] - puf97['OFFICE_BASED'] - 
                      puf97['PRESCRIBED_MEDICINES'] - puf97['HOSPITAL_OUTPATIENT'] - 
                      puf97['DENTAL'] - puf97['EMERGENCY_ROOM'] - puf97['HOME_HEALTH'])
    
    # Create flag variables for persons with an expense
    expense_vars = ['TOTAL', 'HOSPITAL_INPATIENT', 'OFFICE_BASED', 'PRESCRIBED_MEDICINES',
                    'HOSPITAL_OUTPATIENT', 'DENTAL', 'EMERGENCY_ROOM', 'HOME_HEALTH', 'OTHER']
    
    for var in expense_vars:
        puf97[f'X_{var}'] = (puf97[var] > 0).astype(int)
    
    # Calculate estimates
    design = SurveyDesign(
        data=puf97,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT05F'
    )
    
    # Figure 1: Distribution by type of service
    print("\n" + "=" * 80)
    print("FIGURE 1: DISTRIBUTION BY TYPE OF SERVICE")
    print("=" * 80)
    
    # Calculate totals for each type of service
    service_vars = ['HOSPITAL_INPATIENT', 'OFFICE_BASED', 'PRESCRIBED_MEDICINES',
                    'HOSPITAL_OUTPATIENT', 'DENTAL', 'EMERGENCY_ROOM', 'HOME_HEALTH', 'OTHER']
    
    total_result = survey_total(design, 'TOTAL')
    total_exp = total_result['total'].values[0]
    
    print(f"\nTotal Healthcare Expenditures: ${total_exp:,.0f}")
    print(f"\n{'Type of Service':<25} {'Total Exp':>18} {'% of Total':>12}")
    print("-" * 60)
    
    for var in service_vars:
        result = survey_total(design, var)
        exp = result['total'].values[0]
        pct = exp / total_exp * 100 if total_exp > 0 else 0
        label = var.replace('_', ' ').title()
        print(f"{label:<25} ${exp:>17,.0f} {pct:>11.1f}%")
    
    # Figure 2: Percentage of persons with an expense
    print("\n" + "=" * 80)
    print("FIGURE 2: PERCENTAGE OF PERSONS WITH AN EXPENSE, BY TYPE OF SERVICE")
    print("=" * 80)
    
    print(f"\n{'Type of Service':<25} {'% with Expense':>15} {'SE':>10}")
    print("-" * 55)
    
    # Any service
    mean_any = survey_mean(design, 'X_TOTAL')
    print(f"{'Any Service':<25} {mean_any['mean'].values[0]*100:>14.1f}% {mean_any['se'].values[0]*100:>9.2f}")
    
    for var in service_vars:
        mean_result = survey_mean(design, f'X_{var}')
        label = var.replace('_', ' ').title()
        print(f"{label:<25} {mean_result['mean'].values[0]*100:>14.1f}% {mean_result['se'].values[0]*100:>9.2f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
