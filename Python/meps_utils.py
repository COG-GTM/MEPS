"""
MEPS Python Utility Module

This module provides utility functions for loading and analyzing MEPS
(Medical Expenditure Panel Survey) data in Python, equivalent to SAS
SURVEY procedures.

Key features:
- Data loading from SAS7BDAT and SSP files
- Survey-weighted statistics (means, totals, frequencies)
- Complex survey design handling (strata, clusters, weights)
- Domain analysis for subpopulation estimates
"""

import numpy as np
import pandas as pd
from typing import Optional, Union, List, Dict, Any, Tuple
import warnings


def load_sas_data(filepath: str) -> pd.DataFrame:
    """
    Load MEPS data from SAS7BDAT or SSP file.
    
    For 2017+ files: Uses pyreadstat to read SAS7BDAT files
    For 1996-2016 files: Uses pyreadstat to read SAS transport (SSP) files
    
    Parameters
    ----------
    filepath : str
        Path to the SAS data file (.sas7bdat or .ssp)
        
    Returns
    -------
    pd.DataFrame
        DataFrame containing the MEPS data
    """
    try:
        import pyreadstat
    except ImportError:
        raise ImportError(
            "pyreadstat is required for loading SAS files. "
            "Install with: pip install pyreadstat"
        )
    
    filepath_lower = filepath.lower()
    
    if filepath_lower.endswith('.sas7bdat'):
        df, meta = pyreadstat.read_sas7bdat(filepath)
    elif filepath_lower.endswith('.ssp') or filepath_lower.endswith('.xpt'):
        df, meta = pyreadstat.read_xport(filepath)
    else:
        try:
            df, meta = pyreadstat.read_sas7bdat(filepath)
        except Exception:
            df, meta = pyreadstat.read_xport(filepath)
    
    return df


class SurveyDesign:
    """
    Survey design specification for complex survey analysis.
    
    Equivalent to SAS PROC SURVEY procedures with STRATUM, CLUSTER, and WEIGHT statements.
    
    Parameters
    ----------
    data : pd.DataFrame
        Survey data
    strata : str, optional
        Name of stratification variable (VARSTR in MEPS)
    cluster : str, optional
        Name of cluster/PSU variable (VARPSU in MEPS)
    weight : str, optional
        Name of weight variable (PERWT##F in MEPS)
    nest : bool, default True
        Whether clusters are nested within strata
    """
    
    def __init__(
        self,
        data: pd.DataFrame,
        strata: Optional[str] = None,
        cluster: Optional[str] = None,
        weight: Optional[str] = None,
        nest: bool = True
    ):
        self.data = data.copy()
        self.strata = strata
        self.cluster = cluster
        self.weight = weight
        self.nest = nest
        
        if weight and weight in self.data.columns:
            self.data['_weight_'] = self.data[weight]
        else:
            self.data['_weight_'] = 1.0
            
    def _get_weights(self, subset: Optional[pd.Series] = None) -> np.ndarray:
        """Get weights, optionally for a subset."""
        if subset is not None:
            return self.data.loc[subset, '_weight_'].values
        return self.data['_weight_'].values
    
    def _taylor_variance(
        self,
        data: pd.DataFrame,
        var: str,
        estimate_type: str = 'mean'
    ) -> Tuple[float, float]:
        """
        Calculate Taylor series linearization variance estimate.
        
        This implements the variance estimation method used by SAS SURVEY procedures
        for complex survey designs with stratification and clustering.
        """
        if self.strata is None and self.cluster is None:
            weights = data['_weight_'].values
            values = data[var].values
            
            weighted_sum = np.sum(weights * values)
            sum_weights = np.sum(weights)
            
            if estimate_type == 'mean':
                estimate = weighted_sum / sum_weights
                residuals = values - estimate
                variance = np.sum(weights**2 * residuals**2) / (sum_weights**2)
            else:
                estimate = weighted_sum
                n = len(values)
                if n > 1:
                    variance = n / (n - 1) * np.sum(weights**2 * values**2) - \
                               (n / (n - 1)) * estimate**2 / n
                else:
                    variance = 0
                    
            return estimate, np.sqrt(max(0, variance))
        
        strata_var = self.strata if self.strata else '_dummy_strata_'
        cluster_var = self.cluster if self.cluster else '_dummy_cluster_'
        
        if strata_var == '_dummy_strata_':
            data = data.copy()
            data['_dummy_strata_'] = 1
        if cluster_var == '_dummy_cluster_':
            data = data.copy()
            data['_dummy_cluster_'] = range(len(data))
        
        weights = data['_weight_'].values
        values = data[var].values
        
        weighted_sum = np.sum(weights * values)
        sum_weights = np.sum(weights)
        
        if estimate_type == 'mean':
            estimate = weighted_sum / sum_weights
        else:
            estimate = weighted_sum
        
        strata_groups = data.groupby(strata_var)
        n_strata = strata_groups.ngroups
        
        total_variance = 0.0
        
        for stratum_name, stratum_data in strata_groups:
            cluster_groups = stratum_data.groupby(cluster_var)
            n_clusters = cluster_groups.ngroups
            
            if n_clusters <= 1:
                continue
            
            cluster_totals = []
            cluster_weight_totals = []
            
            for cluster_name, cluster_data in cluster_groups:
                w = cluster_data['_weight_'].values
                v = cluster_data[var].values
                cluster_totals.append(np.sum(w * v))
                cluster_weight_totals.append(np.sum(w))
            
            cluster_totals = np.array(cluster_totals)
            cluster_weight_totals = np.array(cluster_weight_totals)
            
            if estimate_type == 'mean':
                stratum_weighted_sum = np.sum(cluster_totals)
                stratum_weight_sum = np.sum(cluster_weight_totals)
                stratum_mean = stratum_weighted_sum / stratum_weight_sum if stratum_weight_sum > 0 else 0
                
                z_h = cluster_totals - stratum_mean * cluster_weight_totals
                z_bar = np.mean(z_h)
                
                stratum_variance = (n_clusters / (n_clusters - 1)) * np.sum((z_h - z_bar)**2)
                stratum_variance = stratum_variance / (sum_weights**2)
            else:
                z_h = cluster_totals
                z_bar = np.mean(z_h)
                stratum_variance = (n_clusters / (n_clusters - 1)) * np.sum((z_h - z_bar)**2)
            
            total_variance += stratum_variance
        
        return estimate, np.sqrt(max(0, total_variance))


