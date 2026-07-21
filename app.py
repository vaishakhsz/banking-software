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
                conn.execute("UPDATE accounts SET balance=?, total_interest_earned=?, last_interest_calculation=? WHERE id=?", (new_balance, new_total_interest, calc_to_date, account_id))
                txn_id = generate_id('TXN')
                voucher_num = generate_voucher_number('RECEIPT')
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

# ==================== PREMIUM CSS DESIGN ====================

def load_premium_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    /* Main Background */
    .main { background: linear-gradient(135deg, #f0f4ff 0%, #e8eeff 50%, #f5f3ff 100%); }
    .main .block-container { padding: 1rem 1.5rem; max-width: 1400px; }
    
    /* Glass Morphism Header */
    .main-header {
        font-size: 2.6rem;
        font-weight: 800;
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 30%, #ec4899 60%, #f43f5e 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.3rem;
        padding: 0.5rem;
        letter-spacing: -1px;
        animation: gradientShift 3s ease infinite;
        background-size: 200% 200%;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .sub-header {
        text-align: center;
        color: #6b7280;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
        padding-bottom: 0.8rem;
        border-bottom: 2px solid rgba(139, 92, 246, 0.2);
        font-weight: 500;
        letter-spacing: 0.5px;
    }
    
    /* Premium Glass Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.8);
        box-shadow: 0 8px 32px rgba(99, 102, 241, 0.08);
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(99, 102, 241, 0.15);
        border-color: rgba(139, 92, 246, 0.3);
    }
    
    /* Premium Metric Cards */
    .premium-metric {
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 1.5rem 1.2rem;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.9);
        box-shadow: 0 4px 20px rgba(0,0,0,0.04);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .premium-metric::after {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 100%;
        height: 100%;
        background: radial-gradient(circle, rgba(139,92,246,0.1) 0%, transparent 70%);
        border-radius: 50%;
    }
    
    .premium-metric:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px rgba(139, 92, 246, 0.2);
        border-color: rgba(139, 92, 246, 0.4);
    }
    
    .premium-metric .icon-large {
        font-size: 2.8rem;
        display: block;
        margin-bottom: 0.5rem;
        position: relative;
        z-index: 1;
    }
    
    .premium-metric h3 {
        font-size: 2rem;
        font-weight: 800;
        margin: 0.3rem 0;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        position: relative;
        z-index: 1;
    }
    
    .premium-metric p {
        margin: 0;
        font-size: 0.8rem;
        color: #6b7280;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        position: relative;
        z-index: 1;
    }
    
    /* Color Variants */
    .premium-metric.purple::after { background: radial-gradient(circle, rgba(139,92,246,0.15) 0%, transparent 70%); }
    .premium-metric.pink::after { background: radial-gradient(circle, rgba(236,72,153,0.15) 0%, transparent 70%); }
    .premium-metric.blue::after { background: radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%); }
    .premium-metric.amber::after { background: radial-gradient(circle, rgba(245,158,11,0.15) 0%, transparent 70%); }
    
    .premium-metric.pink h3 { background: linear-gradient(135deg, #ec4899, #f43f5e); -webkit-background-clip: text; }
    .premium-metric.blue h3 { background: linear-gradient(135deg, #3b82f6, #06b6d4); -webkit-background-clip: text; }
    .premium-metric.amber h3 { background: linear-gradient(135deg, #f59e0b, #ef4444); -webkit-background-clip: text; }
    
    /* Section Cards */
    .section-glass {
        background: rgba(255, 255, 255, 0.75);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.8);
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.06);
        padding: 1.8rem;
        margin-bottom: 1.2rem;
    }
    
    .section-glass h3 {
        font-size: 1.2rem;
        font-weight: 700;
        color: #1e1b4b;
        margin-bottom: 1.2rem;
        padding-bottom: 0.8rem;
        border-bottom: 2px solid rgba(139, 92, 246, 0.2);
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Premium Buttons */
    .stButton > button {
        width: 100%;
        border-radius: 14px;
        font-weight: 700;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        border: none;
        padding: 0.75rem 1.5rem;
        font-size: 0.95rem;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button::after {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s;
    }
    
    .stButton > button:hover::after {
        left: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 30px rgba(99, 102, 241, 0.3);
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
        color: white;
        font-weight: 700;
    }
    
    /* Input Fields */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 12px !important;
        border: 2px solid rgba(139, 92, 246, 0.2) !important;
        padding: 0.7rem 1rem !important;
        font-size: 0.95rem !important;
        transition: all 0.3s ease !important;
        background: rgba(255,255,255,0.9) !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #8b5cf6 !important;
        box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.1) !important;
    }
    
    /* Premium Tables */
    .stDataFrame {
        border-radius: 16px !important;
        overflow: hidden !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.04) !important;
    }
    
    .stDataFrame thead th {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        color: white !important;
        font-weight: 700 !important;
        padding: 0.9rem 1rem !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .stDataFrame tbody tr:nth-child(even) {
        background: rgba(139, 92, 246, 0.03) !important;
    }
    
    .stDataFrame tbody tr:hover {
        background: rgba(139, 92, 246, 0.08) !important;
    }
    
    /* Premium Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background: rgba(255,255,255,0.5);
        backdrop-filter: blur(10px);
        padding: 8px;
        border-radius: 16px;
        border: 1px solid rgba(139,92,246,0.1);
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 12px;
        padding: 0.6rem 1.4rem;
        font-weight: 600;
        font-size: 0.9rem;
        transition: all 0.3s ease;
        color: #6b7280;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(139,92,246,0.1);
        color: #6366f1;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(99,102,241,0.3);
    }
    
    /* Premium Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1b4b 0%, #312e81 50%, #3730a3 100%) !important;
        border-right: none !important;
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    [data-testid="stSidebar"] .stButton > button {
        background: rgba(255,255,255,0.1) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.2) !important;
        color: white !important;
        text-align: left;
        padding: 0.7rem 1rem;
        font-weight: 500;
        border-radius: 12px;
        transition: all 0.3s ease;
    }
    
    [data-testid="stSidebar"] .stButton > button:hover {
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
        border-color: transparent !important;
        transform: translateX(6px);
        box-shadow: 0 4px 20px rgba(99,102,241,0.4);
    }
    
    /* Premium Expanders */
    .streamlit-expanderHeader {
        border-radius: 14px !important;
        font-weight: 700 !important;
        padding: 0.9rem 1.2rem !important;
        background: rgba(255,255,255,0.8) !important;
        backdrop-filter: blur(10px);
        border: 2px solid rgba(139,92,246,0.2) !important;
        transition: all 0.3s ease !important;
        color: #1e1b4b !important;
    }
    
    .streamlit-expanderHeader:hover {
        border-color: #8b5cf6 !important;
        background: rgba(139,92,246,0.05) !important;
        box-shadow: 0 4px 20px rgba(139,92,246,0.15);
    }
    
    /* Alerts */
    .alert-premium {
        padding: 1.2rem 1.5rem;
        border-radius: 16px;
        margin: 1rem 0;
        font-weight: 600;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.3);
    }
    
    .alert-success {
        background: rgba(16, 185, 129, 0.15);
        border-left: 5px solid #10b981;
        color: #065f46;
    }
    
    .alert-info {
        background: rgba(99, 102, 241, 0.1);
        border-left: 5px solid #6366f1;
        color: #3730a3;
    }
    
    .alert-warning {
        background: rgba(245, 158, 11, 0.15);
        border-left: 5px solid #f59e0b;
        color: #92400e;
    }
    
    .alert-danger {
        background: rgba(239, 68, 68, 0.1);
        border-left: 5px solid #ef4444;
        color: #991b1b;
    }
    
    /* Balance Sheet Display */
    .bs-display {
        background: rgba(255,255,255,0.9);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 2rem;
        border: 1px solid rgba(139,92,246,0.2);
        box-shadow: 0 8px 32px rgba(99,102,241,0.08);
        margin-bottom: 1rem;
    }
    
    .bs-display h3 {
        font-size: 1.3rem;
        font-weight: 800;
        color: #6366f1;
        margin-bottom: 1.2rem;
        padding-bottom: 0.8rem;
        border-bottom: 3px solid rgba(139,92,246,0.3);
    }
    
    .bs-row {
        display: flex;
        justify-content: space-between;
        padding: 0.5rem 0;
        border-bottom: 1px solid rgba(139,92,246,0.1);
        color: #374151;
        font-weight: 500;
    }
    
    .bs-total {
        display: flex;
        justify-content: space-between;
        padding: 0.8rem 0;
        margin-top: 0.5rem;
        border-top: 2px solid rgba(139,92,246,0.3);
        font-weight: 800;
        font-size: 1.1rem;
        color: #1e1b4b;
    }
    
    /* Login Glass */
    .login-glass {
        max-width: 440px;
        margin: 2rem auto;
        padding: 2.5rem;
        background: rgba(255,255,255,0.8);
        backdrop-filter: blur(30px);
        border-radius: 24px;
        box-shadow: 0 20px 60px rgba(99,102,241,0.15);
        border: 1px solid rgba(255,255,255,0.8);
    }
    
    /* Date Info */
    .date-glass {
        background: rgba(139,92,246,0.08);
        backdrop-filter: blur(10px);
        padding: 1.5rem;
        border-radius: 16px;
        border: 1px solid rgba(139,92,246,0.2);
        margin: 1rem 0;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-weight: 800 !important;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .main-header { font-size: 1.8rem; }
        .premium-metric h3 { font-size: 1.5rem; }
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: rgba(139,92,246,0.05); border-radius: 10px; }
    ::-webkit-scrollbar-thumb { background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 10px; }
    
    /* Animations */
    @keyframes slideUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .animate-up {
        animation: slideUp 0.6s ease-out;
    }
    </style>
    """, unsafe_allow_html=True)

# ==================== STREAMLIT UI ====================

def main():
    st.set_page_config(page_title="🏦 NovaBank Enterprise", page_icon="✨", layout="wide", initial_sidebar_state="expanded")
    init_database()
    create_default_admin()
    init_session_state()
    load_premium_css()
    
    if st.session_state.user is None:
        show_login_page()
    else:
        show_main_app()

def show_login_page():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 2rem 0 1rem 0;">
            <h1 style="font-size: 5rem; margin: 0;">✨</h1>
            <h1 class="main-header">NovaBank Enterprise</h1>
            <p style="text-align: center; color: #6b7280; font-size: 0.95rem; font-weight: 500;">Next-Gen Banking Platform</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="login-glass">', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align: center; color: #1e1b4b; font-weight: 800;">🔐 Welcome Back</h2>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; color: #6b7280; margin-bottom: 1.5rem; font-size: 0.9rem;">Sign in to continue</p>', unsafe_allow_html=True)
        
        username = st.text_input("👤 Username", placeholder="Enter your username", key="login_username")
        password = st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="login_password")
        
        if st.button("✨ Sign In", use_container_width=True, type="primary", key="btn_signin"):
            user = login_user(username, password)
            if user:
                st.session_state.user = {'id': user[0], 'username': user[1], 'role': user[3]}
                st.success("✅ Welcome back!")
                st.rerun()
            else:
                st.error("❌ Invalid credentials")
        
        st.divider()
        st.markdown("""
        <div style="text-align: center; color: #6b7280; font-size: 0.8rem;">
            <p style="margin:0;">Demo Credentials</p>
            <p style="margin:0; font-weight:700; color:#6366f1;">admin / admin123</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def show_main_app():
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1.5rem 0 1rem 0;">
            <h1 style="font-size: 2.5rem; margin: 0;">✨</h1>
            <h3 style="margin: 0.3rem 0; font-weight: 800; letter-spacing: 1px;">NovaBank</h3>
            <p style="font-size: 0.7rem; margin: 0; opacity: 0.7; letter-spacing: 2px;">ENTERPRISE</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        st.markdown(f"""
        <div style="text-align: center; padding: 0.3rem 0;">
            <div style="display: inline-block; padding: 0.4rem 1.2rem; background: rgba(255,255,255,0.15); border-radius: 25px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);">
                <span style="font-weight: 600;">👤 {st.session_state.user['username']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        role_badge = {
            'admin': '<span style="background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 4px 14px; border-radius: 20px; font-weight: 700; font-size: 0.75rem; letter-spacing: 1px;">ADMIN</span>',
            'staff': '<span style="background: linear-gradient(135deg, #f59e0b, #d97706); color: white; padding: 4px 14px; border-radius: 20px; font-weight: 700; font-size: 0.75rem; letter-spacing: 1px;">STAFF</span>',
            'customer': '<span style="background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 4px 14px; border-radius: 20px; font-weight: 700; font-size: 0.75rem; letter-spacing: 1px;">CUSTOMER</span>'
        }
        st.markdown(f'<div style="text-align: center; margin: 0.8rem 0;">{role_badge.get(st.session_state.user["role"], "USER")}</div>', unsafe_allow_html=True)
        
        st.divider()
        
        if st.session_state.user['role'] in ['admin', 'staff']:
            menu_options = {
                'dashboard': '📊 Dashboard',
                'customer_management': '👥 Customers',
                'kyc_verification': '🔍 KYC Verify',
                'create_sb_account': '🏦 New SB Account',
                'sb_accounts': '💰 SB Accounts',
                'fixed_deposits': '💎 Fixed Deposits',
                'recurring_deposits': '🔄 Recurring Deposits',
                'transactions': '💳 Transactions',
                'journal_vouchers': '📝 Journal Vouchers',
                'income_expenses': '📈 Income/Expenses',
                'interest_calculation': '📊 Interest Calc',
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
            if st.sidebar.button(label, key=f"menu_{key}", use_container_width=True):
                st.session_state.page = key
                st.rerun()
        
        st.divider()
        if st.sidebar.button("🚪 Sign Out", use_container_width=True, key="btn_logout"):
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
    st.markdown('<h1 class="main-header">✨ Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Real-time banking intelligence</p>', unsafe_allow_html=True)
    
    conn = get_db()
    
    col1, col2, col3, col4 = st.columns(4)
    
    customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    active_sb = conn.execute("SELECT COUNT(*) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    total_bal = conn.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    total_int = conn.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    pending_kyc = conn.execute("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'").fetchone()[0]
    
    with col1:
        st.markdown(f'''
        <div class="premium-metric purple">
            <span class="icon-large">👥</span>
            <h3>{customers}</h3>
            <p>Total Customers</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        st.markdown(f'''
        <div class="premium-metric pink">
            <span class="icon-large">💎</span>
            <h3>{active_sb}</h3>
            <p>Active SB Accounts</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col3:
        st.markdown(f'''
        <div class="premium-metric blue">
            <span class="icon-large">🏦</span>
            <h3>₹{total_bal+total_int:,.0f}</h3>
            <p>Total SB Maturity</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col4:
        st.markdown(f'''
        <div class="premium-metric amber">
            <span class="icon-large">🔍</span>
            <h3>{pending_kyc}</h3>
            <p>Pending KYC</p>
        </div>
        ''', unsafe_allow_html=True)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h3>📋 Recent Transactions</h3>', unsafe_allow_html=True)
        transactions = conn.execute("""
            SELECT t.transaction_id, c.first_name||' '||c.last_name, t.transaction_type, t.amount, t.created_at
            FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id
            ORDER BY t.created_at DESC LIMIT 8
        """).fetchall()
        if transactions:
            df = pd.DataFrame(transactions, columns=['Txn ID','Customer','Type','Amount','Date'])
            st.dataframe(df.style.format({'Amount':'₹{:,.2f}'}), use_container_width=True, height=300)
        else:
            st.info("No transactions yet")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h3>📊 Account Distribution</h3>', unsafe_allow_html=True)
        acc_types = conn.execute("SELECT account_type, COUNT(*) FROM accounts WHERE status='ACTIVE' GROUP BY account_type").fetchall()
        if acc_types:
            df_acc = pd.DataFrame(acc_types, columns=['Type','Count'])
            colors = ['#6366f1','#ec4899','#f59e0b']
            fig = px.pie(df_acc, values='Count', names='Type', hole=0.5, color_discrete_sequence=colors)
            fig.update_layout(height=300, margin=dict(t=20,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            fig.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='white',width=3)))
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    conn.close()

def show_customer_management():
    st.markdown('<h1 class="main-header">👥 Customer Management</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Register and manage customer profiles</p>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📝 Register", "👥 View All"])
    
    with tab1:
        st.markdown('<div class="section-glass">', unsafe_allow_html=True)
        st.markdown('<h3>📝 New Customer Registration</h3>', unsafe_allow_html=True)
        with st.form("cust_reg"):
            col1, col2 = st.columns(2)
            with col1:
                fn = st.text_input("First Name *", placeholder="Enter first name")
                ln = st.text_input("Last Name *", placeholder="Enter last name")
                dob = st.date_input("Date of Birth *", min_value=date(1900,1,1), max_value=date.today())
                email = st.text_input("Email *", placeholder="email@example.com")
                phone = st.text_input("Phone *", placeholder="10-digit number")
            with col2:
                pan = st.text_input("PAN Number *", placeholder="ABCDE1234F")
                aadhar = st.text_input("Aadhar Number *", placeholder="12-digit Aadhar")
                addr = st.text_area("Address", placeholder="Full address")
                city = st.text_input("City")
                state = st.text_input("State")
                pin = st.text_input("PIN Code")
            
            st.markdown("#### 📎 KYC Documents")
            c1, c2 = st.columns(2)
            with c1: pan_doc = st.file_uploader("PAN Card *", type=['jpg','jpeg','png','pdf'], key="pan_up")
            with c2: aadhar_doc = st.file_uploader("Aadhar Card *", type=['jpg','jpeg','png','pdf'], key="aad_up")
            
            if st.form_submit_button("✨ Register Customer", use_container_width=True):
                if not all([fn, ln, email, phone, pan, aadhar]):
                    st.error("❌ Fill all required fields")
                elif not pan_doc or not aadhar_doc:
                    st.error("❌ Upload PAN and Aadhar")
                else:
                    try:
                        conn = get_db()
                        cid = generate_id('CUST')
                        conn.execute("INSERT INTO customers (customer_id, first_name, last_name, date_of_birth, email, phone, address, city, state, pincode, pan_number, aadhar_number, pan_document, aadhar_document) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                   (cid, fn, ln, dob, email, phone, addr, city, state, pin, pan, aadhar, pan_doc.read(), aadhar_doc.read()))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Registered! ID: **{cid}**")
                        st.balloons()
                    except Exception as e:
                        st.error(f"❌ {str(e)}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="section-glass">', unsafe_allow_html=True)
        st.markdown('<h3>👥 Customer Directory</h3>', unsafe_allow_html=True)
        conn = get_db()
        customers = conn.execute("SELECT customer_id, first_name, last_name, email, phone, city, kyc_status FROM customers ORDER BY customer_id DESC").fetchall()
        if customers:
            df = pd.DataFrame(customers, columns=['ID','First','Last','Email','Phone','City','KYC'])
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button("📥 Export CSV", df.to_csv(index=False), "customers.csv", "text/csv", key="dl_cust")
        else:
            st.info("No customers yet")
        conn.close()
        st.markdown('</div>', unsafe_allow_html=True)

def show_kyc_verification():
    st.markdown('<h1 class="main-header">🔍 KYC Verification</h1>', unsafe_allow_html=True)
    if st.session_state.user['role'] not in ['admin','staff']: st.error("⛔ Unauthorized"); return
    conn = get_db()
    pending = conn.execute("SELECT * FROM customers WHERE kyc_status='PENDING' ORDER BY created_at").fetchall()
    if not pending:
        st.markdown('<div class="alert-premium alert-success">✅ All KYC verified!</div>', unsafe_allow_html=True)
    else:
        st.info(f"📋 {len(pending)} pending")
        for cust in pending:
            with st.expander(f"📄 {cust[3]} {cust[4]} - {cust[2]}", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Name:** {cust[3]} {cust[4]}")
                    st.write(f"**DOB:** {cust[5]} | **Email:** {cust[7]}")
                    st.write(f"**Phone:** {cust[8]}")
                    st.write(f"**PAN:** {cust[12]} | **Aadhar:** {cust[13]}")
                with c2:
                    if cust[16]:
                        try: st.image(cust[16], caption="PAN", width=200)
                        except: st.info("PAN uploaded")
                    if cust[17]:
                        try: st.image(cust[17], caption="Aadhar", width=200)
                        except: st.info("Aadhar uploaded")
                st.divider()
                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button(f"✅ Approve", key=f"app_{cust[0]}", use_container_width=True, type="primary"):
                        conn.execute("UPDATE customers SET kyc_status='VERIFIED', kyc_verified_by=?, kyc_verified_at=CURRENT_TIMESTAMP WHERE id=?", (st.session_state.user['id'], cust[0]))
                        if not conn.execute("SELECT id FROM accounts WHERE customer_id=? AND account_type='SB' AND status='ACTIVE'",(cust[0],)).fetchone():
                            conn.execute("INSERT INTO accounts (account_number, customer_id, account_type, balance, interest_rate, last_interest_calculation, total_interest_earned) VALUES (?,?,'SB',0.00,3.50,DATE('now'),0.00)", (generate_account_number('SB'), cust[0]))
                        conn.commit()
                        st.success("✅ Approved!")
                        st.rerun()
                with bc2:
                    if st.button(f"❌ Reject", key=f"rej_{cust[0]}", use_container_width=True):
                        conn.execute("UPDATE customers SET kyc_status='REJECTED' WHERE id=?",(cust[0],))
                        conn.commit()
                        st.rerun()
    conn.close()

def show_create_sb_account():
    st.markdown('<h1 class="main-header">🏦 Create SB Account</h1>', unsafe_allow_html=True)
    if st.session_state.user['role'] not in ['admin','staff']: st.error("⛔ Unauthorized"); return
    conn = get_db()
    customers = conn.execute("""SELECT c.id, c.customer_id, c.first_name||' '||c.last_name, c.email FROM customers c WHERE c.kyc_status='VERIFIED' AND NOT EXISTS (SELECT 1 FROM accounts a WHERE a.customer_id=c.id AND a.account_type='SB' AND a.status='ACTIVE') ORDER BY c.created_at DESC""").fetchall()
    if not customers:
        st.markdown('<div class="alert-premium alert-success">✅ All verified customers have SB accounts!</div>', unsafe_allow_html=True)
        return
    st.markdown('<div class="section-glass">', unsafe_allow_html=True)
    st.markdown('<h3>🏦 Open New SB Account</h3>', unsafe_allow_html=True)
    selected = st.selectbox("Select Customer", [f"{c[1]} - {c[2]}" for c in customers])
    if selected:
        idx = [f"{c[1]} - {c[2]}" for c in customers].index(selected)
        cust = customers[idx]
        st.markdown(f'<div class="alert-premium alert-info"><b>Selected:</b> {cust[2]} ({cust[1]})</div>', unsafe_allow_html=True)
        with st.form("create_sb"):
            c1, c2 = st.columns(2)
            with c1: rate = st.number_input("Interest Rate (%)", 0.0, 10.0, 3.50, 0.25)
            with c2: bal = st.number_input("Opening Balance (₹)", 0.0, step=100.0, value=0.0)
            if st.form_submit_button("✨ Create Account", use_container_width=True):
                an = generate_account_number('SB')
                conn.execute("INSERT INTO accounts (account_number, customer_id, account_type, balance, interest_rate, last_interest_calculation, total_interest_earned) VALUES (?,?,'SB',?,?,DATE('now'),0.00)", (an, cust[0], bal, rate))
                conn.commit()
                st.success(f"✅ Created! **{an}**")
                st.balloons()
    st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

def show_sb_accounts():
    st.markdown('<h1 class="main-header">💰 SB Accounts</h1>', unsafe_allow_html=True)
    conn = get_db()
    tab1, tab2, tab3, tab4 = st.tabs(["📋 List", "💸 Transact", "📜 Statement", "📈 Maturity"])
    
    with tab1:
        st.markdown('<div class="section-glass">', unsafe_allow_html=True)
        if st.session_state.user['role']=='customer':
            accounts = conn.execute("SELECT a.account_number, c.first_name||' '||c.last_name, a.balance, a.interest_rate, a.status, COALESCE(a.total_interest_earned,0), a.created_at FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND c.user_id=? ORDER BY a.created_at DESC",(st.session_state.user['id'],)).fetchall()
        else:
            accounts = conn.execute("SELECT a.account_number, c.first_name||' '||c.last_name, a.balance, a.interest_rate, a.status, COALESCE(a.total_interest_earned,0), a.created_at FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND c.kyc_status='VERIFIED' ORDER BY a.created_at DESC").fetchall()
        if accounts:
            data = [{'Account':a[0],'Customer':a[1],'Principal':a[2],'Rate':f"{a[3]:.2f}%",'Status':a[4],'Interest':a[5],'Maturity':a[2]+a[5]} for a in accounts]
            df = pd.DataFrame(data)
            st.dataframe(df.style.format({'Principal':'₹{:,.2f}','Interest':'₹{:,.2f}','Maturity':'₹{:,.2f}'}), use_container_width=True, height=350)
            c1,c2,c3=st.columns(3)
            with c1: st.metric("Total Principal", f"₹{sum(d['Principal'] for d in data):,.2f}")
            with c2: st.metric("Total Interest", f"₹{sum(d['Interest'] for d in data):,.2f}")
            with c3: st.metric("Total Maturity", f"₹{sum(d['Maturity'] for d in data):,.2f}")
        else:
            st.info("No SB accounts")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="section-glass">', unsafe_allow_html=True)
        if st.session_state.user['role']=='customer':
            accounts = conn.execute("SELECT a.id, a.account_number, c.first_name||' '||c.last_name, a.balance, COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND c.user_id=?",(st.session_state.user['id'],)).fetchall()
        else:
            accounts = conn.execute("SELECT a.id, a.account_number, c.first_name||' '||c.last_name, a.balance, COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        if accounts:
            sel = st.selectbox("Select Account", [f"{a[1]} - {a[2]} (Maturity: ₹{a[3]+a[4]:,.2f})" for a in accounts])
            if sel:
                idx = [f"{a[1]} - {a[2]} (Maturity: ₹{a[3]+a[4]:,.2f})" for a in accounts].index(sel)
                acc = accounts[idx]
                tt = st.radio("Type", ["💰 Deposit","💸 Withdraw"], horizontal=True)
                with st.form("txn_f"):
                    amt = st.number_input("Amount (₹)", min_value=0.01, step=100.0)
                    desc = st.text_input("Description")
                    mode = st.selectbox("Mode", ["CASH","TRANSFER","CHEQUE"])
                    if st.form_submit_button("✨ Process", use_container_width=True):
                        atype = "DEPOSIT" if "Deposit" in tt else "WITHDRAWAL"
                        if atype=="WITHDRAWAL" and amt>acc[3]: st.error("❌ Insufficient!")
                        else:
                            nb = acc[3]+amt if atype=="DEPOSIT" else acc[3]-amt
                            tdb = "CREDIT" if atype=="DEPOSIT" else "DEBIT"
                            vt = "RECEIPT" if atype=="DEPOSIT" else "PAYMENT"
                            conn.execute("INSERT INTO transactions (transaction_id, account_id, transaction_type, amount, balance_after, description, reference_type, voucher_type, voucher_number, created_by) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                       (generate_id('TXN'), acc[0], tdb, amt, nb, desc, mode, vt, generate_voucher_number(vt), st.session_state.user['id']))
                            conn.execute("UPDATE accounts SET balance=? WHERE id=?",(nb,acc[0]))
                            conn.commit()
                            st.success(f"✅ Done! New Maturity: ₹{nb+acc[4]:,.2f}")
                            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        st.markdown('<div class="section-glass">', unsafe_allow_html=True)
        if st.session_state.user['role']=='customer':
            accounts = conn.execute("SELECT a.id, a.account_number, c.first_name||' '||c.last_name FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND c.user_id=?",(st.session_state.user['id'],)).fetchall()
        else:
            accounts = conn.execute("SELECT a.id, a.account_number, c.first_name||' '||c.last_name FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        if accounts:
            sel = st.selectbox("Select Account", [f"{a[1]} - {a[2]}" for a in accounts], key="st_sel")
            if sel:
                aid = [a[0] for a in accounts if f"{a[1]} - {a[2]}"==sel][0]
                c1,c2=st.columns(2)
                with c1: fd = st.date_input("From", date.today()-timedelta(days=30), key="st_f")
                with c2: td = st.date_input("To", date.today(), key="st_t")
                txns = conn.execute("SELECT transaction_id, created_at, transaction_type, amount, balance_after, description, voucher_number FROM transactions WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ? ORDER BY created_at DESC",(aid,fd,td)).fetchall()
                if txns:
                    df = pd.DataFrame(txns, columns=['Txn ID','Date','Type','Amount','Balance','Description','Voucher'])
                    st.dataframe(df.style.format({'Amount':'₹{:,.2f}','Balance':'₹{:,.2f}'}), use_container_width=True, height=350)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab4:
        st.markdown('<div class="section-glass">', unsafe_allow_html=True)
        if st.session_state.user['role']=='customer':
            accounts = conn.execute("SELECT a.account_number, c.first_name||' '||c.last_name, a.balance, a.interest_rate, COALESCE(a.total_interest_earned,0), a.created_at FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND c.user_id=?",(st.session_state.user['id'],)).fetchall()
        else:
            accounts = conn.execute("SELECT a.account_number, c.first_name||' '||c.last_name, a.balance, a.interest_rate, COALESCE(a.total_interest_earned,0), a.created_at FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB'").fetchall()
        if accounts:
            data = [{'Account':a[0],'Customer':a[1],'Principal':a[2],'Rate':f"{a[3]:.2f}%",'Interest':a[4],'Maturity':a[2]+a[4]} for a in accounts]
            df = pd.DataFrame(data)
            st.dataframe(df.style.format({'Principal':'₹{:,.2f}','Interest':'₹{:,.2f}','Maturity':'₹{:,.2f}'}), use_container_width=True, height=300)
            c1,c2,c3=st.columns(3)
            with c1: st.metric("Total Principal", f"₹{sum(d['Principal'] for d in data):,.2f}")
            with c2: st.metric("Total Interest", f"₹{sum(d['Interest'] for d in data):,.2f}")
            with c3: st.metric("Total Maturity", f"₹{sum(d['Maturity'] for d in data):,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    conn.close()

def show_interest_calculation():
    st.markdown('<h1 class="main-header">📊 Interest Calculation</h1>', unsafe_allow_html=True)
    if st.session_state.user['role'] not in ['admin','staff']: st.error("⛔ Unauthorized"); return
    conn = get_db()
    tab1, tab2, tab3 = st.tabs(["🧮 Calculate", "📊 History", "📈 JV Impact"])
    
    with tab1:
        st.markdown('<div class="section-glass">', unsafe_allow_html=True)
        st.markdown('<div class="date-glass">', unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1: cfd = st.date_input("From", date.today().replace(day=1), key="if")
        with c2: ctd = st.date_input("To", date.today(), key="it")
        if cfd>ctd: st.error("❌ Invalid range")
        else: st.info(f"📊 {cfd.strftime('%d-%b-%Y')} → {ctd.strftime('%d-%b-%Y')} ({(ctd-cfd).days+1} days)")
        st.markdown('</div>', unsafe_allow_html=True)
        
        accounts = conn.execute("SELECT a.id, a.account_number, c.first_name||' '||c.last_name, a.balance, a.interest_rate, COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        if accounts:
            bc1,bc2=st.columns(2)
            with bc1:
                if st.button("✨ Calculate & Post", use_container_width=True, type="primary", key="btn_cp"):
                    if cfd>ctd: st.error("❌ Invalid!")
                    else:
                        status, result = calculate_and_post_sb_interest(st.session_state.user['id'], cfd, ctd)
                        if status=="SUCCESS" and len(result)>0:
                            st.success(f"✅ Posted! Total: ₹{sum(r['interest'] for r in result):,.2f}")
                            st.balloons()
                        else: st.info(status if status!="SUCCESS" else "No interest")
            with bc2:
                if st.button("🔍 Preview", use_container_width=True, key="btn_pv"):
                    preview = []
                    for acc in accounts:
                        mb = get_minimum_balance(conn, acc[0], cfd, ctd)
                        if mb<=0: mb=acc[3]
                        days = (ctd-cfd).days+1
                        if days>0:
                            interest = calculate_sb_interest(mb, acc[4] if acc[4] else 3.5, days)
                            preview.append({'Account':acc[1],'Customer':acc[2],'Min Bal':mb,'Interest':interest,'New Maturity':acc[3]+acc[5]+interest})
                    if preview:
                        st.dataframe(pd.DataFrame(preview).style.format({'Min Bal':'₹{:,.2f}','Interest':'₹{:,.2f}','New Maturity':'₹{:,.2f}'}), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="section-glass">', unsafe_allow_html=True)
        history = conn.execute("SELECT ic.calculation_date, a.account_number, c.first_name||' '||c.last_name, ic.principal_amount, ic.interest_rate, ic.interest_earned, ic.days_calculated FROM interest_calculations ic JOIN accounts a ON ic.account_id=a.id JOIN customers c ON a.customer_id=c.id ORDER BY ic.calculation_date DESC LIMIT 50").fetchall()
        if history:
            df = pd.DataFrame(history, columns=['Date','Account','Customer','Principal','Rate','Interest','Days'])
            st.dataframe(df.style.format({'Principal':'₹{:,.2f}','Interest':'₹{:,.2f}'}), use_container_width=True, height=350)
            st.metric("Total Interest Paid", f"₹{sum(h[5] for h in history):,.2f}")
        else: st.info("No history")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        st.markdown('<div class="section-glass">', unsafe_allow_html=True)
        jvs = conn.execute("SELECT jv.voucher_number, jv.voucher_date, jv.description, jv.total_amount, je.account_head, je.debit_amount, je.credit_amount, je.description FROM journal_vouchers jv JOIN journal_entries je ON jv.id=je.voucher_id WHERE (je.account_head='Interest Paid on SB' OR je.account_head LIKE '%SB Account%') AND jv.status='POSTED' ORDER BY jv.voucher_date DESC LIMIT 50").fetchall()
        if jvs:
            jd = {}
            for j in jvs:
                vn=j[0]
                if vn not in jd: jd[vn]={'date':j[1],'desc':j[2],'amt':j[3],'entries':[]}
                jd[vn]['entries'].append({'head':j[4],'debit':j[5],'credit':j[6],'desc':j[7]})
            for vn,d in jd.items():
                with st.expander(f"📄 {vn} - {d['date']} - ₹{d['amt']:,.2f}"):
                    for e in d['entries']:
                        bg = "#fee2e2" if e['debit']>0 else "#d1fae5"
                        st.markdown(f'<div style="background:{bg};color:black;padding:0.8rem;border-radius:10px;margin:0.3rem 0;border-left:4px solid #6366f1;"><b>{e["head"]}</b><br>Debit: ₹{e["debit"]:,.2f} | Credit: ₹{e["credit"]:,.2f}<br><small>{e["desc"]}</small></div>', unsafe_allow_html=True)
            tj = sum(d['amt'] for d in jd.values())
            c1,c2=st.columns(2)
            with c1: st.metric("P&L Expense", f"₹{tj:,.2f}")
            with c2: st.metric("B/S Liability", f"₹{tj:,.2f}")
            st.success(f"✅ Trial Balance impact: ₹{tj:,.2f} both sides")
        else: st.info("No JVs found")
        st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

def show_trial_balance():
    st.markdown('<h1 class="main-header">⚖️ Trial Balance</h1>', unsafe_allow_html=True)
    if st.session_state.user['role'] not in ['admin','staff']: st.error("⛔ Unauthorized"); return
    conn = get_db()
    st.markdown('<div class="section-glass">', unsafe_allow_html=True)
    if st.button("✨ Generate Trial Balance", use_container_width=True, type="primary", key="btn_tb"):
        td = []
        cash = conn.execute("SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END),0) FROM transactions WHERE reference_type='CASH'").fetchone()[0]
        if abs(cash)>0: td.append({'account_head':'Cash in Hand','category':'Asset','debit':max(cash,0),'credit':max(-cash,0),'jv_ref':'Cash'})
        
        sb = conn.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb>0: td.append({'account_head':'SB Deposits (Principal)','category':'Liability','debit':0,'credit':sb,'jv_ref':'SB balances'})
        
        jvl = conn.execute("SELECT je.account_head, COALESCE(SUM(je.credit_amount),0), COALESCE(SUM(je.debit_amount),0), GROUP_CONCAT(DISTINCT jv.voucher_number) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE jv.status='POSTED' AND (je.account_head LIKE '%SB Account%' OR je.account_head LIKE '%Payable%' OR je.account_head LIKE '%Deposit%' OR je.account_head LIKE '%Liability%') GROUP BY je.account_head").fetchall()
        for e in jvl:
            h,cr,dr,jn = e[0],e[1],e[2],e[3] or ''
            jl = jn.split(',') if jn else []
            jr = ', '.join(jl[:3])+('...' if len(jl)>3 else '') if jl else 'JV'
            if cr>dr: td.append({'account_head':h,'category':'Liability','debit':dr,'credit':cr,'jv_ref':f'JV: {jr}'})
        
        fd = conn.execute("SELECT COALESCE(SUM(principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        if fd>0: td.append({'account_head':'Fixed Deposits','category':'Liability','debit':0,'credit':fd,'jv_ref':'FD'})
        rd = conn.execute("SELECT COALESCE(SUM(monthly_amount*installments_paid),0) FROM recurring_deposits WHERE status='ACTIVE'").fetchone()[0]
        if rd>0: td.append({'account_head':'Recurring Deposits','category':'Liability','debit':0,'credit':rd,'jv_ref':'RD'})
        
        for it in ['Interest Earned','Fees & Charges','Commission Income','Other Income']:
            amt = conn.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type=?",(it,)).fetchone()[0]
            if amt>0: td.append({'account_head':it,'category':'Income','debit':0,'credit':amt,'jv_ref':'Income'})
        
        jve = conn.execute("SELECT je.account_head, COALESCE(SUM(je.debit_amount),0), COALESCE(SUM(je.credit_amount),0), GROUP_CONCAT(DISTINCT jv.voucher_number) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE jv.status='POSTED' AND je.account_head NOT LIKE '%SB Account%' GROUP BY je.account_head").fetchall()
        for e in jve:
            h,dr,cr,jn = e[0],e[1],e[2],e[3] or ''
            jl = jn.split(',') if jn else []
            jr = ', '.join(jl[:3])+('...' if len(jl)>3 else '') if jl else 'JV'
            if dr>0: td.append({'account_head':h,'category':'Expense','debit':dr,'credit':0,'jv_ref':f'JV: {jr}'})
            if cr>0: td.append({'account_head':h,'category':'Income','debit':0,'credit':cr,'jv_ref':f'JV: {jr}'})
        
        for et in ['Salary & Wages','Rent & Utilities','Operating Expenses','Administrative Expenses','Other Expenses']:
            amt = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type=?",(et,)).fetchone()[0]
            if amt>0: td.append({'account_head':et,'category':'Expense','debit':amt,'credit':0,'jv_ref':'Expense'})
        
        tdr = sum(i['debit'] for i in td)
        tcr = sum(i['credit'] for i in td)
        diff = tcr-tdr
        if abs(diff)>0.01: td.append({'account_head':'Capital/Reserves','category':'Capital','debit':max(-diff,0),'credit':max(diff,0),'jv_ref':'Balance'})
        
        if td:
            df = pd.DataFrame(td)
            c1,c2,c3,c4=st.columns(4)
            with c1: st.metric("Assets", f"₹{sum(i['debit'] for i in td if i['category']=='Asset'):,.2f}")
            with c2: st.metric("Liabilities", f"₹{sum(i['credit'] for i in td if i['category']=='Liability'):,.2f}")
            with c3: st.metric("Income", f"₹{sum(i['credit'] for i in td if i['category']=='Income'):,.2f}")
            with c4: st.metric("Expenses", f"₹{sum(i['debit'] for i in td if i['category']=='Expense'):,.2f}")
            st.divider()
            for cat in ['Asset','Liability','Income','Expense','Capital']:
                cd = [i for i in td if i['category']==cat]
                if cd:
                    st.markdown(f"**{cat}s**")
                    disp = pd.DataFrame(cd)[['account_head','debit','credit','jv_ref']]
                    disp.columns=['Account Head','Debit (₹)','Credit (₹)','JV Ref']
                    st.dataframe(disp.style.format({'Debit (₹)':'₹{:,.2f}','Credit (₹)':'₹{:,.2f}'}), use_container_width=True, height=min(250,len(cd)*40))
            dft = df['debit'].sum(); cft = df['credit'].sum()
            st.divider()
            cc1,cc2,cc3=st.columns(3)
            with cc1: st.metric("Total Debit", f"₹{dft:,.2f}")
            with cc2: st.metric("Total Credit", f"₹{cft:,.2f}")
            with cc3:
                if abs(dft-cft)<0.01: st.success("✅ BALANCED!")
                else: st.error(f"❌ Diff: ₹{abs(dft-cft):,.2f}")
            
            sbi = sum(i['credit'] for i in td if 'SB Account' in i['account_head'])
            st.divider()
            st.markdown("### 💎 Interest Summary")
            st.write(f"• SB Principal: ₹{sb:,.2f} | • SB Interest: ₹{sbi:,.2f} | • Maturity: ₹{sb+sbi:,.2f}")
            jvc = len([i for i in td if i['jv_ref'].startswith('JV:')])
            st.success(f"✅ {jvc} JV entries reflected")
            
            st.download_button("📥 CSV", df.to_csv(index=False), "trial_balance.csv", "text/csv", key="dl_tb")
        else: st.info("No data")
    st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

def show_balance_sheet():
    st.markdown('<h1 class="main-header">📊 Balance Sheet</h1>', unsafe_allow_html=True)
    if st.session_state.user['role'] not in ['admin','staff']: st.error("⛔ Unauthorized"); return
    conn = get_db()
    st.markdown('<div class="section-glass">', unsafe_allow_html=True)
    if st.button("✨ Generate", use_container_width=True, type="primary", key="btn_bs"):
        cash = conn.execute("SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END),0) FROM transactions WHERE reference_type='CASH'").fetchone()[0]
        sb_bal = conn.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        sb_int = conn.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb_int==0: sb_int = conn.execute("SELECT COALESCE(SUM(credit_amount),0) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE je.account_head LIKE '%SB Account%' AND jv.status='POSTED'").fetchone()[0]
        fd = conn.execute("SELECT COALESCE(SUM(principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        rd = conn.execute("SELECT COALESCE(SUM(monthly_amount*installments_paid),0) FROM recurring_deposits WHERE status='ACTIVE'").fetchone()[0]
        fd_int = conn.execute("SELECT COALESCE(SUM(maturity_amount-principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        ta = cash+sb_bal+fd+rd
        tl = sb_int+fd_int+fd+rd+sb_bal
        cap = ta-tl
        
        c1,c2=st.columns(2)
        with c1:
            st.markdown(f"""
            <div class="bs-display"><h3>📊 ASSETS</h3>
            <div class="bs-row"><span>💰 Cash</span><span>₹{cash:,.2f}</span></div>
            <div class="bs-row"><span>🏦 SB Deposits</span><span>₹{sb_bal:,.2f}</span></div>
            <div class="bs-row"><span>💎 Fixed Deposits</span><span>₹{fd:,.2f}</span></div>
            <div class="bs-row"><span>🔄 Recurring Deposits</span><span>₹{rd:,.2f}</span></div>
            <div class="bs-total"><span>TOTAL ASSETS</span><span>₹{ta:,.2f}</span></div></div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="bs-display"><h3>📋 LIABILITIES</h3>
            <div class="bs-row"><span>📈 SB Interest Payable</span><span>₹{sb_int:,.2f}</span></div>
            <div class="bs-row"><span>📈 FD Interest Payable</span><span>₹{fd_int:,.2f}</span></div>
            <div class="bs-row"><span>🏦 SB Deposits</span><span>₹{sb_bal:,.2f}</span></div>
            <div class="bs-row"><span>💎 FD Deposits</span><span>₹{fd:,.2f}</span></div>
            <div class="bs-row"><span>🔄 RD Deposits</span><span>₹{rd:,.2f}</span></div>
            <div class="bs-total"><span>TOTAL LIABILITIES</span><span>₹{tl:,.2f}</span></div></div>""", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="bs-display"><h3>💰 CAPITAL</h3>
        <div class="bs-row" style="font-size:1.1rem;"><span><b>Capital / Net Worth</b></span><span><b>₹{cap:,.2f}</b></span></div></div>""", unsafe_allow_html=True)
        
        if abs(ta-(tl+cap))<0.01: st.success(f"✅ Balanced! A ₹{ta:,.2f} = L ₹{tl:,.2f} + C ₹{cap:,.2f}")
    st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

def show_profit_loss():
    st.markdown('<h1 class="main-header">💵 Profit & Loss</h1>', unsafe_allow_html=True)
    if st.session_state.user['role'] not in ['admin','staff']: st.error("⛔ Unauthorized"); return
    conn = get_db()
    st.markdown('<div class="section-glass">', unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1: fd = st.date_input("From", date.today().replace(month=1,day=1), key="plf")
    with c2: td = st.date_input("To", date.today(), key="plt")
    if st.button("✨ Generate P&L", use_container_width=True, type="primary", key="btn_pl"):
        inc = [('Interest Earned', conn.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Interest Earned' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),
               ('Fees & Charges', conn.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Fees & Charges' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),
               ('Commission', conn.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Commission Income' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),
               ('Other Income', conn.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Other Income' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0])]
        exp = [('Interest on SB', conn.execute("SELECT COALESCE(SUM(debit_amount),0) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE je.account_head='Interest Paid on SB' AND jv.status='POSTED' AND DATE(jv.voucher_date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),
               ('Salary', conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Salary & Wages' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),
               ('Rent', conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Rent & Utilities' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),
               ('Operating', conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Operating Expenses' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),
               ('Admin', conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Administrative Expenses' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),
               ('Other', conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Other Expenses' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0])]
        ti = sum(i[1] for i in inc); te = sum(e[1] for e in exp)
        pc1,pc2=st.columns(2)
        with pc1:
            st.markdown('<div class="bs-display"><h3>📈 INCOME</h3>', unsafe_allow_html=True)
            for item,amt in inc: st.write(f"• {item}: ₹{amt:,.2f}")
            st.markdown(f'<div class="bs-total">Total: ₹{ti:,.2f}</div></div>', unsafe_allow_html=True)
        with pc2:
            st.markdown('<div class="bs-display"><h3>📉 EXPENSES</h3>', unsafe_allow_html=True)
            for item,amt in exp:
                if amt>0: st.write(f"• {item}: ₹{amt:,.2f}")
            st.markdown(f'<div class="bs-total">Total: ₹{te:,.2f}</div></div>', unsafe_allow_html=True)
        net = ti-te
        if net>=0: st.success(f"## 🎉 Net Profit: ₹{net:,.2f}")
        else: st.error(f"## 📉 Net Loss: ₹{abs(net):,.2f}")
    st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

def show_income_expenses():
    st.markdown('<h1 class="main-header">📈 Income & Expenses</h1>', unsafe_allow_html=True)
    if st.session_state.user['role'] not in ['admin','staff']: st.error("⛔ Unauthorized"); return
    conn = get_db()
    t1,t2=st.tabs(["💰 Income","💸 Expense"])
    with t1:
        st.markdown('<div class="section-glass">', unsafe_allow_html=True)
        with st.form("inc_f"):
            c1,c2=st.columns(2)
            with c1: it=st.selectbox("Type",["Interest Earned","Fees & Charges","Commission Income","Other Income"]); amt=st.number_input("Amount (₹)",min_value=1.0,step=100.0)
            with c2: dt=st.date_input("Date",date.today(),key="id"); desc=st.text_area("Description")
            if st.form_submit_button("✨ Record Income",use_container_width=True):
                conn.execute("INSERT INTO income (income_id,income_type,amount,description,date,created_by) VALUES (?,?,?,?,?,?)",(generate_id('INC'),it,amt,desc,dt,st.session_state.user['id']))
                conn.commit(); st.success(f"✅ ₹{amt:,.2f}")
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="section-glass">',unsafe_allow_html=True)
        with st.form("exp_f"):
            c1,c2=st.columns(2)
            with c1: et=st.selectbox("Type",["Salary & Wages","Rent & Utilities","Operating Expenses","Administrative Expenses","Other Expenses"]); amt=st.number_input("Amount (₹)",min_value=1.0,step=100.0)
            with c2: dt=st.date_input("Date",date.today(),key="ed"); desc=st.text_area("Description")
            if st.form_submit_button("✨ Record Expense",use_container_width=True):
                conn.execute("INSERT INTO expenses (expense_id,expense_type,amount,description,date,created_by) VALUES (?,?,?,?,?,?)",(generate_id('EXP'),et,amt,desc,dt,st.session_state.user['id']))
                conn.commit(); st.success(f"✅ ₹{amt:,.2f}")
        st.markdown('</div>',unsafe_allow_html=True)
    conn.close()

def show_fixed_deposits():
    st.markdown('<h1 class="main-header">💎 Fixed Deposits</h1>', unsafe_allow_html=True)
    conn = get_db()
    t1,t2,t3=st.tabs(["📝 Open","📋 Active","🔔 Maturity"])
    with t1:
        st.markdown('<div class="section-glass">',unsafe_allow_html=True)
        customers = conn.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND c.kyc_status='VERIFIED' AND a.status='ACTIVE'").fetchall()
        if customers:
            sel = st.selectbox("Customer",[f"{c[1]} - {c[2]}" for c in customers])
            if sel:
                idx = [f"{c[1]} - {c[2]}" for c in customers].index(sel)
                cust = customers[idx]
                with st.form("fd_f"):
                    c1,c2=st.columns(2)
                    with c1: principal=st.number_input("Principal (₹)",min_value=1000.0,step=1000.0,value=10000.0); tenure=st.selectbox("Tenure",[3,6,12,24,36,60]); rate=st.number_input("Rate (%)",3.0,10.0,6.5,0.25)
                    with c2: sd=st.date_input("Start",date.today(),key="fds"); nom=st.text_input("Nominee")
                    md = sd+timedelta(days=tenure*30); ma = calculate_fd_maturity(principal,rate,tenure)
                    st.info(f"📅 Maturity: {md.strftime('%d-%m-%Y')} | 💰 Maturity: ₹{ma:,.2f}")
                    if st.form_submit_button("✨ Open FD",use_container_width=True):
                        fdn = generate_id('FD'); an = generate_account_number('FD')
                        conn.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate) VALUES (?,?,'FD',0.00,?)",(an,cust[0],rate))
                        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                        conn.execute("INSERT INTO fixed_deposits (fd_number,account_id,principal_amount,interest_rate,start_date,maturity_date,maturity_amount,tenure_months,nominee_name) VALUES (?,?,?,?,?,?,?,?,?)",(fdn,aid,principal,rate,sd,md,ma,tenure,nom))
                        conn.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,'FD Deposit','FD_DEPOSIT','RECEIPT',?,?)",(generate_id('TXN'),aid,principal,principal,generate_voucher_number('RECEIPT'),st.session_state.user['id']))
                        conn.commit(); st.success(f"✅ Opened! **{fdn}**"); st.balloons()
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="section-glass">',unsafe_allow_html=True)
        fds = conn.execute("SELECT fd.fd_number,c.first_name||' '||c.last_name,fd.principal_amount,fd.interest_rate,fd.start_date,fd.maturity_date,fd.maturity_amount FROM fixed_deposits fd JOIN accounts a ON fd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE fd.status='ACTIVE' ORDER BY fd.maturity_date").fetchall()
        if fds:
            df = pd.DataFrame(fds,columns=['FD No','Customer','Principal','Rate','Start','Maturity','Maturity Amt'])
            st.dataframe(df.style.format({'Principal':'₹{:,.2f}','Maturity Amt':'₹{:,.2f}'}),use_container_width=True)
        else: st.info("No active FDs")
        st.markdown('</div>',unsafe_allow_html=True)
    with t3:
        st.markdown('<div class="section-glass">',unsafe_allow_html=True)
        today=date.today(); mat=conn.execute("SELECT fd.fd_number,c.first_name||' '||c.last_name,fd.maturity_amount,fd.maturity_date FROM fixed_deposits fd JOIN accounts a ON fd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE fd.maturity_date BETWEEN ? AND ? AND fd.status='ACTIVE'",(today,today+timedelta(days=30))).fetchall()
        if mat: st.warning(f"🔔 {len(mat)} FD(s) maturing soon"); st.dataframe(pd.DataFrame(mat,columns=['FD','Customer','Amount','Date']).style.format({'Amount':'₹{:,.2f}'}),use_container_width=True)
        else: st.success("✅ No maturing FDs")
        st.markdown('</div>',unsafe_allow_html=True)
    conn.close()

def show_recurring_deposits():
    st.markdown('<h1 class="main-header">🔄 Recurring Deposits</h1>', unsafe_allow_html=True)
    conn = get_db()
    t1,t2,t3=st.tabs(["📝 Open","📋 Active","💳 Pay"])
    with t1:
        st.markdown('<div class="section-glass">',unsafe_allow_html=True)
        customers = conn.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND c.kyc_status='VERIFIED' AND a.status='ACTIVE'").fetchall()
        if customers:
            sel = st.selectbox("Customer",[f"{c[1]} - {c[2]}" for c in customers])
            if sel:
                idx = [f"{c[1]} - {c[2]}" for c in customers].index(sel); cust = customers[idx]
                with st.form("rd_f"):
                    c1,c2=st.columns(2)
                    with c1: monthly=st.number_input("Monthly (₹)",min_value=100.0,step=100.0,value=1000.0); tenure=st.selectbox("Tenure",[6,12,24,36,48,60]); rate=st.number_input("Rate (%)",3.0,10.0,6.0,0.25)
                    with c2: sd=st.date_input("Start",date.today(),key="rds"); nom=st.text_input("Nominee")
                    md = sd+timedelta(days=tenure*30); ma = calculate_rd_maturity(monthly,rate,tenure)
                    st.info(f"📅 Maturity: {md.strftime('%d-%m-%Y')} | 💰 Maturity: ₹{ma:,.2f}")
                    if st.form_submit_button("✨ Open RD",use_container_width=True):
                        rdn = generate_id('RD'); an = generate_account_number('RD')
                        conn.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate) VALUES (?,?,'RD',0.00,?)",(an,cust[0],rate))
                        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                        conn.execute("INSERT INTO recurring_deposits (rd_number,account_id,monthly_amount,interest_rate,start_date,maturity_date,maturity_amount,tenure_months,total_installments,nominee_name) VALUES (?,?,?,?,?,?,?,?,?,?)",(rdn,aid,monthly,rate,sd,md,ma,tenure,tenure,nom))
                        conn.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,'RD Install 1','RD_INSTALLMENT','RECEIPT',?,?)",(generate_id('TXN'),aid,monthly,monthly,generate_voucher_number('RECEIPT'),st.session_state.user['id']))
                        conn.execute("UPDATE recurring_deposits SET installments_paid=1 WHERE rd_number=?",(rdn,))
                        conn.commit(); st.success(f"✅ Opened! **{rdn}**"); st.balloons()
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="section-glass">',unsafe_allow_html=True)
        rds = conn.execute("SELECT rd.rd_number,c.first_name||' '||c.last_name,rd.monthly_amount,rd.interest_rate,rd.start_date,rd.maturity_date,rd.maturity_amount,rd.installments_paid,rd.total_installments FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE rd.status='ACTIVE' ORDER BY rd.maturity_date").fetchall()
        if rds:
            df = pd.DataFrame(rds,columns=['RD No','Customer','Monthly','Rate','Start','Maturity','Maturity Amt','Paid','Total'])
            df['Progress']=df.apply(lambda r:f"{r['Paid']}/{r['Total']} ({r['Paid']/r['Total']*100:.0f}%)",axis=1)
            st.dataframe(df.style.format({'Monthly':'₹{:,.2f}','Maturity Amt':'₹{:,.2f}'}),use_container_width=True)
        st.markdown('</div>',unsafe_allow_html=True)
    with t3:
        st.markdown('<div class="section-glass">',unsafe_allow_html=True)
        rds = conn.execute("SELECT rd.id,rd.rd_number,c.first_name||' '||c.last_name,rd.monthly_amount,rd.installments_paid,rd.total_installments,a.id FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE rd.status='ACTIVE' AND rd.installments_paid<rd.total_installments").fetchall()
        if rds:
            sel = st.selectbox("Select RD",[f"{r[1]} - {r[2]} ({r[4]}/{r[5]})" for r in rds])
            if sel:
                idx = [f"{r[1]} - {r[2]} ({r[4]}/{r[5]})" for r in rds].index(sel); rd = rds[idx]
                with st.form("pay_rd"):
                    amt = st.number_input("Amount (₹)",value=float(rd[3]),min_value=float(rd[3]))
                    if st.form_submit_button("✨ Pay",use_container_width=True):
                        conn.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,?,'RD_INSTALLMENT','RECEIPT',?,?)",(generate_id('TXN'),rd[6],amt,amt,f"RD {rd[4]+1}/{rd[5]}",generate_voucher_number('RECEIPT'),st.session_state.user['id']))
                        np=rd[4]+1; conn.execute("UPDATE recurring_deposits SET installments_paid=? WHERE id=?",(np,rd[0]))
                        if np>=rd[5]: conn.execute("UPDATE recurring_deposits SET status='MATURED' WHERE id=?",(rd[0],))
                        conn.commit(); st.success(f"✅ {np}/{rd[5]}"); st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)
    conn.close()

def show_transactions():
    st.markdown('<h1 class="main-header">💳 Transactions</h1>', unsafe_allow_html=True)
    conn = get_db()
    st.markdown('<div class="section-glass">',unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    with c1: at=st.selectbox("Account",["All","SB","FD","RD"])
    with c2: tt=st.selectbox("Type",["All","CREDIT","DEBIT"])
    with c3: fd=st.date_input("From",date.today()-timedelta(days=30),key="txf")
    with c4: td=st.date_input("To",date.today(),key="txt")
    q="SELECT t.transaction_id,c.first_name||' '||c.last_name,a.account_number,a.account_type,t.transaction_type,t.amount,t.balance_after,t.description,t.voucher_number,t.created_at FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE DATE(t.created_at) BETWEEN ? AND ?"
    params=[fd,td]
    if st.session_state.user['role']=='customer': q+=" AND c.user_id=?"; params.append(st.session_state.user['id'])
    if at!="All": q+=" AND a.account_type=?"; params.append(at)
    if tt!="All": q+=" AND t.transaction_type=?"; params.append(tt)
    q+=" ORDER BY t.created_at DESC LIMIT 200"
    txns=conn.execute(q,params).fetchall()
    if txns:
        df=pd.DataFrame(txns,columns=['Txn ID','Customer','Account','Type','Action','Amount','Balance','Description','Voucher','Date'])
        st.dataframe(df.style.format({'Amount':'₹{:,.2f}','Balance':'₹{:,.2f}'}),use_container_width=True,height=400)
        tc=sum(t[5] for t in txns if t[4]=='CREDIT'); td=sum(t[5] for t in txns if t[4]=='DEBIT')
        cc1,cc2,cc3=st.columns(3)
        with cc1: st.metric("Credits",f"₹{tc:,.2f}")
        with cc2: st.metric("Debits",f"₹{td:,.2f}")
        with cc3: st.metric("Net",f"₹{tc-td:,.2f}")
    else: st.info("No transactions")
    st.markdown('</div>',unsafe_allow_html=True)
    conn.close()

def show_journal_vouchers():
    st.markdown('<h1 class="main-header">📝 Journal Vouchers</h1>', unsafe_allow_html=True)
    if st.session_state.user['role'] not in ['admin','staff']: st.error("⛔ Unauthorized"); return
    conn = get_db()
    t1,t2=st.tabs(["📝 Create","📋 List"])
    with t1:
        st.markdown('<div class="section-glass">',unsafe_allow_html=True)
        with st.form("jv_f"):
            vd=st.date_input("Date",date.today(),key="jvd"); desc=st.text_area("Description")
            n=st.number_input("Entries",2,10,2); entries=[]; td_v=0; tc_v=0
            for i in range(int(n)):
                st.markdown(f"**Entry {i+1}**")
                x1,x2,x3=st.columns(3)
                with x1: h=st.text_input(f"Head",key=f"jh{i}")
                with x2: d=st.number_input(f"Debit",min_value=0.0,step=100.0,key=f"jd{i}")
                with x3: c=st.number_input(f"Credit",min_value=0.0,step=100.0,key=f"jc{i}")
                td_v+=d; tc_v+=c; entries.append({'h':h,'d':d,'c':c})
            st.write(f"Debit: ₹{td_v:,.2f} | Credit: ₹{tc_v:,.2f}")
            if abs(td_v-tc_v)>0.01: st.error(f"⚠️ Diff: ₹{abs(td_v-tc_v):,.2f}")
            if st.form_submit_button("✨ Create",use_container_width=True):
                if abs(td_v-tc_v)>0.01: st.error("Must balance!")
                else:
                    vn=generate_voucher_number('JOURNAL')
                    conn.execute("INSERT INTO journal_vouchers (voucher_number,voucher_date,description,total_amount,created_by) VALUES (?,?,?,?,?)",(vn,vd,desc,td_v,st.session_state.user['id']))
                    vid=conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    for e in entries:
                        if e['d']>0 or e['c']>0: conn.execute("INSERT INTO journal_entries (voucher_id,account_head,debit_amount,credit_amount) VALUES (?,?,?,?)",(vid,e['h'],e['d'],e['c']))
                    conn.commit(); st.success(f"✅ Created: **{vn}**"); st.balloons()
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="section-glass">',unsafe_allow_html=True)
        vouchers=conn.execute("SELECT jv.voucher_number,jv.voucher_date,jv.description,jv.total_amount,jv.status FROM journal_vouchers jv ORDER BY jv.created_at DESC").fetchall()
        if vouchers:
            for v in vouchers:
                sc={'DRAFT':'🟡','POSTED':'🟢','CANCELLED':'🔴'}
                with st.expander(f"{sc.get(v[4],'⚪')} {v[0]} - {v[1]} - ₹{v[3]:,.2f} ({v[4]})"):
                    st.write(f"**{v[2]}**")
                    entries=conn.execute("SELECT account_head,debit_amount,credit_amount FROM journal_entries WHERE voucher_id=(SELECT id FROM journal_vouchers WHERE voucher_number=?)",(v[0],)).fetchall()
                    if entries: st.dataframe(pd.DataFrame(entries,columns=['Head','Debit','Credit']).style.format({'Debit':'₹{:,.2f}','Credit':'₹{:,.2f}'}),use_container_width=True)
                    if v[4]=='DRAFT':
                        st.divider(); y1,y2=st.columns(2)
                        with y1:
                            if st.button(f"✅ Post",key=f"po_{v[0]}",use_container_width=True,type="primary"):
                                conn.execute("UPDATE journal_vouchers SET status='POSTED',posted_by=?,posted_at=CURRENT_TIMESTAMP WHERE voucher_number=?",(st.session_state.user['id'],v[0])); conn.commit(); st.success("✅ Posted!"); st.rerun()
                        with y2:
                            if st.button(f"❌ Cancel",key=f"ca_{v[0]}",use_container_width=True):
                                conn.execute("UPDATE journal_vouchers SET status='CANCELLED' WHERE voucher_number=?",(v[0],)); conn.commit(); st.warning("Cancelled!"); st.rerun()
        else: st.info("No vouchers")
        st.markdown('</div>',unsafe_allow_html=True)
    conn.close()

def show_reports():
    st.markdown('<h1 class="main-header">📋 Reports</h1>', unsafe_allow_html=True)
    if st.session_state.user['role'] not in ['admin','staff']: st.error("⛔ Unauthorized"); return
    rt=st.selectbox("Report",["Customer List","Interest Report","Daily Transactions"])
    conn=get_db()
    st.markdown('<div class="section-glass">',unsafe_allow_html=True)
    if rt=="Customer List":
        cust=conn.execute("SELECT customer_id,first_name,last_name,email,phone,city,kyc_status FROM customers ORDER BY customer_id DESC").fetchall()
        if cust: st.dataframe(pd.DataFrame(cust,columns=['ID','First','Last','Email','Phone','City','KYC']),use_container_width=True)
    elif rt=="Interest Report":
        calcs=conn.execute("SELECT ic.calculation_date,a.account_number,c.first_name||' '||c.last_name,ic.principal_amount,ic.interest_rate,ic.interest_earned,ic.days_calculated FROM interest_calculations ic JOIN accounts a ON ic.account_id=a.id JOIN customers c ON a.customer_id=c.id ORDER BY ic.calculation_date DESC").fetchall()
        if calcs: st.dataframe(pd.DataFrame(calcs,columns=['Date','Account','Customer','Principal','Rate','Interest','Days']).style.format({'Principal':'₹{:,.2f}','Interest':'₹{:,.2f}'}),use_container_width=True)
    elif rt=="Daily Transactions":
        rd=st.date_input("Date",date.today(),key="rpd")
        txns=conn.execute("SELECT t.transaction_id,c.first_name||' '||c.last_name,a.account_type,t.transaction_type,t.amount,t.voucher_number FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE DATE(t.created_at)=?",(rd,)).fetchall()
        if txns: st.dataframe(pd.DataFrame(txns,columns=['Txn','Customer','Type','Action','Amount','Voucher']).style.format({'Amount':'₹{:,.2f}'}),use_container_width=True)
        else: st.info(f"No transactions on {rd}")
    st.markdown('</div>',unsafe_allow_html=True)
    conn.close()

def show_my_details():
    st.markdown('<h1 class="main-header">👤 My Details</h1>', unsafe_allow_html=True)
    conn=get_db()
    cust=conn.execute("SELECT * FROM customers WHERE user_id=?",(st.session_state.user['id'],)).fetchone()
    if cust:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6,#ec4899);color:white;padding:2rem;border-radius:20px;margin-bottom:1.5rem;box-shadow:0 10px 40px rgba(99,102,241,0.3);">
            <h2 style="margin:0 0 1rem 0;">{cust[3]} {cust[4]}</h2>
            <p style="margin:0.3rem 0;">📋 {cust[2]} | 📧 {cust[7]} | 📱 {cust[8]}</p>
            <p style="margin:0.3rem 0;">🎂 {cust[5]} | 🆔 PAN: {cust[12]}</p>
        </div>""",unsafe_allow_html=True)
        st.markdown('<div class="section-glass">',unsafe_allow_html=True)
        st.markdown('<h3>💰 My SB Accounts</h3>',unsafe_allow_html=True)
        accounts=conn.execute("SELECT account_number,balance,COALESCE(total_interest_earned,0),created_at FROM accounts WHERE customer_id=? AND account_type='SB' ORDER BY created_at DESC",(cust[0],)).fetchall()
        if accounts:
            for a in accounts:
                mv=a[1]+a[2]
                st.markdown(f"""
                <div style="background:rgba(139,92,246,0.05);padding:1rem;border-radius:12px;margin:0.5rem 0;border-left:4px solid #6366f1;">
                    <b>{a[0]}</b><br>
                    Principal: ₹{a[1]:,.2f} | Interest: ₹{a[2]:,.2f}<br>
                    <b>Maturity: ₹{mv:,.2f}</b>
                </div>""",unsafe_allow_html=True)
        else: st.info("No accounts")
        st.markdown('</div>',unsafe_allow_html=True)
    else: st.warning("No profile")
    conn.close()

if __name__ == "__main__":
    main()
