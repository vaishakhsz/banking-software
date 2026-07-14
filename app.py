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

# ============== DATABASE SETUP ==============
DB_FILE = "savings_bank.db"
_db_lock = threading.Lock()

def get_db_connection():
    """Get database connection"""
    with _db_lock:
        try:
            conn = sqlite3.connect(DB_FILE, timeout=60.0, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=60000")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            return conn
        except Exception as e:
            print(f"Database connection error: {e}")
            return None

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def init_database():
    """Initialize all tables for Savings Bank Account"""
    try:
        conn = get_db_connection()
        if conn is None:
            print("Failed to get database connection")
            return
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
        
        # SB Account Master table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sb_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_number TEXT UNIQUE NOT NULL,
                customer_id TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                kyc_id TEXT NOT NULL,
                kyc_type TEXT NOT NULL,
                address TEXT,
                phone TEXT,
                email TEXT,
                opening_balance REAL DEFAULT 0,
                current_balance REAL DEFAULT 0,
                interest_rate REAL DEFAULT 3.5,
                account_status TEXT DEFAULT 'ACTIVE',
                opening_date TEXT NOT NULL,
                last_interest_date TEXT,
                created_by TEXT,
                nominee_name TEXT,
                nominee_relation TEXT,
                aadhar_number TEXT,
                pan_number TEXT
            )
        ''')
        
        # SB Account Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sb_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE NOT NULL,
                account_number TEXT NOT NULL,
                transaction_date TEXT NOT NULL,
                particulars TEXT NOT NULL,
                debit REAL DEFAULT 0,
                credit REAL DEFAULT 0,
                balance REAL NOT NULL,
                transaction_type TEXT NOT NULL,
                ref_no TEXT,
                created_by TEXT,
                FOREIGN KEY (account_number) REFERENCES sb_accounts(account_number)
            )
        ''')
        
        # Interest History table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sb_interest_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_number TEXT NOT NULL,
                quarter_start TEXT NOT NULL,
                quarter_end TEXT NOT NULL,
                interest_rate REAL NOT NULL,
                average_balance REAL NOT NULL,
                interest_amount REAL NOT NULL,
                credited_date TEXT NOT NULL,
                FOREIGN KEY (account_number) REFERENCES sb_accounts(account_number)
            )
        ''')
        
        # KYC Documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kyc_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kyc_id TEXT UNIQUE NOT NULL,
                customer_name TEXT NOT NULL,
                aadhar_number TEXT,
                pan_number TEXT,
                aadhar_image TEXT,
                pan_image TEXT,
                address TEXT,
                phone TEXT,
                email TEXT,
                document_type TEXT,
                upload_date TEXT,
                verified INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        
        # Check if default admin user exists - FIXED
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("Creating default users...")
            current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            admin_password = hash_password("admin123")
            
            # Insert admin user
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
            print("Default users created successfully")
        
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error in init_database: {e}")
        print(traceback.format_exc())

def verify_user(username, password):
    """Verify user credentials"""
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        cursor = conn.cursor()
        
        # Hash the password
        hashed = hash_password(password)
        
        cursor.execute('SELECT * FROM users WHERE username = ? AND password_hash = ?', 
                       (username, hashed))
        user = cursor.fetchone()
        
        if user:
            # Update last login
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
                'last_login': user[6] if len(user) > 6 else None
            }
        conn.close()
    except Exception as e:
        print(f"Error in verify_user: {e}")
        return None
    return None

# ============== HELPER FUNCTIONS ==============
def generate_account_number():
    """Generate unique SB account number"""
    try:
        conn = get_db_connection()
        if conn is None:
            return f"SB{datetime.now().strftime('%Y%m')}{str(int(time.time()))[-6:]}"
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sb_accounts")
        count = cursor.fetchone()[0]
        conn.close()
        year = datetime.now().strftime('%Y')
        month = datetime.now().strftime('%m')
        return f"SB{year}{month}{str(count + 1).zfill(6)}"
    except Exception as e:
        print(f"Error generating account number: {e}")
        return f"SB{datetime.now().strftime('%Y%m')}{str(int(time.time()))[-6:]}"

def generate_transaction_id():
    """Generate unique transaction ID"""
    return f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{str(int(time.time()))[-6:]}"

def calculate_interest(principal, rate, days):
    """Calculate simple interest"""
    return (principal * rate * days) / (100 * 365)

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

# ============== SB ACCOUNT FUNCTIONS ==============
def create_sb_account(data, username):
    """Create a new Savings Bank Account"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        
        account_number = generate_account_number()
        opening_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO sb_accounts (
                account_number, customer_id, customer_name, kyc_id, kyc_type,
                address, phone, email, opening_balance, current_balance,
                interest_rate, account_status, opening_date, created_by,
                nominee_name, nominee_relation, aadhar_number, pan_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            account_number,
            data['customer_id'],
            data['customer_name'],
            data['kyc_id'],
            data['kyc_type'],
            data['address'],
            data['phone'],
            data['email'],
            data['opening_balance'],
            data['opening_balance'],
            data['interest_rate'],
            'ACTIVE',
            opening_date,
            username,
            data.get('nominee_name', ''),
            data.get('nominee_relation', ''),
            data.get('aadhar_number', ''),
            data.get('pan_number', '')
        ))
        
        # Create initial transaction for opening balance
        if data['opening_balance'] > 0:
            transaction_id = generate_transaction_id()
            cursor.execute('''
                INSERT INTO sb_transactions (
                    transaction_id, account_number, transaction_date,
                    particulars, credit, balance, transaction_type, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                transaction_id,
                account_number,
                opening_date,
                'Opening Balance',
                data['opening_balance'],
                data['opening_balance'],
                'DEPOSIT',
                username
            ))
        
        conn.commit()
        conn.close()
        return True, f"SB Account {account_number} created successfully for {data['customer_name']}"
    except Exception as e:
        print(f"Error in create_sb_account: {e}")
        return False, f"Error creating account: {str(e)}"

