"""Prescribed drugs, 2016.

Purchases and expenditures by Multum therapeutic class name (TC1):
 - Number of people with purchase
 - Total purchases
 - Total expenditures

Input file: C:/MEPS/h188a.ssp (2016 RX event file)

Ported from: R/summary_tables_examples/pmed_therapeutic_class_2016.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_by


def main(data_dir: str = "C:/MEPS") -> None:
    RX = read_meps(year=2016, file_type="RX", data_dir=data_dir)

    # Define therapeutic classes
    tc1_map = {
        -9: "Not_ascertained", -1: "Inapplicable",
        1: "Anti-infectives", 19: "Antihyperlipidemic_agents",
        20: "Antineoplastics", 28: "Biologicals",
        40: "Cardiovascular_agents", 57: "Central_nervous_system_agents",
        81: "Coagulation_modifiers", 87: "Gastrointestinal_agents",
        97: "Hormones/hormone_modifiers", 105: "Miscellaneous_agents",
        113: "Genitourinary_tract_agents", 115: "Nutritional_products",
        122: "Respiratory_agents", 133: "Topical_agents",
        218: "Alternative_medicines", 242: "Psychotherapeutic_agents",
        254: "Immunologic_agents", 358: "Metabolic_agents",
    }
    RX = RX.with_columns(
        pl.col("TC1").replace_strict(tc1_map, default="Other").alias("TC1name")
    )

    # Aggregate to person-level by therapeutic class
    TC1_pers = (
        RX.group_by(["DUPERSID", "VARSTR", "VARPSU", "TC1name"])
        .agg([
            pl.col("PERWT16F").mean(),
            pl.col("RXXP16X").sum().alias("pers_RXXP"),
            pl.len().alias("n_purchases"),
        ])
        .with_columns(pl.lit(1).alias("persons"))
    )

    dsgn = MEPSSurveyDesign(
        data=TC1_pers, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT16F", nest=True,
    )

    print("=== Purchases and expenditures by therapeutic class ===")
    results = survey_by(dsgn, ["persons", "n_purchases", "pers_RXXP"],
                        by=["TC1name"], fun="total")
    for est in results:
        print(f"  {est.by_value} | {est.variable}: {est.estimate:,.0f} (SE: {est.se:,.0f})")


if __name__ == "__main__":
    main()
