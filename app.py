import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import os
from fpdf import FPDF
import pytz
import plotly.graph_objects as go
import plotly.express as px

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Aasha Nidhi Banking Software",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CUSTOM CSS FOR BETTER UI ---
st.markdown("""
<style>
    /* Main container styling */
    .main {
        padding: 0rem 1rem;
    }
    
    /* Custom header styling */
    .custom-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .custom-header h1 {
        color: white;
        margin: 0;
        font-weight: 600;
    }
    .custom-header p {
        color: #e0e0e0;
        margin: 0;
        font-size: 0.9rem;
    }
    
    /* Metric cards styling */
    .metric-card {
        background: white;
        padding: 1.2rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 4px solid #2a5298;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .metric-card .label {
        color: #666;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .metric-card .value {
        color: #1e3c72;
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0.3rem 0;
    }
    .metric-card .change {
        color: #28a745;
        font-size: 0.8rem;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: #f8f9fa;
    }
    .sidebar-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e3c72;
        padding: 1rem 0;
        border-bottom: 2px solid #e0e0e0;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        border: none;
        padding: 0.5rem 1.5rem;
        border-radius: 5px;
        font-weight: 500;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(42,82,152,0.3);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        background: #f8f9fa;
        border-radius: 5px 5px 0 0;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: white;
        border-top: 3px solid #2a5298;
    }
    
    /* Dataframe styling */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: #f8f9fa;
        border-radius: 8px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# --- INDIAN TIMEZONE SETUP ---
IST = pytz.timezone('Asia/Kolkata')

def get_indian_time():
    return datetime.now(IST)

def get_indian_date():
    return get_indian_time().strftime("%Y-%m-%d %H:%M:%S")

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
                   (get_indian_date(), narration))
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
    pdf.cell(0, 10, f"Generated on: {get_indian_time().strftime('%Y-%m-%d %H:%M:%S')} | Aasha Nidhi Bank", 0, 1, "C")
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

def create_circular_chart(labels, values, title):
    """Create a circular/pie chart using Plotly"""
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=['#1e3c72', '#2a5298', '#4a7fb5', '#6b9ac9']),
        textinfo='label+percent',
        textposition='inside'
    )])
    fig.update_layout(
        title=dict(text=title, font=dict(size=20, color='#1e3c72')),
        showlegend=True,
        height=400,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    return fig

# --- SIDEBAR NAVIGATION ---
st.sidebar.markdown("""
<div class="sidebar-title">
    🏦 Aasha Nidhi<br>
    <span style="font-size: 0.8rem; color: #666;">Banking Software</span>
</div>
""", unsafe_allow_html=True)

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

# --- HEADER ---
st.markdown("""
<div class="custom-header">
    <h1>🏦 Aasha Nidhi Bank</h1>
    <p>Empowering Financial Growth • Serving Since 2025</p>
</div>
""", unsafe_allow_html=True)

# --- 1. DASHBOARD ---
if menu == "Dashboard":
    st.title("📊 Bank Dashboard & Portfolio Analytics")
    st.caption(f"Last updated: {get_indian_time().strftime('%d-%m-%Y %H:%M:%S')} IST")
    
    # Get data for dashboard
    total_cust = run_query("SELECT COUNT(*) FROM customers")[0][0]
    kyc_pending = run_query("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'")[0][0]
    kyc_approved = run_query("SELECT COUNT(*) FROM customers WHERE kyc_status='APPROVED'")[0][0]
    sb_count = run_query("SELECT COUNT(*) FROM sb_accounts")[0][0]
    total_sb_dep = run_query("SELECT SUM(balance) FROM sb_accounts")[0][0] or 0.0
    total_fd = run_query("SELECT SUM(principal) FROM fixed_deposits WHERE status='ACTIVE'")[0][0] or 0.0
    total_rd = run_query("SELECT SUM(monthly_amount * installments_paid) FROM recurring_deposits WHERE status='ACTIVE'")[0][0] or 0.0
    total_transactions = run_query("SELECT COUNT(*) FROM transactions")[0][0]
    total_income = run_query("SELECT SUM(amount) FROM operational_finances WHERE type='INCOME'")[0][0] or 0.0
    total_expense = run_query("SELECT SUM(amount) FROM operational_finances WHERE type='EXPENSE'")[0][0] or 0.0
    
    # Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">👥 Total Customers</div>
            <div class="value">{total_cust}</div>
            <div class="change">✅ {kyc_approved} Approved • ⏳ {kyc_pending} Pending</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="border-left-color: #28a745;">
            <div class="label">💰 SB Accounts</div>
            <div class="value">{sb_count}</div>
            <div class="change">Total Deposits: ₹{total_sb_dep:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card" style="border-left-color: #ffc107;">
            <div class="label">📈 Deposit Portfolio</div>
            <div class="value">₹{(total_sb_dep + total_fd + total_rd):,.0f}</div>
            <div class="change">FD: ₹{total_fd:,.0f} • RD: ₹{total_rd:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card" style="border-left-color: #dc3545;">
            <div class="label">💳 Transaction Activity</div>
            <div class="value">{total_transactions}</div>
            <div class="change">Income: ₹{total_income:,.0f} • Expense: ₹{total_expense:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Charts Row
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.subheader("💰 Deposit Portfolio Distribution")
        portfolio_data = {
            "Deposit Type": ["Savings Bank (SB)", "Fixed Deposits (FD)", "Recurring Deposits (RD)"],
            "Amount": [total_sb_dep, total_fd, total_rd]
        }
        df_portfolio = pd.DataFrame(portfolio_data)
        if df_portfolio['Amount'].sum() > 0:
            fig = create_circular_chart(
                df_portfolio['Deposit Type'],
                df_portfolio['Amount'],
                "Deposit Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No deposit data available to display.")
    
    with chart_col2:
        st.subheader("📊 KYC Status Overview")
        kyc_data = {
            "Status": ["Approved", "Pending"],
            "Count": [kyc_approved, kyc_pending]
        }
        df_kyc = pd.DataFrame(kyc_data)
        if df_kyc['Count'].sum() > 0:
            fig = create_circular_chart(
                df_kyc['Status'],
                df_kyc['Count'],
                "KYC Status Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No KYC data available to display.")
    
    st.markdown("---")
    
    # SB Account Details Section
    st.subheader("💳 Savings Bank Account Details")
    sb_details = run_query("""
        SELECT s.account_no, c.name, s.balance, s.interest_rate, s.created_at
        FROM sb_accounts s 
        JOIN customers c ON s.customer_id = c.id
        ORDER BY s.balance DESC
        LIMIT 10
    """)
    
    if sb_details:
        df_sb_details = pd.DataFrame(sb_details, columns=["Account No", "Customer Name", "Balance (₹)", "Interest Rate (%)", "Created Date"])
        
        # Add some statistics
        col1, col2, col3 = st.columns(3)
        avg_balance = df_sb_details['Balance (₹)'].mean()
        max_balance = df_sb_details['Balance (₹)'].max()
        min_balance = df_sb_details['Balance (₹)'].min()
        
        col1.metric("Average SB Balance", f"₹{avg_balance:,.2f}")
        col2.metric("Highest Balance", f"₹{max_balance:,.2f}")
        col3.metric("Lowest Balance", f"₹{min_balance:,.2f}")
        
        st.dataframe(df_sb_details, use_container_width=True)
        
        # SB Balance Distribution Chart
        st.subheader("📈 SB Account Balance Distribution")
        fig = px.bar(
            df_sb_details,
            x="Customer Name",
            y="Balance (₹)",
            color="Balance (₹)",
            color_continuous_scale="Blues",
            title="Top 10 SB Account Balances",
            labels={"Customer Name": "Customer", "Balance (₹)": "Balance"}
        )
        fig.update_layout(
            height=400,
            showlegend=False,
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No SB accounts found.")
    
    st.markdown("---")
    
    # Recent Activity
    st.subheader("🔄 Recent Transaction Activity")
    recent_tx = run_query("""
        SELECT tx_id, account_no, type, amount, mode, date 
        FROM transactions 
        ORDER BY id DESC 
        LIMIT 10
    """)
    
    if recent_tx:
        df_tx = pd.DataFrame(recent_tx, columns=["Transaction ID", "Account No", "Type", "Amount (₹)", "Mode", "Date"])
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
                    """, (name, str(dob), gender, email, phone, street, city, state, pincode, pan, "[Redacted]", adhar_path, pan_path, sig_path, get_indian_date()), fetch=False)
                    st.success(f"✅ Customer {name} registered successfully!")
                    st.balloons()
                else:
                    st.error("Please fill in mandatory fields: Name and Phone.")

    with tab2:
        st.subheader("Customer Directory")
        customers = run_query("SELECT id, name, phone, email, kyc_status, pan, created_at FROM customers ORDER BY id DESC")
        if customers:
            df_cust = pd.DataFrame(customers, columns=["ID", "Name", "Phone", "Email", "KYC Status", "PAN", "Joined"])
            st.dataframe(df_cust, use_container_width=True)
            
            col_csv, col_pdf = st.columns(2)
            col_csv.download_button("📥 Download CSV Report", df_cust.to_csv(index=False).encode('utf-8'), "customers_report.csv", "text/csv")
            col_pdf.download_button("📥 Download PDF Report", create_pdf_report("Customer Directory Report", df_cust), "customers_report.pdf", "application/pdf")
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
                    st.success("✅ Customer details updated successfully!")

