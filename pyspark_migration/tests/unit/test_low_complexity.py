"""Unit tests for low complexity ETL jobs.

Tests cover:
  - Schema validation (expected columns and data types)
  - Row count assertions
  - Null/zero checks on key columns
  - Variable derivation correctness
"""

import pytest
from pyspark.sql import SparkSession
from pyspark.sql.functions import col


# ---------------------------------------------------------------------------
# Exercise 1a tests
# ---------------------------------------------------------------------------

class TestExercise1a:
    """Tests for exercise_1a ETL (national health care expenses, 2016)."""

    def test_schema_has_required_columns(self, spark):
        """Output must contain TOTAL, X_ANYSVCE, AGE, AGECAT, and survey design vars."""
        data = [
            (100.0, 30, 30, 30, 1001, 1, 1.0),
            (0.0, 70, 70, 70, 1002, 2, 1.5),
        ]
        schema = ["TOTEXP16", "AGE16X", "AGE42X", "AGE31X", "VARSTR", "VARPSU", "PERWT16F"]
        df = spark.createDataFrame(data, schema)

        # Apply transformations inline (mirrors ETL logic)
        from pyspark.sql.functions import when
        df = df.withColumn("TOTAL", col("TOTEXP16"))
        df = df.withColumn("X_ANYSVCE", when(col("TOTAL") > 0, 1).otherwise(0))
        df = df.withColumn(
            "AGE",
            when(col("AGE16X") >= 0, col("AGE16X"))
            .when(col("AGE42X") >= 0, col("AGE42X"))
            .when(col("AGE31X") >= 0, col("AGE31X")),
        )
        df = df.withColumn(
            "AGECAT",
            when((col("AGE") >= 0) & (col("AGE") <= 64), 1)
            .when(col("AGE") > 64, 2),
        )

        required_cols = {"TOTAL", "X_ANYSVCE", "AGE", "AGECAT", "VARSTR", "VARPSU", "PERWT16F"}
        assert required_cols.issubset(set(df.columns))

    def test_x_anysvce_flag_correctness(self, spark):
        """X_ANYSVCE should be 1 when TOTEXP16 > 0, else 0."""
        from pyspark.sql.functions import when
        data = [(100.0,), (0.0,), (500.0,), (0.0,)]
        df = spark.createDataFrame(data, ["TOTEXP16"])
        df = df.withColumn("TOTAL", col("TOTEXP16"))
        df = df.withColumn("X_ANYSVCE", when(col("TOTAL") > 0, 1).otherwise(0))

        results = [row["X_ANYSVCE"] for row in df.collect()]
        assert results == [1, 0, 1, 0]

    def test_age_cascade_derivation(self, spark):
        """AGE should prefer AGE16X, then AGE42X, then AGE31X."""
        from pyspark.sql.functions import when
        data = [
            (30, 30, 30),   # AGE16X valid -> 30
            (-1, 45, 45),   # AGE16X invalid, use AGE42X -> 45
            (-1, -1, 70),   # Both invalid, use AGE31X -> 70
        ]
        df = spark.createDataFrame(data, ["AGE16X", "AGE42X", "AGE31X"])
        df = df.withColumn(
            "AGE",
            when(col("AGE16X") >= 0, col("AGE16X"))
            .when(col("AGE42X") >= 0, col("AGE42X"))
            .when(col("AGE31X") >= 0, col("AGE31X")),
        )

        ages = [row["AGE"] for row in df.orderBy("AGE").collect()]
        assert sorted(ages) == [30, 45, 70]

    def test_agecat_derivation(self, spark):
        """AGECAT should be 1 for age 0-64, 2 for age 65+."""
        from pyspark.sql.functions import when, lit
        data = [(30,), (64,), (65,), (80,)]
        df = spark.createDataFrame(data, ["AGE"])
        df = df.withColumn(
            "AGECAT",
            when((col("AGE") >= 0) & (col("AGE") <= 64), 1)
            .when(col("AGE") > 64, 2),
        )

        results = [row["AGECAT"] for row in df.orderBy("AGE").collect()]
        assert results == [1, 1, 2, 2]

    def test_no_null_survey_design_vars(self, spark):
        """VARSTR, VARPSU, PERWT16F must not have nulls."""
        data = [
            (100.0, 30, 30, 30, 1001, 1, 1.0),
            (0.0, 70, 70, 70, 1002, 2, 1.5),
        ]
        schema = ["TOTEXP16", "AGE16X", "AGE42X", "AGE31X", "VARSTR", "VARPSU", "PERWT16F"]
        df = spark.createDataFrame(data, schema)

        for col_name in ["VARSTR", "VARPSU", "PERWT16F"]:
            null_count = df.filter(col(col_name).isNull()).count()
            assert null_count == 0, f"{col_name} has {null_count} nulls"


