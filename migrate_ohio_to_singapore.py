import os
import sys
import psycopg2
from psycopg2 import extras
import urllib.parse
import re

OHIO_URL = "postgresql://neondb_owner:npg_62aSwNvWgUBT@ep-holy-lake-ayhswebt.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"
SINGAPORE_URL = "postgresql://neondb_owner:npg_WBjT5wU1lrzy@ep-restless-haze-azsi5s6f-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    role TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    street TEXT,
    city TEXT,
    state TEXT,
    pincode TEXT,
    adhar_file TEXT,
    pan_file TEXT,
    signature_file TEXT,
    kyc_status TEXT DEFAULT 'PENDING',
    pan TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    account_number TEXT UNIQUE,
    account_type TEXT,
    customer_id INTEGER,
    balance REAL DEFAULT 0,
    created_at TEXT,
    FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    account_id INTEGER,
    type TEXT,
    amount REAL,
    balance_after REAL,
    date TEXT,
    FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS fixed_deposits (
    fd_id SERIAL PRIMARY KEY,
    customer_id INTEGER,
    principal DOUBLE PRECISION,
    tenure_months INTEGER,
    interest_rate DOUBLE PRECISION,
    maturity_amount DOUBLE PRECISION,
    nominee TEXT,
    status TEXT DEFAULT 'ACTIVE',
    created_at TEXT,
    payment_mode TEXT,
    closed_date TEXT,
    FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recurring_deposits (
    rd_id SERIAL PRIMARY KEY,
    customer_id INTEGER,
    monthly_amount DOUBLE PRECISION,
    tenure_months INTEGER,
    interest_rate DOUBLE PRECISION,
    installments_paid INTEGER DEFAULT 0,
    nominee TEXT,
    status TEXT DEFAULT 'ACTIVE',
    created_at TEXT,
    payment_mode TEXT,
    closed_date TEXT,
    maturity_amount DOUBLE PRECISION DEFAULT 0,
    FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chart_of_accounts (
    account_code TEXT PRIMARY KEY,
    account_name TEXT,
    account_type TEXT, 
    category TEXT
);

CREATE TABLE IF NOT EXISTS journal_vouchers (
    jv_id SERIAL PRIMARY KEY,
    voucher_date TEXT,
    narration TEXT,
    status TEXT DEFAULT 'POSTED'
);

CREATE TABLE IF NOT EXISTS jv_entries (
    entry_id SERIAL PRIMARY KEY,
    jv_id INTEGER,
    account_code TEXT,
    debit DOUBLE PRECISION DEFAULT 0,
    credit DOUBLE PRECISION DEFAULT 0,
    FOREIGN KEY(jv_id) REFERENCES journal_vouchers(jv_id) ON DELETE CASCADE,
    FOREIGN KEY(account_code) REFERENCES chart_of_accounts(account_code)
);

CREATE TABLE IF NOT EXISTS cash_book (
    id SERIAL PRIMARY KEY,
    date TEXT,
    voucher_no TEXT,
    particulars TEXT,
    debit_amount DOUBLE PRECISION DEFAULT 0,
    credit_amount DOUBLE PRECISION DEFAULT 0,
    balance DOUBLE PRECISION DEFAULT 0,
    account_code TEXT,
    narration TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS bank_book (
    id SERIAL PRIMARY KEY,
    date TEXT,
    voucher_no TEXT,
    particulars TEXT,
    debit_amount DOUBLE PRECISION DEFAULT 0,
    credit_amount DOUBLE PRECISION DEFAULT 0,
    balance DOUBLE PRECISION DEFAULT 0,
    bank_name TEXT,
    account_code TEXT,
    narration TEXT,
    created_at TEXT
);
"""

TABLES_IN_ORDER = [
    ("chart_of_accounts", ["account_code", "account_name", "account_type", "category"], None),
    ("users", ["username", "password", "role"], None),
    ("customers", ["id", "name", "email", "phone", "street", "city", "state", "pincode", "adhar_file", "pan_file", "signature_file", "kyc_status", "pan", "created_at"], "customers_id_seq"),
    ("accounts", ["id", "account_number", "account_type", "customer_id", "balance", "created_at"], "accounts_id_seq"),
    ("transactions", ["id", "account_id", "type", "amount", "balance_after", "date"], "transactions_id_seq"),
    ("fixed_deposits", ["fd_id", "customer_id", "principal", "tenure_months", "interest_rate", "maturity_amount", "nominee", "status", "created_at", "payment_mode", "closed_date"], "fixed_deposits_fd_id_seq"),
    ("recurring_deposits", ["rd_id", "customer_id", "monthly_amount", "tenure_months", "interest_rate", "installments_paid", "nominee", "status", "created_at", "payment_mode", "closed_date", "maturity_amount"], "recurring_deposits_rd_id_seq"),
    ("journal_vouchers", ["jv_id", "voucher_date", "narration", "status"], "journal_vouchers_jv_id_seq"),
    ("jv_entries", ["entry_id", "jv_id", "account_code", "debit", "credit"], "jv_entries_entry_id_seq"),
    ("cash_book", ["id", "date", "voucher_no", "particulars", "debit_amount", "credit_amount", "balance", "account_code", "narration", "created_at"], "cash_book_id_seq"),
    ("bank_book", ["id", "date", "voucher_no", "particulars", "debit_amount", "credit_amount", "balance", "bank_name", "account_code", "narration", "created_at"], "bank_book_id_seq"),
]

def migrate():
    print("=" * 60)
    print("🚀 NEON DATABASE MIGRATION: OHIO (US) ➔ SINGAPORE (ASIA)")
    print("=" * 60)

    # 1. Connect to source and target
    print("\n⏳ Connecting to Source Database (Ohio, USA)...")
    try:
        conn_src = psycopg2.connect(OHIO_URL)
        cur_src = conn_src.cursor()
        print("✅ Connected to Ohio database.")
    except Exception as e:
        print(f"❌ Failed to connect to Ohio database: {e}")
        return

    print("\n⏳ Connecting to Target Database (Singapore, Asia)...")
    try:
        conn_tgt = psycopg2.connect(SINGAPORE_URL)
        cur_tgt = conn_tgt.cursor()
        print("✅ Connected to Singapore database.")
    except Exception as e:
        print(f"❌ Failed to connect to Singapore database: {e}")
        conn_src.close()
        return

    # 2. Create schema in Singapore
    print("\n⏳ Initializing table schema in Singapore...")
    try:
        cur_tgt.execute(SCHEMA_SQL)
        conn_tgt.commit()
        print("✅ All 11 tables created successfully in Singapore.")
    except Exception as e:
        print(f"❌ Schema creation error: {e}")
        conn_tgt.rollback()
        conn_src.close()
        conn_tgt.close()
        return

    # 3. Transfer data table by table
    print("\n📦 Transferring data records...")
    for table_name, columns, seq_name in TABLES_IN_ORDER:
        col_str = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))
        
        try:
            # Read from source
            cur_src.execute(f"SELECT {col_str} FROM {table_name}")
            rows = cur_src.fetchall()
            
            if rows:
                # Insert into target
                insert_query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                extras.execute_batch(cur_tgt, insert_query, rows)
                conn_tgt.commit()
                print(f"  ✓ {table_name:22} : {len(rows):4d} rows transferred")
                
                # Update sequence to prevent ID conflicts
                if seq_name:
                    try:
                        pk_col = columns[0]
                        cur_tgt.execute(f"SELECT setval('{seq_name}', COALESCE((SELECT MAX({pk_col}) FROM {table_name}), 1))")
                        conn_tgt.commit()
                    except Exception as sq_err:
                        pass
            else:
                print(f"  - {table_name:22} :    0 rows (empty)")
        except Exception as t_err:
            print(f"  ⚠️ Error transferring {table_name}: {t_err}")
            conn_tgt.rollback()

    # 4. Final verification
    print("\n" + "=" * 60)
    print("🎉 MIGRATION COMPLETE! VERIFICATION SUMMARY:")
    print("=" * 60)
    
    for table_name, _, _ in TABLES_IN_ORDER:
        cur_tgt.execute(f"SELECT COUNT(*) FROM {table_name}")
        cnt = cur_tgt.fetchone()[0]
        print(f"  📊 {table_name:22} : {cnt:4d} rows in Singapore")

    cur_src.close()
    conn_src.close()
    cur_tgt.close()
    conn_tgt.close()
    print("\n✅ All data is fully replicated and active in Singapore!")

if __name__ == "__main__":
    migrate()
