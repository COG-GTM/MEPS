"""Summary Table: Expenditures by Race and Sex, 2016.

Migrated from: SAS/summary_tables_examples/use_race_sex_2016.sas

Calculates:
  - Number of people
  - Percent of population with an expense
  - Total expenditures
  - Mean expenditure per person
  - Mean/median expenditure per person with expense
  - By sex and race/ethnicity

Input: 2016 Full-Year Consolidated file (HC-192)
"""

from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.survey_stats import survey_mean, survey_mean_by_domain


def prepare_data(
    spark: SparkSession,
    input_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Prepare FYC data with race/ethnicity and expense variables."""
    df = input_df

    # Create race variable
    df = df.withColumn(
        "RACE",
        F.when(F.col("RACETHX") == 1, F.lit("Hispanic"))
        .when(F.col("RACETHX") == 2, F.lit("White"))
        .when(F.col("RACETHX") == 3, F.lit("Black"))
        .when(
            (F.col("RACETHX") > 3) & (F.col("RACEV1X").isin(3, 6)),
            F.lit("Amer. Indian, AK Native, or mult. races")
        )
        .when(
            (F.col("RACETHX") > 3) & (F.col("RACEV1X").isin(4, 5)),
            F.lit("Asian, Hawaiian, or Pacific Islander")
        )
    )

    df = df.withColumn("PERSON", F.lit(1))
    df = df.withColumn(
        "HAS_EXP",
        F.when(F.col("TOTEXP16") > 0, 1).otherwise(0)
    )

    return df


def estimate_by_sex_race(df: DataFrame) -> DataFrame:
    """Calculate estimates by sex and race domain."""
    return survey_mean_by_domain(
        df,
        var_cols=["PERSON", "HAS_EXP", "TOTEXP16"],
        domain_col="SEX",
        domain_value=None,
        weight_col="PERWT16F",
        by_col="RACE",
    )


def run(
    spark: SparkSession,
    input_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full analysis pipeline."""
    df = prepare_data(spark, input_df)
    estimates = estimate_by_sex_race(df)
    return {"prepared_data": df, "estimates": estimates}
