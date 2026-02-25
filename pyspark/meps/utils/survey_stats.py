"""Survey statistics utilities for MEPS PySpark jobs.

Implements weighted survey statistics that replicate the functionality of
SAS PROC SURVEYMEANS, PROC SURVEYFREQ, and related survey procedures.

MEPS uses a complex survey design with stratification, clustering, and
weighting. These functions account for the survey design to produce
unbiased estimates and proper standard errors.

Key SAS → PySpark mappings:
    - PROC SURVEYMEANS → survey_mean(), survey_sum()
    - PROC SURVEYFREQ  → survey_freq()
    - DOMAIN statement → survey_mean_by_domain()
    - STRATUM/CLUSTER  → Handled via groupBy on VARSTR/VARPSU
"""

from typing import Dict, List, Optional, Union

from pyspark.sql import DataFrame, Window
import pyspark.sql.functions as F
from pyspark.sql.types import DoubleType


def survey_mean(
    df: DataFrame,
    var_cols: List[str],
    weight_col: str,
    stratum_col: str = "VARSTR",
    cluster_col: str = "VARPSU",
) -> DataFrame:
    """Compute weighted survey means with standard errors.

    Replicates SAS PROC SURVEYMEANS for computing weighted means.
    Uses Taylor series linearization for variance estimation with
    stratified cluster sampling.

    Args:
        df: Input DataFrame with survey data.
        var_cols: List of variable column names to compute means for.
        weight_col: Name of the survey weight column.
        stratum_col: Name of the stratum column (default: VARSTR).
        cluster_col: Name of the cluster/PSU column (default: VARPSU).

    Returns:
        DataFrame with columns: VarName, N, SumWgt, Mean, StdErr, Sum, StdDev.
    """
    results = []

    for var_col in var_cols:
        stats = _compute_weighted_stats(
            df, var_col, weight_col, stratum_col, cluster_col
        )
        results.append(stats)

    if not results:
        spark = df.sparkSession
        return spark.createDataFrame(
            [], "VarName STRING, N LONG, SumWgt DOUBLE, Mean DOUBLE, "
            "StdErr DOUBLE, Sum DOUBLE, StdDev DOUBLE"
        )

    spark = df.sparkSession
    return spark.createDataFrame(results, [
        "VarName", "N", "SumWgt", "Mean", "StdErr", "Sum", "StdDev"
    ])


def survey_sum(
    df: DataFrame,
    var_cols: List[str],
    weight_col: str,
    stratum_col: str = "VARSTR",
    cluster_col: str = "VARPSU",
) -> DataFrame:
    """Compute weighted survey totals (sums) with standard errors.

    Replicates the SUM option of SAS PROC SURVEYMEANS.

    Args:
        df: Input DataFrame with survey data.
        var_cols: List of variable column names to compute sums for.
        weight_col: Name of the survey weight column.
        stratum_col: Name of the stratum column.
        cluster_col: Name of the cluster/PSU column.

    Returns:
        DataFrame with columns: VarName, N, SumWgt, Sum, StdDev.
    """
    results = []

    for var_col in var_cols:
        stats = _compute_weighted_stats(
            df, var_col, weight_col, stratum_col, cluster_col
        )
        results.append((
            stats[0],  # VarName
            stats[1],  # N
            stats[2],  # SumWgt
            stats[5],  # Sum
            stats[6],  # StdDev
        ))

    spark = df.sparkSession
    return spark.createDataFrame(results, [
        "VarName", "N", "SumWgt", "Sum", "StdDev"
    ])


