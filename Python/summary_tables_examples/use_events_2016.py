"""
Example code to replicate estimates from the MEPS-HC Data Tools summary tables

Use, expenditures, and population, 2016

Utilization and expenditures by event type and source of payment (SOP):
    - Total number of events
    - Mean expenditure per event, by source of payment
    - Mean events per person, for office-based visits

Selected event types:
    - Office-based medical visits (OBV)
    - Office-based physician visits (OBD)
    - Outpatient visits (OPT)
    - Outpatient physician visits (OPV)

Input files:
    - h192.ssp (2016 full-year consolidated)
    - h188f.ssp (2016 OP event file)
    - h188g.ssp (2016 OB event file)

Python equivalent of: SAS/summary_tables_examples/use_events_2016.sas
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
    print("Utilization and Expenditures by Event Type")
    print("=" * 80)
    
    # Load datasets
    print("\nLoading data files...")
    
    fyc = load_sas_data(data_dir / "h192.ssp")
    ob = load_sas_data(data_dir / "h188g.ssp")
    op = load_sas_data(data_dir / "h188f.ssp")
    
    print(f"  FYC records: {len(fyc):,}")
    print(f"  OB records: {len(ob):,}")
    print(f"  OP records: {len(op):,}")
    
    # Process Office-Based events
    ob = ob[ob['OBXP16X'] >= 0].copy()  # Remove inapplicable events
    
    # Aggregate payment sources
    # PR = Private (PV) + TRICARE (TR)
    # OZ = other federal (OF) + State/local (SL) + other private (OR) +
    #      other public (OU) + other unclassified sources (OT) +
    #      worker's comp (WC) + Veteran's (VA)
    
    ob['PR'] = ob['OBPV16X'] + ob['OBTR16X']
    ob['OZ'] = (ob['OBOF16X'] + ob['OBSL16X'] + ob['OBVA16X'] + 
                ob['OBOT16X'] + ob['OBOR16X'] + ob['OBOU16X'] + ob['OBWC16X'])
    ob['COUNT'] = 1
    ob['PHYS_COUNT'] = (ob['SEEDOC'] == 1).astype(int)
    
    # Process Outpatient events
    op = op[op['OPXP16X'] >= 0].copy()  # Remove inapplicable events
    
    # Facility expenses
    op['PR_FAC'] = op['OPFPV16X'] + op['OPFTR16X']
    op['OZ_FAC'] = (op['OPFOF16X'] + op['OPFSL16X'] + op['OPFOR16X'] + 
                   op['OPFOU16X'] + op['OPFVA16X'] + op['OPFOT16X'] + op['OPFWC16X'])
    
    # SBD expenses
    op['PR_SBD'] = op['OPDPV16X'] + op['OPDTR16X']
    op['OZ_SBD'] = (op['OPDOF16X'] + op['OPDSL16X'] + op['OPDOR16X'] + 
                   op['OPDOU16X'] + op['OPDVA16X'] + op['OPDOT16X'] + op['OPDWC16X'])
    
    # Combined facility and SBD expenses
    op['SF'] = op['OPFSF16X'] + op['OPDSF16X']  # out-of-pocket
    op['MR'] = op['OPFMR16X'] + op['OPDMR16X']  # Medicare
    op['MD'] = op['OPFMD16X'] + op['OPDMD16X']  # Medicaid
    op['PR'] = op['PR_FAC'] + op['PR_SBD']      # private insurance
    op['OZ'] = op['OZ_FAC'] + op['OZ_SBD']      # other sources
    op['COUNT'] = 1
    
    # Merge with FYC to retain all PSUs
    fyc_subset = fyc[['DUPERSID', 'VARSTR', 'VARPSU', 'PERWT16F']].copy()
    
    ob_cols = ['DUPERSID', 'OBXP16X', 'OBSF16X', 'PR', 'OBMR16X', 'OBMD16X', 'OZ', 'COUNT', 'PHYS_COUNT', 'SEEDOC']
    ob_fyc = ob[ob_cols].merge(fyc_subset, on='DUPERSID', how='left')
    
    op_cols = ['DUPERSID', 'OPXP16X', 'SF', 'PR', 'MR', 'MD', 'OZ', 'COUNT', 'SEEDOC']
    op_fyc = op[op_cols].merge(fyc_subset, on='DUPERSID', how='left')
    
    # Calculate estimates
    print("\n" + "=" * 80)
    print("OFFICE-BASED VISITS")
    print("=" * 80)
    
    design_ob = SurveyDesign(
        data=ob_fyc,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT16F'
    )
    
    # Total number of events
    total_events = survey_total(design_ob, 'COUNT')
    print(f"\nTotal number of office-based visits: {total_events['total'].values[0]:,.0f}")
    print(f"  SE: {total_events['se'].values[0]:,.0f}")
    
    # Mean expenditure per event by source of payment
    print("\nMean expenditure per event by source of payment:")
    sop_vars = [('OBSF16X', 'Out-of-pocket'), ('PR', 'Private'), 
                ('OBMR16X', 'Medicare'), ('OBMD16X', 'Medicaid'), ('OZ', 'Other')]
    
    for var, label in sop_vars:
        mean_result = survey_mean(design_ob, var)
        print(f"  {label}: ${mean_result['mean'].values[0]:,.2f} (SE: ${mean_result['se'].values[0]:.2f})")
    
    # Office-based physician visits
    print("\n" + "-" * 60)
    print("OFFICE-BASED PHYSICIAN VISITS")
    print("-" * 60)
    
    ob_phys = ob_fyc[ob_fyc['SEEDOC'] == 1].copy()
    
    design_ob_phys = SurveyDesign(
        data=ob_phys,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT16F'
    )
    
    total_phys = survey_total(design_ob_phys, 'COUNT')
    print(f"\nTotal number of office-based physician visits: {total_phys['total'].values[0]:,.0f}")
    
    print("\nMean expenditure per event by source of payment:")
    for var, label in sop_vars:
        mean_result = survey_mean(design_ob_phys, var)
        print(f"  {label}: ${mean_result['mean'].values[0]:,.2f} (SE: ${mean_result['se'].values[0]:.2f})")
    
    # Outpatient visits
    print("\n" + "=" * 80)
    print("OUTPATIENT VISITS")
    print("=" * 80)
    
    design_op = SurveyDesign(
        data=op_fyc,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT16F'
    )
    
    total_op = survey_total(design_op, 'COUNT')
    print(f"\nTotal number of outpatient visits: {total_op['total'].values[0]:,.0f}")
    
    print("\nMean expenditure per event by source of payment:")
    sop_vars_op = [('SF', 'Out-of-pocket'), ('PR', 'Private'), 
                   ('MR', 'Medicare'), ('MD', 'Medicaid'), ('OZ', 'Other')]
    
    for var, label in sop_vars_op:
        mean_result = survey_mean(design_op, var)
        print(f"  {label}: ${mean_result['mean'].values[0]:,.2f} (SE: ${mean_result['se'].values[0]:.2f})")
    
    # Outpatient physician visits
    print("\n" + "-" * 60)
    print("OUTPATIENT PHYSICIAN VISITS")
    print("-" * 60)
    
    op_phys = op_fyc[op_fyc['SEEDOC'] == 1].copy()
    
    design_op_phys = SurveyDesign(
        data=op_phys,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT16F'
    )
    
    total_op_phys = survey_total(design_op_phys, 'COUNT')
    print(f"\nTotal number of outpatient physician visits: {total_op_phys['total'].values[0]:,.0f}")
    
    # Mean events per person
    print("\n" + "=" * 80)
    print("MEAN EVENTS PER PERSON")
    print("=" * 80)
    
    # Aggregate to person-level
    pers_ob = ob_fyc.groupby(['DUPERSID', 'VARSTR', 'VARPSU']).agg(
        n_events=('COUNT', 'sum'),
        n_phys_events=('PHYS_COUNT', 'sum'),
        PERWT16F=('PERWT16F', 'mean')
    ).reset_index()
    
    # Fill missing with 0
    pers_ob['n_events'] = pers_ob['n_events'].fillna(0)
    pers_ob['n_phys_events'] = pers_ob['n_phys_events'].fillna(0)
    
    design_pers = SurveyDesign(
        data=pers_ob,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT16F'
    )
    
    mean_events = survey_mean(design_pers, 'n_events')
    mean_phys_events = survey_mean(design_pers, 'n_phys_events')
    
    print(f"\nMean office-based visits per person: {mean_events['mean'].values[0]:.2f}")
    print(f"Mean office-based physician visits per person: {mean_phys_events['mean'].values[0]:.2f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
