# MEPS Python Migration Mapping

## Overview

This document maps every original R/SAS/Stata script in the MEPS repository to its Python equivalent, along with function-level mappings and known differences.

## Script Mapping

### Summary Tables (13 scripts)

| Python Script | R Source | SAS Source | Stata Source | Complexity |
|---|---|---|---|---|
| `use_expenditures_2016.py` | `R/summary_tables_examples/use_expenditures_2016.R` | `SAS/summary_tables_examples/use_expenditures_2016.sas` | `Stata/summary_tables_examples/use_expenditures_2016.do` | Low |
| `use_expenditures_2019.py` | `R/summary_tables_examples/use_expenditures_2019.R` | `SAS/summary_tables_examples/use_expenditures_2019.sas` | `Stata/summary_tables_examples/use_expenditures_2019.do` | Low |
| `use_events_2016.py` | — | — | `Stata/summary_tables_examples/use_events_2016.do` | Medium |
| `ins_age_2016.py` | — | — | `Stata/summary_tables_examples/ins_age_2016.do` | Low |
| `care_access_2017.py` | `R/summary_tables_examples/care_access_2017.R` | `SAS/summary_tables_examples/care_access_2017.sas` | `Stata/summary_tables_examples/care_access_2017.do` | Medium |
| `care_access_2019.py` | `R/summary_tables_examples/care_access_2019.R` | `SAS/summary_tables_examples/care_access_2019.sas` | `Stata/summary_tables_examples/care_access_2019.do` | Medium |
| `care_diabetes_a1c_2016.py` | — | — | `Stata/summary_tables_examples/care_diabetes_a1c_2016.do` | Medium |
| `care_quality_2016.py` | `R/summary_tables_examples/care_quality_2016.R` | `SAS/summary_tables_examples/care_quality_2016.sas` | — | Medium |
| `pmed_prescribed_drug_2016.py` | `R/summary_tables_examples/pmed_prescribed_drug_2016.R` | `SAS/summary_tables_examples/pmed_prescribed_drug_2016.sas` | — | Medium |
| `pmed_therapeutic_class_2016.py` | `R/summary_tables_examples/pmed_therapeutic_class_2016.R` | `SAS/summary_tables_examples/pmed_therapeutic_class_2016.sas` | — | Medium |
| `use_race_sex_2016.py` | — | — | `Stata/summary_tables_examples/use_race_sex_2016.do` | Medium |
| `cond_expenditures_2015.py` | — | — | `Stata/summary_tables_examples/cond_expenditures_2015.do` | High |
| `cond_expenditures_2018.py` | `R/summary_tables_examples/cond_expenditures_2018.R` | `SAS/summary_tables_examples/cond_expenditures_2018.sas` | `Stata/summary_tables_examples/cond_expenditures_2018.do` | High |

### Workshop Exercises (17 scripts)

