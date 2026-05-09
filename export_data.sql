-- Exports the tables to CSV files under data/.
-- Usage: psql -U postgres -d clinical_db -f export_data.sql

\set ON_ERROR_STOP on

\copy (SELECT * FROM patients   ORDER BY patient_id)   TO 'data/patients.csv'   WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM providers  ORDER BY provider_id)  TO 'data/providers.csv'  WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM encounters ORDER BY encounter_id) TO 'data/encounters.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM diagnoses  ORDER BY diagnosis_id) TO 'data/diagnoses.csv'  WITH (FORMAT csv, HEADER true)
\copy (SELECT * FROM treatments ORDER BY treatment_id) TO 'data/treatments.csv' WITH (FORMAT csv, HEADER true)

\echo
\echo CSV export complete. Files written to data/:
\! ls -la data/*.csv
