"""Linking Conditions to Office-Based Visits: Mental Health, 2020.

Migrated from: SAS/workshop_exercises/cond_mv_2020.sas

Links MEPS-HC Medical Conditions file to Office-based medical visits file
for data year 2020 to estimate:

Event-level estimates:
  - Number of office-based visits for mental health
  - Total expenditures for office-based mental health treatment
  - Mean expenditure per office-based mental health visit

Person-level estimates:
  - Number of people with office-based mental health visits
  - Percent of people with office-based mental health visits
  - Mean expenditure per person for office-based mental health visits

Input files:
  - h220g.sas7bdat   (2020 Office-based event file)
  - h222.sas7bdat    (2020 Conditions file)
  - h220if1.sas7bdat (2020 CLNK: Condition-event link file)
  - h224.sas7bdat    (2020 Full-Year Consolidated file)

SAS → PySpark Migration Notes:
  - CAT(CCSR1X,CCSR2X,CCSR3X) CONTAINS 'MBD' → concat + contains
  - EVENTYPE = 1 filter                        → filter()
  - MERGE with indicators                      → join with flags
  - PROC MEANS NOPRINT BY                      → groupBy().agg()
  - PROC SURVEYMEANS DOMAIN mh_ob              → survey_mean_by_domain()
"""

from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.data_loader import load_meps_data
from meps.utils.survey_stats import survey_mean, survey_mean_by_domain


# Mental health CCSR codes
MH_CCSR_CODES = ["MBD", "FAC002", "FAC007", "NVS011", "SYM008", "SYM009"]


def identify_mental_health_conditions(cond_df: DataFrame) -> DataFrame:
    """Filter conditions to mental health disorders.

    Uses CCSR codes containing MBD, FAC002, FAC007, NVS011, SYM008, SYM009.

    Args:
        cond_df: Conditions DataFrame.

    Returns:
        DataFrame filtered to mental health conditions.
    """
    # Concatenate all CCSR columns
    all_ccsr_cols = []
    for col_name in ["CCSR1X", "CCSR2X", "CCSR3X"]:
        if col_name in cond_df.columns:
            all_ccsr_cols.append(col_name)

    if not all_ccsr_cols:
        return cond_df.limit(0)

    df = cond_df.withColumn(
        "ALL_CCSR",
        F.concat_ws("", *[F.coalesce(F.col(c), F.lit("")) for c in all_ccsr_cols])
    )

    # Build OR filter for all MH codes
    condition = F.lit(False)
    for code in MH_CCSR_CODES:
        condition = condition | F.col("ALL_CCSR").contains(code)

    return df.filter(condition)


def filter_ob_events_from_clnk(clnk_df: DataFrame) -> DataFrame:
    """Filter CLNK file to only office-based visit events (EVENTYPE=1).

    Args:
        clnk_df: Condition-event link DataFrame.

    Returns:
        DataFrame filtered to office-based events.
    """
    return clnk_df.filter(F.col("EVENTYPE") == 1)


def link_mh_to_ob_events(
    mh_df: DataFrame,
    clnk_ob_df: DataFrame,
    ob_df: DataFrame,
) -> DataFrame:
    """Link mental health conditions to office-based visit events.

    Steps:
      1. Merge MH conditions with OB-filtered CLNK
      2. De-duplicate by DUPERSID + EVNTIDX
      3. Merge with OB event file for expenditure data

    Args:
        mh_df: Mental health conditions DataFrame.
        clnk_ob_df: CLNK filtered to office-based events.
        ob_df: Office-based visits DataFrame.

    Returns:
        DataFrame of OB events linked to mental health conditions.
    """
    # Merge conditions with CLNK
    mh_clnk = mh_df.select("DUPERSID", "CONDIDX").join(
        clnk_ob_df.select("DUPERSID", "CONDIDX", "EVNTIDX", "EVENTYPE"),
        on=["DUPERSID", "CONDIDX"],
        how="inner",
    )

    # De-duplicate by event
    mh_clnk_nodup = mh_clnk.select(
        "DUPERSID", "EVNTIDX", "EVENTYPE"
    ).dropDuplicates(["DUPERSID", "EVNTIDX", "EVENTYPE"])

    # Merge with OB event file
    ob_mh = mh_clnk_nodup.join(
        ob_df,
        on=["DUPERSID", "EVNTIDX"],
        how="inner",
    )

    # Add indicator variable
    ob_mh = ob_mh.withColumn("MH_OB_VISIT", F.lit(1))

    return ob_mh


