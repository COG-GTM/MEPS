"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Accessibility and quality of care: Quality of Care, 2016

Self-administered questionnaire (SAQ):
    - Number/percent of adults by ability to schedule a routine appointment
    - By insurance coverage status

Input file: h192.ssp (2016 full-year consolidated)

Python equivalent of: SAS/summary_tables_examples/care_quality_2016.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_freq


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS")
    
    print("=" * 80)
    print("ACCESSIBILITY AND QUALITY OF CARE: QUALITY OF CARE, 2016")
    print("Ability to Schedule a Routine Appointment (Adults)")
    print("=" * 80)
    
    # Load FYC file
    fyc_file = data_dir / "h192.ssp"
    print(f"\nLoading data from: {fyc_file}")
    
    meps = load_sas_data(fyc_file)
    
    # Define domain - adults who made an appointment
    meps['DOMAIN'] = ((meps['ADRTCR42'] == 1) & (meps['AGELAST'] >= 18)).astype(int)
    
    # Adjust weights so observations aren't dropped
    meps.loc[(meps['DOMAIN'] == 0) & (meps['SAQWT16F'] == 0), 'SAQWT16F'] = 1
    
    # Define labels
    freq_labels = {
        4: 'Always',
        3: 'Usually',
        2: 'Sometimes/Never',
        1: 'Sometimes/Never',
        -7: "Don't know/Non-response",
        -8: "Don't know/Non-response",
        -9: "Don't know/Non-response",
        -1: 'Inapplicable'
    }
    
    insurance_labels = {
        1: '<65, Any private',
        2: '<65, Public only',
        3: '<65, Uninsured',
        4: '65+, Medicare only',
        5: '65+, Medicare and private',
        6: '65+, Medicare and other public',
        7: '65+, No medicare',
        8: '65+, No medicare'
    }
    
    # Calculate estimates
    print("\n" + "=" * 80)
    print("ABILITY TO SCHEDULE A ROUTINE APPOINTMENT (ADULTS)")
    print("By Insurance Coverage Status")
    print("=" * 80)
    
    # Subset to domain (adults who made an appointment)
    domain_data = meps[meps['DOMAIN'] == 1].copy()
    
    print(f"\nN (unweighted): {len(domain_data):,}")
    
    # Overall distribution
    print("\n" + "-" * 60)
    print("OVERALL DISTRIBUTION")
    print("-" * 60)
    
    design = SurveyDesign(
        data=domain_data,
        strata='VARSTR',
        cluster='VARPSU',
        weight='SAQWT16F'
    )
    
    freq_result = survey_freq(design, 'ADRTWW42')
    
    print(f"\n{'Response':<30} {'Count':>15} {'Percent':>10}")
    print("-" * 60)
    
    for idx, row in freq_result.iterrows():
        level = row['level']
        label = freq_labels.get(int(level), str(level)) if pd.notna(level) else 'Missing'
        print(f"{label:<30} {row['count']:>15,.0f} {row['proportion']*100:>9.2f}%")
    
    # By insurance coverage status
    print("\n" + "-" * 60)
    print("BY INSURANCE COVERAGE STATUS")
    print("-" * 60)
    
    # Get unique insurance categories
    ins_cats = sorted(domain_data['INSURC16'].dropna().unique())
    
    for ins_val in ins_cats:
        if ins_val > 0:  # Skip negative values
            ins_label = insurance_labels.get(int(ins_val), f'Insurance {int(ins_val)}')
            subset = domain_data[domain_data['INSURC16'] == ins_val].copy()
            
            if len(subset) > 0:
                design_ins = SurveyDesign(
                    data=subset,
                    strata='VARSTR',
                    cluster='VARPSU',
                    weight='SAQWT16F'
                )
                
                freq_result = survey_freq(design_ins, 'ADRTWW42')
                
                print(f"\n{ins_label}:")
                print(f"  N: {len(subset):,}")
                
                for idx, row in freq_result.iterrows():
                    level = row['level']
                    if pd.notna(level) and int(level) > 0:  # Only show valid responses
                        label = freq_labels.get(int(level), str(level))
                        print(f"  {label}: {row['count']:,.0f} ({row['proportion']*100:.2f}%)")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