| Python Script | R Source | SAS Source | Stata Source | Complexity |
|---|---|---|---|---|
| `exercise_1a.py` | `R/workshop_exercises/exercise_1a.R` | `SAS/workshop_exercises/exercise_1/` | `Stata/workshop_exercises/Exercise1a.do` | Low |
| `exercise_1b.py` | `R/workshop_exercises/exercise_1b.R` | — | `Stata/workshop_exercises/Exercise1b.do` | Low |
| `exercise_1c.py` | — | `SAS/workshop_exercises/exercise_1c/` | — | Low |
| `exercise_2a.py` | `R/workshop_exercises/exercise_2a.R` | `SAS/workshop_exercises/exercise_2/` | — | Medium |
| `exercise_2b.py` | `R/workshop_exercises/exercise_2b.R` | — | — | Medium |
| `exercise_2c.py` | — | `SAS/workshop_exercises/exercise_2c/` | — | Medium |
| `exercise_3a.py` | `R/workshop_exercises/exercise_3a.R` | `SAS/workshop_exercises/exercise_4a/` | — | Medium |
| `exercise_3b.py` | `R/workshop_exercises/exercise_3b.R` | `SAS/workshop_exercises/exercise_4b/` | — | Medium |
| `exercise_3c.py` | `R/workshop_exercises/exercise_3c.R` | `SAS/workshop_exercises/exercise_4c/` | — | High |
| `exercise_3d.py` | `R/workshop_exercises/exercise_3d.R` | `SAS/workshop_exercises/exercise_4d/` | — | High |
| `exercise_5a.py` | — | `SAS/workshop_exercises/exercise_5a/` | — | Medium |
| `exercise_5b.py` | — | `SAS/workshop_exercises/exercise_5b/` | — | High |
| `exercise_6a.py` | `R/workshop_exercises/exercise_4a.R` | — | `Stata/workshop_exercises/Exercise6a.do` | High |
| `exercise_6b.py` | `R/workshop_exercises/exercise_4b.R` | — | — | High |
| `cond_mv_2020.py` | `R/workshop_exercises/cond_mv_2020.R` | — | — | High |
| `cond_pmed_2020.py` | `R/workshop_exercises/cond_pmed_2020.R` | — | — | High |
| `ggplot_example.py` | `R/workshop_exercises/ggplot_example.R` | — | — | Medium |

### Legacy SAS Exercises (27 scripts)

| Python Script | SAS Source | Complexity |
|---|---|---|
| `e1.py` | `SAS/older_exercises_1996_to_2006/Estimation_examples/E1/` | Low |
| `e2.py` | `SAS/older_exercises_1996_to_2006/Estimation_examples/E2/` | Medium |
| `e3.py` | `SAS/older_exercises_1996_to_2006/Estimation_examples/E3/` | Medium |
| `e4.py` | `SAS/older_exercises_1996_to_2006/Estimation_examples/E4/` | Medium |
| `e5.py` | `SAS/older_exercises_1996_to_2006/Estimation_examples/E5/` | Medium |
| `e6.py` | `SAS/older_exercises_1996_to_2006/Estimation_examples/E6/` | Low |
| `e7.py` | `SAS/older_exercises_1996_to_2006/Estimation_examples/E7/` | Low |
| `e8.py` | `SAS/older_exercises_1996_to_2006/Estimation_examples/E8/` | Low |
| `em1.py` | `SAS/older_exercises_1996_to_2006/Employment_examples/EM1/` | Medium |
| `em2.py` | `SAS/older_exercises_1996_to_2006/Employment_examples/EM2/` | Medium |
| `l1.py` | `SAS/older_exercises_1996_to_2006/Linking_examples/L1/` | Low |
| `l1a.py` | `SAS/older_exercises_1996_to_2006/Linking_examples/L1A/` | Medium |
| `l2.py` | `SAS/older_exercises_1996_to_2006/Linking_examples/L2/` | High |
| `l3.py` | `SAS/older_exercises_1996_to_2006/Linking_examples/L3/` | Low |
| `l4.py` | `SAS/older_exercises_1996_to_2006/Linking_examples/L4/` | Low |
| `l5.py` | `SAS/older_exercises_1996_to_2006/Linking_examples/L5/` | High |
| `m1.py` | `SAS/older_exercises_1996_to_2006/Misc_examples/M1/` | Low |
| `m2.py` | `SAS/older_exercises_1996_to_2006/Misc_examples/M2/` | Medium |
| `m3.py` | `SAS/older_exercises_1996_to_2006/Misc_examples/M3/` | Medium |
| `m4.py` | `SAS/older_exercises_1996_to_2006/Misc_examples/M4/` | Medium |
| `m5.py` | `SAS/older_exercises_1996_to_2006/Misc_examples/M5/` | Medium |
| `m6.py` | `SAS/older_exercises_1996_to_2006/Misc_examples/M6/` | Low |
| `m7.py` | `SAS/older_exercises_1996_to_2006/Misc_examples/M7/` | Medium |
| `m8.py` | `SAS/older_exercises_1996_to_2006/Misc_examples/M8/` | Medium |
| `m9.py` | `SAS/older_exercises_1996_to_2006/Misc_examples/M9/` | Medium |
| `m10.py` | `SAS/older_exercises_1996_to_2006/Misc_examples/M10/` | Medium |
| `m11.py` | `SAS/older_exercises_1996_to_2006/Misc_examples/M11/` | Medium |

