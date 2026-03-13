"""Medical conditions: Expenditures by Condition, 2018.

Expenditures and utilization by medical condition category using ICD-10/CCSR
crosswalk. Merges 6 event files with the Medical Conditions file.

Input files:
 - C:/MEPS/h209.dta  (2018 FYC)
 - C:/MEPS/h207.dta  (2018 Medical Conditions)
 - C:/MEPS/h209if1.dta (2018 CLNK)
 - C:/MEPS/h206d.dta (2018 IP event file)
 - C:/MEPS/h206e.dta (2018 ER event file)
 - C:/MEPS/h206f.dta (2018 OP event file)
 - C:/MEPS/h206g.dta (2018 OB event file)
 - C:/MEPS/h206h.dta (2018 HH event file)
 - C:/MEPS/h206a.dta (2018 RX event file)

Ported from: R/summary_tables_examples/cond_expenditures_2018.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by
from meps.transforms.conditions import load_ccsr_crosswalk


def main(data_dir: str = "C:/MEPS") -> None:
    # Load data files
    FYC = read_meps(year=2018, file_type="FYC", data_dir=data_dir).select(
        ["DUPERSID", "PERWT18F", "VARSTR", "VARPSU"]
    )
    COND = read_meps(year=2018, file_type="COND", data_dir=data_dir)
    CLNK = read_meps(year=2018, file_type="CLNK", data_dir=data_dir)

    # Load event files
    IP = read_meps(year=2018, file_type="IP", data_dir=data_dir)
    ER = read_meps(year=2018, file_type="ER", data_dir=data_dir)
    OP = read_meps(year=2018, file_type="OP", data_dir=data_dir)
    OB = read_meps(year=2018, file_type="OB", data_dir=data_dir)
    HH = read_meps(year=2018, file_type="HH", data_dir=data_dir)
    RX = read_meps(year=2018, file_type="RX", data_dir=data_dir)

    # Select expenditure variables per event type
    def _evt(df, xp_col, label, link_col="EVNTIDX"):
        return df.select([
            "DUPERSID", pl.col(link_col).alias("EVNTIDX"), pl.col(xp_col).alias("XP")
        ]).with_columns(pl.lit(label).alias("event_type"))

    IP = _evt(IP, "IPXP18X", "IP")
    ER = _evt(ER, "ERXP18X", "ER")
    OP = _evt(OP, "OPXP18X", "OP")
    OB = _evt(OB, "OBXP18X", "OB")
    HH = _evt(HH, "HHXP18X", "HH")
    RX = _evt(RX, "RXXP18X", "RX", link_col="LINKIDX")

    # Stack all event files
    events = pl.concat([IP, ER, OP, OB, HH, RX])

    # Load CCSR crosswalk (ICD-10 for 2018)
    ccsr = load_ccsr_crosswalk()

    # Merge conditions with CCSR codes
    cond_cols = ["DUPERSID", "CONDIDX", "ICD10CDX", "CCSR1X", "CCSR2X", "CCSR3X"]
    cond_available = [c for c in cond_cols if c in COND.columns]
    COND = COND.select(cond_available)

    # Use CCSR1X for primary category mapping
    COND = COND.join(
        ccsr.select(["CCSR", "Condition"]).unique(),
        left_on="CCSR1X", right_on="CCSR", how="left"
    )

    # Merge conditions with CLNK
    cond_clnk = COND.join(
        CLNK.select(["DUPERSID", "CONDIDX", "EVNTIDX"]),
        on=["DUPERSID", "CONDIDX"], how="inner"
    )

    # De-duplicate by EVNTIDX
    cond_clnk_nodup = cond_clnk.unique(subset=["DUPERSID", "EVNTIDX"], keep="first")

    # Merge with events
    cond_events = cond_clnk_nodup.join(
        events, on=["DUPERSID", "EVNTIDX"], how="inner"
    )

    # Aggregate to person-condition level
    pers_cond = (
        cond_events
        .group_by(["DUPERSID", "Condition"])
        .agg([
            pl.col("XP").sum().alias("cond_XP"),
            pl.len().alias("n_events"),
        ])
        .with_columns(pl.lit(1).alias("person_flag"))
    )

    # Merge with FYC
    pers_fyc = FYC.join(pers_cond, on="DUPERSID", how="left")
    pers_fyc = pers_fyc.with_columns([
        pl.col("cond_XP").fill_null(0),
        pl.col("n_events").fill_null(0),
        pl.col("person_flag").fill_null(0),
    ])

    # Define survey design
    dsgn = MEPSSurveyDesign(
        data=pers_fyc, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT18F", nest=True,
    )

    # Expenditures by condition
    cond_dsgn = dsgn.subset(pl.col("person_flag") == 1)

    print("=== Total expenditures by condition category ===")
    results = survey_by(cond_dsgn, ["cond_XP"], by=["Condition"], fun="total")
    for est in results:
        print(f"  {est.by_value}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    print("\n=== Mean expenditure per person by condition ===")
    results = survey_by(cond_dsgn, ["cond_XP"], by=["Condition"], fun="mean")
    for est in results:
        print(f"  {est.by_value}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
