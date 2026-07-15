import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import calendar
from dateutil.relativedelta import relativedelta
import uuid
import json
import os

# Page configuration
st.set_page_config(
    page_title="Banking Management System",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #1f4287;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2781b5;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# Database initialization
def init_database():
    """Initialize database and create all tables"""
    if os.path.exists('banking_system.db'):
        try:
            conn = sqlite3.connect('banking_system.db')
            c = conn.cursor()
            c.execute("SELECT password FROM users LIMIT 1")
            conn.close()
        except:
            os.remove('banking_system.db')
    
    conn = sqlite3.connect('banking_system.db', check_same_thread=False)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'staff',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Customers table with KYC
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        customer_id TEXT PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        date_of_birth DATE NOT NULL,
        email TEXT UNIQUE,
        phone TEXT,
        address TEXT,
        id_proof_type TEXT,
        id_proof_number TEXT,
        kyc_status TEXT DEFAULT 'pending',
        kyc_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by INTEGER,
        FOREIGN KEY (created_by) REFERENCES users (id)
    )''')
    
    # Accounts table
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (
        account_number TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        account_type TEXT NOT NULL,
        balance REAL DEFAULT 0.00,
        interest_rate REAL DEFAULT 0.00,
        status TEXT DEFAULT 'active',
        opened_date DATE NOT NULL,
        closed_date DATE,
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
    )''')
    
    # Transactions table
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        transaction_id TEXT PRIMARY KEY,
        account_number TEXT NOT NULL,
        transaction_type TEXT NOT NULL,
        amount REAL NOT NULL,
        balance_before REAL,
        balance_after REAL,
        description TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (account_number) REFERENCES accounts (account_number)
    )''')
    
    # Fixed Deposits
    c.execute('''CREATE TABLE IF NOT EXISTS fixed_deposits (
        fd_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        account_number TEXT NOT NULL,
        principal_amount REAL NOT NULL,
        interest_rate REAL NOT NULL,
        tenure_months INTEGER NOT NULL,
        start_date DATE NOT NULL,
        maturity_date DATE NOT NULL,
        maturity_amount REAL,
        status TEXT DEFAULT 'active',
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
        FOREIGN KEY (account_number) REFERENCES accounts (account_number)
    )''')
    
    # Recurring Deposits
    c.execute('''CREATE TABLE IF NOT EXISTS recurring_deposits (
        rd_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        account_number TEXT NOT NULL,
        monthly_amount REAL NOT NULL,
        interest_rate REAL NOT NULL,
        tenure_months INTEGER NOT NULL,
        start_date DATE NOT NULL,
        maturity_date DATE NOT NULL,
        maturity_amount REAL,
        installments_paid INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
        FOREIGN KEY (account_number) REFERENCES accounts (account_number)
    )''')
    
    # Loans
    c.execute('''CREATE TABLE IF NOT EXISTS loans (
        loan_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        account_number TEXT NOT NULL,
        loan_type TEXT NOT NULL,
        principal_amount REAL NOT NULL,
        interest_rate REAL NOT NULL,
        tenure_months INTEGER NOT NULL,
        emi_amount REAL,
        start_date DATE NOT NULL,
        end_date DATE,
        outstanding_amount REAL,
        status TEXT DEFAULT 'active',
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
        FOREIGN KEY (account_number) REFERENCES accounts (account_number)
    )''')
    
    # EMI Payments
    c.execute('''CREATE TABLE IF NOT EXISTS emi_payments (
        payment_id TEXT PRIMARY KEY,
        loan_id TEXT NOT NULL,
        payment_date DATE NOT NULL,
        amount REAL NOT NULL,
        principal_component REAL,
        interest_component REAL,
        outstanding_after REAL,
        FOREIGN KEY (loan_id) REFERENCES loans (loan_id)
    )''')
    
    # Journal Vouchers
    c.execute('''CREATE TABLE IF NOT EXISTS journal_vouchers (
        voucher_id TEXT PRIMARY KEY,
        voucher_date DATE NOT NULL,
        narration TEXT,
        total_amount REAL,
        status TEXT DEFAULT 'draft',
        created_by INTEGER,
        approved_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users (id),
        FOREIGN KEY (approved_by) REFERENCES users (id)
    )''')
    
    # Journal Voucher Entries
    c.execute('''CREATE TABLE IF NOT EXISTS journal_entries (
        entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
        voucher_id TEXT NOT NULL,
        account_head TEXT NOT NULL,
        debit_amount REAL DEFAULT 0.00,
        credit_amount REAL DEFAULT 0.00,
        FOREIGN KEY (voucher_id) REFERENCES journal_vouchers (voucher_id)
    )''')
    
    # Chart of Accounts
    c.execute('''CREATE TABLE IF NOT EXISTS chart_of_accounts (
        account_head TEXT PRIMARY KEY,
        account_type TEXT NOT NULL,
        category TEXT NOT NULL
    )''')
    
    # Audit Logs
    c.execute('''CREATE TABLE IF NOT EXISTS audit_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        table_affected TEXT,
        record_id TEXT,
        old_values TEXT,
        new_values TEXT,
        ip_address TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Insert default users
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                 ('admin', admin_password, 'admin'))
        
        staff_password = hashlib.sha256('staff123'.encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                 ('staff', staff_password, 'staff'))
    
    # Insert default chart of accounts
    default_accounts = [
        ('CASH', 'asset', 'current_asset'),
        ('BANK', 'asset', 'current_asset'),
        ('LOANS_RECEIVABLE', 'asset', 'current_asset'),
        ('FIXED_DEPOSITS', 'asset', 'non_current_asset'),
        ('CUSTOMER_DEPOSITS', 'liability', 'current_liability'),
        ('SAVINGS_DEPOSITS', 'liability', 'current_liability'),
        ('CURRENT_DEPOSITS', 'liability', 'current_liability'),
        ('INTEREST_INCOME', 'income', 'operating_income'),
        ('INTEREST_EXPENSE', 'expense', 'operating_expense'),
        ('SALARY_EXPENSE', 'expense', 'operating_expense'),
        ('RENT_EXPENSE', 'expense', 'operating_expense'),
        ('UTILITIES_EXPENSE', 'expense', 'operating_expense'),
        ('COMMISSION_INCOME', 'income', 'operating_income'),
        ('FEES_INCOME', 'income', 'operating_income'),
        ('LOAN_INTEREST_INCOME', 'income', 'operating_income'),
        ('FD_INTEREST_EXPENSE', 'expense', 'operating_expense'),
        ('RD_INTEREST_EXPENSE', 'expense', 'operating_expense'),
    ]
    
    for account in default_accounts:
        c.execute("INSERT OR IGNORE INTO chart_of_accounts (account_head, account_type, category) VALUES (?, ?, ?)", account)
    
    conn.commit()
    return conn

