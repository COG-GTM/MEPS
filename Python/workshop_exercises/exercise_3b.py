"""
Exercise 3b: Expenditures for Events Associated with Diabetes, 2015

This program illustrates how to calculate expenditures for all events
associated with a condition.

The condition used in this exercise is Diabetes (CCS CODE=049 or 050)

Input files:
    - 2015 Full-Year Consolidated file (h181)
    - 2015 Condition file (h180)
    - 2015 Prescribed Medicines file (h178a)
    - 2015 Inpatient Visits file (h178d)
    - 2015 Emergency Room Visits file (h178e)
    - 2015 Outpatient Visits file (h178f)
    - 2015 Office-Based Visits file (h178g)
    - 2015 Home Health file (h178h)
    - 2015 Condition-Event Link file (h178if1)

Python equivalent of: SAS/workshop_exercises/exercise_3b/Exercise3b.sas
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
    print("AHRQ MEPS DATA USERS WORKSHOP -- 2018")
    print("EXERCISE 3b: EXPENDITURES FOR EVENTS ASSOCIATED WITH DIABETES")
    print("=" * 80)
    
    # 1) Pull out conditions with Diabetes (CCS CODE='049', '050')
    cond_file = data_dir / "h180.sas7bdat"
    print(f"\nLoading conditions data from: {cond_file}")
    
    cond = load_sas_data(cond_file)
    diab = cond[cond['CCCODEX'].isin(['049', '050'])].copy()
    
    print("\nCCS codes for diabetic conditions:")
    print(diab['CCCODEX'].value_counts())
    
    # 2) Get event ID for diabetic conditions from condition-event link file
    clnk_file = data_dir / "h178if1.sas7bdat"
    print(f"\nLoading condition-event link file from: {clnk_file}")
    
    clnk = load_sas_data(clnk_file, columns=['CONDIDX', 'EVNTIDX'])
    
    # Merge diabetes conditions with link file
    diab2 = diab[['DUPERSID', 'CONDIDX', 'CCCODEX']].merge(
        clnk, on='CONDIDX', how='inner'
    )
    
    print(f"\nNumber of condition-event links for diabetes: {len(diab2):,}")
    
    # 3) Delete duplicate cases per event
    diab3 = diab2[['DUPERSID', 'EVNTIDX']].drop_duplicates(subset='EVNTIDX')
    print(f"\nUnique events for diabetes: {len(diab3):,}")
    
    # 4) Load and process event files
    print("\nLoading event files...")
    
    # Source of payment variables
    sop_vars = ['SF', 'MR', 'MD', 'PV', 'VA', 'TR', 'OF', 'SL', 'WC', 'OR', 'OU', 'OT']
    
    # Prescribed Medicines
    pmed_file = data_dir / "h178a.sas7bdat"
    pmed = load_sas_data(pmed_file)
    pmed = pmed.rename(columns={'LINKIDX': 'EVNTIDX'})
    
    # Aggregate PMED to event level
    pmed_agg = pmed.groupby('EVNTIDX').agg({
        'RXXP15X': 'sum',
        'RXSF15X': 'sum', 'RXMR15X': 'sum', 'RXMD15X': 'sum', 'RXPV15X': 'sum',
        'RXVA15X': 'sum', 'RXTR15X': 'sum', 'RXOF15X': 'sum', 'RXSL15X': 'sum',
        'RXWC15X': 'sum', 'RXOR15X': 'sum', 'RXOU15X': 'sum', 'RXOT15X': 'sum'
    }).reset_index()
    
    pmed_agg = pmed_agg.rename(columns={
        'RXXP15X': 'TOTEXP', 'RXSF15X': 'SF', 'RXMR15X': 'MR', 'RXMD15X': 'MD',
        'RXPV15X': 'PV', 'RXVA15X': 'VA', 'RXTR15X': 'TR', 'RXOF15X': 'OF',
        'RXSL15X': 'SL', 'RXWC15X': 'WC', 'RXOR15X': 'OR', 'RXOU15X': 'OU', 'RXOT15X': 'OT'
    })
    pmed_agg['EVNTYP'] = 'PMED'
    pmed_agg = pmed_agg[pmed_agg['TOTEXP'] >= 0]
    
    # Office-Based Visits
    ob_file = data_dir / "h178g.sas7bdat"
    ob = load_sas_data(ob_file)
    ob_proc = ob[['EVNTIDX', 'OBXP15X', 'OBSF15X', 'OBMR15X', 'OBMD15X', 'OBPV15X',
                  'OBVA15X', 'OBTR15X', 'OBOF15X', 'OBSL15X', 'OBWC15X', 'OBOR15X',
                  'OBOU15X', 'OBOT15X']].copy()
    ob_proc = ob_proc.rename(columns={
        'OBXP15X': 'TOTEXP', 'OBSF15X': 'SF', 'OBMR15X': 'MR', 'OBMD15X': 'MD',
        'OBPV15X': 'PV', 'OBVA15X': 'VA', 'OBTR15X': 'TR', 'OBOF15X': 'OF',
        'OBSL15X': 'SL', 'OBWC15X': 'WC', 'OBOR15X': 'OR', 'OBOU15X': 'OU', 'OBOT15X': 'OT'
    })
    ob_proc['EVNTYP'] = 'AMBU'
    ob_proc = ob_proc[ob_proc['TOTEXP'] >= 0]
    
    # Emergency Room
    er_file = data_dir / "h178e.sas7bdat"
    er = load_sas_data(er_file)
    er_proc = er[['EVNTIDX', 'ERXP15X']].copy()
    er_proc['SF'] = er['ERFSF15X'] + er['ERDSF15X']
    er_proc['MR'] = er['ERFMR15X'] + er['ERDMR15X']
    er_proc['MD'] = er['ERFMD15X'] + er['ERDMD15X']
    er_proc['PV'] = er['ERFPV15X'] + er['ERDPV15X']
    er_proc['VA'] = er['ERFVA15X'] + er['ERDVA15X']
    er_proc['TR'] = er['ERFTR15X'] + er['ERDTR15X']
    er_proc['OF'] = er['ERFOF15X'] + er['ERDOF15X']
    er_proc['SL'] = er['ERFSL15X'] + er['ERDSL15X']
    er_proc['WC'] = er['ERFWC15X'] + er['ERDWC15X']
    er_proc['OR'] = er['ERFOR15X'] + er['ERDOR15X']
    er_proc['OU'] = er['ERFOU15X'] + er['ERDOU15X']
    er_proc['OT'] = er['ERFOT15X'] + er['ERDOT15X']
    er_proc = er_proc.rename(columns={'ERXP15X': 'TOTEXP'})
    er_proc['EVNTYP'] = 'EROM'
    er_proc = er_proc[er_proc['TOTEXP'] >= 0]
    
    # Inpatient
    ip_file = data_dir / "h178d.sas7bdat"
    ip = load_sas_data(ip_file)
    ip_proc = ip[['EVNTIDX', 'IPXP15X']].copy()
    ip_proc['SF'] = ip['IPFSF15X'] + ip['IPDSF15X']
    ip_proc['MR'] = ip['IPFMR15X'] + ip['IPDMR15X']
    ip_proc['MD'] = ip['IPFMD15X'] + ip['IPDMD15X']
    ip_proc['PV'] = ip['IPFPV15X'] + ip['IPDPV15X']
    ip_proc['VA'] = ip['IPFVA15X'] + ip['IPDVA15X']
    ip_proc['TR'] = ip['IPFTR15X'] + ip['IPDTR15X']
    ip_proc['OF'] = ip['IPFOF15X'] + ip['IPDOF15X']
    ip_proc['SL'] = ip['IPFSL15X'] + ip['IPDSL15X']
    ip_proc['WC'] = ip['IPFWC15X'] + ip['IPDWC15X']
    ip_proc['OR'] = ip['IPFOR15X'] + ip['IPDOR15X']
    ip_proc['OU'] = ip['IPFOU15X'] + ip['IPDOU15X']
    ip_proc['OT'] = ip['IPFOT15X'] + ip['IPDOT15X']
    ip_proc = ip_proc.rename(columns={'IPXP15X': 'TOTEXP'})
    ip_proc['EVNTYP'] = 'IPAT'
    ip_proc = ip_proc[ip_proc['TOTEXP'] >= 0]
    
    # Home Health
    hh_file = data_dir / "h178h.sas7bdat"
    hh = load_sas_data(hh_file)
    hh_proc = hh[['EVNTIDX', 'HHXP15X', 'HHSF15X', 'HHMR15X', 'HHMD15X', 'HHPV15X',
                  'HHVA15X', 'HHTR15X', 'HHOF15X', 'HHSL15X', 'HHWC15X', 'HHOR15X',
                  'HHOU15X', 'HHOT15X']].copy()
    hh_proc = hh_proc.rename(columns={
        'HHXP15X': 'TOTEXP', 'HHSF15X': 'SF', 'HHMR15X': 'MR', 'HHMD15X': 'MD',
        'HHPV15X': 'PV', 'HHVA15X': 'VA', 'HHTR15X': 'TR', 'HHOF15X': 'OF',
        'HHSL15X': 'SL', 'HHWC15X': 'WC', 'HHOR15X': 'OR', 'HHOU15X': 'OU', 'HHOT15X': 'OT'
    })
    hh_proc['EVNTYP'] = 'HVIS'
    hh_proc = hh_proc[hh_proc['TOTEXP'] >= 0]
    
    # Outpatient
    op_file = data_dir / "h178f.sas7bdat"
    op = load_sas_data(op_file)
    op_proc = op[['EVNTIDX', 'OPXP15X']].copy()
    op_proc['SF'] = op['OPFSF15X'] + op['OPDSF15X']
    op_proc['MR'] = op['OPFMR15X'] + op['OPDMR15X']
    op_proc['MD'] = op['OPFMD15X'] + op['OPDMD15X']
    op_proc['PV'] = op['OPFPV15X'] + op['OPDPV15X']
    op_proc['VA'] = op['OPFVA15X'] + op['OPDVA15X']
    op_proc['TR'] = op['OPFTR15X'] + op['OPDTR15X']
    op_proc['OF'] = op['OPFOF15X'] + op['OPDOF15X']
    op_proc['SL'] = op['OPFSL15X'] + op['OPDSL15X']
    op_proc['WC'] = op['OPFWC15X'] + op['OPDWC15X']
    op_proc['OR'] = op['OPFOR15X'] + op['OPDOR15X']
    op_proc['OU'] = op['OPFOU15X'] + op['OPDOU15X']
    op_proc['OT'] = op['OPFOT15X'] + op['OPDOT15X']
    op_proc = op_proc.rename(columns={'OPXP15X': 'TOTEXP'})
    op_proc['EVNTYP'] = 'AMBU'
    op_proc = op_proc[op_proc['TOTEXP'] >= 0]
    
    # 6) Combine all events into one dataset
    keep_cols = ['EVNTIDX', 'TOTEXP', 'SF', 'MR', 'MD', 'PV', 'VA', 'TR', 'OF', 'SL', 'WC', 'OR', 'OU', 'OT', 'EVNTYP']
    
    allevent = pd.concat([
        ob_proc[keep_cols],
        er_proc[keep_cols],
        ip_proc[keep_cols],
        hh_proc[keep_cols],
        op_proc[keep_cols],
        pmed_agg[keep_cols]
    ], ignore_index=True)
    
    print(f"\nTotal events in combined file: {len(allevent):,}")
    print("\nEvent type distribution:")
    print(allevent['EVNTYP'].value_counts())
    
    # 7) Subset events to those only with diabetes
    diab4 = diab3.merge(allevent, on='EVNTIDX', how='inner')
    print(f"\nEvents associated with diabetes: {len(diab4):,}")
    
    # 8) Calculate estimates - aggregate to person level
    person_exp = diab4.groupby('DUPERSID').agg({
        'TOTEXP': 'sum', 'SF': 'sum', 'MR': 'sum', 'MD': 'sum', 'PV': 'sum',
        'VA': 'sum', 'TR': 'sum', 'OF': 'sum', 'SL': 'sum', 'WC': 'sum',
        'OR': 'sum', 'OU': 'sum', 'OT': 'sum'
    }).reset_index()
    
    # Merge with FY file
    fyc_file = data_dir / "h181.sas7bdat"
    fyc = load_sas_data(fyc_file, columns=['DUPERSID', 'VARPSU', 'VARSTR', 'PERWT15F'])
    
    fy = fyc.merge(person_exp, on='DUPERSID', how='left')
    
    # Create diabetes flag
    fy['DIABPERS'] = fy['TOTEXP'].notna().astype(int)
    fy['DIABPERS'] = fy['DIABPERS'].replace({1: 1, 0: 2})
    
    # Fill missing values
    for col in ['TOTEXP', 'SF', 'MR', 'MD', 'PV', 'VA', 'TR', 'OF', 'SL', 'WC', 'OR', 'OU', 'OT']:
        fy[col] = fy[col].fillna(0)
    
    # Calculate estimates for persons with diabetes
    print("\n" + "=" * 60)
    print("EXPENDITURES FOR EVENTS ASSOCIATED WITH DIABETES, 2015")
    print("=" * 60)
    
    fy_diab = fy[fy['DIABPERS'] == 1].copy()
    
    design = SurveyDesign(
        data=fy_diab,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT15F'
    )
    
    print(f"\nN (unweighted): {len(fy_diab):,}")
    print(f"Population Size: {fy_diab['PERWT15F'].sum():,.0f}")
    
    # Total expenditure
    total_result = survey_total(design, 'TOTEXP')
    mean_result = survey_mean(design, 'TOTEXP')
    print(f"\nTotal Expenditure for Diabetes-Related Events:")
    print(f"  Total: ${total_result['total'].values[0]:,.0f}")
    print(f"  SE: ${total_result['se'].values[0]:,.0f}")
    print(f"  Mean per person: ${mean_result['mean'].values[0]:,.2f}")
    print(f"  SE of Mean: ${mean_result['se'].values[0]:.2f}")
    
    # By source of payment
    print("\nBy Source of Payment:")
    sop_labels = {
        'SF': 'Self/Family', 'MR': 'Medicare', 'MD': 'Medicaid',
        'PV': 'Private Insurance', 'VA': 'Veterans', 'TR': 'TRICARE',
        'OF': 'Other Federal', 'SL': 'State & Local', 'WC': 'Workers Comp',
        'OR': 'Other Private', 'OU': 'Other Public', 'OT': 'Other Insurance'
    }
    
    for sop, label in sop_labels.items():
        sop_total = survey_total(design, sop)
        print(f"  {label}: ${sop_total['total'].values[0]:,.0f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
