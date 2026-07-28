# 🏦 AASHA NIDHI PVT LIMITED BANK - BALARAMAPURAM
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import uuid
import os
from PIL import Image
import io
import hashlib
import base64
import plotly.express as px
import plotly.graph_objects as go
import tempfile

try:
    from fpdf import FPDF
except ImportError:
    try:
        from fpdf2 import FPDF
    except ImportError:
        FPDF = None

# ==================== DATABASE SETUP ====================
def init_database():
    conn = sqlite3.connect('banking_system.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL, is_active BOOLEAN DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id TEXT UNIQUE NOT NULL, user_id INTEGER, first_name TEXT NOT NULL, last_name TEXT NOT NULL, date_of_birth DATE NOT NULL, gender TEXT, email TEXT UNIQUE NOT NULL, phone TEXT NOT NULL, address TEXT, city TEXT, state TEXT, pincode TEXT, pan_number TEXT UNIQUE, aadhar_number TEXT UNIQUE, kyc_status TEXT DEFAULT 'PENDING', kyc_verified_by INTEGER, kyc_verified_at TIMESTAMP, pan_document BLOB, aadhar_document BLOB, photo BLOB, signature BLOB, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, account_number TEXT UNIQUE NOT NULL, customer_id INTEGER NOT NULL, account_type TEXT NOT NULL, balance DECIMAL(15,2) DEFAULT 0.00, status TEXT DEFAULT 'ACTIVE', interest_rate DECIMAL(5,2), last_interest_calculation DATE, total_interest_earned DECIMAL(15,2) DEFAULT 0.00, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    
    try: 
        c.execute("SELECT total_interest_earned FROM accounts LIMIT 1")
    except: 
        c.execute("ALTER TABLE accounts ADD COLUMN total_interest_earned DECIMAL(15,2) DEFAULT 0.00")
    
    c.execute('''CREATE TABLE IF NOT EXISTS fixed_deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, fd_number TEXT UNIQUE NOT NULL, account_id INTEGER NOT NULL, principal_amount DECIMAL(15,2) NOT NULL, interest_rate DECIMAL(5,2) NOT NULL, start_date DATE NOT NULL, maturity_date DATE NOT NULL, maturity_amount DECIMAL(15,2), tenure_months INTEGER NOT NULL, status TEXT DEFAULT 'ACTIVE', nominee_name TEXT, nominee_relation TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (account_id) REFERENCES accounts (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS recurring_deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, rd_number TEXT UNIQUE NOT NULL, account_id INTEGER NOT NULL, monthly_amount DECIMAL(15,2) NOT NULL, interest_rate DECIMAL(5,2) NOT NULL, start_date DATE NOT NULL, maturity_date DATE NOT NULL, maturity_amount DECIMAL(15,2), tenure_months INTEGER NOT NULL, installments_paid INTEGER DEFAULT 0, total_installments INTEGER NOT NULL, status TEXT DEFAULT 'ACTIVE', nominee_name TEXT, nominee_relation TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (account_id) REFERENCES accounts (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id TEXT UNIQUE NOT NULL, account_id INTEGER NOT NULL, transaction_type TEXT NOT NULL, amount DECIMAL(15,2) NOT NULL, balance_after DECIMAL(15,2) NOT NULL, description TEXT, reference_type TEXT, reference_id TEXT, voucher_type TEXT, voucher_number TEXT, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (account_id) REFERENCES accounts (id), FOREIGN KEY (created_by) REFERENCES users (id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS journal_vouchers (id INTEGER PRIMARY KEY AUTOINCREMENT, voucher_number TEXT UNIQUE NOT NULL, voucher_date DATE NOT NULL, description TEXT, total_amount DECIMAL(15,2) NOT NULL, status TEXT DEFAULT 'DRAFT', created_by INTEGER, posted_by INTEGER, posted_at TIMESTAMP, customer_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (created_by) REFERENCES users (id), FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    try:
        c.execute("SELECT customer_id FROM journal_vouchers LIMIT 1")
    except:
        c.execute("ALTER TABLE journal_vouchers ADD COLUMN customer_id INTEGER")
    
    c.execute('''CREATE TABLE IF NOT EXISTS journal_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, voucher_id INTEGER NOT NULL, account_id INTEGER, account_head TEXT, debit_amount DECIMAL(15,2) DEFAULT 0.00, credit_amount DECIMAL(15,2) DEFAULT 0.00, description TEXT, FOREIGN KEY (voucher_id) REFERENCES journal_vouchers (id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS interest_calculations (id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER NOT NULL, calculation_date DATE NOT NULL, principal_amount DECIMAL(15,2) NOT NULL, interest_rate DECIMAL(5,2) NOT NULL, interest_earned DECIMAL(15,2) NOT NULL, days_calculated INTEGER NOT NULL, customer_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (account_id) REFERENCES accounts (id), FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    try:
        c.execute("SELECT customer_id FROM interest_calculations LIMIT 1")
    except:
        c.execute("ALTER TABLE interest_calculations ADD COLUMN customer_id INTEGER")
    
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, expense_id TEXT UNIQUE NOT NULL, expense_type TEXT NOT NULL, amount DECIMAL(15,2) NOT NULL, description TEXT, date DATE NOT NULL, customer_id INTEGER, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (created_by) REFERENCES users (id), FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    try:
        c.execute("SELECT customer_id FROM expenses LIMIT 1")
    except:
        c.execute("ALTER TABLE expenses ADD COLUMN customer_id INTEGER")
    
    c.execute('''CREATE TABLE IF NOT EXISTS income (id INTEGER PRIMARY KEY AUTOINCREMENT, income_id TEXT UNIQUE NOT NULL, income_type TEXT NOT NULL, amount DECIMAL(15,2) NOT NULL, description TEXT, date DATE NOT NULL, customer_id INTEGER, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (created_by) REFERENCES users (id), FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    try:
        c.execute("SELECT customer_id FROM income LIMIT 1")
    except:
        c.execute("ALTER TABLE income ADD COLUMN customer_id INTEGER")
    
    conn.commit()
    conn.close()

# ==================== UTILITY FUNCTIONS ====================
def get_db(): 
    return sqlite3.connect('banking_system.db')

def generate_id(p): 
    return f"{p}{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4]}"

def generate_account_number(t): 
    return f"{'100' if t=='SB' else '200' if t=='FD' else '300'}{datetime.now().strftime('%y%m%d')}{str(uuid.uuid4().int)[:6]}"

def generate_voucher_number(v): 
    return f"{'PMT' if v=='PAYMENT' else 'RCT' if v=='RECEIPT' else 'JNL'}{datetime.now().strftime('%Y%m%d%H%M')}{str(uuid.uuid4().int)[:4]}"

def safe_text(text):
    if text is None:
        return "N/A"
    try:
        return str(text)
    except:
        return "Error displaying text"

def calculate_fd_maturity(p, r, m): 
    return round(p * (1 + r/400) ** (m/3), 2)

def calculate_rd_maturity(m, r, mo): 
    return round(m * (((1 + r/400) ** (mo/3) - 1) / (1 - (1 + r/400) ** (-1/3))), 2)

def calculate_sb_interest(b, r, d): 
    return 0 if b <= 0 else round((b * r * d) / (100 * 365), 2)

def get_minimum_balance(c, aid, fd, td):
    try:
        sb = c.execute("SELECT balance_after FROM transactions WHERE account_id=? AND DATE(created_at)<? ORDER BY created_at DESC LIMIT 1", (aid, fd)).fetchone()
        sb = sb[0] if sb else (c.execute("SELECT balance FROM accounts WHERE id=?", (aid,)).fetchone() or [0])[0]
        txns = c.execute("SELECT balance_after FROM transactions WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ? ORDER BY created_at", (aid, fd, td)).fetchall()
        return min([sb] + [t[0] for t in txns]) if txns else sb
    except: 
        return (c.execute("SELECT balance FROM accounts WHERE id=?", (aid,)).fetchone() or [0])[0]

def hash_password(p): 
    return hashlib.sha256(p.encode()).hexdigest()

def login_user(u, p):
    c = get_db()
    cur = c.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=? AND is_active=1", (u, hash_password(p)))
    user = cur.fetchone()
    c.close()
    return user

def create_default_admin():
    c = get_db()
    if c.execute("SELECT COUNT(*) FROM users WHERE username='admin'").fetchone()[0] == 0:
        c.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)", ('admin', hash_password('admin123'), 'admin'))
        c.commit()
    c.close()

def get_ist_time():
    from datetime import timezone, timedelta
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).strftime('%d-%m-%Y %I:%M:%S %p')

def format_date(date_obj):
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
        except:
            return date_obj
    return date_obj.strftime('%d-%m-%Y')

def delete_record(table, id_column, id_value, table_display):
    c = get_db()
    try:
        c.execute(f"DELETE FROM {table} WHERE {id_column}=?", (id_value,))
        c.commit()
        st.success(f"Success: {table_display} deleted successfully!")
        st.rerun()
    except Exception as e:
        st.error(f"Error deleting: {str(e)}")
    finally:
        c.close()

def calculate_and_post_sb_interest(created_by, from_date, to_date, customer_id=None):
    c = get_db()
    results = []
    try:
        if customer_id:
            accs = c.execute("SELECT a.id, a.account_number, c.first_name||' '||c.last_name, a.balance, a.interest_rate, COALESCE(a.total_interest_earned, 0), c.id as cust_id FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND c.id=?", (customer_id,)).fetchall()
        else:
            accs = c.execute("SELECT a.id, a.account_number, c.first_name||' '||c.last_name, a.balance, a.interest_rate, COALESCE(a.total_interest_earned, 0), c.id as cust_id FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        
        for acc in accs:
            min_bal = get_minimum_balance(c, acc[0], from_date, to_date)
            if min_bal <= 0:
                min_bal = acc[3]
            days = (to_date - from_date).days + 1
            if days > 0:
                interest = calculate_sb_interest(min_bal, acc[4] or 3.5, days)
                if interest > 0:
                    c.execute("UPDATE accounts SET total_interest_earned = COALESCE(total_interest_earned, 0) + ? WHERE id=?", (interest, acc[0]))
                    try:
                        c.execute("INSERT INTO interest_calculations (account_id, calculation_date, principal_amount, interest_rate, interest_earned, days_calculated, customer_id) VALUES (?, DATE('now'), ?, ?, ?, ?, ?)", 
                                 (acc[0], min_bal, acc[4] or 3.5, interest, days, acc[6]))
                    except:
                        c.execute("INSERT INTO interest_calculations (account_id, calculation_date, principal_amount, interest_rate, interest_earned, days_calculated) VALUES (?, DATE('now'), ?, ?, ?, ?)", 
                                 (acc[0], min_bal, acc[4] or 3.5, interest, days))
                    results.append({
                        'account': acc[1],
                        'customer': acc[2],
                        'min_balance': min_bal,
                        'interest': interest,
                        'days': days
                    })
        c.commit()
        return "SUCCESS", results
    except Exception as e:
        c.rollback()
        return f"ERROR: {str(e)}", []
    finally:
        c.close()

# ==================== PDF GENERATION FUNCTIONS ====================
class BankPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 8, 'AASHA NIDHI PVT LIMITED BANK', 0, 1, 'C')
        self.set_font('Arial', 'B', 12)
        self.cell(0, 6, 'BALARAMAPURAM', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, '-------------------------------------------', 0, 1, 'C')
        self.ln(3)
    
    def footer(self): 
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

def generate_statement_pdf(account_data, transactions, customer_data, from_date, to_date):
    if FPDF is None:
        return None
    pdf = BankPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, f"CUSTOMER ID: {customer_data['customer_id']}", 0, 1, 'L')
    pdf.cell(0, 6, f"CUSTOMER NAME: {customer_data['customer_name']}", 0, 1, 'L')
    pdf.cell(0, 6, f"ACCOUNT NUMBER: {account_data['account_number']}", 0, 1, 'L')
    pdf.cell(0, 6, f"INTEREST RATE: {account_data['interest_rate']}%", 0, 1, 'L')
    pdf.cell(0, 6, f"TOTAL DEPOSITS: Rs. {account_data['total_deposits']:,.2f}", 0, 1, 'L')
    pdf.cell(0, 6, f"TOTAL INTEREST EARNED: Rs. {account_data['total_interest']:,.2f}", 0, 1, 'L')
    pdf.cell(0, 6, f"TOTAL AMOUNT: Rs. {account_data['total_amount']:,.2f}", 0, 1, 'L')
    pdf.cell(0, 6, f"STATEMENT PERIOD: {from_date} to {to_date}", 0, 1, 'L')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(15, 7, 'S.No', 1)
    pdf.cell(30, 7, 'Date', 1)
    pdf.cell(25, 7, 'Type', 1)
    pdf.cell(30, 7, 'Description', 1)
    pdf.cell(25, 7, 'Credit', 1, 0, 'R')
    pdf.cell(25, 7, 'Debit', 1, 0, 'R')
    pdf.cell(30, 7, 'Balance', 1, 1, 'R')
    
    pdf.set_font('Arial', '', 9)
    for idx, txn in enumerate(transactions, 1):
        pdf.cell(15, 6, str(idx), 1)
        pdf.cell(30, 6, txn['date'], 1)
        pdf.cell(25, 6, txn['type'], 1)
        pdf.cell(30, 6, txn['description'][:20], 1)
        pdf.cell(25, 6, f"{txn['credit']:,.2f}" if txn['credit'] > 0 else "", 1, 0, 'R')
        pdf.cell(25, 6, f"{txn['debit']:,.2f}" if txn['debit'] > 0 else "", 1, 0, 'R')
        pdf.cell(30, 6, f"{txn['balance']:,.2f}", 1, 1, 'R')
    
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 7, f"TOTAL CREDIT: Rs. {sum(t['credit'] for t in transactions):,.2f}", 0, 1, 'L')
    pdf.cell(0, 7, f"TOTAL DEBIT: Rs. {sum(t['debit'] for t in transactions):,.2f}", 0, 1, 'L')
    pdf.cell(0, 7, f"CLOSING BALANCE: Rs. {account_data['total_amount']:,.2f}", 0, 1, 'L')
    
    pdf.set_font('Arial', 'I', 8)
    pdf.cell(0, 5, f"Generated on: {get_ist_time()}", 0, 1, 'L')
    return pdf

def generate_fd_statement_pdf(fd_data, customer_data):
    if FPDF is None:
        return None
    pdf = BankPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'FIXED DEPOSIT RECEIPT', 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, f"CUSTOMER ID: {customer_data['customer_id']}", 0, 1, 'L')
    pdf.cell(0, 6, f"CUSTOMER NAME: {customer_data['customer_name']}", 0, 1, 'L')
    pdf.cell(0, 6, f"ADDRESS: {customer_data.get('address', 'N/A')}", 0, 1, 'L')
    pdf.cell(0, 6, f"PHONE: {customer_data.get('phone', 'N/A')}", 0, 1, 'L')
    pdf.ln(3)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, 'FIXED DEPOSIT DETAILS', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.cell(60, 6, 'FD Number:', 0, 0, 'L')
    pdf.cell(0, 6, f"{fd_data['fd_number']}", 0, 1, 'L')
    pdf.cell(60, 6, 'Account Number:', 0, 0, 'L')
    pdf.cell(0, 6, f"{fd_data['account_number']}", 0, 1, 'L')
    pdf.cell(60, 6, 'Principal Amount:', 0, 0, 'L')
    pdf.cell(0, 6, f"Rs. {fd_data['principal']:,.2f}", 0, 1, 'L')
    pdf.cell(60, 6, 'Interest Rate:', 0, 0, 'L')
    pdf.cell(0, 6, f"{fd_data['interest_rate']}% per annum", 0, 1, 'L')
    pdf.cell(60, 6, 'Tenure:', 0, 0, 'L')
    pdf.cell(0, 6, f"{fd_data['tenure_months']} months", 0, 1, 'L')
    pdf.cell(60, 6, 'Start Date:', 0, 0, 'L')
    pdf.cell(0, 6, f"{fd_data['start_date']}", 0, 1, 'L')
    pdf.cell(60, 6, 'Maturity Date:', 0, 0, 'L')
    pdf.cell(0, 6, f"{fd_data['maturity_date']}", 0, 1, 'L')
    pdf.cell(60, 6, 'Maturity Amount:', 0, 0, 'L')
    pdf.cell(0, 6, f"Rs. {fd_data['maturity_amount']:,.2f}", 0, 1, 'L')
    pdf.cell(60, 6, 'Total Interest Earned:', 0, 0, 'L')
    pdf.cell(0, 6, f"Rs. {fd_data.get('total_interest', fd_data['maturity_amount'] - fd_data['principal']):,.2f}", 0, 1, 'L')
    
    if fd_data.get('nominee_name'):
        pdf.cell(60, 6, 'Nominee Name:', 0, 0, 'L')
        pdf.cell(0, 6, f"{fd_data['nominee_name']}", 0, 1, 'L')
    if fd_data.get('nominee_relation'):
        pdf.cell(60, 6, 'Nominee Relation:', 0, 0, 'L')
        pdf.cell(0, 6, f"{fd_data['nominee_relation']}", 0, 1, 'L')
    
    pdf.cell(60, 6, 'Status:', 0, 0, 'L')
    pdf.cell(0, 6, f"{fd_data['status']}", 0, 1, 'L')
    
    pdf.ln(5)
    pdf.set_font('Arial', 'I', 9)
    pdf.cell(0, 5, 'This is a system generated receipt.', 0, 1, 'C')
    pdf.cell(0, 5, f"Generated on: {get_ist_time()}", 0, 1, 'C')
    
    pdf.ln(3)
    pdf.set_font('Arial', 'I', 8)
    pdf.cell(0, 4, 'Terms & Conditions:', 0, 1, 'L')
    pdf.cell(0, 4, '1. Fixed Deposit is subject to terms and conditions of the bank.', 0, 1, 'L')
    pdf.cell(0, 4, '2. Premature withdrawal is subject to applicable penalties.', 0, 1, 'L')
    pdf.cell(0, 4, '3. TDS will be applicable as per Income Tax rules.', 0, 1, 'L')
    pdf.cell(0, 4, '4. Please keep this receipt for future reference.', 0, 1, 'L')
    return pdf

def generate_rd_statement_pdf(rd_data, customer_data):
    if FPDF is None:
        return None
    pdf = BankPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'RECURRING DEPOSIT RECEIPT', 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, f"CUSTOMER ID: {customer_data['customer_id']}", 0, 1, 'L')
    pdf.cell(0, 6, f"CUSTOMER NAME: {customer_data['customer_name']}", 0, 1, 'L')
    pdf.cell(0, 6, f"ADDRESS: {customer_data.get('address', 'N/A')}", 0, 1, 'L')
    pdf.cell(0, 6, f"PHONE: {customer_data.get('phone', 'N/A')}", 0, 1, 'L')
    pdf.ln(3)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, 'RECURRING DEPOSIT DETAILS', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.cell(60, 6, 'RD Number:', 0, 0, 'L')
    pdf.cell(0, 6, f"{rd_data['rd_number']}", 0, 1, 'L')
    pdf.cell(60, 6, 'Account Number:', 0, 0, 'L')
    pdf.cell(0, 6, f"{rd_data['account_number']}", 0, 1, 'L')
    pdf.cell(60, 6, 'Monthly Installment:', 0, 0, 'L')
    pdf.cell(0, 6, f"Rs. {rd_data['monthly_amount']:,.2f}", 0, 1, 'L')
    pdf.cell(60, 6, 'Interest Rate:', 0, 0, 'L')
    pdf.cell(0, 6, f"{rd_data['interest_rate']}% per annum", 0, 1, 'L')
    pdf.cell(60, 6, 'Tenure:', 0, 0, 'L')
    pdf.cell(0, 6, f"{rd_data['tenure_months']} months", 0, 1, 'L')
    pdf.cell(60, 6, 'Total Installments:', 0, 0, 'L')
    pdf.cell(0, 6, f"{rd_data['total_installments']}", 0, 1, 'L')
    pdf.cell(60, 6, 'Installments Paid:', 0, 0, 'L')
    pdf.cell(0, 6, f"{rd_data['installments_paid']}", 0, 1, 'L')
    pdf.cell(60, 6, 'Start Date:', 0, 0, 'L')
    pdf.cell(0, 6, f"{rd_data['start_date']}", 0, 1, 'L')
    pdf.cell(60, 6, 'Maturity Date:', 0, 0, 'L')
    pdf.cell(0, 6, f"{rd_data['maturity_date']}", 0, 1, 'L')
    
    total_deposited = rd_data['monthly_amount'] * rd_data['installments_paid']
    pdf.cell(60, 6, 'Total Deposit Amount:', 0, 0, 'L')
    pdf.cell(0, 6, f"Rs. {total_deposited:,.2f}", 0, 1, 'L')
    
    actual_interest = 0
    if rd_data['installments_paid'] > 0:
        actual_maturity = calculate_rd_maturity(rd_data['monthly_amount'], rd_data['interest_rate'], rd_data['installments_paid'])
        actual_interest = actual_maturity - total_deposited
    
    pdf.cell(60, 6, 'Maturity Amount (Projected):', 0, 0, 'L')
    pdf.cell(0, 6, f"Rs. {rd_data['maturity_amount']:,.2f}", 0, 1, 'L')
    pdf.cell(60, 6, 'Interest Earned (Actual):', 0, 0, 'L')
    pdf.cell(0, 6, f"Rs. {actual_interest:,.2f}", 0, 1, 'L')
    
    if rd_data.get('nominee_name'):
        pdf.cell(60, 6, 'Nominee Name:', 0, 0, 'L')
        pdf.cell(0, 6, f"{rd_data['nominee_name']}", 0, 1, 'L')
    if rd_data.get('nominee_relation'):
        pdf.cell(60, 6, 'Nominee Relation:', 0, 0, 'L')
        pdf.cell(0, 6, f"{rd_data['nominee_relation']}", 0, 1, 'L')
    
    pdf.cell(60, 6, 'Status:', 0, 0, 'L')
    pdf.cell(0, 6, f"{rd_data['status']}", 0, 1, 'L')
    
    pdf.ln(3)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 6, 'INSTALLMENT PROGRESS:', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    progress = (rd_data['installments_paid'] / rd_data['total_installments']) * 100
    pdf.cell(0, 6, f"Progress: {rd_data['installments_paid']} / {rd_data['total_installments']} installments paid ({progress:.1f}%)", 0, 1, 'L')
    bar_length = 50
    filled = int((progress / 100) * bar_length)
    bar = '=' * filled + '-' * (bar_length - filled)
    pdf.cell(0, 6, f"[{bar}]", 0, 1, 'L')
    
    pdf.ln(5)
    pdf.set_font('Arial', 'I', 9)
    pdf.cell(0, 5, 'This is a system generated receipt.', 0, 1, 'C')
    pdf.cell(0, 5, f"Generated on: {get_ist_time()}", 0, 1, 'C')
    
    pdf.ln(3)
    pdf.set_font('Arial', 'I', 8)
    pdf.cell(0, 4, 'Terms & Conditions:', 0, 1, 'L')
    pdf.cell(0, 4, '1. Recurring Deposit is subject to terms and conditions of the bank.', 0, 1, 'L')
    pdf.cell(0, 4, '2. Premature closure is subject to applicable penalties.', 0, 1, 'L')
    pdf.cell(0, 4, '3. TDS will be applicable as per Income Tax rules.', 0, 1, 'L')
    pdf.cell(0, 4, '4. Please keep this receipt for future reference.', 0, 1, 'L')
    return pdf

def generate_journal_voucher_pdf(voucher_data, entries_data):
    if FPDF is None:
        return None
    pdf = BankPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'JOURNAL VOUCHER', 0, 1, 'C')
    pdf.ln(3)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, f"Voucher Number: {voucher_data['voucher_number']}", 0, 1, 'L')
    pdf.cell(0, 6, f"Date: {voucher_data['voucher_date']}", 0, 1, 'L')
    pdf.cell(0, 6, f"Description: {voucher_data['description']}", 0, 1, 'L')
    pdf.cell(0, 6, f"Status: {voucher_data.get('status', 'DRAFT')}", 0, 1, 'L')
    if voucher_data.get('customer_name'):
        pdf.cell(0, 6, f"Customer: {voucher_data['customer_name']}", 0, 1, 'L')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(8, 7, 'S.No', 1)
    pdf.cell(60, 7, 'Account Head', 1)
    pdf.cell(25, 7, 'Category', 1)
    pdf.cell(35, 7, 'Debit (Dr)', 1, 0, 'R')
    pdf.cell(35, 7, 'Credit (Cr)', 1, 1, 'R')
    
    pdf.set_font('Arial', '', 9)
    total_dr = 0
    total_cr = 0
    for idx, entry in enumerate(entries_data, 1):
        debit = entry.get('debit_amount', entry.get('debit', 0))
        credit = entry.get('credit_amount', entry.get('credit', 0))
        account_head = entry.get('account_head', entry.get('head', 'N/A'))
        category = entry.get('category', '') or entry.get('sub_category', '')
        
        pdf.cell(8, 6, str(idx), 1)
        pdf.cell(60, 6, account_head[:30] if len(account_head) > 30 else account_head, 1)
        pdf.cell(25, 6, category[:20] if len(str(category)) > 20 else str(category), 1)
        pdf.cell(35, 6, f"{debit:,.2f}", 1, 0, 'R')
        pdf.cell(35, 6, f"{credit:,.2f}", 1, 1, 'R')
        total_dr += debit
        total_cr += credit
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(93, 7, 'TOTAL', 1)
    pdf.cell(35, 7, f"{total_dr:,.2f}", 1, 0, 'R')
    pdf.cell(35, 7, f"{total_cr:,.2f}", 1, 1, 'R')
    
    if abs(total_dr - total_cr) < 0.01:
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(0, 128, 0)
        pdf.cell(0, 7, '[OK] VOUCHER IS BALANCED', 0, 1, 'C')
    else:
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 7, f'[!!] MISMATCH: Rs. {abs(total_dr - total_cr):,.2f}', 0, 1, 'C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    pdf.set_font('Arial', 'I', 9)
    pdf.cell(0, 5, 'This is a system generated voucher.', 0, 1, 'C')
    pdf.cell(0, 5, f"Generated on: {get_ist_time()}", 0, 1, 'C')
    
    # Add account classification legend
    pdf.ln(3)
    pdf.set_font('Arial', 'I', 7)
    pdf.cell(0, 4, 'Account Classification Legend:', 0, 1, 'L')
    pdf.cell(0, 4, '• ASSETS & EXPENSES - Debit (Dr) | • LIABILITIES, EQUITY & INCOME - Credit (Cr)', 0, 1, 'L')
    
    return pdf
def generate_profit_loss_pdf(data, from_date, to_date):
    if FPDF is None:
        return None
    pdf = BankPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'PROFIT & LOSS STATEMENT', 0, 1, 'C')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, f"Period: {from_date} to {to_date}", 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, 'INCOME', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    total_income = 0
    for item in data['income']:
        pdf.cell(50, 6, item['name'], 0, 0, 'L')
        pdf.cell(0, 6, f"Rs. {item['amount']:,.2f}", 0, 1, 'R')
        total_income += item['amount']
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(50, 7, 'Total Income', 0, 0, 'L')
    pdf.cell(0, 7, f"Rs. {total_income:,.2f}", 0, 1, 'R')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, 'EXPENSES', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    total_expense = 0
    for item in data['expenses']:
        pdf.cell(50, 6, item['name'], 0, 0, 'L')
        pdf.cell(0, 6, f"Rs. {item['amount']:,.2f}", 0, 1, 'R')
        total_expense += item['amount']
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(50, 7, 'Total Expenses', 0, 0, 'L')
    pdf.cell(0, 7, f"Rs. {total_expense:,.2f}", 0, 1, 'R')
    pdf.ln(5)
    
    net = total_income - total_expense
    pdf.set_font('Arial', 'B', 12)
    if net >= 0:
        pdf.set_text_color(0, 128, 0)
        pdf.cell(0, 8, f"NET PROFIT: Rs. {net:,.2f}", 0, 1, 'C')
    else:
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 8, f"NET LOSS: Rs. {abs(net):,.2f}", 0, 1, 'C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    pdf.set_font('Arial', 'I', 9)
    pdf.cell(0, 5, f"Generated on: {get_ist_time()}", 0, 1, 'C')
    return pdf

def generate_balance_sheet_pdf(data):
    if FPDF is None:
        return None
    pdf = BankPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'BALANCE SHEET', 0, 1, 'C')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, f"As on: {data['as_on']}", 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, 'ASSETS', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    total_assets = 0
    for item in data['assets']:
        pdf.cell(60, 6, item['name'], 0, 0, 'L')
        pdf.cell(0, 6, f"Rs. {item['amount']:,.2f}", 0, 1, 'R')
        total_assets += item['amount']
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(60, 7, 'Total Assets', 0, 0, 'L')
    pdf.cell(0, 7, f"Rs. {total_assets:,.2f}", 0, 1, 'R')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, 'LIABILITIES', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    total_liabilities = 0
    for item in data['liabilities']:
        pdf.cell(60, 6, item['name'], 0, 0, 'L')
        pdf.cell(0, 6, f"Rs. {item['amount']:,.2f}", 0, 1, 'R')
        total_liabilities += item['amount']
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(60, 7, 'Total Liabilities', 0, 0, 'L')
    pdf.cell(0, 7, f"Rs. {total_liabilities:,.2f}", 0, 1, 'R')
    pdf.ln(5)
    
    if data.get('capital'):
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'CAPITAL / EQUITY', 0, 1, 'L')
        pdf.set_font('Arial', '', 10)
        pdf.cell(60, 6, 'Capital / Equity', 0, 0, 'L')
        pdf.cell(0, 6, f"Rs. {data['capital']:,.2f}", 0, 1, 'R')
        pdf.ln(3)
    
    pdf.set_font('Arial', 'B', 10)
    liabilities_plus_capital = total_liabilities + data.get('capital', 0)
    pdf.cell(60, 7, 'Total Assets', 0, 0, 'L')
    pdf.cell(0, 7, f"Rs. {total_assets:,.2f}", 0, 1, 'R')
    pdf.cell(60, 7, 'Total Liabilities + Capital', 0, 0, 'L')
    pdf.cell(0, 7, f"Rs. {liabilities_plus_capital:,.2f}", 0, 1, 'R')
    
    if abs(total_assets - liabilities_plus_capital) < 0.01:
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(0, 128, 0)
        pdf.cell(0, 7, '[OK] BALANCE SHEET IS BALANCED', 0, 1, 'C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    pdf.set_font('Arial', 'I', 9)
    pdf.cell(0, 5, f"Generated on: {get_ist_time()}", 0, 1, 'C')
    return pdf

def generate_trial_balance_pdf(data):
    if FPDF is None:
        return None
    pdf = BankPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'TRIAL BALANCE', 0, 1, 'C')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, f"As on: {data['as_on']}", 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(10, 7, 'S.No', 1)
    pdf.cell(80, 7, 'Account Head', 1)
    pdf.cell(45, 7, 'Debit (Dr)', 1, 0, 'R')
    pdf.cell(45, 7, 'Credit (Cr)', 1, 1, 'R')
    
    pdf.set_font('Arial', '', 9)
    total_dr = 0
    total_cr = 0
    for idx, entry in enumerate(data['entries'], 1):
        pdf.cell(10, 6, str(idx), 1)
        pdf.cell(80, 6, entry['account_head'], 1)
        pdf.cell(45, 6, f"{entry['debit']:,.2f}", 1, 0, 'R')
        pdf.cell(45, 6, f"{entry['credit']:,.2f}", 1, 1, 'R')
        total_dr += entry['debit']
        total_cr += entry['credit']
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(90, 7, 'TOTAL', 1)
    pdf.cell(45, 7, f"{total_dr:,.2f}", 1, 0, 'R')
    pdf.cell(45, 7, f"{total_cr:,.2f}", 1, 1, 'R')
    
    if abs(total_dr - total_cr) < 0.01:
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(0, 128, 0)
        pdf.cell(0, 7, '[OK] TRIAL BALANCE IS BALANCED', 0, 1, 'C')
    else:
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 7, f'[!!] MISMATCH: Rs. {abs(total_dr - total_cr):,.2f}', 0, 1, 'C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    pdf.set_font('Arial', 'I', 9)
    pdf.cell(0, 5, f"Generated on: {get_ist_time()}", 0, 1, 'C')
    return pdf

def generate_report_pdf(data, report_type, title):
    if FPDF is None:
        return None
    pdf = BankPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, title.upper(), 0, 1, 'C')
    pdf.ln(5)
    
    if isinstance(data, list) and len(data) > 0:
        columns = list(data[0].keys())
        col_widths = []
        for col in columns:
            max_len = len(col)
            for row in data:
                if len(str(row[col])) > max_len:
                    max_len = len(str(row[col]))
            col_widths.append(min(max_len * 2 + 4, 50))
        
        pdf.set_font('Arial', 'B', 9)
        for i, col in enumerate(columns):
            pdf.cell(col_widths[i], 7, col.upper(), 1, 0, 'C')
        pdf.ln()
        
        pdf.set_font('Arial', '', 8)
        for row in data:
            for i, col in enumerate(columns):
                value = str(row[col])
                if len(value) > 20:
                    value = value[:17] + '...'
                pdf.cell(col_widths[i], 6, value, 1, 0, 'L')
            pdf.ln()
    
    pdf.ln(5)
    pdf.set_font('Arial', 'I', 9)
    pdf.cell(0, 5, f"Generated on: {get_ist_time()}", 0, 1, 'C')
    return pdf

# ==================== CSS ====================
def load_enterprise_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    html, body, [class*="css"] { background-color: #f0f2f5; }
    .stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div, .stDateInput input, .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus, div[data-baseweb="select"] span, input, textarea { color: #0f172a !important; -webkit-text-fill-color: #0f172a !important; }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder { color: #94a3b8 !important; -webkit-text-fill-color: #94a3b8 !important; }
    .topbar { background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); color: white; padding: 1.2rem 2.5rem; border-radius: 14px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 2rem; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15); }
    .topbar h1 { margin: 0; font-size: 1.4rem; font-weight: 800; color: #ffffff !important; letter-spacing: -0.5px; }
    .topbar .subtitle { font-size: 0.7rem; opacity: 0.8; font-weight: 400; }
    .topbar .user { font-size: 0.9rem; font-weight: 500; background: rgba(255,255,255,0.15); padding: 0.5rem 1.2rem; border-radius: 20px; backdrop-filter: blur(5px); }
    .dash-card { background: white; border: none; border-radius: 16px; padding: 1.8rem 1.2rem; text-align: center; transition: transform 0.3s, box-shadow 0.3s; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 1rem; }
    .dash-card:hover { transform: translateY(-5px); box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); border-bottom: 3px solid #203a43; }
    .dash-card .icon { font-size: 2.5rem; margin-bottom: 0.5rem; display: block; }
    .dash-card h2 { font-size: 2rem; margin: 0.5rem 0; font-weight: 800; color: #0f172a; }
    .dash-card p { margin: 0; font-size: 0.8rem; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 1.2px; }
    .section-card { background: white; border-radius: 16px; padding: 2rem; margin-bottom: 1.5rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); border: 1px solid #f1f5f9; }
    .section-card h3 { font-size: 1.2rem; font-weight: 700; color: #1e293b; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 2px solid #f1f5f9; }
    .login-wrapper { display: flex; justify-content: center; align-items: center; min-height: 90vh; padding: 2rem; background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); }
    .login-box { width: 100%; max-width: 420px; background: white; padding: 3rem 2.5rem; border-radius: 24px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.3); text-align: center; animation: fadeIn 0.5s ease-in-out; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(-20px); } to { opacity: 1; transform: translateY(0); } }
    .login-box .bank-logo { font-size: 3.5rem; margin-bottom: 0.5rem; }
    .login-box h1 { margin-bottom: 0; font-size: 1.8rem; font-weight: 800; color: #0f172a; }
    .login-box .bank-subtitle { font-size: 0.9rem; color: #64748b; font-weight: 500; margin-bottom: 0.5rem; }
    .login-box p { color: #94a3b8; font-weight: 400; margin-bottom: 2rem; font-size: 0.9rem; }
    [data-testid="stSidebar"] { background-color: #0f2027 !important; border-right: none !important; }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }
    [data-testid="stSidebar"] .stButton>button { background: transparent !important; border: 1px solid transparent !important; text-align: left !important; padding: 0.7rem 1.2rem !important; border-radius: 10px !important; font-weight: 600; margin-bottom: 0.2rem; transition: all 0.2s ease; }
    [data-testid="stSidebar"] .stButton>button:hover, [data-testid="stSidebar"] .stButton>button:active { background: rgba(255,255,255,0.1) !important; color: #ffffff !important; transform: translateX(6px); }
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stTextArea>div>div>textarea { border-radius: 10px !important; border: 1.5px solid #e2e8f0 !important; padding: 0.6rem 1rem !important; background-color: #f8fafc !important; }
    .stButton>button { border-radius: 10px !important; font-weight: 700 !important; padding: 0.6rem 1.2rem !important; }
    div[data-testid="stFormSubmitButton"]>button, button[kind="primary"] { background: linear-gradient(135deg, #0f2027, #2c5364) !important; color: white !important; border: none !important; }
    .stDataFrame { border-radius: 12px !important; border: 1px solid #e2e8f0 !important; }
    .stDataFrame thead th { background-color: #f8fafc !important; font-weight: 700 !important; text-transform: uppercase; font-size: 0.75rem; }
    .stTabs [data-baseweb="tab-list"] { background-color: #f1f5f9; padding: 6px; border-radius: 12px; }
    .stTabs [aria-selected="true"] { background-color: white !important; color: #0f172a !important; }
    .alert { padding: 1rem 1.2rem; border-radius: 12px; margin: 0.8rem 0; font-weight: 600; }
    .alert-info { background: #eff6ff; border-left: 4px solid #3b82f6; color: #1e40af; }
    .alert-success { background: #f0fdf4; border-left: 4px solid #22c55e; color: #166534; }
    .alert-warning { background: #fffbeb; border-left: 4px solid #f59e0b; color: #92400e; }
    .alert-danger { background: #fef2f2; border-left: 4px solid #ef4444; color: #991b1b; }
    .delete-btn { background: #ef4444 !important; color: white !important; border: none !important; }
    .delete-btn:hover { background: #dc2626 !important; }
    </style>
    """, unsafe_allow_html=True)

# ==================== SESSION STATE ====================
def init_session_state():
    if 'user' not in st.session_state: 
        st.session_state.user = None
    if 'page' not in st.session_state: 
        st.session_state.page = 'dashboard'

# ==================== MAIN APP ====================
def main():
    st.set_page_config(page_title="Aasha Nidhi Bank - Balaramapuram", page_icon="🏦", layout="wide", initial_sidebar_state="expanded")
    init_database()
    create_default_admin()
    init_session_state()
    load_enterprise_css()
    
    if st.session_state.user is None:
        show_login()
    else:
        show_app()

def show_login():
    st.markdown("""
    <div class="login-wrapper">
        <div class="login-box">
            <div class="bank-logo">🏦</div>
            <h1>AASHA NIDHI PVT LIMITED</h1>
            <div class="bank-subtitle">BALARAMAPURAM</div>
            <p>Enterprise Banking Management Platform</p>
    """, unsafe_allow_html=True)
    
    u = st.text_input("Username", key="lu", placeholder="Enter your username")
    p = st.text_input("Password", type="password", key="lp", placeholder="Enter your password")
    
    st.markdown('<br>', unsafe_allow_html=True)
    if st.button("Secure Sign In", use_container_width=True, type="primary", key="bl"):
        user = login_user(u, p)
        if user:
            st.session_state.user = {'id': user[0], 'username': user[1], 'role': user[3]}
            st.rerun()
        else:
            st.error("Invalid credentials. Please try again.")
            
    st.markdown('<div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #e2e8f0;"><small style="color: #94a3b8;">Demo Access: <b>admin</b> / <b>admin123</b></small></div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

def show_app():
    st.markdown(f"""
    <div class="topbar">
        <div>
            <h1>🏦 AASHA NIDHI PVT LIMITED BANK</h1>
            <div class="subtitle">BALARAMAPURAM | Enterprise Banking System</div>
        </div>
        <div class="user">👤 {st.session_state.user["username"]} &nbsp;<span style="opacity:0.7; font-size:0.8rem;">({st.session_state.user["role"].upper()})</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown('<div style="padding: 1rem 0; text-align: center;"><img src="https://cdn-icons-png.flaticon.com/512/2830/2830284.png" width="60" style="opacity:0.9; margin-bottom: 10px;"/><h3 style="margin:0; font-weight:700; color:white; font-size: 1.1rem;">AASHA NIDHI BANK</h3><p style="margin:0; font-size:0.7rem; opacity:0.7; color:white;">Balaramapuram</p></div>', unsafe_allow_html=True)
        st.markdown('<hr style="border-color: rgba(255,255,255,0.1); margin-top: 0;">', unsafe_allow_html=True)
        
        menu = {
            'dashboard': '📊 Dashboard', 
            'customer_management': '👥 Customers', 
            'kyc_verification': '🔍 KYC Center', 
            'create_sb_account': '🏦 Open SB A/c', 
            'sb_accounts': '💰 SB Accounts', 
            'fixed_deposits': '💎 Fixed Deposits', 
            'recurring_deposits': '🔄 Recurring Dep.', 
            'transactions': '💳 Transactions', 
            'journal_vouchers': '📝 Journal Vouchers', 
            'income_expenses': '📈 Income & Exp.', 
            'interest_calculation': '📊 Interest Calc', 
            'trial_balance': '⚖️ Trial Balance', 
            'balance_sheet': '📊 Balance Sheet', 
            'profit_loss': '💵 Profit & Loss', 
            'reports': '📋 Reports Engine'
        } if st.session_state.user['role'] in ['admin', 'staff'] else {
            'dashboard': '📊 Dashboard', 
            'my_accounts': '💰 My Accounts', 
            'my_transactions': '💳 Transactions', 
            'my_details': '👤 Profile'
        }
        
        for k, v in menu.items():
            if st.sidebar.button(v, key=f"m_{k}", use_container_width=True):
                st.session_state.page = k
                st.rerun()
                
        st.markdown('<hr style="border-color: rgba(255,255,255,0.1); margin-bottom: 1rem;">', unsafe_allow_html=True)
        if st.sidebar.button("🚪 Sign Out", use_container_width=True, key="so"):
            st.session_state.user = None
            st.rerun()
    
    page = st.session_state.get('page', 'dashboard')
    
    if page == 'dashboard': dashboard()
    elif page == 'customer_management': customer_mgmt()
    elif page == 'kyc_verification': kyc_verify()
    elif page == 'create_sb_account': create_sb()
    elif page in ('sb_accounts', 'my_accounts'): sb_accounts()
    elif page == 'fixed_deposits': fixed_deposits()
    elif page == 'recurring_deposits': recurring_deposits()
    elif page in ('transactions', 'my_transactions'): transactions()
    elif page == 'journal_vouchers': journal_vouchers()
    elif page == 'income_expenses': income_expenses()
    elif page == 'interest_calculation': interest_calc()
    elif page == 'trial_balance': trial_balance()
    elif page == 'balance_sheet': balance_sheet()
    elif page == 'profit_loss': profit_loss()
    elif page == 'reports': reports()
    elif page == 'my_details': my_details()

# ==================== DASHBOARD ====================
def dashboard():
    c = get_db()
    cust = c.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    sb = c.execute("SELECT COUNT(*) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    bal = c.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    intt = c.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    kyc = c.execute("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'").fetchone()[0]
    
    cols = st.columns(4)
    with cols[0]: st.markdown(f'<div class="dash-card"><span class="icon">👥</span><h2>{cust}</h2><p>Total Customers</p></div>', unsafe_allow_html=True)
    with cols[1]: st.markdown(f'<div class="dash-card"><span class="icon">💰</span><h2>{sb}</h2><p>Active SB Accounts</p></div>', unsafe_allow_html=True)
    with cols[2]: st.markdown(f'<div class="dash-card"><span class="icon">🏦</span><h2>Rs{bal+intt:,.0f}</h2><p>Total SB Deposits</p></div>', unsafe_allow_html=True)
    with cols[3]: st.markdown(f'<div class="dash-card"><span class="icon">🔍</span><h2>{kyc}</h2><p>Pending KYC Approvals</p></div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    x1, x2 = st.columns([1.5, 1])
    with x1:
        st.markdown('<div class="section-card"><h3>📋 Recent Transactions</h3>', unsafe_allow_html=True)
        txns = c.execute("SELECT t.transaction_id,c.first_name||' '||c.last_name,t.transaction_type,t.amount,t.created_at FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id ORDER BY t.created_at DESC LIMIT 8").fetchall()
        if txns:
            df = pd.DataFrame(txns, columns=['Txn ID', 'Customer', 'Type', 'Amount', 'Date'])
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%d-%m-%Y %H:%M')
            st.dataframe(df.style.format({'Amount': 'Rs{:,.2f}'}), use_container_width=True, height=290)
        else:
            st.info("No recent transactions found.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with x2:
        st.markdown('<div class="section-card"><h3>📊 Accounts Distribution</h3>', unsafe_allow_html=True)
        accs = c.execute("SELECT account_type,COUNT(*) FROM accounts WHERE status='ACTIVE' GROUP BY account_type").fetchall()
        if accs:
            df = pd.DataFrame(accs, columns=['Type', 'Count'])
            fig = px.pie(df, values='Count', names='Type', hole=0.6, color_discrete_sequence=['#0f2027', '#2c5364', '#64748b'])
            fig.update_layout(height=280, margin=dict(t=10, b=10, l=10, r=10), showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No active accounts found.")
        st.markdown('</div>', unsafe_allow_html=True)
    c.close()

# ==================== CUSTOMER MANAGEMENT ====================
def customer_mgmt():
    t1, t2, t3, t4 = st.tabs(["Register New Customer", "View Customers", "Edit Customer (KYC Rejected)", "Edit Any Customer"])
    
    with t1:
        st.markdown('<div class="section-card"><h3>Register New Customer</h3>', unsafe_allow_html=True)
        with st.form("cr"):
            c1, c2 = st.columns(2)
            with c1: 
                fn = st.text_input("First Name*")
                ln = st.text_input("Last Name*")
                dob = st.date_input("Date of Birth*", min_value=date(1900, 1, 1))
                email = st.text_input("Email Address*")
                phone = st.text_input("Phone Number*")
            with c2: 
                pan = st.text_input("PAN Number*")
                aadhar = st.text_input("Aadhar Number*")
                addr = st.text_area("Full Address")
                col_c1, col_c2 = st.columns(2)
                with col_c1: city = st.text_input("City")
                with col_c2: state = st.text_input("State")
                pin = st.text_input("PIN Code")
                
            st.markdown("#### Document Uploads")
            doc1, doc2 = st.columns(2)
            with doc1: pan_doc = st.file_uploader("Upload PAN Card*", type=['jpg', 'jpeg', 'png', 'pdf'], key="pu")
            with doc2: aadhar_doc = st.file_uploader("Upload Aadhar Card*", type=['jpg', 'jpeg', 'png', 'pdf'], key="au")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("Create Customer Profile", use_container_width=True, type="primary"):
                if not all([fn, ln, email, phone, pan, aadhar]):
                    st.error("Please fill all required (*) fields.")
                elif not pan_doc or not aadhar_doc:
                    st.error("Please upload both required documents.")
                else:
                    try:
                        conn = get_db()
                        cid = generate_id('CUST')
                        conn.execute("INSERT INTO customers (customer_id,first_name,last_name,date_of_birth,email,phone,address,city,state,pincode,pan_number,aadhar_number,pan_document,aadhar_document) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (cid, fn, ln, dob, email, phone, addr, city, state, pin, pan, aadhar, pan_doc.read(), aadhar_doc.read()))
                        conn.commit()
                        conn.close()
                        st.success(f"Customer successfully registered! ID: {cid}")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Database Error: {str(e)}")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with t2:
        st.markdown('<div class="section-card"><h3>Customer Directory</h3>', unsafe_allow_html=True)
        conn = get_db()
        custs = conn.execute("SELECT id,customer_id,first_name,last_name,email,phone,city,kyc_status FROM customers ORDER BY customer_id DESC").fetchall()
        if custs:
            df = pd.DataFrame(custs, columns=['ID','Customer ID', 'First Name', 'Last Name', 'Email', 'Phone', 'City', 'KYC Status'])
            st.dataframe(df, use_container_width=True, height=450)
            
            st.markdown("---")
            st.warning("Delete Customer (This action cannot be undone)")
            del_cust = st.selectbox("Select Customer to Delete", [f"{c[1]} - {c[2]} {c[3]}" for c in custs], key="del_cust")
            if del_cust and st.button("Delete Customer", use_container_width=True, key="del_cust_btn"):
                idx = [f"{c[1]} - {c[2]} {c[3]}" for c in custs].index(del_cust)
                cust_id = custs[idx][0]
                if st.button("Confirm Delete", use_container_width=True, key="confirm_del_cust"):
                    delete_record('customers', 'id', cust_id, 'Customer')
        else:
            st.info("No customers registered yet.")
        conn.close()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with t3:
        st.markdown('<div class="section-card"><h3>Edit Customer Details (For KYC Rejected Cases)</h3>', unsafe_allow_html=True)
        conn = get_db()
        rejected_custs = conn.execute("SELECT id, customer_id, first_name, last_name, email, phone, address, city, state, pincode, pan_number, aadhar_number, kyc_status, date_of_birth FROM customers WHERE kyc_status IN ('REJECTED', 'PENDING') ORDER BY created_at DESC").fetchall()
        
        if not rejected_custs:
            st.info("No customers with rejected or pending KYC status found.")
        else:
            sel = st.selectbox("Select Customer to Edit", [f"{c[1]} - {c[2]} {c[3]} ({c[12]})" for c in rejected_custs], key="edit_rejected_cust")
            if sel:
                idx = [f"{c[1]} - {c[2]} {c[3]} ({c[12]})" for c in rejected_custs].index(sel)
                cust = rejected_custs[idx]
                
                with st.form("edit_cust_rejected"):
                    st.warning(f"Editing Customer ID: {cust[1]} | Current KYC Status: {cust[12]}")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        fn = st.text_input("First Name*", value=cust[2])
                        ln = st.text_input("Last Name*", value=cust[3])
                        try:
                            dob_val = datetime.strptime(str(cust[13])[:10], '%Y-%m-%d').date() if cust[13] else date(2000, 1, 1)
                        except:
                            dob_val = date(2000, 1, 1)
                        dob = st.date_input("Date of Birth*", value=dob_val)
                        email = st.text_input("Email Address*", value=cust[4])
                        phone = st.text_input("Phone Number*", value=cust[5])
                    with c2:
                        pan = st.text_input("PAN Number*", value=cust[10] if cust[10] else "")
                        aadhar = st.text_input("Aadhar Number*", value=cust[11] if cust[11] else "")
                        addr = st.text_area("Full Address", value=cust[6] if cust[6] else "")
                        col_c1, col_c2 = st.columns(2)
                        with col_c1: city = st.text_input("City", value=cust[7] if cust[7] else "")
                        with col_c2: state = st.text_input("State", value=cust[8] if cust[8] else "")
                        pin = st.text_input("PIN Code", value=cust[9] if cust[9] else "")
                    
                    st.markdown("#### Update Documents (Upload new to replace)")
                    doc1, doc2 = st.columns(2)
                    with doc1: pan_doc = st.file_uploader("Upload PAN Card (Leave empty to keep existing)", type=['jpg', 'jpeg', 'png', 'pdf'], key="epu_rejected")
                    with doc2: aadhar_doc = st.file_uploader("Upload Aadhar Card (Leave empty to keep existing)", type=['jpg', 'jpeg', 'png', 'pdf'], key="eau_rejected")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.info("After editing, the KYC status will be reset to PENDING for re-verification.")
                    
                    if st.form_submit_button("Update Customer & Send for Re-verification", use_container_width=True, type="primary"):
                        try:
                            update_query = """UPDATE customers SET first_name=?, last_name=?, date_of_birth=?, email=?, phone=?, address=?, city=?, state=?, pincode=?, pan_number=?, aadhar_number=?, kyc_status='PENDING', kyc_verified_by=NULL, kyc_verified_at=NULL"""
                            params = [fn, ln, dob, email, phone, addr, city, state, pin, pan, aadhar]
                            
                            if pan_doc:
                                update_query += ", pan_document=?"
                                params.append(pan_doc.read())
                            if aadhar_doc:
                                update_query += ", aadhar_document=?"
                                params.append(aadhar_doc.read())
                            
                            update_query += " WHERE id=?"
                            params.append(cust[0])
                            
                            conn.execute(update_query, params)
                            conn.commit()
                            st.success(f"Customer {cust[1]} updated successfully!")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Update Error: {str(e)}")
        conn.close()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with t4:
        st.markdown('<div class="section-card"><h3>Edit Any Customer (No KYC Restriction)</h3>', unsafe_allow_html=True)
        conn = get_db()
        all_custs = conn.execute("SELECT id, customer_id, first_name, last_name, email, phone, address, city, state, pincode, pan_number, aadhar_number, kyc_status, date_of_birth FROM customers ORDER BY created_at DESC").fetchall()
        
        if not all_custs:
            st.info("No customers found in the system.")
        else:
            sel = st.selectbox("Select Customer to Edit", [f"{c[1]} - {c[2]} {c[3]} ({c[12]})" for c in all_custs], key="edit_any_cust")
            if sel:
                idx = [f"{c[1]} - {c[2]} {c[3]} ({c[12]})" for c in all_custs].index(sel)
                cust = all_custs[idx]
                
                with st.form("edit_cust_any"):
                    current_kyc = cust[12]
                    if current_kyc == 'VERIFIED':
                        st.success(f"Editing Customer ID: {cust[1]} | Current KYC Status: {current_kyc}")
                    elif current_kyc == 'PENDING':
                        st.warning(f"Editing Customer ID: {cust[1]} | Current KYC Status: {current_kyc}")
                    else:
                        st.error(f"Editing Customer ID: {cust[1]} | Current KYC Status: {current_kyc}")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        fn = st.text_input("First Name*", value=cust[2])
                        ln = st.text_input("Last Name*", value=cust[3])
                        try:
                            dob_val = datetime.strptime(str(cust[13])[:10], '%Y-%m-%d').date() if cust[13] else date(2000, 1, 1)
                        except:
                            dob_val = date(2000, 1, 1)
                        dob = st.date_input("Date of Birth*", value=dob_val)
                        email = st.text_input("Email Address*", value=cust[4])
                        phone = st.text_input("Phone Number*", value=cust[5])
                    with c2:
                        pan = st.text_input("PAN Number*", value=cust[10] if cust[10] else "")
                        aadhar = st.text_input("Aadhar Number*", value=cust[11] if cust[11] else "")
                        addr = st.text_area("Full Address", value=cust[6] if cust[6] else "")
                        col_c1, col_c2 = st.columns(2)
                        with col_c1: city = st.text_input("City", value=cust[7] if cust[7] else "")
                        with col_c2: state = st.text_input("State", value=cust[8] if cust[8] else "")
                        pin = st.text_input("PIN Code", value=cust[9] if cust[9] else "")
                    
                    st.markdown("#### Update Documents (Upload new to replace)")
                    doc1, doc2 = st.columns(2)
                    with doc1: pan_doc = st.file_uploader("Upload PAN Card (Leave empty to keep existing)", type=['jpg', 'jpeg', 'png', 'pdf'], key="ap1_any")
                    with doc2: aadhar_doc = st.file_uploader("Upload Aadhar Card (Leave empty to keep existing)", type=['jpg', 'jpeg', 'png', 'pdf'], key="ap2_any")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    new_kyc_status = st.selectbox("Update KYC Status (Optional)", ["KEEP_CURRENT", "VERIFIED", "PENDING", "REJECTED"], help="Select 'KEEP_CURRENT' to maintain existing KYC status", key="kyc_status_any")
                    
                    if new_kyc_status != "KEEP_CURRENT":
                        st.warning(f"KYC status will be changed to: {new_kyc_status}")
                    
                    if st.form_submit_button("Update Customer Details", use_container_width=True, type="primary"):
                        try:
                            update_query = """UPDATE customers SET first_name=?, last_name=?, date_of_birth=?, email=?, phone=?, address=?, city=?, state=?, pincode=?, pan_number=?, aadhar_number=?"""
                            params = [fn, ln, dob, email, phone, addr, city, state, pin, pan, aadhar]
                            
                            if new_kyc_status != "KEEP_CURRENT":
                                update_query += ", kyc_status=?"
                                params.append(new_kyc_status)
                                if new_kyc_status == "VERIFIED":
                                    update_query += ", kyc_verified_by=?, kyc_verified_at=CURRENT_TIMESTAMP"
                                    params.append(st.session_state.user['id'])
                                else:
                                    update_query += ", kyc_verified_by=NULL, kyc_verified_at=NULL"
                            
                            if pan_doc:
                                update_query += ", pan_document=?"
                                params.append(pan_doc.read())
                            if aadhar_doc:
                                update_query += ", aadhar_document=?"
                                params.append(aadhar_doc.read())
                            
                            update_query += " WHERE id=?"
                            params.append(cust[0])
                            
                            conn.execute(update_query, params)
                            conn.commit()
                            st.success(f"Customer {cust[1]} updated successfully!")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Update Error: {str(e)}")
        conn.close()
        st.markdown('</div>', unsafe_allow_html=True)

# ==================== KYC VERIFICATION ====================
def kyc_verify():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("Unauthorized Access."); return
        
    c = get_db()
    pending = c.execute("SELECT * FROM customers WHERE kyc_status='PENDING' ORDER BY created_at").fetchall()
    
    st.markdown('<div class="section-card"><h3>KYC Approval Center</h3>', unsafe_allow_html=True)
    if not pending:
        st.markdown('<div class="alert alert-success">All customer accounts are verified!</div>', unsafe_allow_html=True)
    else:
        for cust in pending:
            with st.expander(f"{cust[3]} {cust[4]} (ID: {cust[2]}) - Pending Verification", expanded=False):
                st.markdown(f"**Name:** {cust[3]} {cust[4]} | **Email:** {cust[7]} | **Phone:** {cust[8]} | **PAN:** {cust[12]}")
                b1, b2, b3 = st.columns([1, 1, 2])
                with b1:
                    if st.button("Approve KYC", key=f"a_{cust[0]}", use_container_width=True, type="primary"):
                        c.execute("UPDATE customers SET kyc_status='VERIFIED',kyc_verified_by=?,kyc_verified_at=CURRENT_TIMESTAMP WHERE id=?", (st.session_state.user['id'], cust[0]))
                        c.commit()
                        st.success("KYC Approved Successfully!")
                        st.rerun()
                with b2:
                    if st.button("Reject KYC", key=f"r_{cust[0]}", use_container_width=True):
                        c.execute("UPDATE customers SET kyc_status='REJECTED' WHERE id=?", (cust[0],))
                        c.commit()
                        st.error("KYC Rejected! Customer can edit and resubmit.")
                        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    c.close()

# ==================== CREATE SB ACCOUNT ====================
def create_sb():
    if st.session_state.user['role'] not in ['admin', 'staff']: 
        st.error("Unauthorized"); return
        
    c = get_db()
    custs = c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c WHERE NOT EXISTS (SELECT 1 FROM accounts a WHERE a.customer_id=c.id AND a.account_type='SB' AND a.status='ACTIVE')").fetchall()
    
    st.markdown('<div class="section-card"><h3>Open Savings Account</h3>', unsafe_allow_html=True)
    if not custs:
        st.markdown('<div class="alert alert-success">All customers already have an SB account!</div>', unsafe_allow_html=True)
    else:
        cust_list = []
        for x in custs:
            kyc_status = c.execute("SELECT kyc_status FROM customers WHERE id=?", (x[0],)).fetchone()[0]
            status_icon = "OK" if kyc_status == 'VERIFIED' else "!!" if kyc_status == 'PENDING' else "XX"
            cust_list.append(f"{x[1]} - {x[2]} (KYC: {status_icon} {kyc_status})")
        
        sel = st.selectbox("Select Customer", cust_list)
        if sel:
            idx = cust_list.index(sel)
            cust = custs[idx]
            kyc_status = c.execute("SELECT kyc_status FROM customers WHERE id=?", (cust[0],)).fetchone()[0]
            
            if kyc_status == 'VERIFIED':
                st.success("Customer KYC is VERIFIED")
            elif kyc_status == 'PENDING':
                st.warning("Customer KYC is PENDING - Account can still be opened")
            else:
                st.warning("Customer KYC is REJECTED - Account can still be opened")
            
            with st.form("sb"):
                c1, c2 = st.columns(2)
                with c1: rate = st.number_input("Interest Rate (%)", 0.0, 10.0, 3.5, 0.25)
                with c2: bal = st.number_input("Opening Balance (Rs)", 0.0, step=100.0)
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("Create Account", use_container_width=True, type="primary"):
                    an = generate_account_number('SB')
                    c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate,last_interest_calculation,total_interest_earned) VALUES (?,?,'SB',?,?,DATE('now'),0.00)", (an, cust[0], bal, rate))
                    c.commit()
                    st.success(f"Savings Account Created! Account Number: {an}")
                    st.balloons()
    st.markdown('</div>', unsafe_allow_html=True)
    c.close()

# ==================== SB ACCOUNTS ====================
def sb_accounts():
    c = get_db()
    t1, t2, t3, t4 = st.tabs(["Account List", "Transact", "Statement", "Deposits Summary"])
    role = st.session_state.user['role']
    uid = st.session_state.user['id']
    
    with t1:
        st.markdown('<div class="section-card"><h3>Savings Accounts Overview</h3>', unsafe_allow_html=True)
        q = "SELECT a.id,a.account_number,c.first_name||' '||c.last_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND " + ("c.user_id=?" if role == 'customer' else "1=1")
        accs = c.execute(q, (uid,) if role == 'customer' else ()).fetchall()
        if accs:
            data = [{'Account Number': a[1], 'Customer Name': a[2], 'Total Deposits (Rs)': a[3], 'Rate': f"{a[4]:.2f}%", 'Interest Earned (Rs)': a[5], 'Total Amount (Rs)': a[3]+a[5]} for a in accs]
            st.dataframe(pd.DataFrame(data).style.format({'Total Deposits (Rs)': 'Rs{:,.2f}', 'Interest Earned (Rs)': 'Rs{:,.2f}', 'Total Amount (Rs)': 'Rs{:,.2f}'}), use_container_width=True, height=350)
            
            st.markdown("---")
            st.warning("Delete Account (This action cannot be undone)")
            del_acc = st.selectbox("Select Account to Delete", [f"{a[1]} - {a[2]}" for a in accs], key="del_sb_acc")
            if del_acc and st.button("Delete Account", use_container_width=True, key="del_sb_acc_btn"):
                idx = [f"{a[1]} - {a[2]}" for a in accs].index(del_acc)
                acc_id = accs[idx][0]
                if st.button("Confirm Delete", use_container_width=True, key="confirm_del_sb_acc"):
                    delete_record('accounts', 'id', acc_id, 'SB Account')
        else:
            st.info("No active accounts found.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with t2:
        st.markdown('<div class="section-card"><h3>Deposit & Withdraw Funds</h3>', unsafe_allow_html=True)
        q2 = "SELECT a.id,a.account_number,c.first_name||' '||c.last_name,a.balance,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND " + ("c.user_id=?" if role == 'customer' else "1=1")
        accs = c.execute(q2, (uid,) if role == 'customer' else ()).fetchall()
        if accs:
            sel = st.selectbox("Select Account", [f"{a[1]} - {a[2]} (Total Amount: Rs{a[3]+a[4]:,.2f})" for a in accs])
            if sel:
                idx = [f"{a[1]} - {a[2]} (Total Amount: Rs{a[3]+a[4]:,.2f})" for a in accs].index(sel)
                acc = accs[idx]
                st.markdown("<br>", unsafe_allow_html=True)
                tt = st.radio("Transaction Type", ["Deposit", "Withdraw"], horizontal=True)
                with st.form("tx"):
                    amt = st.number_input("Amount (Rs)", min_value=0.01, step=100.0)
                    c1, c2 = st.columns(2)
                    with c1: desc = st.text_input("Description / Notes")
                    with c2: mode = st.selectbox("Transaction Mode", ["CASH", "BANK", "CHEQUE"])
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.form_submit_button("Process Transaction", use_container_width=True, type="primary"):
                        at = "DEPOSIT" if tt == "Deposit" else "WITHDRAWAL"
                        if at == "WITHDRAWAL" and amt > acc[3]:
                            st.error("Insufficient Funds for this withdrawal!")
                        else:
                            nb = acc[3]+amt if at == "DEPOSIT" else acc[3]-amt
                            tdb = "CREDIT" if at == "DEPOSIT" else "DEBIT"
                            vt = "RECEIPT" if at == "DEPOSIT" else "PAYMENT"
                            
                            c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,?,?,?,?,?,?,?,?)", (generate_id('TXN'), acc[0], tdb, amt, nb, desc, mode, vt, generate_voucher_number(vt), uid))
                            c.execute("UPDATE accounts SET balance=? WHERE id=?", (nb, acc[0]))
                            c.commit()
                            st.success(f"Transaction Successful! New Total Amount: Rs{nb+acc[4]:,.2f}")
                            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with t3:
        st.markdown('<div class="section-card"><h3>Account Statement</h3>', unsafe_allow_html=True)
        q3 = "SELECT a.id,a.account_number,c.id as customer_id,c.customer_id as cust_id,c.first_name||' '||c.last_name as customer_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND " + ("c.user_id=?" if role == 'customer' else "1=1")
        accs = c.execute(q3, (uid,) if role == 'customer' else ()).fetchall()
        
        if accs:
            sel = st.selectbox("Choose Account", [f"{a[1]} - {a[4]}" for a in accs], key="ss")
            if sel:
                idx = [f"{a[1]} - {a[4]}" for a in accs].index(sel)
                acc_data = accs[idx]
                aid = acc_data[0]
                account_number = acc_data[1]
                cust_id_display = acc_data[3]
                customer_name = acc_data[4]
                balance = acc_data[5]
                interest_rate = acc_data[6]
                total_interest = acc_data[7]
                
                d1, d2 = st.columns(2)
                with d1: fd = st.date_input("From Date", date.today()-timedelta(days=30), key="sf")
                with d2: td = st.date_input("To Date", date.today(), key="st")
                
                if fd <= td:
                    txns = c.execute("""SELECT transaction_id, created_at, transaction_type, amount, balance_after, description, voucher_number FROM transactions WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ? ORDER BY created_at DESC""", (aid, fd, td)).fetchall()
                    
                    if txns:
                        txn_data = []
                        for txn in txns:
                            if isinstance(txn[1], str):
                                date_obj = datetime.strptime(txn[1], '%Y-%m-%d %H:%M:%S')
                            else:
                                date_obj = txn[1]
                            
                            txn_data.append({
                                'Date': date_obj.strftime('%d-%m-%Y %H:%M'),
                                'Type': txn[2],
                                'Description': txn[5],
                                'Credit': txn[3] if txn[2] == 'CREDIT' else 0,
                                'Debit': txn[3] if txn[2] == 'DEBIT' else 0,
                                'Balance': txn[4],
                                'Voucher': txn[6]
                            })
                        
                        df = pd.DataFrame(txn_data)
                        st.dataframe(df.style.format({'Credit': 'Rs{:,.2f}', 'Debit': 'Rs{:,.2f}', 'Balance': 'Rs{:,.2f}'}), use_container_width=True, height=350)
                        
                        st.markdown("---")
                        st.markdown("#### Account Summary")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1: st.metric("Total Deposits", f"Rs{balance:,.2f}")
                        with col2: st.metric("Total Interest", f"Rs{total_interest:,.2f}")
                        with col3: st.metric("Interest Rate", f"{interest_rate}%")
                        with col4: st.metric("Total Amount", f"Rs{balance + total_interest:,.2f}")
                        
                        st.markdown("---")
                        if st.button("Print Statement (PDF)", use_container_width=True, type="primary"):
                            pdf_data = {
                                'account_number': account_number,
                                'total_deposits': balance,
                                'total_interest': total_interest,
                                'total_amount': balance + total_interest,
                                'interest_rate': interest_rate,
                                'interest_calculated': 0
                            }
                            
                            customer_data = {'customer_id': cust_id_display, 'customer_name': customer_name}
                            
                            pdf_txns = []
                            for txn in txns:
                                if isinstance(txn[1], str):
                                    date_obj = datetime.strptime(txn[1], '%Y-%m-%d %H:%M:%S')
                                else:
                                    date_obj = txn[1]
                                pdf_txns.append({
                                    'date': date_obj.strftime('%d-%m-%Y'),
                                    'type': txn[2],
                                    'description': txn[5],
                                    'credit': txn[3] if txn[2] == 'CREDIT' else 0,
                                    'debit': txn[3] if txn[2] == 'DEBIT' else 0,
                                    'balance': txn[4]
                                })
                            
                            pdf = generate_statement_pdf(pdf_data, pdf_txns, customer_data, fd.strftime('%d-%m-%Y'), td.strftime('%d-%m-%Y'))
                            
                            if pdf:
                                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                                    pdf.output(tmp_file.name)
                                    tmp_file.flush()
                                    with open(tmp_file.name, 'rb') as f:
                                        pdf_bytes = f.read()
                                    os.unlink(tmp_file.name)
                                
                                st.download_button(label="Download Statement PDF", data=pdf_bytes, file_name=f"Statement_{account_number}_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True)
                                st.success("Statement generated successfully!")
                            else:
                                st.error("PDF generation library not available.")
                    else:
                        st.info("No transactions found in this period.")
                else:
                    st.error("From Date must be before To Date")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with t4:
        st.markdown('<div class="section-card"><h3>Deposits Summary</h3>', unsafe_allow_html=True)
        q4 = "SELECT a.account_number,c.first_name||' '||c.last_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND " + ("c.user_id=?" if role == 'customer' else "1=1")
        accs = c.execute(q4, (uid,) if role == 'customer' else ()).fetchall()
        if accs:
            data = [{'Account': a[0], 'Customer': a[1], 'Total Deposits': a[2], 'Rate': f"{a[3]:.2f}%", 'Interest': a[4], 'Total Amount': a[2]+a[4]} for a in accs]
            
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("Total Deposits", f"Rs{sum(d['Total Deposits'] for d in data):,.2f}")
            with m2: st.metric("Total Interest", f"Rs{sum(d['Interest'] for d in data):,.2f}")
            with m3: st.metric("Gross Total", f"Rs{sum(d['Total Amount'] for d in data):,.2f}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(data).style.format({'Total Deposits': 'Rs{:,.2f}', 'Interest': 'Rs{:,.2f}', 'Total Amount': 'Rs{:,.2f}'}), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    c.close()

# ==================== FIXED DEPOSITS ====================
def fixed_deposits():
    c = get_db()
    uid = st.session_state.user['id']
    t1, t2, t3 = st.tabs(["Open FD", "Active FDs", "Maturity Alerts"])
    
    with t1:
        st.markdown('<div class="section-card"><h3>Open Fixed Deposit</h3>', unsafe_allow_html=True)
        custs = c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        if custs:
            sel = st.selectbox("Select Customer", [f"{x[1]} - {x[2]}" for x in custs])
            if sel:
                idx = [f"{x[1]} - {x[2]}" for x in custs].index(sel)
                cust = custs[idx]
                with st.form("fd"):
                    d1, d2 = st.columns(2)
                    with d1: 
                        p = st.number_input("Principal Amount (Rs)", min_value=1000.0, step=1000.0, value=10000.0)
                        t = st.selectbox("Tenure (Months)", [1, 3, 6, 9, 12, 18, 24, 36, 48, 60])
                        r = st.number_input("Interest Rate (%)", 3.0, 10.0, 6.5, 0.25)
                    with d2: 
                        sd = st.date_input("Start Date", date.today(), key="fs")
                        nom = st.text_input("Nominee Name")
                        nom_rel = st.text_input("Nominee Relation")
                    
                    md = sd + relativedelta(months=t)
                    ma = calculate_fd_maturity(p, r, t)
                    
                    st.info(f"Calculated Maturity Date: **{md.strftime('%d-%m-%Y')}** | Maturity Value: **Rs{ma:,.2f}**")
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    if st.form_submit_button("Open Fixed Deposit", use_container_width=True, type="primary"):
                        fdn = generate_id('FD')
                        an = generate_account_number('FD')
                        c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate) VALUES (?,?,'FD',0.00,?)", (an, cust[0], r))
                        aid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                        c.execute("INSERT INTO fixed_deposits (fd_number,account_id,principal_amount,interest_rate,start_date,maturity_date,maturity_amount,tenure_months,nominee_name,nominee_relation) VALUES (?,?,?,?,?,?,?,?,?,?)", (fdn, aid, p, r, sd, md, ma, t, nom, nom_rel))
                        c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,'FD','FD_DEPOSIT','RECEIPT',?,?)", (generate_id('TXN'), aid, p, p, generate_voucher_number('RECEIPT'), uid))
                        c.commit()
                        st.success(f"FD Successfully Opened! FD ID: {fdn}")
                        st.balloons()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with t2:
        st.markdown('<div class="section-card"><h3>Active Fixed Deposits</h3>', unsafe_allow_html=True)
        fds = c.execute("""SELECT fd.id, fd.fd_number, c.first_name||' '||c.last_name, fd.principal_amount, fd.interest_rate, fd.start_date, fd.maturity_date, fd.maturity_amount, fd.tenure_months, fd.nominee_name, fd.nominee_relation, fd.status, c.id as customer_id, a.account_number FROM fixed_deposits fd JOIN accounts a ON fd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE fd.status='ACTIVE' ORDER BY fd.maturity_date""").fetchall()
        
        if fds:
            df_data = []
            for fd in fds:
                start_date = fd[5]
                maturity_date = fd[6]
                
                if isinstance(start_date, str):
                    try: start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                    except: start_date = date.today()
                elif isinstance(start_date, datetime): start_date = start_date.date()
                
                if isinstance(maturity_date, str):
                    try: maturity_date = datetime.strptime(maturity_date, '%Y-%m-%d').date()
                    except: maturity_date = date.today()
                elif isinstance(maturity_date, datetime): maturity_date = maturity_date.date()
                
                df_data.append({'FD Ref': fd[1], 'Customer': fd[2], 'Principal (Rs)': fd[3], 'Rate': f"{fd[4]:.2f}%", 'Start Date': start_date.strftime('%d-%m-%Y') if start_date else 'N/A', 'Maturity Date': maturity_date.strftime('%d-%m-%Y') if maturity_date else 'N/A', 'Maturity Value (Rs)': fd[7], 'Tenure': f"{fd[8]} months", 'Nominee': fd[9] or 'N/A', 'Status': fd[11]})
            
            if df_data:
                st.dataframe(pd.DataFrame(df_data).style.format({'Principal (Rs)': 'Rs{:,.2f}', 'Maturity Value (Rs)': 'Rs{:,.2f}'}), use_container_width=True)
                
                st.markdown("---")
                st.warning("Delete Fixed Deposit (This action cannot be undone)")
                del_fd = st.selectbox("Select FD to Delete", [f"{fd[1]} - {fd[2]}" for fd in fds], key="del_fd")
                if del_fd and st.button("Delete FD", use_container_width=True, key="del_fd_btn"):
                    idx = [f"{fd[1]} - {fd[2]}" for fd in fds].index(del_fd)
                    fd_id = fds[idx][0]
                    if st.button("Confirm Delete", use_container_width=True, key="confirm_del_fd"):
                        delete_record('fixed_deposits', 'id', fd_id, 'Fixed Deposit')
                
                st.markdown("---")
                st.subheader("Print FD Receipt")
                
                fd_options = [f"{fd[1]} - {fd[2]} (Rs{fd[7]:,.2f})" for fd in fds]
                selected_fd = st.selectbox("Select FD to print receipt", fd_options, key="fd_print")
                
                if selected_fd and st.button("Print FD Receipt (PDF)", use_container_width=True, type="primary"):
                    fd_idx = fd_options.index(selected_fd)
                    fd = fds[fd_idx]
                    
                    customer_data = {'customer_id': fd[12], 'customer_name': fd[2]}
                    cust_info = c.execute("SELECT address, phone FROM customers WHERE id=?", (fd[12],)).fetchone()
                    if cust_info:
                        customer_data['address'] = cust_info[0] or 'N/A'
                        customer_data['phone'] = cust_info[1] or 'N/A'
                    
                    start_date = fd[5]
                    maturity_date = fd[6]
                    if isinstance(start_date, str):
                        try: start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                        except: start_date = date.today()
                    elif isinstance(start_date, datetime): start_date = start_date.date()
                    if isinstance(maturity_date, str):
                        try: maturity_date = datetime.strptime(maturity_date, '%Y-%m-%d').date()
                        except: maturity_date = date.today()
                    elif isinstance(maturity_date, datetime): maturity_date = maturity_date.date()
                    
                    fd_data = {'fd_number': fd[1], 'account_number': fd[13], 'principal': fd[3], 'interest_rate': fd[4], 'start_date': start_date.strftime('%d-%m-%Y') if start_date else 'N/A', 'maturity_date': maturity_date.strftime('%d-%m-%Y') if maturity_date else 'N/A', 'maturity_amount': fd[7], 'tenure_months': fd[8], 'nominee_name': fd[9], 'nominee_relation': fd[10], 'status': fd[11], 'total_interest': fd[7] - fd[3]}
                    
                    pdf = generate_fd_statement_pdf(fd_data, customer_data)
                    
                    if pdf:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                            pdf.output(tmp_file.name)
                            tmp_file.flush()
                            with open(tmp_file.name, 'rb') as f: pdf_bytes = f.read()
                            os.unlink(tmp_file.name)
                        
                        st.download_button(label="Download FD Receipt PDF", data=pdf_bytes, file_name=f"FD_Receipt_{fd[1]}_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True)
                        st.success("FD Receipt generated successfully!")
                    else:
                        st.error("PDF generation library not available.")
        else:
            st.info("No active FDs found in the system.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with t3:
        st.markdown('<div class="section-card"><h3>Upcoming FD Maturities (Next 30 Days)</h3>', unsafe_allow_html=True)
        today = date.today()
        mat = c.execute("""SELECT fd.fd_number, c.first_name||' '||c.last_name, fd.maturity_amount, fd.maturity_date FROM fixed_deposits fd JOIN accounts a ON fd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE fd.maturity_date BETWEEN ? AND ? AND fd.status='ACTIVE'""", (today, today+timedelta(days=30))).fetchall()
        if mat:
            st.warning(f"{len(mat)} accounts are maturing soon")
            mat_data = []
            for m in mat:
                maturity_date = m[3]
                if isinstance(maturity_date, str):
                    try: maturity_date = datetime.strptime(maturity_date, '%Y-%m-%d').date()
                    except: maturity_date = date.today()
                elif isinstance(maturity_date, datetime): maturity_date = maturity_date.date()
                mat_data.append({'FD Ref': m[0], 'Customer': m[1], 'Maturity Value': m[2], 'Maturity Date': maturity_date.strftime('%d-%m-%Y') if maturity_date else 'N/A'})
            st.dataframe(pd.DataFrame(mat_data).style.format({'Maturity Value': 'Rs{:,.2f}'}), use_container_width=True)
        else:
            st.success("No imminent maturities to process.")
        st.markdown('</div>', unsafe_allow_html=True)
    c.close()

# ==================== RECURRING DEPOSITS ====================
def recurring_deposits():
    c = get_db()
    uid = st.session_state.user['id']
    t1, t2, t3 = st.tabs(["Open RD", "Active RDs", "Pay Installment"])
    
    with t1:
        st.markdown('<div class="section-card"><h3>Open Recurring Deposit</h3>', unsafe_allow_html=True)
        custs = c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        if custs:
            sel = st.selectbox("Select Customer", [f"{x[1]} - {x[2]}" for x in custs])
            if sel:
                idx = [f"{x[1]} - {x[2]}" for x in custs].index(sel)
                cust = custs[idx]
                with st.form("rd"):
                    d1, d2 = st.columns(2)
                    with d1: 
                        m = st.number_input("Monthly Installment (Rs)", min_value=100.0, step=100.0, value=1000.0)
                        t = st.selectbox("Tenure (Months)", [3, 6, 9, 12, 18, 24, 36, 48, 60])
                        r = st.number_input("Interest Rate (%)", 3.0, 10.0, 6.0, 0.25)
                    with d2: 
                        sd = st.date_input("Start Date", date.today(), key="rs")
                        nom = st.text_input("Nominee Name")
                        nom_rel = st.text_input("Nominee Relation")
                    
                    md = sd + relativedelta(months=t)
                    ma = calculate_rd_maturity(m, r, t)
                    
                    st.info(f"Calculated Maturity Date: **{md.strftime('%d-%m-%Y')}** | Maturity Value: **Rs{ma:,.2f}**")
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    if st.form_submit_button("Open Recurring Deposit", use_container_width=True, type="primary"):
                        rdn = generate_id('RD')
                        an = generate_account_number('RD')
                        c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate) VALUES (?,?,'RD',0.00,?)", (an, cust[0], r))
                        aid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                        c.execute("INSERT INTO recurring_deposits (rd_number,account_id,monthly_amount,interest_rate,start_date,maturity_date,maturity_amount,tenure_months,total_installments,nominee_name,nominee_relation) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (rdn, aid, m, r, sd, md, ma, t, t, nom, nom_rel))
                        c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,'RD Install 1','RD_INSTALLMENT','RECEIPT',?,?)", (generate_id('TXN'), aid, m, m, generate_voucher_number('RECEIPT'), uid))
                        c.execute("UPDATE recurring_deposits SET installments_paid=1 WHERE rd_number=?", (rdn,))
                        c.commit()
                        st.success(f"RD Successfully Opened! RD ID: {rdn}")
                        st.balloons()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with t2:
        st.markdown('<div class="section-card"><h3>Active Recurring Deposits</h3>', unsafe_allow_html=True)
        rds = c.execute("""SELECT rd.id, rd.rd_number, c.first_name||' '||c.last_name, rd.monthly_amount, rd.interest_rate, rd.start_date, rd.maturity_date, rd.maturity_amount, rd.tenure_months, rd.installments_paid, rd.total_installments, rd.nominee_name, rd.nominee_relation, rd.status, c.id as customer_id, a.account_number FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE rd.status='ACTIVE' ORDER BY rd.maturity_date""").fetchall()
        
        if rds:
            df_data = []
            for rd in rds:
                start_date = rd[5]
                maturity_date = rd[6]
                if isinstance(start_date, str):
                    try: start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                    except: start_date = date.today()
                elif isinstance(start_date, datetime): start_date = start_date.date()
                if isinstance(maturity_date, str):
                    try: maturity_date = datetime.strptime(maturity_date, '%Y-%m-%d').date()
                    except: maturity_date = date.today()
                elif isinstance(maturity_date, datetime): maturity_date = maturity_date.date()
                
                progress = (rd[9] / rd[10]) * 100 if rd[10] > 0 else 0
                df_data.append({'RD Ref': rd[1], 'Customer': rd[2], 'Monthly (Rs)': rd[3], 'Rate': f"{rd[4]:.2f}%", 'Start Date': start_date.strftime('%d-%m-%Y') if start_date else 'N/A', 'Maturity Date': maturity_date.strftime('%d-%m-%Y') if maturity_date else 'N/A', 'Maturity Value (Rs)': rd[7], 'Progress': f"{rd[9]}/{rd[10]} ({progress:.0f}%)", 'Status': rd[13]})
            
            if df_data:
                st.dataframe(pd.DataFrame(df_data).style.format({'Monthly (Rs)': 'Rs{:,.2f}', 'Maturity Value (Rs)': 'Rs{:,.2f}'}), use_container_width=True)
                
                st.markdown("---")
                st.warning("Delete Recurring Deposit (This action cannot be undone)")
                del_rd = st.selectbox("Select RD to Delete", [f"{rd[1]} - {rd[2]}" for rd in rds], key="del_rd")
                if del_rd and st.button("Delete RD", use_container_width=True, key="del_rd_btn"):
                    idx = [f"{rd[1]} - {rd[2]}" for rd in rds].index(del_rd)
                    rd_id = rds[idx][0]
                    if st.button("Confirm Delete", use_container_width=True, key="confirm_del_rd"):
                        delete_record('recurring_deposits', 'id', rd_id, 'Recurring Deposit')
                
                st.markdown("---")
                st.subheader("Print RD Receipt")
                
                rd_options = [f"{rd[1]} - {rd[2]} (Rs{rd[7]:,.2f})" for rd in rds]
                selected_rd = st.selectbox("Select RD to print receipt", rd_options, key="rd_print")
                
                if selected_rd and st.button("Print RD Receipt (PDF)", use_container_width=True, type="primary"):
                    rd_idx = rd_options.index(selected_rd)
                    rd = rds[rd_idx]
                    
                    customer_data = {'customer_id': rd[14], 'customer_name': rd[2]}
                    cust_info = c.execute("SELECT address, phone FROM customers WHERE id=?", (rd[14],)).fetchone()
                    if cust_info:
                        customer_data['address'] = cust_info[0] or 'N/A'
                        customer_data['phone'] = cust_info[1] or 'N/A'
                    
                    start_date = rd[5]
                    maturity_date = rd[6]
                    if isinstance(start_date, str):
                        try: start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                        except: start_date = date.today()
                    elif isinstance(start_date, datetime): start_date = start_date.date()
                    if isinstance(maturity_date, str):
                        try: maturity_date = datetime.strptime(maturity_date, '%Y-%m-%d').date()
                        except: maturity_date = date.today()
                    elif isinstance(maturity_date, datetime): maturity_date = maturity_date.date()
                    
                    rd_data = {'rd_number': rd[1], 'account_number': rd[15], 'monthly_amount': rd[3], 'interest_rate': rd[4], 'start_date': start_date.strftime('%d-%m-%Y') if start_date else 'N/A', 'maturity_date': maturity_date.strftime('%d-%m-%Y') if maturity_date else 'N/A', 'maturity_amount': rd[7], 'tenure_months': rd[8], 'installments_paid': rd[9], 'total_installments': rd[10], 'nominee_name': rd[11], 'nominee_relation': rd[12], 'status': rd[13]}
                    
                    pdf = generate_rd_statement_pdf(rd_data, customer_data)
                    
                    if pdf:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                            pdf.output(tmp_file.name)
                            tmp_file.flush()
                            with open(tmp_file.name, 'rb') as f: pdf_bytes = f.read()
                            os.unlink(tmp_file.name)
                        
                        st.download_button(label="Download RD Receipt PDF", data=pdf_bytes, file_name=f"RD_Receipt_{rd[1]}_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True)
                        st.success("RD Receipt generated successfully!")
                    else:
                        st.error("PDF generation library not available.")
        else:
            st.info("No active RDs found in the system.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with t3:
        st.markdown('<div class="section-card"><h3>Process RD Installment</h3>', unsafe_allow_html=True)
        rds = c.execute("""SELECT rd.id, rd.rd_number, c.first_name||' '||c.last_name, rd.monthly_amount, rd.installments_paid, rd.total_installments, a.id FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE rd.status='ACTIVE' AND rd.installments_paid<rd.total_installments""").fetchall()
        
        if rds:
            sel = st.selectbox("Select RD Account", [f"{r[1]} - {r[2]} (Paid: {r[4]}/{r[5]})" for r in rds])
            if sel:
                idx = [f"{r[1]} - {r[2]} (Paid: {r[4]}/{r[5]})" for r in rds].index(sel)
                rd = rds[idx]
                with st.form("pr"):
                    amt = st.number_input("Installment Amount (Rs)", value=float(rd[3]), min_value=float(rd[3]))
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.form_submit_button("Pay Installment", use_container_width=True, type="primary"):
                        c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,?,'RD_INSTALLMENT','RECEIPT',?,?)", (generate_id('TXN'), rd[6], amt, amt, f"RD Installment {rd[4]+1} of {rd[5]}", generate_voucher_number('RECEIPT'), uid))
                        np = rd[4] + 1
                        c.execute("UPDATE recurring_deposits SET installments_paid=? WHERE id=?", (np, rd[0]))
                        if np >= rd[5]: 
                            c.execute("UPDATE recurring_deposits SET status='MATURED' WHERE id=?", (rd[0],))
                        c.commit()
                        st.success(f"Installment Paid Successfully! Progress: {np}/{rd[5]}")
                        st.rerun()
        else:
            st.info("All installments are up to date!")
        st.markdown('</div>', unsafe_allow_html=True)
    c.close()

# ==================== TRANSACTIONS ====================
def transactions():
    c = get_db()
    uid = st.session_state.user['id']
    st.markdown('<div class="section-card"><h3>Global Transactions Ledger</h3>', unsafe_allow_html=True)
    
    d1, d2, d3, d4 = st.columns(4)
    with d1: at = st.selectbox("Account Segment", ["All", "SB", "FD", "RD"])
    with d2: tt = st.selectbox("Flow Type", ["All", "CREDIT", "DEBIT"])
    with d3: fd = st.date_input("Start Date", date.today() - timedelta(days=30), key="tf")
    with d4: td = st.date_input("End Date", date.today(), key="tt")
    
    q = "SELECT t.id,t.transaction_id,c.first_name||' '||c.last_name,a.account_number,a.account_type,t.transaction_type,t.amount,t.balance_after,t.description,t.voucher_number,t.created_at FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE DATE(t.created_at) BETWEEN ? AND ?"
    params = [fd, td]
    
    if st.session_state.user['role'] == 'customer': 
        q += " AND c.user_id=?"
        params.append(uid)
    if at != "All": 
        q += " AND a.account_type=?"
        params.append(at)
    if tt != "All": 
        q += " AND t.transaction_type=?"
        params.append(tt)
        
    q += " ORDER BY t.created_at DESC LIMIT 200"
    txns = c.execute(q, params).fetchall()
    
    if txns:
        df = pd.DataFrame(txns, columns=['ID','Txn ID', 'Customer', 'A/C Number', 'Type', 'Action', 'Amount', 'Closing Balance', 'Description', 'Voucher Ref', 'Date/Time'])
        df['Date/Time'] = pd.to_datetime(df['Date/Time']).dt.strftime('%d-%m-%Y %H:%M')
        st.dataframe(df.style.format({'Amount': 'Rs{:,.2f}', 'Closing Balance': 'Rs{:,.2f}'}), use_container_width=True, height=450)
        
        st.markdown("---")
        st.warning("Delete Transaction (This action cannot be undone)")
        del_txn = st.selectbox("Select Transaction to Delete", [f"{t[1]} - {t[2]} - Rs{t[6]:,.2f}" for t in txns], key="del_txn")
        if del_txn and st.button("Delete Transaction", use_container_width=True, key="del_txn_btn"):
            idx = [f"{t[1]} - {t[2]} - Rs{t[6]:,.2f}" for t in txns].index(del_txn)
            txn_id = txns[idx][0]
            if st.button("Confirm Delete", use_container_width=True, key="confirm_del_txn"):
                delete_record('transactions', 'id', txn_id, 'Transaction')
    else:
        st.info("No transactions found for the given criteria.")
        
    st.markdown('</div>', unsafe_allow_html=True)
    c.close()

# ==================== JOURNAL VOUCHERS ====================
# ==================== JOURNAL VOUCHERS ====================
def journal_vouchers():
    if st.session_state.user['role'] not in ['admin', 'staff']: 
        st.error("Unauthorized"); return
        
    c = get_db()
    uid = st.session_state.user['id']
    
    # ==================== CHART OF ACCOUNTS ====================
    def get_chart_of_accounts():
        """Returns structured chart of accounts with classifications"""
        return {
            'ASSETS': {
                'Current Assets': [
                    'Cash in Hand',
                    'Cash at Bank',
                    'Cheque in Hand',
                    'Accounts Receivable',
                    'Interest Receivable',
                    'Prepaid Expenses',
                    'Short-term Investments'
                ],
                'Fixed Assets': [
                    'Building',
                    'Furniture & Fixtures',
                    'Computer Equipment',
                    'Office Equipment',
                    'Vehicles',
                    'Land',
                    'Leasehold Improvements'
                ]
            },
            'LIABILITIES': {
                'Current Liabilities': [
                    'SB Deposits (Customer Money)',
                    'FD Deposits (Customer Money)',
                    'RD Deposits (Customer Money)',
                    'Accounts Payable',
                    'Interest Payable',
                    'Accrued Expenses',
                    'Unearned Revenue',
                    'TDS Payable',
                    'GST Payable',
                    'Salary Payable'
                ],
                'Long-term Liabilities': [
                    'Long-term Loans',
                    'Bonds Payable',
                    'Deferred Tax Liability'
                ]
            },
            'EQUITY': {
                'Capital': [
                    'Capital / Retained Earnings',
                    'Owner\'s Equity',
                    'Reserves & Surplus'
                ]
            },
            'INCOME': {
                'Operating Income': [
                    'Interest Earned (SB)',
                    'Interest Earned (FD)',
                    'Interest Earned (RD)',
                    'Fees & Charges',
                    'Commission Income',
                    'Service Charges',
                    'Processing Fees',
                    'Late Payment Fees'
                ],
                'Other Income': [
                    'Other Income',
                    'Miscellaneous Income',
                    'Profit on Sale of Assets',
                    'Gain on Exchange'
                ]
            },
            'EXPENSES': {
                'Operating Expenses': [
                    'Salary & Wages',
                    'Rent & Utilities',
                    'Office Expenses',
                    'Postage & Courier',
                    'Telephone & Internet',
                    'Printing & Stationery',
                    'Insurance',
                    'Maintenance & Repairs',
                    'Security Services',
                    'Professional Fees'
                ],
                'Administrative Expenses': [
                    'Administrative Expenses',
                    'Legal & Professional Fees',
                    'Audit Fees',
                    'Director\'s Fees',
                    'Travelling & Conveyance',
                    'Entertainment',
                    'Training & Development',
                    'Membership & Subscriptions'
                ],
                'Financial Expenses': [
                    'Interest Paid (SB)',
                    'Interest Paid (FD)',
                    'Interest Paid (RD)',
                    'Bank Charges',
                    'Transaction Fees',
                    'TDS on Interest'
                ],
                'Other Expenses': [
                    'Other Expenses',
                    'Depreciation',
                    'Bad Debts',
                    'Loss on Sale of Assets',
                    'Donations',
                    'Penalties & Fines'
                ]
            }
        }
    
    def get_account_type(account_head):
        """Get the classification type for a given account head"""
        chart = get_chart_of_accounts()
        for category, sub_categories in chart.items():
            for sub_cat, accounts in sub_categories.items():
                if account_head in accounts:
                    return category[:-1]  # Remove 's' from category name
        return 'Unknown'
    
    def get_account_list():
        """Get all account heads with their full path"""
        chart = get_chart_of_accounts()
        accounts = []
        for category, sub_categories in chart.items():
            for sub_cat, account_list in sub_categories.items():
                for account in account_list:
                    accounts.append({
                        'display': f"{category} → {sub_cat} → {account}",
                        'head': account,
                        'category': category,
                        'sub_category': sub_cat
                    })
        return accounts
    
    def get_accounts_by_category(category):
        """Get all account heads for a specific category"""
        chart = get_chart_of_accounts()
        if category in chart:
            accounts = []
            for sub_cat, account_list in chart[category].items():
                for account in account_list:
                    accounts.append({
                        'display': f"{sub_cat} → {account}",
                        'head': account,
                        'sub_category': sub_cat
                    })
            return accounts
        return []
    
    try:
        custs = c.execute("SELECT id, customer_id, first_name||' '||last_name FROM customers ORDER BY customer_id").fetchall()
    except:
        custs = []
    cust_options = ["None (General Voucher)"] + [f"{c[1]} - {c[2]}" for c in custs]
    
    t1, t2 = st.tabs(["Create JV", "Manage Vouchers"])
    
    with t1:
        st.markdown('<div class="section-card"><h3>Create New Journal Voucher</h3>', unsafe_allow_html=True)
        
        # Show Chart of Accounts for reference
        with st.expander("📚 View Chart of Accounts (Reference)"):
            chart = get_chart_of_accounts()
            for category, sub_categories in chart.items():
                st.markdown(f"**{category}**")
                for sub_cat, accounts in sub_categories.items():
                    st.markdown(f"  - *{sub_cat}*")
                    for account in accounts:
                        st.markdown(f"    - {account}")
                st.markdown("---")
        
        with st.form("jv"):
            vd = st.date_input("Voucher Date", date.today(), key="jvd")
            desc = st.text_area("Voucher Narration / Description")
            
            sel_cust = st.selectbox("Related Customer (Optional)", cust_options, key="jv_cust")
            customer_id = None
            if sel_cust != "None (General Voucher)":
                idx = cust_options.index(sel_cust) - 1
                if idx >= 0:
                    customer_id = custs[idx][0]
            
            n = st.number_input("Number of Ledger Entries", 2, 10, 2)
            entries = []
            td_v = 0
            tc_v = 0
            
            st.markdown("<hr>", unsafe_allow_html=True)
            
            # Display account selection guide
            st.info("""
            **📋 Account Selection Guide:**
            - **ASSETS** (Dr): Cash, Bank, Receivables, Fixed Assets
            - **LIABILITIES** (Cr): Deposits, Payables, Accruals
            - **EQUITY** (Cr): Capital, Reserves
            - **INCOME** (Cr): Interest, Fees, Commission
            - **EXPENSES** (Dr): Salaries, Rent, Utilities, Operational Costs
            """)
            
            for i in range(int(n)):
                st.markdown(f"**Entry line {i+1}**")
                e1, e2, e3, e4 = st.columns([2, 1, 1, 1.5])
                
                with e1:
                    # Get category selection
                    category = st.selectbox(
                        f"Category", 
                        ['Select Category...', 'ASSETS', 'LIABILITIES', 'EQUITY', 'INCOME', 'EXPENSES'],
                        key=f"cat_{i}"
                    )
                    
                    # Get account based on category
                    if category != 'Select Category...':
                        accounts = get_accounts_by_category(category)
                        account_options = ['Select Account...'] + [acc['display'] for acc in accounts]
                        selected_account = st.selectbox(
                            f"Account Head",
                            account_options,
                            key=f"acc_{i}"
                        )
                        
                        if selected_account != 'Select Account...':
                            # Extract the actual account head
                            acc_idx = account_options.index(selected_account) - 1
                            h = accounts[acc_idx]['head']
                            actual_category = category
                            st.caption(f"📌 {actual_category[:-1]} | {accounts[acc_idx]['sub_category']}")
                        else:
                            h = ""
                    else:
                        h = st.text_input(f"Account Head (Manual Entry)", key=f"jh{i}", placeholder="e.g., Custom Account")
                        if h:
                            st.caption("⚠️ Custom account - verify classification")
                
                with e2:
                    d = st.number_input(f"Debit (Dr)", min_value=0.0, step=100.0, key=f"jd{i}")
                with e3:
                    cr = st.number_input(f"Credit (Cr)", min_value=0.0, step=100.0, key=f"jc{i}")
                with e4:
                    if h and h not in ['Select Category...', 'Select Account...']:
                        acct_type = get_account_type(h)
                        if acct_type in ['ASSET', 'EXPENSE']:
                            st.info("💳 Dr")
                        elif acct_type in ['LIABILITY', 'EQUITY', 'INCOME']:
                            st.info("💳 Cr")
                        else:
                            st.warning("⚠️ Unknown")
                
                td_v += d
                tc_v += cr
                
                # Store entry with category info
                if category != 'Select Category...' and selected_account != 'Select Account...':
                    entries.append({
                        'h': h, 
                        'd': d, 
                        'c': cr,
                        'category': category,
                        'sub_category': accounts[acc_idx]['sub_category'] if selected_account != 'Select Account...' else 'Manual'
                    })
                else:
                    entries.append({'h': h, 'd': d, 'c': cr, 'category': 'Manual', 'sub_category': 'Manual'})
            
            st.info(f"**Total Debit:** Rs.{td_v:,.2f} | **Total Credit:** Rs.{tc_v:,.2f}")
            if abs(td_v - tc_v) > 0.01: 
                st.error(f"Mismatch Detected: Difference of Rs.{abs(td_v - tc_v):,.2f}")
                
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Preview entries in a table
            valid_entries = [e for e in entries if (e['d'] > 0 or e['c'] > 0) and e['h'].strip()]
            if valid_entries:
                st.markdown("#### Preview Entries")
                preview_data = []
                for e in valid_entries:
                    acct_type = get_account_type(e['h']) if e['h'] else 'Unknown'
                    preview_data.append({
                        'Account Head': e['h'],
                        'Category': e.get('category', 'Manual'),
                        'Type': acct_type,
                        'Debit (Dr)': e['d'],
                        'Credit (Cr)': e['c']
                    })
                df_preview = pd.DataFrame(preview_data)
                st.dataframe(df_preview.style.format({'Debit (Dr)': 'Rs{:,.2f}', 'Credit (Cr)': 'Rs{:,.2f}'}), use_container_width=True)
            
            submitted = st.form_submit_button("Generate Voucher", use_container_width=True, type="primary")
            
            if submitted:
                if abs(td_v - tc_v) > 0.01: 
                    st.error("Voucher must be perfectly balanced!")
                elif len([e for e in entries if (e['d'] > 0 or e['c'] > 0) and e['h'].strip()]) == 0:
                    st.error("Please add at least one entry with amount > 0 and account head")
                else:
                    vn = generate_voucher_number('JOURNAL')
                    try:
                        c.execute("INSERT INTO journal_vouchers (voucher_number,voucher_date,description,total_amount,created_by,customer_id) VALUES (?,?,?,?,?,?)", (vn, vd, desc, td_v, uid, customer_id))
                    except:
                        c.execute("INSERT INTO journal_vouchers (voucher_number,voucher_date,description,total_amount,created_by) VALUES (?,?,?,?,?)", (vn, vd, desc, td_v, uid))
                    
                    vid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                    
                    entries_saved = 0
                    for e in entries:
                        if (e['d'] > 0 or e['c'] > 0) and e['h'].strip():
                            # Store the category info as part of the description or as a separate field
                            # Since we don't have a category column, we'll store it in description
                            category_info = f"Category: {e.get('category', 'Manual')}"
                            c.execute("INSERT INTO journal_entries (voucher_id,account_head,debit_amount,credit_amount,description) VALUES (?,?,?,?,?)", 
                                     (vid, e['h'].strip(), e['d'], e['c'], category_info))
                            entries_saved += 1
                    
                    c.commit()
                    
                    st.session_state.last_voucher = {
                        'voucher_number': vn,
                        'voucher_date': vd.strftime('%d-%m-%Y'),
                        'description': desc,
                        'status': 'DRAFT',
                        'is_balanced': True,
                        'entries': [{
                            'account_head': e['h'].strip(), 
                            'debit_amount': e['d'], 
                            'credit_amount': e['c'],
                            'category': e.get('category', 'Manual'),
                            'sub_category': e.get('sub_category', 'Manual')
                        } for e in entries if e['h'].strip() and (e['d'] > 0 or e['c'] > 0)]
                    }
                    
                    st.success(f"Voucher Drafted! Reference: {vn} | Entries saved: {entries_saved}")
                    st.balloons()
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if 'last_voucher' in st.session_state:
            vd_data = st.session_state.last_voucher
            st.markdown("---")
            st.markdown(f"### Download Voucher: {vd_data['voucher_number']}")
            
            entries_data = vd_data['entries']
            pdf = generate_journal_voucher_pdf(
                {'voucher_number': vd_data['voucher_number'], 'voucher_date': vd_data['voucher_date'], 'description': vd_data['description'], 'status': vd_data.get('status', 'DRAFT'), 'is_balanced': vd_data['is_balanced']}, 
                entries_data
            )
            
            if pdf:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    pdf.output(tmp_file.name)
                    tmp_file.flush()
                    with open(tmp_file.name, 'rb') as f: pdf_bytes = f.read()
                    os.unlink(tmp_file.name)
                
                st.download_button(label=f"Download PDF - {vd_data['voucher_number']}", data=pdf_bytes, file_name=f"JV_{vd_data['voucher_number']}.pdf", mime="application/pdf", use_container_width=True)
            
            if st.button("Clear & Create New Voucher", key="clear_voucher"):
                del st.session_state.last_voucher
                st.rerun()
        
    with t2:
        st.markdown('<div class="section-card"><h3>Journal Voucher Directory</h3>', unsafe_allow_html=True)
        
        # Filter options
        st.markdown("#### Filter Vouchers")
        f1, f2, f3 = st.columns(3)
        with f1:
            status_filter = st.selectbox("Status", ["All", "DRAFT", "POSTED", "CANCELLED"], key="jv_status_filter")
        with f2:
            date_filter = st.date_input("From Date", date.today() - timedelta(days=30), key="jv_date_from")
        with f3:
            date_to = st.date_input("To Date", date.today(), key="jv_date_to")
        
        try:
            query = """
                SELECT jv.id, jv.voucher_number, jv.voucher_date, jv.description, jv.total_amount, jv.status, 
                       COALESCE((SELECT first_name||' '||last_name FROM customers WHERE id=jv.customer_id), 'General') as customer_name,
                       jv.created_at
                FROM journal_vouchers jv 
                WHERE DATE(jv.voucher_date) BETWEEN ? AND ?
            """
            params = [date_filter, date_to]
            
            if status_filter != "All":
                query += " AND jv.status = ?"
                params.append(status_filter)
            
            query += " ORDER BY jv.created_at DESC"
            
            vouchers = c.execute(query, params).fetchall()
        except:
            vouchers = []
        
        if vouchers:
            # Summary stats
            total_draft = sum(1 for v in vouchers if v[5] == 'DRAFT')
            total_posted = sum(1 for v in vouchers if v[5] == 'POSTED')
            total_amount = sum(v[4] for v in vouchers if v[5] == 'POSTED')
            
            s1, s2, s3 = st.columns(3)
            with s1: st.metric("Total Vouchers", len(vouchers))
            with s2: st.metric("Draft", total_draft)
            with s3: st.metric("Posted (Value)", f"Rs{total_amount:,.2f}")
            
            st.markdown("---")
            
            for v in vouchers:
                status_icon = {'DRAFT': '📝', 'POSTED': '✅', 'CANCELLED': '❌'}
                status_color = {'DRAFT': '#f59e0b', 'POSTED': '#22c55e', 'CANCELLED': '#ef4444'}
                cust_label = f" | Customer: {v[6]}" if v[6] != 'General' else ""
                
                with st.expander(f"{status_icon.get(v[5], '📄')} | {v[1]} | Date: {v[2]} | Rs.{v[4]:,.2f}{cust_label}"):
                    st.markdown(f"**Narration:** {safe_text(v[3])}")
                    if v[6] != 'General':
                        st.markdown(f"**Customer:** {safe_text(v[6])}")
                    
                    entries = c.execute("""SELECT account_head, debit_amount, credit_amount, description FROM journal_entries WHERE voucher_id=? ORDER BY id""", (v[0],)).fetchall()
                    
                    if entries:
                        st.markdown("**Voucher Entries:**")
                        entries_data = []
                        for e in entries:
                            # Extract category from description if available
                            category_info = e[3] if e[3] else 'N/A'
                            entries_data.append({
                                'Account Head': e[0] if e[0] and e[0].strip() else 'N/A',
                                'Category': category_info,
                                'Debit (Dr)': e[1],
                                'Credit (Cr)': e[2]
                            })
                        
                        df_entries = pd.DataFrame(entries_data)
                        st.dataframe(df_entries.style.format({'Debit (Dr)': 'Rs{:,.2f}', 'Credit (Cr)': 'Rs{:,.2f}'}), use_container_width=True)
                        
                        total_dr = sum(e[1] for e in entries)
                        total_cr = sum(e[2] for e in entries)
                        st.markdown(f"**Total Debit:** Rs{total_dr:,.2f} | **Total Credit:** Rs{total_cr:,.2f}")
                        
                        if abs(total_dr - total_cr) < 0.01:
                            st.success("✅ Voucher is balanced")
                        else:
                            st.error(f"❌ Mismatch: Rs{abs(total_dr - total_cr):,.2f}")
                        
                        pdf_entries = []
                        for e in entries:
                            pdf_entries.append({
                                'account_head': e[0] if e[0] and e[0].strip() else 'N/A', 
                                'debit_amount': e[1], 
                                'credit_amount': e[2]
                            })
                        
                        voucher_data = {'voucher_number': v[1], 'voucher_date': v[2], 'description': v[3], 'status': v[5], 'is_balanced': True}
                        if v[6] != 'General':
                            voucher_data['customer_name'] = v[6]
                        
                        pdf = generate_journal_voucher_pdf(voucher_data, pdf_entries)
                        if pdf:
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                                pdf.output(tmp_file.name)
                                tmp_file.flush()
                                with open(tmp_file.name, 'rb') as f: pdf_bytes = f.read()
                                os.unlink(tmp_file.name)
                            
                            st.download_button(label=f"Download PDF - {v[1]}", data=pdf_bytes, file_name=f"JV_{v[1]}.pdf", mime="application/pdf", key=f"dl_{v[1]}")
                    else:
                        st.warning("No entries found for this voucher.")
                        
                    if v[5] == 'DRAFT':
                        st.divider()
                        f1, f2 = st.columns(2)
                        with f1:
                            if st.button("✅ Post Ledger", key=f"po_{v[1]}", use_container_width=True, type="primary"):
                                c.execute("UPDATE journal_vouchers SET status='POSTED',posted_by=?,posted_at=CURRENT_TIMESTAMP WHERE id=?", (uid, v[0]))
                                c.commit()
                                st.success("Voucher Posted successfully!")
                                st.rerun()
                        with f2:
                            if st.button("❌ Cancel Voucher", key=f"ca_{v[1]}", use_container_width=True):
                                c.execute("UPDATE journal_vouchers SET status='CANCELLED' WHERE id=?", (v[0],))
                                c.commit()
                                st.warning("Voucher Cancelled!")
                                st.rerun()
        else: 
            st.info("No journal vouchers available for the selected criteria.")
        st.markdown('</div>', unsafe_allow_html=True)
    c.close()

# ==================== INCOME & EXPENSES ====================
# ==================== INCOME & EXPENSES ====================
# ==================== INCOME & EXPENSES ====================
def income_expenses():
    if st.session_state.user['role'] not in ['admin','staff']: 
        st.error("Unauthorized"); return
    c = get_db()
    uid = st.session_state.user['id']
    t1, t2, t3, t4 = st.tabs(["Record Income", "Record Expense", "View Income", "View Expenses"])
    
    try:
        custs = c.execute("SELECT id, customer_id, first_name||' '||last_name FROM customers ORDER BY customer_id").fetchall()
    except:
        custs = []
    cust_options = ["None (General Entry)"] + [f"{c[1]} - {c[2]}" for c in custs]
    
    with t1:
        st.markdown('<div class="section-card"><h3>Register New Income (Credit Entry)</h3>', unsafe_allow_html=True)
        st.info("Income is recorded as CREDIT entry. The corresponding DEBIT will be to Cash/Bank Account.")
        with st.form("if"):
            d1, d2 = st.columns(2)
            with d1: 
                it = st.selectbox("Income Type", ["Interest Earned", "Fees & Charges", "Commission Income", "Other Income"])
                amt = st.number_input("Amount (Rs)", min_value=1.0, step=100.0)
                sel_cust = st.selectbox("Related Customer (Optional)", cust_options, key="inc_cust")
            with d2: 
                dt = st.date_input("Date", date.today(), key="id")
                mode = st.selectbox("Payment Mode", ["CASH", "BANK", "CHEQUE"], key="inc_mode")
                desc = st.text_area("Description / Narration")
            
            customer_id = None
            if sel_cust != "None (General Entry)":
                idx = cust_options.index(sel_cust) - 1
                if idx >= 0: customer_id = custs[idx][0]
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Show journal entry preview
            st.markdown("**Journal Entry Preview:**")
            st.markdown(f"""
            | Account Head | Debit (Dr) | Credit (Cr) |
            |-------------|------------|-------------|
            | Cash/Bank ({mode}) | Rs{amt:,.2f} | - |
            | {it} | - | Rs{amt:,.2f} |
            """)
            
            if st.form_submit_button("Record Income", use_container_width=True, type="primary"):
                try:
                    c.execute("INSERT INTO income (income_id,income_type,amount,description,date,created_by,customer_id) VALUES (?,?,?,?,?,?,?)", 
                             (generate_id('INC'), it, amt, desc, dt, uid, customer_id))
                except:
                    c.execute("INSERT INTO income (income_id,income_type,amount,description,date,created_by) VALUES (?,?,?,?,?,?)", 
                             (generate_id('INC'), it, amt, desc, dt, uid))
                
                # Create corresponding transaction entry (Debit to Cash/Bank)
                txn_id = generate_id('TXN')
                c.execute("""
                    INSERT INTO transactions (transaction_id, account_id, transaction_type, amount, balance_after, description, reference_type, voucher_type, voucher_number, created_by) 
                    VALUES (?, 0, 'CREDIT', ?, ?, ?, ?, 'RECEIPT', ?, ?)
                """, (txn_id, amt, amt, f"Income: {it} - {desc}", mode, generate_voucher_number('RECEIPT'), uid))
                
                c.commit()
                st.success(f"Successfully recorded Income: Rs{amt:,.2f} | Mode: {mode} | Cash/Bank updated")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with t2:
        st.markdown('<div class="section-card"><h3>Register New Expense (Debit Entry)</h3>', unsafe_allow_html=True)
        st.info("Expense is recorded as DEBIT entry. The corresponding CREDIT will be to Cash/Bank Account.")
        with st.form("ef"):
            d1, d2 = st.columns(2)
            with d1: 
                et = st.selectbox("Expense Type", ["Salary & Wages", "Rent & Utilities", "Operating Expenses", "Administrative Expenses", "Other Expenses"])
                amt = st.number_input("Amount (Rs)", min_value=1.0, step=100.0)
                sel_cust = st.selectbox("Related Customer (Optional)", cust_options, key="exp_cust")
            with d2: 
                dt = st.date_input("Date", date.today(), key="ed")
                mode = st.selectbox("Payment Mode", ["CASH", "BANK", "CHEQUE"], key="exp_mode")
                desc = st.text_area("Description / Narration")
            
            customer_id = None
            if sel_cust != "None (General Entry)":
                idx = cust_options.index(sel_cust) - 1
                if idx >= 0: customer_id = custs[idx][0]
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Show journal entry preview
            st.markdown("**Journal Entry Preview:**")
            st.markdown(f"""
            | Account Head | Debit (Dr) | Credit (Cr) |
            |-------------|------------|-------------|
            | {et} | Rs{amt:,.2f} | - |
            | Cash/Bank ({mode}) | - | Rs{amt:,.2f} |
            """)
            
            if st.form_submit_button("Record Expense", use_container_width=True, type="primary"):
                try:
                    c.execute("INSERT INTO expenses (expense_id,expense_type,amount,description,date,created_by,customer_id) VALUES (?,?,?,?,?,?,?)", 
                             (generate_id('EXP'), et, amt, desc, dt, uid, customer_id))
                except:
                    c.execute("INSERT INTO expenses (expense_id,expense_type,amount,description,date,created_by) VALUES (?,?,?,?,?,?)", 
                             (generate_id('EXP'), et, amt, desc, dt, uid))
                
                # Create corresponding transaction entry (Credit to Cash/Bank)
                txn_id = generate_id('TXN')
                c.execute("""
                    INSERT INTO transactions (transaction_id, account_id, transaction_type, amount, balance_after, description, reference_type, voucher_type, voucher_number, created_by) 
                    VALUES (?, 0, 'DEBIT', ?, ?, ?, ?, 'PAYMENT', ?, ?)
                """, (txn_id, amt, -amt, f"Expense: {et} - {desc}", mode, generate_voucher_number('PAYMENT'), uid))
                
                c.commit()
                st.success(f"Successfully recorded Expense: Rs{amt:,.2f} | Mode: {mode} | Cash/Bank updated")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with t3:
        st.markdown('<div class="section-card"><h3>Income Ledger (Credit Entries)</h3>', unsafe_allow_html=True)
        
        # Summary cards
        total_income = c.execute("SELECT COALESCE(SUM(amount),0) FROM income").fetchone()[0]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Income (Cr)", f"Rs{total_income:,.2f}")
        with col2:
            interest_income = c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Interest Earned'").fetchone()[0]
            st.metric("Interest Income", f"Rs{interest_income:,.2f}")
        with col3:
            other_income = c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type!='Interest Earned'").fetchone()[0]
            st.metric("Other Income", f"Rs{other_income:,.2f}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Income by type
        income_by_type = c.execute("""
            SELECT income_type, COALESCE(SUM(amount),0) 
            FROM income 
            GROUP BY income_type 
            ORDER BY SUM(amount) DESC
        """).fetchall()
        
        if income_by_type:
            st.markdown("#### Income by Category")
            df_type = pd.DataFrame(income_by_type, columns=['Income Type', 'Amount (Cr)'])
            st.dataframe(df_type.style.format({'Amount (Cr)': 'Rs{:,.2f}'}), use_container_width=True)
        
        st.markdown("---")
        
        # Detailed income list
        try:
            inc_data = c.execute("""
                SELECT id, income_id, income_type, amount, description, date, 
                       COALESCE((SELECT first_name||' '||last_name FROM customers WHERE id=income.customer_id), 'General') as customer_name 
                FROM income ORDER BY date DESC LIMIT 100
            """).fetchall()
        except:
            inc_data = c.execute("""
                SELECT id, income_id, income_type, amount, description, date, 'General' as customer_name 
                FROM income ORDER BY date DESC LIMIT 100
            """).fetchall()
            
        if inc_data:
            st.markdown("#### Detailed Income Transactions")
            df = pd.DataFrame(inc_data, columns=['ID','Income ID', 'Type', 'Amount (Cr)', 'Description', 'Date', 'Customer'])
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%d-%m-%Y')
            st.dataframe(df.style.format({'Amount (Cr)': 'Rs{:,.2f}'}), use_container_width=True, height=400)
            
            # Delete option
            st.markdown("---")
            with st.expander("Delete Income Record"):
                st.warning("Delete Income Record (This action cannot be undone)")
                del_inc = st.selectbox("Select Income to Delete", [f"{i[1]} - {i[2]} - Rs{i[3]:,.2f}" for i in inc_data], key="del_inc")
                if del_inc and st.button("Delete Income", use_container_width=True, key="del_inc_btn"):
                    idx = [f"{i[1]} - {i[2]} - Rs{i[3]:,.2f}" for i in inc_data].index(del_inc)
                    inc_id = inc_data[idx][0]
                    if st.button("Confirm Delete", use_container_width=True, key="confirm_del_inc"):
                        delete_record('income', 'id', inc_id, 'Income Record')
        else:
            st.info("No income records found.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with t4:
        st.markdown('<div class="section-card"><h3>Expense Ledger (Debit Entries)</h3>', unsafe_allow_html=True)
        
        # Summary cards
        total_expenses = c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Expenses (Dr)", f"Rs{total_expenses:,.2f}")
        with col2:
            salary_exp = c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Salary & Wages'").fetchone()[0]
            st.metric("Salary & Wages", f"Rs{salary_exp:,.2f}")
        with col3:
            other_exp = c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type!='Salary & Wages'").fetchone()[0]
            st.metric("Other Expenses", f"Rs{other_exp:,.2f}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Expenses by type
        expense_by_type = c.execute("""
            SELECT expense_type, COALESCE(SUM(amount),0) 
            FROM expenses 
            GROUP BY expense_type 
            ORDER BY SUM(amount) DESC
        """).fetchall()
        
        if expense_by_type:
            st.markdown("#### Expenses by Category")
            df_type = pd.DataFrame(expense_by_type, columns=['Expense Type', 'Amount (Dr)'])
            st.dataframe(df_type.style.format({'Amount (Dr)': 'Rs{:,.2f}'}), use_container_width=True)
        
        st.markdown("---")
        
        # Detailed expense list
        try:
            exp_data = c.execute("""
                SELECT id, expense_id, expense_type, amount, description, date, 
                       COALESCE((SELECT first_name||' '||last_name FROM customers WHERE id=expenses.customer_id), 'General') as customer_name 
                FROM expenses ORDER BY date DESC LIMIT 100
            """).fetchall()
        except:
            exp_data = c.execute("""
                SELECT id, expense_id, expense_type, amount, description, date, 'General' as customer_name 
                FROM expenses ORDER BY date DESC LIMIT 100
            """).fetchall()
            
        if exp_data:
            st.markdown("#### Detailed Expense Transactions")
            df = pd.DataFrame(exp_data, columns=['ID','Expense ID', 'Type', 'Amount (Dr)', 'Description', 'Date', 'Customer'])
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%d-%m-%Y')
            st.dataframe(df.style.format({'Amount (Dr)': 'Rs{:,.2f}'}), use_container_width=True, height=400)
            
            # Delete option
            st.markdown("---")
            with st.expander("Delete Expense Record"):
                st.warning("Delete Expense Record (This action cannot be undone)")
                del_exp = st.selectbox("Select Expense to Delete", [f"{e[1]} - {e[2]} - Rs{e[3]:,.2f}" for e in exp_data], key="del_exp")
                if del_exp and st.button("Delete Expense", use_container_width=True, key="del_exp_btn"):
                    idx = [f"{e[1]} - {e[2]} - Rs{e[3]:,.2f}" for e in exp_data].index(del_exp)
                    exp_id = exp_data[idx][0]
                    if st.button("Confirm Delete", use_container_width=True, key="confirm_del_exp"):
                        delete_record('expenses', 'id', exp_id, 'Expense Record')
        else:
            st.info("No expense records found.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Income vs Expense Summary
    total_inc = c.execute("SELECT COALESCE(SUM(amount),0) FROM income").fetchone()[0]
    total_exp = c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
    net = total_inc - total_exp
    
    if total_inc > 0 or total_exp > 0:
        st.markdown("---")
        st.markdown("### Income vs Expense Summary")
        
        s1, s2, s3 = st.columns(3)
        with s1:
            st.metric("Total Income (Cr)", f"Rs{total_inc:,.2f}")
        with s2:
            st.metric("Total Expenses (Dr)", f"Rs{total_exp:,.2f}")
        with s3:
            if net >= 0:
                st.metric("Net Surplus", f"Rs{net:,.2f}", delta="Profit")
            else:
                st.metric("Net Deficit", f"Rs{abs(net):,.2f}", delta="Loss", delta_color="inverse")
    
    c.close()

# ==================== INTEREST CALCULATION ====================
def interest_calc():
    if st.session_state.user['role'] not in ['admin', 'staff']: 
        st.error("Unauthorized"); return
        
    c = get_db()
    uid = st.session_state.user['id']
    t1, t2, t3, t4 = st.tabs(["Calculate & Post (All)", "Calculate by Customer", "History", "Impact Check"])
    
    with t1:
        st.markdown('<div class="section-card"><h3>Calculate Interest - All SB Accounts</h3>', unsafe_allow_html=True)
        d1, d2 = st.columns(2)
        with d1: cfd = st.date_input("From Date", date.today().replace(day=1), key="if")
        with d2: ctd = st.date_input("To Date", date.today(), key="it")
        
        if cfd > ctd:
            st.error("Invalid date range selected.")
        else:
            st.info(f"Targeting: {cfd.strftime('%d-%m-%Y')} -> {ctd.strftime('%d-%m-%Y')} ({(ctd-cfd).days+1} days)")
            
        accs = c.execute("SELECT a.id,a.account_number,c.first_name||' '||c.last_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        
        if accs:
            st.markdown("<br>", unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            with b1:
                if st.button("Calculate & Post Interest", use_container_width=True, type="primary", key="cp"):
                    s, r = calculate_and_post_sb_interest(uid, cfd, ctd)
                    if s == "SUCCESS" and len(r) > 0:
                        st.success(f"Successfully posted Rs{sum(x['interest'] for x in r):,.2f} in interest!")
                        st.balloons()
                    else:
                        st.info(s if s != "SUCCESS" else "No interest to post for this period.")
            with b2:
                if st.button("Preview Calculations Only", use_container_width=True, key="pv"):
                    pv = []
                    for a in accs:
                        mb = get_minimum_balance(c, a[0], cfd, ctd)
                        if mb <= 0: mb = a[3]
                        days = (ctd-cfd).days+1
                        if days > 0:
                            pv.append({'Account': a[1], 'Min Balance': mb, 'Interest Output': calculate_sb_interest(mb, a[4] or 3.5, days), 'New Total Amount': a[3]+a[5]+calculate_sb_interest(mb, a[4] or 3.5, days)})
                    if pv:
                        st.dataframe(pd.DataFrame(pv).style.format({'Min Balance': 'Rs{:,.2f}', 'Interest Output': 'Rs{:,.2f}', 'New Total Amount': 'Rs{:,.2f}'}), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with t2:
        st.markdown('<div class="section-card"><h3>Calculate Interest - By Customer</h3>', unsafe_allow_html=True)
        custs = c.execute("SELECT DISTINCT c.id, c.customer_id, c.first_name||' '||c.last_name FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        
        if custs:
            sel_cust = st.selectbox("Select Customer", [f"{c[1]} - {c[2]}" for c in custs], key="ic_cust")
            if sel_cust:
                idx = [f"{c[1]} - {c[2]}" for c in custs].index(sel_cust)
                selected_customer_id = custs[idx][0]
                selected_customer_name = custs[idx][2]
                
                d1, d2 = st.columns(2)
                with d1: cfd = st.date_input("From Date", date.today().replace(day=1), key="icf_cust")
                with d2: ctd = st.date_input("To Date", date.today(), key="ict_cust")
                
                accs = c.execute("SELECT a.id,a.account_number,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a WHERE a.customer_id=? AND a.account_type='SB' AND a.status='ACTIVE'", (selected_customer_id,)).fetchall()
                
                if accs:
                    st.markdown(f"**Customer:** {selected_customer_name} | **Accounts:** {len(accs)}")
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("Calculate & Post Interest", use_container_width=True, type="primary", key="cp_cust"):
                            s, r = calculate_and_post_sb_interest(uid, cfd, ctd, selected_customer_id)
                            if s == "SUCCESS" and len(r) > 0:
                                st.success(f"Posted Rs{sum(x['interest'] for x in r):,.2f} interest for {selected_customer_name}")
                                st.balloons()
                            else:
                                st.info(s if s != "SUCCESS" else f"No interest to post for {selected_customer_name}")
                    with b2:
                        if st.button("Preview Calculations Only", use_container_width=True, key="pv_cust"):
                            pv = []
                            for a in accs:
                                mb = get_minimum_balance(c, a[0], cfd, ctd)
                                if mb <= 0: mb = a[2]
                                days = (ctd-cfd).days+1
                                if days > 0:
                                    pv.append({'Account': a[1], 'Min Balance': mb, 'Interest Output': calculate_sb_interest(mb, a[3] or 3.5, days), 'New Total Amount': a[2]+a[4]+calculate_sb_interest(mb, a[3] or 3.5, days)})
                            if pv:
                                st.dataframe(pd.DataFrame(pv).style.format({'Min Balance': 'Rs{:,.2f}', 'Interest Output': 'Rs{:,.2f}', 'New Total Amount': 'Rs{:,.2f}'}), use_container_width=True)
                else:
                    st.info("No active SB accounts found for this customer.")
        else:
            st.info("No customers with active SB accounts found.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with t3:
        st.markdown('<div class="section-card"><h3>Interest Run History</h3>', unsafe_allow_html=True)
        h = c.execute("SELECT ic.id,ic.calculation_date,a.account_number,c.first_name||' '||c.last_name,ic.principal_amount,ic.interest_rate,ic.interest_earned,ic.days_calculated FROM interest_calculations ic JOIN accounts a ON ic.account_id=a.id JOIN customers c ON a.customer_id=c.id ORDER BY ic.calculation_date DESC LIMIT 50").fetchall()
        if h:
            df = pd.DataFrame(h, columns=['ID','Run Date', 'Account', 'Customer', 'Principal Computed', 'Rate', 'Interest Output', 'Days'])
            df['Run Date'] = pd.to_datetime(df['Run Date']).dt.strftime('%d-%m-%Y')
            st.dataframe(df.style.format({'Principal Computed': 'Rs{:,.2f}', 'Interest Output': 'Rs{:,.2f}'}), use_container_width=True, height=350)
        else:
            st.info("No interest calculation history available.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with t4:
        st.markdown('<div class="section-card"><h3>Journal Voucher Impact</h3>', unsafe_allow_html=True)
        jvs = c.execute("SELECT jv.voucher_number,jv.voucher_date,jv.description,jv.total_amount,je.account_head,je.debit_amount,je.credit_amount FROM journal_vouchers jv JOIN journal_entries je ON jv.id=je.voucher_id WHERE (je.account_head='Interest Paid on SB' OR je.account_head LIKE '%SB Account%') AND jv.status='POSTED' ORDER BY jv.voucher_date DESC LIMIT 50").fetchall()
        if jvs:
            jd = {}
            for j in jvs:
                if j[0] not in jd: 
                    jd[j[0]] = {'date': j[1], 'desc': j[2], 'amt': j[3], 'entries': []}
                jd[j[0]]['entries'].append({'head': j[4], 'debit': j[5], 'credit': j[6]})
            for vn, d in jd.items():
                with st.expander(f"JV {vn} | Date: {d['date']} | Total: Rs{d['amt']:,.2f}"):
                    for e in d['entries']: 
                        st.markdown(f"**{e['head']}**: Dr Rs{e['debit']:,.2f} | Cr Rs{e['credit']:,.2f}")
            st.success(f"Total TB Impact: Rs{sum(d['amt'] for d in jd.values()):,.2f}")
        else:
            st.info("No mapped Journal Vouchers found.")
        st.markdown('</div>', unsafe_allow_html=True)
    c.close()

# ==================== TRIAL BALANCE ====================
# ==================== TRIAL BALANCE ====================
def trial_balance():
    if st.session_state.user['role'] not in ['admin', 'staff']: 
        st.error("Unauthorized"); return
    c = get_db()
    
    st.markdown('<div class="section-card"><h3>Corporate Trial Balance</h3>', unsafe_allow_html=True)
    if st.button("Generate Ledger Balances", use_container_width=True, type="primary", key="tb"):
        td = []
        
        # Cash in Hand - from CASH transactions
        cash_in_hand = c.execute("SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END),0) FROM transactions WHERE reference_type='CASH'").fetchone()[0]
        if abs(cash_in_hand) > 0: 
            td.append({'head': 'Cash in Hand', 'cat': 'Asset', 'dr': max(cash_in_hand, 0), 'cr': max(-cash_in_hand, 0)})
        
        # Cash in Bank - from BANK transactions
        cash_in_bank = c.execute("SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END),0) FROM transactions WHERE reference_type='BANK'").fetchone()[0]
        if abs(cash_in_bank) > 0: 
            td.append({'head': 'Cash in Bank', 'cat': 'Asset', 'dr': max(cash_in_bank, 0), 'cr': max(-cash_in_bank, 0)})
        
        # Cash from CHEQUE transactions
        cash_cheque = c.execute("SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END),0) FROM transactions WHERE reference_type='CHEQUE'").fetchone()[0]
        if abs(cash_cheque) > 0: 
            td.append({'head': 'Cash (Cheque)', 'cat': 'Asset', 'dr': max(cash_cheque, 0), 'cr': max(-cash_cheque, 0)})
        
        # SB Deposits - Liability
        sb = c.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb > 0: 
            td.append({'head': 'SB Deposits', 'cat': 'Liability', 'dr': 0, 'cr': sb})
        
        # FD Deposits - Liability
        fd = c.execute("SELECT COALESCE(SUM(principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        if fd > 0: 
            td.append({'head': 'FD Deposits', 'cat': 'Liability', 'dr': 0, 'cr': fd})
        
        # RD Deposits - Liability
        rd = c.execute("SELECT COALESCE(SUM(monthly_amount*installments_paid),0) FROM recurring_deposits WHERE status='ACTIVE'").fetchone()[0]
        if rd > 0: 
            td.append({'head': 'RD Deposits', 'cat': 'Liability', 'dr': 0, 'cr': rd})
        
        # Interest Payable on SB
        sb_int = c.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb_int > 0: 
            td.append({'head': 'SB Interest Payable', 'cat': 'Liability', 'dr': 0, 'cr': sb_int})
        
        # FD Interest Payable
        fd_int = c.execute("SELECT COALESCE(SUM(maturity_amount-principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        if fd_int > 0: 
            td.append({'head': 'FD Interest Payable', 'cat': 'Liability', 'dr': 0, 'cr': fd_int})
        
        # RD Interest Payable
        rd_int = c.execute("SELECT COALESCE(SUM(maturity_amount-(monthly_amount*installments_paid)),0) FROM recurring_deposits WHERE status='ACTIVE'").fetchone()[0]
        if rd_int > 0: 
            td.append({'head': 'RD Interest Payable', 'cat': 'Liability', 'dr': 0, 'cr': rd_int})
        
        # JV entries related to SB Accounts (liabilities)
        jvl = c.execute("""
            SELECT je.account_head, SUM(je.credit_amount), SUM(je.debit_amount) 
            FROM journal_entries je 
            JOIN journal_vouchers jv ON je.voucher_id=jv.id 
            WHERE jv.status='POSTED' 
            AND (je.account_head LIKE '%SB Account%' OR je.account_head LIKE '%Payable%') 
            GROUP BY je.account_head
        """).fetchall()
        for e in jvl:
            if e[1] > e[2]: 
                td.append({'head': e[0], 'cat': 'Liability', 'dr': e[2] or 0, 'cr': e[1] or 0})
        
        # Income entries
        for it in ['Interest Earned', 'Fees & Charges', 'Commission Income', 'Other Income']:
            amt = c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type=?", (it,)).fetchone()[0]
            if amt > 0: 
                td.append({'head': it, 'cat': 'Income', 'dr': 0, 'cr': amt})
        
        # All other JV entries (non-SB account)
        jve = c.execute("""
            SELECT je.account_head, SUM(je.debit_amount), SUM(je.credit_amount) 
            FROM journal_entries je 
            JOIN journal_vouchers jv ON je.voucher_id=jv.id 
            WHERE jv.status='POSTED' 
            AND je.account_head NOT LIKE '%SB Account%' 
            AND je.account_head NOT LIKE '%Payable%'
            GROUP BY je.account_head
        """).fetchall()
        for e in jve:
            if e[1] > 0: 
                td.append({'head': e[0], 'cat': 'Expense' if e[1] > e[2] else 'Income', 'dr': e[1], 'cr': 0})
            if e[2] > 0: 
                td.append({'head': e[0], 'cat': 'Income' if e[2] > e[1] else 'Liability', 'dr': 0, 'cr': e[2]})
        
        # Expense entries
        for et in ['Salary & Wages', 'Rent & Utilities', 'Operating Expenses', 'Administrative Expenses', 'Other Expenses']:
            amt = c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type=?", (et,)).fetchone()[0]
            if amt > 0: 
                td.append({'head': et, 'cat': 'Expense', 'dr': amt, 'cr': 0})
        
        # Calculate totals
        tdr = sum(i['dr'] for i in td)
        tcr = sum(i['cr'] for i in td)
        diff = tcr - tdr
        
        # Add Capital/Retained Earnings as balancing figure
        if abs(diff) > 0.01: 
            td.append({'head': 'Capital / Retained Earnings', 'cat': 'Capital', 'dr': max(-diff, 0), 'cr': max(diff, 0)})
        
        # Recalculate totals after adding capital
        tdr = sum(i['dr'] for i in td)
        tcr = sum(i['cr'] for i in td)
        
        if td:
            df = pd.DataFrame(td)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Summary metrics
            m1, m2, m3, m4 = st.columns(4)
            with m1: 
                st.metric("Total Assets", f"Rs{sum(i['dr'] for i in td if i['cat']=='Asset'):,.2f}")
            with m2: 
                st.metric("Total Liabilities", f"Rs{sum(i['cr'] for i in td if i['cat']=='Liability'):,.2f}")
            with m3: 
                st.metric("Gross Income", f"Rs{sum(i['cr'] for i in td if i['cat']=='Income'):,.2f}")
            with m4: 
                st.metric("Gross Expenses", f"Rs{sum(i['dr'] for i in td if i['cat']=='Expense'):,.2f}")
            
            st.divider()
            
            # Display by category
            for cat in ['Asset', 'Liability', 'Income', 'Expense', 'Capital']:
                cd = [i for i in td if i['cat'] == cat]
                if cd:
                    st.markdown(f"#### {cat}s Ledger")
                    cat_df = pd.DataFrame(cd)[['head', 'dr', 'cr']]
                    cat_df = cat_df.rename(columns={'head': 'Account Head', 'dr': 'Debit (Dr)', 'cr': 'Credit (Cr)'})
                    st.dataframe(
                        cat_df.style.format({'Debit (Dr)': 'Rs{:,.2f}', 'Credit (Cr)': 'Rs{:,.2f}'}), 
                        use_container_width=True, 
                        height=min(250, len(cd)*45+40)
                    )
                    
            st.divider()
            
            # Final totals
            n1, n2, n3 = st.columns(3)
            with n1: 
                st.metric("Gross Debit Total", f"Rs{tdr:,.2f}")
            with n2: 
                st.metric("Gross Credit Total", f"Rs{tcr:,.2f}")
            with n3:
                if abs(tdr - tcr) < 0.01:
                    st.success("ACCOUNTS FULLY BALANCED")
                else:
                    st.error(f"Mismatch: Rs{abs(tdr-tcr):,.2f}")
            
            # Show transaction mode breakdown
            st.markdown("---")
            st.markdown("#### Transaction Mode Summary")
            tm1, tm2, tm3 = st.columns(3)
            with tm1:
                st.metric("CASH Transactions", f"Rs{cash_in_hand:,.2f}")
            with tm2:
                st.metric("BANK Transactions", f"Rs{cash_in_bank:,.2f}")
            with tm3:
                st.metric("CHEQUE Transactions", f"Rs{cash_cheque:,.2f}")
            
            # Download options
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.download_button("Download as CSV", df.to_csv(index=False), "trial_balance.csv", "text/csv", key="dtb", use_container_width=True)
            
            with col2:
                if st.button("Print Trial Balance (PDF)", use_container_width=True, type="primary"):
                    tb_data = {
                        'entries': [{'account_head': row['head'], 'debit': row['dr'], 'credit': row['cr']} for _, row in df.iterrows()],
                        'as_on': date.today().strftime('%d-%m-%Y')
                    }
                    pdf = generate_trial_balance_pdf(tb_data)
                    
                    if pdf:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                            pdf.output(tmp_file.name)
                            tmp_file.flush()
                            with open(tmp_file.name, 'rb') as f: 
                                pdf_bytes = f.read()
                            os.unlink(tmp_file.name)
                        
                        st.download_button(
                            label="Download Trial Balance PDF",
                            data=pdf_bytes,
                            file_name=f"Trial_Balance_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                        st.success("Trial Balance PDF generated successfully!")
        else:
            st.info("No ledger entries found to construct Trial Balance.")
            
    st.markdown('</div>', unsafe_allow_html=True)
    c.close()


# ==================== BALANCE SHEET ====================
def balance_sheet():
    if st.session_state.user['role'] not in ['admin', 'staff']: 
        st.error("Unauthorized"); return
        
    c = get_db()
    st.markdown('<div class="section-card"><h3>Corporate Balance Sheet</h3>', unsafe_allow_html=True)
    
    if st.button("Generate Balance Sheet", use_container_width=True, type="primary", key="bs"):
        # ============ ASSETS (What bank owns/receivables) ============
        
        # Cash in Hand - from CASH transactions
        cash_in_hand = c.execute("""
            SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END),0) 
            FROM transactions WHERE reference_type='CASH'
        """).fetchone()[0]
        
        # Cash in Bank - from BANK transactions (money received via bank)
        cash_in_bank = c.execute("""
            SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END),0) 
            FROM transactions WHERE reference_type='BANK'
        """).fetchone()[0]
        
        # Cash from CHEQUE transactions
        cash_cheque = c.execute("""
            SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END),0) 
            FROM transactions WHERE reference_type='CHEQUE'
        """).fetchone()[0]
        
        # Income received is an asset
        total_income = c.execute("SELECT COALESCE(SUM(amount),0) FROM income").fetchone()[0]
        
        # JV debit entries represent assets
        jv_debit_breakdown = c.execute("""
            SELECT je.account_head, SUM(je.debit_amount) as total 
            FROM journal_entries je 
            JOIN journal_vouchers jv ON je.voucher_id=jv.id 
            WHERE jv.status='POSTED' AND je.debit_amount > 0 
            GROUP BY je.account_head
        """).fetchall()
        jv_assets = sum(e[1] for e in jv_debit_breakdown) if jv_debit_breakdown else 0
        
        total_assets = cash_in_hand + cash_in_bank + cash_cheque + jv_assets + total_income
        
        # ============ LIABILITIES (What bank owes to others) ============
        
        # Customer deposits are liabilities
        sb_bal = c.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        fd_bal = c.execute("SELECT COALESCE(SUM(principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        rd_bal = c.execute("SELECT COALESCE(SUM(monthly_amount*installments_paid),0) FROM recurring_deposits WHERE status='ACTIVE'").fetchone()[0]
        
        # Interest payable
        sb_int = c.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        fd_int = c.execute("SELECT COALESCE(SUM(maturity_amount-principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        rd_int = c.execute("SELECT COALESCE(SUM(maturity_amount-(monthly_amount*installments_paid)),0) FROM recurring_deposits WHERE status='ACTIVE'").fetchone()[0]
        
        # Expenses are liabilities
        total_expenses = c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
        
        # JV credit entries represent liabilities/equity
        jv_credit_breakdown = c.execute("""
            SELECT je.account_head, SUM(je.credit_amount) as total 
            FROM journal_entries je 
            JOIN journal_vouchers jv ON je.voucher_id=jv.id 
            WHERE jv.status='POSTED' AND je.credit_amount > 0 
            GROUP BY je.account_head
        """).fetchall()
        jv_liabilities = sum(e[1] for e in jv_credit_breakdown) if jv_credit_breakdown else 0
        
        total_liabilities = sb_bal + fd_bal + rd_bal + sb_int + fd_int + rd_int + total_expenses + jv_liabilities
        
        # Capital = Assets - Liabilities
        capital = total_assets - total_liabilities
        
        # ============ PREPARE DISPLAY DATA ============
        assets_data = []
        if cash_in_hand > 0:
            assets_data.append({'name': 'Cash in Hand', 'amount': cash_in_hand})
        if cash_in_bank > 0:
            assets_data.append({'name': 'Cash in Bank', 'amount': cash_in_bank})
        if cash_cheque > 0:
            assets_data.append({'name': 'Cash (Cheque)', 'amount': cash_cheque})
        for jv_entry in jv_debit_breakdown:
            if jv_entry[1] > 0:
                assets_data.append({'name': f'JV: {jv_entry[0]}', 'amount': jv_entry[1]})
        if total_income > 0:
            assets_data.append({'name': 'Total Income Received', 'amount': total_income})
        
        liabilities_data = []
        if sb_bal > 0:
            liabilities_data.append({'name': 'SB Deposits (Customer Money)', 'amount': sb_bal})
        if fd_bal > 0:
            liabilities_data.append({'name': 'FD Deposits (Customer Money)', 'amount': fd_bal})
        if rd_bal > 0:
            liabilities_data.append({'name': 'RD Deposits (Customer Money)', 'amount': rd_bal})
        if sb_int > 0:
            liabilities_data.append({'name': 'SB Interest Payable', 'amount': sb_int})
        if fd_int > 0:
            liabilities_data.append({'name': 'FD Interest Payable', 'amount': fd_int})
        if rd_int > 0:
            liabilities_data.append({'name': 'RD Interest Payable', 'amount': rd_int})
        if total_expenses > 0:
            liabilities_data.append({'name': 'Total Expenses', 'amount': total_expenses})
        for jv_entry in jv_credit_breakdown:
            if jv_entry[1] > 0:
                liabilities_data.append({'name': f'JV: {jv_entry[0]}', 'amount': jv_entry[1]})
        
        # ============ DISPLAY ============
        st.markdown("<br>", unsafe_allow_html=True)
        p1, p2 = st.columns(2)
        
        with p1:
            st.markdown(f'''
            <div class="dash-card" style="text-align: left;">
                <h3 style="color:#0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom:10px;">ASSETS (What Bank Owns)</h3>
            ''', unsafe_allow_html=True)
            for item in assets_data:
                st.markdown(f'<p style="font-size: 1rem; color:#334155; display:flex; justify-content:space-between;"><span>{item["name"]}:</span> <b>Rs{item["amount"]:,.2f}</b></p>', unsafe_allow_html=True)
            st.markdown(f'''
                <hr style="border-color:#e2e8f0;">
                <p style="font-size: 1.2rem; color:#0f172a; display:flex; justify-content:space-between;"><b>Total Assets:</b> <b>Rs{total_assets:,.2f}</b></p>
            </div>
            ''', unsafe_allow_html=True)
            
        with p2:
            st.markdown(f'''
            <div class="dash-card" style="text-align: left;">
                <h3 style="color:#0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom:10px;">LIABILITIES (What Bank Owes)</h3>
            ''', unsafe_allow_html=True)
            for item in liabilities_data:
                st.markdown(f'<p style="font-size: 1rem; color:#334155; display:flex; justify-content:space-between;"><span>{item["name"]}:</span> <b>Rs{item["amount"]:,.2f}</b></p>', unsafe_allow_html=True)
            st.markdown(f'''
                <hr style="border-color:#e2e8f0;">
                <p style="font-size: 1.2rem; color:#0f172a; display:flex; justify-content:space-between;"><b>Total Liabilities:</b> <b>Rs{total_liabilities:,.2f}</b></p>
            </div>
            ''', unsafe_allow_html=True)
            
        st.markdown(f'''
        <div class="dash-card" style="background: linear-gradient(135deg, #0f2027, #2c5364); color: white;">
            <h3 style="color:white; margin:0;">CAPITAL / EQUITY (Balancing Figure)</h3>
            <h2 style="color:white; margin: 10px 0;">Rs{capital:,.2f}</h2>
        </div>
        ''', unsafe_allow_html=True)
        
        # Check if balanced
        balance_difference = total_assets - (total_liabilities + capital)
        if abs(balance_difference) < 0.01:
            st.success("Balance Sheet is perfectly aligned.")
        else:
            st.warning(f"Balance Sheet difference: Rs{abs(balance_difference):,.2f}")
        
        # Transaction mode breakdown
        st.markdown("---")
        st.markdown("#### Transaction Mode Breakdown")
        tx_col1, tx_col2, tx_col3 = st.columns(3)
        with tx_col1:
            st.metric("CASH Transactions", f"Rs{cash_in_hand:,.2f}")
        with tx_col2:
            st.metric("BANK Transactions", f"Rs{cash_in_bank:,.2f}")
        with tx_col3:
            st.metric("CHEQUE Transactions", f"Rs{cash_cheque:,.2f}")
        
        # Summary explanation
        total_deposits = sb_bal + fd_bal + rd_bal
        total_cash = cash_in_hand + cash_in_bank + cash_cheque
        st.markdown("---")
        st.info(f"""
        **Balance Sheet Explanation:**
        - **Total Cash Available = Rs{total_cash:,.2f}** (Cash in Hand + Cash in Bank + Cheques)
        - **Customer Deposits = Rs{total_deposits:,.2f}** (money bank owes to customers)
        - When customers deposit money, both Assets (Cash) AND Liabilities (Deposits) increase equally
        - **Capital = Rs{capital:,.2f}** represents owner's equity (Assets - Liabilities)
        """)
        
        # Show JV breakdown for verification
        if jv_debit_breakdown or jv_credit_breakdown:
            st.markdown("---")
            st.markdown("#### Journal Voucher Impact")
            jv_col1, jv_col2 = st.columns(2)
            with jv_col1:
                st.markdown("**JV Debit Entries (Assets):**")
                for entry in jv_debit_breakdown:
                    st.markdown(f"- {entry[0]}: Rs{entry[1]:,.2f}")
            with jv_col2:
                st.markdown("**JV Credit Entries (Liabilities/Equity):**")
                for entry in jv_credit_breakdown:
                    st.markdown(f"- {entry[0]}: Rs{entry[1]:,.2f}")
        
        st.markdown("---")
        if st.button("Print Balance Sheet (PDF)", use_container_width=True, type="primary"):
            pdf_data = {
                'assets': assets_data, 
                'liabilities': liabilities_data, 
                'capital': capital, 
                'as_on': date.today().strftime('%d-%m-%Y')
            }
            pdf = generate_balance_sheet_pdf(pdf_data)
            
            if pdf:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    pdf.output(tmp_file.name)
                    tmp_file.flush()
                    with open(tmp_file.name, 'rb') as f: 
                        pdf_bytes = f.read()
                    os.unlink(tmp_file.name)
                
                st.download_button(
                    label="Download Balance Sheet PDF", 
                    data=pdf_bytes, 
                    file_name=f"Balance_Sheet_{datetime.now().strftime('%Y%m%d')}.pdf", 
                    mime="application/pdf", 
                    use_container_width=True
                )
                st.success("Balance Sheet PDF generated successfully!")
            
    st.markdown('</div>', unsafe_allow_html=True)
    c.close()

# ==================== PROFIT & LOSS ====================
def profit_loss():
    if st.session_state.user['role'] not in ['admin','staff']: 
        st.error("Unauthorized"); return
    c = get_db()
    st.markdown('<div class="section-card"><h3>Profit & Loss Statement</h3>', unsafe_allow_html=True)
    d1, d2 = st.columns(2)
    with d1: fd = st.date_input("Period Start", date.today().replace(month=1, day=1), key="plf")
    with d2: td = st.date_input("Period End", date.today(), key="plt")
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Generate Statement", use_container_width=True, type="primary", key="pl"):
        inc = [
            ('Interest Income', c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Interest Earned' AND DATE(date) BETWEEN ? AND ?", (fd,td)).fetchone()[0]),
            ('Fee Income', c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Fees & Charges' AND DATE(date) BETWEEN ? AND ?", (fd,td)).fetchone()[0]),
            ('Commission Income', c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Commission Income' AND DATE(date) BETWEEN ? AND ?", (fd,td)).fetchone()[0]),
            ('Miscellaneous', c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type='Other Income' AND DATE(date) BETWEEN ? AND ?", (fd,td)).fetchone()[0])
        ]
        exp = [
            ('Interest Paid (SB)', c.execute("SELECT COALESCE(SUM(debit_amount),0) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE je.account_head='Interest Paid on SB' AND jv.status='POSTED' AND DATE(jv.voucher_date) BETWEEN ? AND ?", (fd,td)).fetchone()[0]),
            ('Salaries & Wages', c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Salary & Wages' AND DATE(date) BETWEEN ? AND ?", (fd,td)).fetchone()[0]),
            ('Rent & Utilities', c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Rent & Utilities' AND DATE(date) BETWEEN ? AND ?", (fd,td)).fetchone()[0]),
            ('Operating Exps.', c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Operating Expenses' AND DATE(date) BETWEEN ? AND ?", (fd,td)).fetchone()[0]),
            ('Admin Exps.', c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Administrative Expenses' AND DATE(date) BETWEEN ? AND ?", (fd,td)).fetchone()[0]),
            ('Other Expenses', c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type='Other Expenses' AND DATE(date) BETWEEN ? AND ?", (fd,td)).fetchone()[0])
        ]
        ti = sum(i[1] for i in inc)
        te = sum(e[1] for e in exp)
        net = ti - te
        
        q1, q2 = st.columns(2)
        
        income_data = []
        expense_data = []
        
        with q1:
            st.markdown('<div class="dash-card" style="text-align: left;"><h3 style="color:#0f172a;">INCOME</h3>', unsafe_allow_html=True)
            for item, amt in inc: 
                if amt > 0:
                    st.markdown(f"<p style='display:flex; justify-content:space-between; margin:5px 0;'><span>{item}:</span> <b>Rs{amt:,.2f}</b></p>", unsafe_allow_html=True)
                    income_data.append({'name': item, 'amount': amt})
            if not income_data: income_data.append({'name': 'No Income', 'amount': 0})
            st.markdown(f'<hr><p style="display:flex; justify-content:space-between; font-size:1.1rem; color:#0f172a;"><b>Total Income:</b> <b>Rs{ti:,.2f}</b></p></div>', unsafe_allow_html=True)
            
        with q2:
            st.markdown('<div class="dash-card" style="text-align: left;"><h3 style="color:#0f172a;">EXPENSES</h3>', unsafe_allow_html=True)
            for item, amt in exp:
                if amt > 0:
                    st.markdown(f"<p style='display:flex; justify-content:space-between; margin:5px 0;'><span>{item}:</span> <b>Rs{amt:,.2f}</b></p>", unsafe_allow_html=True)
                    expense_data.append({'name': item, 'amount': amt})
            if not expense_data: expense_data.append({'name': 'No Expenses', 'amount': 0})
            st.markdown(f'<hr><p style="display:flex; justify-content:space-between; font-size:1.1rem; color:#0f172a;"><b>Total Expenses:</b> <b>Rs{te:,.2f}</b></p></div>', unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        if net >= 0:
            st.success(f"### Net Profit: Rs{net:,.2f}")
        else:
            st.error(f"### Net Loss: Rs{abs(net):,.2f}")
        
        st.markdown("---")
        if st.button("Print Profit & Loss Statement (PDF)", use_container_width=True, type="primary"):
            pdf_data = {'income': income_data, 'expenses': expense_data}
            pdf = generate_profit_loss_pdf(pdf_data, fd.strftime('%d-%m-%Y'), td.strftime('%d-%m-%Y'))
            
            if pdf:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    pdf.output(tmp_file.name)
                    tmp_file.flush()
                    with open(tmp_file.name, 'rb') as f: pdf_bytes = f.read()
                    os.unlink(tmp_file.name)
                
                st.download_button(label="Download Profit & Loss PDF", data=pdf_bytes, file_name=f"Profit_Loss_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True)
                st.success("Profit & Loss PDF generated successfully!")
            
    st.markdown('</div>', unsafe_allow_html=True)
    c.close()

# ==================== REPORTS ====================
def reports():
    if st.session_state.user['role'] not in ['admin', 'staff']: 
        st.error("Unauthorized"); return
        
    c = get_db()
    st.markdown('<div class="section-card"><h3>Reporting Engine</h3>', unsafe_allow_html=True)
    rt = st.selectbox("Select Report Template", ["Customer List", "Interest Report", "Daily Transactions"])
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    report_data = None
    report_title = ""
    
    if rt == "Customer List":
        custs = c.execute("SELECT customer_id,first_name,last_name,email,phone,city,kyc_status,created_at FROM customers ORDER BY customer_id DESC").fetchall()
        if custs: 
            df = pd.DataFrame(custs, columns=['Customer ID', 'First Name', 'Last Name', 'Email', 'Phone', 'City', 'KYC Status', 'Created At'])
            df['Created At'] = pd.to_datetime(df['Created At']).dt.strftime('%d-%m-%Y %H:%M')
            st.dataframe(df, use_container_width=True, height=500)
            report_data = df.to_dict('records')
            report_title = "Customer List Report"
            
    elif rt == "Interest Report":
        calcs = c.execute("SELECT ic.calculation_date,a.account_number,c.first_name||' '||c.last_name,ic.principal_amount,ic.interest_rate,ic.interest_earned,ic.days_calculated FROM interest_calculations ic JOIN accounts a ON ic.account_id=a.id JOIN customers c ON a.customer_id=c.id ORDER BY ic.calculation_date DESC").fetchall()
        if calcs: 
            df = pd.DataFrame(calcs, columns=['Run Date', 'Account', 'Customer', 'Principal Computed', 'Rate', 'Interest Applied', 'Days'])
            df['Run Date'] = pd.to_datetime(df['Run Date']).dt.strftime('%d-%m-%Y')
            st.dataframe(df.style.format({'Principal Computed': 'Rs{:,.2f}', 'Interest Applied': 'Rs{:,.2f}'}), use_container_width=True, height=500)
            report_data = df.to_dict('records')
            report_title = "Interest Report"
            
    elif rt == "Daily Transactions":
        rd = st.date_input("Target Date", date.today(), key="rpd")
        txns = c.execute("SELECT t.transaction_id,c.first_name||' '||c.last_name,a.account_type,t.transaction_type,t.amount,t.voucher_number,t.created_at FROM transactions t JOIN accounts a ON t.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE DATE(t.created_at)=?", (rd,)).fetchall()
        if txns: 
            df = pd.DataFrame(txns, columns=['Txn Ref', 'Customer', 'Product Type', 'Action', 'Amount', 'Voucher', 'Time'])
            df['Time'] = pd.to_datetime(df['Time']).dt.strftime('%H:%M:%S')
            st.dataframe(df.style.format({'Amount': 'Rs{:,.2f}'}), use_container_width=True, height=500)
            report_data = df.to_dict('records')
            report_title = f"Daily Transactions - {rd.strftime('%d-%m-%Y')}"
        else: 
            st.info(f"No logged transactions occurred on {rd.strftime('%d-%m-%Y')}")
    
    if report_data:
        st.markdown("---")
        if st.button("Print Report (PDF)", use_container_width=True, type="primary"):
            pdf = generate_report_pdf(report_data, rt, report_title)
            
            if pdf:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    pdf.output(tmp_file.name)
                    tmp_file.flush()
                    with open(tmp_file.name, 'rb') as f: pdf_bytes = f.read()
                    os.unlink(tmp_file.name)
                
                st.download_button(label="Download Report PDF", data=pdf_bytes, file_name=f"{report_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True)
                st.success("Report PDF generated successfully!")
            
    st.markdown('</div>', unsafe_allow_html=True)
    c.close()

# ==================== MY DETAILS ====================
def my_details():
    c = get_db()
    uid = st.session_state.user['id']
    cust = c.execute("SELECT * FROM customers WHERE user_id=?", (uid,)).fetchone()
    
    if cust:
        st.markdown(f"""
        <div class="dash-card" style="background: linear-gradient(135deg, #0f2027, #2c5364); color: white; text-align: left; padding: 2rem;">
            <h2 style="color: white; margin-bottom: 0.5rem;">{cust[3]} {cust[4]}</h2>
            <p style="color: #cbd5e1; font-size: 1rem; margin:0;">ID: {cust[2]} | {cust[7]} | {cust[8]}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="section-card"><h3>My Savings Accounts</h3>', unsafe_allow_html=True)
        accs = c.execute("SELECT account_number,balance,COALESCE(total_interest_earned,0) FROM accounts WHERE customer_id=? AND account_type='SB'", (cust[0],)).fetchall()
        if accs:
            for a in accs:
                mv = a[1] + a[2]
                st.markdown(f"""
                <div style="background:#f8fafc; padding:1.2rem; border-radius:12px; margin:0.5rem 0; border-left:4px solid #203a43; box-shadow: 0 2px 4px rgba(0,0,0,0.03);">
                    <h4 style="margin: 0 0 10px 0; color:#0f172a;">Account: {a[0]}</h4>
                    <p style="margin: 0; color:#334155;">Total Deposits: <b>Rs{a[1]:,.2f}</b> | Interest Earned: <b>Rs{a[2]:,.2f}</b></p>
                    <p style="margin: 5px 0 0 0; color:#0f172a; font-size:1.1rem;">Total Amount: <b>Rs{mv:,.2f}</b></p>
                </div>
                """, unsafe_allow_html=True)
        else: 
            st.info("No active accounts found.")
        st.markdown('</div>', unsafe_allow_html=True)
    else: 
        st.warning("No profile information could be retrieved.")
    c.close()

if __name__ == "__main__":
    main()



