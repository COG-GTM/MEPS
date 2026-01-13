"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Use, expenditures, and population, 2019:
 - Mean expenditure per person
 - By event type and source of payment

Input file: H216.sas7bdat (2019 full-year consolidated)
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, print_results


def main(meps_data_path: str = "C:/MEPS"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    print("MEPS-HC Data Tools: Use, Expenditures, and Population, 2019")
    print("Mean expenditure per person by event type and source of payment")
    print("="*80)
    
    # Load FYC file
    print("\nLoading 2019 Full-Year Consolidated file...")
    h216 = load_sas_data(os.path.join(meps_data_path, "H216.sas7bdat"))
    
    # Define variables
    meps = h216.copy()
    
    # Total expenditures (TOT)
    meps['TOT_SF'] = meps['TOTSLF19']  # Out-of-pocket
    meps['TOT_PTR'] = meps['TOTPTR19']  # Private insurance
    meps['TOT_MCR'] = meps['TOTMCR19']  # Medicare
    meps['TOT_MCD'] = meps['TOTMCD19']  # Medicaid
    meps['TOT_OTZ'] = meps['TOTOTH19'] + meps['TOTVA19'] + meps['TOTTRI19'] + meps['TOTOFD19'] + meps['TOTSTL19'] + meps['TOTWCP19']  # Other
    meps['TOT_TOT'] = meps['TOTEXP19']  # Total
    
    # Emergency room visits (ERT)
    meps['ERT_SF'] = meps['ERTSLF19']
    meps['ERT_PTR'] = meps['ERTPTR19']
    meps['ERT_MCR'] = meps['ERTMCR19']
    meps['ERT_MCD'] = meps['ERTMCD19']
    meps['ERT_OTZ'] = meps['ERTOTH19'] + meps['ERTVA19'] + meps['ERTTRI19'] + meps['ERTOFD19'] + meps['ERTSTL19'] + meps['ERTWCP19']
    meps['ERT_TOT'] = meps['ERTEXP19']
    
    # Inpatient stays (IPT)
    meps['IPT_SF'] = meps['IPTSLF19']
    meps['IPT_PTR'] = meps['IPTPTR19']
    meps['IPT_MCR'] = meps['IPTMCR19']
    meps['IPT_MCD'] = meps['IPTMCD19']
    meps['IPT_OTZ'] = meps['IPTOTH19'] + meps['IPTVA19'] + meps['IPTTRI19'] + meps['IPTOFD19'] + meps['IPTSTL19'] + meps['IPTWCP19']
    meps['IPT_TOT'] = meps['IPTEXP19']
    
    # Calculate estimates
    print("\n" + "="*80)
    print("MEAN EXPENDITURE PER PERSON BY EVENT TYPE AND SOURCE OF PAYMENT, 2019")
    print("="*80)
    
    design = SurveyDesign(
        data=meps,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT19F'
    )
    
    event_types = ['TOT', 'ERT', 'IPT']
    event_labels = {
        'TOT': 'All events',
        'ERT': 'Emergency room visits',
        'IPT': 'Inpatient stays'
    }
    
    payment_sources = ['SF', 'PTR', 'MCR', 'MCD', 'OTZ', 'TOT']
    payment_labels = {
        'SF': 'Out-of-pocket',
        'PTR': 'Private insurance',
        'MCR': 'Medicare',
        'MCD': 'Medicaid',
        'OTZ': 'Other',
        'TOT': 'Total'
    }
    
    for event_type in event_types:
        event_label = event_labels.get(event_type, event_type)
        print(f"\n{event_label}")
        print("-" * 60)
        
        for source in payment_sources:
            var_name = f'{event_type}_{source}'
            if var_name in meps.columns:
                mean_result = survey_mean(design, var_name)
                source_label = payment_labels.get(source, source)
                print(f"  {source_label}: ${mean_result['Mean'].values[0]:,.2f} (SE: ${mean_result['StdErr'].values[0]:,.2f})")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Summary Tables - Use Expenditures 2019')
    parser.add_argument('--data-path', type=str, default='C:/MEPS',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
