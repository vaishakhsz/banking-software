import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import uuid
import json
import os
import base64
from PIL import Image
import io

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
    /* Global Styles */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main container */
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0d1128 100%);
    }
    
    /* Header styles */
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
    
    /* Card styles */
    .card {
        background: linear-gradient(135deg, rgba(26, 31, 58, 0.9), rgba(45, 43, 85, 0.9));
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
    }
    
    .card:hover {
        border: 1px solid rgba(102, 126, 234, 0.5);
        box-shadow: 0 12px 40px rgba(102, 126, 234, 0.15);
        transform: translateY(-2px);
        transition: all 0.3s ease;
    }
    
    /* Success/Error/Info boxes */
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
    
    /* Form styles */
    div[data-testid="stForm"] {
        background: linear-gradient(135deg, rgba(26, 31, 58, 0.95), rgba(45, 43, 85, 0.95));
        border: 1px solid rgba(102, 126, 234, 0.3);
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 15px 50px rgba(0, 0, 0, 0.4);
    }
    
    /* Input fields */
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
    
    /* Labels */
    .stTextInput > label,
    .stNumberInput > label,
    .stSelectbox > label,
    .stTextArea > label {
        color: #c4b5fd !important;
        font-weight: 500 !important;
    }
    
    /* Buttons */
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
    
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0e27 0%, #1a1f3a 100%) !important;
        border-right: 1px solid rgba(102, 126, 234, 0.2) !important;
    }
    
    section[data-testid="stSidebar"] .stMarkdown {
        color: #e2e8f0 !important;
    }
    
    /* Radio buttons in sidebar */
    .stRadio > div {
        background: transparent !important;
    }
    
    .stRadio > div > div > label {
        color: #c4b5fd !important;
        font-weight: 500 !important;
    }
    
    .stRadio > div > div > label:hover {
        background: rgba(102, 126, 234, 0.1) !important;
        border-radius: 10px !important;
    }
    
    /* Tabs */
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
        transition: all 0.3s ease !important;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(102, 126, 234, 0.1) !important;
        color: #c4b5fd !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2)) !important;
        color: #a78bfa !important;
        border: 1px solid rgba(102, 126, 234, 0.3) !important;
    }
    
    /* Dataframe */
    .stDataFrame {
        background: rgba(15, 18, 35, 0.8) !important;
        border-radius: 15px !important;
        border: 1px solid rgba(102, 126, 234, 0.2) !important;
    }
    
    .stDataFrame [data-testid="stTable"] {
        background: transparent !important;
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
    
    /* Metrics */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(26, 31, 58, 0.9), rgba(45, 43, 85, 0.9));
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 15px;
        padding: 1.5rem !important;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
    }
    
    [data-testid="stMetric"]:hover {
        border-color: rgba(102, 126, 234, 0.5);
        box-shadow: 0 12px 35px rgba(102, 126, 234, 0.2);
    }
    
    [data-testid="stMetric"] label {
        color: #94a3b8 !important;
        font-weight: 500 !important;
    }
    
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #a78bfa !important;
        font-weight: 700 !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, rgba(26, 31, 58, 0.8), rgba(45, 43, 85, 0.8)) !important;
        border: 1px solid rgba(102, 126, 234, 0.2) !important;
        border-radius: 12px !important;
        color: #c4b5fd !important;
        font-weight: 600 !important;
    }
    
    .streamlit-expanderHeader:hover {
        border-color: rgba(102, 126, 234, 0.5) !important;
    }
    
    /* Dividers */
    hr {
        border-color: rgba(102, 126, 234, 0.2) !important;
    }
    
    /* Success/Error messages */
    .stAlert {
        background: rgba(15, 18, 35, 0.9) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(102, 126, 234, 0.2) !important;
    }
    
    /* Tooltips */
    .stTooltip {
        background: rgba(15, 18, 35, 0.95) !important;
        border: 1px solid rgba(102, 126, 234, 0.3) !important;
        color: #e2e8f0 !important;
    }
    
    /* Scrollbar */
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
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #764ba2, #667eea);
    }
    
    /* Balloons animation override */
    @keyframes float-up {
        0% { transform: translateY(0) rotate(0deg); opacity: 1; }
        100% { transform: translateY(-100vh) rotate(720deg); opacity: 0; }
    }
    
    /* Logo-like gradient text */
    .gradient-text {
        background: linear-gradient(120deg, #667eea, #764ba2, #f093fb);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
    }
    
    /* Card grid for dashboard */
    .dashboard-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1.5rem;
        margin: 1rem 0;
    }
    
    /* Badge styles */
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
    
    .badge-danger {
        background: rgba(239, 68, 68, 0.2);
        color: #fca5a5;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    .badge-info {
        background: rgba(59, 130, 246, 0.2);
        color: #93c5fd;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    </style>
""", unsafe_allow_html=True)

# ============================================
# MODULE 1: DATABASE LAYER
# ============================================
class DatabaseLayer:
    """Central database management for the entire banking system"""
    
    def __init__(self):
        self.db_path = 'complete_banking.db'
        self.conn = None
        self.cursor = None
        
    def initialize_database(self):
        """Initialize all database tables with proper schema"""
        if os.path.exists(self.db_path):
            try:
                temp_conn = sqlite3.connect(self.db_path)
                temp_c = temp_conn.cursor()
                temp_c.execute("SELECT password_hash FROM users LIMIT 1")
                temp_conn.close()
            except:
                os.remove(self.db_path)
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        self.cursor.execute("PRAGMA journal_mode=WAL")
        self.cursor.execute("PRAGMA foreign_keys=ON")
        
        self._create_user_tables()
        self._create_customer_tables()
        self._create_account_tables()
        self._create_voucher_tables()
        self._create_transaction_tables()
        self._create_loan_tables()
        
        self._insert_default_users()
        self._insert_chart_of_accounts()
        
        self.conn.commit()
        return self.conn
    
    def _create_user_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE,
                role TEXT NOT NULL CHECK(role IN ('Admin', 'Manager', 'User')),
                is_active INTEGER DEFAULT 1,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER REFERENCES users(user_id)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id),
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                logout_time TIMESTAMP,
                ip_address TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
    
    def _create_customer_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                date_of_birth DATE NOT NULL,
                gender TEXT CHECK(gender IN ('Male', 'Female', 'Other')),
                email TEXT UNIQUE,
                phone TEXT NOT NULL,
                address TEXT,
                city TEXT,
                state TEXT,
                pincode TEXT,
                occupation TEXT,
                annual_income REAL,
                kyc_status TEXT DEFAULT 'Pending' CHECK(kyc_status IN ('Pending', 'Verified', 'Rejected')),
                kyc_verified_by INTEGER REFERENCES users(user_id),
                kyc_verified_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER REFERENCES users(user_id),
                updated_at TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS kyc_documents (
                doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT REFERENCES customers(customer_id),
                doc_type TEXT NOT NULL CHECK(doc_type IN ('Aadhaar', 'PAN', 'Passport', 'Driving_License', 'Voter_ID', 'Photo')),
                doc_number TEXT,
                doc_file BLOB,
                doc_filename TEXT,
                verification_status TEXT DEFAULT 'Pending',
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_by INTEGER REFERENCES users(user_id)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS nominees (
                nominee_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT REFERENCES customers(customer_id),
                nominee_name TEXT NOT NULL,
                relationship TEXT NOT NULL,
                date_of_birth DATE,
                phone TEXT,
                address TEXT,
                percentage_share REAL DEFAULT 100.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_account_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sb_accounts (
                account_number TEXT PRIMARY KEY,
                customer_id TEXT REFERENCES customers(customer_id),
                account_type TEXT DEFAULT 'Savings',
                balance REAL DEFAULT 0.00,
                interest_rate REAL DEFAULT 4.00,
                min_balance REAL DEFAULT 500.00,
                opened_date DATE NOT NULL,
                last_interest_date DATE,
                status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Dormant', 'Closed', 'Frozen')),
                nominee_id INTEGER REFERENCES nominees(nominee_id),
                created_by INTEGER REFERENCES users(user_id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS fd_accounts (
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS rd_accounts (
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
                status TEXT DEFAULT 'Active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_voucher_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_vouchers (
                voucher_id TEXT PRIMARY KEY,
                voucher_type TEXT NOT NULL CHECK(voucher_type IN ('Payment', 'Receipt', 'Journal', 'Contra', 'Interest')),
                voucher_date DATE NOT NULL,
                narration TEXT NOT NULL,
                total_amount REAL NOT NULL DEFAULT 0.00,
                status TEXT DEFAULT 'Draft' CHECK(status IN ('Draft', 'Pending', 'Approved', 'Rejected')),
                is_posted INTEGER DEFAULT 0,
                created_by INTEGER REFERENCES users(user_id),
                approved_by INTEGER REFERENCES users(user_id),
                verified_by INTEGER REFERENCES users(user_id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                verification_status TEXT DEFAULT 'Pending' CHECK(verification_status IN ('Pending', 'Verified', 'Rejected'))
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_entries (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                voucher_id TEXT REFERENCES journal_vouchers(voucher_id),
                account_head TEXT REFERENCES chart_of_accounts(account_head),
                debit_amount REAL DEFAULT 0.00,
                credit_amount REAL DEFAULT 0.00,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chart_of_accounts (
                account_head TEXT PRIMARY KEY,
                account_name TEXT NOT NULL,
                account_type TEXT NOT NULL CHECK(account_type IN ('Asset', 'Liability', 'Equity', 'Income', 'Expense')),
                category TEXT NOT NULL,
                sub_category TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_transaction_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sb_transactions (
                transaction_id TEXT PRIMARY KEY,
                account_number TEXT REFERENCES sb_accounts(account_number),
                transaction_type TEXT NOT NULL CHECK(transaction_type IN ('Deposit', 'Withdrawal', 'Interest_Credit', 'Transfer_In', 'Transfer_Out', 'FD_Transfer', 'RD_Transfer')),
                amount REAL NOT NULL,
                balance_before REAL,
                balance_after REAL,
                description TEXT,
                voucher_id TEXT REFERENCES journal_vouchers(voucher_id),
                created_by INTEGER REFERENCES users(user_id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS interest_calculations (
                calc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_number TEXT REFERENCES sb_accounts(account_number),
                interest_period_start DATE,
                interest_period_end DATE,
                minimum_balance REAL,
                interest_rate REAL,
                interest_amount REAL,
                is_credited INTEGER DEFAULT 0,
                voucher_id TEXT REFERENCES journal_vouchers(voucher_id),
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_loan_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS loans (
                loan_id TEXT PRIMARY KEY,
                customer_id TEXT REFERENCES customers(customer_id),
                sb_account TEXT REFERENCES sb_accounts(account_number),
                loan_type TEXT CHECK(loan_type IN ('Personal', 'Home', 'Car', 'Business', 'Gold')),
                principal_amount REAL NOT NULL,
                interest_rate REAL NOT NULL,
                tenure_months INTEGER NOT NULL,
                emi_amount REAL,
                start_date DATE NOT NULL,
                end_date DATE,
                outstanding_amount REAL,
                status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Closed', 'NPA')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS loan_repayments (
                payment_id TEXT PRIMARY KEY,
                loan_id TEXT REFERENCES loans(loan_id),
                payment_date DATE NOT NULL,
                amount REAL NOT NULL,
                principal_component REAL,
                interest_component REAL,
                outstanding_after REAL,
                voucher_id TEXT REFERENCES journal_vouchers(voucher_id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_trail (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(user_id),
                module TEXT NOT NULL,
                action TEXT NOT NULL,
                record_type TEXT,
                record_id TEXT,
                old_data TEXT,
                new_data TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _insert_default_users(self):
        self.cursor.execute("SELECT COUNT(*) FROM users")
        if self.cursor.fetchone()[0] == 0:
            users = [
                ('admin', 'admin123', 'System Administrator', 'admin@bank.com', 'Admin'),
                ('manager', 'manager123', 'Branch Manager', 'manager@bank.com', 'Manager'),
                ('user1', 'user123', 'Bank User', 'user@bank.com', 'User'),
            ]
            for username, password, full_name, email, role in users:
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                self.cursor.execute(
                    "INSERT INTO users (username, password_hash, full_name, email, role) VALUES (?, ?, ?, ?, ?)",
                    (username, password_hash, full_name, email, role)
                )
    
    def _insert_chart_of_accounts(self):
        self.cursor.execute("SELECT COUNT(*) FROM chart_of_accounts")
        if self.cursor.fetchone()[0] == 0:
            accounts = [
                # Assets
                ('CASH_IN_HAND', 'Cash in Hand', 'Asset', 'Current Asset', 'Cash'),
                ('BANK_ACCOUNTS', 'Bank Accounts', 'Asset', 'Current Asset', 'Bank'),
                ('SB_DEPOSITS', 'SB Deposits', 'Asset', 'Current Asset', 'Deposits'),
                ('LOANS_RECEIVABLE', 'Loans Receivable', 'Asset', 'Current Asset', 'Loans'),
                ('FD_INVESTMENTS', 'FD Investments', 'Asset', 'Investment', 'FD'),
                ('RD_INVESTMENTS', 'RD Investments', 'Asset', 'Investment', 'RD'),
                ('FURNITURE', 'Furniture & Fixtures', 'Asset', 'Fixed Asset', 'Office'),
                ('COMPUTERS', 'Computer Equipment', 'Asset', 'Fixed Asset', 'IT'),
                
                # Liabilities
                ('SB_ACCOUNTS', 'Savings Bank Accounts', 'Liability', 'Current Liability', 'Deposits'),
                ('FD_ACCOUNTS', 'Fixed Deposit Accounts', 'Liability', 'Current Liability', 'Deposits'),
                ('RD_ACCOUNTS', 'Recurring Deposit Accounts', 'Liability', 'Current Liability', 'Deposits'),
                ('INTEREST_PAYABLE', 'Interest Payable', 'Liability', 'Current Liability', 'Interest'),
                ('LOANS_PAYABLE', 'Loans Payable', 'Liability', 'Current Liability', 'Borrowings'),
                
                # Equity
                ('SHARE_CAPITAL', 'Share Capital', 'Equity', 'Share Capital', 'Capital'),
                ('RESERVES', 'Reserves & Surplus', 'Equity', 'Reserves', 'Reserves'),
                
                # Income
                ('INTEREST_ON_LOANS', 'Interest on Loans', 'Income', 'Operating Income', 'Interest'),
                ('FD_INTEREST', 'FD Interest Income', 'Income', 'Operating Income', 'Interest'),
                ('COMMISSION', 'Commission Income', 'Income', 'Operating Income', 'Fees'),
                ('PROCESSING_FEES', 'Processing Fees', 'Income', 'Operating Income', 'Fees'),
                ('OTHER_INCOME', 'Other Income', 'Income', 'Other Income', 'Misc'),
                
                # Expenses
                ('INTEREST_ON_SB', 'Interest on SB Accounts', 'Expense', 'Operating Expense', 'Interest'),
                ('INTEREST_ON_FD', 'Interest on FD Accounts', 'Expense', 'Operating Expense', 'Interest'),
                ('INTEREST_ON_RD', 'Interest on RD Accounts', 'Expense', 'Operating Expense', 'Interest'),
                ('SALARY', 'Salary Expense', 'Expense', 'Administrative Expense', 'Staff'),
                ('RENT', 'Rent Expense', 'Expense', 'Administrative Expense', 'Office'),
                ('UTILITIES', 'Utilities Expense', 'Expense', 'Administrative Expense', 'Office'),
                ('STATIONERY', 'Stationery & Printing', 'Expense', 'Administrative Expense', 'Office'),
                ('DEPRECIATION', 'Depreciation', 'Expense', 'Administrative Expense', 'Fixed Assets'),
            ]
            
            for account in accounts:
                self.cursor.execute(
                    "INSERT OR IGNORE INTO chart_of_accounts (account_head, account_name, account_type, category, sub_category) VALUES (?, ?, ?, ?, ?)",
                    account
                )
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def add_audit_entry(self, user_id, module, action, record_type, record_id, old_data=None, new_data=None):
        try:
            conn = self.get_connection()
            c = conn.cursor()
            c.execute("""
                INSERT INTO audit_trail (user_id, module, action, record_type, record_id, old_data, new_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, module, action, record_type, record_id,
                  json.dumps(old_data) if old_data else None,
                  json.dumps(new_data) if new_data else None))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Audit error: {e}")

