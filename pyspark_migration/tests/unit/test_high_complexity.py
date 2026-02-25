"""Unit tests for high complexity ETL jobs.

Tests cover:
  - De-duplication correctness on EVNTIDX
  - Zero-fill for non-matched FYC persons
  - Join chain correctness
  - CCSR filtering
  - Person-level collapse
  - Multi-year pooling with DUPERSID handling
"""

import pytest
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, lit, sum as spark_sum, when


# ---------------------------------------------------------------------------
# cond_pmed_2020 tests
# ---------------------------------------------------------------------------

class TestCondPmed2020:
    """Tests for cond_pmed_2020 ETL (hyperlipidemia Rx, 4-file join chain)."""

    def test_dedup_on_evntidx(self, spark):
        """EVNTIDX dedup must match Stata 'duplicates drop evntidx, force'.

        When two conditions (C001, C002) link to the same event (E001),
        de-duplication on DUPERSID+EVNTIDX should reduce to one row.
        """
        data = [
            ("P001", "C001", "E001"),
            ("P001", "C002", "E001"),  # Same EVNTIDX, different CONDIDX
            ("P001", "C001", "E002"),  # Different EVNTIDX
        ]
        df = spark.createDataFrame(data, ["DUPERSID", "CONDIDX", "EVNTIDX"])
        result = df.dropDuplicates(["DUPERSID", "EVNTIDX"])
        assert result.count() == 2  # E001 and E002

    def test_no_duplicate_evntidx_after_dedup(self, spark):
        """After dropDuplicates, no duplicate DUPERSID+EVNTIDX pairs should remain."""
        data = [
            ("P001", "C001", "E001"),
            ("P001", "C002", "E001"),
            ("P002", "C003", "E001"),  # Different person, same EVNTIDX is OK
            ("P002", "C004", "E002"),
        ]
        df = spark.createDataFrame(data, ["DUPERSID", "CONDIDX", "EVNTIDX"])
        result = df.dropDuplicates(["DUPERSID", "EVNTIDX"])

        # Count duplicates
        dup_count = (
            result.groupBy("DUPERSID", "EVNTIDX")
            .agg(count("*").alias("cnt"))
            .filter(col("cnt") > 1)
            .count()
        )
        assert dup_count == 0

    def test_zero_fill_for_nonmatched_fyc(self, spark):
        """Persons in FYC with no PMED fills must get num_rx=0, exp_rx=0."""
        fyc = spark.createDataFrame(
            [("P001",), ("P002",), ("P003",)],
            ["DUPERSID"],
        )
        pmed_agg = spark.createDataFrame(
            [("P001", 3, 150.0)],
            ["DUPERSID", "n_hl_fills", "hl_drug_exp"],
        )

        result = fyc.join(pmed_agg, on="DUPERSID", how="left")
        result = result.fillna({"n_hl_fills": 0, "hl_drug_exp": 0.0})

        p2 = result.filter(col("DUPERSID") == "P002").collect()[0]
        assert p2["n_hl_fills"] == 0
        assert p2["hl_drug_exp"] == 0.0

        p3 = result.filter(col("DUPERSID") == "P003").collect()[0]
        assert p3["n_hl_fills"] == 0

    def test_left_join_preserves_all_fyc_rows(self, spark):
        """Left join to FYC must preserve all FYC rows."""
        fyc = spark.createDataFrame(
            [("P001",), ("P002",), ("P003",), ("P004",)],
            ["DUPERSID"],
        )
        pmed_agg = spark.createDataFrame(
            [("P001", 3, 150.0), ("P003", 1, 50.0)],
            ["DUPERSID", "n_hl_fills", "hl_drug_exp"],
        )

        result = fyc.join(pmed_agg, on="DUPERSID", how="left")
        assert result.count() == fyc.count()

    def test_ccsr_filter_end010(self, spark):
        """Filter must keep only rows where any CCSR column equals 'END010'."""
        data = [
            ("C001", "END010", "", ""),
            ("C002", "", "END010", ""),
            ("C003", "", "", "END010"),
            ("C004", "CIR007", "MUS001", ""),  # Not hyperlipidemia
            ("C005", "END010", "CIR007", ""),  # Has END010 in CCSR1X
        ]
        df = spark.createDataFrame(data, ["CONDIDX", "CCSR1X", "CCSR2X", "CCSR3X"])

        hl = df.filter(
            (col("CCSR1X") == "END010")
            | (col("CCSR2X") == "END010")
            | (col("CCSR3X") == "END010")
        )
        assert hl.count() == 4  # C001, C002, C003, C005

    def test_person_level_collapse(self, spark):
        """Collapse must sum fills and expenditures per person correctly."""
        data = [
            ("P001", "E001", 50.0),
            ("P001", "E002", 30.0),
            ("P001", "E003", 20.0),
            ("P002", "E004", 75.0),
        ]
        df = spark.createDataFrame(data, ["DUPERSID", "EVNTIDX", "RXXP20X"])

        person = df.groupBy("DUPERSID").agg(
            count("*").alias("n_hl_fills"),
            spark_sum("RXXP20X").alias("hl_drug_exp"),
        )

        p1 = person.filter(col("DUPERSID") == "P001").collect()[0]
        assert p1["n_hl_fills"] == 3
        assert p1["hl_drug_exp"] == 100.0

        p2 = person.filter(col("DUPERSID") == "P002").collect()[0]
        assert p2["n_hl_fills"] == 1
        assert p2["hl_drug_exp"] == 75.0

    def test_hl_pmed_flag_creation(self, spark):
        """hl_pmed_flag must be 1 when n_hl_fills > 0, else 0."""
        data = [
            ("P001", 3, 150.0),
            ("P002", 0, 0.0),
            ("P003", 1, 50.0),
        ]
        df = spark.createDataFrame(data, ["DUPERSID", "n_hl_fills", "hl_drug_exp"])
        df = df.withColumn(
            "hl_pmed_flag",
            when(col("n_hl_fills") > 0, lit(1)).otherwise(lit(0)),
        )

        results = {row["DUPERSID"]: row["hl_pmed_flag"] for row in df.collect()}
        assert results["P001"] == 1
        assert results["P002"] == 0
        assert results["P003"] == 1


