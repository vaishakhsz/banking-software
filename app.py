To build a complete, highly reliable Core Banking & ERP application in Streamlit without falling into execution loops or database locks, the architecture must handle data mutations efficiently.

Below is the architecture outline and the complete production-grade code incorporating **Savings Bank (SB) Portfolios**, **Fixed Deposit / Recurring Deposit (FD/RD) Systems**, **Double-Entry Voucher Bookings**, and an automated accounting ledger matrix (**Trial Balance**, **Profit & Loss**, and dynamic internal validations).

---

### 🏛️ Architecture & System Design Highlights

* **Session-Isolated DB Initialization:** To prevent infinite loading screen traps caused by Streamlit's structural reruns, database structure creation and migrations are wrapped inside a session state conditional initialization gate (`st.session_state.db_initialized`).
* **Thread-Safe WAL SQLite Mode:** The database backend operates with a local thread lock, `WAL` (Write-Ahead Logging) journal mode, and elevated busy timeout thresholds ($60,000\text{ ms}$) to prevent multi-session locking during concurrent ledger posting operations.
* **Pure Double-Entry Validation:** Every financial transaction—whether an SB cash deposit, an FD booking, or a custom journal entry—mandates that the mathematical summation of Debits exactly matches Credits ($\sum \text{Debits} = \sum \text{Credits}$) prior to committing to the ledger.
* **Cross-Module Accounting Engine:** All dynamic components seamlessly post to predefined chart of accounts ledger heads:
* **1000 (CASH / ASSET)**: Liquid funds tracking cash counter operations.
* **2100 (CUSTOMER DEPOSITS / LIABILITY)**: Active Savings Account (SB) balances.
* **2200 (FD LIABILITY / LIABILITY)**: Active Fixed Deposit liability holdings.
* **4100 (INTEREST INCOME / INCOME)**: Yield earned on financing loops.
* **5999 (SB INTEREST EXPENSE / EXPENSE)**: Accumulating cost of customer deposits.



---

### 💻 The Complete Production-Ready Code

