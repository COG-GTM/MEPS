"""Unit tests for meps.transforms.conditions module."""

import polars as pl
import pytest
from meps.transforms.conditions import (
    load_ccs_crosswalk,
    load_ccsr_crosswalk,
)


class TestLoadCCSCrosswalk:
    """Test CCS crosswalk loading (ICD-9, pre-2016)."""

    def test_returns_dataframe(self):
        try:
            ccs = load_ccs_crosswalk()
            assert isinstance(ccs, pl.DataFrame)
        except FileNotFoundError:
            pytest.skip("CCS crosswalk file not available in test environment")

    def test_has_required_columns(self):
        try:
            ccs = load_ccs_crosswalk()
            assert "Condition" in ccs.columns or "CCS" in ccs.columns
        except FileNotFoundError:
            pytest.skip("CCS crosswalk file not available")


class TestLoadCCSRCrosswalk:
    """Test CCSR crosswalk loading (ICD-10, 2016+)."""

    def test_returns_dataframe(self):
        try:
            ccsr = load_ccsr_crosswalk()
            assert isinstance(ccsr, pl.DataFrame)
        except FileNotFoundError:
            pytest.skip("CCSR crosswalk file not available in test environment")

    def test_has_required_columns(self):
        try:
            ccsr = load_ccsr_crosswalk()
            assert "CCSR" in ccsr.columns or "Condition" in ccsr.columns
        except FileNotFoundError:
            pytest.skip("CCSR crosswalk file not available")
