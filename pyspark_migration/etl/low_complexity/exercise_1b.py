"""PySpark ETL migration of SAS/workshop_exercises/exercise_1b/Exercise1b.sas

National health care expenses by age group and type of service, 2015.

Original SAS logic:
  - Reads HC-181 (2015 Full-Year Consolidated file)
  - Derives expenditure variables by type of service:
    HOSPITAL_INPATIENT, AMBULATORY, PRESCRIBED_MEDICINES, DENTAL, HOME_HEALTH_OTHER
  - Creates binary flags for persons with an expense by type of service
  - Derives AGE and AGECAT
  - Survey estimation: PROC SURVEYMEANS with VARSTR, VARPSU, PERWT15F

Input:  H181 (2015 FYC)
Output: Parquet with service-type expenditure columns
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, when, lit


def run_etl(spark: SparkSession, input_path: str, output_path: str) -> DataFrame:
    """Execute the Exercise 1b ETL pipeline.

    Args:
        spark: Active SparkSession.
        input_path: Path to H181 data file.
        output_path: Path for output Parquet.

    Returns:
        Transformed DataFrame ready for survey estimation.
    """
    h181 = spark.read.parquet(input_path)

    # Define expenditure variables by type of service
    df = h181.withColumn("TOTAL", col("TOTEXP15"))
    df = df.withColumn("HOSPITAL_INPATIENT", col("IPDEXP15") + col("IPFEXP15"))
    df = df.withColumn(
        "AMBULATORY",
        col("OBVEXP15") + col("OPDEXP15") + col("OPFEXP15") + col("ERDEXP15") + col("ERFEXP15"),
    )
    df = df.withColumn("PRESCRIBED_MEDICINES", col("RXEXP15"))
    df = df.withColumn("DENTAL", col("DVTEXP15"))
    df = df.withColumn(
        "HOME_HEALTH_OTHER",
        col("HHAEXP15") + col("HHNEXP15") + col("OTHEXP15") + col("VISEXP15"),
    )

    # QC: Difference should be zero
    df = df.withColumn(
        "DIFF",
        col("TOTAL")
        - col("HOSPITAL_INPATIENT")
        - col("AMBULATORY")
        - col("PRESCRIBED_MEDICINES")
        - col("DENTAL")
        - col("HOME_HEALTH_OTHER"),
    )

    # Create binary flags for persons with an expense by type
    expense_cols = [
        ("TOTAL", "X_ANYSVCE"),
        ("HOSPITAL_INPATIENT", "X_HOSPITAL_INPATIENT"),
        ("AMBULATORY", "X_AMBULATORY"),
        ("PRESCRIBED_MEDICINES", "X_PRESCRIBED_MEDICINES"),
        ("DENTAL", "X_DENTAL"),
        ("HOME_HEALTH_OTHER", "X_HOME_HEALTH_OTHER"),
    ]
    for src_col, flag_col in expense_cols:
        df = df.withColumn(flag_col, when(col(src_col) > 0, 1).otherwise(0))

    # Derive AGE from AGE15X / AGE42X / AGE31X
    df = df.withColumn(
        "AGE",
        when(col("AGE15X") >= 0, col("AGE15X"))
        .when(col("AGE42X") >= 0, col("AGE42X"))
        .when(col("AGE31X") >= 0, col("AGE31X")),
    )

    # Create AGECAT
    df = df.withColumn(
        "AGECAT",
        when((col("AGE") >= 0) & (col("AGE") <= 64), 1)
        .when(col("AGE") > 64, 2),
    )

    df.write.mode("overwrite").parquet(output_path)
    return df


def get_job_metadata() -> dict:
    """Return metadata about this ETL job."""
    return {
        "job_name": "exercise_1b",
        "description": "National health care expenses by age group and type of service, 2015",
        "complexity_tier": "Low",
        "original_script": "SAS/workshop_exercises/exercise_1b/Exercise1b.sas",
        "input_files": ["H181 (2015 FYC)"],
        "key_transformations": [
            "Derive expenditure by service type (HOSPITAL_INPATIENT, AMBULATORY, etc.)",
            "Create binary flags per service type",
            "Derive AGE from AGE15X/AGE42X/AGE31X cascade",
            "Create AGECAT (1=0-64, 2=65+)",
        ],
        "survey_design": {
            "strata": "VARSTR",
            "cluster": "VARPSU",
            "weight": "PERWT15F",
        },
    }
