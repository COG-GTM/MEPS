"""Summary Table: Accessibility and Quality of Care - Quality of Care, 2016.

Migrated from: SAS/summary_tables_examples/care_quality_2016.sas

Self-administered questionnaire (SAQ):
  - Number/percent of adults by ability to schedule a routine appointment
  - By insurance coverage status

Uses SAQWT16F weight (SAQ supplement weight).

Input: 2016 Full-Year Consolidated file (HC-192)
"""

from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.survey_stats import survey_freq


FREQ_LABELS = {
    4: "Always",
    3: "Usually",
    2: "Sometimes/Never",
    1: "Sometimes/Never",
    -7: "Don't know/Non-response",
    -8: "Don't know/Non-response",
    -9: "Don't know/Non-response",
    -1: "Inapplicable",
}

INSURANCE_LABELS = {
    1: "<65, Any private",
    2: "<65, Public only",
    3: "<65, Uninsured",
    4: "65+, Medicare only",
    5: "65+, Medicare and private",
    6: "65+, Medicare and other public",
    7: "65+, No medicare",
    8: "65+, No medicare",
}


def prepare_data(
    spark: SparkSession,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Prepare FYC data with quality of care variables."""
    df = input_df

    # Domain: adults who made an appointment
    df = df.withColumn(
        "DOMAIN",
        F.when(
            (F.col("ADRTCR42") == 1) & (F.col("AGELAST") >= 18), 1
        ).otherwise(0)
    )

    # Adjust weights
    df = df.withColumn(
        "SAQWT16F",
        F.when(
            (F.col("DOMAIN") == 0) & (F.col("SAQWT16F") == 0), 1
        ).otherwise(F.col("SAQWT16F"))
    )

    # Create appointment frequency label
    freq_expr = F.lit(None).cast("string")
    for code, label in FREQ_LABELS.items():
        freq_expr = F.when(F.col("ADRTWW42") == code, F.lit(label)).otherwise(freq_expr)
    df = df.withColumn("APPT_FREQ", freq_expr)

    # Create insurance label
    ins_expr = F.lit(None).cast("string")
    for code, label in INSURANCE_LABELS.items():
        ins_expr = F.when(F.col("INSURC16") == code, F.lit(label)).otherwise(ins_expr)
    df = df.withColumn("INSURANCE", ins_expr)

    return df


def run(
    spark: SparkSession,
    input_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full analysis pipeline."""
    df = prepare_data(spark, input_df)
    domain_df = df.filter(F.col("DOMAIN") == 1)
    estimates = survey_freq(domain_df, "APPT_FREQ", "SAQWT16F")
    return {"prepared_data": df, "estimates": estimates}
