import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import io
import os
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
    """Initialize database and ensure missing columns are added dynamically"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Create all base tables if they don't exist
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

        # Safe migration for missing columns
        try:
            cursor.execute("ALTER TABLE fixed_deposits ADD COLUMN payment_mode TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE fixed_deposits ADD COLUMN closed_date TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE recurring_deposits ADD COLUMN payment_mode TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE recurring_deposits ADD COLUMN closed_date TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE recurring_deposits ADD COLUMN maturity_amount REAL DEFAULT 0")
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

        # Comprehensive default Chart of Accounts list with all Depreciation heads
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

def get_account_balance_from_jv(account_code):
    """Get real balance from journal entries - SINGLE SOURCE OF TRUTH"""
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
    """Get real cash balance from journal entries"""
    return get_account_balance_from_jv('AST-101')

def get_bank_balance(bank_name=None):
    """Get real bank balance from journal entries"""
    if bank_name == "Union Bank of India" or bank_name is None:
        return get_account_balance_from_jv('AST-102')
    elif bank_name == "State Bank of India":
        return get_account_balance_from_jv('AST-103')
    else:
        # Try to find by name
        result = run_query("SELECT account_code FROM chart_of_accounts WHERE account_name = ? AND account_type = 'Asset'", (bank_name,))
        if result:
            return get_account_balance_from_jv(result[0][0])
        return 0.0

def update_cash_book_balance(balance):
    """Update the running balance in cash book - secondary to JV"""
    run_query("UPDATE cash_book SET balance = ? WHERE id = (SELECT MAX(id) FROM cash_book)", (balance,), fetch=False)

def update_bank_book_balance(bank_name, balance):
    """Update the running balance in bank book - secondary to JV"""
    run_query("UPDATE bank_book SET balance = ? WHERE bank_name = ? AND id = (SELECT MAX(id) FROM bank_book WHERE bank_name = ?)", 
              (balance, bank_name, bank_name), fetch=False)

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
    """Post a journal voucher - this is the single source of truth"""
    if amount <= 0:
        return None
    try:
        debit_check = run_query("SELECT account_code FROM chart_of_accounts WHERE account_code = ?", (debit_acc,))
        credit_check = run_query("SELECT account_code FROM chart_of_accounts WHERE account_code = ?", (credit_acc,))
        
        if not debit_check or not credit_check:
            st.error(f"Invalid account codes: {debit_acc} or {credit_acc}")
            return None
        
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

def get_account_name(account_code):
    """Get account name from chart_of_accounts"""
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
    doc = SimpleDocTemplate(buffer, pagesize=A5, rightMargin=12*mm, leftMargin=12*mm, topMargin=12*mm, bottomMargin=12*mm)
    elements = []
    
    available_width = A5[0] - (24*mm)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('VoucherTitle', parent=styles['Heading1'], fontSize=13, textColor=colors.HexColor('#1f4e78'), alignment=1, spaceAfter=6)
    normal_style = ParagraphStyle('VoucherNormal', parent=styles['Normal'], fontSize=9, leading=12)
    bold_style = ParagraphStyle('VoucherBold', parent=styles['Normal'], fontSize=9, leading=12, fontName='Helvetica-Bold')
    
    if voucher_type == 'CB':
        date_val, v_num, part, dr, cr, acc_code, narr = voucher_data[0]
        acc_name = get_account_name(acc_code)
        account_display = f"{acc_code} - {acc_name}" if acc_name else acc_code
        
        elements.append(Paragraph("AASHA NIDHI BANK", title_style))
        elements.append(Paragraph("CASH VOUCHER (CB)", ParagraphStyle('Sub', parent=styles['Heading2'], fontSize=11, alignment=1, spaceAfter=8)))
        elements.append(Spacer(1, 6))
        
        voucher_content = [
            ["Voucher No:", v_num, "Date:", date_val],
            ["Particulars:", part, "", ""],
            ["Account Head:", account_display, "", ""],
            ["Amount:", f"Debit (Receipt): ₹{dr:,.2f}" if dr > 0 else f"Credit (Payment): ₹{cr:,.2f}", "", ""],
            ["Narration:", narr if narr else 'N/A', "", ""],
        ]
        
        table_data = []
        for row in voucher_content:
            para_row = []
            for i, cell in enumerate(row):
                if i == 0:
                    para_row.append(Paragraph(f"<b>{cell}</b>", bold_style))
                else:
                    para_row.append(Paragraph(cell, normal_style))
            table_data.append(para_row)
        
        col_widths = [available_width * 0.25, available_width * 0.35, available_width * 0.15, available_width * 0.25]
        
        t = Table(table_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('SPAN', (1, 1), (-1, 1)),
            ('SPAN', (1, 2), (-1, 2)),
            ('SPAN', (1, 3), (-1, 3)),
            ('SPAN', (1, 4), (-1, 4)),
        ]))
        elements.append(t)
        
    elif voucher_type == 'BB':
        date_val, v_num, bank_n, part, dr, cr, acc_code, narr = voucher_data[0]
        acc_name = get_account_name(acc_code)
        account_display = f"{acc_code} - {acc_name}" if acc_name else acc_code
        
        elements.append(Paragraph("AASHA NIDHI BANK", title_style))
        elements.append(Paragraph("BANK VOUCHER (BB)", ParagraphStyle('Sub', parent=styles['Heading2'], fontSize=11, alignment=1, spaceAfter=8)))
        elements.append(Spacer(1, 6))
        
        voucher_content = [
            ["Voucher No:", v_num, "Date:", date_val],
            ["Bank:", bank_n, "", ""],
            ["Particulars:", part, "", ""],
            ["Account Head:", account_display, "", ""],
            ["Amount:", f"Debit (Deposit): ₹{dr:,.2f}" if dr > 0 else f"Credit (Withdrawal): ₹{cr:,.2f}", "", ""],
            ["Narration:", narr if narr else 'N/A', "", ""],
        ]
        
        table_data = []
        for row in voucher_content:
            para_row = []
            for i, cell in enumerate(row):
                if i == 0:
                    para_row.append(Paragraph(f"<b>{cell}</b>", bold_style))
                else:
                    para_row.append(Paragraph(cell, normal_style))
            table_data.append(para_row)
        
        col_widths = [available_width * 0.22, available_width * 0.38, available_width * 0.15, available_width * 0.25]
        
        t = Table(table_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('SPAN', (1, 1), (-1, 1)),
            ('SPAN', (1, 2), (-1, 2)),
            ('SPAN', (1, 3), (-1, 3)),
            ('SPAN', (1, 4), (-1, 4)),
            ('SPAN', (1, 5), (-1, 5)),
        ]))
        elements.append(t)
        
    elif voucher_type == 'JV':
        elements.append(Paragraph("AASHA NIDHI BANK", title_style))
        elements.append(Paragraph("JOURNAL VOUCHER (JV)", ParagraphStyle('Sub', parent=styles['Heading2'], fontSize=11, alignment=1, spaceAfter=8)))
        elements.append(Spacer(1, 6))
        
        jv_date = voucher_data[0][0]
        narration_text = voucher_data[0][1]
        
        header_data = [
            [Paragraph(f"<b>JV ID:</b> JV-{jv_id if jv_id else 'N/A'}", bold_style),
             Paragraph(f"<b>Date:</b> {jv_date}", normal_style)]
        ]
        header_t = Table(header_data, colWidths=[available_width*0.5, available_width*0.5])
        header_t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(header_t)
        elements.append(Spacer(1, 8))
        
        col1_width = available_width * 0.55
        col2_width = available_width * 0.225
        col3_width = available_width * 0.225
        
        table_data = [[Paragraph("<b>Account Head</b>", bold_style), 
                      Paragraph("<b>Debit (₹)</b>", bold_style), 
                      Paragraph("<b>Credit (₹)</b>", bold_style)]]
        
        total_dr = 0
        total_cr = 0
        for row in voucher_data:
            _, _, acc_code, acc_name, dr, cr = row
            account_display = f"{acc_code} - {acc_name}" if acc_name else acc_code
            table_data.append([
                Paragraph(account_display, normal_style),
                Paragraph(f"{dr:,.2f}" if dr > 0 else "-", normal_style),
                Paragraph(f"{cr:,.2f}" if cr > 0 else "-", normal_style)
            ])
            total_dr += dr
            total_cr += cr
        
        table_data.append([
            Paragraph("<b>Total</b>", bold_style),
            Paragraph(f"<b>{total_dr:,.2f}</b>", bold_style),
            Paragraph(f"<b>{total_cr:,.2f}</b>", bold_style)
        ])
        
        t = Table(table_data, colWidths=[col1_width, col2_width, col3_width])
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4e78')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f0f0')),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"<b>Narration:</b> {narration_text if narration_text else 'N/A'}", normal_style))
    
    elements.append(Spacer(1, 25))
    sign_line = "_" * 60
    elements.append(Paragraph(sign_line, ParagraphStyle('Line', alignment=1, fontSize=8)))
    elements.append(Paragraph("Authorized Signature / Stamp", ParagraphStyle('Sign', alignment=1, fontSize=8)))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

def fetch_cb_voucher(voucher_no):
    return run_query("SELECT date, voucher_no, particulars, debit_amount, credit_amount, account_code, narration FROM cash_book WHERE voucher_no = ?", (voucher_no,))

def fetch_bb_voucher(voucher_no):
    return run_query("SELECT date, voucher_no, bank_name, particulars, debit_amount, credit_amount, account_code, narration FROM bank_book WHERE voucher_no = ?", (voucher_no,))

def fetch_jv_voucher(jv_id):
    query = """
        SELECT 
            jv.voucher_date,
            jv.narration,
            je.account_code,
            co.account_name,
            je.debit,
            je.credit
        FROM journal_vouchers jv
        JOIN jv_entries je ON jv.jv_id = je.jv_id
        JOIN chart_of_accounts co ON je.account_code = co.account_code
        WHERE jv.jv_id = ?
    """
    return run_query(query, (jv_id,))

# --- SIDEBAR NAVIGATION & BACKUP ---
st.sidebar.title("🏦 Aasha Nidhi Bank")
role = st.sidebar.selectbox("User Role", ["Admin/Staff", "Customer Portal"])

if role == "Admin/Staff":
    menu = st.sidebar.selectbox("Navigation", [
        "Dashboard", "Customer Management", "KYC Verification", "SB Accounts",
        "Fixed Deposits (FD)", "Recurring Deposits (RD)", 
        "Chart of Accounts", "Cash Book", "Bank Book", "Journal Vouchers",
        "Admin Record Editor", "Financial Statements (Trial/BS/PL)", "Reports", "SB Interest Calculation"
    ])
else:
    menu = "Customer Portal"

# --- DATABASE BACKUP & RESTORE MODULE ---
st.sidebar.markdown("---")
st.sidebar.subheader("💾 System Backup & Recovery")

if os.path.exists(DB_NAME):
    with open(DB_NAME, "rb") as f:
        db_bytes = f.read()
    st.sidebar.download_button(
        label="Download Database Backup",
        data=db_bytes,
        file_name=f"aasha_nidhi_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
        mime="application/octet-stream",
        help="Download a complete copy of the SQLite database file for safety."
    )

uploaded_db = st.sidebar.file_uploader("Restore Database (.db)", type=["db", "sqlite", "sqlite3"])
if uploaded_db is not None:
    if st.sidebar.button("⚠️ Confirm Database Restore", type="primary"):
        try:
            with open(DB_NAME, "wb") as f:
                f.write(uploaded_db.getbuffer())
            st.sidebar.success("Database restored successfully! Please refresh the page.")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error restoring database: {str(e)}")

# --- DASHBOARD MODULE ---
if menu == "Dashboard":
    st.title("📊 Executive Dashboard & Active Deposits")
    
    total_cust = run_query("SELECT COUNT(*) FROM customers")[0][0]
    total_sb = run_query("SELECT COUNT(*) FROM sb_accounts")[0][0]
    total_fds = run_query("SELECT COUNT(*) FROM fixed_deposits WHERE status='ACTIVE'")[0][0]
    rd_active = run_query("SELECT COUNT(*) FROM recurring_deposits WHERE status = 'ACTIVE'")[0][0]
    cash_bal = get_cash_balance()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Customers", total_cust)
    col2.metric("Active SB Accounts", total_sb)
    col3.metric("Active FDs", total_fds)
    col4.metric("Active RDs", rd_active)
    
    st.markdown("---")
    st.subheader("📋 Active Recurring Deposits (RD) Directory")
    rd_query = """
        SELECT r.rd_id, c.name, r.monthly_amount, r.tenure_months, r.interest_rate, r.installments_paid, r.status, r.created_at
        FROM recurring_deposits r
        JOIN customers c ON r.customer_id = c.id
        WHERE r.status = 'ACTIVE'
    """
    rd_data = run_query(rd_query)
    if rd_data:
        df_rd = pd.DataFrame(rd_data, columns=["RD ID", "Customer Name", "Monthly Amount", "Tenure (Months)", "Interest Rate (%)", "Installments Paid", "Status", "Created Date"])
        st.dataframe(df_rd, use_container_width=True)
    else:
        st.info("No active Recurring Deposit accounts found.")

#CUSTOMER MANAGEMENT

elif menu == "Customer Management":
    st.title("👥 Customer Management Module")
    tab1, tab2, tab3 = st.tabs(["Register Customer", "View / Manage Customers", "Edit Customer"])
    
    with tab1:
        st.subheader("New Customer Registration")
        st.info("ℹ️ All mandatory fields (*), phone number uniqueness, and file uploads (Aadhaar, PAN, Signature) are required.")
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
            pincode = col2.text_input("Pincode")
            pan = col1.text_input("PAN Number")
            
            st.markdown("---")
            adhar_upload = st.file_uploader("Upload Aadhaar Document *", type=["pdf", "png", "jpg", "jpeg"], key="reg_adhar")
            pan_upload = st.file_uploader("Upload PAN Card Document *", type=["pdf", "png", "jpg", "jpeg"], key="reg_pan")
            sig_upload = st.file_uploader("Upload Signature *", type=["png", "jpg", "jpeg"], key="reg_sig")
            
            submitted = st.form_submit_button("Register Customer")
            if submitted:
                if not name or not phone:
                    st.error("Please fill in mandatory fields: Name and Phone.")
                elif not adhar_upload or not pan_upload or not sig_upload:
                    st.error("All document uploads (Aadhaar, PAN Card, and Signature) are mandatory before registering.")
                else:
                    # Check duplication by phone number
                    existing = run_query("SELECT COUNT(*) FROM customers WHERE phone = ?", (phone,))
                    if existing and existing[0][0] > 0:
                        st.error(f"A customer with phone number {phone} already exists. Duplication is not allowed.")
                    else:
                        adhar_path = save_uploaded_file(adhar_upload)
                        pan_path = save_uploaded_file(pan_upload)
                        sig_path = save_uploaded_file(sig_upload)
                        
                        run_query("""
                            INSERT INTO customers (name, dob, gender, email, phone, street, city, state, pincode, pan, adhar, adhar_file, pan_file, signature_file, kyc_status, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
                        """, (name, str(dob), gender, email, phone, street, city, state, pincode, pan, "[Redacted]", adhar_path, pan_path, sig_path, datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                        st.success(f"Customer {name} registered successfully!")

    with tab2:
        st.subheader("Customer Directory & Document Viewer")
        customers = run_query("SELECT id, name, phone, email, kyc_status, pan, created_at FROM customers")
        if customers:
            df_cust = pd.DataFrame(customers, columns=["ID", "Name", "Phone", "Email", "KYC Status", "PAN", "Joined"])
            st.dataframe(df_cust, use_container_width=True)
            
            col_csv, col_pdf = st.columns(2)
            col_csv.download_button("Download CSV Report", df_cust.to_csv(index=False).encode('utf-8'), "customers_report.csv", "text/csv")
            col_pdf.download_button("Download PDF Report", create_pdf_report("Customer Directory Report", df_cust), "customers_report.pdf", "application/pdf")
            
            st.markdown("---")
            st.subheader("🔍 View & Download Original Customer Documents")
            cust_ids = [row[0] for row in customers]
            selected_cust_id = st.selectbox("Select Customer ID to View Documents", cust_ids, key="view_docs_id")
            if selected_cust_id:
                doc_data = run_query("SELECT name, adhar_file, pan_file, signature_file FROM customers WHERE id = ?", (selected_cust_id,))
                if doc_data:
                    c_name, a_file, p_file, s_file = doc_data[0]
                    st.write(f"**Documents for:** {c_name} (ID: {selected_cust_id})")
                    d_col1, d_col2, d_col3 = st.columns(3)
                    
                    import os
                    
                    with d_col1:
                        st.markdown("**Aadhaar Document**")
                        if a_file:
                            st.write(f"Path: `{a_file}`")
                            try:
                                original_filename = os.path.basename(a_file)
                                with open(a_file, "rb") as file_file:
                                    st.download_button("Download Original Aadhaar", file_file, file_name=original_filename, key=f"dl_adh_{selected_cust_id}")
                            except Exception:
                                st.info("File not found on disk.")
                        else:
                            st.info("No file uploaded.")
                            
                    with d_col2:
                        st.markdown("**PAN Card Document**")
                        if p_file:
                            st.write(f"Path: `{p_file}`")
                            try:
                                original_filename = os.path.basename(p_file)
                                with open(p_file, "rb") as file_file:
                                    st.download_button("Download Original PAN", file_file, file_name=original_filename, key=f"dl_pan_{selected_cust_id}")
                            except Exception:
                                st.info("File not found on disk.")
                        else:
                            st.info("No file uploaded.")
                            
                    with d_col3:
                        st.markdown("**Signature**")
                        if s_file:
                            st.write(f"Path: `{s_file}`")
                            try:
                                original_filename = os.path.basename(s_file)
                                with open(s_file, "rb") as file_file:
                                    st.download_button("Download Original Signature", file_file, file_name=original_filename, key=f"dl_sig_{selected_cust_id}")
                            except Exception:
                                st.info("File not found on disk.")
                        else:
                            st.info("No file uploaded.")
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
            
            asset_accounts = run_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset'")
            asset_dict = {f"{a[0]} - {a[1]}": a[0] for a in asset_accounts} if asset_accounts else {}
            
            if asset_dict:
                selected_asset_code = st.selectbox(
                    "Funding Mode (Drill-down: Chart of Accounts)", 
                    list(asset_dict.keys()), 
                    key="sb_open_asset_account"
                )
                chosen_asset_code = asset_dict[selected_asset_code]
                mode = selected_asset_code.split(" - ")[1]
            else:
                chosen_asset_code = "AST-101"
                mode = "CASH"
            
            if st.button("Create SB Account"):
                # For SB opening with initial balance, the customer is depositing money
                # So the asset account (cash/bank) should be DEBITED (increase)
                # No balance check needed for deposit - money comes from customer
                
                acc_no = f"SB{datetime.now().strftime('%Y%m%d%H%M%S')}"
                run_query("INSERT INTO sb_accounts VALUES (?, ?, ?, 3.5, ?)", 
                          (acc_no, cust_id, init_bal, datetime.now().strftime("%Y-%m-%d")), fetch=False)
                
                if init_bal > 0:
                    run_query("INSERT INTO transactions (tx_id, account_no, type, amount, mode, narration, date) VALUES (?, ?, 'CREDIT', ?, ?, 'Opening Balance Deposit', ?)",
                              (f"TX{datetime.now().strftime('%M%S%f')}", acc_no, init_bal, mode, datetime.now().strftime("%Y-%m-%d")), fetch=False)
                    
                    # DEPOSIT: Debit Asset (Cash/Bank increases) -> Credit Liability (SB Deposits Control)
                    jv_result = post_automated_jv(f"SB Opening Balance - Account {acc_no}", chosen_asset_code, "LIA-101", init_bal)
                    
                    # Update cash/bank book
                    if jv_result:
                        today = datetime.now().strftime("%Y-%m-%d")
                        new_asset_balance = get_account_balance_from_jv(chosen_asset_code)
                        
                        if chosen_asset_code == 'AST-101':
                            voucher_no = generate_cash_voucher_no()
                            run_query("""
                                INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (today, voucher_no, f"SB Opening Deposit: {acc_no}", init_bal, 0, new_asset_balance, chosen_asset_code, f"SB Opening Balance - {acc_no}", datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                        elif chosen_asset_code in ['AST-102', 'AST-103']:
                            bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
                            voucher_no = generate_bank_voucher_no()
                            run_query("""
                                INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (today, voucher_no, f"SB Opening Deposit: {acc_no}", init_bal, 0, new_asset_balance, bank_name, chosen_asset_code, f"SB Opening Balance - {acc_no}", datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)

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
            
            asset_accounts = run_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset' AND account_code IN ('AST-101', 'AST-102', 'AST-103')")
            if not asset_accounts:
                asset_accounts = run_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset'")
            
            asset_dict = {f"{a[0]} - {a[1]}": a[0] for a in asset_accounts} if asset_accounts else {}
            
            if asset_dict:
                selected_asset_code = st.selectbox(
                    "Payment Mode (Drill-down: Chart of Accounts)", 
                    list(asset_dict.keys()), 
                    key="sb_tx_asset_account"
                )
                chosen_asset_code = asset_dict[selected_asset_code]
                pay_mode = selected_asset_code.split(" - ")[1]
            else:
                chosen_asset_code = "AST-101"
                pay_mode = "CASH"
                
            narration = st.text_input("Narration / Remarks", value="Counter transaction")
            
            if st.button("Execute Transaction"):
                current_bal = run_query("SELECT balance FROM sb_accounts WHERE account_no=?", (acc_choice,))[0][0]
                
                if tx_type == "DEPOSIT":
                    # DEPOSIT: Customer gives money to bank
                    # Debit Asset (Cash/Bank increases) -> Credit Liability (SB Deposits Control)
                    # NO balance check needed - money is coming FROM customer INTO bank
                    
                    new_bal = current_bal + amount
                    run_query("UPDATE sb_accounts SET balance=? WHERE account_no=?", (new_bal, acc_choice), fetch=False)
                    run_query("INSERT INTO transactions (tx_id, account_no, type, amount, mode, narration, date) VALUES (?, ?, 'CREDIT', ?, ?, ?, ?)",
                              (f"TX{datetime.now().strftime('%M%S%f')}", acc_choice, amount, pay_mode, narration, datetime.now().strftime("%Y-%m-%d")), fetch=False)
                    
                    jv_result = post_automated_jv(f"SB Deposit: {narration} ({acc_choice})", chosen_asset_code, "LIA-101", amount)
                    
                    if jv_result:
                        today = datetime.now().strftime("%Y-%m-%d")
                        new_asset_balance = get_account_balance_from_jv(chosen_asset_code)
                        
                        if chosen_asset_code == 'AST-101':
                            voucher_no = generate_cash_voucher_no()
                            run_query("""
                                INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (today, voucher_no, f"SB Deposit: {acc_choice}", amount, 0, new_asset_balance, chosen_asset_code, narration, datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                        elif chosen_asset_code in ['AST-102', 'AST-103']:
                            bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
                            voucher_no = generate_bank_voucher_no()
                            run_query("""
                                INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (today, voucher_no, f"SB Deposit: {acc_choice}", amount, 0, new_asset_balance, bank_name, chosen_asset_code, narration, datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                    
                    st.success(f"✅ Deposit successful! New Balance: ₹{new_bal:,.2f}")
                    st.rerun()
                    
                elif tx_type == "WITHDRAWAL":
                    # WITHDRAWAL: Bank gives money to customer
                    # Check SB account has sufficient balance
                    if current_bal < amount:
                        st.error(f"❌ Insufficient SB account balance! Available: ₹{current_bal:,.2f}, Required: ₹{amount:,.2f}")
                        st.stop()
                    
                    # Check bank/cash has sufficient funds to give to customer
                    asset_balance = get_account_balance_from_jv(chosen_asset_code)
                    if amount > asset_balance:
                        st.error(f"❌ Insufficient funds in {pay_mode}! Available: ₹{asset_balance:,.2f}, Required: ₹{amount:,.2f}")
                        st.stop()
                    
                    new_bal = current_bal - amount
                    run_query("UPDATE sb_accounts SET balance=? WHERE account_no=?", (new_bal, acc_choice), fetch=False)
                    run_query("INSERT INTO transactions (tx_id, account_no, type, amount, mode, narration, date) VALUES (?, ?, 'DEBIT', ?, ?, ?, ?)",
                              (f"TX{datetime.now().strftime('%M%S%f')}", acc_choice, amount, pay_mode, narration, datetime.now().strftime("%Y-%m-%d")), fetch=False)
                    
                    # WITHDRAWAL: Debit Liability (SB Deposits Control) -> Credit Asset (Cash/Bank decreases)
                    jv_result = post_automated_jv(f"SB Withdrawal: {narration} ({acc_choice})", "LIA-101", chosen_asset_code, amount)
                    
                    if jv_result:
                        today = datetime.now().strftime("%Y-%m-%d")
                        new_asset_balance = get_account_balance_from_jv(chosen_asset_code)
                        
                        if chosen_asset_code == 'AST-101':
                            voucher_no = generate_cash_voucher_no()
                            run_query("""
                                INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (today, voucher_no, f"SB Withdrawal: {acc_choice}", 0, amount, new_asset_balance, chosen_asset_code, narration, datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                        elif chosen_asset_code in ['AST-102', 'AST-103']:
                            bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
                            voucher_no = generate_bank_voucher_no()
                            run_query("""
                                INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (today, voucher_no, f"SB Withdrawal: {acc_choice}", 0, amount, new_asset_balance, bank_name, chosen_asset_code, narration, datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                    
                    st.success(f"✅ Withdrawal successful! New Balance: ₹{new_bal:,.2f}")
                    st.rerun()

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
    tab1, tab2, tab3 = st.tabs(["Open FD", "Active FDs", "Close FD"])
    
    with tab1:
        customers = run_query("SELECT id, name FROM customers")
        if customers:
            cust_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers}
            selected_cust = st.selectbox("Select Customer Name for FD", list(cust_dict.keys()), key="fd_cust")
            principal = st.number_input("Principal Amount (₹)", min_value=1000.0, value=10000.0, step=500.0)
            tenure = st.slider("Tenure (Months)", 1, 60, 12)
            interest_rate = st.number_input("Interest Rate (% p.a.)", value=6.5)
            nominee = st.text_input("Nominee Name")
            
            asset_accounts = run_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset' AND account_code IN ('AST-101', 'AST-102', 'AST-103')")
            if not asset_accounts:
                asset_accounts = run_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset'")
            
            asset_dict = {f"{a[0]} - {a[1]}": a[0] for a in asset_accounts} if asset_accounts else {}
            
            if asset_dict:
                selected_asset_code = st.selectbox(
                    "Mode of Transfer (Drill-down: Chart of Accounts)", 
                    list(asset_dict.keys()), 
                    key="fd_asset_account"
                )
                chosen_asset_code = asset_dict[selected_asset_code]
                payment_mode = selected_asset_code.split(" - ")[1]
            else:
                chosen_asset_code = "AST-101"
                payment_mode = "Cash"
            
            maturity_amount = principal + (principal * interest_rate * (tenure / 12) / 100)
            st.info(f"Estimated Maturity Amount: **₹{maturity_amount:,.2f}**")
            
            if st.button("Open FD Account"):
                # Validate available balance
                available_balance = get_account_balance_from_jv(chosen_asset_code)
                if principal > available_balance:
                    st.error(f"❌ Insufficient balance in {payment_mode}! Available: ₹{available_balance:,.2f}, Required: ₹{principal:,.2f}")
                    st.stop()
                
                run_query("""
                    INSERT INTO fixed_deposits (customer_id, principal, tenure_months, interest_rate, maturity_amount, nominee, status, created_at, payment_mode)
                    VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                """, (cust_dict[selected_cust], principal, tenure, interest_rate, maturity_amount, nominee, datetime.now().strftime("%Y-%m-%d"), payment_mode), fetch=False)
                
                # FD goes to FD Deposits Control (LIA-102)
                jv_result = post_automated_jv(f"Fixed Deposit Opening - Principal ₹{principal} via {payment_mode}", chosen_asset_code, "LIA-102", principal)
                
                # Update cash/bank book
                if jv_result:
                    today = datetime.now().strftime("%Y-%m-%d")
                    new_balance = get_account_balance_from_jv(chosen_asset_code)
                    
                    if chosen_asset_code == 'AST-101':
                        voucher_no = generate_cash_voucher_no()
                        run_query("""
                            INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (today, voucher_no, f"FD Opening - Customer {cust_dict[selected_cust]}", 0, principal, new_balance, chosen_asset_code, f"FD Opening via {payment_mode}", datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                    elif chosen_asset_code in ['AST-102', 'AST-103']:
                        bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
                        voucher_no = generate_bank_voucher_no()
                        run_query("""
                            INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (today, voucher_no, f"FD Opening - Customer {cust_dict[selected_cust]}", 0, principal, new_balance, bank_name, chosen_asset_code, f"FD Opening via {payment_mode}", datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                
                st.success(f"Fixed Deposit opened & recorded successfully via {payment_mode}!")
        else:
            st.warning("Register a customer first.")

    with tab2:
        fds = run_query("""
            SELECT f.fd_id, c.name, f.principal, f.tenure_months, f.interest_rate, f.maturity_amount, f.status, f.payment_mode
            FROM fixed_deposits f JOIN customers c ON f.customer_id = c.id
            WHERE f.status = 'ACTIVE'
        """)
        if fds:
            df_fds = pd.DataFrame(fds, columns=["FD ID", "Customer", "Principal (₹)", "Tenure (M)", "Rate (%)", "Maturity (₹)", "Status", "Payment Mode"])
            st.dataframe(df_fds, use_container_width=True)
        else:
            st.info("No active fixed deposits found.")

    with tab3:
        
        st.subheader("Close Fixed Deposit")
        active_fds = run_query("""
            SELECT f.fd_id, c.name, f.principal, f.maturity_amount, f.interest_rate, f.tenure_months
            FROM fixed_deposits f JOIN customers c ON f.customer_id = c.id
            WHERE f.status = 'ACTIVE'
        """)
        
        if active_fds:
            fd_dict = {f"FD ID: {r[0]} - {r[1]} (Principal: ₹{r[2]:,.2f}, Maturity: ₹{r[3]:,.2f})": r for r in active_fds}
            selected_fd_str = st.selectbox("Select FD to Close", list(fd_dict.keys()))
            selected_fd = fd_dict[selected_fd_str]
            fd_id, cust_name, principal, maturity_amount, interest_rate, tenure = selected_fd
            
            interest_earned = maturity_amount - principal
            st.info(f"Interest Earned: ₹{interest_earned:,.2f}")
            st.info(f"Total Maturity Amount (Principal + Interest): ₹{maturity_amount:,.2f}")
            
            if st.button("Close FD", type="primary"):
                # Update FD status
                run_query("""
                    UPDATE fixed_deposits 
                    SET status = 'CLOSED', closed_date = ?
                    WHERE fd_id = ?
                """, (datetime.now().strftime("%Y-%m-%d"), fd_id), fetch=False)
                
                # Step 1: Record Interest Expense -> This accumulates in FD Deposits Control (LIA-102)
                # Debit: EXP-102 (FD Interest Paid) | Credit: LIA-102 (FD Deposits Control)
                if interest_earned > 0:
                    post_automated_jv(f"FD #{fd_id} Interest Accrued", "EXP-102", "LIA-102", interest_earned)
                
                # Step 2: Now FD Deposits Control (LIA-102) has Principal + Interest = Maturity Amount
                # Transfer full maturity from FD Deposits Control to SB Deposits Control
                # Debit: LIA-102 (FD Deposits Control) | Credit: LIA-101 (SB Deposits Control)
                post_automated_jv(f"FD #{fd_id} Maturity - Transfer to SB", "LIA-102", "LIA-101", maturity_amount)
                
                st.success(f"FD #{fd_id} closed successfully!")
                st.info(f"₹{maturity_amount:,.2f} transferred from FD Deposits Control to SB Deposits Control")
                st.rerun()
        else:
            st.info("No active FDs available to close.")

# --- RECURRING DEPOSITS ---
elif menu == "Recurring Deposits (RD)":
    st.title("🔄 Recurring Deposits Management")
    tab1, tab2, tab3, tab4 = st.tabs(["Open RD", "Pay Installment", "Active RDs", "Close RD"])
    
    with tab1:
        customers = run_query("SELECT id, name FROM customers")
        if customers:
            cust_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers}
            selected_cust = st.selectbox("Select Customer Name for RD", list(cust_dict.keys()), key="rd_cust")
            monthly_amt = st.number_input("Monthly Installment Amount (₹)", min_value=100.0, value=1000.0)
            tenure = st.slider("Tenure (Months)", 6, 60, 12, key="rd_tenure")
            interest_rate = st.number_input("Interest Rate (% p.a.)", value=6.0, key="rd_rate")
            nominee = st.text_input("Nominee Name", key="rd_nom")
            
            asset_accounts = run_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset' AND account_code IN ('AST-101', 'AST-102', 'AST-103')")
            if not asset_accounts:
                asset_accounts = run_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset'")
            
            asset_dict = {f"{a[0]} - {a[1]}": a[0] for a in asset_accounts} if asset_accounts else {}
            
            if asset_dict:
                selected_asset_code = st.selectbox(
                    "Mode of Transfer (Drill-down: Chart of Accounts)", 
                    list(asset_dict.keys()), 
                    key="rd_open_asset_account"
                )
                chosen_asset_code = asset_dict[selected_asset_code]
                payment_mode = selected_asset_code.split(" - ")[1]
            else:
                chosen_asset_code = "AST-101"
                payment_mode = "Cash"
            
            # Calculate approximate maturity
            total_deposits = monthly_amt * tenure
            approx_interest = total_deposits * (interest_rate / 100) * (tenure / 24)
            approx_maturity = total_deposits + approx_interest
            
            st.info(f"**Estimated Maturity:** Total Deposits ₹{total_deposits:,.2f} + Interest ₹{approx_interest:,.2f} = ₹{approx_maturity:,.2f}")
            
            if st.button("Open RD Account"):
                # Validate balance for first installment
                available_balance = get_account_balance_from_jv(chosen_asset_code)
                if monthly_amt > available_balance:
                    st.error(f"❌ Insufficient balance in {payment_mode}! Available: ₹{available_balance:,.2f}, Required: ₹{monthly_amt:,.2f}")
                    st.stop()
                
                run_query("""
                    INSERT INTO recurring_deposits (customer_id, monthly_amount, tenure_months, interest_rate, installments_paid, nominee, status, created_at, payment_mode, maturity_amount)
                    VALUES (?, ?, ?, ?, 0, ?, 'ACTIVE', ?, ?, ?)
                """, (cust_dict[selected_cust], monthly_amt, tenure, interest_rate, nominee, 
                      datetime.now().strftime("%Y-%m-%d"), payment_mode, approx_maturity), fetch=False)
                
                # Post first installment
                jv_result = post_automated_jv(f"RD Opening - First Installment via {payment_mode}", chosen_asset_code, "LIA-103", monthly_amt)
                
                # Update installment count and books
                rd_id_result = run_query("SELECT last_insert_rowid()")
                if rd_id_result and jv_result:
                    rd_id = rd_id_result[0][0]
                    run_query("UPDATE recurring_deposits SET installments_paid=1 WHERE rd_id=?", (rd_id,), fetch=False)
                    
                    today = datetime.now().strftime("%Y-%m-%d")
                    new_balance = get_account_balance_from_jv(chosen_asset_code)
                    
                    if chosen_asset_code == 'AST-101':
                        voucher_no = generate_cash_voucher_no()
                        run_query("""
                            INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (today, voucher_no, f"RD Opening - Inst 1 - Customer {cust_dict[selected_cust]}", 0, monthly_amt, new_balance, chosen_asset_code, f"RD Opening via {payment_mode}", datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                    elif chosen_asset_code in ['AST-102', 'AST-103']:
                        bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
                        voucher_no = generate_bank_voucher_no()
                        run_query("""
                            INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (today, voucher_no, f"RD Opening - Inst 1 - Customer {cust_dict[selected_cust]}", 0, monthly_amt, new_balance, bank_name, chosen_asset_code, f"RD Opening via {payment_mode}", datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                
                st.success(f"Recurring Deposit opened successfully via {payment_mode}! First installment paid.")
        else:
            st.warning("Register customers first.")

    with tab2:
        active_rds = run_query("""
            SELECT r.rd_id, c.name, r.monthly_amount, r.tenure_months, r.installments_paid, r.maturity_amount
            FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id 
            WHERE r.status='ACTIVE'
        """)
        if active_rds:
            rd_dict = {f"RD ID: {r[0]} - {r[1]} (Monthly: ₹{r[2]:,.2f}, Paid: {r[4]}/{r[3]})": r for r in active_rds}
            chosen_rd_str = st.selectbox("Select Active RD Account", list(rd_dict.keys()))
            selected_rd = rd_dict[chosen_rd_str]
            rd_id, cust_name, monthly_amt, tenure_m, paid_inst, maturity_amt = selected_rd
            
            asset_accounts = run_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset' AND account_code IN ('AST-101', 'AST-102', 'AST-103')")
            if not asset_accounts:
                asset_accounts = run_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset'")
            
            asset_dict = {f"{a[0]} - {a[1]}": a[0] for a in asset_accounts} if asset_accounts else {}
            
            if asset_dict:
                selected_asset_code = st.selectbox(
                    "Mode of Transfer (Drill-down: Chart of Accounts)", 
                    list(asset_dict.keys()), 
                    key="rd_pay_asset_account"
                )
                chosen_asset_code = asset_dict[selected_asset_code]
                payment_mode_pay = selected_asset_code.split(" - ")[1]
            else:
                chosen_asset_code = "AST-101"
                payment_mode_pay = "Cash"
            
            if st.button("Confirm & Pay Installment"):
                # Validate balance
                available_balance = get_account_balance_from_jv(chosen_asset_code)
                if monthly_amt > available_balance:
                    st.error(f"❌ Insufficient balance in {payment_mode_pay}! Available: ₹{available_balance:,.2f}, Required: ₹{monthly_amt:,.2f}")
                    st.stop()
                
                if paid_inst < tenure_m:
                    new_paid = paid_inst + 1
                    run_query("UPDATE recurring_deposits SET installments_paid=? WHERE rd_id=?", (new_paid, rd_id), fetch=False)
                    
                    jv_result = post_automated_jv(f"RD Installment Paid - RD #{rd_id} (Inst #{new_paid}) via {payment_mode_pay}", chosen_asset_code, "LIA-103", monthly_amt)
                    
                    if jv_result:
                        today = datetime.now().strftime("%Y-%m-%d")
                        new_balance = get_account_balance_from_jv(chosen_asset_code)
                        
                        if chosen_asset_code == 'AST-101':
                            voucher_no = generate_cash_voucher_no()
                            run_query("""
                                INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (today, voucher_no, f"RD #{rd_id} - Inst #{new_paid}", 0, monthly_amt, new_balance, chosen_asset_code, f"RD Installment #{new_paid}", datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                        elif chosen_asset_code in ['AST-102', 'AST-103']:
                            bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
                            voucher_no = generate_bank_voucher_no()
                            run_query("""
                                INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (today, voucher_no, f"RD #{rd_id} - Inst #{new_paid}", 0, monthly_amt, new_balance, bank_name, chosen_asset_code, f"RD Installment #{new_paid}", datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                    
                    st.success(f"Installment #{new_paid} successfully paid via {payment_mode_pay}!")
                    st.rerun()
        else:
            st.info("No active recurring deposits found.")

    with tab3:
        rds = run_query("""
            SELECT r.rd_id, c.name, r.monthly_amount, r.tenure_months, r.interest_rate, r.installments_paid, r.status, r.payment_mode, r.maturity_amount
            FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id
            WHERE r.status = 'ACTIVE'
        """)
        if rds:
            df_rds = pd.DataFrame(rds, columns=["RD ID", "Customer", "Monthly (₹)", "Tenure (M)", "Rate (%)", "Paid Installments", "Status", "Payment Mode", "Est. Maturity"])
            st.dataframe(df_rds, use_container_width=True)

    with tab4:
        st.subheader("Close Recurring Deposit")
        active_rds_close = run_query("""
            SELECT r.rd_id, c.name, r.monthly_amount, r.tenure_months, r.installments_paid, r.maturity_amount, r.interest_rate
            FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id
            WHERE r.status = 'ACTIVE'
        """)
        
        if active_rds_close:
            rd_close_dict = {f"RD ID: {r[0]} - {r[1]} (Paid: {r[4]}/{r[3]}, Est. Maturity: ₹{r[5]:,.2f})": r for r in active_rds_close}
            selected_rd_str = st.selectbox("Select RD to Close", list(rd_close_dict.keys()))
            selected_rd = rd_close_dict[selected_rd_str]
            rd_id, cust_name, monthly_amt, tenure_m, paid_inst, maturity_amt, interest_rate = selected_rd
            
            if paid_inst < tenure_m:
                st.warning(f"⚠️ Only {paid_inst} out of {tenure_m} installments paid. Early closure will reduce maturity amount.")
                total_paid = monthly_amt * paid_inst
                prorated_interest = total_paid * (interest_rate / 100) * (paid_inst / 24)
                prorated_maturity = total_paid + prorated_interest
                st.info(f"**Prorated Maturity Amount:** ₹{prorated_maturity:,.2f}")
                maturity_amount_to_pay = prorated_maturity
            else:
                maturity_amount_to_pay = maturity_amt
                st.success(f"✅ All installments paid. Full maturity amount: ₹{maturity_amt:,.2f}")
            
            total_paid = monthly_amt * paid_inst
            interest_earned = maturity_amount_to_pay - total_paid
            st.info(f"Interest Earned: ₹{interest_earned:,.2f}")
            
            if st.button("Close RD", type="primary"):
                run_query("""
                    UPDATE recurring_deposits 
                    SET status = 'CLOSED', closed_date = ?
                    WHERE rd_id = ?
                """, (datetime.now().strftime("%Y-%m-%d"), rd_id), fetch=False)
                
                post_automated_jv(f"RD #{rd_id} Maturity - Transfer to SB Deposits Control", "LIA-103", "LIA-101", maturity_amount_to_pay)
                
                if interest_earned > 0:
                    post_automated_jv(f"RD #{rd_id} Interest Expense", "EXP-103", "LIA-103", interest_earned)
                
                st.success(f"RD #{rd_id} closed successfully! Amount transferred to SB Deposits Control")
                st.rerun()
        else:
            st.info("No active RDs available to close.")

# --- CHART OF ACCOUNTS ---
elif menu == "Chart of Accounts":
    st.title("🗂️ Chart of Accounts Management")
    st.write("View, add, edit, or delete accounting heads directly below.")

    tab_coa1, tab_coa2 = st.tabs(["📋 View & Delete Accounts", "➕ Add / Edit Account Head"])

    with tab_coa1:
        st.subheader("Existing Accounts Directory")
        accounts = run_query("SELECT account_code, account_name, account_type, category FROM chart_of_accounts")
        if accounts:
            df_coa = pd.DataFrame(accounts, columns=["Account Code", "Account Name", "Account Type", "Category"])
            st.dataframe(df_coa, use_container_width=True)

            st.divider()
            st.subheader("🗑️ Delete Account Head")
            del_code = st.selectbox("Select Account Code to Delete", df_coa["Account Code"].tolist())
            if st.button("Delete Account Head", type="primary"):
                try:
                    run_query("DELETE FROM chart_of_accounts WHERE account_code = ?", (del_code,), fetch=False)
                    st.success(f"Successfully deleted account code: {del_code}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not delete account. It may be linked to active entries. Error: {e}")
        else:
            st.info("No records found in the Chart of Accounts.")

    with tab_coa2:
        st.subheader("Create or Update Account Head")
        with st.form("coa_upsert_form"):
            col1, col2 = st.columns(2)
            with col1:
                input_code = st.text_input("Account Code (e.g., INC-302, EXP-402)").upper().strip()
                input_type = st.selectbox("Account Type", ["Income", "Expense", "Asset", "Liability", "Equity"])
            with col2:
                input_name = st.text_input("Account Name (e.g., Special Service Income)")
                input_category = st.text_input("Category (e.g., Operating Expenses, Current Assets)")
            
            submitted = st.form_submit_button("Save / Update Account Head")
            if submitted:
                if not input_code or not input_name or not input_category:
                    st.warning("Please fill out all fields.")
                else:
                    try:
                        run_query(
                            "INSERT OR REPLACE INTO chart_of_accounts (account_code, account_name, account_type, category) VALUES (?, ?, ?, ?)",
                            (input_code, input_name, input_type, input_category),
                            fetch=False
                        )
                        st.success(f"Account head '{input_code} - {input_name}' saved successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving account entry: {e}")

# --- CASH BOOK ---
elif menu == "Cash Book":
    st.title("💰 Cash Book Entries")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Record Entry", "View / Delete", "Edit Entry", "Print Book", "🖨️ Print CB Vouchers"])
    
    with tab1:
        current_balance = get_cash_balance()
        st.info(f"💰 **Current Cash Balance (from JV):** ₹{current_balance:,.2f}")
        
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
                    account_code = coa_dict[account_head]
                    
                    if entry_type == "DEBIT (Receipt)":
                        # Cash IN - debit cash, credit other account
                        jv_result = post_automated_jv(f"Cash Receipt: {particulars}", "AST-101", account_code, amount)
                    else:
                        # Cash OUT - check balance
                        if current_balance < amount:
                            st.error(f"❌ Insufficient Cash Balance! Available: ₹{current_balance:,.2f}")
                            st.stop()
                        jv_result = post_automated_jv(f"Cash Payment: {particulars}", account_code, "AST-101", amount)
                    
                    if jv_result:
                        voucher_no = generate_cash_voucher_no()
                        today = datetime.now().strftime("%Y-%m-%d")
                        new_balance = get_cash_balance()
                        
                        dr_amt = amount if entry_type == "DEBIT (Receipt)" else 0
                        cr_amt = amount if entry_type == "CREDIT (Payment)" else 0
                        
                        run_query("""
                            INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (today, voucher_no, particulars, dr_amt, cr_amt, new_balance, account_code, narration, datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                        
                        # Handle bank transfers
                        if account_code == 'AST-102':
                            bank_voucher_no = generate_bank_voucher_no()
                            union_bal = get_bank_balance("Union Bank of India")
                            bank_dr = amount if entry_type == "CREDIT (Payment)" else 0
                            bank_cr = amount if entry_type == "DEBIT (Receipt)" else 0
                            run_query("""
                                INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (today, bank_voucher_no, f"Cash Transfer: {particulars}", bank_dr, bank_cr, union_bal, "Union Bank of India", "AST-101", narration, datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                        elif account_code == 'AST-103':
                            bank_voucher_no = generate_bank_voucher_no()
                            sbi_bal = get_bank_balance("State Bank of India")
                            bank_dr = amount if entry_type == "CREDIT (Payment)" else 0
                            bank_cr = amount if entry_type == "DEBIT (Receipt)" else 0
                            run_query("""
                                INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (today, bank_voucher_no, f"Cash Transfer: {particulars}", bank_dr, bank_cr, sbi_bal, "State Bank of India", "AST-101", narration, datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                        
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

    with tab5:
        st.subheader("🖨️ Cash Book Voucher (CB) Drill-Down Print")
        cb_records = run_query("SELECT voucher_no, particulars, date FROM cash_book ORDER BY id DESC")
        if cb_records:
            cb_dict = {f"{r[0]} - {r[1]} ({r[2]})": r[0] for r in cb_records}
            selected_cb = st.selectbox("Select Cash Voucher to Print", list(cb_dict.keys()), key="cb_drilldown")
            if selected_cb:
                v_no = cb_dict[selected_cb]
                v_data = fetch_cb_voucher(v_no)
                if v_data:
                    date_val, v_num, part, dr, cr, acc_code, narr = v_data[0]
                    acc_name = get_account_name(acc_code)
                    account_display = f"{acc_code} - {acc_name}" if acc_name else acc_code
                    
                    with st.container(border=True):
                        col1, col2 = st.columns(2)
                        col1.markdown("### **CASH VOUCHER (CB)**")
                        col1.write(f"**Voucher No:** {v_num}")
                        col2.write(f"**Date:** {date_val}")
                        st.divider()
                        st.write(f"**Particulars:** {part}")
                        st.write(f"**Account Head:** {account_display}")
                        if dr > 0:
                            st.write(f"**Debit Amount (Receipt):** ₹{dr:,.2f}")
                        else:
                            st.write(f"**Credit Amount (Payment):** ₹{cr:,.2f}")
                        st.write(f"**Narration:** {narr if narr else 'N/A'}")
                        st.markdown("---")
                        st.caption("Authorized Signature / Cashier Stamp")
                    
                    pdf_data = generate_voucher_pdf('CB', v_data)
                    st.download_button(
                        label=f"📥 Download Cash Voucher {v_num} (PDF)",
                        data=pdf_data,
                        file_name=f"Cash_Voucher_{v_num}.pdf",
                        mime="application/pdf",
                        key=f"download_cb_{v_num}"
                    )
        else:
            st.info("No Cash Book vouchers available.")

# --- BANK BOOK ---
elif menu == "Bank Book":
    st.title("🏦 Bank Book Entries")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Record Entry", "View / Delete", "Edit Entry", "Print Book", "🖨️ Print BB Vouchers"])
    
    with tab1:
        bank_accounts = run_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset' AND account_name LIKE '%Bank%'")
        if not bank_accounts:
            bank_accounts = [("AST-102", "Union Bank of India"), ("AST-103", "State Bank of India")]
        
        bank_dict = {f"{b[0]} - {b[1]}": (b[0], b[1]) for b in bank_accounts}
        selected_bank_str = st.selectbox("Select Bank", list(bank_dict.keys()), key="bank_select")
        bank_code, bank_name = bank_dict[selected_bank_str]
        
        current_balance = get_account_balance_from_jv(bank_code)
        st.info(f"🏦 **{bank_name} Current Balance (from JV):** ₹{current_balance:,.2f}")
        
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
                    account_code = coa_dict[account_head]
                    
                    if entry_type == "DEBIT (Deposit)":
                        # Bank IN - debit bank, credit other account
                        jv_result = post_automated_jv(f"Bank Deposit: {particulars} - {bank_name}", bank_code, account_code, amount)
                    else:
                        # Bank OUT - check balance
                        if current_balance < amount:
                            st.error(f"❌ Insufficient Bank Balance in {bank_name}! Available: ₹{current_balance:,.2f}")
                            st.stop()
                        jv_result = post_automated_jv(f"Bank Withdrawal: {particulars} - {bank_name}", account_code, bank_code, amount)
                    
                    if jv_result:
                        voucher_no = generate_bank_voucher_no()
                        today = datetime.now().strftime("%Y-%m-%d")
                        new_balance = get_account_balance_from_jv(bank_code)
                        
                        dr_amt = amount if entry_type == "DEBIT (Deposit)" else 0
                        cr_amt = amount if entry_type == "CREDIT (Withdrawal)" else 0
                        
                        run_query("""
                            INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (today, voucher_no, particulars, dr_amt, cr_amt, new_balance, bank_name, account_code, narration, datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                        
                        # If transferring to cash, also update cash book
                        if account_code == 'AST-101':
                            cash_voucher_no = generate_cash_voucher_no()
                            cash_bal = get_cash_balance()
                            cash_dr = amount if entry_type == "CREDIT (Withdrawal)" else 0
                            cash_cr = amount if entry_type == "DEBIT (Deposit)" else 0
                            run_query("""
                                INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (today, cash_voucher_no, f"Bank Transfer: {particulars}", cash_dr, cash_cr, cash_bal, bank_code, narration, datetime.now().strftime("%Y-%m-%d %H:%M")), fetch=False)
                        
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

    with tab5:
        st.subheader("🖨️ Bank Book Voucher (BB) Drill-Down Print")
        bb_records = run_query("SELECT voucher_no, bank_name, particulars, date FROM bank_book ORDER BY id DESC")
        if bb_records:
            bb_dict = {f"{r[0]} - {r[1]} - {r[2]} ({r[3]})": r[0] for r in bb_records}
            selected_bb = st.selectbox("Select Bank Voucher to Print", list(bb_dict.keys()), key="bb_drilldown")
            if selected_bb:
                v_no = bb_dict[selected_bb]
                v_data = fetch_bb_voucher(v_no)
                if v_data:
                    date_val, v_num, bank_n, part, dr, cr, acc_code, narr = v_data[0]
                    acc_name = get_account_name(acc_code)
                    account_display = f"{acc_code} - {acc_name}" if acc_name else acc_code
                    
                    with st.container(border=True):
                        col1, col2 = st.columns(2)
                        col1.markdown("### **BANK VOUCHER (BB)**")
                        col1.write(f"**Voucher No:** {v_num}")
                        col1.write(f"**Bank Name:** {bank_n}")
                        col2.write(f"**Date:** {date_val}")
                        st.divider()
                        st.write(f"**Particulars:** {part}")
                        st.write(f"**Account Head:** {account_display}")
                        if dr > 0:
                            st.write(f"**Debit Amount (Deposit):** ₹{dr:,.2f}")
                        else:
                            st.write(f"**Credit Amount (Withdrawal):** ₹{cr:,.2f}")
                        st.write(f"**Narration:** {narr if narr else 'N/A'}")
                        st.markdown("---")
                        st.caption("Authorized Signature / Accountant Stamp")
                    
                    pdf_data = generate_voucher_pdf('BB', v_data)
                    st.download_button(
                        label=f"📥 Download Bank Voucher {v_num} (PDF)",
                        data=pdf_data,
                        file_name=f"Bank_Voucher_{v_num}.pdf",
                        mime="application/pdf",
                        key=f"download_bb_{v_num}"
                    )
        else:
            st.info("No Bank Book vouchers available.")

# --- JOURNAL VOUCHERS ---
# --- JOURNAL VOUCHERS ---
# --- JOURNAL Vouchers ---
elif menu == "Journal Vouchers":
    st.title("📝 Journal Vouchers Management")
    tab1, tab2, tab3 = st.tabs(["Create Journal Voucher", "View Vouchers", "🖨️ Print JV Vouchers"])
    
    with tab1:
        st.subheader("Create Journal Voucher")
        st.info("💡 **Depreciation Posting:** Selecting an expense head like EXP-204 to EXP-207 allows you to enter the asset base value. The system computes the depreciation, debits the P&L expense, and credits the selected credit account.")
        
        # Fetch ALL Chart of Accounts so everything appears on both sides
        coa_list = run_query("SELECT account_code, account_name, account_type FROM chart_of_accounts")
        coa_dict = {f"{c[0]} - {c[1]}": c[0] for c in coa_list}
        coa_names = {c[0]: c[1] for c in coa_list}
        
        # Explicit mapping for your specific depreciation heads
        dep_rate_map = {
            "EXP-204": 5.0,
            "EXP-205": 10.0,
            "EXP-206": 15.0,
            "EXP-207": 40.0
        }

        with st.form("unified_jv_form"):
            v_date = st.date_input("Voucher Date", value=date.today())
            narration = st.text_input("Narration / Description", value="Depreciation entry")
            
            st.markdown("---")
            st.markdown("#### **Debit Entry (Expense Head)**")
            col_acc1, col_dummy = st.columns([2, 1])
            acc1 = col_acc1.selectbox("Debit Account Head", list(coa_dict.keys()), key="jv_acc1")
            acc1_code = coa_dict[acc1]
            acc1_name = coa_names.get(acc1_code, "")
            acc1_name_lower = acc1_name.lower()
            
            is_depreciation = acc1_code in dep_rate_map or "depreciation" in acc1_name_lower
            
            if is_depreciation:
                # Determine rate from map or fallback to regex extraction
                if acc1_code in dep_rate_map:
                    default_rate = dep_rate_map[acc1_code]
                else:
                    rate_match = re.search(r'(\d+(?:\.\d+)?)%', acc1_name)
                    default_rate = float(rate_match.group(1)) if rate_match else 15.0
                
                st.markdown("##### ⚙️ Asset Depreciation Calculator")
                col_p1, col_p2 = st.columns(2)
                dep_percentage = col_p1.number_input("Depreciation Percentage (%)", min_value=0.0, max_value=100.0, value=default_rate, step=0.5, key="jv_dep_rate")
                base_amount = col_p2.number_input("Enter Asset Base Value (₹)", min_value=0.0, value=0.0, step=100.0, key="jv_base_amt")
                
                calculated_dep = round(base_amount * (dep_percentage / 100.0), 2)
                st.write(f"**Calculated Expense ({dep_percentage}% of ₹{base_amount:,.2f}):** **₹{calculated_dep:,.2f}**")
                dr1 = calculated_dep
            else:
                dr1 = st.number_input("Debit Amount (₹)", min_value=0.0, value=0.0, step=100.0, key="jv_dr1")
            
            st.markdown("---")
            st.markdown("#### **Credit Entry**")
            col_acc2, col_dummy2 = st.columns([2, 1])
            # Using coa_dict here ensures ALL account heads appear on the credit side as well
            acc2 = col_acc2.selectbox("Credit Account Head", list(coa_dict.keys()), key="jv_acc2")
            acc2_code = coa_dict[acc2]
            
            if is_depreciation:
                st.write(f"**Credit Amount (Auto-balanced):** ₹{calculated_dep:,.2f}")
                cr2 = calculated_dep
            else:
                cr2 = st.number_input("Credit Amount (₹)", min_value=0.0, value=0.0, step=100.0, key="jv_cr2")
            
            submitted = st.form_submit_button("Post Journal Voucher")
            if submitted:
                if dr1 == cr2 and dr1 > 0:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", (str(v_date), narration))
                    jv_id = cursor.lastrowid
                    # Debit entry increases P&L expense
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, acc1_code, dr1))
                    # Credit entry records the credit side
                    cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, acc2_code, cr2))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Journal Voucher JV-{jv_id} posted successfully! Amount recorded: ₹{dr1:,.2f}.")
                else:
                    st.error("Journal Voucher unbalanced! Total Debits must equal Total Credits and be greater than zero.")

    with tab2:
        jvs = run_query("SELECT jv_id, voucher_date, narration, status FROM journal_vouchers")
        if jvs:
            df_jvs = pd.DataFrame(jvs, columns=["JV ID", "Date", "Narration", "Status"])
            st.dataframe(df_jvs, use_container_width=True)
        else:
            st.info("No journal vouchers found.")

    with tab3:
        st.subheader("🖨️ Journal Voucher (JV) Drill-Down Print")
        jv_records = run_query("SELECT jv_id, voucher_date, narration FROM journal_vouchers ORDER BY jv_id DESC")
        if jv_records:
            jv_dict = {f"JV-{r[0]} - {r[2]} ({r[1]})": r[0] for r in jv_records}
            selected_jv = st.selectbox("Select Journal Voucher to Print", list(jv_dict.keys()), key="jv_drilldown")
            if selected_jv:
                jv_id = jv_dict[selected_jv]
                v_data = fetch_jv_voucher(jv_id)
                if v_data:
                    with st.container(border=True):
                        col1, col2 = st.columns(2)
                        col1.markdown("### **JOURNAL VOUCHER (JV)**")
                        col1.write(f"**Voucher ID:** JV-{jv_id}")
                        col2.write(f"**Date:** {v_data[0][0]}")
                        st.divider()
                        
                        rows_list = []
                        total_dr = 0.0
                        total_cr = 0.0
                        for row in v_data:
                            _, _, acc_code, acc_name, dr, cr = row
                            account_display = f"{acc_code} - {acc_name}"
                            rows_list.append([account_display, f"₹{dr:,.2f}" if dr > 0 else "-", f"₹{cr:,.2f}" if cr > 0 else "-"])
                            total_dr += dr
                            total_cr += cr
                        
                        df_jv_print = pd.DataFrame(rows_list, columns=["Account Head", "Debit (₹)", "Credit (₹)"])
                        st.dataframe(df_jv_print, use_container_width=True, hide_index=True)
                        st.write(f"**Narration:** {v_data[0][1] if v_data[0][1] else 'N/A'}")
                        st.divider()
                        col_f1, col_f2 = st.columns(2)
                        col_f1.write(f"**Total Debit:** ₹{total_dr:,.2f}")
                        col_f2.write(f"**Total Credit:** ₹{total_cr:,.2f}")
                        st.markdown("---")
                        st.caption("Authorized Signature / Auditor Stamp")
                    
                    pdf_data = generate_voucher_pdf('JV', v_data, jv_id)
                    st.download_button(
                        label=f"📥 Download Journal Voucher JV-{jv_id} (PDF)",
                        data=pdf_data,
                        file_name=f"Journal_Voucher_JV-{jv_id}.pdf",
                        mime="application/pdf",
                        key=f"download_jv_{jv_id}"
                    )
        else:
            st.info("No Journal Vouchers available.")

# --- ADMIN RECORD EDITOR ---
elif menu == "Admin Record Editor":
    st.title("🛠️ Universal Database Record Editor")
    tables_res = run_query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    table_list = [t[0] for t in tables_res]
    selected_table = st.selectbox("Select Database Table to Manage", table_list)
    
    if selected_table:
        pk_info = run_query(f"PRAGMA table_info({selected_table})")
        pk_col = None
        for col in pk_info:
            if col[5] == 1:
                pk_col = col[1]
                break
        if not pk_col and pk_info:
            pk_col = pk_info[0][1]

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
        
        # Get balances from journal entries for all asset accounts
        asset_balances = run_query("""
            SELECT 
                CO.account_code,
                CO.account_name,
                COALESCE(SUM(JE.debit), 0) - COALESCE(SUM(JE.credit), 0) as net_balance
            FROM chart_of_accounts CO
            LEFT JOIN jv_entries JE ON CO.account_code = JE.account_code
            WHERE CO.account_type = 'Asset'
            GROUP BY CO.account_code, CO.account_name
            HAVING net_balance != 0
        """)
        
        # Create a dictionary of asset balances
        asset_balance_dict = {}
        for row in asset_balances:
            asset_balance_dict[row[0]] = row[2]
        
        # Get specific bank balances
        cash_bal = asset_balance_dict.get('AST-101', 0)
        union_bank_bal = asset_balance_dict.get('AST-102', 0)
        sbi_bal = asset_balance_dict.get('AST-103', 0)
        
        # Get SB, FD, RD liability balances
        sb_liability = run_query("""
            SELECT COALESCE(SUM(JE.credit), 0) - COALESCE(SUM(JE.debit), 0)
            FROM jv_entries JE
            JOIN chart_of_accounts CO ON JE.account_code = CO.account_code
            WHERE CO.account_code = 'LIA-101'
        """)[0][0] or 0.0
        
        fd_liability = run_query("""
            SELECT COALESCE(SUM(JE.credit), 0) - COALESCE(SUM(JE.debit), 0)
            FROM jv_entries JE
            JOIN chart_of_accounts CO ON JE.account_code = CO.account_code
            WHERE CO.account_code = 'LIA-102'
        """)[0][0] or 0.0
        
        rd_liability = run_query("""
            SELECT COALESCE(SUM(JE.credit), 0) - COALESCE(SUM(JE.debit), 0)
            FROM jv_entries JE
            JOIN chart_of_accounts CO ON JE.account_code = CO.account_code
            WHERE CO.account_code = 'LIA-103'
        """)[0][0] or 0.0
        
        # Get other assets
        other_asset_balances = run_query("""
            SELECT 
                CO.account_code,
                CO.account_name,
                COALESCE(SUM(JE.debit), 0) - COALESCE(SUM(JE.credit), 0) as net_balance
            FROM chart_of_accounts CO
            LEFT JOIN jv_entries JE ON CO.account_code = JE.account_code
            WHERE CO.account_type = 'Asset' 
              AND CO.account_code NOT IN ('AST-101', 'AST-102', 'AST-103')
            GROUP BY CO.account_code, CO.account_name
        """)

        # Get depreciation / expense balances to show reduction on assets side
        depreciation_balances = run_query("""
            SELECT 
                CO.account_code,
                CO.account_name,
                COALESCE(SUM(JE.debit), 0) - COALESCE(SUM(JE.credit), 0) as net_balance
            FROM chart_of_accounts CO
            LEFT JOIN jv_entries JE ON CO.account_code = JE.account_code
            WHERE CO.account_type = 'Expense' 
              AND (CO.account_code LIKE 'EXP-20%' OR LOWER(CO.account_name) LIKE '%depreciation%')
            GROUP BY CO.account_code, CO.account_name
            HAVING net_balance != 0
        """)

        # Get income and expense
        tot_inc_result = run_query("SELECT SUM(JE.credit - JE.debit) FROM jv_entries JE JOIN chart_of_accounts CO ON JE.account_code = CO.account_code WHERE CO.account_type = 'Income'")
        tot_exp_result = run_query("SELECT SUM(JE.debit - JE.credit) FROM jv_entries JE JOIN chart_of_accounts CO ON JE.account_code = CO.account_code WHERE CO.account_type = 'Expense'")
        
        tot_inc = tot_inc_result[0][0] if tot_inc_result and tot_inc_result[0][0] is not None else 0.0
        tot_exp = tot_exp_result[0][0] if tot_exp_result and tot_exp_result[0][0] is not None else 0.0
        net_profit_loss = tot_inc - tot_exp

        col_bs1, col_bs2 = st.columns(2)
        
        with col_bs1:
            st.markdown("### Assets")
            
            asset_rows = []
            total_assets = 0
            
            if cash_bal != 0:
                asset_rows.append(["Cash in Hand", f"₹{cash_bal:,.2f}"])
                total_assets += cash_bal
            
            if union_bank_bal != 0:
                asset_rows.append(["Union Bank of India", f"₹{union_bank_bal:,.2f}"])
                total_assets += union_bank_bal
            
            if sbi_bal != 0:
                asset_rows.append(["State Bank of India", f"₹{sbi_bal:,.2f}"])
                total_assets += sbi_bal
            
            if other_asset_balances:
                for row in other_asset_balances:
                    acc_code, acc_name, net_val = row
                    if net_val != 0:
                        asset_rows.append([f"{acc_code} - {acc_name}", f"₹{net_val:,.2f}"])
                        total_assets += net_val

            # Append depreciation heads purely for reference display
            if depreciation_balances:
                for row in depreciation_balances:
                    acc_code, acc_name, dep_val = row
                    if dep_val != 0:
                        asset_rows.append([f"Less: {acc_code} - {acc_name}", f"₹{dep_val:,.2f}"])
            
            if asset_rows:
                df_assets = pd.DataFrame(asset_rows, columns=["Account Description", "Amount (₹)"])
                st.dataframe(df_assets, use_container_width=True, hide_index=True)
                st.metric("Total Assets", f"₹{total_assets:,.2f}")
            else:
                st.info("No assets recorded.")

        with col_bs2:
            st.markdown("### Liabilities & Equity")
            lia_data = []
            total_lia = 0
            
            if sb_liability != 0:
                lia_data.append(["SB Deposits Control", f"₹{sb_liability:,.2f}"])
                total_lia += sb_liability
            
            if fd_liability != 0:
                lia_data.append(["FD Deposits Control", f"₹{fd_liability:,.2f}"])
                total_lia += fd_liability
            
            if rd_liability != 0:
                lia_data.append(["RD Deposits Control", f"₹{rd_liability:,.2f}"])
                total_lia += rd_liability
            
            # Fetch individual equity/capital entries broken down by their JV narration
            equity_details = run_query("""
                SELECT 
                    CO.account_name,
                    COALESCE(JV.narration, 'Capital') as narration_label,
                    COALESCE(SUM(JE.credit), 0) - COALESCE(SUM(JE.debit), 0) as net_balance
                FROM jv_entries JE
                JOIN chart_of_accounts CO ON JE.account_code = CO.account_code
                LEFT JOIN journal_vouchers JV ON JE.jv_id = JV.jv_id
                WHERE CO.account_type = 'Equity'
                GROUP BY CO.account_code, CO.account_name, JV.narration
                HAVING net_balance != 0
            """)
            
            if equity_details:
                for row in equity_details:
                    acc_name, narration_label, eq_val = row
                    # Displays each person's contribution distinctly using their narration
                    display_label = f"{acc_name} ({narration_label})" if narration_label else acc_name
                    lia_data.append([display_label, f"₹{eq_val:,.2f}"])
                    total_lia += eq_val
            
            if net_profit_loss != 0:
                label_pnl = "Current Year Profit" if net_profit_loss > 0 else "Current Year Loss"
                lia_data.append([label_pnl, f"₹{net_profit_loss:,.2f}"])
                total_lia += net_profit_loss
            
            if lia_data:
                df_lia = pd.DataFrame(lia_data, columns=["Account", "Amount"])
                st.dataframe(df_lia, use_container_width=True, hide_index=True)
                st.metric("Total Liabilities & Equity", f"₹{total_lia:,.2f}")
            else:
                st.info("No liabilities or equity recorded.")

    with tab3:
        st.subheader("Profit and Loss Account")
        
        income_details = run_query("""
            SELECT CO.account_code, CO.account_name, 
                   COALESCE(SUM(JE.credit - JE.debit), 0) as balance
            FROM chart_of_accounts CO
            LEFT JOIN jv_entries JE ON CO.account_code = JE.account_code
            WHERE CO.account_type = 'Income'
            GROUP BY CO.account_code, CO.account_name
            HAVING balance != 0
        """)

        expense_details = run_query("""
            SELECT CO.account_code, CO.account_name, 
                   COALESCE(SUM(JE.debit - JE.credit), 0) as balance
            FROM chart_of_accounts CO
            LEFT JOIN jv_entries JE ON CO.account_code = JE.account_code
            WHERE CO.account_type = 'Expense'
            GROUP BY CO.account_code, CO.account_name
            HAVING balance != 0
        """)

        col_pl1, col_pl2 = st.columns(2)
        
        with col_pl1:
            st.markdown("### Expenditure")
            exp_rows = []
            total_exp = 0.0
            
            if expense_details:
                for row in expense_details:
                    acc_code, acc_name, balance = row
                    exp_rows.append([f"{acc_code} - {acc_name}", f"₹{balance:,.2f}"])
                    total_exp += balance
            
            if exp_rows:
                df_exp = pd.DataFrame(exp_rows, columns=["Expense Account", "Amount (₹)"])
                st.dataframe(df_exp, use_container_width=True, hide_index=True)
            else:
                st.info("No recorded expenses.")
                
            st.metric("Total Expenses", f"₹{total_exp:,.2f}")

        with col_pl2:
            st.markdown("### Income")
            inc_rows = []
            total_inc = 0.0
            
            if income_details:
                for row in income_details:
                    acc_code, acc_name, balance = row
                    inc_rows.append([f"{acc_code} - {acc_name}", f"₹{balance:,.2f}"])
                    total_inc += balance
            
            if inc_rows:
                df_inc = pd.DataFrame(inc_rows, columns=["Income Account", "Amount (₹)"])
                st.dataframe(df_inc, use_container_width=True, hide_index=True)
            else:
                st.info("No recorded incomes.")
                
            st.metric("Total Income", f"₹{total_inc:,.2f}")

        st.divider()
        net_result = total_inc - total_exp
        if net_result > 0:
            st.success(f"**Net Profit for the Period:** ₹{net_result:,.2f}")
        elif net_result < 0:
            st.error(f"**Net Loss for the Period:** ₹{abs(net_result):,.2f}")
        else:
            st.info("**Net Result:** Balanced (₹0.00)")



# --- REPORTS ---
elif menu == "Reports":
    st.title("📄 Comprehensive Bank Reports Center")
    report_type = st.selectbox("Select Report to Generate", ["Customer List Report", "Daily Transactions Report"])
    
    if st.button("Generate Report"):
        if report_type == "Customer List Report":
            data = run_query("SELECT id, name, phone, email, kyc_status, created_at FROM customers")
            if data:
                df_rep = pd.DataFrame(data, columns=["ID", "Name", "Phone", "Email", "KYC Status", "Registered Date"])
                st.dataframe(df_rep, use_container_width=True)
                st.download_button("Download Customer List PDF", create_pdf_report("Customer List Report", df_rep), "customer_list.pdf", "application/pdf")
            else:
                st.info("No customer records found.")
        elif report_type == "Daily Transactions Report":
            data = run_query("SELECT tx_id, account_no, type, amount, mode, narration, date FROM transactions")
            if data:
                df_rep = pd.DataFrame(data, columns=["Tx ID", "Account No", "Type", "Amount (₹)", "Mode", "Narration", "Date"])
                st.dataframe(df_rep, use_container_width=True)
                st.download_button("Download Transactions PDF", create_pdf_report("Daily Transactions Report", df_rep), "transactions_report.pdf", "application/pdf")
            else:
                st.info("No transaction records found.")

# --- SB INTEREST CALCULATION & CREDIT ---
elif menu == "SB Interest Calculation":
    st.title("💰 Savings Bank (SB) Interest Calculation & Crediting")
    st.write("Calculate periodic interest for SB accounts, review details, print/export sheet, and credit directly.")

    sb_accounts = run_query("SELECT s.account_no, c.name, s.balance, s.interest_rate FROM sb_accounts s JOIN customers c ON s.customer_id = c.id")
    
    if sb_accounts:
        df_sb = pd.DataFrame(sb_accounts, columns=["Account No", "Customer Name", "Current Balance", "Interest Rate (%)"])
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            calc_period = st.selectbox("Calculation Period Frequency", ["Monthly", "Quarterly", "Half-Yearly", "Annually"])
        with col_c2:
            interest_multiplier = {"Monthly": 1/12, "Quarterly": 3/12, "Half-Yearly": 6/12, "Annually": 1}[calc_period]
        
        if st.button("Calculate Interest Preview", type="primary"):
            calculated_rows = []
            for idx, row in df_sb.iterrows():
                acct = row["Account No"]
                name = row["Customer Name"]
                bal = row["Current Balance"]
                rate = row["Interest Rate (%)"]
                
                calculated_interest = round((bal * (rate / 100) * interest_multiplier), 2)
                calculated_rows.append({
                    "Account No": acct,
                    "Customer Name": name,
                    "Balance": bal,
                    "Interest Rate (%)": rate,
                    "Calculated Interest": calculated_interest
                })
            
            st.session_state["interest_preview_df"] = pd.DataFrame(calculated_rows)
            st.success("Interest calculated successfully! Review details below.")

        if "interest_preview_df" in st.session_state and not st.session_state["interest_preview_df"].empty:
            preview_df = st.session_state["interest_preview_df"]
            st.subheader("📋 Interest Calculation Sheet Preview")
            st.dataframe(preview_df, use_container_width=True)

            total_interest_payout = preview_df["Calculated Interest"].sum()
            st.metric("Total Interest Payout Amount", f"₹ {total_interest_payout:,.2f}")

            csv_data = preview_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV Interest Report", csv_data, "interest_report.csv", "text/csv")
            
            if st.button("✅ Credit Interest to All SB Accounts", type="primary"):
                for idx, row in preview_df.iterrows():
                    acct = row["Account No"]
                    interest_amt = row["Calculated Interest"]
                    
                    if interest_amt > 0:
                        current_bal = run_query("SELECT balance FROM sb_accounts WHERE account_no=?", (acct,))[0][0]
                        new_bal = current_bal + interest_amt
                        run_query("UPDATE sb_accounts SET balance=? WHERE account_no=?", (new_bal, acct), fetch=False)
                        
                        run_query("""
                            INSERT INTO transactions (tx_id, account_no, type, amount, mode, narration, date)
                            VALUES (?, ?, 'CREDIT', ?, 'Interest Credit', ?, ?)
                        """, (f"INT{datetime.now().strftime('%M%S%f')}", acct, interest_amt, 
                              f"Interest for {calc_period} period", datetime.now().strftime("%Y-%m-%d")), fetch=False)
                        
                        # SB Interest Expense (EXP-101) -> SB Deposits Control (LIA-101)
                        post_automated_jv(f"SB Interest - Account {acct} ({calc_period})", "EXP-101", "LIA-101", interest_amt)
                
                st.success(f"✅ Interest credited to all SB accounts successfully!")
                st.rerun()
    else:
        st.info("No SB accounts found to calculate interest.")


