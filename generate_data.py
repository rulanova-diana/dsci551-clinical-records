# inserts random data into clinical_db
import random
from datetime import date, timedelta

import psycopg2

from config import DB_CONFIG


DIAGNOSES = [
    ("G43", "Migraine"),
    ("J45", "Asthma"),
    ("E11", "Type 2 Diabetes Mellitus"),
    ("I10", "Essential Hypertension"),
    ("M54", "Dorsalgia / Back Pain"),
    ("J06", "Acute Upper Respiratory Infection"),
    ("K21", "Gastroesophageal Reflux Disease"),
    ("F32", "Major Depressive Disorder"),
    ("F41", "Anxiety Disorder"),
    ("N39", "Urinary Tract Infection"),
    ("J20", "Acute Bronchitis"),
    ("K57", "Diverticular Disease of Intestine"),
    ("M79", "Fibromyalgia"),
    ("I25", "Chronic Ischemic Heart Disease"),
    ("E78", "Hyperlipidemia"),
    ("G47", "Sleep Disorders"),
    ("L40", "Psoriasis"),
    ("M05", "Rheumatoid Arthritis"),
    ("N18", "Chronic Kidney Disease"),
    ("J44", "Chronic Obstructive Pulmonary Disease"),
]

COMPLAINTS = [
    "Chest pain", "Shortness of breath", "Persistent headache", "Fatigue",
    "Abdominal pain", "Lower back pain", "Dizziness", "Nausea and vomiting",
    "High fever", "Joint pain", "Skin rash", "Anxiety and restlessness",
    "Insomnia", "Unexplained weight loss", "Chronic cough", "Heart palpitations",
    "Blurred vision", "Frequent urination", "Muscle weakness", "Swollen ankles",
]

TREATMENT_PLANS = [
    "Prescribed Metformin 500 mg twice daily; dietary counseling",
    "Initiated physical therapy 3x/week; NSAIDs as needed",
    "Started SSRI therapy (Sertraline 50 mg); follow-up in 4 weeks",
    "Ordered CT scan and comprehensive blood panel",
    "Advised Mediterranean diet and 30-min daily exercise",
    "Prescribed Lisinopril 10 mg daily; sodium restriction",
    "Albuterol inhaler for acute relief; daily ICS controller",
    "Referred to specialist; imaging scheduled",
    "Cognitive behavioral therapy; sleep hygiene education",
    "Amoxicillin 500 mg TID for 7 days; increased fluid intake",
    "Lifestyle modifications; weight reduction program",
    "MRI lumbar spine ordered; activity modification",
    "Anticoagulation therapy initiated; INR monitoring weekly",
    "Multimodal pain management; opioid-sparing approach",
    "Follow-up labs in 3 months; statin therapy adjusted",
]

OUTCOMES = [
    "Improving", "Stable", "Recovered",
    "Worsening", "Under Observation", "Referred to Specialist",
]

FIRST = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael",
    "Linda", "William", "Barbara", "David", "Elizabeth", "Richard", "Susan",
    "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen", "Christopher",
    "Lisa", "Daniel", "Nancy", "Matthew", "Betty", "Anthony", "Margaret",
    "Mark", "Sandra", "Donald", "Ashley", "Steven", "Dorothy", "Paul",
    "Kimberly", "Andrew", "Emily", "Joshua", "Donna", "Kenneth", "Michelle",
    "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa", "Timothy", "Deborah",
]

LAST = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts",
]

SPECIALTIES = [
    "General Practice", "Cardiology", "Neurology", "Orthopedics",
    "Gastroenterology", "Pulmonology", "Endocrinology", "Psychiatry",
    "Dermatology", "Nephrology",
]


def rnd_date(start=date(2020, 1, 1), end=date(2025, 12, 31)):
    return start + timedelta(days=random.randint(0, (end - start).days))


def rnd_name():
    return f"{random.choice(FIRST)} {random.choice(LAST)}"


def batch_insert(cur, query, rows, batch=500):
    for i in range(0, len(rows), batch):
        cur.executemany(query, rows[i : i + batch])


def main():
    N_PATIENTS   = 1_000
    N_PROVIDERS  = 50
    N_ENCOUNTERS = 10_000

    print("Connecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    print(f"Inserting {N_PATIENTS} patients...")
    patients = [
        (
            rnd_name(),
            date(random.randint(1940, 2005), random.randint(1, 12), random.randint(1, 28)),
            f"555-{random.randint(1000, 9999)}",
        )
        for _ in range(N_PATIENTS)
    ]
    batch_insert(cur, "INSERT INTO patients (full_name, dob, contact) VALUES (%s,%s,%s)", patients)
    conn.commit()

    print(f"Inserting {N_PROVIDERS} providers...")
    providers = [
        (f"Dr. {rnd_name()}", random.choice(SPECIALTIES), f"ext-{random.randint(100,999)}@hospital.org")
        for _ in range(N_PROVIDERS)
    ]
    batch_insert(cur, "INSERT INTO providers (full_name, specialty, contact) VALUES (%s,%s,%s)", providers)
    conn.commit()

    print(f"Inserting {N_ENCOUNTERS} encounters...")
    encounters = [
        (
            random.randint(1, N_PATIENTS),
            random.randint(1, N_PROVIDERS),
            rnd_date(),
            random.choice(COMPLAINTS),
        )
        for _ in range(N_ENCOUNTERS)
    ]
    batch_insert(
        cur,
        "INSERT INTO encounters (patient_id, provider_id, encounter_date, chief_complaint) VALUES (%s,%s,%s,%s)",
        encounters,
    )
    conn.commit()

    print("Inserting diagnoses (1-3 per encounter)...")
    cur.execute("SELECT encounter_id FROM encounters ORDER BY encounter_id")
    enc_ids = [r[0] for r in cur.fetchall()]
    diag_rows = []
    for eid in enc_ids:
        for code, desc in random.sample(DIAGNOSES, random.randint(1, 3)):
            diag_rows.append((eid, code, desc))
    batch_insert(
        cur,
        "INSERT INTO diagnoses (encounter_id, diagnosis_code, description) VALUES (%s,%s,%s)",
        diag_rows,
    )
    conn.commit()

    print("Inserting treatments (1-2 per diagnosis)...")
    cur.execute("SELECT diagnosis_id FROM diagnoses ORDER BY diagnosis_id")
    diag_ids = [r[0] for r in cur.fetchall()]
    treat_rows = []
    for did in diag_ids:
        for _ in range(random.randint(1, 2)):
            treat_rows.append((did, random.choice(TREATMENT_PLANS), random.choice(OUTCOMES)))
    batch_insert(
        cur,
        "INSERT INTO treatments (diagnosis_id, treatment_plan, outcome) VALUES (%s,%s,%s)",
        treat_rows,
    )
    conn.commit()

    print("Updating table statistics (ANALYZE)...")
    cur.execute("ANALYZE patients, providers, encounters, diagnoses, treatments")
    conn.commit()

    cur.close()
    conn.close()

    print("\nDataset generation complete")
    print(f"  Patients:   {N_PATIENTS:,}")
    print(f"  Providers:  {N_PROVIDERS:,}")
    print(f"  Encounters: {N_ENCOUNTERS:,}")
    print(f"  Diagnoses:  {len(diag_rows):,}")
    print(f"  Treatments: {len(treat_rows):,}")


if __name__ == "__main__":
    main()
