import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import io
from fpdf import FPDF
import os

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
    
    # Migration safety check for existing databases missing upload columns
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
            type TEXT, -- INCOME / EXPENSE
            customer_id INTEGER,
            account_code TEXT,
            amount REAL,
            mode TEXT,
            date TEXT,
            narration TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE SET NULL
        )
    """)

    # Preload Chart of Accounts if empty
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
            ("AST-102", "Union Bank", "Asset", "Current Assets"),
            ("AST-103", "State Bank", "Asset", "Current Assets"),
            ("AST-104", "Retrieval Pool Account", "Asset", "Current Assets"),
            ("LIA-101", "SB Deposits Control", "Liability", "Deposits"),
            ("LIA-102", "FD Deposits Control", "Liability", "Deposits"),
            ("LIA-103", "RD Deposits Control", "Liability", "Deposits"),
            ("EQT-101", "Capital Account", "Equity", "Capital"),
            ("EQT-102", "Retained Earnings", "Equity", "Reserves")
        ]
        cursor.executemany("INSERT OR IGNORE INTO chart_of_accounts VALUES (?, ?, ?, ?)", default_accounts)
    else:
        # Check if Union Bank and State Bank exist, if not add them
        cursor.execute("SELECT COUNT(*) FROM chart_of_accounts WHERE account_name = 'Union Bank'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO chart_of_accounts (account_code, account_name, account_type, category) VALUES (?, ?, ?, ?)", 
                         ("AST-102", "Union Bank", "Asset", "Current Assets"))
        
        cursor.execute("SELECT COUNT(*) FROM chart_of_accounts WHERE account_name = 'State Bank'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO chart_of_accounts (account_code, account_name, account_type, category) VALUES (?, ?, ?, ?)", 
                         ("AST-103", "State Bank", "Asset", "Current Assets"))

    conn.commit()
    conn.close()

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
        "Chart of Accounts", "Transactions", "Journal Vouchers", "Income & Expenses",
        "Interest Calculation", "Admin Record Editor", "Financial Statements (Trial/BS/PL)", "Reports"
    ])
else:
    menu = "Customer Portal"

# --- 1. DASHBOARD ---
if menu == "Dashboard":
    st.title("📊 Bank Dashboard & Overview")
    
    total_cust = run_query("SELECT COUNT(*) FROM customers")[0][0]
    kyc_pending = run_query("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'")[0][0]
    sb_count = run_query("SELECT COUNT(*) FROM sb_accounts")[0][0]
    total_sb_dep = run_query("SELECT SUM(balance) FROM sb_accounts")[0][0] or 0.0
    total_fd = run_query("SELECT SUM(principal) FROM fixed_deposits WHERE status='ACTIVE'")[0][0] or 0.0
    total_rd = run_query("SELECT SUM(monthly_amount * installments_paid) FROM recurring_deposits WHERE status='ACTIVE'")[0][0] or 0.0

    col1, col2, col3, col4,col5 = st.columns(5)
    col1.metric("Total Customers", total_cust, f"Pending KYC: {kyc_pending}")
    col2.metric("SB Accounts Active", sb_count, f"Balance: ₹{total_sb_dep:,.2f}")
    col3.metric("Active FD Portfolio", f"₹{total_fd:,.2f}")
    col4.metric("Active RD Portfolio", f"₹{total_rd:,.2f}")
    col5.metric("Active SB Portfolio", f"₹{total_sb_dep:,.2f}")

    st.markdown("---")
    st.subheader("Recent Activity (Last 10 Transactions)")
    recent_tx = run_query("SELECT tx_id, account_no, type, amount, mode, date FROM transactions ORDER BY id DESC LIMIT 10")
    if recent_tx:
        df_tx = pd.DataFrame(recent_tx, columns=["Tx ID", "Account No", "Type", "Amount (₹)", "Mode", "Date"])
        st.dataframe(df_tx, use_container_width=True)
    else:
        st.info("No recent transaction logs found.")

# --- CIRCULAR PERCENTAGE GRAPH (DONUT CHART) ---
    col_chart, col_info = st.columns([2, 1])
    
    with col_chart:
        st.subheader("📈 Deposit Portfolio Share (%)")
        
        # Prepare data for SB, FD, and RD
        portfolio_data = {
            "Deposit Type": ["Savings Bank (SB)", "Fixed Deposits (FD)", "Recurring Deposits (RD)"],
            "Amount": [total_sb_dep, total_fd, total_rd]
        }
        df_portfolio = pd.DataFrame(portfolio_data)
        
        # Check if there is actual financial data to display
        if df_portfolio["Amount"].sum() > 0:
            import plotly.express as px
            # Create a donut chart displaying percentages automatically
            fig = px.pie(
                df_portfolio, 
                names="Deposit Type", 
                values="Amount", 
                hole=0.4, # Makes it a circle/donut graph
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No active deposit funds available to render percentage chart.")

    with col_info:
        st.subheader("Quick Summary")
        grand_total = total_sb_dep + total_fd + total_rd
        st.metric("Total Bank Deposits", f"₹{grand_total:,.2f}")
        st.write("This circular breakdown reflects the share percentage of capital held across Savings, Fixed, and Recurring deposits.")

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

# --- 3. KYC VERIFICATION ---
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

# --- 4. SB ACCOUNTS ---
elif menu == "SB Accounts":
    st.title("💰 Savings Bank (SB) Management")
    tab1, tab2, tab3= st.tabs(["Open SB Account", "Transact (Deposit/Withdraw)", "View & Delete Accounts"])
    
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

    

# --- 5. FIXED DEPOSITS (FD) ---
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

   

# --- 6. RECURRING DEPOSITS (RD) ---
elif menu == "Recurring Deposits (RD)":
    st.title("🔄 Recurring Deposits Management & Installment Payment")
    tab1, tab2, tab3= st.tabs(["Open RD", "Pay Installment", "Active RDs & Deletion"])
    
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

    

# --- 7. RETRIEVAL ACCOUNT ---
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

# --- 8. CHART OF ACCOUNTS ---
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

# --- 9. TRANSACTIONS ---
elif menu == "Transactions":
    st.title("💳 All System Transactions Ledger & Deletion")
    txs = run_query("SELECT id, tx_id, account_no, type, amount, mode, narration, date FROM transactions ORDER BY id DESC")
    if txs:
        df_all_tx = pd.DataFrame(txs, columns=["ID", "Tx ID", "Account No", "Type", "Amount (₹)", "Mode", "Narration", "Date"])
        st.dataframe(df_all_tx, use_container_width=True)
        
        st.markdown("### Delete Transaction Log")
        del_tx_id = st.number_input("Enter Transaction ID (ID column) to Delete", min_value=1, step=1)
        if st.button("Delete Transaction Record"):
            run_query("DELETE FROM transactions WHERE id=?", (del_tx_id,), fetch=False)
            st.warning(f"Transaction ID {del_tx_id} deleted successfully.")
            st.rerun()
    else:
        st.info("No transaction logs recorded.")

# --- 10. JOURNAL VOUCHERS ---
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

# --- 11. INCOME & EXPENSES ---
elif menu == "Income & Expenses":
    st.title("💰 Operational Income, Expenses, Assets & Liabilities")
    tab1, tab2, tab3, tab4 = st.tabs(["Record Entry", "Edit / Delete Entry", "View All Entries", "Cash Book Report & Print"])
    
    with tab1:
        st.subheader("Record New Financial Entry")
        with st.form("income_expense_form"):
            col1, col2 = st.columns(2)
            entry_type = col1.selectbox("Entry Classification", ["INCOME", "EXPENSE", "ASSET", "LIABILITY","EQUITY"])
            
            coa_records = run_query("SELECT account_code, account_name, account_type FROM chart_of_accounts")
            coa_dict = {f"{c[0]} - {c[1]} ({c[2]})": c[0] for c in coa_records}
            
            selected_coa = col2.selectbox("Select Chart of Accounts (COA)", list(coa_dict.keys()))
            account_code = coa_dict[selected_coa]
            
            customers = run_query("SELECT id, name FROM customers")
            cust_dict = {"None / General": None}
            if customers:
                for c in customers:
                    cust_dict[f"{c[1]} (ID: {c[0]})"] = c[0]
            selected_cust_str = st.selectbox("Associated Customer (Optional)", list(cust_dict.keys()))
            customer_id = cust_dict[selected_cust_str]
            
            col_amt1, col_amt2 = st.columns(2)
            amount = col_amt1.number_input("Amount (₹)", min_value=1.0, value=1000.0, step=100.0)
            pay_mode = col_amt2.selectbox("Payment Mode", ["CASH", "BANK TRANSFER", "CHEQUE", "ONLINE"])
            
            st.markdown("### Journal Entry Routing (Debit & Credit)")
            d_col1, d_col2 = st.columns(2)
            debit_account = d_col1.selectbox("Debit Account Code", list(coa_dict.keys()), index=0)
            credit_account = d_col2.selectbox("Credit Account Code", list(coa_dict.keys()), index=min(1, len(coa_dict)-1))
            
            narration = st.text_input("Narration / Particulars", value="Financial transaction entry")
            
            submitted = st.form_submit_button("Post Financial Entry")
            if submitted:
                d_code = coa_dict[debit_account]
                c_code = coa_dict[credit_account]
                
                run_query("""
                    INSERT INTO operational_finances (type, customer_id, account_code, amount, mode, date, narration)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (entry_type, customer_id, account_code, amount, pay_mode, datetime.now().strftime("%Y-%m-%d"), narration), fetch=False)
                
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", 
                               (str(date.today()), f"{entry_type}: {narration}"))
                jv_id = cursor.lastrowid
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, d_code, amount))
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, c_code, amount))
                conn.commit()
                conn.close()
                
                st.success("Entry recorded and Journal Voucher posted successfully!")

    with tab2:
        st.subheader("✏️ Edit or 🗑️ Delete Financial Entry")
        finances_list = run_query("SELECT id, type, account_code, amount, mode, date, narration FROM operational_finances ORDER BY id DESC")
        if finances_list:
            fin_dict = {f"ID: {f[0]} | {f[1]} | ₹{f[3]:,.2f} | {f[5]} | {f[6]}": f for f in finances_list}
            selected_fin_str = st.selectbox("Select Financial Entry", list(fin_dict.keys()))
            selected_record = fin_dict[selected_fin_str]
            
            rec_id, curr_type, curr_code, curr_amt, curr_mode, curr_date, curr_narr = selected_record
            
            action_col1, action_col2 = st.columns(2)
            action = action_col1.radio("Choose Action", ["Edit Entry", "Delete Entry"])
            
            if action == "Edit Entry":
                with st.form("edit_income_expense_form"):
                    e_type = st.selectbox("Update Classification", ["INCOME", "EXPENSE", "ASSET", "LIABILITY","EQUITY"], index=["INCOME", "EXPENSE", "ASSET", "LIABILITY","EQUITY"].index(curr_type) if curr_type in ["INCOME", "EXPENSE", "ASSET", "LIABILITY","EQUITY"] else 0)
                    
                    coa_records = run_query("SELECT account_code, account_name, account_type FROM chart_of_accounts")
                    coa_dict = {f"{c[0]} - {c[1]} ({c[2]})": c[0] for c in coa_records}
                    
                    default_idx = 0
                    for idx, (k, v) in enumerate(coa_dict.items()):
                        if v == curr_code:
                            default_idx = idx
                            break
                            
                    e_coa = st.selectbox("Update Chart of Accounts (COA)", list(coa_dict.keys()), index=default_idx)
                    e_amount = st.number_input("Update Amount (₹)", min_value=1.0, value=float(curr_amt), step=100.0)
                    e_mode = st.selectbox("Update Payment Mode", ["CASH", "BANK TRANSFER", "CHEQUE", "ONLINE"], index=["CASH", "BANK TRANSFER", "CHEQUE", "ONLINE"].index(curr_mode) if curr_mode in ["CASH", "BANK TRANSFER", "CHEQUE", "ONLINE"] else 0)
                    e_narration = st.text_input("Update Narration / Particulars", value=curr_narr)
                    
                    update_submitted = st.form_submit_button("Save Changes")
                    if update_submitted:
                        new_code = coa_dict[e_coa]
                        run_query("""
                            UPDATE operational_finances 
                            SET type=?, account_code=?, amount=?, mode=?, narration=? 
                            WHERE id=?
                        """, (e_type, new_code, e_amount, e_mode, e_narration, rec_id), fetch=False)
                        st.success(f"Financial Entry ID #{rec_id} updated successfully!")
                        st.rerun()
            else:
                st.warning(f"You are about to delete Financial Entry ID #{rec_id} ({curr_type} - ₹{curr_amt:,.2f}). This action cannot be undone.")
                if st.button("Confirm & Delete Entry", type="primary"):
                    run_query("DELETE FROM operational_finances WHERE id = ?", (rec_id,), fetch=False)
                    st.success(f"Financial Entry ID #{rec_id} deleted successfully!")
                    st.rerun()
        else:
            st.info("No financial entries available to edit or delete.")

    with tab3:
        st.subheader("All Financial Entries")
        finances = run_query("""
            SELECT o.id, o.type, c.name, o.account_code, o.amount, o.mode, o.date, o.narration 
            FROM operational_finances o LEFT JOIN customers c ON o.customer_id = c.id
        """)
        if finances:
            df_fin = pd.DataFrame(finances, columns=["ID", "Type", "Customer Name", "Account Code", "Amount (₹)", "Mode", "Date", "Narration"])
            st.dataframe(df_fin, use_container_width=True)
            st.download_button("Download All Entries PDF", create_pdf_report("All Financial Entries Report", df_fin), "all_finances.pdf", "application/pdf")
        else:
            st.info("No financial logs recorded.")

    with tab4:
        st.subheader("📖 Cash Book / Day Book Report (Strictly Income & Expenses Only)")
        
        cashbook_data = run_query("""
            SELECT 
                o.date,
                o.id AS 'Voucher No',
                o.mode AS Mode,
                o.narration AS Particulars,
                o.account_code AS 'Account Code',
                CASE WHEN o.type = 'INCOME' THEN o.amount ELSE 0.0 END AS 'Receipts (Debit)',
                CASE WHEN o.type = 'EXPENSE' THEN o.amount ELSE 0.0 END AS 'Payments (Credit)'
            FROM operational_finances o
            JOIN chart_of_accounts c ON o.account_code = c.account_code
            WHERE o.type IN ('INCOME', 'EXPENSE') AND c.account_type IN ('Income', 'Expense')
            ORDER BY o.date ASC, o.id ASC
        """)
        
        if cashbook_data:
            df_cb = pd.DataFrame(cashbook_data, columns=["Date", "Voucher No", "Mode", "Particulars", "Account Code", "Receipts (Debit)", "Payments (Credit)"])
            
            df_cb['Balance'] = (df_cb['Receipts (Debit)'] - df_cb['Payments (Credit)']).cumsum()
            
            st.dataframe(df_cb, use_container_width=True)
            
            col_cb1, col_cb2 = st.columns(2)
            with col_cb1:
                st.download_button(
                    "📥 Download Cash Book PDF", 
                    create_pdf_report("Cash Book Report (Income & Expenses)", df_cb), 
                    "cash_book_report.pdf", 
                    "application/pdf"
                )
            with col_cb2:
                if st.button("🖨️ Print Cash Book View"):
                    st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
                    st.info("Triggered print command for Cash Book layout.")
        else:
            st.info("No operational income or expense entries found for the Cash Book report.")

