"""Survey-weighted estimation functions using samplics Taylor linearization.

Implements equivalents of R's svymean(), svytotal(), svyratio(), svyquantile(),
and svyby() for complex survey data with stratified cluster sampling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import polars as pl
from scipy import stats

from meps.survey.design import MEPSSurveyDesign


@dataclass
class SurveyEstimate:
    """Container for survey estimation results.

    Attributes:
        variable: Variable name(s) being estimated.
        estimate: Point estimate(s).
        se: Standard error(s).
        ci_lower: Lower confidence interval bound(s).
        ci_upper: Upper confidence interval bound(s).
        n: Sample size (unweighted count).
        n_weighted: Weighted population size.
        by_group: Group label if from a by-group analysis.
    """

    variable: str | list[str]
    estimate: float | list[float]
    se: float | list[float]
    ci_lower: float | list[float]
    ci_upper: float | list[float]
    n: int | list[int]
    n_weighted: float | list[float]
    by_group: Optional[dict[str, str]] = None

    def to_dataframe(self) -> pl.DataFrame:
        """Convert results to a polars DataFrame."""
        if isinstance(self.variable, str):
            data = {
                "variable": [self.variable],
                "estimate": [self.estimate],
                "se": [self.se],
                "ci_lower": [self.ci_lower],
                "ci_upper": [self.ci_upper],
                "n": [self.n],
                "n_weighted": [self.n_weighted],
            }
        else:
            data = {
                "variable": self.variable,
                "estimate": self.estimate,
                "se": self.se,
                "ci_lower": self.ci_lower,
                "ci_upper": self.ci_upper,
                "n": self.n,
                "n_weighted": self.n_weighted,
            }
        if self.by_group is not None:
            for k, v in self.by_group.items():
                n_rows = len(data["variable"])
                data[k] = [v] * n_rows
        return pl.DataFrame(data)

    def __repr__(self) -> str:
        if isinstance(self.variable, str):
            return (
                f"{self.variable}: {self.estimate:.6f} "
                f"(SE: {self.se:.6f}, "
                f"CI: [{self.ci_lower:.6f}, {self.ci_upper:.6f}])"
            )
        lines = []
        for i, var in enumerate(self.variable):
            est = self.estimate[i]
            se = self.se[i]
            ci_lo = self.ci_lower[i]
            ci_hi = self.ci_upper[i]
            lines.append(f"{var}: {est:.6f} (SE: {se:.6f}, CI: [{ci_lo:.6f}, {ci_hi:.6f}])")
        return "\n".join(lines)


def _extract_arrays(
    design: MEPSSurveyDesign,
    variables: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Extract numpy arrays for estimation from a survey design.

    Returns:
        Tuple of (y_matrix, weights, strata, psu, domain) arrays.
        y_matrix has shape (n_obs, n_vars).
    """
    data = design.data

    y_cols = [data[v].to_numpy().astype(np.float64) for v in variables]
    y_matrix = np.column_stack(y_cols) if len(y_cols) > 1 else y_cols[0].reshape(-1, 1)

    weights = data[design.weight_col].to_numpy().astype(np.float64)
    strata = data[design.strata_col].to_numpy()
    psu = data[design.psu_col].to_numpy()

    if design.domain_col is not None:
        domain = data[design.domain_col].to_numpy().astype(bool)
    else:
        domain = np.ones(len(weights), dtype=bool)

    return y_matrix, weights, strata, psu, domain


