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
    """Initialize database with all required tables"""
    try:
        # Close any existing connections
        if os.path.exists(DB_NAME):
            try:
                os.remove(DB_NAME)
                print(f"✅ Deleted existing database: {DB_NAME}")
            except PermissionError:
                print("Database file is locked, waiting...")
                time.sleep(2)
                try:
                    os.remove(DB_NAME)
                    print(f"✅ Deleted existing database: {DB_NAME}")
                except:
                    pass
        
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

        # Preload Chart of Accounts
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
        print("✅ Database initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ Database initialization error: {str(e)}")
        return False

# --- INITIALIZE DATABASE ---
# Force delete and recreate
if os.path.exists(DB_NAME):
    try:
        os.remove(DB_NAME)
        print(f"✅ Deleted existing database: {DB_NAME}")
    except Exception as e:
        print(f"Could not delete database: {e}")

# Initialize database with retry
max_init_retries = 3
for attempt in range(max_init_retries):
    if init_db():
        break
    if attempt < max_init_retries - 1:
        print(f"Retrying database initialization... (Attempt {attempt + 2})")
        time.sleep(2)

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
        # Try to recreate database
        if os.path.exists(DB_NAME):
            try:
                os.remove(DB_NAME)
            except:
                pass
        init_db()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        res = cursor.fetchall() if fetch else None
        conn.commit()
        conn.close()
        return res

# --- HELPER FUNCTIONS ---
def save_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

def get_cash_balance():
    """Get current Cash balance from cash_book"""
    try:
        result = run_query("SELECT balance FROM cash_book ORDER BY id DESC LIMIT 1")
        return result[0][0] if result else 0
    except:
        return 0

def get_bank_balance(bank_name=None):
    """Get current Bank balance from bank_book"""
    try:
        if bank_name:
            result = run_query("SELECT balance FROM bank_book WHERE bank_name = ? ORDER BY id DESC LIMIT 1", (bank_name,))
        else:
            result = run_query("SELECT balance FROM bank_book ORDER BY id DESC LIMIT 1")
        return result[0][0] if result else 0
    except:
        return 0

def generate_cash_voucher_no():
    """Generate Cash Book voucher number with prefix CB"""
    today = datetime.now().strftime("%Y%m%d")
    try:
        result = run_query("""
            SELECT voucher_no FROM cash_book 
            WHERE voucher_no LIKE ? 
            ORDER BY id DESC LIMIT 1
        """, (f"CB{today}%",))
        
        if result:
            last_seq = int(result[0][0][-4:])
            new_seq = last_seq + 1
        else:
            new_seq = 1
    except:
        new_seq = 1
    
    return f"CB{today}{new_seq:04d}"

def generate_bank_voucher_no():
    """Generate Bank Book voucher number with prefix BB"""
    today = datetime.now().strftime("%Y%m%d")
    try:
        result = run_query("""
            SELECT voucher_no FROM bank_book 
            WHERE voucher_no LIKE ? 
            ORDER BY id DESC LIMIT 1
        """, (f"BB{today}%",))
        
        if result:
            last_seq = int(result[0][0][-4:])
            new_seq = last_seq + 1
        else:
            new_seq = 1
    except:
        new_seq = 1
    
    return f"BB{today}{new_seq:04d}"

def post_automated_jv(narration, debit_acc, credit_acc, amount):
    """Post automated journal voucher"""
    if amount <= 0:
        return
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", 
                       (str(date.today()), narration))
        jv_id = cursor.lastrowid
        cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, debit_acc, amount))
        cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, credit_acc, amount))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Error posting journal voucher: {str(e)}")

def create_pdf_report(title, df):
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    import io

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
    
    try:
        total_cust = run_query("SELECT COUNT(*) FROM customers")[0][0] if run_query("SELECT COUNT(*) FROM customers") else 0
    except:
        total_cust = 0
    
    try:
        kyc_pending = run_query("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'")[0][0] if run_query("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'") else 0
    except:
        kyc_pending = 0
    
    try:
        sb_count = run_query("SELECT COUNT(*) FROM sb_accounts")[0][0] if run_query("SELECT COUNT(*) FROM sb_accounts") else 0
    except:
        sb_count = 0
    
    try:
        total_sb_dep = run_query("SELECT SUM(balance) FROM sb_accounts")[0][0] or 0.0
    except:
        total_sb_dep = 0.0
    
    try:
        total_fd = run_query("SELECT SUM(principal) FROM fixed_deposits WHERE status='ACTIVE'")[0][0] or 0.0
    except:
        total_fd = 0.0
    
    try:
        total_rd = run_query("SELECT SUM(monthly_amount * installments_paid) FROM recurring_deposits WHERE status='ACTIVE'")[0][0] or 0.0
    except:
        total_rd = 0.0
    
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
        st.subheader("New Customer Registration (with Document & Signature Upload)")
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
                    st.success(f"Customer {name} registered successfully with status PENDING and documents uploaded!")
                else:
                    st.error("Please fill in mandatory fields: Name and Phone.")

    with tab2:
        st.subheader("Customer Directory & Deletion")
        customers = run_query("SELECT id, name, phone, email, kyc_status, pan, created_at FROM customers")
        if customers:
            df_cust = pd.DataFrame(customers, columns=["ID", "Name", "Phone", "Email", "KYC Status", "PAN", "Joined"])
            st.dataframe(df_cust, use_container_width=True)
            
            col_csv, col_pdf = st.columns(2)
            col_csv.download_button("Download CSV Report", df_cust.to_csv(index=False).encode('utf-8'), "customers_report.csv", "text/csv")
            col_pdf.download_button("Download PDF Report", create_pdf_report("Customer Directory Report", df_cust), "customers_report.pdf", "application/pdf")
            
            st.markdown("### Delete Customer")
            del_id = st.number_input("Enter Customer ID to Delete", min_value=1, step=1, key="del_cust")
            if st.button("Delete Customer Record"):
                run_query("DELETE FROM customers WHERE id=?", (del_id,), fetch=False)
                st.warning(f"Customer ID {del_id} and associated mapping records deleted.")
                st.rerun()
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
                
                st.write(f"Current Aadhaar File: `{c[7]}`")
                st.write(f"Current PAN File: `{c[8]}`")
                st.write(f"Current Signature File: `{c[9]}`")
                
                if st.form_submit_button("Update Details"):
                    run_query("""
                        UPDATE customers SET name=?, email=?, phone=?, street=?, city=?, state=?, pincode=? WHERE id=?
                    """, (new_name, new_email, new_phone, new_street, new_city, new_state, new_pincode, cust_id_edit), fetch=False)
                    st.success("Customer details updated successfully across records!")

