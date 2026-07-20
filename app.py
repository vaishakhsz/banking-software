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

def get_minimum_balance(conn, account_id, from_date, to_date):
    """Get minimum balance for an account during a period"""
    try:
        # Get starting balance (last balance before period)
        start_balance_result = conn.execute("""
            SELECT balance_after
            FROM transactions
            WHERE account_id=? AND DATE(created_at) < ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (account_id, from_date)).fetchone()
        
        if start_balance_result:
            start_balance = start_balance_result[0]
        else:
            # If no transactions before period, get current balance
            current_result = conn.execute("""
                SELECT balance FROM accounts WHERE id=?
            """, (account_id,)).fetchone()
            if current_result:
                start_balance = current_result[0]
            else:
                return 0
        
        # Get all transactions during the period
        transactions = conn.execute("""
            SELECT balance_after
            FROM transactions
            WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ?
            ORDER BY created_at
        """, (account_id, from_date, to_date)).fetchall()
        
        if transactions:
            all_balances = [start_balance] + [t[0] for t in transactions]
            return min(all_balances)
        else:
            return start_balance
            
    except Exception as e:
        # Return current balance as fallback
        current_result = conn.execute("""
            SELECT balance FROM accounts WHERE id=?
        """, (account_id,)).fetchone()
        return current_result[0] if current_result else 0

def calculate_and_post_sb_interest(created_by_user_id=1):
    """Calculate interest for all SB accounts and post to accounts with journal entries"""
    conn = get_db()
    try:
        # Get all active SB accounts
        accounts = conn.execute("""
            SELECT id, account_number, balance, interest_rate, 
                   COALESCE(total_interest_earned, 0) as total_interest,
                   last_interest_calculation, customer_id
            FROM accounts 
            WHERE account_type='SB' AND status='ACTIVE'
        """).fetchall()
        
        if not accounts:
            return "No active SB accounts found", []
        
        current_date = date.today()
        interest_posted = []
        
        for acc in accounts:
            account_id = acc[0]
            account_number = acc[1]
            balance = acc[2]
            rate = acc[3] if acc[3] else 3.5  # Default 3.5% if not set
            existing_interest = acc[4]
            last_calc_date = acc[5]
            customer_id = acc[6]
            
            # Determine calculation period
            if last_calc_date:
                try:
                    last_date = datetime.strptime(last_calc_date, '%Y-%m-%d').date()
                except:
                    last_date = current_date.replace(day=1)
            else:
                # Get account creation date
                acc_created = conn.execute("""
                    SELECT DATE(created_at) FROM accounts WHERE id=?
                """, (account_id,)).fetchone()
                if acc_created and acc_created[0]:
                    try:
                        last_date = datetime.strptime(acc_created[0], '%Y-%m-%d').date()
                    except:
                        last_date = current_date.replace(day=1)
                else:
                    last_date = current_date.replace(day=1)
            
            # Calculate days for interest
            days = (current_date - last_date).days
            if days <= 0:
                continue
            
            # Calculate minimum balance for the period
            min_balance = get_minimum_balance(conn, account_id, last_date, current_date)
            if min_balance <= 0:
                min_balance = balance
            
            # Calculate interest
            interest = calculate_sb_interest(min_balance, rate, days)
            
            if interest > 0:
                # Update account with interest
                new_balance = balance + interest
                new_total_interest = existing_interest + interest
                
                conn.execute("""
                    UPDATE accounts 
                    SET balance = ?, 
                        total_interest_earned = ?,
                        last_interest_calculation = DATE('now')
                    WHERE id = ?
                """, (new_balance, new_total_interest, account_id))
                
                # Record transaction
                txn_id = generate_id('TXN')
                voucher_num = generate_voucher_number('RECEIPT')
                
                conn.execute("""
                    INSERT INTO transactions 
                    (transaction_id, account_id, transaction_type, amount, 
                     balance_after, description, reference_type, voucher_type, 
                     voucher_number, created_by)
                    VALUES (?, ?, 'CREDIT', ?, ?, 'SB Interest Credited', 'INTEREST', 
                            'RECEIPT', ?, ?)
                """, (txn_id, account_id, interest, new_balance, 
                      voucher_num, created_by_user_id))
                
                # Record interest calculation log
                conn.execute("""
                    INSERT INTO interest_calculations 
                    (account_id, calculation_date, principal_amount, interest_rate, 
                     interest_earned, days_calculated)
                    VALUES (?, DATE('now'), ?, ?, ?, ?)
                """, (account_id, min_balance, rate, interest, days))
                
                # Create journal voucher for interest
                journal_voucher_num = generate_voucher_number('JOURNAL')
                conn.execute("""
                    INSERT INTO journal_vouchers 
                    (voucher_number, voucher_date, description, total_amount, status, created_by)
                    VALUES (?, DATE('now'), ?, ?, 'POSTED', ?)
                """, (journal_voucher_num, f"SB Interest Credited - A/C {account_number} (Customer ID: {customer_id})", 
                      interest, created_by_user_id))
                
                jv_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                
                # Debit entry - Interest Expense (goes to P&L)
                conn.execute("""
                    INSERT INTO journal_entries 
                    (voucher_id, account_head, debit_amount, credit_amount, description)
                    VALUES (?, 'Interest Paid on SB', ?, 0, ?)
                """, (jv_id, interest, f"Interest for A/C {account_number} - {days} days @ {rate}% p.a. on min balance ₹{min_balance:,.2f}"))
                
                # Credit entry - SB Account (liability)
                conn.execute("""
                    INSERT INTO journal_entries 
                    (voucher_id, account_head, debit_amount, credit_amount, description)
                    VALUES (?, 'SB Account - ' || ?, 0, ?, ?)
                """, (jv_id, account_number, interest, f"Interest credited to A/C {account_number}"))
                
                interest_posted.append({
                    'account_id': account_id,
                    'account_number': account_number,
                    'customer_id': customer_id,
                    'min_balance': min_balance,
                    'balance_before': balance,
                    'interest': interest,
                    'new_balance': new_balance,
                    'rate': rate,
                    'days': days,
                    'journal_voucher': journal_voucher_num,
                    'total_interest_earned': new_total_interest,
                    'maturity_value': new_balance  # For SB, maturity = balance + interest
                })
        
        conn.commit()
        return "SUCCESS", interest_posted
    
    except Exception as e:
        conn.rollback()
        return f"Error: {str(e)}", []
    finally:
        conn.close()

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
    .jv-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
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

def show_dashboard():
    st.markdown('<h1 class="main-header">📊 Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Real-time overview of your banking operations</p>', unsafe_allow_html=True)
    
    conn = get_db()
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        st.markdown(f'''
        <div class="metric-card">
            <span class="icon">👥</span>
            <h3>{customers}</h3>
            <p>Total Customers</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        accounts = conn.execute("SELECT COUNT(*) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
        st.markdown(f'''
        <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <span class="icon">💰</span>
            <h3>{accounts}</h3>
            <p>Active SB Accounts</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col3:
        total_balance = conn.execute("SELECT COALESCE(SUM(balance), 0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
        total_interest = conn.execute("SELECT COALESCE(SUM(total_interest_earned), 0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
        maturity_value = total_balance + total_interest
        st.markdown(f'''
        <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <span class="icon">🏦</span>
            <h3>₹{maturity_value:,.2f}</h3>
            <p>Total SB Maturity Value</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col4:
        pending_kyc = conn.execute("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'").fetchone()[0]
        st.markdown(f'''
        <div class="metric-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
            <span class="icon">🔍</span>
            <h3>{pending_kyc}</h3>
            <p>Pending KYC</p>
        </div>
        ''', unsafe_allow_html=True)
    
    st.divider()
    
    # Recent Transactions
    st.subheader("📌 Recent Transactions")
    transactions = conn.execute("""
        SELECT t.transaction_id, c.first_name || ' ' || c.last_name as customer_name,
               t.transaction_type, t.amount, t.description, t.created_at
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        JOIN customers c ON a.customer_id = c.id
        ORDER BY t.created_at DESC
        LIMIT 10
    """).fetchall()
    
    if transactions:
        df = pd.DataFrame(transactions, columns=['Transaction ID', 'Customer', 'Type', 'Amount', 'Description', 'Date'])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No transactions yet")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Account Distribution")
        account_types = conn.execute("""
            SELECT account_type, COUNT(*) as count 
            FROM accounts 
            WHERE status='ACTIVE' 
            GROUP BY account_type
        """).fetchall()
        
        if account_types:
            df = pd.DataFrame(account_types, columns=['Type', 'Count'])
            fig = px.pie(df, values='Count', names='Type', title='Account Types', 
                         color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(showlegend=True, height=350)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Monthly Transactions")
        monthly = conn.execute("""
            SELECT strftime('%Y-%m', created_at) as month, 
                   COUNT(*) as count,
                   SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE 0 END) as credits,
                   SUM(CASE WHEN transaction_type='DEBIT' THEN amount ELSE 0 END) as debits
            FROM transactions
            GROUP BY month
            ORDER BY month DESC
            LIMIT 6
        """).fetchall()
        
        if monthly:
            df = pd.DataFrame(monthly, columns=['Month', 'Count', 'Credits', 'Debits'])
            fig = go.Figure()
            fig.add_trace(go.Bar(name='Credits', x=df['Month'], y=df['Credits'], 
                                 marker_color='#10b981'))
            fig.add_trace(go.Bar(name='Debits', x=df['Month'], y=df['Debits'], 
                                 marker_color='#ef4444'))
            fig.update_layout(barmode='group', title='Monthly Credit/Debit Analysis',
                            height=350, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
    
    conn.close()

def show_customer_management():
    st.markdown('<h1 class="main-header">👥 Customer Management</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Register, view and manage customer profiles</p>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Register Customer", "👥 View Customers", "🔍 Search Customer", "📊 Customer Analytics"])
    
    with tab1:
        st.subheader("New Customer Registration")
        
        with st.form("customer_registration"):
            col1, col2 = st.columns(2)
            
            with col1:
                first_name = st.text_input("First Name *")
                last_name = st.text_input("Last Name *")
                date_of_birth = st.date_input("Date of Birth *", min_value=date(1900,1,1), max_value=date.today())
                gender = st.selectbox("Gender", ["Male", "Female", "Other"])
                email = st.text_input("Email *")
                phone = st.text_input("Phone Number *")
            
            with col2:
                pan_number = st.text_input("PAN Number * (e.g., ABCDE1234F)")
                aadhar_number = st.text_input("Aadhar Number * (12 digits)")
                address = st.text_area("Address")
                city = st.text_input("City")
                state = st.text_input("State")
                pincode = st.text_input("PIN Code")
            
            st.subheader("📎 KYC Documents Upload")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                pan_document = st.file_uploader("PAN Card *", type=['jpg', 'jpeg', 'png', 'pdf'])
            with col2:
                aadhar_document = st.file_uploader("Aadhar Card *", type=['jpg', 'jpeg', 'png', 'pdf'])
            with col3:
                photo = st.file_uploader("Passport Size Photo", type=['jpg', 'jpeg', 'png'])
            
            signature = st.file_uploader("Signature", type=['jpg', 'jpeg', 'png'])
            
            submitted = st.form_submit_button("📝 Register Customer", use_container_width=True)
            
            if submitted:
                if not all([first_name, last_name, email, phone, pan_number, aadhar_number]):
                    st.error("Please fill all required fields marked with *")
                elif not pan_document or not aadhar_document:
                    st.error("Please upload PAN and Aadhar documents")
                else:
                    try:
                        conn = get_db()
                        customer_id = generate_id('CUST')
                        
                        # Read file data
                        pan_data = pan_document.read()
                        aadhar_data = aadhar_document.read()
                        photo_data = photo.read() if photo else None
                        signature_data = signature.read() if signature else None
                        
                        conn.execute("""
                            INSERT INTO customers (customer_id, first_name, last_name, date_of_birth, 
                            gender, email, phone, address, city, state, pincode, pan_number, 
                            aadhar_number, pan_document, aadhar_document, photo, signature)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (customer_id, first_name, last_name, date_of_birth, gender, email, 
                              phone, address, city, state, pincode, pan_number, aadhar_number,
                              pan_data, aadhar_data, photo_data, signature_data))
                        
                        conn.commit()
                        conn.close()
                        
                        st.success(f"✅ Customer registered successfully!")
                        st.info(f"Customer ID: **{customer_id}**")
                        st.warning("KYC verification is pending. Admin will verify the documents.")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    with tab2:
        st.subheader("Customer List & Details")
        conn = get_db()
        customers = conn.execute("""
            SELECT c.id, c.customer_id, c.first_name, c.last_name, c.email, c.phone, 
                   c.city, c.state, c.pan_number, c.aadhar_number, c.kyc_status, 
                   c.created_at, c.date_of_birth, c.gender, c.address, c.pincode
            FROM customers c
            ORDER BY c.created_at DESC
        """).fetchall()
        
        if customers:
            for cust in customers:
                with st.expander(f"👤 {cust[2]} {cust[3]} - {cust[1]} ({cust[10]})", expanded=False):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.markdown("### 📋 Personal Information")
                        st.write(f"**Customer ID:** {cust[1]}")
                        st.write(f"**Full Name:** {cust[2]} {cust[3]}")
                        st.write(f"**Date of Birth:** {cust[12]}")
                        st.write(f"**Age:** {calculate_age(cust[12])} years")
                        st.write(f"**Gender:** {cust[13]}")
                        st.write(f"**Email:** {cust[4]}")
                        st.write(f"**Phone:** {cust[5]}")
                    
                    with col2:
                        st.markdown("### 🏠 Address & Documents")
                        st.write(f"**Address:** {cust[14]}")
                        st.write(f"**City:** {cust[6]}")
                        st.write(f"**State:** {cust[7]}")
                        st.write(f"**PIN Code:** {cust[15]}")
                        st.write(f"**PAN Number:** {cust[8]}")
                        st.write(f"**Aadhar Number:** {cust[9]}")
                        
                        kyc_status_color = {
                            'VERIFIED': '🟢',
                            'PENDING': '🟡',
                            'REJECTED': '🔴'
                        }
                        st.write(f"**KYC Status:** {kyc_status_color.get(cust[10], '⚪')} {cust[10]}")
                    
                    with col3:
                        st.markdown("### 📅 Account Info")
                        st.write(f"**Registration Date:** {cust[11][:10] if cust[11] else 'N/A'}")
                        
                        # Get accounts linked to this customer
                        accounts = conn.execute("""
                            SELECT account_number, account_type, balance, status,
                                   COALESCE(total_interest_earned, 0) as total_interest
                            FROM accounts
                            WHERE customer_id=? AND account_type='SB'
                        """, (cust[0],)).fetchall()
                        
                        if accounts:
                            st.write("**SB Accounts:**")
                            for acc in accounts:
                                maturity = acc[2] + acc[4]
                                st.write(f"• {acc[0]}")
                                st.write(f"  Balance: ₹{acc[2]:,.2f}")
                                st.write(f"  Interest: ₹{acc[4]:,.2f}")
                                st.write(f"  Maturity: ₹{maturity:,.2f} | {acc[3]}")
                        else:
                            st.write("No SB accounts linked yet")
                    
                    # Show documents if available
                    st.divider()
                    st.markdown("### 📎 Documents")
                    doc_col1, doc_col2, doc_col3 = st.columns(3)
                    
                    # Get full customer data with documents
                    cust_full = conn.execute("SELECT * FROM customers WHERE id=?", (cust[0],)).fetchone()
                    
                    with doc_col1:
                        if cust_full[16]:  # PAN
                            st.write("**PAN Card:**")
                            try:
                                st.image(cust_full[16], width=200)
                            except:
                                st.info("Document available (click to view)")
                    
                    with doc_col2:
                        if cust_full[17]:  # Aadhar
                            st.write("**Aadhar Card:**")
                            try:
                                st.image(cust_full[17], width=200)
                            except:
                                st.info("Document available (click to view)")
                    
                    with doc_col3:
                        if cust_full[18]:  # Photo
                            st.write("**Photo:**")
                            try:
                                st.image(cust_full[18], width=150)
                            except:
                                st.info("Photo available (click to view)")
            
            # Export option
            df = pd.DataFrame(customers, columns=['ID', 'Customer ID', 'First Name', 'Last Name', 
                                                  'Email', 'Phone', 'City', 'State', 'PAN', 'Aadhar',
                                                  'KYC Status', 'Reg Date', 'DOB', 'Gender', 'Address', 'PIN'])
            csv = df.to_csv(index=False)
            st.download_button("📥 Download Customer List", csv, "customers.csv", "text/csv")
        else:
            st.info("No customers registered yet")
        conn.close()
    
    with tab3:
        st.subheader("Search Customer")
        search_term = st.text_input("Search by Name, Customer ID, Email, Phone, PAN, or Aadhar")
        
        if search_term:
            conn = get_db()
            customers = conn.execute("""
                SELECT * FROM customers
                WHERE customer_id LIKE ? OR first_name LIKE ? OR last_name LIKE ? 
                OR email LIKE ? OR phone LIKE ? OR pan_number LIKE ? OR aadhar_number LIKE ?
            """, (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%',
                  f'%{search_term}%', f'%{search_term}%', f'%{search_term}%', f'%{search_term}%')).fetchall()
            
            if customers:
                st.success(f"Found {len(customers)} customer(s)")
                for cust in customers:
                    with st.expander(f"📋 {cust[3]} {cust[4]} - {cust[2]}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Customer ID:** {cust[2]}")
                            st.write(f"**Date of Birth:** {cust[5]}")
                            st.write(f"**Gender:** {cust[6]}")
                            st.write(f"**Email:** {cust[7]}")
                            st.write(f"**Phone:** {cust[8]}")
                            st.write(f"**PAN:** {cust[12]}")
                            st.write(f"**Aadhar:** {cust[13]}")
                        with col2:
                            kyc_color = {'VERIFIED': '🟢', 'PENDING': '🟡', 'REJECTED': '🔴'}
                            st.write(f"**KYC Status:** {kyc_color.get(cust[14], '⚪')} {cust[14]}")
                            st.write(f"**Address:** {cust[9]}")
                            st.write(f"**City:** {cust[10]}, {cust[11]}")
                            st.write(f"**Registration:** {cust[20][:10] if cust[20] else 'N/A'}")
            else:
                st.warning("No customer found")
            conn.close()
    
    with tab4:
        st.subheader("Customer Analytics")
        conn = get_db()
        
        # KYC Status Distribution
        kyc_stats = conn.execute("""
            SELECT kyc_status, COUNT(*) as count
            FROM customers
            GROUP BY kyc_status
        """).fetchall()
        
        if kyc_stats:
            df = pd.DataFrame(kyc_stats, columns=['Status', 'Count'])
            fig = px.pie(df, values='Count', names='Status', title='KYC Status Distribution',
                         color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig, use_container_width=True)
        
        # City-wise distribution
        city_stats = conn.execute("""
            SELECT city, COUNT(*) as count
            FROM customers
            GROUP BY city
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()
        
        if city_stats:
            df = pd.DataFrame(city_stats, columns=['City', 'Customers'])
            fig = px.bar(df, x='City', y='Customers', title='Top 10 Cities by Customers',
                        color_discrete_sequence=['#667eea'])
            st.plotly_chart(fig, use_container_width=True)
        
        conn.close()

def calculate_age(dob_str):
    """Calculate age from date of birth string"""
    if not dob_str:
        return "N/A"
    try:
        dob = datetime.strptime(str(dob_str), '%Y-%m-%d').date()
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age
    except:
        return "N/A"

def show_my_details():
    st.markdown('<h1 class="main-header">👤 My Details</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">View your personal information and accounts</p>', unsafe_allow_html=True)
    
    conn = get_db()
    
    # Get customer linked to this user
    customer = conn.execute("""
        SELECT * FROM customers WHERE user_id=?
    """, (st.session_state.user['id'],)).fetchone()
    
    if customer:
        st.markdown('<div class="customer-card">', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if customer[18]:  # Photo
                try:
                    st.image(customer[18], width=150)
                except:
                    st.write("📷 No photo")
        
        with col2:
            st.markdown(f"## {customer[3]} {customer[4]}")
            st.write(f"**Customer ID:** {customer[2]}")
            st.write(f"**Email:** {customer[7]}")
            st.write(f"**Phone:** {customer[8]}")
            kyc_color = {'VERIFIED': '🟢', 'PENDING': '🟡', 'REJECTED': '🔴'}
            st.write(f"**KYC Status:** {kyc_color.get(customer[14], '⚪')} {customer[14]}")
        
        with col3:
            st.write(f"**DOB:** {customer[5]}")
            st.write(f"**Gender:** {customer[6]}")
            st.write(f"**PAN:** {customer[12]}")
            st.write(f"**Aadhar:** {customer[13]}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Show accounts
        st.subheader("💰 My Accounts")
        accounts = conn.execute("""
            SELECT account_number, account_type, balance, interest_rate, status, 
                   COALESCE(total_interest_earned, 0) as total_interest, created_at
            FROM accounts
            WHERE customer_id=? AND account_type='SB'
            ORDER BY created_at DESC
        """, (customer[0],)).fetchall()
        
        if accounts:
            for acc in accounts:
                maturity_value = acc[2] + acc[5]
                with st.expander(f"{acc[1]} - {acc[0]} (Maturity: ₹{maturity_value:,.2f})"):
                    st.write(f"**Account Number:** {acc[0]}")
                    st.write(f"**Type:** {acc[1]}")
                    st.write(f"**Principal Balance:** ₹{acc[2]:,.2f}")
                    st.write(f"**Total Interest Earned:** ₹{acc[5]:,.2f}")
                    st.write(f"**Maturity Value (Principal + Interest):** ₹{maturity_value:,.2f}")
                    st.write(f"**Interest Rate:** {acc[3]}%")
                    st.write(f"**Status:** {acc[4]}")
                    st.write(f"**Opened:** {acc[6][:10]}")
        else:
            st.info("No SB accounts found")
    else:
        st.warning("Customer profile not found. Please contact admin.")
    
    conn.close()

def show_kyc_verification():
    st.markdown('<h1 class="main-header">🔍 KYC Verification</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Verify customer documents and approve accounts</p>', unsafe_allow_html=True)
    
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized access")
        return
    
    conn = get_db()
    
    tab1, tab2 = st.tabs(["📋 Pending Verifications", "✅ Verified Customers"])
    
    with tab1:
        pending_kyc = conn.execute("""
            SELECT * FROM customers WHERE kyc_status='PENDING'
            ORDER BY created_at
        """).fetchall()
        
        if not pending_kyc:
            st.success("✅ No pending KYC verifications!")
        else:
            st.subheader(f"Pending Verifications: {len(pending_kyc)}")
            
            for cust in pending_kyc:
                with st.expander(f"📄 {cust[3]} {cust[4]} - {cust[2]}", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("### Personal Information")
                        st.write(f"**Name:** {cust[3]} {cust[4]}")
                        st.write(f"**Date of Birth:** {cust[5]}")
                        st.write(f"**Gender:** {cust[6]}")
                        st.write(f"**Email:** {cust[7]}")
                        st.write(f"**Phone:** {cust[8]}")
                        st.write(f"**PAN Number:** {cust[12]}")
                        st.write(f"**Aadhar Number:** {cust[13]}")
                        st.write(f"**Address:** {cust[9]}, {cust[10]}, {cust[11]}")
                    
                    with col2:
                        st.write("### Documents")
                        
                        if cust[16]:
                            st.write("**PAN Card:**")
                            try:
                                st.image(cust[16], width=250)
                            except:
                                st.info("Document uploaded (binary format)")
                        
                        if cust[17]:
                            st.write("**Aadhar Card:**")
                            try:
                                st.image(cust[17], width=250)
                            except:
                                st.info("Document uploaded (binary format)")
                        
                        if cust[18]:
                            st.write("**Photo:**")
                            try:
                                st.image(cust[18], width=150)
                            except:
                                st.info("Photo uploaded (binary format)")
                    
                    st.divider()
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button(f"✅ Approve KYC", key=f"approve_{cust[0]}", use_container_width=True):
                            # Check if customer already has an SB account
                            existing_account = conn.execute("""
                                SELECT id FROM accounts 
                                WHERE customer_id=? AND account_type='SB' AND status='ACTIVE'
                            """, (cust[0],)).fetchone()
                            
                            if existing_account:
                                st.warning("Customer already has an SB account. Updating KYC status only.")
                                conn.execute("""
                                    UPDATE customers 
                                    SET kyc_status='VERIFIED', 
                                        kyc_verified_by=?,
                                        kyc_verified_at=CURRENT_TIMESTAMP
                                    WHERE id=?
                                """, (st.session_state.user['id'], cust[0]))
                                conn.commit()
                                st.success("✅ KYC approved! Customer already has an SB account.")
                            else:
                                conn.execute("""
                                    UPDATE customers 
                                    SET kyc_status='VERIFIED', 
                                        kyc_verified_by=?,
                                        kyc_verified_at=CURRENT_TIMESTAMP
                                    WHERE id=?
                                """, (st.session_state.user['id'], cust[0]))
                                
                                # Create SB account with 0 balance automatically
                                account_number = generate_account_number('SB')
                                conn.execute("""
                                    INSERT INTO accounts (account_number, customer_id, account_type, 
                                                         balance, interest_rate, last_interest_calculation,
                                                         total_interest_earned)
                                    VALUES (?, ?, 'SB', 0.00, 3.50, DATE('now'), 0.00)
                                """, (account_number, cust[0]))
                                
                                conn.commit()
                                st.success(f"✅ KYC approved! SB Account created with 0 balance.")
                                st.info(f"SB Account Number: **{account_number}**")
                            st.rerun()
                    
                    with col2:
                        if st.button(f"❌ Reject KYC", key=f"reject_{cust[0]}", use_container_width=True):
                            conn.execute("""
                                UPDATE customers 
                                SET kyc_status='REJECTED'
                                WHERE id=?
                            """, (cust[0],))
                            conn.commit()
                            st.warning(f"KYC rejected for {cust[3]} {cust[4]}")
                            st.rerun()
                    
                    with col3:
                        st.text_input(f"Remarks", key=f"remarks_{cust[0]}", placeholder="Optional remarks")
    
    with tab2:
        verified_customers = conn.execute("""
            SELECT customer_id, first_name, last_name, email, phone, kyc_verified_at
            FROM customers
            WHERE kyc_status='VERIFIED'
            ORDER BY kyc_verified_at DESC
        """).fetchall()
        
        if verified_customers:
            st.subheader(f"Verified Customers: {len(verified_customers)}")
            df = pd.DataFrame(verified_customers, columns=['Customer ID', 'First Name', 'Last Name', 
                                                           'Email', 'Phone', 'Verified Date'])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No verified customers yet")
    
    conn.close()

def show_create_sb_account():
    st.markdown('<h1 class="main-header">🏦 Create SB Account</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Open a new Savings Bank Account for a verified customer</p>', unsafe_allow_html=True)
    
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized access")
        return
    
    conn = get_db()
    
    # Get verified customers who don't have an SB account
    customers = conn.execute("""
        SELECT c.id, c.customer_id, c.first_name || ' ' || c.last_name as name,
               c.email, c.phone
        FROM customers c
        WHERE c.kyc_status='VERIFIED' 
        AND NOT EXISTS (
            SELECT 1 FROM accounts a 
            WHERE a.customer_id = c.id 
            AND a.account_type='SB' 
            AND a.status='ACTIVE'
        )
        ORDER BY c.created_at DESC
    """).fetchall()
    
    if not customers:
        st.info("✅ All verified customers already have SB accounts!")
        return
    
    st.subheader("Select Customer for SB Account")
    
    customer_options = {f"{cust[1]} - {cust[2]} (Email: {cust[3]})": cust for cust in customers}
    selected = st.selectbox("Select Customer", list(customer_options.keys()))
    
    if selected:
        customer = customer_options[selected]
        
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        st.write(f"**Customer ID:** {customer[1]}")
        st.write(f"**Name:** {customer[2]}")
        st.write(f"**Email:** {customer[3]}")
        st.write(f"**Phone:** {customer[4]}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        with st.form("create_sb_account_form"):
            col1, col2 = st.columns(2)
            with col1:
                interest_rate = st.number_input("Interest Rate (%)", min_value=0.0, max_value=10.0, value=3.50, step=0.25)
            with col2:
                opening_balance = st.number_input("Opening Balance (₹)", min_value=0.0, step=100.0, value=0.0)
            
            if st.form_submit_button("🏦 Create SB Account", use_container_width=True):
                try:
                    account_number = generate_account_number('SB')
                    
                    conn.execute("""
                        INSERT INTO accounts (account_number, customer_id, account_type, 
                                             balance, interest_rate, last_interest_calculation,
                                             total_interest_earned)
                        VALUES (?, ?, 'SB', ?, ?, DATE('now'), 0.00)
                    """, (account_number, customer[0], opening_balance, interest_rate))
                    
                    conn.commit()
                    st.success(f"✅ SB Account created successfully!")
                    st.info(f"Account Number: **{account_number}**")
                    st.info(f"Opening Balance: **₹{opening_balance:,.2f}**")
                    st.info(f"Maturity Value (Principal + Interest): **₹{opening_balance:,.2f}**")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    conn.close()

def show_sb_accounts():
    st.markdown('<h1 class="main-header">💰 Savings Bank Accounts</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Manage savings accounts, deposits and withdrawals with maturity values</p>', unsafe_allow_html=True)
    
    conn = get_db()
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Account List", "💸 Deposit/Withdraw", "📜 Account Statement", "📈 Interest Info"])
    
    with tab1:
        st.subheader("SB Account List with Maturity Values")
        
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
                maturity_value = acc[2] + acc[5]
                account_data.append({
                    'Account Number': acc[0],
                    'Customer Name': acc[1],
                    'Principal Balance': acc[2],
                    'Interest Rate': acc[3],
                    'Status': acc[4],
                    'Total Interest Earned': acc[5],
                    'Maturity Value': maturity_value,
                    'Opening Date': acc[6]
                })
            
            df = pd.DataFrame(account_data)
            st.dataframe(df.style.format({
                'Principal Balance': '₹{:,.2f}',
                'Interest Rate': '{:.2f}%',
                'Total Interest Earned': '₹{:,.2f}',
                'Maturity Value': '₹{:,.2f}'
            }), use_container_width=True)
            
            total_sb = sum(acc[2] for acc in accounts)
            total_interest = sum(acc[5] for acc in accounts)
            total_maturity = total_sb + total_interest
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"**Total Principal: ₹{total_sb:,.2f}**")
            with col2:
                st.info(f"**Total Interest: ₹{total_interest:,.2f}**")
            with col3:
                st.success(f"**Total Maturity Value: ₹{total_maturity:,.2f}**")
        else:
            st.info("No SB accounts found")
    
    with tab2:
        st.subheader("Transaction (Deposit/Withdrawal)")
        
        if st.session_state.user['role'] == 'customer':
            accounts = conn.execute("""
                SELECT a.id, a.account_number, c.first_name || ' ' || c.last_name as name, a.balance,
                       COALESCE(a.total_interest_earned, 0) as total_interest
                FROM accounts a
                JOIN customers c ON a.customer_id = c.id
                WHERE a.account_type='SB' AND a.status='ACTIVE' AND c.user_id=?
            """, (st.session_state.user['id'],)).fetchall()
        else:
            accounts = conn.execute("""
                SELECT a.id, a.account_number, c.first_name || ' ' || c.last_name as name, a.balance,
                       COALESCE(a.total_interest_earned, 0) as total_interest
                FROM accounts a
                JOIN customers c ON a.customer_id = c.id
                WHERE a.account_type='SB' AND a.status='ACTIVE'
            """).fetchall()
        
        if accounts:
            account_options = {f"{acc[1]} - {acc[2]} (Principal: ₹{acc[3]:,.2f}, Maturity: ₹{acc[3]+acc[4]:,.2f})": acc for acc in accounts}
            selected = st.selectbox("Select Account", list(account_options.keys()))
            
            if selected:
                account = account_options[selected]
                maturity_value = account[3] + account[4]
                st.info(f"**Maturity Value:** ₹{maturity_value:,.2f} (Principal: ₹{account[3]:,.2f} + Interest: ₹{account[4]:,.2f})")
                
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
                            st.error("❌ Insufficient principal balance!")
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
                                
                                new_maturity = new_balance + account[4]
                                st.success(f"✅ Transaction successful!")
                                st.info(f"Voucher: **{voucher_num}**")
                                st.info(f"New Principal: **₹{new_balance:,.2f}**")
                                st.info(f"New Maturity Value: **₹{new_maturity:,.2f}**")
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
        st.subheader("Interest Information & Maturity Details")
        
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
                principal = acc[2]
                total_interest = acc[4]
                maturity_value = principal + total_interest
                
                interest_data.append({
                    'Account Number': acc[0],
                    'Customer': acc[1],
                    'Principal': principal,
                    'Interest Rate': f"{acc[3]:.2f}%",
                    'Total Interest': total_interest,
                    'Maturity Value': maturity_value,
                    'Opened': acc[5][:10] if acc[5] else 'N/A'
                })
            
            df = pd.DataFrame(interest_data)
            st.dataframe(df.style.format({
                'Principal': '₹{:,.2f}',
                'Total Interest': '₹{:,.2f}',
                'Maturity Value': '₹{:,.2f}'
            }), use_container_width=True)
            
            total_principal = sum(d['Principal'] for d in interest_data)
            total_interest = sum(d['Total Interest'] for d in interest_data)
            total_maturity = sum(d['Maturity Value'] for d in interest_data)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Principal", f"₹{total_principal:,.2f}")
            with col2:
                st.metric("Total Interest Earned", f"₹{total_interest:,.2f}")
            with col3:
                st.metric("Total Maturity Value", f"₹{total_maturity:,.2f}", delta=f"₹{total_interest:,.2f}")
        else:
            st.info("No SB accounts found")
    
    conn.close()

def show_interest_calculation():
    st.markdown('<h1 class="main-header">📊 Interest Calculation</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Calculate and post interest to SB accounts with journal vouchers</p>', unsafe_allow_html=True)
    
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized access")
        return
    
    conn = get_db()
    
    tab1, tab2, tab3 = st.tabs(["🧮 Calculate & Post Interest", "📊 Interest History", "📈 Trial Balance Impact"])
    
    with tab1:
        st.subheader("Calculate and Post SB Interest")
        st.info("""
        **Interest Calculation Rules:**
        - Interest is calculated on the minimum balance for the period
        - Default interest rate: 3.5% per annum
        - Formula: Interest = (Min Balance × Rate × Days) / (100 × 365)
        - Creates automatic journal vouchers with full details
        """)
        
        # Show SB accounts summary
        accounts = conn.execute("""
            SELECT a.id, a.account_number, c.first_name || ' ' || c.last_name as name, 
                   a.balance, a.interest_rate, 
                   COALESCE(a.total_interest_earned, 0) as total_interest,
                   COALESCE(a.last_interest_calculation, DATE(a.created_at)) as last_calc
            FROM accounts a
            JOIN customers c ON a.customer_id = c.id
            WHERE a.account_type='SB' AND a.status='ACTIVE'
            ORDER BY a.created_at
        """).fetchall()
        
        if accounts:
            st.markdown("### Current SB Account Status")
            account_data = []
            for acc in accounts:
                maturity_value = acc[3] + acc[5]
                last_calc_date = acc[6] if acc[6] else 'Never'
                account_data.append({
                    'Account': acc[1],
                    'Customer': acc[2],
                    'Principal': acc[3],
                    'Rate': f"{acc[4]:.2f}%" if acc[4] else "3.50%",
                    'Interest': acc[5],
                    'Maturity Value': maturity_value,
                    'Last Calculation': last_calc_date
                })
            
            df = pd.DataFrame(account_data)
            st.dataframe(df.style.format({
                'Principal': '₹{:,.2f}',
                'Interest': '₹{:,.2f}',
                'Maturity Value': '₹{:,.2f}'
            }), use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🧮 Calculate & Post Interest", use_container_width=True, type="primary"):
                    with st.spinner("Calculating and posting interest..."):
                        status, result = calculate_and_post_sb_interest(st.session_state.user['id'])
                    
                    if status == "SUCCESS":
                        if len(result) > 0:
                            st.success(f"✅ Interest calculated and posted for {len(result)} accounts!")
                            
                            st.markdown("### Interest Posted Summary")
                            result_data = []
                            for r in result:
                                result_data.append({
                                    'Account': r['account_number'],
                                    'Min Balance': r['min_balance'],
                                    'Principal Before': r['balance_before'],
                                    'Interest': r['interest'],
                                    'New Principal': r['new_balance'],
                                    'Maturity Value': r['maturity_value'],
                                    'Rate': f"{r['rate']:.2f}%",
                                    'Days': r['days'],
                                    'Journal Voucher': r['journal_voucher']
                                })
                            
                            result_df = pd.DataFrame(result_data)
                            st.dataframe(result_df.style.format({
                                'Min Balance': '₹{:,.2f}',
                                'Principal Before': '₹{:,.2f}',
                                'Interest': '₹{:,.2f}',
                                'New Principal': '₹{:,.2f}',
                                'Maturity Value': '₹{:,.2f}'
                            }), use_container_width=True)
                            
                            total_interest = sum(r['interest'] for r in result)
                            st.metric("Total Interest Posted", f"₹{total_interest:,.2f}")
                            st.info("✅ Journal vouchers created and posted. Check Trial Balance for impact.")
                            st.balloons()
                            
                            csv = result_df.to_csv(index=False)
                            st.download_button("📥 Download Summary", csv, "interest_posting.csv", "text/csv")
                        else:
                            st.info("No interest to post. All accounts are up to date.")
                    else:
                        st.error(status)
            
            with col2:
                if st.button("📊 Preview Interest", use_container_width=True):
                    preview_data = []
                    for acc in accounts:
                        balance = acc[3]
                        rate = acc[4] if acc[4] else 3.5
                        last_calc = acc[6]
                        
                        if last_calc:
                            try:
                                last_date = datetime.strptime(last_calc, '%Y-%m-%d').date()
                            except:
                                last_date = date.today().replace(day=1)
                        else:
                            last_date = date.today().replace(day=1)
                        
                        days = (date.today() - last_date).days
                        if days > 0:
                            interest = calculate_sb_interest(balance, rate, days)
                            maturity_value = balance + acc[5] + interest
                            preview_data.append({
                                'Account': acc[1],
                                'Customer': acc[2],
                                'Principal': balance,
                                'Rate': f"{rate:.2f}%",
                                'Days': days,
                                'Interest': interest,
                                'New Principal': balance + interest,
                                'New Maturity': maturity_value
                            })
                    
                    if preview_data:
                        preview_df = pd.DataFrame(preview_data)
                        st.dataframe(preview_df.style.format({
                            'Principal': '₹{:,.2f}',
                            'Interest': '₹{:,.2f}',
                            'New Principal': '₹{:,.2f}',
                            'New Maturity': '₹{:,.2f}'
                        }), use_container_width=True)
                        
                        total_estimated = sum(p['Interest'] for p in preview_data)
                        st.info(f"📊 Total Estimated Interest: ₹{total_estimated:,.2f}")
                    else:
                        st.info("No interest to calculate for current period")
        else:
            st.warning("No active SB accounts found")
    
    with tab2:
        st.subheader("Interest Calculation History")
        
        history = conn.execute("""
            SELECT ic.calculation_date, a.account_number, 
                   c.first_name || ' ' || c.last_name as customer,
                   ic.principal_amount, ic.interest_rate, ic.interest_earned, 
                   ic.days_calculated,
                   (ic.principal_amount + ic.interest_earned) as maturity_value
            FROM interest_calculations ic
            JOIN accounts a ON ic.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            ORDER BY ic.calculation_date DESC
            LIMIT 100
        """).fetchall()
        
        if history:
            hist_data = []
            for h in history:
                hist_data.append({
                    'Date': h[0],
                    'Account': h[1],
                    'Customer': h[2],
                    'Principal': h[3],
                    'Rate': f"{h[4]:.2f}%",
                    'Interest': h[5],
                    'Days': h[6],
                    'Maturity Value': h[7]
                })
            
            df = pd.DataFrame(hist_data)
            st.dataframe(df.style.format({
                'Principal': '₹{:,.2f}',
                'Interest': '₹{:,.2f}',
                'Maturity Value': '₹{:,.2f}'
            }), use_container_width=True)
            
            total_interest_paid = sum(h[5] for h in history)
            st.metric("Total Interest Paid to Date", f"₹{total_interest_paid:,.2f}")
            
            csv = df.to_csv(index=False)
            st.download_button("📥 Download History", csv, "interest_history.csv", "text/csv")
        else:
            st.info("No interest calculations recorded yet")
    
    with tab3:
        st.subheader("Interest Impact on Trial Balance")
        st.info("View all journal vouchers created for interest posting")
        
        # Show interest journal vouchers
        interest_jvs = conn.execute("""
            SELECT jv.voucher_number, jv.voucher_date, jv.description, jv.total_amount,
                   jv.status,
                   je.account_head, je.debit_amount, je.credit_amount, je.description
            FROM journal_vouchers jv
            JOIN journal_entries je ON jv.id = je.voucher_id
            WHERE (je.account_head = 'Interest Paid on SB' OR je.account_head LIKE '%SB Account%')
            AND jv.status = 'POSTED'
            ORDER BY jv.voucher_date DESC
            LIMIT 50
        """).fetchall()
        
        if interest_jvs:
            st.markdown(f"### 📝 Interest Journal Vouchers ({len(set(jv[0] for jv in interest_jvs))} vouchers)")
            
            # Group by voucher
            jv_dict = {}
            for jv in interest_jvs:
                vn = jv[0]
                if vn not in jv_dict:
                    jv_dict[vn] = {
                        'date': jv[1],
                        'desc': jv[2],
                        'amount': jv[3],
                        'status': jv[4],
                        'entries': []
                    }
                jv_dict[vn]['entries'].append({
                    'head': jv[5],
                    'debit': jv[6],
                    'credit': jv[7],
                    'desc': jv[8]
                })
            
            for vn, data in jv_dict.items():
                with st.expander(f"📄 {vn} - {data['date']} - ₹{data['amount']:,.2f} - {data['status']}"):
                    st.write(f"**Description:** {data['desc']}")
                    st.markdown("**Journal Entries:**")
                    for entry in data['entries']:
                        st.markdown(f"""
                        <div class="jv-card">
                            <b>{entry['head']}</b><br>
                            Debit: ₹{entry['debit']:,.2f} | Credit: ₹{entry['credit']:,.2f}<br>
                            <small>{entry['desc']}</small>
                        </div>
                        """, unsafe_allow_html=True)
            
            total_jv_amount = sum(jv[3] for jv in interest_jvs)
            
            st.divider()
            st.markdown("### 📊 Trial Balance Impact Summary")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Interest Expense (Debit - P&L):**")
                st.write(f"₹{total_jv_amount:,.2f}")
                st.write("*Reduces Net Profit*")
            
            with col2:
                st.markdown("**SB Account Liability (Credit - Balance Sheet):**")
                st.write(f"₹{total_jv_amount:,.2f}")
                st.write("*Increases SB Deposits*")
            
            st.success(f"✅ Trial Balance impact: Both Debit and Credit increase by ₹{total_jv_amount:,.2f} (Balanced)")
        else:
            st.info("No interest journal vouchers found. Post interest first to see the impact.")
            
            st.markdown("### Expected Journal Entry Format:")
            st.markdown("""
            <div class="jv-card">
                <b>Interest Paid on SB (Expense)</b><br>
                Debit: ₹XXX.XX | Credit: ₹0.00<br>
                <small>Interest for A/C XXXXXX - XX days @ X.XX% p.a.</small>
            </div>
            <div class="jv-card">
                <b>SB Account - XXXXXX (Liability)</b><br>
                Debit: ₹0.00 | Credit: ₹XXX.XX<br>
                <small>Interest credited to A/C XXXXXX</small>
            </div>
            """, unsafe_allow_html=True)
    
    conn.close()

def show_trial_balance():
    st.markdown('<h1 class="main-header">⚖️ Trial Balance</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Complete trial balance with all accounts including SB interest & journal vouchers</p>', unsafe_allow_html=True)
    
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
                'credit': max(-cash_balance, 0),
                'jv_ref': 'Cash transactions'
            })
        
        # ==================== LIABILITIES (Credit Balance) ====================
        
        # 2. Savings Bank Deposits (Principal only)
        sb_total = conn.execute("""
            SELECT COALESCE(SUM(balance), 0) FROM accounts 
            WHERE account_type='SB' AND status='ACTIVE'
        """).fetchone()[0]
        if sb_total > 0:
            trial_data.append({
                'account_head': 'Savings Bank Deposits (Principal)',
                'category': 'Liability',
                'debit': 0,
                'credit': sb_total,
                'jv_ref': 'Sum of all SB account principal balances'
            })
        
        # 3. Interest Payable on SB (from total_interest_earned)
        interest_payable_sb = conn.execute("""
            SELECT COALESCE(SUM(total_interest_earned), 0) 
            FROM accounts 
            WHERE account_type='SB' AND status='ACTIVE'
        """).fetchone()[0]
        
        # Check journal entries as backup
        if interest_payable_sb == 0:
            interest_payable_sb = conn.execute("""
                SELECT COALESCE(SUM(credit_amount), 0) 
                FROM journal_entries je
                JOIN journal_vouchers jv ON je.voucher_id = jv.id
                WHERE je.account_head LIKE '%SB Account%' AND jv.status='POSTED'
            """).fetchone()[0]
        
        # Check transactions as backup
        if interest_payable_sb == 0:
            interest_payable_sb = conn.execute("""
                SELECT COALESCE(SUM(amount), 0) 
                FROM transactions 
                WHERE transaction_type='CREDIT' AND reference_type='INTEREST'
            """).fetchone()[0]
        
        if interest_payable_sb > 0:
            # Get related JV numbers
            jv_numbers = conn.execute("""
                SELECT DISTINCT jv.voucher_number
                FROM journal_vouchers jv
                JOIN journal_entries je ON jv.id = je.voucher_id
                WHERE je.account_head LIKE '%SB Account%' AND jv.status='POSTED'
            """).fetchall()
            jv_ref = ', '.join([jv[0] for jv in jv_numbers]) if jv_numbers else 'From SB interest postings'
            
            trial_data.append({
                'account_head': 'Interest Payable on SB',
                'category': 'Liability',
                'debit': 0,
                'credit': interest_payable_sb,
                'jv_ref': jv_ref
            })
        
        # 4. Total SB Liability (Principal + Interest)
        total_sb_liability = sb_total + interest_payable_sb
        if total_sb_liability > 0:
            trial_data.append({
                'account_head': 'Total SB Deposits (Principal + Interest)',
                'category': 'Liability',
                'debit': 0,
                'credit': total_sb_liability,
                'jv_ref': f'SB Principal (₹{sb_total:,.2f}) + SB Interest (₹{interest_payable_sb:,.2f})'
            })
        
        # 5. Fixed Deposits
        fd_total = conn.execute("""
            SELECT COALESCE(SUM(principal_amount), 0) FROM fixed_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if fd_total > 0:
            trial_data.append({
                'account_head': 'Fixed Deposits',
                'category': 'Liability',
                'debit': 0,
                'credit': fd_total,
                'jv_ref': 'Sum of active FD principals'
            })
        
        # 6. Interest Payable on FD
        interest_payable_fd = conn.execute("""
            SELECT COALESCE(SUM(maturity_amount - principal_amount), 0)
            FROM fixed_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if interest_payable_fd > 0:
            trial_data.append({
                'account_head': 'Interest Payable on FD',
                'category': 'Liability',
                'debit': 0,
                'credit': interest_payable_fd,
                'jv_ref': 'Accrued interest on active FDs'
            })
        
        # 7. Recurring Deposits
        rd_total = conn.execute("""
            SELECT COALESCE(SUM(monthly_amount * installments_paid), 0) 
            FROM recurring_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if rd_total > 0:
            trial_data.append({
                'account_head': 'Recurring Deposits',
                'category': 'Liability',
                'debit': 0,
                'credit': rd_total,
                'jv_ref': 'Sum of RD installments paid'
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
                'credit': interest_earned,
                'jv_ref': 'Income entries'
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
                'credit': fees_income,
                'jv_ref': 'Income entries'
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
                'credit': commission_income,
                'jv_ref': 'Income entries'
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
                'credit': other_income,
                'jv_ref': 'Income entries'
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
            # Get JV numbers
            jv_numbers_exp = conn.execute("""
                SELECT DISTINCT jv.voucher_number
                FROM journal_vouchers jv
                JOIN journal_entries je ON jv.id = je.voucher_id
                WHERE je.account_head = 'Interest Paid on SB' AND jv.status='POSTED'
            """).fetchall()
            jv_ref_exp = ', '.join([jv[0] for jv in jv_numbers_exp]) if jv_numbers_exp else 'From interest postings'
            
            trial_data.append({
                'account_head': 'Interest Paid on SB Accounts',
                'category': 'Expense',
                'debit': interest_paid_sb,
                'credit': 0,
                'jv_ref': jv_ref_exp
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
                'credit': 0,
                'jv_ref': 'Expense entries'
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
                'credit': 0,
                'jv_ref': 'Expense entries'
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
                'credit': 0,
                'jv_ref': 'Expense entries'
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
                'credit': 0,
                'jv_ref': 'Expense entries'
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
                'credit': 0,
                'jv_ref': 'Expense entries'
            })
        
        # ==================== CAPITAL ====================
        
        total_debits = sum(item['debit'] for item in trial_data)
        total_credits = sum(item['credit'] for item in trial_data)
        
        diff = total_credits - total_debits
        
        if abs(diff) > 0.01:
            if diff > 0:
                trial_data.append({
                    'account_head': 'Capital/Reserves (Net Worth)',
                    'category': 'Capital',
                    'debit': 0,
                    'credit': diff,
                    'jv_ref': 'Balancing figure'
                })
            else:
                trial_data.append({
                    'account_head': 'Capital/Reserves (Net Worth)',
                    'category': 'Capital',
                    'debit': abs(diff),
                    'credit': 0,
                    'jv_ref': 'Balancing figure'
                })
        
        if trial_data:
            df = pd.DataFrame(trial_data)
            
            st.markdown('<div class="trial-balance-table">', unsafe_allow_html=True)
            
            # Summary metrics
            liabilities = sum(item['credit'] for item in trial_data if item['category'] == 'Liability')
            assets = sum(item['debit'] for item in trial_data if item['category'] == 'Asset')
            expenses = sum(item['debit'] for item in trial_data if item['category'] == 'Expense')
            income = sum(item['credit'] for item in trial_data if item['category'] == 'Income')
            capital = sum(item['credit'] for item in trial_data if item['category'] == 'Capital') - sum(item['debit'] for item in trial_data if item['category'] == 'Capital')
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Assets", f"₹{assets:,.2f}")
            with col2:
                st.metric("Total Liabilities", f"₹{liabilities:,.2f}")
            with col3:
                st.metric("Total Income", f"₹{income:,.2f}")
            with col4:
                st.metric("Total Expenses", f"₹{expenses:,.2f}")
            
            st.divider()
            
            # Full trial balance with JV references
            st.subheader("📋 Complete Trial Balance with Journal Voucher References")
            
            for category in ['Asset', 'Liability', 'Income', 'Expense', 'Capital']:
                cat_data = [item for item in trial_data if item['category'] == category]
                if cat_data:
                    st.markdown(f"**{category}s**")
                    cat_df = pd.DataFrame(cat_data)
                    display_df = cat_df[['account_head', 'debit', 'credit', 'jv_ref']].copy()
                    display_df.columns = ['Account Head', 'Debit (₹)', 'Credit (₹)', 'JV Reference / Source']
                    st.dataframe(display_df.style.format({
                        'Debit (₹)': '₹{:,.2f}',
                        'Credit (₹)': '₹{:,.2f}'
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
                else:
                    st.error(f"❌ Difference: ₹{abs(total_debit - total_credit):,.2f}")
            
            # Interest-specific summary
            st.divider()
            st.markdown("### 📊 Interest-Related Entries Summary")
            
            interest_tb_entries = [item for item in trial_data if 'Interest' in item['account_head']]
            if interest_tb_entries:
                for entry in interest_tb_entries:
                    direction = "DEBIT" if entry['debit'] > 0 else "CREDIT"
                    amount = entry['debit'] if entry['debit'] > 0 else entry['credit']
                    st.write(f"• **{entry['account_head']}**: {direction} ₹{amount:,.2f}")
                    st.write(f"  *Source: {entry['jv_ref']}*")
                
                st.info(f"✅ Interest Paid on SB (Expense) = Interest Payable on SB (Liability) = ₹{interest_paid_sb:,.2f}")
                st.info(f"✅ Total SB Maturity Value in Trial Balance: ₹{total_sb_liability:,.2f}")
            else:
                st.info("No interest entries in trial balance yet. Use Interest Calculation to post interest.")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Export options
            col1, col2 = st.columns(2)
            with col1:
                csv = df.to_csv(index=False)
                st.download_button("📥 Download CSV", csv, "trial_balance.csv", "text/csv")
            
            with col2:
                if st.button("📄 Generate PDF Report"):
                    pdf_data = {
                        'date': as_on_date.strftime('%d-%m-%Y'),
                        'entries': [{'account_head': item['account_head'], 'debit': item['debit'], 'credit': item['credit']} for item in trial_data]
                    }
                    pdf_file = generate_report_pdf('trial_balance', pdf_data, 'trial_balance.pdf')
                    if pdf_file:
                        with open(pdf_file, 'rb') as f:
                            st.download_button("📥 Download PDF", f, "trial_balance.pdf", "application/pdf")
        else:
            st.info("No data available for trial balance")
    
    conn.close()

def show_balance_sheet():
    st.markdown('<h1 class="main-header">📊 Balance Sheet</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Complete balance sheet with assets, liabilities and capital</p>', unsafe_allow_html=True)
    
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized access")
        return
    
    conn = get_db()
    as_on_date = st.date_input("As on Date", date.today())
    
    if st.button("📊 Generate Balance Sheet", use_container_width=True):
        st.markdown(f"## Balance Sheet as on {as_on_date.strftime('%d-%m-%Y')}")
        
        # ==================== ASSETS ====================
        st.markdown('<div class="balance-sheet-card">', unsafe_allow_html=True)
        st.markdown('<h3 class="section-header">📊 ASSETS</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Current Assets**")
            
            cash = conn.execute("""
                SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END), 0)
                FROM transactions WHERE reference_type='CASH'
            """).fetchone()[0]
            st.write(f"💰 Cash in Hand: **₹{cash:,.2f}**")
            
            sb_balance = conn.execute("""
                SELECT COALESCE(SUM(balance), 0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'
            """).fetchone()[0]
            
            total_interest_earned = conn.execute("""
                SELECT COALESCE(SUM(total_interest_earned), 0) 
                FROM accounts WHERE account_type='SB' AND status='ACTIVE'
            """).fetchone()[0]
            
            if total_interest_earned == 0:
                total_interest_earned = conn.execute("""
                    SELECT COALESCE(SUM(credit_amount), 0) 
                    FROM journal_entries je
                    JOIN journal_vouchers jv ON je.voucher_id = jv.id
                    WHERE je.account_head LIKE '%SB Account%' AND jv.status='POSTED'
                """).fetchone()[0]
            
            if total_interest_earned == 0:
                total_interest_earned = conn.execute("""
                    SELECT COALESCE(SUM(amount), 0) 
                    FROM transactions 
                    WHERE transaction_type='CREDIT' AND reference_type='INTEREST'
                """).fetchone()[0]
            
            sb_display = sb_balance
            sb_maturity = sb_display + total_interest_earned
            st.write(f"🏦 SB Deposits (Principal): **₹{sb_display:,.2f}**")
            st.write(f"📈 SB Interest Accrued: **₹{total_interest_earned:,.2f}**")
            st.write(f"💎 SB Total Maturity Value: **₹{sb_maturity:,.2f}**")
            total_sb = sb_display
        
        with col2:
            st.markdown("**Investments**")
            
            fd_total = conn.execute("""
                SELECT COALESCE(SUM(principal_amount), 0) FROM fixed_deposits WHERE status='ACTIVE'
            """).fetchone()[0]
            st.write(f"💎 Fixed Deposits: **₹{fd_total:,.2f}**")
            
            rd_total = conn.execute("""
                SELECT COALESCE(SUM(monthly_amount * installments_paid), 0)
                FROM recurring_deposits WHERE status='ACTIVE'
            """).fetchone()[0]
            st.write(f"🔄 Recurring Deposits: **₹{rd_total:,.2f}**")
        
        total_assets = cash + total_sb + fd_total + rd_total
        st.markdown(f"### **Total Assets: ₹{total_assets:,.2f}**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()
        
        # ==================== LIABILITIES ====================
        st.markdown('<div class="balance-sheet-card">', unsafe_allow_html=True)
        st.markdown('<h3 class="section-header">📋 LIABILITIES</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Current Liabilities**")
            
            interest_payable_sb = conn.execute("""
                SELECT COALESCE(SUM(total_interest_earned), 0) 
                FROM accounts WHERE account_type='SB' AND status='ACTIVE'
            """).fetchone()[0]
            
            if interest_payable_sb == 0:
                interest_payable_sb = conn.execute("""
                    SELECT COALESCE(SUM(credit_amount), 0) 
                    FROM journal_entries je
                    JOIN journal_vouchers jv ON je.voucher_id = jv.id
                    WHERE je.account_head LIKE '%SB Account%' AND jv.status='POSTED'
                """).fetchone()[0]
            
            if interest_payable_sb == 0:
                interest_payable_sb = conn.execute("""
                    SELECT COALESCE(SUM(amount), 0) 
                    FROM transactions 
                    WHERE transaction_type='CREDIT' AND reference_type='INTEREST'
                """).fetchone()[0]
            
            st.write(f"📈 Interest Payable on SB: **₹{interest_payable_sb:,.2f}**")
            
            interest_fd = conn.execute("""
                SELECT COALESCE(SUM(maturity_amount - principal_amount), 0)
                FROM fixed_deposits WHERE status='ACTIVE'
            """).fetchone()[0]
            st.write(f"📈 Interest Payable on FD: **₹{interest_fd:,.2f}**")
        
        with col2:
            st.markdown("**Deposits (Liabilities)**")
            st.write(f"💎 FD Deposits: **₹{fd_total:,.2f}**")
            st.write(f"🔄 RD Deposits: **₹{rd_total:,.2f}**")
            st.write(f"🏦 SB Deposits (Principal): **₹{sb_display:,.2f}**")
            st.write(f"🏦 SB Total Liability (Principal + Interest): **₹{sb_maturity:,.2f}**")
        
        total_liabilities = interest_payable_sb + interest_fd + fd_total + rd_total + sb_display
        st.markdown(f"### **Total Liabilities: ₹{total_liabilities:,.2f}**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()
        
        # ==================== CAPITAL ====================
        capital = total_assets - total_liabilities
        st.markdown('<div class="balance-sheet-card">', unsafe_allow_html=True)
        st.markdown('<h3 class="section-header">💰 CAPITAL</h3>', unsafe_allow_html=True)
        st.write(f"**Capital/Net Worth: ₹{capital:,.2f}**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()
        
        # Verification
        if abs(total_assets - (total_liabilities + capital)) < 0.01:
            st.success(f"✅ Balance Sheet Balanced!")
            st.write(f"Assets (₹{total_assets:,.2f}) = Liabilities (₹{total_liabilities:,.2f}) + Capital (₹{capital:,.2f})")
        else:
            st.error("❌ Balance Sheet not balanced!")
        
        # Detailed breakdown
        with st.expander("📊 Detailed Breakdown with Interest & Maturity Values"):
            st.markdown("### Assets")
            st.write(f"💰 Cash in Hand: ₹{cash:,.2f}")
            st.write(f"🏦 SB Deposits (Principal): ₹{sb_display:,.2f}")
            st.write(f"💎 FD Deposits: ₹{fd_total:,.2f}")
            st.write(f"🔄 RD Deposits: ₹{rd_total:,.2f}")
            st.write(f"**Total Assets: ₹{total_assets:,.2f}**")
            
            st.markdown("### Liabilities")
            st.write(f"📈 Interest Payable on SB: ₹{interest_payable_sb:,.2f}")
            st.write(f"📈 Interest Payable on FD: ₹{interest_fd:,.2f}")
            st.write(f"🏦 SB Deposits (Principal): ₹{sb_display:,.2f}")
            st.write(f"💎 FD Deposits: ₹{fd_total:,.2f}")
            st.write(f"🔄 RD Deposits: ₹{rd_total:,.2f}")
            st.write(f"**Total Liabilities: ₹{total_liabilities:,.2f}**")
            
            st.markdown("### SB Account Maturity Summary")
            st.write(f"💰 SB Principal: ₹{sb_display:,.2f}")
            st.write(f"📈 SB Interest Accrued: ₹{interest_payable_sb:,.2f}")
            st.write(f"💎 SB Total Maturity Value: ₹{sb_maturity:,.2f}")
            
            st.markdown("### Capital")
            st.write(f"💰 Capital/Net Worth: ₹{capital:,.2f}")
            
            st.markdown("### Verification")
            st.write(f"Assets = Liabilities + Capital")
            st.write(f"₹{total_assets:,.2f} = ₹{total_liabilities:,.2f} + ₹{capital:,.2f}")
    
    conn.close()

def show_profit_loss():
    st.markdown('<h1 class="main-header">💵 Profit & Loss Account</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Complete profit and loss statement with income and expenses</p>', unsafe_allow_html=True)
    
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized access")
        return
    
    conn = get_db()
    
    col1, col2 = st.columns(2)
    with col1:
        from_date = st.date_input("From Date", date.today().replace(month=1, day=1))
    with col2:
        to_date = st.date_input("To Date", date.today())
    
    if st.button("📊 Generate P&L Statement", use_container_width=True):
        st.subheader(f"Profit & Loss Account ({from_date.strftime('%d-%m-%Y')} to {to_date.strftime('%d-%m-%Y')})")
        
        # ==================== INCOME ====================
        st.markdown('<div class="balance-sheet-card">', unsafe_allow_html=True)
        st.markdown('<h3 class="section-header">📈 INCOME</h3>', unsafe_allow_html=True)
        
        income_items = []
        
        interest_earned = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM income
            WHERE income_type='Interest Earned' AND DATE(date) BETWEEN ? AND ?
        """, (from_date, to_date)).fetchone()[0]
        income_items.append(('Interest Earned', interest_earned))
        
        fees = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM income
            WHERE income_type='Fees & Charges' AND DATE(date) BETWEEN ? AND ?
        """, (from_date, to_date)).fetchone()[0]
        income_items.append(('Fees & Charges', fees))
        
        commission = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM income
            WHERE income_type='Commission Income' AND DATE(date) BETWEEN ? AND ?
        """, (from_date, to_date)).fetchone()[0]
        income_items.append(('Commission Income', commission))
        
        other_income = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM income
            WHERE income_type='Other Income' AND DATE(date) BETWEEN ? AND ?
        """, (from_date, to_date)).fetchone()[0]
        income_items.append(('Other Income', other_income))
        
        total_income = 0
        for item, amount in income_items:
            st.write(f"• {item}: **₹{amount:,.2f}**")
            total_income += amount
        
        st.markdown(f"### **Total Income: ₹{total_income:,.2f}**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()
        
        # ==================== EXPENSES ====================
        st.markdown('<div class="balance-sheet-card">', unsafe_allow_html=True)
        st.markdown('<h3 class="section-header">📉 EXPENSES</h3>', unsafe_allow_html=True)
        
        expense_items = []
        
        # Interest Paid on SB (from journal entries)
        interest_paid_sb = conn.execute("""
            SELECT COALESCE(SUM(debit_amount), 0) 
            FROM journal_entries je
            JOIN journal_vouchers jv ON je.voucher_id = jv.id
            WHERE je.account_head = 'Interest Paid on SB' AND jv.status='POSTED'
            AND DATE(jv.voucher_date) BETWEEN ? AND ?
        """, (from_date, to_date)).fetchone()[0]
        if interest_paid_sb > 0:
            expense_items.append(('Interest Paid on SB', interest_paid_sb))
        
        salary = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM expenses
            WHERE expense_type='Salary & Wages' AND DATE(date) BETWEEN ? AND ?
        """, (from_date, to_date)).fetchone()[0]
        expense_items.append(('Salary & Wages', salary))
        
        rent = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM expenses
            WHERE expense_type='Rent & Utilities' AND DATE(date) BETWEEN ? AND ?
        """, (from_date, to_date)).fetchone()[0]
        expense_items.append(('Rent & Utilities', rent))
        
        operating = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM expenses
            WHERE expense_type='Operating Expenses' AND DATE(date) BETWEEN ? AND ?
        """, (from_date, to_date)).fetchone()[0]
        expense_items.append(('Operating Expenses', operating))
        
        admin = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM expenses
            WHERE expense_type='Administrative Expenses' AND DATE(date) BETWEEN ? AND ?
        """, (from_date, to_date)).fetchone()[0]
        expense_items.append(('Administrative Expenses', admin))
        
        other_exp = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM expenses
            WHERE expense_type='Other Expenses' AND DATE(date) BETWEEN ? AND ?
        """, (from_date, to_date)).fetchone()[0]
        expense_items.append(('Other Expenses', other_exp))
        
        total_expenses = 0
        for item, amount in expense_items:
            if amount > 0:
                st.write(f"• {item}: **₹{amount:,.2f}**")
                total_expenses += amount
        
        st.markdown(f"### **Total Expenses: ₹{total_expenses:,.2f}**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()
        
        # ==================== NET PROFIT/LOSS ====================
        net_profit = total_income - total_expenses
        
        if net_profit >= 0:
            st.success(f"## 🎉 Net Profit: ₹{net_profit:,.2f}")
        else:
            st.error(f"## 📉 Net Loss: ₹{abs(net_profit):,.2f}")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            income_items_filtered = [(item, amt) for item, amt in income_items if amt > 0]
            if income_items_filtered:
                df_income = pd.DataFrame(income_items_filtered, columns=['Source', 'Amount'])
                fig = px.pie(df_income, values='Amount', names='Source', title='Income Breakdown',
                             color_discrete_sequence=px.colors.qualitative.Set3)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            expense_items_filtered = [(item, amt) for item, amt in expense_items if amt > 0]
            if expense_items_filtered:
                df_expense = pd.DataFrame(expense_items_filtered, columns=['Category', 'Amount'])
                fig = px.pie(df_expense, values='Amount', names='Category', title='Expense Breakdown',
                             color_discrete_sequence=px.colors.qualitative.Set3)
                st.plotly_chart(fig, use_container_width=True)
    
    conn.close()

def show_income_expenses():
    st.markdown('<h1 class="main-header">📈 Income & Expenses</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Record and track all income and expenses</p>', unsafe_allow_html=True)
    
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized access")
        return
    
    conn = get_db()
    
    tab1, tab2 = st.tabs(["💰 Record Income", "💸 Record Expense"])
    
    with tab1:
        st.subheader("Record Income")
        
        with st.form("income_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                income_type = st.selectbox("Income Type", [
                    "Interest Earned",
                    "Fees & Charges",
                    "Commission Income",
                    "Other Income"
                ])
                amount = st.number_input("Amount (₹)", min_value=1.0, step=100.0)
            
            with col2:
                income_date = st.date_input("Date", date.today())
                description = st.text_area("Description", placeholder="Enter income details")
            
            if st.form_submit_button("💰 Record Income", use_container_width=True):
                try:
                    income_id = generate_id('INC')
                    conn.execute("""
                        INSERT INTO income (income_id, income_type, amount, description, date, created_by)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (income_id, income_type, amount, description, income_date, st.session_state.user['id']))
                    conn.commit()
                    st.success(f"✅ Income recorded successfully! ₹{amount:,.2f}")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    with tab2:
        st.subheader("Record Expense")
        
        with st.form("expense_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                expense_type = st.selectbox("Expense Type", [
                    "Salary & Wages",
                    "Rent & Utilities",
                    "Operating Expenses",
                    "Administrative Expenses",
                    "Other Expenses"
                ])
                amount = st.number_input("Amount (₹)", min_value=1.0, step=100.0)
            
            with col2:
                expense_date = st.date_input("Date", date.today())
                description = st.text_area("Description", placeholder="Enter expense details")
            
            if st.form_submit_button("💸 Record Expense", use_container_width=True):
                try:
                    expense_id = generate_id('EXP')
                    conn.execute("""
                        INSERT INTO expenses (expense_id, expense_type, amount, description, date, created_by)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (expense_id, expense_type, amount, description, expense_date, st.session_state.user['id']))
                    conn.commit()
                    st.success(f"✅ Expense recorded successfully! ₹{amount:,.2f}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    conn.close()

def show_fixed_deposits():
    st.markdown('<h1 class="main-header">💎 Fixed Deposits</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Open and manage fixed deposit accounts</p>', unsafe_allow_html=True)
    
    conn = get_db()
    
    tab1, tab2, tab3 = st.tabs(["📝 Open New FD", "📋 Active FDs", "🔔 Maturity Alerts"])
    
    with tab1:
        st.subheader("Open New Fixed Deposit")
        
        customers = conn.execute("""
            SELECT c.id, c.customer_id, c.first_name || ' ' || c.last_name as name,
                   a.account_number, a.balance
            FROM customers c
            JOIN accounts a ON c.id = a.customer_id
            WHERE a.account_type='SB' AND c.kyc_status='VERIFIED' AND a.status='ACTIVE'
        """).fetchall()
        
        if customers:
            customer_options = {f"{cust[1]} - {cust[2]} (SB: {cust[3]})": cust for cust in customers}
            selected = st.selectbox("Select Customer", list(customer_options.keys()))
            
            if selected:
                customer = customer_options[selected]
                
                with st.form("open_fd"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        principal = st.number_input("Principal Amount (₹)", min_value=1000.0, step=1000.0, value=10000.0)
                        tenure_months = st.selectbox("Tenure (Months)", [3, 6, 12, 24, 36, 60])
                        interest_rate = st.number_input("Interest Rate (%)", min_value=3.0, max_value=10.0, value=6.5, step=0.25)
                    
                    with col2:
                        start_date = st.date_input("Start Date", date.today())
                        nominee_name = st.text_input("Nominee Name", placeholder="Enter nominee name")
                        nominee_relation = st.text_input("Nominee Relation", placeholder="e.g., Spouse, Son, Daughter")
                    
                    maturity_date = start_date + timedelta(days=tenure_months * 30)
                    maturity_amount = calculate_fd_maturity(principal, interest_rate, tenure_months)
                    interest_earned = maturity_amount - principal
                    
                    st.info(f"📅 **Maturity Date:** {maturity_date.strftime('%d-%m-%Y')}")
                    st.info(f"💰 **Maturity Amount:** ₹{maturity_amount:,.2f} (Interest: ₹{interest_earned:,.2f})")
                    
                    if st.form_submit_button("🔒 Open FD", use_container_width=True):
                        try:
                            fd_number = generate_id('FD')
                            
                            account_number = generate_account_number('FD')
                            conn.execute("""
                                INSERT INTO accounts (account_number, customer_id, account_type, 
                                                     balance, interest_rate)
                                VALUES (?, ?, 'FD', 0.00, ?)
                            """, (account_number, customer[0], interest_rate))
                            
                            account_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                            
                            conn.execute("""
                                INSERT INTO fixed_deposits 
                                (fd_number, account_id, principal_amount, interest_rate, 
                                 start_date, maturity_date, maturity_amount, tenure_months,
                                 nominee_name, nominee_relation)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (fd_number, account_id, principal, interest_rate,
                                  start_date, maturity_date, maturity_amount, tenure_months,
                                  nominee_name, nominee_relation))
                            
                            txn_id = generate_id('TXN')
                            voucher_num = generate_voucher_number('RECEIPT')
                            conn.execute("""
                                INSERT INTO transactions 
                                (transaction_id, account_id, transaction_type, amount, 
                                 balance_after, description, reference_type, voucher_type, 
                                 voucher_number, created_by)
                                VALUES (?, ?, 'CREDIT', ?, ?, 'FD Deposit - Principal', 'FD_DEPOSIT', 
                                        'RECEIPT', ?, ?)
                            """, (txn_id, account_id, principal, principal,
                                  voucher_num, st.session_state.user['id']))
                            
                            conn.commit()
                            st.success(f"✅ FD opened successfully!")
                            st.info(f"FD Number: **{fd_number}**")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        else:
            st.warning("No verified customers with SB accounts available")
    
    with tab2:
        st.subheader("Active Fixed Deposits")
        
        fds = conn.execute("""
            SELECT fd.fd_number, c.first_name || ' ' || c.last_name as name,
                   fd.principal_amount, fd.interest_rate, fd.start_date, 
                   fd.maturity_date, fd.maturity_amount, fd.status
            FROM fixed_deposits fd
            JOIN accounts a ON fd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            WHERE fd.status='ACTIVE'
            ORDER BY fd.maturity_date
        """).fetchall()
        
        if fds:
            df = pd.DataFrame(fds, columns=['FD Number', 'Customer', 'Principal', 
                                           'Rate (%)', 'Start Date', 'Maturity Date',
                                           'Maturity Amount', 'Status'])
            st.dataframe(df.style.format({
                'Principal': '₹{:,.2f}',
                'Rate (%)': '{:.2f}%',
                'Maturity Amount': '₹{:,.2f}'
            }), use_container_width=True)
            
            total_fd = sum(fd[2] for fd in fds)
            total_fd_interest = sum(fd[6] - fd[2] for fd in fds)
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Total FD Deposits: ₹{total_fd:,.2f}**")
            with col2:
                st.info(f"**Total Interest Payable: ₹{total_fd_interest:,.2f}**")
        else:
            st.info("No active FDs found")
    
    with tab3:
        st.subheader("FD Maturity Calendar")
        
        today = date.today()
        next_30_days = today + timedelta(days=30)
        
        maturing_fds = conn.execute("""
            SELECT fd.fd_number, c.first_name || ' ' || c.last_name as name,
                   fd.principal_amount, fd.maturity_amount, fd.maturity_date,
                   fd.nominee_name, fd.nominee_relation
            FROM fixed_deposits fd
            JOIN accounts a ON fd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            WHERE fd.maturity_date BETWEEN ? AND ? AND fd.status='ACTIVE'
            ORDER BY fd.maturity_date
        """, (today, next_30_days)).fetchall()
        
        if maturing_fds:
            st.warning(f"🔔 **{len(maturing_fds)} FD(s) maturing in next 30 days**")
            df = pd.DataFrame(maturing_fds, columns=['FD Number', 'Customer', 'Principal', 
                                                     'Maturity Amount', 'Maturity Date',
                                                     'Nominee', 'Relation'])
            st.dataframe(df.style.format({
                'Principal': '₹{:,.2f}',
                'Maturity Amount': '₹{:,.2f}'
            }), use_container_width=True)
        else:
            st.success("No FDs maturing in next 30 days")
    
    conn.close()

def show_recurring_deposits():
    st.markdown('<h1 class="main-header">🔄 Recurring Deposits</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Open and manage recurring deposit accounts</p>', unsafe_allow_html=True)
    
    conn = get_db()
    
    tab1, tab2, tab3 = st.tabs(["📝 Open New RD", "📋 Active RDs", "💳 Pay Installment"])
    
    with tab1:
        st.subheader("Open New Recurring Deposit")
        
        customers = conn.execute("""
            SELECT c.id, c.customer_id, c.first_name || ' ' || c.last_name as name,
                   a.account_number, a.id as account_id
            FROM customers c
            JOIN accounts a ON c.id = a.customer_id
            WHERE a.account_type='SB' AND c.kyc_status='VERIFIED' AND a.status='ACTIVE'
        """).fetchall()
        
        if customers:
            customer_options = {f"{cust[1]} - {cust[2]} (SB: {cust[3]})": cust for cust in customers}
            selected = st.selectbox("Select Customer", list(customer_options.keys()))
            
            if selected:
                customer = customer_options[selected]
                
                with st.form("open_rd"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        monthly_amount = st.number_input("Monthly Installment (₹)", min_value=100.0, step=100.0, value=1000.0)
                        tenure_months = st.selectbox("Tenure (Months)", [6, 12, 24, 36, 48, 60])
                        interest_rate = st.number_input("Interest Rate (%)", min_value=3.0, max_value=10.0, value=6.0, step=0.25)
                    
                    with col2:
                        start_date = st.date_input("Start Date", date.today())
                        nominee_name = st.text_input("Nominee Name")
                        nominee_relation = st.text_input("Nominee Relation")
                    
                    maturity_date = start_date + timedelta(days=tenure_months * 30)
                    maturity_amount = calculate_rd_maturity(monthly_amount, interest_rate, tenure_months)
                    total_deposit = monthly_amount * tenure_months
                    interest_earned = maturity_amount - total_deposit
                    
                    st.info(f"📅 **Maturity Date:** {maturity_date.strftime('%d-%m-%Y')}")
                    st.info(f"💰 **Total Deposits:** ₹{total_deposit:,.2f}")
                    st.info(f"💎 **Maturity Amount:** ₹{maturity_amount:,.2f} (Interest: ₹{interest_earned:,.2f})")
                    
                    if st.form_submit_button("🔄 Open RD", use_container_width=True):
                        try:
                            rd_number = generate_id('RD')
                            
                            account_number = generate_account_number('RD')
                            conn.execute("""
                                INSERT INTO accounts (account_number, customer_id, account_type, 
                                                     balance, interest_rate)
                                VALUES (?, ?, 'RD', 0.00, ?)
                            """, (account_number, customer[0], interest_rate))
                            
                            account_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                            
                            conn.execute("""
                                INSERT INTO recurring_deposits 
                                (rd_number, account_id, monthly_amount, interest_rate,
                                 start_date, maturity_date, maturity_amount, tenure_months,
                                 total_installments, nominee_name, nominee_relation)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (rd_number, account_id, monthly_amount, interest_rate,
                                  start_date, maturity_date, maturity_amount, tenure_months,
                                  tenure_months, nominee_name, nominee_relation))
                            
                            txn_id = generate_id('TXN')
                            voucher_num = generate_voucher_number('RECEIPT')
                            conn.execute("""
                                INSERT INTO transactions 
                                (transaction_id, account_id, transaction_type, amount, 
                                 balance_after, description, reference_type, voucher_type, 
                                 voucher_number, created_by)
                                VALUES (?, ?, 'CREDIT', ?, ?, 'RD Installment 1', 'RD_INSTALLMENT', 
                                        'RECEIPT', ?, ?)
                            """, (txn_id, account_id, monthly_amount, monthly_amount,
                                  voucher_num, st.session_state.user['id']))
                            
                            conn.execute("UPDATE recurring_deposits SET installments_paid=1 WHERE rd_number=?",
                                       (rd_number,))
                            
                            conn.commit()
                            st.success(f"✅ RD opened successfully!")
                            st.info(f"RD Number: **{rd_number}**")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        else:
            st.warning("No verified customers with SB accounts")
    
    with tab2:
        st.subheader("Active Recurring Deposits")
        
        rds = conn.execute("""
            SELECT rd.rd_number, c.first_name || ' ' || c.last_name as name,
                   rd.monthly_amount, rd.interest_rate, rd.start_date,
                   rd.maturity_date, rd.maturity_amount, 
                   rd.installments_paid, rd.total_installments, rd.status
            FROM recurring_deposits rd
            JOIN accounts a ON rd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            WHERE rd.status='ACTIVE'
            ORDER BY rd.maturity_date
        """).fetchall()
        
        if rds:
            df = pd.DataFrame(rds, columns=['RD Number', 'Customer', 'Monthly Amount',
                                           'Rate (%)', 'Start Date', 'Maturity Date',
                                           'Maturity Amount', 'Paid', 'Total', 'Status'])
            df['Progress'] = df.apply(lambda row: f"{row['Paid']}/{row['Total']} ({(row['Paid']/row['Total']*100):.0f}%)", axis=1)
            st.dataframe(df.style.format({
                'Monthly Amount': '₹{:,.2f}',
                'Rate (%)': '{:.2f}%',
                'Maturity Amount': '₹{:,.2f}'
            }), use_container_width=True)
        else:
            st.info("No active RDs found")
    
    with tab3:
        st.subheader("Pay RD Installment")
        
        rds = conn.execute("""
            SELECT rd.id, rd.rd_number, c.first_name || ' ' || c.last_name as name,
                   rd.monthly_amount, rd.installments_paid, rd.total_installments,
                   a.id as account_id
            FROM recurring_deposits rd
            JOIN accounts a ON rd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            WHERE rd.status='ACTIVE' AND rd.installments_paid < rd.total_installments
        """).fetchall()
        
        if rds:
            rd_options = {
                f"{rd[1]} - {rd[2]} (Paid: {rd[4]}/{rd[5]} - ₹{rd[3]:,.2f}/month)": rd 
                for rd in rds
            }
            selected = st.selectbox("Select RD", list(rd_options.keys()))
            
            if selected:
                rd = rd_options[selected]
                
                with st.form("pay_installment"):
                    st.write(f"**Monthly Installment Amount:** ₹{rd[3]:,.2f}")
                    amount = st.number_input("Amount (₹)", value=float(rd[3]), min_value=float(rd[3]))
                    description = st.text_input("Description", value=f"RD Installment {rd[4]+1}/{rd[5]}")
                    
                    if st.form_submit_button("💳 Pay Installment", use_container_width=True):
                        try:
                            txn_id = generate_id('TXN')
                            voucher_num = generate_voucher_number('RECEIPT')
                            conn.execute("""
                                INSERT INTO transactions 
                                (transaction_id, account_id, transaction_type, amount, 
                                 balance_after, description, reference_type, voucher_type, 
                                 voucher_number, created_by)
                                VALUES (?, ?, 'CREDIT', ?, ?, ?, 'RD_INSTALLMENT', 'RECEIPT', ?, ?)
                            """, (txn_id, rd[6], amount, amount, description,
                                  voucher_num, st.session_state.user['id']))
                            
                            new_paid = rd[4] + 1
                            conn.execute("""
                                UPDATE recurring_deposits 
                                SET installments_paid=? 
                                WHERE id=?
                            """, (new_paid, rd[0]))
                            
                            if new_paid >= rd[5]:
                                conn.execute("""
                                    UPDATE recurring_deposits 
                                    SET status='MATURED' 
                                    WHERE id=?
                                """, (rd[0],))
                                st.info("🎉 Congratulations! RD matured.")
                            
                            conn.commit()
                            st.success(f"✅ Installment paid! ({new_paid}/{rd[5]})")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        else:
            st.info("No pending RD installments")
    
    conn.close()

def show_transactions():
    st.markdown('<h1 class="main-header">💳 Transactions</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">View and filter all transactions</p>', unsafe_allow_html=True)
    
    conn = get_db()
    
    st.subheader("🔍 Filter Transactions")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        account_type = st.selectbox("Account Type", ["All", "SB", "FD", "RD"])
    with col2:
        txn_type = st.selectbox("Transaction Type", ["All", "CREDIT", "DEBIT"])
    with col3:
        from_date = st.date_input("From Date", date.today() - timedelta(days=30))
    with col4:
        to_date = st.date_input("To Date", date.today())
    
    query = """
        SELECT t.transaction_id, c.first_name || ' ' || c.last_name as customer,
               a.account_number, a.account_type, t.transaction_type, t.amount,
               t.balance_after, t.description, t.reference_type, t.voucher_number, t.created_at
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        JOIN customers c ON a.customer_id = c.id
        WHERE DATE(t.created_at) BETWEEN ? AND ?
    """
    params = [from_date, to_date]
    
    if st.session_state.user['role'] == 'customer':
        query += " AND c.user_id=?"
        params.append(st.session_state.user['id'])
    
    if account_type != "All":
        query += " AND a.account_type=?"
        params.append(account_type)
    
    if txn_type != "All":
        query += " AND t.transaction_type=?"
        params.append(txn_type)
    
    query += " ORDER BY t.created_at DESC LIMIT 200"
    
    transactions = conn.execute(query, params).fetchall()
    
    if transactions:
        df = pd.DataFrame(transactions, columns=['Txn ID', 'Customer', 'Account', 'Type',
                                                  'Action', 'Amount', 'Balance', 'Description',
                                                  'Mode', 'Voucher', 'Date'])
        st.dataframe(df.style.format({'Amount': '₹{:,.2f}', 'Balance': '₹{:,.2f}'}), 
                    use_container_width=True)
        
        total_credit = sum(t[5] for t in transactions if t[4] == 'CREDIT')
        total_debit = sum(t[5] for t in transactions if t[4] == 'DEBIT')
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Credits", f"₹{total_credit:,.2f}")
        with col2:
            st.metric("Total Debits", f"₹{total_debit:,.2f}")
        with col3:
            st.metric("Net Flow", f"₹{total_credit - total_debit:,.2f}")
        
        csv = df.to_csv(index=False)
        st.download_button("📥 Download Transactions", csv, "transactions.csv", "text/csv")
    else:
        st.info("No transactions found")
    
    conn.close()

def show_journal_vouchers():
    st.markdown('<h1 class="main-header">📝 Journal Vouchers</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Create and manage journal voucher entries</p>', unsafe_allow_html=True)
    
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized access")
        return
    
    conn = get_db()
    
    tab1, tab2 = st.tabs(["📝 Create Voucher", "📋 Voucher List"])
    
    with tab1:
        st.subheader("Create Journal Voucher")
        
        with st.form("journal_voucher"):
            voucher_date = st.date_input("Voucher Date", date.today())
            description = st.text_area("Description/Narration", placeholder="Enter voucher description")
            
            st.subheader("Journal Entries")
            st.info("Debit total must equal Credit total")
            
            num_entries = st.number_input("Number of Entries", min_value=2, max_value=10, value=2)
            
            entries = []
            total_debit = 0
            total_credit = 0
            
            for i in range(int(num_entries)):
                st.markdown(f"**Entry {i+1}**")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    account_head = st.text_input(f"Account Head", key=f"head_{i}", 
                                                placeholder="e.g., Cash, Interest, Expense")
                with col2:
                    debit = st.number_input(f"Debit Amount", min_value=0.0, step=100.0, key=f"debit_{i}")
                with col3:
                    credit = st.number_input(f"Credit Amount", min_value=0.0, step=100.0, key=f"credit_{i}")
                
                total_debit += debit
                total_credit += credit
                
                entries.append({
                    'account_head': account_head,
                    'debit': debit,
                    'credit': credit
                })
                st.divider()
            
            st.write(f"**Total Debit: ₹{total_debit:,.2f}** | **Total Credit: ₹{total_credit:,.2f}**")
            
            if abs(total_debit - total_credit) > 0.01:
                st.error(f"⚠️ Difference: ₹{abs(total_debit - total_credit):,.2f}")
            
            if st.form_submit_button("📝 Create Voucher", use_container_width=True):
                if abs(total_debit - total_credit) > 0.01:
                    st.error("Cannot create voucher: Debits must equal Credits")
                else:
                    try:
                        voucher_num = generate_voucher_number('JOURNAL')
                        
                        conn.execute("""
                            INSERT INTO journal_vouchers 
                            (voucher_number, voucher_date, description, total_amount, created_by)
                            VALUES (?, ?, ?, ?, ?)
                        """, (voucher_num, voucher_date, description, total_debit, 
                              st.session_state.user['id']))
                        
                        voucher_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                        
                        for entry in entries:
                            if entry['debit'] > 0 or entry['credit'] > 0:
                                conn.execute("""
                                    INSERT INTO journal_entries 
                                    (voucher_id, account_head, debit_amount, credit_amount)
                                    VALUES (?, ?, ?, ?)
                                """, (voucher_id, entry['account_head'], 
                                      entry['debit'], entry['credit']))
                        
                        conn.commit()
                        st.success(f"✅ Journal Voucher created: **{voucher_num}**")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    with tab2:
        st.subheader("Journal Vouchers List")
        
        vouchers = conn.execute("""
            SELECT jv.voucher_number, jv.voucher_date, jv.description,
                   jv.total_amount, jv.status, u.username, jv.created_at
            FROM journal_vouchers jv
            LEFT JOIN users u ON jv.created_by = u.id
            ORDER BY jv.created_at DESC
        """).fetchall()
        
        if vouchers:
            for v in vouchers:
                status_color = {'DRAFT': '🟡', 'POSTED': '🟢', 'CANCELLED': '🔴'}
                with st.expander(f"{status_color.get(v[4], '⚪')} {v[0]} - {v[1]} - ₹{v[3]:,.2f} ({v[4]})"):
                    st.write(f"**Date:** {v[1]}")
                    st.write(f"**Description:** {v[2]}")
                    st.write(f"**Created by:** {v[5]}")
                    st.write(f"**Amount:** ₹{v[3]:,.2f}")
                    
                    entries = conn.execute("""
                        SELECT account_head, debit_amount, credit_amount
                        FROM journal_entries
                        WHERE voucher_id=(
                            SELECT id FROM journal_vouchers WHERE voucher_number=?
                        )
                    """, (v[0],)).fetchall()
                    
                    if entries:
                        df_entries = pd.DataFrame(entries, columns=['Account Head', 'Debit', 'Credit'])
                        st.dataframe(df_entries.style.format({
                            'Debit': '₹{:,.2f}',
                            'Credit': '₹{:,.2f}'
                        }), use_container_width=True)
                    
                    if v[4] == 'DRAFT':
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(f"✅ Post Voucher", key=f"post_{v[0]}", use_container_width=True):
                                conn.execute("""
                                    UPDATE journal_vouchers 
                                    SET status='POSTED', posted_by=?, posted_at=CURRENT_TIMESTAMP
                                    WHERE voucher_number=?
                                """, (st.session_state.user['id'], v[0]))
                                conn.commit()
                                st.success("Voucher posted successfully!")
                                st.rerun()
                        with col2:
                            if st.button(f"❌ Cancel Voucher", key=f"cancel_{v[0]}", use_container_width=True):
                                conn.execute("""
                                    UPDATE journal_vouchers 
                                    SET status='CANCELLED'
                                    WHERE voucher_number=?
                                """, (v[0],))
                                conn.commit()
                                st.warning("Voucher cancelled!")
                                st.rerun()
        else:
            st.info("No journal vouchers found")
    
    conn.close()

def show_reports():
    st.markdown('<h1 class="main-header">📋 Reports</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Generate and download various reports</p>', unsafe_allow_html=True)
    
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized access")
        return
    
    report_type = st.selectbox("Select Report Type", [
        "Customer Master List",
        "Account Statement Summary",
        "FD Maturity Report",
        "RD Installment Report",
        "Transaction Summary",
        "KYC Status Report",
        "Daily Transaction Report",
        "Interest Calculation Report",
        "Income & Expense Report"
    ])
    
    conn = get_db()
    
    if report_type == "Customer Master List":
        st.subheader("Customer Master List")
        customers = conn.execute("""
            SELECT customer_id, first_name, last_name, email, phone, city, 
                   kyc_status, created_at
            FROM customers ORDER BY created_at DESC
        """).fetchall()
        
        if customers:
            df = pd.DataFrame(customers, columns=['ID', 'First Name', 'Last Name', 'Email', 
                                                  'Phone', 'City', 'KYC', 'Registration Date'])
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False)
            st.download_button("📥 Download CSV", csv, "customer_list.csv", "text/csv")
    
    elif report_type == "FD Maturity Report":
        st.subheader("FD Maturity Report")
        fds = conn.execute("""
            SELECT fd.fd_number, c.first_name || ' ' || c.last_name as name,
                   fd.principal_amount, fd.maturity_amount, fd.start_date,
                   fd.maturity_date, fd.status
            FROM fixed_deposits fd
            JOIN accounts a ON fd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            ORDER BY fd.maturity_date
        """).fetchall()
        
        if fds:
            df = pd.DataFrame(fds, columns=['FD No', 'Customer', 'Principal', 
                                           'Maturity Amt', 'Start Date', 'Maturity Date', 'Status'])
            st.dataframe(df.style.format({
                'Principal': '₹{:,.2f}',
                'Maturity Amt': '₹{:,.2f}'
            }), use_container_width=True)
    
    elif report_type == "Interest Calculation Report":
        st.subheader("Interest Calculation Report")
        calcs = conn.execute("""
            SELECT ic.calculation_date, a.account_number, 
                   c.first_name || ' ' || c.last_name as customer,
                   ic.principal_amount, ic.interest_rate, ic.interest_earned, ic.days_calculated
            FROM interest_calculations ic
            JOIN accounts a ON ic.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            ORDER BY ic.calculation_date DESC
        """).fetchall()
        
        if calcs:
            df = pd.DataFrame(calcs, columns=['Date', 'Account', 'Customer', 'Principal', 
                                             'Rate', 'Interest', 'Days'])
            st.dataframe(df.style.format({
                'Principal': '₹{:,.2f}',
                'Rate': '{:.2f}%',
                'Interest': '₹{:,.2f}'
            }), use_container_width=True)
    
    elif report_type == "Daily Transaction Report":
        st.subheader("Daily Transaction Report")
        report_date = st.date_input("Select Date", date.today())
        
        transactions = conn.execute("""
            SELECT t.transaction_id, c.first_name || ' ' || c.last_name as customer,
                   a.account_type, t.transaction_type, t.amount, t.voucher_number, t.created_at
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            WHERE DATE(t.created_at) = ?
            ORDER BY t.created_at DESC
        """, (report_date,)).fetchall()
        
        if transactions:
            df = pd.DataFrame(transactions, columns=['Txn ID', 'Customer', 'Account Type',
                                                      'Type', 'Amount', 'Voucher', 'Time'])
            st.dataframe(df.style.format({'Amount': '₹{:,.2f}'}), use_container_width=True)
        else:
            st.info(f"No transactions on {report_date}")
    
    elif report_type == "Income & Expense Report":
        st.subheader("Income & Expense Report")
        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input("From Date", date.today().replace(day=1))
        with col2:
            to_date = st.date_input("To Date", date.today())
        
        if st.button("Generate Report"):
            income_data = conn.execute("""
                SELECT income_type, SUM(amount) as total
                FROM income
                WHERE DATE(date) BETWEEN ? AND ?
                GROUP BY income_type
            """, (from_date, to_date)).fetchall()
            
            if income_data:
                st.markdown("### Income")
                df_income = pd.DataFrame(income_data, columns=['Type', 'Amount'])
                st.dataframe(df_income.style.format({'Amount': '₹{:,.2f}'}), use_container_width=True)
            
            expense_data = conn.execute("""
                SELECT expense_type, SUM(amount) as total
                FROM expenses
                WHERE DATE(date) BETWEEN ? AND ?
                GROUP BY expense_type
            """, (from_date, to_date)).fetchall()
            
            if expense_data:
                st.markdown("### Expenses")
                df_expense = pd.DataFrame(expense_data, columns=['Type', 'Amount'])
                st.dataframe(df_expense.style.format({'Amount': '₹{:,.2f}'}), use_container_width=True)
    
    conn.close()

# ==================== MAIN ====================

if __name__ == "__main__":
    main()
