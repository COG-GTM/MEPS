"""PySpark ETL migration of SAS/workshop_exercises/exercise_1a/Exercise1a.sas

National health care expenses by age group, 2016.

Original SAS logic:
  - Reads HC-192 (2016 Full-Year Consolidated file)
  - Creates TOTAL = TOTEXP16
  - Creates binary X_ANYSVCE flag (1 if TOTAL > 0)
  - Derives AGE from AGE16X / AGE42X / AGE31X cascade
  - Derives AGECAT (1 = 0-64, 2 = 65+)
  - Survey estimation: PROC SURVEYMEANS with VARSTR, VARPSU, PERWT16F

Input:  H192 (2016 FYC) - parquet or sas7bdat
Output: Parquet with columns for survey estimation
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, when, lit


def run_etl(spark: SparkSession, input_path: str, output_path: str) -> DataFrame:
    """Execute the Exercise 1a ETL pipeline.

    Args:
        spark: Active SparkSession.
        input_path: Path to H192 data file.
        output_path: Path for output Parquet.

    Returns:
        Transformed DataFrame ready for survey estimation.
    """
    # Read in data from 2016 Consolidated Data File (HC-192)
    h192 = spark.read.parquet(input_path)

    # Keep only needed columns
    keep_cols = ["TOTEXP16", "AGE16X", "AGE42X", "AGE31X", "VARSTR", "VARPSU", "PERWT16F"]
    available_cols = [c for c in keep_cols if c in h192.columns]
    df = h192.select(available_cols)

    # Create TOTAL variable
    df = df.withColumn("TOTAL", col("TOTEXP16"))

    # Create flag (1/0) variable for persons with an expense
    df = df.withColumn("X_ANYSVCE", when(col("TOTAL") > 0, 1).otherwise(0))

    # Create a summary AGE variable from end-of-year, 42, and 31 variables
    df = df.withColumn(
        "AGE",
        when(col("AGE16X") >= 0, col("AGE16X"))
        .when(col("AGE42X") >= 0, col("AGE42X"))
        .when(col("AGE31X") >= 0, col("AGE31X"))
    )

    # Create AGECAT: 1 = 0-64, 2 = 65+
    df = df.withColumn(
        "AGECAT",
        when((col("AGE") >= 0) & (col("AGE") <= 64), 1)
        .when(col("AGE") > 64, 2)
    )

    # Write output
    df.write.mode("overwrite").parquet(output_path)

    return df


def get_job_metadata() -> dict:
    """Return metadata about this ETL job."""
    return {
        "job_name": "exercise_1a",
        "description": "National health care expenses by age group, 2016",
        "complexity_tier": "Low",
        "original_script": "SAS/workshop_exercises/exercise_1a/Exercise1a.sas",
        "input_files": ["H192 (2016 FYC)"],
        "key_transformations": [
            "Create TOTAL from TOTEXP16",
            "Create binary X_ANYSVCE flag (expense > 0)",
            "Derive AGE from AGE16X/AGE42X/AGE31X cascade",
            "Create AGECAT (1=0-64, 2=65+)",
        ],
        "survey_design": {
            "strata": "VARSTR",
            "cluster": "VARPSU",
            "weight": "PERWT16F",
        },
    }