# --- KYC VERIFICATION ---
elif menu == "KYC Verification":
    st.title("✅ KYC Verification Panel")
    pending = run_query("SELECT id, name, phone, pan, adhar_file, pan_file, signature_file, created_at FROM customers WHERE kyc_status='PENDING'")
    if pending:
        for p in pending:
            with st.expander(f"Customer: {p[1]} (ID: {p[0]}) - Phone: {p[2]}"):
                st.write(f"**PAN:** {p[3]} | **Aadhar Document:** `{p[4]}` | **PAN Document:** `{p[5]}` | **Signature:** `{p[6]}`")
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
    tab1, tab2, tab3 = st.tabs(["Open SB Account", "Transact (Deposit/Withdraw)", "View & Delete Accounts"])
    
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
        st.subheader("Active SB Accounts & Deletion")
        accounts = run_query("""
            SELECT s.account_no, c.name, s.balance, s.interest_rate, s.created_at 
            FROM sb_accounts s JOIN customers c ON s.customer_id = c.id
        """)
        if accounts:
            df_sb = pd.DataFrame(accounts, columns=["Account No", "Customer Name", "Balance (₹)", "Interest Rate (%)", "Created"])
            st.dataframe(df_sb, use_container_width=True)
            st.download_button("Download SB Accounts PDF", create_pdf_report("Savings Bank Accounts Report", df_sb), "sb_accounts.pdf", "application/pdf")
            
            st.markdown("### Delete SB Account")
            del_sb_no = st.selectbox("Select Account No to Delete", [a[0] for a in accounts])
            if st.button("Delete SB Account Record"):
                run_query("DELETE FROM sb_accounts WHERE account_no=?", (del_sb_no,), fetch=False)
                run_query("DELETE FROM transactions WHERE account_no=?", (del_sb_no,), fetch=False)
                st.warning(f"SB Account {del_sb_no} and its transaction logs were successfully deleted.")
                st.rerun()
        else:
            st.info("No active SB accounts found.")

# --- FIXED DEPOSITS ---
elif menu == "Fixed Deposits (FD)":
    st.title("📈 Fixed Deposits Management & Closure")
    tab1, tab2 = st.tabs(["Open FD", "Active FDs, Close & Delete"])
    
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
                st.success("Fixed Deposit opened & recorded in Trial Balance successfully!")
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
            
            st.download_button("Download FDs PDF Report", create_pdf_report("Fixed Deposits Report", df_fds), "fixed_deposits.pdf", "application/pdf")
            
            st.markdown("---")
            st.subheader("Close / Settle or Delete FD Account")
            active_fds = [f for f in fds if f[6] == 'ACTIVE']
            if active_fds:
                fd_choice = st.selectbox("Select Active FD ID to Close/Settle", [f[0] for f in active_fds])
                selected_fd_record = next(f for f in fds if f[0] == fd_choice)
                
                cust_id = selected_fd_record[7]
                maturity_amt = selected_fd_record[5]
                
                settlement_mode = st.selectbox("Settlement Mode", ["CASH", "TRANSFER TO RETRIEVAL POOL", "BANK TRANSFER"])
                
                if st.button("Close & Settle FD Account"):
                    run_query("UPDATE fixed_deposits SET status='CLOSED' WHERE fd_id=?", (fd_choice,), fetch=False)
                    
                    if settlement_mode == "TRANSFER TO RETRIEVAL POOL":
                        ret_exists = run_query("SELECT balance FROM retrieval_accounts WHERE customer_id=?", (cust_id,))
                        if ret_exists:
                            new_ret_bal = ret_exists[0][0] + maturity_amt
                            run_query("UPDATE retrieval_accounts SET balance=? WHERE customer_id=?", (new_ret_bal, cust_id))
                        else:
                            ret_acc_no = f"RET{datetime.now().strftime('%Y%m%d%H%M%S')}"
                            run_query("INSERT INTO retrieval_accounts VALUES (?, ?, ?)", (ret_acc_no, cust_id, maturity_amt))
                    
                    post_automated_jv(f"FD Closure Settlement (FD #{fd_choice})", "LIA-102", "AST-101", maturity_amt)
                    st.success(f"FD #{fd_choice} successfully closed and settled for amount ₹{maturity_amt:,.2f}!")
                    st.rerun()
            else:
                st.info("No active FDs available for settlement.")

            st.markdown("### Delete FD Record")
            del_fd_id = st.number_input("Enter FD ID to Delete Record", min_value=1, step=1, key="del_fd_rec")
            if st.button("Delete FD Record"):
                run_query("DELETE FROM fixed_deposits WHERE fd_id=?", (del_fd_id,), fetch=False)
                st.warning(f"FD Record ID {del_fd_id} deleted successfully.")
                st.rerun()
        else:
            st.info("No fixed deposits found.")

