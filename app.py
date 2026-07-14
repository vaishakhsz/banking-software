import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import hashlib
import os
import time
import traceback
import base64
from io import BytesIO
from PIL import Image
import re
import threading
import uuid

# ============== DATABASE SETUP WITH SINGLE CONNECTION ==============
DB_FILE = "banking_system.db"
_db_lock = threading.Lock()
_connection = None

def get_db_connection():
    """Get a database connection with proper locking"""
    global _connection
    
    with _db_lock:
        try:
            if _connection is None:
                _connection = sqlite3.connect(DB_FILE, timeout=60.0, check_same_thread=False)
                _connection.execute("PRAGMA journal_mode=WAL")
                _connection.execute("PRAGMA busy_timeout=60000")
                _connection.execute("PRAGMA synchronous=NORMAL")
                _connection.execute("PRAGMA cache_size=10000")
            return _connection
        except sqlite3.OperationalError as e:
            print(f"Database connection error: {e}")
            time.sleep(1)
            _connection = None
            return get_db_connection()

def execute_query(query, params=None, fetch=False, commit=False):
    """Execute a query with retry logic"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch:
                result = cursor.fetchall()
                cursor.close()
                return result
            elif commit:
                conn.commit()
                cursor.close()
                return True
            else:
                cursor.close()
                return True
        except sqlite3.OperationalError as e:
            error_msg = str(e)
            if "database is locked" in error_msg or "DatabaseError" in error_msg:
                wait_time = (attempt + 1) * 1.0
                time.sleep(wait_time)
                global _connection
                _connection = None
                continue
            else:
                print(f"Query error: {e}")
                if fetch:
                    return []
                return False
        except Exception as e:
            print(f"Query error: {e}")
            if fetch:
                return []
            return False
    
    if fetch:
        return []
    return False

def init_database():
    """Initialize SQLite database with all required tables"""
    try:
        conn = get_db_connection()
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
        
        # Savings Accounts table with KYC
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS savings_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_number TEXT UNIQUE NOT NULL,
                kyc_id TEXT UNIQUE NOT NULL,
                customer_name TEXT NOT NULL,
                address TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                id_type TEXT NOT NULL,
                id_number TEXT NOT NULL,
                aadhar_number TEXT,
                pan_number TEXT,
                date_of_birth TEXT,
                nominee_name TEXT,
                nominee_relation TEXT,
                nominee_phone TEXT,
                interest_rate REAL DEFAULT 4.0,
                balance REAL DEFAULT 0,
                opening_date TEXT NOT NULL,
                last_transaction_date TEXT,
                is_active INTEGER DEFAULT 1,
                created_by TEXT,
                FOREIGN KEY (kyc_id) REFERENCES kyc_documents(kyc_id)
            )
        ''')
        
        # KYC Documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kyc_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kyc_id TEXT UNIQUE NOT NULL,
                customer_name TEXT NOT NULL,
                address TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                id_type TEXT NOT NULL,
                id_number TEXT NOT NULL,
                aadhar_number TEXT,
                aadhar_image TEXT,
                pan_number TEXT,
                pan_image TEXT,
                date_of_birth TEXT,
                nominee_name TEXT,
                nominee_relation TEXT,
                nominee_phone TEXT,
                kyc_status TEXT DEFAULT 'PENDING',
                created_date TEXT NOT NULL,
                verified_date TEXT,
                verified_by TEXT
            )
        ''')
        
        # Savings Account Transactions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS savings_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE NOT NULL,
                account_number TEXT NOT NULL,
                transaction_date TEXT NOT NULL,
                particulars TEXT NOT NULL,
                debit REAL DEFAULT 0,
                credit REAL DEFAULT 0,
                balance REAL NOT NULL,
                transaction_type TEXT NOT NULL,
                description TEXT,
                ref_no TEXT,
                username TEXT,
                FOREIGN KEY (account_number) REFERENCES savings_accounts(account_number)
            )
        ''')
        
        # Interest Calculation Log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interest_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_number TEXT NOT NULL,
                calculation_date TEXT NOT NULL,
                quarter TEXT NOT NULL,
                balance REAL NOT NULL,
                interest_rate REAL NOT NULL,
                interest_amount REAL NOT NULL,
                FOREIGN KEY (account_number) REFERENCES savings_accounts(account_number)
            )
        ''')
        
        # Journal entries
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
                voucher_number TEXT
            )
        ''')
        
        conn.commit()
        
        # Check if default admin user exists
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        
        if count == 0:
            current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            admin_password = hash_password("admin123")
            cursor.execute('''
                INSERT INTO users 
                (username, password_hash, full_name, role, created_date)
                VALUES (?, ?, ?, ?, ?)
            ''', ("admin", admin_password, "System Administrator", "admin", current_date))
            
            # Insert demo users
            demo_password = hash_password("demo123")
            demo_users = [
                ("teller1", demo_password, "Teller One", "user"),
                ("teller2", demo_password, "Teller Two", "user"),
                ("manager", demo_password, "Branch Manager", "manager"),
            ]
            for user in demo_users:
                cursor.execute('''
                    INSERT INTO users 
                    (username, password_hash, full_name, role, created_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user[0], user[1], user[2], user[3], current_date))
        
        conn.commit()
    except Exception as e:
        print(f"Error in init_database: {e}")
        raise e

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username, password):
    """Verify user credentials"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password_hash = ?', 
                       (username, hash_password(password)))
        user = cursor.fetchone()
        
        if user:
            # Update last login
            cursor.execute('UPDATE users SET last_login = ? WHERE username = ?',
                           (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), username))
            conn.commit()
            return {
                'id': user[0],
                'username': user[1],
                'full_name': user[3],
                'role': user[4],
                'created_date': user[5],
                'last_login': user[6] if len(user) > 6 else None
            }
    except Exception as e:
        print(f"Error in verify_user: {e}")
        return None
    return None

