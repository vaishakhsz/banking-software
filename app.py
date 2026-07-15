import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import os
import time
import re

# ============== DATABASE SETUP ==============
DB_FILE = "banking_system.db"

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    """Initialize database with tables and default data"""
    conn = get_db()
    c = conn.cursor()
    
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            full_name TEXT,
            role TEXT
        )
    ''')
    
    # Accounts table
    c.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT,
            type TEXT,
            balance REAL DEFAULT 0
        )
    ''')
    
    # Journal entries
    c.execute('''
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            account_code TEXT,
            account_name TEXT,
            entry_type TEXT,
            amount REAL,
            description TEXT,
            voucher_no TEXT
        )
    ''')
    
    # Vouchers
    c.execute('''
        CREATE TABLE IF NOT EXISTS vouchers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_no TEXT UNIQUE,
            voucher_type TEXT,
            date TEXT,
            description TEXT,
            total_amount REAL
        )
    ''')
    
    # SB Accounts
    c.execute('''
        CREATE TABLE IF NOT EXISTS sb_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT UNIQUE,
            customer_name TEXT,
            balance REAL DEFAULT 0,
            interest_rate REAL DEFAULT 3.5,
            interest_payable REAL DEFAULT 0,
            opening_date TEXT,
            status TEXT DEFAULT 'ACTIVE'
        )
    ''')
    
    # SB Transactions
    c.execute('''
        CREATE TABLE IF NOT EXISTS sb_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT,
            date TEXT,
            particulars TEXT,
            debit REAL DEFAULT 0,
            credit REAL DEFAULT 0,
            balance REAL,
            type TEXT
        )
    ''')
    
    # Customers
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT UNIQUE,
            full_name TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            aadhar TEXT,
            pan TEXT,
            aadhar_image TEXT,
            pan_image TEXT,
            nominee_name TEXT,
            nominee_aadhar TEXT,
            nominee_pan TEXT,
            nominee_aadhar_image TEXT,
            nominee_pan_image TEXT
        )
    ''')
    
    # Insert default admin
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        hashed = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", 
                 (None, "admin", hashed, "Administrator", "admin"))
    
    # Insert default accounts
    c.execute("SELECT * FROM accounts")
    if not c.fetchone():
        accounts = [
            ('1000', 'CASH', 'ASSET', 0),
            ('1100', 'BANK_SAVINGS', 'ASSET', 0),
            ('1200', 'BANK_CURRENT', 'ASSET', 0),
            ('2100', 'CUSTOMER_DEPOSITS', 'LIABILITY', 0),
            ('3100', 'CAPITAL', 'EQUITY', 1000000),
            ('4100', 'INTEREST_INCOME', 'INCOME', 0),
            ('5100', 'GENERAL_EXPENSE', 'EXPENSE', 0),
            ('5500', 'CONVEYANCE_EXPENSE', 'EXPENSE', 0),
            ('5600', 'TRAVEL_EXPENSE', 'EXPENSE', 0),
            ('5900', 'ADVERTISING_EXPENSE', 'EXPENSE', 0),
            ('5999', 'SB_INTEREST_EXPENSE', 'EXPENSE', 0),
            ('2500', 'SB_INTEREST_PAYABLE', 'LIABILITY', 0),
        ]
        for acc in accounts:
            c.execute("INSERT INTO accounts (code, name, type, balance) VALUES (?, ?, ?, ?)", acc)
    
    conn.commit()
    conn.close()

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def verify_user(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hash_password(password)))
    user = c.fetchone()
    conn.close()
    if user:
        return {'id': user[0], 'username': user[1], 'full_name': user[3], 'role': user[4]}
    return None

# ============== ACCOUNT FUNCTIONS ==============
def get_accounts():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT code, name, type, balance FROM accounts ORDER BY code")
    result = c.fetchall()
    conn.close()
    accounts = {}
    for row in result:
        accounts[row[0]] = {'code': row[0], 'name': row[1], 'type': row[2], 'balance': row[3]}
    return accounts

def update_balance(code, amount, is_debit=True):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT type, balance FROM accounts WHERE code=?", (code,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, "Account not found"
    
    acc_type, current = row
    if acc_type in ['ASSET', 'EXPENSE']:
        new_balance = current + amount if is_debit else current - amount
    else:
        new_balance = current - amount if is_debit else current + amount
    
    c.execute("UPDATE accounts SET balance=? WHERE code=?", (new_balance, code))
    conn.commit()
    conn.close()
    return True, new_balance

def get_balance(code):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT balance FROM accounts WHERE code=?", (code,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

# ============== VOUCHER FUNCTIONS ==============
def save_voucher(voucher_type, date, description, entries, username):
    conn = get_db()
    c = conn.cursor()
    
    voucher_no = f"{voucher_type[:3]}-{datetime.now().strftime('%Y%m%d')}-{str(int(time.time()))[-6:]}"
    total = sum(e['amount'] for e in entries)
    
    c.execute("INSERT INTO vouchers (voucher_no, voucher_type, date, description, total_amount) VALUES (?, ?, ?, ?, ?)",
             (voucher_no, voucher_type, date, description, total))
    
    for e in entries:
        c.execute("INSERT INTO journal_entries (date, account_code, account_name, entry_type, amount, description, voucher_no) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (date, e['code'], e['name'], e['type'], e['amount'], description, voucher_no))
        
        if e['type'] == 'DEBIT':
            update_balance(e['code'], e['amount'], True)
        else:
            update_balance(e['code'], e['amount'], False)
    
    conn.commit()
    conn.close()
    return True, f"Voucher {voucher_no} saved"

def get_vouchers():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT voucher_no, voucher_type, date, description, total_amount FROM vouchers ORDER BY date DESC LIMIT 100")
    result = c.fetchall()
    conn.close()
    return result

def delete_voucher(voucher_no):
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT entry_type, account_code, amount FROM journal_entries WHERE voucher_no=?", (voucher_no,))
    entries = c.fetchall()
    for e in entries:
        if e[0] == 'DEBIT':
            update_balance(e[1], e[2], False)
        else:
            update_balance(e[1], e[2], True)
    
    c.execute("DELETE FROM journal_entries WHERE voucher_no=?", (voucher_no,))
    c.execute("DELETE FROM vouchers WHERE voucher_no=?", (voucher_no,))
    conn.commit()
    conn.close()
    return True, "Voucher deleted"

# ============== SB ACCOUNT FUNCTIONS ==============
def create_sb_account(customer_name, balance, rate):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM sb_accounts")
    count = c.fetchone()[0] + 1
    acc_no = f"SB{datetime.now().strftime('%Y%m')}{str(count).zfill(6)}"
    
    c.execute("INSERT INTO sb_accounts (account_number, customer_name, balance, interest_rate, opening_date) VALUES (?, ?, ?, ?, ?)",
             (acc_no, customer_name, balance, rate, datetime.now().strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()
    return acc_no

def get_sb_accounts():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT account_number, customer_name, balance, interest_rate, interest_payable, status FROM sb_accounts")
    result = c.fetchall()
    conn.close()
    return result

def get_sb_transactions(acc_no):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT date, particulars, debit, credit, balance, type FROM sb_transactions WHERE account_number=? ORDER BY date DESC LIMIT 50", (acc_no,))
    result = c.fetchall()
    conn.close()
    return result

def deposit_sb(acc_no, amount, particulars):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT balance FROM sb_accounts WHERE account_number=?", (acc_no,))
    current = c.fetchone()[0]
    new_balance = current + amount
    c.execute("UPDATE sb_accounts SET balance=? WHERE account_number=?", (new_balance, acc_no))
    c.execute("INSERT INTO sb_transactions (account_number, date, particulars, credit, balance, type) VALUES (?, ?, ?, ?, ?, ?)",
             (acc_no, datetime.now().strftime('%Y-%m-%d'), particulars, amount, new_balance, 'DEPOSIT'))
    conn.commit()
    conn.close()
    return True, f"Deposited ₹{amount:,.2f}"

def withdraw_sb(acc_no, amount, particulars):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT balance FROM sb_accounts WHERE account_number=?", (acc_no,))
    current = c.fetchone()[0]
    if current < amount:
        conn.close()
        return False, "Insufficient balance"
    new_balance = current - amount
    c.execute("UPDATE sb_accounts SET balance=? WHERE account_number=?", (new_balance, acc_no))
    c.execute("INSERT INTO sb_transactions (account_number, date, particulars, debit, balance, type) VALUES (?, ?, ?, ?, ?, ?)",
             (acc_no, datetime.now().strftime('%Y-%m-%d'), particulars, amount, new_balance, 'WITHDRAWAL'))
    conn.commit()
    conn.close()
    return True, f"Withdrawn ₹{amount:,.2f}"

def credit_interest(acc_no):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT balance, interest_rate, customer_name FROM sb_accounts WHERE account_number=?", (acc_no,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, "Account not found"
    
    balance, rate, name = row
    interest = balance * (rate / 100) * (90 / 365)
    if interest <= 0:
        conn.close()
        return False, "No interest to credit"
    
    # Update SB account
    new_balance = balance + interest
    c.execute("UPDATE sb_accounts SET balance=?, interest_payable=interest_payable+? WHERE account_number=?", 
             (new_balance, interest, acc_no))
    
    # Record SB transaction
    c.execute("INSERT INTO sb_transactions (account_number, date, particulars, credit, balance, type) VALUES (?, ?, ?, ?, ?, ?)",
             (acc_no, datetime.now().strftime('%Y-%m-%d'), f'Interest @ {rate}%', interest, new_balance, 'INTEREST'))
    
    # DOUBLE ENTRY: Dr SB Interest Expense, Cr SB Interest Payable
    voucher_no = f"INT-{datetime.now().strftime('%Y%m%d')}-{str(int(time.time()))[-6:]}"
    
    # Debit SB Interest Expense
    c.execute("INSERT INTO journal_entries (date, account_code, account_name, entry_type, amount, description, voucher_no) VALUES (?, ?, ?, ?, ?, ?, ?)",
             (datetime.now().strftime('%Y-%m-%d'), '5999', 'SB_INTEREST_EXPENSE', 'DEBIT', interest, f'Interest on {acc_no} - {name}', voucher_no))
    update_balance('5999', interest, True)
    
    # Credit SB Interest Payable
    c.execute("INSERT INTO journal_entries (date, account_code, account_name, entry_type, amount, description, voucher_no) VALUES (?, ?, ?, ?, ?, ?, ?)",
             (datetime.now().strftime('%Y-%m-%d'), '2500', 'SB_INTEREST_PAYABLE', 'CREDIT', interest, f'Interest on {acc_no} - {name}', voucher_no))
    update_balance('2500', interest, False)
    
    conn.commit()
    conn.close()
    return True, f"Interest ₹{interest:,.2f} credited"

# ============== TRIAL BALANCE ==============
def get_trial_balance():
    accounts = get_accounts()
    tb = []
    total_debits = 0
    total_credits = 0
    for code, data in accounts.items():
        balance = data['balance']
        if data['type'] in ['ASSET', 'EXPENSE']:
            tb.append({'Code': code, 'Name': data['name'], 'Type': data['type'], 'Debit': balance, 'Credit': 0})
            total_debits += balance
        else:
            tb.append({'Code': code, 'Name': data['name'], 'Type': data['type'], 'Debit': 0, 'Credit': balance})
            total_credits += balance
    return pd.DataFrame(tb), total_debits, total_credits

def get_balance_sheet():
    accounts = get_accounts()
    assets = {}
    liabilities = {}
    equity = {}
    for code, data in accounts.items():
        if data['type'] == 'ASSET':
            assets[data['name']] = data['balance']
        elif data['type'] == 'LIABILITY':
            liabilities[data['name']] = data['balance']
        elif data['type'] == 'EQUITY':
            equity[data['name']] = data['balance']
    return assets, liabilities, equity

def get_profit_loss():
    accounts = get_accounts()
    income = {}
    expenses = {}
    for code, data in accounts.items():
        if data['type'] == 'INCOME':
            income[data['name']] = data['balance']
        elif data['type'] == 'EXPENSE':
            expenses[data['name']] = data['balance']
    return income, expenses

# ============== UI ==============
def login_page():
    st.title("🏦 Complete Banking System")
    st.subheader("🔐 Login")
    
    if not os.path.exists(DB_FILE):
        init_db()
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            user = verify_user(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid credentials")

def display_account_card(code, icon, color):
    accounts = get_accounts()
    if code not in accounts:
        return
    data = accounts[code]
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {color}20, {color}05); padding: 12px; border-radius: 8px; border-left: 4px solid {color}; margin-bottom: 6px;">
        <div style="display: flex; justify-content: space-between;">
            <span style="font-size: 11px; color: #888;">{code}</span>
            <span style="font-size: 11px; color: #888;">{icon}</span>
        </div>
        <div style="font-size: 13px; font-weight: 500;">{data['name'].replace('_', ' ').title()}</div>
        <div style="font-size: 18px; font-weight: bold;">₹{data['balance']:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

def main():
    try:
        if not os.path.exists(DB_FILE):
            init_db()
        
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
                st.session_state.logged_in = False
                st.rerun()
        
        st.divider()
        
        # Sidebar
        with st.sidebar:
            st.header("📊 Account Overview")
            display_account_card('1000', '💵', '#00A86B')
            display_account_card('1100', '🏦', '#2E86AB')
            display_account_card('1200', '🏦', '#1B4F72')
            st.divider()
            with st.expander("🏦 Other ASSETS"):
                for code in ['1300', '1400']:
                    display_account_card(code, '💰', '#2E86AB')
            with st.expander("🏛️ LIABILITIES"):
                for code in ['2100', '2200', '2500']:
                    display_account_card(code, '🏛️', '#A23B72')
            with st.expander("📈 EQUITY"):
                for code in ['3100', '3200']:
                    display_account_card(code, '📈', '#F18F01')
            with st.expander("📊 INCOME"):
                for code in ['4100', '4200', '4300', '4400']:
                    display_account_card(code, '📊', '#1B998B')
            with st.expander("📉 EXPENSES"):
                for code in ['5100', '5500', '5600', '5900', '5999']:
                    display_account_card(code, '📉', '#D65D5D')
        
        # Tabs
        tabs = ["📝 Journal Vouchers", "🏦 SB Accounts", "📊 Reports", "📋 Trial Balance"]
        tab1, tab2, tab3, tab4 = st.tabs(tabs)
        
        # TAB 1: Journal Vouchers
        with tab1:
            st.header("📝 Journal Vouchers")
            
            vtab1, vtab2 = st.tabs(["➕ Create", "📋 View/Delete"])
            
            with vtab1:
                st.subheader("Create Journal Voucher")
                accounts = get_accounts()
                acc_options = [f"{data['name']} ({code})" for code, data in accounts.items()]
                acc_map = {f"{data['name']} ({code})": code for code, data in accounts.items()}
                
                with st.form("voucher_form"):
                    date = st.date_input("Date", value=datetime.now().date())
                    desc = st.text_input("Description")
                    voucher_type = st.selectbox("Type", ['JOURNAL', 'RECEIPT', 'PAYMENT', 'CONTRA'])
                    
                    entries = []
                    num = st.number_input("Number of entries", min_value=2, max_value=6, value=2, step=1)
                    
                    for i in range(num):
                        st.markdown(f"**Entry {i+1}**")
                        col1, col2, col3 = st.columns([1, 2, 1.5])
                        with col1:
                            entry_type = st.selectbox(f"Type", ['DEBIT', 'CREDIT'], key=f"type_{i}")
                        with col2:
                            acc = st.selectbox(f"Account", acc_options, key=f"acc_{i}")
                        with col3:
                            amt = st.number_input(f"Amount", min_value=0.0, step=100.0, key=f"amt_{i}")
                        
                        if acc and amt > 0:
                            entries.append({
                                'code': acc_map[acc],
                                'name': acc.split('(')[0].strip(),
                                'type': entry_type,
                                'amount': amt
                            })
                    
                    if st.form_submit_button("💾 Save Voucher"):
                        if not entries:
                            st.error("Please add at least one entry")
                        else:
                            debits = sum(e['amount'] for e in entries if e['type'] == 'DEBIT')
                            credits = sum(e['amount'] for e in entries if e['type'] == 'CREDIT')
                            if debits != credits:
                                st.error(f"Debits ({debits}) must equal Credits ({credits})")
                            else:
                                success, msg = save_voucher(voucher_type, date.strftime('%Y-%m-%d'), desc, entries, user['username'])
                                st.success(msg) if success else st.error(msg)
                                if success:
                                    st.rerun()
            
            with vtab2:
                st.subheader("View/Delete Vouchers")
                vouchers = get_vouchers()
                if not vouchers:
                    st.info("No vouchers found")
                else:
                    df = pd.DataFrame(vouchers, columns=['Voucher No', 'Type', 'Date', 'Description', 'Amount'])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    selected = st.selectbox("Select voucher to delete", [""] + [v[0] for v in vouchers])
                    if selected and st.button("🗑️ Delete"):
                        success, msg = delete_voucher(selected)
                        st.success(msg) if success else st.error(msg)
                        if success:
                            st.rerun()
        
        # TAB 2: SB Accounts
        with tab2:
            st.header("🏦 Savings Bank Accounts")
            
            sbtab1, sbtab2, sbtab3 = st.tabs(["🏦 Create", "💰 Operations", "📊 Reports"])
            
            with sbtab1:
                st.subheader("Create SB Account")
                with st.form("sb_create"):
                    name = st.text_input("Customer Name*")
                    balance = st.number_input("Opening Balance", min_value=0.0, step=100.0)
                    rate = st.number_input("Interest Rate (%)", min_value=0.0, max_value=20.0, step=0.1, value=3.5)
                    if st.form_submit_button("Create"):
                        if name:
                            acc_no = create_sb_account(name, balance, rate)
                            st.success(f"Account {acc_no} created for {name}")
                        else:
                            st.error("Customer name required")
            
            with sbtab2:
                st.subheader("Account Operations")
                accounts = get_sb_accounts()
                if not accounts:
                    st.warning("No SB accounts found")
                else:
                    acc_options = [f"{a[0]} - {a[1]} (₹{a[2]:,.2f})" for a in accounts if a[5] == 'ACTIVE']
                    if not acc_options:
                        st.warning("No active accounts")
                    else:
                        selected = st.selectbox("Select Account", acc_options)
                        if selected:
                            acc_no = selected.split(' - ')[0]
                            acc = next(a for a in accounts if a[0] == acc_no)
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Balance", f"₹{acc[2]:,.2f}")
                            with col2:
                                st.metric("Rate", f"{acc[3]}%")
                            with col3:
                                st.metric("Interest Payable", f"₹{acc[4]:,.2f}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("### Deposit")
                                amt = st.number_input("Amount", min_value=0.0, step=100.0, key="dep_amt")
                                part = st.text_input("Particulars", key="dep_part", placeholder="Deposit")
                                if st.button("💰 Deposit", key="dep_btn"):
                                    if amt > 0:
                                        success, msg = deposit_sb(acc_no, amt, part or "Deposit")
                                        st.success(msg) if success else st.error(msg)
                                        if success:
                                            st.rerun()
                            
                            with col2:
                                st.markdown("### Withdraw")
                                amt2 = st.number_input("Amount", min_value=0.0, step=100.0, key="wd_amt")
                                part2 = st.text_input("Particulars", key="wd_part", placeholder="Withdrawal")
                                if st.button("💸 Withdraw", key="wd_btn"):
                                    if amt2 > 0:
                                        success, msg = withdraw_sb(acc_no, amt2, part2 or "Withdrawal")
                                        st.success(msg) if success else st.error(msg)
                                        if success:
                                            st.rerun()
                            
                            st.divider()
                            st.markdown("### Interest")
                            if st.button("🧮 Credit Interest"):
                                success, msg = credit_interest(acc_no)
                                st.success(msg) if success else st.error(msg)
                                if success:
                                    st.rerun()
            
            with sbtab3:
                st.subheader("SB Account Report")
                accounts = get_sb_accounts()
                if not accounts:
                    st.warning("No SB accounts found")
                else:
                    selected = st.selectbox("Select Account", [f"{a[0]} - {a[1]}" for a in accounts])
                    if selected:
                        acc_no = selected.split(' - ')[0]
                        acc = next(a for a in accounts if a[0] == acc_no)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Account", acc_no)
                            st.metric("Customer", acc[1])
                        with col2:
                            st.metric("Balance", f"₹{acc[2]:,.2f}")
                            st.metric("Interest Rate", f"{acc[3]}%")
                        
                        st.markdown("### Transactions")
                        txns = get_sb_transactions(acc_no)
                        if txns:
                            df = pd.DataFrame(txns, columns=['Date', 'Particulars', 'Debit', 'Credit', 'Balance', 'Type'])
                            st.dataframe(df, use_container_width=True, hide_index=True)
                        else:
                            st.info("No transactions")
        
        # TAB 3: Reports
        with tab3:
            st.header("📊 Financial Reports")
            
            report_type = st.radio("Select Report", ["Balance Sheet", "Profit & Loss"], horizontal=True)
            
            if report_type == "Balance Sheet":
                assets, liabilities, equity = get_balance_sheet()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### ASSETS")
                    for name, bal in assets.items():
                        st.metric(name.replace('_', ' ').title(), f"₹{bal:,.2f}")
                    total_assets = sum(assets.values())
                    st.markdown(f"### **Total Assets: ₹{total_assets:,.2f}**")
                    
                    st.markdown("### LIABILITIES")
                    for name, bal in liabilities.items():
                        st.metric(name.replace('_', ' ').title(), f"₹{bal:,.2f}")
                    total_liab = sum(liabilities.values())
                    st.markdown(f"### **Total Liabilities: ₹{total_liab:,.2f}**")
                
                with col2:
                    st.markdown("### EQUITY")
                    for name, bal in equity.items():
                        st.metric(name.replace('_', ' ').title(), f"₹{bal:,.2f}")
                    total_eq = sum(equity.values())
                    st.markdown(f"### **Total Equity: ₹{total_eq:,.2f}**")
                    
                    st.divider()
                    total = total_liab + total_eq
                    if abs(total_assets - total) < 0.01:
                        st.success(f"✅ Balanced: ₹{total_assets:,.2f} = ₹{total:,.2f}")
                    else:
                        st.error(f"❌ Difference: ₹{total_assets - total:,.2f}")
            
            else:
                income, expenses = get_profit_loss()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### INCOME")
                    for name, bal in income.items():
                        st.metric(name.replace('_', ' ').title(), f"₹{bal:,.2f}")
                    total_income = sum(income.values())
                    st.markdown(f"### **Total Income: ₹{total_income:,.2f}**")
                
                with col2:
                    st.markdown("### EXPENSES")
                    for name, bal in expenses.items():
                        st.metric(name.replace('_', ' ').title(), f"₹{bal:,.2f}")
                    total_exp = sum(expenses.values())
                    st.markdown(f"### **Total Expenses: ₹{total_exp:,.2f}**")
                
                st.divider()
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Income", f"₹{total_income:,.2f}")
                with col2:
                    st.metric("Total Expenses", f"₹{total_exp:,.2f}")
                with col3:
                    profit = total_income - total_exp
                    if profit >= 0:
                        st.success(f"NET PROFIT: ₹{profit:,.2f} 🎉")
                    else:
                        st.error(f"NET LOSS: ₹{abs(profit):,.2f}")
        
        # TAB 4: Trial Balance
        with tab4:
            st.header("📋 Trial Balance")
            tb_df, debits, credits = get_trial_balance()
            if not tb_df.empty:
                st.dataframe(tb_df, use_container_width=True, hide_index=True)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Debits", f"₹{debits:,.2f}")
                with col2:
                    st.metric("Total Credits", f"₹{credits:,.2f}")
                with col3:
                    if abs(debits - credits) < 0.01:
                        st.success("✅ Balanced!")
                    else:
                        st.error(f"❌ Difference: ₹{debits - credits:,.2f}")
            else:
                st.info("No accounts")
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
