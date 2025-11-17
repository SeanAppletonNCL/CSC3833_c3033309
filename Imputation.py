import pandas as pd
import numpy as np

df = pd.read_csv("country_economics_data.csv")

# Clean column names to snake_case
df.columns = (
    df.columns
      .str.strip()
      .str.lower()
      .str.replace(r'[^a-z0-9]+', '_', regex=True)
)

print(df.columns.tolist())

num_cols = [
    "gdp",
    "gdp_growth",
    "interest_rate",
    "inflation_rate",
    "jobless_rate",
    "gov_budget",
    "debt_gdp",
    "current_account",
    "population",
    "area"
]


import pandas as pd
import numpy as np

df = pd.read_csv("country_economics_data.csv")

# 1) Normalise column names
df.columns = (
    df.columns
      .str.strip()
      .str.lower()
      .str.replace(r'[^a-z0-9]+', '_', regex=True)
)

# 2) Numeric columns
num_cols = [
    "gdp",
    "gdp_growth",
    "interest_rate",
    "inflation_rate",
    "jobless_rate",
    "gov_budget",
    "debt_gdp",
    "current_account",
    "population",
    "area",
]

# 3) Convert to numeric (anything non-numeric -> NaN)
for c in num_cols:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

# 4) Region column – fill missing with "Unknown"
if "region" in df.columns:
    df["region"] = df["region"].fillna("Unknown")
else:
    df["region"] = "Unknown"

# 5) Region-median imputation
for c in num_cols:
    if c in df.columns:
        df[c] = df.groupby("region")[c].transform(
            lambda s: s.fillna(s.median())
        )
        # Fallback to global median in case an entire region is missing that var
        df[c] = df[c].fillna(df[c].median())

# 6) Create GDP per capita for the map (GDP is in USD billions)
df["gdp_per_capita"] = (df["gdp"] * 1e9) / df["population"]

# 7) Save cleaned file
df.to_csv("imputed_country_economics_data.csv", index=False)

print("Done. Shape:", df.shape)
print(df.isna().sum())
