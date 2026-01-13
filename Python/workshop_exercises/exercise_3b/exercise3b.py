"""
DESCRIPTION: THIS PROGRAM ILLUSTRATES HOW TO CALCULATE EXPENDITURES FOR ALL EVENTS ASSOCIATED WITH A CONDITION

             THE CONDITION USED IN THIS EXERCISE IS DIABETES (CCS CODE=049 OR 050)

INPUT FILES:  1) H181.SAS7BDAT    (2015 FY PUF DATA)
              2) H180.SAS7BDAT    (2015 CONDITION PUF DATA)
              3) H178A.SAS7BDAT   (2015 PMED PUF DATA)
              4) H178D.SAS7BDAT   (2015 INPATIENT VISITS PUF DATA)
              5) H178E.SAS7BDAT   (2015 EROM VISITS PUF DATA)
              6) H178F.SAS7BDAT   (2015 OUTPATIENT VISITS PUF DATA)
              7) H178G.SAS7BDAT   (2015 OFFICE-BASED VISITS PUF DATA)
              8) H178H.SAS7BDAT   (2015 HOME HEALTH PUF DATA)
              9) H178IF1.SAS7BDAT (2015 CONDITION-EVENT LINK PUF DATA)
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meps_utils import load_sas_data, SurveyDesign, survey_mean, survey_total, print_results


def main(meps_data_path: str = "C:/MEPS/SAS/DATA"):
    """
    Main function to run the analysis.
    
    Parameters
    ----------
    meps_data_path : str
        Path to directory containing MEPS data files
    """
    
    print("AHRQ MEPS DATA USERS WORKSHOP -- 2018")
    print("EXERCISE5.SAS: CALCULATE EXPENDITURES FOR ALL EVENTS ASSOCIATED WITH A CONDITION (DIABETES)")
    print("="*80)
    
    # Source of payment columns
    sop_cols = ['SF', 'MR', 'MD', 'PV', 'VA', 'TR', 'OF', 'SL', 'WC', 'OR', 'OU', 'OT', 'TOTEXP']
    sop_labels = {
        'SF': 'SOURCE OF PAYMENT: FAMILY',
        'MR': 'SOURCE OF PAYMENT: MEDICARE',
        'MD': 'SOURCE OF PAYMENT: MEDICAID',
        'PV': 'SOURCE OF PAYMENT: PRIVATE INSURANCE',
        'VA': 'SOURCE OF PAYMENT: VETERANS',
        'TR': 'SOURCE OF PAYMENT: TRICARE',
        'OF': 'SOURCE OF PAYMENT: OTHER FEDERAL',
        'SL': 'SOURCE OF PAYMENT: STATE & LOCAL GOV',
        'WC': 'SOURCE OF PAYMENT: WORKERS COMP',
        'OR': 'SOURCE OF PAYMENT: OTHER PRIVATE',
        'OU': 'SOURCE OF PAYMENT: OTHER PUBLIC',
        'OT': 'SOURCE OF PAYMENT: OTHER INSURANCE',
        'TOTEXP': 'TOTAL EXPENDITURE FOR EVENT'
    }
    
    # 1) PULL OUT CONDITIONS WITH DIABETES (CCS CODE='049', '050') FROM 2015 CONDITION PUF - HC180
    print("\nLoading 2015 Condition file...")
    h180 = load_sas_data(os.path.join(meps_data_path, "H180.sas7bdat"))
    
    diab = h180[h180['CCCODEX'].isin(['049', '050'])].copy()
    
    print("\nCHECK CCS CODES:")
    print(diab['CCCODEX'].value_counts())
    
    # 2) GET EVENT ID FOR THE DIABETIC CONDITIONS FROM CONDITION-EVENT LINK FILE
    print("\nLoading Condition-Event Link file...")
    h178if1 = load_sas_data(os.path.join(meps_data_path, "H178IF1.sas7bdat"))
    
    diab2 = pd.merge(
        diab[['DUPERSID', 'CONDIDX', 'CCCODEX']],
        h178if1[['CONDIDX', 'EVNTIDX']],
        on='CONDIDX',
        how='inner'
    )
    
    print("\nSAMPLE DUMP FOR CONDITION-EVENT LINK FILE:")
    print(diab2.head(20))
    
    # 3) DELETE DUPLICATE CASES PER EVENT
    diab3 = diab2[['DUPERSID', 'EVNTIDX']].drop_duplicates(subset=['EVNTIDX'])
    
    print("\nSAMPLE DUMP AFTER DUPLICATE CASES ARE DELETED:")
    print(diab3.head(30))
    
    # 4) Load and process event files
    print("\nLoading event files...")
    
    # PMED file
    h178a = load_sas_data(os.path.join(meps_data_path, "H178A.sas7bdat"))
    h178a['EVNTIDX'] = h178a['LINKIDX']
    
    # Sum PMED to event level
    pmed_cols = ['RXXP15X', 'RXSF15X', 'RXMR15X', 'RXMD15X', 'RXPV15X', 'RXVA15X', 
                 'RXTR15X', 'RXOF15X', 'RXSL15X', 'RXWC15X', 'RXOR15X', 'RXOU15X', 'RXOT15X']
    pmed_cols = [c for c in pmed_cols if c in h178a.columns]
    
    pmed2 = h178a.groupby('EVNTIDX')[pmed_cols].sum().reset_index()
    
    # Rename columns
    pmed3 = pd.DataFrame()
    pmed3['EVNTIDX'] = pmed2['EVNTIDX']
    pmed3['TOTEXP'] = pmed2.get('RXXP15X', 0)
    pmed3['SF'] = pmed2.get('RXSF15X', 0)
    pmed3['MR'] = pmed2.get('RXMR15X', 0)
    pmed3['MD'] = pmed2.get('RXMD15X', 0)
    pmed3['PV'] = pmed2.get('RXPV15X', 0)
    pmed3['VA'] = pmed2.get('RXVA15X', 0)
    pmed3['TR'] = pmed2.get('RXTR15X', 0)
    pmed3['OF'] = pmed2.get('RXOF15X', 0)
    pmed3['SL'] = pmed2.get('RXSL15X', 0)
    pmed3['WC'] = pmed2.get('RXWC15X', 0)
    pmed3['OR'] = pmed2.get('RXOR15X', 0)
    pmed3['OU'] = pmed2.get('RXOU15X', 0)
    pmed3['OT'] = pmed2.get('RXOT15X', 0)
    pmed3 = pmed3[pmed3['TOTEXP'] >= 0]
    pmed3['EVNTYP'] = 'PMED'
    
    # Office-based visits
    h178g = load_sas_data(os.path.join(meps_data_path, "H178G.sas7bdat"))
    ob = pd.DataFrame()
    ob['EVNTIDX'] = h178g['EVNTIDX']
    ob['TOTEXP'] = h178g.get('OBXP15X', 0)
    ob['SF'] = h178g.get('OBSF15X', 0)
    ob['MR'] = h178g.get('OBMR15X', 0)
    ob['MD'] = h178g.get('OBMD15X', 0)
    ob['PV'] = h178g.get('OBPV15X', 0)
    ob['VA'] = h178g.get('OBVA15X', 0)
    ob['TR'] = h178g.get('OBTR15X', 0)
    ob['OF'] = h178g.get('OBOF15X', 0)
    ob['SL'] = h178g.get('OBSL15X', 0)
    ob['WC'] = h178g.get('OBWC15X', 0)
    ob['OR'] = h178g.get('OBOR15X', 0)
    ob['OU'] = h178g.get('OBOU15X', 0)
    ob['OT'] = h178g.get('OBOT15X', 0)
    ob = ob[ob['TOTEXP'] >= 0]
    ob['EVNTYP'] = 'AMBU'
    
    # Emergency room visits
    h178e = load_sas_data(os.path.join(meps_data_path, "H178E.sas7bdat"))
    erom = pd.DataFrame()
    erom['EVNTIDX'] = h178e['EVNTIDX']
    erom['TOTEXP'] = h178e.get('ERXP15X', 0)
    erom['SF'] = h178e.get('ERFSF15X', 0) + h178e.get('ERDSF15X', 0)
    erom['MR'] = h178e.get('ERFMR15X', 0) + h178e.get('ERDMR15X', 0)
    erom['MD'] = h178e.get('ERFMD15X', 0) + h178e.get('ERDMD15X', 0)
    erom['PV'] = h178e.get('ERFPV15X', 0) + h178e.get('ERDPV15X', 0)
    erom['VA'] = h178e.get('ERFVA15X', 0) + h178e.get('ERDVA15X', 0)
    erom['TR'] = h178e.get('ERFTR15X', 0) + h178e.get('ERDTR15X', 0)
    erom['OF'] = h178e.get('ERFOF15X', 0) + h178e.get('ERDOF15X', 0)
    erom['SL'] = h178e.get('ERFSL15X', 0) + h178e.get('ERDSL15X', 0)
    erom['WC'] = h178e.get('ERFWC15X', 0) + h178e.get('ERDWC15X', 0)
    erom['OR'] = h178e.get('ERFOR15X', 0) + h178e.get('ERDOR15X', 0)
    erom['OU'] = h178e.get('ERFOU15X', 0) + h178e.get('ERDOU15X', 0)
    erom['OT'] = h178e.get('ERFOT15X', 0) + h178e.get('ERDOT15X', 0)
    erom = erom[erom['TOTEXP'] >= 0]
    erom['EVNTYP'] = 'EROM'
    
    # Inpatient stays
    h178d = load_sas_data(os.path.join(meps_data_path, "H178D.sas7bdat"))
    ipat = pd.DataFrame()
    ipat['EVNTIDX'] = h178d['EVNTIDX']
    ipat['TOTEXP'] = h178d.get('IPXP15X', 0)
    ipat['SF'] = h178d.get('IPFSF15X', 0) + h178d.get('IPDSF15X', 0)
    ipat['MR'] = h178d.get('IPFMR15X', 0) + h178d.get('IPDMR15X', 0)
    ipat['MD'] = h178d.get('IPFMD15X', 0) + h178d.get('IPDMD15X', 0)
    ipat['PV'] = h178d.get('IPFPV15X', 0) + h178d.get('IPDPV15X', 0)
    ipat['VA'] = h178d.get('IPFVA15X', 0) + h178d.get('IPDVA15X', 0)
    ipat['TR'] = h178d.get('IPFTR15X', 0) + h178d.get('IPDTR15X', 0)
    ipat['OF'] = h178d.get('IPFOF15X', 0) + h178d.get('IPDOF15X', 0)
    ipat['SL'] = h178d.get('IPFSL15X', 0) + h178d.get('IPDSL15X', 0)
    ipat['WC'] = h178d.get('IPFWC15X', 0) + h178d.get('IPDWC15X', 0)
    ipat['OR'] = h178d.get('IPFOR15X', 0) + h178d.get('IPDOR15X', 0)
    ipat['OU'] = h178d.get('IPFOU15X', 0) + h178d.get('IPDOU15X', 0)
    ipat['OT'] = h178d.get('IPFOT15X', 0) + h178d.get('IPDOT15X', 0)
    ipat = ipat[ipat['TOTEXP'] >= 0]
    ipat['EVNTYP'] = 'IPAT'
    
    # Home health
    h178h = load_sas_data(os.path.join(meps_data_path, "H178H.sas7bdat"))
    hvis = pd.DataFrame()
    hvis['EVNTIDX'] = h178h['EVNTIDX']
    hvis['TOTEXP'] = h178h.get('HHXP15X', 0)
    hvis['SF'] = h178h.get('HHSF15X', 0)
    hvis['MR'] = h178h.get('HHMR15X', 0)
    hvis['MD'] = h178h.get('HHMD15X', 0)
    hvis['PV'] = h178h.get('HHPV15X', 0)
    hvis['VA'] = h178h.get('HHVA15X', 0)
    hvis['TR'] = h178h.get('HHTR15X', 0)
    hvis['OF'] = h178h.get('HHOF15X', 0)
    hvis['SL'] = h178h.get('HHSL15X', 0)
    hvis['WC'] = h178h.get('HHWC15X', 0)
    hvis['OR'] = h178h.get('HHOR15X', 0)
    hvis['OU'] = h178h.get('HHOU15X', 0)
    hvis['OT'] = h178h.get('HHOT15X', 0)
    hvis = hvis[hvis['TOTEXP'] >= 0]
    hvis['EVNTYP'] = 'HVIS'
    
    # Outpatient visits
    h178f = load_sas_data(os.path.join(meps_data_path, "H178F.sas7bdat"))
    opat = pd.DataFrame()
    opat['EVNTIDX'] = h178f['EVNTIDX']
    opat['TOTEXP'] = h178f.get('OPXP15X', 0)
    opat['SF'] = h178f.get('OPFSF15X', 0) + h178f.get('OPDSF15X', 0)
    opat['MR'] = h178f.get('OPFMR15X', 0) + h178f.get('OPDMR15X', 0)
    opat['MD'] = h178f.get('OPFMD15X', 0) + h178f.get('OPDMD15X', 0)
    opat['PV'] = h178f.get('OPFPV15X', 0) + h178f.get('OPDPV15X', 0)
    opat['VA'] = h178f.get('OPFVA15X', 0) + h178f.get('OPDVA15X', 0)
    opat['TR'] = h178f.get('OPFTR15X', 0) + h178f.get('OPDTR15X', 0)
    opat['OF'] = h178f.get('OPFOF15X', 0) + h178f.get('OPDOF15X', 0)
    opat['SL'] = h178f.get('OPFSL15X', 0) + h178f.get('OPDSL15X', 0)
    opat['WC'] = h178f.get('OPFWC15X', 0) + h178f.get('OPDWC15X', 0)
    opat['OR'] = h178f.get('OPFOR15X', 0) + h178f.get('OPDOR15X', 0)
    opat['OU'] = h178f.get('OPFOU15X', 0) + h178f.get('OPDOU15X', 0)
    opat['OT'] = h178f.get('OPFOT15X', 0) + h178f.get('OPDOT15X', 0)
    opat = opat[opat['TOTEXP'] >= 0]
    opat['EVNTYP'] = 'AMBU'
    
    # 6) COMBINE ALL EVENTS INTO ONE DATASET
    allevent = pd.concat([ob, erom, ipat, hvis, opat, pmed3], ignore_index=True)
    allevent = allevent.sort_values('EVNTIDX')
    
    print("\nALL EVENTS ARE COMBINED INTO ONE FILE:")
    print(allevent['EVNTYP'].value_counts())
    print(allevent.head(20))
    
    # 7) SUBSET EVENTS TO THOSE ONLY WITH DIABETES
    diab4 = pd.merge(diab3, allevent, on='EVNTIDX', how='inner')
    
    print(f"\nEvents linked to diabetes: {len(diab4)}")
    
    # 8) CALCULATE ESTIMATES ON EXPENDITURES AND USE, ALL TYPES OF SERVICE
    # Sum to person level
    sum_cols = ['TOTEXP', 'SF', 'MR', 'MD', 'PV', 'VA', 'TR', 'OF', 'SL', 'WC', 'OR', 'OU', 'OT']
    all_pers = diab4.groupby('DUPERSID')[sum_cols].sum().reset_index()
    
    # Load FY file and merge
    print("\nLoading 2015 Full-Year Consolidated file...")
    h181 = load_sas_data(os.path.join(meps_data_path, "H181.sas7bdat"))
    h181 = h181[['DUPERSID', 'VARPSU', 'VARSTR', 'PERWT15F']].copy()
    
    fy1 = pd.merge(h181, all_pers, on='DUPERSID', how='left', indicator=True)
    fy1['DIABPERS'] = np.where(fy1['_merge'] == 'both', 1, 2)
    fy1 = fy1.drop('_merge', axis=1)
    
    # Fill missing values
    for col in sum_cols:
        fy1[col] = fy1[col].fillna(0)
    
    # Calculate estimates for persons with diabetes
    print("\n" + "="*80)
    print("ESTIMATES ON EXPENDITURES FOR EVENTS ASSOCIATED WITH DIABETES, 2015")
    print("="*80)
    
    fy1_diab = fy1[fy1['DIABPERS'] == 1].copy()
    
    design = SurveyDesign(
        data=fy1_diab,
        strata='VARSTR',
        cluster='VARPSU',
        weight='PERWT15F'
    )
    
    means = survey_mean(design, sum_cols)
    totals = survey_total(design, sum_cols)
    
    results = pd.merge(
        means[['Variable', 'N', 'SumWgt', 'Mean', 'StdErr']],
        totals[['Variable', 'Sum', 'StdDev']],
        on='Variable'
    )
    
    print(f"\n{'Variable':<10} {'N':>8} {'Pop Size':>15} {'Sum':>18} {'SE Sum':>15} {'Mean':>12} {'SE Mean':>10}")
    print("-" * 95)
    
    for _, row in results.iterrows():
        var = row['Variable']
        print(f"{var:<10} {row['N']:>8,.0f} {row['SumWgt']:>15,.0f} {row['Sum']:>18,.0f} {row['StdDev']:>15,.0f} {row['Mean']:>12,.2f} {row['StdErr']:>10,.2f}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='MEPS Exercise 3b - Diabetes Event Expenditures 2015')
    parser.add_argument('--data-path', type=str, default='C:/MEPS/SAS/DATA',
                        help='Path to MEPS data files')
    args = parser.parse_args()
    main(args.data_path)
