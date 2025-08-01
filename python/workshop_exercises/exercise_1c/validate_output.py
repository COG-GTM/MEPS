#!/usr/bin/env python3
"""
Validation script to programmatically compare Python output against SAS output
for MEPS Exercise 1c analysis.
"""

import pandas as pd
import numpy as np
import re
from pathlib import Path
import sys
from typing import Dict, List, Tuple, Any
import subprocess

def parse_sas_output(sas_output_path: Path) -> Dict[str, Any]:
    """Parse the SAS output file to extract key statistics"""
    
    with open(sas_output_path, 'r') as f:
        content = f.read()
    
    results = {}
    
    data_summary_match = re.search(r'Number of Strata\s+(\d+)', content)
    if data_summary_match:
        results['n_strata'] = int(data_summary_match.group(1))
    
    clusters_match = re.search(r'Number of Clusters\s+(\d+)', content)
    if clusters_match:
        results['n_clusters'] = int(clusters_match.group(1))
    
    obs_used_match = re.search(r'Number of Observations Used\s+(\d+)', content)
    if obs_used_match:
        results['n_obs_used'] = int(obs_used_match.group(1))
    
    sum_weights_match = re.search(r'Sum of Weights\s+(\d+)', content)
    if sum_weights_match:
        results['sum_weights'] = int(sum_weights_match.group(1))
    
    any_expense_match = re.search(r'Any Expense\s+\d+\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+(\d+)', content)
    if any_expense_match:
        results['any_expense_mean'] = float(any_expense_match.group(1))
        results['any_expense_stderr'] = float(any_expense_match.group(2))
        results['any_expense_sum'] = int(any_expense_match.group(3))
    
    no_expense_match = re.search(r'No Expense\s+\d+\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+(\d+)', content)
    if no_expense_match:
        results['no_expense_mean'] = float(no_expense_match.group(1))
        results['no_expense_stderr'] = float(no_expense_match.group(2))
        results['no_expense_sum'] = int(no_expense_match.group(3))
    
    overall_stats_match = re.search(r'TOTEXP18\s+TOTAL HEALTH CARE\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.E+]+)', content)
    if overall_stats_match:
        results['overall_n'] = int(overall_stats_match.group(1))
        results['overall_mean'] = float(overall_stats_match.group(2))
        results['overall_stderr'] = float(overall_stats_match.group(3))
    
    overall_median_match = re.search(r'50 Median\s+([\d.]+)\s+([\d.]+)', content)
    if overall_median_match:
        results['overall_median'] = float(overall_median_match.group(1))
    
    domain_stats_match = re.search(r'Any Expense\s+TOTEXP18\s+TOTAL HEALTH CARE\s+(\d+)\s+([\d.]+)\s+([\d.]+)', content)
    if domain_stats_match:
        results['domain_any_expense_n'] = int(domain_stats_match.group(1))
        results['domain_any_expense_mean'] = float(domain_stats_match.group(2))
        results['domain_any_expense_stderr'] = float(domain_stats_match.group(3))
    
    domain_median_match = re.search(r'Any Expense\s+TOTEXP18\s+TOTAL HEALTH CARE\s+50 Median\s+([\d.]+)', content)
    if domain_median_match:
        results['domain_any_expense_median'] = float(domain_median_match.group(1))
    
    age_0_64_match = re.search(r'Any Expense\s+0-64\s+TOTEXP18\s+TOTAL HEALTH CARE\s+(\d+)\s+([\d.]+)', content)
    if age_0_64_match:
        results['age_0_64_n'] = int(age_0_64_match.group(1))
        results['age_0_64_mean'] = float(age_0_64_match.group(2))
    
    age_65_plus_match = re.search(r'65\+\s+TOTEXP18\s+TOTAL HEALTH CARE\s+(\d+)\s+([\d.]+)', content)
    if age_65_plus_match:
        results['age_65_plus_n'] = int(age_65_plus_match.group(1))
        results['age_65_plus_mean'] = float(age_65_plus_match.group(2))
    
    age_0_64_median_match = re.search(r'Any Expense\s+0-64\s+TOTEXP18\s+TOTAL HEALTH CARE\s+50 Median\s+([\d.]+)', content)
    if age_0_64_median_match:
        results['age_0_64_median'] = float(age_0_64_median_match.group(1))
    
    age_65_plus_median_match = re.search(r'65\+\s+TOTEXP18\s+TOTAL HEALTH CARE\s+50 Median\s+([\d.]+)', content)
    if age_65_plus_median_match:
        results['age_65_plus_median'] = float(age_65_plus_median_match.group(1))
    
    return results

