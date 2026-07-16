import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import uuid
import json
import os

# Page configuration
st.set_page_config(
    page_title="Complete Banking System",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# PROFESSIONAL DARK THEME CSS
# ============================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    .stApp { background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0d1128 100%); }
    
    .main-header {
        font-size: 2.8rem;
        background: linear-gradient(120deg, #667eea, #764ba2, #f093fb);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 700;
    }
    
    .sub-header {
        font-size: 1.6rem;
        color: #a78bfa;
        margin-bottom: 1.5rem;
        font-weight: 600;
        border-bottom: 2px solid #2d2b55;
        padding-bottom: 0.5rem;
    }
    
    div[data-testid="stForm"] {
        background: linear-gradient(135deg, rgba(26, 31, 58, 0.95), rgba(45, 43, 85, 0.95));
        border: 1px solid rgba(102, 126, 234, 0.3);
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 15px 50px rgba(0, 0, 0, 0.4);
    }
    
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select,
    .stTextArea > div > div > textarea {
        background: rgba(15, 18, 35, 0.8) !important;
        border: 1px solid rgba(102, 126, 234, 0.3) !important;
        border-radius: 10px !important;
        color: #e2e8f0 !important;
        padding: 0.75rem !important;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 12px 35px rgba(102, 126, 234, 0.6) !important;
    }
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0e27 0%, #1a1f3a 100%) !important;
        border-right: 1px solid rgba(102, 126, 234, 0.2) !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(15, 18, 35, 0.6) !important;
        border-radius: 15px !important;
        padding: 0.5rem !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2)) !important;
        color: #a78bfa !important;
    }
    
    .stDataFrame {
        background: rgba(15, 18, 35, 0.8) !important;
        border-radius: 15px !important;
    }
    
    .stDataFrame th {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2)) !important;
        color: #c4b5fd !important;
    }
    
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(26, 31, 58, 0.9), rgba(45, 43, 85, 0.9));
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 15px;
        padding: 1.5rem !important;
    }
    
    [data-testid="stMetricValue"] { color: #a78bfa !important; }
    
    .badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.85rem; font-weight: 600; }
    .badge-success { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; }
    .badge-warning { background: rgba(245, 158, 11, 0.2); color: #fcd34d; }
    .badge-info { background: rgba(59, 130, 246, 0.2); color: #93c5fd; }
    
    .success-box {
        padding: 1rem; background: rgba(16, 185, 129, 0.15); border-left: 4px solid #10b981;
        border-radius: 8px; color: #6ee7b7; margin: 1rem 0;
    }
    .error-box {
        padding: 1rem; background: rgba(239, 68, 68, 0.15); border-left: 4px solid #ef4444;
        border-radius: 8px; color: #fca5a5; margin: 1rem 0;
    }
    .info-box {
        padding: 1rem; background: rgba(59, 130, 246, 0.15); border-left: 4px solid #3b82f6;
        border-radius: 8px; color: #93c5fd; margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================
# DATABASE LAYER
# ============================================
class DatabaseLayer:
    def __init__(self):
        self.db_path = 'complete_banking.db'
        
    def initialize_database(self):
        if os.path.exists(self.db_path):
            try:
                temp_conn = sqlite3.connect(self.db_path)
                temp_c = temp_conn.cursor()
                temp_c.execute("SELECT password_hash FROM users LIMIT 1")
                temp_conn.close()
            except:
                os.remove(self.db_path)
        
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute("PRAGMA foreign_keys=ON")
        
        # Users
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, full_name TEXT NOT NULL, email TEXT UNIQUE,
            role TEXT NOT NULL CHECK(role IN ('Admin', 'Manager', 'User')),
            is_active INTEGER DEFAULT 1, last_login TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS user_sessions (
            session_id TEXT PRIMARY KEY, user_id INTEGER REFERENCES users(user_id),
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, logout_time TIMESTAMP, is_active INTEGER DEFAULT 1
        )''')
        
        # Customers
        c.execute('''CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
            date_of_birth DATE NOT NULL, gender TEXT, email TEXT UNIQUE, phone TEXT NOT NULL,
            address TEXT, city TEXT, state TEXT, pincode TEXT, occupation TEXT, annual_income REAL,
            kyc_status TEXT DEFAULT 'Pending', kyc_verified_by INTEGER REFERENCES users(user_id),
            kyc_verified_date TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER REFERENCES users(user_id)
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS kyc_documents (
            doc_id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id TEXT REFERENCES customers(customer_id),
            doc_type TEXT NOT NULL, doc_number TEXT, verification_status TEXT DEFAULT 'Pending',
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, verified_by INTEGER REFERENCES users(user_id)
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS nominees (
            nominee_id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id TEXT REFERENCES customers(customer_id),
            nominee_name TEXT NOT NULL, relationship TEXT NOT NULL, date_of_birth DATE, phone TEXT,
            percentage_share REAL DEFAULT 100.0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Accounts
        c.execute('''CREATE TABLE IF NOT EXISTS sb_accounts (
            account_number TEXT PRIMARY KEY, customer_id TEXT REFERENCES customers(customer_id),
            balance REAL DEFAULT 0.00, interest_rate REAL DEFAULT 4.00, min_balance REAL DEFAULT 0.00,
            opened_date DATE NOT NULL, last_interest_date DATE,
            status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Dormant', 'Closed', 'Frozen')),
            nominee_id INTEGER REFERENCES nominees(nominee_id),
            created_by INTEGER REFERENCES users(user_id), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS fd_accounts (
            fd_id TEXT PRIMARY KEY, customer_id TEXT REFERENCES customers(customer_id),
            sb_account TEXT REFERENCES sb_accounts(account_number), principal_amount REAL NOT NULL,
            interest_rate REAL NOT NULL, tenure_months INTEGER NOT NULL, start_date DATE NOT NULL,
            maturity_date DATE NOT NULL, maturity_amount REAL,
            status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Matured', 'Premature_Closed')),
            nominee_id INTEGER REFERENCES nominees(nominee_id),
            created_by INTEGER REFERENCES users(user_id), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS rd_accounts (
            rd_id TEXT PRIMARY KEY, customer_id TEXT REFERENCES customers(customer_id),
            sb_account TEXT REFERENCES sb_accounts(account_number), monthly_amount REAL NOT NULL,
            interest_rate REAL NOT NULL, tenure_months INTEGER NOT NULL, start_date DATE NOT NULL,
            maturity_date DATE NOT NULL, maturity_amount REAL, installments_paid INTEGER DEFAULT 0,
            total_installments INTEGER NOT NULL,
            status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Matured', 'Closed', 'Defaulted')),
            nominee_id INTEGER REFERENCES nominees(nominee_id),
            created_by INTEGER REFERENCES users(user_id), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS rd_installments (
            installment_id INTEGER PRIMARY KEY AUTOINCREMENT, rd_id TEXT REFERENCES rd_accounts(rd_id),
            installment_number INTEGER NOT NULL, due_date DATE NOT NULL, paid_date DATE,
            amount REAL NOT NULL, status TEXT DEFAULT 'Pending', voucher_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Vouchers & Accounting
        c.execute('''CREATE TABLE IF NOT EXISTS journal_vouchers (
            voucher_id TEXT PRIMARY KEY, voucher_type TEXT NOT NULL, voucher_date DATE NOT NULL,
            narration TEXT NOT NULL, total_amount REAL NOT NULL DEFAULT 0.00,
            status TEXT DEFAULT 'Approved', is_posted INTEGER DEFAULT 0,
            created_by INTEGER REFERENCES users(user_id), approved_by INTEGER REFERENCES users(user_id),
            verified_by INTEGER REFERENCES users(user_id), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_at TIMESTAMP, verification_status TEXT DEFAULT 'Verified'
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS journal_entries (
            entry_id INTEGER PRIMARY KEY AUTOINCREMENT, voucher_id TEXT REFERENCES journal_vouchers(voucher_id),
            account_head TEXT, debit_amount REAL DEFAULT 0.00, credit_amount REAL DEFAULT 0.00,
            description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS chart_of_accounts (
            account_head TEXT PRIMARY KEY, account_name TEXT NOT NULL, account_type TEXT NOT NULL,
            category TEXT NOT NULL, sub_category TEXT, is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Transactions
        c.execute('''CREATE TABLE IF NOT EXISTS sb_transactions (
            transaction_id TEXT PRIMARY KEY, account_number TEXT REFERENCES sb_accounts(account_number),
            transaction_type TEXT NOT NULL, amount REAL NOT NULL, balance_before REAL, balance_after REAL,
            description TEXT, voucher_id TEXT, created_by INTEGER REFERENCES users(user_id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS fd_transactions (
            transaction_id TEXT PRIMARY KEY, fd_id TEXT REFERENCES fd_accounts(fd_id),
            transaction_type TEXT NOT NULL, amount REAL NOT NULL, description TEXT, voucher_id TEXT,
            created_by INTEGER REFERENCES users(user_id), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS interest_calculations (
            calc_id INTEGER PRIMARY KEY AUTOINCREMENT, account_number TEXT REFERENCES sb_accounts(account_number),
            interest_period_start DATE, interest_period_end DATE, minimum_balance REAL,
            interest_rate REAL, interest_amount REAL, is_credited INTEGER DEFAULT 0, voucher_id TEXT,
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS audit_trail (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, module TEXT NOT NULL,
            action TEXT NOT NULL, record_type TEXT, record_id TEXT, old_data TEXT, new_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Default Users
        c.execute("SELECT COUNT(*) FROM users")
        if c.fetchone()[0] == 0:
            users = [
                ('admin', 'admin123', 'System Administrator', 'admin@bank.com', 'Admin'),
                ('manager', 'manager123', 'Branch Manager', 'manager@bank.com', 'Manager'),
                ('user1', 'user123', 'Bank User', 'user@bank.com', 'User'),
            ]
            for username, password, full_name, email, role in users:
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                c.execute("INSERT INTO users (username, password_hash, full_name, email, role) VALUES (?, ?, ?, ?, ?)",
                         (username, password_hash, full_name, email, role))
        
        # Chart of Accounts
        c.execute("SELECT COUNT(*) FROM chart_of_accounts")
        if c.fetchone()[0] == 0:
            accounts = [
                ('CASH_IN_HAND', 'Cash in Hand', 'Asset', 'Current Asset', 'Cash'),
                ('FD_INVESTMENTS', 'FD Investments', 'Asset', 'Investment', 'FD'),
                ('RD_INVESTMENTS', 'RD Investments', 'Asset', 'Investment', 'RD'),
                ('LOANS_RECEIVABLE', 'Loans Receivable', 'Asset', 'Current Asset', 'Loans'),
                ('FURNITURE', 'Furniture & Fixtures', 'Asset', 'Fixed Asset', 'Office'),
                ('SB_ACCOUNTS', 'Savings Bank Accounts', 'Liability', 'Current Liability', 'Deposits'),
                ('FD_ACCOUNTS', 'Fixed Deposit Accounts', 'Liability', 'Current Liability', 'Deposits'),
                ('RD_ACCOUNTS', 'Recurring Deposit Accounts', 'Liability', 'Current Liability', 'Deposits'),
                ('INTEREST_PAYABLE', 'Interest Payable', 'Liability', 'Current Liability', 'Interest'),
                ('SHARE_CAPITAL', 'Share Capital', 'Equity', 'Share Capital', 'Capital'),
                ('RESERVES', 'Reserves & Surplus', 'Equity', 'Reserves', 'Reserves'),
                ('INTEREST_ON_LOANS', 'Interest on Loans', 'Income', 'Operating Income', 'Interest'),
                ('FD_INTEREST_INCOME', 'FD Interest Income', 'Income', 'Operating Income', 'Interest'),
                ('RD_INTEREST_INCOME', 'RD Interest Income', 'Income', 'Operating Income', 'Interest'),
                ('COMMISSION', 'Commission Income', 'Income', 'Operating Income', 'Fees'),
                ('OTHER_INCOME', 'Other Income', 'Income', 'Other Income', 'Misc'),
                ('INTEREST_ON_SB', 'Interest on SB Accounts', 'Expense', 'Operating Expense', 'Interest'),
                ('INTEREST_ON_FD', 'Interest on FD Accounts', 'Expense', 'Operating Expense', 'Interest'),
                ('INTEREST_ON_RD', 'Interest on RD Accounts', 'Expense', 'Operating Expense', 'Interest'),
                ('SALARY', 'Salary Expense', 'Expense', 'Administrative Expense', 'Staff'),
                ('RENT', 'Rent Expense', 'Expense', 'Administrative Expense', 'Office'),
                ('UTILITIES', 'Utilities Expense', 'Expense', 'Administrative Expense', 'Office'),
            ]
            for account in accounts:
                c.execute("INSERT OR IGNORE INTO chart_of_accounts (account_head, account_name, account_type, category, sub_category) VALUES (?, ?, ?, ?, ?)", account)
        
        conn.commit()
        return conn
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

db = DatabaseLayer()

# ============================================
# AUTH MODULE
# ============================================
class AuthModule:
    @staticmethod
    def authenticate(username, password):
        conn = db.get_connection()
        c = conn.cursor()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        c.execute("SELECT user_id, username, full_name, role, email FROM users WHERE username = ? AND password_hash = ? AND is_active = 1",
                 (username, password_hash))
        user = c.fetchone()
        if user:
            session_id = str(uuid.uuid4())
            c.execute("INSERT INTO user_sessions (session_id, user_id) VALUES (?, ?)", (session_id, user[0]))
            conn.commit()
            conn.close()
            return {'user_id': user[0], 'username': user[1], 'full_name': user[2], 'role': user[3], 'email': user[4], 'session_id': session_id}
        conn.close()
        return None
    
    @staticmethod
    def logout(user_id, session_id):
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("UPDATE user_sessions SET logout_time = ?, is_active = 0 WHERE session_id = ? AND user_id = ?",
                 (datetime.now(), session_id, user_id))
        conn.commit()
        conn.close()

# ============================================
# SB ACCOUNT MODULE
# ============================================
class SBAccountModule:
    @staticmethod
    def generate_account_number():
        return f"SB{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
    
    @staticmethod
    def open_account(customer_id, initial_deposit=0.0, interest_rate=4.0, nominee_id=None, created_by=None):
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("SELECT kyc_status FROM customers WHERE customer_id = ?", (customer_id,))
            customer = c.fetchone()
            if not customer:
                conn.close()
                return False, "Customer not found"
            if customer[0] != 'Verified':
                conn.close()
                return False, "Customer KYC not verified"
            
            account_number = SBAccountModule.generate_account_number()
            today = datetime.now().date()
            
            c.execute("""INSERT INTO sb_accounts (account_number, customer_id, balance, interest_rate, min_balance, opened_date, last_interest_date, nominee_id, created_by)
                VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?)""",
                (account_number, customer_id, initial_deposit, interest_rate, today, today, nominee_id, created_by))
            
            if initial_deposit > 0:
                txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
                c.execute("INSERT INTO sb_transactions (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by) VALUES (?, ?, 'Deposit', ?, 0, ?, 'Initial Deposit', ?)",
                         (txn_id, account_number, initial_deposit, initial_deposit, created_by))
                voucher_id = JournalVoucherModule.create_auto_voucher('Receipt', today, f'Initial deposit for {account_number}', created_by,
                    [('CASH_IN_HAND', initial_deposit, 0), ('SB_ACCOUNTS', 0, initial_deposit)])
                c.execute("UPDATE sb_transactions SET voucher_id = ? WHERE transaction_id = ?", (voucher_id, txn_id))
            
            conn.commit()
            conn.close()
            return True, account_number
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)
    
    @staticmethod
    def deposit(account_number, amount, description, created_by):
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("SELECT balance FROM sb_accounts WHERE account_number = ? AND status = 'Active'", (account_number,))
            account = c.fetchone()
            if not account:
                conn.close()
                return False, "Account not found or inactive"
            
            old_balance, new_balance = account[0], account[0] + amount
            c.execute("UPDATE sb_accounts SET balance = ? WHERE account_number = ?", (new_balance, account_number))
            
            txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
            c.execute("INSERT INTO sb_transactions (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by) VALUES (?, ?, 'Deposit', ?, ?, ?, ?, ?)",
                     (txn_id, account_number, amount, old_balance, new_balance, description, created_by))
            
            voucher_id = JournalVoucherModule.create_auto_voucher('Receipt', datetime.now().date(), f'Deposit in {account_number}', created_by,
                [('CASH_IN_HAND', amount, 0), ('SB_ACCOUNTS', 0, amount)])
            c.execute("UPDATE sb_transactions SET voucher_id = ? WHERE transaction_id = ?", (voucher_id, txn_id))
            
            conn.commit()
            conn.close()
            return True, f"Deposited ₹{amount:,.2f}. New Balance: ₹{new_balance:,.2f}"
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)
    
    @staticmethod
    def withdraw(account_number, amount, description, created_by):
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("SELECT balance FROM sb_accounts WHERE account_number = ? AND status = 'Active'", (account_number,))
            account = c.fetchone()
            if not account:
                conn.close()
                return False, "Account not found or inactive"
            if account[0] < amount:
                conn.close()
                return False, f"Insufficient balance. Available: ₹{account[0]:,.2f}"
            
            old_balance, new_balance = account[0], account[0] - amount
            c.execute("UPDATE sb_accounts SET balance = ? WHERE account_number = ?", (new_balance, account_number))
            
            txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
            c.execute("INSERT INTO sb_transactions (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by) VALUES (?, ?, 'Withdrawal', ?, ?, ?, ?, ?)",
                     (txn_id, account_number, amount, old_balance, new_balance, description, created_by))
            
            voucher_id = JournalVoucherModule.create_auto_voucher('Payment', datetime.now().date(), f'Withdrawal from {account_number}', created_by,
                [('SB_ACCOUNTS', amount, 0), ('CASH_IN_HAND', 0, amount)])
            c.execute("UPDATE sb_transactions SET voucher_id = ? WHERE transaction_id = ?", (voucher_id, txn_id))
            
            conn.commit()
            conn.close()
            return True, f"Withdrew ₹{amount:,.2f}. New Balance: ₹{new_balance:,.2f}"
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)
    
    @staticmethod
    def calculate_quarterly_interest(created_by=None):
        conn = db.get_connection()
        c = conn.cursor()
        try:
            today = datetime.now().date()
            quarter_start = today - relativedelta(months=3)
            
            c.execute("""SELECT sa.account_number, sa.balance, sa.interest_rate FROM sb_accounts sa
                WHERE sa.status = 'Active' AND sa.account_number NOT IN (
                    SELECT DISTINCT account_number FROM interest_calculations 
                    WHERE interest_period_start = ? AND is_credited = 1)""", (quarter_start,))
            accounts = c.fetchall()
            
            if not accounts:
                conn.close()
                return False, "No eligible accounts"
            
            results = []
            for acc in accounts:
                acc_num, balance, rate = acc
                c.execute("SELECT COALESCE(MIN(balance_after), ?) FROM sb_transactions WHERE account_number = ? AND created_at >= ? AND created_at <= ?",
                         (balance, acc_num, quarter_start, today))
                min_balance = c.fetchone()[0]
                
                days_in_quarter = (today - quarter_start).days
                interest = round(min_balance * (rate / 100 / 365) * days_in_quarter, 2)
                
                if interest > 0:
                    new_balance = balance + interest
                    c.execute("UPDATE sb_accounts SET balance = ?, last_interest_date = ? WHERE account_number = ?", (new_balance, today, acc_num))
                    
                    txn_id = f"INT{uuid.uuid4().hex[:8].upper()}"
                    c.execute("INSERT INTO sb_transactions (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by) VALUES (?, ?, 'Interest_Credit', ?, ?, ?, ?, ?)",
                             (txn_id, acc_num, interest, balance, new_balance, f'Quarterly Interest Q{((today.month-1)//3)+1} {today.year}', created_by))
                    
                    voucher_id = JournalVoucherModule.create_auto_voucher('Interest', today, f'Interest credited to {acc_num}', created_by,
                        [('INTEREST_ON_SB', interest, 0), ('SB_ACCOUNTS', 0, interest)])
                    c.execute("UPDATE sb_transactions SET voucher_id = ? WHERE transaction_id = ?", (voucher_id, txn_id))
                    
                    c.execute("INSERT INTO interest_calculations (account_number, interest_period_start, interest_period_end, minimum_balance, interest_rate, interest_amount, is_credited, voucher_id) VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
                             (acc_num, quarter_start, today, min_balance, rate, interest, voucher_id))
                    
                    results.append({'Account': acc_num, 'Min Balance': f"₹{min_balance:,.2f}", 'Interest': f"₹{interest:,.2f}", 'New Balance': f"₹{new_balance:,.2f}"})
            
            conn.commit()
            conn.close()
            return True, results
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)

# ============================================
# FD ACCOUNT MODULE
# ============================================
class FDAccountModule:
    @staticmethod
    def generate_fd_id():
        return f"FD{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}"
    
    @staticmethod
    def open_fd(customer_id, sb_account, principal, interest_rate, tenure_months, nominee_id=None, created_by=None):
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("SELECT balance FROM sb_accounts WHERE account_number = ? AND customer_id = ? AND status = 'Active'",
                     (sb_account, customer_id))
            sb = c.fetchone()
            if not sb:
                conn.close()
                return False, "SB Account not found or inactive"
            if sb[0] < principal:
                conn.close()
                return False, f"Insufficient balance. Available: ₹{sb[0]:,.2f}"
            
            fd_id = FDAccountModule.generate_fd_id()
            start_date = datetime.now().date()
            maturity_date = start_date + relativedelta(months=tenure_months)
            maturity_amount = round(principal * (1 + (interest_rate/1200) * tenure_months), 2)
            
            c.execute("INSERT INTO fd_accounts (fd_id, customer_id, sb_account, principal_amount, interest_rate, tenure_months, start_date, maturity_date, maturity_amount, nominee_id, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (fd_id, customer_id, sb_account, principal, interest_rate, tenure_months, start_date, maturity_date, maturity_amount, nominee_id, created_by))
            
            old_balance, new_balance = sb[0], sb[0] - principal
            c.execute("UPDATE sb_accounts SET balance = ? WHERE account_number = ?", (new_balance, sb_account))
            
            txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
            c.execute("INSERT INTO sb_transactions (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by) VALUES (?, ?, 'FD_Transfer', ?, ?, ?, ?, ?)",
                     (txn_id, sb_account, principal, old_balance, new_balance, f'FD Creation - {fd_id}', created_by))
            
            fd_txn_id = f"FDT{uuid.uuid4().hex[:8].upper()}"
            c.execute("INSERT INTO fd_transactions (transaction_id, fd_id, transaction_type, amount, description, created_by) VALUES (?, ?, 'FD_Creation', ?, ?, ?)",
                     (fd_txn_id, fd_id, principal, f'FD Opened - {tenure_months} months @ {interest_rate}%', created_by))
            
            voucher_id = JournalVoucherModule.create_auto_voucher('FD', start_date, f'FD Creation {fd_id}', created_by,
                [('FD_INVESTMENTS', principal, 0), ('SB_ACCOUNTS', 0, principal)])
            c.execute("UPDATE sb_transactions SET voucher_id = ? WHERE transaction_id = ?", (voucher_id, txn_id))
            c.execute("UPDATE fd_transactions SET voucher_id = ? WHERE transaction_id = ?", (voucher_id, fd_txn_id))
            
            conn.commit()
            conn.close()
            return True, fd_id
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)
    
    @staticmethod
    def mature_fd(fd_id, created_by=None):
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("SELECT * FROM fd_accounts WHERE fd_id = ? AND status = 'Active'", (fd_id,))
            fd = c.fetchone()
            if not fd:
                conn.close()
                return False, "FD not found"
            if datetime.now().date() < fd[6]:
                conn.close()
                return False, "FD not yet matured"
            
            maturity_amount, sb_account, principal = fd[7], fd[2], fd[3]
            interest_earned = maturity_amount - principal
            
            c.execute("UPDATE fd_accounts SET status = 'Matured' WHERE fd_id = ?", (fd_id,))
            
            c.execute("SELECT balance FROM sb_accounts WHERE account_number = ?", (sb_account,))
            old_balance = c.fetchone()[0]
            new_balance = old_balance + maturity_amount
            c.execute("UPDATE sb_accounts SET balance = ? WHERE account_number = ?", (new_balance, sb_account))
            
            txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
            c.execute("INSERT INTO sb_transactions (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by) VALUES (?, ?, 'FD_Transfer', ?, ?, ?, ?, ?)",
                     (txn_id, sb_account, maturity_amount, old_balance, new_balance, f'FD Maturity - {fd_id}', created_by))
            
            fd_txn_id = f"FDT{uuid.uuid4().hex[:8].upper()}"
            c.execute("INSERT INTO fd_transactions (transaction_id, fd_id, transaction_type, amount, description, created_by) VALUES (?, ?, 'FD_Maturity', ?, ?, ?)",
                     (fd_txn_id, fd_id, maturity_amount, f'FD Matured - ₹{maturity_amount:,.2f}', created_by))
            
            voucher_id = JournalVoucherModule.create_auto_voucher('FD', datetime.now().date(), f'FD Maturity {fd_id}', created_by,
                [('SB_ACCOUNTS', 0, principal), ('FD_INVESTMENTS', 0, principal),
                 ('INTEREST_ON_FD', interest_earned, 0), ('SB_ACCOUNTS', 0, interest_earned)])
            c.execute("UPDATE sb_transactions SET voucher_id = ? WHERE transaction_id = ?", (voucher_id, txn_id))
            
            conn.commit()
            conn.close()
            return True, f"FD matured. ₹{maturity_amount:,.2f} credited"
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)

# ============================================
# RD ACCOUNT MODULE
# ============================================
class RDAccountModule:
    @staticmethod
    def generate_rd_id():
        return f"RD{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}"
    
    @staticmethod
    def open_rd(customer_id, sb_account, monthly_amount, interest_rate, tenure_months, nominee_id=None, created_by=None):
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("SELECT balance FROM sb_accounts WHERE account_number = ? AND customer_id = ? AND status = 'Active'",
                     (sb_account, customer_id))
            sb = c.fetchone()
            if not sb:
                conn.close()
                return False, "SB Account not found or inactive"
            
            rd_id = RDAccountModule.generate_rd_id()
            start_date = datetime.now().date()
            maturity_date = start_date + relativedelta(months=tenure_months)
            
            # Calculate RD maturity (compound interest formula)
            r = interest_rate / 400  # quarterly rate
            n = tenure_months / 3  # number of quarters
            maturity_amount = round(monthly_amount * (((1 + r) ** n - 1) / r) * (1 + r), 2)
            
            c.execute("INSERT INTO rd_accounts (rd_id, customer_id, sb_account, monthly_amount, interest_rate, tenure_months, start_date, maturity_date, maturity_amount, total_installments, nominee_id, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (rd_id, customer_id, sb_account, monthly_amount, interest_rate, tenure_months, start_date, maturity_date, maturity_amount, tenure_months, nominee_id, created_by))
            
            # Create installment schedule
            for i in range(tenure_months):
                due_date = start_date + relativedelta(months=i+1)
                c.execute("INSERT INTO rd_installments (rd_id, installment_number, due_date, amount) VALUES (?, ?, ?, ?)",
                         (rd_id, i+1, due_date, monthly_amount))
            
            # Pay first installment if balance available
            if sb[0] >= monthly_amount:
                old_balance, new_balance = sb[0], sb[0] - monthly_amount
                c.execute("UPDATE sb_accounts SET balance = ? WHERE account_number = ?", (new_balance, sb_account))
                c.execute("UPDATE rd_installments SET status = 'Paid', paid_date = ? WHERE rd_id = ? AND installment_number = 1",
                         (start_date, rd_id))
                c.execute("UPDATE rd_accounts SET installments_paid = 1 WHERE rd_id = ?", (rd_id,))
                
                txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
                c.execute("INSERT INTO sb_transactions (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by) VALUES (?, ?, 'RD_Transfer', ?, ?, ?, ?, ?)",
                         (txn_id, sb_account, monthly_amount, old_balance, new_balance, f'RD Installment 1/{tenure_months} - {rd_id}', created_by))
                
                voucher_id = JournalVoucherModule.create_auto_voucher('RD', start_date, f'RD {rd_id} Installment 1', created_by,
                    [('RD_INVESTMENTS', monthly_amount, 0), ('SB_ACCOUNTS', 0, monthly_amount)])
                c.execute("UPDATE sb_transactions SET voucher_id = ? WHERE transaction_id = ?", (voucher_id, txn_id))
            
            conn.commit()
            conn.close()
            return True, rd_id
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)
    
    @staticmethod
    def pay_installment(rd_id, created_by=None):
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("SELECT * FROM rd_accounts WHERE rd_id = ? AND status = 'Active'", (rd_id,))
            rd = c.fetchone()
            if not rd:
                conn.close()
                return False, "RD not found"
            
            c.execute("SELECT * FROM rd_installments WHERE rd_id = ? AND status = 'Pending' ORDER BY installment_number LIMIT 1", (rd_id,))
            inst = c.fetchone()
            if not inst:
                conn.close()
                return False, "All installments paid"
            
            c.execute("SELECT balance FROM sb_accounts WHERE account_number = ?", (rd[2],))
            sb_balance = c.fetchone()[0]
            if sb_balance < rd[3]:
                conn.close()
                return False, "Insufficient balance"
            
            new_balance = sb_balance - rd[3]
            c.execute("UPDATE sb_accounts SET balance = ? WHERE account_number = ?", (new_balance, rd[2]))
            c.execute("UPDATE rd_installments SET status = 'Paid', paid_date = ? WHERE rd_id = ? AND installment_number = ?",
                     (datetime.now().date(), rd_id, inst[1]))
            c.execute("UPDATE rd_accounts SET installments_paid = installments_paid + 1 WHERE rd_id = ?", (rd_id,))
            
            txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
            c.execute("INSERT INTO sb_transactions (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by) VALUES (?, ?, 'RD_Transfer', ?, ?, ?, ?, ?)",
                     (txn_id, rd[2], rd[3], sb_balance, new_balance, f'RD Installment {inst[1]}/{rd[9]} - {rd_id}', created_by))
            
            voucher_id = JournalVoucherModule.create_auto_voucher('RD', datetime.now().date(), f'RD {rd_id} Installment {inst[1]}', created_by,
                [('RD_INVESTMENTS', rd[3], 0), ('SB_ACCOUNTS', 0, rd[3])])
            c.execute("UPDATE sb_transactions SET voucher_id = ? WHERE transaction_id = ?", (voucher_id, txn_id))
            
            conn.commit()
            conn.close()
            return True, f"Installment {inst[1]}/{rd[9]} paid"
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)
    
    @staticmethod
    def mature_rd(rd_id, created_by=None):
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("SELECT * FROM rd_accounts WHERE rd_id = ? AND status = 'Active'", (rd_id,))
            rd = c.fetchone()
            if not rd:
                conn.close()
                return False, "RD not found"
            if rd[8] < rd[9]:
                conn.close()
                return False, f"All installments not paid ({rd[8]}/{rd[9]})"
            if datetime.now().date() < rd[6]:
                conn.close()
                return False, "RD not yet matured"
            
            interest = rd[7] - (rd[3] * rd[9])
            c.execute("UPDATE rd_accounts SET status = 'Matured' WHERE rd_id = ?", (rd_id,))
            
            c.execute("SELECT balance FROM sb_accounts WHERE account_number = ?", (rd[2],))
            old_balance = c.fetchone()[0]
            new_balance = old_balance + rd[7]
            c.execute("UPDATE sb_accounts SET balance = ? WHERE account_number = ?", (new_balance, rd[2]))
            
            txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
            c.execute("INSERT INTO sb_transactions (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by) VALUES (?, ?, 'RD_Transfer', ?, ?, ?, ?, ?)",
                     (txn_id, rd[2], rd[7], old_balance, new_balance, f'RD Maturity - {rd_id}', created_by))
            
            voucher_id = JournalVoucherModule.create_auto_voucher('RD', datetime.now().date(), f'RD Maturity {rd_id}', created_by,
                [('SB_ACCOUNTS', 0, rd[3] * rd[9]), ('RD_INVESTMENTS', 0, rd[3] * rd[9]),
                 ('INTEREST_ON_RD', interest, 0), ('SB_ACCOUNTS', 0, interest)])
            c.execute("UPDATE sb_transactions SET voucher_id = ? WHERE transaction_id = ?", (voucher_id, txn_id))
            
            conn.commit()
            conn.close()
            return True, f"RD matured. ₹{rd[7]:,.2f} credited"
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)

# ============================================
# JOURNAL VOUCHER MODULE
# ============================================
class JournalVoucherModule:
    @staticmethod
    def generate_voucher_id(voucher_type):
        prefix = {'Payment': 'PMT', 'Receipt': 'RCP', 'Journal': 'JNL', 'Contra': 'CNT', 'Interest': 'INT', 'FD': 'FDV', 'RD': 'RDV'}
        return f"{prefix.get(voucher_type, 'JNL')}{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}"
    
    @staticmethod
    def create_voucher(voucher_type, voucher_date, narration, entries, created_by):
        conn = db.get_connection()
        c = conn.cursor()
        try:
            total_debit = sum(e[1] for e in entries)
            total_credit = sum(e[2] for e in entries)
            if abs(total_debit - total_credit) > 0.01:
                conn.close()
                return False, "Debit and Credit must be equal"
            
            voucher_id = JournalVoucherModule.generate_voucher_id(voucher_type)
            c.execute("INSERT INTO journal_vouchers (voucher_id, voucher_type, voucher_date, narration, total_amount, status, created_by) VALUES (?, ?, ?, ?, ?, 'Approved', ?)",
                     (voucher_id, voucher_type, voucher_date, narration, total_debit, created_by))
            for acc_head, debit, credit in entries:
                c.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount) VALUES (?, ?, ?, ?)",
                         (voucher_id, acc_head, debit, credit))
            conn.commit()
            conn.close()
            return True, voucher_id
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)
    
    @staticmethod
    def create_auto_voucher(voucher_type, voucher_date, narration, created_by, entries):
        success, result = JournalVoucherModule.create_voucher(voucher_type, voucher_date, narration, entries, created_by)
        return result if success else None

# ============================================
# CUSTOMER MODULE
# ============================================
class CustomerModule:
    @staticmethod
    def generate_customer_id():
        return f"CUST{uuid.uuid4().hex[:8].upper()}"
    
    @staticmethod
    def register_customer(data, created_by):
        conn = db.get_connection()
        c = conn.cursor()
        try:
            customer_id = CustomerModule.generate_customer_id()
            c.execute("""INSERT INTO customers (customer_id, first_name, last_name, date_of_birth, gender, email, phone, address, city, state, pincode, occupation, annual_income, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (customer_id, data['first_name'], data['last_name'], data['date_of_birth'], data.get('gender'),
                 data.get('email'), data['phone'], data.get('address'), data.get('city'), data.get('state'),
                 data.get('pincode'), data.get('occupation'), data.get('annual_income'), created_by))
            
            if data.get('aadhaar_number'):
                c.execute("INSERT INTO kyc_documents (customer_id, doc_type, doc_number) VALUES (?, 'Aadhaar', ?)",
                         (customer_id, data['aadhaar_number']))
            if data.get('pan_number'):
                c.execute("INSERT INTO kyc_documents (customer_id, doc_type, doc_number) VALUES (?, 'PAN', ?)",
                         (customer_id, data['pan_number']))
            if data.get('nominee_name'):
                c.execute("INSERT INTO nominees (customer_id, nominee_name, relationship, date_of_birth, phone, percentage_share) VALUES (?, ?, ?, ?, ?, ?)",
                         (customer_id, data['nominee_name'], data.get('nominee_relationship'), data.get('nominee_dob'),
                          data.get('nominee_phone'), data.get('nominee_percentage', 100)))
            
            conn.commit()
            conn.close()
            return True, customer_id
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)
    
    @staticmethod
    def verify_kyc(customer_id, verified_by):
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("UPDATE customers SET kyc_status = 'Verified', kyc_verified_by = ?, kyc_verified_date = ? WHERE customer_id = ?",
                     (verified_by, datetime.now(), customer_id))
            c.execute("UPDATE kyc_documents SET verification_status = 'Verified', verified_by = ? WHERE customer_id = ?",
                     (verified_by, customer_id))
            conn.commit()
            conn.close()
            return True, "KYC Verified"
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)

# ============================================
# FINANCIAL REPORTING MODULE
# ============================================
class FinancialReportingModule:
    @staticmethod
    def get_trial_balance(as_of_date=None):
        if as_of_date is None:
            as_of_date = datetime.now().date()
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("""SELECT coa.account_head, coa.account_name, coa.account_type,
            COALESCE(SUM(je.debit_amount), 0) as total_debit, COALESCE(SUM(je.credit_amount), 0) as total_credit
            FROM chart_of_accounts coa
            LEFT JOIN journal_entries je ON coa.account_head = je.account_head
            LEFT JOIN journal_vouchers jv ON je.voucher_id = jv.voucher_id AND jv.voucher_date <= ? AND jv.status = 'Approved'
            WHERE coa.is_active = 1
            GROUP BY coa.account_head, coa.account_name, coa.account_type
            ORDER BY CASE coa.account_type WHEN 'Asset' THEN 1 WHEN 'Liability' THEN 2 WHEN 'Equity' THEN 3 WHEN 'Income' THEN 4 WHEN 'Expense' THEN 5 END, coa.account_head""",
            (as_of_date,))
        data = c.fetchall()
        conn.close()
        
        result, total_dr, total_cr = [], 0, 0
        for row in data:
            if row[2] in ('Asset', 'Expense'):
                net = row[3] - row[4]
                dr_bal, cr_bal = (net, 0) if net > 0 else (0, abs(net))
            else:
                net = row[4] - row[3]
                dr_bal, cr_bal = (0, net) if net > 0 else (abs(net), 0)
            total_dr += dr_bal
            total_cr += cr_bal
            result.append({'account_head': row[0], 'account_name': row[1], 'account_type': row[2], 'debit': dr_bal, 'credit': cr_bal})
        return result, total_dr, total_cr
    
    @staticmethod
    def get_balance_sheet(as_of_date=None):
        tb, _, _ = FinancialReportingModule.get_trial_balance(as_of_date)
        assets = [i for i in tb if i['account_type'] == 'Asset']
        liabilities = [i for i in tb if i['account_type'] == 'Liability']
        equity = [i for i in tb if i['account_type'] == 'Equity']
        
        total_assets = sum(i['debit'] - i['credit'] for i in assets)
        total_liabilities = sum(i['credit'] - i['debit'] for i in liabilities)
        total_equity = sum(i['credit'] - i['debit'] for i in equity)
        
        # Add P&L to equity
        income_items = [i for i in tb if i['account_type'] == 'Income']
        expense_items = [i for i in tb if i['account_type'] == 'Expense']
        net_profit = sum(i['credit'] - i['debit'] for i in income_items) - sum(i['debit'] - i['credit'] for i in expense_items)
        
        if net_profit > 0:
            equity.append({'account_head': 'PROFIT_LOSS', 'account_name': 'Profit & Loss Account', 'account_type': 'Equity', 'debit': 0, 'credit': net_profit})
            total_equity += net_profit
        
        return assets, liabilities, equity, total_assets, total_liabilities, total_equity

# ============================================
# SESSION STATE
# ============================================
def init_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = 'Vouchers'

# ============================================
# UI FUNCTIONS
# ============================================

def login_ui():
    st.markdown('<h1 class="main-header">🏦 Complete Banking System</h1>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.markdown('<h3 style="color: #a78bfa; text-align: center;">Secure Login</h3>', unsafe_allow_html=True)
            username = st.text_input("👤 Username")
            password = st.text_input("🔒 Password", type="password")
            if st.form_submit_button("🔐 Login", use_container_width=True):
                user = AuthModule.authenticate(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.success(f"Welcome, {user['full_name']}!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        st.markdown("""<div class="info-box"><strong>Demo:</strong> admin/admin123 | manager/manager123 | user1/user123</div>""", unsafe_allow_html=True)

def voucher_ui():
    st.markdown('<h2 class="sub-header">📊 Journal Voucher Creation</h2>', unsafe_allow_html=True)
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT account_head, account_name, account_type FROM chart_of_accounts WHERE is_active = 1 ORDER BY account_type, account_head")
    accounts = c.fetchall()
    conn.close()
    account_options = [f"{acc[0]} - {acc[1]} ({acc[2]})" for acc in accounts]
    
    with st.form("voucher_form"):
        col1, col2 = st.columns(2)
        with col1:
            voucher_type = st.selectbox("Voucher Type", ['Payment', 'Receipt', 'Journal', 'Contra', 'Interest'])
        with col2:
            voucher_date = st.date_input("Voucher Date", datetime.now().date())
        narration = st.text_area("Narration *")
        
        st.markdown("#### 🔴 Debit Entries")
        debit_entries = []
        for i in range(3):
            c1, c2 = st.columns([3, 1])
            with c1:
                acc = st.selectbox(f"Debit {i+1}", [""] + account_options, key=f"dr_{i}")
            with c2:
                amt = st.number_input(f"Amount {i+1}", 0.0, step=100.0, key=f"dramt_{i}")
            if acc and amt > 0:
                debit_entries.append((acc.split(" - ")[0], amt, 0))
        
        st.markdown("#### 🟢 Credit Entries")
        credit_entries = []
        for i in range(3):
            c1, c2 = st.columns([3, 1])
            with c1:
                acc = st.selectbox(f"Credit {i+1}", [""] + account_options, key=f"cr_{i}")
            with c2:
                amt = st.number_input(f"Amount {i+1}", 0.0, step=100.0, key=f"cramt_{i}")
            if acc and amt > 0:
                credit_entries.append((acc.split(" - ")[0], 0, amt))
        
        all_entries = debit_entries + credit_entries
        total_dr = sum(e[1] for e in all_entries)
        total_cr = sum(e[2] for e in all_entries)
        
        c1, c2 = st.columns(2)
        c1.metric("Total Debit", f"₹{total_dr:,.2f}")
        c2.metric("Total Credit", f"₹{total_cr:,.2f}")
        
        if st.form_submit_button("Create Voucher", use_container_width=True):
            if not narration:
                st.error("Narration required!")
            elif abs(total_dr - total_cr) > 0.01:
                st.error("Debit and Credit must be equal!")
            else:
                success, result = JournalVoucherModule.create_voucher(voucher_type, voucher_date, narration, all_entries, st.session_state.user['user_id'])
                if success:
                    st.success(f"Voucher created! ID: {result}")
                    st.balloons()
                else:
                    st.error(result)
    
    st.markdown("### Recent Vouchers")
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT voucher_id, voucher_type, voucher_date, narration, total_amount, status FROM journal_vouchers ORDER BY created_at DESC LIMIT 10")
    vouchers = c.fetchall()
    conn.close()
    if vouchers:
        for v in vouchers:
            with st.expander(f"{v[0]} | {v[1]} | ₹{v[4]:,.2f} | {v[3]}"):
                conn = db.get_connection()
                c = conn.cursor()
                c.execute("SELECT je.account_head, coa.account_name, je.debit_amount, je.credit_amount FROM journal_entries je JOIN chart_of_accounts coa ON je.account_head = coa.account_head WHERE je.voucher_id = ?", (v[0],))
                entries = c.fetchall()
                conn.close()
                for e in entries:
                    if e[2] > 0:
                        st.write(f"🔴 Dr: {e[1]} - ₹{e[2]:,.2f}")
                    if e[3] > 0:
                        st.write(f"🟢 Cr: {e[1]} - ₹{e[3]:,.2f}")

def sb_account_ui():
    st.markdown('<h2 class="sub-header">💰 Savings Bank Account</h2>', unsafe_allow_html=True)
    tab1, tab2, tab3, tab4 = st.tabs(["Open Account", "Deposit/Withdraw", "Interest Calculation", "Account List"])
    
    with tab1:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT customer_id, first_name, last_name FROM customers WHERE kyc_status = 'Verified'")
        customers = c.fetchall()
        conn.close()
        if customers:
            with st.form("open_sb"):
                cust_options = {f"{c[1]} {c[2]} ({c[0]})": c[0] for c in customers}
                selected = st.selectbox("Customer *", list(cust_options.keys()))
                c1, c2 = st.columns(2)
                with c1:
                    deposit = st.number_input("Initial Deposit", 0.0, step=500.0)
                    rate = st.number_input("Interest Rate (%)", 0.0, 4.0, 0.25)
                with c2:
                    st.info("📌 Zero Balance Account (Min: ₹0)")
                if st.form_submit_button("Open Account", use_container_width=True):
                    success, result = SBAccountModule.open_account(cust_options[selected], deposit, rate, created_by=st.session_state.user['user_id'])
                    if success:
                        st.success(f"Account opened! Number: {result}")
                        st.balloons()
                    else:
                        st.error(result)
        else:
            st.warning("No verified customers")
    
    with tab2:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT sa.account_number, c.first_name || ' ' || c.last_name, sa.balance FROM sb_accounts sa JOIN customers c ON sa.customer_id = c.customer_id WHERE sa.status = 'Active'")
        accounts = c.fetchall()
        conn.close()
        if accounts:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 💚 Deposit")
                with st.form("deposit"):
                    opts = {f"{a[1]} - {a[0]} (₹{a[2]:,.2f})": a for a in accounts}
                    acc = st.selectbox("Account", list(opts.keys()), key="dep")
                    amt = st.number_input("Amount *", 1.0, step=100.0, key="dep_amt")
                    desc = st.text_input("Description", key="dep_desc")
                    if st.form_submit_button("Deposit 💰"):
                        success, msg = SBAccountModule.deposit(opts[acc][0], amt, desc, st.session_state.user['user_id'])
                        st.success(msg) if success else st.error(msg)
            with c2:
                st.markdown("#### 🔴 Withdraw")
                with st.form("withdraw"):
                    opts = {f"{a[1]} - {a[0]} (₹{a[2]:,.2f})": a for a in accounts}
                    acc = st.selectbox("Account", list(opts.keys()), key="wit")
                    a = opts[acc]
                    amt = st.number_input("Amount *", 0.0, float(a[2]), step=100.0, key="wit_amt")
                    desc = st.text_input("Description", key="wit_desc")
                    if st.form_submit_button("Withdraw 💸"):
                        success, msg = SBAccountModule.withdraw(a[0], amt, desc, st.session_state.user['user_id'])
                        st.success(msg) if success else st.error(msg)
    
    with tab3:
        st.markdown("### Quarterly Interest Calculation")
        if st.button("🧮 Calculate Interest", use_container_width=True):
            with st.spinner("Calculating..."):
                success, results = SBAccountModule.calculate_quarterly_interest(st.session_state.user['user_id'])
                if success:
                    st.success("Interest calculated!")
                    df = pd.DataFrame(results)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.warning(results)
        
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM interest_calculations ORDER BY calculated_at DESC LIMIT 20")
        history = c.fetchall()
        conn.close()
        if history:
            st.markdown("### Interest History")
            hist_data = [{'Account': h[1], 'Period': f"{h[2]} to {h[3]}", 'Min Balance': f"₹{h[4]:,.2f}", 'Rate': f"{h[5]}%", 'Interest': f"₹{h[6]:,.2f}", 'Credited': '✅' if h[7] else '⏳'} for h in history]
            st.dataframe(pd.DataFrame(hist_data), use_container_width=True, hide_index=True)
    
    with tab4:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT sa.account_number, c.first_name || ' ' || c.last_name, sa.balance, sa.interest_rate, sa.opened_date, sa.status FROM sb_accounts sa JOIN customers c ON sa.customer_id = c.customer_id ORDER BY sa.opened_date DESC")
        accounts = c.fetchall()
        conn.close()
        if accounts:
            df = pd.DataFrame(accounts, columns=['Account', 'Customer', 'Balance', 'Rate', 'Opened', 'Status'])
            df['Balance'] = df['Balance'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(df, use_container_width=True, hide_index=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Accounts", len(accounts))
            c2.metric("Active", sum(1 for a in accounts if a[5] == 'Active'))
            c3.metric("Total Deposits", f"₹{sum(a[2] for a in accounts):,.2f}")

def fd_account_ui():
    st.markdown('<h2 class="sub-header">🏦 Fixed Deposit Management</h2>', unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["Open FD", "Mature FD", "FD List"])
    
    with tab1:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT sa.account_number, sa.customer_id, c.first_name, c.last_name, sa.balance FROM sb_accounts sa JOIN customers c ON sa.customer_id = c.customer_id WHERE sa.status = 'Active'")
        accounts = c.fetchall()
        conn.close()
        if accounts:
            with st.form("open_fd"):
                opts = {}
                for a in accounts:
                    opts[f"{a[2]} {a[3]} - {a[0]} (₹{a[4]:,.2f})"] = a
                selected = st.selectbox("SB Account *", list(opts.keys()))
                acc = opts[selected]
                st.info(f"Customer: {acc[1]} | Balance: ₹{acc[4]:,.2f}")
                c1, c2, c3 = st.columns(3)
                with c1:
                    principal = st.number_input("Principal *", 100.0, float(acc[4]), step=1000.0)
                with c2:
                    rate = st.number_input("Interest Rate (%)", 1.0, 7.0, 0.5)
                with c3:
                    tenure = st.selectbox("Tenure (Months)", [3, 6, 12, 24, 36, 48, 60])
                if principal > 0:
                    maturity = principal * (1 + (rate/1200) * tenure)
                    st.info(f"Maturity Amount: ₹{maturity:,.2f}")
                if st.form_submit_button("Open FD", use_container_width=True):
                    success, result = FDAccountModule.open_fd(acc[1], acc[0], principal, rate, tenure, created_by=st.session_state.user['user_id'])
                    if success:
                        st.success(f"FD created! ID: {result}")
                        st.balloons()
                    else:
                        st.error(result)
    
    with tab2:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT fd.*, c.first_name, c.last_name FROM fd_accounts fd JOIN customers c ON fd.customer_id = c.customer_id WHERE fd.status = 'Active' AND fd.maturity_date <= ?", (datetime.now().date(),))
        fds = c.fetchall()
        conn.close()
        if fds:
            for fd in fds:
                with st.expander(f"{fd[0]} | ₹{fd[3]:,.2f} | Maturity: ₹{fd[7]:,.2f}"):
                    st.write(f"Customer: {fd[10]} {fd[11]}")
                    st.write(f"Start: {fd[5]} | Maturity: {fd[6]}")
                    if st.button("Mature", key=f"mat_{fd[0]}"):
                        success, msg = FDAccountModule.mature_fd(fd[0], st.session_state.user['user_id'])
                        st.success(msg) if success else st.error(msg)
                        if success:
                            st.rerun()
        else:
            st.info("No FDs ready for maturity")
    
    with tab3:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT fd.*, c.first_name, c.last_name FROM fd_accounts fd JOIN customers c ON fd.customer_id = c.customer_id ORDER BY fd.start_date DESC")
        fds = c.fetchall()
        conn.close()
        if fds:
            fd_data = [{'FD ID': f[0], 'Customer': f"{f[10]} {f[11]}", 'Principal': f"₹{f[3]:,.2f}", 'Rate': f"{f[4]}%", 'Tenure': f"{f[5]}m", 'Maturity': f"₹{f[7]:,.2f}", 'Status': f[8]} for f in fds]
            st.dataframe(pd.DataFrame(fd_data), use_container_width=True, hide_index=True)

def rd_account_ui():
    st.markdown('<h2 class="sub-header">📅 Recurring Deposit Management</h2>', unsafe_allow_html=True)
    tab1, tab2, tab3, tab4 = st.tabs(["Open RD", "Pay Installment", "Mature RD", "RD List"])
    
    with tab1:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT sa.account_number, sa.customer_id, c.first_name, c.last_name, sa.balance FROM sb_accounts sa JOIN customers c ON sa.customer_id = c.customer_id WHERE sa.status = 'Active'")
        accounts = c.fetchall()
        conn.close()
        if accounts:
            with st.form("open_rd"):
                opts = {f"{a[2]} {a[3]} - {a[0]} (₹{a[4]:,.2f})": a for a in accounts}
                selected = st.selectbox("SB Account *", list(opts.keys()))
                acc = opts[selected]
                c1, c2, c3 = st.columns(3)
                with c1:
                    monthly = st.number_input("Monthly Amount *", 100.0, step=100.0)
                with c2:
                    rate = st.number_input("Interest Rate (%)", 1.0, 6.5, 0.5)
                with c3:
                    tenure = st.selectbox("Tenure (Months)", [12, 24, 36, 48, 60])
                if st.form_submit_button("Open RD", use_container_width=True):
                    success, result = RDAccountModule.open_rd(acc[1], acc[0], monthly, rate, tenure, created_by=st.session_state.user['user_id'])
                    if success:
                        st.success(f"RD created! ID: {result}")
                        st.balloons()
                    else:
                        st.error(result)
    
    with tab2:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT rd.*, c.first_name, c.last_name FROM rd_accounts rd JOIN customers c ON rd.customer_id = c.customer_id WHERE rd.status = 'Active'")
        rds = c.fetchall()
        conn.close()
        if rds:
            for rd in rds:
                with st.expander(f"{rd[0]} | Monthly: ₹{rd[3]:,.2f} | Paid: {rd[8]}/{rd[9]}"):
                    st.write(f"Customer: {rd[12]} {rd[13]}")
                    conn = db.get_connection()
                    c = conn.cursor()
                    c.execute("SELECT * FROM rd_installments WHERE rd_id = ? AND status = 'Pending' ORDER BY installment_number LIMIT 1", (rd[0],))
                    inst = c.fetchone()
                    conn.close()
                    if inst:
                        st.info(f"Next: Installment #{inst[1]} - ₹{inst[4]:,.2f} (Due: {inst[2]})")
                        if st.button("Pay", key=f"pay_{rd[0]}"):
                            success, msg = RDAccountModule.pay_installment(rd[0], st.session_state.user['user_id'])
                            st.success(msg) if success else st.error(msg)
                            if success:
                                st.rerun()
        else:
            st.info("No active RDs")
    
    with tab3:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT rd.*, c.first_name, c.last_name FROM rd_accounts rd JOIN customers c ON rd.customer_id = c.customer_id WHERE rd.status = 'Active' AND rd.installments_paid >= rd.total_installments")
        rds = c.fetchall()
        conn.close()
        if rds:
            for rd in rds:
                with st.expander(f"{rd[0]} | Maturity: ₹{rd[7]:,.2f}"):
                    if st.button("Mature", key=f"mat_{rd[0]}"):
                        success, msg = RDAccountModule.mature_rd(rd[0], st.session_state.user['user_id'])
                        st.success(msg) if success else st.error(msg)
                        if success:
                            st.rerun()
        else:
            st.info("No RDs ready for maturity")
    
    with tab4:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT rd.*, c.first_name, c.last_name FROM rd_accounts rd JOIN customers c ON rd.customer_id = c.customer_id ORDER BY rd.start_date DESC")
        rds = c.fetchall()
        conn.close()
        if rds:
            rd_data = [{'RD ID': r[0], 'Customer': f"{r[12]} {r[13]}", 'Monthly': f"₹{r[3]:,.2f}", 'Rate': f"{r[4]}%", 'Paid': f"{r[8]}/{r[9]}", 'Maturity': f"₹{r[7]:,.2f}", 'Status': r[11]} for r in rds]
            st.dataframe(pd.DataFrame(rd_data), use_container_width=True, hide_index=True)

def customer_ui():
    st.markdown('<h2 class="sub-header">👤 Customer Management</h2>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Register", "Customer List"])
    
    with tab1:
        with st.form("reg_cust"):
            c1, c2, c3 = st.columns(3)
            with c1:
                fn = st.text_input("First Name *")
                dob = st.date_input("DOB *", datetime.now()-timedelta(days=365*18))
                email = st.text_input("Email")
            with c2:
                ln = st.text_input("Last Name *")
                gender = st.selectbox("Gender", ['Male', 'Female', 'Other'])
                phone = st.text_input("Phone *")
            with c3:
                addr = st.text_area("Address")
                city = st.text_input("City")
                state = st.text_input("State")
                pin = st.text_input("Pincode")
            
            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                aadhaar = st.text_input("Aadhaar")
            with c2:
                pan = st.text_input("PAN")
            
            if st.form_submit_button("Register", use_container_width=True):
                if not fn or not ln or not phone:
                    st.error("Required fields missing!")
                else:
                    data = {'first_name': fn, 'last_name': ln, 'date_of_birth': dob, 'gender': gender,
                            'email': email, 'phone': phone, 'address': addr, 'city': city, 'state': state,
                            'pincode': pin, 'aadhaar_number': aadhaar, 'pan_number': pan}
                    success, result = CustomerModule.register_customer(data, st.session_state.user['user_id'])
                    st.success(f"Customer registered! ID: {result}") if success else st.error(result)
    
    with tab2:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT customer_id, first_name, last_name, phone, email, kyc_status FROM customers ORDER BY created_at DESC")
        customers = c.fetchall()
        conn.close()
        if customers:
            for row in customers:
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.markdown(f"**{row[1]} {row[2]}** | 🆔 {row[0]} | 📞 {row[3]}")
                if row[5] == 'Verified':
                    c2.markdown('<span class="badge badge-success">✅ Verified</span>', unsafe_allow_html=True)
                else:
                    c2.markdown(f'<span class="badge badge-warning">⏳ {row[5]}</span>', unsafe_allow_html=True)
                    if st.session_state.user['role'] in ['Admin', 'Manager']:
                        if c3.button("Verify", key=f"v_{row[0]}"):
                            CustomerModule.verify_kyc(row[0], st.session_state.user['user_id'])
                            st.rerun()
                st.divider()

def reports_ui():
    st.markdown('<h2 class="sub-header">📈 Financial Reports</h2>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📊 Trial Balance", "💰 Balance Sheet"])
    
    with tab1:
        dt = st.date_input("As of Date", datetime.now().date(), key="tb")
        if st.button("Generate Trial Balance", use_container_width=True):
            data, td, tc = FinancialReportingModule.get_trial_balance(dt)
            if data:
                df_data = [{'Account': i['account_head'], 'Name': i['account_name'], 'Type': i['account_type'],
                           'Debit': f"₹{i['debit']:,.2f}" if i['debit'] > 0 else "-",
                           'Credit': f"₹{i['credit']:,.2f}" if i['credit'] > 0 else "-"} for i in data]
                df_data.append({'Account': 'TOTAL', 'Name': '', 'Type': '', 'Debit': f"₹{td:,.2f}", 'Credit': f"₹{tc:,.2f}"})
                st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)
                if abs(td - tc) < 0.01:
                    st.success(f"✅ Balanced! Total: ₹{td:,.2f}")
                else:
                    st.error(f"❌ Not Balanced! Difference: ₹{abs(td-tc):,.2f}")
    
    with tab2:
        dt = st.date_input("As at", datetime.now().date(), key="bs")
        if st.button("Generate Balance Sheet", use_container_width=True):
            assets, liab, equity, ta, tl, te = FinancialReportingModule.get_balance_sheet(dt)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 🟢 ASSETS")
                for i in assets:
                    amt = i['debit'] - i['credit']
                    if amt != 0:
                        st.write(f"- {i['account_name']}: ₹{amt:,.2f}")
                st.markdown(f"**Total: ₹{ta:,.2f}**")
            with c2:
                st.markdown("#### 🔴 LIABILITIES & EQUITY")
                for i in liab:
                    amt = i['credit'] - i['debit']
                    if amt != 0:
                        st.write(f"- {i['account_name']}: ₹{amt:,.2f}")
                for i in equity:
                    amt = i['credit'] - i['debit']
                    if amt != 0:
                        st.write(f"- {i['account_name']}: ₹{amt:,.2f}")
                st.markdown(f"**Total: ₹{tl+te:,.2f}**")
            if abs(ta - (tl+te)) < 0.01:
                st.success("✅ Balanced!")
            else:
                st.error(f"❌ Not Balanced! Difference: ₹{abs(ta-(tl+te)):,.2f}")

def head_management_ui():
    st.markdown('<h2 class="sub-header">📋 Chart of Accounts</h2>', unsafe_allow_html=True)
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM chart_of_accounts WHERE is_active = 1 ORDER BY account_type, account_head")
    accounts = c.fetchall()
    conn.close()
    if accounts:
        df = pd.DataFrame(accounts, columns=['Head', 'Name', 'Type', 'Category', 'Sub Category', 'Active', 'Created'])
        st.dataframe(df[['Head', 'Name', 'Type', 'Category', 'Sub Category']], use_container_width=True, hide_index=True)
        counts = df['Type'].value_counts()
        cols = st.columns(len(counts))
        for i, (t, c) in enumerate(counts.items()):
            cols[i].metric(t, c)

def verification_ui():
    st.markdown('<h2 class="sub-header">✅ Voucher Verification</h2>', unsafe_allow_html=True)
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT voucher_id, voucher_type, voucher_date, narration, total_amount, verification_status FROM journal_vouchers WHERE verification_status = 'Pending' ORDER BY created_at DESC")
    vouchers = c.fetchall()
    conn.close()
    if vouchers:
        for v in vouchers:
            with st.expander(f"{v[0]} | {v[1]} | ₹{v[4]:,.2f} | {v[3]}"):
                conn = db.get_connection()
                c = conn.cursor()
                c.execute("SELECT je.account_head, coa.account_name, je.debit_amount, je.credit_amount FROM journal_entries je JOIN chart_of_accounts coa ON je.account_head = coa.account_head WHERE je.voucher_id = ?", (v[0],))
                entries = c.fetchall()
                conn.close()
                for e in entries:
                    if e[2] > 0:
                        st.write(f"🔴 Dr: {e[1]} - ₹{e[2]:,.2f}")
                    if e[3] > 0:
                        st.write(f"🟢 Cr: {e[1]} - ₹{e[3]:,.2f}")
                c1, c2 = st.columns(2)
                if c1.button("✅ Verify", key=f"ve_{v[0]}"):
                    conn = db.get_connection()
                    c = conn.cursor()
                    c.execute("UPDATE journal_vouchers SET verification_status = 'Verified', verified_by = ? WHERE voucher_id = ?", (st.session_state.user['user_id'], v[0]))
                    conn.commit()
                    conn.close()
                    st.rerun()
                if c2.button("❌ Reject", key=f"re_{v[0]}"):
                    conn = db.get_connection()
                    c = conn.cursor()
                    c.execute("UPDATE journal_vouchers SET verification_status = 'Rejected', verified_by = ? WHERE voucher_id = ?", (st.session_state.user['user_id'], v[0]))
                    conn.commit()
                    conn.close()
                    st.rerun()
    else:
        st.success("No pending vouchers")

# ============================================
# MAIN APPLICATION
# ============================================
def main():
    init_session_state()
    
    try:
        db.initialize_database()
    except Exception as e:
        st.error(f"Database error: {e}")
        if st.button("Reset Database"):
            if os.path.exists('complete_banking.db'):
                os.remove('complete_banking.db')
            st.rerun()
        return
    
    if not st.session_state.logged_in:
        login_ui()
        return
    
    with st.sidebar:
        st.markdown(f"""
            <div style='text-align: center; padding: 1rem 0;'>
                <h3 style='color: #a78bfa;'>🏦 Banking System</h3>
                <p style='color: #94a3b8;'>{st.session_state.user['full_name']}</p>
                <span class="badge badge-info">{st.session_state.user['role']}</span>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        
        tabs = {
            'Vouchers': '📊 Journal Vouchers',
            'SB Accounts': '💰 SB Accounts',
            'FD Accounts': '🏦 FD Accounts',
            'RD Accounts': '📅 RD Accounts',
            'Customers': '👤 Customers',
            'Reports': '📈 Reports',
            'Head Management': '🔧 Chart of Accounts',
            'Verification': '✅ Verification'
        }
        
        selected = st.radio("Navigation", list(tabs.keys()), format_func=lambda x: tabs[x], label_visibility="collapsed")
        st.session_state.current_tab = selected
        
        st.markdown("---")
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*), COALESCE(SUM(balance), 0) FROM sb_accounts WHERE status='Active'")
        stats = c.fetchone()
        conn.close()
        st.metric("Active Accounts", stats[0])
        st.metric("Total Deposits", f"₹{stats[1]:,.2f}")
        
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            AuthModule.logout(st.session_state.user['user_id'], st.session_state.user.get('session_id', ''))
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()
    
    # Route to appropriate UI
    if st.session_state.current_tab == 'Vouchers':
        voucher_ui()
    elif st.session_state.current_tab == 'SB Accounts':
        sb_account_ui()
    elif st.session_state.current_tab == 'FD Accounts':
        fd_account_ui()
    elif st.session_state.current_tab == 'RD Accounts':
        rd_account_ui()
    elif st.session_state.current_tab == 'Customers':
        customer_ui()
    elif st.session_state.current_tab == 'Reports':
        reports_ui()
    elif st.session_state.current_tab == 'Head Management':
        head_management_ui()
    elif st.session_state.current_tab == 'Verification':
        verification_ui()

if __name__ == "__main__":
    main()
