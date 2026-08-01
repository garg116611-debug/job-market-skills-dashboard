-- Job Market Skills Intelligence Dashboard
-- Core schema: 4 normalized tables (3NF)
-- Why normalized: avoids storing "Python, AWS, Docker" as one messy text field.
-- Instead, each skill exists once in `skills`, and posting_skills links postings
-- to skills many-to-many. This makes "how many postings need Python?" a fast,
-- simple JOIN instead of string-searching every row.

CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS postings (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(100) UNIQUE,
    title VARCHAR(255),
    company_id INT REFERENCES companies(id),
    location VARCHAR(255),
    role_category VARCHAR(20),      -- 'SDE' or 'DA'
    seniority_level VARCHAR(50),
    min_experience INT,
    max_experience INT,
    salary_min NUMERIC(10,2),
    salary_max NUMERIC(10,2),
    description_raw TEXT,
    posted_date DATE,
    scraped_date DATE DEFAULT CURRENT_DATE,
    source_site VARCHAR(50),
    job_url TEXT
);

CREATE TABLE IF NOT EXISTS skills (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50)            -- language, framework, cloud, etc.
);

CREATE TABLE IF NOT EXISTS posting_skills (
    posting_id INT REFERENCES postings(id),
    skill_id INT REFERENCES skills(id),
    PRIMARY KEY (posting_id, skill_id)
);

-- Simple pipeline run log for Phase 6 automation later
CREATE TABLE IF NOT EXISTS pipeline_logs (
    id SERIAL PRIMARY KEY,
    run_started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rows_scraped INT,
    rows_failed INT,
    duration_seconds NUMERIC(10,2),
    notes TEXT
);
