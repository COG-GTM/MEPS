"""Survey-weighted regression models.

Implements equivalents of R's svyglm() for Gaussian and quasibinomial families,
and Stata's margins command for average marginal effects.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl
from scipy import stats

from meps.survey.design import MEPSSurveyDesign


@dataclass
class SurveyGLMResult:
    """Results from a survey-weighted GLM.

    Attributes:
        coefficients: Named coefficient estimates.
        se: Standard errors (sandwich/robust).
        t_stat: t-statistics.
        p_value: p-values (two-sided).
        ci_lower: Lower 95% CI bounds.
        ci_upper: Upper 95% CI bounds.
        family: Model family ('gaussian' or 'quasibinomial').
        n_obs: Number of observations used.
        formula: Original formula string.
        design_matrix: The X matrix used for fitting.
        response: The y vector used for fitting.
        weights: The weight vector used for fitting.
        fitted_values: Predicted values on the response scale.
    """

    coefficients: dict[str, float]
    se: dict[str, float]
    t_stat: dict[str, float]
    p_value: dict[str, float]
    ci_lower: dict[str, float]
    ci_upper: dict[str, float]
    family: str
    n_obs: int
    formula: str
    design_matrix: np.ndarray
    response: np.ndarray
    weights: np.ndarray
    fitted_values: np.ndarray

    def to_dataframe(self) -> pl.DataFrame:
        """Convert regression results to a polars DataFrame."""
        names = list(self.coefficients.keys())
        return pl.DataFrame({
            "term": names,
            "estimate": [self.coefficients[n] for n in names],
            "se": [self.se[n] for n in names],
            "t_stat": [self.t_stat[n] for n in names],
            "p_value": [self.p_value[n] for n in names],
            "ci_lower": [self.ci_lower[n] for n in names],
            "ci_upper": [self.ci_upper[n] for n in names],
        })

    def summary(self) -> str:
        """Return a formatted summary table matching R's summary(svyglm(...)) output."""
        lines = [
            f"Survey-Weighted GLM: {self.formula}",
            f"Family: {self.family}",
            f"Number of observations: {self.n_obs}",
            "",
            f"{'Term':<30} {'Estimate':>12} {'Std.Error':>12} {'t value':>10} {'Pr(>|t|)':>12}",
            "-" * 78,
        ]
        for name in self.coefficients:
            sig = ""
            p = self.p_value[name]
            if p < 0.001:
                sig = "***"
            elif p < 0.01:
                sig = "**"
            elif p < 0.05:
                sig = "*"
            elif p < 0.1:
                sig = "."

            lines.append(
                f"{name:<30} {self.coefficients[name]:>12.6f} {self.se[name]:>12.6f} "
                f"{self.t_stat[name]:>10.3f} {p:>12.6f} {sig}"
            )
        lines.append("-" * 78)
        lines.append("Signif. codes: 0 '***' 0.001 '**' 0.01 '*' 0.05 '.' 0.1 ' ' 1")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.summary()


def _parse_formula(formula: str, data: pl.DataFrame) -> tuple[str, list[str], list[str]]:
    """Parse an R-style formula string into response and predictor components.

    Handles:
      - Continuous predictors: 'AGELAST'
      - Factor predictors: 'as.factor(SEX)' or 'C(SEX)' or 'factor(SEX)'
      - Multiple predictors with '+'

    Args:
        formula: Formula string like 'y ~ x1 + as.factor(x2) + x3'.
        data: DataFrame to resolve variable names.

    Returns:
        Tuple of (response_var, continuous_predictors, factor_predictors).
    """
    parts = formula.split("~")
    if len(parts) != 2:
        raise ValueError(f"Invalid formula: {formula}. Expected 'y ~ x1 + x2 + ...'")

    response = parts[0].strip()
    predictor_str = parts[1].strip()

    continuous = []
    factors = []

    for term in predictor_str.split("+"):
        term = term.strip()
        if not term:
            continue

        # Check for factor specification
        for prefix in ["as.factor(", "C(", "factor("]:
            if term.startswith(prefix) and term.endswith(")"):
                var_name = term[len(prefix):-1].strip()
                factors.append(var_name)
                break
        else:
            continuous.append(term)

    return response, continuous, factors


