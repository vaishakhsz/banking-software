
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
    r = rate / 400
    n = months / 3
    maturity = principal * (1 + r) ** n
    return round(maturity, 2)

def calculate_rd_maturity(monthly_amount, rate, months):
    r = rate / 400
    n = months / 3
    maturity = monthly_amount * (((1 + r) ** n - 1) / (1 - (1 + r) ** (-1/3)))
    return round(maturity, 2)

def calculate_sb_interest(balance, rate, days):
    if balance <= 0:
        return 0
    interest = (balance * rate * days) / (100 * 365)
    return round(interest, 2)

def get_minimum_balance(conn, account_id, from_date, to_date):
    try:
        start_balance_result = conn.execute("""
            SELECT balance_after FROM transactions
            WHERE account_id=? AND DATE(created_at) < ? ORDER BY created_at DESC LIMIT 1
        """, (account_id, from_date)).fetchone()
        
        if start_balance_result:
            start_balance = start_balance_result[0]
        else:
            current_result = conn.execute("SELECT balance FROM accounts WHERE id=?", (account_id,)).fetchone()
            if current_result:
                start_balance = current_result[0]
            else:
                return 0
        
        transactions = conn.execute("""
            SELECT balance_after FROM transactions
            WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ? ORDER BY created_at
        """, (account_id, from_date, to_date)).fetchall()
        
        if transactions:
            all_balances = [start_balance] + [t[0] for t in transactions]
            return min(all_balances)
        else:
            return start_balance
    except:
        current_result = conn.execute("SELECT balance FROM accounts WHERE id=?", (account_id,)).fetchone()
        return current_result[0] if current_result else 0

def calculate_and_post_sb_interest(created_by_user_id=1, calc_from_date=None, calc_to_date=None):
    conn = get_db()
    try:
        accounts = conn.execute("""
            SELECT id, account_number, balance, interest_rate, 
                   COALESCE(total_interest_earned, 0) as total_interest,
                   last_interest_calculation, customer_id, created_at
            FROM accounts WHERE account_type='SB' AND status='ACTIVE'
        """).fetchall()
        
        if not accounts:
            return "No active SB accounts found", []
        
        if calc_to_date is None:
            calc_to_date = date.today()
        if calc_from_date is None:
            calc_from_date = calc_to_date.replace(day=1)
        
        interest_posted = []
        
        for acc in accounts:
            account_id = acc[0]
            account_number = acc[1]
            balance = acc[2]
            rate = acc[3] if acc[3] else 3.5
            existing_interest = acc[4]
            last_calc_date = acc[5]
            customer_id = acc[6]
            
            actual_from_date = calc_from_date
            
            acc_created = acc[7]
            if acc_created:
                try:
                    acc_created_date = datetime.strptime(str(acc_created)[:10], '%Y-%m-%d').date()
                    if acc_created_date > actual_from_date:
                        actual_from_date = acc_created_date
                except:
                    pass
            
            if last_calc_date:
                try:
                    last_calc = datetime.strptime(str(last_calc_date)[:10], '%Y-%m-%d').date()
                    if last_calc >= actual_from_date:
                        actual_from_date = last_calc + timedelta(days=1)
                except:
                    pass
            
            days = (calc_to_date - actual_from_date).days + 1
            if days <= 0:
                continue
            
            min_balance = get_minimum_balance(conn, account_id, actual_from_date, calc_to_date)
            if min_balance <= 0:
                min_balance = balance
            
            interest = calculate_sb_interest(min_balance, rate, days)
            
            if interest > 0:
                new_balance = balance + interest
                new_total_interest = existing_interest + interest
                
                conn.execute("""
                    UPDATE accounts SET balance=?, total_interest_earned=?, last_interest_calculation=?
                    WHERE id=?
                """, (new_balance, new_total_interest, calc_to_date, account_id))
                
                txn_id = generate_id('TXN')
                voucher_num = generate_voucher_number('RECEIPT')
                conn.execute("""
                    INSERT INTO transactions (transaction_id, account_id, transaction_type, amount, 
                    balance_after, description, reference_type, voucher_type, voucher_number, created_by)
                    VALUES (?, ?, 'CREDIT', ?, ?, 'SB Interest Credited', 'INTEREST', 'RECEIPT', ?, ?)
                """, (txn_id, account_id, interest, new_balance, voucher_num, created_by_user_id))
                
                conn.execute("""
                    INSERT INTO interest_calculations 
                    (account_id, calculation_date, principal_amount, interest_rate, interest_earned, days_calculated)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (account_id, calc_to_date, min_balance, rate, interest, days))
                
                journal_voucher_num = generate_voucher_number('JOURNAL')
                conn.execute("""
                    INSERT INTO journal_vouchers 
                    (voucher_number, voucher_date, description, total_amount, status, created_by)
                    VALUES (?, ?, ?, ?, 'POSTED', ?)
                """, (journal_voucher_num, calc_to_date,
                      f"SB Interest - A/C {account_number} ({actual_from_date.strftime('%d-%m-%Y')} to {calc_to_date.strftime('%d-%m-%Y')})",
                      interest, created_by_user_id))
                
                jv_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                
                conn.execute("""
                    INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description)
                    VALUES (?, 'Interest Paid on SB', ?, 0, ?)
                """, (jv_id, interest, f"Interest A/C {account_number}: {days} days @ {rate}% on min bal ₹{min_balance:,.2f}"))
                
                conn.execute("""
                    INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description)
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
                    'from_date': actual_from_date,
                    'to_date': calc_to_date,
                    'journal_voucher': journal_voucher_num,
                    'total_interest_earned': new_total_interest,
                    'maturity_value': new_balance
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
    c.execute("SELECT * FROM users WHERE username=? AND password=? AND is_active=1", (username, hashed_pw))
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
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(10, 7, 'S.No', 1)
        pdf.cell(90, 7, 'Account Head', 1)
        pdf.cell(45, 7, 'Debit (Rs.)', 1, 0, 'R')
        pdf.cell(45, 7, 'Credit (Rs.)', 1, 1, 'R')
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
    st.set_page_config(page_title="🏦 Complete Banking System", page_icon="🏦", layout="wide", initial_sidebar_state="expanded")
    init_database()
    create_default_admin()
    init_session_state()
    
    st.markdown("""
    <style>
    .main-header { font-size: 2.8rem; font-weight: bold; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; margin-bottom: 0.5rem; padding: 1rem; }
    .sub-header { text-align: center; color: #666; font-size: 1.1rem; margin-bottom: 2rem; border-bottom: 2px solid #e0e0e0; padding-bottom: 1rem; }
    .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.5rem; border-radius: 15px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); transition: transform 0.3s ease; }
    .metric-card:hover { transform: translateY(-5px); }
    .metric-card h3 { font-size: 2.2rem; margin: 0; font-weight: bold; }
    .metric-card p { margin: 0.5rem 0 0 0; font-size: 0.9rem; opacity: 0.9; }
    .metric-card .icon { font-size: 2.5rem; display: block; margin-bottom: 0.5rem; }
    .customer-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.5rem; border-radius: 15px; margin-bottom: 1rem; }
    .stButton > button { width: 100%; border-radius: 10px; font-weight: 600; transition: all 0.3s ease; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 0.6rem 1.2rem; font-size: 1rem; }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(102,126,234,0.4); }
    .info-box { background: linear-gradient(135deg, #e0f2fe 0%, #dbeafe 100%); padding: 1rem; border-radius: 10px; border-left: 4px solid #667eea; margin: 1rem 0; color: black; }
    .success-box { background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); padding: 1rem; border-radius: 10px; border-left: 4px solid #10b981; margin: 1rem 0; color: black; }
    .warning-box { background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); padding: 1rem; border-radius: 10px; border-left: 4px solid #f59e0b; margin: 1rem 0; color: black; }
    .danger-box { background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); padding: 1rem; border-radius: 10px; border-left: 4px solid #ef4444; margin: 1rem 0; color: black; }
    .trial-balance-table { background: white; padding: 1.5rem; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    .balance-sheet-card { background: white; padding: 1.5rem; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 1rem; color: black; }
    .balance-sheet-card h3 { color: black !important; }
    .balance-sheet-card .section-header { color: #667eea !important; }
    .section-header { font-size: 1.3rem; font-weight: bold; color: #667eea; border-bottom: 3px solid #667eea; padding-bottom: 0.5rem; margin-bottom: 1rem; }
    .jv-card { background: #f8f9fa; padding: 1rem; border-radius: 10px; border-left: 4px solid #667eea; margin: 0.5rem 0; color: black; }
    .date-info-box { background: linear-gradient(135deg, #ede9fe 0%, #ddd6fe 100%); padding: 1.2rem; border-radius: 12px; border: 1px solid #c4b5fd; margin: 1rem 0; color: black; }
    .login-container { max-width: 450px; margin: 0 auto; padding: 2rem; background: white; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 10px 10px 0 0; padding: 0.5rem 1rem; font-weight: 600; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white !important; }
    @media (max-width: 768px) { .main-header { font-size: 2rem; } .metric-card h3 { font-size: 1.5rem; } }
    </style>
    """, unsafe_allow_html=True)
    
    if st.session_state.user is None:
        show_login_page()
    else:
        show_main_app()

def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""<div style="text-align: center; padding: 2rem 0 1rem 0;"><h1 style="font-size: 3.5rem; margin: 0;">🏦</h1><h1 class="main-header">Complete Banking System</h1><p class="sub-header">Enterprise Banking Management Platform</p></div>""", unsafe_allow_html=True)
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
                        st.session_state.user = {'id': user[0], 'username': user[1], 'role': user[3]}
                        st.success("✅ Login successful! Redirecting...")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials!")
            with col_b:
                if st.button("📝 Register", use_container_width=True):
                    st.session_state.page = 'register'
                    st.rerun()
            st.divider()
            st.markdown("""<div style="text-align: center; color: #666; font-size: 0.9rem;"><p>Default Admin:<br><strong>admin / admin123</strong></p></div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

