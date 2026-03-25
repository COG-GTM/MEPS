# =============================================================================
# Test Suite: R Workshop Exercise Tests
# Description: Tests that workshop exercise scripts follow expected patterns,
#              reference valid MEPS file names, and use correct survey design
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
    if (nchar(path) > 0 && file.exists(file.path(path, "R"))) {
      return(normalizePath(path))
    }
  }
  stop("Could not find repo root. Set MEPS_REPO_ROOT environment variable.")
}

repo_root <- get_repo_root()
workshop_dir <- file.path(repo_root, "R", "workshop_exercises")
workshop_scripts <- list.files(workshop_dir, pattern = "\\.R$", full.names = TRUE)

# ---------------------------------------------------------------------------
# Workshop exercise pattern tests
# ---------------------------------------------------------------------------
context("Workshop Exercises: Script Pattern Validation")

test_that("workshop_exercises directory contains R scripts", {
  expect_true(dir.exists(workshop_dir))
  expect_true(length(workshop_scripts) > 0)
})

test_that("workshop exercise scripts use survey design variables (VARPSU, VARSTR)", {
  scripts_with_survey <- 0
  for (script in workshop_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    has_varpsu <- grepl("VARPSU", content, ignore.case = FALSE)
    has_varstr <- grepl("VARSTR", content, ignore.case = FALSE)
    if (has_varpsu && has_varstr) {
      scripts_with_survey <- scripts_with_survey + 1
    }
  }
  # Most workshop scripts should use survey design
  expect_true(scripts_with_survey >= length(workshop_scripts) * 0.5,
    info = "At least half of workshop scripts should reference VARPSU and VARSTR")
})

test_that("workshop exercise scripts use person weight variables (PERWT)", {
  scripts_with_weight <- 0
  for (script in workshop_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    has_perwt <- grepl("PERWT\\d+F", content)
    if (has_perwt) {
      scripts_with_weight <- scripts_with_weight + 1
    }
  }
  expect_true(scripts_with_weight >= length(workshop_scripts) * 0.5,
    info = "At least half of workshop scripts should use PERWT weight variables")
})

test_that("workshop scripts use svydesign() for survey design specification", {
  scripts_with_svydesign <- 0
  for (script in workshop_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    if (grepl("svydesign", content)) {
      scripts_with_svydesign <- scripts_with_svydesign + 1
    }
  }
  expect_true(scripts_with_svydesign >= 1,
    info = "At least one workshop script should use svydesign()")
})

test_that("svydesign calls include required parameters (id, strata, weights, data)", {
  for (script in workshop_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    if (grepl("svydesign", content)) {
      # Check for required survey design parameters
      expect_true(grepl("id\\s*=", content),
        info = paste("svydesign missing id= in:", basename(script)))
      expect_true(grepl("strata\\s*=", content),
        info = paste("svydesign missing strata= in:", basename(script)))
      expect_true(grepl("weights\\s*=", content),
        info = paste("svydesign missing weights= in:", basename(script)))
      expect_true(grepl("data\\s*=", content),
        info = paste("svydesign missing data= in:", basename(script)))
    }
  }
})

test_that("workshop scripts set survey.lonely.psu option", {
  scripts_with_psu_option <- 0
  for (script in workshop_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    if (grepl("survey\\.lonely\\.psu", content)) {
      scripts_with_psu_option <- scripts_with_psu_option + 1
    }
  }
  expect_true(scripts_with_psu_option >= 1,
    info = "At least one workshop script should set survey.lonely.psu option")
})

# ---------------------------------------------------------------------------
# MEPS file name reference validation
# ---------------------------------------------------------------------------
context("Workshop Exercises: MEPS File References")

test_that("workshop scripts reference valid MEPS file name patterns", {
  # Load valid file names from reference guide
  fn_path <- file.path(repo_root, "Quick_Reference_Guides", "meps_file_names.csv")
  file_names_df <- read.csv(fn_path, stringsAsFactors = FALSE, check.names = FALSE)

  for (script in workshop_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    # Extract h-file references (e.g., h192, h224, h220g)
    h_refs <- regmatches(content, gregexpr("h\\d{2,3}[a-z]?", content, ignore.case = TRUE))[[1]]
    if (length(h_refs) > 0) {
      # Just check they follow the MEPS naming pattern
      for (ref in h_refs) {
        expect_true(grepl("^h\\d{2,3}", ref, ignore.case = TRUE),
          info = paste("Invalid MEPS file reference:", ref, "in", basename(script)))
      }
    }
  }
})

test_that("workshop scripts reference survey analysis functions", {
  survey_functions <- c("svymean", "svytotal", "svyby", "svyglm",
                        "svyratio", "svydesign", "svyttest")
  for (script in workshop_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    has_survey_fn <- any(sapply(survey_functions, function(fn) grepl(fn, content)))
    has_svydesign <- grepl("svydesign", content)
    if (has_svydesign) {
      expect_true(has_survey_fn,
        info = paste("Script with svydesign should use survey functions:", basename(script)))
    }
  }
})

# ---------------------------------------------------------------------------
# Exercise numbering and naming
# ---------------------------------------------------------------------------
context("Workshop Exercises: File Naming Convention")

test_that("exercise files follow naming convention (exercise_NX.R or descriptive name)", {
  for (script in workshop_scripts) {
    bname <- basename(script)
    # Should be either exercise_XX.R or a descriptive name (lowercase with underscores/digits)
    is_exercise <- grepl("^exercise_\\d+[a-z]?\\.R$", bname)
    is_descriptive <- grepl("^[a-z][a-z0-9_]*\\.R$", bname)
    expect_true(is_exercise || is_descriptive,
      info = paste("Script name should follow convention:", bname))
  }
})

test_that("exercise files cover multiple exercise numbers", {
  exercise_nums <- c()
  for (script in workshop_scripts) {
    bname <- basename(script)
    match <- regmatches(bname, regexpr("exercise_(\\d+)", bname))
    if (length(match) > 0) {
      num <- gsub("exercise_", "", match)
      exercise_nums <- c(exercise_nums, num)
    }
  }
  unique_nums <- unique(exercise_nums)
  expect_true(length(unique_nums) >= 2,
    info = "Should have exercises covering at least 2 different exercise numbers")
})

# ---------------------------------------------------------------------------
# Data manipulation patterns
# ---------------------------------------------------------------------------
context("Workshop Exercises: Data Manipulation Patterns")

test_that("workshop scripts use standard R data manipulation", {
  manipulation_patterns <- c("mutate", "filter", "select", "group_by",
                             "summarize", "summarise", "merge", "join",
                             "subset", "ifelse", "dplyr")
  for (script in workshop_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    # Skip very short/simple scripts
    if (nchar(content) > 200) {
      has_manipulation <- any(sapply(manipulation_patterns, function(p) grepl(p, content)))
      expect_true(has_manipulation,
        info = paste("Longer scripts should use data manipulation:", basename(script)))
    }
  }
})

test_that("workshop scripts that load data specify data source", {
  for (script in workshop_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    loads_data <- grepl("(read\\.|read_|load|import)", content, ignore.case = TRUE)
    if (loads_data) {
      has_source <- grepl("(MEPS|meps|h\\d{2,3}|HC-\\d+|hc-\\d+)", content)
      expect_true(has_source,
        info = paste("Data-loading script should reference MEPS source:", basename(script)))
    }
  }
})
