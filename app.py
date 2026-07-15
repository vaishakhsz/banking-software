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
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-radius: 0.5rem;
        color: #155724;
    }
    .warning-box {
        padding: 1rem;
        background-color: #fff3cd;
        border-radius: 0.5rem;
        color: #856404;
    }
    </style>
""", unsafe_allow_html=True)

# Database initialization
def init_database():
    conn = sqlite3.connect('banking_system.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
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
        balance DECIMAL(15,2) DEFAULT 0.00,
        interest_rate DECIMAL(5,2) DEFAULT 0.00,
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
        amount DECIMAL(15,2) NOT NULL,
        balance_before DECIMAL(15,2),
        balance_after DECIMAL(15,2),
        description TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (account_number) REFERENCES accounts (account_number)
    )''')
    
    # FD/RD Accounts
    c.execute('''CREATE TABLE IF NOT EXISTS fixed_deposits (
        fd_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        account_number TEXT NOT NULL,
        principal_amount DECIMAL(15,2) NOT NULL,
        interest_rate DECIMAL(5,2) NOT NULL,
        tenure_months INTEGER NOT NULL,
        start_date DATE NOT NULL,
        maturity_date DATE NOT NULL,
        maturity_amount DECIMAL(15,2),
        status TEXT DEFAULT 'active',
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
        FOREIGN KEY (account_number) REFERENCES accounts (account_number)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS recurring_deposits (
        rd_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        account_number TEXT NOT NULL,
        monthly_amount DECIMAL(15,2) NOT NULL,
        interest_rate DECIMAL(5,2) NOT NULL,
        tenure_months INTEGER NOT NULL,
        start_date DATE NOT NULL,
        maturity_date DATE NOT NULL,
        maturity_amount DECIMAL(15,2),
        installments_paid INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
        FOREIGN KEY (account_number) REFERENCES accounts (account_number)
    )''')
    
    # Loans table
    c.execute('''CREATE TABLE IF NOT EXISTS loans (
        loan_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        account_number TEXT NOT NULL,
        loan_type TEXT NOT NULL,
        principal_amount DECIMAL(15,2) NOT NULL,
        interest_rate DECIMAL(5,2) NOT NULL,
        tenure_months INTEGER NOT NULL,
        emi_amount DECIMAL(15,2),
        start_date DATE NOT NULL,
        end_date DATE,
        outstanding_amount DECIMAL(15,2),
        status TEXT DEFAULT 'active',
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
        FOREIGN KEY (account_number) REFERENCES accounts (account_number)
    )''')
    
    # EMI Payments
    c.execute('''CREATE TABLE IF NOT EXISTS emi_payments (
        payment_id TEXT PRIMARY KEY,
        loan_id TEXT NOT NULL,
        payment_date DATE NOT NULL,
        amount DECIMAL(15,2) NOT NULL,
        principal_component DECIMAL(15,2),
        interest_component DECIMAL(15,2),
        outstanding_after DECIMAL(15,2),
        FOREIGN KEY (loan_id) REFERENCES loans (loan_id)
    )''')
    
    # Journal Vouchers
    c.execute('''CREATE TABLE IF NOT EXISTS journal_vouchers (
        voucher_id TEXT PRIMARY KEY,
        voucher_date DATE NOT NULL,
        narration TEXT,
        total_amount DECIMAL(15,2),
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
        debit_amount DECIMAL(15,2) DEFAULT 0.00,
        credit_amount DECIMAL(15,2) DEFAULT 0.00,
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
    
    # Insert default admin user if not exists
    c.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    if c.fetchone()[0] == 0:
        admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                 ('admin', admin_password, 'admin'))
        
        # Insert default staff user
        staff_password = hashlib.sha256('staff123'.encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                 ('staff', staff_password, 'staff'))
    
    # Insert default chart of accounts if not exists
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
        ('SALARY', 'expense', 'operating_expense'),
        ('RENT', 'expense', 'operating_expense'),
        ('UTILITIES', 'expense', 'operating_expense'),
    ]
    
    for account in default_accounts:
        c.execute("INSERT OR IGNORE INTO chart_of_accounts (account_head, account_type, category) VALUES (?, ?, ?)", account)
    
    conn.commit()
    return conn

# Session state initialization
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
def generate_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8].upper()}"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def add_audit_log(conn, user_id, action, table_affected, record_id, old_values=None, new_values=None):
    c = conn.cursor()
    c.execute("""INSERT INTO audit_logs (user_id, action, table_affected, record_id, old_values, new_values) 
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (user_id, action, table_affected, record_id, 
               json.dumps(old_values) if old_values else None,
               json.dumps(new_values) if new_values else None))
    conn.commit()

def calculate_emi(principal, annual_rate, tenure_months):
    monthly_rate = annual_rate / (12 * 100)
    emi = principal * monthly_rate * (1 + monthly_rate) ** tenure_months / ((1 + monthly_rate) ** tenure_months - 1)
    return round(emi, 2)

def calculate_fd_maturity(principal, annual_rate, tenure_months):
    rate = annual_rate / 100
    # Quarterly compounding
    n = 4
    t = tenure_months / 12
    amount = principal * (1 + rate/n) ** (n * t)
    return round(amount, 2)

def calculate_rd_maturity(monthly_amount, annual_rate, tenure_months):
    rate = annual_rate / 100
    # Quarterly compounding for RD
    n = 4
    total = 0
    for i in range(tenure_months):
        remaining_months = tenure_months - i
        total += monthly_amount * (1 + rate/n) ** (n * remaining_months/12)
    return round(total, 2)

