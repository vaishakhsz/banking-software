import os
import sqlite3
import time
from datetime import datetime, date, timezone, timedelta
import pytz
import psycopg2
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

# Define IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

DB_NAME = "aasha_nidhi.db"
UPLOAD_DIR = "customer_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Parse Supabase configuration (supporting both Streamlit secrets and local .env)
supabase_url = None
supabase_proj_url = None
supabase_anon_key = None

try:
    import streamlit as st
    if "SUPABASE_URL" in st.secrets:
        supabase_url = st.secrets["SUPABASE_URL"]
    if "SUPABASE_PROJECT_URL" in st.secrets:
        supabase_proj_url = st.secrets["SUPABASE_PROJECT_URL"]
    if "SUPABASE_ANON_KEY" in st.secrets:
        supabase_anon_key = st.secrets["SUPABASE_ANON_KEY"]
except:
    pass

if not supabase_url:
    supabase_url = os.getenv("SUPABASE_URL")
if not supabase_proj_url:
    supabase_proj_url = os.getenv("SUPABASE_PROJECT_URL")
if not supabase_anon_key:
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")

USING_SUPABASE = False
SUPABASE_URL = ""
if supabase_url and "REPLACE_WITH_YOUR_DB_PASSWORD" not in supabase_url and (supabase_url.startswith("postgresql") or supabase_url.startswith("postgres")):
    USING_SUPABASE = True
    SUPABASE_URL = supabase_url

# Initialize Supabase storage client if credentials are provided
supabase_client = None
if supabase_proj_url and supabase_anon_key and "REPLACE_WITH_YOUR_ANON_PUBLIC_KEY" not in supabase_anon_key:
    try:
        from supabase import create_client
        supabase_client = create_client(supabase_proj_url, supabase_anon_key)
    except Exception as e:
        print(f"⚠️ Failed to initialize Supabase storage client: {str(e)}")

