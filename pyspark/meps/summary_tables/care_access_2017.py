"""Summary Table: Accessibility and Quality of Care - Access to Care, 2017.

Migrated from: SAS/summary_tables_examples/care_access_2017.sas

Reasons for difficulty receiving needed care:
  - Number/percent of people
  - By poverty status

Creates delay/affordability/insurance problem flags from survey variables.

Input: 2017 Full-Year Consolidated file (HC-201)
"""

from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.survey_stats import survey_mean_by_domain


def prepare_data(
    spark: SparkSession,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Prepare FYC data with access to care variables."""
    df = input_df

    # Any delay / unable to receive needed care
    df = df.withColumn(
        "DELAY_MD",
        F.when((F.col("MDUNAB42") == 1) | (F.col("MDDLAY42") == 1), 1).otherwise(0)
    )
    df = df.withColumn(
        "DELAY_DN",
        F.when((F.col("DNUNAB42") == 1) | (F.col("DNDLAY42") == 1), 1).otherwise(0)
    )
    df = df.withColumn(
        "DELAY_PM",
        F.when((F.col("PMUNAB42") == 1) | (F.col("PMDLAY42") == 1), 1).otherwise(0)
    )

    # Couldn't afford
    df = df.withColumn(
        "AFFORD_MD",
        F.when((F.col("MDDLRS42") == 1) | (F.col("MDUNRS42") == 1), 1).otherwise(0)
    )
    df = df.withColumn(
        "AFFORD_DN",
        F.when((F.col("DNDLRS42") == 1) | (F.col("DNUNRS42") == 1), 1).otherwise(0)
    )
    df = df.withColumn(
        "AFFORD_PM",
        F.when((F.col("PMDLRS42") == 1) | (F.col("PMUNRS42") == 1), 1).otherwise(0)
    )

    # Insurance problems
    df = df.withColumn(
        "INSURE_MD",
        F.when(
            F.col("MDDLRS42").isin(2, 3) | F.col("MDUNRS42").isin(2, 3), 1
        ).otherwise(0)
    )
    df = df.withColumn(
        "INSURE_DN",
        F.when(
            F.col("DNDLRS42").isin(2, 3) | F.col("DNUNRS42").isin(2, 3), 1
        ).otherwise(0)
    )
    df = df.withColumn(
        "INSURE_PM",
        F.when(
            F.col("PMDLRS42").isin(2, 3) | F.col("PMUNRS42").isin(2, 3), 1
        ).otherwise(0)
    )

    # Other reasons
    df = df.withColumn(
        "OTHER_MD",
        F.when((F.col("MDDLRS42") > 3) | (F.col("MDUNRS42") > 3), 1).otherwise(0)
    )
    df = df.withColumn(
        "OTHER_DN",
        F.when((F.col("DNDLRS42") > 3) | (F.col("DNUNRS42") > 3), 1).otherwise(0)
    )
    df = df.withColumn(
        "OTHER_PM",
        F.when((F.col("PMDLRS42") > 3) | (F.col("PMUNRS42") > 3), 1).otherwise(0)
    )

    # Combined flags
    df = df.withColumn(
        "DELAY_ANY",
        F.when(
            (F.col("DELAY_MD") == 1) | (F.col("DELAY_DN") == 1) | (F.col("DELAY_PM") == 1),
            1
        ).otherwise(0)
    )
    df = df.withColumn(
        "AFFORD_ANY",
        F.when(
            (F.col("AFFORD_MD") == 1) | (F.col("AFFORD_DN") == 1) | (F.col("AFFORD_PM") == 1),
            1
        ).otherwise(0)
    )
    df = df.withColumn(
        "INSURE_ANY",
        F.when(
            (F.col("INSURE_MD") == 1) | (F.col("INSURE_DN") == 1) | (F.col("INSURE_PM") == 1),
            1
        ).otherwise(0)
    )
    df = df.withColumn(
        "OTHER_ANY",
        F.when(
            (F.col("OTHER_MD") == 1) | (F.col("OTHER_DN") == 1) | (F.col("OTHER_PM") == 1),
            1
        ).otherwise(0)
    )

    # Domain: persons eligible for access supplement who had difficulty
    df = df.withColumn(
        "DOMAIN",
        F.when((F.col("ACCELI42") == 1) & (F.col("DELAY_ANY") == 1), 1).otherwise(0)
    )

    # Adjust weights
    df = df.withColumn(
        "PERWT17F",
        F.when(
            (F.col("DOMAIN") == 0) & (F.col("PERWT17F") == 0), 1
        ).otherwise(F.col("PERWT17F"))
    )

    return df


def estimate_by_poverty(df: DataFrame) -> DataFrame:
    """Estimate reasons for difficulty by poverty status."""
    return survey_mean_by_domain(
        df,
        var_cols=["AFFORD_ANY", "INSURE_ANY", "OTHER_ANY"],
        domain_col="DOMAIN",
        domain_value=1,
        weight_col="PERWT17F",
        by_col="POVCAT17",
    )


def run(
    spark: SparkSession,
    input_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full analysis pipeline."""
    df = prepare_data(spark, input_df)
    estimates = estimate_by_poverty(df)
    return {"prepared_data": df, "estimates": estimates}
