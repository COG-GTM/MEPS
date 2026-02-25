"""PySpark ETL migration of R/workshop_exercises/exercise_4b.R

Regression for COVID care delay, 2020.

Original R logic:
  - Reads H224 (2020 FYC via .dta or MEPS R package)
  - Converts CVDLAY*53 variables from 1/2 to 0/1 for logistic regression
  - Creates subpopulation flags for valid responses (value >= 0)
  - Survey estimation: svymean for proportions, svyglm for logistic regression

Input:  H224 (2020 FYC)
Output: Parquet with recoded COVID delay variables and subpop flags
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, when, lit


def run_etl(spark: SparkSession, input_path: str, output_path: str) -> DataFrame:
    """Execute the Exercise 4b COVID care delay ETL pipeline.

    Args:
        spark: Active SparkSession.
        input_path: Path to H224 data file.
        output_path: Path for output Parquet.

    Returns:
        Transformed DataFrame with COVID delay indicators.
    """
    fyc20 = spark.read.parquet(input_path)

    # Select needed variables
    keep_cols = [
        "DUPERSID", "VARPSU", "VARSTR", "PERWT20F",
        "CVDLAYCA53", "CVDLAYDN53", "CVDLAYPM53",
        "AGELAST", "SEX", "RACETHX", "INSCOV20", "REGION53",
    ]
    available = [c for c in keep_cols if c in fyc20.columns]
    df = fyc20.select(available)

    # Convert CVDLAY variables from 1/2 to 0/1
    # 1 = Yes (delayed) -> 1, 2 = No -> 0, negative values = missing
    df = df.withColumn(
        "covid_delay_CARE",
        when(col("CVDLAYCA53") == 1, lit(1))
        .when(col("CVDLAYCA53") == 2, lit(0))
        .otherwise(col("CVDLAYCA53")),
    )
    df = df.withColumn(
        "covid_delay_DENTAL",
        when(col("CVDLAYDN53") == 1, lit(1))
        .when(col("CVDLAYDN53") == 2, lit(0))
        .otherwise(col("CVDLAYDN53")),
    )
    df = df.withColumn(
        "covid_delay_PMED",
        when(col("CVDLAYPM53") == 1, lit(1))
        .when(col("CVDLAYPM53") == 2, lit(0))
        .otherwise(col("CVDLAYPM53")),
    )

    # Create subpopulation flags (exclude missing/inapplicable responses)
    df = df.withColumn("subpop_CARE", (col("CVDLAYCA53") >= 0).cast("int"))
    df = df.withColumn("subpop_DENTAL", (col("CVDLAYDN53") >= 0).cast("int"))
    df = df.withColumn("subpop_PMED", (col("CVDLAYPM53") >= 0).cast("int"))

    df.write.mode("overwrite").parquet(output_path)
    return df


def get_job_metadata() -> dict:
    """Return metadata about this ETL job."""
    return {
        "job_name": "exercise_4b",
        "description": "Regression for COVID care delay, 2020",
        "complexity_tier": "Medium",
        "original_script": "R/workshop_exercises/exercise_4b.R",
        "input_files": ["H224 (2020 FYC)"],
        "key_transformations": [
            "Convert CVDLAYCA53/DN53/PM53 from 1/2 to 0/1 binary",
            "Create subpopulation flags for valid responses (>= 0)",
            "Select demographic covariates: AGELAST, SEX, RACETHX, INSCOV20, REGION53",
        ],
        "survey_design": {
            "strata": "VARSTR",
            "cluster": "VARPSU",
            "weight": "PERWT20F",
        },
    }
