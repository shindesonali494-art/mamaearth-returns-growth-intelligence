# Mamaearth Returns & Growth Intelligence Pipeline

## Overview

This repository implements the 100-mark **Mamaearth Returns & Growth Intelligence Pipeline** in three connected layers:

1. **SQL relational layer** — creates and seeds SQLite tables and runs reporting queries on the raw data.
2. **Python/Pandas analysis layer** — independently cleans the same raw CSV files, performs EDA, reconciles revenue against SQL, flags outliers, tests hypotheses, and generates the verified `narrator/findings.json`.
3. **GenAI narrator layer** — consumes the verified findings and produces a Situation–Complication–Resolution (SCR) narrative. It supports Gemini when `GEMINI_API_KEY` is configured and a fully offline deterministic fallback when it is not.

The source CSV files in `data/` are not manually edited. Cleaning occurs in the Python pipeline.

## Repository structure

```text
mamaearth_returns_growth_intelligence/
├── README.md
├── sql/
│   ├── schema.sql
│   ├── seed_data.sql
│   └── reports.sql
├── data/
│   ├── customers.csv
│   ├── products.csv
│   └── orders.csv
├── analysis/
│   ├── clean_and_eda.py
│   └── visualize.py
├── visualizations/
│   ├── return_rate_by_payment.png
│   └── monthly_revenue_trend.png
└── narrator/
    ├── findings.json
    ├── generate_narrative.py
    └── sample_output.txt
```

## Requirements

- Python 3.9+
- pandas
- numpy
- matplotlib
- SQLite 3
- Optional for online GenAI path: `google-genai`

Install Python dependencies:

```bash
pip install pandas numpy matplotlib google-genai
```

The offline narrator path does not require a Gemini API key.

---

# Exact run order

## 1. SQL relational layer

From the repository root, create a fresh SQLite database:

```bash
sqlite3 mamaearth.db < sql/schema.sql
sqlite3 mamaearth.db < sql/seed_data.sql
sqlite3 mamaearth.db < sql/reports.sql
```

The seed script is generated from the exact CSV source files and is re-runnable after the schema is recreated.

Basic row-count checks:

```sql
SELECT COUNT(*) FROM customers;
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM orders;
```

Expected counts:

- customers: 45
- products: 16
- orders: 180

`sql/reports.sql` contains all required Part 1 reports and includes the expected output as comments above each query.

### SQL → Python relationship

Part 2 intentionally does **not** read the SQLite database. It independently reads the same raw CSV files so the SQL and Pandas pipelines can be compared/reconciled.

---

## 2. Python/Pandas analysis layer

Run:

```bash
python analysis/clean_and_eda.py
```

This script:

- loads all three raw CSV files;
- standardizes payment method casing;
- detects/removes the five natural-key duplicate orders;
- imputes missing discount and rating values;
- merges orders, products and customers;
- calculates `order_value`;
- reconciles cleaned revenue against the raw SQL revenue;
- independently verifies the duplicate revenue delta;
- performs IQR quantity outlier detection;
- tests the COD return-rate hypothesis;
- performs payment-method/city-tier segmentation;
- calculates the correlation matrix and correlation-strength bands;
- produces both monthly revenue series;
- identifies the true corrected peak month;
- writes `narrator/findings.json` **from computed values**, never by hand.

The script prints every intermediate result required by the acceptance criteria.

Then run:

```bash
python analysis/visualize.py
```

This regenerates:

```text
visualizations/return_rate_by_payment.png
visualizations/monthly_revenue_trend.png
```

The first chart uses cleaned payment-method return rates. The second uses the outlier-corrected monthly revenue series.

---

## 3. GenAI narrator layer

### Option A — Gemini API

Set the API key as an environment variable.

macOS/Linux:

```bash
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
python narrator/generate_narrative.py
```

Windows PowerShell:

```powershell
$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
python narrator/generate_narrative.py
```

The key is not stored in this repository.

The Gemini function uses:

- a separate system instruction;
- findings supplied dynamically from `findings.json`;
- `temperature=0.0` for deterministic factual reporting;
- an explicit `max_output_tokens`;
- an explicit request timeout;
- structured success/error return dictionaries.

### Option B — fully offline / no key

Simply run:

```bash
python narrator/generate_narrative.py
```

with no `GEMINI_API_KEY`.

The script automatically uses `generate_scr_narrative_offline(findings)`.

If an API call fails, it also falls back to the same offline deterministic function. Therefore the repository remains gradable without network access, paid quota, or API configuration.

The script also runs a numeric accuracy checker and saves the verified narrative to:

```text
narrator/sample_output.txt
```

---

# Verified pipeline figures

The pipeline is designed to reproduce these acceptance values from the supplied seed data:

| Metric | Verified value |
|---|---:|
| Raw SQL revenue | ₹99,860.20 |
| Cleaned Pandas revenue | ₹97,358.30 |
| Duplicate reconciliation delta | ₹2,501.90 |
| CARD return rate | 14.7% |
| COD return rate | 44.4% |
| UPI return rate | 18.9% |
| Highest-risk segment | COD + Tier-2 |
| Highest-risk segment return rate | 54.5% |
| True corrected peak | 2026-03 |
| Corrected March revenue | ₹20,318.90 |
| Apparent January revenue | ₹29,582.10 |
| Corrected January revenue | ₹11,637.10 |

These numbers are not used as the source of computation. The scripts calculate them from the raw CSVs and then export the verified findings.

## Data-flow guarantee

```text
data/*.csv
    │
    ├──► SQL schema + seed ──► SQL reports
    │
    └──► clean_and_eda.py
             │
             ├──► visual analysis inputs
             └──► narrator/findings.json
                         │
                         └──► generate_narrative.py
                                  │
                                  └──► sample_output.txt
```

No later layer independently invents or recalculates the business findings used in its narrative. The narrator receives its factual numbers from `findings.json`.

## Important reproducibility note

Run the layers in this order for a clean end-to-end reproduction:

```bash
sqlite3 mamaearth.db < sql/schema.sql
sqlite3 mamaearth.db < sql/seed_data.sql
sqlite3 mamaearth.db < sql/reports.sql

python analysis/clean_and_eda.py
python analysis/visualize.py

python narrator/generate_narrative.py
```

`findings.json` should always be regenerated by `clean_and_eda.py` before the narrator is run.
