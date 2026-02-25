"""Exercise 1b: National Health Care Expenses by Type of Service, 2015.

Migrated from: SAS/workshop_exercises/exercise_1b/Exercise1b.sas

Generates estimates on national health care expenses by type of service, 2015:
  (1) Percentage distribution of expenses by type of service
  (2) Percentage of persons with an expense, by type of service
  (3) Mean expense per person with an expense, by type of service

Service categories:
  - Hospital Inpatient
  - Ambulatory (Office-Based + Hospital Outpatient + ER)
  - Prescribed Medicines
  - Dental
  - Home Health/Other

Input: 2015 Full-Year Consolidated file (HC-181)
"""

from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean, survey_mean_by_domain


SERVICE_TYPES = [
    "HOSPITAL_INPATIENT",
    "AMBULATORY",
    "PRESCRIBED_MEDICINES",
    "DENTAL",
    "HOME_HEALTH_OTHER",
]


def prepare_data(
    spark: SparkSession,
    data_path: Optional[Path] = None,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Read and prepare the 2015 FYC data with expenditure type variables.

    Replicates the SAS DATA step that defines expenditure variables by
    type of service and creates binary flag variables.

    Args:
        spark: Active SparkSession.
        data_path: Path to H181 data file.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        Prepared DataFrame with service-type expenditure variables.
    """
    if input_df is not None:
        df = input_df
    else:
        columns = [
            "TOTEXP15", "IPDEXP15", "IPFEXP15", "OBVEXP15", "RXEXP15",
            "OPDEXP15", "OPFEXP15", "DVTEXP15", "ERDEXP15", "ERFEXP15",
            "HHAEXP15", "HHNEXP15", "OTHEXP15", "VISEXP15",
            "AGE15X", "AGE42X", "AGE31X",
            "VARSTR", "VARPSU", "PERWT15F",
        ]
        df = load_meps_data(spark, data_path, columns)

    # Define expenditure variables by type of service
    df = (
        df
        .withColumn("TOTAL", F.col("TOTEXP15"))
        .withColumn(
            "HOSPITAL_INPATIENT",
            F.col("IPDEXP15") + F.col("IPFEXP15")
        )
        .withColumn(
            "AMBULATORY",
            F.col("OBVEXP15") + F.col("OPDEXP15") + F.col("OPFEXP15")
            + F.col("ERDEXP15") + F.col("ERFEXP15")
        )
        .withColumn("PRESCRIBED_MEDICINES", F.col("RXEXP15"))
        .withColumn("DENTAL", F.col("DVTEXP15"))
        .withColumn(
            "HOME_HEALTH_OTHER",
            F.col("HHAEXP15") + F.col("HHNEXP15")
            + F.col("OTHEXP15") + F.col("VISEXP15")
        )
    )

    # QC: verify sum of components equals total
    df = df.withColumn(
        "DIFF",
        F.col("TOTAL") - F.col("HOSPITAL_INPATIENT") - F.col("AMBULATORY")
        - F.col("PRESCRIBED_MEDICINES") - F.col("DENTAL")
        - F.col("HOME_HEALTH_OTHER")
    )

    # Create flag variables for persons with expense by type
    all_types = ["TOTAL"] + SERVICE_TYPES
    for svc in all_types:
        flag_col = f"X_{svc}" if svc != "TOTAL" else "X_ANYSVCE"
        df = df.withColumn(
            flag_col,
            F.when(F.col(svc) > 0, 1).otherwise(0)
        )

    # Create age category
    df = df.withColumn(
        "AGE",
        F.when(F.col("AGE15X") >= 0, F.col("AGE15X"))
        .when(F.col("AGE42X") >= 0, F.col("AGE42X"))
        .when(F.col("AGE31X") >= 0, F.col("AGE31X"))
    )
    df = df.withColumn(
        "AGECAT",
        F.when((F.col("AGE") >= 0) & (F.col("AGE") <= 64), 1)
        .when(F.col("AGE") > 64, 2)
    )
    df = df.withColumn(
        "AGECAT_LABEL",
        F.when(F.col("AGECAT") == 1, F.lit("0-64"))
        .when(F.col("AGECAT") == 2, F.lit("65+"))
        .otherwise(F.lit("All Ages"))
    )

    return df


def estimate_expense_distribution(df: DataFrame) -> DataFrame:
    """Estimate percentage distribution of expenses by type of service.

    Replicates PROC SURVEYMEANS with RATIO option for computing
    the proportion of total expenses attributed to each service type.

    Args:
        df: Prepared DataFrame.

    Returns:
        DataFrame with expense distribution estimates.
    """
    all_vars = SERVICE_TYPES + ["TOTAL"]
    return survey_mean(
        df,
        var_cols=all_vars,
        weight_col="PERWT15F",
    )


def estimate_pct_with_expense(df: DataFrame) -> DataFrame:
    """Estimate percentage of persons with an expense by type of service.

    Args:
        df: Prepared DataFrame.

    Returns:
        DataFrame with percentage estimates by service type.
    """
    flag_vars = ["X_ANYSVCE"] + [f"X_{svc}" for svc in SERVICE_TYPES]
    return survey_mean(
        df,
        var_cols=flag_vars,
        weight_col="PERWT15F",
    )


def estimate_mean_expense_by_service(df: DataFrame) -> dict:
    """Estimate mean expense per person with expense, by service and age.

    Replicates the multiple PROC SURVEYMEANS with DOMAIN statements
    for each service type crossed with age category.

    Args:
        df: Prepared DataFrame.

    Returns:
        Dictionary mapping service type to domain estimates.
    """
    results = {}

    # Total expense by age group
    results["TOTAL"] = survey_mean_by_domain(
        df,
        var_cols=["TOTAL"],
        domain_col="X_ANYSVCE",
        domain_value=1,
        weight_col="PERWT15F",
        by_col="AGECAT",
    )

    # Each service type by age group
    for svc in SERVICE_TYPES:
        flag_col = f"X_{svc}"
        results[svc] = survey_mean_by_domain(
            df,
            var_cols=[svc],
            domain_col=flag_col,
            domain_value=1,
            weight_col="PERWT15F",
            by_col="AGECAT",
        )

    return results


def run(
    spark: SparkSession,
    data_path: Optional[Path] = None,
    input_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full Exercise 1b analysis pipeline.

    Args:
        spark: Active SparkSession.
        data_path: Path to H181 data file.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        Dictionary with all analysis results.
    """
    df = prepare_data(spark, data_path, input_df)

    return {
        "prepared_data": df,
        "expense_distribution": estimate_expense_distribution(df),
        "pct_with_expense": estimate_pct_with_expense(df),
        "mean_expense_by_service": estimate_mean_expense_by_service(df),
    }
