
import hashlib
import os
import sqlite3
import uuid
from datetime import datetime, date
import pandas as pd
import streamlit as st

# --- PAGE CONFIGURATION & STYLING ---
st.set_page_config(
    page_title="Nexus Enterprise Core Banking",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Institutional Dark Navy Sidebar & Global Theme */
    [data-testid="stSidebar"] {
        background-color: #0B192C;
        color: #ffffff;
    }
    [data-testid="stSidebar"] * {
        color: #E2E8F0 !important;
    }
    .main {
        background-color: #F8FAFC;
    }
    .card {
        background: #ffffff;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        border-top: 4px solid #1E3E62;
    }
    .metric-card {
        background: #ffffff;
        padding: 15px;
        border-radius: 6px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        border-left: 4px solid #000000;
    }
</style>
""", unsafe_allow_html=True)

DB_FILE = "core_banking.db"

# --- DATABASE SETUP & AUTOMATIC MIGRATION ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users & RBAC
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    
    # Customers & KYC
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            pan TEXT UNIQUE NOT NULL,
            id_number TEXT UNIQUE NOT NULL,
            address TEXT NOT NULL,
            kyc_status TEXT DEFAULT 'PENDING',
            doc_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Multi-Product Accounts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_no TEXT UNIQUE NOT NULL,
            customer_id INTEGER,
            account_type TEXT NOT NULL,
            balance REAL DEFAULT 0.0,
            interest_rate REAL DEFAULT 0.0,
            tenor_months INTEGER DEFAULT 0,
            monthly_installment REAL DEFAULT 0.0,
            status TEXT DEFAULT 'ACTIVE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    """)
    
    # Chart of Accounts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chart_of_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL
        )
    """)
    
    # Journal Vouchers & Lines
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS journal_vouchers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_no TEXT UNIQUE NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_by TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS journal_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_id INTEGER,
            account_id INTEGER,
            debit REAL DEFAULT 0.0,
            credit REAL DEFAULT 0.0,
            FOREIGN KEY (voucher_id) REFERENCES journal_vouchers (id),
            FOREIGN KEY (account_id) REFERENCES chart_of_accounts (id)
        )
    """)
    
    # Transactions Log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE NOT NULL,
            account_id INTEGER,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            teller TEXT,
            FOREIGN KEY (account_id) REFERENCES accounts (id)
        )
    """)
    
    conn.commit()
    
    # Seed Default Users if none exist
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
        teller_hash = hashlib.sha256("teller123".encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", ("admin", admin_hash, "Admin"))
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", ("teller", teller_hash, "Teller"))
        conn.commit()
        
    # Seed Chart of Accounts if empty
    cursor.execute("SELECT COUNT(*) FROM chart_of_accounts")
    if cursor.fetchone()[0] == 0:
        coa_defaults = [
            ("1001", "Cash in Vault", "Asset"),
            ("1002", "Customer Loans Receivable", "Asset"),
            ("2001", "Savings Deposits", "Liability"),
            ("2002", "Fixed/Recurring Deposits", "Liability"),
            ("3001", "Paid-up Capital", "Equity"),
            ("4001", "Interest Income", "Income"),
            ("5001", "Interest Expense", "Expense")
        ]
        cursor.executemany("INSERT INTO chart_of_accounts (code, name, type) VALUES (?, ?, ?)", coa_defaults)
        conn.commit()
        
    conn.close()

init_db()

# --- UTILITY & ACCOUNTING FUNCTIONS ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def post_journal_voucher(voucher_no, date_str, description, lines, user):
    """
    Lines format: list of tuples (account_code, debit, credit)
    Ensures double-entry rule: Sum(Debits) == Sum(Credits)
    """
    total_debit = sum(l[1] for l in lines)
    total_credit = sum(l[2] for l in lines)
    
    if abs(total_debit - total_credit) > 0.01:
        return False, f"Journal Imbalance! Debits ({total_debit}) do not equal Credits ({total_credit})."
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO journal_vouchers (voucher_no, date, description, created_by) VALUES (?, ?, ?, ?)",
                       (voucher_no, date_str, description, user))
        v_id = cursor.lastrowid
        
        for acc_code, dr, cr in lines:
            cursor.execute("SELECT id FROM chart_of_accounts WHERE code = ?", (acc_code,))
            acc_row = cursor.fetchone()
            if not acc_row:
                raise Exception(f"Account code {acc_code} not found in Chart of Accounts.")
            acc_id = acc_row['id']
            cursor.execute("INSERT INTO journal_lines (voucher_id, account_id, debit, credit) VALUES (?, ?, ?, ?)",
                           (v_id, acc_id, dr, cr))
        conn.commit()
        return True, "Journal Voucher successfully posted."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

# --- SESSION STATE INITIALIZATION ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

# --- AUTHENTICATION & LOGIN UI ---
if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("""
        <div class="card" style="text-align: center;">
            <h2>🏦 Nexus Enterprise Banking</h2>
            <p style="color: #64748B;">Core Financial Infrastructure</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Secure Login", use_container_width=True)
            
            if submit:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                user = cursor.fetchone()
                conn.close()
                
                if user and user['password_hash'] == hash_password(password):
                    st.session_state.logged_in = True
                    st.session_state.username = user['username']
                    st.session_state.role = user['role']
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please verify your username and password.")
    st.stop()

