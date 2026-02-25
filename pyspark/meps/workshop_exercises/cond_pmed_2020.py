"""Linking Conditions to Prescribed Medicines: Hyperlipidemia, 2020.

Migrated from: SAS/workshop_exercises/cond_pmed_2020.sas

Links MEPS-HC Medical Conditions file to Prescribed Medicines file for
data year 2020 to estimate:

National totals:
  - Total number of people with at least one PMED fill for hyperlipidemia
  - Total PMED fills for hyperlipidemia
  - Total PMED expenditures for hyperlipidemia

Per-person averages among people with at least one PMED fill for HL:
  - Avg PMED fills for HL, by sex and poverty (POVCAT20)
  - Avg PMED expenditures for HL, by sex and poverty (POVCAT20)

Input files:
  - h220a.sas7bdat  (2020 Prescribed Medicines file)
  - h222.sas7bdat   (2020 Conditions file)
  - h220if1.sas7bdat (2020 CLNK: Condition-Event Link file)
  - h224.sas7bdat   (2020 Full-Year Consolidated file)

SAS → PySpark Migration Notes:
  - EVNTIDX = LINKIDX rename            → withColumnRenamed()
  - PROC SORT NODUPKEY                   → dropDuplicates()
  - MERGE with IN= flags                → join with indicator
  - PROC MEANS NWAY SUM                 → groupBy().agg()
  - Missing to zero after merge          → fillna()
  - PROC SURVEYMEANS SUM                 → survey_mean() with sum
  - PROC SURVEYMEANS DOMAIN with *      → survey_mean_by_domain() with by_col
"""

from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean, survey_mean_by_domain


def identify_hyperlipidemia(
    cond_df: DataFrame,
) -> DataFrame:
    """Subset conditions to hyperlipidemia (CCSR = 'END010').

    Args:
        cond_df: Conditions DataFrame with CCSR columns.

    Returns:
        DataFrame filtered to hyperlipidemia conditions.
    """
    return cond_df.filter(
        (F.col("CCSR1X") == "END010")
        | (F.col("CCSR2X") == "END010")
        | (F.col("CCSR3X") == "END010")
    )


def link_conditions_to_pmeds(
    hl_df: DataFrame,
    clnk_df: DataFrame,
    pmed_df: DataFrame,
) -> DataFrame:
    """Link hyperlipidemia conditions to prescribed medicine events.

    Steps:
      1. Merge HL conditions with CLNK by DUPERSID + CONDIDX
      2. De-duplicate by DUPERSID + EVNTIDX
      3. Merge with PMED file to get drug details

    Args:
        hl_df: Hyperlipidemia conditions DataFrame.
        clnk_df: Condition-Event link DataFrame.
        pmed_df: Prescribed medicines DataFrame.

    Returns:
        DataFrame at PMED FILL level linked to hyperlipidemia.
    """
    # Merge conditions with CLNK
    clnk_hl = hl_df.select("DUPERSID", "CONDIDX").join(
        clnk_df.select("DUPERSID", "CONDIDX", "EVNTIDX"),
        on=["DUPERSID", "CONDIDX"],
        how="inner",
    )

    # De-duplicate by DUPERSID + EVNTIDX
    clnk_hl_dedup = clnk_hl.dropDuplicates(["DUPERSID", "EVNTIDX"])

    # Prepare PMED with EVNTIDX (rename LINKIDX)
    pmed_with_evntidx = pmed_df
    if "LINKIDX" in pmed_df.columns and "EVNTIDX" not in pmed_df.columns:
        pmed_with_evntidx = pmed_df.withColumnRenamed("LINKIDX", "EVNTIDX")

    # Merge with PMED
    hl_merged = clnk_hl_dedup.select("DUPERSID", "EVNTIDX").join(
        pmed_with_evntidx,
        on=["DUPERSID", "EVNTIDX"],
        how="inner",
    )

    return hl_merged


def aggregate_to_person_level(hl_merged_df: DataFrame) -> DataFrame:
    """Roll up PMED fills to person level.

    Creates:
      - N_HL_FILLS: Total number of fills for HL per person
      - HL_DRUG_EXP: Total PMED expenditures for HL per person

    Args:
        hl_merged_df: Fill-level DataFrame linked to hyperlipidemia.

    Returns:
        Person-level DataFrame with fill counts and expenditures.
    """
    return (
        hl_merged_df.groupBy("DUPERSID")
        .agg(
            F.count("*").alias("N_HL_FILLS"),
            F.sum("RXXP20X").alias("HL_DRUG_EXP"),
        )
    )


