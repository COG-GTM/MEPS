"""Exercise 6a: Logistic Regression for Flu Shot, 2018.

Migrated from: SAS/workshop_exercises/exercise_6a/Exercise6.sas

Includes a regression example for persons receiving a flu shot:
  - Percentage of people with a flu shot (ages 18+), 2018
  - Logistic regression identifying demographic factors associated with flu shot

Input: 2018 Full-Year Consolidated file (HC-209)

SAS → PySpark Migration Notes:
  - PROC FORMAT for age, sex, race → formatting module
  - IF/THEN/ELSE for flushot recode → F.when() chains
  - PROC SURVEYMEANS DOMAIN agelast('18+') → survey_mean_by_domain()
  - PROC SURVEYLOGISTIC CLASS/MODEL → survey_logistic_regression()
"""

from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean_by_domain
from meps.utils.survey_logistic import survey_logistic_regression


def prepare_data(
    spark: SparkSession,
    data_path: Optional[Path] = None,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Read and prepare 2018 FYC data for flu shot analysis.

    Creates FLUSHOT variable from ADFLST42:
      1 → 1 (Yes), 2 → 0 (No), else → null

    Args:
        spark: Active SparkSession.
        data_path: Path to H209 data file.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        Prepared DataFrame with FLUSHOT variable.
    """
    columns = [
        "VARSTR", "VARPSU", "PERWT18F", "SAQWT18F",
        "ADFLST42", "AGELAST", "RACETHX", "POVCAT18",
        "INSCOV18", "SEX",
    ]

    if input_df is not None:
        df = input_df
    else:
        df = load_meps_data(spark, data_path, columns)

    # Recode ADFLST42 to FLUSHOT (1=Yes, 0=No, null=other)
    df = df.withColumn(
        "FLUSHOT",
        F.when(F.col("ADFLST42") == 1, 1)
        .when(F.col("ADFLST42") == 2, 0)
    )

    # Create age 18+ flag
    df = df.withColumn(
        "AGE18P",
        F.when(F.col("AGELAST") >= 18, F.lit("18+"))
        .otherwise(F.lit("0-17"))
    )

    # Add formatted labels
    df = df.withColumn(
        "SEX_LABEL",
        F.when(F.col("SEX") == 1, F.lit("Male"))
        .when(F.col("SEX") == 2, F.lit("Female"))
    )

    df = df.withColumn(
        "RACETHX_LABEL",
        F.when(F.col("RACETHX") == 1, F.lit("Hispanic"))
        .when(F.col("RACETHX") == 2, F.lit("NH White only"))
        .when(F.col("RACETHX") == 3, F.lit("NH Black only"))
        .when(F.col("RACETHX") == 4, F.lit("NH Asian only"))
        .when(F.col("RACETHX") == 5, F.lit("NH Other etc"))
    )

    df = df.withColumn(
        "INSCOV18_LABEL",
        F.when(F.col("INSCOV18") == 1, F.lit("Any Private"))
        .when(F.col("INSCOV18") == 2, F.lit("Public Only"))
        .when(F.col("INSCOV18") == 3, F.lit("Uninsured"))
    )

    return df


def estimate_flu_shot_pct(df: DataFrame) -> DataFrame:
    """Estimate percentage of adults (18+) with a flu shot.

    Replicates: PROC SURVEYMEANS DOMAIN agelast('18+');

    Args:
        df: Prepared DataFrame.

    Returns:
        DataFrame with flu shot percentage estimates.
    """
    return survey_mean_by_domain(
        df,
        var_cols=["FLUSHOT"],
        domain_col="AGE18P",
        domain_value="18+",
        weight_col="SAQWT18F",
    )


def run_logistic_regression(df: DataFrame) -> dict:
    """Run survey logistic regression for flu shot.

    Replicates: PROC SURVEYLOGISTIC
      CLASS sex(ref='Male') RACETHX(ref='Hispanic') INSCOV18(ref='Any Private')
      MODEL flushot(ref='0') = agelast sex RACETHX INSCOV18

    Args:
        df: Prepared DataFrame.

    Returns:
        Dictionary with logistic regression results.
    """
    # Filter to adults with valid flushot data
    adult_df = df.filter(
        (F.col("AGELAST") >= 18) & (F.col("FLUSHOT").isNotNull())
    )

    return survey_logistic_regression(
        adult_df,
        dependent_var="FLUSHOT",
        independent_vars=["AGELAST", "SEX", "RACETHX", "INSCOV18"],
        class_vars=["SEX", "RACETHX", "INSCOV18"],
        ref_levels={
            "SEX": "1",         # Male
            "RACETHX": "1",     # Hispanic
            "INSCOV18": "1",    # Any Private
        },
        weight_col="SAQWT18F",
    )


def run(
    spark: SparkSession,
    data_path: Optional[Path] = None,
    input_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full Exercise 6a analysis pipeline.

    Args:
        spark: Active SparkSession.
        data_path: Path to H209 data file.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        Dictionary with all analysis results.
    """
    df = prepare_data(spark, data_path, input_df)
    flu_pct = estimate_flu_shot_pct(df)
    logistic_results = run_logistic_regression(df)

    return {
        "prepared_data": df,
        "flu_shot_percentage": flu_pct,
        "logistic_regression": logistic_results,
    }
