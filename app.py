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
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
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
    
    try:
        c.execute("SELECT total_interest_earned FROM accounts LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE accounts ADD COLUMN total_interest_earned DECIMAL(15,2) DEFAULT 0.00")
    
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
            account_id = acc[0]; account_number = acc[1]; balance = acc[2]
            rate = acc[3] if acc[3] else 3.5; existing_interest = acc[4]
            last_calc_date = acc[5]; customer_id = acc[6]
            actual_from_date = calc_from_date
            acc_created = acc[7]
            if acc_created:
                try:
                    acc_created_date = datetime.strptime(str(acc_created)[:10], '%Y-%m-%d').date()
                    if acc_created_date > actual_from_date: actual_from_date = acc_created_date
                except: pass
            if last_calc_date:
                try:
                    last_calc = datetime.strptime(str(last_calc_date)[:10], '%Y-%m-%d').date()
                    if last_calc >= actual_from_date: actual_from_date = last_calc + timedelta(days=1)
                except: pass
            days = (calc_to_date - actual_from_date).days + 1
            if days <= 0: continue
            min_balance = get_minimum_balance(conn, account_id, actual_from_date, calc_to_date)
            if min_balance <= 0: min_balance = balance
            interest = calculate_sb_interest(min_balance, rate, days)
            if interest > 0:
                new_balance = balance + interest; new_total_interest = existing_interest + interest
                conn.execute("UPDATE accounts SET balance=?, total_interest_earned=?, last_interest_calculation=? WHERE id=?", (new_balance, new_total_interest, calc_to_date, account_id))
                txn_id = generate_id('TXN'); voucher_num = generate_voucher_number('RECEIPT')
                conn.execute("INSERT INTO transactions (transaction_id, account_id, transaction_type, amount, balance_after, description, reference_type, voucher_type, voucher_number, created_by) VALUES (?, ?, 'CREDIT', ?, ?, 'SB Interest Credited', 'INTEREST', 'RECEIPT', ?, ?)", (txn_id, account_id, interest, new_balance, voucher_num, created_by_user_id))
                conn.execute("INSERT INTO interest_calculations (account_id, calculation_date, principal_amount, interest_rate, interest_earned, days_calculated) VALUES (?, ?, ?, ?, ?, ?)", (account_id, calc_to_date, min_balance, rate, interest, days))
                journal_voucher_num = generate_voucher_number('JOURNAL')
                conn.execute("INSERT INTO journal_vouchers (voucher_number, voucher_date, description, total_amount, status, created_by) VALUES (?, ?, ?, ?, 'POSTED', ?)", (journal_voucher_num, calc_to_date, f"SB Interest - A/C {account_number}", interest, created_by_user_id))
                jv_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?, 'Interest Paid on SB', ?, 0, ?)", (jv_id, interest, f"Interest A/C {account_number}: {days} days @ {rate}%"))
                conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?, 'SB Account - ' || ?, 0, ?, ?)", (jv_id, account_number, interest, f"Interest credited to A/C {account_number}"))
                interest_posted.append({'account_id': account_id, 'account_number': account_number, 'customer_id': customer_id, 'min_balance': min_balance, 'balance_before': balance, 'interest': interest, 'new_balance': new_balance, 'rate': rate, 'days': days, 'from_date': actual_from_date, 'to_date': calc_to_date, 'journal_voucher': journal_voucher_num, 'total_interest_earned': new_total_interest, 'maturity_value': new_balance})
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
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('admin', hash_password('admin123'), 'admin'))
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
    if FPDF is None: return None
    pdf = BankPDF(); pdf.alias_nb_pages(); pdf.add_page()
    if report_type == 'trial_balance':
        pdf.set_font('Arial', 'B', 14); pdf.cell(0, 10, 'TRIAL BALANCE', 0, 1, 'C')
        pdf.set_font('Arial', '', 10); pdf.cell(0, 5, f'As on: {data["date"]}', 0, 1, 'C'); pdf.ln(10)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(10, 7, 'S.No', 1); pdf.cell(90, 7, 'Account Head', 1); pdf.cell(45, 7, 'Debit (Rs.)', 1, 0, 'R'); pdf.cell(45, 7, 'Credit (Rs.)', 1, 1, 'R')
        pdf.set_font('Arial', '', 9); td_pdf=0; tc_pdf=0
        for i, entry in enumerate(data['entries'], 1):
            pdf.cell(10, 6, str(i), 1); pdf.cell(90, 6, entry['account_head'], 1)
            pdf.cell(45, 6, f"{entry['debit']:,.2f}", 1, 0, 'R'); pdf.cell(45, 6, f"{entry['credit']:,.2f}", 1, 1, 'R')
            td_pdf += entry['debit']; tc_pdf += entry['credit']
        pdf.set_font('Arial', 'B', 10); pdf.cell(100, 7, 'TOTAL', 1); pdf.cell(45, 7, f"{td_pdf:,.2f}", 1, 0, 'R'); pdf.cell(45, 7, f"{tc_pdf:,.2f}", 1, 1, 'R')
    pdf.output(filename)
    return filename

# ==================== SESSION STATE ====================

def init_session_state():
    if 'user' not in st.session_state: st.session_state.user = None
    if 'page' not in st.session_state: st.session_state.page = 'dashboard'

# ==================== THEME-AWARE CSS ====================