# ============== HELPER FUNCTIONS ==============
def generate_account_number():
    """Generate a unique savings account number"""
    try:
        # Get the last account number
        result = execute_query('SELECT account_number FROM savings_accounts ORDER BY id DESC LIMIT 1', fetch=True)
        
        if result:
            last_number = result[0][0]
            # Extract the numeric part after SB-
            num_part = int(last_number.split('-')[1])
            new_num = num_part + 1
        else:
            new_num = 1000001
        
        return f"SB-{str(new_num).zfill(7)}"
    except Exception as e:
        print(f"Error generating account number: {e}")
        return f"SB-{str(int(time.time()))[-7:]}"

def generate_kyc_id():
    """Generate a unique KYC ID"""
    try:
        # Get the last KYC ID
        result = execute_query('SELECT kyc_id FROM kyc_documents ORDER BY id DESC LIMIT 1', fetch=True)
        
        if result:
            last_id = result[0][0]
            num_part = int(last_id.split('-')[1])
            new_num = num_part + 1
        else:
            new_num = 10001
        
        return f"KYC-{str(new_num).zfill(6)}"
    except Exception as e:
        print(f"Error generating KYC ID: {e}")
        return f"KYC-{str(int(time.time()))[-6:]}"

def calculate_age_from_date(dob):
    """Calculate age from date string"""
    if not dob:
        return None
    try:
        dob_date = datetime.strptime(dob, '%Y-%m-%d').date()
        today = datetime.now().date()
        age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
        return age
    except Exception as e:
        print(f"Error calculating age: {e}")
        return None

def validate_aadhar(aadhar):
    """Validate Aadhar number (12 digits)"""
    if not aadhar:
        return True
    return bool(re.match(r'^\d{12}$', aadhar))

def validate_pan(pan):
    """Validate PAN number (5 letters, 4 digits, 1 letter)"""
    if not pan:
        return True
    return bool(re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan))

def image_to_base64(image_file):
    """Convert uploaded image to base64 string for storage"""
    if image_file is None:
        return None
    try:
        image = Image.open(image_file)
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode()
    except Exception as e:
        print(f"Error converting image: {e}")
        return None

