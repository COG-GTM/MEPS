"""Summary Table: Health Insurance by Age Groups, 2016.

Migrated from: SAS/summary_tables_examples/ins_age_2016.sas

Health insurance coverage status by age groups:
  - Number/percent of people
  - By insurance coverage (INSURC16) and age groups

Input: 2016 Full-Year Consolidated file (HC-192)
"""

from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.survey_stats import survey_freq


AGE_GROUPS = {
    "Under 5": (0, 4),
    "5-17": (5, 17),
    "18-44": (18, 44),
    "45-64": (45, 64),
    "65+": (65, 999),
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
    """Prepare FYC data with age group and insurance labels."""
    df = input_df

    # Create age group variable
    age_expr = F.lit(None).cast("string")
    for label, (low, high) in AGE_GROUPS.items():
        age_expr = F.when(
            (F.col("AGELAST") >= low) & (F.col("AGELAST") <= high),
            F.lit(label)
        ).otherwise(age_expr)

    df = df.withColumn("AGECAT", age_expr)

    # Create insurance label
    ins_expr = F.lit(None).cast("string")
    for code, label in INSURANCE_LABELS.items():
        ins_expr = F.when(F.col("INSURC16") == code, F.lit(label)).otherwise(ins_expr)

    df = df.withColumn("INSURANCE", ins_expr)

    return df


def estimate_insurance_by_age(df: DataFrame) -> DataFrame:
    """Calculate insurance coverage by age group estimates."""
    return survey_freq(
        df,
        var_col="INSURANCE",
        weight_col="PERWT16F",
    )


def run(
    spark: SparkSession,
    input_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full analysis pipeline."""
    df = prepare_data(spark, input_df)
    estimates = estimate_insurance_by_age(df)
    return {"prepared_data": df, "estimates": estimates}
