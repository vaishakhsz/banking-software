# 🏦 AASHA NIDHI PVT LIMITED BANK - BALARAMAPURAM
# Complete Banking System with Drill-Down & Enhanced UI

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import uuid
import os
import hashlib
import tempfile

try:
    from fpdf import FPDF
except ImportError:
    try:
        from fpdf2 import FPDF
    except ImportError:
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
    
    # Customers table
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
    
    # Fixed Deposits table
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
    
    # Recurring Deposits table
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
    
    # Transactions table
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
    
    # Journal Vouchers table
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
        customer_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users (id),
        FOREIGN KEY (customer_id) REFERENCES customers (id)
    )''')
    
    # Journal Entries table
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
    
    # Interest Calculations table
    c.execute('''CREATE TABLE IF NOT EXISTS interest_calculations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL,
        calculation_date DATE NOT NULL,
        principal_amount DECIMAL(15,2) NOT NULL,
        interest_rate DECIMAL(5,2) NOT NULL,
        interest_earned DECIMAL(15,2) NOT NULL,
        days_calculated INTEGER NOT NULL,
        customer_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (account_id) REFERENCES accounts (id),
        FOREIGN KEY (customer_id) REFERENCES customers (id)
    )''')
    
    # Expenses table
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expense_id TEXT UNIQUE NOT NULL,
        expense_type TEXT NOT NULL,
        amount DECIMAL(15,2) NOT NULL,
        description TEXT,
        date DATE NOT NULL,
        customer_id INTEGER,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users (id),
        FOREIGN KEY (customer_id) REFERENCES customers (id)
    )''')
    
    # Income table
    c.execute('''CREATE TABLE IF NOT EXISTS income (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        income_id TEXT UNIQUE NOT NULL,
        income_type TEXT NOT NULL,
        amount DECIMAL(15,2) NOT NULL,
        description TEXT,
        date DATE NOT NULL,
        customer_id INTEGER,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users (id),
        FOREIGN KEY (customer_id) REFERENCES customers (id)
    )''')
    
    conn.commit()
    conn.close()

# ==================== UTILITY FUNCTIONS ====================
def get_db():
    return sqlite3.connect('banking_system.db')

def generate_id(prefix):
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4]}"

def generate_account_number(account_type):
    prefix = '100' if account_type == 'SB' else '200' if account_type == 'FD' else '300'
    return f"{prefix}{datetime.now().strftime('%y%m%d')}{str(uuid.uuid4().int)[:6]}"

def generate_voucher_number(voucher_type):
    prefix = 'PMT' if voucher_type == 'PAYMENT' else 'RCT' if voucher_type == 'RECEIPT' else 'JNL'
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M')}{str(uuid.uuid4().int)[:4]}"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_user(username, password):
    c = get_db()
    cur = c.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=? AND is_active=1", 
                (username, hash_password(password)))
    user = cur.fetchone()
    c.close()
    return user

def create_default_admin():
    c = get_db()
    if c.execute("SELECT COUNT(*) FROM users WHERE username='admin'").fetchone()[0] == 0:
        c.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)", 
                  ('admin', hash_password('admin123'), 'admin'))
        c.commit()
    c.close()

def calculate_fd_maturity(principal, rate, months):
    return round(principal * (1 + rate/400) ** (months/3), 2)

def calculate_rd_maturity(monthly, rate, months):
    return round(monthly * (((1 + rate/400) ** (months/3) - 1) / (1 - (1 + rate/400) ** (-1/3))), 2)

def calculate_sb_interest(balance, rate, days):
    return 0 if balance <= 0 else round((balance * rate * days) / (100 * 365), 2)

def get_minimum_balance(c, account_id, from_date, to_date):
    try:
        sb = c.execute("""
            SELECT balance_after FROM transactions 
            WHERE account_id=? AND DATE(created_at)<? 
            ORDER BY created_at DESC LIMIT 1
        """, (account_id, from_date)).fetchone()
        
        sb = sb[0] if sb else (c.execute("SELECT balance FROM accounts WHERE id=?", (account_id,)).fetchone() or [0])[0]
        
        txns = c.execute("""
            SELECT balance_after FROM transactions 
            WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ? 
            ORDER BY created_at
        """, (account_id, from_date, to_date)).fetchall()
        
        return min([sb] + [t[0] for t in txns]) if txns else sb
    except:
        return (c.execute("SELECT balance FROM accounts WHERE id=?", (account_id,)).fetchone() or [0])[0]

# ==================== CUSTOMER SELECTOR WITH DRILL-DOWN ====================
def customer_selector(label="👤 Select Customer", key_prefix="cust", include_kyc_filter=False):
    """
    Returns: (customer_id, customer_name, account_id, account_number, account_balance)
    """
    c = get_db()
    
    # Get customers with their SB accounts
    query = """
        SELECT 
            c.id,
            c.customer_id,
            c.first_name || ' ' || c.last_name as full_name,
            c.kyc_status,
            a.id as account_id,
            a.account_number,
            a.balance,
            COALESCE(a.total_interest_earned, 0) as interest
        FROM customers c
        LEFT JOIN accounts a ON c.id = a.customer_id AND a.account_type = 'SB' AND a.status = 'ACTIVE'
        ORDER BY c.first_name
    """
    
    customers = c.execute(query).fetchall()
    c.close()
    
    if not customers:
        st.warning("⚠️ No customers found!")
        return None, None, None, None, None
    
    # Create display options
    options = []
    for cust in customers:
        if cust[4] is None:  # No SB account
            display = f"❌ {cust[2]} | {cust[1]} | No SB Account | KYC: {cust[3]}"
            options.append({
                'display': display,
                'customer_id': cust[0],
                'customer_name': cust[2],
                'account_id': None,
                'account_number': None,
                'balance': 0,
                'interest': 0,
                'total_balance': 0,
                'has_account': False
            })
        else:
            total_balance = cust[6] + cust[7]
            kyc_emoji = "✅" if cust[3] == 'VERIFIED' else "⏳"
            display = f"{kyc_emoji} {cust[2]} | A/c: {cust[5]} | Bal: Rs{total_balance:,.2f} | KYC: {cust[3]}"
            options.append({
                'display': display,
                'customer_id': cust[0],
                'customer_name': cust[2],
                'account_id': cust[4],
                'account_number': cust[5],
                'balance': cust[6],
                'interest': cust[7],
                'total_balance': total_balance,
                'has_account': True
            })
    
    # Show selector
    selected = st.selectbox(
        label,
        options,
        format_func=lambda x: x['display'],
        key=f"{key_prefix}_selector"
    )
    
    if selected and selected['has_account']:
        return (
            selected['customer_id'],
            selected['customer_name'],
            selected['account_id'],
            selected['account_number'],
            selected['total_balance']
        )
    elif selected and not selected['has_account']:
        st.warning(f"⚠️ {selected['customer_name']} doesn't have an SB account yet!")
        return selected['customer_id'], selected['customer_name'], None, None, 0
    
    return None, None, None, None, None