# ============== SAVINGS ACCOUNT FUNCTIONS ==============
def create_savings_account(data, username):
    """Create a new savings account with KYC"""
    try:
        # Generate account number and KYC ID
        account_number = generate_account_number()
        kyc_id = generate_kyc_id()
        
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        opening_date = datetime.now().strftime('%Y-%m-%d')
        
        # Insert KYC document
        execute_query('''
            INSERT INTO kyc_documents 
            (kyc_id, customer_name, address, phone, email, id_type, id_number,
             aadhar_number, aadhar_image, pan_number, pan_image, date_of_birth,
             nominee_name, nominee_relation, nominee_phone,
             kyc_status, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            kyc_id,
            data['customer_name'],
            data['address'],
            data['phone'],
            data['email'],
            data['id_type'],
            data['id_number'],
            data.get('aadhar_number'),
            data.get('aadhar_image'),
            data.get('pan_number'),
            data.get('pan_image'),
            data['date_of_birth'],
            data.get('nominee_name'),
            data.get('nominee_relation'),
            data.get('nominee_phone'),
            'VERIFIED',
            current_date
        ), commit=True)
        
        # Insert savings account
        execute_query('''
            INSERT INTO savings_accounts 
            (account_number, kyc_id, customer_name, address, phone, email,
             id_type, id_number, aadhar_number, pan_number, date_of_birth,
             nominee_name, nominee_relation, nominee_phone,
             interest_rate, balance, opening_date, last_transaction_date,
             is_active, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            account_number,
            kyc_id,
            data['customer_name'],
            data['address'],
            data['phone'],
            data['email'],
            data['id_type'],
            data['id_number'],
            data.get('aadhar_number'),
            data.get('pan_number'),
            data['date_of_birth'],
            data.get('nominee_name'),
            data.get('nominee_relation'),
            data.get('nominee_phone'),
            data.get('interest_rate', 4.0),
            0.0,
            opening_date,
            opening_date,
            1,
            username
        ), commit=True)
        
        # Record initial journal entry
        execute_query('''
            INSERT INTO journal_entries 
            (date, account_code, account_name, entry_type, amount, description, ref_no, username, voucher_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            opening_date,
            '2100',
            'CUSTOMER_DEPOSITS',
            'CREDIT',
            0,
            f'Account opening for {data["customer_name"]} - {account_number}',
            account_number,
            username,
            f'JV-{account_number}'
        ), commit=True)
        
        return True, f"Account created successfully! Account Number: {account_number}, KYC ID: {kyc_id}"
    except Exception as e:
        print(f"Error creating savings account: {e}")
        return False, f"Error creating account: {str(e)}"

def get_all_savings_accounts():
    """Get all savings accounts"""
    try:
        result = execute_query('''
            SELECT account_number, customer_name, phone, email, balance, 
                   interest_rate, opening_date, is_active, kyc_id
            FROM savings_accounts
            ORDER BY opening_date DESC
        ''', fetch=True)
        
        accounts = []
        for row in result:
            accounts.append({
                'account_number': row[0],
                'customer_name': row[1],
                'phone': row[2],
                'email': row[3],
                'balance': row[4],
                'interest_rate': row[5],
                'opening_date': row[6],
                'is_active': row[7],
                'kyc_id': row[8]
            })
        return accounts
    except Exception as e:
        print(f"Error getting savings accounts: {e}")
        return []

def get_savings_account(account_number):
    """Get savings account details"""
    try:
        result = execute_query('''
            SELECT * FROM savings_accounts 
            WHERE account_number = ?
        ''', (account_number,), fetch=True)
        
        if result:
            columns = ['id', 'account_number', 'kyc_id', 'customer_name', 'address', 'phone', 
                      'email', 'id_type', 'id_number', 'aadhar_number', 'pan_number', 
                      'date_of_birth', 'nominee_name', 'nominee_relation', 'nominee_phone',
                      'interest_rate', 'balance', 'opening_date', 'last_transaction_date', 
                      'is_active', 'created_by']
            return dict(zip(columns, result[0]))
        return None
    except Exception as e:
        print(f"Error getting savings account: {e}")
        return None

def get_savings_account_balance(account_number):
    """Get savings account balance"""
    try:
        result = execute_query('SELECT balance FROM savings_accounts WHERE account_number = ?', 
                              (account_number,), fetch=True)
        if result:
            return result[0][0]
        return 0
    except Exception as e:
        print(f"Error getting balance: {e}")
        return 0

def update_savings_account_balance(account_number, amount, transaction_type):
    """Update savings account balance"""
    try:
        current_balance = get_savings_account_balance(account_number)
        
        if transaction_type == 'DEBIT':
            if current_balance < amount:
                return False, "Insufficient balance"
            new_balance = current_balance - amount
        else:  # CREDIT
            new_balance = current_balance + amount
        
        execute_query('''
            UPDATE savings_accounts 
            SET balance = ?, last_transaction_date = ?
            WHERE account_number = ?
        ''', (new_balance, datetime.now().strftime('%Y-%m-%d'), account_number), commit=True)
        
        return True, new_balance
    except Exception as e:
        print(f"Error updating balance: {e}")
        return False, str(e)

def record_savings_transaction(account_number, particulars, debit, credit, 
                               transaction_type, description='', ref_no='', username=''):
    """Record a savings account transaction"""
    try:
        transaction_id = f"TXN-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Get current balance
        current_balance = get_savings_account_balance(account_number)
        
        # Calculate new balance
        if debit > 0:
            if current_balance < debit:
                return False, "Insufficient balance"
            new_balance = current_balance - debit
        else:
            new_balance = current_balance + credit
        
        # Insert transaction
        execute_query('''
            INSERT INTO savings_transactions 
            (transaction_id, account_number, transaction_date, particulars, 
             debit, credit, balance, transaction_type, description, ref_no, username)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            transaction_id, account_number, current_date, particulars,
            debit, credit, new_balance, transaction_type, description, ref_no, username
        ), commit=True)
        
        # Update account balance
        execute_query('''
            UPDATE savings_accounts 
            SET balance = ?, last_transaction_date = ?
            WHERE account_number = ?
        ''', (new_balance, current_date.split(' ')[0], account_number), commit=True)
        
        return True, transaction_id
    except Exception as e:
        print(f"Error recording transaction: {e}")
        return False, str(e)