def run_python_script_and_capture_output(script_path: Path) -> str:
    """Run the Python script and capture its output"""
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=script_path.parent.parent.parent
        )
        if result.returncode != 0:
            print(f"Error running Python script: {result.stderr}")
            return ""
        return result.stdout
    except Exception as e:
        print(f"Exception running Python script: {e}")
        return ""

def parse_python_output(python_output: str) -> Dict[str, Any]:
    """Parse the Python script output to extract key statistics"""
    
    results = {}
    
    strata_match = re.search(r'Number of Strata\s+(\d+)', python_output)
    if strata_match:
        results['n_strata'] = int(strata_match.group(1))
    
    clusters_match = re.search(r'Number of Clusters\s+(\d+)', python_output)
    if clusters_match:
        results['n_clusters'] = int(clusters_match.group(1))
    
    obs_used_match = re.search(r'Number of Observations Used\s+(\d+)', python_output)
    if obs_used_match:
        results['n_obs_used'] = int(obs_used_match.group(1))
    
    sum_weights_match = re.search(r'Sum of Weights\s+(\d+)', python_output)
    if sum_weights_match:
        results['sum_weights'] = int(sum_weights_match.group(1))
    
    any_expense_stats = re.search(r'Any Expense\s+\d+\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+(\d+)', python_output)
    if any_expense_stats:
        results['any_expense_mean'] = float(any_expense_stats.group(1))
        results['any_expense_stderr'] = float(any_expense_stats.group(2))
        results['any_expense_sum'] = int(any_expense_stats.group(3))
    
    no_expense_stats = re.search(r'No Expense\s+\d+\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+(\d+)', python_output)
    if no_expense_stats:
        results['no_expense_mean'] = float(no_expense_stats.group(1))
        results['no_expense_stderr'] = float(no_expense_stats.group(2))
        results['no_expense_sum'] = int(no_expense_stats.group(3))
    
    overall_stats = re.search(r'TOTEXP18\s+TOTAL HEALTH CARE\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.E+]+)', python_output)
    if overall_stats:
        results['overall_n'] = int(overall_stats.group(1))
        results['overall_mean'] = float(overall_stats.group(2))
        results['overall_stderr'] = float(overall_stats.group(3))
    
    overall_median = re.search(r'50 Median\s+([\d.]+)\s+[\d.]+\s+[\d.]+ [\d.]+', python_output)
    if overall_median:
        results['overall_median'] = float(overall_median.group(1))
    
    domain_stats = re.search(r'Any Expense\s+TOTEXP18\s+TOTAL HEALTH CARE\s+(\d+)\s+([\d.]+)\s+([\d.]+)', python_output)
    if domain_stats:
        results['domain_any_expense_n'] = int(domain_stats.group(1))
        results['domain_any_expense_mean'] = float(domain_stats.group(2))
        results['domain_any_expense_stderr'] = float(domain_stats.group(3))
    
    domain_median = re.search(r'Any Expense\s+TOTEXP18\s+TOTAL HEALTH CARE\s+50 Median\s+([\d.]+)', python_output)
    if domain_median:
        results['domain_any_expense_median'] = float(domain_median.group(1))
    
    age_0_64_stats = re.search(r'Any Expense\s+0-64\s+TOTEXP18\s+TOTAL HEALTH CARE\s+(\d+)\s+([\d.]+)\s+([\d.]+)', python_output)
    if age_0_64_stats:
        results['age_0_64_n'] = int(age_0_64_stats.group(1))
        results['age_0_64_mean'] = float(age_0_64_stats.group(2))
    
    age_65_plus_stats = re.search(r'Any Expense\s+65\+\s+TOTEXP18\s+TOTAL HEALTH CARE\s+(\d+)\s+([\d.]+)\s+([\d.]+)', python_output)
    if age_65_plus_stats:
        results['age_65_plus_n'] = int(age_65_plus_stats.group(1))
        results['age_65_plus_mean'] = float(age_65_plus_stats.group(2))
    
    age_0_64_median = re.search(r'Any Expense\s+0-64\s+TOTEXP18\s+TOTAL HEALTH CARE\s+50 Median\s+([\d.]+)', python_output)
    if age_0_64_median:
        results['age_0_64_median'] = float(age_0_64_median.group(1))
    
    age_65_plus_median = re.search(r'Any Expense\s+65\+\s+TOTEXP18\s+TOTAL HEALTH CARE\s+50 Median\s+([\d.]+)', python_output)
    if age_65_plus_median:
        results['age_65_plus_median'] = float(age_65_plus_median.group(1))
    
    return results