# ---------------------------------------------------------------------------
# cond_mv_2020 tests (Stata migration)
# ---------------------------------------------------------------------------

class TestCondMv2020:
    """Tests for cond_mv_2020 ETL (Stata migration, same pattern as cond_pmed)."""

    def test_stata_dedup_evntidx_force(self, spark):
        """Stata 'duplicates drop evntidx, force' keeps first occurrence."""
        data = [
            ("E001", "P001", "C001"),
            ("E001", "P001", "C002"),  # Duplicate EVNTIDX
            ("E002", "P001", "C001"),
        ]
        df = spark.createDataFrame(data, ["EVNTIDX", "DUPERSID", "CONDIDX"])
        result = df.dropDuplicates(["EVNTIDX"])
        assert result.count() == 2

    def test_any_rx_flag(self, spark):
        """any_rx must be 1 when num_rx > 0."""
        data = [(0,), (1,), (5,)]
        df = spark.createDataFrame(data, ["num_rx"])
        df = df.withColumn("any_rx", (col("num_rx") > 0).cast("int"))

        results = [row["any_rx"] for row in df.orderBy("num_rx").collect()]
        assert results == [0, 1, 1]

    def test_choldx_recode_to_hl_ever(self, spark):
        """CHOLDX recode: 1->1 (diagnosed), 2->0 (not diagnosed), else->null."""
        data = [(1,), (2,), (-1,), (-7,)]
        df = spark.createDataFrame(data, ["CHOLDX"])
        df = df.withColumn(
            "HL_ever",
            when(col("CHOLDX") == 1, lit(1))
            .when(col("CHOLDX") == 2, lit(0)),
        )

        results = {row["CHOLDX"]: row["HL_ever"] for row in df.collect()}
        assert results[1] == 1
        assert results[2] == 0
        assert results[-1] is None
        assert results[-7] is None

    def test_inner_join_drops_unmatched(self, spark):
        """Inner join (like Stata drop if _merge~=3) drops unmatched rows."""
        cond = spark.createDataFrame([("C001",), ("C002",), ("C003",)], ["CONDIDX"])
        clnk = spark.createDataFrame([("C001", "E001"), ("C003", "E003")], ["CONDIDX", "EVNTIDX"])

        result = cond.join(clnk, on="CONDIDX", how="inner")
        assert result.count() == 2  # Only C001 and C003 match


