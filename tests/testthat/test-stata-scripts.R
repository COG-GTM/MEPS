# =============================================================================
# Test Suite: Stata Script Validation Tests
# Description: Reads Stata .do files as text and validates expected svy commands,
#              variable naming consistency, and file patterns
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
    if (nchar(path) > 0 && file.exists(file.path(path, "Stata"))) {
      return(normalizePath(path))
    }
  }
  stop("Could not find repo root. Set MEPS_REPO_ROOT environment variable.")
}

repo_root <- get_repo_root()
stata_dir <- file.path(repo_root, "Stata")
stata_scripts <- list.files(stata_dir, pattern = "\\.do$", full.names = TRUE, recursive = TRUE)

# ---------------------------------------------------------------------------
# Stata script existence and readability
# ---------------------------------------------------------------------------
context("Stata Scripts: Existence and Readability")

test_that("Stata directory exists and contains .do files", {
  expect_true(dir.exists(stata_dir))
  expect_true(length(stata_scripts) > 0,
    info = "Stata/ directory should contain .do files")
})

test_that("all Stata scripts are readable as text", {
  for (script in stata_scripts) {
    content <- tryCatch(
      readLines(script, warn = FALSE),
      error = function(e) NULL
    )
    expect_false(is.null(content),
      info = paste("Stata script should be readable:", basename(script)))
  }
})

test_that("no Stata script is completely empty", {
  for (script in stata_scripts) {
    content <- readLines(script, warn = FALSE)
    non_empty <- content[trimws(content) != ""]
    expect_true(length(non_empty) > 0,
      info = paste("Stata script should not be empty:", basename(script)))
  }
})

# ---------------------------------------------------------------------------
# svy command validation
# ---------------------------------------------------------------------------
context("Stata Scripts: Survey Command Validation")

test_that("Stata workshop scripts use svyset for survey design", {
  ws_scripts <- stata_scripts[grepl("workshop_exercises", stata_scripts)]
  scripts_with_svyset <- 0
  for (script in ws_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    if (grepl("svyset", content, ignore.case = TRUE)) {
      scripts_with_svyset <- scripts_with_svyset + 1
    }
  }
  expect_true(scripts_with_svyset >= 1,
    info = "At least one Stata workshop script should use svyset")
})

test_that("Stata scripts use svy: prefix for survey-weighted estimation", {
  svy_commands <- c("svy:\\s*mean", "svy:\\s*total", "svy:\\s*tab",
                    "svy:\\s*regress", "svy:\\s*logistic", "svy,")
  ws_scripts <- stata_scripts[grepl("workshop_exercises", stata_scripts)]
  scripts_with_svy <- 0
  for (script in ws_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    has_svy <- any(sapply(svy_commands, function(cmd) grepl(cmd, content, ignore.case = TRUE)))
    if (has_svy) scripts_with_svy <- scripts_with_svy + 1
  }
  expect_true(scripts_with_svy >= 1,
    info = "At least one Stata workshop script should use svy: commands")
})

test_that("most svyset commands include pweight specification", {
  scripts_with_svyset <- 0
  scripts_with_pweight <- 0
  for (script in stata_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    if (grepl("svyset", content, ignore.case = TRUE)) {
      scripts_with_svyset <- scripts_with_svyset + 1
      if (grepl("pweight", content, ignore.case = TRUE)) {
        scripts_with_pweight <- scripts_with_pweight + 1
      }
    }
  }
  # At least 60% of scripts with svyset should specify pweight
  if (scripts_with_svyset > 0) {
    expect_true(scripts_with_pweight / scripts_with_svyset >= 0.6,
      info = "Most Stata scripts with svyset should specify pweight")
  }
})

test_that("most svyset commands include strata specification", {
  scripts_with_svyset <- 0
  scripts_with_strata <- 0
  for (script in stata_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    if (grepl("svyset", content, ignore.case = TRUE)) {
      scripts_with_svyset <- scripts_with_svyset + 1
      if (grepl("strata", content, ignore.case = TRUE)) {
        scripts_with_strata <- scripts_with_strata + 1
      }
    }
  }
  # At least 60% of scripts with svyset should specify strata
  if (scripts_with_svyset > 0) {
    expect_true(scripts_with_strata / scripts_with_svyset >= 0.6,
      info = "Most Stata scripts with svyset should specify strata")
  }
})

test_that("svyset commands include psu specification", {
  for (script in stata_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    if (grepl("svyset", content, ignore.case = TRUE)) {
      has_psu <- grepl("psu", content, ignore.case = TRUE)
      expect_true(has_psu,
        info = paste("svyset should specify psu:", basename(script)))
    }
  }
})

# ---------------------------------------------------------------------------
# Variable naming consistency
# ---------------------------------------------------------------------------
context("Stata Scripts: Variable Naming Consistency")

test_that("Stata workshop scripts reference MEPS survey design variables", {
  ws_scripts <- stata_scripts[grepl("workshop_exercises", stata_scripts)]
  scripts_with_vars <- 0
  for (script in ws_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    has_varstr <- grepl("varstr", content, ignore.case = TRUE)
    has_varpsu <- grepl("varpsu", content, ignore.case = TRUE)
    if (has_varstr && has_varpsu) scripts_with_vars <- scripts_with_vars + 1
  }
  expect_true(scripts_with_vars >= length(ws_scripts) * 0.3,
    info = "At least 30% of Stata workshop scripts should reference varstr and varpsu")
})

