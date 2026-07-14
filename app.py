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

def migrate_database():
    """Add missing columns to existing tables"""
    try:
        conn = get_db_connection()
        if conn is None:
            return
        cursor = conn.cursor()
        
        # Check if value_date column exists in sb_transactions
        cursor.execute("PRAGMA table_info(sb_transactions)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'value_date' not in columns:
            print("Adding value_date column to sb_transactions...")
            cursor.execute("ALTER TABLE sb_transactions ADD COLUMN value_date TEXT")
            cursor.execute("UPDATE sb_transactions SET value_date = transaction_date WHERE value_date IS NULL")
            conn.commit()
            print("value_date column added successfully")
        
        if 'created_date' not in columns:
            print("Adding created_date column to sb_transactions...")
            cursor.execute("ALTER TABLE sb_transactions ADD COLUMN created_date TEXT")
            cursor.execute("UPDATE sb_transactions SET created_date = transaction_date WHERE created_date IS NULL")
            conn.commit()
            print("created_date column added successfully")
        
        # Check if sb_accounts table needs new columns for interest payable
        cursor.execute("PRAGMA table_info(sb_accounts)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'interest_payable' not in columns:
            print("Adding interest_payable column to sb_accounts...")
            cursor.execute("ALTER TABLE sb_accounts ADD COLUMN interest_payable REAL DEFAULT 0")
            conn.commit()
            print("interest_payable column added successfully")
        
        if 'last_interest_credited' not in columns:
            print("Adding last_interest_credited column to sb_accounts...")
            cursor.execute("ALTER TABLE sb_accounts ADD COLUMN last_interest_credited TEXT")
            conn.commit()
            print("last_interest_credited column added successfully")
        
        conn.close()
        print("Database migration completed successfully")
    except Exception as e:
        print(f"Error in migrate_database: {e}")

def init_database():
    """Initialize all tables for Complete Banking System"""
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
                voucher_number TEXT,
                FOREIGN KEY (account_code) REFERENCES accounts(account_code)
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
                voucher_number TEXT,
                FOREIGN KEY (account_code) REFERENCES accounts(account_code)
            )
        ''')
        
        # Customer transactions
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
                voucher_number TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                FOREIGN KEY (account_code) REFERENCES accounts(account_code)
            )
        ''')
        
        # Cash transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cash_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE NOT NULL,
                date TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                balance_after REAL,
                username TEXT,
                customer_id TEXT,
                voucher_number TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
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
        
        # Voucher entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS voucher_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voucher_number TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                account_code TEXT NOT NULL,
                account_name TEXT NOT NULL,
                amount REAL NOT NULL,
                narration TEXT,
                FOREIGN KEY (voucher_number) REFERENCES vouchers(voucher_number),
                FOREIGN KEY (account_code) REFERENCES accounts(account_code)
            )
        ''')
        
        # ============== SAVINGS BANK ACCOUNT TABLES ==============
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
                created_date TEXT NOT NULL,
                FOREIGN KEY (account_number) REFERENCES sb_accounts(account_number)
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
                voucher_number TEXT,
                FOREIGN KEY (account_number) REFERENCES sb_accounts(account_number)
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
        
        # Check if default admin user exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("Creating default users...")
            current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            admin_password = hash_password("admin123")
            
            cursor.execute('''
                INSERT INTO users 
                (username, password_hash, full_name, role, created_date)
                VALUES (?, ?, ?, ?, ?)
            ''', ("admin", admin_password, "System Administrator", "admin", current_date))
            
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
        
        # Check if default accounts exist
        cursor.execute("SELECT COUNT(*) FROM accounts")
        count = cursor.fetchone()[0]
        
        if count == 0:
            current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            default_accounts = [
                # ===== ASSETS (1xxx) =====
                ('1000', 'CASH', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
                ('1001', 'PETTY_CASH', 'ASSET', 0, 10000, None, None, current_date, 1, 'system'),
                ('1100', 'BANK_SAVINGS', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
                ('1200', 'BANK_CURRENT', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
                ('1300', 'FD', 'ASSET', 0, None, None, 7.0, current_date, 1, 'system'),
                ('1400', 'DAILY_COLLECTION', 'ASSET', 0, 50000, None, None, current_date, 1, 'system'),
                ('1500', 'SUNDRY_DEBTORS', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
                ('1600', 'LOANS_ADVANCED', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
                ('1700', 'SB_INTEREST_PAYABLE', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
                
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
            
            for acc in default_accounts:
                cursor.execute('''
                    INSERT INTO accounts 
                    (account_code, account_name, account_type, balance, daily_limit, maturity_date, interest_rate, created_date, is_active, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (acc[0], acc[1], acc[2], acc[3], acc[4], acc[5], acc[6], acc[7], acc[8], acc[9]))
        
        conn.close()
        print("Database initialized successfully")
        migrate_database()
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
        
        hashed = hash_password(password)
        
        cursor.execute('SELECT * FROM users WHERE username = ? AND password_hash = ?', 
                       (username, hashed))
        user = cursor.fetchone()
        
        if user:
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
def calculate_age_from_date(dob):
    """Calculate age from date object"""
    if not dob:
        return None
    try:
        today = datetime.now().date()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
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

def display_image_from_base64(base64_string):
    """Display image from base64 string"""
    if not base64_string:
        return None
    try:
        return f"data:image/jpeg;base64,{base64_string}"
    except Exception as e:
        print(f"Error displaying image: {e}")
        return None

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

def generate_voucher_number(voucher_type):
    """Generate unique voucher number"""
    prefix_map = {
        'JOURNAL': 'JV',
        'RECEIPT': 'RV',
        'PAYMENT': 'PV',
        'CONTRA': 'CV',
        'INTEREST': 'INT'
    }
    prefix = prefix_map.get(voucher_type, 'V')
    year = datetime.now().strftime('%Y')
    return f"{prefix}-{year}-{str(int(time.time()))[-6:]}"

def calculate_interest(principal, rate, days):
    """Calculate simple interest"""
    return (principal * rate * days) / (100 * 365)

