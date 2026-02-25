"""PySpark ETL migration of SAS/workshop_exercises/exercise_4a/Exercise4a.sas

Pooling FYC files from 2015 and 2016.

Original SAS logic:
  - Reads H181 (2015 FYC) and H192 (2016 FYC)
  - Filters to persons with positive weight (PERWT > 0)
  - Renames year-specific variables to common names:
    INSCOV15/16 -> INSCOV, PERWT15F/16F -> PERWT, POVCAT15/16 -> POVCAT, TOTSLF15/16 -> TOTSLF
  - Stacks (unions) the two years
  - Creates pooled weight: POOLWT = PERWT / 2
  - Creates SUBPOP flag for age 26-30, uninsured (INSCOV=3), high income (POVCAT=5)
  - Survey estimation: PROC SURVEYMEANS with pooled weight on TOTSLF by SUBPOP domain

Input:  H181 (2015 FYC), H192 (2016 FYC)
Output: Parquet with pooled data and standardized variable names
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, when, lit


def run_etl(
    spark: SparkSession,
    input_path_2015: str,
    input_path_2016: str,
    output_path: str,
) -> DataFrame:
    """Execute the Exercise 4a pooling ETL pipeline.

    Args:
        spark: Active SparkSession.
        input_path_2015: Path to H181 (2015 FYC) data file.
        input_path_2016: Path to H192 (2016 FYC) data file.
        output_path: Path for output Parquet.

    Returns:
        Pooled and transformed DataFrame.
    """
    # Read 2015 FYC
    yr1 = spark.read.parquet(input_path_2015)
    yr1 = yr1.select("DUPERSID", "INSCOV15", "PERWT15F", "VARSTR", "VARPSU", "POVCAT15", "AGELAST", "TOTSLF15")
    yr1 = yr1.filter(col("PERWT15F") > 0)

    # Read 2016 FYC
    yr2 = spark.read.parquet(input_path_2016)
    yr2 = yr2.select("DUPERSID", "INSCOV16", "PERWT16F", "VARSTR", "VARPSU", "POVCAT16", "AGELAST", "TOTSLF16")
    yr2 = yr2.filter(col("PERWT16F") > 0)

    # Rename year-specific variables to common names
    yr1x = (
        yr1.withColumnRenamed("INSCOV15", "INSCOV")
        .withColumnRenamed("PERWT15F", "PERWT")
        .withColumnRenamed("POVCAT15", "POVCAT")
        .withColumnRenamed("TOTSLF15", "TOTSLF")
    )

    yr2x = (
        yr2.withColumnRenamed("INSCOV16", "INSCOV")
        .withColumnRenamed("PERWT16F", "PERWT")
        .withColumnRenamed("POVCAT16", "POVCAT")
        .withColumnRenamed("TOTSLF16", "TOTSLF")
    )

    # Stack the two years using union
    pool = yr1x.unionByName(yr2x)

    # Create pooled weight (divide by number of years pooled)
    pool = pool.withColumn("POOLWT", col("PERWT") / lit(2))

    # Create SUBPOP flag: age 26-30, uninsured (INSCOV=3), high income (POVCAT=5)
    pool = pool.withColumn(
        "SUBPOP",
        when(
            (col("AGELAST") >= 26)
            & (col("AGELAST") <= 30)
            & (col("POVCAT") == 5)
            & (col("INSCOV") == 3),
            lit(1),
        ).otherwise(lit(2)),
    )

    pool.write.mode("overwrite").parquet(output_path)
    return pool


def get_job_metadata() -> dict:
    """Return metadata about this ETL job."""
    return {
        "job_name": "exercise_4a",
        "description": "Pooling FYC files 2015+2016 for uninsured high-income age 26-30",
        "complexity_tier": "Medium",
        "original_script": "SAS/workshop_exercises/exercise_4a/Exercise4a.sas",
        "input_files": ["H181 (2015 FYC)", "H192 (2016 FYC)"],
        "key_transformations": [
            "Filter to positive weight persons",
            "Rename year-specific vars (INSCOV15/16->INSCOV, etc.)",
            "Union/stack 2015 and 2016 data",
            "Create pooled weight POOLWT = PERWT / 2",
            "Create SUBPOP flag (age 26-30, uninsured, high income)",
        ],
        "survey_design": {
            "strata": "VARSTR",
            "cluster": "VARPSU",
            "weight": "POOLWT",
        },
    }
