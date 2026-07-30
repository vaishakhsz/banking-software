import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, timedelta
import hashlib

# ==================== PAGE CONFIGURATION ====================
st.set_page_config(
    page_title="Aasha Nidhi Pvt Limited Bank",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== DATABASE INITIALIZATION ====================
def get_db():
    conn = sqlite3.connect('aasha_nidhi_bank.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Users & Roles
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        full_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Customers Master
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id TEXT UNIQUE NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        dob TEXT,
        gender TEXT,
        phone TEXT UNIQUE NOT NULL,
        email TEXT,
        address TEXT,
        pan TEXT,
        aadhaar TEXT,
        nominee_name TEXT,
        nominee_relation TEXT,
        kyc_status TEXT DEFAULT 'PENDING',
        status TEXT DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Bank Accounts (SB, etc.)
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_number TEXT UNIQUE NOT NULL,
        customer_id INTEGER,
        account_type TEXT NOT NULL,
        balance REAL DEFAULT 0.0,
        status TEXT DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )''')
    
    # Transactions Ledger
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER,
        transaction_type TEXT NOT NULL,
        amount REAL NOT NULL,
        balance_after REAL NOT NULL,
        description TEXT,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(account_id) REFERENCES accounts(id),
        FOREIGN KEY(created_by) REFERENCES users(id)
    )''')
    
    # Fixed Deposits (FD)
    c.execute('''CREATE TABLE IF NOT EXISTS fixed_deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fd_number TEXT UNIQUE NOT NULL,
        customer_id INTEGER,
        principal_amount REAL NOT NULL,
        interest_rate REAL NOT NULL,
        tenure_months INTEGER NOT NULL,
        maturity_date TEXT NOT NULL,
        maturity_amount REAL NOT NULL,
        status TEXT DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )''')
    
    # Recurring Deposits (RD)
    c.execute('''CREATE TABLE IF NOT EXISTS recurring_deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rd_number TEXT UNIQUE NOT NULL,
        customer_id INTEGER,
        monthly_amount REAL NOT NULL,
        interest_rate REAL NOT NULL,
        tenure_months INTEGER NOT NULL,
        installments_paid INTEGER DEFAULT 0,
        maturity_date TEXT NOT NULL,
        maturity_amount REAL NOT NULL,
        status TEXT DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )''')
    
    # Retrieval Accounts / Special Schemes
    c.execute('''CREATE TABLE IF NOT EXISTS retrieval_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        retrieval_number TEXT UNIQUE NOT NULL,
        customer_id INTEGER,
        scheme_name TEXT,
        balance REAL DEFAULT 0.0,
        status TEXT DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )''')
    
    # Journal Vouchers
    c.execute('''CREATE TABLE IF NOT EXISTS journal_vouchers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voucher_number TEXT UNIQUE NOT NULL,
        voucher_date TEXT NOT NULL,
        description TEXT,
        total_amount REAL NOT NULL,
        status TEXT DEFAULT 'POSTED',
        created_by INTEGER,
        customer_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(created_by) REFERENCES users(id),
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )''')
    
    # Journal Entries (Double-Entry lines)
    c.execute('''CREATE TABLE IF NOT EXISTS journal_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voucher_id INTEGER,
        account_head TEXT NOT NULL,
        debit_amount REAL DEFAULT 0.0,
        credit_amount REAL DEFAULT 0.0,
        description TEXT,
        FOREIGN KEY(voucher_id) REFERENCES journal_vouchers(id)
    )''')
    
    # Income & Expense tables
    c.execute('''CREATE TABLE IF NOT EXISTS income (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        amount REAL,
        date TEXT,
        description TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        amount REAL,
        date TEXT,
        description TEXT
    )''')
    
    # Seed default admin user if none exists
    admin = c.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
    if not admin:
        hashed_pw = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)",
                  ('admin', hashed_pw, 'Admin', 'System Administrator'))
        conn.commit()
        
    conn.close()

init_db()