test_that("Stata scripts use PERWT weight variables", {
  ws_scripts <- stata_scripts[grepl("workshop_exercises", stata_scripts)]
  scripts_with_weight <- 0
  for (script in ws_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    if (grepl("perwt\\d+f", content, ignore.case = TRUE)) {
      scripts_with_weight <- scripts_with_weight + 1
    }
  }
  expect_true(scripts_with_weight >= 1,
    info = "At least one Stata workshop script should use perwt weight variables")
})

test_that("Stata scripts reference expenditure variables (TOTEXP)", {
  ws_scripts <- stata_scripts[grepl("workshop_exercises", stata_scripts)]
  scripts_with_totexp <- 0
  for (script in ws_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    if (grepl("totexp", content, ignore.case = TRUE)) {
      scripts_with_totexp <- scripts_with_totexp + 1
    }
  }
  expect_true(scripts_with_totexp >= 1,
    info = "At least one Stata workshop script should reference TOTEXP")
})

# ---------------------------------------------------------------------------
# File naming conventions
# ---------------------------------------------------------------------------
context("Stata Scripts: File Naming Conventions")

test_that("Stata workshop exercise files follow naming convention", {
  ws_dir <- file.path(stata_dir, "workshop_exercises")
  if (dir.exists(ws_dir)) {
    do_files <- list.files(ws_dir, pattern = "\\.do$")
    for (f in do_files) {
      bname <- basename(f)
      # Should be ExerciseXX.do or cond_*.do or descriptive name
      is_valid <- grepl("^(Exercise|exercise|cond_)", bname) ||
                  grepl("^[a-zA-Z]", bname)
      expect_true(is_valid,
        info = paste("Stata workshop file naming:", f))
    }
  }
})

test_that("Stata summary table files match R summary table file names", {
  r_st_files <- list.files(file.path(repo_root, "R", "summary_tables_examples"),
    pattern = "\\.R$")
  stata_st_files <- list.files(file.path(stata_dir, "summary_tables_examples"),
    pattern = "\\.do$")
  r_bases <- gsub("\\.R$", "", r_st_files)
  stata_bases <- gsub("\\.do$", "", stata_st_files)
  overlap <- intersect(r_bases, stata_bases)
  expect_true(length(overlap) >= 5,
    info = "R and Stata summary table examples should have matching file names")
})

# ---------------------------------------------------------------------------
# Stata-specific patterns
# ---------------------------------------------------------------------------
context("Stata Scripts: Syntax Patterns")

test_that("Stata scripts have descriptive header comments", {
  for (script in stata_scripts) {
    content <- readLines(script, warn = FALSE, n = 15)
    has_comment <- any(grepl("(^\\*|^/\\*|^//)", content))
    expect_true(has_comment,
      info = paste("Stata script should have header comments:", basename(script)))
  }
})

test_that("Stata scripts reference MEPS data files", {
  ws_scripts <- stata_scripts[grepl("workshop_exercises", stata_scripts)]
  scripts_with_hfile <- 0
  for (script in ws_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    if (grepl("[Hh]\\d{2,3}", content)) {
      scripts_with_hfile <- scripts_with_hfile + 1
    }
  }
  expect_true(scripts_with_hfile >= length(ws_scripts) * 0.3,
    info = "At least 30% of Stata workshop scripts should reference MEPS h-files")
})

test_that("Stata scripts use import or use commands for data loading", {
  ws_scripts <- stata_scripts[grepl("workshop_exercises", stata_scripts)]
  scripts_with_load <- 0
  for (script in ws_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    has_load <- grepl("\\b(import|use)\\b", content, ignore.case = TRUE)
    if (has_load) scripts_with_load <- scripts_with_load + 1
  }
  expect_true(scripts_with_load >= length(ws_scripts) * 0.5,
    info = "At least half of Stata workshop scripts should load data with import/use")
})

test_that("Stata workshop scripts are substantial (not just stubs)", {
  ws_scripts <- stata_scripts[grepl("workshop_exercises", stata_scripts)]
  for (script in ws_scripts) {
    content <- readLines(script, warn = FALSE)
    non_empty <- content[trimws(content) != "" & !grepl("^\\s*(\\*|//|/\\*)", content)]
    expect_true(length(non_empty) >= 5,
      info = paste("Stata workshop script should have substantial code:", basename(script)))
  }
})

# ---------------------------------------------------------------------------
# Cross-language consistency for Stata
# ---------------------------------------------------------------------------
context("Stata Scripts: Cross-Language Consistency")

test_that("Stata has similar number of workshop exercises as R", {
  r_ws <- list.files(file.path(repo_root, "R", "workshop_exercises"), pattern = "\\.R$")
  stata_ws <- list.files(file.path(stata_dir, "workshop_exercises"), pattern = "\\.do$")
  # Stata should have at least half as many workshop exercises as R
  expect_true(length(stata_ws) >= length(r_ws) * 0.5,
    info = "Stata should have a comparable number of workshop exercises to R")
})

test_that("Stata summary tables cover similar topics as R", {
  r_topics <- gsub("\\.R$", "", list.files(
    file.path(repo_root, "R", "summary_tables_examples"), pattern = "\\.R$"))
  stata_topics <- gsub("\\.do$", "", list.files(
    file.path(stata_dir, "summary_tables_examples"), pattern = "\\.do$"))
  # Check for common topic patterns
  common_patterns <- c("use_expenditures", "care_access", "ins_age")
  for (pattern in common_patterns) {
    r_has <- any(grepl(pattern, r_topics))
    stata_has <- any(grepl(pattern, stata_topics))
    if (r_has) {
      expect_true(stata_has,
        info = paste("Stata should cover same topic as R:", pattern))
    }
  }
})
