# Job Market Skills Intelligence Dashboard

Analyzes real Software Engineering (SDE) and Data Analyst (DA) job postings to
answer a genuine analytical question: **which skills actually move the needle
on salary, and by how much?** Built as an end-to-end pipeline — not just a
notebook — from raw scraped/sourced data through a normalized database to
statistically validated findings.

---

## Problem Statement

Job seekers (myself included) are told to "learn in-demand skills," but rarely
shown the actual data behind that advice. This project pulls real job postings,
extracts which skills each one requires, and statistically tests whether
specific skills (like cloud platforms) are tied to higher pay — rather than
just assuming it.

---

## Architecture

```
[Kaggle dataset: 123,849 LinkedIn postings]
        |
        v
[Filter to SDE + DA roles by title]  ->  5,109 relevant postings
        |
        v
[Regex skill extraction against a 96-skill taxonomy]  ->  29,600 skill mentions
        |
        v
[Normalized PostgreSQL DB (Neon)]
   companies | postings | skills | posting_skills | pipeline_logs
        |
        v
[Statistical analysis: correlation, regression, t-test]
        |
        v
[Power BI / Tableau dashboard]  <- in progress
```

---

## Tech Stack

- **Python** (pandas, psycopg2, statsmodels, scipy) — cleaning, extraction, analysis
- **PostgreSQL on Neon** — normalized relational storage
- **Power BI / Tableau** — dashboard (in progress)
- **Git/GitHub** — version control

---

## Key Findings

Full write-up: [`ANALYSIS_FINDINGS.md`](./ANALYSIS_FINDINGS.md)

Analysis run on 1,438 postings with a clean, outlier-removed, USD-normalized
annual salary (IQR method removed 49 rows with clearly erroneous salary values).

- **Seniority is the strongest salary driver**: each level up (Internship →
  Entry → Associate → Mid-Senior → Director → Executive) is associated with
  **+$15,250/year** on average (p < 0.001).
- **Cloud skills (AWS/Azure/GCP) show a real premium in a simple comparison**:
  postings requiring them average **$147,325** vs **$137,962** for postings
  that don't (p = 0.000134, statistically significant).
- **But that premium weakens once seniority is controlled for** (regression
  p = 0.079, borderline) — suggesting cloud skills are partly a *proxy* for
  seniority rather than an independent salary driver on their own.
- Simply listing more skills has only a weak link to salary (p = 0.170, not
  significant) — quantity of skills matters far less than seniority.
- Model R² = 0.101 — these three factors explain ~10% of salary variation,
  which is expected; real salary depends on many things not captured here
  (company size, exact city, negotiation, etc).

## Dashboard (Tableau Public)

Interactive dashboard built in Tableau, connected to flat exports from the
Postgres DB (`export_for_tableau.py`, since Tableau Public doesn't support
live database connections):

1. **SDE vs DA posting split**
2. **Top 15 Skills in Demand**
3. **Salary Distribution by Seniority Level** (box plot, outliers removed)
4. **Average Salary by State** (switched from a city-level map to a state-level
   bar chart after running into geocoding issues with ambiguous/incomplete
   location text in the source data)
5. **Posting Volume Over Time** — intentionally left as a limited/flat view;
   the source dataset is a single ~5-week snapshot, so there isn't enough
   time range for a real trend. A live weekly scraper (out of scope for this
   version) would be needed for genuine trend analysis.
6. **Personal Skill Gap Analysis** — my own skills vs. the top skills in
   demand, highlighting what to learn next.

## Extraction Validation (Phase 2.5)

A 25-posting spot-check of the skill extractor found no confirmed errors on
first manual review. Because a perfect 100%/100% result is unrealistic for
any regex-based extractor, I re-inspected the log independently and caught
two real issues the first pass missed:
- **"Express.js" false positive** — its alias "express" was matching the
  common English word (e.g., "...allows users to *express* themselves"),
  not the framework. Fixed by requiring list-style context for this term,
  the same fix pattern used earlier for "Go"/"R"/"C".
