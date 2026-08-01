"""
Phase 3.2 -- Load cleaned data into Neon Postgres.
Loads: companies, postings (SDE + DA only), skills, posting_skills

Usage: python load_to_db.py
"""
import os
import json
import math
import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL not found -- check your .env file.")


def clean(val):
    """Convert pandas/numpy values to plain Python types psycopg2 can insert,
    turning any NaN/NaT into a real NULL."""
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    if isinstance(val, np.floating):
        return None if math.isnan(val) else float(val)
    if isinstance(val, np.integer):
        return int(val)
    if pd.isna(val):
        return None
    return val


print("Loading CSVs...")
postings = pd.read_csv("data/processed/postings_filtered.csv")
salaries = pd.read_csv("data/raw/jobs/salaries.csv")
skills_extracted = pd.read_csv("data/processed/posting_skills_extracted.csv")

with open("etl/skills_taxonomy.json", "r", encoding="utf-8") as f:
    taxonomy = json.load(f)
taxonomy.pop("_comment", None)
skill_category = {name: info["category"] for name, info in taxonomy.items()}

filtered_ids = set(postings["job_id"])

# One salary row per job (first match), only for our filtered postings
salaries_f = (
    salaries[salaries["job_id"].isin(filtered_ids)]
    .drop_duplicates(subset="job_id", keep="first")
    [["job_id", "min_salary", "max_salary", "pay_period", "currency"]]
)
postings = postings.merge(salaries_f, on="job_id", how="left")

# posted_date from epoch milliseconds
postings["posted_date"] = pd.to_datetime(
    postings["listed_time"], unit="ms", errors="coerce"
).dt.date

# Only keep skill mentions for our filtered postings
skills_extracted = skills_extracted[skills_extracted["job_id"].isin(filtered_ids)]

print(f"Postings to load: {len(postings)}")
print(f"Skill mentions to load: {len(skills_extracted)}")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

try:
    # ---------- companies ----------
    print("Loading companies...")
    company_names = postings["company_name"].dropna().unique().tolist()
    psycopg2.extras.execute_values(
        cur,
        "INSERT INTO companies (name) VALUES %s ON CONFLICT (name) DO NOTHING",
        [(name,) for name in company_names],
    )
    conn.commit()

    cur.execute("SELECT id, name FROM companies")
    company_id_map = {name: id_ for id_, name in cur.fetchall()}

    # ---------- postings ----------
    print("Loading postings...")
    posting_rows = []
    for _, row in postings.iterrows():
        comp_name = clean(row["company_name"])
        company_id = company_id_map.get(comp_name) if comp_name else None
        posting_rows.append((
            int(row["job_id"]),
            clean(row["title"]),
            company_id,
            clean(row["location"]),
            row["role_category"],
            clean(row.get("formatted_experience_level")),
            None,  # min_experience -- needs free-text regex extraction, future step
            None,  # max_experience -- needs free-text regex extraction, future step
            clean(row.get("min_salary")),
            clean(row.get("max_salary")),
            clean(row.get("description")),
            clean(row["posted_date"]),
            "LinkedIn (Kaggle dataset)",
            clean(row.get("job_posting_url")),
        ))

    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO postings
            (job_id, title, company_id, location, role_category, seniority_level,
             min_experience, max_experience, salary_min, salary_max,
             description_raw, posted_date, source_site, job_url)
        VALUES %s
        ON CONFLICT (job_id) DO NOTHING
        """,
        posting_rows,
    )
    conn.commit()

    cur.execute("SELECT id, job_id FROM postings")
    posting_id_map = {int(job_id): id_ for id_, job_id in cur.fetchall()}

    # ---------- skills ----------
    print("Loading skills...")
    skill_names = skills_extracted["skill_name"].unique().tolist()
    psycopg2.extras.execute_values(
        cur,
        "INSERT INTO skills (name, category) VALUES %s ON CONFLICT (name) DO NOTHING",
        [(name, skill_category.get(name)) for name in skill_names],
    )
    conn.commit()

    cur.execute("SELECT id, name FROM skills")
    skill_id_map = {name: id_ for id_, name in cur.fetchall()}

    # ---------- posting_skills ----------
    print("Loading posting_skills links...")
    link_rows = []
    for _, row in skills_extracted.iterrows():
        posting_id = posting_id_map.get(row["job_id"])
        skill_id = skill_id_map.get(row["skill_name"])
        if posting_id and skill_id:
            link_rows.append((posting_id, skill_id))

    psycopg2.extras.execute_values(
        cur,
        "INSERT INTO posting_skills (posting_id, skill_id) VALUES %s ON CONFLICT DO NOTHING",
        link_rows,
    )
    conn.commit()

    print("\nDone. Row counts now in the database:")
    for table in ["companies", "postings", "skills", "posting_skills"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(f" - {table}: {cur.fetchone()[0]}")

except Exception as e:
    conn.rollback()
    print("Something went wrong, rolled back. Error:")
    print(e)
    raise
finally:
    cur.close()
    conn.close()