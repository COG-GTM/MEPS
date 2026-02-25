"""Tests for linking exercises: cond_pmed_2020 and cond_mv_2020."""

import pytest
from pyspark.sql import functions as F

from meps.workshop_exercises.cond_pmed_2020 import (
    identify_hyperlipidemia,
    link_conditions_to_pmeds,
    aggregate_to_person_level,
    merge_to_fyc,
    run as run_cond_pmed,
)
from meps.workshop_exercises.cond_mv_2020 import (
    identify_mental_health_conditions,
    filter_ob_events_from_clnk,
    link_mh_to_ob_events,
    run as run_cond_mv,
)


class TestCondPmed2020IdentifyHL:
    """Tests for hyperlipidemia identification."""

    def test_filters_end010(self, spark, sample_conditions_2020):
        result = identify_hyperlipidemia(sample_conditions_2020)
        assert result is not None
        # C001 and C003 have END010 in CCSR1X
        assert result.count() == 2

    def test_only_hl_conditions(self, spark, sample_conditions_2020):
        result = identify_hyperlipidemia(sample_conditions_2020)
        for row in result.collect():
            ccsr_values = [row["CCSR1X"], row["CCSR2X"], row["CCSR3X"]]
            assert "END010" in ccsr_values


class TestCondPmed2020LinkToFills:
    """Tests for linking conditions to PMED fills."""

    def test_links_via_clnk(self, spark, sample_conditions_2020, sample_clnk, sample_pmed_2020):
        hl = identify_hyperlipidemia(sample_conditions_2020)
        result = link_conditions_to_pmeds(hl, sample_clnk, sample_pmed_2020)
        assert result is not None

    def test_deduplicates_events(self, spark, sample_conditions_2020, sample_clnk, sample_pmed_2020):
        hl = identify_hyperlipidemia(sample_conditions_2020)
        result = link_conditions_to_pmeds(hl, sample_clnk, sample_pmed_2020)
        total = result.count()
        unique = result.dropDuplicates(["DUPERSID", "EVNTIDX"]).count()
        assert total == unique


class TestCondPmed2020MergeToFYC:
    """Tests for merging to FYC."""

    def test_creates_hl_pmed_flag(self, spark, sample_fyc_2020):
        # Create minimal person-level data
        pers_schema = ["DUPERSID", "N_HL_FILLS", "HL_DRUG_EXP"]
        pers_data = [("P001", 3, 150.0), ("P003", 1, 200.0)]
        pers_df = spark.createDataFrame(pers_data, pers_schema)

        result = merge_to_fyc(sample_fyc_2020, pers_df)
        assert "HL_PMED_FLAG" in result.columns

    def test_flag_values(self, spark, sample_fyc_2020):
        pers_data = [("P001", 3, 150.0)]
        pers_df = spark.createDataFrame(pers_data, ["DUPERSID", "N_HL_FILLS", "HL_DRUG_EXP"])
        result = merge_to_fyc(sample_fyc_2020, pers_df)
        # P001 should have flag=1, others flag=0
        p001 = result.filter(F.col("DUPERSID") == "P001").collect()
        p002 = result.filter(F.col("DUPERSID") == "P002").collect()
        if len(p001) > 0:
            assert p001[0]["HL_PMED_FLAG"] == 1
        if len(p002) > 0:
            assert p002[0]["HL_PMED_FLAG"] == 0


class TestCondMv2020IdentifyMH:
    """Tests for mental health condition identification."""

    def test_filters_mh_codes(self, spark, sample_conditions_2020):
        result = identify_mental_health_conditions(sample_conditions_2020)
        assert result is not None
        # C002 and C004 have MBD codes
        assert result.count() == 2


class TestCondMv2020FilterOBEvents:
    """Tests for OB event filtering from CLNK."""

    def test_filters_eventype_1(self, spark, sample_clnk):
        result = filter_ob_events_from_clnk(sample_clnk)
        assert result is not None
        # All should have EVENTYPE=1
        for row in result.collect():
            assert row["EVENTYPE"] == 1


class TestCondMv2020LinkMHToOB:
    """Tests for linking MH conditions to OB events."""

    def test_links_conditions_to_events(self, spark, sample_conditions_2020, sample_clnk, sample_ob_events_2020):
        mh = identify_mental_health_conditions(sample_conditions_2020)
        clnk_ob = filter_ob_events_from_clnk(sample_clnk)
        result = link_mh_to_ob_events(mh, clnk_ob, sample_ob_events_2020)
        assert result is not None
        assert result.count() > 0