- **"COBOL" was missing from the taxonomy entirely** — a posting explicitly
  titled "Sr. Software Engineer - COBOL" couldn't have been caught since the
  skill wasn't in the list. Added it.

Both were fixed and the full dataset was re-extracted and reloaded before
final analysis. This is a more honest and defensible validation story than
an inflated "100% precision" claim.

---

## How to Run Locally

1. Clone the repo, create a virtual environment, install dependencies:
   ```bash
   python -m venv venv
   venv\Scripts\Activate.ps1        # Windows
   pip install -r requirements.txt
   ```
2. Create a `.env` file (see `.env.example`) with your own Postgres
   `DATABASE_URL` (this project uses [Neon](https://neon.tech)'s free tier).
3. Download the [LinkedIn Job Postings dataset](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings)
   from Kaggle into `data/raw/` (see folder structure below).
4. Run the pipeline in order:
   ```bash
   python create_schema.py            # create DB tables
   python filter_postings.py          # filter to SDE + DA roles
   python extract_skills.py           # regex skill extraction
   python load_to_db.py               # load everything into Postgres
   python fix_salary_normalization.py # normalize salary to annual USD
   python analyze.py                  # run the statistical analysis
   ```

---

## Project Structure

```
├── sql/schema.sql              # DB schema (5 tables)
├── etl/skills_taxonomy.json    # 96-skill taxonomy with aliases
├── data/raw/                   # source CSVs (not committed)
├── data/processed/             # cleaned/derived CSVs (not committed)
├── filter_postings.py          # Phase 1.5 - role filtering
├── extract_skills.py           # Phase 2 - skill extraction
├── load_to_db.py                # Phase 3 - DB loading
├── fix_salary_normalization.py # salary unit normalization fix
├── analyze.py                  # Phase 4 - statistical analysis
├── ANALYSIS_FINDINGS.md        # full write-up of Phase 4 results
└── PROGRESS_LOG.md             # session-by-session build log
```

---

## Status

- [x] Data collection & cleaning
- [x] Skill extraction (regex + taxonomy)
- [x] Normalized database (Neon Postgres)
- [x] Statistical analysis (correlation, regression, t-test)
- [x] Extraction validation (spot-check + real bug fixes)
- [x] Interactive dashboard (Tableau) — 6 sheets, published locally
- [ ] Live scraper (Naukri/Indeed) — not implemented; used a static Kaggle
      dataset instead. Documented here rather than left unmentioned.
- [ ] Automation (weekly refresh via cron/Airflow) — future scope for the
      same reason; no live data source to refresh yet.

## Key Learnings / Challenges

- Raw LinkedIn skill categories (`skills.csv`) turned out to be broad job-function
  tags, not technical skills — had to build a custom taxonomy + regex matcher instead.
- Naive regex matching produced false positives for short/common skill names
  ("Go", "R", "C", later also "Express.js") matching ordinary English words —
  fixed by requiring list-style context for ambiguous terms.
- Salary data mixed hourly/weekly/monthly/yearly pay periods — had to normalize
  everything to annual USD before any salary analysis was meaningful.
- Extreme outliers ($32/year to $6.9M/year) were distorting every statistic
  until removed via the IQR method.
- A rushed first pass at manual validation produced a suspicious "0 errors
  found" result — re-inspecting it independently surfaced two real, fixable
  issues. Worth remembering: a perfect validation score is a signal to look
  harder, not a result to report at face value.
- Tableau Public can't connect live to a database, so the pipeline needed a
  flat-CSV export step before any dashboard work could start.
- City-level geocoding in Tableau failed for a meaningful chunk of postings
  (inconsistent "City, ST" formatting in the source data) — a state-level
  view was more reliable than fighting individual city geocoding.