# Initialize database
db = DatabaseLayer()

# ============================================
# MODULE 2: AUTHENTICATION & USER MANAGEMENT
# ============================================
class AuthModule:
    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def authenticate(username, password):
        conn = db.get_connection()
        c = conn.cursor()
        password_hash = AuthModule.hash_password(password)
        c.execute("""
            SELECT user_id, username, full_name, role, email 
            FROM users 
            WHERE username = ? AND password_hash = ? AND is_active = 1
        """, (username, password_hash))
        user = c.fetchone()
        
        if user:
            c.execute("UPDATE users SET last_login = ? WHERE user_id = ?", 
                     (datetime.now(), user[0]))
            conn.commit()
            
            session_id = str(uuid.uuid4())
            c.execute("INSERT INTO user_sessions (session_id, user_id) VALUES (?, ?)",
                     (session_id, user[0]))
            conn.commit()
            
            db.add_audit_entry(user[0], 'Authentication', 'LOGIN', 'users', str(user[0]))
            
            result = {
                'user_id': user[0],
                'username': user[1],
                'full_name': user[2],
                'role': user[3],
                'email': user[4],
                'session_id': session_id
            }
            conn.close()
            return result
        
        conn.close()
        return None
    
    @staticmethod
    def logout(user_id, session_id):
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("UPDATE user_sessions SET logout_time = ?, is_active = 0 WHERE session_id = ? AND user_id = ?",
                 (datetime.now(), session_id, user_id))
        conn.commit()
        db.add_audit_entry(user_id, 'Authentication', 'LOGOUT', 'users', str(user_id))
        conn.close()

