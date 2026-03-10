"""
PySpark Data Loader for MEPS Public Use Files.

This module provides utilities for loading MEPS (Medical Expenditure Panel Survey)
data files into PySpark DataFrames. It serves as the PySpark equivalent of the
R MEPS package's ``read_MEPS()`` function.

Supported file formats:
    - SAS Transport (.ssp) via pandas intermediary
    - Stata (.dta) via pandas intermediary
    - SAS Data (.sas7bdat) via pandas intermediary
    - Parquet (.parquet) -- recommended format for Spark performance
    - CSV (.csv) via native Spark reader

Typical usage::

    from utils.data_loader import get_spark_session, read_MEPS, get_meps_file

    spark = get_spark_session()
    # Load by file path
    fyc = read_MEPS(spark, "data/h224.parquet")

    # Load by year and type (convenience)
    file_name = get_meps_file(year=2020, file_type="FYC")
    fyc = read_MEPS(spark, f"data/{file_name}.parquet")
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import pandas as pd
from pyspark.sql import DataFrame, SparkSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MEPS file-name lookup
# ---------------------------------------------------------------------------

# Mapping of (year, file_type) -> MEPS PUF file name (without extension).
# Sources: Quick_Reference_Guides/meps_file_names.csv and the MEPS website.
#
# To extend this dictionary for additional years:
#   1. Visit https://meps.ahrq.gov/mepsweb/data_stats/download_data_files.jsp
#   2. Find the file number for the desired year and type (e.g., "HC-233"
#      for the 2021 FYC file corresponds to file name "h233").
#   3. Add an entry: (year, "TYPE"): "hNNN"
#
# Event sub-files use a letter suffix. For example, h220g is the 2020
# office-based visits file (OB). The event letter codes are:
#   b = Dental (DV), c = Other Medical (OM), d = Inpatient (IP),
#   e = ER, f = Outpatient (OP), g = Office-based (OB),
#   h = Home Health (HH)

MEPS_FILE_LOOKUP: dict[tuple[int, str], str] = {
    # ---- 2016 ----
    (2016, "FYC"):  "h192",
    (2016, "COND"): "h190",
    (2016, "PMED"): "h188a",
    (2016, "RX"):   "h188a",
    (2016, "CLNK"): "h188if1",
    (2016, "EVNT"): "h188",
    (2016, "OB"):   "h188g",
    (2016, "ER"):   "h188e",
    (2016, "IP"):   "h188d",
    (2016, "OP"):   "h188f",
    (2016, "DV"):   "h188b",
    # ---- 2017 ----
    (2017, "FYC"):  "h201",
    (2017, "COND"): "h199",
    (2017, "PMED"): "h197a",
    (2017, "RX"):   "h197a",
    (2017, "CLNK"): "h197if1",
    (2017, "EVNT"): "h197",
    (2017, "OB"):   "h197g",
    (2017, "ER"):   "h197e",
    (2017, "IP"):   "h197d",
    (2017, "OP"):   "h197f",
    (2017, "DV"):   "h197b",
    # ---- 2018 ----
    (2018, "FYC"):  "h209",
    (2018, "COND"): "h207",
    (2018, "PMED"): "h206a",
    (2018, "RX"):   "h206a",
    (2018, "CLNK"): "h206if1",
    (2018, "EVNT"): "h206",
    (2018, "OB"):   "h206g",
    (2018, "ER"):   "h206e",
    (2018, "IP"):   "h206d",
    (2018, "OP"):   "h206f",
    (2018, "DV"):   "h206b",
    # ---- 2019 ----
    (2019, "FYC"):  "h216",
    (2019, "COND"): "h214",
    (2019, "PMED"): "h213a",
    (2019, "RX"):   "h213a",
    (2019, "CLNK"): "h213if1",
    (2019, "EVNT"): "h213",
    (2019, "OB"):   "h213g",
    (2019, "ER"):   "h213e",
    (2019, "IP"):   "h213d",
    (2019, "OP"):   "h213f",
    (2019, "DV"):   "h213b",
    # ---- 2020 ----
    (2020, "FYC"):  "h224",
    (2020, "COND"): "h222",
    (2020, "PMED"): "h220a",
    (2020, "RX"):   "h220a",
    (2020, "CLNK"): "h220if1",
    (2020, "EVNT"): "h220",
    (2020, "OB"):   "h220g",
    (2020, "ER"):   "h220e",
    (2020, "IP"):   "h220d",
    (2020, "OP"):   "h220f",
    (2020, "DV"):   "h220b",
    # ---- 2021 ----
    (2021, "FYC"):  "h233",
    (2021, "COND"): "h231",
    (2021, "PMED"): "h229a",
    (2021, "RX"):   "h229a",
    (2021, "CLNK"): "h229if1",
    (2021, "EVNT"): "h229",
    (2021, "OB"):   "h229g",
    (2021, "ER"):   "h229e",
    (2021, "IP"):   "h229d",
    (2021, "OP"):   "h229f",
    (2021, "DV"):   "h229b",
}

# Supported file extensions and the method used to read them.
_SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".ssp":      "sas_xport",
    ".sas7bdat": "sas7bdat",
    ".dta":      "stata",
    ".parquet":  "parquet",
    ".csv":      "csv",
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_spark_session(
    app_name: str = "MEPS_Analysis",
    driver_memory: str = "4g",
) -> SparkSession:
    """Create or retrieve a SparkSession with sensible defaults for local MEPS analysis.

    Parameters
    ----------
    app_name:
        Spark application name shown in the Spark UI.
    driver_memory:
        Amount of memory allocated to the Spark driver (e.g. ``"4g"``).
        Increase for larger MEPS files or multi-year pooling.

    Returns
    -------
    SparkSession
        An active SparkSession instance.
    """
    spark = (
        SparkSession.builder
        .appName(app_name)
        .config("spark.driver.memory", driver_memory)
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        .getOrCreate()
    )
    logger.info("SparkSession '%s' ready (driver memory: %s).", app_name, driver_memory)
    return spark


def get_meps_file(year: int, file_type: str) -> str:
    """Return the MEPS PUF file name (without extension) for a given *year* and *file_type*.

    This mirrors the convenience interface of R's ``read_MEPS(year=..., type=...)``.

    Parameters
    ----------
    year:
        Data year (e.g. ``2020``).
    file_type:
        MEPS file type code.  Common values:

        * ``"FYC"``  -- Full-Year Consolidated
        * ``"COND"`` -- Medical Conditions
        * ``"PMED"`` / ``"RX"`` -- Prescribed Medicines
        * ``"CLNK"`` -- Conditions-Event Link
        * ``"EVNT"`` -- All events (base)
        * ``"OB"``   -- Office-Based visits
        * ``"ER"``   -- Emergency Room visits
        * ``"IP"``   -- Inpatient stays
        * ``"OP"``   -- Outpatient visits
        * ``"DV"``   -- Dental Visits

    Returns
    -------
    str
        The MEPS file name, e.g. ``"h224"`` for FYC 2020.

    Raises
    ------
    KeyError
        If the requested year/type combination is not in the lookup table.
        See the ``MEPS_FILE_LOOKUP`` dictionary for available entries and
        the module docstring for instructions on extending it.

    Examples
    --------
    >>> get_meps_file(2020, "FYC")
    'h224'
    >>> get_meps_file(2020, "COND")
    'h222'
    """
    key = (year, file_type.upper())
    if key not in MEPS_FILE_LOOKUP:
        available_years = sorted({y for y, _ in MEPS_FILE_LOOKUP})
        available_types = sorted({t for _, t in MEPS_FILE_LOOKUP})
        raise KeyError(
            f"No MEPS file mapping found for year={year}, type='{file_type}'. "
            f"Available years: {available_years}. "
            f"Available types: {available_types}. "
            "See MEPS_FILE_LOOKUP in data_loader.py to add new entries."
        )
    return MEPS_FILE_LOOKUP[key]


# ---------------------------------------------------------------------------
# Core reader
# ---------------------------------------------------------------------------


def read_MEPS(
    spark: SparkSession,
    file_path: str,
    file_format: Optional[str] = None,
) -> DataFrame:
    """Load a MEPS data file into a PySpark DataFrame.

    This is the PySpark equivalent of the R ``read_MEPS()`` function.  It
    supports multiple file formats commonly used to distribute MEPS Public
    Use Files and returns a Spark DataFrame suitable for distributed
    analysis.

    Parameters
    ----------
    spark:
        An active ``SparkSession`` instance.
    file_path:
        Path to the MEPS data file.  May be a local path or a cloud URI
        (e.g. ``s3://bucket/h224.parquet``).
    file_format:
        Explicit file format override.  One of ``"ssp"``, ``"sas7bdat"``,
        ``"dta"``, ``"parquet"``, or ``"csv"``.  When ``None`` (the
        default), the format is auto-detected from the file extension.

    Returns
    -------
    pyspark.sql.DataFrame
        A Spark DataFrame containing the MEPS data.

    Raises
    ------
    FileNotFoundError
        If *file_path* points to a local file that does not exist.
    ValueError
        If the file format cannot be determined or is unsupported.

    Notes
    -----
    For ``.ssp``, ``.sas7bdat``, and ``.dta`` files the data is first read
    into a *pandas* DataFrame and then converted to a Spark DataFrame via
    ``spark.createDataFrame()``.  For best Spark performance, pre-convert
    source files to Parquet using :func:`convert_to_parquet`.

    Examples
    --------
    >>> spark = get_spark_session()
    >>> fyc = read_MEPS(spark, "data/h224.parquet")
    >>> fyc.printSchema()
    """
    # --- resolve format ---
    if file_format is not None:
        fmt = file_format.lower().lstrip(".")
    else:
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        if ext not in _SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Cannot auto-detect format for extension '{ext}'. "
                f"Supported extensions: {list(_SUPPORTED_EXTENSIONS.keys())}. "
                "Pass file_format explicitly if using a non-standard extension."
            )
        fmt = _SUPPORTED_EXTENSIONS[ext]

    # --- validate local paths ---
    if "://" not in file_path and not os.path.exists(file_path):
        raise FileNotFoundError(f"MEPS data file not found: {file_path}")

    logger.info("Reading MEPS file '%s' (format=%s) ...", file_path, fmt)

    # --- dispatch to the appropriate reader ---
    if fmt == "parquet":
        return _read_parquet(spark, file_path)
    if fmt == "csv":
        return _read_csv(spark, file_path)
    if fmt in ("sas_xport", "ssp"):
        return _read_sas_xport(spark, file_path)
    if fmt in ("sas7bdat",):
        return _read_sas7bdat(spark, file_path)
    if fmt in ("stata", "dta"):
        return _read_stata(spark, file_path)

    raise ValueError(
        f"Unsupported file format: '{fmt}'. "
        f"Supported formats: {list(_SUPPORTED_EXTENSIONS.values())}."
    )


# ---------------------------------------------------------------------------
# Format-specific readers (private)
# ---------------------------------------------------------------------------


def _read_parquet(spark: SparkSession, file_path: str) -> DataFrame:
    """Read a Parquet file natively with Spark (recommended)."""
    logger.debug("Using native Spark Parquet reader.")
    return spark.read.parquet(file_path)


def _read_csv(spark: SparkSession, file_path: str) -> DataFrame:
    """Read a CSV file natively with Spark, inferring the header and schema."""
    logger.debug("Using native Spark CSV reader with header and schema inference.")
    return spark.read.csv(file_path, header=True, inferSchema=True)


def _read_sas_xport(spark: SparkSession, file_path: str) -> DataFrame:
    """Read a SAS XPORT / transport (.ssp) file via pandas."""
    logger.debug("Reading SAS XPORT (.ssp) via pandas.read_sas(format='xport').")
    pdf = pd.read_sas(file_path, format="xport", encoding="utf-8")
    return spark.createDataFrame(pdf)


def _read_sas7bdat(spark: SparkSession, file_path: str) -> DataFrame:
    """Read a SAS data (.sas7bdat) file via pandas."""
    logger.debug("Reading SAS data (.sas7bdat) via pandas.read_sas(format='sas7bdat').")
    pdf = pd.read_sas(file_path, format="sas7bdat", encoding="utf-8")
    return spark.createDataFrame(pdf)


def _read_stata(spark: SparkSession, file_path: str) -> DataFrame:
    """Read a Stata (.dta) file via pandas."""
    logger.debug("Reading Stata (.dta) via pandas.read_stata().")
    pdf = pd.read_stata(file_path)
    return spark.createDataFrame(pdf)


# ---------------------------------------------------------------------------
# Parquet conversion helper
# ---------------------------------------------------------------------------


def convert_to_parquet(
    source_path: str,
    output_path: str,
    file_format: Optional[str] = None,
) -> str:
    """Convert a MEPS source file to Parquet for optimised Spark ingestion.

    This helper reads the source file using *pandas* and writes it out as a
    Parquet file using *pyarrow* (the default pandas Parquet engine).  The
    resulting file can then be loaded efficiently with
    ``read_MEPS(spark, output_path)``.

    Parameters
    ----------
    source_path:
        Path to the original MEPS data file (``.ssp``, ``.dta``,
        ``.sas7bdat``, or ``.csv``).
    output_path:
        Destination path for the Parquet file (e.g. ``"data/h224.parquet"``).
    file_format:
        Explicit format override.  Auto-detected from *source_path* extension
        when ``None``.

    Returns
    -------
    str
        The *output_path* for convenient chaining.

    Raises
    ------
    FileNotFoundError
        If *source_path* does not exist.
    ValueError
        If the source format is unsupported.

    Examples
    --------
    >>> convert_to_parquet("data/h224.dta", "data/h224.parquet")
    'data/h224.parquet'
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source file not found: {source_path}")

    # Determine format
    if file_format is not None:
        fmt = file_format.lower().lstrip(".")
    else:
        _, ext = os.path.splitext(source_path)
        ext = ext.lower()
        if ext not in _SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Cannot auto-detect format for extension '{ext}'. "
                f"Supported: {list(_SUPPORTED_EXTENSIONS.keys())}."
            )
        fmt = _SUPPORTED_EXTENSIONS[ext]

    logger.info("Converting '%s' (format=%s) -> '%s' ...", source_path, fmt, output_path)

    # Read into pandas
    if fmt in ("sas_xport", "ssp"):
        pdf = pd.read_sas(source_path, format="xport", encoding="utf-8")
    elif fmt in ("sas7bdat",):
        pdf = pd.read_sas(source_path, format="sas7bdat", encoding="utf-8")
    elif fmt in ("stata", "dta"):
        pdf = pd.read_stata(source_path)
    elif fmt == "csv":
        pdf = pd.read_csv(source_path)
    else:
        raise ValueError(
            f"Cannot convert format '{fmt}' to Parquet. "
            "Supported source formats: ssp, sas7bdat, dta, csv."
        )

    # Write Parquet via pyarrow
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    pdf.to_parquet(output_path, engine="pyarrow", index=False)
    logger.info("Parquet file written to '%s' (%d rows).", output_path, len(pdf))
    return output_path
