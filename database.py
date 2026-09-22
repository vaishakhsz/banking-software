import os
import sys
import sqlite3
import time
import re
import urllib.parse
from datetime import datetime, date, timezone, timedelta
import pytz
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Load local environment variables
load_dotenv()

# Define IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

DB_NAME = "aasha_nidhi.db"
UPLOAD_DIR = "customer_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ----------------------------------------------------
# SUPABASE / POSTGRESQL CREDENTIALS & PARSING
# ----------------------------------------------------
supabase_url = None
supabase_proj_url = None
supabase_anon_key = None

try:
    import streamlit as st
    secrets_obj = getattr(st, "secrets", None)
    if secrets_obj is not None:
        try:
            if "SUPABASE_URL" in secrets_obj:
                supabase_url = secrets_obj["SUPABASE_URL"]
            elif "DATABASE_URL" in secrets_obj:
                supabase_url = secrets_obj["DATABASE_URL"]
            elif "postgres_url" in secrets_obj:
                supabase_url = secrets_obj["postgres_url"]
            elif "POSTGRES_URL" in secrets_obj:
                supabase_url = secrets_obj["POSTGRES_URL"]
            
            if not supabase_url and "connections" in secrets_obj and "supabase" in secrets_obj["connections"]:
                sub = secrets_obj["connections"]["supabase"]
                if isinstance(sub, dict) and "url" in sub:
                    supabase_url = sub["url"]
        except (Exception, BaseException):
            pass
except (Exception, BaseException):
    pass

DEFAULT_DB_URL = "postgresql://neondb_owner:npg_WBjT5wU1lrzy@ep-restless-haze-azsi5s6f-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

if not supabase_url:
    supabase_url = os.getenv("SUPABASE_URL") or os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or DEFAULT_DB_URL

USING_SUPABASE = False
SUPABASE_CONN_PARAMS = {}
SUPABASE_URL = ""

def parse_postgres_conn_info(raw_url):
    """
    Safely parses PostgreSQL connection string and returns parameter dict
    to avoid URI parsing issues with special characters in passwords.
    """
    if not raw_url:
        return None
    
    if not (raw_url.startswith("postgresql://") or raw_url.startswith("postgres://")):
        return None

    try:
        pattern = r'^(?:postgresql|postgres):\/\/(?:([^:]+):?(.*)@)?([^:\/\?]+)(?::(\d+))?(?:\/([^?]*))?(?:\?(.*))?$'
        match = re.match(pattern, raw_url)
        
        if match:
            user = match.group(1) or "postgres"
            password = match.group(2) or ""
            host = match.group(3)
            port = int(match.group(4)) if match.group(4) else 5432
            dbname = match.group(5) or "postgres"
            
            user = urllib.parse.unquote(user)
            password = urllib.parse.unquote(password)
            
            return {
                "host": host,
                "port": port,
                "user": user,
                "password": password,
                "dbname": dbname,
                "sslmode": "require",
                "connect_timeout": 15,
                "keepalives": 1,
                "keepalives_idle": 10,
                "keepalives_interval": 5,
                "keepalives_count": 3
            }
    except Exception as e:
        print(f"⚠️ Error parsing connection string: {e}")
    
    return None

if supabase_url and "REPLACE_WITH_YOUR_DB_PASSWORD" not in supabase_url:
    parsed_params = parse_postgres_conn_info(supabase_url)
    if parsed_params:
        USING_SUPABASE = True
        SUPABASE_URL = supabase_url
        SUPABASE_CONN_PARAMS = parsed_params

# ----------------------------------------------------
# DIRECT DATABASE DOCUMENT STORAGE (BYTEA)
# (All customer documents are stored directly in PostgreSQL)
# ----------------------------------------------------

# ----------------------------------------------------
# HIGH-SPEED PERSISTENT CONNECTION POOLING
# ----------------------------------------------------
DB_INITIALIZED = False
DB_INIT_ERROR = None
_pg_pool = None

def reset_pg_pool():
    """Closes all connections in pool and resets it to force fresh connections"""
    global _pg_pool
    if _pg_pool is not None:
        try:
            if not _pg_pool.closed:
                _pg_pool.closeall()
        except Exception:
            pass
    _pg_pool = None

def get_pg_pool():
    """Initializes and returns a persistent PostgreSQL connection pool"""
    global _pg_pool
    if _pg_pool is None or _pg_pool.closed:
        import psycopg2
        from psycopg2 import pool
        params = dict(SUPABASE_CONN_PARAMS)
        _pg_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            **params
        )
    return _pg_pool

def get_connection(retries=3):
    """Get database connection from persistent pool with sub-millisecond response"""
    if USING_SUPABASE:
        for attempt in range(retries):
            try:
                p = get_pg_pool()
                conn = p.getconn()
                if conn.closed != 0:
                    try:
                        p.putconn(conn, close=True)
                    except Exception:
                        pass
                    reset_pg_pool()
                    continue
                conn.autocommit = False
                return conn
            except Exception:
                reset_pg_pool()
                time.sleep(0.1 * (attempt + 1))
                
        # Direct fallback
        import psycopg2
        params = dict(SUPABASE_CONN_PARAMS)
        direct_conn = psycopg2.connect(**params)
        direct_conn.autocommit = False
        return direct_conn
    else:
        db_dir = os.path.dirname(DB_NAME)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        return sqlite3.connect(DB_NAME, check_same_thread=False, timeout=10)

def release_connection(conn, is_broken=False):
    """Safely return connection back to pool for instant reuse or close if broken"""
    if conn is not None:
        if USING_SUPABASE and _pg_pool is not None and not _pg_pool.closed:
            try:
                _pg_pool.putconn(conn, close=is_broken)
                return
            except Exception:
                pass
        try:
            conn.close()
        except Exception:
            pass

def translate_sqlite_schema_to_postgres(sql):
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    sql = sql.replace("INTEGER PRIMARY KEY", "SERIAL PRIMARY KEY")
    sql = sql.replace("REAL", "DOUBLE PRECISION")
    sql = sql.replace("BLOB", "BYTEA")
    return sql

def execute_create(cursor, sql):
    if USING_SUPABASE:
        sql = translate_sqlite_schema_to_postgres(sql)
    cursor.execute(sql)

def resequence_all_accounts():
    """Resequence all account codes in chart_of_accounts to be strictly sequential (101, 102, 103...)"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        placeholder = "%s" if USING_SUPABASE else "?"
        
        cursor.execute("SELECT account_code, account_name, account_type, category FROM chart_of_accounts")
        rows = cursor.fetchall()
        if not rows:
            release_connection(conn)
            return
            
        by_type = {}
        for row in rows:
            code, name, acc_type, cat = row
            by_type.setdefault(acc_type, []).append((code, name, cat))
            
        prefix_map = {
            "Asset": "AST",
            "Liability": "LIA",
            "Income": "INC",
            "Expense": "EXP",
            "Equity": "EQT"
        }
        
        updates_to_make = []
        for acc_type, acc_list in by_type.items():
            prefix = prefix_map.get(acc_type, "ACC")
            
            def get_sort_key(item):
                code = item[0]
                try:
                    parts = code.split("-")
                    suffix = int(parts[1]) if len(parts) > 1 else 9999
                except Exception:
                    suffix = 9999
                return (suffix, item[1])
                
            acc_list.sort(key=get_sort_key)
            
            for index, (old_code, name, cat) in enumerate(acc_list):
                new_code = f"{prefix}-{101 + index}"
                if old_code != new_code:
                    updates_to_make.append((old_code, new_code, name, acc_type, cat))
                    
        if not updates_to_make:
            release_connection(conn)
            return
            
        try:
            if not USING_SUPABASE:
                cursor.execute("PRAGMA foreign_keys = OFF;")
                
            for old_code, new_code, name, acc_type, cat in updates_to_make:
                cursor.execute(f"UPDATE jv_entries SET account_code = {placeholder} WHERE account_code = {placeholder}", (new_code, old_code))
                cursor.execute(f"UPDATE cash_book SET account_code = {placeholder} WHERE account_code = {placeholder}", (new_code, old_code))
                cursor.execute(f"UPDATE bank_book SET account_code = {placeholder} WHERE account_code = {placeholder}", (new_code, old_code))
                
                cursor.execute(f"SELECT account_name FROM chart_of_accounts WHERE account_code = {placeholder}", (new_code,))
                new_row = cursor.fetchone()
                
                if new_row:
                    cursor.execute(f"UPDATE chart_of_accounts SET account_name = {placeholder}, category = {placeholder} WHERE account_code = {placeholder}", (name, cat, new_code))
                    cursor.execute(f"DELETE FROM chart_of_accounts WHERE account_code = {placeholder}", (old_code,))
                else:
                    cursor.execute(f"INSERT INTO chart_of_accounts (account_code, account_name, account_type, category) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})", (new_code, name, acc_type, cat))
                    cursor.execute(f"DELETE FROM chart_of_accounts WHERE account_code = {placeholder}", (old_code,))
                    
            conn.commit()
            print("✅ Resequenced all accounts successfully!")
        finally:
            try:
                if not USING_SUPABASE:
                    cursor.execute("PRAGMA foreign_keys = ON;")
                conn.commit()
            except Exception as ex:
                print(f"Error restoring foreign keys: {str(ex)}")
                
    except Exception as e:
        import traceback
        print(f"Error during re-sequencing: {str(e)}")
        traceback.print_exc()
    finally:
        release_connection(conn)


def reconcile_books():
    """One-time database reconciliation to align old cash/bank entries with ledger JVs"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        placeholder = "%s" if USING_SUPABASE else "?"
        
        cursor.execute("SELECT id, date, voucher_no, particulars, debit_amount, credit_amount, account_code, narration FROM cash_book")
        cash_rows = cursor.fetchall()
        for row in cash_rows:
            c_id, c_date, v_no, part, dr, cr, acc_code, narr = row
            amt = dr if dr > 0 else cr
            is_dr = dr > 0
            
            cursor.execute(f"SELECT jv_id, narration FROM journal_vouchers WHERE narration LIKE {placeholder} OR (narration LIKE {placeholder} AND jv_id IN (SELECT jv_id FROM jv_entries WHERE debit = {placeholder} OR credit = {placeholder}))", (f"%{v_no}%", f"%{part}%", amt, amt))
            jv_row = cursor.fetchone()
            if jv_row:
                jv_id, jv_narr = jv_row
                jv_prefix = "Cash Receipt" if is_dr else "Cash Payment"
                full_narr = part
                if narr and narr.strip():
                    full_narr += f" ({narr.strip()})"
                new_narr = f"{jv_prefix} [{v_no}]: {full_narr}"
                cursor.execute(f"UPDATE journal_vouchers SET narration = {placeholder} WHERE jv_id = {placeholder}", (new_narr, jv_id))
                
                cursor.execute(f"DELETE FROM jv_entries WHERE jv_id = {placeholder}", (jv_id,))
                if is_dr:
                    cursor.execute(f"INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES ({placeholder}, 'AST-101', {placeholder}, 0)", (jv_id, amt))
                    cursor.execute(f"INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES ({placeholder}, {placeholder}, 0, {placeholder})", (jv_id, acc_code, amt))
                else:
                    cursor.execute(f"INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES ({placeholder}, {placeholder}, {placeholder}, 0)", (jv_id, acc_code, amt))
                    cursor.execute(f"INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES ({placeholder}, 'AST-101', 0, {placeholder})", (jv_id, amt))
                    
        cursor.execute("SELECT id, date, voucher_no, particulars, debit_amount, credit_amount, bank_name, account_code, narration FROM bank_book")
        bank_rows = cursor.fetchall()
        for row in bank_rows:
            b_id, b_date, v_no, part, dr, cr, b_name, acc_code, narr = row
            amt = dr if dr > 0 else cr
            is_dr = dr > 0
            bank_code = "AST-102" if "Union" in b_name else "AST-103"
            
            cursor.execute(f"SELECT jv_id, narration FROM journal_vouchers WHERE narration LIKE {placeholder} OR (narration LIKE {placeholder} AND jv_id IN (SELECT jv_id FROM jv_entries WHERE debit = {placeholder} OR credit = {placeholder}))", (f"%{v_no}%", f"%{part}%", amt, amt))
            jv_row = cursor.fetchone()
            if jv_row:
                jv_id, jv_narr = jv_row
                jv_prefix = "Bank Deposit" if is_dr else "Bank Withdrawal"
                full_narr = part
                if narr and narr.strip():
                    full_narr += f" ({narr.strip()})"
                new_narr = f"{jv_prefix} [{v_no}]: {full_narr} - {b_name}"
                cursor.execute(f"UPDATE journal_vouchers SET narration = {placeholder} WHERE jv_id = {placeholder}", (new_narr, jv_id))
                
                cursor.execute(f"DELETE FROM jv_entries WHERE jv_id = {placeholder}", (jv_id,))
                if is_dr:
                    cursor.execute(f"INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES ({placeholder}, {placeholder}, {placeholder}, 0)", (jv_id, bank_code, amt))
                    cursor.execute(f"INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES ({placeholder}, {placeholder}, 0, {placeholder})", (jv_id, acc_code, amt))
                else:
                    cursor.execute(f"INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES ({placeholder}, {placeholder}, {placeholder}, 0)", (jv_id, acc_code, amt))
                    cursor.execute(f"INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES ({placeholder}, {placeholder}, 0, {placeholder})", (jv_id, bank_code, amt))
                    
        conn.commit()
    except Exception as e:
        print(f"Error during reconciliation: {str(e)}")
    finally:
        release_connection(conn)


SCHEMA_VERSION = 4

def init_db(force=False):
    """Initialize database tables lazily on first query execution with sub-millisecond fast-path check"""
    global DB_INITIALIZED, DB_INIT_ERROR
    if DB_INITIALIZED and not force:
        return True
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if not USING_SUPABASE:
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("CREATE TABLE IF NOT EXISTS _schema_init_tracker (id INTEGER PRIMARY KEY, version INTEGER NOT NULL, updated_at TEXT)")
            if not force:
                cursor.execute("SELECT version FROM _schema_init_tracker WHERE id = 1")
                row = cursor.fetchone()
                if row and row[0] >= SCHEMA_VERSION:
                    DB_INITIALIZED = True
                    DB_INIT_ERROR = None
                    return True
        else:
            if not force:
                try:
                    cursor.execute("SELECT version FROM _schema_init_tracker WHERE id = 1")
                    row = cursor.fetchone()
                    if row and row[0] >= SCHEMA_VERSION:
                        DB_INITIALIZED = True
                        DB_INIT_ERROR = None
                        return True
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
        
        # Combined DDL statements for rapid 1-roundtrip schema execution
        tables_sql = """
            CREATE TABLE IF NOT EXISTS _schema_init_tracker (
                id INTEGER PRIMARY KEY,
                version INTEGER NOT NULL,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dob TEXT,
                gender TEXT,
                email TEXT,
                phone TEXT,
                account_type TEXT,
                street TEXT,
                city TEXT,
                state TEXT,
                pincode TEXT,
                pan TEXT,
                adhar TEXT,
                adhar_file TEXT,
                adhar_data BLOB,
                pan_file TEXT,
                pan_data BLOB,
                signature_file TEXT,
                signature_data BLOB,
                kyc_status TEXT DEFAULT 'PENDING',
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_number TEXT,
                account_type TEXT,
                customer_id INTEGER,
                balance REAL DEFAULT 0.0,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS sb_accounts (
                account_no TEXT PRIMARY KEY,
                customer_id INTEGER,
                balance REAL DEFAULT 0.0,
                interest_rate REAL DEFAULT 3.5,
                created_at TEXT,
                FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_id TEXT,
                account_no TEXT,
                type TEXT,
                amount REAL,
                mode TEXT,
                narration TEXT,
                balance_after REAL,
                account_id INTEGER,
                date TEXT
            );
            CREATE TABLE IF NOT EXISTS fixed_deposits (
                fd_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                principal REAL,
                tenure_months INTEGER,
                interest_rate REAL,
                maturity_amount REAL,
                nominee TEXT,
                status TEXT DEFAULT 'ACTIVE',
                created_at TEXT,
                payment_mode TEXT,
                closed_date TEXT,
                FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS recurring_deposits (
                rd_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                scheme_name TEXT DEFAULT 'SWAYAMVARA KSHEMANIDHI',
                rd_no TEXT,
                monthly_amount REAL,
                tenure_months INTEGER,
                interest_rate REAL,
                installments_paid INTEGER DEFAULT 0,
                nominee TEXT,
                status TEXT DEFAULT 'ACTIVE',
                created_at TEXT,
                payment_mode TEXT,
                maturity_date TEXT,
                closed_date TEXT,
                maturity_amount REAL DEFAULT 0,
                collected_balance REAL DEFAULT 0,
                FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS chart_of_accounts (
                account_code TEXT PRIMARY KEY,
                account_name TEXT,
                account_type TEXT, 
                category TEXT
            );
            CREATE TABLE IF NOT EXISTS journal_vouchers (
                jv_id INTEGER PRIMARY KEY AUTOINCREMENT,
                voucher_date TEXT,
                narration TEXT,
                status TEXT DEFAULT 'POSTED'
            );
            CREATE TABLE IF NOT EXISTS jv_entries (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                jv_id INTEGER,
                account_code TEXT,
                debit REAL DEFAULT 0,
                credit REAL DEFAULT 0,
                FOREIGN KEY(jv_id) REFERENCES journal_vouchers(jv_id) ON DELETE CASCADE,
                FOREIGN KEY(account_code) REFERENCES chart_of_accounts(account_code)
            );
            CREATE TABLE IF NOT EXISTS cash_book (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                voucher_no TEXT,
                particulars TEXT,
                debit_amount REAL DEFAULT 0,
                credit_amount REAL DEFAULT 0,
                balance REAL DEFAULT 0,
                account_code TEXT,
                narration TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS bank_book (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                voucher_no TEXT,
                particulars TEXT,
                debit_amount REAL DEFAULT 0,
                credit_amount REAL DEFAULT 0,
                balance REAL DEFAULT 0,
                bank_name TEXT,
                account_code TEXT,
                narration TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS personal_loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_no TEXT,
                customer_id INTEGER,
                sanction_date TEXT,
                principal_amount REAL,
                interest_rate REAL,
                interest_type TEXT,
                tenure_days INTEGER,
                tenure_months INTEGER,
                total_interest REAL,
                total_repayable REAL,
                installment_amount REAL,
                outstanding_due REAL,
                disbursal_mode TEXT,
                voucher_no TEXT,
                guarantor_name TEXT,
                guarantor_phone TEXT,
                purpose TEXT,
                status TEXT,
                remarks TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS gold_loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_no TEXT,
                customer_id INTEGER,
                sanction_date TEXT,
                principal_amount REAL,
                interest_rate REAL,
                tenure_days INTEGER DEFAULT 365,
                tenure_months INTEGER,
                total_interest REAL,
                total_repayable REAL,
                monthly_interest REAL,
                outstanding_due REAL,
                disbursal_mode TEXT,
                voucher_no TEXT,
                gold_weight_gross REAL,
                gold_weight_net REAL,
                gold_purity TEXT,
                gold_items_description TEXT,
                status TEXT,
                remarks TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS loan_repayments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_type TEXT,
                loan_id INTEGER,
                customer_id INTEGER,
                payment_date TEXT,
                amount_paid REAL,
                principal_component REAL,
                interest_component REAL,
                payment_mode TEXT,
                voucher_no TEXT,
                narration TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS loan_emi_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_type TEXT,
                loan_id INTEGER,
                loan_no TEXT,
                emi_number INTEGER,
                from_date TEXT,
                to_date TEXT,
                due_date TEXT,
                principal_component REAL DEFAULT 0,
                interest_component REAL DEFAULT 0,
                emi_amount REAL DEFAULT 0,
                paid_amount REAL DEFAULT 0,
                paid_date TEXT,
                status TEXT DEFAULT 'PENDING',
                created_at TEXT
            );
        """
        
        if USING_SUPABASE:
            tables_sql = translate_sqlite_schema_to_postgres(tables_sql)
            cursor.execute(tables_sql)
            try:
                cursor.execute("""
                    ALTER TABLE customers ADD COLUMN IF NOT EXISTS dob TEXT;
                    ALTER TABLE customers ADD COLUMN IF NOT EXISTS gender TEXT;
                    ALTER TABLE customers ADD COLUMN IF NOT EXISTS adhar TEXT;
                    ALTER TABLE customers ADD COLUMN IF NOT EXISTS adhar_data BYTEA;
                    ALTER TABLE customers ADD COLUMN IF NOT EXISTS pan_data BYTEA;
                    ALTER TABLE customers ADD COLUMN IF NOT EXISTS signature_data BYTEA;
                    ALTER TABLE customers ADD COLUMN IF NOT EXISTS account_no TEXT;
                    ALTER TABLE customers ADD COLUMN IF NOT EXISTS account_type TEXT;
                    ALTER TABLE accounts ADD COLUMN IF NOT EXISTS account_number TEXT;
                    ALTER TABLE accounts ADD COLUMN IF NOT EXISTS account_type TEXT;
                    ALTER TABLE accounts ADD COLUMN IF NOT EXISTS customer_id INTEGER;
                    ALTER TABLE accounts ADD COLUMN IF NOT EXISTS balance REAL DEFAULT 0.0;
                    ALTER TABLE accounts ADD COLUMN IF NOT EXISTS created_at TEXT;
                    ALTER TABLE sb_accounts ADD COLUMN IF NOT EXISTS account_no TEXT;
                    ALTER TABLE sb_accounts ADD COLUMN IF NOT EXISTS customer_id INTEGER;
                    ALTER TABLE sb_accounts ADD COLUMN IF NOT EXISTS balance REAL DEFAULT 0.0;
                    ALTER TABLE sb_accounts ADD COLUMN IF NOT EXISTS interest_rate REAL DEFAULT 3.5;
                    ALTER TABLE sb_accounts ADD COLUMN IF NOT EXISTS created_at TEXT;
                    ALTER TABLE transactions ADD COLUMN IF NOT EXISTS tx_id TEXT;
                    ALTER TABLE transactions ADD COLUMN IF NOT EXISTS account_no TEXT;
                    ALTER TABLE transactions ADD COLUMN IF NOT EXISTS mode TEXT;
                    ALTER TABLE transactions ADD COLUMN IF NOT EXISTS narration TEXT;
                    ALTER TABLE transactions ADD COLUMN IF NOT EXISTS balance_after REAL;
                    ALTER TABLE transactions ADD COLUMN IF NOT EXISTS account_id INTEGER;
                    ALTER TABLE transactions ADD COLUMN IF NOT EXISTS created_at TEXT;
                    ALTER TABLE recurring_deposits ADD COLUMN IF NOT EXISTS scheme_name TEXT;
                    ALTER TABLE recurring_deposits ADD COLUMN IF NOT EXISTS rd_no TEXT;
                    ALTER TABLE recurring_deposits ADD COLUMN IF NOT EXISTS maturity_date TEXT;
                    ALTER TABLE recurring_deposits ADD COLUMN IF NOT EXISTS collected_balance DOUBLE PRECISION DEFAULT 0;
                    ALTER TABLE personal_loans ADD COLUMN IF NOT EXISTS renewal_count INTEGER DEFAULT 0;
                    ALTER TABLE personal_loans ADD COLUMN IF NOT EXISTS last_renewal_date TEXT;
                    ALTER TABLE personal_loans ADD COLUMN IF NOT EXISTS guarantor_relation TEXT;
                    ALTER TABLE personal_loans ADD COLUMN IF NOT EXISTS guarantor_address TEXT;
                    ALTER TABLE personal_loans ADD COLUMN IF NOT EXISTS loan_from_date TEXT;
                    ALTER TABLE personal_loans ADD COLUMN IF NOT EXISTS loan_to_date TEXT;
                    ALTER TABLE personal_loans ADD COLUMN IF NOT EXISTS first_emi_due TEXT;
                    ALTER TABLE personal_loans ADD COLUMN IF NOT EXISTS last_emi_due TEXT;
                    ALTER TABLE personal_loans ADD COLUMN IF NOT EXISTS monthly_principal_emi DOUBLE PRECISION DEFAULT 0;
                    ALTER TABLE personal_loans ADD COLUMN IF NOT EXISTS monthly_interest_emi DOUBLE PRECISION DEFAULT 0;
                    ALTER TABLE personal_loans ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS renewal_count INTEGER DEFAULT 0;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS last_renewal_date TEXT;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS vault_packet_no TEXT;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS gold_rate_per_gram DOUBLE PRECISION DEFAULT 6500;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS ornament_details TEXT;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS item_count INTEGER DEFAULT 1;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS stone_deduction DOUBLE PRECISION DEFAULT 0;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS purity TEXT DEFAULT '22K';
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS market_value DOUBLE PRECISION DEFAULT 0;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS ltv_percent DOUBLE PRECISION DEFAULT 75;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS interest_rate_monthly DOUBLE PRECISION DEFAULT 1.0;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS monthly_interest_due DOUBLE PRECISION DEFAULT 0;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS outstanding_due DOUBLE PRECISION DEFAULT 0;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS closure_date TEXT;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS loan_from_date TEXT;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS loan_to_date TEXT;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS first_emi_due TEXT;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS last_emi_due TEXT;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS monthly_principal_emi DOUBLE PRECISION DEFAULT 0;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS monthly_interest_emi DOUBLE PRECISION DEFAULT 0;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS installment_amount DOUBLE PRECISION DEFAULT 0;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS interest_rate DOUBLE PRECISION DEFAULT 12.0;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS total_interest DOUBLE PRECISION DEFAULT 0;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS total_repayable DOUBLE PRECISION DEFAULT 0;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS tenure_days INTEGER DEFAULT 365;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS gold_image_file TEXT;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS gold_image_name TEXT;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS gold_image_data BYTEA;
                    ALTER TABLE gold_loans ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                    
                    -- HIGH-PERFORMANCE POSTGRESQL B-TREE INDEXES FOR SUB-MILLISECOND LOOKUPS & AGGREGATIONS
                    CREATE INDEX IF NOT EXISTS idx_customers_acc_no ON customers(account_no);
                    CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
                    CREATE INDEX IF NOT EXISTS idx_sb_accounts_cust_id ON sb_accounts(customer_id);
                    CREATE INDEX IF NOT EXISTS idx_fixed_deposits_cust_id ON fixed_deposits(customer_id);
                    CREATE INDEX IF NOT EXISTS idx_fixed_deposits_status ON fixed_deposits(status);
                    CREATE INDEX IF NOT EXISTS idx_recurring_deposits_cust_id ON recurring_deposits(customer_id);
                    CREATE INDEX IF NOT EXISTS idx_recurring_deposits_status ON recurring_deposits(status);
                    CREATE INDEX IF NOT EXISTS idx_personal_loans_cust_id ON personal_loans(customer_id);
                    CREATE INDEX IF NOT EXISTS idx_personal_loans_loan_no ON personal_loans(loan_no);
                    CREATE INDEX IF NOT EXISTS idx_personal_loans_status ON personal_loans(status);
                    CREATE INDEX IF NOT EXISTS idx_gold_loans_cust_id ON gold_loans(customer_id);
                    CREATE INDEX IF NOT EXISTS idx_gold_loans_loan_no ON gold_loans(loan_no);
                    CREATE INDEX IF NOT EXISTS idx_gold_loans_status ON gold_loans(status);
                    CREATE INDEX IF NOT EXISTS idx_loan_repayments_type_id ON loan_repayments(loan_type, loan_id);
                    CREATE INDEX IF NOT EXISTS idx_loan_emi_schedules_type_id ON loan_emi_schedules(loan_type, loan_id);
                    CREATE INDEX IF NOT EXISTS idx_jv_entries_acc_code ON jv_entries(account_code);
                    CREATE INDEX IF NOT EXISTS idx_jv_entries_jv_id ON jv_entries(jv_id);
                    CREATE INDEX IF NOT EXISTS idx_journal_vouchers_date ON journal_vouchers(voucher_date);
                    CREATE INDEX IF NOT EXISTS idx_cash_book_date ON cash_book(date);
                    CREATE INDEX IF NOT EXISTS idx_cash_book_vno ON cash_book(voucher_no);
                    CREATE INDEX IF NOT EXISTS idx_cash_book_acccode ON cash_book(account_code);
                    CREATE INDEX IF NOT EXISTS idx_bank_book_date ON bank_book(date);
                    CREATE INDEX IF NOT EXISTS idx_bank_book_vno ON bank_book(voucher_no);
                    CREATE INDEX IF NOT EXISTS idx_bank_book_bname ON bank_book(bank_name);
                    CREATE INDEX IF NOT EXISTS idx_transactions_acc_no ON transactions(account_no);
                    CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
                    
                    DO $$ 
                    BEGIN
                        BEGIN
                            ALTER TABLE gold_loans ALTER COLUMN monthly_interest_rate DROP NOT NULL;
                        EXCEPTION WHEN OTHERS THEN NULL;
                        END;
                        BEGIN
                            ALTER TABLE gold_loans ALTER COLUMN outstanding_principal DROP NOT NULL;
                        EXCEPTION WHEN OTHERS THEN NULL;
                        END;
                        BEGIN
                            ALTER TABLE gold_loans ALTER COLUMN appraised_value DROP NOT NULL;
                        EXCEPTION WHEN OTHERS THEN NULL;
                        END;
                    END $$;
                """)
            except Exception:
                pass
        else:
            cursor.executescript(tables_sql)
            for col in [("dob", "TEXT"), ("gender", "TEXT"), ("adhar", "TEXT"), ("account_no", "TEXT"), ("account_type", "TEXT"), ("adhar_data", "BLOB"), ("pan_data", "BLOB"), ("signature_data", "BLOB")]:
                try:
                    cursor.execute(f"ALTER TABLE customers ADD COLUMN {col[0]} {col[1]};")
                except Exception:
                    pass
            for col in [("tx_id", "TEXT"), ("account_no", "TEXT"), ("mode", "TEXT"), ("narration", "TEXT"), ("balance_after", "REAL"), ("account_id", "INTEGER"), ("created_at", "TEXT")]:
                try:
                    cursor.execute(f"ALTER TABLE transactions ADD COLUMN {col[0]} {col[1]};")
                except Exception:
                    pass
            for col in [("scheme_name", "TEXT"), ("rd_no", "TEXT"), ("maturity_date", "TEXT"), ("collected_balance", "REAL")]:
                try:
                    cursor.execute(f"ALTER TABLE recurring_deposits ADD COLUMN {col[0]} {col[1]};")
                except Exception:
                    pass
            for col in [
                ("renewal_count", "INTEGER DEFAULT 0"),
                ("last_renewal_date", "TEXT"),
                ("guarantor_relation", "TEXT"),
                ("guarantor_address", "TEXT"),
                ("loan_from_date", "TEXT"),
                ("loan_to_date", "TEXT"),
                ("first_emi_due", "TEXT"),
                ("last_emi_due", "TEXT"),
                ("monthly_principal_emi", "REAL DEFAULT 0"),
                ("monthly_interest_emi", "REAL DEFAULT 0"),
                ("installment_amount", "REAL DEFAULT 0"),
                ("interest_rate", "REAL DEFAULT 12.0"),
                ("total_interest", "REAL DEFAULT 0"),
                ("total_repayable", "REAL DEFAULT 0"),
                ("tenure_days", "INTEGER DEFAULT 365"),
                ("gold_image_name", "TEXT"),
                ("gold_image_data", "BLOB")
            ]:
                try:
                    cursor.execute(f"ALTER TABLE personal_loans ADD COLUMN {col[0]} {col[1]};")
                except Exception:
                    pass
                try:
                    cursor.execute(f"ALTER TABLE gold_loans ADD COLUMN {col[0]} {col[1]};")
                except Exception:
                    pass

        default_accounts = [
            ("INC-101", "Loan Interest Income", "Income", "Primary Revenue"),
            ("INC-102", "Investment Income", "Income", "Primary Revenue"),
            ("INC-103", "Processing Fees", "Income", "Service Income"),
            ("INC-104", "Service Charges", "Income", "Service Income"),
            ("INC-105", "Commission Income", "Income", "Service Income"),
            ("INC-106", "Transaction Fees", "Income", "Service Income"),
            ("INC-107", "Miscellaneous Income", "Income", "Other Income"),
            ("EXP-101", "SB Interest Paid", "Expense", "Cost of Funds"),
            ("EXP-102", "FD Interest Paid", "Expense", "Cost of Funds"),
            ("EXP-103", "RD Interest Paid", "Expense", "Cost of Funds"),
            ("EXP-104", "Salaries & Benefits", "Expense", "Operating Expenses"),
            ("EXP-105", "Rent & Utilities", "Expense", "Operating Expenses"),
            ("EXP-106", "Electricity Charges", "Expense", "Operating Expenses"),
            ("EXP-107", "Depreciation 5%", "Expense", "Operating Expenses"),
            ("EXP-108", "Depreciation 10%", "Expense", "Operating Expenses"),
            ("EXP-109", "Depreciation 15%", "Expense", "Operating Expenses"),
            ("EXP-110", "Depreciation 40%", "Expense", "Operating Expenses"),
            ("EXP-111", "Printing & Stationary", "Expense", "Administrative Expenses"),
            ("EXP-112", "Bank Charges", "Expense", "Other Expenses"),
            ("EXP-120", "Waste/Plastic Collection Charges", "Expense", "Operating Expenses"),
            ("AST-101", "Cash in Hand", "Asset", "Current Assets"),
            ("AST-102", "Union Bank of India", "Asset", "Current Assets"),
            ("AST-103", "State Bank of India", "Asset", "Current Assets"),
            ("AST-104", "Fixed Asset Computer", "Asset", "Non Current Assets"),
            ("AST-105", "Fixed Asset Furniture & Fixtures", "Asset", "Non Current Assets"),
            ("AST-106", "Office Equipments", "Asset", "Non Current Assets"),  
            ("AST-107", "Building", "Asset", "Non Current Assets"),
            ("AST-108", "Loan Principal Control", "Asset", "Loans & Advances"),
            ("AST-110", "Gold Loan Advances", "Asset", "Loans & Advances"),
            ("LIA-101", "SB Deposits Control", "Liability", "Deposits"),
            ("LIA-102", "FD Deposits Control", "Liability", "Deposits"),
            ("LIA-103", "RD Deposits Control", "Liability", "Deposits"),
            ("LIA-104", "Unearned Interest Suspense Account", "Liability", "Deferred Income"),
            ("INC-111", "Gold Loan Interest Income", "Income", "Primary Revenue"),
            ("EQT-101", "Capital Account", "Equity", "Capital"),
            ("EQT-102", "Retained Earnings", "Equity", "Reserves"),
            ("EQT-103", "Income Summary", "Equity", "Temporary")
        ]
        
        if USING_SUPABASE:
            cursor.executemany("""
                INSERT INTO chart_of_accounts (account_code, account_name, account_type, category) 
                VALUES (%s, %s, %s, %s) 
                ON CONFLICT (account_code) DO NOTHING
            """, default_accounts)
            cursor.execute("""
                INSERT INTO _schema_init_tracker (id, version, updated_at)
                VALUES (1, %s, CURRENT_TIMESTAMP::text)
                ON CONFLICT (id) DO UPDATE SET version = EXCLUDED.version, updated_at = CURRENT_TIMESTAMP::text
            """, (SCHEMA_VERSION,))
            
            # Ensure customers.account_type is populated and sync legacy accounts
            try:
                cursor.execute("""
                    UPDATE customers
                    SET account_type = accounts.account_type
                    FROM accounts
                    WHERE customers.id = accounts.customer_id AND (customers.account_type IS NULL OR customers.account_type = '');
                """)
                cursor.execute("""
                    DELETE FROM sb_accounts
                    WHERE customer_id IN (
                        SELECT c.id FROM customers c
                        JOIN accounts a ON c.id = a.customer_id
                        WHERE a.account_type IN ('Recurring Deposit', 'Fixed Deposit')
                    ) AND balance = 0 AND account_no NOT IN (SELECT DISTINCT account_no FROM transactions WHERE account_no IS NOT NULL);
                """)
            except Exception:
                pass
                
            sync_postgres_sequences(conn)
        else:
            cursor.executemany("INSERT OR IGNORE INTO chart_of_accounts VALUES (?, ?, ?, ?)", default_accounts)
            cursor.execute("INSERT OR REPLACE INTO _schema_init_tracker (id, version, updated_at) VALUES (1, ?, datetime('now'))", (SCHEMA_VERSION,))
            try:
                cursor.execute("""
                    UPDATE customers
                    SET account_type = (SELECT account_type FROM accounts WHERE accounts.customer_id = customers.id LIMIT 1)
                    WHERE account_type IS NULL OR account_type = '';
                """)
                cursor.execute("""
                    DELETE FROM sb_accounts
                    WHERE customer_id IN (
                        SELECT c.id FROM customers c
                        JOIN accounts a ON c.id = a.customer_id
                        WHERE a.account_type IN ('Recurring Deposit', 'Fixed Deposit')
                    ) AND balance = 0 AND account_no NOT IN (SELECT DISTINCT account_no FROM transactions WHERE account_no IS NOT NULL);
                """)
            except Exception:
                pass

        conn.commit()
        DB_INITIALIZED = True
        DB_INIT_ERROR = None
        return True
    except Exception as e:
        DB_INIT_ERROR = str(e)
        print(f"❌ Database initialization error: {str(e)}")
        return False
    finally:
        release_connection(conn)

