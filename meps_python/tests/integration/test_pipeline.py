"""Integration tests for end-to-end analysis pipelines.

These tests verify the full workflow: load → transform → estimate → output
for representative analyses. They use mock data since actual MEPS data
files are not available in the test environment.
"""

import polars as pl
import pytest
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by, survey_mean, survey_total
from meps.survey.regression import survey_glm


@pytest.fixture
def mock_fyc():
    """Create mock FYC-like data for integration testing."""
    import numpy as np
    np.random.seed(42)
    n = 1000

    return pl.DataFrame({
        "DUPERSID": [f"P{i:06d}" for i in range(n)],
        "VARPSU": np.random.choice([1, 2], n).tolist(),
        "VARSTR": (np.random.choice(range(1, 51), n)).tolist(),
        "PERWT20F": np.random.uniform(500, 5000, n).tolist(),
        "TOTEXP20": np.random.exponential(5000, n).tolist(),
        "TOTSLF20": np.random.exponential(1000, n).tolist(),
        "AGELAST": np.random.randint(0, 90, n).tolist(),
        "SEX": np.random.choice([1, 2], n).tolist(),
        "RACETHX": np.random.choice([1, 2, 3, 4, 5], n).tolist(),
        "INSCOV20": np.random.choice([1, 2, 3], n).tolist(),
    })


class TestSimplePipeline:
    """Test simple person-level analysis pipeline."""

    def test_mean_expenditure(self, mock_fyc):
        """End-to-end: load → design → mean."""
        dsgn = MEPSSurveyDesign(
            data=mock_fyc, psu_col="VARPSU", strata_col="VARSTR",
            weight_col="PERWT20F", nest=True,
        )

        results = list(survey_mean(dsgn, ["TOTEXP20"]))
        assert len(results) == 1
        assert results[0].estimate > 0
        assert results[0].se > 0

    def test_total_expenditure(self, mock_fyc):
        """End-to-end: load → design → total."""
        dsgn = MEPSSurveyDesign(
            data=mock_fyc, psu_col="VARPSU", strata_col="VARSTR",
            weight_col="PERWT20F", nest=True,
        )

        results = list(survey_total(dsgn, ["TOTEXP20"]))
        assert len(results) == 1
        assert results[0].estimate > 0

    def test_subpopulation_analysis(self, mock_fyc):
        """End-to-end: load → design → subset → mean."""
        mock_fyc = mock_fyc.with_columns(
            (pl.col("TOTEXP20") > 0).cast(pl.Int32).alias("has_exp")
        )

        dsgn = MEPSSurveyDesign(
            data=mock_fyc, psu_col="VARPSU", strata_col="VARSTR",
            weight_col="PERWT20F", nest=True,
        )
        sub = dsgn.subset(pl.col("has_exp") == 1)

        results = list(survey_mean(sub, ["TOTEXP20"]))
        assert len(results) >= 1
        assert results[0].estimate > 0


class TestGroupByPipeline:
    """Test grouped analysis pipeline."""

    def test_mean_by_group(self, mock_fyc):
        """End-to-end: load → derive → design → by-group mean."""
        mock_fyc = mock_fyc.with_columns(
            pl.when(pl.col("AGELAST") < 18).then(pl.lit("Under 18"))
            .when(pl.col("AGELAST") <= 64).then(pl.lit("18-64"))
            .otherwise(pl.lit("65+"))
            .alias("agegrps")
        )

        dsgn = MEPSSurveyDesign(
            data=mock_fyc, psu_col="VARPSU", strata_col="VARSTR",
            weight_col="PERWT20F", nest=True,
        )

        results = list(survey_by(dsgn, ["TOTEXP20"], by=["agegrps"], fun="mean"))
        assert len(results) >= 1


class TestRegressionPipeline:
    """Test regression analysis pipeline."""

    def test_logistic_regression(self, mock_fyc):
        """End-to-end: load → derive → design → logistic."""
        mock_fyc = mock_fyc.with_columns([
            (pl.col("TOTEXP20") > 3000).cast(pl.Int32).alias("high_exp"),
            pl.col("SEX").cast(pl.Utf8).alias("SEX_f"),
        ])

        dsgn = MEPSSurveyDesign(
            data=mock_fyc, psu_col="VARPSU", strata_col="VARSTR",
            weight_col="PERWT20F", nest=True,
        )

        result = survey_glm(
            "high_exp ~ AGELAST + C(SEX_f)",
            dsgn, family="quasibinomial"
        )
        assert result is not None

    def test_linear_regression(self, mock_fyc):
        """End-to-end: load → design → linear regression."""
        mock_fyc = mock_fyc.with_columns(
            pl.col("SEX").cast(pl.Utf8).alias("SEX_f")
        )

        dsgn = MEPSSurveyDesign(
            data=mock_fyc, psu_col="VARPSU", strata_col="VARSTR",
            weight_col="PERWT20F", nest=True,
        )

        result = survey_glm(
            "TOTEXP20 ~ AGELAST + C(SEX_f)",
            dsgn, family="gaussian"
        )
        assert result is not None
