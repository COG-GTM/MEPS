"""Unit tests for meps.survey.estimators module."""

import polars as pl
import pytest
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total


@pytest.fixture
def simple_design():
    """Create a simple survey design for testing estimators."""
    data = pl.DataFrame({
        "DUPERSID": [f"P{i:04d}" for i in range(200)],
        "VARPSU": ([1, 2] * 100),
        "VARSTR": [i // 20 + 1 for i in range(200)],
        "PERWT": [1000.0] * 200,
        "x": [float(i) for i in range(200)],
        "binary": [1 if i % 3 == 0 else 0 for i in range(200)],
        "group": ["A" if i < 100 else "B" for i in range(200)],
    })
    return MEPSSurveyDesign(
        data=data, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT", nest=True,
    )


class TestSurveyMean:
    """Test survey_mean function."""

    def test_returns_estimates(self, simple_design):
        est = survey_mean(simple_design, ["x"])
        assert hasattr(est, "estimate")
        assert hasattr(est, "se")
        assert hasattr(est, "variable")

    def test_mean_is_reasonable(self, simple_design):
        est = survey_mean(simple_design, ["x"])
        # Mean of 0..199 should be close to 99.5
        assert 90 < est.estimate < 110

    def test_se_is_positive(self, simple_design):
        est = survey_mean(simple_design, ["x"])
        assert est.se > 0

    def test_binary_mean_is_proportion(self, simple_design):
        est = survey_mean(simple_design, ["binary"])
        # About 1/3 should be 1
        assert 0.2 < est.estimate < 0.5


class TestSurveyTotal:
    """Test survey_total function."""

    def test_returns_estimates(self, simple_design):
        est = survey_total(simple_design, ["x"])
        assert hasattr(est, "estimate")
        assert hasattr(est, "se")

    def test_total_is_reasonable(self, simple_design):
        est = survey_total(simple_design, ["x"])
        # Total = sum(x) * weight / n * N
        # With equal weights of 1000, total ≈ mean * sum_of_weights
        assert est.estimate > 0

    def test_se_is_positive(self, simple_design):
        est = survey_total(simple_design, ["x"])
        assert est.se > 0
