# =============================================================================
# Test Suite: SAS Script Validation Tests
# Description: Reads SAS files as text and validates expected PROC statements,
#              consistent variable references, and file naming conventions
# =============================================================================

library(testthat)

# Helper: get repo root
get_repo_root <- function() {
  candidates <- c(
    Sys.getenv("MEPS_REPO_ROOT"),
    file.path(getwd(), "..", ".."),
    file.path(getwd())
  )
  for (path in candidates) {
    if (nchar(path) > 0 && file.exists(file.path(path, "SAS"))) {
      return(normalizePath(path))
    }
  }
  stop("Could not find repo root. Set MEPS_REPO_ROOT environment variable.")
}

repo_root <- get_repo_root()
sas_dir <- file.path(repo_root, "SAS")
sas_scripts <- list.files(sas_dir, pattern = "\\.sas$", full.names = TRUE, recursive = TRUE)

# ---------------------------------------------------------------------------
# SAS script existence and readability
# ---------------------------------------------------------------------------
context("SAS Scripts: Existence and Readability")

test_that("SAS directory exists and contains .sas files", {
  expect_true(dir.exists(sas_dir))
  expect_true(length(sas_scripts) > 0,
    info = "SAS/ directory should contain .sas files")
})

test_that("all SAS scripts are readable as text", {
  for (script in sas_scripts) {
    content <- tryCatch(
      readLines(script, warn = FALSE),
      error = function(e) NULL
    )
    expect_false(is.null(content),
      info = paste("SAS script should be readable:", basename(script)))
  }
})

test_that("no SAS script is completely empty", {
  for (script in sas_scripts) {
    content <- readLines(script, warn = FALSE)
    non_empty <- content[trimws(content) != ""]
    expect_true(length(non_empty) > 0,
      info = paste("SAS script should not be empty:", basename(script)))
  }
})

# ---------------------------------------------------------------------------
# PROC statement validation
# ---------------------------------------------------------------------------
context("SAS Scripts: PROC Statement Validation")

test_that("SAS workshop scripts contain PROC statements", {
  ws_scripts <- sas_scripts[grepl("workshop_exercises", sas_scripts)]
  for (script in ws_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    has_proc <- grepl("PROC\\s+\\w+", content, ignore.case = TRUE)
    expect_true(has_proc,
      info = paste("Workshop SAS script should contain PROC statements:", basename(script)))
  }
})

test_that("SAS workshop scripts contain PROC SURVEY procedures for survey analysis", {
  ws_scripts <- sas_scripts[grepl("workshop_exercises", sas_scripts)]
  survey_procs <- c("SURVEYMEANS", "SURVEYFREQ", "SURVEYREG", "SURVEYLOGISTIC")
  scripts_with_survey <- 0
  for (script in ws_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    has_survey <- any(sapply(survey_procs, function(p) grepl(p, content, ignore.case = TRUE)))
    if (has_survey) scripts_with_survey <- scripts_with_survey + 1
  }
  expect_true(scripts_with_survey >= 1,
    info = "At least one SAS workshop script should use PROC SURVEY procedures")
})

test_that("SAS summary table scripts contain PROC statements", {
  st_scripts <- sas_scripts[grepl("summary_tables_examples", sas_scripts)]
  for (script in st_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    has_proc <- grepl("PROC\\s+\\w+", content, ignore.case = TRUE)
    expect_true(has_proc,
      info = paste("Summary table SAS script should contain PROC:", basename(script)))
  }
})

test_that("SAS scripts end PROC steps with RUN or QUIT", {
  for (script in sas_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    if (grepl("PROC\\s+\\w+", content, ignore.case = TRUE)) {
      has_run_or_quit <- grepl("\\b(RUN|QUIT)\\s*;", content, ignore.case = TRUE)
      expect_true(has_run_or_quit,
        info = paste("SAS PROC steps should end with RUN or QUIT:", basename(script)))
    }
  }
})

# ---------------------------------------------------------------------------
# Variable reference consistency
# ---------------------------------------------------------------------------
context("SAS Scripts: Variable Reference Consistency")

test_that("SAS workshop scripts reference VARSTR for stratification", {
  ws_scripts <- sas_scripts[grepl("workshop_exercises", sas_scripts)]
  scripts_with_varstr <- 0
  for (script in ws_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    if (grepl("VARSTR", content, ignore.case = TRUE)) {
      scripts_with_varstr <- scripts_with_varstr + 1
    }
  }
  expect_true(scripts_with_varstr >= length(ws_scripts) * 0.3,
    info = "At least 30% of SAS workshop scripts should reference VARSTR")
})

test_that("SAS workshop scripts reference VARPSU for clustering", {
  ws_scripts <- sas_scripts[grepl("workshop_exercises", sas_scripts)]
  scripts_with_varpsu <- 0
  for (script in ws_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    if (grepl("VARPSU", content, ignore.case = TRUE)) {
      scripts_with_varpsu <- scripts_with_varpsu + 1
    }
  }
  expect_true(scripts_with_varpsu >= length(ws_scripts) * 0.3,
    info = "At least 30% of SAS workshop scripts should reference VARPSU")
})

