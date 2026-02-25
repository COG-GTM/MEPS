"""PySpark ETL migration of SAS/workshop_exercises/cond_pmed_2020.sas

Prescribed medicine utilization and expenditures for hyperlipidemia, 2020.

Original SAS logic (4-file join chain):
  1. Read PMED (h220a), Conditions (h222), CLNK (h220if1), FYC (h224)
  2. Filter conditions to hyperlipidemia (any CCSR = 'END010')
  3. Join Conditions -> CLNK on CONDIDX (many-to-many)
  4. De-duplicate on EVNTIDX (CRITICAL step to avoid double-counting)
  5. Join to PMED on EVNTIDX (1:many)
  6. Collapse to person level: count fills, sum expenditures
  7. Left join to FYC, fill zeros for non-matched persons
  8. Create hl_pmed_flag indicator

Input files:
  - h220a (2020 Prescribed Medicines)
  - h222 (2020 Conditions)
  - h220if1 (2020 CLNK: Condition-Event Link)
  - h224 (2020 Full-Year Consolidated)

Output: Person-level Parquet with rx fill counts and expenditures for hyperlipidemia
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
    """Execute the cond_pmed_2020 ETL pipeline.

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

    # --- Step 1: Read input files ---

    # PMED file (record = rx fill or refill for a person)
    pmed = spark.read.parquet(pmed_path)
    pmed = pmed.withColumnRenamed("LINKIDX", "EVNTIDX")
    pmed = pmed.select("DUPERSID", "DRUGIDX", "RXRECIDX", "EVNTIDX", "RXDRGNAM", "RXXP20X")

    # Conditions file (record = medical condition for a person)
    cond = spark.read.parquet(cond_path)
    cond = cond.select("DUPERSID", "CONDIDX", "ICD10CDX", "CCSR1X", "CCSR2X", "CCSR3X")

    # CLNK file (crosswalk between conditions and events)
    clnk = spark.read.parquet(clnk_path)

    # FYC file (person-level)
    fyc = spark.read.parquet(fyc_path)
    fyc = fyc.select(
        "DUPERSID", "AGELAST", "SEX", "CHOLDX", "POVCAT20",
        "VARSTR", "VARPSU", "PERWT20F",
    )

    # --- Step 2: Filter conditions to hyperlipidemia (CCSR = 'END010') ---
    hl_cond = cond.filter(
        (col("CCSR1X") == "END010")
        | (col("CCSR2X") == "END010")
        | (col("CCSR3X") == "END010")
    )
    checkpoints["hl_cond"] = hl_cond

    # --- Step 3: Join Conditions -> CLNK on CONDIDX (many-to-many) ---
    # Equivalent to SAS: merge hl (in=A) clnk20 (in=B); by dupersid condidx; if A and B;
    clnk_hl = hl_cond.join(clnk, on=["DUPERSID", "CONDIDX"], how="inner")
    checkpoints["clnk_hl"] = clnk_hl

    # --- Step 4: CRITICAL - De-duplicate on EVNTIDX ---
    # Equivalent to SAS: proc sort nodupkey; by dupersid evntidx;
    # This prevents double-counting when multiple HL conditions link to the same event
    clnk_hl_dedup = clnk_hl.dropDuplicates(["DUPERSID", "EVNTIDX"])
    checkpoints["clnk_hl_dedup"] = clnk_hl_dedup

    # --- Step 5: Join to PMED on EVNTIDX (1:many on EVNTIDX) ---
    # Equivalent to SAS: merge clnk_hl_dedup (in=a) pmed20 (in=b); by dupersid evntidx; if a and b;
    hl_merged = clnk_hl_dedup.join(pmed, on=["DUPERSID", "EVNTIDX"], how="inner")
    checkpoints["hl_merged"] = hl_merged

    # --- Step 6: Collapse to person level ---
    # Sum number of fills and expenditures per person
    drugs_by_pers = hl_merged.groupBy("DUPERSID").agg(
        count("*").alias("n_hl_fills"),
        spark_sum("RXXP20X").alias("hl_drug_exp"),
    )
    checkpoints["drugs_by_pers"] = drugs_by_pers

    # --- Step 7: Left join to FYC, fill zeros ---
    # Keep ALL FYC persons (need VARPSU/VARSTR for correct SEs)
    result = fyc.join(drugs_by_pers, on="DUPERSID", how="left")
    result = result.fillna({"n_hl_fills": 0, "hl_drug_exp": 0.0})

    # Create flag for persons with any PMED fills for hyperlipidemia
    result = result.withColumn(
        "hl_pmed_flag",
        when(col("n_hl_fills") > 0, lit(1)).otherwise(lit(0)),
    )
    checkpoints["result"] = result

    # Write output
    result.write.mode("overwrite").parquet(output_path)

    return checkpoints


def get_job_metadata() -> dict:
    """Return metadata about this ETL job."""
    return {
        "job_name": "cond_pmed_2020",
        "description": "Prescribed medicine utilization/expenditures for hyperlipidemia, 2020",
        "complexity_tier": "High",
        "original_script": "SAS/workshop_exercises/cond_pmed_2020.sas",
        "input_files": [
            "h220a (2020 PMED)",
            "h222 (2020 Conditions)",
            "h220if1 (2020 CLNK)",
            "h224 (2020 FYC)",
        ],
        "key_transformations": [
            "Filter conditions to hyperlipidemia (CCSR = END010)",
            "Join Conditions -> CLNK on CONDIDX (many-to-many)",
            "CRITICAL: De-duplicate on DUPERSID+EVNTIDX",
            "Join to PMED on EVNTIDX",
            "Collapse to person-level (sum fills and expenditures)",
            "Left join to FYC, fill zeros for non-matched",
            "Create hl_pmed_flag indicator",
        ],
        "num_join_operations": 3,
        "survey_design": {
            "strata": "VARSTR",
            "cluster": "VARPSU",
            "weight": "PERWT20F",
        },
    }
