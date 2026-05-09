import psycopg2
import psycopg2.extras
import threading
import time

from config import DB_CONFIG


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def lookup_diagnosis_by_code(conn):
    print("\n" + "="*60)
    print("OPERATION 1: Lookup Diagnoses by Code")
    print("="*60)

    code = input("\nEnter diagnosis code (e.g. G43, J45, E11, I10): ").strip().upper()
    if not code:
        code = "G43"

    query = """
        SELECT diagnosis_id, diagnosis_code, description
        FROM diagnoses
        WHERE diagnosis_code = %s
    """

    print("\nSearching for diagnoses with code:", code)
    print("\nSQL:")
    print("    SELECT diagnosis_id, diagnosis_code, description")
    print("    FROM diagnoses")
    print("    WHERE diagnosis_code = %s")

    # run with the index first
    print("\n--- EXPLAIN ANALYZE with B-tree index ---")
    cur = conn.cursor()
    cur.execute("EXPLAIN (ANALYZE, BUFFERS) " + query, (code,))
    rows = cur.fetchall()
    for row in rows:
        print("   ", row[0])

    print("\nPostgres uses the B-tree index (Bitmap Index Scan + Bitmap Heap Scan),")
    print("so it only touches the matching pages instead of every row.")

    # now turn off index access to compare
    print("\n--- EXPLAIN ANALYZE without index (forced Sequential Scan) ---")
    cur.execute("SET enable_indexscan = off")
    cur.execute("SET enable_bitmapscan = off")
    cur.execute("EXPLAIN (ANALYZE, BUFFERS) " + query, (code,))
    rows = cur.fetchall()
    for row in rows:
        print("   ", row[0])
    cur.execute("SET enable_indexscan = on")
    cur.execute("SET enable_bitmapscan = on")

    print("\nWithout the index Postgres has to scan every row.")
    print("Notice 'Rows Removed by Filter' and the higher execution time.")

    # print the actual rows
    print("\n--- Results ---")
    cur2 = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur2.execute(query + " LIMIT 10", (code,))
    results = cur2.fetchall()

    if results:
        print(f"Found diagnoses for code '{code}' (showing first 10):")
        for r in results:
            print(f"  ID: {r['diagnosis_id']}  |  Code: {r['diagnosis_code']}  |  {r['description']}")
    else:
        print(f"No diagnoses found for code '{code}'")

    cur.close()
    cur2.close()
    input("\nPress Enter to go back to the menu...")


def get_encounter_history(conn):
    print("\n" + "="*60)
    print("OPERATION 2: Patient Encounter History")
    print("="*60)

    patient_id = input("\nEnter patient ID (1-1000): ").strip()
    if not patient_id.isdigit():
        patient_id = "10"
    patient_id = int(patient_id)

    query = """
        SELECT encounter_id, patient_id, encounter_date, chief_complaint
        FROM encounters
        WHERE patient_id = %s
        ORDER BY encounter_date DESC
        LIMIT 10
    """

    print(f"\nGetting encounter history for patient #{patient_id}")
    print("\nSQL:")
    print("    SELECT encounter_id, patient_id, encounter_date, chief_complaint")
    print("    FROM encounters")
    print("    WHERE patient_id = %s")
    print("    ORDER BY encounter_date DESC")
    print("    LIMIT 10")

    print("\n--- EXPLAIN ANALYZE ---")
    cur = conn.cursor()
    cur.execute("EXPLAIN (ANALYZE, BUFFERS) " + query, (patient_id,))
    rows = cur.fetchall()
    for row in rows:
        print("   ", row[0])

    print("\nThe composite index is on (patient_id, encounter_date).")
    print("Postgres does an 'Index Scan Backward' to get the dates in DESC order.")
    print("There is no Sort node because the index is already sorted.")

    print("\n--- Results ---")
    cur2 = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur2.execute(query, (patient_id,))
    results = cur2.fetchall()

    if results:
        print(f"Encounter history for patient #{patient_id}:")
        for r in results:
            print(f"  Encounter {r['encounter_id']}  |  Date: {r['encounter_date']}  |  {r['chief_complaint']}")
    else:
        print(f"No encounters found for patient #{patient_id}")

    cur.close()
    cur2.close()
    input("\nPress Enter to go back to the menu...")


