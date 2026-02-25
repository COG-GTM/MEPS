"""PySpark ETL migration of SAS/summary_tables_examples/ins_age_2016.sas

Health insurance by age group, 2016.

Original SAS logic:
  - Reads H192 (2016 FYC via .ssp CPORT)
  - Uses AGELAST and INSURC16 variables
  - Cross-tabulates insurance coverage by age groups using PROC SURVEYFREQ
  - Survey estimation: VARSTR, VARPSU, PERWT16F

Input:  H192 (2016 FYC)
Output: Parquet with age group and insurance classification columns
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, when, lit


def run_etl(spark: SparkSession, input_path: str, output_path: str) -> DataFrame:
    """Execute the ins_age_2016 ETL pipeline.

    Args:
        spark: Active SparkSession.
        input_path: Path to H192 data file.
        output_path: Path for output Parquet.

    Returns:
        Transformed DataFrame ready for survey estimation.
    """
    h192 = spark.read.parquet(input_path)

    # Create age group classification
    df = h192.withColumn(
        "AGEGRP",
        when(col("AGELAST") < 5, lit("Under 5"))
        .when((col("AGELAST") >= 5) & (col("AGELAST") <= 17), lit("5-17"))
        .when((col("AGELAST") >= 18) & (col("AGELAST") <= 44), lit("18-44"))
        .when((col("AGELAST") >= 45) & (col("AGELAST") <= 64), lit("45-64"))
        .when(col("AGELAST") >= 65, lit("65+")),
    )

    # Create insurance coverage classification
    df = df.withColumn(
        "INSURANCE",
        when(col("INSURC16") == 1, lit("<65, Any private"))
        .when(col("INSURC16") == 2, lit("<65, Public only"))
        .when(col("INSURC16") == 3, lit("<65, Uninsured"))
        .when(col("INSURC16") == 4, lit("65+, Medicare only"))
        .when(col("INSURC16") == 5, lit("65+, Medicare and private"))
        .when(col("INSURC16") == 6, lit("65+, Medicare and other public"))
        .when((col("INSURC16") == 7) | (col("INSURC16") == 8), lit("65+, No medicare")),
    )

    df.write.mode("overwrite").parquet(output_path)
    return df


def get_job_metadata() -> dict:
    """Return metadata about this ETL job."""
    return {
        "job_name": "ins_age_2016",
        "description": "Health insurance by age group, 2016",
        "complexity_tier": "Low",
        "original_script": "SAS/summary_tables_examples/ins_age_2016.sas",
        "input_files": ["H192 (2016 FYC)"],
        "key_transformations": [
            "Create AGEGRP from AGELAST (Under 5, 5-17, 18-44, 45-64, 65+)",
            "Create INSURANCE from INSURC16 (7 categories)",
        ],
        "survey_design": {
            "strata": "VARSTR",
            "cluster": "VARPSU",
            "weight": "PERWT16F",
        },
    }
