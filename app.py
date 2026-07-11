import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import hashlib
import os
import time
import traceback

# ============== DATABASE SETUP WITH MIGRATION ==============
DB_FILE = "banking_system.db"

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect(DB_FILE)

def get_table_columns(table_name):
    """Get column names of a table"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    conn.close()
    return columns

def migrate_database():
    """Add missing columns to existing tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check and add missing columns to accounts table
    columns = get_table_columns('accounts')
    
    if 'created_by' not in columns:
        try:
            cursor.execute("ALTER TABLE accounts ADD COLUMN created_by TEXT")
            cursor.execute("UPDATE accounts SET created_by = 'system' WHERE created_by IS NULL")
        except sqlite3.OperationalError as e:
            print(f"Could not add created_by: {e}")
    
    if 'is_active' not in columns:
        try:
            cursor.execute("ALTER TABLE accounts ADD COLUMN is_active INTEGER DEFAULT 1")
            cursor.execute("UPDATE accounts SET is_active = 1 WHERE is_active IS NULL")
        except sqlite3.OperationalError as e:
            print(f"Could not add is_active: {e}")
    
    conn.commit()
    conn.close()

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
            email TEXT NOT NULL,
            id_type TEXT NOT NULL,
            id_number TEXT NOT NULL,
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
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    ''')
    
    conn.commit()
    
    # Check if default accounts already exist
    cursor.execute("SELECT COUNT(*) FROM accounts")
    count = cursor.fetchone()[0]
    
    if count == 0:
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Insert default accounts
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
    conn.close()
    
    # Run migration to ensure all columns exist
    migrate_database()

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username, password):
    """Verify user credentials"""
    try:
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
                'last_login': user[6] if len(user) > 6 else None
            }
    except Exception as e:
        print(f"Error in verify_user: {e}")
        return None
    return None

# ============== CASH TRANSACTION FUNCTIONS ==============
def generate_cash_transaction_id():
    """Generate unique cash transaction ID"""
    return f"CASHTXN{datetime.now().strftime('%Y%m%d%H%M%S')}{str(time.time_ns())[-6:]}"

def record_cash_transaction(txn_type, amount, description="", username="", customer_id=None):
    """Record a single cash transaction (single entry)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        txn_id = generate_cash_transaction_id()
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Get current cash balance
        cursor.execute('SELECT balance FROM accounts WHERE account_code = "1000"')
        result = cursor.fetchone()
        current_balance = result[0] if result else 0
        
        if txn_type == 'RECEIPT':
            new_balance = current_balance + amount
        elif txn_type == 'PAYMENT':
            if current_balance < amount:
                conn.close()
                return False, f"Insufficient cash balance. Available: ₹{current_balance:,.2f}"
            new_balance = current_balance - amount
        else:
            conn.close()
            return False, "Invalid transaction type"
        
        # Update cash account balance
        cursor.execute('UPDATE accounts SET balance = ? WHERE account_code = "1000"', (new_balance,))
        
        # Record cash transaction
        cursor.execute('''
            INSERT INTO cash_transactions 
            (transaction_id, date, transaction_type, amount, description, balance_after, username, customer_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (txn_id, date, txn_type, amount, description, new_balance, username, customer_id))
        
        # Also record in main transactions for journal
        cursor.execute('''
            INSERT INTO transactions 
            (transaction_id, date, account_code, transaction_type, amount, description, balance_after, username)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (txn_id, date, '1000', txn_type, amount, description, new_balance, username))
        
        # Record in journal entries
        entry_type = 'DEBIT' if txn_type == 'RECEIPT' else 'CREDIT'
        cursor.execute('''
            INSERT INTO journal_entries 
            (date, account_code, account_name, entry_type, amount, description, ref_no, username)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date, '1000', 'CASH', entry_type, amount, description, txn_id, username))
        
        conn.commit()
        conn.close()
        
        return True, f"Cash {txn_type} of ₹{amount:,.2f} recorded successfully"
    except Exception as e:
        print(f"Error in record_cash_transaction: {e}")
        return False, f"Error: {str(e)}"

