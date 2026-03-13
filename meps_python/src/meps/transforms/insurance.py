"""Monthly insurance status construction from MEPS FYC data.

Ports the SAS exercise 5b logic which iterates over 12 monthly insurance
indicator arrays to construct annual insurance status flags.

Uses polars vectorized operations instead of row-by-row iteration.
"""

from __future__ import annotations

import polars as pl

# Month abbreviations used in MEPS variable names
_MONTHS = ["JA", "FE", "MA", "AP", "MY", "JU", "JL", "AU", "SE", "OC", "NO", "DE"]

# Insurance type prefixes and their monthly variable patterns
_INSURANCE_PREFIXES = {
    "PEG": "PEG",   # Employer/Union group
    "POU": "POU",   # Holder outside RU
    "PDK": "PDK",   # Private (source unknown)
    "PNG": "PNG",   # Non-group
    "POG": "POG",   # Other group
    "PRS": "PRS",   # Self-employed
    "PRX": "PRX",   # Private exchange
    "PRI": "PRI",   # Any private
    "INS": "INS",   # Any insurance (with X suffix for edited)
    "MCD": "MCD",   # Medicaid (with X suffix for edited)
    "MCR": "MCR",   # Medicare (with X suffix for edited)
    "TRI": "TRI",   # TRICARE (with X suffix for edited)
    "OPA": "OPA",   # Other public A
    "OPB": "OPB",   # Other public B
}


def _monthly_col_names(prefix: str, year_suffix: str, edited: bool = False) -> list[str]:
    """Generate the 12 monthly column names for an insurance variable.

    Args:
        prefix: Variable prefix (e.g., 'PRI', 'INS', 'MCD').
        year_suffix: Two-digit year (e.g., '15' for 2015).
        edited: If True, append 'X' suffix (for edited variables).

    Returns:
        List of 12 column names.
    """
    suffix = "X" if edited else ""
    return [f"{prefix}{month}{year_suffix}{suffix}" for month in _MONTHS]