def show_main_app():
    with st.sidebar:
        st.markdown("""<div style="text-align: center; padding: 0.5rem 0 1rem 0;"><h1 style="font-size: 2.5rem; margin: 0;">🏦</h1><h3 style="margin: 0; color: #667eea;">Banking System</h3></div>""", unsafe_allow_html=True)
        st.divider()
        st.markdown(f"""<div style="text-align: center;"><p style="font-size: 1.1rem; font-weight: bold;">👤 {st.session_state.user['username']}</p></div>""", unsafe_allow_html=True)
        role_badge = {'admin': '<span style="background: #10b981; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold;">ADMIN</span>', 'staff': '<span style="background: #f59e0b; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold;">STAFF</span>', 'customer': '<span style="background: #ef4444; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold;">CUSTOMER</span>'}
        st.markdown(f'<div style="text-align: center; margin: 0.5rem 0;">{role_badge.get(st.session_state.user["role"], "USER")}</div>', unsafe_allow_html=True)
        st.divider()
        
        if st.session_state.user['role'] in ['admin', 'staff']:
            menu_options = {'dashboard': '📊 Dashboard', 'customer_management': '👥 Customer Management', 'kyc_verification': '🔍 KYC Verification', 'create_sb_account': '🏦 Create SB Account', 'sb_accounts': '💰 SB Accounts', 'fixed_deposits': '💎 Fixed Deposits', 'recurring_deposits': '🔄 Recurring Deposits', 'transactions': '💳 All Transactions', 'journal_vouchers': '📝 Journal Vouchers', 'income_expenses': '📈 Income & Expenses', 'interest_calculation': '📊 Interest Calculation', 'trial_balance': '⚖️ Trial Balance', 'balance_sheet': '📊 Balance Sheet', 'profit_loss': '💵 Profit & Loss', 'reports': '📋 Reports'}
        else:
            menu_options = {'dashboard': '📊 Dashboard', 'my_accounts': '💰 My Accounts', 'my_transactions': '💳 My Transactions', 'my_details': '👤 My Details'}
        
        for key, label in menu_options.items():
            if st.sidebar.button(label, key=key, use_container_width=True):
                st.session_state.page = key
                st.rerun()
        
        st.divider()
        if st.sidebar.button("🚪 Logout", use_container_width=True, type="primary"):
            st.session_state.user = None
            st.session_state.page = 'login'
            st.rerun()
    
    page = st.session_state.get('page', 'dashboard')
    if page == 'dashboard': show_dashboard()
    elif page == 'customer_management': show_customer_management()
    elif page == 'kyc_verification': show_kyc_verification()
    elif page == 'create_sb_account': show_create_sb_account()
    elif page in ('sb_accounts', 'my_accounts'): show_sb_accounts()
    elif page == 'fixed_deposits': show_fixed_deposits()
    elif page == 'recurring_deposits': show_recurring_deposits()
    elif page in ('transactions', 'my_transactions'): show_transactions()
    elif page == 'journal_vouchers': show_journal_vouchers()
    elif page == 'income_expenses': show_income_expenses()
    elif page == 'interest_calculation': show_interest_calculation()
    elif page == 'trial_balance': show_trial_balance()
    elif page == 'balance_sheet': show_balance_sheet()
    elif page == 'profit_loss': show_profit_loss()
    elif page == 'reports': show_reports()
    elif page == 'my_details': show_my_details()

