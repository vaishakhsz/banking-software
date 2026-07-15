
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
            cursor.execute('SELECT COUNT(*) FROM accounts WHERE account_code = ?', (acc[0],))
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                    INSERT INTO accounts (account_code, account_name, account_type, balance, daily_limit, maturity_date, interest_rate, created_date, is_active, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', acc)
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error in ensure_accounts_exist: {e}")

def migrate_database():
    try:
        conn = get_db_connection()
        if conn is None:
            return
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(sb_interest_history)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'interest_payable' not in columns:
            cursor.execute("ALTER TABLE sb_interest_history ADD COLUMN interest_payable REAL DEFAULT 0")
            conn.commit()
        
        if 'voucher_number' not in columns:
            cursor.execute("ALTER TABLE sb_interest_history ADD COLUMN voucher_number TEXT")
            conn.commit()
        
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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customer_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                account_code TEXT NOT NULL,
                balance REAL DEFAULT 0
            )
        ''')
        
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
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        
        cursor.execute('SELECT account_type, balance FROM accounts WHERE account_code = ? AND is_active = 1', (account_code,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, f"Account {account_code} not found"
        
        acc_type, current_balance = result
        
        if acc_type in ['ASSET', 'EXPENSE']:
            if is_debit:
                new_balance = current_balance + amount
            else:
                new_balance = current_balance - amount
        else:
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
        
        cursor.execute('INSERT INTO vouchers (voucher_number, voucher_type, voucher_date, description, total_amount, created_date, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)',
                      (voucher_number, voucher_type, voucher_date, description, total_amount, current_date, username))
        
        for entry in entries:
            cursor.execute('INSERT INTO voucher_entries (voucher_number, entry_type, account_code, account_name, amount, narration) VALUES (?, ?, ?, ?, ?, ?)',
                          (voucher_number, entry['entry_type'], entry['account_code'], entry['account_name'], entry['amount'], entry.get('narration', '')))
            
            if entry['entry_type'] == 'DEBIT':
                success, msg = update_account_balance(entry['account_code'], entry['amount'], is_debit=True)
            else:
                success, msg = update_account_balance(entry['account_code'], entry['amount'], is_debit=False)
            
            if not success:
                conn.close()
                return False, f"Error updating balance for {entry['account_name']}: {msg}"
            
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
            return False, "Insufficient balance"
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
        return True, f"Withdrew ₹{amount:,.2f}. New balance: ₹{new_balance:,.2f}"
    except Exception as e:
        return False, f"Error: {str(e)}"

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
            
    # Calculate Profit/Loss to append to retained earnings
    pl = get_profit_loss()
    net_profit = pl['net_profit']
    if 'RETAINED_EARNINGS' in equity:
        equity['RETAINED_EARNINGS'] += net_profit
    else:
        equity['RETAINED_EARNINGS'] = net_profit
        
    return {'assets': assets, 'liabilities': liabilities, 'equity': equity, 'total_assets': sum(assets.values()), 'total_liabilities_equity': sum(liabilities.values()) + sum(equity.values())}

def get_profit_loss():
    accounts = get_all_accounts()
    income, expenses = {}, {}
    for code, data in accounts.items():
        if data['account_type'] == 'INCOME':
            income[data['account_name']] = data['balance']
        elif data['account_type'] == 'EXPENSE':
            expenses[data['account_name']] = data['balance']
    total_income = sum(income.values())
    total_expenses = sum(expenses.values())
    return {'income': income, 'expenses': expenses, 'total_income': total_income, 'total_expenses': total_expenses, 'net_profit': total_income - total_expenses}

def verify_account_balances():
    try:
        conn = get_db_connection()
        if conn is None:
            return
        cursor = conn.cursor()
        cursor.execute("SELECT account_code, account_name, account_type, balance FROM accounts")
        db_accounts = cursor.fetchall()
        
        st.subheader("🔍 Real-time Internal System Verification")
        audit_data = []
        
        for code, name, acc_type, current_bal in db_accounts:
            cursor.execute("SELECT entry_type, amount FROM journal_entries WHERE account_code = ?", (code,))
            entries = cursor.fetchall()
            
            calculated_balance = 0.0
            if code == '3100': # Starting Capital Injection fallback if not tracked in general logs
                calculated_balance = 1000000.0
                
            for entry_type, amount in entries:
                if acc_type in ['ASSET', 'EXPENSE']:
                    if entry_type == 'DEBIT':
                        calculated_balance += amount
                    else:
                        calculated_balance -= amount
                else:
                    if entry_type == 'DEBIT':
                        calculated_balance -= amount
                    else:
                        calculated_balance += amount
            
            diff = abs(current_bal - calculated_balance)
            audit_data.append({
                "Code": code,
                "Name": name,
                "Type": acc_type,
                "Ledger Balance": f"₹{current_bal:,.2f}",
                "Journal Audited Balance": f"₹{calculated_balance:,.2f}",
                "Status": "✅ Match" if diff < 0.01 else f"❌ Mismatch (₹{diff:,.2f})"
            })
        
        st.dataframe(pd.DataFrame(audit_data), use_container_width=True, hide_index=True)
        conn.close()
    except Exception as e:
        st.error(f"Audit failed: {str(e)}")

def render_head_management():
    st.header("🗂️ Chart of Accounts Management")
    
    with st.form("create_head_form"):
        st.subheader("Create New Ledger/Account Head")
        head_name = st.text_input("Account Head Name (e.g. Electricity Expense)")
        head_type = st.selectbox("Account Category", ["ASSET", "LIABILITY", "EQUITY", "INCOME", "EXPENSE"])
        initial_bal = st.number_input("Opening Balance", min_value=0.0, value=0.0, step=100.0)
        daily_lim = st.number_input("Daily Transaction Limit (Optional, 0 for None)", min_value=0.0, value=0.0, step=1000.0)
        
        if st.form_submit_button("Create Account Head"):
            if not head_name:
                st.error("Please enter a valid head name")
            else:
                lim = None if daily_lim == 0 else daily_lim
                success, msg = create_account(head_name, head_type, initial_bal, lim, st.session_state.user['username'])
                if success:
                    st.success(msg)
                    st.session_state.accounts_dirty = True
                    st.rerun()
                else:
                    st.error(msg)

def login_page():
    st.markdown("""
        <style>
        .login-box {
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h2 style='text-align: center;'>🏦 Core Enterprise & Savings Banking Engine</h2>", unsafe_allow_html=True)
    
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
        # 1. Initialize DB file structure once
        if not os.path.exists(DB_FILE):
            init_database()
        
        # 2. Performance Fix: Only perform heavy routines ONCE per application context startup
        if "db_initialized" not in st.session_state:
            ensure_accounts_exist()
            migrate_database()
            st.session_state.db_initialized = True

        if 'logged_in' not in st.session_state or not st.session_state.logged_in:
            login_page()
            return
            
        user = st.session_state.user
        col1, col2, col3 = st.columns([2.5, 1.5, 1])
        with col1:
            st.title("🏦 Complete ERP & Core Banking")
        with col2:
            st.markdown(f"<p style='margin-top:25px;'>👤 <b>{user['full_name']}</b> ({user['role'].upper()})</p>", unsafe_allow_html=True)
        with col3:
            st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
            if st.button("Logout", key="logout_top_btn"):
                logout()
                
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "💰 Savings Bank (SB)", 
            "📝 Voucher Posting", 
            "📖 Journal Ledger", 
            "📊 Profit & Loss", 
            "📋 Trial Balance",
            "🗂️ Manage Heads",
            "🔍 System Audit"
        ])
        
        with tab1:
            st.header("💰 Savings Bank (SB) Module")
            sb_sub_tab1, sb_sub_tab2, sb_sub_tab3, sb_sub_tab4 = st.tabs([
                "🆕 Open SB Account", "💵 Deposit/Withdrawal", "📋 Active Accounts", "📄 Account Statements"
            ])
            
            with sb_sub_tab1:
                st.subheader("Open New Savings Bank Account")
                customers = get_all_customers()
                
                # Dynamic generation helper fallback if customer profile table is empty
                if not customers:
                    st.info("No primary KYC directory profiles found. Please register customer under standard database schema first or input directly down below.")
                    
                with st.form("open_sb_form"):
                    cust_name = st.text_input("Customer Name")
                    cust_phone = st.text_input("Phone Number")
                    cust_email = st.text_input("Email ID")
                    cust_address = st.text_area("Address")
                    kyc_type = st.selectbox("KYC Identity Document Type", ["AADHAR", "PAN", "PASSPORT", "VOTER_ID"])
                    kyc_id = st.text_input("KYC Identity Document Number")
                    opening_bal = st.number_input("Initial Opening Deposit Amount", min_value=0.0, value=500.0, step=100.0)
                    interest_rate = st.number_input("Interest Rate Offered (% per annum)", min_value=0.0, max_value=15.0, value=3.5, step=0.25)
                    
                    nom_name = st.text_input("Nominee Name")
                    nom_rel = st.text_input("Relationship with Nominee")
                    
                    if st.form_submit_button("Provision SB Account"):
                        if not cust_name or not kyc_id:
                            st.error("Customer name and KYC documentation are required fields.")
                        else:
                            sb_data = {
                                'customer_id': f"CUST-{str(int(time.time()))[-5:]}",
                                'customer_name': cust_name,
                                'kyc_id': kyc_id,
                                'kyc_type': kyc_type,
                                'address': cust_address,
                                'phone': cust_phone,
                                'email': cust_email,
                                'opening_balance': opening_bal,
                                'interest_rate': interest_rate,
                                'nominee_name': nom_name,
                                'nominee_relation': nom_rel
                            }
                            # Book entry automatically into 2100 Customer Deposit Liability Account
                            success, msg = create_sb_account(sb_data, user['username'])
                            if success:
                                update_account_balance('1000', opening_bal, is_debit=True) # Cash account Debit increases
                                update_account_balance('2100', opening_bal, is_debit=False) # Deposit Liability Credit increases
                                st.success(msg)
                            else:
                                st.error(msg)
                                
            with sb_sub_tab2:
                st.subheader("Post Cash Transaction into Savings Portfolio")
                accounts = get_all_sb_accounts()
                if not accounts:
                    st.info("No functional savings accounts registered.")
                else:
                    acc_options = [f"{a['account_number']} - {a['customer_name']}" for a in accounts]
                    selected_acc = st.selectbox("Select Target Portfolio Holder", acc_options, key="txn_sb_acc")
                    acc_no = selected_acc.split(' - ')[0]
                    
                    txn_type = st.radio("Transaction Type Mode", ["DEPOSIT", "WITHDRAWAL"])
                    txn_amount = st.number_input("Transaction Cash Amount (₹)", min_value=1.0, value=1000.0, step=500.0)
                    particulars = st.text_input("Transaction Description/Remarks", value="Cash Transaction")
                    val_date = st.date_input("Value Date Effective", value=datetime.now().date())
                    
                    if st.button("Execute SB Transaction Transaction"):
                        if txn_type == "DEPOSIT":
                            success, msg = deposit_sb_account(acc_no, txn_amount, particulars, val_date.strftime('%Y-%m-%d'), user['username'])
                            if success:
                                update_account_balance('1000', txn_amount, is_debit=True)
                                update_account_balance('2100', txn_amount, is_debit=False)
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                        else:
                            success, msg = withdraw_sb_account(acc_no, txn_amount, particulars, val_date.strftime('%Y-%m-%d'), user['username'])
                            if success:
                                update_account_balance('1000', txn_amount, is_debit=False)
                                update_account_balance('2100', txn_amount, is_debit=True)
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                                
            with sb_sub_tab3:
                st.subheader("Active Savings Portfolios Registry")
                accounts = get_all_sb_accounts()
                if accounts:
                    st.dataframe(pd.DataFrame(accounts), use_container_width=True, hide_index=True)
                else:
                    st.info("No records to pull.")
                    
            with sb_sub_tab4:
                st.subheader("Generate Statement / Account Reports Ledger")
                accounts = get_all_sb_accounts()
                if not accounts:
                    st.info("No active portfolios detected.")
                else:
                    account_options = [f"{a['account_number']} - {a['customer_name']}" for a in accounts]
                    selected = st.selectbox("Select Target Account Portfolio", account_options, key="stmt_sb_select")
                    if selected:
                        acc_no = selected.split(' - ')[0]
                        account = get_sb_account(acc_no)
                        if account:
                            st.markdown("### 📋 Portfolio Summary")
                            col1, col2, col3, col4 = st.columns(4)
                            with col1: st.metric("Account Number", account['account_number'])
                            with col2: st.metric("Customer Name", account['customer_name'])
                            with col3: st.metric("Yield Rate", f"{account['interest_rate']}%")
                            with col4: st.metric("Accrued Liability Pay", f"₹{account['interest_payable']:,.2f}")
                            
                            col1, col2 = st.columns(2)
                            with col1: st.metric("Initial Deposit Booked", f"₹{account['opening_balance']:,.2f}")
                            with col2: st.metric("Current Dynamic Ledger Balance", f"₹{account['current_balance']:,.2f}")
                            
                            st.divider()
                            col1, col2 = st.columns(2)
                            from_date = st.date_input("Query From Date", value=datetime.now().date() - timedelta(days=30), key="report_from")
                            to_date = st.date_input("Query To Date", value=datetime.now().date(), key="report_to")
                            
                            if st.button("📄 Query Statement Matrix", key="generate_report_btn"):
                                transactions = get_sb_transactions_by_date(acc_no, from_date.strftime('%Y-%m-%d'), to_date.strftime('%Y-%m-%d'))
                                if transactions:
                                    df = pd.DataFrame(transactions)
                                    display_df = df.copy()
                                    display_df['Debit Amount'] = display_df['debit'].apply(lambda x: f"₹{x:,.2f}" if x > 0 else '-')
                                    display_df['Credit Amount'] = display_df['credit'].apply(lambda x: f"₹{x:,.2f}" if x > 0 else '-')
                                    display_df['Running Balance'] = display_df['balance'].apply(lambda x: f"₹{x:,.2f}")
                                    st.dataframe(display_df[['value_date', 'particulars', 'Debit Amount', 'Credit Amount', 'Running Balance', 'transaction_type']], use_container_width=True, hide_index=True)
                                else:
                                    st.info("No records matching the timeline found inside ledger history.")
        
        with tab2:
            st.header("📝 Double-Entry Voucher Ledger Posting")
            accounts = get_all_accounts()
            
            if 'voucher_entries' not in st.session_state:
                st.session_state.voucher_entries = []
                
            v_type = st.selectbox("Voucher Category Classification Head", ["JOURNAL", "RECEIPT", "PAYMENT", "CONTRA"])
            v_date = st.date_input("Voucher Transaction Entry Date", value=datetime.now().date())
            v_desc = st.text_input("Voucher Master Global Summary Narration/Description")
            
            st.divider()
            st.subheader("Add Balanced Entry Row Item")
            
            col1, col2, col3 = st.columns([1.5, 1, 1.5])
            with col1:
                acc_opts = [f"{code} - {data['account_name']} ({data['account_type']})" for code, data in accounts.items()]
                selected_entry_acc = st.selectbox("Select Target Head Ledger", acc_opts, key="voucher_entry_acc_select")
            with col2:
                e_type = st.selectbox("Debit / Credit Instruction Type", ["DEBIT", "CREDIT"], key="voucher_entry_dc")
            with col3:
                e_amt = st.number_input("Transaction Value Metric Amount (₹)", min_value=0.01, value=0.0, step=100.0, key="voucher_entry_amt")
                
            e_narration = st.text_input("Line Item Breakout Specific Row Narration", key="voucher_entry_narr")
            
            if st.button("➕ Push Row Line Item into Voucher Stack"):
                code = selected_entry_acc.split(' - ')[0]
                name = selected_entry_acc.split(' - ')[1].split(' (')[0]
                st.session_state.voucher_entries.append({
                    'account_code': code,
                    'account_name': name,
                    'entry_type': e_type,
                    'amount': e_amt,
                    'narration': e_narration
                })
                st.toast("Row Line Item added to current workspace stack.")
                
            if st.session_state.voucher_entries:
                st.markdown("### 📊 Current Workspace Entry Balancing Matrix Grid")
                v_df = pd.DataFrame(st.session_state.voucher_entries)
                st.dataframe(v_df, use_container_width=True)
                
                total_deb = sum(x['amount'] for x in st.session_state.voucher_entries if x['entry_type'] == 'DEBIT')
                total_cred = sum(x['amount'] for x in st.session_state.voucher_entries if x['entry_type'] == 'CREDIT')
                
                col_d, col_c = st.columns(2)
                col_d.metric("Total Sum Debits Matrix", f"₹{total_deb:,.2f}")
                col_c.metric("Total Sum Credits Matrix", f"₹{total_cred:,.2f}")
                
                if st.button("🗑️ Reset Workspace Staging Form Layout"):
                    st.session_state.voucher_entries = []
                    st.rerun()
                    
                if abs(total_deb - total_credits) < 0.01 and total_deb > 0:
                    if st.button("💾 Commit Transaction Entry and Execute Post to Book"):
                        success, msg = save_voucher(v_type, v_date.strftime('%Y-%m-%d'), v_desc, st.session_state.voucher_entries, user['username'])
                        if success:
                            st.success(msg)
                            st.session_state.voucher_entries = []
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    st.warning("⚠️ Ledger entry mismatch warning. Double entry systems mandate that total debits must mathematically match total credits exactly to process booking pipelines.")
                    
        with tab3:
            st.header("📖 General Journal Ledger Book")
            
            # Journal Filter Form to restrict data size dynamically
            col_filter1, col_filter2 = st.columns(2)
            with col_filter1:
                j_from_date = st.date_input("Journal View From Date", value=datetime.now().date() - timedelta(days=60), key="j_from_d")
            with col_filter2:
                j_to_date = st.date_input("Journal View To Date", value=datetime.now().date(), key="j_to_d")
            
            conn = get_db_connection()
            if conn is not None:
                cursor = conn.cursor()
                # Query with structured time constraints and standard fallback limit to speed up execution
                cursor.execute('''
                    SELECT date, voucher_number, account_code, account_name, entry_type, amount, description, username 
                    FROM journal_entries 
                    WHERE date >= ? AND date <= ?
                    ORDER BY date DESC, voucher_number DESC LIMIT 500
                ''', (j_from_date.strftime('%Y-%m-%d'), j_to_date.strftime('%Y-%m-%d')))
                j_rows = cursor.fetchall()
                conn.close()
                
                if j_rows:
                    j_df = pd.DataFrame(j_rows, columns=['Date', 'Voucher ID', 'Code', 'Account Name', 'Type', 'Amount', 'Global Summary Description', 'Operator Module'])
                    j_df['Amount'] = j_df['Amount'].apply(lambda x: f"₹{x:,.2f}")
                    st.dataframe(j_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No journal entry parameters recorded matching date ranges.")
                    
        with tab4:
            st.header("📊 Profit & Loss Account Statements (Income Statement)")
            pl = get_profit_loss()
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Revenue Streams / Operational Income")
                if pl['income']:
                    for inc_name, inc_bal in pl['income'].items():
                        st.text(f"{inc_name}: ₹{inc_bal:,.2f}")
                else: st.info("No income records generated yet.")
            with col2:
                st.subheader("Operational Expense Accounts Ledger")
                if pl['expenses']:
                    for exp_name, exp_bal in pl['expenses'].items():
                        st.text(f"{exp_name}: ₹{exp_bal:,.2f}")
                else: st.info("No expense data recorded inside metrics.")
                
            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Gross Revenue Income Summation", f"₹{pl['total_income']:,.2f}")
            with col2: st.metric("Gross Operational Overhead Expense", f"₹{pl['total_expenses']:,.2f}")
            with col3:
                if pl['net_profit'] >= 0:
                    st.success(f"NET PERIOD PROFIT SURPLUS: ₹{pl['net_profit']:,.2f} 🎉")
                else:
                    st.error(f"NET RETAINED LOSS INCURRED: ₹{abs(pl['net_profit']):,.2f}")
                    
        with tab5:
            st.header("📋 Balanced Unadjusted Trial Balance")
            tb_df, total_debits, total_credits = get_trial_balance()
            if not tb_df.empty:
                st.dataframe(tb_df, use_container_width=True, hide_index=True)
                col1, col2, col3 = st.columns(3)
                with col1: st.metric("Summation Debits Balance Metrics", f"₹{total_debits:,.2f}")
                with col2: st.metric("Summation Credits Balance Metrics", f"₹{total_credits:,.2f}")
                with col3:
                    if abs(total_debits - total_credits) < 0.01:
                        st.success("✅ Ledger Balanced Successfully Status!")
                    else:
                        st.error(f"❌ Difference out of adjustment detected: ₹{total_debits - total_credits:,.2f}")
            else:
                st.info("No core accounts parameters exist.")
                
        with tab6:
            render_head_management()
            
        with tab7:
            verify_account_balances()
            
    except Exception as e:
        st.error(f"Critical System Core Process Interrupted: {str(e)}")
        st.code(traceback.format_exc())

if __name__ == "__main__":
    main()