def load_theme_css():
    st.markdown("""
    <style>
    /* ========== ROOT VARIABLES FOR LIGHT/DARK MODE ========== */
    :root {
        --bg-primary: #ffffff;
        --bg-secondary: #f8fafc;
        --bg-card: #ffffff;
        --text-primary: #0f172a;
        --text-secondary: #475569;
        --text-muted: #94a3b8;
        --border-color: #e2e8f0;
        --border-light: #f1f5f9;
        --accent-1: #3b82f6;
        --accent-2: #8b5cf6;
        --accent-3: #ec4899;
        --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
        --shadow-md: 0 4px 6px rgba(0,0,0,0.07);
        --shadow-lg: 0 10px 25px rgba(0,0,0,0.1);
        --gradient-1: linear-gradient(135deg, #3b82f6, #8b5cf6);
        --gradient-2: linear-gradient(135deg, #8b5cf6, #ec4899);
        --input-bg: #ffffff;
        --input-border: #e2e8f0;
        --input-text: #0f172a;
        --input-placeholder: #94a3b8;
        --table-header-bg: #3b82f6;
        --table-header-text: #ffffff;
        --table-row-hover: #f1f5f9;
        --table-row-alt: #f8fafc;
        --expander-bg: #f8fafc;
        --expander-border: #e2e8f0;
        --sidebar-bg: #0f172a;
        --sidebar-text: #ffffff;
        --sidebar-btn-bg: rgba(255,255,255,0.1);
        --sidebar-btn-hover: rgba(59,130,246,0.3);
    }

    /* ========== DARK MODE OVERRIDES ========== */
    @media (prefers-color-scheme: dark) {
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #1e293b;
            --text-primary: #f1f5f9;
            --text-secondary: #cbd5e1;
            --text-muted: #64748b;
            --border-color: #334155;
            --border-light: #1e293b;
            --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.4);
            --shadow-lg: 0 10px 25px rgba(0,0,0,0.5);
            --input-bg: #1e293b;
            --input-border: #334155;
            --input-text: #f1f5f9;
            --input-placeholder: #64748b;
            --table-row-hover: #334155;
            --table-row-alt: #1e293b;
            --expander-bg: #1e293b;
            --expander-border: #334155;
        }
    }

    /* ========== GLOBAL STYLES ========== */
    .stApp {
        background-color: var(--bg-primary);
    }

    .main .block-container {
        padding-top: 0.5rem;
        padding-bottom: 1rem;
        max-width: 1400px;
    }

    /* ========== HEADER ========== */
    .app-header {
        background: var(--gradient-1);
        color: white;
        padding: 0.8rem 2rem;
        border-radius: 0 0 20px 20px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: var(--shadow-lg);
        position: sticky;
        top: 0;
        z-index: 100;
    }

    .app-header h1 {
        margin: 0;
        font-size: 1.5rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }

    .app-header .user-info {
        display: flex;
        align-items: center;
        gap: 1rem;
        font-weight: 500;
    }

    /* ========== CARDS ========== */
    .card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: var(--shadow-sm);
        transition: all 0.3s ease;
    }

    .card:hover {
        box-shadow: var(--shadow-md);
    }

    .card-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 1rem;
        padding-bottom: 0.8rem;
        border-bottom: 2px solid var(--border-color);
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* ========== METRIC CARDS ========== */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 1.3rem 1rem;
        text-align: center;
        box-shadow: var(--shadow-sm);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 4px;
        border-radius: 16px 16px 0 0;
    }

    .metric-card.c1::before { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
    .metric-card.c2::before { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
    .metric-card.c3::before { background: linear-gradient(90deg, #ec4899, #f472b6); }
    .metric-card.c4::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }

    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-lg);
    }

    .metric-card .icon {
        font-size: 2rem;
        display: block;
        margin-bottom: 0.3rem;
    }

    .metric-card h3 {
        font-size: 1.8rem;
        margin: 0.3rem 0;
        font-weight: 800;
        color: var(--text-primary);
    }

    .metric-card p {
        margin: 0;
        font-size: 0.8rem;
        color: var(--text-secondary);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    @media (max-width: 768px) {
        .metric-grid { grid-template-columns: repeat(2, 1fr); }
        .metric-card h3 { font-size: 1.3rem; }
    }

    /* ========== INPUT FIELDS - THEME AWARE ========== */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div,
    .stDateInput > div > div > input {
        background-color: var(--input-bg) !important;
        color: var(--input-text) !important;
        border: 2px solid var(--input-border) !important;
        border-radius: 10px !important;
        padding: 0.6rem 0.8rem !important;
        font-size: 0.9rem !important;
        transition: all 0.2s ease !important;
    }

    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {
        color: var(--input-placeholder) !important;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > div:focus,
    .stDateInput > div > div > input:focus {
        border-color: var(--accent-1) !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
    }

    /* ========== BUTTONS ========== */
    .stButton > button {
        width: 100%;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
        border: none;
        padding: 0.6rem 1.2rem;
        font-size: 0.9rem;
        letter-spacing: 0.3px;
        box-shadow: var(--shadow-sm);
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-lg);
    }

    .stButton > button[kind="primary"] {
        background: var(--gradient-1);
        color: white;
    }

    .stButton > button[kind="secondary"] {
        background: var(--bg-card);
        color: var(--text-primary);
        border: 2px solid var(--border-color);
    }

    /* ========== TABLES ========== */
    .stDataFrame {
        border-radius: 12px !important;
        overflow: hidden !important;
        border: 1px solid var(--border-color) !important;
    }

    .stDataFrame thead th {
        background: var(--gradient-1) !important;
        color: var(--table-header-text) !important;
        font-weight: 600 !important;
        padding: 0.7rem 0.8rem !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .stDataFrame tbody td {
        padding: 0.6rem 0.8rem !important;
        font-size: 0.85rem !important;
        color: var(--text-primary) !important;
        border-bottom: 1px solid var(--border-light) !important;
    }

    .stDataFrame tbody tr:nth-child(even) {
        background: var(--table-row-alt) !important;
    }

    .stDataFrame tbody tr:hover {
        background: var(--table-row-hover) !important;
    }

    /* ========== TABS ========== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: var(--bg-secondary);
        padding: 5px;
        border-radius: 12px;
        border: 1px solid var(--border-color);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 0.5rem 1.2rem;
        font-weight: 600;
        font-size: 0.85rem;
        color: var(--text-secondary);
        transition: all 0.2s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: var(--border-color);
        color: var(--text-primary);
    }

    .stTabs [aria-selected="true"] {
        background: var(--gradient-1) !important;
        color: white !important;
        box-shadow: var(--shadow-md);
    }

    /* ========== EXPANDERS ========== */
    .streamlit-expanderHeader {
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 0.7rem 1rem !important;
        background: var(--expander-bg) !important;
        border: 2px solid var(--expander-border) !important;
        color: var(--text-primary) !important;
        transition: all 0.2s ease !important;
    }

    .streamlit-expanderHeader:hover {
        border-color: var(--accent-1) !important;
    }

    /* ========== SIDEBAR ========== */
    [data-testid="stSidebar"] {
        background: var(--sidebar-bg) !important;
        border-right: none !important;
    }

    [data-testid="stSidebar"] * {
        color: var(--sidebar-text) !important;
    }

    [data-testid="stSidebar"] .stButton > button {
        background: var(--sidebar-btn-bg) !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        color: white !important;
        text-align: left;
        padding: 0.6rem 0.8rem;
        font-weight: 500;
        font-size: 0.85rem;
        border-radius: 8px;
        transition: all 0.2s ease;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        background: var(--sidebar-btn-hover) !important;
        border-color: transparent !important;
        transform: translateX(4px);
    }

    /* ========== METRICS ========== */
    [data-testid="stMetricValue"] {
        font-weight: 800 !important;
        color: var(--text-primary) !important;
    }

    [data-testid="stMetricLabel"] {
        color: var(--text-secondary) !important;
    }

    /* ========== ALERTS ========== */
    .alert {
        padding: 1rem 1.2rem;
        border-radius: 12px;
        margin: 0.8rem 0;
        font-weight: 500;
        border-left: 4px solid;
    }

    .alert-info { background: rgba(59,130,246,0.1); border-color: #3b82f6; color: var(--text-primary); }
    .alert-success { background: rgba(16,185,129,0.1); border-color: #10b981; color: var(--text-primary); }
    .alert-warning { background: rgba(245,158,11,0.1); border-color: #f59e0b; color: var(--text-primary); }
    .alert-error { background: rgba(239,68,68,0.1); border-color: #ef4444; color: var(--text-primary); }

    /* ========== LOGIN PAGE ========== */
    .login-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 80vh;
    }

    .login-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 20px;
        padding: 2.5rem;
        width: 400px;
        box-shadow: var(--shadow-lg);
    }

    /* ========== SCROLLBAR ========== */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--text-muted); border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# ==================== MAIN APP ====================

def main():
    st.set_page_config(page_title="🏦 Banking System", page_icon="🏦", layout="wide", initial_sidebar_state="expanded")
    init_database()
    create_default_admin()
    init_session_state()
    load_theme_css()
    
    if st.session_state.user is None:
        show_login_page()
    else:
        show_main_app()

def show_login_page():
    st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align:center;margin-bottom:1.5rem;">
        <h1 style="font-size:3rem;margin:0;">🏦</h1>
        <h2 style="margin:0.5rem 0;color:var(--text-primary);font-weight:700;">Banking System</h2>
        <p style="color:var(--text-secondary);font-size:0.9rem;">Enterprise Management Platform</p>
    </div>
    """, unsafe_allow_html=True)
    
    username = st.text_input("Username", placeholder="Enter username", key="login_user")
    password = st.text_input("Password", type="password", placeholder="Enter password", key="login_pass")
    
    if st.button("🔑 Sign In", use_container_width=True, type="primary", key="btn_login"):
        user = login_user(username, password)
        if user:
            st.session_state.user = {'id': user[0], 'username': user[1], 'role': user[3]}
            st.session_state.page = 'dashboard'
            st.rerun()
        else:
            st.error("Invalid credentials")
    
    st.divider()
    st.markdown('<p style="text-align:center;color:var(--text-muted);font-size:0.8rem;">Demo: admin / admin123</p>', unsafe_allow_html=True)
    
    st.markdown('</div></div>', unsafe_allow_html=True)

