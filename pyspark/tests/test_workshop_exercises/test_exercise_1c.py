"""Tests for exercise_1c: National health care expenses with median, 2018."""

import pytest

from meps.workshop_exercises.exercise_1c import (
    prepare_data,
    run,
)


class TestPrepareData:
    """Tests for prepare_data function."""

    def test_creates_expense_flag(self, spark, sample_fyc_2018):
        result = prepare_data(spark, input_df=sample_fyc_2018)
        assert result is not None
        cols = result.columns
        assert "WITH_AN_EXPENSE" in cols or "CHAR_WITH_AN_EXPENSE" in cols or "TOTEXP18" in cols

    def test_preserves_row_count(self, spark, sample_fyc_2018):
        result = prepare_data(spark, input_df=sample_fyc_2018)
        assert result.count() == sample_fyc_2018.count()


class TestRun:
    """Tests for run function."""

    def test_returns_dict(self, spark, sample_fyc_2018):
        result = run(spark, input_df=sample_fyc_2018)
        assert isinstance(result, dict)
        assert len(result) > 0