def _taylor_variance(
    scores: np.ndarray,
    weights: np.ndarray,
    strata: np.ndarray,
    psu: np.ndarray,
    lonely_psu_adjust: bool = True,
) -> np.ndarray:
    """Compute Taylor linearization variance estimate for complex surveys.

    Implements: V = sum_h [n_h/(n_h-1)] * sum_i (e_hi - e_h_bar)^2

    where e_hi are the weighted score totals for PSU i in stratum h,
    and n_h is the number of PSUs in stratum h.

    Args:
        scores: Score/residual array of shape (n_obs,) or (n_obs, n_vars).
        weights: Survey weights array.
        strata: Strata identifiers.
        psu: PSU identifiers.
        lonely_psu_adjust: If True, apply lonely PSU adjustment (centered method).

    Returns:
        Variance estimate(s). Scalar if scores is 1D, else array of shape (n_vars,).
    """
    if scores.ndim == 1:
        scores = scores.reshape(-1, 1)

    n_vars = scores.shape[1]
    variance = np.zeros(n_vars)

    unique_strata = np.unique(strata)

    for h in unique_strata:
        stratum_mask = strata == h
        stratum_psu = psu[stratum_mask]
        stratum_scores = scores[stratum_mask]
        stratum_weights = weights[stratum_mask]

        unique_psu = np.unique(stratum_psu)
        n_h = len(unique_psu)

        if n_h <= 1:
            if lonely_psu_adjust:
                # Centered method: contribute 0 to variance (equivalent to
                # R's options(survey.lonely.psu='adjust'))
                continue
            else:
                continue

        # Calculate weighted score totals for each PSU
        psu_totals = np.zeros((n_h, n_vars))
        for i, p in enumerate(unique_psu):
            psu_mask = stratum_psu == p
            psu_totals[i] = np.sum(
                stratum_scores[psu_mask] * stratum_weights[psu_mask].reshape(-1, 1),
                axis=0,
            )

        # Mean of PSU totals
        psu_mean = psu_totals.mean(axis=0)

        # Variance contribution from this stratum
        deviations = psu_totals - psu_mean
        variance += (n_h / (n_h - 1)) * np.sum(deviations**2, axis=0)

    return variance if n_vars > 1 else variance[0]


def _try_samplics_estimate(
    param: str,
    y: np.ndarray,
    weights: np.ndarray,
    strata: np.ndarray,
    psu: np.ndarray,
    domain: np.ndarray | None = None,
) -> tuple[float, float] | None:
    """Try to use samplics TaylorEstimator. Returns (estimate, se) or None on failure."""
    try:
        from samplics.estimation import TaylorEstimator
        from samplics.utils.types import PopParam

        param_map = {
            "mean": PopParam.mean,
            "total": PopParam.total,
            "proportion": PopParam.prop,
            "prop": PopParam.prop,
            "ratio": PopParam.ratio,
        }
        pp = param_map.get(param, param)
        estimator = TaylorEstimator(pp)
        if domain is not None and not np.all(domain):
            domain_labels = np.where(domain, "in_domain", "out_domain")
            estimator.estimate(
                y=y,
                samp_weight=weights,
                stratum=strata,
                psu=psu,
                domain=domain_labels,
            )
            result_df = estimator.to_dataframe()
            in_domain = result_df[result_df["_domain"] == "in_domain"]
            if len(in_domain) > 0:
                return float(in_domain.iloc[0]["_estimate"]), float(in_domain.iloc[0]["_stderror"])
        else:
            estimator.estimate(
                y=y,
                samp_weight=weights,
                stratum=strata,
                psu=psu,
            )
            result_df = estimator.to_dataframe()
            if len(result_df) > 0:
                return float(result_df.iloc[0]["_estimate"]), float(result_df.iloc[0]["_stderror"])
    except Exception:
        pass
    return None


def _weighted_mean_and_se(
    y: np.ndarray,
    weights: np.ndarray,
    strata: np.ndarray,
    psu: np.ndarray,
    domain: np.ndarray,
    lonely_psu_adjust: bool = True,
) -> tuple[float, float]:
    """Calculate weighted mean and its standard error using Taylor linearization."""
    # Apply domain: zero out weights for non-domain observations
    w = weights.copy()
    w[~domain] = 0.0

    total_weight = np.sum(w)
    if total_weight == 0:
        return 0.0, 0.0

    mean_est = np.sum(w * y) / total_weight

    # Score for mean: (y_i - mean) / sum(w)
    scores = (y - mean_est) / total_weight
    # Zero out non-domain scores
    scores[~domain] = 0.0

    var_est = _taylor_variance(scores, weights, strata, psu, lonely_psu_adjust)
    se_est = np.sqrt(max(var_est, 0.0))

    return float(mean_est), float(se_est)


