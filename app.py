# 🏦 ENTERPRISE CORE BANKING SYSTEM - AUTO-MIGRATION & FINANCIAL STATEMENTS
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
import uuid
import hashlib
import os

# ==================== DATABASE INITIALIZATION & MIGRATION ====================
def init_database():
    conn = sqlite3.connect('enterprise_banking_system.db')
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
        pan_document TEXT,
        aadhar_document TEXT,
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
        loan_amount DECIMAL(15,2) DEFAULT 0.00,
        emi_amount DECIMAL(15,2) DEFAULT 0.00,
        maturity_date DATE,
        maturity_amount DECIMAL(15,2) DEFAULT 0.00,
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
        voucher_number TEXT, 
        created_by INTEGER, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
        FOREIGN KEY (account_id) REFERENCES accounts (id), 
        FOREIGN KEY (created_by) REFERENCES users (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS ledger_heads (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        head_name TEXT UNIQUE NOT NULL,
        category TEXT NOT NULL
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS journal_vouchers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        voucher_number TEXT UNIQUE NOT NULL, 
        voucher_date DATE NOT NULL, 
        description TEXT, 
        total_amount DECIMAL(15,2) NOT NULL, 
        status TEXT DEFAULT 'POSTED', 
        created_by INTEGER, 
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
    
    conn.commit()
    
    # Safe Schema Migration for existing databases
    c.execute("PRAGMA table_info(customers)")
    cust_cols = [col[1] for col in c.fetchall()]
    if cust_cols:
        if 'pan_document' not in cust_cols:
            c.execute("ALTER TABLE customers ADD COLUMN pan_document TEXT")
        if 'aadhar_document' not in cust_cols:
            c.execute("ALTER TABLE customers ADD COLUMN aadhar_document TEXT")
        conn.commit()
        
    # Seed default accounting chart of accounts
    default_heads = [
        ('Cash', 'Asset'), ('Bank Main Clearing', 'Asset'), ('Savings Bank Control Account', 'Liability'), 
        ('Fixed Deposit Control Account', 'Liability'), ('Recurring Deposit Control Account', 'Liability'),
        ('Loan Asset Portfolio', 'Asset'), ('Interest Paid on SB', 'Expense'), ('Interest Paid on FD', 'Expense'),
        ('Interest Paid on RD', 'Expense'), ('Interest Income on Loans', 'Income'), ('Fee & Commission Income', 'Income'), 
        ('Salary Expense', 'Expense'), ('Rent & Utilities Expense', 'Expense'), ('Capital Account', 'Equity')
    ]
    for h, cat in default_heads:
        c.execute("INSERT OR IGNORE INTO ledger_heads (head_name, category) VALUES (?, ?)", (h, cat))
        
    conn.commit()
    
    # Auto-seed demo data if customers table is empty
    if c.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0:
        seed_demo_data(c, conn)
        
    conn.close()

def seed_demo_data(c, conn):
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", ('admin', hashlib.sha256('admin123'.encode()).hexdigest(), 'admin'))
    admin_id = c.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
    
    c.execute("""INSERT INTO customers (customer_id, first_name, last_name, date_of_birth, email, phone, address, city, state, pincode, pan_number, aadhar_number, kyc_status) 
                  VALUES ('CUST2026001', 'Aarav', 'Sharma', '1992-05-14', 'aarav.sharma@example.com', '9876543210', 'MG Road', 'Mumbai', 'Maharashtra', '400001', 'ABCDE1234F', '912345678901', 'VERIFIED')""")
    c1_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    c.execute("""INSERT INTO customers (customer_id, first_name, last_name, date_of_birth, email, phone, address, city, state, pincode, pan_number, aadhar_number, kyc_status) 
                  VALUES ('CUST2026002', 'Priya', 'Nair', '1988-11-20', 'priya.nair@example.com', '9811223344', 'Indiranagar', 'Bangalore', 'Karnataka', '560038', 'FGHIJ5678K', '987654321098', 'VERIFIED')""")
    c2_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    c.execute("INSERT INTO accounts (account_number, customer_id, account_type, balance, interest_rate, status) VALUES ('100202601', ?, 'SB', 45000.00, 3.5, 'ACTIVE')", (c1_id,))
    c.execute("INSERT INTO accounts (account_number, customer_id, account_type, balance, interest_rate, status, tenor_months, maturity_date, maturity_amount) VALUES ('300202601', ?, 'FD', 100000.00, 6.5, 'ACTIVE', 12, '2027-07-22', 106718.00)", (c1_id,))
    c.execute("INSERT INTO accounts (account_number, customer_id, account_type, balance, interest_rate, status, tenor_months, loan_amount, emi_amount) VALUES ('500202601', ?, 'LOAN', 250000.00, 8.5, 'ACTIVE', 60, 250000.00, 5133.00)", (c2_id,))
    
    vouchers = [
        ('RCT202607221001', '2026-07-01', 'Initial Capital Contribution', 500000.00, [('Cash', 500000.00, 0.0), ('Capital Account', 0.0, 500000.00)]),
        ('RCT202607221002', '2026-07-05', 'Savings Bank Deposits Control', 45000.00, [('Cash', 45000.00, 0.0), ('Savings Bank Control Account', 0.0, 45000.00)]),
        ('RCT202607221003', '2026-07-08', 'Fixed Deposit Received', 100000.00, [('Cash', 100000.00, 0.0), ('Fixed Deposit Control Account', 0.0, 100000.00)]),
        ('PMT202607221004', '2026-07-10', 'Loan Disbursement to Borrower', 250000.00, [('Loan Asset Portfolio', 250000.00, 0.0), ('Bank Main Clearing', 0.0, 250000.00)]),
        ('JNL202607221005', '2026-07-15', 'Monthly Staff Salary Paid', 85000.00, [('Salary Expense', 85000.00, 0.0), ('Cash', 0.0, 85000.00)]),
        ('JNL202607221006', '2026-07-18', 'Office Rent & Utilities Paid', 25000.00, [('Rent & Utilities Expense', 25000.00, 0.0), ('Cash', 0.0, 25000.00)]),
        ('RCT202607221007', '2026-07-20', 'Loan Interest & Processing Fees Collected', 18500.00, [('Cash', 18500.00, 0.0), ('Interest Income on Loans', 0.0, 12500.00), ('Fee & Commission Income', 0.0, 6000.00)])
    ]
    
    for vno, vdate, desc, tot_amt, entries in vouchers:
        c.execute("INSERT INTO journal_vouchers (voucher_number, voucher_date, description, total_amount, status, created_by) VALUES (?,?,?,?,'POSTED',?)", (vno, vdate, desc, tot_amt, admin_id))
        jid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        for head, dr, cr in entries:
            c.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?,?,?,?,?)", (jid, head, dr, cr, desc))
            
    conn.commit()

# ==================== UTILITY FUNCTIONS ====================
def get_db(): return sqlite3.connect('enterprise_banking_system.db')
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()
def generate_id(p): return f"{p}{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4]}"
def generate_account_number(t): 
    prefix = {'SB': '100', 'FD': '300', 'RD': '400', 'LOAN': '500'}.get(t, '900')
    return f"{prefix}{datetime.now().strftime('%y%m%d')}{str(uuid.uuid4().int)[:6]}"
def generate_voucher_number(v): return f"{'PMT' if v=='PAYMENT' else 'RCT' if v=='RECEIPT' else 'JNL'}{datetime.now().strftime('%Y%m%d%H%M')}{str(uuid.uuid4().int)[:4]}"

def login_user(u, p):
    conn = get_db()
    user = conn.cursor().execute("SELECT * FROM users WHERE username=? AND password=? AND is_active=1", (u, hash_password(p))).fetchone()
    conn.close()
    return user

def calculate_fd_maturity(principal, rate, months):
    years = months / 12.0
    maturity = principal * ((1 + (rate / 400.0)) ** (4 * years))
    return round(maturity, 2)

def calculate_rd_maturity(monthly_amt, rate, months):
    total_deposit = monthly_amt * months
    interest = monthly_amt * (months * (months + 1) / 2.0) * (rate / 1200.0)
    return round(total_deposit + interest, 2)

def calculate_loan_emi(principal, rate_annual, months):
    if rate_annual == 0:
        return round(principal / months, 2)
    r = rate_annual / (12 * 100)
    emi = principal * r * ((1 + r)**months) / (((1 + r)**months) - 1)
    return round(emi, 2)

# ==================== STYLING & UI CONFIG ====================
def load_enterprise_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    html, body, [class*="css"] { background-color: #f8fafc; }
    .topbar {
        background: linear-gradient(135deg, #0f172a, #1e293b, #334155);
        color: white; padding: 1.2rem 2.5rem; border-radius: 14px;
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 2rem; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15);
    }
    .topbar h1 { margin: 0; font-size: 1.6rem; font-weight: 800; color: #ffffff !important; }
    .topbar .user { font-size: 0.9rem; font-weight: 500; background: rgba(255,255,255,0.15); padding: 0.5rem 1.2rem; border-radius: 20px; }
    .dash-card {
        background: white; border-radius: 16px; padding: 1.8rem 1.2rem; text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 1rem; border: 1px solid #e2e8f0;
    }
    .dash-card h2 { font-size: 2rem; margin: 0.5rem 0; font-weight: 800; color: #0f172a; }
    .dash-card p { margin: 0; font-size: 0.8rem; color: #64748b; font-weight: 700; text-transform: uppercase; }
    .section-card {
        background: white; border-radius: 16px; padding: 2rem; margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0;
    }
    .section-card h3 {
        font-size: 1.2rem; font-weight: 700; color: #1e293b; margin-bottom: 1.5rem;
        padding-bottom: 1rem; border-bottom: 2px solid #f1f5f9;
    }
    [data-testid="stSidebar"] { background-color: #0f172a !important; }
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
    st.set_page_config(page_title="Enterprise Core Banking System", page_icon="🏦", layout="wide", initial_sidebar_state="expanded")
    init_database()
    
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
            'loan_accounts': '🏠 Loan Accounts',
            'transactions': '💳 Cashier & Teller',
            'journal_vouchers': '📝 Journal Vouchers',
            'financial_reports': '📈 Financial Statements'
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
    elif page == 'loan_accounts': loan_accounts_module()
    elif page == 'transactions': transactions_module()
    elif page == 'journal_vouchers': journal_vouchers_module()
    elif page == 'financial_reports': financial_reports_module()

# ==================== MODULES ====================

def dashboard():
    conn = get_db()
    cust_count = conn.execute("SELECT COUNT(*) FROM customers WHERE kyc_status!='DEACTIVATED'").fetchone()[0]
    sb_count = conn.execute("SELECT COUNT(*) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
    fd_count = conn.execute("SELECT COUNT(*) FROM accounts WHERE account_type='FD' AND status='ACTIVE'").fetchone()[0]
    loan_count = conn.execute("SELECT COUNT(*) FROM accounts WHERE account_type='LOAN' AND status='ACTIVE'").fetchone()[0]
    total_deposits = conn.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE account_type IN ('SB','FD','RD') AND status='ACTIVE'").fetchone()[0]
    conn.close()
    
    cols = st.columns(4)
    with cols[0]: st.markdown(f'<div class="dash-card"><h2>{cust_count}</h2><p>Total Customers</p></div>', unsafe_allow_html=True)
    with cols[1]: st.markdown(f'<div class="dash-card"><h2>{sb_count}</h2><p>Active SB A/Cs</p></div>', unsafe_allow_html=True)
    with cols[2]: st.markdown(f'<div class="dash-card"><h2>{fd_count} / {loan_count}</h2><p>FD / Active Loans</p></div>', unsafe_allow_html=True)
    with cols[3]: st.markdown(f'<div class="dash-card"><h2>₹{total_deposits:,.2f}</h2><p>Total Deposit Portfolio</p></div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    conn = get_db()
    c1, c2 = st.columns([1.5, 1])
    with c1:
        st.markdown('<div class="section-card"><h3>📋 Recent Journal Entries & Financial Activity</h3>', unsafe_allow_html=True)
        txns = conn.execute("SELECT voucher_number, voucher_date, description, total_amount FROM journal_vouchers ORDER BY voucher_date DESC LIMIT 6").fetchall()
        if txns:
            st.dataframe(pd.DataFrame(txns, columns=['Voucher No', 'Date', 'Description', 'Amount']).style.format({'Amount': '₹{:,.2f}'}), use_container_width=True)
        else:
            st.info("No journal records found.")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="section-card"><h3>⚡ Quick Management Actions</h3>', unsafe_allow_html=True)
        if st.button("➕ Register New Customer", use_container_width=True, type="primary"):
            st.session_state.page = 'customers'; st.rerun()
        if st.button("📈 View Financial Statements", use_container_width=True):
            st.session_state.page = 'financial_reports'; st.rerun()
        if st.button("🔒 Open Fixed Deposit (FD)", use_container_width=True):
            st.session_state.page = 'fd_accounts'; st.rerun()
        if st.button("🏠 Issue New Loan Account", use_container_width=True):
            st.session_state.page = 'loan_accounts'; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

def customers_module():
    st.markdown('<div class="section-card"><h3>👥 Customer Registration & KYC Document Upload</h3>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["Register Customer & Upload KYC", "View & Verify KYC Documents"])
    
    with t1:
        with st.form("cust_reg"):
            c1, c2 = st.columns(2)
            with c1:
                fn = st.text_input("First Name*")
                ln = st.text_input("Last Name*")
                dob = st.date_input("Date of Birth*", min_value=date(1900,1,1), max_value=date.today())
                email = st.text_input("Email Address*")
                phone = st.text_input("Phone Number*")
            with c2:
                pan = st.text_input("PAN Number*")
                aadhar = st.text_input("Aadhar Number / Gov ID*")
                addr = st.text_area("Address")
                city = st.text_input("City")
                state = st.text_input("State")
                pin = st.text_input("PIN Code")
            
            st.markdown("---")
            st.markdown("#### 📂 KYC Document Uploads")
            col_up1, col_up2 = st.columns(2)
            with col_up1:
                pan_file = st.file_uploader("Upload PAN Card (PDF, JPG, PNG)", type=['pdf', 'jpg', 'png'], key="pan_upload")
            with col_up2:
                aadhar_file = st.file_uploader("Upload Aadhar Card (PDF, JPG, PNG)", type=['pdf', 'jpg', 'png'], key="aadhar_upload")
                
            if st.form_submit_button("Submit Registration & Upload KYC", type="primary", use_container_width=True):
                if not all([fn, ln, email, phone, pan, aadhar]):
                    st.error("Please fill all required (*) text fields.")
                else:
                    try:
                        os.makedirs("kyc_docs", exist_ok=True)
                        pan_filename = None
                        aadhar_filename = None
                        
                        if pan_file is not None:
                            pan_filename = f"kyc_docs/PAN_{pan}_{pan_file.name}"
                            with open(pan_filename, "wb") as f: f.write(pan_file.getbuffer())
                                
                        if aadhar_file is not None:
                            aadhar_filename = f"kyc_docs/AADHAR_{aadhar[-4:]}_{aadhar_file.name}"
                            with open(aadhar_filename, "wb") as f: f.write(aadhar_file.getbuffer())

                        conn = get_db()
                        cid = generate_id('CUST')
                        conn.execute("""INSERT INTO customers (customer_id, first_name, last_name, date_of_birth, email, phone, address, city, state, pincode, pan_number, aadhar_number, pan_document, aadhar_document) 
                                      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", 
                                     (cid, fn, ln, dob, email, phone, addr, city, state, pin, pan, aadhar, pan_filename, aadhar_filename))
                        conn.commit(); conn.close()
                        st.success(f"✅ Customer successfully registered with documents! ID: {cid}")
                    except sqlite3.IntegrityError:
                        st.error("❌ Customer with this Email, PAN, or Aadhar already exists.")
                        
    with t2:
        conn = get_db()
        custs = conn.execute("SELECT id, customer_id, first_name||' '||last_name, email, phone, pan_number, aadhar_number, pan_document, aadhar_document, kyc_status FROM customers WHERE kyc_status!='DEACTIVATED'").fetchall()
        conn.close()
        if custs:
            df = pd.DataFrame(custs, columns=['DB ID', 'Customer ID', 'Name', 'Email', 'Phone', 'PAN', 'Aadhar', 'PAN Doc', 'Aadhaar Doc', 'KYC Status'])
            st.dataframe(df, use_container_width=True)
            
            sel_id = st.selectbox("Select Customer to Review Documents & Verify", options=[c[0] for c in custs], format_func=lambda x: next(f"{c[1]} - {c[2]} ({c[9]})" for c in custs if c[0] == x))
            
            selected_cust = next(c for c in custs if c[0] == sel_id)
            st.markdown(f"#### Reviewing Documents for: **{selected_cust[2]}**")
            dc1, dc2 = st.columns(2)
            with dc1:
                st.write(f"**PAN Number:** {selected_cust[5]}")
                if selected_cust[7] and os.path.exists(selected_cust[7]):
                    st.success("✅ PAN Document Uploaded")
                    st.download_button("Download PAN Document", data=open(selected_cust[7], "rb").read(), file_name=os.path.basename(selected_cust[7]), key=f"dl_pan_{sel_id}")
                else:
                    st.info("📄 Demo Account (Sample document verified in system)")
            with dc2:
                st.write(f"**Aadhaar Number:** {selected_cust[6]}")
                if selected_cust[8] and os.path.exists(selected_cust[8]):
                    st.success("✅ Aadhaar Document Uploaded")
                    st.download_button("Download Aadhaar Document", data=open(selected_cust[8], "rb").read(), file_name=os.path.basename(selected_cust[8]), key=f"dl_aadhaar_{sel_id}")
                else:
                    st.info("📄 Demo Account (Sample document verified in system)")
            
            st.markdown("<br>", unsafe_allow_html=True)
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
    st.markdown('<div class="section-card"><h3>💰 Savings Bank Accounts Portfolio</h3>', unsafe_allow_html=True)
    conn = get_db()
    accs = conn.execute("SELECT a.account_number, c.first_name||' '||c.last_name, a.balance, a.interest_rate, a.status FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB'").fetchall()
    conn.close()
    if accs:
        st.dataframe(pd.DataFrame(accs, columns=['Account Number', 'Customer Name', 'Balance (₹)', 'Interest Rate (%)', 'Status']).style.format({'Balance (₹)': '₹{:,.2f}'}), use_container_width=True)
    else:
        st.info("No Savings Bank accounts found.")
    st.markdown('</div>', unsafe_allow_html=True)

def fd_accounts_module():
    st.markdown('<div class="section-card"><h3>🔒 Fixed Deposit (FD) Management</h3>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["Create New Fixed Deposit", "Existing FD Accounts"])
    
    with t1:
        conn = get_db()
        custs = conn.execute("SELECT id, customer_id, first_name||' '||last_name FROM customers WHERE kyc_status='VERIFIED'").fetchall()
        conn.close()
        
        with st.form("fd_creation_form"):
            cust_dict = {f"{c[1]} - {c[2]}": c[0] for c in custs} if custs else {}
            sel_cust = st.selectbox("Select Customer", options=list(cust_dict.keys()) if cust_dict else ["No verified customers"])
            principal = st.number_input("Deposit Principal Amount (₹)", min_value=1000.00, step=1000.00, value=50000.00)
            tenor_months = st.number_input("Tenor (in Months)", min_value=1, max_value=120, value=12)
            interest_rate = st.number_input("Interest Rate (% p.a.)", min_value=0.1, max_value=20.0, value=6.5, step=0.1)
            
            maturity_amt = calculate_fd_maturity(principal, interest_rate, tenor_months)
            maturity_dt = date.today() + timedelta(days=int(tenor_months * 30.44))
            
            st.info(f"📅 **Estimated Maturity Date:** {maturity_dt.strftime('%d-%b-%Y')} &nbsp;|&nbsp; 💰 **Maturity Amount:** ₹{maturity_amt:,.2f}")
            
            if st.form_submit_button("Create Fixed Deposit Account", type="primary", use_container_width=True):
                if not cust_dict:
                    st.error("Please verify a customer first.")
                else:
                    cid = cust_dict[sel_cust]
                    conn = get_db()
                    acno = generate_account_number('FD')
                    conn.execute("INSERT INTO accounts (account_number, customer_id, account_type, balance, status, interest_rate, tenor_months, maturity_date, maturity_amount) VALUES (?,?,'FD',?,'ACTIVE',?,?,?,?)", (acno, cid, principal, interest_rate, tenor_months, maturity_dt, maturity_amt))
                    
                    jvn = generate_voucher_number('JOURNAL')
                    conn.execute("INSERT INTO journal_vouchers (voucher_number, voucher_date, description, total_amount, status, created_by) VALUES (?,?,?,?,'POSTED',?)", (jvn, date.today(), f"Fixed Deposit Creation {acno}", principal, st.session_state.user['id']))
                    jid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?,'Cash',?,0,?)", (jid, principal, "FD Opening Cash"))
                    conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?,'Fixed Deposit Control Account',0,?,?)", (jid, principal, f"FD A/C {acno}"))
                    
                    conn.commit(); conn.close()
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
    st.markdown('<div class="section-card"><h3>🔄 Recurring Deposit (RD) Management</h3>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["Create New Recurring Deposit", "Existing RD Accounts"])
    
    with t1:
        conn = get_db()
        custs = conn.execute("SELECT id, customer_id, first_name||' '||last_name FROM customers WHERE kyc_status='VERIFIED'").fetchall()
        conn.close()
        
        with st.form("rd_creation_form"):
            cust_dict = {f"{c[1]} - {c[2]}": c[0] for c in custs} if custs else {}
            sel_cust = st.selectbox("Select Customer", options=list(cust_dict.keys()) if cust_dict else ["No verified customers"], key="rd_cust")
            monthly_amt = st.number_input("Monthly Installment Amount (₹)", min_value=500.00, step=500.00, value=5000.00, key="rd_monthly")
            tenor_months = st.number_input("Tenor (in Months)", min_value=6, max_value=120, value=12, key="rd_tenor")
            interest_rate = st.number_input("Interest Rate (% p.a.)", min_value=0.1, max_value=20.0, value=6.0, step=0.1, key="rd_rate")
            
            maturity_amt = calculate_rd_maturity(monthly_amt, interest_rate, tenor_months)
            maturity_dt = date.today() + timedelta(days=int(tenor_months * 30.44))
            
            st.info(f"📅 **Maturity Date:** {maturity_dt.strftime('%d-%b-%Y')} &nbsp;|&nbsp; 💰 **Maturity Value:** ₹{maturity_amt:,.2f}")
            
            if st.form_submit_button("Create Recurring Deposit Account", type="primary", use_container_width=True):
                if not cust_dict:
                    st.error("Please verify a customer first.")
                else:
                    cid = cust_dict[sel_cust]
                    conn = get_db()
                    acno = generate_account_number('RD')
                    conn.execute("INSERT INTO accounts (account_number, customer_id, account_type, balance, status, interest_rate, tenor_months, monthly_installment, maturity_date, maturity_amount) VALUES (?,?,'RD',?,'ACTIVE',?,?,?,?,?)", (acno, cid, monthly_amt, interest_rate, tenor_months, monthly_amt, maturity_dt, maturity_amt))
                    
                    jvn = generate_voucher_number('JOURNAL')
                    conn.execute("INSERT INTO journal_vouchers (voucher_number, voucher_date, description, total_amount, status, created_by) VALUES (?,?,?,?,'POSTED',?)", (jvn, date.today(), f"Recurring Deposit Opening {acno}", monthly_amt, st.session_state.user['id']))
                    jid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?,'Cash',?,0,?)", (jid, monthly_amt, "RD 1st Installment Cash"))
                    conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?,'Recurring Deposit Control Account',0,?,?)", (jid, monthly_amt, f"RD A/C {acno}"))
                    
                    conn.commit(); conn.close()
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

def loan_accounts_module():
    st.markdown('<div class="section-card"><h3>🏠 Loan Accounts & EMI Management</h3>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["Disburse New Loan", "Existing Loan Portfolio"])
    
    with t1:
        conn = get_db()
        custs = conn.execute("SELECT id, customer_id, first_name||' '||last_name FROM customers WHERE kyc_status='VERIFIED'").fetchall()
        conn.close()
        
        with st.form("loan_creation_form"):
            cust_dict = {f"{c[1]} - {c[2]}": c[0] for c in custs} if custs else {}
            sel_cust = st.selectbox("Select Borrower", options=list(cust_dict.keys()) if cust_dict else ["No verified customers"], key="loan_cust")
            loan_amt = st.number_input("Loan Principal Amount (₹)", min_value=10000.00, step=10000.00, value=250000.00, key="loan_amt")
            tenor_months = st.number_input("Tenor (in Months)", min_value=6, max_value=360, value=60, key="loan_tenor")
            interest_rate = st.number_input("Interest Rate (% p.a.)", min_value=1.0, max_value=30.0, value=8.5, step=0.1, key="loan_rate")
            
            emi = calculate_loan_emi(loan_amt, interest_rate, tenor_months)
            total_payable = emi * tenor_months
            
            st.info(f"📊 **Calculated Monthly EMI:** ₹{emi:,.2f} &nbsp;|&nbsp; 💰 **Total Repayment Amount:** ₹{total_payable:,.2f}")
            
            if st.form_submit_button("Disburse Loan Account", type="primary", use_container_width=True):
                if not cust_dict:
                    st.error("Please verify a customer first.")
                else:
                    cid = cust_dict[sel_cust]
                    conn = get_db()
                    acno = generate_account_number('LOAN')
                    conn.execute("INSERT INTO accounts (account_number, customer_id, account_type, balance, status, interest_rate, tenor_months, loan_amount, emi_amount) VALUES (?,?,'LOAN',?,'ACTIVE',?,?,?,?)", (acno, cid, loan_amt, interest_rate, tenor_months, loan_amt, emi))
                    
                    jvn = generate_voucher_number('JOURNAL')
                    conn.execute("INSERT INTO journal_vouchers (voucher_number, voucher_date, description, total_amount, status, created_by) VALUES (?,?,?,?,'POSTED',?)", (jvn, date.today(), f"Loan Disbursement {acno}", loan_amt, st.session_state.user['id']))
                    jid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?,'Loan Asset Portfolio',?,0,?)", (jid, loan_amt, f"Loan Disbursement A/C {acno}"))
                    conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?,'Bank Main Clearing',0,?,?)", (jid, loan_amt, "Loan Disbursement Outflow"))
                    
                    conn.commit(); conn.close()
                    st.success(f"✅ Loan successfully disbursed! Account Number: {acno}")
                    st.rerun()
                    
    with t2:
        conn = get_db()
        loans = conn.execute("SELECT a.account_number, c.first_name||' '||c.last_name, a.loan_amount, a.interest_rate, a.tenor_months, a.emi_amount, a.status FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='LOAN'").fetchall()
        conn.close()
        if loans:
            df = pd.DataFrame(loans, columns=['A/C Number', 'Borrower Name', 'Loan Principal (₹)', 'Rate (%)', 'Tenor (Mo)', 'Monthly EMI (₹)', 'Status'])
            st.dataframe(df.style.format({'Loan Principal (₹)': '₹{:,.2f}', 'Monthly EMI (₹)': '₹{:,.2f}'}), use_container_width=True)
        else:
            st.info("No active loan accounts found.")
    st.markdown('</div>', unsafe_allow_html=True)

def transactions_module():
    st.markdown('<div class="section-card"><h3>💳 Teller Cashier Counter (Deposits & Withdrawals)</h3>', unsafe_allow_html=True)
    conn = get_db()
    accs = conn.execute("SELECT a.id, a.account_number, a.account_type, c.first_name||' '||c.last_name, a.balance FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.status='ACTIVE' AND a.account_type='SB'").fetchall()
    conn.close()
    
    if not accs:
        st.warning("No active Savings Bank accounts available.")
        return
        
    with st.form("txn_form"):
        acc_dict = {f"[{r[2]}] {r[3]} (A/C: {r[1]}) - Bal: ₹{r[4]:,.2f}": r[0] for r in accs}
        sel_acc = st.selectbox("Select Account", options=list(acc_dict.keys()))
        t_type = st.radio("Transaction Type", ["DEPOSIT", "WITHDRAWAL"], horizontal=True)
        amount = st.number_input("Amount (₹)", min_value=1.00, step=100.00, value=1000.00)
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
                conn.execute("INSERT INTO transactions (transaction_id, account_id, transaction_type, amount, balance_after, description, reference_type, voucher_number, created_by) VALUES (?,?,?,?,?,?,'CASH',?,?)", (txn_id, aid, t_type, amount, new_bal, desc, vvn, st.session_state.user['id']))
                
                jvn = generate_voucher_number('JOURNAL')
                conn.execute("INSERT INTO journal_vouchers (voucher_number, voucher_date, description, total_amount, status, created_by) VALUES (?,?,?,?,'POSTED',?)", (jvn, date.today(), f"Cashier {t_type} {txn_id}", amount, st.session_state.user['id']))
                jid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                if t_type == 'DEPOSIT':
                    conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?,'Cash',?,0,?)", (jid, amount, "Cash Received"))
                    conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?,'Savings Bank Control Account',0,?,?)", (jid, amount, "SB Deposit Credit"))
                else:
                    conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?,'Savings Bank Control Account',?,0,?)", (jid, amount, "SB Withdrawal Debit"))
                    conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?,'Cash',0,?,?)", (jid, amount, "Cash Paid Out"))

                conn.commit(); conn.close()
                st.success(f"✅ Successful {t_type}! New Balance: ₹{new_bal:,.2f}")
    st.markdown('</div>', unsafe_allow_html=True)

def journal_vouchers_module():
    st.markdown('<div class="section-card"><h3>📝 Double-Entry Journal Vouchers</h3>', unsafe_allow_html=True)
    conn = get_db()
    vouchers = conn.execute("SELECT v.id, v.voucher_number, v.voucher_date, v.description, v.total_amount, u.username FROM journal_vouchers v JOIN users u ON v.created_by=u.id ORDER BY v.voucher_date DESC").fetchall()
    conn.close()
    
    if vouchers:
        df = pd.DataFrame(vouchers, columns=['ID', 'Voucher Number', 'Date', 'Description', 'Total Amount (₹)', 'Created By'])
        st.dataframe(df.style.format({'Total Amount (₹)': '₹{:,.2f}'}), use_container_width=True)
    else:
        st.info("No journal vouchers found.")
    st.markdown('</div>', unsafe_allow_html=True)

def financial_reports_module():
    st.markdown('<div class="section-card"><h3>📈 Comprehensive Financial Statements & Reports</h3>', unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["Trial Balance", "Profit & Loss (Income Statement)", "Balance Sheet"])
    
    conn = get_db()
    heads_df = pd.read_sql("SELECT head_name, category FROM ledger_heads", conn)
    entries = conn.execute("""
        SELECT je.account_head, 
               COALESCE(SUM(je.debit_amount), 0), 
               COALESCE(SUM(je.credit_amount), 0) 
        FROM journal_entries je 
        GROUP BY je.account_head
    """).fetchall()
    conn.close()
    
    head_cat_map = dict(zip(heads_df['head_name'], heads_df['category']))
    report_data = {}
    for head, dr, cr in entries:
        cat = head_cat_map.get(head, 'Asset')
        report_data[head] = {'category': cat, 'debit': dr, 'credit': cr}
        
    with tab1:
        st.markdown("#### ⚖️ Trial Balance Report")
        if not entries:
            st.info("No journal entries recorded for trial balance.")
        else:
            tb_rows = []
            tot_dr, tot_cr = 0.0, 0.0
            for head, data in report_data.items():
                dr, cr = data['debit'], data['credit']
                net = dr - cr
                net_dr = net if net > 0 else 0.0
                net_cr = abs(net) if net < 0 else 0.0
                tot_dr += net_dr
                tot_cr += net_cr
                tb_rows.append({
                    "Account Head": head, 
                    "Category": data['category'],
                    "Total Debit (₹)": dr, 
                    "Total Credit (₹)": cr, 
                    "Net Debit (₹)": net_dr, 
                    "Net Credit (₹)": net_cr
                })
            st.dataframe(pd.DataFrame(tb_rows).style.format({"Total Debit (₹)": "₹{:,.2f}", "Total Credit (₹)": "₹{:,.2f}", "Net Debit (₹)": "₹{:,.2f}", "Net Credit (₹)": "₹{:,.2f}"}), use_container_width=True)
            
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Total Net Debits", f"₹{tot_dr:,.2f}")
            with c2: st.metric("Total Net Credits", f"₹{tot_cr:,.2f}")
            with c3:
                diff = abs(tot_dr - tot_cr)
                if diff < 0.01: st.success("✅ Books Balanced Perfectly")
                else: st.error(f"❌ Imbalance: ₹{diff:,.2f}")
                
    with tab2:
        st.markdown("#### 📊 Profit & Loss Statement (Income Statement)")
        income_rows = []
        expense_rows = []
        total_income = 0.0
        total_expense = 0.0
        
        for head, data in report_data.items():
            cat = data['category']
            if cat == 'Income':
                net_inc = data['credit'] - data['debit']
                total_income += net_inc
                income_rows.append({"Income Head": head, "Amount (₹)": net_inc})
            elif cat == 'Expense':
                net_exp = data['debit'] - data['credit']
                total_expense += net_exp
                expense_rows.append({"Expense Head": head, "Amount (₹)": net_exp})
                
        col_inc, col_exp = st.columns(2)
        with col_inc:
            st.markdown("##### 📥 Incomes & Revenues")
            if income_rows:
                st.dataframe(pd.DataFrame(income_rows).style.format({"Amount (₹)": "₹{:,.2f}"}), use_container_width=True)
            else:
                st.info("No income recorded.")
            st.metric("Total Income", f"₹{total_income:,.2f}")
            
        with col_exp:
            st.markdown("##### 📤 Expenses")
            if expense_rows:
                st.dataframe(pd.DataFrame(expense_rows).style.format({"Amount (₹)": "₹{:,.2f}"}), use_container_width=True)
            else:
                st.info("No expenses recorded.")
            st.metric("Total Expenses", f"₹{total_expense:,.2f}")
            
        st.markdown("---")
        net_profit = total_income - total_expense
        if net_profit >= 0:
            st.success(f"🎉 **Net Profit (YTD):** ₹{net_profit:,.2f}")
        else:
            st.error(f"⚠️ **Net Loss (YTD):** ₹{abs(net_profit):,.2f}")
            
    with tab3:
        st.markdown("#### 🏛️ Balance Sheet Summary")
        asset_rows = []
        liability_rows = []
        equity_rows = []
        
        total_assets = 0.0
        total_liabilities = 0.0
        total_equity = 0.0
        
        for head, data in report_data.items():
            cat = data['category']
            if cat == 'Asset':
                net_val = data['debit'] - data['credit']
                total_assets += net_val
                asset_rows.append({"Asset Head": head, "Amount (₹)": net_val})
            elif cat == 'Liability':
                net_val = data['credit'] - data['debit']
                total_liabilities += net_val
                liability_rows.append({"Liability Head": head, "Amount (₹)": net_val})
            elif cat == 'Equity':
                net_val = data['credit'] - data['debit']
                total_equity += net_val
                equity_rows.append({"Equity Head": head, "Amount (₹)": net_val})
                
        net_profit = total_income - total_expense
        total_equity += net_profit
        equity_rows.append({"Equity Head": "Retained Earnings / Net Profit (YTD)", "Amount (₹)": net_profit})
        
        col_a, col_l = st.columns(2)
        with col_a:
            st.markdown("##### 💼 Assets Portfolio")
            if asset_rows:
                st.dataframe(pd.DataFrame(asset_rows).style.format({"Amount (₹)": "₹{:,.2f}"}), use_container_width=True)
            else:
                st.info("No assets recorded.")
            st.metric("Total Assets", f"₹{total_assets:,.2f}")
            
        with col_l:
            st.markdown("##### 📋 Liabilities & Equity")
            if liability_rows:
                st.markdown("**Liabilities:**")
                st.dataframe(pd.DataFrame(liability_rows).style.format({"Amount (₹)": "₹{:,.2f}"}), use_container_width=True)
            if equity_rows:
                st.markdown("**Equity & Reserves:**")
                st.dataframe(pd.DataFrame(equity_rows).style.format({"Amount (₹)": "₹{:,.2f}"}), use_container_width=True)
                
            total_liab_equity = total_liabilities + total_equity
            st.metric("Total Liabilities & Equity", f"₹{total_liab_equity:,.2f}")
            
        st.markdown("---")
        bs_diff = abs(total_assets - total_liab_equity)
        if bs_diff < 0.01:
            st.success("✅ Balance Sheet Matches (Assets = Liabilities + Equity)")
        else:
            st.error(f"❌ Balance Sheet Imbalance: ₹{bs_diff:,.2f}")
            
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == '__main__':
    main()








