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
    c.execute('''CREATE TABLE IF NOT EXISTS interest_calculations (id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER NOT NULL, calculation_date DATE NOT NULL, principal_amount DECIMAL(15,2) NOT NULL, interest_rate DECIMAL(5,2) NOT NULL, interest_earned DECIMAL(15,2) NOT NULL, days_calculated INTEGER NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (account_id) REFERENCES accounts (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, expense_id TEXT UNIQUE NOT NULL, expense_type TEXT NOT NULL, amount DECIMAL(15,2) NOT NULL, description TEXT, date DATE NOT NULL, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (created_by) REFERENCES users (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS income (id INTEGER PRIMARY KEY AUTOINCREMENT, income_id TEXT UNIQUE NOT NULL, income_type TEXT NOT NULL, amount DECIMAL(15,2) NOT NULL, description TEXT, date DATE NOT NULL, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (created_by) REFERENCES users (id))''')
    conn.commit(); conn.close()

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

def calculate_and_post_sb_interest(uid=1,cfd=None,ctd=None):
    c=get_db()
    try:
        accs=c.execute("SELECT id,account_number,balance,interest_rate,COALESCE(total_interest_earned,0),last_interest_calculation,customer_id,created_at FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchall()
        if not accs: return "No active SB accounts",[]
        if not ctd: ctd=date.today()
        if not cfd: cfd=ctd.replace(day=1)
        posted=[]
        for a in accs:
            aid,an,bal,rate,ei,lc,cid=a[0],a[1],a[2],a[3] or 3.5,a[4],a[5],a[6]
            afd=cfd
            if a[7]:
                try:
                    acd=datetime.strptime(str(a[7])[:10],'%Y-%m-%d').date()
                    if acd>afd: afd=acd
                except: pass
            if lc:
                try:
                    lcd=datetime.strptime(str(lc)[:10],'%Y-%m-%d').date()
                    if lcd>=afd: afd=lcd+timedelta(days=1)
                except: pass
            days=(ctd-afd).days+1
            if days<=0: continue
            mb=get_minimum_balance(c,aid,afd,ctd)
            if mb<=0: mb=bal
            interest=calculate_sb_interest(mb,rate,days)
            if interest>0:
                nb=bal+interest; nti=ei+interest
                c.execute("UPDATE accounts SET balance=?,total_interest_earned=?,last_interest_calculation=? WHERE id=?",(nb,nti,ctd,aid))
                c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,'SB Interest','INTEREST','RECEIPT',?,?)",(generate_id('TXN'),aid,interest,nb,generate_voucher_number('RECEIPT'),uid))
                c.execute("INSERT INTO interest_calculations (account_id,calculation_date,principal_amount,interest_rate,interest_earned,days_calculated) VALUES (?,?,?,?,?,?)",(aid,ctd,mb,rate,interest,days))
                jvn=generate_voucher_number('JOURNAL')
                c.execute("INSERT INTO journal_vouchers (voucher_number,voucher_date,description,total_amount,status,created_by) VALUES (?,?,?,?,'POSTED',?)",(jvn,ctd,f"SB Interest - A/C {an}",interest,uid))
                jid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                c.execute("INSERT INTO journal_entries (voucher_id,account_head,debit_amount,credit_amount,description) VALUES (?,'Interest Paid on SB',?,0,?)",(jid,interest,f"{days}d @ {rate}%"))
                c.execute("INSERT INTO journal_entries (voucher_id,account_head,debit_amount,credit_amount,description) VALUES (?,'SB Account - '||?,0,?,?)",(jid,an,interest,f"Interest credited"))
                posted.append({'account_number':an,'min_balance':mb,'balance_before':bal,'interest':interest,'new_balance':nb,'rate':rate,'days':days,'from_date':afd,'to_date':ctd,'journal_voucher':jvn,'total_interest_earned':nti,'maturity_value':nb})
        c.commit(); return "SUCCESS",posted
    except Exception as e: c.rollback(); return f"Error: {e}",[]
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

