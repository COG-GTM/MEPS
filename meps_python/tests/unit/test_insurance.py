"""Unit tests for meps.transforms.insurance module."""

import polars as pl
import pytest
from meps.transforms.insurance import construct_insurance_flags, construct_insurance_status


@pytest.fixture
def mock_fyc():
    """Create mock FYC data with monthly insurance columns."""
    n = 50
    data = {"DUPERSID": [f"P{i:04d}" for i in range(n)]}

    # Create monthly insurance indicator columns for year 18
    for month in ["JA", "FE", "MA", "AP", "MY", "JU", "JL", "AU", "SE", "OC", "NO", "DE"]:
        for prefix in ["PEG", "POU", "INS", "MCD", "MCR", "TRI"]:
            col = f"{prefix}{month}18"
            data[col] = [1 if i % 3 == 0 else 2 for i in range(n)]

    return pl.DataFrame(data)


class TestConstructInsuranceStatus:
    """Test monthly insurance status construction."""

    def test_returns_dataframe(self, mock_fyc):
        result = construct_insurance_status(mock_fyc, year_suffix="18")
        assert isinstance(result, pl.DataFrame)

    def test_adds_count_columns(self, mock_fyc):
        result = construct_insurance_status(mock_fyc, year_suffix="18")
        # Should add _N columns for month counts
        count_cols = [c for c in result.columns if c.endswith("_N")]
        assert len(count_cols) >= 1


class TestConstructInsuranceFlags:
    """Test insurance flag construction."""

    def test_returns_dataframe(self, mock_fyc):
        result = construct_insurance_status(mock_fyc, year_suffix="18")
        result = construct_insurance_flags(result)
        assert isinstance(result, pl.DataFrame)
