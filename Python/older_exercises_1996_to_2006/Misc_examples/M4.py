"""
AHRQ MEPS Data Users Workshop - Misc Example M4

This example illustrates two ways of determining the number of events
associated with conditions:
(1) Using the evNUM variables on the Conditions file
(2) Using the number of matches between the Conditions file and CLNK file

About 76% of conditions listed on the Medical Conditions file are
associated with one or more events.

Note: Because persons can have more than one reported condition, and a
condition can be associated with more than one event, the counts computed
here for the condition level will not equal person- or event-level counts.

Input files:
    - h78.sas7bdat (2003 Medical Conditions File)
    - h77i1.sas7bdat (2003 CLNK File)

Python equivalent of: SAS/older_exercises_1996_to_2006/Misc_examples/M4/M4.sas
"""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from meps_utils import load_sas_data


def main():
    # Set data directory - adjust as needed
    data_dir = Path("C:/MEPS/DATA")
    
    print("=" * 80)
    print("AHRQ MEPS DATA USERS WORKSHOP")
    print("COMPUTING NUMBER OF EVENTS ASSOCIATED WITH CONDITIONS")
    print("=" * 80)
    
    # Load Conditions file
    print("\n" + "-" * 60)
    print("METHOD 1: USING evNUM VARIABLES FROM CONDITIONS FILE")
    print("-" * 60)
    
    cond_file = data_dir / "h78.sas7bdat"
    print(f"Loading conditions data from: {cond_file}")
    
    cond_num = load_sas_data(cond_file, columns=[
        'CONDIDX', 'ERNUM', 'HHNUM', 'IPNUM', 'OBNUM', 'OPNUM', 'RXNUM'
    ])
    
    # Calculate total number of events
    cond_num['TOTNUM'] = (cond_num['ERNUM'] + cond_num['HHNUM'] + cond_num['IPNUM'] + 
                          cond_num['OBNUM'] + cond_num['OPNUM'] + cond_num['RXNUM'])
    
    print(f"Total condition records: {len(cond_num):,}")
    
    # Load CLNK file
    print("\n" + "-" * 60)
    print("METHOD 2: COUNTING MATCHES FROM CLNK FILE")
    print("-" * 60)
    
    clnk_file = data_dir / "h77i1.sas7bdat"
    print(f"Loading CLNK data from: {clnk_file}")
    
    clnk = load_sas_data(clnk_file, columns=['CONDIDX', 'EVENTYPE'])
    print(f"Total CLNK records: {len(clnk):,}")
    
    # Count events by type for each condition
    # EVENTYPE: 1=OB, 2=OP, 3=ER, 4=IP, 7=HH, 8=RX
    eventype_map = {1: 'OBCNT', 2: 'OPCNT', 3: 'ERCNT', 4: 'IPCNT', 7: 'HHCNT', 8: 'RXCNT'}
    
    # Create pivot table to count events by type
    cond_cnt = clnk.groupby(['CONDIDX', 'EVENTYPE']).size().unstack(fill_value=0)
    cond_cnt.columns = [eventype_map.get(c, f'TYPE{c}') for c in cond_cnt.columns]
    cond_cnt = cond_cnt.reset_index()
    
    # Ensure all columns exist
    for col in ['ERCNT', 'HHCNT', 'IPCNT', 'OBCNT', 'OPCNT', 'RXCNT']:
        if col not in cond_cnt.columns:
            cond_cnt[col] = 0
    
    # Calculate total count
    cond_cnt['TOTCNT'] = (cond_cnt['ERCNT'] + cond_cnt['HHCNT'] + cond_cnt['IPCNT'] + 
                          cond_cnt['OBCNT'] + cond_cnt['OPCNT'] + cond_cnt['RXCNT'])
    
    print(f"Conditions with events: {len(cond_cnt):,}")
    
    # Merge the two datasets
    print("\n" + "-" * 60)
    print("MERGING CONDITIONS FILE WITH CLNK COUNTS")
    print("-" * 60)
    
    cond2003 = cond_num.merge(cond_cnt, on='CONDIDX', how='outer')
    
    # Fill missing values with 0
    for col in ['ERCNT', 'HHCNT', 'IPCNT', 'OBCNT', 'OPCNT', 'RXCNT', 'TOTCNT']:
        cond2003[col] = cond2003[col].fillna(0).astype(int)
    
    # Count merge results
    both = len(cond2003[(cond2003['TOTNUM'].notna()) & (cond2003['TOTCNT'] > 0)])
    just_cond = len(cond2003[(cond2003['TOTNUM'].notna()) & (cond2003['TOTCNT'] == 0)])
    just_clnk = len(cond2003[(cond2003['TOTNUM'].isna()) & (cond2003['TOTCNT'] > 0)])
    
    print(f"Records in both files: {both:,}")
    print(f"Records only in conditions file: {just_cond:,}")
    print(f"Records only in CLNK file: {just_clnk:,}")
    
    # Compare evNUM from conditions file with counts from CLNK
    print("\n" + "=" * 80)
    print("COMPARISON: evNUM FROM CONDITIONS FILE vs evCNT FROM CLNK MATCHES")
    print("=" * 80)
    
    # Create bins for display
    def bin_events(x):
        if pd.isna(x) or x == 0:
            return '0'
        elif x <= 10:
            return '1-10'
        elif x <= 25:
            return '11-25'
        elif x <= 50:
            return '26-50'
        else:
            return '51+'
    
    # Total events comparison
    print("\n" + "-" * 60)
    print("TOTAL EVENTS")
    print("-" * 60)
    
    cond2003['TOTNUM_BIN'] = cond2003['TOTNUM'].apply(bin_events)
    cond2003['TOTCNT_BIN'] = cond2003['TOTCNT'].apply(bin_events)
    
    print(pd.crosstab(cond2003['TOTNUM_BIN'], cond2003['TOTCNT_BIN'], margins=True))
    
    # Event type comparisons
    event_pairs = [
        ('ERNUM', 'ERCNT', 'Emergency Room'),
        ('HHNUM', 'HHCNT', 'Home Health'),
        ('IPNUM', 'IPCNT', 'Inpatient'),
        ('OBNUM', 'OBCNT', 'Office-Based'),
        ('OPNUM', 'OPCNT', 'Outpatient'),
        ('RXNUM', 'RXCNT', 'Prescribed Medicines')
    ]
    
    for num_col, cnt_col, label in event_pairs:
        print(f"\n{label}:")
        cond2003[f'{num_col}_BIN'] = cond2003[num_col].apply(bin_events)
        cond2003[f'{cnt_col}_BIN'] = cond2003[cnt_col].apply(bin_events)
        print(pd.crosstab(cond2003[f'{num_col}_BIN'], cond2003[f'{cnt_col}_BIN'], margins=True))
    
    print("\n" + "=" * 80)
    print("Analysis complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
