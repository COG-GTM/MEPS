"""Exercise 3b: Expenditures for Events Associated with Diabetes, 2015.

Migrated from: SAS/workshop_exercises/exercise_3b/Exercise3b.sas

Illustrates how to calculate expenditures for ALL events associated
with a condition (diabetes), including:
  - Link conditions to events via condition-event link file
  - Standardize expenditure variables across event types
  - Calculate total and by-service-type expenditures

Input files:
  - 2015 FY PUF (HC-181)
  - 2015 Condition PUF (HC-180)
  - 2015 PMED PUF (HC-178A)
  - 2015 Inpatient Visits PUF (HC-178D)
  - 2015 ER Visits PUF (HC-178E)
  - 2015 Outpatient Visits PUF (HC-178F)
  - 2015 Office-Based Visits PUF (HC-178G)
  - 2015 Home Health PUF (HC-178H)
  - 2015 Condition-Event Link PUF (HC-178IF1)

SAS → PySpark Migration Notes:
  - Multiple DATA steps with event alignment → standardize_event_expenses()
  - SET with IN= flags for event type       → union with EVNTYP column
  - MERGE with condition-event link          → join chains
  - PROC SUMMARY NWAY by DUPERSID           → groupBy().agg()
  - PROC SURVEYMEANS DOMAIN SUB('1')        → survey_mean_by_domain()
"""

from pathlib import Path
from typing import Dict, Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean_by_domain


# Standard payment source columns
PAYMENT_COLS = ["SF", "MR", "MD", "PV", "VA", "TR", "OF", "SL", "WC", "OR_PAY", "OU", "OT"]
ALL_EXP_COLS = PAYMENT_COLS + ["TOTEXP"]


