"""
Phase 2.5 -- Validation.
Samples random postings, shows the description + what skills our extractor
found, and asks YOU (quickly) to flag any mistakes. Computes real
precision/recall from your answers -- this is what makes the extraction
trustworthy instead of just assumed.

Usage: python validate_extraction.py
Takes about 15-20 minutes for 25 postings. Answer honestly and fast --
skim, don't overthink each one.
"""
import os
import json
import textwrap
import random
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
SAMPLE_SIZE = 25

with open("etl/skills_taxonomy.json", "r", encoding="utf-8") as f:
    taxonomy = json.load(f)
taxonomy.pop("_comment", None)
ALL_SKILLS = sorted(taxonomy.keys())

print("Connecting to Neon and sampling postings...")
conn = psycopg2.connect(DATABASE_URL)
query = """
    SELECT p.id, p.job_id, p.title, p.description_raw,
           STRING_AGG(s.name, ', ' ORDER BY s.name) AS extracted_skills
    FROM postings p
    LEFT JOIN posting_skills ps ON ps.posting_id = p.id
    LEFT JOIN skills s ON s.id = ps.skill_id
    WHERE p.description_raw IS NOT NULL
    GROUP BY p.id, p.job_id, p.title, p.description_raw
"""
df = pd.read_sql(query, conn)
conn.close()

sample = df.sample(n=min(SAMPLE_SIZE, len(df)), random_state=42).reset_index(drop=True)

print(f"\n{'=' * 70}")
print(f"VALIDATION -- {len(sample)} random postings")
print("For each one: read the description, look at what we extracted.")
print("Type WRONG skill names that shouldn't be there (comma-separated), or press Enter if all correct.")
print("Then type any MISSED skill names you spot in the text (comma-separated), or press Enter if none.")
print(f"{'=' * 70}\n")

total_extracted = 0
total_wrong = 0
total_missed = 0

results_log = []

for i, row in sample.iterrows():
    print(f"\n--- Posting {i + 1}/{len(sample)} (job_id: {row['job_id']}) ---")
    print(f"Title: {row['title']}")
    desc = str(row["description_raw"])[:900]
    print("\nDescription (first ~900 chars):")
    print(textwrap.fill(desc, width=90))

    extracted = row["extracted_skills"] if row["extracted_skills"] else "(none found)"
    print(f"\nWe extracted: {extracted}")
    n_extracted = 0 if not row["extracted_skills"] else len(row["extracted_skills"].split(", "))
    total_extracted += n_extracted

    wrong_input = input("\nWRONG skills (comma-separated, or Enter): ").strip()
    wrong_list = [s.strip() for s in wrong_input.split(",") if s.strip()]
    total_wrong += len(wrong_list)

    missed_input = input("MISSED skills (comma-separated, or Enter): ").strip()
    missed_list = [s.strip() for s in missed_input.split(",") if s.strip()]
    total_missed += len(missed_list)

    results_log.append({
        "job_id": row["job_id"],
        "title": row["title"],
        "extracted": extracted,
        "wrong": ", ".join(wrong_list),
        "missed": ", ".join(missed_list),
    })

# ---------------- Results ----------------
correct = total_extracted - total_wrong
precision = correct / total_extracted if total_extracted else 0
recall = correct / (correct + total_missed) if (correct + total_missed) else 0

print(f"\n{'=' * 70}")
print("VALIDATION RESULTS")
print(f"{'=' * 70}")
print(f"Postings reviewed: {len(sample)}")
print(f"Total skills extracted (in sample): {total_extracted}")
print(f"Flagged as WRONG (false positives): {total_wrong}")
print(f"Flagged as MISSED (false negatives): {total_missed}")
print(f"\nPrecision: {precision:.1%}  (of what we found, how much was correct)")
print(f"Recall:    {recall:.1%}  (of what was actually there, how much we caught)")

pd.DataFrame(results_log).to_csv("data/processed/validation_log.csv", index=False)
print("\nSaved detailed log to data/processed/validation_log.csv")
