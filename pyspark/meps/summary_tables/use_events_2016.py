"""Summary Table: Use and Events, 2016.

Migrated from: SAS/summary_tables_examples/use_events_2016.sas

Estimates on number of events and mean events per person by event type.

Input: 2016 Full-Year Consolidated file (HC-192)
"""

from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.survey_stats import survey_mean


def prepare_data(
    spark: SparkSession,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Prepare FYC data for event analysis."""
    return input_df


def run(
    spark: SparkSession,
    input_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full analysis pipeline."""
    df = prepare_data(spark, input_df)

    event_vars = [
        c for c in df.columns
        if c.endswith("16") and any(c.startswith(p) for p in [
            "OBTOTV", "OPTOTV", "ERTOT", "IPDIS", "HHTOTD", "RXTOT"
        ])
    ]

    if not event_vars:
        event_vars = ["OBTOTV16"]

    estimates = survey_mean(df, var_cols=event_vars, weight_col="PERWT16F")
    return {"prepared_data": df, "estimates": estimates}
