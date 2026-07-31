# 🏦 AASHA NIDHI PVT LIMITED BANK - COMPLETE SYSTEM
# With IST Timezone, Edit Customer, Delete Everywhere, Print Everywhere

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import uuid
import hashlib
import tempfile
import os
import base64

# IST Timezone handling
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo('Asia/Kolkata')
except ImportError:
    from datetime import timezone, timedelta
    IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now():
    try:
        return datetime.now(IST)
    except:
        return datetime.utcnow() + timedelta(hours=5, minutes=30)

def get_ist_today():
    return get_ist_now().date()

def format_ist_datetime(dt_str):
    if dt_str:
        try:
            dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
            return dt.strftime('%d-%m-%Y %I:%M %p')
        except:
            return dt_str
    return 'N/A'

try:
    from fpdf import FPDF
except ImportError:
    try:
        from fpdf2 import FPDF
    except ImportError:
        FPDF = None

# ==================== DATABASE SETUP ====================
def init_database():
    try:
        conn = sqlite3.connect('banking_system.db')
        c = conn.cursor()
        
        # Users table
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Customers table
        c.execute('''CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            date_of_birth DATE NOT NULL,
            gender TEXT,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            address TEXT,
            city TEXT,
            state TEXT,
            pincode TEXT,
            pan_number TEXT UNIQUE,
            aadhar_number TEXT UNIQUE,
            kyc_status TEXT DEFAULT 'PENDING',
            kyc_verified_by INTEGER,
            kyc_verified_at TIMESTAMP,
            pan_document BLOB,
            aadhar_document BLOB,
            photo BLOB,
            signature BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )''')
        
        # Accounts table
        c.execute('''CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT UNIQUE NOT NULL,
            customer_id INTEGER NOT NULL,
            account_type TEXT NOT NULL,
            balance DECIMAL(15,2) DEFAULT 0.00,
            status TEXT DEFAULT 'ACTIVE',
            interest_rate DECIMAL(5,2),
            last_interest_calculation DATE,
            total_interest_earned DECIMAL(15,2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )''')
        
        # Fixed Deposits table
        c.execute('''CREATE TABLE IF NOT EXISTS fixed_deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fd_number TEXT UNIQUE NOT NULL,
            account_id INTEGER NOT NULL,
            principal_amount DECIMAL(15,2) NOT NULL,
            interest_rate DECIMAL(5,2) NOT NULL,
            start_date DATE NOT NULL,
            maturity_date DATE NOT NULL,
            maturity_amount DECIMAL(15,2),
            tenure_months INTEGER NOT NULL,
            status TEXT DEFAULT 'ACTIVE',
            nominee_name TEXT,
            nominee_relation TEXT,
            closed_date DATE,
            closed_amount DECIMAL(15,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts (id)
        )''')
        
        # Check if closed_date and closed_amount columns exist
        c.execute("PRAGMA table_info(fixed_deposits)")
        columns = [col[1] for col in c.fetchall()]
        if 'closed_date' not in columns:
            c.execute("ALTER TABLE fixed_deposits ADD COLUMN closed_date DATE")
        if 'closed_amount' not in columns:
            c.execute("ALTER TABLE fixed_deposits ADD COLUMN closed_amount DECIMAL(15,2)")
        
        # Recurring Deposits table
        c.execute('''CREATE TABLE IF NOT EXISTS recurring_deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rd_number TEXT UNIQUE NOT NULL,
            account_id INTEGER NOT NULL,
            monthly_amount DECIMAL(15,2) NOT NULL,
            interest_rate DECIMAL(5,2) NOT NULL,
            start_date DATE NOT NULL,
            maturity_date DATE NOT NULL,
            maturity_amount DECIMAL(15,2),
            tenure_months INTEGER NOT NULL,
            installments_paid INTEGER DEFAULT 0,
            total_installments INTEGER NOT NULL,
            status TEXT DEFAULT 'ACTIVE',
            nominee_name TEXT,
            nominee_relation TEXT,
            closed_date DATE,
            closed_amount DECIMAL(15,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts (id)
        )''')
        
        # Check if closed_date and closed_amount columns exist in recurring_deposits
        c.execute("PRAGMA table_info(recurring_deposits)")
        columns = [col[1] for col in c.fetchall()]
        if 'closed_date' not in columns:
            c.execute("ALTER TABLE recurring_deposits ADD COLUMN closed_date DATE")
        if 'closed_amount' not in columns:
            c.execute("ALTER TABLE recurring_deposits ADD COLUMN closed_amount DECIMAL(15,2)")
        
        # Retrieval Accounts table
        c.execute('''CREATE TABLE IF NOT EXISTS retrieval_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT UNIQUE NOT NULL,
            customer_id INTEGER NOT NULL,
            balance DECIMAL(15,2) DEFAULT 0.00,
            status TEXT DEFAULT 'ACTIVE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )''')
        
        # Matured Deposits table
        c.execute('''CREATE TABLE IF NOT EXISTS matured_deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deposit_id TEXT UNIQUE NOT NULL,
            customer_id INTEGER NOT NULL,
            original_deposit_type TEXT NOT NULL,
            original_deposit_number TEXT NOT NULL,
            principal_amount DECIMAL(15,2) NOT NULL,
            interest_earned DECIMAL(15,2) DEFAULT 0.00,
            total_amount DECIMAL(15,2) NOT NULL,
            maturity_date DATE NOT NULL,
            deposited_date DATE NOT NULL,
            status TEXT DEFAULT 'ACTIVE',
            withdrawn_date DATE,
            withdrawn_amount DECIMAL(15,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )''')
        
        # Transactions table
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE NOT NULL,
            account_id INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,
            amount DECIMAL(15,2) NOT NULL,
            balance_after DECIMAL(15,2) NOT NULL,
            description TEXT,
            reference_type TEXT,
            reference_id TEXT,
            voucher_type TEXT,
            voucher_number TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )''')
        
        # System Settings table
        c.execute('''CREATE TABLE IF NOT EXISTS system_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Chart of Accounts table
        c.execute('''CREATE TABLE IF NOT EXISTS chart_of_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_code TEXT UNIQUE NOT NULL,
            account_name TEXT NOT NULL,
            account_type TEXT NOT NULL,
            category TEXT NOT NULL,
            parent_id INTEGER,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES chart_of_accounts (id)
        )''')
        
        # Journal Vouchers table
        c.execute('''CREATE TABLE IF NOT EXISTS journal_vouchers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_number TEXT UNIQUE NOT NULL,
            voucher_date DATE NOT NULL,
            description TEXT,
            total_amount DECIMAL(15,2) NOT NULL,
            status TEXT DEFAULT 'DRAFT',
            created_by INTEGER,
            posted_by INTEGER,
            posted_at TIMESTAMP,
            customer_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id),
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )''')
        
        # Journal Entries table
        c.execute('''CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_id INTEGER NOT NULL,
            account_id INTEGER,
            account_head TEXT,
            debit_amount DECIMAL(15,2) DEFAULT 0.00,
            credit_amount DECIMAL(15,2) DEFAULT 0.00,
            description TEXT,
            FOREIGN KEY (voucher_id) REFERENCES journal_vouchers (id)
        )''')
        
        # Interest Calculations table
        c.execute('''CREATE TABLE IF NOT EXISTS interest_calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            calculation_date DATE NOT NULL,
            principal_amount DECIMAL(15,2) NOT NULL,
            interest_rate DECIMAL(5,2) NOT NULL,
            interest_earned DECIMAL(15,2) NOT NULL,
            days_calculated INTEGER NOT NULL,
            customer_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts (id),
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )''')
        
        # Expenses table
        c.execute('''CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_id TEXT UNIQUE NOT NULL,
            expense_type TEXT NOT NULL,
            chart_of_accounts_id INTEGER,
            amount DECIMAL(15,2) NOT NULL,
            description TEXT,
            date DATE NOT NULL,
            customer_id INTEGER,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id),
            FOREIGN KEY (customer_id) REFERENCES customers (id),
            FOREIGN KEY (chart_of_accounts_id) REFERENCES chart_of_accounts (id)
        )''')
        
        # Income table
        c.execute('''CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            income_id TEXT UNIQUE NOT NULL,
            income_type TEXT NOT NULL,
            chart_of_accounts_id INTEGER,
            amount DECIMAL(15,2) NOT NULL,
            description TEXT,
            date DATE NOT NULL,
            customer_id INTEGER,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id),
            FOREIGN KEY (customer_id) REFERENCES customers (id),
            FOREIGN KEY (chart_of_accounts_id) REFERENCES chart_of_accounts (id)
        )''')
        
        # Check and add columns if missing
        c.execute("PRAGMA table_info(expenses)")
        columns = [col[1] for col in c.fetchall()]
        if 'chart_of_accounts_id' not in columns:
            c.execute("ALTER TABLE expenses ADD COLUMN chart_of_accounts_id INTEGER")
        if 'customer_id' not in columns:
            c.execute("ALTER TABLE expenses ADD COLUMN customer_id INTEGER")
        
        c.execute("PRAGMA table_info(income)")
        columns = [col[1] for col in c.fetchall()]
        if 'chart_of_accounts_id' not in columns:
            c.execute("ALTER TABLE income ADD COLUMN chart_of_accounts_id INTEGER")
        if 'customer_id' not in columns:
            c.execute("ALTER TABLE income ADD COLUMN customer_id INTEGER")
        
        # Insert default settings
        c.execute("""
            INSERT OR IGNORE INTO system_settings (key, value, description)
            VALUES ('SB_INTEREST_RATE', '3.5', 'SB Account Interest Rate (%)')
        """)
        
        # Insert default Chart of Accounts
        default_accounts = [
            # INCOME - Primary Revenue
            ('INC001', 'Loan Interest Income', 'Income', 'Primary Revenue'),
            ('INC002', 'Investment Income', 'Income', 'Primary Revenue'),
            
            # INCOME - Service Income
            ('INC003', 'Processing Fees', 'Income', 'Service Income'),
            ('INC004', 'Service Charges', 'Income', 'Service Income'),
            ('INC005', 'Commission Income', 'Income', 'Service Income'),
            ('INC006', 'Transaction Fees', 'Income', 'Service Income'),
            
            # INCOME - Other Income
            ('INC007', 'Miscellaneous Income', 'Income', 'Other Income'),
            
            # EXPENSES - Cost of Funds
            ('EXP001', 'SB Interest Paid', 'Expense', 'Cost of Funds'),
            ('EXP002', 'FD Interest Paid', 'Expense', 'Cost of Funds'),
            ('EXP003', 'RD Interest Paid', 'Expense', 'Cost of Funds'),
            ('EXP004', 'Interest on Borrowings', 'Expense', 'Cost of Funds'),
            
            # EXPENSES - Operating Expenses
            ('EXP005', 'Salaries & Benefits', 'Expense', 'Operating Expenses'),
            ('EXP006', 'Rent & Utilities', 'Expense', 'Operating Expenses'),
            ('EXP007', 'Electricity Charges', 'Expense', 'Operating Expenses'),
            ('EXP008', 'Water Charges', 'Expense', 'Operating Expenses'),
            ('EXP009', 'Internet & Telephone', 'Expense', 'Operating Expenses'),
            ('EXP010', 'IT Infrastructure', 'Expense', 'Operating Expenses'),
            
            # EXPENSES - Administrative Expenses
            ('EXP011', 'Printing & Stationary', 'Expense', 'Administrative Expenses'),
            ('EXP012', 'Postage & Courier', 'Expense', 'Administrative Expenses'),
            ('EXP013', 'Office Supplies', 'Expense', 'Administrative Expenses'),
            ('EXP014', 'Conveyance', 'Expense', 'Administrative Expenses'),
            ('EXP015', 'Travel Expenses', 'Expense', 'Administrative Expenses'),
            ('EXP016', 'Legal & Audit Fees', 'Expense', 'Administrative Expenses'),
            
            # EXPENSES - Other Expenses
            ('EXP017', 'Bank Charges', 'Expense', 'Other Expenses'),
            ('EXP018', 'Insurance', 'Expense', 'Other Expenses'),
            ('EXP019', 'Maintenance', 'Expense', 'Other Expenses'),
            ('EXP020', 'Marketing Expenses', 'Expense', 'Other Expenses'),
            ('EXP021', 'Depreciation', 'Expense', 'Other Expenses'),
            ('EXP022', 'Provision for NPAs', 'Expense', 'Other Expenses'),
            ('EXP023', 'Miscellaneous Expenses', 'Expense', 'Other Expenses'),
        ]
        
        for acc_code, acc_name, acc_type, category in default_accounts:
            c.execute("""
                INSERT OR IGNORE INTO chart_of_accounts 
                (account_code, account_name, account_type, category)
                VALUES (?, ?, ?, ?)
            """, (acc_code, acc_name, acc_type, category))
        
        # Update existing closed FDs with closed_amount if null
        c.execute("""
            UPDATE fixed_deposits 
            SET closed_amount = maturity_amount 
            WHERE status = 'CLOSED' AND closed_amount IS NULL
        """)
        
        # Update existing closed RDs with closed_amount if null
        c.execute("""
            UPDATE recurring_deposits 
            SET closed_amount = maturity_amount 
            WHERE status = 'MATURED' AND closed_amount IS NULL
        """)
        
        conn.commit()
        conn.close()
        print("Database initialized successfully!")
        
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise

