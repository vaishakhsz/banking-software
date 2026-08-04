import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import io
from fpdf import FPDF
import os
import plotly.express as px
import time

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
    """Get database connection with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            db_dir = os.path.dirname(DB_NAME)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            return sqlite3.connect(DB_NAME, check_same_thread=False, timeout=10)
        except sqlite3.OperationalError as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(1)

def init_db():
    """Initialize database with all required tables only if they don't exist"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Create all tables
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS retrieval_accounts (
                account_no TEXT PRIMARY KEY,
                customer_id INTEGER,
                balance REAL DEFAULT 0.0,
                FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chart_of_accounts (
                account_code TEXT PRIMARY KEY,
                account_name TEXT,
                account_type TEXT, 
                category TEXT
            )
        """)

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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cash_book (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                voucher_no TEXT,
                particulars TEXT,
                debit_amount REAL DEFAULT 0,
                credit_amount REAL DEFAULT 0,
                balance REAL DEFAULT 0,
                account_code TEXT,
                narration TEXT,
                created_at TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bank_book (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                voucher_no TEXT,
                particulars TEXT,
                debit_amount REAL DEFAULT 0,
                credit_amount REAL DEFAULT 0,
                balance REAL DEFAULT 0,
                bank_name TEXT,
                account_code TEXT,
                narration TEXT,
                created_at TEXT
            )
        """)

        # Preload Chart of Accounts with strict separation
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
                ("AST-102", "Union Bank of India", "Asset", "Current Assets"),
                ("AST-103", "State Bank of India", "Asset", "Current Assets"),
                ("AST-104", "Retrieval Pool Account", "Asset", "Current Assets"),
                ("LIA-101", "SB Deposits Control", "Liability", "Deposits"),
                ("LIA-102", "FD Deposits Control", "Liability", "Deposits"),
                ("LIA-103", "RD Deposits Control", "Liability", "Deposits"),
                ("EQT-101", "Capital Account", "Equity", "Capital"),
                ("EQT-102", "Retained Earnings", "Equity", "Reserves"),
                ("EQT-103", "Income Summary", "Equity", "Temporary")
            ]
            cursor.executemany("INSERT OR IGNORE INTO chart_of_accounts VALUES (?, ?, ?, ?)", default_accounts)

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database initialization error: {str(e)}")
        return False

# --- INITIALIZE DATABASE PERSISTENTLY ---
init_db()