def construct_insurance_status(
    data: pl.DataFrame,
    year_suffix: str,
) -> pl.DataFrame:
    """Construct annual insurance status count variables from monthly indicators.

    Ports the SAS exercise 5b logic (Exercise5b.sas lines 54-98).
    For each person, counts the number of months with each type of insurance.

    Output variables:
        PRI_N:   # months covered by private insurance
        INS_N:   # months covered by any insurance
        UNINS_N: # months without insurance
        MCD_N:   # months covered by Medicaid
        MCR_N:   # months covered by Medicare
        TRI_N:   # months covered by TRICARE
        OPAB_N:  # months covered by Other Public A or B
        GRP_N:   # months covered by private group insurance
        NG_N:    # months covered by private non-group insurance
        PUB_N:   # months covered by public insurance
        REF_N:   # months in MEPS survey (reference period)

    Args:
        data: FYC DataFrame with monthly insurance variables.
        year_suffix: Two-digit year suffix (e.g., '15').

    Returns:
        DataFrame with insurance count variables added.
    """
    yy = year_suffix

    # Build column name lists for each insurance type
    pri_cols = _monthly_col_names("PRI", yy)
    ins_cols = _monthly_col_names("INS", yy, edited=True)
    mcd_cols = _monthly_col_names("MCD", yy, edited=True)
    mcr_cols = _monthly_col_names("MCR", yy, edited=True)
    tri_cols = _monthly_col_names("TRI", yy, edited=True)
    opa_cols = _monthly_col_names("OPA", yy)
    opb_cols = _monthly_col_names("OPB", yy)
    peg_cols = _monthly_col_names("PEG", yy)
    pou_cols = _monthly_col_names("POU", yy)
    pdk_cols = _monthly_col_names("PDK", yy)
    prx_cols = _monthly_col_names("PRX", yy)
    png_cols = _monthly_col_names("PNG", yy)
    pog_cols = _monthly_col_names("POG", yy)
    prs_cols = _monthly_col_names("PRS", yy)

    def _safe_cols(col_list: list[str]) -> list[str]:
        """Return only columns that exist in the data."""
        return [c for c in col_list if c in data.columns]

    def _count_months_eq(col_list: list[str], value: int) -> pl.Expr:
        """Count months where column equals value."""
        safe = _safe_cols(col_list)
        if not safe:
            return pl.lit(0)
        exprs = [(pl.col(c) == value).cast(pl.Int32) for c in safe]
        return sum(exprs[1:], exprs[0])

    def _count_months_gt(col_list: list[str], value: int) -> pl.Expr:
        """Count months where column > value."""
        safe = _safe_cols(col_list)
        if not safe:
            return pl.lit(0)
        exprs = [(pl.col(c) > value).cast(pl.Int32) for c in safe]
        return sum(exprs[1:], exprs[0])

    def _count_months_or(col_lists: list[list[str]], value: int = 1) -> pl.Expr:
        """Count months where ANY of the listed variables equals value."""
        month_exprs = []
        for month_idx in range(12):
            or_expr = pl.lit(False)
            for col_list in col_lists:
                safe = _safe_cols(col_list)
                if month_idx < len(safe):
                    or_expr = or_expr | (pl.col(safe[month_idx]) == value)
            month_exprs.append(or_expr.cast(pl.Int32))
        if not month_exprs:
            return pl.lit(0)
        return sum(month_exprs[1:], month_exprs[0])

    result = data.with_columns([
        # PRI_N: months covered by private insurance
        _count_months_eq(pri_cols, 1).alias("PRI_N"),

        # INS_N: months covered by any insurance
        _count_months_eq(ins_cols, 1).alias("INS_N"),

        # UNINS_N: months without insurance (INS = 2)
        _count_months_eq(ins_cols, 2).alias("UNINS_N"),

        # MCD_N: months covered by Medicaid
        _count_months_eq(mcd_cols, 1).alias("MCD_N"),

        # MCR_N: months covered by Medicare
        _count_months_eq(mcr_cols, 1).alias("MCR_N"),

        # TRI_N: months covered by TRICARE
        _count_months_eq(tri_cols, 1).alias("TRI_N"),

        # OPAB_N: months covered by Other Public A or B
        _count_months_or([opa_cols, opb_cols], 1).alias("OPAB_N"),

        # GRP_N: months covered by private group (PEG=1 or TRI=1 or POU=1 or PDK=1)
        _count_months_or([peg_cols, tri_cols, pou_cols, pdk_cols], 1).alias("GRP_N"),

        # NG_N: months covered by private non-group (PRX=1 or PNG=1 or POG=1 or PRS=1)
        _count_months_or([prx_cols, png_cols, pog_cols, prs_cols], 1).alias("NG_N"),

        # PUB_N: months covered by public insurance (MCR=1 or MCD=1 or OPA=1 or OPB=1)
        _count_months_or([mcr_cols, mcd_cols, opa_cols, opb_cols], 1).alias("PUB_N"),

        # REF_N: months in MEPS survey (INS > 0)
        _count_months_gt(ins_cols, 0).alias("REF_N"),
    ])

    return result


def construct_insurance_flags(data: pl.DataFrame) -> pl.DataFrame:
    """Create binary insurance status flags from monthly count variables.

    Requires construct_insurance_status() to have been run first.

    Output flags:
        FULL_INSU:    Insured for full year (UNINS_N == 0)
        GROUP_INS1:   Ever insured by private group (GRP_N > 0)
        GROUP_INS2:   Insured by private group for full year (GRP_N == REF_N)
        NG_INS:       Ever insured by private non-group (NG_N > 0)

    Args:
        data: DataFrame with insurance count variables.

    Returns:
        DataFrame with insurance flag variables added.
    """
    return data.with_columns([
        (pl.col("UNINS_N") == 0).cast(pl.Int32).alias("FULL_INSU"),
        (pl.col("GRP_N") > 0).cast(pl.Int32).alias("GROUP_INS1"),
        ((pl.col("GRP_N") > 0) & (pl.col("GRP_N") == pl.col("REF_N"))).cast(pl.Int32).alias("GROUP_INS2"),
        (pl.col("NG_N") > 0).cast(pl.Int32).alias("NG_INS"),
    ])