# Session state
def init_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'role' not in st.session_state:
        st.session_state.role = None

# Helper functions
def get_db_connection():
    conn = sqlite3.connect('banking_system.db')
    conn.row_factory = sqlite3.Row
    return conn

def generate_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8].upper()}"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def add_audit_log(user_id, action, table_affected, record_id, old_values=None, new_values=None):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""INSERT INTO audit_logs (user_id, action, table_affected, record_id, old_values, new_values) 
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (user_id, action, table_affected, record_id, 
                   json.dumps(old_values) if old_values else None,
                   json.dumps(new_values) if new_values else None))
        conn.commit()
        conn.close()
    except:
        pass

def calculate_emi(principal, annual_rate, tenure_months):
    monthly_rate = annual_rate / (12 * 100)
    emi = principal * monthly_rate * (1 + monthly_rate) ** tenure_months / ((1 + monthly_rate) ** tenure_months - 1)
    return round(emi, 2)

def calculate_fd_maturity(principal, annual_rate, tenure_months):
    rate = annual_rate / 100
    n = 4
    t = tenure_months / 12
    amount = principal * (1 + rate/n) ** (n * t)
    return round(amount, 2)

def calculate_rd_maturity(monthly_amount, annual_rate, tenure_months):
    rate = annual_rate / 100
    n = 4
    total = 0
    for i in range(tenure_months):
        remaining_months = tenure_months - i
        total += monthly_amount * (1 + rate/n) ** (n * remaining_months/12)
    return round(total, 2)

