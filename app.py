import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import os
from fpdf import FPDF

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Aasha Nidhi Banking Software",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- UPLOAD FOLDER SETUP ---
UPLOAD_DIR = "customer_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
            adhar_file TEXT,
            pan_file TEXT,
            signature_file TEXT,
            kyc_status TEXT DEFAULT 'PENDING',
            created_at TEXT
        )
    """)
    
    for col, col_type in [("adhar_file", "TEXT"), ("pan_file", "TEXT"), ("signature_file", "TEXT")]:
        try:
            cursor.execute(f"ALTER TABLE customers ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass
    
    # SB Accounts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sb_accounts (
            account_no TEXT PRIMARY KEY,
            customer_id INTEGER,
            balance REAL DEFAULT 0.0,
            interest_rate REAL DEFAULT 3.5,
            created_at TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
        )
    """)
    
    # Transactions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_id TEXT,
            account_no TEXT,
            type TEXT, 
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
            created_at TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
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
            created_at TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
        )
    """)

    # Retrieval Accounts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS retrieval_accounts (
            account_no TEXT PRIMARY KEY,
            customer_id INTEGER,
            balance REAL DEFAULT 0.0,
            FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
        )
    """)

    # Chart of Accounts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chart_of_accounts (
            account_code TEXT PRIMARY KEY,
            account_name TEXT,
            account_type TEXT, 
            category TEXT
        )
    """)

    # Journal Vouchers Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS journal_vouchers (
            jv_id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_date TEXT,
            narration TEXT,
            status TEXT DEFAULT 'POSTED'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jv_entries (
            entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            jv_id INTEGER,
            account_code TEXT,
            debit REAL DEFAULT 0,
            credit REAL DEFAULT 0,
            FOREIGN KEY(jv_id) REFERENCES journal_vouchers(jv_id) ON DELETE CASCADE,
            FOREIGN KEY(account_code) REFERENCES chart_of_accounts(account_code)
        )
    """)

    # Income & Expense Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operational_finances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT, 
            customer_id INTEGER,
            account_code TEXT,
            amount REAL,
            mode TEXT,
            date TEXT,
            narration TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE SET NULL
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM chart_of_accounts")
    if cursor.fetchone()[0] == 0:
        default_accounts = [
            ("INC-101", "Loan Interest Income", "Income", "Primary Revenue"),
            ("INC-102", "Investment Income", "Income", "Primary Revenue"),
            ("INC-201", "Processing Fees", "Income", "Service Income"),
            ("INC-202", "Service Charges", "Income", "Service Income"),
            ("INC-203", "Commission Income", "Income", "Service Income"),
            ("INC-204", "Transaction Fees", "Income", "Service Income"),
            ("INC-301", "Miscellaneous Income", "Income", "Other Income"),
            ("EXP-101", "SB Interest Paid", "Expense", "Cost of Funds"),
            ("EXP-102", "FD Interest Paid", "Expense", "Cost of Funds"),
            ("EXP-103", "RD Interest Paid", "Expense", "Cost of Funds"),
            ("EXP-201", "Salaries & Benefits", "Expense", "Operating Expenses"),
            ("EXP-202", "Rent & Utilities", "Expense", "Operating Expenses"),
            ("EXP-203", "Electricity Charges", "Expense", "Operating Expenses"),
            ("EXP-301", "Printing & Stationary", "Expense", "Administrative Expenses"),
            ("EXP-401", "Bank Charges", "Expense", "Other Expenses"),
            ("AST-101", "Cash in Hand", "Asset", "Current Assets"),
            ("AST-102", "Bank Balance", "Asset", "Current Assets"),
            ("AST-103", "Retrieval Pool Account", "Asset", "Current Assets"),
            ("LIA-101", "SB Deposits Control", "Liability", "Deposits"),
            ("LIA-102", "FD Deposits Control", "Liability", "Deposits"),
            ("LIA-103", "RD Deposits Control", "Liability", "Deposits"),
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

def save_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

def post_automated_jv(narration, debit_acc, credit_acc, amount):
    if amount <= 0:
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", 
                   (str(date.today()), narration))
    jv_id = cursor.lastrowid
    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, debit_acc, amount))
    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, credit_acc, amount))
    conn.commit()
    conn.close()