def get_sb_account(account_number):
    """Get SB account details"""
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sb_accounts WHERE account_number = ?', (account_number,))
        result = cursor.fetchone()
        conn.close()
        if result:
            columns = ['id', 'account_number', 'customer_id', 'customer_name', 'kyc_id', 'kyc_type',
                      'address', 'phone', 'email', 'opening_balance', 'current_balance',
                      'interest_rate', 'account_status', 'opening_date', 'last_interest_date',
                      'created_by', 'nominee_name', 'nominee_relation', 'aadhar_number', 'pan_number']
            return dict(zip(columns, result))
        return None
    except Exception as e:
        print(f"Error in get_sb_account: {e}")
        return None

def get_all_sb_accounts():
    """Get all SB accounts"""
    try:
        conn = get_db_connection()
        if conn is None:
            return []
        cursor = conn.cursor()
        cursor.execute('''
            SELECT account_number, customer_id, customer_name, kyc_id, 
                   opening_balance, current_balance, interest_rate, 
                   account_status, opening_date
            FROM sb_accounts 
            ORDER BY opening_date DESC
        ''')
        result = cursor.fetchall()
        conn.close()
        accounts = []
        for row in result:
            accounts.append({
                'account_number': row[0],
                'customer_id': row[1],
                'customer_name': row[2],
                'kyc_id': row[3],
                'opening_balance': row[4],
                'current_balance': row[5],
                'interest_rate': row[6],
                'account_status': row[7],
                'opening_date': row[8]
            })
        return accounts
    except Exception as e:
        print(f"Error in get_all_sb_accounts: {e}")
        return []

def get_sb_transactions(account_number, from_date=None, to_date=None, limit=1000):
    """Get transactions for an SB account"""
    try:
        conn = get_db_connection()
        if conn is None:
            return []
        cursor = conn.cursor()
        
        query = '''
            SELECT transaction_id, transaction_date, particulars, debit, credit, balance, 
                   transaction_type, ref_no, created_by
            FROM sb_transactions 
            WHERE account_number = ?
        '''
        params = [account_number]
        
        if from_date:
            query += ' AND transaction_date >= ?'
            params.append(from_date)
        if to_date:
            query += ' AND transaction_date <= ?'
            params.append(to_date)
        
        query += ' ORDER BY transaction_date DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.close()
        
        transactions = []
        for row in result:
            transactions.append({
                'transaction_id': row[0],
                'transaction_date': row[1],
                'particulars': row[2],
                'debit': row[3],
                'credit': row[4],
                'balance': row[5],
                'transaction_type': row[6],
                'ref_no': row[7],
                'created_by': row[8]
            })
        return transactions
    except Exception as e:
        print(f"Error in get_sb_transactions: {e}")
        return []