def sync_postgres_sequences(conn=None):
    """
    Ensures all PostgreSQL auto-increment sequences (SERIAL/BIGSERIAL) are 
    advanced to match or exceed the maximum ID present in each table.
    Prevents 'duplicate key value violates unique constraint' errors permanently.
    """
    if not USING_SUPABASE:
        return
        
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
        
    try:
        cursor = conn.cursor()
        cursor.execute("""
            DO $$
            DECLARE
                t text;
                c text;
                s text;
                m bigint;
            BEGIN
                FOR t, c IN VALUES 
                    ('jv_entries', 'entry_id'),
                    ('journal_vouchers', 'jv_id'),
                    ('bank_book', 'id'),
                    ('cash_book', 'id'),
                    ('customers', 'id'),
                    ('transactions', 'id'),
                    ('personal_loans', 'id'),
                    ('gold_loans', 'id'),
                    ('loan_repayments', 'id'),
                    ('loan_emi_schedules', 'id'),
                    ('fixed_deposits', 'fd_id'),
                    ('recurring_deposits', 'rd_id'),
                    ('accounts', 'id')
                LOOP
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = t AND table_schema = 'public') THEN
                        s := pg_get_serial_sequence(t, c);
                        IF s IS NOT NULL THEN
                            EXECUTE format('SELECT COALESCE(MAX(%I), 0) FROM %I', c, t) INTO m;
                            EXECUTE format('SELECT setval(%L, %s, true)', s, GREATEST(m, 1));
                        END IF;
                    END IF;
                END LOOP;
            END $$;
        """)
        conn.commit()
    except Exception as e:
        print(f"⚠️ Sequence sync notice: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        if should_close:
            release_connection(conn)

def clear_db_cache():
    """Clears Streamlit cached queries on data mutations"""
    try:
        import streamlit as st
        if hasattr(st, "cache_data"):
            st.cache_data.clear()
    except Exception:
        pass

def run_query(query, params=(), fetch=True, max_retries=3):
    """Execute a database query with auto-initialization, automatic retry on SSL/connection drops, and connection cleanup"""
    if not DB_INITIALIZED:
        init_db()

    last_err = None
    for attempt in range(max_retries):
        conn = None
        is_broken = False
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Automatic translation for SQLite/Postgres placeholder compatibility
            if USING_SUPABASE:
                if "%s" not in query and "?" in query:
                    query = re.sub(r'%(?!%)', '%%', query)
                    query = query.replace("?", "%s")
                elif params and len(params) > 0:
                    query = re.sub(r'%(?!s|%)', '%%', query)
            else:
                if "?" not in query and "%s" in query:
                    query = query.replace("%s", "?")
                    
            if params and len(params) > 0:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            res = cursor.fetchall() if fetch else None
            conn.commit()
            release_connection(conn)
            if not fetch:
                clear_db_cache()
            if res is not None:
                sanitized = []
                for row in res:
                    if isinstance(row, (tuple, list)):
                        new_row = []
                        for c in row:
                            if isinstance(c, (memoryview, bytearray)):
                                new_row.append(bytes(c))
                            else:
                                new_row.append(c)
                        sanitized.append(tuple(new_row))
                    else:
                        sanitized.append(row)
                res = sanitized
            return res
        except Exception as e:
            last_err = e
            is_broken = True
            if conn is not None and USING_SUPABASE:
                try:
                    conn.rollback()
                except Exception:
                    pass
            release_connection(conn, is_broken=True)
            
            # If SSL drop, connection lost, or operational error, reset pool and retry!
            err_msg = str(e).lower()
            if any(s in err_msg for s in ["ssl", "closed unexpectedly", "terminat", "broken", "connection", "operationalerror", "eof"]):
                reset_pg_pool()
                time.sleep(0.2 * (attempt + 1))
                continue
            else:
                break
                
    try:
        import streamlit as st
        if hasattr(st, "runtime") and st.runtime.exists():
            st.error(f"Database error: {str(last_err)}")
        else:
            print(f"Database error: {str(last_err)}")
    except Exception:
        print(f"Database error: {str(last_err)}")
    return None

try:
    import streamlit as st
    @st.cache_data(ttl=600, show_spinner=False)
    def _inner_cached_query(query, params=()):
        return run_query(query, params, fetch=True)

    def cached_query(query, params=()):
        try:
            p = tuple(params) if isinstance(params, (list, tuple)) else params
            return _inner_cached_query(query, p)
        except Exception:
            return run_query(query, params, fetch=True)

    @st.cache_data(ttl=600, show_spinner=False)
    def get_all_gold_loans_bundle():
        """
        Fetches all Gold Loans, all Gold EMI Schedules, and all Gold Repayments
        in 1 unified cacheable bundle for 0.0ms instant tab rendering.
        """
        all_gl_data = run_query("""
            SELECT gl.id, gl.loan_no, gl.customer_id, c.name, COALESCE(c.account_no, 'N/A'), c.phone,
                   gl.sanction_date, gl.gold_rate_per_gram, gl.ornament_details, gl.item_count,
                   gl.gross_weight, gl.stone_deduction, gl.net_weight, gl.purity, gl.market_value,
                   gl.ltv_percent, gl.principal_amount, gl.interest_rate, gl.interest_rate_monthly,
                   COALESCE(gl.tenure_days, gl.tenure_months * 30, 365) AS tenure_days,
                   gl.tenure_months, gl.total_interest, gl.total_repayable, gl.installment_amount,
                   gl.monthly_principal_emi, gl.monthly_interest_emi, gl.monthly_interest_due,
                   gl.loan_from_date, gl.loan_to_date, gl.first_emi_due, gl.last_emi_due,
                   gl.outstanding_due, gl.vault_packet_no, gl.locker_no, gl.appraiser_name,
                   gl.disbursal_mode, gl.voucher_no, gl.status, gl.remarks, COALESCE(gl.renewal_count, 0),
                   gl.last_renewal_date, c.street, c.city, c.state, c.pincode, gl.gold_image_file,
                   CASE WHEN gl.gold_image_data IS NOT NULL THEN 1 ELSE 0 END as has_photo
            FROM gold_loans gl
            JOIN customers c ON gl.customer_id = c.id
            ORDER BY gl.id DESC
        """) or []

        gl_schedules = run_query("""
            SELECT loan_id, emi_number, from_date, to_date, due_date, principal_component, interest_component, emi_amount, paid_amount, status
            FROM loan_emi_schedules
            WHERE loan_type = 'GOLD'
            ORDER BY loan_id, emi_number ASC
        """) or []

        gl_repayments = run_query("""
            SELECT loan_id, payment_date, voucher_no, amount_paid, payment_mode, narration
            FROM loan_repayments
            WHERE loan_type = 'GOLD'
            ORDER BY loan_id, id ASC
        """) or []

        gl_sched_map = {}
        for s in gl_schedules:
            gl_sched_map.setdefault(s[0], []).append(s[1:])

        gl_rep_map = {}
        for r in gl_repayments:
            gl_rep_map.setdefault(r[0], []).append(r[1:])

        return all_gl_data, gl_sched_map, gl_rep_map

    @st.cache_data(ttl=600, show_spinner=False)
    def get_all_personal_loans_bundle():
        """
        Fetches all Personal Loans, all Personal EMI Schedules, and all Personal Repayments
        in 1 unified cacheable bundle for 0.0ms instant tab rendering.
        """
        all_pl_data = run_query("""
            SELECT pl.id, pl.loan_no, pl.customer_id, c.name, COALESCE(c.account_no, 'N/A'), c.phone,
                   pl.sanction_date, pl.principal_amount, pl.interest_rate, pl.interest_type,
                   pl.tenure_days, pl.tenure_months, pl.total_interest, pl.total_repayable,
                   pl.installment_amount, pl.monthly_principal_emi, pl.monthly_interest_emi,
                   pl.loan_from_date, pl.loan_to_date, pl.first_emi_due, pl.last_emi_due,
                   pl.outstanding_due, pl.disbursal_mode, pl.voucher_no, pl.guarantor_name,
                   pl.guarantor_phone, COALESCE(pl.guarantor_relation, 'Surety'),
                   COALESCE(pl.guarantor_address, 'Balaramapuram, Trivandrum'),
                   pl.purpose, pl.status, pl.remarks, COALESCE(pl.renewal_count, 0),
                   pl.last_renewal_date, c.street, c.city, c.state, c.pincode
            FROM personal_loans pl
            JOIN customers c ON pl.customer_id = c.id
            ORDER BY pl.id DESC
        """) or []

        pl_schedules = run_query("""
            SELECT loan_id, emi_number, from_date, to_date, due_date, principal_component, interest_component, emi_amount, paid_amount, status
            FROM loan_emi_schedules
            WHERE loan_type = 'PERSONAL'
            ORDER BY loan_id, emi_number ASC
        """) or []

        pl_repayments = run_query("""
            SELECT loan_id, payment_date, voucher_no, amount_paid, payment_mode, narration
            FROM loan_repayments
            WHERE loan_type = 'PERSONAL'
            ORDER BY loan_id, id ASC
        """) or []

        pl_sched_map = {}
        for s in pl_schedules:
            pl_sched_map.setdefault(s[0], []).append(s[1:])

        pl_rep_map = {}
        for r in pl_repayments:
            pl_rep_map.setdefault(r[0], []).append(r[1:])

        return all_pl_data, pl_sched_map, pl_rep_map
except Exception:
    def cached_query(query, params=()):
        return run_query(query, params, fetch=True)
    def get_all_gold_loans_bundle():
        return [], {}, {}
    def get_all_personal_loans_bundle():
        return [], {}, {}

def sync_db_sequences(table_name=None, id_column='id'):
    """
    Syncs PostgreSQL auto-increment sequences to match MAX(id) in a single fast roundtrip.
    """
    if not USING_SUPABASE:
        return
    
    if table_name:
        table_cols = [(table_name, id_column)]
    else:
        table_cols = [
            ('customers', 'id'), ('journal_vouchers', 'jv_id'), ('jv_entries', 'entry_id'),
            ('cash_book', 'id'), ('bank_book', 'id'), ('transactions', 'id'),
            ('fixed_deposits', 'fd_id'), ('recurring_deposits', 'rd_id')
        ]
        
    statements = []
    for tbl, col in table_cols:
        statements.append(f"""
            seq_name := pg_get_serial_sequence('{tbl}', '{col}');
            IF seq_name IS NOT NULL THEN
                EXECUTE 'SELECT COALESCE(MAX({col}), 0) FROM {tbl}' INTO max_id;
                IF max_id = 0 THEN
                    EXECUTE 'ALTER SEQUENCE ' || seq_name || ' RESTART WITH 1';
                ELSE
                    EXECUTE 'SELECT setval(''' || seq_name || ''', ' || max_id || ', true)';
                END IF;
            END IF;
        """)
        
    combined_sql = f"""
        DO $$
        DECLARE
            seq_name text;
            max_id bigint;
        BEGIN
            {' '.join(statements)}
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END $$;
    """
    try:
        run_query(combined_sql, fetch=False)
    except Exception:
        pass

def save_uploaded_file(uploaded_file):
    """
    Processes uploaded files directly in memory:
    - Compresses images with PIL (max 1200px, 80% quality)
    - Returns (safe_filename, binary_bytes) for direct database insertion.
    """
    if uploaded_file is None:
        return None, None
    try:
        raw_bytes = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
        safe_name = "".join(c for c in uploaded_file.name if c.isalnum() or c in "._- ")
        unique_name = f"{int(time.time())}_{safe_name}"
        
        # Optimize / compress image if it's an image
        if hasattr(uploaded_file, "type") and uploaded_file.type and uploaded_file.type.startswith("image/"):
            try:
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(raw_bytes))
                if img.mode in ("RGBA", "P") and not unique_name.lower().endswith(".png"):
                    img = img.convert("RGB")
                img.thumbnail((1200, 1200), Image.LANCZOS)
                out_io = io.BytesIO()
                img_format = "PNG" if unique_name.lower().endswith(".png") else "JPEG"
                img.save(out_io, format=img_format, optimize=True, quality=80)
                raw_bytes = out_io.getvalue()
            except Exception as ex:
                print(f"Image compression note: {ex}")
                
        return unique_name, raw_bytes
    except Exception as e:
        print(f"Error processing uploaded file: {str(e)}")
        return None, None

def get_document_data(file_identifier, doc_type=None, customer_id=None):
    """
    Retrieves document binary bytes and clean filename.
    1. First checks the direct database BYTEA/BLOB storage (fastest & most reliable).
    2. Fallback to S3 bucket or local disk if not yet migrated.
    """
    if not file_identifier and not customer_id:
        return None, None
    
    # 1. Check direct database binary storage
    try:
        if customer_id and doc_type:
            col_data = f"{doc_type}_data"
            col_file = f"{doc_type}_file"
            rows = run_query(f"SELECT {col_file}, {col_data} FROM customers WHERE id = ?", (customer_id,))
            if rows and rows[0][1]:
                fn = rows[0][0] or f"{doc_type}.pdf"
                data = bytes(rows[0][1]) if not isinstance(rows[0][1], bytes) else rows[0][1]
                return data, os.path.basename(fn)
                
        if file_identifier:
            rows = run_query("""
                SELECT adhar_file, adhar_data, pan_file, pan_data, signature_file, signature_data
                FROM customers
                WHERE adhar_file = ? OR pan_file = ? OR signature_file = ?
            """, (file_identifier, file_identifier, file_identifier))
            if rows:
                row = rows[0]
                if file_identifier == row[0] and row[1]:
                    data = bytes(row[1]) if not isinstance(row[1], bytes) else row[1]
                    return data, os.path.basename(row[0])
                elif file_identifier == row[2] and row[3]:
                    data = bytes(row[3]) if not isinstance(row[3], bytes) else row[3]
                    return data, os.path.basename(row[2])
                elif file_identifier == row[4] and row[5]:
                    data = bytes(row[5]) if not isinstance(row[5], bytes) else row[5]
                    return data, os.path.basename(row[4])
    except Exception as db_err:
        print(f"Note on DB document fetch: {db_err}")

    if not file_identifier:
        return None, None

    filename = os.path.basename(file_identifier)

    # 2. Local fallback
    try:
        if os.path.exists(file_identifier):
            with open(file_identifier, "rb") as f:
                return f.read(), filename
        local_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read(), filename
    except Exception as e:
        print(f"Error reading local file: {e}")
        
    return None, None