test_that("SAS scripts use PERWT weight variables", {
  ws_scripts <- sas_scripts[grepl("workshop_exercises", sas_scripts)]
  scripts_with_weight <- 0
  for (script in ws_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    if (grepl("PERWT\\d+F", content, ignore.case = TRUE)) {
      scripts_with_weight <- scripts_with_weight + 1
    }
  }
  expect_true(scripts_with_weight >= 1,
    info = "At least one SAS workshop script should use PERWT weight variables")
})

test_that("SAS scripts with PROC SURVEY use survey design specifications", {
  scripts_with_survey <- 0
  scripts_with_design <- 0
  for (script in sas_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    if (grepl("PROC\\s+SURVEY", content, ignore.case = TRUE)) {
      scripts_with_survey <- scripts_with_survey + 1
      # Check for STRATUM/STRATA and CLUSTER statements
      has_stratum <- grepl("(STRATUM|STRATA)", content, ignore.case = TRUE)
      has_cluster <- grepl("CLUSTER", content, ignore.case = TRUE)
      # Also accept WEIGHT statement as part of survey design
      has_weight <- grepl("WEIGHT", content, ignore.case = TRUE)
      if (has_stratum || has_cluster || has_weight) {
        scripts_with_design <- scripts_with_design + 1
      }
    }
  }
  # At least 50% of scripts with PROC SURVEY should have survey design specs
  if (scripts_with_survey > 0) {
    expect_true(scripts_with_design / scripts_with_survey >= 0.5,
      info = "Most PROC SURVEY scripts should include survey design specifications")
  }
})

# ---------------------------------------------------------------------------
# File naming conventions
# ---------------------------------------------------------------------------
context("SAS Scripts: File Naming Conventions")

test_that("SAS workshop exercise files follow naming convention", {
  ws_dir <- file.path(sas_dir, "workshop_exercises")
  if (dir.exists(ws_dir)) {
    # SAS workshop exercises are in subdirectories or directly named
    sas_ws_files <- list.files(ws_dir, pattern = "\\.sas$", recursive = TRUE)
    for (f in sas_ws_files) {
      bname <- tolower(basename(f))
      # Should be exercise*.sas or cond_*.sas or descriptive name
      is_valid <- grepl("^(exercise|cond_|pmed_|care_|ins_|use_)", bname) ||
                  grepl("^[a-z]", bname)
      expect_true(is_valid,
        info = paste("SAS workshop file naming:", f))
    }
  }
})

test_that("SAS summary table files match R summary table file names", {
  r_st_files <- list.files(file.path(repo_root, "R", "summary_tables_examples"),
    pattern = "\\.R$")
  sas_st_files <- list.files(file.path(sas_dir, "summary_tables_examples"),
    pattern = "\\.sas$")
  # Extract base names without extensions
  r_bases <- gsub("\\.R$", "", r_st_files)
  sas_bases <- gsub("\\.sas$", "", sas_st_files)
  overlap <- intersect(r_bases, sas_bases)
  expect_true(length(overlap) >= 5,
    info = "R and SAS summary table examples should have matching file names")
})

# ---------------------------------------------------------------------------
# SAS-specific syntax patterns
# ---------------------------------------------------------------------------
context("SAS Scripts: Syntax Patterns")

test_that("SAS scripts have proper DATA step syntax", {
  scripts_with_data <- 0
  for (script in sas_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    if (grepl("\\bDATA\\s+\\w+\\s*;", content, ignore.case = TRUE)) {
      scripts_with_data <- scripts_with_data + 1
      # DATA steps should have SET or INPUT
      has_set_or_input <- grepl("\\b(SET|INPUT|MERGE)\\b", content, ignore.case = TRUE)
      expect_true(has_set_or_input,
        info = paste("DATA step should have SET/INPUT/MERGE:", basename(script)))
    }
  }
  expect_true(scripts_with_data >= 1,
    info = "At least one SAS script should have DATA steps")
})

test_that("SAS scripts have descriptive comments or titles", {
  for (script in sas_scripts) {
    content <- readLines(script, warn = FALSE, n = 20)
    has_comment <- any(grepl("(/\\*|\\*|TITLE)", content, ignore.case = TRUE))
    expect_true(has_comment,
      info = paste("SAS script should have comments or TITLE:", basename(script)))
  }
})

test_that("SAS scripts reference MEPS data files (h-files)", {
  ws_scripts <- sas_scripts[grepl("workshop_exercises", sas_scripts)]
  scripts_with_hfile <- 0
  for (script in ws_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    if (grepl("[Hh]\\d{2,3}", content)) {
      scripts_with_hfile <- scripts_with_hfile + 1
    }
  }
  expect_true(scripts_with_hfile >= length(ws_scripts) * 0.3,
    info = "At least 30% of SAS workshop scripts should reference MEPS h-files")
})
