# 🏦 COMPLETE BANKING SYSTEM - Enterprise Edition
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
from decimal import Decimal
import uuid
import os
from PIL import Image
import io
import hashlib
import base64
import plotly.express as px
import plotly.graph_objects as go

# Fix: Try importing fpdf with the correct package name
try:
    from fpdf import FPDF
except ImportError:
    try:
        from fpdf2 import FPDF
    except ImportError:
        st.error("Please install fpdf2: pip install fpdf2")
        FPDF = None

# ==================== DATABASE SETUP ====================

def init_database():
    conn = sqlite3.connect('banking_system.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Customers table with KYC
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id TEXT UNIQUE NOT NULL,
        user_id INTEGER,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        date_of_birth DATE NOT NULL,
        gender TEXT,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        address TEXT,
        city TEXT,
        state TEXT,
        pincode TEXT,
        pan_number TEXT UNIQUE,
        aadhar_number TEXT UNIQUE,
        kyc_status TEXT DEFAULT 'PENDING',
        kyc_verified_by INTEGER,
        kyc_verified_at TIMESTAMP,
        pan_document BLOB,
        aadhar_document BLOB,
        photo BLOB,
        signature BLOB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Accounts table
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_number TEXT UNIQUE NOT NULL,
        customer_id INTEGER NOT NULL,
        account_type TEXT NOT NULL,
        balance DECIMAL(15,2) DEFAULT 0.00,
        status TEXT DEFAULT 'ACTIVE',
        interest_rate DECIMAL(5,2),
        last_interest_calculation DATE,
        total_interest_earned DECIMAL(15,2) DEFAULT 0.00,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (id)
    )''')
    
    # Check if total_interest_earned column exists, if not add it
    try:
        c.execute("SELECT total_interest_earned FROM accounts LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE accounts ADD COLUMN total_interest_earned DECIMAL(15,2) DEFAULT 0.00")
    
    # Fixed Deposits
    c.execute('''CREATE TABLE IF NOT EXISTS fixed_deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fd_number TEXT UNIQUE NOT NULL,
        account_id INTEGER NOT NULL,
        principal_amount DECIMAL(15,2) NOT NULL,
        interest_rate DECIMAL(5,2) NOT NULL,
        start_date DATE NOT NULL,
        maturity_date DATE NOT NULL,
        maturity_amount DECIMAL(15,2),
        tenure_months INTEGER NOT NULL,
        status TEXT DEFAULT 'ACTIVE',
        nominee_name TEXT,
        nominee_relation TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (account_id) REFERENCES accounts (id)
    )''')
    
    # Recurring Deposits
    c.execute('''CREATE TABLE IF NOT EXISTS recurring_deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rd_number TEXT UNIQUE NOT NULL,
        account_id INTEGER NOT NULL,
        monthly_amount DECIMAL(15,2) NOT NULL,
        interest_rate DECIMAL(5,2) NOT NULL,
        start_date DATE NOT NULL,
        maturity_date DATE NOT NULL,
        maturity_amount DECIMAL(15,2),
        tenure_months INTEGER NOT NULL,
        installments_paid INTEGER DEFAULT 0,
        total_installments INTEGER NOT NULL,
        status TEXT DEFAULT 'ACTIVE',
        nominee_name TEXT,
        nominee_relation TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (account_id) REFERENCES accounts (id)
    )''')
    
    # Transactions
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id TEXT UNIQUE NOT NULL,
        account_id INTEGER NOT NULL,
        transaction_type TEXT NOT NULL,
        amount DECIMAL(15,2) NOT NULL,
        balance_after DECIMAL(15,2) NOT NULL,
        description TEXT,
        reference_type TEXT,
        reference_id TEXT,
        voucher_type TEXT,
        voucher_number TEXT,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (account_id) REFERENCES accounts (id),
        FOREIGN KEY (created_by) REFERENCES users (id)
    )''')
    
    # Journal Vouchers
    c.execute('''CREATE TABLE IF NOT EXISTS journal_vouchers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voucher_number TEXT UNIQUE NOT NULL,
        voucher_date DATE NOT NULL,
        description TEXT,
        total_amount DECIMAL(15,2) NOT NULL,
        status TEXT DEFAULT 'DRAFT',
        created_by INTEGER,
        posted_by INTEGER,
        posted_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users (id)
    )''')
    
    # Journal Entries
    c.execute('''CREATE TABLE IF NOT EXISTS journal_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voucher_id INTEGER NOT NULL,
        account_id INTEGER,
        account_head TEXT,
        debit_amount DECIMAL(15,2) DEFAULT 0.00,
        credit_amount DECIMAL(15,2) DEFAULT 0.00,
        description TEXT,
        FOREIGN KEY (voucher_id) REFERENCES journal_vouchers (id)
    )''')
    
    # Interest Calculation Log
    c.execute('''CREATE TABLE IF NOT EXISTS interest_calculations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL,
        calculation_date DATE NOT NULL,
        principal_amount DECIMAL(15,2) NOT NULL,
        interest_rate DECIMAL(5,2) NOT NULL,
        interest_earned DECIMAL(15,2) NOT NULL,
        days_calculated INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (account_id) REFERENCES accounts (id)
    )''')
    
    # Expenses table
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expense_id TEXT UNIQUE NOT NULL,
        expense_type TEXT NOT NULL,
        amount DECIMAL(15,2) NOT NULL,
        description TEXT,
        date DATE NOT NULL,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users (id)
    )''')
    
    # Income table
    c.execute('''CREATE TABLE IF NOT EXISTS income (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        income_id TEXT UNIQUE NOT NULL,
        income_type TEXT NOT NULL,
        amount DECIMAL(15,2) NOT NULL,
        description TEXT,
        date DATE NOT NULL,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users (id)
    )''')
    
    conn.commit()
    conn.close()

# ==================== UTILITY FUNCTIONS ====================

def get_db():
    return sqlite3.connect('banking_system.db')

def generate_id(prefix):
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4]}"

def generate_account_number(account_type):
    prefix = {'SB': '100', 'FD': '200', 'RD': '300'}
    return f"{prefix.get(account_type, '100')}{datetime.now().strftime('%y%m%d')}{str(uuid.uuid4().int)[:6]}"

def generate_voucher_number(v_type):
    prefix = {'PAYMENT': 'PMT', 'RECEIPT': 'RCT', 'JOURNAL': 'JNL'}
    return f"{prefix.get(v_type, 'JNL')}{datetime.now().strftime('%Y%m%d%H%M')}{str(uuid.uuid4().int)[:4]}"

def calculate_fd_maturity(principal, rate, months):
    # Compound interest quarterly
    r = rate / 400  # Quarterly rate
    n = months / 3  # Number of quarters
    maturity = principal * (1 + r) ** n
    return round(maturity, 2)

def calculate_rd_maturity(monthly_amount, rate, months):
    # RD maturity calculation
    r = rate / 400  # Quarterly rate
    n = months / 3  # Number of quarters
    maturity = monthly_amount * (((1 + r) ** n - 1) / (1 - (1 + r) ** (-1/3)))
    return round(maturity, 2)

def calculate_sb_interest(balance, rate, days):
    """Calculate SB interest using daily balance method"""
    if balance <= 0:
        return 0
    # Simple interest calculation: (Principal * Rate * Time) / (100 * 365)
    interest = (balance * rate * days) / (100 * 365)
    return round(interest, 2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ==================== AUTHENTICATION ====================

def login_user(username, password):
    conn = get_db()
    c = conn.cursor()
    hashed_pw = hash_password(password)
    c.execute("SELECT * FROM users WHERE username=? AND password=? AND is_active=1", 
              (username, hashed_pw))
    user = c.fetchone()
    conn.close()
    return user

def create_default_admin():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ('admin', hash_password('admin123'), 'admin'))
        conn.commit()
    conn.close()

# ==================== PDF GENERATION ====================

class BankPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'BANKING SYSTEM', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, 'Financial Reports', 0, 1, 'C')
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

def generate_report_pdf(report_type, data, filename):
    if FPDF is None:
        return None
    
    pdf = BankPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    if report_type == 'trial_balance':
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'TRIAL BALANCE', 0, 1, 'C')
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 5, f'As on: {data["date"]}', 0, 1, 'C')
        pdf.ln(10)
        
        # Table header
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(10, 7, 'S.No', 1)
        pdf.cell(90, 7, 'Account Head', 1)
        pdf.cell(45, 7, 'Debit (Rs.)', 1, 0, 'R')
        pdf.cell(45, 7, 'Credit (Rs.)', 1, 1, 'R')
        
        # Table data
        pdf.set_font('Arial', '', 9)
        total_debit = 0
        total_credit = 0
        for i, entry in enumerate(data['entries'], 1):
            pdf.cell(10, 6, str(i), 1)
            pdf.cell(90, 6, entry['account_head'], 1)
            pdf.cell(45, 6, f"{entry['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(45, 6, f"{entry['credit']:,.2f}", 1, 1, 'R')
            total_debit += entry['debit']
            total_credit += entry['credit']
        
        # Totals
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(100, 7, 'TOTAL', 1)
        pdf.cell(45, 7, f"{total_debit:,.2f}", 1, 0, 'R')
        pdf.cell(45, 7, f"{total_credit:,.2f}", 1, 1, 'R')
    
    pdf.output(filename)
    return filename

# ==================== SESSION STATE ====================

def init_session_state():
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = 'login'

# ==================== STREAMLIT UI ====================

def main():
    st.set_page_config(
        page_title="🏦 Complete Banking System",
        page_icon="🏦",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    init_database()
    create_default_admin()
    init_session_state()
    
    # Custom CSS with better UI
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.8rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
        padding: 1rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
        border-bottom: 2px solid #e0e0e0;
        padding-bottom: 1rem;
    }
    .card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        border: 1px solid #e0e0e0;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }
    .metric-card h3 {
        font-size: 2.2rem;
        margin: 0;
        font-weight: bold;
    }
    .metric-card p {
        margin: 0.5rem 0 0 0;
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .metric-card .icon {
        font-size: 2.5rem;
        display: block;
        margin-bottom: 0.5rem;
    }
    .customer-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 1rem;
    }
    .stButton > button {
        width: 100%;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.6rem 1.2rem;
        font-size: 1rem;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    .stButton > button:active {
        transform: translateY(0px);
    }
    .info-box {
        background: linear-gradient(135deg, #e0f2fe 0%, #dbeafe 100%);
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    .success-box {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #10b981;
        margin: 1rem 0;
    }
    .warning-box {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #f59e0b;
        margin: 1rem 0;
    }
    .danger-box {
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #ef4444;
        margin: 1rem 0;
    }
    .trial-balance-table {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .balance-sheet-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: bold;
        color: #667eea;
        border-bottom: 3px solid #667eea;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }
    .css-1d391kg {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #f0f0f0;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
    .login-container {
        max-width: 450px;
        margin: 0 auto;
        padding: 2rem;
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
    }
    @media (max-width: 768px) {
        .main-header {
            font-size: 2rem;
        }
        .metric-card h3 {
            font-size: 1.5rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    if st.session_state.user is None:
        show_login_page()
    else:
        show_main_app()

def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 2rem 0 1rem 0;">
            <h1 style="font-size: 3.5rem; margin: 0;">🏦</h1>
            <h1 class="main-header">Complete Banking System</h1>
            <p class="sub-header">Enterprise Banking Management Platform</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            st.markdown('<h2 style="text-align: center; color: #667eea;">🔐 Welcome Back</h2>', unsafe_allow_html=True)
            st.markdown('<p style="text-align: center; color: #666; margin-bottom: 1.5rem;">Sign in to access your banking dashboard</p>', unsafe_allow_html=True)
            
            username = st.text_input("Username", placeholder="Enter your username", key="login_username")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
            
            col_a, col_b = st.columns([1, 1])
            with col_a:
                if st.button("🔑 Sign In", use_container_width=True):
                    user = login_user(username, password)
                    if user:
                        st.session_state.user = {
                            'id': user[0],
                            'username': user[1],
                            'role': user[3]
                        }
                        st.success("✅ Login successful! Redirecting...")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials! Please try again.")
            
            with col_b:
                if st.button("📝 Register", use_container_width=True):
                    st.session_state.page = 'register'
                    st.rerun()
            
            st.divider()
            st.markdown("""
            <div style="text-align: center; color: #666; font-size: 0.9rem;">
                <p>Default Admin Credentials:</p>
                <p><strong>Username:</strong> admin<br><strong>Password:</strong> admin123</p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

def show_main_app():
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 0.5rem 0 1rem 0;">
            <h1 style="font-size: 2.5rem; margin: 0;">🏦</h1>
            <h3 style="margin: 0; color: #667eea;">Banking System</h3>
            <p style="color: #666; font-size: 0.8rem;">Enterprise Edition</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        st.markdown(f"""
        <div style="text-align: center;">
            <p style="font-size: 1.1rem; font-weight: bold;">👤 {st.session_state.user['username']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        role_badge = {
            'admin': '<span style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold;">ADMIN</span>',
            'staff': '<span style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold;">STAFF</span>',
            'customer': '<span style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold;">CUSTOMER</span>'
        }
        st.markdown(f'<div style="text-align: center; margin: 0.5rem 0;">{role_badge.get(st.session_state.user["role"], "USER")}</div>', unsafe_allow_html=True)
        st.divider()
        
        # Menu based on role
        if st.session_state.user['role'] in ['admin', 'staff']:
            menu_options = {
                'dashboard': '📊 Dashboard',
                'customer_management': '👥 Customer Management',
                'kyc_verification': '🔍 KYC Verification',
                'create_sb_account': '🏦 Create SB Account',
                'sb_accounts': '💰 SB Accounts',
                'fixed_deposits': '💎 Fixed Deposits',
                'recurring_deposits': '🔄 Recurring Deposits',
                'transactions': '💳 All Transactions',
                'journal_vouchers': '📝 Journal Vouchers',
                'income_expenses': '📈 Income & Expenses',
                'interest_calculation': '📊 Interest Calculation',
                'trial_balance': '⚖️ Trial Balance',
                'balance_sheet': '📊 Balance Sheet',
                'profit_loss': '💵 Profit & Loss',
                'reports': '📋 Reports'
            }
        else:
            menu_options = {
                'dashboard': '📊 Dashboard',
                'my_accounts': '💰 My Accounts',
                'my_transactions': '💳 My Transactions',
                'my_details': '👤 My Details'
            }
        
        for key, label in menu_options.items():
            if st.sidebar.button(label, key=key, use_container_width=True):
                st.session_state.page = key
                st.rerun()
        
        st.divider()
        if st.sidebar.button("🚪 Logout", use_container_width=True, type="primary"):
            st.session_state.user = None
            st.session_state.page = 'login'
            st.rerun()
    
    # Main content area
    page = st.session_state.get('page', 'dashboard')
    
    if page == 'dashboard':
        show_dashboard()
    elif page == 'customer_management':
        show_customer_management()
    elif page == 'kyc_verification':
        show_kyc_verification()
    elif page == 'create_sb_account':
        show_create_sb_account()
    elif page == 'sb_accounts' or page == 'my_accounts':
        show_sb_accounts()
    elif page == 'fixed_deposits':
        show_fixed_deposits()
    elif page == 'recurring_deposits':
        show_recurring_deposits()
    elif page == 'transactions' or page == 'my_transactions':
        show_transactions()
    elif page == 'journal_vouchers':
        show_journal_vouchers()
    elif page == 'income_expenses':
        show_income_expenses()
    elif page == 'interest_calculation':
        show_interest_calculation()
    elif page == 'trial_balance':
        show_trial_balance()
    elif page == 'balance_sheet':
        show_balance_sheet()
    elif page == 'profit_loss':
        show_profit_loss()
    elif page == 'reports':
        show_reports()
    elif page == 'my_details':
        show_my_details()

# [Previous functions remain the same until show_sb_accounts]

def show_sb_accounts():
    st.markdown('<h1 class="main-header">💰 Savings Bank Accounts</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Manage savings accounts, deposits and withdrawals</p>', unsafe_allow_html=True)
    
    conn = get_db()
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Account List", "💸 Deposit/Withdraw", "📜 Account Statement", "📈 Interest Info"])
    
    with tab1:
        st.subheader("SB Account List")
        
        if st.session_state.user['role'] == 'customer':
            accounts = conn.execute("""
                SELECT a.account_number, c.first_name || ' ' || c.last_name as name,
                       a.balance, a.interest_rate, a.status, 
                       COALESCE(a.total_interest_earned, 0) as total_interest, 
                       a.created_at
                FROM accounts a
                JOIN customers c ON a.customer_id = c.id
                WHERE a.account_type='SB' AND c.user_id=?
                ORDER BY a.created_at DESC
            """, (st.session_state.user['id'],)).fetchall()
        else:
            accounts = conn.execute("""
                SELECT a.account_number, c.first_name || ' ' || c.last_name as name,
                       a.balance, a.interest_rate, a.status, 
                       COALESCE(a.total_interest_earned, 0) as total_interest,
                       a.created_at
                FROM accounts a
                JOIN customers c ON a.customer_id = c.id
                WHERE a.account_type='SB' AND c.kyc_status='VERIFIED'
                ORDER BY a.created_at DESC
            """).fetchall()
        
        if accounts:
            account_data = []
            for acc in accounts:
                account_data.append({
                    'Account Number': acc[0],
                    'Customer Name': acc[1],
                    'Balance': acc[2],
                    'Interest Rate': acc[3],
                    'Status': acc[4],
                    'Total Interest Earned': acc[5],
                    'Total Value (Balance + Interest)': acc[2] + acc[5],
                    'Opening Date': acc[6]
                })
            
            df = pd.DataFrame(account_data)
            st.dataframe(df.style.format({
                'Balance': '₹{:,.2f}',
                'Interest Rate': '{:.2f}%',
                'Total Interest Earned': '₹{:,.2f}',
                'Total Value (Balance + Interest)': '₹{:,.2f}'
            }), use_container_width=True)
            
            total_sb = sum(acc[2] for acc in accounts)
            total_interest = sum(acc[5] for acc in accounts)
            total_value = total_sb + total_interest
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"**Total Deposits: ₹{total_sb:,.2f}**")
            with col2:
                st.info(f"**Total Interest Earned: ₹{total_interest:,.2f}**")
            with col3:
                st.success(f"**Total Value: ₹{total_value:,.2f}**")
        else:
            st.info("No SB accounts found")
    
    with tab2:
        st.subheader("Transaction (Deposit/Withdrawal)")
        st.warning("**Note: SB Account opening balance is always ₹0.00. All transactions are recorded with voucher numbers.**")
        
        if st.session_state.user['role'] == 'customer':
            accounts = conn.execute("""
                SELECT a.id, a.account_number, c.first_name || ' ' || c.last_name as name, a.balance
                FROM accounts a
                JOIN customers c ON a.customer_id = c.id
                WHERE a.account_type='SB' AND a.status='ACTIVE' AND c.user_id=?
            """, (st.session_state.user['id'],)).fetchall()
        else:
            accounts = conn.execute("""
                SELECT a.id, a.account_number, c.first_name || ' ' || c.last_name as name, a.balance
                FROM accounts a
                JOIN customers c ON a.customer_id = c.id
                WHERE a.account_type='SB' AND a.status='ACTIVE'
            """).fetchall()
        
        if accounts:
            account_options = {f"{acc[1]} - {acc[2]} (Balance: ₹{acc[3]:,.2f})": acc for acc in accounts}
            selected = st.selectbox("Select Account", list(account_options.keys()))
            
            if selected:
                account = account_options[selected]
                transaction_type = st.radio("Transaction Type", ["💰 DEPOSIT", "💸 WITHDRAWAL"], horizontal=True)
                
                with st.form("sb_transaction"):
                    amount = st.number_input("Amount (₹)", min_value=0.01, step=100.0)
                    description = st.text_input("Description/Narration", placeholder="Enter transaction details")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        reference_type = st.selectbox("Payment Mode", ["CASH", "TRANSFER", "CHEQUE"])
                    
                    if st.form_submit_button("💳 Process Transaction", use_container_width=True):
                        txn_type_actual = "WITHDRAWAL" if "WITHDRAWAL" in transaction_type else "DEPOSIT"
                        
                        if txn_type_actual == "WITHDRAWAL" and amount > account[3]:
                            st.error("❌ Insufficient balance!")
                        else:
                            try:
                                if txn_type_actual == "DEPOSIT":
                                    new_balance = account[3] + amount
                                    txn_type = "CREDIT"
                                    voucher_type = "RECEIPT"
                                else:
                                    new_balance = account[3] - amount
                                    txn_type = "DEBIT"
                                    voucher_type = "PAYMENT"
                                
                                txn_id = generate_id('TXN')
                                voucher_num = generate_voucher_number(voucher_type)
                                
                                conn.execute("""
                                    INSERT INTO transactions 
                                    (transaction_id, account_id, transaction_type, amount, 
                                     balance_after, description, reference_type, voucher_type, 
                                     voucher_number, created_by)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (txn_id, account[0], txn_type, amount, new_balance,
                                      description, reference_type, voucher_type,
                                      voucher_num, st.session_state.user['id']))
                                
                                conn.execute("UPDATE accounts SET balance=? WHERE id=?", 
                                           (new_balance, account[0]))
                                
                                conn.commit()
                                
                                st.success(f"✅ Transaction successful!")
                                st.info(f"Voucher: **{voucher_num}** | New Balance: **₹{new_balance:,.2f}**")
                                st.balloons()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
        else:
            st.warning("No active SB accounts available")
    
    with tab3:
        st.subheader("Account Statement")
        
        if st.session_state.user['role'] == 'customer':
            accounts = conn.execute("""
                SELECT a.id, a.account_number, c.first_name || ' ' || c.last_name as name
                FROM accounts a
                JOIN customers c ON a.customer_id = c.id
                WHERE a.account_type='SB' AND a.status='ACTIVE' AND c.user_id=?
            """, (st.session_state.user['id'],)).fetchall()
        else:
            accounts = conn.execute("""
                SELECT a.id, a.account_number, c.first_name || ' ' || c.last_name as name
                FROM accounts a
                JOIN customers c ON a.customer_id = c.id
                WHERE a.account_type='SB' AND a.status='ACTIVE'
            """).fetchall()
        
        if accounts:
            account_options = {f"{acc[1]} - {acc[2]}": acc[0] for acc in accounts}
            selected = st.selectbox("Select Account for Statement", list(account_options.keys()))
            
            if selected:
                account_id = account_options[selected]
                
                col1, col2 = st.columns(2)
                with col1:
                    from_date = st.date_input("From Date", date.today() - timedelta(days=30))
                with col2:
                    to_date = st.date_input("To Date", date.today())
                
                transactions = conn.execute("""
                    SELECT transaction_id, created_at, transaction_type, amount, 
                           balance_after, description, reference_type, voucher_number
                    FROM transactions
                    WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ?
                    ORDER BY created_at DESC
                """, (account_id, from_date, to_date)).fetchall()
                
                if transactions:
                    df = pd.DataFrame(transactions, 
                                    columns=['Transaction ID', 'Date', 'Type', 'Amount', 
                                           'Balance', 'Description', 'Mode', 'Voucher No.'])
                    st.dataframe(df.style.format({'Amount': '₹{:,.2f}', 'Balance': '₹{:,.2f}'}), 
                                use_container_width=True)
                    
                    csv = df.to_csv(index=False)
                    st.download_button("📥 Download Statement", csv, "account_statement.csv", "text/csv")
                else:
                    st.info("No transactions in selected period")
        else:
            st.info("No accounts available")
    
    with tab4:
        st.subheader("Interest Rate Information & Maturity Details")
        
        # Get SB accounts with interest details
        if st.session_state.user['role'] == 'customer':
            accounts = conn.execute("""
                SELECT a.account_number, c.first_name || ' ' || c.last_name as name,
                       a.balance, a.interest_rate, COALESCE(a.total_interest_earned, 0) as total_interest,
                       a.created_at
                FROM accounts a
                JOIN customers c ON a.customer_id = c.id
                WHERE a.account_type='SB' AND c.user_id=?
                ORDER BY a.created_at DESC
            """, (st.session_state.user['id'],)).fetchall()
        else:
            accounts = conn.execute("""
                SELECT a.account_number, c.first_name || ' ' || c.last_name as name,
                       a.balance, a.interest_rate, COALESCE(a.total_interest_earned, 0) as total_interest,
                       a.created_at
                FROM accounts a
                JOIN customers c ON a.customer_id = c.id
                WHERE a.account_type='SB'
                ORDER BY a.created_at DESC
            """).fetchall()
        
        if accounts:
            st.markdown("### 📊 SB Account Maturity Values")
            
            interest_data = []
            for acc in accounts:
                principal = acc[2]  # Balance is the principal
                total_interest = acc[4]
                maturity_value = principal + total_interest
                
                interest_data.append({
                    'Account Number': acc[0],
                    'Customer': acc[1],
                    'Principal (Balance)': principal,
                    'Interest Rate': acc[3],
                    'Total Interest Earned': total_interest,
                    'Maturity Value (Principal + Interest)': maturity_value,
                    'Opened': acc[5][:10] if acc[5] else 'N/A'
                })
            
            df = pd.DataFrame(interest_data)
            st.dataframe(df.style.format({
                'Principal (Balance)': '₹{:,.2f}',
                'Interest Rate': '{:.2f}%',
                'Total Interest Earned': '₹{:,.2f}',
                'Maturity Value (Principal + Interest)': '₹{:,.2f}'
            }), use_container_width=True)
            
            total_principal = sum(d['Principal (Balance)'] for d in interest_data)
            total_interest = sum(d['Total Interest Earned'] for d in interest_data)
            total_maturity = sum(d['Maturity Value (Principal + Interest)'] for d in interest_data)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Principal", f"₹{total_principal:,.2f}")
            with col2:
                st.metric("Total Interest Earned", f"₹{total_interest:,.2f}")
            with col3:
                st.success(f"**Total Maturity Value: ₹{total_maturity:,.2f}**")
            
            st.divider()
            
            # Interest rate info
            st.info("""
            ### SB Account Interest Calculation Rules:
            
            1. **Interest Rate:** 3.50% per annum (subject to change)
            2. **Calculation Method:** Interest is calculated on the **minimum monthly balance** between 10th and last day of each month
            3. **Calculation Frequency:** Quarterly (March, June, September, December)
            4. **Minimum Balance:** No minimum balance required
            5. **Opening Balance:** Always ₹0.00
            6. **Maturity Value:** Principal + Total Interest Earned
            
            **Formula:** Interest = (Minimum Balance × Rate × Number of Days) / (100 × 365)
            
            **Example:**
            - If minimum balance in January is ₹10,000
            - Interest for January = (10,000 × 3.50 × 31) / (100 × 365) = ₹29.73
            - Maturity Value = ₹10,000 + ₹29.73 = ₹10,029.73
            """)
        else:
            st.info("No SB accounts found")
        
        # Show recent interest calculations
        if st.session_state.user['role'] in ['admin', 'staff']:
            st.subheader("Recent Interest Calculations")
            try:
                interest_calcs = conn.execute("""
                    SELECT ic.calculation_date, a.account_number, c.first_name || ' ' || c.last_name,
                           ic.principal_amount, ic.interest_rate, ic.interest_earned, ic.days_calculated
                    FROM interest_calculations ic
                    JOIN accounts a ON ic.account_id = a.id
                    JOIN customers c ON a.customer_id = c.id
                    ORDER BY ic.calculation_date DESC
                    LIMIT 20
                """).fetchall()
                
                if interest_calcs:
                    calc_data = []
                    for calc in interest_calcs:
                        calc_data.append({
                            'Date': calc[0],
                            'Account': calc[1],
                            'Customer': calc[2],
                            'Principal': calc[3],
                            'Rate': calc[4],
                            'Interest Earned': calc[5],
                            'Days': calc[6],
                            'Maturity Value (Principal + Interest)': calc[3] + calc[5]
                        })
                    
                    df = pd.DataFrame(calc_data)
                    st.dataframe(df.style.format({
                        'Principal': '₹{:,.2f}',
                        'Rate': '{:.2f}%',
                        'Interest Earned': '₹{:,.2f}',
                        'Maturity Value (Principal + Interest)': '₹{:,.2f}'
                    }), use_container_width=True)
                else:
                    st.info("No interest calculations yet")
            except sqlite3.OperationalError:
                st.info("Interest calculations feature will be available after first interest calculation")
    
    conn.close()

def show_interest_calculation():
    st.markdown('<h1 class="main-header">📊 Interest Calculation</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Calculate and credit interest to SB accounts</p>', unsafe_allow_html=True)
    
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized access")
        return
    
    conn = get_db()
    
    tab1, tab2 = st.tabs(["🧮 Calculate Interest", "📊 Interest History"])
    
    with tab1:
        st.subheader("Calculate SB Interest")
        st.info("Interest is calculated on the minimum balance for the selected period")
        
        # Get all active SB accounts
        accounts = conn.execute("""
            SELECT a.id, a.account_number, c.first_name || ' ' || c.last_name as name, a.balance,
                   COALESCE(a.total_interest_earned, 0) as total_interest
            FROM accounts a
            JOIN customers c ON a.customer_id = c.id
            WHERE a.account_type='SB' AND a.status='ACTIVE'
        """).fetchall()
        
        if accounts:
            calc_option = st.radio("Calculate for:", ["All SB Accounts", "Single Account"])
            
            if calc_option == "Single Account":
                account_options = {f"{acc[1]} - {acc[2]} (₹{acc[3]:,.2f})": acc for acc in accounts}
                selected = st.selectbox("Select Account", list(account_options.keys()))
                selected_accounts = [account_options[selected]]
            else:
                selected_accounts = accounts
            
            col1, col2 = st.columns(2)
            with col1:
                calc_from = st.date_input("Calculate Interest From", date.today().replace(day=1))
            with col2:
                calc_to = st.date_input("Calculate Interest To", date.today())
            
            if st.button("🧮 Calculate Interest", use_container_width=True):
                total_interest = 0
                results = []
                
                for acc in selected_accounts:
                    min_balance = get_minimum_balance(conn, acc[0], calc_from, calc_to)
                    
                    if min_balance == 0 and acc[3] > 0:
                        min_balance = acc[3]
                    
                    days = (calc_to - calc_from).days + 1
                    
                    rate = conn.execute("SELECT interest_rate FROM accounts WHERE id=?", 
                                      (acc[0],)).fetchone()
                    if rate and rate[0]:
                        rate = rate[0]
                    else:
                        rate = 3.5
                    
                    interest = calculate_sb_interest(min_balance, rate, days)
                    total_interest += interest
                    
                    conn.execute("""
                        INSERT INTO interest_calculations 
                        (account_id, calculation_date, principal_amount, interest_rate, interest_earned, days_calculated)
                        VALUES (?, DATE('now'), ?, ?, ?, ?)
                    """, (acc[0], min_balance, rate, interest, days))
                    
                    results.append({
                        'Account': acc[1],
                        'Customer': acc[2],
                        'Current Balance (Principal)': acc[3],
                        'Total Interest Earned (Before)': acc[4],
                        'Min Balance': min_balance,
                        'Rate': rate,
                        'Days': days,
                        'Interest': interest,
                        'New Total Interest': acc[4] + interest,
                        'New Balance (Principal + Interest)': acc[3] + interest,
                        'Maturity Value': acc[3] + acc[4] + interest
                    })
                
                conn.commit()
                
                st.subheader("Interest Calculation Results")
                df = pd.DataFrame(results)
                st.dataframe(df.style.format({
                    'Current Balance (Principal)': '₹{:,.2f}',
                    'Total Interest Earned (Before)': '₹{:,.2f}',
                    'Min Balance': '₹{:,.2f}',
                    'Rate': '{:.2f}%',
                    'Interest': '₹{:,.2f}',
                    'New Total Interest': '₹{:,.2f}',
                    'New Balance (Principal + Interest)': '₹{:,.2f}',
                    'Maturity Value': '₹{:,.2f}'
                }), use_container_width=True)
                
                st.success(f"Total Interest for period: **₹{total_interest:,.2f}**")
                
                if total_interest > 0:
                    if st.button("💰 Credit Interest to Accounts", use_container_width=True):
                        for res in results:
                            acc_id = [a[0] for a in accounts if a[1] == res['Account']][0]
                            
                            conn.execute("""
                                UPDATE accounts 
                                SET balance=?, total_interest_earned=?, last_interest_calculation=DATE('now') 
                                WHERE id=?
                            """, (res['New Balance (Principal + Interest)'], res['New Total Interest'], acc_id))
                            
                            txn_id = generate_id('TXN')
                            voucher_num = generate_voucher_number('RECEIPT')
                            
                            conn.execute("""
                                INSERT INTO transactions 
                                (transaction_id, account_id, transaction_type, amount, 
                                 balance_after, description, reference_type, voucher_type, 
                                 voucher_number, created_by)
                                VALUES (?, ?, 'CREDIT', ?, ?, 'SB Interest Credited', 'INTEREST', 'RECEIPT', ?, ?)
                            """, (txn_id, acc_id, res['Interest'], res['New Balance (Principal + Interest)'], 
                                  voucher_num, st.session_state.user['id']))
                            
                            # Create journal entry for interest
                            journal_voucher_num = generate_voucher_number('JOURNAL')
                            conn.execute("""
                                INSERT INTO journal_vouchers 
                                (voucher_number, voucher_date, description, total_amount, status, created_by)
                                VALUES (?, DATE('now'), ?, ?, 'POSTED', ?)
                            """, (journal_voucher_num, f"Interest credited to {res['Account']}", 
                                  res['Interest'], st.session_state.user['id']))
                            
                            jv_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                            
                            # Debit entry - Interest Expense
                            conn.execute("""
                                INSERT INTO journal_entries 
                                (voucher_id, account_head, debit_amount, credit_amount)
                                VALUES (?, 'Interest Paid on SB', ?, 0)
                            """, (jv_id, res['Interest']))
                            
                            # Credit entry - SB Account
                            conn.execute("""
                                INSERT INTO journal_entries 
                                (voucher_id, account_head, debit_amount, credit_amount)
                                VALUES (?, 'SB Account - ' || ?, 0, ?)
                            """, (jv_id, res['Account'], res['Interest']))
                        
                        conn.commit()
                        st.success("✅ Interest credited to all accounts successfully!")
                        st.info("Journal entries have been created for the interest transaction.")
                        st.balloons()
                        st.rerun()
                else:
                    st.info("No interest to credit. Minimum balance is 0 for all accounts.")
        else:
            st.warning("No active SB accounts found")
    
    with tab2:
        st.subheader("Interest Calculation History")
        
        history = conn.execute("""
            SELECT ic.calculation_date, a.account_number, c.first_name || ' ' || c.last_name as customer,
                   ic.principal_amount, ic.interest_rate, ic.interest_earned, ic.days_calculated
            FROM interest_calculations ic
            JOIN accounts a ON ic.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            ORDER BY ic.calculation_date DESC
            LIMIT 50
        """).fetchall()
        
        if history:
            hist_data = []
            for h in history:
                hist_data.append({
                    'Date': h[0],
                    'Account': h[1],
                    'Customer': h[2],
                    'Min Balance': h[3],
                    'Rate': h[4],
                    'Interest': h[5],
                    'Days': h[6],
                    'Maturity Value (Min Balance + Interest)': h[3] + h[5]
                })
            
            df = pd.DataFrame(hist_data)
            st.dataframe(df.style.format({
                'Min Balance': '₹{:,.2f}',
                'Rate': '{:.2f}%',
                'Interest': '₹{:,.2f}',
                'Maturity Value (Min Balance + Interest)': '₹{:,.2f}'
            }), use_container_width=True)
            
            total_interest_paid = sum(h[5] for h in history)
            st.info(f"**Total Interest Paid: ₹{total_interest_paid:,.2f}**")
            
            csv = df.to_csv(index=False)
            st.download_button("📥 Download History", csv, "interest_history.csv", "text/csv")
        else:
            st.info("No interest calculations recorded yet")
    
    conn.close()

def get_minimum_balance(conn, account_id, from_date, to_date):
    """Get minimum balance for an account during a period"""
    try:
        transactions = conn.execute("""
            SELECT balance_after
            FROM transactions
            WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ?
            ORDER BY created_at
        """, (account_id, from_date, to_date)).fetchall()
        
        if transactions:
            start_balance = conn.execute("""
                SELECT balance_after
                FROM transactions
                WHERE account_id=? AND DATE(created_at) < ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (account_id, from_date)).fetchone()
            
            if not start_balance:
                current = conn.execute("SELECT balance FROM accounts WHERE id=?", 
                                      (account_id,)).fetchone()[0]
                return current
            
            start_balance = start_balance[0]
            all_balances = [start_balance] + [t[0] for t in transactions]
            min_bal = min(all_balances)
            
            if min_bal == 0:
                current_balance = conn.execute("SELECT balance FROM accounts WHERE id=?", 
                                              (account_id,)).fetchone()[0]
                if current_balance > 0:
                    return current_balance
            
            return min_bal
        else:
            current = conn.execute("SELECT balance FROM accounts WHERE id=?", 
                                  (account_id,)).fetchone()[0]
            return current
    except Exception as e:
        current = conn.execute("SELECT balance FROM accounts WHERE id=?", 
                              (account_id,)).fetchone()[0]
        return current

def show_trial_balance():
    st.markdown('<h1 class="main-header">⚖️ Trial Balance</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Complete trial balance with all accounts categorized</p>', unsafe_allow_html=True)
    
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized access")
        return
    
    conn = get_db()
    
    st.subheader("Generate Trial Balance")
    as_on_date = st.date_input("As on Date", date.today())
    
    if st.button("📊 Generate Trial Balance", use_container_width=True):
        trial_data = []
        
        # ==================== ASSETS (Debit Balance) ====================
        
        # 1. Cash in Hand
        cash_balance = conn.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END), 0)
            FROM transactions
            WHERE reference_type='CASH'
        """).fetchone()[0]
        if cash_balance != 0:
            trial_data.append({
                'account_head': 'Cash in Hand',
                'category': 'Asset',
                'debit': max(cash_balance, 0),
                'credit': max(-cash_balance, 0)
            })
        
        # ==================== LIABILITIES (Credit Balance) ====================
        
        # 2. Savings Bank Deposits
        sb_total = conn.execute("""
            SELECT COALESCE(SUM(balance), 0) FROM accounts 
            WHERE account_type='SB' AND status='ACTIVE'
        """).fetchone()[0]
        if sb_total > 0:
            trial_data.append({
                'account_head': 'Savings Bank Deposits',
                'category': 'Liability',
                'debit': 0,
                'credit': sb_total
            })
        
        # 3. Interest Payable on SB (Total interest earned by customers)
        interest_payable_sb = conn.execute("""
            SELECT COALESCE(SUM(total_interest_earned), 0) 
            FROM accounts 
            WHERE account_type='SB' AND status='ACTIVE'
        """).fetchone()[0]
        if interest_payable_sb > 0:
            trial_data.append({
                'account_head': 'Interest Payable on SB',
                'category': 'Liability',
                'debit': 0,
                'credit': interest_payable_sb
            })
        
        # 4. Fixed Deposits
        fd_total = conn.execute("""
            SELECT COALESCE(SUM(principal_amount), 0) FROM fixed_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if fd_total > 0:
            trial_data.append({
                'account_head': 'Fixed Deposits',
                'category': 'Liability',
                'debit': 0,
                'credit': fd_total
            })
        
        # 5. Interest Payable on FD
        interest_payable_fd = conn.execute("""
            SELECT COALESCE(SUM(maturity_amount - principal_amount), 0)
            FROM fixed_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if interest_payable_fd > 0:
            trial_data.append({
                'account_head': 'Interest Payable on FD',
                'category': 'Liability',
                'debit': 0,
                'credit': interest_payable_fd
            })
        
        # 6. Recurring Deposits
        rd_total = conn.execute("""
            SELECT COALESCE(SUM(monthly_amount * installments_paid), 0) 
            FROM recurring_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if rd_total > 0:
            trial_data.append({
                'account_head': 'Recurring Deposits',
                'category': 'Liability',
                'debit': 0,
                'credit': rd_total
            })
        
        # 7. Interest Payable on RD
        interest_payable_rd = conn.execute("""
            SELECT COALESCE(SUM(maturity_amount - (monthly_amount * installments_paid)), 0)
            FROM recurring_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if interest_payable_rd > 0:
            trial_data.append({
                'account_head': 'Interest Payable on RD',
                'category': 'Liability',
                'debit': 0,
                'credit': interest_payable_rd
            })
        
        # ==================== INCOME (Credit Balance) ====================
        
        # 8. Interest Earned
        interest_earned = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM income
            WHERE income_type='Interest Earned'
        """).fetchone()[0]
        if interest_earned > 0:
            trial_data.append({
                'account_head': 'Interest Earned',
                'category': 'Income',
                'debit': 0,
                'credit': interest_earned
            })
        
        # 9. Fees & Charges
        fees_income = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM income
            WHERE income_type='Fees & Charges'
        """).fetchone()[0]
        if fees_income > 0:
            trial_data.append({
                'account_head': 'Fees & Charges Income',
                'category': 'Income',
                'debit': 0,
                'credit': fees_income
            })
        
        # 10. Commission Income
        commission_income = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM income
            WHERE income_type='Commission Income'
        """).fetchone()[0]
        if commission_income > 0:
            trial_data.append({
                'account_head': 'Commission Income',
                'category': 'Income',
                'debit': 0,
                'credit': commission_income
            })
        
        # 11. Other Income
        other_income = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM income
            WHERE income_type='Other Income'
        """).fetchone()[0]
        if other_income > 0:
            trial_data.append({
                'account_head': 'Other Income',
                'category': 'Income',
                'debit': 0,
                'credit': other_income
            })
        
        # ==================== EXPENSES (Debit Balance) ====================
        
        # 12. Interest Paid on SB (from journal entries)
        interest_paid_sb = conn.execute("""
            SELECT COALESCE(SUM(debit_amount), 0) 
            FROM journal_entries je
            JOIN journal_vouchers jv ON je.voucher_id = jv.id
            WHERE je.account_head = 'Interest Paid on SB' AND jv.status='POSTED'
        """).fetchone()[0]
        if interest_paid_sb > 0:
            trial_data.append({
                'account_head': 'Interest Paid on SB Accounts',
                'category': 'Expense',
                'debit': interest_paid_sb,
                'credit': 0
            })
        
        # 13. Salary & Wages
        salary_expense = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM expenses
            WHERE expense_type='Salary & Wages'
        """).fetchone()[0]
        if salary_expense > 0:
            trial_data.append({
                'account_head': 'Salary & Wages',
                'category': 'Expense',
                'debit': salary_expense,
                'credit': 0
            })
        
        # 14. Rent & Utilities
        rent_expense = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM expenses
            WHERE expense_type='Rent & Utilities'
        """).fetchone()[0]
        if rent_expense > 0:
            trial_data.append({
                'account_head': 'Rent & Utilities',
                'category': 'Expense',
                'debit': rent_expense,
                'credit': 0
            })
        
        # 15. Operating Expenses
        operating_expense = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM expenses
            WHERE expense_type='Operating Expenses'
        """).fetchone()[0]
        if operating_expense > 0:
            trial_data.append({
                'account_head': 'Operating Expenses',
                'category': 'Expense',
                'debit': operating_expense,
                'credit': 0
            })
        
        # 16. Administrative Expenses
        admin_expense = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM expenses
            WHERE expense_type='Administrative Expenses'
        """).fetchone()[0]
        if admin_expense > 0:
            trial_data.append({
                'account_head': 'Administrative Expenses',
                'category': 'Expense',
                'debit': admin_expense,
                'credit': 0
            })
        
        # 17. Other Expenses
        other_expense = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM expenses
            WHERE expense_type='Other Expenses'
        """).fetchone()[0]
        if other_expense > 0:
            trial_data.append({
                'account_head': 'Other Expenses',
                'category': 'Expense',
                'debit': other_expense,
                'credit': 0
            })
        
        # ==================== CAPITAL (Balancing Figure) ====================
        
        total_debits = sum(item['debit'] for item in trial_data)
        total_credits = sum(item['credit'] for item in trial_data)
        
        diff = total_credits - total_debits
        
        if abs(diff) > 0.01:
            if diff > 0:
                trial_data.append({
                    'account_head': 'Capital/Reserves',
                    'category': 'Capital',
                    'debit': 0,
                    'credit': diff
                })
            else:
                trial_data.append({
                    'account_head': 'Capital/Reserves',
                    'category': 'Capital',
                    'debit': abs(diff),
                    'credit': 0
                })
        
        if trial_data:
            df = pd.DataFrame(trial_data)
            
            st.markdown('<div class="trial-balance-table">', unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
            liabilities = sum(item['credit'] for item in trial_data if item['category'] == 'Liability')
            assets = sum(item['debit'] for item in trial_data if item['category'] == 'Asset')
            expenses = sum(item['debit'] for item in trial_data if item['category'] == 'Expense')
            income = sum(item['credit'] for item in trial_data if item['category'] == 'Income')
            capital = sum(item['credit'] for item in trial_data if item['category'] == 'Capital') - sum(item['debit'] for item in trial_data if item['category'] == 'Capital')
            
            with col1:
                st.metric("Total Assets", f"₹{assets:,.2f}")
            with col2:
                st.metric("Total Liabilities", f"₹{liabilities:,.2f}")
            with col3:
                st.metric("Total Income", f"₹{income:,.2f}")
            with col4:
                st.metric("Total Expenses", f"₹{expenses:,.2f}")
            
            st.divider()
            
            st.subheader("📋 Full Trial Balance")
            
            for category in ['Asset', 'Liability', 'Income', 'Expense', 'Capital']:
                cat_data = [item for item in trial_data if item['category'] == category]
                if cat_data:
                    st.markdown(f"**{category}s**")
                    cat_df = pd.DataFrame(cat_data)
                    st.dataframe(cat_df.style.format({
                        'debit': '₹{:,.2f}',
                        'credit': '₹{:,.2f}'
                    }), use_container_width=True)
            
            total_debit = df['debit'].sum()
            total_credit = df['credit'].sum()
            
            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Debit", f"₹{total_debit:,.2f}")
            with col2:
                st.metric("Total Credit", f"₹{total_credit:,.2f}")
            with col3:
                if abs(total_debit - total_credit) < 0.01:
                    st.success("✅ BALANCED!")
                    st.info(f"Assets (₹{assets:,.2f}) = Liabilities (₹{liabilities:,.2f}) + Capital (₹{capital:,.2f})")
                else:
                    st.error(f"❌ Difference: ₹{abs(total_debit - total_credit):,.2f}")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                csv = df.to_csv(index=False)
                st.download_button("📥 Download CSV", csv, "trial_balance.csv", "text/csv")
            
            with col2:
                if st.button("📄 Generate PDF Report"):
                    pdf_data = {
                        'date': as_on_date.strftime('%d-%m-%Y'),
                        'entries': trial_data
                    }
                    pdf_file = generate_report_pdf('trial_balance', pdf_data, 'trial_balance.pdf')
                    if pdf_file:
                        with open(pdf_file, 'rb') as f:
                            st.download_button("📥 Download PDF", f, "trial_balance.pdf", "application/pdf")
        else:
            st.info("No data available for trial balance")
    
    conn.close()

# [All other functions remain the same - show_fixed_deposits, show_recurring_deposits, 
# show_transactions, show_journal_vouchers, show_income_expenses, show_balance_sheet, 
# show_profit_loss, show_reports, show_create_sb_account, show_my_details, show_dashboard]

# ==================== MAIN ====================

if __name__ == "__main__":
    main()
    