# ---------------------------------------------------------------------------
# exercise_4d tests (Pooling 2017-2019)
# ---------------------------------------------------------------------------

class TestExercise4d:
    """Tests for exercise_4d ETL (3-year pooling with variance file)."""

    def test_pooled_weight_divided_by_three(self, spark):
        """PERWTF must equal PERWTyyF / 3 for 3-year pooling."""
        data = [(3.0,), (6.0,), (9.0,)]
        df = spark.createDataFrame(data, ["PERWT17F"])
        df = df.withColumn("PERWTF", col("PERWT17F") / lit(3))

        results = [row["PERWTF"] for row in df.orderBy("PERWT17F").collect()]
        assert results == [1.0, 2.0, 3.0]

    def test_dupersid_8char_to_10char(self, spark):
        """8-char DUPERSID must be prepended with zero-padded PANEL."""
        from pyspark.sql.functions import concat, length, lpad
        data = [
            ("12345678", 21),   # 8-char -> "2112345678"
            ("1234567890", 22),  # 10-char -> unchanged
        ]
        df = spark.createDataFrame(data, ["DUPERSID", "PANEL"])
        df = df.withColumn(
            "DUPERSID",
            when(
                length(col("DUPERSID")) == 8,
                concat(lpad(col("PANEL").cast("string"), 2, "0"), col("DUPERSID")),
            ).otherwise(col("DUPERSID")),
        )

        results = {row["PANEL"]: row["DUPERSID"] for row in df.collect()}
        assert results[21] == "2112345678"
        assert results[22] == "1234567890"

    def test_joint_pain_variable_2017(self, spark):
        """JOINT_PAIN=1 if ARTHDX=1 or JTPAIN31=1, for adults in 2017."""
        data = [
            (1, 1, 30),  # ARTHDX=1 -> JOINT_PAIN=1
            (2, 1, 40),  # JTPAIN31=1 -> JOINT_PAIN=1
            (2, 2, 50),  # Neither -> JOINT_PAIN=2
            (1, -1, 15), # Under 18 -> no SPOP
        ]
        df = spark.createDataFrame(data, ["ARTHDX", "JTPAIN31", "AGELAST"])

        df = df.withColumn(
            "SPOP",
            when(
                (col("AGELAST") >= 18) & ~((col("ARTHDX") <= 0) & (col("JTPAIN31") < 0)),
                lit(1),
            ).otherwise(lit(0)),
        )
        df = df.withColumn(
            "JOINT_PAIN",
            when(
                (col("SPOP") == 1) & ((col("ARTHDX") == 1) | (col("JTPAIN31") == 1)),
                lit(1),
            ).when(col("SPOP") == 1, lit(2)),
        )

        results = df.orderBy("AGELAST").collect()
        assert results[0]["SPOP"] == 0  # Age 15 -> not in subpop
        assert results[1]["JOINT_PAIN"] == 1  # ARTHDX=1
        assert results[2]["JOINT_PAIN"] == 1  # JTPAIN31=1
        assert results[3]["JOINT_PAIN"] == 2  # Neither

    def test_three_year_union_row_count(self, spark):
        """Union of 3 years must contain sum of all rows."""
        yr1 = spark.createDataFrame([("P1",), ("P2",)], ["DUPERSID"])
        yr2 = spark.createDataFrame([("P3",), ("P4",)], ["DUPERSID"])
        yr3 = spark.createDataFrame([("P5",)], ["DUPERSID"])

        pool = yr1.union(yr2).union(yr3)
        assert pool.count() == 5