# ==================== CSS WITH ENHANCED UI ====================
def load_enterprise_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        
        * {
            font-family: 'Plus Jakarta Sans', sans-serif;
        }
        
        .main-header {
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            color: white;
            padding: 1.5rem 2rem;
            border-radius: 16px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }
        
        .main-header h1 {
            margin: 0;
            font-size: 2rem;
            font-weight: 800;
        }
        
        .main-header small {
            opacity: 0.8;
            font-size: 1rem;
        }
        
        .metric-card {
            background: white;
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
            border-left: 4px solid #2c5364;
            transition: transform 0.2s;
        }
        
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
        }
        
        .section-card {
            background: white;
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        }
        
        .stButton > button {
            border-radius: 10px !important;
            font-weight: 700 !important;
            transition: all 0.3s ease !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.15) !important;
        }
        
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #0f2027, #2c5364) !important;
            color: white !important;
        }
        
        .stButton > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #1a3340, #3a6b80) !important;
        }
        
        .success-box {
            background: #d4edda;
            border: 2px solid #28a745;
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        .info-box {
            background: #d1ecf1;
            border: 2px solid #17a2b8;
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        .warning-box {
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        .balance-sheet {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border-radius: 16px;
            padding: 2rem;
            margin: 1rem 0;
        }
        
        .balance-sheet h3 {
            color: #0f2027;
            font-weight: 700;
        }
        
        .drill-down-item {
            background: white;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            margin: 0.25rem 0;
            border-left: 3px solid #2c5364;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .drill-down-item:hover {
            background: #f0f4f8;
            transform: translateX(5px);
        }
        
        [data-testid="stSidebar"] {
            background: #0f2027 !important;
        }
        
        [data-testid="stSidebar"] .stButton > button {
            color: white !important;
            background: transparent !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
        }
        
        [data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(255,255,255,0.1) !important;
            border-color: rgba(255,255,255,0.3) !important;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 8px 16px;
            background: #f0f2f6;
            font-weight: 600;
        }
        
        .stTabs [aria-selected="true"] {
            background: #0f2027 !important;
            color: white !important;
        }
        
        .stSelectbox > div > div {
            border-radius: 10px !important;
        }
        
        .stNumberInput > div > div > input {
            border-radius: 10px !important;
        }
        
        .stDateInput > div > div > input {
            border-radius: 10px !important;
        }
        
        .stTextInput > div > div > input {
            border-radius: 10px !important;
        }
        
        .stTextArea > div > div > textarea {
            border-radius: 10px !important;
        }
        
        .stAlert {
            border-radius: 12px !important;
        }
        
        .stDataFrame {
            border-radius: 12px !important;
            overflow: hidden !important;
        }
        
        .stMetric {
            background: white;
            padding: 1rem;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        .stMetric .css-1xarl3l {
            font-size: 1.5rem !important;
        }
        
        .stExpander {
            border-radius: 12px !important;
            border: 1px solid #e9ecef !important;
        }
        
        .stExpander > details > summary {
            font-weight: 600 !important;
            padding: 0.5rem 1rem !important;
        }
        
        .emoji-icon {
            font-size: 1.2rem;
            margin-right: 0.5rem;
        }
        
        .footer {
            text-align: center;
            padding: 2rem 0;
            color: #6c757d;
            font-size: 0.9rem;
            border-top: 1px solid #dee2e6;
            margin-top: 2rem;
        }
        
        @media (max-width: 768px) {
            .main-header h1 {
                font-size: 1.5rem;
            }
        }
    </style>
    """, unsafe_allow_html=True)

# ==================== SESSION STATE ====================
def init_session_state():
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = 'dashboard'
    if 'selected_customer' not in st.session_state:
        st.session_state.selected_customer = None

# ==================== MAIN APP ====================
def main():
    st.set_page_config(
        page_title="🏦 Aasha Nidhi Bank - Complete Banking System",
        page_icon="🏦",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    init_database()
    create_default_admin()
    init_session_state()
    load_enterprise_css()
    
    if st.session_state.user is None:
        show_login()
    else:
        show_app()

def show_login():
    st.markdown("""
    <div style="display:flex;justify-content:center;align-items:center;min-height:80vh">
        <div style="background:white;padding:3rem;border-radius:24px;text-align:center;max-width:400px;box-shadow:0 20px 60px rgba(0,0,0,0.1)">
            <h1 style="font-size:2.5rem;margin-bottom:0">🏦</h1>
            <h1 style="font-size:1.8rem;font-weight:800;margin:0.5rem 0">AASHA NIDHI BANK</h1>
            <p style="color:#6c757d;margin-bottom:2rem">Balaramapuram</p>
    """, unsafe_allow_html=True)
    
    username = st.text_input("👤 Username", placeholder="Enter your username")
    password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🚀 Sign In", use_container_width=True, type="primary"):
            user = login_user(username, password)
            if user:
                st.session_state.user = {
                    'id': user[0],
                    'username': user[1],
                    'role': user[3]
                }
                st.rerun()
            else:
                st.error("❌ Invalid credentials! Please try again.")
        
        st.markdown("""
        <div style="margin-top:1rem;padding:1rem;background:#f8f9fa;border-radius:12px">
            <small style="color:#6c757d">
                🔑 Demo: <strong>admin</strong> / <strong>admin123</strong>
            </small>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div></div>", unsafe_allow_html=True)

def show_app():
    # Header
    st.markdown(f"""
    <div class="main-header">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap">
            <div>
                <h1>🏦 AASHA NIDHI PVT LIMITED BANK</h1>
                <small>📍 BALARAMAPURAM • {datetime.now().strftime('%d-%m-%Y %I:%M %p')}</small>
            </div>
            <div style="text-align:right">
                <span style="font-size:1.2rem;font-weight:600">👤 {st.session_state.user['username']}</span>
                <br>
                <span style="background:rgba(255,255,255,0.2);padding:0.25rem 1rem;border-radius:20px;font-size:0.9rem">
                    {st.session_state.user['role'].upper()}
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🏦 Navigation")
        st.markdown("---")
        
        # Menu items with emojis
        menu_items = {
            'dashboard': '📊 Dashboard',
            'customer_management': '👥 Customers',
            'kyc_verification': '✅ KYC Verification',
            'create_sb_account': '💰 Open SB Account',
            'sb_accounts': '🏦 SB Accounts',
            'fixed_deposits': '📈 Fixed Deposits',
            'recurring_deposits': '🔄 Recurring Dep.',
            'transactions': '💳 Transactions',
            'journal_vouchers': '📝 Journal Vouchers',
            'income_expenses': '💰 Income & Exp.',
            'interest_calculation': '📊 Interest',
            'trial_balance': '⚖️ Trial Balance',
            'balance_sheet': '📋 Balance Sheet',
            'profit_loss': '📈 Profit & Loss',
            'reports': '📄 Reports'
        }
        
        # Show menu based on role
        if st.session_state.user['role'] in ['admin', 'staff']:
            for key, label in menu_items.items():
                if st.button(label, key=f"m_{key}", use_container_width=True):
                    st.session_state.page = key
                    st.rerun()
        else:
            if st.button("📊 Dashboard", key="m_dashboard", use_container_width=True):
                st.session_state.page = 'dashboard'
                st.rerun()
            if st.button("💰 My Accounts", key="m_my_accounts", use_container_width=True):
                st.session_state.page = 'my_accounts'
                st.rerun()
            if st.button("💳 Transactions", key="m_my_transactions", use_container_width=True):
                st.session_state.page = 'my_transactions'
                st.rerun()
        
        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.user = None
            st.rerun()
        
        st.markdown("""
        <div style="position:fixed;bottom:1rem;left:1rem;right:1rem;text-align:center;color:#6c757d;font-size:0.8rem">
            © 2024 Aasha Nidhi Bank<br>
            v2.0
        </div>
        """, unsafe_allow_html=True)
    
    # Page routing
    page = st.session_state.get('page', 'dashboard')
    
    if page == 'dashboard':
        dashboard()
    elif page == 'customer_management':
        customer_management()
    elif page == 'kyc_verification':
        kyc_verification()
    elif page == 'create_sb_account':
        create_sb_account()
    elif page == 'sb_accounts':
        sb_accounts()
    elif page == 'fixed_deposits':
        fixed_deposits()
    elif page == 'recurring_deposits':
        recurring_deposits()
    elif page == 'transactions':
        transactions()
    elif page == 'journal_vouchers':
        journal_vouchers()
    elif page == 'income_expenses':
        income_expenses()
    elif page == 'interest_calculation':
        interest_calculation()
    elif page == 'trial_balance':
        trial_balance()
    elif page == 'balance_sheet':
        balance_sheet()
    elif page == 'profit_loss':
        profit_loss()
    elif page == 'reports':
        reports()
    elif page == 'my_accounts':
        my_accounts()
    elif page == 'my_transactions':
        my_transactions()
    else:
        st.error(f"❌ Page '{page}' not found")

# ==================== DASHBOARD ====================
def dashboard():
    c = get_db()
    
    # Metrics
    total_customers = c.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    total_sb_accounts = c.execute("SELECT COUNT(*) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
    total_sb_balance = c.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
    total_interest = c.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
    total_fd = c.execute("SELECT COALESCE(SUM(principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
    total_rd = c.execute("SELECT COALESCE(SUM(monthly_amount*installments_paid),0) FROM recurring_deposits WHERE status='ACTIVE'").fetchone()[0]
    pending_kyc = c.execute("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'").fetchone()[0]
    
    c.close()
    
    # Display metrics
    st.markdown("### 📊 Bank Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Total Customers", f"{total_customers:,}")
        st.metric("✅ KYC Verified", f"{total_customers - pending_kyc:,}")
    
    with col2:
        st.metric("🏦 SB Accounts", f"{total_sb_accounts:,}")
        st.metric("💰 SB Deposits", f"Rs {total_sb_balance:,.2f}")
    
    with col3:
        st.metric("📈 FD Deposits", f"Rs {total_fd:,.2f}")
        st.metric("🔄 RD Deposits", f"Rs {total_rd:,.2f}")
    
    with col4:
        st.metric("💹 Interest Earned", f"Rs {total_interest:,.2f}")
        st.metric("⏳ Pending KYC", f"{pending_kyc:,}")
    
    # Recent Activity
    st.markdown("### 🕐 Recent Activity")
    c = get_db()
    recent_txns = c.execute("""
        SELECT t.transaction_id, COALESCE(c.first_name||' '||c.last_name,'System'), 
               t.transaction_type, t.amount, t.created_at
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id=a.id
        LEFT JOIN customers c ON a.customer_id=c.id
        ORDER BY t.created_at DESC LIMIT 10
    """).fetchall()
    c.close()
    
    if recent_txns:
        df = pd.DataFrame(recent_txns, columns=['Txn ID', 'Customer', 'Type', 'Amount', 'Time'])
        st.dataframe(df.style.format({'Amount': 'Rs {:,.2f}'}), use_container_width=True)
    else:
        st.info("No recent transactions")

# ==================== CUSTOMER MANAGEMENT ====================
def customer_management():
    tab1, tab2 = st.tabs(["📝 Register Customer", "👥 View Customers"])
    
    with tab1:
        st.markdown("### 📝 Register New Customer")
        with st.form("register_customer"):
            col1, col2 = st.columns(2)
            
            with col1:
                first_name = st.text_input("👤 First Name*", placeholder="Enter first name")
                last_name = st.text_input("👤 Last Name*", placeholder="Enter last name")
                dob = st.date_input("🎂 Date of Birth*", min_value=date(1900, 1, 1), max_value=date.today())
                email = st.text_input("📧 Email*", placeholder="customer@email.com")
                phone = st.text_input("📱 Phone*", placeholder="9876543210")
                gender = st.selectbox("⚥ Gender", ["Male", "Female", "Other"])
            
            with col2:
                pan = st.text_input("🪪 PAN Number*", placeholder="ABCDE1234F")
                aadhar = st.text_input("🆔 Aadhar Number*", placeholder="1234 5678 9012")
                address = st.text_area("🏠 Address", placeholder="Street, City, State, Pincode")
                city = st.text_input("🏙️ City", placeholder="City")
                state = st.text_input("🏛️ State", placeholder="State")
                pincode = st.text_input("📮 Pincode", placeholder="695001")
            
            st.markdown("### 📎 Documents Upload")
            col1, col2 = st.columns(2)
            with col1:
                pan_doc = st.file_uploader("🪪 PAN Document*", type=['jpg', 'jpeg', 'png', 'pdf'])
                photo = st.file_uploader("📸 Photo", type=['jpg', 'jpeg', 'png'])
            with col2:
                aadhar_doc = st.file_uploader("🆔 Aadhar Document*", type=['jpg', 'jpeg', 'png', 'pdf'])
                signature = st.file_uploader("✍️ Signature", type=['jpg', 'jpeg', 'png'])
            
            if st.form_submit_button("✅ Register Customer", use_container_width=True, type="primary"):
                if all([first_name, last_name, email, phone, pan, aadhar]) and pan_doc and aadhar_doc:
                    conn = get_db()
                    try:
                        conn.execute("""
                            INSERT INTO customers (
                                customer_id, first_name, last_name, date_of_birth, gender,
                                email, phone, address, city, state, pincode,
                                pan_number, aadhar_number, pan_document, aadhar_document,
                                photo, signature, kyc_status
                            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """, (
                            generate_id('CUST'), first_name, last_name, dob, gender,
                            email, phone, address, city, state, pincode,
                            pan, aadhar, pan_doc.read(), aadhar_doc.read(),
                            photo.read() if photo else None,
                            signature.read() if signature else None,
                            'PENDING'
                        ))
                        conn.commit()
                        conn.close()
                        st.success("✅ Customer registered successfully! 🎉")
                        st.balloons()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                else:
                    st.error("❌ Please fill all required fields (*)")
    
    with tab2:
        st.markdown("### 👥 Customer List")
        conn = get_db()
        customers = conn.execute("""
            SELECT customer_id, first_name, last_name, email, phone, kyc_status, 
                   CASE WHEN kyc_status='VERIFIED' THEN '✅' WHEN kyc_status='PENDING' THEN '⏳' ELSE '❌' END as status_emoji
            FROM customers ORDER BY created_at DESC
        """).fetchall()
        conn.close()
        
        if customers:
            df = pd.DataFrame(customers, columns=['ID', 'First', 'Last', 'Email', 'Phone', 'KYC', 'Status'])
            st.dataframe(df[['ID', 'First', 'Last', 'Email', 'Phone', 'Status', 'KYC']], use_container_width=True)
            
            # Export button
            st.download_button(
                "📥 Export to CSV",
                df.to_csv(index=False),
                "customers.csv",
                "text/csv"
            )
        else:
            st.info("No customers registered yet")

# ==================== KYC VERIFICATION ====================
def kyc_verification():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    pending = c.execute("SELECT * FROM customers WHERE kyc_status='PENDING'").fetchall()
    
    if not pending:
        st.success("✅ All customers are KYC verified! 🎉")
        c.close()
        return
    
    st.markdown(f"### ✅ KYC Verification ({len(pending)} pending)")
    
    for cust in pending:
        with st.expander(f"{'⏳' if cust[12]=='PENDING' else '✅'} {cust[3]} {cust[4]} (ID: {cust[2]})"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                **📋 Customer Details:**
                - 👤 Name: {cust[3]} {cust[4]}
                - 📧 Email: {cust[7]}
                - 📱 Phone: {cust[8]}
                - 📅 DOB: {cust[5]}
                - ⚥ Gender: {cust[6]}
                - 🪪 PAN: {cust[10]}
                - 🆔 Aadhar: {cust[11]}
                - 🏠 Address: {cust[9] or 'N/A'}
                """)
            
            with col2:
                st.markdown("**📎 Documents:**")
                if cust[14]:  # PAN document
                    st.success("✅ PAN Document Uploaded")
                if cust[15]:  # Aadhar document
                    st.success("✅ Aadhar Document Uploaded")
                if cust[16]:  # Photo
                    st.success("✅ Photo Uploaded")
                if cust[17]:  # Signature
                    st.success("✅ Signature Uploaded")
            
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("✅ Approve KYC", key=f"approve_{cust[0]}", use_container_width=True):
                    c.execute("""
                        UPDATE customers 
                        SET kyc_status='VERIFIED', 
                            kyc_verified_by=?, 
                            kyc_verified_at=CURRENT_TIMESTAMP 
                        WHERE id=?
                    """, (st.session_state.user['id'], cust[0]))
                    c.commit()
                    st.success(f"✅ KYC Approved for {cust[3]} {cust[4]}!")
                    st.rerun()
            
            with col2:
                if st.button("❌ Reject KYC", key=f"reject_{cust[0]}", use_container_width=True):
                    c.execute("UPDATE customers SET kyc_status='REJECTED' WHERE id=?", (cust[0],))
                    c.commit()
                    st.warning(f"❌ KYC Rejected for {cust[3]} {cust[4]}")
                    st.rerun()
            
            with col3:
                if st.button("⏳ Hold", key=f"hold_{cust[0]}", use_container_width=True):
                    st.info("KYC put on hold")
    
    c.close()

# ==================== CREATE SB ACCOUNT ====================
def create_sb_account():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    
    # Get customers without SB account (KYC not required)
    customers = c.execute("""
        SELECT c.id, c.customer_id, c.first_name||' '||c.last_name as name, c.kyc_status
        FROM customers c
        WHERE NOT EXISTS (
            SELECT 1 FROM accounts a 
            WHERE a.customer_id = c.id AND a.account_type='SB' AND a.status='ACTIVE'
        )
        ORDER BY c.first_name
    """).fetchall()
    
    if not customers:
        st.success("🎉 All customers already have SB accounts!")
        c.close()
        return
    
    st.markdown("### 💰 Open SB Account")
    
    # Customer selection with KYC status
    options = []
    for cust in customers:
        kyc_emoji = "✅" if cust[3] == 'VERIFIED' else "⏳"
        options.append(f"{kyc_emoji} {cust[2]} | {cust[1]} | KYC: {cust[3]}")
    
    selected = st.selectbox("👤 Select Customer", options)
    
    if selected:
        idx = options.index(selected)
        cust = customers[idx]
        
        with st.form("open_sb"):
            col1, col2 = st.columns(2)
            
            with col1:
                interest_rate = st.number_input(
                    "📈 Interest Rate (%)",
                    min_value=0.0,
                    max_value=10.0,
                    value=3.5,
                    step=0.25,
                    help="Annual interest rate for SB account"
                )
                opening_balance = st.number_input(
                    "💰 Opening Balance (Rs)",
                    min_value=0.0,
                    step=100.0,
                    value=500.0,
                    help="Minimum opening balance"
                )
            
            with col2:
                mode = st.selectbox(
                    "💳 Funding Mode",
                    ["CASH", "BANK TRANSFER", "CHEQUE", "ONLINE"]
                )
                nominee = st.text_input("👤 Nominee Name (Optional)")
            
            # KYC warning
            if cust[3] != 'VERIFIED':
                st.warning("⚠️ Customer KYC is pending. Account can still be opened but KYC verification is recommended.")
            
            if st.form_submit_button("✅ Create SB Account", use_container_width=True, type="primary"):
                account_number = generate_account_number('SB')
                
                conn = get_db()
                try:
                    # Create account
                    conn.execute("""
                        INSERT INTO accounts (
                            account_number, customer_id, account_type, 
                            balance, interest_rate, last_interest_calculation,
                            total_interest_earned
                        ) VALUES (?,?,?,?,?,DATE('now'),0.00)
                    """, (account_number, cust[0], 'SB', opening_balance, interest_rate))
                    
                    account_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    
                    # Create transaction
                    if opening_balance > 0:
                        conn.execute("""
                            INSERT INTO transactions (
                                transaction_id, account_id, transaction_type,
                                amount, balance_after, description,
                                reference_type, voucher_type, voucher_number,
                                created_by
                            ) VALUES (?,?,?,?,?,?,?,?,?,?)
                        """, (
                            generate_id('TXN'), account_id, 'CREDIT',
                            opening_balance, opening_balance,
                            f"SB Account Opening: {account_number}",
                            mode, 'RECEIPT', generate_voucher_number('RECEIPT'),
                            st.session_state.user['id']
                        ))
                    
                    conn.commit()
                    conn.close()
                    
                    st.success(f"""
                    ✅ SB Account Created Successfully! 🎉
                    
                    📋 **Account Details:**
                    - Account Number: **{account_number}**
                    - Customer: **{cust[2]}**
                    - Opening Balance: **Rs {opening_balance:,.2f}**
                    - Interest Rate: **{interest_rate}%**
                    """)
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    c.close()

# ==================== SB ACCOUNTS ====================
def sb_accounts():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    tab1, tab2, tab3 = st.tabs(["💳 Transact", "📊 Accounts", "📋 Statement"])
    
    with tab1:
        st.markdown("### 💳 Deposit/Withdraw")
        
        # Customer selector with drill-down
        cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
            "👤 Select Customer Account",
            "txn_customer"
        )
        
        if cust_id and acc_id:
            st.success(f"""
            ✅ **Selected Account:**
            - Customer: **{cust_name}**
            - Account: **{acc_number}**
            - Balance: **Rs {balance:,.2f}**
            """)
            
            with st.form("transaction_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    transaction_type = st.radio(
                        "📊 Transaction Type",
                        ["💰 Deposit", "💳 Withdraw"],
                        horizontal=True
                    )
                
                with col2:
                    amount = st.number_input(
                        "💵 Amount (Rs)",
                        min_value=1.0,
                        step=100.0
                    )
                
                mode = st.selectbox(
                    "💳 Payment Mode",
                    ["CASH", "BANK TRANSFER", "CHEQUE", "ONLINE"]
                )
                description = st.text_input("📝 Description", placeholder="Transaction details")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("✅ Process Transaction", use_container_width=True, type="primary"):
                        if transaction_type == "💳 Withdraw" and amount > balance:
                            st.error("❌ Insufficient balance!")
                        else:
                            conn = get_db()
                            try:
                                txn_type = "DEBIT" if transaction_type == "💳 Withdraw" else "CREDIT"
                                new_balance = balance - amount if txn_type == "DEBIT" else balance + amount
                                voucher_type = "PAYMENT" if txn_type == "DEBIT" else "RECEIPT"
                                
                                conn.execute("""
                                    INSERT INTO transactions (
                                        transaction_id, account_id, transaction_type,
                                        amount, balance_after, description,
                                        reference_type, voucher_type, voucher_number,
                                        created_by
                                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                                """, (
                                    generate_id('TXN'), acc_id, txn_type,
                                    amount, new_balance, description or f"{transaction_type}",
                                    mode, voucher_type, generate_voucher_number(voucher_type),
                                    st.session_state.user['id']
                                ))
                                
                                conn.execute("UPDATE accounts SET balance=? WHERE id=?", (new_balance, acc_id))
                                conn.commit()
                                conn.close()
                                
                                st.success(f"""
                                ✅ Transaction Successful! 🎉
                                
                                📋 **Details:**
                                - Type: **{transaction_type}**
                                - Amount: **Rs {amount:,.2f}**
                                - New Balance: **Rs {new_balance:,.2f}**
                                """)
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
                
                with col2:
                    if st.form_submit_button("❌ Cancel", use_container_width=True):
                        st.info("Transaction cancelled")
    
    with tab2:
        st.markdown("### 📊 Active SB Accounts")
        accounts = c.execute("""
            SELECT a.account_number, c.first_name||' '||c.last_name as customer,
                   a.balance, COALESCE(a.total_interest_earned,0) as interest,
                   a.interest_rate, a.status, c.kyc_status
            FROM accounts a
            JOIN customers c ON a.customer_id = c.id
            WHERE a.account_type='SB'
            ORDER BY a.created_at DESC
        """).fetchall()
        
        if accounts:
            df = pd.DataFrame(accounts, columns=['Account', 'Customer', 'Balance', 'Interest', 'Rate', 'Status', 'KYC'])
            st.dataframe(
                df.style.format({
                    'Balance': 'Rs {:,.2f}',
                    'Interest': 'Rs {:,.2f}',
                    'Rate': '{:.2f}%'
                }),
                use_container_width=True
            )
            
            # Summary
            total_balance = df['Balance'].sum()
            total_interest = df['Interest'].sum()
            st.info(f"💰 Total SB Deposits: Rs {total_balance:,.2f} | Total Interest: Rs {total_interest:,.2f}")
        else:
            st.info("No SB accounts found")
    
    with tab3:
        st.markdown("### 📋 Account Statement")
        
        cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
            "👤 Select Customer for Statement",
            "stmt_customer"
        )
        
        if cust_id and acc_id:
            col1, col2 = st.columns(2)
            with col1:
                from_date = st.date_input("📅 From Date", date.today() - timedelta(days=30))
            with col2:
                to_date = st.date_input("📅 To Date", date.today())
            
            if st.button("📊 Generate Statement", use_container_width=True):
                conn = get_db()
                transactions = conn.execute("""
                    SELECT transaction_id, transaction_type, amount,
                           balance_after, description, reference_type,
                           created_at
                    FROM transactions
                    WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ?
                    ORDER BY created_at DESC
                """, (acc_id, from_date, to_date)).fetchall()
                conn.close()
                
                if transactions:
                    df = pd.DataFrame(transactions, columns=['ID', 'Type', 'Amount', 'Balance', 'Description', 'Mode', 'Date'])
                    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%d-%m-%Y %I:%M %p')
                    
                    st.dataframe(
                        df.style.format({
                            'Amount': 'Rs {:,.2f}',
                            'Balance': 'Rs {:,.2f}'
                        }),
                        use_container_width=True
                    )
                    
                    # Summary
                    total_credit = df[df['Type'] == 'CREDIT']['Amount'].sum()
                    total_debit = df[df['Type'] == 'DEBIT']['Amount'].sum()
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Credits", f"Rs {total_credit:,.2f}")
                    col2.metric("Total Debits", f"Rs {total_debit:,.2f}")
                    col3.metric("Net Change", f"Rs {(total_credit - total_debit):,.2f}")
                    
                    st.download_button(
                        "📥 Download Statement",
                        df.to_csv(index=False),
                        f"statement_{acc_number}_{from_date}_{to_date}.csv",
                        "text/csv"
                    )
                else:
                    st.info("No transactions in this period")
    
    c.close()

# ==================== FIXED DEPOSITS WITH DRILL-DOWN ====================
# ==================== FIXED DEPOSITS WITH CLOSURE ====================
def fixed_deposits():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    tab1, tab2, tab3 = st.tabs(["📝 Open FD", "📊 Active FDs", "🔒 Close FD"])
    
    with tab1:
        st.markdown("### 📝 Open Fixed Deposit")
        
        # Customer selector with drill-down
        cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
            "👤 Select Customer for FD",
            "fd_customer"
        )
        
        if cust_id and acc_id:
            st.success(f"""
            ✅ **Selected Customer:**
            - 👤 Name: **{cust_name}**
            - 🏦 Account: **{acc_number}**
            - 💰 Balance: **Rs {balance:,.2f}**
            """)
            
            with st.form("fd_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    principal = st.number_input(
                        "💰 Principal Amount",
                        min_value=1000.0,
                        step=1000.0,
                        value=10000.0,
                        help="Minimum FD amount is Rs 1,000"
                    )
                    
                    tenure = st.selectbox(
                        "📅 Tenure (Months)",
                        [1, 3, 6, 9, 12, 18, 24, 36, 48, 60],
                        help="Select FD duration in months"
                    )
                
                with col2:
                    interest_rate = st.number_input(
                        "📈 Interest Rate (%)",
                        min_value=3.0,
                        max_value=10.0,
                        value=6.5,
                        step=0.25,
                        help="Annual interest rate"
                    )
                    
                    start_date = st.date_input(
                        "📆 Start Date",
                        date.today()
                    )
                
                maturity_date = start_date + relativedelta(months=tenure)
                maturity_amount = calculate_fd_maturity(principal, interest_rate, tenure)
                interest_earned = maturity_amount - principal
                
                st.info(f"""
                📊 **FD Summary:**
                - Maturity Date: **{maturity_date.strftime('%d-%m-%Y')}**
                - Maturity Amount: **Rs {maturity_amount:,.2f}**
                - Interest Earned: **Rs {interest_earned:,.2f}**
                """)
                
                # Funding options
                funding_mode = st.radio(
                    "💳 Funding Mode",
                    ["SB Transfer (Debit from SB)", "Cash", "Bank Transfer", "Cheque"],
                    horizontal=True
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    nominee_name = st.text_input("👤 Nominee Name (Optional)")
                with col2:
                    nominee_relation = st.text_input("🤝 Relationship (Optional)")
                
                # Check if sufficient balance for SB transfer
                if funding_mode == "SB Transfer (Debit from SB)" and principal > balance:
                    st.error(f"❌ Insufficient balance! Available: Rs {balance:,.2f}")
                
                if st.form_submit_button("✅ Open FD", use_container_width=True, type="primary"):
                    if funding_mode == "SB Transfer (Debit from SB)" and principal > balance:
                        st.error("❌ Insufficient balance!")
                    else:
                        conn = get_db()
                        try:
                            fd_number = generate_id('FD')
                            fd_account_number = generate_account_number('FD')
                            
                            # Create FD account
                            conn.execute("""
                                INSERT INTO accounts (
                                    account_number, customer_id, account_type,
                                    balance, interest_rate
                                ) VALUES (?,?,?,0.00,?)
                            """, (fd_account_number, cust_id, 'FD', interest_rate))
                            
                            fd_account_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                            
                            # Create FD record
                            conn.execute("""
                                INSERT INTO fixed_deposits (
                                    fd_number, account_id, principal_amount,
                                    interest_rate, start_date, maturity_date,
                                    maturity_amount, tenure_months, nominee_name,
                                    nominee_relation
                                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                            """, (
                                fd_number, fd_account_id, principal,
                                interest_rate, start_date, maturity_date,
                                maturity_amount, tenure, nominee_name,
                                nominee_relation
                            ))
                            
                            # Debit from SB account if transfer
                            if funding_mode == "SB Transfer (Debit from SB)":
                                new_balance = balance - principal
                                conn.execute("UPDATE accounts SET balance=? WHERE id=?", (new_balance, acc_id))
                                conn.execute("""
                                    INSERT INTO transactions (
                                        transaction_id, account_id, transaction_type,
                                        amount, balance_after, description,
                                        reference_type, voucher_type, voucher_number,
                                        created_by
                                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                                """, (
                                    generate_id('TXN'), acc_id, 'DEBIT',
                                    principal, new_balance,
                                    f"FD Transfer to {fd_number}",
                                    'SB_TRANSFER', 'PAYMENT',
                                    generate_voucher_number('PAYMENT'),
                                    st.session_state.user['id']
                                ))
                            
                            # Credit FD account
                            conn.execute("""
                                INSERT INTO transactions (
                                    transaction_id, account_id, transaction_type,
                                    amount, balance_after, description,
                                    reference_type, voucher_type, voucher_number,
                                    created_by
                                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                            """, (
                                generate_id('TXN'), fd_account_id, 'CREDIT',
                                principal, principal,
                                f"FD Opening: {fd_number}",
                                funding_mode, 'RECEIPT',
                                generate_voucher_number('RECEIPT'),
                                st.session_state.user['id']
                            ))
                            
                            conn.commit()
                            conn.close()
                            
                            st.success(f"""
                            ✅ FD Opened Successfully! 🎉
                            
                            📋 **FD Details:**
                            - FD Number: **{fd_number}**
                            - Amount: **Rs {principal:,.2f}**
                            - Rate: **{interest_rate}%**
                            - Maturity: **{maturity_date.strftime('%d-%m-%Y')}**
                            - Maturity Amount: **Rs {maturity_amount:,.2f}**
                            """)
                            st.balloons()
                            
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
    
    with tab2:
        st.markdown("### 📊 Active Fixed Deposits")
        fds = c.execute("""
            SELECT fd.id, fd.fd_number, c.id as customer_id,
                   c.first_name||' '||c.last_name as customer,
                   a.id as sb_account_id, a.account_number as sb_account,
                   fd.principal_amount, fd.interest_rate, 
                   fd.start_date, fd.maturity_date,
                   fd.maturity_amount, fd.status,
                   CASE 
                       WHEN date('now') > fd.maturity_date THEN '🔴 Matured'
                       ELSE '🟢 Active'
                   END as maturity_status,
                   julianday('now') - julianday(fd.start_date) as days_elapsed,
                   julianday(fd.maturity_date) - julianday(fd.start_date) as total_days
            FROM fixed_deposits fd
            JOIN accounts a ON fd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            WHERE fd.status='ACTIVE'
            ORDER BY fd.maturity_date
        """).fetchall()
        
        if fds:
            fd_data = []
            for fd in fds:
                fd_id, fd_number, cust_id, customer, sb_acc_id, sb_acc, principal, rate, start, maturity, maturity_amount, status, maturity_status, days_elapsed, total_days = fd
                
                # Calculate interest as of today
                if days_elapsed > 0 and total_days > 0:
                    # Simple interest calculation for elapsed period
                    accrued_interest = (principal * rate * days_elapsed) / (100 * 365)
                    # Cap at maturity interest
                    max_interest = maturity_amount - principal
                    accrued_interest = min(accrued_interest, max_interest)
                else:
                    accrued_interest = 0
                
                fd_data.append({
                    'ID': fd_id,
                    'FD No': fd_number,
                    'Customer': customer,
                    'SB Account': sb_acc,
                    'Principal': principal,
                    'Rate': rate,
                    'Start Date': start,
                    'Maturity Date': maturity,
                    'Maturity Amount': maturity_amount,
                    'Accrued Interest': accrued_interest,
                    'Total Value': principal + accrued_interest,
                    'Status': maturity_status,
                    'Days Elapsed': int(days_elapsed) if days_elapsed > 0 else 0
                })
            
            fd_df = pd.DataFrame(fd_data)
            st.dataframe(
                fd_df.style.format({
                    'Principal': 'Rs {:,.2f}',
                    'Rate': '{:.2f}%',
                    'Maturity Amount': 'Rs {:,.2f}',
                    'Accrued Interest': 'Rs {:,.2f}',
                    'Total Value': 'Rs {:,.2f}'
                }),
                use_container_width=True
            )
            
            total_fd = fd_df['Principal'].sum()
            total_interest = fd_df['Accrued Interest'].sum()
            total_value = fd_df['Total Value'].sum()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("💰 Total FD Investments", f"Rs {total_fd:,.2f}")
            col2.metric("📈 Accrued Interest", f"Rs {total_interest:,.2f}")
            col3.metric("💎 Total Value", f"Rs {total_value:,.2f}")
        else:
            st.info("No active fixed deposits")
    
    with tab3:
        st.markdown("### 🔒 Close/Withdraw Fixed Deposit")
        
        # Get active FDs for closure
        active_fds = c.execute("""
            SELECT fd.id, fd.fd_number, 
                   c.id as customer_id,
                   c.first_name||' '||c.last_name as customer,
                   a.id as sb_account_id, 
                   a.account_number as sb_account,
                   a.balance as sb_balance,
                   fd.principal_amount, fd.interest_rate, 
                   fd.start_date, fd.maturity_date,
                   fd.maturity_amount,
                   julianday('now') - julianday(fd.start_date) as days_elapsed,
                   julianday(fd.maturity_date) - julianday(fd.start_date) as total_days
            FROM fixed_deposits fd
            JOIN accounts a ON fd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            WHERE fd.status='ACTIVE'
            ORDER BY fd.maturity_date
        """).fetchall()
        
        if not active_fds:
            st.info("No active fixed deposits to close")
            c.close()
            return
        
        # Create selection options
        fd_options = []
        for fd in active_fds:
            fd_id, fd_number, cust_id, customer, sb_acc_id, sb_acc, sb_balance, principal, rate, start, maturity, maturity_amount, days_elapsed, total_days = fd
            
            # Calculate accrued interest
            if days_elapsed > 0 and total_days > 0:
                accrued_interest = (principal * rate * days_elapsed) / (100 * 365)
                max_interest = maturity_amount - principal
                accrued_interest = min(accrued_interest, max_interest)
            else:
                accrued_interest = 0
            
            total_value = principal + accrued_interest
            
            fd_options.append({
                'display': f"{fd_number} - {customer} | Principal: Rs{principal:,.2f} | Value: Rs{total_value:,.2f}",
                'fd_id': fd_id,
                'fd_number': fd_number,
                'customer_id': cust_id,
                'customer': customer,
                'sb_account_id': sb_acc_id,
                'sb_account': sb_acc,
                'sb_balance': sb_balance,
                'principal': principal,
                'rate': rate,
                'start_date': start,
                'maturity_date': maturity,
                'maturity_amount': maturity_amount,
                'accrued_interest': accrued_interest,
                'total_value': total_value,
                'days_elapsed': int(days_elapsed) if days_elapsed > 0 else 0,
                'total_days': int(total_days) if total_days > 0 else 0,
                'is_matured': datetime.strptime(maturity, '%Y-%m-%d').date() <= date.today()
            })
        
        selected_fd = st.selectbox(
            "📋 Select FD to Close",
            fd_options,
            format_func=lambda x: x['display']
        )
        
        if selected_fd:
            st.markdown("---")
            st.markdown(f"""
            ### 📋 FD Details
            
            | Field | Value |
            |-------|-------|
            | **FD Number** | {selected_fd['fd_number']} |
            | **Customer** | {selected_fd['customer']} |
            | **SB Account** | {selected_fd['sb_account']} |
            | **SB Balance** | Rs {selected_fd['sb_balance']:,.2f} |
            | **Principal** | Rs {selected_fd['principal']:,.2f} |
            | **Interest Rate** | {selected_fd['rate']}% |
            | **Start Date** | {selected_fd['start_date']} |
            | **Maturity Date** | {selected_fd['maturity_date']} |
            | **Maturity Amount** | Rs {selected_fd['maturity_amount']:,.2f} |
            | **Days Elapsed** | {selected_fd['days_elapsed']} days |
            | **Accrued Interest** | Rs {selected_fd['accrued_interest']:,.2f} |
            | **Total Value** | Rs {selected_fd['total_value']:,.2f} |
            """)
            
            # Check maturity status and set final amount
            if selected_fd['is_matured']:
                st.success("✅ This FD has matured and is eligible for closure with full interest!")
                final_amount = selected_fd['total_value']
                penalty_applied = False
            else:
                st.warning(f"""
                ⚠️ **Early Closure Warning:**
                - FD matures on: **{selected_fd['maturity_date']}**
                - Days remaining: **{selected_fd['total_days'] - selected_fd['days_elapsed']} days**
                - Early closure may result in reduced interest rate (penalty applies)
                """)
                
                # Early closure penalty
                penalty_rate = st.number_input(
                    "📉 Early Closure Penalty Rate (%)",
                    min_value=0.0,
                    max_value=5.0,
                    value=1.0,
                    step=0.25,
                    help="Penalty rate applied for early closure"
                )
                
                # Calculate penalty
                penalty_amount = (selected_fd['principal'] * penalty_rate * selected_fd['days_elapsed']) / (100 * 365)
                final_amount = selected_fd['total_value'] - penalty_amount
                penalty_applied = True
                
                st.info(f"""
                📊 **Early Closure Calculation:**
                - Accrued Interest: **Rs {selected_fd['accrued_interest']:,.2f}**
                - Penalty ({penalty_rate}%): **Rs {penalty_amount:,.2f}**
                - Final Payout: **Rs {final_amount:,.2f}**
                """)
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔒 Close FD & Transfer to SB", use_container_width=True, type="primary"):
                    conn = get_db()
                    try:
                        # Get FD account ID
                        fd_acc = conn.execute("""
                            SELECT account_id FROM fixed_deposits WHERE id=?
                        """, (selected_fd['fd_id'],)).fetchone()
                        
                        if not fd_acc:
                            st.error("❌ FD not found!")
                            conn.close()
                            return
                        
                        fd_account_id = fd_acc[0]
                        
                        # Update FD status
                        conn.execute("""
                            UPDATE fixed_deposits 
                            SET status='CLOSED' 
                            WHERE id=?
                        """, (selected_fd['fd_id'],))
                        
                        # Credit the amount to SB account
                        new_sb_balance = selected_fd['sb_balance'] + final_amount
                        conn.execute("""
                            UPDATE accounts 
                            SET balance=? 
                            WHERE id=?
                        """, (new_sb_balance, selected_fd['sb_account_id']))
                        
                        # Record transaction in SB account (CREDIT)
                        conn.execute("""
                            INSERT INTO transactions (
                                transaction_id, account_id, transaction_type,
                                amount, balance_after, description,
                                reference_type, voucher_type, voucher_number,
                                created_by
                            ) VALUES (?,?,?,?,?,?,?,?,?,?)
                        """, (
                            generate_id('TXN'), 
                            selected_fd['sb_account_id'], 
                            'CREDIT',
                            final_amount, 
                            new_sb_balance,
                            f"FD Closure: {selected_fd['fd_number']} (Interest: Rs{selected_fd['accrued_interest']:,.2f})",
                            'FD_CLOSURE', 
                            'RECEIPT',
                            generate_voucher_number('RECEIPT'),
                            st.session_state.user['id']
                        ))
                        
                        # Record transaction in FD account (DEBIT)
                        conn.execute("""
                            INSERT INTO transactions (
                                transaction_id, account_id, transaction_type,
                                amount, balance_after, description,
                                reference_type, voucher_type, voucher_number,
                                created_by
                            ) VALUES (?,?,?,?,?,?,?,?,?,?)
                        """, (
                            generate_id('TXN'), 
                            fd_account_id, 
                            'DEBIT',
                            final_amount, 
                            0,
                            f"FD Closure: {selected_fd['fd_number']}",
                            'FD_CLOSURE', 
                            'PAYMENT',
                            generate_voucher_number('PAYMENT'),
                            st.session_state.user['id']
                        ))
                        
                        # Record interest earned in income
                        if selected_fd['accrued_interest'] > 0:
                            conn.execute("""
                                INSERT INTO income (
                                    income_id, income_type, amount,
                                    description, date, customer_id,
                                    created_by
                                ) VALUES (?,?,?,?,?,?,?)
                            """, (
                                generate_id('INC'),
                                'Interest Earned',
                                selected_fd['accrued_interest'],
                                f"FD Interest: {selected_fd['fd_number']}",
                                date.today(),
                                selected_fd['customer_id'],
                                st.session_state.user['id']
                            ))
                        
                        conn.commit()
                        conn.close()
                        
                        st.success(f"""
                        ✅ **FD Closed Successfully!** 🎉
                        
                        📋 **Closure Summary:**
                        - FD Number: **{selected_fd['fd_number']}**
                        - Customer: **{selected_fd['customer']}**
                        - Principal: **Rs {selected_fd['principal']:,.2f}**
                        - Interest Earned: **Rs {selected_fd['accrued_interest']:,.2f}**
                        - {'Penalty Applied' if penalty_applied else 'No Penalty'}
                        - Total Amount: **Rs {final_amount:,.2f}**
                        - Transferred to: **{selected_fd['sb_account']}**
                        - New SB Balance: **Rs {new_sb_balance:,.2f}**
                        """)
                        st.balloons()
                        st.rerun()
                        
                    except Exception as e:
                        conn.rollback()
                        conn.close()
                        st.error(f"❌ Error closing FD: {str(e)}")
            
            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.info("FD closure cancelled")
    
    c.close()

# ==================== RECURRING DEPOSITS WITH DRILL-DOWN ====================
def recurring_deposits():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    tab1, tab2 = st.tabs(["📝 Open RD", "📊 Active RDs"])
    
    with tab1:
        st.markdown("### 📝 Open Recurring Deposit")
        
        cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
            "👤 Select Customer for RD",
            "rd_customer"
        )
        
        if cust_id and acc_id:
            st.success(f"""
            ✅ **Selected Customer:**
            - 👤 Name: **{cust_name}**
            - 🏦 Account: **{acc_number}**
            - 💰 Balance: **Rs {balance:,.2f}**
            """)
            
            with st.form("rd_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    monthly_amount = st.number_input(
                        "💰 Monthly Amount",
                        min_value=100.0,
                        step=100.0,
                        value=1000.0,
                        help="Minimum RD amount is Rs 100"
                    )
                    
                    tenure = st.selectbox(
                        "📅 Tenure (Months)",
                        [3, 6, 9, 12, 18, 24, 36, 48, 60],
                        help="Select RD duration in months"
                    )
                
                with col2:
                    interest_rate = st.number_input(
                        "📈 Interest Rate (%)",
                        min_value=3.0,
                        max_value=10.0,
                        value=6.0,
                        step=0.25,
                        help="Annual interest rate"
                    )
                    
                    start_date = st.date_input(
                        "📆 Start Date",
                        date.today()
                    )
                
                maturity_date = start_date + relativedelta(months=tenure)
                maturity_amount = calculate_rd_maturity(monthly_amount, interest_rate, tenure)
                total_investment = monthly_amount * tenure
                interest_earned = maturity_amount - total_investment
                
                st.info(f"""
                📊 **RD Summary:**
                - Total Investment: **Rs {total_investment:,.2f}**
                - Maturity Date: **{maturity_date.strftime('%d-%m-%Y')}**
                - Maturity Amount: **Rs {maturity_amount:,.2f}**
                - Interest Earned: **Rs {interest_earned:,.2f}**
                - Installments: **{tenure} monthly payments**
                """)
                
                # First installment funding
                funding_mode = st.radio(
                    "💳 First Installment Funding",
                    ["SB Transfer (Debit from SB)", "Cash", "Bank Transfer", "Cheque"],
                    horizontal=True
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    nominee_name = st.text_input("👤 Nominee Name (Optional)")
                with col2:
                    nominee_relation = st.text_input("🤝 Relationship (Optional)")
                
                if funding_mode == "SB Transfer (Debit from SB)" and monthly_amount > balance:
                    st.error(f"❌ Insufficient balance for first installment! Available: Rs {balance:,.2f}")
                
                if st.form_submit_button("✅ Open RD", use_container_width=True, type="primary"):
                    if funding_mode == "SB Transfer (Debit from SB)" and monthly_amount > balance:
                        st.error("❌ Insufficient balance for first installment!")
                    else:
                        conn = get_db()
                        try:
                            rd_number = generate_id('RD')
                            rd_account_number = generate_account_number('RD')
                            
                            # Create RD account
                            conn.execute("""
                                INSERT INTO accounts (
                                    account_number, customer_id, account_type,
                                    balance, interest_rate
                                ) VALUES (?,?,?,0.00,?)
                            """, (rd_account_number, cust_id, 'RD', interest_rate))
                            
                            rd_account_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                            
                            # Create RD record
                            conn.execute("""
                                INSERT INTO recurring_deposits (
                                    rd_number, account_id, monthly_amount,
                                    interest_rate, start_date, maturity_date,
                                    maturity_amount, tenure_months, total_installments,
                                    installments_paid, nominee_name, nominee_relation
                                ) VALUES (?,?,?,?,?,?,?,?,?,1,?,?)
                            """, (
                                rd_number, rd_account_id, monthly_amount,
                                interest_rate, start_date, maturity_date,
                                maturity_amount, tenure, tenure,
                                nominee_name, nominee_relation
                            ))
                            
                            # Debit from SB account if transfer
                            if funding_mode == "SB Transfer (Debit from SB)":
                                new_balance = balance - monthly_amount
                                conn.execute("UPDATE accounts SET balance=? WHERE id=?", (new_balance, acc_id))
                                conn.execute("""
                                    INSERT INTO transactions (
                                        transaction_id, account_id, transaction_type,
                                        amount, balance_after, description,
                                        reference_type, voucher_type, voucher_number,
                                        created_by
                                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                                """, (
                                    generate_id('TXN'), acc_id, 'DEBIT',
                                    monthly_amount, new_balance,
                                    f"RD Transfer to {rd_number}",
                                    'SB_TRANSFER', 'PAYMENT',
                                    generate_voucher_number('PAYMENT'),
                                    st.session_state.user['id']
                                ))
                            
                            # Credit RD account with first installment
                            conn.execute("""
                                INSERT INTO transactions (
                                    transaction_id, account_id, transaction_type,
                                    amount, balance_after, description,
                                    reference_type, voucher_type, voucher_number,
                                    created_by
                                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                            """, (
                                generate_id('TXN'), rd_account_id, 'CREDIT',
                                monthly_amount, monthly_amount,
                                f"RD Installment 1/{tenure}: {rd_number}",
                                funding_mode, 'RECEIPT',
                                generate_voucher_number('RECEIPT'),
                                st.session_state.user['id']
                            ))
                            
                            conn.commit()
                            conn.close()
                            
                            st.success(f"""
                            ✅ RD Opened Successfully! 🎉
                            
                            📋 **RD Details:**
                            - RD Number: **{rd_number}**
                            - Monthly Amount: **Rs {monthly_amount:,.2f}**
                            - Rate: **{interest_rate}%**
                            - Total Investment: **Rs {total_investment:,.2f}**
                            - Maturity: **{maturity_date.strftime('%d-%m-%Y')}**
                            - Maturity Amount: **Rs {maturity_amount:,.2f}**
                            """)
                            st.balloons()
                            
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
    
    with tab2:
        st.markdown("### 📊 Active Recurring Deposits")
        rds = c.execute("""
            SELECT rd.rd_number, c.first_name||' '||c.last_name as customer,
                   rd.monthly_amount, rd.installments_paid, rd.total_installments,
                   rd.maturity_amount, rd.status,
                   round(rd.installments_paid * 100.0 / rd.total_installments, 1) as progress
            FROM recurring_deposits rd
            JOIN accounts a ON rd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            WHERE rd.status='ACTIVE'
            ORDER BY rd.created_at DESC
        """).fetchall()
        
        if rds:
            df = pd.DataFrame(rds, columns=['RD No', 'Customer', 'Monthly', 'Paid', 'Total', 'Maturity', 'Status', 'Progress %'])
            st.dataframe(
                df.style.format({
                    'Monthly': 'Rs {:,.2f}',
                    'Maturity': 'Rs {:,.2f}',
                    'Progress %': '{:.1f}%'
                }),
                use_container_width=True
            )
            
            # Progress bar for each RD
            for rd in rds:
                progress = rd[7]
                st.progress(progress/100, text=f"RD {rd[0]} - {rd[1]} - {progress}% completed")
        else:
            st.info("No active recurring deposits")
    
    c.close()

# ==================== TRANSACTIONS ====================
def transactions():
    c = get_db()
    
    st.markdown("### 💳 All Transactions")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        txn_type = st.selectbox("📊 Type", ["All", "CREDIT", "DEBIT"])
    with col2:
        from_date = st.date_input("📅 From", date.today() - timedelta(days=30))
    with col3:
        to_date = st.date_input("📅 To", date.today())
    
    # Query
    query = """
        SELECT t.transaction_id, 
               COALESCE(c.first_name||' '||c.last_name, 'System') as customer,
               COALESCE(a.account_type, 'GEN') as acc_type,
               t.transaction_type, t.amount, 
               t.reference_type, t.description, t.created_at,
               t.balance_after
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.id
        LEFT JOIN customers c ON a.customer_id = c.id
        WHERE DATE(t.created_at) BETWEEN ? AND ?
    """
    params = [from_date, to_date]
    
    if txn_type != "All":
        query += " AND t.transaction_type = ?"
        params.append(txn_type)
    
    query += " ORDER BY t.created_at DESC LIMIT 200"
    
    txns = c.execute(query, params).fetchall()
    c.close()
    
    if txns:
        df = pd.DataFrame(txns, columns=['Txn ID', 'Customer', 'Account', 'Type', 'Amount', 'Mode', 'Description', 'Time', 'Balance'])
        df['Time'] = pd.to_datetime(df['Time']).dt.strftime('%d-%m-%Y %I:%M %p')
        
        st.dataframe(
            df.style.format({
                'Amount': 'Rs {:,.2f}',
                'Balance': 'Rs {:,.2f}'
            }),
            use_container_width=True,
            height=500
        )
        
        # Summary
        total_credit = df[df['Type'] == 'CREDIT']['Amount'].sum()
        total_debit = df[df['Type'] == 'DEBIT']['Amount'].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Total Credits", f"Rs {total_credit:,.2f}")
        col2.metric("💳 Total Debits", f"Rs {total_debit:,.2f}")
        col3.metric("📊 Net Balance", f"Rs {(total_credit - total_debit):,.2f}")
        
        st.download_button(
            "📥 Download Transactions",
            df.to_csv(index=False),
            f"transactions_{from_date}_{to_date}.csv",
            "text/csv"
        )
    else:
        st.info("No transactions in this period")

# ==================== JOURNAL VOUCHERS WITH DRILL-DOWN ====================
def journal_vouchers():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    tab1, tab2 = st.tabs(["📝 Create JV", "📋 Manage JVs"])
    
    with tab1:
        st.markdown("### 📝 Create Journal Voucher")
        
        # Optional customer selection
        cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
            "👤 Link Customer (Optional)",
            "jv_customer"
        )
        
        if cust_id and acc_id:
            st.info(f"📌 Linking JV to: **{cust_name}** (Account: {acc_number})")
        
        with st.form("jv_form"):
            voucher_date = st.date_input("📅 Voucher Date", date.today())
            description = st.text_area("📝 Narration", placeholder="Describe the transaction")
            
            num_entries = st.number_input("📊 Number of Entries", min_value=2, max_value=10, value=2)
            
            st.markdown("### 📊 Journal Entries")
            entries = []
            total_dr = 0
            total_cr = 0
            
            for i in range(int(num_entries)):
                st.markdown(f"**Entry {i+1}**")
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    head = st.text_input(f"Account Head", key=f"jh_{i}", placeholder="e.g., Bank A/c, Capital A/c")
                with col2:
                    dr = st.number_input(f"Debit", min_value=0.0, step=100.0, key=f"jd_{i}")
                with col3:
                    cr = st.number_input(f"Credit", min_value=0.0, step=100.0, key=f"jc_{i}")
                
                total_dr += dr
                total_cr += cr
                entries.append({'head': head, 'dr': dr, 'cr': cr})
            
            st.markdown("---")
            st.info(f"💰 **Total Debit: Rs {total_dr:,.2f} | Total Credit: Rs {total_cr:,.2f}**")
            
            if abs(total_dr - total_cr) > 0.01:
                st.error(f"❌ Difference: Rs {abs(total_dr - total_cr):,.2f} - Must balance!")
            
            if st.form_submit_button("✅ Create JV", use_container_width=True, type="primary"):
                if abs(total_dr - total_cr) > 0.01:
                    st.error("❌ Journal must be balanced!")
                else:
                    conn = get_db()
                    try:
                        voucher_number = generate_voucher_number('JOURNAL')
                        
                        conn.execute("""
                            INSERT INTO journal_vouchers (
                                voucher_number, voucher_date, description,
                                total_amount, created_by, customer_id
                            ) VALUES (?,?,?,?,?,?)
                        """, (voucher_number, voucher_date, description, total_dr, 
                              st.session_state.user['id'], cust_id))
                        
                        voucher_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                        
                        for entry in entries:
                            if (entry['dr'] > 0 or entry['cr'] > 0) and entry['head'].strip():
                                conn.execute("""
                                    INSERT INTO journal_entries (
                                        voucher_id, account_head,
                                        debit_amount, credit_amount
                                    ) VALUES (?,?,?,?)
                                """, (voucher_id, entry['head'].strip(), entry['dr'], entry['cr']))
                        
                        conn.commit()
                        conn.close()
                        
                        st.success(f"""
                        ✅ Journal Voucher Created! 🎉
                        
                        📋 **JV Details:**
                        - Voucher Number: **{voucher_number}**
                        - Total Amount: **Rs {total_dr:,.2f}**
                        - Entries: **{num_entries}**
                        """)
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    with tab2:
        st.markdown("### 📋 Manage Journal Vouchers")
        
        vouchers = c.execute("""
            SELECT jv.id, jv.voucher_number, jv.voucher_date,
                   jv.description, jv.total_amount, jv.status,
                   u.username as created_by, jv.created_at,
                   COALESCE(c.first_name||' '||c.last_name, 'N/A') as customer
            FROM journal_vouchers jv
            LEFT JOIN users u ON jv.created_by = u.id
            LEFT JOIN customers c ON jv.customer_id = c.id
            ORDER BY jv.created_at DESC
        """).fetchall()
        
        if vouchers:
            for v in vouchers:
                status_color = "🟡" if v[5] == 'DRAFT' else "🟢" if v[5] == 'POSTED' else "🔴"
                
                with st.expander(f"{status_color} {v[1]} | {v[2]} | Rs {v[4]:,.2f} | {v[5]}"):
                    st.markdown(f"""
                    **📋 Voucher Details:**
                    - Number: **{v[1]}**
                    - Date: **{v[2]}**
                    - Description: {v[3] or 'N/A'}
                    - Total: **Rs {v[4]:,.2f}**
                    - Status: **{v[5]}**
                    - Created By: {v[6]}
                    - Customer: {v[8]}
                    """)
                    
                    # Show entries
                    entries = c.execute("""
                        SELECT account_head, debit_amount, credit_amount
                        FROM journal_entries
                        WHERE voucher_id=?
                    """, (v[0],)).fetchall()
                    
                    if entries:
                        df = pd.DataFrame(entries, columns=['Account Head', 'Debit', 'Credit'])
                        st.dataframe(
                            df.style.format({
                                'Debit': 'Rs {:,.2f}',
                                'Credit': 'Rs {:,.2f}'
                            }),
                            use_container_width=True
                        )
                    
                    if v[5] == 'DRAFT':
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Post JV", key=f"post_{v[0]}", use_container_width=True):
                                conn = get_db()
                                conn.execute("""
                                    UPDATE journal_vouchers 
                                    SET status='POSTED', posted_by=?, posted_at=CURRENT_TIMESTAMP
                                    WHERE id=?
                                """, (st.session_state.user['id'], v[0]))
                                conn.commit()
                                conn.close()
                                st.success("✅ JV Posted!")
                                st.rerun()
                        
                        with col2:
                            if st.button("❌ Cancel JV", key=f"cancel_{v[0]}", use_container_width=True):
                                conn = get_db()
                                conn.execute("UPDATE journal_vouchers SET status='CANCELLED' WHERE id=?", (v[0],))
                                conn.commit()
                                conn.close()
                                st.warning("❌ JV Cancelled")
                                st.rerun()
        else:
            st.info("No journal vouchers found")
    
    c.close()

# ==================== INCOME & EXPENSES ====================
def income_expenses():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    tab1, tab2, tab3, tab4 = st.tabs(["💰 Income", "💸 Expense", "📊 View Income", "📊 View Expenses"])
    
    with tab1:
        st.markdown("### 💰 Record Income")
        
        with st.form("income_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                income_type = st.selectbox(
                    "📊 Income Type",
                    ["Interest Earned", "Fees & Charges", "Commission Income", "Other Income"]
                )
                amount = st.number_input("💰 Amount (Rs)", min_value=1.0, step=100.0)
            
            with col2:
                mode = st.selectbox("💳 Mode", ["CASH", "BANK", "CHEQUE", "ONLINE"])
                date_recorded = st.date_input("📅 Date", date.today())
            
            description = st.text_area("📝 Description")
            
            if st.form_submit_button("✅ Record Income", use_container_width=True, type="primary"):
                conn = get_db()
                try:
                    conn.execute("""
                        INSERT INTO income (
                            income_id, income_type, amount,
                            description, date, created_by
                        ) VALUES (?,?,?,?,?,?)
                    """, (generate_id('INC'), income_type, amount,
                          description, date_recorded, st.session_state.user['id']))
                    
                    # Also record in transactions
                    conn.execute("""
                        INSERT INTO transactions (
                            transaction_id, account_id, transaction_type,
                            amount, balance_after, description,
                            reference_type, voucher_type, voucher_number,
                            created_by
                        ) VALUES (?,?,?,?,?,?,?,?,?,?)
                    """, (
                        generate_id('TXN'), 0, 'CREDIT',
                        amount, amount,
                        f"Income: {income_type}",
                        mode, 'RECEIPT',
                        generate_voucher_number('RECEIPT'),
                        st.session_state.user['id']
                    ))
                    
                    conn.commit()
                    conn.close()
                    
                    st.success(f"✅ Income recorded: Rs {amount:,.2f}")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    with tab2:
        st.markdown("### 💸 Record Expense")
        
        with st.form("expense_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                expense_type = st.selectbox(
                    "📊 Expense Type",
                    ["Salary & Wages", "Rent & Utilities", "Operating Expenses", 
                     "Administrative Expenses", "Other Expenses"]
                )
                amount = st.number_input("💰 Amount (Rs)", min_value=1.0, step=100.0)
            
            with col2:
                mode = st.selectbox("💳 Mode", ["CASH", "BANK", "CHEQUE", "ONLINE"])
                date_recorded = st.date_input("📅 Date", date.today())
            
            description = st.text_area("📝 Description")
            
            if st.form_submit_button("✅ Record Expense", use_container_width=True, type="primary"):
                conn = get_db()
                try:
                    conn.execute("""
                        INSERT INTO expenses (
                            expense_id, expense_type, amount,
                            description, date, created_by
                        ) VALUES (?,?,?,?,?,?)
                    """, (generate_id('EXP'), expense_type, amount,
                          description, date_recorded, st.session_state.user['id']))
                    
                    # Also record in transactions
                    conn.execute("""
                        INSERT INTO transactions (
                            transaction_id, account_id, transaction_type,
                            amount, balance_after, description,
                            reference_type, voucher_type, voucher_number,
                            created_by
                        ) VALUES (?,?,?,?,?,?,?,?,?,?)
                    """, (
                        generate_id('TXN'), 0, 'DEBIT',
                        amount, -amount,
                        f"Expense: {expense_type}",
                        mode, 'PAYMENT',
                        generate_voucher_number('PAYMENT'),
                        st.session_state.user['id']
                    ))
                    
                    conn.commit()
                    conn.close()
                    
                    st.success(f"✅ Expense recorded: Rs {amount:,.2f}")
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    with tab3:
        st.markdown("### 📊 Income Summary")
        income_data = c.execute("""
            SELECT income_type, SUM(amount) as total, COUNT(*) as count
            FROM income
            GROUP BY income_type
            ORDER BY total DESC
        """).fetchall()
        
        if income_data:
            df = pd.DataFrame(income_data, columns=['Type', 'Total', 'Count'])
            st.dataframe(
                df.style.format({
                    'Total': 'Rs {:,.2f}'
                }),
                use_container_width=True
            )
            
            total_income = df['Total'].sum()
            st.info(f"💰 Total Income: Rs {total_income:,.2f}")
        else:
            st.info("No income recorded")
    
    with tab4:
        st.markdown("### 📊 Expense Summary")
        expense_data = c.execute("""
            SELECT expense_type, SUM(amount) as total, COUNT(*) as count
            FROM expenses
            GROUP BY expense_type
            ORDER BY total DESC
        """).fetchall()
        
        if expense_data:
            df = pd.DataFrame(expense_data, columns=['Type', 'Total', 'Count'])
            st.dataframe(
                df.style.format({
                    'Total': 'Rs {:,.2f}'
                }),
                use_container_width=True
            )
            
            total_expense = df['Total'].sum()
            st.info(f"💸 Total Expenses: Rs {total_expense:,.2f}")
        else:
            st.info("No expenses recorded")
    
    c.close()

# ==================== INTEREST CALCULATION ====================
def interest_calculation():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    st.markdown("### 📊 Interest Calculation")
    
    c = get_db()
    
    col1, col2 = st.columns(2)
    with col1:
        from_date = st.date_input("📅 From Date", date.today().replace(day=1))
    with col2:
        to_date = st.date_input("📅 To Date", date.today())
    
    # Optional customer filter
    cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
        "👤 Calculate for specific customer (Optional)",
        "int_customer"
    )
    
    if st.button("📊 Calculate & Post Interest", use_container_width=True, type="primary"):
        conn = get_db()
        
        try:
            # Get accounts
            if cust_id and acc_id:
                accounts = conn.execute("""
                    SELECT a.id, a.account_number, c.first_name||' '||c.last_name as customer,
                           a.balance, a.interest_rate, c.id
                    FROM accounts a
                    JOIN customers c ON a.customer_id = c.id
                    WHERE a.account_type='SB' AND a.status='ACTIVE' AND a.customer_id=?
                """, (cust_id,)).fetchall()
            else:
                accounts = conn.execute("""
                    SELECT a.id, a.account_number, c.first_name||' '||c.last_name as customer,
                           a.balance, a.interest_rate, c.id
                    FROM accounts a
                    JOIN customers c ON a.customer_id = c.id
                    WHERE a.account_type='SB' AND a.status='ACTIVE'
                """).fetchall()
            
            if not accounts:
                st.warning("No SB accounts found for interest calculation")
                conn.close()
                return
            
            total_interest = 0
            interest_details = []
            
            for acc in accounts:
                min_balance = get_minimum_balance(conn, acc[0], from_date, to_date)
                days = (to_date - from_date).days + 1
                
                if min_balance > 0 and days > 0:
                    interest = calculate_sb_interest(min_balance, acc[4] or 3.5, days)
                    
                    if interest > 0:
                        # Update account
                        conn.execute("""
                            UPDATE accounts 
                            SET total_interest_earned = COALESCE(total_interest_earned, 0) + ?
                            WHERE id=?
                        """, (interest, acc[0]))
                        
                        # Record calculation
                        conn.execute("""
                            INSERT INTO interest_calculations (
                                account_id, calculation_date,
                                principal_amount, interest_rate,
                                interest_earned, days_calculated,
                                customer_id
                            ) VALUES (?,DATE('now'),?,?,?,?,?)
                        """, (acc[0], min_balance, acc[4] or 3.5, interest, days, acc[5]))
                        
                        total_interest += interest
                        interest_details.append({
                            'Account': acc[1],
                            'Customer': acc[2],
                            'Min Balance': min_balance,
                            'Rate': acc[4] or 3.5,
                            'Days': days,
                            'Interest': interest
                        })
            
            conn.commit()
            conn.close()
            
            if interest_details:
                df = pd.DataFrame(interest_details)
                st.dataframe(
                    df.style.format({
                        'Min Balance': 'Rs {:,.2f}',
                        'Interest': 'Rs {:,.2f}',
                        'Rate': '{:.2f}%'
                    }),
                    use_container_width=True
                )
                
                st.success(f"✅ Interest Posted: Rs {total_interest:,.2f}")
                st.balloons()
            else:
                st.info("No interest calculated for this period")
                
        except Exception as e:
            conn.rollback()
            conn.close()
            st.error(f"❌ Error: {str(e)}")
    
    # Show recent interest calculations
    st.markdown("### 📊 Recent Interest Calculations")
    recent = c.execute("""
        SELECT ic.calculation_date, c.first_name||' '||c.last_name as customer,
               ic.principal_amount, ic.interest_rate, ic.interest_earned,
               ic.days_calculated
        FROM interest_calculations ic
        JOIN customers c ON ic.customer_id = c.id
        ORDER BY ic.created_at DESC LIMIT 20
    """).fetchall()
    c.close()
    
    if recent:
        df = pd.DataFrame(recent, columns=['Date', 'Customer', 'Principal', 'Rate', 'Interest', 'Days'])
        st.dataframe(
            df.style.format({
                'Principal': 'Rs {:,.2f}',
                'Interest': 'Rs {:,.2f}',
                'Rate': '{:.2f}%'
            }),
            use_container_width=True
        )

# ==================== TRIAL BALANCE ====================
def trial_balance():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    st.markdown("### ⚖️ Trial Balance")
    
    if st.button("🔄 Generate Trial Balance", use_container_width=True, type="primary"):
        trial = []
        
        # === ASSETS ===
        # Cash balances
        for mode, name in [('CASH', 'Cash in Hand'), ('BANK', 'Cash in Bank'), ('CHEQUE', 'Cash (Cheque)')]:
            bal = c.execute("""
                SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END), 0)
                FROM transactions WHERE reference_type=?
            """, (mode,)).fetchone()[0]
            if abs(bal) > 0:
                trial.append({'head': name, 'cat': 'Asset', 'dr': max(bal, 0), 'cr': max(-bal, 0)})
        
        # FD Principal
        fd_total = c.execute("SELECT COALESCE(SUM(principal_amount), 0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        if fd_total > 0:
            trial.append({'head': 'FD Deposits Held', 'cat': 'Asset', 'dr': fd_total, 'cr': 0})
        
        # RD Deposits
        rd_total = c.execute("""
            SELECT COALESCE(SUM(monthly_amount * installments_paid), 0) 
            FROM recurring_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if rd_total > 0:
            trial.append({'head': 'RD Deposits Held', 'cat': 'Asset', 'dr': rd_total, 'cr': 0})
        
        # FD Interest Receivable
        fd_int_asset = c.execute("""
            SELECT COALESCE(SUM(maturity_amount - principal_amount), 0) 
            FROM fixed_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if fd_int_asset > 0:
            trial.append({'head': 'FD Interest Receivable', 'cat': 'Asset', 'dr': fd_int_asset, 'cr': 0})
        
        # RD Interest Receivable
        rd_int_asset = c.execute("""
            SELECT COALESCE(SUM(maturity_amount - (monthly_amount * installments_paid)), 0) 
            FROM recurring_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if rd_int_asset > 0:
            trial.append({'head': 'RD Interest Receivable', 'cat': 'Asset', 'dr': rd_int_asset, 'cr': 0})
        
        # === LIABILITIES ===
        # SB Deposits
        sb_total = c.execute("SELECT COALESCE(SUM(balance), 0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb_total > 0:
            trial.append({'head': 'SB Deposits', 'cat': 'Liability', 'dr': 0, 'cr': sb_total})
        
        # SB Interest Payable
        sb_int = c.execute("SELECT COALESCE(SUM(total_interest_earned), 0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb_int > 0:
            trial.append({'head': 'SB Interest Payable', 'cat': 'Liability', 'dr': 0, 'cr': sb_int})
        
        # FD Interest Payable
        if fd_int_asset > 0:
            trial.append({'head': 'FD Interest Payable', 'cat': 'Liability', 'dr': 0, 'cr': fd_int_asset})
        
        # RD Interest Payable
        if rd_int_asset > 0:
            trial.append({'head': 'RD Interest Payable', 'cat': 'Liability', 'dr': 0, 'cr': rd_int_asset})
        
        # === JV ENTRIES ===
        jv_dr = c.execute("""
            SELECT je.account_head, SUM(je.debit_amount) 
            FROM journal_entries je 
            JOIN journal_vouchers jv ON je.voucher_id = jv.id 
            WHERE jv.status='POSTED' AND je.debit_amount > 0 
            GROUP BY je.account_head
        """).fetchall()
        for e in jv_dr:
            if e[1] > 0:
                trial.append({'head': f"JV: {e[0]}", 'cat': 'Asset', 'dr': e[1], 'cr': 0})
        
        jv_cr = c.execute("""
            SELECT je.account_head, SUM(je.credit_amount) 
            FROM journal_entries je 
            JOIN journal_vouchers jv ON je.voucher_id = jv.id 
            WHERE jv.status='POSTED' AND je.credit_amount > 0 
            GROUP BY je.account_head
        """).fetchall()
        for e in jv_cr:
            if e[1] > 0:
                trial.append({'head': f"JV: {e[0]}", 'cat': 'Liability', 'dr': 0, 'cr': e[1]})
        
        # === INCOME ===
        income_types = ['Interest Earned', 'Fees & Charges', 'Commission Income', 'Other Income']
        for it in income_types:
            amt = c.execute("SELECT COALESCE(SUM(amount), 0) FROM income WHERE income_type=?", (it,)).fetchone()[0]
            if amt > 0:
                trial.append({'head': it, 'cat': 'Income', 'dr': 0, 'cr': amt})
        
        # === EXPENSES ===
        expense_types = ['Salary & Wages', 'Rent & Utilities', 'Operating Expenses', 'Administrative Expenses', 'Other Expenses']
        for et in expense_types:
            amt = c.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE expense_type=?", (et,)).fetchone()[0]
            if amt > 0:
                trial.append({'head': et, 'cat': 'Expense', 'dr': amt, 'cr': 0})
        
        # === CALCULATE AND ADD CAPITAL ===
        tdr = sum(i['dr'] for i in trial)
        tcr = sum(i['cr'] for i in trial)
        
        if abs(tdr - tcr) > 0.01:
            diff = tdr - tcr
            if diff > 0:
                trial.append({'head': 'Capital/Equity', 'cat': 'Capital', 'dr': 0, 'cr': diff})
            else:
                trial.append({'head': 'Capital/Equity', 'cat': 'Capital', 'dr': -diff, 'cr': 0})
        
        # === DISPLAY ===
        if trial:
            df = pd.DataFrame(trial)
            
            # Final totals
            final_tdr = sum(i['dr'] for i in trial)
            final_tcr = sum(i['cr'] for i in trial)
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                asset_total = sum(i['dr'] for i in trial if i['cat'] == 'Asset')
                st.metric("📊 Assets (Dr)", f"Rs {asset_total:,.2f}")
            with col2:
                liability_total = sum(i['cr'] for i in trial if i['cat'] == 'Liability')
                st.metric("📊 Liabilities (Cr)", f"Rs {liability_total:,.2f}")
            with col3:
                income_total = sum(i['cr'] for i in trial if i['cat'] == 'Income')
                st.metric("💰 Income (Cr)", f"Rs {income_total:,.2f}")
            with col4:
                expense_total = sum(i['dr'] for i in trial if i['cat'] == 'Expense')
                st.metric("💸 Expenses (Dr)", f"Rs {expense_total:,.2f}")
            
            # Capital
            capital = next((i['cr'] for i in trial if i['cat'] == 'Capital' and i['cr'] > 0), 
                          next((i['dr'] for i in trial if i['cat'] == 'Capital' and i['dr'] > 0), 0))
            st.info(f"💰 **Capital/Equity: Rs {capital:,.2f}**")
            
            # Table
            display_df = df[['head', 'cat', 'dr', 'cr']].rename(columns={
                'head': 'Account Head',
                'cat': 'Category',
                'dr': 'Debit (Dr)',
                'cr': 'Credit (Cr)'
            })
            
            st.dataframe(
                display_df.style.format({
                    'Debit (Dr)': 'Rs {:,.2f}',
                    'Credit (Cr)': 'Rs {:,.2f}'
                }),
                use_container_width=True,
                height=500
            )
            
            # Totals
            st.markdown(f"**Total Debit: Rs {final_tdr:,.2f} | Total Credit: Rs {final_tcr:,.2f}**")
            
            if abs(final_tdr - final_tcr) < 0.01:
                st.success("✅ **PERFECTLY BALANCED!** 🎉")
                st.markdown(f"""
                ### 📊 Balance Sheet Equation:
                **Assets (Rs {asset_total:,.2f}) = Liabilities (Rs {liability_total:,.2f}) + Capital (Rs {capital:,.2f})**
                """)
            else:
                st.error(f"❌ Difference: Rs {abs(final_tdr - final_tcr):,.2f}")
            
            # Download
            st.download_button(
                "📥 Download Trial Balance",
                df.to_csv(index=False),
                "trial_balance.csv",
                "text/csv"
            )
    
    c.close()

# ==================== BALANCE SHEET ====================
def balance_sheet():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    st.markdown("### 📋 Balance Sheet")
    
    if st.button("🔄 Generate Balance Sheet", use_container_width=True, type="primary"):
        assets = []
        liabilities = []
        ta = 0
        tl = 0
        
        # === ASSETS ===
        # Cash
        for mode, name in [('CASH', 'Cash in Hand'), ('BANK', 'Cash in Bank'), ('CHEQUE', 'Cash (Cheque)')]:
            bal = c.execute("""
                SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END), 0)
                FROM transactions WHERE reference_type=?
            """, (mode,)).fetchone()[0]
            if bal > 0:
                assets.append({'name': name, 'amount': bal})
                ta += bal
        
        # FD Deposits
        fd_total = c.execute("SELECT COALESCE(SUM(principal_amount), 0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        if fd_total > 0:
            assets.append({'name': 'FD Deposits Held', 'amount': fd_total})
            ta += fd_total
        
        # RD Deposits
        rd_total = c.execute("""
            SELECT COALESCE(SUM(monthly_amount * installments_paid), 0) 
            FROM recurring_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if rd_total > 0:
            assets.append({'name': 'RD Deposits Held', 'amount': rd_total})
            ta += rd_total
        
        # Interest Receivable
        fd_int_asset = c.execute("""
            SELECT COALESCE(SUM(maturity_amount - principal_amount), 0) 
            FROM fixed_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if fd_int_asset > 0:
            assets.append({'name': 'FD Interest Receivable', 'amount': fd_int_asset})
            ta += fd_int_asset
        
        rd_int_asset = c.execute("""
            SELECT COALESCE(SUM(maturity_amount - (monthly_amount * installments_paid)), 0) 
            FROM recurring_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if rd_int_asset > 0:
            assets.append({'name': 'RD Interest Receivable', 'amount': rd_int_asset})
            ta += rd_int_asset
        
        # === LIABILITIES ===
        # SB Deposits
        sb_total = c.execute("SELECT COALESCE(SUM(balance), 0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb_total > 0:
            liabilities.append({'name': 'SB Deposits', 'amount': sb_total})
            tl += sb_total
        
        # SB Interest Payable
        sb_int = c.execute("SELECT COALESCE(SUM(total_interest_earned), 0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb_int > 0:
            liabilities.append({'name': 'SB Interest Payable', 'amount': sb_int})
            tl += sb_int
        
        # FD Interest Payable
        if fd_int_asset > 0:
            liabilities.append({'name': 'FD Interest Payable', 'amount': fd_int_asset})
            tl += fd_int_asset
        
        # RD Interest Payable
        if rd_int_asset > 0:
            liabilities.append({'name': 'RD Interest Payable', 'amount': rd_int_asset})
            tl += rd_int_asset
        
        # === CAPITAL ===
        capital = ta - tl
        
        # === DISPLAY ===
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📈 ASSETS (What Bank Owns)")
            st.markdown("---")
            for item in assets:
                st.markdown(f"💰 **{item['name']}**: Rs {item['amount']:,.2f}")
            st.markdown("---")
            st.markdown(f"### **Total Assets: Rs {ta:,.2f}**")
        
        with col2:
            st.markdown("### 📉 LIABILITIES (What Bank Owes)")
            st.markdown("---")
            for item in liabilities:
                st.markdown(f"💳 **{item['name']}**: Rs {item['amount']:,.2f}")
            st.markdown("---")
            st.markdown(f"### **Total Liabilities: Rs {tl:,.2f}**")
        
        st.markdown("---")
        st.markdown(f"## 💰 CAPITAL/EQUITY: Rs {capital:,.2f}")
        st.markdown("---")
        
        # Balance check
        if abs(ta - (tl + capital)) < 0.01:
            st.success(f"""
            ### ✅ PERFECTLY BALANCED! 🎉
            
            **Assets (Rs {ta:,.2f}) = Liabilities (Rs {tl:,.2f}) + Capital (Rs {capital:,.2f})**
            """)
            st.balloons()
        else:
            st.error(f"❌ Difference: Rs {abs(ta - (tl + capital)):,.2f}")
        
        # Interest explanation
        st.info(f"""
        ### 📊 Interest Balance Sheet:
        
        | Interest Type | Asset Side | Liability Side | Amount |
        |--------------|------------|----------------|--------|
        | FD Interest | FD Interest Receivable | FD Interest Payable | Rs {fd_int_asset:,.2f} |
        | RD Interest | RD Interest Receivable | RD Interest Payable | Rs {rd_int_asset:,.2f} |
        
        **How it works:**
        - **Receivable (Asset)**: Bank will earn/receive this interest
        - **Payable (Liability)**: Bank owes this same interest to customers
        - Both sides are equal, maintaining the balance
        """)
    
    c.close()

# ==================== PROFIT & LOSS ====================
def profit_loss():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    st.markdown("### 📈 Profit & Loss Statement")
    
    col1, col2 = st.columns(2)
    with col1:
        from_date = st.date_input("📅 From Date", date.today().replace(month=1, day=1))
    with col2:
        to_date = st.date_input("📅 To Date", date.today())
    
    if st.button("🔄 Generate P&L", use_container_width=True, type="primary"):
        # Income
        income_data = c.execute("""
            SELECT income_type, SUM(amount) as total
            FROM income
            WHERE DATE(date) BETWEEN ? AND ?
            GROUP BY income_type
        """, (from_date, to_date)).fetchall()
        
        # Expenses
        expense_data = c.execute("""
            SELECT expense_type, SUM(amount) as total
            FROM expenses
            WHERE DATE(date) BETWEEN ? AND ?
            GROUP BY expense_type
        """, (from_date, to_date)).fetchall()
        
        total_income = sum(i[1] for i in income_data)
        total_expense = sum(e[1] for e in expense_data)
        net_profit = total_income - total_expense
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 💰 INCOME")
            st.markdown("---")
            if income_data:
                for item in income_data:
                    st.markdown(f"📊 **{item[0]}**: Rs {item[1]:,.2f}")
                st.markdown("---")
                st.markdown(f"### **Total Income: Rs {total_income:,.2f}**")
            else:
                st.info("No income in this period")
        
        with col2:
            st.markdown("### 💸 EXPENSES")
            st.markdown("---")
            if expense_data:
                for item in expense_data:
                    st.markdown(f"📊 **{item[0]}**: Rs {item[1]:,.2f}")
                st.markdown("---")
                st.markdown(f"### **Total Expenses: Rs {total_expense:,.2f}**")
            else:
                st.info("No expenses in this period")
        
        st.markdown("---")
        
        if net_profit >= 0:
            st.success(f"### 🎉 Net Profit: Rs {net_profit:,.2f}")
            st.balloons()
        else:
            st.error(f"### 📉 Net Loss: Rs {abs(net_profit):,.2f}")
        
        # Ratio
        if total_income > 0:
            profit_margin = (net_profit / total_income) * 100
            st.info(f"📊 Profit Margin: {profit_margin:.1f}%")
    
    c.close()

# ==================== REPORTS ====================
def reports():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    st.markdown("### 📄 Reports")
    
    report_type = st.selectbox(
        "📊 Select Report",
        ["Customer List", "Daily Transactions", "Account Statement", "Interest Summary"]
    )
    
    if report_type == "Customer List":
        st.markhead("### 👥 Customer List")
        customers = c.execute("""
            SELECT customer_id, first_name, last_name, email, phone, kyc_status, created_at
            FROM customers
            ORDER BY created_at DESC
        """).fetchall()
        
        if customers:
            df = pd.DataFrame(customers, columns=['ID', 'First', 'Last', 'Email', 'Phone', 'KYC', 'Joined'])
            st.dataframe(df, use_container_width=True)
            st.download_button(
                "📥 Download CSV",
                df.to_csv(index=False),
                "customers_list.csv",
                "text/csv"
            )
        else:
            st.info("No customers found")
    
    elif report_type == "Daily Transactions":
        report_date = st.date_input("📅 Date", date.today())
        
        transactions = c.execute("""
            SELECT t.transaction_id, 
                   COALESCE(c.first_name||' '||c.last_name, 'System') as customer,
                   t.transaction_type, t.amount, t.reference_type,
                   t.description, t.created_at
            FROM transactions t
            LEFT JOIN accounts a ON t.account_id = a.id
            LEFT JOIN customers c ON a.customer_id = c.id
            WHERE DATE(t.created_at) = ?
            ORDER BY t.created_at DESC
        """, (report_date,)).fetchall()
        
        if transactions:
            df = pd.DataFrame(transactions, columns=['Txn ID', 'Customer', 'Type', 'Amount', 'Mode', 'Description', 'Time'])
            df['Time'] = pd.to_datetime(df['Time']).dt.strftime('%I:%M %p')
            st.dataframe(
                df.style.format({'Amount': 'Rs {:,.2f}'}),
                use_container_width=True
            )
            
            total_credit = df[df['Type'] == 'CREDIT']['Amount'].sum()
            total_debit = df[df['Type'] == 'DEBIT']['Amount'].sum()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("💰 Credits", f"Rs {total_credit:,.2f}")
            col2.metric("💳 Debits", f"Rs {total_debit:,.2f}")
            col3.metric("📊 Net", f"Rs {(total_credit - total_debit):,.2f}")
        else:
            st.info("No transactions on this date")
    
    elif report_type == "Account Statement":
        cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
            "👤 Select Customer",
            "report_customer"
        )
        
        if cust_id and acc_id:
            col1, col2 = st.columns(2)
            with col1:
                from_date = st.date_input("📅 From", date.today() - timedelta(days=30))
            with col2:
                to_date = st.date_input("📅 To", date.today())
            
            if st.button("📊 Generate Statement"):
                txns = c.execute("""
                    SELECT transaction_id, transaction_type, amount,
                           balance_after, description, reference_type,
                           created_at
                    FROM transactions
                    WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ?
                    ORDER BY created_at DESC
                """, (acc_id, from_date, to_date)).fetchall()
                
                if txns:
                    df = pd.DataFrame(txns, columns=['ID', 'Type', 'Amount', 'Balance', 'Description', 'Mode', 'Date'])
                    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%d-%m-%Y %I:%M %p')
                    st.dataframe(
                        df.style.format({
                            'Amount': 'Rs {:,.2f}',
                            'Balance': 'Rs {:,.2f}'
                        }),
                        use_container_width=True
                    )
                    st.download_button(
                        "📥 Download Statement",
                        df.to_csv(index=False),
                        f"statement_{acc_number}_{from_date}_{to_date}.csv",
                        "text/csv"
                    )
                else:
                    st.info("No transactions in this period")
    
    elif report_type == "Interest Summary":
        st.markdown("### 📊 Interest Summary")
        interest_data = c.execute("""
            SELECT c.first_name||' '||c.last_name as customer,
                   a.account_number,
                   COALESCE(a.total_interest_earned, 0) as interest_earned
            FROM customers c
            JOIN accounts a ON c.id = a.customer_id
            WHERE a.account_type='SB' AND a.status='ACTIVE'
            ORDER BY interest_earned DESC
        """).fetchall()
        
        if interest_data:
            df = pd.DataFrame(interest_data, columns=['Customer', 'Account', 'Interest Earned'])
            st.dataframe(
                df.style.format({'Interest Earned': 'Rs {:,.2f}'}),
                use_container_width=True
            )
            total_interest = df['Interest Earned'].sum()
            st.info(f"💰 Total Interest Earned: Rs {total_interest:,.2f}")
        else:
            st.info("No interest data available")
    
    c.close()

# ==================== MY ACCOUNTS (Customer View) ====================
def my_accounts():
    c = get_db()
    uid = st.session_state.user['id']
    
    customer = c.execute("SELECT * FROM customers WHERE user_id=?", (uid,)).fetchone()
    
    if not customer:
        st.warning("⚠️ No customer profile linked to your account. Please contact bank staff.")
        c.close()
        return
    
    st.markdown(f"### 👋 Welcome, {customer[3]} {customer[4]}!")
    
    accounts = c.execute("""
        SELECT account_number, account_type, balance,
               COALESCE(total_interest_earned, 0) as interest,
               interest_rate, status
        FROM accounts
        WHERE customer_id=? AND status='ACTIVE'
    """, (customer[0],)).fetchall()
    
    if accounts:
        for acc in accounts:
            with st.expander(f"🏦 {acc[1]} Account - {acc[0]}"):
                col1, col2, col3 = st.columns(3)
                col1.metric("💰 Balance", f"Rs {acc[2]:,.2f}")
                col2.metric("📈 Interest Earned", f"Rs {acc[3]:,.2f}")
                col3.metric("📊 Interest Rate", f"{acc[4]}%")
        
        # Total balance
        total_balance = sum(acc[2] for acc in accounts)
        total_interest = sum(acc[3] for acc in accounts)
        
        st.info(f"💰 **Total Portfolio: Rs {total_balance + total_interest:,.2f}**")
    else:
        st.info("No active accounts found")
    
    # FD and RD summary
    fds = c.execute("""
        SELECT fd_number, principal_amount, interest_rate,
               maturity_date, maturity_amount, status
        FROM fixed_deposits fd
        JOIN accounts a ON fd.account_id = a.id
        WHERE a.customer_id=?
    """, (customer[0],)).fetchall()
    
    rds = c.execute("""
        SELECT rd_number, monthly_amount, installments_paid,
               total_installments, maturity_amount, status
        FROM recurring_deposits rd
        JOIN accounts a ON rd.account_id = a.id
        WHERE a.customer_id=?
    """, (customer[0],)).fetchall()
    
    if fds:
        st.markdown("### 📈 Your Fixed Deposits")
        df = pd.DataFrame(fds, columns=['FD No', 'Principal', 'Rate', 'Maturity Date', 'Maturity Amount', 'Status'])
        st.dataframe(df.style.format({'Principal': 'Rs {:,.2f}', 'Maturity Amount': 'Rs {:,.2f}'}), use_container_width=True)
    
    if rds:
        st.markdown("### 🔄 Your Recurring Deposits")
        df = pd.DataFrame(rds, columns=['RD No', 'Monthly', 'Paid', 'Total', 'Maturity', 'Status'])
        st.dataframe(df.style.format({'Monthly': 'Rs {:,.2f}', 'Maturity': 'Rs {:,.2f}'}), use_container_width=True)
    
    c.close()

# ==================== MY TRANSACTIONS (Customer View) ====================
def my_transactions():
    c = get_db()
    uid = st.session_state.user['id']
    
    customer = c.execute("SELECT id FROM customers WHERE user_id=?", (uid,)).fetchone()
    
    if not customer:
        st.warning("⚠️ No customer profile found.")
        c.close()
        return
    
    st.markdown("### 💳 Your Transactions")
    
    txns = c.execute("""
        SELECT t.transaction_id, a.account_number, t.transaction_type,
               t.amount, t.balance_after, t.description,
               t.reference_type, t.created_at
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        WHERE a.customer_id=?
        ORDER BY t.created_at DESC
        LIMIT 100
    """, (customer[0],)).fetchall()
    
    if txns:
        df = pd.DataFrame(txns, columns=['Txn ID', 'Account', 'Type', 'Amount', 'Balance', 'Description', 'Mode', 'Date'])
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%d-%m-%Y %I:%M %p')
        st.dataframe(
            df.style.format({
                'Amount': 'Rs {:,.2f}',
                'Balance': 'Rs {:,.2f}'
            }),
            use_container_width=True
        )
        
        # Summary
        total_credit = df[df['Type'] == 'CREDIT']['Amount'].sum()
        total_debit = df[df['Type'] == 'DEBIT']['Amount'].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Total Credits", f"Rs {total_credit:,.2f}")
        col2.metric("💳 Total Debits", f"Rs {total_debit:,.2f}")
        col3.metric("📊 Net Change", f"Rs {(total_credit - total_debit):,.2f}")
    else:
        st.info("No transactions found")
    
    c.close()

# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    main()

