import os
import sqlite3
import time
from datetime import datetime, date, timezone, timedelta
import pytz

# Define IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

DB_NAME = "aasha_nidhi.db"
UPLOAD_DIR = "customer_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_connection():
    """Get database connection with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            db_dir = os.path.dirname(DB_NAME)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            return sqlite3.connect(DB_NAME, check_same_thread=False, timeout=10)
        except sqlite3.OperationalError as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(1)

def init_db():
    """Initialize database and ensure missing columns are added dynamically"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Create all base tables if they don't exist
        cursor.execute("""
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
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sb_accounts (
                account_no TEXT PRIMARY KEY,
                customer_id INTEGER,
                balance REAL DEFAULT 0.0,
                interest_rate REAL DEFAULT 3.5,
                created_at TEXT,
                FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
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

        cursor.execute("""
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

        cursor.execute("""
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

        # Safe migration for missing columns
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chart_of_accounts (
                account_code TEXT PRIMARY KEY,
                account_name TEXT,
                account_type TEXT, 
                category TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS journal_vouchers (
                jv_id INTEGER PRIMARY KEY AUTOINCREMENT,
                voucher_date TEXT,
                narration TEXT,
                status TEXT DEFAULT 'POSTED'
            )
        """)

        cursor.execute("""
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

        cursor.execute("""
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

        cursor.execute("""
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
        cursor.execute(query, params)
        res = cursor.fetchall() if fetch else None
        conn.commit()
        conn.close()
        return res
    except sqlite3.OperationalError as e:
        import streamlit as st
        st.error(f"Database error: {str(e)}")
        return None

def save_uploaded_file(uploaded_file):
    if uploaded_file is not None:
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