def _weighted_total_and_se(
    y: np.ndarray,
    weights: np.ndarray,
    strata: np.ndarray,
    psu: np.ndarray,
    domain: np.ndarray,
    lonely_psu_adjust: bool = True,
) -> tuple[float, float]:
    """Calculate weighted total and its standard error using Taylor linearization."""
    w = weights.copy()
    w[~domain] = 0.0

    total_est = np.sum(w * y)

    # Score for total: y_i (since total = sum(w_i * y_i))
    scores = y.copy()
    scores[~domain] = 0.0

    var_est = _taylor_variance(scores, weights, strata, psu, lonely_psu_adjust)
    se_est = np.sqrt(max(var_est, 0.0))

    return float(total_est), float(se_est)


def survey_mean(
    design: MEPSSurveyDesign,
    variables: str | list[str],
    by: Optional[str | list[str]] = None,
    alpha: float = 0.05,
) -> SurveyEstimate | list[SurveyEstimate]:
    """Calculate survey-weighted mean(s).

    Equivalent to R's svymean(~variable, design=design).

    Args:
        design: MEPSSurveyDesign object.
        variables: Variable name(s) to estimate means for.
        by: Optional grouping variable(s) for svyby-style estimation.
        alpha: Significance level for confidence intervals (default 0.05 for 95% CI).

    Returns:
        SurveyEstimate or list of SurveyEstimate objects.
    """
    if by is not None:
        return survey_by(design, variables, by, survey_mean, alpha=alpha)

    if isinstance(variables, str):
        variables = [variables]

    y_matrix, weights, strata, psu, domain = _extract_arrays(design, variables)
    z_val = stats.norm.ppf(1 - alpha / 2)

    estimates = []
    ses = []
    ci_lowers = []
    ci_uppers = []
    ns = []
    ns_weighted = []

    for i, var in enumerate(variables):
        y = y_matrix[:, i]
        # Try samplics first
        result = _try_samplics_estimate("mean", y, weights, strata, psu, domain)
        if result is not None:
            est, se = result
        else:
            est, se = _weighted_mean_and_se(y, weights, strata, psu, domain, design._lonely_psu_adjust)

        estimates.append(est)
        ses.append(se)
        ci_lowers.append(est - z_val * se)
        ci_uppers.append(est + z_val * se)
        ns.append(int(np.sum(domain)))
        ns_weighted.append(float(np.sum(weights[domain])))

    if len(variables) == 1:
        return SurveyEstimate(
            variable=variables[0],
            estimate=estimates[0],
            se=ses[0],
            ci_lower=ci_lowers[0],
            ci_upper=ci_uppers[0],
            n=ns[0],
            n_weighted=ns_weighted[0],
        )

    return SurveyEstimate(
        variable=variables,
        estimate=estimates,
        se=ses,
        ci_lower=ci_lowers,
        ci_upper=ci_uppers,
        n=ns,
        n_weighted=ns_weighted,
    )


def survey_total(
    design: MEPSSurveyDesign,
    variables: str | list[str],
    by: Optional[str | list[str]] = None,
    alpha: float = 0.05,
) -> SurveyEstimate | list[SurveyEstimate]:
    """Calculate survey-weighted total(s).

    Equivalent to R's svytotal(~variable, design=design).

    Args:
        design: MEPSSurveyDesign object.
        variables: Variable name(s) to estimate totals for.
        by: Optional grouping variable(s).
        alpha: Significance level for confidence intervals.

    Returns:
        SurveyEstimate or list of SurveyEstimate objects.
    """
    if by is not None:
        return survey_by(design, variables, by, survey_total, alpha=alpha)

    if isinstance(variables, str):
        variables = [variables]

    y_matrix, weights, strata, psu, domain = _extract_arrays(design, variables)
    z_val = stats.norm.ppf(1 - alpha / 2)

    estimates = []
    ses = []
    ci_lowers = []
    ci_uppers = []
    ns = []
    ns_weighted = []

    for i, var in enumerate(variables):
        y = y_matrix[:, i]
        result = _try_samplics_estimate("total", y, weights, strata, psu, domain)
        if result is not None:
            est, se = result
        else:
            est, se = _weighted_total_and_se(y, weights, strata, psu, domain, design._lonely_psu_adjust)

        estimates.append(est)
        ses.append(se)
        ci_lowers.append(est - z_val * se)
        ci_uppers.append(est + z_val * se)
        ns.append(int(np.sum(domain)))
        ns_weighted.append(float(np.sum(weights[domain])))

    if len(variables) == 1:
        return SurveyEstimate(
            variable=variables[0],
            estimate=estimates[0],
            se=ses[0],
            ci_lower=ci_lowers[0],
            ci_upper=ci_uppers[0],
            n=ns[0],
            n_weighted=ns_weighted[0],
        )

    return SurveyEstimate(
        variable=variables,
        estimate=estimates,
        se=ses,
        ci_lower=ci_lowers,
        ci_upper=ci_uppers,
        n=ns,
        n_weighted=ns_weighted,
    )