def get_cash_transactions(limit=100):
    """Get cash transactions"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT date, transaction_type, amount, description, balance_after, username, customer_id
            FROM cash_transactions
            ORDER BY date DESC
            LIMIT ?
        ''', (limit,))
        result = cursor.fetchall()
        conn.close()
        return result
    except Exception as e:
        print(f"Error in get_cash_transactions: {e}")
        return []

# ============== BANK TRANSACTION FUNCTIONS ==============
def record_bank_transaction(account_code, txn_type, amount, description="", username="", customer_id=None):
    """Record a single bank transaction (single entry)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        txn_id = generate_transaction_id()
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Get current bank balance
        cursor.execute('SELECT balance, account_name FROM accounts WHERE account_code = ?', (account_code,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "Account not found"
        
        current_balance, account_name = result
        
        if txn_type == 'DEPOSIT':
            new_balance = current_balance + amount
        elif txn_type == 'WITHDRAWAL':
            if current_balance < amount:
                conn.close()
                return False, f"Insufficient balance in {account_name}. Available: ₹{current_balance:,.2f}"
            new_balance = current_balance - amount
        else:
            conn.close()
            return False, "Invalid transaction type"
        
        # Update account balance
        cursor.execute('UPDATE accounts SET balance = ? WHERE account_code = ?', (new_balance, account_code))
        
        # Record transaction
        cursor.execute('''
            INSERT INTO transactions 
            (transaction_id, date, account_code, transaction_type, amount, description, balance_after, username)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (txn_id, date, account_code, txn_type, amount, description, new_balance, username))
        
        # Record in journal entries
        entry_type = 'DEBIT' if txn_type == 'DEPOSIT' else 'CREDIT'
        cursor.execute('''
            INSERT INTO journal_entries 
            (date, account_code, account_name, entry_type, amount, description, ref_no, username)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date, account_code, account_name, entry_type, amount, description, txn_id, username))
        
        conn.commit()
        conn.close()
        
        return True, f"Bank {txn_type} of ₹{amount:,.2f} recorded in {account_name}"
    except Exception as e:
        print(f"Error in record_bank_transaction: {e}")
        return False, f"Error: {str(e)}"

# ============== ACCOUNT MANAGEMENT FUNCTIONS ==============
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

def create_account(account_name, account_type, initial_balance=0, daily_limit=None, interest_rate=None, username=""):
    """Create a new account"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if account already exists
        cursor.execute('SELECT * FROM accounts WHERE account_name = ? AND account_type = ? AND is_active = 1', 
                       (account_name, account_type))
        if cursor.fetchone():
            conn.close()
            return False, f"Account '{account_name}' already exists in {account_type} category"
        
        account_code = generate_account_code(account_type)
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Ensure daily_limit is None if 0 or negative
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
            # Ensure daily_limit is None if 0 or negative
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
        
        # Check if account has transactions
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

def get_all_accounts():
    """Get all active accounts"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        columns = get_table_columns('accounts')
        
        if 'maturity_date' in columns and 'interest_rate' in columns:
            cursor.execute('''
                SELECT account_code, account_name, account_type, balance, daily_limit, maturity_date, interest_rate, is_active
                FROM accounts 
                WHERE is_active = 1
                ORDER BY account_code
            ''')
        else:
            cursor.execute('''
                SELECT account_code, account_name, account_type, balance, daily_limit, NULL as maturity_date, NULL as interest_rate, is_active
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
                'maturity_date': row[5] if len(row) > 5 else None,
                'interest_rate': row[6] if len(row) > 6 else None,
                'is_active': row[7] if len(row) > 7 else 1
            }
        return accounts
    except Exception as e:
        print(f"Error in get_all_accounts: {e}")
        return {}

def get_account_name(account_code):
    """Get account name from code"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT account_name FROM accounts WHERE account_code = ?', (account_code,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error in get_account_name: {e}")
        return None

# ============== ACCOUNTING FUNCTIONS ==============
def generate_transaction_id():
    """Generate unique transaction ID"""
    return f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{str(time.time_ns())[-6:]}"

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

def update_account_balance(account_code, amount, is_debit=True):
    """Update account balance with debit/credit logic"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT account_type, balance FROM accounts WHERE account_code = ?', (account_code,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "Account not found"
        
        acc_type, current_balance = result
        
        if acc_type in ['ASSET', 'EXPENSE']:
            new_balance = current_balance + amount if is_debit else current_balance - amount
        else:
            new_balance = current_balance - amount if is_debit else current_balance + amount
        
        cursor.execute('UPDATE accounts SET balance = ? WHERE account_code = ?', (new_balance, account_code))
        conn.commit()
        conn.close()
        return True, new_balance
    except Exception as e:
        print(f"Error in update_account_balance: {e}")
        return False, str(e)

def record_transaction(account_code, txn_type, amount, description="", username="", ref_no=""):
    """Record a transaction"""
    try:
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
        
        cursor.execute('SELECT account_name FROM accounts WHERE account_code = ?', (account_code,))
        acc_name = cursor.fetchone()[0]
        
        entry_type = 'DEBIT' if txn_type in ['DEPOSIT', 'RECEIPT'] else 'CREDIT'
        cursor.execute('''
            INSERT INTO journal_entries 
            (date, account_code, account_name, entry_type, amount, description, ref_no, username)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date, account_code, acc_name, entry_type, amount, description, ref_no, username))
        
        conn.commit()
        conn.close()
        return True, txn_id
    except Exception as e:
        print(f"Error in record_transaction: {e}")
        return False, str(e)