def compare_results(sas_results: Dict[str, Any], python_results: Dict[str, Any], tolerance: float = 0.01) -> List[str]:
    """Compare SAS and Python results and return list of discrepancies"""
    
    discrepancies = []
    
    comparisons = [
        ('n_strata', 'Number of Strata', 'exact'),
        ('n_clusters', 'Number of Clusters', 'exact'),
        ('n_obs_used', 'Number of Observations Used', 'exact'),
        ('sum_weights', 'Sum of Weights', 'exact'),
        ('any_expense_mean', 'Any Expense Mean', 'relative'),
        ('no_expense_mean', 'No Expense Mean', 'relative'),
        ('any_expense_sum', 'Any Expense Sum', 'exact'),
        ('no_expense_sum', 'No Expense Sum', 'exact'),
        ('overall_mean', 'Overall Mean Expense', 'relative'),
        ('overall_median', 'Overall Median Expense', 'relative'),
        ('domain_any_expense_mean', 'Domain Any Expense Mean', 'relative'),
        ('domain_any_expense_median', 'Domain Any Expense Median', 'relative'),
        ('age_0_64_mean', 'Age 0-64 Mean', 'relative'),
        ('age_65_plus_mean', 'Age 65+ Mean', 'relative'),
        ('age_0_64_median', 'Age 0-64 Median', 'relative'),
        ('age_65_plus_median', 'Age 65+ Median', 'relative'),
    ]
    
    for key, description, comparison_type in comparisons:
        if key in sas_results and key in python_results:
            sas_val = sas_results[key]
            python_val = python_results[key]
            
            if comparison_type == 'exact':
                if sas_val != python_val:
                    discrepancies.append(f"{description}: SAS={sas_val}, Python={python_val} (EXACT MISMATCH)")
            elif comparison_type == 'relative':
                if sas_val != 0:
                    relative_diff = abs(sas_val - python_val) / abs(sas_val)
                    if relative_diff > tolerance:
                        discrepancies.append(f"{description}: SAS={sas_val:.6f}, Python={python_val:.6f} (Relative diff: {relative_diff:.4f})")
                else:
                    if abs(python_val) > tolerance:
                        discrepancies.append(f"{description}: SAS={sas_val}, Python={python_val} (Absolute diff when SAS=0)")
        elif key in sas_results:
            discrepancies.append(f"{description}: Missing in Python output (SAS={sas_results[key]})")
        elif key in python_results:
            discrepancies.append(f"{description}: Missing in SAS output (Python={python_results[key]})")
    
    return discrepancies

def main():
    """Main validation function"""
    print("MEPS Exercise 1c Output Validation")
    print("=" * 50)
    
    base_path = Path(__file__).parent.parent.parent.parent
    sas_output_path = base_path / "SAS" / "workshop_exercises" / "exercise_1c" / "Exercise1c_OUTPUT.TXT"
    python_script_path = Path(__file__).parent / "exercise1c.py"
    
    if not sas_output_path.exists():
        print(f"Error: SAS output file not found at {sas_output_path}")
        sys.exit(1)
    
    if not python_script_path.exists():
        print(f"Error: Python script not found at {python_script_path}")
        sys.exit(1)
    
    print(f"Parsing SAS output from: {sas_output_path}")
    sas_results = parse_sas_output(sas_output_path)
    print(f"Extracted {len(sas_results)} metrics from SAS output")
    
    print(f"\nRunning Python script: {python_script_path}")
    python_output = run_python_script_and_capture_output(python_script_path)
    
    if not python_output:
        print("Error: Could not capture Python script output")
        sys.exit(1)
    
    print("Parsing Python output...")
    python_results = parse_python_output(python_output)
    print(f"Extracted {len(python_results)} metrics from Python output")
    
    print("\nComparing results...")
    discrepancies = compare_results(sas_results, python_results)
    
    print("\n" + "=" * 50)
    print("VALIDATION RESULTS")
    print("=" * 50)
    
    if not discrepancies:
        print("✅ SUCCESS: All metrics match within tolerance!")
        print("Python implementation produces equivalent results to SAS.")
    else:
        print(f"❌ DISCREPANCIES FOUND: {len(discrepancies)} issues detected")
        print("\nDetailed discrepancies:")
        for i, discrepancy in enumerate(discrepancies, 1):
            print(f"{i:2d}. {discrepancy}")
    
    print(f"\nSAS Results Summary:")
    for key, value in sorted(sas_results.items()):
        print(f"  {key}: {value}")
    
    print(f"\nPython Results Summary:")
    for key, value in sorted(python_results.items()):
        print(f"  {key}: {value}")
    
    sys.exit(0 if not discrepancies else 1)

if __name__ == "__main__":
    main()
