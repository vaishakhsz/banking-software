import os
import sqlite3
import time
import re
import urllib.parse
from datetime import datetime, date, timezone, timedelta
import pytz
from dotenv import load_dotenv

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
    if "SUPABASE_URL" in st.secrets:
        supabase_url = st.secrets["SUPABASE_URL"]
    elif "DATABASE_URL" in st.secrets:
        supabase_url = st.secrets["DATABASE_URL"]
    elif "postgres_url" in st.secrets:
        supabase_url = st.secrets["postgres_url"]
    elif "POSTGRES_URL" in st.secrets:
        supabase_url = st.secrets["POSTGRES_URL"]
    
    if not supabase_url and "connections" in st.secrets and "supabase" in st.secrets["connections"]:
        sub = st.secrets["connections"]["supabase"]
        if isinstance(sub, dict) and "url" in sub:
            supabase_url = sub["url"]
except Exception:
    pass

if not supabase_url:
    supabase_url = os.getenv("SUPABASE_URL") or os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")

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
                "connect_timeout": 8,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
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
# NEON OBJECT STORAGE (S3 COMPATIBLE) CONFIGURATION
# ----------------------------------------------------
neon_s3_endpoint = None
neon_s3_access_key = None
neon_s3_secret_key = None
neon_s3_bucket = None

try:
    import streamlit as st
    if "NEON_STORAGE_ENDPOINT" in st.secrets:
        neon_s3_endpoint = st.secrets["NEON_STORAGE_ENDPOINT"]
    elif "S3_ENDPOINT_URL" in st.secrets:
        neon_s3_endpoint = st.secrets["S3_ENDPOINT_URL"]
        
    if "NEON_STORAGE_ACCESS_KEY" in st.secrets:
        neon_s3_access_key = st.secrets["NEON_STORAGE_ACCESS_KEY"]
    elif "AWS_ACCESS_KEY_ID" in st.secrets:
        neon_s3_access_key = st.secrets["AWS_ACCESS_KEY_ID"]
        
    if "NEON_STORAGE_SECRET_KEY" in st.secrets:
        neon_s3_secret_key = st.secrets["NEON_STORAGE_SECRET_KEY"]
    elif "AWS_SECRET_ACCESS_KEY" in st.secrets:
        neon_s3_secret_key = st.secrets["AWS_SECRET_ACCESS_KEY"]
        
    if "NEON_STORAGE_BUCKET" in st.secrets:
        neon_s3_bucket = st.secrets["NEON_STORAGE_BUCKET"]
    elif "S3_BUCKET_NAME" in st.secrets:
        neon_s3_bucket = st.secrets["S3_BUCKET_NAME"]
except Exception:
    pass

if not neon_s3_endpoint:
    neon_s3_endpoint = os.getenv("NEON_STORAGE_ENDPOINT") or os.getenv("S3_ENDPOINT_URL")
if not neon_s3_access_key:
    neon_s3_access_key = os.getenv("NEON_STORAGE_ACCESS_KEY") or os.getenv("AWS_ACCESS_KEY_ID")