def delete_customer_cascade(customer_id):
    """
    Safely deletes a customer and cascades all linked accounts, transactions,
    loans, deposits, shares, and documents.
    Resequences remaining customers (id = id - 1) and shifts child customer_id references.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        placeholder = "%s" if USING_SUPABASE else "?"
        
        # 1. Fetch customer details
        cursor.execute(f"SELECT id, name, account_no, adhar_file, pan_file, signature_file FROM customers WHERE id = {placeholder}", (customer_id,))
        cust_row = cursor.fetchone()
        if not cust_row:
            return False, f"Customer with ID {customer_id} not found."
        
        c_id, c_name, c_acc, adh_f, pan_f, sig_f = cust_row
        
        # Helper to execute safe query with savepoints in Postgres
        def safe_exec(sql, params):
            try:
                if USING_SUPABASE:
                    cursor.execute("SAVEPOINT sp")
                cursor.execute(sql, params)
                if USING_SUPABASE:
                    cursor.execute("RELEASE SAVEPOINT sp")
            except Exception:
                if USING_SUPABASE:
                    cursor.execute("ROLLBACK TO SAVEPOINT sp")

        # 2. Delete transactions linked to customer's accounts
        cursor.execute(f"SELECT id FROM accounts WHERE customer_id = {placeholder}", (c_id,))
        acc_ids = [r[0] for r in cursor.fetchall()]
        for a_id in acc_ids:
            safe_exec(f"DELETE FROM transactions WHERE account_id = {placeholder}", (a_id,))
        safe_exec(f"DELETE FROM accounts WHERE customer_id = {placeholder}", (c_id,))
            
        # 3. Delete from sb_accounts
        safe_exec(f"DELETE FROM sb_accounts WHERE customer_id = {placeholder}", (c_id,))
        if c_acc:
            safe_exec(f"DELETE FROM sb_accounts WHERE account_no = {placeholder}", (c_acc,))
            
        # 4. Delete loan repayments, schedules, and loans
        cursor.execute(f"SELECT id FROM personal_loans WHERE customer_id = {placeholder}", (c_id,))
        pl_ids = [r[0] for r in cursor.fetchall()]
        for pl_id in pl_ids:
            safe_exec(f"DELETE FROM loan_repayments WHERE loan_type = 'PERSONAL' AND loan_id = {placeholder}", (pl_id,))
            safe_exec(f"DELETE FROM loan_emi_schedules WHERE loan_type = 'PERSONAL' AND loan_id = {placeholder}", (pl_id,))
        safe_exec(f"DELETE FROM loan_repayments WHERE customer_id = {placeholder}", (c_id,))
        safe_exec(f"DELETE FROM personal_loans WHERE customer_id = {placeholder}", (c_id,))
        
        # 5. Delete gold loans, FDs, RDs
        cursor.execute(f"SELECT id FROM gold_loans WHERE customer_id = {placeholder}", (c_id,))
        gl_ids = [r[0] for r in cursor.fetchall()]
        for gl_id in gl_ids:
            safe_exec(f"DELETE FROM loan_repayments WHERE loan_type = 'GOLD' AND loan_id = {placeholder}", (gl_id,))
            safe_exec(f"DELETE FROM loan_emi_schedules WHERE loan_type = 'GOLD' AND loan_id = {placeholder}", (gl_id,))
        safe_exec(f"DELETE FROM gold_loans WHERE customer_id = {placeholder}", (c_id,))
        safe_exec(f"DELETE FROM fixed_deposits WHERE customer_id = {placeholder}", (c_id,))
        safe_exec(f"DELETE FROM recurring_deposits WHERE customer_id = {placeholder}", (c_id,))
            
        # 6. Delete from customers table
        cursor.execute(f"DELETE FROM customers WHERE id = {placeholder}", (c_id,))
        
        # 7. Resequence remaining customers and shift foreign keys
        if USING_SUPABASE:
            cursor.execute("UPDATE sb_accounts SET customer_id = customer_id - 1 WHERE customer_id > %s", (c_id,))
            safe_exec("UPDATE accounts SET customer_id = customer_id - 1 WHERE customer_id > %s", (c_id,))
            cursor.execute("UPDATE personal_loans SET customer_id = customer_id - 1 WHERE customer_id > %s", (c_id,))
            cursor.execute("UPDATE gold_loans SET customer_id = customer_id - 1 WHERE customer_id > %s", (c_id,))
            cursor.execute("UPDATE loan_repayments SET customer_id = customer_id - 1 WHERE customer_id > %s", (c_id,))
            cursor.execute("UPDATE fixed_deposits SET customer_id = customer_id - 1 WHERE customer_id > %s", (c_id,))
            cursor.execute("UPDATE recurring_deposits SET customer_id = customer_id - 1 WHERE customer_id > %s", (c_id,))
            
            cursor.execute("UPDATE customers SET id = -id WHERE id > %s", (c_id,))
            cursor.execute("UPDATE customers SET id = (-id) - 1 WHERE id < 0")
            cursor.execute("""
                DO $$
                DECLARE
                    max_id BIGINT;
                BEGIN
                    SELECT COALESCE(MAX(id), 0) INTO max_id FROM customers;
                    IF max_id = 0 THEN
                        EXECUTE 'ALTER SEQUENCE customers_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('customers_id_seq', max_id, true);
                    END IF;
                END $$;
            """)
        else:
            cursor.execute("UPDATE sb_accounts SET customer_id = customer_id - 1 WHERE customer_id > ?", (c_id,))
            cursor.execute("UPDATE personal_loans SET customer_id = customer_id - 1 WHERE customer_id > ?", (c_id,))
            cursor.execute("UPDATE gold_loans SET customer_id = customer_id - 1 WHERE customer_id > ?", (c_id,))
            cursor.execute("UPDATE loan_repayments SET customer_id = customer_id - 1 WHERE customer_id > ?", (c_id,))
            cursor.execute("UPDATE fixed_deposits SET customer_id = customer_id - 1 WHERE customer_id > ?", (c_id,))
            cursor.execute("UPDATE recurring_deposits SET customer_id = customer_id - 1 WHERE customer_id > ?", (c_id,))
            
            cursor.execute("UPDATE customers SET id = -id WHERE id > ?", (c_id,))
            cursor.execute("UPDATE customers SET id = (-id) - 1 WHERE id < 0")
            
        conn.commit()
        
        # 8. Clean up local files if any
        for fpath in [adh_f, pan_f, sig_f]:
            if fpath and os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass
                    
        return True, f"Customer #{c_id} ({c_name}) and all associated accounts were permanently deleted. Sequence re-aligned without gaps."
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)

def get_account_balance_from_jv(account_code):
    try:
        result = run_query("""
            SELECT COALESCE(SUM(JE.debit), 0) - COALESCE(SUM(JE.credit), 0) as net_balance
            FROM jv_entries JE
            JOIN chart_of_accounts CO ON JE.account_code = CO.account_code
            WHERE CO.account_code = ?
        """, (account_code,))
        return result[0][0] if result and result[0][0] is not None else 0.0
    except Exception:
        return 0.0

def get_all_balances():
    """Fetches Cash, Union Bank, and SBI closing balances directly from cash_book and bank_book."""
    try:
        c_row = run_query("SELECT balance FROM cash_book ORDER BY id DESC LIMIT 1")
        c_bal = float(c_row[0][0]) if (c_row and c_row[0] and c_row[0][0] is not None) else None
        
        u_row = run_query("SELECT balance FROM bank_book WHERE bank_name = 'Union Bank of India' ORDER BY id DESC LIMIT 1")
        u_bal = float(u_row[0][0]) if (u_row and u_row[0] and u_row[0][0] is not None) else None
        
        s_row = run_query("SELECT balance FROM bank_book WHERE bank_name = 'State Bank of India' ORDER BY id DESC LIMIT 1")
        s_bal = float(s_row[0][0]) if (s_row and s_row[0] and s_row[0][0] is not None) else None

        if c_bal is None or u_bal is None or s_bal is None:
            jv_res = run_query("""
                SELECT account_code, COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) as net_bal
                FROM jv_entries
                WHERE account_code IN ('AST-101', 'AST-102', 'AST-103')
                GROUP BY account_code
            """)
            bal_map = {'AST-101': 0.0, 'AST-102': 0.0, 'AST-103': 0.0}
            if jv_res:
                for code, bal in jv_res:
                    bal_map[code] = float(bal) if bal is not None else 0.0
            if c_bal is None: c_bal = bal_map['AST-101']
            if u_bal is None: u_bal = bal_map['AST-102']
            if s_bal is None: s_bal = bal_map['AST-103']

        return float(c_bal or 0.0), float(u_bal or 0.0), float(s_bal or 0.0)
    except Exception:
        return 0.0, 0.0, 0.0

def get_cash_balance():
    c_bal, _, _ = get_all_balances()
    return c_bal

def get_bank_balance(bank_name=None):
    _, u_bal, s_bal = get_all_balances()
    if bank_name == "Union Bank of India" or bank_name is None:
        return u_bal
    elif bank_name == "State Bank of India":
        return s_bal
    else:
        result = run_query("SELECT account_code FROM chart_of_accounts WHERE account_name = ? AND account_type = 'Asset'", (bank_name,))
        if result:
            return get_account_balance_from_jv(result[0][0])
        return 0.0

def generate_cash_voucher_no():
    today = datetime.now(IST).strftime("%Y%m%d")
    try:
        result = run_query("SELECT voucher_no FROM cash_book WHERE voucher_no LIKE ? ORDER BY id DESC LIMIT 1", (f"CB{today}%",))
        if result:
            last_seq = int(result[0][0][-4:])
            new_seq = last_seq + 1
        else:
            new_seq = 1
    except Exception:
        new_seq = 1
    return f"CB{today}{new_seq:04d}"

def generate_bank_voucher_no():
    today = datetime.now(IST).strftime("%Y%m%d")
    try:
        result = run_query("SELECT voucher_no FROM bank_book WHERE voucher_no LIKE ? ORDER BY id DESC LIMIT 1", (f"BB{today}%",))
        if result:
            last_seq = int(result[0][0][-4:])
            new_seq = last_seq + 1
        else:
            new_seq = 1
    except Exception:
        new_seq = 1
    return f"BB{today}{new_seq:04d}"

def post_automated_jv(narration, debit_acc, credit_acc, amount, voucher_date=None):
    if amount <= 0:
        return None
    
    if voucher_date is None:
        target_date = str(date.today())
    else:
        target_date = str(voucher_date)
        
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USING_SUPABASE:
            cursor.execute("""
                INSERT INTO journal_vouchers (voucher_date, narration, status) 
                VALUES (%s, %s, 'POSTED') RETURNING jv_id
            """, (target_date, narration))
            jv_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, %s, 0)", (jv_id, debit_acc, amount))
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, 0, %s)", (jv_id, credit_acc, amount))
        else:
            cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", (target_date, narration))
            jv_id = cursor.lastrowid
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, debit_acc, amount))
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, credit_acc, amount))
        
        conn.commit()
        return jv_id
    except Exception as e:
        import streamlit as st
        st.error(f"Error posting journal voucher: {str(e)}")
        if conn is not None and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return None
    finally:
        release_connection(conn)

def post_compound_jv(narration, debit_entries, credit_entries, voucher_date=None):
    """
    debit_entries: list of (account_code, amount)
    credit_entries: list of (account_code, amount)
    """
    if voucher_date is None:
        target_date = str(date.today())
    else:
        target_date = str(voucher_date)
        
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USING_SUPABASE:
            cursor.execute("""
                INSERT INTO journal_vouchers (voucher_date, narration, status) 
                VALUES (%s, %s, 'POSTED') RETURNING jv_id
            """, (target_date, narration))
            jv_id = cursor.fetchone()[0]
            for acc, amt in debit_entries:
                if amt > 0:
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, %s, 0)", (jv_id, acc, amt))
            for acc, amt in credit_entries:
                if amt > 0:
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, 0, %s)", (jv_id, acc, amt))
        else:
            cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", (target_date, narration))
            jv_id = cursor.lastrowid
            for acc, amt in debit_entries:
                if amt > 0:
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, acc, amt))
            for acc, amt in credit_entries:
                if amt > 0:
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, acc, amt))
        
        conn.commit()
        return jv_id
    except Exception as e:
        import streamlit as st
        st.error(f"Error posting compound journal voucher: {str(e)}")
        if conn is not None and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return None
    finally:
        release_connection(conn)

_account_name_cache = {}

def get_account_name(account_code):
    global _account_name_cache
    if not account_code:
        return ""
    if account_code in _account_name_cache:
        return _account_name_cache[account_code]
    try:
        result = run_query("SELECT account_name FROM chart_of_accounts WHERE account_code = ?", (account_code,))
        name = result[0][0] if result else ""
        if name:
            _account_name_cache[account_code] = name
        return name
    except Exception:
        return ""

def fetch_cb_voucher(voucher_no):
    return run_query("SELECT date, voucher_no, particulars, debit_amount, credit_amount, account_code, narration FROM cash_book WHERE voucher_no = ?", (voucher_no,))

def fetch_bb_voucher(voucher_no):
    return run_query("SELECT date, voucher_no, bank_name, particulars, debit_amount, credit_amount, account_code, narration FROM bank_book WHERE voucher_no = ?", (voucher_no,))

def fetch_jv_voucher(jv_id):
    query = """
        SELECT 
            jv.voucher_date,
            jv.narration,
            je.account_code,
            co.account_name,
            je.debit,
            je.credit
        FROM journal_vouchers jv
        JOIN jv_entries je ON jv.jv_id = je.jv_id
        JOIN chart_of_accounts co ON je.account_code = co.account_code
        WHERE jv.jv_id = ?
    """
    return run_query(query, (jv_id,))

def delete_document(file_identifier, doc_type=None, customer_id=None):
    """
    Clears the document from database BYTEA storage and cleans up any legacy S3/local files.
    """
    if customer_id and doc_type:
        try:
            run_query(f"UPDATE customers SET {doc_type}_file = NULL, {doc_type}_data = NULL WHERE id = ?", (customer_id,), fetch=False)
        except Exception:
            pass

    if not file_identifier:
        return

    # Clear from DB by identifier
    try:
        run_query("""
            UPDATE customers
            SET adhar_file = CASE WHEN adhar_file = ? THEN NULL ELSE adhar_file END,
                adhar_data = CASE WHEN adhar_file = ? THEN NULL ELSE adhar_data END,
                pan_file = CASE WHEN pan_file = ? THEN NULL ELSE pan_file END,
                pan_data = CASE WHEN pan_file = ? THEN NULL ELSE pan_data END,
                signature_file = CASE WHEN signature_file = ? THEN NULL ELSE signature_file END,
                signature_data = CASE WHEN signature_file = ? THEN NULL ELSE signature_data END
            WHERE adhar_file = ? OR pan_file = ? OR signature_file = ?
        """, (file_identifier, file_identifier, file_identifier, file_identifier, file_identifier, file_identifier, file_identifier, file_identifier, file_identifier), fetch=False)
    except Exception:
        pass

def record_cash_book_transaction(entry_type, amount, account_code, particulars, narration, tx_date):
    """
    Executes JV creation, JV entries, Cash balance calculation, Cash Book insertion, 
    and Bank Book mirror insertion inside a SINGLE high-speed database transaction.
    Reduces 10-15 network round trips down to 1 single trip!
    """
    if amount <= 0:
        return False, "Amount must be greater than 0"
        
    today = str(tx_date)
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Generate Cash Voucher Number
        today_code = datetime.now(IST).strftime("%Y%m%d")
        if USING_SUPABASE:
            cursor.execute("SELECT voucher_no FROM cash_book WHERE voucher_no LIKE %s ORDER BY id DESC LIMIT 1", (f"CB{today_code}%%",))
        else:
            cursor.execute("SELECT voucher_no FROM cash_book WHERE voucher_no LIKE ? ORDER BY id DESC LIMIT 1", (f"CB{today_code}%",))
        v_res = cursor.fetchone()
        if v_res and v_res[0]:
            try:
                seq = int(v_res[0][-4:]) + 1
            except Exception:
                seq = 1
        else:
            seq = 1
        voucher_no = f"CB{today_code}{seq:04d}"
        
        # 2. Build narration
        full_narration = particulars
        if narration and narration.strip():
            full_narration += f" ({narration.strip()})"
            
        jv_prefix = "Cash Receipt" if "DEBIT" in entry_type else "Cash Payment"
        jv_narr = f"{jv_prefix} [{voucher_no}]: {full_narration}"
        
        # 3. Insert Journal Voucher
        if USING_SUPABASE:
            cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (%s, %s, 'POSTED') RETURNING jv_id", (today, jv_narr))
            jv_id = cursor.fetchone()[0]
            
            # 4. Insert JV Entries
            if "DEBIT" in entry_type:
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, 'AST-101', %s, 0)", (jv_id, amount))
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, 0, %s)", (jv_id, account_code, amount))
            else:
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, %s, 0)", (jv_id, account_code, amount))
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, 'AST-101', 0, %s)", (jv_id, amount))
                
            # 5. Calculate new cash balance
            cursor.execute("SELECT COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) FROM jv_entries WHERE account_code = 'AST-101'")
            new_cash_bal = float(cursor.fetchone()[0] or 0.0)
            
            # 6. Insert Cash Book
            dr_amt = amount if "DEBIT" in entry_type else 0.0
            cr_amt = amount if "CREDIT" in entry_type else 0.0
            cursor.execute("""
                INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (today, voucher_no, particulars, dr_amt, cr_amt, new_cash_bal, account_code, narration, datetime.now(IST).strftime("%Y-%m-%d %H:%M")))
            
            # 7. Mirror entry for Bank if account_code is AST-102 or AST-103
            if account_code in ('AST-102', 'AST-103'):
                bank_name = "Union Bank of India" if account_code == 'AST-102' else "State Bank of India"
                cursor.execute("SELECT voucher_no FROM bank_book WHERE voucher_no LIKE %s ORDER BY id DESC LIMIT 1", (f"BB{today_code}%%",))
                bb_res = cursor.fetchone()
                b_seq = int(bb_res[0][-4:]) + 1 if bb_res and bb_res[0] else 1
                b_voucher = f"BB{today_code}{b_seq:04d}"
                
                cursor.execute("SELECT COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) FROM jv_entries WHERE account_code = %s", (account_code,))
                new_bank_bal = float(cursor.fetchone()[0] or 0.0)
                
                bank_dr = amount if "CREDIT" in entry_type else 0.0
                bank_cr = amount if "DEBIT" in entry_type else 0.0
                cursor.execute("""
                    INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (today, b_voucher, f"Cash Transfer: {particulars}", bank_dr, bank_cr, new_bank_bal, bank_name, "AST-101", narration, datetime.now(IST).strftime("%Y-%m-%d %H:%M")))
        else:
            cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", (today, jv_narr))
            jv_id = cursor.lastrowid
            if "DEBIT" in entry_type:
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, 'AST-101', ?, 0)", (jv_id, amount))
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, account_code, amount))
            else:
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, account_code, amount))
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, 'AST-101', 0, ?)", (jv_id, amount))
            
            cursor.execute("SELECT COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) FROM jv_entries WHERE account_code = 'AST-101'")
            new_cash_bal = float(cursor.fetchone()[0] or 0.0)
            dr_amt = amount if "DEBIT" in entry_type else 0.0
            cr_amt = amount if "CREDIT" in entry_type else 0.0
            cursor.execute("""
                INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (today, voucher_no, particulars, dr_amt, cr_amt, new_cash_bal, account_code, narration, datetime.now(IST).strftime("%Y-%m-%d %H:%M")))
            
        conn.commit()
        return True, voucher_no
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)

def update_cash_book_transaction(edit_id, entry_type, amount, account_code, particulars, narration, voucher_no, tx_date=None):
    """
    Executes Cash Book update, JV header update, and JV entries regeneration
    in a SINGLE high-speed database transaction.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        dr_amt = amount if "DEBIT" in entry_type else 0.0
        cr_amt = amount if "CREDIT" in entry_type else 0.0
        
        if USING_SUPABASE:
            # 1. Update Cash Book row
            if tx_date:
                cursor.execute("""
                    UPDATE cash_book 
                    SET date = %s, particulars = %s, debit_amount = %s, credit_amount = %s, account_code = %s, narration = %s 
                    WHERE id = %s
                """, (str(tx_date), particulars, dr_amt, cr_amt, account_code, narration, edit_id))
            else:
                cursor.execute("""
                    UPDATE cash_book 
                    SET particulars = %s, debit_amount = %s, credit_amount = %s, account_code = %s, narration = %s 
                    WHERE id = %s
                """, (particulars, dr_amt, cr_amt, account_code, narration, edit_id))
            
            # 2. Locate matching JV
            cursor.execute("SELECT jv_id FROM journal_vouchers WHERE narration LIKE %s", (f"%%{voucher_no}%%",))
            jv_row = cursor.fetchone()
            if jv_row:
                jv_id = jv_row[0]
                full_narr = particulars
                if narration and narration.strip():
                    full_narr += f" ({narration.strip()})"
                jv_prefix = "Cash Receipt" if "DEBIT" in entry_type else "Cash Payment"
                if tx_date:
                    cursor.execute("UPDATE journal_vouchers SET voucher_date = %s, narration = %s WHERE jv_id = %s", (str(tx_date), f"{jv_prefix} [{voucher_no}]: {full_narr}", jv_id))
                else:
                    cursor.execute("UPDATE journal_vouchers SET narration = %s WHERE jv_id = %s", (f"{jv_prefix} [{voucher_no}]: {full_narr}", jv_id))
                
                # Regenerate entries
                cursor.execute("DELETE FROM jv_entries WHERE jv_id = %s", (jv_id,))
                if "DEBIT" in entry_type:
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, 'AST-101', %s, 0)", (jv_id, amount))
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, 0, %s)", (jv_id, account_code, amount))
                else:
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, %s, 0)", (jv_id, account_code, amount))
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, 'AST-101', 0, %s)", (jv_id, amount))
        else:
            if tx_date:
                cursor.execute("""
                    UPDATE cash_book 
                    SET date = ?, particulars = ?, debit_amount = ?, credit_amount = ?, account_code = ?, narration = ? 
                    WHERE id = ?
                """, (str(tx_date), particulars, dr_amt, cr_amt, account_code, narration, edit_id))
            else:
                cursor.execute("""
                    UPDATE cash_book 
                    SET particulars = ?, debit_amount = ?, credit_amount = ?, account_code = ?, narration = ? 
                    WHERE id = ?
                """, (particulars, dr_amt, cr_amt, account_code, narration, edit_id))
            
            cursor.execute("SELECT jv_id FROM journal_vouchers WHERE narration LIKE ?", (f"%{voucher_no}%",))
            jv_row = cursor.fetchone()
            if jv_row:
                jv_id = jv_row[0]
                full_narr = particulars
                if narration and narration.strip():
                    full_narr += f" ({narration.strip()})"
                jv_prefix = "Cash Receipt" if "DEBIT" in entry_type else "Cash Payment"
                if tx_date:
                    cursor.execute("UPDATE journal_vouchers SET voucher_date = ?, narration = ? WHERE jv_id = ?", (str(tx_date), f"{jv_prefix} [{voucher_no}]: {full_narr}", jv_id))
                else:
                    cursor.execute("UPDATE journal_vouchers SET narration = ? WHERE jv_id = ?", (f"{jv_prefix} [{voucher_no}]: {full_narr}", jv_id))
                cursor.execute("DELETE FROM jv_entries WHERE jv_id = ?", (jv_id,))
                if "DEBIT" in entry_type:
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, 'AST-101', ?, 0)", (jv_id, amount))
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, account_code, amount))
                else:
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, account_code, amount))
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, 'AST-101', 0, ?)", (jv_id, amount))
                    
        conn.commit()
        return True, "Updated successfully"
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)

def record_bank_book_transaction(entry_type, amount, bank_name, bank_code, account_code, particulars, narration, tx_date):
    """
    Executes Bank JV creation, JV entries, Bank balance calculation, Bank Book insertion,
    and Cash Book mirror insertion inside a SINGLE high-speed database transaction.
    """
    if amount <= 0:
        return False, "Amount must be greater than 0"
        
    today = str(tx_date)
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        today_code = datetime.now(IST).strftime("%Y%m%d")
        if USING_SUPABASE:
            cursor.execute("SELECT voucher_no FROM bank_book WHERE voucher_no LIKE %s ORDER BY id DESC LIMIT 1", (f"BB{today_code}%%",))
        else:
            cursor.execute("SELECT voucher_no FROM bank_book WHERE voucher_no LIKE ? ORDER BY id DESC LIMIT 1", (f"BB{today_code}%",))
        bb_res = cursor.fetchone()
        b_seq = int(bb_res[0][-4:]) + 1 if bb_res and bb_res[0] else 1
        voucher_no = f"BB{today_code}{b_seq:04d}"
        
        full_narration = particulars
        if narration and narration.strip():
            full_narration += f" ({narration.strip()})"
            
        jv_prefix = f"Bank Deposit [{voucher_no}]: {full_narration} - {bank_name}" if "DEBIT" in entry_type else f"Bank Withdrawal [{voucher_no}]: {full_narration} - {bank_name}"
        
        if USING_SUPABASE:
            cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (%s, %s, 'POSTED') RETURNING jv_id", (today, jv_prefix))
            jv_id = cursor.fetchone()[0]
            
            if "DEBIT" in entry_type:
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, %s, 0)", (jv_id, bank_code, amount))
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, 0, %s)", (jv_id, account_code, amount))
            else:
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, %s, 0)", (jv_id, account_code, amount))
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, 0, %s)", (jv_id, bank_code, amount))
                
            cursor.execute("SELECT COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) FROM jv_entries WHERE account_code = %s", (bank_code,))
            new_bank_bal = float(cursor.fetchone()[0] or 0.0)
            
            dr_amt = amount if "DEBIT" in entry_type else 0.0
            cr_amt = amount if "CREDIT" in entry_type else 0.0
            cursor.execute("""
                INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (today, voucher_no, particulars, dr_amt, cr_amt, new_bank_bal, bank_name, account_code, narration, datetime.now(IST).strftime("%Y-%m-%d %H:%M")))
            
            if account_code == 'AST-101':
                cursor.execute("SELECT voucher_no FROM cash_book WHERE voucher_no LIKE %s ORDER BY id DESC LIMIT 1", (f"CB{today_code}%%",))
                cb_res = cursor.fetchone()
                c_seq = int(cb_res[0][-4:]) + 1 if cb_res and cb_res[0] else 1
                c_voucher = f"CB{today_code}{c_seq:04d}"
                
                cursor.execute("SELECT COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) FROM jv_entries WHERE account_code = 'AST-101'")
                new_cash_bal = float(cursor.fetchone()[0] or 0.0)
                
                cash_dr = amount if "CREDIT" in entry_type else 0.0
                cash_cr = amount if "DEBIT" in entry_type else 0.0
                cursor.execute("""
                    INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (today, c_voucher, f"Bank Transfer: {particulars}", cash_dr, cash_cr, new_cash_bal, bank_code, narration, datetime.now(IST).strftime("%Y-%m-%d %H:%M")))
        else:
            cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", (today, jv_prefix))
            jv_id = cursor.lastrowid
            if "DEBIT" in entry_type:
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, bank_code, amount))
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, account_code, amount))
            else:
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, account_code, amount))
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, bank_code, amount))
                
            cursor.execute("SELECT COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) FROM jv_entries WHERE account_code = ?", (bank_code,))
            new_bank_bal = float(cursor.fetchone()[0] or 0.0)
            dr_amt = amount if "DEBIT" in entry_type else 0.0
            cr_amt = amount if "CREDIT" in entry_type else 0.0
            cursor.execute("""
                INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (today, voucher_no, particulars, dr_amt, cr_amt, new_bank_bal, bank_name, account_code, narration, datetime.now(IST).strftime("%Y-%m-%d %H:%M")))
            
        conn.commit()
        return True, voucher_no
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        err_msg = str(e)
        if USING_SUPABASE and any(term in err_msg.lower() for term in ["unique constraint", "pkey", "duplicate key"]):
            try:
                sync_postgres_sequences()
                # Retry once after auto-healing sequence
                return record_bank_book_transaction(entry_type, amount, bank_name, bank_code, account_code, particulars, narration, tx_date)
            except Exception as retry_e:
                err_msg = str(retry_e)
        return False, err_msg
    finally:
        release_connection(conn)