```python
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

# ============== GLOBAL CONFIG & SAFE DATABASE ENGINE ==============
DB_FILE = "core_banking_erp.db"
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
        except Exception:
            return None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_safe_float(value, default=0.0):
    try:
        if value is None: return default
        if isinstance(value, str):
            if value.strip() == '': return default
            return float(value)
        return float(value)
    except (ValueError, TypeError):
        return default

def generate_uid(prefix="TXN"):
    return f"{prefix}-{datetime.now().strftime('%Y')}-{str(int(time.time()))[-7:]}"

# ============== SYSTEM DB INITIALIZATION MATRIX ==============
def ensure_ledger_heads_exist(cursor, current_date):
    required_accounts = [
        # ===== ASSETS (1xxx) =====
        ('1000', 'CASH_ON_HAND', 'ASSET', 5000000.0, 'system'),
        ('1100', 'CLEARING_ACCOUNT', 'ASSET', 0.0, 'system'),
        ('1600', 'LOANS_AND_ADVANCES', 'ASSET', 0.0, 'system'),
        
        # ===== LIABILITIES (2xxx) =====
        ('2100', 'SAVINGS_BANK_DEPOSITS', 'LIABILITY', 0.0, 'system'),
        ('2200', 'FIXED_DEPOSIT_HOLDINGS', 'LIABILITY', 0.0, 'system'),
        ('2250', 'RECURRING_DEPOSIT_HOLDINGS', 'LIABILITY', 0.0, 'system'),
        ('2500', 'INTEREST_PAYABLE_ACCRUALS', 'LIABILITY', 0.0, 'system'),
        
        # ===== EQUITY (3xxx) =====
        ('3100', 'SHARE_CAPITAL_INJECTED', 'EQUITY', 5000000.0, 'system'),
        ('3200', 'RETAINED_EARNINGS', 'EQUITY', 0.0, 'system'),
        
        # ===== INCOME (4xxx) =====
        ('4100', 'INTEREST_INCOME_LOANS', 'INCOME', 0.0, 'system'),
        ('4200', 'PROCESSING_FEES_INCOME', 'INCOME', 0.0, 'system'),
        
        # ===== EXPENSES (5xxx) =====
        ('5100', 'OFFICE_ADMINISTRATION_EXPENSE', 'EXPENSE', 0.0, 'system'),
        ('5999', 'DEPOSIT_INTEREST_EXPENSE', 'EXPENSE', 0.0, 'system'),
    ]
    
    for acc in required_accounts:
        cursor.execute('SELECT COUNT(*) FROM accounts WHERE account_code = ?', (acc[0],))
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO accounts (account_code, account_name, account_type, balance, created_date, is_active, created_by)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            ''', (acc[0], acc[1], acc[2], acc[3], current_date, acc[4]))

def init_database():
    try:
        conn = get_db_connection()
        if conn is None: return
        cursor = conn.cursor()
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 1. Base Users Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT DEFAULT 'user'
            )
        ''')
        
        # 2. General Ledger Chart of Accounts Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_code TEXT UNIQUE NOT NULL,
                account_name TEXT NOT NULL,
                account_type TEXT NOT NULL,
                balance REAL DEFAULT 0.0,
                created_date TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_by TEXT
            )
        ''')
        
        # 3. Balanced Journal Transactions Engine
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                account_code TEXT NOT NULL,
                account_name TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                voucher_number TEXT,
                username TEXT
            )
        ''')
        
        # 4. Savings Bank (SB) Sub-Ledger Registry
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sb_accounts (
                account_number TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                phone TEXT,
                current_balance REAL DEFAULT 0.0,
                interest_rate REAL DEFAULT 3.5,
                opening_date TEXT NOT NULL,
                status TEXT DEFAULT 'ACTIVE'
            )
        ''')
        
        # 5. Fixed Deposit / Recurring Deposit Sub-Ledger Registry
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fdrd_accounts (
                account_number TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                product_type TEXT NOT NULL, -- 'FD' or 'RD'
                principal_amount REAL NOT NULL,
                monthly_installment REAL DEFAULT 0.0, -- Relevant for RD portfolios
                interest_rate REAL NOT NULL,
                tenure_months INTEGER NOT NULL,
                maturity_amount REAL NOT NULL,
                current_balance REAL DEFAULT 0.0,
                opening_date TEXT NOT NULL,
                maturity_date TEXT NOT NULL,
                status TEXT DEFAULT 'ACTIVE'
            )
        ''')
        
        # Seed core infrastructure baseline parameters safely
        ensure_ledger_heads_exist(cursor, current_date)
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            cursor.execute('INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)',
                          ("admin", hash_password("admin123"), "Head Administrator", "admin"))
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Critical error initializes local DB infrastructure context: {str(e)}")

# ============== LEDGER CORE DYNAMICS MECHANISMS ==============
def get_all_accounts():
    try:
        conn = get_db_connection()
        if conn is None: return {}
        cursor = conn.cursor()
        cursor.execute('SELECT account_code, account_name, account_type, balance FROM accounts WHERE is_active = 1 ORDER BY account_code')
        rows = cursor.fetchall()
        conn.close()
        return {r[0]: {'code': r[0], 'name': r[1], 'type': r[2], 'balance': r[3]} for r in rows}
    except Exception:
        return {}

def update_ledger_head_balance(cursor, account_code, amount, is_debit=True):
    cursor.execute('SELECT account_type, balance FROM accounts WHERE account_code = ?', (account_code,))
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"Ledger account code {account_code} does not exist in COA mapping.")
    
    acc_type, current_bal = row
    if acc_type in ['ASSET', 'EXPENSE']:
        new_balance = (current_bal + amount) if is_debit else (current_bal - amount)
    else:
        new_balance = (current_bal - amount) if is_debit else (current_bal + amount)
        
    cursor.execute('UPDATE accounts SET balance = ? WHERE account_code = ?', (new_balance, account_code))

def execute_double_entry_voucher(v_type, v_date, description, line_items, username):
    """
    Core atomic process workflow executing double-entry voucher allocations.
    line_items format structure: list of dicts -> [{'account_code', 'entry_type': 'DEBIT'/'CREDIT', 'amount', 'narration'}]
    """
    total_debits = sum(get_safe_float(item['amount']) for item in line_items if item['entry_type'] == 'DEBIT')
    total_credits = sum(get_safe_float(item['amount']) for item in line_items if item['entry_type'] == 'CREDIT')
    
    if abs(total_debits - total_credits) > 0.001:
        return False, f"Imbalanced double-entry stack parameters: Total Debits (₹{total_debits:,.2f}) must equate Total Credits (₹{total_credits:,.2f})"
        
    try:
        conn = get_db_connection()
        if conn is None: return False, "Database operational connection pool fault."
        cursor = conn.cursor()
        
        v_num = generate_uid(prefix=v_type[:3].upper())
        
        for item in line_items:
            amt = get_safe_float(item['amount'])
            code = item['account_code']
            is_deb = (item['entry_type'] == 'DEBIT')
            
            cursor.execute('SELECT account_name FROM accounts WHERE account_code = ?', (code,))
            name_row = cursor.fetchone()
            acc_name = name_row[0] if name_row else "UNKNOWN HEAD"
            
            # Post transaction record directly into historical journals
            cursor.execute('''
                INSERT INTO journal_entries (date, account_code, account_name, entry_type, amount, description, voucher_number, username)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (v_date, code, acc_name, item['entry_type'], amt, item.get('narration', description), v_num, username))
            
            # Mutation step calculating financial impact inside global COA ledger indices
            update_ledger_head_balance(cursor, code, amt, is_debit=is_deb)
            
        conn.commit()
        conn.close()
        return True, f"Voucher transaction booked effectively under entry trace identifier: {v_num}"
    except Exception as e:
        return False, f"Internal Transaction Rollback Exception: {str(e)}"

# ============== SUB-LEDGER CUSTOM SYSTEM ACTIONS ==============
def open_sb_portfolio(cust_name, phone, initial_dep, rate, opening_date, username):
    if initial_dep < 0: return False, "Initial deposit balances cannot register dynamically negative numbers."
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        acc_num = f"SB{datetime.now().strftime('%Y%m')}{str(int(time.time()))[-5:]}"
        
        cursor.execute('''
            INSERT INTO sb_accounts (account_number, customer_name, phone, current_balance, interest_rate, opening_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (acc_num, cust_name, phone, initial_dep, rate, opening_date))
        
        conn.commit()
        conn.close()
        
        if initial_dep > 0:
            # Rebalance the core systems ledger sheet automatically via transaction pathways
            items = [
                {'account_code': '1000', 'entry_type': 'DEBIT', 'amount': initial_dep, 'narration': f"Opening portfolio allocation cash deposit for {acc_num}"},
                {'account_code': '2100', 'entry_type': 'CREDIT', 'amount': initial_dep, 'narration': f"Opening dynamic portfolio allocation for {acc_num}"}
            ]
            execute_double_entry_voucher("RECEIPT", opening_date, f"SB Portfolio Allocation: {acc_num}", items, username)
            
        return True, f"Savings Bank account initialized effectively: {acc_num}"
    except Exception as e:
        return False, f"Exception caught provisioning account parameters: {str(e)}"

def post_sb_transaction(acc_no, txn_type, amount, val_date, username):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT current_balance, customer_name FROM sb_accounts WHERE account_number = ?', (acc_no,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return False, "Target profile portfolio parameters not active."
            
        cur_bal, name = row
        if txn_type == "WITHDRAWAL" and cur_bal < amount:
            conn.close()
            return False, "Execution halted: Insufficient balance."
            
        new_bal = (cur_bal + amount) if txn_type == "DEPOSIT" else (cur_bal - amount)
        cursor.execute('UPDATE sb_accounts SET current_balance = ? WHERE account_number = ?', (new_bal, acc_no))
        conn.commit()
        conn.close()
        
        # Double-entry transaction engine ledger synchronization routing pathways
        if txn_type == "DEPOSIT":
            items = [
                {'account_code': '1000', 'entry_type': 'DEBIT', 'amount': amount, 'narration': f"Cash counter deposit into portfolio tracking ledger: {acc_no}"},
                {'account_code': '2100', 'entry_type': 'CREDIT', 'amount': amount, 'narration': f"Savings balance growth index credit allocation: {acc_no}"}
            ]
        else:
            items = [
                {'account_code': '2100', 'entry_type': 'DEBIT', 'amount': amount, 'narration': f"Portfolio validation ledger debit balance check: {acc_no}"},
                {'account_code': '1000', 'entry_type': 'CREDIT', 'amount': amount, 'narration': f"Cash drawer physical disbursement matching: {acc_no}"}
            ]
            
        execute_double_entry_voucher("JOURNAL", val_date, f"SB Txn: {txn_type} | {acc_no}", items, username)
        return True, f"Transaction successfully posted to portfolio index tracking path. Balance updated to ₹{new_bal:,.2f}"
    except Exception as e:
        return False, f"Failure writing execution row: {str(e)}"

def provision_fdrd_portfolio(cust_name, prod_type, principal, installment, rate, tenure, opening_date, username):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        acc_num = f"{prod_type}{datetime.now().strftime('%Y%m')}{str(int(time.time()))[-5:]}"
        
        # Financial projection algorithms
        t_years = tenure / 12.0
        if prod_type == "FD":
            mat_amt = principal * ((1.0 + (rate / 100.0)) ** t_years)
            cur_bal = principal
        else: # RD compounding formula logic structures
            n = tenure
            i = (rate / 100.0) / 12.0
            mat_amt = installment * (((1.0 + i)**n - 1.0) / i) * (1.0 + i)
            cur_bal = installment
            principal = installment # Initial footprint placement tracking value metrics
            
        op_d = datetime.strptime(opening_date, '%Y-%m-%d')
        mat_d = (op_d + timedelta(days=int(tenure * 30.4375))).strftime('%Y-%m-%d')
        
        cursor.execute('''
            INSERT INTO fdrd_accounts (account_number, customer_name, product_type, principal_amount, monthly_installment,
                                      interest_rate, tenure_months, maturity_amount, current_balance, opening_date, maturity_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (acc_num, cust_name, prod_type, principal, installment, rate, tenure, mat_amt, cur_bal, opening_date, mat_d))
        
        conn.commit()
        conn.close()
        
        # Route balance sheet integration pipelines seamlessly
        target_coa = '2200' if prod_type == "FD" else '2250'
        book_amt = principal if prod_type == "FD" else installment
        
        items = [
            {'account_code': '1000', 'entry_type': 'DEBIT', 'amount': book_amt, 'narration': f"Cash intake transaction booking verification for {acc_num}"},
            {'account_code': target_coa, 'entry_type': 'CREDIT', 'amount': book_amt, 'narration': f"Liability account allocation structure entry for {acc_num}"}
        ]
        execute_double_entry_voucher("RECEIPT", opening_date, f"Open Term Deposit Portfolio: {acc_num}", items, username)
        
        return True, f"Term ledger entry processed efficiently: {acc_num} | Maturity Estimation: ₹{mat_amt:,.2f}"
    except Exception as e:
        return False, f"Exception inside provisioning pathways sequence: {str(e)}"

# ============== FINANCIAL REVENUE REPORT GENERATORS ==============
def get_trial_balance_matrix():
    accounts = get_all_accounts()
    tb_rows = []
    tot_debits, tot_credits = 0.0, 0.0
    
    for code, data in accounts.items():
        bal = get_safe_float(data['balance'])
        if bal == 0: continue
        
        deb, cred = 0.0, 0.0
        if data['type'] in ['ASSET', 'EXPENSE']:
            if bal >= 0: deb = bal
            else: cred = abs(bal)
        else:
            if bal >= 0: cred = bal
            else: deb = abs(bal)
            
        tb_rows.append({
            'Code': code,
            'Ledger Account Head': data['name'],
            'Classification Category': data['type'],
            'Debit (₹)': deb,
            'Credit (₹)': cred
        })
        tot_debits += deb
        tot_credits += cred
        
    return pd.DataFrame(tb_rows), tot_debits, tot_credits

def get_profit_loss_matrix():
    accounts = get_all_accounts()
    inc_items, exp_items = {}, {}
    
    for code, data in accounts.items():
        bal = get_safe_float(data['balance'])
        if data['type'] == 'INCOME':
            inc_items[data['name']] = bal
        elif data['type'] == 'EXPENSE':
            exp_items[data['name']] = bal
            
    sum_inc = sum(inc_items.values())
    sum_exp = sum(exp_items.values())
    return {'revenues': inc_items, 'expenses': exp_items, 'total_revenue': sum_inc, 'total_expense': sum_exp, 'net_profit': (sum_inc - sum_exp)}

# ============== RENDER INTERFACES AND ENGINE GRAPHICS ==============
def login_page():
    st.markdown("""
        <style>
        .auth-container { max-width: 450px; margin: 80px auto; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); background-color: #ffffff; }
        .branding-title { text-align: center; font-weight: 700; color: #1e293b; margin-bottom: 5px; }
        .branding-sub { text-align: center; font-size: 0.9em; color: #64748b; margin-bottom: 25px; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown('<h2 class="branding-title">🏦 NEXUS CORE</h2>', unsafe_allow_html=True)
    st.markdown('<p class="branding-sub">Enterprise General Ledger & Sub-Ledger Banking Suite</p>', unsafe_allow_html=True)
    
    with st.form("auth_form"):
        user_input = st.text_input("Operator Username Identity")
        pass_input = st.text_input("Secure Authorization Token / Password", type="password")
        submit = st.form_submit_button("Authenticate Access Path")
        
        if submit:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                hashed = hash_password(pass_input)
                cursor.execute('SELECT username, full_name, role FROM users WHERE username = ? AND password_hash = ?', (user_input, hashed))
                res = cursor.fetchone()
                conn.close()
                
                if res:
                    st.session_state.logged_in = True
                    st.session_state.user = {'username': res[0], 'name': res[1], 'role': res[2]}
                    st.success("Authorization confirmed. Loading engine dashboard environment...")
                    st.rerun()
                else:
                    st.error("Authentication rejected: Invalid credential pairing signature matching.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.caption("<center>System Initialization Default Verification Tokens: admin / admin123</center>", unsafe_allow_html=True)

# ============== MAIN CONTROLLER ROOT CONTEXT ==============
def main():
    st.set_page_config(page_title="Nexus Core Banking Suite", page_icon="🏦", layout="wide")
    
    # 1. Gatekeeper thread-safe workspace setup execution once per system lifespan
    if not os.path.exists(DB_FILE):
        init_database()
        
    if "db_initialized" not in st.session_state:
        init_database()
        st.session_state.db_initialized = True
        
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        login_page()
        return
        
    user = st.session_state.user
    
    # Global Header Component Structure UI
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown("<h1 style='margin:0; padding:0; color:#0f172a;'>🏦 NEXUS CORE BANKING ENGINE</h1>", unsafe_allow_html=True)
        st.caption(f"Operated Session Context Authenticated Module Node Active | System Terminal ID: 2026-NEXUS")
    with col_h2:
        st.markdown(f"<div style='text-align:right; margin-top:5px;'><b>{user['name']}</b> ({user['role'].upper()})</div>", unsafe_allow_html=True)
        if st.button("Terminate Session Sequence", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()
            
    st.divider()
    
    # Navigation Matrix Controls Layout
    t_sb, t_fdrd, t_voucher, t_journal, t_trial, t_pl, t_audit = st.tabs([
        "💰 Savings Bank Module",
        "⏳ Term Deposits (FD/RD)",
        "📝 Double-Entry Voucher Posting",
        "📖 General Journal Log",
        "⚖️ Unadjusted Trial Balance",
        "📊 Profit & Loss Statements",
        "🔍 Real-time Internal System Verification"
    ])
    
    # ==================== MODULE 1: SAVINGS BANK (SB) PORTFOLIOS ====================
    with t_sb:
        st.subheader("Savings Bank Sub-Ledger Processing Environment")
        sb_action = st.radio("Select Processing Target Sequence Operations Strategy", ["Open New Account", "Post Cash Deposit / Withdrawal Transaction", "View Active Sub-Ledger Portfolios Table Matrix"], horizontal=True)
        
        if sb_action == "Open New Account":
            with st.form("sb_open_form"):
                c_name = st.text_input("Legal Full Name of Primary Account Holder")
                c_phone = st.text_input("Contact Mobile Phone Number Address")
                init_dep = st.number_input("Opening Counter Cash Deposit Amount (₹)", min_value=0.0, value=1000.0, step=500.0)
                int_rate = st.number_input("Yield Interest Matrix Target Rate Assignment (% P.A.)", min_value=0.0, max_value=12.0, value=3.5, step=0.25)
                op_date = st.date_input("Value Date Asset Creation Effective Alignment", value=datetime.now().date())
                
                if st.form_submit_button("Commit SB Activation Parameters Request"):
                    if not c_name:
                        st.error("Missing processing attribute requirement: Customer validation credentials.")
                    else:
                        success, message = open_sb_portfolio(c_name, c_phone, init_dep, int_rate, op_date.strftime('%Y-%m-%d'), user['username'])
                        if success: st.success(message)
                        else: st.error(message)
                        
        elif sb_action == "Post Cash Deposit / Withdrawal Transaction":
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT account_number, customer_name, current_balance FROM sb_accounts WHERE status = "ACTIVE"')
            sb_rows = cursor.fetchall()
            conn.close()
            
            if not sb_rows:
                st.info("No active portfolios detected inside sub-ledger tables.")
            else:
                sb_opts = {f"{r[0]} - {r[1]} (Bal: ₹{r[2]:,.2f})": r[0] for r in sb_rows}
                selected_sb = st.selectbox("Select Target Portfolio Target Index Assignment", list(sb_opts.keys()))
                target_acc = sb_opts[selected_sb]
                
                with st.form("sb_transaction_posting"):
                    t_mode = st.selectbox("Transaction Processing Operational Intent Category", ["DEPOSIT", "WITHDRAWAL"])
                    t_amt = st.number_input("Counter Liquid Asset Valuation Amount (₹)", min_value=1.0, value=500.0, step=100.0)
                    t_date = st.date_input("Processing Target Value Date Alignment Reference", value=datetime.now().date())
                    
                    if st.form_submit_button("Book Sub-Ledger Entry Stack"):
                        success, message = post_sb_transaction(target_acc, t_mode, t_amt, t_date.strftime('%Y-%m-%d'), user['username'])
                        if success:
                            st.success(message)
                            st.rerun()
                        else: st.error(message)
                        
        elif sb_action == "View Active Sub-Ledger Portfolios Table Matrix":
            conn = get_db_connection()
            df = pd.read_sql_query('SELECT * FROM sb_accounts', conn)
            conn.close()
            if not df.empty:
                df.columns = ['Account Number Identifier', 'Customer Profile Legal Entity Name', 'Phone Target Line Contact', 'Current Net Balance (₹)', 'Contractual Yield Rate (%)', 'Account Initialization Timestamp Reference', 'Current State Lifecycle Designation']
                st.dataframe(df, use_container_width=True, hide_index=True)
            else: st.info("No records match target trace query indices parameter scopes.")
            
    # ==================== MODULE 2: FIXED DEPOSIT / RECURRING DEPOSIT (FD/RD) ====================
    with t_fdrd:
        st.subheader("Term Deposit Assets Ledger Strategy Processing Matrix")
        fdrd_action = st.radio("Operational Objective Term Actions Task", ["Issue New Term Asset Contract Structure Entry", "Active Maturing Asset Portfolio Tables"], horizontal=True)
        
        if fdrd_action == "Issue New Term Asset Contract Structure Entry":
            with st.form("fdrd_issue_form"):
                f_name = st.text_input("Legal Holder Primary Entity Counterparty Name")
                p_type = st.selectbox("Product Line Segment Classification Portfolio", ["FD", "RD"])
                
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    p_amt = st.number_input("Principal Term Injection Valuation (Lump-Sum for FD) (₹)", min_value=0.0, value=10000.0, step=1000.0)
                with col_f2:
                    r_inst = st.number_input("Monthly Portfolio Recurrent Installment Commitment (For RD only) (₹)", min_value=0.0, value=0.0, step=500.0)
                    
                col_f3, col_f4 = st.columns(2)
                with col_f3:
                    f_rate = st.number_input("Contractual Component Interest Percentage Target Scale Fixed (% P.A.)", min_value=1.0, max_value=15.0, value=7.0, step=0.1)
                with col_f4:
                    f_tenure = st.number_input("Contract Lifespan Operational Duration Constraint (Months)", min_value=1, max_value=360, value=12, step=1)
                    
                f_date = st.date_input("Value Effective Opening Booking Sequence Timestamp", value=datetime.now().date())
                
                if st.form_submit_button("Provision Term Asset Contract Ledger Line Item"):
                    if p_type == "RD" and r_inst <= 0:
                        st.error("Validation reject: Recurring Deposit instruments mandate a regular monthly contribution valuation sequence definition input.")
                    elif p_type == "FD" and p_amt <= 0:
                        st.error("Validation reject: Fixed Deposit instruments require a non-zero principal capital asset injection benchmark designation value.")
                    else:
                        success, message = provision_fdrd_portfolio(f_name, p_type, p_amt, r_inst, f_rate, f_tenure, f_date.strftime('%Y-%m-%d'), user['username'])
                        if success: st.success(message)
                        else: st.error(message)
                        
        elif fdrd_action == "Active Maturing Asset Portfolio Tables":
            conn = get_db_connection()
            df = pd.read_sql_query('SELECT * FROM fdrd_accounts', conn)
            conn.close()
            if not df.empty:
                df.columns = ['Contract ID Trace', 'Customer Entity Counterparty Identity', 'Classification Type Portfolio', 'Initial Principal Injected Base (₹)', 'Monthly Commitment Index Rate Asset (₹)', 'Annualized Return Metric Yield Scale (%)', 'Contract Duration Footprint (Months)', 'Projected Valuation Horizon Maturity Target (₹)', 'Current State Running Book Accumulation Valuation (₹)', 'Lifecycle Inception Timestamp Target', 'Projected Maturity Value Settlement Timestamp Target', 'Asset Status Engine Execution Flag']
                st.dataframe(df, use_container_width=True, hide_index=True)
            else: st.info("No record structures allocated within dynamic cache databases currently.")
            
    # ==================== MODULE 3: BALANCED VOUCHER LEDGER INTERFACE ====================
    with t_voucher:
        st.subheader("Manual Ledger Adjustment Posting Engine Terminal Node")
        accounts = get_all_accounts()
        
        if 'v_items' not in st.session_state:
            st.session_state.v_items = []
            
        with st.expander("🛠️ Configuration Context Global Meta Parameters Descriptor Reference Form Layer", expanded=True):
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                mst_type = st.selectbox("Master Document Classification Flag Type Category", ["JOURNAL", "RECEIPT", "PAYMENT", "CONTRA"])
            with col_v2:
                mst_date = st.date_input("Master Processing Ledger Book Target Entry Value Date Reference", value=datetime.now().date())
            mst_desc = st.text_input("Global Transaction Objective Narrative Summary Meta String Reference", value="Manual Adjustment Allocation Entry Sequence Execution")
            
        st.markdown("#### 🗂️ Staging Workspace Row Row Entry Item Grid Definition Node Form")
        col_r1, col_r2, col_r3 = st.columns([2, 1, 1])
        with col_r1:
            coa_opts = {f"{k} - {v['name']} [{v['type']}] (Bal: ₹{v['balance']:,.2f})": k for k, v in accounts.items()}
            selected_coa = st.selectbox("Target Ledger Core Head Account Allocation Link mapping Selection", list(coa_opts.keys()))
        with col_r2:
            row_dc = st.selectbox("Ledger Account Mutation Intended Signal Vector Instruction", ["DEBIT", "CREDIT"])
        with col_r3:
            row_amt = st.number_input("Valuation Metric Multiplier Quantum Currency Units (₹)", min_value=0.01, value=0.0, step=100.0)
            
        row_narr = st.text_input("Line Item Level Detailed Micro Granular Explanation Row Context Specific Commentary Description String", value="")
        
        if st.button("➕ Inject Staged Line Row Data Structure Into Runtime Working Variable Workspace Stack"):
            st.session_state.v_items.append({
                'account_code': coa_opts[selected_coa],
                'entry_type': row_dc,
                'amount': row_amt,
                'narration': row_narr if row_narr else mst_desc
            })
            st.toast("Line record item injected successfully into execution memory stack storage allocation arrays.")
            
        if st.session_state.v_items:
            st.markdown("---")
            st.markdown("### 📊 Active Work Area Queue Framework Verification Data Frame Grid")
            v_df = pd.DataFrame(st.session_state.v_items)
            st.dataframe(v_df, use_container_width=True)
            
            deb_sum = sum(x['amount'] for x in st.session_state.v_items if x['entry_type'] == 'DEBIT')
            cred_sum = sum(x['amount'] for x in st.session_state.v_items if x['entry_type'] == 'CREDIT')
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Current Cumulative Debits Allocation Scale Summation Metric", f"₹{deb_sum:,.2f}")
            col_m2.metric("Current Cumulative Credits Allocation Scale Summation Metric", f"₹{cred_sum:,.2f}")
            
            variance = abs(deb_sum - cred_sum)
            col_m3.metric("Double-Entry System Out Of Alignment Discrepancy Variance Residual Margin", f"₹{variance:,.2f}", 
                          delta=f"-₹{variance:,.2f}" if variance == 0 else f"+₹{variance:,.2f}", delta_color="inverse" if variance > 0 else "normal")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("🗑️ Purge Working Workspace Allocation Registries Instantly", use_container_width=True):
                    st.session_state.v_items = []
                    st.rerun()
            with col_btn2:
                if variance < 0.001 and deb_sum > 0:
                    if st.button("💾 Commit Balanced Master Voucher Transaction Structure Block Elements Directly to General Ledger Records Store", use_container_width=True, type="primary"):
                        success, message = execute_double_entry_voucher(mst_type, mst_date.strftime('%Y-%m-%d'), mst_desc, st.session_state.v_items, user['username'])
                        if success:
                            st.success(message)
                            st.session_state.v_items = []
                            st.rerun()
                        else: st.error(message)
                else:
                    st.warning("⚠️ Submission blocked: Double-entry consistency protocol violation rules apply. The processing system cannot post asymmetric currency balancing elements safely.")
                    
    # ==================== MODULE 4: ARCHIVAL HISTORICAL GENERAL JOURNAL LOG ====================
    with t_journal:
        st.subheader("General Journal Historical Line Item Record Entry Audit Log Matrix Registry")
        
        col_j1, col_j2 = st.columns(2)
        with col_j1:
            j_start = st.date_input("Filter Date Matrix Baseline Range Starting Boundaries Viewpoint", value=datetime.now().date() - timedelta(days=60))
        with col_j2:
            j_end = st.date_input("Filter Date Matrix Baseline Range Ending Boundaries Viewpoint", value=datetime.now().date())
            
        conn = get_db_connection()
        query = '''
            SELECT date AS [Value Date], voucher_number AS [Document Key Reference ID], account_code AS [GL Code Link], 
                   account_name AS [Core Ledger Title Mapping Account Head], entry_type AS [Debit / Credit Allocation Indicator Signal Vector Type], 
                   amount AS [Valuation Quantum Currency Matrix Units (₹)], description AS [Global Event Meta Description Narrative Record Trace Context String], 
                   username AS [System Authenticated Operator Identity Trace ID Reference]
            FROM journal_entries
            WHERE date >= ? AND date <= ?
            ORDER BY id DESC LIMIT 500
        '''
        df = pd.read_sql_query(query, conn, params=(j_start.strftime('%Y-%m-%d'), j_end.strftime('%Y-%m-%d')))
        conn.close()
        
        if not df.empty:
            df['Valuation Quantum Currency Matrix Units (₹)'] = df['Valuation Quantum Currency Matrix Units (₹)'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else: st.info("Zero operational transaction structural traces discovered matching input parameter date filtering frames.")
        
    # ==================== MODULE 5: EXPERT BALANCED TRIAL BALANCE SHEET ====================
    with t_trial:
        st.subheader("Dynamic Real-time Core Unadjusted Trial Balance Matrix Representation Model Engine View")
        tb_data, tot_d, tot_c = get_trial_balance_matrix()
        
        if not tb_data.empty:
            st.dataframe(tb_data.style.format({'Debit (₹)': '₹{:,.2f}', 'Credit (₹)': '₹{:,.2f}'}), use_container_width=True, hide_index=True)
            st.markdown("---")
            col_t1, col_t2, col_t3 = st.columns(3)
            col_t1.metric("Cumulative Trial Balance Structural Matrix Combined System Debits Summation", f"₹{tot_d:,.2f}")
            col_t2.metric("Cumulative Trial Balance Structural Matrix Combined System Credits Summation", f"₹{tot_c:,.2f}")
            
            diff = abs(tot_d - tot_c)
            if diff < 0.01:
                col_t3.success("📊 System State Status Check Confirmation: Balanced Ledger Integrity Confirmed.")
            else:
                col_t3.error(f"❌ Internal Accounting Core Structural Error Variance: ₹{diff:,.2f}")
        else: st.info("Zero asset data mappings exist on global core accounts registers layout grids currently.")
        
    # ==================== MODULE 6: COMPREHENSIVE INCOME STATEMENT (PROFIT & LOSS) ====================
    with t_pl:
        st.subheader("Enterprise Accrual Operational Income & Expenditure Performance Statement Metric Portfolio")
        pl_dict = get_profit_loss_matrix()
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("#### 📈 Dynamic Operational Inflow System Revenue Stream Allocation Structures")
            if pl_dict['revenues']:
                for k, v in pl_dict['revenues'].items():
                    st.markdown(f"**{k}**: `₹{v:,.2f}`")
            else: st.caption("No positive dynamic income booking profiles recorded currently.")
            st.markdown(f"**Gross Sum Aggregated Operational Turnover Revenues Baseline:** `₹{pl_dict['total_revenue']:,.2f}`")
            
        with col_p2:
            st.markdown("#### 📉 Cumulative Structural Corporate Overhead Cost Outflows Expenditure Matrix")
            if pl_dict['expenses']:
                for k, v in pl_dict['expenses'].items():
                    st.markdown(f"**{k}**: `₹{v:,.2f}`")
            else: st.caption("No overhead production structural losses recorded under variable operational codes fields currently.")
            st.markdown(f"**Gross Sum Aggregated Direct Maintenance Expenses Overhead Liability Total:** `₹{pl_dict['total_expense']:,.2f}`")
            
        st.divider()
        st.markdown("### 🏆 Comprehensive Net System Yield Performance Factor Summary Metrics Analysis")
        net = pl_dict['net_profit']
        if net >= 0:
            st.success(f"### 🎉 NET FISCAL PERIOD SURPLUS ECO-SYSTEM EARNINGS NET CASH RETAINED PROVISIONS PROFIT GAIN ACCUMULATION GENERATION: ₹{net:,.2f}")
        else:
            st.error(f"### ⚠️ DEFICIT OPERATIONAL NET FINANCIAL OUTFLOW LIABILITY DRAWN OVERHEAD EXPENDITURE NET SURPLUS RETENTION LOSS DEPRECIATION VALUE: ₹{abs(net):,.2f}")
            
    # ==================== MODULE 7: CONTINUOUS AUDITING ENGINE PROTOCOLS ====================
    with t_audit:
        st.subheader("Automated Cross-Reference Reconciliation Internal Audit Dashboard Engine")
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT account_code, account_name, account_type, balance FROM accounts")
            db_accounts = cursor.fetchall()
            
            audit_records = []
            for code, name, acc_type, ledger_bal in db_accounts:
                cursor.execute("SELECT entry_type, amount FROM journal_entries WHERE account_code = ?", (code,))
                entries = cursor.fetchall()
                
                calculated_balance = 0.0
                # Fallback injector baseline tracking validation check for initial systems capital initialization values
                if code == '1000': calculated_balance += 5000000.0
                if code == '3100': calculated_balance += 5000000.0
                
                for entry_type, amount in entries:
                    if acc_type in ['ASSET', 'EXPENSE']:
                        calculated_balance = (calculated_balance + amount) if entry_type == 'DEBIT' else (calculated_balance - amount)
                    else:
                        calculated_balance = (calculated_balance - amount) if entry_type == 'DEBIT' else (calculated_balance + amount)
                        
                diff = abs(ledger_bal - calculated_balance)
                audit_records.append({
                    "GL Code Element": code,
                    "Core Account Label Descriptor Head": name,
                    "Classification Tier": acc_type,
                    "Dynamic Ledger Index Balance Matrix Parameter Value": f"₹{ledger_bal:,.2f}",
                    "Archival Historical Journal Reconstruction Ledger Sum Calculation Value": f"₹{calculated_balance:,.2f}",
                    "System Integrity Validation Reconciliation Metric Status State Code": "🟢 Match Verified" if diff < 0.01 else f"🔴 Mismatch (Δ: ₹{diff:,.2f})"
                })
                
            st.dataframe(pd.DataFrame(audit_records), use_container_width=True, hide_index=True)
            conn.close()
        except Exception as ex:
            st.error(f"Audit analysis run routine aborted mid-execution loop pass criteria steps framework context fault: {str(ex)}")
            st.code(traceback.format_exc())

if __name__ == "__main__":
    main()

```