# --- 3. KYC VERIFICATION ---
elif menu == "KYC Verification":
    st.title("✅ KYC Verification Panel")
    pending = run_query("SELECT id, name, phone, pan, adhar_file, pan_file, signature_file, created_at FROM customers WHERE kyc_status='PENDING' ORDER BY id DESC")
    if pending:
        for p in pending:
            with st.expander(f"👤 Customer: {p[1]} (ID: {p[0]}) - 📱 {p[2]}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**PAN:** {p[3]}")
                    st.write(f"**Aadhaar File:** `{p[4]}`")
                    st.write(f"**PAN File:** `{p[5]}`")
                    st.write(f"**Signature:** `{p[6]}`")
                    st.write(f"**Registered:** {p[7]}")
                
                with col2:
                    st.write("### Verification Actions")
                    if st.button(f"✅ Approve KYC #{p[0]}", key=f"app_{p[0]}", use_container_width=True):
                        run_query("UPDATE customers SET kyc_status='APPROVED' WHERE id=?", (p[0],), fetch=False)
                        st.success(f"✅ KYC Approved for ID {p[0]}")
                        st.rerun()
                    if st.button(f"❌ Reject KYC #{p[0]}", key=f"rej_{p[0]}", use_container_width=True):
                        run_query("UPDATE customers SET kyc_status='REJECTED' WHERE id=?", (p[0],), fetch=False)
                        st.error(f"❌ KYC Rejected for ID {p[0]}")
                        st.rerun()
    else:
        st.info("🎉 No pending KYC verification requests.")