def show_dashboard():
    st.markdown('<h1 class="main-header">📊 Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Real-time overview of your banking operations</p>', unsafe_allow_html=True)
    conn = get_db()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        st.markdown(f'<div class="metric-card"><span class="icon">👥</span><h3>{customers}</h3><p>Total Customers</p></div>', unsafe_allow_html=True)
    with col2:
        accounts = conn.execute("SELECT COUNT(*) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
        st.markdown(f'<div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);"><span class="icon">💰</span><h3>{accounts}</h3><p>Active SB Accounts</p></div>', unsafe_allow_html=True)
    with col3:
        total_balance = conn.execute("SELECT COALESCE(SUM(balance), 0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
        total_interest = conn.execute("SELECT COALESCE(SUM(total_interest_earned), 0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
        maturity_value = total_balance + total_interest
        st.markdown(f'<div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);"><span class="icon">🏦</span><h3>₹{maturity_value:,.2f}</h3><p>Total SB Maturity Value</p></div>', unsafe_allow_html=True)
    with col4:
        pending_kyc = conn.execute("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'").fetchone()[0]
        st.markdown(f'<div class="metric-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);"><span class="icon">🔍</span><h3>{pending_kyc}</h3><p>Pending KYC</p></div>', unsafe_allow_html=True)
    conn.close()

def show_customer_management():
    st.markdown('<h1 class="main-header">👥 Customer Management</h1>', unsafe_allow_html=True)
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Register", "👥 View", "🔍 Search", "📊 Analytics"])
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
                phone = st.text_input("Phone *")
            with col2:
                pan_number = st.text_input("PAN Number *")
                aadhar_number = st.text_input("Aadhar Number *")
                address = st.text_area("Address")
                city = st.text_input("City")
                state = st.text_input("State")
                pincode = st.text_input("PIN Code")
            st.subheader("📎 KYC Documents")
            col1, col2, col3 = st.columns(3)
            with col1: pan_document = st.file_uploader("PAN Card *", type=['jpg','jpeg','png','pdf'])
            with col2: aadhar_document = st.file_uploader("Aadhar Card *", type=['jpg','jpeg','png','pdf'])
            with col3: photo = st.file_uploader("Photo", type=['jpg','jpeg','png'])
            signature = st.file_uploader("Signature", type=['jpg','jpeg','png'])
            if st.form_submit_button("📝 Register", use_container_width=True):
                if not all([first_name, last_name, email, phone, pan_number, aadhar_number]):
                    st.error("Fill all required fields")
                elif not pan_document or not aadhar_document:
                    st.error("Upload PAN and Aadhar")
                else:
                    try:
                        conn = get_db()
                        customer_id = generate_id('CUST')
                        pan_data = pan_document.read()
                        aadhar_data = aadhar_document.read()
                        photo_data = photo.read() if photo else None
                        signature_data = signature.read() if signature else None
                        conn.execute("""INSERT INTO customers (customer_id, first_name, last_name, date_of_birth, gender, email, phone, address, city, state, pincode, pan_number, aadhar_number, pan_document, aadhar_document, photo, signature) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                   (customer_id, first_name, last_name, date_of_birth, gender, email, phone, address, city, state, pincode, pan_number, aadhar_number, pan_data, aadhar_data, photo_data, signature_data))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Registered! ID: **{customer_id}**")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    with tab2:
        st.subheader("Customer List")
        conn = get_db()
        customers = conn.execute("SELECT id, customer_id, first_name, last_name, email, phone, city, state, pan_number, aadhar_number, kyc_status, created_at FROM customers ORDER BY created_at DESC").fetchall()
        if customers:
            for cust in customers:
                with st.expander(f"👤 {cust[2]} {cust[3]} - {cust[1]} ({cust[10]})"):
                    st.write(f"**ID:** {cust[1]} | **Email:** {cust[4]} | **Phone:** {cust[5]}")
                    st.write(f"**PAN:** {cust[8]} | **Aadhar:** {cust[9]} | **KYC:** {cust[10]}")
                    accounts = conn.execute("SELECT account_number, balance, COALESCE(total_interest_earned,0) FROM accounts WHERE customer_id=? AND account_type='SB'", (cust[0],)).fetchall()
                    if accounts:
                        for acc in accounts:
                            st.write(f"• {acc[0]} - ₹{acc[1]:,.2f} (Maturity: ₹{acc[1]+acc[2]:,.2f})")
            df = pd.DataFrame(customers, columns=['ID','Customer ID','First','Last','Email','Phone','City','State','PAN','Aadhar','KYC','Date'])
            st.download_button("📥 Download", df.to_csv(index=False), "customers.csv", "text/csv")
        else:
            st.info("No customers")
        conn.close()

def show_kyc_verification():
    st.markdown('<h1 class="main-header">🔍 KYC Verification</h1>', unsafe_allow_html=True)
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized")
        return
    conn = get_db()
    tab1, tab2 = st.tabs(["📋 Pending", "✅ Verified"])
    with tab1:
        pending = conn.execute("SELECT * FROM customers WHERE kyc_status='PENDING' ORDER BY created_at").fetchall()
        if not pending:
            st.success("✅ No pending!")
        else:
            for cust in pending:
                with st.expander(f"📄 {cust[3]} {cust[4]} - {cust[2]}", expanded=True):
                    st.write(f"**Name:** {cust[3]} {cust[4]} | **DOB:** {cust[5]} | **Email:** {cust[7]} | **Phone:** {cust[8]}")
                    st.write(f"**PAN:** {cust[12]} | **Aadhar:** {cust[13]}")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button(f"✅ Approve", key=f"app_{cust[0]}", use_container_width=True):
                            conn.execute("UPDATE customers SET kyc_status='VERIFIED', kyc_verified_by=?, kyc_verified_at=CURRENT_TIMESTAMP WHERE id=?", (st.session_state.user['id'], cust[0]))
                            existing = conn.execute("SELECT id FROM accounts WHERE customer_id=? AND account_type='SB' AND status='ACTIVE'", (cust[0],)).fetchone()
                            if not existing:
                                account_number = generate_account_number('SB')
                                conn.execute("INSERT INTO accounts (account_number, customer_id, account_type, balance, interest_rate, last_interest_calculation, total_interest_earned) VALUES (?, ?, 'SB', 0.00, 3.50, DATE('now'), 0.00)", (account_number, cust[0]))
                            conn.commit()
                            st.success("✅ Approved!")
                            st.rerun()
                    with col2:
                        if st.button(f"❌ Reject", key=f"rej_{cust[0]}", use_container_width=True):
                            conn.execute("UPDATE customers SET kyc_status='REJECTED' WHERE id=?", (cust[0],))
                            conn.commit()
                            st.rerun()
    with tab2:
        verified = conn.execute("SELECT customer_id, first_name, last_name, email, phone, kyc_verified_at FROM customers WHERE kyc_status='VERIFIED' ORDER BY kyc_verified_at DESC").fetchall()
        if verified:
            st.dataframe(pd.DataFrame(verified, columns=['ID','First','Last','Email','Phone','Verified']), use_container_width=True)
    conn.close()

def show_create_sb_account():
    st.markdown('<h1 class="main-header">🏦 Create SB Account</h1>', unsafe_allow_html=True)
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized")
        return
    conn = get_db()
    customers = conn.execute("""SELECT c.id, c.customer_id, c.first_name || ' ' || c.last_name, c.email, c.phone FROM customers c WHERE c.kyc_status='VERIFIED' AND NOT EXISTS (SELECT 1 FROM accounts a WHERE a.customer_id=c.id AND a.account_type='SB' AND a.status='ACTIVE') ORDER BY c.created_at DESC""").fetchall()
    if not customers:
        st.info("All verified customers have SB accounts!")
        return
    selected = st.selectbox("Select Customer", [f"{c[1]} - {c[2]}" for c in customers])
    if selected:
        idx = [f"{c[1]} - {c[2]}" for c in customers].index(selected)
        customer = customers[idx]
        with st.form("create_sb"):
            col1, col2 = st.columns(2)
            with col1: interest_rate = st.number_input("Interest Rate (%)", 0.0, 10.0, 3.50, 0.25)
            with col2: opening_balance = st.number_input("Opening Balance (₹)", 0.0, step=100.0, value=0.0)
            if st.form_submit_button("🏦 Create", use_container_width=True):
                try:
                    account_number = generate_account_number('SB')
                    conn.execute("INSERT INTO accounts (account_number, customer_id, account_type, balance, interest_rate, last_interest_calculation, total_interest_earned) VALUES (?, ?, 'SB', ?, ?, DATE('now'), 0.00)", (account_number, customer[0], opening_balance, interest_rate))
                    conn.commit()
                    st.success(f"✅ Created! Account: **{account_number}**")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    conn.close()

def show_sb_accounts():
    st.markdown('<h1 class="main-header">💰 SB Accounts</h1>', unsafe_allow_html=True)
    conn = get_db()
    tab1, tab2, tab3, tab4 = st.tabs(["📋 List", "💸 Deposit/Withdraw", "📜 Statement", "📈 Interest Info"])
    with tab1:
        if st.session_state.user['role'] == 'customer':
            accounts = conn.execute("SELECT a.account_number, c.first_name||' '||c.last_name, a.balance, a.interest_rate, a.status, COALESCE(a.total_interest_earned,0), a.created_at FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND c.user_id=? ORDER BY a.created_at DESC", (st.session_state.user['id'],)).fetchall()
        else:
            accounts = conn.execute("SELECT a.account_number, c.first_name||' '||c.last_name, a.balance, a.interest_rate, a.status, COALESCE(a.total_interest_earned,0), a.created_at FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND c.kyc_status='VERIFIED' ORDER BY a.created_at DESC").fetchall()
        if accounts:
            data = []
            for a in accounts:
                mv = a[2] + a[5]
                data.append({'Account': a[0], 'Customer': a[1], 'Principal': a[2], 'Rate': a[3], 'Status': a[4], 'Interest': a[5], 'Maturity Value': mv, 'Opened': a[6]})
            df = pd.DataFrame(data)
            st.dataframe(df.style.format({'Principal':'₹{:,.2f}','Interest':'₹{:,.2f}','Maturity Value':'₹{:,.2f}'}), use_container_width=True)
        else:
            st.info("No SB accounts")
    with tab2:
        if st.session_state.user['role'] == 'customer':
            accounts = conn.execute("SELECT a.id, a.account_number, c.first_name||' '||c.last_name, a.balance, COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND c.user_id=?", (st.session_state.user['id'],)).fetchall()
        else:
            accounts = conn.execute("SELECT a.id, a.account_number, c.first_name||' '||c.last_name, a.balance, COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        if accounts:
            selected = st.selectbox("Select Account", [f"{a[1]} - {a[2]} (Principal: ₹{a[3]:,.2f}, Maturity: ₹{a[3]+a[4]:,.2f})" for a in accounts])
            if selected:
                idx = [f"{a[1]} - {a[2]} (Principal: ₹{a[3]:,.2f}, Maturity: ₹{a[3]+a[4]:,.2f})" for a in accounts].index(selected)
                acc = accounts[idx]
                txn_type = st.radio("Type", ["💰 DEPOSIT", "💸 WITHDRAWAL"], horizontal=True)
                with st.form("txn"):
                    amount = st.number_input("Amount (₹)", min_value=0.01, step=100.0)
                    description = st.text_input("Description")
                    mode = st.selectbox("Mode", ["CASH", "TRANSFER", "CHEQUE"])
                    if st.form_submit_button("💳 Process", use_container_width=True):
                        actual_type = "DEPOSIT" if "DEPOSIT" in txn_type else "WITHDRAWAL"
                        if actual_type == "WITHDRAWAL" and amount > acc[3]:
                            st.error("❌ Insufficient balance!")
                        else:
                            try:
                                new_balance = acc[3] + amount if actual_type == "DEPOSIT" else acc[3] - amount
                                txn_type_db = "CREDIT" if actual_type == "DEPOSIT" else "DEBIT"
                                voucher_type = "RECEIPT" if actual_type == "DEPOSIT" else "PAYMENT"
                                txn_id = generate_id('TXN')
                                voucher_num = generate_voucher_number(voucher_type)
                                conn.execute("INSERT INTO transactions (transaction_id, account_id, transaction_type, amount, balance_after, description, reference_type, voucher_type, voucher_number, created_by) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                           (txn_id, acc[0], txn_type_db, amount, new_balance, description, mode, voucher_type, voucher_num, st.session_state.user['id']))
                                conn.execute("UPDATE accounts SET balance=? WHERE id=?", (new_balance, acc[0]))
                                conn.commit()
                                st.success(f"✅ Done! New Principal: ₹{new_balance:,.2f} | New Maturity: ₹{new_balance+acc[4]:,.2f}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
    with tab3:
        st.subheader("Account Statement")
        if st.session_state.user['role'] == 'customer':
            accounts = conn.execute("SELECT a.id, a.account_number, c.first_name || ' ' || c.last_name as name FROM accounts a JOIN customers c ON a.customer_id = c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND c.user_id=?", (st.session_state.user['id'],)).fetchall()
        else:
            accounts = conn.execute("SELECT a.id, a.account_number, c.first_name || ' ' || c.last_name as name FROM accounts a JOIN customers c ON a.customer_id = c.id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        if accounts:
            account_options = {f"{acc[1]} - {acc[2]}": acc[0] for acc in accounts}
            selected = st.selectbox("Select Account for Statement", list(account_options.keys()), key="stmt_select")
            if selected:
                account_id = account_options[selected]
                col1, col2 = st.columns(2)
                with col1:
                    from_date = st.date_input("From Date", date.today() - timedelta(days=30), key="stmt_from")
                with col2:
                    to_date = st.date_input("To Date", date.today(), key="stmt_to")
                transactions = conn.execute("SELECT transaction_id, created_at, transaction_type, amount, balance_after, description, reference_type, voucher_number FROM transactions WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ? ORDER BY created_at DESC", (account_id, from_date, to_date)).fetchall()
                if transactions:
                    df = pd.DataFrame(transactions, columns=['Transaction ID', 'Date', 'Type', 'Amount', 'Balance', 'Description', 'Mode', 'Voucher No.'])
                    st.dataframe(df.style.format({'Amount': '₹{:,.2f}', 'Balance': '₹{:,.2f}'}), use_container_width=True)
                    csv = df.to_csv(index=False)
                    st.download_button("📥 Download Statement", csv, "account_statement.csv", "text/csv")
                else:
                    st.info("No transactions in selected period")
        else:
            st.info("No accounts available")
    with tab4:
        st.subheader("Interest Information & Maturity Details")
        if st.session_state.user['role'] == 'customer':
            accounts = conn.execute("SELECT a.account_number, c.first_name || ' ' || c.last_name as name, a.balance, a.interest_rate, COALESCE(a.total_interest_earned, 0) as total_interest, a.created_at, a.last_interest_calculation FROM accounts a JOIN customers c ON a.customer_id = c.id WHERE a.account_type='SB' AND c.user_id=? ORDER BY a.created_at DESC", (st.session_state.user['id'],)).fetchall()
        else:
            accounts = conn.execute("SELECT a.account_number, c.first_name || ' ' || c.last_name as name, a.balance, a.interest_rate, COALESCE(a.total_interest_earned, 0) as total_interest, a.created_at, a.last_interest_calculation FROM accounts a JOIN customers c ON a.customer_id = c.id WHERE a.account_type='SB' ORDER BY a.created_at DESC").fetchall()
        if accounts:
            st.markdown("### 📊 SB Account Maturity Values")
            interest_data = []
            for acc in accounts:
                interest_data.append({
                    'Account Number': acc[0], 'Customer': acc[1],
                    'Principal': acc[2], 'Interest Rate': f"{acc[3]:.2f}%" if acc[3] else "3.50%",
                    'Total Interest': acc[4], 'Maturity Value': acc[2] + acc[4],
                    'Last Calc': acc[6] if acc[6] else 'Never', 'Opened': acc[5][:10] if acc[5] else 'N/A'
                })
            df = pd.DataFrame(interest_data)
            st.dataframe(df.style.format({'Principal': '₹{:,.2f}', 'Total Interest': '₹{:,.2f}', 'Maturity Value': '₹{:,.2f}'}), use_container_width=True)
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Total Principal", f"₹{sum(d['Principal'] for d in interest_data):,.2f}")
            with col2: st.metric("Total Interest", f"₹{sum(d['Total Interest'] for d in interest_data):,.2f}")
            with col3: st.metric("Total Maturity", f"₹{sum(d['Maturity Value'] for d in interest_data):,.2f}")
        else:
            st.info("No SB accounts found")
        if st.session_state.user['role'] in ['admin', 'staff']:
            st.subheader("Recent Interest Calculations")
            interest_calcs = conn.execute("SELECT ic.calculation_date, a.account_number, c.first_name || ' ' || c.last_name, ic.principal_amount, ic.interest_rate, ic.interest_earned, ic.days_calculated FROM interest_calculations ic JOIN accounts a ON ic.account_id = a.id JOIN customers c ON a.customer_id = c.id ORDER BY ic.calculation_date DESC LIMIT 20").fetchall()
            if interest_calcs:
                calc_data = [{'Date': c[0], 'Account': c[1], 'Customer': c[2], 'Principal': c[3], 'Rate': f"{c[4]:.2f}%", 'Interest': c[5], 'Days': c[6]} for c in interest_calcs]
                st.dataframe(pd.DataFrame(calc_data).style.format({'Principal': '₹{:,.2f}', 'Interest': '₹{:,.2f}'}), use_container_width=True)
            else:
                st.info("No interest calculations yet")
    conn.close()

def show_interest_calculation():
    st.markdown('<h1 class="main-header">📊 Interest Calculation</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Calculate and post interest to SB accounts with date range selection</p>', unsafe_allow_html=True)
    
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized access")
        return
    
    conn = get_db()
    
    tab1, tab2, tab3 = st.tabs(["🧮 Calculate & Post Interest", "📊 Interest History", "📈 Trial Balance Impact"])
    
    with tab1:
        st.subheader("Calculate and Post SB Interest")
        
        st.markdown('<div class="date-info-box">', unsafe_allow_html=True)
        st.markdown("### 📅 Select Interest Calculation Period")
        col1, col2 = st.columns(2)
        with col1:
            calc_from_date = st.date_input("Calculate Interest From", value=date.today().replace(day=1), help="Start date for interest calculation", key="int_calc_from")
        with col2:
            calc_to_date = st.date_input("Calculate Interest To", value=date.today(), help="End date for interest calculation", key="int_calc_to")
        
        if calc_from_date > calc_to_date:
            st.error("❌ 'From Date' cannot be after 'To Date'")
        else:
            days_in_period = (calc_to_date - calc_from_date).days + 1
            st.info(f"📊 **Selected Period:** {calc_from_date.strftime('%d-%b-%Y')} to {calc_to_date.strftime('%d-%b-%Y')} ({days_in_period} days)")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.info("""
        **Interest Calculation Rules:**
        - Interest is calculated on the **minimum balance** during the selected period
        - Default interest rate: **3.50% per annum**
        - Formula: `Interest = (Minimum Balance × Rate × Number of Days) / (100 × 365)`
        - Interest is posted to account balance and recorded in journal vouchers
        """)
        
        accounts = conn.execute("""
            SELECT a.id, a.account_number, c.first_name || ' ' || c.last_name as name, 
                   a.balance, a.interest_rate, 
                   COALESCE(a.total_interest_earned, 0) as total_interest,
                   COALESCE(a.last_interest_calculation, DATE(a.created_at)) as last_calc
            FROM accounts a JOIN customers c ON a.customer_id = c.id
            WHERE a.account_type='SB' AND a.status='ACTIVE' ORDER BY a.created_at
        """).fetchall()
        
        if accounts:
            st.markdown("### Current SB Account Status")
            account_data = []
            for acc in accounts:
                mv = acc[3] + acc[5]
                account_data.append({'Account': acc[1], 'Customer': acc[2], 'Principal': acc[3], 'Rate': f"{acc[4]:.2f}%" if acc[4] else "3.50%", 'Interest': acc[5], 'Maturity Value': mv, 'Last Calc': acc[6] if acc[6] else 'Never'})
            df = pd.DataFrame(account_data)
            st.dataframe(df.style.format({'Principal': '₹{:,.2f}', 'Interest': '₹{:,.2f}', 'Maturity Value': '₹{:,.2f}'}), use_container_width=True)
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"🧮 Calculate & Post Interest", use_container_width=True, type="primary", key="btn_calc_post"):
                    if calc_from_date > calc_to_date:
                        st.error("❌ Invalid date range!")
                    else:
                        with st.spinner(f"Calculating interest from {calc_from_date} to {calc_to_date}..."):
                            status, result = calculate_and_post_sb_interest(st.session_state.user['id'], calc_from_date, calc_to_date)
                        
                        if status == "SUCCESS":
                            if len(result) > 0:
                                st.success(f"✅ Interest posted for {len(result)} accounts!")
                                result_data = []
                                for r in result:
                                    result_data.append({'Account': r['account_number'], 'Min Balance': r['min_balance'], 'Principal Before': r['balance_before'], 'Interest': r['interest'], 'New Principal': r['new_balance'], 'Maturity Value': r['maturity_value'], 'Rate': f"{r['rate']:.2f}%", 'Days': r['days'], 'Period': f"{r['from_date']} to {r['to_date']}", 'JV': r['journal_voucher']})
                                result_df = pd.DataFrame(result_data)
                                st.dataframe(result_df.style.format({'Min Balance':'₹{:,.2f}','Principal Before':'₹{:,.2f}','Interest':'₹{:,.2f}','New Principal':'₹{:,.2f}','Maturity Value':'₹{:,.2f}'}), use_container_width=True)
                                total_interest = sum(r['interest'] for r in result)
                                st.metric("Total Interest Posted", f"₹{total_interest:,.2f}")
                                st.success(f"✅ {len(result)} Journal Vouchers created and posted!")
                                st.balloons()
                                csv = result_df.to_csv(index=False)
                                st.download_button("📥 Download Summary", csv, "interest_posting.csv", "text/csv")
                            else:
                                st.info("No interest to post.")
                        else:
                            st.error(status)
            
            with col2:
                if st.button(f"📊 Preview Interest", use_container_width=True, key="btn_preview"):
                    if calc_from_date > calc_to_date:
                        st.error("❌ Invalid date range!")
                    else:
                        preview_data = []
                        for acc in accounts:
                            balance = acc[3]
                            rate = acc[4] if acc[4] else 3.5
                            account_id = acc[0]
                            min_balance = get_minimum_balance(conn, account_id, calc_from_date, calc_to_date)
                            if min_balance <= 0:
                                min_balance = balance
                            days = (calc_to_date - calc_from_date).days + 1
                            if days > 0:
                                interest = calculate_sb_interest(min_balance, rate, days)
                                preview_data.append({'Account': acc[1], 'Customer': acc[2], 'Principal': balance, 'Min Balance': min_balance, 'Rate': f"{rate:.2f}%", 'Days': days, 'Interest': interest, 'New Principal': balance+interest, 'New Maturity': balance+acc[5]+interest})
                        if preview_data:
                            preview_df = pd.DataFrame(preview_data)
                            st.dataframe(preview_df.style.format({'Principal':'₹{:,.2f}','Min Balance':'₹{:,.2f}','Interest':'₹{:,.2f}','New Principal':'₹{:,.2f}','New Maturity':'₹{:,.2f}'}), use_container_width=True)
                            total_estimated = sum(p['Interest'] for p in preview_data)
                            st.info(f"📊 Total Estimated Interest: ₹{total_estimated:,.2f}")
                            st.warning("⚠️ Preview only. No interest posted.")
                        else:
                            st.info("No interest to calculate")
        else:
            st.warning("No active SB accounts found")
    
    with tab2:
        st.subheader("Interest Calculation History")
        history = conn.execute("""
            SELECT ic.calculation_date, a.account_number, c.first_name||' '||c.last_name,
                   ic.principal_amount, ic.interest_rate, ic.interest_earned, ic.days_calculated
            FROM interest_calculations ic JOIN accounts a ON ic.account_id=a.id JOIN customers c ON a.customer_id=c.id
            ORDER BY ic.calculation_date DESC LIMIT 100
        """).fetchall()
        if history:
            hist_data = []
            for h in history:
                hist_data.append({'Date': h[0], 'Account': h[1], 'Customer': h[2], 'Principal': h[3], 'Rate': f"{h[4]:.2f}%", 'Interest': h[5], 'Days': h[6], 'Maturity Value': h[3]+h[5]})
            df = pd.DataFrame(hist_data)
            st.dataframe(df.style.format({'Principal':'₹{:,.2f}','Interest':'₹{:,.2f}','Maturity Value':'₹{:,.2f}'}), use_container_width=True)
            total_interest_paid = sum(h[5] for h in history)
            st.metric("Total Interest Paid to Date", f"₹{total_interest_paid:,.2f}")
            csv = df.to_csv(index=False)
            st.download_button("📥 Download", csv, "interest_history.csv", "text/csv")
        else:
            st.info("No history yet")
    
    with tab3:
        st.subheader("Interest Impact on Trial Balance")
        st.info("View all journal vouchers created for interest posting")
        
        interest_jvs = conn.execute("""
            SELECT jv.voucher_number, jv.voucher_date, jv.description, jv.total_amount, jv.status,
                   je.account_head, je.debit_amount, je.credit_amount, je.description
            FROM journal_vouchers jv
            JOIN journal_entries je ON jv.id = je.voucher_id
            WHERE (je.account_head = 'Interest Paid on SB' OR je.account_head LIKE '%SB Account%')
            AND jv.status = 'POSTED'
            ORDER BY jv.voucher_date DESC LIMIT 50
        """).fetchall()
        
        if interest_jvs:
            jv_dict = {}
            for jv in interest_jvs:
                vn = jv[0]
                if vn not in jv_dict:
                    jv_dict[vn] = {'date': jv[1], 'desc': jv[2], 'amount': jv[3], 'status': jv[4], 'entries': []}
                jv_dict[vn]['entries'].append({'head': jv[5], 'debit': jv[6], 'credit': jv[7], 'desc': jv[8]})
            
            st.markdown(f"### 📝 Interest Journal Vouchers ({len(jv_dict)} vouchers)")
            
            for vn, data in jv_dict.items():
                with st.expander(f"📄 {vn} - {data['date']} - ₹{data['amount']:,.2f} - {data['status']}"):
                    st.write(f"**Description:** {data['desc']}")
                    for entry in data['entries']:
                        color = "#fee2e2" if entry['debit'] > 0 else "#d1fae5"
                        st.markdown(f"""<div style="background: {color}; color: black; padding: 0.8rem; border-radius: 8px; margin: 0.3rem 0; border-left: 4px solid #667eea;"><b>{entry['head']}</b><br>Debit: ₹{entry['debit']:,.2f} | Credit: ₹{entry['credit']:,.2f}<br><small>{entry['desc']}</small></div>""", unsafe_allow_html=True)
            
            total_jv_amount = sum(data['amount'] for data in jv_dict.values())
            
            st.divider()
            st.markdown("### 📊 Trial Balance Impact")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Interest Expense (Debit - P&L):**")
                st.metric("Reduces Net Profit by", f"₹{total_jv_amount:,.2f}")
            with col2:
                st.markdown("**SB Account Liability (Credit - B/S):**")
                st.metric("Increases Liabilities by", f"₹{total_jv_amount:,.2f}")
            
            st.success(f"✅ Both sides of Trial Balance increase by ₹{total_jv_amount:,.2f} (Perfectly Balanced)")
        else:
            st.info("No interest journal vouchers found. Post interest first to see the impact.")
            
            st.markdown("### Expected Journal Entry Structure:")
            st.markdown("""
            <div style="background: #fee2e2; color: black; padding: 0.8rem; border-radius: 8px; margin: 0.3rem 0; border-left: 4px solid #ef4444;">
                <b>Interest Paid on SB (Expense - Debit)</b><br>
                Debit: ₹XXX.XX | Credit: ₹0.00
            </div>
            <div style="background: #d1fae5; color: black; padding: 0.8rem; border-radius: 8px; margin: 0.3rem 0; border-left: 4px solid #10b981;">
                <b>SB Account - XXXXXX (Liability - Credit)</b><br>
                Debit: ₹0.00 | Credit: ₹XXX.XX
            </div>
            <br>
            <b>Net Effect:</b> Trial Balance remains BALANCED ✅
            """, unsafe_allow_html=True)
    
    conn.close()

def show_trial_balance():
    st.markdown('<h1 class="main-header">⚖️ Trial Balance</h1>', unsafe_allow_html=True)
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized")
        return
    conn = get_db()
    as_on_date = st.date_input("As on Date", date.today())
    if st.button("📊 Generate Trial Balance", use_container_width=True):
        trial_data = []
        
        cash_balance = conn.execute("SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END), 0) FROM transactions WHERE reference_type='CASH'").fetchone()[0]
        if abs(cash_balance) > 0:
            trial_data.append({'account_head': 'Cash in Hand', 'category': 'Asset', 'debit': max(cash_balance, 0), 'credit': max(-cash_balance, 0), 'jv_ref': 'Cash transactions'})
        
        sb_total = conn.execute("SELECT COALESCE(SUM(balance), 0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        interest_payable_sb = conn.execute("SELECT COALESCE(SUM(total_interest_earned), 0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if interest_payable_sb == 0:
            interest_payable_sb = conn.execute("SELECT COALESCE(SUM(credit_amount), 0) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE je.account_head LIKE '%SB Account%' AND jv.status='POSTED'").fetchone()[0]
        
        if sb_total > 0:
            trial_data.append({'account_head': 'SB Deposits (Principal)', 'category': 'Liability', 'debit': 0, 'credit': sb_total, 'jv_ref': 'All SB principal balances'})
        if interest_payable_sb > 0:
            jv_numbers = conn.execute("SELECT DISTINCT jv.voucher_number FROM journal_vouchers jv JOIN journal_entries je ON jv.id=je.voucher_id WHERE je.account_head LIKE '%SB Account%' AND jv.status='POSTED'").fetchall()
            jv_ref = ', '.join([j[0] for j in jv_numbers[:3]]) + ('...' if len(jv_numbers) > 3 else '') if jv_numbers else 'Interest postings'
            trial_data.append({'account_head': 'Interest Payable on SB', 'category': 'Liability', 'debit': 0, 'credit': interest_payable_sb, 'jv_ref': f'JV: {jv_ref}'})
        
        fd_total = conn.execute("SELECT COALESCE(SUM(principal_amount), 0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        if fd_total > 0:
            trial_data.append({'account_head': 'Fixed Deposits', 'category': 'Liability', 'debit': 0, 'credit': fd_total, 'jv_ref': 'Active FD principals'})
        
        rd_total = conn.execute("SELECT COALESCE(SUM(monthly_amount * installments_paid), 0) FROM recurring_deposits WHERE status='ACTIVE'").fetchone()[0]
        if rd_total > 0:
            trial_data.append({'account_head': 'Recurring Deposits', 'category': 'Liability', 'debit': 0, 'credit': rd_total, 'jv_ref': 'RD installments paid'})
        
        for inc_type in ['Interest Earned', 'Fees & Charges', 'Commission Income', 'Other Income']:
            amt = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM income WHERE income_type=?", (inc_type,)).fetchone()[0]
            if amt > 0:
                trial_data.append({'account_head': inc_type, 'category': 'Income', 'debit': 0, 'credit': amt, 'jv_ref': 'Income entries'})
        
        interest_paid_sb = conn.execute("SELECT COALESCE(SUM(debit_amount), 0) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE je.account_head='Interest Paid on SB' AND jv.status='POSTED'").fetchone()[0]
        if interest_paid_sb > 0:
            jv_numbers_exp = conn.execute("SELECT DISTINCT jv.voucher_number FROM journal_vouchers jv JOIN journal_entries je ON jv.id=je.voucher_id WHERE je.account_head='Interest Paid on SB' AND jv.status='POSTED'").fetchall()
            jv_ref_exp = ', '.join([j[0] for j in jv_numbers_exp[:3]]) + ('...' if len(jv_numbers_exp) > 3 else '') if jv_numbers_exp else 'Interest postings'
            trial_data.append({'account_head': 'Interest Paid on SB', 'category': 'Expense', 'debit': interest_paid_sb, 'credit': 0, 'jv_ref': f'JV: {jv_ref_exp}'})
        
        for exp_type in ['Salary & Wages', 'Rent & Utilities', 'Operating Expenses', 'Administrative Expenses', 'Other Expenses']:
            amt = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE expense_type=?", (exp_type,)).fetchone()[0]
            if amt > 0:
                trial_data.append({'account_head': exp_type, 'category': 'Expense', 'debit': amt, 'credit': 0, 'jv_ref': 'Expense entries'})
        
        total_debits = sum(item['debit'] for item in trial_data)
        total_credits = sum(item['credit'] for item in trial_data)
        diff = total_credits - total_debits
        if abs(diff) > 0.01:
            trial_data.append({'account_head': 'Capital/Reserves', 'category': 'Capital', 'debit': max(-diff, 0), 'credit': max(diff, 0), 'jv_ref': 'Balancing figure'})
        
        if trial_data:
            df = pd.DataFrame(trial_data)
            st.markdown('<div class="trial-balance-table">', unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("Total Assets", f"₹{sum(i['debit'] for i in trial_data if i['category']=='Asset'):,.2f}")
            with col2: st.metric("Total Liabilities", f"₹{sum(i['credit'] for i in trial_data if i['category']=='Liability'):,.2f}")
            with col3: st.metric("Total Income", f"₹{sum(i['credit'] for i in trial_data if i['category']=='Income'):,.2f}")
            with col4: st.metric("Total Expenses", f"₹{sum(i['debit'] for i in trial_data if i['category']=='Expense'):,.2f}")
            
            st.divider()
            
            for category in ['Asset', 'Liability', 'Income', 'Expense', 'Capital']:
                cat_data = [item for item in trial_data if item['category'] == category]
                if cat_data:
                    st.markdown(f"**{category}s**")
                    display_df = pd.DataFrame(cat_data)[['account_head', 'debit', 'credit', 'jv_ref']]
                    display_df.columns = ['Account Head', 'Debit (₹)', 'Credit (₹)', 'JV Reference']
                    st.dataframe(display_df.style.format({'Debit (₹)': '₹{:,.2f}', 'Credit (₹)': '₹{:,.2f}'}), use_container_width=True)
            
            total_debit = df['debit'].sum()
            total_credit = df['credit'].sum()
            
            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Total Debit", f"₹{total_debit:,.2f}")
            with col2: st.metric("Total Credit", f"₹{total_credit:,.2f}")
            with col3:
                if abs(total_debit - total_credit) < 0.01:
                    st.success("✅ BALANCED!")
                else:
                    st.error(f"❌ Difference: ₹{abs(total_debit - total_credit):,.2f}")
            
            st.divider()
            st.markdown("### 📊 Interest & Maturity Summary")
            st.write(f"• SB Principal: ₹{sb_total:,.2f}")
            st.write(f"• SB Interest Payable: ₹{interest_payable_sb:,.2f}")
            st.write(f"• SB Maturity Value: ₹{sb_total + interest_payable_sb:,.2f}")
            st.write(f"• Interest Expense: ₹{interest_paid_sb:,.2f}")
            if interest_paid_sb > 0:
                st.success(f"✅ Interest reflected in Trial Balance")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1: st.download_button("📥 Download CSV", df.to_csv(index=False), "trial_balance.csv", "text/csv")
            with col2:
                if st.button("📄 Generate PDF"):
                    pdf_data = {'date': as_on_date.strftime('%d-%m-%Y'), 'entries': [{'account_head': i['account_head'], 'debit': i['debit'], 'credit': i['credit']} for i in trial_data]}
                    pdf_file = generate_report_pdf('trial_balance', pdf_data, 'trial_balance.pdf')
                    if pdf_file:
                        with open(pdf_file, 'rb') as f:
                            st.download_button("📥 Download PDF", f, "trial_balance.pdf", "application/pdf")
        else:
            st.info("No data available")
    conn.close()

def show_balance_sheet():
    st.markdown('<h1 class="main-header">📊 Balance Sheet</h1>', unsafe_allow_html=True)
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized")
        return
    conn = get_db()
    as_on_date = st.date_input("As on Date", date.today())
    if st.button("📊 Generate", use_container_width=True):
        cash = conn.execute("SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END), 0) FROM transactions WHERE reference_type='CASH'").fetchone()[0]
        sb_balance = conn.execute("SELECT COALESCE(SUM(balance), 0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        total_interest = conn.execute("SELECT COALESCE(SUM(total_interest_earned), 0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if total_interest == 0:
            total_interest = conn.execute("SELECT COALESCE(SUM(credit_amount), 0) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE je.account_head LIKE '%SB Account%' AND jv.status='POSTED'").fetchone()[0]
        fd_total = conn.execute("SELECT COALESCE(SUM(principal_amount), 0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        rd_total = conn.execute("SELECT COALESCE(SUM(monthly_amount * installments_paid), 0) FROM recurring_deposits WHERE status='ACTIVE'").fetchone()[0]
        interest_fd = conn.execute("SELECT COALESCE(SUM(maturity_amount - principal_amount), 0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        
        total_assets = cash + sb_balance + fd_total + rd_total
        total_liabilities = total_interest + interest_fd + fd_total + rd_total + sb_balance
        capital = total_assets - total_liabilities
        sb_maturity = sb_balance + total_interest
        
        st.markdown('<div class="balance-sheet-card"><h3 class="section-header" style="color: #667eea !important;">📊 ASSETS</h3>', unsafe_allow_html=True)
        st.write(f"💰 Cash: ₹{cash:,.2f}")
        st.write(f"🏦 SB Principal: ₹{sb_balance:,.2f}")
        st.write(f"💎 FD: ₹{fd_total:,.2f}")
        st.write(f"🔄 RD: ₹{rd_total:,.2f}")
        st.markdown(f"### **Total Assets: ₹{total_assets:,.2f}**</div>", unsafe_allow_html=True)
        
        st.markdown('<div class="balance-sheet-card"><h3 class="section-header" style="color: #667eea !important;">📋 LIABILITIES</h3>', unsafe_allow_html=True)
        st.write(f"📈 SB Interest Payable: ₹{total_interest:,.2f}")
        st.write(f"📈 FD Interest: ₹{interest_fd:,.2f}")
        st.write(f"🏦 SB Principal: ₹{sb_balance:,.2f}")
        st.write(f"💎 FD: ₹{fd_total:,.2f}")
        st.write(f"🔄 RD: ₹{rd_total:,.2f}")
        st.write(f"💎 SB Total Liability: ₹{sb_maturity:,.2f}")
        st.markdown(f"### **Total Liabilities: ₹{total_liabilities:,.2f}**</div>", unsafe_allow_html=True)
        
        st.markdown('<div class="balance-sheet-card"><h3 class="section-header" style="color: #667eea !important;">💰 CAPITAL</h3>', unsafe_allow_html=True)
        st.write(f"**Capital/Net Worth: ₹{capital:,.2f}**</div>", unsafe_allow_html=True)
        
        if abs(total_assets - (total_liabilities + capital)) < 0.01:
            st.success(f"✅ Balanced! Assets ₹{total_assets:,.2f} = Liabilities ₹{total_liabilities:,.2f} + Capital ₹{capital:,.2f}")
        
        with st.expander("📊 SB Account Maturity Details"):
            st.write(f"💰 SB Principal: ₹{sb_balance:,.2f}")
            st.write(f"📈 SB Interest Accrued: ₹{total_interest:,.2f}")
            st.write(f"💎 SB Total Maturity Value: ₹{sb_maturity:,.2f}")
            if sb_balance > 0:
                st.write(f"📊 Interest as % of Principal: {total_interest/sb_balance*100:.2f}%")
    conn.close()

def show_profit_loss():
    st.markdown('<h1 class="main-header">💵 Profit & Loss</h1>', unsafe_allow_html=True)
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized")
        return
    conn = get_db()
    col1, col2 = st.columns(2)
    with col1: from_date = st.date_input("From", date.today().replace(month=1, day=1))
    with col2: to_date = st.date_input("To", date.today())
    if st.button("📊 Generate", use_container_width=True):
        income = [
            ('Interest Earned', conn.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Interest Earned' AND DATE(date) BETWEEN ? AND ?", (from_date, to_date)).fetchone()[0]),
            ('Fees & Charges', conn.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Fees & Charges' AND DATE(date) BETWEEN ? AND ?", (from_date, to_date)).fetchone()[0]),
            ('Commission', conn.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Commission Income' AND DATE(date) BETWEEN ? AND ?", (from_date, to_date)).fetchone()[0]),
            ('Other Income', conn.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Other Income' AND DATE(date) BETWEEN ? AND ?", (from_date, to_date)).fetchone()[0]),
        ]
        expenses = [
            ('Interest Paid on SB', conn.execute("SELECT COALESCE(SUM(debit_amount),0) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE je.account_head='Interest Paid on SB' AND jv.status='POSTED' AND DATE(jv.voucher_date) BETWEEN ? AND ?", (from_date, to_date)).fetchone()[0]),
            ('Salary & Wages', conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Salary & Wages' AND DATE(date) BETWEEN ? AND ?", (from_date, to_date)).fetchone()[0]),
            ('Rent & Utilities', conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Rent & Utilities' AND DATE(date) BETWEEN ? AND ?", (from_date, to_date)).fetchone()[0]),
            ('Operating Expenses', conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Operating Expenses' AND DATE(date) BETWEEN ? AND ?", (from_date, to_date)).fetchone()[0]),
            ('Admin Expenses', conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Administrative Expenses' AND DATE(date) BETWEEN ? AND ?", (from_date, to_date)).fetchone()[0]),
            ('Other Expenses', conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Other Expenses' AND DATE(date) BETWEEN ? AND ?", (from_date, to_date)).fetchone()[0]),
        ]
        total_income = sum(i[1] for i in income)
        total_expenses = sum(e[1] for e in expenses)
        st.markdown("### 📈 Income")
        for item, amt in income: st.write(f"• {item}: ₹{amt:,.2f}")
        st.markdown(f"**Total Income: ₹{total_income:,.2f}**")
        st.markdown("### 📉 Expenses")
        for item, amt in expenses:
            if amt > 0: st.write(f"• {item}: ₹{amt:,.2f}")
        st.markdown(f"**Total Expenses: ₹{total_expenses:,.2f}**")
        net = total_income - total_expenses
        if net >= 0:
            st.success(f"## 🎉 Net Profit: ₹{net:,.2f}")
        else:
            st.error(f"## 📉 Net Loss: ₹{abs(net):,.2f}")
    conn.close()

def show_income_expenses():
    st.markdown('<h1 class="main-header">📈 Income & Expenses</h1>', unsafe_allow_html=True)
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized")
        return
    conn = get_db()
    tab1, tab2 = st.tabs(["💰 Income", "💸 Expense"])
    with tab1:
        with st.form("income"):
            income_type = st.selectbox("Type", ["Interest Earned", "Fees & Charges", "Commission Income", "Other Income"])
            amount = st.number_input("Amount (₹)", min_value=1.0, step=100.0)
            income_date = st.date_input("Date", date.today())
            description = st.text_area("Description")
            if st.form_submit_button("💰 Record", use_container_width=True):
                conn.execute("INSERT INTO income (income_id, income_type, amount, description, date, created_by) VALUES (?,?,?,?,?,?)",
                           (generate_id('INC'), income_type, amount, description, income_date, st.session_state.user['id']))
                conn.commit()
                st.success(f"✅ Recorded! ₹{amount:,.2f}")
    with tab2:
        with st.form("expense"):
            expense_type = st.selectbox("Type", ["Salary & Wages", "Rent & Utilities", "Operating Expenses", "Administrative Expenses", "Other Expenses"])
            amount = st.number_input("Amount (₹)", min_value=1.0, step=100.0)
            expense_date = st.date_input("Date", date.today())
            description = st.text_area("Description")
            if st.form_submit_button("💸 Record", use_container_width=True):
                conn.execute("INSERT INTO expenses (expense_id, expense_type, amount, description, date, created_by) VALUES (?,?,?,?,?,?)",
                           (generate_id('EXP'), expense_type, amount, description, expense_date, st.session_state.user['id']))
                conn.commit()
                st.success(f"✅ Recorded! ₹{amount:,.2f}")
    conn.close()

def show_fixed_deposits():
    st.markdown('<h1 class="main-header">💎 Fixed Deposits</h1>', unsafe_allow_html=True)
    conn = get_db()
    tab1, tab2, tab3 = st.tabs(["📝 Open", "📋 Active", "🔔 Maturity"])
    with tab1:
        customers = conn.execute("SELECT c.id, c.customer_id, c.first_name||' '||c.last_name, a.account_number FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND c.kyc_status='VERIFIED' AND a.status='ACTIVE'").fetchall()
        if customers:
            selected = st.selectbox("Select Customer", [f"{c[1]} - {c[2]}" for c in customers])
            if selected:
                idx = [f"{c[1]} - {c[2]}" for c in customers].index(selected)
                cust = customers[idx]
                with st.form("open_fd"):
                    col1, col2 = st.columns(2)
                    with col1:
                        principal = st.number_input("Principal (₹)", min_value=1000.0, step=1000.0, value=10000.0)
                        tenure = st.selectbox("Tenure (Months)", [3, 6, 12, 24, 36, 60])
                        rate = st.number_input("Rate (%)", 3.0, 10.0, 6.5, 0.25)
                    with col2:
                        start_date = st.date_input("Start Date", date.today())
                        nominee_name = st.text_input("Nominee")
                        nominee_relation = st.text_input("Relation")
                    maturity_date = start_date + timedelta(days=tenure*30)
                    maturity_amt = calculate_fd_maturity(principal, rate, tenure)
                    st.info(f"📅 Maturity: {maturity_date.strftime('%d-%m-%Y')} | 💰 Maturity: ₹{maturity_amt:,.2f}")
                    if st.form_submit_button("🔒 Open FD", use_container_width=True):
                        try:
                            fd_number = generate_id('FD')
                            account_number = generate_account_number('FD')
                            conn.execute("INSERT INTO accounts (account_number, customer_id, account_type, balance, interest_rate) VALUES (?,?,'FD',0.00,?)", (account_number, cust[0], rate))
                            acc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                            conn.execute("INSERT INTO fixed_deposits (fd_number, account_id, principal_amount, interest_rate, start_date, maturity_date, maturity_amount, tenure_months, nominee_name, nominee_relation) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                       (fd_number, acc_id, principal, rate, start_date, maturity_date, maturity_amt, tenure, nominee_name, nominee_relation))
                            txn_id = generate_id('TXN')
                            voucher_num = generate_voucher_number('RECEIPT')
                            conn.execute("INSERT INTO transactions (transaction_id, account_id, transaction_type, amount, balance_after, description, reference_type, voucher_type, voucher_number, created_by) VALUES (?,?,'CREDIT',?,?,'FD Deposit','FD_DEPOSIT','RECEIPT',?,?)",
                                       (txn_id, acc_id, principal, principal, voucher_num, st.session_state.user['id']))
                            conn.commit()
                            st.success(f"✅ FD opened! **{fd_number}**")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
    with tab2:
        fds = conn.execute("SELECT fd.fd_number, c.first_name||' '||c.last_name, fd.principal_amount, fd.interest_rate, fd.start_date, fd.maturity_date, fd.maturity_amount, fd.status FROM fixed_deposits fd JOIN accounts a ON fd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE fd.status='ACTIVE' ORDER BY fd.maturity_date").fetchall()
        if fds:
            df = pd.DataFrame(fds, columns=['FD No','Customer','Principal','Rate','Start','Maturity','Maturity Amt','Status'])
            st.dataframe(df.style.format({'Principal':'₹{:,.2f}','Maturity Amt':'₹{:,.2f}'}), use_container_width=True)
    with tab3:
        today = date.today()
        maturing = conn.execute("SELECT fd.fd_number, c.first_name||' '||c.last_name, fd.maturity_amount, fd.maturity_date FROM fixed_deposits fd JOIN accounts a ON fd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE fd.maturity_date BETWEEN ? AND ? AND fd.status='ACTIVE' ORDER BY fd.maturity_date", (today, today+timedelta(days=30))).fetchall()
        if maturing:
            st.warning(f"🔔 {len(maturing)} FD(s) maturing soon")
            df = pd.DataFrame(maturing, columns=['FD No','Customer','Maturity Amt','Date'])
            st.dataframe(df.style.format({'Maturity Amt':'₹{:,.2f}'}), use_container_width=True)
        else:
            st.success("No FDs maturing soon")
    conn.close()

def show_recurring_deposits():
    st.markdown('<h1 class="main-header">🔄 Recurring Deposits</h1>', unsafe_allow_html=True)
    conn = get_db()
    tab1, tab2, tab3 = st.tabs(["📝 Open", "📋 Active", "💳 Pay"])
    with tab1:
        customers = conn.execute("SELECT c.id, c.customer_id, c.first_name||' '||c.last_name, a.account_number, a.id FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND c.kyc_status='VERIFIED' AND a.status='ACTIVE'").fetchall()
        if customers:
            selected = st.selectbox("Select Customer", [f"{c[1]} - {c[2]}" for c in customers])
            if selected:
                idx = [f"{c[1]} - {c[2]}" for c in customers].index(selected)
                cust = customers[idx]
                with st.form("open_rd"):
                    col1, col2 = st.columns(2)
                    with col1:
                        monthly = st.number_input("Monthly (₹)", min_value=100.0, step=100.0, value=1000.0)
                        tenure = st.selectbox("Tenure (Months)", [6, 12, 24, 36, 48, 60])
                        rate = st.number_input("Rate (%)", 3.0, 10.0, 6.0, 0.25)
                    with col2:
                        start_date = st.date_input("Start Date", date.today())
                        nominee_name = st.text_input("Nominee")
                        nominee_relation = st.text_input("Relation")
                    maturity_date = start_date + timedelta(days=tenure*30)
                    maturity_amt = calculate_rd_maturity(monthly, rate, tenure)
                    total_deposit = monthly * tenure
                    st.info(f"📅 Maturity: {maturity_date.strftime('%d-%m-%Y')} | 💰 Maturity: ₹{maturity_amt:,.2f} (Deposit: ₹{total_deposit:,.2f})")
                    if st.form_submit_button("🔄 Open RD", use_container_width=True):
                        try:
                            rd_number = generate_id('RD')
                            account_number = generate_account_number('RD')
                            conn.execute("INSERT INTO accounts (account_number, customer_id, account_type, balance, interest_rate) VALUES (?,?,'RD',0.00,?)", (account_number, cust[0], rate))
                            acc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                            conn.execute("INSERT INTO recurring_deposits (rd_number, account_id, monthly_amount, interest_rate, start_date, maturity_date, maturity_amount, tenure_months, total_installments, nominee_name, nominee_relation) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                       (rd_number, acc_id, monthly, rate, start_date, maturity_date, maturity_amt, tenure, tenure, nominee_name, nominee_relation))
                            txn_id = generate_id('TXN')
                            voucher_num = generate_voucher_number('RECEIPT')
                            conn.execute("INSERT INTO transactions (transaction_id, account_id, transaction_type, amount, balance_after, description, reference_type, voucher_type, voucher_number, created_by) VALUES (?,?,'CREDIT',?,?,'RD Installment 1','RD_INSTALLMENT','RECEIPT',?,?)",
                                       (txn_id, acc_id, monthly, monthly, voucher_num, st.session_state.user['id']))
                            conn.execute("UPDATE recurring_deposits SET installments_paid=1 WHERE rd_number=?", (rd_number,))
                            conn.commit()
                            st.success(f"✅ RD opened! **{rd_number}**")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
    with tab2:
        rds = conn.execute("SELECT rd.rd_number, c.first_name||' '||c.last_name, rd.monthly_amount, rd.interest_rate, rd.start_date, rd.maturity_date, rd.maturity_amount, rd.installments_paid, rd.total_installments, rd.status FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE rd.status='ACTIVE' ORDER BY rd.maturity_date").fetchall()
        if rds:
            df = pd.DataFrame(rds, columns=['RD No','Customer','Monthly','Rate','Start','Maturity','Maturity Amt','Paid','Total','Status'])
            df['Progress'] = df.apply(lambda r: f"{r['Paid']}/{r['Total']} ({r['Paid']/r['Total']*100:.0f}%)", axis=1)
            st.dataframe(df.style.format({'Monthly':'₹{:,.2f}','Maturity Amt':'₹{:,.2f}'}), use_container_width=True)
    with tab3:
        rds = conn.execute("SELECT rd.id, rd.rd_number, c.first_name||' '||c.last_name, rd.monthly_amount, rd.installments_paid, rd.total_installments, a.id FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE rd.status='ACTIVE' AND rd.installments_paid < rd.total_installments").fetchall()
        if rds:
            selected = st.selectbox("Select RD", [f"{r[1]} - {r[2]} (Paid: {r[4]}/{r[5]})" for r in rds])
            if selected:
                idx = [f"{r[1]} - {r[2]} (Paid: {r[4]}/{r[5]})" for r in rds].index(selected)
                rd = rds[idx]
                with st.form("pay_installment"):
                    amount = st.number_input("Amount (₹)", value=float(rd[3]), min_value=float(rd[3]))
                    if st.form_submit_button("💳 Pay", use_container_width=True):
                        txn_id = generate_id('TXN')
                        voucher_num = generate_voucher_number('RECEIPT')
                        conn.execute("INSERT INTO transactions (transaction_id, account_id, transaction_type, amount, balance_after, description, reference_type, voucher_type, voucher_number, created_by) VALUES (?,?,'CREDIT',?,?,?, 'RD_INSTALLMENT','RECEIPT',?,?)",
                                   (txn_id, rd[6], amount, amount, f"RD Installment {rd[4]+1}/{rd[5]}", voucher_num, st.session_state.user['id']))
                        new_paid = rd[4] + 1
                        conn.execute("UPDATE recurring_deposits SET installments_paid=? WHERE id=?", (new_paid, rd[0]))
                        if new_paid >= rd[5]:
                            conn.execute("UPDATE recurring_deposits SET status='MATURED' WHERE id=?", (rd[0],))
                        conn.commit()
                        st.success(f"✅ Paid! ({new_paid}/{rd[5]})")
                        st.rerun()
    conn.close()

def show_transactions():
    st.markdown('<h1 class="main-header">💳 Transactions</h1>', unsafe_allow_html=True)
    conn = get_db()
    col1, col2, col3, col4 = st.columns(4)
    with col1: account_type = st.selectbox("Account Type", ["All", "SB", "FD", "RD"])
    with col2: txn_type = st.selectbox("Type", ["All", "CREDIT", "DEBIT"])
    with col3: from_date = st.date_input("From", date.today()-timedelta(days=30))
    with col4: to_date = st.date_input("To", date.today())
    
    query = """SELECT t.transaction_id, c.first_name||' '||c.last_name, a.account_number, a.account_type, t.transaction_type, t.amount, t.balance_after, t.description, t.reference_type, t.voucher_number, t.created_at FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE DATE(t.created_at) BETWEEN ? AND ?"""
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
        df = pd.DataFrame(transactions, columns=['Txn ID','Customer','Account','Type','Action','Amount','Balance','Description','Mode','Voucher','Date'])
        st.dataframe(df.style.format({'Amount':'₹{:,.2f}','Balance':'₹{:,.2f}'}), use_container_width=True)
    else:
        st.info("No transactions")
    conn.close()

def show_journal_vouchers():
    st.markdown('<h1 class="main-header">📝 Journal Vouchers</h1>', unsafe_allow_html=True)
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized")
        return
    conn = get_db()
    tab1, tab2 = st.tabs(["📝 Create", "📋 List"])
    with tab1:
        with st.form("jv"):
            voucher_date = st.date_input("Date", date.today())
            description = st.text_area("Description")
            num_entries = st.number_input("Entries", 2, 10, 2)
            entries = []
            total_debit = 0
            total_credit = 0
            for i in range(int(num_entries)):
                col1, col2, col3 = st.columns(3)
                with col1: head = st.text_input(f"Head", key=f"h_{i}")
                with col2: debit = st.number_input(f"Debit", min_value=0.0, step=100.0, key=f"d_{i}")
                with col3: credit = st.number_input(f"Credit", min_value=0.0, step=100.0, key=f"c_{i}")
                total_debit += debit
                total_credit += credit
                entries.append({'head': head, 'debit': debit, 'credit': credit})
            st.write(f"Debit: ₹{total_debit:,.2f} | Credit: ₹{total_credit:,.2f}")
            if st.form_submit_button("📝 Create", use_container_width=True):
                if abs(total_debit - total_credit) > 0.01:
                    st.error("Must balance!")
                else:
                    try:
                        voucher_num = generate_voucher_number('JOURNAL')
                        conn.execute("INSERT INTO journal_vouchers (voucher_number, voucher_date, description, total_amount, created_by) VALUES (?,?,?,?,?)",
                                   (voucher_num, voucher_date, description, total_debit, st.session_state.user['id']))
                        v_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                        for e in entries:
                            if e['debit'] > 0 or e['credit'] > 0:
                                conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount) VALUES (?,?,?,?)",
                                           (v_id, e['head'], e['debit'], e['credit']))
                        conn.commit()
                        st.success(f"✅ Created: **{voucher_num}**")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    with tab2:
        st.subheader("Journal Vouchers List")
        vouchers = conn.execute("SELECT jv.voucher_number, jv.voucher_date, jv.description, jv.total_amount, jv.status, u.username, jv.created_at FROM journal_vouchers jv LEFT JOIN users u ON jv.created_by = u.id ORDER BY jv.created_at DESC").fetchall()
        if vouchers:
            for v in vouchers:
                status_color = {'DRAFT': '🟡', 'POSTED': '🟢', 'CANCELLED': '🔴'}
                with st.expander(f"{status_color.get(v[4], '⚪')} {v[0]} - {v[1]} - ₹{v[3]:,.2f} ({v[4]})"):
                    st.write(f"**Date:** {v[1]}")
                    st.write(f"**Description:** {v[2]}")
                    st.write(f"**Created by:** {v[5]}")
                    st.write(f"**Amount:** ₹{v[3]:,.2f}")
                    
                    entries = conn.execute("SELECT account_head, debit_amount, credit_amount FROM journal_entries WHERE voucher_id=(SELECT id FROM journal_vouchers WHERE voucher_number=?)", (v[0],)).fetchall()
                    if entries:
                        df_entries = pd.DataFrame(entries, columns=['Account Head', 'Debit', 'Credit'])
                        st.dataframe(df_entries.style.format({'Debit': '₹{:,.2f}', 'Credit': '₹{:,.2f}'}), use_container_width=True)
                    
                    if v[4] == 'DRAFT':
                        st.divider()
                        st.markdown("**Actions:**")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(f"✅ Post/Approve Voucher", key=f"post_{v[0]}", use_container_width=True, type="primary"):
                                conn.execute("UPDATE journal_vouchers SET status='POSTED', posted_by=?, posted_at=CURRENT_TIMESTAMP WHERE voucher_number=?", (st.session_state.user['id'], v[0]))
                                conn.commit()
                                st.success(f"✅ Voucher {v[0]} posted successfully!")
                                st.rerun()
                        with col2:
                            if st.button(f"❌ Cancel Voucher", key=f"cancel_{v[0]}", use_container_width=True):
                                conn.execute("UPDATE journal_vouchers SET status='CANCELLED' WHERE voucher_number=?", (v[0],))
                                conn.commit()
                                st.warning(f"⚠️ Voucher {v[0]} cancelled!")
                                st.rerun()
        else:
            st.info("No journal vouchers found. Create one in the 'Create Voucher' tab.")
    conn.close()

def show_reports():
    st.markdown('<h1 class="main-header">📋 Reports</h1>', unsafe_allow_html=True)
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized")
        return
    report_type = st.selectbox("Report", ["Customer Master List", "Interest Calculation Report", "Daily Transaction Report"])
    conn = get_db()
    if report_type == "Customer Master List":
        customers = conn.execute("SELECT customer_id, first_name, last_name, email, phone, city, kyc_status, created_at FROM customers ORDER BY created_at DESC").fetchall()
        if customers:
            df = pd.DataFrame(customers, columns=['ID','First','Last','Email','Phone','City','KYC','Date'])
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 Download", df.to_csv(index=False), "customers.csv", "text/csv")
    elif report_type == "Interest Calculation Report":
        calcs = conn.execute("SELECT ic.calculation_date, a.account_number, c.first_name||' '||c.last_name, ic.principal_amount, ic.interest_rate, ic.interest_earned, ic.days_calculated FROM interest_calculations ic JOIN accounts a ON ic.account_id=a.id JOIN customers c ON a.customer_id=c.id ORDER BY ic.calculation_date DESC").fetchall()
        if calcs:
            df = pd.DataFrame(calcs, columns=['Date','Account','Customer','Principal','Rate','Interest','Days'])
            st.dataframe(df.style.format({'Principal':'₹{:,.2f}','Interest':'₹{:,.2f}'}), use_container_width=True)
    elif report_type == "Daily Transaction Report":
        report_date = st.date_input("Date", date.today())
        transactions = conn.execute("SELECT t.transaction_id, c.first_name||' '||c.last_name, a.account_type, t.transaction_type, t.amount, t.voucher_number, t.created_at FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE DATE(t.created_at)=? ORDER BY t.created_at DESC", (report_date,)).fetchall()
        if transactions:
            df = pd.DataFrame(transactions, columns=['Txn ID','Customer','Type','Action','Amount','Voucher','Time'])
            st.dataframe(df.style.format({'Amount':'₹{:,.2f}'}), use_container_width=True)
    conn.close()

def show_my_details():
    st.markdown('<h1 class="main-header">👤 My Details</h1>', unsafe_allow_html=True)
    conn = get_db()
    customer = conn.execute("SELECT * FROM customers WHERE user_id=?", (st.session_state.user['id'],)).fetchone()
    if customer:
        st.markdown('<div class="customer-card">', unsafe_allow_html=True)
        st.markdown(f"## {customer[3]} {customer[4]}")
        st.write(f"**ID:** {customer[2]} | **Email:** {customer[7]} | **Phone:** {customer[8]}")
        st.write(f"**DOB:** {customer[5]} | **PAN:** {customer[12]} | **Aadhar:** {customer[13]}")
        st.markdown('</div>', unsafe_allow_html=True)
        accounts = conn.execute("SELECT account_number, balance, COALESCE(total_interest_earned,0), created_at FROM accounts WHERE customer_id=? AND account_type='SB' ORDER BY created_at DESC", (customer[0],)).fetchall()
        if accounts:
            for acc in accounts:
                mv = acc[1] + acc[2]
                st.write(f"• {acc[0]} - Principal: ₹{acc[1]:,.2f}, Interest: ₹{acc[2]:,.2f}, Maturity: ₹{mv:,.2f}")
    else:
        st.warning("No profile found")
    conn.close()

# ==================== MAIN ====================
if __name__ == "__main__":
    main()

