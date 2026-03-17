"""Unit tests for meps.transforms.pooling module."""

import polars as pl
import pytest
from meps.survey.utils import merge_variance_linkage, pool_weights


@pytest.fixture
def pooled_data():
    """Create mock pooled data."""
    return pl.DataFrame({
        "DUPERSID": [f"P{i:04d}" for i in range(20)],
        "PANEL": [21, 22] * 10,
        "VARSTR": [i // 5 + 1 for i in range(20)],
        "VARPSU": [1, 2] * 10,
        "perwt": [2000.0] * 20,
        "totexp": [float(i * 100) for i in range(20)],
    })


class TestAdjustPooledWeights:
    """Test weight adjustment for multi-year pooling."""

    def test_divides_weights(self, pooled_data):
        result = pool_weights(pooled_data, n_years=2, weight_col="perwt")
        assert "poolwt" in result.columns
        # Pooled weight = perwt / n_years
        assert result["poolwt"][0] == pytest.approx(1000.0)

    def test_three_year_pooling(self, pooled_data):
        result = pool_weights(pooled_data, n_years=3, weight_col="perwt")
        assert result["poolwt"][0] == pytest.approx(2000.0 / 3)

    def test_preserves_other_columns(self, pooled_data):
        result = pool_weights(pooled_data, n_years=2, weight_col="perwt")
        assert "DUPERSID" in result.columns
        assert "totexp" in result.columns
        assert result.height == 20


class TestMergeVarianceLinkage:
    """Test variance linkage file merge."""

    def test_merge_adds_linkage_columns(self, pooled_data):
        linkage = pl.DataFrame({
            "DUPERSID": [f"P{i:04d}" for i in range(20)],
            "PANEL": [21, 22] * 10,
            "PSU9619": [1, 2] * 10,
            "STRA9619": [i // 5 + 1 for i in range(20)],
        })
        result = merge_variance_linkage(pooled_data, linkage)
        assert "PSU9619" in result.columns
        assert "STRA9619" in result.columns

    def test_preserves_original_columns(self, pooled_data):
        linkage = pl.DataFrame({
            "DUPERSID": [f"P{i:04d}" for i in range(20)],
            "PANEL": [21, 22] * 10,
            "PSU9619": [1, 2] * 10,
            "STRA9619": [i // 5 + 1 for i in range(20)],
        })
        result = merge_variance_linkage(pooled_data, linkage)
        assert "perwt" in result.columns
        assert "totexp" in result.columns
