"""Summary Table: Use, Expenditures, and Population, 2016.

Migrated from: SAS/summary_tables_examples/use_expenditures_2016.sas

Expenditures by event type and source of payment (SOP):
  - Total expenditures
  - Mean expenditure per person
  - Mean out-of-pocket payment per person with an out-of-pocket expense

Selected event types: OBV, OBD, OPT, OPV (office-based and outpatient).

Input: 2016 Full-Year Consolidated file (HC-192)
"""

from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean, survey_mean_by_domain


EVENT_TYPES = {
    "OBV": "Office-based visits",
    "OBD": "Office-based physician visits",
    "OPT": "Outpatient visits",
    "OPp": "Outpatient physician visits",
}

SOP_LABELS = {
    "SLF": "Out-of-pocket",
    "PTR": "Private",
    "MCR": "Medicare",
    "MCD": "Medicaid",
    "OTZ": "Other",
}


def prepare_data(
    spark: SparkSession,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Prepare FYC data with aggregated payment source variables.

    Creates PTR (Private + TRICARE) and OTZ (Other) payment aggregates
    for each event type.

    Args:
        spark: Active SparkSession.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        DataFrame with aggregated payment variables and domain flags.
    """
    df = input_df

    # Office-based visits aggregates
    if "OBVPRV16" in df.columns:
        df = df.withColumn("OBVPTR", F.col("OBVPRV16") + F.col("OBVTRI16"))
    if "OBVOFD16" in df.columns:
        df = df.withColumn(
            "OBVOTZ",
            F.col("OBVOFD16") + F.col("OBVSTL16") + F.col("OBVOPR16")
            + F.col("OBVOPU16") + F.col("OBVOSR16") + F.col("OBVWCP16")
            + F.col("OBVVA16")
        )

    # Office-based physician aggregates
    if "OBDPRV16" in df.columns:
        df = df.withColumn("OBDPTR", F.col("OBDPRV16") + F.col("OBDTRI16"))
    if "OBDOFD16" in df.columns:
        df = df.withColumn(
            "OBDOTZ",
            F.col("OBDOFD16") + F.col("OBDSTL16") + F.col("OBDOPR16")
            + F.col("OBDOPU16") + F.col("OBDOSR16") + F.col("OBDWCP16")
            + F.col("OBDVA16")
        )

    # Outpatient visit aggregates
    if "OPTPRV16" in df.columns:
        df = df.withColumn("OPTPTR", F.col("OPTPRV16") + F.col("OPTTRI16"))
    if "OPTOFD16" in df.columns:
        df = df.withColumn(
            "OPTOTZ",
            F.col("OPTOFD16") + F.col("OPTSTL16") + F.col("OPTOPR16")
            + F.col("OPTOPU16") + F.col("OPTOSR16") + F.col("OPTWCP16")
            + F.col("OPTVA16")
        )

    # Domain flags for persons with OOP expense
    for prefix in ["OBV", "OBD", "OPT"]:
        slf_col = f"{prefix}SLF16"
        if slf_col in df.columns:
            df = df.withColumn(
                f"HAS_{prefix}SLF",
                F.when(F.col(slf_col) > 0, 1).otherwise(0)
            )

    return df


def estimate_total_and_mean(df: DataFrame) -> DataFrame:
    """Calculate total expenditures and mean per person by event/SOP.

    Args:
        df: Prepared DataFrame.

    Returns:
        DataFrame with survey estimates.
    """
    var_cols = []
    for col_name in df.columns:
        if any(col_name.startswith(prefix) for prefix in ["OBV", "OBD", "OPT", "OPp"]):
            if col_name.endswith(("SLF16", "PTR", "MCR16", "MCD16", "OTZ")):
                var_cols.append(col_name)

    if not var_cols:
        var_cols = ["OBVSLF16"]

    return survey_mean(df, var_cols=var_cols, weight_col="PERWT16F")


def run(
    spark: SparkSession,
    input_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full analysis pipeline.

    Args:
        spark: Active SparkSession.
        input_df: Pre-loaded DataFrame (for testing).

    Returns:
        Dictionary with all analysis results.
    """
    df = prepare_data(spark, input_df)
    estimates = estimate_total_and_mean(df)

    return {
        "prepared_data": df,
        "estimates": estimates,
    }