# ============================================
# MODULE 3: SAVINGS BANK ACCOUNT MODULE
# ============================================
class SBAccountModule:
    @staticmethod
    def generate_account_number():
        return f"SB{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
    
    @staticmethod
    def open_account(customer_id, initial_deposit, interest_rate=4.0, nominee_id=None, created_by=None):
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
            
            if initial_deposit < 500:
                conn.close()
                return False, "Minimum initial deposit is ₹500"
            
            account_number = SBAccountModule.generate_account_number()
            today = datetime.now().date()
            
            c.execute("""
                INSERT INTO sb_accounts 
                (account_number, customer_id, balance, interest_rate, min_balance, opened_date, last_interest_date, nominee_id, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (account_number, customer_id, initial_deposit, interest_rate, 500, today, today, nominee_id, created_by))
            
            txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
            c.execute("""
                INSERT INTO sb_transactions 
                (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (txn_id, account_number, 'Deposit', initial_deposit, 0, initial_deposit, 'Initial Deposit - Account Opening', created_by))
            
            voucher_id = JournalVoucherModule.create_auto_voucher(
                'Receipt', today, f'Initial deposit for SB Account {account_number}', created_by,
                [('CASH_IN_HAND', initial_deposit, 0), ('SB_ACCOUNTS', 0, initial_deposit)]
            )
            
            c.execute("UPDATE sb_transactions SET voucher_id = ? WHERE transaction_id = ?", (voucher_id, txn_id))
            
            conn.commit()
            db.add_audit_entry(created_by, 'SB Account', 'CREATE', 'sb_accounts', account_number,
                             new_data={'customer_id': customer_id, 'balance': initial_deposit})
            
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (txn_id, account_number, 'Deposit', amount, old_balance, new_balance, description, created_by))
            
            voucher_id = JournalVoucherModule.create_auto_voucher(
                'Receipt', datetime.now().date(), f'Deposit in {account_number}: {description}', created_by,
                [('CASH_IN_HAND', amount, 0), ('SB_ACCOUNTS', 0, amount)]
            )
            
            c.execute("UPDATE sb_transactions SET voucher_id = ? WHERE transaction_id = ?", (voucher_id, txn_id))
            
            conn.commit()
            db.add_audit_entry(created_by, 'SB Account', 'DEPOSIT', 'sb_transactions', txn_id,
                             new_data={'amount': amount, 'account': account_number})
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
            
            if account[0] - amount < account[1]:
                conn.close()
                return False, f"Insufficient balance. Minimum balance of ₹{account[1]:,.2f} required"
            
            old_balance = account[0]
            new_balance = old_balance - amount
            
            c.execute("UPDATE sb_accounts SET balance = ? WHERE account_number = ?", (new_balance, account_number))
            
            txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
            c.execute("""
                INSERT INTO sb_transactions 
                (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (txn_id, account_number, 'Withdrawal', amount, old_balance, new_balance, description, created_by))
            
            voucher_id = JournalVoucherModule.create_auto_voucher(
                'Payment', datetime.now().date(), f'Withdrawal from {account_number}: {description}', created_by,
                [('SB_ACCOUNTS', amount, 0), ('CASH_IN_HAND', 0, amount)]
            )
            
            c.execute("UPDATE sb_transactions SET voucher_id = ? WHERE transaction_id = ?", (voucher_id, txn_id))
            
            conn.commit()
            db.add_audit_entry(created_by, 'SB Account', 'WITHDRAW', 'sb_transactions', txn_id,
                             new_data={'amount': amount, 'account': account_number})
            conn.close()
            return True, f"Withdrew ₹{amount:,.2f}. New Balance: ₹{new_balance:,.2f}"
            
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)
    
    @staticmethod
    def calculate_quarterly_interest(account_number=None, created_by=None):
        conn = db.get_connection()
        c = conn.cursor()
        
        try:
            today = datetime.now().date()
            quarter_start = today - relativedelta(months=3)
            
            if account_number:
                c.execute("""
                    SELECT account_number, balance, interest_rate, last_interest_date 
                    FROM sb_accounts 
                    WHERE account_number = ? AND status = 'Active'
                """, (account_number,))
            else:
                c.execute("""
                    SELECT account_number, balance, interest_rate, last_interest_date 
                    FROM sb_accounts 
                    WHERE status = 'Active' AND last_interest_date <= ?
                """, (today - relativedelta(months=3),))
            
            accounts = c.fetchall()
            results = []
            
            for account in accounts:
                acc_num, balance, rate, last_int_date = account
                
                c.execute("""
                    SELECT MIN(balance_after) FROM sb_transactions 
                    WHERE account_number = ? AND created_at >= ? AND created_at <= ?
                """, (acc_num, quarter_start, today))
                
                min_balance_result = c.fetchone()
                min_balance = min_balance_result[0] if min_balance_result and min_balance_result[0] else balance
                
                quarterly_rate = rate / 400
                interest = round(min_balance * quarterly_rate, 2)
                
                if interest > 0:
                    new_balance = balance + interest
                    c.execute("UPDATE sb_accounts SET balance = ?, last_interest_date = ? WHERE account_number = ?",
                             (new_balance, today, acc_num))
                    
                    txn_id = f"INT{uuid.uuid4().hex[:8].upper()}"
                    c.execute("""
                        INSERT INTO sb_transactions 
                        (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (txn_id, acc_num, 'Interest_Credit', interest, balance, new_balance, f'Quarterly Interest Q{((today.month-1)//3)+1} {today.year}', created_by))
                    
                    voucher_id = JournalVoucherModule.create_auto_voucher(
                        'Interest', today, f'Quarterly interest credited to {acc_num}', created_by,
                        [('INTEREST_ON_SB', interest, 0), ('SB_ACCOUNTS', 0, interest)]
                    )
                    
                    c.execute("UPDATE sb_transactions SET voucher_id = ? WHERE transaction_id = ?", (voucher_id, txn_id))
                    
                    c.execute("""
                        INSERT INTO interest_calculations 
                        (account_number, interest_period_start, interest_period_end, minimum_balance, interest_rate, interest_amount, is_credited, voucher_id)
                        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                    """, (acc_num, quarter_start, today, min_balance, rate, interest, voucher_id))
                    
                    results.append({
                        'account': acc_num,
                        'min_balance': min_balance,
                        'interest': interest,
                        'new_balance': new_balance
                    })
            
            conn.commit()
            conn.close()
            return True, results
            
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)
    
    @staticmethod
    def get_account_details(account_number):
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT sa.*, c.first_name, c.last_name, c.phone, c.email, n.nominee_name
            FROM sb_accounts sa
            JOIN customers c ON sa.customer_id = c.customer_id
            LEFT JOIN nominees n ON sa.nominee_id = n.nominee_id
            WHERE sa.account_number = ?
        """, (account_number,))
        account = c.fetchone()
        conn.close()
        return account
    
    @staticmethod
    def get_transaction_history(account_number, limit=50):
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM sb_transactions 
            WHERE account_number = ? 
            ORDER BY created_at DESC LIMIT ?
        """, (account_number, limit))
        transactions = c.fetchall()
        conn.close()
        return transactions

