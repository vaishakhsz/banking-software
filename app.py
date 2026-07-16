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
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0d1128 100%);
    }
    
    .main-header {
        font-size: 2.8rem;
        background: linear-gradient(120deg, #667eea, #764ba2, #f093fb);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 700;
        text-shadow: 0 0 40px rgba(102, 126, 234, 0.3);
    }
    
    .sub-header {
        font-size: 1.6rem;
        color: #a78bfa;
        margin-bottom: 1.5rem;
        font-weight: 600;
        border-bottom: 2px solid #2d2b55;
        padding-bottom: 0.5rem;
    }
    
    .card {
        background: linear-gradient(135deg, rgba(26, 31, 58, 0.9), rgba(45, 43, 85, 0.9));
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
    }
    
    .success-box {
        padding: 1.2rem;
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.1));
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 12px;
        color: #6ee7b7;
        border-left: 4px solid #10b981;
        margin: 1rem 0;
    }
    
    .error-box {
        padding: 1.2rem;
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(220, 38, 38, 0.1));
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 12px;
        color: #fca5a5;
        border-left: 4px solid #ef4444;
        margin: 1rem 0;
    }
    
    .info-box {
        padding: 1.2rem;
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(37, 99, 235, 0.1));
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 12px;
        color: #93c5fd;
        border-left: 4px solid #3b82f6;
        margin: 1rem 0;
    }
    
    .warning-box {
        padding: 1.2rem;
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(217, 119, 6, 0.1));
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 12px;
        color: #fcd34d;
        border-left: 4px solid #f59e0b;
        margin: 1rem 0;
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
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 20px rgba(102, 126, 234, 0.3) !important;
    }
    
    .stTextInput > label,
    .stNumberInput > label,
    .stSelectbox > label,
    .stTextArea > label {
        color: #c4b5fd !important;
        font-weight: 500 !important;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4) !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 12px 35px rgba(102, 126, 234, 0.6) !important;
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%) !important;
    }
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0e27 0%, #1a1f3a 100%) !important;
        border-right: 1px solid rgba(102, 126, 234, 0.2) !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(15, 18, 35, 0.6) !important;
        border-radius: 15px !important;
        padding: 0.5rem !important;
        gap: 0.5rem !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: #94a3b8 !important;
        border-radius: 10px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 500 !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2)) !important;
        color: #a78bfa !important;
        border: 1px solid rgba(102, 126, 234, 0.3) !important;
    }
    
    .stDataFrame {
        background: rgba(15, 18, 35, 0.8) !important;
        border-radius: 15px !important;
        border: 1px solid rgba(102, 126, 234, 0.2) !important;
    }
    
    .stDataFrame th {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2)) !important;
        color: #c4b5fd !important;
        font-weight: 600 !important;
    }
    
    .stDataFrame td {
        color: #e2e8f0 !important;
        border-bottom: 1px solid rgba(102, 126, 234, 0.1) !important;
    }
    
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(26, 31, 58, 0.9), rgba(45, 43, 85, 0.9));
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 15px;
        padding: 1.5rem !important;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
    }
    
    [data-testid="stMetric"] label {
        color: #94a3b8 !important;
        font-weight: 500 !important;
    }
    
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #a78bfa !important;
        font-weight: 700 !important;
    }
    
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(15, 18, 35, 0.5);
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea, #764ba2);
        border-radius: 10px;
    }
    
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    .badge-success {
        background: rgba(16, 185, 129, 0.2);
        color: #6ee7b7;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .badge-warning {
        background: rgba(245, 158, 11, 0.2);
        color: #fcd34d;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    
    .badge-info {
        background: rgba(59, 130, 246, 0.2);
        color: #93c5fd;
        border: 1px solid rgba(59, 130, 246, 0.3);
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
        
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        
        # Users
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE,
            role TEXT NOT NULL CHECK(role IN ('Admin', 'Manager', 'User')),
            is_active INTEGER DEFAULT 1,
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS user_sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER REFERENCES users(user_id),
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            logout_time TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )''')
        
        # Customers
        c.execute('''CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            date_of_birth DATE NOT NULL,
            gender TEXT,
            email TEXT UNIQUE,
            phone TEXT NOT NULL,
            address TEXT,
            city TEXT,
            state TEXT,
            pincode TEXT,
            occupation TEXT,
            annual_income REAL,
            kyc_status TEXT DEFAULT 'Pending',
            kyc_verified_by INTEGER REFERENCES users(user_id),
            kyc_verified_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER REFERENCES users(user_id)
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS kyc_documents (
            doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT REFERENCES customers(customer_id),
            doc_type TEXT NOT NULL,
            doc_number TEXT,
            verification_status TEXT DEFAULT 'Pending',
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verified_by INTEGER REFERENCES users(user_id)
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS nominees (
            nominee_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT REFERENCES customers(customer_id),
            nominee_name TEXT NOT NULL,
            relationship TEXT NOT NULL,
            date_of_birth DATE,
            phone TEXT,
            percentage_share REAL DEFAULT 100.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Accounts
        c.execute('''CREATE TABLE IF NOT EXISTS sb_accounts (
            account_number TEXT PRIMARY KEY,
            customer_id TEXT REFERENCES customers(customer_id),
            account_type TEXT DEFAULT 'Savings',
            balance REAL DEFAULT 0.00,
            interest_rate REAL DEFAULT 4.00,
            min_balance REAL DEFAULT 0.00,
            opened_date DATE NOT NULL,
            last_interest_date DATE,
            status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Dormant', 'Closed', 'Frozen')),
            nominee_id INTEGER REFERENCES nominees(nominee_id),
            created_by INTEGER REFERENCES users(user_id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS fd_accounts (
            fd_id TEXT PRIMARY KEY,
            customer_id TEXT REFERENCES customers(customer_id),
            sb_account TEXT REFERENCES sb_accounts(account_number),
            principal_amount REAL NOT NULL,
            interest_rate REAL NOT NULL,
            tenure_months INTEGER NOT NULL,
            start_date DATE NOT NULL,
            maturity_date DATE NOT NULL,
            maturity_amount REAL,
            status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Matured', 'Premature_Closed')),
            nominee_id INTEGER REFERENCES nominees(nominee_id),
            created_by INTEGER REFERENCES users(user_id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS rd_accounts (
            rd_id TEXT PRIMARY KEY,
            customer_id TEXT REFERENCES customers(customer_id),
            sb_account TEXT REFERENCES sb_accounts(account_number),
            monthly_amount REAL NOT NULL,
            interest_rate REAL NOT NULL,
            tenure_months INTEGER NOT NULL,
            start_date DATE NOT NULL,
            maturity_date DATE NOT NULL,
            maturity_amount REAL,
            installments_paid INTEGER DEFAULT 0,
            total_installments INTEGER NOT NULL,
            status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Matured', 'Closed', 'Defaulted')),
            nominee_id INTEGER REFERENCES nominees(nominee_id),
            created_by INTEGER REFERENCES users(user_id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS rd_installments (
            installment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            rd_id TEXT REFERENCES rd_accounts(rd_id),
            installment_number INTEGER NOT NULL,
            due_date DATE NOT NULL,
            paid_date DATE,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Paid', 'Defaulted')),
            voucher_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Vouchers
        c.execute('''CREATE TABLE IF NOT EXISTS journal_vouchers (
            voucher_id TEXT PRIMARY KEY,
            voucher_type TEXT NOT NULL,
            voucher_date DATE NOT NULL,
            narration TEXT NOT NULL,
            total_amount REAL NOT NULL DEFAULT 0.00,
            status TEXT DEFAULT 'Approved',
            is_posted INTEGER DEFAULT 0,
            created_by INTEGER REFERENCES users(user_id),
            approved_by INTEGER REFERENCES users(user_id),
            verified_by INTEGER REFERENCES users(user_id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_at TIMESTAMP,
            verification_status TEXT DEFAULT 'Pending'
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS journal_entries (
            entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_id TEXT REFERENCES journal_vouchers(voucher_id),
            account_head TEXT,
            debit_amount REAL DEFAULT 0.00,
            credit_amount REAL DEFAULT 0.00,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS chart_of_accounts (
            account_head TEXT PRIMARY KEY,
            account_name TEXT NOT NULL,
            account_type TEXT NOT NULL,
            category TEXT NOT NULL,
            sub_category TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Transactions
        c.execute('''CREATE TABLE IF NOT EXISTS sb_transactions (
            transaction_id TEXT PRIMARY KEY,
            account_number TEXT REFERENCES sb_accounts(account_number),
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            balance_before REAL,
            balance_after REAL,
            description TEXT,
            voucher_id TEXT,
            created_by INTEGER REFERENCES users(user_id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS fd_transactions (
            transaction_id TEXT PRIMARY KEY,
            fd_id TEXT REFERENCES fd_accounts(fd_id),
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            voucher_id TEXT,
            created_by INTEGER REFERENCES users(user_id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS interest_calculations (
            calc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT REFERENCES sb_accounts(account_number),
            interest_period_start DATE,
            interest_period_end DATE,
            minimum_balance REAL,
            interest_rate REAL,
            interest_amount REAL,
            is_credited INTEGER DEFAULT 0,
            voucher_id TEXT,
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS audit_trail (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            module TEXT NOT NULL,
            action TEXT NOT NULL,
            record_type TEXT,
            record_id TEXT,
            old_data TEXT,
            new_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Insert default data
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
        
        c.execute("SELECT COUNT(*) FROM chart_of_accounts")
        if c.fetchone()[0] == 0:
            accounts = [
                ('CASH_IN_HAND', 'Cash in Hand', 'Asset', 'Current Asset', 'Cash'),
                ('BANK_ACCOUNTS', 'Bank Accounts', 'Asset', 'Current Asset', 'Bank'),
                ('FD_INVESTMENTS', 'FD Investments', 'Asset', 'Investment', 'FD'),
                ('RD_INVESTMENTS', 'RD Investments', 'Asset', 'Investment', 'RD'),
                ('LOANS_RECEIVABLE', 'Loans Receivable', 'Asset', 'Current Asset', 'Loans'),
                ('FURNITURE', 'Furniture & Fixtures', 'Asset', 'Fixed Asset', 'Office'),
                ('COMPUTERS', 'Computer Equipment', 'Asset', 'Fixed Asset', 'IT'),
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
            return {
                'user_id': user[0], 'username': user[1], 'full_name': user[2],
                'role': user[3], 'email': user[4], 'session_id': session_id
            }
        conn.close()
        return None

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
            
            # FIXED: Minimum deposit is 0, not 500
            if initial_deposit < 0:
                conn.close()
                return False, "Initial deposit cannot be negative"
            
            account_number = SBAccountModule.generate_account_number()
            today = datetime.now().date()
            
            # FIXED: min_balance set to 0
            c.execute("""
                INSERT INTO sb_accounts 
                (account_number, customer_id, balance, interest_rate, min_balance, opened_date, last_interest_date, nominee_id, created_by)
                VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?)
            """, (account_number, customer_id, initial_deposit, interest_rate, today, today, nominee_id, created_by))
            
            if initial_deposit > 0:
                txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
                c.execute("""
                    INSERT INTO sb_transactions 
                    (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by)
                    VALUES (?, ?, 'Deposit', ?, 0, ?, 'Initial Deposit', ?)
                """, (txn_id, account_number, initial_deposit, initial_deposit, created_by))
                
                voucher_id = JournalVoucherModule.create_auto_voucher(
                    'Receipt', today, f'Initial deposit for SB Account {account_number}', created_by,
                    [('CASH_IN_HAND', initial_deposit, 0), ('SB_ACCOUNTS', 0, initial_deposit)]
                )
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
            c.execute("SELECT balance, customer_id FROM sb_accounts WHERE account_number = ? AND status = 'Active'", (account_number,))
            account = c.fetchone()
            
            if not account:
                conn.close()
                return False, "Account not found or inactive"
            
            old_balance = account[0]
            new_balance = old_balance + amount
            
            c.execute("UPDATE sb_accounts SET balance = ? WHERE account_number = ?", (new_balance, account_number))
            
            txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
            c.execute("""
                INSERT INTO sb_transactions 
                (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by)
                VALUES (?, ?, 'Deposit', ?, ?, ?, ?, ?)
            """, (txn_id, account_number, amount, old_balance, new_balance, description, created_by))
            
            voucher_id = JournalVoucherModule.create_auto_voucher(
                'Receipt', datetime.now().date(), f'Deposit in {account_number}: {description}', created_by,
                [('CASH_IN_HAND', amount, 0), ('SB_ACCOUNTS', 0, amount)]
            )
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
            c.execute("SELECT balance, min_balance FROM sb_accounts WHERE account_number = ? AND status = 'Active'", (account_number,))
            account = c.fetchone()
            
            if not account:
                conn.close()
                return False, "Account not found or inactive"
            
            # FIXED: Check if withdrawal would make balance negative (min_balance is 0)
            if account[0] - amount < account[1]:
                conn.close()
                return False, f"Insufficient balance. Available: ₹{account[0]:,.2f}"
            
            old_balance = account[0]
            new_balance = old_balance - amount
            
            c.execute("UPDATE sb_accounts SET balance = ? WHERE account_number = ?", (new_balance, account_number))
            
            txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
            c.execute("""
                INSERT INTO sb_transactions 
                (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by)
                VALUES (?, ?, 'Withdrawal', ?, ?, ?, ?, ?)
            """, (txn_id, account_number, amount, old_balance, new_balance, description, created_by))
            
            voucher_id = JournalVoucherModule.create_auto_voucher(
                'Payment', datetime.now().date(), f'Withdrawal from {account_number}: {description}', created_by,
                [('SB_ACCOUNTS', amount, 0), ('CASH_IN_HAND', 0, amount)]
            )
            c.execute("UPDATE sb_transactions SET voucher_id = ? WHERE transaction_id = ?", (voucher_id, txn_id))
            
            conn.commit()
            conn.close()
            return True, f"Withdrew ₹{amount:,.2f}. New Balance: ₹{new_balance:,.2f}"
            
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)

# ============================================
# FD ACCOUNT MODULE (FIXED)
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
            # FIXED: Check SB account exists and is active for this customer
            c.execute("""
                SELECT balance FROM sb_accounts 
                WHERE account_number = ? AND customer_id = ? AND status = 'Active'
            """, (sb_account, customer_id))
            sb = c.fetchone()
            
            if not sb:
                conn.close()
                return False, "SB Account not found, inactive, or doesn't belong to this customer"
            
            if sb[0] < principal:
                conn.close()
                return False, f"Insufficient balance in SB account. Available: ₹{sb[0]:,.2f}"
            
            # Calculate maturity amount
            rate_per_month = interest_rate / 1200
            maturity_amount = round(principal * (1 + rate_per_month * tenure_months), 2)
            
            fd_id = FDAccountModule.generate_fd_id()
            start_date = datetime.now().date()
            maturity_date = start_date + relativedelta(months=tenure_months)
            
            # Create FD account
            c.execute("""
                INSERT INTO fd_accounts (fd_id, customer_id, sb_account, principal_amount, 
                    interest_rate, tenure_months, start_date, maturity_date, maturity_amount, nominee_id, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (fd_id, customer_id, sb_account, principal, interest_rate, tenure_months,
                  start_date, maturity_date, maturity_amount, nominee_id, created_by))
            
            # Deduct from SB account
            old_balance = sb[0]
            new_balance = old_balance - principal
            c.execute("UPDATE sb_accounts SET balance = ? WHERE account_number = ?", (new_balance, sb_account))
            
            # Record SB transaction
            txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
            c.execute("""
                INSERT INTO sb_transactions 
                (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by)
                VALUES (?, ?, 'FD_Transfer', ?, ?, ?, ?, ?)
            """, (txn_id, sb_account, principal, old_balance, new_balance,
                  f'FD Creation - {fd_id}', created_by))
            
            # Record FD transaction
            fd_txn_id = f"FDT{uuid.uuid4().hex[:8].upper()}"
            c.execute("""
                INSERT INTO fd_transactions (transaction_id, fd_id, transaction_type, amount, description, created_by)
                VALUES (?, ?, 'FD_Creation', ?, ?, ?)
            """, (fd_txn_id, fd_id, principal, f'FD Account Opened - {tenure_months} months @ {interest_rate}%', created_by))
            
            # Accounting entries
            voucher_id = JournalVoucherModule.create_auto_voucher(
                'FD', start_date, f'FD Creation {fd_id} from SB {sb_account}', created_by,
                [('FD_INVESTMENTS', principal, 0), ('SB_ACCOUNTS', 0, principal)]
            )
            
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
    def get_fd_list(customer_id=None):
        conn = db.get_connection()
        c = conn.cursor()
        
        if customer_id:
            c.execute("""
                SELECT fd.*, c.first_name, c.last_name 
                FROM fd_accounts fd
                JOIN customers c ON fd.customer_id = c.customer_id
                WHERE fd.customer_id = ?
                ORDER BY fd.start_date DESC
            """, (customer_id,))
        else:
            c.execute("""
                SELECT fd.*, c.first_name, c.last_name 
                FROM fd_accounts fd
                JOIN customers c ON fd.customer_id = c.customer_id
                ORDER BY fd.start_date DESC
            """)
        
        fds = c.fetchall()
        conn.close()
        return fds

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
            total_debit = sum(entry[1] for entry in entries)
            total_credit = sum(entry[2] for entry in entries)
            
            if abs(total_debit - total_credit) > 0.01:
                conn.close()
                return False, f"Debit (₹{total_debit:,.2f}) and Credit (₹{total_credit:,.2f}) must be equal"
            
            if total_debit == 0:
                conn.close()
                return False, "Amount cannot be zero"
            
            voucher_id = JournalVoucherModule.generate_voucher_id(voucher_type)
            
            c.execute("""
                INSERT INTO journal_vouchers 
                (voucher_id, voucher_type, voucher_date, narration, total_amount, status, created_by)
                VALUES (?, ?, ?, ?, ?, 'Approved', ?)
            """, (voucher_id, voucher_type, voucher_date, narration, total_debit, created_by))
            
            for entry in entries:
                account_head, debit, credit = entry
                c.execute("""
                    INSERT INTO journal_entries 
                    (voucher_id, account_head, debit_amount, credit_amount)
                    VALUES (?, ?, ?, ?)
                """, (voucher_id, account_head, debit, credit))
            
            conn.commit()
            conn.close()
            return True, voucher_id
            
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)
    
    @staticmethod
    def create_auto_voucher(voucher_type, voucher_date, narration, created_by, entries):
        success, result = JournalVoucherModule.create_voucher(
            voucher_type, voucher_date, narration, entries, created_by
        )
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
            
            c.execute("""
                INSERT INTO customers 
                (customer_id, first_name, last_name, date_of_birth, gender, email, phone, 
                 address, city, state, pincode, occupation, annual_income, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                customer_id, data['first_name'], data['last_name'], data['date_of_birth'],
                data.get('gender'), data.get('email'), data['phone'], data.get('address'),
                data.get('city'), data.get('state'), data.get('pincode'),
                data.get('occupation'), data.get('annual_income'), created_by
            ))
            
            if 'aadhaar_number' in data and data['aadhaar_number']:
                c.execute("INSERT INTO kyc_documents (customer_id, doc_type, doc_number) VALUES (?, 'Aadhaar', ?)",
                         (customer_id, data['aadhaar_number']))
            
            if 'pan_number' in data and data['pan_number']:
                c.execute("INSERT INTO kyc_documents (customer_id, doc_type, doc_number) VALUES (?, 'PAN', ?)",
                         (customer_id, data['pan_number']))
            
            if 'nominee_name' in data and data['nominee_name']:
                c.execute("""
                    INSERT INTO nominees (customer_id, nominee_name, relationship, date_of_birth, phone, percentage_share)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (customer_id, data['nominee_name'], data.get('nominee_relationship'),
                      data.get('nominee_dob'), data.get('nominee_phone'), data.get('nominee_percentage', 100)))
            
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
            c.execute("""
                UPDATE customers 
                SET kyc_status = 'Verified', kyc_verified_by = ?, kyc_verified_date = ?
                WHERE customer_id = ?
            """, (verified_by, datetime.now(), customer_id))
            
            c.execute("""
                UPDATE kyc_documents 
                SET verification_status = 'Verified', verified_by = ?
                WHERE customer_id = ?
            """, (verified_by, customer_id))
            
            conn.commit()
            conn.close()
            return True, "KYC Verified successfully"
            
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)

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
        st.markdown("""
            <div style='text-align: center; margin-bottom: 2rem;'>
                <h3 style='color: #a78bfa; font-size: 1.8rem;'>Secure Login</h3>
                <p style='color: #94a3b8;'>Enter your credentials to access the system</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("👤 Username", placeholder="Enter your username")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            submit = st.form_submit_button("🔐 Login", use_container_width=True)
            
            if submit:
                if username and password:
                    user = AuthModule.authenticate(username, password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        st.success(f"Welcome back, {user['full_name']}! 👋")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
                else:
                    st.error("⚠️ Please enter both username and password")
        
        st.markdown("---")
        st.markdown("""
            <div class="info-box">
                <strong>🔑 Demo Credentials:</strong><br>
                • Admin: <code>admin</code> / <code>admin123</code><br>
                • Manager: <code>manager</code> / <code>manager123</code><br>
                • User: <code>user1</code> / <code>user123</code>
            </div>
        """, unsafe_allow_html=True)

def sb_account_ui():
    st.markdown('<h2 class="sub-header">💰 Savings Bank Account</h2>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📂 Open Account", "💳 Deposit/Withdraw", "📋 Account List"])
    
    with tab1:
        st.markdown("### Open New SB Account")
        
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT customer_id, first_name, last_name FROM customers WHERE kyc_status = 'Verified'")
        customers = c.fetchall()
        conn.close()
        
        if customers:
            with st.form("open_sb_account"):
                customer_options = {f"{c[1]} {c[2]} ({c[0]})": c[0] for c in customers}
                selected_customer = st.selectbox("Select Customer *", list(customer_options.keys()))
                
                col1, col2 = st.columns(2)
                with col1:
                    initial_deposit = st.number_input("Initial Deposit", min_value=0.0, value=0.0, step=500.0)
                    interest_rate = st.number_input("Interest Rate (%)", min_value=0.0, value=4.0, step=0.25)
                with col2:
                    st.info("📌 Minimum Balance: ₹0 (Zero Balance Account)")
                    st.info(f"📈 Quarterly Interest @ {interest_rate}%")
                
                if st.form_submit_button("Open Account", use_container_width=True):
                    success, result = SBAccountModule.open_account(
                        customer_options[selected_customer], initial_deposit, interest_rate,
                        created_by=st.session_state.user['user_id']
                    )
                    if success:
                        st.success(f"✅ Account opened! Number: {result}")
                        st.balloons()
                    else:
                        st.error(result)
        else:
            st.warning("⚠️ No customers with verified KYC available")
    
    with tab2:
        st.markdown("### Deposit / Withdraw")
        
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT sa.account_number, c.first_name || ' ' || c.last_name as customer, sa.balance
            FROM sb_accounts sa
            JOIN customers c ON sa.customer_id = c.customer_id
            WHERE sa.status = 'Active'
        """)
        accounts = c.fetchall()
        conn.close()
        
        if accounts:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 💚 Deposit")
                with st.form("deposit_form"):
                    acc_options = {f"{acc[1]} - {acc[0]} (₹{acc[2]:,.2f})": acc for acc in accounts}
                    dep_account = st.selectbox("Account", list(acc_options.keys()), key="dep_acc")
                    dep_amount = st.number_input("Amount *", min_value=1.0, step=100.0, key="dep_amt")
                    dep_desc = st.text_input("Description", key="dep_desc")
                    
                    if st.form_submit_button("Deposit 💰"):
                        acc = acc_options[dep_account]
                        success, msg = SBAccountModule.deposit(
                            acc[0], dep_amount, dep_desc, st.session_state.user['user_id']
                        )
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
            
            with col2:
                st.markdown("#### 🔴 Withdraw")
                with st.form("withdraw_form"):
                    acc_options = {f"{acc[1]} - {acc[0]} (₹{acc[2]:,.2f})": acc for acc in accounts}
                    wit_account = st.selectbox("Account", list(acc_options.keys()), key="wit_acc")
                    acc = acc_options[wit_account]
                    max_withdraw = float(acc[2])
                    wit_amount = st.number_input("Amount *", min_value=0.0, max_value=max_withdraw, step=100.0, key="wit_amt")
                    wit_desc = st.text_input("Description", key="wit_desc")
                    
                    if st.form_submit_button("Withdraw 💸"):
                        success, msg = SBAccountModule.withdraw(
                            acc[0], wit_amount, wit_desc, st.session_state.user['user_id']
                        )
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
        else:
            st.info("No active SB accounts")
    
    with tab3:
        st.markdown("### SB Account List")
        
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT sa.account_number, c.first_name || ' ' || c.last_name as customer,
                   sa.balance, sa.interest_rate, sa.opened_date, sa.status, c.customer_id
            FROM sb_accounts sa
            JOIN customers c ON sa.customer_id = c.customer_id
            ORDER BY sa.opened_date DESC
        """)
        accounts = c.fetchall()
        conn.close()
        
        if accounts:
            accounts_data = []
            for acc in accounts:
                accounts_data.append({
                    'Account No': acc[0],
                    'Customer': acc[1],
                    'Customer ID': acc[6],
                    'Balance': f"₹{acc[2]:,.2f}",
                    'Interest Rate': f"{acc[3]}%",
                    'Opened': acc[4],
                    'Status': acc[5]
                })
            st.dataframe(pd.DataFrame(accounts_data), use_container_width=True, hide_index=True)
            
            total_balance = sum(acc[2] for acc in accounts)
            active_accounts = sum(1 for acc in accounts if acc[5] == 'Active')
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Accounts", len(accounts))
            with col2:
                st.metric("Active Accounts", active_accounts)
            with col3:
                st.metric("Total Deposits", f"₹{total_balance:,.2f}")
        else:
            st.info("No SB accounts")

def fd_account_ui():
    st.markdown('<h2 class="sub-header">🏦 Fixed Deposit Management</h2>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📂 Open FD", "📋 FD List"])
    
    with tab1:
        st.markdown("### Open New Fixed Deposit")
        
        # FIXED: Get SB accounts with customer details
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT sa.account_number, sa.customer_id, c.first_name, c.last_name, sa.balance
            FROM sb_accounts sa
            JOIN customers c ON sa.customer_id = c.customer_id
            WHERE sa.status = 'Active'
        """)
        accounts = c.fetchall()
        conn.close()
        
        if accounts:
            with st.form("open_fd_form"):
                # Show accounts with customer name, account number, and balance
                acc_options = {}
                for acc in accounts:
                    label = f"{acc[2]} {acc[3]} - {acc[0]} (Balance: ₹{acc[4]:,.2f})"
                    acc_options[label] = acc
                
                selected_label = st.selectbox("Select SB Account *", list(acc_options.keys()))
                selected_acc = acc_options[selected_label]
                
                account_number = selected_acc[0]
                customer_id = selected_acc[1]
                balance = selected_acc[4]
                
                st.info(f"👤 Customer ID: {customer_id} | Available Balance: ₹{balance:,.2f}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    principal = st.number_input("Principal Amount *", 
                                               min_value=100.0, 
                                               max_value=float(balance),
                                               step=1000.0,
                                               value=min(1000.0, float(balance)))
                with col2:
                    interest_rate = st.number_input("Interest Rate (%)", min_value=1.0, value=7.0, step=0.5)
                with col3:
                    tenure = st.selectbox("Tenure (Months)", [3, 6, 12, 24, 36, 48, 60])
                
                if principal > 0:
                    maturity = principal * (1 + (interest_rate/1200) * tenure)
                    st.info(f"📊 Maturity Amount after {tenure} months: ₹{maturity:,.2f}")
                
                if st.form_submit_button("Open FD", use_container_width=True):
                    # FIXED: Pass customer_id and account_number correctly
                    success, result = FDAccountModule.open_fd(
                        customer_id=customer_id,
                        sb_account=account_number,
                        principal=principal,
                        interest_rate=interest_rate,
                        tenure_months=tenure,
                        created_by=st.session_state.user['user_id']
                    )
                    if success:
                        st.success(f"✅ FD created successfully! ID: {result}")
                        st.balloons()
                    else:
                        st.error(result)
        else:
            st.warning("No active SB accounts available")
    
    with tab2:
        st.markdown("### All Fixed Deposits")
        
        fds = FDAccountModule.get_fd_list()
        
        if fds:
            fd_data = []
            for fd in fds:
                days_left = (datetime.strptime(fd[6], '%Y-%m-%d').date() - datetime.now().date()).days if fd[8] == 'Active' else 0
                fd_data.append({
                    'FD ID': fd[0],
                    'Customer': f"{fd[10]} {fd[11]}",
                    'SB Account': fd[2],
                    'Principal': f"₹{fd[3]:,.2f}",
                    'Rate': f"{fd[4]}%",
                    'Tenure': f"{fd[5]} months",
                    'Start Date': fd[5],
                    'Maturity Date': fd[6],
                    'Maturity Amount': f"₹{fd[7]:,.2f}",
                    'Days Left': f"{days_left} days" if fd[8] == 'Active' else '-',
                    'Status': fd[8]
                })
            st.dataframe(pd.DataFrame(fd_data), use_container_width=True, hide_index=True)
            
            # Summary
            active_fds = sum(1 for fd in fds if fd[8] == 'Active')
            total_fd_amount = sum(fd[3] for fd in fds if fd[8] == 'Active')
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Active FDs", active_fds)
            with col2:
                st.metric("Total FD Amount", f"₹{total_fd_amount:,.2f}")
        else:
            st.info("No FDs created yet")

def customer_ui():
    st.markdown('<h2 class="sub-header">👤 Customer Registration & KYC</h2>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📝 Register Customer", "📋 Customer List"])
    
    with tab1:
        with st.form("customer_form"):
            st.markdown("### Personal Information")
            col1, col2, col3 = st.columns(3)
            with col1:
                first_name = st.text_input("First Name *")
                date_of_birth = st.date_input("Date of Birth *", 
                                             min_value=datetime.now()-timedelta(days=365*100),
                                             max_value=datetime.now()-timedelta(days=365*18))
                email = st.text_input("Email")
            with col2:
                last_name = st.text_input("Last Name *")
                gender = st.selectbox("Gender", ['Male', 'Female', 'Other'])
                phone = st.text_input("Phone *")
            with col3:
                address = st.text_area("Address")
                city = st.text_input("City")
                state = st.text_input("State")
                pincode = st.text_input("Pincode")
            
            st.markdown("---")
            st.markdown("### KYC Documents")
            col1, col2 = st.columns(2)
            with col1:
                aadhaar = st.text_input("Aadhaar Number")
            with col2:
                pan = st.text_input("PAN Number")
            
            if st.form_submit_button("Register Customer", use_container_width=True):
                if not first_name or not last_name or not phone:
                    st.error("⚠️ First name, last name, and phone are required!")
                else:
                    data = {
                        'first_name': first_name, 'last_name': last_name,
                        'date_of_birth': date_of_birth, 'gender': gender,
                        'email': email, 'phone': phone, 'address': address,
                        'city': city, 'state': state, 'pincode': pincode,
                        'aadhaar_number': aadhaar, 'pan_number': pan
                    }
                    
                    success, result = CustomerModule.register_customer(
                        data, st.session_state.user['user_id']
                    )
                    if success:
                        st.success(f"✅ Customer registered! ID: {result}")
                    else:
                        st.error(result)
    
    with tab2:
        st.markdown("### Customer List")
        
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT customer_id, first_name, last_name, phone, email, kyc_status, created_at
            FROM customers ORDER BY created_at DESC
        """)
        customers = c.fetchall()
        conn.close()
        
        if customers:
            for row in customers:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"**{row[1]} {row[2]}**")
                    st.caption(f"🆔 {row[0]} | 📞 {row[3]} | 📧 {row[4]}")
                with col2:
                    if row[5] == 'Verified':
                        st.markdown('<span class="badge badge-success">✅ KYC Verified</span>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span class="badge badge-warning">⏳ KYC: {row[5]}</span>', unsafe_allow_html=True)
                with col3:
                    if row[5] != 'Verified' and st.session_state.user['role'] in ['Admin', 'Manager']:
                        if st.button("✅ Verify", key=f"verify_{row[0]}"):
                            CustomerModule.verify_kyc(row[0], st.session_state.user['user_id'])
                            st.rerun()
                st.divider()
        else:
            st.info("No customers registered")

# ============================================
# MAIN APPLICATION
# ============================================
def main():
    init_session_state()
    
    try:
        db.initialize_database()
    except Exception as e:
        st.error(f"Database initialization error: {e}")
        if st.button("🔄 Reset Database"):
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
                <h3 style='color: #a78bfa; margin: 0;'>🏦 Banking System</h3>
                <p style='color: #94a3b8; margin: 0.5rem 0;'>{st.session_state.user['full_name']}</p>
                <span class="badge badge-info">{st.session_state.user['role']}</span>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        
        tabs = {
            'SB Accounts': '💰 SB Accounts',
            'FD Accounts': '🏦 FD Accounts',
            'Customers': '👤 Customers',
        }
        
        selected_tab = st.radio(
            "Navigation",
            list(tabs.keys()),
            format_func=lambda x: tabs[x],
            label_visibility="collapsed"
        )
        
        st.session_state.current_tab = selected_tab
        
        st.markdown("---")
        
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM sb_accounts WHERE status='Active'")
        active_accounts = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(balance), 0) FROM sb_accounts WHERE status='Active'")
        total_deposits = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM customers WHERE kyc_status='Verified'")
        verified_customers = c.fetchone()[0]
        conn.close()
        
        st.markdown("### Quick Stats")
        st.metric("Active Accounts", active_accounts)
        st.metric("Total Deposits", f"₹{total_deposits:,.2f}")
        st.metric("Verified Customers", verified_customers)
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()
    
    if st.session_state.current_tab == 'SB Accounts':
        sb_account_ui()
    elif st.session_state.current_tab == 'FD Accounts':
        fd_account_ui()
    elif st.session_state.current_tab == 'Customers':
        customer_ui()

if __name__ == "__main__":
    main()
