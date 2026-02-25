"""Exercise 4a: Pooling MEPS Data Files from Different Years (2015-2016).

Migrated from: SAS/workshop_exercises/exercise_4a/Exercise4a.sas

Illustrates how to pool MEPS data files from different years.
Example: Population age 26-30, uninsured, high income.

Data from 2015 and 2016 are pooled. Variables with year-specific names
are renamed before combining files. Pooled weight = PERWT / 2.

Input files:
  - 2016 Full-Year file (HC-192)
  - 2015 Full-Year file (HC-181)

SAS → PySpark Migration Notes:
  - SET with RENAME= → withColumnRenamed()
  - Concatenating datasets → union()
  - POOLWT = PERWT/2 → withColumn arithmetic
  - PROC SURVEYMEANS DOMAIN → survey_mean_by_domain()
"""

from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean_by_domain


def prepare_year1(
    spark: SparkSession,
    data_path: Optional[Path] = None,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Prepare 2015 FYC data with renamed year-specific variables.

    Args:
        spark: Active SparkSession.
        data_path: Path to H181 data file.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        DataFrame with standardized variable names.
    """
    if input_df is not None:
        df = input_df
    else:
        columns = [
            "DUPERSID", "INSCOV15", "PERWT15F", "VARSTR", "VARPSU",
            "POVCAT15", "AGELAST", "TOTSLF15",
        ]
        df = load_meps_data(spark, data_path, columns)

    df = df.filter(F.col("PERWT15F") > 0)
    df = (
        df
        .withColumnRenamed("INSCOV15", "INSCOV")
        .withColumnRenamed("PERWT15F", "PERWT")
        .withColumnRenamed("POVCAT15", "POVCAT")
        .withColumnRenamed("TOTSLF15", "TOTSLF")
    )
    return df


def prepare_year2(
    spark: SparkSession,
    data_path: Optional[Path] = None,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Prepare 2016 FYC data with renamed year-specific variables.

    Args:
        spark: Active SparkSession.
        data_path: Path to H192 data file.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        DataFrame with standardized variable names.
    """
    if input_df is not None:
        df = input_df
    else:
        columns = [
            "DUPERSID", "INSCOV16", "PERWT16F", "VARSTR", "VARPSU",
            "POVCAT16", "AGELAST", "TOTSLF16",
        ]
        df = load_meps_data(spark, data_path, columns)

    df = df.filter(F.col("PERWT16F") > 0)
    df = (
        df
        .withColumnRenamed("INSCOV16", "INSCOV")
        .withColumnRenamed("PERWT16F", "PERWT")
        .withColumnRenamed("POVCAT16", "POVCAT")
        .withColumnRenamed("TOTSLF16", "TOTSLF")
    )
    return df


def pool_data(yr1_df: DataFrame, yr2_df: DataFrame) -> DataFrame:
    """Pool 2015 and 2016 data with adjusted weights.

    Creates:
      - POOLWT = PERWT / 2
      - SUBPOP = 1 if age 26-30, POVCAT=5 (high income), INSCOV=3 (uninsured)

    Args:
        yr1_df: Prepared 2015 DataFrame.
        yr2_df: Prepared 2016 DataFrame.

    Returns:
        Pooled DataFrame with SUBPOP flag and POOLWT.
    """
    common_cols = list(set(yr1_df.columns) & set(yr2_df.columns))
    pool = yr1_df.select(common_cols).union(yr2_df.select(common_cols))

    pool = pool.withColumn("POOLWT", F.col("PERWT") / 2.0)

    pool = pool.withColumn(
        "SUBPOP",
        F.when(
            (F.col("AGELAST") >= 26)
            & (F.col("AGELAST") <= 30)
            & (F.col("POVCAT") == 5)
            & (F.col("INSCOV") == 3),
            1
        ).otherwise(2)
    )

    return pool


def estimate_totslf(df: DataFrame) -> DataFrame:
    """Estimate TOTSLF for the subpopulation.

    Replicates: PROC SURVEYMEANS DOMAIN SUBPOP("1"); VAR TOTSLF;

    Args:
        df: Pooled DataFrame.

    Returns:
        DataFrame with domain estimates.
    """
    return survey_mean_by_domain(
        df,
        var_cols=["TOTSLF"],
        domain_col="SUBPOP",
        domain_value=1,
        weight_col="POOLWT",
    )


def run(
    spark: SparkSession,
    yr1_path: Optional[Path] = None,
    yr2_path: Optional[Path] = None,
    yr1_df: Optional[DataFrame] = None,
    yr2_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full Exercise 4a analysis pipeline.

    Args:
        spark: Active SparkSession.
        yr1_path: Path to 2015 FYC file.
        yr2_path: Path to 2016 FYC file.
        yr1_df: Pre-loaded 2015 DataFrame (for testing).
        yr2_df: Pre-loaded 2016 DataFrame (for testing).

    Returns:
        Dictionary with all analysis results.
    """
    yr1 = prepare_year1(spark, yr1_path, yr1_df)
    yr2 = prepare_year2(spark, yr2_path, yr2_df)
    pooled = pool_data(yr1, yr2)
    estimates = estimate_totslf(pooled)

    return {
        "year1_data": yr1,
        "year2_data": yr2,
        "pooled_data": pooled,
        "estimates": estimates,
    }
