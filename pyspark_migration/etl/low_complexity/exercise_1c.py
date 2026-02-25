"""PySpark ETL migration of SAS/workshop_exercises/exercise_1c/Exercise1c.sas

National health care expenses by age group, 2018.

Original SAS logic:
  - Reads HC-209 (2018 Full-Year Consolidated file)
  - Creates WITH_AN_EXPENSE = TOTEXP18
  - Creates CHAR_WITH_AN_EXPENSE (character flag: 'No Expense' / 'Any Expense')
  - Survey estimation: PROC SURVEYMEANS, PROC SURVEYFREQ with VARSTR, VARPSU, PERWT18F

Input:  H209 (2018 FYC)
Output: Parquet with expense classification columns
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, when, lit


def run_etl(spark: SparkSession, input_path: str, output_path: str) -> DataFrame:
    """Execute the Exercise 1c ETL pipeline.

    Args:
        spark: Active SparkSession.
        input_path: Path to H209 data file.
        output_path: Path for output Parquet.

    Returns:
        Transformed DataFrame ready for survey estimation.
    """
    h209 = spark.read.parquet(input_path)

    # Keep only needed columns
    keep_cols = ["TOTEXP18", "AGELAST", "VARSTR", "VARPSU", "PERWT18F", "PANEL"]
    available = [c for c in keep_cols if c in h209.columns]
    df = h209.select(available)

    # Create WITH_AN_EXPENSE variable (copy of TOTEXP18)
    df = df.withColumn("WITH_AN_EXPENSE", col("TOTEXP18"))

    # Create character classification variable
    df = df.withColumn(
        "CHAR_WITH_AN_EXPENSE",
        when(col("TOTEXP18") == 0, lit("No Expense")).otherwise(lit("Any Expense")),
    )

    # Create AGECAT for domain analysis
    df = df.withColumn(
        "AGECAT",
        when(col("AGELAST") <= 64, lit("0-64")).otherwise(lit("65+")),
    )

    df.write.mode("overwrite").parquet(output_path)
    return df


def get_job_metadata() -> dict:
    """Return metadata about this ETL job."""
    return {
        "job_name": "exercise_1c",
        "description": "National health care expenses by age group, 2018",
        "complexity_tier": "Low",
        "original_script": "SAS/workshop_exercises/exercise_1c/Exercise1c.sas",
        "input_files": ["H209 (2018 FYC)"],
        "key_transformations": [
            "Create WITH_AN_EXPENSE from TOTEXP18",
            "Create CHAR_WITH_AN_EXPENSE classification",
            "Create AGECAT for domain analysis",
        ],
        "survey_design": {
            "strata": "VARSTR",
            "cluster": "VARPSU",
            "weight": "PERWT18F",
        },
    }