# --- RECURRING DEPOSITS ---
elif menu == "Recurring Deposits (RD)":
    st.title("🔄 Recurring Deposits Management & Installment Payment")
    tab1, tab2, tab3 = st.tabs(["Open RD", "Pay Installment", "Active RDs & Deletion"])
    
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
        st.subheader("Pay Monthly Installment for RD")
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
            
            st.info(f"Installment Amount Due: **₹{monthly_amt:,.2f}** | Current Installments Paid: **{paid_inst} / {tenure_m}**")
            pay_mode = st.selectbox("Payment Mode", ["CASH", "BANK TRANSFER", "ONLINE", "CHEQUE"], key="rd_pay_mode")
            
            if st.button("Confirm & Pay Installment"):
                if paid_inst < tenure_m:
                    new_paid = paid_inst + 1
                    run_query("UPDATE recurring_deposits SET installments_paid=? WHERE rd_id=?", (new_paid, rd_id), fetch=False)
                    
                    run_query("""
                        INSERT INTO transactions (tx_id, account_no, type, amount, mode, narration, date)
                        VALUES (?, ?, 'CREDIT', ?, ?, ?, ?)
                    """, (f"TX{datetime.now().strftime('%M%S%f')}", f"RD-{rd_id}", monthly_amt, pay_mode, f"RD Installment Payment #{new_paid}", datetime.now().strftime("%Y-%m-%d")), fetch=False)
                    
                    post_automated_jv(f"RD Installment Paid - RD #{rd_id} (Inst #{new_paid})", "AST-101", "LIA-103", monthly_amt)
                    st.success(f"Installment #{new_paid} of ₹{monthly_amt:,.2f} successfully paid for RD #{rd_id}!")
                    st.rerun()
                else:
                    st.warning("This Recurring Deposit account has already completed all installments!")
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
            
            st.download_button("Download RDs PDF Report", create_pdf_report("Recurring Deposits Report", df_rds), "recurring_deposits.pdf", "application/pdf")
            
            st.markdown("### Delete RD Record")
            del_rd_id = st.number_input("Enter RD ID to Delete", min_value=1, step=1, key="del_rd")
            if st.button("Delete RD Record"):
                run_query("DELETE FROM recurring_deposits WHERE rd_id=?", (del_rd_id,), fetch=False)
                st.warning(f"RD Record ID {del_rd_id} deleted successfully.")
                st.rerun()
        else:
            st.info("No recurring deposits found.")

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
    
    st.subheader("Add or Delete Account Head")
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

    del_code = st.text_input("Enter Account Code to Delete (Custom heads only)")
    if st.button("Delete Account Head"):
        run_query("DELETE FROM chart_of_accounts WHERE account_code=?", (del_code,), fetch=False)
        st.warning(f"Account code {del_code} deleted.")
        st.rerun()

