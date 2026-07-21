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
        FPDF = None

# ==================== DATABASE SETUP ====================
def init_database():
    conn = sqlite3.connect('banking_system.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL, is_active BOOLEAN DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id TEXT UNIQUE NOT NULL, user_id INTEGER, first_name TEXT NOT NULL, last_name TEXT NOT NULL, date_of_birth DATE NOT NULL, gender TEXT, email TEXT UNIQUE NOT NULL, phone TEXT NOT NULL, address TEXT, city TEXT, state TEXT, pincode TEXT, pan_number TEXT UNIQUE, aadhar_number TEXT UNIQUE, kyc_status TEXT DEFAULT 'PENDING', kyc_verified_by INTEGER, kyc_verified_at TIMESTAMP, pan_document BLOB, aadhar_document BLOB, photo BLOB, signature BLOB, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, account_number TEXT UNIQUE NOT NULL, customer_id INTEGER NOT NULL, account_type TEXT NOT NULL, balance DECIMAL(15,2) DEFAULT 0.00, status TEXT DEFAULT 'ACTIVE', interest_rate DECIMAL(5,2), last_interest_calculation DATE, total_interest_earned DECIMAL(15,2) DEFAULT 0.00, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    try: c.execute("SELECT total_interest_earned FROM accounts LIMIT 1")
    except: c.execute("ALTER TABLE accounts ADD COLUMN total_interest_earned DECIMAL(15,2) DEFAULT 0.00")
    c.execute('''CREATE TABLE IF NOT EXISTS fixed_deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, fd_number TEXT UNIQUE NOT NULL, account_id INTEGER NOT NULL, principal_amount DECIMAL(15,2) NOT NULL, interest_rate DECIMAL(5,2) NOT NULL, start_date DATE NOT NULL, maturity_date DATE NOT NULL, maturity_amount DECIMAL(15,2), tenure_months INTEGER NOT NULL, status TEXT DEFAULT 'ACTIVE', nominee_name TEXT, nominee_relation TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (account_id) REFERENCES accounts (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS recurring_deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, rd_number TEXT UNIQUE NOT NULL, account_id INTEGER NOT NULL, monthly_amount DECIMAL(15,2) NOT NULL, interest_rate DECIMAL(5,2) NOT NULL, start_date DATE NOT NULL, maturity_date DATE NOT NULL, maturity_amount DECIMAL(15,2), tenure_months INTEGER NOT NULL, installments_paid INTEGER DEFAULT 0, total_installments INTEGER NOT NULL, status TEXT DEFAULT 'ACTIVE', nominee_name TEXT, nominee_relation TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (account_id) REFERENCES accounts (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id TEXT UNIQUE NOT NULL, account_id INTEGER NOT NULL, transaction_type TEXT NOT NULL, amount DECIMAL(15,2) NOT NULL, balance_after DECIMAL(15,2) NOT NULL, description TEXT, reference_type TEXT, reference_id TEXT, voucher_type TEXT, voucher_number TEXT, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (account_id) REFERENCES accounts (id), FOREIGN KEY (created_by) REFERENCES users (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS journal_vouchers (id INTEGER PRIMARY KEY AUTOINCREMENT, voucher_number TEXT UNIQUE NOT NULL, voucher_date DATE NOT NULL, description TEXT, total_amount DECIMAL(15,2) NOT NULL, status TEXT DEFAULT 'DRAFT', created_by INTEGER, posted_by INTEGER, posted_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (created_by) REFERENCES users (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS journal_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, voucher_id INTEGER NOT NULL, account_id INTEGER, account_head TEXT, debit_amount DECIMAL(15,2) DEFAULT 0.00, credit_amount DECIMAL(15,2) DEFAULT 0.00, description TEXT, FOREIGN KEY (voucher_id) REFERENCES journal_vouchers (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS ledger_heads (id INTEGER PRIMARY KEY AUTOINCREMENT, head_name TEXT UNIQUE NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS interest_calculations (id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER NOT NULL, calculation_date DATE NOT NULL, principal_amount DECIMAL(15,2) NOT NULL, interest_rate DECIMAL(5,2) NOT NULL, interest_earned DECIMAL(15,2) NOT NULL, days_calculated INTEGER NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (account_id) REFERENCES accounts (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, expense_id TEXT UNIQUE NOT NULL, expense_type TEXT NOT NULL, amount DECIMAL(15,2) NOT NULL, description TEXT, date DATE NOT NULL, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (created_by) REFERENCES users (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS income (id INTEGER PRIMARY KEY AUTOINCREMENT, income_id TEXT UNIQUE NOT NULL, income_type TEXT NOT NULL, amount DECIMAL(15,2) NOT NULL, description TEXT, date DATE NOT NULL, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (created_by) REFERENCES users (id))''')
    
    # Insert default ledger heads if empty
    if c.execute("SELECT COUNT(*) FROM ledger_heads").fetchone()[0] == 0:
        for h in ['Cash', 'Bank (Main)', 'Fee Income', 'Rent Expense', 'Salary Expense', 'Interest Paid on SB', 'Miscellaneous']:
            c.execute("INSERT OR IGNORE INTO ledger_heads (head_name) VALUES (?)", (h,))
            
    conn.commit()
    conn.close()

# ==================== UTILITY FUNCTIONS ====================
def get_db(): return sqlite3.connect('banking_system.db')
def generate_id(p): return f"{p}{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4]}"
def generate_account_number(t): return f"{'100' if t=='SB' else '200' if t=='FD' else '300'}{datetime.now().strftime('%y%m%d')}{str(uuid.uuid4().int)[:6]}"
def generate_voucher_number(v): return f"{'PMT' if v=='PAYMENT' else 'RCT' if v=='RECEIPT' else 'JNL'}{datetime.now().strftime('%Y%m%d%H%M')}{str(uuid.uuid4().int)[:4]}"
def calculate_fd_maturity(p,r,m): return round(p*(1+r/400)**(m/3),2)
def calculate_rd_maturity(m,r,mo): return round(m*(((1+r/400)**(mo/3)-1)/(1-(1+r/400)**(-1/3))),2)
def calculate_sb_interest(b,r,d): return 0 if b<=0 else round((b*r*d)/(100*365),2)

def get_minimum_balance(c,aid,fd,td):
    try:
        sb=c.execute("SELECT balance_after FROM transactions WHERE account_id=? AND DATE(created_at)<? ORDER BY created_at DESC LIMIT 1",(aid,fd)).fetchone()
        sb=sb[0] if sb else (c.execute("SELECT balance FROM accounts WHERE id=?",(aid,)).fetchone() or [0])[0]
        txns=c.execute("SELECT balance_after FROM transactions WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ? ORDER BY created_at",(aid,fd,td)).fetchall()
        return min([sb]+[t[0] for t in txns]) if txns else sb
    except: return (c.execute("SELECT balance FROM accounts WHERE id=?",(aid,)).fetchone() or [0])[0]

def calculate_and_post_sb_interest(uid=1, cfd=None, ctd=None, specific_account_ids=None):
    c = get_db()
    try:
        base_query = "SELECT id,account_number,balance,interest_rate,COALESCE(total_interest_earned,0),last_interest_calculation,customer_id,created_at FROM accounts WHERE account_type='SB' AND status='ACTIVE'"
        if specific_account_ids:
            placeholders = ','.join('?' for _ in specific_account_ids)
            base_query += f" AND id IN ({placeholders})"
            accs = c.execute(base_query, tuple(specific_account_ids)).fetchall()
        else:
            accs = c.execute(base_query).fetchall()
            
        if not accs: return "No active SB accounts match the criteria", []
        if not ctd: ctd = date.today()
        if not cfd: cfd = ctd.replace(day=1)
        posted = []
        for a in accs:
            aid, an, bal, rate, ei, lc, cid = a[0], a[1], a[2], a[3] or 3.5, a[4], a[5], a[6]
            afd = cfd
            if a[7]:
                try:
                    acd = datetime.strptime(str(a[7])[:10], '%Y-%m-%d').date()
                    if acd > afd: afd = acd
                except: pass
            if lc:
                try:
                    lcd = datetime.strptime(str(lc)[:10], '%Y-%m-%d').date()
                    if lcd >= afd: afd = lcd + timedelta(days=1)
                except: pass
            days = (ctd - afd).days + 1
            if days <= 0: continue
            mb = get_minimum_balance(c, aid, afd, ctd)
            if mb <= 0: mb = bal
            interest = calculate_sb_interest(mb, rate, days)
            if interest > 0:
                nb = bal + interest; nti = ei + interest
                c.execute("UPDATE accounts SET balance=?,total_interest_earned=?,last_interest_calculation=? WHERE id=?", (nb, nti, ctd, aid))
                c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,'SB Interest','INTEREST','RECEIPT',?,?)", (generate_id('TXN'), aid, interest, nb, generate_voucher_number('RECEIPT'), uid))
                c.execute("INSERT INTO interest_calculations (account_id,calculation_date,principal_amount,interest_rate,interest_earned,days_calculated) VALUES (?,?,?,?,?,?)", (aid, ctd, mb, rate, interest, days))
                jvn = generate_voucher_number('JOURNAL')
                c.execute("INSERT INTO journal_vouchers (voucher_number,voucher_date,description,total_amount,status,created_by) VALUES (?,?,?,?,'POSTED',?)", (jvn, ctd, f"SB Interest - A/C {an}", interest, uid))
                jid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                c.execute("INSERT INTO journal_entries (voucher_id,account_head,debit_amount,credit_amount,description) VALUES (?,'Interest Paid on SB',?,0,?)", (jid, interest, f"{days}d @ {rate}%"))
                c.execute("INSERT INTO journal_entries (voucher_id,account_head,debit_amount,credit_amount,description) VALUES (?,'Customer A/C: '||?,0,?,?)", (jid, an, interest, f"Interest credited"))
                posted.append({'account_number': an, 'min_balance': mb, 'balance_before': bal, 'interest': interest, 'new_balance': nb, 'rate': rate, 'days': days})
        c.commit(); return "SUCCESS", posted
    except Exception as e: c.rollback(); return f"Error: {e}", []
    finally: c.close()