# ==================== UTILITY FUNCTIONS ====================
def get_db():
    return sqlite3.connect('banking_system.db')

def generate_id(prefix):
    return f"{prefix}{get_ist_now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4]}"

def generate_account_number(account_type):
    prefix = '100' if account_type == 'SB' else '200' if account_type == 'FD' else '300' if account_type == 'RD' else '400'
    return f"{prefix}{get_ist_now().strftime('%y%m%d')}{str(uuid.uuid4().int)[:6]}"

def generate_voucher_number(voucher_type):
    prefix = 'PMT' if voucher_type == 'PAYMENT' else 'RCT' if voucher_type == 'RECEIPT' else 'JNL'
    return f"{prefix}{get_ist_now().strftime('%Y%m%d%H%M')}{str(uuid.uuid4().int)[:4]}"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_user(username, password):
    c = get_db()
    cur = c.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=? AND is_active=1", 
                (username, hash_password(password)))
    user = cur.fetchone()
    c.close()
    return user

def create_default_admin():
    c = get_db()
    if c.execute("SELECT COUNT(*) FROM users WHERE username='admin'").fetchone()[0] == 0:
        c.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)", 
                  ('admin', hash_password('admin123'), 'admin'))
        c.commit()
    c.close()

def get_current_sb_interest_rate():
    c = get_db()
    rate = c.execute("""
        SELECT value FROM system_settings WHERE key = 'SB_INTEREST_RATE'
    """).fetchone()
    c.close()
    if rate:
        return float(rate[0])
    return 3.5

def update_sb_interest_rate(new_rate):
    conn = get_db()
    conn.execute("""
        UPDATE system_settings 
        SET value = ?, updated_at = CURRENT_TIMESTAMP
        WHERE key = 'SB_INTEREST_RATE'
    """, (str(new_rate),))
    conn.commit()
    conn.close()

def calculate_fd_maturity(principal, rate, months):
    return round(principal * (1 + rate/400) ** (months/3), 2)

def calculate_rd_maturity(monthly, rate, months):
    return round(monthly * (((1 + rate/400) ** (months/3) - 1) / (1 - (1 + rate/400) ** (-1/3))), 2)

def calculate_sb_interest(balance, rate, days):
    return 0 if balance <= 0 else round((balance * rate * days) / (100 * 365), 2)

# ==================== PDF GENERATION ====================
def create_pdf(title, content, filename):
    if FPDF is None:
        st.warning("⚠️ PDF library not available. Please install fpdf.")
        return None
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(190, 10, 'AASHA NIDHI PVT LIMITED BANK', 0, 1, 'C')
        pdf.set_font('Arial', '', 10)
        pdf.cell(190, 6, 'Balaramapuram', 0, 1, 'C')
        pdf.cell(190, 6, f'Date: {get_ist_now().strftime("%d-%m-%Y %I:%M %p")}', 0, 1, 'C')
        pdf.line(10, 35, 200, 35)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(190, 10, title, 0, 1, 'C')
        pdf.ln(5)
        pdf.set_font('Arial', '', 10)
        for line in content:
            pdf.multi_cell(190, 6, line)
            pdf.ln(2)
        pdf.set_y(-30)
        pdf.set_font('Arial', 'I', 8)
        pdf.cell(190, 10, f'Generated on: {get_ist_now().strftime("%d-%m-%Y %I:%M %p")}', 0, 1, 'C')
        pdf.cell(190, 10, 'This is a system generated statement', 0, 1, 'C')
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        pdf.output(temp_file.name)
        temp_file.close()
        return temp_file.name
    except Exception as e:
        st.error(f"PDF generation error: {e}")
        return None

def create_download_button(file_path, filename, button_text="📥 Download PDF"):
    if file_path and os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}.pdf">📥 {button_text}</a>'
        st.markdown(href, unsafe_allow_html=True)
        try:
            os.unlink(file_path)
        except:
            pass

# ==================== CUSTOMER SELECTOR ====================
def customer_selector(label="👤 Select Customer", key_prefix="cust"):
    c = get_db()
    query = """
        SELECT 
            c.id,
            c.customer_id,
            c.first_name || ' ' || c.last_name as full_name,
            c.kyc_status,
            a.id as account_id,
            a.account_number,
            a.balance,
            COALESCE(a.total_interest_earned, 0) as interest
        FROM customers c
        LEFT JOIN accounts a ON c.id = a.customer_id AND a.account_type = 'SB' AND a.status = 'ACTIVE'
        ORDER BY c.first_name
    """
    customers = c.execute(query).fetchall()
    c.close()
    
    if not customers:
        st.warning("⚠️ No customers found!")
        return None, None, None, None, None
    
    options = []
    for cust in customers:
        if cust[4] is None:
            display = f"❌ {cust[2]} | {cust[1]} | No SB Account | KYC: {cust[3]}"
            options.append({
                'display': display,
                'customer_id': cust[0],
                'customer_name': cust[2],
                'account_id': None,
                'account_number': None,
                'balance': 0,
                'interest': 0,
                'total_balance': 0,
                'has_account': False
            })
        else:
            total_balance = cust[6] + cust[7]
            kyc_emoji = "✅" if cust[3] == 'VERIFIED' else "⏳" if cust[3] == 'PENDING' else "❌"
            display = f"{kyc_emoji} {cust[2]} | A/c: {cust[5]} | Bal: ₹{total_balance:,.2f} | KYC: {cust[3]}"
            options.append({
                'display': display,
                'customer_id': cust[0],
                'customer_name': cust[2],
                'account_id': cust[4],
                'account_number': cust[5],
                'balance': cust[6],
                'interest': cust[7],
                'total_balance': total_balance,
                'has_account': True
            })
    
    selected = st.selectbox(
        label,
        options,
        format_func=lambda x: x['display'],
        key=f"{key_prefix}_selector"
    )
    
    if selected and selected['has_account']:
        return (
            selected['customer_id'],
            selected['customer_name'],
            selected['account_id'],
            selected['account_number'],
            selected['total_balance']
        )
    elif selected and not selected['has_account']:
        st.warning(f"⚠️ {selected['customer_name']} doesn't have an SB account yet!")
        return selected['customer_id'], selected['customer_name'], None, None, 0
    return None, None, None, None, None

