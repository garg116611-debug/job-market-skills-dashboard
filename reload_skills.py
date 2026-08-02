"""
Re-loads skills + posting_skills from scratch after a taxonomy/extraction fix.
Truncates skills and posting_skills (companies and postings are untouched),
then reloads from data/processed/posting_skills_extracted.csv (filtered to
SDE/DA postings only, same as the original load).

Usage: python reload_skills.py
(Run extract_skills.py again FIRST so the CSV reflects the fix.)
"""
import os
import json
import pandas as pd
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

with open("etl/skills_taxonomy.json", "r", encoding="utf-8") as f:
    taxonomy = json.load(f)
taxonomy.pop("_comment", None)
skill_category = {name: info["category"] for name, info in taxonomy.items()}

print("Loading CSVs...")
postings = pd.read_csv("data/processed/postings_filtered.csv", usecols=["job_id"])
skills_extracted = pd.read_csv("data/processed/posting_skills_extracted.csv")

filtered_ids = set(postings["job_id"])
skills_extracted = skills_extracted[skills_extracted["job_id"].isin(filtered_ids)]
print(f"Skill mentions to reload: {len(skills_extracted)}")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
try:
    print("Clearing old posting_skills and skills...")
    cur.execute("TRUNCATE TABLE posting_skills, skills")
    conn.commit()

    print("Reloading skills...")
    skill_names = skills_extracted["skill_name"].unique().tolist()
    psycopg2.extras.execute_values(
        cur,
        "INSERT INTO skills (name, category) VALUES %s",
        [(name, skill_category.get(name)) for name in skill_names],
    )
    conn.commit()

    cur.execute("SELECT id, name FROM skills")
    skill_id_map = {name: id_ for id_, name in cur.fetchall()}

    cur.execute("SELECT id, job_id FROM postings")
    posting_id_map = {int(job_id): id_ for id_, job_id in cur.fetchall()}

    print("Reloading posting_skills links...")
    link_rows = []
    for _, row in skills_extracted.iterrows():
        posting_id = posting_id_map.get(row["job_id"])
        skill_id = skill_id_map.get(row["skill_name"])
        if posting_id and skill_id:
            link_rows.append((posting_id, skill_id))

    psycopg2.extras.execute_values(
        cur,
        "INSERT INTO posting_skills (posting_id, skill_id) VALUES %s",
        link_rows,
    )
    conn.commit()

    print("\nDone. Row counts now:")
    for table in ["skills", "posting_skills"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(f" - {table}: {cur.fetchone()[0]}")

except Exception as e:
    conn.rollback()
    print("Failed, rolled back. Error:", e)
    raise
finally:
    cur.close()
    conn.close()