# Part 1: Login, Database Setup, Customer Registration, KYC
def login_page():
    st.markdown('<h1 class="main-header">🏦 Banking Management System</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<h3 class="sub-header">Login</h3>', unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                conn = init_database()
                c = conn.cursor()
                
                hashed_pw = hash_password(password)
                c.execute("SELECT id, username, role FROM users WHERE username = ? AND password = ?", 
                         (username, hashed_pw))
                user = c.fetchone()
                
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user[0]
                    st.session_state.username = user[1]
                    st.session_state.role = user[2]
                    
                    add_audit_log(conn, user[0], 'LOGIN', 'users', str(user[0]))
                    
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
                conn.close()

def customer_registration():
    st.markdown('<h2 class="sub-header">Customer Registration & KYC</h2>', unsafe_allow_html=True)
    
    conn = init_database()
    
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
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submit = st.form_submit_button("Register Customer", use_container_width=True)
            
            if submit:
                if not first_name or not last_name:
                    st.error("First name and last name are required!")
                elif id_proof_type != "Select" and not id_proof_number:
                    st.error("ID proof number is required when proof type is selected!")
                else:
                    customer_id = generate_id("CUST")
                    c = conn.cursor()
                    
                    try:
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
                        
                        add_audit_log(conn, st.session_state.user_id, 'CREATE', 'customers', customer_id,
                                    new_values={'first_name': first_name, 'last_name': last_name})
                        
                        st.success(f"Customer registered successfully! Customer ID: {customer_id}")
                        
                    except Exception as e:
                        st.error(f"Error registering customer: {e}")
    
    # Display existing customers
    st.markdown("---")
    st.markdown("### Existing Customers")
    
    c = conn.cursor()
    c.execute("""SELECT customer_id, first_name, last_name, phone, email, kyc_status, created_at 
                 FROM customers ORDER BY created_at DESC LIMIT 20""")
    customers = c.fetchall()
    
    if customers:
        df = pd.DataFrame(customers, columns=['Customer ID', 'First Name', 'Last Name', 'Phone', 
                                              'Email', 'KYC Status', 'Created At'])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No customers registered yet")
    
    conn.close()

# Part 2: Savings/Current Accounts, Deposits, Withdrawals
def account_management():
    st.markdown('<h2 class="sub-header">Account Management</h2>', unsafe_allow_html=True)
    
    conn = init_database()
    
    tab1, tab2, tab3 = st.tabs(["Open Account", "Deposit", "Withdraw"])
    
    with tab1:
        st.markdown("### Open New Account")
        
        with st.form("open_account"):
            col1, col2 = st.columns(2)
            
            with col1:
                c = conn.cursor()
                c.execute("SELECT customer_id, first_name, last_name FROM customers WHERE kyc_status = 'completed'")
                customers = c.fetchall()
                
                if customers:
                    customer_options = {f"{c[1]} {c[2]} ({c[0]})": c[0] for c in customers}
                    selected_customer = st.selectbox("Select Customer *", list(customer_options.keys()))
                    
                    account_type = st.selectbox("Account Type *", 
                                              ["Savings Account", "Current Account"])
                    
                    initial_deposit = st.number_input("Initial Deposit", min_value=0.0, value=500.0, step=100.0)
                
                else:
                    st.warning("No customers with completed KYC available")
                    selected_customer = None
                    account_type = None
                    initial_deposit = 0
            
            with col2:
                if account_type == "Savings Account":
                    interest_rate = st.number_input("Interest Rate (%)", min_value=0.0, value=4.0, step=0.25)
                    min_balance = st.number_input("Minimum Balance", value=500.0, step=100.0)
                else:
                    interest_rate = 0.0
                    min_balance = st.number_input("Minimum Balance", value=1000.0, step=500.0)
                
                st.markdown(f"**Min Balance Required:** ₹{min_balance:,.2f}")
            
            submit = st.form_submit_button("Open Account")
            
            if submit and selected_customer:
                if initial_deposit < min_balance:
                    st.error(f"Initial deposit must be at least ₹{min_balance:,.2f}")
                else:
                    customer_id = customer_options[selected_customer]
                    account_number = generate_id("ACC")
                    
                    c.execute("""INSERT INTO accounts 
                               (account_number, customer_id, account_type, balance, interest_rate, opened_date)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (account_number, customer_id, account_type, initial_deposit, 
                             interest_rate, datetime.now().date()))
                    
                    # Record initial deposit transaction
                    if initial_deposit > 0:
                        trans_id = generate_id("TXN")
                        c.execute("""INSERT INTO transactions 
                                   (transaction_id, account_number, transaction_type, amount, 
                                    balance_before, balance_after, description)
                                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                (trans_id, account_number, 'deposit', initial_deposit,
                                 0.0, initial_deposit, 'Initial deposit - Account opening'))
                    
                    conn.commit()
                    
                    add_audit_log(conn, st.session_state.user_id, 'CREATE', 'accounts', account_number,
                                new_values={'customer_id': customer_id, 'account_type': account_type, 'balance': initial_deposit})
                    
                    st.success(f"Account opened successfully! Account Number: {account_number}")
    
    with tab2:
        st.markdown("### Deposit Money")
        
        with st.form("deposit_form"):
            c = conn.cursor()
            c.execute("SELECT account_number, customer_id, account_type, balance FROM accounts WHERE status = 'active'")
            accounts = c.fetchall()
            
            if accounts:
                account_options = {f"{acc[0]} - {acc[2]} (Balance: ₹{acc[3]:,.2f})": acc for acc in accounts}
                selected_account = st.selectbox("Select Account *", list(account_options.keys()))
                
                amount = st.number_input("Deposit Amount *", min_value=1.0, step=100.0)
                description = st.text_input("Description")
                
                submit = st.form_submit_button("Deposit")
                
                if submit and selected_account:
                    acc_data = account_options[selected_account]
                    new_balance = acc_data[3] + amount
                    
                    trans_id = generate_id("TXN")
                    c.execute("""INSERT INTO transactions 
                               (transaction_id, account_number, transaction_type, amount, 
                                balance_before, balance_after, description)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (trans_id, acc_data[0], 'deposit', amount, acc_data[3], new_balance, description))
                    
                    c.execute("UPDATE accounts SET balance = ? WHERE account_number = ?",
                            (new_balance, acc_data[0]))
                    
                    conn.commit()
                    
                    add_audit_log(conn, st.session_state.user_id, 'DEPOSIT', 'transactions', trans_id,
                                new_values={'amount': amount, 'account': acc_data[0]})
                    
                    st.success(f"Deposited ₹{amount:,.2f} successfully! New Balance: ₹{new_balance:,.2f}")
            else:
                st.info("No active accounts available")
    
    with tab3:
        st.markdown("### Withdraw Money")
        
        with st.form("withdraw_form"):
            c = conn.cursor()
            c.execute("SELECT account_number, customer_id, account_type, balance FROM accounts WHERE status = 'active'")
            accounts = c.fetchall()
            
            if accounts:
                account_options = {f"{acc[0]} - {acc[2]} (Balance: ₹{acc[3]:,.2f})": acc for acc in accounts}
                selected_account = st.selectbox("Select Account *", list(account_options.keys()))
                
                acc_data = account_options[selected_account]
                max_withdrawal = acc_data[3]
                
                amount = st.number_input("Withdrawal Amount *", min_value=1.0, max_value=max_withdrawal, step=100.0)
                description = st.text_input("Description")
                
                submit = st.form_submit_button("Withdraw")
                
                if submit and selected_account:
                    new_balance = acc_data[3] - amount
                    
                    trans_id = generate_id("TXN")
                    c.execute("""INSERT INTO transactions 
                               (transaction_id, account_number, transaction_type, amount, 
                                balance_before, balance_after, description)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (trans_id, acc_data[0], 'withdrawal', amount, acc_data[3], new_balance, description))
                    
                    c.execute("UPDATE accounts SET balance = ? WHERE account_number = ?",
                            (new_balance, acc_data[0]))
                    
                    conn.commit()
                    
                    add_audit_log(conn, st.session_state.user_id, 'WITHDRAW', 'transactions', trans_id,
                                new_values={'amount': amount, 'account': acc_data[0]})
                    
                    st.success(f"Withdrew ₹{amount:,.2f} successfully! New Balance: ₹{new_balance:,.2f}")
            else:
                st.info("No active accounts available")
    
    # Account List
    st.markdown("---")
    st.markdown("### Active Accounts")
    
    c.execute("""SELECT a.account_number, c.first_name || ' ' || c.last_name as customer_name,
                 a.account_type, a.balance, a.interest_rate, a.opened_date, a.status
                 FROM accounts a JOIN customers c ON a.customer_id = c.customer_id
                 ORDER BY a.opened_date DESC""")
    accounts = c.fetchall()
    
    if accounts:
        df = pd.DataFrame(accounts, columns=['Account No', 'Customer', 'Type', 'Balance', 
                                             'Interest Rate', 'Opened Date', 'Status'])
        df['Balance'] = df['Balance'].apply(lambda x: f"₹{x:,.2f}")
        df['Interest Rate'] = df['Interest Rate'].apply(lambda x: f"{x}%")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No accounts found")
    
    conn.close()

# Part 3: FD, RD, Loans
def investment_loans():
    st.markdown('<h2 class="sub-header">Fixed Deposits, Recurring Deposits & Loans</h2>', unsafe_allow_html=True)
    
    conn = init_database()
    
    tab1, tab2, tab3 = st.tabs(["Fixed Deposits", "Recurring Deposits", "Loans"])
    
    with tab1:
        st.markdown("### Create Fixed Deposit")
        
        with st.form("fd_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                c = conn.cursor()
                c.execute("""SELECT a.account_number, c.first_name || ' ' || c.last_name, a.balance
                            FROM accounts a JOIN customers c ON a.customer_id = c.customer_id
                            WHERE a.status = 'active' AND a.balance > 0""")
                accounts = c.fetchall()
                
                if accounts:
                    account_options = {f"{acc[0]} - {acc[1]} (₹{acc[2]:,.2f})": acc for acc in accounts}
                    selected_account = st.selectbox("Select Account *", list(account_options.keys()))
                    
                    principal = st.number_input("Principal Amount *", min_value=1000.0, step=1000.0)
                    interest_rate = st.number_input("Interest Rate (%) *", min_value=0.1, value=6.5, step=0.25)
                    
                else:
                    st.warning("No active accounts with balance available")
                    selected_account = None
                    principal = 0
                    interest_rate = 0
            
            with col2:
                tenure_months = st.selectbox("Tenure (Months) *", [3, 6, 12, 24, 36, 60])
                start_date = st.date_input("Start Date", datetime.now().date())
                
                maturity_date = start_date + relativedelta(months=tenure_months)
                maturity_amount = calculate_fd_maturity(principal, interest_rate, tenure_months)
                
                st.markdown(f"**Maturity Date:** {maturity_date}")
                st.markdown(f"**Maturity Amount:** ₹{maturity_amount:,.2f}")
                st.markdown(f"**Total Interest:** ₹{maturity_amount - principal:,.2f}")
            
            submit = st.form_submit_button("Create Fixed Deposit")
            
            if submit and selected_account:
                acc_data = account_options[selected_account]
                
                if principal > acc_data[2]:
                    st.error("Insufficient balance!")
                else:
                    fd_id = generate_id("FD")
                    c.execute("""INSERT INTO fixed_deposits 
                               (fd_id, customer_id, account_number, principal_amount, interest_rate,
                                tenure_months, start_date, maturity_date, maturity_amount)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (fd_id, acc_data[0], acc_data[0], principal, interest_rate,
                             tenure_months, start_date, maturity_date, maturity_amount))
                    
                    # Deduct from account
                    new_balance = acc_data[2] - principal
                    c.execute("UPDATE accounts SET balance = ? WHERE account_number = ?",
                            (new_balance, acc_data[0]))
                    
                    # Record transaction
                    trans_id = generate_id("TXN")
                    c.execute("""INSERT INTO transactions 
                               (transaction_id, account_number, transaction_type, amount, 
                                balance_before, balance_after, description)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (trans_id, acc_data[0], 'fd_created', principal,
                             acc_data[2], new_balance, f'FD Created - {fd_id}'))
                    
                    conn.commit()
                    
                    add_audit_log(conn, st.session_state.user_id, 'CREATE_FD', 'fixed_deposits', fd_id,
                                new_values={'principal': principal, 'tenure': tenure_months})
                    
                    st.success(f"FD created successfully! FD ID: {fd_id}")
    
    with tab2:
        st.markdown("### Create Recurring Deposit")
        
        with st.form("rd_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                c = conn.cursor()
                c.execute("""SELECT a.account_number, c.first_name || ' ' || c.last_name, a.balance
                            FROM accounts a JOIN customers c ON a.customer_id = c.customer_id
                            WHERE a.status = 'active'""")
                accounts = c.fetchall()
                
                if accounts:
                    account_options = {f"{acc[0]} - {acc[1]}" : acc for acc in accounts}
                    selected_account = st.selectbox("Select Account *", list(account_options.keys()))
                    
                    monthly_amount = st.number_input("Monthly Installment *", min_value=500.0, step=100.0)
                    interest_rate = st.number_input("Interest Rate (%) *", min_value=0.1, value=6.0, step=0.25)
                    
                else:
                    st.warning("No active accounts available")
                    selected_account = None
                    monthly_amount = 0
                    interest_rate = 0
            
            with col2:
                tenure_months = st.selectbox("Tenure (Months) *", [12, 24, 36, 48, 60])
                start_date = st.date_input("Start Date", datetime.now().date())
                
                maturity_date = start_date + relativedelta(months=tenure_months)
                maturity_amount = calculate_rd_maturity(monthly_amount, interest_rate, tenure_months)
                total_investment = monthly_amount * tenure_months
                
                st.markdown(f"**Maturity Date:** {maturity_date}")
                st.markdown(f"**Total Investment:** ₹{total_investment:,.2f}")
                st.markdown(f"**Maturity Amount:** ₹{maturity_amount:,.2f}")
                st.markdown(f"**Total Interest:** ₹{maturity_amount - total_investment:,.2f}")
            
            submit = st.form_submit_button("Create Recurring Deposit")
            
            if submit and selected_account:
                acc_data = account_options[selected_account]
                
                rd_id = generate_id("RD")
                c.execute("""INSERT INTO recurring_deposits 
                           (rd_id, customer_id, account_number, monthly_amount, interest_rate,
                            tenure_months, start_date, maturity_date, maturity_amount)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (rd_id, acc_data[0], acc_data[0], monthly_amount, interest_rate,
                         tenure_months, start_date, maturity_date, maturity_amount))
                
                conn.commit()
                
                add_audit_log(conn, st.session_state.user_id, 'CREATE_RD', 'recurring_deposits', rd_id,
                            new_values={'monthly_amount': monthly_amount, 'tenure': tenure_months})
                
                st.success(f"RD created successfully! RD ID: {rd_id}")
    
    with tab3:
        st.markdown("### Apply for Loan")
        
        with st.form("loan_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                c = conn.cursor()
                c.execute("""SELECT a.account_number, c.first_name || ' ' || c.last_name, 
                            c.customer_id
                            FROM accounts a JOIN customers c ON a.customer_id = c.customer_id
                            WHERE a.status = 'active'""")
                accounts = c.fetchall()
                
                if accounts:
                    account_options = {f"{acc[0]} - {acc[1]}" : acc for acc in accounts}
                    selected_account = st.selectbox("Select Account *", list(account_options.keys()))
                    
                    loan_type = st.selectbox("Loan Type *", 
                                           ["Personal Loan", "Home Loan", "Car Loan", "Business Loan"])
                    principal = st.number_input("Loan Amount *", min_value=10000.0, step=5000.0)
                    
                else:
                    st.warning("No active accounts available")
                    selected_account = None
                    loan_type = None
                    principal = 0
            
            with col2:
                interest_rate = st.number_input("Interest Rate (%) *", min_value=1.0, value=12.0, step=0.5)
                tenure_months = st.selectbox("Tenure (Months) *", [6, 12, 24, 36, 48, 60])
                
                emi = calculate_emi(principal, interest_rate, tenure_months)
                total_repayment = emi * tenure_months
                total_interest = total_repayment - principal
                
                st.markdown(f"**Monthly EMI:** ₹{emi:,.2f}")
                st.markdown(f"**Total Repayment:** ₹{total_repayment:,.2f}")
                st.markdown(f"**Total Interest:** ₹{total_interest:,.2f}")
            
            submit = st.form_submit_button("Apply for Loan")
            
            if submit and selected_account:
                acc_data = account_options[selected_account]
                
                loan_id = generate_id("LOAN")
                start_date = datetime.now().date()
                end_date = start_date + relativedelta(months=tenure_months)
                
                c.execute("""INSERT INTO loans 
                           (loan_id, customer_id, account_number, loan_type, principal_amount,
                            interest_rate, tenure_months, emi_amount, start_date, end_date, 
                            outstanding_amount)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (loan_id, acc_data[2], acc_data[0], loan_type, principal,
                         interest_rate, tenure_months, emi, start_date, end_date, principal))
                
                # Credit loan amount to account
                c.execute("SELECT balance FROM accounts WHERE account_number = ?", (acc_data[0],))
                current_balance = c.fetchone()[0]
                new_balance = current_balance + principal
                
                c.execute("UPDATE accounts SET balance = ? WHERE account_number = ?",
                        (new_balance, acc_data[0]))
                
                # Record transaction
                trans_id = generate_id("TXN")
                c.execute("""INSERT INTO transactions 
                           (transaction_id, account_number, transaction_type, amount, 
                            balance_before, balance_after, description)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (trans_id, acc_data[0], 'loan_disbursed', principal,
                         current_balance, new_balance, f'Loan Disbursed - {loan_id}'))
                
                conn.commit()
                
                add_audit_log(conn, st.session_state.user_id, 'CREATE_LOAN', 'loans', loan_id,
                            new_values={'principal': principal, 'emi': emi, 'tenure': tenure_months})
                
                st.success(f"Loan approved! Loan ID: {loan_id}\nAmount ₹{principal:,.2f} credited to your account.")
    
    # Display Active Investments & Loans
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### Active FDs")
        c.execute("""SELECT fd_id, customer_id, principal_amount, interest_rate, 
                    maturity_date, maturity_amount 
                    FROM fixed_deposits WHERE status = 'active' ORDER BY start_date DESC""")
        fds = c.fetchall()
        if fds:
            df = pd.DataFrame(fds, columns=['FD ID', 'Customer', 'Principal', 'Rate', 'Maturity Date', 'Maturity'])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No active FDs")
    
    with col2:
        st.markdown("### Active RDs")
        c.execute("""SELECT rd_id, customer_id, monthly_amount, interest_rate, 
                    maturity_date, maturity_amount 
                    FROM recurring_deposits WHERE status = 'active' ORDER BY start_date DESC""")
        rds = c.fetchall()
        if rds:
            df = pd.DataFrame(rds, columns=['RD ID', 'Customer', 'Monthly', 'Rate', 'Maturity Date', 'Maturity'])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No active RDs")
    
    with col3:
        st.markdown("### Active Loans")
        c.execute("""SELECT loan_id, customer_id, loan_type, principal_amount, 
                    emi_amount, outstanding_amount 
                    FROM loans WHERE status = 'active' ORDER BY start_date DESC""")
        loans = c.fetchall()
        if loans:
            df = pd.DataFrame(loans, columns=['Loan ID', 'Customer', 'Type', 'Principal', 'EMI', 'Outstanding'])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No active loans")
    
    conn.close()

# Part 4: Journal Vouchers, Ledger, Automatic Posting
def accounting_module():
    st.markdown('<h2 class="sub-header">Accounting - Journal Vouchers & Ledger</h2>', unsafe_allow_html=True)
    
    conn = init_database()
    
    tab1, tab2, tab3 = st.tabs(["Journal Vouchers", "General Ledger", "Chart of Accounts"])
    
    with tab1:
        st.markdown("### Create Journal Voucher")
        
        with st.form("journal_voucher"):
            col1, col2 = st.columns(2)
            
            with col1:
                voucher_date = st.date_input("Voucher Date *", datetime.now().date())
                narration = st.text_area("Narration *")
            
            with col2:
                st.markdown("#### Debit Entries")
                
                c = conn.cursor()
                c.execute("SELECT account_head, account_type FROM chart_of_accounts ORDER BY account_head")
                accounts = c.fetchall()
                account_heads = [acc[0] for acc in accounts]
                
                debit_accounts = []
                debit_amounts = []
                
                for i in range(3):
                    col_a, col_b = st.columns([2, 1])
                    with col_a:
                        debit_acc = st.selectbox(f"Debit Account {i+1}", [""] + account_heads, key=f"debit_{i}")
                    with col_b:
                        debit_amt = st.number_input(f"Amount {i+1}", min_value=0.0, step=100.0, key=f"debit_amt_{i}")
                    
                    if debit_acc and debit_amt > 0:
                        debit_accounts.append(debit_acc)
                        debit_amounts.append(debit_amt)
            
            st.markdown("#### Credit Entries")
            
            credit_accounts = []
            credit_amounts = []
            
            col1, col2, col3 = st.columns(3)
            for i in range(3):
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    credit_acc = st.selectbox(f"Credit Account {i+1}", [""] + account_heads, key=f"credit_{i}")
                with col_b:
                    credit_amt = st.number_input(f"Amount {i+1}", min_value=0.0, step=100.0, key=f"credit_amt_{i}")
                
                if credit_acc and credit_amt > 0:
                    credit_accounts.append(credit_acc)
                    credit_amounts.append(credit_amt)
            
            total_debit = sum(debit_amounts)
            total_credit = sum(credit_amounts)
            
            st.markdown(f"**Total Debit:** ₹{total_debit:,.2f} | **Total Credit:** ₹{total_credit:,.2f}")
            
            if total_debit != total_credit and (debit_accounts or credit_accounts):
                st.error("Debit and Credit amounts must be equal!")
            
            submit = st.form_submit_button("Create Voucher")
            
            if submit and narration and debit_accounts and credit_accounts and total_debit == total_credit:
                voucher_id = generate_id("JV")
                
                c.execute("""INSERT INTO journal_vouchers 
                           (voucher_id, voucher_date, narration, total_amount, status, created_by)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (voucher_id, voucher_date, narration, total_debit, 'approved', st.session_state.user_id))
                
                for acc, amt in zip(debit_accounts, debit_amounts):
                    c.execute("""INSERT INTO journal_entries 
                               (voucher_id, account_head, debit_amount, credit_amount)
                               VALUES (?, ?, ?, ?)""",
                            (voucher_id, acc, amt, 0.00))
                
                for acc, amt in zip(credit_accounts, credit_amounts):
                    c.execute("""INSERT INTO journal_entries 
                               (voucher_id, account_head, debit_amount, credit_amount)
                               VALUES (?, ?, ?, ?)""",
                            (voucher_id, acc, 0.00, amt))
                
                conn.commit()
                
                add_audit_log(conn, st.session_state.user_id, 'CREATE_VOUCHER', 'journal_vouchers', voucher_id,
                            new_values={'narration': narration, 'amount': total_debit})
                
                st.success(f"Journal Voucher created successfully! Voucher ID: {voucher_id}")
        
        # Display recent vouchers
        st.markdown("---")
        st.markdown("### Recent Journal Vouchers")
        
        c.execute("""SELECT jv.voucher_id, jv.voucher_date, jv.narration, jv.total_amount, 
                    u.username, jv.status
                    FROM journal_vouchers jv JOIN users u ON jv.created_by = u.id
                    ORDER BY jv.created_at DESC LIMIT 10""")
        vouchers = c.fetchall()
        
        if vouchers:
            for v in vouchers:
                with st.expander(f"📄 {v[0]} - {v[2]} (₹{v[3]:,.2f})"):
                    c.execute("""SELECT account_head, debit_amount, credit_amount 
                               FROM journal_entries WHERE voucher_id = ?""", (v[0],))
                    entries = c.fetchall()
                    
                    if entries:
                        st.markdown(f"**Date:** {v[1]} | **Status:** {v[5]}")
                        entry_data = []
                        for e in entries:
                            entry_data.append({
                                'Account': e[0],
                                'Debit': f"₹{e[1]:,.2f}" if e[1] > 0 else "",
                                'Credit': f"₹{e[2]:,.2f}" if e[2] > 0 else ""
                            })
                        df = pd.DataFrame(entry_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No vouchers created yet")
    
    with tab2:
        st.markdown("### General Ledger")
        
        c = conn.cursor()
        c.execute("SELECT DISTINCT account_head FROM chart_of_accounts ORDER BY account_head")
        accounts = c.fetchall()
        account_list = [acc[0] for acc in accounts]
        
        selected_account = st.selectbox("Select Account Head", account_list)
        
        if selected_account:
            # Get journal entries for this account
            c.execute("""SELECT jv.voucher_date, jv.narration, je.debit_amount, je.credit_amount
                        FROM journal_entries je 
                        JOIN journal_vouchers jv ON je.voucher_id = jv.voucher_id
                        WHERE je.account_head = ? AND jv.status = 'approved'
                        ORDER BY jv.voucher_date""", (selected_account,))
            entries = c.fetchall()
            
            if entries:
                st.markdown(f"### Ledger - {selected_account}")
                
                running_balance = 0
                ledger_data = []
                
                for entry in entries:
                    debit = entry[2]
                    credit = entry[3]
                    running_balance = running_balance + debit - credit
                    
                    ledger_data.append({
                        'Date': entry[0],
                        'Narration': entry[1],
                        'Debit': f"₹{debit:,.2f}" if debit > 0 else "",
                        'Credit': f"₹{credit:,.2f}" if credit > 0 else "",
                        'Balance': f"₹{running_balance:,.2f}"
                    })
                
                df = pd.DataFrame(ledger_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Determine if it's an asset, liability, income, or expense
                c.execute("SELECT account_type, category FROM chart_of_accounts WHERE account_head = ?",
                         (selected_account,))
                acc_info = c.fetchone()
                
                if acc_info:
                    st.markdown(f"**Account Type:** {acc_info[0].upper()} | **Category:** {acc_info[1].replace('_', ' ').title()}")
                    st.markdown(f"**Closing Balance:** ₹{running_balance:,.2f}")
            else:
                st.info(f"No entries found for {selected_account}")
    
    with tab3:
        st.markdown("### Chart of Accounts")
        
        # Add new account head
        with st.expander("➕ Add New Account Head"):
            with st.form("add_account_head"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    new_head = st.text_input("Account Head Name")
                with col2:
                    acc_type = st.selectbox("Type", ["asset", "liability", "income", "expense"])
                with col3:
                    category = st.selectbox("Category", [
                        "current_asset", "non_current_asset", 
                        "current_liability", "non_current_liability",
                        "operating_income", "non_operating_income",
                        "operating_expense", "non_operating_expense"
                    ])
                
                submit = st.form_submit_button("Add Account")
                
                if submit and new_head:
                    try:
                        c.execute("INSERT INTO chart_of_accounts (account_head, account_type, category) VALUES (?, ?, ?)",
                                (new_head.upper().replace(' ', '_'), acc_type, category))
                        conn.commit()
                        st.success(f"Account head '{new_head}' added successfully!")
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        # Display chart of accounts
        c.execute("""SELECT account_type, category, account_head 
                    FROM chart_of_accounts ORDER BY account_type, category, account_head""")
        accounts = c.fetchall()
        
        if accounts:
            current_type = ""
            for acc in accounts:
                if acc[0] != current_type:
                    current_type = acc[0]
                    st.markdown(f"### {current_type.upper()}S")
                
                st.markdown(f"- **{acc[2]}** ({acc[1].replace('_', ' ').title()})")
        else:
            st.info("No accounts in chart")
    
    conn.close()

# Part 5: Trial Balance, P&L, Balance Sheet
def financial_statements():
    st.markdown('<h2 class="sub-header">Financial Statements</h2>', unsafe_allow_html=True)
    
    conn = init_database()
    
    tab1, tab2, tab3 = st.tabs(["Trial Balance", "Profit & Loss", "Balance Sheet"])
    
    with tab1:
        st.markdown("### Trial Balance")
        
        as_of_date = st.date_input("As of Date", datetime.now().date())
        
        c = conn.cursor()
        
        # Get all journal entries up to the date
        c.execute("""SELECT je.account_head, SUM(je.debit_amount) as total_debit, 
                    SUM(je.credit_amount) as total_credit
                    FROM journal_entries je 
                    JOIN journal_vouchers jv ON je.voucher_id = jv.voucher_id
                    WHERE jv.voucher_date <= ? AND jv.status = 'approved'
                    GROUP BY je.account_head
                    ORDER BY je.account_head""", (as_of_date,))
        entries = c.fetchall()
        
        if entries:
            trial_balance_data = []
            total_debit = 0
            total_credit = 0
            
            for entry in entries:
                debit = entry[1]
                credit = entry[2]
                balance = debit - credit
                
                if balance > 0:
                    debit_balance = balance
                    credit_balance = 0
                    total_debit += balance
                else:
                    debit_balance = 0
                    credit_balance = abs(balance)
                    total_credit += abs(balance)
                
                trial_balance_data.append({
                    'Account Head': entry[0],
                    'Debit (₹)': f"₹{debit_balance:,.2f}",
                    'Credit (₹)': f"₹{credit_balance:,.2f}"
                })
            
            # Add totals
            trial_balance_data.append({
                'Account Head': '**TOTAL**',
                'Debit (₹)': f"**₹{total_debit:,.2f}**",
                'Credit (₹)': f"**₹{total_credit:,.2f}**"
            })
            
            df = pd.DataFrame(trial_balance_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            if abs(total_debit - total_credit) < 0.01:
                st.success("✅ Trial Balance is balanced!")
            else:
                st.error(f"❌ Trial Balance difference: ₹{abs(total_debit - total_credit):,.2f}")
        else:
            st.info("No transactions found for the selected period")
    
    with tab2:
        st.markdown("### Profit & Loss Statement")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("From Date", datetime.now().replace(day=1))
        with col2:
            end_date = st.date_input("To Date", datetime.now().date())
        
        c = conn.cursor()
        
        # Income
        c.execute("""SELECT je.account_head, SUM(je.credit_amount) - SUM(je.debit_amount) as balance
                    FROM journal_entries je 
                    JOIN journal_vouchers jv ON je.voucher_id = jv.voucher_id
                    JOIN chart_of_accounts coa ON je.account_head = coa.account_head
                    WHERE coa.account_type = 'income' 
                    AND jv.voucher_date BETWEEN ? AND ?
                    AND jv.status = 'approved'
                    GROUP BY je.account_head""", (start_date, end_date))
        income_entries = c.fetchall()
        
        # Expenses
        c.execute("""SELECT je.account_head, SUM(je.debit_amount) - SUM(je.credit_amount) as balance
                    FROM journal_entries je 
                    JOIN journal_vouchers jv ON je.voucher_id = jv.voucher_id
                    JOIN chart_of_accounts coa ON je.account_head = coa.account_head
                    WHERE coa.account_type = 'expense' 
                    AND jv.voucher_date BETWEEN ? AND ?
                    AND jv.status = 'approved'
                    GROUP BY je.account_head""", (start_date, end_date))
        expense_entries = c.fetchall()
        
        st.markdown("#### Income")
        total_income = 0
        income_data = []
        for entry in income_entries:
            amount = entry[1]
            if amount > 0:
                total_income += amount
                income_data.append({'Account': entry[0], 'Amount': f"₹{amount:,.2f}"})
        
        if income_data:
            df_income = pd.DataFrame(income_data)
            st.dataframe(df_income, use_container_width=True, hide_index=True)
        else:
            st.info("No income recorded")
        
        st.markdown(f"**Total Income: ₹{total_income:,.2f}**")
        
        st.markdown("---")
        st.markdown("#### Expenses")
        total_expenses = 0
        expense_data = []
        for entry in expense_entries:
            amount = entry[1]
            if amount > 0:
                total_expenses += amount
                expense_data.append({'Account': entry[0], 'Amount': f"₹{amount:,.2f}"})
        
        if expense_data:
            df_expense = pd.DataFrame(expense_data)
            st.dataframe(df_expense, use_container_width=True, hide_index=True)
        else:
            st.info("No expenses recorded")
        
        st.markdown(f"**Total Expenses: ₹{total_expenses:,.2f}**")
        
        st.markdown("---")
        net_profit = total_income - total_expenses
        st.markdown(f"### {'Net Profit' if net_profit >= 0 else 'Net Loss'}: ₹{abs(net_profit):,.2f}")
        
        if net_profit >= 0:
            st.success(f"💰 Net Profit: ₹{net_profit:,.2f}")
        else:
            st.error(f"📉 Net Loss: ₹{abs(net_profit):,.2f}")
    
    with tab3:
        st.markdown("### Balance Sheet")
        
        balance_date = st.date_input("As at Date", datetime.now().date(), key="balance_sheet_date")
        
        c = conn.cursor()
        
        # Assets
        c.execute("""SELECT je.account_head, SUM(je.debit_amount) - SUM(je.credit_amount) as balance
                    FROM journal_entries je 
                    JOIN journal_vouchers jv ON je.voucher_id = jv.voucher_id
                    JOIN chart_of_accounts coa ON je.account_head = coa.account_head
                    WHERE coa.account_type = 'asset' 
                    AND jv.voucher_date <= ?
                    AND jv.status = 'approved'
                    GROUP BY je.account_head""", (balance_date,))
        assets = c.fetchall()
        
        # Liabilities
        c.execute("""SELECT je.account_head, SUM(je.credit_amount) - SUM(je.debit_amount) as balance
                    FROM journal_entries je 
                    JOIN journal_vouchers jv ON je.voucher_id = jv.voucher_id
                    JOIN chart_of_accounts coa ON je.account_head = coa.account_head
                    WHERE coa.account_type = 'liability' 
                    AND jv.voucher_date <= ?
                    AND jv.status = 'approved'
                    GROUP BY je.account_head""", (balance_date,))
        liabilities = c.fetchall()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### ASSETS")
            total_assets = 0
            for asset in assets:
                amount = asset[1]
                if amount > 0:
                    total_assets += amount
                    st.markdown(f"- **{asset[0]}:** ₹{amount:,.2f}")
            st.markdown(f"**Total Assets: ₹{total_assets:,.2f}**")
        
        with col2:
            st.markdown("### LIABILITIES & EQUITY")
            total_liabilities = 0
            for liability in liabilities:
                amount = liability[1]
                if amount > 0:
                    total_liabilities += amount
                    st.markdown(f"- **{liability[0]}:** ₹{amount:,.2f}")
            
            # Calculate equity (Assets - Liabilities)
            equity = total_assets - total_liabilities
            st.markdown(f"- **Owner's Equity:** ₹{equity:,.2f}")
            total_liabilities += equity
            st.markdown(f"**Total Liabilities & Equity: ₹{total_liabilities:,.2f}**")
        
        if abs(total_assets - total_liabilities) < 0.01:
            st.success("✅ Balance Sheet is balanced!")
        else:
            st.error(f"❌ Balance Sheet difference: ₹{abs(total_assets - total_liabilities):,.2f}")
    
    conn.close()

# Part 6: Reports, Audit Logs, Dashboard
def reports_dashboard():
    st.markdown('<h2 class="sub-header">Reports, Audit Logs & Dashboard</h2>', unsafe_allow_html=True)
    
    conn = init_database()
    
    tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "Reports", "Audit Logs", "System Info"])
    
    with tab1:
        st.markdown("### 📊 Banking Dashboard")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        c = conn.cursor()
        
        # Total customers
        c.execute("SELECT COUNT(*) FROM customers")
        total_customers = c.fetchone()[0]
        
        # Total accounts
        c.execute("SELECT COUNT(*) FROM accounts WHERE status = 'active'")
        total_accounts = c.fetchone()[0]
        
        # Total deposits
        c.execute("SELECT SUM(balance) FROM accounts WHERE status = 'active'")
        total_deposits = c.fetchone()[0] or 0
        
        # Total loans outstanding
        c.execute("SELECT SUM(outstanding_amount) FROM loans WHERE status = 'active'")
        total_loans = c.fetchone()[0] or 0
        
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
            st.markdown("#### Account Types Distribution")
            c.execute("""SELECT account_type, COUNT(*) as count 
                        FROM accounts WHERE status = 'active' 
                        GROUP BY account_type""")
            account_types = c.fetchall()
            
            if account_types:
                fig = px.pie(values=[x[1] for x in account_types], 
                           names=[x[0] for x in account_types],
                           title="Account Distribution")
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### Monthly Transactions")
            c.execute("""SELECT DATE(timestamp) as date, COUNT(*) as count, SUM(amount) as total
                        FROM transactions 
                        WHERE timestamp >= DATE('now', '-30 days')
                        GROUP BY DATE(timestamp)
                        ORDER BY date""")
            monthly_data = c.fetchall()
            
            if monthly_data:
                df = pd.DataFrame(monthly_data, columns=['Date', 'Count', 'Amount'])
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(go.Bar(x=df['Date'], y=df['Count'], name="Transactions"), secondary_y=False)
                fig.add_trace(go.Scatter(x=df['Date'], y=df['Amount'], name="Amount (₹)", mode='lines+markers'), secondary_y=True)
                fig.update_layout(title="Daily Transactions (Last 30 Days)")
                st.plotly_chart(fig, use_container_width=True)
        
        # Recent activity
        st.markdown("#### Recent Transactions")
        c.execute("""SELECT t.transaction_id, t.account_number, t.transaction_type, t.amount, 
                    t.balance_after, t.description, t.timestamp
                    FROM transactions t ORDER BY t.timestamp DESC LIMIT 10""")
        recent_txns = c.fetchall()
        
        if recent_txns:
            df = pd.DataFrame(recent_txns, columns=['Txn ID', 'Account', 'Type', 'Amount', 'Balance', 'Description', 'Timestamp'])
            df['Amount'] = df['Amount'].apply(lambda x: f"₹{x:,.2f}")
            df['Balance'] = df['Balance'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(df, use_container_width=True, hide_index=True)
    
    with tab2:
        st.markdown("### 📋 Reports")
        
        report_type = st.selectbox("Select Report", [
            "Customer List", "Account Statement", "FD/RD Report", "Loan Report", 
            "Transaction Report", "Daily Collection Report"
        ])
        
        if report_type == "Customer List":
            c.execute("""SELECT customer_id, first_name, last_name, email, phone, 
                        kyc_status, created_at FROM customers ORDER BY created_at DESC""")
            customers = c.fetchall()
            if customers:
                df = pd.DataFrame(customers, columns=['ID', 'First Name', 'Last Name', 'Email', 'Phone', 'KYC', 'Created'])
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                csv = df.to_csv(index=False)
                st.download_button("Download CSV", csv, "customer_list.csv", "text/csv")
        
        elif report_type == "Account Statement":
            c.execute("SELECT account_number FROM accounts WHERE status = 'active'")
            accounts = c.fetchall()
            if accounts:
                account_list = [acc[0] for acc in accounts]
                selected_acc = st.selectbox("Select Account", account_list)
                
                if selected_acc:
                    c.execute("""SELECT transaction_id, transaction_type, amount, balance_before, 
                                balance_after, description, timestamp
                                FROM transactions WHERE account_number = ? 
                                ORDER BY timestamp DESC""", (selected_acc,))
                    txns = c.fetchall()
                    if txns:
                        df = pd.DataFrame(txns, columns=['Txn ID', 'Type', 'Amount', 'Balance Before', 'Balance After', 'Description', 'Date'])
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        
                        csv = df.to_csv(index=False)
                        st.download_button("Download Statement", csv, f"statement_{selected_acc}.csv", "text/csv")
        
        elif report_type == "FD/RD Report":
            st.markdown("#### Fixed Deposits")
            c.execute("""SELECT * FROM fixed_deposits WHERE status = 'active' ORDER BY start_date DESC""")
            fds = c.fetchall()
            if fds:
                df = pd.DataFrame(fds, columns=['FD ID', 'Customer', 'Account', 'Principal', 'Rate', 'Tenure', 'Start', 'Maturity', 'Maturity Amt', 'Status'])
                st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.markdown("#### Recurring Deposits")
            c.execute("""SELECT * FROM recurring_deposits WHERE status = 'active' ORDER BY start_date DESC""")
            rds = c.fetchall()
            if rds:
                df = pd.DataFrame(rds, columns=['RD ID', 'Customer', 'Account', 'Monthly', 'Rate', 'Tenure', 'Start', 'Maturity', 'Maturity Amt', 'Paid', 'Status'])
                st.dataframe(df, use_container_width=True, hide_index=True)
        
        elif report_type == "Loan Report":
            c.execute("""SELECT * FROM loans WHERE status = 'active' ORDER BY start_date DESC""")
            loans = c.fetchall()
            if loans:
                df = pd.DataFrame(loans, columns=['Loan ID', 'Customer', 'Account', 'Type', 'Principal', 'Rate', 'Tenure', 'EMI', 'Start', 'End', 'Outstanding', 'Status'])
                st.dataframe(df, use_container_width=True, hide_index=True)
        
        elif report_type == "Transaction Report":
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("From", datetime.now()-timedelta(days=7))
            with col2:
                end_date = st.date_input("To", datetime.now().date())
            
            c.execute("""SELECT * FROM transactions WHERE DATE(timestamp) BETWEEN ? AND ? 
                        ORDER BY timestamp DESC""", (start_date, end_date))
            txns = c.fetchall()
            if txns:
                df = pd.DataFrame(txns, columns=['Txn ID', 'Account', 'Type', 'Amount', 'Bal Before', 'Bal After', 'Description', 'Timestamp'])
                st.dataframe(df, use_container_width=True, hide_index=True)
    
    with tab3:
        st.markdown("### 🔍 Audit Logs")
        
        col1, col2 = st.columns(2)
        with col1:
            date_filter = st.date_input("Filter by Date", None)
        with col2:
            action_filter = st.selectbox("Filter by Action", ["All", "CREATE", "UPDATE", "DELETE", "LOGIN", "DEPOSIT", "WITHDRAW"])
        
        query = "SELECT al.log_id, u.username, al.action, al.table_affected, al.record_id, al.timestamp FROM audit_logs al LEFT JOIN users u ON al.user_id = u.id WHERE 1=1"
        params = []
        
        if date_filter:
            query += " AND DATE(al.timestamp) = ?"
            params.append(date_filter)
        
        if action_filter != "All":
            query += " AND al.action = ?"
            params.append(action_filter)
        
        query += " ORDER BY al.timestamp DESC LIMIT 100"
        
        c.execute(query, params)
        logs = c.fetchall()
        
        if logs:
            df = pd.DataFrame(logs, columns=['Log ID', 'User', 'Action', 'Table', 'Record ID', 'Timestamp'])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No audit logs found")
    
    with tab4:
        st.markdown("### System Information")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Database Size", "SQLite")
            st.metric("Version", "1.0.0")
        
        with col2:
            c.execute("SELECT COUNT(*) FROM users")
            st.metric("Total Users", c.fetchone()[0])
            
            c.execute("SELECT COUNT(*) FROM audit_logs")
            st.metric("Total Audit Logs", c.fetchone()[0])
        
        with col3:
            st.metric("Last Backup", "Not configured")
            st.metric("System Status", "🟢 Running")
    
    conn.close()

# Main App
def main():
    init_session_state()
    
    # Initialize database
    init_database()
    
    # Sidebar
    with st.sidebar:
        if st.session_state.logged_in:
            st.markdown(f"### Welcome, {st.session_state.username}!")
            st.markdown(f"**Role:** {st.session_state.role}")
            
            st.markdown("---")
            
            # Navigation
            st.markdown("### Navigation")
            
            menu_options = {
                "📋 Customer Registration & KYC": "customer_registration",
                "💰 Account Management": "account_management",
                "📈 Investments & Loans": "investment_loans",
                "📊 Accounting": "accounting_module",
                "💹 Financial Statements": "financial_statements",
                "📑 Reports & Dashboard": "reports_dashboard"
            }
            
            selected_menu = st.radio("Select Module", list(menu_options.keys()))
            
            st.markdown("---")
            
            if st.button("🚪 Logout", use_container_width=True):
                conn = init_database()
                add_audit_log(conn, st.session_state.user_id, 'LOGOUT', 'users', str(st.session_state.user_id))
                conn.close()
                
                st.session_state.logged_in = False
                st.session_state.username = None
                st.session_state.user_id = None
                st.session_state.role = None
                st.rerun()
        else:
            st.markdown("### Banking System")
            st.info("Please login to access the system")
    
    # Main content
    if st.session_state.logged_in:
        if selected_menu == "📋 Customer Registration & KYC":
            customer_registration()
        elif selected_menu == "💰 Account Management":
            account_management()
        elif selected_menu == "📈 Investments & Loans":
            investment_loans()
        elif selected_menu == "📊 Accounting":
            accounting_module()
        elif selected_menu == "💹 Financial Statements":
            financial_statements()
        elif selected_menu == "📑 Reports & Dashboard":
            reports_dashboard()
    else:
        login_page()

if __name__ == "__main__":
    main()

