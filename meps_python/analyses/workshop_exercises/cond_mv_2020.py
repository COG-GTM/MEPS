"""Condition-event linkage: Mental health office visits, 2020.

4-file condition-event linkage (OB + COND + CLNK + FYC):
 - Event-level estimates:
   - Number of office-based visits for mental health
   - Total expenditures for office-based mental health treatment
   - Mean expenditure per office-based mental health visit
 - Person-level estimates:
   - Number of people with office-based mental health visits
   - Percent of people with office-based mental health visits
   - Mean expenditure per person for office-based mental health visits

Input files:
 - C:/MEPS/h220g.sas7bdat (2020 Office-based event file)
 - C:/MEPS/h222.sas7bdat (2020 Conditions file)
 - C:/MEPS/h220if1.sas7bdat (2020 CLNK file)
 - C:/MEPS/h224.sas7bdat (2020 Full-Year Consolidated file)

Ported from: R/workshop_exercises/cond_mv_2020.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean, survey_total


def main(data_dir: str = "C:/MEPS") -> None:
    # Load datasets
    ob20 = read_meps(year=2020, file_type="OB", data_dir=data_dir)
    cond20 = read_meps(year=2020, file_type="COND", data_dir=data_dir)
    clnk20 = read_meps(year=2020, file_type="CLNK", data_dir=data_dir)
    fyc20 = read_meps(year=2020, file_type="FYC", data_dir=data_dir)

    # Keep needed variables
    ob20x = ob20.select([
        "PANEL", "DUPERSID", "EVNTIDX", "EVENTRN", "OBDATEYR", "OBDATEMM",
        "TELEHEALTHFLAG", "OBXP20X", "PERWT20F", "VARPSU", "VARSTR",
    ])

    cond20x = cond20.select(
        ["DUPERSID", "CONDIDX", "ICD10CDX"] +
        [c for c in ["CCSR1X", "CCSR2X", "CCSR3X"] if c in cond20.columns]
    )

    fyc20x = fyc20.select(["DUPERSID", "PERWT20F", "VARSTR", "VARPSU"])

    # Filter COND to mental health conditions
    ccsr_cols = [c for c in ["CCSR1X", "CCSR2X", "CCSR3X"] if c in cond20x.columns]
    mental_health = cond20x.with_columns(
        pl.concat_str(ccsr_cols, separator="_").alias("all_CCSR")
    ).filter(
        pl.col("all_CCSR").str.contains("MBD|FAC002|FAC007|NVS011|SYM008|SYM009")
    )

    print(f"Mental health conditions: {mental_health.height}")

    # Filter CLNK to office-based visits (EVENTYPE = 1)
    clnk_ob = clnk20.filter(pl.col("EVENTYPE") == 1)

    # Merge conditions with CLNK
    mh_clnk = mental_health.join(
        clnk_ob, on=["DUPERSID", "CONDIDX"], how="inner"
    )

    # De-duplicate by EVNTIDX
    mh_clnk_nodup = mh_clnk.unique(
        subset=["DUPERSID", "EVNTIDX", "EVENTYPE"], keep="first"
    )

    # Merge with OB event file
    ob_mental_health = ob20x.join(
        mh_clnk_nodup.select(["DUPERSID", "EVNTIDX", "EVENTYPE"]).unique(),
        on=["DUPERSID", "EVNTIDX"], how="inner"
    ).with_columns(pl.lit(1).alias("mh_ob_visit"))

    # Merge with FYC for complete survey design
    ob_mh_fyc = ob_mental_health.with_columns(
        pl.lit(1).alias("mh_ob")
    ).join(
        fyc20x.with_columns(pl.lit(1).alias("fyc")),
        on="DUPERSID", how="full", coalesce=True, suffix="_fyc"
    )

    # Fill VARSTR/VARPSU/PERWT from FYC where missing
    ob_mh_fyc = ob_mh_fyc.with_columns([
        pl.coalesce(["VARSTR", "VARSTR_fyc"]).alias("VARSTR"),
        pl.coalesce(["VARPSU", "VARPSU_fyc"]).alias("VARPSU"),
        pl.coalesce(["PERWT20F", "PERWT20F_fyc"]).alias("PERWT20F"),
    ])

    # ==========================================
    # EVENT-LEVEL ESTIMATES
    # ==========================================
    evnt_dsgn = MEPSSurveyDesign(
        data=ob_mh_fyc, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT20F", nest=True,
    )
    sub_dsgn = evnt_dsgn.subset(pl.col("mh_ob") == 1)

    print("\n=== Event-level estimates ===")
    # Number of visits
    for est in survey_total(sub_dsgn, ["mh_ob_visit"]):
        print(f"  Number of visits: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    # Total expenditures
    for est in survey_total(sub_dsgn, ["OBXP20X"]):
        print(f"  Total expenditures: ${est.estimate:,.0f} (SE: ${est.se:,.0f})")

    # Mean expenditure per visit
    for est in survey_mean(sub_dsgn, ["OBXP20X"]):
        print(f"  Mean exp per visit: ${est.estimate:,.2f} (SE: ${est.se:,.2f})")

    # ==========================================
    # PERSON-LEVEL ESTIMATES
    # ==========================================
    pers_mh = (
        ob_mh_fyc.group_by(["DUPERSID", "VARSTR", "VARPSU", "PERWT20F"])
        .agg([
            pl.col("OBXP20X").sum().alias("persXP"),
            pl.col("mh_ob_visit").sum().alias("pers_nevents"),
            pl.col("mh_ob_visit").mean().alias("mh_ob_visit_pers"),
            pl.col("mh_ob").mean().alias("mh_ob_pers"),
        ])
        .with_columns([
            pl.col("pers_nevents").fill_null(0),
            pl.col("mh_ob_pers").fill_null(0),
            pl.col("mh_ob_visit_pers").fill_null(0),
            pl.col("persXP").fill_null(0),
        ])
    )

    # Person-level survey design
    pers_dsgn = MEPSSurveyDesign(
        data=pers_mh, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT20F", nest=True,
    )
    pers_sub = pers_dsgn.subset(pl.col("mh_ob_pers") == 1)

    print("\n=== Person-level estimates ===")
    # Number of people
    for est in survey_total(pers_dsgn, ["mh_ob_visit_pers"]):
        print(f"  Number of people: {est.estimate:,.0f} (SE: {est.se:,.0f})")

    # Percent of people
    for est in survey_mean(pers_dsgn, ["mh_ob_visit_pers"]):
        print(f"  Percent of people: {est.estimate:.4f} (SE: {est.se:.4f})")

    # Mean exp per person
    for est in survey_mean(pers_sub, ["persXP"]):
        print(f"  Mean exp per person: ${est.estimate:,.2f} (SE: ${est.se:,.2f})")

    # QC: Event-level totals from person-level
    for est in survey_total(pers_sub, ["pers_nevents"]):
        print(f"  QC - Number of visits: {est.estimate:,.0f} (SE: {est.se:,.0f})")
    for est in survey_total(pers_sub, ["persXP"]):
        print(f"  QC - Total exp: ${est.estimate:,.0f} (SE: ${est.se:,.0f})")


if __name__ == "__main__":
    main()