def calculate_quarterly_interest(account_number):
    """Calculate and post interest for a savings account"""
    try:
        # Get account details
        account = get_savings_account(account_number)
        if not account:
            return False, "Account not found"
        
        if not account['is_active']:
            return False, "Account is inactive"
        
        # Get current quarter
        today = datetime.now()
        quarter = f"Q{(today.month - 1) // 3 + 1}-{today.year}"
        
        # Check if interest already calculated for this quarter
        result = execute_query('''
            SELECT COUNT(*) FROM interest_calculations 
            WHERE account_number = ? AND quarter = ?
        ''', (account_number, quarter), fetch=True)
        
        if result and result[0][0] > 0:
            return False, f"Interest already calculated for {quarter}"
        
        # Get average balance for the quarter
        # For simplicity, use current balance
        balance = account['balance']
        interest_rate = account['interest_rate']
        
        # Calculate interest (simple interest for quarter)
        # Interest = Balance * Rate * (3/12)
        interest_amount = balance * (interest_rate / 100) * 0.25
        
        if interest_amount <= 0:
            return False, "No interest to credit (balance is zero or negative)"
        
        # Record interest calculation
        execute_query('''
            INSERT INTO interest_calculations 
            (account_number, calculation_date, quarter, balance, interest_rate, interest_amount)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            account_number,
            datetime.now().strftime('%Y-%m-%d'),
            quarter,
            balance,
            interest_rate,
            interest_amount
        ), commit=True)
        
        # Credit interest to account
        success, msg = record_savings_transaction(
            account_number,
            f"Interest credited for {quarter}",
            0,
            interest_amount,
            'INTEREST',
            f"Quarterly interest at {interest_rate}% on balance ₹{balance:,.2f}",
            f"INT-{quarter}",
            'SYSTEM'
        )
        
        if success:
            return True, f"Interest ₹{interest_amount:,.2f} credited for {quarter}"
        else:
            return False, msg
            
    except Exception as e:
        print(f"Error calculating interest: {e}")
        return False, str(e)

def calculate_all_quarterly_interest():
    """Calculate interest for all savings accounts"""
    try:
        accounts = get_all_savings_accounts()
        results = []
        
        for account in accounts:
            if account['is_active'] and account['balance'] > 0:
                success, msg = calculate_quarterly_interest(account['account_number'])
                results.append({
                    'account_number': account['account_number'],
                    'customer_name': account['customer_name'],
                    'success': success,
                    'message': msg
                })
        
        return results
    except Exception as e:
        print(f"Error calculating all interest: {e}")
        return []

def get_account_transactions(account_number, from_date=None, to_date=None):
    """Get transactions for an account within date range"""
    try:
        query = '''
            SELECT transaction_date, particulars, debit, credit, balance, 
                   transaction_type, description, ref_no, username
            FROM savings_transactions
            WHERE account_number = ?
        '''
        params = [account_number]
        
        if from_date and to_date:
            query += ' AND transaction_date BETWEEN ? AND ?'
            params.append(from_date)
            params.append(to_date)
        
        query += ' ORDER BY transaction_date DESC'
        
        result = execute_query(query, tuple(params), fetch=True)
        
        transactions = []
        for row in result:
            transactions.append({
                'date': row[0],
                'particulars': row[1],
                'debit': row[2],
                'credit': row[3],
                'balance': row[4],
                'type': row[5],
                'description': row[6] if row[6] else '',
                'ref_no': row[7] if row[7] else '',
                'username': row[8]
            })
        return transactions
    except Exception as e:
        print(f"Error getting transactions: {e}")
        return []

def generate_account_report(account_number, from_date, to_date):
    """Generate a detailed account report"""
    try:
        account = get_savings_account(account_number)
        if not account:
            return None, "Account not found"
        
        transactions = get_account_transactions(account_number, from_date, to_date)
        
        # Calculate summary
        total_debits = sum(t['debit'] for t in transactions)
        total_credits = sum(t['credit'] for t in transactions)
        opening_balance = get_balance_before_date(account_number, from_date)
        closing_balance = account['balance']
        
        report = {
            'account': account,
            'transactions': transactions,
            'summary': {
                'opening_balance': opening_balance,
                'total_debits': total_debits,
                'total_credits': total_credits,
                'closing_balance': closing_balance,
                'from_date': from_date,
                'to_date': to_date
            }
        }
        
        return report, None
    except Exception as e:
        print(f"Error generating report: {e}")
        return None, str(e)

def get_balance_before_date(account_number, date):
    """Get account balance before a specific date"""
    try:
        result = execute_query('''
            SELECT balance FROM savings_transactions 
            WHERE account_number = ? AND transaction_date < ?
            ORDER BY transaction_date DESC LIMIT 1
        ''', (account_number, date), fetch=True)
        
        if result:
            return result[0][0]
        
        # If no transactions before date, return initial balance
        result = execute_query('SELECT balance FROM savings_accounts WHERE account_number = ?', 
                              (account_number,), fetch=True)
        if result:
            return result[0][0]
        return 0
    except Exception as e:
        print(f"Error getting balance before date: {e}")
        return 0

def update_savings_account(account_number, data, username):
    """Update savings account details"""
    try:
        execute_query('''
            UPDATE savings_accounts 
            SET customer_name = ?, address = ?, phone = ?, email = ?,
                id_type = ?, id_number = ?, aadhar_number = ?, pan_number = ?,
                date_of_birth = ?, nominee_name = ?, nominee_relation = ?,
                nominee_phone = ?, interest_rate = ?
            WHERE account_number = ?
        ''', (
            data['customer_name'],
            data['address'],
            data['phone'],
            data['email'],
            data['id_type'],
            data['id_number'],
            data.get('aadhar_number'),
            data.get('pan_number'),
            data['date_of_birth'],
            data.get('nominee_name'),
            data.get('nominee_relation'),
            data.get('nominee_phone'),
            data.get('interest_rate', 4.0),
            account_number
        ), commit=True)
        
        return True, f"Account updated successfully"
    except Exception as e:
        print(f"Error updating account: {e}")
        return False, str(e)

def close_savings_account(account_number):
    """Close a savings account"""
    try:
        account = get_savings_account(account_number)
        if not account:
            return False, "Account not found"
        
        if account['balance'] > 0:
            return False, "Account has balance. Please withdraw all funds before closing."
        
        execute_query('''
            UPDATE savings_accounts 
            SET is_active = 0
            WHERE account_number = ?
        ''', (account_number,), commit=True)
        
        return True, "Account closed successfully"
    except Exception as e:
        print(f"Error closing account: {e}")
        return False, str(e)

def delete_savings_account(account_number):
    """Delete a savings account (hard delete)"""
    try:
        account = get_savings_account(account_number)
        if not account:
            return False, "Account not found"
        
        # Check if there are transactions
        result = execute_query('SELECT COUNT(*) FROM savings_transactions WHERE account_number = ?', 
                              (account_number,), fetch=True)
        count = result[0][0] if result else 0
        
        if count > 0:
            return False, "Account has transactions. Cannot delete. Please close it instead."
        
        # Delete related records
        execute_query('DELETE FROM interest_calculations WHERE account_number = ?', 
                     (account_number,), commit=True)
        execute_query('DELETE FROM savings_accounts WHERE account_number = ?', 
                     (account_number,), commit=True)
        
        return True, "Account deleted successfully"
    except Exception as e:
        print(f"Error deleting account: {e}")
        return False, str(e)

# ============== UI FUNCTIONS ==============
def login_page():
    """Display login page"""
    st.title("🏦 Savings Bank System")
    st.subheader("🔐 Login")
    
    if not os.path.exists(DB_FILE):
        try:
            init_database()
        except Exception as e:
            st.error(f"Error initializing database: {str(e)}")
            return
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            try:
                user = verify_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.success(f"Welcome, {user['full_name']}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            except Exception as e:
                st.error(f"Login error: {str(e)}")
    
    st.caption("Default Users: admin/admin123, teller1/demo123, teller2/demo123, manager/demo123")

def logout():
    """Logout user"""
    st.session_state.logged_in = False
    st.session_state.user = None
    st.rerun()

def render_account_opening():
    """Render account opening form"""
    st.subheader("📝 Open New Savings Account")
    
    with st.form("open_account_form"):
        st.markdown("### 👤 Customer Details")
        
        col1, col2 = st.columns(2)
        with col1:
            customer_name = st.text_input("Full Name*")
            phone = st.text_input("Phone Number*")
            email = st.text_input("Email*")
            date_of_birth = st.date_input("Date of Birth*", 
                                         min_value=datetime(1900, 1, 1).date(),
                                         max_value=datetime.now().date())
            
            if date_of_birth:
                age = calculate_age_from_date(date_of_birth.strftime('%Y-%m-%d'))
                st.caption(f"Age: {age} years")
        
        with col2:
            address = st.text_area("Address*")
            id_type = st.selectbox("ID Type*", ["Aadhaar", "PAN", "Passport", "Driving License", "Voter ID"])
            id_number = st.text_input("ID Number*")
        
        st.markdown("### 🪪 KYC Documents")
        
        col3, col4 = st.columns(2)
        with col3:
            aadhar_number = st.text_input("Aadhaar Number (12 digits)")
            if aadhar_number and not validate_aadhar(aadhar_number):
                st.error("❌ Invalid Aadhaar number. Must be 12 digits.")
            
            aadhar_image = st.file_uploader("Upload Aadhaar Card Image", type=['jpg', 'jpeg', 'png', 'pdf'])
        
        with col4:
            pan_number = st.text_input("PAN Number (e.g., ABCDE1234F)")
            if pan_number and not validate_pan(pan_number):
                st.error("❌ Invalid PAN number. Format: ABCDE1234F")
            
            pan_image = st.file_uploader("Upload PAN Card Image", type=['jpg', 'jpeg', 'png', 'pdf'])
        
        st.markdown("### 👤 Nominee Details (Optional)")
        
        col5, col6 = st.columns(2)
        with col5:
            nominee_name = st.text_input("Nominee Name")
            nominee_relation = st.text_input("Relation with Nominee")
        
        with col6:
            nominee_phone = st.text_input("Nominee Phone Number")
        
        st.markdown("### 💰 Account Settings")
        
        interest_rate = st.number_input(
            "Interest Rate (%) per annum",
            min_value=0.0,
            max_value=15.0,
            value=4.0,
            step=0.1,
            help="Interest rate applied quarterly"
        )
        
        col7, col8 = st.columns(2)
        with col7:
            submit = st.form_submit_button("✅ Open Account", type="primary")
        with col8:
            clear = st.form_submit_button("🔄 Clear Form")
        
        if submit:
            # Validate
            errors = []
            if not customer_name:
                errors.append("Customer name is required")
            if not phone:
                errors.append("Phone number is required")
            if not email:
                errors.append("Email is required")
            if not date_of_birth:
                errors.append("Date of birth is required")
            if not address:
                errors.append("Address is required")
            if not id_type:
                errors.append("ID type is required")
            if not id_number:
                errors.append("ID number is required")
            
            if errors:
                for error in errors:
                    st.error(error)
            else:
                data = {
                    'customer_name': customer_name,
                    'address': address,
                    'phone': phone,
                    'email': email,
                    'id_type': id_type,
                    'id_number': id_number,
                    'aadhar_number': aadhar_number if aadhar_number else None,
                    'aadhar_image': image_to_base64(aadhar_image) if aadhar_image else None,
                    'pan_number': pan_number if pan_number else None,
                    'pan_image': image_to_base64(pan_image) if pan_image else None,
                    'date_of_birth': date_of_birth.strftime('%Y-%m-%d'),
                    'nominee_name': nominee_name if nominee_name else None,
                    'nominee_relation': nominee_relation if nominee_relation else None,
                    'nominee_phone': nominee_phone if nominee_phone else None,
                    'interest_rate': interest_rate
                }
                
                success, msg = create_savings_account(data, st.session_state.user['username'])
                
                if success:
                    st.success(msg)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(msg)
        
        if clear:
            st.rerun()

def render_account_transactions():
    """Render transaction entry form"""
    st.subheader("💰 Record Transaction")
    
    accounts = get_all_savings_accounts()
    
    if not accounts:
        st.info("No savings accounts available. Please open an account first.")
        return
    
    account_options = [f"{acc['account_number']} - {acc['customer_name']}" for acc in accounts if acc['is_active']]
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        selected = st.selectbox("Select Account", account_options)
        if selected:
            account_number = selected.split(' - ')[0]
            account = get_savings_account(account_number)
            if account:
                st.metric("Current Balance", f"₹{account['balance']:,.2f}")
                st.caption(f"Interest Rate: {account['interest_rate']}% p.a.")
    
    with col2:
        st.info("""
        📝 **Instructions:**
        - Use Credit for deposits
        - Use Debit for withdrawals
        - Particulars should describe the transaction
        """)
    
    with st.form("transaction_form"):
        st.markdown("### Transaction Details")
        
        col3, col4 = st.columns(2)
        with col3:
            transaction_type = st.selectbox("Transaction Type", ["CREDIT", "DEBIT"])
            amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0, value=0.0)
        
        with col4:
            particulars = st.text_input("Particulars*", placeholder="e.g., Salary, Rent, Withdrawal")
            description = st.text_area("Description (Optional)", placeholder="Additional details")
        
        ref_no = st.text_input("Reference Number (Optional)")
        
        col5, col6 = st.columns(2)
        with col5:
            submit = st.form_submit_button("💾 Record Transaction", type="primary")
        with col6:
            clear = st.form_submit_button("🔄 Clear")
        
        if submit:
            if not selected:
                st.error("Please select an account")
            elif not particulars:
                st.error("Particulars is required")
            elif amount <= 0:
                st.error("Amount must be greater than zero")
            else:
                if transaction_type == "DEBIT":
                    debit = amount
                    credit = 0
                else:
                    debit = 0
                    credit = amount
                
                success, msg = record_savings_transaction(
                    account_number,
                    particulars,
                    debit,
                    credit,
                    transaction_type,
                    description,
                    ref_no,
                    st.session_state.user['username']
                )
                
                if success:
                    st.success(f"Transaction recorded successfully! Transaction ID: {msg}")
                    st.balloons()
                    st.rerun()
                else:
                    st.error(msg)
        
        if clear:
            st.rerun()

def render_interest_calculation():
    """Render interest calculation section"""
    st.subheader("💰 Quarterly Interest Calculation")
    
    accounts = get_all_savings_accounts()
    
    if not accounts:
        st.info("No savings accounts available.")
        return
    
    active_accounts = [acc for acc in accounts if acc['is_active'] and acc['balance'] > 0]
    
    if not active_accounts:
        st.info("No active accounts with balance for interest calculation.")
        return
    
    st.info("ℹ️ Interest is calculated quarterly on the account balance.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Active Accounts", len(active_accounts))
    
    with col2:
        total_balance = sum(acc['balance'] for acc in active_accounts)
        st.metric("Total Balance", f"₹{total_balance:,.2f}")
    
    # Calculate interest for all accounts
    if st.button("🔄 Calculate Interest for All Accounts", type="primary"):
        with st.spinner("Calculating interest..."):
            results = calculate_all_quarterly_interest()
            
            if results:
                success_count = sum(1 for r in results if r['success'])
                st.success(f"Interest calculated for {success_count} accounts")
                
                # Show results table
                results_data = []
                for r in results:
                    results_data.append({
                        'Account': r['account_number'],
                        'Customer': r['customer_name'],
                        'Status': '✅ Success' if r['success'] else '❌ Failed',
                        'Message': r['message']
                    })
                
                df = pd.DataFrame(results_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No interest calculated. All accounts may have zero balance or already received interest.")
    
    # Individual account interest calculation
    st.divider()
    st.subheader("📊 Calculate Interest for Individual Account")
    
    account_options = [f"{acc['account_number']} - {acc['customer_name']} (₹{acc['balance']:,.2f})" 
                      for acc in active_accounts]
    
    selected = st.selectbox("Select Account", account_options)
    
    if selected:
        account_number = selected.split(' - ')[0]
        account = get_savings_account(account_number)
        
        if account:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Balance", f"₹{account['balance']:,.2f}")
            with col2:
                st.metric("Interest Rate", f"{account['interest_rate']}%")
            with col3:
                quarterly_interest = account['balance'] * (account['interest_rate'] / 100) * 0.25
                st.metric("Quarterly Interest", f"₹{quarterly_interest:,.2f}")
            
            if st.button("💵 Calculate Interest for This Account", type="secondary"):
                success, msg = calculate_quarterly_interest(account_number)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

def render_account_reports():
    """Render account reports section"""
    st.subheader("📊 Account Reports")
    
    accounts = get_all_savings_accounts()
    
    if not accounts:
        st.info("No savings accounts available.")
        return
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        account_options = [f"{acc['account_number']} - {acc['customer_name']}" 
                          for acc in accounts if acc['is_active']]
        selected = st.selectbox("Select Account", account_options)
    
    with col2:
        st.info("📝 Select date range for the report")
    
    if selected:
        account_number = selected.split(' - ')[0]
        
        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input("From Date", 
                                     value=datetime.now().date() - timedelta(days=30),
                                     key="report_from")
        with col2:
            to_date = st.date_input("To Date", 
                                   value=datetime.now().date(),
                                   key="report_to")
        
        if from_date > to_date:
            st.error("From date must be before To date")
        else:
            report, error = generate_account_report(
                account_number,
                from_date.strftime('%Y-%m-%d'),
                to_date.strftime('%Y-%m-%d')
            )
            
            if error:
                st.error(f"Error generating report: {error}")
            elif report:
                account = report['account']
                summary = report['summary']
                transactions = report['transactions']
                
                st.divider()
                
                # Account header
                st.markdown(f"""
                ### 📄 Account Statement
                **Account Number:** {account['account_number']}  
                **Customer Name:** {account['customer_name']}  
                **Phone:** {account['phone']}  
                **Email:** {account['email']}  
                **Interest Rate:** {account['interest_rate']}% p.a.
                """)
                
                st.markdown(f"**Period:** {from_date.strftime('%d-%b-%Y')} to {to_date.strftime('%d-%b-%Y')}")
                
                # Summary
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Opening Balance", f"₹{summary['opening_balance']:,.2f}")
                with col2:
                    st.metric("Total Debits", f"₹{summary['total_debits']:,.2f}")
                with col3:
                    st.metric("Total Credits", f"₹{summary['total_credits']:,.2f}")
                with col4:
                    st.metric("Closing Balance", f"₹{summary['closing_balance']:,.2f}")
                
                # Transaction table
                if transactions:
                    st.markdown("#### Transaction Details")
                    
                    tx_data = []
                    for tx in transactions:
                        tx_data.append({
                            'Date': tx['date'][:10],
                            'Time': tx['date'][11:16] if len(tx['date']) > 10 else '',
                            'Particulars': tx['particulars'],
                            'Debit': f"₹{tx['debit']:,.2f}" if tx['debit'] > 0 else '-',
                            'Credit': f"₹{tx['credit']:,.2f}" if tx['credit'] > 0 else '-',
                            'Balance': f"₹{tx['balance']:,.2f}",
                            'Type': tx['type'],
                            'Ref No': tx['ref_no'] if tx['ref_no'] else '-'
                        })
                    
                    df = pd.DataFrame(tx_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # Download options
                    col1, col2 = st.columns(2)
                    with col1:
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download CSV",
                            data=csv,
                            file_name=f"account_statement_{account_number}_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                    
                    with col2:
                        st.caption(f"Total Transactions: {len(transactions)}")
                else:
                    st.info("No transactions found for the selected period")

def render_account_management():
    """Render account management section (edit/delete/close)"""
    st.subheader("⚙️ Account Management")
    
    accounts = get_all_savings_accounts()
    
    if not accounts:
        st.info("No savings accounts available.")
        return
    
    account_options = [f"{acc['account_number']} - {acc['customer_name']} (₹{acc['balance']:,.2f})" 
                      for acc in accounts]
    
    selected = st.selectbox("Select Account to Manage", account_options)
    
    if selected:
        account_number = selected.split(' - ')[0]
        account = get_savings_account(account_number)
        
        if account:
            st.divider()
            
            # Account details display
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Account Number", account['account_number'])
                st.metric("KYC ID", account['kyc_id'])
            with col2:
                st.metric("Customer Name", account['customer_name'])
                st.metric("Balance", f"₹{account['balance']:,.2f}")
            with col3:
                st.metric("Interest Rate", f"{account['interest_rate']}%")
                st.metric("Status", "Active" if account['is_active'] else "Closed")
            
            st.caption(f"Opened: {account['opening_date']}")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("✏️ Edit Account")
                with st.form("edit_account_form"):
                    edit_name = st.text_input("Customer Name", value=account['customer_name'])
                    edit_phone = st.text_input("Phone", value=account['phone'])
                    edit_email = st.text_input("Email", value=account['email'])
                    edit_address = st.text_area("Address", value=account['address'])
                    edit_interest = st.number_input(
                        "Interest Rate (%)",
                        min_value=0.0,
                        max_value=15.0,
                        value=account['interest_rate'],
                        step=0.1
                    )
                    
                    if st.form_submit_button("💾 Update Account"):
                        data = {
                            'customer_name': edit_name,
                            'address': edit_address,
                            'phone': edit_phone,
                            'email': edit_email,
                            'id_type': account['id_type'],
                            'id_number': account['id_number'],
                            'aadhar_number': account.get('aadhar_number'),
                            'pan_number': account.get('pan_number'),
                            'date_of_birth': account['date_of_birth'],
                            'nominee_name': account.get('nominee_name'),
                            'nominee_relation': account.get('nominee_relation'),
                            'nominee_phone': account.get('nominee_phone'),
                            'interest_rate': edit_interest
                        }
                        
                        success, msg = update_savings_account(account_number, data, 
                                                             st.session_state.user['username'])
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
            
            with col2:
                st.subheader("🔒 Close Account")
                
                if account['is_active']:
                    if account['balance'] > 0:
                        st.warning(f"⚠️ Account has balance: ₹{account['balance']:,.2f}. Please withdraw all funds before closing.")
                    else:
                        if st.button("🔒 Close Account", type="primary"):
                            success, msg = close_savings_account(account_number)
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                else:
                    st.info("Account is already closed.")
            
            with col3:
                st.subheader("🗑️ Delete Account")
                st.warning("⚠️ This will permanently delete the account.")
                st.caption("Only accounts with no transactions can be deleted.")
                
                if st.button("🗑️ Delete Account", type="secondary"):
                    success, msg = delete_savings_account(account_number)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

def render_interest_log():
    """Render interest calculation log"""
    st.subheader("📋 Interest Calculation Log")
    
    try:
        result = execute_query('''
            SELECT account_number, calculation_date, quarter, balance, interest_rate, interest_amount
            FROM interest_calculations
            ORDER BY calculation_date DESC
            LIMIT 100
        ''', fetch=True)
        
        if not result:
            st.info("No interest calculations recorded yet.")
            return
        
        data = []
        for row in result:
            # Get customer name for display
            account = get_savings_account(row[0])
            customer_name = account['customer_name'] if account else 'Unknown'
            
            data.append({
                'Account': row[0],
                'Customer': customer_name,
                'Date': row[1],
                'Quarter': row[2],
                'Balance': f"₹{row[3]:,.2f}",
                'Rate': f"{row[4]}%",
                'Interest': f"₹{row[5]:,.2f}"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Summary
        total_interest = sum(row[5] for row in result)
        st.metric("Total Interest Paid", f"₹{total_interest:,.2f}")
        
    except Exception as e:
        st.error(f"Error loading interest log: {str(e)}")

def render_dashboard():
    """Render main dashboard"""
    st.header("📊 Dashboard")
    
    accounts = get_all_savings_accounts()
    
    if not accounts:
        st.info("No savings accounts opened yet.")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    active_accounts = [acc for acc in accounts if acc['is_active']]
    total_balance = sum(acc['balance'] for acc in accounts)
    active_balance = sum(acc['balance'] for acc in active_accounts)
    
    with col1:
        st.metric("Total Accounts", len(accounts))
    with col2:
        st.metric("Active Accounts", len(active_accounts))
    with col3:
        st.metric("Total Balance", f"₹{total_balance:,.2f}")
    with col4:
        st.metric("Active Balance", f"₹{active_balance:,.2f}")
    
    st.divider()
    
    # Show accounts list
    st.subheader("📋 All Accounts")
    
    if accounts:
        account_data = []
        for acc in accounts:
            account_data.append({
                'Account No': acc['account_number'],
                'Customer': acc['customer_name'],
                'Phone': acc['phone'],
                'Balance': f"₹{acc['balance']:,.2f}",
                'Interest Rate': f"{acc['interest_rate']}%",
                'Opened': acc['opening_date'],
                'Status': '🟢 Active' if acc['is_active'] else '🔴 Closed'
            })
        
        df = pd.DataFrame(account_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Quick actions
    st.divider()
    st.subheader("⚡ Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 Open New Account", use_container_width=True):
            st.session_state.active_tab = "Open Account"
            st.rerun()
    
    with col2:
        if st.button("💰 Record Transaction", use_container_width=True):
            st.session_state.active_tab = "Transactions"
            st.rerun()
    
    with col3:
        if st.button("📊 View Reports", use_container_width=True):
            st.session_state.active_tab = "Reports"
            st.rerun()

# ============== MAIN APP ==============
def main():
    try:
        if not os.path.exists(DB_FILE):
            init_database()
        
        if 'logged_in' not in st.session_state or not st.session_state.logged_in:
            login_page()
            return
        
        user = st.session_state.user
        
        # Initialize session state
        if 'active_tab' not in st.session_state:
            st.session_state.active_tab = "Dashboard"
        
        # Header
        col1, col2, col3 = st.columns([2.5, 1.5, 1])
        with col1:
            st.title("🏦 Savings Bank System")
        with col2:
            st.markdown(f"**👤 {user['full_name']}**")
            st.caption(f"Role: {user['role']}")
        with col3:
            if st.button("🚪 Logout"):
                logout()
        
        st.divider()
        
        # Main Navigation
        tabs = ["📊 Dashboard", "📝 Open Account", "💰 Transactions", 
                "📊 Reports", "💵 Interest", "📋 Interest Log", "⚙️ Manage Accounts"]
        
        tab_names = ["Dashboard", "Open Account", "Transactions", 
                    "Reports", "Interest", "Interest Log", "Manage Accounts"]
        
        current_tab = st.session_state.active_tab
        
        # Find the index of the current tab
        tab_index = 0
        for i, name in enumerate(tab_names):
            if name == current_tab:
                tab_index = i
                break
        
        selected_tab = st.radio("Navigation", tabs, index=tab_index, horizontal=True)
        
        # Update session state
        for i, name in enumerate(tab_names):
            if selected_tab == tabs[i]:
                st.session_state.active_tab = name
        
        # Render selected tab
        if st.session_state.active_tab == "Dashboard":
            render_dashboard()
        elif st.session_state.active_tab == "Open Account":
            render_account_opening()
        elif st.session_state.active_tab == "Transactions":
            render_account_transactions()
        elif st.session_state.active_tab == "Reports":
            render_account_reports()
        elif st.session_state.active_tab == "Interest":
            render_interest_calculation()
        elif st.session_state.active_tab == "Interest Log":
            render_interest_log()
        elif st.session_state.active_tab == "Manage Accounts":
            render_account_management()
        
        # Footer
        st.divider()
        st.caption("🏦 Savings Bank System | All rights reserved")
        
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        print(f"Error in main: {e}")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