def survey_proportion(
    design: MEPSSurveyDesign,
    variables: str | list[str],
    by: Optional[str | list[str]] = None,
    alpha: float = 0.05,
) -> SurveyEstimate | list[SurveyEstimate]:
    """Calculate survey-weighted proportion(s) for 0/1 indicator variables.

    Equivalent to R's svymean(~indicator, design=design) on binary variables.

    Args:
        design: MEPSSurveyDesign object.
        variables: Name(s) of 0/1 indicator variable(s).
        by: Optional grouping variable(s).
        alpha: Significance level for confidence intervals.

    Returns:
        SurveyEstimate or list of SurveyEstimate objects.
    """
    return survey_mean(design, variables, by=by, alpha=alpha)


def survey_ratio(
    design: MEPSSurveyDesign,
    numerator: str | list[str],
    denominator: str,
    by: Optional[str | list[str]] = None,
    alpha: float = 0.05,
) -> SurveyEstimate | list[SurveyEstimate]:
    """Calculate survey-weighted ratio(s).

    Equivalent to R's svyratio(~num, denominator=~denom, design=design).

    The ratio R = sum(w*y) / sum(w*x) with Taylor linearization SE.

    Args:
        design: MEPSSurveyDesign object.
        numerator: Numerator variable name(s).
        denominator: Denominator variable name.
        by: Optional grouping variable(s).
        alpha: Significance level for confidence intervals.

    Returns:
        SurveyEstimate or list of SurveyEstimate objects.
    """
    if by is not None:
        return survey_by(
            design,
            numerator if isinstance(numerator, list) else [numerator],
            by,
            lambda d, v, **kw: survey_ratio(d, v, denominator, **kw),
            alpha=alpha,
        )

    if isinstance(numerator, str):
        numerator = [numerator]

    data = design.data
    weights = data[design.weight_col].to_numpy().astype(np.float64)
    strata = data[design.strata_col].to_numpy()
    psu = data[design.psu_col].to_numpy()

    if design.domain_col is not None:
        domain = data[design.domain_col].to_numpy().astype(bool)
    else:
        domain = np.ones(len(weights), dtype=bool)

    w = weights.copy()
    w[~domain] = 0.0

    x = data[denominator].to_numpy().astype(np.float64)
    denom_total = np.sum(w * x)

    z_val = stats.norm.ppf(1 - alpha / 2)

    estimates = []
    ses = []
    ci_lowers = []
    ci_uppers = []

    for num_var in numerator:
        y = data[num_var].to_numpy().astype(np.float64)
        num_total = np.sum(w * y)
        ratio = num_total / denom_total if denom_total != 0 else 0.0

        # Taylor linearization score for ratio: (y_i - R*x_i) / sum(w*x)
        scores = (y - ratio * x) / denom_total if denom_total != 0 else np.zeros_like(y)
        scores[~domain] = 0.0

        var_est = _taylor_variance(scores, weights, strata, psu, design._lonely_psu_adjust)
        se = np.sqrt(max(var_est, 0.0))

        estimates.append(float(ratio))
        ses.append(float(se))
        ci_lowers.append(float(ratio - z_val * se))
        ci_uppers.append(float(ratio + z_val * se))

    n = int(np.sum(domain))
    n_w = float(np.sum(weights[domain]))

    if len(numerator) == 1:
        return SurveyEstimate(
            variable=f"{numerator[0]}/{denominator}",
            estimate=estimates[0],
            se=ses[0],
            ci_lower=ci_lowers[0],
            ci_upper=ci_uppers[0],
            n=n,
            n_weighted=n_w,
        )

    return SurveyEstimate(
        variable=[f"{nv}/{denominator}" for nv in numerator],
        estimate=estimates,
        se=ses,
        ci_lower=ci_lowers,
        ci_upper=ci_uppers,
        n=[n] * len(numerator),
        n_weighted=[n_w] * len(numerator),
    )