def record_sb_transaction(account_no, tx_type, amount, pay_mode, chosen_asset_code, narration, tx_date=None):
    """
    Executes SB balance update, transaction record, JV creation, JV entries,
    and Cash/Bank book recording inside a SINGLE database transaction.
    """
    if amount <= 0:
        return False, "Amount must be greater than 0"
        
    if tx_date:
        today = str(tx_date)
        today_code = today.replace("-", "")
        today_time = f"{today} 12:00"
    else:
        today = datetime.now(IST).strftime("%Y-%m-%d")
        today_time = datetime.now(IST).strftime("%Y-%m-%d %H:%M")
        today_code = datetime.now(IST).strftime("%Y%m%d")
    tx_id = f"TX{datetime.now(IST).strftime('%M%S%f')}"
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Fetch current SB balance
        if USING_SUPABASE:
            cursor.execute("SELECT balance FROM sb_accounts WHERE account_no = %s", (account_no,))
        else:
            cursor.execute("SELECT balance FROM sb_accounts WHERE account_no = ?", (account_no,))
        res = cursor.fetchone()
        if not res:
            return False, "Account not found"
        current_bal = float(res[0] or 0.0)
        
        # 2. Check sufficient funds on withdrawal
        if tx_type == "WITHDRAWAL":
            if current_bal < amount:
                return False, f"Insufficient SB account balance! Available: ₹{current_bal:,.2f}"
            new_bal = current_bal - amount
            tx_direction = "DEBIT"
            debit_acc = "LIA-101"
            credit_acc = chosen_asset_code
            cb_dr = 0.0
            cb_cr = amount
            bb_dr = 0.0
            bb_cr = amount
            particulars = f"SB Withdrawal: {account_no}"
        else:
            new_bal = current_bal + amount
            tx_direction = "CREDIT"
            debit_acc = chosen_asset_code
            credit_acc = "LIA-101"
            cb_dr = amount
            cb_cr = 0.0
            bb_dr = amount
            bb_cr = 0.0
            particulars = f"SB Deposit: {account_no}"
            
        # 3. Update SB Account
        if USING_SUPABASE:
            cursor.execute("UPDATE sb_accounts SET balance = %s WHERE account_no = %s", (new_bal, account_no))
            cursor.execute("INSERT INTO transactions (tx_id, account_no, type, amount, mode, narration, date) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                           (tx_id, account_no, tx_direction, amount, pay_mode, narration, today))
                           
            # 4. Insert JV
            jv_narr = f"SB {tx_type.capitalize()}: {narration} ({account_no})"
            cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (%s, %s, 'POSTED') RETURNING jv_id", (today, jv_narr))
            jv_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, %s, 0)", (jv_id, debit_acc, amount))
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, 0, %s)", (jv_id, credit_acc, amount))
            
            # 5. Asset balance calculation
            cursor.execute("SELECT COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) FROM jv_entries WHERE account_code = %s", (chosen_asset_code,))
            new_asset_bal = float(cursor.fetchone()[0] or 0.0)
            
            # 6. Insert Cash Book / Bank Book
            if chosen_asset_code == 'AST-101':
                cursor.execute("SELECT voucher_no FROM cash_book WHERE voucher_no LIKE %s ORDER BY id DESC LIMIT 1", (f"CB{today_code}%%",))
                cb_res = cursor.fetchone()
                c_seq = int(cb_res[0][-4:]) + 1 if cb_res and cb_res[0] else 1
                voucher_no = f"CB{today_code}{c_seq:04d}"
                cursor.execute("""
                    INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (today, voucher_no, particulars, cb_dr, cb_cr, new_asset_bal, chosen_asset_code, narration, today_time))
            elif chosen_asset_code in ('AST-102', 'AST-103'):
                bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
                cursor.execute("SELECT voucher_no FROM bank_book WHERE voucher_no LIKE %s ORDER BY id DESC LIMIT 1", (f"BB{today_code}%%",))
                bb_res = cursor.fetchone()
                b_seq = int(bb_res[0][-4:]) + 1 if bb_res and bb_res[0] else 1
                voucher_no = f"BB{today_code}{b_seq:04d}"
                cursor.execute("""
                    INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (today, voucher_no, particulars, bb_dr, bb_cr, new_asset_bal, bank_name, chosen_asset_code, narration, today_time))
        else:
            cursor.execute("UPDATE sb_accounts SET balance = ? WHERE account_no = ?", (new_bal, account_no))
            cursor.execute("INSERT INTO transactions (tx_id, account_no, type, amount, mode, narration, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (tx_id, account_no, tx_direction, amount, pay_mode, narration, today))
            jv_narr = f"SB {tx_type.capitalize()}: {narration} ({account_no})"
            cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", (today, jv_narr))
            jv_id = cursor.lastrowid
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, debit_acc, amount))
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, credit_acc, amount))
            
            cursor.execute("SELECT COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) FROM jv_entries WHERE account_code = ?", (chosen_asset_code,))
            new_asset_bal = float(cursor.fetchone()[0] or 0.0)
            
            if chosen_asset_code == 'AST-101':
                cursor.execute("SELECT voucher_no FROM cash_book WHERE voucher_no LIKE ? ORDER BY id DESC LIMIT 1", (f"CB{today_code}%",))
                cb_res = cursor.fetchone()
                c_seq = int(cb_res[0][-4:]) + 1 if cb_res and cb_res[0] else 1
                voucher_no = f"CB{today_code}{c_seq:04d}"
                cursor.execute("""
                    INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (today, voucher_no, particulars, cb_dr, cb_cr, new_asset_bal, chosen_asset_code, narration, today_time))
            elif chosen_asset_code in ('AST-102', 'AST-103'):
                bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
                cursor.execute("SELECT voucher_no FROM bank_book WHERE voucher_no LIKE ? ORDER BY id DESC LIMIT 1", (f"BB{today_code}%",))
                bb_res = cursor.fetchone()
                b_seq = int(bb_res[0][-4:]) + 1 if bb_res and bb_res[0] else 1
                voucher_no = f"BB{today_code}{b_seq:04d}"
                cursor.execute("""
                    INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (today, voucher_no, particulars, bb_dr, bb_cr, new_asset_bal, bank_name, chosen_asset_code, narration, today_time))
                
        conn.commit()
        return True, new_bal
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


# ----------------------------------------------------
# RECURRING DEPOSIT (RD) FINANCIAL CALCULATIONS
# Standard Indian Banking / RBI / IBA Quarterly Compounding
# ----------------------------------------------------
def calculate_rd_maturity(monthly_amount: float, interest_rate: float, tenure_months: int):
    """
    Calculate Recurring Deposit Maturity using standard RBI / Banking Quarterly Compounding formula.
    Each monthly installment k (1 to tenure_months) earns compound interest for the remaining duration:
    remaining_months = tenure_months - k + 1
    A_k = P * (1 + R / 400) ** (remaining_months / 3)
    
    Returns:
        (total_deposit, maturity_amount, total_interest)
    """
    try:
        monthly_amount = float(monthly_amount)
        interest_rate = float(interest_rate)
        tenure_months = int(tenure_months)
    except (ValueError, TypeError):
        return 0.0, 0.0, 0.0

    if monthly_amount <= 0 or tenure_months <= 0:
        return 0.0, 0.0, 0.0

    total_deposit = round(monthly_amount * tenure_months, 2)
    if interest_rate <= 0:
        return total_deposit, total_deposit, 0.0

    i = interest_rate / 400.0
    maturity_amount = sum(monthly_amount * ((1.0 + i) ** ((tenure_months - k + 1) / 3.0)) for k in range(1, tenure_months + 1))
    maturity_amount = round(maturity_amount, 2)
    total_interest = round(maturity_amount - total_deposit, 2)
    return total_deposit, maturity_amount, total_interest


def calculate_rd_accrued_value(monthly_amount: float, interest_rate: float, installments_paid: int):
    """
    Calculate current accrued balance / value for the installments paid so far (e.g. for premature closure or current standing value).
    Returns:
        (total_paid, accrued_amount, interest_earned)
    """
    try:
        monthly_amount = float(monthly_amount)
        interest_rate = float(interest_rate)
        installments_paid = int(installments_paid)
    except (ValueError, TypeError):
        return 0.0, 0.0, 0.0

    if monthly_amount <= 0 or installments_paid <= 0:
        return 0.0, 0.0, 0.0

    total_paid = round(monthly_amount * installments_paid, 2)
    if interest_rate <= 0:
        return total_paid, total_paid, 0.0

    i = interest_rate / 400.0
    accrued_amount = sum(monthly_amount * ((1.0 + i) ** ((installments_paid - k + 1) / 3.0)) for k in range(1, installments_paid + 1))
    accrued_amount = round(accrued_amount, 2)
    interest_earned = round(accrued_amount - total_paid, 2)
    return total_paid, accrued_amount, interest_earned


def delete_cash_book_entry(del_id):
    """
    Deletes an entry from cash_book:
    1. Cascades deletion of associated Journal Voucher and JV entries.
    2. Deletes the row from cash_book.
    3. Shifts all subsequent rows down (id = id - 1) with zero sequence gaps.
    4. Adjusts running balances for all subsequent rows.
    5. Syncs the auto-increment sequence to MAX(id) so the next entry starts at MAX(id) + 1.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Fetch entry details before deletion
        if USING_SUPABASE:
            cursor.execute("SELECT voucher_no, particulars, debit_amount, credit_amount FROM cash_book WHERE id = %s", (del_id,))
        else:
            cursor.execute("SELECT voucher_no, particulars, debit_amount, credit_amount FROM cash_book WHERE id = ?", (del_id,))
        row = cursor.fetchone()
        if not row:
            return False, f"Cash Entry ID {del_id} not found."
            
        voucher_no, particulars, dr, cr = row
        dr = float(dr or 0.0)
        cr = float(cr or 0.0)
        del_delta = dr - cr
        
        # 2. Delete related journal voucher and its entries
        if voucher_no:
            if USING_SUPABASE:
                cursor.execute("SELECT jv_id FROM journal_vouchers WHERE narration LIKE %s", (f"%{voucher_no}%",))
            else:
                cursor.execute("SELECT jv_id FROM journal_vouchers WHERE narration LIKE ?", (f"%{voucher_no}%",))
            jv_row = cursor.fetchone()
            if jv_row:
                jv_id = jv_row[0]
                if USING_SUPABASE:
                    cursor.execute("DELETE FROM jv_entries WHERE jv_id = %s", (jv_id,))
                    cursor.execute("DELETE FROM journal_vouchers WHERE jv_id = %s", (jv_id,))
                else:
                    cursor.execute("DELETE FROM jv_entries WHERE jv_id = ?", (jv_id,))
                    cursor.execute("DELETE FROM journal_vouchers WHERE jv_id = ?", (jv_id,))
                    
        # 3. Delete the cash_book row
        if USING_SUPABASE:
            cursor.execute("DELETE FROM cash_book WHERE id = %s", (del_id,))
            cursor.execute("UPDATE cash_book SET id = -id WHERE id > %s", (del_id,))
            cursor.execute("UPDATE cash_book SET id = (-id) - 1, balance = balance - %s WHERE id < 0", (del_delta,))
            cursor.execute("""
                DO $$
                DECLARE
                    max_id BIGINT;
                BEGIN
                    SELECT COALESCE(MAX(id), 0) INTO max_id FROM cash_book;
                    IF max_id = 0 THEN
                        EXECUTE 'ALTER SEQUENCE cash_book_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('cash_book_id_seq', max_id, true);
                    END IF;
                END $$;
            """)
        else:
            cursor.execute("DELETE FROM cash_book WHERE id = ?", (del_id,))
            cursor.execute("UPDATE cash_book SET id = -id WHERE id > ?", (del_id,))
            cursor.execute("UPDATE cash_book SET id = (-id) - 1, balance = balance - ? WHERE id < 0", (del_delta,))
            
        conn.commit()
        return True, f"Cash Entry ID {del_id} and related ledger entries deleted successfully. Sequence and balances re-aligned without gaps."
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


def delete_bank_book_entry(del_id):
    """
    Deletes an entry from bank_book:
    1. Cascades deletion of associated Journal Voucher and JV entries.
    2. Deletes the row from bank_book.
    3. Shifts all subsequent rows down (id = id - 1) with zero sequence gaps.
    4. Adjusts running balances for subsequent rows of the same bank.
    5. Syncs the auto-increment sequence to MAX(id) so the next entry starts at MAX(id) + 1.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Fetch entry details before deletion
        if USING_SUPABASE:
            cursor.execute("SELECT voucher_no, particulars, debit_amount, credit_amount, bank_name FROM bank_book WHERE id = %s", (del_id,))
        else:
            cursor.execute("SELECT voucher_no, particulars, debit_amount, credit_amount, bank_name FROM bank_book WHERE id = ?", (del_id,))
        row = cursor.fetchone()
        if not row:
            return False, f"Bank Entry ID {del_id} not found."
            
        voucher_no, particulars, dr, cr, bank_name = row
        bank_name = bank_name or 'Union Bank of India'
        dr = float(dr or 0.0)
        cr = float(cr or 0.0)
        del_delta = dr - cr
        
        # 2. Delete related journal voucher and its entries
        if voucher_no:
            if USING_SUPABASE:
                cursor.execute("SELECT jv_id FROM journal_vouchers WHERE narration LIKE %s", (f"%{voucher_no}%",))
            else:
                cursor.execute("SELECT jv_id FROM journal_vouchers WHERE narration LIKE ?", (f"%{voucher_no}%",))
            jv_row = cursor.fetchone()
            if jv_row:
                jv_id = jv_row[0]
                if USING_SUPABASE:
                    cursor.execute("DELETE FROM jv_entries WHERE jv_id = %s", (jv_id,))
                    cursor.execute("DELETE FROM journal_vouchers WHERE jv_id = %s", (jv_id,))
                else:
                    cursor.execute("DELETE FROM jv_entries WHERE jv_id = ?", (jv_id,))
                    cursor.execute("DELETE FROM journal_vouchers WHERE jv_id = ?", (jv_id,))
                    
        # 3. Delete the bank_book row
        if USING_SUPABASE:
            cursor.execute("DELETE FROM bank_book WHERE id = %s", (del_id,))
            cursor.execute("UPDATE bank_book SET id = -id WHERE id > %s", (del_id,))
            cursor.execute("""
                UPDATE bank_book 
                SET id = (-id) - 1, 
                    balance = CASE WHEN bank_name = %s THEN balance - %s ELSE balance END 
                WHERE id < 0
            """, (bank_name, del_delta))
            cursor.execute("""
                DO $$
                DECLARE
                    max_id BIGINT;
                BEGIN
                    SELECT COALESCE(MAX(id), 0) INTO max_id FROM bank_book;
                    IF max_id = 0 THEN
                        EXECUTE 'ALTER SEQUENCE bank_book_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('bank_book_id_seq', max_id, true);
                    END IF;
                END $$;
            """)
        else:
            cursor.execute("DELETE FROM bank_book WHERE id = ?", (del_id,))
            cursor.execute("UPDATE bank_book SET id = -id WHERE id > ?", (del_id,))
            cursor.execute("""
                UPDATE bank_book 
                SET id = (-id) - 1,
                    balance = CASE WHEN bank_name = ? THEN balance - ? ELSE balance END
                WHERE id < 0
            """, (bank_name, del_delta))
            
        conn.commit()
        return True, f"Bank Entry ID {del_id} and related ledger entries deleted successfully. Sequence and balances re-aligned without gaps."
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


def resequence_cash_book():
    """Resequences all cash_book rows from 1 to N without gaps and recalculates running balances."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if USING_SUPABASE:
            cursor.execute("""
                DO $$
                DECLARE
                    r RECORD;
                    new_id INT := 1;
                    curr_bal NUMERIC := 0;
                BEGIN
                    UPDATE cash_book SET id = -id;
                    FOR r IN SELECT id, particulars, debit_amount, credit_amount FROM cash_book ORDER BY date ASC, -id ASC LOOP
                        IF new_id = 1 AND r.particulars ILIKE '%opening%' THEN
                            curr_bal := COALESCE(r.debit_amount, 0) - COALESCE(r.credit_amount, 0);
                        ELSE
                            curr_bal := curr_bal + COALESCE(r.debit_amount, 0) - COALESCE(r.credit_amount, 0);
                        END IF;
                        UPDATE cash_book SET id = new_id, balance = curr_bal WHERE id = r.id;
                        new_id := new_id + 1;
                    END LOOP;
                    
                    IF (SELECT COUNT(*) FROM cash_book) = 0 THEN
                        EXECUTE 'ALTER SEQUENCE cash_book_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('cash_book_id_seq', (SELECT MAX(id) FROM cash_book), true);
                    END IF;
                END $$;
            """)
        else:
            cursor.execute("SELECT id, particulars, debit_amount, credit_amount FROM cash_book ORDER BY date ASC, id ASC")
            rows = cursor.fetchall()
            cursor.execute("UPDATE cash_book SET id = -id")
            curr_bal = 0.0
            for new_id, (old_neg_id, part, dr, cr) in enumerate(rows, 1):
                dr = float(dr or 0.0)
                cr = float(cr or 0.0)
                if new_id == 1 and "opening" in (part or "").lower():
                    curr_bal = dr - cr
                else:
                    curr_bal += (dr - cr)
                cursor.execute("UPDATE cash_book SET id = ?, balance = ? WHERE id = ?", (new_id, curr_bal, -old_neg_id))
        conn.commit()
        return True, "Cash Book resequenced successfully."
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


def resequence_bank_book():
    """Resequences all bank_book rows from 1 to N without gaps and recalculates running balances per bank."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if USING_SUPABASE:
            cursor.execute("""
                DO $$
                DECLARE
                    r RECORD;
                    new_id INT := 1;
                BEGIN
                    UPDATE bank_book SET id = -id;
                    FOR r IN SELECT id FROM bank_book ORDER BY date ASC, -id ASC LOOP
                        UPDATE bank_book SET id = new_id WHERE id = r.id;
                        new_id := new_id + 1;
                    END LOOP;
                    
                    IF (SELECT COUNT(*) FROM bank_book) = 0 THEN
                        EXECUTE 'ALTER SEQUENCE bank_book_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('bank_book_id_seq', (SELECT MAX(id) FROM bank_book), true);
                    END IF;
                END $$;
            """)
        else:
            cursor.execute("SELECT id FROM bank_book ORDER BY date ASC, id ASC")
            rows = cursor.fetchall()
            cursor.execute("UPDATE bank_book SET id = -id")
            for new_id, (old_neg_id,) in enumerate(rows, 1):
                cursor.execute("UPDATE bank_book SET id = ? WHERE id = ?", (new_id, -old_neg_id))
        conn.commit()
        return True, "Bank Book resequenced successfully."
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


def delete_personal_loan_entry(del_id):
    """
    Deletes a personal loan, cascades linked schedules and repayments,
    resequences personal_loans IDs (1..N) and dependent loan_id references,
    and resets the sequence counter.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Fetch loan details
        if USING_SUPABASE:
            cursor.execute("SELECT loan_no, voucher_no, customer_id FROM personal_loans WHERE id = %s", (del_id,))
        else:
            cursor.execute("SELECT loan_no, voucher_no, customer_id FROM personal_loans WHERE id = ?", (del_id,))
        row = cursor.fetchone()
        if not row:
            return False, f"Personal Loan ID {del_id} not found."
            
        loan_no, voucher_no, cust_id = row
        
        # 2. Delete linked EMI schedules & repayments
        if USING_SUPABASE:
            cursor.execute("DELETE FROM loan_emi_schedules WHERE loan_type = 'PERSONAL' AND loan_id = %s", (del_id,))
            cursor.execute("DELETE FROM loan_repayments WHERE loan_type = 'PERSONAL' AND loan_id = %s", (del_id,))
            if voucher_no:
                cursor.execute("DELETE FROM journal_vouchers WHERE narration LIKE %s", (f"%{voucher_no}%",))
            cursor.execute("DELETE FROM personal_loans WHERE id = %s", (del_id,))
            
            # 3. Shift child loan_ids and personal_loans.id
            cursor.execute("UPDATE loan_emi_schedules SET loan_id = loan_id - 1 WHERE loan_type = 'PERSONAL' AND loan_id > %s", (del_id,))
            cursor.execute("UPDATE loan_repayments SET loan_id = loan_id - 1 WHERE loan_type = 'PERSONAL' AND loan_id > %s", (del_id,))
            cursor.execute("UPDATE personal_loans SET id = -id WHERE id > %s", (del_id,))
            cursor.execute("UPDATE personal_loans SET id = (-id) - 1 WHERE id < 0")
            cursor.execute("""
                DO $$
                DECLARE
                    max_id BIGINT;
                BEGIN
                    SELECT COALESCE(MAX(id), 0) INTO max_id FROM personal_loans;
                    IF max_id = 0 THEN
                        EXECUTE 'ALTER SEQUENCE personal_loans_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('personal_loans_id_seq', max_id, true);
                    END IF;
                END $$;
            """)
        else:
            cursor.execute("DELETE FROM loan_emi_schedules WHERE loan_type = 'PERSONAL' AND loan_id = ?", (del_id,))
            cursor.execute("DELETE FROM loan_repayments WHERE loan_type = 'PERSONAL' AND loan_id = ?", (del_id,))
            if voucher_no:
                cursor.execute("DELETE FROM journal_vouchers WHERE narration LIKE ?", (f"%{voucher_no}%",))
            cursor.execute("DELETE FROM personal_loans WHERE id = ?", (del_id,))
            
            cursor.execute("UPDATE loan_emi_schedules SET loan_id = loan_id - 1 WHERE loan_type = 'PERSONAL' AND loan_id > ?", (del_id,))
            cursor.execute("UPDATE loan_repayments SET loan_id = loan_id - 1 WHERE loan_type = 'PERSONAL' AND loan_id > ?", (del_id,))
            cursor.execute("UPDATE personal_loans SET id = -id WHERE id > ?", (del_id,))
            cursor.execute("UPDATE personal_loans SET id = (-id) - 1 WHERE id < 0")
            
        conn.commit()
        return True, f"Personal Loan #{loan_no} deleted and loans re-sequenced successfully without gaps."
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


def delete_gold_loan_entry(del_id):
    """
    Deletes a gold loan, cascades linked schedules and repayments,
    resequences gold_loans IDs (1..N) and dependent loan_id references,
    and resets the sequence counter.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Fetch loan details
        if USING_SUPABASE:
            cursor.execute("SELECT loan_no, voucher_no, customer_id FROM gold_loans WHERE id = %s", (del_id,))
        else:
            cursor.execute("SELECT loan_no, voucher_no, customer_id FROM gold_loans WHERE id = ?", (del_id,))
        row = cursor.fetchone()
        if not row:
            return False, f"Gold Loan ID {del_id} not found."
            
        loan_no, voucher_no, cust_id = row
        
        # 2. Delete linked EMI schedules & repayments
        if USING_SUPABASE:
            cursor.execute("DELETE FROM loan_emi_schedules WHERE loan_type = 'GOLD' AND loan_id = %s", (del_id,))
            cursor.execute("DELETE FROM loan_repayments WHERE loan_type = 'GOLD' AND loan_id = %s", (del_id,))
            if voucher_no:
                cursor.execute("DELETE FROM journal_vouchers WHERE narration LIKE %s", (f"%{voucher_no}%",))
            cursor.execute("DELETE FROM gold_loans WHERE id = %s", (del_id,))
            
            # 3. Shift child loan_ids and gold_loans.id
            cursor.execute("UPDATE loan_emi_schedules SET loan_id = loan_id - 1 WHERE loan_type = 'GOLD' AND loan_id > %s", (del_id,))
            cursor.execute("UPDATE loan_repayments SET loan_id = loan_id - 1 WHERE loan_type = 'GOLD' AND loan_id > %s", (del_id,))
            cursor.execute("UPDATE gold_loans SET id = -id WHERE id > %s", (del_id,))
            cursor.execute("UPDATE gold_loans SET id = (-id) - 1 WHERE id < 0")
            cursor.execute("""
                DO $$
                DECLARE
                    max_id BIGINT;
                BEGIN
                    SELECT COALESCE(MAX(id), 0) INTO max_id FROM gold_loans;
                    IF max_id = 0 THEN
                        EXECUTE 'ALTER SEQUENCE gold_loans_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('gold_loans_id_seq', max_id, true);
                    END IF;
                END $$;
            """)
        else:
            cursor.execute("DELETE FROM loan_emi_schedules WHERE loan_type = 'GOLD' AND loan_id = ?", (del_id,))
            cursor.execute("DELETE FROM loan_repayments WHERE loan_type = 'GOLD' AND loan_id = ?", (del_id,))
            if voucher_no:
                cursor.execute("DELETE FROM journal_vouchers WHERE narration LIKE ?", (f"%{voucher_no}%",))
            cursor.execute("DELETE FROM gold_loans WHERE id = ?", (del_id,))
            
            cursor.execute("UPDATE loan_emi_schedules SET loan_id = loan_id - 1 WHERE loan_type = 'GOLD' AND loan_id > ?", (del_id,))
            cursor.execute("UPDATE loan_repayments SET loan_id = loan_id - 1 WHERE loan_type = 'GOLD' AND loan_id > ?", (del_id,))
            cursor.execute("UPDATE gold_loans SET id = -id WHERE id > ?", (del_id,))
            cursor.execute("UPDATE gold_loans SET id = (-id) - 1 WHERE id < 0")
            
        conn.commit()
        return True, f"Gold Loan #{loan_no} deleted and gold loans re-sequenced successfully without gaps."
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


