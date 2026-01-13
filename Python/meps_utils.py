"""
MEPS Utility Module for Python

This module provides utilities for loading and analyzing MEPS (Medical Expenditure 
Panel Survey) data in Python, with proper handling of complex survey design.

Key features:
- Data loading from SAS7BDAT and SSP (SAS transport) files
- Survey design specification with strata, clusters, and weights
- Survey statistics (means, totals, frequencies) with proper variance estimation
- Domain/subpopulation analysis

Dependencies:
    pip install pandas numpy scipy pyreadstat statsmodels
"""

from pathlib import Path
from typing import Optional, Union, List, Dict, Any, Tuple
import warnings

import numpy as np
import pandas as pd


def load_sas_data(
    filepath: Union[str, Path],
    columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Load MEPS data from SAS7BDAT or SSP (SAS transport) files.
    
    Parameters
    ----------
    filepath : str or Path
        Path to the SAS data file (.sas7bdat or .ssp)
    columns : list of str, optional
        List of columns to load. If None, loads all columns.
        
    Returns
    -------
    pd.DataFrame
        Loaded data as a pandas DataFrame
        
    Examples
    --------
    >>> fyc = load_sas_data("C:/MEPS/h224.sas7bdat")
    >>> rx = load_sas_data("C:/MEPS/h188a.ssp", columns=['DUPERSID', 'RXDRGNAM', 'RXXP16X'])
    """
    filepath = Path(filepath)
    
    if filepath.suffix.lower() == '.sas7bdat':
        try:
            import pyreadstat
            df, meta = pyreadstat.read_sas7bdat(str(filepath), usecols=columns)
            return df
        except ImportError:
            try:
                from sas7bdat import SAS7BDAT
                with SAS7BDAT(str(filepath)) as f:
                    df = f.to_data_frame()
                if columns:
                    df = df[columns]
                return df
            except ImportError:
                raise ImportError(
                    "Please install pyreadstat or sas7bdat to read SAS7BDAT files: "
                    "pip install pyreadstat"
                )
    elif filepath.suffix.lower() == '.ssp':
        try:
            import pyreadstat
            df, meta = pyreadstat.read_xport(str(filepath), usecols=columns)
            return df
        except ImportError:
            try:
                import pandas as pd
                df = pd.read_sas(str(filepath), format='xport')
                if columns:
                    df = df[columns]
                return df
            except Exception as e:
                raise ImportError(
                    f"Could not read SSP file. Please install pyreadstat: "
                    f"pip install pyreadstat. Error: {e}"
                )
    else:
        raise ValueError(f"Unsupported file format: {filepath.suffix}")


def download_meps_file(
    filename: str,
    data_dir: Union[str, Path] = ".",
    file_format: str = "sas7bdat"
) -> Path:
    """
    Download a MEPS public use file from the MEPS website.
    
    Parameters
    ----------
    filename : str
        MEPS file name (e.g., 'h224' for 2020 FYC file)
    data_dir : str or Path
        Directory to save the downloaded file
    file_format : str
        File format to download: 'sas7bdat', 'dta', 'xlsx', or 'ssp'
        
    Returns
    -------
    Path
        Path to the downloaded file
    """
    import urllib.request
    import zipfile
    import tempfile
    
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    format_map = {
        'sas7bdat': 'sas',
        'dta': 'dta',
        'xlsx': 'xlsx',
        'ssp': 'ssp'
    }
    
    url_format = format_map.get(file_format, file_format)
    url = f"https://meps.ahrq.gov/mepsweb/data_files/pufs/{filename}/{filename}{url_format}.zip"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
        urllib.request.urlretrieve(url, tmp.name)
        with zipfile.ZipFile(tmp.name, 'r') as zip_ref:
            zip_ref.extractall(data_dir)
    
    expected_file = data_dir / f"{filename}.{file_format}"
    if expected_file.exists():
        return expected_file
    
    for f in data_dir.glob(f"{filename}*"):
        if f.suffix.lower() == f".{file_format}":
            return f
    
    raise FileNotFoundError(f"Could not find downloaded file for {filename}")


class SurveyDesign:
    """
    Survey design specification for complex survey analysis.
    
    This class handles the survey design variables (strata, clusters, weights)
    needed for proper variance estimation in MEPS analyses.
    
    Parameters
    ----------
    data : pd.DataFrame
        Survey data
    strata : str
        Name of the stratum variable (e.g., 'VARSTR')
    cluster : str
        Name of the cluster/PSU variable (e.g., 'VARPSU')
    weight : str
        Name of the weight variable (e.g., 'PERWT20F')
    nest : bool, default True
        Whether clusters are nested within strata
        
    Examples
    --------
    >>> design = SurveyDesign(
    ...     data=fyc,
    ...     strata='VARSTR',
    ...     cluster='VARPSU',
    ...     weight='PERWT20F'
    ... )
    """
    
    def __init__(
        self,
        data: pd.DataFrame,
        strata: str,
        cluster: str,
        weight: str,
        nest: bool = True
    ):
        self.data = data.copy()
        self.strata = strata
        self.cluster = cluster
        self.weight = weight
        self.nest = nest
        
        required_cols = [strata, cluster, weight]
        missing = [c for c in required_cols if c not in data.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        self._validate_design()
    
    def _validate_design(self):
        """Validate survey design variables."""
        if self.data[self.weight].isna().any():
            warnings.warn("Weight variable contains missing values")
        
        if (self.data[self.weight] < 0).any():
            warnings.warn("Weight variable contains negative values")
    
    def subset(self, condition: pd.Series) -> 'SurveyDesign':
        """
        Create a subset of the survey design.
        
        Note: For proper variance estimation with subpopulations, use the
        domain parameter in survey functions instead of subsetting.
        
        Parameters
        ----------
        condition : pd.Series
            Boolean series indicating which rows to keep
            
        Returns
        -------
        SurveyDesign
            New survey design with subset of data
        """
        return SurveyDesign(
            data=self.data[condition].copy(),
            strata=self.strata,
            cluster=self.cluster,
            weight=self.weight,
            nest=self.nest
        )


def survey_mean(
    design: SurveyDesign,
    variables: Union[str, List[str]],
    domain: Optional[str] = None,
    domain_value: Optional[Any] = None
) -> pd.DataFrame:
    """
    Calculate survey-weighted means with standard errors.
    
    Uses Taylor series linearization for variance estimation, accounting
    for the complex survey design (stratification and clustering).
    
    Parameters
    ----------
    design : SurveyDesign
        Survey design object
    variables : str or list of str
        Variable(s) to calculate means for
    domain : str, optional
        Domain/subpopulation variable for domain analysis
    domain_value : any, optional
        Value of domain variable to analyze (if domain is specified)
        
    Returns
    -------
    pd.DataFrame
        DataFrame with columns: variable, mean, se, ci_lower, ci_upper
        
    Examples
    --------
    >>> results = survey_mean(design, 'TOTEXP20')
    >>> results = survey_mean(design, ['TOTEXP20', 'OBTOTV20'], domain='SEX', domain_value=1)
    """
    if isinstance(variables, str):
        variables = [variables]
    
    data = design.data.copy()
    
    if domain is not None and domain_value is not None:
        domain_mask = data[domain] == domain_value
    else:
        domain_mask = pd.Series(True, index=data.index)
    
    results = []
    
    for var in variables:
        mean_val, se_val = _calculate_survey_mean(
            data=data,
            variable=var,
            strata=design.strata,
            cluster=design.cluster,
            weight=design.weight,
            domain_mask=domain_mask
        )
        
        ci_lower = mean_val - 1.96 * se_val
        ci_upper = mean_val + 1.96 * se_val
        
        results.append({
            'variable': var,
            'mean': mean_val,
            'se': se_val,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper
        })
    
    return pd.DataFrame(results)


def survey_total(
    design: SurveyDesign,
    variables: Union[str, List[str]],
    domain: Optional[str] = None,
    domain_value: Optional[Any] = None
) -> pd.DataFrame:
    """
    Calculate survey-weighted totals with standard errors.
    
    Uses Taylor series linearization for variance estimation, accounting
    for the complex survey design (stratification and clustering).
    
    Parameters
    ----------
    design : SurveyDesign
        Survey design object
    variables : str or list of str
        Variable(s) to calculate totals for
    domain : str, optional
        Domain/subpopulation variable for domain analysis
    domain_value : any, optional
        Value of domain variable to analyze (if domain is specified)
        
    Returns
    -------
    pd.DataFrame
        DataFrame with columns: variable, total, se, ci_lower, ci_upper
        
    Examples
    --------
    >>> results = survey_total(design, 'TOTEXP20')
    >>> results = survey_total(design, 'person', domain='RXDRGNAM', domain_value='ATORVASTATIN CALCIUM')
    """
    if isinstance(variables, str):
        variables = [variables]
    
    data = design.data.copy()
    
    if domain is not None and domain_value is not None:
        domain_mask = data[domain] == domain_value
    else:
        domain_mask = pd.Series(True, index=data.index)
    
    results = []
    
    for var in variables:
        total_val, se_val = _calculate_survey_total(
            data=data,
            variable=var,
            strata=design.strata,
            cluster=design.cluster,
            weight=design.weight,
            domain_mask=domain_mask
        )
        
        ci_lower = total_val - 1.96 * se_val
        ci_upper = total_val + 1.96 * se_val
        
        results.append({
            'variable': var,
            'total': total_val,
            'se': se_val,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper
        })
    
    return pd.DataFrame(results)


def survey_by(
    design: SurveyDesign,
    variables: Union[str, List[str]],
    by: str,
    func: str = 'total'
) -> pd.DataFrame:
    """
    Calculate survey statistics by group.
    
    Parameters
    ----------
    design : SurveyDesign
        Survey design object
    variables : str or list of str
        Variable(s) to calculate statistics for
    by : str
        Grouping variable
    func : str
        Function to apply: 'total' or 'mean'
        
    Returns
    -------
    pd.DataFrame
        DataFrame with statistics for each group
        
    Examples
    --------
    >>> results = survey_by(design, ['persons', 'n_purchases', 'pers_RXXP'], by='RXDRGNAM', func='total')
    """
    if isinstance(variables, str):
        variables = [variables]
    
    data = design.data
    groups = data[by].unique()
    
    all_results = []
    
    for group_val in groups:
        if pd.isna(group_val):
            continue
            
        if func == 'total':
            result = survey_total(design, variables, domain=by, domain_value=group_val)
        else:
            result = survey_mean(design, variables, domain=by, domain_value=group_val)
        
        result[by] = group_val
        all_results.append(result)
    
    if not all_results:
        return pd.DataFrame()
    
    return pd.concat(all_results, ignore_index=True)


def survey_freq(
    design: SurveyDesign,
    variable: str,
    domain: Optional[str] = None,
    domain_value: Optional[Any] = None
) -> pd.DataFrame:
    """
    Calculate survey-weighted frequencies and proportions.
    
    Parameters
    ----------
    design : SurveyDesign
        Survey design object
    variable : str
        Categorical variable to tabulate
    domain : str, optional
        Domain/subpopulation variable
    domain_value : any, optional
        Value of domain variable to analyze
        
    Returns
    -------
    pd.DataFrame
        DataFrame with columns: value, count, proportion, se_count, se_proportion
    """
    data = design.data.copy()
    
    if domain is not None and domain_value is not None:
        domain_mask = data[domain] == domain_value
    else:
        domain_mask = pd.Series(True, index=data.index)
    
    categories = data.loc[domain_mask, variable].unique()
    results = []
    
    total_weight = data.loc[domain_mask, design.weight].sum()
    
    for cat in categories:
        if pd.isna(cat):
            continue
        
        cat_mask = domain_mask & (data[variable] == cat)
        data['_indicator'] = cat_mask.astype(int)
        
        count, se_count = _calculate_survey_total(
            data=data,
            variable='_indicator',
            strata=design.strata,
            cluster=design.cluster,
            weight=design.weight,
            domain_mask=domain_mask
        )
        
        proportion = count / total_weight if total_weight > 0 else 0
        se_proportion = se_count / total_weight if total_weight > 0 else 0
        
        results.append({
            'value': cat,
            'count': count,
            'proportion': proportion,
            'se_count': se_count,
            'se_proportion': se_proportion
        })
    
    if '_indicator' in data.columns:
        data.drop('_indicator', axis=1, inplace=True)
    
    return pd.DataFrame(results)


def _calculate_survey_mean(
    data: pd.DataFrame,
    variable: str,
    strata: str,
    cluster: str,
    weight: str,
    domain_mask: pd.Series
) -> Tuple[float, float]:
    """
    Calculate survey-weighted mean with Taylor series linearization SE.
    
    Uses the formula for stratified cluster sampling with domain analysis.
    """
    subset = data[domain_mask].copy()
    
    if len(subset) == 0:
        return np.nan, np.nan
    
    w = subset[weight].values
    y = subset[variable].values
    
    valid = ~(np.isnan(y) | np.isnan(w))
    w = w[valid]
    y = y[valid]
    
    if len(w) == 0:
        return np.nan, np.nan
    
    total_weight = w.sum()
    weighted_sum = (w * y).sum()
    mean_val = weighted_sum / total_weight if total_weight > 0 else 0
    
    subset_valid = subset[valid].copy()
    subset_valid['_y'] = y
    subset_valid['_w'] = w
    subset_valid['_wy'] = w * y
    subset_valid['_resid'] = w * (y - mean_val)
    
    strata_groups = subset_valid.groupby(strata)
    
    var_sum = 0.0
    
    for stratum_name, stratum_data in strata_groups:
        cluster_groups = stratum_data.groupby(cluster)
        n_clusters = len(cluster_groups)
        
        if n_clusters <= 1:
            continue
        
        cluster_totals = cluster_groups['_resid'].sum().values
        stratum_mean = cluster_totals.mean()
        
        cluster_var = ((cluster_totals - stratum_mean) ** 2).sum()
        
        fpc = n_clusters / (n_clusters - 1)
        var_sum += fpc * cluster_var
    
    se_val = np.sqrt(var_sum) / total_weight if total_weight > 0 else 0
    
    return mean_val, se_val


def _calculate_survey_total(
    data: pd.DataFrame,
    variable: str,
    strata: str,
    cluster: str,
    weight: str,
    domain_mask: pd.Series
) -> Tuple[float, float]:
    """
    Calculate survey-weighted total with Taylor series linearization SE.
    
    Uses the formula for stratified cluster sampling with domain analysis.
    """
    data = data.copy()
    
    data['_domain_var'] = 0.0
    data.loc[domain_mask, '_domain_var'] = data.loc[domain_mask, variable]
    
    w = data[weight].values
    y = data['_domain_var'].values
    
    valid = ~(np.isnan(y) | np.isnan(w))
    
    total_val = (w[valid] * y[valid]).sum()
    
    data_valid = data[valid].copy()
    data_valid['_w'] = w[valid]
    data_valid['_y'] = y[valid]
    data_valid['_wy'] = w[valid] * y[valid]
    
    strata_groups = data_valid.groupby(strata)
    
    var_sum = 0.0
    
    for stratum_name, stratum_data in strata_groups:
        cluster_groups = stratum_data.groupby(cluster)
        n_clusters = len(cluster_groups)
        
        if n_clusters <= 1:
            continue
        
        cluster_totals = cluster_groups['_wy'].sum().values
        stratum_mean = cluster_totals.mean()
        
        cluster_var = ((cluster_totals - stratum_mean) ** 2).sum()
        
        fpc = n_clusters / (n_clusters - 1)
        var_sum += fpc * cluster_var
    
    se_val = np.sqrt(var_sum)
    
    return total_val, se_val


def survey_glm(
    design: SurveyDesign,
    formula: str,
    family: str = 'gaussian'
) -> Dict[str, Any]:
    """
    Fit a survey-weighted generalized linear model.
    
    Parameters
    ----------
    design : SurveyDesign
        Survey design object
    formula : str
        Model formula (e.g., 'TOTEXP ~ AGE + SEX')
    family : str
        Distribution family: 'gaussian', 'binomial', 'poisson'
        
    Returns
    -------
    dict
        Dictionary with model results including coefficients, standard errors,
        p-values, and confidence intervals
        
    Examples
    --------
    >>> results = survey_glm(design, 'TOTEXP20 ~ AGE + SEX', family='gaussian')
    """
    try:
        import statsmodels.api as sm
        import statsmodels.formula.api as smf
    except ImportError:
        raise ImportError("Please install statsmodels: pip install statsmodels")
    
    data = design.data.copy()
    
    family_map = {
        'gaussian': sm.families.Gaussian(),
        'binomial': sm.families.Binomial(),
        'poisson': sm.families.Poisson()
    }
    
    if family not in family_map:
        raise ValueError(f"Unknown family: {family}. Use one of {list(family_map.keys())}")
    
    model = smf.glm(
        formula=formula,
        data=data,
        family=family_map[family],
        freq_weights=data[design.weight]
    )
    
    result = model.fit()
    
    return {
        'params': result.params,
        'bse': result.bse,
        'pvalues': result.pvalues,
        'conf_int': result.conf_int(),
        'summary': result.summary()
    }


def create_age_groups(
    data: pd.DataFrame,
    age_var: str,
    bins: List[int] = [0, 18, 45, 65, 100],
    labels: Optional[List[str]] = None
) -> pd.Series:
    """
    Create age group categories from continuous age variable.
    
    Parameters
    ----------
    data : pd.DataFrame
        Data containing age variable
    age_var : str
        Name of age variable
    bins : list of int
        Age bin boundaries
    labels : list of str, optional
        Labels for age groups
        
    Returns
    -------
    pd.Series
        Categorical age group variable
    """
    if labels is None:
        labels = [f"{bins[i]}-{bins[i+1]-1}" for i in range(len(bins)-1)]
    
    return pd.cut(data[age_var], bins=bins, labels=labels, right=False)


def pool_data(
    datasets: List[pd.DataFrame],
    years: List[int],
    weight_var_pattern: str = 'PERWT{year}F',
    pooled_weight_name: str = 'POOLWT'
) -> pd.DataFrame:
    """
    Pool multiple years of MEPS data with adjusted weights.
    
    Parameters
    ----------
    datasets : list of pd.DataFrame
        List of annual datasets to pool
    years : list of int
        Corresponding years for each dataset
    weight_var_pattern : str
        Pattern for weight variable names (use {year} as placeholder)
    pooled_weight_name : str
        Name for the pooled weight variable
        
    Returns
    -------
    pd.DataFrame
        Pooled dataset with adjusted weights
        
    Examples
    --------
    >>> pooled = pool_data([fyc2017, fyc2018], [2017, 2018])
    """
    n_years = len(years)
    pooled_dfs = []
    
    for df, year in zip(datasets, years):
        df = df.copy()
        
        weight_var = weight_var_pattern.format(year=str(year)[-2:])
        if weight_var not in df.columns:
            weight_var = weight_var_pattern.format(year=year)
        
        if weight_var in df.columns:
            df[pooled_weight_name] = df[weight_var] / n_years
        else:
            warnings.warn(f"Weight variable {weight_var} not found for year {year}")
        
        df['YEAR'] = year
        pooled_dfs.append(df)
    
    return pd.concat(pooled_dfs, ignore_index=True)


if __name__ == "__main__":
    print("MEPS Python Utilities")
    print("=====================")
    print("This module provides utilities for analyzing MEPS survey data in Python.")
    print("\nKey functions:")
    print("  - load_sas_data(): Load SAS7BDAT or SSP files")
    print("  - SurveyDesign(): Define survey design with strata, clusters, weights")
    print("  - survey_mean(): Calculate survey-weighted means")
    print("  - survey_total(): Calculate survey-weighted totals")
    print("  - survey_freq(): Calculate survey-weighted frequencies")
    print("  - survey_by(): Calculate statistics by group")
    print("  - survey_glm(): Fit survey-weighted regression models")
    print("\nExample usage:")
    print("  >>> from meps_utils import load_sas_data, SurveyDesign, survey_total")
    print("  >>> fyc = load_sas_data('h224.sas7bdat')")
    print("  >>> design = SurveyDesign(fyc, strata='VARSTR', cluster='VARPSU', weight='PERWT20F')")
    print("  >>> results = survey_total(design, 'TOTEXP20')")
