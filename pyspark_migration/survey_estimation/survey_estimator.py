"""Survey estimation layer for MEPS PySpark migration.

PySpark has no native survey estimation equivalent to SAS PROC SURVEYMEANS,
R survey::svydesign, or Stata svy. This module wraps the Python `samplics`
library to produce survey-weighted estimates (means, totals, proportions,
and standard errors) from Parquet outputs of the PySpark ETL layer.

Survey design variables used across all MEPS analyses:
  - VARSTR  : Stratum variable
  - VARPSU  : Primary Sampling Unit (cluster) variable
  - PERWT**F: Person-level weight (year-specific, e.g. PERWT16F, PERWT20F)
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from samplics.estimation import TaylorEstimator
from samplics.utils.types import PopParam


def create_survey_design(
    df: pd.DataFrame,
    strata_col: str = "VARSTR",
    cluster_col: str = "VARPSU",
    weight_col: str = "PERWT16F",
) -> Dict[str, np.ndarray]:
    """Extract survey design arrays from a pandas DataFrame.

    Args:
        df: Input DataFrame with survey design columns.
        strata_col: Name of the stratum column.
        cluster_col: Name of the PSU/cluster column.
        weight_col: Name of the survey weight column (year-specific).

    Returns:
        Dictionary with 'strata', 'cluster', and 'weight' arrays.
    """
    return {
        "strata": df[strata_col].values,
        "cluster": df[cluster_col].values,
        "weight": df[weight_col].values,
    }


def survey_mean(
    df: pd.DataFrame,
    var_cols: List[str],
    weight_col: str,
    strata_col: str = "VARSTR",
    cluster_col: str = "VARPSU",
    domain_col: Optional[str] = None,
) -> pd.DataFrame:
    """Compute survey-weighted means with standard errors.

    Equivalent to SAS PROC SURVEYMEANS ... MEAN STDERR.

    Args:
        df: Input DataFrame.
        var_cols: Variable columns to estimate means for.
        weight_col: Survey weight column.
        strata_col: Stratum column.
        cluster_col: PSU/cluster column.
        domain_col: Optional domain/subpopulation column.

    Returns:
        DataFrame with columns: variable, mean, se, n.
    """
    results = []
    for var_name in var_cols:
        estimator = TaylorEstimator(PopParam.mean)
        y = df[var_name].values.astype(float)
        w = df[weight_col].values.astype(float)
        strata = df[strata_col].values
        psu = df[cluster_col].values

        if domain_col is not None:
            domain = df[domain_col].values
            estimator.estimate(y=y, samp_weight=w, stratum=strata, psu=psu, domain=domain)
            for dom_key in estimator.point_est:
                results.append({
                    "variable": var_name,
                    "domain": dom_key,
                    "mean": float(estimator.point_est[dom_key]),
                    "se": float(estimator.stderror[dom_key]),
                    "n": int(np.sum(domain == dom_key)),
                })
        else:
            estimator.estimate(y=y, samp_weight=w, stratum=strata, psu=psu)
            results.append({
                "variable": var_name,
                "domain": "_overall_",
                "mean": float(estimator.point_est),
                "se": float(estimator.stderror),
                "n": len(y),
            })

    return pd.DataFrame(results)


def survey_total(
    df: pd.DataFrame,
    var_cols: List[str],
    weight_col: str,
    strata_col: str = "VARSTR",
    cluster_col: str = "VARPSU",
    domain_col: Optional[str] = None,
) -> pd.DataFrame:
    """Compute survey-weighted totals with standard errors.

    Equivalent to SAS PROC SURVEYMEANS ... SUM.

    Args:
        df: Input DataFrame.
        var_cols: Variable columns to estimate totals for.
        weight_col: Survey weight column.
        strata_col: Stratum column.
        cluster_col: PSU/cluster column.
        domain_col: Optional domain/subpopulation column.

    Returns:
        DataFrame with columns: variable, total, se, n.
    """
    results = []
    for var_name in var_cols:
        estimator = TaylorEstimator(PopParam.total)
        y = df[var_name].values.astype(float)
        w = df[weight_col].values.astype(float)
        strata = df[strata_col].values
        psu = df[cluster_col].values

        if domain_col is not None:
            domain = df[domain_col].values
            estimator.estimate(y=y, samp_weight=w, stratum=strata, psu=psu, domain=domain)
            for dom_key in estimator.point_est:
                results.append({
                    "variable": var_name,
                    "domain": dom_key,
                    "total": float(estimator.point_est[dom_key]),
                    "se": float(estimator.stderror[dom_key]),
                    "n": int(np.sum(domain == dom_key)),
                })
        else:
            estimator.estimate(y=y, samp_weight=w, stratum=strata, psu=psu)
            results.append({
                "variable": var_name,
                "domain": "_overall_",
                "total": float(estimator.point_est),
                "se": float(estimator.stderror),
                "n": len(y),
            })

    return pd.DataFrame(results)


def survey_proportion(
    df: pd.DataFrame,
    var_cols: List[str],
    weight_col: str,
    strata_col: str = "VARSTR",
    cluster_col: str = "VARPSU",
    domain_col: Optional[str] = None,
) -> pd.DataFrame:
    """Compute survey-weighted proportions with standard errors.

    Equivalent to SAS PROC SURVEYFREQ or PROC SURVEYMEANS on binary variables.

    Args:
        df: Input DataFrame.
        var_cols: Binary (0/1) variable columns.
        weight_col: Survey weight column.
        strata_col: Stratum column.
        cluster_col: PSU/cluster column.
        domain_col: Optional domain/subpopulation column.

    Returns:
        DataFrame with columns: variable, proportion, se, weighted_count, n.
    """
    results = []
    for var_name in var_cols:
        estimator = TaylorEstimator(PopParam.mean)
        y = df[var_name].values.astype(float)
        w = df[weight_col].values.astype(float)
        strata = df[strata_col].values
        psu = df[cluster_col].values

        if domain_col is not None:
            domain = df[domain_col].values
            estimator.estimate(y=y, samp_weight=w, stratum=strata, psu=psu, domain=domain)
            for dom_key in estimator.point_est:
                mask = domain == dom_key
                weighted_count = float(np.sum(y[mask] * w[mask]))
                results.append({
                    "variable": var_name,
                    "domain": dom_key,
                    "proportion": float(estimator.point_est[dom_key]),
                    "se": float(estimator.stderror[dom_key]),
                    "weighted_count": weighted_count,
                    "n": int(np.sum(mask)),
                })
        else:
            estimator.estimate(y=y, samp_weight=w, stratum=strata, psu=psu)
            weighted_count = float(np.sum(y * w))
            results.append({
                "variable": var_name,
                "domain": "_overall_",
                "proportion": float(estimator.point_est),
                "se": float(estimator.stderror),
                "weighted_count": weighted_count,
                "n": len(y),
            })

    return pd.DataFrame(results)


def survey_ratio(
    df: pd.DataFrame,
    numerator_cols: List[str],
    denominator_col: str,
    weight_col: str,
    strata_col: str = "VARSTR",
    cluster_col: str = "VARPSU",
) -> pd.DataFrame:
    """Compute survey-weighted ratios with standard errors.

    Equivalent to SAS PROC SURVEYMEANS ... RATIO.

    Args:
        df: Input DataFrame.
        numerator_cols: Numerator variable columns.
        denominator_col: Denominator variable column.
        weight_col: Survey weight column.
        strata_col: Stratum column.
        cluster_col: PSU/cluster column.

    Returns:
        DataFrame with columns: numerator, denominator, ratio, se.
    """
    results = []
    for num_col in numerator_cols:
        estimator = TaylorEstimator(PopParam.ratio)
        y = df[num_col].values.astype(float)
        x = df[denominator_col].values.astype(float)
        w = df[weight_col].values.astype(float)
        strata = df[strata_col].values
        psu = df[cluster_col].values

        estimator.estimate(y=y, samp_weight=w, stratum=strata, psu=psu, x=x)
        results.append({
            "numerator": num_col,
            "denominator": denominator_col,
            "ratio": float(estimator.point_est),
            "se": float(estimator.stderror),
        })

    return pd.DataFrame(results)