def create_pdf_report(title, df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    clean_title = title.encode('ascii', 'ignore').decode('ascii')
    pdf.cell(0, 10, clean_title, 0, 1, "C")
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Aasha Nidhi Bank", 0, 1, "C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 10)
    if not df.empty:
        df_clean = df.copy()
        df_clean.columns = [str(col).replace('₹', 'Rs.').encode('ascii', 'ignore').decode('ascii') for col in df_clean.columns]
        for col in df_clean.columns:
            df_clean[col] = df_clean[col].astype(str).str.replace('₹', 'Rs.').str.encode('ascii', 'ignore').str.decode('ascii')

        cols = list(df_clean.columns)
        col_width = 190 / len(cols) if len(cols) > 0 else 190
        
        for col in cols:
            pdf.cell(col_width, 8, str(col)[:15], 1, 0, "C")
        pdf.ln()
        
        pdf.set_font("Arial", "", 9)
        for row in df_clean.itertuples(index=False):
            for val in row:
                pdf.cell(col_width, 6, str(val)[:20], 1, 0, "C")
            pdf.ln()
            
    return pdf.output(dest='S').encode('latin1', errors='ignore')

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("🏦 Aasha Nidhi Bank")
role = st.sidebar.selectbox("User Role", ["Admin/Staff", "Customer Portal"])

if role == "Admin/Staff":
    menu = st.sidebar.selectbox("Navigation", [
        "Dashboard", "Customer Management", "KYC Verification", "SB Accounts",
        "Fixed Deposits (FD)", "Recurring Deposits (RD)", "Retrieval Account",
        "Chart of Accounts", "Transactions", "Journal Vouchers", "Income & Expenses",
        "Interest Calculation", "Admin Record Editor", "Financial Statements (Trial/BS/PL)", "Reports"
    ])
else:
    menu = "Customer Portal"

