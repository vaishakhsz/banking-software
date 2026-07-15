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
    """Initialize database and create all tables"""
    # Delete existing database if it has wrong structure
    if os.path.exists('banking_system.db'):
        try:
            # Test if users table has correct structure
            conn = sqlite3.connect('banking_system.db')
            c = conn.cursor()
            c.execute("SELECT password FROM users LIMIT 1")
            conn.close()
        except:
            # If column doesn't exist, delete and recreate
            os.remove('banking_system.db')
            st.warning("Database recreated with correct structure")
    
    conn = sqlite3.connect('banking_system.db', check_same_thread=False)
    c = conn.cursor()
    
    # Create all tables fresh
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'staff',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS journal_entries (
        entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
        voucher_id TEXT NOT NULL,
        account_head TEXT NOT NULL,
        debit_amount REAL DEFAULT 0.00,
        credit_amount REAL DEFAULT 0.00,
        FOREIGN KEY (voucher_id) REFERENCES journal_vouchers (voucher_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS chart_of_accounts (
        account_head TEXT PRIMARY KEY,
        account_type TEXT NOT NULL,
        category TEXT NOT NULL
    )''')
    
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
    
    # Insert default users if not exists
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        # Create admin user - password: admin123
        admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                 ('admin', admin_password, 'admin'))
        
        # Create staff user - password: staff123
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
def get_db_connection():
    """Get a fresh database connection"""
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
    except Exception as e:
        st.error(f"Audit log error: {e}")

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

# Login Page
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
                    
                    # Debug: Show table structure
                    c.execute("PRAGMA table_info(users)")
                    columns = c.fetchall()
                    
                    # Check if password column exists
                    column_names = [col[1] for col in columns]
                    
                    if 'password' not in column_names:
                        st.error("Database structure is incorrect. Please restart the app.")
                        st.info("Available columns: " + ", ".join(column_names))
                        conn.close()
                        return
                    
                    c.execute("SELECT id, username, role, password FROM users WHERE username = ?", (username,))
                    user = c.fetchone()
                    
                    if user:
                        stored_password = user[3]  # password is 4th column (index 3)
                        if stored_password == hashed_pw:
                            st.session_state.logged_in = True
                            st.session_state.user_id = user[0]
                            st.session_state.username = user[1]
                            st.session_state.role = user[2]
                            
                            add_audit_log(user[0], 'LOGIN', 'users', str(user[0]))
                            
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.error("Invalid password")
                    else:
                        st.error("User not found")
                    
                    conn.close()
                except Exception as e:
                    st.error(f"Login error: {str(e)}")
                    st.info("Try refreshing the page or clearing the app cache")

# Customer Registration
def customer_registration():
    st.markdown('<h2 class="sub-header">Customer Registration & KYC</h2>', unsafe_allow_html=True)
    
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
                add_audit_log(st.session_state.user_id, 'CREATE', 'customers', customer_id,
                            new_values={'first_name': first_name, 'last_name': last_name})
                
                st.success(f"Customer registered successfully! Customer ID: {customer_id}")
                conn.close()
            except Exception as e:
                st.error(f"Error registering customer: {e}")
    
    # Display existing customers
    st.markdown("---")
    st.markdown("### Existing Customers")
    
    try:
        conn = get_db_connection()
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
    except Exception as e:
        st.error(f"Error loading customers: {e}")

# Account Management
def account_management():
    st.markdown('<h2 class="sub-header">Account Management</h2>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Open Account", "Deposit", "Withdraw"])
    
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
                    
                    st.info(f"Minimum Balance Required: ₹{min_balance:,.2f}")
                    
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
                            add_audit_log(st.session_state.user_id, 'CREATE', 'accounts', account_number,
                                        new_values={'customer_id': customer_id, 'account_type': account_type})
                            
                            st.success(f"Account opened successfully! Account Number: {account_number}")
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
            c.execute("SELECT account_number, customer_id, account_type, balance FROM accounts WHERE status = 'active'")
            accounts = c.fetchall()
            conn.close()
            
            if accounts:
                with st.form("deposit_form"):
                    account_options = {f"{acc[0]} - {acc[2]} (Balance: ₹{acc[3]:,.2f})": acc for acc in accounts}
                    selected_account = st.selectbox("Select Account *", list(account_options.keys()))
                    
                    amount = st.number_input("Deposit Amount *", min_value=1.0, step=100.0)
                    description = st.text_input("Description")
                    
                    if st.form_submit_button("Deposit"):
                        acc_data = account_options[selected_account]
                        new_balance = float(acc_data[3]) + amount
                        
                        conn = get_db_connection()
                        c = conn.cursor()
                        
                        trans_id = generate_id("TXN")
                        c.execute("""INSERT INTO transactions 
                                   (transaction_id, account_number, transaction_type, amount, 
                                    balance_before, balance_after, description)
                                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                (trans_id, acc_data[0], 'deposit', amount, acc_data[3], new_balance, description))
                        
                        c.execute("UPDATE accounts SET balance = ? WHERE account_number = ?",
                                (new_balance, acc_data[0]))
                        
                        conn.commit()
                        add_audit_log(st.session_state.user_id, 'DEPOSIT', 'transactions', trans_id)
                        
                        st.success(f"Deposited ₹{amount:,.2f} successfully! New Balance: ₹{new_balance:,.2f}")
                        conn.close()
            else:
                st.info("No active accounts available")
        except Exception as e:
            st.error(f"Error: {e}")
    
    with tab3:
        st.markdown("### Withdraw Money")
        
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT account_number, customer_id, account_type, balance FROM accounts WHERE status = 'active'")
            accounts = c.fetchall()
            conn.close()
            
            if accounts:
                with st.form("withdraw_form"):
                    account_options = {f"{acc[0]} - {acc[2]} (Balance: ₹{acc[3]:,.2f})": acc for acc in accounts}
                    selected_account = st.selectbox("Select Account *", list(account_options.keys()))
                    
                    acc_data = account_options[selected_account]
                    amount = st.number_input("Withdrawal Amount *", min_value=1.0, max_value=float(acc_data[3]), step=100.0)
                    description = st.text_input("Description")
                    
                    if st.form_submit_button("Withdraw"):
                        new_balance = float(acc_data[3]) - amount
                        
                        conn = get_db_connection()
                        c = conn.cursor()
                        
                        trans_id = generate_id("TXN")
                        c.execute("""INSERT INTO transactions 
                                   (transaction_id, account_number, transaction_type, amount, 
                                    balance_before, balance_after, description)
                                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                (trans_id, acc_data[0], 'withdrawal', amount, acc_data[3], new_balance, description))
                        
                        c.execute("UPDATE accounts SET balance = ? WHERE account_number = ?",
                                (new_balance, acc_data[0]))
                        
                        conn.commit()
                        add_audit_log(st.session_state.user_id, 'WITHDRAW', 'transactions', trans_id)
                        
                        st.success(f"Withdrew ₹{amount:,.2f} successfully! New Balance: ₹{new_balance:,.2f}")
                        conn.close()
            else:
                st.info("No active accounts available")
        except Exception as e:
            st.error(f"Error: {e}")
    
    # Account List
    st.markdown("---")
    st.markdown("### Active Accounts")
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
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
    except Exception as e:
        st.error(f"Error loading accounts: {e}")

# Main App
def main():
    # Initialize session state first
    init_session_state()
    
    # Initialize database (this will recreate if structure is wrong)
    try:
        init_database()
    except Exception as e:
        st.error(f"Database initialization error: {e}")
        if st.button("Reset Database"):
            if os.path.exists('banking_system.db'):
                os.remove('banking_system.db')
            st.rerun()
        return
    
    # Sidebar
    with st.sidebar:
        if st.session_state.logged_in:
            st.markdown(f"### Welcome, {st.session_state.username}!")
            st.markdown(f"**Role:** {st.session_state.role}")
            st.markdown("---")
            
            # Navigation
            menu_options = {
                "📋 Customer Registration & KYC": customer_registration,
                "💰 Account Management": account_management,
            }
            
            selected_menu = st.radio("Select Module", list(menu_options.keys()))
            
            st.markdown("---")
            if st.button("🚪 Logout", use_container_width=True):
                if st.session_state.user_id:
                    add_audit_log(st.session_state.user_id, 'LOGOUT', 'users', str(st.session_state.user_id))
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
        selected_menu()
    else:
        login_page()

if __name__ == "__main__":
    main()

