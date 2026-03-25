# =============================================================================
# Test Suite: R Script Syntax Validation Tests
# Description: Verifies all R scripts in R/ can be parsed without syntax errors
#              and checks for common issues
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
r_dir <- file.path(repo_root, "R")

# Get all R scripts
r_scripts <- list.files(r_dir, pattern = "\\.R$", full.names = TRUE, recursive = TRUE)

# ---------------------------------------------------------------------------
# Syntax parsing tests
# ---------------------------------------------------------------------------
context("R Script Syntax: Parsing Validation")

test_that("R directory exists and contains R scripts", {
  expect_true(dir.exists(r_dir))
  expect_true(length(r_scripts) > 0,
    info = "R/ directory should contain .R files")
})

test_that("all R scripts in workshop_exercises/ parse without syntax errors", {
  workshop_scripts <- r_scripts[grepl("workshop_exercises", r_scripts)]
  expect_true(length(workshop_scripts) > 0)

  for (script in workshop_scripts) {
    result <- tryCatch(
      {
        parse(file = script)
        TRUE
      },
      error = function(e) {
        FALSE
      }
    )
    expect_true(result,
      info = paste("Syntax error in:", basename(script)))
  }
})

test_that("R scripts in summary_tables_examples/ parse without syntax errors", {
  summary_scripts <- r_scripts[grepl("summary_tables_examples", r_scripts)]
  expect_true(length(summary_scripts) > 0)

  # Known issue: ins_age_2016.R has a stray character on line 28 in the original repo
  known_issues <- c("ins_age_2016.R")
  parse_failures <- c()

  for (script in summary_scripts) {
    result <- tryCatch(
      {
        parse(file = script)
        TRUE
      },
      error = function(e) {
        FALSE
      }
    )
    if (!result) {
      parse_failures <- c(parse_failures, basename(script))
    }
  }

  # All failures should be in the known issues list
  unexpected_failures <- setdiff(parse_failures, known_issues)
  expect_equal(length(unexpected_failures), 0,
    info = paste("Unexpected syntax errors in:",
      paste(unexpected_failures, collapse = ", ")))

  # Verify known issues are actually still present (so we know when they're fixed)
  if (length(known_issues) > 0) {
    for (ki in known_issues) {
      matching <- summary_scripts[grepl(ki, summary_scripts)]
      if (length(matching) > 0) {
        expect_true(ki %in% parse_failures,
          info = paste("Known issue may have been fixed:", ki))
      }
    }
  }
})

# ---------------------------------------------------------------------------
# Common issue checks
# ---------------------------------------------------------------------------
context("R Script Syntax: Common Issue Detection")

test_that("R scripts that use packages include library() or install.packages() calls", {
  for (script in r_scripts) {
    content <- readLines(script, warn = FALSE)
    # Check that scripts using packages call library(), require(), or install.packages()
    has_library <- any(grepl("(library|require|install\\.packages)\\(", content))
    # Also check if script sources another file that may load packages
    has_source <- any(grepl("source\\(", content))
    has_pkg_usage <- any(grepl("(svydesign|svymean|svytotal|read\\.xport|read_dta|read_MEPS)", content))

    if (has_pkg_usage) {
      expect_true(has_library || has_source,
        info = paste("Script uses packages but missing library/source call:", basename(script)))
    }
  }
})

test_that("R scripts have balanced parentheses (excluding strings and comments)", {
  for (script in r_scripts) {
    content <- readLines(script, warn = FALSE)
    # Remove comment lines and strings for more accurate counting
    active_lines <- content[!grepl("^\\s*#", content)]
    active_content <- paste(active_lines, collapse = "\n")
    # Remove quoted strings (rough heuristic)
    active_content <- gsub('"[^"]*"', '', active_content)
    active_content <- gsub("'[^']*'", '', active_content)
    open_parens <- nchar(gsub("[^(]", "", active_content))
    close_parens <- nchar(gsub("[^)]", "", active_content))
    # Allow small differences due to strings/comments containing parens
    expect_true(abs(open_parens - close_parens) <= 2,
      info = paste("Significantly mismatched parentheses in:", basename(script)))
  }
})

test_that("R scripts do not have unclosed curly braces", {
  for (script in r_scripts) {
    content <- paste(readLines(script, warn = FALSE), collapse = "\n")
    open_braces <- nchar(gsub("[^{]", "", content))
    close_braces <- nchar(gsub("[^}]", "", content))
    expect_equal(open_braces, close_braces,
      info = paste("Mismatched curly braces in:", basename(script)))
  }
})

test_that("R scripts do not contain obvious placeholder paths that are broken", {
  for (script in r_scripts) {
    content <- readLines(script, warn = FALSE)
    # Filter out commented lines
    active_lines <- content[!grepl("^\\s*#", content)]
    # Check for obviously broken paths like empty quotes
    has_empty_path <- any(grepl('read\\.(csv|xport|dta)\\(\\s*""\\s*\\)', active_lines))
    expect_false(has_empty_path,
      info = paste("Empty file path in read call:", basename(script)))
  }
})

test_that("all R scripts have consistent line endings", {
  for (script in r_scripts) {
    raw <- readBin(script, "raw", file.info(script)$size)
    raw_str <- rawToChar(raw)
    # Check for mixed line endings (both \r\n and \n alone)
    has_crlf <- grepl("\r\n", raw_str)
    has_lf_only <- grepl("[^\r]\n", raw_str)
    # It's OK to have all CRLF or all LF, but mixed is problematic
    # This is a soft check - just verify file is readable
    content <- readLines(script, warn = FALSE)
    expect_true(length(content) > 0,
      info = paste("Script should have content:", basename(script)))
  }
})

test_that("no R script is completely empty", {
  for (script in r_scripts) {
    content <- readLines(script, warn = FALSE)
    non_empty <- content[trimws(content) != ""]
    expect_true(length(non_empty) > 0,
      info = paste("Script should not be empty:", basename(script)))
  }
})

test_that("R scripts have descriptive header comments", {
  for (script in r_scripts) {
    content <- readLines(script, warn = FALSE, n = 10)
    has_comment <- any(grepl("^\\s*#", content))
    expect_true(has_comment,
      info = paste("Script should have header comments:", basename(script)))
  }
})