def mvcc_demo():
    print("\n" + "="*60)
    print("OPERATION 3: Concurrent Update - MVCC Demo")
    print("="*60)

    print("\nTwo sessions update/read the same treatment row.")
    print("Isolation level: READ COMMITTED (Postgres default)")
    print("\nFlow:")
    print("  Session 1 UPDATEs the row, then waits 3s before COMMIT")
    print("  Session 2 reads the row before Session 1 commits  -> sees old value")
    print("  Session 1 commits")
    print("  Session 2 reads again                              -> sees new value")

    # pick a row to use
    conn_temp = get_connection()
    cur = conn_temp.cursor()
    cur.execute("SELECT treatment_id, outcome FROM treatments LIMIT 1")
    treatment_id, original_outcome = cur.fetchone()
    cur.close()
    conn_temp.close()

    print(f"\nTarget row: treatment_id = {treatment_id}, current outcome = '{original_outcome}'")
    input("\nPress Enter to start the demo...")

    # used to sync the two threads
    session1_updated = threading.Event()
    session1_committed = threading.Event()
    results = {}

    def session1():
        conn = get_connection()
        conn.autocommit = False
        cur = conn.cursor()

        print("\n[Session 1] BEGIN")
        cur.execute(
            "UPDATE treatments SET outcome = %s WHERE treatment_id = %s",
            ("Improved", treatment_id)
        )
        print("[Session 1] UPDATE outcome -> 'Improved' (not committed yet)")
        session1_updated.set()

        # sleep so session 2 can read first
        time.sleep(3)
        conn.commit()
        session1_committed.set()
        print("[Session 1] COMMIT")

        cur.close()
        conn.close()

    def session2():
        # wait until s1 has issued its update
        session1_updated.wait()

        conn = get_connection()
        conn.autocommit = False
        cur = conn.cursor()

        # read before s1 commits
        cur.execute(
            "SELECT outcome FROM treatments WHERE treatment_id = %s",
            (treatment_id,)
        )
        value_before = cur.fetchone()[0]
        results["before"] = value_before
        print(f"\n[Session 2] Read before commit -> outcome = '{value_before}'")
        print("            (sees the last committed version, not the in-progress update)")

        # wait until s1 commits
        session1_committed.wait()

        # read again
        cur.execute(
            "SELECT outcome FROM treatments WHERE treatment_id = %s",
            (treatment_id,)
        )
        value_after = cur.fetchone()[0]
        results["after"] = value_after
        print(f"\n[Session 2] Read after commit  -> outcome = '{value_after}'")
        print("            (READ COMMITTED takes a fresh snapshot per statement)")

        conn.commit()
        cur.close()
        conn.close()

    t1 = threading.Thread(target=session1)
    t2 = threading.Thread(target=session2)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print("\n--- Summary ---")
    print(f"Before commit: Session 2 saw '{results.get('before')}'")
    print(f"After  commit: Session 2 saw '{results.get('after')}'")
    print("\nPostgres keeps both versions of the row (using xmin/xmax).")
    print("Session 2 sees the old one until Session 1 actually commits.")
    print("Readers never block writers and writers never block readers.")

    # put the row back the way we found it
    conn_reset = get_connection()
    cur_reset = conn_reset.cursor()
    cur_reset.execute(
        "UPDATE treatments SET outcome = %s WHERE treatment_id = %s",
        (original_outcome, treatment_id)
    )
    conn_reset.commit()
    cur_reset.close()
    conn_reset.close()

    input("\nPress Enter to go back to the menu...")


def locking_demo():
    print("\n" + "="*60)
    print("OPERATION 4: Row-Level Locking - SELECT FOR UPDATE")
    print("="*60)

    print("\nOne session locks a row, the other tries to update it.")
    print("\nFlow:")
    print("  Session 1 does SELECT FOR UPDATE and holds the lock 4s")
    print("  Session 2 tries to UPDATE the same row -> BLOCKED")
    print("  Session 1 COMMIT -> lock released")
    print("  Session 2 unblocks and completes")

    conn_temp = get_connection()
    cur = conn_temp.cursor()
    cur.execute("SELECT treatment_id FROM treatments LIMIT 1 OFFSET 1")
    treatment_id = cur.fetchone()[0]
    cur.close()
    conn_temp.close()

    print(f"\nTarget row: treatment_id = {treatment_id}")
    input("\nPress Enter to start the demo...")

    lock_acquired = threading.Event()

    def session1():
        conn = get_connection()
        conn.autocommit = False
        cur = conn.cursor()

        print("\n[Session 1] Locking row with SELECT FOR UPDATE...")
        cur.execute(
            "SELECT outcome FROM treatments WHERE treatment_id = %s FOR UPDATE",
            (treatment_id,)
        )
        lock_acquired.set()
        print("[Session 1] Row locked. Holding lock for 4 seconds...")

        time.sleep(4)

        cur.execute(
            "UPDATE treatments SET outcome = %s WHERE treatment_id = %s",
            ("Recovered", treatment_id)
        )
        conn.commit()
        print("[Session 1] COMMIT - lock released")

        cur.close()
        conn.close()

    def session2():
        lock_acquired.wait()
        time.sleep(0.3)

        conn = get_connection()
        conn.autocommit = False
        cur = conn.cursor()

        print(f"\n[Session 2] Trying to UPDATE treatment_id = {treatment_id}...")
        print("[Session 2] BLOCKED - waiting for Session 1 to release the lock")

        start = time.time()
        cur.execute(
            "UPDATE treatments SET outcome = %s WHERE treatment_id = %s",
            ("Stable", treatment_id)
        )
        waited = time.time() - start
        conn.commit()
        print(f"[Session 2] Unblocked. Update went through after waiting {waited:.1f} seconds")

        cur.close()
        conn.close()

    t1 = threading.Thread(target=session1)
    t2 = threading.Thread(target=session2)
    t1.start()
    time.sleep(0.2)
    t2.start()
    t1.join()
    t2.join()

    print("\n--- Summary ---")
    print("SELECT FOR UPDATE takes an exclusive lock on the row,")
    print("so any other UPDATE on the same row has to wait.")
    print("MVCC handles read/write, SELECT FOR UPDATE handles write/write.")

    input("\nPress Enter to go back to the menu...")