# --- 4. SB ACCOUNTS ---
elif menu == "SB Accounts":
    st.title("💰 Savings Bank (SB) Management")
    tab1, tab2, tab3 = st.tabs(["Open SB Account", "Transact (Deposit/Withdraw)", "View Accounts"])
    
    with tab1:
        customers = run_query("SELECT id, name FROM customers WHERE kyc_status='APPROVED'")
        if customers:
            cust_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers}
            selected_cust = st.selectbox("Select Customer Name", list(cust_dict.keys()))
            cust_id = cust_dict[selected_cust]
            
            init_bal = st.number_input("Opening Balance (₹)", min_value=0.0, value=500.0)
            mode = st.selectbox("Funding Mode", ["CASH", "BANK TRANSFER", "CHEQUE", "ONLINE"])
            
            if st.button("Create SB Account"):
                acc_no = f"SB{get_indian_time().strftime('%Y%m%d%H%M%S')}"
                run_query("INSERT INTO sb_accounts VALUES (?, ?, ?, 3.5, ?)", 
                          (acc_no, cust_id, init_bal, get_indian_date()), fetch=False)
                
                if init_bal > 0:
                    run_query("INSERT INTO transactions (tx_id, account_no, type, amount, mode, narration, date) VALUES (?, ?, 'CREDIT', ?, ?, 'Opening Balance Deposit', ?)",
                              (f"TX{get_indian_time().strftime('%M%S%f')}", acc_no, init_bal, mode, get_indian_date()), fetch=False)
                    post_automated_jv(f"SB Opening Balance - Account {acc_no}", "AST-101", "LIA-101", init_bal)

                st.success(f"✅ SB Account created successfully! Account No: {acc_no}")
                st.balloons()
        else:
            st.warning("⚠️ Please register and approve KYC for a customer first.")

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
                              (f"TX{get_indian_time().strftime('%M%S%f')}", acc_choice, db_type, amount, pay_mode, narration, get_indian_date()), fetch=False)
                    
                    if tx_type == "DEPOSIT":
                        post_automated_jv(f"SB Deposit: {narration} ({acc_choice})", "AST-101", "LIA-101", amount)
                    else:
                        post_automated_jv(f"SB Withdrawal: {narration} ({acc_choice})", "LIA-101", "AST-101", amount)

                    st.success(f"✅ Transaction successful! New Balance: ₹{new_bal:,.2f}")
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
            st.download_button("📥 Download SB Accounts PDF", create_pdf_report("Savings Bank Accounts Report", df_sb), "sb_accounts.pdf", "application/pdf")
        else:
            st.info("No active SB accounts found.")