def deposit_sb_account(account_number, amount, particulars, username):
    """Deposit money into SB account"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        
        # Get current balance
        cursor.execute('SELECT current_balance FROM sb_accounts WHERE account_number = ?', (account_number,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "Account not found"
        
        current_balance = result[0]
        new_balance = current_balance + amount
        transaction_id = generate_transaction_id()
        transaction_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Update account balance
        cursor.execute('UPDATE sb_accounts SET current_balance = ? WHERE account_number = ?', 
                      (new_balance, account_number))
        
        # Record transaction
        cursor.execute('''
            INSERT INTO sb_transactions (
                transaction_id, account_number, transaction_date,
                particulars, credit, balance, transaction_type, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            transaction_id,
            account_number,
            transaction_date,
            particulars,
            amount,
            new_balance,
            'DEPOSIT',
            username
        ))
        
        conn.commit()
        conn.close()
        return True, f"Deposited ₹{amount:,.2f} successfully. New balance: ₹{new_balance:,.2f}"
    except Exception as e:
        print(f"Error in deposit_sb_account: {e}")
        return False, f"Error depositing: {str(e)}"

def withdraw_sb_account(account_number, amount, particulars, username):
    """Withdraw money from SB account"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        
        # Get current balance
        cursor.execute('SELECT current_balance FROM sb_accounts WHERE account_number = ?', (account_number,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "Account not found"
        
        current_balance = result[0]
        if current_balance < amount:
            conn.close()
            return False, f"Insufficient balance. Available: ₹{current_balance:,.2f}"
        
        new_balance = current_balance - amount
        transaction_id = generate_transaction_id()
        transaction_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Update account balance
        cursor.execute('UPDATE sb_accounts SET current_balance = ? WHERE account_number = ?', 
                      (new_balance, account_number))
        
        # Record transaction
        cursor.execute('''
            INSERT INTO sb_transactions (
                transaction_id, account_number, transaction_date,
                particulars, debit, balance, transaction_type, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            transaction_id,
            account_number,
            transaction_date,
            particulars,
            amount,
            new_balance,
            'WITHDRAWAL',
            username
        ))
        
        conn.commit()
        conn.close()
        return True, f"Withdrawn ₹{amount:,.2f} successfully. New balance: ₹{new_balance:,.2f}"
    except Exception as e:
        print(f"Error in withdraw_sb_account: {e}")
        return False, f"Error withdrawing: {str(e)}"

def calculate_and_credit_interest(account_number):
    """Calculate and credit quarterly interest for SB account"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        
        # Get account details
        cursor.execute('SELECT current_balance, interest_rate FROM sb_accounts WHERE account_number = ?', 
                      (account_number,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "Account not found"
        
        current_balance, interest_rate = result
        
        # Calculate quarterly interest (simplified - 3 months)
        interest = current_balance * (interest_rate / 100) * (90 / 365)
        
        if interest <= 0:
            conn.close()
            return False, "No interest to credit"
        
        # Credit interest to account
        new_balance = current_balance + interest
        cursor.execute('UPDATE sb_accounts SET current_balance = ? WHERE account_number = ?',
                      (new_balance, account_number))
        
        # Record interest transaction
        transaction_id = generate_transaction_id()
        transaction_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO sb_transactions (
                transaction_id, account_number, transaction_date,
                particulars, credit, balance, transaction_type, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            transaction_id,
            account_number,
            transaction_date,
            f'Quarterly Interest @ {interest_rate}%',
            interest,
            new_balance,
            'INTEREST',
            'SYSTEM'
        ))
        
        conn.commit()
        conn.close()
        return True, f"Interest ₹{interest:,.2f} credited at {interest_rate}%"
    except Exception as e:
        print(f"Error in calculate_and_credit_interest: {e}")
        return False, f"Error calculating interest: {str(e)}"

def get_interest_history(account_number):
    """Get interest history for an account"""
    try:
        conn = get_db_connection()
        if conn is None:
            return []
        cursor = conn.cursor()
        cursor.execute('''
            SELECT quarter_start, quarter_end, interest_rate, average_balance, interest_amount, credited_date
            FROM sb_interest_history 
            WHERE account_number = ?
            ORDER BY quarter_start DESC
        ''', (account_number,))
        result = cursor.fetchall()
        conn.close()
        
        history = []
        for row in result:
            history.append({
                'quarter_start': row[0],
                'quarter_end': row[1],
                'interest_rate': row[2],
                'average_balance': row[3],
                'interest_amount': row[4],
                'credited_date': row[5]
            })
        return history
    except Exception as e:
        print(f"Error in get_interest_history: {e}")
        return []

def generate_sb_account_report(account_number, from_date, to_date):
    """Generate detailed report for SB account"""
    try:
        account = get_sb_account(account_number)
        if not account:
            return None
        
        transactions = get_sb_transactions(account_number, from_date, to_date)
        
        # Calculate summary
        total_debits = sum(t['debit'] for t in transactions)
        total_credits = sum(t['credit'] for t in transactions)
        opening_balance = account['opening_balance']
        closing_balance = account['current_balance']
        
        report = {
            'account': account,
            'transactions': transactions,
            'summary': {
                'total_debits': total_debits,
                'total_credits': total_credits,
                'opening_balance': opening_balance,
                'closing_balance': closing_balance,
                'net_change': closing_balance - opening_balance
            }
        }
        return report
    except Exception as e:
        print(f"Error in generate_sb_account_report: {e}")
        return None

# ============== KYC FUNCTIONS ==============
def create_kyc(data, username):
    """Create KYC record"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        
        kyc_id = f"KYC{datetime.now().strftime('%Y%m%d')}{str(int(time.time()))[-6:]}"
        upload_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO kyc_documents (
                kyc_id, customer_name, aadhar_number, pan_number,
                aadhar_image, pan_image, address, phone, email,
                document_type, upload_date, verified
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            kyc_id,
            data['customer_name'],
            data.get('aadhar_number', ''),
            data.get('pan_number', ''),
            data.get('aadhar_image', ''),
            data.get('pan_image', ''),
            data['address'],
            data['phone'],
            data['email'],
            data.get('document_type', 'SB Account'),
            upload_date,
            0
        ))
        
        conn.commit()
        conn.close()
        return True, f"KYC {kyc_id} created successfully"
    except Exception as e:
        print(f"Error in create_kyc: {e}")
        return False, f"Error creating KYC: {str(e)}"

def get_kyc(kyc_id):
    """Get KYC details"""
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM kyc_documents WHERE kyc_id = ?', (kyc_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            columns = ['id', 'kyc_id', 'customer_name', 'aadhar_number', 'pan_number',
                      'aadhar_image', 'pan_image', 'address', 'phone', 'email',
                      'document_type', 'upload_date', 'verified']
            return dict(zip(columns, result))
        return None
    except Exception as e:
        print(f"Error in get_kyc: {e}")
        return None

def get_all_kyc():
    """Get all KYC records"""
    try:
        conn = get_db_connection()
        if conn is None:
            return []
        cursor = conn.cursor()
        cursor.execute('''
            SELECT kyc_id, customer_name, aadhar_number, pan_number, 
                   address, phone, email, upload_date, verified
            FROM kyc_documents
            ORDER BY upload_date DESC
        ''')
        result = cursor.fetchall()
        conn.close()
        kyc_list = []
        for row in result:
            kyc_list.append({
                'kyc_id': row[0],
                'customer_name': row[1],
                'aadhar_number': row[2],
                'pan_number': row[3],
                'address': row[4],
                'phone': row[5],
                'email': row[6],
                'upload_date': row[7],
                'verified': row[8]
            })
        return kyc_list
    except Exception as e:
        print(f"Error in get_all_kyc: {e}")
        return []

# ============== UI FUNCTIONS ==============
def render_kyc_form():
    """Render KYC registration form"""
    st.subheader("📋 KYC Registration")
    
    with st.form("kyc_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            customer_name = st.text_input("Customer Full Name*")
            address = st.text_area("Address*")
            phone = st.text_input("Phone Number*")
            email = st.text_input("Email*")
            
        with col2:
            aadhar_number = st.text_input("Aadhaar Number (12 digits)*")
            if aadhar_number and not re.match(r'^\d{12}$', aadhar_number):
                st.error("❌ Invalid Aadhaar number. Must be 12 digits.")
            
            pan_number = st.text_input("PAN Number (e.g., ABCDE1234F)*")
            if pan_number and not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan_number):
                st.error("❌ Invalid PAN number. Format: ABCDE1234F")
            
            document_type = st.selectbox("Document Type", ["SB Account", "Loan", "FD", "Other"])
        
        aadhar_image = st.file_uploader("Upload Aadhaar Card Image*", type=['jpg', 'jpeg', 'png', 'pdf'], key="kyc_aadhar")
        pan_image = st.file_uploader("Upload PAN Card Image*", type=['jpg', 'jpeg', 'png', 'pdf'], key="kyc_pan")
        
        submitted = st.form_submit_button("✅ Register KYC")
        
        if submitted:
            errors = []
            if not customer_name:
                errors.append("Customer Name is required")
            if not address:
                errors.append("Address is required")
            if not phone:
                errors.append("Phone Number is required")
            if not email:
                errors.append("Email is required")
            if not aadhar_number:
                errors.append("Aadhaar Number is required")
            elif not re.match(r'^\d{12}$', aadhar_number):
                errors.append("Invalid Aadhaar number (must be 12 digits)")
            if not pan_number:
                errors.append("PAN Number is required")
            elif not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan_number):
                errors.append("Invalid PAN number (format: ABCDE1234F)")
            if not aadhar_image:
                errors.append("Aadhaar Card image is required")
            if not pan_image:
                errors.append("PAN Card image is required")
            
            if errors:
                for error in errors:
                    st.error(error)
            else:
                # Convert images to base64
                aadhar_image_b64 = image_to_base64(aadhar_image)
                pan_image_b64 = image_to_base64(pan_image)
                
                kyc_data = {
                    'customer_name': customer_name,
                    'address': address,
                    'phone': phone,
                    'email': email,
                    'aadhar_number': aadhar_number,
                    'pan_number': pan_number,
                    'aadhar_image': aadhar_image_b64,
                    'pan_image': pan_image_b64,
                    'document_type': document_type
                }
                
                success, msg = create_kyc(kyc_data, st.session_state.user['username'])
                if success:
                    st.success(msg)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(msg)

def render_sb_account_creation():
    """Render SB Account creation form"""
    st.subheader("🏦 Create Savings Bank Account")
    
    # Get existing KYC records for selection
    kyc_list = get_all_kyc()
    kyc_options = [""] + [f"{k['customer_name']} ({k['kyc_id']})" for k in kyc_list]
    selected_kyc = st.selectbox("Select Existing KYC*", kyc_options)
    
    if selected_kyc:
        kyc_id = selected_kyc.split('(')[-1].replace(')', '')
        kyc_data = get_kyc(kyc_id)
        
        if kyc_data:
            st.info(f"✅ KYC Verified for: {kyc_data['customer_name']}")
            
            with st.form("sb_account_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    customer_name = st.text_input("Customer Name*", value=kyc_data['customer_name'], disabled=True)
                    customer_id = st.text_input("Customer ID*", value=f"CUST{kyc_id}", disabled=True)
                    kyc_type = st.selectbox("KYC Type*", ["Aadhaar", "PAN", "Passport", "Driving License", "Voter ID"])
                    
                with col2:
                    address = st.text_area("Address*", value=kyc_data['address'])
                    phone = st.text_input("Phone*", value=kyc_data['phone'])
                    email = st.text_input("Email*", value=kyc_data['email'])
                
                st.markdown("### 💰 Account Details")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    opening_balance = st.number_input("Opening Balance*", min_value=0.0, step=100.0, value=0.0)
                
                with col2:
                    interest_rate = st.number_input("Interest Rate (%)*", min_value=0.0, max_value=20.0, step=0.1, value=3.5)
                
                with col3:
                    nominee_name = st.text_input("Nominee Name")
                    nominee_relation = st.text_input("Nominee Relation")
                
                submitted = st.form_submit_button("✅ Create SB Account")
                
                if submitted:
                    if not customer_name or not address or not phone or not email:
                        st.error("Please fill all required fields")
                    else:
                        account_data = {
                            'customer_id': customer_id,
                            'customer_name': customer_name,
                            'kyc_id': kyc_id,
                            'kyc_type': kyc_type,
                            'address': address,
                            'phone': phone,
                            'email': email,
                            'opening_balance': opening_balance,
                            'interest_rate': interest_rate,
                            'nominee_name': nominee_name,
                            'nominee_relation': nominee_relation,
                            'aadhar_number': kyc_data.get('aadhar_number', ''),
                            'pan_number': kyc_data.get('pan_number', '')
                        }
                        
                        success, msg = create_sb_account(account_data, st.session_state.user['username'])
                        if success:
                            st.success(msg)
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(msg)
    else:
        st.info("📋 Please register KYC first before creating SB account.")

def render_sb_account_operations():
    """Render SB Account operations (Deposit, Withdraw, Interest)"""
    st.subheader("💰 Account Operations")
    
    accounts = get_all_sb_accounts()
    if not accounts:
        st.warning("No SB accounts found. Please create an account first.")
        return
    
    account_options = [f"{a['account_number']} - {a['customer_name']} (₹{a['current_balance']:,.2f})" 
                      for a in accounts if a['account_status'] == 'ACTIVE']
    
    if not account_options:
        st.warning("No active SB accounts found.")
        return
    
    selected_account = st.selectbox("Select Account", account_options)
    
    if selected_account:
        account_number = selected_account.split(' - ')[0]
        account = get_sb_account(account_number)
        
        if account:
            st.metric("💰 Current Balance", f"₹{account['current_balance']:,.2f}")
            st.caption(f"📊 Interest Rate: {account['interest_rate']}%")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### 💵 Deposit")
                deposit_amount = st.number_input("Amount", min_value=0.0, step=100.0, key="deposit_amt")
                deposit_particulars = st.text_input("Particulars", key="deposit_particulars", placeholder="e.g., Cash deposit")
                if st.button("💰 Deposit", key="deposit_btn"):
                    if deposit_amount > 0:
                        success, msg = deposit_sb_account(account_number, deposit_amount, deposit_particulars, 
                                                        st.session_state.user['username'])
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("Enter amount greater than zero")
            
            with col2:
                st.markdown("### 💸 Withdraw")
                withdraw_amount = st.number_input("Amount", min_value=0.0, step=100.0, key="withdraw_amt")
                withdraw_particulars = st.text_input("Particulars", key="withdraw_particulars", placeholder="e.g., ATM withdrawal")
                if st.button("💸 Withdraw", key="withdraw_btn"):
                    if withdraw_amount > 0:
                        success, msg = withdraw_sb_account(account_number, withdraw_amount, withdraw_particulars, 
                                                        st.session_state.user['username'])
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("Enter amount greater than zero")
            
            with col3:
                st.markdown("### 📊 Interest")
                st.caption(f"Current Rate: {account['interest_rate']}%")
                if st.button("🧮 Calculate & Credit Interest", key="interest_btn"):
                    success, msg = calculate_and_credit_interest(account_number)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

def render_sb_account_report():
    """Render SB Account report"""
    st.subheader("📊 SB Account Report")
    
    accounts = get_all_sb_accounts()
    if not accounts:
        st.warning("No SB accounts found.")
        return
    
    account_options = [f"{a['account_number']} - {a['customer_name']}" for a in accounts]
    selected_account = st.selectbox("Select Account for Report", account_options)
    
    if selected_account:
        account_number = selected_account.split(' - ')[0]
        
        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input("From Date", value=datetime.now().date() - timedelta(days=30))
        with col2:
            to_date = st.date_input("To Date", value=datetime.now().date())
        
        if st.button("📄 Generate Report", key="report_btn"):
            report = generate_sb_account_report(
                account_number,
                from_date.strftime('%Y-%m-%d'),
                to_date.strftime('%Y-%m-%d')
            )
            
            if report:
                account = report['account']
                transactions = report['transactions']
                summary = report['summary']
                
                st.markdown("### 📋 Account Summary")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Account Number", account['account_number'])
                    st.metric("Customer", account['customer_name'])
                with col2:
                    st.metric("Opening Balance", f"₹{summary['opening_balance']:,.2f}")
                    st.metric("Closing Balance", f"₹{summary['closing_balance']:,.2f}")
                with col3:
                    st.metric("Total Debits", f"₹{summary['total_debits']:,.2f}")
                    st.metric("Total Credits", f"₹{summary['total_credits']:,.2f}")
                
                st.markdown("### 📝 Transaction Details")
                if transactions:
                    txn_data = []
                    for t in transactions:
                        txn_data.append({
                            'Date': t['transaction_date'],
                            'Particulars': t['particulars'],
                            'Debit': f"₹{t['debit']:,.2f}" if t['debit'] > 0 else '-',
                            'Credit': f"₹{t['credit']:,.2f}" if t['credit'] > 0 else '-',
                            'Balance': f"₹{t['balance']:,.2f}",
                            'Type': t['transaction_type']
                        })
                    df = pd.DataFrame(txn_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # Download as CSV
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"SB_Account_{account_number}_{from_date.strftime('%Y%m%d')}_{to_date.strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No transactions for the selected period")
                
                # Interest History
                st.markdown("### 📈 Interest History")
                interest_history = get_interest_history(account_number)
                if interest_history:
                    interest_data = []
                    for ih in interest_history:
                        interest_data.append({
                            'Quarter Start': ih['quarter_start'],
                            'Quarter End': ih['quarter_end'],
                            'Rate': f"{ih['interest_rate']}%",
                            'Avg Balance': f"₹{ih['average_balance']:,.2f}",
                            'Interest': f"₹{ih['interest_amount']:,.2f}",
                            'Credited Date': ih['credited_date']
                        })
                    df_interest = pd.DataFrame(interest_data)
                    st.dataframe(df_interest, use_container_width=True, hide_index=True)
                else:
                    st.info("No interest history available")

def render_sb_account_list():
    """Render SB Account list"""
    st.subheader("📋 SB Account List")
    
    accounts = get_all_sb_accounts()
    if not accounts:
        st.info("No SB accounts created yet.")
        return
    
    account_data = []
    for acc in accounts:
        account_data.append({
            'Account No': acc['account_number'],
            'Customer': acc['customer_name'],
            'KYC ID': acc['kyc_id'],
            'Opening Balance': f"₹{acc['opening_balance']:,.2f}",
            'Current Balance': f"₹{acc['current_balance']:,.2f}",
            'Interest Rate': f"{acc['interest_rate']}%",
            'Status': acc['account_status'],
            'Opening Date': acc['opening_date']
        })
    
    df = pd.DataFrame(account_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

# ============== LOGIN PAGE ==============
def login_page():
    """Display login page"""
    st.title("🏦 Savings Bank Account System")
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

# ============== MAIN APP ==============
def main():
    try:
        if not os.path.exists(DB_FILE):
            print("Database not found. Initializing...")
            init_database()
        else:
            print("Database found. Checking tables...")
            # Ensure tables exist even if database exists
            init_database()
        
        if 'logged_in' not in st.session_state or not st.session_state.logged_in:
            login_page()
            return
        
        user = st.session_state.user
        
        # Header
        col1, col2, col3 = st.columns([2.5, 1.5, 1])
        with col1:
            st.title("🏦 Savings Bank Account System")
        with col2:
            st.markdown(f"**👤 {user['full_name']}**")
            st.caption(f"Role: {user['role']}")
        with col3:
            if st.button("🚪 Logout"):
                logout()
        
        st.divider()
        
        # Main Tabs
        tabs = ["📋 KYC Registration", "🏦 Create SB Account", "💰 Account Operations", 
                "📊 Reports", "📋 Account List"]
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs(tabs)
        
        with tab1:
            render_kyc_form()
        
        with tab2:
            render_sb_account_creation()
        
        with tab3:
            render_sb_account_operations()
        
        with tab4:
            render_sb_account_report()
        
        with tab5:
            render_sb_account_list()
    
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        print(f"Error in main: {e}")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
