"""Value formatting utilities for MEPS PySpark jobs.

Replicates SAS PROC FORMAT functionality by providing functions to
categorize and label values in PySpark DataFrames.

Key SAS → PySpark mappings:
    - VALUE format  → Python function returning pyspark.sql.Column
    - PUT function  → apply_format()
    - FORMAT statement → Use with .withColumn()
"""

from typing import Dict, List, Optional, Tuple, Union

from pyspark.sql import Column, DataFrame
import pyspark.sql.functions as F


def age_category(
    col: Union[str, Column],
    breaks: Optional[List[int]] = None,
    labels: Optional[List[str]] = None,
) -> Column:
    """Categorize age into groups (replaces SAS VALUE AGEF/AGECAT formats).

    Default breaks create 0-64 and 65+ groups matching the common
    MEPS age categorization.

    Args:
        col: Column name or Column expression for age.
        breaks: List of breakpoints. Default: [0, 64, float('inf')].
        labels: List of labels for each category. Must be len(breaks)-1.
            Default: ['0-64', '65+'].

    Returns:
        A PySpark Column expression with the age category.

    Example:
        >>> df.withColumn("age_group", age_category("AGELAST"))
    """
    if isinstance(col, str):
        col = F.col(col)

    if breaks is None:
        breaks = [0, 64]
        labels = ["0-64", "65+"]

    if labels is None:
        labels = [f"{breaks[i]}-{breaks[i+1]}" for i in range(len(breaks) - 1)]
        labels.append(f"{breaks[-1]}+")

    result = F.lit(None).cast("string")
    for i in range(len(breaks) - 1):
        result = F.when(
            (col >= breaks[i]) & (col <= breaks[i + 1]),
            F.lit(labels[i])
        ).otherwise(result)

    # Handle the last open-ended category
    if len(labels) > len(breaks) - 1:
        result = F.when(
            col > breaks[-1], F.lit(labels[-1])
        ).otherwise(result)
    else:
        result = F.when(
            col > breaks[-1], F.lit(labels[-1])
        ).otherwise(result)

    return result


def gt_zero_format(col: Union[str, Column]) -> Column:
    """Format values as '0' or '>0' (replaces SAS VALUE GTZERO format).

    Args:
        col: Column name or Column expression.

    Returns:
        A PySpark Column expression with '0' or '>0'.
    """
    if isinstance(col, str):
        col = F.col(col)
    return F.when(col == 0, F.lit("0")).otherwise(F.lit(">0"))


def yes_no_format(col: Union[str, Column]) -> Column:
    """Format 1/2 values as 'Yes'/'No' (replaces SAS VALUE YESNO format).

    Args:
        col: Column name or Column expression.

    Returns:
        A PySpark Column expression with 'Yes', 'No', or 'TOTAL'.
    """
    if isinstance(col, str):
        col = F.col(col)
    return (
        F.when(col == 1, F.lit("Yes"))
        .when(col == 2, F.lit("No"))
        .otherwise(F.lit("TOTAL"))
    )


def sex_format(col: Union[str, Column]) -> Column:
    """Format sex codes (replaces SAS VALUE SEX format).

    Args:
        col: Column name or Column expression.

    Returns:
        A PySpark Column expression with 'Male', 'Female', or 'TOTAL'.
    """
    if isinstance(col, str):
        col = F.col(col)
    return (
        F.when(col == 1, F.lit("Male"))
        .when(col == 2, F.lit("Female"))
        .otherwise(F.lit("TOTAL"))
    )


def poverty_category_format(col: Union[str, Column]) -> Column:
    """Format poverty category codes (replaces SAS VALUE POVCAT format).

    Args:
        col: Column name or Column expression.

    Returns:
        A PySpark Column expression with the poverty category label.
    """
    if isinstance(col, str):
        col = F.col(col)
    return (
        F.when(col == 1, F.lit("Poor/Negative"))
        .when(col == 2, F.lit("Near Poor"))
        .when(col == 3, F.lit("Low Income"))
        .when(col == 4, F.lit("Middle Income"))
        .when(col == 5, F.lit("High Income"))
        .otherwise(F.lit("Unknown"))
    )