# --- 1. DASHBOARD ---
if menu == "Dashboard":
    st.title("📊 Bank Dashboard & Portfolio Analytics")
    
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
    
    # Portfolio Visualization Charts
    st.subheader("📈 Deposit Portfolios Breakdown")
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.write("### Portfolio Distribution (₹)")
        portfolio_df = pd.DataFrame({
            "Deposit Type": ["Savings Bank (SB)", "Fixed Deposits (FD)", "Recurring Deposits (RD)"],
            "Total Amount (₹)": [total_sb_dep, total_fd, total_rd]
        })
        st.bar_chart(portfolio_df.set_index("Deposit Type"))

    with chart_col2:
        st.write("### Savings Accounts Balance Spread")
        sb_accounts_list = run_query("SELECT s.account_no, s.balance FROM sb_accounts s")
        if sb_accounts_list:
            df_sb_chart = pd.DataFrame(sb_accounts_list, columns=["Account No", "Balance"])
            st.line_chart(df_sb_chart.set_index("Account No"))
        else:
            st.info("No active SB account balances to plot.")

    st.markdown("---")
    st.subheader("Recent Activity Logs")
    recent_tx = run_query("SELECT tx_id, account_no, type, amount, mode, date FROM transactions ORDER BY id DESC LIMIT 5")
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
            adhar_num = col1.text_input("Aadhaar Number [Redacted Policy Active]")
            
            st.markdown("---")
            st.subheader("Document & Signature Uploads")
            adhar_upload = st.file_uploader("Upload Aadhaar Document", type=["pdf", "png", "jpg", "jpeg"])
            pan_upload = st.file_uploader("Upload PAN Card Document", type=["pdf", "png", "jpg", "jpeg"])
            sig_upload = st.file_uploader("Upload Signature", type=["png", "jpg", "jpeg"])
            
            submitted = st.form_submit_button("Register Customer")
            if submitted:
                if name and phone:
                    adhar_path = save_uploaded_file(adhar_upload)
                    pan_path = save_uploaded_file(pan_upload)
                    sig_path = save_uploaded_file(sig_upload)
                    
                    run_query("""
                        INSERT INTO customers (name, dob, gender, email, phone, street, city, state, pincode, pan, adhar, adhar_file, pan_file, signature_file, kyc_status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
                    """, (name, str(dob), gender, email, phone, street, city, state, pincode, pan, "[Redacted]", adhar_path, pan_path, sig_path, datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                    st.success(f"Customer {name} registered successfully!")
                else:
                    st.error("Please fill in mandatory fields: Name and Phone.")

    with tab2:
        st.subheader("Customer Directory")
        customers = run_query("SELECT id, name, phone, email, kyc_status, pan, created_at FROM customers")
        if customers:
            df_cust = pd.DataFrame(customers, columns=["ID", "Name", "Phone", "Email", "KYC Status", "PAN", "Joined"])
            st.dataframe(df_cust, use_container_width=True)
            
            col_csv, col_pdf = st.columns(2)
            col_csv.download_button("Download CSV Report", df_cust.to_csv(index=False).encode('utf-8'), "customers_report.csv", "text/csv")
            col_pdf.download_button("Download PDF Report", create_pdf_report("Customer Directory Report", df_cust), "customers_report.pdf", "application/pdf")
        else:
            st.info("No customers found.")

    with tab3:
        st.subheader("Edit Customer Information")
        cust_id_edit = st.number_input("Enter Customer ID to Edit", min_value=1, step=1, key="edit_cust_id")
        cust_data = run_query("SELECT name, email, phone, street, city, state, pincode, adhar_file, pan_file, signature_file FROM customers WHERE id=?", (cust_id_edit,))
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
    pending = run_query("SELECT id, name, phone, pan, adhar_file, pan_file, signature_file, created_at FROM customers WHERE kyc_status='PENDING'")
    if pending:
        for p in pending:
            with st.expander(f"Customer: {p[1]} (ID: {p[0]}) - Phone: {p[2]}"):
                st.write(f"**PAN:** {p[3]} | **Aadhaar File:** `{p[4]}` | **PAN File:** `{p[5]}` | **Signature:** `{p[6]}`")
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
    tab1, tab2, tab3 = st.tabs(["Open SB Account", "Transact (Deposit/Withdraw)", "View Accounts"])
    
    with tab1:
        customers = run_query("SELECT id, name FROM customers")
        if customers:
            cust_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers}
            selected_cust = st.selectbox("Select Customer Name", list(cust_dict.keys()))
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
                    post_automated_jv(f"SB Opening Balance - Account {acc_no}", "AST-101", "LIA-101", init_bal)

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
                    
                    if tx_type == "DEPOSIT":
                        post_automated_jv(f"SB Deposit: {narration} ({acc_choice})", "AST-101", "LIA-101", amount)
                    else:
                        post_automated_jv(f"SB Withdrawal: {narration} ({acc_choice})", "LIA-101", "AST-101", amount)

                    st.success(f"Transaction successful! New Balance: ₹{new_bal:,.2f}")
        else:
            st.info("No active SB accounts found.")

    with tab3:
        st.subheader("Active SB Accounts Directory")
        accounts = run_query("""
            SELECT s.account_no, c.name, s.balance, s.interest_rate, s.created_at 
            FROM sb_accounts s JOIN customers c ON s.customer_id = c.id
        """)
        if accounts:
            df_sb = pd.DataFrame(accounts, columns=["Account No", "Customer Name", "Balance (₹)", "Interest Rate (%)", "Created"])
            st.dataframe(df_sb, use_container_width=True)
            st.download_button("Download SB Accounts PDF", create_pdf_report("Savings Bank Accounts Report", df_sb), "sb_accounts.pdf", "application/pdf")
        else:
            st.info("No active SB accounts found.")

# --- 5. FIXED DEPOSITS (FD) ---
elif menu == "Fixed Deposits (FD)":
    st.title("📈 Fixed Deposits Management")
    tab1, tab2 = st.tabs(["Open FD", "Active FDs & Closure"])
    
    with tab1:
        customers = run_query("SELECT id, name FROM customers")
        if customers:
            cust_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers}
            selected_cust = st.selectbox("Select Customer Name for FD", list(cust_dict.keys()), key="fd_cust")
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
                
                post_automated_jv(f"Fixed Deposit Opening - Principal ₹{principal}", "AST-101", "LIA-102", principal)
                st.success("Fixed Deposit opened successfully!")
        else:
            st.warning("Register a customer first.")

    with tab2:
        fds = run_query("""
            SELECT f.fd_id, c.name, f.principal, f.tenure_months, f.interest_rate, f.maturity_amount, f.status, f.customer_id
            FROM fixed_deposits f JOIN customers c ON f.customer_id = c.id
        """)
        if fds:
            cleaned_fds = [row[:-1] if len(row) > 7 else row for row in fds]
            df_fds = pd.DataFrame(cleaned_fds, columns=["FD ID", "Customer", "Principal (₹)", "Tenure (M)", "Rate (%)", "Maturity (₹)", "Status"])
            st.dataframe(df_fds, use_container_width=True)
            
            st.markdown("---")
            st.subheader("Close / Settle FD Account")
            active_fds = [f for f in fds if f[6] == 'ACTIVE']
            if active_fds:
                fd_choice = st.selectbox("Select Active FD ID to Close/Settle", [f[0] for f in active_fds])
                selected_fd_record = next(f for f in fds if f[0] == fd_choice)
                
                cust_id = selected_fd_record[7]
                maturity_amt = selected_fd_record[5]
                
                if st.button("Close & Settle FD Account"):
                    run_query("UPDATE fixed_deposits SET status='CLOSED' WHERE fd_id=?", (fd_choice,), fetch=False)
                    post_automated_jv(f"FD Closure Settlement (FD #{fd_choice})", "LIA-102", "AST-101", maturity_amt)
                    st.success(f"FD #{fd_choice} successfully closed and settled for ₹{maturity_amt:,.2f}!")
                    st.rerun()
            else:
                st.info("No active FDs available for settlement.")
        else:
            st.info("No fixed deposits found.")

