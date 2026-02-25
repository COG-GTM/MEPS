"""PySpark ETL migration of SAS/workshop_exercises/exercise_5a/Exercise5a.sas

Family-level variables from person-level data, 2015.

Original SAS logic:
  - Reads H181 (2015 FYC)
  - Sorts by DUID CPSFAMID (CPS family ID)
  - Accumulates person-level data to family level:
    FAMSIZE (count), FAMOOP (sum of TOTSLF15), FAMINC (sum of TTLP15X)
  - Merges family-level weights (FAMWT15C) back to family data
  - Survey estimation: PROC SURVEYMEANS with FAMWT15C weight

Input:  H181 (2015 FYC)
Output: Parquet at family level with FAMSIZE, FAMOOP, FAMINC
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, count, sum as spark_sum, first


def run_etl(spark: SparkSession, input_path: str, output_path: str) -> DataFrame:
    """Execute the Exercise 5a family-level ETL pipeline.

    Args:
        spark: Active SparkSession.
        input_path: Path to H181 data file.
        output_path: Path for output Parquet.

    Returns:
        Family-level DataFrame ready for survey estimation.
    """
    h181 = spark.read.parquet(input_path)

    # Select needed columns
    pers = h181.select(
        "DUPERSID", "DUID", "CPSFAMID", "FAMWT15C", "VARSTR", "VARPSU", "TOTSLF15", "TTLP15X"
    )

    # Aggregate to CPS family level
    fam = pers.groupBy("DUID", "CPSFAMID").agg(
        count("*").alias("FAMSIZE"),
        spark_sum("TOTSLF15").alias("FAMOOP"),
        spark_sum("TTLP15X").alias("FAMINC"),
    )

    # Get family weight and survey design variables
    # Use first non-null value per family (all members share same family weight)
    famwt = (
        pers.filter(col("FAMWT15C") > 0)
        .groupBy("DUID", "CPSFAMID")
        .agg(
            first("FAMWT15C").alias("FAMWT15C"),
            first("VARSTR").alias("VARSTR"),
            first("VARPSU").alias("VARPSU"),
        )
    )

    # Merge family aggregates with weights (equivalent to SAS MERGE with IN=)
    fam2 = fam.join(famwt, on=["DUID", "CPSFAMID"], how="inner")

    fam2.write.mode("overwrite").parquet(output_path)
    return fam2


def get_job_metadata() -> dict:
    """Return metadata about this ETL job."""
    return {
        "job_name": "exercise_5a",
        "description": "Family-level variables from person-level data, 2015",
        "complexity_tier": "Medium",
        "original_script": "SAS/workshop_exercises/exercise_5a/Exercise5a.sas",
        "input_files": ["H181 (2015 FYC)"],
        "key_transformations": [
            "Aggregate person data to CPS family level (DUID + CPSFAMID)",
            "Calculate FAMSIZE (count of family members)",
            "Calculate FAMOOP (sum of TOTSLF15 per family)",
            "Calculate FAMINC (sum of TTLP15X per family)",
            "Merge family weights (FAMWT15C) and survey design vars",
        ],
        "survey_design": {
            "strata": "VARSTR",
            "cluster": "VARPSU",
            "weight": "FAMWT15C",
        },
    }
