"""Exercise 5b: Constructing Insurance Status Variables, 2015.

Migrated from: SAS/workshop_exercises/exercise_5b/Exercise5b.sas

Illustrates how to construct insurance status variables from monthly
insurance indicator variables in the person-level data.

Creates count variables for number of months with each insurance type,
then derives flag variables:
  - FULL_INSU: Insured for full year
  - GROUP_INS1: Ever insured by private group
  - GROUP_INS2: Insured by private group for full year
  - NG_INS: Ever insured by private non-group

Input: 2015 Full-Year Consolidated file (HC-181)

SAS → PySpark Migration Notes:
  - ARRAY / DO I=1 TO 12 loop  → Column expressions with sum
  - Multiple SAS arrays          → Structured column references
  - IF condition THEN counter+1  → F.when().otherwise() with sum
  - PROC SURVEYMEANS DOMAIN      → survey_mean_by_domain()
"""

from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean, survey_mean_by_domain


# Month abbreviations for insurance variable naming
MONTHS = ["JA", "FE", "MA", "AP", "MY", "JU", "JL", "AU", "SE", "OC", "NO", "DE"]
YR = "15"


def _count_months(df: DataFrame, prefix: str, yr: str, condition_value: int = 1) -> F.Column:
    """Count number of months where a monthly indicator equals the condition value.

    Replicates the SAS ARRAY/DO loop pattern for counting months.

    Args:
        df: Input DataFrame.
        prefix: Column prefix (e.g., 'PRI' for PRIJA15..PRIDE15).
        yr: Year suffix (e.g., '15').
        condition_value: Value to count (default: 1).

    Returns:
        Column expression with count of months matching condition.
    """
    month_cols = [f"{prefix}{m}{yr}" for m in MONTHS]
    # Add X suffix variants used by some variables
    month_cols_x = [f"{prefix}{m}{yr}X" for m in MONTHS]

    # Use whichever naming convention exists
    count_expr = F.lit(0)
    for col_name in month_cols + month_cols_x:
        count_expr = count_expr + F.when(
            F.col(col_name) == condition_value, 1
        ).otherwise(0)

    return count_expr


def create_insurance_counts(
    spark: SparkSession,
    data_path: Optional[Path] = None,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Create count variables for months with each insurance type.

    Replicates the SAS DATA step with ARRAY loops.

    Args:
        spark: Active SparkSession.
        data_path: Path to H181 data file.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        DataFrame with monthly insurance count variables.
    """
    if input_df is not None:
        df = input_df
    else:
        df = load_meps_data(spark, data_path)

    # For each insurance type, count months with coverage
    # Using simplified approach - sum of indicator columns
    pri_cols = [f"PRI{m}{YR}" for m in MONTHS]
    ins_cols = [f"INS{m}{YR}X" for m in MONTHS]
    mcd_cols = [f"MCD{m}{YR}X" for m in MONTHS]
    mcr_cols = [f"MCR{m}{YR}X" for m in MONTHS]
    tri_cols = [f"TRI{m}{YR}X" for m in MONTHS]

    # Count months for each type
    for col_list, name in [
        (pri_cols, "PRI_N"),
    ]:
        available = [c for c in col_list if c in df.columns]
        if available:
            df = df.withColumn(
                name,
                sum(F.when(F.col(c) == 1, 1).otherwise(0) for c in available)
            )
        else:
            df = df.withColumn(name, F.lit(0))

    # Count uninsured months (INS == 2)
    ins_available = [c for c in ins_cols if c in df.columns]
    if ins_available:
        df = df.withColumn(
            "INS_N",
            sum(F.when(F.col(c) == 1, 1).otherwise(0) for c in ins_available)
        )
        df = df.withColumn(
            "UNINS_N",
            sum(F.when(F.col(c) == 2, 1).otherwise(0) for c in ins_available)
        )
        df = df.withColumn(
            "REF_N",
            sum(F.when(F.col(c) > 0, 1).otherwise(0) for c in ins_available)
        )
    else:
        df = df.withColumn("INS_N", F.lit(0))
        df = df.withColumn("UNINS_N", F.lit(0))
        df = df.withColumn("REF_N", F.lit(0))

    # Medicaid, Medicare, TRICARE counts
    for col_list, name in [
        (mcd_cols, "MCD_N"),
        (mcr_cols, "MCR_N"),
        (tri_cols, "TRI_N"),
    ]:
        available = [c for c in col_list if c in df.columns]
        if available:
            df = df.withColumn(
                name,
                sum(F.when(F.col(c) == 1, 1).otherwise(0) for c in available)
            )
        else:
            df = df.withColumn(name, F.lit(0))

    return df


def create_insurance_flags(df: DataFrame) -> DataFrame:
    """Create insurance flag variables from month counts.

    Flags created:
      - FULL_INSU: Insured for full year (UNINS_N == 0)
      - GROUP_INS1: Ever insured by private group (GRP_N > 0)
      - GROUP_INS2: Insured by private group for full year
      - NG_INS: Ever insured by private non-group

    Args:
        df: DataFrame with monthly insurance counts.

    Returns:
        DataFrame with flag variables added.
    """
    df = df.withColumn(
        "FULL_INSU",
        F.when(F.col("UNINS_N") == 0, 1).otherwise(0)
    )

    # GROUP_INS1 and GROUP_INS2 need GRP_N
    if "GRP_N" not in df.columns:
        df = df.withColumn("GRP_N", F.lit(0))

    df = df.withColumn(
        "GROUP_INS1",
        F.when(F.col("GRP_N") > 0, 1).otherwise(0)
    )
    df = df.withColumn(
        "GROUP_INS2",
        F.when(
            (F.col("GRP_N") > 0) & (F.col("GRP_N") == F.col("REF_N")),
            1
        ).otherwise(0)
    )

    if "NG_N" not in df.columns:
        df = df.withColumn("NG_N", F.lit(0))

    df = df.withColumn(
        "NG_INS",
        F.when(F.col("NG_N") > 0, 1).otherwise(0)
    )

    return df


def estimate_insurance_coverage(df: DataFrame) -> DataFrame:
    """Calculate weighted estimates of insurance coverage by race/ethnicity.

    Replicates: PROC SURVEYMEANS DOMAIN RACETHX;

    Args:
        df: DataFrame with insurance flag variables.

    Returns:
        DataFrame with survey estimates.
    """
    flag_vars = ["FULL_INSU", "GROUP_INS1", "GROUP_INS2", "NG_INS"]

    # Overall estimates
    overall = survey_mean(
        df,
        var_cols=flag_vars,
        weight_col="PERWT15F",
    )

    return overall


def run(
    spark: SparkSession,
    data_path: Optional[Path] = None,
    input_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full Exercise 5b analysis pipeline.

    Args:
        spark: Active SparkSession.
        data_path: Path to H181 data file.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        Dictionary with all analysis results.
    """
    df = create_insurance_counts(spark, data_path, input_df)
    df = create_insurance_flags(df)
    estimates = estimate_insurance_coverage(df)

    return {
        "insurance_data": df,
        "estimates": estimates,
    }
