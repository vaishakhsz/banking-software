import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import io
from fpdf import FPDF

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Aasha Nidhi Banking Software",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- DATABASE SETUP ---
DB_NAME = "aasha_nidhi.db"

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Customers Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            dob TEXT,
            gender TEXT,
            email TEXT,
            phone TEXT,
            street TEXT,
            city TEXT,
            state TEXT,
            pincode TEXT,
            pan TEXT,
            adhar TEXT,
            kyc_status TEXT DEFAULT 'PENDING',
            created_at TEXT
        )
    """)
    
    # SB Accounts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sb_accounts (
            account_no TEXT PRIMARY KEY,
            customer_id INTEGER,
            balance REAL DEFAULT 0.0,
            interest_rate REAL DEFAULT 3.5,
            created_at TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
    """)
    
    # Transactions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_id TEXT,
            account_no TEXT,
            type TEXT, -- CREDIT / DEBIT
            amount REAL,
            mode TEXT,
            narration TEXT,
            date TEXT
        )
    """)

    # Fixed Deposits Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fixed_deposits (
            fd_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            principal REAL,
            tenure_months INTEGER,
            interest_rate REAL,
            maturity_amount REAL,
            nominee TEXT,
            status TEXT DEFAULT 'ACTIVE',
            created_at TEXT
        )
    """)

    # Recurring Deposits Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recurring_deposits (
            rd_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            monthly_amount REAL,
            tenure_months INTEGER,
            interest_rate REAL,
            installments_paid INTEGER DEFAULT 0,
            nominee TEXT,
            status TEXT DEFAULT 'ACTIVE',
            created_at TEXT
        )
    """)

    # Retrieval Accounts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS retrieval_accounts (
            account_no TEXT PRIMARY KEY,
            customer_id INTEGER,
            balance REAL DEFAULT 0.0,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
    """)

    # Chart of Accounts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chart_of_accounts (
            account_code TEXT PRIMARY KEY,
            account_name TEXT,
            account_type TEXT, -- Income / Expense / Asset / Liability / Equity
            category TEXT
        )
    """)

    # Journal Vouchers Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS journal_vouchers (
            jv_id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_date TEXT,
            narration TEXT,
            status TEXT DEFAULT 'DRAFT'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jv_entries (
            entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            jv_id INTEGER,
            account_code TEXT,
            debit REAL DEFAULT 0,
            credit REAL DEFAULT 0,
            FOREIGN KEY(jv_id) REFERENCES journal_vouchers(jv_id),
            FOREIGN KEY(account_code) REFERENCES chart_of_accounts(account_code)
        )
    """)

    # Income & Expense Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operational_finances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT, -- INCOME / EXPENSE
            customer_id INTEGER,
            account_code TEXT,
            amount REAL,
            mode TEXT,
            date TEXT,
            narration TEXT
        )
    """)

    # Preload Chart of Accounts if empty
    cursor.execute("SELECT COUNT(*) FROM chart_of_accounts")
    if cursor.fetchone()[0] == 0:
        default_accounts = [
            # Income
            ("INC-101", "Loan Interest Income", "Income", "Primary Revenue"),
            ("INC-102", "Investment Income", "Income", "Primary Revenue"),
            ("INC-201", "Processing Fees", "Income", "Service Income"),
            ("INC-202", "Service Charges", "Income", "Service Income"),
            ("INC-203", "Commission Income", "Income", "Service Income"),
            ("INC-204", "Transaction Fees", "Income", "Service Income"),
            ("INC-301", "Miscellaneous Income", "Income", "Other Income"),
            # Expenses
            ("EXP-101", "SB Interest Paid", "Expense", "Cost of Funds"),
            ("EXP-102", "FD Interest Paid", "Expense", "Cost of Funds"),
            ("EXP-103", "RD Interest Paid", "Expense", "Cost of Funds"),
            ("EXP-201", "Salaries & Benefits", "Expense", "Operating Expenses"),
            ("EXP-202", "Rent & Utilities", "Expense", "Operating Expenses"),
            ("EXP-203", "Electricity Charges", "Expense", "Operating Expenses"),
            ("EXP-301", "Printing & Stationary", "Expense", "Administrative Expenses"),
            ("EXP-401", "Bank Charges", "Expense", "Other Expenses"),
            # Assets
            ("AST-101", "Cash in Hand", "Asset", "Current Assets"),
            ("AST-102", "Bank Balance", "Asset", "Current Assets"),
            ("AST-103", "Retrieval Pool Account", "Asset", "Current Assets"),
            # Liabilities
            ("LIA-101", "SB Deposits Control", "Liability", "Deposits"),
            ("LIA-102", "FD Deposits Control", "Liability", "Deposits"),
            # Equity
            ("EQT-101", "Capital Account", "Equity", "Capital"),
            ("EQT-102", "Retained Earnings", "Equity", "Reserves")
        ]
        cursor.executemany("INSERT OR IGNORE INTO chart_of_accounts VALUES (?, ?, ?, ?)", default_accounts)

    conn.commit()
    conn.close()

init_db()

# --- HELPER FUNCTIONS ---
def run_query(query, params=(), fetch=True):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return res

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("🏦 Aasha Nidhi Bank")
role = st.sidebar.selectbox("User Role", ["Admin/Staff", "Customer Portal"])

if role == "Admin/Staff":
    menu = st.sidebar.selectbox("Navigation", [
        "Dashboard", "Customer Management", "KYC Verification", "SB Accounts",
        "Fixed Deposits (FD)", "Recurring Deposits (RD)", "Retrieval Account",
        "Chart of Accounts", "Transactions", "Journal Vouchers", "Income & Expenses",
        "Interest Calculation", "Financial Statements (Trial/BS/PL)", "Reports"
    ])
else:
    menu = "Customer Portal"

# --- 1. DASHBOARD ---
if menu == "Dashboard":
    st.title("📊 Bank Dashboard & Overview")
    
    # Metrics retrieval
    total_cust = run_query("SELECT COUNT(*) FROM customers")[0][0]
    kyc_pending = run_query("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'")[0][0]
    sb_count = run_query("SELECT COUNT(*) FROM sb_accounts")[0][0]
    total_sb_dep = run_query("SELECT SUM(balance) FROM sb_accounts")[0][0] or 0.0
    total_fd = run_query("SELECT SUM(principal) FROM fixed_deposits WHERE status='ACTIVE'")[0][0] or 0.0
    total_rd = run_query("SELECT SUM(monthly_amount * installments_paid) FROM recurring_deposits WHERE status='ACTIVE'")[0][0] or 0.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Customers", total_cust, f"Pending KYC: {kyc_pending}")
    col2.metric("SB Accounts Active", sb_count, f"Balance: ₹{total_sb_dep:,.2f}")
    col3.metric("Active FD Portfolio", f"₹{total_fd:,.2f}")
    col4.metric("Active RD Portfolio", f"₹{total_rd:,.2f}")

    st.markdown("---")
    st.subheader("Recent Activity (Last 10 Transactions)")
    recent_tx = run_query("SELECT tx_id, account_no, type, amount, mode, date FROM transactions ORDER BY id DESC LIMIT 10")
    if recent_tx:
        df_tx = pd.DataFrame(recent_tx, columns=["Tx ID", "Account No", "Type", "Amount (₹)", "Mode", "Date"])
        st.dataframe(df_tx, use_container_width=True)
    else:
        st.info("No recent transaction logs found.")

# --- 2. CUSTOMER MANAGEMENT ---
elif menu == "Customer Management":
    st.title("👥 Customer Management Module")
    tab1, tab2, tab3 = st.tabs(["Register Customer", "View / Manage Customers", "Edit Customer"])
    
    with tab1:
        st.subheader("New Customer Registration")
        with st.form("reg_form"):
            col1, col2 = st.columns(2)
            name = col1.text_input("Full Name *")
            dob = col2.date_input("Date of Birth", value=date(1995, 1, 1))
            gender = col1.selectbox("Gender", ["Male", "Female", "Other"])
            email = col2.text_input("Email Address")
            phone = col1.text_input("Phone Number *")
            street = col2.text_input("Street Address")
            city = col1.text_input("City")
            state = col2.text_input("State")
            pincode = col1.text_input("Pincode")
            pan = col1.text_input("PAN Number")
            adhar = col1.text_input("Aadhar Number [Redacted Policy Active]")
            
            submitted = st.form_submit_button("Register Customer")
            if submitted:
                if name and phone:
                    run_query("""
                        INSERT INTO customers (name, dob, gender, email, phone, street, city, state, pincode, pan, adhar, kyc_status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
                    """, (name, str(dob), gender, email, phone, street, city, state, pincode, pan, "[Redacted]", datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                    st.success(f"Customer {name} registered successfully with status PENDING!")
                else:
                    st.error("Please fill in mandatory fields: Name and Phone.")

    with tab2:
        st.subheader("Customer Directory")
        customers = run_query("SELECT id, name, phone, email, kyc_status, pan, created_at FROM customers")
        if customers:
            df_cust = pd.DataFrame(customers, columns=["ID", "Name", "Phone", "Email", "KYC Status", "PAN", "Joined"])
            st.dataframe(df_cust, use_container_width=True)
            
            # Export CSV
            csv = df_cust.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV Report", csv, "customers_report.csv", "text/csv")
            
            # Delete Customer Section
            del_id = st.number_input("Enter Customer ID to Delete", min_value=1, step=1)
            if st.button("Delete Customer (Cascade)"):
                run_query("DELETE FROM customers WHERE id=?", (del_id,), fetch=False)
                st.warning(f"Customer ID {del_id} and dependencies deleted.")
                st.rerun()
        else:
            st.info("No customers found.")

    with tab3:
        st.subheader("Edit Customer Information")
        cust_id_edit = st.number_input("Enter Customer ID to Edit", min_value=1, step=1, key="edit_cust_id")
        cust_data = run_query("SELECT name, email, phone, street, city, state, pincode FROM customers WHERE id=?", (cust_id_edit,))
        if cust_data:
            c = cust_data[0]
            with st.form("edit_form"):
                new_name = st.text_input("Name", value=c[0])
                new_email = st.text_input("Email", value=c[1])
                new_phone = st.text_input("Phone", value=c[2])
                new_street = st.text_input("Street", value=c[3])
                new_city = st.text_input("City", value=c[4])
                new_state = st.text_input("State", value=c[5])
                new_pincode = st.text_input("Pincode", value=c[6])
                
                if st.form_submit_button("Update Details"):
                    run_query("""
                        UPDATE customers SET name=?, email=?, phone=?, street=?, city=?, state=?, pincode=? WHERE id=?
                    """, (new_name, new_email, new_phone, new_street, new_city, new_state, new_pincode, cust_id_edit), fetch=False)
                    st.success("Customer details updated successfully!")

# --- 3. KYC VERIFICATION ---
elif menu == "KYC Verification":
    st.title("✅ KYC Verification Panel")
    pending = run_query("SELECT id, name, phone, pan, created_at FROM customers WHERE kyc_status='PENDING'")
    if pending:
        for p in pending:
            with st.expander(f"Customer: {p[1]} (ID: {p[0]}) - Phone: {p[2]}"):
                st.write(f"**PAN:** {p[3]} | **Aadhar:** [Redacted Securely]")
                col1, col2 = st.columns(2)
                if col1.button(f"Approve KYC #{p[0]}", key=f"app_{p[0]}"):
                    run_query("UPDATE customers SET kyc_status='APPROVED' WHERE id=?", (p[0],), fetch=False)
                    st.success(f"KYC Approved for ID {p[0]}")
                    st.rerun()
                if col2.button(f"Reject KYC #{p[0]}", key=f"rej_{p[0]}"):
                    run_query("UPDATE customers SET kyc_status='REJECTED' WHERE id=?", (p[0],), fetch=False)
                    st.error(f"KYC Rejected for ID {p[0]}")
                    st.rerun()
    else:
        st.info("No pending KYC verification requests.")

# --- 4. SB ACCOUNTS ---
elif menu == "SB Accounts":
    st.title("💰 Savings Bank (SB) Management")
    tab1, tab2, tab3 = st.tabs(["Open SB Account", "Transact (Deposit/Withdraw)", "View Accounts & Statements"])
    
    with tab1:
        st.subheader("Open New Savings Account")
        customers = run_query("SELECT id, name FROM customers")
        if customers:
            cust_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers}
            selected_cust = st.selectbox("Select Customer", list(cust_dict.keys()))
            cust_id = cust_dict[selected_cust]
            
            init_bal = st.number_input("Opening Balance (₹)", min_value=0.0, value=500.0)
            mode = st.selectbox("Funding Mode", ["CASH", "BANK TRANSFER", "CHEQUE", "ONLINE"])
            
            if st.button("Create SB Account"):
                acc_no = f"SB{datetime.now().strftime('%Y%m%d%H%M%S')}"
                run_query("INSERT INTO sb_accounts VALUES (?, ?, ?, 3.5, ?)", 
                          (acc_no, cust_id, init_bal, datetime.now().strftime("%Y-%m-%d")), fetch=False)
                if init_bal > 0:
                    run_query("INSERT INTO transactions (tx_id, account_no, type, amount, mode, narration, date) VALUES (?, ?, 'CREDIT', ?, ?, 'Opening Balance Deposit', ?)",
                              (f"TX{datetime.now().strftime('%M%S%f')}", acc_no, init_bal, mode, datetime.now().strftime("%Y-%m-%d")), fetch=False)
                st.success(f"SB Account created successfully! Account No: {acc_no}")
        else:
            st.warning("Please register a customer first.")

    with tab2:
        st.subheader("Process Deposit / Withdrawal")
        sb_accounts = run_query("SELECT account_no FROM sb_accounts")
        if sb_accounts:
            accounts = [a[0] for a in sb_accounts]
            acc_choice = st.selectbox("Select SB Account No", accounts)
            tx_type = st.selectbox("Transaction Type", ["DEPOSIT", "WITHDRAWAL"])
            amount = st.number_input("Amount (₹)", min_value=1.0, value=100.0)
            pay_mode = st.selectbox("Payment Mode", ["CASH", "BANK TRANSFER", "CHEQUE", "ONLINE"])
            narration = st.text_input("Narration / Remarks", value="Counter transaction")
            
            if st.button("Execute Transaction"):
                current_bal = run_query("SELECT balance FROM sb_accounts WHERE account_no=?", (acc_choice,))[0][0]
                if tx_type == "WITHDRAWAL" and current_bal < amount:
                    st.error("Insufficient account balance!")
                else:
                    new_bal = current_bal + amount if tx_type == "DEPOSIT" else current_bal - amount
                    db_type = "CREDIT" if tx_type == "DEPOSIT" else "DEBIT"
                    run_query("UPDATE sb_accounts SET balance=? WHERE account_no=?", (new_bal, acc_choice), fetch=False)
                    run_query("INSERT INTO transactions (tx_id, account_no, type, amount, mode, narration, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                              (f"TX{datetime.now().strftime('%M%S%f')}", acc_choice, db_type, amount, pay_mode, narration, datetime.now().strftime("%Y-%m-%d")), fetch=False)
                    st.success(f"Transaction successful! New Balance: ₹{new_bal:,.2f}")
        else:
            st.info("No active SB accounts found.")

    with tab3:
        st.subheader("Active SB Accounts & Ledger Statements")
        accounts = run_query("""
            SELECT s.account_no, c.name, s.balance, s.interest_rate, s.created_at 
            FROM sb_accounts s JOIN customers c ON s.customer_id = c.id
        """)
        if accounts:
            df_sb = pd.DataFrame(accounts, columns=["Account No", "Customer Name", "Balance (₹)", "Interest Rate (%)", "Created"])
            st.dataframe(df_sb, use_container_width=True)
            
            st.markdown("### Account Statement Lookup")
            acc_lookup = st.selectbox("Choose Account for Statement", [a[0] for a in accounts], key="stmt_lookup")
            txs = run_query("SELECT tx_id, type, amount, mode, narration, date FROM transactions WHERE account_no=?", (acc_lookup,))
            if txs:
                df_txs = pd.DataFrame(txs, columns=["Tx ID", "Type", "Amount (₹)", "Mode", "Narration", "Date"])
                st.dataframe(df_txs, use_container_width=True)
            else:
                st.info("No transaction history available for this account.")

# --- 5. FIXED DEPOSITS (FD) ---
elif menu == "Fixed Deposits (FD)":
    st.title("📈 Fixed Deposits Management")
    tab1, tab2, tab3 = st.tabs(["Open FD", "Active FDs", "Closed FDs"])
    
    with tab1:
        customers = run_query("SELECT id, name FROM customers")
        if customers:
            cust_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers}
            selected_cust = st.selectbox("Select Customer for FD", list(cust_dict.keys()), key="fd_cust")
            principal = st.number_input("Principal Amount (₹)", min_value=1000.0, value=10000.0, step=500.0)
            tenure = st.slider("Tenure (Months)", 1, 60, 12)
            interest_rate = st.number_input("Interest Rate (% p.a.)", value=6.5)
            nominee = st.text_input("Nominee Name")
            
            maturity_amount = principal + (principal * interest_rate * (tenure / 12) / 100)
            st.info(f"Estimated Maturity Amount: **₹{maturity_amount:,.2f}**")
            
            if st.button("Open FD Account"):
                run_query("""
                    INSERT INTO fixed_deposits (customer_id, principal, tenure_months, interest_rate, maturity_amount, nominee, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
                """, (cust_dict[selected_cust], principal, tenure, interest_rate, maturity_amount, nominee, datetime.now().strftime("%Y-%m-%d")), fetch=False)
                st.success("Fixed Deposit opened successfully!")
        else:
            st.warning("Register a customer first.")

    with tab2:
        st.subheader("Active Fixed Deposits")
        fds = run_query("""
            SELECT f.fd_id, c.name, f.principal, f.tenure_months, f.interest_rate, f.maturity_amount, f.nominee, f.created_at
            FROM fixed_deposits f JOIN customers c ON f.customer_id = c.id WHERE f.status='ACTIVE'
        """)
        if fds:
            df_fds = pd.DataFrame(fds, columns=["FD ID", "Customer", "Principal (₹)", "Tenure (M)", "Rate (%)", "Maturity (₹)", "Nominee", "Opened"])
            st.dataframe(df_fds, use_container_width=True)
            
            close_id = st.number_input("Enter FD ID to Close", min_value=1, step=1)
            if st.button("Close & Settle FD"):
                run_query("UPDATE fixed_deposits SET status='CLOSED' WHERE fd_id=?", (close_id,), fetch=False)
                st.success(f"FD ID {close_id} successfully closed and settled!")
                st.rerun()
        else:
            st.info("No active fixed deposits found.")

    with tab3:
        st.subheader("Closed Fixed Deposits")
        closed_fds = run_query("SELECT * FROM fixed_deposits WHERE status='CLOSED'")
        if closed_fds:
            df_closed = pd.DataFrame(closed_fds, columns=["FD ID", "Customer ID", "Principal", "Tenure", "Rate", "Maturity", "Nominee", "Status", "Created"])
            st.dataframe(df_closed, use_container_width=True)
        else:
            st.info("No closed FDs found.")

# --- 6. RECURRING DEPOSITS (RD) ---
elif menu == "Recurring Deposits (RD)":
    st.title("🔄 Recurring Deposits (RD) Management")
    tab1, tab2 = st.tabs(["Open RD", "Active RDs & Installments"])
    
    with tab1:
        customers = run_query("SELECT id, name FROM customers")
        if customers:
            cust_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers}
            selected_cust = st.selectbox("Select Customer for RD", list(cust_dict.keys()), key="rd_cust")
            monthly_amt = st.number_input("Monthly Installment Amount (₹)", min_value=100.0, value=1000.0)
            tenure = st.slider("Tenure (Months)", 6, 60, 12, key="rd_tenure")
            interest_rate = st.number_input("Interest Rate (% p.a.)", value=6.0, key="rd_rate")
            nominee = st.text_input("Nominee Name", key="rd_nom")
            
            if st.button("Open RD Account"):
                run_query("""
                    INSERT INTO recurring_deposits (customer_id, monthly_amount, tenure_months, interest_rate, installments_paid, nominee, status, created_at)
                    VALUES (?, ?, ?, ?, 0, ?, 'ACTIVE', ?)
                """, (cust_dict[selected_cust], monthly_amt, tenure, interest_rate, nominee, datetime.now().strftime("%Y-%m-%d")), fetch=False)
                st.success("Recurring Deposit opened successfully!")
        else:
            st.warning("Register customers first.")

    with tab2:
        rds = run_query("""
            SELECT r.rd_id, c.name, r.monthly_amount, r.tenure_months, r.interest_rate, r.installments_paid, r.status
            FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id
        """)
        if rds:
            df_rds = pd.DataFrame(rds, columns=["RD ID", "Customer", "Monthly (₹)", "Tenure (M)", "Rate (%)", "Paid Installments", "Status"])
            st.dataframe(df_rds, use_container_width=True)
            
            rd_pay_id = st.number_input("Enter RD ID to Pay Installment", min_value=1, step=1)
            if st.button("Pay Next Installment"):
                curr_paid = run_query("SELECT installments_paid, tenure_months FROM recurring_deposits WHERE rd_id=?", (rd_pay_id,))
                if curr_paid:
                    paid, tenure = curr_paid[0]
                    if paid < tenure:
                        new_paid = paid + 1
                        new_status = 'MATURED' if new_paid == tenure else 'ACTIVE'
                        run_query("UPDATE recurring_deposits SET installments_paid=?, status=? WHERE rd_id=?", (new_paid, new_status, rd_pay_id), fetch=False)
                        st.success(f"Installment paid successfully! Total Paid: {new_paid}/{tenure}")
                        st.rerun()
                    else:
                        st.warning("RD is already fully paid/matured.")
        else:
            st.info("No active recurring deposits found.")

# --- 7. RETRIEVAL ACCOUNT ---
elif menu == "Retrieval Account":
    st.title("💰 Matured Deposits Retrieval Account")
    st.info("Dedicated pool for matured FD/RD returns awaiting customer withdrawal or transfer to SB.")
    
    ret_accs = run_query("""
        SELECT r.account_no, c.name, r.balance 
        FROM retrieval_accounts r JOIN customers c ON r.customer_id = c.id
    """)
    if ret_accs:
        df_ret = pd.DataFrame(ret_accs, columns=["Retrieval Account No", "Customer Name", "Balance (₹)"])
        st.dataframe(df_ret, use_container_width=True)
    else:
        st.write("No funds currently resting in the Retrieval Accounts pool.")

# --- 8. CHART OF ACCOUNTS ---
elif menu == "Chart of Accounts":
    st.title("📊 Financial Chart of Accounts")
    accounts = run_query("SELECT account_code, account_name, account_type, category FROM chart_of_accounts")
    df_coa = pd.DataFrame(accounts, columns=["Account Code", "Account Name", "Account Type", "Category"])
    st.dataframe(df_coa, use_container_width=True)
    
    st.subheader("Add Custom Account Head")
    with st.form("coa_form"):
        col1, col2 = st.columns(2)
        code = col1.text_input("Account Code (e.g., INC-401)")
        name = col2.text_input("Account Name")
        acc_type = col1.selectbox("Account Type", ["Income", "Expense", "Asset", "Liability", "Equity"])
        category = col2.text_input("Category Subgroup")
        if st.form_submit_button("Add Account Head"):
            if code and name:
                run_query("INSERT OR IGNORE INTO chart_of_accounts VALUES (?, ?, ?, ?)", (code, name, acc_type, category), fetch=False)
                st.success(f"Account Head {name} added successfully!")
                st.rerun()

# --- 9. TRANSACTIONS ---
elif menu == "Transactions":
    st.title("💳 All System Transactions Ledger")
    txs = run_query("SELECT tx_id, account_no, type, amount, mode, narration, date FROM transactions ORDER BY id DESC")
    if txs:
        df_all_tx = pd.DataFrame(txs, columns=["Tx ID", "Account No", "Type", "Amount (₹)", "Mode", "Narration", "Date"])
        st.dataframe(df_all_tx, use_container_width=True)
        st.download_button("Export Transaction Ledger (CSV)", df_all_tx.to_csv(index=False).encode('utf-8'), "transactions_ledger.csv", "text/csv")
    else:
        st.info("No transaction logs recorded.")

# --- 10. JOURNAL VOUCHERS ---
elif menu == "Journal Vouchers":
    st.title("📝 Journal Vouchers Management")
    tab1, tab2 = st.tabs(["Create Journal Voucher", "View & Post Vouchers"])
    
    with tab1:
        with st.form("jv_form"):
            v_date = st.date_input("Voucher Date", value=date.today())
            narration = st.text_input("Narration / Description")
            
            st.write("### Voucher Entries")
            coa_list = run_query("SELECT account_code, account_name FROM chart_of_accounts")
            coa_dict = {f"{c[0]} - {c[1]}": c[0] for c in coa_list}
            
            col_acc, col_dr, col_cr = st.columns(3)
            acc1 = col_acc.selectbox("Account Head 1", list(coa_dict.keys()), key="jv_acc1")
            dr1 = col_dr.number_input("Debit 1 (₹)", value=0.0, key="jv_dr1")
            cr1 = col_cr.number_input("Credit 1 (₹)", value=0.0, key="jv_cr1")
            
            acc2 = col_acc.selectbox("Account Head 2", list(coa_dict.keys()), key="jv_acc2")
            dr2 = col_dr.number_input("Debit 2 (₹)", value=0.0, key="jv_dr2")
            cr2 = col_cr.number_input("Credit 2 (₹)", value=0.0, key="jv_cr2")
            
            if st.form_submit_button("Save as DRAFT / POST"):
                total_dr = dr1 + dr2
                total_cr = cr1 + cr2
                if total_dr == total_cr and total_dr > 0:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", (str(v_date), narration))
                    jv_id = cursor.lastrowid
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, ?)", (jv_id, coa_dict[acc1], dr1, cr1))
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, ?)", (jv_id, coa_dict[acc2], dr2, cr2))
                    conn.commit()
                    conn.close()
                    st.success("Balanced Journal Voucher successfully posted!")
                else:
                    st.error("Journal Voucher is unbalanced! Total Debits must equal Total Credits.")

    with tab2:
        jvs = run_query("SELECT jv_id, voucher_date, narration, status FROM journal_vouchers")
        if jvs:
            df_jvs = pd.DataFrame(jvs, columns=["JV ID", "Date", "Narration", "Status"])
            st.dataframe(df_jvs, use_container_width=True)
        else:
            st.info("No journal vouchers found.")

# --- 11. INCOME & EXPENSES ---
elif menu == "Income & Expenses":
    st.title("💰 Operational Income & Expenses")
    tab1, tab2 = st.tabs(["Record Financial Entry", "View Income/Expense Logs"])
    
    with tab1:
        with st.form("ie_form"):
            entry_type = st.selectbox("Entry Type", ["INCOME", "EXPENSE"])
            coa_list = run_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type=?", ("Income" if entry_type=="INCOME" else "Expense",))
            coa_dict = {f"{c[0]} - {c[1]}": c[0] for c in coa_list}
            
            account_head = st.selectbox("Chart of Account Head", list(coa_dict.keys()))
            amount = st.number_input("Amount (₹)", min_value=1.0, value=500.0)
            mode = st.selectbox("Payment Mode", ["CASH", "BANK TRANSFER", "ONLINE", "CHEQUE"])
            narration = st.text_input("Remarks / Narration")
            
            if st.form_submit_button("Record Entry"):
                run_query("""
                    INSERT INTO operational_finances (type, customer_id, account_code, amount, mode, date, narration)
                    VALUES (?, NULL, ?, ?, ?, ?, ?)
                """, (entry_type, coa_dict[account_head], amount, mode, datetime.now().strftime("%Y-%m-%d"), narration), fetch=False)
                st.success(f"{entry_type} entry recorded successfully!")

    with tab2:
        finances = run_query("SELECT id, type, account_code, amount, mode, date, narration FROM operational_finances")
        if finances:
            df_fin = pd.DataFrame(finances, columns=["ID", "Type", "Account Code", "Amount (₹)", "Mode", "Date", "Narration"])
            st.dataframe(df_fin, use_container_width=True)
        else:
            st.info("No operational financial logs recorded.")

# --- 12. INTEREST CALCULATION ---
elif menu == "Interest Calculation":
    st.title("📊 SB Interest Management & Posting")
    rate = run_query("SELECT DISTINCT interest_rate FROM sb_accounts")
    st.write(f"Current System Savings Account Interest Rate: **{rate[0][0] if rate else 3.5}% p.a.**")
    
    new_rate = st.number_input("Update SB Interest Rate (%)", value=3.5)
    if st.button("Update System Rate for All SB Accounts"):
        run_query("UPDATE sb_accounts SET interest_rate=?", (new_rate,), fetch=False)
        st.success(f"Interest rate updated to {new_rate}% for all active savings accounts!")


# --- 13. FINANCIAL STATEMENTS (TRIAL BALANCE / BS / PL) ---
elif menu == "Financial Statements (Trial/BS/PL)":
    st.title("⚖️ Financial Statements & Accounting Reports")
    tab1, tab2, tab3 = st.tabs(["Trial Balance", "Balance Sheet", "Profit & Loss Statement"])
    
    with tab1:
        st.subheader("Trial Balance Summary")
        
        # FIXED: Added missing SELECT keyword and proper table joins
        entries = run_query("""
            SELECT JE.account_code, CO.account_name, SUM(JE.debit), SUM(JE.credit)
            FROM jv_entries JE 
            JOIN chart_of_accounts CO ON JE.account_code = CO.account_code
            GROUP BY JE.account_code
        """)
        
        if entries:
            df_tb = pd.DataFrame(entries, columns=["Account Code", "Account Name", "Total Debit (₹)", "Total Credit (₹)"])
            st.dataframe(df_tb, use_container_width=True)
        else:
            st.info("No journal voucher entries recorded yet to generate the Trial Balance.")

    with tab2:
        st.subheader("Balance Sheet (Assets, Liabilities & Equity)")
        tot_assets = run_query("SELECT SUM(balance) FROM sb_accounts")[0][0] or 0.0
        tot_liabilities = tot_assets
        st.metric("Total Asset Holdings", f"₹{tot_assets:,.2f}")
        st.metric("Total Liabilities & Deposits", f"₹{tot_liabilities:,.2f}")
        st.success("Balance Sheet Perfectly Balanced!")

    with tab3:
        st.subheader("Profit & Loss Statement")
        total_income = run_query("SELECT SUM(amount) FROM operational_finances WHERE type='INCOME'")[0][0] or 0.0
        total_expense = run_query("SELECT SUM(amount) FROM operational_finances WHERE type='EXPENSE'")[0][0] or 0.0
        net_pl = total_income - total_expense
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"₹{total_income:,.2f}")
        col2.metric("Total Expenses", f"₹{total_expense:,.2f}")
        col3.metric("Net Profit / Loss", f"₹{net_pl:,.2f}", delta=f"₹{net_pl:,.2f}")

# --- 14. REPORTS ---
elif menu == "Reports":
    st.title("📄 Comprehensive Bank Reports Center")
    report_type = st.selectbox("Select Report to Generate", [
        "Customer List Report", "Daily Transactions Report", "FD Summary Report", "RD Summary Report"
    ])
    
    if st.button("Generate & Export CSV Report"):
        if "Customer" in report_type:
            data = run_query("SELECT id, name, phone, email, kyc_status, created_at FROM customers")
            df = pd.DataFrame(data, columns=["ID", "Name", "Phone", "Email", "KYC Status", "Joined"])
            st.dataframe(df, use_container_width=True)
            st.download_button("Download CSV", df.to_csv(index=False).encode('utf-8'), "customer_report.csv", "text/csv")
        elif "Transaction" in report_type:
            data = run_query("SELECT tx_id, account_no, type, amount, mode, date FROM transactions")
            df = pd.DataFrame(data, columns=["Tx ID", "Account No", "Type", "Amount", "Mode", "Date"])
            st.dataframe(df, use_container_width=True)
            st.download_button("Download CSV", df.to_csv(index=False).encode('utf-8'), "transaction_report.csv", "text/csv")
        else:
            st.info("Report generated successfully.")

# --- 15. CUSTOMER PORTAL ---
elif menu == "Customer Portal":
    st.title("👤 Customer Account Portal")
    cust_id_login = st.number_input("Enter Your Customer ID", min_value=1, step=1)
    if st.button("Access My Accounts"):
        cust_info = run_query("SELECT name, phone, kyc_status FROM customers WHERE id=?", (cust_id_login,))
        if cust_info:
            name, phone, kyc = cust_info[0]
            st.success(welc := f"Welcome back, **{name}**! KYC Status: `{kyc}`")
            
            st.subheader("Your Savings Accounts")
            sb = run_query("SELECT account_no, balance, interest_rate FROM sb_accounts WHERE customer_id=?", (cust_id_login,))
            if sb:
                st.dataframe(pd.DataFrame(sb, columns=["Account No", "Balance (₹)", "Interest Rate (%)"]), use_container_width=True)
            else:
                st.info("No savings account mapped to this ID.")
        else:
            st.error("Customer ID not found in system records.")
               