# ============================================
# PART 1: LOGIN PAGE
# ============================================
def login_page():
    st.markdown('<h1 class="main-header">🏦 Banking Management System</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<h3 class="sub-header">Login</h3>', unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("Please enter username and password")
                    return
                
                try:
                    conn = get_db_connection()
                    c = conn.cursor()
                    hashed_pw = hash_password(password)
                    c.execute("SELECT id, username, role, password FROM users WHERE username = ?", (username,))
                    user = c.fetchone()
                    
                    if user and user[3] == hashed_pw:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user[0]
                        st.session_state.username = user[1]
                        st.session_state.role = user[2]
                        add_audit_log(user[0], 'LOGIN', 'users', str(user[0]))
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                    conn.close()
                except Exception as e:
                    st.error(f"Login error: {str(e)}")

# ============================================
# PART 2: CUSTOMER REGISTRATION & KYC
# ============================================
def customer_registration():
    st.markdown('<h2 class="sub-header">📋 Customer Registration & KYC</h2>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Register Customer", "Customer List"])
    
    with tab1:
        with st.form("customer_registration"):
            col1, col2 = st.columns(2)
            
            with col1:
                first_name = st.text_input("First Name *")
                last_name = st.text_input("Last Name *")
                date_of_birth = st.date_input("Date of Birth *", 
                                             min_value=datetime.now()-timedelta(days=365*100),
                                             max_value=datetime.now()-timedelta(days=365*18))
                email = st.text_input("Email")
                
            with col2:
                phone = st.text_input("Phone Number")
                address = st.text_area("Address")
                id_proof_type = st.selectbox("ID Proof Type", 
                                            ["Select", "Passport", "Driver's License", "National ID", "PAN Card", "Aadhar Card"])
                id_proof_number = st.text_input("ID Proof Number")
            
            submit = st.form_submit_button("Register Customer", use_container_width=True)
            
            if submit:
                if not first_name or not last_name:
                    st.error("First name and last name are required!")
                    return
                
                try:
                    conn = get_db_connection()
                    c = conn.cursor()
                    customer_id = generate_id("CUST")
                    c.execute("""INSERT INTO customers 
                               (customer_id, first_name, last_name, date_of_birth, email, phone, address, 
                                id_proof_type, id_proof_number, kyc_status, created_by)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (customer_id, first_name, last_name, date_of_birth, email, phone, address,
                             id_proof_type if id_proof_type != "Select" else None,
                             id_proof_number if id_proof_type != "Select" else None,
                             'pending' if id_proof_type == "Select" else 'completed',
                             st.session_state.user_id))
                    conn.commit()
                    add_audit_log(st.session_state.user_id, 'CREATE', 'customers', customer_id)
                    st.success(f"Customer registered successfully! Customer ID: {customer_id}")
                    conn.close()
                except Exception as e:
                    st.error(f"Error: {e}")
    
    with tab2:
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("""SELECT customer_id, first_name, last_name, phone, email, kyc_status, created_at 
                         FROM customers ORDER BY created_at DESC""")
            customers = c.fetchall()
            
            if customers:
                df = pd.DataFrame(customers, columns=['Customer ID', 'First Name', 'Last Name', 'Phone', 
                                                      'Email', 'KYC Status', 'Created At'])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No customers registered yet")
            conn.close()
        except Exception as e:
            st.error(f"Error: {e}")

# ============================================
# PART 3: ACCOUNT MANAGEMENT
# ============================================
def account_management():
    st.markdown('<h2 class="sub-header">💰 Account Management</h2>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["Open Account", "Deposit", "Withdraw", "Account List"])
    
    with tab1:
        st.markdown("### Open New Account")
        
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT customer_id, first_name, last_name FROM customers WHERE kyc_status = 'completed'")
            customers = c.fetchall()
            conn.close()
            
            if customers:
                with st.form("open_account"):
                    customer_options = {f"{c[1]} {c[2]} ({c[0]})": c[0] for c in customers}
                    selected_customer = st.selectbox("Select Customer *", list(customer_options.keys()))
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        account_type = st.selectbox("Account Type *", ["Savings Account", "Current Account"])
                    with col2:
                        initial_deposit = st.number_input("Initial Deposit", min_value=0.0, value=500.0, step=100.0)
                    
                    if account_type == "Savings Account":
                        interest_rate = 4.0
                        min_balance = 500.0
                    else:
                        interest_rate = 0.0
                        min_balance = 1000.0
                    
                    st.info(f"Minimum Balance Required: ₹{min_balance:,.2f} | Interest Rate: {interest_rate}%")
                    
                    if st.form_submit_button("Open Account"):
                        if initial_deposit < min_balance:
                            st.error(f"Initial deposit must be at least ₹{min_balance:,.2f}")
                        else:
                            conn = get_db_connection()
                            c = conn.cursor()
                            customer_id = customer_options[selected_customer]
                            account_number = generate_id("ACC")
                            
                            c.execute("""INSERT INTO accounts 
                                       (account_number, customer_id, account_type, balance, interest_rate, opened_date)
                                       VALUES (?, ?, ?, ?, ?, ?)""",
                                    (account_number, customer_id, account_type, initial_deposit, 
                                     interest_rate, datetime.now().date()))
                            
                            if initial_deposit > 0:
                                trans_id = generate_id("TXN")
                                c.execute("""INSERT INTO transactions 
                                           (transaction_id, account_number, transaction_type, amount, 
                                            balance_before, balance_after, description)
                                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                        (trans_id, account_number, 'deposit', initial_deposit,
                                         0.0, initial_deposit, 'Initial deposit'))
                            
                            conn.commit()
                            add_audit_log(st.session_state.user_id, 'CREATE', 'accounts', account_number)
                            st.success(f"Account opened! Account Number: {account_number}")
                            conn.close()
            else:
                st.warning("No customers with completed KYC available")
        except Exception as e:
            st.error(f"Error: {e}")
    
    with tab2:
        st.markdown("### Deposit Money")
        
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT account_number, account_type, balance FROM accounts WHERE status = 'active'")
            accounts = c.fetchall()
            conn.close()
            
            if accounts:
                with st.form("deposit_form"):
                    account_options = {f"{acc[0]} - {acc[1]} (₹{acc[2]:,.2f})": acc for acc in accounts}
                    selected_account = st.selectbox("Select Account", list(account_options.keys()))
                    amount = st.number_input("Amount *", min_value=1.0, step=100.0)
                    description = st.text_input("Description")
                    
                    if st.form_submit_button("Deposit"):
                        acc_data = account_options[selected_account]
                        new_balance = float(acc_data[2]) + amount
                        
                        conn = get_db_connection()
                        c = conn.cursor()
                        trans_id = generate_id("TXN")
                        c.execute("""INSERT INTO transactions 
                                   (transaction_id, account_number, transaction_type, amount, 
                                    balance_before, balance_after, description)
                                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                (trans_id, acc_data[0], 'deposit', amount, acc_data[2], new_balance, description))
                        c.execute("UPDATE accounts SET balance = ? WHERE account_number = ?", (new_balance, acc_data[0]))
                        conn.commit()
                        add_audit_log(st.session_state.user_id, 'DEPOSIT', 'transactions', trans_id)
                        st.success(f"Deposited ₹{amount:,.2f}. New Balance: ₹{new_balance:,.2f}")
                        conn.close()
            else:
                st.info("No active accounts")
        except Exception as e:
            st.error(f"Error: {e}")
    
    with tab3:
        st.markdown("### Withdraw Money")
        
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT account_number, account_type, balance FROM accounts WHERE status = 'active'")
            accounts = c.fetchall()
            conn.close()
            
            if accounts:
                with st.form("withdraw_form"):
                    account_options = {f"{acc[0]} - {acc[1]} (₹{acc[2]:,.2f})": acc for acc in accounts}
                    selected_account = st.selectbox("Select Account", list(account_options.keys()))
                    acc_data = account_options[selected_account]
                    amount = st.number_input("Amount *", min_value=1.0, max_value=float(acc_data[2]), step=100.0)
                    description = st.text_input("Description")
                    
                    if st.form_submit_button("Withdraw"):
                        new_balance = float(acc_data[2]) - amount
                        
                        conn = get_db_connection()
                        c = conn.cursor()
                        trans_id = generate_id("TXN")
                        c.execute("""INSERT INTO transactions 
                                   (transaction_id, account_number, transaction_type, amount, 
                                    balance_before, balance_after, description)
                                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                (trans_id, acc_data[0], 'withdrawal', amount, acc_data[2], new_balance, description))
                        c.execute("UPDATE accounts SET balance = ? WHERE account_number = ?", (new_balance, acc_data[0]))
                        conn.commit()
                        add_audit_log(st.session_state.user_id, 'WITHDRAW', 'transactions', trans_id)
                        st.success(f"Withdrew ₹{amount:,.2f}. New Balance: ₹{new_balance:,.2f}")
                        conn.close()
            else:
                st.info("No active accounts")
        except Exception as e:
            st.error(f"Error: {e}")
    
    with tab4:
        st.markdown("### Active Accounts")
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("""SELECT a.account_number, c.first_name || ' ' || c.last_name, a.account_type, 
                         a.balance, a.interest_rate, a.opened_date
                         FROM accounts a JOIN customers c ON a.customer_id = c.customer_id
                         WHERE a.status = 'active' ORDER BY a.opened_date DESC""")
            accounts = c.fetchall()
            if accounts:
                df = pd.DataFrame(accounts, columns=['Account No', 'Customer', 'Type', 'Balance', 'Rate', 'Opened'])
                df['Balance'] = df['Balance'].apply(lambda x: f"₹{x:,.2f}")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No accounts found")
            conn.close()
        except Exception as e:
            st.error(f"Error: {e}")

# ============================================
# PART 4: FD, RD & LOANS
# ============================================
def investments_loans():
    st.markdown('<h2 class="sub-header">📈 Fixed Deposits, Recurring Deposits & Loans</h2>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Fixed Deposits", "Recurring Deposits", "Loans"])
    
    with tab1:
        st.markdown("### Create Fixed Deposit")
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""SELECT a.account_number, c.first_name || ' ' || c.last_name, a.balance, c.customer_id
                    FROM accounts a JOIN customers c ON a.customer_id = c.customer_id
                    WHERE a.status = 'active' AND a.balance > 0""")
        accounts = c.fetchall()
        conn.close()
        
        if accounts:
            with st.form("fd_form"):
                account_options = {f"{acc[0]} - {acc[1]} (₹{acc[2]:,.2f})": acc for acc in accounts}
                selected_account = st.selectbox("Select Account", list(account_options.keys()))
                
                col1, col2 = st.columns(2)
                with col1:
                    principal = st.number_input("Principal Amount *", min_value=1000.0, step=1000.0)
                    interest_rate = st.number_input("Interest Rate (%) *", min_value=0.1, value=6.5, step=0.25)
                with col2:
                    tenure_months = st.selectbox("Tenure (Months)", [3, 6, 12, 24, 36, 60])
                    start_date = st.date_input("Start Date", datetime.now().date())
                
                maturity_date = start_date + relativedelta(months=tenure_months)
                maturity_amount = calculate_fd_maturity(principal, interest_rate, tenure_months)
                
                st.markdown(f"**Maturity Date:** {maturity_date}")
                st.markdown(f"**Maturity Amount:** ₹{maturity_amount:,.2f}")
                st.markdown(f"**Interest Earned:** ₹{maturity_amount - principal:,.2f}")
                
                if st.form_submit_button("Create FD"):
                    acc_data = account_options[selected_account]
                    if principal > acc_data[2]:
                        st.error("Insufficient balance!")
                    else:
                        conn = get_db_connection()
                        c = conn.cursor()
                        fd_id = generate_id("FD")
                        c.execute("""INSERT INTO fixed_deposits 
                                   (fd_id, customer_id, account_number, principal_amount, interest_rate,
                                    tenure_months, start_date, maturity_date, maturity_amount)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (fd_id, acc_data[3], acc_data[0], principal, interest_rate,
                                 tenure_months, start_date, maturity_date, maturity_amount))
                        
                        new_balance = acc_data[2] - principal
                        c.execute("UPDATE accounts SET balance = ? WHERE account_number = ?", (new_balance, acc_data[0]))
                        
                        trans_id = generate_id("TXN")
                        c.execute("""INSERT INTO transactions 
                                   (transaction_id, account_number, transaction_type, amount, 
                                    balance_before, balance_after, description)
                                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                (trans_id, acc_data[0], 'fd_created', principal, acc_data[2], new_balance, f'FD: {fd_id}'))
                        
                        conn.commit()
                        add_audit_log(st.session_state.user_id, 'CREATE_FD', 'fixed_deposits', fd_id)
                        st.success(f"FD created! ID: {fd_id}")
                        conn.close()
        else:
            st.info("No active accounts with balance")
        
        # Active FDs
        st.markdown("---")
        st.markdown("### Active Fixed Deposits")
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""SELECT fd_id, customer_id, principal_amount, interest_rate, maturity_date, maturity_amount 
                    FROM fixed_deposits WHERE status = 'active'""")
        fds = c.fetchall()
        conn.close()
        if fds:
            df = pd.DataFrame(fds, columns=['FD ID', 'Customer', 'Principal', 'Rate', 'Maturity', 'Amount'])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No active FDs")
    
    with tab2:
        st.markdown("### Create Recurring Deposit")
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""SELECT a.account_number, c.first_name || ' ' || c.last_name, c.customer_id
                    FROM accounts a JOIN customers c ON a.customer_id = c.customer_id
                    WHERE a.status = 'active'""")
        accounts = c.fetchall()
        conn.close()
        
        if accounts:
            with st.form("rd_form"):
                account_options = {f"{acc[0]} - {acc[1]}": acc for acc in accounts}
                selected_account = st.selectbox("Select Account", list(account_options.keys()))
                
                col1, col2 = st.columns(2)
                with col1:
                    monthly_amount = st.number_input("Monthly Installment *", min_value=500.0, step=100.0)
                    interest_rate = st.number_input("Interest Rate (%) *", min_value=0.1, value=6.0, step=0.25)
                with col2:
                    tenure_months = st.selectbox("Tenure (Months)", [12, 24, 36, 48, 60])
                    start_date = st.date_input("Start Date", datetime.now().date())
                
                maturity_date = start_date + relativedelta(months=tenure_months)
                maturity_amount = calculate_rd_maturity(monthly_amount, interest_rate, tenure_months)
                total_investment = monthly_amount * tenure_months
                
                st.markdown(f"**Maturity Date:** {maturity_date}")
                st.markdown(f"**Total Investment:** ₹{total_investment:,.2f}")
                st.markdown(f"**Maturity Amount:** ₹{maturity_amount:,.2f}")
                st.markdown(f"**Interest Earned:** ₹{maturity_amount - total_investment:,.2f}")
                
                if st.form_submit_button("Create RD"):
                    acc_data = account_options[selected_account]
                    conn = get_db_connection()
                    c = conn.cursor()
                    rd_id = generate_id("RD")
                    c.execute("""INSERT INTO recurring_deposits 
                               (rd_id, customer_id, account_number, monthly_amount, interest_rate,
                                tenure_months, start_date, maturity_date, maturity_amount)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (rd_id, acc_data[2], acc_data[0], monthly_amount, interest_rate,
                             tenure_months, start_date, maturity_date, maturity_amount))
                    conn.commit()
                    add_audit_log(st.session_state.user_id, 'CREATE_RD', 'recurring_deposits', rd_id)
                    st.success(f"RD created! ID: {rd_id}")
                    conn.close()
        else:
            st.info("No active accounts")
        
        # Active RDs
        st.markdown("---")
        st.markdown("### Active Recurring Deposits")
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""SELECT rd_id, customer_id, monthly_amount, interest_rate, maturity_date, maturity_amount 
                    FROM recurring_deposits WHERE status = 'active'""")
        rds = c.fetchall()
        conn.close()
        if rds:
            df = pd.DataFrame(rds, columns=['RD ID', 'Customer', 'Monthly', 'Rate', 'Maturity', 'Amount'])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No active RDs")
    
    with tab3:
        st.markdown("### Apply for Loan")
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""SELECT a.account_number, c.first_name || ' ' || c.last_name, c.customer_id
                    FROM accounts a JOIN customers c ON a.customer_id = c.customer_id
                    WHERE a.status = 'active'""")
        accounts = c.fetchall()
        conn.close()
        
        if accounts:
            with st.form("loan_form"):
                account_options = {f"{acc[0]} - {acc[1]}": acc for acc in accounts}
                selected_account = st.selectbox("Select Account", list(account_options.keys()))
                
                col1, col2 = st.columns(2)
                with col1:
                    loan_type = st.selectbox("Loan Type", ["Personal Loan", "Home Loan", "Car Loan", "Business Loan"])
                    principal = st.number_input("Loan Amount *", min_value=10000.0, step=5000.0)
                with col2:
                    interest_rate = st.number_input("Interest Rate (%) *", min_value=1.0, value=12.0, step=0.5)
                    tenure_months = st.selectbox("Tenure (Months)", [6, 12, 24, 36, 48, 60])
                
                emi = calculate_emi(principal, interest_rate, tenure_months)
                total_repayment = emi * tenure_months
                
                st.markdown(f"**Monthly EMI:** ₹{emi:,.2f}")
                st.markdown(f"**Total Repayment:** ₹{total_repayment:,.2f}")
                st.markdown(f"**Total Interest:** ₹{total_repayment - principal:,.2f}")
                
                if st.form_submit_button("Apply for Loan"):
                    acc_data = account_options[selected_account]
                    conn = get_db_connection()
                    c = conn.cursor()
                    loan_id = generate_id("LOAN")
                    start_date = datetime.now().date()
                    end_date = start_date + relativedelta(months=tenure_months)
                    
                    c.execute("""INSERT INTO loans 
                               (loan_id, customer_id, account_number, loan_type, principal_amount,
                                interest_rate, tenure_months, emi_amount, start_date, end_date, outstanding_amount)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (loan_id, acc_data[2], acc_data[0], loan_type, principal,
                             interest_rate, tenure_months, emi, start_date, end_date, principal))
                    
                    c.execute("SELECT balance FROM accounts WHERE account_number = ?", (acc_data[0],))
                    current_balance = c.fetchone()[0]
                    new_balance = current_balance + principal
                    c.execute("UPDATE accounts SET balance = ? WHERE account_number = ?", (new_balance, acc_data[0]))
                    
                    trans_id = generate_id("TXN")
                    c.execute("""INSERT INTO transactions 
                               (transaction_id, account_number, transaction_type, amount, 
                                balance_before, balance_after, description)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (trans_id, acc_data[0], 'loan_disbursed', principal, current_balance, new_balance, f'Loan: {loan_id}'))
                    
                    conn.commit()
                    add_audit_log(st.session_state.user_id, 'CREATE_LOAN', 'loans', loan_id)
                    st.success(f"Loan approved! ID: {loan_id}. ₹{principal:,.2f} credited.")
                    conn.close()
        else:
            st.info("No active accounts")
        
        # Active Loans
        st.markdown("---")
        st.markdown("### Active Loans")
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""SELECT loan_id, customer_id, loan_type, principal_amount, emi_amount, outstanding_amount 
                    FROM loans WHERE status = 'active'""")
        loans = c.fetchall()
        conn.close()
        if loans:
            df = pd.DataFrame(loans, columns=['Loan ID', 'Customer', 'Type', 'Principal', 'EMI', 'Outstanding'])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No active loans")

# ============================================
# PART 5: JOURNAL VOUCHERS & LEDGER
# ============================================
def accounting_module():
    st.markdown('<h2 class="sub-header">📊 Journal Vouchers & Ledger</h2>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Create Voucher", "General Ledger", "Chart of Accounts"])
    
    with tab1:
        st.markdown("### Create Journal Voucher")
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT account_head FROM chart_of_accounts ORDER BY account_head")
        accounts = [row[0] for row in c.fetchall()]
        conn.close()
        
        with st.form("journal_voucher"):
            voucher_date = st.date_input("Voucher Date", datetime.now().date())
            narration = st.text_area("Narration *")
            
            st.markdown("#### Debit Entries")
            debit_accounts = []
            debit_amounts = []
            
            for i in range(3):
                col1, col2 = st.columns([2, 1])
                with col1:
                    acc = st.selectbox(f"Debit Account {i+1}", [""] + accounts, key=f"debit_{i}")
                with col2:
                    amt = st.number_input(f"Amount {i+1}", min_value=0.0, step=100.0, key=f"debit_amt_{i}")
                if acc and amt > 0:
                    debit_accounts.append(acc)
                    debit_amounts.append(amt)
            
            st.markdown("#### Credit Entries")
            credit_accounts = []
            credit_amounts = []
            
            for i in range(3):
                col1, col2 = st.columns([2, 1])
                with col1:
                    acc = st.selectbox(f"Credit Account {i+1}", [""] + accounts, key=f"credit_{i}")
                with col2:
                    amt = st.number_input(f"Amount {i+1}", min_value=0.0, step=100.0, key=f"credit_amt_{i}")
                if acc and amt > 0:
                    credit_accounts.append(acc)
                    credit_amounts.append(amt)
            
            total_debit = sum(debit_amounts)
            total_credit = sum(credit_amounts)
            
            st.markdown(f"**Total Debit: ₹{total_debit:,.2f} | Total Credit: ₹{total_credit:,.2f}**")
            
            if total_debit != total_credit and (debit_accounts or credit_accounts):
                st.error("Debit and Credit must be equal!")
            
            if st.form_submit_button("Create Voucher"):
                if not narration:
                    st.error("Narration is required!")
                elif not debit_accounts:
                    st.error("At least one debit entry required!")
                elif total_debit != total_credit:
                    st.error("Debit and Credit amounts must match!")
                else:
                    conn = get_db_connection()
                    c = conn.cursor()
                    voucher_id = generate_id("JV")
                    
                    c.execute("""INSERT INTO journal_vouchers 
                               (voucher_id, voucher_date, narration, total_amount, status, created_by)
                               VALUES (?, ?, ?, ?, 'approved', ?)""",
                            (voucher_id, voucher_date, narration, total_debit, st.session_state.user_id))
                    
                    for acc, amt in zip(debit_accounts, debit_amounts):
                        c.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount) VALUES (?, ?, ?, 0)", (voucher_id, acc, amt))
                    
                    for acc, amt in zip(credit_accounts, credit_amounts):
                        c.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount) VALUES (?, ?, 0, ?)", (voucher_id, acc, amt))
                    
                    conn.commit()
                    add_audit_log(st.session_state.user_id, 'CREATE_VOUCHER', 'journal_vouchers', voucher_id)
                    st.success(f"Voucher created! ID: {voucher_id}")
                    conn.close()
        
        # Recent vouchers
        st.markdown("---")
        st.markdown("### Recent Vouchers")
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""SELECT voucher_id, voucher_date, narration, total_amount, status 
                    FROM journal_vouchers ORDER BY created_at DESC LIMIT 10""")
        vouchers = c.fetchall()
        conn.close()
        
        if vouchers:
            for v in vouchers:
                with st.expander(f"📄 {v[0]} - {v[2]} (₹{v[3]:,.2f}) - {v[4]}"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("SELECT account_head, debit_amount, credit_amount FROM journal_entries WHERE voucher_id = ?", (v[0],))
                    entries = c.fetchall()
                    conn.close()
                    
                    entry_data = []
                    for e in entries:
                        entry_data.append({
                            'Account': e[0],
                            'Debit': f"₹{e[1]:,.2f}" if e[1] > 0 else "",
                            'Credit': f"₹{e[2]:,.2f}" if e[2] > 0 else ""
                        })
                    st.dataframe(pd.DataFrame(entry_data), use_container_width=True, hide_index=True)
        else:
            st.info("No vouchers created")
    
    with tab2:
        st.markdown("### General Ledger")
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT DISTINCT account_head FROM chart_of_accounts ORDER BY account_head")
        accounts = [row[0] for row in c.fetchall()]
        conn.close()
        
        selected_account = st.selectbox("Select Account Head", accounts)
        
        if selected_account:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("""SELECT jv.voucher_date, jv.narration, je.debit_amount, je.credit_amount
                        FROM journal_entries je 
                        JOIN journal_vouchers jv ON je.voucher_id = jv.voucher_id
                        WHERE je.account_head = ? AND jv.status = 'approved'
                        ORDER BY jv.voucher_date""", (selected_account,))
            entries = c.fetchall()
            conn.close()
            
            if entries:
                running_balance = 0
                ledger_data = []
                
                for entry in entries:
                    debit, credit = entry[2], entry[3]
                    running_balance += (debit - credit)
                    ledger_data.append({
                        'Date': entry[0],
                        'Narration': entry[1],
                        'Debit': f"₹{debit:,.2f}" if debit > 0 else "",
                        'Credit': f"₹{credit:,.2f}" if credit > 0 else "",
                        'Balance': f"₹{running_balance:,.2f}"
                    })
                
                df = pd.DataFrame(ledger_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.markdown(f"**Closing Balance: ₹{running_balance:,.2f}**")
            else:
                st.info(f"No entries for {selected_account}")
    
    with tab3:
        st.markdown("### Chart of Accounts")
        
        with st.expander("➕ Add New Account Head"):
            with st.form("add_account"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    new_head = st.text_input("Account Head Name")
                with col2:
                    acc_type = st.selectbox("Type", ["asset", "liability", "income", "expense"])
                with col3:
                    category = st.selectbox("Category", ["current_asset", "non_current_asset", "current_liability", "non_current_liability", "operating_income", "non_operating_income", "operating_expense", "non_operating_expense"])
                
                if st.form_submit_button("Add Account"):
                    if new_head:
                        try:
                            conn = get_db_connection()
                            c = conn.cursor()
                            c.execute("INSERT INTO chart_of_accounts (account_head, account_type, category) VALUES (?, ?, ?)",
                                    (new_head.upper().replace(' ', '_'), acc_type, category))
                            conn.commit()
                            conn.close()
                            st.success(f"Added: {new_head}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT account_type, account_head, category FROM chart_of_accounts ORDER BY account_type, account_head")
        accounts = c.fetchall()
        conn.close()
        
        current_type = ""
        for acc in accounts:
            if acc[0] != current_type:
                current_type = acc[0]
                st.markdown(f"### {current_type.upper()}S")
            st.markdown(f"- **{acc[1]}** ({acc[2].replace('_', ' ').title()})")

# ============================================
# PART 6: FINANCIAL STATEMENTS
# ============================================
def financial_statements():
    st.markdown('<h2 class="sub-header">💹 Financial Statements</h2>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Trial Balance", "Profit & Loss", "Balance Sheet"])
    
    with tab1:
        st.markdown("### Trial Balance")
        as_of_date = st.date_input("As of Date", datetime.now().date())
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""SELECT je.account_head, SUM(je.debit_amount) as total_debit, SUM(je.credit_amount) as total_credit
                    FROM journal_entries je 
                    JOIN journal_vouchers jv ON je.voucher_id = jv.voucher_id
                    WHERE jv.voucher_date <= ? AND jv.status = 'approved'
                    GROUP BY je.account_head ORDER BY je.account_head""", (as_of_date,))
        entries = c.fetchall()
        conn.close()
        
        if entries:
            trial_data = []
            total_debit = 0
            total_credit = 0
            
            for entry in entries:
                balance = entry[1] - entry[2]
                if balance > 0:
                    dr, cr = balance, 0
                    total_debit += balance
                else:
                    dr, cr = 0, abs(balance)
                    total_credit += abs(balance)
                
                trial_data.append({
                    'Account Head': entry[0],
                    'Debit (₹)': f"₹{dr:,.2f}",
                    'Credit (₹)': f"₹{cr:,.2f}"
                })
            
            trial_data.append({
                'Account Head': 'TOTAL',
                'Debit (₹)': f"₹{total_debit:,.2f}",
                'Credit (₹)': f"₹{total_credit:,.2f}"
            })
            
            st.dataframe(pd.DataFrame(trial_data), use_container_width=True, hide_index=True)
            
            if abs(total_debit - total_credit) < 0.01:
                st.success("✅ Trial Balance is balanced!")
            else:
                st.error(f"❌ Difference: ₹{abs(total_debit - total_credit):,.2f}")
        else:
            st.info("No entries found")
    
    with tab2:
        st.markdown("### Profit & Loss Statement")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("From", datetime.now().replace(day=1))
        with col2:
            end_date = st.date_input("To", datetime.now().date())
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Income
        c.execute("""SELECT je.account_head, SUM(je.credit_amount) - SUM(je.debit_amount) as balance
                    FROM journal_entries je 
                    JOIN journal_vouchers jv ON je.voucher_id = jv.voucher_id
                    JOIN chart_of_accounts coa ON je.account_head = coa.account_head
                    WHERE coa.account_type = 'income' AND jv.voucher_date BETWEEN ? AND ? AND jv.status = 'approved'
                    GROUP BY je.account_head""", (start_date, end_date))
        income_entries = c.fetchall()
        
        # Expenses
        c.execute("""SELECT je.account_head, SUM(je.debit_amount) - SUM(je.credit_amount) as balance
                    FROM journal_entries je 
                    JOIN journal_vouchers jv ON je.voucher_id = jv.voucher_id
                    JOIN chart_of_accounts coa ON je.account_head = coa.account_head
                    WHERE coa.account_type = 'expense' AND jv.voucher_date BETWEEN ? AND ? AND jv.status = 'approved'
                    GROUP BY je.account_head""", (start_date, end_date))
        expense_entries = c.fetchall()
        conn.close()
        
        st.markdown("#### Income")
        total_income = 0
        for entry in income_entries:
            if entry[1] > 0:
                total_income += entry[1]
                st.markdown(f"- **{entry[0]}:** ₹{entry[1]:,.2f}")
        st.markdown(f"**Total Income: ₹{total_income:,.2f}**")
        
        st.markdown("---")
        st.markdown("#### Expenses")
        total_expenses = 0
        for entry in expense_entries:
            if entry[1] > 0:
                total_expenses += entry[1]
                st.markdown(f"- **{entry[0]}:** ₹{entry[1]:,.2f}")
        st.markdown(f"**Total Expenses: ₹{total_expenses:,.2f}**")
        
        st.markdown("---")
        net_profit = total_income - total_expenses
        if net_profit >= 0:
            st.success(f"💰 Net Profit: ₹{net_profit:,.2f}")
        else:
            st.error(f"📉 Net Loss: ₹{abs(net_profit):,.2f}")
    
    with tab3:
        st.markdown("### Balance Sheet")
        balance_date = st.date_input("As at", datetime.now().date(), key="bs_date")
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Assets
        c.execute("""SELECT je.account_head, SUM(je.debit_amount) - SUM(je.credit_amount) as balance
                    FROM journal_entries je 
                    JOIN journal_vouchers jv ON je.voucher_id = jv.voucher_id
                    JOIN chart_of_accounts coa ON je.account_head = coa.account_head
                    WHERE coa.account_type = 'asset' AND jv.voucher_date <= ? AND jv.status = 'approved'
                    GROUP BY je.account_head""", (balance_date,))
        assets = c.fetchall()
        
        # Liabilities
        c.execute("""SELECT je.account_head, SUM(je.credit_amount) - SUM(je.debit_amount) as balance
                    FROM journal_entries je 
                    JOIN journal_vouchers jv ON je.voucher_id = jv.voucher_id
                    JOIN chart_of_accounts coa ON je.account_head = coa.account_head
                    WHERE coa.account_type = 'liability' AND jv.voucher_date <= ? AND jv.status = 'approved'
                    GROUP BY je.account_head""", (balance_date,))
        liabilities = c.fetchall()
        conn.close()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### ASSETS")
            total_assets = 0
            for asset in assets:
                if asset[1] > 0:
                    total_assets += asset[1]
                    st.markdown(f"- **{asset[0]}:** ₹{asset[1]:,.2f}")
            st.markdown(f"**Total Assets: ₹{total_assets:,.2f}**")
        
        with col2:
            st.markdown("### LIABILITIES & EQUITY")
            total_liabilities = 0
            for liability in liabilities:
                if liability[1] > 0:
                    total_liabilities += liability[1]
                    st.markdown(f"- **{liability[0]}:** ₹{liability[1]:,.2f}")
            
            equity = total_assets - total_liabilities
            st.markdown(f"- **Owner's Equity:** ₹{equity:,.2f}")
            total_liabilities += equity
            st.markdown(f"**Total Liabilities & Equity: ₹{total_liabilities:,.2f}**")
        
        if abs(total_assets - total_liabilities) < 0.01:
            st.success("✅ Balance Sheet is balanced!")
        else:
            st.error(f"❌ Difference: ₹{abs(total_assets - total_liabilities):,.2f}")

# ============================================
# PART 7: DASHBOARD & REPORTS
# ============================================
def reports_dashboard():
    st.markdown('<h2 class="sub-header">📑 Dashboard & Reports</h2>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Dashboard", "Reports", "Audit Logs"])
    
    with tab1:
        st.markdown("### 📊 Banking Dashboard")
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Key metrics
        c.execute("SELECT COUNT(*) FROM customers")
        total_customers = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM accounts WHERE status = 'active'")
        total_accounts = c.fetchone()[0]
        
        c.execute("SELECT SUM(balance) FROM accounts WHERE status = 'active'")
        total_deposits = c.fetchone()[0] or 0
        
        c.execute("SELECT SUM(outstanding_amount) FROM loans WHERE status = 'active'")
        total_loans = c.fetchone()[0] or 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Customers", total_customers)
        with col2:
            st.metric("Active Accounts", total_accounts)
        with col3:
            st.metric("Total Deposits", f"₹{total_deposits:,.0f}")
        with col4:
            st.metric("Loans Outstanding", f"₹{total_loans:,.0f}")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Account Distribution")
            c.execute("SELECT account_type, COUNT(*) FROM accounts WHERE status = 'active' GROUP BY account_type")
            acc_types = c.fetchall()
            if acc_types:
                fig = px.pie(values=[x[1] for x in acc_types], names=[x[0] for x in acc_types])
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### Recent Transactions")
            c.execute("""SELECT transaction_type, amount, timestamp FROM transactions 
                        ORDER BY timestamp DESC LIMIT 10""")
            txns = c.fetchall()
            if txns:
                df = pd.DataFrame(txns, columns=['Type', 'Amount', 'Date'])
                fig = px.bar(df, x='Date', y='Amount', color='Type')
                st.plotly_chart(fig, use_container_width=True)
        
        conn.close()
    
    with tab2:
        st.markdown("### 📋 Reports")
        
        report_type = st.selectbox("Select Report", [
            "Customer List", "Account Statement", "Transaction Report", 
            "FD Report", "RD Report", "Loan Report"
        ])
        
        conn = get_db_connection()
        c = conn.cursor()
        
        if report_type == "Customer List":
            c.execute("SELECT * FROM customers ORDER BY created_at DESC")
            data = c.fetchall()
            if data:
                df = pd.DataFrame(data, columns=['ID', 'First', 'Last', 'DOB', 'Email', 'Phone', 'Address', 'ID Type', 'ID No', 'KYC', 'KYC Date', 'Created', 'By'])
                st.dataframe(df, use_container_width=True)
                st.download_button("Download CSV", df.to_csv(index=False), "customers.csv")
        
        elif report_type == "Transaction Report":
            c.execute("SELECT * FROM transactions ORDER BY timestamp DESC LIMIT 100")
            data = c.fetchall()
            if data:
                df = pd.DataFrame(data, columns=['ID', 'Account', 'Type', 'Amount', 'Before', 'After', 'Desc', 'Date'])
                st.dataframe(df, use_container_width=True)
                st.download_button("Download CSV", df.to_csv(index=False), "transactions.csv")
        
        elif report_type == "FD Report":
            c.execute("SELECT * FROM fixed_deposits ORDER BY start_date DESC")
            data = c.fetchall()
            if data:
                df = pd.DataFrame(data, columns=['FD ID', 'Customer', 'Account', 'Principal', 'Rate', 'Tenure', 'Start', 'Maturity', 'Amount', 'Status'])
                st.dataframe(df, use_container_width=True)
        
        elif report_type == "RD Report":
            c.execute("SELECT * FROM recurring_deposits ORDER BY start_date DESC")
            data = c.fetchall()
            if data:
                df = pd.DataFrame(data, columns=['RD ID', 'Customer', 'Account', 'Monthly', 'Rate', 'Tenure', 'Start', 'Maturity', 'Amount', 'Paid', 'Status'])
                st.dataframe(df, use_container_width=True)
        
        elif report_type == "Loan Report":
            c.execute("SELECT * FROM loans ORDER BY start_date DESC")
            data = c.fetchall()
            if data:
                df = pd.DataFrame(data, columns=['Loan ID', 'Customer', 'Account', 'Type', 'Principal', 'Rate', 'Tenure', 'EMI', 'Start', 'End', 'Outstanding', 'Status'])
                st.dataframe(df, use_container_width=True)
        
        conn.close()
    
    with tab3:
        st.markdown("### 🔍 Audit Logs")
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""SELECT al.log_id, u.username, al.action, al.table_affected, al.record_id, al.timestamp 
                    FROM audit_logs al LEFT JOIN users u ON al.user_id = u.id 
                    ORDER BY al.timestamp DESC LIMIT 100""")
        logs = c.fetchall()
        conn.close()
        
        if logs:
            df = pd.DataFrame(logs, columns=['ID', 'User', 'Action', 'Table', 'Record', 'Timestamp'])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No audit logs")

# ============================================
# MAIN APP
# ============================================
def main():
    init_session_state()
    
    try:
        init_database()
    except Exception as e:
        st.error(f"Database error: {e}")
        if st.button("Reset Database"):
            if os.path.exists('banking_system.db'):
                os.remove('banking_system.db')
            st.rerun()
        return
    
    if not st.session_state.logged_in:
        login_page()
        return
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"### Welcome, {st.session_state.username}!")
        st.markdown(f"**Role:** {st.session_state.role}")
        st.markdown("---")
        st.markdown("### Navigation")
        
        menu_options = {
            "📋 Customer Registration": "customer",
            "💰 Account Management": "accounts",
            "📈 FD / RD / Loans": "investments",
            "📊 Journal & Ledger": "accounting",
            "💹 Financial Statements": "financials",
            "📑 Dashboard & Reports": "dashboard",
        }
        
        selected_menu = st.radio("Select Module", list(menu_options.keys()), label_visibility="collapsed")
        
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            if st.session_state.user_id:
                add_audit_log(st.session_state.user_id, 'LOGOUT', 'users', str(st.session_state.user_id))
            for key in ['logged_in', 'username', 'user_id', 'role']:
                st.session_state[key] = None if key != 'logged_in' else False
            st.rerun()
    
    # Main content
    selected = menu_options[selected_menu]
    
    if selected == "customer":
        customer_registration()
    elif selected == "accounts":
        account_management()
    elif selected == "investments":
        investments_loans()
    elif selected == "accounting":
        accounting_module()
    elif selected == "financials":
        financial_statements()
    elif selected == "dashboard":
        reports_dashboard()

if __name__ == "__main__":
    main()
      