def identify_diabetes_events(
    spark: SparkSession,
    cond_df: Optional[DataFrame] = None,
    clnk_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Get event IDs for diabetic conditions via condition-event link.

    Steps:
      1. Filter conditions to diabetes (CCS 049/050)
      2. Merge with condition-event link file
      3. De-duplicate by EVNTIDX

    Args:
        spark: Active SparkSession.
        cond_df: Conditions DataFrame with CCCODEX column.
        clnk_df: Condition-event link DataFrame.

    Returns:
        DataFrame with unique DUPERSID, EVNTIDX for diabetes events.
    """
    diab = cond_df.filter(F.col("CCCODEX").isin("049", "050"))

    # Merge with condition-event link (join on both DUPERSID and CONDIDX
    # to avoid cross-person linkage since CONDIDX is not globally unique)
    diab_events = diab.select("DUPERSID", "CONDIDX", "CCCODEX").join(
        clnk_df.select("DUPERSID", "CONDIDX", "EVNTIDX"),
        on=["DUPERSID", "CONDIDX"],
        how="inner",
    )

    # De-duplicate by DUPERSID + EVNTIDX
    return diab_events.select("DUPERSID", "EVNTIDX").dropDuplicates(["DUPERSID", "EVNTIDX"])


def standardize_event_expenses(
    event_df: DataFrame,
    event_type: str,
    col_mapping: Dict[str, str],
) -> DataFrame:
    """Standardize expense column names across event types.

    Each event type (OB, ER, IP, OP, HH, RX) has different column
    naming conventions. This function renames them to a common schema.

    Args:
        event_df: Event-type DataFrame.
        event_type: Event type code (AMBU, EROM, IPAT, HVIS, PMED).
        col_mapping: Dictionary mapping standard names to source column names.

    Returns:
        DataFrame with standardized columns + EVNTYP.
    """
    result = event_df
    for std_name, src_name in col_mapping.items():
        if src_name in event_df.columns:
            result = result.withColumn(std_name, F.col(src_name))
        elif "+" in src_name:
            # Handle sum of two columns (e.g., facility + doctor)
            parts = [p.strip() for p in src_name.split("+")]
            result = result.withColumn(
                std_name,
                sum(F.col(p) for p in parts if p in event_df.columns)
            )

    result = result.withColumn("EVNTYP", F.lit(event_type))

    keep_cols = ["EVNTIDX", "EVNTYP"] + ALL_EXP_COLS
    available = [c for c in keep_cols if c in result.columns]
    return result.select(available)


def combine_all_events(event_dfs: list) -> DataFrame:
    """Combine all event type DataFrames into one.

    Args:
        event_dfs: List of standardized event DataFrames.

    Returns:
        Combined DataFrame with all events.
    """
    result = event_dfs[0]
    for df in event_dfs[1:]:
        result = result.unionByName(df, allowMissingColumns=True)
    return result


def calculate_person_level_expenses(
    diab_events_df: DataFrame,
    all_events_df: DataFrame,
) -> DataFrame:
    """Subset events to diabetes and sum to person level.

    Args:
        diab_events_df: Unique diabetes event IDs.
        all_events_df: All events combined.

    Returns:
        Person-level DataFrame with total expenditures for diabetes events.
    """
    # Subset to diabetes events
    diab_exp = diab_events_df.join(
        all_events_df,
        on="EVNTIDX",
        how="inner",
    )

    # Sum to person level
    agg_cols = [F.sum(c).alias(c) for c in ALL_EXP_COLS if c in diab_exp.columns]

    return diab_exp.groupBy("DUPERSID").agg(*agg_cols)


def merge_to_fyc_and_estimate(
    spark: SparkSession,
    person_exp_df: DataFrame,
    fyc_df: DataFrame,
) -> DataFrame:
    """Merge person-level expenses to FYC and run survey estimates.

    Args:
        spark: Active SparkSession.
        person_exp_df: Person-level diabetes expenditures.
        fyc_df: Full-year consolidated DataFrame.

    Returns:
        DataFrame with domain estimates for diabetes events.
    """
    fyc_cols = ["DUPERSID", "VARPSU", "VARSTR", "PERWT15F"]
    fy = fyc_df.select([c for c in fyc_cols if c in fyc_df.columns])

    merged = fy.join(person_exp_df, on="DUPERSID", how="left")

    # Set SUB flag and fill nulls
    merged = merged.withColumn(
        "SUB",
        F.when(F.col("TOTEXP").isNotNull(), 1).otherwise(2)
    )

    fill_cols = [c for c in ALL_EXP_COLS if c in merged.columns]
    merged = merged.fillna(0, subset=fill_cols)

    # Filter to positive weights
    merged = merged.filter(F.col("PERWT15F") > 0)

    var_cols = [c for c in ALL_EXP_COLS if c in merged.columns]
    return survey_mean_by_domain(
        merged,
        var_cols=var_cols,
        domain_col="SUB",
        domain_value=1,
        weight_col="PERWT15F",
    )


def run(
    spark: SparkSession,
    fyc_df: Optional[DataFrame] = None,
    cond_df: Optional[DataFrame] = None,
    clnk_df: Optional[DataFrame] = None,
    event_dfs: Optional[Dict[str, DataFrame]] = None,
) -> dict:
    """Execute the full Exercise 3b analysis pipeline.

    Args:
        spark: Active SparkSession.
        fyc_df: Full-year consolidated DataFrame.
        cond_df: Conditions DataFrame.
        clnk_df: Condition-event link DataFrame.
        event_dfs: Dict of event type DataFrames keyed by type name.

    Returns:
        Dictionary with all analysis results.
    """
    diab_events = identify_diabetes_events(spark, cond_df, clnk_df)

    if event_dfs is not None:
        all_events = combine_all_events(list(event_dfs.values()))
    else:
        all_events = spark.createDataFrame([], "EVNTIDX STRING")

    person_exp = calculate_person_level_expenses(diab_events, all_events)
    estimates = merge_to_fyc_and_estimate(spark, person_exp, fyc_df)

    return {
        "diabetes_events": diab_events,
        "person_level_expenses": person_exp,
        "estimates": estimates,
    }