# --- 6. RECURRING DEPOSITS (RD) ---
elif menu == "Recurring Deposits (RD)":
    st.title("🔄 Recurring Deposits Management")
    tab1, tab2, tab3 = st.tabs(["Open RD", "Pay Installment", "View RDs"])
    
    with tab1:
        customers = run_query("SELECT id, name FROM customers")
        if customers:
            cust_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers}
            selected_cust = st.selectbox("Select Customer Name for RD", list(cust_dict.keys()), key="rd_cust")
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
        st.subheader("Pay Monthly Installment")
        active_rds = run_query("""
            SELECT r.rd_id, c.name, r.monthly_amount, r.tenure_months, r.installments_paid 
            FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id 
            WHERE r.status='ACTIVE'
        """)
        if active_rds:
            rd_dict = {f"RD ID: {r[0]} - {r[1]} (Monthly: ₹{r[2]:,.2f}, Paid: {r[4]}/{r[3]})": r for r in active_rds}
            chosen_rd_str = st.selectbox("Select Active RD Account", list(rd_dict.keys()))
            selected_rd = rd_dict[chosen_rd_str]
            rd_id, cust_name, monthly_amt, tenure_m, paid_inst = selected_rd
            
            if st.button("Confirm & Pay Installment"):
                if paid_inst < tenure_m:
                    new_paid = paid_inst + 1
                    run_query("UPDATE recurring_deposits SET installments_paid=? WHERE rd_id=?", (new_paid, rd_id), fetch=False)
                    post_automated_jv(f"RD Installment Paid - RD #{rd_id} (Inst #{new_paid})", "AST-101", "LIA-103", monthly_amt)
                    st.success(f"Installment #{new_paid} successfully paid!")
                    st.rerun()
                else:
                    st.warning("All installments completed!")
        else:
            st.info("No active RDs found.")

    with tab3:
        rds = run_query("""
            SELECT r.rd_id, c.name, r.monthly_amount, r.tenure_months, r.interest_rate, r.installments_paid, r.status
            FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id
        """)
        if rds:
            df_rds = pd.DataFrame(rds, columns=["RD ID", "Customer", "Monthly (₹)", "Tenure (M)", "Rate (%)", "Paid Installments", "Status"])
            st.dataframe(df_rds, use_container_width=True)
        else:
            st.info("No recurring deposits found.")