def insurance_coverage_format(col: Union[str, Column]) -> Column:
    """Format insurance coverage codes (replaces SAS VALUE INSF format).

    Args:
        col: Column name or Column expression.

    Returns:
        A PySpark Column expression with the insurance coverage label.
    """
    if isinstance(col, str):
        col = F.col(col)
    return (
        F.when(col == 1, F.lit("Any Private"))
        .when(col == 2, F.lit("Public Only"))
        .when(col == 3, F.lit("Uninsured"))
        .otherwise(F.lit("Unknown"))
    )


def race_ethnicity_format(col: Union[str, Column]) -> Column:
    """Format race/ethnicity codes (replaces SAS VALUE RACETHX format).

    Args:
        col: Column name or Column expression.

    Returns:
        A PySpark Column expression with the race/ethnicity label.
    """
    if isinstance(col, str):
        col = F.col(col)
    return (
        F.when(col == 1, F.lit("Hispanic"))
        .when(col == 2, F.lit("NH White Only"))
        .when(col == 3, F.lit("NH Black Only"))
        .when(col == 4, F.lit("NH Asian Only"))
        .when(col == 5, F.lit("NH Other/Multiple"))
        .otherwise(F.lit("Unknown"))
    )


def region_format(col: Union[str, Column]) -> Column:
    """Format region codes (replaces SAS VALUE REGION format).

    Args:
        col: Column name or Column expression.

    Returns:
        A PySpark Column expression with the region label.
    """
    if isinstance(col, str):
        col = F.col(col)
    return (
        F.when(col == 1, F.lit("Northeast"))
        .when(col == 2, F.lit("Midwest"))
        .when(col == 3, F.lit("South"))
        .when(col == 4, F.lit("West"))
        .otherwise(F.lit("Unknown"))
    )


def insurance_detail_format(col: Union[str, Column]) -> Column:
    """Format detailed insurance status codes (replaces SAS VALUE INSURANCE).

    Used for the INSURC variable that differentiates Medicare combinations.

    Args:
        col: Column name or Column expression.

    Returns:
        A PySpark Column expression with the detailed insurance label.
    """
    if isinstance(col, str):
        col = F.col(col)
    return (
        F.when(col == 1, F.lit("<65, Any Private"))
        .when(col == 2, F.lit("<65, Public Only"))
        .when(col == 3, F.lit("<65, Uninsured"))
        .when(col == 4, F.lit("65+, Medicare Only"))
        .when(col == 5, F.lit("65+, Medicare and Private"))
        .when(col == 6, F.lit("65+, Medicare and Other Public"))
        .when(col.isin(7, 8), F.lit("65+, No Medicare"))
        .otherwise(F.lit("Unknown"))
    )


def flag_format(col: Union[str, Column]) -> Column:
    """Format expense flag (replaces SAS VALUE FLAG format).

    Args:
        col: Column name or Column expression.

    Returns:
        A PySpark Column expression with 'No expense' or 'Any expense'.
    """
    if isinstance(col, str):
        col = F.col(col)
    return (
        F.when(col == 0, F.lit("No expense"))
        .when(col == 1, F.lit("Any expense"))
        .otherwise(F.lit("No or any expense"))
    )


def apply_format(
    df: DataFrame,
    col_name: str,
    format_map: Dict[Union[int, str], str],
    output_col: Optional[str] = None,
) -> DataFrame:
    """Apply a custom format mapping to a column (general SAS PUT equivalent).

    Args:
        df: Input DataFrame.
        col_name: Name of the column to format.
        format_map: Dictionary mapping input values to formatted labels.
        output_col: Name of the output column. If None, overwrites col_name.

    Returns:
        DataFrame with the formatted column.
    """
    if output_col is None:
        output_col = col_name

    col_expr = F.col(col_name)
    result = F.lit(None).cast("string")

    for value, label in format_map.items():
        result = F.when(col_expr == value, F.lit(label)).otherwise(result)

    return df.withColumn(output_col, result)