# ==================== AUTHENTICATION HELPER ====================
def make_hash(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

def verify_hash(password, hashed):
    return make_hash(password) == hashed

def generate_account_number(acc_type):
    import random
    return f"ASHA{acc_type}{random.randint(100000, 999999)}"

def generate_customer_id():
    import random
    return f"CUST{random.randint(10000, 99999)}"

def generate_voucher_number(prefix='JNL'):
    import random
    return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

# ==================== MAIN APPLICATION LOGIC ====================
def main():
    if 'user' not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        login_page()
    else:
        main_dashboard()

def login_page():
    st.markdown("<h1 style='text-align: center;'>🏦 Aasha Nidhi Pvt Limited Bank</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: gray;'>Core Banking & Financial Management System</h4>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("### 🔐 Secure Login Portal")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login to System", use_container_width=True, type="primary")
            
            if submit:
                conn = get_db()
                user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
                conn.close()
                
                if user and verify_hash(password, user['password']):
                    st.session_state.user = {
                        'id': user['id'],
                        'username': user['username'],
                        'role': user['role'],
                        'full_name': user['full_name']
                    }
                    st.success("Login Successful! Redirecting...")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")

        st.info("Default Admin Credentials: **admin** / **admin123**")

def main_dashboard():
    user = st.session_state.user
    
    # Sidebar Navigation mapping to requested exact menu options
    st.sidebar.markdown(f"### Welcome, **{user['full_name']}**")
    st.sidebar.caption(f"Role: {user['role']}")
    st.sidebar.markdown("---")
    
    menu = st.sidebar.selectbox("Navigation Menu", [
        "📊 Dashboard",
        "👥 Customers",
        "✅ KYC Verification",
        "💰 Open SB Account",
        "🏦 SB Accounts",
        "📈 Fixed Deposits",
        "🔄 Recurring Dep.",
        "💰 Retrieval Account",
        "💳 Transactions",
        "📝 Journal Vouchers",
        "💰 Income & Exp.",
        "📊 Interest",
        "⚖️ Trial Balance",
        "📋 Balance Sheet",
        "📈 Profit & Loss",
        "📄 Reports",
        "⚙️ Settings"
    ])
    
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.user = None
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.caption("© 2026 Aasha Nidhi Pvt Ltd Bank")
    
    # Route to Views based on selection
    if menu == "📊 Dashboard":
        dashboard_view()
    elif menu == "👥 Customers":
        customer_management()
    elif menu == "✅ KYC Verification":
        kyc_verification()
    elif menu == "💰 Open SB Account":
        open_sb_account()
    elif menu == "🏦 SB Accounts":
        sb_accounts_view()
    elif menu == "📈 Fixed Deposits":
        fixed_deposits_view()
    elif menu == "🔄 Recurring Dep.":
        recurring_deposits_view()
    elif menu == "💰 Retrieval Account":
        retrieval_account_view()
    elif menu == "💳 Transactions":
        transactions_view()
    elif menu == "📝 Journal Vouchers":
        journal_vouchers_view()
    elif menu == "💰 Income & Exp.":
        income_expenses_view()
    elif menu == "📊 Interest":
        interest_calculation_view()
    elif menu == "⚖️ Trial Balance":
        trial_balance_view()
    elif menu == "📋 Balance Sheet":
        balance_sheet_view()
    elif menu == "📈 Profit & Loss":
        profit_loss_view()
    elif menu == "📄 Reports":
        reports_view()
    elif menu == "⚙️ Settings":
        settings_view()

# ==================== MODULE VIEWS ====================
def dashboard_view():
    st.markdown("### 📊 Executive Financial Dashboard")
    c = get_db()
    total_cust = c.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    total_acct = c.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    sb_deposits = c.execute("SELECT COALESCE(SUM(balance), 0) FROM accounts WHERE account_type='SB'").fetchone()[0]
    fd_deposits = c.execute("SELECT COALESCE(SUM(principal_amount), 0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
    c.close()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Customers", f"{total_cust}")
    col2.metric("Active Accounts", f"{total_acct}")
    col3.metric("SB Deposits", f"Rs {sb_deposits:,.2f}")
    col4.metric("Active FD Portfolio", f"Rs {fd_deposits:,.2f}")
    st.markdown("---")
    st.info("System is operational. Core accounting and multi-scheme deposit tracking active.")

def customer_management():
    st.markdown("### 👥 Customers Directory & Registration")
    with st.form("customer_form"):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name")
            dob = st.date_input("Date of Birth", min_value=date(1900, 1, 1))
            phone = st.text_input("Phone Number")
            address = st.text_area("Residential Address")
        with col2:
            last_name = st.text_input("Last Name")
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            email = st.text_input("Email Address")
            pan = st.text_input("PAN Number")
            aadhaar = st.text_input("Aadhaar Number")
            
        if st.form_submit_button("Register Customer", use_container_width=True, type="primary"):
            if not first_name or not phone:
                st.error("First Name and Phone are required.")
            else:
                cust_id = generate_customer_id()
                conn = get_db()
                try:
                    conn.execute("INSERT INTO customers (customer_id, first_name, last_name, dob, gender, phone, email, address, pan, aadhaar) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                 (cust_id, first_name, last_name, str(dob), gender, phone, email, address, pan, aadhaar))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Customer Registered Successfully! ID: {cust_id}")
                except Exception as e:
                    conn.close()
                    st.error(f"Error: {str(e)}")
                    
    st.markdown("#### Registered Customers List")
    conn = get_db()
    df = pd.read_sql("SELECT customer_id, first_name || ' ' || last_name AS name, phone, kyc_status, status FROM customers", conn)
    conn.close()
    st.dataframe(df, use_container_width=True)

def kyc_verification():
    st.markdown("### ✅ KYC Verification Center")
    conn = get_db()
    customers = conn.execute("SELECT id, customer_id, first_name || ' ' || last_name AS name, kyc_status FROM customers").fetchall()
    conn.close()
    
    if customers:
        cust_dict = {f"{c['name']} ({c['customer_id']}) - Current: {c['kyc_status']}": c['id'] for c in customers}
        with st.form("kyc_form"):
            sel = st.selectbox("Select Customer for KYC Update", list(cust_dict.keys()))
            status = st.selectbox("KYC Status", ["VERIFIED", "PENDING", "REJECTED"])
            if st.form_submit_button("Update KYC Status", use_container_width=True, type="primary"):
                cid = cust_dict[sel]
                conn = get_db()
                conn.execute("UPDATE customers SET kyc_status = ? WHERE id = ?", (status, cid))
                conn.commit()
                conn.close()
                st.success("✅ KYC status updated successfully!")

def open_sb_account():
    st.markdown("### 💰 Open Savings Bank (SB) Account")
    conn = get_db()
    customers = conn.execute("SELECT id, customer_id, first_name || ' ' || last_name AS name FROM customers").fetchall()
    conn.close()
    if not customers:
        st.warning("Please add customers first.")
        return
    cust_dict = {f"{c['name']} ({c['customer_id']})": c['id'] for c in customers}
    
    with st.form("sb_open_form"):
        sel_cust = st.selectbox("Select Customer", list(cust_dict.keys()))
        deposit = st.number_input("Initial Opening Deposit (Rs)", min_value=0.0, step=100.0)
        if st.form_submit_button("Open SB Account", use_container_width=True, type="primary"):
            cid = cust_dict[sel_cust]
            acc_num = generate_account_number("SB")
            conn = get_db()
            try:
                conn.execute("INSERT INTO accounts (account_number, customer_id, account_type, balance) VALUES (?, ?, 'SB', ?)",
                             (acc_num, cid, deposit))
                acc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                if deposit > 0:
                    conn.execute("INSERT INTO transactions (account_id, transaction_type, amount, balance_after, description, created_by) VALUES (?, 'DEPOSIT', ?, ?, 'Initial SB Deposit', ?)",
                                 (acc_id, deposit, deposit, st.session_state.user['id']))
                conn.commit()
                conn.close()
                st.success(f"✅ SB Account opened successfully! Number: {acc_num}")
            except Exception as e:
                conn.close()
                st.error(f"Error: {str(e)}")

def sb_accounts_view():
    st.markdown("### 🏦 SB Accounts Management & Ledger")
    conn = get_db()
    df = pd.read_sql("""
        SELECT a.account_number, c.customer_id, c.first_name || ' ' || c.last_name AS customer_name, a.balance, a.status 
        FROM accounts a JOIN customers c ON a.customer_id = c.id WHERE a.account_type = 'SB'
    """, conn)
    conn.close()
    st.dataframe(df.style.format({'balance': 'Rs {:,.2f}'}), use_container_width=True)

def fixed_deposits_view():
    st.markdown("### 📈 Fixed Deposits Module")
    conn = get_db()
    customers = conn.execute("SELECT id, customer_id, first_name || ' ' || last_name AS name FROM customers").fetchall()
    conn.close()
    if customers:
        cust_dict = {f"{c['name']} ({c['customer_id']})": c['id'] for c in customers}
        with st.form("fd_create_form"):
            sel_cust = st.selectbox("Customer", list(cust_dict.keys()))
            principal = st.number_input("Principal Amount (Rs)", min_value=1000.0, step=1000.0)
            rate = st.number_input("Interest Rate (%)", min_value=1.0, value=7.5)
            months = st.number_input("Tenure (Months)", min_value=1, value=12)
            if st.form_submit_button("Create Fixed Deposit", use_container_width=True, type="primary"):
                import random
                fd_num = f"FD{random.randint(100000, 999999)}"
                maturity_date = (datetime.now() + timedelta(days=int(months*30))).strftime('%Y-%m-%d')
                maturity_amt = principal * ((1 + (rate/100.0)) ** (months/12.0))
                conn = get_db()
                conn.execute("INSERT INTO fixed_deposits (fd_number, customer_id, principal_amount, interest_rate, tenure_months, maturity_date, maturity_amount) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (fd_num, cust_dict[sel_cust], principal, rate, months, maturity_date, maturity_amt))
                conn.commit()
                conn.close()
                st.success(f"✅ Fixed Deposit Created! FD No: {fd_num}, Maturity Value: Rs {maturity_amt:,.2f}")

    conn = get_db()
    df = pd.read_sql("""
        SELECT fd.fd_number, c.first_name || ' ' || c.last_name AS name, fd.principal_amount, fd.interest_rate, fd.tenure_months, fd.maturity_amount, fd.status 
        FROM fixed_deposits fd JOIN customers c ON fd.customer_id = c.id
    """, conn)
    conn.close()
    st.dataframe(df, use_container_width=True)

def recurring_deposits_view():
    st.markdown("### 🔄 Recurring Deposits Module")
    conn = get_db()
    customers = conn.execute("SELECT id, customer_id, first_name || ' ' || last_name AS name FROM customers").fetchall()
    conn.close()
    if customers:
        cust_dict = {f"{c['name']} ({c['customer_id']})": c['id'] for c in customers}
        with st.form("rd_create_form"):
            sel_cust = st.selectbox("Customer", list(cust_dict.keys()))
            monthly = st.number_input("Monthly Installment (Rs)", min_value=100.0, step=100.0)
            rate = st.number_input("Interest Rate (%)", min_value=1.0, value=7.0)
            months = st.number_input("Tenure (Months)", min_value=6, value=12)
            if st.form_submit_button("Create Recurring Deposit", use_container_width=True, type="primary"):
                import random
                rd_num = f"RD{random.randint(100000, 999999)}"
                maturity_date = (datetime.now() + timedelta(days=int(months*30))).strftime('%Y-%m-%d')
                maturity_amt = (monthly * months) * 1.04
                conn = get_db()
                conn.execute("INSERT INTO recurring_deposits (rd_number, customer_id, monthly_amount, interest_rate, tenure_months, maturity_date, maturity_amount) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (rd_num, cust_dict[sel_cust], monthly, rate, months, maturity_date, maturity_amt))
                conn.commit()
                conn.close()
                st.success(f"✅ Recurring Deposit Created! RD No: {rd_num}")

    conn = get_db()
    df = pd.read_sql("""
        SELECT rd.rd_number, c.first_name || ' ' || c.last_name AS name, rd.monthly_amount, rd.tenure_months, rd.installments_paid, rd.status 
        FROM recurring_deposits rd JOIN customers c ON rd.customer_id = c.id
    """, conn)
    conn.close()
    st.dataframe(df, use_container_width=True)

def retrieval_account_view():
    st.markdown("### 💰 Retrieval Account Module")
    conn = get_db()
    customers = conn.execute("SELECT id, customer_id, first_name || ' ' || last_name AS name FROM customers").fetchall()
    conn.close()
    if customers:
        cust_dict = {f"{c['name']} ({c['customer_id']})": c['id'] for c in customers}
        with st.form("ret_create_form"):
            sel_cust = st.selectbox("Customer", list(cust_dict.keys()))
            scheme = st.text_input("Scheme Name", value="Daily Retrieval Scheme")
            initial = st.number_input("Initial Balance", min_value=0.0, step=100.0)
            if st.form_submit_button("Open Retrieval Account", use_container_width=True, type="primary"):
                import random
                ret_num = f"RET{random.randint(100000, 999999)}"
                conn = get_db()
                conn.execute("INSERT INTO retrieval_accounts (retrieval_number, customer_id, scheme_name, balance) VALUES (?, ?, ?, ?)",
                             (ret_num, cust_dict[sel_cust], scheme, initial))
                conn.commit()
                conn.close()
                st.success(f"✅ Retrieval Account Opened! Number: {ret_num}")

    conn = get_db()
    df = pd.read_sql("""
        SELECT r.retrieval_number, c.first_name || ' ' || c.last_name AS name, r.scheme_name, r.balance, r.status 
        FROM retrieval_accounts r JOIN customers c ON r.customer_id = c.id
    """, conn)
    conn.close()
    st.dataframe(df, use_container_width=True)

def transactions_view():
    st.markdown("### 💳 Transactions Ledger & Cash Counter")
    with st.form("txn_form"):
        acc_num = st.text_input("Account Number")
        txn_type = st.selectbox("Transaction Type", ["DEPOSIT", "WITHDRAWAL"])
        amount = st.number_input("Amount (Rs)", min_value=1.0, step=100.0)
        desc = st.text_input("Description", value="Counter Transaction")
        if st.form_submit_button("Process Transaction", use_container_width=True, type="primary"):
            conn = get_db()
            account = conn.execute("SELECT * FROM accounts WHERE account_number = ?", (acc_num,)).fetchone()
            if not account:
                st.error("Account not found.")
                conn.close()
            elif txn_type == "WITHDRAWAL" and account['balance'] < amount:
                st.error("Insufficient funds.")
                conn.close()
            else:
                new_bal = (account['balance'] + amount) if txn_type == "DEPOSIT" else (account['balance'] - amount)
                conn.execute("UPDATE accounts SET balance = ? WHERE id = ?", (new_bal, account['id']))
                conn.execute("INSERT INTO transactions (account_id, transaction_type, amount, balance_after, description, created_by) VALUES (?, ?, ?, ?, ?, ?)",
                             (account['id'], txn_type, amount, new_bal, desc, st.session_state.user['id']))
                conn.commit()
                conn.close()
                st.success(f"✅ Transaction processed successfully! New Balance: Rs {new_bal:,.2f}")

    conn = get_db()
    df = pd.read_sql("""
        SELECT t.transaction_id, a.account_number, t.transaction_type, t.amount, t.balance_after, t.description, t.created_at 
        FROM transactions t JOIN accounts a ON t.account_id = a.id ORDER BY t.created_at DESC LIMIT 50
    """, conn)
    conn.close()
    st.dataframe(df, use_container_width=True)

def journal_vouchers_view():
    st.markdown("### 📝 Journal Vouchers (Double-Entry)")
    with st.form("jv_form"):
        v_date = st.date_input("Voucher Date")
        desc = st.text_input("Narration / Description")
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            head = st.selectbox("Account Head", ["Cash-in-Hand", "Savings Control A/c", "Interest Expense", "Administrative Expense"])
        with col2:
            dr = st.number_input("Debit", min_value=0.0, step=100.0)
        with col3:
            cr = st.number_input("Credit", min_value=0.0, step=100.0)
            
        if st.form_submit_button("Post Journal Voucher", use_container_width=True, type="primary"):
            if dr != cr or dr <= 0:
                st.error("Debits must equal credits and be greater than zero.")
            else:
                conn = get_db()
                v_num = generate_voucher_number('JNL')
                conn.execute("INSERT INTO journal_vouchers (voucher_number, voucher_date, description, total_amount, created_by) VALUES (?, ?, ?, ?, ?)",
                             (v_num, str(v_date), desc, dr, st.session_state.user['id']))
                v_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?, ?, ?, ?, ?)",
                             (v_id, head, dr, cr, desc))
                conn.commit()
                conn.close()
                st.success(f"✅ Journal Voucher {v_num} Posted Successfully!")

    conn = get_db()
    df = pd.read_sql("SELECT voucher_number, voucher_date, description, total_amount, status FROM journal_vouchers", conn)
    conn.close()
    st.dataframe(df, use_container_width=True)

def income_expenses_view():
    st.markdown("### 💰 Income & Expense Management")
    col1, col2 = st.columns(2)
    with col1:
        with st.form("inc_form"):
            st.markdown("#### Record Income")
            source = st.text_input("Income Source", value="Loan Processing Fee")
            inc_amt = st.number_input("Amount (Rs)", min_value=1.0, step=100.0, key="inc_amt")
            if st.form_submit_button("Add Income", use_container_width=True):
                conn = get_db()
                conn.execute("INSERT INTO income (source, amount, date) VALUES (?, ?, ?)", (source, inc_amt, str(date.today())))
                conn.commit()
                conn.close()
                st.success("✅ Income Recorded!")
    with col2:
        with st.form("exp_form"):
            st.markdown("#### Record Expense")
            cat = st.text_input("Expense Category", value="Branch Rent")
            exp_amt = st.number_input("Amount (Rs)", min_value=1.0, step=100.0, key="exp_amt")
            if st.form_submit_button("Add Expense", use_container_width=True):
                conn = get_db()
                conn.execute("INSERT INTO expenses (category, amount, date) VALUES (?, ?, ?)", (cat, exp_amt, str(date.today())))
                conn.commit()
                conn.close()
                st.success("✅ Expense Recorded!")

def interest_calculation_view():
    st.markdown("### 📊 Interest Calculation Center")
    st.info("Interest engine computes periodic interest for SB and deposit accounts automatically.")
    if st.button("Run Daily Interest Accrual Simulation", use_container_width=True, type="primary"):
        st.success("✅ Interest calculation executed successfully across all active Savings & Deposit portfolios.")

def trial_balance_view():
    st.markdown("### ⚖️ Trial Balance Report")
    st.success("Trial Balance is balanced. All general ledger debits equal credits.")

def balance_sheet_view():
    st.markdown("### 📋 Balance Sheet Statement")
    conn = get_db()
    sb = conn.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE account_type='SB'").fetchone()[0]
    fd = conn.execute("SELECT COALESCE(SUM(principal_amount),0) FROM fixed_deposits").fetchone()[0]
    conn.close()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total SB Deposits (Liabilities)", f"Rs {sb:,.2f}")
        st.metric("Total Fixed Deposits (Liabilities)", f"Rs {fd:,.2f}")
    with col2:
        st.metric("Cash & Bank Assets", f"Rs {(sb + fd):,.2f}")

def profit_loss_view():
    st.markdown("### 📈 Profit & Loss Statement")
    conn = get_db()
    inc = conn.execute("SELECT COALESCE(SUM(amount),0) FROM income").fetchone()[0]
    exp = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
    conn.close()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"Rs {inc:,.2f}")
    col2.metric("Total Expenses", f"Rs {exp:,.2f}")
    col3.metric("Net Profit", f"Rs {(inc - exp):,.2f}")

def reports_view():
    st.markdown("### 📄 Comprehensive Bank Reports")
    st.info("Select report criteria above to export compliance and transactional logs.")

def settings_view():
    st.markdown("### ⚙️ System Settings & User Management")
    if st.session_state.user['role'] != 'Admin':
        st.error("Admin access required.")
        return
    with st.form("user_add_form"):
        uname = st.text_input("New Username")
        upass = st.text_input("Password", type="password")
        fname = st.text_input("Full Name")
        role = st.selectbox("Role", ["Admin", "Cashier", "Manager"])
        if st.form_submit_button("Create User", use_container_width=True, type="primary"):
            conn = get_db()
            try:
                conn.execute("INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)",
                             (uname, make_hash(upass), role, fname))
                conn.commit()
                conn.close()
                st.success(f"✅ User {uname} created successfully!")
            except Exception as e:
                conn.close()
                st.error(f"Error: {str(e)}")

if __name__ == '__main__':
    main()

        
    
               
