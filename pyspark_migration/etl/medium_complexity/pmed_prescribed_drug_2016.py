"""PySpark ETL migration of SAS/summary_tables_examples/pmed_prescribed_drug_2016.sas

Prescribed drug purchases and expenditures by generic drug name, 2016.

Original SAS logic:
  - Reads H188A (2016 RX event file via .ssp CPORT)
  - Sorts by DUPERSID VARSTR VARPSU PERWT16F RXDRGNAM
  - Aggregates to person-drug level: sum of RXXP16X (pers_RXXP), count (n_purchases)
  - Adds person=1 indicator for counting unique persons
  - Survey estimation: PROC SURVEYMEANS by RXDRGNAM domain

Input:  H188A (2016 Prescribed Medicines event file)
Output: Parquet at person-drug level with expenditure aggregates
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, count, lit, sum as spark_sum


def run_etl(spark: SparkSession, input_path: str, output_path: str) -> DataFrame:
    """Execute the pmed_prescribed_drug_2016 ETL pipeline.

    Args:
        spark: Active SparkSession.
        input_path: Path to H188A data file.
        output_path: Path for output Parquet.

    Returns:
        Transformed DataFrame at person-drug level.
    """
    rx = spark.read.parquet(input_path)

    # Aggregate to person-drug level (equivalent to PROC MEANS with BY statement)
    # Group by DUPERSID, VARSTR, VARPSU, PERWT16F, RXDRGNAM
    rx_pers = rx.groupBy("DUPERSID", "VARSTR", "VARPSU", "PERWT16F", "RXDRGNAM").agg(
        spark_sum("RXXP16X").alias("pers_RXXP"),
        count("RXXP16X").alias("n_purchases"),
    )

    # Add person indicator for counting unique persons per drug
    rx_pers = rx_pers.withColumn("person", lit(1))

    rx_pers.write.mode("overwrite").parquet(output_path)
    return rx_pers


def get_job_metadata() -> dict:
    """Return metadata about this ETL job."""
    return {
        "job_name": "pmed_prescribed_drug_2016",
        "description": "Prescribed drug purchases/expenditures by generic drug name, 2016",
        "complexity_tier": "Medium",
        "original_script": "SAS/summary_tables_examples/pmed_prescribed_drug_2016.sas",
        "input_files": ["H188A (2016 Prescribed Medicines event file)"],
        "key_transformations": [
            "Group by DUPERSID, survey design vars, and RXDRGNAM",
            "Sum RXXP16X as pers_RXXP (person-level drug expenditure)",
            "Count fills as n_purchases",
            "Add person=1 indicator for counting unique persons",
        ],
        "survey_design": {
            "strata": "VARSTR",
            "cluster": "VARPSU",
            "weight": "PERWT16F",
        },
    }