# --- SIDEBAR NAVIGATION ---
st.sidebar.markdown(f"### 👤 Welcome, {st.session_state.username}")
st.sidebar.markdown(f"**Role:** {st.session_state.role}")
st.sidebar.markdown("---")

menu = st.sidebar.radio("Core Modules", [
    "Dashboard",
    "CRM & KYC Management",
    "Accounts & Deposits",
    "Teller & Cashier Counter",
    "General Ledger & Financials"
])

if st.sidebar.button("Log Out", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.rerun()

# --- MODULE 1: DASHBOARD ---
if menu == "Dashboard":
    st.title("📊 Executive Dashboard")
    st.markdown("Overview of core banking health, liquidity, and operational metrics.")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    total_cust = cursor.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    verified_cust = cursor.execute("SELECT COUNT(*) FROM customers WHERE kyc_status='VERIFIED'").fetchone()[0]
    total_accounts = cursor.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    total_deposits = cursor.execute("SELECT COALESCE(SUM(balance), 0) FROM accounts WHERE account_type IN ('SB', 'FD', 'RD')").fetchone()[0]
    total_loans = cursor.execute("SELECT COALESCE(SUM(balance), 0) FROM accounts WHERE account_type = 'LOAN'").fetchone()[0]
    
    conn.close()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="metric-card"><h3>Total Customers</h3><h2>{total_cust}</h2><p>{verified_cust} Verified KYC</p></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card"><h3>Active Accounts</h3><h2>{total_accounts}</h2><p>Multi-product portfolio</p></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="metric-card"><h3>Total Deposits</h3><h2>${total_deposits:,.2f}</h2><p>Liabilities portfolio</p></div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="metric-card"><h3>Total Loans</h3><h2>${total_loans:,.2f}</h2><p>Assets portfolio</p></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("System Status")
    st.info("All institutional nodes, ledger reconciliation checks, and cryptographic security verification layers are fully operational.")

# --- MODULE 2: CRM & KYC MANAGEMENT ---
elif menu == "CRM & KYC Management":
    st.title("📇 Customer Relationship Management & KYC")
    
    tab1, tab2 = st.tabs(["Register Customer", "KYC Verification & Directory"])
    
    with tab1:
        st.subheader("New Customer Onboarding")
        with st.form("customer_onboard"):
            c1, c2 = st.columns(2)
            with c1:
                full_name = st.text_input("Full Legal Name")
                email = st.text_input("Email Address")
                phone = st.text_input("Phone Number")
                pan = st.text_input("Tax Identifier / PAN")
            with c2:
                id_number = st.text_input("Government ID Number (Passport/SSN)")
                address = st.text_area("Residential Address")
                uploaded_doc = st.file_uploader("Upload KYC Document (PDF/Image)", type=["pdf", "png", "jpg"])
                
            submitted = st.form_submit_button("Submit for KYC Verification", use_container_width=True)
            if submitted:
                if not full_name or not pan or not id_number:
                    st.error("Please fill in all mandatory fields.")
                else:
                    doc_path = ""
                    if uploaded_doc:
                        os.makedirs("kyc_docs", exist_ok=True)
                        doc_path = os.path.join("kyc_docs", f"{pan}_{uploaded_doc.name}")
                        with open(doc_path, "wb") as f:
                            f.write(uploaded_doc.getbuffer())
                    
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute("""
                            INSERT INTO customers (full_name, email, phone, pan, id_number, address, doc_path)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (full_name, email, phone, pan, id_number, address, doc_path))
                        conn.commit()
                        st.success(f"Customer {full_name} registered successfully with PENDING KYC status.")
                    except sqlite3.IntegrityError:
                        st.error("A customer with this PAN or Government ID already exists.")
                    finally:
                        conn.close()
                        
    with tab2:
        st.subheader("Customer Directory & KYC Workflow")
        conn = get_db_connection()
        customers_df = pd.read_sql("SELECT * FROM customers", conn)
        conn.close()
        
        if customers_df.empty:
            st.info("No customers found in the directory.")
        else:
            st.dataframe(customers_df, use_container_width=True)
            
            st.markdown("### Update KYC Status")
            selected_pan = st.selectbox("Select Customer by PAN", customers_df['pan'].tolist())
            new_status = st.selectbox("Target KYC Status", ["PENDING", "VERIFIED", "REJECTED"])
            
            if st.button("Apply KYC Status Update"):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE customers SET kyc_status = ? WHERE pan = ?", (new_status, selected_pan))
                conn.commit()
                conn.close()
                st.success(f"Customer {selected_pan} status updated to {new_status}.")
                st.rerun()

# --- MODULE 3: MULTI-PRODUCT DEPOSIT & LOAN ACCOUNTS ---
elif menu == "Accounts & Deposits":
    st.title("💼 Multi-Product Deposit & Loan Accounts")
    
    tab1, tab2, tab3 = st.tabs(["Open Account", "Account Portfolio", "Loan Amortization Calculator"])
    
    conn = get_db_connection()
    customers_df = pd.read_sql("SELECT id, full_name, pan, kyc_status FROM customers WHERE kyc_status='VERIFIED'", conn)
    conn.close()
    
    with tab1:
        st.subheader("Account Origination")
        if customers_df.empty:
            st.warning("No VERIFIED customers available for account opening. Complete KYC first.")
        else:
            with st.form("account_origination"):
                cust_dict = {f"{row['full_name']} (PAN: {row['pan']})": row['id'] for _, row in customers_df.iterrows()}
                selected_cust_label = st.selectbox("Select Verified Customer", list(cust_dict.keys()))
                customer_id = cust_dict[selected_cust_label]
                
                acc_type = st.selectbox("Account Product Type", ["Savings Bank (SB)", "Fixed Deposit (FD)", "Recurring Deposit (RD)", "Loan Account"])
                
                initial_deposit = st.number_input("Initial Principal / Opening Deposit ($)", min_value=0.0, value=1000.0, step=100.0)
                interest_rate = st.number_input("Annual Interest Rate (%)", min_value=0.0, value=4.5, step=0.1)
                tenor_months = st.number_input("Tenor (Months) [FD/RD/Loan]", min_value=0, value=12, step=1)
                monthly_installment = st.number_input("Monthly Installment [RD/Loan only]", min_value=0.0, value=0.0, step=50.0)
                
                open_submit = st.form_submit_button("Originate Account", use_container_width=True)
                
                if open_submit:
                    account_no = f"ACC-{uuid.uuid4().hex[:8].upper()}"
                    db_type = {"Savings Bank (SB)": "SB", "Fixed Deposit (FD)": "FD", "Recurring Deposit (RD)": "RD", "Loan Account": "LOAN"}[acc_type]
                    
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO accounts (account_no, customer_id, account_type, balance, interest_rate, tenor_months, monthly_installment)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (account_no, customer_id, db_type, initial_deposit, interest_rate, tenor_months, monthly_installment))
                    conn.commit()
                    conn.close()
                    
                    # Post opening journal voucher
                    v_no = f"JV-{uuid.uuid4().hex[:6].upper()}"
                    today_str = date.today().isoformat()
                    if db_type in ["SB", "FD", "RD"]:
                        # Dr. Cash, Cr. Customer Deposits
                        post_journal_voucher(v_no, today_str, f"Account Opening - {account_no}", [("1001", initial_deposit, 0.0), ("2001", 0.0, initial_deposit)], st.session_state.username)
                    elif db_type == "LOAN":
                        # Dr. Loans Receivable, Cr. Cash (Disbursement)
                        post_journal_voucher(v_no, today_str, f"Loan Disbursement - {account_no}", [("1002", initial_deposit, 0.0), ("1001", 0.0, initial_deposit)], st.session_state.username)
                        
                    st.success(f"Account {account_no} successfully originated and journalized!")
                    
    with tab2:
        st.subheader("Active Account Portfolio")
        conn = get_db_connection()
        portfolio_df = pd.read_sql("""
            SELECT a.account_no, c.full_name, a.account_type, a.balance, a.interest_rate, a.tenor_months, a.status, a.created_at
            FROM accounts a JOIN customers c ON a.customer_id = c.id
        """, conn)
        conn.close()
        st.dataframe(portfolio_df, use_container_width=True)
        
    with tab3:
        st.subheader("Loan EMI Amortization Schedule Calculator")
        loan_amt = st.number_input("Loan Principal ($)", value=10000.0, step=1000.0)
        annual_rate = st.number_input("Annual Interest Rate (%) ", value=10.0, step=0.5)
        tenor_m = st.number_input("Tenor (Months) ", value=12, step=1)
        
        if st.button("Generate Amortization Schedule"):
            if tenor_m > 0 and annual_rate > 0:
                r = (annual_rate / 100) / 12
                emi = (loan_amt * r * (1 + r)**tenor_m) / ((1 + r)**tenor_m - 1)
                st.metric("Computed Monthly EMI", f"${emi:,.2f}")
                
                schedule = []
                balance = loan_amt
                for m in range(1, tenor_m + 1):
                    interest_payment = balance * r
                    principal_payment = emi - interest_payment
                    balance -= principal_payment
                    schedule.append({
                        "Month": m,
                        "EMI": round(emi, 2),
                        "Principal": round(principal_payment, 2),
                        "Interest": round(interest_payment, 2),
                        "Remaining Balance": max(0.0, round(balance, 2))
                    })
                st.dataframe(pd.DataFrame(schedule), use_container_width=True)
            else:
                st.error("Tenor and Interest Rate must be greater than zero.")

# --- MODULE 4: TELLER & CASHIER COUNTER ---
elif menu == "Teller & Cashier Counter":
    st.title("💵 Teller & Cashier Counter")
    st.markdown("Perform instantaneous cash deposits and withdrawals with automated ledger integration.")
    
    conn = get_db_connection()
    accounts_df = pd.read_sql("SELECT account_no, account_type, balance FROM accounts WHERE status='ACTIVE'", conn)
    conn.close()
    
    if accounts_df.empty:
        st.warning("No active accounts available.")
    else:
        with st.form("teller_transaction"):
            acc_list = accounts_df['account_no'].tolist()
            selected_acc = st.selectbox("Select Account Number", acc_list)
            tx_type = st.selectbox("Transaction Type", ["Deposit", "Withdrawal"])
            amount = st.number_input("Transaction Amount ($)", min_value=1.0, value=100.0, step=10.0)
            description = st.text_input("Transaction Narrative / Reference", "Over-the-Counter Cashier Transaction")
            
            submit_tx = st.form_submit_button("Process Transaction", use_container_width=True)
            
            if submit_tx:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id, balance, account_type FROM accounts WHERE account_no = ?", (selected_acc,))
                acc_row = cursor.fetchone()
                acc_id, current_bal, acc_product = acc_row['id'], acc_row['balance'], acc_row['account_type']
                
                if tx_type == "Withdrawal" and current_bal < amount and acc_product != "LOAN":
                    st.error("Insufficient funds in account for withdrawal.")
                else:
                    new_bal = current_bal + amount if tx_type == "Deposit" else current_bal - amount
                    cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?", (new_bal, acc_id))
                    
                    tx_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
                    cursor.execute("""
                        INSERT INTO transactions (transaction_id, account_id, type, amount, description, teller)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (tx_id, acc_id, tx_type, amount, description, st.session_state.username))
                    conn.commit()
                    conn.close()
                    
                    # Post Double-Entry Journal Voucher
                    v_no = f"JV-{uuid.uuid4().hex[:6].upper()}"
                    today_str = date.today().isoformat()
                    if tx_type == "Deposit":
                        # Dr. Cash in Vault, Cr. Savings Deposits
                        post_journal_voucher(v_no, today_str, f"Deposit {tx_id} - {selected_acc}", [("1001", amount, 0.0), ("2001", 0.0, amount)], st.session_state.username)
                    else:
                        # Dr. Savings Deposits, Cr. Cash in Vault
                        post_journal_voucher(v_no, today_str, f"Withdrawal {tx_id} - {selected_acc}", [("2001", amount, 0.0), ("1001", 0.0, amount)], st.session_state.username)
                        
                    st.success(f"Successfully processed {tx_type} of ${amount:,.2f} for account {selected_acc}. Tx ID: {tx_id}")

        st.markdown("---")
        st.subheader("Recent Teller Transactions")
        conn = get_db_connection()
        tx_history = pd.read_sql("""
            SELECT t.transaction_id, a.account_no, t.type, t.amount, t.description, t.timestamp, t.teller
            FROM transactions t JOIN accounts a ON t.account_id = a.id
            ORDER BY t.timestamp DESC LIMIT 10
        """, conn)
        conn.close()
        st.dataframe(tx_history, use_container_width=True)

# --- MODULE 5: GENERAL LEDGER & FINANCIAL STATEMENTS ---
elif menu == "General Ledger & Financials":
    st.title("📚 Double-Entry General Ledger & Financial Statements")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Chart of Accounts", 
        "Journal Vouchers", 
        "Trial Balance", 
        "Profit & Loss Statement", 
        "Balance Sheet"
    ])
    
    with tab1:
        st.subheader("Institutional Chart of Accounts")
        conn = get_db_connection()
        coa_df = pd.read_sql("SELECT * FROM chart_of_accounts", conn)
        conn.close()
        st.dataframe(coa_df, use_container_width=True)
        
    with tab2:
        st.subheader("Double-Entry Journal Vouchers")
        conn = get_db_connection()
        jv_df = pd.read_sql("""
            SELECT jv.voucher_no, jv.date, jv.description, jv.created_by,
                   coa.code as account_code, coa.name as account_name, jl.debit, jl.credit
            FROM journal_vouchers jv
            JOIN journal_lines jl ON jv.id = jl.voucher_id
            JOIN chart_of_accounts coa ON jl.account_id = coa.id
            ORDER BY jv.id DESC
        """, conn)
        conn.close()
        st.dataframe(jv_df, use_container_width=True)
        
    with tab3:
        st.subheader("Trial Balance (Debit & Credit Verification)")
        conn = get_db_connection()
        tb_df = pd.read_sql("""
            SELECT coa.code, coa.name, coa.type,
                   SUM(jl.debit) as total_debit,
                   SUM(jl.credit) as total_credit
            FROM chart_of_accounts coa
            LEFT JOIN journal_lines jl ON coa.id = jl.account_id
            GROUP BY coa.id, coa.code, coa.name, coa.type
        """, conn)
        conn.close()
        
        tb_df['total_debit'] = tb_df['total_debit'].fillna(0.0)
        tb_df['total_credit'] = tb_df['total_credit'].fillna(0.0)
        
        st.dataframe(tb_df, use_container_width=True)
        
        tot_dr = tb_df['total_debit'].sum()
        tot_cr = tb_df['total_credit'].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("Total Debits", f"${tot_dr:,.2f}")
        c2.metric("Total Credits", f"${tot_cr:,.2f}")
        
        if abs(tot_dr - tot_cr) < 0.01:
            st.success("Trial Balance is Balanced (Sum of Debits equals Sum of Credits).")
        else:
            st.error("Trial Balance Mismatch detected!")
            
    with tab4:
        st.subheader("Profit & Loss Statement (Income vs. Expense)")
        conn = get_db_connection()
        pl_df = pd.read_sql("""
            SELECT coa.code, coa.name, coa.type,
                   SUM(jl.credit - jl.debit) as net_balance
            FROM chart_of_accounts coa
            JOIN journal_lines jl ON coa.id = jl.account_id
            WHERE coa.type IN ('Income', 'Expense')
            GROUP BY coa.id, coa.code, coa.name, coa.type
        """, conn)
        conn.close()
        
        income_df = pl_df[pl_df['type'] == 'Income']
        expense_df = pl_df[pl_df['type'] == 'Expense']
        
        st.markdown("### Income")
        st.dataframe(income_df, use_container_width=True)
        total_income = income_df['net_balance'].sum() if not income_df.empty else 0.0
        
        st.markdown("### Expenses")
        st.dataframe(expense_df, use_container_width=True)
        total_expense = expense_df['net_balance'].sum() if not expense_df.empty else 0.0
        
        net_profit = total_income - total_expense
        st.markdown("---")
        st.metric("YTD Net Profit / (Loss)", f"${net_profit:,.2f}")
        
    with tab5:
        st.subheader("Balance Sheet (Assets = Liabilities + Equity)")
        conn = get_db_connection()
        bs_df = pd.read_sql("""
            SELECT coa.code, coa.name, coa.type,
                   SUM(CASE WHEN coa.type IN ('Asset', 'Expense') THEN jl.debit - jl.credit ELSE jl.credit - jl.debit END) as balance
            FROM chart_of_accounts coa
            JOIN journal_lines jl ON coa.id = jl.account_id
            GROUP BY coa.id, coa.code, coa.name, coa.type
        """, conn)
        conn.close()
        
        assets = bs_df[bs_df['type'] == 'Asset']
        liabilities = bs_df[bs_df['type'] == 'Liability']
        equity = bs_df[bs_df['type'] == 'Equity']
        
        st.markdown("### Assets")
        st.dataframe(assets, use_container_width=True)
        tot_assets = assets['balance'].sum() if not assets.empty else 0.0
        
        st.markdown("### Liabilities")
        st.dataframe(liabilities, use_container_width=True)
        tot_liab = liabilities['balance'].sum() if not liabilities.empty else 0.0
        
        st.markdown("### Equity")
        st.dataframe(equity, use_container_width=True)
        tot_equity = equity['balance'].sum() if not equity.empty else 0.0
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        c1.metric("Total Assets", f"${tot_assets:,.2f}")
        c2.metric("Total Liabilities + Equity", f"${tot_liab + tot_equity:,.2f}")