def double_entry(debit_account, credit_account, amount, description="", username=""):
    """Perform double-entry bookkeeping for transfers between accounts"""
    if amount <= 0:
        return False, "Amount must be greater than zero"
    
    success, msg = update_account_balance(debit_account, amount, is_debit=True)
    if not success:
        return False, msg
    
    success, msg = update_account_balance(credit_account, amount, is_debit=False)
    if not success:
        update_account_balance(debit_account, amount, is_debit=False)
        return False, msg
    
    ref_no = f"JE{datetime.now().strftime('%Y%m%d%H%M%S')}"
    record_transaction(debit_account, 'DEBIT', amount, f"{description} (Dr)", username, ref_no)
    record_transaction(credit_account, 'CREDIT', amount, f"{description} (Cr)", username, ref_no)
    
    return True, f"Journal entry posted: Dr {debit_account} / Cr {credit_account} for ₹{amount:,.2f}"

# ============== CUSTOMER FUNCTIONS ==============
def create_customer(full_name, address, phone, email, id_type, id_number, username):
    """Create a new customer"""
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
            (customer_id, full_name, address, phone, email, id_type, id_number, kyc_completed, created_date, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (customer_id, full_name, address, phone, email, id_type, id_number, 1, date, username))
        
        for acc_code in ['1100', '1200', '1300']:
            cursor.execute('''
                INSERT INTO customer_accounts (customer_id, account_code, balance)
                VALUES (?, ?, ?)
            ''', (customer_id, acc_code, 0))
        
        conn.commit()
        conn.close()
        return True, f"Customer {full_name} created with ID: {customer_id}"
    except Exception as e:
        print(f"Error in create_customer: {e}")
        return False, f"Error creating customer: {str(e)}"

def get_all_customers():
    """Get all customers"""
    try:
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
    except Exception as e:
        print(f"Error in get_all_customers: {e}")
        return {}

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

