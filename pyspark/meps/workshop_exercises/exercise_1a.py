"""Exercise 1a: National Health Care Expenses, 2016.

Migrated from: SAS/workshop_exercises/exercise_1a/Exercise1a.sas

Generates the following estimates on national health care expenses, 2016:
  (1) Overall expenses
  (2) Percentage of persons with an expense
  (3) Mean expense per person with an expense

Input: 2016 Full-Year Consolidated file (HC-192)

SAS → PySpark Migration Notes:
  - DATA step with SET/KEEP → load_meps_data() with column selection
  - PROC FORMAT VALUE       → formatting.age_category(), formatting.flag_format()
  - IF/THEN/ELSE age logic  → F.when().otherwise() chains
  - PROC SURVEYMEANS         → survey_stats.survey_mean()
  - DOMAIN statement         → survey_stats.survey_mean_by_domain()
  - PROC FREQ crosstab       → survey_stats.crosstab()
"""

from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.formatting import age_category, flag_format, gt_zero_format
from meps.utils.survey_stats import survey_mean, survey_mean_by_domain, crosstab


def prepare_data(
    spark: SparkSession,
    data_path: Optional[Path] = None,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Read and prepare the 2016 FYC data for analysis.

    Replicates the SAS DATA step that reads HC-192 and creates
    derived variables (TOTAL, X_ANYSVCE, AGE, AGECAT).

    Args:
        spark: Active SparkSession.
        data_path: Path to H192 data file. Used if input_df is None.
        input_df: Pre-loaded DataFrame. If provided, data_path is ignored.

    Returns:
        Prepared DataFrame with derived variables.
    """
    columns = [
        "TOTEXP16", "AGE16X", "AGE42X", "AGE31X",
        "VARSTR", "VARPSU", "PERWT16F",
    ]

    if input_df is not None:
        df = input_df
    else:
        df = load_meps_data(spark, data_path, columns)

    # Create TOTAL variable
    df = df.withColumn("TOTAL", F.col("TOTEXP16"))

    # Create flag for persons with an expense (X_ANYSVCE)
    df = df.withColumn(
        "X_ANYSVCE",
        F.when(F.col("TOTAL") > 0, 1).otherwise(0)
    )

    # Create summary AGE variable from end-of-year, round 4/2, round 3/1
    df = df.withColumn(
        "AGE",
        F.when(F.col("AGE16X") >= 0, F.col("AGE16X"))
        .when(F.col("AGE42X") >= 0, F.col("AGE42X"))
        .when(F.col("AGE31X") >= 0, F.col("AGE31X"))
    )

    # Create age category
    df = df.withColumn(
        "AGECAT",
        F.when((F.col("AGE") >= 0) & (F.col("AGE") <= 64), 1)
        .when(F.col("AGE") > 64, 2)
    )

    # Add formatted labels
    df = df.withColumn(
        "AGECAT_LABEL",
        F.when(F.col("AGECAT") == 1, F.lit("0-64"))
        .when(F.col("AGECAT") == 2, F.lit("65+"))
        .otherwise(F.lit("ALL AGES"))
    )

    return df


def run_crosstabs(df: DataFrame) -> dict:
    """Run supporting crosstabs for flag variables.

    Replicates the SAS PROC FREQ step for QC verification.

    Args:
        df: Prepared DataFrame from prepare_data().

    Returns:
        Dictionary with crosstab DataFrames.
    """
    expense_xtab = crosstab(df, "X_ANYSVCE", "TOTAL")
    age_xtab = crosstab(df, "AGECAT", "AGE")

    return {
        "expense_crosstab": expense_xtab,
        "age_crosstab": age_xtab,
    }


def estimate_overall(df: DataFrame) -> DataFrame:
    """Estimate percentage with expense and overall expenses.

    Replicates the first PROC SURVEYMEANS: overall weighted means
    for X_ANYSVCE (proportion with expense) and TOTAL (mean expense).

    Args:
        df: Prepared DataFrame from prepare_data().

    Returns:
        DataFrame with overall estimates.
    """
    return survey_mean(
        df,
        var_cols=["X_ANYSVCE", "TOTAL"],
        weight_col="PERWT16F",
        stratum_col="VARSTR",
        cluster_col="VARPSU",
    )


def estimate_by_age_group(df: DataFrame) -> DataFrame:
    """Estimate mean expense per person with expense, by age group.

    Replicates the second PROC SURVEYMEANS with DOMAIN statement:
    X_ANYSVCE('1') and X_ANYSVCE('1')*AGECAT.

    Args:
        df: Prepared DataFrame from prepare_data().

    Returns:
        DataFrame with domain estimates by age group.
    """
    # Overall for persons with expense
    overall = survey_mean_by_domain(
        df,
        var_cols=["TOTAL"],
        domain_col="X_ANYSVCE",
        domain_value=1,
        weight_col="PERWT16F",
    )

    # By age category for persons with expense
    by_age = survey_mean_by_domain(
        df,
        var_cols=["TOTAL"],
        domain_col="X_ANYSVCE",
        domain_value=1,
        weight_col="PERWT16F",
        by_col="AGECAT",
    )

    return overall, by_age


def run(
    spark: SparkSession,
    data_path: Optional[Path] = None,
    input_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full Exercise 1a analysis pipeline.

    Args:
        spark: Active SparkSession.
        data_path: Path to H192 data file.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        Dictionary with all analysis results.
    """
    df = prepare_data(spark, data_path, input_df)
    crosstabs = run_crosstabs(df)
    overall = estimate_overall(df)
    by_age_overall, by_age_detail = estimate_by_age_group(df)

    return {
        "prepared_data": df,
        "crosstabs": crosstabs,
        "overall_estimates": overall,
        "by_age_overall": by_age_overall,
        "by_age_detail": by_age_detail,
    }