# --- 7. RETRIEVAL ACCOUNT ---
elif menu == "Retrieval Account":
    st.title("💰 Retrieval Account Pool")
    ret_accs = run_query("""
        SELECT r.account_no, c.name, r.balance 
        FROM retrieval_accounts r JOIN customers c ON r.customer_id = c.id
    """)
    if ret_accs:
        df_ret = pd.DataFrame(ret_accs, columns=["Retrieval Account No", "Customer Name", "Balance (₹)"])
        st.dataframe(df_ret, use_container_width=True)
    else:
        st.info("No funds currently resting in the Retrieval Accounts pool.")

# --- 8. CHART OF ACCOUNTS ---
elif menu == "Chart of Accounts":
    st.title("📊 Financial Chart of Accounts")
    accounts = run_query("SELECT account_code, account_name, account_type, category FROM chart_of_accounts")
    df_coa = pd.DataFrame(accounts, columns=["Account Code", "Account Name", "Account Type", "Category"])
    st.dataframe(df_coa, use_container_width=True)

# --- 9. TRANSACTIONS ---
elif menu == "Transactions":
    st.title("💳 Transaction Ledger")
    txs = run_query("SELECT id, tx_id, account_no, type, amount, mode, narration, date FROM transactions ORDER BY id DESC")
    if txs:
        df_all_tx = pd.DataFrame(txs, columns=["ID", "Tx ID", "Account No", "Type", "Amount (₹)", "Mode", "Narration", "Date"])
        st.dataframe(df_all_tx, use_container_width=True)
    else:
        st.info("No transaction logs recorded.")

# --- 10. JOURNAL VOUCHERS ---
elif menu == "Journal Vouchers":
    st.title("📝 Journal Vouchers Ledger")
    jvs = run_query("SELECT jv_id, voucher_date, narration, status FROM journal_vouchers")
    if jvs:
        df_jvs = pd.DataFrame(jvs, columns=["JV ID", "Date", "Narration", "Status"])
        st.dataframe(df_jvs, use_container_width=True)
    else:
        st.info("No journal vouchers found.")

# --- 11. INCOME & EXPENSES ---
elif menu == "Income & Expenses":
    st.title("💰 Operational Income & Expenses")
    finances = run_query("""
        SELECT o.id, o.type, c.name, o.account_code, o.amount, o.mode, o.date, o.narration 
        FROM operational_finances o LEFT JOIN customers c ON o.customer_id = c.id
    """)
    if finances:
        df_fin = pd.DataFrame(finances, columns=["ID", "Type", "Customer Name", "Account Code", "Amount (₹)", "Mode", "Date", "Narration"])
        st.dataframe(df_fin, use_container_width=True)
    else:
        st.info("No operational financial logs recorded.")

