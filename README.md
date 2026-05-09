# Clinical Diagnosis and Treatment Records System

DSCI 551, Spring 2026
Diana Rulanova and Eliza Loke

A PostgreSQL command-line application that explores B-tree indexing, composite indexes, MVCC, and row-level locking in a clinical records setting.

---

## Prerequisites

- PostgreSQL 14 or later
- Python 3.9 or later
- psycopg2-binary (installed via pip, see step 3 below)

---

## Setup

### 1. Create the database

```bash
psql -U postgres -c "CREATE DATABASE clinical_db;"
```

### 2. Edit connection settings

Open `config.py` and update it with your PostgreSQL credentials:

```python
DB_CONFIG = {
    "dbname": "clinical_db",
    "user": "postgres",
    "password": "YOUR_PASSWORD",
    "host": "localhost",
    "port": "5432",
}
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Create tables and indexes

```bash
psql -U postgres -d clinical_db -f schema.sql
```

### 5. Load the dataset

There are two ways to load the data. Pick one.

**Option A: load the CSV files we already generated**

```bash
psql -U postgres -d clinical_db -f load_data.sql
```

The `data/` folder has five CSV files (patients, providers, encounters, diagnoses, treatments) with the same dataset we used in the demo and the report (1,000 patients, 50 providers, 10,000 encounters, 19,885 diagnoses, 29,949 treatments). Run the script from the repository root so the relative `data/...` paths work.

**Option B: generate a new synthetic dataset**

```bash
python generate_data.py
```

This produces a fresh dataset with different random values. The row counts will be slightly different because the script samples 1-3 diagnoses per encounter and 1-2 treatments per diagnosis, but the queries and execution plans behave the same way.

`export_data.sql` is what we used to produce the CSVs in `data/`. You only need it if you regenerate the data and want to refresh those files.

### 6. Run the application

```bash
python app.py
```

---

## Application Operations

| Option | Feature | PostgreSQL Internal |
|---|---|---|
| 1 | Lookup diagnoses by code | B-tree index scan vs sequential scan |
| 2 | Patient encounter history | Composite index, skip-sort |
| 3 | Concurrent treatment update | MVCC / READ COMMITTED |
| 4 | Row-level locking demo | SELECT FOR UPDATE |
| 5 | Monthly diagnosis summary | Hash join + HashAggregate |

---

## Project Structure

```
dsci551-clinical-records/
├── config.py           # database connection settings
├── schema.sql          # tables and indexes
├── data/               # pre-generated dataset (5 CSV files)
│   ├── patients.csv
│   ├── providers.csv
│   ├── encounters.csv
│   ├── diagnoses.csv
│   └── treatments.csv
├── load_data.sql       # loads the CSVs into the tables
├── export_data.sql     # exports the tables back out to CSV
├── generate_data.py    # generates a new synthetic dataset
├── app.py              # main CLI application
├── requirements.txt
└── README.md
```

---

## Team Focus Areas

**Diana Rulanova: B-tree indexing**

- `idx_diagnoses_code` on `diagnoses(diagnosis_code)` — used in operation 1.
- `idx_encounters_patient_date` on `encounters(patient_id, encounter_date)` — used in operation 2.
- Execution plans are shown using `EXPLAIN (ANALYZE, BUFFERS)`.

**Eliza Loke: MVCC and row-level locking**

- Operation 3 runs two concurrent sessions on the same treatment row to show how MVCC handles read/write concurrency.
- Operation 4 uses `SELECT FOR UPDATE` to show write/write blocking.
