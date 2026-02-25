"""PySpark ETL migration of SAS/summary_tables_examples/use_expenditures_2016.sas

Expenditures by event type and source of payment, 2016.

Original SAS logic:
  - Reads H192 (2016 FYC)
  - Aggregates payment sources into PTR (Private+TRICARE) and OTZ (Other) for
    office-based visits (OBV), office-based physician visits (OBD),
    outpatient visits (OPT), outpatient physician visits (OPV/OPS)
  - Combines facility and SBD expenses for outpatient physician visits
  - Creates domain flags for persons with out-of-pocket expense
  - Survey estimation: PROC SURVEYMEANS with VARSTR, VARPSU, PERWT16F

Input:  H192 (2016 FYC)
Output: Parquet with aggregated payment source columns
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, when


def run_etl(spark: SparkSession, input_path: str, output_path: str) -> DataFrame:
    """Execute the use_expenditures_2016 ETL pipeline.

    Args:
        spark: Active SparkSession.
        input_path: Path to H192 data file.
        output_path: Path for output Parquet.

    Returns:
        Transformed DataFrame ready for survey estimation.
    """
    h192 = spark.read.parquet(input_path)

    # --- Aggregate payment sources ---

    # Office-based visits: PTR and OTZ
    df = h192.withColumn("OBVPTR", col("OBVPRV16") + col("OBVTRI16"))
    df = df.withColumn(
        "OBVOTZ",
        col("OBVOFD16") + col("OBVSTL16") + col("OBVOPR16")
        + col("OBVOPU16") + col("OBVOSR16") + col("OBVWCP16") + col("OBVVA16"),
    )

    # Office-based physician visits
    df = df.withColumn("OBDPTR", col("OBDPRV16") + col("OBDTRI16"))
    df = df.withColumn(
        "OBDOTZ",
        col("OBDOFD16") + col("OBDSTL16") + col("OBDOPR16")
        + col("OBDOPU16") + col("OBDOSR16") + col("OBDWCP16") + col("OBDVA16"),
    )

    # Outpatient visits (facility + SBD)
    df = df.withColumn("OPTPTR", col("OPTPRV16") + col("OPTTRI16"))
    df = df.withColumn(
        "OPTOTZ",
        col("OPTOFD16") + col("OPTSTL16") + col("OPTOPR16")
        + col("OPTOPU16") + col("OPTOSR16") + col("OPTWCP16") + col("OPTVA16"),
    )

    # Outpatient physician visits (facility expense)
    df = df.withColumn("OPVPTR", col("OPVPRV16") + col("OPVTRI16"))
    df = df.withColumn(
        "OPVOTZ",
        col("OPVOFD16") + col("OPVSTL16") + col("OPVOPR16")
        + col("OPVOPU16") + col("OPVOSR16") + col("OPVWCP16") + col("OPVVA16"),
    )

    # Outpatient physician visits (SBD expense)
    df = df.withColumn("OPSPTR", col("OPSPRV16") + col("OPSTRI16"))
    df = df.withColumn(
        "OPSOTZ",
        col("OPSOFD16") + col("OPSSTL16") + col("OPSOPR16")
        + col("OPSOPU16") + col("OPSOSR16") + col("OPSWCP16") + col("OPSVA16"),
    )

    # --- Combine facility and SBD for outpatient physician visits ---
    df = df.withColumn("OPpSLF", col("OPVSLF16") + col("OPSSLF16"))
    df = df.withColumn("OPpMCR", col("OPVMCR16") + col("OPSMCR16"))
    df = df.withColumn("OPpMCD", col("OPVMCD16") + col("OPSMCD16"))
    df = df.withColumn("OPpPTR", col("OPVPTR") + col("OPSPTR"))
    df = df.withColumn("OPpOTZ", col("OPVOTZ") + col("OPSOTZ"))

    # --- Domain flags for persons with out-of-pocket expense ---
    df = df.withColumn("has_OBVSLF", (col("OBVSLF16") > 0).cast("int"))
    df = df.withColumn("has_OBDSLF", (col("OBDSLF16") > 0).cast("int"))
    df = df.withColumn("has_OPTSLF", (col("OPTSLF16") > 0).cast("int"))
    df = df.withColumn("has_OPpSLF", (col("OPpSLF") > 0).cast("int"))

    df.write.mode("overwrite").parquet(output_path)
    return df


def get_job_metadata() -> dict:
    """Return metadata about this ETL job."""
    return {
        "job_name": "use_expenditures_2016",
        "description": "Expenditures by event type and source of payment, 2016",
        "complexity_tier": "Low",
        "original_script": "SAS/summary_tables_examples/use_expenditures_2016.sas",
        "input_files": ["H192 (2016 FYC)"],
        "key_transformations": [
            "Aggregate PTR (Private+TRICARE) for OBV, OBD, OPT, OPV, OPS",
            "Aggregate OTZ (Other sources) for all event types",
            "Combine facility + SBD for outpatient physician visits (OPp*)",
            "Create domain flags for persons with OOP expense",
        ],
        "survey_design": {
            "strata": "VARSTR",
            "cluster": "VARPSU",
            "weight": "PERWT16F",
        },
    }
