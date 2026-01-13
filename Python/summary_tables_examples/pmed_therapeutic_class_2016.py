"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Prescribed drugs, 2016

Purchases and expenditures by Multum therapeutic class name (TC1):
    - Number of people with purchase
    - Total purchases
    - Total expenditures

Input file: h188a.ssp (2016 RX event file)

Python equivalent of: SAS/summary_tables_examples/pmed_therapeutic_class_2016.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_total


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS")
    
    print("=" * 80)
    print("PRESCRIBED DRUGS, 2016")
    print("Purchases and Expenditures by Therapeutic Class")
    print("=" * 80)
    
    # Define therapeutic class labels
    tc1_labels = {
        -9: 'Not ascertained',
        -1: 'Inapplicable',
        1: 'Anti-infectives',
        19: 'Antihyperlipidemic agents',
        20: 'Antineoplastics',
        28: 'Biologicals',
        40: 'Cardiovascular agents',
        57: 'Central nervous system agents',
        81: 'Coagulation modifiers',
        87: 'Gastrointestinal agents',
        97: 'Hormones/hormone modifiers',
        105: 'Miscellaneous agents',
        113: 'Genitourinary tract agents',
        115: 'Nutritional products',
        122: 'Respiratory agents',
        133: 'Topical agents',
        218: 'Alternative medicines',
        242: 'Psychotherapeutic agents',
        254: 'Immunologic agents',
        358: 'Metabolic agents'
    }
    
    # Load RX file
    rx_file = data_dir / "h188a.ssp"
    print(f"\nLoading data from: {rx_file}")
    
    rx = load_sas_data(rx_file)
    print(f"Total RX records: {len(rx):,}")
    
    # Aggregate to person-level by therapeutic class
    print("\n" + "-" * 60)
    print("AGGREGATING TO PERSON-LEVEL BY THERAPEUTIC CLASS")
    print("-" * 60)
    
    tc1_pers = rx.groupby(['DUPERSID', 'VARSTR', 'VARPSU', 'PERWT16F', 'TC1']).agg(
        pers_RXXP=('RXXP16X', 'sum'),
        n_purchases=('RXXP16X', 'count')
    ).reset_index()
    
    tc1_pers['PERSON'] = 1
    
    print(f"Person-TC1 records: {len(tc1_pers):,}")
    
    # Calculate estimates by therapeutic class
    print("\n" + "=" * 80)
    print("ESTIMATES BY THERAPEUTIC CLASS")
    print("=" * 80)
    
    # Get unique therapeutic classes
    tc1_values = sorted(tc1_pers['TC1'].unique())
    
    results = []
    for tc1 in tc1_values:
        tc1_data = tc1_pers[tc1_pers['TC1'] == tc1].copy()
        
        if len(tc1_data) > 0:
            design = SurveyDesign(
                data=tc1_data,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT16F'
            )
            
            # Number of people with purchase
            people_result = survey_total(design, 'PERSON')
            
            # Total purchases
            purchases_result = survey_total(design, 'n_purchases')
            
            # Total expenditures
            exp_result = survey_total(design, 'pers_RXXP')
            
            tc1_label = tc1_labels.get(int(tc1), f'TC1={int(tc1)}')
            
            results.append({
                'TC1': int(tc1),
                'Label': tc1_label,
                'People': people_result['total'].values[0],
                'People_SE': people_result['se'].values[0],
                'Purchases': purchases_result['total'].values[0],
                'Purchases_SE': purchases_result['se'].values[0],
                'Expenditures': exp_result['total'].values[0],
                'Expenditures_SE': exp_result['se'].values[0]
            })
    
    # Sort by total expenditures
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('Expenditures', ascending=False)
    
    print("\n" + "-" * 100)
    print(f"{'Therapeutic Class':<35} {'# People':>15} {'Total Purchases':>18} {'Total Expenditures':>20}")
    print("-" * 100)
    
    for idx, row in results_df.iterrows():
        if row['TC1'] > 0:  # Skip negative values
            print(f"{row['Label']:<35} {row['People']:>15,.0f} {row['Purchases']:>18,.0f} ${row['Expenditures']:>19,.0f}")
    
    # Summary statistics
    print("\n" + "-" * 60)
    print("SUMMARY")
    print("-" * 60)
    
    valid_results = results_df[results_df['TC1'] > 0]
    print(f"\nTotal therapeutic classes: {len(valid_results):,}")
    print(f"Total people with purchases: {valid_results['People'].sum():,.0f}")
    print(f"Total purchases: {valid_results['Purchases'].sum():,.0f}")
    print(f"Total expenditures: ${valid_results['Expenditures'].sum():,.0f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