# --- 12. INTEREST CALCULATION ---
elif menu == "Interest Calculation":
    st.title("📊 Interest Calculation & Posting")
    sb_records = run_query("""
        SELECT s.account_no, c.name, s.balance, s.interest_rate 
        FROM sb_accounts s JOIN customers c ON s.customer_id = c.id
    """)
    if sb_records:
        df_sb_calc = pd.DataFrame(sb_records, columns=["Account No", "Customer", "Balance", "Rate (%)"])
        st.dataframe(df_sb_calc, use_container_width=True)
    else:
        st.info("No accounts available.")

# --- 13. ADMIN RECORD EDITOR ---
elif menu == "Admin Record Editor":
    st.title("🛠️ Database Record Editor")
    tables_res = run_query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    table_list = [t[0] for t in tables_res]
    selected_table = st.selectbox("Select Database Table to Inspect", table_list)
    if selected_table:
        rows = run_query(f"SELECT * FROM {selected_table}")
        columns_info = run_query(f"PRAGMA table_info({selected_table})")
        df_table = pd.DataFrame(rows, columns=[col[1] for col in columns_info])
        st.dataframe(df_table, use_container_width=True)

# --- 14. FINANCIAL STATEMENTS ---
elif menu == "Financial Statements (Trial/BS/PL)":
    st.title("⚖️ Financial Statements & Reports")
    tab1, tab2, tab3 = st.tabs(["Trial Balance", "Balance Sheet", "Profit & Loss Statement"])
    
    with tab1:
        st.subheader("Trial Balance Summary")
        entries = run_query("""
            SELECT JE.account_code, CO.account_name, SUM(JE.debit), SUM(JE.credit)
            FROM jv_entries JE JOIN chart_of_accounts CO ON JE.account_code = CO.account_code
            GROUP BY JE.account_code
        """)
        if entries:
            df_tb = pd.DataFrame(entries, columns=["Account Code", "Account Name", "Total Debit (₹)", "Total Credit (₹)"])
            st.dataframe(df_tb, use_container_width=True)
            st.download_button("Download Trial Balance PDF", create_pdf_report("Trial Balance Statement", df_tb), "trial_balance.pdf", "application/pdf")
        else:
            st.info("No entries recorded yet.")

    with tab2:
        st.subheader("Balance Sheet (Assets, Liabilities & Equity)")
        tot_sb_assets = run_query("SELECT SUM(balance) FROM sb_accounts")[0][0] or 0.0
        tot_fd_liabilities = run_query("SELECT SUM(principal) FROM fixed_deposits WHERE status='ACTIVE'")[0][0] or 0.0
        tot_rd_liabilities = run_query("SELECT SUM(monthly_amount * installments_paid) FROM recurring_deposits WHERE status='ACTIVE'")[0][0] or 0.0
        
        total_customer_funds = tot_sb_assets + tot_fd_liabilities + tot_rd_liabilities
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Assets")
            cash_in_hand = st.number_input("Vault Cash / Physical Currency (₹)", value=float(total_customer_funds), step=1000.0)
            loans_advances = st.number_input("Loans & Advances Receivable (₹)", value=0.0, step=1000.0)
            total_assets = cash_in_hand + loans_advances
            st.metric("Total Asset Holdings", f"₹{total_assets:,.2f}")
            
        with col2:
            st.markdown("### Liabilities & Equity")
            sb_deposits_liab = st.number_input("Savings Bank (SB) Deposits Control (₹)", value=tot_sb_assets, step=1000.0)
            fd_deposits_liab = st.number_input("Fixed Deposits (FD) Control (₹)", value=tot_fd_liabilities, step=1000.0)
            rd_deposits_liab = st.number_input("Recurring Deposits (RD) Control (₹)", value=tot_rd_liabilities, step=1000.0)
            capital_equity = st.number_input("Capital & Reserves (₹)", value=0.0, step=1000.0)
            total_liabilities = sb_deposits_liab + fd_deposits_liab + rd_deposits_liab + capital_equity
            st.metric("Total Liabilities & Equity", f"₹{total_liabilities:,.2f}")
            
        st.markdown("---")
        diff = total_assets - total_liabilities
        if abs(diff) < 0.01:
            st.success("Balance Sheet Perfectly Balanced!")
        else:
            st.warning(f"Balance Sheet Discrepancy / Difference: ₹{diff:,.2f}")

        if st.button("Export Balance Sheet Report"):
            bs_data = [
                ["Assets Section", "Amount (₹)"],
                ["Vault Cash / Physical Currency", cash_in_hand],
                ["Total Assets", total_assets],
                ["Liabilities & Equity", "Amount (₹)"],
                ["SB Deposits Control", sb_deposits_liab],
                ["FD Deposits Control", fd_deposits_liab],
                ["RD Deposits Control", rd_deposits_liab],
                ["Total Liabilities & Equity", total_liabilities]
            ]
            df_bs = pd.DataFrame(bs_data[1:], columns=bs_data[0])
            st.download_button("Download Balance Sheet PDF", create_pdf_report("Balance Sheet Statement", df_bs), "balance_sheet.pdf", "application/pdf")

    with tab3:
        st.subheader("Profit & Loss Statement")
        total_income = run_query("SELECT SUM(amount) FROM operational_finances WHERE type='INCOME'")[0][0] or 0.0
        total_expense = run_query("SELECT SUM(amount) FROM operational_finances WHERE type='EXPENSE'")[0][0] or 0.0
        net_pl = total_income - total_expense
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"₹{total_income:,.2f}")
        col2.metric("Total Expenses", f"₹{total_expense:,.2f}")
        col3.metric("Net Profit / Loss", f"₹{net_pl:,.2f}")

