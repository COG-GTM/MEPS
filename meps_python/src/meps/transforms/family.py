"""Family-level variable construction from person-level MEPS data.

Ports SAS exercise 5a logic for aggregating person-level variables
to CPS family level, including expenditure summation and insurance
status aggregation.
"""

from __future__ import annotations

from typing import Optional

import polars as pl


def aggregate_to_family(
    data: pl.DataFrame,
    family_id_col: str = "DTEFAMIDX",
    expenditure_cols: Optional[list[str]] = None,
    count_cols: Optional[list[str]] = None,
    max_cols: Optional[list[str]] = None,
    weight_col: Optional[str] = None,
    strata_col: str = "VARSTR",
    psu_col: str = "VARPSU",
) -> pl.DataFrame:
    """Aggregate person-level data to family level.

    Creates family-level summaries by:
    - Summing expenditure columns across family members
    - Counting persons with each characteristic
    - Taking max of indicator variables (any family member = 1)
    - Preserving design variables (strata, PSU, weight) from first member

    Equivalent to SAS exercise 5a pattern:
        PROC MEANS NWAY DATA=... NOPRINT;
          CLASS DTEFAMIDX;
          VAR expenditure_vars;
          OUTPUT OUT=... SUM=;
        RUN;

    Args:
        data: Person-level DataFrame.
        family_id_col: Family identifier column. Default 'DTEFAMIDX'.
        expenditure_cols: Columns to sum across family members.
        count_cols: Columns to count (sum of indicators) across family members.
        max_cols: Columns to take max of (any family member = 1).
        weight_col: Weight column to preserve (takes first member's value).
        strata_col: Strata column to preserve.
        psu_col: PSU column to preserve.

    Returns:
        Family-level DataFrame.
    """
    if expenditure_cols is None:
        expenditure_cols = []
    if count_cols is None:
        count_cols = []
    if max_cols is None:
        max_cols = []

    agg_exprs = [
        # Family size
        pl.len().alias("FAMSIZE"),
        # Preserve design variables from first member
        pl.col(strata_col).first().alias(strata_col),
        pl.col(psu_col).first().alias(psu_col),
    ]

    if weight_col and weight_col in data.columns:
        agg_exprs.append(pl.col(weight_col).first().alias(weight_col))

    # Sum expenditure columns
    for col in expenditure_cols:
        if col in data.columns:
            agg_exprs.append(pl.col(col).sum().alias(col))

    # Count/sum indicator columns
    for col in count_cols:
        if col in data.columns:
            agg_exprs.append(pl.col(col).sum().alias(col))

    # Max of indicator columns (any family member)
    for col in max_cols:
        if col in data.columns:
            agg_exprs.append(pl.col(col).max().alias(col))

    result = data.group_by(family_id_col).agg(agg_exprs)
    return result


def create_family_expenditure_vars(
    data: pl.DataFrame,
    year_suffix: str,
) -> pl.DataFrame:
    """Create common family-level expenditure variables.

    Adds total and per-capita expenditure variables at the family level.

    Args:
        data: Family-level DataFrame from aggregate_to_family().
        year_suffix: Two-digit year suffix (e.g., '18').

    Returns:
        DataFrame with additional expenditure variables.
    """
    yy = year_suffix
    totexp_col = f"TOTEXP{yy}"

    result = data
    if totexp_col in data.columns and "FAMSIZE" in data.columns:
        result = result.with_columns(
            (pl.col(totexp_col) / pl.col("FAMSIZE")).alias(f"PERCAP_EXP{yy}")
        )

    return result


def merge_person_family(
    person_data: pl.DataFrame,
    family_data: pl.DataFrame,
    family_id_col: str = "DTEFAMIDX",
    suffix: str = "_fam",
) -> pl.DataFrame:
    """Merge family-level variables back to person-level data.

    Args:
        person_data: Person-level DataFrame.
        family_data: Family-level DataFrame.
        family_id_col: Family identifier column for joining.
        suffix: Suffix for family-level columns to avoid name collisions.

    Returns:
        Person-level DataFrame with family-level variables merged.
    """
    return person_data.join(family_data, on=family_id_col, how="left", suffix=suffix)
