"""
First look at the raw Kaggle data.
Usage: python explore_data.py
"""
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 150)

print("Loading postings.csv ... (this may take a moment, it's a big file)\n")
df = pd.read_csv("data/raw/postings.csv")

print("=" * 60)
print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
print("=" * 60)

print("\nColumn names:")
print(list(df.columns))

print("\nFirst 3 rows:")
print(df.head(3))

print("\nData types:")
print(df.dtypes)

print("\nMissing values per column (top 15):")
print(df.isnull().sum().sort_values(ascending=False).head(15))
