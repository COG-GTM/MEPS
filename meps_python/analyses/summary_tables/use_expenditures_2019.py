"""Use, expenditures, and population, 2019.

Expenditures by event type and source of payment (SOP):
 - Mean expenditure per person

Selected event types: All (TOT), ER (ERT), Inpatient (IPT)

Input file: C:/MEPS/h216.dta (2019 full-year consolidated)

Ported from: R/summary_tables_examples/use_expenditures_2019.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_mean


def main(data_dir: str = "C:/MEPS") -> None:
    # Load FYC file
    FYC = read_meps(year=2019, file_type="FYC", data_dir=data_dir)

    # Aggregate payment sources (2019+: OPU/OPR dropped)
    # OTZ = OFD + STL + OSR + WCP + VA
    FYC = FYC.with_columns([
        (pl.col("TOTOFD19") + pl.col("TOTSTL19") + pl.col("TOTOSR19") +
         pl.col("TOTWCP19") + pl.col("TOTVA19")).alias("TOTOTZ"),
        (pl.col("ERTOFD19") + pl.col("ERTSTL19") + pl.col("ERTOSR19") +
         pl.col("ERTWCP19") + pl.col("ERTVA19")).alias("ERTOTZ"),
        (pl.col("IPTOFD19") + pl.col("IPTSTL19") + pl.col("IPTOSR19") +
         pl.col("IPTWCP19") + pl.col("IPTVA19")).alias("IPTOTZ"),
    ])

    # Define survey design
    dsgn = MEPSSurveyDesign(
        data=FYC, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT19F", nest=True,
    )

    # Mean expenditure per person, by source of payment
    print("=== All event types ===")
    tot_vars = ["TOTEXP19", "TOTSLF19", "TOTPTR19", "TOTMCR19", "TOTMCD19", "TOTOTZ"]
    for est in survey_mean(dsgn, tot_vars):
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    print("\n=== Emergency room visits ===")
    ert_vars = ["ERTEXP19", "ERTSLF19", "ERTPTR19", "ERTMCR19", "ERTMCD19", "ERTOTZ"]
    for est in survey_mean(dsgn, ert_vars):
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")

    print("\n=== Inpatient stays ===")
    ipt_vars = ["IPTEXP19", "IPTSLF19", "IPTPTR19", "IPTMCR19", "IPTMCD19", "IPTOTZ"]
    for est in survey_mean(dsgn, ipt_vars):
        print(f"  {est.variable}: {est.estimate:,.2f} (SE: {est.se:,.2f})")


if __name__ == "__main__":
    main()
