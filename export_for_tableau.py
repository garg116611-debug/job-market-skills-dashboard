"""
Phase 5 prep -- Export flat, Tableau-friendly CSVs from Neon.
Tableau Public can't connect live to a database, so we export the joined,
analysis-ready data as CSV files instead.

Produces:
  data/processed/postings_master.csv     -- one row per posting (wide)
  data/processed/posting_skills_long.csv -- one row per (posting, skill) (long)

Usage: python export_for_tableau.py
"""
import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

print("Connecting to Neon...")
conn = psycopg2.connect(DATABASE_URL)

# ---------- 1. postings_master (wide, one row per posting) ----------
print("Exporting postings_master...")
master_query = """
    SELECT
        p.job_id,
        p.title,
        c.name AS company_name,
        p.location,
        p.role_category,
        p.seniority_level,
        p.salary_min,
        p.salary_max,
        (p.salary_min + p.salary_max) / 2.0 AS avg_salary,
        p.posted_date,
        p.job_url,
        COUNT(ps.skill_id) AS skill_count,
        BOOL_OR(s.name IN ('AWS', 'Azure', 'GCP')) AS has_cloud_skill
    FROM postings p
    LEFT JOIN companies c ON c.id = p.company_id
    LEFT JOIN posting_skills ps ON ps.posting_id = p.id
    LEFT JOIN skills s ON s.id = ps.skill_id
    GROUP BY p.id, c.name
"""
master = pd.read_sql(master_query, conn)

# Split "City, ST" location into two columns for map/geography charts in Tableau
loc_split = master["location"].str.split(",", n=1, expand=True)
master["city"] = loc_split[0].str.strip()
master["state"] = loc_split[1].str.strip() if loc_split.shape[1] > 1 else None

# Flag salary outliers with the same IQR rule used in analyze.py, so Tableau
# salary charts can filter them out while other charts (skills, counts) keep
# using every posting.
valid_salary = master["avg_salary"].dropna()
q1, q3 = valid_salary.quantile(0.25), valid_salary.quantile(0.75)
iqr = q3 - q1
lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr


def flag_outlier(x):
    if pd.isna(x):
        return None  # no salary disclosed -- outlier flag not applicable
    return not (lower <= x <= upper)


master["is_salary_outlier"] = master["avg_salary"].apply(flag_outlier)

master.to_csv("data/processed/postings_master.csv", index=False)
print(f"Saved postings_master.csv -- {len(master)} rows")

# ---------- 2. posting_skills_long (long, one row per posting+skill) ----------
print("Exporting posting_skills_long...")
long_query = """
    SELECT
        p.job_id,
        p.role_category,
        s.name AS skill_name,
        s.category AS skill_category
    FROM posting_skills ps
    JOIN postings p ON p.id = ps.posting_id
    JOIN skills s ON s.id = ps.skill_id
"""
long_df = pd.read_sql(long_query, conn)
long_df.to_csv("data/processed/posting_skills_long.csv", index=False)
print(f"Saved posting_skills_long.csv -- {len(long_df)} rows")

conn.close()
print("\nDone. Both CSVs are in data/processed/, ready to import into Tableau.")