def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()
def login_user(u,p):
    c=get_db(); cur=c.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=? AND is_active=1",(u,hash_password(p))); user=cur.fetchone(); c.close(); return user

def create_default_admin():
    c=get_db()
    if c.execute("SELECT COUNT(*) FROM users WHERE username='admin'").fetchone()[0]==0:
        c.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",('admin',hash_password('admin123'),'admin')); c.commit()
    c.close()

class BankPDF(FPDF):
    def header(self): self.set_font('Arial','B',16); self.cell(0,10,'BANKING SYSTEM',0,1,'C'); self.set_font('Arial','',10); self.cell(0,5,'Reports',0,1,'C'); self.line(10,self.get_y(),200,self.get_y()); self.ln(5)
    def footer(self): self.set_y(-15); self.set_font('Arial','I',8); self.cell(0,10,f'Page {self.page_no()}/{{nb}}',0,0,'C')

def generate_report_pdf(rt,data,fn):
    if FPDF is None: return None
    pdf=BankPDF(); pdf.alias_nb_pages(); pdf.add_page()
    if rt=='trial_balance':
        pdf.set_font('Arial','B',14); pdf.cell(0,10,'TRIAL BALANCE',0,1,'C'); pdf.set_font('Arial','',10); pdf.cell(0,5,f'As on: {data["date"]}',0,1,'C'); pdf.ln(10)
        pdf.set_font('Arial','B',10); pdf.cell(10,7,'S.No',1); pdf.cell(90,7,'Account Head',1); pdf.cell(45,7,'Debit',1,0,'R'); pdf.cell(45,7,'Credit',1,1,'R')
        pdf.set_font('Arial','',9); td_pdf=0; tc_pdf=0
        for i,e in enumerate(data['entries'],1):
            pdf.cell(10,6,str(i),1); pdf.cell(90,6,e['account_head'],1); pdf.cell(45,6,f"{e['debit']:,.2f}",1,0,'R'); pdf.cell(45,6,f"{e['credit']:,.2f}",1,1,'R'); td_pdf+=e['debit']; tc_pdf+=e['credit']
        pdf.set_font('Arial','B',10); pdf.cell(100,7,'TOTAL',1); pdf.cell(45,7,f"{td_pdf:,.2f}",1,0,'R'); pdf.cell(45,7,f"{tc_pdf:,.2f}",1,1,'R')
    pdf.output(fn); return fn

