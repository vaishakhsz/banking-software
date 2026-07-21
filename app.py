# 🏦 COMPLETE BANKING SYSTEM - Enterprise Edition
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
from decimal import Decimal
import uuid, os, io, hashlib, base64
from PIL import Image
import plotly.express as px
import plotly.graph_objects as go

try:
    from fpdf import FPDF
except ImportError:
    try:
        from fpdf2 import FPDF
    except ImportError:
        FPDF = None

# ==================== DATABASE ====================
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

# ==================== UTILS ====================
def get_db(): return sqlite3.connect('banking_system.db')
def gid(p): return f"{p}{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4]}"
def gan(t): return f"{'100' if t=='SB' else '200' if t=='FD' else '300'}{datetime.now().strftime('%y%m%d')}{str(uuid.uuid4().int)[:6]}"
def gvn(v): return f"{'PMT' if v=='PAYMENT' else 'RCT' if v=='RECEIPT' else 'JNL'}{datetime.now().strftime('%Y%m%d%H%M')}{str(uuid.uuid4().int)[:4]}"
def fd_mat(p,r,m): return round(p*(1+r/400)**(m/3),2)
def rd_mat(m,r,mo): return round(m*(((1+r/400)**(mo/3)-1)/(1-(1+r/400)**(-1/3))),2)
def sb_int(b,r,d): return 0 if b<=0 else round((b*r*d)/(100*365),2)
def min_bal(c,aid,fd,td):
    try:
        sb=c.execute("SELECT balance_after FROM transactions WHERE account_id=? AND DATE(created_at)<? ORDER BY created_at DESC LIMIT 1",(aid,fd)).fetchone()
        sb=sb[0] if sb else (c.execute("SELECT balance FROM accounts WHERE id=?",(aid,)).fetchone() or [0])[0]
        tx=c.execute("SELECT balance_after FROM transactions WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ? ORDER BY created_at",(aid,fd,td)).fetchall()
        return min([sb]+[t[0] for t in tx]) if tx else sb
    except: return (c.execute("SELECT balance FROM accounts WHERE id=?",(aid,)).fetchone() or [0])[0]

def calc_post_interest(uid=1,cfd=None,ctd=None):
    c=get_db()
    try:
        accs=c.execute("SELECT id,account_number,balance,interest_rate,COALESCE(total_interest_earned,0),last_interest_calculation,customer_id,created_at FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchall()
        if not accs: return "No accounts",[]
        if not ctd: ctd=date.today()
        if not cfd: cfd=ctd.replace(day=1)
        posted=[]
        for a in accs:
            aid,an,bal,rate,ei,lc,cid=a[0],a[1],a[2],a[3] or 3.5,a[4],a[5],a[6]; afd=cfd
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
            mb=min_bal(c,aid,afd,ctd)
            if mb<=0: mb=bal
            interest=sb_int(mb,rate,days)
            if interest>0:
                nb=bal+interest; nti=ei+interest
                c.execute("UPDATE accounts SET balance=?,total_interest_earned=?,last_interest_calculation=? WHERE id=?",(nb,nti,ctd,aid))
                c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,'Interest','INTEREST','RECEIPT',?,?)",(gid('TXN'),aid,interest,nb,gvn('RECEIPT'),uid))
                c.execute("INSERT INTO interest_calculations (account_id,calculation_date,principal_amount,interest_rate,interest_earned,days_calculated) VALUES (?,?,?,?,?,?)",(aid,ctd,mb,rate,interest,days))
                jvn=gvn('JOURNAL'); c.execute("INSERT INTO journal_vouchers (voucher_number,voucher_date,description,total_amount,status,created_by) VALUES (?,?,?,?,'POSTED',?)",(jvn,ctd,f"SB Interest - {an}",interest,uid))
                jid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                c.execute("INSERT INTO journal_entries (voucher_id,account_head,debit_amount,credit_amount,description) VALUES (?,'Interest Paid on SB',?,0,?)",(jid,interest,f"{days}d@{rate}%"))
                c.execute("INSERT INTO journal_entries (voucher_id,account_head,debit_amount,credit_amount,description) VALUES (?,'SB Account - '||?,0,?,?)",(jid,an,interest,"Interest credited"))
                posted.append({'acc':an,'mb':mb,'bal':bal,'int':interest,'nb':nb,'rate':rate,'days':days,'jv':jvn,'nti':nti,'mv':nb})
        c.commit(); return "OK",posted
    except Exception as e: c.rollback(); return str(e),[]
    finally: c.close()

def hpw(p): return hashlib.sha256(p.encode()).hexdigest()
def login(u,p):
    c=get_db(); cur=c.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=? AND is_active=1",(u,hpw(p))); usr=cur.fetchone(); c.close(); return usr
def make_admin():
    c=get_db()
    if c.execute("SELECT COUNT(*) FROM users WHERE username='admin'").fetchone()[0]==0:
        c.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",('admin',hpw('admin123'),'admin')); c.commit()
    c.close()

class BP(FPDF):
    def header(self): self.set_font('Arial','B',16); self.cell(0,10,'BANKING SYSTEM',0,1,'C'); self.set_font('Arial','',10); self.cell(0,5,'Reports',0,1,'C'); self.line(10,self.get_y(),200,self.get_y()); self.ln(5)
    def footer(self): self.set_y(-15); self.set_font('Arial','I',8); self.cell(0,10,f'Page {self.page_no()}/{{nb}}',0,0,'C')

def gen_pdf(rt,data,fn):
    if FPDF is None: return None
    pdf=BP(); pdf.alias_nb_pages(); pdf.add_page()
    if rt=='tb':
        pdf.set_font('Arial','B',14); pdf.cell(0,10,'TRIAL BALANCE',0,1,'C'); pdf.set_font('Arial','',10); pdf.cell(0,5,f'As on: {data["date"]}',0,1,'C'); pdf.ln(10)
        pdf.set_font('Arial','B',10); pdf.cell(10,7,'#',1); pdf.cell(90,7,'Account Head',1); pdf.cell(45,7,'Debit',1,0,'R'); pdf.cell(45,7,'Credit',1,1,'R')
        pdf.set_font('Arial','',9); td=0; tc=0
        for i,e in enumerate(data['entries'],1): pdf.cell(10,6,str(i),1); pdf.cell(90,6,e['head'],1); pdf.cell(45,6,f"{e['dr']:,.2f}",1,0,'R'); pdf.cell(45,6,f"{e['cr']:,.2f}",1,1,'R'); td+=e['dr']; tc+=e['cr']
        pdf.set_font('Arial','B',10); pdf.cell(100,7,'TOTAL',1); pdf.cell(45,7,f"{td:,.2f}",1,0,'R'); pdf.cell(45,7,f"{tc:,.2f}",1,1,'R')
    pdf.output(fn); return fn

