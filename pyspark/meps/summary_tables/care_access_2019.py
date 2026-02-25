"""Summary Table: Accessibility and Quality of Care - Access to Care, 2019.

Migrated from: SAS/summary_tables_examples/care_access_2019.sas

Did not receive treatment because couldn't afford it:
  - Number/percent of people
  - By poverty status

Input: 2019 Full-Year Consolidated file (HC-216)
"""

from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.survey_stats import survey_mean_by_domain


def prepare_data(
    spark: SparkSession,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Prepare FYC data with affordability variables."""
    df = input_df

    # Couldn't afford care
    df = df.withColumn(
        "AFFORD_MD", F.when(F.col("AFRDCA42") == 1, 1).otherwise(0)
    )
    df = df.withColumn(
        "AFFORD_DN", F.when(F.col("AFRDDN42") == 1, 1).otherwise(0)
    )
    df = df.withColumn(
        "AFFORD_PM", F.when(F.col("AFRDPM42") == 1, 1).otherwise(0)
    )
    df = df.withColumn(
        "AFFORD_ANY",
        F.when(
            (F.col("AFFORD_MD") == 1) | (F.col("AFFORD_DN") == 1) | (F.col("AFFORD_PM") == 1),
            1
        ).otherwise(0)
    )

    # Domain: persons eligible for access supplement
    df = df.withColumn(
        "DOMAIN", F.when(F.col("ACCELI42") == 1, 1).otherwise(0)
    )

    # Adjust weights
    df = df.withColumn(
        "PERWT19F",
        F.when(
            (F.col("DOMAIN") == 0) & (F.col("PERWT19F") == 0), 1
        ).otherwise(F.col("PERWT19F"))
    )

    return df


def estimate_by_poverty(df: DataFrame) -> DataFrame:
    """Estimate affordability issues by poverty status."""
    return survey_mean_by_domain(
        df,
        var_cols=["AFFORD_ANY", "AFFORD_MD", "AFFORD_DN", "AFFORD_PM"],
        domain_col="DOMAIN",
        domain_value=1,
        weight_col="PERWT19F",
        by_col="POVCAT19",
    )


def run(
    spark: SparkSession,
    input_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full analysis pipeline."""
    df = prepare_data(spark, input_df)
    estimates = estimate_by_poverty(df)
    return {"prepared_data": df, "estimates": estimates}
