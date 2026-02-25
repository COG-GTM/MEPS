"""Exercise 2a: Antipsychotic Purchases and Expenses, 2015.

Migrated from: SAS/workshop_exercises/exercise_2a/Exercise2a.sas

Generates estimates on antipsychotic drug purchases and expenses, 2015:
  (1) Total expense for antipsychotics
  (2) Total number of purchases
  (3) Total number of persons purchasing 1+ antipsychotics
  (4) Average total, OOP, and third-party payer expense per person

Input files:
  - 2015 Full-Year Consolidated file (HC-181)
  - 2015 Prescribed Medicines file (HC-178A)

SAS → PySpark Migration Notes:
  - DATA step with TC filter → df.filter()
  - PROC SUMMARY NWAY CLASS  → groupBy().agg()
  - DATA step MERGE with IN=  → join with indicator
  - PROC SURVEYMEANS DOMAIN   → survey_mean_by_domain()
"""

from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean, survey_mean_by_domain


def identify_antipsychotics(
    spark: SparkSession,
    pmed_path: Optional[Path] = None,
    pmed_df: Optional[DataFrame] = None,
) -> DataFrame:
    """Identify antipsychotic drugs using TC codes (TC1=242, TC1S1=251).

    Args:
        spark: Active SparkSession.
        pmed_path: Path to H178A prescribed medicines file.
        pmed_df: Pre-loaded PMED DataFrame (for testing).

    Returns:
        DataFrame filtered to antipsychotic drug records.
    """
    if pmed_df is not None:
        df = pmed_df
    else:
        df = load_meps_data(spark, pmed_path)

    return df.filter(
        (F.col("TC1") == 242) & (F.col("TC1S1") == 251)
    )


def sum_to_person_level(drug_df: DataFrame) -> DataFrame:
    """Sum drug-level data to person-level expenditures.

    Replicates: PROC SUMMARY DATA=DRUG NWAY; CLASS DUPERSID;

    Args:
        drug_df: DataFrame of antipsychotic drug records.

    Returns:
        Person-level DataFrame with TOT, OOP, N_PHRCHASE, THIRD_PAYER.
    """
    perdrug = (
        drug_df.groupBy("DUPERSID")
        .agg(
            F.sum("RXXP15X").alias("TOT"),
            F.sum("RXSF15X").alias("OOP"),
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

    Replicates the SAS MERGE with IN= logic, setting zero values
    for persons without antipsychotic purchases.

    Args:
        spark: Active SparkSession.
        perdrug_df: Person-level drug expenditures.
        fyc_path: Path to H181 FYC file.
        fyc_df: Pre-loaded FYC DataFrame (for testing).

    Returns:
        Merged DataFrame with SUB flag for domain analysis.
    """
    if fyc_df is not None:
        fy = fyc_df
    else:
        columns = ["DUPERSID", "VARSTR", "VARPSU", "PERWT15F"]
        fy = load_meps_data(spark, fyc_path, columns)

    merged = fy.join(
        perdrug_df.select("DUPERSID", "N_PHRCHASE", "TOT", "OOP", "THIRD_PAYER"),
        on="DUPERSID",
        how="left",
    )

    # Set SUB flag and fill nulls
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
    """Calculate estimates on expenditures and use for antipsychotics.

    Replicates PROC SURVEYMEANS with DOMAIN SUB('1').

    Args:
        df: Merged FYC DataFrame with drug expenditure variables.

    Returns:
        DataFrame with domain estimates for persons with 1+ antipsychotic.
    """
    return survey_mean_by_domain(
        df,
        var_cols=["TOT", "N_PHRCHASE", "OOP", "THIRD_PAYER"],
        domain_col="SUB",
        domain_value=1,
        weight_col="PERWT15F",
    )


def run(
    spark: SparkSession,
    fyc_path: Optional[Path] = None,
    pmed_path: Optional[Path] = None,
    fyc_df: Optional[DataFrame] = None,
    pmed_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full Exercise 2a analysis pipeline.

    Args:
        spark: Active SparkSession.
        fyc_path: Path to H181 FYC file.
        pmed_path: Path to H178A PMED file.
        fyc_df: Pre-loaded FYC DataFrame (for testing).
        pmed_df: Pre-loaded PMED DataFrame (for testing).

    Returns:
        Dictionary with all analysis results.
    """
    drugs = identify_antipsychotics(spark, pmed_path, pmed_df)
    perdrug = sum_to_person_level(drugs)
    merged = merge_to_fyc(spark, perdrug, fyc_path, fyc_df)
    estimates = estimate_expenditures(merged)

    return {
        "antipsychotic_drugs": drugs,
        "person_level_drugs": perdrug,
        "merged_data": merged,
        "estimates": estimates,
    }