def iss():
    if 'user' not in st.session_state: st.session_state.user=None
    if 'page' not in st.session_state: st.session_state.page='dashboard'

# ==================== FRESH DESIGN CSS ====================
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
    *{font-family:'Space Grotesk',sans-serif}
    
    :root{--bg:#fafafa;--card:#ffffff;--text:#1a1a2e;--sub:#6b7280;--border:#e5e7eb;--accent:#6366f1;--accent2:#ec4899;--green:#10b981;--amber:#f59e0b}
    
    .stApp{background:var(--bg)}
    
    /* Top Bar */
    .topbar{background:var(--card);border-bottom:1px solid var(--border);padding:0.6rem 1.5rem;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:50}
    .topbar h1{font-size:1.1rem;font-weight:700;color:var(--text);margin:0;letter-spacing:-0.5px}
    .topbar .pill{background:var(--bg);padding:0.3rem 0.8rem;border-radius:20px;font-size:0.8rem;font-weight:500;color:var(--text);border:1px solid var(--border)}
    
    /* Stat Cards */
    .stat-row{display:flex;gap:0.8rem;margin-bottom:1.2rem}
    .stat-card{flex:1;background:var(--card);border:1px solid var(--border);border-radius:20px;padding:1.2rem;display:flex;align-items:center;gap:1rem;transition:all 0.2s}
    .stat-card:hover{border-color:var(--accent);box-shadow:0 0 0 4px rgba(99,102,241,0.06)}
    .stat-icon{width:48px;height:48px;border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:1.4rem}
    .stat-icon.purple{background:#eef2ff;color:#6366f1}
    .stat-icon.pink{background:#fdf2f8;color:#ec4899}
    .stat-icon.green{background:#ecfdf5;color:#10b981}
    .stat-icon.amber{background:#fffbeb;color:#f59e0b}
    .stat-info h3{font-size:1.6rem;font-weight:700;color:var(--text);margin:0;line-height:1}
    .stat-info p{margin:0.2rem 0 0;font-size:0.78rem;color:var(--sub);font-weight:500}
    
    /* Panel */
    .panel{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:1.5rem;margin-bottom:1rem}
    .panel h3{font-size:1rem;font-weight:700;color:var(--text);margin-bottom:1rem;display:flex;align-items:center;gap:0.5rem}
    
    /* Buttons */
    .stButton>button{width:100%;border-radius:12px;font-weight:600;border:none;padding:0.55rem 1rem;font-size:0.88rem;transition:all 0.2s;cursor:pointer}
    .stButton>button[kind="primary"]{background:var(--text);color:white}
    .stButton>button[kind="primary"]:hover{background:#374151}
    .stButton>button:not([kind="primary"]){background:var(--bg);color:var(--text);border:1.5px solid var(--border)}
    .stButton>button:not([kind="primary"]):hover{border-color:var(--text)}
    
    /* Inputs */
    .stTextInput>div>div>input,.stNumberInput>div>div>input,.stTextArea>div>div>textarea,.stSelectbox>div>div>div,.stDateInput>div>div>input{border-radius:10px!important;border:1.5px solid var(--border)!important;padding:0.5rem 0.7rem!important;font-size:0.88rem!important;background:var(--bg)!important;color:var(--text)!important}
    .stTextInput>div>div>input:focus,.stNumberInput>div>div>input:focus,.stTextArea>div>div>textarea:focus,.stSelectbox>div>div>div:focus,.stDateInput>div>div>input:focus{border-color:var(--accent)!important;box-shadow:0 0 0 3px rgba(99,102,241,0.1)!important}
    
    /* Tables */
    .stDataFrame{border-radius:14px!important;overflow:hidden!important;border:1px solid var(--border)!important}
    .stDataFrame thead th{background:var(--text)!important;color:white!important;font-weight:600!important;padding:0.55rem 0.7rem!important;font-size:0.73rem!important;text-transform:uppercase;letter-spacing:0.5px}
    .stDataFrame tbody td{padding:0.5rem 0.7rem!important;font-size:0.84rem!important;color:var(--text)!important;border-bottom:1px solid var(--border)!important}
    .stDataFrame tbody tr:nth-child(even){background:#f9fafb!important}
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"]{gap:2px;background:var(--bg);padding:4px;border-radius:12px;border:1px solid var(--border)}
    .stTabs [data-baseweb="tab"]{border-radius:10px;padding:0.4rem 1rem;font-weight:500;font-size:0.83rem;color:var(--sub)}
    .stTabs [data-baseweb="tab"]:hover{background:var(--border);color:var(--text)}
    .stTabs [aria-selected="true"]{background:var(--text)!important;color:white!important}
    
    /* Expander */
    .streamlit-expanderHeader{border-radius:10px!important;font-weight:600!important;padding:0.55rem 0.8rem!important;background:var(--bg)!important;border:1.5px solid var(--border)!important;color:var(--text)!important;font-size:0.88rem!important}
    
    /* Sidebar */
    [data-testid="stSidebar"]{background:#1a1a2e!important;border-right:none!important}
    [data-testid="stSidebar"] *{color:white!important}
    [data-testid="stSidebar"] .stButton>button{background:rgba(255,255,255,0.06)!important;border:1px solid rgba(255,255,255,0.1)!important;color:white!important;text-align:left;padding:0.45rem 0.7rem;font-weight:500;font-size:0.82rem;border-radius:8px}
    [data-testid="stSidebar"] .stButton>button:hover{background:rgba(255,255,255,0.14)!important}
    
    /* Login */
    .login-wrap{max-width:400px;margin:2rem auto;background:var(--card);border:1px solid var(--border);border-radius:24px;padding:2rem}
    
    @media(max-width:768px){.stat-row{flex-wrap:wrap}.stat-card{flex:1 1 45%}}
    </style>""",unsafe_allow_html=True)

# ==================== MAIN ====================
def main():
    st.set_page_config(page_title="Banking System",page_icon="🏦",layout="wide",initial_sidebar_state="expanded")
    init_database(); make_admin(); iss(); load_css()
    if st.session_state.user is None: show_login()
    else: show_app()

def show_login():
    st.markdown('<div class="login-wrap">',unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;margin-bottom:1.2rem"><h1 style="font-size:2.5rem">🏦</h1><h2 style="font-weight:700;color:#1a1a2e;margin:0.3rem 0">Banking System</h2></div>',unsafe_allow_html=True)
    u=st.text_input("Username",key="lu"); p=st.text_input("Password",type="password",key="lp")
    if st.button("Sign In",use_container_width=True,type="primary",key="bl"):
        usr=login(u,p)
        if usr: st.session_state.user={'id':usr[0],'username':usr[1],'role':usr[3]}; st.rerun()
        else: st.error("Invalid")
    st.caption("admin / admin123")
    st.markdown('</div>',unsafe_allow_html=True)

def show_app():
    st.markdown(f'<div class="topbar"><h1>🏦 Banking System</h1><div class="pill">👤 {st.session_state.user["username"]}</div></div>',unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown('<div style="text-align:center;padding:0.5rem 0"><h3 style="margin:0;font-weight:600;font-size:0.95rem">Menu</h3></div>',unsafe_allow_html=True)
        st.divider()
        if st.session_state.user['role'] in ['admin','staff']:
            menu={'dashboard':'📊 Dashboard','customer_management':'👥 Customers','kyc_verification':'🔍 KYC','create_sb_account':'🏦 New SB','sb_accounts':'💰 SB Accounts','fixed_deposits':'💎 FD','recurring_deposits':'🔄 RD','transactions':'💳 Transactions','journal_vouchers':'📝 JV','income_expenses':'📈 Income/Exp','interest_calculation':'📊 Interest','trial_balance':'⚖️ Trial Balance','balance_sheet':'📊 Balance Sheet','profit_loss':'💵 P&L','reports':'📋 Reports'}
        else: menu={'dashboard':'📊 Dashboard','my_accounts':'💰 My Accounts','my_transactions':'💳 Transactions','my_details':'👤 Profile'}
        for k,v in menu.items():
            if st.sidebar.button(v,key=f"m_{k}",use_container_width=True): st.session_state.page=k; st.rerun()
        st.divider()
        if st.sidebar.button("🚪 Sign Out",use_container_width=True,key="so"): st.session_state.user=None; st.rerun()
    
    page=st.session_state.get('page','dashboard')
    globals()[page]()

def dashboard():
    c=get_db()
    cust=c.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    sb=c.execute("SELECT COUNT(*) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    bal=c.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    intt=c.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    kyc=c.execute("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'").fetchone()[0]
    
    st.markdown(f'''<div class="stat-row">
    <div class="stat-card"><div class="stat-icon purple">👥</div><div class="stat-info"><h3>{cust}</h3><p>Customers</p></div></div>
    <div class="stat-card"><div class="stat-icon pink">💰</div><div class="stat-info"><h3>{sb}</h3><p>Active SB</p></div></div>
    <div class="stat-card"><div class="stat-icon green">🏦</div><div class="stat-info"><h3>₹{bal+intt:,.0f}</h3><p>SB Maturity</p></div></div>
    <div class="stat-card"><div class="stat-icon amber">🔍</div><div class="stat-info"><h3>{kyc}</h3><p>Pending KYC</p></div></div>
    </div>''',unsafe_allow_html=True)
    
    x1,x2=st.columns(2)
    with x1:
        st.markdown('<div class="panel"><h3>📋 Recent</h3>',unsafe_allow_html=True)
        txns=c.execute("SELECT t.transaction_id,c.first_name||' '||c.last_name,t.transaction_type,t.amount,t.created_at FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id ORDER BY t.created_at DESC LIMIT 8").fetchall()
        if txns: st.dataframe(pd.DataFrame(txns,columns=['ID','Customer','Type','Amount','Date']).style.format({'Amount':'₹{:,.2f}'}),use_container_width=True,height=260)
        else: st.info("No transactions")
        st.markdown('</div>',unsafe_allow_html=True)
    with x2:
        st.markdown('<div class="panel"><h3>📊 Distribution</h3>',unsafe_allow_html=True)
        accs=c.execute("SELECT account_type,COUNT(*) FROM accounts WHERE status='ACTIVE' GROUP BY account_type").fetchall()
        if accs:
            df=pd.DataFrame(accs,columns=['Type','Count'])
            fig=px.pie(df,values='Count',names='Type',hole=0.55,color_discrete_sequence=['#6366f1','#ec4899','#10b981'])
            fig.update_layout(height=260,margin=dict(t=0,b=0),showlegend=False)
            fig.update_traces(textposition='inside',textinfo='percent+label')
            st.plotly_chart(fig,use_container_width=True)
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def customer_management():
    t1,t2=st.tabs(["Register","View"])
    with t1:
        st.markdown('<div class="panel"><h3>New Customer</h3>',unsafe_allow_html=True)
        with st.form("cr"):
            c1,c2=st.columns(2)
            with c1: fn=st.text_input("First*"); ln=st.text_input("Last*"); dob=st.date_input("DOB*",min_value=date(1900,1,1)); email=st.text_input("Email*"); phone=st.text_input("Phone*")
            with c2: pan=st.text_input("PAN*"); aadhar=st.text_input("Aadhar*"); addr=st.text_area("Address"); city=st.text_input("City"); stt=st.text_input("State"); pin=st.text_input("PIN")
            d1,d2=st.columns(2)
            with d1: pdoc=st.file_uploader("PAN Card*",type=['jpg','jpeg','png','pdf'],key="pu")
            with d2: adoc=st.file_uploader("Aadhar*",type=['jpg','jpeg','png','pdf'],key="au")
            if st.form_submit_button("Register",use_container_width=True,type="primary"):
                if not all([fn,ln,email,phone,pan,aadhar]): st.error("Fill all")
                elif not pdoc or not adoc: st.error("Upload docs")
                else:
                    try:
                        conn=get_db(); cid=gid('CUST')
                        conn.execute("INSERT INTO customers (customer_id,first_name,last_name,date_of_birth,email,phone,address,city,state,pincode,pan_number,aadhar_number,pan_document,aadhar_document) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(cid,fn,ln,dob,email,phone,addr,city,stt,pin,pan,aadhar,pdoc.read(),adoc.read()))
                        conn.commit(); conn.close(); st.success(f"✅ {cid}"); st.balloons()
                    except Exception as e: st.error(str(e))
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="panel"><h3>Customers</h3>',unsafe_allow_html=True)
        conn=get_db(); custs=conn.execute("SELECT customer_id,first_name,last_name,email,phone,city,kyc_status FROM customers ORDER BY customer_id DESC").fetchall()
        if custs: st.dataframe(pd.DataFrame(custs,columns=['ID','First','Last','Email','Phone','City','KYC']),use_container_width=True,height=400)
        else: st.info("None")
        conn.close(); st.markdown('</div>',unsafe_allow_html=True)

def kyc_verification():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c=get_db()
    pending=c.execute("SELECT * FROM customers WHERE kyc_status='PENDING' ORDER BY created_at").fetchall()
    if not pending: st.success("✅ All verified!")
    else:
        for cust in pending:
            with st.expander(f"📄 {cust[3]} {cust[4]} - {cust[2]}",expanded=True):
                st.write(f"**{cust[3]} {cust[4]}** | {cust[7]} | {cust[8]}")
                b1,b2=st.columns(2)
                with b1:
                    if st.button("✅ Approve",key=f"a_{cust[0]}",use_container_width=True,type="primary"):
                        c.execute("UPDATE customers SET kyc_status='VERIFIED',kyc_verified_by=?,kyc_verified_at=CURRENT_TIMESTAMP WHERE id=?",(st.session_state.user['id'],cust[0]))
                        if not c.execute("SELECT id FROM accounts WHERE customer_id=? AND account_type='SB' AND status='ACTIVE'",(cust[0],)).fetchone():
                            c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate,last_interest_calculation,total_interest_earned) VALUES (?,?,'SB',0.00,3.50,DATE('now'),0.00)",(gan('SB'),cust[0]))
                        c.commit(); st.success("Approved!"); st.rerun()
                with b2:
                    if st.button("❌ Reject",key=f"r_{cust[0]}",use_container_width=True):
                        c.execute("UPDATE customers SET kyc_status='REJECTED' WHERE id=?",(cust[0],)); c.commit(); st.rerun()
    c.close()

def create_sb_account():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c=get_db()
    custs=c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c WHERE c.kyc_status='VERIFIED' AND NOT EXISTS (SELECT 1 FROM accounts a WHERE a.customer_id=c.id AND a.account_type='SB' AND a.status='ACTIVE')").fetchall()
    if not custs: st.success("✅ All have SB!"); return
    st.markdown('<div class="panel"><h3>Open SB Account</h3>',unsafe_allow_html=True)
    sel=st.selectbox("Customer",[f"{x[1]} - {x[2]}" for x in custs])
    if sel:
        idx=[f"{x[1]} - {x[2]}" for x in custs].index(sel); cust=custs[idx]
        with st.form("sb"):
            c1,c2=st.columns(2)
            with c1: rate=st.number_input("Rate (%)",0.0,10.0,3.5,0.25)
            with c2: bal=st.number_input("Opening Bal",0.0,step=100.0)
            if st.form_submit_button("Create",use_container_width=True,type="primary"):
                an=gan('SB'); c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate,last_interest_calculation,total_interest_earned) VALUES (?,?,'SB',?,?,DATE('now'),0.00)",(an,cust[0],bal,rate))
                c.commit(); st.success(f"✅ {an}"); st.balloons()
    st.markdown('</div>',unsafe_allow_html=True); c.close()

def sb_accounts():
    c=get_db(); role=st.session_state.user['role']; uid=st.session_state.user['id']
    t1,t2,t3,t4=st.tabs(["List","Transact","Statement","Maturity"])
    with t1:
        st.markdown('<div class="panel"><h3>SB Accounts</h3>',unsafe_allow_html=True)
        q=f"SELECT a.account_number,c.first_name||' '||c.last_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND {'c.user_id=?' if role=='customer' else 'c.kyc_status=\\'VERIFIED\\''}"
        accs=c.execute(q,(uid,) if role=='customer' else ()).fetchall()
        if accs:
            data=[{'Account':a[0],'Customer':a[1],'Principal':a[2],'Rate':f"{a[3]:.2f}%",'Interest':a[4],'Maturity':a[2]+a[4]} for a in accs]
            st.dataframe(pd.DataFrame(data).style.format({'Principal':'₹{:,.2f}','Interest':'₹{:,.2f}','Maturity':'₹{:,.2f}'}),use_container_width=True,height=350)
        else: st.info("None")
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="panel"><h3>Transact</h3>',unsafe_allow_html=True)
        q2=f"SELECT a.id,a.account_number,c.first_name||' '||c.last_name,a.balance,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND {'c.user_id=?' if role=='customer' else '1=1'}"
        accs=c.execute(q2,(uid,) if role=='customer' else ()).fetchall()
        if accs:
            sel=st.selectbox("Account",[f"{a[1]} - {a[2]} (₹{a[3]+a[4]:,.2f})" for a in accs])
            if sel:
                idx=[f"{a[1]} - {a[2]} (₹{a[3]+a[4]:,.2f})" for a in accs].index(sel); acc=accs[idx]
                tt=st.radio("Type",["Deposit","Withdraw"],horizontal=True)
                with st.form("tx"):
                    amt=st.number_input("Amount",min_value=0.01,step=100.0); desc=st.text_input("Desc"); mode=st.selectbox("Mode",["CASH","TRANSFER","CHEQUE"])
                    if st.form_submit_button("Process",use_container_width=True,type="primary"):
                        at="DEPOSIT" if tt=="Deposit" else "WITHDRAWAL"
                        if at=="WITHDRAWAL" and amt>acc[3]: st.error("Insufficient!")
                        else:
                            nb=acc[3]+amt if at=="DEPOSIT" else acc[3]-amt; tdb="CREDIT" if at=="DEPOSIT" else "DEBIT"; vt="RECEIPT" if at=="DEPOSIT" else "PAYMENT"
                            c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,?,?,?,?,?,?,?,?)",(gid('TXN'),acc[0],tdb,amt,nb,desc,mode,vt,gvn(vt),uid))
                            c.execute("UPDATE accounts SET balance=? WHERE id=?",(nb,acc[0])); c.commit()
                            st.success(f"✅ Maturity: ₹{nb+acc[4]:,.2f}"); st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)
    with t3:
        st.markdown('<div class="panel"><h3>Statement</h3>',unsafe_allow_html=True)
        q3=f"SELECT a.id,a.account_number,c.first_name||' '||c.last_name FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND {'c.user_id=?' if role=='customer' else '1=1'}"
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
        st.markdown('<div class="panel"><h3>Maturity</h3>',unsafe_allow_html=True)
        q4=f"SELECT a.account_number,c.first_name||' '||c.last_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND {'c.user_id=?' if role=='customer' else '1=1'}"
        accs=c.execute(q4,(uid,) if role=='customer' else ()).fetchall()
        if accs:
            data=[{'Account':a[0],'Principal':a[2],'Rate':f"{a[3]:.2f}%",'Interest':a[4],'Maturity':a[2]+a[4]} for a in accs]
            st.dataframe(pd.DataFrame(data).style.format({'Principal':'₹{:,.2f}','Interest':'₹{:,.2f}','Maturity':'₹{:,.2f}'}),use_container_width=True)
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def interest_calculation():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c=get_db(); t1,t2,t3=st.tabs(["Calculate","History","Impact"])
    with t1:
        st.markdown('<div class="panel"><h3>Calculate Interest</h3>',unsafe_allow_html=True)
        d1,d2=st.columns(2)
        with d1: cfd=st.date_input("From",date.today().replace(day=1),key="if")
        with d2: ctd=st.date_input("To",date.today(),key="it")
        if cfd>ctd: st.error("Invalid")
        else: st.info(f"{cfd.strftime('%d-%b')} → {ctd.strftime('%d-%b')} ({(ctd-cfd).days+1}d)")
        accs=c.execute("SELECT a.id,a.account_number,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        if accs:
            b1,b2=st.columns(2)
            with b1:
                if st.button("Calculate & Post",use_container_width=True,type="primary",key="cp"):
                    if cfd>ctd: st.error("Invalid!")
                    else:
                        s,r=calc_post_interest(st.session_state.user['id'],cfd,ctd)
                        if s=="OK" and r: st.success(f"✅ ₹{sum(x['int'] for x in r):,.2f}"); st.balloons()
                        else: st.info(s if s!="OK" else "No interest")
            with b2:
                if st.button("Preview",use_container_width=True,key="pv"):
                    pv=[]
                    for a in accs:
                        mb=min_bal(c,a[0],cfd,ctd)
                        if mb<=0: mb=a[2]
                        days=(ctd-cfd).days+1
                        if days>0: pv.append({'Account':a[1],'Min Bal':mb,'Interest':sb_int(mb,a[3] or 3.5,days)})
                    if pv: st.dataframe(pd.DataFrame(pv).style.format({'Min Bal':'₹{:,.2f}','Interest':'₹{:,.2f}'}),use_container_width=True)
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="panel"><h3>History</h3>',unsafe_allow_html=True)
        h=c.execute("SELECT calculation_date,account_number,c.first_name||' '||c.last_name,principal_amount,interest_rate,interest_earned,days_calculated FROM interest_calculations ic JOIN accounts a ON ic.account_id=a.id JOIN customers c ON a.customer_id=c.id ORDER BY calculation_date DESC LIMIT 50").fetchall()
        if h: st.dataframe(pd.DataFrame(h,columns=['Date','Account','Customer','Principal','Rate','Interest','Days']).style.format({'Principal':'₹{:,.2f}','Interest':'₹{:,.2f}'}),use_container_width=True,height=350)
        else: st.info("None")
        st.markdown('</div>',unsafe_allow_html=True)
    with t3:
        st.markdown('<div class="panel"><h3>JV Impact</h3>',unsafe_allow_html=True)
        jvs=c.execute("SELECT jv.voucher_number,jv.voucher_date,jv.total_amount,je.account_head,je.debit_amount,je.credit_amount FROM journal_vouchers jv JOIN journal_entries je ON jv.id=je.voucher_id WHERE (je.account_head='Interest Paid on SB' OR je.account_head LIKE '%SB Account%') AND jv.status='POSTED' ORDER BY jv.voucher_date DESC LIMIT 50").fetchall()
        if jvs:
            jd={}
            for j in jvs:
                if j[0] not in jd: jd[j[0]]={'date':j[1],'amt':j[2],'entries':[]}
                jd[j[0]]['entries'].append({'head':j[3],'dr':j[4],'cr':j[5]})
            for vn,d in jd.items():
                with st.expander(f"{vn} - {d['date']} - ₹{d['amt']:,.2f}"):
                    for e in d['entries']: st.write(f"{e['head']}: Dr ₹{e['dr']:,.2f} | Cr ₹{e['cr']:,.2f}")
            st.success(f"TB Impact: ₹{sum(d['amt'] for d in jd.values()):,.2f}")
        else: st.info("None")
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def trial_balance():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c=get_db()
    st.markdown('<div class="panel"><h3>Trial Balance</h3>',unsafe_allow_html=True)
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
                if cd: st.dataframe(pd.DataFrame(cd)[['head','dr','cr']].rename(columns={'head':'Head','dr':'Debit','cr':'Credit'}).style.format({'Debit':'₹{:,.2f}','Credit':'₹{:,.2f}'}),use_container_width=True,height=min(250,len(cd)*40))
            dft=df['dr'].sum(); cft=df['cr'].sum()
            st.divider()
            n1,n2,n3=st.columns(3)
            with n1: st.metric("Total Debit",f"₹{dft:,.2f}")
            with n2: st.metric("Total Credit",f"₹{cft:,.2f}")
            with n3: st.success("✅ BALANCED!") if abs(dft-cft)<0.01 else st.error(f"Diff: ₹{abs(dft-cft):,.2f}")
            st.download_button("📥 CSV",df.to_csv(index=False),"tb.csv","text/csv",key="dtb")
    st.markdown('</div>',unsafe_allow_html=True); c.close()

def balance_sheet():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c=get_db()
    st.markdown('<div class="panel"><h3>Balance Sheet</h3>',unsafe_allow_html=True)
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
            st.markdown(f"""<div class="panel"><h3>📊 ASSETS</h3><div style="display:flex;justify-content:space-between;padding:0.3rem 0"><span>💰 Cash</span><b>₹{cash:,.2f}</b></div><div style="display:flex;justify-content:space-between;padding:0.3rem 0"><span>🏦 SB</span><b>₹{sb_bal:,.2f}</b></div><div style="display:flex;justify-content:space-between;padding:0.3rem 0"><span>💎 FD</span><b>₹{fd:,.2f}</b></div><div style="display:flex;justify-content:space-between;padding:0.3rem 0"><span>🔄 RD</span><b>₹{rd:,.2f}</b></div><hr><div style="display:flex;justify-content:space-between"><b>Total</b><b>₹{ta:,.2f}</b></div></div>""",unsafe_allow_html=True)
        with p2:
            st.markdown(f"""<div class="panel"><h3>📋 LIABILITIES</h3><div style="display:flex;justify-content:space-between;padding:0.3rem 0"><span>📈 SB Int</span><b>₹{sb_int:,.2f}</b></div><div style="display:flex;justify-content:space-between;padding:0.3rem 0"><span>📈 FD Int</span><b>₹{fd_int:,.2f}</b></div><div style="display:flex;justify-content:space-between;padding:0.3rem 0"><span>🏦 SB</span><b>₹{sb_bal:,.2f}</b></div><div style="display:flex;justify-content:space-between;padding:0.3rem 0"><span>💎 FD</span><b>₹{fd:,.2f}</b></div><div style="display:flex;justify-content:space-between;padding:0.3rem 0"><span>🔄 RD</span><b>₹{rd:,.2f}</b></div><hr><div style="display:flex;justify-content:space-between"><b>Total</b><b>₹{tl:,.2f}</b></div></div>""",unsafe_allow_html=True)
        st.markdown(f"""<div class="panel"><h3>💰 CAPITAL</h3><div style="display:flex;justify-content:space-between"><b>Capital</b><b>₹{cap:,.2f}</b></div></div>""",unsafe_allow_html=True)
        if abs(ta-(tl+cap))<0.01: st.success("✅ Balanced!")
    st.markdown('</div>',unsafe_allow_html=True); c.close()

def profit_loss():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c=get_db()
    st.markdown('<div class="panel"><h3>P&L</h3>',unsafe_allow_html=True)
    d1,d2=st.columns(2)
    with d1: fd=st.date_input("From",date.today().replace(month=1,day=1),key="plf")
    with d2: td=st.date_input("To",date.today(),key="plt")
    if st.button("Generate",use_container_width=True,type="primary",key="pl"):
        inc=[('Interest',c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Interest Earned' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),('Fees',c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Fees & Charges' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),('Commission',c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Commission Income' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),('Other',c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Other Income' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0])]
        exp=[('SB Interest',c.execute("SELECT COALESCE(SUM(debit_amount),0) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE je.account_head='Interest Paid on SB' AND jv.status='POSTED' AND DATE(jv.voucher_date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),('Salary',c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Salary & Wages' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),('Rent',c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Rent & Utilities' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),('Operating',c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Operating Expenses' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),('Admin',c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Administrative Expenses' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0]),('Other',c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Other Expenses' AND DATE(date) BETWEEN ? AND ?",(fd,td)).fetchone()[0])]
        ti=sum(i[1] for i in inc); te=sum(e[1] for e in exp); net=ti-te
        q1,q2=st.columns(2)
        with q1:
            st.markdown('<div class="panel"><h3>📈 INCOME</h3>',unsafe_allow_html=True)
            for i,amt in inc: st.write(f"• {i}: ₹{amt:,.2f}")
            st.markdown(f'<hr><b>Total: ₹{ti:,.2f}</b></div>',unsafe_allow_html=True)
        with q2:
            st.markdown('<div class="panel"><h3>📉 EXPENSES</h3>',unsafe_allow_html=True)
            for i,amt in exp:
                if amt>0: st.write(f"• {i}: ₹{amt:,.2f}")
            st.markdown(f'<hr><b>Total: ₹{te:,.2f}</b></div>',unsafe_allow_html=True)
        if net>=0: st.success(f"## Net Profit: ₹{net:,.2f}")
        else: st.error(f"## Net Loss: ₹{abs(net):,.2f}")
    st.markdown('</div>',unsafe_allow_html=True); c.close()

def income_expenses():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c=get_db(); uid=st.session_state.user['id']
    t1,t2=st.tabs(["Income","Expense"])
    with t1:
        st.markdown('<div class="panel"><h3>Record Income</h3>',unsafe_allow_html=True)
        with st.form("if"):
            d1,d2=st.columns(2)
            with d1: it=st.selectbox("Type",["Interest Earned","Fees & Charges","Commission Income","Other Income"]); amt=st.number_input("Amount",min_value=1.0,step=100.0)
            with d2: dt=st.date_input("Date",date.today(),key="id"); desc=st.text_area("Desc")
            if st.form_submit_button("Record",use_container_width=True,type="primary"):
                c.execute("INSERT INTO income (income_id,income_type,amount,description,date,created_by) VALUES (?,?,?,?,?,?)",(gid('INC'),it,amt,desc,dt,uid)); c.commit(); st.success(f"✅ ₹{amt:,.2f}")
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="panel"><h3>Record Expense</h3>',unsafe_allow_html=True)
        with st.form("ef"):
            d1,d2=st.columns(2)
            with d1: et=st.selectbox("Type",["Salary & Wages","Rent & Utilities","Operating Expenses","Administrative Expenses","Other Expenses"]); amt=st.number_input("Amount",min_value=1.0,step=100.0)
            with d2: dt=st.date_input("Date",date.today(),key="ed"); desc=st.text_area("Desc")
            if st.form_submit_button("Record",use_container_width=True,type="primary"):
                c.execute("INSERT INTO expenses (expense_id,expense_type,amount,description,date,created_by) VALUES (?,?,?,?,?,?)",(gid('EXP'),et,amt,desc,dt,uid)); c.commit(); st.success(f"✅ ₹{amt:,.2f}")
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def fixed_deposits():
    c=get_db(); uid=st.session_state.user['id']
    t1,t2,t3=st.tabs(["Open","Active","Maturity"])
    with t1:
        st.markdown('<div class="panel"><h3>Open FD</h3>',unsafe_allow_html=True)
        custs=c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND c.kyc_status='VERIFIED' AND a.status='ACTIVE'").fetchall()
        if custs:
            sel=st.selectbox("Customer",[f"{x[1]} - {x[2]}" for x in custs])
            if sel:
                idx=[f"{x[1]} - {x[2]}" for x in custs].index(sel); cust=custs[idx]
                with st.form("fd"):
                    d1,d2=st.columns(2)
                    with d1: p=st.number_input("Principal",min_value=1000.0,step=1000.0,value=10000.0); t=st.selectbox("Tenure",[3,6,12,24,36,60]); r=st.number_input("Rate",3.0,10.0,6.5,0.25)
                    with d2: sd=st.date_input("Start",date.today(),key="fs"); nom=st.text_input("Nominee")
                    md=sd+timedelta(days=t*30); ma=fd_mat(p,r,t)
                    st.info(f"Maturity: {md.strftime('%d-%m-%Y')} | Amount: ₹{ma:,.2f}")
                    if st.form_submit_button("Open FD",use_container_width=True,type="primary"):
                        fdn=gid('FD'); an=gan('FD')
                        c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate) VALUES (?,?,'FD',0.00,?)",(an,cust[0],r))
                        aid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                        c.execute("INSERT INTO fixed_deposits (fd_number,account_id,principal_amount,interest_rate,start_date,maturity_date,maturity_amount,tenure_months,nominee_name) VALUES (?,?,?,?,?,?,?,?,?)",(fdn,aid,p,r,sd,md,ma,t,nom))
                        c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,'FD','FD_DEPOSIT','RECEIPT',?,?)",(gid('TXN'),aid,p,p,gvn('RECEIPT'),uid))
                        c.commit(); st.success(f"✅ {fdn}"); st.balloons()
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="panel"><h3>Active FDs</h3>',unsafe_allow_html=True)
        fds=c.execute("SELECT fd_number,c.first_name||' '||c.last_name,principal_amount,interest_rate,start_date,maturity_date,maturity_amount FROM fixed_deposits fd JOIN accounts a ON fd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE fd.status='ACTIVE' ORDER BY maturity_date").fetchall()
        if fds: st.dataframe(pd.DataFrame(fds,columns=['FD','Customer','Principal','Rate','Start','Maturity','Maturity Amt']).style.format({'Principal':'₹{:,.2f}','Maturity Amt':'₹{:,.2f}'}),use_container_width=True)
        else: st.info("None")
        st.markdown('</div>',unsafe_allow_html=True)
    with t3:
        st.markdown('<div class="panel"><h3>Maturity Alerts</h3>',unsafe_allow_html=True)
        today=date.today(); mat=c.execute("SELECT fd_number,c.first_name||' '||c.last_name,maturity_amount,maturity_date FROM fixed_deposits fd JOIN accounts a ON fd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE maturity_date BETWEEN ? AND ? AND status='ACTIVE'",(today,today+timedelta(days=30))).fetchall()
        if mat: st.warning(f"🔔 {len(mat)} maturing soon"); st.dataframe(pd.DataFrame(mat,columns=['FD','Customer','Amount','Date']).style.format({'Amount':'₹{:,.2f}'}),use_container_width=True)
        else: st.success("✅ None")
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def recurring_deposits():
    c=get_db(); uid=st.session_state.user['id']
    t1,t2,t3=st.tabs(["Open","Active","Pay"])
    with t1:
        st.markdown('<div class="panel"><h3>Open RD</h3>',unsafe_allow_html=True)
        custs=c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND c.kyc_status='VERIFIED' AND a.status='ACTIVE'").fetchall()
        if custs:
            sel=st.selectbox("Customer",[f"{x[1]} - {x[2]}" for x in custs])
            if sel:
                idx=[f"{x[1]} - {x[2]}" for x in custs].index(sel); cust=custs[idx]
                with st.form("rd"):
                    d1,d2=st.columns(2)
                    with d1: m=st.number_input("Monthly",min_value=100.0,step=100.0,value=1000.0); t=st.selectbox("Tenure",[6,12,24,36,48,60]); r=st.number_input("Rate",3.0,10.0,6.0,0.25)
                    with d2: sd=st.date_input("Start",date.today(),key="rs"); nom=st.text_input("Nominee")
                    md=sd+timedelta(days=t*30); ma=rd_mat(m,r,t)
                    st.info(f"Maturity: {md.strftime('%d-%m-%Y')} | Amount: ₹{ma:,.2f}")
                    if st.form_submit_button("Open RD",use_container_width=True,type="primary"):
                        rdn=gid('RD'); an=gan('RD')
                        c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate) VALUES (?,?,'RD',0.00,?)",(an,cust[0],r))
                        aid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                        c.execute("INSERT INTO recurring_deposits (rd_number,account_id,monthly_amount,interest_rate,start_date,maturity_date,maturity_amount,tenure_months,total_installments,nominee_name) VALUES (?,?,?,?,?,?,?,?,?,?)",(rdn,aid,m,r,sd,md,ma,t,t,nom))
                        c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,'RD 1','RD_INSTALLMENT','RECEIPT',?,?)",(gid('TXN'),aid,m,m,gvn('RECEIPT'),uid))
                        c.execute("UPDATE recurring_deposits SET installments_paid=1 WHERE rd_number=?",(rdn,)); c.commit(); st.success(f"✅ {rdn}"); st.balloons()
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="panel"><h3>Active RDs</h3>',unsafe_allow_html=True)
        rds=c.execute("SELECT rd_number,c.first_name||' '||c.last_name,monthly_amount,interest_rate,start_date,maturity_date,maturity_amount,installments_paid,total_installments FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE status='ACTIVE' ORDER BY maturity_date").fetchall()
        if rds:
            df=pd.DataFrame(rds,columns=['RD','Customer','Monthly','Rate','Start','Maturity','Maturity Amt','Paid','Total'])
            df['Progress']=df.apply(lambda r:f"{r['Paid']}/{r['Total']}",axis=1)
            st.dataframe(df.style.format({'Monthly':'₹{:,.2f}','Maturity Amt':'₹{:,.2f}'}),use_container_width=True)
        st.markdown('</div>',unsafe_allow_html=True)
    with t3:
        st.markdown('<div class="panel"><h3>Pay Installment</h3>',unsafe_allow_html=True)
        rds=c.execute("SELECT rd.id,rd_number,c.first_name||' '||c.last_name,monthly_amount,installments_paid,total_installments,a.id FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE status='ACTIVE' AND installments_paid<total_installments").fetchall()
        if rds:
            sel=st.selectbox("RD",[f"{r[1]} - {r[2]} ({r[4]}/{r[5]})" for r in rds])
            if sel:
                idx=[f"{r[1]} - {r[2]} ({r[4]}/{r[5]})" for r in rds].index(sel); rd=rds[idx]
                with st.form("pr"):
                    amt=st.number_input("Amount",value=float(rd[3]),min_value=float(rd[3]))
                    if st.form_submit_button("Pay",use_container_width=True,type="primary"):
                        c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,?,'RD_INSTALLMENT','RECEIPT',?,?)",(gid('TXN'),rd[6],amt,amt,f"RD {rd[4]+1}/{rd[5]}",gvn('RECEIPT'),uid))
                        np=rd[4]+1; c.execute("UPDATE recurring_deposits SET installments_paid=? WHERE id=?",(np,rd[0]))
                        if np>=rd[5]: c.execute("UPDATE recurring_deposits SET status='MATURED' WHERE id=?",(rd[0],))
                        c.commit(); st.success(f"✅ {np}/{rd[5]}"); st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def transactions():
    c=get_db(); uid=st.session_state.user['id']
    st.markdown('<div class="panel"><h3>Transactions</h3>',unsafe_allow_html=True)
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
    else: st.info("None")
    st.markdown('</div>',unsafe_allow_html=True); c.close()

def journal_vouchers():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c=get_db(); uid=st.session_state.user['id']
    t1,t2=st.tabs(["Create","List"])
    with t1:
        st.markdown('<div class="panel"><h3>Create JV</h3>',unsafe_allow_html=True)
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
            if st.form_submit_button("Create",use_container_width=True,type="primary"):
                if abs(td_v-tc_v)>0.01: st.error("Must balance!")
                else:
                    vn=gvn('JOURNAL'); c.execute("INSERT INTO journal_vouchers (voucher_number,voucher_date,description,total_amount,created_by) VALUES (?,?,?,?,?)",(vn,vd,desc,td_v,uid))
                    vid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                    for e in entries:
                        if e['d']>0 or e['c']>0: c.execute("INSERT INTO journal_entries (voucher_id,account_head,debit_amount,credit_amount) VALUES (?,?,?,?)",(vid,e['h'],e['d'],e['c']))
                    c.commit(); st.success(f"✅ {vn}"); st.balloons()
        st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="panel"><h3>JV List</h3>',unsafe_allow_html=True)
        vouchers=c.execute("SELECT voucher_number,voucher_date,description,total_amount,status FROM journal_vouchers ORDER BY created_at DESC").fetchall()
        if vouchers:
            for v in vouchers:
                sc={'DRAFT':'🟡','POSTED':'🟢','CANCELLED':'🔴'}
                with st.expander(f"{sc.get(v[4],'⚪')} {v[0]} - {v[1]} - ₹{v[3]:,.2f}"):
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
        else: st.info("None")
        st.markdown('</div>',unsafe_allow_html=True)
    c.close()

def reports():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    rt=st.selectbox("Report",["Customer List","Interest Report","Daily Transactions"])
    c=get_db()
    st.markdown('<div class="panel"><h3>Report</h3>',unsafe_allow_html=True)
    if rt=="Customer List":
        custs=c.execute("SELECT customer_id,first_name,last_name,email,phone,city,kyc_status FROM customers ORDER BY customer_id DESC").fetchall()
        if custs: st.dataframe(pd.DataFrame(custs,columns=['ID','First','Last','Email','Phone','City','KYC']),use_container_width=True)
    elif rt=="Interest Report":
        calcs=c.execute("SELECT calculation_date,account_number,c.first_name||' '||c.last_name,principal_amount,interest_rate,interest_earned,days_calculated FROM interest_calculations ic JOIN accounts a ON ic.account_id=a.id JOIN customers c ON a.customer_id=c.id ORDER BY calculation_date DESC").fetchall()
        if calcs: st.dataframe(pd.DataFrame(calcs,columns=['Date','Account','Customer','Principal','Rate','Interest','Days']).style.format({'Principal':'₹{:,.2f}','Interest':'₹{:,.2f}'}),use_container_width=True)
    elif rt=="Daily Transactions":
        rd=st.date_input("Date",date.today(),key="rpd")
        txns=c.execute("SELECT transaction_id,c.first_name||' '||c.last_name,account_type,transaction_type,amount,voucher_number FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE DATE(t.created_at)=?",(rd,)).fetchall()
        if txns: st.dataframe(pd.DataFrame(txns,columns=['Txn','Customer','Type','Action','Amount','Voucher']).style.format({'Amount':'₹{:,.2f}'}),use_container_width=True)
        else: st.info(f"None on {rd}")
    st.markdown('</div>',unsafe_allow_html=True); c.close()

def my_details():
    c=get_db(); uid=st.session_state.user['id']
    cust=c.execute("SELECT * FROM customers WHERE user_id=?",(uid,)).fetchone()
    if cust:
        st.markdown(f"""<div style="background:#1a1a2e;color:white;padding:1.2rem;border-radius:16px;margin-bottom:1rem"><h2>{cust[3]} {cust[4]}</h2><p>📋 {cust[2]} | 📧 {cust[7]} | 📱 {cust[8]}</p></div>""",unsafe_allow_html=True)
        st.markdown('<div class="panel"><h3>My SB Accounts</h3>',unsafe_allow_html=True)
        accs=c.execute("SELECT account_number,balance,COALESCE(total_interest_earned,0) FROM accounts WHERE customer_id=? AND account_type='SB'",(cust[0],)).fetchall()
        if accs:
            for a in accs:
                mv=a[1]+a[2]
                st.markdown(f"""<div style="background:#f9fafb;padding:0.7rem;border-radius:10px;margin:0.3rem 0;border-left:3px solid #6366f1"><b>{a[0]}</b> | Principal: ₹{a[1]:,.2f} | Interest: ₹{a[2]:,.2f} | <b>Maturity: ₹{mv:,.2f}</b></div>""",unsafe_allow_html=True)
        else: st.info("None")
        st.markdown('</div>',unsafe_allow_html=True)
    else: st.warning("No profile")
    c.close()

if __name__=="__main__":
    main()