def survey_mean(
    design: SurveyDesign,
    var: Union[str, List[str]],
    domain: Optional[str] = None,
    domain_value: Optional[Any] = None
) -> pd.DataFrame:
    """
    Calculate survey-weighted means with standard errors.
    
    Equivalent to SAS PROC SURVEYMEANS with MEAN option.
    
    Parameters
    ----------
    design : SurveyDesign
        Survey design object
    var : str or list of str
        Variable(s) to analyze
    domain : str, optional
        Domain variable for subpopulation analysis
    domain_value : any, optional
        Specific domain value to analyze
        
    Returns
    -------
    pd.DataFrame
        DataFrame with mean, stderr, and other statistics
    """
    if isinstance(var, str):
        var = [var]
    
    results = []
    
    data = design.data.copy()
    
    if domain is not None:
        if domain_value is not None:
            subset = data[domain] == domain_value
            data_subset = data[subset].copy()
        else:
            domain_values = data[domain].dropna().unique()
            for dv in domain_values:
                subset = data[domain] == dv
                data_subset = data[subset].copy()
                
                for v in var:
                    if v not in data_subset.columns:
                        continue
                    valid = data_subset[v].notna()
                    valid_data = data_subset[valid]
                    
                    if len(valid_data) == 0:
                        continue
                    
                    mean_val, se_val = design._taylor_variance(valid_data, v, 'mean')
                    
                    results.append({
                        'Domain': domain,
                        'DomainValue': dv,
                        'Variable': v,
                        'N': len(valid_data),
                        'SumWgt': valid_data['_weight_'].sum(),
                        'Mean': mean_val,
                        'StdErr': se_val,
                        'LowerCL': mean_val - 1.96 * se_val,
                        'UpperCL': mean_val + 1.96 * se_val
                    })
            
            return pd.DataFrame(results)
    else:
        data_subset = data
    
    for v in var:
        if v not in data_subset.columns:
            continue
        valid = data_subset[v].notna()
        valid_data = data_subset[valid]
        
        if len(valid_data) == 0:
            continue
        
        mean_val, se_val = design._taylor_variance(valid_data, v, 'mean')
        
        result = {
            'Variable': v,
            'N': len(valid_data),
            'SumWgt': valid_data['_weight_'].sum(),
            'Mean': mean_val,
            'StdErr': se_val,
            'LowerCL': mean_val - 1.96 * se_val,
            'UpperCL': mean_val + 1.96 * se_val
        }
        
        if domain is not None:
            result['Domain'] = domain
            result['DomainValue'] = domain_value
            
        results.append(result)
    
    return pd.DataFrame(results)