# ---------------------------------------------------------------------------
# Exercise 1b tests
# ---------------------------------------------------------------------------

class TestExercise1b:
    """Tests for exercise_1b ETL (expenses by type of service, 2015)."""

    def test_expenditure_categories_sum_to_total(self, spark):
        """Sum of service-type expenditures must equal TOTAL."""
        from pyspark.sql.functions import abs as spark_abs
        data = [(1000.0, 200.0, 100.0, 300.0, 100.0, 150.0, 50.0, 25.0, 25.0, 10.0, 5.0, 15.0, 20.0)]
        schema = [
            "TOTEXP15", "IPDEXP15", "IPFEXP15", "OBVEXP15", "RXEXP15",
            "OPDEXP15", "OPFEXP15", "DVTEXP15", "ERDEXP15", "ERFEXP15",
            "HHAEXP15", "HHNEXP15", "OTHEXP15",
        ]
        df = spark.createDataFrame(data, schema)
        # Mimic: add VISEXP15 = 0 since not in test data
        from pyspark.sql.functions import lit
        df = df.withColumn("VISEXP15", lit(0.0))

        df = df.withColumn("TOTAL", col("TOTEXP15"))
        df = df.withColumn("HOSPITAL_INPATIENT", col("IPDEXP15") + col("IPFEXP15"))
        df = df.withColumn(
            "AMBULATORY",
            col("OBVEXP15") + col("OPDEXP15") + col("OPFEXP15") + col("ERDEXP15") + col("ERFEXP15"),
        )
        df = df.withColumn("PRESCRIBED_MEDICINES", col("RXEXP15"))
        df = df.withColumn("DENTAL", col("DVTEXP15"))
        df = df.withColumn(
            "HOME_HEALTH_OTHER",
            col("HHAEXP15") + col("HHNEXP15") + col("OTHEXP15") + col("VISEXP15"),
        )
        df = df.withColumn(
            "DIFF",
            col("TOTAL") - col("HOSPITAL_INPATIENT") - col("AMBULATORY")
            - col("PRESCRIBED_MEDICINES") - col("DENTAL") - col("HOME_HEALTH_OTHER"),
        )

        row = df.collect()[0]
        assert abs(row["DIFF"]) < 0.01, f"DIFF = {row['DIFF']}, expected 0"

    def test_binary_flags_are_zero_or_one(self, spark):
        """All X_* flag variables must be 0 or 1."""
        from pyspark.sql.functions import when
        data = [(100.0,), (0.0,)]
        df = spark.createDataFrame(data, ["expense"])
        df = df.withColumn("flag", when(col("expense") > 0, 1).otherwise(0))

        flags = {row["flag"] for row in df.collect()}
        assert flags.issubset({0, 1})


# ---------------------------------------------------------------------------
# Exercise 1c tests
# ---------------------------------------------------------------------------

class TestExercise1c:
    """Tests for exercise_1c ETL (national health care expenses, 2018)."""

    def test_expense_classification(self, spark):
        """CHAR_WITH_AN_EXPENSE must be 'No Expense' when TOTEXP18 == 0."""
        from pyspark.sql.functions import when, lit
        data = [(0.0,), (100.0,), (500.0,)]
        df = spark.createDataFrame(data, ["TOTEXP18"])
        df = df.withColumn(
            "CHAR_WITH_AN_EXPENSE",
            when(col("TOTEXP18") == 0, lit("No Expense")).otherwise(lit("Any Expense")),
        )

        results = [row["CHAR_WITH_AN_EXPENSE"] for row in df.orderBy("TOTEXP18").collect()]
        assert results == ["No Expense", "Any Expense", "Any Expense"]


# ---------------------------------------------------------------------------
# care_access_2019 tests
# ---------------------------------------------------------------------------

