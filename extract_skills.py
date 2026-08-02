"""
Phase 2.3 -- Skill matching.
Scans postings.csv `description` text for known skills from etl/skills_taxonomy.json.
Saves results to data/processed/posting_skills_extracted.csv

Usage: python extract_skills.py
"""
import json
import re
import time
import pandas as pd

# ---------- 1. Load the taxonomy ----------
with open("etl/skills_taxonomy.json", "r", encoding="utf-8") as f:
    taxonomy = json.load(f)
taxonomy.pop("_comment", None)  # not a real skill, just a note in the file

# Build alias -> canonical name map (canonical name maps to itself too)
alias_to_canonical = {}
for canonical, info in taxonomy.items():
    alias_to_canonical[canonical.lower()] = canonical
    for alias in info.get("aliases", []):
        alias_to_canonical[alias.lower()] = canonical

print(f"Loaded {len(taxonomy)} skills, {len(alias_to_canonical)} total terms (incl. aliases)")

# ---------- 2. Build one big regex ----------
# Sort longest-first so multi-word terms (e.g. "Power BI") aren't shadowed by shorter ones.
terms_sorted = sorted(alias_to_canonical.keys(), key=len, reverse=True)
escaped_terms = [re.escape(t) for t in terms_sorted]

# Custom boundaries instead of \b: \b breaks on symbols like "+" or "#" (as in C++, C#),
# so we check "not preceded/followed by a letter or digit" instead.
pattern = re.compile(
    r"(?<![A-Za-z0-9])(?:" + "|".join(escaped_terms) + r")(?![A-Za-z0-9])",
    re.IGNORECASE,
)

# ---------- 3. Load postings and match ----------
print("Loading postings.csv (only job_id + description columns, to keep it light)...")
df = pd.read_csv("data/raw/postings.csv", usecols=["job_id", "description"])
df["description"] = df["description"].fillna("")

# These skill names collide with common English words / single letters, so a plain
# regex match is unreliable ("go" the verb, "R" as a random letter, etc).
# We only accept them when they appear in list-style formatting, e.g. "Python, SQL, Go, AWS".
AMBIGUOUS_SKILLS = {"Go", "R", "C", "Express.js"}
LIST_DELIMS = set(",;|•-*()\n:")

def looks_like_list_context(text, start, end, window=3):
    before = text[max(0, start - window):start].rstrip()
    after = text[end:end + window].lstrip()
    before_ok = (len(before) == 0) or (before[-1] in LIST_DELIMS)
    after_ok = (len(after) == 0) or (after[0] in LIST_DELIMS)
    return before_ok and after_ok

print(f"Scanning {len(df)} postings for skill mentions... this may take a few minutes.")
start = time.time()

rows = []
for job_id, text in zip(df["job_id"], df["description"]):
    found = set()
    for match in pattern.finditer(text):
        canonical = alias_to_canonical[match.group(0).lower()]
        if canonical in AMBIGUOUS_SKILLS:
            if not looks_like_list_context(text, match.start(), match.end()):
                continue
        found.add(canonical)
    for skill in found:
        rows.append((job_id, skill))

elapsed = time.time() - start
print(f"Done in {elapsed:.1f} seconds.")

result = pd.DataFrame(rows, columns=["job_id", "skill_name"])
result.to_csv("data/processed/posting_skills_extracted.csv", index=False)

# ---------- 4. Quick sanity stats ----------
print("\n" + "=" * 50)
print(f"Total (posting, skill) pairs extracted: {len(result)}")
print(f"Postings with at least 1 skill found: {result['job_id'].nunique()} / {len(df)} "
      f"({100 * result['job_id'].nunique() / len(df):.1f}%)")
print("\nTop 15 most common skills found:")
print(result["skill_name"].value_counts().head(15))