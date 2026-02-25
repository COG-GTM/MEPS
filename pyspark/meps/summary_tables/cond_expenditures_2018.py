"""Summary Table: Medical Conditions Expenditures, 2018.

Migrated from: SAS/summary_tables_examples/cond_expenditures_2018.sas

Medical Conditions, 2018 (uses CCSR codes, post-2016):
  - Number of people with care
  - Number of events
  - Total expenditures
  - Mean expenditure per person

Input files:
  - 2018 event files (RX, IP, ER, OP, OB, HH)
  - 2018 CLNK file
  - 2018 Conditions file
  - CCSR crosswalk file
"""

from typing import Dict, Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.survey_stats import survey_mean
from meps.summary_tables.cond_expenditures_2015 import stack_events


def link_conditions_ccsr(
    stacked_df: DataFrame,
    clnk_df: DataFrame,
    cond_df: DataFrame,
    ccsr_xwalk_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Link conditions to events via CLNK using CCSR codes.

    For 2016+, conditions use CCSR codes instead of CCS codes.
    Transposes wide CCSR columns to long format before linking.

    Args:
        stacked_df: Stacked events DataFrame.
        clnk_df: Condition-event link DataFrame.
        cond_df: Conditions DataFrame with CCSR columns.
        ccsr_xwalk_df: CCSR-to-condition crosswalk (optional).

    Returns:
        Events linked to condition categories.
    """
    # Merge conditions with CLNK
    ccsr_cols = [c for c in cond_df.columns if c.startswith("CCSR")]
    cond_clnk = clnk_df.select("DUPERSID", "CONDIDX", "EVNTIDX").join(
        cond_df.select("DUPERSID", "CONDIDX", *ccsr_cols),
        on=["DUPERSID", "CONDIDX"],
        how="inner",
    )

    # Transpose CCSR columns to long format
    ccsr_long_parts = []
    for ccsr_col in ccsr_cols:
        part = cond_clnk.select(
            "DUPERSID", "CONDIDX", "EVNTIDX",
            F.col(ccsr_col).alias("CCSR"),
        ).filter(F.col("CCSR").isNotNull() & (F.col("CCSR") != "-1"))
        ccsr_long_parts.append(part)

    if ccsr_long_parts:
        cond_long = ccsr_long_parts[0]
        for part in ccsr_long_parts[1:]:
            cond_long = cond_long.union(part)
    else:
        return stacked_df.limit(0)

    # If crosswalk is provided, merge on condition labels
    if ccsr_xwalk_df is not None:
        cond_long = cond_long.join(ccsr_xwalk_df, on="CCSR", how="left")
        cond_long = cond_long.filter(F.col("Condition").isNotNull())

    # De-duplicate
    cond_long = cond_long.dropDuplicates(["DUPERSID", "EVNTIDX", "CCSR"])

    # Merge with events
    all_events = stacked_df.join(
        cond_long.select("DUPERSID", "EVNTIDX", "CCSR"),
        on=["DUPERSID", "EVNTIDX"],
        how="inner",
    )

    all_events = all_events.filter(F.col("XP") >= 0)

    return all_events


def aggregate_to_person(all_events_df: DataFrame) -> DataFrame:
    """Aggregate to person-condition level."""
    return (
        all_events_df
        .groupBy("DUPERSID", "VARSTR", "VARPSU", "CCSR")
        .agg(
            F.mean("PERWT18F").alias("PERWT18F"),
            F.sum("XP").alias("PERS_XP"),
            F.sum("N_EVENTS").alias("N_EVENTS"),
        )
        .withColumn("PERSON", F.lit(1))
    )


def run(
    spark: SparkSession,
    event_dfs: Optional[Dict[str, DataFrame]] = None,
    clnk_df: Optional[DataFrame] = None,
    cond_df: Optional[DataFrame] = None,
    ccsr_xwalk_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full analysis pipeline."""
    stacked = stack_events(event_dfs, "18")
    linked = link_conditions_ccsr(stacked, clnk_df, cond_df, ccsr_xwalk_df)
    person_level = aggregate_to_person(linked)

    estimates = survey_mean(
        person_level,
        var_cols=["PERSON", "N_EVENTS", "PERS_XP"],
        weight_col="PERWT18F",
    )

    return {
        "stacked_events": stacked,
        "linked_events": linked,
        "person_level": person_level,
        "estimates": estimates,
    }