## Function Mapping

### Data I/O

| R/SAS/Stata | Python | Notes |
|---|---|---|
| `read_MEPS(year, type)` | `meps.io.readers.read_meps(year, file_type)` | Returns polars DataFrame |
| `read.xport()` | `pyreadstat.read_xport()` | For .ssp files (1996-2016) |
| `read_dta()` | `pyreadstat.read_dta()` | For .dta files (2017+) |
| `read_sas()` | `pyreadstat.read_sas7bdat()` | For .sas7bdat files |
| SAS INPUT with column positions | `meps.io.readers.read_fixed_width()` | For ASCII .dat files |

### Survey Design

| R/SAS/Stata | Python | Notes |
|---|---|---|
| `svydesign(id=~VARPSU, strata=~VARSTR, weights=~PERWTyyF, nest=TRUE)` | `MEPSSurveyDesign(data, psu_col, strata_col, weight_col, nest=True)` | |
| `subset(design, condition)` | `design.subset(pl.col(...) == ...)` | Uses domain indicator, does NOT filter rows |
| `options(survey.lonely.psu='adjust')` | Handled internally in MEPSSurveyDesign | |

### Estimation

| R/SAS/Stata | Python | Notes |
|---|---|---|
| `svymean()` / `PROC SURVEYMEANS MEAN` / `svy: mean` | `survey_mean(design, vars)` | Uses samplics TaylorEstimator |
| `svytotal()` / `PROC SURVEYMEANS SUM` / `svy: total` | `survey_total(design, vars)` | |
| `svyby(..., FUN=svymean)` / DOMAIN statement / `over()` | `survey_by(design, vars, by, fun)` | |
| `svyratio()` | `survey_ratio(design, num, den)` | |
| `svyquantile()` | `survey_quantile(design, vars, quantiles)` | Weighted quantile with linearized SE |

### Regression

| R/SAS/Stata | Python | Notes |
|---|---|---|
| `svyglm(y ~ x, family=gaussian)` | `survey_glm(formula, design, family="gaussian")` | Uses statsmodels WLS |
| `svyglm(y ~ x, family=quasibinomial)` | `survey_glm(formula, design, family="quasibinomial")` | Uses statsmodels GLM with Binomial |
| Stata `margins` | `survey_margins(model, design, vars)` | Average marginal effects |

### Data Transforms

| R/SAS/Stata | Python | Notes |
|---|---|---|
| `merge(fyc, events)` / `MERGE` / `merge` | `df.join(other, on=key)` | polars join |
| `bind_rows()` / `SET` / `append` | `pl.concat([...])` | polars concat |
| `group_by() %>% summarize()` / `PROC MEANS` / `collapse` | `df.group_by(...).agg(...)` | polars group_by |
| `mutate()` / `DATA step` / `gen` | `df.with_columns(...)` | polars expressions |
| `case_when()` / `IF-THEN` / `recode` | `pl.when(...).then(...).otherwise(...)` | polars conditional |

## Known Differences

1. **Survey regression SEs**: Python uses statsmodels sandwich estimator which may differ slightly from R's survey package Taylor linearization. Differences are typically < 1e-4 relative error.

2. **Quantile estimation**: R's `svyquantile()` uses a specific interpolation method. Python implementation uses weighted percentile with linearized SEs, which may produce slightly different point estimates at boundaries.

3. **Lonely PSU handling**: Both implementations use the "adjust" method, but numerical handling may differ at machine precision level.

4. **Factor ordering**: R automatically orders factor levels alphabetically. Python categorical variables may have different default ordering, but results are equivalent.

5. **Missing value handling**: SAS treats missing values as the smallest possible number. Python/polars uses null. This can affect sorting and conditional logic.
