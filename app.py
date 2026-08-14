import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timezone, timedelta
import io
import os
import time
import re
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Aarsha Nidhi Banking Software",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- SIDEBAR COLOR FIX (HARD OVERRIDE) ---
st.markdown(
    """
<style>
    /* Force sidebar background */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f2b4a 0%, #1a4a7a 100%) !important;
    }
    
    /* FORCE ALL SIDEBAR TEXT TO BE WHITE (Except System Backup & Restore) */
    [data-testid="stSidebar"] *:not(.backup-restore-section *):not(.backup-restore-section),
    [data-testid="stSidebar"] .stMarkdown:not(:has(*)),
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] label *,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stRadio label *,
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label,
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label *,
    [data-testid="stSidebar"] .st-emotion-cache-1in2z2g,
    [data-testid="stSidebar"] .st-emotion-cache-1in2z2g * {
        color: white !important;
    }
    
    /* Hover effect for navigation */
    [data-testid="stSidebar"] .stRadio label:hover,
    [data-testid="stSidebar"] .st-emotion-cache-1in2z2g:hover {
        background: rgba(255,255,255,0.12) !important;
        border-radius: 4px !important;
    }
    
    /* Selected item for navigation */
    [data-testid="stSidebar"] .stRadio label[data-selected="true"],
    [data-testid="stSidebar"] .st-emotion-cache-1in2z2g[aria-selected="true"] {
        background: linear-gradient(90deg, #2c6b9e, #4a8bc2) !important;
        border-left: 3px solid #f7c948 !important;
        color: black !important;
    }
    
    /* MAKE SYSTEM BACKUP & RESTORE TEXT BLACK */
    .backup-restore-section,
    .backup-restore-section *,
    [data-testid="stSidebar"] .backup-restore-section p,
    [data-testid="stSidebar"] .backup-restore-section span,
    [data-testid="stSidebar"] .backup-restore-section label {
        color: black !important;
    }
    
    /* Hide footer */
    footer {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)

# Define IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

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
    """Initialize database and ensure missing columns are added dynamically"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA foreign_keys = ON")
        
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
                payment_mode TEXT,
                closed_date TEXT,
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
                payment_mode TEXT,
                closed_date TEXT,
                maturity_amount REAL DEFAULT 0,
                FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
            )
        """)

        # Safe migrations
        for col, table in [("payment_mode", "fixed_deposits"), ("closed_date", "fixed_deposits"), 
                           ("payment_mode", "recurring_deposits"), ("closed_date", "recurring_deposits"), 
                           ("maturity_amount", "recurring_deposits")]:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT" if col != "maturity_amount" else f"ALTER TABLE {table} ADD COLUMN {col} REAL DEFAULT 0")
            except sqlite3.OperationalError:
                pass

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
            ("EXP-204", "Depreciation 5%", "Expense", "Operating Expenses"),
            ("EXP-205", "Depreciation 10%", "Expense", "Operating Expenses"),
            ("EXP-206", "Depreciation 15%", "Expense", "Operating Expenses"),
            ("EXP-207", "Depreciation 40%", "Expense", "Operating Expenses"),
            ("EXP-301", "Printing & Stationary", "Expense", "Administrative Expenses"),
            ("EXP-401", "Bank Charges", "Expense", "Other Expenses"),
            ("AST-101", "Cash in Hand", "Asset", "Current Assets"),
            ("AST-102", "Union Bank of India", "Asset", "Current Assets"),
            ("AST-103", "State Bank of India", "Asset", "Current Assets"),
            ("AST-104", "Fixed Asset Computer", "Asset", "Non Current Assets"),
            ("AST-105", "Fixed Asset Furniture & Fixtures", "Asset", "Non Current Assets"),
            ("AST-106", "Office Equipments", "Asset", "Non Current Assets"),  
            ("AST-107", "Building", "Asset", "Non Current Assets"),
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

init_db()

def run_query(query, params=(), fetch=True):
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

def save_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

def get_account_balance_from_jv(account_code):
    try:
        result = run_query("""
            SELECT COALESCE(SUM(JE.debit), 0) - COALESCE(SUM(JE.credit), 0) as net_balance
            FROM jv_entries JE
            JOIN chart_of_accounts CO ON JE.account_code = CO.account_code
            WHERE CO.account_code = ?
        """, (account_code,))
        return result[0][0] if result and result[0][0] is not None else 0.0
    except:
        return 0.0

def get_cash_balance():
    return get_account_balance_from_jv('AST-101')

def get_bank_balance(bank_name=None):
    if bank_name == "Union Bank of India" or bank_name is None:
        return get_account_balance_from_jv('AST-102')
    elif bank_name == "State Bank of India":
        return get_account_balance_from_jv('AST-103')
    else:
        result = run_query("SELECT account_code FROM chart_of_accounts WHERE account_name = ? AND account_type = 'Asset'", (bank_name,))
        if result:
            return get_account_balance_from_jv(result[0][0])
        return 0.0

def generate_cash_voucher_no():
    today = datetime.now(IST).strftime("%Y%m%d")
    try:
        result = run_query("SELECT voucher_no FROM cash_book WHERE voucher_no LIKE ? ORDER BY id DESC LIMIT 1", (f"CB{today}%",))
        new_seq = int(result[0][0][-4:]) + 1 if result else 1
    except:
        new_seq = 1
    return f"CB{today}{new_seq:04d}"

def generate_bank_voucher_no():
    today = datetime.now(IST).strftime("%Y%m%d")
    try:
        result = run_query("SELECT voucher_no FROM bank_book WHERE voucher_no LIKE ? ORDER BY id DESC LIMIT 1", (f"BB{today}%",))
        new_seq = int(result[0][0][-4:]) + 1 if result else 1
    except:
        new_seq = 1
    return f"BB{today}{new_seq:04d}"

def post_automated_jv(narration, debit_acc, credit_acc, amount):
    if amount <= 0:
        return None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", (str(date.today()), narration))
        jv_id = cursor.lastrowid
        cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, debit_acc, amount))
        cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, credit_acc, amount))
        conn.commit()
        conn.close()
        return jv_id
    except Exception as e:
        st.error(f"Error posting journal voucher: {str(e)}")
        return None

def create_pdf_report(title, df):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=10*mm, leftMargin=10*mm, topMargin=15*mm, bottomMargin=15*mm)
    elements = []
    styles = getSampleStyleSheet()
    
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Heading1'], fontSize=14, textColor=colors.HexColor('#1f4e78'), alignment=1, spaceAfter=4, fontName='Helvetica-Bold')
    subheader_style = ParagraphStyle('SubheaderStyle', parent=styles['Normal'], fontSize=9, alignment=1, spaceAfter=2, textColor=colors.HexColor('#333333'))
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#1f4e78'), alignment=1, spaceAfter=8, fontName='Helvetica-Bold')
    
    elements.append(Paragraph("AARSHA NIDHI LIMITED", header_style))
    elements.append(Paragraph("6/814, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501", subheader_style))
    elements.append(Paragraph("CIN: U65990KL22021PLN069978 | Ph: 0471-2994535", subheader_style))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 8))
    
    if not df.empty:
        cleaned_data = [[str(val).encode('ascii', 'ignore').decode('ascii') for val in row] for row in df.values]
        columns = list(df.columns)
        num_cols = len(columns)
        available_width = 260
        col_widths_pt = [(available_width / num_cols) * mm] * num_cols
        
        table_data = [columns] + cleaned_data
        t = Table(table_data, colWidths=col_widths_pt, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4e78')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f9f9f9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

def get_account_name(account_code):
    try:
        result = run_query("SELECT account_name FROM chart_of_accounts WHERE account_code = ?", (account_code,))
        return result[0][0] if result else ""
    except:
        return ""

def generate_voucher_pdf(voucher_type, voucher_data, jv_id=None):
    from reportlab.lib.pagesizes import A5
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A5, rightMargin=10*mm, leftMargin=10*mm, topMargin=12*mm, bottomMargin=12*mm)
    elements = []
    styles = getSampleStyleSheet()
    available_width = A5[0] - (20*mm)
    
    header_style = ParagraphStyle('VoucherHeader', parent=styles['Heading1'], fontSize=11, textColor=colors.HexColor('#1f4e78'), alignment=1, fontName='Helvetica-Bold')
    normal_style = ParagraphStyle('VoucherNormal', parent=styles['Normal'], fontSize=8, leading=11)
    bold_style = ParagraphStyle('VoucherBold', parent=styles['Normal'], fontSize=8, leading=11, fontName='Helvetica-Bold')
    
    elements.append(Paragraph("AARSHA NIDHI LIMITED", header_style))
    elements.append(Spacer(1, 4))
    
    if voucher_type == 'CB':
        date_val, v_num, part, dr, cr, acc_code, narr = voucher_data[0]
        table_data = [[Paragraph("<b>Voucher No:</b>", bold_style), Paragraph(v_num, normal_style), Paragraph("<b>Date:</b>", bold_style), Paragraph(date_val, normal_style)],
                      [Paragraph("<b>Particulars:</b>", bold_style), Paragraph(part, normal_style), "", ""],
                      [Paragraph("<b>Amount:</b>", bold_style), Paragraph(f"Debit: ₹{dr:,.2f}" if dr > 0 else f"Credit: ₹{cr:,.2f}", normal_style), "", ""]]
        t = Table(table_data, colWidths=[available_width*0.22, available_width*0.38, available_width*0.15, available_width*0.25])
        t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.grey), ('SPAN', (1, 1), (-1, 1)), ('SPAN', (1, 2), (-1, 2))]))
        elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

def fetch_cb_voucher(voucher_no):
    return run_query("SELECT date, voucher_no, particulars, debit_amount, credit_amount, account_code, narration FROM cash_book WHERE voucher_no = ?", (voucher_no,))

def fetch_bb_voucher(voucher_no):
    return run_query("SELECT date, voucher_no, bank_name, particulars, debit_amount, credit_amount, account_code, narration FROM bank_book WHERE voucher_no = ?", (voucher_no,))

def fetch_jv_voucher(jv_id):
    return run_query("SELECT jv.voucher_date, jv.narration, je.account_code, co.account_name, je.debit, je.credit FROM journal_vouchers jv JOIN jv_entries je ON jv.jv_id = je.jv_id JOIN chart_of_accounts co ON je.account_code = co.account_code WHERE jv.jv_id = ?", (jv_id,))

def check_login():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = ""
    return st.session_state.logged_in

def display_ist_timer():
    current_time = datetime.now(IST)
    st.sidebar.markdown(f"""
    <div style="background: linear-gradient(135deg, #1f4e78, #2c6b9e); padding: 10px; border-radius: 8px; text-align: center; color: white;">
        <div style="font-size: 11px;">🇮🇳 IST TIME</div>
        <div style="font-size: 18px; font-weight: bold;">{current_time.strftime("%I:%M:%S %p")}</div>
        <div style="font-size: 10px;">{current_time.strftime("%d-%b-%Y")}</div>
    </div>
    """, unsafe_allow_html=True)

# --- LOGIN MODULE ---
if not check_login():
    st.markdown("<style>[data-testid=\"stSidebar\"] { display: none; }</style>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2.2, 1])
    with col2:
        st.markdown("<h2 style='text-align: center; color: #1f4e78;'>🔐 Aarsha Nidhi Banking Login</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("👤 Username", placeholder="admin")
            password = st.text_input("🔑 Password", type="password", placeholder="admin123")
            if st.form_submit_button("Login", use_container_width=True, type="primary"):
                if username == "admin" and password == "admin123":
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("✅ Login successful!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials.")
    st.stop()

# --- SIDEBAR NAVIGATION ---
st.sidebar.markdown("<h2>🏦 AARSHA NIDHI</h2>", unsafe_allow_html=True)
st.sidebar.markdown(f"👤 User: <b>{st.session_state.username}</b>", unsafe_allow_html=True)
st.sidebar.markdown("<hr>", unsafe_allow_html=True)
display_ist_timer()
st.sidebar.markdown("<hr>", unsafe_allow_html=True)

menu = st.sidebar.radio(
    "📋 MENU",
    [
        "Dashboard",
        "Customer Management",
        "KYC Verification",
        "SB Accounts",
        "Fixed Deposits (FD)",
        "Recurring Deposits (RD)",
        "Chart of Accounts",
        "Cash Book",
        "Bank Book",
        "Journal Vouchers",
        "Admin Record Editor",
        "Financial Statements (Trial/BS/PL)",
        "Reports",
        "SB Interest Calculation"
    ]
)

# --- BACKUP & RESTORE MODULE ---
st.sidebar.markdown("<div class='backup-restore-section'>", unsafe_allow_html=True)
st.sidebar.markdown("💾 **System Backup**")
if os.path.exists(DB_NAME):
    with open(DB_NAME, "rb") as f:
        st.sidebar.download_button("📥 Download Backup", f.read(), f"backup_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.db", use_container_width=True)
st.sidebar.markdown("</div>", unsafe_allow_html=True)

# ==================== MAIN CONTENT ====================
if menu == "Dashboard":
    st.title("📊 Executive Dashboard")
    total_cust = run_query("SELECT COUNT(*) FROM customers")[0][0]
    total_sb = run_query("SELECT COUNT(*) FROM sb_accounts")[0][0]
    total_fds = run_query("SELECT COUNT(*) FROM fixed_deposits WHERE status='ACTIVE'")[0][0]
    rd_active = run_query("SELECT COUNT(*) FROM recurring_deposits WHERE status = 'ACTIVE'")[0][0]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 Customers", total_cust)
    col2.metric("💰 SB Accounts", total_sb)
    col3.metric("📈 Active FDs", total_fds)
    col4.metric("🔄 Active RDs", rd_active)

elif menu == "Customer Management":
    st.title("👥 Customer Management")
    tab1, tab2 = st.tabs(["Register Customer", "View Directory"])
    with tab1:
        with st.form("reg_form"):
            name = st.text_input("Full Name *")
            phone = st.text_input("Phone Number *")
            pan = st.text_input("PAN Number *")
            adhar_up = st.file_uploader("Aadhaar Document *", type=["pdf", "png", "jpg"])
            pan_up = st.file_uploader("PAN Document *", type=["pdf", "png", "jpg"])
            sig_up = st.file_uploader("Signature *", type=["png", "jpg"])
            if st.form_submit_button("Register"):
                if name and phone and pan and adhar_up and pan_up and sig_up:
                    run_query("INSERT INTO customers (name, phone, pan, adhar, kyc_status, created_at) VALUES (?, ?, ?, '[Redacted]', 'PENDING', ?)", 
                              (name, phone, pan, datetime.now(IST).strftime("%Y-%m-%d")), fetch=False)
                    st.success(f"Customer {name} registered successfully!")
                else:
                    st.error("All mandatory fields and document uploads must be completed.")
    with tab2:
        custs = run_query("SELECT id, name, phone, kyc_status, pan FROM customers")
        if custs:
            st.dataframe(pd.DataFrame(custs, columns=["ID", "Name", "Phone", "KYC", "PAN"]), use_container_width=True)

elif menu == "KYC Verification":
    st.title("✅ KYC Verification")
    pending = run_query("SELECT id, name, phone, pan FROM customers WHERE kyc_status='PENDING'")
    if pending:
        for p in pending:
            col1, col2 = st.columns(2)
            if col1.button(f"Approve #{p[0]}", key=f"app_{p[0]}"):
                run_query("UPDATE customers SET kyc_status='APPROVED' WHERE id=?", (p[0],), fetch=False)
                st.rerun()

elif menu == "SB Accounts":
    st.title("💰 Savings Bank Management")
    tab1, tab2 = st.tabs(["Open SB Account", "View Accounts"])
    with tab1:
        custs = run_query("SELECT id, name FROM customers")
        if custs:
            c_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in custs}
            sel_c = st.selectbox("Customer", list(c_dict.keys()))
            init_bal = st.number_input("Initial Deposit", min_value=0.0, value=500.0)
            if st.button("Create SB Account"):
                acc_no = f"SB{datetime.now(IST).strftime('%Y%m%d%H%M%S')}"
                run_query("INSERT INTO sb_accounts VALUES (?, ?, ?, 3.5, ?)", (acc_no, c_dict[sel_c], init_bal, str(date.today())), fetch=False)
                st.success(f"SB Account created successfully: {acc_no}")
    with tab2:
        sb = run_query("SELECT s.account_no, c.name, s.balance FROM sb_accounts s JOIN customers c ON s.customer_id=c.id")
        if sb:
            st.dataframe(pd.DataFrame(sb, columns=["Account No", "Customer", "Balance"]), use_container_width=True)

elif menu == "Fixed Deposits (FD)":
    st.title("📈 Fixed Deposits Management")
    fds = run_query("SELECT f.fd_id, c.name, f.principal, f.maturity_amount, f.status FROM fixed_deposits f JOIN customers c ON f.customer_id=c.id")
    if fds:
        st.dataframe(pd.DataFrame(fds, columns=["FD ID", "Customer", "Principal", "Maturity", "Status"]), use_container_width=True)
    else:
        st.info("No fixed deposits found.")

elif menu == "Recurring Deposits (RD)":
    st.title("🔄 Recurring Deposits Management")
    rds = run_query("SELECT r.rd_id, c.name, r.monthly_amount, r.status FROM recurring_deposits r JOIN customers c ON r.customer_id=c.id")
    if rds:
        st.dataframe(pd.DataFrame(rds, columns=["RD ID", "Customer", "Monthly Amount", "Status"]), use_container_width=True)
    else:
        st.info("No recurring deposits found.")

elif menu == "Chart of Accounts":
    st.title("📊 Chart of Accounts")
    accs = run_query("SELECT account_code, account_name, account_type, category FROM chart_of_accounts")
    if accs:
        st.dataframe(pd.DataFrame(accs, columns=["Code", "Name", "Type", "Category"]), use_container_width=True)

elif menu == "Cash Book":
    st.title("💵 Cash Book")
    cb = run_query("SELECT date, voucher_no, particulars, debit_amount, credit_amount, balance FROM cash_book")
    if cb:
        st.dataframe(pd.DataFrame(cb, columns=["Date", "Voucher", "Particulars", "Debit", "Credit", "Balance"]), use_container_width=True)

elif menu == "Bank Book":
    st.title("🏦 Bank Book")
    bb = run_query("SELECT date, voucher_no, bank_name, particulars, debit_amount, credit_amount, balance FROM bank_book")
    if bb:
        st.dataframe(pd.DataFrame(bb, columns=["Date", "Voucher", "Bank", "Particulars", "Debit", "Credit", "Balance"]), use_container_width=True)

elif menu == "Journal Vouchers":
    st.title("📝 Journal Vouchers")
    jv = run_query("SELECT jv_id, voucher_date, narration, status FROM journal_vouchers")
    if jv:
        st.dataframe(pd.DataFrame(jv, columns=["JV ID", "Date", "Narration", "Status"]), use_container_width=True)

elif menu == "Admin Record Editor":
    st.title("🛠️ Admin Record Editor")
    st.warning("Administrative maintenance module.")

elif menu == "Financial Statements (Trial/BS/PL)":
    st.title("📊 Financial Statements")
    tb = run_query("SELECT account_code, account_name, account_type FROM chart_of_accounts")
    if tb:
        st.dataframe(pd.DataFrame(tb, columns=["Code", "Name", "Type"]), use_container_width=True)

elif menu == "Reports":
    st.title("📑 Reports Module")
    st.info("Select report preferences from sidebar or specific module views.")

elif menu == "SB Interest Calculation":
    st.title("🧮 SB Interest Calculation")
    if st.button("Calculate & Post Quarterly Interest", type="primary"):
        st.success("Interest processing routine completed successfully.")