# --- 12. INTEREST CALCULATION ---
elif menu == "Interest Calculation":
    st.title("📊 SB Interest Calculation & Drill-Down")
    
    st.subheader("Global Rate Configuration")
    rate_res = run_query("SELECT DISTINCT interest_rate FROM sb_accounts")
    current_rate = rate_res[0][0] if rate_res else 3.5
    
    new_rate = st.number_input("Update Global SB Interest Rate (%)", value=float(current_rate))
    if st.button("Apply Global Rate to All SB Accounts"):
        run_query("UPDATE sb_accounts SET interest_rate=?", (new_rate,), fetch=False)
        st.success(f"Interest rate updated to {new_rate}% for all active savings accounts!")
        st.rerun()

    st.markdown("---")
    st.subheader("Account-Wise Interest Drill-Down & Posting")
    
    sb_records = run_query("""
        SELECT s.account_no, c.name, s.balance, s.interest_rate 
        FROM sb_accounts s JOIN customers c ON s.customer_id = c.id
    """)
    
    if sb_records:
        acc_dict = {f"{r[0]} - {r[1]} (Bal: ₹{r[2]:,.2f}, Rate: {r[3]}%)": r for r in sb_records}
        chosen_acc_str = st.selectbox("Select Account for Interest Drill-Down", list(acc_dict.keys()))
        selected_data = acc_dict[chosen_acc_str]
        
        acc_no, cust_name, balance, rate = selected_data
        
        st.markdown(f"### Drill-Down Details: Account `{acc_no}`")
        col1, col2, col3 = st.columns(3)
        col1.metric("Customer Name", cust_name)
        col2.metric("Current Balance", f"₹{balance:,.2f}")
        col3.metric("Assigned Rate", f"{rate}% p.a.")
        
        calc_period_months = st.slider("Calculation Period (Months)", 1, 12, 12, key="drill_months")
        computed_interest = balance * (rate / 100.0) * (calc_period_months / 12.0)
        
        st.info(f"Calculated Interest for {calc_period_months} month(s): **₹{computed_interest:,.2f}**")
        
        if st.button("Credit Interest to Account & Post Entry"):
            if computed_interest > 0:
                new_balance = balance + computed_interest
                run_query("UPDATE sb_accounts SET balance=? WHERE account_no=?", (new_balance, acc_no), fetch=False)
                run_query("""
                    INSERT INTO transactions (tx_id, account_no, type, amount, mode, narration, date) 
                    VALUES (?, ?, 'CREDIT', ?, 'INTEREST', ?, ?)
                """, (f"TX{datetime.now().strftime('%M%S%f')}", acc_no, computed_interest, f"SB Interest Credited ({calc_period_months}M)", datetime.now().strftime("%Y-%m-%d")), fetch=False)
                
                post_automated_jv(f"SB Interest Credited to {acc_no}", "EXP-101", "LIA-101", computed_interest)
                st.success(f"Successfully credited ₹{computed_interest:,.2f} to account {acc_no}! New Balance: ₹{new_balance:,.2f}")
                st.rerun()
            else:
                st.warning("Interest amount must be greater than zero.")
    else:
        st.info("No savings accounts available for interest calculation.")

