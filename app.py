import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import hashlib
import os
import time

# ============== DATABASE SETUP ==============
DB_FILE = "banking_system.db"

def init_database():
    """Initialize SQLite database with all required tables"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_date TEXT NOT NULL,
            last_login TEXT
        )
    ''')
    
    # Accounts table (Chart of Accounts)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_code TEXT UNIQUE NOT NULL,
            account_name TEXT NOT NULL,
            account_type TEXT NOT NULL,
            balance REAL DEFAULT 0,
            daily_limit REAL DEFAULT NULL,
            maturity_date TEXT DEFAULT NULL,
            interest_rate REAL DEFAULT NULL,
            created_date TEXT NOT NULL
        )
    ''')
    
    # Customers table with KYC
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            address TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            id_type TEXT NOT NULL,
            id_number TEXT NOT NULL,
            kyc_completed INTEGER DEFAULT 1,
            created_date TEXT NOT NULL,
            created_by TEXT
        )
    ''')
    
    # Customer Accounts (linking customers to accounts)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            account_code TEXT NOT NULL,
            balance REAL DEFAULT 0,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY (account_code) REFERENCES accounts(account_code)
        )
    ''')
    
    # Transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE NOT NULL,
            date TEXT NOT NULL,
            account_code TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            ref_no TEXT,
            balance_after REAL,
            username TEXT,
            FOREIGN KEY (account_code) REFERENCES accounts(account_code)
        )
    ''')
    
    # Journal entries table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            account_code TEXT NOT NULL,
            account_name TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            ref_no TEXT,
            username TEXT,
            FOREIGN KEY (account_code) REFERENCES accounts(account_code)
        )
    ''')
    
    # Customer transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            date TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            account_code TEXT NOT NULL,
            description TEXT,
            username TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY (account_code) REFERENCES accounts(account_code)
        )
    ''')
    
    conn.commit()
    
    # Insert default chart of accounts if not exists
    default_accounts = [
        ('1100', 'SAVINGS', 'ASSET', 0, None, None, None),
        ('1200', 'CURRENT', 'ASSET', 0, None, None, None),
        ('1300', 'FD', 'ASSET', 0, None, None, 7.0),
        ('1400', 'DAILY_COLLECTION', 'ASSET', 0, 50000, None, None),
        ('2100', 'CUSTOMER_DEPOSITS', 'LIABILITY', 0, None, None, None),
        ('2200', 'FD_LIABILITY', 'LIABILITY', 0, None, None, None),
        ('3100', 'CAPITAL', 'EQUITY', 1000000, None, None, None),
        ('3200', 'RETAINED_EARNINGS', 'EQUITY', 0, None, None, None),
        ('4100', 'INTEREST_INCOME', 'INCOME', 0, None, None, None),
        ('4200', 'SERVICE_CHARGE', 'INCOME', 0, None, None, None),
        ('5100', 'GENERAL_EXPENSE', 'EXPENSE', 0, None, None, None),
        ('5200', 'SALARY_EXPENSE', 'EXPENSE', 0, None, None, None),
        ('5300', 'RENT_EXPENSE', 'EXPENSE', 0, None, None, None),
        ('5400', 'UTILITY_EXPENSE', 'EXPENSE', 0, None, None, None),
    ]
    
    for acc in default_accounts:
        cursor.execute('''
            INSERT OR IGNORE INTO accounts 
            (account_code, account_name, account_type, balance, daily_limit, maturity_date, interest_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', acc)
    
    # Insert default admin user if not exists
    admin_password = hash_password("admin123")
    cursor.execute('''
        INSERT OR IGNORE INTO users 
        (username, password_hash, full_name, role, created_date)
        VALUES (?, ?, ?, ?, ?)
    ''', ("admin", admin_password, "System Administrator", "admin", datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    
    # Insert demo users
    demo_password = hash_password("demo123")
    demo_users = [
        ("teller1", demo_password, "Teller One", "user"),
        ("teller2", demo_password, "Teller Two", "user"),
        ("manager", demo_password, "Branch Manager", "manager"),
    ]
    for user in demo_users:
        cursor.execute('''
            INSERT OR IGNORE INTO users 
            (username, password_hash, full_name, role, created_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user[0], user[1], user[2], user[3], datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username, password):
    """Verify user credentials"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ? AND password_hash = ?', 
                   (username, hash_password(password)))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        # Update last login
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_login = ? WHERE username = ?',
                       (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), username))
        conn.commit()
        conn.close()
        return {
            'id': user[0],
            'username': user[1],
            'full_name': user[3],
            'role': user[4],
            'created_date': user[5],
            'last_login': user[6]
        }
    return None

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect(DB_FILE)

