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
    if text is None: return "N/A"
    try: return str(text)
    except: return "Error"

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
            if min_bal <= 0: min_bal = acc[3]
            days = (to_date - from_date).days + 1
            if days > 0:
                interest = calculate_sb_interest(min_bal, acc[4] or 3.5, days)
                if interest > 0:
                    c.execute("UPDATE accounts SET total_interest_earned = COALESCE(total_interest_earned, 0) + ? WHERE id=?", (interest, acc[0]))
                    try:
                        c.execute("INSERT INTO interest_calculations (account_id, calculation_date, principal_amount, interest_rate, interest_earned, days_calculated, customer_id) VALUES (?, DATE('now'), ?, ?, ?, ?, ?)", (acc[0], min_bal, acc[4] or 3.5, interest, days, acc[6]))
                    except:
                        c.execute("INSERT INTO interest_calculations (account_id, calculation_date, principal_amount, interest_rate, interest_earned, days_calculated) VALUES (?, DATE('now'), ?, ?, ?, ?)", (acc[0], min_bal, acc[4] or 3.5, interest, days))
                    results.append({'account': acc[1], 'customer': acc[2], 'min_balance': min_bal, 'interest': interest, 'days': days})
        c.commit()
        return "SUCCESS", results
    except Exception as e:
        c.rollback()
        return f"ERROR: {str(e)}", []
    finally:
        c.close()

# ==================== PDF FUNCTIONS ====================
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
    if FPDF is None: return None
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
    if FPDF is None: return None
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
    for label, value in [('FD Number:', fd_data['fd_number']), ('Account Number:', fd_data['account_number']), ('Principal Amount:', f"Rs. {fd_data['principal']:,.2f}"), ('Interest Rate:', f"{fd_data['interest_rate']}% per annum"), ('Tenure:', f"{fd_data['tenure_months']} months"), ('Start Date:', fd_data['start_date']), ('Maturity Date:', fd_data['maturity_date']), ('Maturity Amount:', f"Rs. {fd_data['maturity_amount']:,.2f}"), ('Total Interest Earned:', f"Rs. {fd_data.get('total_interest', fd_data['maturity_amount'] - fd_data['principal']):,.2f}")]:
        pdf.cell(60, 6, label, 0, 0, 'L')
        pdf.cell(0, 6, value, 0, 1, 'L')
    if fd_data.get('nominee_name'):
        pdf.cell(60, 6, 'Nominee Name:', 0, 0, 'L')
        pdf.cell(0, 6, fd_data['nominee_name'], 0, 1, 'L')
    if fd_data.get('nominee_relation'):
        pdf.cell(60, 6, 'Nominee Relation:', 0, 0, 'L')
        pdf.cell(0, 6, fd_data['nominee_relation'], 0, 1, 'L')
    pdf.cell(60, 6, 'Status:', 0, 0, 'L')
    pdf.cell(0, 6, fd_data['status'], 0, 1, 'L')
    pdf.ln(5)
    pdf.set_font('Arial', 'I', 9)
    pdf.cell(0, 5, 'This is a system generated receipt.', 0, 1, 'C')
    pdf.cell(0, 5, f"Generated on: {get_ist_time()}", 0, 1, 'C')
    return pdf

def generate_rd_statement_pdf(rd_data, customer_data):
    if FPDF is None: return None
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
    for label, value in [('RD Number:', rd_data['rd_number']), ('Account Number:', rd_data['account_number']), ('Monthly Installment:', f"Rs. {rd_data['monthly_amount']:,.2f}"), ('Interest Rate:', f"{rd_data['interest_rate']}% per annum"), ('Tenure:', f"{rd_data['tenure_months']} months"), ('Total Installments:', str(rd_data['total_installments'])), ('Installments Paid:', str(rd_data['installments_paid'])), ('Start Date:', rd_data['start_date']), ('Maturity Date:', rd_data['maturity_date']), ('Maturity Amount (Projected):', f"Rs. {rd_data['maturity_amount']:,.2f}")]:
        pdf.cell(60, 6, label, 0, 0, 'L')
        pdf.cell(0, 6, value, 0, 1, 'L')
    if rd_data.get('nominee_name'):
        pdf.cell(60, 6, 'Nominee Name:', 0, 0, 'L')
        pdf.cell(0, 6, rd_data['nominee_name'], 0, 1, 'L')
    if rd_data.get('nominee_relation'):
        pdf.cell(60, 6, 'Nominee Relation:', 0, 0, 'L')
        pdf.cell(0, 6, rd_data['nominee_relation'], 0, 1, 'L')
    pdf.cell(60, 6, 'Status:', 0, 0, 'L')
    pdf.cell(0, 6, rd_data['status'], 0, 1, 'L')
    pdf.ln(5)
    pdf.set_font('Arial', 'I', 9)
    pdf.cell(0, 5, 'This is a system generated receipt.', 0, 1, 'C')
    pdf.cell(0, 5, f"Generated on: {get_ist_time()}", 0, 1, 'C')
    return pdf

def generate_journal_voucher_pdf(voucher_data, entries_data):
    if FPDF is None: return None
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
    pdf.cell(10, 7, 'S.No', 1)
    pdf.cell(80, 7, 'Account Head', 1)
    pdf.cell(45, 7, 'Debit (Dr)', 1, 0, 'R')
    pdf.cell(45, 7, 'Credit (Cr)', 1, 1, 'R')
    pdf.set_font('Arial', '', 9)
    total_dr = 0
    total_cr = 0
    for idx, entry in enumerate(entries_data, 1):
        debit = entry.get('debit_amount', entry.get('debit', 0))
        credit = entry.get('credit_amount', entry.get('credit', 0))
        account_head = entry.get('account_head', entry.get('head', 'N/A'))
        pdf.cell(10, 6, str(idx), 1)
        pdf.cell(80, 6, account_head, 1)
        pdf.cell(45, 6, f"{debit:,.2f}", 1, 0, 'R')
        pdf.cell(45, 6, f"{credit:,.2f}", 1, 1, 'R')
        total_dr += debit
        total_cr += credit
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(90, 7, 'TOTAL', 1)
    pdf.cell(45, 7, f"{total_dr:,.2f}", 1, 0, 'R')
    pdf.cell(45, 7, f"{total_cr:,.2f}", 1, 1, 'R')
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
    return pdf