# ============================================
# MODULE 4: JOURNAL VOUCHER MODULE
# ============================================
class JournalVoucherModule:
    @staticmethod
    def generate_voucher_id(voucher_type):
        prefix = {'Payment': 'PMT', 'Receipt': 'RCP', 'Journal': 'JNL', 'Contra': 'CNT', 'Interest': 'INT'}
        return f"{prefix.get(voucher_type, 'JNL')}{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}"
    
    @staticmethod
    def create_voucher(voucher_type, voucher_date, narration, entries, created_by):
        conn = db.get_connection()
        c = conn.cursor()
        
        try:
            total_debit = sum(entry[1] for entry in entries if len(entry) > 1)
            total_credit = sum(entry[2] for entry in entries if len(entry) > 2)
            
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
            db.add_audit_entry(created_by, 'Journal Voucher', 'CREATE', 'journal_vouchers', voucher_id,
                             new_data={'type': voucher_type, 'amount': total_debit, 'narration': narration})
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
    
    @staticmethod
    def get_voucher_details(voucher_id):
        conn = db.get_connection()
        c = conn.cursor()
        
        c.execute("SELECT * FROM journal_vouchers WHERE voucher_id = ?", (voucher_id,))
        voucher = c.fetchone()
        
        if voucher:
            c.execute("""
                SELECT je.*, coa.account_name 
                FROM journal_entries je 
                JOIN chart_of_accounts coa ON je.account_head = coa.account_head
                WHERE je.voucher_id = ?
            """, (voucher_id,))
            entries = c.fetchall()
            conn.close()
            return voucher, entries
        
        conn.close()
        return None, None

