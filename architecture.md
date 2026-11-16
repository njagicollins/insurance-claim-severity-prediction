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
| 0 | Project setup | Structure, environment, config, logging | 🚧 |
| 1 | Data generation | Reproducible synthetic policies, claims, claimants, reserves, payments, loss history, adjuster notes | 📋 |
| 2 | Source systems | Relational store (SQLite) and document store for adjuster notes | 📋 |
| 3 | Integration | SQL joins and PySpark jobs into a governed, partitioned Parquet dataset with data-quality checks | 📋 |
| 4 | Features | Cleaning, outlier handling, tabular features, NLTK + TF-IDF text indicators (injury, litigation, fraud, severity) | 📋 |
| 5 | Modelling & evaluation | Logistic Regression, Decision Tree, Random Forest, Gradient Boosting for both targets. Precision, recall, F1, ROC-AUC, confusion matrices, cross-validation, per-product-line stability | 📋 |
| 6 | Reporting | Matplotlib reports and a Streamlit dashboard: severity, reserve exposure, loss trends, high-risk segments | 📋 |
| 7 | Automation | GitHub Actions CI (lint, tests, pipeline smoke test) and continuous deployment of the dashboard | 📋 |

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
| CI/CD | GitHub Actions | Native to GitHub, no server to maintain, free for public repos |
| Code layout | Logic in an installable `src/` package. Notebooks only for exploration | Testable, reusable, importable by the dashboard and CI |

## 5. Repository layout

```
insurance-claim-severity-prediction/
├── src/claim_severity/   # installable Python package: all real logic lives here
├── tests/                # pytest test suite
├── notebooks/            # exploration only; imports from src/
├── config/               # YAML settings (row counts, seeds, paths)
├── pyproject.toml        # dependencies, build settings, ruff + pytest config
└── architecture.md       # this document
```

Generated data and models (`data/`, `models/`) are created by the pipeline and are not committed.