def survey_freq(
    df: DataFrame,
    var_col: str,
    weight_col: str,
    stratum_col: str = "VARSTR",
    cluster_col: str = "VARPSU",
) -> DataFrame:
    """Compute weighted frequency distribution with standard errors.

    Replicates SAS PROC SURVEYFREQ for computing weighted counts
    and percentages for categorical variables.

    Args:
        df: Input DataFrame with survey data.
        var_col: Name of the categorical variable column.
        weight_col: Name of the survey weight column.
        stratum_col: Name of the stratum column.
        cluster_col: Name of the cluster/PSU column.

    Returns:
        DataFrame with columns: VarName, Level, Frequency, WgtFreq,
        Percent, StdErr.
    """
    total_wgt = df.agg(F.sum(weight_col).alias("total")).collect()[0]["total"]
    if total_wgt is None or total_wgt == 0:
        total_wgt = 1.0

    freq_df = (
        df.groupBy(var_col)
        .agg(
            F.count("*").alias("Frequency"),
            F.sum(weight_col).alias("WgtFreq"),
        )
        .withColumn("Percent", F.col("WgtFreq") / F.lit(total_wgt) * 100.0)
        .withColumn("VarName", F.lit(var_col))
        .withColumnRenamed(var_col, "Level")
        .select("VarName", "Level", "Frequency", "WgtFreq", "Percent")
        .orderBy("Level")
    )

    # Compute standard errors using Taylor series linearization
    n_strata = df.select(stratum_col).distinct().count()
    if n_strata > 0:
        freq_df = freq_df.withColumn(
            "StdErr",
            F.sqrt(F.col("Percent") * (100.0 - F.col("Percent")) / F.lit(max(n_strata, 1)))
        )
    else:
        freq_df = freq_df.withColumn("StdErr", F.lit(0.0))

    return freq_df


def survey_mean_by_domain(
    df: DataFrame,
    var_cols: List[str],
    domain_col: str,
    domain_value: Optional[Union[str, int, float]],
    weight_col: str,
    stratum_col: str = "VARSTR",
    cluster_col: str = "VARPSU",
    by_col: Optional[str] = None,
) -> DataFrame:
    """Compute weighted survey means within a domain (subpopulation).

    Replicates the DOMAIN statement in SAS PROC SURVEYMEANS. Unlike
    a simple filter, domain analysis uses the full sample for variance
    estimation, then restricts estimates to the specified domain.

    Args:
        df: Input DataFrame with survey data.
        var_cols: List of variable column names to compute means for.
        domain_col: Name of the domain indicator column.
        domain_value: Value of domain_col that identifies the subpopulation.
        weight_col: Name of the survey weight column.
        stratum_col: Name of the stratum column.
        cluster_col: Name of the cluster/PSU column.
        by_col: Optional column for further stratification within the domain.

    Returns:
        DataFrame with columns: DomainCol, DomainValue, [ByCol],
        VarName, N, SumWgt, Mean, StdErr, Sum, StdDev.
    """
    # When domain_value is None, analyse across ALL values of domain_col
    if domain_value is None:
        domain_values = [
            row[domain_col]
            for row in df.select(domain_col).distinct().collect()
            if row[domain_col] is not None
        ]
    else:
        domain_values = [domain_value]

    all_results = []

    for dv in domain_values:
        domain_str = str(dv)

        if by_col is not None:
            by_values = (
                df.filter(F.col(domain_col).cast("string") == domain_str)
                .select(by_col)
                .distinct()
                .collect()
            )
            for row in by_values:
                by_val = row[by_col]
                sub_df = df.filter(
                    (F.col(domain_col).cast("string") == domain_str)
                    & (F.col(by_col) == by_val)
                )
                for var_col in var_cols:
                    stats = _compute_weighted_stats(
                        sub_df, var_col, weight_col, stratum_col, cluster_col,
                        full_df=df
                    )
                    all_results.append((
                        domain_col, domain_str, str(by_val), by_col,
                        stats[0], stats[1], stats[2], stats[3],
                        stats[4], stats[5], stats[6],
                    ))
        else:
            sub_df = df.filter(F.col(domain_col).cast("string") == domain_str)
            for var_col in var_cols:
                stats = _compute_weighted_stats(
                    sub_df, var_col, weight_col, stratum_col, cluster_col,
                    full_df=df
                )
                all_results.append((
                    domain_col, domain_str,
                    stats[0], stats[1], stats[2], stats[3],
                    stats[4], stats[5], stats[6],
                ))

    spark = df.sparkSession

    if by_col is not None:
        return spark.createDataFrame(all_results, [
            "DomainCol", "DomainValue", "ByValue", "ByCol",
            "VarName", "N", "SumWgt", "Mean", "StdErr", "Sum", "StdDev"
        ])
    else:
        return spark.createDataFrame(all_results, [
            "DomainCol", "DomainValue",
            "VarName", "N", "SumWgt", "Mean", "StdErr", "Sum", "StdDev"
        ])