# --- 5. FIXED DEPOSITS (FD) ---
elif menu == "Fixed Deposits (FD)":
    st.title("📈 Fixed Deposits Management")
    tab1, tab2 = st.tabs(["Open FD", "Active FDs & Closure"])
    
    with tab1:
        customers = run_query("SELECT id, name FROM customers WHERE kyc_status='APPROVED'")
        if customers:
            cust_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers}
            selected_cust = st.selectbox("Select Customer Name for FD", list(cust_dict.keys()), key="fd_cust")
            principal = st.number_input("Principal Amount (₹)", min_value=1000.0, value=10000.0, step=500.0)
            tenure = st.slider("Tenure (Months)", 1, 60, 12)
            interest_rate = st.number_input("Interest Rate (% p.a.)", value=6.5, min_value=0.0, max_value=15.0, step=0.5)
            nominee = st.text_input("Nominee Name")
            
            maturity_amount = principal + (principal * interest_rate * (tenure / 12) / 100)
            st.info(f"💰 Estimated Maturity Amount: **₹{maturity_amount:,.2f}**")
            
            if st.button("Open FD Account"):
                run_query("""
                    INSERT INTO fixed_deposits (customer_id, principal, tenure_months, interest_rate, maturity_amount, nominee, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
                """, (cust_dict[selected_cust], principal, tenure, interest_rate, maturity_amount, nominee, get_indian_date()), fetch=False)
                
                post_automated_jv(f"Fixed Deposit Opening - Principal ₹{principal}", "AST-101", "LIA-102", principal)
                st.success("✅ Fixed Deposit opened successfully!")
                st.balloons()
        else:
            st.warning("⚠️ Please register and approve KYC for a customer first.")

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
                    st.success(f"✅ FD #{fd_choice} successfully closed and settled for ₹{maturity_amt:,.2f}!")
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
        customers = run_query("SELECT id, name FROM customers WHERE kyc_status='APPROVED'")
        if customers:
            cust_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers}
            selected_cust = st.selectbox("Select Customer Name for RD", list(cust_dict.keys()), key="rd_cust")
            monthly_amt = st.number_input("Monthly Installment Amount (₹)", min_value=100.0, value=1000.0)
            tenure = st.slider("Tenure (Months)", 6, 60, 12, key="rd_tenure")
            interest_rate = st.number_input("Interest Rate (% p.a.)", value=6.0, key="rd_rate", min_value=0.0, max_value=15.0, step=0.5)
            nominee = st.text_input("Nominee Name", key="rd_nom")
            
            if st.button("Open RD Account"):
                run_query("""
                    INSERT INTO recurring_deposits (customer_id, monthly_amount, tenure_months, interest_rate, installments_paid, nominee, status, created_at)
                    VALUES (?, ?, ?, ?, 0, ?, 'ACTIVE', ?)
                """, (cust_dict[selected_cust], monthly_amt, tenure, interest_rate, nominee, get_indian_date()), fetch=False)
                st.success("✅ Recurring Deposit opened successfully!")
                st.balloons()
        else:
            st.warning("⚠️ Please register and approve KYC for a customer first.")

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
                    st.success(f"✅ Installment #{new_paid} successfully paid!")
                    st.rerun()
                else:
                    st.warning("⚠️ All installments completed!")
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
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Add Funds to Retrieval Pool")
        customers = run_query("SELECT id, name FROM customers WHERE kyc_status='APPROVED'")
        if customers:
            cust_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers}
            selected_cust = st.selectbox("Select Customer", list(cust_dict.keys()))
            amount = st.number_input("Amount to Add (₹)", min_value=1.0, value=1000.0)
            
            if st.button("Add to Retrieval Account"):
                ret_acc_no = f"RET{get_indian_time().strftime('%Y%m%d%H%M%S')}"
                # Check if customer already has a retrieval account
                existing = run_query("SELECT account_no FROM retrieval_accounts WHERE customer_id=?", (cust_dict[selected_cust],))
                if existing:
                    acc_no = existing[0][0]
                    run_query("UPDATE retrieval_accounts SET balance = balance + ? WHERE account_no=?", (amount, acc_no), fetch=False)
                else:
                    run_query("INSERT INTO retrieval_accounts VALUES (?, ?, ?)", (ret_acc_no, cust_dict[selected_cust], amount), fetch=False)
                    acc_no = ret_acc_no
                
                post_automated_jv(f"Retrieval Pool Deposit - Customer ID {cust_dict[selected_cust]}", "AST-101", "AST-103", amount)
                st.success(f"✅ ₹{amount:,.2f} added to Retrieval Account {acc_no}")
        else:
            st.info("No KYC approved customers available.")
    
    with col2:
        st.subheader("Retrieval Account Balances")
        ret_accs = run_query("""
            SELECT r.account_no, c.name, r.balance 
            FROM retrieval_accounts r JOIN customers c ON r.customer_id = c.id
        """)
        if ret_accs:
            df_ret = pd.DataFrame(ret_accs, columns=["Retrieval Account No", "Customer Name", "Balance (₹)"])
            st.dataframe(df_ret, use_container_width=True)
            
            total_ret_balance = sum(r[2] for r in ret_accs)
            st.metric("Total Retrieval Pool Balance", f"₹{total_ret_balance:,.2f}")
        else:
            st.info("No funds currently resting in the Retrieval Accounts pool.")

# --- 8. CHART OF ACCOUNTS ---
elif menu == "Chart of Accounts":
    st.title("📊 Financial Chart of Accounts")
    accounts = run_query("SELECT account_code, account_name, account_type, category FROM chart_of_accounts ORDER BY account_type, account_code")
    if accounts:
        df_coa = pd.DataFrame(accounts, columns=["Account Code", "Account Name", "Account Type", "Category"])
        st.dataframe(df_coa, use_container_width=True)
        
        # Summary statistics
        st.markdown("---")
        st.subheader("Chart of Accounts Summary")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Income Accounts", len([a for a in accounts if a[2] == "Income"]))
        col2.metric("Expense Accounts", len([a for a in accounts if a[2] == "Expense"]))
        col3.metric("Asset Accounts", len([a for a in accounts if a[2] == "Asset"]))
        col4.metric("Liability Accounts", len([a for a in accounts if a[2] == "Liability"]))
    else:
        st.info("No accounts found in chart of accounts.")