def show_main_app():
    # Header
    st.markdown(f"""
    <div class="app-header">
        <h1>🏦 Banking System</h1>
        <div class="user-info">
            <span>👤 {st.session_state.user['username']}</span>
            <span style="font-size:0.75rem;opacity:0.8;">({st.session_state.user['role'].upper()})</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:1rem 0;">
            <h2 style="margin:0;font-weight:700;font-size:1.2rem;">🏦 Navigation</h2>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
        
        if st.session_state.user['role'] in ['admin', 'staff']:
            menu = {
                'dashboard': '📊 Dashboard', 'customer_management': '👥 Customers',
                'kyc_verification': '🔍 KYC', 'create_sb_account': '🏦 New Account',
                'sb_accounts': '💰 SB Accounts', 'fixed_deposits': '💎 FD',
                'recurring_deposits': '🔄 RD', 'transactions': '💳 Transactions',
                'journal_vouchers': '📝 JV', 'income_expenses': '📈 Income/Exp',
                'interest_calculation': '📊 Interest', 'trial_balance': '⚖️ Trial Bal',
                'balance_sheet': '📊 Balance Sheet', 'profit_loss': '💵 P&L',
                'reports': '📋 Reports'
            }
        else:
            menu = {'dashboard': '📊 Dashboard', 'my_accounts': '💰 My Accounts',
                    'my_transactions': '💳 My Transactions', 'my_details': '👤 My Details'}
        
        for k, v in menu.items():
            if st.sidebar.button(v, key=f"m_{k}", use_container_width=True):
                st.session_state.page = k
                st.rerun()
        
        st.divider()
        if st.sidebar.button("🚪 Sign Out", use_container_width=True, key="btn_out"):
            st.session_state.user = None; st.session_state.page = 'dashboard'; st.rerun()
    
    # Route to page
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
    conn = get_db()
    customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    active_sb = conn.execute("SELECT COUNT(*) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    total_bal = conn.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    total_int = conn.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    pending_kyc = conn.execute("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'").fetchone()[0]
    
    st.markdown('<div class="metric-grid">', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-card c1"><span class="icon">👥</span><h3>{customers}</h3><p>Customers</p></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-card c2"><span class="icon">💰</span><h3>{active_sb}</h3><p>Active SB</p></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-card c3"><span class="icon">🏦</span><h3>₹{total_bal+total_int:,.0f}</h3><p>SB Maturity</p></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-card c4"><span class="icon">🔍</span><h3>{pending_kyc}</h3><p>Pending KYC</p></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="card"><div class="card-header">📋 Recent Transactions</div>', unsafe_allow_html=True)
        txns = conn.execute("SELECT t.transaction_id, c.first_name||' '||c.last_name, t.transaction_type, t.amount, t.created_at FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id ORDER BY t.created_at DESC LIMIT 8").fetchall()
        if txns:
            df = pd.DataFrame(txns, columns=['ID','Customer','Type','Amount','Date'])
            st.dataframe(df.style.format({'Amount':'₹{:,.2f}'}), use_container_width=True, height=280)
        else: st.info("No transactions")
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="card"><div class="card-header">📊 Account Distribution</div>', unsafe_allow_html=True)
        acc_types = conn.execute("SELECT account_type, COUNT(*) FROM accounts WHERE status='ACTIVE' GROUP BY account_type").fetchall()
        if acc_types:
            df_a = pd.DataFrame(acc_types, columns=['Type','Count'])
            fig = px.pie(df_a, values='Count', names='Type', hole=0.5, color_discrete_sequence=['#3b82f6','#8b5cf6','#ec4899'])
            fig.update_layout(height=280, margin=dict(t=10,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

def show_customer_management():
    t1, t2 = st.tabs(["📝 Register", "👥 View"])
    with t1:
        st.markdown('<div class="card"><div class="card-header">New Customer Registration</div>', unsafe_allow_html=True)
        with st.form("cr"):
            c1, c2 = st.columns(2)
            with c1:
                fn = st.text_input("First Name *"); ln = st.text_input("Last Name *")
                dob = st.date_input("DOB *", min_value=date(1900,1,1), max_value=date.today())
                email = st.text_input("Email *"); phone = st.text_input("Phone *")
            with c2:
                pan = st.text_input("PAN *"); aadhar = st.text_input("Aadhar *")
                addr = st.text_area("Address"); city = st.text_input("City")
                state = st.text_input("State"); pin = st.text_input("PIN")
            x1, x2 = st.columns(2)
            with x1: pan_doc = st.file_uploader("PAN Card *", type=['jpg','jpeg','png','pdf'], key="pu")
            with x2: aadhar_doc = st.file_uploader("Aadhar Card *", type=['jpg','jpeg','png','pdf'], key="au")
            if st.form_submit_button("✨ Register", use_container_width=True):
                if not all([fn, ln, email, phone, pan, aadhar]): st.error("Fill all fields")
                elif not pan_doc or not aadhar_doc: st.error("Upload documents")
                else:
                    try:
                        c = get_db(); cid = generate_id('CUST')
                        c.execute("INSERT INTO customers (customer_id,first_name,last_name,date_of_birth,email,phone,address,city,state,pincode,pan_number,aadhar_number,pan_document,aadhar_document) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                (cid,fn,ln,dob,email,phone,addr,city,state,pin,pan,aadhar,pan_doc.read(),aadhar_doc.read()))
                        c.commit(); c.close()
                        st.success(f"✅ Registered! ID: {cid}"); st.balloons()
                    except Exception as e: st.error(str(e))
        st.markdown('</div>', unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="card"><div class="card-header">Customer Directory</div>', unsafe_allow_html=True)
        c = get_db()
        custs = c.execute("SELECT customer_id,first_name,last_name,email,phone,city,kyc_status FROM customers ORDER BY customer_id DESC").fetchall()
        if custs: st.dataframe(pd.DataFrame(custs, columns=['ID','First','Last','Email','Phone','City','KYC']), use_container_width=True, height=400)
        else: st.info("No customers")
        c.close()
        st.markdown('</div>', unsafe_allow_html=True)

def show_kyc_verification():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("⛔ Unauthorized"); return
    c = get_db()
    pending = c.execute("SELECT * FROM customers WHERE kyc_status='PENDING' ORDER BY created_at").fetchall()
    if not pending: st.markdown('<div class="alert alert-success">✅ All verified!</div>', unsafe_allow_html=True)
    else:
        for cust in pending:
            with st.expander(f"📄 {cust[3]} {cust[4]} - {cust[2]}", expanded=True):
                x1,x2=st.columns(2)
                with x1: st.write(f"**{cust[3]} {cust[4]}** | {cust[7]} | {cust[8]} | PAN:{cust[12]}")
                with x2:
                    if cust[16]:
                        try: st.image(cust[16], width=200)
                        except: st.info("Doc uploaded")
                b1,b2=st.columns(2)
                with b1:
                    if st.button("✅ Approve", key=f"a_{cust[0]}", use_container_width=True, type="primary"):
                        c.execute("UPDATE customers SET kyc_status='VERIFIED',kyc_verified_by=?,kyc_verified_at=CURRENT_TIMESTAMP WHERE id=?",(st.session_state.user['id'],cust[0]))
                        if not c.execute("SELECT id FROM accounts WHERE customer_id=? AND account_type='SB' AND status='ACTIVE'",(cust[0],)).fetchone():
                            c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate,last_interest_calculation,total_interest_earned) VALUES (?,?,'SB',0.00,3.50,DATE('now'),0.00)",(generate_account_number('SB'),cust[0]))
                        c.commit(); st.success("✅ Approved!"); st.rerun()
                with b2:
                    if st.button("❌ Reject", key=f"r_{cust[0]}", use_container_width=True):
                        c.execute("UPDATE customers SET kyc_status='REJECTED' WHERE id=?",(cust[0],)); c.commit(); st.rerun()
    c.close()

def show_create_sb_account():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("⛔ Unauthorized"); return
    c = get_db()
    custs = c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c WHERE c.kyc_status='VERIFIED' AND NOT EXISTS (SELECT 1 FROM accounts a WHERE a.customer_id=c.id AND a.account_type='SB' AND a.status='ACTIVE')").fetchall()
    if not custs: st.markdown('<div class="alert alert-success">✅ All have SB accounts!</div>', unsafe_allow_html=True); return
    st.markdown('<div class="card"><div class="card-header">Open New SB Account</div>', unsafe_allow_html=True)
    sel = st.selectbox("Customer", [f"{x[1]} - {x[2]}" for x in custs])
    if sel:
        idx = [f"{x[1]} - {x[2]}" for x in custs].index(sel); cust = custs[idx]
        with st.form("sb"):
            x1,x2=st.columns(2)
            with x1: rate=st.number_input("Rate (%)",0.0,10.0,3.5,0.25)
            with x2: bal=st.number_input("Opening Bal (₹)",0.0,step=100.0)
            if st.form_submit_button("✨ Create", use_container_width=True):
                an=generate_account_number('SB')
                c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate,last_interest_calculation,total_interest_earned) VALUES (?,?,'SB',?,?,DATE('now'),0.00)",(an,cust[0],bal,rate))
                c.commit(); st.success(f"✅ Created: {an}"); st.balloons()
    st.markdown('</div>', unsafe_allow_html=True); c.close()

def show_sb_accounts():
    c = get_db()
    t1,t2,t3,t4=st.tabs(["📋 List","💸 Transact","📜 Statement","📈 Maturity"])
    with t1:
        st.markdown('<div class="card"><div class="card-header">SB Accounts</div>', unsafe_allow_html=True)
        if st.session_state.user['role']=='customer':
            accs=c.execute("SELECT a.account_number,c.first_name||' '||c.last_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND c.user_id=?",(st.session_state.user['id'],)).fetchall()
        else:
            accs=c.execute("SELECT a.account_number,c.first_name||' '||c.last_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND c.kyc_status='VERIFIED'").fetchall()
        if accs:
            data=[{'Account':a[0],'Customer':a[1],'Principal':a[2],'Rate':f"{a[3]:.2f}%",'Interest':a[4],'Maturity':a[2]+a[4]} for a in accs]
            st.dataframe(pd.DataFrame(data).style.format({'Principal':'₹{:,.2f}','Interest':'₹{:,.2f}','Maturity':'₹{:,.2f}'}),use_container_width=True,height=350)
        else: st.info("No accounts")
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="card"><div class="card-header">Deposit / Withdraw</div>', unsafe_allow_html=True)
        if st.session_state.user['role']=='customer':
            accs=c.execute("SELECT a.id,a.account_number,c.first_name||' '||c.last_name,a.balance,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND c.user_id=?",(st.session_state.user['id'],)).fetchall()
        else:
            accs=c.execute("SELECT a.id,a.account_number,c.first_name||' '||c.last_name,a.balance,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        if accs:
            sel=st.selectbox("Account",[f"{a[1]} - {a[2]} (Maturity: ₹{a[3]+a[4]:,.2f})" for a in accs])
            if sel:
                idx=[f"{a[1]} - {a[2]} (Maturity: ₹{a[3]+a[4]:,.2f})" for a in accs].index(sel); acc=accs[idx]
                tt=st.radio("Type",["💰 Deposit","💸 Withdraw"],horizontal=True)
                with st.form("tx"):
                    amt=st.number_input("Amount (₹)",min_value=0.01,step=100.0); desc=st.text_input("Desc"); mode=st.selectbox("Mode",["CASH","TRANSFER","CHEQUE"])
                    if st.form_submit_button("✨ Process",use_container_width=True):
                        at="DEPOSIT" if "Deposit" in tt else "WITHDRAWAL"
                        if at=="WITHDRAWAL" and amt>acc[3]: st.error("❌ Insufficient!")
                        else:
                            nb=acc[3]+amt if at=="DEPOSIT" else acc[3]-amt; tdb="CREDIT" if at=="DEPOSIT" else "DEBIT"; vt="RECEIPT" if at=="DEPOSIT" else "PAYMENT"
                            c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,?,?,?,?,?,?,?,?)",(generate_id('TXN'),acc[0],tdb,amt,nb,desc,mode,vt,generate_voucher_number(vt),st.session_state.user['id']))
                            c.execute("UPDATE accounts SET balance=? WHERE id=?",(nb,acc[0])); c.commit()
                            st.success(f"✅ Done! New Maturity: ₹{nb+acc[4]:,.2f}"); st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)
    with t3:
        st.markdown('<div class="card"><div class="card-header">Account Statement</div>',unsafe_allow_html=True)
        if st.session_state.user['role']=='customer':
            accs=c.execute("SELECT a.id,a.account_number,c.first_name||' '||c.last_name FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND c.user_id=?",(st.session_state.user['id'],)).fetchall()
        else:
            accs=c.execute("SELECT a.id,a.account_number,c.first_name||' '||c.last_name FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        if accs:
            sel=st.selectbox("Account",[f"{a[1]} - {a[2]}" for a in accs],key="ss")
            if sel:
                aid=[a[0] for a in accs if f"{a[1]} - {a[2]}"==sel][0]
                x1,x2=st.columns(2)
                with x1: fd=st.date_input("From",date.today()-timedelta(days=30),key="sf")
                with x2: td=st.date_input("To",date.today(),key="st")
                txns=c.execute("SELECT transaction_id,created_at,transaction_type,amount,balance_after,description,voucher_number FROM transactions WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ? ORDER BY created_at DESC",(aid,fd,td)).fetchall()
                if txns: st.dataframe(pd.DataFrame(txns,columns=['ID','Date','Type','Amount','Balance','Desc','Voucher']).style.format({'Amount':'₹{:,.2f}','Balance':'₹{:,.2f}'}),use_container_width=True,height=350)
        st.markdown('</div>',unsafe_allow_html=True)
    with t4:
        st.markdown('<div class="card"><div class="card-header">Maturity Details</div>',unsafe_allow_html=True)
        if st.session_state.user['role']=='customer':
            accs=c.execute("SELECT a.account_number,c.first_name||' '||c.last_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND c.user_id=?",(st.session_state.user['id'],)).fetchall()
        else:
            accs=c.execute("SELECT a.account_number,c.first_name||' '||c.last_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB'").fetchall()
        if accs:
            data=[{'Account':a[0],'Customer':a[1],'Principal':a[2],'Rate':f"{a[3]:.2f}%",'Interest':a[4],'Maturity':a[2]+a[4]} for a in accs]
            st.dataframe(pd.DataFrame(data).style.format({'Principal':'₹{:,.2f}','Interest':'₹{:,.2f}','Maturity':'₹{:,.2f}'}),use_container_width=True)
            x1,x2,x3=st.columns(3)
            with x1: st.metric("Principal",f"₹{sum(d['Principal'] for d in data):,.2f}")
            with x2: st.metric("Interest",f"₹{sum(d['Interest'] for d in data):,.2f}")
            with x3: st.metric("Maturity",f"₹{sum(d['Maturity'] for d in data):,.2f}")
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def show_interest_calculation():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("⛔ Unauthorized"); return
    c=get_db()
    t1,t2,t3=st.tabs(["🧮 Calculate","📊 History","📈 Impact"])
    with t1:
        st.markdown('<div class="card"><div class="card-header">Calculate & Post Interest</div>',unsafe_allow_html=True)
        x1,x2=st.columns(2)
        with x1: cfd=st.date_input("From",date.today().replace(day=1),key="if")
        with x2: ctd=st.date_input("To",date.today(),key="it")
        if cfd>ctd: st.error("Invalid range")
        else: st.info(f"Period: {cfd.strftime('%d-%b-%Y')} → {ctd.strftime('%d-%b-%Y')} ({(ctd-cfd).days+1} days)")
        accs=c.execute("SELECT a.id,a.account_number,c.first_name||' '||c.last_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        if accs:
            b1,b2=st.columns(2)
            with b1:
                if st.button("✨ Calculate & Post",use_container_width=True,type="primary",key="cp"):
                    if cfd>ctd: st.error("Invalid!")
                    else:
                        s,r=calculate_and_post_sb_interest(st.session_state.user['id'],cfd,ctd)
                        if s=="SUCCESS" and len(r)>0: st.success(f"✅ Posted! Total: ₹{sum(x['interest'] for x in r):,.2f}"); st.balloons()
                        else: st.info(s if s!="SUCCESS" else "No interest")
            with b2:
                if st.button("🔍 Preview",use_container_width=True,key="pv"):
                    pv=[]
                    for a in accs:
                        mb=get_minimum_balance(c,a[0],cfd,ctd)
                        if mb<=0: mb=a[3]
                        days=(ctd-cfd).days+1
                        if days>0:
                            interest=calculate_sb_interest(mb,a[4] if a[4] else 3.5,days)
                            pv.append({'Account':a[1],'Customer':a[2],'Min Bal':mb,'Interest':interest,'New Maturity':a[3]+a[5]+interest})
                    if pv: st.dataframe(pd.DataFrame(pv).style.format({'Min Bal':'₹{:,.2f}','Interest':'₹{:,.2f}','New Maturity':'₹{:,.2f}'}),use_container_width=True)
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="card"><div class="card-header">Interest History</div>',unsafe_allow_html=True)
        h=c.execute("SELECT ic.calculation_date,a.account_number,c.first_name||' '||c.last_name,ic.principal_amount,ic.interest_rate,ic.interest_earned,ic.days_calculated FROM interest_calculations ic JOIN accounts a ON ic.account_id=a.id JOIN customers c ON a.customer_id=c.id ORDER BY ic.calculation_date DESC LIMIT 50").fetchall()
        if h: st.dataframe(pd.DataFrame(h,columns=['Date','Account','Customer','Principal','Rate','Interest','Days']).style.format({'Principal':'₹{:,.2f}','Interest':'₹{:,.2f}'}),use_container_width=True,height=350)
        else: st.info("No history")
        st.markdown('</div>',unsafe_allow_html=True)
    with t3:
        st.markdown('<div class="card"><div class="card-header">JV Impact on Trial Balance</div>',unsafe_allow_html=True)
        jvs=c.execute("SELECT jv.voucher_number,jv.voucher_date,jv.description,jv.total_amount,je.account_head,je.debit_amount,je.credit_amount,je.description FROM journal_vouchers jv JOIN journal_entries je ON jv.id=je.voucher_id WHERE (je.account_head='Interest Paid on SB' OR je.account_head LIKE '%SB Account%') AND jv.status='POSTED' ORDER BY jv.voucher_date DESC LIMIT 50").fetchall()
        if jvs:
            jd={}
            for j in jvs:
                vn=j[0]
                if vn not in jd: jd[vn]={'date':j[1],'desc':j[2],'amt':j[3],'entries':[]}
                jd[vn]['entries'].append({'head':j[4],'debit':j[5],'credit':j[6],'desc':j[7]})
            for vn,d in jd.items():
                with st.expander(f"📄 {vn} - {d['date']} - ₹{d['amt']:,.2f}"):
                    for e in d['entries']:
                        bg="#fee2e2" if e['debit']>0 else "#d1fae5"
                        st.markdown(f'<div style="background:{bg};color:black;padding:0.6rem;border-radius:8px;margin:0.2rem 0;border-left:3px solid #3b82f6;"><b>{e["head"]}</b><br>Debit: ₹{e["debit"]:,.2f} | Credit: ₹{e["credit"]:,.2f}</div>',unsafe_allow_html=True)
            tj=sum(d['amt'] for d in jd.values()); st.success(f"✅ TB Impact: ₹{tj:,.2f} both sides")
        else: st.info("No JVs")
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def show_trial_balance():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("⛔ Unauthorized"); return
    c=get_db()
    st.markdown('<div class="card"><div class="card-header">Trial Balance</div>',unsafe_allow_html=True)
    if st.button("✨ Generate",use_container_width=True,type="primary",key="tb"):
        td=[]
        cash=c.execute("SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END),0) FROM transactions WHERE reference_type='CASH'").fetchone()[0]
        if abs(cash)>0: td.append({'head':'Cash in Hand','cat':'Asset','dr':max(cash,0),'cr':max(-cash,0),'ref':'Cash'})
        sb=c.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb>0: td.append({'head':'SB Deposits (Principal)','cat':'Liability','dr':0,'cr':sb,'ref':'SB balances'})
        jvl=c.execute("SELECT je.account_head,COALESCE(SUM(je.credit_amount),0),COALESCE(SUM(je.debit_amount),0),GROUP_CONCAT(DISTINCT jv.voucher_number) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE jv.status='POSTED' AND (je.account_head LIKE '%SB Account%' OR je.account_head LIKE '%Payable%' OR je.account_head LIKE '%Deposit%') GROUP BY je.account_head").fetchall()
        for e in jvl:
            h,cr,dr,jn=e[0],e[1],e[2],e[3] or ''; jl=jn.split(',') if jn else []; jr=', '.join(jl[:3])+('...' if len(jl)>3 else '') if jl else 'JV'
            if cr>dr: td.append({'head':h,'cat':'Liability','dr':dr,'cr':cr,'ref':f'JV: {jr}'})
        fd=c.execute("SELECT COALESCE(SUM(principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        if fd>0: td.append({'head':'Fixed Deposits','cat':'Liability','dr':0,'cr':fd,'ref':'FD'})
        rd=c.execute("SELECT COALESCE(SUM(monthly_amount*installments_paid),0) FROM recurring_deposits WHERE status='ACTIVE'").fetchone()[0]
        if rd>0: td.append({'head':'Recurring Deposits','cat':'Liability','dr':0,'cr':rd,'ref':'RD'})
        for it in ['Interest Earned','Fees & Charges','Commission Income','Other Income']:
            amt=c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type=?",(it,)).fetchone()[0]
            if amt>0: td.append({'head':it,'cat':'Income','dr':0,'cr':amt,'ref':'Income'})
        jve=c.execute("SELECT je.account_head,COALESCE(SUM(je.debit_amount),0),COALESCE(SUM(je.credit_amount),0),GROUP_CONCAT(DISTINCT jv.voucher_number) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE jv.status='POSTED' AND je.account_head NOT LIKE '%SB Account%' GROUP BY je.account_head").fetchall()
        for e in jve:
            h,dr,cr,jn=e[0],e[1],e[2],e[3] or ''; jl=jn.split(',') if jn else []; jr=', '.join(jl[:3])+('...' if len(jl)>3 else '') if jl else 'JV'
            if dr>0: td.append({'head':h,'cat':'Expense','dr':dr,'cr':0,'ref':f'JV: {jr}'})
            if cr>0: td.append({'head':h,'cat':'Income','dr':0,'cr':cr,'ref':f'JV: {jr}'})
        for et in ['Salary & Wages','Rent & Utilities','Operating Expenses','Administrative Expenses','Other Expenses']:
            amt=c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type=?",(et,)).fetchone()[0]
            if amt>0: td.append({'head':et,'cat':'Expense','dr':amt,'cr':0,'ref':'Expense'})
        tdr=sum(i['dr'] for i in td); tcr=sum(i['cr'] for i in td); diff=tcr-tdr
        if abs(diff)>0.01: td.append({'head':'Capital/Reserves','cat':'Capital','dr':max(-diff,0),'cr':max(diff,0),'ref':'Balance'})
        if td:
            df=pd.DataFrame(td)
            x1,x2,x3,x4=st.columns(4)
            with x1: st.metric("Assets",f"₹{sum(i['dr'] for i in td if i['cat']=='Asset'):,.2f}")
            with x2: st.metric("Liabilities",f"₹{sum(i['cr'] for i in td if i['cat']=='Liability'):,.2f}")
            with x3: st.metric("Income",f"₹{sum(i['cr'] for i in td if i['cat']=='Income'):,.2f}")
            with x4: st.metric("Expenses",f"₹{sum(i['dr'] for i in td if i['cat']=='Expense'):,.2f}")
            st.divider()
            for cat in ['Asset','Liability','Income','Expense','Capital']:
                cd=[i for i in td if i['cat']==cat]
                if cd:
                    st.markdown(f"**{cat}s**")
                    disp=pd.DataFrame(cd)[['head','dr','cr','ref']]; disp.columns=['Head','Debit','Credit','Ref']
                    st.dataframe(disp.style.format({'Debit':'₹{:,.2f}','Credit':'₹{:,.2f}'}),use_container_width=True,height=min(250,len(cd)*40))
            dft=df['dr'].sum(); cft=df['cr'].sum()
            st.divider()
            y1,y2,y3=st.columns(3)
            with y1: st.metric("Total Debit",f"₹{dft:,.2f}")
            with y2: st.metric("Total Credit",f"₹{cft:,.2f}")
            with y3:
                if abs(dft-cft)<0.01: st.success("✅ BALANCED!")
                else: st.error(f"❌ Diff: ₹{abs(dft-cft):,.2f}")
            sbi=sum(i['cr'] for i in td if 'SB Account' in i['head'])
            st.divider(); st.markdown(f"**💎 SB:** Principal ₹{sb:,.2f} + Interest ₹{sbi:,.2f} = Maturity ₹{sb+sbi:,.2f}")
            st.success(f"✅ {len([i for i in td if i['ref'].startswith('JV:')])} JV entries reflected")
            st.download_button("📥 CSV",df.to_csv(index=False),"tb.csv","text/csv",key="dtb")
        else: st.info("No data")
    st.markdown('</div>',unsafe_allow_html=True); c.close()

def show_balance_sheet():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("⛔ Unauthorized"); return
    c=get_db()
    st.markdown('<div class="card"><div class="card-header">Balance Sheet</div>',unsafe_allow_html=True)
    if st.button("✨ Generate",use_container_width=True,type="primary",key="bs"):
        cash=c.execute("SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END),0) FROM transactions WHERE reference_type='CASH'").fetchone()[0]
        sb_bal=c.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        sb_int=c.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb_int==0: sb_int=c.execute("SELECT COALESCE(SUM(credit_amount),0) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE je.account_head LIKE '%SB Account%' AND jv.status='POSTED'").fetchone()[0]
        fd=c.execute("SELECT COALESCE(SUM(principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        rd=c.execute("SELECT COALESCE(SUM(monthly_amount*installments_paid),0) FROM recurring_deposits WHERE status='ACTIVE'").fetchone()[0]
        fd_int=c.execute("SELECT COALESCE(SUM(maturity_amount-principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        ta=cash+sb_bal+fd+rd; tl=sb_int+fd_int+fd+rd+sb_bal; cap=ta-tl
        z1,z2=st.columns(2)
        with z1:
            st.markdown(f"""<div class="card"><h3>📊 ASSETS</h3>
            <p>💰 Cash: <b>₹{cash:,.2f}</b></p><p>🏦 SB Deposits: <b>₹{sb_bal:,.2f}</b></p>
            <p>💎 FD: <b>₹{fd:,.2f}</b></p><p>🔄 RD: <b>₹{rd:,.2f}</b></p>
            <hr><p><b>Total: ₹{ta:,.2f}</b></p></div>""",unsafe_allow_html=True)
        with z2:
            st.markdown(f"""<div class="card"><h3>📋 LIABILITIES</h3>
            <p>📈 SB Interest: <b>₹{sb_int:,.2f}</b></p><p>📈 FD Interest: <b>₹{fd_int:,.2f}</b></p>
            <p>🏦 SB Deposits: <b>₹{sb_bal:,.2f}</b></p><p>💎 FD: <b>₹{fd:,.2f}</b></p>
            <p>🔄 RD: <b>₹{rd:,.2f}</b></p><hr><p><b>Total: ₹{tl:,.2f}</b></p></div>""",unsafe_allow_html=True)
        st.markdown(f"""<div class="card"><h3>💰 CAPITAL</h3><p><b>Capital/Net Worth: ₹{cap:,.2f}</b></p></div>""",unsafe_allow_html=True)
        if abs(ta-(tl+cap))<0.01: st.success(f"✅ Balanced! A={ta:,.2f} = L={tl:,.2f} + C={cap:,.2f}")
    st.markdown('</div>',unsafe_allow_html=True); c.close()

def show_profit_loss():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("⛔ Unauthorized"); return
    c=get_db()
    st.markdown('<div class="card"><div class="card-header">Profit & Loss</div>',unsafe_allow_html=True)
    x1,x2=st.columns(2)
    with x1: fd=st.date_input("From",date.today().replace(month=1,day=1),key="plf")
    with x2: td=st.date_input("To",date.today(),key="plt")
    if st.button("✨ Generate",use_container_width=True,type="primary",key="pl"):
        inc=[('Interest Earned',c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Interest Earned' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),
             ('Fees',c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Fees & Charges' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),
             ('Commission',c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Commission Income' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),
             ('Other',c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Other Income' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0])]
        exp=[('Interest on SB',c.execute("SELECT COALESCE(SUM(debit_amount),0) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE je.account_head='Interest Paid on SB' AND jv.status='POSTED' AND DATE(jv.voucher_date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),
             ('Salary',c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Salary & Wages' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),
             ('Rent',c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Rent & Utilities' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),
             ('Operating',c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Operating Expenses' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),
             ('Admin',c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Administrative Expenses' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),
             ('Other',c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Other Expenses' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0])]
        ti=sum(i[1] for i in inc); te=sum(e[1] for e in exp); net=ti-te
        p1,p2=st.columns(2)
        with p1:
            st.markdown('<div class="card"><h3>📈 INCOME</h3>',unsafe_allow_html=True)
            for item,amt in inc: st.write(f"• {item}: ₹{amt:,.2f}")
            st.markdown(f'<hr><b>Total: ₹{ti:,.2f}</b></div>',unsafe_allow_html=True)
        with p2:
            st.markdown('<div class="card"><h3>📉 EXPENSES</h3>',unsafe_allow_html=True)
            for item,amt in exp:
                if amt>0: st.write(f"• {item}: ₹{amt:,.2f}")
            st.markdown(f'<hr><b>Total: ₹{te:,.2f}</b></div>',unsafe_allow_html=True)
        if net>=0: st.success(f"## 🎉 Net Profit: ₹{net:,.2f}")
        else: st.error(f"## 📉 Net Loss: ₹{abs(net):,.2f}")
    st.markdown('</div>',unsafe_allow_html=True); c.close()

def show_income_expenses():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("⛔ Unauthorized"); return
    c=get_db(); t1,t2=st.tabs(["💰 Income","💸 Expense"])
    with t1:
        st.markdown('<div class="card"><div class="card-header">Record Income</div>',unsafe_allow_html=True)
        with st.form("if"):
            x1,x2=st.columns(2)
            with x1: it=st.selectbox("Type",["Interest Earned","Fees & Charges","Commission Income","Other Income"]); amt=st.number_input("Amount",min_value=1.0,step=100.0)
            with x2: dt=st.date_input("Date",date.today(),key="id"); desc=st.text_area("Desc")
            if st.form_submit_button("✨ Record",use_container_width=True):
                c.execute("INSERT INTO income (income_id,income_type,amount,description,date,created_by) VALUES (?,?,?,?,?,?)",(generate_id('INC'),it,amt,desc,dt,st.session_state.user['id'])); c.commit()
                st.success(f"✅ ₹{amt:,.2f}")
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="card"><div class="card-header">Record Expense</div>',unsafe_allow_html=True)
        with st.form("ef"):
            x1,x2=st.columns(2)
            with x1: et=st.selectbox("Type",["Salary & Wages","Rent & Utilities","Operating Expenses","Administrative Expenses","Other Expenses"]); amt=st.number_input("Amount",min_value=1.0,step=100.0)
            with x2: dt=st.date_input("Date",date.today(),key="ed"); desc=st.text_area("Desc")
            if st.form_submit_button("✨ Record",use_container_width=True):
                c.execute("INSERT INTO expenses (expense_id,expense_type,amount,description,date,created_by) VALUES (?,?,?,?,?,?)",(generate_id('EXP'),et,amt,desc,dt,st.session_state.user['id'])); c.commit()
                st.success(f"✅ ₹{amt:,.2f}")
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def show_fixed_deposits():
    c=get_db(); t1,t2,t3=st.tabs(["📝 Open","📋 Active","🔔 Maturity"])
    with t1:
        st.markdown('<div class="card"><div class="card-header">Open FD</div>',unsafe_allow_html=True)
        custs=c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND c.kyc_status='VERIFIED' AND a.status='ACTIVE'").fetchall()
        if custs:
            sel=st.selectbox("Customer",[f"{x[1]} - {x[2]}" for x in custs])
            if sel:
                idx=[f"{x[1]} - {x[2]}" for x in custs].index(sel); cust=custs[idx]
                with st.form("fd"):
                    x1,x2=st.columns(2)
                    with x1: p=st.number_input("Principal",min_value=1000.0,step=1000.0,value=10000.0); t=st.selectbox("Tenure",[3,6,12,24,36,60]); r=st.number_input("Rate",3.0,10.0,6.5,0.25)
                    with x2: sd=st.date_input("Start",date.today(),key="fs"); nom=st.text_input("Nominee")
                    md=sd+timedelta(days=t*30); ma=calculate_fd_maturity(p,r,t)
                    st.info(f"Maturity: {md.strftime('%d-%m-%Y')} | Amount: ₹{ma:,.2f}")
                    if st.form_submit_button("✨ Open",use_container_width=True):
                        fdn=generate_id('FD'); an=generate_account_number('FD')
                        c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate) VALUES (?,?,'FD',0.00,?)",(an,cust[0],r))
                        aid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                        c.execute("INSERT INTO fixed_deposits (fd_number,account_id,principal_amount,interest_rate,start_date,maturity_date,maturity_amount,tenure_months,nominee_name) VALUES (?,?,?,?,?,?,?,?,?)",(fdn,aid,p,r,sd,md,ma,t,nom))
                        c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,'FD Deposit','FD_DEPOSIT','RECEIPT',?,?)",(generate_id('TXN'),aid,p,p,generate_voucher_number('RECEIPT'),st.session_state.user['id']))
                        c.commit(); st.success(f"✅ Opened: {fdn}"); st.balloons()
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="card"><div class="card-header">Active FDs</div>',unsafe_allow_html=True)
        fds=c.execute("SELECT fd.fd_number,c.first_name||' '||c.last_name,fd.principal_amount,fd.interest_rate,fd.start_date,fd.maturity_date,fd.maturity_amount FROM fixed_deposits fd JOIN accounts a ON fd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE fd.status='ACTIVE' ORDER BY fd.maturity_date").fetchall()
        if fds: st.dataframe(pd.DataFrame(fds,columns=['FD','Customer','Principal','Rate','Start','Maturity','Maturity Amt']).style.format({'Principal':'₹{:,.2f}','Maturity Amt':'₹{:,.2f}'}),use_container_width=True)
        else: st.info("No active FDs")
        st.markdown('</div>',unsafe_allow_html=True)
    with t3:
        st.markdown('<div class="card"><div class="card-header">Maturity Alerts</div>',unsafe_allow_html=True)
        today=date.today(); mat=c.execute("SELECT fd.fd_number,c.first_name||' '||c.last_name,fd.maturity_amount,fd.maturity_date FROM fixed_deposits fd JOIN accounts a ON fd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE fd.maturity_date BETWEEN ? AND ? AND fd.status='ACTIVE'",(today,today+timedelta(days=30))).fetchall()
        if mat: st.warning(f"🔔 {len(mat)} FD(s) maturing soon"); st.dataframe(pd.DataFrame(mat,columns=['FD','Customer','Amount','Date']).style.format({'Amount':'₹{:,.2f}'}),use_container_width=True)
        else: st.success("✅ None maturing soon")
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def show_recurring_deposits():
    c=get_db(); t1,t2,t3=st.tabs(["📝 Open","📋 Active","💳 Pay"])
    with t1:
        st.markdown('<div class="card"><div class="card-header">Open RD</div>',unsafe_allow_html=True)
        custs=c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND c.kyc_status='VERIFIED' AND a.status='ACTIVE'").fetchall()
        if custs:
            sel=st.selectbox("Customer",[f"{x[1]} - {x[2]}" for x in custs])
            if sel:
                idx=[f"{x[1]} - {x[2]}" for x in custs].index(sel); cust=custs[idx]
                with st.form("rd"):
                    x1,x2=st.columns(2)
                    with x1: m=st.number_input("Monthly",min_value=100.0,step=100.0,value=1000.0); t=st.selectbox("Tenure",[6,12,24,36,48,60]); r=st.number_input("Rate",3.0,10.0,6.0,0.25)
                    with x2: sd=st.date_input("Start",date.today(),key="rs"); nom=st.text_input("Nominee")
                    md=sd+timedelta(days=t*30); ma=calculate_rd_maturity(m,r,t)
                    st.info(f"Maturity: {md.strftime('%d-%m-%Y')} | Amount: ₹{ma:,.2f}")
                    if st.form_submit_button("✨ Open",use_container_width=True):
                        rdn=generate_id('RD'); an=generate_account_number('RD')
                        c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate) VALUES (?,?,'RD',0.00,?)",(an,cust[0],r))
                        aid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                        c.execute("INSERT INTO recurring_deposits (rd_number,account_id,monthly_amount,interest_rate,start_date,maturity_date,maturity_amount,tenure_months,total_installments,nominee_name) VALUES (?,?,?,?,?,?,?,?,?,?)",(rdn,aid,m,r,sd,md,ma,t,t,nom))
                        c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,'RD Install 1','RD_INSTALLMENT','RECEIPT',?,?)",(generate_id('TXN'),aid,m,m,generate_voucher_number('RECEIPT'),st.session_state.user['id']))
                        c.execute("UPDATE recurring_deposits SET installments_paid=1 WHERE rd_number=?",(rdn,)); c.commit(); st.success(f"✅ Opened: {rdn}"); st.balloons()
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="card"><div class="card-header">Active RDs</div>',unsafe_allow_html=True)
        rds=c.execute("SELECT rd.rd_number,c.first_name||' '||c.last_name,rd.monthly_amount,rd.interest_rate,rd.start_date,rd.maturity_date,rd.maturity_amount,rd.installments_paid,rd.total_installments FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE rd.status='ACTIVE' ORDER BY rd.maturity_date").fetchall()
        if rds:
            df=pd.DataFrame(rds,columns=['RD','Customer','Monthly','Rate','Start','Maturity','Maturity Amt','Paid','Total'])
            df['Progress']=df.apply(lambda r:f"{r['Paid']}/{r['Total']} ({r['Paid']/r['Total']*100:.0f}%)",axis=1)
            st.dataframe(df.style.format({'Monthly':'₹{:,.2f}','Maturity Amt':'₹{:,.2f}'}),use_container_width=True)
        st.markdown('</div>',unsafe_allow_html=True)
    with t3:
        st.markdown('<div class="card"><div class="card-header">Pay Installment</div>',unsafe_allow_html=True)
        rds=c.execute("SELECT rd.id,rd.rd_number,c.first_name||' '||c.last_name,rd.monthly_amount,rd.installments_paid,rd.total_installments,a.id FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE rd.status='ACTIVE' AND rd.installments_paid<rd.total_installments").fetchall()
        if rds:
            sel=st.selectbox("RD",[f"{r[1]} - {r[2]} ({r[4]}/{r[5]})" for r in rds])
            if sel:
                idx=[f"{r[1]} - {r[2]} ({r[4]}/{r[5]})" for r in rds].index(sel); rd=rds[idx]
                with st.form("pr"):
                    amt=st.number_input("Amount",value=float(rd[3]),min_value=float(rd[3]))
                    if st.form_submit_button("✨ Pay",use_container_width=True):
                        c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,?,'RD_INSTALLMENT','RECEIPT',?,?)",(generate_id('TXN'),rd[6],amt,amt,f"RD {rd[4]+1}/{rd[5]}",generate_voucher_number('RECEIPT'),st.session_state.user['id']))
                        np=rd[4]+1; c.execute("UPDATE recurring_deposits SET installments_paid=? WHERE id=?",(np,rd[0]))
                        if np>=rd[5]: c.execute("UPDATE recurring_deposits SET status='MATURED' WHERE id=?",(rd[0],))
                        c.commit(); st.success(f"✅ {np}/{rd[5]}"); st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def show_transactions():
    c=get_db()
    st.markdown('<div class="card"><div class="card-header">Transactions</div>',unsafe_allow_html=True)
    x1,x2,x3,x4=st.columns(4)
    with x1: at=st.selectbox("Account",["All","SB","FD","RD"])
    with x2: tt=st.selectbox("Type",["All","CREDIT","DEBIT"])
    with x3: fd=st.date_input("From",date.today()-timedelta(days=30),key="tf")
    with x4: td=st.date_input("To",date.today(),key="tt")
    q="SELECT t.transaction_id,c.first_name||' '||c.last_name,a.account_number,a.account_type,t.transaction_type,t.amount,t.balance_after,t.description,t.voucher_number,t.created_at FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE DATE(t.created_at) BETWEEN ? AND ?"
    params=[fd,td]
    if st.session_state.user['role']=='customer': q+=" AND c.user_id=?"; params.append(st.session_state.user['id'])
    if at!="All": q+=" AND a.account_type=?"; params.append(at)
    if tt!="All": q+=" AND t.transaction_type=?"; params.append(tt)
    q+=" ORDER BY t.created_at DESC LIMIT 200"
    txns=c.execute(q,params).fetchall()
    if txns: st.dataframe(pd.DataFrame(txns,columns=['ID','Customer','Account','Type','Action','Amount','Balance','Desc','Voucher','Date']).style.format({'Amount':'₹{:,.2f}','Balance':'₹{:,.2f}'}),use_container_width=True,height=400)
    else: st.info("No transactions")
    st.markdown('</div>',unsafe_allow_html=True); c.close()

def show_journal_vouchers():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("⛔ Unauthorized"); return
    c=get_db(); t1,t2=st.tabs(["📝 Create","📋 List"])
    with t1:
        st.markdown('<div class="card"><div class="card-header">Create JV</div>',unsafe_allow_html=True)
        with st.form("jv"):
            vd=st.date_input("Date",date.today(),key="jvd"); desc=st.text_area("Desc")
            n=st.number_input("Entries",2,10,2); entries=[]; td_v=0; tc_v=0
            for i in range(int(n)):
                st.markdown(f"**Entry {i+1}**")
                a1,a2,a3=st.columns(3)
                with a1: h=st.text_input(f"Head",key=f"jh{i}")
                with a2: d=st.number_input(f"Debit",min_value=0.0,step=100.0,key=f"jd{i}")
                with a3: c=st.number_input(f"Credit",min_value=0.0,step=100.0,key=f"jc{i}")
                td_v+=d; tc_v+=c; entries.append({'h':h,'d':d,'c':c})
            st.write(f"Debit: ₹{td_v:,.2f} | Credit: ₹{tc_v:,.2f}")
            if abs(td_v-tc_v)>0.01: st.error(f"Diff: ₹{abs(td_v-tc_v):,.2f}")
            if st.form_submit_button("✨ Create",use_container_width=True):
                if abs(td_v-tc_v)>0.01: st.error("Must balance!")
                else:
                    vn=generate_voucher_number('JOURNAL')
                    c.execute("INSERT INTO journal_vouchers (voucher_number,voucher_date,description,total_amount,created_by) VALUES (?,?,?,?,?)",(vn,vd,desc,td_v,st.session_state.user['id']))
                    vid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                    for e in entries:
                        if e['d']>0 or e['c']>0: c.execute("INSERT INTO journal_entries (voucher_id,account_head,debit_amount,credit_amount) VALUES (?,?,?,?)",(vid,e['h'],e['d'],e['c']))
                    c.commit(); st.success(f"✅ Created: {vn}"); st.balloons()
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="card"><div class="card-header">JV List</div>',unsafe_allow_html=True)
        vouchers=c.execute("SELECT jv.voucher_number,jv.voucher_date,jv.description,jv.total_amount,jv.status FROM journal_vouchers jv ORDER BY jv.created_at DESC").fetchall()
        if vouchers:
            for v in vouchers:
                sc={'DRAFT':'🟡','POSTED':'🟢','CANCELLED':'🔴'}
                with st.expander(f"{sc.get(v[4],'⚪')} {v[0]} - {v[1]} - ₹{v[3]:,.2f} ({v[4]})"):
                    st.write(f"**{v[2]}**")
                    entries=c.execute("SELECT account_head,debit_amount,credit_amount FROM journal_entries WHERE voucher_id=(SELECT id FROM journal_vouchers WHERE voucher_number=?)",(v[0],)).fetchall()
                    if entries: st.dataframe(pd.DataFrame(entries,columns=['Head','Debit','Credit']).style.format({'Debit':'₹{:,.2f}','Credit':'₹{:,.2f}'}),use_container_width=True)
                    if v[4]=='DRAFT':
                        st.divider(); b1,b2=st.columns(2)
                        with b1:
                            if st.button("✅ Post",key=f"po_{v[0]}",use_container_width=True,type="primary"):
                                c.execute("UPDATE journal_vouchers SET status='POSTED',posted_by=?,posted_at=CURRENT_TIMESTAMP WHERE voucher_number=?",(st.session_state.user['id'],v[0])); c.commit(); st.success("Posted!"); st.rerun()
                        with b2:
                            if st.button("❌ Cancel",key=f"ca_{v[0]}",use_container_width=True):
                                c.execute("UPDATE journal_vouchers SET status='CANCELLED' WHERE voucher_number=?",(v[0],)); c.commit(); st.warning("Cancelled!"); st.rerun()
        else: st.info("No vouchers")
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def show_reports():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("⛔ Unauthorized"); return
    rt=st.selectbox("Report",["Customer List","Interest Report","Daily Transactions"])
    c=get_db()
    st.markdown('<div class="card"><div class="card-header">Report</div>',unsafe_allow_html=True)
    if rt=="Customer List":
        custs=c.execute("SELECT customer_id,first_name,last_name,email,phone,city,kyc_status FROM customers ORDER BY customer_id DESC").fetchall()
        if custs: st.dataframe(pd.DataFrame(custs,columns=['ID','First','Last','Email','Phone','City','KYC']),use_container_width=True)
    elif rt=="Interest Report":
        calcs=c.execute("SELECT ic.calculation_date,a.account_number,c.first_name||' '||c.last_name,ic.principal_amount,ic.interest_rate,ic.interest_earned,ic.days_calculated FROM interest_calculations ic JOIN accounts a ON ic.account_id=a.id JOIN customers c ON a.customer_id=c.id ORDER BY ic.calculation_date DESC").fetchall()
        if calcs: st.dataframe(pd.DataFrame(calcs,columns=['Date','Account','Customer','Principal','Rate','Interest','Days']).style.format({'Principal':'₹{:,.2f}','Interest':'₹{:,.2f}'}),use_container_width=True)
    elif rt=="Daily Transactions":
        rd=st.date_input("Date",date.today(),key="rpd")
        txns=c.execute("SELECT t.transaction_id,c.first_name||' '||c.last_name,a.account_type,t.transaction_type,t.amount,t.voucher_number FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE DATE(t.created_at)=?",(rd,)).fetchall()
        if txns: st.dataframe(pd.DataFrame(txns,columns=['Txn','Customer','Type','Action','Amount','Voucher']).style.format({'Amount':'₹{:,.2f}'}),use_container_width=True)
        else: st.info(f"No transactions on {rd}")
    st.markdown('</div>',unsafe_allow_html=True); c.close()

def show_my_details():
    c=get_db()
    cust=c.execute("SELECT * FROM customers WHERE user_id=?",(st.session_state.user['id'],)).fetchone()
    if cust:
        st.markdown(f"""
        <div style="background:var(--gradient-1);color:white;padding:1.5rem;border-radius:16px;margin-bottom:1rem;">
            <h2>{cust[3]} {cust[4]}</h2>
            <p>📋 {cust[2]} | 📧 {cust[7]} | 📱 {cust[8]} | 🎂 {cust[5]}</p>
        </div>""",unsafe_allow_html=True)
        st.markdown('<div class="card"><div class="card-header">My SB Accounts</div>',unsafe_allow_html=True)
        accs=c.execute("SELECT account_number,balance,COALESCE(total_interest_earned,0) FROM accounts WHERE customer_id=? AND account_type='SB'",(cust[0],)).fetchall()
        if accs:
            for a in accs:
                mv=a[1]+a[2]
                st.markdown(f"""
                <div style="background:var(--bg-secondary);padding:0.8rem;border-radius:10px;margin:0.3rem 0;border-left:3px solid #3b82f6;">
                    <b>{a[0]}</b> | Principal: ₹{a[1]:,.2f} | Interest: ₹{a[2]:,.2f} | <b>Maturity: ₹{mv:,.2f}</b>
                </div>""",unsafe_allow_html=True)
        else: st.info("No accounts")
        st.markdown('</div>',unsafe_allow_html=True)
    else: st.warning("No profile")
    c.close()

if __name__ == "__main__":
    main()