def delete_fd_entry(del_id):
    """
    Deletes a fixed deposit and resequences fixed_deposits (fd_id = fd_id - 1) without gaps.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if USING_SUPABASE:
            cursor.execute("DELETE FROM fixed_deposits WHERE fd_id = %s", (del_id,))
            cursor.execute("UPDATE fixed_deposits SET fd_id = -fd_id WHERE fd_id > %s", (del_id,))
            cursor.execute("UPDATE fixed_deposits SET fd_id = (-fd_id) - 1 WHERE fd_id < 0")
            cursor.execute("""
                DO $$
                DECLARE
                    max_id BIGINT;
                BEGIN
                    SELECT COALESCE(MAX(fd_id), 0) INTO max_id FROM fixed_deposits;
                    IF max_id = 0 THEN
                        EXECUTE 'ALTER SEQUENCE fixed_deposits_fd_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('fixed_deposits_fd_id_seq', max_id, true);
                    END IF;
                END $$;
            """)
        else:
            cursor.execute("DELETE FROM fixed_deposits WHERE fd_id = ?", (del_id,))
            cursor.execute("UPDATE fixed_deposits SET fd_id = -fd_id WHERE fd_id > ?", (del_id,))
            cursor.execute("UPDATE fixed_deposits SET fd_id = (-fd_id) - 1 WHERE fd_id < 0")
        conn.commit()
        return True, f"Fixed Deposit #{del_id} deleted and resequenced successfully."
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


def delete_rd_entry(del_id):
    """
    Deletes a recurring deposit and resequences recurring_deposits (rd_id = rd_id - 1) without gaps.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if USING_SUPABASE:
            cursor.execute("DELETE FROM recurring_deposits WHERE rd_id = %s", (del_id,))
            cursor.execute("UPDATE recurring_deposits SET rd_id = -rd_id WHERE rd_id > %s", (del_id,))
            cursor.execute("UPDATE recurring_deposits SET rd_id = (-rd_id) - 1 WHERE rd_id < 0")
            cursor.execute("""
                DO $$
                DECLARE
                    max_id BIGINT;
                BEGIN
                    SELECT COALESCE(MAX(rd_id), 0) INTO max_id FROM recurring_deposits;
                    IF max_id = 0 THEN
                        EXECUTE 'ALTER SEQUENCE recurring_deposits_rd_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('recurring_deposits_rd_id_seq', max_id, true);
                    END IF;
                END $$;
            """)
        else:
            cursor.execute("DELETE FROM recurring_deposits WHERE rd_id = ?", (del_id,))
            cursor.execute("UPDATE recurring_deposits SET rd_id = -rd_id WHERE rd_id > ?", (del_id,))
            cursor.execute("UPDATE recurring_deposits SET rd_id = (-rd_id) - 1 WHERE rd_id < 0")
        conn.commit()
        return True, f"Recurring Deposit #{del_id} deleted and resequenced successfully."
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


def delete_jv_entry(del_jv_id):
    """
    Deletes a journal voucher and cascades its jv_entries,
    resequences journal_vouchers (jv_id = jv_id - 1), shifts jv_entries.jv_id,
    resequences jv_entries.entry_id, and syncs sequences.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if USING_SUPABASE:
            cursor.execute("DELETE FROM jv_entries WHERE jv_id = %s", (del_jv_id,))
            cursor.execute("DELETE FROM journal_vouchers WHERE jv_id = %s", (del_jv_id,))
            cursor.execute("UPDATE jv_entries SET jv_id = jv_id - 1 WHERE jv_id > %s", (del_jv_id,))
            cursor.execute("UPDATE journal_vouchers SET jv_id = -jv_id WHERE jv_id > %s", (del_jv_id,))
            cursor.execute("UPDATE journal_vouchers SET jv_id = (-jv_id) - 1 WHERE jv_id < 0")
            
            # Resequence jv_entries entry_id
            cursor.execute("""
                DO $$
                DECLARE
                    rec RECORD;
                    new_id INT := 1;
                    max_j BIGINT;
                    max_e BIGINT;
                BEGIN
                    UPDATE jv_entries SET entry_id = -entry_id;
                    FOR rec IN SELECT entry_id FROM jv_entries ORDER BY -entry_id ASC LOOP
                        UPDATE jv_entries SET entry_id = new_id WHERE entry_id = rec.entry_id;
                        new_id := new_id + 1;
                    END LOOP;
                    
                    SELECT COALESCE(MAX(jv_id), 0) INTO max_j FROM journal_vouchers;
                    IF max_j = 0 THEN
                        EXECUTE 'ALTER SEQUENCE journal_vouchers_jv_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('journal_vouchers_jv_id_seq', max_j, true);
                    END IF;
                    
                    SELECT COALESCE(MAX(entry_id), 0) INTO max_e FROM jv_entries;
                    IF max_e = 0 THEN
                        EXECUTE 'ALTER SEQUENCE jv_entries_entry_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('jv_entries_entry_id_seq', max_e, true);
                    END IF;
                END $$;
            """)
        else:
            cursor.execute("DELETE FROM jv_entries WHERE jv_id = ?", (del_jv_id,))
            cursor.execute("DELETE FROM journal_vouchers WHERE jv_id = ?", (del_jv_id,))
            cursor.execute("UPDATE jv_entries SET jv_id = jv_id - 1 WHERE jv_id > ?", (del_jv_id,))
            cursor.execute("UPDATE journal_vouchers SET jv_id = -jv_id WHERE jv_id > ?", (del_jv_id,))
            cursor.execute("UPDATE journal_vouchers SET jv_id = (-jv_id) - 1 WHERE jv_id < 0")
        conn.commit()
        return True, f"Journal Voucher #{del_jv_id} deleted and resequenced successfully."
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


def delete_transaction_entry(del_id):
    """
    Deletes a savings account transaction and resequences transactions.id (1..N).
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if USING_SUPABASE:
            cursor.execute("DELETE FROM transactions WHERE id = %s", (del_id,))
            cursor.execute("UPDATE transactions SET id = -id WHERE id > %s", (del_id,))
            cursor.execute("UPDATE transactions SET id = (-id) - 1 WHERE id < 0")
            cursor.execute("""
                DO $$
                DECLARE
                    max_id BIGINT;
                BEGIN
                    SELECT COALESCE(MAX(id), 0) INTO max_id FROM transactions;
                    IF max_id = 0 THEN
                        EXECUTE 'ALTER SEQUENCE transactions_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('transactions_id_seq', max_id, true);
                    END IF;
                END $$;
            """)
        else:
            cursor.execute("DELETE FROM transactions WHERE id = ?", (del_id,))
            cursor.execute("UPDATE transactions SET id = -id WHERE id > ?", (del_id,))
            cursor.execute("UPDATE transactions SET id = (-id) - 1 WHERE id < 0")
        conn.commit()
        return True, f"Transaction #{del_id} deleted and resequenced successfully."
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


def delete_sb_account_entry(account_no):
    """
    Deletes an SB account, cascades linked transactions, and resequences remaining transactions.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        placeholder = "%s" if USING_SUPABASE else "?"
        
        # 1. Fetch account details
        cursor.execute(f"SELECT account_no, customer_id, balance FROM sb_accounts WHERE account_no = {placeholder}", (account_no,))
        row = cursor.fetchone()
        if not row:
            return False, f"SB Account {account_no} not found."
            
        # 2. Delete transactions linked to account_no
        cursor.execute(f"DELETE FROM transactions WHERE account_no = {placeholder}", (account_no,))
        
        # 3. Delete SB account
        cursor.execute(f"DELETE FROM sb_accounts WHERE account_no = {placeholder}", (account_no,))
        
        # 4. Resequence transactions
        if USING_SUPABASE:
            cursor.execute("""
                DO $$
                DECLARE
                    rec RECORD;
                    new_id INT := 1;
                    max_id BIGINT;
                BEGIN
                    UPDATE transactions SET id = -id;
                    FOR rec IN SELECT id FROM transactions ORDER BY -id ASC LOOP
                        UPDATE transactions SET id = new_id WHERE id = rec.id;
                        new_id := new_id + 1;
                    END LOOP;
                    SELECT COALESCE(MAX(id), 0) INTO max_id FROM transactions;
                    IF max_id = 0 THEN
                        EXECUTE 'ALTER SEQUENCE transactions_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('transactions_id_seq', max_id, true);
                    END IF;
                END $$;
            """)
        else:
            cursor.execute("SELECT id FROM transactions ORDER BY id ASC")
            rows = cursor.fetchall()
            cursor.execute("UPDATE transactions SET id = -id")
            for new_id, (old_neg_id,) in enumerate(rows, 1):
                cursor.execute("UPDATE transactions SET id = ? WHERE id = ?", (new_id, -old_neg_id))
                
        conn.commit()
        return True, f"SB Account {account_no} deleted successfully."
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


def update_sb_account_details(old_acc_no, new_acc_no, new_cust_id, new_balance, new_rate, new_created_date, chosen_asset_code="AST-102", new_op_bal_date=None):
    """
    Updates SB account details, customer assignment, balance, rate, account opening date, and opening balance date,
    and automatically synchronizes linked transactions, Journal Vouchers, Cash Book, and Bank Book entries,
    recalculating running balances and resequencing chronologically.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        placeholder = "%s" if USING_SUPABASE else "?"
        
        # 1. Fetch customer name
        cursor.execute(f"SELECT name FROM customers WHERE id = {placeholder}", (new_cust_id,))
        c_row = cursor.fetchone()
        cust_name = c_row[0] if c_row else "Customer"
        
        created_dt_str = str(new_created_date)[:10]
        op_bal_dt_str = str(new_op_bal_date)[:10] if new_op_bal_date else created_dt_str
        today_time = f"{op_bal_dt_str} 12:00"
        
        # 2. Update sb_accounts (stores A/c Opening Date)
        cursor.execute(f"""
            UPDATE sb_accounts 
            SET account_no = {placeholder}, customer_id = {placeholder}, balance = {placeholder}, interest_rate = {placeholder}, created_at = {placeholder}
            WHERE account_no = {placeholder}
        """, (new_acc_no, new_cust_id, new_balance, new_rate, created_dt_str, old_acc_no))
        
        # 3. Update accounts table
        cursor.execute(f"""
            UPDATE accounts 
            SET account_number = {placeholder}, customer_id = {placeholder}, balance = {placeholder}, created_at = {placeholder}
            WHERE account_number = {placeholder} OR (customer_id = {placeholder} AND account_type = 'Savings Account')
        """, (new_acc_no, new_cust_id, new_balance, created_dt_str, old_acc_no, new_cust_id))
        
        # 4. Update transactions table (account_no & date for opening deposit using Opening Balance Date)
        if new_acc_no != old_acc_no:
            cursor.execute(f"UPDATE transactions SET account_no = {placeholder} WHERE account_no = {placeholder}", (new_acc_no, old_acc_no))
        cursor.execute(f"""
            UPDATE transactions 
            SET date = {placeholder} 
            WHERE account_no = {placeholder} 
              AND (narration LIKE {placeholder} OR narration LIKE {placeholder} OR id = (SELECT MIN(id) FROM transactions WHERE account_no = {placeholder}))
        """, (op_bal_dt_str, new_acc_no, "%Opening%", "%Deposit%", new_acc_no))
            
        # 5. Locate existing Bank Book or Cash Book entry for this account
        cursor.execute(f"""
            SELECT id, voucher_no, particulars, account_code, bank_name 
            FROM bank_book 
            WHERE particulars LIKE {placeholder} OR particulars LIKE {placeholder} OR narration LIKE {placeholder} OR narration LIKE {placeholder}
            ORDER BY id ASC LIMIT 1
        """, (f"%{old_acc_no}%", f"%{new_acc_no}%", f"%{old_acc_no}%", f"%{new_acc_no}%"))
        existing_bb = cursor.fetchone()
        
        cursor.execute(f"""
            SELECT id, voucher_no, particulars, account_code 
            FROM cash_book 
            WHERE particulars LIKE {placeholder} OR particulars LIKE {placeholder} OR narration LIKE {placeholder} OR narration LIKE {placeholder}
            ORDER BY id ASC LIMIT 1
        """, (f"%{old_acc_no}%", f"%{new_acc_no}%", f"%{old_acc_no}%", f"%{new_acc_no}%"))
        existing_cb = cursor.fetchone()
        
        bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else ("State Bank of India" if chosen_asset_code == 'AST-103' else "Cash")
        
        if existing_bb:
            bb_id, bb_v_no, bb_part, bb_acc, bb_bname = existing_bb
            if chosen_asset_code in ('AST-102', 'AST-103'):
                cursor.execute(f"""
                    UPDATE bank_book 
                    SET date = {placeholder}, particulars = {placeholder}, debit_amount = {placeholder},
                        bank_name = {placeholder}, account_code = {placeholder}, narration = {placeholder}, created_at = {placeholder}
                    WHERE id = {placeholder}
                """, (op_bal_dt_str, f"SB Deposit: {new_acc_no} ({cust_name})", new_balance, bank_name, chosen_asset_code, f"SB Deposit - {new_acc_no}", today_time, bb_id))
            else:
                cursor.execute(f"DELETE FROM bank_book WHERE id = {placeholder}", (bb_id,))
                today_code = op_bal_dt_str.replace("-", "")
                cursor.execute(f"SELECT voucher_no FROM cash_book WHERE voucher_no LIKE {placeholder} ORDER BY id DESC LIMIT 1", (f"CB{today_code}%",))
                cb_res = cursor.fetchone()
                c_seq = int(cb_res[0][-4:]) + 1 if cb_res and cb_res[0] else 1
                c_voucher = f"CB{today_code}{c_seq:04d}"
                cursor.execute(f"""
                    INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 0, 0, 'AST-101', {placeholder}, {placeholder})
                """, (op_bal_dt_str, c_voucher, f"SB Deposit: {new_acc_no} ({cust_name})", new_balance, f"SB Deposit - {new_acc_no}", today_time))
                
            cursor.execute(f"""
                SELECT jv_id FROM journal_vouchers 
                WHERE narration LIKE {placeholder} OR narration LIKE {placeholder} OR narration LIKE {placeholder}
                ORDER BY jv_id DESC LIMIT 1
            """, (f"%{bb_v_no}%", f"%{old_acc_no}%", f"%{new_acc_no}%"))
            jv_row = cursor.fetchone()
            if jv_row:
                jv_id = jv_row[0]
                cursor.execute(f"UPDATE journal_vouchers SET voucher_date = {placeholder}, narration = {placeholder} WHERE jv_id = {placeholder}",
                               (op_bal_dt_str, f"SB Deposit: {new_acc_no} ({cust_name})", jv_id))
                cursor.execute(f"UPDATE jv_entries SET account_code = {placeholder}, debit = {placeholder} WHERE jv_id = {placeholder} AND debit > 0", (chosen_asset_code, new_balance, jv_id))
                cursor.execute(f"UPDATE jv_entries SET account_code = 'LIA-101', credit = {placeholder} WHERE jv_id = {placeholder} AND credit > 0", (new_balance, jv_id))
                
        elif existing_cb:
            cb_id, cb_v_no, cb_part, cb_acc = existing_cb
            if chosen_asset_code == 'AST-101':
                cursor.execute(f"""
                    UPDATE cash_book 
                    SET date = {placeholder}, particulars = {placeholder}, debit_amount = {placeholder},
                        account_code = 'AST-101', narration = {placeholder}, created_at = {placeholder}
                    WHERE id = {placeholder}
                """, (op_bal_dt_str, f"SB Deposit: {new_acc_no} ({cust_name})", new_balance, f"SB Deposit - {new_acc_no}", today_time, cb_id))
            else:
                cursor.execute(f"DELETE FROM cash_book WHERE id = {placeholder}", (cb_id,))
                today_code = op_bal_dt_str.replace("-", "")
                cursor.execute(f"SELECT voucher_no FROM bank_book WHERE voucher_no LIKE {placeholder} ORDER BY id DESC LIMIT 1", (f"BB{today_code}%",))
                b_res = cursor.fetchone()
                b_seq = int(b_res[0][-4:]) + 1 if b_res and b_res[0] else 1
                b_voucher = f"BB{today_code}{b_seq:04d}"
                cursor.execute(f"""
                    INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 0, 0, {placeholder}, {placeholder}, {placeholder}, {placeholder})
                """, (op_bal_dt_str, b_voucher, f"SB Deposit: {new_acc_no} ({cust_name})", new_balance, bank_name, chosen_asset_code, f"SB Deposit - {new_acc_no}", today_time))
                
            cursor.execute(f"""
                SELECT jv_id FROM journal_vouchers 
                WHERE narration LIKE {placeholder} OR narration LIKE {placeholder} OR narration LIKE {placeholder}
                ORDER BY jv_id DESC LIMIT 1
            """, (f"%{cb_v_no}%", f"%{old_acc_no}%", f"%{new_acc_no}%"))
            jv_row = cursor.fetchone()
            if jv_row:
                jv_id = jv_row[0]
                cursor.execute(f"UPDATE journal_vouchers SET voucher_date = {placeholder}, narration = {placeholder} WHERE jv_id = {placeholder}",
                               (op_bal_dt_str, f"SB Deposit: {new_acc_no} ({cust_name})", jv_id))
                cursor.execute(f"UPDATE jv_entries SET account_code = {placeholder}, debit = {placeholder} WHERE jv_id = {placeholder} AND debit > 0", (chosen_asset_code, new_balance, jv_id))
                cursor.execute(f"UPDATE jv_entries SET account_code = 'LIA-101', credit = {placeholder} WHERE jv_id = {placeholder} AND credit > 0", (new_balance, jv_id))
                
        else:
            if new_balance > 0:
                today_code = op_bal_dt_str.replace("-", "")
                jv_narr = f"SB Deposit: {new_acc_no} ({cust_name})"
                if USING_SUPABASE:
                    cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (%s, %s, 'POSTED') RETURNING jv_id", (op_bal_dt_str, jv_narr))
                    jv_id = cursor.fetchone()[0]
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, %s, 0)", (jv_id, chosen_asset_code, new_balance))
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, 'LIA-101', 0, %s)", (jv_id, new_balance))
                else:
                    cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", (op_bal_dt_str, jv_narr))
                    jv_id = cursor.lastrowid
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, chosen_asset_code, new_balance))
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, 'LIA-101', 0, ?)", (jv_id, new_balance))
                    
                if chosen_asset_code in ('AST-102', 'AST-103'):
                    cursor.execute(f"SELECT voucher_no FROM bank_book WHERE voucher_no LIKE {placeholder} ORDER BY id DESC LIMIT 1", (f"BB{today_code}%",))
                    b_res = cursor.fetchone()
                    b_seq = int(b_res[0][-4:]) + 1 if b_res and b_res[0] else 1
                    b_voucher = f"BB{today_code}{b_seq:04d}"
                    cursor.execute(f"""
                        INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 0, 0, {placeholder}, {placeholder}, {placeholder}, {placeholder})
                    """, (str(new_created_date), b_voucher, f"SB Deposit: {new_acc_no} ({cust_name})", new_balance, bank_name, chosen_asset_code, f"SB Deposit - {new_acc_no}", today_time))
                else:
                    cursor.execute(f"SELECT voucher_no FROM cash_book WHERE voucher_no LIKE {placeholder} ORDER BY id DESC LIMIT 1", (f"CB{today_code}%",))
                    cb_res = cursor.fetchone()
                    c_seq = int(cb_res[0][-4:]) + 1 if cb_res and cb_res[0] else 1
                    c_voucher = f"CB{today_code}{c_seq:04d}"
                    cursor.execute(f"""
                        INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 0, 0, 'AST-101', {placeholder}, {placeholder})
                    """, (str(new_created_date), c_voucher, f"SB Deposit: {new_acc_no} ({cust_name})", new_balance, f"SB Deposit - {new_acc_no}", today_time))

        if new_acc_no != old_acc_no:
            cursor.execute(f"UPDATE bank_book SET particulars = REPLACE(particulars, {placeholder}, {placeholder}), narration = REPLACE(narration, {placeholder}, {placeholder}) WHERE particulars LIKE {placeholder} OR narration LIKE {placeholder}", (old_acc_no, new_acc_no, old_acc_no, new_acc_no, f"%{old_acc_no}%", f"%{old_acc_no}%"))
            cursor.execute(f"UPDATE cash_book SET particulars = REPLACE(particulars, {placeholder}, {placeholder}), narration = REPLACE(narration, {placeholder}, {placeholder}) WHERE particulars LIKE {placeholder} OR narration LIKE {placeholder}", (old_acc_no, new_acc_no, old_acc_no, new_acc_no, f"%{old_acc_no}%", f"%{old_acc_no}%"))
            cursor.execute(f"UPDATE journal_vouchers SET narration = REPLACE(narration, {placeholder}, {placeholder}) WHERE narration LIKE {placeholder}", (old_acc_no, new_acc_no, f"%{old_acc_no}%"))

        # Recalculate Bank Book cumulative running balances
        cursor.execute("SELECT id, debit_amount, credit_amount FROM bank_book ORDER BY date ASC, id ASC")
        rows = cursor.fetchall()
        running_bal = 0.0
        for r_id, dr, cr in rows:
            dr = float(dr or 0.0)
            cr = float(cr or 0.0)
            running_bal += (dr - cr)
            cursor.execute(f"UPDATE bank_book SET balance = {placeholder} WHERE id = {placeholder}", (round(running_bal, 2), r_id))

        conn.commit()
        resequence_cash_book()
        resequence_bank_book()
        clear_db_cache()
        return True, f"SB Account {new_acc_no} updated and synchronized with Bank/Cash Book and Journal Vouchers successfully."
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


