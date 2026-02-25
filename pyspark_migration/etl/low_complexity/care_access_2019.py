"""PySpark ETL migration of SAS/summary_tables_examples/care_access_2019.sas

Access to care by poverty status, 2019.

Original SAS logic:
  - Reads H216 (2019 Full-Year Consolidated file)
  - Creates binary affordability indicators:
    afford_MD (medical), afford_DN (dental), afford_PM (prescriptions), afford_ANY
  - Creates domain flag for persons eligible for 'access to care' supplement
  - Adjusts weights: if domain=0 and PERWT19F=0, set PERWT19F=1
  - Survey estimation: PROC SURVEYMEANS by POVCAT19 domain

Input:  H216 (2019 FYC)
Output: Parquet with affordability indicators
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, when, lit


def run_etl(spark: SparkSession, input_path: str, output_path: str) -> DataFrame:
    """Execute the care_access_2019 ETL pipeline.

    Args:
        spark: Active SparkSession.
        input_path: Path to H216 data file.
        output_path: Path for output Parquet.

    Returns:
        Transformed DataFrame ready for survey estimation.
    """
    h216 = spark.read.parquet(input_path)

    # Create affordability indicator variables
    df = h216.withColumn("afford_MD", (col("AFRDCA42") == 1).cast("int"))
    df = df.withColumn("afford_DN", (col("AFRDDN42") == 1).cast("int"))
    df = df.withColumn("afford_PM", (col("AFRDPM42") == 1).cast("int"))
    df = df.withColumn(
        "afford_ANY",
        ((col("afford_MD") == 1) | (col("afford_DN") == 1) | (col("afford_PM") == 1)).cast("int"),
    )

    # Define domain: persons eligible for access to care supplement
    df = df.withColumn("domain", (col("ACCELI42") == 1).cast("int"))

    # Adjust weights so SAS doesn't drop observations
    df = df.withColumn(
        "PERWT19F",
        when((col("domain") == 0) & (col("PERWT19F") == 0), lit(1)).otherwise(col("PERWT19F")),
    )

    df.write.mode("overwrite").parquet(output_path)
    return df


def get_job_metadata() -> dict:
    """Return metadata about this ETL job."""
    return {
        "job_name": "care_access_2019",
        "description": "Access to care by poverty status, 2019",
        "complexity_tier": "Low",
        "original_script": "SAS/summary_tables_examples/care_access_2019.sas",
        "input_files": ["H216 (2019 FYC)"],
        "key_transformations": [
            "Create afford_MD from AFRDCA42",
            "Create afford_DN from AFRDDN42",
            "Create afford_PM from AFRDPM42",
            "Create afford_ANY (any affordability issue)",
            "Create domain flag (ACCELI42 == 1)",
            "Adjust PERWT19F for non-domain zero-weight records",
        ],
        "survey_design": {
            "strata": "VARSTR",
            "cluster": "VARPSU",
            "weight": "PERWT19F",
        },
    }
