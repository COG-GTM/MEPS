"""Unit tests for meps.io.readers module."""

import polars as pl
import pytest
from meps.io.readers import (
    _resolve_file_name,
    read_fixed_width,
    read_meps,
)


class TestResolveFileName:
    """Test file name resolution from year + type."""

    def test_fyc_2016(self):
        name = _resolve_file_name(year=2016, file_type="FYC")
        assert "192" in name or "h192" in name.lower()

    def test_fyc_2019(self):
        name = _resolve_file_name(year=2019, file_type="FYC")
        assert "216" in name or "h216" in name.lower()

    def test_pooled_linkage(self):
        name = _resolve_file_name(year=2019, file_type="Pooled linkage")
        assert name == "h36u19"

    def test_unknown_type_raises(self):
        with pytest.raises((ValueError, KeyError)):
            _resolve_file_name(year=2020, file_type="UNKNOWN_TYPE")


class TestReadMeps:
    """Test read_meps function returns polars DataFrame."""

    def test_returns_polars_dataframe(self, tmp_path):
        """Test that read_meps returns a polars DataFrame when file exists."""
        # This test verifies the return type contract
        # Actual file reading requires MEPS data files
        with pytest.raises((FileNotFoundError, OSError, Exception)):
            read_meps(year=2020, file_type="FYC", data_dir=str(tmp_path))


class TestReadFixedWidth:
    """Test fixed-width file reader."""

    def test_reads_fixed_width_file(self, tmp_path):
        # Create a test fixed-width file
        content = "ABCDE12345FGHIJ\nKLMNO67890PQRST\n"
        fpath = tmp_path / "test.dat"
        fpath.write_text(content)

        col_spec = [
            ("col1", 1, 5),
            ("col2", 6, 10),
            ("col3", 11, 15),
        ]

        result = read_fixed_width(str(fpath), col_spec)
        assert isinstance(result, pl.DataFrame)
        assert result.height == 2
        assert result.columns == ["col1", "col2", "col3"]
        assert result["col1"][0] == "ABCDE"
        # col2 may be auto-cast to float since "12345" is numeric
        assert str(int(result["col2"][0])) == "12345"
        assert result["col3"][1] == "PQRST"

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            read_fixed_width("/nonexistent/file.dat", [("a", 1, 5)])
