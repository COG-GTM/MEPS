"""MEPS data file readers supporting multiple formats across data years.

Handles the format transitions:
  - 1996-2015: SAS XPORT (.ssp) files
  - 2016: .ssp for most files, .sas7bdat or .dta for Medical Conditions
  - 2017+: .dta or .sas7bdat files
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import polars as pl
import pyreadstat

# Mapping of MEPS file types to column indices in meps_file_names.csv
_FILE_TYPE_COLUMNS = {
    "PIT": "PIT",
    "FYC": "FYC",
    "COND": "Conditions",
    "Conditions": "Conditions",
    "PMED": "PMED Events",
    "PMED Events": "PMED Events",
    "RX": "PMED Events",
    "Events": "Events",
    "OB": "Events",
    "IP": "Events",
    "ER": "Events",
    "OP": "Events",
    "HH": "Events",
    "DV": "Events",
    "OM": "Events",
    "Jobs": "Jobs",
    "PRPL": "PRPL",
    "CLNK": "CLNK",
    "RXLK": "RXLK",
    "Multum": "Multum",
    "PSAQ": "PSAQ",
    "MOS": "MOS",
    "FS": "FS",
    "Pooled linkage": "Pooled linkage",
}

# Event file letter suffixes (appended to the base Events file number)
_EVENT_SUFFIXES = {
    "RX": "a",
    "DV": "b",
    "OM": "c",
    "IP": "d",
    "ER": "e",
    "OP": "f",
    "OB": "g",
    "HH": "h",
}


def _load_file_names_csv() -> pl.DataFrame:
    """Load the meps_file_names.csv reference file."""
    # Try several candidate locations relative to this file and environment
    candidates = [
        # meps_python/src/meps/io/readers.py -> parents[4] = meps_python/ -> .. = repo root
        Path(__file__).resolve().parents[4] / "Quick_Reference_Guides" / "meps_file_names.csv",
        # Direct repo root (parents[4] is repo root when installed editable)
        Path(__file__).resolve().parents[3] / "Quick_Reference_Guides" / "meps_file_names.csv",
        Path(__file__).resolve().parents[5] / "Quick_Reference_Guides" / "meps_file_names.csv",
        # Environment variable override
        Path(os.environ.get("MEPS_REPO_ROOT", "")) / "Quick_Reference_Guides" / "meps_file_names.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return pl.read_csv(
                str(candidate), null_values=["-", ""],
                ignore_errors=True, truncate_ragged_lines=True,
            )
    raise FileNotFoundError(
        "Could not find meps_file_names.csv. Set MEPS_REPO_ROOT env var to the MEPS repo root."
    )


def _resolve_file_name(year: int, file_type: str) -> str:
    """Resolve a MEPS file name from year and type using meps_file_names.csv.

    Args:
        year: Data year (1996-2022).
        file_type: File type (e.g., 'FYC', 'COND', 'OB', 'RX', 'CLNK').

    Returns:
        The MEPS file identifier (e.g., 'h224').
    """
    if file_type == "Pooled linkage":
        return "h36u19"

    file_names = _load_file_names_csv()

    # Filter to the requested year
    year_row = file_names.filter(pl.col("Year") == year)
    if year_row.is_empty():
        raise ValueError(f"Year {year} not found in meps_file_names.csv")

    # Look up the column for this file type
    if file_type in _EVENT_SUFFIXES:
        col_name = "Events"
    elif file_type in _FILE_TYPE_COLUMNS:
        col_name = _FILE_TYPE_COLUMNS[file_type]
    else:
        raise ValueError(f"Unknown file type: {file_type}")

    raw_value = year_row[col_name][0]
    if raw_value is None:
        raise ValueError(f"No file available for year={year}, type={file_type}")

    raw_value = str(raw_value).strip()

    # For event files, replace the wildcard '*' with the event suffix
    if file_type in _EVENT_SUFFIXES:
        suffix = _EVENT_SUFFIXES[file_type]
        if "*" in raw_value:
            raw_value = raw_value.replace("*", suffix)
        elif raw_value.endswith("f1") or raw_value.endswith("f2"):
            # Older format like h10*f1 -> h10af1
            raw_value = raw_value.replace("*", suffix)
        else:
            raw_value = raw_value + suffix

    # For PMED/RX events, file name already includes 'a' suffix in the CSV
    if file_type in ("PMED", "PMED Events", "RX") and "a" not in raw_value:
        raw_value = raw_value + "a"

    return raw_value


def _find_file(file_name: str, data_dir: str) -> tuple[str, str]:
    """Find a MEPS data file on disk, trying multiple extensions.

    Returns:
        Tuple of (full_path, format) where format is one of 'xport', 'sas7bdat', 'dta'.
    """
    data_path = Path(data_dir)

    # Try formats in preference order
    for ext, fmt in [(".dta", "dta"), (".sas7bdat", "sas7bdat"), (".ssp", "xport")]:
        candidate = data_path / f"{file_name}{ext}"
        if candidate.exists():
            return str(candidate), fmt

    # Try uppercase extensions
    for ext, fmt in [(".DTA", "dta"), (".SAS7BDAT", "sas7bdat"), (".SSP", "xport")]:
        candidate = data_path / f"{file_name}{ext}"
        if candidate.exists():
            return str(candidate), fmt

    raise FileNotFoundError(
        f"Could not find MEPS file '{file_name}' in {data_dir}. "
        f"Tried extensions: .dta, .sas7bdat, .ssp"
    )


def _preferred_format(year: int, file_type: str) -> str:
    """Return the preferred file format for a given year.

    - 1996-2015: xport (.ssp)
    - 2016: xport (.ssp) for most; sas7bdat/dta for Conditions
    - 2017+: dta or sas7bdat
    """
    if year <= 2015:
        return "xport"
    if year == 2016:
        if file_type in ("COND", "Conditions"):
            return "sas7bdat"
        return "xport"
    return "dta"


def _read_file_to_pandas(file_path: str, fmt: str):
    """Read a single MEPS data file into a pandas DataFrame using pyreadstat."""
    if fmt == "xport":
        df, meta = pyreadstat.read_xport(file_path)
    elif fmt == "sas7bdat":
        df, meta = pyreadstat.read_sas7bdat(file_path)
    elif fmt == "dta":
        df, meta = pyreadstat.read_dta(file_path)
    else:
        raise ValueError(f"Unknown format: {fmt}")
    return df, meta


def _pandas_to_polars(pandas_df) -> pl.DataFrame:
    """Convert a pandas DataFrame to a polars DataFrame.

    Handles column name uppercasing for consistency.
    """
    # Uppercase all column names for consistency
    pandas_df.columns = [c.upper() for c in pandas_df.columns]
    return pl.from_pandas(pandas_df)


def _cache_path(file_path: str) -> Path:
    """Return path for Parquet cache of a source file."""
    src = Path(file_path)
    return src.with_suffix(".parquet")


def read_meps(
    year: Optional[int] = None,
    file_type: Optional[str] = None,
    file_name: Optional[str] = None,
    data_dir: str = "C:/MEPS",
    cache: bool = True,
) -> pl.DataFrame:
    """Read a MEPS data file and return a polars DataFrame.

    Can specify either (year, file_type) or file_name directly.

    Args:
        year: Data year (1996-2022).
        file_type: File type (e.g., 'FYC', 'COND', 'OB', 'RX', 'CLNK', 'Pooled linkage').
        file_name: Direct file name (e.g., 'h224'). Overrides year/file_type.
        data_dir: Directory containing MEPS data files. Defaults to 'C:/MEPS'.
        cache: If True, cache converted Parquet files for faster subsequent reads.

    Returns:
        polars DataFrame with uppercased column names.

    Examples:
        >>> df = read_meps(year=2020, file_type='FYC', data_dir='/data/meps')
        >>> df = read_meps(file_name='h224', data_dir='/data/meps')
    """
    if file_name is None:
        if year is None or file_type is None:
            raise ValueError("Must specify either (year, file_type) or file_name")
        file_name = _resolve_file_name(year, file_type)

    file_path, fmt = _find_file(file_name, data_dir)

    # Check for cached Parquet
    parquet_path = _cache_path(file_path)
    if cache and parquet_path.exists():
        src_mtime = os.path.getmtime(file_path)
        cache_mtime = os.path.getmtime(str(parquet_path))
        if cache_mtime >= src_mtime:
            return pl.read_parquet(str(parquet_path))

    # Read the source file
    pandas_df, _meta = _read_file_to_pandas(file_path, fmt)
    result = _pandas_to_polars(pandas_df)

    # Cache as Parquet for future reads
    if cache:
        try:
            result.write_parquet(str(parquet_path))
        except (OSError, PermissionError):
            pass  # Non-critical: skip caching on write failure

    return result


def read_fixed_width(
    file_path: str,
    col_specs: list[tuple[str, int, int]],
) -> pl.DataFrame:
    """Read a fixed-width ASCII (.dat) file used in older MEPS exercises.

    Args:
        file_path: Path to the .dat file.
        col_specs: List of (column_name, start_position, end_position) tuples.
            Positions are 1-indexed and inclusive, matching SAS INPUT statement format.

    Returns:
        polars DataFrame.

    Example:
        Matching SAS: INPUT @1 DUPERSID $10. @11 PANEL 2.
        >>> read_fixed_width('data.dat', [('DUPERSID', 1, 10), ('PANEL', 11, 12)])
    """
    rows: list[dict[str, str]] = []
    with open(file_path, "r") as f:
        for line in f:
            row = {}
            for col_name, start, end in col_specs:
                # Convert from 1-indexed inclusive to 0-indexed
                row[col_name] = line[start - 1 : end].strip()
            rows.append(row)

    if not rows:
        schema = {name: pl.Utf8 for name, _, _ in col_specs}
        return pl.DataFrame(schema=schema)

    df = pl.DataFrame(rows)

    # Try to convert numeric columns
    for col_name in df.columns:
        try:
            df = df.with_columns(pl.col(col_name).cast(pl.Float64).alias(col_name))
        except (pl.exceptions.InvalidOperationError, pl.exceptions.ComputeError):
            pass  # Keep as string

    return df
