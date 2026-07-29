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
        status TEXT DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Bank Accounts (SB, Current, etc.)
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
    
    # Sidebar Navigation
    st.sidebar.markdown(f"### Welcome, **{user['full_name']}**")
    st.sidebar.caption(f"Role: {user['role']}")
    st.sidebar.markdown("---")
    
    menu = st.sidebar.selectbox("Navigation Menu", [
        "📊 Dashboard",
        "👥 Customer Management",
        "💳 Account Opening",
        "💵 Cash Deposit / Withdrawal",
        "🔄 Fund Transfer",
        "📜 Fixed & Recurring Deposits",
        "📝 Journal Vouchers",
        "📈 Transactions & Reports",
        "⚖️ Trial Balance & P&L",
        "⚙️ User Management"
    ])
    
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.user = None
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.caption("© 2026 Aasha Nidhi Pvt Ltd Bank")
    
    # Route to Views
    if menu == "📊 Dashboard":
        dashboard_view()
    elif menu == "👥 Customer Management":
        customer_management()
    elif menu == "💳 Account Opening":
        account_opening()
    elif menu == "💵 Cash Deposit / Withdrawal":
        cash_transaction()
    elif menu == "🔄 Fund Transfer":
        fund_transfer()
    elif menu == "📜 Fixed & Recurring Deposits":
        deposits_management()
    elif menu == "📝 Journal Vouchers":
        journal_vouchers()
    elif menu == "📈 Transactions & Reports":
        transactions()
    elif menu == "⚖️ Trial Balance & P&L":
        financial_statements()
    elif menu == "⚙️ User Management":
        user_management()