def survey_total(
    design: SurveyDesign,
    var: Union[str, List[str]],
    domain: Optional[str] = None,
    domain_value: Optional[Any] = None
) -> pd.DataFrame:
    """
    Calculate survey-weighted totals with standard errors.
    
    Equivalent to SAS PROC SURVEYMEANS with SUM option.
    
    Parameters
    ----------
    design : SurveyDesign
        Survey design object
    var : str or list of str
        Variable(s) to analyze
    domain : str, optional
        Domain variable for subpopulation analysis
    domain_value : any, optional
        Specific domain value to analyze
        
    Returns
    -------
    pd.DataFrame
        DataFrame with sum, stderr, and other statistics
    """
    if isinstance(var, str):
        var = [var]
    
    results = []
    
    data = design.data.copy()
    
    if domain is not None:
        if domain_value is not None:
            subset = data[domain] == domain_value
            data_subset = data[subset].copy()
        else:
            domain_values = data[domain].dropna().unique()
            for dv in domain_values:
                subset = data[domain] == dv
                data_subset = data[subset].copy()
                
                for v in var:
                    if v not in data_subset.columns:
                        continue
                    valid = data_subset[v].notna()
                    valid_data = data_subset[valid]
                    
                    if len(valid_data) == 0:
                        continue
                    
                    total_val, se_val = design._taylor_variance(valid_data, v, 'total')
                    
                    results.append({
                        'Domain': domain,
                        'DomainValue': dv,
                        'Variable': v,
                        'N': len(valid_data),
                        'SumWgt': valid_data['_weight_'].sum(),
                        'Sum': total_val,
                        'StdDev': se_val,
                        'LowerCL': total_val - 1.96 * se_val,
                        'UpperCL': total_val + 1.96 * se_val
                    })
            
            return pd.DataFrame(results)
    else:
        data_subset = data
    
    for v in var:
        if v not in data_subset.columns:
            continue
        valid = data_subset[v].notna()
        valid_data = data_subset[valid]
        
        if len(valid_data) == 0:
            continue
        
        total_val, se_val = design._taylor_variance(valid_data, v, 'total')
        
        result = {
            'Variable': v,
            'N': len(valid_data),
            'SumWgt': valid_data['_weight_'].sum(),
            'Sum': total_val,
            'StdDev': se_val,
            'LowerCL': total_val - 1.96 * se_val,
            'UpperCL': total_val + 1.96 * se_val
        }
        
        if domain is not None:
            result['Domain'] = domain
            result['DomainValue'] = domain_value
            
        results.append(result)
    
    return pd.DataFrame(results)


def survey_freq(
    design: SurveyDesign,
    var: str,
    by: Optional[str] = None
) -> pd.DataFrame:
    """
    Calculate survey-weighted frequencies.
    
    Equivalent to SAS PROC SURVEYFREQ.
    
    Parameters
    ----------
    design : SurveyDesign
        Survey design object
    var : str
        Variable to tabulate
    by : str, optional
        Grouping variable for cross-tabulation
        
    Returns
    -------
    pd.DataFrame
        DataFrame with frequency counts and percentages
    """
    data = design.data.copy()
    
    if by is not None:
        results = []
        for by_val in data[by].dropna().unique():
            subset = data[by] == by_val
            subset_data = data[subset]
            
            for val in subset_data[var].dropna().unique():
                val_subset = subset_data[var] == val
                freq = val_subset.sum()
                weighted_freq = subset_data.loc[val_subset, '_weight_'].sum()
                total_weight = subset_data['_weight_'].sum()
                pct = 100 * weighted_freq / total_weight if total_weight > 0 else 0
                
                results.append({
                    by: by_val,
                    var: val,
                    'Frequency': freq,
                    'WeightedFreq': weighted_freq,
                    'Percent': pct
                })
        
        return pd.DataFrame(results)
    else:
        results = []
        total_weight = data['_weight_'].sum()
        
        for val in data[var].dropna().unique():
            val_subset = data[var] == val
            freq = val_subset.sum()
            weighted_freq = data.loc[val_subset, '_weight_'].sum()
            pct = 100 * weighted_freq / total_weight if total_weight > 0 else 0
            
            results.append({
                var: val,
                'Frequency': freq,
                'WeightedFreq': weighted_freq,
                'Percent': pct
            })
        
        return pd.DataFrame(results)


