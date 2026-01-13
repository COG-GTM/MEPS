"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Prescribed drugs, 2016

Purchases and expenditures by generic drug name (RXDRGNAM):
    - Number of people with purchase
    - Total purchases
    - Total expenditures

Input file: h188a.ssp (2016 RX event file)

Python equivalent of: SAS/summary_tables_examples/pmed_prescribed_drug_2016.sas
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
    print("Purchases and Expenditures by Generic Drug Name")
    print("=" * 80)
    
    # Load RX file
    rx_file = data_dir / "h188a.ssp"
    print(f"\nLoading data from: {rx_file}")
    
    rx = load_sas_data(rx_file)
    print(f"Total RX records: {len(rx):,}")
    
    # Aggregate to person-level by drug name
    print("\n" + "-" * 60)
    print("AGGREGATING TO PERSON-LEVEL BY DRUG NAME")
    print("-" * 60)
    
    # Sort and aggregate
    rx_pers = rx.groupby(['DUPERSID', 'VARSTR', 'VARPSU', 'PERWT16F', 'RXDRGNAM']).agg(
        pers_RXXP=('RXXP16X', 'sum'),
        n_purchases=('RXXP16X', 'count')
    ).reset_index()
    
    # Add person indicator
    rx_pers['PERSON'] = 1
    
    print(f"Person-drug records: {len(rx_pers):,}")
    print(f"Unique drug names: {rx_pers['RXDRGNAM'].nunique():,}")
    
    # Calculate estimates by drug name
    print("\n" + "=" * 80)
    print("ESTIMATES BY GENERIC DRUG NAME")
    print("=" * 80)
    
    # Get top drugs by number of people
    drug_counts = rx_pers.groupby('RXDRGNAM').agg(
        n_people=('PERSON', 'sum'),
        total_purchases=('n_purchases', 'sum'),
        total_exp=('pers_RXXP', 'sum')
    ).reset_index()
    
    drug_counts = drug_counts.sort_values('n_people', ascending=False)
    
    print("\nTop 20 drugs by number of people (unweighted):")
    print("-" * 80)
    print(f"{'Drug Name':<40} {'# People':>10} {'Purchases':>12} {'Expenditures':>15}")
    print("-" * 80)
    
    for idx, row in drug_counts.head(20).iterrows():
        print(f"{row['RXDRGNAM'][:40]:<40} {row['n_people']:>10,} {row['total_purchases']:>12,} ${row['total_exp']:>14,.0f}")
    
    # Calculate survey-weighted estimates for top drugs
    print("\n" + "=" * 80)
    print("SURVEY-WEIGHTED ESTIMATES FOR TOP 10 DRUGS")
    print("=" * 80)
    
    top_drugs = drug_counts.head(10)['RXDRGNAM'].tolist()
    
    results = []
    for drug in top_drugs:
        drug_data = rx_pers[rx_pers['RXDRGNAM'] == drug].copy()
        
        if len(drug_data) > 0:
            design = SurveyDesign(
                data=drug_data,
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
            
            results.append({
                'Drug': drug,
                'People': people_result['total'].values[0],
                'People_SE': people_result['se'].values[0],
                'Purchases': purchases_result['total'].values[0],
                'Purchases_SE': purchases_result['se'].values[0],
                'Expenditures': exp_result['total'].values[0],
                'Expenditures_SE': exp_result['se'].values[0]
            })
    
    print("\n" + "-" * 100)
    print(f"{'Drug Name':<30} {'# People':>15} {'Total Purchases':>18} {'Total Expenditures':>20}")
    print("-" * 100)
    
    for r in results:
        print(f"{r['Drug'][:30]:<30} {r['People']:>15,.0f} {r['Purchases']:>18,.0f} ${r['Expenditures']:>19,.0f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
