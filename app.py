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
        
        # Customers table
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
        
        # Check if default accounts exist
        cursor.execute("SELECT COUNT(*) FROM accounts")
        if cursor.fetchone()[0] == 0:
            current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            default_accounts = [
                ('1000', 'CASH', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
                ('1001', 'PETTY_CASH', 'ASSET', 0, 10000, None, None, current_date, 1, 'system'),
                ('1100', 'BANK_SAVINGS', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
                ('1200', 'BANK_CURRENT', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
                ('1300', 'FD', 'ASSET', 0, None, None, 7.0, current_date, 1, 'system'),
                ('1400', 'DAILY_COLLECTION', 'ASSET', 0, 50000, None, None, current_date, 1, 'system'),
                ('1500', 'SUNDRY_DEBTORS', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
                ('1600', 'LOANS_ADVANCED', 'ASSET', 0, None, None, None, current_date, 1, 'system'),
                ('2100', 'CUSTOMER_DEPOSITS', 'LIABILITY', 0, None, None, None, current_date, 1, 'system'),
                ('2200', 'FD_LIABILITY', 'LIABILITY', 0, None, None, None, current_date, 1, 'system'),
                ('2300', 'SUNDRY_CREDITORS', 'LIABILITY', 0, None, None, None, current_date, 1, 'system'),
                ('2400', 'LOANS_TAKEN', 'LIABILITY', 0, None, None, None, current_date, 1, 'system'),
                ('2500', 'SB_INTEREST_PAYABLE', 'LIABILITY', 0, None, None, None, current_date, 1, 'system'),
                ('3100', 'CAPITAL', 'EQUITY', 1000000, None, None, None, current_date, 1, 'system'),
                ('3200', 'RETAINED_EARNINGS', 'EQUITY', 0, None, None, None, current_date, 1, 'system'),
                ('4100', 'INTEREST_INCOME', 'INCOME', 0, None, None, None, current_date, 1, 'system'),
                ('4200', 'SERVICE_CHARGE', 'INCOME', 0, None, None, None, current_date, 1, 'system'),
                ('4300', 'COMMISSION_INCOME', 'INCOME', 0, None, None, None, current_date, 1, 'system'),
                ('4400', 'RENT_INCOME', 'INCOME', 0, None, None, None, current_date, 1, 'system'),
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
                    INSERT INTO accounts (account_code, account_name, account_type, balance, daily_limit, maturity_date, interest_rate, created_date, is_active, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', acc)
        
        conn.close()
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
        return False, str(e)

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
                update_account_balance(entry['account_code'], entry['amount'], is_debit=True)
            else:
                update_account_balance(entry['account_code'], entry['amount'], is_debit=False)
            cursor.execute('INSERT INTO journal_entries (date, account_code, account_name, entry_type, amount, description, ref_no, username, voucher_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                          (voucher_date, entry['account_code'], entry['account_name'], entry['entry_type'], entry['amount'], description, voucher_number, username, voucher_number))
        conn.commit()
        conn.close()
        return True, f"Voucher {voucher_number} saved successfully"
    except Exception as e:
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
                'opening_balance': get_safe_float(row[4]),
                'current_balance': get_safe_float(row[5]),
                'interest_rate': get_safe_float(row[6], 3.5),
                'interest_payable': get_safe_float(row[7]),
                'account_status': row[8] if row[8] else 'ACTIVE',
                'opening_date': row[9] if row[9] else ''
            })
        return accounts
    except Exception as e:
        print(f"Error in get_all_sb_accounts: {e}")
        return []

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
            INSERT INTO sb_transactions (transaction_id, account_number, transaction_date, value_date, particulars, credit, balance, transaction_type, created_by, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transaction_id, account_number, transaction_date, value_date, particulars, amount, new_balance, 'DEPOSIT', username, transaction_date))
        conn.commit()
        conn.close()
        return True, f"Deposited ₹{amount:,.2f} on {value_date}. New balance: ₹{new_balance:,.2f}"
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
            INSERT INTO sb_transactions (transaction_id, account_number, transaction_date, value_date, particulars, debit, balance, transaction_type, created_by, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transaction_id, account_number, transaction_date, value_date, particulars, amount, new_balance, 'WITHDRAWAL', username, transaction_date))
        conn.commit()
        conn.close()
        return True, f"Withdrawn ₹{amount:,.2f} on {value_date}. New balance: ₹{new_balance:,.2f}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def calculate_and_credit_interest(account_number, username):
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        cursor = conn.cursor()
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
        new_balance = current_balance + interest
        new_interest_payable = get_safe_float(interest_payable) + interest
        cursor.execute('UPDATE sb_accounts SET current_balance = ?, interest_payable = ?, last_interest_credited = ? WHERE account_number = ?',
                      (new_balance, new_interest_payable, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), account_number))
        transaction_id = generate_transaction_id()
        transaction_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        value_date = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            INSERT INTO sb_transactions (transaction_id, account_number, transaction_date, value_date, particulars, credit, balance, transaction_type, created_by, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transaction_id, account_number, transaction_date, value_date, f'Quarterly Interest @ {interest_rate}%', interest, new_balance, 'INTEREST', 'SYSTEM', transaction_date))
        voucher_number = generate_voucher_number('INTEREST')
        cursor.execute('INSERT INTO journal_entries (date, account_code, account_name, entry_type, amount, description, ref_no, username, voucher_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                      (value_date, '5999', 'SB_INTEREST_EXPENSE', 'DEBIT', interest, f'Interest on SB Account {account_number}', voucher_number, username, voucher_number))
        cursor.execute('INSERT INTO journal_entries (date, account_code, account_name, entry_type, amount, description, ref_no, username, voucher_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                      (value_date, '2500', 'SB_INTEREST_PAYABLE', 'CREDIT', interest, f'Interest on SB Account {account_number}', voucher_number, username, voucher_number))
        cursor.execute('UPDATE accounts SET balance = balance + ? WHERE account_code = "5999"', (interest,))
        cursor.execute('UPDATE accounts SET balance = balance + ? WHERE account_code = "2500"', (interest,))
        cursor.execute('''
            INSERT INTO sb_interest_history (account_number, quarter_start, quarter_end, interest_rate, average_balance, interest_amount, interest_payable, credited_date, voucher_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (account_number, datetime.now().replace(day=1).strftime('%Y-%m-%d'), datetime.now().strftime('%Y-%m-%d'), interest_rate, current_balance, interest, interest, transaction_date, voucher_number))
        conn.commit()
        conn.close()
        return True, f"Interest ₹{interest:,.2f} credited at {interest_rate}%"
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
            trial_balance.append({'Account Code': code, 'Account Name': data['account_name'], 'Account Type': acc_type, 'Debit': balance, 'Credit': 0})
            total_debits += balance
        else:
            trial_balance.append({'Account Code': code, 'Account Name': data['account_name'], 'Account Type': acc_type, 'Debit': 0, 'Credit': balance})
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
    return {'assets': assets, 'liabilities': liabilities, 'equity': equity, 'total_assets': sum(assets.values()), 'total_liabilities': sum(liabilities.values()), 'total_equity': sum(equity.values())}

def get_profit_loss():
    accounts = get_all_accounts()
    income, expenses = {}, {}
    for code, data in accounts.items():
        if data['account_type'] == 'INCOME':
            income[data['account_name']] = data['balance']
        elif data['account_type'] == 'EXPENSE':
            expenses[data['account_name']] = data['balance']
    return {'income': income, 'expenses': expenses, 'total_income': sum(income.values()), 'total_expenses': sum(expenses.values()), 'net_profit': sum(income.values()) - sum(expenses.values())}

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
                st.success(msg) if success else st.error(msg)
                if success:
                    st.rerun()

def render_sb_report():
    st.subheader("📊 SB Account Report")
    accounts = get_all_sb_accounts()
    if not accounts:
        st.warning("No SB accounts found.")
        return
    selected = st.selectbox("Select Account", [f"{a['account_number']} - {a['customer_name']}" for a in accounts])
    if selected:
        acc_no = selected.split(' - ')[0]
        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input("From Date", value=datetime.now().date() - timedelta(days=30))
        with col2:
            to_date = st.date_input("To Date", value=datetime.now().date())
        if st.button("📄 Generate Report"):
            account = get_sb_account(acc_no)
            if account:
                st.markdown("### 📋 Account Summary")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Account", account['account_number'])
                    st.metric("Customer", account['customer_name'])
                with col2:
                    st.metric("Opening Balance", f"₹{account['opening_balance']:,.2f}")
                    st.metric("Current Balance", f"₹{account['current_balance']:,.2f}")
                with col3:
                    st.metric("Interest Rate", f"{account['interest_rate']}%")
                    st.metric("Interest Payable", f"₹{account['interest_payable']:,.2f}")

def main():
    try:
        if not os.path.exists(DB_FILE):
            init_database()
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
        tabs = ["📝 Vouchers", "🏦 SB Accounts", "📊 Reports", "📋 Trial Balance"]
        tab1, tab2, tab3, tab4 = st.tabs(tabs)
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
            st.header("🏦 Savings Bank Accounts")
            sbtab1, sbtab2 = st.tabs(["💰 Operations", "📊 Reports"])
            with sbtab1:
                render_sb_operations()
            with sbtab2:
                render_sb_report()
        with tab3:
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
        with tab4:
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
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
