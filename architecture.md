# Architecture

> Living document. Updated as each component is built.
> Status legend: ✅ built · 🚧 in progress · 📋 planned

## 1. Problem

A commercial insurer receives thousands of claims across several product lines. Two things decide how a claim should be handled:

1. **Severity**: will this claim be **Low**, **Medium**, or **High** cost?
2. **Prolonged settlement risk**: is this claim likely to take much longer than usual to close?

Predicting both early lets the insurer send complex claims to senior adjusters, set reserves more accurately, and reduce settlement time.

**Product lines covered:** Commercial Auto, General Liability, Workers' Compensation, Commercial Property.

## 2. High-level pipeline

```
 ┌──────────────┐   ┌─────────────────────┐   ┌──────────────────┐
 │ 1. Synthetic │──▶│ 2. Source systems   │──▶│ 3. Integration   │
 │    data gen  │   │  SQLite  ("DB2")    │   │  SQL + PySpark   │
 └──────────────┘   │  Doc store("FileNet")│   │  → Parquet lake  │
                    └─────────────────────┘   └────────┬─────────┘
                                                       ▼
 ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐
 │ 6. Reporting │◀──│ 5. Models &  │◀──│ 4. Features              │
 │ Matplotlib + │   │  evaluation  │   │  tabular + NLP (TF-IDF)  │
 │  Streamlit   │   │  (sklearn)   │   └──────────────────────────┘
 └──────────────┘   └──────────────┘
```

| # | Component | Responsibility | Status |
|---|-----------|----------------|--------|
| 0 | Project setup | Structure, environment, config, logging, CI | ✅ |
| 1 | Data generation | Reproducible synthetic policies, claims, claimants, reserves, payments, loss history, adjuster notes | 📋 |
| 2 | Source systems | Relational store (SQLite) and document store for adjuster notes | 📋 |
| 3 | Integration | SQL joins and PySpark jobs into a governed, partitioned Parquet dataset with data-quality checks | 📋 |
| 4 | Features | Cleaning, outlier handling, tabular features, NLTK + TF-IDF text indicators (injury, litigation, fraud, severity) | 📋 |
| 5 | Modelling & evaluation | Logistic Regression, Decision Tree, Random Forest, Gradient Boosting for both targets. Precision, recall, F1, ROC-AUC, confusion matrices, cross-validation, per-product-line stability | 📋 |
| 6 | Reporting | Matplotlib reports and a Streamlit dashboard: severity, reserve exposure, loss trends, high-risk segments | 📋 |
| 7 | Automation | CI (lint + tests on every PR, `main` protected) is live since Phase 0. Still to add: pipeline smoke test and continuous deployment of the dashboard | 🚧 |

## 3. Technology mapping

This project mirrors an enterprise claims-analytics stack using open, locally runnable equivalents.

| Enterprise system | Role | Used here |
|-------------------|------|-----------|
| IBM DB2 | Operational database | SQLite (SQL kept portable to PostgreSQL/DB2) |
| IBM FileNet | Document management | File-based document store with a metadata index |
| Hadoop / HDFS / Hive | Distributed storage and SQL | PySpark + partitioned Parquet |
| IBM Cognos | BI reporting | Matplotlib reports + Streamlit dashboard |
| Python 2.7 | Language | Python 3.11 |

## 4. Key design decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Data | Synthetic, seeded (~50,000 claims, configurable) | No privacy risk. Fully reproducible |
| CI/CD | GitHub Actions, set up in Phase 0 (`.github/workflows/ci.yml`) | Native to GitHub, no server to maintain, free for public repos. Every PR runs `ruff` + `pytest` with coverage on a clean Ubuntu / Python 3.11 machine. `main` only accepts green PRs. Least-privilege (read-only) token, outdated runs cancelled, 10-minute timeout |
| Code layout | Logic in an installable `src/` package. Notebooks only for exploration | Testable, reusable, importable by the dashboard and CI |
| Configuration | One YAML file (`config/settings.yaml`) loaded into frozen, typed dataclasses and validated at startup | No magic numbers in code. Bad settings fail fast with a clear error. `CLAIM_SEVERITY_CONFIG` lets CI swap in a small, fast config. `safe_load` only, so a config file can never run code |
| Target definitions | Business thresholds live in a `targets` config section: severity cut points (Low < $10k ≤ Medium < $100k ≤ High) and prolonged settlement (> 365 days). Only cut points are stored, never full ranges | The generator produces raw facts (cost, days). Labelling is a separate, shared decision. Storing each boundary once means bands can never overlap or leave gaps |
| Synthetic data realism | A clean "truth" generator with a hidden cost/duration recipe, then a separate, config-driven mess-maker that injects real-world problems and writes an answer key (git-ignored, under `data/`) | Real claims data is confidential. Fault injection lets the cleaning pipeline be **measured**, not just written |
| Logging | Standard-library `logging`, configured once by entry points via `setup_logging()`. Modules only call `logging.getLogger(__name__)` | Timestamped, levelled, source-tagged messages. Logs go to stderr so they never corrupt real output on stdout. Optional log file. `CLAIM_SEVERITY_LOG_LEVEL` turns detail up or down without code changes. Independent of config, so it still works when config is broken |

## 5. Repository layout

```
insurance-claim-severity-prediction/
├── .github/workflows/    # CI: lint + tests on every pull request
├── src/claim_severity/   # installable Python package: all real logic lives here
├── tests/                # pytest test suite
├── notebooks/            # exploration only; imports from src/
├── config/               # YAML settings (row counts, seeds, paths)
├── pyproject.toml        # dependencies, build settings, ruff + pytest config
└── architecture.md       # this document
```

Generated data and models (`data/`, `models/`) are created by the pipeline and are not committed.
