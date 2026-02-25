"""Exercise 4d: Pooling 2017-2019 Data with Variance Estimation File.

Migrated from: SAS/workshop_exercises/exercise_4d/Exercise4.sas

Pools 2017, 2018, and 2019 data and calculates:
  - Percentage of people with Joint Pain / Arthritis
  - Average expenditures per person, by Joint Pain status
  - Standard errors using common variance structure from pooled linkage file

Input files:
  - 2017 Full-Year Consolidated file
  - 2018 Full-Year Consolidated file
  - 2019 Full-Year Consolidated file
  - 1996-2019 pooled linkage variance estimation file

SAS → PySpark Migration Notes:
  - 3-way SET with year-specific renames → prepare/union pattern
  - DUPERSID 8-char to 10-char conversion → string manipulation
  - Match-merge with variance estimation file → join
  - STRATUM stra9619 / CLUSTER psu9619 → custom variance structure
"""

from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean_by_domain


def prepare_year(
    spark: SparkSession,
    year: int,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Prepare a single year's data with standardized variables.

    Handles year-specific variable naming and joint pain variable
    differences between pre-2018 and post-2018 CAPI redesign.

    Args:
        spark: Active SparkSession.
        year: Data year (2017, 2018, or 2019).
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        Prepared DataFrame with standardized column names.
    """
    df = input_df
    yr_suffix = str(year)[2:]

    # Standardize variable names
    df = (
        df
        .withColumnRenamed(f"TOTEXP{yr_suffix}", "TOTEXP")
        .withColumnRenamed(f"TOTSLF{yr_suffix}", "TOTSLF")
        .withColumn("YEAR", F.lit(year))
    )

    # Set pooled weight (divide by 3 for 3-year pooling)
    wt_col = f"PERWT{yr_suffix}F"
    df = df.withColumn("PERWTF", F.col(wt_col) / 3.0)

    # Standardize joint pain variable
    if year == 2017:
        df = df.withColumnRenamed("JTPAIN31", "JTPAIN")
    else:
        if "JTPAIN31_M18" in df.columns:
            df = df.withColumnRenamed("JTPAIN31_M18", "JTPAIN")
        elif "JTPAIN31_m18" in df.columns:
            df = df.withColumnRenamed("JTPAIN31_m18", "JTPAIN")

    # Create SPOP and JOINT_PAIN
    df = df.withColumn("SPOP", F.lit(0))

    if year == 2017:
        df = df.withColumn(
            "SPOP",
            F.when(
                (F.col("AGELAST") >= 18)
                & ~((F.col("ARTHDX") <= 0) & (F.col("JTPAIN") < 0)),
                1
            ).otherwise(0)
        )
    else:
        df = df.withColumn(
            "SPOP",
            F.when(
                (F.col("AGELAST") >= 18)
                & ~((F.col("ARTHDX") < 0) & (F.col("JTPAIN") < 0)),
                1
            ).otherwise(0)
        )

    df = df.withColumn(
        "JOINT_PAIN",
        F.when(
            (F.col("SPOP") == 1)
            & ((F.col("ARTHDX") == 1) | (F.col("JTPAIN") == 1)),
            1
        ).when(F.col("SPOP") == 1, 2)
    )

    return df


def pool_years(year_dfs: list) -> DataFrame:
    """Pool multiple years of data.

    Args:
        year_dfs: List of prepared year DataFrames.

    Returns:
        Pooled DataFrame.
    """
    common_cols = set(year_dfs[0].columns)
    for df in year_dfs[1:]:
        common_cols = common_cols & set(df.columns)
    common_cols = list(common_cols)

    result = year_dfs[0].select(common_cols)
    for df in year_dfs[1:]:
        result = result.union(df.select(common_cols))

    return result


def merge_variance_file(
    pooled_df: DataFrame,
    vs_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Merge pooled data with variance estimation file.

    The variance estimation file provides stra9619 and psu9619 for
    proper variance estimation across pooled years.

    Args:
        pooled_df: Pooled data DataFrame.
        vs_df: Variance structure DataFrame (optional).

    Returns:
        Merged DataFrame with variance structure variables.
    """
    if vs_df is None:
        return pooled_df

    merged = pooled_df.join(vs_df, on="DUPERSID", how="left")
    return merged


def estimate_joint_pain(df: DataFrame) -> dict:
    """Estimate joint pain prevalence and expenditures.

    Uses stra9619/psu9619 if available, else VARSTR/VARPSU.

    Args:
        df: Pooled and merged DataFrame.

    Returns:
        Dictionary with estimates.
    """
    stratum = "stra9619" if "stra9619" in df.columns else "VARSTR"
    cluster = "psu9619" if "psu9619" in df.columns else "VARPSU"

    # Joint pain proportion
    proportion = survey_mean_by_domain(
        df,
        var_cols=["JOINT_PAIN"],
        domain_col="SPOP",
        domain_value=1,
        weight_col="PERWTF",
        stratum_col=stratum,
        cluster_col=cluster,
    )

    # Expenditures by joint pain status
    expenditures = survey_mean_by_domain(
        df,
        var_cols=["TOTEXP", "TOTSLF"],
        domain_col="SPOP",
        domain_value=1,
        weight_col="PERWTF",
        by_col="JOINT_PAIN",
        stratum_col=stratum,
        cluster_col=cluster,
    )

    return {
        "joint_pain_proportion": proportion,
        "expenditures_by_joint_pain": expenditures,
    }


def run(
    spark: SparkSession,
    year_dfs: Optional[list] = None,
    vs_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full Exercise 4d analysis pipeline.

    Args:
        spark: Active SparkSession.
        year_dfs: List of (year, DataFrame) tuples for each year.
        vs_df: Variance structure DataFrame.

    Returns:
        Dictionary with all analysis results.
    """
    prepared = []
    for year, df in year_dfs:
        prepared.append(prepare_year(spark, year, df))

    pooled = pool_years(prepared)
    merged = merge_variance_file(pooled, vs_df)
    estimates = estimate_joint_pain(merged)

    return {
        "pooled_data": pooled,
        "merged_data": merged,
        **estimates,
    }
