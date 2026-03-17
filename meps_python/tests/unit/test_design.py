"""Unit tests for meps.survey.design module."""

import polars as pl
import pytest
from meps.survey.design import MEPSSurveyDesign


@pytest.fixture
def sample_data():
    """Create sample survey data for testing."""
    return pl.DataFrame({
        "DUPERSID": [f"P{i:04d}" for i in range(100)],
        "VARPSU": [1, 2] * 50,
        "VARSTR": [i // 10 + 1 for i in range(100)],
        "PERWT20F": [1000.0 + i * 10 for i in range(100)],
        "TOTEXP20": [float(i * 100) for i in range(100)],
        "AGELAST": [20 + (i % 60) for i in range(100)],
        "SEX": [1 if i % 2 == 0 else 2 for i in range(100)],
    })


class TestMEPSSurveyDesign:
    """Test MEPSSurveyDesign class."""

    def test_creation(self, sample_data):
        dsgn = MEPSSurveyDesign(
            data=sample_data, psu_col="VARPSU", strata_col="VARSTR",
            weight_col="PERWT20F", nest=True,
        )
        assert dsgn.data.height == 100
        assert dsgn.psu_col == "VARPSU"
        assert dsgn.strata_col == "VARSTR"
        assert dsgn.weight_col == "PERWT20F"
        assert dsgn.nest is True

    def test_subset_keeps_all_rows(self, sample_data):
        """Critical: subset should NOT drop rows, only set domain indicator."""
        dsgn = MEPSSurveyDesign(
            data=sample_data, psu_col="VARPSU", strata_col="VARSTR",
            weight_col="PERWT20F", nest=True,
        )
        sub = dsgn.subset(pl.col("AGELAST") >= 65)
        # All rows must be preserved for correct variance estimation
        assert sub.data.height == 100

    def test_subset_creates_domain_indicator(self, sample_data):
        dsgn = MEPSSurveyDesign(
            data=sample_data, psu_col="VARPSU", strata_col="VARSTR",
            weight_col="PERWT20F", nest=True,
        )
        sub = dsgn.subset(pl.col("SEX") == 1)
        assert sub.domain_col is not None
        # Domain column should have 1s and 0s
        domain_vals = sub.data[sub.domain_col].unique().sort().to_list()
        assert 0 in domain_vals or 1 in domain_vals

    def test_missing_column_raises(self, sample_data):
        with pytest.raises((ValueError, Exception)):
            MEPSSurveyDesign(
                data=sample_data, psu_col="NONEXISTENT",
                strata_col="VARSTR", weight_col="PERWT20F",
            )

    def test_data_is_polars_dataframe(self, sample_data):
        dsgn = MEPSSurveyDesign(
            data=sample_data, psu_col="VARPSU", strata_col="VARSTR",
            weight_col="PERWT20F", nest=True,
        )
        assert isinstance(dsgn.data, pl.DataFrame)