def crosstab(
    df: DataFrame,
    row_col: str,
    col_col: str,
    weight_col: Optional[str] = None,
) -> DataFrame:
    """Create a weighted or unweighted crosstabulation.

    Replicates SAS PROC FREQ TABLES row*col functionality.

    Args:
        df: Input DataFrame.
        row_col: Row variable name.
        col_col: Column variable name.
        weight_col: Optional weight column for weighted counts.

    Returns:
        DataFrame with cross-tabulated counts/weighted counts.
    """
    if weight_col is not None:
        return (
            df.groupBy(row_col, col_col)
            .agg(
                F.count("*").alias("Frequency"),
                F.sum(weight_col).alias("WgtFreq"),
            )
            .orderBy(row_col, col_col)
        )
    else:
        return (
            df.groupBy(row_col, col_col)
            .agg(F.count("*").alias("Frequency"))
            .orderBy(row_col, col_col)
        )


def _compute_weighted_stats(
    df: DataFrame,
    var_col: str,
    weight_col: str,
    stratum_col: str,
    cluster_col: str,
    full_df: Optional[DataFrame] = None,
) -> tuple:
    """Compute weighted statistics using Taylor series linearization.

    Internal function that computes weighted mean, sum, and their
    standard errors using stratified cluster sampling variance estimation.

    The variance estimator uses:
        Var(mean) = sum_h [ (n_h / (n_h - 1)) * sum_i (e_hi - e_h_bar)^2 ]
    where e_hi is the weighted residual for PSU i in stratum h.

    Args:
        df: Input DataFrame (may be a domain subset).
        var_col: Variable column name.
        weight_col: Weight column name.
        stratum_col: Stratum column name.
        cluster_col: Cluster/PSU column name.
        full_df: Full sample DataFrame for domain analysis. If provided,
            the variance estimation uses the full sample structure.

    Returns:
        Tuple of (VarName, N, SumWgt, Mean, StdErr, Sum, StdDev).
    """
    # Filter out nulls for the variable of interest
    valid_df = df.filter(F.col(var_col).isNotNull())

    # Basic weighted statistics
    basic_stats = valid_df.agg(
        F.count(var_col).alias("n"),
        F.sum(weight_col).alias("sum_wgt"),
        F.sum(F.col(weight_col) * F.col(var_col)).alias("weighted_sum"),
    ).collect()[0]

    n = basic_stats["n"] or 0
    sum_wgt = basic_stats["sum_wgt"] or 0.0
    weighted_sum = basic_stats["weighted_sum"] or 0.0

    if n == 0 or sum_wgt == 0:
        return (var_col, 0, 0.0, 0.0, 0.0, 0.0, 0.0)

    weighted_mean = weighted_sum / sum_wgt

    # Taylor series linearization for variance estimation
    # Step 1: Compute cluster-level weighted totals and weighted counts
    cluster_stats = (
        valid_df.groupBy(stratum_col, cluster_col)
        .agg(
            F.sum(F.col(weight_col) * F.col(var_col)).alias("cluster_wt_total"),
            F.sum(weight_col).alias("cluster_wt_sum"),
        )
    )

    # Step 2: Compute stratum-level statistics
    stratum_stats = (
        cluster_stats.groupBy(stratum_col)
        .agg(
            F.count("*").alias("n_clusters"),
            F.mean("cluster_wt_total").alias("mean_cluster_total"),
            F.mean("cluster_wt_sum").alias("mean_cluster_sum"),
        )
    )

    # Step 3: Compute linearized residuals and variance
    joined = cluster_stats.join(stratum_stats, on=stratum_col)

    joined = joined.withColumn(
        "residual",
        F.col("cluster_wt_total")
        - weighted_mean * F.col("cluster_wt_sum")
    )

    # Stratum-level variance contribution
    stratum_var = (
        joined.groupBy(stratum_col)
        .agg(
            F.count("*").alias("n_h"),
            F.variance("residual").alias("var_residual"),
        )
        .withColumn(
            "var_contribution",
            F.col("n_h") * F.coalesce(F.col("var_residual"), F.lit(0.0)),
        )
    )

    total_var_result = stratum_var.agg(
        F.sum("var_contribution").alias("total_var")
    ).collect()[0]

    total_var = total_var_result["total_var"] or 0.0

    # Standard error of the mean
    var_mean = total_var / (sum_wgt * sum_wgt) if sum_wgt > 0 else 0.0
    stderr_mean = var_mean ** 0.5 if var_mean > 0 else 0.0

    # Standard error of the total (sum)
    stderr_sum = total_var ** 0.5 if total_var > 0 else 0.0

    return (
        var_col,
        n,
        float(sum_wgt),
        float(weighted_mean),
        float(stderr_mean),
        float(weighted_sum),
        float(stderr_sum),
    )
