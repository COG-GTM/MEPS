"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Use, expenditures, and population, 2019

Expenditures by event type and source of payment (SOP):
    - Mean expenditure per person

Selected event types:
    - All event types (TOT)
    - Emergency room visits (ERT)
    - Inpatient stays (IPT)

Input file: h216.sas7bdat (2019 full-year consolidated)

Note: Starting in 2019, 'Other public' (OPU) and 'Other private' (OPR) are
dropped from the files

Python equivalent of: SAS/summary_tables_examples/use_expenditures_2019.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_mean


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS")
    
    print("=" * 80)
    print("USE, EXPENDITURES, AND POPULATION, 2019")
    print("Mean Expenditure per Person by Event Type and Source of Payment")
    print("=" * 80)
    
    # Load FYC file
    fyc_file = data_dir / "h216.sas7bdat"
    print(f"\nLoading data from: {fyc_file}")
    
    fyc = load_sas_data(fyc_file)
    
    # Aggregate payment sources
    # OTZ = other federal (OFD) + State/local (STL) + other unclassified sources (OSR) +
    #       worker's comp (WCP) + Veteran's (VA)
    # Note: Starting in 2019, OPU and OPR are dropped from files
    
    # All event types
    fyc['TOTOTZ'] = (fyc['TOTOFD19'] + fyc['TOTSTL19'] + fyc['TOTOSR19'] + 
                    fyc['TOTWCP19'] + fyc['TOTVA19'])
    
    # Emergency room visits (facility + SBD expenses)
    fyc['ERTOTZ'] = (fyc['ERTOFD19'] + fyc['ERTSTL19'] + fyc['ERTOSR19'] + 
                    fyc['ERTWCP19'] + fyc['ERTVA19'])
    
    # Inpatient stays (facility + SBD expenses)
    fyc['IPTOTZ'] = (fyc['IPTOFD19'] + fyc['IPTSTL19'] + fyc['IPTOSR19'] + 
                    fyc['IPTWCP19'] + fyc['IPTVA19'])
    
    # Calculate estimates
    design = SurveyDesign(
        data=fyc,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT19F'
    )
    
    # Event types and their variables
    event_types = {
        'Any event': {
            'EXP': 'TOTEXP19', 'SLF': 'TOTSLF19', 'PTR': 'TOTPTR19', 
            'MCR': 'TOTMCR19', 'MCD': 'TOTMCD19', 'OTZ': 'TOTOTZ'
        },
        'Emergency room visits': {
            'EXP': 'ERTEXP19', 'SLF': 'ERTSLF19', 'PTR': 'ERTPTR19', 
            'MCR': 'ERTMCR19', 'MCD': 'ERTMCD19', 'OTZ': 'ERTOTZ'
        },
        'Inpatient stays': {
            'EXP': 'IPTEXP19', 'SLF': 'IPTSLF19', 'PTR': 'IPTPTR19', 
            'MCR': 'IPTMCR19', 'MCD': 'IPTMCD19', 'OTZ': 'IPTOTZ'
        }
    }
    
    sop_labels = {
        'EXP': 'Any source',
        'SLF': 'Out-of-pocket',
        'PTR': 'Private',
        'MCR': 'Medicare',
        'MCD': 'Medicaid',
        'OTZ': 'Other'
    }
    
    print("\n" + "=" * 80)
    print("MEAN EXPENDITURE PER PERSON BY EVENT TYPE AND SOURCE OF PAYMENT")
    print("=" * 80)
    
    for event_name, sop_vars in event_types.items():
        print(f"\n{event_name}:")
        print("-" * 60)
        print(f"{'Source of Payment':<20} {'Mean per Person':>15} {'Std Error':>12}")
        print("-" * 60)
        
        for sop, var in sop_vars.items():
            if var in fyc.columns:
                mean_result = survey_mean(design, var)
                print(f"{sop_labels[sop]:<20} ${mean_result['mean'].values[0]:>14,.2f} ${mean_result['se'].values[0]:>11,.2f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
