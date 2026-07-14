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
DB_FILE = "banking_system.db"
_db_lock = threading.Lock()

def get_db_connection():
    with _db_lock:
        try:
            conn = sqlite3.connect(DB_FILE, timeout=60.0, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=60000")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            return conn
        except:
            return None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def ensure_accounts_exist():
    """Ensure all required accounts exist in the database"""
    try:
        conn = get_db_connection()
        if conn is None:
            return
        cursor = conn.cursor()
        
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # List of all required accounts
        required_accounts = [
            # ===== ASSETS (1xxx) =====
            ('1000', 'CASH', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
            ('1001', 'PETTY_CASH', 'ASSET', 0, 10000, None, None, current_date, 1, 'system'),
            ('1100', 'BANK_SAVINGS', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
            ('1200', 'BANK_CURRENT', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
            ('1300', 'FD', 'ASSET', 0, None, None, 7.0, current_date, 1, 'system'),
            ('1400', 'DAILY_COLLECTION', 'ASSET', 0, 50000, None, None, current_date, 1, 'system'),
            ('1500', 'SUNDRY_DEBTORS', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
            ('1600', 'LOANS_ADVANCED', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
            
            # ===== LIABILITIES (2xxx) =====
            ('2100', 'CUSTOMER_DEPOSITS', 'LIABILITY', 0, None, None, None, current_date, 1, 'system'),
            ('2200', 'FD_LIABILITY', 'LIABILITY', 0, None, None, None, current_date, 1, 'system'),
            ('2300', 'SUNDRY_CREDITORS', 'LIABILITY', 0, None, None, None, current_date, 1, 'system'),
            ('2400', 'LOANS_TAKEN', 'LIABILITY', 0, None, None, None, current_date, 1, 'system'),
            ('2500', 'SB_INTEREST_PAYABLE', 'LIABILITY', 0, None, None, None, current_date, 1, 'system'),
            
            # ===== EQUITY (3xxx) =====
            ('3100', 'CAPITAL', 'EQUITY', 1000000, None, None, None, current_date, 1, 'system'),
            ('3200', 'RETAINED_EARNINGS', 'EQUITY', 0, None, None, None, current_date, 1, 'system'),
            
            # ===== INCOME (4xxx) =====
            ('4100', 'INTEREST_INCOME', 'INCOME', 0, None, None, None, current_date, 1, 'system'),
            ('4200', 'SERVICE_CHARGE', 'INCOME', 0, None, None, None, current_date, 1, 'system'),
            ('4300', 'COMMISSION_INCOME', 'INCOME', 0, None, None, None, current_date, 1, 'system'),
            ('4400', 'RENT_INCOME', 'INCOME', 0, None, None, None, current_date, 1, 'system'),
            
            # ===== EXPENSES (5xxx) =====
            ('5100', 'GENERAL_EXPENSE', 'EXPENSE', 0, None, None, None, current_date, 1, 'system'),
            ('5200', 'SALARY_EXPENSE', 'EXPENSE', 0, None, None, None, current_date, 1, 'system'),
            ('5300', 'RENT_EXPENSE', 'EXPENSE', 0, None, None, None, current_date, 1, 'system'),
            ('5400', 'UTILITY_EXPENSE', 'EXPENSE', 0, None, None, None, current_date, 1, 'system'),
            ('5500', 'CONVEYANCE_EXPENSE', 'EXPENSE', 0, None, None, None, current_date, 1, 'system'),
            ('5600', 'TRAVEL_EXPENSE', 'EXPENSE', 0, None, None, None, current_date, 1, 'system'),
            ('5700', 'STATIONERY_EXPENSE', 'EXPENSE', 0, None, None, None, current_date, 1, 'system'),
            ('5800', 'TELEPHONE_EXPENSE', 'EXPENSE', 0, None, None, None, current_date, 1, 'system'),
            ('5900', 'ADVERTISING_EXPENSE', 'EXPENSE', 0, None, None, None, current_date, 1, 'system'),
            ('5999', 'SB_INTEREST_EXPENSE', 'EXPENSE', 0, None, None, None, current_date, 1, 'system'),
        ]
        
        for acc in required_accounts:
            # Check if account exists
            cursor.execute('SELECT COUNT(*) FROM accounts WHERE account_code = ?', (acc[0],))
            if cursor.fetchone()[0] == 0:
                # Account doesn't exist, insert it
                cursor.execute('''
                    INSERT INTO accounts (account_code, account_name, account_type, balance, daily_limit, maturity_date, interest_rate, created_date, is_active, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', acc)
                print(f"Created account: {acc[1]} ({acc[0]})")
        
        conn.commit()
        conn.close()
        print("All required accounts ensured")
    except Exception as e:
        print(f"Error in ensure_accounts_exist: {e}")

def migrate_database():
    try:
        conn = get_db_connection()
        if conn is None:
            return
        cursor = conn.cursor()
        
        # Check if interest_payable column exists in sb_interest_history
        cursor.execute("PRAGMA table_info(sb_interest_history)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'interest_payable' not in columns:
            cursor.execute("ALTER TABLE sb_interest_history ADD COLUMN interest_payable REAL DEFAULT 0")
            conn.commit()
        
        if 'voucher_number' not in columns:
            cursor.execute("ALTER TABLE sb_interest_history ADD COLUMN voucher_number TEXT")
            conn.commit()
        
        # Check if sb_accounts table has interest_payable
        cursor.execute("PRAGMA table_info(sb_accounts)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'interest_payable' not in columns:
            cursor.execute("ALTER TABLE sb_accounts ADD COLUMN interest_payable REAL DEFAULT 0")
            conn.commit()
        
        if 'last_interest_credited' not in columns:
            cursor.execute("ALTER TABLE sb_accounts ADD COLUMN last_interest_credited TEXT")
            conn.commit()
        
        conn.close()
    except Exception as e:
        print(f"Error in migrate_database: {e}")

def init_database():
    try:
        conn = get_db_connection()
        if conn is None:
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
        
        # Accounts table
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
                created_date TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_by TEXT
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
                whatsapp_number TEXT,
                email TEXT NOT NULL,
                id_type TEXT NOT NULL,
                id_number TEXT NOT NULL,
                aadhar_number TEXT,
                aadhar_image TEXT,
                pan_number TEXT,
                pan_image TEXT,
                date_of_birth TEXT,
                age INTEGER,
                nominee_name TEXT,
                nominee_address TEXT,
                nominee_relation TEXT,
                nominee_dob TEXT,
                nominee_age INTEGER,
                nominee_aadhar TEXT,
                nominee_aadhar_image TEXT,
                nominee_pan TEXT,
                nominee_pan_image TEXT,
                kyc_completed INTEGER DEFAULT 1,
                created_date TEXT NOT NULL,
                created_by TEXT
            )
        ''')
        
        # Customer Accounts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customer_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                account_code TEXT NOT NULL,
                balance REAL DEFAULT 0
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
        
        # Vouchers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vouchers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voucher_number TEXT UNIQUE NOT NULL,
                voucher_type TEXT NOT NULL,
                voucher_date TEXT NOT NULL,
                description TEXT,
                total_amount REAL DEFAULT 0,
                status TEXT DEFAULT 'DRAFT',
                created_date TEXT NOT NULL,
                created_by TEXT,
                updated_date TEXT,
                updated_by TEXT
            )
        ''')
        
        # Voucher entries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS voucher_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voucher_number TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                account_code TEXT NOT NULL,
                account_name TEXT NOT NULL,
                amount REAL NOT NULL,
                narration TEXT
            )
        ''')
        
        # SB Accounts
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
                interest_payable REAL DEFAULT 0,
                account_status TEXT DEFAULT 'ACTIVE',
                opening_date TEXT NOT NULL,
                last_interest_date TEXT,
                last_interest_credited TEXT,
                created_by TEXT,
                nominee_name TEXT,
                nominee_relation TEXT,
                aadhar_number TEXT,
                pan_number TEXT
            )
        ''')
        
        # SB Transactions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sb_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE NOT NULL,
                account_number TEXT NOT NULL,
                transaction_date TEXT NOT NULL,
                value_date TEXT NOT NULL,
                particulars TEXT NOT NULL,
                debit REAL DEFAULT 0,
                credit REAL DEFAULT 0,
                balance REAL NOT NULL,
                transaction_type TEXT NOT NULL,
                ref_no TEXT,
                created_by TEXT,
                created_date TEXT NOT NULL
            )
        ''')
        
        # SB Interest History
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sb_interest_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_number TEXT NOT NULL,
                quarter_start TEXT NOT NULL,
                quarter_end TEXT NOT NULL,
                interest_rate REAL NOT NULL,
                average_balance REAL NOT NULL,
                interest_amount REAL NOT NULL,
                interest_payable REAL DEFAULT 0,
                credited_date TEXT NOT NULL,
                voucher_number TEXT
            )
        ''')
        
        # KYC Documents
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
        
        # Check if default admin user exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            admin_password = hash_password("admin123")
            cursor.execute('INSERT INTO users (username, password_hash, full_name, role, created_date) VALUES (?, ?, ?, ?, ?)',
                          ("admin", admin_password, "System Administrator", "admin", current_date))
            
            demo_password = hash_password("demo123")
            for user in [("teller1", "Teller One"), ("teller2", "Teller Two"), ("manager", "Branch Manager")]:
                cursor.execute('INSERT INTO users (username, password_hash, full_name, role, created_date) VALUES (?, ?, ?, ?, ?)',
                              (user[0], demo_password, user[1], "user", current_date))
            conn.commit()
        
        conn.close()
        migrate_database()
        
        # Ensure all accounts exist
        ensure_accounts_exist()
    except Exception as e:
        print(f"Error in init_database: {e}")

def verify_user(username, password):
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        cursor = conn.cursor()
        hashed = hash_password(password)
        cursor.execute('SELECT * FROM users WHERE username = ? AND password_hash = ?', (username, hashed))
        user = cursor.fetchone()
        if user:
            cursor.execute('UPDATE users SET last_login = ? WHERE username = ?',
                          (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), username))
            conn.commit()
            conn.close()
            return {'id': user[0], 'username': user[1], 'full_name': user[3], 'role': user[4]}
        conn.close()
    except:
        return None
    return None

def image_to_base64(image_file):
    if image_file is None:
        return None
    try:
        image = Image.open(image_file)
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode()
    except:
        return None

def display_image_from_base64(base64_string):
    if not base64_string:
        return None
    try:
        return f"data:image/jpeg;base64,{base64_string}"
    except:
        return None

def validate_aadhar(aadhar):
    if not aadhar:
        return True
    return bool(re.match(r'^\d{12}$', aadhar))

def validate_pan(pan):
    if not pan:
        return True
    return bool(re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan))

def get_safe_float(value, default=0):
    try:
        if value is None:
            return default
        if isinstance(value, str):
            if value.strip() == '':
                return default
            return float(value)
        return float(value)
    except (ValueError, TypeError):
        return default

# ============== ACCOUNT FUNCTIONS ==============
def get_all_accounts():
    try:
        conn = get_db_connection()
        if conn is None:
            return {}
        cursor = conn.cursor()
        cursor.execute('SELECT account_code, account_name, account_type, balance, daily_limit FROM accounts WHERE is_active = 1 ORDER BY account_code')
        result = cursor.fetchall()
        conn.close()
        accounts = {}
        for row in result:
            accounts[row[0]] = {'account_code': row[0], 'account_name': row[1], 'account_type': row[2], 'balance': row[3], 'daily_limit': row[4]}
        return accounts
    except:
        return {}

def get_account_balance(account_code):
    try:
        conn = get_db_connection()
        if conn is None:
            return 0
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM accounts WHERE account_code = ?', (account_code,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    except:
        return 0

def update_account_balance(account_code, amount, is_debit=True):
    """Update account balance with debit/credit logic"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        
        # Get account type and current balance
        cursor.execute('SELECT account_type, balance FROM accounts WHERE account_code = ? AND is_active = 1', (account_code,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, f"Account {account_code} not found"
        
        acc_type, current_balance = result
        
        # Calculate new balance based on account type and debit/credit
        if acc_type in ['ASSET', 'EXPENSE']:
            # Debit increases, Credit decreases
            if is_debit:
                new_balance = current_balance + amount
            else:
                new_balance = current_balance - amount
        else:  # LIABILITY, EQUITY, INCOME
            # Credit increases, Debit decreases
            if is_debit:
                new_balance = current_balance - amount
            else:
                new_balance = current_balance + amount
        
        cursor.execute('UPDATE accounts SET balance = ? WHERE account_code = ?', (new_balance, account_code))
        conn.commit()
        conn.close()
        return True, new_balance
    except Exception as e:
        print(f"Error in update_account_balance: {e}")
        return False, str(e)

def create_account(account_name, account_type, initial_balance=0, daily_limit=None, username=""):
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM accounts WHERE account_name = ? AND account_type = ? AND is_active = 1', 
                       (account_name, account_type))
        if cursor.fetchone():
            conn.close()
            return False, f"Account '{account_name}' already exists"
        account_code = generate_account_code(account_type)
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if daily_limit is not None and daily_limit <= 0:
            daily_limit = None
        cursor.execute('''
            INSERT INTO accounts (account_code, account_name, account_type, balance, daily_limit, created_date, created_by, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (account_code, account_name.upper(), account_type, initial_balance, daily_limit, date, username, 1))
        conn.commit()
        conn.close()
        return True, f"Account '{account_name}' created with code {account_code}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def generate_account_code(account_type):
    try:
        conn = get_db_connection()
        if conn is None:
            return '5100'
        cursor = conn.cursor()
        prefix_map = {'INCOME': '4', 'EXPENSE': '5', 'ASSET': '1', 'LIABILITY': '2', 'EQUITY': '3'}
        prefix = prefix_map.get(account_type, '9')
        cursor.execute(f"SELECT account_code FROM accounts WHERE account_code LIKE '{prefix}%' AND account_type = ? AND is_active = 1 ORDER BY account_code DESC LIMIT 1", (account_type,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return str(int(result[0]) + 1)
        else:
            if account_type == 'INCOME':
                return '4100'
            elif account_type == 'EXPENSE':
                return '5100'
            elif account_type == 'ASSET':
                return '1500'
            elif account_type == 'LIABILITY':
                return '2300'
            else:
                return '9100'
    except:
        return '5100'

# ============== CUSTOMER FUNCTIONS ==============
def create_customer(data, username):
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        cursor.execute('SELECT MAX(CAST(SUBSTR(customer_id, 5) AS INTEGER)) FROM customers')
        max_id = cursor.fetchone()[0]
        new_id = (max_id or 1000) + 1
        customer_id = f"CUST{new_id}"
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO customers (customer_id, full_name, address, phone, whatsapp_number, email, id_type, id_number,
             aadhar_number, aadhar_image, pan_number, pan_image, date_of_birth, age,
             nominee_name, nominee_address, nominee_relation, nominee_dob, nominee_age,
             nominee_aadhar, nominee_aadhar_image, nominee_pan, nominee_pan_image,
             kyc_completed, created_date, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (customer_id, data['full_name'], data['address'], data['phone'], data['whatsapp_number'],
              data['email'], data['id_type'], data['id_number'], data['aadhar_number'], data['aadhar_image'],
              data['pan_number'], data['pan_image'], data['date_of_birth'], data['age'],
              data['nominee_name'], data['nominee_address'], data['nominee_relation'],
              data['nominee_dob'], data['nominee_age'], data['nominee_aadhar'], data['nominee_aadhar_image'],
              data['nominee_pan'], data['nominee_pan_image'], 1, date, username))
        conn.commit()
        conn.close()
        return True, f"Customer {data['full_name']} created with ID: {customer_id}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def get_all_customers():
    try:
        conn = get_db_connection()
        if conn is None:
            return {}
        cursor = conn.cursor()
        cursor.execute('''
            SELECT customer_id, full_name, address, phone, whatsapp_number, email, 
                   id_type, id_number, aadhar_number, pan_number, date_of_birth, age,
                   nominee_name, nominee_address, nominee_relation, nominee_dob, nominee_age,
                   aadhar_image, pan_image, nominee_aadhar_image, nominee_pan_image
            FROM customers WHERE kyc_completed = 1 ORDER BY created_date DESC
        ''')
        result = cursor.fetchall()
        conn.close()
        customers = {}
        for row in result:
            customers[row[0]] = {
                'customer_id': row[0], 'full_name': row[1], 'address': row[2], 'phone': row[3],
                'whatsapp_number': row[4], 'email': row[5], 'id_type': row[6], 'id_number': row[7],
                'aadhar_number': row[8], 'pan_number': row[9], 'date_of_birth': row[10], 'age': row[11],
                'nominee_name': row[12], 'nominee_address': row[13], 'nominee_relation': row[14],
                'nominee_dob': row[15], 'nominee_age': row[16],
                'aadhar_image': row[17] if len(row) > 17 else None,
                'pan_image': row[18] if len(row) > 18 else None,
                'nominee_aadhar_image': row[19] if len(row) > 19 else None,
                'nominee_pan_image': row[20] if len(row) > 20 else None
            }
        return customers
    except:
        return {}

def get_customer_details(customer_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM customers WHERE customer_id = ?', (customer_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            columns = ['id', 'customer_id', 'full_name', 'address', 'phone', 'whatsapp_number', 
                      'email', 'id_type', 'id_number', 'aadhar_number', 'aadhar_image', 
                      'pan_number', 'pan_image', 'date_of_birth', 'age', 'nominee_name', 
                      'nominee_address', 'nominee_relation', 'nominee_dob', 'nominee_age', 
                      'nominee_aadhar', 'nominee_aadhar_image', 'nominee_pan', 'nominee_pan_image']
            return dict(zip(columns, result))
        return None
    except:
        return None

def get_customer_balances(customer_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return {}
        cursor = conn.cursor()
        cursor.execute('SELECT account_code, balance FROM customer_accounts WHERE customer_id = ?', (customer_id,))
        result = cursor.fetchall()
        conn.close()
        balances = {}
        for row in result:
            balances[row[0]] = row[1]
        return balances
    except:
        return {}

# ============== VOUCHER FUNCTIONS ==============
def generate_voucher_number(voucher_type):
    prefix_map = {'JOURNAL': 'JV', 'RECEIPT': 'RV', 'PAYMENT': 'PV', 'CONTRA': 'CV', 'INTEREST': 'INT'}
    prefix = prefix_map.get(voucher_type, 'V')
    return f"{prefix}-{datetime.now().strftime('%Y')}-{str(int(time.time()))[-6:]}"

def generate_transaction_id():
    return f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{str(int(time.time()))[-6:]}"

def generate_account_number():
    try:
        conn = get_db_connection()
        if conn is None:
            return f"SB{datetime.now().strftime('%Y%m')}{str(int(time.time()))[-6:]}"
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sb_accounts")
        count = cursor.fetchone()[0]
        conn.close()
        return f"SB{datetime.now().strftime('%Y%m')}{str(count + 1).zfill(6)}"
    except:
        return f"SB{datetime.now().strftime('%Y%m')}{str(int(time.time()))[-6:]}"

def save_voucher(voucher_type, voucher_date, description, entries, username):
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        voucher_number = generate_voucher_number(voucher_type)
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        total_amount = sum(entry['amount'] for entry in entries)
        
        # Insert voucher
        cursor.execute('INSERT INTO vouchers (voucher_number, voucher_type, voucher_date, description, total_amount, created_date, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)',
                      (voucher_number, voucher_type, voucher_date, description, total_amount, current_date, username))
        
        # Process each entry
        for entry in entries:
            # Insert into voucher_entries
            cursor.execute('INSERT INTO voucher_entries (voucher_number, entry_type, account_code, account_name, amount, narration) VALUES (?, ?, ?, ?, ?, ?)',
                          (voucher_number, entry['entry_type'], entry['account_code'], entry['account_name'], entry['amount'], entry.get('narration', '')))
            
            # UPDATE ACCOUNT BALANCE
            if entry['entry_type'] == 'DEBIT':
                success, msg = update_account_balance(entry['account_code'], entry['amount'], is_debit=True)
            else:
                success, msg = update_account_balance(entry['account_code'], entry['amount'], is_debit=False)
            
            if not success:
                conn.close()
                return False, f"Error updating balance for {entry['account_name']}: {msg}"
            
            # Insert into journal_entries
            cursor.execute('INSERT INTO journal_entries (date, account_code, account_name, entry_type, amount, description, ref_no, username, voucher_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                          (voucher_date, entry['account_code'], entry['account_name'], entry['entry_type'], entry['amount'], description, voucher_number, username, voucher_number))
        
        conn.commit()
        conn.close()
        return True, f"Voucher {voucher_number} saved successfully"
    except Exception as e:
        print(f"Error in save_voucher: {e}")
        return False, f"Error: {str(e)}"

def get_all_vouchers(limit=100):
    try:
        conn = get_db_connection()
        if conn is None:
            return []
        cursor = conn.cursor()
        cursor.execute('SELECT voucher_number, voucher_type, voucher_date, description, total_amount, status, created_date, created_by FROM vouchers ORDER BY created_date DESC LIMIT ?', (limit,))
        result = cursor.fetchall()
        conn.close()
        vouchers = []
        for row in result:
            vouchers.append({'voucher_number': row[0], 'voucher_type': row[1], 'voucher_date': row[2], 'description': row[3], 'total_amount': row[4], 'status': row[5], 'created_date': row[6], 'created_by': row[7]})
        return vouchers
    except:
        return []

def delete_voucher(voucher_number):
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM vouchers WHERE voucher_number = ?', (voucher_number,))
        if not cursor.fetchone():
            conn.close()
            return False, "Voucher not found"
        cursor.execute('SELECT entry_type, account_code, amount FROM voucher_entries WHERE voucher_number = ?', (voucher_number,))
        entries = cursor.fetchall()
        for entry in entries:
            if entry[0] == 'DEBIT':
                update_account_balance(entry[1], entry[2], is_debit=False)
            else:
                update_account_balance(entry[1], entry[2], is_debit=True)
        cursor.execute('DELETE FROM voucher_entries WHERE voucher_number = ?', (voucher_number,))
        cursor.execute('DELETE FROM journal_entries WHERE voucher_number = ?', (voucher_number,))
        cursor.execute('DELETE FROM vouchers WHERE voucher_number = ?', (voucher_number,))
        conn.commit()
        conn.close()
        return True, "Voucher deleted successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"

# ============== SB ACCOUNT FUNCTIONS ==============
def create_sb_account(data, username):
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        account_number = generate_account_number()
        opening_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO sb_accounts (account_number, customer_id, customer_name, kyc_id, kyc_type,
                address, phone, email, opening_balance, current_balance,
                interest_rate, interest_payable, account_status, opening_date, 
                last_interest_date, created_by, nominee_name, nominee_relation, aadhar_number, pan_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (account_number, data['customer_id'], data['customer_name'], data['kyc_id'], data['kyc_type'],
              data['address'], data['phone'], data['email'], data['opening_balance'], data['opening_balance'],
              data['interest_rate'], 0, 'ACTIVE', opening_date, opening_date, username,
              data.get('nominee_name', ''), data.get('nominee_relation', ''),
              data.get('aadhar_number', ''), data.get('pan_number', '')))
        if data['opening_balance'] > 0:
            transaction_id = generate_transaction_id()
            cursor.execute('''
                INSERT INTO sb_transactions (transaction_id, account_number, transaction_date, value_date,
                    particulars, credit, balance, transaction_type, created_by, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (transaction_id, account_number, opening_date, opening_date, 'Opening Balance',
                  data['opening_balance'], data['opening_balance'], 'DEPOSIT', username, opening_date))
        conn.commit()
        conn.close()
        return True, f"SB Account {account_number} created successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"

def get_sb_account(account_number):
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sb_accounts WHERE account_number = ?', (account_number,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {
                'account_number': result[1], 'customer_id': result[2], 'customer_name': result[3],
                'kyc_id': result[4], 'kyc_type': result[5], 'address': result[6], 'phone': result[7],
                'email': result[8], 'opening_balance': get_safe_float(result[9]),
                'current_balance': get_safe_float(result[10]), 'interest_rate': get_safe_float(result[11], 3.5),
                'interest_payable': get_safe_float(result[12]), 'account_status': result[13] if result[13] else 'ACTIVE',
                'opening_date': result[14], 'last_interest_date': result[15], 'created_by': result[17]
            }
        return None
    except:
        return None

def get_all_sb_accounts():
    try:
        conn = get_db_connection()
        if conn is None:
            return []
        cursor = conn.cursor()
        cursor.execute('''
            SELECT account_number, customer_id, customer_name, kyc_id, 
                   opening_balance, current_balance, interest_rate, 
                   interest_payable, account_status, opening_date
            FROM sb_accounts ORDER BY opening_date DESC
        ''')
        result = cursor.fetchall()
        conn.close()
        accounts = []
        for row in result:
            accounts.append({
                'account_number': row[0], 'customer_id': row[1], 'customer_name': row[2],
                'kyc_id': row[3], 'opening_balance': get_safe_float(row[4]),
                'current_balance': get_safe_float(row[5]), 'interest_rate': get_safe_float(row[6], 3.5),
                'interest_payable': get_safe_float(row[7]), 'account_status': row[8] if row[8] else 'ACTIVE',
                'opening_date': row[9] if row[9] else ''
            })
        return accounts
    except:
        return []

def get_sb_transactions(account_number, limit=100):
    try:
        conn = get_db_connection()
        if conn is None:
            return []
        cursor = conn.cursor()
        cursor.execute('''
            SELECT transaction_id, transaction_date, value_date, particulars, debit, credit, balance, transaction_type
            FROM sb_transactions 
            WHERE account_number = ? 
            ORDER BY value_date DESC, transaction_date DESC
            LIMIT ?
        ''', (account_number, limit))
        result = cursor.fetchall()
        conn.close()
        transactions = []
        for row in result:
            transactions.append({
                'transaction_id': row[0],
                'transaction_date': row[1],
                'value_date': row[2],
                'particulars': row[3],
                'debit': row[4] if row[4] is not None else 0,
                'credit': row[5] if row[5] is not None else 0,
                'balance': row[6] if row[6] is not None else 0,
                'transaction_type': row[7]
            })
        return transactions
    except:
        return []

def get_sb_transactions_by_date(account_number, from_date, to_date):
    try:
        conn = get_db_connection()
        if conn is None:
            return []
        cursor = conn.cursor()
        cursor.execute('''
            SELECT transaction_id, transaction_date, value_date, particulars, debit, credit, balance, transaction_type
            FROM sb_transactions 
            WHERE account_number = ? AND value_date >= ? AND value_date <= ?
            ORDER BY value_date DESC, transaction_date DESC
        ''', (account_number, from_date, to_date))
        result = cursor.fetchall()
        conn.close()
        transactions = []
        for row in result:
            transactions.append({
                'transaction_id': row[0],
                'transaction_date': row[1],
                'value_date': row[2],
                'particulars': row[3],
                'debit': row[4] if row[4] is not None else 0,
                'credit': row[5] if row[5] is not None else 0,
                'balance': row[6] if row[6] is not None else 0,
                'transaction_type': row[7]
            })
        return transactions
    except:
        return []

def deposit_sb_account(account_number, amount, particulars, value_date, username):
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        cursor.execute('SELECT current_balance FROM sb_accounts WHERE account_number = ?', (account_number,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "Account not found"
        current_balance = result[0]
        new_balance = current_balance + amount
        transaction_id = generate_transaction_id()
        transaction_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('UPDATE sb_accounts SET current_balance = ? WHERE account_number = ?', (new_balance, account_number))
        cursor.execute('''
            INSERT INTO sb_transactions (transaction_id, account_number, transaction_date, value_date,
                particulars, credit, balance, transaction_type, created_by, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transaction_id, account_number, transaction_date, value_date, particulars,
              amount, new_balance, 'DEPOSIT', username, transaction_date))
        conn.commit()
        conn.close()
        return True, f"Deposited ₹{amount:,.2f}. New balance: ₹{new_balance:,.2f}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def withdraw_sb_account(account_number, amount, particulars, value_date, username):
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
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
        cursor.execute('UPDATE sb_accounts SET current_balance = ? WHERE account_number = ?', (new_balance, account_number))
        cursor.execute('''
            INSERT INTO sb_transactions (transaction_id, account_number, transaction_date, value_date,
                particulars, debit, balance, transaction_type, created_by, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transaction_id, account_number, transaction_date, value_date, particulars,
              amount, new_balance, 'WITHDRAWAL', username, transaction_date))
        conn.commit()
        conn.close()
        return True, f"Withdrawn ₹{amount:,.2f}. New balance: ₹{new_balance:,.2f}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def calculate_and_credit_interest(account_number, username):
    """Calculate and credit quarterly interest for SB account with DOUBLE ENTRY"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        
        # Get account details
        cursor.execute('SELECT current_balance, interest_rate, interest_payable, customer_name FROM sb_accounts WHERE account_number = ?', (account_number,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "Account not found"
        
        current_balance, interest_rate, interest_payable, customer_name = result
        interest = current_balance * (interest_rate / 100) * (90 / 365)
        
        if interest <= 0:
            conn.close()
            return False, "No interest to credit"
        
        # ============== PART 1: Update SB Account ==============
        new_balance = current_balance + interest
        new_interest_payable = get_safe_float(interest_payable) + interest
        
        cursor.execute('UPDATE sb_accounts SET current_balance = ?, interest_payable = ?, last_interest_credited = ? WHERE account_number = ?',
                      (new_balance, new_interest_payable, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), account_number))
        
        # Record SB transaction
        transaction_id = generate_transaction_id()
        transaction_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        value_date = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute('''
            INSERT INTO sb_transactions (transaction_id, account_number, transaction_date, value_date,
                particulars, credit, balance, transaction_type, created_by, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transaction_id, account_number, transaction_date, value_date, f'Quarterly Interest @ {interest_rate}%',
              interest, new_balance, 'INTEREST', 'SYSTEM', transaction_date))
        
        # ============== PART 2: POST DOUBLE ENTRY TO MAIN SYSTEM ==============
        voucher_number = generate_voucher_number('INTEREST')
        
        # DEBIT: SB Interest Expense (5999) - Expense increases
        cursor.execute('''
            INSERT INTO journal_entries (date, account_code, account_name, entry_type, amount, description, ref_no, username, voucher_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (value_date, '5999', 'SB_INTEREST_EXPENSE', 'DEBIT', interest, 
              f'Quarterly Interest on SB Account {account_number} - {customer_name}', voucher_number, username, voucher_number))
        
        # CREDIT: SB Interest Payable (2500) - Liability increases
        cursor.execute('''
            INSERT INTO journal_entries (date, account_code, account_name, entry_type, amount, description, ref_no, username, voucher_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (value_date, '2500', 'SB_INTEREST_PAYABLE', 'CREDIT', interest, 
              f'Quarterly Interest on SB Account {account_number} - {customer_name}', voucher_number, username, voucher_number))
        
        # ============== PART 3: UPDATE ACCOUNT BALANCES IN MAIN ACCOUNTS TABLE ==============
        # Update SB Interest Expense - DEBIT (increases expense)
        exp_success, exp_balance = update_account_balance('5999', interest, is_debit=True)
        if not exp_success:
            conn.close()
            return False, f"Error updating SB Interest Expense: {exp_balance}"
        
        # Update SB Interest Payable - CREDIT (increases liability)
        pay_success, pay_balance = update_account_balance('2500', interest, is_debit=False)
        if not pay_success:
            conn.close()
            return False, f"Error updating SB Interest Payable: {pay_balance}"
        
        # ============== PART 4: Record in interest history ==============
        cursor.execute('''
            INSERT INTO sb_interest_history (account_number, quarter_start, quarter_end, interest_rate,
                average_balance, interest_amount, interest_payable, credited_date, voucher_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (account_number, datetime.now().replace(day=1).strftime('%Y-%m-%d'), datetime.now().strftime('%Y-%m-%d'),
              interest_rate, current_balance, interest, interest, transaction_date, voucher_number))
        
        conn.commit()
        conn.close()
        
        return True, f"Interest ₹{interest:,.2f} credited at {interest_rate}%.\n\nJournal Entry:\nDr SB_INTEREST_EXPENSE (5999) - ₹{interest:,.2f}\nCr SB_INTEREST_PAYABLE (2500) - ₹{interest:,.2f}"
    except Exception as e:
        print(f"Error in calculate_and_credit_interest: {e}")
        return False, f"Error: {str(e)}"

# ============== FINANCIAL REPORTS ==============
def get_trial_balance():
    accounts = get_all_accounts()
    trial_balance = []
    total_debits, total_credits = 0, 0
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

def get_balance_sheet():
    accounts = get_all_accounts()
    assets, liabilities, equity = {}, {}, {}
    for code, data in accounts.items():
        if data['account_type'] == 'ASSET':
            assets[data['account_name']] = data['balance']
        elif data['account_type'] == 'LIABILITY':
            liabilities[data['account_name']] = data['balance']
        elif data['account_type'] == 'EQUITY':
            equity[data['account_name']] = data['balance']
    return {
        'assets': assets, 
        'liabilities': liabilities, 
        'equity': equity, 
        'total_assets': sum(assets.values()), 
        'total_liabilities': sum(liabilities.values()), 
        'total_equity': sum(equity.values())
    }

def get_profit_loss():
    accounts = get_all_accounts()
    income, expenses = {}, {}
    for code, data in accounts.items():
        if data['account_type'] == 'INCOME':
            income[data['account_name']] = data['balance']
        elif data['account_type'] == 'EXPENSE':
            expenses[data['account_name']] = data['balance']
    return {
        'income': income, 
        'expenses': expenses, 
        'total_income': sum(income.values()), 
        'total_expenses': sum(expenses.values()), 
        'net_profit': sum(income.values()) - sum(expenses.values())
    }

def display_account_card(acc_code, icon, color):
    accounts = get_all_accounts()
    if acc_code not in accounts:
        return
    data = accounts[acc_code]
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {color}20, {color}05); padding: 12px; border-radius: 8px; border-left: 4px solid {color}; margin-bottom: 6px;">
        <div style="display: flex; justify-content: space-between;">
            <span style="font-size: 11px; color: #888;">{acc_code} | {data['account_type']}</span>
            <span style="font-size: 11px; color: #888;">{icon}</span>
        </div>
        <div style="font-size: 13px; font-weight: 500;">{data['account_name'].replace('_', ' ').title()}</div>
        <div style="font-size: 18px; font-weight: bold;">₹{data['balance']:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

# ============== UI RENDER FUNCTIONS ==============
def render_customer_registration():
    st.subheader("📝 Register New Customer with KYC")
    
    with st.form("customer_form"):
        st.markdown("### 📋 Personal Details")
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name*")
            address = st.text_area("Address*")
            phone = st.text_input("Phone Number*")
            email = st.text_input("Email*")
            whatsapp = st.text_input("WhatsApp Number")
        with col2:
            dob = st.date_input("Date of Birth", min_value=datetime(1900, 1, 1).date(), max_value=datetime.now().date())
            if dob:
                age = datetime.now().year - dob.year - ((datetime.now().month, datetime.now().day) < (dob.month, dob.day))
                st.info(f"Age: {age} years")
            else:
                age = None
            id_type = st.selectbox("ID Type", ["Aadhaar", "PAN", "Passport", "Driving License", "Voter ID"])
            id_number = st.text_input("ID Number*")
        
        st.markdown("### 🪪 KYC Documents (Compulsory)")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Aadhaar Card**")
            aadhar_number = st.text_input("Aadhaar Number (12 digits)*")
            if aadhar_number and not validate_aadhar(aadhar_number):
                st.error("Invalid Aadhaar number. Must be 12 digits.")
            aadhar_file = st.file_uploader("Upload Aadhaar Card Image*", type=['jpg', 'jpeg', 'png', 'pdf'], key="aadhar_upload")
        with col2:
            st.markdown("**PAN Card**")
            pan_number = st.text_input("PAN Number (e.g., ABCDE1234F)*")
            if pan_number and not validate_pan(pan_number):
                st.error("Invalid PAN number. Format: ABCDE1234F")
            pan_file = st.file_uploader("Upload PAN Card Image*", type=['jpg', 'jpeg', 'png', 'pdf'], key="pan_upload")
        
        st.markdown("### 👤 Nominee Details")
        col1, col2 = st.columns(2)
        with col1:
            nominee_name = st.text_input("Nominee Full Name")
            nominee_relation = st.text_input("Nominee Relation (e.g., Spouse, Son, Daughter)")
            nominee_dob = st.date_input("Nominee Date of Birth", min_value=datetime(1900, 1, 1).date(), max_value=datetime.now().date())
            if nominee_dob:
                nominee_age = datetime.now().year - nominee_dob.year - ((datetime.now().month, datetime.now().day) < (nominee_dob.month, nominee_dob.day))
                st.caption(f"Nominee Age: {nominee_age} years")
            else:
                nominee_age = None
        with col2:
            nominee_address = st.text_area("Nominee Address")
        
        st.markdown("**Nominee Documents (Optional)**")
        col1, col2 = st.columns(2)
        with col1:
            nominee_aadhar = st.text_input("Nominee Aadhaar Number")
            if nominee_aadhar and not validate_aadhar(nominee_aadhar):
                st.error("Invalid Aadhaar number. Must be 12 digits.")
            nominee_aadhar_file = st.file_uploader("Upload Nominee Aadhaar Image", type=['jpg', 'jpeg', 'png', 'pdf'], key="nom_aadhar_upload")
        with col2:
            nominee_pan = st.text_input("Nominee PAN Number")
            if nominee_pan and not validate_pan(nominee_pan):
                st.error("Invalid PAN number. Format: ABCDE1234F")
            nominee_pan_file = st.file_uploader("Upload Nominee PAN Image", type=['jpg', 'jpeg', 'png', 'pdf'], key="nom_pan_upload")
        
        if st.form_submit_button("✅ Register Customer"):
            errors = []
            if not full_name:
                errors.append("Full Name required")
            if not address:
                errors.append("Address required")
            if not phone:
                errors.append("Phone required")
            if not email:
                errors.append("Email required")
            if not aadhar_number:
                errors.append("Aadhaar Number required")
            elif not validate_aadhar(aadhar_number):
                errors.append("Invalid Aadhaar number")
            if not pan_number:
                errors.append("PAN Number required")
            elif not validate_pan(pan_number):
                errors.append("Invalid PAN number")
            if not aadhar_file:
                errors.append("Aadhaar Card image required")
            if not pan_file:
                errors.append("PAN Card image required")
            if not id_number:
                errors.append("ID Number required")
            
            if errors:
                for e in errors:
                    st.error(e)
            else:
                aadhar_image_b64 = image_to_base64(aadhar_file)
                pan_image_b64 = image_to_base64(pan_file)
                nominee_aadhar_b64 = image_to_base64(nominee_aadhar_file) if nominee_aadhar_file else None
                nominee_pan_b64 = image_to_base64(nominee_pan_file) if nominee_pan_file else None
                
                data = {
                    'full_name': full_name, 'address': address, 'phone': phone,
                    'whatsapp_number': whatsapp, 'email': email, 'id_type': id_type,
                    'id_number': id_number, 'aadhar_number': aadhar_number,
                    'aadhar_image': aadhar_image_b64, 'pan_number': pan_number,
                    'pan_image': pan_image_b64, 'date_of_birth': dob.strftime('%Y-%m-%d') if dob else None,
                    'age': age, 'nominee_name': nominee_name,
                    'nominee_address': nominee_address, 'nominee_relation': nominee_relation,
                    'nominee_dob': nominee_dob.strftime('%Y-%m-%d') if nominee_dob else None,
                    'nominee_age': nominee_age, 'nominee_aadhar': nominee_aadhar,
                    'nominee_aadhar_image': nominee_aadhar_b64, 'nominee_pan': nominee_pan,
                    'nominee_pan_image': nominee_pan_b64
                }
                success, msg = create_customer(data, st.session_state.user['username'])
                st.success(msg) if success else st.error(msg)
                if success:
                    st.rerun()

def render_customer_list():
    st.subheader("📋 Customer List")
    customers = get_all_customers()
    if not customers:
        st.info("No customers registered")
        return
    cust_data = []
    for cid, cust in customers.items():
        balances = get_customer_balances(cid)
        cust_data.append({
            'ID': cid, 'Name': cust['full_name'], 'Phone': cust['phone'],
            'Email': cust['email'], 'Aadhaar': cust.get('aadhar_number', ''),
            'PAN': cust.get('pan_number', ''), 'Age': cust.get('age', ''),
            'Savings': f"₹{balances.get('1100', 0):,.2f}",
            'Current': f"₹{balances.get('1200', 0):,.2f}",
            'Nominee': cust.get('nominee_name', 'N/A')
        })
    st.dataframe(pd.DataFrame(cust_data), use_container_width=True, hide_index=True)
    
    st.divider()
    st.subheader("🔍 View Customer Details")
    selected = st.selectbox("Select Customer", [""] + [f"{c['full_name']} ({cid})" for cid, c in customers.items()])
    if selected:
        cust_id = selected.split('(')[-1].replace(')', '')
        cust = customers[cust_id]
        details = get_customer_details(cust_id)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Name:** {cust['full_name']}")
            st.markdown(f"**ID:** {cust_id}")
            st.markdown(f"**Phone:** {cust['phone']}")
            st.markdown(f"**WhatsApp:** {cust.get('whatsapp_number', 'N/A')}")
        with col2:
            st.markdown(f"**Email:** {cust['email']}")
            st.markdown(f"**DOB:** {cust.get('date_of_birth', 'N/A')}")
            st.markdown(f"**Age:** {cust.get('age', 'N/A')} years")
            st.markdown(f"**ID Type:** {cust.get('id_type', 'N/A')}")
        with col3:
            st.markdown(f"**Aadhaar:** {cust.get('aadhar_number', 'N/A')}")
            st.markdown(f"**PAN:** {cust.get('pan_number', 'N/A')}")
        
        st.markdown("---")
        st.markdown("### 📎 Uploaded Documents")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Aadhaar Card**")
            if details and details.get('aadhar_image'):
                st.image(display_image_from_base64(details['aadhar_image']), use_container_width=True)
            else:
                st.caption("No Aadhaar image uploaded")
            
            st.markdown("**PAN Card**")
            if details and details.get('pan_image'):
                st.image(display_image_from_base64(details['pan_image']), use_container_width=True)
            else:
                st.caption("No PAN image uploaded")
        with col2:
            st.markdown("**Nominee Aadhaar Card**")
            if details and details.get('nominee_aadhar_image'):
                st.image(display_image_from_base64(details['nominee_aadhar_image']), use_container_width=True)
            else:
                st.caption("No Nominee Aadhaar image uploaded")
            
            st.markdown("**Nominee PAN Card**")
            if details and details.get('nominee_pan_image'):
                st.image(display_image_from_base64(details['nominee_pan_image']), use_container_width=True)
            else:
                st.caption("No Nominee PAN image uploaded")
        
        if cust.get('nominee_name'):
            st.markdown("---")
            st.markdown("### 👤 Nominee Details")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Name:** {cust.get('nominee_name', 'N/A')}")
                st.markdown(f"**Relation:** {cust.get('nominee_relation', 'N/A')}")
            with col2:
                st.markdown(f"**DOB:** {cust.get('nominee_dob', 'N/A')}")
                st.markdown(f"**Age:** {cust.get('nominee_age', 'N/A')} years")
            with col3:
                st.markdown(f"**Aadhaar:** {cust.get('nominee_aadhar', 'N/A')}")
                st.markdown(f"**PAN:** {cust.get('nominee_pan', 'N/A')}")
            st.markdown(f"**Address:** {cust.get('nominee_address', 'N/A')}")

def render_head_management():
    st.subheader("⚙️ Head Management")
    expense_accounts = [acc for acc in get_all_accounts().values() if acc['account_type'] == 'EXPENSE']
    income_accounts = [acc for acc in get_all_accounts().values() if acc['account_type'] == 'INCOME']
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📉 Expense Heads")
        if expense_accounts:
            df = pd.DataFrame([{'Code': a['account_code'], 'Name': a['account_name'], 'Balance': f"₹{a['balance']:,.2f}"} for a in expense_accounts])
            st.dataframe(df, use_container_width=True, hide_index=True)
    with col2:
        st.markdown("### 📊 Income Heads")
        if income_accounts:
            df = pd.DataFrame([{'Code': a['account_code'], 'Name': a['account_name'], 'Balance': f"₹{a['balance']:,.2f}"} for a in income_accounts])
            st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.divider()
    st.markdown("### ➕ Create New Head")
    col1, col2 = st.columns(2)
    with col1:
        with st.form("create_expense"):
            name = st.text_input("Expense Head Name")
            if st.form_submit_button("Create Expense"):
                if name:
                    success, msg = create_account(name, 'EXPENSE', 0, None, st.session_state.user['username'])
                    st.success(msg) if success else st.error(msg)
                    if success:
                        st.rerun()
    with col2:
        with st.form("create_income"):
            name = st.text_input("Income Head Name")
            if st.form_submit_button("Create Income"):
                if name:
                    success, msg = create_account(name, 'INCOME', 0, None, st.session_state.user['username'])
                    st.success(msg) if success else st.error(msg)
                    if success:
                        st.rerun()

def render_journal_voucher_form():
    st.subheader("📝 Create Journal Voucher")
    all_accounts = get_all_accounts()
    account_options = []
    account_code_map = {}
    for code, data in all_accounts.items():
        display_text = f"{data['account_name']} ({code})"
        account_options.append(display_text)
        account_code_map[display_text] = code
    if not account_options:
        st.warning("No accounts found.")
        return None
    with st.form("journal_voucher_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            voucher_date = st.date_input("Voucher Date", value=datetime.now().date())
        with col2:
            st.text_input("Voucher Number", value="Auto-generated", disabled=True)
        with col3:
            voucher_type = st.selectbox("Voucher Type", ['JOURNAL', 'RECEIPT', 'PAYMENT', 'CONTRA'])
        description = st.text_area("Description")
        st.markdown("---")
        st.markdown("### Voucher Entries")
        entries = []
        num_entries = st.number_input("Number of entries", min_value=2, max_value=10, value=2, step=1)
        for i in range(num_entries):
            st.markdown(f"**Entry {i+1}**")
            col1, col2, col3, col4 = st.columns([1, 2, 1.5, 1.5])
            with col1:
                entry_type = st.selectbox(f"Type", ['DEBIT', 'CREDIT'], key=f"type_{i}")
            with col2:
                account_display = st.selectbox(f"Account", account_options, key=f"acc_{i}")
                acc_code = account_code_map.get(account_display, '')
                acc_name = account_display.split('(')[0].strip() if account_display else ''
            with col3:
                amount = st.number_input(f"Amount", min_value=0.0, step=100.0, key=f"amt_{i}")
            with col4:
                narration = st.text_input(f"Narration", key=f"nar_{i}", placeholder="Optional")
            if account_display and amount > 0 and acc_code:
                entries.append({'entry_type': entry_type, 'account_code': acc_code, 'account_name': acc_name, 'amount': amount, 'narration': narration})
        total_debits = sum(e['amount'] for e in entries if e['entry_type'] == 'DEBIT')
        total_credits = sum(e['amount'] for e in entries if e['entry_type'] == 'CREDIT')
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Debits", f"₹{total_debits:,.2f}")
        with col2:
            st.metric("Total Credits", f"₹{total_credits:,.2f}")
        with col3:
            diff = total_debits - total_credits
            if abs(diff) < 0.01 and total_debits > 0:
                st.success("✅ Balanced")
            else:
                st.error(f"❌ Difference: ₹{diff:,.2f}")
        if st.form_submit_button("💾 Save Voucher", type="primary"):
            if not entries:
                st.error("Please enter at least one valid entry")
                return None
            if total_debits == 0 or total_credits == 0:
                st.error("Please enter amounts greater than zero")
                return None
            if abs(diff) > 0.01:
                st.error("Total Debits must equal Total Credits")
                return None
            return {'voucher_type': voucher_type, 'voucher_date': voucher_date.strftime('%Y-%m-%d'), 'description': description, 'entries': entries}
    return None

def render_voucher_list():
    st.subheader("📋 Voucher List")
    col1, col2 = st.columns(2)
    with col1:
        filter_type = st.selectbox("Filter by Type", ['ALL', 'JOURNAL', 'RECEIPT', 'PAYMENT', 'CONTRA'])
    with col2:
        if st.button("🔄 Refresh"):
            st.rerun()
    vouchers = get_all_vouchers(200)
    if filter_type != 'ALL':
        vouchers = [v for v in vouchers if v['voucher_type'] == filter_type]
    if not vouchers:
        st.info("No vouchers found")
        return None
    df = pd.DataFrame(vouchers)
    st.dataframe(df[['voucher_number', 'voucher_type', 'voucher_date', 'description', 'total_amount', 'status', 'created_by']], use_container_width=True)
    selected = st.selectbox("Select Voucher to Delete", [""] + [v['voucher_number'] for v in vouchers])
    if selected and st.button("🗑️ Delete Voucher", type="secondary"):
        if st.button("✅ Confirm Delete", type="primary"):
            success, msg = delete_voucher(selected)
            st.success(msg) if success else st.error(msg)
            if success:
                st.rerun()
    return None

def render_sb_account_creation():
    st.subheader("🏦 Create Savings Bank Account")
    customers = get_all_customers()
    if not customers:
        st.warning("Please register a customer first.")
        return
    customer_options = [f"{c['full_name']} ({cid})" for cid, c in customers.items()]
    selected = st.selectbox("Select Customer", customer_options)
    if selected:
        cust_id = selected.split('(')[-1].replace(')', '')
        cust = customers[cust_id]
        with st.form("sb_form"):
            col1, col2 = st.columns(2)
            with col1:
                customer_name = st.text_input("Customer Name", value=cust['full_name'], disabled=True)
                opening_balance = st.number_input("Opening Balance", min_value=0.0, step=100.0, value=0.0)
            with col2:
                interest_rate = st.number_input("Interest Rate (%)", min_value=0.0, max_value=20.0, step=0.1, value=3.5)
                nominee_name = st.text_input("Nominee Name")
            if st.form_submit_button("✅ Create SB Account"):
                data = {
                    'customer_id': cust_id, 'customer_name': cust['full_name'],
                    'kyc_id': 'KYC001', 'kyc_type': 'Aadhaar',
                    'address': cust['address'], 'phone': cust['phone'],
                    'email': cust['email'], 'opening_balance': opening_balance,
                    'interest_rate': interest_rate, 'nominee_name': nominee_name,
                    'nominee_relation': '', 'aadhar_number': cust.get('aadhar_number', ''),
                    'pan_number': cust.get('pan_number', '')
                }
                success, msg = create_sb_account(data, st.session_state.user['username'])
                st.success(msg) if success else st.error(msg)
                if success:
                    st.rerun()

def render_sb_operations():
    st.subheader("💰 Savings Bank Account Operations")
    accounts = get_all_sb_accounts()
    if not accounts:
        st.warning("No SB accounts found.")
        return
    account_options = [f"{a['account_number']} - {a['customer_name']} (₹{a['current_balance']:,.2f})" for a in accounts if a['account_status'] == 'ACTIVE']
    if not account_options:
        st.warning("No active SB accounts.")
        return
    selected = st.selectbox("Select Account", account_options)
    if selected:
        acc_no = selected.split(' - ')[0]
        account = get_sb_account(acc_no)
        if account:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💰 Current Balance", f"₹{account['current_balance']:,.2f}")
            with col2:
                st.metric("📊 Interest Rate", f"{account['interest_rate']}%")
            with col3:
                st.metric("📋 Interest Payable", f"₹{account['interest_payable']:,.2f}")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 💵 Deposit")
                dep_date = st.date_input("Date", value=datetime.now().date(), key="dep_date")
                dep_amt = st.number_input("Amount", min_value=0.0, step=100.0, key="dep_amt")
                dep_part = st.text_input("Particulars", key="dep_part", placeholder="Cash deposit")
                if st.button("💰 Deposit", key="dep_btn"):
                    if dep_amt > 0:
                        success, msg = deposit_sb_account(acc_no, dep_amt, dep_part, dep_date.strftime('%Y-%m-%d'), st.session_state.user['username'])
                        st.success(msg) if success else st.error(msg)
                        if success:
                            st.rerun()
            with col2:
                st.markdown("### 💸 Withdraw")
                wd_date = st.date_input("Date", value=datetime.now().date(), key="wd_date")
                wd_amt = st.number_input("Amount", min_value=0.0, step=100.0, key="wd_amt")
                wd_part = st.text_input("Particulars", key="wd_part", placeholder="ATM withdrawal")
                if st.button("💸 Withdraw", key="wd_btn"):
                    if wd_amt > 0:
                        success, msg = withdraw_sb_account(acc_no, wd_amt, wd_part, wd_date.strftime('%Y-%m-%d'), st.session_state.user['username'])
                        st.success(msg) if success else st.error(msg)
                        if success:
                            st.rerun()
            st.markdown("---")
            st.markdown("### 📊 Interest")
            est_interest = account['current_balance'] * (account['interest_rate'] / 100) * (90 / 365)
            st.caption(f"Estimated Quarterly Interest: ₹{est_interest:,.2f}")
            if st.button("🧮 Calculate & Credit Interest"):
                success, msg = calculate_and_credit_interest(acc_no, st.session_state.user['username'])
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

def render_sb_report():
    st.subheader("📊 SB Account Report")
    accounts = get_all_sb_accounts()
    if not accounts:
        st.warning("No SB accounts found.")
        return
    
    account_options = [f"{a['account_number']} - {a['customer_name']}" for a in accounts]
    selected = st.selectbox("Select Account", account_options)
    
    if selected:
        acc_no = selected.split(' - ')[0]
        account = get_sb_account(acc_no)
        
        if account:
            st.markdown("### 📋 Account Summary")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Account Number", account['account_number'])
            with col2:
                st.metric("Customer", account['customer_name'])
            with col3:
                st.metric("Interest Rate", f"{account['interest_rate']}%")
            with col4:
                st.metric("Interest Payable", f"₹{account['interest_payable']:,.2f}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Opening Balance", f"₹{account['opening_balance']:,.2f}")
            with col2:
                st.metric("Current Balance", f"₹{account['current_balance']:,.2f}")
            
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                from_date = st.date_input("From Date", value=datetime.now().date() - timedelta(days=30), key="report_from")
            with col2:
                to_date = st.date_input("To Date", value=datetime.now().date(), key="report_to")
            
            if st.button("📄 Generate Report", key="generate_report_btn"):
                transactions = get_sb_transactions_by_date(acc_no, from_date.strftime('%Y-%m-%d'), to_date.strftime('%Y-%m-%d'))
                
                if transactions:
                    st.markdown("### 📝 Transaction Details")
                    df = pd.DataFrame(transactions)
                    display_df = df.copy()
                    display_df['Debit'] = display_df['debit'].apply(lambda x: f"₹{x:,.2f}" if x > 0 else '-')
                    display_df['Credit'] = display_df['credit'].apply(lambda x: f"₹{x:,.2f}" if x > 0 else '-')
                    display_df['Balance'] = display_df['balance'].apply(lambda x: f"₹{x:,.2f}")
                    
                    display_columns = ['value_date', 'particulars', 'Debit', 'Credit', 'Balance', 'transaction_type']
                    st.dataframe(display_df[display_columns], use_container_width=True, hide_index=True)
                    
                    st.markdown("### 📊 Transaction Summary")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        total_debits = sum(t['debit'] for t in transactions)
                        st.metric("Total Debits", f"₹{total_debits:,.2f}")
                    with col2:
                        total_credits = sum(t['credit'] for t in transactions)
                        st.metric("Total Credits", f"₹{total_credits:,.2f}")
                    with col3:
                        net_change = total_credits - total_debits
                        st.metric("Net Change", f"₹{net_change:,.2f}")
                    with col4:
                        st.metric("Closing Balance", f"₹{account['current_balance']:,.2f}")
                    
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"SB_Account_{acc_no}_{from_date.strftime('%Y%m%d')}_{to_date.strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No transactions found for the selected period")
            
            st.markdown("---")
            st.markdown("### 📝 Recent Transactions (Last 10)")
            recent_transactions = get_sb_transactions(acc_no, 10)
            if recent_transactions:
                df_recent = pd.DataFrame(recent_transactions)
                df_recent['Debit'] = df_recent['debit'].apply(lambda x: f"₹{x:,.2f}" if x > 0 else '-')
                df_recent['Credit'] = df_recent['credit'].apply(lambda x: f"₹{x:,.2f}" if x > 0 else '-')
                df_recent['Balance'] = df_recent['balance'].apply(lambda x: f"₹{x:,.2f}")
                st.dataframe(df_recent[['value_date', 'particulars', 'Debit', 'Credit', 'Balance', 'transaction_type']], 
                           use_container_width=True, hide_index=True)
            else:
                st.info("No recent transactions found")

def verify_account_balances():
    st.subheader("🔍 Account Balance Verification")
    
    accounts = get_all_accounts()
    
    data = []
    for code, acc in accounts.items():
        data.append({
            'Code': code,
            'Name': acc['account_name'],
            'Type': acc['account_type'],
            'Balance': f"₹{acc['balance']:,.2f}"
        })
    
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    tb_df, total_debits, total_credits = get_trial_balance()
    st.metric("Total Debits", f"₹{total_debits:,.2f}")
    st.metric("Total Credits", f"₹{total_credits:,.2f}")
    
    if abs(total_debits - total_credits) < 0.01:
        st.success("✅ Trial Balance is Balanced!")
    else:
        st.error(f"❌ Difference: ₹{total_debits - total_credits:,.2f}")

# ============== LOGIN PAGE ==============
def login_page():
    st.title("🏦 Complete Banking System")
    st.subheader("🔐 Login")
    if not os.path.exists(DB_FILE):
        init_database()
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            user = verify_user(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.success(f"Welcome, {user['full_name']}!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    st.caption("Default: admin/admin123, teller1/demo123, manager/demo123")

def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.rerun()

# ============== MAIN APP ==============
def main():
    try:
        if not os.path.exists(DB_FILE):
            init_database()
        else:
            # Even if database exists, ensure all accounts are present
            ensure_accounts_exist()
            migrate_database()
        
        if 'logged_in' not in st.session_state or not st.session_state.logged_in:
            login_page()
            return
        user = st.session_state.user
        col1, col2, col3 = st.columns([2.5, 1.5, 1])
        with col1:
            st.title("🏦 Complete Banking System")
        with col2:
            st.markdown(f"**👤 {user['full_name']}**")
            st.caption(f"Role: {user['role']}")
        with col3:
            if st.button("🚪 Logout"):
                logout()
        st.divider()
        
        with st.sidebar:
            st.header("📊 Account Overview")
            st.subheader("💰 Cash & Bank")
            display_account_card('1000', '💵', '#00A86B')
            display_account_card('1001', '💵', '#00A86B')
            display_account_card('1100', '🏦', '#2E86AB')
            display_account_card('1200', '🏦', '#1B4F72')
            st.divider()
            with st.expander("🏦 Other ASSETS"):
                for code in ['1300', '1400', '1500', '1600']:
                    display_account_card(code, '💰', '#2E86AB')
            with st.expander("🏛️ LIABILITIES"):
                for code in ['2100', '2200', '2300', '2400', '2500']:
                    display_account_card(code, '🏛️', '#A23B72')
            with st.expander("📈 EQUITY"):
                for code in ['3100', '3200']:
                    display_account_card(code, '📈', '#F18F01')
            with st.expander("📊 INCOME"):
                for acc in get_all_accounts().values():
                    if acc['account_type'] == 'INCOME':
                        display_account_card(acc['account_code'], '📊', '#1B998B')
            with st.expander("📉 EXPENSES"):
                for acc in get_all_accounts().values():
                    if acc['account_type'] == 'EXPENSE':
                        display_account_card(acc['account_code'], '📉', '#D65D5D')
        
        tabs = ["📝 Vouchers", "👥 Customers", "🏦 SB Accounts", "📊 Reports", "📋 Trial Balance", "⚙️ Heads", "🔍 Verify"]
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(tabs)
        
        with tab1:
            st.header("📝 Voucher Management")
            vtab1, vtab2 = st.tabs(["➕ Create", "📋 View/Delete"])
            with vtab1:
                result = render_journal_voucher_form()
                if result:
                    success, msg = save_voucher(result['voucher_type'], result['voucher_date'], result['description'], result['entries'], user['username'])
                    st.success(msg) if success else st.error(msg)
                    if success:
                        st.rerun()
            with vtab2:
                render_voucher_list()
        
        with tab2:
            st.header("👥 Customer Management")
            ctab1, ctab2 = st.tabs(["➕ Register", "📋 List"])
            with ctab1:
                render_customer_registration()
            with ctab2:
                render_customer_list()
        
        with tab3:
            st.header("🏦 Savings Bank Accounts")
            sbtab1, sbtab2, sbtab3 = st.tabs(["🏦 Create", "💰 Operations", "📊 Reports"])
            with sbtab1:
                render_sb_account_creation()
            with sbtab2:
                render_sb_operations()
            with sbtab3:
                render_sb_report()
        
        with tab4:
            st.header("📊 Financial Reports")
            report_type = st.radio("Select Report", ["Balance Sheet", "Profit & Loss"], horizontal=True)
            if report_type == "Balance Sheet":
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
                    total = bs['total_liabilities'] + bs['total_equity']
                    if abs(bs['total_assets'] - total) < 0.01:
                        st.success(f"✅ Balanced: ₹{bs['total_assets']:,.2f} = ₹{total:,.2f}")
                    else:
                        st.error(f"❌ Difference: ₹{bs['total_assets'] - total:,.2f}")
            else:
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
                    if abs(total_debits - total_credits) < 0.01:
                        st.success("✅ Balanced!")
                    else:
                        st.error(f"❌ Difference: ₹{total_debits - total_credits:,.2f}")
            else:
                st.info("No accounts to display")
        
        with tab6:
            render_head_management()
        
        with tab7:
            verify_account_balances()
            
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