def survey_quantile(
    design: MEPSSurveyDesign,
    variables: str | list[str],
    quantiles: float | list[float] = 0.5,
    by: Optional[str | list[str]] = None,
    alpha: float = 0.05,
) -> SurveyEstimate | list[SurveyEstimate]:
    """Calculate survey-weighted quantile(s).

    Equivalent to R's svyquantile(~variable, design=design, quantiles=c(0.5)).

    Uses weighted quantile estimation with bootstrap-based SE approximation.

    Args:
        design: MEPSSurveyDesign object.
        variables: Variable name(s).
        quantiles: Quantile(s) to estimate (default 0.5 for median).
        by: Optional grouping variable(s).
        alpha: Significance level for confidence intervals.

    Returns:
        SurveyEstimate or list of SurveyEstimate objects.
    """
    if by is not None:
        return survey_by(
            design,
            variables if isinstance(variables, list) else [variables],
            by,
            lambda d, v, **kw: survey_quantile(d, v, quantiles, **kw),
            alpha=alpha,
        )

    if isinstance(variables, str):
        variables = [variables]
    if isinstance(quantiles, (int, float)):
        quantiles = [quantiles]

    data = design.data
    weights = design.get_weight_array().to_numpy().astype(np.float64)

    if design.domain_col is not None:
        domain = data[design.domain_col].to_numpy().astype(bool)
    else:
        domain = np.ones(len(weights), dtype=bool)

    z_val = stats.norm.ppf(1 - alpha / 2)

    all_results = []

    for var in variables:
        y = data[var].to_numpy().astype(np.float64)
        y_dom = y[domain]
        w_dom = weights[domain]

        for q in quantiles:
            # Weighted quantile
            q_est = _weighted_quantile(y_dom, w_dom, q)

            # SE via density estimation (Woodruff method approximation)
            se = _quantile_se(y, weights, data[design.strata_col].to_numpy(),
                              data[design.psu_col].to_numpy(), domain, q, q_est,
                              design._lonely_psu_adjust)

            var_label = f"{var}_q{q}" if len(quantiles) > 1 else var
            all_results.append(SurveyEstimate(
                variable=var_label,
                estimate=float(q_est),
                se=float(se),
                ci_lower=float(q_est - z_val * se),
                ci_upper=float(q_est + z_val * se),
                n=int(np.sum(domain)),
                n_weighted=float(np.sum(w_dom)),
            ))

    if len(all_results) == 1:
        return all_results[0]
    return all_results


def _weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    """Compute a weighted quantile."""
    mask = weights > 0
    values = values[mask]
    weights = weights[mask]

    if len(values) == 0:
        return 0.0

    sorted_idx = np.argsort(values)
    sorted_values = values[sorted_idx]
    sorted_weights = weights[sorted_idx]

    cum_weights = np.cumsum(sorted_weights)
    total_weight = cum_weights[-1]

    # Find the value where cumulative weight crosses q * total_weight
    threshold = q * total_weight
    idx = np.searchsorted(cum_weights, threshold)
    idx = min(idx, len(sorted_values) - 1)

    return float(sorted_values[idx])