def init_session_state():
    if 'user' not in st.session_state: st.session_state.user=None
    if 'page' not in st.session_state: st.session_state.page='dashboard'

# ==================== MODERN ENTERPRISE CSS ====================
def load_enterprise_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    html, body, [class*="css"] { background-color: #f4f7f6; }
    
    .topbar {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        color: white;
        padding: 1.2rem 2.5rem;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15);
    }
    .topbar h1 { margin: 0; font-size: 1.6rem; font-weight: 800; color: #ffffff !important; letter-spacing: -0.5px; }
    .topbar .user { font-size: 0.9rem; font-weight: 500; background: rgba(255,255,255,0.15); padding: 0.5rem 1.2rem; border-radius: 20px; backdrop-filter: blur(5px); }
    
    .dash-card {
        background: white;
        border: none;
        border-radius: 16px;
        padding: 1.8rem 1.2rem;
        text-align: center;
        transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
        margin-bottom: 1rem;
    }
    .dash-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04);
        border-bottom: 3px solid #203a43;
    }
    .dash-card .icon { font-size: 2.5rem; margin-bottom: 0.5rem; display: block; }
    .dash-card h2 { font-size: 2rem; margin: 0.5rem 0; font-weight: 800; color: #0f172a; }
    .dash-card p { margin: 0; font-size: 0.8rem; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 1.2px; }
    
    .section-card {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid #f1f5f9;
    }
    .section-card h3 {
        font-size: 1.2rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid #f1f5f9;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .login-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 85vh;
        padding: 2rem;
    }
    .login-box {
        width: 100%;
        max-width: 400px;
        background: white;
        padding: 3rem 2.5rem;
        border-radius: 24px;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.1);
        border: 1px solid #e2e8f0;
        text-align: center;
    }
    .login-box h1 { margin-bottom: 0; font-size: 3rem; }
    .login-box h2 { font-weight: 800; color: #0f172a; margin-top: 1rem; margin-bottom: 0.2rem; }
    .login-box p { color: #64748b; font-weight: 500; margin-bottom: 2rem; }
    
    [data-testid="stSidebar"] {
        background-color: #0f2027 !important;
        border-right: none !important;
    }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }
    [data-testid="stSidebar"] .stButton>button {
        background: transparent !important;
        border: 1px solid transparent !important;
        text-align: left !important;
        padding: 0.7rem 1.2rem !important;
        border-radius: 10px !important;
        font-weight: 600;
        margin-bottom: 0.2rem;
        transition: all 0.2s ease;
    }
    [data-testid="stSidebar"] .stButton>button:hover,
    [data-testid="stSidebar"] .stButton>button:active {
        background: rgba(255,255,255,0.1) !important;
        color: #ffffff !important;
        transform: translateX(6px);
    }
    
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stTextArea>div>div>textarea {
        border-radius: 10px !important;
        border: 1.5px solid #e2e8f0 !important;
        box-shadow: none !important;
        padding: 0.6rem 1rem !important;
        font-weight: 500;
        background-color: #f8fafc !important;
        color: #0f172a !important;
    }
    .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus, .stSelectbox>div>div>div:focus {
        border-color: #203a43 !important;
        background-color: white !important;
        color: #0f172a !important;
        box-shadow: 0 0 0 3px rgba(32, 58, 67, 0.1) !important;
    }
    
    .stButton>button {
        border-radius: 10px !important;
        font-weight: 700 !important;
        padding: 0.6rem 1.2rem !important;
        transition: all 0.3s ease !important;
    }
    div[data-testid="stFormSubmitButton"]>button, 
    button[kind="primary"] {
        background: linear-gradient(135deg, #0f2027, #2c5364) !important;
        color: white !important;
        border: none !important;
    }
    div[data-testid="stFormSubmitButton"]>button:hover,
    button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1) !important;
    }
    
    .stDataFrame {
        border-radius: 12px !important;
        border: 1px solid #e2e8f0 !important;
        overflow: hidden !important;
    }
    .stDataFrame thead th {
        background-color: #f8fafc !important;
        color: #475569 !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.5px;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        background-color: #f1f5f9;
        padding: 6px;
        border-radius: 12px;
        gap: 4px;
        border: none;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        color: #64748b;
    }
    .stTabs [data-baseweb="tab"]:hover { background-color: #e2e8f0; }
    .stTabs [aria-selected="true"] {
        background-color: white !important;
        color: #0f172a !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ==================== MAIN APP ====================
def main():
    st.set_page_config(page_title="Banking System", page_icon="🏦", layout="wide", initial_sidebar_state="expanded")
    init_database()
    create_default_admin()
    init_session_state()
    load_enterprise_css()
    
    if st.session_state.user is None:
        show_login()
    else:
        show_app()

def show_login():
    st.markdown('<div class="login-wrapper"><div class="login-box">', unsafe_allow_html=True)
    st.markdown('<h1>🏦</h1><h2>CoreBanking</h2><p>Enterprise Management Platform</p>', unsafe_allow_html=True)
    
    u = st.text_input("Username", key="lu", placeholder="Enter your username")
    p = st.text_input("Password", type="password", key="lp", placeholder="Enter your password")
    
    st.markdown('<br>', unsafe_allow_html=True)
    if st.button("Secure Sign In", use_container_width=True, type="primary", key="bl"):
        user = login_user(u, p)
        if user:
            st.session_state.user = {'id': user[0], 'username': user[1], 'role': user[3]}
            st.rerun()
        else:
            st.error("Invalid credentials. Please try again.")
            
    st.markdown('<div style="margin-top: 1.5rem;"><small style="color: #94a3b8;">Demo Access: <b>admin / admin123</b></small></div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

def show_app():
    st.markdown(f'<div class="topbar"><h1>🏦 CoreBanking OS</h1><div class="user">👤 {st.session_state.user["username"]} &nbsp;<span style="opacity:0.7; font-size:0.8rem;">({st.session_state.user["role"].upper()})</span></div></div>', unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown('<div style="padding: 1rem 0; text-align: center;"><img src="https://cdn-icons-png.flaticon.com/512/2830/2830284.png" width="60" style="opacity:0.9; margin-bottom: 10px;"/><h3 style="margin:0; font-weight:700; color:white; font-size: 1.2rem;">Navigation</h3></div>', unsafe_allow_html=True)
        st.markdown('<hr style="border-color: rgba(255,255,255,0.1); margin-top: 0;">', unsafe_allow_html=True)
        
        menu = {'dashboard': '📊 Dashboard', 'customer_management': '👥 Customers', 'kyc_verification': '🔍 KYC Center', 'create_sb_account': '🏦 Open SB A/c', 'sb_accounts': '💰 SB Accounts', 'fixed_deposits': '💎 Fixed Deposits', 'recurring_deposits': '🔄 Recurring Dep.', 'transactions': '💳 Transactions', 'journal_vouchers': '📝 Journal Vouchers', 'income_expenses': '📈 Income & Exp.', 'interest_calculation': '📊 Interest Calc', 'trial_balance': '⚖️ Trial Balance', 'balance_sheet': '📊 Balance Sheet', 'profit_loss': '💵 Profit & Loss', 'reports': '📋 Reports Engine'} if st.session_state.user['role'] in ['admin', 'staff'] else {'dashboard': '📊 Dashboard', 'my_accounts': '💰 My Accounts', 'my_transactions': '💳 Transactions', 'my_details': '👤 Profile'}
        
        for k, v in menu.items():
            if st.sidebar.button(v, key=f"m_{k}", use_container_width=True):
                st.session_state.page = k
                st.rerun()
                
        st.markdown('<hr style="border-color: rgba(255,255,255,0.1); margin-bottom: 1rem;">', unsafe_allow_html=True)
        if st.sidebar.button("🚪 Secure Sign Out", use_container_width=True, key="so"):
            st.session_state.user = None
            st.rerun()
    
    page = st.session_state.get('page', 'dashboard')
    
    if page == 'dashboard': dashboard()
    elif page == 'customer_management': customer_mgmt()
    elif page == 'kyc_verification': kyc_verify()
    elif page == 'create_sb_account': create_sb()
    elif page in ('sb_accounts', 'my_accounts'): sb_accounts()
    elif page == 'fixed_deposits': fixed_deposits()
    elif page == 'recurring_deposits': recurring_deposits()
    elif page in ('transactions', 'my_transactions'): transactions()
    elif page == 'journal_vouchers': journal_vouchers()
    elif page == 'income_expenses': income_expenses()
    elif page == 'interest_calculation': interest_calc()
    elif page == 'trial_balance': trial_balance()
    elif page == 'balance_sheet': balance_sheet()
    elif page == 'profit_loss': profit_loss()
    elif page == 'reports': reports()
    elif page == 'my_details': my_details()

def dashboard():
    c = get_db()
    cust = c.execute("SELECT COUNT(*) FROM customers WHERE kyc_status != 'DEACTIVATED'").fetchone()[0]
    sb = c.execute("SELECT COUNT(*) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    bal = c.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    intt = c.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    kyc = c.execute("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'").fetchone()[0]
    c.close()
    
    cols = st.columns(4)
    with cols[0]: st.markdown(f'<div class="dash-card"><span class="icon">👥</span><h2>{cust}</h2><p>Total Customers</p></div>', unsafe_allow_html=True)
    with cols[1]: st.markdown(f'<div class="dash-card"><span class="icon">💰</span><h2>{sb}</h2><p>Active SB Accounts</p></div>', unsafe_allow_html=True)
    with cols[2]: st.markdown(f'<div class="dash-card"><span class="icon">🏦</span><h2>₹{bal+intt:,.0f}</h2><p>Total SB Maturity</p></div>', unsafe_allow_html=True)
    with cols[3]: st.markdown(f'<div class="dash-card"><span class="icon">🔍</span><h2>{kyc}</h2><p>Pending KYC Approvals</p></div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    c = get_db()
    x1, x2 = st.columns([1.5, 1])
    with x1:
        st.markdown('<div class="section-card"><h3>📋 Recent Transactions</h3>', unsafe_allow_html=True)
        txns = c.execute("SELECT t.transaction_id,c.first_name||' '||c.last_name,t.transaction_type,t.amount,t.created_at FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id ORDER BY t.created_at DESC LIMIT 8").fetchall()
        if txns:
            st.dataframe(pd.DataFrame(txns, columns=['Txn ID', 'Customer', 'Type', 'Amount', 'Date']).style.format({'Amount': '₹{:,.2f}'}), use_container_width=True, height=290)
        else:
            st.info("No recent transactions found.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with x2:
        st.markdown('<div class="section-card"><h3>📊 Accounts Distribution</h3>', unsafe_allow_html=True)
        accs = c.execute("SELECT account_type,COUNT(*) FROM accounts WHERE status='ACTIVE' GROUP BY account_type").fetchall()
        if accs:
            df = pd.DataFrame(accs, columns=['Type', 'Count'])
            fig = px.pie(df, values='Count', names='Type', hole=0.6, color_discrete_sequence=['#0f2027', '#2c5364', '#64748b'])
            fig.update_layout(height=280, margin=dict(t=10, b=10, l=10, r=10), showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No active accounts found.")
        st.markdown('</div>', unsafe_allow_html=True)
    c.close()

def customer_mgmt():
    t1, t2, t3 = st.tabs(["➕ Register New Customer", "📋 View Customers", "✏️ Edit / Resubmit KYC"])
    
    with t1:
        st.markdown('<div class="section-card"><h3>Register New Customer</h3>', unsafe_allow_html=True)
        with st.form("cr"):
            c1, c2 = st.columns(2)
            with c1: 
                fn = st.text_input("First Name*")
                ln = st.text_input("Last Name*")
                dob = st.date_input("Date of Birth*", min_value=date(1900, 1, 1))
                email = st.text_input("Email Address*")
                phone = st.text_input("Phone Number*")
            with c2: 
                pan = st.text_input("PAN Number*")
                aadhar = st.text_input("Aadhar Number*")
                addr = st.text_area("Full Address")
                col_c1, col_c2 = st.columns(2)
                with col_c1: city = st.text_input("City")
                with col_c2: state = st.text_input("State")
                pin = st.text_input("PIN Code")
                
            st.markdown("#### Document Uploads")
            doc1, doc2 = st.columns(2)
            with doc1: pan_doc = st.file_uploader("Upload PAN Card*", type=['jpg', 'jpeg', 'png', 'pdf'], key="pu")
            with doc2: aadhar_doc = st.file_uploader("Upload Aadhar Card*", type=['jpg', 'jpeg', 'png', 'pdf'], key="au")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("Create Customer Profile", use_container_width=True, type="primary"):
                if not all([fn, ln, email, phone, pan, aadhar]):
                    st.error("Please fill all required (*) fields.")
                elif not pan_doc or not aadhar_doc:
                    st.error("Please upload both required documents.")
                else:
                    try:
                        conn = get_db(); cid = generate_id('CUST')
                        conn.execute("INSERT INTO customers (customer_id,first_name,last_name,date_of_birth,email,phone,address,city,state,pincode,pan_number,aadhar_number,pan_document,aadhar_document) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (cid, fn, ln, dob, email, phone, addr, city, state, pin, pan, aadhar, pan_doc.read(), aadhar_doc.read()))
                        conn.commit(); conn.close()
                        st.success(f"✅ Customer successfully registered! ID: {cid}")
                        st.balloons()
                    except sqlite3.IntegrityError:
                        st.error("❌ A customer with this Email, PAN, or Aadhar already exists.")
                    except Exception as e:
                        st.error(f"Database Error: {str(e)}")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with t2:
        st.markdown('<div class="section-card"><h3>Customer Directory</h3>', unsafe_allow_html=True)
        conn = get_db()
        custs = conn.execute("SELECT customer_id,first_name,last_name,email,phone,city,kyc_status FROM customers WHERE kyc_status != 'DEACTIVATED' ORDER BY customer_id DESC").fetchall()
        if custs:
            st.dataframe(pd.DataFrame(custs, columns=['Customer ID', 'First Name', 'Last Name', 'Email', 'Phone', 'City', 'KYC Status']), use_container_width=True, height=450)
        else:
            st.info("No active customers registered.")
        conn.close()
        st.markdown('</div>', unsafe_allow_html=True)

    with t3:
        st.markdown('<div class="section-card"><h3>Edit Customer Details & Deactivate</h3>', unsafe_allow_html=True)
        c = get_db()
        customers = c.execute("SELECT customer_id, first_name, last_name, kyc_status FROM customers WHERE kyc_status != 'DEACTIVATED' ORDER BY created_at DESC").fetchall()
        
        if not customers:
            st.info("No customers available to edit.")
        else:
            cust_dict = {f"{r[0]} - {r[1]} {r[2]} ({r[3]})": r[0] for r in customers}
            selected_cust = st.selectbox("Select Customer to Edit/Deactivate", options=list(cust_dict.keys()))
            cid = cust_dict[selected_cust]
            
            curr = c.execute("SELECT first_name, last_name, date_of_birth, email, phone, pan_number, aadhar_number, address, city, state, pincode, kyc_status FROM customers WHERE customer_id=?", (cid,)).fetchone()
            
            if curr:
                try: dob_val = datetime.strptime(str(curr[2])[:10], '%Y-%m-%d').date()
                except: dob_val = date(2000, 1, 1)
                    
                with st.form("edit_form"):
                    st.info(f"Current KYC Status: **{curr[11]}**. Submitting updates will reset status to **PENDING**.")
                    c1, c2 = st.columns(2)
                    with c1: 
                        fn = st.text_input("First Name*", value=curr[0])
                        ln = st.text_input("Last Name*", value=curr[1])
                        dob = st.date_input("Date of Birth*", value=dob_val)
                        email = st.text_input("Email Address*", value=curr[3])
                        phone = st.text_input("Phone Number*", value=curr[4])
                    with c2: 
                        pan = st.text_input("PAN Number*", value=curr[5])
                        aadhar = st.text_input("Aadhar Number*", value=curr[6])
                        addr = st.text_area("Full Address", value=curr[7] if curr[7] else "")
                        col_c1, col_c2 = st.columns(2)
                        with col_c1: city = st.text_input("City", value=curr[8] if curr[8] else "")
                        with col_c2: state = st.text_input("State", value=curr[9] if curr[9] else "")
                        pin = st.text_input("PIN Code", value=curr[10] if curr[10] else "")
                        
                    st.markdown("#### Update Documents (Optional)")
                    doc1, doc2 = st.columns(2)
                    with doc1: pan_doc = st.file_uploader("Upload New PAN Card", type=['jpg', 'jpeg', 'png', 'pdf'], key="pu_edit")
                    with doc2: aadhar_doc = st.file_uploader("Upload New Aadhar Card", type=['jpg', 'jpeg', 'png', 'pdf'], key="au_edit")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_b1, col_b2 = st.columns(2)
                    with col_b1: submit_update = st.form_submit_button("Update & Resubmit KYC", use_container_width=True, type="primary")
                    with col_b2: deactivate_btn = st.form_submit_button("🚫 Deactivate Account", use_container_width=True)
                    
                    if submit_update:
                        if not all([fn, ln, email, phone, pan, aadhar]):
                            st.error("Please fill all required (*) fields.")
                        else:
                            try:
                                conn = get_db()
                                conn.execute("""UPDATE customers SET first_name=?, last_name=?, date_of_birth=?, email=?, phone=?, address=?, city=?, state=?, pincode=?, pan_number=?, aadhar_number=?, kyc_status='PENDING' WHERE customer_id=?""", (fn, ln, dob, email, phone, addr, city, state, pin, pan, aadhar, cid))
                                if pan_doc: conn.execute("UPDATE customers SET pan_document=? WHERE customer_id=?", (pan_doc.read(), cid))
                                if aadhar_doc: conn.execute("UPDATE customers SET aadhar_document=? WHERE customer_id=?", (aadhar_doc.read(), cid))
                                conn.commit(); conn.close()
                                st.success(f"✅ Customer {cid} successfully updated and returned to PENDING status!")
                            except sqlite3.IntegrityError:
                                st.error("❌ Update failed. This Email, PAN, or Aadhar belongs to another user.")
                            except Exception as e:
                                st.error(f"Database Error: {str(e)}")
                                
                    if deactivate_btn:
                        conn = get_db()
                        conn.execute("UPDATE customers SET kyc_status='DEACTIVATED' WHERE customer_id=?", (cid,))
                        conn.commit(); conn.close()
                        st.success(f"🚫 Customer {cid} has been deactivated.")
                        st.rerun()
        c.close()
        st.markdown('</div>', unsafe_allow_html=True)

def kyc_verify():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("Unauthorized Access."); return
        
    c = get_db()
    pending = c.execute("SELECT * FROM customers WHERE kyc_status='PENDING' ORDER BY created_at").fetchall()
    c.close()
    
    st.markdown('<div class="section-card"><h3>KYC Approval Center</h3>', unsafe_allow_html=True)
    if not pending:
        st.markdown('<div class="alert alert-success">✅ All customer accounts are verified!</div>', unsafe_allow_html=True)
    else:
        for cust in pending:
            with st.expander(f"📄 {cust[3]} {cust[4]} (ID: {cust[2]}) - Pending Verification", expanded=False):
                st.markdown(f"**Name:** {cust[3]} {cust[4]} | **Email:** {cust[7]} | **Phone:** {cust[8]} | **PAN:** {cust[12]}")
                b1, b2, b3 = st.columns([1, 1, 2])
                with b1:
                    if st.button("✅ Approve KYC", key=f"a_{cust[0]}", use_container_width=True, type="primary"):
                        conn = get_db()
                        conn.execute("UPDATE customers SET kyc_status='VERIFIED',kyc_verified_by=?,kyc_verified_at=CURRENT_TIMESTAMP WHERE id=?", (st.session_state.user['id'], cust[0]))
                        if not conn.execute("SELECT id FROM accounts WHERE customer_id=? AND account_type='SB' AND status='ACTIVE'", (cust[0],)).fetchone():
                            acno = generate_account_number('SB')
                            conn.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate) VALUES (?,?,'SB',0.00,3.5)", (acno, cust[0]))
                        conn.commit(); conn.close()
                        st.success("KYC Approved & SB Account Created!")
                        st.rerun()
                with b2:
                    if st.button("❌ Reject KYC", key=f"r_{cust[0]}", use_container_width=True):
                        conn = get_db()
                        conn.execute("UPDATE customers SET kyc_status='REJECTED' WHERE id=?", (cust[0],))
                        conn.commit(); conn.close()
                        st.warning("KYC Rejected.")
                        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def create_sb():
    st.markdown('<div class="section-card"><h3>Open New Savings Account</h3>', unsafe_allow_html=True)
    c = get_db()
    custs = c.execute("SELECT id,customer_id,first_name,last_name FROM customers WHERE kyc_status='VERIFIED'").fetchall()
    c.close()
    if not custs:
        st.warning("No verified customers available. Please complete KYC verification first.")
    else:
        with st.form("sb_form"):
            cd = {f"{r[2]} {r[3]} ({r[1]})": r[0] for r in custs}
            sel = st.selectbox("Select Verified Customer", options=list(cd.keys()))
            rate = st.number_input("Interest Rate (%)", value=3.5, step=0.1)
            init_dep = st.number_input("Initial Deposit (₹)", min_value=0.00, value=1000.00)
            
            if st.form_submit_button("Create Account", type="primary", use_container_width=True):
                cid = cd[sel]; acno = generate_account_number('SB')
                conn = get_db()
                conn.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate) VALUES (?,?,'SB',?,?)", (acno, cid, init_dep, rate))
                if init_dep > 0:
                    aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    conn.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,created_by) VALUES (?,?,'CREDIT',?,?,'Initial Deposit','DEPOSIT','RECEIPT',?)", (generate_id('TXN'), aid, init_dep, init_dep, st.session_state.user['id']))
                conn.commit(); conn.close()
                st.success(f"✅ SB Account {acno} created successfully!")
    st.markdown('</div>', unsafe_allow_html=True)

def sb_accounts():
    st.markdown('<div class="section-card"><h3>Savings Bank Accounts Directory</h3>', unsafe_allow_html=True)
    c = get_db()
    if st.session_state.user['role'] == 'admin' or st.session_state.user['role'] == 'staff':
        accs = c.execute("SELECT a.account_number, c.first_name||' '||c.last_name, a.balance, a.interest_rate, a.status FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB'").fetchall()
    else:
        accs = c.execute("SELECT a.account_number, c.first_name||' '||c.last_name, a.balance, a.interest_rate, a.status FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND c.user_id=?", (st.session_state.user['id'],)).fetchall()
    c.close()
    if accs:
        st.dataframe(pd.DataFrame(accs, columns=['Account Number', 'Customer Name', 'Balance (₹)', 'Interest Rate (%)', 'Status']).style.format({'Balance (₹)': '₹{:,.2f}'}), use_container_width=True)
    else:
        st.info("No accounts found.")
    st.markdown('</div>', unsafe_allow_html=True)

def fixed_deposits(): st.info("Fixed Deposits Module Active.")
def recurring_deposits(): st.info("Recurring Deposits Module Active.")

def transactions():
    st.markdown('<div class="section-card"><h3>Transactions & Passbook Ledger</h3>', unsafe_allow_html=True)
    c = get_db()
    txns = c.execute("SELECT t.transaction_id, c.first_name||' '||c.last_name, a.account_number, t.transaction_type, t.amount, t.balance_after, t.description, t.created_at FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id ORDER BY t.created_at DESC LIMIT 50").fetchall()
    c.close()
    if txns:
        st.dataframe(pd.DataFrame(txns, columns=['Txn ID', 'Customer', 'Account No', 'Type', 'Amount', 'Balance After', 'Description', 'Timestamp']).style.format({'Amount': '₹{:,.2f}', 'Balance After': '₹{:,.2f}'}), use_container_width=True)
    else:
        st.info("No transactions recorded yet.")
    st.markdown('</div>', unsafe_allow_html=True)

def journal_vouchers():
    c = get_db()
    c.execute('''CREATE TABLE IF NOT EXISTS ledger_heads (id INTEGER PRIMARY KEY AUTOINCREMENT, head_name TEXT UNIQUE NOT NULL)''')
    if c.execute("SELECT COUNT(*) FROM ledger_heads").fetchone()[0] == 0:
        for h in ['Cash', 'Bank (Main)', 'Fee Income', 'Rent Expense', 'Salary Expense', 'Miscellaneous']:
            c.execute("INSERT OR IGNORE INTO ledger_heads (head_name) VALUES (?)", (h,))
    c.commit()

    t1, t2 = st.tabs(["📝 Create Journal Voucher", "⚙️ Manage Ledger Heads"])
    
    with t2:
        st.markdown('<div class="section-card"><h3>Create New Ledger Head</h3>', unsafe_allow_html=True)
        with st.form("new_ledger_form"):
            new_head = st.text_input("Enter New Ledger Name")
            if st.form_submit_button("➕ Add Ledger", type="primary"):
                if new_head:
                    try:
                        c.execute("INSERT INTO ledger_heads (head_name) VALUES (?)", (new_head.strip(),))
                        c.commit()
                        st.success(f"✅ Ledger '{new_head.strip()}' added!")
                    except sqlite3.IntegrityError:
                        st.error("❌ Ledger head already exists.")
                else:
                    st.error("Please enter a name.")
        st.markdown("#### Current Master Ledger Heads")
        heads = c.execute("SELECT head_name FROM ledger_heads ORDER BY head_name").fetchall()
        st.write([h[0] for h in heads])
        st.markdown('</div>', unsafe_allow_html=True)
        
    with t1:
        st.markdown('<div class="section-card"><h3>Dynamic Journal Voucher</h3>', unsafe_allow_html=True)
        accs = c.execute("SELECT a.id, a.account_number, c.first_name, c.last_name FROM accounts a JOIN customers c ON a.customer_id = c.id WHERE a.status='ACTIVE'").fetchall()
        ledgers = c.execute("SELECT head_name FROM ledger_heads ORDER BY head_name").fetchall()
        
        acc_options = {f"Customer A/C: {r[1]} ({r[2]} {r[3]})": str(r[0]) for r in accs}
        all_options = [h[0] for h in ledgers] + list(acc_options.keys())
        
        linked_cust = st.selectbox("Link Voucher to Specific Customer (Optional)", options=["None"] + [f"{r[2]} {r[3]} (A/C: {r[1]})" for r in accs])
        desc_main = st.text_input("Master Voucher Description / Narration")
        
        st.markdown("#### Voucher Entries")
        st.caption("💡 Scroll to the bottom of the table to add dynamic rows.")
        
        if 'jv_data' not in st.session_state:
            st.session_state.jv_data = pd.DataFrame([
                {"Account": None, "Debit": 0.00, "Credit": 0.00, "Line_Remarks": ""},
                {"Account": None, "Debit": 0.00, "Credit": 0.00, "Line_Remarks": ""}
            ])
            
        edited_df = st.data_editor(
            st.session_state.jv_data,
            column_config={
                "Account": st.column_config.SelectboxColumn("Account / Ledger Head", options=all_options, required=True, width="large"),
                "Debit": st.column_config.NumberColumn("Debit (₹)", min_value=0.0, format="%.2f"),
                "Credit": st.column_config.NumberColumn("Credit (₹)", min_value=0.0, format="%.2f"),
                "Line_Remarks": st.column_config.TextColumn("Line Remarks")
            },
            num_rows="dynamic",
            use_container_width=True,
            key="jv_editor"
        )
        
        total_debit = edited_df["Debit"].sum()
        total_credit = edited_df["Credit"].sum()
        
        st.markdown(f"<h4 style='text-align: right; color: {'#166534' if total_debit == total_credit and total_debit > 0 else '#92400e'};'>Total Debit: ₹{total_debit:,.2f} &nbsp;|&nbsp; Total Credit: ₹{total_credit:,.2f}</h4>", unsafe_allow_html=True)
        
        if st.button("🚀 Post Journal Entry", type="primary", use_container_width=True):
            if total_debit <= 0 or total_credit <= 0:
                st.error("❌ Amounts must be greater than zero.")
            elif round(total_debit, 2) != round(total_credit, 2):
                st.error(f"❌ Out of Balance! Debits (₹{total_debit}) and Credits (₹{total_credit}) must match.")
            elif edited_df["Account"].isnull().any():
                st.error("❌ Please select an Account/Ledger for all rows.")
            else:
                try:
                    final_desc = desc_main
                    if linked_cust != "None": final_desc = f"[Linked: {linked_cust}] " + final_desc
                        
                    conn = get_db()
                    jvn = generate_voucher_number('JOURNAL')
                    conn.execute("INSERT INTO journal_vouchers (voucher_number, voucher_date, description, total_amount, status, created_by) VALUES (?,?,?,?,'POSTED',?)", (jvn, date.today(), final_desc, total_debit, st.session_state.user['id']))
                    jid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    
                    for index, row in edited_df.iterrows():
                        acc_val = row["Account"]
                        deb = float(row["Debit"])
                        cred = float(row["Credit"])
                        narr = row["Line_Remarks"] if pd.notna(row["Line_Remarks"]) else ""
                        
                        if str(acc_val).startswith("Customer A/C:"):
                            actual_aid = acc_options[acc_val]
                            curr_bal = conn.execute("SELECT balance FROM accounts WHERE id=?", (actual_aid,)).fetchone()[0]
                            if cred > 0: 
                                new_bal = curr_bal + cred; txn_type = 'CREDIT'; amt = cred
                            elif deb > 0: 
                                new_bal = curr_bal - deb; txn_type = 'DEBIT'; amt = deb
                            else: continue
                                
                            conn.execute("UPDATE accounts SET balance=? WHERE id=?", (new_bal, actual_aid))
                            conn.execute("INSERT INTO transactions (transaction_id, account_id, transaction_type, amount, balance_after, description, reference_type, voucher_type, voucher_number, created_by) VALUES (?,?,?,?,?,?,'JOURNAL','JOURNAL',?,?)", (generate_id('TXN'), actual_aid, txn_type, amt, new_bal, narr or final_desc, jvn, st.session_state.user['id']))
                            
                        conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?,?,?,?,?)", (jid, acc_val, deb, cred, narr))
                        
                    conn.commit()
                    st.success(f"✅ Journal Voucher {jvn} posted successfully!")
                    del st.session_state.jv_data 
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Error: {e}")
                finally:
                    conn.close()
    c.close()
    st.markdown('</div>', unsafe_allow_html=True)

def income_expenses():
    st.markdown('<div class="section-card"><h3>Income & Expenses Module</h3>', unsafe_allow_html=True)
    st.info("Record general office expenses, bank penalties, and branch income here.")
    st.markdown('</div>', unsafe_allow_html=True)

def interest_calc():
    st.markdown('<div class="section-card"><h3>Savings Bank Interest Calculation</h3>', unsafe_allow_html=True)
    c = get_db()
    accs = c.execute("SELECT a.id, a.account_number, c.first_name, c.last_name FROM accounts a JOIN customers c ON a.customer_id = c.id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
    c.close()
    
    acc_options = {f"{r[1]} - {r[2]} {r[3]}": r[0] for r in accs}
    
    with st.form("int_calc"):
        calc_type = st.radio("Calculation Scope", ["Apply to Specific Accounts", "Apply to ALL Active Accounts"], horizontal=True)
        selected_acc_ids = None
        if calc_type == "Apply to Specific Accounts":
            selected_names = st.multiselect("Select Target Accounts", options=list(acc_options.keys()))
            if selected_names: selected_acc_ids = [acc_options[n] for n in selected_names]
                
        c1, c2 = st.columns(2)
        with c1: fd = st.date_input("From Date", value=date.today().replace(day=1))
        with c2: td = st.date_input("To Date", value=date.today())
        
        if st.form_submit_button("Calculate & Post Interest", type="primary", use_container_width=True):
            if calc_type == "Apply to Specific Accounts" and not selected_acc_ids:
                st.error("❌ Please select at least one account.")
            else:
                status, results = calculate_and_post_sb_interest(st.session_state.user['id'], fd, td, selected_acc_ids)
                if status == "SUCCESS":
                    st.success(f"✅ Posted interest for {len(results)} account(s)!")
                    if results: st.dataframe(pd.DataFrame(results))
                else: st.error(status)
    st.markdown('</div>', unsafe_allow_html=True)

def trial_balance():
    st.markdown('<div class="section-card"><h3>⚖️ Trial Balance Report</h3>', unsafe_allow_html=True)
    c = get_db()
    entries = c.execute("SELECT account_head, SUM(debit_amount), SUM(credit_amount) FROM journal_entries GROUP BY account_head ORDER BY account_head").fetchall()
    c.close()
    
    if not entries:
        st.info("No accounting entries found.")
    else:
        tb_data = []
        total_dr = 0.0; total_cr = 0.0
        for head, dr, cr in entries:
            dr = dr or 0.0; cr = cr or 0.0
            net = dr - cr
            net_dr = net if net > 0 else 0.0
            net_cr = abs(net) if net < 0 else 0.0
            total_dr += net_dr; total_cr += net_cr
            tb_data.append({"Account Head": head, "Total Debit (₹)": dr, "Total Credit (₹)": cr, "Net Debit (₹)": net_dr, "Net Credit (₹)": net_cr})
            
        df_tb = pd.DataFrame(tb_data)
        st.dataframe(df_tb.style.format({"Total Debit (₹)": "₹{:,.2f}", "Total Credit (₹)": "₹{:,.2f}", "Net Debit (₹)": "₹{:,.2f}", "Net Credit (₹)": "₹{:,.2f}"}), use_container_width=True)
        
        m1, m2, m3 = st.columns(3)
        with m1: st.metric("Total Net Debits", f"₹{total_dr:,.2f}")
        with m2: st.metric("Total Net Credits", f"₹{total_cr:,.2f}")
        with m3:
            diff = abs(total_dr - total_cr)
            if diff < 0.01: st.success("✅ Trial Balance Matches")
            else: st.error(f"❌ Imbalance: ₹{diff:,.2f}")
    st.markdown('</div>', unsafe_allow_html=True)

def balance_sheet(): st.markdown('<div class="section-card"><h3>Balance Sheet</h3><p>Module active.</p></div>', unsafe_allow_html=True)
def profit_loss(): st.markdown('<div class="section-card"><h3>Profit & Loss Statement</h3><p>Module active.</p></div>', unsafe_allow_html=True)
def reports(): st.markdown('<div class="section-card"><h3>Reports Engine</h3><p>Module active.</p></div>', unsafe_allow_html=True)
def my_details(): st.markdown('<div class="section-card"><h3>My Profile</h3><p>Module active.</p></div>', unsafe_allow_html=True)

if __name__ == '__main__':
    main()