# ==================== CSS ====================
def load_enterprise_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        * { font-family: 'Plus Jakarta Sans', sans-serif; }
        .main-header {
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            color: white;
            padding: 1rem 2rem;
            border-radius: 16px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        .main-header h1 { margin: 0; font-size: 1.6rem; font-weight: 800; }
        .main-header small { opacity: 0.8; font-size: 0.85rem; }
        .bank-logo { display: flex; align-items: center; gap: 15px; }
        .bank-logo-icon { font-size: 2.5rem; animation: pulse 2s infinite; }
        @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); } }
        .header-time { background: rgba(255,255,255,0.15); padding: 0.3rem 1rem; border-radius: 20px; font-size: 0.8rem; margin-top: 5px; display: inline-block; }
        .stButton > button { border-radius: 10px !important; font-weight: 700 !important; transition: all 0.3s ease !important; }
        .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.15) !important; }
        .stButton > button[kind="primary"] { background: linear-gradient(135deg, #0f2027, #2c5364) !important; color: white !important; }
        .stButton > button[kind="primary"]:hover { background: linear-gradient(135deg, #1a3340, #3a6b80) !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 8px 16px; background: #f0f2f6; font-weight: 600; }
        .stTabs [aria-selected="true"] { background: #0f2027 !important; color: white !important; }
        [data-testid="stSidebar"] { background: linear-gradient(180deg, #0f2027, #203a43) !important; }
        [data-testid="stSidebar"] .stButton > button { color: white !important; background: transparent !important; border: 1px solid rgba(255,255,255,0.1) !important; text-align: left !important; justify-content: flex-start !important; }
        [data-testid="stSidebar"] .stButton > button:hover { background: rgba(255,255,255,0.1) !important; border-color: rgba(255,255,255,0.3) !important; }
        .sidebar-logo { text-align: center; padding: 20px 0; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px; }
        .sidebar-logo h2 { color: white; margin: 0; font-size: 1.2rem; font-weight: 700; }
        .sidebar-logo p { color: rgba(255,255,255,0.6); font-size: 0.8rem; margin: 0; }
        .sidebar-logo .logo-icon { font-size: 3rem; display: block; margin-bottom: 5px; }
        .stDataFrame { border-radius: 12px !important; overflow: hidden !important; }
        .stMetric { background: white; padding: 1rem; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: all 0.3s ease; }
        .stMetric:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.1); }
        .delete-btn { background: #dc3545 !important; color: white !important; }
        .delete-btn:hover { background: #c82333 !important; }
    </style>
    """, unsafe_allow_html=True)

# ==================== SESSION STATE ====================
def init_session_state():
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = 'dashboard'

# ==================== MAIN APP ====================
def main():
    st.set_page_config(
        page_title="🏦 Aasha Nidhi Bank - Complete Banking System",
        page_icon="🏦",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    init_database()
    create_default_admin()
    init_session_state()
    load_enterprise_css()
    if st.session_state.user is None:
        show_login()
    else:
        show_app()

def show_login():
    st.markdown(f"""
    <div style="display:flex;justify-content:center;align-items:center;min-height:80vh">
        <div style="background:white;padding:3rem;border-radius:24px;text-align:center;max-width:420px;box-shadow:0 20px 60px rgba(0,0,0,0.1);width:100%">
            <div style="font-size:4rem;margin-bottom:0">🏦</div>
            <h1 style="font-size:1.8rem;font-weight:800;margin:0.5rem 0;color:#0f2027">AASHA NIDHI BANK</h1>
            <p style="color:#6c757d;margin-bottom:2rem">Balaramapuram • {get_ist_now().strftime('%d-%m-%Y %I:%M %p')}</p>
    """, unsafe_allow_html=True)
    
    username = st.text_input("👤 Username", placeholder="Enter your username")
    password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🚀 Sign In", use_container_width=True, type="primary"):
            user = login_user(username, password)
            if user:
                st.session_state.user = {'id': user[0], 'username': user[1], 'role': user[3]}
                st.rerun()
            else:
                st.error("❌ Invalid credentials!")
        st.markdown("""
        <div style="margin-top:1rem;padding:1rem;background:#f8f9fa;border-radius:12px">
            <small style="color:#6c757d">🔑 Demo: <strong>admin</strong> / <strong>admin123</strong></small>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

def show_app():
    current_time = get_ist_now().strftime('%d-%m-%Y %I:%M:%S %p')
    st.markdown(f"""
    <div class="main-header">
        <div class="bank-logo">
            <span class="bank-logo-icon">🏦</span>
            <div>
                <h1>AASHA NIDHI PVT LIMITED BANK</h1>
                <small>📍 BALARAMAPURAM • <span class="header-time">🕐 {current_time}</span></small>
            </div>
        </div>
        <div style="text-align:right">
            <span style="font-size:1.1rem;font-weight:600">👤 {st.session_state.user['username']}</span>
            <br>
            <span style="background:rgba(255,255,255,0.2);padding:0.25rem 1rem;border-radius:20px;font-size:0.8rem">
                {st.session_state.user['role'].upper()}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-logo">
            <span class="logo-icon">🏦</span>
            <h2>AASHA NIDHI BANK</h2>
            <p>Complete Banking Solution</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("### 📋 Navigation")
        st.markdown("---")
        
        menu_items = {
            'dashboard': '📊 Dashboard',
            'customer_management': '👥 Customers',
            'kyc_verification': '✅ KYC Verification',
            'create_sb_account': '💰 Open SB Account',
            'sb_accounts': '🏦 SB Accounts',
            'fixed_deposits': '📈 Fixed Deposits',
            'recurring_deposits': '🔄 Recurring Dep.',
            'retrieval_account': '💰 Retrieval Account',
            'chart_of_accounts': '📊 Chart of Accounts',
            'transactions': '💳 Transactions',
            'journal_vouchers': '📝 Journal Vouchers',
            'income_expenses': '💰 Income & Exp.',
            'interest_calculation': '📊 Interest',
            'trial_balance': '⚖️ Trial Balance',
            'balance_sheet': '📋 Balance Sheet',
            'profit_loss': '📈 Profit & Loss',
            'reports': '📄 Reports'
        }
        
        for key, label in menu_items.items():
            if st.button(label, key=f"m_{key}", use_container_width=True):
                st.session_state.page = key
                st.rerun()
        
        st.markdown("---")
        st.markdown("### 🔧 Settings")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.user = None
            st.rerun()
        
        st.markdown(f"""
        <div style="position:fixed;bottom:1rem;left:1rem;right:1rem;text-align:center;color:rgba(255,255,255,0.4);font-size:0.7rem;padding:10px;">
            © 2024 Aasha Nidhi Bank<br>
            v3.0 • {get_ist_now().strftime('%d-%m-%Y %I:%M %p')}
        </div>
        """, unsafe_allow_html=True)
    
    page = st.session_state.get('page', 'dashboard')
    if page == 'dashboard':
        dashboard()
    elif page == 'customer_management':
        customer_management()
    elif page == 'kyc_verification':
        kyc_verification()
    elif page == 'create_sb_account':
        create_sb_account()
    elif page == 'sb_accounts':
        sb_accounts()
    elif page == 'fixed_deposits':
        fixed_deposits()
    elif page == 'recurring_deposits':
        recurring_deposits()
    elif page == 'retrieval_account':
        retrieval_account()
    elif page == 'chart_of_accounts':
        chart_of_accounts()
    elif page == 'transactions':
        transactions()
    elif page == 'journal_vouchers':
        journal_vouchers()
    elif page == 'income_expenses':
        income_expenses()
    elif page == 'interest_calculation':
        interest_calculation()
    elif page == 'trial_balance':
        trial_balance()
    elif page == 'balance_sheet':
        balance_sheet()
    elif page == 'profit_loss':
        profit_loss()
    elif page == 'reports':
        reports()
    else:
        st.error(f"❌ Page '{page}' not found")

# ==================== DASHBOARD ====================
def dashboard():
    c = get_db()
    total_customers = c.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    total_sb_accounts = c.execute("SELECT COUNT(*) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
    total_sb_balance = c.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
    total_interest = c.execute("SELECT COALESCE(SUM(total_interest_earned),0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
    total_fd = c.execute("SELECT COALESCE(SUM(principal_amount),0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
    total_rd = c.execute("SELECT COALESCE(SUM(monthly_amount*installments_paid),0) FROM recurring_deposits WHERE status='ACTIVE'").fetchone()[0]
    pending_kyc = c.execute("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'").fetchone()[0]
    rejected_kyc = c.execute("SELECT COUNT(*) FROM customers WHERE kyc_status='REJECTED'").fetchone()[0]
    total_retrieval = c.execute("SELECT COALESCE(SUM(balance),0) FROM retrieval_accounts WHERE status='ACTIVE'").fetchone()[0]
    current_rate = get_current_sb_interest_rate()
    c.close()
    
    st.markdown("### 📊 Bank Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Total Customers", f"{total_customers:,}")
        st.metric("✅ KYC Verified", f"{total_customers - pending_kyc - rejected_kyc:,}")
    with col2:
        st.metric("🏦 SB Accounts", f"{total_sb_accounts:,}")
        st.metric("💰 SB Deposits", f"₹ {total_sb_balance:,.2f}")
    with col3:
        st.metric("📈 FD Deposits", f"₹ {total_fd:,.2f}")
        st.metric("🔄 RD Deposits", f"₹ {total_rd:,.2f}")
    with col4:
        st.metric("💹 Interest Earned", f"₹ {total_interest:,.2f}")
        st.metric("💰 Retrieval Balance", f"₹ {total_retrieval:,.2f}")
    
    st.info(f"📈 Current SB Interest Rate: **{current_rate}%** per annum")
    
    st.markdown("### 🕐 Recent Activity")
    c = get_db()
    recent_txns = c.execute("""
        SELECT t.transaction_id, COALESCE(c.first_name||' '||c.last_name,'System'), 
               t.transaction_type, t.amount, t.created_at
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id=a.id
        LEFT JOIN customers c ON a.customer_id=c.id
        ORDER BY t.created_at DESC LIMIT 10
    """).fetchall()
    c.close()
    
    if recent_txns:
        data = []
        for txn in recent_txns:
            data.append({
                'Txn ID': txn[0],
                'Customer': txn[1],
                'Type': '✅ Credit' if txn[2] == 'CREDIT' else '💳 Debit',
                'Amount': f"₹ {txn[3]:,.2f}",
                'Time': format_ist_datetime(txn[4])
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No recent transactions")

# ==================== CUSTOMER MANAGEMENT ====================
def customer_management():
    tab1, tab2, tab3 = st.tabs(["📝 Register Customer", "👥 View Customers", "✏️ Edit Customer"])
    
    # Tab 1: Register Customer
    with tab1:
        st.markdown("### 📝 Register New Customer")
        with st.form("register_customer"):
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input("👤 First Name*", placeholder="Enter first name")
                last_name = st.text_input("👤 Last Name*", placeholder="Enter last name")
                dob = st.date_input("🎂 Date of Birth*", min_value=date(1900, 1, 1), max_value=get_ist_today())
                email = st.text_input("📧 Email*", placeholder="customer@email.com")
                phone = st.text_input("📱 Phone*", placeholder="9876543210")
                gender = st.selectbox("⚥ Gender", ["Male", "Female", "Other"])
            with col2:
                pan = st.text_input("🪪 PAN Number*", placeholder="ABCDE1234F")
                aadhar = st.text_input("🆔 Aadhar Number*", placeholder="1234 5678 9012")
                address = st.text_area("🏠 Address", placeholder="Street, City, State, Pincode")
                city = st.text_input("🏙️ City", placeholder="City")
                state = st.text_input("🏛️ State", placeholder="State")
                pincode = st.text_input("📮 Pincode", placeholder="695001")
            
            st.markdown("### 📎 Documents Upload")
            col1, col2 = st.columns(2)
            with col1:
                pan_doc = st.file_uploader("🪪 PAN Document*", type=['jpg', 'jpeg', 'png', 'pdf'])
                photo = st.file_uploader("📸 Photo", type=['jpg', 'jpeg', 'png'])
            with col2:
                aadhar_doc = st.file_uploader("🆔 Aadhar Document*", type=['jpg', 'jpeg', 'png', 'pdf'])
                signature = st.file_uploader("✍️ Signature", type=['jpg', 'jpeg', 'png'])
            
            if st.form_submit_button("✅ Register Customer", use_container_width=True, type="primary"):
                if all([first_name, last_name, email, phone, pan, aadhar]) and pan_doc and aadhar_doc:
                    conn = get_db()
                    try:
                        conn.execute("""
                            INSERT INTO customers (
                                customer_id, first_name, last_name, date_of_birth, gender,
                                email, phone, address, city, state, pincode,
                                pan_number, aadhar_number, pan_document, aadhar_document,
                                photo, signature, kyc_status
                            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """, (
                            generate_id('CUST'), first_name, last_name, dob, gender,
                            email, phone, address, city, state, pincode,
                            pan, aadhar, pan_doc.read(), aadhar_doc.read(),
                            photo.read() if photo else None,
                            signature.read() if signature else None,
                            'PENDING'
                        ))
                        conn.commit()
                        conn.close()
                        st.success("✅ Customer registered successfully! 🎉")
                        st.balloons()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                else:
                    st.error("❌ Please fill all required fields (*)")
    
    # Tab 2: View Customers
    with tab2:
        st.markdown("### 👥 Customer List")
        conn = get_db()
        customers = conn.execute("""
            SELECT id, customer_id, first_name, last_name, email, phone, kyc_status,
                   CASE WHEN kyc_status='VERIFIED' THEN '✅' WHEN kyc_status='PENDING' THEN '⏳' ELSE '❌' END as status_emoji,
                   created_at
            FROM customers ORDER BY created_at DESC
        """).fetchall()
        conn.close()
        
        if customers:
            data = []
            for cust in customers:
                data.append({
                    'Customer ID': cust[1],
                    'First': cust[2],
                    'Last': cust[3],
                    'Email': cust[4],
                    'Phone': cust[5],
                    'KYC': cust[6],
                    'Status': cust[7],
                    'Created': format_ist_datetime(cust[8]) if cust[8] else 'N/A'
                })
            df = pd.DataFrame(data)
            st.dataframe(df[['Customer ID', 'First', 'Last', 'Email', 'Phone', 'KYC', 'Status']], use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.download_button("📥 Export CSV", df.to_csv(index=False), "customers.csv", "text/csv")
            with col2:
                if st.button("📄 Print PDF", use_container_width=True):
                    content = ["👥 CUSTOMER LIST", "=" * 50]
                    content.append(f"Generated on: {get_ist_now().strftime('%d-%m-%Y %I:%M %p')}")
                    content.append(f"Total Customers: {len(customers)}")
                    content.append("")
                    for cust in customers:
                        content.append(f"ID: {cust[1]} | Name: {cust[2]} {cust[3]} | Email: {cust[4]} | Phone: {cust[5]} | KYC: {cust[6]}")
                    pdf_file = create_pdf("Customer List", content, "customer_list")
                    if pdf_file:
                        create_download_button(pdf_file, "customer_list", "📥 Download PDF Report")
            with col3:
                with st.expander("🗑️ Delete Customer"):
                    st.warning("⚠️ This will delete the customer and ALL related records.")
                    delete_id = st.text_input("Enter Customer ID to delete:", key="del_cust_id")
                    if delete_id:
                        confirm = st.checkbox("☑️ Confirm delete?", key="del_cust_confirm")
                        if confirm and st.button("🗑️ Delete", use_container_width=True, type="secondary"):
                            try:
                                conn = get_db()
                                customer = conn.execute("SELECT id FROM customers WHERE customer_id=?", (delete_id,)).fetchone()
                                if customer:
                                    cust_id = customer[0]
                                    conn.execute("DELETE FROM accounts WHERE customer_id=?", (cust_id,))
                                    conn.execute("DELETE FROM fixed_deposits WHERE account_id IN (SELECT id FROM accounts WHERE customer_id=?)", (cust_id,))
                                    conn.execute("DELETE FROM recurring_deposits WHERE account_id IN (SELECT id FROM accounts WHERE customer_id=?)", (cust_id,))
                                    conn.execute("DELETE FROM retrieval_accounts WHERE customer_id=?", (cust_id,))
                                    conn.execute("DELETE FROM matured_deposits WHERE customer_id=?", (cust_id,))
                                    conn.execute("DELETE FROM transactions WHERE account_id IN (SELECT id FROM accounts WHERE customer_id=?)", (cust_id,))
                                    conn.execute("DELETE FROM income WHERE customer_id=?", (cust_id,))
                                    conn.execute("DELETE FROM expenses WHERE customer_id=?", (cust_id,))
                                    conn.execute("DELETE FROM customers WHERE customer_id=?", (delete_id,))
                                    conn.commit()
                                    conn.close()
                                    st.success("✅ Customer and all related records deleted!")
                                    st.rerun()
                                else:
                                    st.error("❌ Customer not found!")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
        else:
            st.info("No customers registered yet")
    
    # Tab 3: Edit Customer
    with tab3:
        st.markdown("### ✏️ Edit Customer Details")
        
        conn = get_db()
        all_customers = conn.execute("""
            SELECT id, customer_id, first_name, last_name, date_of_birth, gender,
                   email, phone, address, city, state, pincode,
                   pan_number, aadhar_number, kyc_status
            FROM customers ORDER BY first_name
        """).fetchall()
        conn.close()
        
        if all_customers:
            cust_options = {f"{c[1]} - {c[2]} {c[3]}": c[0] for c in all_customers}
            selected_cust = st.selectbox("👤 Select Customer to Edit", list(cust_options.keys()))
            
            if selected_cust:
                cust_id = cust_options[selected_cust]
                conn = get_db()
                cust = conn.execute("SELECT * FROM customers WHERE id=?", (cust_id,)).fetchone()
                conn.close()
                
                if cust:
                    with st.form("edit_customer_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            first_name = st.text_input("First Name*", value=cust[3])
                            last_name = st.text_input("Last Name*", value=cust[4])
                            dob = st.date_input("Date of Birth*", value=datetime.strptime(cust[5], '%Y-%m-%d').date())
                            email = st.text_input("Email*", value=cust[7])
                            phone = st.text_input("Phone*", value=cust[8])
                            gender = st.selectbox("Gender", ["Male", "Female", "Other"], index=["Male", "Female", "Other"].index(cust[6]) if cust[6] in ["Male", "Female", "Other"] else 0)
                        with col2:
                            pan = st.text_input("PAN Number*", value=cust[10])
                            aadhar = st.text_input("Aadhar Number*", value=cust[11])
                            address = st.text_area("Address", value=cust[9] if cust[9] else "")
                            city = st.text_input("City", value=cust[12] if cust[12] else "")
                            state = st.text_input("State", value=cust[13] if cust[13] else "")
                            pincode = st.text_input("Pincode", value=cust[14] if cust[14] else "")
                        
                        st.info(f"Current KYC Status: **{cust[12]}**")
                        
                        if st.form_submit_button("💾 Update Customer", use_container_width=True, type="primary"):
                            if all([first_name, last_name, email, phone, pan, aadhar]):
                                conn = get_db()
                                try:
                                    conn.execute("""
                                        UPDATE customers SET
                                            first_name=?, last_name=?, date_of_birth=?,
                                            gender=?, email=?, phone=?, address=?,
                                            city=?, state=?, pincode=?,
                                            pan_number=?, aadhar_number=?
                                        WHERE id=?
                                    """, (first_name, last_name, dob, gender, email, phone,
                                          address, city, state, pincode, pan, aadhar, cust_id))
                                    conn.commit()
                                    conn.close()
                                    st.success("✅ Customer updated successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")
                            else:
                                st.error("❌ Please fill all required fields (*)")
        else:
            st.info("No customers to edit")

# ==================== KYC VERIFICATION ====================
def kyc_verification():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    pending = c.execute("SELECT * FROM customers WHERE kyc_status='PENDING'").fetchall()
    
    if not pending:
        st.success("✅ All customers are KYC verified! 🎉")
        c.close()
        return
    
    st.markdown(f"### ✅ KYC Verification ({len(pending)} pending)")
    
    for cust in pending:
        with st.expander(f"⏳ {cust[3]} {cust[4]} (ID: {cust[2]})"):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(f"""
                **📋 Customer Details:**
                - 👤 Name: {cust[3]} {cust[4]}
                - 📧 Email: {cust[7]}
                - 📱 Phone: {cust[8]}
                - 📅 DOB: {cust[5]}
                - ⚥ Gender: {cust[6]}
                - 🪪 PAN: {cust[10]}
                - 🆔 Aadhar: {cust[11]}
                - 🏠 Address: {cust[9] or 'N/A'}
                """)
            with col2:
                st.markdown("**📎 Documents:**")
                if cust[14]:
                    st.success("✅ PAN Document Uploaded")
                if cust[15]:
                    st.success("✅ Aadhar Document Uploaded")
                if cust[16]:
                    st.success("✅ Photo Uploaded")
                if cust[17]:
                    st.success("✅ Signature Uploaded")
            
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✅ Approve", key=f"approve_{cust[0]}", use_container_width=True):
                    c.execute("""
                        UPDATE customers 
                        SET kyc_status='VERIFIED', 
                            kyc_verified_by=?, 
                            kyc_verified_at=CURRENT_TIMESTAMP 
                        WHERE id=?
                    """, (st.session_state.user['id'], cust[0]))
                    c.commit()
                    st.success(f"✅ KYC Approved for {cust[3]} {cust[4]}!")
                    st.rerun()
            with col2:
                if st.button("❌ Reject", key=f"reject_{cust[0]}", use_container_width=True):
                    c.execute("UPDATE customers SET kyc_status='REJECTED' WHERE id=?", (cust[0],))
                    c.commit()
                    st.warning(f"❌ KYC Rejected for {cust[3]} {cust[4]}")
                    st.rerun()
            with col3:
                if st.button("⏳ Keep Pending", key=f"pending_{cust[0]}", use_container_width=True):
                    st.info("Status remains PENDING")
    c.close()

# ==================== CREATE SB ACCOUNT ====================
def create_sb_account():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    current_rate = get_current_sb_interest_rate()
    
    # Allow ALL customers regardless of KYC status
    customers = c.execute("""
        SELECT c.id, c.customer_id, c.first_name||' '||c.last_name as name, c.kyc_status
        FROM customers c
        WHERE NOT EXISTS (
            SELECT 1 FROM accounts a 
            WHERE a.customer_id = c.id AND a.account_type='SB' AND a.status='ACTIVE'
        )
        ORDER BY c.first_name
    """).fetchall()
    
    if not customers:
        st.success("🎉 All customers already have SB accounts!")
        c.close()
        return
    
    st.markdown("### 💰 Open SB Account")
    st.info(f"📈 Current SB Interest Rate: **{current_rate}%** per annum")
    st.info("ℹ️ Customers with any KYC status (PENDING, VERIFIED, REJECTED) can open accounts")
    
    options = []
    for cust in customers:
        kyc_emoji = "✅" if cust[3] == 'VERIFIED' else "⏳" if cust[3] == 'PENDING' else "❌"
        options.append(f"{kyc_emoji} {cust[2]} | {cust[1]} | KYC: {cust[3]}")
    
    selected = st.selectbox("👤 Select Customer", options)
    if selected:
        idx = options.index(selected)
        cust = customers[idx]
        
        with st.form("open_sb"):
            col1, col2 = st.columns(2)
            with col1:
                interest_rate = st.number_input(
                    "📈 Interest Rate (%)",
                    min_value=0.0,
                    max_value=10.0,
                    value=current_rate,
                    step=0.25
                )
                opening_balance = st.number_input(
                    "💰 Opening Balance (₹)",
                    min_value=0.0,
                    step=100.0,
                    value=500.0
                )
            with col2:
                mode = st.selectbox("💳 Funding Mode", ["CASH", "BANK TRANSFER", "CHEQUE", "ONLINE"])
                nominee = st.text_input("👤 Nominee Name (Optional)")
            
            if cust[3] != 'VERIFIED':
                st.warning(f"⚠️ Customer KYC is {cust[3]}. Account can still be opened.")
            
            if st.form_submit_button("✅ Create SB Account", use_container_width=True, type="primary"):
                account_number = generate_account_number('SB')
                conn = get_db()
                try:
                    conn.execute("""
                        INSERT INTO accounts (
                            account_number, customer_id, account_type,
                            balance, interest_rate, last_interest_calculation,
                            total_interest_earned
                        ) VALUES (?,?,?,?,?,DATE('now'),0.00)
                    """, (account_number, cust[0], 'SB', opening_balance, interest_rate))
                    
                    account_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    if opening_balance > 0:
                        conn.execute("""
                            INSERT INTO transactions (
                                transaction_id, account_id, transaction_type,
                                amount, balance_after, description,
                                reference_type, voucher_type, voucher_number,
                                created_by
                            ) VALUES (?,?,?,?,?,?,?,?,?,?)
                        """, (
                            generate_id('TXN'), account_id, 'CREDIT',
                            opening_balance, opening_balance,
                            f"SB Account Opening: {account_number}",
                            mode, 'RECEIPT', generate_voucher_number('RECEIPT'),
                            st.session_state.user['id']
                        ))
                    conn.commit()
                    conn.close()
                    st.success(f"""
                    ✅ SB Account Created Successfully! 🎉
                    📋 **Account Details:**
                    - Account Number: **{account_number}**
                    - Customer: **{cust[2]}**
                    - Opening Balance: **₹ {opening_balance:,.2f}**
                    - Interest Rate: **{interest_rate}%**
                    """)
                    st.balloons()
                except Exception as e:
                    conn.rollback()
                    conn.close()
                    st.error(f"❌ Error: {str(e)}")
    c.close()

# ==================== SB ACCOUNTS ====================
def sb_accounts():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    tab1, tab2, tab3 = st.tabs(["💳 Transact", "📊 Accounts", "📋 Statement"])
    
    with tab1:
        st.markdown("### 💳 Deposit/Withdraw")
        cust_id, cust_name, acc_id, acc_number, balance = customer_selector("👤 Select Customer Account", "txn_customer")
        
        if cust_id and acc_id:
            st.success(f"""
            ✅ **Selected Account:**
            - Customer: **{cust_name}**
            - Account: **{acc_number}**
            - Balance: **₹ {balance:,.2f}**
            """)
            
            with st.form("transaction_form"):
                col1, col2 = st.columns(2)
                with col1:
                    transaction_type = st.radio("📊 Transaction Type", ["💰 Deposit", "💳 Withdraw"], horizontal=True)
                with col2:
                    amount = st.number_input("💵 Amount (₹)", min_value=1.0, step=100.0, value=100.0)
                mode = st.selectbox("💳 Payment Mode", ["CASH", "BANK TRANSFER", "CHEQUE", "ONLINE"], key="sb_txn_mode")
                description = st.text_input("📝 Description", placeholder="Transaction details", key="sb_txn_desc")
                
                if st.form_submit_button("✅ Process Transaction", use_container_width=True, type="primary"):
                    if transaction_type == "💳 Withdraw" and amount > balance:
                        st.error("❌ Insufficient balance!")
                    else:
                        conn = get_db()
                        try:
                            txn_type = "DEBIT" if transaction_type == "💳 Withdraw" else "CREDIT"
                            new_balance = balance - amount if txn_type == "DEBIT" else balance + amount
                            voucher_type = "PAYMENT" if txn_type == "DEBIT" else "RECEIPT"
                            txn_id = generate_id('TXN')
                            voucher_number = generate_voucher_number(voucher_type)
                            
                            conn.execute("""
                                INSERT INTO transactions (
                                    transaction_id, account_id, transaction_type,
                                    amount, balance_after, description,
                                    reference_type, voucher_type, voucher_number,
                                    created_by
                                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                            """, (
                                txn_id, acc_id, txn_type,
                                amount, new_balance, description or f"{transaction_type}",
                                mode, voucher_type, voucher_number,
                                st.session_state.user['id']
                            ))
                            
                            conn.execute("UPDATE accounts SET balance=? WHERE id=?", (new_balance, acc_id))
                            conn.commit()
                            conn.close()
                            
                            st.success(f"""
                            ✅ Transaction Successful! 🎉
                            📋 **Details:**
                            - Type: **{transaction_type}**
                            - Amount: **₹ {amount:,.2f}**
                            - New Balance: **₹ {new_balance:,.2f}**
                            - Transaction ID: **{txn_id}**
                            - Voucher: **{voucher_number}**
                            """)
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            conn.close()
                            st.error(f"❌ Error: {str(e)}")
    
    with tab2:
        st.markdown("### 📊 Active SB Accounts")
        accounts = c.execute("""
            SELECT a.id, a.account_number, c.first_name||' '||c.last_name as customer,
                   a.balance, COALESCE(a.total_interest_earned,0) as interest,
                   a.interest_rate, a.status, c.kyc_status
            FROM accounts a
            JOIN customers c ON a.customer_id = c.id
            WHERE a.account_type='SB'
            ORDER BY a.created_at DESC
        """).fetchall()
        
        if accounts:
            data = []
            for acc in accounts:
                data.append({
                    'ID': acc[0],
                    'Account': acc[1],
                    'Customer': acc[2],
                    'Balance': f"₹ {acc[3]:,.2f}",
                    'Interest': f"₹ {acc[4]:,.2f}",
                    'Rate': f"{acc[5]}%",
                    'Status': acc[6],
                    'KYC': acc[7]
                })
            df = pd.DataFrame(data)
            st.dataframe(df[['Account', 'Customer', 'Balance', 'Interest', 'Rate', 'Status', 'KYC']], use_container_width=True)
            
            total_balance = sum(acc[3] for acc in accounts)
            total_interest = sum(acc[4] for acc in accounts)
            st.info(f"💰 Total SB Deposits: ₹ {total_balance:,.2f} | Total Interest Earned: ₹ {total_interest:,.2f}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📄 Print Report", use_container_width=True):
                    content = ["📊 SB ACCOUNTS REPORT", "=" * 50]
                    content.append(f"Generated on: {get_ist_now().strftime('%d-%m-%Y %I:%M %p')}")
                    content.append(f"Total Accounts: {len(accounts)}")
                    content.append(f"Total Deposits: ₹ {total_balance:,.2f}")
                    content.append("")
                    for acc in accounts:
                        content.append(f"Account: {acc[1]} | Customer: {acc[2]} | Balance: ₹ {acc[3]:,.2f}")
                    pdf_file = create_pdf("SB Accounts Report", content, "sb_accounts")
                    if pdf_file:
                        create_download_button(pdf_file, "sb_accounts", "📥 Download PDF Report")
            
            with col2:
                with st.expander("🗑️ Delete SB Account"):
                    st.warning("⚠️ This will delete the SB account and all its transactions.")
                    acc_num = st.text_input("Enter Account Number to delete:", key="del_sb_acc")
                    if acc_num:
                        confirm = st.checkbox("☑️ Confirm delete?", key="del_sb_confirm")
                        if confirm and st.button("🗑️ Delete", use_container_width=True, type="secondary"):
                            try:
                                conn = get_db()
                                acc = conn.execute("SELECT id FROM accounts WHERE account_number=?", (acc_num,)).fetchone()
                                if acc:
                                    acc_id = acc[0]
                                    conn.execute("DELETE FROM transactions WHERE account_id=?", (acc_id,))
                                    conn.execute("DELETE FROM accounts WHERE account_number=?", (acc_num,))
                                    conn.commit()
                                    conn.close()
                                    st.success("✅ Account deleted!")
                                    st.rerun()
                                else:
                                    st.error("❌ Account not found!")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
        else:
            st.info("No SB accounts found")
    
    with tab3:
        st.markdown("### 📋 Account Statement")
        cust_id, cust_name, acc_id, acc_number, balance = customer_selector("👤 Select Customer for Statement", "stmt_customer")
        
        if cust_id and acc_id:
            col1, col2 = st.columns(2)
            with col1:
                from_date = st.date_input("📅 From Date", get_ist_today() - timedelta(days=30))
            with col2:
                to_date = st.date_input("📅 To Date", get_ist_today())
            
            if st.button("📊 Generate Statement", use_container_width=True):
                conn = get_db()
                transactions = conn.execute("""
                    SELECT transaction_id, transaction_type, amount,
                           balance_after, description, reference_type,
                           created_at
                    FROM transactions
                    WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ?
                    ORDER BY created_at DESC
                """, (acc_id, from_date, to_date)).fetchall()
                conn.close()
                
                if transactions:
                    data = []
                    for txn in transactions:
                        try:
                            txn_date = format_ist_datetime(txn[6])
                        except:
                            txn_date = str(txn[6]) if txn[6] else 'N/A'
                        amount = txn[2]
                        amount_str = f"- ₹ {amount:,.2f}" if txn[1] == 'DEBIT' else f"+ ₹ {amount:,.2f}"
                        data.append({
                            'Txn ID': txn[0],
                            'Type': '💳 Debit' if txn[1] == 'DEBIT' else '💰 Credit',
                            'Amount': amount_str,
                            'Balance': f"₹ {txn[3]:,.2f}",
                            'Description': txn[4] if txn[4] else 'N/A',
                            'Mode': txn[5] if txn[5] else 'N/A',
                            'Date': txn_date
                        })
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)
                    
                    total_credit = sum(txn[2] for txn in transactions if txn[1] == 'CREDIT')
                    total_debit = sum(txn[2] for txn in transactions if txn[1] == 'DEBIT')
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("💰 Total Credits", f"₹ {total_credit:,.2f}")
                    col2.metric("💳 Total Debits", f"₹ {total_debit:,.2f}")
                    col3.metric("📊 Net Change", f"₹ {(total_credit - total_debit):,.2f}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        download_data = []
                        for txn in transactions:
                            download_data.append({
                                'Transaction ID': txn[0],
                                'Type': txn[1],
                                'Amount': txn[2],
                                'Balance': txn[3],
                                'Description': txn[4] if txn[4] else '',
                                'Mode': txn[5] if txn[5] else '',
                                'Date': txn[6] if txn[6] else ''
                            })
                        df_download = pd.DataFrame(download_data)
                        st.download_button(
                            "📥 Download CSV",
                            df_download.to_csv(index=False),
                            f"statement_{acc_number}_{from_date.strftime('%d%m%Y')}_{to_date.strftime('%d%m%Y')}.csv",
                            "text/csv"
                        )
                    with col2:
                        if st.button("📄 Print Statement", use_container_width=True):
                            content = [
                                f"📋 ACCOUNT STATEMENT - {acc_number}",
                                "=" * 50,
                                f"Customer: {cust_name}",
                                f"Period: {from_date.strftime('%d-%m-%Y')} to {to_date.strftime('%d-%m-%Y')}",
                                f"Generated on: {get_ist_now().strftime('%d-%m-%Y %I:%M %p')}",
                                "",
                                "TRANSACTION DETAILS:",
                                "-" * 50
                            ]
                            for txn in transactions:
                                content.append(f"{txn[0]} | {txn[1]} | ₹ {txn[2]:,.2f} | ₹ {txn[3]:,.2f} | {txn[4]} | {txn[6]}")
                            content.append("")
                            content.append(f"Opening Balance: ₹ {balance:,.2f}")
                            content.append(f"Closing Balance: ₹ {transactions[0][3] if transactions else balance:,.2f}")
                            pdf_file = create_pdf(f"Account Statement - {acc_number}", content, f"statement_{acc_number}")
                            if pdf_file:
                                create_download_button(pdf_file, f"statement_{acc_number}", "📥 Download PDF Report")
                else:
                    st.info("No transactions in this period")
    c.close()

# ==================== INTEREST CALCULATION ====================
def interest_calculation():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    st.markdown("### 📊 Interest Calculation")
    
    c = get_db()
    
    # Get current rate and allow setting it here
    current_rate = get_current_sb_interest_rate()
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📈 Current SB Interest Rate: **{current_rate}%** per annum")
        new_rate = st.number_input(
            "✏️ Update Interest Rate (%)",
            min_value=0.0,
            max_value=10.0,
            value=current_rate,
            step=0.25,
            help="Change the interest rate for future calculations"
        )
        if new_rate != current_rate:
            if st.button("💾 Update Rate", use_container_width=True):
                update_sb_interest_rate(new_rate)
                st.success(f"✅ Interest Rate updated to {new_rate}%!")
                st.rerun()
    with col2:
        from_date = st.date_input("📅 From Date", get_ist_today().replace(day=1))
        to_date = st.date_input("📅 To Date", get_ist_today())
    
    cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
        "👤 Calculate for specific customer (Optional)",
        "int_customer"
    )
    
    use_custom_rate = st.checkbox("🔧 Use custom rate for this calculation")
    custom_rate = None
    if use_custom_rate:
        custom_rate = st.number_input("📊 Custom Rate (%)", min_value=0.0, max_value=10.0, value=current_rate, step=0.25)
    
    with st.expander("🗑️ Delete Interest Records"):
        st.warning("⚠️ This will delete ALL interest calculation records.")
        if st.button("🗑️ Delete All Interest Records", use_container_width=True, type="secondary"):
            confirm = st.checkbox("☑️ Confirm delete ALL?", key="del_all_int_confirm")
            if confirm:
                try:
                    conn = get_db()
                    conn.execute("UPDATE accounts SET total_interest_earned = 0 WHERE account_type='SB'")
                    conn.execute("DELETE FROM interest_calculations")
                    conn.commit()
                    conn.close()
                    st.success("✅ All interest records deleted!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    if st.button("📊 Calculate & Post Interest", use_container_width=True, type="primary"):
        conn = get_db()
        try:
            rate_to_use = custom_rate if use_custom_rate else current_rate
            
            if cust_id and acc_id:
                accounts = conn.execute("""
                    SELECT a.id, a.account_number, c.first_name||' '||c.last_name as customer,
                           a.balance, a.interest_rate, c.id
                    FROM accounts a
                    JOIN customers c ON a.customer_id = c.id
                    WHERE a.account_type='SB' AND a.status='ACTIVE' AND a.customer_id=?
                """, (cust_id,)).fetchall()
            else:
                accounts = conn.execute("""
                    SELECT a.id, a.account_number, c.first_name||' '||c.last_name as customer,
                           a.balance, a.interest_rate, c.id
                    FROM accounts a
                    JOIN customers c ON a.customer_id = c.id
                    WHERE a.account_type='SB' AND a.status='ACTIVE'
                """).fetchall()
            
            if not accounts:
                st.warning("No SB accounts found")
                conn.close()
                return
            
            total_interest = 0
            interest_details = []
            
            for acc in accounts:
                balance = acc[3]
                days = (to_date - from_date).days + 1
                
                if balance > 0 and days > 0:
                    interest = calculate_sb_interest(balance, rate_to_use, days)
                    
                    if interest > 0:
                        conn.execute("""
                            UPDATE accounts 
                            SET total_interest_earned = COALESCE(total_interest_earned, 0) + ?
                            WHERE id=?
                        """, (interest, acc[0]))
                        
                        conn.execute("""
                            INSERT INTO interest_calculations (
                                account_id, calculation_date,
                                principal_amount, interest_rate,
                                interest_earned, days_calculated,
                                customer_id
                            ) VALUES (?,DATE('now'),?,?,?,?,?)
                        """, (acc[0], balance, rate_to_use, interest, days, acc[5]))
                        
                        total_interest += interest
                        interest_details.append({
                            'Account': acc[1],
                            'Customer': acc[2],
                            'Balance': balance,
                            'Rate': rate_to_use,
                            'Days': days,
                            'Interest': interest
                        })
            
            conn.commit()
            conn.close()
            
            if interest_details:
                df = pd.DataFrame(interest_details)
                st.dataframe(
                    df.style.format({
                        'Balance': '₹ {:,.2f}',
                        'Interest': '₹ {:,.2f}',
                        'Rate': '{:.2f}%'
                    }),
                    use_container_width=True
                )
                st.success(f"✅ Interest Posted: ₹ {total_interest:,.2f}")
                st.balloons()
            else:
                st.info("No interest calculated")
        except Exception as e:
            conn.rollback()
            conn.close()
            st.error(f"❌ Error: {str(e)}")
    
    st.markdown("### 📊 Recent Interest Calculations")
    recent = c.execute("""
        SELECT ic.id, ic.calculation_date, c.first_name||' '||c.last_name as customer,
               ic.principal_amount, ic.interest_rate, ic.interest_earned,
               ic.days_calculated
        FROM interest_calculations ic
        JOIN customers c ON ic.customer_id = c.id
        ORDER BY ic.created_at DESC LIMIT 20
    """).fetchall()
    c.close()
    
    if recent:
        data = []
        for item in recent:
            data.append({
                'ID': item[0],
                'Date': item[1] if item[1] else 'N/A',
                'Customer': item[2],
                'Principal': f"₹ {item[3]:,.2f}",
                'Rate': f"{item[4]}%",
                'Interest': f"₹ {item[5]:,.2f}",
                'Days': item[6] if item[6] else 0
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📄 Print Report", use_container_width=True):
                content = ["📊 INTEREST CALCULATION REPORT", "=" * 50]
                content.append(f"Generated on: {get_ist_now().strftime('%d-%m-%Y %I:%M %p')}")
                content.append(f"Total Records: {len(recent)}")
                content.append("")
                for item in recent:
                    content.append(f"Customer: {item[2]} | Interest: ₹ {item[5]:,.2f} | Rate: {item[4]}% | Days: {item[6]}")
                pdf_file = create_pdf("Interest Report", content, "interest_report")
                if pdf_file:
                    create_download_button(pdf_file, "interest_report", "📥 Download PDF Report")
        
        with col2:
            with st.expander("🗑️ Delete Individual Record"):
                int_id = st.text_input("Enter Interest Calculation ID to delete:")
                if int_id:
                    confirm = st.checkbox("☑️ Confirm delete?", key="del_int_confirm")
                    if confirm and st.button("🗑️ Delete", use_container_width=True, type="secondary"):
                        try:
                            conn = get_db()
                            interest_rec = conn.execute("SELECT account_id, interest_earned FROM interest_calculations WHERE id=?", (int_id,)).fetchone()
                            if interest_rec:
                                conn.execute("""
                                    UPDATE accounts 
                                    SET total_interest_earned = total_interest_earned - ? 
                                    WHERE id = ?
                                """, (interest_rec[1], interest_rec[0]))
                                conn.execute("DELETE FROM interest_calculations WHERE id=?", (int_id,))
                                conn.commit()
                                conn.close()
                                st.success("✅ Interest record deleted and account adjusted!")
                                st.rerun()
                            else:
                                st.error("❌ Record not found!")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")

# ==================== PROFIT & LOSS ====================
def profit_loss():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    st.markdown("### 📈 Profit & Loss Statement")
    
    col1, col2 = st.columns(2)
    with col1:
        from_date = st.date_input("📅 From Date", get_ist_today().replace(day=1))
    with col2:
        to_date = st.date_input("📅 To Date", get_ist_today())
    
    if st.button("🔄 Generate P&L", use_container_width=True, type="primary"):
        # === INCOME ===
        income_data = []
        total_income = 0
        
        # Primary Revenue
        primary_income = c.execute("""
            SELECT 
                income_type,
                COALESCE(SUM(amount), 0) as total
            FROM income
            WHERE income_type IN ('Loan Interest Income', 'Investment Income')
            AND DATE(date) BETWEEN ? AND ?
            GROUP BY income_type
            ORDER BY total DESC
        """, (from_date, to_date)).fetchall()
        
        for item in primary_income:
            if item[1] > 0:
                income_data.append({
                    'Name': item[0],
                    'Amount': item[1],
                    'Category': 'Primary Revenue'
                })
                total_income += item[1]
        
        # Service Income
        service_income = c.execute("""
            SELECT 
                income_type,
                COALESCE(SUM(amount), 0) as total
            FROM income
            WHERE income_type IN ('Processing Fees', 'Service Charges', 'Commission Income', 'Transaction Fees')
            AND DATE(date) BETWEEN ? AND ?
            GROUP BY income_type
            ORDER BY total DESC
        """, (from_date, to_date)).fetchall()
        
        for item in service_income:
            if item[1] > 0:
                income_data.append({
                    'Name': item[0],
                    'Amount': item[1],
                    'Category': 'Service Income'
                })
                total_income += item[1]
        
        # Other Income
        other_income = c.execute("""
            SELECT 
                income_type,
                COALESCE(SUM(amount), 0) as total
            FROM income
            WHERE income_type = 'Miscellaneous Income'
            AND DATE(date) BETWEEN ? AND ?
            GROUP BY income_type
            ORDER BY total DESC
        """, (from_date, to_date)).fetchall()
        
        for item in other_income:
            if item[1] > 0:
                income_data.append({
                    'Name': item[0],
                    'Amount': item[1],
                    'Category': 'Other Income'
                })
                total_income += item[1]
        
        # === EXPENSES ===
        expense_data = []
        total_expense = 0
        
        # Cost of Funds
        cost_of_funds = c.execute("""
            SELECT 
                expense_type,
                COALESCE(SUM(amount), 0) as total
            FROM expenses
            WHERE expense_type IN ('SB Interest Paid', 'FD Interest Paid', 'RD Interest Paid', 'Interest on Borrowings')
            AND DATE(date) BETWEEN ? AND ?
            GROUP BY expense_type
            ORDER BY total DESC
        """, (from_date, to_date)).fetchall()
        
        for item in cost_of_funds:
            if item[1] > 0:
                expense_data.append({
                    'Name': item[0],
                    'Amount': item[1],
                    'Category': 'Cost of Funds'
                })
                total_expense += item[1]
        
        # Operating Expenses
        operating_exp = c.execute("""
            SELECT 
                expense_type,
                COALESCE(SUM(amount), 0) as total
            FROM expenses
            WHERE expense_type IN ('Salaries & Benefits', 'Rent & Utilities', 'Electricity Charges', 
                                   'Water Charges', 'Internet & Telephone', 'IT Infrastructure')
            AND DATE(date) BETWEEN ? AND ?
            GROUP BY expense_type
            ORDER BY total DESC
        """, (from_date, to_date)).fetchall()
        
        for item in operating_exp:
            if item[1] > 0:
                expense_data.append({
                    'Name': item[0],
                    'Amount': item[1],
                    'Category': 'Operating Expenses'
                })
                total_expense += item[1]
        
        # Administrative Expenses
        admin_exp = c.execute("""
            SELECT 
                expense_type,
                COALESCE(SUM(amount), 0) as total
            FROM expenses
            WHERE expense_type IN ('Printing & Stationary', 'Postage & Courier', 'Office Supplies',
                                   'Conveyance', 'Travel Expenses', 'Legal & Audit Fees')
            AND DATE(date) BETWEEN ? AND ?
            GROUP BY expense_type
            ORDER BY total DESC
        """, (from_date, to_date)).fetchall()
        
        for item in admin_exp:
            if item[1] > 0:
                expense_data.append({
                    'Name': item[0],
                    'Amount': item[1],
                    'Category': 'Administrative Expenses'
                })
                total_expense += item[1]
        
        # Other Expenses
        other_exp = c.execute("""
            SELECT 
                expense_type,
                COALESCE(SUM(amount), 0) as total
            FROM expenses
            WHERE expense_type IN ('Bank Charges', 'Insurance', 'Maintenance', 
                                   'Marketing Expenses', 'Depreciation', 
                                   'Provision for NPAs', 'Miscellaneous Expenses')
            AND DATE(date) BETWEEN ? AND ?
            GROUP BY expense_type
            ORDER BY total DESC
        """, (from_date, to_date)).fetchall()
        
        for item in other_exp:
            if item[1] > 0:
                expense_data.append({
                    'Name': item[0],
                    'Amount': item[1],
                    'Category': 'Other Expenses'
                })
                total_expense += item[1]
        
        # Add Interest Paid from Interest Calculations
        sb_int_paid = c.execute("""
            SELECT 
                'SB Interest Paid',
                COALESCE(SUM(interest_earned), 0) as total
            FROM interest_calculations
            WHERE DATE(calculation_date) BETWEEN ? AND ?
        """, (from_date, to_date)).fetchone()
        
        if sb_int_paid and sb_int_paid[1] > 0:
            # Check if already added
            already_added = False
            for item in expense_data:
                if item['Name'] == 'SB Interest Paid':
                    already_added = True
                    break
            if not already_added:
                expense_data.append({
                    'Name': 'SB Interest Paid',
                    'Amount': sb_int_paid[1],
                    'Category': 'Cost of Funds'
                })
                total_expense += sb_int_paid[1]
        
        # Calculate net profit/loss
        net_profit = total_income - total_expense
        
        # === DISPLAY ===
        st.markdown("### 📊 Profit & Loss Summary")
        st.markdown(f"**Period:** {from_date.strftime('%d-%m-%Y')} to {to_date.strftime('%d-%m-%Y')}")
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 💰 INCOME")
            st.markdown("---")
            if income_data:
                # Group by category
                income_by_cat = {}
                for item in income_data:
                    cat = item['Category']
                    if cat not in income_by_cat:
                        income_by_cat[cat] = []
                    income_by_cat[cat].append(item)
                
                for category, items in income_by_cat.items():
                    st.markdown(f"**{category}**")
                    for item in items:
                        st.markdown(f"• {item['Name']}: **₹ {item['Amount']:,.2f}**")
                    total_cat = sum(item['Amount'] for item in items)
                    st.markdown(f"*Total {category}: ₹ {total_cat:,.2f}*")
                    st.markdown("---")
                
                st.markdown(f"### **Total Income: ₹ {total_income:,.2f}**")
            else:
                st.info("No income in this period")
        
        with col2:
            st.markdown("#### 💸 EXPENSES")
            st.markdown("---")
            if expense_data:
                expense_by_cat = {}
                for item in expense_data:
                    cat = item['Category']
                    if cat not in expense_by_cat:
                        expense_by_cat[cat] = []
                    expense_by_cat[cat].append(item)
                
                for category, items in expense_by_cat.items():
                    st.markdown(f"**{category}**")
                    for item in items:
                        st.markdown(f"• {item['Name']}: **₹ {item['Amount']:,.2f}**")
                    total_cat = sum(item['Amount'] for item in items)
                    st.markdown(f"*Total {category}: ₹ {total_cat:,.2f}*")
                    st.markdown("---")
                
                st.markdown(f"### **Total Expenses: ₹ {total_expense:,.2f}**")
            else:
                st.info("No expenses in this period")
        
        st.markdown("---")
        
        if net_profit >= 0:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #e8f5e9, #c8e6c9); padding: 2rem; border-radius: 12px; text-align: center;">
                <h2 style="color: #1b5e20; margin: 0;">🎉 Net Profit: ₹ {net_profit:,.2f}</h2>
                <p style="color: #1b5e20; margin: 10px 0 0 0; font-size: 1rem;">
                    Profit Margin: {((net_profit / total_income) * 100) if total_income > 0 else 0:.1f}%
                </p>
            </div>
            """, unsafe_allow_html=True)
            st.balloons()
        else:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #fce4ec, #f8d7da); padding: 2rem; border-radius: 12px; text-align: center;">
                <h2 style="color: #721c24; margin: 0;">📉 Net Loss: ₹ {abs(net_profit):,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        # === INTEREST SUMMARY ===
        st.markdown("### 📊 Interest Summary")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 📈 Interest Received (Income)")
            interest_received = sum(item['Amount'] for item in income_data if 'Interest' in item['Name'])
            if interest_received > 0:
                st.metric("Total Interest Received", f"₹ {interest_received:,.2f}")
                for item in income_data:
                    if 'Interest' in item['Name']:
                        st.write(f"• {item['Name']}: ₹ {item['Amount']:,.2f}")
            else:
                st.info("No interest received")
        
        with col2:
            st.markdown("#### 📉 Interest Paid (Expenses)")
            interest_paid = sum(item['Amount'] for item in expense_data if 'Interest' in item['Name'])
            if interest_paid > 0:
                st.metric("Total Interest Paid", f"₹ {interest_paid:,.2f}")
                for item in expense_data:
                    if 'Interest' in item['Name']:
                        st.write(f"• {item['Name']}: ₹ {item['Amount']:,.2f}")
            else:
                st.info("No interest paid")
        
        net_interest = interest_received - interest_paid
        if net_interest >= 0:
            st.success(f"✅ **Net Interest Income: ₹ {net_interest:,.2f}**")
        else:
            st.error(f"❌ **Net Interest Expense: ₹ {abs(net_interest):,.2f}**")
        
        # === DOWNLOAD ===
        col1, col2 = st.columns(2)
        with col1:
            csv_data = [['Type', 'Category', 'Name', 'Amount']]
            for item in income_data:
                csv_data.append(['Income', item['Category'], item['Name'], item['Amount']])
            for item in expense_data:
                csv_data.append(['Expense', item['Category'], item['Name'], item['Amount']])
            csv_data.append(['Net', '', 'Net Profit/Loss', net_profit])
            df_csv = pd.DataFrame(csv_data[1:], columns=csv_data[0])
            st.download_button(
                "📥 Download CSV",
                df_csv.to_csv(index=False),
                f"profit_loss_{from_date.strftime('%d%m%Y')}_{to_date.strftime('%d%m%Y')}.csv",
                "text/csv"
            )
        
        with col2:
            if st.button("📄 Print/PDF P&L", use_container_width=True):
                content = [
                    "📈 PROFIT & LOSS STATEMENT",
                    "=" * 50,
                    f"Period: {from_date.strftime('%d-%m-%Y')} to {to_date.strftime('%d-%m-%Y')}",
                    f"Generated on: {get_ist_now().strftime('%d-%m-%Y %I:%M %p')}",
                    "",
                    "INCOME:",
                    "-" * 30
                ]
                for item in income_data:
                    content.append(f"{item['Name']} ({item['Category']}): ₹ {item['Amount']:,.2f}")
                content.append(f"Total Income: ₹ {total_income:,.2f}")
                content.append("")
                content.append("EXPENSES:")
                content.append("-" * 30)
                for item in expense_data:
                    content.append(f"{item['Name']} ({item['Category']}): ₹ {item['Amount']:,.2f}")
                content.append(f"Total Expenses: ₹ {total_expense:,.2f}")
                content.append("")
                if net_profit >= 0:
                    content.append(f"NET PROFIT: ₹ {net_profit:,.2f}")
                    content.append(f"Profit Margin: {((net_profit/total_income*100) if total_income > 0 else 0):.1f}%")
                else:
                    content.append(f"NET LOSS: ₹ {abs(net_profit):,.2f}")
                pdf_file = create_pdf("Profit & Loss Statement", content, "profit_loss")
                if pdf_file:
                    create_download_button(pdf_file, "profit_loss", "📥 Download PDF Report")
    
    c.close()

# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    main()
               
