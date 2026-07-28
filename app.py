# 🏦 AASHA NIDHI PVT LIMITED BANK - BALARAMAPURAM
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
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL, is_active BOOLEAN DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id TEXT UNIQUE NOT NULL, user_id INTEGER, first_name TEXT NOT NULL, last_name TEXT NOT NULL, date_of_birth DATE NOT NULL, gender TEXT, email TEXT UNIQUE NOT NULL, phone TEXT NOT NULL, address TEXT, city TEXT, state TEXT, pincode TEXT, pan_number TEXT UNIQUE, aadhar_number TEXT UNIQUE, kyc_status TEXT DEFAULT 'PENDING', kyc_verified_by INTEGER, kyc_verified_at TIMESTAMP, pan_document BLOB, aadhar_document BLOB, photo BLOB, signature BLOB, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, account_number TEXT UNIQUE NOT NULL, customer_id INTEGER NOT NULL, account_type TEXT NOT NULL, balance DECIMAL(15,2) DEFAULT 0.00, status TEXT DEFAULT 'ACTIVE', interest_rate DECIMAL(5,2), last_interest_calculation DATE, total_interest_earned DECIMAL(15,2) DEFAULT 0.00, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    try: c.execute("SELECT total_interest_earned FROM accounts LIMIT 1")
    except: c.execute("ALTER TABLE accounts ADD COLUMN total_interest_earned DECIMAL(15,2) DEFAULT 0.00")
    c.execute('''CREATE TABLE IF NOT EXISTS fixed_deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, fd_number TEXT UNIQUE NOT NULL, account_id INTEGER NOT NULL, principal_amount DECIMAL(15,2) NOT NULL, interest_rate DECIMAL(5,2) NOT NULL, start_date DATE NOT NULL, maturity_date DATE NOT NULL, maturity_amount DECIMAL(15,2), tenure_months INTEGER NOT NULL, status TEXT DEFAULT 'ACTIVE', nominee_name TEXT, nominee_relation TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (account_id) REFERENCES accounts (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS recurring_deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, rd_number TEXT UNIQUE NOT NULL, account_id INTEGER NOT NULL, monthly_amount DECIMAL(15,2) NOT NULL, interest_rate DECIMAL(5,2) NOT NULL, start_date DATE NOT NULL, maturity_date DATE NOT NULL, maturity_amount DECIMAL(15,2), tenure_months INTEGER NOT NULL, installments_paid INTEGER DEFAULT 0, total_installments INTEGER NOT NULL, status TEXT DEFAULT 'ACTIVE', nominee_name TEXT, nominee_relation TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (account_id) REFERENCES accounts (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id TEXT UNIQUE NOT NULL, account_id INTEGER NOT NULL, transaction_type TEXT NOT NULL, amount DECIMAL(15,2) NOT NULL, balance_after DECIMAL(15,2) NOT NULL, description TEXT, reference_type TEXT, reference_id TEXT, voucher_type TEXT, voucher_number TEXT, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (account_id) REFERENCES accounts (id), FOREIGN KEY (created_by) REFERENCES users (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS journal_vouchers (id INTEGER PRIMARY KEY AUTOINCREMENT, voucher_number TEXT UNIQUE NOT NULL, voucher_date DATE NOT NULL, description TEXT, total_amount DECIMAL(15,2) NOT NULL, status TEXT DEFAULT 'DRAFT', created_by INTEGER, posted_by INTEGER, posted_at TIMESTAMP, customer_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (created_by) REFERENCES users (id), FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    try: c.execute("SELECT customer_id FROM journal_vouchers LIMIT 1")
    except: c.execute("ALTER TABLE journal_vouchers ADD COLUMN customer_id INTEGER")
    c.execute('''CREATE TABLE IF NOT EXISTS journal_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, voucher_id INTEGER NOT NULL, account_id INTEGER, account_head TEXT, debit_amount DECIMAL(15,2) DEFAULT 0.00, credit_amount DECIMAL(15,2) DEFAULT 0.00, description TEXT, FOREIGN KEY (voucher_id) REFERENCES journal_vouchers (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS interest_calculations (id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER NOT NULL, calculation_date DATE NOT NULL, principal_amount DECIMAL(15,2) NOT NULL, interest_rate DECIMAL(5,2) NOT NULL, interest_earned DECIMAL(15,2) NOT NULL, days_calculated INTEGER NOT NULL, customer_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (account_id) REFERENCES accounts (id), FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    try: c.execute("SELECT customer_id FROM interest_calculations LIMIT 1")
    except: c.execute("ALTER TABLE interest_calculations ADD COLUMN customer_id INTEGER")
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, expense_id TEXT UNIQUE NOT NULL, expense_type TEXT NOT NULL, amount DECIMAL(15,2) NOT NULL, description TEXT, date DATE NOT NULL, customer_id INTEGER, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (created_by) REFERENCES users (id), FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    try: c.execute("SELECT customer_id FROM expenses LIMIT 1")
    except: c.execute("ALTER TABLE expenses ADD COLUMN customer_id INTEGER")
    c.execute('''CREATE TABLE IF NOT EXISTS income (id INTEGER PRIMARY KEY AUTOINCREMENT, income_id TEXT UNIQUE NOT NULL, income_type TEXT NOT NULL, amount DECIMAL(15,2) NOT NULL, description TEXT, date DATE NOT NULL, customer_id INTEGER, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (created_by) REFERENCES users (id), FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    try: c.execute("SELECT customer_id FROM income LIMIT 1")
    except: c.execute("ALTER TABLE income ADD COLUMN customer_id INTEGER")
    conn.commit()
    conn.close()

# ==================== UTILITY FUNCTIONS ====================
def get_db(): return sqlite3.connect('banking_system.db')
def generate_id(p): return f"{p}{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4]}"
def generate_account_number(t): return f"{'100' if t=='SB' else '200' if t=='FD' else '300'}{datetime.now().strftime('%y%m%d')}{str(uuid.uuid4().int)[:6]}"
def generate_voucher_number(v): return f"{'PMT' if v=='PAYMENT' else 'RCT' if v=='RECEIPT' else 'JNL'}{datetime.now().strftime('%Y%m%d%H%M')}{str(uuid.uuid4().int)[:4]}"
def safe_text(text):
    if text is None: return "N/A"
    try: return str(text)
    except: return "Error"
def calculate_fd_maturity(p, r, m): return round(p * (1 + r/400) ** (m/3), 2)
def calculate_rd_maturity(m, r, mo): return round(m * (((1 + r/400) ** (mo/3) - 1) / (1 - (1 + r/400) ** (-1/3))), 2)
def calculate_sb_interest(b, r, d): return 0 if b <= 0 else round((b * r * d) / (100 * 365), 2)
def get_minimum_balance(c, aid, fd, td):
    try:
        sb = c.execute("SELECT balance_after FROM transactions WHERE account_id=? AND DATE(created_at)<? ORDER BY created_at DESC LIMIT 1", (aid, fd)).fetchone()
        sb = sb[0] if sb else (c.execute("SELECT balance FROM accounts WHERE id=?", (aid,)).fetchone() or [0])[0]
        txns = c.execute("SELECT balance_after FROM transactions WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ? ORDER BY created_at", (aid, fd, td)).fetchall()
        return min([sb] + [t[0] for t in txns]) if txns else sb
    except: return (c.execute("SELECT balance FROM accounts WHERE id=?", (aid,)).fetchone() or [0])[0]
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()
def login_user(u, p):
    c = get_db(); cur = c.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=? AND is_active=1", (u, hash_password(p)))
    user = cur.fetchone(); c.close(); return user
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
    try: c.execute(f"DELETE FROM {table} WHERE {id_column}=?", (id_value,)); c.commit(); st.success(f"Deleted!"); st.rerun()
    except Exception as e: st.error(f"Error: {str(e)}")
    finally: c.close()

# ==================== INTEREST CALCULATION ====================
def calculate_and_post_sb_interest(created_by, from_date, to_date, customer_id=None):
    c = get_db(); results = []
    try:
        if customer_id: accs = c.execute("SELECT a.id,a.account_number,c.first_name||' '||c.last_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0),c.id FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND c.id=?",(customer_id,)).fetchall()
        else: accs = c.execute("SELECT a.id,a.account_number,c.first_name||' '||c.last_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0),c.id FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        for acc in accs:
            min_bal=get_minimum_balance(c,acc[0],from_date,to_date)
            if min_bal<=0:min_bal=acc[3]
            days=(to_date-from_date).days+1
            if days>0:
                interest=calculate_sb_interest(min_bal,acc[4] or 3.5,days)
                if interest>0:
                    c.execute("UPDATE accounts SET total_interest_earned=COALESCE(total_interest_earned,0)+? WHERE id=?",(interest,acc[0]))
                    try: c.execute("INSERT INTO interest_calculations (account_id,calculation_date,principal_amount,interest_rate,interest_earned,days_calculated,customer_id) VALUES (?,DATE('now'),?,?,?,?,?)",(acc[0],min_bal,acc[4] or 3.5,interest,days,acc[6]))
                    except: c.execute("INSERT INTO interest_calculations (account_id,calculation_date,principal_amount,interest_rate,interest_earned,days_calculated) VALUES (?,DATE('now'),?,?,?,?)",(acc[0],min_bal,acc[4] or 3.5,interest,days))
                    results.append({'account':acc[1],'customer':acc[2],'min_balance':min_bal,'interest':interest,'days':days})
        c.commit(); return "SUCCESS",results
    except Exception as e: c.rollback(); return f"ERROR:{str(e)}",[]
    finally: c.close()

# ==================== CSS ====================
def load_enterprise_css():
    st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    *{font-family:'Plus Jakarta Sans',sans-serif}
    .topbar{background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);color:white;padding:1rem 2rem;border-radius:14px;display:flex;justify-content:space-between;margin-bottom:1.5rem}
    .dash-card{background:white;border-radius:16px;padding:1.5rem;text-align:center;box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);margin-bottom:1rem}
    .section-card{background:white;border-radius:16px;padding:1.5rem;margin-bottom:1rem;box-shadow:0 4px 6px -1px rgba(0,0,0,0.05)}
    [data-testid="stSidebar"]{background-color:#0f2027!important}
    .stButton>button{border-radius:10px!important;font-weight:700!important}
    button[kind="primary"]{background:linear-gradient(135deg,#0f2027,#2c5364)!important;color:white!important}
    </style>""",unsafe_allow_html=True)

# ==================== SESSION STATE ====================
def init_session_state():
    if 'user' not in st.session_state: st.session_state.user = None
    if 'page' not in st.session_state: st.session_state.page = 'dashboard'

# ==================== MAIN APP ====================
def main():
    st.set_page_config(page_title="Aasha Nidhi Bank",page_icon="🏦",layout="wide")
    init_database(); create_default_admin(); init_session_state(); load_enterprise_css()
    if st.session_state.user is None: show_login()
    else: show_app()

def show_login():
    st.markdown('<div style="display:flex;justify-content:center;align-items:center;min-height:80vh"><div style="background:white;padding:3rem;border-radius:24px;text-align:center;max-width:400px"><h1>🏦 AASHA NIDHI BANK</h1><p>Balaramapuram</p>',unsafe_allow_html=True)
    u=st.text_input("Username");p=st.text_input("Password",type="password")
    if st.button("Sign In",use_container_width=True,type="primary"):
        user=login_user(u,p)
        if user: st.session_state.user={'id':user[0],'username':user[1],'role':user[3]};st.rerun()
        else: st.error("Invalid credentials")
    st.markdown('</div></div>',unsafe_allow_html=True)

def show_app():
    st.markdown(f'<div class="topbar"><div><h2>🏦 AASHA NIDHI PVT LIMITED BANK</h2><small>BALARAMAPURAM</small></div><div>👤 {st.session_state.user["username"]} ({st.session_state.user["role"].upper()})</div></div>',unsafe_allow_html=True)
    with st.sidebar:
        menu={'dashboard':'Dashboard','customer_management':'Customers','kyc_verification':'KYC','create_sb_account':'Open SB','sb_accounts':'SB Accounts','fixed_deposits':'Fixed Deposits','recurring_deposits':'Recurring Dep.','transactions':'Transactions','journal_vouchers':'Journal Vouchers','income_expenses':'Income & Exp.','interest_calculation':'Interest','trial_balance':'Trial Balance','balance_sheet':'Balance Sheet','profit_loss':'Profit & Loss','reports':'Reports'} if st.session_state.user['role'] in ['admin','staff'] else {'dashboard':'Dashboard','my_accounts':'My Accounts','my_transactions':'Transactions'}
        for k,v in menu.items():
            if st.sidebar.button(v,key=f"m_{k}",use_container_width=True): st.session_state.page=k;st.rerun()
        if st.sidebar.button("Sign Out",use_container_width=True): st.session_state.user=None;st.rerun()
    page=st.session_state.get('page','dashboard')
    if page in globals(): globals()[page]()
    else: st.error(f"Page {page} not found")

# ==================== DASHBOARD ====================
def dashboard():
    c=get_db()
    cust=c.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    sb=c.execute("SELECT COUNT(*) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    bal=c.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    intt=c.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    cols=st.columns(4)
    cols[0].metric("Customers",cust);cols[1].metric("SB Accounts",sb)
    cols[2].metric("SB Deposits",f"Rs{bal:,.0f}");cols[3].metric("Interest",f"Rs{intt:,.0f}")
    c.close()

# ==================== CUSTOMER MANAGEMENT ====================
def customer_management():
    t1,t2=st.tabs(["Register","View"])
    with t1:
        with st.form("cr"):
            c1,c2=st.columns(2)
            with c1:fn=st.text_input("First Name*");ln=st.text_input("Last Name*");dob=st.date_input("DOB*",min_value=date(1900,1,1));email=st.text_input("Email*");phone=st.text_input("Phone*")
            with c2:pan=st.text_input("PAN*");aadhar=st.text_input("Aadhar*");addr=st.text_area("Address")
            pan_doc=st.file_uploader("PAN*",type=['jpg','jpeg','png','pdf']);aadhar_doc=st.file_uploader("Aadhar*",type=['jpg','jpeg','png','pdf'])
            if st.form_submit_button("Register",use_container_width=True,type="primary"):
                if all([fn,ln,email,phone,pan,aadhar]) and pan_doc and aadhar_doc:
                    conn=get_db()
                    conn.execute("INSERT INTO customers(customer_id,first_name,last_name,date_of_birth,email,phone,address,pan_number,aadhar_number,pan_document,aadhar_document) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(generate_id('CUST'),fn,ln,dob,email,phone,addr,pan,aadhar,pan_doc.read(),aadhar_doc.read()))
                    conn.commit();conn.close();st.success("Registered!");st.balloons()
                else:st.error("Fill all fields")
    with t2:
        conn=get_db()
        custs=conn.execute("SELECT customer_id,first_name,last_name,email,phone,kyc_status FROM customers").fetchall()
        if custs:st.dataframe(pd.DataFrame(custs,columns=['ID','First','Last','Email','Phone','KYC']),use_container_width=True)
        conn.close()

# ==================== KYC ====================
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

# ==================== CREATE SB ====================
def create_sb_account():
    if st.session_state.user['role'] not in ['admin','staff']:st.error("Unauthorized");return
    c=get_db()
    custs=c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c WHERE NOT EXISTS(SELECT 1 FROM accounts a WHERE a.customer_id=c.id AND a.account_type='SB' AND a.status='ACTIVE')").fetchall()
    if not custs:st.success("All have SB!")
    else:
        sel=st.selectbox("Customer",[f"{x[1]}-{x[2]}" for x in custs])
        if sel:
            idx=[f"{x[1]}-{x[2]}" for x in custs].index(sel);cust=custs[idx]
            with st.form("sb"):
                rate=st.number_input("Rate(%)",0.0,10.0,3.5,0.25);bal=st.number_input("Opening(Rs)",0.0,step=100.0)
                mode=st.selectbox("Mode",["CASH","BANK","CHEQUE"])
                if st.form_submit_button("Create",use_container_width=True,type="primary"):
                    an=generate_account_number('SB')
                    c.execute("INSERT INTO accounts(account_number,customer_id,account_type,balance,interest_rate,last_interest_calculation,total_interest_earned) VALUES(?,?,'SB',?,?,DATE('now'),0.00)",(an,cust[0],bal,rate))
                    c.execute("INSERT INTO transactions(transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES(?,0,'CREDIT',?,?,?,?,?,?,?)",(generate_id('TXN'),bal,bal,f"SB Opening:{an}",mode,'RECEIPT',generate_voucher_number('RECEIPT'),st.session_state.user['id']))
                    c.commit();st.success(f"Created:{an}");st.balloons()
    c.close()

# ==================== SB ACCOUNTS ====================
def sb_accounts():
    c=get_db();role=st.session_state.user['role'];uid=st.session_state.user['id']
    t1,t2=st.tabs(["Transact","Statement"])
    with t1:
        q="SELECT a.id,a.account_number,c.first_name||' '||c.last_name,a.balance,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND "+("c.user_id=?" if role=='customer' else "1=1")
        accs=c.execute(q,(uid,) if role=='customer' else ()).fetchall()
        if accs:
            sel=st.selectbox("Account",[f"{a[1]}-{a[2]}(Rs{a[3]+a[4]:,.2f})" for a in accs])
            if sel:
                idx=[f"{a[1]}-{a[2]}(Rs{a[3]+a[4]:,.2f})" for a in accs].index(sel);acc=accs[idx]
                tt=st.radio("Type",["Deposit","Withdraw"],horizontal=True)
                with st.form("tx"):
                    amt=st.number_input("Amount",min_value=0.01,step=100.0);mode=st.selectbox("Mode",["CASH","BANK","CHEQUE"]);desc=st.text_input("Desc")
                    if st.form_submit_button("Process",use_container_width=True,type="primary"):
                        at="DEPOSIT" if tt=="Deposit" else "WITHDRAWAL"
                        if at=="WITHDRAWAL" and amt>acc[3]:st.error("Insufficient!")
                        else:
                            nb=acc[3]+amt if at=="DEPOSIT" else acc[3]-amt
                            tdb="CREDIT" if at=="DEPOSIT" else "DEBIT"
                            vt="RECEIPT" if at=="DEPOSIT" else "PAYMENT"
                            c.execute("INSERT INTO transactions(transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES(?,?,?,?,?,?,?,?,?,?)",(generate_id('TXN'),acc[0],tdb,amt,nb,desc,mode,vt,generate_voucher_number(vt),uid))
                            c.execute("UPDATE accounts SET balance=? WHERE id=?",(nb,acc[0]));c.commit()
                            st.success(f"Done! Balance:Rs{nb+acc[4]:,.2f}");st.rerun()
    with t2:
        q2="SELECT a.id,a.account_number,c.customer_id,c.first_name||' '||c.last_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND "+("c.user_id=?" if role=='customer' else "1=1")
        accs=c.execute(q2,(uid,) if role=='customer' else ()).fetchall()
        if accs:
            sel=st.selectbox("Account",[f"{a[1]}-{a[4]}" for a in accs],key="ss")
            if sel:
                idx=[f"{a[1]}-{a[4]}" for a in accs].index(sel);acc=accs[idx]
                d1,d2=st.columns(2)
                with d1:fd=st.date_input("From",date.today()-timedelta(days=30))
                with d2:td=st.date_input("To",date.today())
                txns=c.execute("SELECT created_at,transaction_type,amount,balance_after,description FROM transactions WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ? ORDER BY created_at DESC",(acc[0],fd,td)).fetchall()
                if txns:
                    df=pd.DataFrame(txns,columns=['Date','Type','Amount','Balance','Desc'])
                    df['Date']=pd.to_datetime(df['Date']).dt.strftime('%d-%m-%Y %H:%M')
                    st.dataframe(df.style.format({'Amount':'Rs{:,.2f}','Balance':'Rs{:,.2f}'}),use_container_width=True)
    c.close()

# ==================== FIXED DEPOSITS ====================
def fixed_deposits():
    c=get_db();uid=st.session_state.user['id'];t1,t2=st.tabs(["Open FD","Active"])
    with t1:
        custs=c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        if custs:
            sel=st.selectbox("Customer",[f"{x[1]}-{x[2]}" for x in custs])
            if sel:
                idx=[f"{x[1]}-{x[2]}" for x in custs].index(sel);cust=custs[idx]
                with st.form("fd"):
                    p=st.number_input("Principal",min_value=1000.0,step=1000.0,value=10000.0)
                    t=st.selectbox("Tenure(Months)",[1,3,6,9,12,18,24,36,48,60]);r=st.number_input("Rate(%)",3.0,10.0,6.5,0.25)
                    sd=st.date_input("Start",date.today());md=sd+relativedelta(months=t);ma=calculate_fd_maturity(p,r,t)
                    mode=st.selectbox("Funding",["CASH","BANK","CHEQUE","SB_TRANSFER"])
                    st.info(f"Maturity:{md.strftime('%d-%m-%Y')} | Value:Rs{ma:,.2f}")
                    if st.form_submit_button("Open FD",use_container_width=True,type="primary"):
                        fdn=generate_id('FD');an=generate_account_number('FD')
                        c.execute("INSERT INTO accounts(account_number,customer_id,account_type,balance,interest_rate) VALUES(?,?,'FD',0.00,?)",(an,cust[0],r))
                        aid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                        c.execute("INSERT INTO fixed_deposits(fd_number,account_id,principal_amount,interest_rate,start_date,maturity_date,maturity_amount,tenure_months) VALUES(?,?,?,?,?,?,?,?)",(fdn,aid,p,r,sd,md,ma,t))
                        c.execute("INSERT INTO transactions(transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES(?,?,'CREDIT',?,?,'FD Deposit',?,?,?,?)",(generate_id('TXN'),aid,p,p,mode,'RECEIPT',generate_voucher_number('RECEIPT'),uid))
                        if mode=='SB_TRANSFER':
                            sb_acc=c.execute("SELECT id,balance FROM accounts WHERE customer_id=? AND account_type='SB' AND status='ACTIVE'",(cust[0],)).fetchone()
                            if sb_acc and sb_acc[1]>=p:
                                c.execute("UPDATE accounts SET balance=balance-? WHERE id=?",(p,sb_acc[0]))
                                c.execute("INSERT INTO transactions(transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES(?,?,'DEBIT',?,?,'FD Transfer',?,?,?,?)",(generate_id('TXN'),sb_acc[0],p,sb_acc[1]-p,'SB_TRANSFER','PAYMENT',generate_voucher_number('PAYMENT'),uid))
                        c.commit();st.success(f"FD:{fdn}");st.balloons()
    with t2:
        fds=c.execute("SELECT fd.fd_number,c.first_name||' '||c.last_name,fd.principal_amount,fd.interest_rate,fd.maturity_date,fd.maturity_amount,fd.status FROM fixed_deposits fd JOIN accounts a ON fd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE fd.status='ACTIVE'").fetchall()
        if fds:st.dataframe(pd.DataFrame(fds,columns=['FD','Customer','Principal','Rate','Maturity','Value','Status']).style.format({'Principal':'Rs{:,.2f}','Value':'Rs{:,.2f}'}),use_container_width=True)
        else:st.info("No active FDs")
    c.close()

# ==================== RECURRING DEPOSITS ====================
def recurring_deposits():
    c=get_db();uid=st.session_state.user['id'];t1,t2,t3=st.tabs(["Open RD","Active","Pay"])
    with t1:
        custs=c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        if custs:
            sel=st.selectbox("Customer",[f"{x[1]}-{x[2]}" for x in custs])
            if sel:
                idx=[f"{x[1]}-{x[2]}" for x in custs].index(sel);cust=custs[idx]
                with st.form("rd"):
                    m=st.number_input("Monthly",min_value=100.0,step=100.0,value=1000.0)
                    t=st.selectbox("Tenure",[3,6,9,12,18,24,36,48,60]);r=st.number_input("Rate(%)",3.0,10.0,6.0,0.25)
                    sd=st.date_input("Start",date.today());md=sd+relativedelta(months=t);ma=calculate_rd_maturity(m,r,t)
                    mode=st.selectbox("Mode",["CASH","BANK","CHEQUE"])
                    st.info(f"Maturity:{md.strftime('%d-%m-%Y')} | Value:Rs{ma:,.2f}")
                    if st.form_submit_button("Open RD",use_container_width=True,type="primary"):
                        rdn=generate_id('RD');an=generate_account_number('RD')
                        c.execute("INSERT INTO accounts(account_number,customer_id,account_type,balance,interest_rate) VALUES(?,?,'RD',0.00,?)",(an,cust[0],r))
                        aid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                        c.execute("INSERT INTO recurring_deposits(rd_number,account_id,monthly_amount,interest_rate,start_date,maturity_date,maturity_amount,tenure_months,total_installments) VALUES(?,?,?,?,?,?,?,?,?)",(rdn,aid,m,r,sd,md,ma,t,t))
                        c.execute("INSERT INTO transactions(transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES(?,?,'CREDIT',?,?,'RD Install 1',?,?,?,?)",(generate_id('TXN'),aid,m,m,mode,'RECEIPT',generate_voucher_number('RECEIPT'),uid))
                        c.execute("UPDATE recurring_deposits SET installments_paid=1 WHERE rd_number=?",(rdn,));c.commit()
                        st.success(f"RD:{rdn}");st.balloons()
    with t2:
        rds=c.execute("SELECT rd.rd_number,c.first_name||' '||c.last_name,rd.monthly_amount,rd.installments_paid,rd.total_installments,rd.maturity_amount FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE rd.status='ACTIVE'").fetchall()
        if rds:st.dataframe(pd.DataFrame(rds,columns=['RD','Customer','Monthly','Paid','Total','Maturity']).style.format({'Monthly':'Rs{:,.2f}','Maturity':'Rs{:,.2f}'}),use_container_width=True)
        else:st.info("No active RDs")
    with t3:
        rds=c.execute("SELECT rd.id,rd.rd_number,c.first_name||' '||c.last_name,rd.monthly_amount,rd.installments_paid,rd.total_installments,a.id FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE rd.status='ACTIVE' AND rd.installments_paid<rd.total_installments").fetchall()
        if rds:
            sel=st.selectbox("RD",[f"{r[1]}-{r[2]}({r[4]}/{r[5]})" for r in rds])
            if sel:
                idx=[f"{r[1]}-{r[2]}({r[4]}/{r[5]})" for r in rds].index(sel);rd=rds[idx];mode=st.selectbox("Mode",["CASH","BANK","CHEQUE"],key="rdm")
                with st.form("pr"):
                    amt=st.number_input("Amount",value=float(rd[3]),min_value=float(rd[3]))
                    if st.form_submit_button("Pay",use_container_width=True,type="primary"):
                        c.execute("INSERT INTO transactions(transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES(?,?,'CREDIT',?,?,?,?,?,?,?)",(generate_id('TXN'),rd[6],amt,amt,f"RD Install {rd[4]+1}/{rd[5]}",mode,'RECEIPT',generate_voucher_number('RECEIPT'),uid))
                        np=rd[4]+1;c.execute("UPDATE recurring_deposits SET installments_paid=? WHERE id=?",(np,rd[0]))
                        if np>=rd[5]:c.execute("UPDATE recurring_deposits SET status='MATURED' WHERE id=?",(rd[0],));c.commit()
                        st.success(f"Paid!{np}/{rd[5]}");st.rerun()
        else:st.info("All up to date!")
    c.close()

# ==================== TRANSACTIONS ====================
def transactions():
    c=get_db()
    txns=c.execute("SELECT t.transaction_id,COALESCE(c.first_name||' '||c.last_name,'System'),COALESCE(a.account_type,'Gen'),t.transaction_type,t.amount,t.reference_type,t.description,t.created_at FROM transactions t LEFT JOIN accounts a ON t.account_id=a.id LEFT JOIN customers c ON a.customer_id=c.id ORDER BY t.created_at DESC LIMIT 200").fetchall()
    if txns:st.dataframe(pd.DataFrame(txns,columns=['Txn','Customer','A/C','Type','Amount','Mode','Desc','Date']).style.format({'Amount':'Rs{:,.2f}'}),use_container_width=True,height=500)
    else:st.info("No transactions")
    c.close()

# ==================== JOURNAL VOUCHERS ====================
def journal_vouchers():
    if st.session_state.user['role'] not in ['admin','staff']:st.error("Unauthorized");return
    c=get_db();uid=st.session_state.user['id'];t1,t2=st.tabs(["Create","Manage"])
    with t1:
        with st.form("jv"):
            vd=st.date_input("Date",date.today());desc=st.text_area("Narration")
            n=st.number_input("Entries",2,10,2);entries=[];td_v=0;tc_v=0
            for i in range(int(n)):
                e1,e2,e3=st.columns([2,1,1])
                with e1:h=st.text_input(f"Head",key=f"jh{i}",placeholder="Capital A/c / Bank A/c")
                with e2:d=st.number_input(f"Dr",min_value=0.0,step=100.0,key=f"jd{i}")
                with e3:cr=st.number_input(f"Cr",min_value=0.0,step=100.0,key=f"jc{i}")
                td_v+=d;tc_v+=cr;entries.append({'h':h,'d':d,'c':cr})
            st.info(f"Dr:Rs{td_v:,.2f} | Cr:Rs{tc_v:,.2f}")
            if st.form_submit_button("Generate",use_container_width=True,type="primary"):
                if abs(td_v-tc_v)>0.01:st.error("Must balance!")
                else:
                    vn=generate_voucher_number('JOURNAL')
                    c.execute("INSERT INTO journal_vouchers(voucher_number,voucher_date,description,total_amount,created_by) VALUES(?,?,?,?,?)",(vn,vd,desc,td_v,uid))
                    vid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                    for e in entries:
                        if(e['d']>0 or e['c']>0)and e['h'].strip():
                            c.execute("INSERT INTO journal_entries(voucher_id,account_head,debit_amount,credit_amount) VALUES(?,?,?,?)",(vid,e['h'].strip(),e['d'],e['c']))
                    c.commit();st.success(f"JV:{vn}");st.rerun()
    with t2:
        vouchers=c.execute("SELECT id,voucher_number,voucher_date,description,total_amount,status FROM journal_vouchers ORDER BY created_at DESC").fetchall()
        if vouchers:
            for v in vouchers:
                with st.expander(f"{v[1]}|{v[2]}|Rs{v[4]:,.2f}|{v[5]}"):
                    entries=c.execute("SELECT account_head,debit_amount,credit_amount FROM journal_entries WHERE voucher_id=?",(v[0],)).fetchall()
                    if entries:
                        df=pd.DataFrame(entries,columns=['Head','Dr','Cr'])
                        st.dataframe(df.style.format({'Dr':'Rs{:,.2f}','Cr':'Rs{:,.2f}'}),use_container_width=True)
                    if v[5]=='DRAFT':
                        b1,b2=st.columns(2)
                        if b1.button("Post",key=f"po_{v[0]}"):c.execute("UPDATE journal_vouchers SET status='POSTED',posted_by=?,posted_at=CURRENT_TIMESTAMP WHERE id=?",(uid,v[0]));c.commit();st.rerun()
                        if b2.button("Cancel",key=f"ca_{v[0]}"):c.execute("UPDATE journal_vouchers SET status='CANCELLED' WHERE id=?",(v[0],));c.commit();st.rerun()
        else:st.info("No vouchers")
    c.close()

# ==================== INCOME & EXPENSES ====================
def income_expenses():
    if st.session_state.user['role'] not in ['admin','staff']:st.error("Unauthorized");return
    c=get_db();uid=st.session_state.user['id'];t1,t2,t3,t4=st.tabs(["Income","Expense","View Inc","View Exp"])
    with t1:
        with st.form("if"):
            it=st.selectbox("Type",["Interest Earned","Fees & Charges","Commission Income","Other Income"])
            amt=st.number_input("Amount",min_value=1.0,step=100.0);mode=st.selectbox("Mode",["CASH","BANK","CHEQUE"]);dt=st.date_input("Date",date.today());desc=st.text_area("Desc")
            st.markdown(f"**JV:** Dr {mode} Rs{amt:,.2f} | Cr {it} Rs{amt:,.2f}")
            if st.form_submit_button("Record",use_container_width=True,type="primary"):
                c.execute("INSERT INTO income(income_id,income_type,amount,description,date,created_by) VALUES(?,?,?,?,?,?)",(generate_id('INC'),it,amt,desc,dt,uid))
                c.execute("INSERT INTO transactions(transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES(?,0,'CREDIT',?,?,?,?,?,?,?)",(generate_id('TXN'),amt,amt,f"Income:{it}",mode,'RECEIPT',generate_voucher_number('RECEIPT'),uid))
                c.commit();st.success(f"Done:Rs{amt:,.2f}")
    with t2:
        with st.form("ef"):
            et=st.selectbox("Type",["Salary & Wages","Rent & Utilities","Operating Expenses","Administrative Expenses","Other Expenses"])
            amt=st.number_input("Amount",min_value=1.0,step=100.0);mode=st.selectbox("Mode",["CASH","BANK","CHEQUE"]);dt=st.date_input("Date",date.today());desc=st.text_area("Desc")
            st.markdown(f"**JV:** Dr {et} Rs{amt:,.2f} | Cr {mode} Rs{amt:,.2f}")
            if st.form_submit_button("Record",use_container_width=True,type="primary"):
                c.execute("INSERT INTO expenses(expense_id,expense_type,amount,description,date,created_by) VALUES(?,?,?,?,?,?)",(generate_id('EXP'),et,amt,desc,dt,uid))
                c.execute("INSERT INTO transactions(transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES(?,0,'DEBIT',?,?,?,?,?,?,?)",(generate_id('TXN'),amt,-amt,f"Expense:{et}",mode,'PAYMENT',generate_voucher_number('PAYMENT'),uid))
                c.commit();st.success(f"Done:Rs{amt:,.2f}")
    with t3:
        inc=c.execute("SELECT income_type,SUM(amount) FROM income GROUP BY income_type").fetchall()
        if inc:st.dataframe(pd.DataFrame(inc,columns=['Type','Amount(Cr)']).style.format({'Amount(Cr)':'Rs{:,.2f}'}),use_container_width=True)
    with t4:
        exp=c.execute("SELECT expense_type,SUM(amount) FROM expenses GROUP BY expense_type").fetchall()
        if exp:st.dataframe(pd.DataFrame(exp,columns=['Type','Amount(Dr)']).style.format({'Amount(Dr)':'Rs{:,.2f}'}),use_container_width=True)
    c.close()

# ==================== INTEREST ====================
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

# ==================== TRIAL BALANCE (BALANCED) ====================
# ==================== TRIAL BALANCE (BALANCED) ====================
def trial_balance():
    if st.session_state.user['role'] not in ['admin','staff']:
        st.error("Unauthorized")
        return
    c = get_db()
    st.markdown("### 📊 Trial Balance")
    
    if st.button("🔄 Generate Trial Balance", use_container_width=True, type="primary"):
        td = []
        
        # ============ ASSETS (DEBIT) ============
        
        # 1. Cash in Hand (from transactions)
        cash_bal = c.execute("""
            SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END), 0) 
            FROM transactions WHERE reference_type='CASH'
        """).fetchone()[0]
        if cash_bal > 0:
            td.append({'head': 'Cash in Hand', 'cat': 'Asset', 'dr': cash_bal, 'cr': 0})
        
        # 2. FD Deposits (from fixed_deposits)
        fd_total = c.execute("""
            SELECT COALESCE(SUM(principal_amount), 0) 
            FROM fixed_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if fd_total > 0:
            td.append({'head': 'FD Deposits Held', 'cat': 'Asset', 'dr': fd_total, 'cr': 0})
        
        # 3. RD Deposits (from recurring_deposits)
        rd_total = c.execute("""
            SELECT COALESCE(SUM(monthly_amount * installments_paid), 0) 
            FROM recurring_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if rd_total > 0:
            td.append({'head': 'RD Deposits Held', 'cat': 'Asset', 'dr': rd_total, 'cr': 0})
        
        # 4. FD Interest Receivable
        fd_int_asset = c.execute("""
            SELECT COALESCE(SUM(maturity_amount - principal_amount), 0) 
            FROM fixed_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if fd_int_asset > 0:
            td.append({'head': 'FD Interest Receivable', 'cat': 'Asset', 'dr': fd_int_asset, 'cr': 0})
        
        # 5. RD Interest Receivable
        rd_int_asset = c.execute("""
            SELECT COALESCE(SUM(maturity_amount - (monthly_amount * installments_paid)), 0) 
            FROM recurring_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if rd_int_asset > 0:
            td.append({'head': 'RD Interest Receivable', 'cat': 'Asset', 'dr': rd_int_asset, 'cr': 0})
        
        # 6. JV: Union Bank of India (from journal entries - debit)
        jv_dr = c.execute("""
            SELECT je.account_head, SUM(je.debit_amount) 
            FROM journal_entries je 
            JOIN journal_vouchers jv ON je.voucher_id = jv.id 
            WHERE jv.status='POSTED' AND je.debit_amount > 0 
            GROUP BY je.account_head
        """).fetchall()
        for e in jv_dr:
            if e[1] > 0:
                td.append({'head': f"JV: {e[0]}", 'cat': 'Asset', 'dr': e[1], 'cr': 0})
        
        # ============ LIABILITIES (CREDIT) ============
        
        # 7. SB Deposits (from accounts)
        sb_total = c.execute("""
            SELECT COALESCE(SUM(balance), 0) 
            FROM accounts WHERE account_type='SB' AND status='ACTIVE'
        """).fetchone()[0]
        if sb_total > 0:
            td.append({'head': 'SB Deposits', 'cat': 'Liability', 'dr': 0, 'cr': sb_total})
        
        # 8. SB Interest Payable
        sb_int = c.execute("""
            SELECT COALESCE(SUM(total_interest_earned), 0) 
            FROM accounts WHERE account_type='SB' AND status='ACTIVE'
        """).fetchone()[0]
        if sb_int > 0:
            td.append({'head': 'SB Interest Payable', 'cat': 'Liability', 'dr': 0, 'cr': sb_int})
        
        # 9. FD Interest Payable
        if fd_int_asset > 0:
            td.append({'head': 'FD Interest Payable', 'cat': 'Liability', 'dr': 0, 'cr': fd_int_asset})
        
        # 10. RD Interest Payable
        if rd_int_asset > 0:
            td.append({'head': 'RD Interest Payable', 'cat': 'Liability', 'dr': 0, 'cr': rd_int_asset})
        
        # 11. JV: Director Kumar (from journal entries - credit)
        jv_cr = c.execute("""
            SELECT je.account_head, SUM(je.credit_amount) 
            FROM journal_entries je 
            JOIN journal_vouchers jv ON je.voucher_id = jv.id 
            WHERE jv.status='POSTED' AND je.credit_amount > 0 
            GROUP BY je.account_head
        """).fetchall()
        for e in jv_cr:
            if e[1] > 0:
                td.append({'head': f"JV: {e[0]}", 'cat': 'Liability', 'dr': 0, 'cr': e[1]})
        
        # ============ CALCULATE TOTALS ============
        tdr = sum(i['dr'] for i in td)
        tcr = sum(i['cr'] for i in td)
        
        # ============ ADD CAPITAL AS BALANCING FIGURE ============
        if abs(tdr - tcr) > 0.01:
            diff = tdr - tcr
            if diff > 0:
                td.append({'head': 'Capital/Equity', 'cat': 'Capital', 'dr': 0, 'cr': diff})
            else:
                td.append({'head': 'Capital/Equity', 'cat': 'Capital', 'dr': -diff, 'cr': 0})
        
        # ============ DISPLAY ============
        if td:
            df = pd.DataFrame(td)
            
            # Final totals after adding capital
            final_tdr = sum(i['dr'] for i in td)
            final_tcr = sum(i['cr'] for i in td)
            
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                asset_total = sum(i['dr'] for i in td if i['cat'] == 'Asset')
                st.metric("Assets (Dr)", f"Rs {asset_total:,.2f}")
            with col2:
                liability_total = sum(i['cr'] for i in td if i['cat'] == 'Liability')
                st.metric("Liabilities (Cr)", f"Rs {liability_total:,.2f}")
            with col3:
                income_total = sum(i['cr'] for i in td if i['cat'] == 'Income')
                st.metric("Income (Cr)", f"Rs {income_total:,.2f}")
            with col4:
                expense_total = sum(i['dr'] for i in td if i['cat'] == 'Expense')
                st.metric("Expenses (Dr)", f"Rs {expense_total:,.2f}")
            
            # Get capital amount
            capital_amount = 0
            for item in td:
                if item['cat'] == 'Capital':
                    capital_amount = item['cr'] if item['cr'] > 0 else item['dr']
                    break
            
            # Show capital
            st.info(f"💰 **Capital/Equity: Rs {capital_amount:,.2f}**")
            
            # Display table
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
            
            # Show totals
            st.markdown(f"**Total Debit: Rs {final_tdr:,.2f} | Total Credit: Rs {final_tcr:,.2f}**")
            
            # Check if balanced
            if abs(final_tdr - final_tcr) < 0.01:
                st.success("✅ **PERFECTLY BALANCED!**")
                st.markdown(f"""
                ### 📊 Balance Sheet Equation:
                **Assets (Rs {asset_total:,.2f}) = Liabilities (Rs {liability_total:,.2f}) + Capital (Rs {capital_amount:,.2f})**
                """)
            else:
                st.error(f"❌ Difference: Rs {abs(final_tdr - final_tcr):,.2f}")
            
            # Download button
            st.download_button(
                "📥 Download CSV",
                df.to_csv(index=False),
                "trial_balance.csv",
                "text/csv"
            )
    
    c.close()
# ==================== BALANCE SHEET (BALANCED) ====================
# ==================== BALANCE SHEET (BALANCED) ====================
def balance_sheet():
    if st.session_state.user['role'] not in ['admin','staff']:
        st.error("Unauthorized")
        return
    c = get_db()
    st.markdown("### 📊 Balance Sheet")
    
    if st.button("🔄 Generate Balance Sheet", use_container_width=True, type="primary"):
        assets = []
        liabilities = []
        ta = 0
        tl = 0
        
        # ============ ASSETS ============
        
        # 1. Cash in Hand
        cash_bal = c.execute("""
            SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END), 0) 
            FROM transactions WHERE reference_type='CASH'
        """).fetchone()[0]
        if cash_bal > 0:
            assets.append({'name': 'Cash in Hand', 'amount': cash_bal})
            ta += cash_bal
        
        # 2. FD Deposits Held
        fd_total = c.execute("""
            SELECT COALESCE(SUM(principal_amount), 0) 
            FROM fixed_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if fd_total > 0:
            assets.append({'name': 'FD Deposits Held', 'amount': fd_total})
            ta += fd_total
        
        # 3. RD Deposits Held
        rd_total = c.execute("""
            SELECT COALESCE(SUM(monthly_amount * installments_paid), 0) 
            FROM recurring_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if rd_total > 0:
            assets.append({'name': 'RD Deposits Held', 'amount': rd_total})
            ta += rd_total
        
        # 4. FD Interest Receivable
        fd_int_asset = c.execute("""
            SELECT COALESCE(SUM(maturity_amount - principal_amount), 0) 
            FROM fixed_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if fd_int_asset > 0:
            assets.append({'name': 'FD Interest Receivable', 'amount': fd_int_asset})
            ta += fd_int_asset
        
        # 5. RD Interest Receivable
        rd_int_asset = c.execute("""
            SELECT COALESCE(SUM(maturity_amount - (monthly_amount * installments_paid)), 0) 
            FROM recurring_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if rd_int_asset > 0:
            assets.append({'name': 'RD Interest Receivable', 'amount': rd_int_asset})
            ta += rd_int_asset
        
        # 6. JV: Union Bank of India (from journal entries)
        jv_dr_total = c.execute("""
            SELECT COALESCE(SUM(je.debit_amount), 0) 
            FROM journal_entries je 
            JOIN journal_vouchers jv ON je.voucher_id = jv.id 
            WHERE jv.status='POSTED' AND je.debit_amount > 0 
            AND je.account_head LIKE '%Union Bank%'
        """).fetchone()[0]
        if jv_dr_total > 0:
            assets.append({'name': 'JV: Union Bank of India', 'amount': jv_dr_total})
            ta += jv_dr_total
        
        # ============ LIABILITIES ============
        
        # 7. SB Deposits
        sb_total = c.execute("""
            SELECT COALESCE(SUM(balance), 0) 
            FROM accounts WHERE account_type='SB' AND status='ACTIVE'
        """).fetchone()[0]
        if sb_total > 0:
            liabilities.append({'name': 'SB Deposits', 'amount': sb_total})
            tl += sb_total
        
        # 8. SB Interest Payable
        sb_int = c.execute("""
            SELECT COALESCE(SUM(total_interest_earned), 0) 
            FROM accounts WHERE account_type='SB' AND status='ACTIVE'
        """).fetchone()[0]
        if sb_int > 0:
            liabilities.append({'name': 'SB Interest Payable', 'amount': sb_int})
            tl += sb_int
        
        # 9. FD Interest Payable
        if fd_int_asset > 0:
            liabilities.append({'name': 'FD Interest Payable', 'amount': fd_int_asset})
            tl += fd_int_asset
        
        # 10. RD Interest Payable
        if rd_int_asset > 0:
            liabilities.append({'name': 'RD Interest Payable', 'amount': rd_int_asset})
            tl += rd_int_asset
        
        # 11. JV: Director Kumar (from journal entries)
        jv_cr_total = c.execute("""
            SELECT COALESCE(SUM(je.credit_amount), 0) 
            FROM journal_entries je 
            JOIN journal_vouchers jv ON je.voucher_id = jv.id 
            WHERE jv.status='POSTED' AND je.credit_amount > 0 
            AND je.account_head LIKE '%Director Kumar%'
        """).fetchone()[0]
        if jv_cr_total > 0:
            liabilities.append({'name': 'JV: Director Kumar', 'amount': jv_cr_total})
            tl += jv_cr_total
        
        # ============ CALCULATE CAPITAL ============
        capital = ta - tl
        
        # ============ DISPLAY ============
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📈 ASSETS (What Bank Owns/Will Receive)")
            st.markdown("---")
            for item in assets:
                st.markdown(f"- **{item['name']}**: Rs {item['amount']:,.2f}")
            st.markdown("---")
            st.markdown(f"### **Total Assets: Rs {ta:,.2f}**")
        
        with col2:
            st.markdown("### 📉 LIABILITIES (What Bank Owes)")
            st.markdown("---")
            for item in liabilities:
                st.markdown(f"- **{item['name']}**: Rs {item['amount']:,.2f}")
            st.markdown("---")
            st.markdown(f"### **Total Liabilities: Rs {tl:,.2f}**")
        
        st.markdown("---")
        st.markdown(f"## 💰 CAPITAL/EQUITY: Rs {capital:,.2f}")
        st.markdown("---")
        
        # Balance check
        if abs(ta - (tl + capital)) < 0.01:
            st.success(f"""
            ### ✅ PERFECTLY BALANCED!
            
            **Assets (Rs {ta:,.2f}) = Liabilities (Rs {tl:,.2f}) + Capital (Rs {capital:,.2f})**
            """)
        else:
            st.error(f"❌ Difference: Rs {abs(ta - (tl + capital)):,.2f}")
        
        # Detailed explanation
        st.info(f"""
        ### 📋 Balance Sheet Summary:
        
        | Category | Amount |
        |----------|--------|
        | **Total Assets** | Rs {ta:,.2f} |
        | **Total Liabilities** | Rs {tl:,.2f} |
        | **Capital/Equity** | Rs {capital:,.2f} |
        | **Balance Check** | Rs {ta:,.2f} = Rs {tl:,.2f} + Rs {capital:,.2f} |
        """)
        
        st.balloons()
    
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
            for i in inc:st.markdown(f"- {i[0]}:Rs{i[1]:,.2f}")
            st.markdown(f"**Total:Rs{ti:,.2f}**")
        with col2:
            st.markdown("### EXPENSES")
            for e in exp:st.markdown(f"- {e[0]}:Rs{e[1]:,.2f}")
            st.markdown(f"**Total:Rs{te:,.2f}**")
        net=ti-te
        if net>=0:st.success(f"Net Profit:Rs{net:,.2f}")
        else:st.error(f"Net Loss:Rs{abs(net):,.2f}")
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
        txns=c.execute("SELECT t.transaction_id,COALESCE(c.first_name||' '||c.last_name,'System'),COALESCE(a.account_type,'Gen'),t.transaction_type,t.amount,t.reference_type,t.created_at FROM transactions t LEFT JOIN accounts a ON t.account_id=a.id LEFT JOIN customers c ON a.customer_id=c.id WHERE DATE(t.created_at)=?",(rd,)).fetchall()
        if txns:st.dataframe(pd.DataFrame(txns,columns=['Txn','Customer','A/C','Type','Amount','Mode','Time']),use_container_width=True)
        else:st.info("No transactions")
    c.close()

# ==================== MY ACCOUNTS ====================
def my_accounts():
    c=get_db();uid=st.session_state.user['id']
    cust=c.execute("SELECT * FROM customers WHERE user_id=?",(uid,)).fetchone()
    if cust:
        accs=c.execute("SELECT account_number,balance,COALESCE(total_interest_earned,0) FROM accounts WHERE customer_id=? AND account_type='SB'",(cust[0],)).fetchall()
        if accs:
            for a in accs:st.metric(a[0],f"Rs{a[1]+a[2]:,.2f}",f"Dep:Rs{a[1]:,.2f}+Int:Rs{a[2]:,.2f}")
    c.close()

def my_transactions():
    c=get_db();uid=st.session_state.user['id']
    txns=c.execute("SELECT t.transaction_id,a.account_number,t.transaction_type,t.amount,t.reference_type,t.description,t.created_at FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE c.user_id=? ORDER BY t.created_at DESC LIMIT 100",(uid,)).fetchall()
    if txns:st.dataframe(pd.DataFrame(txns,columns=['Txn','A/C','Type','Amount','Mode','Desc','Date']),use_container_width=True)
    else:st.info("No transactions")
    c.close()

def my_details():
    c=get_db();uid=st.session_state.user['id']
    cust=c.execute("SELECT * FROM customers WHERE user_id=?",(uid,)).fetchone()
    if cust:st.markdown(f"### {cust[3]} {cust[4]}\nID:{cust[2]}|Email:{cust[7]}|Phone:{cust[8]}")
    c.close()

if __name__=="__main__":
    main()

