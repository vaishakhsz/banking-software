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

# ============== DATABASE SETUP ==============
DB_FILE = "banking_system.db"

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn

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
        
        # Check if default accounts exist
        cursor.execute("SELECT COUNT(*) FROM accounts")
        count = cursor.fetchone()[0]
        
        if count == 0:
            current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            default_accounts = [
                ('1000', 'CASH', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
                ('1100', 'BANK_SAVINGS', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
                ('1200', 'BANK_CURRENT', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
                ('1300', 'FD', 'ASSET', 0, None, None, 7.0, current_date, 1, 'system'),
                ('1400', 'DAILY_COLLECTION', 'ASSET', 0, 50000, None, None, current_date, 1, 'system'),
                ('2100', 'CUSTOMER_DEPOSITS', 'LIABILITY', 0, None, None, None, current_date, 1, 'system'),
                ('2200', 'FD_LIABILITY', 'LIABILITY', 0, None, None, None, current_date, 1, 'system'),
                ('3100', 'CAPITAL', 'EQUITY', 1000000, None, None, None, current_date, 1, 'system'),
                ('3200', 'RETAINED_EARNINGS', 'EQUITY', 0, None, None, None, current_date, 1, 'system'),
                ('4100', 'INTEREST_INCOME', 'INCOME', 0, None, None, None, current_date, 1, 'system'),
                ('4200', 'SERVICE_CHARGE', 'INCOME', 0, None, None, None, current_date, 1, 'system'),
                ('5100', 'GENERAL_EXPENSE', 'EXPENSE', 0, None, None, None, current_date, 1, 'system'),
                ('5200', 'SALARY_EXPENSE', 'EXPENSE', 0, None, None, None, current_date, 1, 'system'),
                ('5300', 'RENT_EXPENSE', 'EXPENSE', 0, None, None, None, current_date, 1, 'system'),
                ('5400', 'UTILITY_EXPENSE', 'EXPENSE', 0, None, None, None, current_date, 1, 'system'),
            ]
            
            for acc in default_accounts:
                cursor.execute('''
                    INSERT INTO accounts 
                    (account_code, account_name, account_type, balance, daily_limit, maturity_date, interest_rate, created_date, is_active, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', acc)
        
        conn.commit()
        conn.close()
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
        conn.close()
        
        if user:
            # Update last login
            conn = get_db_connection()
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
                'last_login': user[6] if len(user) > 6 else None
            }
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

# ============== CUSTOMER FUNCTIONS ==============
def create_customer(data, username):
    """Create a new customer with KYC"""
    try:
        conn = get_db_connection()
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
        
        # Create customer account mappings
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
        cursor = conn.cursor()
        cursor.execute('''
            SELECT customer_id, full_name, address, phone, whatsapp_number, email, 
                   id_type, id_number, aadhar_number, pan_number, date_of_birth, age,
                   nominee_name, nominee_address, nominee_relation, nominee_dob, nominee_age,
                   created_date
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

# ============== ACCOUNT FUNCTIONS ==============
def get_account_balance(account_code):
    """Get current balance of an account"""
    try:
        conn = get_db_connection()
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

def create_account(account_name, account_type, initial_balance=0, daily_limit=None, interest_rate=None, username=""):
    """Create a new account"""
    try:
        conn = get_db_connection()
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

def generate_account_code(account_type):
    """Generate a new account code based on type"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        prefix_map = {
            'INCOME': '4',
            'EXPENSE': '5',
            'ASSET': '1'
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
            else:
                new_code = '9100'
        
        return new_code
    except Exception as e:
        print(f"Error in generate_account_code: {e}")
        return '5100'

# ============== VOUCHER FUNCTIONS ==============
def generate_voucher_number(voucher_type):
    """Generate unique voucher number"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        prefix_map = {
            'JOURNAL': 'JV',
            'RECEIPT': 'RV',
            'PAYMENT': 'PV',
            'CONTRA': 'CV'
        }
        
        prefix = prefix_map.get(voucher_type, 'V')
        year = datetime.now().strftime('%Y')
        
        cursor.execute(f'''
            SELECT voucher_number FROM vouchers 
            WHERE voucher_number LIKE '{prefix}-{year}-%'
            ORDER BY voucher_number DESC LIMIT 1
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            last_number = int(result[0].split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"{prefix}-{year}-{str(new_number).zfill(6)}"
    except Exception as e:
        print(f"Error in generate_voucher_number: {e}")
        return f"V-{datetime.now().strftime('%Y%m%d')}-{str(int(time.time()))[-6:]}"

def update_account_balance(account_code, amount, is_debit=True):
    """Update account balance with debit/credit logic"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT account_type, balance FROM accounts WHERE account_code = ?', (account_code,))
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

def save_voucher(voucher_type, voucher_date, description, entries, username, status='POSTED'):
    """Save a new voucher and update account balances"""
    try:
        conn = get_db_connection()
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
                if not success:
                    conn.close()
                    return False, f"Error updating balance for {entry['account_name']}: {msg}"
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

def get_vouchers_by_type(voucher_type):
    """Get vouchers by type"""
    try:
        conn = get_db_connection()
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

def get_voucher(voucher_number):
    """Get voucher details"""
    try:
        conn = get_db_connection()
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

def update_voucher(voucher_number, voucher_date, description, entries, username):
    """Update an existing voucher"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM vouchers WHERE voucher_number = ?', (voucher_number,))
        if not cursor.fetchone():
            conn.close()
            return False, "Voucher not found"
        
        cursor.execute('SELECT entry_type, account_code, amount FROM voucher_entries WHERE voucher_number = ?', 
                      (voucher_number,))
        old_entries = cursor.fetchall()
        
        for entry in old_entries:
            if entry[0] == 'DEBIT':
                success, msg = update_account_balance(entry[1], entry[2], is_debit=False)
            else:
                success, msg = update_account_balance(entry[1], entry[2], is_debit=True)
            if not success:
                conn.close()
                return False, f"Error reversing old entries: {msg}"
        
        cursor.execute('DELETE FROM voucher_entries WHERE voucher_number = ?', (voucher_number,))
        cursor.execute('DELETE FROM journal_entries WHERE voucher_number = ?', (voucher_number,))
        
        total_amount = sum(entry['amount'] for entry in entries)
        
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            UPDATE vouchers 
            SET voucher_date = ?, description = ?, total_amount = ?, updated_date = ?, updated_by = ?
            WHERE voucher_number = ?
        ''', (voucher_date, description, total_amount, current_date, username, voucher_number))
        
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
        return True, f"Voucher {voucher_number} updated successfully"
    except Exception as e:
        print(f"Error in update_voucher: {e}")
        return False, f"Error updating voucher: {str(e)}"

def delete_voucher(voucher_number):
    """Delete a voucher and reverse balances"""
    try:
        conn = get_db_connection()
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

def delete_journal_entry(journal_id):
    """Delete a specific journal entry"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get the journal entry details first
        cursor.execute('SELECT account_code, amount, entry_type FROM journal_entries WHERE id = ?', (journal_id,))
        entry = cursor.fetchone()
        
        if not entry:
            conn.close()
            return False, "Journal entry not found"
        
        account_code, amount, entry_type = entry
        
        # Reverse the balance change
        if entry_type == 'DEBIT':
            success, msg = update_account_balance(account_code, amount, is_debit=False)
        else:
            success, msg = update_account_balance(account_code, amount, is_debit=True)
        
        if not success:
            conn.close()
            return False, f"Error reversing journal entry: {msg}"
        
        # Delete the journal entry
        cursor.execute('DELETE FROM journal_entries WHERE id = ?', (journal_id,))
        conn.commit()
        conn.close()
        return True, "Journal entry deleted successfully"
    except Exception as e:
        print(f"Error in delete_journal_entry: {e}")
        return False, f"Error deleting journal entry: {str(e)}"

def get_all_journal_entries(limit=200):
    """Get all journal entries"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, date, account_code, account_name, entry_type, amount, description, ref_no, username, voucher_number
            FROM journal_entries
            ORDER BY date DESC
            LIMIT ?
        ''', (limit,))
        result = cursor.fetchall()
        conn.close()
        return result
    except Exception as e:
        print(f"Error in get_all_journal_entries: {e}")
        return []

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

# ============== UI COMPONENTS ==============
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

# ============== VOUCHER UI FUNCTIONS ==============
def render_journal_voucher_form(voucher_data=None, edit_mode=False):
    """Render journal voucher entry form"""
    st.subheader("📝 Journal Voucher")
    
    all_accounts = get_all_accounts()
    account_options = []
    account_code_map = {}
    
    for code, data in all_accounts.items():
        display_text = f"{data['account_name']} ({code}) - {data['account_type']}"
        account_options.append(display_text)
        account_code_map[display_text] = code
    
    if not account_options:
        st.warning("No accounts found. Please create accounts first.")
        return None
    
    with st.form("journal_voucher_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            voucher_date = st.date_input("Voucher Date", value=datetime.now().date())
            if edit_mode and voucher_data:
                voucher_date = datetime.strptime(voucher_data['voucher_date'], '%Y-%m-%d').date()
        
        with col2:
            if edit_mode:
                st.text_input("Voucher Number", value=voucher_data['voucher_number'], disabled=True)
            else:
                st.text_input("Voucher Number", value="Auto-generated", disabled=True)
        
        with col3:
            if edit_mode:
                voucher_type = voucher_data['voucher_type']
                st.text_input("Voucher Type", value=voucher_type, disabled=True)
            else:
                voucher_type = st.selectbox("Voucher Type", ['JOURNAL', 'RECEIPT', 'PAYMENT', 'CONTRA'], key="voucher_type")
        
        description = st.text_area("Description", value=voucher_data.get('description', '') if edit_mode else '')
        
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
                acc_code = account_code_map.get(account_display, '')
                acc_name = account_display.split('(')[0].strip() if account_display else ''
            
            with col3:
                amount = st.number_input(f"Amount", min_value=0.0, step=100.0, key=f"amt_{i}")
            
            with col4:
                narration = st.text_input(f"Narration", key=f"nar_{i}", placeholder="Optional")
            
            if account_display and amount > 0 and acc_code:
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
        
        col1, col2 = st.columns(2)
        with col1:
            if edit_mode:
                submit = st.form_submit_button("💾 Update Voucher", type="primary")
            else:
                submit = st.form_submit_button("💾 Save Voucher", type="primary")
        
        with col2:
            if edit_mode and st.form_submit_button("🗑️ Delete Voucher", type="secondary"):
                return {'action': 'delete'}
        
        if submit:
            if len(entries) == 0:
                st.error("Please enter at least one valid entry")
                return None
            
            if total_debits == 0 and total_credits == 0:
                st.error("Please enter amounts greater than zero")
                return None
            
            if abs(diff) > 0.01:
                st.error("Total Debits must equal Total Credits")
                return None
            
            if edit_mode:
                voucher_type = voucher_data['voucher_type']
            else:
                voucher_type = st.session_state.get('voucher_type', 'JOURNAL')
            
            return {
                'action': 'save' if not edit_mode else 'update',
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
        filter_type = st.selectbox("Filter by Type", ['ALL', 'JOURNAL', 'RECEIPT', 'PAYMENT', 'CONTRA'])
    
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

# ============== JOURNAL ENTRIES MANAGEMENT ==============
def render_journal_entries_management():
    """Render journal entries management tab"""
    st.header("📋 Journal Entries Management")
    
    # Get all journal entries
    entries = get_all_journal_entries(limit=200)
    
    if not entries:
        st.info("No journal entries found")
        return
    
    # Display entries in a table
    entries_data = []
    for entry in entries:
        entries_data.append({
            'ID': entry[0],
            'Date': entry[1],
            'Account Code': entry[2],
            'Account Name': entry[3],
            'Type': entry[4],
            'Amount': f"₹{entry[5]:,.2f}",
            'Description': entry[6],
            'Ref No': entry[7],
            'User': entry[8],
            'Voucher No': entry[9] if entry[9] else 'N/A'
        })
    
    df = pd.DataFrame(entries_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.divider()
    st.subheader("🗑️ Delete Journal Entry")
    
    # Select entry to delete
    entry_options = [f"ID: {e[0]} - {e[3]} - ₹{e[5]:,.2f} - {e[1]}" for e in entries]
    selected_entry = st.selectbox("Select Journal Entry to Delete", entry_options)
    
    if selected_entry:
        # Extract ID from selection
        entry_id = int(selected_entry.split(' - ')[0].replace('ID: ', ''))
        
        # Show entry details
        entry_details = next((e for e in entries if e[0] == entry_id), None)
        if entry_details:
            st.warning(f"""
            ⚠️ You are about to delete journal entry:
            - **Account:** {entry_details[3]} ({entry_details[2]})
            - **Type:** {entry_details[4]}
            - **Amount:** ₹{entry_details[5]:,.2f}
            - **Date:** {entry_details[1]}
            - **Description:** {entry_details[6]}
            """)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Delete Entry", type="primary"):
                    success, msg = delete_journal_entry(entry_id)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
            with col2:
                if st.button("❌ Cancel"):
                    st.rerun()
    
    st.divider()
    st.caption(f"Total Journal Entries: {len(entries)}")

# ============== MAIN APP ==============
def main():
    try:
        if not os.path.exists(DB_FILE):
            init_database()
        
        if 'logged_in' not in st.session_state or not st.session_state.logged_in:
            login_page()
            return
        
        user = st.session_state.user
        
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
                display_account_card('1100', '🏦', '#2E86AB')
                display_account_card('1200', '🏦', '#1B4F72')
                
                st.divider()
                
                with st.expander("🏦 Other ASSETS", expanded=True):
                    for code in ['1300', '1400']:
                        display_account_card(code, '💰', '#2E86AB')
                
                with st.expander("🏛️ LIABILITIES", expanded=True):
                    for code in ['2100', '2200']:
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
        
        # Main Tabs - Added Journal Entries Management Tab
        tabs = ["📝 Journal Vouchers", "💰 Cash & Bank", "👥 Customers & KYC", 
                "📊 Financial Reports", "📋 Trial Balance", "📋 Journal Entries", "⚙️ Head Management"]
        
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(tabs)
        
        # ---------- TAB 1: JOURNAL VOUCHERS ----------
        with tab1:
            st.header("📝 Voucher Management")
            
            voucher_tab1, voucher_tab2, voucher_tab3 = st.tabs(["➕ Create Voucher", "📋 View/Edit/Delete Vouchers", "🧾 Voucher Register"])
            
            with voucher_tab1:
                result = render_journal_voucher_form()
                if result:
                    if result['action'] == 'save':
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
                                result = render_journal_voucher_form(voucher_data, edit_mode=True)
                                if result:
                                    if result['action'] == 'update':
                                        success, msg = update_voucher(
                                            selected_voucher,
                                            result['voucher_date'],
                                            result['description'],
                                            result['entries'],
                                            user['username']
                                        )
                                        if success:
                                            st.success(msg)
                                            st.rerun()
                                        else:
                                            st.error(msg)
                        
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
            
            with voucher_tab3:
                st.subheader("🧾 Voucher Register")
                
                all_vouchers = get_all_vouchers(limit=1000)
                if all_vouchers:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Vouchers", len(all_vouchers))
                    with col2:
                        journal_count = len([v for v in all_vouchers if v['voucher_type'] == 'JOURNAL'])
                        st.metric("Journal Vouchers", journal_count)
                    with col3:
                        receipt_count = len([v for v in all_vouchers if v['voucher_type'] == 'RECEIPT'])
                        st.metric("Receipt Vouchers", receipt_count)
                    with col4:
                        payment_count = len([v for v in all_vouchers if v['voucher_type'] == 'PAYMENT'])
                        st.metric("Payment Vouchers", payment_count)
                    
                    st.divider()
                    
                    register_data = []
                    for v in all_vouchers:
                        register_data.append({
                            'Voucher No': v['voucher_number'],
                            'Type': v['voucher_type'],
                            'Date': v['voucher_date'],
                            'Description': v['description'],
                            'Amount': f"₹{v['total_amount']:,.2f}",
                            'Status': v['status'],
                            'Created': v['created_date'],
                            'By': v['created_by']
                        })
                    
                    df_register = pd.DataFrame(register_data)
                    st.dataframe(df_register, use_container_width=True, hide_index=True)
                    
                    if st.button("📊 Export to CSV"):
                        csv = df_register.to_csv(index=False)
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name=f"voucher_register_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                else:
                    st.info("No vouchers found")
        
        # ---------- TAB 2: CASH & BANK ----------
        with tab2:
            st.header("💰 Cash & Bank Transactions")
            
            col1, col2, col3 = st.columns(3)
            cash_balance = get_account_balance('1000')
            bank_savings = get_account_balance('1100')
            bank_current = get_account_balance('1200')
            
            with col1:
                st.metric("💵 Cash Balance", f"₹{cash_balance:,.2f}")
            with col2:
                st.metric("🏦 Bank Savings", f"₹{bank_savings:,.2f}")
            with col3:
                st.metric("🏦 Bank Current", f"₹{bank_current:,.2f}")
            
            st.info("💡 Use Journal Vouchers tab to create Cash/Bank entries with proper voucher numbers")
        
        # ---------- TAB 3: CUSTOMERS & KYC ----------
        with tab3:
            st.header("👥 Customer Management with KYC")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("➕ Register New Customer")
                
                # Initialize session state for age if not exists
                if 'customer_age' not in st.session_state:
                    st.session_state.customer_age = ""
                if 'nominee_age' not in st.session_state:
                    st.session_state.nominee_age = ""
                
                with st.form("customer_form", clear_on_submit=False):
                    st.markdown("### 📋 Personal Details")
                    
                    full_name = st.text_input("Full Name*", value=st.session_state.get('full_name', ''))
                    
                    # Date of Birth with age in separate text box
                    min_date = datetime(1900, 1, 1).date()
                    max_date = datetime.now().date()
                    
                    date_of_birth = st.date_input(
                        "Date of Birth*", 
                        value=st.session_state.get('dob_value', None),
                        min_value=min_date,
                        max_value=max_date,
                        help="Select date of birth (1900 to present)"
                    )
                    
                    # Age display - disabled text box
                    st.text_input(
                        "Age (Auto-calculated)*",
                        value=st.session_state.customer_age,
                        disabled=True,
                        help="Age will be auto-calculated when you click the Calculate button"
                    )
                    
                    # Calculate Age button
                    calc_age = st.form_submit_button("📅 Calculate Age")
                    if calc_age:
                        if date_of_birth:
                            today = datetime.now().date()
                            age_value = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
                            st.session_state.customer_age = str(age_value)
                            st.session_state.dob_value = date_of_birth
                            st.session_state.full_name = full_name
                            st.success(f"✅ Age calculated: {age_value} years")
                        else:
                            st.warning("⚠️ Please select a Date of Birth first")
                    
                    address = st.text_area("Address*", value=st.session_state.get('address', ''))
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        phone = st.text_input("Phone Number*", value=st.session_state.get('phone', ''))
                        email = st.text_input("Email*", value=st.session_state.get('email', ''))
                    with col_b:
                        whatsapp_number = st.text_input("WhatsApp Number", value=st.session_state.get('whatsapp', ''))
                    
                    st.markdown("### 🪪 KYC Documents")
                    st.markdown("**Aadhaar Details (Compulsory)**")
                    col_c, col_d = st.columns(2)
                    with col_c:
                        aadhar_number = st.text_input("Aadhaar Number (12 digits)*", value=st.session_state.get('aadhar', ''))
                        if aadhar_number and not validate_aadhar(aadhar_number):
                            st.error("❌ Invalid Aadhaar number. Must be 12 digits.")
                    with col_d:
                        aadhar_image = st.file_uploader("Upload Aadhaar Card Image*", type=['jpg', 'jpeg', 'png', 'pdf'], key="aadhar_upload")
                    
                    st.markdown("**PAN Card Details (Compulsory)**")
                    col_e, col_f = st.columns(2)
                    with col_e:
                        pan_number = st.text_input("PAN Number (e.g., ABCDE1234F)*", value=st.session_state.get('pan', ''))
                        if pan_number and not validate_pan(pan_number):
                            st.error("❌ Invalid PAN number. Format: ABCDE1234F")
                    with col_f:
                        pan_image = st.file_uploader("Upload PAN Card Image*", type=['jpg', 'jpeg', 'png', 'pdf'], key="pan_upload")
                    
                    st.markdown("### 👤 Nominee Details")
                    col_g, col_h = st.columns(2)
                    with col_g:
                        nominee_name = st.text_input("Nominee Full Name", value=st.session_state.get('nominee_name', ''))
                        
                        nominee_dob = st.date_input(
                            "Nominee Date of Birth", 
                            value=st.session_state.get('nominee_dob_value', None),
                            min_value=min_date,
                            max_value=max_date,
                            help="Select nominee's date of birth (1900 to present)"
                        )
                        
                        # Nominee Age - disabled text box
                        st.text_input(
                            "Nominee Age (Auto-calculated)",
                            value=st.session_state.nominee_age,
                            disabled=True,
                            help="Age will be auto-calculated when you click the Calculate button"
                        )
                        
                        # Calculate Nominee Age button
                        calc_nom_age = st.form_submit_button("📅 Calculate Nominee Age")
                        if calc_nom_age:
                            if nominee_dob:
                                today = datetime.now().date()
                                age_value = today.year - nominee_dob.year - ((today.month, today.day) < (nominee_dob.month, nominee_dob.day))
                                st.session_state.nominee_age = str(age_value)
                                st.session_state.nominee_dob_value = nominee_dob
                                st.success(f"✅ Nominee Age calculated: {age_value} years")
                            else:
                                st.warning("⚠️ Please select a Nominee Date of Birth first")
                        
                        nominee_relation = st.text_input("Nominee Relation (e.g., Spouse, Son, Daughter)", value=st.session_state.get('nominee_relation', ''))
                    with col_h:
                        nominee_address = st.text_area("Nominee Address", value=st.session_state.get('nominee_address', ''))
                    
                    st.markdown("**Nominee Aadhaar Details (Optional)**")
                    col_i, col_j = st.columns(2)
                    with col_i:
                        nominee_aadhar = st.text_input("Nominee Aadhaar Number", value=st.session_state.get('nominee_aadhar', ''))
                        if nominee_aadhar and not validate_aadhar(nominee_aadhar):
                            st.error("❌ Invalid Aadhaar number. Must be 12 digits.")
                    with col_j:
                        nominee_aadhar_image = st.file_uploader("Upload Nominee Aadhaar Image", type=['jpg', 'jpeg', 'png', 'pdf'], key="nom_aadhar_upload")
                    
                    st.markdown("**Nominee PAN Details (Optional)**")
                    col_k, col_l = st.columns(2)
                    with col_k:
                        nominee_pan = st.text_input("Nominee PAN Number", value=st.session_state.get('nominee_pan', ''))
                        if nominee_pan and not validate_pan(nominee_pan):
                            st.error("❌ Invalid PAN number. Format: ABCDE1234F")
                    with col_l:
                        nominee_pan_image = st.file_uploader("Upload Nominee PAN Image", type=['jpg', 'jpeg', 'png', 'pdf'], key="nom_pan_upload")
                    
                    st.markdown("### 📝 Additional Information")
                    id_type = st.selectbox("ID Type*", ["Aadhaar", "PAN", "Passport", "Driving License", "Voter ID"], index=st.session_state.get('id_type_index', 0))
                    id_number = st.text_input("ID Number*", value=st.session_state.get('id_number', ''))
                    
                    # Submit button
                    submitted = st.form_submit_button("✅ Register Customer")
                    
                    if submitted:
                        # Save all values to session state
                        st.session_state.full_name = full_name
                        st.session_state.dob_value = date_of_birth
                        st.session_state.address = address
                        st.session_state.phone = phone
                        st.session_state.email = email
                        st.session_state.whatsapp = whatsapp_number
                        st.session_state.aadhar = aadhar_number
                        st.session_state.pan = pan_number
                        st.session_state.nominee_name = nominee_name
                        st.session_state.nominee_dob_value = nominee_dob
                        st.session_state.nominee_relation = nominee_relation
                        st.session_state.nominee_address = nominee_address
                        st.session_state.nominee_aadhar = nominee_aadhar
                        st.session_state.nominee_pan = nominee_pan
                        st.session_state.id_type_index = ["Aadhaar", "PAN", "Passport", "Driving License", "Voter ID"].index(id_type)
                        st.session_state.id_number = id_number
                        
                        # Validate required fields
                        errors = []
                        if not full_name:
                            errors.append("Full Name is required")
                        if not date_of_birth:
                            errors.append("Date of Birth is required")
                        if not st.session_state.customer_age or st.session_state.customer_age == "":
                            errors.append("Please calculate Age using the 'Calculate Age' button")
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
                            # Convert images to base64
                            aadhar_image_b64 = image_to_base64(aadhar_image)
                            pan_image_b64 = image_to_base64(pan_image)
                            nominee_aadhar_image_b64 = image_to_base64(nominee_aadhar_image) if nominee_aadhar_image else None
                            nominee_pan_image_b64 = image_to_base64(nominee_pan_image) if nominee_pan_image else None
                            
                            # Get age values from session state
                            customer_age = int(st.session_state.customer_age) if st.session_state.customer_age else None
                            nominee_age_value = int(st.session_state.nominee_age) if st.session_state.nominee_age else None
                            
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
                                'age': customer_age,
                                'nominee_name': nominee_name,
                                'nominee_address': nominee_address,
                                'nominee_relation': nominee_relation,
                                'nominee_dob': nominee_dob.strftime('%Y-%m-%d') if nominee_dob else None,
                                'nominee_age': nominee_age_value,
                                'nominee_aadhar': nominee_aadhar,
                                'nominee_aadhar_image': nominee_aadhar_image_b64,
                                'nominee_pan': nominee_pan,
                                'nominee_pan_image': nominee_pan_image_b64
                            }
                            
                            success, msg = create_customer(customer_data, user['username'])
                            if success:
                                st.success(msg)
                                st.balloons()
                                # Clear session state after successful registration
                                for key in list(st.session_state.keys()):
                                    if key not in ['logged_in', 'user']:
                                        del st.session_state[key]
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
                            'KYC': '✅',
                            'Savings': f"₹{balances.get('1100', 0):,.2f}",
                            'Current': f"₹{balances.get('1200', 0):,.2f}",
                            'FD': f"₹{balances.get('1300', 0):,.2f}"
                        })
                    df = pd.DataFrame(cust_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("No customers registered yet.")
            
            if customers:
                st.divider()
                st.subheader("🔍 Customer Details")
                selected = st.selectbox("Select Customer", [f"{c['full_name']} ({cid})" for cid, c in customers.items()])
                if selected:
                    cust_id = selected.split('(')[-1].replace(')', '')
                    cust = customers[cust_id]
                    balances = get_customer_balances(cust_id)
                    
                    full_details = get_customer_details(cust_id)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**Name:** {cust['full_name']}")
                        st.markdown(f"**ID:** {cust_id}")
                        st.markdown(f"**DOB:** {cust.get('date_of_birth', 'N/A')}")
                        st.markdown(f"**Age:** {cust.get('age', 'N/A')} years")
                    with col2:
                        st.markdown(f"**Phone:** {cust['phone']}")
                        st.markdown(f"**WhatsApp:** {cust.get('whatsapp_number', 'N/A')}")
                        st.markdown(f"**Email:** {cust['email']}")
                    with col3:
                        st.markdown(f"**Aadhaar:** {cust.get('aadhar_number', 'N/A')}")
                        st.markdown(f"**PAN:** {cust.get('pan_number', 'N/A')}")
                        st.markdown(f"**Address:** {cust.get('address', 'N/A')}")
                    
                    # Display uploaded documents
                    st.markdown("---")
                    st.markdown("### 📎 Uploaded Documents")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Aadhaar Card**")
                        if full_details and full_details.get('aadhar_image'):
                            st.image(display_image_from_base64(full_details['aadhar_image']), use_container_width=True)
                        else:
                            st.caption("No Aadhaar image uploaded")
                        
                        st.markdown("**PAN Card**")
                        if full_details and full_details.get('pan_image'):
                            st.image(display_image_from_base64(full_details['pan_image']), use_container_width=True)
                        else:
                            st.caption("No PAN image uploaded")
                    
                    with col2:
                        st.markdown("**Nominee Aadhaar Card**")
                        if full_details and full_details.get('nominee_aadhar_image'):
                            st.image(display_image_from_base64(full_details['nominee_aadhar_image']), use_container_width=True)
                        else:
                            st.caption("No Nominee Aadhaar image uploaded")
                        
                        st.markdown("**Nominee PAN Card**")
                        if full_details and full_details.get('nominee_pan_image'):
                            st.image(display_image_from_base64(full_details['nominee_pan_image']), use_container_width=True)
                        else:
                            st.caption("No Nominee PAN image uploaded")
                    
                    # Nominee Details
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
                    
                    st.markdown("---")
                    st.markdown("**Account Balances**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Savings", f"₹{balances.get('1100', 0):,.2f}")
                    with col2:
                        st.metric("Current", f"₹{balances.get('1200', 0):,.2f}")
                    with col3:
                        st.metric("FD", f"₹{balances.get('1300', 0):,.2f}")
        
        # ---------- TAB 4: FINANCIAL REPORTS ----------
        with tab4:
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
        
        # ---------- TAB 6: JOURNAL ENTRIES MANAGEMENT ----------
        with tab6:
            render_journal_entries_management()
        
        # ---------- TAB 7: HEAD MANAGEMENT ----------
        with tab7:
            st.header("⚙️ Expense & Income Head Management")
            
            if user['role'] not in ['admin', 'manager']:
                st.warning("⚠️ Only administrators and managers can manage expense/income heads.")
            else:
                head_tab1, head_tab2, head_tab3 = st.tabs(["➕ Create Head", "✏️ Edit/Delete Head", "📊 Head Summary"])
                
                with head_tab1:
                    st.subheader("➕ Create New Expense or Income Head")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        with st.form("create_head_form"):
                            head_type = st.selectbox("Head Type", ['INCOME', 'EXPENSE'])
                            head_name = st.text_input("Head Name*", placeholder="e.g., Office Supplies, Commission Income")
                            initial_balance = st.number_input("Initial Balance", min_value=0.0, step=100.0, value=0.0)
                            
                            if head_type == 'EXPENSE':
                                daily_limit = st.number_input("Daily Limit (Optional)", min_value=0.0, step=1000.0, value=0.0)
                            else:
                                daily_limit = 0
                            
                            submitted = st.form_submit_button("Create Head")
                            
                            if submitted:
                                if head_name:
                                    limit_value = daily_limit if daily_limit > 0 else None
                                    success, msg = create_account(
                                        head_name, 
                                        head_type, 
                                        initial_balance,
                                        limit_value,
                                        None,
                                        user['username']
                                    )
                                    if success:
                                        st.success(msg)
                                        st.balloons()
                                        st.rerun()
                                    else:
                                        st.error(msg)
                                else:
                                    st.warning("Please enter a head name")
                    
                    with col2:
                        st.subheader("📋 Existing Heads")
                        income_heads = get_accounts_by_type('INCOME')
                        expense_heads = get_accounts_by_type('EXPENSE')
                        
                        st.markdown("**Income Heads**")
                        if income_heads:
                            for acc in income_heads:
                                st.caption(f"• {acc['account_code']}: {acc['account_name']} (₹{acc['balance']:,.2f})")
                        else:
                            st.caption("No income heads created yet")
                        
                        st.markdown("**Expense Heads**")
                        if expense_heads:
                            for acc in expense_heads:
                                st.caption(f"• {acc['account_code']}: {acc['account_name']} (₹{acc['balance']:,.2f})")
                        else:
                            st.caption("No expense heads created yet")
                
                with head_tab2:
                    st.subheader("✏️ Edit or Delete Head")
                    
                    all_heads = get_accounts_by_type('INCOME') + get_accounts_by_type('EXPENSE')
                    
                    if not all_heads:
                        st.info("No heads available to edit or delete.")
                    else:
                        head_options = [f"{acc['account_name']} ({acc['account_code']}) - {acc['account_type']}" 
                                       for acc in all_heads]
                        selected_head = st.selectbox("Select Head to Manage", head_options)
                        
                        if selected_head:
                            acc_code = selected_head.split('(')[1].split(')')[0]
                            head_data = next((acc for acc in all_heads if acc['account_code'] == acc_code), None)
                            
                            if head_data:
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.subheader("✏️ Edit Head")
                                    with st.form("edit_head_form"):
                                        new_name = st.text_input("New Name", value=head_data['account_name'])
                                        
                                        if head_data['account_type'] == 'EXPENSE':
                                            current_limit = head_data.get('daily_limit')
                                            default_limit = current_limit if current_limit is not None else 0.0
                                            new_limit = st.number_input("Daily Limit", 
                                                                       value=float(default_limit),
                                                                       step=1000.0)
                                        else:
                                            new_limit = 0
                                            st.info("Income heads don't have daily limits")
                                        
                                        edit_submitted = st.form_submit_button("Update Head")
                                        
                                        if edit_submitted:
                                            if new_name:
                                                limit_value = new_limit if new_limit > 0 else None
                                                if head_data['account_type'] == 'EXPENSE':
                                                    success, msg = update_account(
                                                        acc_code, 
                                                        new_name,
                                                        limit_value,
                                                        None
                                                    )
                                                else:
                                                    success, msg = update_account(
                                                        acc_code, 
                                                        new_name,
                                                        None,
                                                        None
                                                    )
                                                if success:
                                                    st.success(msg)
                                                    st.rerun()
                                                else:
                                                    st.error(msg)
                                            else:
                                                st.warning("Name cannot be empty")
                                
                                with col2:
                                    st.subheader("🗑️ Delete Head")
                                    st.warning(f"⚠️ You are about to delete '{head_data['account_name']}'")
                                    
                                    try:
                                        conn = get_db_connection()
                                        if conn:
                                            cursor = conn.cursor()
                                            cursor.execute('SELECT COUNT(*) FROM transactions WHERE account_code = ?', (acc_code,))
                                            txn_count = cursor.fetchone()[0]
                                            conn.close()
                                    except Exception as e:
                                        print(f"Error checking transactions: {e}")
                                        txn_count = 0
                                    
                                    if txn_count > 0:
                                        st.info(f"This account has {txn_count} transactions. It will be marked as inactive.")
                                    else:
                                        st.info("This account has no transactions. It will be permanently deleted.")
                                    
                                    if st.button("🗑️ Delete Head", type="primary"):
                                        success, msg = delete_account(acc_code)
                                        if success:
                                            st.success(msg)
                                            st.rerun()
                                        else:
                                            st.error(msg)
                
                with head_tab3:
                    st.subheader("📊 Head Summary")
                    
                    income_heads = get_accounts_by_type('INCOME')
                    expense_heads = get_accounts_by_type('EXPENSE')
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### 📊 Income Heads")
                        if income_heads:
                            income_data = []
                            total_income = 0
                            for acc in income_heads:
                                income_data.append({
                                    'Code': acc['account_code'],
                                    'Name': acc['account_name'],
                                    'Balance': f"₹{acc['balance']:,.2f}",
                                    'Created': acc['created_date'][:10] if acc['created_date'] else '',
                                    'By': acc['created_by']
                                })
                                total_income += acc['balance']
                            df = pd.DataFrame(income_data)
                            st.dataframe(df, use_container_width=True, hide_index=True)
                            st.metric("Total Income", f"₹{total_income:,.2f}")
                        else:
                            st.info("No income heads created yet")
                    
                    with col2:
                        st.markdown("### 📉 Expense Heads")
                        if expense_heads:
                            expense_data = []
                            total_expense = 0
                            for acc in expense_heads:
                                daily_limit = acc.get('daily_limit')
                                expense_data.append({
                                    'Code': acc['account_code'],
                                    'Name': acc['account_name'],
                                    'Balance': f"₹{acc['balance']:,.2f}",
                                    'Daily Limit': f"₹{daily_limit:,.2f}" if daily_limit is not None else 'N/A',
                                    'Created': acc['created_date'][:10] if acc['created_date'] else '',
                                    'By': acc['created_by']
                                })
                                total_expense += acc['balance']
                            df = pd.DataFrame(expense_data)
                            st.dataframe(df, use_container_width=True, hide_index=True)
                            st.metric("Total Expenses", f"₹{total_expense:,.2f}")
                        else:
                            st.info("No expense heads created yet")
                    
                    st.divider()
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Income Heads", len(income_heads))
                    with col2:
                        st.metric("Total Expense Heads", len(expense_heads))
                    with col3:
                        net = sum(acc['balance'] for acc in income_heads) - sum(acc['balance'] for acc in expense_heads)
                        if net >= 0:
                            st.success(f"Net Income: ₹{net:,.2f}")
                        else:
                            st.error(f"Net Loss: ₹{abs(net):,.2f}")
    
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        print(f"Error in main: {e}")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