def create_or_link_sb_opening(cust_id, initial_balance, open_date, interest_rate=3.5, chosen_asset_code="AST-102", op_bal_date=None):
    """
    Creates a new Savings Bank (SB) account with opening balance for an existing customer,
    generates opening JV (Dr Asset, Cr LIA-101), posts into Cash/Bank book, and transactions table.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        placeholder = "%s" if USING_SUPABASE else "?"

        cursor.execute(f"SELECT name, COALESCE(account_no, '') FROM customers WHERE id = {placeholder}", (cust_id,))
        c_row = cursor.fetchone()
        if not c_row:
            return False, "Customer not found."
        cust_name, cust_acc = c_row

        initial_balance = float(initial_balance or 0.0)
        open_date_str = str(open_date)[:10]
        op_bal_date_str = str(op_bal_date)[:10] if op_bal_date else open_date_str
        sb_acc_no = f"SB{datetime.now(IST).strftime('%Y%m%d%H%M%S')}"

        cursor.execute(f"""
            INSERT INTO sb_accounts (account_no, customer_id, balance, interest_rate, created_at)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
        """, (sb_acc_no, cust_id, initial_balance, float(interest_rate or 3.5), open_date_str))

        cursor.execute(f"""
            INSERT INTO accounts (account_number, account_type, customer_id, balance, created_at)
            VALUES ({placeholder}, 'Savings Account', {placeholder}, {placeholder}, {placeholder})
        """, (sb_acc_no, cust_id, initial_balance, open_date_str))

        pay_mode = "Union Bank of India" if chosen_asset_code == "AST-102" else ("State Bank of India" if chosen_asset_code == "AST-103" else "Cash")

        if initial_balance > 0:
            tx_id = f"TX{datetime.now(IST).strftime('%M%S%f')}"
            cursor.execute(f"""
                INSERT INTO transactions (tx_id, account_no, type, amount, mode, narration, date)
                VALUES ({placeholder}, {placeholder}, 'CREDIT', {placeholder}, {placeholder}, 'SB Opening Balance Deposit', {placeholder})
            """, (tx_id, sb_acc_no, initial_balance, pay_mode, op_bal_date_str))

            post_automated_jv(f"SB Opening Balance - Account {sb_acc_no} ({cust_name})", chosen_asset_code, "LIA-101", initial_balance, voucher_date=op_bal_date_str)

            today_time = f"{op_bal_date_str} 10:00"
            if chosen_asset_code == 'AST-101':
                v_no = generate_cash_voucher_no()
                cursor.execute(f"""
                    INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 0, 0, 'AST-101', {placeholder}, {placeholder})
                """, (op_bal_date_str, v_no, f"SB Opening Deposit: {sb_acc_no} ({cust_name})", initial_balance, f"SB Opening Balance - {sb_acc_no}", today_time))
            else:
                b_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
                v_no = generate_bank_voucher_no()
                cursor.execute(f"""
                    INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 0, 0, {placeholder}, {placeholder}, {placeholder}, {placeholder})
                """, (op_bal_date_str, v_no, f"SB Opening Deposit: {sb_acc_no} ({cust_name})", initial_balance, b_name, chosen_asset_code, f"SB Opening Balance - {sb_acc_no}", today_time))

        conn.commit()
        resequence_cash_book()
        resequence_bank_book()
        clear_db_cache()
        return True, f"Savings Bank account {sb_acc_no} created successfully for {cust_name} with opening balance ₹{initial_balance:,.2f} on {open_date_str}."
    except Exception as e:
        if conn and USING_SUPABASE:
            try: conn.rollback()
            except Exception: pass
        return False, str(e)
    finally:
        release_connection(conn)


def update_personal_loan_details(
    pl_id, new_l_no, new_sanction_date, new_princ, new_rate, new_tenure_days,
    new_out_due, new_disbursal_mode, new_guar_name, new_guar_phone, new_guar_rel,
    new_guar_addr, new_purpose, new_status, new_remarks, new_op_bal_date=None
):
    """
    Updates Personal Loan financial terms, borrower & guarantor metadata,
    recalculates EMI amortization schedule, updates customer account balance,
    and synchronizes disbursal Journal Voucher, Cash Book, and Bank Book entries with resequenced running balances.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        placeholder = "%s" if USING_SUPABASE else "?"
        
        # 1. Fetch current loan details & borrower name
        cursor.execute(f"""
            SELECT p.loan_no, p.customer_id, c.name, COALESCE(c.account_no, ''), p.voucher_no, p.principal_amount, p.disbursal_mode
            FROM personal_loans p
            JOIN customers c ON p.customer_id = c.id
            WHERE p.id = {placeholder}
        """, (pl_id,))
        p_row = cursor.fetchone()
        if not p_row:
            return False, "Personal Loan not found."
            
        old_l_no, cust_id, cust_name, cust_acc, old_v_no, old_princ, old_d_mode = p_row
        old_v_no = old_v_no or f"PLV{pl_id:04d}"
        
        new_princ = float(new_princ)
        new_rate = float(new_rate)
        new_tenure_days = int(new_tenure_days)
        new_tenure_months = max(1, int(round(new_tenure_days / 30.0)))
        
        calc_tot_interest = round(new_princ * (new_rate / 100.0) * (new_tenure_days / 365.0), 2)
        calc_tot_repayable = round(new_princ + calc_tot_interest, 2)
        calc_p_emi = round(new_princ / float(new_tenure_months), 2)
        calc_i_emi = round(calc_tot_interest / float(new_tenure_months), 2)
        calc_installment = round(calc_tot_repayable / float(new_tenure_months), 2)
        
        new_scheme_name = f"{new_tenure_days}-Day Loan"
        
        # Schedules calculation
        ed_sched = generate_loan_schedule(new_sanction_date, new_princ, calc_tot_interest, tenure_months=new_tenure_months, loan_type='PERSONAL')
        ed_loan_from = ed_sched[0]["from_date"] if ed_sched else str(new_sanction_date)
        ed_loan_to = ed_sched[-1]["to_date"] if ed_sched else str(new_sanction_date)
        ed_first_due = ed_sched[0]["due_date"] if ed_sched else str(new_sanction_date)
        ed_last_due = ed_sched[-1]["due_date"] if ed_sched else str(new_sanction_date)
        
        # 2. Update personal_loans table
        cursor.execute(f"""
            UPDATE personal_loans
            SET loan_no = {placeholder}, sanction_date = {placeholder}, principal_amount = {placeholder}, interest_rate = {placeholder},
                interest_type = {placeholder}, tenure_days = {placeholder}, tenure_months = {placeholder}, total_interest = {placeholder},
                total_repayable = {placeholder}, installment_amount = {placeholder}, monthly_principal_emi = {placeholder},
                monthly_interest_emi = {placeholder}, loan_from_date = {placeholder}, loan_to_date = {placeholder},
                first_emi_due = {placeholder}, last_emi_due = {placeholder}, outstanding_due = {placeholder}, disbursal_mode = {placeholder},
                guarantor_name = {placeholder}, guarantor_phone = {placeholder}, guarantor_relation = {placeholder},
                guarantor_address = {placeholder}, purpose = {placeholder}, status = {placeholder}, remarks = {placeholder}
            WHERE id = {placeholder}
        """, (
            new_l_no, str(new_sanction_date), new_princ, new_rate,
            new_scheme_name, new_tenure_days, new_tenure_months, calc_tot_interest,
            calc_tot_repayable, calc_installment, calc_p_emi,
            calc_i_emi, ed_loan_from, ed_loan_to,
            ed_first_due, ed_last_due, new_out_due, new_disbursal_mode,
            new_guar_name, new_guar_phone, new_guar_rel,
            new_guar_addr, new_purpose, new_status, new_remarks,
            pl_id
        ))
        
        # 3. Update customer accounts table
        cursor.execute(f"""
            UPDATE accounts 
            SET balance = {placeholder} 
            WHERE customer_id = {placeholder} AND (account_type = 'Loan Account' OR account_number = {placeholder})
        """, (new_out_due, cust_id, cust_acc))
        
        # 4. Regenerate pending schedules
        cursor.execute(f"DELETE FROM loan_emi_schedules WHERE loan_type = 'PERSONAL' AND loan_id = {placeholder} AND status = 'PENDING'", (pl_id,))
        cursor.execute(f"SELECT emi_number FROM loan_emi_schedules WHERE loan_type = 'PERSONAL' AND loan_id = {placeholder} AND status = 'PAID'", (pl_id,))
        paid_emis = set(r[0] for r in cursor.fetchall())
        pending_schedules = [s for s in ed_sched if s['emi_number'] not in paid_emis]
        for sch in pending_schedules:
            cursor.execute(f"""
                INSERT INTO loan_emi_schedules (
                    loan_type, loan_id, loan_no, emi_number, from_date, to_date, due_date,
                    principal_component, interest_component, emi_amount, status
                ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, 'PENDING')
            """, (
                'PERSONAL', pl_id, new_l_no, sch['emi_number'],
                sch['from_date'], sch['to_date'], sch['due_date'],
                sch['principal_component'], sch['interest_component'], sch['emi_amount']
            ))
            
        # 5. Synchronize Disbursal Journal Voucher & Cash / Bank Book
        op_bal_date_str = str(new_op_bal_date) if new_op_bal_date else str(new_sanction_date)
        chosen_asset_code = 'AST-101' if 'cash' in new_disbursal_mode.lower() else ('AST-103' if 'state bank' in new_disbursal_mode.lower() or 'sbi' in new_disbursal_mode.lower() else 'AST-102')
        bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else ("State Bank of India" if chosen_asset_code == 'AST-103' else "Cash")
        today_time = f"{op_bal_date_str} 12:00"
        
        # Locate existing JV
        cursor.execute(f"""
            SELECT jv_id FROM journal_vouchers 
            WHERE narration LIKE {placeholder} OR narration LIKE {placeholder} OR narration LIKE {placeholder}
            ORDER BY jv_id DESC LIMIT 1
        """, (f"%Personal Loan Disbursal%{old_l_no}%", f"%Personal Loan Disbursal%{new_l_no}%", f"%{old_v_no}%"))
        jv_res = cursor.fetchone()
        
        if jv_res:
            jv_id = jv_res[0]
            cursor.execute(f"UPDATE journal_vouchers SET voucher_date = {placeholder}, narration = {placeholder} WHERE jv_id = {placeholder}",
                           (op_bal_date_str, f"Personal Loan Disbursal - {cust_name} ({new_l_no})", jv_id))
            cursor.execute(f"UPDATE jv_entries SET account_code = 'AST-108', debit = {placeholder} WHERE jv_id = {placeholder} AND debit > 0", (new_princ, jv_id))
            cursor.execute(f"UPDATE jv_entries SET account_code = {placeholder}, credit = {placeholder} WHERE jv_id = {placeholder} AND credit > 0", (chosen_asset_code, new_princ, jv_id))
        else:
            if new_princ > 0:
                if USING_SUPABASE:
                    cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (%s, %s, 'POSTED') RETURNING jv_id", (op_bal_date_str, f"Personal Loan Disbursal - {cust_name} ({new_l_no})"))
                    jv_id = cursor.fetchone()[0]
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, 'AST-108', %s, 0)", (jv_id, new_princ))
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, 0, %s)", (jv_id, chosen_asset_code, new_princ))
                else:
                    cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", (op_bal_date_str, f"Personal Loan Disbursal - {cust_name} ({new_l_no})"))
                    jv_id = cursor.lastrowid
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, 'AST-108', ?, 0)", (jv_id, new_princ))
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, chosen_asset_code, new_princ))
                    
        # Locate existing Cash / Bank Book entry
        cursor.execute(f"""
            SELECT id FROM bank_book 
            WHERE particulars LIKE {placeholder} OR particulars LIKE {placeholder} OR narration LIKE {placeholder} OR narration LIKE {placeholder}
            ORDER BY id ASC LIMIT 1
        """, (f"%Personal Loan Disbursal%{old_l_no}%", f"%Personal Loan Disbursal%{new_l_no}%", f"%{old_l_no}%", f"%{old_v_no}%"))
        bb_row = cursor.fetchone()
        
        cursor.execute(f"""
            SELECT id FROM cash_book 
            WHERE particulars LIKE {placeholder} OR particulars LIKE {placeholder} OR narration LIKE {placeholder} OR narration LIKE {placeholder}
            ORDER BY id ASC LIMIT 1
        """, (f"%Personal Loan Disbursal%{old_l_no}%", f"%Personal Loan Disbursal%{new_l_no}%", f"%{old_l_no}%", f"%{old_v_no}%"))
        cb_row = cursor.fetchone()
        
        if bb_row:
            bb_id = bb_row[0]
            if chosen_asset_code in ('AST-102', 'AST-103'):
                cursor.execute(f"""
                    UPDATE bank_book 
                    SET date = {placeholder}, particulars = {placeholder}, credit_amount = {placeholder},
                        bank_name = {placeholder}, account_code = 'AST-108', narration = {placeholder}, created_at = {placeholder}
                    WHERE id = {placeholder}
                """, (op_bal_date_str, f"Personal Loan Disbursal: {cust_acc} ({cust_name}) [{new_l_no}]", new_princ, bank_name, f"Opening Personal Loan Disbursal - {new_l_no}", today_time, bb_id))
            else:
                cursor.execute(f"DELETE FROM bank_book WHERE id = {placeholder}", (bb_id,))
                c_voucher = generate_cash_voucher_no()
                cursor.execute(f"""
                    INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, 0, {placeholder}, 0, 'AST-108', {placeholder}, {placeholder})
                """, (op_bal_date_str, c_voucher, f"Personal Loan Disbursal: {cust_acc} ({cust_name}) [{new_l_no}]", new_princ, f"Opening Personal Loan Disbursal - {new_l_no}", today_time))
        elif cb_row:
            cb_id = cb_row[0]
            if chosen_asset_code == 'AST-101':
                cursor.execute(f"""
                    UPDATE cash_book 
                    SET date = {placeholder}, particulars = {placeholder}, credit_amount = {placeholder},
                        account_code = 'AST-108', narration = {placeholder}, created_at = {placeholder}
                    WHERE id = {placeholder}
                """, (op_bal_date_str, f"Personal Loan Disbursal: {cust_acc} ({cust_name}) [{new_l_no}]", new_princ, f"Opening Personal Loan Disbursal - {new_l_no}", today_time, cb_id))
            else:
                cursor.execute(f"DELETE FROM cash_book WHERE id = {placeholder}", (cb_id,))
                b_voucher = generate_bank_voucher_no()
                cursor.execute(f"""
                    INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, 0, {placeholder}, 0, {placeholder}, 'AST-108', {placeholder}, {placeholder})
                """, (op_bal_date_str, b_voucher, f"Personal Loan Disbursal: {cust_acc} ({cust_name}) [{new_l_no}]", new_princ, bank_name, f"Opening Personal Loan Disbursal - {new_l_no}", today_time))
        else:
            if new_princ > 0:
                if chosen_asset_code in ('AST-102', 'AST-103'):
                    b_voucher = generate_bank_voucher_no()
                    cursor.execute(f"""
                        INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                        VALUES ({placeholder}, {placeholder}, {placeholder}, 0, {placeholder}, 0, {placeholder}, 'AST-108', {placeholder}, {placeholder})
                    """, (op_bal_date_str, b_voucher, f"Personal Loan Disbursal: {cust_acc} ({cust_name}) [{new_l_no}]", new_princ, bank_name, f"Opening Personal Loan Disbursal - {new_l_no}", today_time))
                else:
                    c_voucher = generate_cash_voucher_no()
                    cursor.execute(f"""
                        INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                        VALUES ({placeholder}, {placeholder}, {placeholder}, 0, {placeholder}, 0, 'AST-108', {placeholder}, {placeholder})
                    """, (op_bal_date_str, c_voucher, f"Personal Loan Disbursal: {cust_acc} ({cust_name}) [{new_l_no}]", new_princ, f"Opening Personal Loan Disbursal - {new_l_no}", today_time))
                    
        conn.commit()
        resequence_cash_book()
        resequence_bank_book()
        
        return True, f"Personal Loan #{new_l_no} updated and synchronized with schedules, ledgers, and books successfully."
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


def update_gold_loan_details(
    gl_id, new_l_no, new_sanction_date, new_princ, new_rate, new_tenure_days,
    new_out_due, new_disbursal_mode, new_gold_rate, new_orn_desc, new_item_cnt,
    new_gross_wt, new_stone_ded, new_pkt_no, new_locker_no, new_appr_name,
    new_status, new_remarks, new_photo_bytes=None, new_photo_name=None, new_op_bal_date=None
):
    """
    Updates Gold Loan terms, collateral appraisal, weight & valuation,
    recalculates EMI amortization schedule, updates customer account balance,
    and synchronizes disbursal Journal Voucher, Cash Book, and Bank Book entries with resequenced running balances.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        placeholder = "%s" if USING_SUPABASE else "?"
        
        # 1. Fetch current loan details & borrower name
        cursor.execute(f"""
            SELECT g.loan_no, g.customer_id, c.name, COALESCE(c.account_no, ''), g.voucher_no, g.principal_amount, g.disbursal_mode
            FROM gold_loans g
            JOIN customers c ON g.customer_id = c.id
            WHERE g.id = {placeholder}
        """, (gl_id,))
        g_row = cursor.fetchone()
        if not g_row:
            return False, "Gold Loan not found."
            
        old_l_no, cust_id, cust_name, cust_acc, old_v_no, old_princ, old_d_mode = g_row
        old_v_no = old_v_no or f"GLV{gl_id:04d}"
        
        new_princ = float(new_princ)
        new_rate = float(new_rate)
        new_tenure_days = int(new_tenure_days)
        new_tenure_months = max(1, int(round(new_tenure_days / 30.0)))
        
        ed_net_wt = max(0.01, round(float(new_gross_wt) - float(new_stone_ded), 3))
        ed_market_val = round(ed_net_wt * float(new_gold_rate), 2)
        
        calc_gl_interest = round(new_princ * (new_rate / 100.0) * (new_tenure_days / 365.0), 2)
        calc_gl_repayable = round(new_princ + calc_gl_interest, 2)
        calc_gl_p_emi = round(new_princ / float(new_tenure_months), 2)
        calc_gl_i_emi = round(calc_gl_interest / float(new_tenure_months), 2)
        calc_gl_installment = round(calc_gl_repayable / float(new_tenure_months), 2)
        
        # Schedules calculation
        ed_gl_sched = generate_loan_schedule(new_sanction_date, new_princ, calc_gl_interest, tenure_months=new_tenure_months, loan_type='GOLD')
        ed_loan_from = ed_gl_sched[0]["from_date"] if ed_gl_sched else str(new_sanction_date)
        ed_loan_to = ed_gl_sched[-1]["to_date"] if ed_gl_sched else str(new_sanction_date)
        ed_first_due = ed_gl_sched[0]["due_date"] if ed_gl_sched else str(new_sanction_date)
        ed_last_due = ed_gl_sched[-1]["due_date"] if ed_gl_sched else str(new_sanction_date)
        
        # Update photo if provided
        if new_photo_bytes:
            import psycopg2
            u_param = psycopg2.Binary(new_photo_bytes) if (USING_SUPABASE and new_photo_bytes) else new_photo_bytes
            cursor.execute(f"UPDATE gold_loans SET gold_image_file = {placeholder}, gold_image_data = {placeholder} WHERE id = {placeholder}", (new_photo_name, u_param, gl_id))
            
        # 2. Update gold_loans table
        cursor.execute(f"""
            UPDATE gold_loans
            SET loan_no = {placeholder}, sanction_date = {placeholder}, gold_rate_per_gram = {placeholder}, ornament_details = {placeholder},
                item_count = {placeholder}, gross_weight = {placeholder}, stone_deduction = {placeholder}, net_weight = {placeholder},
                market_value = {placeholder}, principal_amount = {placeholder}, interest_rate = {placeholder},
                interest_rate_monthly = {placeholder}, tenure_days = {placeholder}, tenure_months = {placeholder}, total_interest = {placeholder},
                total_repayable = {placeholder}, installment_amount = {placeholder}, monthly_principal_emi = {placeholder},
                monthly_interest_emi = {placeholder}, monthly_interest_due = {placeholder},
                loan_from_date = {placeholder}, loan_to_date = {placeholder}, first_emi_due = {placeholder}, last_emi_due = {placeholder},
                outstanding_due = {placeholder}, vault_packet_no = {placeholder}, locker_no = {placeholder},
                appraiser_name = {placeholder}, disbursal_mode = {placeholder}, status = {placeholder}, remarks = {placeholder}
            WHERE id = {placeholder}
        """, (
            new_l_no, str(new_sanction_date), new_gold_rate, new_orn_desc,
            new_item_cnt, new_gross_wt, new_stone_ded, ed_net_wt,
            ed_market_val, new_princ, new_rate,
            round(new_rate / 12.0, 2), new_tenure_days, new_tenure_months, calc_gl_interest,
            calc_gl_repayable, calc_gl_installment, calc_gl_p_emi,
            calc_gl_i_emi, calc_gl_i_emi,
            ed_loan_from, ed_loan_to, ed_first_due, ed_last_due,
            new_out_due, new_pkt_no, new_locker_no,
            new_appr_name, new_disbursal_mode, new_status, new_remarks,
            gl_id
        ))
        
        # 3. Update customer accounts table
        cursor.execute(f"""
            UPDATE accounts 
            SET balance = {placeholder} 
            WHERE customer_id = {placeholder} AND (account_type = 'Loan Account' OR account_number = {placeholder})
        """, (new_out_due, cust_id, cust_acc))
        
        # 4. Regenerate pending schedules
        cursor.execute(f"DELETE FROM loan_emi_schedules WHERE loan_type = 'GOLD' AND loan_id = {placeholder} AND status = 'PENDING'", (gl_id,))
        cursor.execute(f"SELECT emi_number FROM loan_emi_schedules WHERE loan_type = 'GOLD' AND loan_id = {placeholder} AND status = 'PAID'", (gl_id,))
        paid_emis = set(r[0] for r in cursor.fetchall())
        pending_schedules = [s for s in ed_gl_sched if s['emi_number'] not in paid_emis]
        for sch in pending_schedules:
            cursor.execute(f"""
                INSERT INTO loan_emi_schedules (
                    loan_type, loan_id, loan_no, emi_number, from_date, to_date, due_date,
                    principal_component, interest_component, emi_amount, status
                ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, 'PENDING')
            """, (
                'GOLD', gl_id, new_l_no, sch['emi_number'],
                sch['from_date'], sch['to_date'], sch['due_date'],
                sch['principal_component'], sch['interest_component'], sch['emi_amount']
            ))
            
        # 5. Synchronize Disbursal Journal Voucher & Cash / Bank Book
        op_bal_date_str = str(new_op_bal_date) if new_op_bal_date else str(new_sanction_date)
        chosen_asset_code = 'AST-101' if 'cash' in new_disbursal_mode.lower() else ('AST-103' if 'state bank' in new_disbursal_mode.lower() or 'sbi' in new_disbursal_mode.lower() else 'AST-102')
        bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else ("State Bank of India" if chosen_asset_code == 'AST-103' else "Cash")
        today_time = f"{op_bal_date_str} 12:00"
        
        # Locate existing JV
        cursor.execute(f"""
            SELECT jv_id FROM journal_vouchers 
            WHERE narration LIKE {placeholder} OR narration LIKE {placeholder} OR narration LIKE {placeholder}
            ORDER BY jv_id DESC LIMIT 1
        """, (f"%Gold Loan Disbursal%{old_l_no}%", f"%Gold Loan Disbursal%{new_l_no}%", f"%{old_v_no}%"))
        jv_res = cursor.fetchone()
        
        if jv_res:
            jv_id = jv_res[0]
            cursor.execute(f"UPDATE journal_vouchers SET voucher_date = {placeholder}, narration = {placeholder} WHERE jv_id = {placeholder}",
                           (op_bal_date_str, f"Gold Loan Disbursal - {cust_name} ({new_l_no})", jv_id))
            cursor.execute(f"UPDATE jv_entries SET account_code = 'AST-110', debit = {placeholder} WHERE jv_id = {placeholder} AND debit > 0", (new_princ, jv_id))
            cursor.execute(f"UPDATE jv_entries SET account_code = {placeholder}, credit = {placeholder} WHERE jv_id = {placeholder} AND credit > 0", (chosen_asset_code, new_princ, jv_id))
        else:
            if new_princ > 0:
                if USING_SUPABASE:
                    cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (%s, %s, 'POSTED') RETURNING jv_id", (op_bal_date_str, f"Gold Loan Disbursal - {cust_name} ({new_l_no})"))
                    jv_id = cursor.fetchone()[0]
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, 'AST-110', %s, 0)", (jv_id, new_princ))
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, 0, %s)", (jv_id, chosen_asset_code, new_princ))
                else:
                    cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", (op_bal_date_str, f"Gold Loan Disbursal - {cust_name} ({new_l_no})"))
                    jv_id = cursor.lastrowid
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, 'AST-110', ?, 0)", (jv_id, new_princ))
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, chosen_asset_code, new_princ))
                    
        # Locate existing Cash / Bank Book entry
        cursor.execute(f"""
            SELECT id FROM bank_book 
            WHERE particulars LIKE {placeholder} OR particulars LIKE {placeholder} OR narration LIKE {placeholder} OR narration LIKE {placeholder}
            ORDER BY id ASC LIMIT 1
        """, (f"%Gold Loan Disbursal%{old_l_no}%", f"%Gold Loan Disbursal%{new_l_no}%", f"%{old_l_no}%", f"%{old_v_no}%"))
        bb_row = cursor.fetchone()
        
        cursor.execute(f"""
            SELECT id FROM cash_book 
            WHERE particulars LIKE {placeholder} OR particulars LIKE {placeholder} OR narration LIKE {placeholder} OR narration LIKE {placeholder}
            ORDER BY id ASC LIMIT 1
        """, (f"%Gold Loan Disbursal%{old_l_no}%", f"%Gold Loan Disbursal%{new_l_no}%", f"%{old_l_no}%", f"%{old_v_no}%"))
        cb_row = cursor.fetchone()
        
        if bb_row:
            bb_id = bb_row[0]
            if chosen_asset_code in ('AST-102', 'AST-103'):
                cursor.execute(f"""
                    UPDATE bank_book 
                    SET date = {placeholder}, particulars = {placeholder}, credit_amount = {placeholder},
                        bank_name = {placeholder}, account_code = 'AST-110', narration = {placeholder}, created_at = {placeholder}
                    WHERE id = {placeholder}
                """, (op_bal_date_str, f"Gold Loan Disbursal: {cust_acc} ({cust_name}) [{new_l_no}]", new_princ, bank_name, f"Opening Gold Loan Disbursal - {new_l_no}", today_time, bb_id))
            else:
                cursor.execute(f"DELETE FROM bank_book WHERE id = {placeholder}", (bb_id,))
                c_voucher = generate_cash_voucher_no()
                cursor.execute(f"""
                    INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, 0, {placeholder}, 0, 'AST-110', {placeholder}, {placeholder})
                """, (op_bal_date_str, c_voucher, f"Gold Loan Disbursal: {cust_acc} ({cust_name}) [{new_l_no}]", new_princ, f"Opening Gold Loan Disbursal - {new_l_no}", today_time))
        elif cb_row:
            cb_id = cb_row[0]
            if chosen_asset_code == 'AST-101':
                cursor.execute(f"""
                    UPDATE cash_book 
                    SET date = {placeholder}, particulars = {placeholder}, credit_amount = {placeholder},
                        account_code = 'AST-110', narration = {placeholder}, created_at = {placeholder}
                    WHERE id = {placeholder}
                """, (op_bal_date_str, f"Gold Loan Disbursal: {cust_acc} ({cust_name}) [{new_l_no}]", new_princ, f"Opening Gold Loan Disbursal - {new_l_no}", today_time, cb_id))
            else:
                cursor.execute(f"DELETE FROM cash_book WHERE id = {placeholder}", (cb_id,))
                b_voucher = generate_bank_voucher_no()
                cursor.execute(f"""
                    INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, 0, {placeholder}, 0, {placeholder}, 'AST-110', {placeholder}, {placeholder})
                """, (op_bal_date_str, b_voucher, f"Gold Loan Disbursal: {cust_acc} ({cust_name}) [{new_l_no}]", new_princ, bank_name, f"Opening Gold Loan Disbursal - {new_l_no}", today_time))
        else:
            if new_princ > 0:
                if chosen_asset_code in ('AST-102', 'AST-103'):
                    b_voucher = generate_bank_voucher_no()
                    cursor.execute(f"""
                        INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                        VALUES ({placeholder}, {placeholder}, {placeholder}, 0, {placeholder}, 0, {placeholder}, 'AST-110', {placeholder}, {placeholder})
                    """, (op_bal_date_str, b_voucher, f"Gold Loan Disbursal: {cust_acc} ({cust_name}) [{new_l_no}]", new_princ, bank_name, f"Opening Gold Loan Disbursal - {new_l_no}", today_time))
                else:
                    c_voucher = generate_cash_voucher_no()
                    cursor.execute(f"""
                        INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                        VALUES ({placeholder}, {placeholder}, {placeholder}, 0, {placeholder}, 0, 'AST-110', {placeholder}, {placeholder})
                    """, (op_bal_date_str, c_voucher, f"Gold Loan Disbursal: {cust_acc} ({cust_name}) [{new_l_no}]", new_princ, f"Opening Gold Loan Disbursal - {new_l_no}", today_time))
                    
        conn.commit()
        resequence_cash_book()
        resequence_bank_book()
        
        return True, f"Gold Loan #{new_l_no} updated and synchronized with schedules, ledgers, and books successfully."
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


def create_or_link_personal_loan_opening(cust_id, princ_amount, sanction_date, tenure_days=100, int_rate=12.0, disbursal_mode="Union Bank of India", loan_no=None, remarks="Opening Loan Balance", op_bal_date=None):
    """
    Creates a new Personal Loan opening balance for an existing customer, generates 12-month schedule,
    posts Disbursal JV (AST-108), and logs Cash/Bank book entry.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        placeholder = "%s" if USING_SUPABASE else "?"
        
        cursor.execute(f"SELECT name, COALESCE(account_no, ''), phone FROM customers WHERE id = {placeholder}", (cust_id,))
        c_row = cursor.fetchone()
        if not c_row:
            return False, "Customer not found"
        cust_name, cust_acc, cust_phone = c_row
        
        pl_code = loan_no.strip() if loan_no and loan_no.strip() else f"PL-2026-{cust_id:04d}"
        s_date_str = str(sanction_date)
        op_bal_date_str = str(op_bal_date) if op_bal_date else s_date_str
        today_code = op_bal_date_str.replace("-", "")
        pl_vno = f"PLV{today_code}{cust_id:03d}"
        
        princ_amount = float(princ_amount)
        tenure_days = int(tenure_days)
        int_rate = float(int_rate)
        tenure_months = max(1, int(round(tenure_days / 30.0)))
        
        calc_tot_interest = round(princ_amount * (int_rate / 100.0) * (tenure_days / 365.0), 2)
        calc_tot_repayable = round(princ_amount + calc_tot_interest, 2)
        calc_p_emi = round(princ_amount / float(tenure_months), 2)
        calc_i_emi = round(calc_tot_interest / float(tenure_months), 2)
        calc_installment = round(calc_tot_repayable / float(tenure_months), 2)
        
        pl_sched = generate_loan_schedule(s_date_str, princ_amount, calc_tot_interest, tenure_months=tenure_months, loan_type='PERSONAL')
        loan_from = pl_sched[0]["from_date"] if pl_sched else s_date_str
        loan_to = pl_sched[-1]["to_date"] if pl_sched else s_date_str
        first_due = pl_sched[0]["due_date"] if pl_sched else s_date_str
        last_due = pl_sched[-1]["due_date"] if pl_sched else s_date_str
        
        if USING_SUPABASE:
            cursor.execute("""
                INSERT INTO personal_loans (
                    loan_no, customer_id, sanction_date, principal_amount, interest_rate,
                    interest_type, tenure_days, tenure_months, total_interest, total_repayable,
                    installment_amount, outstanding_due, disbursal_mode, voucher_no,
                    guarantor_name, guarantor_phone, purpose, status, remarks,
                    loan_from_date, loan_to_date, first_emi_due, last_emi_due,
                    monthly_principal_emi, monthly_interest_emi, renewal_count
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    'Member Surety', %s, 'Personal Loan', 'ACTIVE', %s,
                    %s, %s, %s, %s,
                    %s, %s, 0
                ) RETURNING id
            """, (
                pl_code, cust_id, s_date_str, princ_amount, int_rate,
                f"{tenure_days}-Day Loan", tenure_days, tenure_months, calc_tot_interest, calc_tot_repayable,
                calc_installment, calc_tot_repayable, disbursal_mode, pl_vno,
                cust_phone or 'N/A', remarks,
                loan_from, loan_to, first_due, last_due,
                calc_p_emi, calc_i_emi
            ))
            new_pl_id = cursor.fetchone()[0]
        else:
            cursor.execute("""
                INSERT INTO personal_loans (
                    loan_no, customer_id, sanction_date, principal_amount, interest_rate,
                    interest_type, tenure_days, tenure_months, total_interest, total_repayable,
                    installment_amount, outstanding_due, disbursal_mode, voucher_no,
                    guarantor_name, guarantor_phone, purpose, status, remarks,
                    loan_from_date, loan_to_date, first_emi_due, last_emi_due,
                    monthly_principal_emi, monthly_interest_emi, renewal_count
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    'Member Surety', ?, 'Personal Loan', 'ACTIVE', ?,
                    ?, ?, ?, ?,
                    ?, ?, 0
                )
            """, (
                pl_code, cust_id, s_date_str, princ_amount, int_rate,
                f"{tenure_days}-Day Loan", tenure_days, tenure_months, calc_tot_interest, calc_tot_repayable,
                calc_installment, calc_tot_repayable, disbursal_mode, pl_vno,
                cust_phone or 'N/A', remarks,
                loan_from, loan_to, first_due, last_due,
                calc_p_emi, calc_i_emi
            ))
            new_pl_id = cursor.lastrowid
            
        # Schedules
        for sch in pl_sched:
            cursor.execute(f"""
                INSERT INTO loan_emi_schedules (
                    loan_type, loan_id, loan_no, emi_number, from_date, to_date, due_date,
                    principal_component, interest_component, emi_amount, status
                ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, 'PENDING')
            """, (
                'PERSONAL', new_pl_id, pl_code, sch['emi_number'],
                sch['from_date'], sch['to_date'], sch['due_date'],
                sch['principal_component'], sch['interest_component'], sch['emi_amount']
            ))
            
        # Update accounts table
        cursor.execute(f"""
            UPDATE accounts SET balance = {placeholder} WHERE customer_id = {placeholder} AND account_type = 'Loan Account'
        """, (calc_tot_repayable, cust_id))
        
        # Disbursal JV and Cash/Bank book
        chosen_asset_code = 'AST-101' if 'cash' in disbursal_mode.lower() else ('AST-103' if 'state bank' in disbursal_mode.lower() or 'sbi' in disbursal_mode.lower() else 'AST-102')
        bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else ("State Bank of India" if chosen_asset_code == 'AST-103' else "Cash")
        today_time = f"{op_bal_date_str} 12:00"
        
        if USING_SUPABASE:
            cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (%s, %s, 'POSTED') RETURNING jv_id", (op_bal_date_str, f"Personal Loan Disbursal - {cust_name} ({pl_code})"))
            jv_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, 'AST-108', %s, 0)", (jv_id, princ_amount))
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, 0, %s)", (jv_id, chosen_asset_code, princ_amount))
        else:
            cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", (op_bal_date_str, f"Personal Loan Disbursal - {cust_name} ({pl_code})"))
            jv_id = cursor.lastrowid
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, 'AST-108', ?, 0)", (jv_id, princ_amount))
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, chosen_asset_code, princ_amount))
            
        if chosen_asset_code in ('AST-102', 'AST-103'):
            b_voucher = generate_bank_voucher_no()
            cursor.execute(f"""
                INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                VALUES ({placeholder}, {placeholder}, {placeholder}, 0, {placeholder}, 0, {placeholder}, 'AST-108', {placeholder}, {placeholder})
            """, (op_bal_date_str, b_voucher, f"Personal Loan Disbursal: {cust_acc} ({cust_name}) [{pl_code}]", princ_amount, bank_name, f"Opening Personal Loan Disbursal - {pl_code}", today_time))
        else:
            c_voucher = generate_cash_voucher_no()
            cursor.execute(f"""
                INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                VALUES ({placeholder}, {placeholder}, {placeholder}, 0, {placeholder}, 0, 'AST-108', {placeholder}, {placeholder})
            """, (op_bal_date_str, c_voucher, f"Personal Loan Disbursal: {cust_acc} ({cust_name}) [{pl_code}]", princ_amount, f"Opening Personal Loan Disbursal - {pl_code}", today_time))
            
        conn.commit()
        resequence_cash_book()
        resequence_bank_book()
        
        return True, f"Personal Loan #{pl_code} of ₹{princ_amount:,.2f} created and linked successfully."
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


