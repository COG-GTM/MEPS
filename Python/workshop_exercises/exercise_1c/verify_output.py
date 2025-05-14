"""
This script compares the output of the Python version of Exercise1c with the SAS output.
It extracts key statistics from both outputs and reports any significant differences.
"""

import os
import re
import numpy as np

def extract_statistics(file_path):
    """Extract key statistics from the output file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    stats = {}
    
    match = re.search(r'WITH_AN_EXPENSE\s+No Expense\s+\d+\s+([\d\.]+)', content)
    if match:
        stats['no_expense_percent'] = float(match.group(1))
    
    match = re.search(r'WITH_AN_EXPENSE\s+Any Expense\s+\d+\s+([\d\.]+)', content)
    if match:
        stats['any_expense_percent'] = float(match.group(1))
    
    match = re.search(r'TOTEXP18\s+TOTAL HEALTH CARE\s+\d+\s+([\d\.]+)', content)
    if match:
        stats['mean_expense_per_person'] = float(match.group(1))
    
    pattern = r'Any Expense\s+TOTEXP18\s+TOTAL HEALTH CARE\s+\d+\s+([\d\.]+)'
    matches = re.findall(pattern, content)
    if matches:
        stats['mean_expense_with_expense'] = float(matches[0])
    
    pattern = r'Any Expense\s+TOTEXP18\s+TOTAL HEALTH CARE\s+50 Median\s+([\d\.]+)'
    matches = re.findall(pattern, content)
    if matches:
        stats['median_expense_with_expense'] = float(matches[0])
    
    pattern = r'Any Expense\s+0-64\s+TOTEXP18\s+TOTAL HEALTH CARE\s+\d+\s+([\d\.]+)'
    matches = re.findall(pattern, content)
    if matches:
        stats['mean_expense_0_64'] = float(matches[0])
    
    pattern = r'Any Expense\s+65\+\s+TOTEXP18\s+TOTAL HEALTH CARE\s+\d+\s+([\d\.]+)'
    matches = re.findall(pattern, content)
    if matches:
        stats['mean_expense_65plus'] = float(matches[0])
    
    pattern = r'Any Expense\s+0-64\s+TOTEXP18\s+TOTAL HEALTH CARE\s+50 Median\s+([\d\.]+)'
    matches = re.findall(pattern, content)
    if matches:
        stats['median_expense_0_64'] = float(matches[0])
    
    pattern = r'Any Expense\s+65\+\s+TOTEXP18\s+TOTAL HEALTH CARE\s+50 Median\s+([\d\.]+)'
    matches = re.findall(pattern, content)
    if matches:
        stats['median_expense_65plus'] = float(matches[0])
    
    return stats

def compare_statistics(sas_stats, python_stats, tolerance=0.05):
    """Compare statistics from SAS and Python outputs"""
    print("Comparing SAS and Python statistics:")
    print("=" * 80)
    print(f"{'Statistic':<30} {'SAS Value':<15} {'Python Value':<15} {'Difference %':<15} {'Within Tolerance':<15}")
    print("-" * 80)
    
    all_within_tolerance = True
    
    for key in sas_stats:
        if key in python_stats:
            sas_value = sas_stats[key]
            python_value = python_stats[key]
            
            if sas_value != 0:
                diff_percent = abs((python_value - sas_value) / sas_value) * 100
            else:
                diff_percent = abs(python_value - sas_value) * 100
            
            within_tolerance = diff_percent <= tolerance * 100
            
            if not within_tolerance:
                all_within_tolerance = False
            
            print(f"{key:<30} {sas_value:<15.6f} {python_value:<15.6f} {diff_percent:<15.2f} {'Yes' if within_tolerance else 'No':<15}")
        else:
            print(f"{key:<30} {sas_stats[key]:<15.6f} {'Not found':<15} {'N/A':<15} {'No':<15}")
            all_within_tolerance = False
    
    for key in python_stats:
        if key not in sas_stats:
            print(f"{key:<30} {'Not found':<15} {python_stats[key]:<15.6f} {'N/A':<15} {'No':<15}")
            all_within_tolerance = False
    
    print("=" * 80)
    if all_within_tolerance:
        print("All statistics are within the tolerance level. Verification PASSED!")
    else:
        print("Some statistics are outside the tolerance level. Verification FAILED!")
    
    return all_within_tolerance

def main():
    sas_output_path = os.path.expanduser("~/repos/MEPS/SAS/workshop_exercises/exercise_1c/Exercise1c_OUTPUT.TXT")
    python_output_path = os.path.expanduser("~/repos/MEPS/Python/workshop_exercises/exercise_1c/Exercise1c_Python_OUTPUT.TXT")
    
    if not os.path.exists(sas_output_path):
        print(f"Error: SAS output file not found at {sas_output_path}")
        return False
    
    if not os.path.exists(python_output_path):
        print(f"Error: Python output file not found at {python_output_path}")
        return False
    
    print(f"Extracting statistics from SAS output: {sas_output_path}")
    sas_stats = extract_statistics(sas_output_path)
    
    print(f"Extracting statistics from Python output: {python_output_path}")
    python_stats = extract_statistics(python_output_path)
    
    success = compare_statistics(sas_stats, python_stats)
    
    return success

if __name__ == "__main__":
    main()
