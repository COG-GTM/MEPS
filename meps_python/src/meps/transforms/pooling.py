"""Multi-year data pooling utilities for MEPS analysis.

Implements weight adjustment and variance linkage file merging
for pooling across CAPI survey redesign boundaries.
"""

from __future__ import annotations

from typing import Optional

import polars as pl

from meps.survey.utils import merge_variance_linkage, pool_weights


def pool_years(
    datasets: list[tuple[pl.DataFrame, int]],
    weight_renames: Optional[dict[int, str]] = None,
    expenditure_renames: Optional[dict[int, dict[str, str]]] = None,
    select_cols: Optional[list[str]] = None,
) -> pl.DataFrame:
    """Pool multiple years of MEPS data with weight adjustment.

    Handles:
    1. Renaming year-specific variable suffixes to generic names
    2. Selecting common columns
    3. Stacking years
    4. Dividing weights by number of years

    Equivalent to R:
        pool = bind_rows(fyc19p, fyc18p, fyc17p) %>%
            mutate(poolwt = perwt / 3)

    Args:
        datasets: List of (DataFrame, year) tuples.
        weight_renames: Maps year to weight column name. If None, auto-generates
            from PERWTyyF pattern.
        expenditure_renames: Maps year to {old_name: new_name} for expenditure vars.
        select_cols: Columns to select after renaming (before stacking).

    Returns:
        Pooled DataFrame with 'poolwt' column.
    """
    n_years = len(datasets)
    standardized = []

    for df, year in datasets:
        yy = str(year)[-2:]

        # Build rename mapping
        renames = {}
        if weight_renames and year in weight_renames:
            renames[weight_renames[year]] = "perwt"
        else:
            renames[f"PERWT{yy}F"] = "perwt"

        # Add expenditure renames
        if expenditure_renames and year in expenditure_renames:
            renames.update(expenditure_renames[year])
        else:
            # Default common expenditure renames
            for prefix in ["TOTEXP", "TOTSLF"]:
                col = f"{prefix}{yy}"
                if col in df.columns:
                    renames[col] = prefix.lower()

        # Apply renames
        actual_renames = {k: v for k, v in renames.items() if k in df.columns}
        df_renamed = df.rename(actual_renames)

        # Select columns if specified
        if select_cols:
            available = [c for c in select_cols if c in df_renamed.columns]
            df_renamed = df_renamed.select(available)

        # Add year identifier
        df_renamed = df_renamed.with_columns(pl.lit(year).alias("data_year"))

        standardized.append(df_renamed)

    # Stack all years
    pooled = pl.concat(standardized, how="diagonal_relaxed")

    # Create pooled weight
    pooled = pool_weights(pooled, n_years)

    return pooled


def pool_with_linkage(
    datasets: list[tuple[pl.DataFrame, int]],
    linkage: pl.DataFrame,
    weight_renames: Optional[dict[int, str]] = None,
    expenditure_renames: Optional[dict[int, dict[str, str]]] = None,
    select_cols: Optional[list[str]] = None,
    psu_col: str = "PSU9619",
    strata_col: str = "STRA9619",
) -> pl.DataFrame:
    """Pool multiple years with variance linkage file for cross-redesign pooling.

    Use when pooling data years that span the 2018 CAPI redesign boundary
    (e.g., 2017-2019). The linkage file provides PSU9619/STRA9619 variables
    for correct variance estimation.

    Equivalent to R exercise_3d.R:
        pool_linked = left_join(pool, linkage_sub, by=c("DUPERSID","PANEL"))
        pool_dsgn = svydesign(id=~PSU9619, strata=~STRA9619, ...)

    Args:
        datasets: List of (DataFrame, year) tuples.
        linkage: Pooled Variance Linkage file (e.g., h36u19).
        weight_renames: Maps year to weight column name.
        expenditure_renames: Maps year to expenditure rename mapping.
        select_cols: Columns to select before stacking.
        psu_col: PSU column in linkage file. Default 'PSU9619'.
        strata_col: Strata column in linkage file. Default 'STRA9619'.

    Returns:
        Pooled DataFrame with linkage PSU/strata merged.
    """
    # First pool the data
    pooled = pool_years(
        datasets,
        weight_renames=weight_renames,
        expenditure_renames=expenditure_renames,
        select_cols=select_cols,
    )

    # Merge with linkage file
    pooled = merge_variance_linkage(
        pooled, linkage,
        psu_col=psu_col,
        strata_col=strata_col,
    )

    return pooled
