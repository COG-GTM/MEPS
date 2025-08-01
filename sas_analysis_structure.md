# SAS Script Structure Analysis: Exercise1c.sas

## Overview
This SAS script analyzes national healthcare expenses for the civilian noninstitutionalized population in 2018 using MEPS data. It generates survey-weighted estimates accounting for the complex survey design.

## Input Data
- **Source**: 2018 Full-year consolidated file (HC-209) - h209.sas7bdat
- **Key Variables**:
  - `TOTEXP18`: Total health care expenses in 2018
  - `AGELAST`: Person's age last time eligible
  - `VARSTR`: Variance estimation stratum (stratification variable)
  - `VARPSU`: Variance estimation PSU (clustering variable)  
  - `PERWT18F`: Final person weight for 2018 (survey weight)
  - `panel`: Panel number

## SAS Code Structure Analysis

### 1. PROC FORMAT (Lines 38-46)
**Purpose**: Create user-defined formats for categorical variables
- `AGECAT`: Maps ages to categories (0-64, 65+)
- `totexp18_cate`: Maps expenses to categories (0='No Expense', Other='Any Expense')

**Python Equivalent**: Use pandas categorical data or custom mapping functions

### 2. DATA Step (Lines 56-63)
**Purpose**: Load and transform data
- Loads specific variables from H209V9 dataset
- Creates `WITH_AN_EXPENSE` variable (copy of TOTEXP18)
- Creates `CHAR_WITH_AN_EXPENSE` character variable using format lookup

**Python Equivalent**: 
```python
# Load data with specific columns
df = pd.read_sas('h209.sas7bdat', usecols=['TOTEXP18', 'AGELAST', 'VARSTR', 'VARPSU', 'PERWT18F', 'panel'])
# Create derived variables
df['WITH_AN_EXPENSE'] = df['TOTEXP18']
df['CHAR_WITH_AN_EXPENSE'] = df['TOTEXP18'].apply(lambda x: 'No Expense' if x == 0 else 'Any Expense')
```

### 3. PROC SURVEYMEANS - Method 1 (Lines 85-92)
**Purpose**: Calculate percentage of persons with expenses using numeric variable
- Uses survey design: STRATUM VARSTR, CLUSTER VARPSU, WEIGHT PERWT18F
- Analyzes `WITH_AN_EXPENSE` variable with CLASS statement
- Outputs: NOBS, MEAN, STDERR, SUM

**Python Equivalent**: Use survey package or manual survey-weighted calculations

### 4. PROC SURVEYMEANS - Method 2 (Lines 95-100)
**Purpose**: Same analysis using character variable
- Same survey design specifications
- Analyzes `CHAR_WITH_AN_EXPENSE` variable without CLASS statement

### 5. PROC SURVEYFREQ (Lines 103-108)
**Purpose**: Frequency analysis of expense categories
- Same survey design specifications
- Creates frequency table for `CHAR_WITH_AN_EXPENSE`

**Python Equivalent**: Survey-weighted crosstabulation

### 6. PROC SURVEYMEANS - Domain Analysis (Lines 112-119)
**Purpose**: Calculate mean and median expenses by domain
- Analyzes `totexp18` variable
- Uses DOMAIN statement for:
  - Overall persons with any expense
  - Persons with any expense by age group (0-64, 65+)
- Outputs: NOBS, MEAN, STDERR, SUM, MEDIAN

**Python Equivalent**: Survey-weighted statistics with domain/subgroup analysis

## Survey Design Elements
- **Stratification**: VARSTR (117 strata)
- **Clustering**: VARPSU (257 clusters) 
- **Weights**: PERWT18F (person-level weights)
- **Sample Size**: 30,461 observations, 29,415 used (1,046 with nonpositive weights)
- **Population**: 326,327,888 (sum of weights)

## Expected Outputs
1. **Method 1**: Percentage with expenses by category (13.33% No Expense, 86.67% Any Expense)
2. **Method 2**: Same percentages using character variable
3. **Method 3**: Frequency table with same percentages
4. **Domain Analysis**: 
   - Overall mean expense: $6,063, median: $1,316
   - Among those with expenses: mean $6,996, median $1,849
   - By age group (with expenses):
     - 0-64: mean $5,650, median $1,401
     - 65+: mean $12,866, median $5,877

## Dependencies
- SAS7BDAT file reader for Python (pandas.read_sas or sas7bdat package)
- Survey statistics package (need to implement survey-weighted calculations)
- Statistical functions for mean, median, standard errors with complex survey design
