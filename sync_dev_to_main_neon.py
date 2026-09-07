import psycopg2
from psycopg2 import extras

DEV_URL = "postgresql://neondb_owner:npg_WBjT5wU1lrzy@ep-shiny-snow-azpqiece-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
MAIN_URL = "postgresql://neondb_owner:npg_WBjT5wU1lrzy@ep-restless-haze-azsi5s6f-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

print("Connecting to Neon DEV (shiny-snow)...")
conn_dev = psycopg2.connect(DEV_URL)
cur_dev = conn_dev.cursor()

print("Connecting to Neon MAIN (restless-haze)...")
conn_main = psycopg2.connect(MAIN_URL)
cur_main = conn_main.cursor()

# Deletion order (children first)
delete_order = [
    "transactions",
    "accounts",
    "jv_entries",
    "journal_vouchers",
    "cash_book",
    "bank_book",
    "recurring_deposits",
    "sb_accounts",
    "customers",
    "chart_of_accounts",
]

# Insertion order (parents first)
insert_order = [
    ("chart_of_accounts", "account_code"),
    ("customers", "id"),
    ("sb_accounts", "account_no"),
    ("recurring_deposits", "rd_id"),
    ("cash_book", "id"),
    ("bank_book", "id"),
    ("journal_vouchers", "jv_id"),
    ("jv_entries", "entry_id"),
    ("accounts", "id"),
    ("transactions", "id"),
]

print("Clearing tables in Neon MAIN...")
for tbl in delete_order:
    try:
        cur_main.execute(f"DELETE FROM {tbl};")
        print(f"  Cleared {tbl}")
    except Exception as e:
        print(f"  Note clearing {tbl}: {e}")
conn_main.commit()

print("\nCopying records from Neon DEV to Neon MAIN...")
for tbl, pk in insert_order:
    print(f"\nProcessing {tbl}...")
    
    # Get columns
    cur_dev.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{tbl}' ORDER BY ordinal_position")
    dev_cols = [r[0] for r in cur_dev.fetchall()]
    
    cur_main.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{tbl}' ORDER BY ordinal_position")
    main_cols = set(r[0] for r in cur_main.fetchall())
    
    # Common columns
    common_cols = [c for c in dev_cols if c in main_cols]
    col_str = ", ".join(common_cols)
    placeholders = ", ".join(["%s"] * len(common_cols))
    
    # Fetch from DEV
    cur_dev.execute(f"SELECT {col_str} FROM {tbl}")
    rows = cur_dev.fetchall()
    print(f"  Fetched {len(rows)} rows from DEV")
    
    if rows:
        insert_query = f"INSERT INTO {tbl} ({col_str}) VALUES ({placeholders})"
        extras.execute_batch(cur_main, insert_query, rows, page_size=500)
        conn_main.commit()
        print(f"  Inserted {len(rows)} rows into MAIN")
        
        # Reset sequence if exists
        try:
            cur_main.execute(f"SELECT pg_get_serial_sequence('{tbl}', '{pk}')")
            seq_row = cur_main.fetchone()
            if seq_row and seq_row[0]:
                seq = seq_row[0]
                cur_main.execute(f"SELECT setval('{seq}', COALESCE((SELECT MAX({pk}) FROM {tbl}), 1))")
                conn_main.commit()
                print(f"  Reset sequence {seq}")
        except Exception as ex:
            print(f"  Sequence reset note: {ex}")

print("\n" + "="*50)
print("VERIFICATION ON NEON MAIN (restless-haze)")
print("="*50)
for tbl, _ in insert_order:
    cur_main.execute(f"SELECT COUNT(*) FROM {tbl}")
    cnt = cur_main.fetchone()[0]
    print(f"  {tbl:22} : {cnt:4d} rows")

cur_dev.close()
conn_dev.close()
cur_main.close()
conn_main.close()
print("\nNeon DEV -> Neon MAIN sync completed successfully!")