def monthly_summary(conn):
    print("\n" + "="*60)
    print("OPERATION 5: Monthly Diagnosis Summary")
    print("="*60)

    query = """
        SELECT
            DATE_TRUNC('month', e.encounter_date) AS month,
            d.diagnosis_code,
            COUNT(*) AS diagnosis_count
        FROM diagnoses d
        JOIN encounters e ON d.encounter_id = e.encounter_id
        GROUP BY 1, 2
        ORDER BY month DESC, diagnosis_count DESC
        LIMIT 15
    """

    print("\nMonthly report of diagnosis counts per code.")
    print("\nSQL:")
    print("    SELECT DATE_TRUNC('month', e.encounter_date) AS month,")
    print("           d.diagnosis_code, COUNT(*) AS diagnosis_count")
    print("    FROM diagnoses d")
    print("    JOIN encounters e ON d.encounter_id = e.encounter_id")
    print("    GROUP BY 1, 2")
    print("    ORDER BY month DESC, diagnosis_count DESC")
    print("    LIMIT 15")

    print("\n--- EXPLAIN ANALYZE ---")
    cur = conn.cursor()
    cur.execute("EXPLAIN (ANALYZE, BUFFERS) " + query)
    rows = cur.fetchall()
    for row in rows:
        print("   ", row[0])

    print("\nThe planner picks Hash Join + HashAggregate with Seq Scans on both tables.")
    print("The query touches every row, so an index would not help here.")
    print("This is the opposite of operations 1 and 2.")

    print("\n--- Results ---")
    cur2 = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur2.execute(query)
    results = cur2.fetchall()

    print(f"{'Month':<14} {'Code':<10} {'Count'}")
    print("-" * 35)
    for r in results:
        month_str = r['month'].strftime('%Y-%m') if r['month'] else 'N/A'
        print(f"{month_str:<14} {r['diagnosis_code']:<10} {r['diagnosis_count']}")

    cur.close()
    cur2.close()
    input("\nPress Enter to go back to the menu...")


def main():
    print("\nConnecting to PostgreSQL...")

    try:
        conn = get_connection()
        conn.autocommit = True
        print("Connected successfully!")
    except psycopg2.OperationalError as e:
        print(f"Error connecting to database: {e}")
        print("Make sure PostgreSQL is running and check config.py")
        return

    while True:
        print("\n" + "="*60)
        print("   CLINICAL DIAGNOSIS AND TREATMENT RECORDS SYSTEM")
        print("="*60)
        print("  1. Lookup diagnoses by code")
        print("  2. Patient encounter history")
        print("  3. Concurrent treatment update (MVCC)")
        print("  4. Row-level locking demo")
        print("  5. Monthly diagnosis summary")
        print("  0. Exit")
        print("="*60)

        choice = input("\nEnter choice: ").strip()

        if choice == "0":
            print("Goodbye!")
            break
        elif choice == "1":
            lookup_diagnosis_by_code(conn)
        elif choice == "2":
            get_encounter_history(conn)
        elif choice == "3":
            mvcc_demo()
        elif choice == "4":
            locking_demo()
        elif choice == "5":
            monthly_summary(conn)
        else:
            print("Invalid choice, please try again.")

    conn.close()


if __name__ == "__main__":
    main()