# ==================== MINIMAL CSS ====================
def load_minimal_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    *{font-family:'Inter',sans-serif}
    
    /* Header */
    .topbar{background:#111827;color:white;padding:0.7rem 2rem;display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem}
    .topbar h1{margin:0;font-size:1.3rem;font-weight:700;letter-spacing:-0.3px}
    .topbar .user{font-size:0.85rem;opacity:0.9}
    
    /* Cards */
    .dash-card{background:white;border:1px solid #e5e7eb;border-radius:12px;padding:1.3rem 1rem;text-align:center;transition:all 0.2s}
    .dash-card:hover{box-shadow:0 4px 12px rgba(0,0,0,0.08);border-color:#d1d5db}
    .dash-card .icon{font-size:2rem;margin-bottom:0.3rem}
    .dash-card h2{font-size:1.8rem;margin:0.3rem 0;font-weight:700;color:#111827}
    .dash-card p{margin:0;font-size:0.8rem;color:#6b7280;font-weight:500;text-transform:uppercase;letter-spacing:0.5px}
    
    .section-card{background:white;border:1px solid #e5e7eb;border-radius:12px;padding:1.5rem;margin-bottom:1rem}
    .section-card h3{font-size:1.05rem;font-weight:700;color:#111827;margin-bottom:1rem;padding-bottom:0.7rem;border-bottom:2px solid #f3f4f6}
    
    /* Buttons */
    .stButton>button{width:100%;border-radius:8px;font-weight:600;transition:all 0.2s;border:none;padding:0.6rem 1rem;font-size:0.9rem;background:#111827;color:white}
    .stButton>button:hover{background:#1f2937;transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,0.15)}
    
    /* Inputs */
    .stTextInput>div>div>input,.stNumberInput>div>div>input,.stTextArea>div>div>textarea,.stSelectbox>div>div>div,.stDateInput>div>div>input{border-radius:8px!important;border:1.5px solid #d1d5db!important;padding:0.55rem 0.7rem!important;font-size:0.9rem!important;background:white!important;color:#111827!important}
    .stTextInput>div>div>input:focus,.stNumberInput>div>div>input:focus,.stTextArea>div>div>textarea:focus,.stSelectbox>div>div>div:focus,.stDateInput>div>div>input:focus{border-color:#111827!important;box-shadow:0 0 0 3px rgba(0,0,0,0.05)!important}
    
    /* Tables */
    .stDataFrame{border-radius:10px!important;overflow:hidden!important;border:1px solid #e5e7eb!important}
    .stDataFrame thead th{background:#111827!important;color:white!important;font-weight:600!important;padding:0.6rem 0.8rem!important;font-size:0.75rem!important;text-transform:uppercase;letter-spacing:0.5px}
    .stDataFrame tbody td{padding:0.5rem 0.8rem!important;font-size:0.85rem!important;color:#374151!important;border-bottom:1px solid #f3f4f6!important}
    .stDataFrame tbody tr:nth-child(even){background:#f9fafb!important}
    .stDataFrame tbody tr:hover{background:#f3f4f6!important}
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"]{gap:2px;background:#f9fafb;padding:4px;border-radius:10px;border:1px solid #e5e7eb}
    .stTabs [data-baseweb="tab"]{border-radius:8px;padding:0.4rem 1rem;font-weight:500;font-size:0.85rem;color:#6b7280}
    .stTabs [data-baseweb="tab"]:hover{background:#e5e7eb;color:#111827}
    .stTabs [aria-selected="true"]{background:#111827!important;color:white!important}
    
    /* Expanders */
    .streamlit-expanderHeader{border-radius:8px!important;font-weight:600!important;padding:0.6rem 0.9rem!important;background:#f9fafb!important;border:1.5px solid #e5e7eb!important;color:#111827!important;font-size:0.9rem!important}
    .streamlit-expanderHeader:hover{border-color:#111827!important}
    
    /* Sidebar */
    [data-testid="stSidebar"]{background:#111827!important;border-right:none!important}
    [data-testid="stSidebar"] *{color:white!important}
    [data-testid="stSidebar"] .stButton>button{background:rgba(255,255,255,0.08)!important;border:1px solid rgba(255,255,255,0.12)!important;color:white!important;text-align:left;padding:0.5rem 0.7rem;font-weight:500;font-size:0.83rem;border-radius:6px}
    [data-testid="stSidebar"] .stButton>button:hover{background:rgba(255,255,255,0.18)!important;border-color:rgba(255,255,255,0.25)!important;transform:translateX(3px)}
    
    /* Metrics */
    [data-testid="stMetricValue"]{font-weight:700!important;color:#111827!important;font-size:1.4rem!important}
    [data-testid="stMetricLabel"]{color:#6b7280!important;font-size:0.8rem!important}
    
    /* Login */
    .login-box{max-width:380px;margin:3rem auto;padding:2rem;background:white;border:1px solid #e5e7eb;border-radius:16px;box-shadow:0 4px 20px rgba(0,0,0,0.06)}
    
    /* Alerts */
    .alert{padding:0.9rem 1.1rem;border-radius:10px;margin:0.7rem 0;font-weight:500;font-size:0.9rem}
    .alert-info{background:#eff6ff;border-left:4px solid #3b82f6;color:#1e40af}
    .alert-success{background:#f0fdf4;border-left:4px solid #22c55e;color:#166534}
    .alert-warning{background:#fffbeb;border-left:4px solid #f59e0b;color:#92400e}
    
    @media(max-width:768px){.dash-card h2{font-size:1.3rem}}
    </style>""",unsafe_allow_html=True)

# ==================== MAIN APP ====================
def main():
    st.set_page_config(page_title="Banking System",page_icon="🏦",layout="wide",initial_sidebar_state="expanded")
    init_database(); create_default_admin(); init_session_state(); load_minimal_css()
    if st.session_state.user is None: show_login()
    else: show_app()

def show_login():
    st.markdown('<div class="login-box">',unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;margin-bottom:1.2rem"><h1 style="font-size:2.5rem;margin:0">🏦</h1><h2 style="margin:0.3rem 0;font-weight:700;color:#111827">Banking System</h2><p style="color:#6b7280;font-size:0.85rem">Enterprise Platform</p></div>',unsafe_allow_html=True)
    u=st.text_input("Username",key="lu"); p=st.text_input("Password",type="password",key="lp")
    if st.button("Sign In",use_container_width=True,key="bl"):
        user=login_user(u,p)
        if user: st.session_state.user={'id':user[0],'username':user[1],'role':user[3]}; st.rerun()
        else: st.error("Invalid credentials")
    st.caption("Demo: admin / admin123")
    st.markdown('</div>',unsafe_allow_html=True)

def show_app():
    # Top Bar
    st.markdown(f'<div class="topbar"><h1>🏦 Banking System</h1><div class="user">👤 {st.session_state.user["username"]} <span style="opacity:0.6">({st.session_state.user["role"]})</span></div></div>',unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown('<div style="text-align:center;padding:0.5rem 0"><h3 style="margin:0;font-weight:600;font-size:1rem">Navigation</h3></div>',unsafe_allow_html=True)
        st.divider()
        menu={'dashboard':'📊 Dashboard','customer_management':'👥 Customers','kyc_verification':'🔍 KYC','create_sb_account':'🏦 New SB','sb_accounts':'💰 SB Accounts','fixed_deposits':'💎 FD','recurring_deposits':'🔄 RD','transactions':'💳 Transactions','journal_vouchers':'📝 JV','income_expenses':'📈 Income/Exp','interest_calculation':'📊 Interest','trial_balance':'⚖️ Trial Balance','balance_sheet':'📊 Balance Sheet','profit_loss':'💵 P&L','reports':'📋 Reports'} if st.session_state.user['role'] in ['admin','staff'] else {'dashboard':'📊 Dashboard','my_accounts':'💰 My Accounts','my_transactions':'💳 Transactions','my_details':'👤 Profile'}
        for k,v in menu.items():
            if st.sidebar.button(v,key=f"m_{k}",use_container_width=True): st.session_state.page=k; st.rerun()
        st.divider()
        if st.sidebar.button("🚪 Sign Out",use_container_width=True,key="so"): st.session_state.user=None; st.rerun()
    
    page=st.session_state.get('page','dashboard')
    if page=='dashboard': dashboard()
    elif page=='customer_management': customer_mgmt()
    elif page=='kyc_verification': kyc_verify()
    elif page=='create_sb_account': create_sb()
    elif page in('sb_accounts','my_accounts'): sb_accounts()
    elif page=='fixed_deposits': fixed_deposits()
    elif page=='recurring_deposits': recurring_deposits()
    elif page in('transactions','my_transactions'): transactions()
    elif page=='journal_vouchers': journal_vouchers()
    elif page=='income_expenses': income_expenses()
    elif page=='interest_calculation': interest_calc()
    elif page=='trial_balance': trial_balance()
    elif page=='balance_sheet': balance_sheet()
    elif page=='profit_loss': profit_loss()
    elif page=='reports': reports()
    elif page=='my_details': my_details()

def dashboard():
    c=get_db()
    cust=c.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    sb=c.execute("SELECT COUNT(*) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    bal=c.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    intt=c.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    kyc=c.execute("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'").fetchone()[0]
    
    cols=st.columns(4)
    with cols[0]: st.markdown(f'<div class="dash-card"><span class="icon">👥</span><h2>{cust}</h2><p>Customers</p></div>',unsafe_allow_html=True)
    with cols[1]: st.markdown(f'<div class="dash-card"><span class="icon">💰</span><h2>{sb}</h2><p>Active SB</p></div>',unsafe_allow_html=True)
    with cols[2]: st.markdown(f'<div class="dash-card"><span class="icon">🏦</span><h2>₹{bal+intt:,.0f}</h2><p>SB Maturity</p></div>',unsafe_allow_html=True)
    with cols[3]: st.markdown(f'<div class="dash-card"><span class="icon">🔍</span><h2>{kyc}</h2><p>Pending KYC</p></div>',unsafe_allow_html=True)
    
    x1,x2=st.columns(2)
    with x1:
        st.markdown('<div class="section-card"><h3>📋 Recent Transactions</h3>',unsafe_allow_html=True)
        txns=c.execute("SELECT t.transaction_id,c.first_name||' '||c.last_name,t.transaction_type,t.amount,t.created_at FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id ORDER BY t.created_at DESC LIMIT 8").fetchall()
        if txns: st.dataframe(pd.DataFrame(txns,columns=['ID','Customer','Type','Amount','Date']).style.format({'Amount':'₹{:,.2f}'}),use_container_width=True,height=260)
        else: st.info("No transactions")
        st.markdown('</div>',unsafe_allow_html=True)
    with x2:
        st.markdown('<div class="section-card"><h3>📊 Accounts</h3>',unsafe_allow_html=True)
        accs=c.execute("SELECT account_type,COUNT(*) FROM accounts WHERE status='ACTIVE' GROUP BY account_type").fetchall()
        if accs:
            df=pd.DataFrame(accs,columns=['Type','Count'])
            fig=px.pie(df,values='Count',names='Type',hole=0.5,color_discrete_sequence=['#111827','#374151','#6b7280'])
            fig.update_layout(height=260,margin=dict(t=0,b=0,l=0,r=0))
            st.plotly_chart(fig,use_container_width=True)
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def customer_mgmt():
    t1,t2=st.tabs(["Register","View"])
    with t1:
        st.markdown('<div class="section-card"><h3>New Customer</h3>',unsafe_allow_html=True)
        with st.form("cr"):
            c1,c2=st.columns(2)
            with c1: fn=st.text_input("First Name*"); ln=st.text_input("Last Name*"); dob=st.date_input("DOB*",min_value=date(1900,1,1)); email=st.text_input("Email*"); phone=st.text_input("Phone*")
            with c2: pan=st.text_input("PAN*"); aadhar=st.text_input("Aadhar*"); addr=st.text_area("Address"); city=st.text_input("City"); state=st.text_input("State"); pin=st.text_input("PIN")
            col1,col2=st.columns(2)
            with col1: pan_doc=st.file_uploader("PAN Card*",type=['jpg','jpeg','png','pdf'],key="pu")
            with col2: aadhar_doc=st.file_uploader("Aadhar*",type=['jpg','jpeg','png','pdf'],key="au")
            if st.form_submit_button("Register",use_container_width=True):
                if not all([fn,ln,email,phone,pan,aadhar]): st.error("Fill all fields")
                elif not pan_doc or not aadhar_doc: st.error("Upload docs")
                else:
                    try:
                        conn=get_db(); cid=generate_id('CUST')
                        conn.execute("INSERT INTO customers (customer_id,first_name,last_name,date_of_birth,email,phone,address,city,state,pincode,pan_number,aadhar_number,pan_document,aadhar_document) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(cid,fn,ln,dob,email,phone,addr,city,state,pin,pan,aadhar,pan_doc.read(),aadhar_doc.read()))
                        conn.commit(); conn.close(); st.success(f"✅ Registered! {cid}"); st.balloons()
                    except Exception as e: st.error(str(e))
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="section-card"><h3>Customers</h3>',unsafe_allow_html=True)
        conn=get_db(); custs=conn.execute("SELECT customer_id,first_name,last_name,email,phone,city,kyc_status FROM customers ORDER BY customer_id DESC").fetchall()
        if custs: st.dataframe(pd.DataFrame(custs,columns=['ID','First','Last','Email','Phone','City','KYC']),use_container_width=True,height=400)
        else: st.info("No customers")
        conn.close(); st.markdown('</div>',unsafe_allow_html=True)

def kyc_verify():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c=get_db()
    pending=c.execute("SELECT * FROM customers WHERE kyc_status='PENDING' ORDER BY created_at").fetchall()
    if not pending: st.markdown('<div class="alert alert-success">✅ All verified!</div>',unsafe_allow_html=True)
    else:
        for cust in pending:
            with st.expander(f"📄 {cust[3]} {cust[4]} - {cust[2]}",expanded=True):
                st.write(f"**{cust[3]} {cust[4]}** | {cust[7]} | {cust[8]} | PAN:{cust[12]}")
                b1,b2=st.columns(2)
                with b1:
                    if st.button("✅ Approve",key=f"a_{cust[0]}",use_container_width=True,type="primary"):
                        c.execute("UPDATE customers SET kyc_status='VERIFIED',kyc_verified_by=?,kyc_verified_at=CURRENT_TIMESTAMP WHERE id=?",(st.session_state.user['id'],cust[0]))
                        if not c.execute("SELECT id FROM accounts WHERE customer_id=? AND account_type='SB' AND status='ACTIVE'",(cust[0],)).fetchone():
                            c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate,last_interest_calculation,total_interest_earned) VALUES (?,?,'SB',0.00,3.50,DATE('now'),0.00)",(generate_account_number('SB'),cust[0]))
                        c.commit(); st.success("✅ Approved!"); st.rerun()
                with b2:
                    if st.button("❌ Reject",key=f"r_{cust[0]}",use_container_width=True):
                        c.execute("UPDATE customers SET kyc_status='REJECTED' WHERE id=?",(cust[0],)); c.commit(); st.rerun()
    c.close()

def create_sb():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c=get_db()
    custs=c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c WHERE c.kyc_status='VERIFIED' AND NOT EXISTS (SELECT 1 FROM accounts a WHERE a.customer_id=c.id AND a.account_type='SB' AND a.status='ACTIVE')").fetchall()
    if not custs: st.markdown('<div class="alert alert-success">✅ All have SB!</div>',unsafe_allow_html=True); return
    st.markdown('<div class="section-card"><h3>Open SB Account</h3>',unsafe_allow_html=True)
    sel=st.selectbox("Customer",[f"{x[1]} - {x[2]}" for x in custs])
    if sel:
        idx=[f"{x[1]} - {x[2]}" for x in custs].index(sel); cust=custs[idx]
        with st.form("sb"):
            c1,c2=st.columns(2)
            with c1: rate=st.number_input("Rate (%)",0.0,10.0,3.5,0.25)
            with c2: bal=st.number_input("Opening Bal",0.0,step=100.0)
            if st.form_submit_button("Create",use_container_width=True):
                an=generate_account_number('SB'); c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate,last_interest_calculation,total_interest_earned) VALUES (?,?,'SB',?,?,DATE('now'),0.00)",(an,cust[0],bal,rate))
                c.commit(); st.success(f"✅ {an}"); st.balloons()
    st.markdown('</div>',unsafe_allow_html=True); c.close()

def sb_accounts():
    c=get_db(); t1,t2,t3,t4=st.tabs(["List","Transact","Statement","Maturity"])
    role=st.session_state.user['role']
    uid=st.session_state.user['id']
    
    with t1:
        st.markdown('<div class="section-card"><h3>SB Accounts</h3>',unsafe_allow_html=True)
        q="SELECT a.account_number,c.first_name||' '||c.last_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND " + ("c.user_id=?" if role=='customer' else "c.kyc_status='VERIFIED'")
        accs=c.execute(q,(uid,) if role=='customer' else ()).fetchall()
        if accs:
            data=[{'Account':a[0],'Customer':a[1],'Principal':a[2],'Rate':f"{a[3]:.2f}%",'Interest':a[4],'Maturity':a[2]+a[4]} for a in accs]
            st.dataframe(pd.DataFrame(data).style.format({'Principal':'₹{:,.2f}','Interest':'₹{:,.2f}','Maturity':'₹{:,.2f}'}),use_container_width=True,height=350)
        else: st.info("No accounts")
        st.markdown('</div>',unsafe_allow_html=True)
    
    with t2:
        st.markdown('<div class="section-card"><h3>Deposit / Withdraw</h3>',unsafe_allow_html=True)
        q2="SELECT a.id,a.account_number,c.first_name||' '||c.last_name,a.balance,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND " + ("c.user_id=?" if role=='customer' else "1=1")
        accs=c.execute(q2,(uid,) if role=='customer' else ()).fetchall()
        if accs:
            sel=st.selectbox("Account",[f"{a[1]} - {a[2]} (Maturity: ₹{a[3]+a[4]:,.2f})" for a in accs])
            if sel:
                idx=[f"{a[1]} - {a[2]} (Maturity: ₹{a[3]+a[4]:,.2f})" for a in accs].index(sel); acc=accs[idx]
                tt=st.radio("Type",["Deposit","Withdraw"],horizontal=True)
                with st.form("tx"):
                    amt=st.number_input("Amount",min_value=0.01,step=100.0); desc=st.text_input("Desc"); mode=st.selectbox("Mode",["CASH","TRANSFER","CHEQUE"])
                    if st.form_submit_button("Process",use_container_width=True):
                        at="DEPOSIT" if tt=="Deposit" else "WITHDRAWAL"
                        if at=="WITHDRAWAL" and amt>acc[3]: st.error("Insufficient!")
                        else:
                            nb=acc[3]+amt if at=="DEPOSIT" else acc[3]-amt; tdb="CREDIT" if at=="DEPOSIT" else "DEBIT"; vt="RECEIPT" if at=="DEPOSIT" else "PAYMENT"
                            c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,?,?,?,?,?,?,?,?)",(generate_id('TXN'),acc[0],tdb,amt,nb,desc,mode,vt,generate_voucher_number(vt),uid))
                            c.execute("UPDATE accounts SET balance=? WHERE id=?",(nb,acc[0])); c.commit()
                            st.success(f"✅ Done! Maturity: ₹{nb+acc[4]:,.2f}"); st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)
    
    with t3:
        st.markdown('<div class="section-card"><h3>Statement</h3>',unsafe_allow_html=True)
        q3="SELECT a.id,a.account_number,c.first_name||' '||c.last_name FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND " + ("c.user_id=?" if role=='customer' else "1=1")
        accs=c.execute(q3,(uid,) if role=='customer' else ()).fetchall()
        if accs:
            sel=st.selectbox("Account",[f"{a[1]} - {a[2]}" for a in accs],key="ss")
            if sel:
                aid=[a[0] for a in accs if f"{a[1]} - {a[2]}"==sel][0]
                d1,d2=st.columns(2)
                with d1: fd=st.date_input("From",date.today()-timedelta(days=30),key="sf")
                with d2: td=st.date_input("To",date.today(),key="st")
                txns=c.execute("SELECT transaction_id,created_at,transaction_type,amount,balance_after,description,voucher_number FROM transactions WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ? ORDER BY created_at DESC",(aid,fd,td)).fetchall()
                if txns: st.dataframe(pd.DataFrame(txns,columns=['ID','Date','Type','Amount','Balance','Desc','Voucher']).style.format({'Amount':'₹{:,.2f}','Balance':'₹{:,.2f}'}),use_container_width=True,height=350)
        st.markdown('</div>',unsafe_allow_html=True)
    
    with t4:
        st.markdown('<div class="section-card"><h3>Maturity</h3>',unsafe_allow_html=True)
        q4="SELECT a.account_number,c.first_name||' '||c.last_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND " + ("c.user_id=?" if role=='customer' else "1=1")
        accs=c.execute(q4,(uid,) if role=='customer' else ()).fetchall()
        if accs:
            data=[{'Account':a[0],'Customer':a[1],'Principal':a[2],'Rate':f"{a[3]:.2f}%",'Interest':a[4],'Maturity':a[2]+a[4]} for a in accs]
            st.dataframe(pd.DataFrame(data).style.format({'Principal':'₹{:,.2f}','Interest':'₹{:,.2f}','Maturity':'₹{:,.2f}'}),use_container_width=True)
            m1,m2,m3=st.columns(3)
            with m1: st.metric("Principal",f"₹{sum(d['Principal'] for d in data):,.2f}")
            with m2: st.metric("Interest",f"₹{sum(d['Interest'] for d in data):,.2f}")
            with m3: st.metric("Maturity",f"₹{sum(d['Maturity'] for d in data):,.2f}")
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def interest_calc():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c=get_db(); t1,t2,t3=st.tabs(["Calculate","History","Impact"])
    with t1:
        st.markdown('<div class="section-card"><h3>Calculate Interest</h3>',unsafe_allow_html=True)
        d1,d2=st.columns(2)
        with d1: cfd=st.date_input("From",date.today().replace(day=1),key="if")
        with d2: ctd=st.date_input("To",date.today(),key="it")
        if cfd>ctd: st.error("Invalid range")
        else: st.info(f"{cfd.strftime('%d-%b-%Y')} → {ctd.strftime('%d-%b-%Y')} ({(ctd-cfd).days+1}d)")
        accs=c.execute("SELECT a.id,a.account_number,c.first_name||' '||c.last_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        if accs:
            b1,b2=st.columns(2)
            with b1:
                if st.button("Calculate & Post",use_container_width=True,type="primary",key="cp"):
                    if cfd>ctd: st.error("Invalid!")
                    else:
                        s,r=calculate_and_post_sb_interest(uid,cfd,ctd)
                        if s=="SUCCESS" and len(r)>0: st.success(f"✅ Posted! ₹{sum(x['interest'] for x in r):,.2f}"); st.balloons()
                        else: st.info(s if s!="SUCCESS" else "No interest")
            with b2:
                if st.button("Preview",use_container_width=True,key="pv"):
                    pv=[]
                    for a in accs:
                        mb=get_minimum_balance(c,a[0],cfd,ctd)
                        if mb<=0: mb=a[3]
                        days=(ctd-cfd).days+1
                        if days>0: pv.append({'Account':a[1],'Min Bal':mb,'Interest':calculate_sb_interest(mb,a[4] or 3.5,days),'New Maturity':a[3]+a[5]+calculate_sb_interest(mb,a[4] or 3.5,days)})
                    if pv: st.dataframe(pd.DataFrame(pv).style.format({'Min Bal':'₹{:,.2f}','Interest':'₹{:,.2f}','New Maturity':'₹{:,.2f}'}),use_container_width=True)
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="section-card"><h3>History</h3>',unsafe_allow_html=True)
        h=c.execute("SELECT ic.calculation_date,a.account_number,c.first_name||' '||c.last_name,ic.principal_amount,ic.interest_rate,ic.interest_earned,ic.days_calculated FROM interest_calculations ic JOIN accounts a ON ic.account_id=a.id JOIN customers c ON a.customer_id=c.id ORDER BY ic.calculation_date DESC LIMIT 50").fetchall()
        if h: st.dataframe(pd.DataFrame(h,columns=['Date','Account','Customer','Principal','Rate','Interest','Days']).style.format({'Principal':'₹{:,.2f}','Interest':'₹{:,.2f}'}),use_container_width=True,height=350)
        else: st.info("No history")
        st.markdown('</div>',unsafe_allow_html=True)
    with t3:
        st.markdown('<div class="section-card"><h3>JV Impact</h3>',unsafe_allow_html=True)
        jvs=c.execute("SELECT jv.voucher_number,jv.voucher_date,jv.description,jv.total_amount,je.account_head,je.debit_amount,je.credit_amount FROM journal_vouchers jv JOIN journal_entries je ON jv.id=je.voucher_id WHERE (je.account_head='Interest Paid on SB' OR je.account_head LIKE '%SB Account%') AND jv.status='POSTED' ORDER BY jv.voucher_date DESC LIMIT 50").fetchall()
        if jvs:
            jd={}
            for j in jvs:
                if j[0] not in jd: jd[j[0]]={'date':j[1],'desc':j[2],'amt':j[3],'entries':[]}
                jd[j[0]]['entries'].append({'head':j[4],'debit':j[5],'credit':j[6]})
            for vn,d in jd.items():
                with st.expander(f"📄 {vn} - {d['date']} - ₹{d['amt']:,.2f}"):
                    for e in d['entries']: st.write(f"{e['head']}: Dr ₹{e['debit']:,.2f} | Cr ₹{e['credit']:,.2f}")
            st.success(f"✅ TB Impact: ₹{sum(d['amt'] for d in jd.values()):,.2f}")
        else: st.info("No JVs")
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def trial_balance():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c=get_db()
    st.markdown('<div class="section-card"><h3>Trial Balance</h3>',unsafe_allow_html=True)
    if st.button("Generate",use_container_width=True,type="primary",key="tb"):
        td=[]
        cash=c.execute("SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END),0) FROM transactions WHERE reference_type='CASH'").fetchone()[0]
        if abs(cash)>0: td.append({'head':'Cash','cat':'Asset','dr':max(cash,0),'cr':max(-cash,0)})
        sb=c.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb>0: td.append({'head':'SB Deposits','cat':'Liability','dr':0,'cr':sb})
        jvl=c.execute("SELECT je.account_head,SUM(je.credit_amount),SUM(je.debit_amount) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE jv.status='POSTED' AND (je.account_head LIKE '%SB Account%' OR je.account_head LIKE '%Payable%') GROUP BY je.account_head").fetchall()
        for e in jvl:
            if e[1]>e[2]: td.append({'head':e[0],'cat':'Liability','dr':e[2] or 0,'cr':e[1] or 0})
        fd=c.execute("SELECT COALESCE(SUM(principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        if fd>0: td.append({'head':'Fixed Deposits','cat':'Liability','dr':0,'cr':fd})
        rd=c.execute("SELECT COALESCE(SUM(monthly_amount*installments_paid),0) FROM recurring_deposits WHERE status='ACTIVE'").fetchone()[0]
        if rd>0: td.append({'head':'Recurring Deposits','cat':'Liability','dr':0,'cr':rd})
        for it in ['Interest Earned','Fees & Charges','Commission Income','Other Income']:
            amt=c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type=?",(it,)).fetchone()[0]
            if amt>0: td.append({'head':it,'cat':'Income','dr':0,'cr':amt})
        jve=c.execute("SELECT je.account_head,SUM(je.debit_amount),SUM(je.credit_amount) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE jv.status='POSTED' AND je.account_head NOT LIKE '%SB Account%' GROUP BY je.account_head").fetchall()
        for e in jve:
            if e[1]>0: td.append({'head':e[0],'cat':'Expense','dr':e[1],'cr':0})
            if e[2]>0: td.append({'head':e[0],'cat':'Income','dr':0,'cr':e[2]})
        for et in ['Salary & Wages','Rent & Utilities','Operating Expenses','Administrative Expenses','Other Expenses']:
            amt=c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type=?",(et,)).fetchone()[0]
            if amt>0: td.append({'head':et,'cat':'Expense','dr':amt,'cr':0})
        tdr=sum(i['dr'] for i in td); tcr=sum(i['cr'] for i in td); diff=tcr-tdr
        if abs(diff)>0.01: td.append({'head':'Capital','cat':'Capital','dr':max(-diff,0),'cr':max(diff,0)})
        if td:
            df=pd.DataFrame(td)
            m1,m2,m3,m4=st.columns(4)
            with m1: st.metric("Assets",f"₹{sum(i['dr'] for i in td if i['cat']=='Asset'):,.2f}")
            with m2: st.metric("Liabilities",f"₹{sum(i['cr'] for i in td if i['cat']=='Liability'):,.2f}")
            with m3: st.metric("Income",f"₹{sum(i['cr'] for i in td if i['cat']=='Income'):,.2f}")
            with m4: st.metric("Expenses",f"₹{sum(i['dr'] for i in td if i['cat']=='Expense'):,.2f}")
            st.divider()
            for cat in ['Asset','Liability','Income','Expense','Capital']:
                cd=[i for i in td if i['cat']==cat]
                if cd:
                    st.markdown(f"**{cat}s**")
                    st.dataframe(pd.DataFrame(cd)[['head','dr','cr']].rename(columns={'head':'Head','dr':'Debit','cr':'Credit'}).style.format({'Debit':'₹{:,.2f}','Credit':'₹{:,.2f}'}),use_container_width=True,height=min(250,len(cd)*40))
            dft=df['dr'].sum(); cft=df['cr'].sum()
            st.divider()
            n1,n2,n3=st.columns(3)
            with n1: st.metric("Total Debit",f"₹{dft:,.2f}")
            with n2: st.metric("Total Credit",f"₹{cft:,.2f}")
            with n3:
                if abs(dft-cft)<0.01: st.success("✅ BALANCED!")
                else: st.error(f"Diff: ₹{abs(dft-cft):,.2f}")
            st.download_button("📥 CSV",df.to_csv(index=False),"tb.csv","text/csv",key="dtb")
        else: st.info("No data")
    st.markdown('</div>',unsafe_allow_html=True); c.close()

def balance_sheet():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c=get_db()
    st.markdown('<div class="section-card"><h3>Balance Sheet</h3>',unsafe_allow_html=True)
    if st.button("Generate",use_container_width=True,type="primary",key="bs"):
        cash=c.execute("SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END),0) FROM transactions WHERE reference_type='CASH'").fetchone()[0]
        sb_bal=c.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        sb_int=c.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb_int==0: sb_int=c.execute("SELECT COALESCE(SUM(credit_amount),0) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE je.account_head LIKE '%SB Account%' AND jv.status='POSTED'").fetchone()[0]
        fd=c.execute("SELECT COALESCE(SUM(principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        rd=c.execute("SELECT COALESCE(SUM(monthly_amount*installments_paid),0) FROM recurring_deposits WHERE status='ACTIVE'").fetchone()[0]
        fd_int=c.execute("SELECT COALESCE(SUM(maturity_amount-principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        ta=cash+sb_bal+fd+rd; tl=sb_int+fd_int+fd+rd+sb_bal; cap=ta-tl
        p1,p2=st.columns(2)
        with p1:
            st.markdown(f"""<div class="section-card"><h3>ASSETS</h3><p>💰 Cash: <b>₹{cash:,.2f}</b></p><p>🏦 SB: <b>₹{sb_bal:,.2f}</b></p><p>💎 FD: <b>₹{fd:,.2f}</b></p><p>🔄 RD: <b>₹{rd:,.2f}</b></p><hr><p><b>Total: ₹{ta:,.2f}</b></p></div>""",unsafe_allow_html=True)
        with p2:
            st.markdown(f"""<div class="section-card"><h3>LIABILITIES</h3><p>📈 SB Int: <b>₹{sb_int:,.2f}</b></p><p>📈 FD Int: <b>₹{fd_int:,.2f}</b></p><p>🏦 SB: <b>₹{sb_bal:,.2f}</b></p><p>💎 FD: <b>₹{fd:,.2f}</b></p><p>🔄 RD: <b>₹{rd:,.2f}</b></p><hr><p><b>Total: ₹{tl:,.2f}</b></p></div>""",unsafe_allow_html=True)
        st.markdown(f"""<div class="section-card"><h3>CAPITAL</h3><p><b>Capital: ₹{cap:,.2f}</b></p></div>""",unsafe_allow_html=True)
        if abs(ta-(tl+cap))<0.01: st.success(f"✅ Balanced!")
    st.markdown('</div>',unsafe_allow_html=True); c.close()

def profit_loss():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c=get_db()
    st.markdown('<div class="section-card"><h3>P&L</h3>',unsafe_allow_html=True)
    d1,d2=st.columns(2)
    with d1: fd=st.date_input("From",date.today().replace(month=1,day=1),key="plf")
    with d2: td=st.date_input("To",date.today(),key="plt")
    if st.button("Generate",use_container_width=True,type="primary",key="pl"):
        inc=[('Interest',c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Interest Earned' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),('Fees',c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Fees & Charges' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),('Commission',c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Commission Income' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),('Other',c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Other Income' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0])]
        exp=[('SB Interest',c.execute("SELECT COALESCE(SUM(debit_amount),0) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE je.account_head='Interest Paid on SB' AND jv.status='POSTED' AND DATE(jv.voucher_date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),('Salary',c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Salary & Wages' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),('Rent',c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Rent & Utilities' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),('Operating',c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Operating Expenses' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),('Admin',c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Administrative Expenses' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),('Other',c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Other Expenses' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0])]
        ti=sum(i[1] for i in inc); te=sum(e[1] for e in exp); net=ti-te
        q1,q2=st.columns(2)
        with q1:
            st.markdown('<div class="section-card"><h3>INCOME</h3>',unsafe_allow_html=True)
            for item,amt in inc: st.write(f"• {item}: ₹{amt:,.2f}")
            st.markdown(f'<hr><b>Total: ₹{ti:,.2f}</b></div>',unsafe_allow_html=True)
        with q2:
            st.markdown('<div class="section-card"><h3>EXPENSES</h3>',unsafe_allow_html=True)
            for item,amt in exp:
                if amt>0: st.write(f"• {item}: ₹{amt:,.2f}")
            st.markdown(f'<hr><b>Total: ₹{te:,.2f}</b></div>',unsafe_allow_html=True)
        if net>=0: st.success(f"## Net Profit: ₹{net:,.2f}")
        else: st.error(f"## Net Loss: ₹{abs(net):,.2f}")
    st.markdown('</div>',unsafe_allow_html=True); c.close()

def income_expenses():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c=get_db(); t1,t2=st.tabs(["Income","Expense"])
    with t1:
        st.markdown('<div class="section-card"><h3>Record Income</h3>',unsafe_allow_html=True)
        with st.form("if"):
            d1,d2=st.columns(2)
            with d1: it=st.selectbox("Type",["Interest Earned","Fees & Charges","Commission Income","Other Income"]); amt=st.number_input("Amount",min_value=1.0,step=100.0)
            with d2: dt=st.date_input("Date",date.today(),key="id"); desc=st.text_area("Desc")
            if st.form_submit_button("Record",use_container_width=True):
                c.execute("INSERT INTO income (income_id,income_type,amount,description,date,created_by) VALUES (?,?,?,?,?,?)",(generate_id('INC'),it,amt,desc,dt,uid)); c.commit(); st.success(f"✅ ₹{amt:,.2f}")
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="section-card"><h3>Record Expense</h3>',unsafe_allow_html=True)
        with st.form("ef"):
            d1,d2=st.columns(2)
            with d1: et=st.selectbox("Type",["Salary & Wages","Rent & Utilities","Operating Expenses","Administrative Expenses","Other Expenses"]); amt=st.number_input("Amount",min_value=1.0,step=100.0)
            with d2: dt=st.date_input("Date",date.today(),key="ed"); desc=st.text_area("Desc")
            if st.form_submit_button("Record",use_container_width=True):
                c.execute("INSERT INTO expenses (expense_id,expense_type,amount,description,date,created_by) VALUES (?,?,?,?,?,?)",(generate_id('EXP'),et,amt,desc,dt,uid)); c.commit(); st.success(f"✅ ₹{amt:,.2f}")
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def fixed_deposits():
    c=get_db(); t1,t2,t3=st.tabs(["Open","Active","Maturity"])
    with t1:
        st.markdown('<div class="section-card"><h3>Open FD</h3>',unsafe_allow_html=True)
        custs=c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND c.kyc_status='VERIFIED' AND a.status='ACTIVE'").fetchall()
        if custs:
            sel=st.selectbox("Customer",[f"{x[1]} - {x[2]}" for x in custs])
            if sel:
                idx=[f"{x[1]} - {x[2]}" for x in custs].index(sel); cust=custs[idx]
                with st.form("fd"):
                    d1,d2=st.columns(2)
                    with d1: p=st.number_input("Principal",min_value=1000.0,step=1000.0,value=10000.0); t=st.selectbox("Tenure",[3,6,12,24,36,60]); r=st.number_input("Rate",3.0,10.0,6.5,0.25)
                    with d2: sd=st.date_input("Start",date.today(),key="fs"); nom=st.text_input("Nominee")
                    md=sd+timedelta(days=t*30); ma=calculate_fd_maturity(p,r,t)
                    st.info(f"Maturity: {md.strftime('%d-%m-%Y')} | Amount: ₹{ma:,.2f}")
                    if st.form_submit_button("Open",use_container_width=True):
                        fdn=generate_id('FD'); an=generate_account_number('FD')
                        c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate) VALUES (?,?,'FD',0.00,?)",(an,cust[0],r))
                        aid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                        c.execute("INSERT INTO fixed_deposits (fd_number,account_id,principal_amount,interest_rate,start_date,maturity_date,maturity_amount,tenure_months,nominee_name) VALUES (?,?,?,?,?,?,?,?,?)",(fdn,aid,p,r,sd,md,ma,t,nom))
                        c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,'FD','FD_DEPOSIT','RECEIPT',?,?)",(generate_id('TXN'),aid,p,p,generate_voucher_number('RECEIPT'),uid))
                        c.commit(); st.success(f"✅ {fdn}"); st.balloons()
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="section-card"><h3>Active FDs</h3>',unsafe_allow_html=True)
        fds=c.execute("SELECT fd.fd_number,c.first_name||' '||c.last_name,fd.principal_amount,fd.interest_rate,fd.start_date,fd.maturity_date,fd.maturity_amount FROM fixed_deposits fd JOIN accounts a ON fd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE fd.status='ACTIVE' ORDER BY fd.maturity_date").fetchall()
        if fds: st.dataframe(pd.DataFrame(fds,columns=['FD','Customer','Principal','Rate','Start','Maturity','Maturity Amt']).style.format({'Principal':'₹{:,.2f}','Maturity Amt':'₹{:,.2f}'}),use_container_width=True)
        else: st.info("No active FDs")
        st.markdown('</div>',unsafe_allow_html=True)
    with t3:
        st.markdown('<div class="section-card"><h3>Maturity Alerts</h3>',unsafe_allow_html=True)
        today=date.today(); mat=c.execute("SELECT fd.fd_number,c.first_name||' '||c.last_name,fd.maturity_amount,fd.maturity_date FROM fixed_deposits fd JOIN accounts a ON fd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE fd.maturity_date BETWEEN ? AND ? AND fd.status='ACTIVE'",(today,today+timedelta(days=30))).fetchall()
        if mat: st.warning(f"🔔 {len(mat)} maturing soon"); st.dataframe(pd.DataFrame(mat,columns=['FD','Customer','Amount','Date']).style.format({'Amount':'₹{:,.2f}'}),use_container_width=True)
        else: st.success("✅ None")
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def recurring_deposits():
    c=get_db(); t1,t2,t3=st.tabs(["Open","Active","Pay"])
    with t1:
        st.markdown('<div class="section-card"><h3>Open RD</h3>',unsafe_allow_html=True)
        custs=c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND c.kyc_status='VERIFIED' AND a.status='ACTIVE'").fetchall()
        if custs:
            sel=st.selectbox("Customer",[f"{x[1]} - {x[2]}" for x in custs])
            if sel:
                idx=[f"{x[1]} - {x[2]}" for x in custs].index(sel); cust=custs[idx]
                with st.form("rd"):
                    d1,d2=st.columns(2)
                    with d1: m=st.number_input("Monthly",min_value=100.0,step=100.0,value=1000.0); t=st.selectbox("Tenure",[6,12,24,36,48,60]); r=st.number_input("Rate",3.0,10.0,6.0,0.25)
                    with d2: sd=st.date_input("Start",date.today(),key="rs"); nom=st.text_input("Nominee")
                    md=sd+timedelta(days=t*30); ma=calculate_rd_maturity(m,r,t)
                    st.info(f"Maturity: {md.strftime('%d-%m-%Y')} | Amount: ₹{ma:,.2f}")
                    if st.form_submit_button("Open",use_container_width=True):
                        rdn=generate_id('RD'); an=generate_account_number('RD')
                        c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate) VALUES (?,?,'RD',0.00,?)",(an,cust[0],r))
                        aid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                        c.execute("INSERT INTO recurring_deposits (rd_number,account_id,monthly_amount,interest_rate,start_date,maturity_date,maturity_amount,tenure_months,total_installments,nominee_name) VALUES (?,?,?,?,?,?,?,?,?,?)",(rdn,aid,m,r,sd,md,ma,t,t,nom))
                        c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,'RD Install 1','RD_INSTALLMENT','RECEIPT',?,?)",(generate_id('TXN'),aid,m,m,generate_voucher_number('RECEIPT'),uid))
                        c.execute("UPDATE recurring_deposits SET installments_paid=1 WHERE rd_number=?",(rdn,)); c.commit(); st.success(f"✅ {rdn}"); st.balloons()
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="section-card"><h3>Active RDs</h3>',unsafe_allow_html=True)
        rds=c.execute("SELECT rd.rd_number,c.first_name||' '||c.last_name,rd.monthly_amount,rd.interest_rate,rd.start_date,rd.maturity_date,rd.maturity_amount,rd.installments_paid,rd.total_installments FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE rd.status='ACTIVE' ORDER BY rd.maturity_date").fetchall()
        if rds:
            df=pd.DataFrame(rds,columns=['RD','Customer','Monthly','Rate','Start','Maturity','Maturity Amt','Paid','Total'])
            df['Progress']=df.apply(lambda r:f"{r['Paid']}/{r['Total']}",axis=1)
            st.dataframe(df.style.format({'Monthly':'₹{:,.2f}','Maturity Amt':'₹{:,.2f}'}),use_container_width=True)
        st.markdown('</div>',unsafe_allow_html=True)
    with t3:
        st.markdown('<div class="section-card"><h3>Pay Installment</h3>',unsafe_allow_html=True)
        rds=c.execute("SELECT rd.id,rd.rd_number,c.first_name||' '||c.last_name,rd.monthly_amount,rd.installments_paid,rd.total_installments,a.id FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE rd.status='ACTIVE' AND rd.installments_paid<rd.total_installments").fetchall()
        if rds:
            sel=st.selectbox("RD",[f"{r[1]} - {r[2]} ({r[4]}/{r[5]})" for r in rds])
            if sel:
                idx=[f"{r[1]} - {r[2]} ({r[4]}/{r[5]})" for r in rds].index(sel); rd=rds[idx]
                with st.form("pr"):
                    amt=st.number_input("Amount",value=float(rd[3]),min_value=float(rd[3]))
                    if st.form_submit_button("Pay",use_container_width=True):
                        c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,?,'RD_INSTALLMENT','RECEIPT',?,?)",(generate_id('TXN'),rd[6],amt,amt,f"RD {rd[4]+1}/{rd[5]}",generate_voucher_number('RECEIPT'),uid))
                        np=rd[4]+1; c.execute("UPDATE recurring_deposits SET installments_paid=? WHERE id=?",(np,rd[0]))
                        if np>=rd[5]: c.execute("UPDATE recurring_deposits SET status='MATURED' WHERE id=?",(rd[0],))
                        c.commit(); st.success(f"✅ {np}/{rd[5]}"); st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def transactions():
    c=get_db()
    st.markdown('<div class="section-card"><h3>Transactions</h3>',unsafe_allow_html=True)
    d1,d2,d3,d4=st.columns(4)
    with d1: at=st.selectbox("Account",["All","SB","FD","RD"])
    with d2: tt=st.selectbox("Type",["All","CREDIT","DEBIT"])
    with d3: fd=st.date_input("From",date.today()-timedelta(days=30),key="tf")
    with d4: td=st.date_input("To",date.today(),key="tt")
    q="SELECT t.transaction_id,c.first_name||' '||c.last_name,a.account_number,a.account_type,t.transaction_type,t.amount,t.balance_after,t.description,t.voucher_number,t.created_at FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE DATE(t.created_at) BETWEEN ? AND ?"
    params=[fd,td]
    if st.session_state.user['role']=='customer': q+=" AND c.user_id=?"; params.append(uid)
    if at!="All": q+=" AND a.account_type=?"; params.append(at)
    if tt!="All": q+=" AND t.transaction_type=?"; params.append(tt)
    q+=" ORDER BY t.created_at DESC LIMIT 200"
    txns=c.execute(q,params).fetchall()
    if txns: st.dataframe(pd.DataFrame(txns,columns=['ID','Customer','Account','Type','Action','Amount','Balance','Desc','Voucher','Date']).style.format({'Amount':'₹{:,.2f}','Balance':'₹{:,.2f}'}),use_container_width=True,height=400)
    else: st.info("No transactions")
    st.markdown('</div>',unsafe_allow_html=True); c.close()

def journal_vouchers():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c=get_db(); t1,t2=st.tabs(["Create","List"])
    with t1:
        st.markdown('<div class="section-card"><h3>Create JV</h3>',unsafe_allow_html=True)
        with st.form("jv"):
            vd=st.date_input("Date",date.today(),key="jvd"); desc=st.text_area("Desc")
            n=st.number_input("Entries",2,10,2); entries=[]; td_v=0; tc_v=0
            for i in range(int(n)):
                st.markdown(f"**Entry {i+1}**")
                e1,e2,e3=st.columns(3)
                with e1: h=st.text_input(f"Head",key=f"jh{i}")
                with e2: d=st.number_input(f"Debit",min_value=0.0,step=100.0,key=f"jd{i}")
                with e3: c=st.number_input(f"Credit",min_value=0.0,step=100.0,key=f"jc{i}")
                td_v+=d; tc_v+=c; entries.append({'h':h,'d':d,'c':c})
            st.write(f"Dr: ₹{td_v:,.2f} | Cr: ₹{tc_v:,.2f}")
            if abs(td_v-tc_v)>0.01: st.error(f"Diff: ₹{abs(td_v-tc_v):,.2f}")
            if st.form_submit_button("Create",use_container_width=True):
                if abs(td_v-tc_v)>0.01: st.error("Must balance!")
                else:
                    vn=generate_voucher_number('JOURNAL')
                    c.execute("INSERT INTO journal_vouchers (voucher_number,voucher_date,description,total_amount,created_by) VALUES (?,?,?,?,?)",(vn,vd,desc,td_v,uid))
                    vid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                    for e in entries:
                        if e['d']>0 or e['c']>0: c.execute("INSERT INTO journal_entries (voucher_id,account_head,debit_amount,credit_amount) VALUES (?,?,?,?)",(vid,e['h'],e['d'],e['c']))
                    c.commit(); st.success(f"✅ {vn}"); st.balloons()
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="section-card"><h3>JV List</h3>',unsafe_allow_html=True)
        vouchers=c.execute("SELECT jv.voucher_number,jv.voucher_date,jv.description,jv.total_amount,jv.status FROM journal_vouchers jv ORDER BY jv.created_at DESC").fetchall()
        if vouchers:
            for v in vouchers:
                sc={'DRAFT':'🟡','POSTED':'🟢','CANCELLED':'🔴'}
                with st.expander(f"{sc.get(v[4],'⚪')} {v[0]} - {v[1]} - ₹{v[3]:,.2f} ({v[4]})"):
                    st.write(f"**{v[2]}**")
                    entries=c.execute("SELECT account_head,debit_amount,credit_amount FROM journal_entries WHERE voucher_id=(SELECT id FROM journal_vouchers WHERE voucher_number=?)",(v[0],)).fetchall()
                    if entries: st.dataframe(pd.DataFrame(entries,columns=['Head','Debit','Credit']).style.format({'Debit':'₹{:,.2f}','Credit':'₹{:,.2f}'}),use_container_width=True)
                    if v[4]=='DRAFT':
                        st.divider(); f1,f2=st.columns(2)
                        with f1:
                            if st.button("✅ Post",key=f"po_{v[0]}",use_container_width=True,type="primary"):
                                c.execute("UPDATE journal_vouchers SET status='POSTED',posted_by=?,posted_at=CURRENT_TIMESTAMP WHERE voucher_number=?",(uid,v[0])); c.commit(); st.success("Posted!"); st.rerun()
                        with f2:
                            if st.button("❌ Cancel",key=f"ca_{v[0]}",use_container_width=True):
                                c.execute("UPDATE journal_vouchers SET status='CANCELLED' WHERE voucher_number=?",(v[0],)); c.commit(); st.warning("Cancelled!"); st.rerun()
        else: st.info("No vouchers")
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def reports():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    rt=st.selectbox("Report",["Customer List","Interest Report","Daily Transactions"])
    c=get_db()
    st.markdown('<div class="section-card"><h3>Report</h3>',unsafe_allow_html=True)
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

def my_details():
    c=get_db()
    cust=c.execute("SELECT * FROM customers WHERE user_id=?",(uid,)).fetchone()
    if cust:
        st.markdown(f"""<div style="background:#111827;color:white;padding:1.2rem;border-radius:12px;margin-bottom:1rem"><h2>{cust[3]} {cust[4]}</h2><p>📋 {cust[2]} | 📧 {cust[7]} | 📱 {cust[8]}</p></div>""",unsafe_allow_html=True)
        st.markdown('<div class="section-card"><h3>My SB Accounts</h3>',unsafe_allow_html=True)
        accs=c.execute("SELECT account_number,balance,COALESCE(total_interest_earned,0) FROM accounts WHERE customer_id=? AND account_type='SB'",(cust[0],)).fetchall()
        if accs:
            for a in accs:
                mv=a[1]+a[2]
                st.markdown(f"""<div style="background:#f9fafb;padding:0.7rem;border-radius:8px;margin:0.3rem 0;border-left:3px solid #111827"><b>{a[0]}</b> | Principal: ₹{a[1]:,.2f} | Interest: ₹{a[2]:,.2f} | <b>Maturity: ₹{mv:,.2f}</b></div>""",unsafe_allow_html=True)
        else: st.info("No accounts")
        st.markdown('</div>',unsafe_allow_html=True)
    else: st.warning("No profile")
    c.close()

if __name__=="__main__":
    uid=1
    main()