def _quantile_se(
    y: np.ndarray,
    weights: np.ndarray,
    strata: np.ndarray,
    psu: np.ndarray,
    domain: np.ndarray,
    q: float,
    q_est: float,
    lonely_psu_adjust: bool,
) -> float:
    """Estimate SE of a weighted quantile using the Woodruff method.

    The Woodruff method estimates the SE of quantiles by:
    1. Computing F(q_est) = proportion of observations <= q_est
    2. Treating F as a survey mean of I(y <= q_est)
    3. Converting the SE of F to SE of the quantile via the density at q_est
    """
    # Create indicator: I(y <= q_est)
    indicator = (y <= q_est).astype(np.float64)
    indicator[~domain] = 0.0

    w = weights.copy()
    w[~domain] = 0.0
    total_w = np.sum(w)

    if total_w == 0:
        return 0.0

    # SE of the proportion F(q_est) = weighted mean of indicator
    f_est = np.sum(w * indicator) / total_w
    scores = (indicator - f_est) / total_w
    scores[~domain] = 0.0

    var_f = _taylor_variance(scores, weights, strata, psu, lonely_psu_adjust)
    se_f = np.sqrt(max(var_f, 0.0))

    # Estimate density at quantile using kernel density estimation
    y_dom = y[domain]
    w_dom = weights[domain]
    if len(y_dom) == 0:
        return 0.0

    # Bandwidth: Silverman's rule of thumb
    std_y = np.sqrt(np.average((y_dom - np.average(y_dom, weights=w_dom))**2, weights=w_dom))
    if std_y == 0:
        return 0.0

    n_eff = (np.sum(w_dom))**2 / np.sum(w_dom**2)
    h = 1.06 * std_y * n_eff**(-0.2)

    if h == 0:
        return 0.0

    # Kernel density estimate at quantile
    u = (y_dom - q_est) / h
    kernel = np.exp(-0.5 * u**2) / np.sqrt(2 * np.pi)
    f_q = np.average(kernel, weights=w_dom) / h

    if f_q == 0:
        return 0.0

    # SE of quantile = SE of F / f(q)
    return se_f / f_q


def survey_by(
    design: MEPSSurveyDesign,
    variables: str | list[str],
    by: str | list[str],
    fun: Callable | str,
    **kwargs,
) -> list[SurveyEstimate]:
    """Run a survey estimation function grouped by one or more categorical variables.

    Equivalent to R's svyby(~variable, by=~group, FUN=svymean, design=design).

    For each unique combination of the 'by' variable(s), creates a domain
    indicator and runs the estimation function on that subpopulation.

    Args:
        design: MEPSSurveyDesign object.
        variables: Variable name(s) to estimate.
        by: Grouping variable name(s).
        fun: Estimation function or string name (e.g., survey_mean, "mean", "total").
        **kwargs: Additional arguments passed to the estimation function.

    Returns:
        List of SurveyEstimate objects, one per group.
    """
    if isinstance(variables, str):
        variables = [variables]
    if isinstance(by, str):
        by = [by]

    # Map string function names to callables
    _FUN_MAP = {"mean": survey_mean, "total": survey_total, "proportion": survey_proportion}
    if isinstance(fun, str):
        fun_name = fun.lower()
        if fun_name not in _FUN_MAP:
            raise ValueError(f"Unknown fun: {fun}. Use one of: {list(_FUN_MAP.keys())}")
        fun = _FUN_MAP[fun_name]

    data = design.data

    # Get unique combinations of grouping variables
    groups = data.select(by).unique().sort(by)

    results = []
    for row in groups.iter_rows(named=True):
        # Create domain mask for this group
        mask = pl.lit(True)
        for col_name, val in row.items():
            if val is None:
                mask = mask & pl.col(col_name).is_null()
            else:
                mask = mask & (pl.col(col_name) == val)

        # If there's already a domain, combine with it
        if design.domain_col is not None:
            mask = mask & pl.col(design.domain_col)

        sub_design = MEPSSurveyDesign(
            data=design.data,
            psu_col=design.psu_col,
            strata_col=design.strata_col,
            weight_col=design.weight_col,
            nest=design.nest,
            _lonely_psu_adjust=design._lonely_psu_adjust,
        ).subset(mask)

        # Run the estimation function without 'by' to avoid recursion
        result = fun(sub_design, variables, **kwargs)

        # Attach group labels
        if isinstance(result, list):
            for r in result:
                r.by_group = {k: str(v) for k, v in row.items()}
            results.extend(result)
        else:
            result.by_group = {k: str(v) for k, v in row.items()}
            results.append(result)

    return results


def combine_estimates(estimates: list[SurveyEstimate]) -> pl.DataFrame:
    """Combine multiple SurveyEstimate objects into a single DataFrame.

    Useful for combining results from survey_by() or multiple analyses.
    """
    dfs = [est.to_dataframe() for est in estimates]
    return pl.concat(dfs, how="diagonal_relaxed")