def create_or_link_gold_loan_opening(cust_id, princ_amount, sanction_date, tenure_days=365, int_rate=12.0, disbursal_mode="Union Bank of India", loan_no=None, gold_rate=6500.0, net_weight=None, gross_weight=None, packet_no=None, locker_no="LOCKER-01", remarks="Opening Gold Loan Balance", op_bal_date=None):
    """
    Creates a new Gold Loan opening balance for an existing customer, creates collateral appraisal record,
    generates 12-month schedule, posts Disbursal JV (AST-110), and logs Cash/Bank book entry.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        placeholder = "%s" if USING_SUPABASE else "?"
        
        cursor.execute(f"SELECT name, COALESCE(account_no, ''), phone FROM customers WHERE id = {placeholder}", (cust_id,))
        c_row = cursor.fetchone()
        if not c_row:
            return False, "Customer not found"
        cust_name, cust_acc, cust_phone = c_row
        
        gl_code = loan_no.strip() if loan_no and loan_no.strip() else f"GL-2026-{cust_id:04d}"
        s_date_str = str(sanction_date)
        op_bal_date_str = str(op_bal_date) if op_bal_date else s_date_str
        today_code = op_bal_date_str.replace("-", "")
        gl_vno = f"GLV{today_code}{cust_id:03d}"
        
        princ_amount = float(princ_amount)
        tenure_days = int(tenure_days)
        int_rate = float(int_rate)
        tenure_months = max(1, int(round(tenure_days / 30.0)))
        gold_rate = float(gold_rate or 6500.0)
        
        calc_weight = float(net_weight) if net_weight else max(1.0, round(princ_amount / 5000.0, 3))
        calc_gross = float(gross_weight) if gross_weight else calc_weight
        calc_market_val = round(calc_weight * gold_rate, 2)
        
        calc_gl_interest = round(princ_amount * (int_rate / 100.0) * (tenure_days / 365.0), 2)
        calc_gl_repayable = round(princ_amount + calc_gl_interest, 2)
        calc_gl_p_emi = round(princ_amount / float(tenure_months), 2)
        calc_gl_i_emi = round(calc_gl_interest / float(tenure_months), 2)
        calc_gl_installment = round(calc_gl_repayable / float(tenure_months), 2)
        
        gl_sched = generate_loan_schedule(s_date_str, princ_amount, calc_gl_interest, tenure_months=tenure_months, loan_type='GOLD')
        loan_from = gl_sched[0]["from_date"] if gl_sched else s_date_str
        loan_to = gl_sched[-1]["to_date"] if gl_sched else s_date_str
        first_due = gl_sched[0]["due_date"] if gl_sched else s_date_str
        last_due = gl_sched[-1]["due_date"] if gl_sched else s_date_str
        pkt_val = packet_no or f"PKT-{cust_id:04d}"
        
        if USING_SUPABASE:
            cursor.execute("""
                INSERT INTO gold_loans (
                    loan_no, customer_id, sanction_date, gold_rate_per_gram, ornament_details,
                    item_count, gross_weight, stone_deduction, net_weight, purity,
                    market_value, ltv_percent, principal_amount, interest_rate,
                    interest_rate_monthly, tenure_days, tenure_months, total_interest, total_repayable,
                    installment_amount, monthly_principal_emi, monthly_interest_emi, monthly_interest_due,
                    loan_from_date, loan_to_date, first_emi_due, last_emi_due,
                    outstanding_due, vault_packet_no, locker_no, appraiser_name,
                    disbursal_mode, voucher_no, status, remarks, renewal_count
                ) VALUES (
                    %s, %s, %s, %s, 'Gold Ornaments (Opening Loan)',
                    1, %s, 0.0, %s, '22K',
                    %s, 75.0, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, 'Approved Nidhi Appraiser',
                    %s, %s, 'ACTIVE', %s, 0
                ) RETURNING id
            """, (
                gl_code, cust_id, s_date_str, gold_rate,
                calc_gross, calc_weight,
                calc_market_val, princ_amount, int_rate,
                round(int_rate / 12.0, 2), tenure_days, tenure_months, calc_gl_interest, calc_gl_repayable,
                calc_gl_installment, calc_gl_p_emi, calc_gl_i_emi, calc_gl_i_emi,
                loan_from, loan_to, first_due, last_due,
                calc_gl_repayable, pkt_val, locker_no,
                disbursal_mode, gl_vno, remarks
            ))
            new_gl_id = cursor.fetchone()[0]
        else:
            cursor.execute("""
                INSERT INTO gold_loans (
                    loan_no, customer_id, sanction_date, gold_rate_per_gram, ornament_details,
                    item_count, gross_weight, stone_deduction, net_weight, purity,
                    market_value, ltv_percent, principal_amount, interest_rate,
                    interest_rate_monthly, tenure_days, tenure_months, total_interest, total_repayable,
                    installment_amount, monthly_principal_emi, monthly_interest_emi, monthly_interest_due,
                    loan_from_date, loan_to_date, first_emi_due, last_emi_due,
                    outstanding_due, vault_packet_no, locker_no, appraiser_name,
                    disbursal_mode, voucher_no, status, remarks, renewal_count
                ) VALUES (
                    ?, ?, ?, ?, 'Gold Ornaments (Opening Loan)',
                    1, ?, 0.0, ?, '22K',
                    ?, 75.0, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, 'Approved Nidhi Appraiser',
                    ?, ?, 'ACTIVE', ?, 0
                )
            """, (
                gl_code, cust_id, s_date_str, gold_rate,
                calc_gross, calc_weight,
                calc_market_val, princ_amount, int_rate,
                round(int_rate / 12.0, 2), tenure_days, tenure_months, calc_gl_interest, calc_gl_repayable,
                calc_gl_installment, calc_gl_p_emi, calc_gl_i_emi, calc_gl_i_emi,
                loan_from, loan_to, first_due, last_due,
                calc_gl_repayable, pkt_val, locker_no,
                disbursal_mode, gl_vno, remarks
            ))
            new_gl_id = cursor.lastrowid
            
        # Schedules
        for sch in gl_sched:
            cursor.execute(f"""
                INSERT INTO loan_emi_schedules (
                    loan_type, loan_id, loan_no, emi_number, from_date, to_date, due_date,
                    principal_component, interest_component, emi_amount, status
                ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, 'PENDING')
            """, (
                'GOLD', new_gl_id, gl_code, sch['emi_number'],
                sch['from_date'], sch['to_date'], sch['due_date'],
                sch['principal_component'], sch['interest_component'], sch['emi_amount']
            ))
            
        # Update accounts table
        cursor.execute(f"""
            UPDATE accounts SET balance = {placeholder} WHERE customer_id = {placeholder} AND account_type = 'Loan Account'
        """, (calc_gl_repayable, cust_id))
        
        # Disbursal JV and Cash/Bank book
        chosen_asset_code = 'AST-101' if 'cash' in disbursal_mode.lower() else ('AST-103' if 'state bank' in disbursal_mode.lower() or 'sbi' in disbursal_mode.lower() else 'AST-102')
        bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else ("State Bank of India" if chosen_asset_code == 'AST-103' else "Cash")
        today_time = f"{op_bal_date_str} 12:00"
        
        if USING_SUPABASE:
            cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (%s, %s, 'POSTED') RETURNING jv_id", (op_bal_date_str, f"Gold Loan Disbursal - {cust_name} ({gl_code})"))
            jv_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, 'AST-110', %s, 0)", (jv_id, princ_amount))
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, 0, %s)", (jv_id, chosen_asset_code, princ_amount))
        else:
            cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", (op_bal_date_str, f"Gold Loan Disbursal - {cust_name} ({gl_code})"))
            jv_id = cursor.lastrowid
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, 'AST-110', ?, 0)", (jv_id, princ_amount))
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, chosen_asset_code, princ_amount))
            
        if chosen_asset_code in ('AST-102', 'AST-103'):
            b_voucher = generate_bank_voucher_no()
            cursor.execute(f"""
                INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                VALUES ({placeholder}, {placeholder}, {placeholder}, 0, {placeholder}, 0, {placeholder}, 'AST-110', {placeholder}, {placeholder})
            """, (op_bal_date_str, b_voucher, f"Gold Loan Disbursal: {cust_acc} ({cust_name}) [{gl_code}]", princ_amount, bank_name, f"Opening Gold Loan Disbursal - {gl_code}", today_time))
        else:
            c_voucher = generate_cash_voucher_no()
            cursor.execute(f"""
                INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                VALUES ({placeholder}, {placeholder}, {placeholder}, 0, {placeholder}, 0, 'AST-110', {placeholder}, {placeholder})
            """, (op_bal_date_str, c_voucher, f"Gold Loan Disbursal: {cust_acc} ({cust_name}) [{gl_code}]", princ_amount, f"Opening Gold Loan Disbursal - {gl_code}", today_time))
            
        conn.commit()
        resequence_cash_book()
        resequence_bank_book()
        
        return True, f"Gold Loan #{gl_code} of ₹{princ_amount:,.2f} created and linked successfully."
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


def resequence_customers():
    """Resequences all customers (1..N) and maps all child table customer_id references."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if USING_SUPABASE:
            cursor.execute("""
                DO $$
                DECLARE
                    rec RECORD;
                    new_id INT := 1;
                BEGIN
                    CREATE TEMP TABLE IF NOT EXISTS temp_cust_map (old_id INT, new_id INT) ON COMMIT DROP;
                    TRUNCATE temp_cust_map;
                    
                    FOR rec IN SELECT id FROM customers ORDER BY id ASC LOOP
                        INSERT INTO temp_cust_map VALUES (rec.id, new_id);
                        new_id := new_id + 1;
                    END LOOP;
                    
                    UPDATE sb_accounts SET customer_id = temp_cust_map.new_id FROM temp_cust_map WHERE sb_accounts.customer_id = temp_cust_map.old_id AND sb_accounts.customer_id != temp_cust_map.new_id;
                    UPDATE personal_loans SET customer_id = temp_cust_map.new_id FROM temp_cust_map WHERE personal_loans.customer_id = temp_cust_map.old_id AND personal_loans.customer_id != temp_cust_map.new_id;
                    UPDATE gold_loans SET customer_id = temp_cust_map.new_id FROM temp_cust_map WHERE gold_loans.customer_id = temp_cust_map.old_id AND gold_loans.customer_id != temp_cust_map.new_id;
                    UPDATE fixed_deposits SET customer_id = temp_cust_map.new_id FROM temp_cust_map WHERE fixed_deposits.customer_id = temp_cust_map.old_id AND fixed_deposits.customer_id != temp_cust_map.new_id;
                    UPDATE recurring_deposits SET customer_id = temp_cust_map.new_id FROM temp_cust_map WHERE recurring_deposits.customer_id = temp_cust_map.old_id AND recurring_deposits.customer_id != temp_cust_map.new_id;
                    UPDATE loan_repayments SET customer_id = temp_cust_map.new_id FROM temp_cust_map WHERE loan_repayments.customer_id = temp_cust_map.old_id AND loan_repayments.customer_id != temp_cust_map.new_id;
                    
                    UPDATE customers SET id = -id;
                    UPDATE customers SET id = temp_cust_map.new_id FROM temp_cust_map WHERE customers.id = -temp_cust_map.old_id;
                    
                    IF (SELECT COUNT(*) FROM customers) = 0 THEN
                        EXECUTE 'ALTER SEQUENCE customers_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('customers_id_seq', (SELECT MAX(id) FROM customers), true);
                    END IF;
                END $$;
            """)
        else:
            cursor.execute("SELECT id FROM customers ORDER BY id ASC")
            rows = cursor.fetchall()
            id_map = {old_id: new_id for new_id, (old_id,) in enumerate(rows, 1)}
            for old_id, new_id in id_map.items():
                if old_id != new_id:
                    cursor.execute("UPDATE sb_accounts SET customer_id = ? WHERE customer_id = ?", (new_id, old_id))
                    cursor.execute("UPDATE personal_loans SET customer_id = ? WHERE customer_id = ?", (new_id, old_id))
                    cursor.execute("UPDATE gold_loans SET customer_id = ? WHERE customer_id = ?", (new_id, old_id))
                    cursor.execute("UPDATE fixed_deposits SET customer_id = ? WHERE customer_id = ?", (new_id, old_id))
                    cursor.execute("UPDATE recurring_deposits SET customer_id = ? WHERE customer_id = ?", (new_id, old_id))
                    cursor.execute("UPDATE loan_repayments SET customer_id = ? WHERE customer_id = ?", (new_id, old_id))
            cursor.execute("UPDATE customers SET id = -id")
            for old_id, new_id in id_map.items():
                cursor.execute("UPDATE customers SET id = ? WHERE id = ?", (new_id, -old_id))
        conn.commit()
        return True, "Customers resequenced successfully."
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


