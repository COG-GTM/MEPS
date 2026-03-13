"""ggplot example: Reproducing Figure 1 of Stat brief #491.

Survey ratio + bar chart visualization:
 - Percentage distribution of spending by type of service
 - By age group (<65, 65+)
 - Grouped bar chart with custom colors

Input file: Downloaded h163ssp.zip from MEPS website (2013 FYC)

Ported from: R/workshop_exercises/ggplot_example.R
"""

import polars as pl
from meps.io.readers import read_meps
from meps.survey.design import MEPSSurveyDesign
from meps.survey.estimators import survey_ratio
from meps.viz.charts import export_table, grouped_bar_chart


def main(data_dir: str = "C:/MEPS") -> None:
    # Load 2013 FYC
    h163 = read_meps(year=2013, file_type="FYC", data_dir=data_dir)

    # Create derived variables
    h163 = h163.with_columns([
        (pl.col("OBVEXP13") + pl.col("OPTEXP13") + pl.col("ERTEXP13")).alias("ambexp13"),
        (pl.col("HHAEXP13") + pl.col("HHNEXP13") + pl.col("VISEXP13") + pl.col("OTHEXP13")).alias("hhexp13"),
    ])

    # Survey design
    dsgn = MEPSSurveyDesign(
        data=h163, psu_col="VARPSU", strata_col="VARSTR",
        weight_col="PERWT13F", nest=True,
    )

    # Ratio by type of service
    num_vars = ["IPTEXP13", "ambexp13", "RXEXP13", "DVTEXP13", "hhexp13"]
    den_var = "TOTEXP13"

    # Overall
    pct_total = survey_ratio(dsgn, numerators=num_vars, denominator=den_var)

    # By age group
    lt65 = dsgn.subset(pl.col("AGELAST") < 65)
    ge65 = dsgn.subset(pl.col("AGELAST") >= 65)
    pct_lt65 = survey_ratio(lt65, numerators=num_vars, denominator=den_var)
    pct_ge65 = survey_ratio(ge65, numerators=num_vars, denominator=den_var)

    # Build output table
    labels = ["Hospital IP", "Ambulatory", "RX", "Dental", "HH and Other"]
    rows = []
    for i, label in enumerate(labels):
        rows.append({
            "Type of Service": label,
            "Total": pct_total[i].estimate * 100,
            "<65 years": pct_lt65[i].estimate * 100,
            "65+ years": pct_ge65[i].estimate * 100,
        })

    result_df = pl.DataFrame(rows)
    print(result_df)

    # Export table
    export_table(result_df, "figure1.csv")

    # Create grouped bar chart
    # Melt to long format
    long = result_df.unpivot(
        index="Type of Service",
        on=["Total", "<65 years", "65+ years"],
        variable_name="Age Group",
        value_name="Percentage",
    )

    grouped_bar_chart(
        data=long,
        x="Type of Service",
        y="Percentage",
        group="Age Group",
        title="Figure 1: Percentage Distribution of Spending by Type of Service",
        colors=["rgb(0,115,189)", "rgb(255,197,0)", "rgb(99,16,99)"],
        ylabel="Percentage",
        save_path="figure1.png",
    )

    print("\nChart saved to figure1.png")


if __name__ == "__main__":
    main()
