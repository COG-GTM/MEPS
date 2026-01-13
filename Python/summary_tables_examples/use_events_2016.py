"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Use, expenditures, and population, 2016:
 - Total number of events
 - Mean expenditure per event by source of payment
 - Mean events per person
 - By event type (office-based, outpatient)

Input files:
 - H188G.ssp (2016 OB event file)
 - H188F.ssp (2016 OP event file)
 - H192.ssp (2016 full-year consolidated)
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
    print("Utilization and expenditures by event type")
    print("="*80)
    
    # Load FYC file
    print("\nLoading 2016 Full-Year Consolidated file...")
    h192 = load_sas_data(os.path.join(meps_data_path, "H192.sas7bdat"))
    fyc = h192[['DUPERSID', 'VARSTR', 'VARPSU', 'PERWT16F']].drop_duplicates()
    
    # Load OB event file
    print("Loading 2016 OB event file...")
    h188g = load_sas_data(os.path.join(meps_data_path, "H188G.sas7bdat"))
    
    # Load OP event file
    print("Loading 2016 OP event file...")
    h188f = load_sas_data(os.path.join(meps_data_path, "H188F.sas7bdat"))
    
    # Office-based visits (OBV)
    ob = h188g.copy()
    ob['EVENT'] = 1
    ob['XP_SF'] = ob['OBSF16X']  # Out-of-pocket
    ob['XP_PR'] = ob['OBPR16X']  # Private insurance
    ob['XP_MR'] = ob['OBMR16X']  # Medicare
    ob['XP_MD'] = ob['OBMD16X']  # Medicaid
    ob['XP_OZ'] = ob['OBOR16X'] + ob['OBOU16X'] + ob['OBVA16X'] + ob['OBTR16X'] + ob['OBOF16X'] + ob['OBSL16X'] + ob['OBWC16X']  # Other
    ob['XP_TOT'] = ob['OBXP16X']  # Total
    
    # Office-based physician visits (OBD) - subset where SEEDOC=1
    obd = ob[ob['SEEDOC'] == 1].copy()
    
    # Outpatient visits (OPT)
    op = h188f.copy()
    op['EVENT'] = 1
    op['XP_SF'] = op['OPSF16X']
    op['XP_PR'] = op['OPPR16X']
    op['XP_MR'] = op['OPMR16X']
    op['XP_MD'] = op['OPMD16X']
    op['XP_OZ'] = op['OPOR16X'] + op['OPOU16X'] + op['OPVA16X'] + op['OPTR16X'] + op['OPOF16X'] + op['OPSL16X'] + op['OPWC16X']
    op['XP_TOT'] = op['OPXP16X']
    
    # Outpatient physician visits (OPV) - subset where SEEDOC=1
    opv = op[op['SEEDOC'] == 1].copy()
    
    # Merge with FYC to retain all PSUs
    ob = pd.merge(ob, fyc, on='DUPERSID', how='left')
    obd = pd.merge(obd, fyc, on='DUPERSID', how='left')
    op = pd.merge(op, fyc, on='DUPERSID', how='left')
    opv = pd.merge(opv, fyc, on='DUPERSID', how='left')
    
    # Calculate estimates
    print("\n" + "="*80)
    print("UTILIZATION AND EXPENDITURES BY EVENT TYPE, 2016")
    print("="*80)
    
    event_types = [
        ('Office-based visits (OBV)', ob),
        ('Office-based physician visits (OBD)', obd),
        ('Outpatient visits (OPT)', op),
        ('Outpatient physician visits (OPV)', opv)
    ]
    
    payment_sources = ['XP_SF', 'XP_PR', 'XP_MR', 'XP_MD', 'XP_OZ', 'XP_TOT']
    payment_labels = {
        'XP_SF': 'Out-of-pocket',
        'XP_PR': 'Private insurance',
        'XP_MR': 'Medicare',
        'XP_MD': 'Medicaid',
        'XP_OZ': 'Other',
        'XP_TOT': 'Total'
    }
    
    for event_name, event_data in event_types:
        if len(event_data) == 0:
            continue
        
        design = SurveyDesign(
            data=event_data,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWT16F'
        )
        
        print(f"\n{event_name}")
        print("-" * 60)
        
        # Total number of events
        event_total = survey_total(design, 'EVENT')
        print(f"  Total number of events: {event_total['Sum'].values[0]:,.0f} (SE: {event_total['StdDev'].values[0]:,.0f})")
        
        # Mean expenditure per event by source of payment
        print("\n  Mean expenditure per event by source of payment:")
        for source in payment_sources:
            if source in event_data.columns:
                mean_result = survey_mean(design, source)
                label = payment_labels.get(source, source)
                print(f"    {label}: ${mean_result['Mean'].values[0]:,.2f} (SE: ${mean_result['StdErr'].values[0]:,.2f})")
        
        # Mean events per person
        pers_events = event_data.groupby(['DUPERSID', 'VARSTR', 'VARPSU', 'PERWT16F']).agg({
            'EVENT': 'sum'
        }).reset_index()
        
        pers_design = SurveyDesign(
            data=pers_events,
            strata='VARSTR',
            cluster='VARPSU',
            weight='PERWT16F'
        )
        
        mean_events = survey_mean(pers_design, 'EVENT')
        print(f"\n  Mean events per person: {mean_events['Mean'].values[0]:.2f} (SE: {mean_events['StdErr'].values[0]:.2f})")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Summary Tables - Use Events 2016')
    parser.add_argument('--data-path', type=str, default='C:/MEPS',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
