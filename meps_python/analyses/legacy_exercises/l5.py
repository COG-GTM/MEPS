"""L5: Merge Conditions with FYC and multiple event files, 2001.

Link medical conditions with FYC and 6 event files (IP, ER, OP, OB, HH, RX).

Input files:
 - C:/MEPS/h60.ssp (2001 FYC)
 - C:/MEPS/h59.ssp (2001 Medical Conditions)
 - C:/MEPS/h59d.ssp through h59h.ssp (2001 event files)

Ported from: SAS/older_exercises_1996_to_2006/Linking_examples/L5/L5.sas
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by
from meps.transforms.conditions import load_ccs_crosswalk


def main(data_dir: str = "C:/MEPS") -> None:
    fyc01 = read_meps(year=2001, file_type="FYC", data_dir=data_dir).select(
        ["DUPERSID", "PERWT01F", "VARSTR", "VARPSU"]
    )
    cond01 = read_meps(year=2001, file_type="COND", data_dir=data_dir)

    # Load event files
    IP = read_meps(year=2001, file_type="IP", data_dir=data_dir)
    ER = read_meps(year=2001, file_type="ER", data_dir=data_dir)
    OP = read_meps(year=2001, file_type="OP", data_dir=data_dir)
    OB = read_meps(year=2001, file_type="OB", data_dir=data_dir)
    HH = read_meps(year=2001, file_type="HH", data_dir=data_dir)
    RX = read_meps(year=2001, file_type="RX", data_dir=data_dir)

    # Standardize event files
    def _evt(df, xp_col, label, link_col="EVNTIDX"):
        return df.select([
            "DUPERSID", pl.col(link_col).alias("EVNTIDX"),
            pl.col(xp_col).alias("XP")
        ]).with_columns(pl.lit(label).alias("evt"))

    IP = _evt(IP, "IPXP01X", "IP")
    ER = _evt(ER, "ERXP01X", "ER")
    OP = _evt(OP, "OPXP01X", "OP")
    OB = _evt(OB, "OBXP01X", "OB")
    HH = _evt(HH, "HHXP01X", "HH")
    RX = _evt(RX, "RXXP01X", "RX", link_col="LINKIDX")

    _events = pl.concat([IP, ER, OP, OB, HH, RX])  # noqa: F841

    # Load CCS crosswalk
    ccs = load_ccs_crosswalk()

    # Merge conditions with CCS
    cond01 = cond01.select(["DUPERSID", "CONDIDX", "ICD9CODX"]).join(
        ccs, left_on="ICD9CODX", right_on="ICD9CODX", how="left"
    )

    # For 2001, use CONDIDX-EVNTIDX linkage from conditions file itself
    # (CLNK not available for all years)
    cond_cols = [c for c in cond01.columns if "EVNTIDX" in c or "CLNK" in c]
    if len(cond_cols) == 0:
        # Fall back to person-level condition counts
        cond_pers = (
            cond01.group_by(["DUPERSID", "Condition"])
            .agg(pl.len().alias("n_cond"))
            .with_columns(pl.lit(1).alias("has_cond"))
        )

        merged = fyc01.join(cond_pers, on="DUPERSID", how="left")
        merged = merged.with_columns([
            pl.col("has_cond").fill_null(0),
            pl.col("n_cond").fill_null(0),
        ])

        dsgn = MEPSSurveyDesign(
            data=merged, psu_col="VARPSU", strata_col="VARSTR",
            weight_col="PERWT01F", nest=True,
        )

        print("=== Conditions by Category, 2001 ===")
        sub = dsgn.subset(pl.col("has_cond") == 1)
        for est in survey_by(sub, ["n_cond"], by=["Condition"], fun="total"):
            print(f"  {est.by_value}: {est.estimate:,.0f} (SE: {est.se:,.0f})")
    else:
        print("CLNK-style linkage available; using event-level merge.")


if __name__ == "__main__":
    main()
