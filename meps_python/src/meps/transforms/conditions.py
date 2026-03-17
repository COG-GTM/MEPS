"""Condition code crosswalk and condition-event linkage logic.

Handles:
  - ICD-9/CCS crosswalk (1996-2015)
  - ICD-10/CCSR crosswalk (2016+)
  - Condition-event linkage via CLNK file
  - 6-event-file stacking pattern
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import polars as pl


def _find_reference_file(filename: str) -> Path:
    """Locate a Quick_Reference_Guides file."""
    candidates = [
        Path(__file__).resolve().parents[4] / ".." / "Quick_Reference_Guides" / filename,
        Path(__file__).resolve().parents[5] / "Quick_Reference_Guides" / filename,
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"Could not find {filename} in Quick_Reference_Guides/")


def load_ccs_crosswalk(csv_path: Optional[str] = None) -> pl.DataFrame:
    """Load ICD-9/CCS to MEPS condition category crosswalk (for data years 1996-2015).

    Args:
        csv_path: Path to meps_ccs_conditions.csv. Auto-detected if None.

    Returns:
        DataFrame with columns: CCS_code, CCS_desc, Condition (MEPS collapsed category).
    """
    if csv_path is None:
        csv_path = str(_find_reference_file("meps_ccs_conditions.csv"))

    df = pl.read_csv(csv_path)
    # Standardize column names
    cols = df.columns
    if len(cols) >= 3:
        df = df.rename({cols[0]: "CCS", cols[1]: "CCS_desc", cols[2]: "Condition"})
    return df


def load_ccsr_crosswalk(csv_path: Optional[str] = None) -> pl.DataFrame:
    """Load ICD-10/CCSR to MEPS condition category crosswalk (for data years 2016+).

    Args:
        csv_path: Path to meps_ccsr_conditions.csv. Auto-detected if None.

    Returns:
        DataFrame with columns: CCSR, CCSR_desc, Condition (MEPS collapsed category).
    """
    if csv_path is None:
        csv_path = str(_find_reference_file("meps_ccsr_conditions.csv"))

    df = pl.read_csv(csv_path)
    cols = df.columns
    if len(cols) >= 3:
        df = df.rename({cols[0]: "CCSR", cols[1]: "CCSR_desc", cols[2]: "Condition"})
    return df


def link_conditions_events(
    conditions: pl.DataFrame,
    clnk: pl.DataFrame,
    events: pl.DataFrame,
    condition_filter: Optional[pl.Expr] = None,
    event_type_filter: Optional[int] = None,
    dedup_by: list[str] | None = None,
) -> pl.DataFrame:
    """Link medical conditions to healthcare events via the CLNK file.

    Implements the standard MEPS condition-event linkage pattern:
    1. Filter conditions (optional)
    2. Filter CLNK to event type (optional)
    3. Inner join conditions with CLNK on (DUPERSID, CONDIDX)
    4. De-duplicate by EVNTIDX to prevent double-counting
    5. Inner join with events on (DUPERSID, EVNTIDX)

    See R/workshop_exercises/cond_mv_2020.R lines 148-181.

    Args:
        conditions: Medical Conditions file (COND).
        clnk: Condition-event link file (CLNK).
        events: Event file(s) (OB, IP, ER, OP, RX, HH).
        condition_filter: Optional polars expression to filter conditions.
        event_type_filter: Optional EVENTYPE value to filter CLNK.
        dedup_by: Columns to de-duplicate by. Defaults to ['DUPERSID', 'EVNTIDX'].

    Returns:
        Linked DataFrame with condition and event data.
    """
    if dedup_by is None:
        dedup_by = ["DUPERSID", "EVNTIDX"]

    # Step 1: Filter conditions
    cond = conditions
    if condition_filter is not None:
        cond = cond.filter(condition_filter)

    # Step 2: Filter CLNK by event type
    clnk_filtered = clnk
    if event_type_filter is not None and "EVENTYPE" in clnk.columns:
        clnk_filtered = clnk_filtered.filter(pl.col("EVENTYPE") == event_type_filter)

    # Step 3: Merge conditions with CLNK
    join_cols_cond = ["DUPERSID", "CONDIDX"]
    available_join = [c for c in join_cols_cond if c in cond.columns and c in clnk_filtered.columns]
    cond_clnk = cond.join(clnk_filtered, on=available_join, how="inner")

    # Step 4: De-duplicate
    available_dedup = [c for c in dedup_by if c in cond_clnk.columns]
    if available_dedup:
        cond_clnk = cond_clnk.unique(subset=available_dedup, keep="first")

    # Step 5: Merge with events
    join_cols_evt = ["DUPERSID", "EVNTIDX"]
    available_evt_join = [c for c in join_cols_evt if c in cond_clnk.columns and c in events.columns]
    result = events.join(cond_clnk, on=available_evt_join, how="inner")

    return result


def filter_conditions_by_ccsr(
    conditions: pl.DataFrame,
    ccsr_codes: list[str],
) -> pl.DataFrame:
    """Filter conditions file by CCSR codes (checking CCSR1X, CCSR2X, CCSR3X).

    Equivalent to R:
        cond %>% filter(grepl("MBD|FAC002", paste(CCSR1X, CCSR2X, CCSR3X)))

    Args:
        conditions: Conditions DataFrame with CCSR1X, CCSR2X, CCSR3X columns.
        ccsr_codes: List of CCSR code prefixes to match.

    Returns:
        Filtered DataFrame.
    """
    ccsr_cols = [c for c in ["CCSR1X", "CCSR2X", "CCSR3X"] if c in conditions.columns]
    if not ccsr_cols:
        raise ValueError("No CCSR columns found in conditions data")

    # Build filter expression: any CCSR column starts with any of the codes
    filter_expr = pl.lit(False)
    for col in ccsr_cols:
        for code in ccsr_codes:
            filter_expr = filter_expr | pl.col(col).cast(pl.Utf8).str.starts_with(code)

    return conditions.filter(filter_expr)


def filter_conditions_by_ccsr_pattern(
    conditions: pl.DataFrame,
    pattern: str,
) -> pl.DataFrame:
    """Filter conditions by a regex pattern across all CCSR columns.

    Equivalent to R:
        cond %>% unite("all_CCSR", CCSR1X:CCSR3X) %>% filter(grepl(pattern, all_CCSR))

    Args:
        conditions: Conditions DataFrame.
        pattern: Regex pattern to match against concatenated CCSR codes.

    Returns:
        Filtered DataFrame.
    """
    ccsr_cols = [c for c in ["CCSR1X", "CCSR2X", "CCSR3X"] if c in conditions.columns]
    if not ccsr_cols:
        raise ValueError("No CCSR columns found in conditions data")

    # Concatenate CCSR columns and filter by pattern
    concat_expr = pl.concat_str([pl.col(c).cast(pl.Utf8) for c in ccsr_cols], separator="_")
    return conditions.filter(concat_expr.str.contains(pattern))


def merge_conditions_with_crosswalk(
    conditions: pl.DataFrame,
    crosswalk: pl.DataFrame,
    ccsr_cols: list[str] | None = None,
) -> pl.DataFrame:
    """Merge collapsed condition codes to conditions via CCSR crosswalk.

    Converts multiple CCSRs to separate rows (wide to long), then joins
    with the crosswalk to get MEPS collapsed condition categories.

    Equivalent to R:
        cond %>%
            pivot_longer(CCSR1X:CCSR3X) %>%
            filter(CCSR != "-1") %>%
            left_join(condition_codes, by="CCSR")

    Args:
        conditions: Conditions DataFrame.
        crosswalk: CCSR crosswalk from load_ccsr_crosswalk().
        ccsr_cols: CCSR columns to unpivot. Defaults to ['CCSR1X', 'CCSR2X', 'CCSR3X'].

    Returns:
        Long-format DataFrame with Condition column from crosswalk.
    """
    if ccsr_cols is None:
        ccsr_cols = [c for c in ["CCSR1X", "CCSR2X", "CCSR3X"] if c in conditions.columns]

    other_cols = [c for c in conditions.columns if c not in ccsr_cols]

    # Unpivot CCSR columns to long format
    long = conditions.unpivot(
        on=ccsr_cols,
        index=other_cols,
        variable_name="CCSRnum",
        value_name="CCSR",
    )

    # Filter out missing/inapplicable values
    long = long.filter(
        (pl.col("CCSR").is_not_null())
        & (pl.col("CCSR").cast(pl.Utf8) != "-1")
        & (pl.col("CCSR").cast(pl.Utf8) != "")
    )

    # Join with crosswalk
    long = long.with_columns(pl.col("CCSR").cast(pl.Utf8))
    crosswalk_typed = crosswalk.with_columns(pl.col("CCSR").cast(pl.Utf8))
    result = long.join(crosswalk_typed, on="CCSR", how="left")

    return result


def stack_event_files(
    event_files: dict[str, pl.DataFrame],
    expenditure_col_map: dict[str, str],
    common_cols: list[str] | None = None,
    year_suffix: str = "",
) -> pl.DataFrame:
    """Stack multiple event files into a single DataFrame.

    Implements the 6-event-file stacking pattern from
    R/summary_tables_examples/cond_expenditures_2018.R lines 44-64.

    For RX events, aggregates to LINKIDX level first (counting fills).

    Args:
        event_files: Dict mapping event type label to DataFrame.
            Example: {'RX': rx_df, 'IP': ip_df, 'ER': er_df, ...}
        expenditure_col_map: Maps event type to its expenditure column.
            Example: {'RX': 'RXXP18X', 'IP': 'IPXP18X', ...}
        common_cols: Columns to keep from all event files.
            Defaults to ['EVNTIDX', 'DUPERSID', 'VARSTR', 'VARPSU', weight_col].
        year_suffix: Year suffix for variable names (e.g., '18' for 2018).

    Returns:
        Stacked DataFrame with standardized 'XPX' column and 'data' source label.
    """
    weight_col = f"PERWT{year_suffix}F" if year_suffix else None

    frames = []
    for event_type, df in event_files.items():
        xp_col = expenditure_col_map.get(event_type)
        if xp_col is None:
            continue

        if event_type == "RX" and "LINKIDX" in df.columns:
            # Aggregate RX to event level (sum expenditures, count fills)
            group_cols = ["DUPERSID", "LINKIDX"]
            agg_cols = [c for c in ["VARSTR", "VARPSU"] if c in df.columns]
            if weight_col and weight_col in df.columns:
                agg_cols.append(weight_col)

            df_agg = (
                df.group_by(group_cols)
                .agg(
                    [pl.col(xp_col).sum().alias("XPX"), pl.len().alias("n_fills")]
                    + [pl.col(c).first() for c in agg_cols]
                )
                .rename({"LINKIDX": "EVNTIDX"})
            )
            df_agg = df_agg.with_columns(pl.lit(event_type).alias("data"))
            frames.append(df_agg)
        else:
            renamed = df.rename({xp_col: "XPX"})
            renamed = renamed.with_columns(pl.lit(event_type).alias("data"))
            if "n_fills" not in renamed.columns:
                renamed = renamed.with_columns(pl.lit(None).cast(pl.UInt32).alias("n_fills"))
            frames.append(renamed)

    if not frames:
        return pl.DataFrame()

    # Select common columns and stack
    select_cols = ["data", "EVNTIDX", "DUPERSID", "XPX", "VARSTR", "VARPSU", "n_fills"]
    if weight_col:
        select_cols.append(weight_col)

    normalized = []
    for f in frames:
        available = [c for c in select_cols if c in f.columns]
        normalized.append(f.select(available))

    stacked = pl.concat(normalized, how="diagonal_relaxed")

    # Add n_events column (max of n_fills or 1)
    stacked = stacked.with_columns(
        pl.when(pl.col("n_fills").is_not_null())
        .then(pl.col("n_fills"))
        .otherwise(1)
        .alias("n_events")
    )

    return stacked