# --- 9. TRANSACTIONS ---
elif menu == "Transactions":
    st.title("💳 Transaction Ledger")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        tx_type_filter = st.selectbox("Filter by Type", ["All", "CREDIT", "DEBIT"])
    with col2:
        mode_filter = st.selectbox("Filter by Mode", ["All", "CASH", "BANK TRANSFER", "CHEQUE", "ONLINE"])
    with col3:
        date_filter = st.date_input("Filter by Date (Last 7 Days)", value=date.today())
    
    # Build query with filters
    query = "SELECT id, tx_id, account_no, type, amount, mode, narration, date FROM transactions"
    conditions = []
    params = []
    
    if tx_type_filter != "All":
        conditions.append("type = ?")
        params.append(tx_type_filter)
    if mode_filter != "All":
        conditions.append("mode = ?")
        params.append(mode_filter)
    if date_filter:
        conditions.append("date >= date('now', '-7 days')")
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC"
    
    txs = run_query(query, tuple(params))
    if txs:
        df_all_tx = pd.DataFrame(txs, columns=["ID", "Tx ID", "Account No", "Type", "Amount (₹)", "Mode", "Narration", "Date"])
        st.dataframe(df_all_tx, use_container_width=True)
        
        # Summary stats
        total_debit = sum(t[4] for t in txs if t[3] == "DEBIT")
        total_credit = sum(t[4] for t in txs if t[3] == "CREDIT")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Transactions", len(txs))
        col2.metric("Total Debits", f"₹{total_debit:,.2f}")
        col3.metric("Total Credits", f"₹{total_credit:,.2f}")
    else:
        st.info("No transaction logs recorded.")

# --- 10. JOURNAL VOUCHERS ---
elif menu == "Journal Vouchers":
    st.title("📝 Journal Vouchers Ledger")
    jvs = run_query("SELECT jv_id, voucher_date, narration, status FROM journal_vouchers ORDER BY jv_id DESC")
    if jvs:
        df_jvs = pd.DataFrame(jvs, columns=["JV ID", "Date", "Narration", "Status"])
        st.dataframe(df_jvs, use_container_width=True)
        
        # View entries for selected JV
        st.markdown("---")
        jv_choice = st.selectbox("Select JV ID to View Details", [j[0] for j in jvs])
        if jv_choice:
            entries = run_query("""
                SELECT jv_id, account_code, debit, credit 
                FROM jv_entries 
                WHERE jv_id = ?
            """, (jv_choice,))
            if entries:
                df_entries = pd.DataFrame(entries, columns=["JV ID", "Account Code", "Debit (₹)", "Credit (₹)"])
                st.dataframe(df_entries, use_container_width=True)
                
                total_debit = sum(e[2] for e in entries)
                total_credit = sum(e[3] for e in entries)
                
                col1, col2 = st.columns(2)
                col1.metric("Total Debit", f"₹{total_debit:,.2f}")
                col2.metric("Total Credit", f"₹{total_credit:,.2f}")
                
                if abs(total_debit - total_credit) < 0.01:
                    st.success("✅ Voucher is balanced!")
                else:
                    st.warning("⚠️ Voucher is not balanced!")
    else:
        st.info("No journal vouchers found.")