def merge_with_fyc(
    ob_mh_df: DataFrame,
    fyc_df: DataFrame,
) -> DataFrame:
    """Merge OB mental health events with FYC for complete survey design.

    This step is CRITICAL for correct standard errors - must include
    all strata and PSUs from the full MEPS sample.

    Args:
        ob_mh_df: Office-based mental health events.
        fyc_df: Full-year consolidated DataFrame.

    Returns:
        Merged DataFrame with complete survey design variables.
    """
    # Add flag column before merge
    ob_mh_flagged = ob_mh_df.withColumn("MH_OB", F.lit(1))

    # Drop columns from ob_mh that overlap with FYC to avoid ambiguous refs
    cols_to_keep = ["DUPERSID", "EVNTIDX", "EVENTYPE", "MH_OB_VISIT", "MH_OB"]
    if "OBXP20X" in ob_mh_flagged.columns:
        cols_to_keep.append("OBXP20X")
    ob_mh_flagged = ob_mh_flagged.select(
        [c for c in cols_to_keep if c in ob_mh_flagged.columns]
    )

    merged = fyc_df.join(
        ob_mh_flagged,
        on="DUPERSID",
        how="left",
    )

    # Reset missing indicators to 0
    merged = (
        merged
        .withColumn("MH_OB", F.when(F.col("MH_OB").isNull(), 0).otherwise(F.col("MH_OB")))
        .withColumn(
            "MH_OB_VISIT",
            F.when(F.col("MH_OB_VISIT").isNull(), 0).otherwise(F.col("MH_OB_VISIT"))
        )
    )

    return merged


def aggregate_to_person_level(ob_mh_fyc_df: DataFrame) -> DataFrame:
    """Aggregate event-level data to person level.

    Creates per-person totals:
      - PERSXP: Total expenditures for OB MH visits
      - PERS_NEVENTS: Number of OB MH visits
      - MH_OB_VISIT_PERS: Flag for any OB MH visit
      - MH_OB_PERS: Flag for any MH condition

    Args:
        ob_mh_fyc_df: Merged event-level DataFrame.

    Returns:
        Person-level DataFrame.
    """
    exp_col = "OBXP20X" if "OBXP20X" in ob_mh_fyc_df.columns else None

    agg_exprs = [
        F.mean("PERWT20F").alias("PERWT20F"),
        F.sum("MH_OB_VISIT").alias("PERS_NEVENTS"),
        F.mean("MH_OB_VISIT").alias("MH_OB_VISIT_PERS"),
        F.mean("MH_OB").alias("MH_OB_PERS"),
    ]

    if exp_col:
        agg_exprs.append(F.sum(exp_col).alias("PERSXP"))

    return (
        ob_mh_fyc_df
        .groupBy("DUPERSID", "VARSTR", "VARPSU")
        .agg(*agg_exprs)
    )


def estimate_event_level(df: DataFrame) -> DataFrame:
    """Estimate event-level statistics for OB mental health visits.

    Uses DOMAIN mh_ob for correct lonely PSU handling.

    Args:
        df: Event-level merged DataFrame.

    Returns:
        DataFrame with event-level estimates.
    """
    var_cols = ["MH_OB_VISIT"]
    if "OBXP20X" in df.columns:
        var_cols.append("OBXP20X")

    return survey_mean_by_domain(
        df,
        var_cols=var_cols,
        domain_col="MH_OB",
        domain_value=1,
        weight_col="PERWT20F",
    )


def estimate_person_level(pers_df: DataFrame) -> DataFrame:
    """Estimate person-level statistics for OB mental health.

    Args:
        pers_df: Person-level aggregated DataFrame.

    Returns:
        DataFrame with person-level estimates.
    """
    var_cols = ["MH_OB_VISIT_PERS", "PERS_NEVENTS"]
    if "PERSXP" in pers_df.columns:
        var_cols.append("PERSXP")

    return survey_mean_by_domain(
        pers_df,
        var_cols=var_cols,
        domain_col="MH_OB_PERS",
        domain_value=1,
        weight_col="PERWT20F",
    )


def run(
    spark: SparkSession,
    ob_df: Optional[DataFrame] = None,
    cond_df: Optional[DataFrame] = None,
    clnk_df: Optional[DataFrame] = None,
    fyc_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full cond_mv_2020 analysis pipeline.

    Args:
        spark: Active SparkSession.
        ob_df: Office-based visits DataFrame.
        cond_df: Conditions DataFrame.
        clnk_df: Condition-event link DataFrame.
        fyc_df: Full-year consolidated DataFrame.

    Returns:
        Dictionary with all analysis results.
    """
    mh = identify_mental_health_conditions(cond_df)
    clnk_ob = filter_ob_events_from_clnk(clnk_df)
    ob_mh = link_mh_to_ob_events(mh, clnk_ob, ob_df)
    ob_mh_fyc = merge_with_fyc(ob_mh, fyc_df)

    event_estimates = estimate_event_level(ob_mh_fyc)

    pers_mh = aggregate_to_person_level(ob_mh_fyc)
    person_estimates = estimate_person_level(pers_mh)

    return {
        "mental_health_conditions": mh,
        "ob_mental_health_events": ob_mh,
        "merged_event_data": ob_mh_fyc,
        "person_level_data": pers_mh,
        "event_level_estimates": event_estimates,
        "person_level_estimates": person_estimates,
    }
