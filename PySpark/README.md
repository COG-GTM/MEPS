# Analyzing MEPS data using PySpark <!-- omit in toc -->

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Directory structure](#directory-structure)
- [Quick start](#quick-start)
  - [1. Create a SparkSession](#1-create-a-sparksession)
  - [2. Load a MEPS file by path](#2-load-a-meps-file-by-path)
  - [3. Load a MEPS file by year and type](#3-load-a-meps-file-by-year-and-type)
  - [4. Pre-convert to Parquet (recommended)](#4-pre-convert-to-parquet-recommended)
- [Supported file formats](#supported-file-formats)
- [Parquet pre-conversion workflow](#parquet-pre-conversion-workflow)
- [Survey estimation (Phase 2+)](#survey-estimation-phase-2)

# Overview

This directory contains a **PySpark** implementation of MEPS analysis exercises, migrated from the existing R, SAS, and Stata examples in this repository. The goal is to enable scalable, distributed analysis of MEPS-HC (Medical Expenditure Panel Survey - Household Component) Public Use Files using Apache Spark.

The migration is organized in phases:

| Phase | Scope | Status |
|-------|-------|--------|
| **1** | Data loader utility (`utils/data_loader.py`) | **Current** |
| 2 | Survey estimation helpers (weighted means, totals, etc.) | Planned |
| 3 | Workshop exercise ports | Planned |
| 4 | Summary table examples | Planned |

# Prerequisites

- **Python 3.8+**
- **PySpark** (tested with 3.x)
- **pandas**
- **pyarrow** (for Parquet I/O and Arrow-based Spark conversion)

Install the core dependencies:

```bash
pip install pyspark pandas pyarrow
```

# Directory structure

```
PySpark/
├── README.md                   # This file
├── utils/
│   ├── __init__.py
│   └── data_loader.py          # read_MEPS(), convert_to_parquet(), get_meps_file(), get_spark_session()
├── workshop_exercises/         # (Phase 3 - planned) PySpark ports of R/SAS/Stata exercises
└── summary_tables_examples/    # (Phase 4 - planned) PySpark ports of summary table scripts
```

# Quick start

## 1. Create a SparkSession

```python
from utils.data_loader import get_spark_session

spark = get_spark_session()  # default: app_name="MEPS_Analysis", driver_memory="4g"
```

## 2. Load a MEPS file by path

```python
from utils.data_loader import read_MEPS

# Parquet (recommended - fastest)
fyc = read_MEPS(spark, "data/h224.parquet")

# Stata
fyc = read_MEPS(spark, "data/h224.dta")

# SAS transport (pre-2017 files)
fyc = read_MEPS(spark, "data/h192.ssp")

# SAS data
fyc = read_MEPS(spark, "data/h224.sas7bdat")

# CSV
fyc = read_MEPS(spark, "data/h224.csv")
```

The file format is auto-detected from the extension. You can override it explicitly:

```python
fyc = read_MEPS(spark, "data/h224_renamed", file_format="parquet")
```

## 3. Load a MEPS file by year and type

Use `get_meps_file()` to look up the standard MEPS file name, then load:

```python
from utils.data_loader import get_meps_file, read_MEPS

# Equivalent of R's: read_MEPS(year=2020, type="FYC")
file_name = get_meps_file(year=2020, file_type="FYC")   # returns "h224"
fyc = read_MEPS(spark, f"data/{file_name}.parquet")

# Other file types
cond_file = get_meps_file(year=2020, file_type="COND")   # "h222"
pmed_file = get_meps_file(year=2020, file_type="PMED")   # "h220a"
clnk_file = get_meps_file(year=2020, file_type="CLNK")   # "h220if1"
```

The lookup covers years **2016-2021** for common file types (FYC, COND, PMED/RX, CLNK, OB, ER, IP, OP, DV). See the `MEPS_FILE_LOOKUP` dictionary in `utils/data_loader.py` for the full list and instructions on extending it.

## 4. Pre-convert to Parquet (recommended)

```python
from utils.data_loader import convert_to_parquet

# One-time conversion
convert_to_parquet("data/h224.dta",  "data/h224.parquet")
convert_to_parquet("data/h192.ssp",  "data/h192.parquet")
```

# Supported file formats

| Extension    | Method                                       | Notes                                    |
|------------- |----------------------------------------------|------------------------------------------|
| `.parquet`   | Native `spark.read.parquet()`                | **Recommended** -- best performance      |
| `.csv`       | Native `spark.read.csv()` with header inference | Good for small files or quick inspection |
| `.dta`       | `pandas.read_stata()` -> Spark DataFrame     | Stata format, common for 2017+ files     |
| `.ssp`       | `pandas.read_sas(format='xport')` -> Spark   | SAS transport, common for pre-2017 files |
| `.sas7bdat`  | `pandas.read_sas(format='sas7bdat')` -> Spark | SAS V9 data files                        |

For `.ssp`, `.sas7bdat`, and `.dta` files, the data is loaded into a pandas DataFrame first and then converted to a Spark DataFrame. This works well for typical MEPS file sizes but may be memory-constrained for very large datasets. Pre-converting to Parquet avoids this limitation.

# Parquet pre-conversion workflow

For best performance with PySpark, we recommend a one-time conversion of MEPS source files (`.ssp`, `.dta`, `.sas7bdat`) to Parquet format:

1. **Download** the MEPS PUF files from [the MEPS website](https://meps.ahrq.gov/mepsweb/data_stats/download_data_files.jsp)
2. **Convert** each file to Parquet using `convert_to_parquet()`
3. **Use** the Parquet files in all subsequent PySpark analyses

Benefits of Parquet:
- Columnar storage enables reading only the columns you need
- Efficient compression reduces storage and I/O
- Native Spark support -- no pandas intermediary needed
- Schema is preserved in the file metadata

# Survey estimation (Phase 2+)

MEPS uses a complex survey design with stratification (`VARSTR`), clustering (`VARPSU`), and person-level weights (e.g. `PERWT20F`). Proper analysis requires accounting for this design to produce unbiased national estimates and correct standard errors.

In R, the `survey` package handles this via `svydesign()`, `svymean()`, `svytotal()`, etc. The PySpark equivalent will be developed in Phase 2 of the migration, likely using:

- **Spark DataFrame operations** with manual Taylor-series linearization for variance estimation
- **Integration with statsmodels or pandas** for survey-aware estimation on aggregated data
- **Custom UDFs** wrapping established survey estimation logic

Until Phase 2 is complete, you can use the data loader to read MEPS files into Spark, perform data manipulation and joins, then collect subsets to pandas for survey-weighted estimation using Python's `statsmodels` or the `samplics` package.
