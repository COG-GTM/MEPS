"""Exercise 2c: Narcotic Analgesics Purchases and Expenses, 2018.

Migrated from: SAS/workshop_exercises/exercise_2c/Exercise2c.sas

Generates national totals and per-person averages for narcotic analgesics
and narcotic analgesic combos, 2018:
  - Number of purchases (fills)
  - Total expenditures
  - Out-of-pocket payments
  - Third-party payments

Input files:
  - 2018 Prescribed medicines file (HC-206A)
  - 2018 Full-year consolidated file (HC-209)

SAS → PySpark Migration Notes:
  - DATA step with WHERE=(TC1S1_1 IN (60, 191)) → filter()
  - PROC SUMMARY NWAY → groupBy().agg()
  - RENAME= on SET → withColumnRenamed()
  - MERGE with IN= → join with indicator
  - PROC SURVEYMEANS DOMAIN SUBPOP → survey_mean_by_domain()
"""

from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean_by_domain


def identify_narcotics_2018(
    spark: SparkSession,
    pmed_path: Optional[Path] = None,
    pmed_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Identify narcotic analgesics using TC codes for 2018 data.

    Args:
        spark: Active SparkSession.
        pmed_path: Path to H206A prescribed medicines file.
        pmed_df: Pre-loaded PMED DataFrame (for testing).

    Returns:
        DataFrame filtered to narcotic analgesic records.
    """
    if pmed_df is not None:
        df = pmed_df
    else:
        columns = [
            "DUPERSID", "RXRECIDX", "LINKIDX", "TC1S1_1",
            "RXXP18X", "RXSF18X",
        ]
        df = load_meps_data(spark, pmed_path, columns)

    return df.filter(F.col("TC1S1_1").isin(60, 191))


def sum_to_person_level(drug_df: DataFrame) -> DataFrame:
    """Sum drug-level data to person-level expenditures for 2018.

    Args:
        drug_df: DataFrame of narcotic analgesic records.

    Returns:
        Person-level DataFrame with TOT, OOP, N_PHRCHASE, THIRD_PAYER.
    """
    perdrug = (
        drug_df.groupBy("DUPERSID")
        .agg(
            F.sum("RXXP18X").alias("TOT"),
            F.sum("RXSF18X").alias("OOP"),
            F.count("*").alias("N_PHRCHASE"),
        )
    )

    perdrug = perdrug.withColumn(
        "THIRD_PAYER", F.col("TOT") - F.col("OOP")
    )

    return perdrug


def merge_to_fyc(
    spark: SparkSession,
    perdrug_df: DataFrame,
    fyc_path: Optional[Path] = None,
    fyc_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Merge person-level drug expenditures to 2018 FYC file.

    Args:
        spark: Active SparkSession.
        perdrug_df: Person-level drug expenditures.
        fyc_path: Path to H209 FYC file.
        fyc_df: Pre-loaded FYC DataFrame (for testing).

    Returns:
        Merged DataFrame with SUBPOP flag.
    """
    if fyc_df is not None:
        fy = fyc_df
    else:
        columns = ["DUPERSID", "VARSTR", "VARPSU", "PERWT18F"]
        fy = load_meps_data(spark, fyc_path, columns)

    merged = fy.join(
        perdrug_df.select("DUPERSID", "N_PHRCHASE", "TOT", "OOP", "THIRD_PAYER"),
        on="DUPERSID",
        how="left",
    )

    merged = (
        merged
        .withColumn(
            "SUBPOP",
            F.when(F.col("TOT").isNotNull(), 1).otherwise(2)
        )
        .fillna(0, subset=["N_PHRCHASE", "TOT", "OOP", "THIRD_PAYER"])
    )

    return merged


def estimate_expenditures(df: DataFrame) -> DataFrame:
    """Calculate estimates on expenditures and use for 2018 narcotics.

    Args:
        df: Merged FYC DataFrame.

    Returns:
        DataFrame with domain estimates for SUBPOP=1.
    """
    return survey_mean_by_domain(
        df,
        var_cols=["N_PHRCHASE", "TOT", "OOP", "THIRD_PAYER"],
        domain_col="SUBPOP",
        domain_value=1,
        weight_col="PERWT18F",
    )


def run(
    spark: SparkSession,
    fyc_path: Optional[Path] = None,
    pmed_path: Optional[Path] = None,
    fyc_df: Optional[DataFrame] = None,
    pmed_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full Exercise 2c analysis pipeline.

    Args:
        spark: Active SparkSession.
        fyc_path: Path to H209 FYC file.
        pmed_path: Path to H206A PMED file.
        fyc_df: Pre-loaded FYC DataFrame (for testing).
        pmed_df: Pre-loaded PMED DataFrame (for testing).

    Returns:
        Dictionary with all analysis results.
    """
    drugs = identify_narcotics_2018(spark, pmed_path, pmed_df)
    perdrug = sum_to_person_level(drugs)
    merged = merge_to_fyc(spark, perdrug, fyc_path, fyc_df)
    estimates = estimate_expenditures(merged)

    return {
        "narcotic_drugs": drugs,
        "person_level_drugs": perdrug,
        "merged_data": merged,
        "estimates": estimates,
    }
