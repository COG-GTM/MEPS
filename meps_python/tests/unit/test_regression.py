"""Unit tests for meps.survey.regression module."""

import polars as pl
import pytest
from meps.survey.design import MEPSSurveyDesign
from meps.survey.regression import survey_glm


@pytest.fixture
def regression_design():
    """Create survey design with data suitable for regression."""
    import numpy as np
    np.random.seed(42)
    n = 500

    data = pl.DataFrame({
        "DUPERSID": [f"P{i:04d}" for i in range(n)],
        "VARPSU": ([1, 2] * (n // 2)),
        "VARSTR": [i // 50 + 1 for i in range(n)],
        "PERWT": [1000.0] * n,
        "y_cont": np.random.normal(100, 20, n).tolist(),
        "y_binary": np.random.binomial(1, 0.3, n).tolist(),
        "x1": np.random.normal(0, 1, n).tolist(),
        "x2": np.random.choice(["A", "B", "C"], n).tolist(),
        "age": np.random.randint(18, 85, n).tolist(),
    })

    return MEPSSurveyDesign(
        data=data, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT", nest=True,
    )


class TestSurveyGLM:
    """Test survey_glm function."""

    def test_gaussian_returns_result(self, regression_design):
        result = survey_glm("y_cont ~ x1 + age", regression_design, family="gaussian")
        assert result is not None
        assert hasattr(result, "summary")

    def test_gaussian_has_coefficients(self, regression_design):
        result = survey_glm("y_cont ~ x1 + age", regression_design, family="gaussian")
        summary = result.summary()
        assert summary is not None

    def test_logistic_returns_result(self, regression_design):
        result = survey_glm("y_binary ~ x1 + age", regression_design, family="quasibinomial")
        assert result is not None

    def test_categorical_predictors(self, regression_design):
        result = survey_glm("y_cont ~ x1 + C(x2)", regression_design, family="gaussian")
        assert result is not None

    def test_invalid_formula_raises(self, regression_design):
        with pytest.raises(Exception):
            survey_glm("nonexistent ~ x1", regression_design, family="gaussian")
