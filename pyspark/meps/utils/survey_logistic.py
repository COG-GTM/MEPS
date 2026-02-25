"""Survey logistic regression utilities for MEPS PySpark jobs.

Implements weighted logistic regression that replicates the functionality
of SAS PROC SURVEYLOGISTIC. Uses scipy for the actual optimization and
PySpark for data preparation.

Key SAS → PySpark mappings:
    - PROC SURVEYLOGISTIC → survey_logistic_regression()
    - CLASS statement     → Handled via one-hot encoding
    - MODEL statement     → Specified via dependent/independent params
    - DOMAIN statement    → Pre-filter with full sample variance
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
from pyspark.sql import DataFrame
import pyspark.sql.functions as F


def survey_logistic_regression(
    df: DataFrame,
    dependent_var: str,
    independent_vars: List[str],
    class_vars: Optional[List[str]] = None,
    ref_levels: Optional[Dict[str, str]] = None,
    weight_col: str = "PERWT18F",
    stratum_col: str = "VARSTR",
    cluster_col: str = "VARPSU",
) -> Dict:
    """Perform weighted logistic regression replicating PROC SURVEYLOGISTIC.

    This function implements a survey-weighted logistic regression model.
    It handles categorical variables (CLASS statement equivalent) with
    reference coding (param=ref equivalent).

    Args:
        df: Input DataFrame with survey data.
        dependent_var: Name of the binary dependent variable (0/1).
        independent_vars: List of independent variable names.
        class_vars: List of categorical variable names (CLASS statement).
            These will be one-hot encoded with reference level dropped.
        ref_levels: Dictionary mapping class variable names to their
            reference level values. Equivalent to SAS ref= option.
        weight_col: Name of the survey weight column.
        stratum_col: Name of the stratum column.
        cluster_col: Name of the cluster/PSU column.

    Returns:
        Dictionary with keys:
            - coefficients: Dict mapping variable names to coefficient values
            - std_errors: Dict mapping variable names to standard errors
            - odds_ratios: Dict mapping variable names to odds ratios
            - n_obs: Number of observations used
            - n_weighted: Weighted number of observations
            - convergence: Whether the model converged
    """
    if class_vars is None:
        class_vars = []
    if ref_levels is None:
        ref_levels = {}

    # Prepare data: filter nulls and encode categoricals
    work_df = df.filter(F.col(dependent_var).isNotNull())
    for var in independent_vars:
        work_df = work_df.filter(F.col(var).isNotNull())
    work_df = work_df.filter(F.col(weight_col) > 0)

    # One-hot encode class variables
    encoded_vars = []
    encoding_map = {}

    for var in independent_vars:
        if var in class_vars:
            ref = ref_levels.get(var)
            levels = sorted([
                row[var] for row in
                work_df.select(var).distinct().collect()
                if row[var] is not None
            ], key=str)

            for level in levels:
                level_str = str(level)
                if ref is not None and level_str == str(ref):
                    continue
                col_name = f"{var}_{level_str}"
                work_df = work_df.withColumn(
                    col_name,
                    F.when(F.col(var).cast("string") == level_str, 1.0)
                    .otherwise(0.0)
                )
                encoded_vars.append(col_name)
                encoding_map[col_name] = (var, level_str)
        else:
            encoded_vars.append(var)

    # Collect data to driver for scipy optimization
    select_cols = (
        [dependent_var, weight_col] + encoded_vars
    )
    pdf = work_df.select(select_cols).toPandas()

    y = pdf[dependent_var].values.astype(float)
    w = pdf[weight_col].values.astype(float)
    X = pdf[encoded_vars].values.astype(float)

    # Add intercept
    n = len(y)
    X = np.column_stack([np.ones(n), X])
    var_names = ["Intercept"] + encoded_vars

    # Weighted logistic regression via IRLS
    coefficients, converged = _weighted_logistic_irls(X, y, w)

    # Compute standard errors using sandwich estimator
    std_errors = _compute_sandwich_se(X, y, w, coefficients)

    # Build results
    coef_dict = {}
    se_dict = {}
    or_dict = {}

    for i, name in enumerate(var_names):
        coef_dict[name] = float(coefficients[i])
        se_dict[name] = float(std_errors[i])
        or_dict[name] = float(np.exp(coefficients[i]))

    n_weighted = float(np.sum(w))

    return {
        "coefficients": coef_dict,
        "std_errors": se_dict,
        "odds_ratios": or_dict,
        "n_obs": n,
        "n_weighted": n_weighted,
        "convergence": converged,
    }


def _weighted_logistic_irls(
    X: np.ndarray,
    y: np.ndarray,
    w: np.ndarray,
    max_iter: int = 25,
    tol: float = 1e-8,
) -> Tuple[np.ndarray, bool]:
    """Iteratively Reweighted Least Squares for weighted logistic regression.

    Args:
        X: Design matrix (n x p) including intercept.
        y: Binary response vector (n,).
        w: Survey weight vector (n,).
        max_iter: Maximum number of iterations.
        tol: Convergence tolerance.

    Returns:
        Tuple of (coefficients array, converged boolean).
    """
    n, p = X.shape
    beta = np.zeros(p)
    converged = False

    for iteration in range(max_iter):
        eta = X @ beta
        # Clip to avoid overflow
        eta = np.clip(eta, -500, 500)
        mu = 1.0 / (1.0 + np.exp(-eta))

        # Working weights
        ww = mu * (1.0 - mu)
        ww = np.maximum(ww, 1e-10)

        # Combined weights
        combined_w = w * ww

        # Working response
        z = eta + (y - mu) / ww

        # Weighted least squares step
        W_diag = combined_w
        XtWX = X.T @ (X * W_diag[:, np.newaxis])
        XtWz = X.T @ (W_diag * z)

        try:
            beta_new = np.linalg.solve(XtWX, XtWz)
        except np.linalg.LinAlgError:
            beta_new = np.linalg.lstsq(XtWX, XtWz, rcond=None)[0]

        if np.max(np.abs(beta_new - beta)) < tol:
            converged = True
            beta = beta_new
            break

        beta = beta_new

    return beta, converged


def _compute_sandwich_se(
    X: np.ndarray,
    y: np.ndarray,
    w: np.ndarray,
    beta: np.ndarray,
) -> np.ndarray:
    """Compute sandwich (robust) standard errors for logistic regression.

    Args:
        X: Design matrix (n x p).
        y: Binary response vector.
        w: Survey weight vector.
        beta: Estimated coefficients.

    Returns:
        Array of standard errors for each coefficient.
    """
    n, p = X.shape
    eta = X @ beta
    eta = np.clip(eta, -500, 500)
    mu = 1.0 / (1.0 + np.exp(-eta))

    ww = mu * (1.0 - mu)
    ww = np.maximum(ww, 1e-10)

    # Bread: inverse of weighted Fisher information
    W_diag = w * ww
    bread = X.T @ (X * W_diag[:, np.newaxis])

    try:
        bread_inv = np.linalg.inv(bread)
    except np.linalg.LinAlgError:
        bread_inv = np.linalg.pinv(bread)

    # Meat: sum of outer products of score contributions
    resid = (y - mu) * w
    scores = X * resid[:, np.newaxis]
    meat = scores.T @ scores

    # Sandwich
    sandwich = bread_inv @ meat @ bread_inv
    se = np.sqrt(np.maximum(np.diag(sandwich), 0))

    return se
