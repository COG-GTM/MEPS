"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Use, expenditures, and population, 2016

Expenditures by event type and source of payment (SOP):
    - Total expenditures
    - Mean expenditure per person
    - Mean out-of-pocket (SLF) payment per person with an out-of-pocket expense

Selected event types:
    - Office-based medical visits (OBV)
    - Office-based physician visits (OBD)
    - Outpatient visits (OPT)
    - Outpatient physician visits (OPV)

Input file: h192.ssp (2016 full-year consolidated)

Python equivalent of: SAS/summary_tables_examples/use_expenditures_2016.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS")
    
    print("=" * 80)
    print("USE, EXPENDITURES, AND POPULATION, 2016")
    print("Expenditures by Event Type and Source of Payment")
    print("=" * 80)
    
    # Load FYC file
    fyc_file = data_dir / "h192.ssp"
    print(f"\nLoading data from: {fyc_file}")
    
    fyc = load_sas_data(fyc_file)
    
    # Aggregate payment sources
    # PTR = Private (PRV) + TRICARE (TRI)
    # OTZ = other federal (OFD) + State/local (STL) + other private (OPR) +
    #       other public (OPU) + other unclassified sources (OSR) +
    #       worker's comp (WCP) + Veteran's (VA)
    
    # Office-based visits
    fyc['OBVPTR'] = fyc['OBVPRV16'] + fyc['OBVTRI16']
    fyc['OBVOTZ'] = (fyc['OBVOFD16'] + fyc['OBVSTL16'] + fyc['OBVOPR16'] + 
                    fyc['OBVOPU16'] + fyc['OBVOSR16'] + fyc['OBVWCP16'] + fyc['OBVVA16'])
    
    # Office-based physician visits
    fyc['OBDPTR'] = fyc['OBDPRV16'] + fyc['OBDTRI16']
    fyc['OBDOTZ'] = (fyc['OBDOFD16'] + fyc['OBDSTL16'] + fyc['OBDOPR16'] + 
                    fyc['OBDOPU16'] + fyc['OBDOSR16'] + fyc['OBDWCP16'] + fyc['OBDVA16'])
    
    # Outpatient visits (facility + SBD expenses)
    fyc['OPTPTR'] = fyc['OPTPRV16'] + fyc['OPTTRI16']
    fyc['OPTOTZ'] = (fyc['OPTOFD16'] + fyc['OPTSTL16'] + fyc['OPTOPR16'] + 
                    fyc['OPTOPU16'] + fyc['OPTOSR16'] + fyc['OPTWCP16'] + fyc['OPTVA16'])
    
    # Outpatient physician visits (facility expense)
    fyc['OPVPTR'] = fyc['OPVPRV16'] + fyc['OPVTRI16']
    fyc['OPVOTZ'] = (fyc['OPVOFD16'] + fyc['OPVSTL16'] + fyc['OPVOPR16'] + 
                    fyc['OPVOPU16'] + fyc['OPVOSR16'] + fyc['OPVWCP16'] + fyc['OPVVA16'])
    
    # Outpatient physician visits (SBD expense)
    fyc['OPSPTR'] = fyc['OPSPRV16'] + fyc['OPSTRI16']
    fyc['OPSOTZ'] = (fyc['OPSOFD16'] + fyc['OPSSTL16'] + fyc['OPSOPR16'] + 
                    fyc['OPSOPU16'] + fyc['OPSOSR16'] + fyc['OPSWCP16'] + fyc['OPSVA16'])
    
    # Combine facility and SBD expenses for hospital-type events
    fyc['OPpSLF'] = fyc['OPVSLF16'] + fyc['OPSSLF16']  # out-of-pocket payments
    fyc['OPpMCR'] = fyc['OPVMCR16'] + fyc['OPSMCR16']  # Medicare
    fyc['OPpMCD'] = fyc['OPVMCD16'] + fyc['OPSMCD16']  # Medicaid
    fyc['OPpPTR'] = fyc['OPVPTR'] + fyc['OPSPTR']      # private insurance
    fyc['OPpOTZ'] = fyc['OPVOTZ'] + fyc['OPSOTZ']      # other sources
    
    # Define domains for persons with out-of-pocket expense
    fyc['has_OBVSLF'] = (fyc['OBVSLF16'] > 0).astype(int)
    fyc['has_OBDSLF'] = (fyc['OBDSLF16'] > 0).astype(int)
    fyc['has_OPTSLF'] = (fyc['OPTSLF16'] > 0).astype(int)
    fyc['has_OPpSLF'] = (fyc['OPpSLF'] > 0).astype(int)
    
    # Calculate estimates
    design = SurveyDesign(
        data=fyc,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT16F'
    )
    
    # Event types and their variables
    event_types = {
        'Office-based visits': {
            'SLF': 'OBVSLF16', 'PTR': 'OBVPTR', 'MCR': 'OBVMCR16', 
            'MCD': 'OBVMCD16', 'OTZ': 'OBVOTZ'
        },
        'Office-based physician visits': {
            'SLF': 'OBDSLF16', 'PTR': 'OBDPTR', 'MCR': 'OBDMCR16', 
            'MCD': 'OBDMCD16', 'OTZ': 'OBDOTZ'
        },
        'Outpatient visits': {
            'SLF': 'OPTSLF16', 'PTR': 'OPTPTR', 'MCR': 'OPTMCR16', 
            'MCD': 'OPTMCD16', 'OTZ': 'OPTOTZ'
        },
        'Outpatient physician visits': {
            'SLF': 'OPpSLF', 'PTR': 'OPpPTR', 'MCR': 'OPpMCR', 
            'MCD': 'OPpMCD', 'OTZ': 'OPpOTZ'
        }
    }
    
    sop_labels = {
        'SLF': 'Out-of-pocket',
        'PTR': 'Private',
        'MCR': 'Medicare',
        'MCD': 'Medicaid',
        'OTZ': 'Other'
    }
    
    print("\n" + "=" * 80)
    print("TOTAL EXPENDITURES AND MEAN EXPENDITURE PER PERSON")
    print("=" * 80)
    
    for event_name, sop_vars in event_types.items():
        print(f"\n{event_name}:")
        print("-" * 60)
        print(f"{'Source of Payment':<20} {'Total Exp':>15} {'Mean per Person':>15}")
        print("-" * 60)
        
        for sop, var in sop_vars.items():
            if var in fyc.columns:
                total_result = survey_total(design, var)
                mean_result = survey_mean(design, var)
                print(f"{sop_labels[sop]:<20} ${total_result['total'].values[0]:>14,.0f} ${mean_result['mean'].values[0]:>14,.2f}")
    
    # Mean expenditure per person with expense
    print("\n" + "=" * 80)
    print("MEAN OUT-OF-POCKET EXPENSE PER PERSON WITH EXPENSE")
    print("=" * 80)
    
    oop_vars = [
        ('Office-based visits', 'OBVSLF16', 'has_OBVSLF'),
        ('Office-based physician visits', 'OBDSLF16', 'has_OBDSLF'),
        ('Outpatient visits', 'OPTSLF16', 'has_OPTSLF'),
        ('Outpatient physician visits', 'OPpSLF', 'has_OPpSLF')
    ]
    
    for event_name, var, domain_var in oop_vars:
        subset = fyc[fyc[domain_var] == 1].copy()
        if len(subset) > 0:
            design_sub = SurveyDesign(
                data=subset,
                strata='VARSTR',
                cluster='VARPSU',
                weight='PERWT16F'
            )
            mean_result = survey_mean(design_sub, var)
            print(f"\n{event_name}:")
            print(f"  Mean OOP per person with expense: ${mean_result['mean'].values[0]:,.2f}")
            print(f"  SE: ${mean_result['se'].values[0]:.2f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
