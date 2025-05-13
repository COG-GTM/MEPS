"""
This script compares the output from the Python implementation of Exercise1c
with the expected output from the SAS implementation.
"""

import os
import re
import numpy as np

def extract_numeric_values(text):
    """Extract all numeric values from a string."""
    pattern = r'[-+]?\d*\.\d+|\d+'
    return [float(x) for x in re.findall(pattern, text)]

def compare_files(sas_output_file, python_output_file, tolerance=1e-4):
    """
    Compare the numeric values in the SAS and Python output files.
    Returns a dictionary with comparison results.
    """
    with open(sas_output_file, 'r') as f:
        sas_content = f.read()
    
    with open(python_output_file, 'r') as f:
        python_content = f.read()
    
    sas_values = extract_numeric_values(sas_content)
    python_values = extract_numeric_values(python_content)
    
    length_match = len(sas_values) == len(python_values)
    
    if length_match:
        match_count = 0
        mismatch_details = []
        
        for i, (sas_val, py_val) in enumerate(zip(sas_values, python_values)):
            if abs(sas_val - py_val) <= tolerance * max(1, abs(sas_val)):
                match_count += 1
            else:
                mismatch_details.append(f"Value {i+1}: SAS={sas_val}, Python={py_val}, Diff={sas_val-py_val}")
        
        percent_match = (match_count / len(sas_values)) * 100
    else:
        percent_match = 0
        mismatch_details = [f"Length mismatch: SAS={len(sas_values)}, Python={len(python_values)}"]
    
    return {
        "length_match": length_match,
        "total_values": len(sas_values) if length_match else f"SAS: {len(sas_values)}, Python: {len(python_values)}",
        "matching_values": match_count if length_match else "N/A",
        "percent_match": percent_match if length_match else 0,
        "mismatch_details": mismatch_details[:10] + (["..."] if len(mismatch_details) > 10 else [])
    }

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sas_output = os.path.join(current_dir, "Exercise1c_OUTPUT.TXT")
    python_output = os.path.join(current_dir, "Exercise1c_Python_OUTPUT.TXT")
    
    results = compare_files(sas_output, python_output)
    
    print("\nOutput Comparison Results:")
    print("==========================")
    print(f"Length match: {results['length_match']}")
    print(f"Total values compared: {results['total_values']}")
    
    if results['length_match']:
        print(f"Matching values: {results['matching_values']}")
        print(f"Match percentage: {results['percent_match']:.2f}%")
    
    if results['mismatch_details']:
        print("\nMismatch details (up to 10):")
        for detail in results['mismatch_details']:
            print(f"  {detail}")
    
    if results['length_match'] and results['percent_match'] > 99:
        print("\nOVERALL RESULT: PASS - Outputs match within tolerance")
    else:
        print("\nOVERALL RESULT: FAIL - Outputs do not match")

if __name__ == "__main__":
    main()
