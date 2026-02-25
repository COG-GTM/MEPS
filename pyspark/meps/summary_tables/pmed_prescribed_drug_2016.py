"""Summary Table: Prescribed Drugs by Generic Drug Name, 2016.

Migrated from: SAS/summary_tables_examples/pmed_prescribed_drug_2016.sas

Purchases and expenditures by generic drug name (RXDRGNAM):
  - Number of people with purchase
  - Total purchases
  - Total expenditures

Input: 2016 RX event file (HC-188A)
"""

from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.survey_stats import survey_mean


def aggregate_to_person_drug(
    spark: SparkSession,
    rx_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Aggregate RX events to person-drug level.

    Args:
        spark: Active SparkSession.
        rx_df: RX event DataFrame.

    Returns:
        Person-drug level DataFrame.
    """
    return (
        rx_df
        .groupBy("DUPERSID", "VARSTR", "VARPSU", "PERWT16F", "RXDRGNAM")
        .agg(
            F.sum("RXXP16X").alias("PERS_RXXP"),
            F.count("*").alias("N_PURCHASES"),
        )
        .withColumn("PERSON", F.lit(1))
    )


def run(
    spark: SparkSession,
    rx_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full analysis pipeline."""
    person_drug = aggregate_to_person_drug(spark, rx_df)

    estimates = survey_mean(
        person_drug,
        var_cols=["PERSON", "N_PURCHASES", "PERS_RXXP"],
        weight_col="PERWT16F",
    )

    return {
        "person_drug_level": person_drug,
        "estimates": estimates,
    }