if not neon_s3_secret_key:
    neon_s3_secret_key = os.getenv("NEON_STORAGE_SECRET_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
if not neon_s3_bucket:
    neon_s3_bucket = os.getenv("NEON_STORAGE_BUCKET") or os.getenv("S3_BUCKET_NAME")

# Initialize S3 client for Neon Object Storage
s3_client = None
if neon_s3_endpoint and neon_s3_access_key and neon_s3_secret_key:
    try:
        import boto3
        from botocore.client import Config
        # Dynamically extract region from Neon endpoint URL (e.g. us-east-2)
        region = 'us-east-2'
        if neon_s3_endpoint:
            region_match = re.search(r'\.([a-z0-9-]+)\.aws\.neon\.tech', neon_s3_endpoint)
            if region_match:
                region = region_match.group(1)
                
        s3_client = boto3.client(
            's3',
            endpoint_url=neon_s3_endpoint,
            aws_access_key_id=neon_s3_access_key,
            aws_secret_access_key=neon_s3_secret_key,
            region_name=region,
            config=Config(s3={'addressing_style': 'path'})
        )
        print(f"✅ Neon Object Storage S3 Client (Region: {region}, Path-Style) initialized successfully!")
    except Exception as e:
        print(f"⚠️ Failed to initialize Neon Object Storage S3 Client: {e}")

# ----------------------------------------------------
# HIGH-SPEED PERSISTENT CONNECTION POOLING
# ----------------------------------------------------
DB_INITIALIZED = False
DB_INIT_ERROR = None
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

def get_connection():
    """Get database connection from persistent pool with sub-millisecond response"""
    if USING_SUPABASE:
        try:
            p = get_pg_pool()
            conn = p.getconn()
            if conn.closed:
                p.putconn(conn, close=True)
                conn = p.getconn()
            conn.autocommit = False
            return conn
        except Exception:
            global _pg_pool
            try:
                if _pg_pool and not _pg_pool.closed:
                    _pg_pool.closeall()
            except Exception:
                pass
            _pg_pool = None
            p = get_pg_pool()
            conn = p.getconn()
            conn.autocommit = False
            return conn
    else:
        db_dir = os.path.dirname(DB_NAME)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        return sqlite3.connect(DB_NAME, check_same_thread=False, timeout=10)

def release_connection(conn, is_broken=False):
    """Safely return connection back to pool for instant reuse"""
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


def init_db():
    """Initialize database tables lazily on first query execution"""
    global DB_INITIALIZED, DB_INIT_ERROR
    if DB_INITIALIZED:
        return True
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if not USING_SUPABASE:
            cursor.execute("PRAGMA foreign_keys = ON")
        
        # Combined DDL statements for rapid 1-roundtrip schema execution
        tables_sql = """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dob TEXT,
                gender TEXT,
                email TEXT,
                phone TEXT,
                street TEXT,
                city TEXT,
                state TEXT,
                pincode TEXT,
                pan TEXT,
                adhar TEXT,
                adhar_file TEXT,
                pan_file TEXT,
                signature_file TEXT,
                kyc_status TEXT DEFAULT 'PENDING',
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
                monthly_amount REAL,
                tenure_months INTEGER,
                interest_rate REAL,
                installments_paid INTEGER DEFAULT 0,
                nominee TEXT,
                status TEXT DEFAULT 'ACTIVE',
                created_at TEXT,
                payment_mode TEXT,
                closed_date TEXT,
                maturity_amount REAL DEFAULT 0,
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
        """
        
        if USING_SUPABASE:
            tables_sql = translate_sqlite_schema_to_postgres(tables_sql)
            cursor.execute(tables_sql)
        else:
            cursor.executescript(tables_sql)

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
            ("AST-101", "Cash in Hand", "Asset", "Current Assets"),
            ("AST-102", "Union Bank of India", "Asset", "Current Assets"),
            ("AST-103", "State Bank of India", "Asset", "Current Assets"),
            ("AST-104", "Fixed Asset Computer", "Asset", "Non Current Assets"),
            ("AST-105", "Fixed Asset Furniture & Fixtures", "Asset", "Non Current Assets"),
            ("AST-106", "Office Equipments", "Asset", "Non Current Assets"),  
            ("AST-107", "Building", "Asset", "Non Current Assets"),
            ("LIA-101", "SB Deposits Control", "Liability", "Deposits"),
            ("LIA-102", "FD Deposits Control", "Liability", "Deposits"),
            ("LIA-103", "RD Deposits Control", "Liability", "Deposits"),
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
        else:
            cursor.executemany("INSERT OR IGNORE INTO chart_of_accounts VALUES (?, ?, ?, ?)", default_accounts)

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

def run_query(query, params=(), fetch=True):
    """Execute a database query with auto-initialization, commit, and connection cleanup"""
    if not DB_INITIALIZED:
        init_db()

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USING_SUPABASE:
            query = query.replace("%", "%%")
            query = query.replace("?", "%s")
            query = query.replace("LIKE %s", "ILIKE %s")
            query = query.replace("LIKE  %s", "ILIKE %s")
            
        cursor.execute(query, params)
        res = cursor.fetchall() if fetch else None
        conn.commit()
        return res
    except Exception as e:
        import streamlit as st
        err_str = str(e)
        st.error(f"Database error: {err_str}")
        if conn is not None and USING_SUPABASE:
            try:
                conn.rollback()
            except Exception:
                pass
        return None
    finally:
        release_connection(conn)

def save_uploaded_file(uploaded_file):
    """Saves uploaded files to local disk and uploads to Neon Object Storage if configured"""
    if uploaded_file is not None:
        try:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            safe_name = "".join(c for c in uploaded_file.name if c.isalnum() or c in "._- ")
            unique_name = f"{int(time.time())}_{safe_name}"
            file_path = os.path.join(UPLOAD_DIR, unique_name)
            
            # Save file locally first (with PIL compression if image)
            saved_local = False
            if hasattr(uploaded_file, "type") and uploaded_file.type and uploaded_file.type.startswith("image/"):
                try:
                    from PIL import Image
                    img = Image.open(uploaded_file)
                    if img.mode in ("RGBA", "P") and not unique_name.lower().endswith(".png"):
                        img = img.convert("RGB")
                    img.thumbnail((1400, 1400), Image.LANCZOS)
                    img.save(file_path, optimize=True, quality=80)
                    saved_local = True
                except Exception as ex:
                    print(f"PIL compression failed: {ex}")
            
            if not saved_local:
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            
            # If S3 is configured, upload the optimized local file to Neon Object Storage
            if s3_client and neon_s3_bucket:
                try:
                    with open(file_path, "rb") as f_s3:
                        s3_client.put_object(
                            Bucket=neon_s3_bucket,
                            Key=unique_name,
                            Body=f_s3,
                            ContentType=uploaded_file.type if hasattr(uploaded_file, "type") else "application/octet-stream"
                        )
                    print(f"✅ Uploaded to Neon Object Storage: {unique_name}")
                    # Clean up local file to save disk space if stored in the cloud
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
                    # Return the S3 key so it gets stored in the database!
                    return unique_name
                except Exception as s3_err:
                    print(f"⚠️ S3 upload failed, keeping local file: {s3_err}")
            
            # If S3 is not configured, return the local file path
            return file_path
        except Exception as e:
            print(f"Error saving uploaded file: {str(e)}")
            return None
    return None

def get_document_data(file_identifier):
    """
    Retrieves the binary bytes and clean filename of the file.
    Supports both local disk paths and S3 bucket object keys.
    """
    if not file_identifier:
        return None, None
    
    filename = os.path.basename(file_identifier)
    
    # 1. Try S3 if client is initialized
    if s3_client and neon_s3_bucket:
        try:
            response = s3_client.get_object(Bucket=neon_s3_bucket, Key=file_identifier)
            return response['Body'].read(), filename
        except Exception:
            # Fallback to local file if S3 key is not found or fails
            pass
            
    # 2. Local fallback
    try:
        if os.path.exists(file_identifier):
            with open(file_identifier, "rb") as f:
                return f.read(), filename
        # If it's a relative path or key, check in local UPLOAD_DIR
        local_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read(), filename
    except Exception as e:
        print(f"Error reading local file: {e}")
        
    return None, None

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
    """Fetches Cash, Union Bank, and SBI balances in a single database round-trip."""
    try:
        result = run_query("""
            SELECT account_code, COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) as net_bal
            FROM jv_entries
            WHERE account_code IN ('AST-101', 'AST-102', 'AST-103')
            GROUP BY account_code
        """)
        bal_map = {'AST-101': 0.0, 'AST-102': 0.0, 'AST-103': 0.0}
        if result:
            for code, bal in result:
                bal_map[code] = float(bal) if bal is not None else 0.0
        return bal_map['AST-101'], bal_map['AST-102'], bal_map['AST-103']
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

def get_account_name(account_code):
    try:
        result = run_query("SELECT account_name FROM chart_of_accounts WHERE account_code = ?", (account_code,))
        return result[0][0] if result else ""
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

def delete_document(file_identifier):
    """
    Deletes the document from cloud storage (Neon S3) or local disk.
    """
    if not file_identifier:
        return
        
    # 1. Try deleting from S3
    if s3_client and neon_s3_bucket:
        try:
            # Check if it's an S3 key (doesn't look like an absolute file path on disk)
            if not ("/" in file_identifier or "\\" in file_identifier or os.path.isabs(file_identifier)):
                s3_client.delete_object(Bucket=neon_s3_bucket, Key=file_identifier)
                print(f"🗑️ Deleted from Neon S3: {file_identifier}")
                return
        except Exception as e:
            print(f"Failed to delete from S3: {e}")
            
    # 2. Try deleting from local storage
    try:
        if os.path.exists(file_identifier):
            os.remove(file_identifier)
            print(f"🗑️ Deleted local file: {file_identifier}")
            return
        local_path = os.path.join(UPLOAD_DIR, os.path.basename(file_identifier))
        if os.path.exists(local_path):
            os.remove(local_path)
            print(f"🗑️ Deleted local file: {local_path}")
    except Exception as e:
        print(f"Failed to delete local file: {e}")

