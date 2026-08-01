"""
Phase 4 -- Statistical Analysis.
Pulls postings with a clean annual salary from Neon, builds features
(skill_count, seniority_ordinal, has_cloud_skill), then runs:
  4.1 Correlation matrix
  4.2 Linear regression (salary ~ skill_count + seniority + has_cloud_skill)
  4.3 T-test (cloud-skill postings vs non-cloud-skill postings)

Usage: python analyze.py
"""
import os
import pandas as pd
import psycopg2
import statsmodels.api as sm
from scipy import stats
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

CLOUD_SKILLS = ("AWS", "Azure", "GCP")

# Ordinal scale for seniority -- dataset gives text levels, not numeric years,
# so this is our stand-in for "experience" in the regression.
SENIORITY_ORDER = {
    "Internship": 0,
    "Entry level": 1,
    "Associate": 2,
    "Mid-Senior level": 3,
    "Director": 4,
    "Executive": 5,
}

print("Connecting to Neon and pulling data...")
conn = psycopg2.connect(DATABASE_URL)

query = """
    SELECT
        p.id,
        p.role_category,
        p.seniority_level,
        p.salary_min,
        p.salary_max,
        COUNT(ps.skill_id) AS skill_count,
        BOOL_OR(s.name IN %(cloud)s) AS has_cloud_skill
    FROM postings p
    LEFT JOIN posting_skills ps ON ps.posting_id = p.id
    LEFT JOIN skills s ON s.id = ps.skill_id
    WHERE p.salary_min IS NOT NULL AND p.salary_max IS NOT NULL
    GROUP BY p.id, p.role_category, p.seniority_level, p.salary_min, p.salary_max
"""
df = pd.read_sql(query, conn, params={"cloud": CLOUD_SKILLS})
conn.close()

df["avg_salary"] = (df["salary_min"] + df["salary_max"]) / 2
df["seniority_ordinal"] = df["seniority_level"].map(SENIORITY_ORDER)

print(f"\nRows pulled: {len(df)}")
print(f"Rows with a recognized seniority level: {df['seniority_ordinal'].notna().sum()}")

print("\n" + "=" * 60)
print("Descriptive stats on avg_salary (sanity check for outliers)")
print("=" * 60)
print(df["avg_salary"].describe())

# The raw data has extreme outliers (data errors / unusual comp packages) that
# distort every statistic downstream. Remove them using the standard IQR rule
# before running any real analysis.
q1 = df["avg_salary"].quantile(0.25)
q3 = df["avg_salary"].quantile(0.75)
iqr = q3 - q1
lower_bound = q1 - 1.5 * iqr
upper_bound = q3 + 1.5 * iqr

before_count = len(df)
df = df[(df["avg_salary"] >= lower_bound) & (df["avg_salary"] <= upper_bound)].copy()
after_count = len(df)

print(f"\nIQR outlier bounds: [${lower_bound:,.0f}, ${upper_bound:,.0f}]")
print(f"Removed {before_count - after_count} outlier rows ({before_count} -> {after_count})")
print("\nDescriptive stats AFTER outlier removal:")
print(df["avg_salary"].describe())

# ---------------- 4.1 Correlation matrix ----------------
print("\n" + "=" * 60)
print("4.1 -- Correlation matrix")
print("=" * 60)
corr_df = df[["avg_salary", "skill_count", "seniority_ordinal"]].dropna()
print(f"(using {len(corr_df)} rows with all 3 fields present)\n")
print(corr_df.corr())

# ---------------- 4.2 Linear regression ----------------
print("\n" + "=" * 60)
print("4.2 -- Linear regression: avg_salary ~ skill_count + seniority_ordinal + has_cloud_skill")
print("=" * 60)
reg_df = df.dropna(subset=["avg_salary", "skill_count", "seniority_ordinal", "has_cloud_skill"]).copy()
reg_df["has_cloud_skill"] = reg_df["has_cloud_skill"].astype(int)
print(f"(using {len(reg_df)} rows with all fields present)\n")

X = reg_df[["skill_count", "seniority_ordinal", "has_cloud_skill"]]
X = sm.add_constant(X)
y = reg_df["avg_salary"]

model = sm.OLS(y, X).fit()
print(model.summary())

# ---------------- 4.3 T-test ----------------
print("\n" + "=" * 60)
print("4.3 -- T-test: does having a cloud skill (AWS/Azure/GCP) change salary?")
print("=" * 60)
cloud_group = df[df["has_cloud_skill"] == True]["avg_salary"].dropna()
no_cloud_group = df[df["has_cloud_skill"] == False]["avg_salary"].dropna()

print(f"Cloud-skill postings: n={len(cloud_group)}, mean salary=${cloud_group.mean():,.0f}")
print(f"No-cloud postings:    n={len(no_cloud_group)}, mean salary=${no_cloud_group.mean():,.0f}")

t_stat, p_value = stats.ttest_ind(cloud_group, no_cloud_group, equal_var=False)
print(f"\nt-statistic: {t_stat:.3f}")
print(f"p-value: {p_value:.6f}")
if p_value < 0.05:
    print("-> Statistically significant difference (p < 0.05).")
else:
    print("-> NOT statistically significant at the 0.05 level.")

# Save the working dataset for later (dashboard / reference)
df.to_csv("data/processed/analysis_dataset.csv", index=False)
print("\nSaved working dataset to data/processed/analysis_dataset.csv")