def generate_profit_loss_pdf(data, from_date, to_date):
    if FPDF is None: return None
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
    if FPDF is None: return None
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
    if FPDF is None: return None
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
    if FPDF is None: return None
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
                if len(str(row[col])) > max_len: max_len = len(str(row[col]))
            col_widths.append(min(max_len * 2 + 4, 50))
        pdf.set_font('Arial', 'B', 9)
        for i, col in enumerate(columns):
            pdf.cell(col_widths[i], 7, col.upper(), 1, 0, 'C')
        pdf.ln()
        pdf.set_font('Arial', '', 8)
        for row in data:
            for i, col in enumerate(columns):
                value = str(row[col])
                if len(value) > 20: value = value[:17] + '...'
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
    .topbar { background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); color: white; padding: 1.2rem 2.5rem; border-radius: 14px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 2rem; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15); }
    .topbar h1 { margin: 0; font-size: 1.4rem; font-weight: 800; color: #ffffff !important; }
    .topbar .subtitle { font-size: 0.7rem; opacity: 0.8; }
    .topbar .user { font-size: 0.9rem; font-weight: 500; background: rgba(255,255,255,0.15); padding: 0.5rem 1.2rem; border-radius: 20px; }
    .dash-card { background: white; border: none; border-radius: 16px; padding: 1.8rem 1.2rem; text-align: center; transition: transform 0.3s; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 1rem; }
    .dash-card:hover { transform: translateY(-5px); box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); }
    .dash-card h2 { font-size: 2rem; margin: 0.5rem 0; font-weight: 800; color: #0f172a; }
    .dash-card p { margin: 0; font-size: 0.8rem; color: #64748b; font-weight: 700; text-transform: uppercase; }
    .section-card { background: white; border-radius: 16px; padding: 2rem; margin-bottom: 1.5rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); border: 1px solid #f1f5f9; }
    .section-card h3 { font-size: 1.2rem; font-weight: 700; color: #1e293b; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 2px solid #f1f5f9; }
    .login-wrapper { display: flex; justify-content: center; align-items: center; min-height: 90vh; background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); }
    .login-box { width: 100%; max-width: 420px; background: white; padding: 3rem 2.5rem; border-radius: 24px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.3); text-align: center; }
    [data-testid="stSidebar"] { background-color: #0f2027 !important; }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }
    .stButton>button { border-radius: 10px !important; font-weight: 700 !important; }
    div[data-testid="stFormSubmitButton"]>button, button[kind="primary"] { background: linear-gradient(135deg, #0f2027, #2c5364) !important; color: white !important; border: none !important; }
    </style>
    """, unsafe_allow_html=True)

# ==================== SESSION STATE ====================
def init_session_state():
    if 'user' not in st.session_state: st.session_state.user = None
    if 'page' not in st.session_state: st.session_state.page = 'dashboard'

# ==================== MAIN APP ====================
def main():
    st.set_page_config(page_title="Aasha Nidhi Bank", page_icon="🏦", layout="wide")
    init_database()
    create_default_admin()
    init_session_state()
    load_enterprise_css()
    if st.session_state.user is None: show_login()
    else: show_app()

def show_login():
    st.markdown('<div class="login-wrapper"><div class="login-box"><div class="bank-logo">🏦</div><h1>AASHA NIDHI PVT LIMITED</h1><div class="bank-subtitle">BALARAMAPURAM</div><p>Enterprise Banking Management Platform</p>', unsafe_allow_html=True)
    u = st.text_input("Username", key="lu")
    p = st.text_input("Password", type="password", key="lp")
    if st.button("Sign In", use_container_width=True, type="primary"):
        user = login_user(u, p)
        if user:
            st.session_state.user = {'id': user[0], 'username': user[1], 'role': user[3]}
            st.rerun()
        else: st.error("Invalid credentials")
    st.markdown('</div></div>', unsafe_allow_html=True)

def show_app():
    st.markdown(f'<div class="topbar"><div><h1>🏦 AASHA NIDHI PVT LIMITED BANK</h1><div class="subtitle">BALARAMAPURAM | Enterprise Banking System</div></div><div class="user">👤 {st.session_state.user["username"]} ({st.session_state.user["role"].upper()})</div></div>', unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown('<h3 style="color:white; text-align:center;">AASHA NIDHI BANK</h3><p style="color:white; text-align:center; font-size:0.7rem;">Balaramapuram</p>', unsafe_allow_html=True)
        menu = {'dashboard': 'Dashboard', 'customer_management': 'Customers', 'kyc_verification': 'KYC Center', 'create_sb_account': 'Open SB A/c', 'sb_accounts': 'SB Accounts', 'fixed_deposits': 'Fixed Deposits', 'recurring_deposits': 'Recurring Dep.', 'transactions': 'Transactions', 'journal_vouchers': 'Journal Vouchers', 'income_expenses': 'Income & Exp.', 'interest_calculation': 'Interest Calc', 'trial_balance': 'Trial Balance', 'balance_sheet': 'Balance Sheet', 'profit_loss': 'Profit & Loss', 'reports': 'Reports'} if st.session_state.user['role'] in ['admin', 'staff'] else {'dashboard': 'Dashboard', 'my_accounts': 'My Accounts', 'my_transactions': 'Transactions', 'my_details': 'Profile'}
        for k, v in menu.items():
            if st.sidebar.button(v, key=f"m_{k}", use_container_width=True):
                st.session_state.page = k
                st.rerun()
        if st.sidebar.button("Sign Out", use_container_width=True):
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

# ==================== ALL MODULE FUNCTIONS ====================
def dashboard():
    c = get_db()
    cust = c.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    sb = c.execute("SELECT COUNT(*) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    bal = c.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    intt = c.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE status='ACTIVE' AND account_type='SB'").fetchone()[0]
    kyc = c.execute("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'").fetchone()[0]
    cols = st.columns(4)
    cols[0].markdown(f'<div class="dash-card"><h2>{cust}</h2><p>Customers</p></div>', unsafe_allow_html=True)
    cols[1].markdown(f'<div class="dash-card"><h2>{sb}</h2><p>SB Accounts</p></div>', unsafe_allow_html=True)
    cols[2].markdown(f'<div class="dash-card"><h2>Rs{bal+intt:,.0f}</h2><p>SB Deposits</p></div>', unsafe_allow_html=True)
    cols[3].markdown(f'<div class="dash-card"><h2>{kyc}</h2><p>Pending KYC</p></div>', unsafe_allow_html=True)
    c.close()

def customer_mgmt():
    t1, t2 = st.tabs(["Register", "View All"])
    with t1:
        with st.form("cr"):
            c1, c2 = st.columns(2)
            with c1: fn = st.text_input("First Name*"); ln = st.text_input("Last Name*"); dob = st.date_input("Date of Birth*", min_value=date(1900,1,1)); email = st.text_input("Email*"); phone = st.text_input("Phone*")
            with c2: pan = st.text_input("PAN*"); aadhar = st.text_input("Aadhar*"); addr = st.text_area("Address"); city = st.text_input("City"); state = st.text_input("State"); pin = st.text_input("PIN")
            pan_doc = st.file_uploader("PAN Card*", type=['jpg','jpeg','png','pdf'])
            aadhar_doc = st.file_uploader("Aadhar Card*", type=['jpg','jpeg','png','pdf'])
            if st.form_submit_button("Register", use_container_width=True, type="primary"):
                if all([fn, ln, email, phone, pan, aadhar]) and pan_doc and aadhar_doc:
                    try:
                        conn = get_db()
                        conn.execute("INSERT INTO customers (customer_id,first_name,last_name,date_of_birth,email,phone,address,city,state,pincode,pan_number,aadhar_number,pan_document,aadhar_document) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (generate_id('CUST'), fn, ln, dob, email, phone, addr, city, state, pin, pan, aadhar, pan_doc.read(), aadhar_doc.read()))
                        conn.commit(); conn.close()
                        st.success("Customer registered!"); st.balloons()
                    except Exception as e: st.error(str(e))
                else: st.error("Fill all required fields")
    with t2:
        conn = get_db()
        custs = conn.execute("SELECT customer_id,first_name,last_name,email,phone,city,kyc_status FROM customers ORDER BY customer_id DESC").fetchall()
        if custs: st.dataframe(pd.DataFrame(custs, columns=['ID','First','Last','Email','Phone','City','KYC']), use_container_width=True)
        else: st.info("No customers")
        conn.close()

def kyc_verify():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c = get_db()
    pending = c.execute("SELECT * FROM customers WHERE kyc_status='PENDING'").fetchall()
    if not pending: st.success("All verified!")
    else:
        for cust in pending:
            with st.expander(f"{cust[3]} {cust[4]} ({cust[2]})"):
                b1, b2 = st.columns(2)
                if b1.button("Approve", key=f"a_{cust[0]}"): c.execute("UPDATE customers SET kyc_status='VERIFIED',kyc_verified_by=?,kyc_verified_at=CURRENT_TIMESTAMP WHERE id=?", (st.session_state.user['id'], cust[0])); c.commit(); st.rerun()
                if b2.button("Reject", key=f"r_{cust[0]}"): c.execute("UPDATE customers SET kyc_status='REJECTED' WHERE id=?", (cust[0],)); c.commit(); st.rerun()
    c.close()

def create_sb():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c = get_db()
    custs = c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c WHERE NOT EXISTS (SELECT 1 FROM accounts a WHERE a.customer_id=c.id AND a.account_type='SB' AND a.status='ACTIVE')").fetchall()
    if not custs: st.success("All customers have SB accounts!")
    else:
        sel = st.selectbox("Select Customer", [f"{x[1]} - {x[2]}" for x in custs])
        if sel:
            idx = [f"{x[1]} - {x[2]}" for x in custs].index(sel)
            cust = custs[idx]
            with st.form("sb"):
                rate = st.number_input("Interest Rate (%)", 0.0, 10.0, 3.5, 0.25)
                bal = st.number_input("Opening Balance (Rs)", 0.0, step=100.0)
                if st.form_submit_button("Create Account", use_container_width=True, type="primary"):
                    an = generate_account_number('SB')
                    c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate,last_interest_calculation,total_interest_earned) VALUES (?,?,'SB',?,?,DATE('now'),0.00)", (an, cust[0], bal, rate))
                    c.commit()
                    st.success(f"Account Created: {an}")
    c.close()

def sb_accounts():
    c = get_db()
    t1, t2 = st.tabs(["Transact", "Statement"])
    role = st.session_state.user['role']
    uid = st.session_state.user['id']
    
    with t1:
        q = "SELECT a.id,a.account_number,c.first_name||' '||c.last_name,a.balance,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND " + ("c.user_id=?" if role=='customer' else "1=1")
        accs = c.execute(q, (uid,) if role=='customer' else ()).fetchall()
        if accs:
            sel = st.selectbox("Select Account", [f"{a[1]} - {a[2]} (Rs{a[3]+a[4]:,.2f})" for a in accs])
            if sel:
                idx = [f"{a[1]} - {a[2]} (Rs{a[3]+a[4]:,.2f})" for a in accs].index(sel)
                acc = accs[idx]
                tt = st.radio("Type", ["Deposit", "Withdraw"], horizontal=True)
                with st.form("tx"):
                    amt = st.number_input("Amount", min_value=0.01, step=100.0)
                    mode = st.selectbox("Mode", ["CASH", "BANK", "CHEQUE"])
                    desc = st.text_input("Description")
                    if st.form_submit_button("Process", use_container_width=True, type="primary"):
                        at = "DEPOSIT" if tt=="Deposit" else "WITHDRAWAL"
                        if at=="WITHDRAWAL" and amt>acc[3]: st.error("Insufficient funds!")
                        else:
                            nb = acc[3]+amt if at=="DEPOSIT" else acc[3]-amt
                            tdb = "CREDIT" if at=="DEPOSIT" else "DEBIT"
                            vt = "RECEIPT" if at=="DEPOSIT" else "PAYMENT"
                            # Debit leg: Cash/Bank (for deposit) or SB Account (for withdrawal)
                            # Credit leg: SB Account (for deposit) or Cash/Bank (for withdrawal)
                            c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,?,?,?,?,?,?,?,?)", (generate_id('TXN'), acc[0], tdb, amt, nb, desc, mode, vt, generate_voucher_number(vt), uid))
                            c.execute("UPDATE accounts SET balance=? WHERE id=?", (nb, acc[0]))
                            c.commit()
                            st.success(f"Done! New Balance: Rs{nb+acc[4]:,.2f}"); st.rerun()
    
    with t2:
        q2 = "SELECT a.id,a.account_number,c.customer_id,c.first_name||' '||c.last_name,a.balance,a.interest_rate,COALESCE(a.total_interest_earned,0) FROM accounts a JOIN customers c ON a.customer_id=c.id WHERE a.account_type='SB' AND a.status='ACTIVE' AND " + ("c.user_id=?" if role=='customer' else "1=1")
        accs = c.execute(q2, (uid,) if role=='customer' else ()).fetchall()
        if accs:
            sel = st.selectbox("Choose Account", [f"{a[1]} - {a[4]}" for a in accs], key="ss")
            if sel:
                idx = [f"{a[1]} - {a[4]}" for a in accs].index(sel)
                acc = accs[idx]
                d1, d2 = st.columns(2)
                with d1: fd = st.date_input("From", date.today()-timedelta(days=30))
                with d2: td = st.date_input("To", date.today())
                txns = c.execute("SELECT created_at, transaction_type, amount, balance_after, description FROM transactions WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ? ORDER BY created_at DESC", (acc[0], fd, td)).fetchall()
                if txns:
                    df = pd.DataFrame(txns, columns=['Date','Type','Amount','Balance','Description'])
                    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%d-%m-%Y %H:%M')
                    st.dataframe(df.style.format({'Amount':'Rs{:,.2f}','Balance':'Rs{:,.2f}'}), use_container_width=True)
    c.close()

def fixed_deposits():
    c = get_db()
    uid = st.session_state.user['id']
    t1, t2 = st.tabs(["Open FD", "Active FDs"])
    with t1:
        custs = c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        if custs:
            sel = st.selectbox("Select Customer", [f"{x[1]} - {x[2]}" for x in custs])
            if sel:
                idx = [f"{x[1]} - {x[2]}" for x in custs].index(sel)
                cust = custs[idx]
                with st.form("fd"):
                    p = st.number_input("Principal", min_value=1000.0, step=1000.0, value=10000.0)
                    t = st.selectbox("Tenure (Months)", [1,3,6,9,12,18,24,36,48,60])
                    r = st.number_input("Interest Rate (%)", 3.0, 10.0, 6.5, 0.25)
                    sd = st.date_input("Start Date", date.today())
                    md = sd + relativedelta(months=t)
                    ma = calculate_fd_maturity(p, r, t)
                    st.info(f"Maturity: {md.strftime('%d-%m-%Y')} | Value: Rs{ma:,.2f}")
                    if st.form_submit_button("Open FD", use_container_width=True, type="primary"):
                        fdn = generate_id('FD'); an = generate_account_number('FD')
                        c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate) VALUES (?,?,'FD',0.00,?)", (an, cust[0], r))
                        aid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                        c.execute("INSERT INTO fixed_deposits (fd_number,account_id,principal_amount,interest_rate,start_date,maturity_date,maturity_amount,tenure_months) VALUES (?,?,?,?,?,?,?,?)", (fdn, aid, p, r, sd, md, ma, t))
                        # Debit: FD Account (Asset), Credit: SB Account (Liability decreases) or Cash
                        c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,'FD Deposit','FD','RECEIPT',?,?)", (generate_id('TXN'), aid, p, p, generate_voucher_number('RECEIPT'), uid))
                        c.commit()
                        st.success(f"FD Opened: {fdn}"); st.balloons()
    with t2:
        fds = c.execute("SELECT fd.fd_number, c.first_name||' '||c.last_name, fd.principal_amount, fd.interest_rate, fd.maturity_date, fd.maturity_amount, fd.status FROM fixed_deposits fd JOIN accounts a ON fd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE fd.status='ACTIVE'").fetchall()
        if fds: st.dataframe(pd.DataFrame(fds, columns=['FD Ref','Customer','Principal','Rate','Maturity','Maturity Value','Status']).style.format({'Principal':'Rs{:,.2f}','Maturity Value':'Rs{:,.2f}'}), use_container_width=True)
        else: st.info("No active FDs")
    c.close()

def recurring_deposits():
    c = get_db()
    uid = st.session_state.user['id']
    t1, t2 = st.tabs(["Open RD", "Active RDs"])
    with t1:
        custs = c.execute("SELECT c.id,c.customer_id,c.first_name||' '||c.last_name FROM customers c JOIN accounts a ON c.id=a.customer_id WHERE a.account_type='SB' AND a.status='ACTIVE'").fetchall()
        if custs:
            sel = st.selectbox("Select Customer", [f"{x[1]} - {x[2]}" for x in custs])
            if sel:
                idx = [f"{x[1]} - {x[2]}" for x in custs].index(sel)
                cust = custs[idx]
                with st.form("rd"):
                    m = st.number_input("Monthly Installment", min_value=100.0, step=100.0, value=1000.0)
                    t = st.selectbox("Tenure (Months)", [3,6,9,12,18,24,36,48,60])
                    r = st.number_input("Interest Rate (%)", 3.0, 10.0, 6.0, 0.25)
                    sd = st.date_input("Start Date", date.today())
                    md = sd + relativedelta(months=t)
                    ma = calculate_rd_maturity(m, r, t)
                    st.info(f"Maturity: {md.strftime('%d-%m-%Y')} | Value: Rs{ma:,.2f}")
                    if st.form_submit_button("Open RD", use_container_width=True, type="primary"):
                        rdn = generate_id('RD'); an = generate_account_number('RD')
                        c.execute("INSERT INTO accounts (account_number,customer_id,account_type,balance,interest_rate) VALUES (?,?,'RD',0.00,?)", (an, cust[0], r))
                        aid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                        c.execute("INSERT INTO recurring_deposits (rd_number,account_id,monthly_amount,interest_rate,start_date,maturity_date,maturity_amount,tenure_months,total_installments) VALUES (?,?,?,?,?,?,?,?,?)", (rdn, aid, m, r, sd, md, ma, t, t))
                        c.execute("INSERT INTO transactions (transaction_id,account_id,transaction_type,amount,balance_after,description,reference_type,voucher_type,voucher_number,created_by) VALUES (?,?,'CREDIT',?,?,'RD Install 1','RD','RECEIPT',?,?)", (generate_id('TXN'), aid, m, m, generate_voucher_number('RECEIPT'), uid))
                        c.execute("UPDATE recurring_deposits SET installments_paid=1 WHERE rd_number=?", (rdn,))
                        c.commit()
                        st.success(f"RD Opened: {rdn}"); st.balloons()
    with t2:
        rds = c.execute("SELECT rd.rd_number, c.first_name||' '||c.last_name, rd.monthly_amount, rd.interest_rate, rd.installments_paid, rd.total_installments, rd.maturity_amount FROM recurring_deposits rd JOIN accounts a ON rd.account_id=a.id JOIN customers c ON a.customer_id=c.id WHERE rd.status='ACTIVE'").fetchall()
        if rds: st.dataframe(pd.DataFrame(rds, columns=['RD Ref','Customer','Monthly','Rate','Paid','Total','Maturity']).style.format({'Monthly':'Rs{:,.2f}','Maturity':'Rs{:,.2f}'}), use_container_width=True)
        else: st.info("No active RDs")
    c.close()

def transactions():
    c = get_db()
    txns = c.execute("SELECT t.transaction_id,c.first_name||' '||c.last_name,a.account_type,t.transaction_type,t.amount,t.reference_type,t.description,t.created_at FROM transactions t LEFT JOIN accounts a ON t.account_id=a.id LEFT JOIN customers c ON a.customer_id=c.id ORDER BY t.created_at DESC LIMIT 100").fetchall()
    if txns:
        df = pd.DataFrame(txns, columns=['Txn ID','Customer','Account','Type','Amount','Mode','Description','Date'])
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%d-%m-%Y %H:%M')
        st.dataframe(df.style.format({'Amount':'Rs{:,.2f}'}), use_container_width=True, height=500)
    else: st.info("No transactions")
    c.close()

def journal_vouchers():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c = get_db()
    uid = st.session_state.user['id']
    t1, t2 = st.tabs(["Create JV", "Manage Vouchers"])
    
    with t1:
        with st.form("jv"):
            vd = st.date_input("Voucher Date", date.today())
            desc = st.text_area("Narration")
            n = st.number_input("Number of Entries", 2, 10, 2)
            entries = []; td_v = 0; tc_v = 0
            for i in range(int(n)):
                st.markdown(f"**Entry {i+1}**")
                e1, e2, e3 = st.columns([2,1,1])
                with e1: h = st.text_input(f"Account Head", key=f"jh{i}", placeholder="e.g., Capital A/c, Bank A/c")
                with e2: d = st.number_input(f"Debit", min_value=0.0, step=100.0, key=f"jd{i}")
                with e3: cr = st.number_input(f"Credit", min_value=0.0, step=100.0, key=f"jc{i}")
                td_v += d; tc_v += cr
                entries.append({'h':h,'d':d,'c':cr})
            st.info(f"Debit: Rs{td_v:,.2f} | Credit: Rs{tc_v:,.2f}")
            if st.form_submit_button("Generate Voucher", use_container_width=True, type="primary"):
                if abs(td_v-tc_v)>0.01: st.error("Must be balanced!")
                else:
                    vn = generate_voucher_number('JOURNAL')
                    c.execute("INSERT INTO journal_vouchers (voucher_number,voucher_date,description,total_amount,created_by) VALUES (?,?,?,?,?)", (vn, vd, desc, td_v, uid))
                    vid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                    for e in entries:
                        if (e['d']>0 or e['c']>0) and e['h'].strip():
                            c.execute("INSERT INTO journal_entries (voucher_id,account_head,debit_amount,credit_amount) VALUES (?,?,?,?)", (vid, e['h'].strip(), e['d'], e['c']))
                    c.commit()
                    st.success(f"Voucher Created: {vn}"); st.rerun()
    
    with t2:
        vouchers = c.execute("SELECT id, voucher_number, voucher_date, description, total_amount, status FROM journal_vouchers ORDER BY created_at DESC").fetchall()
        if vouchers:
            for v in vouchers:
                with st.expander(f"{v[1]} | {v[2]} | Rs{v[4]:,.2f} | {v[5]}"):
                    entries = c.execute("SELECT account_head, debit_amount, credit_amount FROM journal_entries WHERE voucher_id=?", (v[0],)).fetchall()
                    if entries:
                        df = pd.DataFrame(entries, columns=['Account Head','Debit (Dr)','Credit (Cr)'])
                        st.dataframe(df.style.format({'Debit (Dr)':'Rs{:,.2f}','Credit (Cr)':'Rs{:,.2f}'}), use_container_width=True)
                    if v[5]=='DRAFT':
                        b1, b2 = st.columns(2)
                        if b1.button("Post", key=f"po_{v[0]}"): c.execute("UPDATE journal_vouchers SET status='POSTED',posted_by=?,posted_at=CURRENT_TIMESTAMP WHERE id=?", (uid, v[0])); c.commit(); st.rerun()
                        if b2.button("Cancel", key=f"ca_{v[0]}"): c.execute("UPDATE journal_vouchers SET status='CANCELLED' WHERE id=?", (v[0],)); c.commit(); st.rerun()
        else: st.info("No vouchers")
    c.close()

def income_expenses():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c = get_db()
    uid = st.session_state.user['id']
    t1, t2, t3, t4 = st.tabs(["Record Income", "Record Expense", "View Income", "View Expenses"])
    
    with t1:
        st.info("Income = CREDIT entry | Debit to Cash/Bank")
        with st.form("if"):
            it = st.selectbox("Income Type", ["Interest Earned", "Fees & Charges", "Commission Income", "Other Income"])
            amt = st.number_input("Amount (Rs)", min_value=1.0, step=100.0)
            mode = st.selectbox("Payment Mode", ["CASH", "BANK", "CHEQUE"])
            dt = st.date_input("Date", date.today())
            desc = st.text_area("Description")
            st.markdown(f"**JV Preview:** Dr Cash/Bank({mode}) Rs{amt:,.2f} | Cr {it} Rs{amt:,.2f}")
            if st.form_submit_button("Record Income", use_container_width=True, type="primary"):
                c.execute("INSERT INTO income (income_id,income_type,amount,description,date,created_by) VALUES (?,?,?,?,?,?)", (generate_id('INC'), it, amt, desc, dt, uid))
                # Debit leg: Cash/Bank increases (CREDIT transaction)
                c.execute("INSERT INTO transactions (transaction_id, account_id, transaction_type, amount, balance_after, description, reference_type, voucher_type, voucher_number, created_by) VALUES (?,0,'CREDIT',?,?,?,?,?,?,?)", (generate_id('TXN'), amt, amt, f"Income: {it}", mode, 'RECEIPT', generate_voucher_number('RECEIPT'), uid))
                c.commit()
                st.success(f"Income recorded: Rs{amt:,.2f}")
    
    with t2:
        st.info("Expense = DEBIT entry | Credit to Cash/Bank")
        with st.form("ef"):
            et = st.selectbox("Expense Type", ["Salary & Wages", "Rent & Utilities", "Operating Expenses", "Administrative Expenses", "Other Expenses"])
            amt = st.number_input("Amount (Rs)", min_value=1.0, step=100.0)
            mode = st.selectbox("Payment Mode", ["CASH", "BANK", "CHEQUE"])
            dt = st.date_input("Date", date.today())
            desc = st.text_area("Description")
            st.markdown(f"**JV Preview:** Dr {et} Rs{amt:,.2f} | Cr Cash/Bank({mode}) Rs{amt:,.2f}")
            if st.form_submit_button("Record Expense", use_container_width=True, type="primary"):
                c.execute("INSERT INTO expenses (expense_id,expense_type,amount,description,date,created_by) VALUES (?,?,?,?,?,?)", (generate_id('EXP'), et, amt, desc, dt, uid))
                # Credit leg: Cash/Bank decreases (DEBIT transaction)
                c.execute("INSERT INTO transactions (transaction_id, account_id, transaction_type, amount, balance_after, description, reference_type, voucher_type, voucher_number, created_by) VALUES (?,0,'DEBIT',?,?,?,?,?,?,?)", (generate_id('TXN'), amt, -amt, f"Expense: {et}", mode, 'PAYMENT', generate_voucher_number('PAYMENT'), uid))
                c.commit()
                st.success(f"Expense recorded: Rs{amt:,.2f}")
    
    with t3:
        inc = c.execute("SELECT income_type, COALESCE(SUM(amount),0) FROM income GROUP BY income_type").fetchall()
        if inc: st.dataframe(pd.DataFrame(inc, columns=['Type','Amount (Cr)']).style.format({'Amount (Cr)':'Rs{:,.2f}'}), use_container_width=True)
        else: st.info("No income")
    
    with t4:
        exp = c.execute("SELECT expense_type, COALESCE(SUM(amount),0) FROM expenses GROUP BY expense_type").fetchall()
        if exp: st.dataframe(pd.DataFrame(exp, columns=['Type','Amount (Dr)']).style.format({'Amount (Dr)':'Rs{:,.2f}'}), use_container_width=True)
        else: st.info("No expenses")
    
    total_inc = c.execute("SELECT COALESCE(SUM(amount),0) FROM income").fetchone()[0]
    total_exp = c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
    if total_inc>0 or total_exp>0:
        st.metric("Net", f"Rs{total_inc-total_exp:,.2f}", delta="Surplus" if total_inc>=total_exp else "Deficit")
    c.close()

def interest_calc():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c = get_db()
    uid = st.session_state.user['id']
    d1, d2 = st.columns(2)
    with d1: cfd = st.date_input("From", date.today().replace(day=1))
    with d2: ctd = st.date_input("To", date.today())
    if st.button("Calculate & Post Interest", use_container_width=True, type="primary"):
        s, r = calculate_and_post_sb_interest(uid, cfd, ctd)
        if s=="SUCCESS" and r: st.success(f"Posted Rs{sum(x['interest'] for x in r):,.2f} interest")
        else: st.info("No interest to post")
    c.close()

def trial_balance():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c = get_db()
    if st.button("Generate Trial Balance", use_container_width=True, type="primary"):
        td = []
        # Assets (Debit balances)
        for mode, name in [('CASH','Cash in Hand'), ('BANK','Cash in Bank'), ('CHEQUE','Cash (Cheque)')]:
            bal = c.execute("SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END),0) FROM transactions WHERE reference_type=?", (mode,)).fetchone()[0]
            if abs(bal)>0: td.append({'head':name,'cat':'Asset','dr':max(bal,0),'cr':max(-bal,0)})
        
        # Liabilities (Credit balances)
        sb = c.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb>0: td.append({'head':'SB Deposits','cat':'Liability','dr':0,'cr':sb})
        fd = c.execute("SELECT COALESCE(SUM(principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        if fd>0: td.append({'head':'FD Deposits','cat':'Liability','dr':0,'cr':fd})
        rd = c.execute("SELECT COALESCE(SUM(monthly_amount*installments_paid),0) FROM recurring_deposits WHERE status='ACTIVE'").fetchone()[0]
        if rd>0: td.append({'head':'RD Deposits','cat':'Liability','dr':0,'cr':rd})
        
        # Interest payable
        sb_int = c.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb_int>0: td.append({'head':'SB Interest Payable','cat':'Liability','dr':0,'cr':sb_int})
        
        # Income
        for it in ['Interest Earned','Fees & Charges','Commission Income','Other Income']:
            amt = c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE income_type=?",(it,)).fetchone()[0]
            if amt>0: td.append({'head':it,'cat':'Income','dr':0,'cr':amt})
        
        # Expenses
        for et in ['Salary & Wages','Rent & Utilities','Operating Expenses','Administrative Expenses','Other Expenses']:
            amt = c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_type=?",(et,)).fetchone()[0]
            if amt>0: td.append({'head':et,'cat':'Expense','dr':amt,'cr':0})
        
        # JV entries (posted)
        jve = c.execute("SELECT je.account_head, SUM(je.debit_amount), SUM(je.credit_amount) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE jv.status='POSTED' GROUP BY je.account_head").fetchall()
        for e in jve:
            if e[1]>0: td.append({'head':e[0],'cat':'Asset' if e[1]>e[2] else 'Expense','dr':e[1],'cr':0})
            if e[2]>0: td.append({'head':e[0],'cat':'Liability' if e[2]>e[1] else 'Income','dr':0,'cr':e[2]})
        
        tdr = sum(i['dr'] for i in td)
        tcr = sum(i['cr'] for i in td)
        if abs(tcr-tdr)>0.01: td.append({'head':'Capital/Equity','cat':'Capital','dr':max(tdr-tcr,0),'cr':max(tcr-tdr,0)})
        
        if td:
            df = pd.DataFrame(td)
            st.dataframe(df[['head','cat','dr','cr']].rename(columns={'head':'Account Head','cat':'Category','dr':'Debit','cr':'Credit'}).style.format({'Debit':'Rs{:,.2f}','Credit':'Rs{:,.2f}'}), use_container_width=True)
            dft = df['dr'].sum(); cft = df['cr'].sum()
            st.metric("Debit Total", f"Rs{dft:,.2f}"); st.metric("Credit Total", f"Rs{cft:,.2f}")
            if abs(dft-cft)<0.01: st.success("BALANCED")
    c.close()

def balance_sheet():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c = get_db()
    if st.button("Generate Balance Sheet", use_container_width=True, type="primary"):
        # ASSETS
        assets_data = []
        total_assets = 0
        for mode, name in [('CASH','Cash in Hand'), ('BANK','Cash in Bank'), ('CHEQUE','Cash (Cheque)')]:
            bal = c.execute("SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END),0) FROM transactions WHERE reference_type=?", (mode,)).fetchone()[0]
            if abs(bal)>0: assets_data.append({'name':name,'amount':bal}); total_assets += bal
        
        total_inc = c.execute("SELECT COALESCE(SUM(amount),0) FROM income").fetchone()[0]
        if total_inc>0: assets_data.append({'name':'Income Receivable','amount':total_inc}); total_assets += total_inc
        
        jv_dr = c.execute("SELECT je.account_head, SUM(je.debit_amount) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE jv.status='POSTED' AND je.debit_amount>0 GROUP BY je.account_head").fetchall()
        for e in jv_dr:
            if e[1]>0: assets_data.append({'name':f'JV: {e[0]}','amount':e[1]}); total_assets += e[1]
        
        # LIABILITIES
        liabilities_data = []
        total_liabilities = 0
        sb = c.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb>0: liabilities_data.append({'name':'SB Deposits','amount':sb}); total_liabilities += sb
        fd = c.execute("SELECT COALESCE(SUM(principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        if fd>0: liabilities_data.append({'name':'FD Deposits','amount':fd}); total_liabilities += fd
        rd = c.execute("SELECT COALESCE(SUM(monthly_amount*installments_paid),0) FROM recurring_deposits WHERE status='ACTIVE'").fetchone()[0]
        if rd>0: liabilities_data.append({'name':'RD Deposits','amount':rd}); total_liabilities += rd
        
        sb_int = c.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb_int>0: liabilities_data.append({'name':'SB Interest Payable','amount':sb_int}); total_liabilities += sb_int
        
        total_exp = c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
        if total_exp>0: liabilities_data.append({'name':'Expenses Payable','amount':total_exp}); total_liabilities += total_exp
        
        jv_cr = c.execute("SELECT je.account_head, SUM(je.credit_amount) FROM journal_entries je JOIN journal_vouchers jv ON je.voucher_id=jv.id WHERE jv.status='POSTED' AND je.credit_amount>0 GROUP BY je.account_head").fetchall()
        for e in jv_cr:
            if e[1]>0: liabilities_data.append({'name':f'JV: {e[0]}','amount':e[1]}); total_liabilities += e[1]
        
        capital = total_assets - total_liabilities
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### ASSETS")
            for item in assets_data: st.markdown(f"- **{item['name']}**: Rs{item['amount']:,.2f}")
            st.markdown(f"**Total Assets: Rs{total_assets:,.2f}**")
        with col2:
            st.markdown("### LIABILITIES")
            for item in liabilities_data: st.markdown(f"- **{item['name']}**: Rs{item['amount']:,.2f}")
            st.markdown(f"**Total Liabilities: Rs{total_liabilities:,.2f}**")
        
        st.markdown(f"### CAPITAL/EQUITY: Rs{capital:,.2f}")
        if abs(total_assets-(total_liabilities+capital))<0.01: st.success("Balance Sheet Balanced")
    c.close()

def profit_loss():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c = get_db()
    d1, d2 = st.columns(2)
    with d1: fd = st.date_input("From", date.today().replace(month=1,day=1))
    with d2: td = st.date_input("To", date.today())
    if st.button("Generate P&L", use_container_width=True, type="primary"):
        inc = c.execute("SELECT income_type, COALESCE(SUM(amount),0) FROM income WHERE DATE(date) BETWEEN ? AND ? GROUP BY income_type", (fd,td)).fetchall()
        exp = c.execute("SELECT expense_type, COALESCE(SUM(amount),0) FROM expenses WHERE DATE(date) BETWEEN ? AND ? GROUP BY expense_type", (fd,td)).fetchall()
        ti = sum(i[1] for i in inc); te = sum(e[1] for e in exp)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### INCOME")
            for i in inc: st.markdown(f"- {i[0]}: Rs{i[1]:,.2f}")
            st.markdown(f"**Total: Rs{ti:,.2f}**")
        with col2:
            st.markdown("### EXPENSES")
            for e in exp: st.markdown(f"- {e[0]}: Rs{e[1]:,.2f}")
            st.markdown(f"**Total: Rs{te:,.2f}**")
        net = ti-te
        if net>=0: st.success(f"Net Profit: Rs{net:,.2f}")
        else: st.error(f"Net Loss: Rs{abs(net):,.2f}")
    c.close()

def reports():
    if st.session_state.user['role'] not in ['admin','staff']: st.error("Unauthorized"); return
    c = get_db()
    rt = st.selectbox("Report", ["Customer List", "Daily Transactions"])
    if rt=="Customer List":
        custs = c.execute("SELECT customer_id,first_name,last_name,email,phone,kyc_status FROM customers").fetchall()
        if custs: st.dataframe(pd.DataFrame(custs, columns=['ID','First','Last','Email','Phone','KYC']), use_container_width=True)
    elif rt=="Daily Transactions":
        rd = st.date_input("Date", date.today())
        txns = c.execute("SELECT t.transaction_id,c.first_name||' '||c.last_name,a.account_type,t.transaction_type,t.amount,t.reference_type,t.created_at FROM transactions t LEFT JOIN accounts a ON t.account_id=a.id LEFT JOIN customers c ON a.customer_id=c.id WHERE DATE(t.created_at)=?", (rd,)).fetchall()
        if txns: st.dataframe(pd.DataFrame(txns, columns=['Txn ID','Customer','Account','Type','Amount','Mode','Time']), use_container_width=True)
        else: st.info("No transactions")
    c.close()

def my_details():
    c = get_db()
    uid = st.session_state.user['id']
    cust = c.execute("SELECT * FROM customers WHERE user_id=?", (uid,)).fetchone()
    if cust:
        st.markdown(f"### {cust[3]} {cust[4]}")
        st.markdown(f"ID: {cust[2]} | Email: {cust[7]} | Phone: {cust[8]}")
        accs = c.execute("SELECT account_number,balance,COALESCE(total_interest_earned,0) FROM accounts WHERE customer_id=? AND account_type='SB'", (cust[0],)).fetchall()
        if accs:
            for a in accs: st.markdown(f"**{a[0]}**: Deposits Rs{a[1]:,.2f} + Interest Rs{a[2]:,.2f} = Rs{a[1]+a[2]:,.2f}")
    else: st.warning("No profile found")
    c.close()

if __name__ == "__main__":
    main()



