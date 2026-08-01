"""
Fixes a bug: salary_min/max in the DB currently mix HOURLY/WEEKLY/MONTHLY/YEARLY
figures together. This script re-derives a clean, USD-only, annualized salary
per posting and UPDATEs the existing rows (no need to reload everything).

Usage: python fix_salary_normalization.py
"""
import os
import math
import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

MULTIPLIER = {
    "HOURLY": 2080,   # 40 hrs/week * 52 weeks
    "WEEKLY": 52,
    "MONTHLY": 12,
    "YEARLY": 1,
    "BIWEEKLY": 26,
}


def clean(val):
    if val is None:
        return None
    if isinstance(val, (float, np.floating)):
        return None if math.isnan(val) else float(val)
    return val


print("Loading source CSVs...")
postings = pd.read_csv("data/processed/postings_filtered.csv", usecols=["job_id"])
salaries = pd.read_csv("data/raw/jobs/salaries.csv")

filtered_ids = set(postings["job_id"])
salaries_f = (
    salaries[salaries["job_id"].isin(filtered_ids)]
    .drop_duplicates(subset="job_id", keep="first")
)

total = len(postings)
dropped_non_usd = (salaries_f["currency"] != "USD").sum()
salaries_f = salaries_f[salaries_f["currency"] == "USD"].copy()

unknown_period = ~salaries_f["pay_period"].isin(MULTIPLIER.keys())
dropped_unknown_period = unknown_period.sum()
salaries_f = salaries_f[~unknown_period].copy()

salaries_f["mult"] = salaries_f["pay_period"].map(MULTIPLIER)
salaries_f["salary_min_annual"] = salaries_f["min_salary"] * salaries_f["mult"]
salaries_f["salary_max_annual"] = salaries_f["max_salary"] * salaries_f["mult"]

print(f"Total filtered postings: {total}")
print(f"Dropped (non-USD currency): {dropped_non_usd}")
print(f"Dropped (unrecognized pay_period): {dropped_unknown_period}")
print(f"Postings with a clean annual USD salary: {len(salaries_f)}")

# Build the full update set: every filtered job_id gets an explicit value,
# NULL if we don't have a clean salary for it (clears out any old mixed-unit value).
salary_map = {
    int(row["job_id"]): (clean(row["salary_min_annual"]), clean(row["salary_max_annual"]))
    for _, row in salaries_f.iterrows()
}

update_rows = [
    (str(job_id), *salary_map.get(job_id, (None, None)))
    for job_id in postings["job_id"]
]

print("Updating Neon...")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
try:
    psycopg2.extras.execute_values(
        cur,
        """
        UPDATE postings AS p
        SET salary_min = v.salary_min, salary_max = v.salary_max
        FROM (VALUES %s) AS v(job_id, salary_min, salary_max)
        WHERE p.job_id = v.job_id
        """,
        update_rows,
        template="(%s, %s, %s)",
    )
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM postings WHERE salary_min IS NOT NULL")
    print(f"\nDone. Postings with a valid annual salary now: {cur.fetchone()[0]}")
except Exception as e:
    conn.rollback()
    print("Failed, rolled back. Error:", e)
    raise
finally:
    cur.close()
    conn.close()
