import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import uuid
import os

# Page configuration
st.set_page_config(page_title="Complete Banking System", page_icon="🏦", layout="wide", initial_sidebar_state="expanded")

# ============================================
# CSS
# ============================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0d1128 100%); }
    .main-header { font-size: 2.8rem; background: linear-gradient(120deg, #667eea, #764ba2, #f093fb); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; margin-bottom: 2rem; font-weight: 700; }
    .sub-header { font-size: 1.6rem; color: #a78bfa; margin-bottom: 1.5rem; font-weight: 600; border-bottom: 2px solid #2d2b55; padding-bottom: 0.5rem; }
    div[data-testid="stForm"] { background: linear-gradient(135deg, rgba(26, 31, 58, 0.95), rgba(45, 43, 85, 0.95)); border: 1px solid rgba(102, 126, 234, 0.3); padding: 2rem; border-radius: 20px; }
    .stButton > button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important; color: white !important; border: none !important; border-radius: 12px !important; padding: 0.75rem 2rem !important; font-weight: 600 !important; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0a0e27 0%, #1a1f3a 100%) !important; }
    .badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.85rem; font-weight: 600; }
    .badge-success { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; }
    .badge-warning { background: rgba(245, 158, 11, 0.2); color: #fcd34d; }
    .badge-info { background: rgba(59, 130, 246, 0.2); color: #93c5fd; }
    .info-box { padding: 1rem; background: rgba(59, 130, 246, 0.15); border-left: 4px solid #3b82f6; border-radius: 8px; color: #93c5fd; margin: 1rem 0; }
    </style>
""", unsafe_allow_html=True)

# ============================================
# DATABASE
# ============================================
class DatabaseLayer:
    def __init__(self):
        self.db_path = 'complete_banking.db'
    
    def _ensure_column(self, c, table, col_name, col_type):
        try:
            c.execute(f"SELECT {col_name} FROM {table} LIMIT 1")
        except:
            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
            except:
                pass
    
    def initialize_database(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute("PRAGMA foreign_keys=ON")
        
        # Users
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, full_name TEXT NOT NULL, email TEXT,
            role TEXT NOT NULL, is_active INTEGER DEFAULT 1,
            last_login TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS user_sessions (
            session_id TEXT PRIMARY KEY, user_id INTEGER,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, logout_time TIMESTAMP
        )''')
        
        # Customers
        c.execute('''CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
            date_of_birth DATE, phone TEXT, email TEXT, address TEXT, city TEXT, state TEXT,
            kyc_status TEXT DEFAULT 'Pending', created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # SB Accounts
        c.execute('''CREATE TABLE IF NOT EXISTS sb_accounts (
            account_number TEXT PRIMARY KEY, customer_id TEXT,
            balance REAL DEFAULT 0, interest_rate REAL DEFAULT 4.0,
            opened_date DATE, status TEXT DEFAULT 'Active',
            created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # FD Accounts
        c.execute('''CREATE TABLE IF NOT EXISTS fd_accounts (
            fd_id TEXT PRIMARY KEY, customer_id TEXT, sb_account TEXT,
            principal_amount REAL, interest_rate REAL, tenure_months INTEGER,
            start_date DATE, maturity_date DATE, maturity_amount REAL,
            status TEXT DEFAULT 'Active', created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # RD Accounts
        c.execute('''CREATE TABLE IF NOT EXISTS rd_accounts (
            rd_id TEXT PRIMARY KEY, customer_id TEXT, sb_account TEXT,
            monthly_amount REAL, interest_rate REAL, tenure_months INTEGER,
            start_date DATE, maturity_date DATE, maturity_amount REAL,
            installments_paid INTEGER DEFAULT 0, total_installments INTEGER,
            status TEXT DEFAULT 'Active', created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # RD Installments
        c.execute('''CREATE TABLE IF NOT EXISTS rd_installments (
            installment_id INTEGER PRIMARY KEY AUTOINCREMENT, rd_id TEXT,
            installment_number INTEGER, due_date DATE, paid_date DATE,
            amount REAL, status TEXT DEFAULT 'Pending'
        )''')
        
        # Journal Vouchers
        c.execute('''CREATE TABLE IF NOT EXISTS journal_vouchers (
            voucher_id TEXT PRIMARY KEY, voucher_type TEXT, voucher_date DATE,
            narration TEXT, total_amount REAL, status TEXT DEFAULT 'Approved',
            created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Journal Entries
        c.execute('''CREATE TABLE IF NOT EXISTS journal_entries (
            entry_id INTEGER PRIMARY KEY AUTOINCREMENT, voucher_id TEXT,
            account_head TEXT, debit_amount REAL DEFAULT 0, credit_amount REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Chart of Accounts
        c.execute('''CREATE TABLE IF NOT EXISTS chart_of_accounts (
            account_head TEXT PRIMARY KEY, account_name TEXT, account_type TEXT,
            category TEXT, is_active INTEGER DEFAULT 1
        )''')
        
        # SB Transactions
        c.execute('''CREATE TABLE IF NOT EXISTS sb_transactions (
            transaction_id TEXT PRIMARY KEY, account_number TEXT,
            transaction_type TEXT, amount REAL, balance_before REAL, balance_after REAL,
            description TEXT, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Interest Calculations
        c.execute('''CREATE TABLE IF NOT EXISTS interest_calculations (
            calc_id INTEGER PRIMARY KEY AUTOINCREMENT, account_number TEXT,
            interest_period_start DATE, interest_period_end DATE,
            minimum_balance REAL, interest_rate REAL, interest_amount REAL,
            is_credited INTEGER DEFAULT 0, calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Default Users
        c.execute("SELECT COUNT(*) FROM users")
        if c.fetchone()[0] == 0:
            users = [
                ('admin', 'admin123', 'System Administrator', 'admin@bank.com', 'Admin'),
                ('manager', 'manager123', 'Branch Manager', 'manager@bank.com', 'Manager'),
                ('user1', 'user123', 'Bank User', 'user@bank.com', 'User'),
            ]
            for username, password, full_name, email, role in users:
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                c.execute("INSERT INTO users (username, password_hash, full_name, email, role) VALUES (?, ?, ?, ?, ?)",
                         (username, password_hash, full_name, email, role))
        
        # Default Chart of Accounts
        c.execute("SELECT COUNT(*) FROM chart_of_accounts")
        if c.fetchone()[0] == 0:
            accounts = [
                ('CASH_IN_HAND', 'Cash in Hand', 'Asset', 'Current Asset'),
                ('FD_INVESTMENTS', 'FD Investments', 'Asset', 'Investment'),
                ('RD_INVESTMENTS', 'RD Investments', 'Asset', 'Investment'),
                ('SB_ACCOUNTS', 'Savings Bank Accounts', 'Liability', 'Deposits'),
                ('FD_ACCOUNTS', 'Fixed Deposit Accounts', 'Liability', 'Deposits'),
                ('RD_ACCOUNTS', 'Recurring Deposit Accounts', 'Liability', 'Deposits'),
                ('SHARE_CAPITAL', 'Share Capital', 'Equity', 'Capital'),
                ('RESERVES', 'Reserves & Surplus', 'Equity', 'Reserves'),
                ('INTEREST_ON_SB', 'Interest on SB', 'Expense', 'Interest'),
                ('INTEREST_ON_FD', 'Interest on FD', 'Expense', 'Interest'),
                ('INTEREST_ON_RD', 'Interest on RD', 'Expense', 'Interest'),
                ('SALARY', 'Salary', 'Expense', 'Staff'),
                ('RENT', 'Rent', 'Expense', 'Office'),
                ('COMMISSION', 'Commission Income', 'Income', 'Fees'),
            ]
            for acc in accounts:
                c.execute("INSERT OR IGNORE INTO chart_of_accounts (account_head, account_name, account_type, category) VALUES (?, ?, ?, ?)", acc)
        
        conn.commit()
        return conn
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

db = DatabaseLayer()

# ============================================
# AUTH
# ============================================
class AuthModule:
    @staticmethod
    def authenticate(username, password):
        conn = db.get_connection(); c = conn.cursor()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        c.execute("SELECT * FROM users WHERE username = ? AND password_hash = ? AND is_active = 1", (username, password_hash))
        user = c.fetchone()
        if user:
            session_id = str(uuid.uuid4())
            c.execute("INSERT INTO user_sessions (session_id, user_id) VALUES (?, ?)", (session_id, user[0]))
            conn.commit(); conn.close()
            return {'user_id': user[0], 'username': user[1], 'full_name': user[3], 'role': user[5], 'email': user[4]}
        conn.close()
        return None

# ============================================
# SB ACCOUNT MODULE
# ============================================
class SBAccountModule:
    @staticmethod
    def generate_account_number():
        return f"SB{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
    
    @staticmethod
    def open_account(customer_id, initial_deposit=0.0, interest_rate=4.0, created_by=None):
        conn = db.get_connection(); c = conn.cursor()
        try:
            c.execute("SELECT kyc_status FROM customers WHERE customer_id = ?", (customer_id,))
            cust = c.fetchone()
            if not cust: conn.close(); return False, "Customer not found"
            if cust[0] != 'Verified': conn.close(); return False, "KYC not verified"
            
            acc_num = SBAccountModule.generate_account_number()
            today = datetime.now().date()
            c.execute("INSERT INTO sb_accounts (account_number, customer_id, balance, interest_rate, opened_date, created_by) VALUES (?, ?, ?, ?, ?, ?)",
                     (acc_num, customer_id, initial_deposit, interest_rate, today, created_by))
            
            if initial_deposit > 0:
                txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
                c.execute("INSERT INTO sb_transactions (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by) VALUES (?, ?, 'Deposit', ?, 0, ?, 'Initial Deposit', ?)",
                         (txn_id, acc_num, initial_deposit, initial_deposit, created_by))
                # Accounting: Cash IN (Debit), SB Liability UP (Credit)
                JournalVoucherModule.create_auto_voucher('Receipt', today, f'Initial deposit SB {acc_num}', created_by,
                    [('CASH_IN_HAND', initial_deposit, 0), ('SB_ACCOUNTS', 0, initial_deposit)])
            
            conn.commit(); conn.close()
            return True, acc_num
        except Exception as e:
            conn.rollback(); conn.close()
            return False, str(e)
    
    @staticmethod
    def deposit(account_number, amount, description, created_by):
        conn = db.get_connection(); c = conn.cursor()
        try:
            c.execute("SELECT balance FROM sb_accounts WHERE account_number = ? AND status = 'Active'", (account_number,))
            acc = c.fetchone()
            if not acc: conn.close(); return False, "Account not found"
            
            old_bal, new_bal = acc[0], acc[0] + amount
            c.execute("UPDATE sb_accounts SET balance = ? WHERE account_number = ?", (new_bal, account_number))
            
            txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
            c.execute("INSERT INTO sb_transactions (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by) VALUES (?, ?, 'Deposit', ?, ?, ?, ?, ?)",
                     (txn_id, account_number, amount, old_bal, new_bal, description, created_by))
            # Accounting: Cash IN (Debit), SB Liability UP (Credit)
            JournalVoucherModule.create_auto_voucher('Receipt', datetime.now().date(), f'Deposit {account_number}', created_by,
                [('CASH_IN_HAND', amount, 0), ('SB_ACCOUNTS', 0, amount)])
            
            conn.commit(); conn.close()
            return True, f"Deposited ₹{amount:,.2f}. Balance: ₹{new_bal:,.2f}"
        except Exception as e:
            conn.rollback(); conn.close()
            return False, str(e)
    
    @staticmethod
    def withdraw(account_number, amount, description, created_by):
        conn = db.get_connection(); c = conn.cursor()
        try:
            c.execute("SELECT balance FROM sb_accounts WHERE account_number = ? AND status = 'Active'", (account_number,))
            acc = c.fetchone()
            if not acc: conn.close(); return False, "Account not found"
            if acc[0] < amount: conn.close(); return False, f"Insufficient balance. Available: ₹{acc[0]:,.2f}"
            
            old_bal, new_bal = acc[0], acc[0] - amount
            c.execute("UPDATE sb_accounts SET balance = ? WHERE account_number = ?", (new_bal, account_number))
            
            txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
            c.execute("INSERT INTO sb_transactions (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by) VALUES (?, ?, 'Withdrawal', ?, ?, ?, ?, ?)",
                     (txn_id, account_number, amount, old_bal, new_bal, description, created_by))
            # Accounting: SB Liability DOWN (Debit), Cash OUT (Credit)
            JournalVoucherModule.create_auto_voucher('Payment', datetime.now().date(), f'Withdrawal {account_number}', created_by,
                [('SB_ACCOUNTS', amount, 0), ('CASH_IN_HAND', 0, amount)])
            
            conn.commit(); conn.close()
            return True, f"Withdrew ₹{amount:,.2f}. Balance: ₹{new_bal:,.2f}"
        except Exception as e:
            conn.rollback(); conn.close()
            return False, str(e)
    
    @staticmethod
    def calculate_quarterly_interest(created_by=None):
        conn = db.get_connection(); c = conn.cursor()
        try:
            today = datetime.now().date()
            quarter_start = today - relativedelta(months=3)
            
            c.execute("""SELECT account_number, balance, interest_rate FROM sb_accounts 
                WHERE status = 'Active' AND account_number NOT IN (
                    SELECT DISTINCT account_number FROM interest_calculations 
                    WHERE interest_period_start = ? AND is_credited = 1)""", (quarter_start,))
            accounts = c.fetchall()
            if not accounts: conn.close(); return False, "No eligible accounts"
            
            results = []
            for acc in accounts:
                acc_num, balance, rate = acc
                c.execute("SELECT COALESCE(MIN(balance_after), ?) FROM sb_transactions WHERE account_number = ? AND created_at >= ? AND created_at <= ?",
                         (balance, acc_num, quarter_start, today))
                min_bal = c.fetchone()[0]
                
                interest = round(min_bal * (rate / 100 / 365) * (today - quarter_start).days, 2)
                
                if interest > 0:
                    new_bal = balance + interest
                    c.execute("UPDATE sb_accounts SET balance = ? WHERE account_number = ?", (new_bal, acc_num))
                    
                    txn_id = f"INT{uuid.uuid4().hex[:8].upper()}"
                    c.execute("INSERT INTO sb_transactions (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by) VALUES (?, ?, 'Interest_Credit', ?, ?, ?, 'Quarterly Interest', ?)",
                             (txn_id, acc_num, interest, balance, new_bal, created_by))
                    # Accounting: Interest Expense UP (Debit), SB Liability UP (Credit)
                    JournalVoucherModule.create_auto_voucher('Interest', today, f'Interest {acc_num}', created_by,
                        [('INTEREST_ON_SB', interest, 0), ('SB_ACCOUNTS', 0, interest)])
                    
                    c.execute("INSERT INTO interest_calculations (account_number, interest_period_start, interest_period_end, minimum_balance, interest_rate, interest_amount, is_credited) VALUES (?, ?, ?, ?, ?, ?, 1)",
                             (acc_num, quarter_start, today, min_bal, rate, interest))
                    
                    results.append({'Account': acc_num, 'Interest': f"₹{interest:,.2f}", 'New Balance': f"₹{new_bal:,.2f}"})
            
            conn.commit(); conn.close()
            return True, results
        except Exception as e:
            conn.rollback(); conn.close()
            return False, str(e)

# ============================================
# FD ACCOUNT MODULE
# ============================================
class FDAccountModule:
    @staticmethod
    def generate_fd_id():
        return f"FD{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}"
    
    @staticmethod
    def open_fd(customer_id, sb_account, principal, interest_rate, tenure_months, created_by=None):
        conn = db.get_connection(); c = conn.cursor()
        try:
            c.execute("SELECT balance FROM sb_accounts WHERE account_number = ? AND customer_id = ? AND status = 'Active'", (sb_account, customer_id))
            sb = c.fetchone()
            if not sb: conn.close(); return False, "SB Account not found"
            if sb[0] < principal: conn.close(); return False, f"Insufficient balance. Available: ₹{sb[0]:,.2f}"
            
            fd_id = FDAccountModule.generate_fd_id()
            start_date = datetime.now().date()
            maturity_date = start_date + relativedelta(months=tenure_months)
            maturity_amount = round(principal * (1 + (interest_rate/1200) * tenure_months), 2)
            
            c.execute("INSERT INTO fd_accounts (fd_id, customer_id, sb_account, principal_amount, interest_rate, tenure_months, start_date, maturity_date, maturity_amount, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (fd_id, customer_id, sb_account, principal, interest_rate, tenure_months, start_date, maturity_date, maturity_amount, created_by))
            
            old_bal, new_bal = sb[0], sb[0] - principal
            c.execute("UPDATE sb_accounts SET balance = ? WHERE account_number = ?", (new_bal, sb_account))
            
            txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
            c.execute("INSERT INTO sb_transactions (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by) VALUES (?, ?, 'FD_Transfer', ?, ?, ?, ?, ?)",
                     (txn_id, sb_account, principal, old_bal, new_bal, f'FD Creation - {fd_id}', created_by))
            # Accounting: FD Asset UP (Debit), SB Liability DOWN (Debit)
            JournalVoucherModule.create_auto_voucher('FD', start_date, f'FD Creation {fd_id}', created_by,
                [('FD_INVESTMENTS', principal, 0), ('SB_ACCOUNTS', principal, 0)])
            
            conn.commit(); conn.close()
            return True, fd_id
        except Exception as e:
            conn.rollback(); conn.close()
            return False, str(e)
    
    @staticmethod
    def mature_fd(fd_id, created_by=None):
        conn = db.get_connection(); c = conn.cursor()
        try:
            c.execute("SELECT * FROM fd_accounts WHERE fd_id = ? AND status = 'Active'", (fd_id,))
            fd = c.fetchone()
            if not fd: conn.close(); return False, "FD not found"
            
            maturity_amount, sb_account, principal = fd[8], fd[2], fd[3]
            interest_earned = maturity_amount - principal
            
            c.execute("UPDATE fd_accounts SET status = 'Matured' WHERE fd_id = ?", (fd_id,))
            
            c.execute("SELECT balance FROM sb_accounts WHERE account_number = ?", (sb_account,))
            old_bal = c.fetchone()[0]
            new_bal = old_bal + maturity_amount
            c.execute("UPDATE sb_accounts SET balance = ? WHERE account_number = ?", (new_bal, sb_account))
            
            txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
            c.execute("INSERT INTO sb_transactions (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by) VALUES (?, ?, 'FD_Transfer', ?, ?, ?, ?, ?)",
                     (txn_id, sb_account, maturity_amount, old_bal, new_bal, f'FD Maturity - {fd_id}', created_by))
            # Accounting: FD Asset DOWN (Credit), SB Liability UP (Credit) + Interest expense
            JournalVoucherModule.create_auto_voucher('FD', datetime.now().date(), f'FD Maturity {fd_id}', created_by,
                [('FD_INVESTMENTS', 0, principal), ('SB_ACCOUNTS', 0, principal),
                 ('INTEREST_ON_FD', interest_earned, 0), ('SB_ACCOUNTS', 0, interest_earned)])
            
            conn.commit(); conn.close()
            return True, f"FD matured. ₹{maturity_amount:,.2f} credited"
        except Exception as e:
            conn.rollback(); conn.close()
            return False, str(e)

# ============================================
# RD ACCOUNT MODULE
# ============================================
class RDAccountModule:
    @staticmethod
    def generate_rd_id():
        return f"RD{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}"
    
    @staticmethod
    def open_rd(customer_id, sb_account, monthly_amount, interest_rate, tenure_months, created_by=None):
        conn = db.get_connection(); c = conn.cursor()
        try:
            c.execute("SELECT balance FROM sb_accounts WHERE account_number = ? AND customer_id = ? AND status = 'Active'", (sb_account, customer_id))
            sb = c.fetchone()
            if not sb: conn.close(); return False, "SB Account not found"
            
            rd_id = RDAccountModule.generate_rd_id()
            start_date = datetime.now().date()
            
            r = interest_rate / 400; n = tenure_months / 3
            maturity_amount = round(monthly_amount * (((1 + r) ** n - 1) / r) * (1 + r), 2)
            
            c.execute("INSERT INTO rd_accounts (rd_id, customer_id, sb_account, monthly_amount, interest_rate, tenure_months, start_date, maturity_date, maturity_amount, total_installments, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (rd_id, customer_id, sb_account, monthly_amount, interest_rate, tenure_months, start_date, start_date + relativedelta(months=tenure_months), maturity_amount, tenure_months, created_by))
            
            for i in range(tenure_months):
                c.execute("INSERT INTO rd_installments (rd_id, installment_number, due_date, amount) VALUES (?, ?, ?, ?)",
                         (rd_id, i+1, start_date + relativedelta(months=i+1), monthly_amount))
            
            if sb[0] >= monthly_amount:
                old_bal, new_bal = sb[0], sb[0] - monthly_amount
                c.execute("UPDATE sb_accounts SET balance = ? WHERE account_number = ?", (new_bal, sb_account))
                c.execute("UPDATE rd_installments SET status = 'Paid', paid_date = ? WHERE rd_id = ? AND installment_number = 1", (start_date, rd_id))
                c.execute("UPDATE rd_accounts SET installments_paid = 1 WHERE rd_id = ?", (rd_id,))
                
                txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
                c.execute("INSERT INTO sb_transactions (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by) VALUES (?, ?, 'RD_Transfer', ?, ?, ?, ?, ?)",
                         (txn_id, sb_account, monthly_amount, old_bal, new_bal, f'RD Installment 1/{tenure_months} - {rd_id}', created_by))
                # Accounting: RD Asset UP (Debit), SB Liability DOWN (Debit)
                JournalVoucherModule.create_auto_voucher('RD', start_date, f'RD {rd_id} Installment 1', created_by,
                    [('RD_INVESTMENTS', monthly_amount, 0), ('SB_ACCOUNTS', monthly_amount, 0)])
            
            conn.commit(); conn.close()
            return True, rd_id
        except Exception as e:
            conn.rollback(); conn.close()
            return False, str(e)
    
    @staticmethod
    def pay_installment(rd_id, created_by=None):
        conn = db.get_connection(); c = conn.cursor()
        try:
            c.execute("SELECT * FROM rd_accounts WHERE rd_id = ? AND status = 'Active'", (rd_id,))
            rd = c.fetchone()
            if not rd: conn.close(); return False, "RD not found"
            
            c.execute("SELECT * FROM rd_installments WHERE rd_id = ? AND status = 'Pending' ORDER BY installment_number LIMIT 1", (rd_id,))
            inst = c.fetchone()
            if not inst: conn.close(); return False, "All installments paid"
            
            c.execute("SELECT balance FROM sb_accounts WHERE account_number = ?", (rd[2],))
            sb_bal = c.fetchone()[0]
            if sb_bal < rd[3]: conn.close(); return False, "Insufficient balance"
            
            new_bal = sb_bal - rd[3]
            c.execute("UPDATE sb_accounts SET balance = ? WHERE account_number = ?", (new_bal, rd[2]))
            c.execute("UPDATE rd_installments SET status = 'Paid', paid_date = ? WHERE rd_id = ? AND installment_number = ?", (datetime.now().date(), rd_id, inst[1]))
            c.execute("UPDATE rd_accounts SET installments_paid = installments_paid + 1 WHERE rd_id = ?", (rd_id,))
            
            txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
            c.execute("INSERT INTO sb_transactions (transaction_id, account_number, transaction_type, amount, balance_before, balance_after, description, created_by) VALUES (?, ?, 'RD_Transfer', ?, ?, ?, ?, ?)",
                     (txn_id, rd[2], rd[3], sb_bal, new_bal, f'RD Installment {inst[1]}/{rd[9]} - {rd_id}', created_by))
            # Accounting
            JournalVoucherModule.create_auto_voucher('RD', datetime.now().date(), f'RD {rd_id} Installment {inst[1]}', created_by,
                [('RD_INVESTMENTS', rd[3], 0), ('SB_ACCOUNTS', rd[3], 0)])
            
            conn.commit(); conn.close()
            return True, f"Installment {inst[1]}/{rd[9]} paid"
        except Exception as e:
            conn.rollback(); conn.close()
            return False, str(e)

# ============================================
# JOURNAL VOUCHER MODULE
# ============================================
class JournalVoucherModule:
    @staticmethod
    def generate_voucher_id(vt):
        prefix = {'Payment': 'PMT', 'Receipt': 'RCP', 'Journal': 'JNL', 'Interest': 'INT', 'FD': 'FDV', 'RD': 'RDV'}
        return f"{prefix.get(vt, 'JNL')}{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}"
    
    @staticmethod
    def create_voucher(voucher_type, voucher_date, narration, entries, created_by):
        conn = db.get_connection(); c = conn.cursor()
        try:
            total_dr = sum(e[1] for e in entries)
            total_cr = sum(e[2] for e in entries)
            if abs(total_dr - total_cr) > 0.01: conn.close(); return False, "Debit and Credit must be equal"
            if total_dr == 0: conn.close(); return False, "Amount cannot be zero"
            
            vid = JournalVoucherModule.generate_voucher_id(voucher_type)
            c.execute("INSERT INTO journal_vouchers (voucher_id, voucher_type, voucher_date, narration, total_amount, created_by) VALUES (?, ?, ?, ?, ?, ?)",
                     (vid, voucher_type, voucher_date, narration, total_dr, created_by))
            for acc, dr, cr in entries:
                c.execute("INSERT INTO journal_entries (voucher_id, account_head, debit_amount, credit_amount) VALUES (?, ?, ?, ?)",
                         (vid, acc, dr, cr))
            conn.commit(); conn.close()
            return True, vid
        except Exception as e:
            conn.rollback(); conn.close()
            return False, str(e)
    
    @staticmethod
    def create_auto_voucher(vt, dt, nar, created_by, entries):
        success, result = JournalVoucherModule.create_voucher(vt, dt, nar, entries, created_by)
        return result if success else None

# ============================================
# CUSTOMER MODULE
# ============================================
class CustomerModule:
    @staticmethod
    def generate_customer_id():
        return f"CUST{uuid.uuid4().hex[:8].upper()}"
    
    @staticmethod
    def register_customer(data, created_by):
        conn = db.get_connection(); c = conn.cursor()
        try:
            cid = CustomerModule.generate_customer_id()
            c.execute("INSERT INTO customers (customer_id, first_name, last_name, date_of_birth, phone, email, address, city, state, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (cid, data['first_name'], data['last_name'], data.get('date_of_birth'), data['phone'], data.get('email'), data.get('address'), data.get('city'), data.get('state'), created_by))
            conn.commit(); conn.close()
            return True, cid
        except Exception as e:
            conn.rollback(); conn.close()
            return False, str(e)
    
    @staticmethod
    def verify_kyc(customer_id, verified_by):
        conn = db.get_connection(); c = conn.cursor()
        try:
            c.execute("UPDATE customers SET kyc_status = 'Verified' WHERE customer_id = ?", (customer_id,))
            conn.commit(); conn.close()
            return True, "KYC Verified"
        except Exception as e:
            conn.rollback(); conn.close()
            return False, str(e)

# ============================================
# FINANCIAL REPORTING
# ============================================
class FinancialReportingModule:
    @staticmethod
    def get_trial_balance(as_of_date=None):
        if as_of_date is None: as_of_date = datetime.now().date()
        conn = db.get_connection(); c = conn.cursor()
        c.execute("""SELECT coa.account_head, coa.account_name, coa.account_type,
            COALESCE(SUM(je.debit_amount), 0) as total_debit, COALESCE(SUM(je.credit_amount), 0) as total_credit
            FROM chart_of_accounts coa
            LEFT JOIN journal_entries je ON coa.account_head = je.account_head
            LEFT JOIN journal_vouchers jv ON je.voucher_id = jv.voucher_id AND jv.voucher_date <= ? AND jv.status = 'Approved'
            WHERE coa.is_active = 1
            GROUP BY coa.account_head, coa.account_name, coa.account_type
            ORDER BY coa.account_type, coa.account_head""", (as_of_date,))
        data = c.fetchall(); conn.close()
        
        result, td, tc = [], 0, 0
        for row in data:
            if row[2] in ('Asset', 'Expense'):
                net = row[3] - row[4]
                dr, cr = (net, 0) if net > 0 else (0, abs(net))
            else:
                net = row[4] - row[3]
                dr, cr = (0, net) if net > 0 else (abs(net), 0)
            td += dr; tc += cr
            result.append({'account_head': row[0], 'account_name': row[1], 'account_type': row[2], 'debit': dr, 'credit': cr})
        return result, td, tc
    
    @staticmethod
    def get_balance_sheet(as_of_date=None):
        tb, _, _ = FinancialReportingModule.get_trial_balance(as_of_date)
        assets = [i for i in tb if i['account_type'] == 'Asset']
        liabilities = [i for i in tb if i['account_type'] == 'Liability']
        equity = [i for i in tb if i['account_type'] == 'Equity']
        
        ta = sum(i['debit'] - i['credit'] for i in assets)
        tl = sum(i['credit'] - i['debit'] for i in liabilities)
        te = sum(i['credit'] - i['debit'] for i in equity)
        
        income_items = [i for i in tb if i['account_type'] == 'Income']
        expense_items = [i for i in tb if i['account_type'] == 'Expense']
        net_profit = sum(i['credit'] - i['debit'] for i in income_items) - sum(i['debit'] - i['credit'] for i in expense_items)
        
        if net_profit > 0:
            equity.append({'account_head': 'PROFIT_LOSS', 'account_name': 'P&L', 'account_type': 'Equity', 'debit': 0, 'credit': net_profit})
            te += net_profit
        
        return assets, liabilities, equity, ta, tl, te

# ============================================
# SESSION STATE
# ============================================
def init_session_state():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'user' not in st.session_state: st.session_state.user = None
    if 'current_tab' not in st.session_state: st.session_state.current_tab = 'SB Accounts'

# ============================================
# UI
# ============================================
def login_ui():
    st.markdown('<h1 class="main-header">🏦 Complete Banking System</h1>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login"):
            st.markdown('<h3 style="color: #a78bfa; text-align: center;">Login</h3>', unsafe_allow_html=True)
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login", use_container_width=True):
                user = AuthModule.authenticate(u, p)
                if user:
                    st.session_state.logged_in = True; st.session_state.user = user
                    st.success(f"Welcome, {user['full_name']}!"); st.rerun()
                else:
                    st.error("Invalid credentials")
        st.markdown("""<div class="info-box">Demo: admin/admin123 | manager/manager123 | user1/user123</div>""", unsafe_allow_html=True)

def sb_account_ui():
    st.markdown('<h2 class="sub-header">💰 Savings Bank Account</h2>', unsafe_allow_html=True)
    tab1, tab2, tab3, tab4 = st.tabs(["Open Account", "Deposit/Withdraw", "Interest", "List"])
    
    with tab1:
        conn = db.get_connection(); c = conn.cursor()
        c.execute("SELECT customer_id, first_name, last_name FROM customers WHERE kyc_status = 'Verified'")
        customers = c.fetchall(); conn.close()
        if customers:
            with st.form("open_sb"):
                opts = {f"{c[1]} {c[2]} ({c[0]})": c[0] for c in customers}
                sel = st.selectbox("Customer", list(opts.keys()))
                c1, c2 = st.columns(2)
                with c1: dep = st.number_input("Initial Deposit", min_value=0.0, value=0.0, step=500.0)
                with c2: rate = st.number_input("Interest Rate %", min_value=0.0, max_value=10.0, value=4.0, step=0.25)
                if st.form_submit_button("Open Account", use_container_width=True):
                    success, result = SBAccountModule.open_account(opts[sel], dep, rate, created_by=st.session_state.user['user_id'])
                    if success: st.success(f"Account: {result}"); st.balloons()
                    else: st.error(result)
        else: st.warning("No verified customers")
    
    with tab2:
        conn = db.get_connection(); c = conn.cursor()
        c.execute("SELECT sa.account_number, c.first_name || ' ' || c.last_name, sa.balance FROM sb_accounts sa JOIN customers c ON sa.customer_id = c.customer_id WHERE sa.status = 'Active'")
        accounts = c.fetchall(); conn.close()
        if accounts:
            c1, c2 = st.columns(2)
            with c1:
                with st.form("dep"):
                    opts = {f"{a[1]} - {a[0]} (₹{a[2]:,.2f})": a for a in accounts}
                    acc = st.selectbox("Account", list(opts.keys()), key="dep")
                    amt = st.number_input("Amount", min_value=1.0, value=100.0, step=100.0, key="da")
                    desc = st.text_input("Description", key="dd")
                    if st.form_submit_button("Deposit"):
                        success, msg = SBAccountModule.deposit(opts[acc][0], amt, desc, st.session_state.user['user_id'])
                        st.success(msg) if success else st.error(msg)
            with c2:
                with st.form("wit"):
                    opts = {f"{a[1]} - {a[0]} (₹{a[2]:,.2f})": a for a in accounts}
                    acc = st.selectbox("Account", list(opts.keys()), key="wit")
                    a = opts[acc]
                    amt = st.number_input("Amount", min_value=0.0, max_value=float(a[2]), value=0.0, step=100.0, key="wa")
                    desc = st.text_input("Description", key="wd")
                    if st.form_submit_button("Withdraw"):
                        success, msg = SBAccountModule.withdraw(a[0], amt, desc, st.session_state.user['user_id'])
                        st.success(msg) if success else st.error(msg)
    
    with tab3:
        if st.button("Calculate Interest", use_container_width=True):
            with st.spinner("Calculating..."):
                success, results = SBAccountModule.calculate_quarterly_interest(st.session_state.user['user_id'])
                if success:
                    st.success("Done!")
                    if results: st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
                else: st.warning(results)
    
    with tab4:
        conn = db.get_connection(); c = conn.cursor()
        c.execute("SELECT sa.account_number, c.first_name || ' ' || c.last_name, sa.balance, sa.status FROM sb_accounts sa JOIN customers c ON sa.customer_id = c.customer_id ORDER BY sa.created_at DESC")
        accounts = c.fetchall(); conn.close()
        if accounts:
            df = pd.DataFrame(accounts, columns=['Account', 'Customer', 'Balance', 'Status'])
            df['Balance'] = df['Balance'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(df, use_container_width=True, hide_index=True)

def fd_account_ui():
    st.markdown('<h2 class="sub-header">🏦 Fixed Deposit</h2>', unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["Open FD", "Mature", "List"])
    
    with tab1:
        conn = db.get_connection(); c = conn.cursor()
        c.execute("SELECT sa.account_number, sa.customer_id, c.first_name, c.last_name, sa.balance FROM sb_accounts sa JOIN customers c ON sa.customer_id = c.customer_id WHERE sa.status = 'Active'")
        accounts = c.fetchall(); conn.close()
        if accounts:
            with st.form("open_fd"):
                opts = {f"{a[2]} {a[3]} - {a[0]} (₹{a[4]:,.2f})": a for a in accounts}
                acc = opts[st.selectbox("SB Account", list(opts.keys()))]
                c1, c2, c3 = st.columns(3)
                with c1: principal = st.number_input("Principal", min_value=100.0, max_value=float(acc[4]), value=min(1000.0, float(acc[4])), step=1000.0)
                with c2: rate = st.number_input("Rate %", min_value=1.0, max_value=15.0, value=7.0, step=0.5)
                with c3: tenure = st.selectbox("Tenure", [3, 6, 12, 24, 36, 48, 60])
                if st.form_submit_button("Open FD", use_container_width=True):
                    success, result = FDAccountModule.open_fd(acc[1], acc[0], principal, rate, tenure, created_by=st.session_state.user['user_id'])
                    if success: st.success(f"FD: {result}"); st.balloons()
                    else: st.error(result)
    
    with tab2:
        conn = db.get_connection(); c = conn.cursor()
        c.execute("SELECT fd.*, c.first_name, c.last_name FROM fd_accounts fd JOIN customers c ON fd.customer_id = c.customer_id WHERE fd.status = 'Active' AND fd.maturity_date <= ?", (datetime.now().date(),))
        fds = c.fetchall(); conn.close()
        if fds:
            for fd in fds:
                with st.expander(f"{fd[0]} | Principal: ₹{fd[3]:,.2f} | Maturity: ₹{fd[8]:,.2f}"):
                    if st.button("Mature", key=f"m_{fd[0]}"):
                        success, msg = FDAccountModule.mature_fd(fd[0], st.session_state.user['user_id'])
                        st.success(msg) if success else st.error(msg)
                        if success: st.rerun()
        else: st.info("No FDs ready")
    
    with tab3:
        conn = db.get_connection(); c = conn.cursor()
        c.execute("SELECT fd.*, c.first_name, c.last_name FROM fd_accounts fd JOIN customers c ON fd.customer_id = c.customer_id ORDER BY fd.created_at DESC")
        fds = c.fetchall(); conn.close()
        if fds:
            data = [{'FD ID': f[0], 'Customer': f"{f[10]} {f[11]}", 'Principal': f"₹{f[3]:,.2f}", 'Rate': f"{f[4]}%", 'Maturity': f"₹{f[8]:,.2f}", 'Status': f[9]} for f in fds]
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

def rd_account_ui():
    st.markdown('<h2 class="sub-header">📅 Recurring Deposit</h2>', unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["Open RD", "Pay", "List"])
    
    with tab1:
        conn = db.get_connection(); c = conn.cursor()
        c.execute("SELECT sa.account_number, sa.customer_id, c.first_name, c.last_name, sa.balance FROM sb_accounts sa JOIN customers c ON sa.customer_id = c.customer_id WHERE sa.status = 'Active'")
        accounts = c.fetchall(); conn.close()
        if accounts:
            with st.form("open_rd"):
                opts = {f"{a[2]} {a[3]} - {a[0]} (₹{a[4]:,.2f})": a for a in accounts}
                acc = opts[st.selectbox("SB Account", list(opts.keys()))]
                c1, c2, c3 = st.columns(3)
                with c1: monthly = st.number_input("Monthly", min_value=100.0, value=500.0, step=100.0)
                with c2: rate = st.number_input("Rate %", min_value=1.0, max_value=15.0, value=6.5, step=0.5)
                with c3: tenure = st.selectbox("Tenure", [12, 24, 36, 48, 60])
                if st.form_submit_button("Open RD", use_container_width=True):
                    success, result = RDAccountModule.open_rd(acc[1], acc[0], monthly, rate, tenure, created_by=st.session_state.user['user_id'])
                    if success: st.success(f"RD: {result}"); st.balloons()
                    else: st.error(result)
    
    with tab2:
        conn = db.get_connection(); c = conn.cursor()
        c.execute("SELECT rd.*, c.first_name, c.last_name FROM rd_accounts rd JOIN customers c ON rd.customer_id = c.customer_id WHERE rd.status = 'Active'")
        rds = c.fetchall(); conn.close()
        if rds:
            for rd in rds:
                with st.expander(f"{rd[0]} | Monthly: ₹{rd[3]:,.2f} | Paid: {rd[9]}/{rd[10]}"):
                    c2 = db.get_connection().cursor()
                    c2.execute("SELECT * FROM rd_installments WHERE rd_id = ? AND status = 'Pending' ORDER BY installment_number LIMIT 1", (rd[0],))
                    inst = c2.fetchone(); c2.connection.close()
                    if inst:
                        st.info(f"Next: #{inst[1]} - ₹{inst[4]:,.2f}")
                        if st.button("Pay", key=f"p_{rd[0]}"):
                            success, msg = RDAccountModule.pay_installment(rd[0], st.session_state.user['user_id'])
                            st.success(msg) if success else st.error(msg)
                            if success: st.rerun()
                    else: st.success("All paid!")
    
    with tab3:
        conn = db.get_connection(); c = conn.cursor()
        c.execute("SELECT rd.*, c.first_name, c.last_name FROM rd_accounts rd JOIN customers c ON rd.customer_id = c.customer_id ORDER BY rd.created_at DESC")
        rds = c.fetchall(); conn.close()
        if rds:
            data = [{'RD ID': r[0], 'Customer': f"{r[12]} {r[13]}", 'Monthly': f"₹{r[3]:,.2f}", 'Paid': f"{r[9]}/{r[10]}", 'Maturity': f"₹{r[8]:,.2f}", 'Status': r[11]} for r in rds]
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

def customer_ui():
    st.markdown('<h2 class="sub-header">👤 Customers</h2>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Register", "List"])
    
    with tab1:
        with st.form("reg"):
            c1, c2 = st.columns(2)
            with c1: fn = st.text_input("First Name *"); dob = st.date_input("DOB", datetime.now()-timedelta(days=365*18)); email = st.text_input("Email")
            with c2: ln = st.text_input("Last Name *"); phone = st.text_input("Phone *"); addr = st.text_input("Address")
            if st.form_submit_button("Register", use_container_width=True):
                if fn and ln and phone:
                    data = {'first_name': fn, 'last_name': ln, 'date_of_birth': dob, 'phone': phone, 'email': email, 'address': addr}
                    success, result = CustomerModule.register_customer(data, st.session_state.user['user_id'])
                    st.success(f"ID: {result}") if success else st.error(result)
                else: st.error("Required fields missing!")
    
    with tab2:
        conn = db.get_connection(); c = conn.cursor()
        c.execute("SELECT customer_id, first_name, last_name, phone, kyc_status FROM customers ORDER BY created_at DESC")
        customers = c.fetchall(); conn.close()
        if customers:
            for row in customers:
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.markdown(f"**{row[1]} {row[2]}** ({row[0]})")
                if row[4] == 'Verified': c2.markdown('<span class="badge badge-success">✅ Verified</span>', unsafe_allow_html=True)
                else:
                    c2.markdown(f'<span class="badge badge-warning">⏳ {row[4]}</span>', unsafe_allow_html=True)
                    if c3.button("Verify", key=f"v_{row[0]}"):
                        CustomerModule.verify_kyc(row[0], st.session_state.user['user_id']); st.rerun()
                st.divider()

def reports_ui():
    st.markdown('<h2 class="sub-header">📈 Reports</h2>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Trial Balance", "Balance Sheet"])
    
    with tab1:
        if st.button("Generate Trial Balance", use_container_width=True):
            data, td, tc = FinancialReportingModule.get_trial_balance()
            if data:
                df_data = [{'Account': i['account_head'], 'Name': i['account_name'], 'Type': i['account_type'], 'Debit': f"₹{i['debit']:,.2f}" if i['debit'] > 0 else "-", 'Credit': f"₹{i['credit']:,.2f}" if i['credit'] > 0 else "-"} for i in data if i['debit'] > 0 or i['credit'] > 0]
                df_data.append({'Account': 'TOTAL', 'Name': '', 'Type': '', 'Debit': f"₹{td:,.2f}", 'Credit': f"₹{tc:,.2f}"})
                st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)
                if abs(td - tc) < 0.01: st.success(f"✅ Balanced! ₹{td:,.2f}")
                else: st.error(f"❌ Difference: ₹{abs(td-tc):,.2f}")
    
    with tab2:
        if st.button("Generate Balance Sheet", use_container_width=True):
            assets, liab, equity, ta, tl, te = FinancialReportingModule.get_balance_sheet()
            c1, c2 = st.columns(2)
            with c1:
                st.write("**ASSETS**")
                for i in assets:
                    amt = i['debit'] - i['credit']
                    if amt != 0: st.write(f"- {i['account_name']}: ₹{amt:,.2f}")
                st.write(f"**Total: ₹{ta:,.2f}**")
            with c2:
                st.write("**LIABILITIES & EQUITY**")
                for i in liab:
                    amt = i['credit'] - i['debit']
                    if amt != 0: st.write(f"- {i['account_name']}: ₹{amt:,.2f}")
                for i in equity:
                    amt = i['credit'] - i['debit']
                    if amt != 0: st.write(f"- {i['account_name']}: ₹{amt:,.2f}")
                st.write(f"**Total: ₹{tl+te:,.2f}**")

def head_management_ui():
    st.markdown('<h2 class="sub-header">📋 Chart of Accounts</h2>', unsafe_allow_html=True)
    conn = db.get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM chart_of_accounts WHERE is_active = 1 ORDER BY account_type, account_head")
    accounts = c.fetchall(); conn.close()
    if accounts:
        df = pd.DataFrame(accounts, columns=['Head', 'Name', 'Type', 'Category', 'Active'])
        st.dataframe(df[['Head', 'Name', 'Type', 'Category']], use_container_width=True, hide_index=True)

# ============================================
# MAIN
# ============================================
def main():
    init_session_state()
    
    try:
        db.initialize_database()
    except Exception as e:
        st.error(f"DB Error: {e}")
        if st.button("Reset DB"):
            if os.path.exists('complete_banking.db'): os.remove('complete_banking.db')
            st.rerun()
        return
    
    if not st.session_state.logged_in:
        login_ui()
        return
    
    with st.sidebar:
        st.markdown(f"""<div style='text-align:center;padding:1rem 0;'><h3 style='color:#a78bfa;'>🏦 Banking</h3><p style='color:#94a3b8;'>{st.session_state.user['full_name']}</p></div>""", unsafe_allow_html=True)
        st.markdown("---")
        
        tabs = {'SB Accounts': '💰 SB', 'FD Accounts': '🏦 FD', 'RD Accounts': '📅 RD', 'Customers': '👤 Customers', 'Reports': '📈 Reports', 'Head Management': '🔧 Accounts'}
        selected = st.radio("Menu", list(tabs.keys()), format_func=lambda x: tabs[x], label_visibility="collapsed")
        st.session_state.current_tab = selected
        
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False; st.session_state.user = None; st.rerun()
    
    if st.session_state.current_tab == 'SB Accounts': sb_account_ui()
    elif st.session_state.current_tab == 'FD Accounts': fd_account_ui()
    elif st.session_state.current_tab == 'RD Accounts': rd_account_ui()
    elif st.session_state.current_tab == 'Customers': customer_ui()
    elif st.session_state.current_tab == 'Reports': reports_ui()
    elif st.session_state.current_tab == 'Head Management': head_management_ui()

if __name__ == "__main__":
    main()




