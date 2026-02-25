"""Exercise 1c: National Health Care Expenses, 2018.

Migrated from: SAS/workshop_exercises/exercise_1c/Exercise1c.sas

Generates estimates on national health care expenses, 2018:
  (1) Percentage of persons with an expense (3 methods)
  (2) Mean and median expense per person with an expense
  (3) Mean/median expense by age group (0-64, 65+)

Input: 2018 Full-Year Consolidated file (HC-209)

SAS → PySpark Migration Notes:
  - PROC FORMAT VALUE AGECAT   → F.when() chains
  - PROC FORMAT VALUE totexp18 → flag_format()
  - PROC SURVEYMEANS CLASS     → survey_freq()
  - PROC SURVEYFREQ            → survey_freq()
  - DOMAIN WITH_AN_EXPENSE('Any Expense')*AGELAST → survey_mean_by_domain()
"""

from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean, survey_mean_by_domain, survey_freq


def prepare_data(
    spark: SparkSession,
    data_path: Optional[Path] = None,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Read and prepare the 2018 FYC data for analysis.

    Args:
        spark: Active SparkSession.
        data_path: Path to H209 data file.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        Prepared DataFrame with derived variables.
    """
    if input_df is not None:
        df = input_df
    else:
        columns = [
            "TOTEXP18", "AGELAST", "VARSTR", "VARPSU", "PERWT18F", "PANEL",
        ]
        df = load_meps_data(spark, data_path, columns)

    # Create WITH_AN_EXPENSE variable
    df = df.withColumn("WITH_AN_EXPENSE", F.col("TOTEXP18"))

    # Create character version of expense flag
    df = df.withColumn(
        "CHAR_WITH_AN_EXPENSE",
        F.when(F.col("TOTEXP18") == 0, F.lit("No Expense"))
        .otherwise(F.lit("Any Expense"))
    )

    # Create age category
    df = df.withColumn(
        "AGECAT",
        F.when(F.col("AGELAST") <= 64, F.lit("0-64"))
        .otherwise(F.lit("65+"))
    )

    return df


def estimate_pct_with_expense_method1(df: DataFrame) -> DataFrame:
    """Method 1: PROC SURVEYMEANS with CLASS on WITH_AN_EXPENSE.

    Args:
        df: Prepared DataFrame.

    Returns:
        DataFrame with class-level survey means.
    """
    return survey_freq(
        df,
        var_col="CHAR_WITH_AN_EXPENSE",
        weight_col="PERWT18F",
    )


def estimate_pct_with_expense_method2(df: DataFrame) -> DataFrame:
    """Method 2: PROC SURVEYMEANS on CHAR_WITH_AN_EXPENSE.

    Args:
        df: Prepared DataFrame.

    Returns:
        DataFrame with survey means for character expense variable.
    """
    return survey_freq(
        df,
        var_col="CHAR_WITH_AN_EXPENSE",
        weight_col="PERWT18F",
    )


def estimate_pct_with_expense_method3(df: DataFrame) -> DataFrame:
    """Method 3: PROC SURVEYFREQ on CHAR_WITH_AN_EXPENSE.

    Args:
        df: Prepared DataFrame.

    Returns:
        DataFrame with survey frequency estimates.
    """
    return survey_freq(
        df,
        var_col="CHAR_WITH_AN_EXPENSE",
        weight_col="PERWT18F",
    )


def estimate_mean_median_by_age(df: DataFrame) -> tuple:
    """Estimate mean and median expense per person with expense, by age.

    Replicates PROC SURVEYMEANS with DOMAIN
    WITH_AN_EXPENSE('Any Expense') and
    WITH_AN_EXPENSE('Any Expense')*AGELAST.

    Args:
        df: Prepared DataFrame.

    Returns:
        Tuple of (overall estimates, by-age estimates).
    """
    overall = survey_mean_by_domain(
        df,
        var_cols=["TOTEXP18"],
        domain_col="CHAR_WITH_AN_EXPENSE",
        domain_value="Any Expense",
        weight_col="PERWT18F",
    )

    by_age = survey_mean_by_domain(
        df,
        var_cols=["TOTEXP18"],
        domain_col="CHAR_WITH_AN_EXPENSE",
        domain_value="Any Expense",
        weight_col="PERWT18F",
        by_col="AGECAT",
    )

    return overall, by_age


def run(
    spark: SparkSession,
    data_path: Optional[Path] = None,
    input_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full Exercise 1c analysis pipeline.

    Args:
        spark: Active SparkSession.
        data_path: Path to H209 data file.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        Dictionary with all analysis results.
    """
    df = prepare_data(spark, data_path, input_df)
    method1 = estimate_pct_with_expense_method1(df)
    method2 = estimate_pct_with_expense_method2(df)
    method3 = estimate_pct_with_expense_method3(df)
    overall, by_age = estimate_mean_median_by_age(df)

    return {
        "prepared_data": df,
        "pct_expense_method1": method1,
        "pct_expense_method2": method2,
        "pct_expense_method3": method3,
        "mean_expense_overall": overall,
        "mean_expense_by_age": by_age,
    }
