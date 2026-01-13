"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Use, expenditures, and population, 2016:
 - Total expenditures
 - Mean expenditure per person
 - Mean out-of-pocket expense per person with expense
 - By event type and source of payment

Input file: H192.ssp (2016 full-year consolidated)
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
    
    print("MEPS-HC Data Tools: Use, Expenditures, and Population, 2016")
    print("Expenditures by event type and source of payment")
    print("="*80)
    
    # Load FYC file
    print("\nLoading 2016 Full-Year Consolidated file...")
    h192 = load_sas_data(os.path.join(meps_data_path, "H192.sas7bdat"))
    
    # Define variables
    meps = h192.copy()
    
    # Office-based visits (OBV)
    meps['OBV_SF'] = meps['OBVSLF16']  # Out-of-pocket
    meps['OBV_PTR'] = meps['OBVPTR16']  # Private insurance
    meps['OBV_MCR'] = meps['OBVMCR16']  # Medicare
    meps['OBV_MCD'] = meps['OBVMCD16']  # Medicaid
    meps['OBV_OTZ'] = meps['OBVOTH16'] + meps['OBVVA16'] + meps['OBVTRI16'] + meps['OBVOFD16'] + meps['OBVSTL16'] + meps['OBVWCP16']  # Other
    meps['OBV_TOT'] = meps['OBVEXP16']  # Total
    
    # Office-based physician visits (OBD)
    meps['OBD_SF'] = meps['OBDSLF16']
    meps['OBD_PTR'] = meps['OBDPTR16']
    meps['OBD_MCR'] = meps['OBDMCR16']
    meps['OBD_MCD'] = meps['OBDMCD16']
    meps['OBD_OTZ'] = meps['OBDOTH16'] + meps['OBDVA16'] + meps['OBDTRI16'] + meps['OBDOFD16'] + meps['OBDSTL16'] + meps['OBDWCP16']
    meps['OBD_TOT'] = meps['OBDEXP16']
    
    # Outpatient visits (OPT) - facility + SBD
    meps['OPT_SF'] = meps['OPTSLF16']
    meps['OPT_PTR'] = meps['OPTPTR16']
    meps['OPT_MCR'] = meps['OPTMCR16']
    meps['OPT_MCD'] = meps['OPTMCD16']
    meps['OPT_OTZ'] = meps['OPTOTH16'] + meps['OPTVA16'] + meps['OPTTRI16'] + meps['OPTOFD16'] + meps['OPTSTL16'] + meps['OPTWCP16']
    meps['OPT_TOT'] = meps['OPTEXP16']
    
    # Outpatient physician visits (OPV)
    meps['OPV_SF'] = meps['OPVSLF16']
    meps['OPV_PTR'] = meps['OPVPTR16']
    meps['OPV_MCR'] = meps['OPVMCR16']
    meps['OPV_MCD'] = meps['OPVMCD16']
    meps['OPV_OTZ'] = meps['OPVOTH16'] + meps['OPVVA16'] + meps['OPVTRI16'] + meps['OPVOFD16'] + meps['OPVSTL16'] + meps['OPVWCP16']
    meps['OPV_TOT'] = meps['OPVEXP16']
    
    # Calculate estimates
    print("\n" + "="*80)
    print("EXPENDITURES BY EVENT TYPE AND SOURCE OF PAYMENT, 2016")
    print("="*80)
    
    design = SurveyDesign(
        data=meps,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT16F'
    )
    
    event_types = ['OBV', 'OBD', 'OPT', 'OPV']
    event_labels = {
        'OBV': 'Office-based visits',
        'OBD': 'Office-based physician visits',
        'OPT': 'Outpatient visits',
        'OPV': 'Outpatient physician visits'
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
                total_result = survey_total(design, var_name)
                mean_result = survey_mean(design, var_name)
                source_label = payment_labels.get(source, source)
                print(f"\n  {source_label}:")
                print(f"    Total expenditures: ${total_result['Sum'].values[0]:,.0f} (SE: ${total_result['StdDev'].values[0]:,.0f})")
                print(f"    Mean expenditure per person: ${mean_result['Mean'].values[0]:,.2f} (SE: ${mean_result['StdErr'].values[0]:,.2f})")
        
        # Mean out-of-pocket expense per person with expense
        tot_var = f'{event_type}_TOT'
        sf_var = f'{event_type}_SF'
        if tot_var in meps.columns and sf_var in meps.columns:
            meps_with_exp = meps[meps[tot_var] > 0].copy()
            if len(meps_with_exp) > 0:
                design_exp = SurveyDesign(
                    data=meps_with_exp,
                    strata='VARSTR',
                    cluster='VARPSU',
                    weight='PERWT16F'
                )
                mean_sf = survey_mean(design_exp, sf_var)
                print(f"\n  Mean out-of-pocket per person with expense: ${mean_sf['Mean'].values[0]:,.2f} (SE: ${mean_sf['StdErr'].values[0]:,.2f})")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Summary Tables - Use Expenditures 2016')
    parser.add_argument('--data-path', type=str, default='C:/MEPS',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