# --- CASH BOOK ---
elif menu == "Cash Book":
    st.title("💰 Cash Book")
    
    tab1, tab2, tab3 = st.tabs(["Record Cash Entry", "View / Edit / Delete", "Print Cash Book"])
    
    with tab1:
        st.subheader("Record Cash Transaction")
        
        current_balance = get_cash_balance()
        st.info(f"💰 **Current Cash Balance:** ₹{current_balance:,.2f}")
        
        with st.form("cash_entry_form"):
            col1, col2 = st.columns(2)
            entry_type = col1.selectbox("Transaction Type", ["DEBIT (Receipt)", "CREDIT (Payment)"])
            amount = col2.number_input("Amount (₹)", min_value=1.0, value=100.0, step=100.0)
            particulars = st.text_input("Particulars / Description")
            
            coa_list = run_query("SELECT account_code, account_name FROM chart_of_accounts")
            coa_dict = {f"{c[0]} - {c[1]}": c[0] for c in coa_list}
            
            if entry_type == "DEBIT (Receipt)":
                st.info("💡 **Debit Entry:** Cash is increasing. Select the Credit account head.")
                account_head = st.selectbox("Credit Account Head", list(coa_dict.keys()))
            else:
                st.info("💡 **Credit Entry:** Cash is decreasing. Select the Debit account head.")
                account_head = st.selectbox("Debit Account Head", list(coa_dict.keys()))
            
            narration = st.text_area("Narration (Optional)", height=68)
            
            submitted = st.form_submit_button("Record Cash Entry")
            if submitted:
                if amount > 0 and particulars and account_head:
                    voucher_no = generate_cash_voucher_no()
                    today = datetime.now().strftime("%Y-%m-%d")
                    account_code = coa_dict[account_head]
                    
                    if entry_type == "DEBIT (Receipt)":
                        new_balance = current_balance + amount
                        debit_amount = amount
                        credit_amount = 0
                        post_automated_jv(f"Cash Receipt: {particulars}", "AST-101", account_code, amount)
                    else:
                        if current_balance < amount:
                            st.error(f"❌ Insufficient Cash Balance! Available: ₹{current_balance:,.2f}")
                            st.stop()
                        new_balance = current_balance - amount
                        debit_amount = 0
                        credit_amount = amount
                        post_automated_jv(f"Cash Payment: {particulars}", account_code, "AST-101", amount)
                    
                    # FIXED: 9 columns, 9 placeholders
                    run_query("""
                        INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (today, voucher_no, particulars, debit_amount, credit_amount, new_balance, account_code, narration, datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                    
                    st.success(f"✅ Cash {entry_type} of ₹{amount:,.2f} recorded successfully!")
                    st.info(f"📌 Voucher No: {voucher_no}\n"
                           f"📌 {entry_type}: ₹{amount:,.2f}\n"
                           f"📌 Account Head: {account_head}\n"
                           f"📌 New Cash Balance: ₹{current_balance:,.2f} → ₹{new_balance:,.2f}")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields!")
    
    with tab2:
        st.subheader("📋 Cash Book Entries - View / Edit / Delete")
        
        entries = run_query("""
            SELECT id, date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration
            FROM cash_book
            ORDER BY id DESC
        """)
        
        if entries:
            df_cash = pd.DataFrame(entries, columns=["ID", "Date", "Voucher No", "Particulars", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Account Code", "Narration"])
            st.dataframe(df_cash, use_container_width=True)
            
            st.markdown("---")
            st.subheader("✏️ Edit or 🗑️ Delete Cash Entry")
            
            entry_ids = [e[0] for e in entries]
            selected_id = st.selectbox("Select Entry ID to Edit/Delete", entry_ids, key="select_cash_entry")
            
            if selected_id:
                entry_data = run_query("""
                    SELECT id, date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration
                    FROM cash_book WHERE id = ?
                """, (selected_id,))
                
                if entry_data:
                    row = entry_data[0]
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Voucher No:** {row[2]}")
                        st.write(f"**Date:** {row[1]}")
                        st.write(f"**Particulars:** {row[3]}")
                        st.write(f"**Debit Amount:** ₹{row[4]:,.2f}" if row[4] > 0 else "**Debit Amount:** ₹0.00")
                        st.write(f"**Credit Amount:** ₹{row[5]:,.2f}" if row[5] > 0 else "**Credit Amount:** ₹0.00")
                        st.write(f"**Balance:** ₹{row[6]:,.2f}")
                        st.write(f"**Account Code:** {row[7]}")
                        st.write(f"**Narration:** {row[8]}")
                    
                    with col2:
                        action = st.radio("Choose Action", ["Edit Entry", "Delete Entry"])
                        
                        if action == "Edit Entry":
                            with st.form("edit_cash_form"):
                                new_particulars = st.text_input("Particulars", value=row[3])
                                
                                account_info = run_query("SELECT account_name FROM chart_of_accounts WHERE account_code = ?", (row[7],))
                                account_name = account_info[0][0] if account_info else ""
                                
                                coa_list = run_query("SELECT account_code, account_name FROM chart_of_accounts")
                                coa_dict = {f"{c[0]} - {c[1]}": c[0] for c in coa_list}
                                
                                current_account = f"{row[7]} - {account_name}" if account_name else list(coa_dict.keys())[0]
                                if current_account not in coa_dict:
                                    current_account = list(coa_dict.keys())[0]
                                
                                new_account = st.selectbox("Account Head", list(coa_dict.keys()), index=list(coa_dict.keys()).index(current_account) if current_account in coa_dict else 0)
                                new_narration = st.text_area("Narration", value=row[8] if row[8] else "")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    edit_submit = st.form_submit_button("💾 Save Changes")
                                with col2:
                                    cancel = st.form_submit_button("❌ Cancel")
                                
                                if edit_submit:
                                    new_account_code = coa_dict[new_account]
                                    run_query("""
                                        UPDATE cash_book 
                                        SET particulars = ?, account_code = ?, narration = ?
                                        WHERE id = ?
                                    """, (new_particulars, new_account_code, new_narration, selected_id), fetch=False)
                                    st.success(f"✅ Cash Entry #{selected_id} updated successfully!")
                                    st.rerun()
                                if cancel:
                                    st.rerun()
                        
                        else:
                            st.warning(f"⚠️ Are you sure you want to delete Cash Entry #{selected_id}?")
                            st.warning(f"**Voucher No:** {row[2]} | **Particulars:** {row[3]} | **Amount:** ₹{max(row[4], row[5]):,.2f}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("🗑️ Confirm Delete", type="primary"):
                                    run_query("DELETE FROM cash_book WHERE id = ?", (selected_id,), fetch=False)
                                    st.success(f"✅ Cash Entry #{selected_id} deleted successfully!")
                                    st.rerun()
                            with col2:
                                if st.button("❌ Cancel"):
                                    st.rerun()
    
    with tab3:
        st.subheader("🖨️ Print Cash Book")
        
        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input("From Date", value=date.today().replace(day=1))
        with col2:
            to_date = st.date_input("To Date", value=date.today())
        
        if st.button("Generate Cash Book Report"):
            entries = run_query("""
                SELECT date, voucher_no, particulars, debit_amount, credit_amount, balance, narration
                FROM cash_book
                WHERE date BETWEEN ? AND ?
                ORDER BY id ASC
            """, (str(from_date), str(to_date)))
            
            if entries:
                df_print = pd.DataFrame(entries, columns=["Date", "Voucher No", "Particulars", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Narration"])
                st.dataframe(df_print, use_container_width=True)
                
                total_debits = sum(row[3] for row in entries)
                total_credits = sum(row[4] for row in entries)
                opening_balance = run_query("""
                    SELECT balance FROM cash_book 
                    WHERE date < ? 
                    ORDER BY id DESC LIMIT 1
                """, (str(from_date),))
                opening_bal = opening_balance[0][0] if opening_balance else 0
                closing_balance = entries[-1][5] if entries else 0
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Opening Balance", f"₹{opening_bal:,.2f}")
                col2.metric("Total Debits", f"₹{total_debits:,.2f}")
                col3.metric("Total Credits", f"₹{total_credits:,.2f}")
                col4.metric("Closing Balance", f"₹{closing_balance:,.2f}")
                
                st.download_button(
                    "📥 Download Cash Book PDF",
                    create_pdf_report(f"Cash Book Report ({from_date} to {to_date})", df_print),
                    f"cash_book_{from_date}_to_{to_date}.pdf",
                    "application/pdf"
                )
                
                if st.button("🖨️ Print Cash Book"):
                    st.markdown("""
                        <script>
                            window.print();
                        </script>
                    """, unsafe_allow_html=True)
            else:
                st.info("No cash entries found for the selected date range.")

# --- BANK BOOK ---
elif menu == "Bank Book":
    st.title("🏦 Bank Book")
    
    # Initialize session state for tab management
    if 'bank_book_tab' not in st.session_state:
        st.session_state.bank_book_tab = "Record Bank Entry"
    
    # Create tabs with session state control
    tab1, tab2, tab3 = st.tabs(["Record Bank Entry", "View / Edit / Delete", "Print Bank Book"])
    
    with tab1:
        st.subheader("Record Bank Transaction")
        
        bank_accounts = run_query("""
            SELECT account_name FROM chart_of_accounts 
            WHERE account_type = 'Asset' AND account_name LIKE '%Bank%'
        """)
        bank_list = [b[0] for b in bank_accounts] if bank_accounts else ["Union Bank of India", "State Bank of India"]
        
        selected_bank = st.selectbox("Select Bank", bank_list)
        current_balance = get_bank_balance(selected_bank)
        
        st.info(f"🏦 **{selected_bank} Current Balance:** ₹{current_balance:,.2f}")
        
        with st.form("bank_entry_form"):
            col1, col2 = st.columns(2)
            entry_type = col1.selectbox("Transaction Type", ["DEBIT (Deposit)", "CREDIT (Withdrawal)"])
            amount = col2.number_input("Amount (₹)", min_value=1.0, value=100.0, step=100.0)
            particulars = st.text_input("Particulars / Description")
            
            coa_list = run_query("SELECT account_code, account_name FROM chart_of_accounts")
            coa_dict = {f"{c[0]} - {c[1]}": c[0] for c in coa_list}
            
            if entry_type == "DEBIT (Deposit)":
                st.info("💡 **Debit Entry:** Bank balance is increasing. Select the Credit account head.")
                account_head = st.selectbox("Credit Account Head", list(coa_dict.keys()))
            else:
                st.info("💡 **Credit Entry:** Bank balance is decreasing. Select the Debit account head.")
                account_head = st.selectbox("Debit Account Head", list(coa_dict.keys()))
            
            narration = st.text_area("Narration (Optional)", height=68)
            
            submitted = st.form_submit_button("Record Bank Entry")
            if submitted:
                if amount > 0 and particulars and account_head:
                    voucher_no = generate_bank_voucher_no()
                    today = datetime.now().strftime("%Y-%m-%d")
                    account_code = coa_dict[account_head]
                    
                    bank_code = run_query("SELECT account_code FROM chart_of_accounts WHERE account_name = ?", (selected_bank,))
                    if not bank_code:
                        st.error(f"❌ Bank account '{selected_bank}' not found in Chart of Accounts!")
                        st.stop()
                    bank_code = bank_code[0][0]
                    
                    if entry_type == "DEBIT (Deposit)":
                        new_balance = current_balance + amount
                        debit_amount = amount
                        credit_amount = 0
                        post_automated_jv(f"Bank Deposit: {particulars}", bank_code, account_code, amount)
                    else:
                        if current_balance < amount:
                            st.error(f"❌ Insufficient Bank Balance! Available: ₹{current_balance:,.2f}")
                            st.stop()
                        new_balance = current_balance - amount
                        debit_amount = 0
                        credit_amount = amount
                        post_automated_jv(f"Bank Withdrawal: {particulars}", account_code, bank_code, amount)
                    
                    # Insert the entry
                    run_query("""
                        INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (today, voucher_no, particulars, debit_amount, credit_amount, new_balance, selected_bank, account_code, narration, datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                    
                    # Show success message
                    st.success(f"✅ Bank {entry_type} of ₹{amount:,.2f} recorded successfully!")
                    st.info(f"📌 Voucher No: {voucher_no}\n"
                           f"📌 {entry_type}: ₹{amount:,.2f}\n"
                           f"📌 Account Head: {account_head}\n"
                           f"📌 New {selected_bank} Balance: ₹{current_balance:,.2f} → ₹{new_balance:,.2f}")
                    
                    # Add button to view entries
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("📋 View All Bank Entries", key="view_after_record"):
                            st.session_state.bank_book_tab = "View / Edit / Delete"
                            st.rerun()
                    with col2:
                        if st.button("➕ Record Another Entry", key="record_another"):
                            st.rerun()
                    with col3:
                        if st.button("🖨️ Print Bank Book", key="print_after_record"):
                            st.session_state.bank_book_tab = "Print Bank Book"
                            st.rerun()
                else:
                    st.error("Please fill in all required fields!")
    
    with tab2:
        st.subheader("📋 Bank Book Entries - View / Edit / Delete")
        
        # Get all entries
        entries = run_query("""
            SELECT id, date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration
            FROM bank_book
            ORDER BY id DESC
        """)
        
        if entries:
            df_bank = pd.DataFrame(entries, columns=["ID", "Date", "Voucher No", "Particulars", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Bank", "Account Code", "Narration"])
            st.dataframe(df_bank, use_container_width=True)
            
            # Show summary statistics
            total_debits = sum(row[4] for row in entries)
            total_credits = sum(row[5] for row in entries)
            total_balance = entries[0][6] if entries else 0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Debits", f"₹{total_debits:,.2f}")
            col2.metric("Total Credits", f"₹{total_credits:,.2f}")
            col3.metric("Current Balance", f"₹{total_balance:,.2f}")
            
            st.markdown("---")
            st.subheader("✏️ Edit or 🗑️ Delete Bank Entry")
            
            entry_ids = [e[0] for e in entries]
            selected_id = st.selectbox("Select Entry ID to Edit/Delete", entry_ids, key="select_bank_entry")
            
            if selected_id:
                entry_data = run_query("""
                    SELECT id, date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration
                    FROM bank_book WHERE id = ?
                """, (selected_id,))
                
                if entry_data:
                    row = entry_data[0]
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Voucher No:** {row[2]}")
                        st.write(f"**Date:** {row[1]}")
                        st.write(f"**Bank:** {row[7]}")
                        st.write(f"**Particulars:** {row[3]}")
                        st.write(f"**Debit Amount:** ₹{row[4]:,.2f}" if row[4] > 0 else "**Debit Amount:** ₹0.00")
                        st.write(f"**Credit Amount:** ₹{row[5]:,.2f}" if row[5] > 0 else "**Credit Amount:** ₹0.00")
                        st.write(f"**Balance:** ₹{row[6]:,.2f}")
                        st.write(f"**Account Code:** {row[8]}")
                        st.write(f"**Narration:** {row[9]}")
                    
                    with col2:
                        action = st.radio("Choose Action", ["Edit Entry", "Delete Entry"])
                        
                        if action == "Edit Entry":
                            with st.form("edit_bank_form"):
                                new_particulars = st.text_input("Particulars", value=row[3])
                                
                                account_info = run_query("SELECT account_name FROM chart_of_accounts WHERE account_code = ?", (row[8],))
                                account_name = account_info[0][0] if account_info else ""
                                
                                coa_list = run_query("SELECT account_code, account_name FROM chart_of_accounts")
                                coa_dict = {f"{c[0]} - {c[1]}": c[0] for c in coa_list}
                                
                                current_account = f"{row[8]} - {account_name}" if account_name else list(coa_dict.keys())[0]
                                if current_account not in coa_dict:
                                    current_account = list(coa_dict.keys())[0]
                                
                                new_account = st.selectbox("Account Head", list(coa_dict.keys()), index=list(coa_dict.keys()).index(current_account) if current_account in coa_dict else 0)
                                new_narration = st.text_area("Narration", value=row[9] if row[9] else "")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    edit_submit = st.form_submit_button("💾 Save Changes")
                                with col2:
                                    cancel = st.form_submit_button("❌ Cancel")
                                
                                if edit_submit:
                                    new_account_code = coa_dict[new_account]
                                    run_query("""
                                        UPDATE bank_book 
                                        SET particulars = ?, account_code = ?, narration = ?
                                        WHERE id = ?
                                    """, (new_particulars, new_account_code, new_narration, selected_id), fetch=False)
                                    st.success(f"✅ Bank Entry #{selected_id} updated successfully!")
                                    st.rerun()
                                if cancel:
                                    st.rerun()
                        
                        else:
                            st.warning(f"⚠️ Are you sure you want to delete Bank Entry #{selected_id}?")
                            st.warning(f"**Voucher No:** {row[2]} | **Bank:** {row[7]} | **Particulars:** {row[3]} | **Amount:** ₹{max(row[4], row[5]):,.2f}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("🗑️ Confirm Delete", type="primary"):
                                    run_query("DELETE FROM bank_book WHERE id = ?", (selected_id,), fetch=False)
                                    st.success(f"✅ Bank Entry #{selected_id} deleted successfully!")
                                    st.rerun()
                            with col2:
                                if st.button("❌ Cancel"):
                                    st.rerun()
        else:
            st.info("No bank entries found. Record your first bank entry in the 'Record Bank Entry' tab.")
            if st.button("➕ Go to Record Bank Entry"):
                st.session_state.bank_book_tab = "Record Bank Entry"
                st.rerun()
    
    with tab3:
        st.subheader("🖨️ Print Bank Book")
        
        bank_filter = st.selectbox("Select Bank", ["All Banks"] + bank_list)
        
        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input("From Date", value=date.today().replace(day=1))
        with col2:
            to_date = st.date_input("To Date", value=date.today())
        
        if st.button("Generate Bank Book Report"):
            if bank_filter == "All Banks":
                entries = run_query("""
                    SELECT date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, narration
                    FROM bank_book
                    WHERE date BETWEEN ? AND ?
                    ORDER BY bank_name, id ASC
                """, (str(from_date), str(to_date)))
            else:
                entries = run_query("""
                    SELECT date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, narration
                    FROM bank_book
                    WHERE date BETWEEN ? AND ? AND bank_name = ?
                    ORDER BY id ASC
                """, (str(from_date), str(to_date), bank_filter))
            
            if entries:
                df_print = pd.DataFrame(entries, columns=["Date", "Voucher No", "Particulars", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Bank", "Narration"])
                st.dataframe(df_print, use_container_width=True)
                
                total_debits = sum(row[3] for row in entries)
                total_credits = sum(row[4] for row in entries)
                
                if bank_filter == "All Banks":
                    opening_balance = run_query("""
                        SELECT balance FROM bank_book 
                        WHERE date < ? 
                        ORDER BY id DESC LIMIT 1
                    """, (str(from_date),))
                else:
                    opening_balance = run_query("""
                        SELECT balance FROM bank_book 
                        WHERE date < ? AND bank_name = ?
                        ORDER BY id DESC LIMIT 1
                    """, (str(from_date), bank_filter))
                
                opening_bal = opening_balance[0][0] if opening_balance else 0
                closing_balance = entries[-1][5] if entries else 0
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Opening Balance", f"₹{opening_bal:,.2f}")
                col2.metric("Total Debits", f"₹{total_debits:,.2f}")
                col3.metric("Total Credits", f"₹{total_credits:,.2f}")
                col4.metric("Closing Balance", f"₹{closing_balance:,.2f}")
                
                st.download_button(
                    "📥 Download Bank Book PDF",
                    create_pdf_report(f"Bank Book Report ({bank_filter}) - {from_date} to {to_date}", df_print),
                    f"bank_book_{from_date}_to_{to_date}.pdf",
                    "application/pdf"
                )
                
                if st.button("🖨️ Print Bank Book"):
                    st.markdown("""
                        <script>
                            window.print();
                        </script>
                    """, unsafe_allow_html=True)
            else:
                st.info("No bank entries found for the selected date range.")
        
        # Add button to go back to record entry
        if st.button("➕ Record New Bank Entry", key="print_to_record"):
            st.session_state.bank_book_tab = "Record Bank Entry"
            st.rerun()
# --- JOURNAL VOUCHERS ---
elif menu == "Journal Vouchers":
    st.title("📝 Journal Vouchers Management & Deletion")
    tab1, tab2 = st.tabs(["Create Journal Voucher", "View & Delete Vouchers"])
    
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
            
            st.markdown("### Delete Journal Voucher")
            del_jv_id = st.number_input("Enter JV ID to Delete", min_value=1, step=1, key="del_jv")
            if st.button("Delete JV and Entries"):
                run_query("DELETE FROM jv_entries WHERE jv_id=?", (del_jv_id,), fetch=False)
                run_query("DELETE FROM journal_vouchers WHERE jv_id=?", (del_jv_id,), fetch=False)
                st.warning(f"Journal Voucher ID {del_jv_id} deleted successfully.")
                st.rerun()
        else:
            st.info("No journal vouchers found.")

# --- ADMIN RECORD EDITOR ---
elif menu == "Admin Record Editor":
    st.title("🛠️ Universal Database Record Editor")
    st.write("Admin tool to manually inspect and edit **any column** across any table, including financial ledgers.")
    
    tables_res = run_query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    table_list = [t[0] for t in tables_res]
    
    selected_table = st.selectbox("Select Database Table to Edit", table_list)
    
    if selected_table:
        rows = run_query(f"SELECT * FROM {selected_table}")
        columns_info = run_query(f"PRAGMA table_info({selected_table})")
        col_names = [col[1] for col in columns_info]
        pk_col = next((col[1] for col in columns_info if col[5] == 1), col_names[0])
        
        if rows:
            df_table = pd.DataFrame(rows, columns=col_names)
            st.dataframe(df_table, use_container_width=True)
            
            st.markdown("---")
            st.subheader(f"Edit Record in `{selected_table}`")
            
            record_ids = [r[col_names.index(pk_col)] for r in rows]
            selected_id = st.selectbox(f"Select Record `{pk_col}` to Edit", record_ids)
            
            if selected_id is not None:
                current_data = run_query(f"SELECT * FROM {selected_table} WHERE {pk_col}=?", (selected_id,))
                if current_data:
                    row_vals = current_data[0]
                    with st.form("universal_edit_form"):
                        updated_values = {}
                        for idx, col in enumerate(col_names):
                            val = row_vals[idx]
                            if col == pk_col:
                                st.text_input(f"{col} (Primary Key - Read Only)", value=str(val), disabled=True)
                                updated_values[col] = val
                            else:
                                updated_values[col] = st.text_input(f"Column: `{col}`", value="" if val is None else str(val))
                        
                        if st.form_submit_button("Save Changes to Database"):
                            set_clauses = ", ".join([f"{c}=?" for c in col_names if c != pk_col])
                            params = [updated_values[c] for c in col_names if c != pk_col] + [selected_id]
                            run_query(f"UPDATE {selected_table} SET {set_clauses} WHERE {pk_col}=?", tuple(params), fetch=False)
                            st.success(f"Record `{selected_id}` in table `{selected_table}` updated successfully!")
                            st.rerun()
        else:
            st.info(f"Table `{selected_table}` is currently empty.")

# --- FINANCIAL STATEMENTS ---
elif menu == "Financial Statements (Trial/BS/PL)":
    st.title("⚖️ Financial Statements & Reports")
    tab1, tab2, tab3 = st.tabs(["Trial Balance", "Balance Sheet", "Profit & Loss Statement"])
    
    with tab1:
        st.subheader("Trial Balance Summary")
        entries = run_query("""
            SELECT JE.account_code, CO.account_name, CO.account_type, SUM(JE.debit), SUM(JE.credit)
            FROM jv_entries JE JOIN chart_of_accounts CO ON JE.account_code = CO.account_code
            GROUP BY JE.account_code
        """)
        if entries:
            df_tb = pd.DataFrame(entries, columns=["Account Code", "Account Name", "Account Type", "Total Debit (₹)", "Total Credit (₹)"])
            st.dataframe(df_tb, use_container_width=True)
            st.download_button("Download Trial Balance PDF", create_pdf_report("Trial Balance Statement", df_tb), "trial_balance.pdf", "application/pdf")
        else:
            st.info("No entries recorded yet.")

    with tab2:
        st.subheader("Balance Sheet (Assets, Liabilities & Equity)")
        
        account_balances = run_query("""
            SELECT 
                CO.account_code,
                CO.account_name,
                CO.account_type,
                COALESCE(SUM(JE.debit), 0) - COALESCE(SUM(JE.credit), 0) as net_balance
            FROM chart_of_accounts CO
            LEFT JOIN jv_entries JE ON CO.account_code = JE.account_code
            GROUP BY CO.account_code
        """)
        
        assets = {}
        liabilities = {}
        equity = {}
        
        for acc_code, acc_name, acc_type, net_bal in account_balances:
            if acc_type == "Asset":
                assets[acc_name] = net_bal if net_bal != 0 else 0
            elif acc_type == "Liability":
                liabilities[acc_name] = net_bal if net_bal != 0 else 0
            elif acc_type == "Equity":
                equity[acc_name] = net_bal if net_bal != 0 else 0
        
        cash_balance = get_cash_balance()
        assets["Cash in Hand"] = cash_balance
        
        bank_balances = run_query("SELECT bank_name, balance FROM bank_book GROUP BY bank_name ORDER BY id DESC")
        for bank_name, balance in bank_balances:
            assets[bank_name] = balance
        
        tot_sb_balance = run_query("SELECT SUM(balance) FROM sb_accounts")[0][0] or 0.0
        tot_fd_principal = run_query("SELECT SUM(principal) FROM fixed_deposits WHERE status='ACTIVE'")[0][0] or 0.0
        tot_rd_invested = run_query("SELECT SUM(monthly_amount * installments_paid) FROM recurring_deposits WHERE status='ACTIVE'")[0][0] or 0.0
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Assets")
            asset_data = []
            for name, balance in assets.items():
                if "Deposits" not in name and "Retrieval" not in name:
                    asset_data.append([name, f"₹{balance:,.2f}"])
            
            if tot_sb_balance > 0:
                asset_data.append(["Savings Bank (SB) Deposits", f"₹{tot_sb_balance:,.2f}"])
            if tot_fd_principal > 0:
                asset_data.append(["Fixed Deposits (FD) Control", f"₹{tot_fd_principal:,.2f}"])
            if tot_rd_invested > 0:
                asset_data.append(["Recurring Deposits (RD) Control", f"₹{tot_rd_invested:,.2f}"])
            
            if asset_data:
                total_assets = sum(float(val.replace('₹', '').replace(',', '')) for _, val in asset_data if "Total" not in _)
                asset_data.append(["**Total Assets**", f"**₹{total_assets:,.2f}**"])
                df_assets = pd.DataFrame(asset_data, columns=["Account", "Amount"])
                st.dataframe(df_assets, use_container_width=True)
            else:
                st.info("No asset data available")
                total_assets = 0
        
        with col2:
            st.markdown("### Liabilities & Equity")
            
            liability_data = []
            for name, balance in liabilities.items():
                if balance != 0:
                    liability_data.append([name, f"₹{balance:,.2f}"])
            
            equity_data = []
            for name, balance in equity.items():
                if balance != 0:
                    equity_data.append([name, f"₹{balance:,.2f}"])
            
            combined_data = liability_data + equity_data
            
            if combined_data:
                total_liabilities_equity = sum(float(val.replace('₹', '').replace(',', '')) for _, val in combined_data if "Total" not in _)
                combined_data.append(["**Total Liabilities & Equity**", f"**₹{total_liabilities_equity:,.2f}**"])
                df_combined = pd.DataFrame(combined_data, columns=["Account", "Amount"])
                st.dataframe(df_combined, use_container_width=True)
            else:
                st.info("No liability or equity data available")
                total_liabilities_equity = 0
        
        st.markdown("---")
        
        diff = total_assets - total_liabilities_equity
        if abs(diff) < 0.01:
            st.success("✅ Balance Sheet Perfectly Balanced!")
        else:
            st.warning(f"⚠️ Balance Sheet Discrepancy: ₹{diff:,.2f}")
        
        if st.button("Export Balance Sheet Report"):
            bs_data = [
                ["Assets Section", "Amount (₹)"],
                ["---", "---"]
            ]
            for name, balance in assets.items():
                if "Deposits" not in name and "Retrieval" not in name:
                    bs_data.append([name, f"₹{balance:,.2f}"])
            bs_data.append(["Total Assets", f"₹{total_assets:,.2f}"])
            bs_data.append(["", ""])
            bs_data.append(["Liabilities & Equity", "Amount (₹)"])
            bs_data.append(["---", "---"])
            for name, balance in liabilities.items():
                if balance != 0:
                    bs_data.append([name, f"₹{balance:,.2f}"])
            for name, balance in equity.items():
                if balance != 0:
                    bs_data.append([name, f"₹{balance:,.2f}"])
            bs_data.append(["Total Liabilities & Equity", f"₹{total_liabilities_equity:,.2f}"])
            
            df_bs = pd.DataFrame(bs_data[1:], columns=bs_data[0])
            st.download_button("Download Balance Sheet PDF", create_pdf_report("Balance Sheet Statement", df_bs), "balance_sheet.pdf", "application/pdf")

    with tab3:
        st.subheader("Profit & Loss Statement")
        
        income_entries = run_query("""
            SELECT CO.account_name, SUM(JE.credit) as total
            FROM jv_entries JE
            JOIN chart_of_accounts CO ON JE.account_code = CO.account_code
            WHERE CO.account_type = 'Income'
            GROUP BY CO.account_name
        """)
        
        expense_entries = run_query("""
            SELECT CO.account_name, SUM(JE.debit) as total
            FROM jv_entries JE
            JOIN chart_of_accounts CO ON JE.account_code = CO.account_code
            WHERE CO.account_type = 'Expense'
            GROUP BY CO.account_name
        """)
        
        st.markdown("### 📈 INCOME")
        if income_entries:
            income_data = []
            total_income = 0
            for name, amount in income_entries:
                income_data.append([name, f"₹{amount:,.2f}"])
                total_income += amount
            income_data.append(["**Total Income**", f"**₹{total_income:,.2f}**"])
            df_income = pd.DataFrame(income_data, columns=["Account", "Amount"])
            st.dataframe(df_income, use_container_width=True)
        else:
            st.info("No income recorded")
            total_income = 0
        
        st.markdown("---")
        
        st.markdown("### 📉 EXPENSES")
        if expense_entries:
            expense_data = []
            total_expense = 0
            for name, amount in expense_entries:
                expense_data.append([name, f"₹{amount:,.2f}"])
                total_expense += amount
            expense_data.append(["**Total Expenses**", f"**₹{total_expense:,.2f}**"])
            df_expense = pd.DataFrame(expense_data, columns=["Account", "Amount"])
            st.dataframe(df_expense, use_container_width=True)
        else:
            st.info("No expenses recorded")
            total_expense = 0
        
        st.markdown("---")
        
        net_pl = total_income - total_expense
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"₹{total_income:,.2f}")
        col2.metric("Total Expenses", f"₹{total_expense:,.2f}")
        if net_pl >= 0:
            col3.metric("Net Profit", f"₹{net_pl:,.2f}", delta="In the Black")
        else:
            col3.metric("Net Loss", f"₹{net_pl:,.2f}", delta="-In the Red", delta_color="inverse")

# --- REPORTS ---
elif menu == "Reports":
    st.title("📄 Comprehensive Bank Reports Center")
    report_type = st.selectbox("Select Report to Generate", [
        "Customer List Report", "Daily Transactions Report", "FD Summary Report", "RD Summary Report"
    ])
    
    if st.button("Generate & Display Report"):
        if "Customer" in report_type:
            data = run_query("SELECT id, name, phone, email, kyc_status, created_at FROM customers")
            df = pd.DataFrame(data, columns=["ID", "Name", "Phone", "Email", "KYC Status", "Joined"])
            st.dataframe(df, use_container_width=True)
            st.download_button("Download PDF", create_pdf_report("Customer Directory", df), "customer_list.pdf", "application/pdf")
        elif "Transaction" in report_type:
            data = run_query("SELECT tx_id, account_no, type, amount, mode, date FROM transactions")
            df = pd.DataFrame(data, columns=["Tx ID", "Account No", "Type", "Amount", "Mode", "Date"])
            st.dataframe(df, use_container_width=True)
            st.download_button("Download PDF", create_pdf_report("Daily Transactions Report", df), "transactions_report.pdf", "application/pdf")
        elif "FD" in report_type:
            data = run_query("SELECT f.fd_id, c.name, f.principal, f.maturity_amount, f.status FROM fixed_deposits f JOIN customers c ON f.customer_id = c.id")
            df = pd.DataFrame(data, columns=["FD ID", "Customer Name", "Principal", "Maturity", "Status"])
            st.dataframe(df, use_container_width=True)
            st.download_button("Download PDF", create_pdf_report("Fixed Deposits Summary", df), "fd_summary.pdf", "application/pdf")
        elif "RD" in report_type:
            data = run_query("SELECT r.rd_id, c.name, r.monthly_amount, r.installments_paid, r.status FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id")
            df = pd.DataFrame(data, columns=["RD ID", "Customer Name", "Monthly", "Paid", "Status"])
            st.dataframe(df, use_container_width=True)
            st.download_button("Download PDF", create_pdf_report("Recurring Deposits Summary", df), "rd_summary.pdf", "application/pdf")

# --- CUSTOMER PORTAL ---
elif menu == "Customer Portal":
    st.title("👤 Customer Account Portal")
    cust_id_login = st.number_input("Enter Your Customer ID", min_value=1, step=1)
    if st.button("Access My Accounts"):
        cust_info = run_query("SELECT name, phone, kyc_status FROM customers WHERE id=?", (cust_id_login,))
        if cust_info:
            name, phone, kyc = cust_info[0]
            st.success(f"Welcome back, **{name}**! KYC Status: `{kyc}`")
            
            st.subheader("Your Savings Accounts")
            sb = run_query("SELECT account_no, balance, interest_rate FROM sb_accounts WHERE customer_id=?", (cust_id_login,))
            if sb:
                df_cust_sb = pd.DataFrame(sb, columns=["Account No", "Balance (₹)", "Interest Rate (%)"])
                st.dataframe(df_cust_sb, use_container_width=True)
                st.download_button("Download My Account Summary PDF", create_pdf_report(f"Account Statement - {name}", df_cust_sb), "my_accounts.pdf", "application/pdf")
            else:
                st.info("No savings account mapped to this ID.")
        else:
            st.error("Customer ID not found in system records.")