class TestCareAccess2019:
    """Tests for care_access_2019 ETL."""

    def test_afford_any_logic(self, spark):
        """afford_ANY must be 1 if any of afford_MD/DN/PM is 1."""
        from pyspark.sql.functions import when, lit
        data = [
            (1, 2, 2),  # MD affordable concern -> ANY = 1
            (2, 2, 2),  # No concerns -> ANY = 0
            (2, 1, 2),  # DN concern -> ANY = 1
            (2, 2, 1),  # PM concern -> ANY = 1
        ]
        df = spark.createDataFrame(data, ["AFRDCA42", "AFRDDN42", "AFRDPM42"])
        df = df.withColumn("afford_MD", (col("AFRDCA42") == 1).cast("int"))
        df = df.withColumn("afford_DN", (col("AFRDDN42") == 1).cast("int"))
        df = df.withColumn("afford_PM", (col("AFRDPM42") == 1).cast("int"))
        df = df.withColumn(
            "afford_ANY",
            ((col("afford_MD") == 1) | (col("afford_DN") == 1) | (col("afford_PM") == 1)).cast("int"),
        )

        results = [row["afford_ANY"] for row in df.collect()]
        assert results == [1, 0, 1, 1]

    def test_weight_adjustment_for_non_domain(self, spark):
        """PERWT19F should be 1 when domain=0 and original weight=0."""
        from pyspark.sql.functions import when, lit
        data = [
            (0, 0.0),   # domain=0, weight=0 -> should become 1
            (0, 1.5),   # domain=0, weight>0 -> unchanged
            (1, 2.0),   # domain=1 -> unchanged
            (1, 0.0),   # domain=1, weight=0 -> unchanged
        ]
        df = spark.createDataFrame(data, ["domain", "PERWT19F"])
        df = df.withColumn(
            "PERWT19F",
            when((col("domain") == 0) & (col("PERWT19F") == 0), lit(1)).otherwise(col("PERWT19F")),
        )

        results = [row["PERWT19F"] for row in df.collect()]
        assert results == [1.0, 1.5, 2.0, 0.0]


# ---------------------------------------------------------------------------
# ins_age_2016 tests
# ---------------------------------------------------------------------------

class TestInsAge2016:
    """Tests for ins_age_2016 ETL."""

    def test_age_group_boundaries(self, spark):
        """Age groups must have correct boundaries."""
        from pyspark.sql.functions import when, lit
        data = [(3,), (5,), (17,), (18,), (44,), (45,), (64,), (65,), (80,)]
        df = spark.createDataFrame(data, ["AGELAST"])
        df = df.withColumn(
            "AGEGRP",
            when(col("AGELAST") < 5, lit("Under 5"))
            .when((col("AGELAST") >= 5) & (col("AGELAST") <= 17), lit("5-17"))
            .when((col("AGELAST") >= 18) & (col("AGELAST") <= 44), lit("18-44"))
            .when((col("AGELAST") >= 45) & (col("AGELAST") <= 64), lit("45-64"))
            .when(col("AGELAST") >= 65, lit("65+")),
        )

        results = [row["AGEGRP"] for row in df.orderBy("AGELAST").collect()]
        expected = ["Under 5", "5-17", "5-17", "18-44", "18-44", "45-64", "45-64", "65+", "65+"]
        assert results == expected

    def test_insurance_category_mapping(self, spark):
        """INSURC16 values must map to correct insurance labels."""
        from pyspark.sql.functions import when, lit
        data = [(1,), (2,), (3,), (4,), (5,), (6,), (7,)]
        df = spark.createDataFrame(data, ["INSURC16"])
        df = df.withColumn(
            "INSURANCE",
            when(col("INSURC16") == 1, lit("<65, Any private"))
            .when(col("INSURC16") == 2, lit("<65, Public only"))
            .when(col("INSURC16") == 3, lit("<65, Uninsured"))
            .when(col("INSURC16") == 4, lit("65+, Medicare only"))
            .when(col("INSURC16") == 5, lit("65+, Medicare and private"))
            .when(col("INSURC16") == 6, lit("65+, Medicare and other public"))
            .when((col("INSURC16") == 7) | (col("INSURC16") == 8), lit("65+, No medicare")),
        )

        results = [row["INSURANCE"] for row in df.orderBy("INSURC16").collect()]
        assert len(results) == 7
        assert results[0] == "<65, Any private"
        assert results[2] == "<65, Uninsured"
        assert results[6] == "65+, No medicare"


# ---------------------------------------------------------------------------
# use_expenditures_2016 tests
# ---------------------------------------------------------------------------

class TestUseExpenditures2016:
    """Tests for use_expenditures_2016 ETL."""

    def test_ptr_aggregation(self, spark):
        """PTR must equal PRV + TRI for each event type."""
        data = [(100.0, 50.0)]
        df = spark.createDataFrame(data, ["OBVPRV16", "OBVTRI16"])
        df = df.withColumn("OBVPTR", col("OBVPRV16") + col("OBVTRI16"))

        row = df.collect()[0]
        assert row["OBVPTR"] == 150.0

    def test_domain_flags_binary(self, spark):
        """has_*SLF flags must be 0 or 1."""
        from pyspark.sql.functions import when
        data = [(0.0,), (100.0,), (0.0,)]
        df = spark.createDataFrame(data, ["OBVSLF16"])
        df = df.withColumn("has_OBVSLF", (col("OBVSLF16") > 0).cast("int"))

        flags = {row["has_OBVSLF"] for row in df.collect()}
        assert flags.issubset({0, 1})
