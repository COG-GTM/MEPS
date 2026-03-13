"""Medical conditions: Expenditures by Condition, 2015.

Expenditures and utilization by medical condition category using ICD-9/CCS
crosswalk. Merges 6 event files with the Medical Conditions file.

Input files:
 - C:/MEPS/h181.ssp  (2015 FYC)
 - C:/MEPS/h178.ssp  (2015 Medical Conditions)
 - C:/MEPS/h178if1.ssp (2015 CLNK)
 - C:/MEPS/h178d.ssp (2015 IP event file)
 - C:/MEPS/h178e.ssp (2015 ER event file)
 - C:/MEPS/h178f.ssp (2015 OP event file)
 - C:/MEPS/h178g.ssp (2015 OB event file)
 - C:/MEPS/h178h.ssp (2015 HH event file)
 - C:/MEPS/h178a.ssp (2015 RX event file)

Ported from: R/summary_tables_examples/cond_expenditures_2015.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by
from meps.transforms.conditions import load_ccs_crosswalk


def main(data_dir: str = "C:/MEPS") -> None:
    # Load data files
    FYC = read_meps(year=2015, file_type="FYC", data_dir=data_dir).select(
        ["DUPERSID", "PERWT15F", "VARSTR", "VARPSU"]
    )
    COND = read_meps(year=2015, file_type="COND", data_dir=data_dir)
    CLNK = read_meps(year=2015, file_type="CLNK", data_dir=data_dir)

    # Load event files
    IP = read_meps(year=2015, file_type="IP", data_dir=data_dir)
    ER = read_meps(year=2015, file_type="ER", data_dir=data_dir)
    OP = read_meps(year=2015, file_type="OP", data_dir=data_dir)
    OB = read_meps(year=2015, file_type="OB", data_dir=data_dir)
    HH = read_meps(year=2015, file_type="HH", data_dir=data_dir)
    RX = read_meps(year=2015, file_type="RX", data_dir=data_dir)

    # Select expenditure variables per event type
    def _evt(df, xp_col, label, link_col="EVNTIDX"):
        return df.select([
            "DUPERSID", pl.col(link_col).alias("EVNTIDX"), pl.col(xp_col).alias("XP")
        ]).with_columns(pl.lit(label).alias("event_type"))

    IP = _evt(IP, "IPXP15X", "IP")
    ER = _evt(ER, "ERXP15X", "ER")
    OP = _evt(OP, "OPXP15X", "OP")
    OB = _evt(OB, "OBXP15X", "OB")
    HH = _evt(HH, "HHXP15X", "HH")
    RX = _evt(RX, "RXXP15X", "RX", link_col="LINKIDX")

    # Stack all event files
    events = pl.concat([IP, ER, OP, OB, HH, RX])

    # Load CCS crosswalk (ICD-9 for 2015)
    ccs = load_ccs_crosswalk()

    # Merge conditions with CCS codes
    COND = COND.select(["DUPERSID", "CONDIDX", "ICD9CODX"]).join(
        ccs, left_on="ICD9CODX", right_on="ICD9CODX", how="left"
    )

    # Merge conditions with CLNK
    cond_clnk = COND.join(
        CLNK.select(["DUPERSID", "CONDIDX", "EVNTIDX"]),
        on=["DUPERSID", "CONDIDX"], how="inner"
    )

    # De-duplicate by EVNTIDX to avoid double-counting
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

    # Merge with FYC for complete survey design
    pers_fyc = FYC.join(pers_cond, on="DUPERSID", how="left")
    pers_fyc = pers_fyc.with_columns([
        pl.col("cond_XP").fill_null(0),
        pl.col("n_events").fill_null(0),
        pl.col("person_flag").fill_null(0),
    ])

    # Define survey design
    dsgn = MEPSSurveyDesign(
        data=pers_fyc, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT15F", nest=True,
    )

    # Expenditures by condition category
    print("=== Total expenditures by condition category ===")
    cond_dsgn = dsgn.subset(pl.col("person_flag") == 1)
    results = survey_by(cond_dsgn, ["cond_XP"], by=["Condition"], fun="total")
    for est in results:
        print(f"  {est.by_value}: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    print("\n=== Mean expenditure per person by condition ===")
    results = survey_by(cond_dsgn, ["cond_XP"], by=["Condition"], fun="mean")
    for est in results:
        print(f"  {est.by_value}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