def merge_to_fyc(
    fyc_df: DataFrame,
    drugs_by_pers_df: DataFrame,
) -> DataFrame:
    """Merge person-level drug totals to FYC and create HL PMED flag.

    Args:
        fyc_df: Full-year consolidated DataFrame.
        drugs_by_pers_df: Person-level drug totals.

    Returns:
        Merged DataFrame with HL_PMED_FLAG.
    """
    merged = fyc_df.join(drugs_by_pers_df, on="DUPERSID", how="left")

    # Create flag and fill missings
    merged = (
        merged
        .withColumn(
            "HL_PMED_FLAG",
            F.when(F.col("N_HL_FILLS") > 0, 1).otherwise(0)
        )
        .fillna(0, subset=["N_HL_FILLS", "HL_DRUG_EXP"])
    )

    return merged


def estimate_national_totals(df: DataFrame) -> DataFrame:
    """Estimate national totals for HL PMED use.

    Replicates: PROC SURVEYMEANS SUM; VAR hl_pmed_flag n_hl_fills hl_drug_exp;

    Args:
        df: Merged FYC DataFrame.

    Returns:
        DataFrame with national total estimates.
    """
    return survey_mean(
        df,
        var_cols=["HL_PMED_FLAG", "N_HL_FILLS", "HL_DRUG_EXP"],
        weight_col="PERWT20F",
    )


def estimate_per_person_means(df: DataFrame) -> DataFrame:
    """Estimate per-person averages among people with HL PMED fills.

    Replicates: PROC SURVEYMEANS DOMAIN hl_pmed_flag('1')
                hl_pmed_flag('1')*sex hl_pmed_flag('1')*povcat20;

    Args:
        df: Merged FYC DataFrame.

    Returns:
        Dictionary with per-person mean estimates.
    """
    overall = survey_mean_by_domain(
        df,
        var_cols=["N_HL_FILLS", "HL_DRUG_EXP"],
        domain_col="HL_PMED_FLAG",
        domain_value=1,
        weight_col="PERWT20F",
    )

    by_sex = survey_mean_by_domain(
        df,
        var_cols=["N_HL_FILLS", "HL_DRUG_EXP"],
        domain_col="HL_PMED_FLAG",
        domain_value=1,
        weight_col="PERWT20F",
        by_col="SEX",
    )

    by_poverty = survey_mean_by_domain(
        df,
        var_cols=["N_HL_FILLS", "HL_DRUG_EXP"],
        domain_col="HL_PMED_FLAG",
        domain_value=1,
        weight_col="PERWT20F",
        by_col="POVCAT20",
    )

    return {
        "overall": overall,
        "by_sex": by_sex,
        "by_poverty": by_poverty,
    }


def run(
    spark: SparkSession,
    pmed_df: Optional[DataFrame] = None,
    cond_df: Optional[DataFrame] = None,
    clnk_df: Optional[DataFrame] = None,
    fyc_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full cond_pmed_2020 analysis pipeline.

    Args:
        spark: Active SparkSession.
        pmed_df: Prescribed medicines DataFrame.
        cond_df: Conditions DataFrame.
        clnk_df: Condition-Event link DataFrame.
        fyc_df: Full-year consolidated DataFrame.

    Returns:
        Dictionary with all analysis results.
    """
    hl = identify_hyperlipidemia(cond_df)
    hl_merged = link_conditions_to_pmeds(hl, clnk_df, pmed_df)
    drugs_by_pers = aggregate_to_person_level(hl_merged)
    fyc_hl = merge_to_fyc(fyc_df, drugs_by_pers)
    totals = estimate_national_totals(fyc_hl)
    means = estimate_per_person_means(fyc_hl)

    return {
        "hyperlipidemia_conditions": hl,
        "hl_pmed_fills": hl_merged,
        "person_level_drugs": drugs_by_pers,
        "fyc_with_hl": fyc_hl,
        "national_totals": totals,
        "per_person_means": means,
    }