# ============================================
# MODULE 5: CUSTOMER & KYC MODULE
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
                c.execute("""
                    INSERT INTO kyc_documents (customer_id, doc_type, doc_number, verification_status)
                    VALUES (?, 'Aadhaar', ?, 'Pending')
                """, (customer_id, data['aadhaar_number']))
            
            if 'pan_number' in data and data['pan_number']:
                c.execute("""
                    INSERT INTO kyc_documents (customer_id, doc_type, doc_number, verification_status)
                    VALUES (?, 'PAN', ?, 'Pending')
                """, (customer_id, data['pan_number']))
            
            if 'nominee_name' in data and data['nominee_name']:
                c.execute("""
                    INSERT INTO nominees (customer_id, nominee_name, relationship, date_of_birth, phone, percentage_share)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (customer_id, data['nominee_name'], data.get('nominee_relationship'),
                      data.get('nominee_dob'), data.get('nominee_phone'), data.get('nominee_percentage', 100)))
            
            conn.commit()
            db.add_audit_entry(created_by, 'Customer', 'CREATE', 'customers', customer_id,
                             new_data={'name': f"{data['first_name']} {data['last_name']}"})
            conn.close()
            return True, customer_id
            
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)
    
    @staticmethod
    def verify_kyc(customer_id, verified_by, status='Verified'):
        conn = db.get_connection()
        c = conn.cursor()
        
        try:
            c.execute("""
                UPDATE customers 
                SET kyc_status = ?, kyc_verified_by = ?, kyc_verified_date = ?, updated_at = ?
                WHERE customer_id = ?
            """, (status, verified_by, datetime.now(), datetime.now(), customer_id))
            
            c.execute("""
                UPDATE kyc_documents 
                SET verification_status = ?, verified_by = ?
                WHERE customer_id = ?
            """, (status, verified_by, customer_id))
            
            conn.commit()
            db.add_audit_entry(verified_by, 'Customer', 'KYC_VERIFY', 'customers', customer_id,
                             new_data={'kyc_status': status})
            conn.close()
            return True, f"KYC {status} successfully"
            
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)

# ============================================
# MODULE 6: FINANCIAL REPORTING MODULE
# ============================================
class FinancialReportingModule:
    @staticmethod
    def get_trial_balance(as_of_date=None):
        conn = db.get_connection()
        c = conn.cursor()
        
        if as_of_date is None:
            as_of_date = datetime.now().date()
        
        c.execute("""
            SELECT 
                coa.account_head,
                coa.account_name,
                coa.account_type,
                COALESCE(SUM(je.debit_amount), 0) as total_debit,
                COALESCE(SUM(je.credit_amount), 0) as total_credit
            FROM chart_of_accounts coa
            LEFT JOIN journal_entries je ON coa.account_head = je.account_head
            LEFT JOIN journal_vouchers jv ON je.voucher_id = jv.voucher_id AND jv.voucher_date <= ? AND jv.status = 'Approved'
            WHERE coa.is_active = 1
            GROUP BY coa.account_head
            ORDER BY coa.account_type, coa.account_head
        """, (as_of_date,))
        
        data = c.fetchall()
        conn.close()
        
        result = []
        total_debit = 0
        total_credit = 0
        
        for row in data:
            net = row[3] - row[4]
            if net > 0:
                dr_balance, cr_balance = net, 0
            else:
                dr_balance, cr_balance = 0, abs(net)
            
            total_debit += dr_balance
            total_credit += cr_balance
            
            result.append({
                'account_head': row[0],
                'account_name': row[1],
                'account_type': row[2],
                'debit': dr_balance,
                'credit': cr_balance
            })
        
        return result, total_debit, total_credit
    
    @staticmethod
    def get_balance_sheet(as_of_date=None):
        if as_of_date is None:
            as_of_date = datetime.now().date()
        
        trial_balance, _, _ = FinancialReportingModule.get_trial_balance(as_of_date)
        
        assets = [item for item in trial_balance if item['account_type'] == 'Asset' and (item['debit'] > 0 or item['credit'] > 0)]
        liabilities = [item for item in trial_balance if item['account_type'] == 'Liability' and (item['debit'] > 0 or item['credit'] > 0)]
        equity = [item for item in trial_balance if item['account_type'] == 'Equity' and (item['debit'] > 0 or item['credit'] > 0)]
        
        total_assets = sum(item['debit'] - item['credit'] for item in assets)
        total_liabilities = sum(item['credit'] - item['debit'] for item in liabilities)
        total_equity = sum(item['credit'] - item['debit'] for item in equity)
        
        return assets, liabilities, equity, total_assets, total_liabilities, total_equity
    
    @staticmethod
    def get_profit_loss(from_date, to_date):
        conn = db.get_connection()
        c = conn.cursor()
        
        c.execute("""
            SELECT 
                coa.account_head,
                coa.account_name,
                coa.account_type,
                COALESCE(SUM(je.credit_amount), 0) - COALESCE(SUM(je.debit_amount), 0) as net_balance
            FROM chart_of_accounts coa
            LEFT JOIN journal_entries je ON coa.account_head = je.account_head
            LEFT JOIN journal_vouchers jv ON je.voucher_id = jv.voucher_id 
                AND jv.voucher_date BETWEEN ? AND ? AND jv.status = 'Approved'
            WHERE coa.account_type IN ('Income', 'Expense') AND coa.is_active = 1
            GROUP BY coa.account_head
            ORDER BY coa.account_type, coa.account_head
        """, (from_date, to_date))
        
        data = c.fetchall()
        conn.close()
        
        income = [(item[0], item[1], item[3]) for item in data if item[2] == 'Income' and item[3] != 0]
        expenses = [(item[0], item[1], abs(item[3])) for item in data if item[2] == 'Expense' and item[3] != 0]
        
        total_income = sum(item[2] for item in income)
        total_expenses = sum(item[2] for item in expenses)
        net_profit = total_income - total_expenses
        
        return income, expenses, total_income, total_expenses, net_profit

# ============================================
# SESSION STATE INITIALIZATION
# ============================================
def init_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = 'Vouchers'

# ============================================
# UI COMPONENTS WITH DARK THEME
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

def voucher_ui():
    st.markdown('<h2 class="sub-header">📊 Journal Voucher Creation</h2>', unsafe_allow_html=True)
    
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT account_head, account_name, account_type FROM chart_of_accounts WHERE is_active = 1 ORDER BY account_type, account_head")
    accounts = c.fetchall()
    conn.close()
    
    account_options = [f"{acc[0]} - {acc[1]} ({acc[2]})" for acc in accounts]
    
    with st.form("voucher_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            voucher_type = st.selectbox("📝 Voucher Type *", ['Payment', 'Receipt', 'Journal', 'Contra', 'Interest'])
        with col2:
            voucher_date = st.date_input("📅 Voucher Date *", datetime.now().date())
        with col3:
            st.write("")
        
        narration = st.text_area("📄 Narration *", placeholder="Enter transaction description...")
        
        st.markdown("---")
        st.markdown('<h4 style="color: #f87171;">🔴 Debit Entries</h4>', unsafe_allow_html=True)
        
        debit_entries = []
        for i in range(3):
            col1, col2 = st.columns([3, 1])
            with col1:
                account = st.selectbox(f"Debit Account {i+1}", [""] + account_options, key=f"dr_{i}")
            with col2:
                amount = st.number_input(f"Amount {i+1}", min_value=0.0, step=100.0, key=f"dr_amt_{i}")
            
            if account and amount > 0:
                acc_head = account.split(" - ")[0]
                debit_entries.append((acc_head, amount, 0))
        
        st.markdown("---")
        st.markdown('<h4 style="color: #34d399;">🟢 Credit Entries</h4>', unsafe_allow_html=True)
        
        credit_entries = []
        for i in range(3):
            col1, col2 = st.columns([3, 1])
            with col1:
                account = st.selectbox(f"Credit Account {i+1}", [""] + account_options, key=f"cr_{i}")
            with col2:
                amount = st.number_input(f"Amount {i+1}", min_value=0.0, step=100.0, key=f"cr_amt_{i}")
            
            if account and amount > 0:
                acc_head = account.split(" - ")[0]
                credit_entries.append((acc_head, 0, amount))
        
        st.markdown("---")
        
        all_entries = debit_entries + credit_entries
        total_debit = sum(e[1] for e in all_entries)
        total_credit = sum(e[2] for e in all_entries)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Debit", f"₹{total_debit:,.2f}")
        with col2:
            st.metric("Total Credit", f"₹{total_credit:,.2f}")
        with col3:
            if total_debit > 0 and abs(total_debit - total_credit) < 0.01:
                st.success("✅ Balanced")
            elif total_debit > 0:
                st.error("❌ Not Balanced")
        
        if st.form_submit_button("📝 Create Voucher", use_container_width=True):
            if not narration:
                st.error("⚠️ Narration is required!")
            elif not debit_entries and not credit_entries:
                st.error("⚠️ At least one entry required!")
            elif abs(total_debit - total_credit) > 0.01:
                st.error("⚠️ Debit and Credit must be equal!")
            else:
                success, result = JournalVoucherModule.create_voucher(
                    voucher_type, voucher_date, narration, all_entries, st.session_state.user['user_id']
                )
                if success:
                    st.success(f"✅ Voucher created successfully! ID: {result}")
                    st.balloons()
                else:
                    st.error(result)
    
    st.markdown("---")
    st.markdown("### 📋 Recent Vouchers")
    
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT jv.voucher_id, jv.voucher_type, jv.voucher_date, jv.narration, jv.total_amount, 
               jv.status, u.full_name as created_by
        FROM journal_vouchers jv 
        LEFT JOIN users u ON jv.created_by = u.user_id
        ORDER BY jv.created_at DESC LIMIT 10
    """)
    vouchers = c.fetchall()
    conn.close()
    
    if vouchers:
        for v in vouchers:
            with st.expander(f"📄 {v[0]} | {v[1]} | {v[3]} | ₹{v[4]:,.2f} | {v[5]}"):
                conn = db.get_connection()
                c = conn.cursor()
                c.execute("""
                    SELECT je.account_head, coa.account_name, je.debit_amount, je.credit_amount
                    FROM journal_entries je
                    JOIN chart_of_accounts coa ON je.account_head = coa.account_head
                    WHERE je.voucher_id = ?
                """, (v[0],))
                entries = c.fetchall()
                conn.close()
                
                entry_data = []
                for e in entries:
                    entry_data.append({
                        'Account': f"{e[0]} - {e[1]}",
                        'Debit': f"₹{e[2]:,.2f}" if e[2] > 0 else "",
                        'Credit': f"₹{e[3]:,.2f}" if e[3] > 0 else ""
                    })
                st.dataframe(pd.DataFrame(entry_data), use_container_width=True, hide_index=True)
                st.caption(f"Created by: {v[6]} on {v[2]}")
    else:
        st.info("No vouchers created yet")