def run_query(query, params=(), fetch=True):
    """Execute a database query with error handling"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        res = cursor.fetchall() if fetch else None
        conn.commit()
        conn.close()
        return res
    except sqlite3.OperationalError as e:
        st.error(f"Database error: {str(e)}")
        return None

# --- HELPER FUNCTIONS ---
def save_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

def get_cash_balance():
    try:
        result = run_query("SELECT balance FROM cash_book ORDER BY id DESC LIMIT 1")
        return result[0][0] if result else 0
    except:
        return 0

def get_bank_balance(bank_name=None):
    try:
        if bank_name:
            result = run_query("SELECT balance FROM bank_book WHERE bank_name = ? ORDER BY id DESC LIMIT 1", (bank_name,))
        else:
            result = run_query("SELECT balance FROM bank_book ORDER BY id DESC LIMIT 1")
        return result[0][0] if result else 0
    except:
        return 0

def generate_cash_voucher_no():
    today = datetime.now().strftime("%Y%m%d")
    try:
        result = run_query("SELECT voucher_no FROM cash_book WHERE voucher_no LIKE ? ORDER BY id DESC LIMIT 1", (f"CB{today}%",))
        if result:
            last_seq = int(result[0][0][-4:])
            new_seq = last_seq + 1
        else:
            new_seq = 1
    except:
        new_seq = 1
    return f"CB{today}{new_seq:04d}"

def generate_bank_voucher_no():
    today = datetime.now().strftime("%Y%m%d")
    try:
        result = run_query("SELECT voucher_no FROM bank_book WHERE voucher_no LIKE ? ORDER BY id DESC LIMIT 1", (f"BB{today}%",))
        if result:
            last_seq = int(result[0][0][-4:])
            new_seq = last_seq + 1
        else:
            new_seq = 1
    except:
        new_seq = 1
    return f"BB{today}{new_seq:04d}"

def post_automated_jv(narration, debit_acc, credit_acc, amount):
    if amount <= 0:
        return
    try:
        debit_check = run_query("SELECT account_code FROM chart_of_accounts WHERE account_code = ?", (debit_acc,))
        credit_check = run_query("SELECT account_code FROM chart_of_accounts WHERE account_code = ?", (credit_acc,))
        
        if not debit_check or not credit_check:
            return
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", (str(date.today()), narration))
        jv_id = cursor.lastrowid
        cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, debit_acc, amount))
        cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, credit_acc, amount))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error posting journal voucher: {str(e)}")

def create_pdf_report(title, df):
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#1f4e78'), spaceAfter=12)
    
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 10))
    
    if not df.empty:
        cleaned_data = []
        columns = list(df.columns)
        
        for row in df.values:
            cleaned_row = []
            for val in row:
                val_str = str(val) if val is not None else ""
                val_str = val_str.replace('₹', 'Rs.')
                ascii_val = val_str.encode('ascii', 'ignore').decode('ascii')
                cleaned_row.append(ascii_val)
            cleaned_data.append(cleaned_row)
            
        table_data = [columns] + cleaned_data
        col_width = 550 / max(1, len(columns))
        t = Table(table_data, colWidths=[col_width] * len(columns))
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4e78')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f9f9f9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph("No records found for this report.", styles['Normal']))
        
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("🏦 Aasha Nidhi Bank")
role = st.sidebar.selectbox("User Role", ["Admin/Staff", "Customer Portal"])

if role == "Admin/Staff":
    menu = st.sidebar.selectbox("Navigation", [
        "Dashboard", "Customer Management", "KYC Verification", "SB Accounts",
        "Fixed Deposits (FD)", "Recurring Deposits (RD)", "Retrieval Account",
        "Chart of Accounts", "Cash Book", "Bank Book", "Journal Vouchers",
        "Admin Record Editor", "Financial Statements (Trial/BS/PL)", "Reports"
    ])
else:
    menu = "Customer Portal"

# --- DASHBOARD ---
if menu == "Dashboard":
    st.title("📊 Bank Dashboard & Overview")
    
    total_cust = run_query("SELECT COUNT(*) FROM customers")[0][0] if run_query("SELECT COUNT(*) FROM customers") else 0
    kyc_pending = run_query("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'")[0][0] if run_query("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'") else 0
    sb_count = run_query("SELECT COUNT(*) FROM sb_accounts")[0][0] if run_query("SELECT COUNT(*) FROM sb_accounts") else 0
    total_sb_dep = run_query("SELECT SUM(balance) FROM sb_accounts")[0][0] or 0.0
    total_fd = run_query("SELECT SUM(principal) FROM fixed_deposits WHERE status='ACTIVE'")[0][0] or 0.0
    total_rd = run_query("SELECT SUM(monthly_amount * installments_paid) FROM recurring_deposits WHERE status='ACTIVE'")[0][0] or 0.0
    cash_balance = get_cash_balance()
    bank_balance = get_bank_balance()

    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    col1.metric("Total Customers", total_cust, f"Pending KYC: {kyc_pending}")
    col2.metric("SB Accounts Active", sb_count, f"Balance: ₹{total_sb_dep:,.2f}")
    col3.metric("Active FD Portfolio", f"₹{total_fd:,.2f}")
    col4.metric("Active RD Portfolio", f"₹{total_rd:,.2f}")
    col5.metric("Cash Balance", f"₹{cash_balance:,.2f}")
    col6.metric("Bank Balance", f"₹{bank_balance:,.2f}")
    col7.metric("Total SB Deposits", f"₹{total_sb_dep:,.2f}")

# --- CUSTOMER MANAGEMENT ---
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
            
            st.markdown("---")
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

# --- KYC VERIFICATION ---
elif menu == "KYC Verification":
    st.title("✅ KYC Verification Panel")
    pending = run_query("SELECT id, name, phone, pan, adhar_file, pan_file, signature_file, created_at FROM customers WHERE kyc_status='PENDING'")
    if pending:
        for p in pending:
            with st.expander(f"Customer: {p[1]} (ID: {p[0]}) - Phone: {p[2]}"):
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

# --- SB ACCOUNTS ---
elif menu == "SB Accounts":
    st.title("💰 Savings Bank (SB) Management")
    tab1, tab2, tab3 = st.tabs(["Open SB Account", "Transact", "View Accounts"])
    
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

# --- FIXED DEPOSITS ---
elif menu == "Fixed Deposits (FD)":
    st.title("📈 Fixed Deposits Management")
    tab1, tab2 = st.tabs(["Open FD", "Active FDs"])
    
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
                st.success("Fixed Deposit opened & recorded successfully!")
        else:
            st.warning("Register a customer first.")

    with tab2:
        fds = run_query("""
            SELECT f.fd_id, c.name, f.principal, f.tenure_months, f.interest_rate, f.maturity_amount, f.status
            FROM fixed_deposits f JOIN customers c ON f.customer_id = c.id
        """)
        if fds:
            df_fds = pd.DataFrame(fds, columns=["FD ID", "Customer", "Principal (₹)", "Tenure (M)", "Rate (%)", "Maturity (₹)", "Status"])
            st.dataframe(df_fds, use_container_width=True)
            st.download_button("Download FDs PDF Report", create_pdf_report("Fixed Deposits Report", df_fds), "fixed_deposits.pdf", "application/pdf")
        else:
            st.info("No fixed deposits found.")

# --- RECURRING DEPOSITS ---
elif menu == "Recurring Deposits (RD)":
    st.title("🔄 Recurring Deposits Management")
    tab1, tab2, tab3 = st.tabs(["Open RD", "Pay Installment", "Active RDs"])
    
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
            st.info("No active recurring deposits found.")

    with tab3:
        rds = run_query("""
            SELECT r.rd_id, c.name, r.monthly_amount, r.tenure_months, r.interest_rate, r.installments_paid, r.status
            FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id
        """)
        if rds:
            df_rds = pd.DataFrame(rds, columns=["RD ID", "Customer", "Monthly (₹)", "Tenure (M)", "Rate (%)", "Paid Installments", "Status"])
            st.dataframe(df_rds, use_container_width=True)

# --- RETRIEVAL ACCOUNT ---
elif menu == "Retrieval Account":
    st.title("💰 Matured Deposits Retrieval Account")
    ret_accs = run_query("""
        SELECT r.account_no, c.name, r.balance 
        FROM retrieval_accounts r JOIN customers c ON r.customer_id = c.id
    """)
    if ret_accs:
        df_ret = pd.DataFrame(ret_accs, columns=["Retrieval Account No", "Customer Name", "Balance (₹)"])
        st.dataframe(df_ret, use_container_width=True)
    else:
        st.write("No funds currently resting in the Retrieval Accounts pool.")

# --- CHART OF ACCOUNTS ---
elif menu == "Chart of Accounts":
    st.title("📊 Financial Chart of Accounts")
    accounts = run_query("SELECT account_code, account_name, account_type, category FROM chart_of_accounts")
    df_coa = pd.DataFrame(accounts, columns=["Account Code", "Account Name", "Account Type", "Category"])
    st.dataframe(df_coa, use_container_width=True)

# --- CASH BOOK ---
elif menu == "Cash Book":
    st.title("💰 Cash Book Entries")
    tab1, tab2, tab3, tab4 = st.tabs(["Record Entry", "View / Delete", "Edit Entry", "Print Book"])
    
    with tab1:
        current_balance = get_cash_balance()
        st.info(f"💰 **Current Cash Balance:** ₹{current_balance:,.2f}")
        
        with st.form("cash_entry_form"):
            col1, col2 = st.columns(2)
            entry_type = col1.selectbox("Transaction Type", ["DEBIT (Receipt)", "CREDIT (Payment)"])
            amount = col2.number_input("Amount (₹)", min_value=1.0, value=100.0, step=100.0)
            particulars = st.text_input("Particulars / Description")
            
            coa_list = run_query("SELECT account_code, account_name FROM chart_of_accounts")
            coa_dict = {f"{c[0]} - {c[1]}": c[0] for c in coa_list}
            account_head = st.selectbox("Corresponding Account Head", list(coa_dict.keys()))
            narration = st.text_area("Narration", height=68)
            
            if st.form_submit_button("Record Cash Entry"):
                if amount > 0 and particulars and account_head:
                    voucher_no = generate_cash_voucher_no()
                    today = datetime.now().strftime("%Y-%m-%d")
                    account_code = coa_dict[account_head]
                    
                    if entry_type == "DEBIT (Receipt)":
                        new_balance = current_balance + amount
                        debit_amount, credit_amount = amount, 0
                        post_automated_jv(f"Cash Receipt: {particulars}", "AST-101", account_code, amount)
                    else:
                        if current_balance < amount:
                            st.error(f"❌ Insufficient Cash Balance! Available: ₹{current_balance:,.2f}")
                            st.stop()
                        new_balance = current_balance - amount
                        debit_amount, credit_amount = 0, amount
                        post_automated_jv(f"Cash Payment: {particulars}", account_code, "AST-101", amount)
                    
                    run_query("""
                        INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (today, voucher_no, particulars, debit_amount, credit_amount, new_balance, account_code, narration, datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                    
                    st.success(f"✅ Cash entry recorded successfully! Voucher: {voucher_no}")
                    st.rerun()

    with tab2:
        entries = run_query("SELECT id, date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration FROM cash_book ORDER BY id DESC")
        if entries:
            df_cash = pd.DataFrame(entries, columns=["ID", "Date", "Voucher No", "Particulars", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Account Code", "Narration"])
            st.dataframe(df_cash, use_container_width=True)
            
            del_id = st.number_input("Enter Cash Entry ID to Delete", min_value=1, step=1, key="del_cash_id")
            if st.button("Delete Cash Entry"):
                run_query("DELETE FROM cash_book WHERE id=?", (del_id,), fetch=False)
                st.warning(f"Cash Entry ID {del_id} deleted successfully.")
                st.rerun()
        else:
            st.info("No cash book entries found.")

    with tab3:
        st.subheader("Edit Existing Cash Entry")
        edit_id = st.number_input("Enter Cash Entry ID to Edit", min_value=1, step=1, key="edit_cash_id_input")
        entry_to_edit = run_query("SELECT id, particulars, debit_amount, credit_amount, narration FROM cash_book WHERE id=?", (edit_id,))
        
        if entry_to_edit:
            row = entry_to_edit[0]
            with st.form("edit_cash_form"):
                new_part = st.text_input("Particulars", value=row[1])
                curr_dr = row[2] if row[2] > 0 else row[3]
                is_debit = row[2] > 0
                new_type = st.selectbox("Type", ["DEBIT (Receipt)", "CREDIT (Payment)"], index=0 if is_debit else 1)
                new_amt = st.number_input("Amount (₹)", min_value=1.0, value=float(curr_dr))
                new_narration = st.text_area("Narration", value=row[4] if row[4] else "")
                
                if st.form_submit_button("Update Cash Entry"):
                    d_amt = new_amt if "DEBIT" in new_type else 0.0
                    c_amt = new_amt if "CREDIT" in new_type else 0.0
                    run_query("""
                        UPDATE cash_book 
                        SET particulars = ?, debit_amount = ?, credit_amount = ?, narration = ? 
                        WHERE id = ?
                    """, (new_part, d_amt, c_amt, new_narration, edit_id), fetch=False)
                    st.success(f"Cash Entry ID {edit_id} updated successfully!")
                    st.rerun()
        else:
            st.info("Enter a valid Cash Entry ID above to load and edit.")

    with tab4:
        entries = run_query("SELECT date, voucher_no, particulars, debit_amount, credit_amount, balance, narration FROM cash_book ORDER BY id ASC")
        if entries:
            df_print = pd.DataFrame(entries, columns=["Date", "Voucher No", "Particulars", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Narration"])
            st.dataframe(df_print, use_container_width=True)
            st.download_button("Download Cash Book PDF", create_pdf_report("Cash Book Report", df_print), "cash_book.pdf", "application/pdf")

# --- BANK BOOK ---
elif menu == "Bank Book":
    st.title("🏦 Bank Book Entries")
    tab1, tab2, tab3, tab4 = st.tabs(["Record Entry", "View / Delete", "Edit Entry", "Print Book"])
    
    with tab1:
        bank_accounts = run_query("SELECT account_name FROM chart_of_accounts WHERE account_type = 'Asset' AND account_name LIKE '%Bank%'")
        bank_list = [b[0] for b in bank_accounts] if bank_accounts else ["Union Bank of India", "State Bank of India"]
        selected_bank = st.selectbox("Select Bank", bank_list, key="bank_select")
        
        current_balance = get_bank_balance(selected_bank)
        st.info(f"🏦 **{selected_bank} Current Balance:** ₹{current_balance:,.2f}")
        
        with st.form("bank_entry_form"):
            col1, col2 = st.columns(2)
            entry_type = col1.selectbox("Transaction Type", ["DEBIT (Deposit)", "CREDIT (Withdrawal)"])
            amount = col2.number_input("Amount (₹)", min_value=1.0, value=100.0, step=100.0)
            particulars = st.text_input("Particulars / Description")
            
            coa_list = run_query("SELECT account_code, account_name FROM chart_of_accounts")
            coa_dict = {f"{c[0]} - {c[1]}": c[0] for c in coa_list}
            account_head = st.selectbox("Corresponding Account Head", list(coa_dict.keys()))
            narration = st.text_area("Narration", height=68)
            
            if st.form_submit_button("Record Bank Entry"):
                if amount > 0 and particulars and account_head:
                    voucher_no = generate_bank_voucher_no()
                    today = datetime.now().strftime("%Y-%m-%d")
                    account_code = coa_dict[account_head]
                    
                    bank_code_result = run_query("SELECT account_code FROM chart_of_accounts WHERE account_name = ?", (selected_bank,))
                    bank_code = bank_code_result[0][0] if bank_code_result else "AST-102"
                    
                    if entry_type == "DEBIT (Deposit)":
                        new_balance = current_balance + amount
                        debit_amount, credit_amount = amount, 0
                        post_automated_jv(f"Bank Deposit: {particulars} - {selected_bank}", bank_code, account_code, amount)
                    else:
                        if current_balance < amount:
                            st.error(f"❌ Insufficient Bank Balance!")
                            st.stop()
                        new_balance = current_balance - amount
                        debit_amount, credit_amount = 0, amount
                        post_automated_jv(f"Bank Withdrawal: {particulars} - {selected_bank}", account_code, bank_code, amount)
                    
                    run_query("""
                        INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (today, voucher_no, particulars, debit_amount, credit_amount, new_balance, selected_bank, account_code, narration, datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                    
                    st.success(f"✅ Bank entry successfully recorded! Voucher: {voucher_no}")
                    st.rerun()

    with tab2:
        entries = run_query("SELECT id, date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration FROM bank_book ORDER BY id DESC")
        if entries:
            df_bank = pd.DataFrame(entries, columns=["ID", "Date", "Voucher No", "Particulars", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Bank", "Account Code", "Narration"])
            st.dataframe(df_bank, use_container_width=True)
            
            del_id = st.number_input("Enter Bank Entry ID to Delete", min_value=1, step=1, key="del_bank_id")
            if st.button("Delete Bank Entry"):
                run_query("DELETE FROM bank_book WHERE id=?", (del_id,), fetch=False)
                st.warning(f"Bank Entry ID {del_id} deleted successfully.")
                st.rerun()
        else:
            st.info("No bank entries found.")

    with tab3:
        st.subheader("Edit Existing Bank Entry")
        edit_bank_id = st.number_input("Enter Bank Entry ID to Edit", min_value=1, step=1, key="edit_bank_id_input")
        bank_row = run_query("SELECT id, particulars, debit_amount, credit_amount, bank_name, narration FROM bank_book WHERE id=?", (edit_bank_id,))
        
        if bank_row:
            row = bank_row[0]
            with st.form("edit_bank_form"):
                new_part = st.text_input("Particulars", value=row[1])
                curr_dr = row[2] if row[2] > 0 else row[3]
                is_debit = row[2] > 0
                new_type = st.selectbox("Type", ["DEBIT (Deposit)", "CREDIT (Withdrawal)"], index=0 if is_debit else 1)
                new_amt = st.number_input("Amount (₹)", min_value=1.0, value=float(curr_dr))
                new_narration = st.text_area("Narration", value=row[5] if row[5] else "")
                
                if st.form_submit_button("Update Bank Entry"):
                    d_amt = new_amt if "DEBIT" in new_type else 0.0
                    c_amt = new_amt if "CREDIT" in new_type else 0.0
                    run_query("""
                        UPDATE bank_book 
                        SET particulars = ?, debit_amount = ?, credit_amount = ?, narration = ? 
                        WHERE id = ?
                    """, (new_part, d_amt, c_amt, new_narration, edit_bank_id), fetch=False)
                    st.success(f"Bank Entry ID {edit_bank_id} updated successfully!")
                    st.rerun()
        else:
            st.info("Enter a valid Bank Entry ID above to load and edit.")

    with tab4:
        entries = run_query("SELECT date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, narration FROM bank_book ORDER BY id ASC")
        if entries:
            df_print = pd.DataFrame(entries, columns=["Date", "Voucher No", "Particulars", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Bank", "Narration"])
            st.dataframe(df_print, use_container_width=True)
            st.download_button("Download Bank Book PDF", create_pdf_report("Bank Book Report", df_print), "bank_book.pdf", "application/pdf")

# --- JOURNAL VOUCHERS ---
elif menu == "Journal Vouchers":
    st.title("📝 Journal Vouchers Management")
    tab1, tab2 = st.tabs(["Create Journal Voucher", "View Vouchers"])
    
    with tab1:
        with st.form("jv_form"):
            v_date = st.date_input("Voucher Date", value=date.today())
            narration = st.text_input("Narration / Description")
            
            coa_list = run_query("SELECT account_code, account_name FROM chart_of_accounts")
            coa_dict = {f"{c[0]} - {c[1]}": c[0] for c in coa_list}
            
            col_acc, col_dr, col_cr = st.columns(3)
            acc1 = col_acc.selectbox("Account Head 1", list(coa_dict.keys()), key="jv_acc1")
            dr1 = col_dr.number_input("Debit 1 (₹)", value=0.0, key="jv_dr1")
            cr1 = col_cr.number_input("Credit 1 (₹)", value=0.0, key="jv_cr1")
            
            acc2 = col_acc.selectbox("Account Head 2", list(coa_dict.keys()), key="jv_acc2")
            dr2 = col_dr.number_input("Debit 2 (₹)", value=0.0, key="jv_dr2")
            cr2 = col_cr.number_input("Credit 2 (₹)", value=0.0, key="jv_cr2")
            
            if st.form_submit_button("Save and Post JV"):
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
                    st.success("Balanced Journal Voucher posted successfully!")
                else:
                    st.error("Journal Voucher unbalanced! Total Debits must equal Total Credits.")

    with tab2:
        jvs = run_query("SELECT jv_id, voucher_date, narration, status FROM journal_vouchers")
        if jvs:
            df_jvs = pd.DataFrame(jvs, columns=["JV ID", "Date", "Narration", "Status"])
            st.dataframe(df_jvs, use_container_width=True)

# --- ADMIN RECORD EDITOR ---
elif menu == "Admin Record Editor":
    st.title("🛠️ Universal Database Record Editor")
    tables_res = run_query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    table_list = [t[0] for t in tables_res]
    selected_table = st.selectbox("Select Database Table to Manage", table_list)
    
    if selected_table:
        # Determine primary key column name dynamically
        pk_info = run_query(f"PRAGMA table_info({selected_table})")
        pk_col = None
        for col in pk_info:
            if col[5] == 1:  # Primary key indicator in SQLite PRAGMA
                pk_col = col[1]
                break
        if not pk_col and pk_info:
            pk_col = pk_info[0][1] # fallback to first column if no explicit PK flag

        rows = run_query(f"SELECT * FROM {selected_table}")
        col_names = [col[1] for col in pk_info]
        
        if rows:
            df_table = pd.DataFrame(rows, columns=col_names)
            st.dataframe(df_table, use_container_width=True)
            
            st.markdown("---")
            st.subheader(f"Manage Records in `{selected_table}`")
            
            action = st.radio("Select Action", ["Delete Record", "Edit Record"], horizontal=True)
            
            if action == "Delete Record":
                record_id_to_del = st.text_input(f"Enter value for primary identifier (`{pk_col}`) to delete")
                if st.button("Delete Record", type="primary"):
                    if record_id_to_del:
                        # Try parsing as number if column is numeric, else text
                        try:
                            val = int(record_id_to_del)
                        except ValueError:
                            val = record_id_to_del
                            
                        run_query(f"DELETE FROM {selected_table} WHERE {pk_col} = ?", (val,), fetch=False)
                        st.success(f"Record with {pk_col} = {val} deleted successfully from {selected_table}!")
                        st.rerun()
                    else:
                        st.error("Please enter a valid identifier value.")
            
            elif action == "Edit Record":
                record_id_to_edit = st.text_input(f"Enter value for primary identifier (`{pk_col}`) to edit")
                if record_id_to_edit:
                    try:
                        edit_val = int(record_id_to_edit)
                    except ValueError:
                        edit_val = record_id_to_edit
                        
                    target_row = run_query(f"SELECT * FROM {selected_table} WHERE {pk_col} = ?", (edit_val,))
                    if target_row:
                        row_data = target_row[0]
                        with st.form("admin_edit_form"):
                            st.info(f"Editing record where {pk_col} = {edit_val}")
                            updated_values = []
                            for idx, col_name in enumerate(col_names):
                                current_val = row_data[idx]
                                # Don't allow editing the primary key identifier itself to prevent orphan constraints
                                if col_name == pk_col:
                                    st.text(f"{col_name} (Primary Key - Read Only): {current_val}")
                                    updated_values.append(current_val)
                                else:
                                    new_input = st.text_input(f"Field: {col_name}", value="" if current_val is None else str(current_val))
                                    updated_values.append(new_input)
                            
                            if st.form_submit_button("Save Changes"):
                                set_clauses = [f"{col_names[i]} = ?" for i in range(len(col_names)) if col_names[i] != pk_col]
                                update_vals = [updated_values[i] for i in range(len(col_names)) if col_names[i] != pk_col] + [edit_val]
                                update_sql = f"UPDATE {selected_table} SET {', '.join(set_clauses)} WHERE {pk_col} = ?"
                                run_query(update_sql, tuple(update_vals), fetch=False)
                                st.success(f"Record {edit_val} updated successfully!")
                                st.rerun()
                    else:
                        st.warning(f"No record found with {pk_col} = {edit_val}")
        else:
            st.info(f"Table `{selected_table}` is currently empty.")


# --- FINANCIAL STATEMENTS ---
elif menu == "Financial Statements (Trial/BS/PL)":
    st.title("⚖️ Financial Statements & Reports")
    tab1, tab2, tab3 = st.tabs(["Trial Balance", "Balance Sheet", "Profit & Loss Statement"])
    
    with tab1:
        st.subheader("Trial Balance Summary")
        entries = run_query("""
            SELECT 
                CO.account_code, 
                CO.account_name, 
                CO.account_type, 
                COALESCE(SUM(JE.debit), 0) as total_debit, 
                COALESCE(SUM(JE.credit), 0) as total_credit
            FROM chart_of_accounts CO
            LEFT JOIN jv_entries JE ON CO.account_code = JE.account_code
            GROUP BY CO.account_code
            HAVING total_debit > 0 OR total_credit > 0
            ORDER BY CO.account_type, CO.account_code
        """)
        
        if entries:
            df_tb = pd.DataFrame(entries, columns=["Account Code", "Account Name", "Account Type", "Total Debit (₹)", "Total Credit (₹)"])
            st.dataframe(df_tb, use_container_width=True)
            
            total_debits = sum(row[3] for row in entries)
            total_credits = sum(row[4] for row in entries)
            
            col1, col2 = st.columns(2)
            col1.metric("Total Debits", f"₹{total_debits:,.2f}")
            col2.metric("Total Credits", f"₹{total_credits:,.2f}")
            
            st.download_button("Download Trial Balance PDF", create_pdf_report("Trial Balance Statement", df_tb), "trial_balance.pdf", "application/pdf")
        else:
            st.info("No entries recorded yet.")
    
    with tab2:
        st.subheader("Balance Sheet (Assets, Liabilities & Equity)")
        cash_bal = get_cash_balance()
        union_bank_bal = get_bank_balance("Union Bank of India")
        sbi_bal = get_bank_balance("State Bank of India")
        tot_sb_balance = run_query("SELECT SUM(balance) FROM sb_accounts")[0][0] or 0.0
        tot_fd_principal = run_query("SELECT SUM(principal) FROM fixed_deposits WHERE status='ACTIVE'")[0][0] or 0.0
        tot_rd_invested = run_query("SELECT SUM(monthly_amount * installments_paid) FROM recurring_deposits WHERE status='ACTIVE'")[0][0] or 0.0

        col1, col2 = st.columns(2)
        with col2:
            st.markdown("### Assets")
            asset_data = [
                ["Cash in Hand", f"₹{cash_bal:,.2f}"],
                ["Union Bank of India", f"₹{union_bank_bal:,.2f}"],
                ["State Bank of India", f"₹{sbi_bal:,.2f}"]
            ]
            total_assets = cash_bal + union_bank_bal + sbi_bal
            df_assets = pd.DataFrame(asset_data, columns=["Account", "Amount"])
            st.dataframe(df_assets, use_container_width=True)
            st.metric("Total Assets", f"₹{total_assets:,.2f}")

        with col1:
            st.markdown("### Liabilities & Equity")
            lia_data = []
            total_lia = 0
            
            if tot_sb_balance > 0:
                lia_data.append(["SB Deposits Control", f"₹{tot_sb_balance:,.2f}"])
                total_lia += tot_sb_balance
            if tot_fd_principal > 0:
                lia_data.append(["FD Deposits Control", f"₹{tot_fd_principal:,.2f}"])
                total_lia += tot_fd_principal
            if tot_rd_invested > 0:
                lia_data.append(["RD Deposits Control", f"₹{tot_rd_invested:,.2f}"])
                total_lia += tot_rd_invested
                
            # Including Bank sources / funding mapping to mirror asset side and balance out
            if union_bank_bal > 0:
                lia_data.append(["Union Bank Capital / Source Funding", f"₹{union_bank_bal:,.2f}"])
                total_lia += union_bank_bal
                
            if sbi_bal > 0:
                lia_data.append(["State Bank of India Capital / Source Funding", f"₹{sbi_bal:,.2f}"])
                total_lia += sbi_bal
                
            if lia_data:
                df_lia = pd.DataFrame(lia_data, columns=["Account", "Amount"])
                st.dataframe(df_lia, use_container_width=True)
            else:
                st.info("No active liabilities.")
            st.metric("Total Liabilities & Sources", f"₹{total_lia:,.2f}")
    with tab3:
        st.subheader("Profit & Loss Statement")
        income_entries = run_query("SELECT CO.account_name, SUM(JE.credit) FROM jv_entries JE JOIN chart_of_accounts CO ON JE.account_code = CO.account_code WHERE CO.account_type = 'Income' GROUP BY CO.account_name")
        expense_entries = run_query("SELECT CO.account_name, SUM(JE.debit) FROM jv_entries JE JOIN chart_of_accounts CO ON JE.account_code = CO.account_code WHERE CO.account_type = 'Expense' GROUP BY CO.account_name")
        
        tot_inc = sum([row[1] for row in income_entries]) if income_entries else 0.0
        tot_exp = sum([row[1] for row in expense_entries]) if expense_entries else 0.0
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"₹{tot_inc:,.2f}")
        col2.metric("Total Expenses", f"₹{tot_exp:,.2f}")
        col3.metric("Net Profit/Loss", f"₹{tot_inc - tot_exp:,.2f}")

# --- REPORTS ---
elif menu == "Reports":
    st.title("📄 Comprehensive Bank Reports Center")
    report_type = st.selectbox("Select Report to Generate", ["Customer List Report", "Daily Transactions Report"])
    if st.button("Generate Report"):
        data = run_query("SELECT id, name, phone, email, kyc_status FROM customers")
        df = pd.DataFrame(data, columns=["ID", "Name", "Phone", "Email", "KYC Status"])
        st.dataframe(df, use_container_width=True)

# --- CUSTOMER PORTAL ---
elif menu == "Customer Portal":
    st.title("👤 Customer Account Portal")
    cust_id_login = st.number_input("Enter Your Customer ID", min_value=1, step=1)
    if st.button("Access My Accounts"):
        cust_info = run_query("SELECT name, phone, kyc_status FROM customers WHERE id=?", (cust_id_login,))
        if cust_info:
            name, phone, kyc = cust_info[0]
            st.success(f"Welcome back, **{name}**! KYC Status: `{kyc}`")
        else:
            st.error("Customer ID not found.")
