"""
This script compares the Python output with the SAS output to verify that the
conversion is accurate. It extracts key statistics from both outputs and compares them.
"""

import re
import numpy as np

def extract_values(file_path):
    """Extract numerical values from output file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    patterns = {
        "no_expense_percent": r"No Expense\s+\d+\s+\d+\s+\d+\s+(\d+\.\d+)",
        "any_expense_percent": r"Any Expense\s+\d+\s+\d+\s+\d+\s+(\d+\.\d+)",
        "overall_mean": r"TOTEXP18\s+TOTAL HEALTH CARE\s+\d+\s+(\d+\.\d+)",
        "overall_median": r"TOTEXP18\s+TOTAL HEALTH CARE\s+50 Median\s+(\d+\.\d+)",
        "any_expense_mean": r"Any Expense\s+TOTEXP18\s+TOTAL HEALTH CARE\s+\d+\s+(\d+\.\d+)",
        "any_expense_median": r"Any Expense\s+TOTEXP18\s+TOTAL HEALTH CARE\s+50 Median\s+(\d+\.\d+)",
        "age_0_64_mean": r"Any Expense\s+0-64\s+TOTEXP18\s+TOTAL HEALTH CARE\s+\d+\s+(\d+\.\d+)",
        "age_0_64_median": r"Any Expense\s+0-64\s+TOTEXP18\s+TOTAL HEALTH CARE\s+50 Median\s+(\d+\.\d+)",
        "age_65plus_mean": r"Any Expense\s+65\+\s+TOTEXP18\s+TOTAL HEALTH CARE\s+\d+\s+(\d+\.\d+)",
        "age_65plus_median": r"Any Expense\s+65\+\s+TOTEXP18\s+TOTAL HEALTH CARE\s+50 Median\s+(\d+\.\d+)"
    }
    
    results = {}
    for key, pattern in patterns.items():
        matches = re.findall(pattern, content)
        if matches:
            results[key] = float(matches[0])
        else:
            results[key] = None
    
    return results

def compare_values(sas_values, python_values, tolerance=0.05):
    """Compare values with a tolerance"""
    print("Comparing SAS and Python outputs:")
    print("-" * 80)
    print(f"{'Statistic':<25} {'SAS Value':<15} {'Python Value':<15} {'Difference':<15} {'% Diff':<10} {'Pass?':<5}")
    print("-" * 80)
    
    all_pass = True
    for key in sas_values:
        if sas_values[key] is None or python_values[key] is None:
            print(f"{key:<25} {'N/A':<15} {'N/A':<15} {'N/A':<15} {'N/A':<10} {'N/A':<5}")
            continue
        
        diff = abs(sas_values[key] - python_values[key])
        pct_diff = diff / sas_values[key] * 100 if sas_values[key] != 0 else 0
        pass_test = pct_diff <= tolerance * 100
        
        if not pass_test:
            all_pass = False
        
        print(f"{key:<25} {sas_values[key]:<15.6f} {python_values[key]:<15.6f} {diff:<15.6f} {pct_diff:<10.2f}% {'Yes' if pass_test else 'No':<5}")
    
    print("-" * 80)
    if all_pass:
        print("All values match within the tolerance!")
    else:
        print("Some values do not match within the tolerance.")
    
    return all_pass

def main():
    sas_output_path = "/home/ubuntu/repos/MEPS/SAS/workshop_exercises/exercise_1c/Exercise1c_OUTPUT.TXT"
    python_output_path = "/home/ubuntu/repos/MEPS/Python/workshop_exercises/exercise_1c/Exercise1c_Python_OUTPUT.TXT"
    
    print(f"Extracting values from SAS output: {sas_output_path}")
    sas_values = extract_values(sas_output_path)
    
    print(f"Extracting values from Python output: {python_output_path}")
    python_values = extract_values(python_output_path)
    
    print("\nExtracted values from SAS output:")
    for key, value in sas_values.items():
        print(f"{key}: {value}")
    
    print("\nExtracted values from Python output:")
    for key, value in python_values.items():
        print(f"{key}: {value}")
    
    print("\nComparison results:")
    compare_values(sas_values, python_values)

if __name__ == "__main__":
    main()