def survey_reg(
    design: SurveyDesign,
    formula: str,
    family: str = 'gaussian'
) -> Dict[str, Any]:
    """
    Fit survey-weighted regression model.
    
    Equivalent to SAS PROC SURVEYREG or PROC SURVEYLOGISTIC.
    
    Parameters
    ----------
    design : SurveyDesign
        Survey design object
    formula : str
        Model formula (e.g., 'y ~ x1 + x2')
    family : str, default 'gaussian'
        Distribution family ('gaussian' for linear, 'binomial' for logistic)
        
    Returns
    -------
    dict
        Dictionary containing model results
    """
    try:
        import statsmodels.api as sm
        import statsmodels.formula.api as smf
    except ImportError:
        raise ImportError(
            "statsmodels is required for regression analysis. "
            "Install with: pip install statsmodels"
        )
    
    data = design.data.copy()
    weights = data['_weight_'].values
    
    if family == 'gaussian':
        model = smf.wls(formula, data=data, weights=weights)
    elif family == 'binomial':
        model = smf.glm(formula, data=data, family=sm.families.Binomial(),
                        freq_weights=weights)
    else:
        raise ValueError(f"Unknown family: {family}")
    
    results = model.fit()
    
    return {
        'params': results.params,
        'bse': results.bse,
        'tvalues': results.tvalues,
        'pvalues': results.pvalues,
        'rsquared': getattr(results, 'rsquared', None),
        'summary': results.summary()
    }


def print_results(
    df: pd.DataFrame,
    title: str = "",
    format_dict: Optional[Dict[str, str]] = None
) -> None:
    """
    Print formatted results table.
    
    Parameters
    ----------
    df : pd.DataFrame
        Results DataFrame
    title : str, optional
        Title to print above table
    format_dict : dict, optional
        Dictionary mapping column names to format strings
    """
    if title:
        print(f"\n{title}")
        print("=" * len(title))
    
    if format_dict:
        df_formatted = df.copy()
        for col, fmt in format_dict.items():
            if col in df_formatted.columns:
                df_formatted[col] = df_formatted[col].apply(lambda x: fmt.format(x) if pd.notna(x) else '')
        print(df_formatted.to_string(index=False))
    else:
        print(df.to_string(index=False))
    print()


def create_age_category(age: pd.Series, breaks: List[int] = [0, 64]) -> pd.Series:
    """
    Create age categories from continuous age variable.
    
    Parameters
    ----------
    age : pd.Series
        Age variable
    breaks : list of int
        Age breakpoints
        
    Returns
    -------
    pd.Series
        Categorical age variable
    """
    conditions = []
    labels = []
    
    for i, brk in enumerate(breaks):
        if i == 0:
            conditions.append(age <= brk)
            labels.append(f'0-{brk}')
        else:
            conditions.append((age > breaks[i-1]) & (age <= brk))
            labels.append(f'{breaks[i-1]+1}-{brk}')
    
    conditions.append(age > breaks[-1])
    labels.append(f'{breaks[-1]+1}+')
    
    result = pd.Series(index=age.index, dtype='object')
    for cond, label in zip(conditions, labels):
        result[cond] = label
    
    return result


def get_age_from_multiple_vars(
    df: pd.DataFrame,
    age_vars: List[str]
) -> pd.Series:
    """
    Get age from multiple age variables, using first non-missing value.
    
    This is equivalent to the SAS pattern:
        IF AGE16X >= 0 THEN AGE = AGE16X;
        ELSE IF AGE42X >= 0 THEN AGE = AGE42X;
        ELSE IF AGE31X >= 0 THEN AGE = AGE31X;
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing age variables
    age_vars : list of str
        List of age variable names in priority order
        
    Returns
    -------
    pd.Series
        Combined age variable
    """
    age = pd.Series(index=df.index, dtype='float64')
    
    for var in age_vars:
        if var in df.columns:
            mask = age.isna() & (df[var] >= 0)
            age[mask] = df.loc[mask, var]
    
    return age
