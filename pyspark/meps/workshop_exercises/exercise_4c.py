"""Exercise 4c: Pooling 2017-2018 Data with CAPI Redesign Discontinuity.

Migrated from: SAS/workshop_exercises/exercise_4c/Exercise4c.sas

Illustrates how to pool MEPS data files from different years, highlighting
discontinuities from the 2018 CAPI re-design.

Calculates for civilian noninstitutionalized population:
  - Percentage of people with Joint Pain / Arthritis
  - Average expenditures per person, by Joint Pain status

Input files:
  - 2017 Full-Year Consolidated file
  - 2018 Full-Year Consolidated file

SAS → PySpark Migration Notes:
  - Year-specific variable renaming → withColumnRenamed()
  - JTPAIN31 (2017) vs JTPAIN31_M18 (2018) → standardized to JTPAIN
  - Subpop/joint_pain creation logic → F.when() chains
  - PROC SURVEYMEANS CLASS/DOMAIN → survey_mean_by_domain()
"""

from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean_by_domain, survey_freq


def prepare_2017(
    spark: SparkSession,
    data_path: Optional[Path] = None,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Prepare 2017 data with standardized variables.

    Args:
        spark: Active SparkSession.
        data_path: Path to 2017 FYC file.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        Prepared 2017 DataFrame.
    """
    if input_df is not None:
        df = input_df
    else:
        columns = [
            "VARSTR", "VARPSU", "PERWT17F", "AGELAST",
            "ARTHDX", "JTPAIN31", "TOTEXP17", "TOTSLF17",
        ]
        df = load_meps_data(spark, data_path, columns)

    df = (
        df
        .withColumnRenamed("TOTEXP17", "TOTEXP")
        .withColumnRenamed("TOTSLF17", "TOTSLF")
        .withColumnRenamed("JTPAIN31", "JTPAIN")
        .withColumn("PERWTF", F.col("PERWT17F") / 2.0)
    )

    # Create SPOP and JOINT_PAIN
    df = df.withColumn("SPOP", F.lit(2))
    df = df.withColumn(
        "SPOP",
        F.when(
            (F.col("AGELAST") >= 18)
            & ~((F.col("ARTHDX") <= 0) & (F.col("JTPAIN") < 0)),
            1
        ).otherwise(F.col("SPOP"))
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


def prepare_2018(
    spark: SparkSession,
    data_path: Optional[Path] = None,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Prepare 2018 data with standardized variables.

    Args:
        spark: Active SparkSession.
        data_path: Path to 2018 FYC file.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        Prepared 2018 DataFrame.
    """
    if input_df is not None:
        df = input_df
    else:
        columns = [
            "VARSTR", "VARPSU", "PERWT18F", "AGELAST",
            "ARTHDX", "JTPAIN31_M18", "TOTEXP18", "TOTSLF18",
        ]
        df = load_meps_data(spark, data_path, columns)

    df = (
        df
        .withColumnRenamed("TOTEXP18", "TOTEXP")
        .withColumnRenamed("TOTSLF18", "TOTSLF")
        .withColumnRenamed("JTPAIN31_M18", "JTPAIN")
        .withColumn("PERWTF", F.col("PERWT18F") / 2.0)
    )

    df = df.withColumn("SPOP", F.lit(2))
    df = df.withColumn(
        "SPOP",
        F.when(
            (F.col("AGELAST") >= 18)
            & ~((F.col("ARTHDX") <= 0) & (F.col("JTPAIN") < 0)),
            1
        ).otherwise(F.col("SPOP"))
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


def pool_and_estimate(df_2017: DataFrame, df_2018: DataFrame) -> dict:
    """Pool 2017-2018 data and calculate estimates.

    Args:
        df_2017: Prepared 2017 DataFrame.
        df_2018: Prepared 2018 DataFrame.

    Returns:
        Dictionary with pooled estimates.
    """
    common_cols = list(set(df_2017.columns) & set(df_2018.columns))
    pooled = df_2017.select(common_cols).union(df_2018.select(common_cols))

    pooled = pooled.withColumn("TOTEXP_X", F.col("TOTEXP"))

    # Estimate joint pain proportion
    joint_pain_freq = survey_mean_by_domain(
        pooled,
        var_cols=["JOINT_PAIN"],
        domain_col="SPOP",
        domain_value=1,
        weight_col="PERWTF",
    )

    # Estimate expenditures by joint pain status
    exp_by_joint_pain = survey_mean_by_domain(
        pooled,
        var_cols=["TOTEXP", "TOTSLF"],
        domain_col="SPOP",
        domain_value=1,
        weight_col="PERWTF",
        by_col="JOINT_PAIN",
    )

    return {
        "pooled_data": pooled,
        "joint_pain_estimates": joint_pain_freq,
        "expenditure_estimates": exp_by_joint_pain,
    }


def run(
    spark: SparkSession,
    yr2017_path: Optional[Path] = None,
    yr2018_path: Optional[Path] = None,
    yr2017_df: Optional[DataFrame] = None,
    yr2018_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full Exercise 4c analysis pipeline.

    Args:
        spark: Active SparkSession.
        yr2017_path: Path to 2017 FYC file.
        yr2018_path: Path to 2018 FYC file.
        yr2017_df: Pre-loaded 2017 DataFrame (for testing).
        yr2018_df: Pre-loaded 2018 DataFrame (for testing).

    Returns:
        Dictionary with all analysis results.
    """
    df_2017 = prepare_2017(spark, yr2017_path, yr2017_df)
    df_2018 = prepare_2018(spark, yr2018_path, yr2018_df)
    results = pool_and_estimate(df_2017, df_2018)

    return {
        "year_2017": df_2017,
        "year_2018": df_2018,
        **results,
    }
