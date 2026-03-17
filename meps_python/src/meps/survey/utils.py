"""Survey utility functions for MEPS data analysis.

Includes lonely PSU adjustment, weight pooling, and variance linkage merging.
"""

from __future__ import annotations

import polars as pl


def lonely_psu_adjust(
    data: pl.DataFrame,
    strata_col: str = "VARSTR",
    psu_col: str = "VARPSU",
) -> pl.DataFrame:
    """Detect and flag strata with a single PSU (lonely PSUs).

    Equivalent to R's options(survey.lonely.psu='adjust').
    The 'adjust' method centers contributions from lonely PSUs at the
    grand mean, effectively contributing zero to the variance estimate.

    Args:
        data: Input DataFrame.
        strata_col: Name of the strata column.
        psu_col: Name of the PSU column.

    Returns:
        DataFrame with an additional '_lonely_psu' boolean column.
    """
    psu_counts = (
        data.group_by(strata_col)
        .agg(pl.col(psu_col).n_unique().alias("_n_psu"))
    )

    result = data.join(psu_counts, on=strata_col, how="left")
    result = result.with_columns(
        (pl.col("_n_psu") <= 1).alias("_lonely_psu")
    )
    result = result.drop("_n_psu")
    return result


def pool_weights(
    data: pl.DataFrame,
    n_years: int,
    weight_col: str = "perwt",
    pooled_weight_col: str = "poolwt",
) -> pl.DataFrame:
    """Divide person weights by number of pooled years.

    For multi-year pooling, weights must be divided by the number of years
    being pooled to produce correct national estimates.

    Equivalent to R: poolwt = perwt / 3

    Args:
        data: Input DataFrame with weight column.
        n_years: Number of years being pooled.
        weight_col: Name of the weight column to divide.
        pooled_weight_col: Name for the new pooled weight column.

    Returns:
        DataFrame with pooled weight column added.
    """
    return data.with_columns(
        (pl.col(weight_col) / n_years).alias(pooled_weight_col)
    )


def merge_variance_linkage(
    data: pl.DataFrame,
    linkage: pl.DataFrame,
    join_keys: list[str] | None = None,
    psu_col: str = "PSU9619",
    strata_col: str = "STRA9619",
) -> pl.DataFrame:
    """Merge pooled linkage variance file for cross-redesign pooling.

    When pooling data years that span the 2018 CAPI survey redesign boundary
    (e.g., 2017-2019), the Pooled Variance Linkage file must be merged to
    obtain correct PSU and strata variables for variance estimation.

    The linkage file contains PSU9619/STRA9619 variables that replace
    VARPSU/VARSTR when pooling across the redesign.

    Equivalent to R: left_join(pool, linkage, by = c("DUPERSID", "PANEL"))

    Args:
        data: Pooled dataset.
        linkage: Pooled Variance Linkage file (e.g., h36u19).
        join_keys: Columns to join on. Defaults to ['DUPERSID', 'PANEL'].
        psu_col: PSU column name in linkage file. Default 'PSU9619'.
        strata_col: Strata column name in linkage file. Default 'STRA9619'.

    Returns:
        Merged DataFrame with linkage PSU/strata columns.
    """
    if join_keys is None:
        join_keys = ["DUPERSID", "PANEL"]

    # Select only the needed columns from linkage
    linkage_cols = join_keys + [psu_col, strata_col]
    available_cols = [c for c in linkage_cols if c in linkage.columns]
    linkage_sub = linkage.select(available_cols)

    return data.join(linkage_sub, on=join_keys, how="left")


def standardize_year_variables(
    data: pl.DataFrame,
    year: int,
    renames: dict[str, str] | None = None,
) -> pl.DataFrame:
    """Rename year-specific variable suffixes to generic names.

    MEPS variables include year suffixes (e.g., PERWT20F, TOTEXP20).
    For multi-year pooling, these must be standardized.

    Args:
        data: Input DataFrame.
        year: Two-digit year suffix (e.g., 20 for 2020).
        renames: Optional explicit rename mapping. If None, applies common renames.

    Returns:
        DataFrame with standardized column names.
    """
    yy = str(year)[-2:]

    if renames is None:
        renames = {
            f"PERWT{yy}F": "perwt",
            f"TOTEXP{yy}": "totexp",
            f"TOTSLF{yy}": "totslf",
        }

    # Only rename columns that actually exist
    actual_renames = {k: v for k, v in renames.items() if k in data.columns}
    return data.rename(actual_renames)
