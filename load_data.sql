-- Loads the CSV files in data/ into clinical_db.
-- Run after schema.sql.
-- Usage: psql -U postgres -d clinical_db -f load_data.sql

\set ON_ERROR_STOP on

TRUNCATE patients, providers, encounters, diagnoses, treatments
    RESTART IDENTITY CASCADE;

\copy patients   FROM 'data/patients.csv'   WITH (FORMAT csv, HEADER true)
\copy providers  FROM 'data/providers.csv'  WITH (FORMAT csv, HEADER true)
\copy encounters FROM 'data/encounters.csv' WITH (FORMAT csv, HEADER true)
\copy diagnoses  FROM 'data/diagnoses.csv'  WITH (FORMAT csv, HEADER true)
\copy treatments FROM 'data/treatments.csv' WITH (FORMAT csv, HEADER true)

-- update SERIAL counters
SELECT setval('patients_patient_id_seq',     (SELECT MAX(patient_id)   FROM patients));
SELECT setval('providers_provider_id_seq',   (SELECT MAX(provider_id)  FROM providers));
SELECT setval('encounters_encounter_id_seq', (SELECT MAX(encounter_id) FROM encounters));
SELECT setval('diagnoses_diagnosis_id_seq',  (SELECT MAX(diagnosis_id) FROM diagnoses));
SELECT setval('treatments_treatment_id_seq', (SELECT MAX(treatment_id) FROM treatments));

ANALYZE patients, providers, encounters, diagnoses, treatments;

\echo
\echo Dataset loaded:
SELECT 'patients'   AS table_name, COUNT(*) AS rows FROM patients
UNION ALL SELECT 'providers',  COUNT(*) FROM providers
UNION ALL SELECT 'encounters', COUNT(*) FROM encounters
UNION ALL SELECT 'diagnoses',  COUNT(*) FROM diagnoses
UNION ALL SELECT 'treatments', COUNT(*) FROM treatments;
