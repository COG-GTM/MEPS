"""Exercise 2b: Narcotic Analgesics Purchases and Expenses, 2016.

Migrated from: SAS/workshop_exercises/exercise_2b/Exercise2b.sas

Generates estimates on narcotic analgesic purchases and expenses, 2016:
  (1) Total expense for narcotic analgesics
  (2) Total number of purchases
  (3) Total number of persons purchasing 1+ narcotic analgesics
  (4) Average total, OOP, and third-party payer expense per person

Input files:
  - 2016 Full-Year Consolidated file (HC-192)
  - 2016 Prescribed Medicines file (HC-188A)

SAS → PySpark Migration Notes:
  - TC1S1_1 IN (60, 191) filter → df.filter(col.isin())
  - ODS OUTPUT DOMAIN → collect domain results
"""

from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean_by_domain


def identify_narcotics(
    spark: SparkSession,
    pmed_path: Optional[Path] = None,
    pmed_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Identify narcotic analgesics using TC codes (TC1S1_1 IN (60, 191)).

    Args:
        spark: Active SparkSession.
        pmed_path: Path to H188A prescribed medicines file.
        pmed_df: Pre-loaded PMED DataFrame (for testing).

    Returns:
        DataFrame filtered to narcotic analgesic records.
    """
    if pmed_df is not None:
        df = pmed_df
    else:
        df = load_meps_data(spark, pmed_path)

    return df.filter(F.col("TC1S1_1").isin(60, 191))


def sum_to_person_level(drug_df: DataFrame) -> DataFrame:
    """Sum drug-level data to person-level expenditures.

    Args:
        drug_df: DataFrame of narcotic analgesic records.

    Returns:
        Person-level DataFrame with TOT, OOP, N_PHRCHASE, THIRD_PAYER.
    """
    perdrug = (
        drug_df.groupBy("DUPERSID")
        .agg(
            F.sum("RXXP16X").alias("TOT"),
            F.sum("RXSF16X").alias("OOP"),
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
    """Merge person-level drug expenditures to FYC file.

    Args:
        spark: Active SparkSession.
        perdrug_df: Person-level drug expenditures.
        fyc_path: Path to H192 FYC file.
        fyc_df: Pre-loaded FYC DataFrame (for testing).

    Returns:
        Merged DataFrame with SUB flag.
    """
    if fyc_df is not None:
        fy = fyc_df
    else:
        columns = ["DUPERSID", "VARSTR", "VARPSU", "PERWT16F"]
        fy = load_meps_data(spark, fyc_path, columns)

    merged = fy.join(
        perdrug_df.select("DUPERSID", "N_PHRCHASE", "TOT", "OOP", "THIRD_PAYER"),
        on="DUPERSID",
        how="left",
    )

    merged = (
        merged
        .withColumn(
            "SUB",
            F.when(F.col("TOT").isNotNull(), 1).otherwise(2)
        )
        .fillna(0, subset=["N_PHRCHASE", "TOT", "OOP", "THIRD_PAYER"])
    )

    return merged


def estimate_expenditures(df: DataFrame) -> DataFrame:
    """Calculate estimates on expenditures and use for narcotic analgesics.

    Args:
        df: Merged FYC DataFrame.

    Returns:
        DataFrame with domain estimates.
    """
    return survey_mean_by_domain(
        df,
        var_cols=["TOT", "N_PHRCHASE", "OOP", "THIRD_PAYER"],
        domain_col="SUB",
        domain_value=1,
        weight_col="PERWT16F",
    )


def run(
    spark: SparkSession,
    fyc_path: Optional[Path] = None,
    pmed_path: Optional[Path] = None,
    fyc_df: Optional[DataFrame] = None,
    pmed_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full Exercise 2b analysis pipeline.

    Args:
        spark: Active SparkSession.
        fyc_path: Path to H192 FYC file.
        pmed_path: Path to H188A PMED file.
        fyc_df: Pre-loaded FYC DataFrame (for testing).
        pmed_df: Pre-loaded PMED DataFrame (for testing).

    Returns:
        Dictionary with all analysis results.
    """
    drugs = identify_narcotics(spark, pmed_path, pmed_df)
    perdrug = sum_to_person_level(drugs)
    merged = merge_to_fyc(spark, perdrug, fyc_path, fyc_df)
    estimates = estimate_expenditures(merged)

    return {
        "narcotic_drugs": drugs,
        "person_level_drugs": perdrug,
        "merged_data": merged,
        "estimates": estimates,
    }
