"""Download MEPS data files from the AHRQ website.

Mirrors the download pattern from R/workshop_exercises/ggplot_example.R:
  download.file("https://meps.ahrq.gov/mepsweb/data_files/pufs/h163ssp.zip", ...)
"""

from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path

import requests

_MEPS_BASE_URL = "https://meps.ahrq.gov/mepsweb/data_files/pufs"


def _build_download_url(file_name: str, fmt: str = "ssp") -> str:
    """Build the download URL for a MEPS PUF file.

    Args:
        file_name: MEPS file identifier (e.g., 'h224').
        fmt: File format suffix ('ssp', 'dta', 'sas7bdat').

    Returns:
        Full download URL.
    """
    suffix_map = {
        "ssp": "ssp",
        "xport": "ssp",
        "dta": "dta",
        "sas7bdat": "sas7bdat",
    }
    url_suffix = suffix_map.get(fmt, fmt)
    return f"{_MEPS_BASE_URL}/{file_name}{url_suffix}.zip"


def download_meps(
    file_name: str,
    dest_dir: str,
    fmt: str = "ssp",
    overwrite: bool = False,
) -> str:
    """Download a MEPS data file from the AHRQ website.

    Downloads the zip file, extracts it, and returns the path to the extracted file.

    Args:
        file_name: MEPS file identifier (e.g., 'h224', 'h192').
        dest_dir: Directory to save the extracted file to.
        fmt: File format to download ('ssp', 'dta', 'sas7bdat'). Defaults to 'ssp'.
        overwrite: If True, re-download even if file exists. Defaults to False.

    Returns:
        Path to the extracted data file.

    Example:
        >>> path = download_meps('h192', '/data/meps', fmt='ssp')
        >>> # Downloads https://meps.ahrq.gov/mepsweb/data_files/pufs/h192ssp.zip
        >>> # Extracts to /data/meps/h192.ssp
    """
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)

    ext_map = {"ssp": ".ssp", "xport": ".ssp", "dta": ".dta", "sas7bdat": ".sas7bdat"}
    expected_ext = ext_map.get(fmt, f".{fmt}")

    # Check if already downloaded
    expected_file = dest_path / f"{file_name}{expected_ext}"
    if expected_file.exists() and not overwrite:
        return str(expected_file)

    url = _build_download_url(file_name, fmt)

    # Download to temporary file
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        for chunk in response.iter_content(chunk_size=8192):
            tmp.write(chunk)

    try:
        # Extract zip file
        with zipfile.ZipFile(tmp_path, "r") as zf:
            # Find the data file in the zip
            extracted_path = None
            for name in zf.namelist():
                lower_name = name.lower()
                if lower_name.endswith(expected_ext) or lower_name.endswith(expected_ext.upper()):
                    zf.extract(name, str(dest_path))
                    extracted_path = dest_path / name
                    break

            if extracted_path is None:
                # Extract everything and find the file
                zf.extractall(str(dest_path))
                for name in zf.namelist():
                    candidate = dest_path / name
                    if candidate.exists() and candidate.is_file():
                        extracted_path = candidate
                        break

        if extracted_path is None:
            raise FileNotFoundError(f"Could not find data file in downloaded zip from {url}")

        # Rename to standard location if needed
        final_path = dest_path / f"{file_name}{expected_ext}"
        if extracted_path != final_path and extracted_path.exists():
            extracted_path.rename(final_path)

        return str(final_path)

    finally:
        # Clean up temp file
        os.unlink(tmp_path)


def download_meps_by_year(
    year: int,
    file_type: str,
    dest_dir: str,
    fmt: str | None = None,
    overwrite: bool = False,
) -> str:
    """Download a MEPS file by year and type.

    Automatically resolves the file name from year and type, and selects
    the appropriate format based on the data year.

    Args:
        year: Data year (1996-2022).
        file_type: File type (e.g., 'FYC', 'COND', 'OB', 'RX', 'CLNK').
        dest_dir: Directory to save the extracted file to.
        fmt: File format override. If None, auto-selects based on year.
        overwrite: If True, re-download even if file exists.

    Returns:
        Path to the extracted data file.
    """
    from meps.io.readers import _preferred_format, _resolve_file_name

    file_name = _resolve_file_name(year, file_type)

    if fmt is None:
        fmt = _preferred_format(year, file_type)

    return download_meps(file_name, dest_dir, fmt=fmt, overwrite=overwrite)