# --- 11. INCOME & EXPENSES ---
elif menu == "Income & Expenses":
    st.title("💰 Operational Income & Expenses")
    
    # Add new entry
    with st.expander("➕ Record New Income/Expense"):
        col1, col2 = st.columns(2)
        with col1:
            entry_type = st.selectbox("Type", ["INCOME", "EXPENSE"])
            accounts = run_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type IN ('Income', 'Expense')")
            if accounts:
                acc_dict = {f"{a[1]} ({a[0]})": a[0] for a in accounts}
                selected_acc = st.selectbox("Account", list(acc_dict.keys()))
                account_code = acc_dict[selected_acc]
            else:
                account_code = ""
        with col2:
            amount = st.number_input("Amount (₹)", min_value=1.0, value=1000.0)
            mode = st.selectbox("Mode", ["CASH", "BANK TRANSFER", "CHEQUE", "ONLINE"])
            narration = st.text_input("Narration")
            customer_id = st.number_input("Customer ID (if applicable)", min_value=0, value=0)
        
        if st.button("Record Entry"):
            if account_code:
                run_query("""
                    INSERT INTO operational_finances (type, customer_id, account_code, amount, mode, date, narration)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (entry_type, customer_id if customer_id > 0 else None, account_code, amount, mode, get_indian_date(), narration), fetch=False)
                st.success("✅ Entry recorded successfully!")
            else:
                st.error("Please select an account.")
    
    st.markdown("---")
    
    # View entries
    finances = run_query("""
        SELECT o.id, o.type, c.name, o.account_code, o.amount, o.mode, o.date, o.narration 
        FROM operational_finances o LEFT JOIN customers c ON o.customer_id = c.id
        ORDER BY o.id DESC
    """)
    if finances:
        df_fin = pd.DataFrame(finances, columns=["ID", "Type", "Customer Name", "Account Code", "Amount (₹)", "Mode", "Date", "Narration"])
        st.dataframe(df_fin, use_container_width=True)
        
        # Summary
        total_income = sum(f[4] for f in finances if f[1] == "INCOME")
        total_expense = sum(f[4] for f in finances if f[1] == "EXPENSE")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"₹{total_income:,.2f}")
        col2.metric("Total Expenses", f"₹{total_expense:,.2f}")
        col3.metric("Net Profit/Loss", f"₹{total_income - total_expense:,.2f}")
    else:
        st.info("No operational financial logs recorded.")

# --- 12. INTEREST CALCULATION ---
elif menu == "Interest Calculation":
    st.title("📊 Interest Calculation & Posting")
    
    tab1, tab2 = st.tabs(["Savings Bank Interest", "Deposit Interest"])
    
    with tab1:
        st.subheader("SB Interest Calculation")
        sb_records = run_query("""
            SELECT s.account_no, c.name, s.balance, s.interest_rate 
            FROM sb_accounts s JOIN customers c ON s.customer_id = c.id
        """)
        if sb_records:
            df_sb_calc = pd.DataFrame(sb_records, columns=["Account No", "Customer", "Balance (₹)", "Rate (%)"])
            st.dataframe(df_sb_calc, use_container_width=True)
            
            # Calculate monthly interest
            df_sb_calc['Monthly Interest (₹)'] = df_sb_calc['Balance (₹)'] * (df_sb_calc['Rate (%)'] / 100) / 12
            total_interest = df_sb_calc['Monthly Interest (₹)'].sum()
            
            st.metric("Total Monthly Interest Payable", f"₹{total_interest:,.2f}")
            
            if st.button("Post SB Interest"):
                for _, row in df_sb_calc.iterrows():
                    interest = row['Monthly Interest (₹)']
                    if interest > 0:
                        post_automated_jv(f"SB Interest for Account {row['Account No']}", "EXP-101", "LIA-101", interest)
                st.success(f"✅ Interest posted for all SB accounts! Total: ₹{total_interest:,.2f}")
        else:
            st.info("No SB accounts found.")
    
    with tab2:
        st.subheader("FD & RD Interest Calculation")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Fixed Deposits**")
            fds = run_query("SELECT fd_id, principal, interest_rate FROM fixed_deposits WHERE status='ACTIVE'")
            if fds:
                df_fd = pd.DataFrame(fds, columns=["FD ID", "Principal (₹)", "Rate (%)"])
                df_fd['Annual Interest (₹)'] = df_fd['Principal (₹)'] * (df_fd['Rate (%)'] / 100)
                st.dataframe(df_fd, use_container_width=True)
                st.metric("Total Annual FD Interest", f"₹{df_fd['Annual Interest (₹)'].sum():,.2f}")
            else:
                st.info("No active FDs found.")
        
        with col2:
            st.write("**Recurring Deposits**")
            rds = run_query("""
                SELECT rd_id, monthly_amount, interest_rate, installments_paid 
                FROM recurring_deposits WHERE status='ACTIVE'
            """)
            if rds:
                df_rd = pd.DataFrame(rds, columns=["RD ID", "Monthly (₹)", "Rate (%)", "Installments Paid"])
                df_rd['Accrued Interest (₹)'] = df_rd['Monthly (₹)'] * df_rd['Installments Paid'] * (df_rd['Rate (%)'] / 100) / 12
                st.dataframe(df_rd, use_container_width=True)
                st.metric("Total Accrued RD Interest", f"₹{df_rd['Accrued Interest (₹)'].sum():,.2f}")
            else:
                st.info("No active RDs found.")

# --- 13. ADMIN RECORD EDITOR ---
elif menu == "Admin Record Editor":
    st.title("🛠️ Database Record Editor")
    st.warning("⚠️ Admin access only. Changes made here are permanent!")
    
    tables_res = run_query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    table_list = [t[0] for t in tables_res]
    selected_table = st.selectbox("Select Database Table to Inspect", table_list)
    
    if selected_table:
        rows = run_query(f"SELECT * FROM {selected_table}")
        columns_info = run_query(f"PRAGMA table_info({selected_table})")
        columns = [col[1] for col in columns_info]
        df_table = pd.DataFrame(rows, columns=columns)
        st.dataframe(df_table, use_container_width=True)
        st.caption(f"Total records: {len(rows)}")

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
            
            total_debits = sum(e[2] for e in entries)
            total_credits = sum(e[3] for e in entries)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Debits", f"₹{total_debits:,.2f}")
            col2.metric("Total Credits", f"₹{total_credits:,.2f}")
            col3.metric("Difference", f"₹{total_debits - total_credits:,.2f}")
            
            st.download_button("📥 Download Trial Balance PDF", create_pdf_report("Trial Balance Statement", df_tb), "trial_balance.pdf", "application/pdf")
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
            st.success("✅ Balance Sheet Perfectly Balanced!")
        else:
            st.warning(f"⚠️ Balance Sheet Discrepancy / Difference: ₹{diff:,.2f}")

        if st.button("📥 Export Balance Sheet Report"):
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
            st.download_button("📥 Download Balance Sheet PDF", create_pdf_report("Balance Sheet Statement", df_bs), "balance_sheet.pdf", "application/pdf")

    with tab3:
        st.subheader("Profit & Loss Statement")
        total_income = run_query("SELECT SUM(amount) FROM operational_finances WHERE type='INCOME'")[0][0] or 0.0
        total_expense = run_query("SELECT SUM(amount) FROM operational_finances WHERE type='EXPENSE'")[0][0] or 0.0
        net_pl = total_income - total_expense
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"₹{total_income:,.2f}", delta=f"+₹{total_income:,.2f}")
        col2.metric("Total Expenses", f"₹{total_expense:,.2f}", delta=f"-₹{total_expense:,.2f}")
        col3.metric("Net Profit / Loss", f"₹{net_pl:,.2f}", delta=f"{'Profit' if net_pl > 0 else 'Loss'}")
        
        # Income vs Expense Chart
        if total_income > 0 or total_expense > 0:
            fig = go.Figure(data=[
                go.Bar(name='Income', x=['Income'], y=[total_income], marker_color='#28a745'),
                go.Bar(name='Expense', x=['Expense'], y=[total_expense], marker_color='#dc3545')
            ])
            fig.update_layout(
                title="Income vs Expense Comparison",
                height=300,
                showlegend=True,
                barmode='group'
            )
            st.plotly_chart(fig, use_container_width=True)

# --- 15. REPORTS ---
elif menu == "Reports":
    st.title("📄 Comprehensive Bank Reports Center")
    report_type = st.selectbox("Select Report to Generate", [
        "Customer List Report", "Daily Transactions Report", "FD Summary Report", 
        "RD Summary Report", "SB Account Summary", "KYC Status Report"
    ])
    
    if st.button("📊 Generate Report"):
        if "Customer" in report_type:
            data = run_query("SELECT id, name, phone, email, kyc_status, created_at FROM customers ORDER BY id DESC")
            df = pd.DataFrame(data, columns=["ID", "Name", "Phone", "Email", "KYC Status", "Joined"])
        elif "Transaction" in report_type:
            data = run_query("""
                SELECT tx_id, account_no, type, amount, mode, date 
                FROM transactions 
                WHERE date = date('now')
                ORDER BY id DESC
            """)
            df = pd.DataFrame(data, columns=["Tx ID", "Account No", "Type", "Amount", "Mode", "Date"])
        elif "FD" in report_type:
            data = run_query("""
                SELECT f.fd_id, c.name, f.principal, f.maturity_amount, f.status 
                FROM fixed_deposits f JOIN customers c ON f.customer_id = c.id
            """)
            df = pd.DataFrame(data, columns=["FD ID", "Customer Name", "Principal", "Maturity", "Status"])
        elif "RD" in report_type:
            data = run_query("""
                SELECT r.rd_id, c.name, r.monthly_amount, r.installments_paid, r.status 
                FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id
            """)
            df = pd.DataFrame(data, columns=["RD ID", "Customer Name", "Monthly", "Paid", "Status"])
        elif "SB" in report_type:
            data = run_query("""
                SELECT s.account_no, c.name, s.balance, s.interest_rate, s.created_at 
                FROM sb_accounts s JOIN customers c ON s.customer_id = c.id
            """)
            df = pd.DataFrame(data, columns=["Account No", "Customer", "Balance", "Interest Rate", "Created"])
        elif "KYC" in report_type:
            data = run_query("""
                SELECT kyc_status, COUNT(*) as count 
                FROM customers 
                GROUP BY kyc_status
            """)
            df = pd.DataFrame(data, columns=["KYC Status", "Count"])
        
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "📥 Download PDF Report", 
            create_pdf_report(report_type, df), 
            f"{report_type.lower().replace(' ', '_')}.pdf", 
            "application/pdf"
        )
        
        # Show summary statistics
        st.markdown("---")
        st.subheader("Report Summary")
        st.write(f"**Total Records:** {len(df)}")
        if 'Amount' in df.columns:
            st.write(f"**Total Amount:** ₹{df['Amount'].sum():,.2f}")
        if 'Balance' in df.columns:
            st.write(f"**Total Balance:** ₹{df['Balance'].sum():,.2f}")

# --- 16. CUSTOMER PORTAL & LOGIN ---
elif menu == "Customer Portal":
    st.title("🔐 Customer Portal & Account Statement Generator")
    
    # Secure Login Box
    st.markdown("### Secure Customer Login")
    with st.form("customer_login_form"):
        login_cust_id = st.number_input("Customer ID", min_value=1, step=1)
        login_phone = st.text_input("Registered Phone Number", type="password")
        login_submitted = st.form_submit_button("🔑 Login to Portal")
        
    if login_submitted:
        auth_check = run_query("SELECT id, name, phone, kyc_status FROM customers WHERE id=? AND phone=?", (login_cust_id, login_phone))
        if auth_check:
            st.session_state['authenticated_customer'] = auth_check[0]
            st.success(f"✅ Login successful! Welcome back, {auth_check[0][1]}.")
            st.balloons()
        else:
            st.error("❌ Invalid Customer ID or Phone Number combination.")

    # Render Customer Dashboard if Authenticated
    if 'authenticated_customer' in st.session_state:
        cust_id, name, phone, kyc = st.session_state['authenticated_customer']
        
        st.markdown("---")
        st.subheader(f"👋 Welcome, {name} (Customer ID: {cust_id})")
        
        # Status indicators
        col1, col2, col3 = st.columns(3)
        col1.metric("KYC Status", kyc)
        col2.metric("Phone", phone)
        col3.metric("Member Since", run_query("SELECT created_at FROM customers WHERE id=?", (cust_id,))[0][0])
        
        # Container for All Customer Accounts
        st.markdown("### 🏦 Your Active Accounts & Portfolios")
        
        # 1. Savings Accounts
        sb_accs = run_query("SELECT account_no, balance, interest_rate, created_at FROM sb_accounts WHERE customer_id=?", (cust_id,))
        if sb_accs:
            st.write("#### 💰 Savings Bank (SB) Accounts")
            df_cust_sb = pd.DataFrame(sb_accs, columns=["Account No", "Balance (₹)", "Interest Rate (%)", "Opened Date"])
            st.dataframe(df_cust_sb, use_container_width=True)
            
            # SB Balance Chart
            fig = px.pie(
                df_cust_sb,
                values="Balance (₹)",
                names="Account No",
                title="SB Account Distribution",
                hole=0.3
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
            
        # 2. Fixed Deposits
        fd_accs = run_query("SELECT fd_id, principal, tenure_months, interest_rate, maturity_amount, status FROM fixed_deposits WHERE customer_id=?", (cust_id,))
        if fd_accs:
            st.write("#### 📈 Fixed Deposits (FD)")
            df_cust_fd = pd.DataFrame(fd_accs, columns=["FD ID", "Principal (₹)", "Tenure (M)", "Rate (%)", "Maturity (₹)", "Status"])
            st.dataframe(df_cust_fd, use_container_width=True)

        # 3. Recurring Deposits
        rd_accs = run_query("SELECT rd_id, monthly_amount, tenure_months, interest_rate, installments_paid, status FROM recurring_deposits WHERE customer_id=?", (cust_id,))
        if rd_accs:
            st.write("#### 🔄 Recurring Deposits (RD)")
            df_cust_rd = pd.DataFrame(rd_accs, columns=["RD ID", "Monthly (₹)", "Tenure (M)", "Rate (%)", "Installments Paid", "Status"])
            st.dataframe(df_cust_rd, use_container_width=True)

        # 4. Retrieval Pool Account
        ret_accs = run_query("SELECT account_no, balance FROM retrieval_accounts WHERE customer_id=?", (cust_id,))
        if ret_accs:
            st.write("#### 💳 Retrieval Pool Accounts")
            df_cust_ret = pd.DataFrame(ret_accs, columns=["Account No", "Balance (₹)"])
            st.dataframe(df_cust_ret, use_container_width=True)

        st.markdown("---")
        st.subheader("📥 Download Consolidated Account Statement")
        if st.button("📄 Generate Consolidated Statement PDF"):
            # Consolidate user data into a clean report format
            statement_data = []
            if sb_accs:
                for a in sb_accs:
                    statement_data.append(["Savings Account", a[0], f"Balance: ₹{a[1]:,.2f}"])
            if fd_accs:
                for f in fd_accs:
                    statement_data.append(["Fixed Deposit", f"FD #{f[0]}", f"Principal: ₹{f[1]:,.2f} | Maturity: ₹{f[4]:,.2f}"])
            if rd_accs:
                for r in rd_accs:
                    statement_data.append(["Recurring Deposit", f"RD #{r[0]}", f"Monthly: ₹{r[1]:,.2f} | Paid: {r[4]}/{r[2]}"])
            
            if statement_data:
                df_statement = pd.DataFrame(statement_data, columns=["Account Type", "Identifier", "Details"])
                st.download_button(
                    "📥 Download Statement PDF Report", 
                    create_pdf_report(f"Consolidated Statement - {name}", df_statement), 
                    f"statement_{cust_id}_{get_indian_time().strftime('%Y%m%d')}.pdf", 
                    "application/pdf"
                )
            else:
                st.info("No accounts available to export.")
                
        if st.button("🚪 Logout"):
            del st.session_state['authenticated_customer']
            st.rerun()

# --- FOOTER ---
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>© 2025 Aasha Nidhi Bank • Empowering Financial Growth</p>
    <p style="font-size: 0.8rem;">All rights reserved • Developed with ❤️ in India</p>
</div>
""", unsafe_allow_html=True)