# --- 15. REPORTS ---
elif menu == "Reports":
    st.title("📄 Comprehensive Bank Reports Center")
    report_type = st.selectbox("Select Report to Generate", [
        "Customer List Report", "Daily Transactions Report", "FD Summary Report", "RD Summary Report"
    ])
    if st.button("Generate Report"):
        if "Customer" in report_type:
            data = run_query("SELECT id, name, phone, email, kyc_status, created_at FROM customers")
            df = pd.DataFrame(data, columns=["ID", "Name", "Phone", "Email", "KYC Status", "Joined"])
        elif "Transaction" in report_type:
            data = run_query("SELECT tx_id, account_no, type, amount, mode, date FROM transactions")
            df = pd.DataFrame(data, columns=["Tx ID", "Account No", "Type", "Amount", "Mode", "Date"])
        elif "FD" in report_type:
            data = run_query("SELECT f.fd_id, c.name, f.principal, f.maturity_amount, f.status FROM fixed_deposits f JOIN customers c ON f.customer_id = c.id")
            df = pd.DataFrame(data, columns=["FD ID", "Customer Name", "Principal", "Maturity", "Status"])
        else:
            data = run_query("SELECT r.rd_id, c.name, r.monthly_amount, r.installments_paid, r.status FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id")
            df = pd.DataFrame(data, columns=["RD ID", "Customer Name", "Monthly", "Paid", "Status"])
            
        st.dataframe(df, use_container_width=True)
        st.download_button("Download PDF Report", create_pdf_report(report_type, df), f"{report_type.lower().replace(' ', '_')}.pdf", "application/pdf")