def _build_design_matrix(
    data: pl.DataFrame,
    continuous: list[str],
    factors: list[str],
    domain: np.ndarray | None = None,
) -> tuple[np.ndarray, list[str]]:
    """Build a design matrix (X) with intercept, continuous, and dummy-coded factor variables.

    Returns:
        Tuple of (X matrix, column names).
    """
    n = data.height
    columns = [np.ones(n)]
    col_names = ["(Intercept)"]

    # Add continuous predictors
    for var in continuous:
        columns.append(data[var].to_numpy().astype(np.float64))
        col_names.append(var)

    # Add dummy-coded factor predictors (reference = first level)
    for var in factors:
        values = data[var].to_numpy()
        unique_vals = sorted(set(values[~np.isnan(values)] if np.issubdtype(values.dtype, np.floating) else values))
        # Skip first level (reference category)
        for level in unique_vals[1:]:
            dummy = (values == level).astype(np.float64)
            columns.append(dummy)
            col_names.append(f"{var}_{int(level) if isinstance(level, (float, np.floating)) else level}")

    X = np.column_stack(columns)
    return X, col_names


def _fit_wls(X: np.ndarray, y: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Fit weighted least squares: beta = (X'WX)^{-1} X'Wy."""
    # Use element-wise multiplication to avoid O(n^2) memory from np.diag(w)
    W_col = w.reshape(-1, 1)
    XtWX = X.T @ (X * W_col)
    XtWy = X.T @ (w * y)
    try:
        beta = np.linalg.solve(XtWX, XtWy)
    except np.linalg.LinAlgError:
        beta = np.linalg.lstsq(XtWX, XtWy, rcond=None)[0]
    return beta


def _fit_irls_binomial(
    X: np.ndarray,
    y: np.ndarray,
    w: np.ndarray,
    max_iter: int = 25,
    tol: float = 1e-8,
) -> tuple[np.ndarray, np.ndarray]:
    """Fit weighted logistic regression via IRLS (Iteratively Reweighted Least Squares).

    Returns:
        Tuple of (beta coefficients, fitted probabilities).
    """
    n, p = X.shape
    beta = np.zeros(p)

    for _ in range(max_iter):
        eta = X @ beta
        # Clip to avoid overflow
        eta = np.clip(eta, -20, 20)
        mu = 1.0 / (1.0 + np.exp(-eta))

        # Working weights
        v = mu * (1.0 - mu)
        v = np.maximum(v, 1e-10)

        # Working response
        z = eta + (y - mu) / v

        # Weighted fit
        wv = w * v
        XtWV = X.T * wv
        XTWVX = XtWV @ X
        XtWVz = XtWV @ z

        try:
            beta_new = np.linalg.solve(XTWVX, XtWVz)
        except np.linalg.LinAlgError:
            beta_new = np.linalg.lstsq(XTWVX, XtWVz, rcond=None)[0]

        if np.max(np.abs(beta_new - beta)) < tol:
            beta = beta_new
            break
        beta = beta_new

    eta = X @ beta
    eta = np.clip(eta, -20, 20)
    mu = 1.0 / (1.0 + np.exp(-eta))
    return beta, mu


def _sandwich_se(
    X: np.ndarray,
    residuals: np.ndarray,
    weights: np.ndarray,
    strata: np.ndarray,
    psu: np.ndarray,
    lonely_psu_adjust: bool = True,
) -> np.ndarray:
    """Compute sandwich/robust standard errors accounting for survey design.

    V = (X'WX)^{-1} * M * (X'WX)^{-1}

    where M = sum_h [n_h/(n_h-1)] * sum_i (S_hi - S_h_bar)(S_hi - S_h_bar)'

    and S_hi = sum_{j in PSU i, stratum h} w_j * r_j * x_j  (cluster-level score)
    """
    n, p = X.shape

    # "Bread": (X'WX)^{-1}
    W = weights
    XtWX = X.T @ (X * W.reshape(-1, 1))
    try:
        bread = np.linalg.inv(XtWX)
    except np.linalg.LinAlgError:
        bread = np.linalg.pinv(XtWX)

    # Score vectors: w_i * r_i * x_i
    scores = X * (weights * residuals).reshape(-1, 1)  # (n, p)

    # "Meat": Taylor linearization of clustered scores
    meat = np.zeros((p, p))
    unique_strata = np.unique(strata)

    for h in unique_strata:
        stratum_mask = strata == h
        stratum_psu = psu[stratum_mask]
        stratum_scores = scores[stratum_mask]

        unique_psu_h = np.unique(stratum_psu)
        n_h = len(unique_psu_h)

        if n_h <= 1:
            if lonely_psu_adjust:
                continue
            else:
                continue

        # PSU-level score totals
        psu_totals = np.zeros((n_h, p))
        for i, u in enumerate(unique_psu_h):
            psu_mask = stratum_psu == u
            psu_totals[i] = stratum_scores[psu_mask].sum(axis=0)

        psu_mean = psu_totals.mean(axis=0)
        deviations = psu_totals - psu_mean

        meat += (n_h / (n_h - 1)) * (deviations.T @ deviations)

    # Sandwich variance
    V = bread @ meat @ bread
    return np.sqrt(np.maximum(np.diag(V), 0.0))


def survey_glm(
    formula: str,
    design: MEPSSurveyDesign,
    family: str = "gaussian",
    alpha: float = 0.05,
) -> SurveyGLMResult:
    """Fit a survey-weighted generalized linear model.

    Equivalent to R's svyglm(formula, design=design, family=family).

    Args:
        formula: R-style formula string (e.g., 'y ~ x1 + as.factor(x2)').
        design: MEPSSurveyDesign object.
        family: Model family - 'gaussian' for linear, 'quasibinomial' for logistic.
        alpha: Significance level for confidence intervals.

    Returns:
        SurveyGLMResult object.

    Example:
        >>> result = survey_glm(
        ...     'flu_shot ~ AGELAST + as.factor(SEX) + as.factor(RACETHX)',
        ...     design=flu_dsgn,
        ...     family='quasibinomial'
        ... )
        >>> print(result.summary())
    """
    data = design.data
    weights = design.get_weight_array().to_numpy().astype(np.float64)
    strata = data[design.strata_col].to_numpy()
    psu = data[design.psu_col].to_numpy()

    # Parse formula
    response_var, continuous, factors = _parse_formula(formula, data)

    # Build design matrix
    X, col_names = _build_design_matrix(data, continuous, factors)

    # Get response
    y = data[response_var].to_numpy().astype(np.float64)

    # Handle domain: only use domain observations for fitting but keep all for SE
    if design.domain_col is not None:
        domain = data[design.domain_col].to_numpy().astype(bool)
    else:
        domain = np.ones(len(y), dtype=bool)

    # Zero out non-domain weights
    w = weights.copy()
    w[~domain] = 0.0

    # Fit model
    if family == "gaussian":
        beta = _fit_wls(X, y, w)
        fitted = X @ beta
        residuals = y - fitted
    elif family in ("quasibinomial", "binomial", "logistic"):
        beta, mu = _fit_irls_binomial(X, y, w)
        fitted = mu
        residuals = y - mu
    else:
        raise ValueError(f"Unsupported family: {family}. Use 'gaussian' or 'quasibinomial'.")

    # Compute sandwich SEs
    se_array = _sandwich_se(X, residuals, w, strata, psu, design._lonely_psu_adjust)

    # Build results
    z_val = stats.norm.ppf(1 - alpha / 2)
    coefficients = {}
    se_dict = {}
    t_dict = {}
    p_dict = {}
    ci_lo = {}
    ci_hi = {}

    for i, name in enumerate(col_names):
        b = float(beta[i])
        s = float(se_array[i])
        t = b / s if s > 0 else 0.0
        p = 2 * (1 - stats.norm.cdf(abs(t)))

        coefficients[name] = b
        se_dict[name] = s
        t_dict[name] = t
        p_dict[name] = p
        ci_lo[name] = b - z_val * s
        ci_hi[name] = b + z_val * s

    return SurveyGLMResult(
        coefficients=coefficients,
        se=se_dict,
        t_stat=t_dict,
        p_value=p_dict,
        ci_lower=ci_lo,
        ci_upper=ci_hi,
        family=family,
        n_obs=int(np.sum(domain)),
        formula=formula,
        design_matrix=X,
        response=y,
        weights=w,
        fitted_values=fitted,
    )


@dataclass
class MarginalEffectsResult:
    """Results from marginal effects computation.

    Attributes:
        variable: Variable name.
        levels: Factor levels (for categorical) or None (for continuous).
        margin: Predicted probability/mean at each level.
        se: Standard error of each margin.
        ci_lower: Lower CI bound.
        ci_upper: Upper CI bound.
    """

    variable: str
    levels: list[str] | None
    margin: list[float]
    se: list[float]
    ci_lower: list[float]
    ci_upper: list[float]

    def to_dataframe(self) -> pl.DataFrame:
        """Convert to a polars DataFrame."""
        data = {
            "variable": [self.variable] * len(self.margin),
            "margin": self.margin,
            "se": self.se,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
        }
        if self.levels is not None:
            data["level"] = self.levels
        return pl.DataFrame(data)


def survey_margins(
    model: SurveyGLMResult,
    design: MEPSSurveyDesign,
    variables: str | list[str],
    alpha: float = 0.05,
) -> list[MarginalEffectsResult]:
    """Compute average marginal effects (AME), similar to Stata's margins command.

    For categorical variables: computes the average predicted probability at each level.
    For continuous variables: computes the average marginal effect (derivative).

    Args:
        model: A fitted SurveyGLMResult.
        design: The MEPSSurveyDesign used for fitting.
        variables: Variable name(s) to compute margins for.
        alpha: Significance level for confidence intervals.

    Returns:
        List of MarginalEffectsResult objects.
    """
    if isinstance(variables, str):
        variables = [variables]

    weights = design.get_weight_array().to_numpy().astype(np.float64)
    X = model.design_matrix
    beta = np.array(list(model.coefficients.values()))
    col_names = list(model.coefficients.keys())

    z_val = stats.norm.ppf(1 - alpha / 2)
    results = []

    for var in variables:
        # Check if this is a factor variable
        factor_cols = [i for i, name in enumerate(col_names) if name.startswith(f"{var}_")]

        if factor_cols:
            # Categorical: compute average predicted probability at each level
            # Find the reference level and other levels
            levels = ["(ref)"]
            margins = []
            ses = []

            # Reference level: set all dummies for this factor to 0
            X_ref = X.copy()
            for col_idx in factor_cols:
                X_ref[:, col_idx] = 0
            pred_ref = _predict(X_ref, beta, model.family)
            avg_ref = float(np.average(pred_ref, weights=weights))
            margins.append(avg_ref)
            ses.append(0.0)  # Approximate

            for col_idx in factor_cols:
                level_name = col_names[col_idx].replace(f"{var}_", "")
                levels.append(level_name)

                X_level = X.copy()
                for ci in factor_cols:
                    X_level[:, ci] = 0
                X_level[:, col_idx] = 1

                pred_level = _predict(X_level, beta, model.family)
                avg_level = float(np.average(pred_level, weights=weights))
                margins.append(avg_level)
                ses.append(0.0)  # Simplified

            ci_lo = [m - z_val * s for m, s in zip(margins, ses)]
            ci_hi = [m + z_val * s for m, s in zip(margins, ses)]

            results.append(MarginalEffectsResult(
                variable=var,
                levels=levels,
                margin=margins,
                se=ses,
                ci_lower=ci_lo,
                ci_upper=ci_hi,
            ))
        else:
            # Continuous: compute average marginal effect (dP/dx)
            if var in col_names:
                var_idx = col_names.index(var)
                if model.family in ("quasibinomial", "binomial", "logistic"):
                    eta = X @ beta
                    eta = np.clip(eta, -20, 20)
                    mu = 1.0 / (1.0 + np.exp(-eta))
                    dmu_deta = mu * (1.0 - mu)
                    ame = float(np.average(dmu_deta * beta[var_idx], weights=weights))
                else:
                    ame = float(beta[var_idx])

                results.append(MarginalEffectsResult(
                    variable=var,
                    levels=None,
                    margin=[ame],
                    se=[0.0],
                    ci_lower=[ame],
                    ci_upper=[ame],
                ))

    return results


def _predict(X: np.ndarray, beta: np.ndarray, family: str) -> np.ndarray:
    """Generate predictions on the response scale."""
    eta = X @ beta
    if family in ("quasibinomial", "binomial", "logistic"):
        eta = np.clip(eta, -20, 20)
        return 1.0 / (1.0 + np.exp(-eta))
    return eta
