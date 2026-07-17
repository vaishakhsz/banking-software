# banking_system.py - Complete Banking System with Streamlit
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
from decimal import Decimal
import uuid
import os
from PIL import Image
import io
import hashlib
import base64
import plotly.express as px
import plotly.graph_objects as go

# Fix: Try importing fpdf with the correct package name
try:
    from fpdf import FPDF
except ImportError:
    try:
        from fpdf2 import FPDF
    except ImportError:
        st.error("Please install fpdf2: pip install fpdf2")
        FPDF = None

# ==================== DATABASE SETUP ====================

def init_database():
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
    
    # Customers table with KYC
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (id)
    )''')
    
    # Fixed Deposits
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (account_id) REFERENCES accounts (id)
    )''')
    
    # Recurring Deposits
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (account_id) REFERENCES accounts (id)
    )''')
    
    # Transactions
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
    
    # Journal Vouchers
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users (id)
    )''')
    
    # Journal Entries
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
    
    # Interest Calculation Log
    c.execute('''CREATE TABLE IF NOT EXISTS interest_calculations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL,
        calculation_date DATE NOT NULL,
        principal_amount DECIMAL(15,2) NOT NULL,
        interest_rate DECIMAL(5,2) NOT NULL,
        interest_earned DECIMAL(15,2) NOT NULL,
        days_calculated INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (account_id) REFERENCES accounts (id)
    )''')
    
    conn.commit()
    conn.close()

# ==================== UTILITY FUNCTIONS ====================

def get_db():
    return sqlite3.connect('banking_system.db')

def generate_id(prefix):
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4]}"

def generate_account_number(account_type):
    prefix = {'SB': '100', 'FD': '200', 'RD': '300'}
    return f"{prefix.get(account_type, '100')}{datetime.now().strftime('%y%m%d')}{str(uuid.uuid4().int)[:6]}"

def generate_voucher_number(v_type):
    prefix = {'PAYMENT': 'PMT', 'RECEIPT': 'RCT', 'JOURNAL': 'JNL'}
    return f"{prefix.get(v_type, 'JNL')}{datetime.now().strftime('%Y%m%d%H%M')}{str(uuid.uuid4().int)[:4]}"

def calculate_fd_maturity(principal, rate, months):
    # Compound interest quarterly
    r = rate / 400  # Quarterly rate
    n = months / 3  # Number of quarters
    maturity = principal * (1 + r) ** n
    return round(maturity, 2)

def calculate_rd_maturity(monthly_amount, rate, months):
    # RD maturity calculation
    r = rate / 400  # Quarterly rate
    n = months / 3  # Number of quarters
    maturity = monthly_amount * (((1 + r) ** n - 1) / (1 - (1 + r) ** (-1/3)))
    return round(maturity, 2)

def calculate_sb_interest(balance, rate, days):
    """Calculate SB interest using daily balance method"""
    if balance <= 0:
        return 0
    # Simple interest calculation: (Principal * Rate * Time) / (100 * 365)
    interest = (balance * rate * days) / (100 * 365)
    return round(interest, 2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ==================== AUTHENTICATION ====================

def login_user(username, password):
    conn = get_db()
    c = conn.cursor()
    hashed_pw = hash_password(password)
    c.execute("SELECT * FROM users WHERE username=? AND password=? AND is_active=1", 
              (username, hashed_pw))
    user = c.fetchone()
    conn.close()
    return user

def create_default_admin():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ('admin', hash_password('admin123'), 'admin'))
        conn.commit()
    conn.close()

# ==================== PDF GENERATION ====================

class BankPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'BANKING SYSTEM', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, 'Financial Reports', 0, 1, 'C')
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

