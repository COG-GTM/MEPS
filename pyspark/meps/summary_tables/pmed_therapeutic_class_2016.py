"""Summary Table: Prescribed Drugs by Therapeutic Class, 2016.

Migrated from: SAS/summary_tables_examples/pmed_therapeutic_class_2016.sas

Purchases and expenditures by Multum therapeutic class name (TC1):
  - Number of people with purchase
  - Total purchases
  - Total expenditures

Input: 2016 RX event file (HC-188A)
"""

from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.survey_stats import survey_mean


TC1_LABELS = {
    -9: "Not ascertained",
    -1: "Inapplicable",
    1: "Anti-infectives",
    19: "Antihyperlipidemic agents",
    20: "Antineoplastics",
    28: "Biologicals",
    40: "Cardiovascular agents",
    57: "Central nervous system agents",
    81: "Coagulation modifiers",
    87: "Gastrointestinal agents",
    97: "Hormones/hormone modifiers",
    105: "Miscellaneous agents",
    113: "Genitourinary tract agents",
    115: "Nutritional products",
    122: "Respiratory agents",
    133: "Topical agents",
    218: "Alternative medicines",
    242: "Psychotherapeutic agents",
    254: "Immunologic agents",
    358: "Metabolic agents",
}


def aggregate_to_person_tc(
    spark: SparkSession,
    rx_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Aggregate RX events to person-therapeutic class level.

    Args:
        spark: Active SparkSession.
        rx_df: RX event DataFrame.

    Returns:
        Person-TC level DataFrame.
    """
    # Add TC1 label
    tc_expr = F.lit(None).cast("string")
    for code, label in TC1_LABELS.items():
        tc_expr = F.when(F.col("TC1") == code, F.lit(label)).otherwise(tc_expr)

    df = rx_df.withColumn("TC1_LABEL", tc_expr)

    return (
        df
        .groupBy("DUPERSID", "VARSTR", "VARPSU", "PERWT16F", "TC1", "TC1_LABEL")
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
    person_tc = aggregate_to_person_tc(spark, rx_df)

    estimates = survey_mean(
        person_tc,
        var_cols=["PERSON", "N_PURCHASES", "PERS_RXXP"],
        weight_col="PERWT16F",
    )

    return {
        "person_tc_level": person_tc,
        "estimates": estimates,
    }