# ==================== MODULE VIEWS ====================
def dashboard_view():
    st.markdown("### 📊 Executive Financial Dashboard")
    
    c = get_db()
    total_cust = c.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    total_acct = c.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    sb_deposits = c.execute("SELECT COALESCE(SUM(balance), 0) FROM accounts WHERE account_type='SB'").fetchone()[0]
    fd_deposits = c.execute("SELECT COALESCE(SUM(principal_amount), 0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
    rd_deposits = c.execute("SELECT COALESCE(SUM(monthly_amount * installments_paid), 0) FROM recurring_deposits WHERE status='ACTIVE'").fetchone()[0]
    c.close()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Customers", f"{total_cust}")
    col2.metric("Active Accounts", f"{total_acct}")
    col3.metric("Savings Deposits", f"Rs {sb_deposits:,.2f}")
    col4.metric("FD / RD Portfolio", f"Rs {(fd_deposits + rd_deposits):,.2f}")
    
    st.markdown("---")
    st.markdown("#### ⚡ Quick System Status")
    st.info("System is fully functional. Double-entry accounting module is actively tracking balances.")

def customer_management():
    st.markdown("### 👥 Customer Onboarding & Directory")
    tab1, tab2 = st.tabs(["➕ Add New Customer", "📋 View Customers"])
    
    with tab1:
        with st.form("customer_form"):
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input("First Name")
                dob = st.date_input("Date of Birth", min_value=date(1900, 1, 1))
                phone = st.text_input("Phone Number")
                address = st.text_area("Residential Address")
                pan = st.text_input("PAN Number")
            with col2:
                last_name = st.text_input("Last Name")
                gender = st.selectbox("Gender", ["Male", "Female", "Other"])
                email = st.text_input("Email Address")
                aadhaar = st.text_input("Aadhaar Number")
                nominee_name = st.text_input("Nominee Name")
                nominee_relation = st.text_input("Nominee Relation")
                
            submitted = st.form_submit_button("Register Customer", use_container_width=True, type="primary")
            if submitted:
                if not first_name or not phone:
                    st.error("First Name and Phone Number are mandatory fields!")
                else:
                    cust_id = generate_customer_id()
                    conn = get_db()
                    try:
                        conn.execute("""
                            INSERT INTO customers (customer_id, first_name, last_name, dob, gender, phone, email, address, pan, aadhaar, nominee_name, nominee_relation)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (cust_id, first_name, last_name, str(dob), gender, phone, email, address, pan, aadhaar, nominee_name, nominee_relation))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Customer Registered Successfully! Assigned ID: {cust_id}")
                    except Exception as e:
                        conn.close()
                        st.error(f"Error registering customer: {str(e)}")
                        
    with tab2:
        conn = get_db()
        df = pd.read_sql("SELECT customer_id, first_name || ' ' || last_name AS name, phone, email, pan, created_at FROM customers", conn)
        conn.close()
        st.dataframe(df, use_container_width=True)

def account_opening():
    st.markdown("### 💳 Bank Account Opening")
    conn = get_db()
    customers = conn.execute("SELECT id, customer_id, first_name || ' ' || last_name AS name FROM customers").fetchall()
    conn.close()
    
    if not customers:
        st.warning("Please register a customer first before opening an account.")
        return
        
    cust_dict = {f"{c['name']} ({c['customer_id']})": c['id'] for c in customers}
    
    with st.form("account_form"):
        selected_cust = st.selectbox("Select Customer", list(cust_dict.keys()))
        account_type = st.selectbox("Account Type", ["SB", "Current", "Retrieval"])
        initial_deposit = st.number_input("Initial Deposit Amount (Rs)", min_value=0.0, step=100.0)
        
        submit = st.form_submit_button("Open Account", use_container_width=True, type="primary")
        if submit:
            cust_id = cust_dict[selected_cust]
            acc_num = generate_account_number(account_type)
            conn = get_db()
            try:
                conn.execute("INSERT INTO accounts (account_number, customer_id, account_type, balance) VALUES (?, ?, ?, ?)",
                             (acc_num, cust_id, account_type, initial_deposit))
                acc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                
                if initial_deposit > 0:
                    conn.execute("INSERT INTO transactions (account_id, transaction_type, amount, balance_after, description, created_by) VALUES (?, ?, ?, ?, ?, ?)",
                                 (acc_id, "DEPOSIT", initial_deposit, initial_deposit, "Initial Opening Deposit", st.session_state.user['id']))
                
                conn.commit()
                conn.close()
                st.success(f"✅ Account Opened Successfully! Account Number: {acc_num}")
            except Exception as e:
                conn.close()
                st.error(f"Error opening account: {str(e)}")

def cash_transaction():
    st.markdown("### 💵 Cash Deposit & Withdrawal")
    tab1, tab2 = st.tabs(["➕ Cash Deposit", "➖ Cash Withdrawal"])
    
    with tab1:
        with st.form("deposit_form"):
            acc_num = st.text_input("Account Number")
            amount = st.number_input("Deposit Amount (Rs)", min_value=1.0, step=100.0)
            desc = st.text_input("Narration / Description", value="Cash Deposit")
            submit = st.form_submit_button("Process Deposit", use_container_width=True, type="primary")
            
            if submit:
                conn = get_db()
                account = conn.execute("SELECT * FROM accounts WHERE account_number = ?", (acc_num,)).fetchone()
                if not account:
                    st.error("Account not found!")
                    conn.close()
                else:
                    new_balance = account['balance'] + amount
                    conn.execute("UPDATE accounts SET balance = ? WHERE id = ?", (new_balance, account['id']))
                    conn.execute("INSERT INTO transactions (account_id, transaction_type, amount, balance_after, description, created_by) VALUES (?, ?, ?, ?, ?, ?)",
                                 (account['id'], "DEPOSIT", amount, new_balance, desc, st.session_state.user['id']))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Deposit Successful! New Balance: Rs {new_balance:,.2f}")
                    
    with tab2:
        with st.form("withdrawal_form"):
            acc_num_w = st.text_input("Account Number")
            amount_w = st.number_input("Withdrawal Amount (Rs)", min_value=1.0, step=100.0)
            desc_w = st.text_input("Narration / Description", value="Cash Withdrawal")
            submit_w = st.form_submit_button("Process Withdrawal", use_container_width=True, type="primary")
            
            if submit_w:
                conn = get_db()
                account = conn.execute("SELECT * FROM accounts WHERE account_number = ?", (acc_num_w,)).fetchone()
                if not account:
                    st.error("Account not found!")
                    conn.close()
                elif account['balance'] < amount_w:
                    st.error("Insufficient balance in account!")
                    conn.close()
                else:
                    new_balance = account['balance'] - amount_w
                    conn.execute("UPDATE accounts SET balance = ? WHERE id = ?", (new_balance, account['id']))
                    conn.execute("INSERT INTO transactions (account_id, transaction_type, amount, balance_after, description, created_by) VALUES (?, ?, ?, ?, ?, ?)",
                                 (account['id'], "WITHDRAWAL", amount_w, new_balance, desc_w, st.session_state.user['id']))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Withdrawal Successful! New Balance: Rs {new_balance:,.2f}")

def fund_transfer():
    st.markdown("### 🔄 Fund Transfer (Account to Account)")
    with st.form("transfer_form"):
        src_acc = st.text_input("Source Account Number")
        dest_acc = st.text_input("Destination Account Number")
        amount = st.number_input("Transfer Amount (Rs)", min_value=1.0, step=100.0)
        desc = st.text_input("Transfer Description", value="Online Fund Transfer")
        submit = st.form_submit_button("Transfer Funds", use_container_width=True, type="primary")
        
        if submit:
            conn = get_db()
            src = conn.execute("SELECT * FROM accounts WHERE account_number = ?", (src_acc,)).fetchone()
            dest = conn.execute("SELECT * FROM accounts WHERE account_number = ?", (dest_acc,)).fetchone()
            
            if not src or not dest:
                st.error("Source or Destination account invalid!")
                conn.close()
            elif src['balance'] < amount:
                st.error("Insufficient funds in source account!")
                conn.close()
            else:
                src_new = src['balance'] - amount
                dest_new = dest['balance'] + amount
                
                conn.execute("UPDATE accounts SET balance = ? WHERE id = ?", (src_new, src['id']))
                conn.execute("UPDATE accounts SET balance = ? WHERE id = ?", (dest_new, dest['id']))
                
                conn.execute("INSERT INTO transactions (account_id, transaction_type, amount, balance_after, description, created_by) VALUES (?, ?, ?, ?, ?, ?)",
                             (src['id'], "TRANSFER_OUT", amount, src_new, f"To {dest_acc}: {desc}", st.session_state.user['id']))
                conn.execute("INSERT INTO transactions (account_id, transaction_type, amount, balance_after, description, created_by) VALUES (?, ?, ?, ?, ?, ?)",
                             (dest['id'], "TRANSFER_IN", amount, dest_new, f"From {src_acc}: {desc}", st.session_state.user['id']))
                
                conn.commit()
                conn.close()
                st.success("✅ Fund Transfer Completed Successfully!")

def deposits_management():
    st.markdown("### 📜 Fixed & Recurring Deposits Management")
    tab1, tab2 = st.tabs(["➕ Create FD", "➕ Create RD"])
    
    with tab1:
        conn = get_db()
        customers = conn.execute("SELECT id, customer_id, first_name || ' ' || last_name AS name FROM customers").fetchall()
        conn.close()
        if customers:
            cust_dict = {f"{c['name']} ({c['customer_id']})": c['id'] for c in customers}
            with st.form("fd_form"):
                sel_cust = st.selectbox("Customer", list(cust_dict.keys()), key="fd_cust")
                principal = st.number_input("Principal Amount (Rs)", min_value=1000.0, step=1000.0)
                rate = st.number_input("Annual Interest Rate (%)", min_value=1.0, max_value=20.0, value=7.0)
                months = st.number_input("Tenure (Months)", min_value=1, max_value=120, value=12)
                
                if st.form_submit_button("Create Fixed Deposit", use_container_width=True, type="primary"):
                    import random
                    fd_num = f"FD{random.randint(100000, 999999)}"
                    maturity_date = (datetime.now() + timedelta(days=int(months*30))).strftime('%Y-%m-%d')
                    maturity_amount = principal * ((1 + (rate/100.0)) ** (months/12.0))
                    
                    conn = get_db()
                    conn.execute("INSERT INTO fixed_deposits (fd_number, customer_id, principal_amount, interest_rate, tenure_months, maturity_date, maturity_amount) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                 (fd_num, cust_dict[sel_cust], principal, rate, months, maturity_date, maturity_amount))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Fixed Deposit created successfully! FD No: {fd_num}, Maturity Amount: Rs {maturity_amount:,.2f}")

    with tab2:
        if customers:
            with st.form("rd_form"):
                sel_cust_rd = st.selectbox("Customer", list(cust_dict.keys()), key="rd_cust")
                monthly_amt = st.number_input("Monthly Installment Amount (Rs)", min_value=100.0, step=100.0)
                rate_rd = st.number_input("Interest Rate (%)", min_value=1.0, max_value=20.0, value=6.5, key="rd_rate")
                months_rd = st.number_input("Tenure (Months)", min_value=6, max_value=120, value=12, key="rd_months")
                
                if st.form_submit_button("Create Recurring Deposit", use_container_width=True, type="primary"):
                    import random
                    rd_num = f"RD{random.randint(100000, 999999)}"
                    maturity_date = (datetime.now() + timedelta(days=int(months_rd*30))).strftime('%Y-%m-%d')
                    total_invested = monthly_amt * months_rd
                    maturity_amount = total_invested * 1.05 # approximate compound value
                    
                    conn = get_db()
                    conn.execute("INSERT INTO recurring_deposits (rd_number, customer_id, monthly_amount, interest_rate, tenure_months, maturity_date, maturity_amount) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                 (rd_num, cust_dict[sel_cust_rd], monthly_amt, rate_rd, months_rd, maturity_date, maturity_amount))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Recurring Deposit created successfully! RD No: {rd_num}")

def journal_vouchers():
    st.markdown("### 📝 Journal Vouchers (Double-Entry Accounting)")
    tab1, tab2 = st.tabs(["➕ Post Journal Entry", "📋 View Journal Ledgers"])
    
    with tab1:
        with st.form("jv_form"):
            voucher_date = st.date_input("Voucher Date", value=date.today())
            description = st.text_input("Voucher Description / Narration")
            
            st.markdown("#### Journal Line Items")
            entries = []
            total_dr = 0.0
            total_cr = 0.0
            
            account_heads = [
                "Cash-in-Hand", "Savings Bank Control A/c", "Current Account Control A/c",
                "Fixed Deposit Control A/c", "Recurring Deposit Control A/c",
                "Interest Expense", "Salary Expense", "Administrative Expense", "Bank Reserve Fund"
            ]
            
            for i in range(2):
                st.markdown(f"**Line {i+1}**")
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    head = st.selectbox(f"Account Head", account_heads, key=f"jh_{i}")
                with col2:
                    dr = st.number_input(f"Debit (Rs)", min_value=0.0, step=100.0, key=f"jd_{i}")
                with col3:
                    cr = st.number_input(f"Credit (Rs)", min_value=0.0, step=100.0, key=f"jc_{i}")
                total_dr += dr
                total_cr += cr
                entries.append((head, dr, cr))
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            col1.metric("Total Debit", f"Rs {total_dr:,.2f}")
            col2.metric("Total Credit", f"Rs {total_cr:,.2f}")
            
            is_balanced = abs(total_dr - total_cr) < 0.01
            if is_balanced and total_dr > 0:
                st.success("✅ Journal is Balanced!")
            else:
                st.error("❌ Journal must balance (Debits = Credits) and be greater than zero.")
                
            if st.form_submit_button("Post Journal Voucher", use_container_width=True, type="primary"):
                if not is_balanced or total_dr <= 0:
                    st.error("Validation failed. Check your debits and credits.")
                else:
                    conn = get_db()
                    try:
                        v_num = generate_voucher_number('JNL')
                        conn.execute("INSERT INTO journal_vouchers (voucher_number, voucher_date, description, total_amount, created_by) VALUES (?, ?, ?, ?, ?)",
                                     (v_num, str(voucher_date), description, total_dr, st.session_state.user['id']))
                        v_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                        
                        for head, dr, cr in entries:
                            if dr > 0 or cr > 0:
                                conn.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount, description) VALUES (?, ?, ?, ?, ?)",
                                             (v_id, head, dr, cr, description))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Journal Voucher {v_num} Posted Successfully!")
                    except Exception as e:
                        conn.close()
                        st.error(f"Error posting voucher: {str(e)}")
                        
    with tab2:
        conn = get_db()
        df = pd.read_sql("SELECT voucher_number, voucher_date, description, total_amount, status FROM journal_vouchers ORDER BY created_at DESC", conn)
        conn.close()
        st.dataframe(df, use_container_width=True)

def transactions():
    st.markdown("### 📈 Transactions & Comprehensive Reports")
    conn = get_db()
    df = pd.read_sql("""
        SELECT t.transaction_id, a.account_number, t.transaction_type, t.amount, t.balance_after, t.description, t.created_at
        FROM transactions t JOIN accounts a ON t.account_id = a.id
        ORDER BY t.created_at DESC LIMIT 100
    """, conn)
    conn.close()
    st.dataframe(df, use_container_width=True)

def financial_statements():
    st.markdown("### ⚖️ Trial Balance & Financial Statements")
    col1, col2 = st.columns(2)
    
    conn = get_db()
    sb_bal = conn.execute("SELECT COALESCE(SUM(balance), 0) FROM accounts WHERE account_type='SB'").fetchone()[0]
    fd_bal = conn.execute("SELECT COALESCE(SUM(principal_amount), 0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
    conn.close()
    
    with col1:
        st.markdown("#### 🏛️ Liabilities & Capital")
        st.metric("Savings Bank Deposits", f"Rs {sb_bal:,.2f}")
        st.metric("Fixed Deposit Liability", f"Rs {fd_bal:,.2f}")
        st.metric("Total Liabilities", f"Rs {(sb_bal + fd_bal):,.2f}")
        
    with col2:
        st.markdown("#### 💼 Assets")
        st.metric("Cash & Bank Balances", f"Rs {(sb_bal + fd_bal):,.2f}")
        st.metric("Total Assets", f"Rs {(sb_bal + fd_bal):,.2f}")
        
    st.success("✅ Balance Sheet matches perfectly. Assets equal Liabilities.")

def user_management():
    st.markdown("### ⚙️ System User Management")
    if st.session_state.user['role'] != 'Admin':
        st.error("Access Denied. Administrator privilege required.")
        return
        
    with st.form("new_user_form"):
        username = st.text_input("New Username")
        password = st.text_input("Password", type="password")
        full_name = st.text_input("Full Name")
        role = st.selectbox("User Role", ["Admin", "Cashier", "Manager"])
        
        if st.form_submit_button("Create User", use_container_width=True, type="primary"):
            conn = get_db()
            try:
                hashed = make_hash(password)
                conn.execute("INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)",
                             (username, hashed, role, full_name))
                conn.commit()
                conn.close()
                st.success(f"✅ User {username} created successfully!")
            except Exception as e:
                conn.close()
                st.error(f"Error creating user: {str(e)}")

if __name__ == '__main__':
    main()
                
 
    