def generate_report_pdf(report_type, data, filename):
    if FPDF is None:
        return None
    
    pdf = BankPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    if report_type == 'trial_balance':
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'TRIAL BALANCE', 0, 1, 'C')
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 5, f'As on: {data["date"]}', 0, 1, 'C')
        pdf.ln(10)
        
        # Table header
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(10, 7, 'S.No', 1)
        pdf.cell(90, 7, 'Account Head', 1)
        pdf.cell(45, 7, 'Debit (Rs.)', 1, 0, 'R')
        pdf.cell(45, 7, 'Credit (Rs.)', 1, 1, 'R')
        
        # Table data
        pdf.set_font('Arial', '', 9)
        total_debit = 0
        total_credit = 0
        for i, entry in enumerate(data['entries'], 1):
            pdf.cell(10, 6, str(i), 1)
            pdf.cell(90, 6, entry['account_head'], 1)
            pdf.cell(45, 6, f"{entry['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(45, 6, f"{entry['credit']:,.2f}", 1, 1, 'R')
            total_debit += entry['debit']
            total_credit += entry['credit']
        
        # Totals
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(100, 7, 'TOTAL', 1)
        pdf.cell(45, 7, f"{total_debit:,.2f}", 1, 0, 'R')
        pdf.cell(45, 7, f"{total_credit:,.2f}", 1, 1, 'R')
    
    pdf.output(filename)
    return filename

# ==================== SESSION STATE ====================

def init_session_state():
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = 'login'

# ==================== STREAMLIT UI ====================

def main():
    st.set_page_config(
        page_title="Complete Banking System",
        page_icon="🏦",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    init_database()
    create_default_admin()
    init_session_state()
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
    }
    .card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-card h3 {
        font-size: 2rem;
        margin: 0;
    }
    .metric-card p {
        margin: 0.5rem 0 0 0;
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .customer-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .stButton > button {
        width: 100%;
        border-radius: 5px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
    }
    .info-box {
        background-color: #f0f8ff;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    if st.session_state.user is None:
        show_login_page()
    else:
        show_main_app()

def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<h1 class="main-header">🏦 Banking System</h1>', unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("🔐 Login")
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🔑 Login", use_container_width=True):
                    user = login_user(username, password)
                    if user:
                        st.session_state.user = {
                            'id': user[0],
                            'username': user[1],
                            'role': user[3]
                        }
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials!")
            
            with col_b:
                if st.button("📝 Register", use_container_width=True):
                    st.session_state.page = 'register'
                    st.rerun()
            
            st.info("Default admin credentials: **admin** / **admin123**")
            st.markdown('</div>', unsafe_allow_html=True)

def show_main_app():
    with st.sidebar:
        st.markdown(f"## 👤 {st.session_state.user['username']}")
        role_badge = {
            'admin': '<span style="background-color: #10b981; color: white; padding: 5px 10px; border-radius: 20px;">ADMIN</span>',
            'staff': '<span style="background-color: #f59e0b; color: white; padding: 5px 10px; border-radius: 20px;">STAFF</span>',
            'customer': '<span style="background-color: #ef4444; color: white; padding: 5px 10px; border-radius: 20px;">CUSTOMER</span>'
        }
        st.markdown(role_badge.get(st.session_state.user['role'], 'USER'), unsafe_allow_html=True)
        st.divider()
        
        # Menu based on role
        if st.session_state.user['role'] in ['admin', 'staff']:
            menu_options = {
                'dashboard': '📊 Dashboard',
                'customer_management': '👥 Customer Management',
                'kyc_verification': '🔍 KYC Verification',
                'sb_accounts': '💰 SB Accounts',
                'fixed_deposits': '💎 Fixed Deposits',
                'recurring_deposits': '🔄 Recurring Deposits',
                'transactions': '💳 All Transactions',
                'journal_vouchers': '📝 Journal Vouchers',
                'interest_calculation': '📈 Interest Calculation',
                'trial_balance': '⚖️ Trial Balance',
                'balance_sheet': '📊 Balance Sheet',
                'profit_loss': '💵 Profit & Loss',
                'reports': '📋 Reports'
            }
        else:
            menu_options = {
                'dashboard': '📊 Dashboard',
                'my_accounts': '💰 My Accounts',
                'my_transactions': '💳 My Transactions',
                'my_details': '👤 My Details'
            }
        
        for key, label in menu_options.items():
            if st.sidebar.button(label, key=key, use_container_width=True):
                st.session_state.page = key
                st.rerun()
        
        st.divider()
        if st.sidebar.button("🚪 Logout", use_container_width=True, type="primary"):
            st.session_state.user = None
            st.session_state.page = 'login'
            st.rerun()
    
    # Main content area
    page = st.session_state.get('page', 'dashboard')
    
    if page == 'dashboard':
        show_dashboard()
    elif page == 'customer_management':
        show_customer_management()
    elif page == 'kyc_verification':
        show_kyc_verification()
    elif page == 'sb_accounts' or page == 'my_accounts':
        show_sb_accounts()
    elif page == 'fixed_deposits':
        show_fixed_deposits()
    elif page == 'recurring_deposits':
        show_recurring_deposits()
    elif page == 'transactions' or page == 'my_transactions':
        show_transactions()
    elif page == 'journal_vouchers':
        show_journal_vouchers()
    elif page == 'interest_calculation':
        show_interest_calculation()
    elif page == 'trial_balance':
        show_trial_balance()
    elif page == 'balance_sheet':
        show_balance_sheet()
    elif page == 'profit_loss':
        show_profit_loss()
    elif page == 'reports':
        show_reports()
    elif page == 'my_details':
        show_my_details()

def show_dashboard():
    st.markdown('<h1 class="main-header">📊 Dashboard</h1>', unsafe_allow_html=True)
    
    conn = get_db()
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        st.markdown(f'''
        <div class="metric-card">
            <h3>{customers}</h3>
            <p>Total Customers</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        accounts = conn.execute("SELECT COUNT(*) FROM accounts WHERE status='ACTIVE'").fetchone()[0]
        st.markdown(f'''
        <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <h3>{accounts}</h3>
            <p>Active Accounts</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col3:
        total_balance = conn.execute("SELECT COALESCE(SUM(balance), 0) FROM accounts WHERE status='ACTIVE'").fetchone()[0]
        st.markdown(f'''
        <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <h3>₹{total_balance:,.2f}</h3>
            <p>Total Deposits</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col4:
        pending_kyc = conn.execute("SELECT COUNT(*) FROM customers WHERE kyc_status='PENDING'").fetchone()[0]
        st.markdown(f'''
        <div class="metric-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
            <h3>{pending_kyc}</h3>
            <p>Pending KYC</p>
        </div>
        ''', unsafe_allow_html=True)
    
    # Recent Transactions
    st.subheader("📌 Recent Transactions")
    transactions = conn.execute("""
        SELECT t.transaction_id, c.first_name || ' ' || c.last_name as customer_name,
               t.transaction_type, t.amount, t.description, t.created_at
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        JOIN customers c ON a.customer_id = c.id
        ORDER BY t.created_at DESC
        LIMIT 10
    """).fetchall()
    
    if transactions:
        df = pd.DataFrame(transactions, columns=['Transaction ID', 'Customer', 'Type', 'Amount', 'Description', 'Date'])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No transactions yet")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Account Distribution")
        account_types = conn.execute("""
            SELECT account_type, COUNT(*) as count 
            FROM accounts 
            WHERE status='ACTIVE' 
            GROUP BY account_type
        """).fetchall()
        
        if account_types:
            df = pd.DataFrame(account_types, columns=['Type', 'Count'])
            fig = px.pie(df, values='Count', names='Type', title='Account Types')
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Monthly Transactions")
        monthly = conn.execute("""
            SELECT strftime('%Y-%m', created_at) as month, 
                   COUNT(*) as count,
                   SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE 0 END) as credits,
                   SUM(CASE WHEN transaction_type='DEBIT' THEN amount ELSE 0 END) as debits
            FROM transactions
            GROUP BY month
            ORDER BY month DESC
            LIMIT 6
        """).fetchall()
        
        if monthly:
            df = pd.DataFrame(monthly, columns=['Month', 'Count', 'Credits', 'Debits'])
            fig = go.Figure()
            fig.add_trace(go.Bar(name='Credits', x=df['Month'], y=df['Credits']))
            fig.add_trace(go.Bar(name='Debits', x=df['Month'], y=df['Debits']))
            fig.update_layout(barmode='group', title='Monthly Credit/Debit Analysis')
            st.plotly_chart(fig, use_container_width=True)
    
    conn.close()

def show_customer_management():
    st.markdown('<h1 class="main-header">👥 Customer Management</h1>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Register Customer", "👥 View Customers", "🔍 Search Customer", "📊 Customer Analytics"])
    
    with tab1:
        st.subheader("New Customer Registration")
        
        with st.form("customer_registration"):
            col1, col2 = st.columns(2)
            
            with col1:
                first_name = st.text_input("First Name *")
                last_name = st.text_input("Last Name *")
                date_of_birth = st.date_input("Date of Birth *", min_value=date(1900,1,1), max_value=date.today())
                gender = st.selectbox("Gender", ["Male", "Female", "Other"])
                email = st.text_input("Email *")
                phone = st.text_input("Phone Number *")
            
            with col2:
                pan_number = st.text_input("PAN Number * (e.g., ABCDE1234F)")
                aadhar_number = st.text_input("Aadhar Number * (12 digits)")
                address = st.text_area("Address")
                city = st.text_input("City")
                state = st.text_input("State")
                pincode = st.text_input("PIN Code")
            
            st.subheader("📎 KYC Documents Upload")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                pan_document = st.file_uploader("PAN Card *", type=['jpg', 'jpeg', 'png', 'pdf'])
            with col2:
                aadhar_document = st.file_uploader("Aadhar Card *", type=['jpg', 'jpeg', 'png', 'pdf'])
            with col3:
                photo = st.file_uploader("Passport Size Photo", type=['jpg', 'jpeg', 'png'])
            
            signature = st.file_uploader("Signature", type=['jpg', 'jpeg', 'png'])
            
            submitted = st.form_submit_button("📝 Register Customer", use_container_width=True)
            
            if submitted:
                if not all([first_name, last_name, email, phone, pan_number, aadhar_number]):
                    st.error("Please fill all required fields marked with *")
                elif not pan_document or not aadhar_document:
                    st.error("Please upload PAN and Aadhar documents")
                else:
                    try:
                        conn = get_db()
                        customer_id = generate_id('CUST')
                        
                        # Read file data
                        pan_data = pan_document.read()
                        aadhar_data = aadhar_document.read()
                        photo_data = photo.read() if photo else None
                        signature_data = signature.read() if signature else None
                        
                        conn.execute("""
                            INSERT INTO customers (customer_id, first_name, last_name, date_of_birth, 
                            gender, email, phone, address, city, state, pincode, pan_number, 
                            aadhar_number, pan_document, aadhar_document, photo, signature)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (customer_id, first_name, last_name, date_of_birth, gender, email, 
                              phone, address, city, state, pincode, pan_number, aadhar_number,
                              pan_data, aadhar_data, photo_data, signature_data))
                        
                        conn.commit()
                        conn.close()
                        
                        st.success(f"✅ Customer registered successfully!")
                        st.info(f"Customer ID: **{customer_id}**")
                        st.warning("KYC verification is pending. Admin will verify the documents.")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    with tab2:
        st.subheader("Customer List & Details")
        conn = get_db()
        customers = conn.execute("""
            SELECT c.id, c.customer_id, c.first_name, c.last_name, c.email, c.phone, 
                   c.city, c.state, c.pan_number, c.aadhar_number, c.kyc_status, 
                   c.created_at, c.date_of_birth, c.gender, c.address, c.pincode
            FROM customers c
            ORDER BY c.created_at DESC
        """).fetchall()
        
        if customers:
            for cust in customers:
                with st.expander(f"👤 {cust[2]} {cust[3]} - {cust[1]} ({cust[10]})", expanded=False):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.markdown("### 📋 Personal Information")
                        st.write(f"**Customer ID:** {cust[1]}")
                        st.write(f"**Full Name:** {cust[2]} {cust[3]}")
                        st.write(f"**Date of Birth:** {cust[12]}")
                        st.write(f"**Age:** {calculate_age(cust[12])} years")
                        st.write(f"**Gender:** {cust[13]}")
                        st.write(f"**Email:** {cust[4]}")
                        st.write(f"**Phone:** {cust[5]}")
                    
                    with col2:
                        st.markdown("### 🏠 Address & Documents")
                        st.write(f"**Address:** {cust[14]}")
                        st.write(f"**City:** {cust[6]}")
                        st.write(f"**State:** {cust[7]}")
                        st.write(f"**PIN Code:** {cust[15]}")
                        st.write(f"**PAN Number:** {cust[8]}")
                        st.write(f"**Aadhar Number:** {cust[9]}")
                        
                        kyc_status_color = {
                            'VERIFIED': '🟢',
                            'PENDING': '🟡',
                            'REJECTED': '🔴'
                        }
                        st.write(f"**KYC Status:** {kyc_status_color.get(cust[10], '⚪')} {cust[10]}")
                    
                    with col3:
                        st.markdown("### 📅 Account Info")
                        st.write(f"**Registration Date:** {cust[11][:10] if cust[11] else 'N/A'}")
                        
                        # Get accounts linked to this customer
                        accounts = conn.execute("""
                            SELECT account_number, account_type, balance, status
                            FROM accounts
                            WHERE customer_id=?
                        """, (cust[0],)).fetchall()
                        
                        if accounts:
                            st.write("**Linked Accounts:**")
                            for acc in accounts:
                                st.write(f"• {acc[1]}: {acc[0]}")
                                st.write(f"  Balance: ₹{acc[2]:,.2f} | {acc[3]}")
                        else:
                            st.write("No accounts linked yet")
                    
                    # Show documents if available
                    st.divider()
                    st.markdown("### 📎 Documents")
                    doc_col1, doc_col2, doc_col3 = st.columns(3)
                    
                    # Get full customer data with documents
                    cust_full = conn.execute("SELECT * FROM customers WHERE id=?", (cust[0],)).fetchone()
                    
                    with doc_col1:
                        if cust_full[16]:  # PAN
                            st.write("**PAN Card:**")
                            try:
                                st.image(cust_full[16], width=200)
                            except:
                                st.info("Document available (click to view)")
                    
                    with doc_col2:
                        if cust_full[17]:  # Aadhar
                            st.write("**Aadhar Card:**")
                            try:
                                st.image(cust_full[17], width=200)
                            except:
                                st.info("Document available (click to view)")
                    
                    with doc_col3:
                        if cust_full[18]:  # Photo
                            st.write("**Photo:**")
                            try:
                                st.image(cust_full[18], width=150)
                            except:
                                st.info("Photo available (click to view)")
            
            # Export option
            df = pd.DataFrame(customers, columns=['ID', 'Customer ID', 'First Name', 'Last Name', 
                                                  'Email', 'Phone', 'City', 'State', 'PAN', 'Aadhar',
                                                  'KYC Status', 'Reg Date', 'DOB', 'Gender', 'Address', 'PIN'])
            csv = df.to_csv(index=False)
            st.download_button("📥 Download Customer List", csv, "customers.csv", "text/csv")
        else:
            st.info("No customers registered yet")
        conn.close()
    
    with tab3:
        st.subheader("Search Customer")
        search_term = st.text_input("Search by Name, Customer ID, Email, Phone, PAN, or Aadhar")
        
        if search_term:
            conn = get_db()
            customers = conn.execute("""
                SELECT * FROM customers
                WHERE customer_id LIKE ? OR first_name LIKE ? OR last_name LIKE ? 
                OR email LIKE ? OR phone LIKE ? OR pan_number LIKE ? OR aadhar_number LIKE ?
            """, (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%',
                  f'%{search_term}%', f'%{search_term}%', f'%{search_term}%', f'%{search_term}%')).fetchall()
            
            if customers:
                st.success(f"Found {len(customers)} customer(s)")
                for cust in customers:
                    with st.expander(f"📋 {cust[3]} {cust[4]} - {cust[2]}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Customer ID:** {cust[2]}")
                            st.write(f"**Date of Birth:** {cust[5]}")
                            st.write(f"**Gender:** {cust[6]}")
                            st.write(f"**Email:** {cust[7]}")
                            st.write(f"**Phone:** {cust[8]}")
                            st.write(f"**PAN:** {cust[12]}")
                            st.write(f"**Aadhar:** {cust[13]}")
                        with col2:
                            kyc_color = {'VERIFIED': '🟢', 'PENDING': '🟡', 'REJECTED': '🔴'}
                            st.write(f"**KYC Status:** {kyc_color.get(cust[14], '⚪')} {cust[14]}")
                            st.write(f"**Address:** {cust[9]}")
                            st.write(f"**City:** {cust[10]}, {cust[11]}")
                            st.write(f"**Registration:** {cust[20][:10] if cust[20] else 'N/A'}")
            else:
                st.warning("No customer found")
            conn.close()
    
    with tab4:
        st.subheader("Customer Analytics")
        conn = get_db()
        
        # KYC Status Distribution
        kyc_stats = conn.execute("""
            SELECT kyc_status, COUNT(*) as count
            FROM customers
            GROUP BY kyc_status
        """).fetchall()
        
        if kyc_stats:
            df = pd.DataFrame(kyc_stats, columns=['Status', 'Count'])
            fig = px.pie(df, values='Count', names='Status', title='KYC Status Distribution')
            st.plotly_chart(fig, use_container_width=True)
        
        # City-wise distribution
        city_stats = conn.execute("""
            SELECT city, COUNT(*) as count
            FROM customers
            GROUP BY city
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()
        
        if city_stats:
            df = pd.DataFrame(city_stats, columns=['City', 'Customers'])
            fig = px.bar(df, x='City', y='Customers', title='Top 10 Cities by Customers')
            st.plotly_chart(fig, use_container_width=True)
        
        conn.close()

def calculate_age(dob_str):
    """Calculate age from date of birth string"""
    if not dob_str:
        return "N/A"
    try:
        dob = datetime.strptime(str(dob_str), '%Y-%m-%d').date()
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age
    except:
        return "N/A"

def show_my_details():
    st.markdown('<h1 class="main-header">👤 My Details</h1>', unsafe_allow_html=True)
    
    conn = get_db()
    
    # Get customer linked to this user
    customer = conn.execute("""
        SELECT * FROM customers WHERE user_id=?
    """, (st.session_state.user['id'],)).fetchone()
    
    if customer:
        st.markdown('<div class="customer-card">', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if customer[18]:  # Photo
                try:
                    st.image(customer[18], width=150)
                except:
                    st.write("📷 No photo")
        
        with col2:
            st.markdown(f"## {customer[3]} {customer[4]}")
            st.write(f"**Customer ID:** {customer[2]}")
            st.write(f"**Email:** {customer[7]}")
            st.write(f"**Phone:** {customer[8]}")
            kyc_color = {'VERIFIED': '🟢', 'PENDING': '🟡', 'REJECTED': '🔴'}
            st.write(f"**KYC Status:** {kyc_color.get(customer[14], '⚪')} {customer[14]}")
        
        with col3:
            st.write(f"**DOB:** {customer[5]}")
            st.write(f"**Gender:** {customer[6]}")
            st.write(f"**PAN:** {customer[12]}")
            st.write(f"**Aadhar:** {customer[13]}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Show accounts
        st.subheader("💰 My Accounts")
        accounts = conn.execute("""
            SELECT account_number, account_type, balance, interest_rate, status, created_at
            FROM accounts
            WHERE customer_id=?
            ORDER BY created_at DESC
        """, (customer[0],)).fetchall()
        
        if accounts:
            for acc in accounts:
                with st.expander(f"{acc[1]} - {acc[0]} (₹{acc[2]:,.2f})"):
                    st.write(f"**Account Number:** {acc[0]}")
                    st.write(f"**Type:** {acc[1]}")
                    st.write(f"**Balance:** ₹{acc[2]:,.2f}")
                    st.write(f"**Interest Rate:** {acc[3]}%")
                    st.write(f"**Status:** {acc[4]}")
                    st.write(f"**Opened:** {acc[5][:10]}")
        else:
            st.info("No accounts found")
    else:
        st.warning("Customer profile not found. Please contact admin.")
    
    conn.close()

def show_kyc_verification():
    st.markdown('<h1 class="main-header">🔍 KYC Verification</h1>', unsafe_allow_html=True)
    
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized access")
        return
    
    conn = get_db()
    
    tab1, tab2 = st.tabs(["📋 Pending Verifications", "✅ Verified Customers"])
    
    with tab1:
        pending_kyc = conn.execute("""
            SELECT * FROM customers WHERE kyc_status='PENDING'
            ORDER BY created_at
        """).fetchall()
        
        if not pending_kyc:
            st.success("✅ No pending KYC verifications!")
        else:
            st.subheader(f"Pending Verifications: {len(pending_kyc)}")
            
            for cust in pending_kyc:
                with st.expander(f"📄 {cust[3]} {cust[4]} - {cust[2]}", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("### Personal Information")
                        st.write(f"**Name:** {cust[3]} {cust[4]}")
                        st.write(f"**Date of Birth:** {cust[5]}")
                        st.write(f"**Gender:** {cust[6]}")
                        st.write(f"**Email:** {cust[7]}")
                        st.write(f"**Phone:** {cust[8]}")
                        st.write(f"**PAN Number:** {cust[12]}")
                        st.write(f"**Aadhar Number:** {cust[13]}")
                        st.write(f"**Address:** {cust[9]}, {cust[10]}, {cust[11]}")
                    
                    with col2:
                        st.write("### Documents")
                        
                        if cust[16]:
                            st.write("**PAN Card:**")
                            try:
                                st.image(cust[16], width=250)
                            except:
                                st.info("Document uploaded (binary format)")
                        
                        if cust[17]:
                            st.write("**Aadhar Card:**")
                            try:
                                st.image(cust[17], width=250)
                            except:
                                st.info("Document uploaded (binary format)")
                        
                        if cust[18]:
                            st.write("**Photo:**")
                            try:
                                st.image(cust[18], width=150)
                            except:
                                st.info("Photo uploaded (binary format)")
                    
                    st.divider()
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button(f"✅ Approve KYC", key=f"approve_{cust[0]}", use_container_width=True):
                            conn.execute("""
                                UPDATE customers 
                                SET kyc_status='VERIFIED', 
                                    kyc_verified_by=?,
                                    kyc_verified_at=CURRENT_TIMESTAMP
                                WHERE id=?
                            """, (st.session_state.user['id'], cust[0]))
                            
                            # Create SB account with 0 balance automatically
                            account_number = generate_account_number('SB')
                            conn.execute("""
                                INSERT INTO accounts (account_number, customer_id, account_type, balance, interest_rate, last_interest_calculation)
                                VALUES (?, ?, 'SB', 0.00, 3.50, DATE('now'))
                            """, (account_number, cust[0]))
                            
                            conn.commit()
                            st.success(f"✅ KYC approved! SB Account created with 0 balance.")
                            st.info(f"SB Account Number: **{account_number}**")
                            st.rerun()
                    
                    with col2:
                        if st.button(f"❌ Reject KYC", key=f"reject_{cust[0]}", use_container_width=True):
                            conn.execute("""
                                UPDATE customers 
                                SET kyc_status='REJECTED'
                                WHERE id=?
                            """, (cust[0],))
                            conn.commit()
                            st.warning(f"KYC rejected for {cust[3]} {cust[4]}")
                            st.rerun()
                    
                    with col3:
                        st.text_input(f"Remarks", key=f"remarks_{cust[0]}", placeholder="Optional remarks")
    
    with tab2:
        verified_customers = conn.execute("""
            SELECT customer_id, first_name, last_name, email, phone, kyc_verified_at
            FROM customers
            WHERE kyc_status='VERIFIED'
            ORDER BY kyc_verified_at DESC
        """).fetchall()
        
        if verified_customers:
            st.subheader(f"Verified Customers: {len(verified_customers)}")
            df = pd.DataFrame(verified_customers, columns=['Customer ID', 'First Name', 'Last Name', 
                                                           'Email', 'Phone', 'Verified Date'])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No verified customers yet")
    
    conn.close()

def show_sb_accounts():
    st.markdown('<h1 class="main-header">💰 Savings Bank Accounts</h1>', unsafe_allow_html=True)
    
    conn = get_db()
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Account List", "💸 Deposit/Withdraw", "📜 Account Statement", "📈 Interest Info"])
    
    with tab1:
        st.subheader("SB Account List")
        
        # Filter for customer role
        if st.session_state.user['role'] == 'customer':
            accounts = conn.execute("""
                SELECT a.account_number, c.first_name || ' ' || c.last_name as name,
                       a.balance, a.interest_rate, a.status, a.created_at
                FROM accounts a
                JOIN customers c ON a.customer_id = c.id
                WHERE a.account_type='SB' AND c.user_id=?
                ORDER BY a.created_at DESC
            """, (st.session_state.user['id'],)).fetchall()
        else:
            accounts = conn.execute("""
                SELECT a.account_number, c.first_name || ' ' || c.last_name as name,
                       a.balance, a.interest_rate, a.status, a.created_at
                FROM accounts a
                JOIN customers c ON a.customer_id = c.id
                WHERE a.account_type='SB' AND c.kyc_status='VERIFIED'
                ORDER BY a.created_at DESC
            """).fetchall()
        
        if accounts:
            df = pd.DataFrame(accounts, columns=['Account Number', 'Customer Name', 'Balance', 
                                                 'Interest Rate', 'Status', 'Opening Date'])
            st.dataframe(df.style.format({'Balance': '₹{:,.2f}', 'Interest Rate': '{:.2f}%'}), 
                        use_container_width=True)
            
            total_sb = sum(acc[2] for acc in accounts)
            st.info(f"**Total SB Deposits: ₹{total_sb:,.2f}**")
            
            # Important notice about opening balance
            st.markdown('<div class="info-box">⚠️ <strong>Note:</strong> All SB accounts are opened with ₹0.00 balance. Interest is calculated quarterly on the minimum monthly balance.</div>', unsafe_allow_html=True)
        else:
            st.info("No SB accounts found")
    
    with tab2:
        st.subheader("Transaction (Deposit/Withdrawal)")
        st.warning("**Note: SB Account opening balance is always ₹0.00. All transactions are recorded with voucher numbers.**")
        
        # Get all active SB accounts
        if st.session_state.user['role'] == 'customer':
            accounts = conn.execute("""
                SELECT a.id, a.account_number, c.first_name || ' ' || c.last_name as name, a.balance
                FROM accounts a
                JOIN customers c ON a.customer_id = c.id
                WHERE a.account_type='SB' AND a.status='ACTIVE' AND c.user_id=?
            """, (st.session_state.user['id'],)).fetchall()
        else:
            accounts = conn.execute("""
                SELECT a.id, a.account_number, c.first_name || ' ' || c.last_name as name, a.balance
                FROM accounts a
                JOIN customers c ON a.customer_id = c.id
                WHERE a.account_type='SB' AND a.status='ACTIVE'
            """).fetchall()
        
        if accounts:
            account_options = {f"{acc[1]} - {acc[2]} (Balance: ₹{acc[3]:,.2f})": acc for acc in accounts}
            selected = st.selectbox("Select Account", list(account_options.keys()))
            
            if selected:
                account = account_options[selected]
                transaction_type = st.radio("Transaction Type", ["💰 DEPOSIT", "💸 WITHDRAWAL"], horizontal=True)
                
                with st.form("sb_transaction"):
                    amount = st.number_input("Amount (₹)", min_value=0.01, step=100.0)
                    description = st.text_input("Description/Narration", placeholder="Enter transaction details")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        reference_type = st.selectbox("Payment Mode", ["CASH", "TRANSFER", "CHEQUE"])
                    
                    if st.form_submit_button("💳 Process Transaction", use_container_width=True):
                        txn_type_actual = "WITHDRAWAL" if "WITHDRAWAL" in transaction_type else "DEPOSIT"
                        
                        if txn_type_actual == "WITHDRAWAL" and amount > account[3]:
                            st.error("❌ Insufficient balance!")
                        else:
                            try:
                                if txn_type_actual == "DEPOSIT":
                                    new_balance = account[3] + amount
                                    txn_type = "CREDIT"
                                    voucher_type = "RECEIPT"
                                else:
                                    new_balance = account[3] - amount
                                    txn_type = "DEBIT"
                                    voucher_type = "PAYMENT"
                                
                                txn_id = generate_id('TXN')
                                voucher_num = generate_voucher_number(voucher_type)
                                
                                conn.execute("""
                                    INSERT INTO transactions 
                                    (transaction_id, account_id, transaction_type, amount, 
                                     balance_after, description, reference_type, voucher_type, 
                                     voucher_number, created_by)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (txn_id, account[0], txn_type, amount, new_balance,
                                      description, reference_type, voucher_type,
                                      voucher_num, st.session_state.user['id']))
                                
                                conn.execute("UPDATE accounts SET balance=? WHERE id=?", 
                                           (new_balance, account[0]))
                                
                                conn.commit()
                                
                                st.success(f"✅ Transaction successful!")
                                st.info(f"Voucher: **{voucher_num}** | New Balance: **₹{new_balance:,.2f}**")
                                st.balloons()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
        else:
            st.warning("No active SB accounts available")
    
    with tab3:
        st.subheader("Account Statement")
        
        if st.session_state.user['role'] == 'customer':
            accounts = conn.execute("""
                SELECT a.id, a.account_number, c.first_name || ' ' || c.last_name as name
                FROM accounts a
                JOIN customers c ON a.customer_id = c.id
                WHERE a.account_type='SB' AND a.status='ACTIVE' AND c.user_id=?
            """, (st.session_state.user['id'],)).fetchall()
        else:
            accounts = conn.execute("""
                SELECT a.id, a.account_number, c.first_name || ' ' || c.last_name as name
                FROM accounts a
                JOIN customers c ON a.customer_id = c.id
                WHERE a.account_type='SB' AND a.status='ACTIVE'
            """).fetchall()
        
        if accounts:
            account_options = {f"{acc[1]} - {acc[2]}": acc[0] for acc in accounts}
            selected = st.selectbox("Select Account for Statement", list(account_options.keys()))
            
            if selected:
                account_id = account_options[selected]
                
                col1, col2 = st.columns(2)
                with col1:
                    from_date = st.date_input("From Date", date.today() - timedelta(days=30))
                with col2:
                    to_date = st.date_input("To Date", date.today())
                
                transactions = conn.execute("""
                    SELECT transaction_id, created_at, transaction_type, amount, 
                           balance_after, description, reference_type, voucher_number
                    FROM transactions
                    WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ?
                    ORDER BY created_at DESC
                """, (account_id, from_date, to_date)).fetchall()
                
                if transactions:
                    df = pd.DataFrame(transactions, 
                                    columns=['Transaction ID', 'Date', 'Type', 'Amount', 
                                           'Balance', 'Description', 'Mode', 'Voucher No.'])
                    st.dataframe(df.style.format({'Amount': '₹{:,.2f}', 'Balance': '₹{:,.2f}'}), 
                                use_container_width=True)
                    
                    csv = df.to_csv(index=False)
                    st.download_button("📥 Download Statement", csv, "account_statement.csv", "text/csv")
                else:
                    st.info("No transactions in selected period")
        else:
            st.info("No accounts available")
    
    with tab4:
        st.subheader("Interest Rate Information")
        st.info("""
        ### SB Account Interest Calculation Rules:
        
        1. **Interest Rate:** 3.50% per annum (subject to change)
        2. **Calculation Method:** Interest is calculated on the **minimum monthly balance** between 10th and last day of each month
        3. **Calculation Frequency:** Quarterly (March, June, September, December)
        4. **Minimum Balance:** No minimum balance required
        5. **Opening Balance:** Always ₹0.00
        
        **Formula:** Interest = (Minimum Balance × Rate × Number of Days) / (100 × 365)
        
        **Example:**
        - If minimum balance in January is ₹10,000
        - Interest for January = (10,000 × 3.50 × 31) / (100 × 365) = ₹29.73
        """)
        
        # Show recent interest calculations
        if st.session_state.user['role'] in ['admin', 'staff']:
            st.subheader("Recent Interest Calculations")
            try:
                interest_calcs = conn.execute("""
                    SELECT ic.calculation_date, a.account_number, c.first_name || ' ' || c.last_name,
                           ic.principal_amount, ic.interest_rate, ic.interest_earned, ic.days_calculated
                    FROM interest_calculations ic
                    JOIN accounts a ON ic.account_id = a.id
                    JOIN customers c ON a.customer_id = c.id
                    ORDER BY ic.calculation_date DESC
                    LIMIT 20
                """).fetchall()
                
                if interest_calcs:
                    df = pd.DataFrame(interest_calcs, columns=['Date', 'Account', 'Customer', 
                                                               'Principal', 'Rate', 'Interest Earned', 'Days'])
                    st.dataframe(df.style.format({
                        'Principal': '₹{:,.2f}',
                        'Rate': '{:.2f}%',
                        'Interest Earned': '₹{:,.2f}'
                    }), use_container_width=True)
                else:
                    st.info("No interest calculations yet")
            except sqlite3.OperationalError:
                st.info("Interest calculations feature will be available after first interest calculation")
    
    conn.close()

def show_interest_calculation():
    st.markdown('<h1 class="main-header">📈 Interest Calculation</h1>', unsafe_allow_html=True)
    
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized access")
        return
    
    conn = get_db()
    
    tab1, tab2 = st.tabs(["🧮 Calculate Interest", "📊 Interest History"])
    
    with tab1:
        st.subheader("Calculate SB Interest")
        st.info("Interest is calculated on the minimum balance for the selected period")
        
        # Get all active SB accounts
        accounts = conn.execute("""
            SELECT a.id, a.account_number, c.first_name || ' ' || c.last_name as name, a.balance
            FROM accounts a
            JOIN customers c ON a.customer_id = c.id
            WHERE a.account_type='SB' AND a.status='ACTIVE'
        """).fetchall()
        
        if accounts:
            # Option to calculate for all accounts or single account
            calc_option = st.radio("Calculate for:", ["All SB Accounts", "Single Account"])
            
            if calc_option == "Single Account":
                account_options = {f"{acc[1]} - {acc[2]} (₹{acc[3]:,.2f})": acc for acc in accounts}
                selected = st.selectbox("Select Account", list(account_options.keys()))
                selected_accounts = [account_options[selected]]
            else:
                selected_accounts = accounts
            
            col1, col2 = st.columns(2)
            with col1:
                calc_from = st.date_input("Calculate Interest From", date.today().replace(day=1))
            with col2:
                calc_to = st.date_input("Calculate Interest To", date.today())
            
            if st.button("🧮 Calculate Interest", use_container_width=True):
                total_interest = 0
                results = []
                
                for acc in selected_accounts:
                    # Get minimum balance in period
                    min_balance = get_minimum_balance(conn, acc[0], calc_from, calc_to)
                    days = (calc_to - calc_from).days + 1
                    
                    # Get interest rate (default 3.5%)
                    rate = conn.execute("SELECT interest_rate FROM accounts WHERE id=?", 
                                      (acc[0],)).fetchone()[0] or 3.5
                    
                    interest = calculate_sb_interest(min_balance, rate, days)
                    total_interest += interest
                    
                    # Log calculation
                    conn.execute("""
                        INSERT INTO interest_calculations 
                        (account_id, calculation_date, principal_amount, interest_rate, interest_earned, days_calculated)
                        VALUES (?, DATE('now'), ?, ?, ?, ?)
                    """, (acc[0], min_balance, rate, interest, days))
                    
                    results.append({
                        'Account': acc[1],
                        'Customer': acc[2],
                        'Min Balance': min_balance,
                        'Rate': rate,
                        'Days': days,
                        'Interest': interest
                    })
                
                conn.commit()
                
                # Display results
                st.subheader("Interest Calculation Results")
                df = pd.DataFrame(results)
                st.dataframe(df.style.format({
                    'Min Balance': '₹{:,.2f}',
                    'Rate': '{:.2f}%',
                    'Interest': '₹{:,.2f}'
                }), use_container_width=True)
                
                st.success(f"Total Interest for period: **₹{total_interest:,.2f}**")
                
                # Option to credit interest
                if st.button("💰 Credit Interest to Accounts", use_container_width=True):
                    for res in results:
                        acc_id = [a[0] for a in accounts if a[1] == res['Account']][0]
                        
                        # Get current balance
                        current_balance = conn.execute("SELECT balance FROM accounts WHERE id=?", 
                                                       (acc_id,)).fetchone()[0]
                        new_balance = current_balance + res['Interest']
                        
                        # Create interest credit transaction
                        txn_id = generate_id('TXN')
                        voucher_num = generate_voucher_number('RECEIPT')
                        
                        conn.execute("""
                            INSERT INTO transactions 
                            (transaction_id, account_id, transaction_type, amount, 
                             balance_after, description, reference_type, voucher_type, 
                             voucher_number, created_by)
                            VALUES (?, ?, 'CREDIT', ?, ?, 'SB Interest Credited', 'INTEREST', 'RECEIPT', ?, ?)
                        """, (txn_id, acc_id, res['Interest'], new_balance, voucher_num,
                              st.session_state.user['id']))
                        
                        # Update balance
                        conn.execute("UPDATE accounts SET balance=?, last_interest_calculation=DATE('now') WHERE id=?", 
                                   (new_balance, acc_id))
                    
                    conn.commit()
                    st.success("✅ Interest credited to all accounts successfully!")
                    st.balloons()
                    st.rerun()
        else:
            st.warning("No active SB accounts found")
    
    with tab2:
        st.subheader("Interest Calculation History")
        
        history = conn.execute("""
            SELECT ic.calculation_date, a.account_number, c.first_name || ' ' || c.last_name as customer,
                   ic.principal_amount, ic.interest_rate, ic.interest_earned, ic.days_calculated
            FROM interest_calculations ic
            JOIN accounts a ON ic.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            ORDER BY ic.calculation_date DESC
            LIMIT 50
        """).fetchall()
        
        if history:
            df = pd.DataFrame(history, columns=['Date', 'Account', 'Customer', 'Min Balance', 
                                                'Rate', 'Interest', 'Days'])
            st.dataframe(df.style.format({
                'Min Balance': '₹{:,.2f}',
                'Rate': '{:.2f}%',
                'Interest': '₹{:,.2f}'
            }), use_container_width=True)
            
            total_interest_paid = sum(h[5] for h in history)
            st.info(f"**Total Interest Paid: ₹{total_interest_paid:,.2f}**")
            
            csv = df.to_csv(index=False)
            st.download_button("📥 Download History", csv, "interest_history.csv", "text/csv")
        else:
            st.info("No interest calculations recorded yet")
    
    conn.close()

def get_minimum_balance(conn, account_id, from_date, to_date):
    """Get minimum balance for an account during a period"""
    # Get all balances during period
    balances = conn.execute("""
        SELECT balance_after, created_at
        FROM transactions
        WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ?
        ORDER BY created_at
    """, (account_id, from_date, to_date)).fetchall()
    
    if not balances:
        # If no transactions, return current balance
        current = conn.execute("SELECT balance FROM accounts WHERE id=?", 
                              (account_id,)).fetchone()[0]
        return current
    
    # Return minimum balance from transactions
    return min(b[0] for b in balances)

def show_fixed_deposits():
    st.markdown('<h1 class="main-header">💎 Fixed Deposits</h1>', unsafe_allow_html=True)
    
    conn = get_db()
    
    tab1, tab2, tab3 = st.tabs(["📝 Open New FD", "📋 Active FDs", "🔔 Maturity Alerts"])
    
    with tab1:
        st.subheader("Open New Fixed Deposit")
        
        customers = conn.execute("""
            SELECT c.id, c.customer_id, c.first_name || ' ' || c.last_name as name,
                   a.account_number, a.balance
            FROM customers c
            JOIN accounts a ON c.id = a.customer_id
            WHERE a.account_type='SB' AND c.kyc_status='VERIFIED' AND a.status='ACTIVE'
        """).fetchall()
        
        if customers:
            customer_options = {f"{cust[1]} - {cust[2]} (SB: {cust[3]})": cust for cust in customers}
            selected = st.selectbox("Select Customer", list(customer_options.keys()))
            
            if selected:
                customer = customer_options[selected]
                
                with st.form("open_fd"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        principal = st.number_input("Principal Amount (₹)", min_value=1000.0, step=1000.0, value=10000.0)
                        tenure_months = st.selectbox("Tenure (Months)", [3, 6, 12, 24, 36, 60])
                        interest_rate = st.number_input("Interest Rate (%)", min_value=3.0, max_value=10.0, value=6.5, step=0.25)
                    
                    with col2:
                        start_date = st.date_input("Start Date", date.today())
                        nominee_name = st.text_input("Nominee Name", placeholder="Enter nominee name")
                        nominee_relation = st.text_input("Nominee Relation", placeholder="e.g., Spouse, Son, Daughter")
                    
                    # Calculate maturity
                    maturity_date = start_date + timedelta(days=tenure_months * 30)
                    maturity_amount = calculate_fd_maturity(principal, interest_rate, tenure_months)
                    interest_earned = maturity_amount - principal
                    
                    st.info(f"📅 **Maturity Date:** {maturity_date.strftime('%d-%m-%Y')}")
                    st.info(f"💰 **Maturity Amount:** ₹{maturity_amount:,.2f} (Interest: ₹{interest_earned:,.2f})")
                    
                    if st.form_submit_button("🔒 Open FD", use_container_width=True):
                        try:
                            fd_number = generate_id('FD')
                            
                            account_number = generate_account_number('FD')
                            conn.execute("""
                                INSERT INTO accounts (account_number, customer_id, account_type, 
                                                     balance, interest_rate)
                                VALUES (?, ?, 'FD', 0.00, ?)
                            """, (account_number, customer[0], interest_rate))
                            
                            account_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                            
                            conn.execute("""
                                INSERT INTO fixed_deposits 
                                (fd_number, account_id, principal_amount, interest_rate, 
                                 start_date, maturity_date, maturity_amount, tenure_months,
                                 nominee_name, nominee_relation)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (fd_number, account_id, principal, interest_rate,
                                  start_date, maturity_date, maturity_amount, tenure_months,
                                  nominee_name, nominee_relation))
                            
                            txn_id = generate_id('TXN')
                            voucher_num = generate_voucher_number('RECEIPT')
                            conn.execute("""
                                INSERT INTO transactions 
                                (transaction_id, account_id, transaction_type, amount, 
                                 balance_after, description, reference_type, voucher_type, 
                                 voucher_number, created_by)
                                VALUES (?, ?, 'CREDIT', ?, ?, 'FD Deposit - Principal', 'FD_DEPOSIT', 
                                        'RECEIPT', ?, ?)
                            """, (txn_id, account_id, principal, principal,
                                  voucher_num, st.session_state.user['id']))
                            
                            conn.commit()
                            st.success(f"✅ FD opened successfully!")
                            st.info(f"FD Number: **{fd_number}**")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        else:
            st.warning("No verified customers with SB accounts available")
    
    with tab2:
        st.subheader("Active Fixed Deposits")
        
        fds = conn.execute("""
            SELECT fd.fd_number, c.first_name || ' ' || c.last_name as name,
                   fd.principal_amount, fd.interest_rate, fd.start_date, 
                   fd.maturity_date, fd.maturity_amount, fd.status
            FROM fixed_deposits fd
            JOIN accounts a ON fd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            WHERE fd.status='ACTIVE'
            ORDER BY fd.maturity_date
        """).fetchall()
        
        if fds:
            df = pd.DataFrame(fds, columns=['FD Number', 'Customer', 'Principal', 
                                           'Rate (%)', 'Start Date', 'Maturity Date',
                                           'Maturity Amount', 'Status'])
            st.dataframe(df.style.format({
                'Principal': '₹{:,.2f}',
                'Rate (%)': '{:.2f}%',
                'Maturity Amount': '₹{:,.2f}'
            }), use_container_width=True)
            
            total_fd = sum(fd[2] for fd in fds)
            st.info(f"**Total FD Deposits: ₹{total_fd:,.2f}**")
        else:
            st.info("No active FDs found")
    
    with tab3:
        st.subheader("FD Maturity Calendar")
        
        today = date.today()
        next_30_days = today + timedelta(days=30)
        
        maturing_fds = conn.execute("""
            SELECT fd.fd_number, c.first_name || ' ' || c.last_name as name,
                   fd.principal_amount, fd.maturity_amount, fd.maturity_date,
                   fd.nominee_name, fd.nominee_relation
            FROM fixed_deposits fd
            JOIN accounts a ON fd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            WHERE fd.maturity_date BETWEEN ? AND ? AND fd.status='ACTIVE'
            ORDER BY fd.maturity_date
        """, (today, next_30_days)).fetchall()
        
        if maturing_fds:
            st.warning(f"🔔 **{len(maturing_fds)} FD(s) maturing in next 30 days**")
            df = pd.DataFrame(maturing_fds, columns=['FD Number', 'Customer', 'Principal', 
                                                     'Maturity Amount', 'Maturity Date',
                                                     'Nominee', 'Relation'])
            st.dataframe(df.style.format({
                'Principal': '₹{:,.2f}',
                'Maturity Amount': '₹{:,.2f}'
            }), use_container_width=True)
            
            for fd in maturing_fds:
                days_left = (datetime.strptime(fd[4], '%Y-%m-%d').date() - today).days
                st.info(f"📅 {fd[0]} - {fd[1]}: **{days_left} days left** (Matures: {fd[4]})")
        else:
            st.success("No FDs maturing in next 30 days")
    
    conn.close()

def show_recurring_deposits():
    st.markdown('<h1 class="main-header">🔄 Recurring Deposits</h1>', unsafe_allow_html=True)
    
    conn = get_db()
    
    tab1, tab2, tab3 = st.tabs(["📝 Open New RD", "📋 Active RDs", "💳 Pay Installment"])
    
    with tab1:
        st.subheader("Open New Recurring Deposit")
        
        customers = conn.execute("""
            SELECT c.id, c.customer_id, c.first_name || ' ' || c.last_name as name,
                   a.account_number, a.id as account_id
            FROM customers c
            JOIN accounts a ON c.id = a.customer_id
            WHERE a.account_type='SB' AND c.kyc_status='VERIFIED' AND a.status='ACTIVE'
        """).fetchall()
        
        if customers:
            customer_options = {f"{cust[1]} - {cust[2]} (SB: {cust[3]})": cust for cust in customers}
            selected = st.selectbox("Select Customer", list(customer_options.keys()))
            
            if selected:
                customer = customer_options[selected]
                
                with st.form("open_rd"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        monthly_amount = st.number_input("Monthly Installment (₹)", min_value=100.0, step=100.0, value=1000.0)
                        tenure_months = st.selectbox("Tenure (Months)", [6, 12, 24, 36, 48, 60])
                        interest_rate = st.number_input("Interest Rate (%)", min_value=3.0, max_value=10.0, value=6.0, step=0.25)
                    
                    with col2:
                        start_date = st.date_input("Start Date", date.today())
                        nominee_name = st.text_input("Nominee Name")
                        nominee_relation = st.text_input("Nominee Relation")
                    
                    maturity_date = start_date + timedelta(days=tenure_months * 30)
                    maturity_amount = calculate_rd_maturity(monthly_amount, interest_rate, tenure_months)
                    total_deposit = monthly_amount * tenure_months
                    interest_earned = maturity_amount - total_deposit
                    
                    st.info(f"📅 **Maturity Date:** {maturity_date.strftime('%d-%m-%Y')}")
                    st.info(f"💰 **Total Deposits:** ₹{total_deposit:,.2f}")
                    st.info(f"💎 **Maturity Amount:** ₹{maturity_amount:,.2f} (Interest: ₹{interest_earned:,.2f})")
                    
                    if st.form_submit_button("🔄 Open RD", use_container_width=True):
                        try:
                            rd_number = generate_id('RD')
                            
                            account_number = generate_account_number('RD')
                            conn.execute("""
                                INSERT INTO accounts (account_number, customer_id, account_type, 
                                                     balance, interest_rate)
                                VALUES (?, ?, 'RD', 0.00, ?)
                            """, (account_number, customer[0], interest_rate))
                            
                            account_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                            
                            conn.execute("""
                                INSERT INTO recurring_deposits 
                                (rd_number, account_id, monthly_amount, interest_rate,
                                 start_date, maturity_date, maturity_amount, tenure_months,
                                 total_installments, nominee_name, nominee_relation)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (rd_number, account_id, monthly_amount, interest_rate,
                                  start_date, maturity_date, maturity_amount, tenure_months,
                                  tenure_months, nominee_name, nominee_relation))
                            
                            txn_id = generate_id('TXN')
                            voucher_num = generate_voucher_number('RECEIPT')
                            conn.execute("""
                                INSERT INTO transactions 
                                (transaction_id, account_id, transaction_type, amount, 
                                 balance_after, description, reference_type, voucher_type, 
                                 voucher_number, created_by)
                                VALUES (?, ?, 'CREDIT', ?, ?, 'RD Installment 1', 'RD_INSTALLMENT', 
                                        'RECEIPT', ?, ?)
                            """, (txn_id, account_id, monthly_amount, monthly_amount,
                                  voucher_num, st.session_state.user['id']))
                            
                            conn.execute("UPDATE recurring_deposits SET installments_paid=1 WHERE rd_number=?",
                                       (rd_number,))
                            
                            conn.commit()
                            st.success(f"✅ RD opened successfully!")
                            st.info(f"RD Number: **{rd_number}**")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        else:
            st.warning("No verified customers with SB accounts")
    
    with tab2:
        st.subheader("Active Recurring Deposits")
        
        rds = conn.execute("""
            SELECT rd.rd_number, c.first_name || ' ' || c.last_name as name,
                   rd.monthly_amount, rd.interest_rate, rd.start_date,
                   rd.maturity_date, rd.maturity_amount, 
                   rd.installments_paid, rd.total_installments, rd.status
            FROM recurring_deposits rd
            JOIN accounts a ON rd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            WHERE rd.status='ACTIVE'
            ORDER BY rd.maturity_date
        """).fetchall()
        
        if rds:
            df = pd.DataFrame(rds, columns=['RD Number', 'Customer', 'Monthly Amount',
                                           'Rate (%)', 'Start Date', 'Maturity Date',
                                           'Maturity Amount', 'Paid', 'Total', 'Status'])
            df['Progress'] = df.apply(lambda row: f"{row['Paid']}/{row['Total']} ({(row['Paid']/row['Total']*100):.0f}%)", axis=1)
            st.dataframe(df.style.format({
                'Monthly Amount': '₹{:,.2f}',
                'Rate (%)': '{:.2f}%',
                'Maturity Amount': '₹{:,.2f}'
            }), use_container_width=True)
        else:
            st.info("No active RDs found")
    
    with tab3:
        st.subheader("Pay RD Installment")
        
        rds = conn.execute("""
            SELECT rd.id, rd.rd_number, c.first_name || ' ' || c.last_name as name,
                   rd.monthly_amount, rd.installments_paid, rd.total_installments,
                   a.id as account_id
            FROM recurring_deposits rd
            JOIN accounts a ON rd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            WHERE rd.status='ACTIVE' AND rd.installments_paid < rd.total_installments
        """).fetchall()
        
        if rds:
            rd_options = {
                f"{rd[1]} - {rd[2]} (Paid: {rd[4]}/{rd[5]} - ₹{rd[3]:,.2f}/month)": rd 
                for rd in rds
            }
            selected = st.selectbox("Select RD", list(rd_options.keys()))
            
            if selected:
                rd = rd_options[selected]
                
                with st.form("pay_installment"):
                    st.write(f"**Monthly Installment Amount:** ₹{rd[3]:,.2f}")
                    amount = st.number_input("Amount (₹)", value=float(rd[3]), min_value=float(rd[3]))
                    description = st.text_input("Description", value=f"RD Installment {rd[4]+1}/{rd[5]}")
                    
                    if st.form_submit_button("💳 Pay Installment", use_container_width=True):
                        try:
                            txn_id = generate_id('TXN')
                            voucher_num = generate_voucher_number('RECEIPT')
                            conn.execute("""
                                INSERT INTO transactions 
                                (transaction_id, account_id, transaction_type, amount, 
                                 balance_after, description, reference_type, voucher_type, 
                                 voucher_number, created_by)
                                VALUES (?, ?, 'CREDIT', ?, ?, ?, 'RD_INSTALLMENT', 'RECEIPT', ?, ?)
                            """, (txn_id, rd[6], amount, amount, description,
                                  voucher_num, st.session_state.user['id']))
                            
                            new_paid = rd[4] + 1
                            conn.execute("""
                                UPDATE recurring_deposits 
                                SET installments_paid=? 
                                WHERE id=?
                            """, (new_paid, rd[0]))
                            
                            if new_paid >= rd[5]:
                                conn.execute("""
                                    UPDATE recurring_deposits 
                                    SET status='MATURED' 
                                    WHERE id=?
                                """, (rd[0],))
                                st.info("🎉 Congratulations! RD matured. All installments paid.")
                            
                            conn.commit()
                            st.success(f"✅ Installment paid successfully! ({new_paid}/{rd[5]})")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        else:
            st.info("No pending RD installments")
    
    conn.close()

def show_transactions():
    st.markdown('<h1 class="main-header">💳 Transactions</h1>', unsafe_allow_html=True)
    
    conn = get_db()
    
    # Filters
    st.subheader("🔍 Filter Transactions")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        account_type = st.selectbox("Account Type", ["All", "SB", "FD", "RD"])
    with col2:
        txn_type = st.selectbox("Transaction Type", ["All", "CREDIT", "DEBIT"])
    with col3:
        from_date = st.date_input("From Date", date.today() - timedelta(days=30))
    with col4:
        to_date = st.date_input("To Date", date.today())
    
    # Build query
    query = """
        SELECT t.transaction_id, c.first_name || ' ' || c.last_name as customer,
               a.account_number, a.account_type, t.transaction_type, t.amount,
               t.balance_after, t.description, t.reference_type, t.voucher_number, t.created_at
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        JOIN customers c ON a.customer_id = c.id
        WHERE DATE(t.created_at) BETWEEN ? AND ?
    """
    params = [from_date, to_date]
    
    if st.session_state.user['role'] == 'customer':
        query += " AND c.user_id=?"
        params.append(st.session_state.user['id'])
    
    if account_type != "All":
        query += " AND a.account_type=?"
        params.append(account_type)
    
    if txn_type != "All":
        query += " AND t.transaction_type=?"
        params.append(txn_type)
    
    query += " ORDER BY t.created_at DESC LIMIT 200"
    
    transactions = conn.execute(query, params).fetchall()
    
    if transactions:
        df = pd.DataFrame(transactions, columns=['Txn ID', 'Customer', 'Account', 'Type',
                                                  'Action', 'Amount', 'Balance', 'Description',
                                                  'Mode', 'Voucher', 'Date'])
        st.dataframe(df.style.format({'Amount': '₹{:,.2f}', 'Balance': '₹{:,.2f}'}), 
                    use_container_width=True)
        
        # Summary
        total_credit = sum(t[5] for t in transactions if t[4] == 'CREDIT')
        total_debit = sum(t[5] for t in transactions if t[4] == 'DEBIT')
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Credits", f"₹{total_credit:,.2f}")
        with col2:
            st.metric("Total Debits", f"₹{total_debit:,.2f}")
        with col3:
            st.metric("Net Flow", f"₹{total_credit - total_debit:,.2f}")
        
        # Download
        csv = df.to_csv(index=False)
        st.download_button("📥 Download Transactions", csv, "transactions.csv", "text/csv")
    else:
        st.info("No transactions found for the selected filters")
    
    conn.close()

def show_journal_vouchers():
    st.markdown('<h1 class="main-header">📝 Journal Vouchers</h1>', unsafe_allow_html=True)
    
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("⛔ Unauthorized access")
        return
    
    conn = get_db()
    
    tab1, tab2 = st.tabs(["📝 Create Voucher", "📋 Voucher List"])
    
    with tab1:
        st.subheader("Create Journal Voucher")
        
        with st.form("journal_voucher"):
            voucher_date = st.date_input("Voucher Date", date.today())
            description = st.text_area("Description/Narration", placeholder="Enter voucher description")
            
            st.subheader("Journal Entries")
            st.info("Debit total must equal Credit total")
            
            num_entries = st.number_input("Number of Entries", min_value=2, max_value=10, value=2)
            
            entries = []
            total_debit = 0
            total_credit = 0
            
            for i in range(int(num_entries)):
                st.markdown(f"**Entry {i+1}**")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    account_head = st.text_input(f"Account Head", key=f"head_{i}", 
                                                placeholder="e.g., Cash, Interest, Expense")
                with col2:
                    debit = st.number_input(f"Debit Amount", min_value=0.0, step=100.0, key=f"debit_{i}")
                with col3:
                    credit = st.number_input(f"Credit Amount", min_value=0.0, step=100.0, key=f"credit_{i}")
                
                total_debit += debit
                total_credit += credit
                
                entries.append({
                    'account_head': account_head,
                    'debit': debit,
                    'credit': credit
                })
                st.divider()
            
            st.write(f"**Total Debit: ₹{total_debit:,.2f}** | **Total Credit: ₹{total_credit:,.2f}**")
            
            if abs(total_debit - total_credit) > 0.01:
                st.error(f"⚠️ Difference: ₹{abs(total_debit - total_credit):,.2f}. Debits must equal Credits!")
            
            if st.form_submit_button("📝 Create Voucher", use_container_width=True):
                if abs(total_debit - total_credit) > 0.01:
                    st.error("Cannot create voucher: Debits must equal Credits")
                else:
                    try:
                        voucher_num = generate_voucher_number('JOURNAL')
                        
                        conn.execute("""
                            INSERT INTO journal_vouchers 
                            (voucher_number, voucher_date, description, total_amount, created_by)
                            VALUES (?, ?, ?, ?, ?)
                        """, (voucher_num, voucher_date, description, total_debit, 
                              st.session_state.user['id']))
                        
                        voucher_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                        
                        for entry in entries:
                            if entry['debit'] > 0 or entry['credit'] > 0:
                                conn.execute("""
                                    INSERT INTO journal_entries 
                                    (voucher_id, account_head, debit_amount, credit_amount)
                                    VALUES (?, ?, ?, ?)
                                """, (voucher_id, entry['account_head'], 
                                      entry['debit'], entry['credit']))
                        
                        conn.commit()
                        st.success(f"✅ Journal Voucher created: **{voucher_num}**")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    with tab2:
        st.subheader("Journal Vouchers List")
        
        vouchers = conn.execute("""
            SELECT jv.voucher_number, jv.voucher_date, jv.description,
                   jv.total_amount, jv.status, u.username, jv.created_at
            FROM journal_vouchers jv
            LEFT JOIN users u ON jv.created_by = u.id
            ORDER BY jv.created_at DESC
        """).fetchall()
        
        if vouchers:
            for v in vouchers:
                status_color = {'DRAFT': '🟡', 'POSTED': '🟢', 'CANCELLED': '🔴'}
                with st.expander(f"{status_color.get(v[4], '⚪')} {v[0]} - {v[1]} - ₹{v[3]:,.2f} ({v[4]})"):
                    st.write(f"**Date:** {v[1]}")
                    st.write(f"**Description:** {v[2]}")
                    st.write(f"**Created by:** {v[5]}")
                    st.write(f"**Amount:** ₹{v[3]:,.2f}")
                    
                    entries = conn.execute("""
                        SELECT account_head, debit_amount, credit_amount
                        FROM journal_entries
                        WHERE voucher_id=(
                            SELECT id FROM journal_vouchers WHERE voucher_number=?
                        )
                    """, (v[0],)).fetchall()
                    
                    if entries:
                        df_entries = pd.DataFrame(entries, columns=['Account Head', 'Debit', 'Credit'])
                        st.dataframe(df_entries.style.format({
                            'Debit': '₹{:,.2f}',
                            'Credit': '₹{:,.2f}'
                        }), use_container_width=True)
                    
                    if v[4] == 'DRAFT':
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(f"✅ Post Voucher", key=f"post_{v[0]}", use_container_width=True):
                                conn.execute("""
                                    UPDATE journal_vouchers 
                                    SET status='POSTED', posted_by=?, posted_at=CURRENT_TIMESTAMP
                                    WHERE voucher_number=?
                                """, (st.session_state.user['id'], v[0]))
                                conn.commit()
                                st.success("Voucher posted successfully!")
                                st.rerun()
                        with col2:
                            if st.button(f"❌ Cancel Voucher", key=f"cancel_{v[0]}", use_container_width=True):
                                conn.execute("""
                                    UPDATE journal_vouchers 
                                    SET status='CANCELLED'
                                    WHERE voucher_number=?
                                """, (v[0],))
                                conn.commit()
                                st.warning("Voucher cancelled!")
                                st.rerun()
        else:
            st.info("No journal vouchers found")
    
    conn.close()

def show_trial_balance():
    st.markdown('<h1 class="main-header">⚖️ Trial Balance</h1>', unsafe_allow_html=True)
    
    conn = get_db()
    
    st.subheader("Generate Trial Balance")
    as_on_date = st.date_input("As on Date", date.today())
    
    if st.button("📊 Generate Trial Balance", use_container_width=True):
        trial_data = []
        
        sb_accounts = conn.execute("""
            SELECT a.account_number, c.first_name || ' ' || c.last_name as name, a.balance
            FROM accounts a
            JOIN customers c ON a.customer_id = c.id
            WHERE a.account_type='SB' AND a.status='ACTIVE'
        """).fetchall()
        
        total_sb = sum(acc[2] for acc in sb_accounts)
        if total_sb > 0:
            trial_data.append({
                'account_head': 'Savings Bank Deposits',
                'debit': 0,
                'credit': total_sb
            })
        
        fd_total = conn.execute("""
            SELECT COALESCE(SUM(principal_amount), 0) FROM fixed_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        
        if fd_total > 0:
            trial_data.append({
                'account_head': 'Fixed Deposits',
                'debit': 0,
                'credit': fd_total
            })
        
        rd_total = conn.execute("""
            SELECT COALESCE(SUM(monthly_amount * installments_paid), 0) 
            FROM recurring_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        
        if rd_total > 0:
            trial_data.append({
                'account_head': 'Recurring Deposits',
                'debit': 0,
                'credit': rd_total
            })
        
        cash_balance = conn.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END), 0)
            FROM transactions
            WHERE reference_type='CASH'
        """).fetchone()[0]
        
        if cash_balance != 0:
            trial_data.append({
                'account_head': 'Cash in Hand',
                'debit': max(cash_balance, 0),
                'credit': max(-cash_balance, 0)
            })
        
        interest_payable = conn.execute("""
            SELECT COALESCE(SUM(maturity_amount - principal_amount), 0)
            FROM fixed_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        
        if interest_payable > 0:
            trial_data.append({
                'account_head': 'Interest Payable on FD',
                'debit': 0,
                'credit': interest_payable
            })
        
        # Add interest credited to SB accounts
        interest_credited = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM transactions
            WHERE reference_type='INTEREST' AND transaction_type='CREDIT'
        """).fetchone()[0]
        
        if interest_credited > 0:
            trial_data.append({
                'account_head': 'Interest Paid on SB',
                'debit': interest_credited,
                'credit': 0
            })
        
        total_debits = sum(item['debit'] for item in trial_data)
        total_credits = sum(item['credit'] for item in trial_data)
        
        if abs(total_debits - total_credits) > 0.01:
            diff = total_credits - total_debits
            trial_data.append({
                'account_head': 'Capital/Reserves (Balancing)',
                'debit': max(-diff, 0),
                'credit': max(diff, 0)
            })
        
        if trial_data:
            df = pd.DataFrame(trial_data)
            
            total_debit = df['debit'].sum()
            total_credit = df['credit'].sum()
            
            st.dataframe(df.style.format({
                'debit': '₹{:,.2f}',
                'credit': '₹{:,.2f}'
            }), use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Debit", f"₹{total_debit:,.2f}")
            with col2:
                st.metric("Total Credit", f"₹{total_credit:,.2f}")
            with col3:
                if abs(total_debit - total_credit) < 0.01:
                    st.success("✅ Balanced!")
                else:
                    st.error(f"❌ Difference: ₹{abs(total_debit - total_credit):,.2f}")
            
            csv = df.to_csv(index=False)
            st.download_button("📥 Download CSV", csv, "trial_balance.csv", "text/csv")
            
            if st.button("📄 Generate PDF Report"):
                pdf_data = {
                    'date': as_on_date.strftime('%d-%m-%Y'),
                    'entries': trial_data
                }
                pdf_file = generate_report_pdf('trial_balance', pdf_data, 'trial_balance.pdf')
                if pdf_file:
                    with open(pdf_file, 'rb') as f:
                        st.download_button("📥 Download PDF", f, "trial_balance.pdf", "application/pdf")
        else:
            st.info("No data available for trial balance")
    
    conn.close()

def show_balance_sheet():
    st.markdown('<h1 class="main-header">📊 Balance Sheet</h1>', unsafe_allow_html=True)
    
    conn = get_db()
    as_on_date = st.date_input("As on Date", date.today())
    
    if st.button("📊 Generate Balance Sheet", use_container_width=True):
        st.subheader(f"Balance Sheet as on {as_on_date.strftime('%d-%m-%Y')}")
        
        st.markdown("### 📊 ASSETS")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Current Assets**")
            
            cash = conn.execute("""
                SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END), 0)
                FROM transactions WHERE reference_type='CASH'
            """).fetchone()[0]
            st.write(f"💰 Cash in Hand: **₹{cash:,.2f}**")
            
            total_sb = conn.execute("""
                SELECT COALESCE(SUM(balance), 0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'
            """).fetchone()[0]
            st.write(f"🏦 Bank Deposits: **₹{total_sb:,.2f}**")
        
        with col2:
            st.markdown("**Investments**")
            
            fd_total = conn.execute("""
                SELECT COALESCE(SUM(principal_amount), 0) FROM fixed_deposits WHERE status='ACTIVE'
            """).fetchone()[0]
            st.write(f"💎 Fixed Deposits: **₹{fd_total:,.2f}**")
            
            rd_total = conn.execute("""
                SELECT COALESCE(SUM(monthly_amount * installments_paid), 0)
                FROM recurring_deposits WHERE status='ACTIVE'
            """).fetchone()[0]
            st.write(f"🔄 Recurring Deposits: **₹{rd_total:,.2f}**")
        
        total_assets = cash + total_sb + fd_total + rd_total
        st.markdown(f"### **Total Assets: ₹{total_assets:,.2f}**")
        
        st.divider()
        
        st.markdown("### 📋 LIABILITIES")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Current Liabilities**")
            
            interest = conn.execute("""
                SELECT COALESCE(SUM(maturity_amount - principal_amount), 0)
                FROM fixed_deposits WHERE status='ACTIVE'
            """).fetchone()[0]
            st.write(f"📈 Interest Payable: **₹{interest:,.2f}**")
        
        with col2:
            st.markdown("**Deposits (Liabilities)**")
            st.write(f"💎 FD Deposits: **₹{fd_total:,.2f}**")
            st.write(f"🔄 RD Deposits: **₹{rd_total:,.2f}**")
        
        total_liabilities = interest + fd_total + rd_total
        st.markdown(f"### **Total Liabilities: ₹{total_liabilities:,.2f}**")
        
        st.divider()
        
        capital = total_assets - total_liabilities
        st.markdown("### 💰 CAPITAL")
        st.write(f"**Capital/Net Worth: ₹{capital:,.2f}**")
        
        st.divider()
        
        if abs(total_assets - (total_liabilities + capital)) < 0.01:
            st.success(f"✅ Balance Sheet Balanced! Assets (₹{total_assets:,.2f}) = Liabilities (₹{total_liabilities:,.2f}) + Capital (₹{capital:,.2f})")
        else:
            st.error("❌ Balance Sheet not balanced!")
    
    conn.close()

def show_profit_loss():
    st.markdown('<h1 class="main-header">💵 Profit & Loss Account</h1>', unsafe_allow_html=True)
    
    conn = get_db()
    
    col1, col2 = st.columns(2)
    with col1:
        from_date = st.date_input("From Date", date.today().replace(month=1, day=1))
    with col2:
        to_date = st.date_input("To Date", date.today())
    
    if st.button("📊 Generate P&L Statement", use_container_width=True):
        st.subheader(f"Profit & Loss Account ({from_date.strftime('%d-%m-%Y')} to {to_date.strftime('%d-%m-%Y')})")
        
        st.markdown("### 📈 INCOME")
        
        income_items = []
        
        interest_earned = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM transactions
            WHERE description LIKE '%interest%' AND transaction_type='CREDIT'
            AND DATE(created_at) BETWEEN ? AND ?
        """, (from_date, to_date)).fetchone()[0]
        income_items.append(('Interest Earned', interest_earned))
        
        fees = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM transactions
            WHERE (description LIKE '%fee%' OR description LIKE '%charge%') 
            AND transaction_type='CREDIT'
            AND DATE(created_at) BETWEEN ? AND ?
        """, (from_date, to_date)).fetchone()[0]
        income_items.append(('Fees & Charges', fees))
        
        other_income = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM transactions
            WHERE transaction_type='CREDIT' 
            AND description NOT LIKE '%interest%'
            AND description NOT LIKE '%fee%'
            AND description NOT LIKE '%charge%'
            AND description NOT LIKE '%deposit%'
            AND DATE(created_at) BETWEEN ? AND ?
        """, (from_date, to_date)).fetchone()[0]
        income_items.append(('Other Income', other_income))
        
        for item, amount in income_items:
            st.write(f"• {item}: **₹{amount:,.2f}**")
        
        total_income = sum(item[1] for item in income_items)
        st.markdown(f"### **Total Income: ₹{total_income:,.2f}**")
        
        st.divider()
        
        st.markdown("### 📉 EXPENSES")
        
        expense_items = []
        
        interest_paid = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM transactions
            WHERE (description LIKE '%interest%' OR reference_type='INTEREST') 
            AND transaction_type='DEBIT'
            AND DATE(created_at) BETWEEN ? AND ?
        """, (from_date, to_date)).fetchone()[0]
        expense_items.append(('Interest Paid', interest_paid))
        
        operating = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM transactions
            WHERE (description LIKE '%expense%' OR description LIKE '%salary%' 
                   OR description LIKE '%rent%' OR description LIKE '%utility%')
            AND transaction_type='DEBIT'
            AND DATE(created_at) BETWEEN ? AND ?
        """, (from_date, to_date)).fetchone()[0]
        expense_items.append(('Operating Expenses', operating))
        
        other_expenses = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM transactions
            WHERE transaction_type='DEBIT'
            AND description NOT LIKE '%interest%'
            AND description NOT LIKE '%expense%'
            AND description NOT LIKE '%salary%'
            AND description NOT LIKE '%rent%'
            AND description NOT LIKE '%utility%'
            AND description NOT LIKE '%withdrawal%'
            AND reference_type != 'INTEREST'
            AND DATE(created_at) BETWEEN ? AND ?
        """, (from_date, to_date)).fetchone()[0]
        expense_items.append(('Other Expenses', other_expenses))
        
        for item, amount in expense_items:
            st.write(f"• {item}: **₹{amount:,.2f}**")
        
        total_expenses = sum(item[1] for item in expense_items)
        st.markdown(f"### **Total Expenses: ₹{total_expenses:,.2f}**")
        
        st.divider()
        
        net_profit = total_income - total_expenses
        
        if net_profit >= 0:
            st.success(f"## 🎉 Net Profit: ₹{net_profit:,.2f}")
        else:
            st.error(f"## 📉 Net Loss: ₹{abs(net_profit):,.2f}")
        
        fig = go.Figure(data=[go.Pie(labels=['Income', 'Expenses'], 
                                     values=[total_income, total_expenses],
                                     hole=.3)])
        fig.update_layout(title='Income vs Expenses')
        st.plotly_chart(fig, use_container_width=True)
    
    conn.close()

def show_reports():
    st.markdown('<h1 class="main-header">📋 Reports</h1>', unsafe_allow_html=True)
    
    report_type = st.selectbox("Select Report Type", [
        "Customer Master List",
        "Account Statement Summary",
        "FD Maturity Report",
        "RD Installment Report",
        "Transaction Summary",
        "KYC Status Report",
        "Daily Transaction Report",
        "Interest Calculation Report"
    ])
    
    conn = get_db()
    
    if report_type == "Customer Master List":
        st.subheader("Customer Master List")
        customers = conn.execute("""
            SELECT customer_id, first_name, last_name, email, phone, city, 
                   kyc_status, created_at
            FROM customers ORDER BY created_at DESC
        """).fetchall()
        
        if customers:
            df = pd.DataFrame(customers, columns=['ID', 'First Name', 'Last Name', 'Email', 
                                                  'Phone', 'City', 'KYC', 'Registration Date'])
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False)
            st.download_button("📥 Download CSV", csv, "customer_list.csv", "text/csv")
    
    elif report_type == "FD Maturity Report":
        st.subheader("FD Maturity Report")
        fds = conn.execute("""
            SELECT fd.fd_number, c.first_name || ' ' || c.last_name as name,
                   fd.principal_amount, fd.maturity_amount, fd.start_date,
                   fd.maturity_date, fd.status
            FROM fixed_deposits fd
            JOIN accounts a ON fd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            ORDER BY fd.maturity_date
        """).fetchall()
        
        if fds:
            df = pd.DataFrame(fds, columns=['FD No', 'Customer', 'Principal', 
                                           'Maturity Amt', 'Start Date', 'Maturity Date', 'Status'])
            st.dataframe(df.style.format({
                'Principal': '₹{:,.2f}',
                'Maturity Amt': '₹{:,.2f}'
            }), use_container_width=True)
    
    elif report_type == "Interest Calculation Report":
        st.subheader("Interest Calculation Report")
        calcs = conn.execute("""
            SELECT ic.calculation_date, a.account_number, 
                   c.first_name || ' ' || c.last_name as customer,
                   ic.principal_amount, ic.interest_rate, ic.interest_earned, ic.days_calculated
            FROM interest_calculations ic
            JOIN accounts a ON ic.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            ORDER BY ic.calculation_date DESC
        """).fetchall()
        
        if calcs:
            df = pd.DataFrame(calcs, columns=['Date', 'Account', 'Customer', 'Principal', 
                                             'Rate', 'Interest', 'Days'])
            st.dataframe(df.style.format({
                'Principal': '₹{:,.2f}',
                'Rate': '{:.2f}%',
                'Interest': '₹{:,.2f}'
            }), use_container_width=True)
    
    elif report_type == "Daily Transaction Report":
        st.subheader("Daily Transaction Report")
        report_date = st.date_input("Select Date", date.today())
        
        transactions = conn.execute("""
            SELECT t.transaction_id, c.first_name || ' ' || c.last_name as customer,
                   a.account_type, t.transaction_type, t.amount, t.voucher_number, t.created_at
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            WHERE DATE(t.created_at) = ?
            ORDER BY t.created_at DESC
        """, (report_date,)).fetchall()
        
        if transactions:
            df = pd.DataFrame(transactions, columns=['Txn ID', 'Customer', 'Account Type',
                                                      'Type', 'Amount', 'Voucher', 'Time'])
            st.dataframe(df.style.format({'Amount': '₹{:,.2f}'}), use_container_width=True)
        else:
            st.info(f"No transactions on {report_date}")
    
    conn.close()

# ==================== MAIN ====================

if __name__ == "__main__":
    main()


