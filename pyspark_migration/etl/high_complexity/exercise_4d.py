"""PySpark ETL migration of SAS/workshop_exercises/exercise_4d/Exercise4.sas

Pooling FYC files 2017-2019 with Pooled Linkage Variance file (HC-036).

Original SAS logic:
  1. Read 2017 (H201), 2018 (H209), 2019 (H216) FYC files
  2. Rename year-specific variables (totexp17/18/19 -> totexp, etc.)
  3. Stack (concatenate) all three years
  4. Create pooled weight: perwtf = perwtYYf / 3
  5. Construct JOINT_PAIN variable from ARTHDX and JTPAIN31 (with CAPI redesign handling)
  6. Create SPOP (subpopulation: age 18+)
  7. Handle 8-char vs 10-char DUPERSID for 2017 data
  8. Merge with HC-036 Pooled Linkage Variance file (stra9619, psu9619)
  9. Survey estimation uses stra9619/psu9619 instead of VARSTR/VARPSU

Input files:
  - H201 (2017 FYC)
  - H209 (2018 FYC)
  - H216 (2019 FYC)
  - H36U19 (1996-2019 Pooled Linkage Variance Estimation file)

Output: Parquet with pooled 2017-2019 data merged with variance structure
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, concat, length, lit, lpad, strip, when,
)


def run_etl(
    spark: SparkSession,
    fyc_2017_path: str,
    fyc_2018_path: str,
    fyc_2019_path: str,
    vs_file_path: str,
    output_path: str,
) -> dict:
    """Execute the Exercise 4d pooling ETL pipeline.

    Args:
        spark: Active SparkSession.
        fyc_2017_path: Path to H201 (2017 FYC).
        fyc_2018_path: Path to H209 (2018 FYC).
        fyc_2019_path: Path to H216 (2019 FYC).
        vs_file_path: Path to H36U19 (Pooled Linkage Variance file).
        output_path: Path for output Parquet.

    Returns:
        Dictionary of intermediate DataFrames for testing checkpoints.
    """
    checkpoints = {}

    # --- Read 2017 FYC ---
    yr2017 = spark.read.parquet(fyc_2017_path)
    yr2017 = yr2017.select(
        "DUPERSID", "PANEL", "VARSTR", "VARPSU", "PERWT17F",
        "AGELAST", "ARTHDX", "JTPAIN31", "TOTEXP17", "TOTSLF17",
    )
    yr2017 = (
        yr2017.withColumnRenamed("TOTEXP17", "TOTEXP")
        .withColumnRenamed("TOTSLF17", "TOTSLF")
        .withColumn("YEAR", lit(2017))
        .withColumn("PERWTF", col("PERWT17F") / lit(3))
    )

    # Handle 8-char DUPERSID for 2017: prepend PANEL as 2-digit zero-padded
    yr2017 = yr2017.withColumn(
        "DUPERSID",
        when(
            length(col("DUPERSID")) == 8,
            concat(lpad(col("PANEL").cast("string"), 2, "0"), col("DUPERSID")),
        ).otherwise(col("DUPERSID")),
    )

    # Create JOINT_PAIN for 2017 (uses JTPAIN31, not JTPAIN31_M18)
    yr2017 = yr2017.withColumn("SPOP", lit(0))
    yr2017 = yr2017.withColumn(
        "SPOP",
        when(
            (col("AGELAST") >= 18)
            & ~((col("ARTHDX") <= 0) & (col("JTPAIN31") < 0)),
            lit(1),
        ).otherwise(lit(0)),
    )
    yr2017 = yr2017.withColumn(
        "JOINT_PAIN",
        when(
            (col("SPOP") == 1) & ((col("ARTHDX") == 1) | (col("JTPAIN31") == 1)),
            lit(1),
        ).when(col("SPOP") == 1, lit(2)),
    )

    # --- Read 2018 FYC ---
    yr2018 = spark.read.parquet(fyc_2018_path)
    yr2018 = yr2018.select(
        "DUPERSID", "PANEL", "VARSTR", "VARPSU", "PERWT18F",
        "AGELAST", "ARTHDX", "JTPAIN31_M18", "TOTEXP18", "TOTSLF18",
    )
    yr2018 = (
        yr2018.withColumnRenamed("TOTEXP18", "TOTEXP")
        .withColumnRenamed("TOTSLF18", "TOTSLF")
        .withColumn("YEAR", lit(2018))
        .withColumn("PERWTF", col("PERWT18F") / lit(3))
    )
    yr2018 = yr2018.withColumn(
        "SPOP",
        when(
            (col("AGELAST") >= 18)
            & ~((col("ARTHDX") < 0) & (col("JTPAIN31_M18") < 0)),
            lit(1),
        ).otherwise(lit(0)),
    )
    yr2018 = yr2018.withColumn(
        "JOINT_PAIN",
        when(
            (col("SPOP") == 1) & ((col("ARTHDX") == 1) | (col("JTPAIN31_M18") == 1)),
            lit(1),
        ).when(col("SPOP") == 1, lit(2)),
    )

    # --- Read 2019 FYC ---
    yr2019 = spark.read.parquet(fyc_2019_path)
    yr2019 = yr2019.select(
        "DUPERSID", "PANEL", "VARSTR", "VARPSU", "PERWT19F",
        "AGELAST", "ARTHDX", "JTPAIN31_M18", "TOTEXP19", "TOTSLF19",
    )
    yr2019 = (
        yr2019.withColumnRenamed("TOTEXP19", "TOTEXP")
        .withColumnRenamed("TOTSLF19", "TOTSLF")
        .withColumn("YEAR", lit(2019))
        .withColumn("PERWTF", col("PERWT19F") / lit(3))
    )
    yr2019 = yr2019.withColumn(
        "SPOP",
        when(
            (col("AGELAST") >= 18)
            & ~((col("ARTHDX") < 0) & (col("JTPAIN31_M18") < 0)),
            lit(1),
        ).otherwise(lit(0)),
    )
    yr2019 = yr2019.withColumn(
        "JOINT_PAIN",
        when(
            (col("SPOP") == 1) & ((col("ARTHDX") == 1) | (col("JTPAIN31_M18") == 1)),
            lit(1),
        ).when(col("SPOP") == 1, lit(2)),
    )

    # --- Standardize columns for union ---
    common_cols = [
        "DUPERSID", "PANEL", "VARSTR", "VARPSU", "AGELAST",
        "ARTHDX", "TOTEXP", "TOTSLF", "YEAR", "PERWTF", "SPOP", "JOINT_PAIN",
    ]
    yr2017_std = yr2017.select(common_cols)
    yr2018_std = yr2018.select(common_cols)
    yr2019_std = yr2019.select(common_cols)

    # --- Stack all three years ---
    pool = yr2017_std.union(yr2018_std).union(yr2019_std)

    # Add zero weight flag for QC
    pool = pool.withColumn(
        "ZERO_WEIGHT",
        when(col("PERWTF") == 0, lit(1)).otherwise(lit(0)),
    )
    checkpoints["pool"] = pool

    # --- Merge with HC-036 Pooled Linkage Variance file ---
    vs_file = spark.read.parquet(vs_file_path)

    # Handle 8-char DUPERSID in variance file
    if "DUPERSID" in vs_file.columns and "PANEL" in vs_file.columns:
        vs_file = vs_file.withColumn(
            "DUPERSID",
            when(
                length(col("DUPERSID")) == 8,
                concat(lpad(col("PANEL").cast("string"), 2, "0"), col("DUPERSID")),
            ).otherwise(col("DUPERSID")),
        )

    # Filter to panels 21-24 (covering 2017-2019)
    if "PANEL" in vs_file.columns:
        vs_file = vs_file.filter(col("PANEL").isin([21, 22, 23, 24]))

    vs_file = vs_file.dropDuplicates(["DUPERSID"])

    # Select variance structure columns
    vs_cols = ["DUPERSID"]
    if "STRA9619" in vs_file.columns:
        vs_cols.append("STRA9619")
    if "PSU9619" in vs_file.columns:
        vs_cols.append("PSU9619")
    vs_file = vs_file.select(vs_cols)

    # Left join pooled data with variance file
    result = pool.join(vs_file, on="DUPERSID", how="left")
    checkpoints["result"] = result

    result.write.mode("overwrite").parquet(output_path)
    return checkpoints


def get_job_metadata() -> dict:
    """Return metadata about this ETL job."""
    return {
        "job_name": "exercise_4d",
        "description": "Pooling FYC files 2017-2019 with Pooled Linkage Variance file (HC-036)",
        "complexity_tier": "High",
        "original_script": "SAS/workshop_exercises/exercise_4d/Exercise4.sas",
        "input_files": [
            "H201 (2017 FYC)",
            "H209 (2018 FYC)",
            "H216 (2019 FYC)",
            "H36U19 (Pooled Linkage Variance file)",
        ],
        "key_transformations": [
            "Rename year-specific vars to common names",
            "Stack 2017+2018+2019 FYC data",
            "Create pooled weight PERWTF = PERWTyyF / 3",
            "Handle CAPI redesign: JTPAIN31 (2017) vs JTPAIN31_M18 (2018-19)",
            "Handle 8-char vs 10-char DUPERSID for 2017",
            "Merge with HC-036 variance file for STRA9619/PSU9619",
            "Create SPOP (age 18+) and JOINT_PAIN indicators",
        ],
        "num_join_operations": 1,
        "survey_design": {
            "strata": "STRA9619",
            "cluster": "PSU9619",
            "weight": "PERWTF",
        },
    }
