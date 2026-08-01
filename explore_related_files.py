"""
Quick peek at the smaller, related CSVs so we know how to join them to postings.csv.
Usage: python explore_related_files.py
"""
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 150)

files_to_check = {
    "companies": "data/raw/companies/companies.csv",
    "skills (mapping)": "data/raw/mappings/skills.csv",
    "job_skills": "data/raw/jobs/job_skills.csv",
    "salaries": "data/raw/jobs/salaries.csv",
}

for label, path in files_to_check.items():
    print("=" * 60)
    print(f"{label}  ({path})")
    print("=" * 60)
    df = pd.read_csv(path)
    print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
    print(f"Columns: {list(df.columns)}")
    print("Sample rows:")
    print(df.head(3))
    print()