def resequence_entire_database():
    """
    Master resequencer that re-indexes and aligns all tables across the entire banking system:
    Customers, Chart of Accounts, Journal Vouchers, JV Entries, Cash Book, Bank Book,
    Personal Loans, Gold Loans, Fixed Deposits, Recurring Deposits, Transactions,
    Loan Repayments, and EMI Schedules with 100% zero sequence gaps.
    """
    # 1. Resequence Chart of Accounts
    resequence_all_accounts()
    
    # 2. Resequence Customers
    resequence_customers()
    
    # 3. Resequence Cash Book & Bank Book
    resequence_cash_book()
    resequence_bank_book()
    
    # 4. Resequence Personal Loans, Gold Loans, Deposits, JVs, Transactions
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if USING_SUPABASE:
            cursor.execute("""
                DO $$
                DECLARE
                    rec RECORD;
                    new_id INT := 1;
                BEGIN
                    -- Resequence personal_loans
                    CREATE TEMP TABLE IF NOT EXISTS temp_pl_map (old_id INT, new_id INT) ON COMMIT DROP;
                    TRUNCATE temp_pl_map;
                    FOR rec IN SELECT id FROM personal_loans ORDER BY id ASC LOOP
                        INSERT INTO temp_pl_map VALUES (rec.id, new_id);
                        new_id := new_id + 1;
                    END LOOP;
                    UPDATE loan_emi_schedules SET loan_id = temp_pl_map.new_id FROM temp_pl_map WHERE loan_emi_schedules.loan_type = 'PERSONAL' AND loan_emi_schedules.loan_id = temp_pl_map.old_id AND loan_emi_schedules.loan_id != temp_pl_map.new_id;
                    UPDATE loan_repayments SET loan_id = temp_pl_map.new_id FROM temp_pl_map WHERE loan_repayments.loan_type = 'PERSONAL' AND loan_repayments.loan_id = temp_pl_map.old_id AND loan_repayments.loan_id != temp_pl_map.new_id;
                    UPDATE personal_loans SET id = -id;
                    UPDATE personal_loans SET id = temp_pl_map.new_id FROM temp_pl_map WHERE personal_loans.id = -temp_pl_map.old_id;
                    IF (SELECT COUNT(*) FROM personal_loans) = 0 THEN
                        EXECUTE 'ALTER SEQUENCE personal_loans_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('personal_loans_id_seq', (SELECT MAX(id) FROM personal_loans), true);
                    END IF;

                    -- Resequence gold_loans
                    new_id := 1;
                    CREATE TEMP TABLE IF NOT EXISTS temp_gl_map (old_id INT, new_id INT) ON COMMIT DROP;
                    TRUNCATE temp_gl_map;
                    FOR rec IN SELECT id FROM gold_loans ORDER BY id ASC LOOP
                        INSERT INTO temp_gl_map VALUES (rec.id, new_id);
                        new_id := new_id + 1;
                    END LOOP;
                    UPDATE loan_emi_schedules SET loan_id = temp_gl_map.new_id FROM temp_gl_map WHERE loan_emi_schedules.loan_type = 'GOLD' AND loan_emi_schedules.loan_id = temp_gl_map.old_id AND loan_emi_schedules.loan_id != temp_gl_map.new_id;
                    UPDATE loan_repayments SET loan_id = temp_gl_map.new_id FROM temp_gl_map WHERE loan_repayments.loan_type = 'GOLD' AND loan_repayments.loan_id = temp_gl_map.old_id AND loan_repayments.loan_id != temp_gl_map.new_id;
                    UPDATE gold_loans SET id = -id;
                    UPDATE gold_loans SET id = temp_gl_map.new_id FROM temp_gl_map WHERE gold_loans.id = -temp_gl_map.old_id;
                    IF (SELECT COUNT(*) FROM gold_loans) = 0 THEN
                        EXECUTE 'ALTER SEQUENCE gold_loans_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('gold_loans_id_seq', (SELECT MAX(id) FROM gold_loans), true);
                    END IF;

                    -- Resequence fixed_deposits
                    new_id := 1;
                    UPDATE fixed_deposits SET fd_id = -fd_id;
                    FOR rec IN SELECT fd_id FROM fixed_deposits ORDER BY -fd_id ASC LOOP
                        UPDATE fixed_deposits SET fd_id = new_id WHERE fd_id = rec.fd_id;
                        new_id := new_id + 1;
                    END LOOP;
                    IF (SELECT COUNT(*) FROM fixed_deposits) = 0 THEN
                        EXECUTE 'ALTER SEQUENCE fixed_deposits_fd_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('fixed_deposits_fd_id_seq', (SELECT MAX(fd_id) FROM fixed_deposits), true);
                    END IF;

                    -- Resequence recurring_deposits
                    new_id := 1;
                    UPDATE recurring_deposits SET rd_id = -rd_id;
                    FOR rec IN SELECT rd_id FROM recurring_deposits ORDER BY -rd_id ASC LOOP
                        UPDATE recurring_deposits SET rd_id = new_id WHERE rd_id = rec.rd_id;
                        new_id := new_id + 1;
                    END LOOP;
                    IF (SELECT COUNT(*) FROM recurring_deposits) = 0 THEN
                        EXECUTE 'ALTER SEQUENCE recurring_deposits_rd_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('recurring_deposits_rd_id_seq', (SELECT MAX(rd_id) FROM recurring_deposits), true);
                    END IF;

                    -- Resequence journal_vouchers & jv_entries
                    new_id := 1;
                    CREATE TEMP TABLE IF NOT EXISTS temp_jv_map (old_id INT, new_id INT) ON COMMIT DROP;
                    TRUNCATE temp_jv_map;
                    FOR rec IN SELECT jv_id FROM journal_vouchers ORDER BY voucher_date ASC, jv_id ASC LOOP
                        INSERT INTO temp_jv_map VALUES (rec.jv_id, new_id);
                        new_id := new_id + 1;
                    END LOOP;
                    CREATE TEMP TABLE IF NOT EXISTS temp_jv_entries_staged (
                        new_entry_id SERIAL,
                        new_jv_id INT,
                        account_code TEXT,
                        debit REAL,
                        credit REAL
                    ) ON COMMIT DROP;
                    TRUNCATE temp_jv_entries_staged;
                    INSERT INTO temp_jv_entries_staged (new_jv_id, account_code, debit, credit)
                    SELECT m.new_id, e.account_code, e.debit, e.credit
                    FROM jv_entries e
                    JOIN temp_jv_map m ON e.jv_id = m.old_id
                    ORDER BY m.new_id ASC, e.entry_id ASC;
                    DELETE FROM jv_entries;
                    UPDATE journal_vouchers SET jv_id = -jv_id;
                    UPDATE journal_vouchers SET jv_id = temp_jv_map.new_id FROM temp_jv_map WHERE journal_vouchers.jv_id = -temp_jv_map.old_id;
                    INSERT INTO jv_entries (entry_id, jv_id, account_code, debit, credit)
                    SELECT new_entry_id, new_jv_id, account_code, debit, credit FROM temp_jv_entries_staged;
                    IF (SELECT COUNT(*) FROM journal_vouchers) = 0 THEN
                        EXECUTE 'ALTER SEQUENCE journal_vouchers_jv_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('journal_vouchers_jv_id_seq', (SELECT MAX(jv_id) FROM journal_vouchers), true);
                    END IF;
                    IF (SELECT COUNT(*) FROM jv_entries) = 0 THEN
                        EXECUTE 'ALTER SEQUENCE jv_entries_entry_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('jv_entries_entry_id_seq', (SELECT MAX(entry_id) FROM jv_entries), true);
                    END IF;

                    -- Resequence transactions
                    new_id := 1;
                    UPDATE transactions SET id = -id;
                    FOR rec IN SELECT id FROM transactions ORDER BY -id ASC LOOP
                        UPDATE transactions SET id = new_id WHERE id = rec.id;
                        new_id := new_id + 1;
                    END LOOP;
                    IF (SELECT COUNT(*) FROM transactions) = 0 THEN
                        EXECUTE 'ALTER SEQUENCE transactions_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('transactions_id_seq', (SELECT MAX(id) FROM transactions), true);
                    END IF;

                    -- Resequence loan_repayments & loan_emi_schedules
                    new_id := 1;
                    UPDATE loan_repayments SET id = -id;
                    FOR rec IN SELECT id FROM loan_repayments ORDER BY -id ASC LOOP
                        UPDATE loan_repayments SET id = new_id WHERE id = rec.id;
                        new_id := new_id + 1;
                    END LOOP;
                    IF (SELECT COUNT(*) FROM loan_repayments) = 0 THEN
                        EXECUTE 'ALTER SEQUENCE loan_repayments_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('loan_repayments_id_seq', (SELECT MAX(id) FROM loan_repayments), true);
                    END IF;

                    new_id := 1;
                    UPDATE loan_emi_schedules SET id = -id;
                    FOR rec IN SELECT id FROM loan_emi_schedules ORDER BY -id ASC LOOP
                        UPDATE loan_emi_schedules SET id = new_id WHERE id = rec.id;
                        new_id := new_id + 1;
                    END LOOP;
                    IF (SELECT COUNT(*) FROM loan_emi_schedules) = 0 THEN
                        EXECUTE 'ALTER SEQUENCE loan_emi_schedules_id_seq RESTART WITH 1';
                    ELSE
                        PERFORM setval('loan_emi_schedules_id_seq', (SELECT MAX(id) FROM loan_emi_schedules), true);
                    END IF;
                END $$;
            """)
        
        conn.commit()
        sync_db_sequences()
        return True, "Entire database resequenced and all sequences synced successfully."
    except Exception as e:
        if conn and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, str(e)
    finally:
        release_connection(conn)


def update_fd_account_details(
    fd_id, new_cust_id, new_principal, new_tenure, new_rate,
    new_nominee, new_status, new_created_date, new_closed_date,
    new_pay_mode, chosen_asset_code='AST-102', new_op_bal_date=None,
    new_maturity_amount=None
):
    """
    Updates Fixed Deposit parameters (principal, tenure, interest rate, status, nominee, dates, payment mode)
    and synchronizes opening Journal Voucher (AST-101/102/103 vs LIA-102), Cash Book, and Bank Book entries.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        placeholder = "%s" if USING_SUPABASE else "?"

        cursor.execute(f"SELECT f.customer_id, c.name, COALESCE(c.account_no, ''), f.principal, f.created_at, f.payment_mode FROM fixed_deposits f JOIN customers c ON f.customer_id = c.id WHERE f.fd_id = {placeholder}", (fd_id,))
        fd_row = cursor.fetchone()
        if not fd_row:
            return False, "Fixed Deposit not found."

        old_c_id, old_c_name, old_c_acc, old_principal, old_created, old_pm = fd_row
        new_principal = float(new_principal or 0.0)
        new_tenure = int(new_tenure or 12)
        new_rate = float(new_rate or 6.5)
        calc_maturity = round(new_principal + (new_principal * new_rate * (new_tenure / 12.0) / 100.0), 2)
        final_maturity = float(new_maturity_amount) if new_maturity_amount is not None else calc_maturity
        created_dt_str = str(new_created_date)[:10]
        op_bal_dt_str = str(new_op_bal_date)[:10] if new_op_bal_date else created_dt_str
        closed_dt_str = str(new_closed_date)[:10] if new_closed_date else None

        # 1. Update fixed_deposits table
        cursor.execute(f"""
            UPDATE fixed_deposits
            SET customer_id = {placeholder}, principal = {placeholder}, tenure_months = {placeholder},
                interest_rate = {placeholder}, maturity_amount = {placeholder}, nominee = {placeholder},
                status = {placeholder}, created_at = {placeholder}, closed_date = {placeholder},
                payment_mode = {placeholder}
            WHERE fd_id = {placeholder}
        """, (
            new_cust_id, new_principal, new_tenure, new_rate, final_maturity,
            new_nominee or "Family Nominee", new_status or "ACTIVE",
            created_dt_str, closed_dt_str, new_pay_mode or "Union Bank of India", fd_id
        ))

        # 2. Update accounts table if exists
        cursor.execute(f"""
            UPDATE accounts
            SET balance = {placeholder}, created_at = {placeholder}
            WHERE customer_id = {placeholder} AND account_type IN ('Fixed Deposit', 'FD Account')
        """, (new_principal, created_dt_str, new_cust_id))

        # 3. Synchronize Opening JV
        cursor.execute(f"""
            SELECT jv_id, narration FROM journal_vouchers
            WHERE (narration LIKE {placeholder} OR narration LIKE {placeholder})
            ORDER BY jv_id ASC LIMIT 1
        """, (f"%FD #{fd_id}%", f"%FD Opening%Customer {old_c_id}%"))
        jv_match = cursor.fetchone()

        if jv_match:
            jv_id_val, jv_narr = jv_match
            cursor.execute(f"UPDATE journal_vouchers SET voucher_date = {placeholder}, narration = {placeholder} WHERE jv_id = {placeholder}", 
                           (op_bal_dt_str, f"FD #{fd_id} Opening Deposit - {old_c_name}", jv_id_val))
            cursor.execute(f"""
                UPDATE jv_entries
                SET account_code = {placeholder}, debit = {placeholder}
                WHERE jv_id = {placeholder} AND debit > 0
            """, (chosen_asset_code, new_principal, jv_id_val))
            cursor.execute(f"""
                UPDATE jv_entries
                SET account_code = 'LIA-102', credit = {placeholder}
                WHERE jv_id = {placeholder} AND credit > 0
            """, (new_principal, jv_id_val))

        # 4. Synchronize Cash Book / Bank Book
        cursor.execute(f"DELETE FROM cash_book WHERE narration LIKE {placeholder} OR particulars LIKE {placeholder}", (f"%FD #{fd_id}%", f"%FD Opening%Customer {old_c_id}%"))
        cursor.execute(f"DELETE FROM bank_book WHERE narration LIKE {placeholder} OR particulars LIKE {placeholder}", (f"%FD #{fd_id}%", f"%FD Opening%Customer {old_c_id}%"))

        if new_principal > 0:
            today_time = f"{op_bal_dt_str} 10:00"
            if chosen_asset_code == 'AST-101':
                v_no = generate_cash_voucher_no()
                cursor.execute(f"""
                    INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 0, 0, 'AST-101', {placeholder}, {placeholder})
                """, (op_bal_dt_str, v_no, f"FD Opening: FD #{fd_id} ({old_c_name})", new_principal, f"FD #{fd_id} Opening Deposit", today_time))
            else:
                b_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
                v_no = generate_bank_voucher_no()
                cursor.execute(f"""
                    INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 0, 0, {placeholder}, {placeholder}, {placeholder}, {placeholder})
                """, (op_bal_dt_str, v_no, f"FD Opening: FD #{fd_id} ({old_c_name})", new_principal, b_name, chosen_asset_code, f"FD #{fd_id} Opening Deposit", today_time))

        conn.commit()
        resequence_cash_book()
        resequence_bank_book()
        clear_db_cache()
        return True, f"Fixed Deposit FD #{fd_id} updated and synchronized successfully."
    except Exception as e:
        if conn and USING_SUPABASE:
            try: conn.rollback()
            except Exception: pass
        return False, str(e)
    finally:
        release_connection(conn)


def create_or_link_fd_opening(
    cust_id, principal, open_date, tenure_months=12, interest_rate=6.5,
    nominee="Family Nominee", payment_mode="Union Bank of India", chosen_asset_code="AST-102",
    op_bal_date=None
):
    """
    Creates a new Fixed Deposit opening balance for an existing customer,
    generates opening JV (Dr Asset, Cr LIA-102), and posts into Cash/Bank book.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        placeholder = "%s" if USING_SUPABASE else "?"

        cursor.execute(f"SELECT name, COALESCE(account_no, '') FROM customers WHERE id = {placeholder}", (cust_id,))
        c_row = cursor.fetchone()
        if not c_row:
            return False, "Customer not found."
        cust_name, cust_acc = c_row

        principal = float(principal or 0.0)
        tenure_months = int(tenure_months or 12)
        interest_rate = float(interest_rate or 6.5)
        calc_maturity = round(principal + (principal * interest_rate * (tenure_months / 12.0) / 100.0), 2)
        open_date_str = str(open_date)[:10]
        op_bal_date_str = str(op_bal_date)[:10] if op_bal_date else open_date_str

        cursor.execute(f"""
            INSERT INTO fixed_deposits (
                customer_id, principal, tenure_months, interest_rate, maturity_amount,
                nominee, status, created_at, payment_mode
            ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, 'ACTIVE', {placeholder}, {placeholder})
            RETURNING fd_id
        """ if USING_SUPABASE else f"""
            INSERT INTO fixed_deposits (
                customer_id, principal, tenure_months, interest_rate, maturity_amount,
                nominee, status, created_at, payment_mode
            ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, 'ACTIVE', {placeholder}, {placeholder})
        """, (
            cust_id, principal, tenure_months, interest_rate, calc_maturity,
            nominee or "Family Nominee", open_date_str, payment_mode
        ))

        if USING_SUPABASE:
            ret = cursor.fetchone()
            new_fd_id = ret[0] if ret else None
        else:
            new_fd_id = cursor.lastrowid

        if not new_fd_id:
            cursor.execute("SELECT MAX(fd_id) FROM fixed_deposits")
            m_id = cursor.fetchone()
            new_fd_id = m_id[0] if m_id else 1

        post_automated_jv(f"FD #{new_fd_id} Opening Deposit - {cust_name}", chosen_asset_code, "LIA-102", principal, voucher_date=op_bal_date_str)

        today_time = f"{op_bal_date_str} 10:00"
        if chosen_asset_code == 'AST-101':
            v_no = generate_cash_voucher_no()
            cursor.execute(f"""
                INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 0, 0, 'AST-101', {placeholder}, {placeholder})
            """, (op_bal_date_str, v_no, f"FD Opening: FD #{new_fd_id} ({cust_name})", principal, f"FD #{new_fd_id} Opening Deposit", today_time))
        else:
            b_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
            v_no = generate_bank_voucher_no()
            cursor.execute(f"""
                INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 0, 0, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            """, (op_bal_date_str, v_no, f"FD Opening: FD #{new_fd_id} ({cust_name})", principal, b_name, chosen_asset_code, f"FD #{new_fd_id} Opening Deposit", today_time))

        conn.commit()
        resequence_cash_book()
        resequence_bank_book()
        clear_db_cache()
        return True, f"Fixed Deposit FD #{new_fd_id} for {cust_name} created successfully with principal ₹{principal:,.2f}."
    except Exception as e:
        if conn and USING_SUPABASE:
            try: conn.rollback()
            except Exception: pass
        return False, str(e)
    finally:
        release_connection(conn)


def update_rd_account_details(
    rd_id, new_cust_id, new_rd_no, new_monthly_amt, new_tenure, new_rate,
    new_inst_paid, new_collected_bal, new_nominee, new_status,
    new_created_date, new_closed_date, new_pay_mode, chosen_asset_code='AST-102',
    new_op_bal_date=None
):
    """
    Updates Recurring Deposit parameters and synchronizes opening Journal Voucher (AST vs LIA-103),
    Cash Book, and Bank Book entries.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        placeholder = "%s" if USING_SUPABASE else "?"

        cursor.execute(f"SELECT r.customer_id, c.name, COALESCE(c.account_no, ''), r.monthly_amount, r.created_at, r.payment_mode FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id WHERE r.rd_id = {placeholder}", (rd_id,))
        rd_row = cursor.fetchone()
        if not rd_row:
            return False, "Recurring Deposit not found."

        old_c_id, old_c_name, old_c_acc, old_monthly, old_created, old_pm = rd_row
        new_monthly_amt = float(new_monthly_amt or 0.0)
        new_tenure = int(new_tenure or 12)
        new_rate = float(new_rate or 6.0)
        new_inst_paid = int(new_inst_paid or 1)
        new_collected_bal = float(new_collected_bal or (new_monthly_amt * new_inst_paid))
        if (new_status or "").upper() == 'CLOSED' or new_inst_paid < new_tenure:
            approx_maturity = calculate_rd_accrued_value(new_monthly_amt, new_rate, new_inst_paid)[1]
        else:
            approx_maturity = calculate_rd_maturity(new_monthly_amt, new_rate, new_tenure)[1]
        created_dt_str = str(new_created_date)[:10]
        op_bal_dt_str = str(new_op_bal_date)[:10] if new_op_bal_date else created_dt_str
        closed_dt_str = str(new_closed_date)[:10] if new_closed_date else None

        cursor.execute(f"""
            UPDATE recurring_deposits
            SET customer_id = {placeholder}, rd_no = {placeholder}, monthly_amount = {placeholder},
                tenure_months = {placeholder}, interest_rate = {placeholder}, installments_paid = {placeholder},
                collected_balance = {placeholder}, maturity_amount = {placeholder}, nominee = {placeholder},
                status = {placeholder}, created_at = {placeholder}, closed_date = {placeholder},
                payment_mode = {placeholder}
            WHERE rd_id = {placeholder}
        """, (
            new_cust_id, new_rd_no or f"RD-{rd_id:05d}", new_monthly_amt,
            new_tenure, new_rate, new_inst_paid, new_collected_bal, approx_maturity,
            new_nominee or "Family Nominee", new_status or "ACTIVE",
            created_dt_str, closed_dt_str, new_pay_mode or "Union Bank of India", rd_id
        ))

        # Synchronize Opening JV
        cursor.execute(f"""
            SELECT jv_id, narration FROM journal_vouchers
            WHERE (narration LIKE {placeholder} OR narration LIKE {placeholder} OR narration LIKE {placeholder})
            ORDER BY jv_id ASC LIMIT 1
        """, (f"%RD #{rd_id}%", f"%{new_rd_no}%", f"%RD Opening%Customer {old_c_id}%"))
        jv_match = cursor.fetchone()

        if jv_match:
            jv_id_val, jv_narr = jv_match
            cursor.execute(f"UPDATE journal_vouchers SET voucher_date = {placeholder}, narration = {placeholder} WHERE jv_id = {placeholder}", 
                           (op_bal_dt_str, f"RD #{rd_id} Opening Deposit - {old_c_name}", jv_id_val))
            cursor.execute(f"""
                UPDATE jv_entries
                SET account_code = {placeholder}, debit = {placeholder}
                WHERE jv_id = {placeholder} AND debit > 0
            """, (chosen_asset_code, new_collected_bal, jv_id_val))
            cursor.execute(f"""
                UPDATE jv_entries
                SET account_code = 'LIA-103', credit = {placeholder}
                WHERE jv_id = {placeholder} AND credit > 0
            """, (new_collected_bal, jv_id_val))

        # Clear existing book entries matching this RD
        cursor.execute(f"DELETE FROM cash_book WHERE narration LIKE {placeholder} OR particulars LIKE {placeholder}", (f"%RD #{rd_id}%", f"%RD Opening%Customer {old_c_id}%"))
        cursor.execute(f"DELETE FROM bank_book WHERE narration LIKE {placeholder} OR particulars LIKE {placeholder}", (f"%RD #{rd_id}%", f"%RD Opening%Customer {old_c_id}%"))

        if new_collected_bal > 0:
            today_time = f"{op_bal_dt_str} 10:00"
            if chosen_asset_code == 'AST-101':
                v_no = generate_cash_voucher_no()
                cursor.execute(f"""
                    INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 0, 0, 'AST-101', {placeholder}, {placeholder})
                """, (op_bal_dt_str, v_no, f"RD Opening: RD #{rd_id} ({old_c_name})", new_collected_bal, f"RD #{rd_id} Opening Deposit", today_time))
            else:
                b_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
                v_no = generate_bank_voucher_no()
                cursor.execute(f"""
                    INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 0, 0, {placeholder}, {placeholder}, {placeholder}, {placeholder})
                """, (op_bal_dt_str, v_no, f"RD Opening: RD #{rd_id} ({old_c_name})", new_collected_bal, b_name, chosen_asset_code, f"RD #{rd_id} Opening Deposit", today_time))

        conn.commit()
        resequence_cash_book()
        resequence_bank_book()
        clear_db_cache()
        return True, f"Recurring Deposit RD #{rd_id} ({new_rd_no}) updated and synchronized successfully."
    except Exception as e:
        if conn and USING_SUPABASE:
            try: conn.rollback()
            except Exception: pass
        return False, str(e)
    finally:
        release_connection(conn)


def create_or_link_rd_opening(
    cust_id, monthly_amt, open_date, tenure_months=12, interest_rate=6.0,
    nominee="Family Nominee", payment_mode="Union Bank of India", chosen_asset_code="AST-102",
    rd_no=None, op_bal_date=None
):
    """
    Creates a new Recurring Deposit opening balance for an existing customer,
    generates opening JV (Dr Asset, Cr LIA-103), and posts into Cash/Bank book.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        placeholder = "%s" if USING_SUPABASE else "?"

        cursor.execute(f"SELECT name, COALESCE(account_no, '') FROM customers WHERE id = {placeholder}", (cust_id,))
        c_row = cursor.fetchone()
        if not c_row:
            return False, "Customer not found."
        cust_name, cust_acc = c_row

        monthly_amt = float(monthly_amt or 0.0)
        tenure_months = int(tenure_months or 12)
        interest_rate = float(interest_rate or 6.0)
        approx_maturity = calculate_rd_maturity(monthly_amt, interest_rate, tenure_months)[1]
        open_date_str = str(open_date)[:10]
        op_bal_date_str = str(op_bal_date)[:10] if op_bal_date else open_date_str

        cursor.execute(f"""
            INSERT INTO recurring_deposits (
                customer_id, monthly_amount, tenure_months, interest_rate, installments_paid,
                collected_balance, maturity_amount, nominee, status, created_at, payment_mode
            ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 1, {placeholder}, {placeholder}, {placeholder}, 'ACTIVE', {placeholder}, {placeholder})
            RETURNING rd_id
        """ if USING_SUPABASE else f"""
            INSERT INTO recurring_deposits (
                customer_id, monthly_amount, tenure_months, interest_rate, installments_paid,
                collected_balance, maturity_amount, nominee, status, created_at, payment_mode
            ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 1, {placeholder}, {placeholder}, {placeholder}, 'ACTIVE', {placeholder}, {placeholder})
        """, (
            cust_id, monthly_amt, tenure_months, interest_rate, monthly_amt,
            approx_maturity, nominee or "Family Nominee", open_date_str, payment_mode
        ))

        if USING_SUPABASE:
            ret = cursor.fetchone()
            new_rd_id = ret[0] if ret else None
        else:
            new_rd_id = cursor.lastrowid

        if not new_rd_id:
            cursor.execute("SELECT MAX(rd_id) FROM recurring_deposits")
            m_id = cursor.fetchone()
            new_rd_id = m_id[0] if m_id else 1

        final_rd_no = rd_no or f"RD-{new_rd_id:05d}"
        cursor.execute(f"UPDATE recurring_deposits SET rd_no = {placeholder} WHERE rd_id = {placeholder}", (final_rd_no, new_rd_id))

        post_automated_jv(f"RD #{new_rd_id} Opening Deposit - {cust_name}", chosen_asset_code, "LIA-103", monthly_amt, voucher_date=op_bal_date_str)

        today_time = f"{op_bal_date_str} 10:00"
        if chosen_asset_code == 'AST-101':
            v_no = generate_cash_voucher_no()
            cursor.execute(f"""
                INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 0, 0, 'AST-101', {placeholder}, {placeholder})
            """, (op_bal_date_str, v_no, f"RD Opening: {final_rd_no} ({cust_name})", monthly_amt, f"RD #{new_rd_id} Opening Deposit", today_time))
        else:
            b_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
            v_no = generate_bank_voucher_no()
            cursor.execute(f"""
                INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 0, 0, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            """, (op_bal_date_str, v_no, f"RD Opening: {final_rd_no} ({cust_name})", monthly_amt, b_name, chosen_asset_code, f"RD #{new_rd_id} Opening Deposit", today_time))

        conn.commit()
        resequence_cash_book()
        resequence_bank_book()
        clear_db_cache()
        return True, f"Recurring Deposit {final_rd_no} for {cust_name} created successfully with monthly installment ₹{monthly_amt:,.2f}."
    except Exception as e:
        if conn and USING_SUPABASE:
            try: conn.rollback()
            except Exception: pass
        return False, str(e)
    finally:
        release_connection(conn)






