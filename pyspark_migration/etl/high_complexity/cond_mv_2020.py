"""PySpark ETL migration of Stata/workshop_exercises/cond_mv_2020.do

Office-based visits for mental health / hyperlipidemia, 2020.
(The Stata script in the repo actually implements the same hyperlipidemia
PMED linkage as cond_pmed_2020.sas, using Stata syntax.)

Original Stata logic (4-file join chain):
  1. Read PMED (h220a), Conditions (h222), CLNK (h220if1), FYC (h224)
  2. Filter conditions to hyperlipidemia (CCSR = 'END010')
  3. Merge conditions to CLNK by condidx (m:m)
  4. duplicates drop evntidx, force (CRITICAL de-duplication)
  5. Merge to PMED by evntidx (1:m)
  6. collapse to person-level: sum num_rx and exp_rx
  7. Merge to FY, fill zeros, create any_rx flag
  8. svyset and estimate totals/means

Input files:
  - h220a (2020 Prescribed Medicines)
  - h222 (2020 Conditions)
  - h220if1 (2020 CLNK)
  - h224 (2020 FYC)

Output: Person-level Parquet with rx counts and expenditures
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, count, lit, sum as spark_sum, when


def run_etl(
    spark: SparkSession,
    pmed_path: str,
    cond_path: str,
    clnk_path: str,
    fyc_path: str,
    output_path: str,
) -> dict:
    """Execute the cond_mv_2020 ETL pipeline (Stata migration).

    Args:
        spark: Active SparkSession.
        pmed_path: Path to h220a (PMED) data.
        cond_path: Path to h222 (Conditions) data.
        clnk_path: Path to h220if1 (CLNK) data.
        fyc_path: Path to h224 (FYC) data.
        output_path: Path for output Parquet.

    Returns:
        Dictionary of intermediate DataFrames for testing checkpoints.
    """
    checkpoints = {}

    # --- Read input files ---

    # PMED file - rename linkidx to evntidx per Stata script
    pmed = spark.read.parquet(pmed_path)
    # Stata: rename linkidx evntidx
    pmed = pmed.withColumnRenamed("LINKIDX", "EVNTIDX")
    pmed = pmed.select("DUPERSID", "DRUGIDX", "RXRECIDX", "EVNTIDX", "RXDRGNAM", "RXXP20X")

    # Conditions file - subset to hyperlipidemia
    cond = spark.read.parquet(cond_path)
    cond = cond.select("DUPERSID", "CONDIDX", "ICD10CDX", "CCSR1X", "CCSR2X", "CCSR3X")

    # CLNK file
    clnk = spark.read.parquet(clnk_path)

    # FYC file
    fyc = spark.read.parquet(fyc_path)
    fyc = fyc.select(
        "DUPERSID", "SEX", "AGELAST", "CHOLDX", "POVCAT20",
        "VARSTR", "VARPSU", "PERWT20F",
    )

    # --- Filter to hyperlipidemia ---
    # Stata: keep if ccsr1x == "END010" | ccsr2x == "END010" | ccsr3x == "END010"
    hl_cond = cond.filter(
        (col("CCSR1X") == "END010")
        | (col("CCSR2X") == "END010")
        | (col("CCSR3X") == "END010")
    )
    checkpoints["hl_cond"] = hl_cond

    # --- Merge conditions to CLNK by condidx ---
    # Stata: merge m:m condidx using CLNK_2020; drop if _merge~=3
    cond_clnk = hl_cond.join(clnk, on="CONDIDX", how="inner")
    checkpoints["cond_clnk"] = cond_clnk

    # --- CRITICAL: De-duplicate on EVNTIDX ---
    # Stata: duplicates drop evntidx, force
    cond_clnk_dedup = cond_clnk.dropDuplicates(["EVNTIDX"])
    checkpoints["cond_clnk_dedup"] = cond_clnk_dedup

    # --- Merge to PMED by evntidx ---
    # Stata: merge 1:m evntidx using PM_2020; drop if _merge~=3
    linked = cond_clnk_dedup.join(pmed, on="EVNTIDX", how="inner")
    checkpoints["linked"] = linked

    # --- Collapse to person level ---
    # Stata: gen one=1; collapse (sum) num_rx=one (sum) exp_rx=rxxp20x, by(dupersid)
    person_level = linked.groupBy("DUPERSID").agg(
        count("*").alias("num_rx"),
        spark_sum("RXXP20X").alias("exp_rx"),
    )
    checkpoints["person_level"] = person_level

    # --- Merge to FY, fill zeros ---
    # Stata: merge 1:1 dupersid using FY_2020; replace exp_rx=0 if _merge==2; etc.
    result = fyc.join(person_level, on="DUPERSID", how="left")
    result = result.fillna({"num_rx": 0, "exp_rx": 0.0})
    result = result.withColumn("any_rx", (col("num_rx") > 0).cast("int"))

    # Stata: recode choldx (1=1) (2=0) (*=.), gen(HL_ever)
    result = result.withColumn(
        "HL_ever",
        when(col("CHOLDX") == 1, lit(1))
        .when(col("CHOLDX") == 2, lit(0)),
    )
    checkpoints["result"] = result

    result.write.mode("overwrite").parquet(output_path)
    return checkpoints


def get_job_metadata() -> dict:
    """Return metadata about this ETL job."""
    return {
        "job_name": "cond_mv_2020",
        "description": "Prescribed medicines for hyperlipidemia (Stata migration), 2020",
        "complexity_tier": "High",
        "original_script": "Stata/workshop_exercises/cond_mv_2020.do",
        "input_files": [
            "h220a (2020 PMED)",
            "h222 (2020 Conditions)",
            "h220if1 (2020 CLNK)",
            "h224 (2020 FYC)",
        ],
        "key_transformations": [
            "Filter conditions to hyperlipidemia (CCSR = END010)",
            "Merge conditions -> CLNK on CONDIDX (m:m)",
            "CRITICAL: duplicates drop evntidx, force",
            "Merge to PMED on EVNTIDX (1:m)",
            "Collapse to person-level (sum num_rx, exp_rx)",
            "Merge to FY, fill zeros, create any_rx flag",
            "Recode CHOLDX to HL_ever binary",
        ],
        "num_join_operations": 3,
        "survey_design": {
            "strata": "VARSTR",
            "cluster": "VARPSU",
            "weight": "PERWT20F",
        },
    }