# ============== HELPER FUNCTIONS ==============
def generate_transaction_id():
    """Generate unique transaction ID"""
    return f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{str(time.time_ns())[-6:]}"

def get_account_balance(account_code):
    """Get current balance of an account"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM accounts WHERE account_code = ?', (account_code,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def update_account_balance(account_code, amount, is_debit=True):
    """Update account balance with debit/credit logic"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get account type
    cursor.execute('SELECT account_type, balance FROM accounts WHERE account_code = ?', (account_code,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return False, "Account not found"
    
    acc_type, current_balance = result
    
    # Asset/Expense: Debit increases, Credit decreases
    # Liability/Equity/Income: Credit increases, Debit decreases
    if acc_type in ['ASSET', 'EXPENSE']:
        new_balance = current_balance + amount if is_debit else current_balance - amount
    else:
        new_balance = current_balance - amount if is_debit else current_balance + amount
    
    cursor.execute('UPDATE accounts SET balance = ? WHERE account_code = ?', (new_balance, account_code))
    conn.commit()
    conn.close()
    return True, new_balance

def record_transaction(account_code, txn_type, amount, description="", username="", ref_no=""):
    """Record a transaction"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    txn_id = generate_transaction_id()
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    balance_after = get_account_balance(account_code)
    
    cursor.execute('''
        INSERT INTO transactions 
        (transaction_id, date, account_code, transaction_type, amount, description, ref_no, balance_after, username)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (txn_id, date, account_code, txn_type, amount, description, ref_no, balance_after, username))
    
    # Also record in journal entries
    cursor.execute('SELECT account_name FROM accounts WHERE account_code = ?', (account_code,))
    acc_name = cursor.fetchone()[0]
    
    entry_type = 'DEBIT' if txn_type in ['DEPOSIT', 'INCOME'] else 'CREDIT'
    cursor.execute('''
        INSERT INTO journal_entries 
        (date, account_code, account_name, entry_type, amount, description, ref_no, username)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (date, account_code, acc_name, entry_type, amount, description, ref_no, username))
    
    conn.commit()
    conn.close()
    return True, txn_id

def double_entry(debit_account, credit_account, amount, description="", username=""):
    """Perform double-entry bookkeeping"""
    if amount <= 0:
        return False, "Amount must be greater than zero"
    
    # Debit the debit account
    success, msg = update_account_balance(debit_account, amount, is_debit=True)
    if not success:
        return False, msg
    
    # Credit the credit account
    success, msg = update_account_balance(credit_account, amount, is_debit=False)
    if not success:
        # Rollback
        update_account_balance(debit_account, amount, is_debit=False)
        return False, msg
    
    # Record transactions
    ref_no = f"JE{datetime.now().strftime('%Y%m%d%H%M%S')}"
    record_transaction(debit_account, 'DEBIT', amount, f"{description} (Dr)", username, ref_no)
    record_transaction(credit_account, 'CREDIT', amount, f"{description} (Cr)", username, ref_no)
    
    return True, f"Journal entry posted: Dr {debit_account} / Cr {credit_account} for ₹{amount:,.2f}"

def get_all_accounts():
    """Get all accounts from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT account_code, account_name, account_type, balance, daily_limit, maturity_date, interest_rate FROM accounts')
    result = cursor.fetchall()
    conn.close()
    
    accounts = {}
    for row in result:
        accounts[row[0]] = {
            'account_code': row[0],
            'account_name': row[1],
            'account_type': row[2],
            'balance': row[3],
            'daily_limit': row[4],
            'maturity_date': row[5],
            'interest_rate': row[6]
        }
    return accounts

# ============== CUSTOMER FUNCTIONS ==============
def create_customer(full_name, address, phone, email, id_type, id_number, username):
    """Create a new customer with KYC"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Generate customer ID
    cursor.execute('SELECT MAX(CAST(SUBSTR(customer_id, 5) AS INTEGER)) FROM customers')
    max_id = cursor.fetchone()[0]
    new_id = (max_id or 1000) + 1
    customer_id = f"CUST{new_id}"
    
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO customers 
        (customer_id, full_name, address, phone, email, id_type, id_number, kyc_completed, created_date, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (customer_id, full_name, address, phone, email, id_type, id_number, 1, date, username))
    
    # Create customer account mappings with zero balance
    for acc_code in ['1100', '1200', '1300']:  # Savings, Current, FD
        cursor.execute('''
            INSERT INTO customer_accounts (customer_id, account_code, balance)
            VALUES (?, ?, ?)
        ''', (customer_id, acc_code, 0))
    
    conn.commit()
    conn.close()
    return True, f"Customer {full_name} created with ID: {customer_id}"

def get_all_customers():
    """Get all customers"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT customer_id, full_name, address, phone, email, id_type, id_number, created_date
        FROM customers
        ORDER BY created_date DESC
    ''')
    result = cursor.fetchall()
    conn.close()
    
    customers = {}
    for row in result:
        customers[row[0]] = {
            'customer_id': row[0],
            'full_name': row[1],
            'address': row[2],
            'phone': row[3],
            'email': row[4],
            'id_type': row[5],
            'id_number': row[6],
            'created_date': row[7]
        }
    return customers

def get_customer_balances(customer_id):
    """Get customer's account balances"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT account_code, balance 
        FROM customer_accounts 
        WHERE customer_id = ?
    ''', (customer_id,))
    result = cursor.fetchall()
    conn.close()
    
    balances = {}
    for row in result:
        balances[row[0]] = row[1]
    return balances

def record_customer_transaction(customer_id, account_code, amount, txn_type, description="", username=""):
    """Record a customer transaction"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Update customer account balance
    cursor.execute('''
        UPDATE customer_accounts 
        SET balance = balance + ? 
        WHERE customer_id = ? AND account_code = ?
    ''', (amount if txn_type == 'DEPOSIT' else -amount, customer_id, account_code))
    
    # Record transaction
    cursor.execute('''
        INSERT INTO customer_transactions 
        (customer_id, date, transaction_type, amount, account_code, description, username)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (customer_id, date, txn_type, amount, account_code, description, username))
    
    conn.commit()
    conn.close()
    return True

# ============== FINANCIAL REPORTS ==============
def get_balance_sheet():
    """Generate balance sheet"""
    accounts = get_all_accounts()
    
    assets = {}
    liabilities = {}
    equity = {}
    
    for code, data in accounts.items():
        acc_type = data['account_type']
        balance = data['balance']
        
        if acc_type == 'ASSET':
            assets[data['account_name']] = balance
        elif acc_type == 'LIABILITY':
            liabilities[data['account_name']] = balance
        elif acc_type == 'EQUITY':
            equity[data['account_name']] = balance
    
    return {
        'assets': assets,
        'liabilities': liabilities,
        'equity': equity,
        'total_assets': sum(assets.values()),
        'total_liabilities': sum(liabilities.values()),
        'total_equity': sum(equity.values())
    }

def get_profit_loss():
    """Generate Profit & Loss statement"""
    accounts = get_all_accounts()
    
    income = {}
    expenses = {}
    
    for code, data in accounts.items():
        acc_type = data['account_type']
        balance = data['balance']
        
        if acc_type == 'INCOME':
            income[data['account_name']] = balance
        elif acc_type == 'EXPENSE':
            expenses[data['account_name']] = balance
    
    total_income = sum(income.values())
    total_expenses = sum(expenses.values())
    
    return {
        'income': income,
        'expenses': expenses,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_profit': total_income - total_expenses
    }

def get_trial_balance():
    """Generate trial balance"""
    accounts = get_all_accounts()
    
    trial_balance = []
    total_debits = 0
    total_credits = 0
    
    for code, data in accounts.items():
        balance = data['balance']
        acc_type = data['account_type']
        
        if acc_type in ['ASSET', 'EXPENSE']:
            trial_balance.append({
                'Account Code': code,
                'Account Name': data['account_name'],
                'Account Type': acc_type,
                'Debit': balance,
                'Credit': 0
            })
            total_debits += balance
        else:
            trial_balance.append({
                'Account Code': code,
                'Account Name': data['account_name'],
                'Account Type': acc_type,
                'Debit': 0,
                'Credit': balance
            })
            total_credits += balance
    
    return pd.DataFrame(trial_balance), total_debits, total_credits

def get_transactions(account_code=None, limit=100):
    """Get transactions"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if account_code:
        cursor.execute('''
            SELECT date, transaction_type, amount, description, balance_after, username
            FROM transactions 
            WHERE account_code = ?
            ORDER BY date DESC
            LIMIT ?
        ''', (account_code, limit))
    else:
        cursor.execute('''
            SELECT date, account_code, transaction_type, amount, description, balance_after, username
            FROM transactions 
            ORDER BY date DESC
            LIMIT ?
        ''', (limit,))
    
    result = cursor.fetchall()
    conn.close()
    return result

# ============== UI COMPONENTS ==============
def display_account_card(acc_code, icon, color):
    """Display an account card"""
    accounts = get_all_accounts()
    if acc_code not in accounts:
        return
    
    data = accounts[acc_code]
    balance = data['balance']
    acc_name = data['account_name']
    acc_type = data['account_type']
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {color}20, {color}05);
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid {color};
        margin-bottom: 6px;
    ">
        <div style="display: flex; justify-content: space-between;">
            <span style="font-size: 11px; color: #888;">{acc_code} | {acc_type}</span>
            <span style="font-size: 11px; color: #888;">{icon}</span>
        </div>
        <div style="font-size: 13px; font-weight: 500;">{acc_name.replace('_', ' ').title()}</div>
        <div style="font-size: 18px; font-weight: bold;">₹{balance:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

def show_transactions_table(account_code):
    """Display transactions for an account"""
    transactions = get_transactions(account_code)
    if transactions:
        df = pd.DataFrame(transactions, columns=['Date', 'Type', 'Amount', 'Description', 'Balance', 'User'])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions yet.")

def login_page():
    """Display login page"""
    st.title("🏦 Complete Banking System")
    st.subheader("🔐 Login")
    
    # Initialize database on first run
    if not os.path.exists(DB_FILE):
        init_database()
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            user = verify_user(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.success(f"Welcome, {user['full_name']}!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    st.caption("Default Users: admin/admin123, teller1/demo123, teller2/demo123, manager/demo123")

def logout():
    """Logout user"""
    st.session_state.logged_in = False
    st.session_state.user = None
    st.rerun()

# ============== MAIN APP ==============
def main():
    # Initialize database if not exists
    if not os.path.exists(DB_FILE):
        init_database()
    
    # Check login status
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        login_page()
        return
    
    # Main app
    user = st.session_state.user
    
    # Header with user info
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.title("🏦 Complete Banking System")
    with col2:
        st.markdown(f"**👤 {user['full_name']}**")
        st.caption(f"Role: {user['role']}")
    with col3:
        if st.button("🚪 Logout"):
            logout()
    
    st.divider()
    
    # Sidebar - Account Overview
    with st.sidebar:
        st.header("📊 Account Overview")
        
        with st.expander("💰 ASSETS", expanded=True):
            for code in ['1100', '1200', '1300', '1400']:
                display_account_card(code, '💰', '#2E86AB')
        
        with st.expander("🏛️ LIABILITIES", expanded=True):
            for code in ['2100', '2200']:
                display_account_card(code, '🏛️', '#A23B72')
        
        with st.expander("📈 EQUITY", expanded=True):
            for code in ['3100', '3200']:
                display_account_card(code, '📈', '#F18F01')
        
        with st.expander("📊 INCOME", expanded=True):
            for code in ['4100', '4200']:
                display_account_card(code, '📊', '#1B998B')
        
        with st.expander("📉 EXPENSES", expanded=True):
            for code in ['5100', '5200', '5300', '5400']:
                display_account_card(code, '📉', '#D65D5D')
        
        st.divider()
        
        # System stats
        accounts = get_all_accounts()
        total_assets = sum(data['balance'] for code, data in accounts.items() if data['account_type'] == 'ASSET')
        total_liabilities = sum(data['balance'] for code, data in accounts.items() if data['account_type'] == 'LIABILITY')
        total_equity = sum(data['balance'] for code, data in accounts.items() if data['account_type'] == 'EQUITY')
        
        st.metric("Total Assets", f"₹{total_assets:,.2f}")
        st.metric("Total Liabilities", f"₹{total_liabilities:,.2f}")
        st.metric("Total Equity", f"₹{total_equity:,.2f}")
        
        st.caption(f"👥 Users Online: 1")
    
    # Main Tabs
    tabs = ["👥 Customers & KYC", "💰 Customer Operations", "📊 Financial Reports", 
            "📝 Journal Entries", "📋 Trial Balance", "⚙️ Expenses & Income", "👤 User Management"]
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(tabs)
    
    # ---------- TAB 1: CUSTOMERS & KYC ----------
    with tab1:
        st.header("👥 Customer Management with KYC")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("➕ Register New Customer")
            with st.form("customer_form"):
                full_name = st.text_input("Full Name*")
                address = st.text_area("Address*")
                col_a, col_b = st.columns(2)
                with col_a:
                    phone = st.text_input("Phone*")
                    id_type = st.selectbox("ID Type*", ["Aadhaar", "PAN", "Passport", "Driving License", "Voter ID"])
                with col_b:
                    email = st.text_input("Email*")
                    id_number = st.text_input("ID Number*")
                
                submitted = st.form_submit_button("✅ Register Customer")
                if submitted:
                    if all([full_name, address, phone, email, id_type, id_number]):
                        success, msg = create_customer(full_name, address, phone, email, id_type, id_number, user['username'])
                        if success:
                            st.success(msg)
                            st.balloons()
                        else:
                            st.error(msg)
                    else:
                        st.warning("All fields are required")
        
        with col2:
            st.subheader("📋 Customer List")
            customers = get_all_customers()
            if customers:
                cust_data = []
                for cid, cust in customers.items():
                    balances = get_customer_balances(cid)
                    cust_data.append({
                        'ID': cid,
                        'Name': cust['full_name'],
                        'Phone': cust['phone'],
                        'Email': cust['email'],
                        'KYC': '✅',
                        'Savings': f"₹{balances.get('1100', 0):,.2f}",
                        'Current': f"₹{balances.get('1200', 0):,.2f}",
                        'FD': f"₹{balances.get('1300', 0):,.2f}"
                    })
                df = pd.DataFrame(cust_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No customers registered yet.")
        
        # Customer Details View
        if customers:
            st.divider()
            st.subheader("🔍 Customer Details")
            selected = st.selectbox("Select Customer", [f"{c['full_name']} ({cid})" for cid, c in customers.items()])
            if selected:
                cust_id = selected.split('(')[-1].replace(')', '')
                cust = customers[cust_id]
                balances = get_customer_balances(cust_id)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**Name:** {cust['full_name']}")
                    st.markdown(f"**ID:** {cust_id}")
                with col2:
                    st.markdown(f"**Phone:** {cust['phone']}")
                    st.markdown(f"**Email:** {cust['email']}")
                with col3:
                    st.markdown(f"**ID Type:** {cust['id_type']}")
                    st.markdown(f"**ID Number:** {cust['id_number']}")
                
                st.markdown("**Account Balances**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Savings", f"₹{balances.get('1100', 0):,.2f}")
                with col2:
                    st.metric("Current", f"₹{balances.get('1200', 0):,.2f}")
                with col3:
                    st.metric("FD", f"₹{balances.get('1300', 0):,.2f}")
    
    # ---------- TAB 2: CUSTOMER OPERATIONS ----------
    with tab2:
        st.header("💰 Customer Account Operations")
        
        customers = get_all_customers()
        if not customers:
            st.warning("⚠️ Please register customers first using the Customers & KYC tab.")
        else:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("🏦 Deposit")
                selected = st.selectbox("Select Customer", 
                                       [f"{c['full_name']} ({cid})" for cid, c in customers.items()],
                                       key="dep_cust")
                if selected:
                    cust_id = selected.split('(')[-1].replace(')', '')
                    acc_type = st.selectbox("Account Type", ['Savings (1100)', 'Current (1200)'], key="dep_acc")
                    account_code = '1100' if 'Savings' in acc_type else '1200'
                    amount = st.number_input("Amount", min_value=0.0, step=100.0, key="dep_amt")
                    
                    if st.button("💰 Deposit", key="dep_btn"):
                        if amount > 0:
                            # Double entry: Debit Savings/Current, Credit Customer Deposits
                            success, msg = double_entry(account_code, '2100', amount, 
                                                        f"Deposit by {selected.split('(')[0].strip()}", user['username'])
                            if success:
                                record_customer_transaction(cust_id, account_code, amount, 'DEPOSIT', 
                                                          f"Deposit of ₹{amount:,.2f}", user['username'])
                                st.success(msg)
                                st.balloons()
                            else:
                                st.error(msg)
                        else:
                            st.warning("Enter an amount greater than zero")
            
            with col2:
                st.subheader("💸 Withdraw")
                selected2 = st.selectbox("Select Customer", 
                                        [f"{c['full_name']} ({cid})" for cid, c in customers.items()],
                                        key="wd_cust")
                if selected2:
                    cust_id = selected2.split('(')[-1].replace(')', '')
                    acc_type2 = st.selectbox("Account Type", ['Savings (1100)', 'Current (1200)'], key="wd_acc")
                    account_code2 = '1100' if 'Savings' in acc_type2 else '1200'
                    amount2 = st.number_input("Amount", min_value=0.0, step=100.0, key="wd_amt")
                    
                    balances = get_customer_balances(cust_id)
                    if balances.get(account_code2, 0) < amount2:
                        st.warning(f"Insufficient balance. Available: ₹{balances.get(account_code2, 0):,.2f}")
                    
                    if st.button("💸 Withdraw", key="wd_btn"):
                        if amount2 > 0:
                            if balances.get(account_code2, 0) >= amount2:
                                # Double entry: Debit Customer Deposits, Credit Savings/Current
                                success, msg = double_entry('2100', account_code2, amount2,
                                                           f"Withdrawal by {selected2.split('(')[0].strip()}", user['username'])
                                if success:
                                    record_customer_transaction(cust_id, account_code2, amount2, 'WITHDRAWAL',
                                                              f"Withdrawal of ₹{amount2:,.2f}", user['username'])
                                    st.success(msg)
                                else:
                                    st.error(msg)
                            else:
                                st.error("Insufficient balance")
                        else:
                            st.warning("Enter an amount greater than zero")
    
    # ---------- TAB 3: FINANCIAL REPORTS ----------
    with tab3:
        st.header("📊 Financial Reports")
        
        report_type = st.radio("Select Report", ["Balance Sheet", "Profit & Loss Account"], horizontal=True)
        
        if report_type == "Balance Sheet":
            st.subheader("📋 Balance Sheet")
            bs = get_balance_sheet()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### ASSETS")
                for acc, bal in bs['assets'].items():
                    st.metric(acc.replace('_', ' ').title(), f"₹{bal:,.2f}")
                st.markdown(f"### **Total Assets: ₹{bs['total_assets']:,.2f}**")
                
                st.markdown("### LIABILITIES")
                for acc, bal in bs['liabilities'].items():
                    st.metric(acc.replace('_', ' ').title(), f"₹{bal:,.2f}")
                st.markdown(f"### **Total Liabilities: ₹{bs['total_liabilities']:,.2f}**")
            
            with col2:
                st.markdown("### EQUITY")
                for acc, bal in bs['equity'].items():
                    st.metric(acc.replace('_', ' ').title(), f"₹{bal:,.2f}")
                st.markdown(f"### **Total Equity: ₹{bs['total_equity']:,.2f}**")
                
                st.divider()
                st.markdown("### ✅ Balance Sheet Check")
                total = bs['total_liabilities'] + bs['total_equity']
                if abs(bs['total_assets'] - total) < 0.01:
                    st.success(f"✅ Assets = Liabilities + Equity\n₹{bs['total_assets']:,.2f} = ₹{total:,.2f}")
                else:
                    st.error(f"❌ Difference: ₹{bs['total_assets'] - total:,.2f}")
        
        else:
            st.subheader("📊 Profit & Loss Account")
            pl = get_profit_loss()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### INCOME")
                for acc, bal in pl['income'].items():
                    st.metric(acc.replace('_', ' ').title(), f"₹{bal:,.2f}")
                st.markdown(f"### **Total Income: ₹{pl['total_income']:,.2f}**")
            
            with col2:
                st.markdown("### EXPENSES")
                for acc, bal in pl['expenses'].items():
                    st.metric(acc.replace('_', ' ').title(), f"₹{bal:,.2f}")
                st.markdown(f"### **Total Expenses: ₹{pl['total_expenses']:,.2f}**")
            
            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Income", f"₹{pl['total_income']:,.2f}")
            with col2:
                st.metric("Total Expenses", f"₹{pl['total_expenses']:,.2f}")
            with col3:
                if pl['net_profit'] >= 0:
                    st.success(f"NET PROFIT: ₹{pl['net_profit']:,.2f} 🎉")
                else:
                    st.error(f"NET LOSS: ₹{abs(pl['net_profit']):,.2f}")
    
    # ---------- TAB 4: JOURNAL ENTRIES ----------
    with tab4:
        st.header("📝 Journal Entries")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT date, account_code, account_name, entry_type, amount, description, username
            FROM journal_entries
            ORDER BY date DESC
            LIMIT 200
        ''')
        results = cursor.fetchall()
        conn.close()
        
        if results:
            df = pd.DataFrame(results, columns=['Date', 'Account Code', 'Account Name', 'Type', 'Amount', 'Description', 'User'])
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"Total Entries Displayed: {len(results)}")
        else:
            st.info("No journal entries yet.")
    
    # ---------- TAB 5: TRIAL BALANCE ----------
    with tab5:
        st.header("📋 Trial Balance")
        
        tb_df, total_debits, total_credits = get_trial_balance()
        
        if not tb_df.empty:
            st.dataframe(tb_df, use_container_width=True, hide_index=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Debits", f"₹{total_debits:,.2f}")
            with col2:
                st.metric("Total Credits", f"₹{total_credits:,.2f}")
            with col3:
                diff = total_debits - total_credits
                if abs(diff) < 0.01:
                    st.success("✅ Trial Balance is Balanced!")
                else:
                    st.error(f"❌ Difference: ₹{diff:,.2f}")
        else:
            st.info("No accounts to display.")
    
    # ---------- TAB 6: EXPENSES & INCOME ----------
    with tab6:
        st.header("⚙️ Expense & Income Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📉 Record Expense")
            expense_type = st.selectbox("Expense Type", 
                                       ['5100 (General Expense)', '5200 (Salary Expense)', 
                                        '5300 (Rent Expense)', '5400 (Utility Expense)'])
            expense_code = expense_type.split(' ')[0]
            amount = st.number_input("Amount", min_value=0.0, step=100.0, key="exp_amt")
            description = st.text_input("Description", key="exp_desc", placeholder="e.g., Office supplies")
            
            if st.button("💳 Record Expense", key="exp_btn"):
                if amount > 0:
                    success, msg = double_entry(expense_code, '1100', amount, 
                                               f"Expense: {description or expense_type}", user['username'])
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.warning("Enter an amount greater than zero")
        
        with col2:
            st.subheader("📊 Record Income")
            income_type = st.selectbox("Income Type", ['4100 (Interest Income)', '4200 (Service Charge)'])
            income_code = income_type.split(' ')[0]
            amount2 = st.number_input("Amount", min_value=0.0, step=100.0, key="inc_amt")
            description2 = st.text_input("Description", key="inc_desc", placeholder="e.g., Interest on FD")
            
            if st.button("📈 Record Income", key="inc_btn"):
                if amount2 > 0:
                    success, msg = double_entry('1100', income_code, amount2,
                                               f"Income: {description2 or income_type}", user['username'])
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.warning("Enter an amount greater than zero")
    
    # ---------- TAB 7: USER MANAGEMENT ----------
    with tab7:
        st.header("👤 User Management")
        
        # Only admin can manage users
        if user['role'] != 'admin':
            st.warning("⚠️ Only administrators can manage users.")
        else:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("➕ Create New User")
                with st.form("create_user_form"):
                    new_username = st.text_input("Username*")
                    new_password = st.text_input("Password*", type="password")
                    new_full_name = st.text_input("Full Name*")
                    new_role = st.selectbox("Role", ['user', 'manager', 'admin'])
                    
                    if st.form_submit_button("Create User"):
                        if all([new_username, new_password, new_full_name]):
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            try:
                                hashed = hash_password(new_password)
                                date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                cursor.execute('''
                                    INSERT INTO users (username, password_hash, full_name, role, created_date)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', (new_username, hashed, new_full_name, new_role, date))
                                conn.commit()
                                st.success(f"User {new_username} created successfully!")
                            except sqlite3.IntegrityError:
                                st.error("Username already exists!")
                            conn.close()
                        else:
                            st.warning("All fields are required")
            
            with col2:
                st.subheader("📋 User List")
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT id, username, full_name, role, created_date, last_login FROM users')
                users = cursor.fetchall()
                conn.close()
                
                if users:
                    user_df = pd.DataFrame(users, columns=['ID', 'Username', 'Full Name', 'Role', 'Created', 'Last Login'])
                    st.dataframe(user_df, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
