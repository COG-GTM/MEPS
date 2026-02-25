"""PySpark ETL migration of SAS/workshop_exercises/exercise_5b/Exercise5b.sas

Insurance status from monthly insurance variables, 2015.

Original SAS logic:
  - Reads H181 (2015 FYC)
  - Counts number of months with various insurance types using monthly variables:
    PRI, INS, MCD, MCR, TRI, OPA/OPB, group, non-group, public
  - Creates flags: FULL_INSU, GROUP_INS1, GROUP_INS2, NG_INS
  - Survey estimation: PROC SURVEYMEANS by RACETHX domain

Input:  H181 (2015 FYC)
Output: Parquet with monthly insurance count variables and flags
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, when, lit

# Month abbreviations for MEPS monthly variables
MONTHS = ["JA", "FE", "MA", "AP", "MY", "JU", "JL", "AU", "SE", "OC", "NO", "DE"]
YR = "15"


def _count_months(df: DataFrame, prefix: str, suffix: str, value: int = 1) -> DataFrame:
    """Count months where a monthly variable equals a specific value.

    Args:
        df: Input DataFrame.
        prefix: Variable prefix (e.g., 'PRI').
        suffix: Year suffix (e.g., '15').
        value: Value to check for equality.

    Returns:
        DataFrame with added count column.
    """
    count_col = f"{prefix}_N"
    month_cols = [f"{prefix}{m}{suffix}" for m in MONTHS]

    # Build sum expression for available columns
    available = [c for c in month_cols if c in df.columns]
    if not available:
        return df.withColumn(count_col, lit(0))

    expr = sum(when(col(c) == value, lit(1)).otherwise(lit(0)) for c in available)
    return df.withColumn(count_col, expr)


def run_etl(spark: SparkSession, input_path: str, output_path: str) -> DataFrame:
    """Execute the Exercise 5b insurance status ETL pipeline.

    Args:
        spark: Active SparkSession.
        input_path: Path to H181 data file.
        output_path: Path for output Parquet.

    Returns:
        Transformed DataFrame with insurance month counts and flags.
    """
    h181 = spark.read.parquet(input_path)

    df = h181

    # Count months with private insurance (PRI)
    pri_cols = [f"PRI{m}{YR}" for m in MONTHS]
    available_pri = [c for c in pri_cols if c in df.columns]
    if available_pri:
        df = df.withColumn(
            "PRI_N",
            sum(when(col(c) == 1, lit(1)).otherwise(lit(0)) for c in available_pri),
        )
    else:
        df = df.withColumn("PRI_N", lit(0))

    # Count months with any insurance (INS) - value 1 = insured
    ins_cols = [f"INS{m}{YR}X" for m in MONTHS]
    available_ins = [c for c in ins_cols if c in df.columns]
    if available_ins:
        df = df.withColumn(
            "INS_N",
            sum(when(col(c) == 1, lit(1)).otherwise(lit(0)) for c in available_ins),
        )
        # Count months uninsured (INS value = 2)
        df = df.withColumn(
            "UNINS_N",
            sum(when(col(c) == 2, lit(1)).otherwise(lit(0)) for c in available_ins),
        )
        # Count months in survey reference period (INS > 0)
        df = df.withColumn(
            "REF_N",
            sum(when(col(c) > 0, lit(1)).otherwise(lit(0)) for c in available_ins),
        )
    else:
        df = df.withColumn("INS_N", lit(0))
        df = df.withColumn("UNINS_N", lit(0))
        df = df.withColumn("REF_N", lit(0))

    # Count months with Medicaid (MCD)
    mcd_cols = [f"MCD{m}{YR}X" for m in MONTHS]
    available_mcd = [c for c in mcd_cols if c in df.columns]
    if available_mcd:
        df = df.withColumn(
            "MCD_N",
            sum(when(col(c) == 1, lit(1)).otherwise(lit(0)) for c in available_mcd),
        )
    else:
        df = df.withColumn("MCD_N", lit(0))

    # Count months with Medicare (MCR)
    mcr_cols = [f"MCR{m}{YR}X" for m in MONTHS]
    available_mcr = [c for c in mcr_cols if c in df.columns]
    if available_mcr:
        df = df.withColumn(
            "MCR_N",
            sum(when(col(c) == 1, lit(1)).otherwise(lit(0)) for c in available_mcr),
        )
    else:
        df = df.withColumn("MCR_N", lit(0))

    # Count months with TRICARE (TRI)
    tri_cols = [f"TRI{m}{YR}X" for m in MONTHS]
    available_tri = [c for c in tri_cols if c in df.columns]
    if available_tri:
        df = df.withColumn(
            "TRI_N",
            sum(when(col(c) == 1, lit(1)).otherwise(lit(0)) for c in available_tri),
        )
    else:
        df = df.withColumn("TRI_N", lit(0))

    # Count months with Other Public A or B (OPA/OPB)
    opa_cols = [f"OPA{m}{YR}" for m in MONTHS]
    opb_cols = [f"OPB{m}{YR}" for m in MONTHS]
    available_opa = [c for c in opa_cols if c in df.columns]
    available_opb = [c for c in opb_cols if c in df.columns]
    if available_opa or available_opb:
        opa_expr = [when(col(c) == 1, lit(1)).otherwise(lit(0)) for c in available_opa]
        opb_expr = [when(col(c) == 1, lit(1)).otherwise(lit(0)) for c in available_opb]
        combined = []
        for i in range(12):
            opa_val = opa_expr[i] if i < len(opa_expr) else lit(0)
            opb_val = opb_expr[i] if i < len(opb_expr) else lit(0)
            combined.append(when((opa_val == 1) | (opb_val == 1), lit(1)).otherwise(lit(0)))
        df = df.withColumn("OPAB_N", sum(combined))
    else:
        df = df.withColumn("OPAB_N", lit(0))

    # Count months with private group insurance
    peg_cols = [f"PEG{m}{YR}" for m in MONTHS]
    pou_cols = [f"POU{m}{YR}" for m in MONTHS]
    pdk_cols = [f"PDK{m}{YR}" for m in MONTHS]
    avail_peg = [c for c in peg_cols if c in df.columns]
    avail_pou = [c for c in pou_cols if c in df.columns]
    avail_pdk = [c for c in pdk_cols if c in df.columns]
    avail_tri_raw = [c for c in tri_cols if c in df.columns]
    if avail_peg:
        grp_exprs = []
        for i in range(12):
            parts = []
            if i < len(avail_peg):
                parts.append(col(avail_peg[i]) == 1)
            if i < len(avail_tri_raw):
                parts.append(col(avail_tri_raw[i]) == 1)
            if i < len(avail_pou):
                parts.append(col(avail_pou[i]) == 1)
            if i < len(avail_pdk):
                parts.append(col(avail_pdk[i]) == 1)
            if parts:
                condition = parts[0]
                for p in parts[1:]:
                    condition = condition | p
                grp_exprs.append(when(condition, lit(1)).otherwise(lit(0)))
            else:
                grp_exprs.append(lit(0))
        df = df.withColumn("GRP_N", sum(grp_exprs))
    else:
        df = df.withColumn("GRP_N", lit(0))

    # Count months with non-group insurance
    prx_cols = [f"PRX{m}{YR}" for m in MONTHS]
    png_cols = [f"PNG{m}{YR}" for m in MONTHS]
    pog_cols = [f"POG{m}{YR}" for m in MONTHS]
    prs_cols = [f"PRS{m}{YR}" for m in MONTHS]
    avail_prx = [c for c in prx_cols if c in df.columns]
    avail_png = [c for c in png_cols if c in df.columns]
    avail_pog = [c for c in pog_cols if c in df.columns]
    avail_prs = [c for c in prs_cols if c in df.columns]
    if avail_prx or avail_png:
        ng_exprs = []
        for i in range(12):
            parts = []
            if i < len(avail_prx):
                parts.append(col(avail_prx[i]) == 1)
            if i < len(avail_png):
                parts.append(col(avail_png[i]) == 1)
            if i < len(avail_pog):
                parts.append(col(avail_pog[i]) == 1)
            if i < len(avail_prs):
                parts.append(col(avail_prs[i]) == 1)
            if parts:
                condition = parts[0]
                for p in parts[1:]:
                    condition = condition | p
                ng_exprs.append(when(condition, lit(1)).otherwise(lit(0)))
            else:
                ng_exprs.append(lit(0))
        df = df.withColumn("NG_N", sum(ng_exprs))
    else:
        df = df.withColumn("NG_N", lit(0))

    # Count months with any public insurance
    if available_mcr or available_mcd:
        pub_exprs = []
        for i in range(12):
            parts = []
            if i < len(available_mcr):
                parts.append(col(available_mcr[i]) == 1)
            if i < len(available_mcd):
                parts.append(col(available_mcd[i]) == 1)
            if i < len(available_opa):
                parts.append(col(available_opa[i]) == 1)
            if i < len(available_opb):
                parts.append(col(available_opb[i]) == 1)
            if parts:
                condition = parts[0]
                for p in parts[1:]:
                    condition = condition | p
                pub_exprs.append(when(condition, lit(1)).otherwise(lit(0)))
            else:
                pub_exprs.append(lit(0))
        df = df.withColumn("PUB_N", sum(pub_exprs))
    else:
        df = df.withColumn("PUB_N", lit(0))

    # Create insurance flags
    df = df.withColumn("FULL_INSU", when(col("UNINS_N") == 0, 1).otherwise(0))
    df = df.withColumn("GROUP_INS1", when(col("GRP_N") > 0, 1).otherwise(0))
    df = df.withColumn(
        "GROUP_INS2",
        when((col("GRP_N") > 0) & (col("GRP_N") == col("REF_N")), 1).otherwise(0),
    )
    df = df.withColumn("NG_INS", when(col("NG_N") > 0, 1).otherwise(0))

    df.write.mode("overwrite").parquet(output_path)
    return df


def get_job_metadata() -> dict:
    """Return metadata about this ETL job."""
    return {
        "job_name": "exercise_5b",
        "description": "Insurance status from monthly insurance variables, 2015",
        "complexity_tier": "Medium",
        "original_script": "SAS/workshop_exercises/exercise_5b/Exercise5b.sas",
        "input_files": ["H181 (2015 FYC)"],
        "key_transformations": [
            "Count months covered by each insurance type (12 monthly variables each)",
            "Private (PRI_N), Any insurance (INS_N), Uninsured (UNINS_N)",
            "Medicaid (MCD_N), Medicare (MCR_N), TRICARE (TRI_N)",
            "Other Public (OPAB_N), Group (GRP_N), Non-Group (NG_N), Public (PUB_N)",
            "Create flags: FULL_INSU, GROUP_INS1, GROUP_INS2, NG_INS",
        ],
        "survey_design": {
            "strata": "VARSTR",
            "cluster": "VARPSU",
            "weight": "PERWT15F",
        },
    }