def get_connection():
    """Get database connection (Supabase PostgreSQL or local SQLite) with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if USING_SUPABASE:
                return psycopg2.connect(SUPABASE_URL)
            else:
                db_dir = os.path.dirname(DB_NAME)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)
                return sqlite3.connect(DB_NAME, check_same_thread=False, timeout=10)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(1)

def translate_sqlite_schema_to_postgres(sql):
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    sql = sql.replace("INTEGER PRIMARY KEY", "SERIAL PRIMARY KEY")
    sql = sql.replace("REAL", "DOUBLE PRECISION")
    return sql

def execute_create(cursor, sql):
    if USING_SUPABASE:
        sql = translate_sqlite_schema_to_postgres(sql)
    cursor.execute(sql)

def init_db():
    """Initialize database and ensure missing columns are added dynamically"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Enable foreign keys (SQLite specific)
        if not USING_SUPABASE:
            cursor.execute("PRAGMA foreign_keys = ON")
        
        # Create all base tables if they don't exist
        execute_create(cursor, """
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
            )
        """)
        
        execute_create(cursor, """
            CREATE TABLE IF NOT EXISTS sb_accounts (
                account_no TEXT PRIMARY KEY,
                customer_id INTEGER,
                balance REAL DEFAULT 0.0,
                interest_rate REAL DEFAULT 3.5,
                created_at TEXT,
                FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
            )
        """)
        
        execute_create(cursor, """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_id TEXT,
                account_no TEXT,
                type TEXT,
                amount REAL,
                mode TEXT,
                narration TEXT,
                date TEXT
            )
        """)

        execute_create(cursor, """
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
            )
        """)

        execute_create(cursor, """
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
            )
        """)

        # Safe migration for missing columns (Skip for Supabase as fresh DB already has them)
        if not USING_SUPABASE:
            try:
                cursor.execute("ALTER TABLE fixed_deposits ADD COLUMN payment_mode TEXT")
            except sqlite3.OperationalError:
                pass

            try:
                cursor.execute("ALTER TABLE fixed_deposits ADD COLUMN closed_date TEXT")
            except sqlite3.OperationalError:
                pass

            try:
                cursor.execute("ALTER TABLE recurring_deposits ADD COLUMN payment_mode TEXT")
            except sqlite3.OperationalError:
                pass

            try:
                cursor.execute("ALTER TABLE recurring_deposits ADD COLUMN closed_date TEXT")
            except sqlite3.OperationalError:
                pass

            try:
                cursor.execute("ALTER TABLE recurring_deposits ADD COLUMN maturity_amount REAL DEFAULT 0")
            except sqlite3.OperationalError:
                pass

        execute_create(cursor, """
            CREATE TABLE IF NOT EXISTS chart_of_accounts (
                account_code TEXT PRIMARY KEY,
                account_name TEXT,
                account_type TEXT, 
                category TEXT
            )
        """)

        execute_create(cursor, """
            CREATE TABLE IF NOT EXISTS journal_vouchers (
                jv_id INTEGER PRIMARY KEY AUTOINCREMENT,
                voucher_date TEXT,
                narration TEXT,
                status TEXT DEFAULT 'POSTED'
            )
        """)

        execute_create(cursor, """
            CREATE TABLE IF NOT EXISTS jv_entries (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                jv_id INTEGER,
                account_code TEXT,
                debit REAL DEFAULT 0,
                credit REAL DEFAULT 0,
                FOREIGN KEY(jv_id) REFERENCES journal_vouchers(jv_id) ON DELETE CASCADE,
                FOREIGN KEY(account_code) REFERENCES chart_of_accounts(account_code)
            )
        """)

        execute_create(cursor, """
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
            )
        """)

        execute_create(cursor, """
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
            )
        """)

        # Comprehensive default Chart of Accounts list with all Depreciation heads
        default_accounts = [
            ("INC-101", "Loan Interest Income", "Income", "Primary Revenue"),
            ("INC-102", "Investment Income", "Income", "Primary Revenue"),
            ("INC-201", "Processing Fees", "Income", "Service Income"),
            ("INC-202", "Service Charges", "Income", "Service Income"),
            ("INC-203", "Commission Income", "Income", "Service Income"),
            ("INC-204", "Transaction Fees", "Income", "Service Income"),
            ("INC-301", "Miscellaneous Income", "Income", "Other Income"),
            ("EXP-101", "SB Interest Paid", "Expense", "Cost of Funds"),
            ("EXP-102", "FD Interest Paid", "Expense", "Cost of Funds"),
            ("EXP-103", "RD Interest Paid", "Expense", "Cost of Funds"),
            ("EXP-201", "Salaries & Benefits", "Expense", "Operating Expenses"),
            ("EXP-202", "Rent & Utilities", "Expense", "Operating Expenses"),
            ("EXP-203", "Electricity Charges", "Expense", "Operating Expenses"),
            ("EXP-204", "Depreciation 5%", "Expense", "Operating Expenses"),
            ("EXP-205", "Depreciation 10%", "Expense", "Operating Expenses"),
            ("EXP-206", "Depreciation 15%", "Expense", "Operating Expenses"),
            ("EXP-207", "Depreciation 40%", "Expense", "Operating Expenses"),
            ("EXP-301", "Printing & Stationary", "Expense", "Administrative Expenses"),
            ("EXP-401", "Bank Charges", "Expense", "Other Expenses"),
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
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database initialization error: {str(e)}")
        return False

# Initialize the DB
init_db()

def run_query(query, params=(), fetch=True):
    """Execute a database query with error handling"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USING_SUPABASE:
            # Dynamically map query parameters for Postgres
            query = query.replace("?", "%s")
            # Map SQLite case-insensitive LIKE to Postgres ILIKE
            query = query.replace("LIKE %s", "ILIKE %s")
            query = query.replace("LIKE  %s", "ILIKE %s")
            
        cursor.execute(query, params)
        res = cursor.fetchall() if fetch else None
        conn.commit()
        conn.close()
        return res
    except Exception as e:
        import streamlit as st
        st.error(f"Database error: {str(e)}")
        return None

def save_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        # Check if Supabase Storage is configured and initialized
        if supabase_client is not None:
            try:
                # Read file binary content
                data = uploaded_file.getvalue()
                # Sanitize filename (remove characters that might break URLs)
                safe_name = "".join(c for c in uploaded_file.name if c.isalnum() or c in "._-")
                # Prefix with timestamp to prevent name collisions
                unique_name = f"{int(time.time())}_{safe_name}"
                
                # Upload to Supabase Storage bucket 'customer-docs'
                supabase_client.storage.from_("customer-docs").upload(
                    path=unique_name,
                    file=data,
                    file_options={"content-type": uploaded_file.type}
                )
                
                # Retrieve the public URL for the uploaded document
                public_url = supabase_client.storage.from_("customer-docs").get_public_url(unique_name)
                return public_url
            except Exception as e:
                import streamlit as st
                st.warning(f"⚠️ Failed to upload to Supabase Storage: {str(e)}. Saving to local server disk instead.")
        
        # Fallback to local file system
        file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

def get_account_balance_from_jv(account_code):
    """Get real balance from journal entries - SINGLE SOURCE OF TRUTH"""
    try:
        result = run_query("""
            SELECT COALESCE(SUM(JE.debit), 0) - COALESCE(SUM(JE.credit), 0) as net_balance
            FROM jv_entries JE
            JOIN chart_of_accounts CO ON JE.account_code = CO.account_code
            WHERE CO.account_code = ?
        """, (account_code,))
        return result[0][0] if result and result[0][0] is not None else 0.0
    except:
        return 0.0

def get_cash_balance():
    """Get real cash balance from journal entries"""
    return get_account_balance_from_jv('AST-101')

def get_bank_balance(bank_name=None):
    """Get real bank balance from journal entries"""
    if bank_name == "Union Bank of India" or bank_name is None:
        return get_account_balance_from_jv('AST-102')
    elif bank_name == "State Bank of India":
        return get_account_balance_from_jv('AST-103')
    else:
        # Try to find by name
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
    except:
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
    except:
        new_seq = 1
    return f"BB{today}{new_seq:04d}"

def post_automated_jv(narration, debit_acc, credit_acc, amount):
    """Post a journal voucher - this is the single source of truth"""
    if amount <= 0:
        return None
    try:
        debit_check = run_query("SELECT account_code FROM chart_of_accounts WHERE account_code = ?", (debit_acc,))
        credit_check = run_query("SELECT account_code FROM chart_of_accounts WHERE account_code = ?", (credit_acc,))
        
        if not debit_check or not credit_check:
            import streamlit as st
            st.error(f"Invalid account codes: {debit_acc} or {credit_acc}")
            return None
        
        conn = get_connection()
        cursor = conn.cursor()
        
        if USING_SUPABASE:
            cursor.execute("""
                INSERT INTO journal_vouchers (voucher_date, narration, status) 
                VALUES (%s, %s, 'POSTED') RETURNING jv_id
            """, (str(date.today()), narration))
            jv_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, %s, 0)", (jv_id, debit_acc, amount))
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (%s, %s, 0, %s)", (jv_id, credit_acc, amount))
        else:
            cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", (str(date.today()), narration))
            jv_id = cursor.lastrowid
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, debit_acc, amount))
            cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, credit_acc, amount))
        
        conn.commit()
        conn.close()
        return jv_id
    except Exception as e:
        import streamlit as st
        st.error(f"Error posting journal voucher: {str(e)}")
        return None

def get_account_name(account_code):
    """Get account name from chart_of_accounts"""
    try:
        result = run_query("SELECT account_name FROM chart_of_accounts WHERE account_code = ?", (account_code,))
        return result[0][0] if result else ""
    except:
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