def generate_account_code(account_type):
    """Generate a new account code based on type"""
    try:
        conn = get_db_connection()
        if conn is None:
            return '5100'
        cursor = conn.cursor()
        
        prefix_map = {
            'INCOME': '4',
            'EXPENSE': '5',
            'ASSET': '1',
            'LIABILITY': '2',
            'EQUITY': '3'
        }
        
        prefix = prefix_map.get(account_type, '9')
        cursor.execute(f'''
            SELECT account_code FROM accounts 
            WHERE account_code LIKE '{prefix}%' 
            AND account_type = ?
            AND is_active = 1
            ORDER BY account_code DESC LIMIT 1
        ''', (account_type,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            last_code = int(result[0])
            new_code = str(last_code + 1)
        else:
            if account_type == 'INCOME':
                new_code = '4100'
            elif account_type == 'EXPENSE':
                new_code = '5100'
            elif account_type == 'ASSET':
                new_code = '1500'
            elif account_type == 'LIABILITY':
                new_code = '2300'
            elif account_type == 'EQUITY':
                new_code = '3300'
            else:
                new_code = '9100'
        
        return new_code
    except Exception as e:
        print(f"Error in generate_account_code: {e}")
        return '5100'

def create_account(account_name, account_type, initial_balance=0, daily_limit=None, interest_rate=None, username=""):
    """Create a new account"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM accounts WHERE account_name = ? AND account_type = ? AND is_active = 1', 
                       (account_name, account_type))
        if cursor.fetchone():
            conn.close()
            return False, f"Account '{account_name}' already exists in {account_type} category"
        
        account_code = generate_account_code(account_type)
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if daily_limit is not None and daily_limit <= 0:
            daily_limit = None
        
        cursor.execute('''
            INSERT INTO accounts 
            (account_code, account_name, account_type, balance, daily_limit, interest_rate, created_date, created_by, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (account_code, account_name.upper(), account_type, initial_balance, daily_limit, interest_rate, date, username, 1))
        
        conn.commit()
        conn.close()
        return True, f"Account '{account_name}' created with code {account_code}"
    except Exception as e:
        print(f"Error in create_account: {e}")
        return False, f"Error creating account: {str(e)}"

def update_account(account_code, new_name, new_daily_limit=None, new_interest_rate=None):
    """Update an existing account"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM accounts WHERE account_code = ? AND is_active = 1', (account_code,))
        if not cursor.fetchone():
            conn.close()
            return False, "Account not found"
        
        cursor.execute('SELECT * FROM accounts WHERE account_name = ? AND account_code != ? AND is_active = 1', 
                       (new_name.upper(), account_code))
        if cursor.fetchone():
            conn.close()
            return False, f"Account '{new_name}' already exists"
        
        updates = []
        params = []
        
        if new_name:
            updates.append("account_name = ?")
            params.append(new_name.upper())
        
        if new_daily_limit is not None:
            if new_daily_limit <= 0:
                new_daily_limit = None
            updates.append("daily_limit = ?")
            params.append(new_daily_limit)
        
        if new_interest_rate is not None:
            updates.append("interest_rate = ?")
            params.append(new_interest_rate)
        
        if updates:
            query = f"UPDATE accounts SET {', '.join(updates)} WHERE account_code = ?"
            params.append(account_code)
            cursor.execute(query, params)
            conn.commit()
        
        conn.close()
        return True, "Account updated successfully"
    except Exception as e:
        print(f"Error in update_account: {e}")
        return False, f"Error updating account: {str(e)}"

def delete_account(account_code):
    """Delete an account (soft delete - mark inactive)"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM accounts WHERE account_code = ? AND is_active = 1', (account_code,))
        if not cursor.fetchone():
            conn.close()
            return False, "Account not found"
        
        cursor.execute('SELECT COUNT(*) FROM transactions WHERE account_code = ?', (account_code,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            cursor.execute('UPDATE accounts SET is_active = 0 WHERE account_code = ?', (account_code,))
            conn.commit()
            conn.close()
            return True, "Account has transactions. Marked as inactive."
        else:
            cursor.execute('DELETE FROM accounts WHERE account_code = ?', (account_code,))
            conn.commit()
            conn.close()
            return True, "Account deleted successfully"
    except Exception as e:
        print(f"Error in delete_account: {e}")
        return False, f"Error deleting account: {str(e)}"

# ============== ACCOUNT FUNCTIONS ==============
def get_account_balance(account_code):
    """Get current balance of an account"""
    try:
        conn = get_db_connection()
        if conn is None:
            return 0
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM accounts WHERE account_code = ?', (account_code,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    except Exception as e:
        print(f"Error in get_account_balance: {e}")
        return 0

def get_all_accounts():
    """Get all active accounts"""
    try:
        conn = get_db_connection()
        if conn is None:
            return {}
        cursor = conn.cursor()
        cursor.execute('''
            SELECT account_code, account_name, account_type, balance, daily_limit, is_active
            FROM accounts 
            WHERE is_active = 1
            ORDER BY account_code
        ''')
        result = cursor.fetchall()
        conn.close()
        
        accounts = {}
        for row in result:
            accounts[row[0]] = {
                'account_code': row[0],
                'account_name': row[1],
                'account_type': row[2],
                'balance': row[3],
                'daily_limit': row[4] if row[4] is not None else None,
                'is_active': row[5]
            }
        return accounts
    except Exception as e:
        print(f"Error in get_all_accounts: {e}")
        return {}

def get_accounts_by_type(account_type):
    """Get all accounts of a specific type"""
    try:
        conn = get_db_connection()
        if conn is None:
            return []
        cursor = conn.cursor()
        cursor.execute('''
            SELECT account_code, account_name, account_type, balance, daily_limit, interest_rate, is_active, created_date, created_by
            FROM accounts 
            WHERE account_type = ? AND is_active = 1
            ORDER BY account_code
        ''', (account_type,))
        result = cursor.fetchall()
        conn.close()
        
        accounts = []
        for row in result:
            accounts.append({
                'account_code': row[0],
                'account_name': row[1],
                'account_type': row[2],
                'balance': row[3],
                'daily_limit': row[4] if row[4] is not None else None,
                'interest_rate': row[5],
                'is_active': row[6],
                'created_date': row[7],
                'created_by': row[8] if len(row) > 8 else 'system'
            })
        return accounts
    except Exception as e:
        print(f"Error in get_accounts_by_type: {e}")
        return []

def update_account_balance(account_code, amount, is_debit=True):
    """Update account balance with debit/credit logic"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        
        cursor.execute('SELECT account_type, balance FROM accounts WHERE account_code = ? AND is_active = 1', 
                      (account_code,))
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

# ============== VOUCHER FUNCTIONS ==============
def save_voucher(voucher_type, voucher_date, description, entries, username, status='POSTED'):
    """Save a new voucher and update account balances"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        
        voucher_number = generate_voucher_number(voucher_type)
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        total_amount = sum(entry['amount'] for entry in entries)
        
        cursor.execute('''
            INSERT INTO vouchers 
            (voucher_number, voucher_type, voucher_date, description, total_amount, status, created_date, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (voucher_number, voucher_type, voucher_date, description, total_amount, status, current_date, username))
        
        for entry in entries:
            cursor.execute('''
                INSERT INTO voucher_entries 
                (voucher_number, entry_type, account_code, account_name, amount, narration)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (voucher_number, entry['entry_type'], entry['account_code'], 
                  entry['account_name'], entry['amount'], entry.get('narration', '')))
        
        for entry in entries:
            if entry['entry_type'] == 'DEBIT':
                success, msg = update_account_balance(entry['account_code'], entry['amount'], is_debit=True)
            else:
                success, msg = update_account_balance(entry['account_code'], entry['amount'], is_debit=False)
            if not success:
                conn.close()
                return False, f"Error updating balance for {entry['account_name']}: {msg}"
        
        for entry in entries:
            cursor.execute('''
                INSERT INTO journal_entries 
                (date, account_code, account_name, entry_type, amount, description, ref_no, username, voucher_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (voucher_date, entry['account_code'], entry['account_name'], 
                  entry['entry_type'], entry['amount'], description, voucher_number, username, voucher_number))
        
        conn.commit()
        conn.close()
        return True, f"Voucher {voucher_number} saved successfully"
    except Exception as e:
        print(f"Error in save_voucher: {e}")
        return False, f"Error saving voucher: {str(e)}"

def get_all_vouchers(limit=100):
    """Get all vouchers"""
    try:
        conn = get_db_connection()
        if conn is None:
            return []
        cursor = conn.cursor()
        cursor.execute('''
            SELECT voucher_number, voucher_type, voucher_date, description, total_amount, status, created_date, created_by
            FROM vouchers
            ORDER BY created_date DESC
            LIMIT ?
        ''', (limit,))
        result = cursor.fetchall()
        conn.close()
        
        vouchers = []
        for row in result:
            vouchers.append({
                'voucher_number': row[0],
                'voucher_type': row[1],
                'voucher_date': row[2],
                'description': row[3],
                'total_amount': row[4],
                'status': row[5],
                'created_date': row[6],
                'created_by': row[7]
            })
        return vouchers
    except Exception as e:
        print(f"Error in get_all_vouchers: {e}")
        return []

def get_voucher(voucher_number):
    """Get voucher details"""
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        cursor = conn.cursor()
        cursor.execute('''
            SELECT voucher_number, voucher_type, voucher_date, description, total_amount, status
            FROM vouchers 
            WHERE voucher_number = ?
        ''', (voucher_number,))
        voucher = cursor.fetchone()
        
        if not voucher:
            conn.close()
            return None
        
        cursor.execute('''
            SELECT entry_type, account_code, account_name, amount, narration
            FROM voucher_entries 
            WHERE voucher_number = ?
            ORDER BY id
        ''', (voucher_number,))
        entries = cursor.fetchall()
        
        conn.close()
        
        return {
            'voucher_number': voucher[0],
            'voucher_type': voucher[1],
            'voucher_date': voucher[2],
            'description': voucher[3],
            'total_amount': voucher[4],
            'status': voucher[5],
            'entries': [
                {
                    'entry_type': e[0],
                    'account_code': e[1],
                    'account_name': e[2],
                    'amount': e[3],
                    'narration': e[4] if e[4] else ''
                }
                for e in entries
            ]
        }
    except Exception as e:
        print(f"Error in get_voucher: {e}")
        return None

def delete_voucher(voucher_number):
    """Delete a voucher and reverse balances"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM vouchers WHERE voucher_number = ?', (voucher_number,))
        if not cursor.fetchone():
            conn.close()
            return False, "Voucher not found"
        
        cursor.execute('SELECT entry_type, account_code, amount FROM voucher_entries WHERE voucher_number = ?', 
                      (voucher_number,))
        entries = cursor.fetchall()
        
        for entry in entries:
            if entry[0] == 'DEBIT':
                success, msg = update_account_balance(entry[1], entry[2], is_debit=False)
            else:
                success, msg = update_account_balance(entry[1], entry[2], is_debit=True)
            if not success:
                conn.close()
                return False, f"Error reversing entries: {msg}"
        
        cursor.execute('DELETE FROM voucher_entries WHERE voucher_number = ?', (voucher_number,))
        cursor.execute('DELETE FROM journal_entries WHERE voucher_number = ?', (voucher_number,))
        cursor.execute('DELETE FROM vouchers WHERE voucher_number = ?', (voucher_number,))
        
        conn.commit()
        conn.close()
        return True, f"Voucher {voucher_number} deleted successfully"
    except Exception as e:
        print(f"Error in delete_voucher: {e}")
        return False, f"Error deleting voucher: {str(e)}"

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
                interest_rate, interest_payable, account_status, opening_date, 
                last_interest_date, created_by,
                nominee_name, nominee_relation, aadhar_number, pan_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            0,  # interest_payable
            'ACTIVE',
            opening_date,
            opening_date,
            username,
            data.get('nominee_name', ''),
            data.get('nominee_relation', ''),
            data.get('aadhar_number', ''),
            data.get('pan_number', '')
        ))
        
        if data['opening_balance'] > 0:
            transaction_id = generate_transaction_id()
            cursor.execute('''
                INSERT INTO sb_transactions (
                    transaction_id, account_number, transaction_date, value_date,
                    particulars, credit, balance, transaction_type, created_by, created_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                transaction_id,
                account_number,
                opening_date,
                opening_date,
                'Opening Balance',
                data['opening_balance'],
                data['opening_balance'],
                'DEPOSIT',
                username,
                opening_date
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
                      'interest_rate', 'interest_payable', 'account_status', 'opening_date', 
                      'last_interest_date', 'last_interest_credited', 'created_by', 
                      'nominee_name', 'nominee_relation', 'aadhar_number', 'pan_number']
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
                   interest_payable, account_status, opening_date
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
                'interest_payable': float(row[7]) if row[7] is not None else 0,
                'account_status': row[8] if len(row) > 8 else 'ACTIVE',
                'opening_date': row[9] if len(row) > 9 else ''
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
            SELECT transaction_id, transaction_date, value_date, particulars, debit, credit, balance, 
                   transaction_type, ref_no, created_by, created_date
            FROM sb_transactions 
            WHERE account_number = ?
        '''
        params = [account_number]
        
        if from_date:
            query += ' AND value_date >= ?'
            params.append(from_date)
        if to_date:
            query += ' AND value_date <= ?'
            params.append(to_date)
        
        query += ' ORDER BY value_date DESC, created_date DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.close()
        
        transactions = []
        for row in result:
            transactions.append({
                'transaction_id': row[0],
                'transaction_date': row[1],
                'value_date': row[2] if len(row) > 2 else row[1],
                'particulars': row[3],
                'debit': row[4],
                'credit': row[5],
                'balance': row[6],
                'transaction_type': row[7],
                'ref_no': row[8],
                'created_by': row[9] if len(row) > 9 else '',
                'created_date': row[10] if len(row) > 10 else row[1]
            })
        return transactions
    except Exception as e:
        print(f"Error in get_sb_transactions: {e}")
        return []

def deposit_sb_account(account_number, amount, particulars, value_date, username):
    """Deposit money into SB account with date"""
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
        
        cursor.execute('UPDATE sb_accounts SET current_balance = ? WHERE account_number = ?', 
                      (new_balance, account_number))
        
        cursor.execute('''
            INSERT INTO sb_transactions (
                transaction_id, account_number, transaction_date, value_date,
                particulars, credit, balance, transaction_type, created_by, created_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            transaction_id,
            account_number,
            transaction_date,
            value_date,
            particulars,
            amount,
            new_balance,
            'DEPOSIT',
            username,
            transaction_date
        ))
        
        conn.commit()
        conn.close()
        return True, f"Deposited ₹{amount:,.2f} on {value_date}. New balance: ₹{new_balance:,.2f}"
    except Exception as e:
        print(f"Error in deposit_sb_account: {e}")
        return False, f"Error depositing: {str(e)}"

def withdraw_sb_account(account_number, amount, particulars, value_date, username):
    """Withdraw money from SB account with date"""
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
        
        cursor.execute('UPDATE sb_accounts SET current_balance = ? WHERE account_number = ?', 
                      (new_balance, account_number))
        
        cursor.execute('''
            INSERT INTO sb_transactions (
                transaction_id, account_number, transaction_date, value_date,
                particulars, debit, balance, transaction_type, created_by, created_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            transaction_id,
            account_number,
            transaction_date,
            value_date,
            particulars,
            amount,
            new_balance,
            'WITHDRAWAL',
            username,
            transaction_date
        ))
        
        conn.commit()
        conn.close()
        return True, f"Withdrawn ₹{amount:,.2f} on {value_date}. New balance: ₹{new_balance:,.2f}"
    except Exception as e:
        print(f"Error in withdraw_sb_account: {e}")
        return False, f"Error withdrawing: {str(e)}"

def calculate_and_credit_interest(account_number, username):
    """Calculate and credit quarterly interest for SB account with DOUBLE ENTRY"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
        
        # Get account details
        cursor.execute('''SELECT current_balance, interest_rate, interest_payable, account_number, customer_name 
                         FROM sb_accounts WHERE account_number = ?''', (account_number,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "Account not found"
        
        current_balance = result[0]
        interest_rate = result[1]
        interest_payable = result[2] if result[2] is not None else 0
        acc_number = result[3]
        customer_name = result[4]
        
        # Calculate quarterly interest (3 months = 90 days)
        interest = current_balance * (interest_rate / 100) * (90 / 365)
        
        if interest <= 0:
            conn.close()
            return False, "No interest to credit"
        
        # ============== PART 1: Update SB Account ==============
        new_balance = current_balance + interest
        new_interest_payable = interest_payable + interest
        
        cursor.execute('UPDATE sb_accounts SET current_balance = ?, interest_payable = ?, last_interest_credited = ? WHERE account_number = ?',
                      (new_balance, new_interest_payable, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), account_number))
        
        # Record SB transaction
        transaction_id = generate_transaction_id()
        transaction_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        value_date = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute('''
            INSERT INTO sb_transactions (
                transaction_id, account_number, transaction_date, value_date,
                particulars, credit, balance, transaction_type, created_by, created_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            transaction_id,
            account_number,
            transaction_date,
            value_date,
            f'Quarterly Interest @ {interest_rate}% (Payable)',
            interest,
            new_balance,
            'INTEREST',
            'SYSTEM',
            transaction_date
        ))
        
        # ============== PART 2: POST DOUBLE ENTRY TO MAIN SYSTEM ==============
        # DEBIT: SB Interest Expense (5999) - Expense increases
        # CREDIT: SB Interest Payable (2500) - Liability increases
        
        voucher_number = generate_voucher_number('INTEREST')
        
        # Debit entry - SB Interest Expense
        cursor.execute('''
            INSERT INTO journal_entries (
                date, account_code, account_name, entry_type, amount, 
                description, ref_no, username, voucher_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            value_date,
            '5999',
            'SB_INTEREST_EXPENSE',
            'DEBIT',
            interest,
            f'Quarterly Interest on SB Account {account_number} - {customer_name}',
            voucher_number,
            username,
            voucher_number
        ))
        
        # Credit entry - SB Interest Payable
        cursor.execute('''
            INSERT INTO journal_entries (
                date, account_code, account_name, entry_type, amount, 
                description, ref_no, username, voucher_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            value_date,
            '2500',
            'SB_INTEREST_PAYABLE',
            'CREDIT',
            interest,
            f'Quarterly Interest on SB Account {account_number} - {customer_name}',
            voucher_number,
            username,
            voucher_number
        ))
        
        # Update account balances in main accounts table
        # Update SB Interest Expense (DEBIT)
        cursor.execute('SELECT balance FROM accounts WHERE account_code = "5999"')
        exp_result = cursor.fetchone()
        exp_balance = exp_result[0] if exp_result else 0
        cursor.execute('UPDATE accounts SET balance = ? WHERE account_code = "5999"', (exp_balance + interest,))
        
        # Update SB Interest Payable (CREDIT)
        cursor.execute('SELECT balance FROM accounts WHERE account_code = "2500"')
        pay_result = cursor.fetchone()
        pay_balance = pay_result[0] if pay_result else 0
        cursor.execute('UPDATE accounts SET balance = ? WHERE account_code = "2500"', (pay_balance + interest,))
        
        # Record in interest history
        cursor.execute('''
            INSERT INTO sb_interest_history (
                account_number, quarter_start, quarter_end, interest_rate,
                average_balance, interest_amount, interest_payable, credited_date, voucher_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            account_number,
            datetime.now().replace(day=1).strftime('%Y-%m-%d'),
            datetime.now().strftime('%Y-%m-%d'),
            interest_rate,
            current_balance,
            interest,
            interest,
            transaction_date,
            voucher_number
        ))
        
        conn.commit()
        conn.close()
        return True, f"Interest ₹{interest:,.2f} credited to SB Account {account_number} at {interest_rate}%"
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
            SELECT quarter_start, quarter_end, interest_rate, average_balance, 
                   interest_amount, interest_payable, credited_date, voucher_number
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
                'interest_payable': float(row[5]) if row[5] is not None else 0,
                'credited_date': row[6] if len(row) > 6 else '',
                'voucher_number': row[7] if len(row) > 7 else ''
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
        
        total_debits = sum(t['debit'] for t in transactions)
        total_credits = sum(t['credit'] for t in transactions)
        
        report = {
            'account': account,
            'transactions': transactions,
            'summary': {
                'total_debits': total_debits,
                'total_credits': total_credits,
                'opening_balance': account['opening_balance'],
                'closing_balance': account['current_balance'],
                'interest_payable': float(account.get('interest_payable', 0)),
                'net_change': account['current_balance'] - account['opening_balance']
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

# ============== CUSTOMER FUNCTIONS ==============
def create_customer(data, username):
    """Create a new customer with KYC"""
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
            INSERT INTO customers 
            (customer_id, full_name, address, phone, whatsapp_number, email, id_type, id_number,
             aadhar_number, aadhar_image, pan_number, pan_image,
             date_of_birth, age,
             nominee_name, nominee_address, nominee_relation, nominee_dob, nominee_age,
             nominee_aadhar, nominee_aadhar_image, nominee_pan, nominee_pan_image,
             kyc_completed, created_date, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            customer_id,
            data['full_name'],
            data['address'],
            data['phone'],
            data['whatsapp_number'],
            data['email'],
            data['id_type'],
            data['id_number'],
            data['aadhar_number'],
            data['aadhar_image'],
            data['pan_number'],
            data['pan_image'],
            data['date_of_birth'],
            data['age'],
            data['nominee_name'],
            data['nominee_address'],
            data['nominee_relation'],
            data['nominee_dob'],
            data['nominee_age'],
            data['nominee_aadhar'],
            data['nominee_aadhar_image'],
            data['nominee_pan'],
            data['nominee_pan_image'],
            1,
            date,
            username
        ))
        
        for acc_code in ['1100', '1200', '1300']:
            cursor.execute('''
                INSERT INTO customer_accounts (customer_id, account_code, balance)
                VALUES (?, ?, ?)
            ''', (customer_id, acc_code, 0))
        
        conn.commit()
        conn.close()
        return True, f"Customer {data['full_name']} created with ID: {customer_id}"
    except Exception as e:
        print(f"Error in create_customer: {e}")
        return False, f"Error creating customer: {str(e)}"

def get_all_customers():
    """Get all customers"""
    try:
        conn = get_db_connection()
        if conn is None:
            return {}
        cursor = conn.cursor()
        cursor.execute('''
            SELECT customer_id, full_name, address, phone, whatsapp_number, email, 
                   id_type, id_number, aadhar_number, pan_number, date_of_birth, age,
                   nominee_name, nominee_address, nominee_relation, nominee_dob, nominee_age,
                   created_date
            FROM customers
            WHERE kyc_completed = 1
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
                'whatsapp_number': row[4],
                'email': row[5],
                'id_type': row[6],
                'id_number': row[7],
                'aadhar_number': row[8],
                'pan_number': row[9],
                'date_of_birth': row[10],
                'age': row[11],
                'nominee_name': row[12],
                'nominee_address': row[13],
                'nominee_relation': row[14],
                'nominee_dob': row[15],
                'nominee_age': row[16],
                'created_date': row[17]
            }
        return customers
    except Exception as e:
        print(f"Error in get_all_customers: {e}")
        return {}

def get_customer_details(customer_id):
    """Get customer details including images"""
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
                      'nominee_aadhar', 'nominee_aadhar_image', 'nominee_pan', 'nominee_pan_image',
                      'kyc_completed', 'created_date', 'created_by']
            return dict(zip(columns, result))
        return None
    except Exception as e:
        print(f"Error in get_customer_details: {e}")
        return None

def get_customer_balances(customer_id):
    """Get customer's account balances"""
    try:
        conn = get_db_connection()
        if conn is None:
            return {}
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
    except Exception as e:
        print(f"Error in get_customer_balances: {e}")
        return {}

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

# ============== UI FUNCTIONS ==============
def display_account_card(acc_code, icon, color):
    """Display an account card"""
    try:
        accounts = get_all_accounts()
        if acc_code not in accounts:
            return
        
        data = accounts[acc_code]
        balance = data.get('balance', 0)
        acc_name = data.get('account_name', 'Unknown')
        acc_type = data.get('account_type', 'Unknown')
        
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
    except Exception as e:
        print(f"Error in display_account_card for {acc_code}: {e}")

def render_journal_voucher_form():
    """Render journal voucher entry form"""
    st.subheader("📝 Create Journal Voucher")
    
    all_accounts = get_all_accounts()
    
    account_options = []
    account_code_map = {}
    
    # Group accounts by type
    account_types = {
        'ASSET': '💰 Assets',
        'LIABILITY': '🏛️ Liabilities', 
        'EQUITY': '📈 Equity',
        'INCOME': '📊 Income',
        'EXPENSE': '📉 Expenses'
    }
    
    grouped_options = {key: [] for key in account_types.keys()}
    
    for code, data in all_accounts.items():
        acc_type = data['account_type']
        display_text = f"{data['account_name']} ({code})"
        grouped_options[acc_type].append(display_text)
        account_code_map[display_text] = code
    
    for acc_type, header in account_types.items():
        if grouped_options[acc_type]:
            account_options.append(f"--- {header} ---")
            account_options.extend(grouped_options[acc_type])
    
    if not account_options:
        st.warning("No accounts found. Please create accounts first.")
        return None
    
    with st.form("journal_voucher_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            voucher_date = st.date_input("Voucher Date", value=datetime.now().date())
        with col2:
            st.text_input("Voucher Number", value="Auto-generated", disabled=True)
        with col3:
            voucher_type = st.selectbox("Voucher Type", ['JOURNAL', 'RECEIPT', 'PAYMENT', 'CONTRA'])
        
        description = st.text_area("Description", placeholder="Enter voucher description")
        
        st.markdown("---")
        st.markdown("### Voucher Entries")
        st.info("💡 For each entry: Select DEBIT or CREDIT, choose an account, and enter amount")
        
        entries = []
        num_entries = st.number_input("Number of entries", min_value=2, max_value=10, value=2, step=1)
        
        for i in range(num_entries):
            st.markdown(f"**Entry {i+1}**")
            col1, col2, col3, col4 = st.columns([1, 2, 1.5, 1.5])
            
            with col1:
                entry_type = st.selectbox(f"Type", ['DEBIT', 'CREDIT'], key=f"type_{i}")
            
            with col2:
                account_display = st.selectbox(f"Account", account_options, key=f"acc_{i}")
                if account_display.startswith('---'):
                    acc_code = ''
                    acc_name = ''
                else:
                    acc_code = account_code_map.get(account_display, '')
                    acc_name = account_display.split('(')[0].strip() if account_display else ''
            
            with col3:
                amount = st.number_input(f"Amount", min_value=0.0, step=100.0, key=f"amt_{i}")
            
            with col4:
                narration = st.text_input(f"Narration", key=f"nar_{i}", placeholder="Optional")
            
            if account_display and not account_display.startswith('---') and amount > 0 and acc_code:
                entries.append({
                    'entry_type': entry_type,
                    'account_code': acc_code,
                    'account_name': acc_name,
                    'amount': amount,
                    'narration': narration
                })
        
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
        
        submitted = st.form_submit_button("💾 Save Voucher", type="primary")
        
        if submitted:
            if len(entries) == 0:
                st.error("Please enter at least one valid entry")
                return None
            
            if total_debits == 0 and total_credits == 0:
                st.error("Please enter amounts greater than zero")
                return None
            
            if abs(diff) > 0.01:
                st.error("Total Debits must equal Total Credits")
                return None
            
            return {
                'voucher_type': voucher_type,
                'voucher_date': voucher_date.strftime('%Y-%m-%d'),
                'description': description,
                'entries': entries
            }
    
    return None

def render_voucher_list():
    """Render list of vouchers"""
    st.subheader("📋 Voucher List")
    
    col1, col2 = st.columns(2)
    with col1:
        filter_type = st.selectbox("Filter by Type", ['ALL', 'JOURNAL', 'RECEIPT', 'PAYMENT', 'CONTRA', 'INTEREST'])
    
    with col2:
        if st.button("🔄 Refresh List"):
            st.rerun()
    
    if filter_type == 'ALL':
        vouchers = get_all_vouchers(limit=200)
    else:
        vouchers = get_vouchers_by_type(filter_type)
    
    if not vouchers:
        st.info("No vouchers found")
        return None
    
    voucher_data = []
    for v in vouchers:
        voucher_data.append({
            'Voucher No': v['voucher_number'],
            'Type': v['voucher_type'],
            'Date': v['voucher_date'],
            'Description': v['description'][:50] + '...' if len(v['description']) > 50 else v['description'],
            'Amount': f"₹{v['total_amount']:,.2f}",
            'Status': v['status'],
            'Created': v['created_date'][:16],
            'By': v['created_by']
        })
    
    df = pd.DataFrame(voucher_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    selected_voucher = st.selectbox("Select Voucher to View/Edit/Delete", 
                                   [""] + [v['voucher_number'] for v in vouchers])
    
    if selected_voucher:
        return selected_voucher
    
    return None

def get_vouchers_by_type(voucher_type):
    """Get vouchers by type"""
    try:
        conn = get_db_connection()
        if conn is None:
            return []
        cursor = conn.cursor()
        cursor.execute('''
            SELECT voucher_number, voucher_type, voucher_date, description, total_amount, status, created_date, created_by
            FROM vouchers
            WHERE voucher_type = ?
            ORDER BY created_date DESC
        ''', (voucher_type,))
        result = cursor.fetchall()
        conn.close()
        
        vouchers = []
        for row in result:
            vouchers.append({
                'voucher_number': row[0],
                'voucher_type': row[1],
                'voucher_date': row[2],
                'description': row[3],
                'total_amount': row[4],
                'status': row[5],
                'created_date': row[6],
                'created_by': row[7]
            })
        return vouchers
    except Exception as e:
        print(f"Error in get_vouchers_by_type: {e}")
        return []

def render_sb_account_creation():
    """Render SB Account creation form"""
    st.subheader("🏦 Create Savings Bank Account")
    
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
    st.subheader("💰 Savings Bank Account Operations")
    
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
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("💰 Current Balance", f"₹{account['current_balance']:,.2f}")
            
            with col2:
                st.metric("📊 Interest Rate", f"{account['interest_rate']}%")
            
            with col3:
                st.metric("📋 Interest Payable", f"₹{float(account.get('interest_payable', 0)):,.2f}")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### 💵 Deposit")
                deposit_date = st.date_input("Deposit Date", value=datetime.now().date(), key="deposit_date")
                deposit_amount = st.number_input("Amount", min_value=0.0, step=100.0, key="deposit_amt")
                deposit_particulars = st.text_input("Particulars", key="deposit_particulars", placeholder="e.g., Cash deposit")
                
                if st.button("💰 Deposit", key="deposit_btn"):
                    if deposit_amount > 0:
                        success, msg = deposit_sb_account(
                            account_number, 
                            deposit_amount, 
                            deposit_particulars, 
                            deposit_date.strftime('%Y-%m-%d'),
                            st.session_state.user['username']
                        )
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("Enter amount greater than zero")
            
            with col2:
                st.markdown("### 💸 Withdraw")
                withdraw_date = st.date_input("Withdrawal Date", value=datetime.now().date(), key="withdraw_date")
                withdraw_amount = st.number_input("Amount", min_value=0.0, step=100.0, key="withdraw_amt")
                withdraw_particulars = st.text_input("Particulars", key="withdraw_particulars", placeholder="e.g., ATM withdrawal")
                
                if st.button("💸 Withdraw", key="withdraw_btn"):
                    if withdraw_amount > 0:
                        success, msg = withdraw_sb_account(
                            account_number, 
                            withdraw_amount, 
                            withdraw_particulars, 
                            withdraw_date.strftime('%Y-%m-%d'),
                            st.session_state.user['username']
                        )
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
                st.info(f"💰 Interest Payable: ₹{float(account.get('interest_payable', 0)):,.2f}")
                
                # Calculate estimated interest
                estimated_interest = account['current_balance'] * (account['interest_rate'] / 100) * (90 / 365)
                st.caption(f"Estimated Quarterly Interest: ₹{estimated_interest:,.2f}")
                
                if st.button("🧮 Calculate & Credit Interest", key="interest_btn"):
                    # Show confirmation
                    st.warning(f"⚠️ This will credit interest of approximately ₹{estimated_interest:,.2f} at {account['interest_rate']}%")
                    st.caption("📝 Journal Entry: Dr SB Interest Expense / Cr SB Interest Payable")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Yes, Credit Interest", key="confirm_interest"):
                            success, msg = calculate_and_credit_interest(account_number, st.session_state.user['username'])
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    with col2:
                        if st.button("❌ Cancel"):
                            st.rerun()

def render_sb_account_report():
    """Render SB Account report"""
    st.subheader("📊 Savings Bank Account Report")
    
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
                    st.metric("Interest Payable", f"₹{float(summary.get('interest_payable', 0)):,.2f}")
                
                st.markdown("### 📝 Transaction Details")
                if transactions:
                    txn_data = []
                    for t in transactions:
                        txn_data.append({
                            'Transaction Date': t['transaction_date'],
                            'Value Date': t['value_date'],
                            'Particulars': t['particulars'],
                            'Debit': f"₹{t['debit']:,.2f}" if t['debit'] > 0 else '-',
                            'Credit': f"₹{t['credit']:,.2f}" if t['credit'] > 0 else '-',
                            'Balance': f"₹{t['balance']:,.2f}",
                            'Type': t['transaction_type']
                        })
                    df = pd.DataFrame(txn_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"SB_Account_{account_number}_{from_date.strftime('%Y%m%d')}_{to_date.strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No transactions for the selected period")
                
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
                            'Payable': f"₹{float(ih.get('interest_payable', 0)):,.2f}",
                            'Voucher No': ih.get('voucher_number', 'N/A'),
                            'Credited Date': ih['credited_date']
                        })
                    df_interest = pd.DataFrame(interest_data)
                    st.dataframe(df_interest, use_container_width=True, hide_index=True)
                else:
                    st.info("No interest history available")

def render_sb_account_list():
    """Render SB Account list"""
    st.subheader("📋 Savings Bank Account List")
    
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
            'Interest Payable': f"₹{float(acc.get('interest_payable', 0)):,.2f}",
            'Status': acc['account_status'],
            'Opening Date': acc['opening_date']
        })
    
    df = pd.DataFrame(account_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

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

def render_customer_management():
    """Render customer management section"""
    st.subheader("👥 Customer Management")
    
    customers = get_all_customers()
    
    if not customers:
        st.info("No customers registered yet.")
        return
    
    cust_data = []
    for cid, cust in customers.items():
        balances = get_customer_balances(cid)
        cust_data.append({
            'ID': cid,
            'Name': cust['full_name'],
            'Phone': cust['phone'],
            'WhatsApp': cust.get('whatsapp_number', ''),
            'Email': cust['email'],
            'Aadhaar': cust.get('aadhar_number', ''),
            'PAN': cust.get('pan_number', ''),
            'Age': cust.get('age', ''),
            'Savings': f"₹{balances.get('1100', 0):,.2f}",
            'Current': f"₹{balances.get('1200', 0):,.2f}",
            'FD': f"₹{balances.get('1300', 0):,.2f}"
        })
    
    df = pd.DataFrame(cust_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

def render_head_management():
    """Render head management section"""
    st.subheader("⚙️ Expense & Income Head Management")
    
    expense_accounts = get_accounts_by_type('EXPENSE')
    income_accounts = get_accounts_by_type('INCOME')
    
    st.markdown("### 📊 Current Heads")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📉 Expense Heads")
        if expense_accounts:
            expense_data = []
            for acc in expense_accounts:
                expense_data.append({
                    'Code': acc['account_code'],
                    'Name': acc['account_name'],
                    'Balance': f"₹{acc['balance']:,.2f}",
                    'Daily Limit': f"₹{acc['daily_limit']:,.2f}" if acc['daily_limit'] else 'N/A'
                })
            df_expense = pd.DataFrame(expense_data)
            st.dataframe(df_expense, use_container_width=True, hide_index=True)
        else:
            st.info("No expense heads found")
    
    with col2:
        st.markdown("#### 📊 Income Heads")
        if income_accounts:
            income_data = []
            for acc in income_accounts:
                income_data.append({
                    'Code': acc['account_code'],
                    'Name': acc['account_name'],
                    'Balance': f"₹{acc['balance']:,.2f}"
                })
            df_income = pd.DataFrame(income_data)
            st.dataframe(df_income, use_container_width=True, hide_index=True)
        else:
            st.info("No income heads found")
    
    st.divider()
    st.markdown("### ➕ Create New Head")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.form("create_head_form"):
            st.markdown("**Create Expense Head**")
            expense_name = st.text_input("Expense Head Name", placeholder="e.g., CONVEYANCE_EXPENSE")
            expense_limit = st.number_input("Daily Limit (Optional)", min_value=0.0, step=1000.0, value=0.0)
            expense_initial = st.number_input("Initial Balance", min_value=0.0, step=100.0, value=0.0)
            
            if st.form_submit_button("Create Expense Head"):
                if expense_name:
                    limit_value = expense_limit if expense_limit > 0 else None
                    success, msg = create_account(
                        expense_name.upper(),
                        'EXPENSE',
                        expense_initial,
                        limit_value,
                        None,
                        st.session_state.user['username']
                    )
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Please enter a head name")
    
    with col2:
        with st.form("create_income_form"):
            st.markdown("**Create Income Head**")
            income_name = st.text_input("Income Head Name", placeholder="e.g., CONSULTING_INCOME")
            income_initial = st.number_input("Initial Balance", min_value=0.0, step=100.0, value=0.0)
            
            if st.form_submit_button("Create Income Head"):
                if income_name:
                    success, msg = create_account(
                        income_name.upper(),
                        'INCOME',
                        income_initial,
                        None,
                        None,
                        st.session_state.user['username']
                    )
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Please enter a head name")
    
    st.divider()
    st.markdown("### ✏️ Edit/Delete Head")
    
    all_heads = get_accounts_by_type('EXPENSE') + get_accounts_by_type('INCOME')
    
    if all_heads:
        head_options = [f"{acc['account_name']} ({acc['account_code']}) - {acc['account_type']}" 
                       for acc in all_heads]
        selected_head = st.selectbox("Select Head to Manage", head_options)
        
        if selected_head:
            acc_code = selected_head.split('(')[1].split(')')[0]
            head_data = next((acc for acc in all_heads if acc['account_code'] == acc_code), None)
            
            if head_data:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Edit Head**")
                    with st.form("edit_head_form"):
                        new_name = st.text_input("New Name", value=head_data['account_name'])
                        new_limit = st.number_input("Daily Limit", 
                                                   value=head_data.get('daily_limit') or 0.0,
                                                   step=1000.0)
                        
                        if st.form_submit_button("Update Head"):
                            if new_name:
                                limit_value = new_limit if new_limit > 0 else None
                                success, msg = update_account(acc_code, new_name, limit_value, None)
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                            else:
                                st.warning("Name cannot be empty")
                
                with col2:
                    st.markdown("**Delete Head**")
                    st.warning(f"⚠️ You are about to delete '{head_data['account_name']}'")
                    
                    if head_data.get('balance', 0) > 0:
                        st.info(f"This account has balance of ₹{head_data['balance']:,.2f}. It will be marked as inactive.")
                    else:
                        st.info("This account has zero balance. It will be permanently deleted.")
                    
                    if st.button("🗑️ Delete Head", type="primary"):
                        success, msg = delete_account(acc_code)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

# ============== LOGIN PAGE ==============
def login_page():
    """Display login page"""
    st.title("🏦 Complete Banking System")
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
            init_database()
            migrate_database()
        
        if 'logged_in' not in st.session_state or not st.session_state.logged_in:
            login_page()
            return
        
        user = st.session_state.user
        
        # Initialize session state variables
        if 'edit_mode' not in st.session_state:
            st.session_state.edit_mode = False
        if 'edit_customer_id' not in st.session_state:
            st.session_state.edit_customer_id = None
        if 'show_delete_confirmation' not in st.session_state:
            st.session_state.show_delete_confirmation = False
        if 'delete_customer_id' not in st.session_state:
            st.session_state.delete_customer_id = None
        
        # Header
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
        
        # Sidebar
        with st.sidebar:
            st.header("📊 Account Overview")
            
            try:
                st.subheader("💰 Cash & Bank")
                display_account_card('1000', '💵', '#00A86B')
                display_account_card('1001', '💵', '#00A86B')  # Petty Cash
                display_account_card('1100', '🏦', '#2E86AB')
                display_account_card('1200', '🏦', '#1B4F72')
                
                st.divider()
                
                with st.expander("🏦 Other ASSETS", expanded=True):
                    for code in ['1300', '1400', '1500', '1600', '1700']:
                        display_account_card(code, '💰', '#2E86AB')
                
                with st.expander("🏛️ LIABILITIES", expanded=True):
                    for code in ['2100', '2200', '2300', '2400', '2500']:
                        display_account_card(code, '🏛️', '#A23B72')
                
                with st.expander("📈 EQUITY", expanded=True):
                    for code in ['3100', '3200']:
                        display_account_card(code, '📈', '#F18F01')
                
                with st.expander("📊 INCOME", expanded=True):
                    income_accounts = get_accounts_by_type('INCOME')
                    for acc in income_accounts:
                        display_account_card(acc['account_code'], '📊', '#1B998B')
                
                with st.expander("📉 EXPENSES", expanded=True):
                    expense_accounts = get_accounts_by_type('EXPENSE')
                    for acc in expense_accounts:
                        display_account_card(acc['account_code'], '📉', '#D65D5D')
                
                st.divider()
                
                accounts = get_all_accounts()
                if accounts:
                    total_assets = sum(data.get('balance', 0) for code, data in accounts.items() if data.get('account_type') == 'ASSET')
                    total_liabilities = sum(data.get('balance', 0) for code, data in accounts.items() if data.get('account_type') == 'LIABILITY')
                    total_equity = sum(data.get('balance', 0) for code, data in accounts.items() if data.get('account_type') == 'EQUITY')
                    
                    st.metric("Total Assets", f"₹{total_assets:,.2f}")
                    st.metric("Total Liabilities", f"₹{total_liabilities:,.2f}")
                    st.metric("Total Equity", f"₹{total_equity:,.2f}")
            except Exception as e:
                st.error(f"Error loading sidebar: {str(e)}")
        
        # Main Tabs
        tabs = ["📝 Journal Vouchers", "💰 Cash & Bank", "👥 Customers & KYC", 
                "🏦 SB Accounts", "📊 Financial Reports", "📋 Trial Balance", "⚙️ Head Management"]
        
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(tabs)
        
        # ---------- TAB 1: JOURNAL VOUCHERS ----------
        with tab1:
            st.header("📝 Voucher Management")
            
            voucher_tab1, voucher_tab2 = st.tabs(["➕ Create Voucher", "📋 View/Edit/Delete Vouchers"])
            
            with voucher_tab1:
                result = render_journal_voucher_form()
                if result:
                    success, msg = save_voucher(
                        result['voucher_type'],
                        result['voucher_date'],
                        result['description'],
                        result['entries'],
                        user['username']
                    )
                    if success:
                        st.success(msg)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(msg)
            
            with voucher_tab2:
                selected_voucher = render_voucher_list()
                
                if selected_voucher:
                    voucher_data = get_voucher(selected_voucher)
                    if voucher_data:
                        st.divider()
                        st.subheader(f"✏️ Managing Voucher: {selected_voucher}")
                        
                        with st.expander("📄 Voucher Details", expanded=True):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Voucher Number", voucher_data['voucher_number'])
                            with col2:
                                st.metric("Type", voucher_data['voucher_type'])
                            with col3:
                                st.metric("Status", voucher_data['status'])
                            
                            st.caption(f"Date: {voucher_data['voucher_date']}")
                            st.caption(f"Description: {voucher_data['description']}")
                        
                        st.markdown("**Voucher Entries**")
                        entries_data = []
                        for entry in voucher_data['entries']:
                            entries_data.append({
                                'Type': entry['entry_type'],
                                'Account Code': entry['account_code'],
                                'Account Name': entry['account_name'],
                                'Amount': f"₹{entry['amount']:,.2f}",
                                'Narration': entry['narration']
                            })
                        df_entries = pd.DataFrame(entries_data)
                        st.dataframe(df_entries, use_container_width=True, hide_index=True)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✏️ Edit This Voucher", type="primary"):
                                st.info("Edit functionality coming soon")
                        
                        with col2:
                            if st.button("🗑️ Delete This Voucher", type="secondary"):
                                st.warning(f"⚠️ Are you sure you want to delete voucher {selected_voucher}?")
                                if st.button("✅ Yes, Delete Voucher", type="primary"):
                                    success, msg = delete_voucher(selected_voucher)
                                    if success:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
        
        # ---------- TAB 2: CASH & BANK ----------
        with tab2:
            st.header("💰 Cash & Bank Transactions")
            
            col1, col2 = st.columns(2)
            cash_balance = get_account_balance('1000')
            petty_cash = get_account_balance('1001')
            bank_savings = get_account_balance('1100')
            bank_current = get_account_balance('1200')
            
            with col1:
                st.metric("💵 Cash Balance", f"₹{cash_balance:,.2f}")
                st.metric("💵 Petty Cash", f"₹{petty_cash:,.2f}")
            with col2:
                st.metric("🏦 Bank Savings", f"₹{bank_savings:,.2f}")
                st.metric("🏦 Bank Current", f"₹{bank_current:,.2f}")
            
            st.info("💡 Use Journal Vouchers tab to create Cash/Bank entries with proper voucher numbers")
        
        # ---------- TAB 3: CUSTOMERS & KYC ----------
        with tab3:
            st.header("👥 Customer Management with KYC")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("➕ Register New Customer")
                
                with st.form("customer_form"):
                    st.markdown("### 📋 Personal Details")
                    
                    full_name = st.text_input("Full Name*")
                    
                    min_date = datetime(1900, 1, 1).date()
                    max_date = datetime.now().date()
                    
                    date_of_birth = st.date_input(
                        "Date of Birth*", 
                        value=None,
                        min_value=min_date,
                        max_value=max_date,
                        help="Select date of birth (1900 to present)"
                    )
                    
                    age = None
                    if date_of_birth:
                        today = datetime.now().date()
                        age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
                        st.success(f"🎂 Age: {age} years")
                    
                    address = st.text_area("Address*")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        phone = st.text_input("Phone Number*")
                        email = st.text_input("Email*")
                    with col_b:
                        whatsapp_number = st.text_input("WhatsApp Number")
                    
                    st.markdown("### 🪪 KYC Documents")
                    st.markdown("**Aadhaar Details (Compulsory)**")
                    col_c, col_d = st.columns(2)
                    with col_c:
                        aadhar_number = st.text_input("Aadhaar Number (12 digits)*")
                        if aadhar_number and not validate_aadhar(aadhar_number):
                            st.error("❌ Invalid Aadhaar number. Must be 12 digits.")
                    with col_d:
                        aadhar_image = st.file_uploader("Upload Aadhaar Card Image*", type=['jpg', 'jpeg', 'png', 'pdf'], key="aadhar_upload")
                    
                    st.markdown("**PAN Card Details (Compulsory)**")
                    col_e, col_f = st.columns(2)
                    with col_e:
                        pan_number = st.text_input("PAN Number (e.g., ABCDE1234F)*")
                        if pan_number and not validate_pan(pan_number):
                            st.error("❌ Invalid PAN number. Format: ABCDE1234F")
                    with col_f:
                        pan_image = st.file_uploader("Upload PAN Card Image*", type=['jpg', 'jpeg', 'png', 'pdf'], key="pan_upload")
                    
                    st.markdown("### 👤 Nominee Details")
                    col_g, col_h = st.columns(2)
                    with col_g:
                        nominee_name = st.text_input("Nominee Full Name")
                        nominee_dob = st.date_input(
                            "Nominee Date of Birth", 
                            value=None,
                            min_value=min_date,
                            max_value=max_date,
                            help="Select nominee's date of birth (1900 to present)"
                        )
                        if nominee_dob:
                            today = datetime.now().date()
                            nominee_age = today.year - nominee_dob.year - ((today.month, today.day) < (nominee_dob.month, nominee_dob.day))
                            st.caption(f"🎂 Nominee Age: {nominee_age} years")
                        nominee_relation = st.text_input("Nominee Relation (e.g., Spouse, Son, Daughter)")
                    with col_h:
                        nominee_address = st.text_area("Nominee Address")
                    
                    st.markdown("**Nominee Aadhaar Details (Optional)**")
                    col_i, col_j = st.columns(2)
                    with col_i:
                        nominee_aadhar = st.text_input("Nominee Aadhaar Number")
                        if nominee_aadhar and not validate_aadhar(nominee_aadhar):
                            st.error("❌ Invalid Aadhaar number. Must be 12 digits.")
                    with col_j:
                        nominee_aadhar_image = st.file_uploader("Upload Nominee Aadhaar Image", type=['jpg', 'jpeg', 'png', 'pdf'], key="nom_aadhar_upload")
                    
                    st.markdown("**Nominee PAN Details (Optional)**")
                    col_k, col_l = st.columns(2)
                    with col_k:
                        nominee_pan = st.text_input("Nominee PAN Number")
                        if nominee_pan and not validate_pan(nominee_pan):
                            st.error("❌ Invalid PAN number. Format: ABCDE1234F")
                    with col_l:
                        nominee_pan_image = st.file_uploader("Upload Nominee PAN Image", type=['jpg', 'jpeg', 'png', 'pdf'], key="nom_pan_upload")
                    
                    st.markdown("### 📝 Additional Information")
                    id_type = st.selectbox("ID Type*", ["Aadhaar", "PAN", "Passport", "Driving License", "Voter ID"])
                    id_number = st.text_input("ID Number*")
                    
                    submitted = st.form_submit_button("✅ Register Customer")
                    
                    if submitted:
                        errors = []
                        if not full_name:
                            errors.append("Full Name is required")
                        if not date_of_birth:
                            errors.append("Date of Birth is required")
                        if not address:
                            errors.append("Address is required")
                        if not phone:
                            errors.append("Phone Number is required")
                        if not email:
                            errors.append("Email is required")
                        if not aadhar_number:
                            errors.append("Aadhar Number is required")
                        elif not validate_aadhar(aadhar_number):
                            errors.append("Invalid Aadhaar number (must be 12 digits)")
                        if not pan_number:
                            errors.append("PAN Number is required")
                        elif not validate_pan(pan_number):
                            errors.append("Invalid PAN number (format: ABCDE1234F)")
                        if not aadhar_image:
                            errors.append("Aadhaar Card image is required")
                        if not pan_image:
                            errors.append("PAN Card image is required")
                        if not id_type:
                            errors.append("ID Type is required")
                        if not id_number:
                            errors.append("ID Number is required")
                        
                        if errors:
                            for error in errors:
                                st.error(error)
                        else:
                            aadhar_image_b64 = image_to_base64(aadhar_image)
                            pan_image_b64 = image_to_base64(pan_image)
                            nominee_aadhar_image_b64 = image_to_base64(nominee_aadhar_image) if nominee_aadhar_image else None
                            nominee_pan_image_b64 = image_to_base64(nominee_pan_image) if nominee_pan_image else None
                            
                            customer_data = {
                                'full_name': full_name,
                                'address': address,
                                'phone': phone,
                                'whatsapp_number': whatsapp_number,
                                'email': email,
                                'id_type': id_type,
                                'id_number': id_number,
                                'aadhar_number': aadhar_number,
                                'aadhar_image': aadhar_image_b64,
                                'pan_number': pan_number,
                                'pan_image': pan_image_b64,
                                'date_of_birth': date_of_birth.strftime('%Y-%m-%d') if date_of_birth else None,
                                'age': age,
                                'nominee_name': nominee_name,
                                'nominee_address': nominee_address,
                                'nominee_relation': nominee_relation,
                                'nominee_dob': nominee_dob.strftime('%Y-%m-%d') if nominee_dob else None,
                                'nominee_age': calculate_age_from_date(nominee_dob) if nominee_dob else None,
                                'nominee_aadhar': nominee_aadhar,
                                'nominee_aadhar_image': nominee_aadhar_image_b64,
                                'nominee_pan': nominee_pan,
                                'nominee_pan_image': nominee_pan_image_b64
                            }
                            
                            success, msg = create_customer(customer_data, user['username'])
                            if success:
                                st.success(msg)
                                st.balloons()
                                st.rerun()
                            else:
                                st.error(msg)
            
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
                            'WhatsApp': cust.get('whatsapp_number', ''),
                            'Email': cust['email'],
                            'Aadhaar': cust.get('aadhar_number', ''),
                            'PAN': cust.get('pan_number', ''),
                            'Age': cust.get('age', ''),
                            'Savings': f"₹{balances.get('1100', 0):,.2f}",
                            'Current': f"₹{balances.get('1200', 0):,.2f}",
                            'FD': f"₹{balances.get('1300', 0):,.2f}"
                        })
                    df = pd.DataFrame(cust_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("No customers registered yet.")
        
        # ---------- TAB 4: SB ACCOUNTS ----------
        with tab4:
            st.header("🏦 Savings Bank Accounts")
            
            sb_tab1, sb_tab2, sb_tab3, sb_tab4 = st.tabs(["📋 KYC Registration", "🏦 Create SB Account", "💰 Account Operations", "📊 Reports"])
            
            with sb_tab1:
                render_kyc_form()
            
            with sb_tab2:
                render_sb_account_creation()
            
            with sb_tab3:
                render_sb_account_operations()
            
            with sb_tab4:
                render_sb_account_report()
        
        # ---------- TAB 5: FINANCIAL REPORTS ----------
        with tab5:
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
                    if pl['income']:
                        for acc, bal in pl['income'].items():
                            st.metric(acc.replace('_', ' ').title(), f"₹{bal:,.2f}")
                        st.markdown(f"### **Total Income: ₹{pl['total_income']:,.2f}**")
                    else:
                        st.info("No income accounts found")
                
                with col2:
                    st.markdown("### EXPENSES")
                    if pl['expenses']:
                        for acc, bal in pl['expenses'].items():
                            st.metric(acc.replace('_', ' ').title(), f"₹{bal:,.2f}")
                        st.markdown(f"### **Total Expenses: ₹{pl['total_expenses']:,.2f}**")
                    else:
                        st.info("No expense accounts found")
                
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
        
        # ---------- TAB 6: TRIAL BALANCE ----------
        with tab6:
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
        
        # ---------- TAB 7: HEAD MANAGEMENT ----------
        with tab7:
            render_head_management()
    
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        print(f"Error in main: {e}")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