# --- 16. CUSTOMER PORTAL & LOGIN ---
elif menu == "Customer Portal":
    st.title("🔐 Customer Portal & Account Statement Generator")
    
    # Secure Login Box
    st.markdown("### Secure Customer Login")
    with st.form("customer_login_form"):
        login_cust_id = st.number_input("Customer ID", min_value=1, step=1)
        login_phone = st.text_input("Registered Phone Number", type="password")
        login_submitted = st.form_submit_button("Login to Portal")
        
    if login_submitted:
        auth_check = run_query("SELECT id, name, phone, kyc_status FROM customers WHERE id=? AND phone=?", (login_cust_id, login_phone))
        if auth_check:
            st.session_state['authenticated_customer'] = auth_check[0]
            st.success(f"Login successful! Welcome back, {auth_check[0][1]}.")
        else:
            st.error("Invalid Customer ID or Phone Number combination.")

    # Render Customer Dashboard if Authenticated
    if 'authenticated_customer' in st.session_state:
        cust_id, name, phone, kyc = st.session_state['authenticated_customer']
        
        st.markdown("---")
        st.subheader(f"Welcome, {name} (Customer ID: {cust_id})")
        st.write(f"**KYC Verification Status:** `{kyc}` | **Phone:** {phone}")
        
        # Container for All Customer Accounts
        st.markdown("### 🏦 Your Active Accounts & Portfolios")
        
        # 1. Savings Accounts
        sb_accs = run_query("SELECT account_no, balance, interest_rate, created_at FROM sb_accounts WHERE customer_id=?", (cust_id,))
        if sb_accs:
            st.write("#### Savings Bank (SB) Accounts")
            df_cust_sb = pd.DataFrame(sb_accs, columns=["Account No", "Balance (₹)", "Interest Rate (%)", "Opened Date"])
            st.dataframe(df_cust_sb, use_container_width=True)
            
        # 2. Fixed Deposits
        fd_accs = run_query("SELECT fd_id, principal, tenure_months, interest_rate, maturity_amount, status FROM fixed_deposits WHERE customer_id=?", (cust_id,))
        if fd_accs:
            st.write("#### Fixed Deposits (FD)")
            df_cust_fd = pd.DataFrame(fd_accs, columns=["FD ID", "Principal (₹)", "Tenure (M)", "Rate (%)", "Maturity (₹)", "Status"])
            st.dataframe(df_cust_fd, use_container_width=True)

        # 3. Recurring Deposits
        rd_accs = run_query("SELECT rd_id, monthly_amount, tenure_months, interest_rate, installments_paid, status FROM recurring_deposits WHERE customer_id=?", (cust_id,))
        if rd_accs:
            st.write("#### Recurring Deposits (RD)")
            df_cust_rd = pd.DataFrame(rd_accs, columns=["RD ID", "Monthly (₹)", "Tenure (M)", "Rate (%)", "Installments Paid", "Status"])
            st.dataframe(df_cust_rd, use_container_width=True)

        # 4. Retrieval Pool Account
        ret_accs = run_query("SELECT account_no, balance FROM retrieval_accounts WHERE customer_id=?", (cust_id,))
        if ret_accs:
            st.write("#### Retrieval Pool Accounts")
            df_cust_ret = pd.DataFrame(ret_accs, columns=["Account No", "Balance (₹)"])
            st.dataframe(df_cust_ret, use_container_width=True)

        st.markdown("---")
        st.subheader("📥 Download Consolidated Account Statement")
        if st.button("Generate Consolidated Statement PDF"):
            # Consolidate user data into a clean report format
            statement_data = []
            if sb_accs:
                for a in sb_accs:
                    statement_data.append(["Savings Account", a[0], f"Balance: Rs. {a[1]:,.2f}"])
            if fd_accs:
                for f in fd_accs:
                    statement_data.append(["Fixed Deposit", f"FD #{f[0]}", f"Principal: Rs. {f[1]:,.2f} | Maturity: Rs. {f[4]:,.2f}"])
            if rd_accs:
                for r in rd_accs:
                    statement_data.append(["Recurring Deposit", f"RD #{r[0]}", f"Monthly: Rs. {r[1]:,.2f} | Paid: {r[4]}/{r[2]}"])
            
            if statement_data:
                df_statement = pd.DataFrame(statement_data, columns=["Account Type", "Identifier", "Details"])
                st.download_button(
                    "Download Statement PDF Report", 
                    create_pdf_report(f"Consolidated Statement - {name}", df_statement), 
                    f"statement_{cust_id}.pdf", 
                    "application/pdf"
                )
            else:
                st.info("No accounts available to export.")
                
        if st.button("Logout"):
            del st.session_state['authenticated_customer']
            st.rerun()