def sb_account_ui():
    st.markdown('<h2 class="sub-header">💰 Savings Bank Account</h2>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📂 Open Account", "💳 Deposit/Withdraw", "📊 Interest Calculation", "📋 Account List"])
    
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
                    initial_deposit = st.number_input("Initial Deposit *", min_value=500.0, value=1000.0, step=500.0)
                    interest_rate = st.number_input("Interest Rate (%)", min_value=0.0, value=4.0, step=0.25)
                with col2:
                    st.info("📌 Minimum Balance: ₹500")
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
        c.execute("SELECT account_number, customer_id, balance FROM sb_accounts WHERE status = 'Active'")
        accounts = c.fetchall()
        conn.close()
        
        if accounts:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 💚 Deposit")
                with st.form("deposit_form"):
                    acc_options = {f"{acc[0]} (₹{acc[2]:,.2f})": acc for acc in accounts}
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
                    acc_options = {f"{acc[0]} (₹{acc[2]:,.2f})": acc for acc in accounts}
                    wit_account = st.selectbox("Account", list(acc_options.keys()), key="wit_acc")
                    acc = acc_options[wit_account]
                    wit_amount = st.number_input("Amount *", min_value=1.0, max_value=float(acc[2]), step=100.0, key="wit_amt")
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
        st.markdown("### Quarterly Interest Calculation")
        
        if st.button("🧮 Calculate & Credit Interest for All Accounts", use_container_width=True):
            with st.spinner("Calculating interest..."):
                success, results = SBAccountModule.calculate_quarterly_interest(
                    created_by=st.session_state.user['user_id']
                )
                if success:
                    st.success(f"✅ Interest calculated for {len(results)} accounts")
                    if results:
                        df = pd.DataFrame(results)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.error(results)
        
        st.markdown("### Interest History")
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT account_number, interest_period_start, interest_period_end, 
                   minimum_balance, interest_rate, interest_amount, is_credited
            FROM interest_calculations 
            ORDER BY calculated_at DESC LIMIT 20
        """)
        history = c.fetchall()
        conn.close()
        
        if history:
            df = pd.DataFrame(history, columns=['Account', 'Period Start', 'Period End', 'Min Balance', 'Rate', 'Interest', 'Credited'])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No interest calculations yet")
    
    with tab4:
        st.markdown("### SB Account List")
        
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT sa.account_number, c.first_name || ' ' || c.last_name as customer,
                   sa.balance, sa.interest_rate, sa.opened_date, sa.status
            FROM sb_accounts sa
            JOIN customers c ON sa.customer_id = c.customer_id
            ORDER BY sa.opened_date DESC
        """)
        accounts = c.fetchall()
        conn.close()
        
        if accounts:
            df = pd.DataFrame(accounts, columns=['Account No', 'Customer', 'Balance', 'Rate', 'Opened', 'Status'])
            df['Balance'] = df['Balance'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No SB accounts")

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
            
            st.markdown("---")
            st.markdown("### Nominee Details")
            col1, col2 = st.columns(2)
            with col1:
                nominee_name = st.text_input("Nominee Name")
                nominee_relation = st.text_input("Relationship")
            with col2:
                nominee_dob = st.date_input("Nominee DOB", 
                                           min_value=datetime.now()-timedelta(days=365*100),
                                           max_value=datetime.now())
                nominee_percentage = st.number_input("Share %", min_value=0.0, max_value=100.0, value=100.0)
            
            if st.form_submit_button("Register Customer", use_container_width=True):
                if not first_name or not last_name or not phone:
                    st.error("⚠️ First name, last name, and phone are required!")
                else:
                    data = {
                        'first_name': first_name, 'last_name': last_name,
                        'date_of_birth': date_of_birth, 'gender': gender,
                        'email': email, 'phone': phone, 'address': address,
                        'city': city, 'state': state, 'pincode': pincode,
                        'aadhaar_number': aadhaar, 'pan_number': pan,
                        'nominee_name': nominee_name, 'nominee_relationship': nominee_relation,
                        'nominee_dob': nominee_dob, 'nominee_percentage': nominee_percentage
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

def reports_ui():
    st.markdown('<h2 class="sub-header">📈 Financial Reports</h2>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📊 Trial Balance", "💰 Balance Sheet", "📈 Profit & Loss"])
    
    with tab1:
        st.markdown("### Trial Balance")
        as_of_date = st.date_input("As of Date", datetime.now().date(), key="tb_date")
        
        if st.button("Generate Trial Balance", use_container_width=True):
            data, total_debit, total_credit = FinancialReportingModule.get_trial_balance(as_of_date)
            
            if data:
                df_data = []
                for item in data:
                    if item['debit'] > 0 or item['credit'] > 0:
                        df_data.append({
                            'Account Head': item['account_head'],
                            'Account Name': item['account_name'],
                            'Type': item['account_type'],
                            'Debit (₹)': f"{item['debit']:,.2f}" if item['debit'] > 0 else "",
                            'Credit (₹)': f"{item['credit']:,.2f}" if item['credit'] > 0 else ""
                        })
                
                df_data.append({
                    'Account Head': 'TOTAL',
                    'Account Name': '',
                    'Type': '',
                    'Debit (₹)': f"**{total_debit:,.2f}**",
                    'Credit (₹)': f"**{total_credit:,.2f}**"
                })
                
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                if abs(total_debit - total_credit) < 0.01:
                    st.success("✅ Trial Balance is balanced!")
                else:
                    st.error(f"❌ Difference: ₹{abs(total_debit - total_credit):,.2f}")
            else:
                st.info("No transactions found")
    
    with tab2:
        st.markdown("### Balance Sheet")
        bs_date = st.date_input("As at", datetime.now().date(), key="bs_date")
        
        if st.button("Generate Balance Sheet", use_container_width=True):
            assets, liabilities, equity, total_assets, total_liabilities, total_equity = FinancialReportingModule.get_balance_sheet(bs_date)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🟢 ASSETS")
                for item in assets:
                    amount = item['debit'] - item['credit']
                    if amount != 0:
                        st.write(f"- **{item['account_name']}:** ₹{amount:,.2f}")
                st.markdown(f"**Total Assets: ₹{total_assets:,.2f}**")
            
            with col2:
                st.markdown("#### 🔴 LIABILITIES & EQUITY")
                for item in liabilities:
                    amount = item['credit'] - item['debit']
                    if amount != 0:
                        st.write(f"- **{item['account_name']}:** ₹{amount:,.2f}")
                
                for item in equity:
                    amount = item['credit'] - item['debit']
                    if amount != 0:
                        st.write(f"- **{item['account_name']}:** ₹{amount:,.2f}")
                
                total_le = total_liabilities + total_equity
                st.markdown(f"**Total Liabilities & Equity: ₹{total_le:,.2f}**")
    
    with tab3:
        st.markdown("### Profit & Loss Statement")
        
        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input("From", datetime.now().replace(day=1), key="pl_from")
        with col2:
            to_date = st.date_input("To", datetime.now().date(), key="pl_to")
        
        if st.button("Generate P&L", use_container_width=True):
            income, expenses, total_income, total_expenses, net_profit = FinancialReportingModule.get_profit_loss(from_date, to_date)
            
            st.markdown("#### 🟢 INCOME")
            for item in income:
                st.write(f"- **{item[1]}:** ₹{item[2]:,.2f}")
            st.markdown(f"**Total Income: ₹{total_income:,.2f}**")
            
            st.markdown("---")
            st.markdown("#### 🔴 EXPENSES")
            for item in expenses:
                st.write(f"- **{item[1]}:** ₹{item[2]:,.2f}")
            st.markdown(f"**Total Expenses: ₹{total_expenses:,.2f}**")
            
            st.markdown("---")
            if net_profit >= 0:
                st.success(f"### 💰 Net Profit: ₹{net_profit:,.2f}")
            else:
                st.error(f"### 📉 Net Loss: ₹{abs(net_profit):,.2f}")

def head_management_ui():
    st.markdown('<h2 class="sub-header">📋 Chart of Accounts</h2>', unsafe_allow_html=True)
    
    with st.form("add_head"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            head = st.text_input("Account Head")
        with col2:
            name = st.text_input("Account Name")
        with col3:
            acc_type = st.selectbox("Type", ['Asset', 'Liability', 'Equity', 'Income', 'Expense'])
        with col4:
            category = st.text_input("Category")
        
        if st.form_submit_button("➕ Add Account Head", use_container_width=True):
            if head and name:
                try:
                    conn = db.get_connection()
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO chart_of_accounts (account_head, account_name, account_type, category)
                        VALUES (?, ?, ?, ?)
                    """, (head.upper().replace(' ', '_'), name, acc_type, category))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Added: {name}")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM chart_of_accounts WHERE is_active = 1 ORDER BY account_type, account_head")
    accounts = c.fetchall()
    conn.close()
    
    if accounts:
        df = pd.DataFrame(accounts, columns=['Head', 'Name', 'Type', 'Category', 'Sub Category', 'Active', 'Created'])
        st.dataframe(df[['Head', 'Name', 'Type', 'Category']], use_container_width=True, hide_index=True)

def verification_ui():
    st.markdown('<h2 class="sub-header">✅ Voucher Verification</h2>', unsafe_allow_html=True)
    
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT jv.voucher_id, jv.voucher_type, jv.voucher_date, jv.narration, 
               jv.total_amount, jv.status, jv.verification_status, u.full_name
        FROM journal_vouchers jv
        LEFT JOIN users u ON jv.created_by = u.user_id
        WHERE jv.verification_status = 'Pending' OR jv.status = 'Pending'
        ORDER BY jv.created_at DESC
    """)
    pending_vouchers = c.fetchall()
    conn.close()
    
    if pending_vouchers:
        for v in pending_vouchers:
            with st.expander(f"📄 {v[0]} | {v[1]} | {v[3]} | ₹{v[4]:,.2f} | {v[6]}"):
                conn = db.get_connection()
                c = conn.cursor()
                c.execute("""
                    SELECT je.account_head, coa.account_name, je.debit_amount, je.credit_amount
                    FROM journal_entries je
                    JOIN chart_of_accounts coa ON je.account_head = coa.account_head
                    WHERE je.voucher_id = ?
                """, (v[0],))
                entries = c.fetchall()
                conn.close()
                
                for e in entries:
                    if e[2] > 0:
                        st.write(f"🔴 **Dr:** {e[1]} - ₹{e[2]:,.2f}")
                    if e[3] > 0:
                        st.write(f"🟢 **Cr:** {e[1]} - ₹{e[3]:,.2f}")
                
                st.caption(f"Created by: {v[7]}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("✅ Verify", key=f"verify_{v[0]}"):
                        conn = db.get_connection()
                        c = conn.cursor()
                        c.execute("""
                            UPDATE journal_vouchers 
                            SET verification_status = 'Verified', verified_by = ?, approved_at = ?
                            WHERE voucher_id = ?
                        """, (st.session_state.user['user_id'], datetime.now(), v[0]))
                        conn.commit()
                        conn.close()
                        st.rerun()
                with col2:
                    if st.button("❌ Reject", key=f"reject_{v[0]}"):
                        conn = db.get_connection()
                        c = conn.cursor()
                        c.execute("""
                            UPDATE journal_vouchers 
                            SET verification_status = 'Rejected', verified_by = ?
                            WHERE voucher_id = ?
                        """, (st.session_state.user['user_id'], v[0]))
                        conn.commit()
                        conn.close()
                        st.rerun()
    else:
        st.info("No pending vouchers for verification")

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
            'Vouchers': '📊 Journal Vouchers',
            'SB Accounts': '💰 SB Accounts',
            'Customers': '👤 Customers',
            'Reports': '📈 Reports',
            'Trial Balance': '📋 Trial Balance',
            'Head Management': '🔧 Chart of Accounts',
            'Verification': '✅ Verification'
        }
        
        selected_tab = st.radio(
            "Navigation",
            list(tabs.keys()),
            format_func=lambda x: tabs[x],
            label_visibility="collapsed"
        )
        
        st.session_state.current_tab = selected_tab
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            AuthModule.logout(st.session_state.user['user_id'], 
                            st.session_state.user.get('session_id', ''))
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()
    
    if st.session_state.current_tab == 'Vouchers':
        voucher_ui()
    elif st.session_state.current_tab == 'SB Accounts':
        sb_account_ui()
    elif st.session_state.current_tab == 'Customers':
        customer_ui()
    elif st.session_state.current_tab == 'Reports':
        reports_ui()
    elif st.session_state.current_tab == 'Trial Balance':
        reports_ui()
    elif st.session_state.current_tab == 'Head Management':
        head_management_ui()
    elif st.session_state.current_tab == 'Verification':
        verification_ui()

if __name__ == "__main__":
    main()
      
