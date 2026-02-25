"""Summary Table: Medical Conditions Expenditures, 2015.

Migrated from: SAS/summary_tables_examples/cond_expenditures_2015.sas

Medical Conditions, 2015:
  - Number of people with care
  - Number of events
  - Total expenditures
  - Mean expenditure per person

Uses CCS codes (pre-2016 ICD-9 classification).
Condition-event linking via CLNK file.

Input files:
  - 2015 event files (RX, IP, ER, OP, OB, HH)
  - 2015 CLNK file
  - 2015 Conditions file
"""

from typing import Dict, Optional

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.functions as F

from meps.utils.survey_stats import survey_mean


# CCS code to collapsed condition mapping
CCS_CONDITION_MAP = {
    range(1, 10): "Infectious diseases",
    range(11, 46): "Cancer",
    (46, 47): "Non-malignant neoplasm",
    (48,): "Thyroid disease",
    (49, 50): "Diabetes mellitus",
    (53,): "Hyperlipidemia",
    (59,): "Anemia and other deficiencies",
    (84,): "Headache",
    (86,): "Cataract",
    (88,): "Glaucoma",
    (92,): "Otitis media",
    (98, 99): "Hypertension",
    (122,): "Pneumonia",
    (123,): "Influenza",
    (124,): "Tonsillitis",
    (135,): "Intestinal infection",
    (136,): "Disorders of teeth and jaws",
    (137,): "Disorders of mouth and esophagus",
    (142,): "Appendicitis",
    (143,): "Hernias",
    (159,): "Urinary tract infections",
    (167,): "Non-malignant breast disease",
    (205,): "Back problems",
    (259,): "Residual Codes",
    (253,): "Allergic reactions",
}


def map_ccs_to_condition(ccs_code: int) -> str:
    """Map CCS code to collapsed condition category."""
    for key, label in CCS_CONDITION_MAP.items():
        if isinstance(key, range):
            if ccs_code in key:
                return label
        elif ccs_code in key:
            return label
    return "Other"


def stack_events(event_dfs: Dict[str, DataFrame], year: str = "15") -> DataFrame:
    """Stack all event files into one DataFrame with standardized columns.

    For RX events, aggregates fills per LINKIDX first.

    Args:
        event_dfs: Dict of event DataFrames keyed by type (RX, IP, ER, OP, OB, HH).
        year: Year suffix (e.g., "15").

    Returns:
        Combined DataFrame with EVNTIDX, XP, n_events columns.
    """
    stacked_parts = []

    for event_type, df in event_dfs.items():
        if event_type == "RX":
            # Aggregate fills per LINKIDX
            rx_agg = (
                df.groupBy("DUPERSID", "LINKIDX", "VARSTR", "VARPSU", f"PERWT{year}F")
                .agg(
                    F.sum(f"RXXP{year}X").alias("XP"),
                    F.count("*").alias("N_FILLS"),
                )
                .withColumnRenamed("LINKIDX", "EVNTIDX")
                .withColumn("N_EVENTS", F.col("N_FILLS"))
                .withColumn("EVENT_TYPE", F.lit("RX"))
            )
            stacked_parts.append(rx_agg)
        else:
            exp_col_map = {"IP": "IPXP", "ER": "ERXP", "OP": "OPXP", "OB": "OBXP", "HH": "HHXP"}
            exp_col = f"{exp_col_map.get(event_type, event_type + 'XP')}{year}X"

            evt = df.select(
                "DUPERSID", "EVNTIDX", "VARSTR", "VARPSU", f"PERWT{year}F",
                F.col(exp_col).alias("XP") if exp_col in df.columns else F.lit(0).alias("XP"),
            ).withColumn("N_EVENTS", F.lit(1)).withColumn("EVENT_TYPE", F.lit(event_type))

            stacked_parts.append(evt)

    result = stacked_parts[0]
    for part in stacked_parts[1:]:
        common_cols = list(set(result.columns) & set(part.columns))
        result = result.select(common_cols).union(part.select(common_cols))

    return result


def link_conditions_to_events(
    stacked_df: DataFrame,
    clnk_df: DataFrame,
    cond_df: DataFrame,
) -> DataFrame:
    """Link conditions to events via CLNK file.

    Args:
        stacked_df: Stacked events DataFrame.
        clnk_df: Condition-event link DataFrame.
        cond_df: Conditions DataFrame.

    Returns:
        Events linked to condition categories.
    """
    # Merge conditions with CLNK
    cond_clnk = clnk_df.select("DUPERSID", "CONDIDX", "EVNTIDX").join(
        cond_df.select("DUPERSID", "CONDIDX", "CCCODEX"),
        on=["DUPERSID", "CONDIDX"],
        how="inner",
    )

    # De-duplicate by DUPERSID + EVNTIDX + CCCODEX
    cond_clnk = cond_clnk.dropDuplicates(["DUPERSID", "EVNTIDX", "CCCODEX"])

    # Merge with events
    all_events = stacked_df.join(
        cond_clnk.select("DUPERSID", "EVNTIDX", "CCCODEX"),
        on=["DUPERSID", "EVNTIDX"],
        how="inner",
    )

    # Filter to valid conditions and non-negative expenditures
    all_events = all_events.filter(
        (F.col("CCCODEX").isNotNull()) & (F.col("XP") >= 0)
    )

    return all_events


def aggregate_to_person(all_events_df: DataFrame, year: str = "15") -> DataFrame:
    """Aggregate event-level data to person-condition level.

    Args:
        all_events_df: Event-level DataFrame linked to conditions.
        year: Year suffix.

    Returns:
        Person-condition level DataFrame.
    """
    return (
        all_events_df
        .groupBy("DUPERSID", "VARSTR", "VARPSU", "CCCODEX")
        .agg(
            F.mean(f"PERWT{year}F").alias(f"PERWT{year}F"),
            F.sum("XP").alias("PERS_XP"),
            F.sum("N_EVENTS").alias("N_EVENTS"),
        )
        .withColumn("PERSON", F.lit(1))
    )


def run(
    spark: SparkSession,
    event_dfs: Optional[Dict[str, DataFrame]] = None,
    clnk_df: Optional[DataFrame] = None,
    cond_df: Optional[DataFrame] = None,
) -> dict:
    """Execute the full analysis pipeline."""
    stacked = stack_events(event_dfs, "15")
    linked = link_conditions_to_events(stacked, clnk_df, cond_df)
    person_level = aggregate_to_person(linked, "15")

    estimates = survey_mean(
        person_level,
        var_cols=["PERSON", "N_EVENTS", "PERS_XP"],
        weight_col="PERWT15F",
    )

    return {
        "stacked_events": stacked,
        "linked_events": linked,
        "person_level": person_level,
        "estimates": estimates,
    }