def record_customer_transaction(customer_id, account_code, amount, txn_type, description="", username=""):
    """Record a customer transaction"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            UPDATE customer_accounts 
            SET balance = balance + ? 
            WHERE customer_id = ? AND account_code = ?
        ''', (amount if txn_type == 'DEPOSIT' else -amount, customer_id, account_code))
        
        cursor.execute('''
            INSERT INTO customer_transactions 
            (customer_id, date, transaction_type, amount, account_code, description, username)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (customer_id, date, txn_type, amount, account_code, description, username))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error in record_customer_transaction: {e}")
        return False

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

def get_cash_balance():
    """Get current cash balance"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM accounts WHERE account_code = "1000"')
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    except Exception as e:
        print(f"Error in get_cash_balance: {e}")
        return 0

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
            init_database()
        else:
            try:
                migrate_database()
            except Exception as e:
                print(f"Migration error: {e}")
        
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
                # Cash and Bank Accounts - Show prominently
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
        
        # Main Tabs
        tabs = ["💰 Cash & Bank", "👥 Customers & KYC", "📊 Financial Reports", 
                "📝 Journal Entries", "📋 Trial Balance", "⚙️ Head Management"]
        
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(tabs)
        
        # ---------- TAB 1: CASH & BANK ----------
        with tab1:
            st.header("💰 Cash & Bank Transactions")
            
            # Cash and Bank Summary
            col1, col2, col3 = st.columns(3)
            cash_balance = get_cash_balance()
            bank_savings = get_account_balance('1100')
            bank_current = get_account_balance('1200')
            
            with col1:
                st.metric("💵 Cash Balance", f"₹{cash_balance:,.2f}")
            with col2:
                st.metric("🏦 Bank Savings", f"₹{bank_savings:,.2f}")
            with col3:
                st.metric("🏦 Bank Current", f"₹{bank_current:,.2f}")
            
            st.divider()
            
            # Cash Transactions
            st.subheader("💵 Cash Transactions (Single Entry)")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Cash Receipt**")
                cash_receipt_amt = st.number_input("Amount", min_value=0.0, step=100.0, key="cash_rec")
                cash_receipt_desc = st.text_input("Description", key="cash_rec_desc", placeholder="e.g., Customer payment")
                customer_option = st.selectbox("Link to Customer (Optional)", ["None"] + [f"{c['full_name']} ({cid})" for cid, c in get_all_customers().items()], key="cash_rec_cust")
                
                if st.button("💰 Record Cash Receipt", key="cash_rec_btn"):
                    if cash_receipt_amt > 0:
                        customer_id = None
                        if customer_option != "None":
                            customer_id = customer_option.split('(')[-1].replace(')', '')
                        success, msg = record_cash_transaction('RECEIPT', cash_receipt_amt, cash_receipt_desc, user['username'], customer_id)
                        if success:
                            st.success(msg)
                            st.balloons()
                        else:
                            st.error(msg)
                    else:
                        st.warning("Enter an amount greater than zero")
            
            with col2:
                st.markdown("**Cash Payment**")
                cash_payment_amt = st.number_input("Amount", min_value=0.0, step=100.0, key="cash_pay")
                cash_payment_desc = st.text_input("Description", key="cash_pay_desc", placeholder="e.g., Office supplies")
                customer_option2 = st.selectbox("Link to Customer (Optional)", ["None"] + [f"{c['full_name']} ({cid})" for cid, c in get_all_customers().items()], key="cash_pay_cust")
                
                if st.button("💸 Record Cash Payment", key="cash_pay_btn"):
                    if cash_payment_amt > 0:
                        if cash_payment_amt > cash_balance:
                            st.error(f"Insufficient cash balance. Available: ₹{cash_balance:,.2f}")
                        else:
                            customer_id = None
                            if customer_option2 != "None":
                                customer_id = customer_option2.split('(')[-1].replace(')', '')
                            success, msg = record_cash_transaction('PAYMENT', cash_payment_amt, cash_payment_desc, user['username'], customer_id)
                            if success:
                                st.success(msg)
                            else:
                                st.error(msg)
                    else:
                        st.warning("Enter an amount greater than zero")
            
            st.divider()
            
            # Bank Transactions
            st.subheader("🏦 Bank Transactions (Single Entry)")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Bank Deposit**")
                bank_account = st.selectbox("Bank Account", ['1100 - Bank Savings', '1200 - Bank Current'], key="bank_dep_acc")
                bank_acc_code = bank_account.split(' - ')[0]
                bank_dep_amt = st.number_input("Amount", min_value=0.0, step=100.0, key="bank_dep")
                bank_dep_desc = st.text_input("Description", key="bank_dep_desc", placeholder="e.g., Cash deposit")
                
                if st.button("🏦 Record Bank Deposit", key="bank_dep_btn"):
                    if bank_dep_amt > 0:
                        success, msg = record_bank_transaction(bank_acc_code, 'DEPOSIT', bank_dep_amt, bank_dep_desc, user['username'])
                        if success:
                            st.success(msg)
                            st.balloons()
                        else:
                            st.error(msg)
                    else:
                        st.warning("Enter an amount greater than zero")
            
            with col2:
                st.markdown("**Bank Withdrawal**")
                bank_account2 = st.selectbox("Bank Account", ['1100 - Bank Savings', '1200 - Bank Current'], key="bank_wd_acc")
                bank_acc_code2 = bank_account2.split(' - ')[0]
                bank_wd_amt = st.number_input("Amount", min_value=0.0, step=100.0, key="bank_wd")
                bank_wd_desc = st.text_input("Description", key="bank_wd_desc", placeholder="e.g., ATM withdrawal")
                current_bank_balance = get_account_balance(bank_acc_code2)
                st.caption(f"Available balance: ₹{current_bank_balance:,.2f}")
                
                if st.button("💸 Record Bank Withdrawal", key="bank_wd_btn"):
                    if bank_wd_amt > 0:
                        if bank_wd_amt > current_bank_balance:
                            st.error(f"Insufficient balance. Available: ₹{current_bank_balance:,.2f}")
                        else:
                            success, msg = record_bank_transaction(bank_acc_code2, 'WITHDRAWAL', bank_wd_amt, bank_wd_desc, user['username'])
                            if success:
                                st.success(msg)
                            else:
                                st.error(msg)
                    else:
                        st.warning("Enter an amount greater than zero")
            
            st.divider()
            
            # Transfer between Cash and Bank
            st.subheader("🔄 Transfer Between Cash & Bank (Double Entry)")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                transfer_from = st.selectbox("Transfer From", ['CASH (1000)', 'BANK_SAVINGS (1100)', 'BANK_CURRENT (1200)'], key="transfer_from")
                from_code = transfer_from.split('(')[-1].replace(')', '')
            with col2:
                transfer_to = st.selectbox("Transfer To", ['CASH (1000)', 'BANK_SAVINGS (1100)', 'BANK_CURRENT (1200)'], key="transfer_to")
                to_code = transfer_to.split('(')[-1].replace(')', '')
            with col3:
                transfer_amt = st.number_input("Amount", min_value=0.0, step=100.0, key="transfer_amt")
            
            if from_code == to_code:
                st.warning("⚠️ From and To accounts must be different")
            
            if st.button("🔄 Execute Transfer", key="transfer_btn"):
                if from_code == to_code:
                    st.error("Cannot transfer to the same account")
                elif transfer_amt <= 0:
                    st.warning("Enter an amount greater than zero")
                else:
                    # Check if source has sufficient balance
                    source_balance = get_account_balance(from_code)
                    if source_balance < transfer_amt:
                        st.error(f"Insufficient balance in source account. Available: ₹{source_balance:,.2f}")
                    else:
                        # Use double entry for transfer
                        success, msg = double_entry(from_code, to_code, transfer_amt, 
                                                   f"Transfer from {from_code} to {to_code}", user['username'])
                        if success:
                            st.success(msg)
                            st.balloons()
                        else:
                            st.error(msg)
            
            st.divider()
            
            # Transaction History
            st.subheader("📜 Recent Cash & Bank Transactions")
            
            # Show cash transactions
            cash_txns = get_cash_transactions(50)
            if cash_txns:
                df_cash = pd.DataFrame(cash_txns, columns=['Date', 'Type', 'Amount', 'Description', 'Balance', 'User', 'Customer'])
                st.markdown("**Cash Transactions**")
                st.dataframe(df_cash, use_container_width=True, hide_index=True)
            else:
                st.info("No cash transactions yet")
        
        # ---------- TAB 2: CUSTOMERS & KYC ----------
        with tab2:
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
        
        # ---------- TAB 4: JOURNAL ENTRIES ----------
        with tab4:
            st.header("📝 Journal Entries")
            
            try:
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
                    
                    # Show summary statistics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        total_debits = sum(row[4] for row in results if row[3] == 'DEBIT')
                        st.metric("Total Debits", f"₹{total_debits:,.2f}")
                    with col2:
                        total_credits = sum(row[4] for row in results if row[3] == 'CREDIT')
                        st.metric("Total Credits", f"₹{total_credits:,.2f}")
                    with col3:
                        if abs(total_debits - total_credits) < 0.01:
                            st.success("✅ Balanced")
                        else:
                            st.error(f"❌ Difference: ₹{total_debits - total_credits:,.2f}")
                else:
                    st.info("No journal entries yet. Start by recording cash, bank, or customer transactions.")
            except Exception as e:
                st.error(f"Error loading journal entries: {str(e)}")
                print(f"Error in journal entries: {e}")
                print(traceback.format_exc())
        
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
        
        # ---------- TAB 6: HEAD MANAGEMENT ----------
        with tab6:
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
                                    # Pass None if daily_limit is 0
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
