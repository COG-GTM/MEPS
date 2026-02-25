"""Summary Table: Diabetes Care - Hemoglobin A1c, 2016.

Migrated from: SAS/summary_tables_examples/care_diabetes_a1c_2016.sas

Diabetes care survey (DCS):
  - Number/percent of adults with diabetes receiving hemoglobin A1c blood test
  - By race/ethnicity

Uses DIABW16F weight (diabetes care supplement weight).

Input: 2016 Full-Year Consolidated file (HC-192)
"""

from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.survey_stats import survey_freq


RACE_LABELS = {
    1: "Hispanic",
    2: "White",
    3: "Black",
    4: "Amer. Indian, AK Native, or mult. races",
    5: "Asian, Hawaiian, or Pacific Islander",
}


def prepare_data(
    spark: SparkSession,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Prepare FYC data with race and A1c variables."""
    df = input_df

    # Create race variable
    df = df.withColumn(
        "HISP", F.when(F.col("RACETHX") == 1, 1).otherwise(0)
    )
    df = df.withColumn(
        "WHITE", F.when(F.col("RACETHX") == 2, 1).otherwise(0)
    )
    df = df.withColumn(
        "BLACK", F.when(F.col("RACETHX") == 3, 1).otherwise(0)
    )
    df = df.withColumn(
        "NATIVE",
        F.when(
            (F.col("RACETHX") > 3) & (F.col("RACEV1X").isin(3, 6)), 1
        ).otherwise(0)
    )
    df = df.withColumn(
        "ASIAN",
        F.when(
            (F.col("RACETHX") > 3) & (F.col("RACEV1X").isin(4, 5)), 1
        ).otherwise(0)
    )

    df = df.withColumn(
        "RACE",
        F.col("HISP") * 1 + F.col("WHITE") * 2 + F.col("BLACK") * 3
        + F.col("NATIVE") * 4 + F.col("ASIAN") * 5
    )

    # Domain: persons with positive diabetes weight
    df = df.withColumn(
        "DOMAIN",
        F.when(F.col("DIABW16F") > 0, 1).otherwise(0)
    )

    # Adjust weight
    df = df.withColumn(
        "DIABW16F",
        F.when(F.col("DOMAIN") == 0, 1).otherwise(F.col("DIABW16F"))
    )

    # A1c measurement label
    df = df.withColumn(
        "A1C_STATUS",
        F.when(F.col("DSA1C53").between(1, 95), F.lit("Had measurement"))
        .when(F.col("DSA1C53").isin(0, 96), F.lit("Did not have measurement"))
        .when(F.col("DSA1C53").isin(-9, -8, -7), F.lit("Don't know/Non-response"))
        .when(F.col("DSA1C53") == -1, F.lit("Inapplicable"))
    )

    return df


def run(
    spark: SparkSession,
    input_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full analysis pipeline."""
    df = prepare_data(spark, input_df)
    estimates = survey_freq(df.filter(F.col("DOMAIN") == 1), "A1C_STATUS", "DIABW16F")
    return {"prepared_data": df, "estimates": estimates}
