# Phase 4 — Statistical Analysis Findings

**Dataset:** 1,487 SDE/DA postings with a clean, USD-normalized annual salary
(out of 5,109 total relevant postings — most LinkedIn postings simply don't disclose salary).

**Outlier handling:** 49 rows removed via the IQR method (salaries outside
[$11,465, $266,625] — included clear data errors like $32/year and $6.9M/year).
Final analysis set: **1,438 postings**, salary range $12,000–$265,000.

---

## 4.1 Correlation Matrix

| Pair | Correlation | Interpretation |
|---|---|---|
| seniority ↔ salary | **0.326** | Moderate positive — more senior roles pay more, as expected |
| skill_count ↔ salary | 0.101 | Weak positive — listing more skills has only a small link to salary |
| skill_count ↔ seniority | 0.031 | ~None — the two are independent of each other |

## 4.2 Linear Regression

`avg_salary ~ skill_count + seniority_ordinal + has_cloud_skill`
(n = 1,058, R² = 0.101)

| Variable | Coefficient | p-value | Significant? |
|---|---|---|---|
| seniority_ordinal | +$15,250 per level | p < 0.001 | **Yes — strongest finding** |
| has_cloud_skill | +$5,284 | p = 0.079 | Borderline (not quite at 0.05) |
| skill_count | +$430 per skill | p = 0.170 | No |

**R² = 0.101** — the model explains ~10% of salary variation. Low, but expected:
real salary depends on many factors not in this dataset (company size, exact
city, negotiation, etc). The regression is still valid for the relationships
it *does* find.

## 4.3 T-test — Cloud Skills vs Salary

- Cloud-skill postings (AWS/Azure/GCP): n=430, mean = **$147,325**
- Non-cloud postings: n=901, mean = **$137,962**
- t = 3.835, **p = 0.000134 (highly significant)**

## Key Insight — the nuance that ties 4.2 and 4.3 together

The t-test alone says cloud skills come with a statistically significant salary
premium. But once seniority is *controlled for* in the regression, the cloud-skill
effect weakens to borderline significance (p = 0.079). This suggests the raw
cloud-skill salary premium is **partly explained by cloud skills being more
common in senior roles** — not purely an independent effect of the skill itself.

This is the difference between a bivariate test and a controlled regression —
worth stating explicitly in the README/interview, since spotting it is exactly
what separates real analysis from a surface-level chart.

## Known Limitations (be upfront about these)

- Seniority is an ordinal proxy (Internship→0 ... Executive→5) derived from
  LinkedIn's text categories, not numeric years of experience (raw data didn't
  have a clean numeric experience field).
- Salary data covers only the ~29% of postings that disclosed pay — may not be
  representative of all postings.
- `skill_count` is a simple count from the 96-skill taxonomy; doesn't weight by
  skill importance/rarity.
