
# 🏦 ENTERPRISE CORE BANKING SYSTEM - SB, FD & RD MODULES (CORRECTED)
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
from decimal import Decimal
import uuid
import hashlib

# ==================== DATABASE INITIALIZATION ====================
def init_database():
    conn = sqlite3.connect('banking_system_complete.db')
    c = conn.cursor()
    
    # Core Tables
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        account_number TEXT UNIQUE NOT NULL, 
        customer_id INTEGER NOT NULL, 
        account_type TEXT NOT NULL, 
        balance DECIMAL(15,2) DEFAULT 0.00, 
        status TEXT DEFAULT 'ACTIVE', 
        interest_rate DECIMAL(5,2), 
        tenor_months INTEGER DEFAULT 0,
        monthly_installment DECIMAL(15,2) DEFAULT 0.00,
        maturity_date DATE,
        maturity_amount DECIMAL(15,2) DEFAULT 0.00,
        last_interest_calculation DATE, 
        total_interest_earned DECIMAL(15,2) DEFAULT 0.00, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
        FOREIGN KEY (customer_id) REFERENCES customers (id)
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
        voucher_type TEXT, 
        voucher_number TEXT, 
        created_by INTEGER, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
        FOREIGN KEY (account_id) REFERENCES accounts (id), 
        FOREIGN KEY (created_by) REFERENCES users (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS ledger_heads (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        head_name TEXT UNIQUE NOT NULL
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS journal_vouchers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        voucher_number TEXT UNIQUE NOT NULL, 
        voucher_date DATE NOT NULL, 
        description TEXT, 
        total_amount DECIMAL(15,2) NOT NULL, 
        status TEXT DEFAULT 'POSTED', 
        created_by INTEGER, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
        FOREIGN KEY (created_by) REFERENCES users (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS journal_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        voucher_id INTEGER NOT NULL, 
        account_head TEXT NOT NULL, 
        debit_amount DECIMAL(15,2) DEFAULT 0.00, 
        credit_amount DECIMAL(15,2) DEFAULT 0.00, 
        description TEXT, 
        FOREIGN KEY (voucher_id) REFERENCES journal_vouchers (id)
    )''')
    
    # Seed default accounting ledger heads including FD & RD controls
    default_heads = [
        'Cash', 'Bank (Main)', 'Savings Bank Control Account', 
        'Fixed Deposit Control Account', 'Recurring Deposit Control Account',
        'Interest Paid on SB', 'Interest Paid on FD', 'Interest Paid on RD',
        'Fee Income', 'Rent Expense', 'Salary Expense', 'Miscellaneous'
    ]
    for h in default_heads:
        c.execute("INSERT OR IGNORE INTO ledger_heads (head_name) VALUES (?)", (h,))
        
    conn.commit()
    conn.close()

# ==================== UTILITY FUNCTIONS ====================
def get_db(): return sqlite3.connect('banking_system_complete.db')
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()
def generate_id(p): return f"{p}{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4]}"
def generate_account_number(t): 
    prefix = {'SB': '100', 'FD': '300', 'RD': '400'}.get(t, '900')
    return f"{prefix}{datetime.now().strftime('%y%m%d')}{str(uuid.uuid4().int)[:6]}"
def generate_voucher_number(v): return f"{'PMT' if v=='PAYMENT' else 'RCT' if v=='RECEIPT' else 'JNL'}{datetime.now().strftime('%Y%m%d%H%M')}{str(uuid.uuid4().int)[:4]}"

def login_user(u, p):
    conn = get_db()
    user = conn.cursor().execute("SELECT * FROM users WHERE username=? AND password=? AND is_active=1", (u, hash_password(p))).fetchone()
    conn.close()
    return user

def create_default_admin():
    conn = get_db()
    if conn.cursor().execute("SELECT COUNT(*) FROM users WHERE username='admin'").fetchone()[0] == 0:
        conn.cursor().execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('admin', hash_password('admin123'), 'admin'))
        conn.commit()
    conn.close()

def calculate_fd_maturity(principal, rate, months):
    years = months / 12.0
    maturity = principal * ((1 + (rate / 400.0)) ** (4 * years))
    return round(maturity, 2)

def calculate_rd_maturity(monthly_amt, rate, months):
    total_deposit = monthly_amt * months
    interest = monthly_amt * (months * (months + 1) / 2.0) * (rate / 1200.0)
    return round(total_deposit + interest, 2)

# ==================== ENTERPRISE UI STYLING ====================
def load_enterprise_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    html, body, [class*="css"] { background-color: #f4f7f6; }
    .topbar {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        color: white; padding: 1.2rem 2.5rem; border-radius: 14px;
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 2rem; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15);
    }
    .topbar h1 { margin: 0; font-size: 1.6rem; font-weight: 800; color: #ffffff !important; }
    .topbar .user { font-size: 0.9rem; font-weight: 500; background: rgba(255,255,255,0.15); padding: 0.5rem 1.2rem; border-radius: 20px; }
    .dash-card {
        background: white; border-radius: 16px; padding: 1.8rem 1.2rem; text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 1rem; border: 1px solid #f1f5f9;
    }
    .dash-card h2 { font-size: 2rem; margin: 0.5rem 0; font-weight: 800; color: #0f172a; }
    .dash-card p { margin: 0; font-size: 0.8rem; color: #64748b; font-weight: 700; text-transform: uppercase; }
    .section-card {
        background: white; border-radius: 16px; padding: 2rem; margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); border: 1px solid #f1f5f9;
    }
    .section-card h3 {
        font-size: 1.2rem; font-weight: 700; color: #1e293b; margin-bottom: 1.5rem;
        padding-bottom: 1rem; border-bottom: 2px solid #f1f5f9;
    }
    [data-testid="stSidebar"] { background-color: #0f2027 !important; }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }
    [data-testid="stSidebar"] .stButton>button {
        background: transparent !important; border: none !important; text-align: left !important;
        padding: 0.7rem 1.2rem !important; border-radius: 10px !important; font-weight: 600; width: 100%;
    }
    [data-testid="stSidebar"] .stButton>button:hover { background: rgba(255,255,255,0.1) !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# ==================== MAIN APPLICATION ROUTER ====================
def main():
    st.set_page_config(page_title="Core Banking System - Complete", page_icon="🏦", layout="wide", initial_sidebar_state="expanded")
    init_database()
    create_default_admin()
    
    if 'user' not in st.session_state: st.session_state.user = None
    if 'page' not in st.session_state: st.session_state.page = 'dashboard'
    
    load_enterprise_css()
    
    if st.session_state.user is None:
        show_login()
    else:
        show_app()

def show_login():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="section-card" style="text-align:center;">', unsafe_allow_html=True)
        st.markdown('<h1>🏦</h1><h2>CoreBanking OS</h2><p>Secure Enterprise Login</p>', unsafe_allow_html=True)
        u = st.text_input("Username", placeholder="admin")
        p = st.text_input("Password", type="password", placeholder="••••••••")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Sign In", type="primary", use_container_width=True):
            user = login_user(u, p)
            if user:
                st.session_state.user = {'id': user[0], 'username': user[1], 'role': user[3]}
                st.rerun()
            else:
                st.error("Invalid username or password.")
        st.markdown('<small style="color:#64748b;">Default Admin: admin / admin123</small>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def show_app():
    st.markdown(f'<div class="topbar"><h1>🏦 CoreBanking OS</h1><div class="user">👤 {st.session_state.user["username"]} ({st.session_state.user["role"].upper()})</div></div>', unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown('<h3 style="color:white; text-align:center; margin-bottom:1.5rem;">Navigation</h3>', unsafe_allow_html=True)
        menu = {
            'dashboard': '📊 Dashboard',
            'customers': '👥 Customers & KYC',
            'sb_accounts': '💰 SB Accounts',
            'fd_accounts': '🔒 Fixed Deposits (FD)',
            'rd_accounts': '🔄 Recurring Deposits (RD)',
            'transactions': '💳 Cashier & Transactions',
            'journal_vouchers': '📝 Journal Vouchers',
            'trial_balance': '⚖️ Trial Balance'
        }
        for k, v in menu.items():
            if st.button(v, key=f"nav_{k}", use_container_width=True):
                st.session_state.page = k
                st.rerun()
        st.markdown('<hr style="border-color:rgba(255,255,255,0.1)">', unsafe_allow_html=True)
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.user = None
            st.rerun()
            
    page = st.session_state.get('page', 'dashboard')
    if page == 'dashboard': dashboard()
    elif page == 'customers': customers_module()
    elif page == 'sb_accounts': sb_accounts_module()
    elif page == 'fd_accounts': fd_accounts_module()
    elif page == 'rd_accounts': rd_accounts_module()
    elif page == 'transactions': transactions_module()
    elif page == 'journal_vouchers': journal_vouchers_module()
    elif page == 'trial_balance': trial_balance_module()

# ==================== MODULES ====================

def dashboard():
    conn = get_db()
    cust_count = conn.execute("SELECT COUNT(*) FROM customers WHERE kyc_status!='DEACTIVATED'").fetchone()[0]
    sb_count = conn.execute("SELECT COUNT(*) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
    fd_count = conn.execute("SELECT COUNT(*) FROM accounts WHERE account_type='FD' AND status='ACTIVE'").fetchone()[0]
    rd_count = conn.execute("SELECT COUNT(*) FROM accounts WHERE account_type='RD' AND status='ACTIVE'").fetchone()[0]
    total_deposits = conn.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE status='ACTIVE'").fetchone()[0]
    conn.close()
    
    cols = st.columns(4)
    with cols[0]: st.markdown(f'<div class="dash-card"><h2>{cust_count}</h2><p>Total Customers</p></div>', unsafe_allow_html=True)
    with cols[1]: st.markdown(f'<div class="dash-card"><h2>{sb_count}</h2><p>SB Accounts</p></div>', unsafe_allow_html=True)
    with cols[2]: st.markdown(f'<div class="dash-card"><h2>{fd_count} / {rd_count}</h2><p>FD / RD Accounts</p></div>', unsafe_allow_html=True)
    with cols[3]: st.markdown(f'<div class="dash-card"><h2>₹{total_deposits:,.2f}</h2><p>Total Portfolio</p></div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    conn = get_db()
    c1, c2 = st.columns([1.5, 1])
    with c1:
        st.markdown('<div class="section-card"><h3>📋 Recent Transactions</h3>', unsafe_allow_html=True)
        txns = conn.execute("SELECT t.transaction_id, c.first_name||' '||c.last_name, a.account_type, t.transaction_type, t.amount, t.created_at FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id ORDER BY t.created_at DESC LIMIT 6").fetchall()
        if txns:
            st.dataframe(pd.DataFrame(txns, columns=['Txn ID', 'Customer', 'Type', 'Txn Mode', 'Amount', 'Date']).style.format({'Amount': '₹{:,.2f}'}), use_container_width=True)
        else:
            st.info("No transactions recorded yet.")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="section-card"><h3>⚡ Quick Actions</h3>', unsafe_allow_html=True)
        if st.button("➕ Register New Customer", use_container_width=True, type="primary"):
            st.session_state.page = 'customers'; st.rerun()
        if st.button("🔒 Open Fixed Deposit (FD)", use_container_width=True):
            st.session_state.page = 'fd_accounts'; st.rerun()
        if st.button("🔄 Open Recurring Deposit (RD)", use_container_width=True):
            st.session_state.page = 'rd_accounts'; st.rerun()
        if st.button("⚖️ View Trial Balance", use_container_width=True):
            st.session_state.page = 'trial_balance'; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

def customers_module():
    st.markdown('<div class="section-card"><h3>👥 Customer Registration & KYC Management</h3>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["Register Customer", "View & Verify KYC"])
    with t1:
        with st.form("cust_reg"):
            c1, c2 = st.columns(2)
            with c1:
                fn = st.text_input("First Name*")
                ln = st.text_input("Last Name*")
                dob = st.date_input("Date of Birth*", min_value=date(1900,1,1))
                email = st.text_input("Email Address*")
                phone = st.text_input("Phone Number*")
            with c2:
                pan = st.text_input("PAN Number*")
                aadhar = st.text_input("Aadhar Number / Gov ID*")
                addr = st.text_area("Address")
                city = st.text_input("City")
                state = st.text_input("State")
                pin = st.text_input("PIN Code")
            if st.form_submit_button("Submit Registration", type="primary", use_container_width=True):
                if not all([fn, ln, email, phone, pan, aadhar]):
                    st.error("Please fill all required (*) fields.")
                else:
                    try:
                        conn = get_db()
                        cid = generate_id('CUST')
                        conn.execute("INSERT INTO customers (customer_id, first_name, last_name, date_of_birth, email, phone, address, city, state, pincode, pan_number, aadhar_number) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (cid, fn, ln, dob, email, phone, addr, city, state, pin, pan, aadhar))
                        conn.commit(); conn.close()
                        st.success(f"✅ Customer successfully registered! ID: {cid}")
                    except sqlite3.IntegrityError:
                        st.error("❌ Customer with this Email, PAN, or Aadhar already exists.")
    with t2:
        conn = get_db()
        custs = conn.execute("SELECT id, customer_id, first_name||' '||last_name, email, phone, kyc_status FROM customers WHERE kyc_status!='DEACTIVATED'").fetchall()
        conn.close()
        if custs:
            df = pd.DataFrame(custs, columns=['DB ID', 'Customer ID', 'Name', 'Email', 'Phone', 'KYC Status'])
            st.dataframe(df, use_container_width=True)
            
            sel_id = st.selectbox("Select Customer to Verify/Approve", options=[c[0] for c in custs], format_func=lambda x: next(f"{c[1]} - {c[2]} ({c[5])}" for c in custs if c[0] == x))
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Approve KYC & Open SB Account", type="primary", use_container_width=True):
                    conn = get_db()
                    conn.execute("UPDATE customers SET kyc_status='VERIFIED' WHERE id=?", (sel_id,))
                    if not conn.execute("SELECT id FROM accounts WHERE customer_id=? AND account_type='SB'", (sel_id,)).fetchone():
                        acno = generate_account_number('SB')
                        conn.execute("INSERT INTO accounts (account_number, customer_id, account_type, balance, interest_rate) VALUES (?,?,'SB',0.00,3.5)", (acno, sel_id))
                    conn.commit(); conn.close()
                    st.success("KYC Verified & SB Account Opened Successfully!")
                    st.rerun()
            with col2:
                if st.button("❌ Reject KYC", use_container_width=True):
                    conn = get_db()
                    conn.execute("UPDATE customers SET kyc_status='REJECTED' WHERE id=?", (sel_id,))
                    conn.commit(); conn.close()
                    st.warning("KYC Rejected.")
                    st.rerun()
        else:
            st.info("No customers found.")
    st.markdown('</div>', unsafe_allow_html=True)

def sb_accounts_module():
    st.markdown('<div class="section-card"><h3>💰 Savings Bank Accounts Management</h3>', unsafe_allow_html=True)
    conn = get_db()
    accs = conn.execute("SELECT a.account_number, c.first_name||' '||c.last_name, a.balance, a.interest_rate, a.status FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB'").fetchall()
    conn.close()
    if accs:
        st.dataframe(pd.DataFrame(accs, columns=['Account Number', 'Customer Name', 'Balance (₹)', 'Interest Rate (%)', 'Status']).style.format({'Balance (₹)': '₹{:,.2f}'}), use_container_width=True)
    else:
        st.info("No Savings Bank accounts found.")
    st.markdown('</div>', unsafe_allow_html=True)

def fd_accounts_module():
    st.markdown('<div class="section-card"><h3>🔒 Fixed Deposit (FD) Module</h3>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["Create New Fixed Deposit", "Existing FD Accounts"])
    
    with t1:
        conn = get_db()
        custs = conn.execute("SELECT id, customer_id, first_name||' '||last_name FROM customers WHERE kyc_status='VERIFIED'").fetchall()
        conn.close()
        
        if not custs:
            st.warning("No verified customers available to open an FD.")
        else:
            with st.form("fd_creation_form"):
                cust_dict = {f"{c[1]} - {c[2]}": c[0] for c in custs}
                sel_cust = st.selectbox("Select Customer", options=list(cust_dict.keys()))
                principal = st.number_input("Deposit Principal Amount (₹)", min_value=1000.00, step=1000.00, value=50000.00)
                tenor_months = st.number_input("Tenor (in Months)", min_value=1, max_value=120, value=12)
                interest_rate = st.number_input("Interest Rate (% p.a.)", min_value=0.1, max_value=20.0, value=6.5, step=0.1)
                
                maturity_amt = calculate_fd_maturity(principal, interest_rate, tenor_months)
                maturity_dt = date.today() + timedelta(days=int(tenor_months * 30.44))
                
                st.info(f"📅 **Estimated Maturity Date:** {maturity_dt.strftime('%d-%b-%Y')} &nbsp;|&nbsp; 💰 **Maturity Amount:** ₹{maturity_amt:,.2f}")
                
                if st.form_submit_button("Create Fixed Deposit Account", type="primary", use_container_width=True):
                    cid = cust_dict[sel_cust]
                    conn = get_db()
                    acno = generate_account_number('FD')
                    
                    conn.execute("INSERT INTO accounts (account_number, customer_id, account_type, balance, status, interest_rate, tenor_months, maturity_date, maturity_amount) VALUES (?,?,'FD',?,'ACTIVE',?,?,?,?)", (acno, cid, principal, interest_rate, tenor_months, maturity_dt, maturity_amt))
                    
                    jvn = generate_voucher_number('JOURNAL')
                    conn.execute("INSERT INTO journal_vouchers (voucher_number, voucher_date, description, total_amount, status, created_by) VALUES (?,?,?,?,'POSTED',?)", (jvn, date.today(), f"Fixed Deposit Creation {acno}", principal, st.session_state.user['id']))
                    jid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?,'Cash',?,0,?)", (jid, principal, "FD Opening Cash"))
                    conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?,'Fixed Deposit Control Account',0,?,?)", (jid, principal, f"FD A/C {acno}"))
                    
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Fixed Deposit successfully created! Account Number: {acno}")
                    st.rerun()
                    
    with t2:
        conn = get_db()
        fds = conn.execute("SELECT a.account_number, c.first_name||' '||c.last_name, a.balance, a.interest_rate, a.tenor_months, a.maturity_date, a.maturity_amount, a.status FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='FD'").fetchall()
        conn.close()
        if fds:
            df = pd.DataFrame(fds, columns=['A/C Number', 'Customer Name', 'Principal (₹)', 'Rate (%)', 'Tenor (Mo)', 'Maturity Date', 'Maturity Amt (₹)', 'Status'])
            st.dataframe(df.style.format({'Principal (₹)': '₹{:,.2f}', 'Maturity Amt (₹)': '₹{:,.2f}'}), use_container_width=True)
        else:
            st.info("No Fixed Deposit accounts found.")
    st.markdown('</div>', unsafe_allow_html=True)

def rd_accounts_module():
    st.markdown('<div class="section-card"><h3>🔄 Recurring Deposit (RD) Module</h3>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["Create New Recurring Deposit", "Existing RD Accounts"])
    
    with t1:
        conn = get_db()
        custs = conn.execute("SELECT id, customer_id, first_name||' '||last_name FROM customers WHERE kyc_status='VERIFIED'").fetchall()
        conn.close()
        
        if not custs:
            st.warning("No verified customers available to open an RD.")
        else:
            with st.form("rd_creation_form"):
                cust_dict = {f"{c[1]} - {c[2]}": c[0] for c in custs}
                sel_cust = st.selectbox("Select Customer", options=list(cust_dict.keys()), key="rd_cust")
                monthly_amt = st.number_input("Monthly Installment Amount (₹)", min_value=500.00, step=500.00, value=5000.00, key="rd_monthly")
                tenor_months = st.number_input("Tenor (in Months)", min_value=6, max_value=120, value=12, key="rd_tenor")
                interest_rate = st.number_input("Interest Rate (% p.a.)", min_value=0.1, max_value=20.0, value=6.0, step=0.1, key="rd_rate")
                
                maturity_amt = calculate_rd_maturity(monthly_amt, interest_rate, tenor_months)
                maturity_dt = date.today() + timedelta(days=int(tenor_months * 30.44))
                
                st.info(f"📅 **Maturity Date:** {maturity_dt.strftime('%d-%b-%Y')} &nbsp;|&nbsp; 💰 **Maturity Value:** ₹{maturity_amt:,.2f}")
                
                if st.form_submit_button("Create Recurring Deposit Account", type="primary", use_container_width=True):
                    cid = cust_dict[sel_cust]
                    conn = get_db()
                    acno = generate_account_number('RD')
                    
                    conn.execute("INSERT INTO accounts (account_number, customer_id, account_type, balance, status, interest_rate, tenor_months, monthly_installment, maturity_date, maturity_amount) VALUES (?,?,'RD',?,'ACTIVE',?,?,?,?,?)", (acno, cid, monthly_amt, interest_rate, tenor_months, monthly_amt, maturity_dt, maturity_amt))
                    
                    jvn = generate_voucher_number('JOURNAL')
                    conn.execute("INSERT INTO journal_vouchers (voucher_number, voucher_date, description, total_amount, status, created_by) VALUES (?,?,?,?,'POSTED',?)", (jvn, date.today(), f"Recurring Deposit Opening {acno}", monthly_amt, st.session_state.user['id']))
                    jid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?,'Cash',?,0,?)", (jid, monthly_amt, "RD 1st Installment Cash"))
                    conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?,'Recurring Deposit Control Account',0,?,?)", (jid, monthly_amt, f"RD A/C {acno}"))
                    
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Recurring Deposit successfully created! Account Number: {acno}")
                    st.rerun()
                    
    with t2:
        conn = get_db()
        rds = conn.execute("SELECT a.account_number, c.first_name||' '||c.last_name, a.monthly_installment, a.interest_rate, a.tenor_months, a.maturity_date, a.maturity_amount, a.status FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='RD'").fetchall()
        conn.close()
        if rds:
            df = pd.DataFrame(rds, columns=['A/C Number', 'Customer Name', 'Monthly Installment (₹)', 'Rate (%)', 'Tenor (Mo)', 'Maturity Date', 'Maturity Amt (₹)', 'Status'])
            st.dataframe(df.style.format({'Monthly Installment (₹)': '₹{:,.2f}', 'Maturity Amt (₹)': '₹{:,.2f}'}), use_container_width=True)
        else:
            st.info("No Recurring Deposit accounts found.")
    st.markdown('</div>', unsafe_allow_html=True)

def transactions_module():
    st.markdown('<div class="section-card"><h3>💳 Cashier / Deposit & Withdrawal</h3>', unsafe_allow_html=True)
    conn = get_db()
    accs = conn.execute("SELECT a.id, a.account_number, a.account_type, c.first_name||' '||c.last_name, a.balance FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.status='ACTIVE'").fetchall()
    conn.close()
    
    if not accs:
        st.warning("No active accounts available.")
        return
        
    with st.form("txn_form"):
        acc_dict = {f"[{r[2]}] {r[3]} (A/C: {r[1]}) - Bal: ₹{r[4]:,.2f}": r[0] for r in accs}
        sel_acc = st.selectbox("Select Account", options=list(acc_dict.keys()))
        t_type = st.radio("Transaction Type", ["DEPOSIT", "WITHDRAWAL"], horizontal=True)
        amount = st.number_input("Amount (₹)", min_value=1.00, step=100.00)
        desc = st.text_input("Narration / Description", value="Cash counter transaction")
        
        if st.form_submit_button("Process Transaction", type="primary", use_container_width=True):
            aid = acc_dict[sel_acc]
            conn = get_db()
            curr_bal = conn.execute("SELECT balance FROM accounts WHERE id=?", (aid,)).fetchone()[0]
            
            if t_type == "WITHDRAWAL" and curr_bal < amount:
                st.error("❌ Insufficient account balance.")
            else:
                new_bal = curr_bal + amount if t_type == "DEPOSIT" else curr_bal - amount
                txn_id = generate_id('TXN')
                vvn = generate_voucher_number('RECEIPT' if t_type == 'DEPOSIT' else 'PAYMENT')
                
                conn.execute("UPDATE accounts SET balance=? WHERE id=?", (new_bal, aid))
                conn.execute("INSERT INTO transactions (transaction_id, account_id, transaction_type, amount, balance_after, description, reference_type, voucher_type, voucher_number, created_by) VALUES (?,?,?,?,?,?,'CASH','CASH',?,?)", (txn_id, aid, t_type, amount, new_bal, desc, vvn, st.session_state.user['id']))
                
                conn.commit()
                conn.close()
                st.success(f"✅ Successful {t_type}! New Balance: ₹{new_bal:,.2f}")
    st.markdown('</div>', unsafe_allow_html=True)

def journal_vouchers_module():
    st.markdown('<div class="section-card"><h3>📝 Journal Vouchers</h3>', unsafe_allow_html=True)
    st.info("General ledger and journal entries system is online.")
    st.markdown('</div>', unsafe_allow_html=True)

def trial_balance_module():
    st.markdown('<div class="section-card"><h3>⚖️ Enterprise Trial Balance Report</h3>', unsafe_allow_html=True)
    conn = get_db()
    entries = conn.execute("SELECT account_head, SUM(debit_amount), SUM(credit_amount) FROM journal_entries GROUP BY account_head ORDER BY account_head").fetchall()
    conn.close()
    
    if not entries:
        st.info("No accounting journal entries found.")
    else:
        tb_rows = []
        tot_dr = 0.0
        tot_cr = 0.0
        
        for head, dr, cr in entries:
            dr = dr or 0.0
            cr = cr or 0.0
            net = dr - cr
            net_dr = net if net > 0 else 0.0
            net_cr = abs(net) if net < 0 else 0.0
            tot_dr += net_dr
            tot_cr += net_cr
            tb_rows.append({
                "Account Head": head,
                "Total Debit (₹)": dr,
                "Total Credit (₹)": cr,
                "Net Debit (₹)": net_dr,
                "Net Credit (₹)": net_cr
            })
            
        df_tb = pd.DataFrame(tb_rows)
        st.dataframe(df_tb.style.format({
            "Total Debit (₹)": "₹{:,.2f}",
            "Total Credit (₹)": "₹{:,.2f}",
            "Net Debit (₹)": "₹{:,.2f}",
            "Net Credit (₹)": "₹{:,.2f}"
        }), use_container_width=True)
        
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Total Net Debits", f"₹{tot_dr:,.2f}")
        with c2: st.metric("Total Net Credits", f"₹{tot_cr:,.2f}")
        with c3:
            diff = abs(tot_dr - tot_cr)
            if diff < 0.01:
                st.success("✅ Books Balanced Perfectly")
            else:
                st.error(f"❌ Imbalance: ₹{diff:,.2f}")
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == '__main__':
    main()








