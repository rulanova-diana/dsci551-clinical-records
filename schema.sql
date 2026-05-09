-- Clinical Diagnosis and Treatment Records System
-- Run with: psql -U postgres -d clinical_db -f schema.sql

DROP TABLE IF EXISTS treatments  CASCADE;
DROP TABLE IF EXISTS diagnoses   CASCADE;
DROP TABLE IF EXISTS encounters  CASCADE;
DROP TABLE IF EXISTS providers   CASCADE;
DROP TABLE IF EXISTS patients    CASCADE;

CREATE TABLE patients (
    patient_id  SERIAL PRIMARY KEY,
    full_name   VARCHAR(100) NOT NULL,
    dob         DATE         NOT NULL,
    contact     VARCHAR(200)
);

CREATE TABLE providers (
    provider_id SERIAL PRIMARY KEY,
    full_name   VARCHAR(100) NOT NULL,
    specialty   VARCHAR(100),
    contact     VARCHAR(200)
);

CREATE TABLE encounters (
    encounter_id    SERIAL PRIMARY KEY,
    patient_id      INT  REFERENCES patients(patient_id)  ON DELETE CASCADE,
    provider_id     INT  REFERENCES providers(provider_id) ON DELETE SET NULL,
    encounter_date  DATE NOT NULL,
    chief_complaint TEXT
);

CREATE TABLE diagnoses (
    diagnosis_id   SERIAL      PRIMARY KEY,
    encounter_id   INT         REFERENCES encounters(encounter_id) ON DELETE CASCADE,
    diagnosis_code VARCHAR(20) NOT NULL,
    description    TEXT
);

CREATE TABLE treatments (
    treatment_id   SERIAL      PRIMARY KEY,
    diagnosis_id   INT         REFERENCES diagnoses(diagnosis_id) ON DELETE CASCADE,
    treatment_plan TEXT,
    outcome        VARCHAR(50)
);

-- indexes
CREATE INDEX idx_diagnoses_code
    ON diagnoses(diagnosis_code);

CREATE INDEX idx_encounters_patient_date
    ON encounters(patient_id, encounter_date);

ANALYZE patients, providers, encounters, diagnoses, treatments;