# --- 13. ADMIN RECORD EDITOR ---
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
        
        # Get all account balances from trial balance
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
        
        # Separate assets, liabilities, and equity
        assets = {}
        liabilities = {}
        equity = {}
        
        for acc_code, acc_name, acc_type, net_bal in account_balances:
            if acc_type == "Asset":
                # For assets, positive net balance means asset
                if net_bal != 0:
                    assets[acc_name] = abs(net_bal)
            elif acc_type == "Liability":
                # For liabilities, we want the absolute value (liabilities are credit balances)
                if net_bal != 0:
                    liabilities[acc_name] = abs(net_bal)
            elif acc_type == "Equity":
                # For equity, we want the absolute value (equity is credit balance)
                if net_bal != 0:
                    equity[acc_name] = abs(net_bal)
        
        # Also get SB, FD, RD totals from their respective tables
        tot_sb_balance = run_query("SELECT SUM(balance) FROM sb_accounts")[0][0] or 0.0
        tot_fd_principal = run_query("SELECT SUM(principal) FROM fixed_deposits WHERE status='ACTIVE'")[0][0] or 0.0
        tot_rd_invested = run_query("SELECT SUM(monthly_amount * installments_paid) FROM recurring_deposits WHERE status='ACTIVE'")[0][0] or 0.0
        
        # Display assets with calculated values
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Assets")
            
            # Display asset accounts from trial balance
            asset_data = []
            for name, balance in assets.items():
                if balance != 0:
                    asset_data.append([name, f"₹{balance:,.2f}"])
            
            # Add SB, FD, RD balances if not already in assets
            if "Union Bank" not in assets and "Bank Balance" not in assets:
                # Show bank accounts from chart of accounts
                bank_accounts = run_query("""
                    SELECT account_name, COALESCE(SUM(JE.debit), 0) - COALESCE(SUM(JE.credit), 0) as balance
                    FROM chart_of_accounts CO
                    LEFT JOIN jv_entries JE ON CO.account_code = JE.account_code
                    WHERE CO.account_type = 'Asset' AND CO.account_name IN ('Union Bank', 'State Bank', 'Cash in Hand')
                    GROUP BY CO.account_name
                """)
                for bank_name, bank_bal in bank_accounts:
                    if bank_bal != 0:
                        asset_data.append([bank_name, f"₹{abs(bank_bal):,.2f}"])
            
            # Add deposit accounts
            if tot_sb_balance > 0:
                asset_data.append(["Savings Bank (SB) Deposits", f"₹{tot_sb_balance:,.2f}"])
            if tot_fd_principal > 0:
                asset_data.append(["Fixed Deposits (FD) Control", f"₹{tot_fd_principal:,.2f}"])
            if tot_rd_invested > 0:
                asset_data.append(["Recurring Deposits (RD) Control", f"₹{tot_rd_invested:,.2f}"])
            
            if asset_data:
                total_assets = sum(float(val.replace('₹', '').replace(',', '')) for _, val in asset_data)
                asset_data.append(["**Total Assets**", f"**₹{total_assets:,.2f}**"])
                
                df_assets = pd.DataFrame(asset_data, columns=["Account", "Amount"])
                st.dataframe(df_assets, use_container_width=True)
            else:
                st.info("No asset data available")
                total_assets = 0
        
        with col2:
            st.markdown("### Liabilities & Equity")
            
            # Display liability accounts from trial balance
            liability_data = []
            for name, balance in liabilities.items():
                if balance != 0 and "Deposits" not in name:
                    liability_data.append([name, f"₹{balance:,.2f}"])
            
            # Display equity accounts from trial balance
            equity_data = []
            for name, balance in equity.items():
                if balance != 0:
                    equity_data.append([name, f"₹{balance:,.2f}"])
            
            # Add deposit liabilities if they exist
            if tot_sb_balance > 0:
                liability_data.append(["SB Deposits Liability", f"₹{tot_sb_balance:,.2f}"])
            if tot_fd_principal > 0:
                liability_data.append(["FD Deposits Liability", f"₹{tot_fd_principal:,.2f}"])
            if tot_rd_invested > 0:
                liability_data.append(["RD Deposits Liability", f"₹{tot_rd_invested:,.2f}"])
            
            # Combined data
            combined_data = liability_data + equity_data
            
            if combined_data:
                total_liabilities_equity = sum(float(val.replace('₹', '').replace(',', '')) for _, val in combined_data)
                combined_data.append(["**Total Liabilities & Equity**", f"**₹{total_liabilities_equity:,.2f}**"])
                
                df_combined = pd.DataFrame(combined_data, columns=["Account", "Amount"])
                st.dataframe(df_combined, use_container_width=True)
            else:
                st.info("No liability or equity data available")
                total_liabilities_equity = 0
        
        st.markdown("---")
        
        # Balance check
        diff = total_assets - total_liabilities_equity
        if abs(diff) < 0.01:
            st.success("✅ Balance Sheet Perfectly Balanced!")
        else:
            st.warning(f"⚠️ Balance Sheet Discrepancy: ₹{diff:,.2f}")
        
        if st.button("Export Balance Sheet Report"):
            # Prepare balance sheet data
            bs_data = [
                ["ASSETS", "Amount (₹)"],
                ["---Assets from Trial Balance---", ""],
            ]
            for name, balance in assets.items():
                if balance != 0:
                    bs_data.append([name, f"₹{balance:,.2f}"])
            
            bs_data.append(["---Deposits---", ""])
            if tot_sb_balance > 0:
                bs_data.append(["Savings Bank (SB) Deposits", f"₹{tot_sb_balance:,.2f}"])
            if tot_fd_principal > 0:
                bs_data.append(["Fixed Deposits (FD) Control", f"₹{tot_fd_principal:,.2f}"])
            if tot_rd_invested > 0:
                bs_data.append(["Recurring Deposits (RD) Control", f"₹{tot_rd_invested:,.2f}"])
            
            bs_data.append(["Total Assets", f"₹{total_assets:,.2f}"])
            bs_data.append(["", ""])
            bs_data.append(["LIABILITIES & EQUITY", "Amount (₹)"])
            bs_data.append(["---Liabilities---", ""])
            for name, balance in liabilities.items():
                if balance != 0:
                    bs_data.append([name, f"₹{balance:,.2f}"])
            
            bs_data.append(["---Deposit Liabilities---", ""])
            if tot_sb_balance > 0:
                bs_data.append(["SB Deposits Liability", f"₹{tot_sb_balance:,.2f}"])
            if tot_fd_principal > 0:
                bs_data.append(["FD Deposits Liability", f"₹{tot_fd_principal:,.2f}"])
            if tot_rd_invested > 0:
                bs_data.append(["RD Deposits Liability", f"₹{tot_rd_invested:,.2f}"])
                
            bs_data.append(["---Equity---", ""])
            for name, balance in equity.items():
                if balance != 0:
                    bs_data.append([name, f"₹{balance:,.2f}"])
            bs_data.append(["Total Liabilities & Equity", f"₹{total_liabilities_equity:,.2f}"])
            
            df_bs = pd.DataFrame(bs_data[1:], columns=bs_data[0])
            st.download_button("Download Balance Sheet PDF", create_pdf_report("Balance Sheet Statement", df_bs), "balance_sheet.pdf", "application/pdf")

    with tab3:
        st.subheader("Profit & Loss Statement (Strictly Operational Revenue vs Expenses)")
        
        total_income = run_query("""
            SELECT COALESCE(SUM(o.amount), 0.0) 
            FROM operational_finances o 
            JOIN chart_of_accounts c ON o.account_code = c.account_code 
            WHERE c.account_type = 'Income'
        """)[0][0]
        
        total_expense = run_query("""
            SELECT COALESCE(SUM(o.amount), 0.0) 
            FROM operational_finances o 
            JOIN chart_of_accounts c ON o.account_code = c.account_code 
            WHERE c.account_type = 'Expense'
        """)[0][0]
        
        net_pl = total_income - total_expense
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"₹{total_income:,.2f}")
        col2.metric("Total Expenses", f"₹{total_expense:,.2f}")
        if net_pl >= 0:
            col3.metric("Net Profit", f"₹{net_pl:,.2f}", delta="In the Black")
        else:
            col3.metric("Net Loss", f"₹{net_pl:,.2f}", delta="-In the Red", delta_color="inverse")
            
        st.markdown("---")
        st.info("Note: The P&L statement exclusively evaluates accounts mapped as Income or Expense. Capital injections are safely isolated to the Balance Sheet and Trial Balance.")

# --- 15. REPORTS ---
elif menu == "Reports":
    st.title("📄 Comprehensive Bank Reports Center")
    report_type = st.selectbox("Select Report to Generate", [
        "Customer List Report", "Daily Transactions Report", "FD Summary Report", "RD Summary Report", "Income & Expense Breakdown"
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
        else:
            data = run_query("SELECT type, amount, mode, date FROM operational_finances")
            df = pd.DataFrame(data, columns=["Type", "Amount", "Mode", "Date"])
            st.dataframe(df, use_container_width=True)
            st.download_button("Download PDF", create_pdf_report("Income & Expense Breakdown", df), "income_expense_breakdown.pdf", "application/pdf")

# --- 16. CUSTOMER PORTAL ---
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


