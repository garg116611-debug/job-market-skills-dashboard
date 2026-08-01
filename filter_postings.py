"""
Filters postings.csv down to Software Engineering (SDE) and Data Analytics (DA)
roles only, based on job title keywords. Adds a `role_category` column.

Usage: python filter_postings.py
"""
import pandas as pd

DA_KEYWORDS = [
    "data analyst", "business analyst", "data scientist", "data science",
    "business intelligence", "bi analyst", "bi developer", "reporting analyst",
    "quantitative analyst", "analytics", "data engineer",
]

SDE_KEYWORDS = [
    "software engineer", "software developer", "sde", "backend developer",
    "backend engineer", "frontend developer", "frontend engineer",
    "full stack developer", "full stack engineer", "fullstack",
    "web developer", "application developer", "applications engineer",
    "systems engineer", "devops engineer", "mobile developer",
    "ios developer", "android developer", "programmer",
]


def classify(title):
    if not isinstance(title, str):
        return None
    t = title.lower()
    if any(kw in t for kw in DA_KEYWORDS):
        return "DA"
    if any(kw in t for kw in SDE_KEYWORDS):
        return "SDE"
    return None


print("Loading postings.csv (relevant columns only)...")
df = pd.read_csv(
    "data/raw/postings.csv",
    usecols=[
        "job_id", "title", "company_name", "company_id", "location",
        "formatted_experience_level", "job_posting_url", "listed_time",
        "description", "remote_allowed",
    ],
)

print(f"Total postings loaded: {len(df)}")

df["role_category"] = df["title"].apply(classify)
filtered = df[df["role_category"].notna()].copy()

print("\n" + "=" * 50)
print(f"Matched SDE + DA postings: {len(filtered)} / {len(df)} "
      f"({100 * len(filtered) / len(df):.1f}%)")
print(filtered["role_category"].value_counts())

filtered.to_csv("data/processed/postings_filtered.csv", index=False)
print("\nSaved to data/processed/postings_filtered.csv")

print("\nSample titles that got matched (10 random):")
print(filtered["title"].sample(min(10, len(filtered)), random_state=1).to_list())
