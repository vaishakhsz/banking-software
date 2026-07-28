# 🏦 AASHA NIDHI PVT LIMITED BANK - BALARAMAPURAM
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import uuid
import os
from PIL import Image
import io
import hashlib
import base64
import plotly.express as px
import plotly.graph_objects as go
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
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL, is_active BOOLEAN DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id TEXT UNIQUE NOT NULL, user_id INTEGER, first_name TEXT NOT NULL, last_name TEXT NOT NULL, date_of_birth DATE NOT NULL, gender TEXT, email TEXT UNIQUE NOT NULL, phone TEXT NOT NULL, address TEXT, city TEXT, state TEXT, pincode TEXT, pan_number TEXT UNIQUE, aadhar_number TEXT UNIQUE, kyc_status TEXT DEFAULT 'PENDING', kyc_verified_by INTEGER, kyc_verified_at TIMESTAMP, pan_document BLOB, aadhar_document BLOB, photo BLOB, signature BLOB, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, account_number TEXT UNIQUE NOT NULL, customer_id INTEGER NOT NULL, account_type TEXT NOT NULL, balance DECIMAL(15,2) DEFAULT 0.00, status TEXT DEFAULT 'ACTIVE', interest_rate DECIMAL(5,2), last_interest_calculation DATE, total_interest_earned DECIMAL(15,2) DEFAULT 0.00, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    
    try: 
        c.execute("SELECT total_interest_earned FROM accounts LIMIT 1")
    except: 
        c.execute("ALTER TABLE accounts ADD COLUMN total_interest_earned DECIMAL(15,2) DEFAULT 0.00")
    
    c.execute('''CREATE TABLE IF NOT EXISTS fixed_deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, fd_number TEXT UNIQUE NOT NULL, account_id INTEGER NOT NULL, principal_amount DECIMAL(15,2) NOT NULL, interest_rate DECIMAL(5,2) NOT NULL, start_date DATE NOT NULL, maturity_date DATE NOT NULL, maturity_amount DECIMAL(15,2), tenure_months INTEGER NOT NULL, status TEXT DEFAULT 'ACTIVE', nominee_name TEXT, nominee_relation TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (account_id) REFERENCES accounts (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS recurring_deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, rd_number TEXT UNIQUE NOT NULL, account_id INTEGER NOT NULL, monthly_amount DECIMAL(15,2) NOT NULL, interest_rate DECIMAL(5,2) NOT NULL, start_date DATE NOT NULL, maturity_date DATE NOT NULL, maturity_amount DECIMAL(15,2), tenure_months INTEGER NOT NULL, installments_paid INTEGER DEFAULT 0, total_installments INTEGER NOT NULL, status TEXT DEFAULT 'ACTIVE', nominee_name TEXT, nominee_relation TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (account_id) REFERENCES accounts (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id TEXT UNIQUE NOT NULL, account_id INTEGER NOT NULL, transaction_type TEXT NOT NULL, amount DECIMAL(15,2) NOT NULL, balance_after DECIMAL(15,2) NOT NULL, description TEXT, reference_type TEXT, reference_id TEXT, voucher_type TEXT, voucher_number TEXT, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (account_id) REFERENCES accounts (id), FOREIGN KEY (created_by) REFERENCES users (id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS journal_vouchers (id INTEGER PRIMARY KEY AUTOINCREMENT, voucher_number TEXT UNIQUE NOT NULL, voucher_date DATE NOT NULL, description TEXT, total_amount DECIMAL(15,2) NOT NULL, status TEXT DEFAULT 'DRAFT', created_by INTEGER, posted_by INTEGER, posted_at TIMESTAMP, customer_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (created_by) REFERENCES users (id), FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    try:
        c.execute("SELECT customer_id FROM journal_vouchers LIMIT 1")
    except:
        c.execute("ALTER TABLE journal_vouchers ADD COLUMN customer_id INTEGER")
    
    c.execute('''CREATE TABLE IF NOT EXISTS journal_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, voucher_id INTEGER NOT NULL, account_id INTEGER, account_head TEXT, debit_amount DECIMAL(15,2) DEFAULT 0.00, credit_amount DECIMAL(15,2) DEFAULT 0.00, description TEXT, FOREIGN KEY (voucher_id) REFERENCES journal_vouchers (id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS interest_calculations (id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER NOT NULL, calculation_date DATE NOT NULL, principal_amount DECIMAL(15,2) NOT NULL, interest_rate DECIMAL(5,2) NOT NULL, interest_earned DECIMAL(15,2) NOT NULL, days_calculated INTEGER NOT NULL, customer_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (account_id) REFERENCES accounts (id), FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    try:
        c.execute("SELECT customer_id FROM interest_calculations LIMIT 1")
    except:
        c.execute("ALTER TABLE interest_calculations ADD COLUMN customer_id INTEGER")
    
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, expense_id TEXT UNIQUE NOT NULL, expense_type TEXT NOT NULL, amount DECIMAL(15,2) NOT NULL, description TEXT, date DATE NOT NULL, customer_id INTEGER, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (created_by) REFERENCES users (id), FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    try:
        c.execute("SELECT customer_id FROM expenses LIMIT 1")
    except:
        c.execute("ALTER TABLE expenses ADD COLUMN customer_id INTEGER")
    
    c.execute('''CREATE TABLE IF NOT EXISTS income (id INTEGER PRIMARY KEY AUTOINCREMENT, income_id TEXT UNIQUE NOT NULL, income_type TEXT NOT NULL, amount DECIMAL(15,2) NOT NULL, description TEXT, date DATE NOT NULL, customer_id INTEGER, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (created_by) REFERENCES users (id), FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    try:
        c.execute("SELECT customer_id FROM income LIMIT 1")
    except:
        c.execute("ALTER TABLE income ADD COLUMN customer_id INTEGER")
    
    conn.commit()
    conn.close()

# ==================== UTILITY FUNCTIONS ====================
def get_db(): 
    return sqlite3.connect('banking_system.db')

def generate_id(p): 
    return f"{p}{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4]}"

def generate_account_number(t): 
    return f"{'100' if t=='SB' else '200' if t=='FD' else '300'}{datetime.now().strftime('%y%m%d')}{str(uuid.uuid4().int)[:6]}"

def generate_voucher_number(v): 
    return f"{'PMT' if v=='PAYMENT' else 'RCT' if v=='RECEIPT' else 'JNL'}{datetime.now().strftime('%Y%m%d%H%M')}{str(uuid.uuid4().int)[:4]}"

def safe_text(text):
    if text is None: return "N/A"
    try: return str(text)
    except: return "Error"

def calculate_fd_maturity(p, r, m): 
    return round(p * (1 + r/400) ** (m/3), 2)

def calculate_rd_maturity(m, r, mo): 
    return round(m * (((1 + r/400) ** (mo/3) - 1) / (1 - (1 + r/400) ** (-1/3))), 2)

def calculate_sb_interest(b, r, d): 
    return 0 if b <= 0 else round((b * r * d) / (100 * 365), 2)

def get_minimum_balance(c, aid, fd, td):
    try:
        sb = c.execute("SELECT balance_after FROM transactions WHERE account_id=? AND DATE(created_at)<? ORDER BY created_at DESC LIMIT 1", (aid, fd)).fetchone()
        sb = sb[0] if sb else (c.execute("SELECT balance FROM accounts WHERE id=?", (aid,)).fetchone() or [0])[0]
        txns = c.execute("SELECT balance_after FROM transactions WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ? ORDER BY created_at", (aid, fd, td)).fetchall()
        return min([sb] + [t[0] for t in txns]) if txns else sb
    except: 
        return (c.execute("SELECT balance FROM accounts WHERE id=?", (aid,)).fetchone() or [0])[0]

def hash_password(p): 
    return hashlib.sha256(p.encode()).hexdigest()

def login_user(u, p):
    c = get_db()
    cur = c.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=? AND is_active=1", (u, hash_password(p)))
    user = cur.fetchone()
    c.close()
    return user

def create_default_admin():
    c = get_db()
    if c.execute("SELECT COUNT(*) FROM users WHERE username='admin'").fetchone()[0] == 0:
        c.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)", ('admin', hash_password('admin123'), 'admin'))
        c.commit()
    c.close()

def get_ist_time():
    from datetime import timezone, timedelta
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).strftime('%d-%m-%Y %I:%M:%S %p')

def delete_record(table, id_column, id_value, table_display):
    c = get_db()
    try:
        c.execute(f"DELETE FROM {table} WHERE {id_column}=?", (id_value,))
        c.commit()
        st.success(f"Success: {table_display} deleted!")
        st.rerun()
    except Exception as e:
        st.error(f"Error: {str(e)}")
    finally:
        c.close()

def calculate_and_post_sb_interest(created_by, from_date, to_date, customer_id=None):
    c = get_db()
    results = []
    try:
        if customer_id:
            accs = c.execute("""SELECT a.id, a.account_number, c.first_name||' '||c.last_name, a.balance, a.interest_rate, 
                               COALESCE(a.total_interest_earned, 0), c.id as cust_id 
                               FROM accounts a JOIN customers c ON a.customer_id=c.id 
                               WHERE a.account_type='SB' AND a.status='ACTIVE' AND c.id=?""", (customer_id,)).fetchall()
        else:
            accs = c.execute("""SELECT a.id, a.account_number, c.first_name||' '||c.last_name, a.balance, a.interest_rate, 
                               COALESCE(a.total_interest_earned, 0), c.id as cust_id 
                               FROM accounts a JOIN customers c ON a.customer_id=c.id 
                               WHERE a.account_type='SB' AND a.status='ACTIVE'""").fetchall()
        
        for acc in accs:
            min_bal = get_minimum_balance(c, acc[0], from_date, to_date)
            if min_bal <= 0: min_bal = acc[3]
            days = (to_date - from_date).days + 1
            if days > 0:
                interest = calculate_sb_interest(min_bal, acc[4] or 3.5, days)
                if interest > 0:
                    c.execute("UPDATE accounts SET total_interest_earned = COALESCE(total_interest_earned, 0) + ? WHERE id=?", (interest, acc[0]))
                    c.execute("INSERT INTO interest_calculations (account_id, calculation_date, principal_amount, interest_rate, interest_earned, days_calculated, customer_id) VALUES (?, DATE('now'), ?, ?, ?, ?, ?)", (acc[0], min_bal, acc[4] or 3.5, interest, days, acc[6]))
                    results.append({'account': acc[1], 'customer': acc[2], 'min_balance': min_bal, 'interest': interest, 'days': days})
        c.commit()
        return "SUCCESS", results
    except Exception as e:
        c.rollback()
        return f"ERROR: {str(e)}", []
    finally:
        c.close()

# ==================== PDF FUNCTIONS (abbreviated for brevity) ====================
class BankPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 8, 'AASHA NIDHI PVT LIMITED BANK', 0, 1, 'C')
        self.set_font('Arial', 'B', 12)
        self.cell(0, 6, 'BALARAMAPURAM', 0, 1, 'C')
        self.ln(3)
    def footer(self): 
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

def generate_statement_pdf(account_data, transactions, customer_data, from_date, to_date):
    if FPDF is None: return None
    pdf = BankPDF(); pdf.alias_nb_pages(); pdf.add_page()
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, f"ACCOUNT: {account_data['account_number']} | {customer_data['customer_name']}", 0, 1, 'L')
    pdf.cell(0, 6, f"PERIOD: {from_date} to {to_date}", 0, 1, 'L')
    pdf.ln(3)
    pdf.set_font('Arial', 'B', 9)
    for col, w in [('Date',30),('Type',20),('Credit',25),('Debit',25),('Balance',30)]:
        pdf.cell(w, 6, col, 1, 0, 'C')
    pdf.ln()
    pdf.set_font('Arial', '', 8)
    for t in transactions:
        pdf.cell(30, 5, t['date'], 1)
        pdf.cell(20, 5, t['type'], 1)
        pdf.cell(25, 5, f"{t['credit']:,.0f}" if t['credit']>0 else "", 1, 0, 'R')
        pdf.cell(25, 5, f"{t['debit']:,.0f}" if t['debit']>0 else "", 1, 0, 'R')
        pdf.cell(30, 5, f"{t['balance']:,.0f}", 1, 1, 'R')
    return pdf

# ==================== CSS ====================
def load_enterprise_css():
    st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    .topbar { background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); color: white; padding: 1rem 2rem; border-radius: 14px; display: flex; justify-content: space-between; margin-bottom: 1.5rem; }
    .dash-card { background: white; border-radius: 16px; padding: 1.5rem; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 1rem; }
    .section-card { background: white; border-radius: 16px; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    [data-testid="stSidebar"] { background-color: #0f2027 !important; }
    .stButton>button { border-radius: 10px !important; font-weight: 700 !important; }
    button[kind="primary"] { background: linear-gradient(135deg, #0f2027, #2c5364) !important; color: white !important; }
    </style>""", unsafe_allow_html=True)

# ==================== SESSION STATE ====================
def init_session_state():
    if 'user' not in st.session_state: st.session_state.user = None
    if 'page' not in st.session_state: st.session_state.page = 'dashboard'

# ==================== MAIN APP ====================
def main():
    st.set_page_config(page_title="Aasha Nidhi Bank", page_icon="🏦", layout="wide")
    init_database()
    create_default_admin()
    init_session_state()
    load_enterprise_css()
    if st.session_state.user is None: show_login()
    else: show_app()

def show_login():
    st.markdown('<div style="display:flex;justify-content:center;align-items:center;min-height:80vh"><div style="background:white;padding:3rem;border-radius:24px;text-align:center;max-width:400px"><h1>🏦 AASHA NIDHI BANK</h1><p>Balaramapuram</p>', unsafe_allow_html=True)
    u = st.text_input("Username"); p = st.text_input("Password", type="password")
    if st.button("Sign In", use_container_width=True, type="primary"):
        user = login_user(u, p)
        if user: st.session_state.user = {'id': user[0], 'username': user[1], 'role': user[3]}; st.rerun()
        else: st.error("Invalid credentials")
    st.markdown('</div></div>', unsafe_allow_html=True)

def show_app():
    st.markdown(f'<div class="topbar"><div><h2>🏦 AASHA NIDHI PVT LIMITED BANK</h2><small>BALARAMAPURAM</small></div><div>👤 {st.session_state.user["username"]} ({st.session_state.user["role"].upper()})</div></div>', unsafe_allow_html=True)
    
    with st.sidebar:
        menu = {'dashboard': 'Dashboard', 'customer_management': 'Customers', 'kyc_verification': 'KYC', 'create_sb_account': 'Open SB A/c', 'sb_accounts': 'SB Accounts', 'fixed_deposits': 'Fixed Deposits', 'recurring_deposits': 'Recurring Dep.', 'transactions': 'Transactions', 'journal_vouchers': 'Journal Vouchers', 'income_expenses': 'Income & Exp.', 'interest_calculation': 'Interest', 'trial_balance': 'Trial Balance', 'balance_sheet': 'Balance Sheet', 'profit_loss': 'Profit & Loss', 'reports': 'Reports'} if st.session_state.user['role'] in ['admin','staff'] else {'dashboard':'Dashboard','my_accounts':'My Accounts','my_transactions':'Transactions'}
        for k, v in menu.items():
            if st.sidebar.button(v, key=f"m_{k}", use_container_width=True): st.session_state.page = k; st.rerun()
        if st.sidebar.button("Sign Out", use_container_width=True): st.session_state.user = None; st.rerun()
    
    page = st.session_state.get('page', 'dashboard')
    globals()[page]()

# ==================== DASHBOARD ====================
def dashboard():
    c = get_db()
    cust = c.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    sb = c.execute("SELECT COUNT(*) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    bal = c.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    intt = c.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    cols = st.columns(4)
    cols[0].metric("Customers", cust)
    cols[1].metric("SB Accounts", sb)
    cols[2].metric("SB Deposits", f"Rs{bal:,.0f}")
    cols[3].metric("Total Interest", f"Rs{intt:,.0f}")
    c.close()

# ==================== CUSTOMER MANAGEMENT ====================
def customer_management():
    t1, t2 = st.tabs(["Register", "View All"])
    with t1:
        with st.form("cr"):
            c1, c2 = st.columns(2)
            with c1: fn=st.text_input("First Name*"); ln=st.text_input("Last Name*"); dob=st.date_input("DOB*",min_value=date(1900,1,1)); email=st.text_input("Email*"); phone=st.text_input("Phone*")
            with c2: pan=st.text_input("PAN*"); aadhar=st.text_input("Aadhar*"); addr=st.text_area("Address")
            pan_doc=st.file_uploader("PAN Card*",type=['jpg','jpeg','png','pdf'])
            aadhar_doc=st.file_uploader("Aadhar Card*",type=['jpg','jpeg','png','pdf'])
            if st.form_submit_button("Register",use_container_width=True,type="primary"):
                if all([fn,ln,email,phone,pan,aadhar]) and pan_doc and aadhar_doc:
                    conn=get_db()
                    conn.execute("INSERT INTO customers (customer_id,first_name,last_name,date_of_birth,email,phone,address,pan_number,aadhar_number,pan_document,aadhar_document) VALUES (?,?,?,?,?,?,?,?,?,?,?)",(generate_id('CUST'),fn,ln,dob,email,phone,addr,pan,aadhar,pan_doc.read(),aadhar_doc.read()))
                    conn.commit();conn.close()
                    st.success("Customer Registered!");st.balloons()
                else:st.error("Fill all required fields")
    with t2:
        conn=get_db()
        custs=conn.execute("SELECT customer_id,first_name,last_name,email,phone,kyc_status FROM customers").fetchall()
        if custs:st.dataframe(pd.DataFrame(custs,columns=['ID','First','Last','Email','Phone','KYC']),use_container_width=True)
        else:st.info("No customers")
        conn.close()

# ==================== KYC VERIFICATION ====================
def kyc_verification():
    if st.session_state.user['role'] not in ['admin','staff']:st.error("Unauthorized");return
    c=get_db()
    pending=c.execute("SELECT * FROM customers WHERE kyc_status='PENDING'").fetchall()
    if not pending:st.success("All verified!")
    else:
        for cust in pending:
            with st.expander(f"{cust[3]} {cust[4]} ({cust[2]})"):
                b1,b2=st.columns(2)
                if b1.button("Approve",key=f"a_{cust[0]}"):c.execute("UPDATE customers SET kyc_status='VERIFIED',kyc_verified_by=?,kyc_verified_at=CURRENT_TIMESTAMP WHERE id=?",(st.session_state.user['id'],cust[0]));c.commit();st.rerun()
                if b2.button("Reject",key=f"r_{cust[0]}"):c.execute("UPDATE customers SET kyc_status='REJECTED' WHERE id=?",(cust[0],));c.commit();st.rerun()
    c.close()

# ==================== CREATE SB ACCOUNT ====================
def create_sb_account():
    if st.session_state.user['role'] not in ['admin','staff']:st.error("Unauthorized");return
    c=get_db()
    custs=c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c WHERE NOT EXISTS (SELECT 1 FROM accounts a WHERE a.customer_id=c.id AND a.account_type='SB' AND a.status='ACTIVE')").fetchall()
    if not custs:st.success("All customers have SB accounts!")
    else:
        sel=st.selectbox("Select Customer",[f"{x[1]} - {x[2]}" for x in custs])
        if sel:
            idx=[f"{x[1]} - {x[2]}" for x in custs].index(sel)
            cust=custs[idx]
            with st.form("sb"):
                rate=st.number_input("Interest Rate (%)",0.0,10.0,3.5,0.25)
                bal=st.number_input("Opening Balance (Rs)",0.0,step=100.0)
                mode=st.selectbox("Deposit Mode",["CASH","BANK","CHEQUE"])
                if st.form_submit_button("Create Account",use_container_width=True,type="primary"):
                    an=generate_account_number('SB')
                    c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate,last_interest_calculation,total_interest_earned) VALUES (?,?,'SB',?,?,DATE('now'),0.00)",(an,cust[0],bal,rate))
                    # Double entry: Dr Cash/Bank (Asset) | Cr SB Deposit (Liability)
                    c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,0,'CREDIT',?,?,?,'SB_OPENING',?,?,?)",(generate_id('TXN'),bal,bal,f"SB Opening: {an}",mode,'RECEIPT',generate_voucher_number('RECEIPT'),st.session_state.user['id']))
                    c.commit()
                    st.success(f"Account Created: {an}");st.balloons()
    c.close()

# ==================== SB ACCOUNTS ====================
def sb_accounts():
    c=get_db()
    role=st.session_state.user['role'];uid=st.session_state.user['id']
    t1,t2=st.tabs(["Transact","Statement"])
    
    with t1:
        q="SELECT a.id,a.account_number,c.first_name||' '||c.last_name,a.balance,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND "+("c.user_id=?" if role=='customer' else "1=1")
        accs=c.execute(q,(uid,) if role=='customer' else ()).fetchall()
        if accs:
            sel=st.selectbox("Account",[f"{a[1]} - {a[2]} (Rs{a[3]+a[4]:,.2f})" for a in accs])
            if sel:
                idx=[f"{a[1]} - {a[2]} (Rs{a[3]+a[4]:,.2f})" for a in accs].index(sel)
                acc=accs[idx]
                tt=st.radio("Type",["Deposit","Withdraw"],horizontal=True)
                with st.form("tx"):
                    amt=st.number_input("Amount",min_value=0.01,step=100.0)
                    mode=st.selectbox("Mode",["CASH","BANK","CHEQUE"])
                    desc=st.text_input("Description")
                    if st.form_submit_button("Process",use_container_width=True,type="primary"):
                        at="DEPOSIT" if tt=="Deposit" else "WITHDRAWAL"
                        if at=="WITHDRAWAL" and amt>acc[3]:st.error("Insufficient funds!")
                        else:
                            nb=acc[3]+amt if at=="DEPOSIT" else acc[3]-amt
                            tdb="CREDIT" if at=="DEPOSIT" else "DEBIT"
                            vt="RECEIPT" if at=="DEPOSIT" else "PAYMENT"
                            # Double entry for DEPOSIT: Dr Cash/Bank (Asset up) | Cr SB Account (Liability up)
                            # Double entry for WITHDRAWAL: Dr SB Account (Liability down) | Cr Cash/Bank (Asset down)
                            c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,?,?,?,?,?,?,?,?)",(generate_id('TXN'),acc[0],tdb,amt,nb,desc,mode,vt,generate_voucher_number(vt),uid))
                            c.execute("UPDATE accounts SET balance=? WHERE id=?",(nb,acc[0]))
                            c.commit()
                            st.success(f"Done! Balance: Rs{nb+acc[4]:,.2f}");st.rerun()
    
    with t2:
        q2="SELECT a.id,a.account_number,c.customer_id,c.first_name||' '||c.last_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND "+("c.user_id=?" if role=='customer' else "1=1")
        accs=c.execute(q2,(uid,) if role=='customer' else ()).fetchall()
        if accs:
            sel=st.selectbox("Account",[f"{a[1]} - {a[4]}" for a in accs],key="ss")
            if sel:
                idx=[f"{a[1]} - {a[4]}" for a in accs].index(sel);acc=accs[idx]
                d1,d2=st.columns(2)
                with d1:fd=st.date_input("From",date.today()-timedelta(days=30))
                with d2:td=st.date_input("To",date.today())
                txns=c.execute("SELECT created_at,transaction_type,amount,balance_after,description FROM transactions WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ? ORDER BY created_at DESC",(acc[0],fd,td)).fetchall()
                if txns:
                    df=pd.DataFrame(txns,columns=['Date','Type','Amount','Balance','Description'])
                    df['Date']=pd.to_datetime(df['Date']).dt.strftime('%d-%m-%Y %H:%M')
                    st.dataframe(df.style.format({'Amount':'Rs{:,.2f}','Balance':'Rs{:,.2f}'}),use_container_width=True)
    c.close()

# ==================== FIXED DEPOSITS (with Double Entry) ====================
def fixed_deposits():
    c=get_db();uid=st.session_state.user['id']
    t1,t2,t3=st.tabs(["Open FD","Active FDs","Maturity"])
    
    with t1:
        custs=c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        if custs:
            sel=st.selectbox("Customer",[f"{x[1]} - {x[2]}" for x in custs])
            if sel:
                idx=[f"{x[1]} - {x[2]}" for x in custs].index(sel);cust=custs[idx]
                with st.form("fd"):
                    p=st.number_input("Principal (Rs)",min_value=1000.0,step=1000.0,value=10000.0)
                    t=st.selectbox("Tenure",[1,3,6,9,12,18,24,36,48,60])
                    r=st.number_input("Rate (%)",3.0,10.0,6.5,0.25)
                    sd=st.date_input("Start Date",date.today())
                    md=sd+relativedelta(months=t);ma=calculate_fd_maturity(p,r,t)
                    mode=st.selectbox("Funding Mode",["CASH","BANK","CHEQUE","SB_TRANSFER"])
                    st.info(f"Maturity: {md.strftime('%d-%m-%Y')} | Value: Rs{ma:,.2f}")
                    if st.form_submit_button("Open FD",use_container_width=True,type="primary"):
                        fdn=generate_id('FD');an=generate_account_number('FD')
                        c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate) VALUES (?,?,'FD',0.00,?)",(an,cust[0],r))
                        aid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                        c.execute("INSERT INTO fixed_deposits (fd_number,account_id,principal_amount,interest_rate,start_date,maturity_date,maturity_amount,tenure_months) VALUES (?,?,?,?,?,?,?,?)",(fdn,aid,p,r,sd,md,ma,t))
                        # Double entry: Dr FD Account (Asset - bank holds) | Cr Cash/Bank or SB (source of funds)
                        c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,'FD Deposit',?,?,?,?)",(generate_id('TXN'),aid,p,p,mode,'RECEIPT',generate_voucher_number('RECEIPT'),uid))
                        # If transferred from SB, reduce SB balance
                        if mode=='SB_TRANSFER':
                            sb_acc=c.execute("SELECT id,balance FROM accounts WHERE customer_id=? AND account_type='SB' AND status='ACTIVE'",(cust[0],)).fetchone()
                            if sb_acc and sb_acc[1]>=p:
                                c.execute("UPDATE accounts SET balance=balance-? WHERE id=?",(p,sb_acc[0]))
                                c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'DEBIT',?,?,'FD Transfer',?,?,?,?)",(generate_id('TXN'),sb_acc[0],p,sb_acc[1]-p,'SB_TRANSFER','PAYMENT',generate_voucher_number('PAYMENT'),uid))
                        c.commit()
                        st.success(f"FD Opened: {fdn}");st.balloons()
    
    with t2:
        fds=c.execute("""SELECT fd.fd_number,c.first_name||' '||c.last_name,fd.principal_amount,fd.interest_rate,
                        fd.start_date,fd.maturity_date,fd.maturity_amount,fd.tenure_months,fd.status 
                        FROM fixed_deposits fd JOIN accounts a ON fd.account_id=a.id 
                        JOIN customers c ON a.customer_id=c.id WHERE fd.status='ACTIVE'""").fetchall()
        if fds:
            df=pd.DataFrame(fds,columns=['FD Ref','Customer','Principal','Rate','Start','Maturity','Maturity Value','Tenure','Status'])
            st.dataframe(df.style.format({'Principal':'Rs{:,.2f}','Maturity Value':'Rs{:,.2f}'}),use_container_width=True)
        else:st.info("No active FDs")
    
    with t3:
        today=date.today()
        mat=c.execute("""SELECT fd.fd_number,c.first_name||' '||c.last_name,fd.maturity_amount,fd.maturity_date 
                        FROM fixed_deposits fd JOIN accounts a ON fd.account_id=a.id 
                        JOIN customers c ON a.customer_id=c.id 
                        WHERE fd.maturity_date BETWEEN ? AND ? AND fd.status='ACTIVE'""",(today,today+timedelta(days=30))).fetchall()
        if mat:
            st.warning(f"{len(mat)} FDs maturing soon!")
            st.dataframe(pd.DataFrame(mat,columns=['FD','Customer','Amount','Date']).style.format({'Amount':'Rs{:,.2f}'}),use_container_width=True)
        else:st.success("No imminent maturities")
    c.close()

# ==================== RECURRING DEPOSITS (with Double Entry) ====================
def recurring_deposits():
    c=get_db();uid=st.session_state.user['id']
    t1,t2,t3=st.tabs(["Open RD","Active RDs","Pay Installment"])
    
    with t1:
        custs=c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        if custs:
            sel=st.selectbox("Customer",[f"{x[1]} - {x[2]}" for x in custs])
            if sel:
                idx=[f"{x[1]} - {x[2]}" for x in custs].index(sel);cust=custs[idx]
                with st.form("rd"):
                    m=st.number_input("Monthly (Rs)",min_value=100.0,step=100.0,value=1000.0)
                    t=st.selectbox("Tenure",[3,6,9,12,18,24,36,48,60])
                    r=st.number_input("Rate (%)",3.0,10.0,6.0,0.25)
                    sd=st.date_input("Start Date",date.today())
                    md=sd+relativedelta(months=t);ma=calculate_rd_maturity(m,r,t)
                    mode=st.selectbox("Payment Mode",["CASH","BANK","CHEQUE"])
                    st.info(f"Maturity: {md.strftime('%d-%m-%Y')} | Value: Rs{ma:,.2f}")
                    if st.form_submit_button("Open RD",use_container_width=True,type="primary"):
                        rdn=generate_id('RD');an=generate_account_number('RD')
                        c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate) VALUES (?,?,'RD',0.00,?)",(an,cust[0],r))
                        aid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                        c.execute("INSERT INTO recurring_deposits (rd_number,account_id,monthly_amount,interest_rate,start_date,maturity_date,maturity_amount,tenure_months,total_installments) VALUES (?,?,?,?,?,?,?,?,?)",(rdn,aid,m,r,sd,md,ma,t,t))
                        # Double entry: Dr RD Account (Asset) | Cr Cash/Bank (Asset transfer)
                        c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,'RD Install 1',?,?,?,?)",(generate_id('TXN'),aid,m,m,mode,'RECEIPT',generate_voucher_number('RECEIPT'),uid))
                        c.execute("UPDATE recurring_deposits SET installments_paid=1 WHERE rd_number=?",(rdn,))
                        c.commit()
                        st.success(f"RD Opened: {rdn}");st.balloons()
    
    with t2:
        rds=c.execute("""SELECT rd.rd_number,c.first_name||' '||c.last_name,rd.monthly_amount,rd.interest_rate,
                        rd.installments_paid,rd.total_installments,rd.maturity_amount,rd.maturity_date,rd.status 
                        FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id 
                        JOIN customers c ON a.customer_id=c.id WHERE rd.status='ACTIVE'""").fetchall()
        if rds:
            df=pd.DataFrame(rds,columns=['RD Ref','Customer','Monthly','Rate','Paid','Total','Maturity','Maturity Date','Status'])
            st.dataframe(df.style.format({'Monthly':'Rs{:,.2f}','Maturity':'Rs{:,.2f}'}),use_container_width=True)
        else:st.info("No active RDs")
    
    with t3:
        rds=c.execute("""SELECT rd.id,rd.rd_number,c.first_name||' '||c.last_name,rd.monthly_amount,
                        rd.installments_paid,rd.total_installments,a.id 
                        FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id 
                        JOIN customers c ON a.customer_id=c.id 
                        WHERE rd.status='ACTIVE' AND rd.installments_paid<rd.total_installments""").fetchall()
        if rds:
            sel=st.selectbox("RD Account",[f"{r[1]} - {r[2]} (Paid:{r[4]}/{r[5]})" for r in rds])
            if sel:
                idx=[f"{r[1]} - {r[2]} (Paid:{r[4]}/{r[5]})" for r in rds].index(sel);rd=rds[idx]
                mode=st.selectbox("Payment Mode",["CASH","BANK","CHEQUE"],key="rd_mode")
                with st.form("pr"):
                    amt=st.number_input("Amount",value=float(rd[3]),min_value=float(rd[3]))
                    if st.form_submit_button("Pay",use_container_width=True,type="primary"):
                        # Double entry: Dr RD Account | Cr Cash/Bank
                        c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,?,?,?,?,?)",(generate_id('TXN'),rd[6],amt,amt,f"RD Install {rd[4]+1}/{rd[5]}",mode,'RECEIPT',generate_voucher_number('RECEIPT'),uid))
                        np=rd[4]+1
                        c.execute("UPDATE recurring_deposits SET installments_paid=? WHERE id=?",(np,rd[0]))
                        if np>=rd[5]:c.execute("UPDATE recurring_deposits SET status='MATURED' WHERE id=?",(rd[0],))
                        c.commit()
                        st.success(f"Paid! Progress:{np}/{rd[5]}");st.rerun()
        else:st.info("All up to date!")
    c.close()

# ==================== TRANSACTIONS ====================
def transactions():
    c=get_db()
    txns=c.execute("""SELECT t.transaction_id,COALESCE(c.first_name||' '||c.last_name,'System'),COALESCE(a.account_type,'General'),
                     t.transaction_type,t.amount,t.reference_type,t.description,datetime(t.created_at) 
                     FROM transactions t LEFT JOIN accounts a ON t.account_id=a.id 
                     LEFT JOIN customers c ON a.customer_id=c.id 
                     ORDER BY t.created_at DESC LIMIT 200""").fetchall()
    if txns:
        df=pd.DataFrame(txns,columns=['Txn ID','Customer','Account','Type','Amount','Mode','Description','Date'])
        st.dataframe(df.style.format({'Amount':'Rs{:,.2f}'}),use_container_width=True,height=500)
    else:st.info("No transactions")
    c.close()

# ==================== JOURNAL VOUCHERS ====================
def journal_vouchers():
    if st.session_state.user['role'] not in ['admin','staff']:st.error("Unauthorized");return
    c=get_db();uid=st.session_state.user['id']
    t1,t2=st.tabs(["Create JV","Manage"])
    
    with t1:
        with st.form("jv"):
            vd=st.date_input("Date",date.today());desc=st.text_area("Narration")
            n=st.number_input("Entries",2,10,2)
            entries=[];td_v=0;tc_v=0
            for i in range(int(n)):
                e1,e2,e3=st.columns([2,1,1])
                with e1:h=st.text_input(f"Account Head",key=f"jh{i}",placeholder="Dr: Cash/Bank A/c | Cr: Capital A/c")
                with e2:d=st.number_input(f"Debit",min_value=0.0,step=100.0,key=f"jd{i}")
                with e3:cr=st.number_input(f"Credit",min_value=0.0,step=100.0,key=f"jc{i}")
                td_v+=d;tc_v+=cr;entries.append({'h':h,'d':d,'c':cr})
            st.info(f"Dr:Rs{td_v:,.2f} | Cr:Rs{tc_v:,.2f}")
            if st.form_submit_button("Generate",use_container_width=True,type="primary"):
                if abs(td_v-tc_v)>0.01:st.error("Must balance!")
                else:
                    vn=generate_voucher_number('JOURNAL')
                    c.execute("INSERT INTO journal_vouchers (voucher_number,voucher_date,description,total_amount,created_by) VALUES (?,?,?,?,?)",(vn,vd,desc,td_v,uid))
                    vid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                    for e in entries:
                        if (e['d']>0 or e['c']>0) and e['h'].strip():
                            c.execute("INSERT INTO journal_entries (voucher_id,account_head,debit_amount,credit_amount) VALUES (?,?,?,?)",(vid,e['h'].strip(),e['d'],e['c']))
                    c.commit()
                    st.success(f"JV Created:{vn}");st.rerun()
    
    with t2:
        vouchers=c.execute("SELECT id,voucher_number,voucher_date,description,total_amount,status FROM journal_vouchers ORDER BY created_at DESC").fetchall()
        if vouchers:
            for v in vouchers:
                with st.expander(f"{v[1]} | {v[2]} | Rs{v[4]:,.2f} | {v[5]}"):
                    entries=c.execute("SELECT account_head,debit_amount,credit_amount FROM journal_entries WHERE voucher_id=?",(v[0],)).fetchall()
                    if entries:
                        df=pd.DataFrame(entries,columns=['Account Head','Debit (Dr)','Credit (Cr)'])
                        st.dataframe(df.style.format({'Debit (Dr)':'Rs{:,.2f}','Credit (Cr)':'Rs{:,.2f}'}),use_container_width=True)
                    if v[5]=='DRAFT':
                        b1,b2=st.columns(2)
                        if b1.button("Post",key=f"po_{v[0]}"):c.execute("UPDATE journal_vouchers SET status='POSTED',posted_by=?,posted_at=CURRENT_TIMESTAMP WHERE id=?",(uid,v[0]));c.commit();st.rerun()
                        if b2.button("Cancel",key=f"ca_{v[0]}"):c.execute("UPDATE journal_vouchers SET status='CANCELLED' WHERE id=?",(v[0],));c.commit();st.rerun()
        else:st.info("No vouchers")
    c.close()

# ==================== INCOME & EXPENSES (with Double Entry) ====================
def income_expenses():
    if st.session_state.user['role'] not in ['admin','staff']:st.error("Unauthorized");return
    c=get_db();uid=st.session_state.user['id']
    t1,t2,t3,t4=st.tabs(["Income","Expense","View Income","View Expenses"])
    
    with t1:
        st.info("Income = CREDIT (Revenue) | DEBIT to Cash/Bank")
        with st.form("if"):
            it=st.selectbox("Type",["Interest Earned","Fees & Charges","Commission Income","Other Income"])
            amt=st.number_input("Amount",min_value=1.0,step=100.0)
            mode=st.selectbox("Mode",["CASH","BANK","CHEQUE"])
            dt=st.date_input("Date",date.today());desc=st.text_area("Description")
            st.markdown(f"**JV:** Dr Cash/Bank({mode}) Rs{amt:,.2f} | Cr {it} Rs{amt:,.2f}")
            if st.form_submit_button("Record",use_container_width=True,type="primary"):
                c.execute("INSERT INTO income (income_id,income_type,amount,description,date,created_by) VALUES (?,?,?,?,?,?)",(generate_id('INC'),it,amt,desc,dt,uid))
                # Double entry: Dr Cash/Bank | Cr Income
                c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,0,'CREDIT',?,?,?,?,?,?,?)",(generate_id('TXN'),amt,amt,f"Income:{it}",mode,'RECEIPT',generate_voucher_number('RECEIPT'),uid))
                c.commit();st.success(f"Recorded:Rs{amt:,.2f}")
    
    with t2:
        st.info("Expense = DEBIT | CREDIT to Cash/Bank")
        with st.form("ef"):
            et=st.selectbox("Type",["Salary & Wages","Rent & Utilities","Operating Expenses","Administrative Expenses","Other Expenses"])
            amt=st.number_input("Amount",min_value=1.0,step=100.0)
            mode=st.selectbox("Mode",["CASH","BANK","CHEQUE"])
            dt=st.date_input("Date",date.today());desc=st.text_area("Description")
            st.markdown(f"**JV:** Dr {et} Rs{amt:,.2f} | Cr Cash/Bank({mode}) Rs{amt:,.2f}")
            if st.form_submit_button("Record",use_container_width=True,type="primary"):
                c.execute("INSERT INTO expenses (expense_id,expense_type,amount,description,date,created_by) VALUES (?,?,?,?,?,?)",(generate_id('EXP'),et,amt,desc,dt,uid))
                # Double entry: Dr Expense | Cr Cash/Bank
                c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,0,'DEBIT',?,?,?,?,?,?,?)",(generate_id('TXN'),amt,-amt,f"Expense:{et}",mode,'PAYMENT',generate_voucher_number('PAYMENT'),uid))
                c.commit();st.success(f"Recorded:Rs{amt:,.2f}")
    
    with t3:
        inc=c.execute("SELECT income_type,SUM(amount) FROM income GROUP BY income_type").fetchall()
        if inc:st.dataframe(pd.DataFrame(inc,columns=['Type','Amount (Cr)']).style.format({'Amount (Cr)':'Rs{:,.2f}'}),use_container_width=True)
    with t4:
        exp=c.execute("SELECT expense_type,SUM(amount) FROM expenses GROUP BY expense_type").fetchall()
        if exp:st.dataframe(pd.DataFrame(exp,columns=['Type','Amount (Dr)']).style.format({'Amount (Dr)':'Rs{:,.2f}'}),use_container_width=True)
    c.close()

# ==================== INTEREST CALCULATION ====================
def interest_calculation():
    if st.session_state.user['role'] not in ['admin','staff']:st.error("Unauthorized");return
    c=get_db();uid=st.session_state.user['id']
    d1,d2=st.columns(2)
    with d1:cfd=st.date_input("From",date.today().replace(day=1))
    with d2:ctd=st.date_input("To",date.today())
    if st.button("Calculate & Post",use_container_width=True,type="primary"):
        s,r=calculate_and_post_sb_interest(uid,cfd,ctd)
        if s=="SUCCESS" and r:st.success(f"Posted Rs{sum(x['interest'] for x in r):,.2f}")
        else:st.info("No interest")
    c.close()

# ==================== TRIAL BALANCE (Detailed with Account Holders) ====================
def trial_balance():
    if st.session_state.user['role'] not in ['admin','staff']:st.error("Unauthorized");return
    c=get_db()
    
    st.markdown("### Detailed Trial Balance")
    
    if st.button("Generate Trial Balance",use_container_width=True,type="primary"):
        td=[]
        
        # ===== ASSETS (Debit balances) =====
        st.markdown("#### ASSETS (Debit Balances)")
        
        # Cash/Bank balances by mode
        for mode,name in [('CASH','Cash in Hand'),('BANK','Cash in Bank'),('CHEQUE','Cash (Cheque)')]:
            bal=c.execute("SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END),0) FROM transactions WHERE reference_type=?",(mode,)).fetchone()[0]
            if abs(bal)>0:td.append({'head':name,'cat':'Asset','dr':max(bal,0),'cr':max(-bal,0)})
        
        # FD Deposits as Assets (money held in FD)
        fd_list=c.execute("""SELECT a.account_number,c.first_name||' '||c.last_name,fd.principal_amount 
                            FROM fixed_deposits fd JOIN accounts a ON fd.account_id=a.id 
                            JOIN customers c ON a.customer_id=c.id WHERE fd.status='ACTIVE'""").fetchall()
        fd_total=0
        for fd in fd_list:
            td.append({'head':f"FD: {fd[0]} ({fd[1]})",'cat':'Asset','dr':fd[2],'cr':0})
            fd_total+=fd[2]
        
        # RD Deposits as Assets
        rd_list=c.execute("""SELECT a.account_number,c.first_name||' '||c.last_name,rd.monthly_amount*rd.installments_paid 
                            FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id 
                            JOIN customers c ON a.customer_id=c.id WHERE rd.status='ACTIVE' AND rd.installments_paid>0""").fetchall()
        rd_total=0
        for rd in rd_list:
            if rd[2]>0:
                td.append({'head':f"RD: {rd[0]} ({rd[1]})",'cat':'Asset','dr':rd[2],'cr':0})
                rd_total+=rd[2]
        
        # JV Debit entries
        jv_dr=c.execute("SELECT je.account_head,SUM(je.debit_amount) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE jv.status='POSTED' AND je.debit_amount>0 GROUP BY je.account_head").fetchall()
        for e in jv_dr:
            if e[1]>0:td.append({'head':f"JV: {e[0]}",'cat':'Asset','dr':e[1],'cr':0})
        
        # ===== LIABILITIES (Credit balances) =====
        st.markdown("#### LIABILITIES (Credit Balances)")
        
        # SB Deposits with account holder details
        sb_list=c.execute("""SELECT a.account_number,c.first_name||' '||c.last_name,a.balance 
                            FROM accounts a JOIN customers c ON a.customer_id=c.id 
                            WHERE a.account_type='SB' AND a.status='ACTIVE'""").fetchall()
        sb_total=0
        for sb in sb_list:
            if sb[2]>0:
                td.append({'head':f"SB: {sb[0]} ({sb[1]})",'cat':'Liability','dr':0,'cr':sb[2]})
                sb_total+=sb[2]
        
        # FD maturity interest payable
        fd_int_list=c.execute("""SELECT a.account_number,c.first_name||' '||c.last_name,fd.maturity_amount-fd.principal_amount 
                                FROM fixed_deposits fd JOIN accounts a ON fd.account_id=a.id 
                                JOIN customers c ON a.customer_id=c.id WHERE fd.status='ACTIVE'""").fetchall()
        fd_int_total=0
        for fi in fd_int_list:
            if fi[2]>0:
                td.append({'head':f"FD Interest: {fi[0]} ({fi[1]})",'cat':'Liability','dr':0,'cr':fi[2]})
                fd_int_total+=fi[2]
        
        # SB Interest payable
        sb_int_list=c.execute("""SELECT a.account_number,c.first_name||' '||c.last_name,COALESCE(a.total_interest_earned,0) 
                                FROM accounts a JOIN customers c ON a.customer_id=c.id 
                                WHERE a.account_type='SB' AND a.status='ACTIVE'""").fetchall()
        sb_int_total=0
        for si in sb_int_list:
            if si[2]>0:
                td.append({'head':f"SB Interest: {si[0]} ({si[1]})",'cat':'Liability','dr':0,'cr':si[2]})
                sb_int_total+=si[2]
        
        # RD Interest payable
        rd_int_list=c.execute("""SELECT a.account_number,c.first_name||' '||c.last_name,rd.maturity_amount-(rd.monthly_amount*rd.installments_paid) 
                                FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id 
                                JOIN customers c ON a.customer_id=c.id WHERE rd.status='ACTIVE' AND rd.installments_paid>0""").fetchall()
        rd_int_total=0
        for ri in rd_int_list:
            if ri[2]>0:
                td.append({'head':f"RD Interest: {ri[0]} ({ri[1]})",'cat':'Liability','dr':0,'cr':ri[2]})
                rd_int_total+=ri[2]
        
        # JV Credit entries
        jv_cr=c.execute("SELECT je.account_head,SUM(je.credit_amount) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE jv.status='POSTED' AND je.credit_amount>0 GROUP BY je.account_head").fetchall()
        for e in jv_cr:
            if e[1]>0:td.append({'head':f"JV: {e[0]}",'cat':'Liability','dr':0,'cr':e[1]})
        
        # ===== INCOME =====
        st.markdown("#### INCOME (Credit Balances)")
        for it in ['Interest Earned','Fees & Charges','Commission Income','Other Income']:
            amt=c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type=?",(it,)).fetchone()[0]
            if amt>0:td.append({'head':it,'cat':'Income','dr':0,'cr':amt})
        
        # ===== EXPENSES =====
        st.markdown("#### EXPENSES (Debit Balances)")
        for et in ['Salary & Wages','Rent & Utilities','Operating Expenses','Administrative Expenses','Other Expenses']:
            amt=c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type=?",(et,)).fetchone()[0]
            if amt>0:td.append({'head':et,'cat':'Expense','dr':amt,'cr':0})
        
        # ===== TOTALS =====
        tdr=sum(i['dr'] for i in td);tcr=sum(i['cr'] for i in td)
        
        # Capital as balancing figure
        if abs(tcr-tdr)>0.01:
            td.append({'head':'Capital/Retained Earnings','cat':'Capital','dr':max(tdr-tcr,0),'cr':max(tcr-tdr,0)})
        
        if td:
            df=pd.DataFrame(td)
            
            # Display summary
            st.markdown("---")
            st.markdown("### Trial Balance Summary")
            m1,m2,m3,m4=st.columns(4)
            m1.metric("Total Assets (Dr)",f"Rs{sum(i['dr'] for i in td if i['cat']=='Asset'):,.2f}")
            m2.metric("Total Liabilities (Cr)",f"Rs{sum(i['cr'] for i in td if i['cat']=='Liability'):,.2f}")
            m3.metric("Total Income (Cr)",f"Rs{sum(i['cr'] for i in td if i['cat']=='Income'):,.2f}")
            m4.metric("Total Expenses (Dr)",f"Rs{sum(i['dr'] for i in td if i['cat']=='Expense'):,.2f}")
            
            # Display detailed Trial Balance
            st.markdown("---")
            st.markdown("### Detailed Trial Balance")
            st.dataframe(df[['head','cat','dr','cr']].rename(columns={'head':'Account Head','cat':'Category','dr':'Debit (Dr)','cr':'Credit (Cr)'}).style.format({'Debit (Dr)':'Rs{:,.2f}','Credit (Cr)':'Rs{:,.2f}'}),use_container_width=True,height=600)
            
            # Final totals
            dft=df['dr'].sum();cft=df['cr'].sum()
            st.markdown(f"**Gross Debit: Rs{dft:,.2f} | Gross Credit: Rs{cft:,.2f}**")
            if abs(dft-cft)<0.01:st.success("TRIAL BALANCE IS PERFECTLY BALANCED")
            else:st.error(f"Mismatch: Rs{abs(dft-cft):,.2f}")
            
            # Download
            st.download_button("Download CSV",df.to_csv(index=False),"trial_balance.csv","text/csv")
    c.close()

# ==================== BALANCE SHEET ====================
def balance_sheet():
    if st.session_state.user['role'] not in ['admin','staff']:st.error("Unauthorized");return
    c=get_db()
    if st.button("Generate",use_container_width=True,type="primary"):
        assets=[];ta=0
        for mode,name in [('CASH','Cash in Hand'),('BANK','Cash in Bank'),('CHEQUE','Cash (Cheque)')]:
            bal=c.execute("SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END),0) FROM transactions WHERE reference_type=?",(mode,)).fetchone()[0]
            if abs(bal)>0:assets.append({'name':name,'amount':bal});ta+=bal
        
        fd_total=c.execute("SELECT COALESCE(SUM(principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        if fd_total>0:assets.append({'name':'FD Deposits (Asset)','amount':fd_total});ta+=fd_total
        
        rd_total=c.execute("SELECT COALESCE(SUM(monthly_amount*installments_paid),0) FROM recurring_deposits WHERE status='ACTIVE'").fetchone()[0]
        if rd_total>0:assets.append({'name':'RD Deposits (Asset)','amount':rd_total});ta+=rd_total
        
        jv_dr=c.execute("SELECT je.account_head,SUM(je.debit_amount) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE jv.status='POSTED' AND je.debit_amount>0 GROUP BY je.account_head").fetchall()
        for e in jv_dr:
            if e[1]>0:assets.append({'name':f'JV:{e[0]}','amount':e[1]});ta+=e[1]
        
        liabilities=[];tl=0
        sb_total=c.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb_total>0:liabilities.append({'name':'SB Deposits','amount':sb_total});tl+=sb_total
        if fd_total>0:liabilities.append({'name':'FD Deposits (Liability)','amount':fd_total});tl+=fd_total
        if rd_total>0:liabilities.append({'name':'RD Deposits (Liability)','amount':rd_total});tl+=rd_total
        
        sb_int=c.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb_int>0:liabilities.append({'name':'SB Interest Payable','amount':sb_int});tl+=sb_int
        
        fd_int=c.execute("SELECT COALESCE(SUM(maturity_amount-principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        if fd_int>0:liabilities.append({'name':'FD Interest Payable','amount':fd_int});tl+=fd_int
        
        total_exp=c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
        if total_exp>0:liabilities.append({'name':'Expenses','amount':total_exp});tl+=total_exp
        
        jv_cr=c.execute("SELECT je.account_head,SUM(je.credit_amount) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE jv.status='POSTED' AND je.credit_amount>0 GROUP BY je.account_head").fetchall()
        for e in jv_cr:
            if e[1]>0:liabilities.append({'name':f'JV:{e[0]}','amount':e[1]});tl+=e[1]
        
        capital=ta-tl
        
        col1,col2=st.columns(2)
        with col1:
            st.markdown("### ASSETS")
            for item in assets:st.markdown(f"- {item['name']}: Rs{item['amount']:,.2f}")
            st.markdown(f"**Total: Rs{ta:,.2f}**")
        with col2:
            st.markdown("### LIABILITIES")
            for item in liabilities:st.markdown(f"- {item['name']}: Rs{item['amount']:,.2f}")
            st.markdown(f"**Total: Rs{tl:,.2f}**")
        st.markdown(f"### CAPITAL: Rs{capital:,.2f}")
        if abs(ta-(tl+capital))<0.01:st.success("Balanced!")
    c.close()

# ==================== PROFIT & LOSS ====================
def profit_loss():
    if st.session_state.user['role'] not in ['admin','staff']:st.error("Unauthorized");return
    c=get_db()
    d1,d2=st.columns(2)
    with d1:fd=st.date_input("From",date.today().replace(month=1,day=1))
    with d2:td=st.date_input("To",date.today())
    if st.button("Generate",use_container_width=True,type="primary"):
        inc=c.execute("SELECT income_type,SUM(amount) FROM income WHERE DATE(date) BETWEEN ? AND ? GROUP BY income_type",(fd,td)).fetchall()
        exp=c.execute("SELECT expense_type,SUM(amount) FROM expenses WHERE DATE(date) BETWEEN ? AND ? GROUP BY expense_type",(fd,td)).fetchall()
        ti=sum(i[1] for i in inc);te=sum(e[1] for e in exp)
        col1,col2=st.columns(2)
        with col1:
            st.markdown("### INCOME")
            for i in inc:st.markdown(f"- {i[0]}: Rs{i[1]:,.2f}")
            st.markdown(f"**Total: Rs{ti:,.2f}**")
        with col2:
            st.markdown("### EXPENSES")
            for e in exp:st.markdown(f"- {e[0]}: Rs{e[1]:,.2f}")
            st.markdown(f"**Total: Rs{te:,.2f}**")
        net=ti-te
        if net>=0:st.success(f"Net Profit: Rs{net:,.2f}")
        else:st.error(f"Net Loss: Rs{abs(net):,.2f}")
    c.close()

# ==================== REPORTS ====================
def reports():
    if st.session_state.user['role'] not in ['admin','staff']:st.error("Unauthorized");return
    c=get_db()
    rt=st.selectbox("Report",["Customer List","Daily Transactions"])
    if rt=="Customer List":
        custs=c.execute("SELECT customer_id,first_name,last_name,email,phone,kyc_status FROM customers").fetchall()
        if custs:st.dataframe(pd.DataFrame(custs,columns=['ID','First','Last','Email','Phone','KYC']),use_container_width=True)
    elif rt=="Daily Transactions":
        rd=st.date_input("Date",date.today())
        txns=c.execute("SELECT t.transaction_id,COALESCE(c.first_name||' '||c.last_name,'System'),COALESCE(a.account_type,'General'),t.transaction_type,t.amount,t.reference_type,t.created_at FROM transactions t LEFT JOIN accounts a ON t.account_id=a.id LEFT JOIN customers c ON a.customer_id=c.id WHERE DATE(t.created_at)=?",(rd,)).fetchall()
        if txns:st.dataframe(pd.DataFrame(txns,columns=['Txn ID','Customer','Account','Type','Amount','Mode','Time']),use_container_width=True)
        else:st.info("No transactions")
    c.close()

# ==================== MY ACCOUNTS / MY DETAILS ====================
def my_accounts():
    c=get_db()
    uid=st.session_state.user['id']
    cust=c.execute("SELECT * FROM customers WHERE user_id=?",(uid,)).fetchone()
    if cust:
        accs=c.execute("SELECT account_number,balance,COALESCE(total_interest_earned,0) FROM accounts WHERE customer_id=? AND account_type='SB'",(cust[0],)).fetchall()
        if accs:
            for a in accs:st.metric(a[0],f"Rs{a[1]+a[2]:,.2f}",f"Deposits:Rs{a[1]:,.2f} + Interest:Rs{a[2]:,.2f}")
    c.close()

def my_transactions():
    c=get_db()
    uid=st.session_state.user['id']
    txns=c.execute("""SELECT t.transaction_id,a.account_number,t.transaction_type,t.amount,t.reference_type,t.description,t.created_at 
                     FROM transactions t JOIN accounts a ON t.account_id=a.id 
                     JOIN customers c ON a.customer_id=c.id 
                     WHERE c.user_id=? ORDER BY t.created_at DESC LIMIT 100""",(uid,)).fetchall()
    if txns:st.dataframe(pd.DataFrame(txns,columns=['Txn ID','Account','Type','Amount','Mode','Description','Date']),use_container_width=True)
    else:st.info("No transactions")
    c.close()

def my_details():
    c=get_db()
    uid=st.session_state.user['id']
    cust=c.execute("SELECT * FROM customers WHERE user_id=?",(uid,)).fetchone()
    if cust:
        st.markdown(f"### {cust[3]} {cust[4]}")
        st.markdown(f"ID: {cust[2]} | Email: {cust[7]} | Phone: {cust[8]}")
    c.close()

if __name__ == "__main__":
    main()


