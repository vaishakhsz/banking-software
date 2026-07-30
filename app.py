# 🏦 AASHA NIDHI PVT LIMITED BANK - COMPLETE SYSTEM
# With Chart of Accounts, Interest Rate Settings, Customer-wise Income/Expense

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
        
        # Check if closed_date and closed_amount columns exist in fixed_deposits
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
        
        # Interest Rate History table
        c.execute('''CREATE TABLE IF NOT EXISTS interest_rate_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rate DECIMAL(5,2) NOT NULL,
            effective_from DATE NOT NULL,
            changed_by INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (changed_by) REFERENCES users (id)
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
        
        # Insert default settings if not exists
        c.execute("""
            INSERT OR IGNORE INTO system_settings (key, value, description)
            VALUES ('SB_INTEREST_RATE', '3.5', 'SB Account Interest Rate (%)')
        """)
        
        # Insert default Chart of Accounts
        default_accounts = [
            # Income Accounts
            ('INC001', 'Interest Income', 'Income', 'Banking Income'),
            ('INC002', 'Commission Income', 'Income', 'Banking Income'),
            ('INC003', 'Fees & Charges', 'Income', 'Banking Income'),
            ('INC004', 'Processing Fees', 'Income', 'Banking Income'),
            ('INC005', 'Other Income', 'Income', 'Other Income'),
            
            # Expense Accounts - Operating
            ('EXP001', 'Salaries & Wages', 'Expense', 'Operating Expenses'),
            ('EXP002', 'Rent & Utilities', 'Expense', 'Operating Expenses'),
            ('EXP003', 'Electricity Charges', 'Expense', 'Operating Expenses'),
            ('EXP004', 'Water Charges', 'Expense', 'Operating Expenses'),
            ('EXP005', 'Internet & Telephone', 'Expense', 'Operating Expenses'),
            
            # Expense Accounts - Administrative
            ('EXP006', 'Printing & Stationary', 'Expense', 'Administrative Expenses'),
            ('EXP007', 'Postage & Courier', 'Expense', 'Administrative Expenses'),
            ('EXP008', 'Office Supplies', 'Expense', 'Administrative Expenses'),
            ('EXP009', 'Conveyance', 'Expense', 'Administrative Expenses'),
            ('EXP010', 'Travel Expenses', 'Expense', 'Administrative Expenses'),
            
            # Expense Accounts - Other
            ('EXP011', 'Bank Charges', 'Expense', 'Other Expenses'),
            ('EXP012', 'Insurance', 'Expense', 'Other Expenses'),
            ('EXP013', 'Maintenance', 'Expense', 'Other Expenses'),
            ('EXP014', 'Professional Fees', 'Expense', 'Other Expenses'),
            ('EXP015', 'Other Expenses', 'Expense', 'Other Expenses'),
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
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4]}"

def generate_account_number(account_type):
    prefix = '100' if account_type == 'SB' else '200' if account_type == 'FD' else '300' if account_type == 'RD' else '400'
    return f"{prefix}{datetime.now().strftime('%y%m%d')}{str(uuid.uuid4().int)[:6]}"

def generate_voucher_number(voucher_type):
    prefix = 'PMT' if voucher_type == 'PAYMENT' else 'RCT' if voucher_type == 'RECEIPT' else 'JNL'
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M')}{str(uuid.uuid4().int)[:4]}"

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
    """Get the current SB interest rate from settings"""
    c = get_db()
    rate = c.execute("""
        SELECT value FROM system_settings WHERE key = 'SB_INTEREST_RATE'
    """).fetchone()
    c.close()
    
    if rate:
        return float(rate[0])
    return 3.5  # Default if not found

def calculate_fd_maturity(principal, rate, months):
    return round(principal * (1 + rate/400) ** (months/3), 2)

def calculate_rd_maturity(monthly, rate, months):
    return round(monthly * (((1 + rate/400) ** (months/3) - 1) / (1 - (1 + rate/400) ** (-1/3))), 2)

def calculate_sb_interest(balance, rate, days):
    return 0 if balance <= 0 else round((balance * rate * days) / (100 * 365), 2)

# ==================== RETRIEVAL ACCOUNT FUNCTIONS ====================

def get_retrieval_account(customer_id):
    """Get or create a retrieval account for a customer"""
    conn = get_db()
    try:
        acc = conn.execute("""
            SELECT id, account_number, balance 
            FROM retrieval_accounts 
            WHERE customer_id = ? AND status = 'ACTIVE'
        """, (customer_id,)).fetchone()
        
        if acc:
            conn.close()
            return acc[0], acc[1], acc[2]
        
        account_number = f"RET{datetime.now().strftime('%y%m%d')}{str(uuid.uuid4().int)[:6]}"
        
        conn.execute("""
            INSERT INTO retrieval_accounts (account_number, customer_id, balance)
            VALUES (?, ?, 0)
        """, (account_number, customer_id))
        
        acc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()
        
        return acc_id, account_number, 0
    except Exception as e:
        conn.close()
        raise e

def add_to_retrieval_account(customer_id, deposit_type, deposit_number, principal, interest, maturity_date):
    """Add matured deposit to retrieval account"""
    conn = None
    try:
        acc_id, acc_number, current_balance = get_retrieval_account(customer_id)
        
        total_amount = principal + interest
        
        conn = get_db()
        
        new_balance = current_balance + total_amount
        conn.execute("""
            UPDATE retrieval_accounts 
            SET balance = ? 
            WHERE id = ?
        """, (new_balance, acc_id))
        
        deposit_id = generate_id('MAT')
        conn.execute("""
            INSERT INTO matured_deposits (
                deposit_id, customer_id, original_deposit_type,
                original_deposit_number, principal_amount, interest_earned,
                total_amount, maturity_date, deposited_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, DATE('now'))
        """, (deposit_id, customer_id, deposit_type, deposit_number, 
              principal, interest, total_amount, maturity_date))
        
        conn.execute("""
            INSERT INTO transactions (
                transaction_id, account_id, transaction_type,
                amount, balance_after, description,
                reference_type, voucher_type, voucher_number,
                created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            generate_id('TXN'), acc_id, 'CREDIT',
            total_amount, new_balance,
            f"{deposit_type} Maturity: {deposit_number}",
            'MATURITY', 'RECEIPT',
            generate_voucher_number('RECEIPT'),
            st.session_state.user['id']
        ))
        
        conn.commit()
        conn.close()
        return acc_number, new_balance
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        raise e

def transfer_to_sb(customer_id, amount, sb_account_id):
    """Transfer from retrieval account to SB account"""
    conn = get_db()
    
    try:
        ret_acc = conn.execute("""
            SELECT id, account_number, balance 
            FROM retrieval_accounts 
            WHERE customer_id = ? AND status = 'ACTIVE'
        """, (customer_id,)).fetchone()
        
        if not ret_acc:
            conn.close()
            return None, "No retrieval account found"
        
        if ret_acc[2] < amount:
            conn.close()
            return None, "Insufficient balance in retrieval account"
        
        sb_acc = conn.execute("""
            SELECT balance FROM accounts WHERE id = ?
        """, (sb_account_id,)).fetchone()
        
        if not sb_acc:
            conn.close()
            return None, "SB account not found"
        
        new_ret_balance = ret_acc[2] - amount
        conn.execute("""
            UPDATE retrieval_accounts 
            SET balance = ? 
            WHERE id = ?
        """, (new_ret_balance, ret_acc[0]))
        
        new_sb_balance = sb_acc[0] + amount
        conn.execute("""
            UPDATE accounts 
            SET balance = ? 
            WHERE id = ?
        """, (new_sb_balance, sb_account_id))
        
        conn.execute("""
            INSERT INTO transactions (
                transaction_id, account_id, transaction_type,
                amount, balance_after, description,
                reference_type, voucher_type, voucher_number,
                created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            generate_id('TXN'), ret_acc[0], 'DEBIT',
            amount, new_ret_balance,
            "Transfer to SB Account",
            'TRANSFER', 'PAYMENT',
            generate_voucher_number('PAYMENT'),
            st.session_state.user['id']
        ))
        
        conn.execute("""
            INSERT INTO transactions (
                transaction_id, account_id, transaction_type,
                amount, balance_after, description,
                reference_type, voucher_type, voucher_number,
                created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            generate_id('TXN'), sb_account_id, 'CREDIT',
            amount, new_sb_balance,
            "Transfer from Retrieval Account",
            'TRANSFER', 'RECEIPT',
            generate_voucher_number('RECEIPT'),
            st.session_state.user['id']
        ))
        
        conn.commit()
        conn.close()
        return new_ret_balance, new_sb_balance
        
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e

# ==================== PDF GENERATION ====================
def create_pdf(title, content, filename):
    """Generate PDF with proper formatting"""
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
        pdf.cell(190, 6, f'Date: {datetime.now().strftime("%d-%m-%Y %I:%M %p")}', 0, 1, 'C')
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
        pdf.cell(190, 10, f'Generated on: {datetime.now().strftime("%d-%m-%Y %I:%M %p")}', 0, 1, 'C')
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
            kyc_emoji = "✅" if cust[3] == 'VERIFIED' else "⏳"
            display = f"{kyc_emoji} {cust[2]} | A/c: {cust[5]} | Bal: Rs{total_balance:,.2f} | KYC: {cust[3]}"
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
        
        * {
            font-family: 'Plus Jakarta Sans', sans-serif;
        }
        
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
        }
        
        .main-header h1 {
            margin: 0;
            font-size: 1.8rem;
            font-weight: 800;
        }
        
        .main-header small {
            opacity: 0.8;
            font-size: 0.9rem;
        }
        
        .bank-logo {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .bank-logo-icon {
            font-size: 2.5rem;
        }
        
        .stButton > button {
            border-radius: 10px !important;
            font-weight: 700 !important;
            transition: all 0.3s ease !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.15) !important;
        }
        
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #0f2027, #2c5364) !important;
            color: white !important;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 8px 16px;
            background: #f0f2f6;
            font-weight: 600;
        }
        
        .stTabs [aria-selected="true"] {
            background: #0f2027 !important;
            color: white !important;
        }
        
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f2027, #203a43) !important;
        }
        
        [data-testid="stSidebar"] .stButton > button {
            color: white !important;
            background: transparent !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            text-align: left !important;
            justify-content: flex-start !important;
        }
        
        [data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(255,255,255,0.1) !important;
            border-color: rgba(255,255,255,0.3) !important;
        }
        
        .sidebar-logo {
            text-align: center;
            padding: 20px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 20px;
        }
        
        .sidebar-logo h2 {
            color: white;
            margin: 0;
            font-size: 1.2rem;
            font-weight: 700;
        }
        
        .sidebar-logo p {
            color: rgba(255,255,255,0.6);
            font-size: 0.8rem;
            margin: 0;
        }
        
        .sidebar-logo .logo-icon {
            font-size: 3rem;
            display: block;
            margin-bottom: 5px;
        }
        
        .stDataFrame {
            border-radius: 12px !important;
            overflow: hidden !important;
        }
        
        .stMetric {
            background: white;
            padding: 1rem;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
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
    st.markdown("""
    <div style="display:flex;justify-content:center;align-items:center;min-height:80vh">
        <div style="background:white;padding:3rem;border-radius:24px;text-align:center;max-width:400px;box-shadow:0 20px 60px rgba(0,0,0,0.1)">
            <div style="font-size:4rem;margin-bottom:0">🏦</div>
            <h1 style="font-size:1.8rem;font-weight:800;margin:0.5rem 0">AASHA NIDHI BANK</h1>
            <p style="color:#6c757d;margin-bottom:2rem">Balaramapuram</p>
    """, unsafe_allow_html=True)
    
    username = st.text_input("👤 Username", placeholder="Enter your username")
    password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🚀 Sign In", use_container_width=True, type="primary"):
            user = login_user(username, password)
            if user:
                st.session_state.user = {
                    'id': user[0],
                    'username': user[1],
                    'role': user[3]
                }
                st.rerun()
            else:
                st.error("❌ Invalid credentials! Please try again.")
        
        st.markdown("""
        <div style="margin-top:1rem;padding:1rem;background:#f8f9fa;border-radius:12px">
            <small style="color:#6c757d">
                🔑 Demo: <strong>admin</strong> / <strong>admin123</strong>
            </small>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div></div>", unsafe_allow_html=True)

def show_app():
    # Header
    st.markdown(f"""
    <div class="main-header">
        <div class="bank-logo">
            <span class="bank-logo-icon">🏦</span>
            <div>
                <h1>AASHA NIDHI PVT LIMITED BANK</h1>
                <small>📍 BALARAMAPURAM • {datetime.now().strftime('%d-%m-%Y %I:%M %p')}</small>
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
    
    # Sidebar
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
            'interest_rate_settings': '📈 Interest Rate',
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
        
        st.markdown("""
        <div style="position:fixed;bottom:1rem;left:1rem;right:1rem;text-align:center;color:rgba(255,255,255,0.4);font-size:0.7rem;padding:10px;">
            © 2024 Aasha Nidhi Bank<br>
            v3.0
        </div>
        """, unsafe_allow_html=True)
    
    # Page routing
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
    elif page == 'interest_rate_settings':
        interest_rate_settings()
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
    total_retrieval = c.execute("SELECT COALESCE(SUM(balance),0) FROM retrieval_accounts WHERE status='ACTIVE'").fetchone()[0]
    current_rate = get_current_sb_interest_rate()
    
    c.close()
    
    st.markdown("### 📊 Bank Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Total Customers", f"{total_customers:,}")
        st.metric("✅ KYC Verified", f"{total_customers - pending_kyc:,}")
    
    with col2:
        st.metric("🏦 SB Accounts", f"{total_sb_accounts:,}")
        st.metric("💰 SB Deposits", f"Rs {total_sb_balance:,.2f}")
    
    with col3:
        st.metric("📈 FD Deposits", f"Rs {total_fd:,.2f}")
        st.metric("🔄 RD Deposits", f"Rs {total_rd:,.2f}")
    
    with col4:
        st.metric("💹 Interest Earned", f"Rs {total_interest:,.2f}")
        st.metric("💰 Retrieval Balance", f"Rs {total_retrieval:,.2f}")
    
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
        df = pd.DataFrame(recent_txns, columns=['Txn ID', 'Customer', 'Type', 'Amount', 'Time'])
        st.dataframe(df.style.format({'Amount': 'Rs {:,.2f}'}), use_container_width=True)
    else:
        st.info("No recent transactions")

# ==================== CUSTOMER MANAGEMENT ====================
def customer_management():
    tab1, tab2 = st.tabs(["📝 Register Customer", "👥 View Customers"])
    
    with tab1:
        st.markdown("### 📝 Register New Customer")
        with st.form("register_customer"):
            col1, col2 = st.columns(2)
            
            with col1:
                first_name = st.text_input("👤 First Name*", placeholder="Enter first name")
                last_name = st.text_input("👤 Last Name*", placeholder="Enter last name")
                dob = st.date_input("🎂 Date of Birth*", min_value=date(1900, 1, 1), max_value=date.today())
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
            df = pd.DataFrame(customers, columns=['ID', 'Customer ID', 'First', 'Last', 'Email', 'Phone', 'KYC', 'Status', 'Created'])
            st.dataframe(df[['Customer ID', 'First', 'Last', 'Email', 'Phone', 'Status', 'KYC']], use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📥 Export to CSV",
                    df.to_csv(index=False),
                    "customers.csv",
                    "text/csv"
                )
            
            with col2:
                with st.expander("🗑️ Delete Customer"):
                    delete_id = st.text_input("Enter Customer ID to delete:")
                    if delete_id:
                        if st.button("🗑️ Delete Customer", use_container_width=True, type="secondary"):
                            if st.checkbox("☑️ Confirm delete? This cannot be undone!"):
                                try:
                                    conn = get_db()
                                    customer = conn.execute("SELECT id FROM customers WHERE customer_id=?", (delete_id,)).fetchone()
                                    if customer:
                                        conn.execute("DELETE FROM accounts WHERE customer_id=?", (customer[0],))
                                        conn.execute("DELETE FROM fixed_deposits WHERE account_id IN (SELECT id FROM accounts WHERE customer_id=?)", (customer[0],))
                                        conn.execute("DELETE FROM recurring_deposits WHERE account_id IN (SELECT id FROM accounts WHERE customer_id=?)", (customer[0],))
                                        conn.execute("DELETE FROM retrieval_accounts WHERE customer_id=?", (customer[0],))
                                        conn.execute("DELETE FROM matured_deposits WHERE customer_id=?", (customer[0],))
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
        with st.expander(f"{'⏳' if cust[12]=='PENDING' else '✅'} {cust[3]} {cust[4]} (ID: {cust[2]})"):
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
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ Approve KYC", key=f"approve_{cust[0]}", use_container_width=True):
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
                if st.button("❌ Reject KYC", key=f"reject_{cust[0]}", use_container_width=True):
                    c.execute("UPDATE customers SET kyc_status='REJECTED' WHERE id=?", (cust[0],))
                    c.commit()
                    st.warning(f"❌ KYC Rejected for {cust[3]} {cust[4]}")
                    st.rerun()
    
    c.close()

# ==================== CREATE SB ACCOUNT ====================
def create_sb_account():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    
    # Get current interest rate
    current_rate = get_current_sb_interest_rate()
    
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
    
    options = []
    for cust in customers:
        kyc_emoji = "✅" if cust[3] == 'VERIFIED' else "⏳"
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
                    step=0.25,
                    help="Default is the system interest rate"
                )
                opening_balance = st.number_input(
                    "💰 Opening Balance (Rs)",
                    min_value=0.0,
                    step=100.0,
                    value=500.0
                )
            
            with col2:
                mode = st.selectbox(
                    "💳 Funding Mode",
                    ["CASH", "BANK TRANSFER", "CHEQUE", "ONLINE"]
                )
                nominee = st.text_input("👤 Nominee Name (Optional)")
            
            if cust[3] != 'VERIFIED':
                st.warning("⚠️ Customer KYC is pending. Account can still be opened but KYC verification is recommended.")
            
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
                    - Opening Balance: **Rs {opening_balance:,.2f}**
                    - Interest Rate: **{interest_rate}%**
                    """)
                    st.balloons()
                    
                except Exception as e:
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
        
        cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
            "👤 Select Customer Account",
            "txn_customer"
        )
        
        if cust_id and acc_id:
            st.success(f"""
            ✅ **Selected Account:**
            - Customer: **{cust_name}**
            - Account: **{acc_number}**
            - Balance: **Rs {balance:,.2f}**
            """)
            
            with st.form("transaction_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    transaction_type = st.radio(
                        "📊 Transaction Type",
                        ["💰 Deposit", "💳 Withdraw"],
                        horizontal=True
                    )
                
                with col2:
                    amount = st.number_input(
                        "💵 Amount (Rs)",
                        min_value=1.0,
                        step=100.0
                    )
                
                mode = st.selectbox(
                    "💳 Payment Mode",
                    ["CASH", "BANK TRANSFER", "CHEQUE", "ONLINE"]
                )
                description = st.text_input("📝 Description", placeholder="Transaction details")
                
                if st.form_submit_button("✅ Process Transaction", use_container_width=True, type="primary"):
                    if transaction_type == "💳 Withdraw" and amount > balance:
                        st.error("❌ Insufficient balance!")
                    else:
                        conn = get_db()
                        try:
                            txn_type = "DEBIT" if transaction_type == "💳 Withdraw" else "CREDIT"
                            new_balance = balance - amount if txn_type == "DEBIT" else balance + amount
                            voucher_type = "PAYMENT" if txn_type == "DEBIT" else "RECEIPT"
                            
                            conn.execute("""
                                INSERT INTO transactions (
                                    transaction_id, account_id, transaction_type,
                                    amount, balance_after, description,
                                    reference_type, voucher_type, voucher_number,
                                    created_by
                                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                            """, (
                                generate_id('TXN'), acc_id, txn_type,
                                amount, new_balance, description or f"{transaction_type}",
                                mode, voucher_type, generate_voucher_number(voucher_type),
                                st.session_state.user['id']
                            ))
                            
                            conn.execute("UPDATE accounts SET balance=? WHERE id=?", (new_balance, acc_id))
                            conn.commit()
                            conn.close()
                            
                            st.success(f"""
                            ✅ Transaction Successful! 🎉
                            
                            📋 **Details:**
                            - Type: **{transaction_type}**
                            - Amount: **Rs {amount:,.2f}**
                            - New Balance: **Rs {new_balance:,.2f}**
                            """)
                            st.rerun()
                            
                        except Exception as e:
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
            df = pd.DataFrame(accounts, columns=['ID', 'Account', 'Customer', 'Balance', 'Interest', 'Rate', 'Status', 'KYC'])
            st.dataframe(
                df.style.format({
                    'Balance': 'Rs {:,.2f}',
                    'Interest': 'Rs {:,.2f}',
                    'Rate': '{:.2f}%'
                }),
                use_container_width=True
            )
            
            total_balance = df['Balance'].sum()
            total_interest = df['Interest'].sum()
            st.info(f"💰 Total SB Deposits: Rs {total_balance:,.2f} | Total Interest: Rs {total_interest:,.2f}")
            
            with st.expander("🗑️ Delete SB Account"):
                acc_num = st.text_input("Enter Account Number to delete:")
                if acc_num:
                    if st.button("🗑️ Delete Account", use_container_width=True, type="secondary"):
                        if st.checkbox("☑️ Confirm delete? This cannot be undone!"):
                            try:
                                conn = get_db()
                                acc = conn.execute("SELECT id FROM accounts WHERE account_number=?", (acc_num,)).fetchone()
                                if acc:
                                    conn.execute("DELETE FROM transactions WHERE account_id=?", (acc[0],))
                                    conn.execute("DELETE FROM accounts WHERE account_number=?", (acc_num,))
                                    conn.commit()
                                    conn.close()
                                    st.success("✅ Account deleted successfully!")
                                    st.rerun()
                                else:
                                    st.error("❌ Account not found!")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
        else:
            st.info("No SB accounts found")
    
    with tab3:
        st.markdown("### 📋 Account Statement")
        
        cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
            "👤 Select Customer for Statement",
            "stmt_customer"
        )
        
        if cust_id and acc_id:
            col1, col2 = st.columns(2)
            with col1:
                from_date = st.date_input("📅 From Date", date.today() - timedelta(days=30))
            with col2:
                to_date = st.date_input("📅 To Date", date.today())
            
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
                    df = pd.DataFrame(transactions, columns=['ID', 'Type', 'Amount', 'Balance', 'Description', 'Mode', 'Date'])
                    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%d-%m-%Y %I:%M %p')
                    
                    st.dataframe(
                        df.style.format({
                            'Amount': 'Rs {:,.2f}',
                            'Balance': 'Rs {:,.2f}'
                        }),
                        use_container_width=True
                    )
                    
                    total_credit = df[df['Type'] == 'CREDIT']['Amount'].sum()
                    total_debit = df[df['Type'] == 'DEBIT']['Amount'].sum()
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Credits", f"Rs {total_credit:,.2f}")
                    col2.metric("Total Debits", f"Rs {total_debit:,.2f}")
                    col3.metric("Net Change", f"Rs {(total_credit - total_debit):,.2f}")
                    
                    st.download_button(
                        "📥 Download Statement",
                        df.to_csv(index=False),
                        f"statement_{acc_number}_{from_date}_{to_date}.csv",
                        "text/csv"
                    )
                else:
                    st.info("No transactions in this period")
    
    c.close()

# ==================== FIXED DEPOSITS ====================
def fixed_deposits():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Open FD", "📊 Active FDs", "🔒 Close FD", "📋 Closed FDs"])
    
    # Tab 1: Open FD
    with tab1:
        st.markdown("### 📝 Open Fixed Deposit")
        
        cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
            "👤 Select Customer for FD",
            "fd_customer"
        )
        
        if cust_id and acc_id:
            st.success(f"""
            ✅ **Selected Customer:**
            - 👤 Name: **{cust_name}**
            - 🏦 Account: **{acc_number}**
            - 💰 Balance: **Rs {balance:,.2f}**
            """)
            
            with st.form("fd_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    principal = st.number_input(
                        "💰 Principal Amount",
                        min_value=1000.0,
                        step=1000.0,
                        value=10000.0
                    )
                    
                    tenure = st.selectbox(
                        "📅 Tenure (Months)",
                        [1, 3, 6, 9, 12, 18, 24, 36, 48, 60]
                    )
                
                with col2:
                    interest_rate = st.number_input(
                        "📈 Interest Rate (%)",
                        min_value=3.0,
                        max_value=10.0,
                        value=6.5,
                        step=0.25
                    )
                    
                    start_date = st.date_input(
                        "📆 Start Date",
                        date.today()
                    )
                
                maturity_date = start_date + relativedelta(months=tenure)
                maturity_amount = calculate_fd_maturity(principal, interest_rate, tenure)
                interest_earned = maturity_amount - principal
                
                st.info(f"""
                📊 **FD Summary:**
                - Maturity Date: **{maturity_date.strftime('%d-%m-%Y')}**
                - Maturity Amount: **Rs {maturity_amount:,.2f}**
                - Interest Earned: **Rs {interest_earned:,.2f}**
                """)
                
                funding_mode = st.radio(
                    "💳 Funding Mode",
                    ["SB Transfer (Debit from SB)", "Cash", "Bank Transfer", "Cheque"],
                    horizontal=True
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    nominee_name = st.text_input("👤 Nominee Name (Optional)")
                with col2:
                    nominee_relation = st.text_input("🤝 Relationship (Optional)")
                
                if funding_mode == "SB Transfer (Debit from SB)" and principal > balance:
                    st.error(f"❌ Insufficient balance! Available: Rs {balance:,.2f}")
                
                if st.form_submit_button("✅ Open FD", use_container_width=True, type="primary"):
                    if funding_mode == "SB Transfer (Debit from SB)" and principal > balance:
                        st.error("❌ Insufficient balance!")
                    else:
                        conn = get_db()
                        try:
                            fd_number = generate_id('FD')
                            fd_account_number = generate_account_number('FD')
                            
                            conn.execute("""
                                INSERT INTO accounts (
                                    account_number, customer_id, account_type,
                                    balance, interest_rate
                                ) VALUES (?,?,?,0.00,?)
                            """, (fd_account_number, cust_id, 'FD', interest_rate))
                            
                            fd_account_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                            
                            conn.execute("""
                                INSERT INTO fixed_deposits (
                                    fd_number, account_id, principal_amount,
                                    interest_rate, start_date, maturity_date,
                                    maturity_amount, tenure_months, nominee_name,
                                    nominee_relation
                                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                            """, (
                                fd_number, fd_account_id, principal,
                                interest_rate, start_date, maturity_date,
                                maturity_amount, tenure, nominee_name,
                                nominee_relation
                            ))
                            
                            if funding_mode == "SB Transfer (Debit from SB)":
                                new_balance = balance - principal
                                conn.execute("UPDATE accounts SET balance=? WHERE id=?", (new_balance, acc_id))
                                conn.execute("""
                                    INSERT INTO transactions (
                                        transaction_id, account_id, transaction_type,
                                        amount, balance_after, description,
                                        reference_type, voucher_type, voucher_number,
                                        created_by
                                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                                """, (
                                    generate_id('TXN'), acc_id, 'DEBIT',
                                    principal, new_balance,
                                    f"FD Transfer to {fd_number}",
                                    'SB_TRANSFER', 'PAYMENT',
                                    generate_voucher_number('PAYMENT'),
                                    st.session_state.user['id']
                                ))
                            
                            conn.execute("""
                                INSERT INTO transactions (
                                    transaction_id, account_id, transaction_type,
                                    amount, balance_after, description,
                                    reference_type, voucher_type, voucher_number,
                                    created_by
                                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                            """, (
                                generate_id('TXN'), fd_account_id, 'CREDIT',
                                principal, principal,
                                f"FD Opening: {fd_number}",
                                funding_mode, 'RECEIPT',
                                generate_voucher_number('RECEIPT'),
                                st.session_state.user['id']
                            ))
                            
                            conn.commit()
                            conn.close()
                            
                            st.success(f"""
                            ✅ FD Opened Successfully! 🎉
                            
                            📋 **FD Details:**
                            - FD Number: **{fd_number}**
                            - Amount: **Rs {principal:,.2f}**
                            - Rate: **{interest_rate}%**
                            - Maturity: **{maturity_date.strftime('%d-%m-%Y')}**
                            - Maturity Amount: **Rs {maturity_amount:,.2f}**
                            """)
                            st.balloons()
                            
                        except Exception as e:
                            conn.rollback()
                            conn.close()
                            st.error(f"❌ Error: {str(e)}")
    
    # Tab 2: Active FDs
    with tab2:
        st.markdown("### 📊 Active Fixed Deposits")
        fds = c.execute("""
            SELECT fd.id, fd.fd_number, c.id as customer_id,
                   c.first_name||' '||c.last_name as customer,
                   a.id as sb_account_id, a.account_number as sb_account,
                   fd.principal_amount, fd.interest_rate, 
                   fd.start_date, fd.maturity_date,
                   fd.maturity_amount, fd.status,
                   CASE 
                       WHEN date('now') > fd.maturity_date THEN '🔴 Matured'
                       ELSE '🟢 Active'
                   END as maturity_status,
                   julianday('now') - julianday(fd.start_date) as days_elapsed,
                   julianday(fd.maturity_date) - julianday(fd.start_date) as total_days
            FROM fixed_deposits fd
            JOIN accounts a ON fd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            WHERE fd.status='ACTIVE'
            ORDER BY fd.maturity_date
        """).fetchall()
        
        if fds:
            fd_data = []
            for fd in fds:
                fd_id, fd_number, cust_id, customer, sb_acc_id, sb_acc, principal, rate, start, maturity, maturity_amount, status, maturity_status, days_elapsed, total_days = fd
                
                if days_elapsed > 0 and total_days > 0:
                    accrued_interest = (principal * rate * days_elapsed) / (100 * 365)
                    max_interest = maturity_amount - principal
                    accrued_interest = min(accrued_interest, max_interest)
                else:
                    accrued_interest = 0
                
                fd_data.append({
                    'ID': fd_id,
                    'FD No': fd_number,
                    'Customer': customer,
                    'SB Account': sb_acc,
                    'Principal': principal,
                    'Rate': rate,
                    'Start Date': start,
                    'Maturity Date': maturity,
                    'Maturity Amount': maturity_amount,
                    'Accrued Interest': accrued_interest,
                    'Total Value': principal + accrued_interest,
                    'Status': maturity_status,
                    'Days Elapsed': int(days_elapsed) if days_elapsed > 0 else 0
                })
            
            fd_df = pd.DataFrame(fd_data)
            st.dataframe(
                fd_df.style.format({
                    'Principal': 'Rs {:,.2f}',
                    'Rate': '{:.2f}%',
                    'Maturity Amount': 'Rs {:,.2f}',
                    'Accrued Interest': 'Rs {:,.2f}',
                    'Total Value': 'Rs {:,.2f}'
                }),
                use_container_width=True
            )
            
            total_fd = fd_df['Principal'].sum()
            total_interest = fd_df['Accrued Interest'].sum()
            total_value = fd_df['Total Value'].sum()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("💰 Total FD Investments", f"Rs {total_fd:,.2f}")
            col2.metric("📈 Accrued Interest", f"Rs {total_interest:,.2f}")
            col3.metric("💎 Total Value", f"Rs {total_value:,.2f}")
        else:
            st.info("No active fixed deposits")
    
    # Tab 3: Close FD
    with tab3:
        st.markdown("### 🔒 Close/Withdraw Fixed Deposit")
        
        active_fds = c.execute("""
            SELECT 
                fd.id, 
                fd.fd_number, 
                c.id as customer_id,
                c.first_name||' '||c.last_name as customer,
                fd.account_id as fd_account_id,
                a.account_number as fd_account_number,
                sb.id as sb_account_id,
                sb.account_number as sb_account,
                COALESCE(sb.balance, 0) as sb_balance,
                fd.principal_amount, 
                fd.interest_rate, 
                fd.start_date, 
                fd.maturity_date,
                fd.maturity_amount,
                julianday('now') - julianday(fd.start_date) as days_elapsed,
                julianday(fd.maturity_date) - julianday(fd.start_date) as total_days
            FROM fixed_deposits fd
            JOIN accounts a ON fd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            LEFT JOIN accounts sb ON c.id = sb.customer_id AND sb.account_type = 'SB' AND sb.status = 'ACTIVE'
            WHERE fd.status='ACTIVE'
            ORDER BY fd.maturity_date
        """).fetchall()
        
        if not active_fds:
            st.info("No active fixed deposits to close")
            c.close()
            return
        
        fd_options = []
        for fd in active_fds:
            fd_id, fd_number, cust_id, customer, fd_account_id, fd_account_number, sb_acc_id, sb_acc, sb_balance, principal, rate, start, maturity, maturity_amount, days_elapsed, total_days = fd
            
            if days_elapsed > 0 and total_days > 0:
                accrued_interest = (principal * rate * days_elapsed) / (100 * 365)
                max_interest = maturity_amount - principal
                accrued_interest = min(accrued_interest, max_interest)
            else:
                accrued_interest = 0
            
            total_value = principal + accrued_interest
            has_sb = sb_acc_id is not None
            
            fd_options.append({
                'display': f"{fd_number} - {customer} | {'✅' if has_sb else '❌'} SB: {sb_acc if sb_acc else 'No SB'} | Balance: Rs{sb_balance:,.2f} | Principal: Rs{principal:,.2f}",
                'fd_id': fd_id,
                'fd_number': fd_number,
                'customer_id': cust_id,
                'customer': customer,
                'fd_account_id': fd_account_id,
                'fd_account_number': fd_account_number,
                'sb_account_id': sb_acc_id,
                'sb_account': sb_acc if sb_acc else 'No SB Account',
                'sb_balance': sb_balance if sb_acc_id else 0,
                'principal': principal,
                'rate': rate,
                'start_date': start,
                'maturity_date': maturity,
                'maturity_amount': maturity_amount,
                'accrued_interest': accrued_interest,
                'total_value': total_value,
                'days_elapsed': int(days_elapsed) if days_elapsed > 0 else 0,
                'total_days': int(total_days) if total_days > 0 else 0,
                'is_matured': datetime.strptime(maturity, '%Y-%m-%d').date() <= date.today(),
                'has_sb': has_sb
            })
        
        selected_fd = st.selectbox(
            "📋 Select FD to Close",
            fd_options,
            format_func=lambda x: x['display']
        )
        
        if selected_fd:
            st.markdown("---")
            
            if selected_fd['has_sb']:
                st.success(f"✅ SB Account Found: {selected_fd['sb_account']} (Balance: Rs {selected_fd['sb_balance']:,.2f})")
            else:
                st.error("❌ No active SB account found for this customer!")
            
            st.markdown(f"""
            ### 📋 FD Details
            
            | Field | Value |
            |-------|-------|
            | **FD Number** | {selected_fd['fd_number']} |
            | **Customer** | {selected_fd['customer']} |
            | **FD Account** | {selected_fd['fd_account_number']} |
            | **SB Account** | {selected_fd['sb_account']} |
            | **SB Balance** | Rs {selected_fd['sb_balance']:,.2f} |
            | **Principal** | Rs {selected_fd['principal']:,.2f} |
            | **Interest Rate** | {selected_fd['rate']}% |
            | **Start Date** | {selected_fd['start_date']} |
            | **Maturity Date** | {selected_fd['maturity_date']} |
            | **Maturity Amount** | Rs {selected_fd['maturity_amount']:,.2f} |
            | **Days Elapsed** | {selected_fd['days_elapsed']} days |
            | **Accrued Interest** | Rs {selected_fd['accrued_interest']:,.2f} |
            | **Total Value** | Rs {selected_fd['total_value']:,.2f} |
            """)
            
            if selected_fd['is_matured']:
                st.success("✅ This FD has matured!")
                final_amount = selected_fd['total_value']
                penalty_applied = False
            else:
                st.warning(f"⚠️ Early Closure - Penalty applies!")
                penalty_rate = st.number_input(
                    "📉 Penalty Rate (%)",
                    min_value=0.0,
                    max_value=5.0,
                    value=1.0,
                    step=0.25
                )
                
                penalty_amount = (selected_fd['principal'] * penalty_rate * selected_fd['days_elapsed']) / (100 * 365)
                final_amount = selected_fd['total_value'] - penalty_amount
                penalty_applied = True
                
                st.info(f"""
                📊 **Early Closure Calculation:**
                - Accrued Interest: **Rs {selected_fd['accrued_interest']:,.2f}**
                - Penalty ({penalty_rate}%): **Rs {penalty_amount:,.2f}**
                - Final Payout: **Rs {final_amount:,.2f}**
                """)
            
            st.markdown("---")
            st.info("💰 **Amount will be deposited to Retrieval Account**")
            
            if st.button("🔒 Close FD", use_container_width=True, type="primary"):
                conn = None
                try:
                    conn = get_db()
                    conn.execute("""
                        UPDATE fixed_deposits 
                        SET status='CLOSED', 
                            closed_date=CURRENT_DATE, 
                            closed_amount=?
                        WHERE id=?
                    """, (final_amount, selected_fd['fd_id']))
                    conn.commit()
                    conn.close()
                    
                    ret_acc_number, new_ret_balance = add_to_retrieval_account(
                        selected_fd['customer_id'],
                        'FD',
                        selected_fd['fd_number'],
                        selected_fd['principal'],
                        selected_fd['accrued_interest'],
                        selected_fd['maturity_date']
                    )
                    
                    if selected_fd['accrued_interest'] > 0:
                        conn = get_db()
                        conn.execute("""
                            INSERT INTO income (
                                income_id, income_type, amount,
                                description, date, customer_id,
                                created_by
                            ) VALUES (?,?,?,?,?,?,?)
                        """, (
                            generate_id('INC'),
                            'Interest Earned',
                            selected_fd['accrued_interest'],
                            f"FD Interest: {selected_fd['fd_number']}",
                            date.today(),
                            selected_fd['customer_id'],
                            st.session_state.user['id']
                        ))
                        conn.commit()
                        conn.close()
                    
                    st.success(f"""
                    ✅ **FD Closed Successfully!** 🎉
                    
                    📋 **Closure Summary:**
                    - FD Number: **{selected_fd['fd_number']}**
                    - Customer: **{selected_fd['customer']}**
                    - Principal: **Rs {selected_fd['principal']:,.2f}**
                    - Interest Earned: **Rs {selected_fd['accrued_interest']:,.2f}**
                    - {'Penalty Applied' if penalty_applied else 'No Penalty'}
                    - Total Amount: **Rs {final_amount:,.2f}**
                    - 💰 **Deposited to Retrieval Account: {ret_acc_number}**
                    - Retrieval Balance: **Rs {new_ret_balance:,.2f}**
                    """)
                    st.balloons()
                    st.rerun()
                    
                except Exception as e:
                    if conn:
                        conn.rollback()
                        conn.close()
                    st.error(f"❌ Error closing FD: {str(e)}")
    
    # Tab 4: Closed FDs
    with tab4:
        st.markdown("### 📋 Closed Fixed Deposits")
        
        try:
            closed_fds = c.execute("""
                SELECT 
                    fd.fd_number, 
                    fd.principal_amount, 
                    fd.interest_rate,
                    fd.start_date, 
                    fd.maturity_date,
                    fd.maturity_amount, 
                    fd.closed_date,
                    COALESCE(fd.closed_amount, fd.maturity_amount) as closed_amount,
                    COALESCE(fd.closed_amount, fd.maturity_amount) - fd.principal_amount as interest_earned,
                    fd.status
                FROM fixed_deposits fd
                WHERE fd.status = 'CLOSED'
                ORDER BY fd.closed_date DESC
            """).fetchall()
            
            if closed_fds:
                df = pd.DataFrame(closed_fds, columns=[
                    'FD No', 'Principal', 'Rate', 
                    'Start Date', 'Maturity Date', 'Maturity Amount',
                    'Closed Date', 'Closed Amount', 'Interest Earned', 'Status'
                ])
                
                total_principal = df['Principal'].sum()
                total_closed = df['Closed Amount'].sum()
                total_interest = df['Interest Earned'].sum()
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("📊 Total Closed", f"{len(closed_fds)}")
                col2.metric("💰 Total Principal", f"Rs {total_principal:,.2f}")
                col3.metric("💎 Total Closed Amount", f"Rs {total_closed:,.2f}")
                col4.metric("📈 Total Interest", f"Rs {total_interest:,.2f}")
                
                st.markdown("---")
                
                st.dataframe(
                    df.style.format({
                        'Principal': 'Rs {:,.2f}',
                        'Maturity Amount': 'Rs {:,.2f}',
                        'Closed Amount': 'Rs {:,.2f}',
                        'Interest Earned': 'Rs {:,.2f}',
                        'Rate': '{:.2f}%'
                    }),
                    use_container_width=True
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "📥 Download Closed FDs CSV",
                        df.to_csv(index=False),
                        "closed_fixed_deposits.csv",
                        "text/csv"
                    )
                
                with col2:
                    with st.expander("🗑️ Delete FD Record"):
                        fd_num = st.text_input("Enter FD Number to delete:")
                        if fd_num:
                            if st.button("🗑️ Delete FD", use_container_width=True, type="secondary"):
                                if st.checkbox("☑️ Confirm delete? This cannot be undone!"):
                                    try:
                                        conn = get_db()
                                        fd = conn.execute("SELECT id FROM fixed_deposits WHERE fd_number=?", (fd_num,)).fetchone()
                                        if fd:
                                            conn.execute("DELETE FROM fixed_deposits WHERE fd_number=?", (fd_num,))
                                            conn.commit()
                                            conn.close()
                                            st.success("✅ FD record deleted successfully!")
                                            st.rerun()
                                        else:
                                            st.error("❌ FD not found!")
                                    except Exception as e:
                                        st.error(f"❌ Error: {str(e)}")
            else:
                st.info("No closed fixed deposits found")
                
        except Exception as e:
            st.error(f"❌ Error loading closed FDs: {str(e)}")
    
    c.close()

# ==================== RECURRING DEPOSITS ====================
def recurring_deposits():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Open RD", "📊 Active RDs", "💳 Pay Installment", "📋 Closed RDs"])
    
    # Tab 1: Open RD
    with tab1:
        st.markdown("### 📝 Open Recurring Deposit")
        
        cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
            "👤 Select Customer for RD",
            "rd_customer"
        )
        
        if cust_id and acc_id:
            st.success(f"""
            ✅ **Selected Customer:**
            - 👤 Name: **{cust_name}**
            - 🏦 Account: **{acc_number}**
            - 💰 Balance: **Rs {balance:,.2f}**
            """)
            
            with st.form("rd_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    monthly_amount = st.number_input(
                        "💰 Monthly Amount",
                        min_value=100.0,
                        step=100.0,
                        value=1000.0
                    )
                    
                    tenure = st.selectbox(
                        "📅 Tenure (Months)",
                        [3, 6, 9, 12, 18, 24, 36, 48, 60]
                    )
                
                with col2:
                    interest_rate = st.number_input(
                        "📈 Interest Rate (%)",
                        min_value=3.0,
                        max_value=10.0,
                        value=6.0,
                        step=0.25
                    )
                    
                    start_date = st.date_input(
                        "📆 Start Date",
                        date.today()
                    )
                
                maturity_date = start_date + relativedelta(months=tenure)
                maturity_amount = calculate_rd_maturity(monthly_amount, interest_rate, tenure)
                total_investment = monthly_amount * tenure
                interest_earned = maturity_amount - total_investment
                
                st.info(f"""
                📊 **RD Summary:**
                - Total Investment: **Rs {total_investment:,.2f}**
                - Maturity Date: **{maturity_date.strftime('%d-%m-%Y')}**
                - Maturity Amount: **Rs {maturity_amount:,.2f}**
                - Interest Earned: **Rs {interest_earned:,.2f}**
                - Installments: **{tenure} monthly payments**
                """)
                
                funding_mode = st.radio(
                    "💳 First Installment Funding",
                    ["SB Transfer (Debit from SB)", "Cash", "Bank Transfer", "Cheque"],
                    horizontal=True
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    nominee_name = st.text_input("👤 Nominee Name (Optional)")
                with col2:
                    nominee_relation = st.text_input("🤝 Relationship (Optional)")
                
                if funding_mode == "SB Transfer (Debit from SB)" and monthly_amount > balance:
                    st.error(f"❌ Insufficient balance for first installment! Available: Rs {balance:,.2f}")
                
                if st.form_submit_button("✅ Open RD", use_container_width=True, type="primary"):
                    if funding_mode == "SB Transfer (Debit from SB)" and monthly_amount > balance:
                        st.error("❌ Insufficient balance for first installment!")
                    else:
                        conn = get_db()
                        try:
                            rd_number = generate_id('RD')
                            rd_account_number = generate_account_number('RD')
                            
                            conn.execute("""
                                INSERT INTO accounts (
                                    account_number, customer_id, account_type,
                                    balance, interest_rate
                                ) VALUES (?,?,?,0.00,?)
                            """, (rd_account_number, cust_id, 'RD', interest_rate))
                            
                            rd_account_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                            
                            conn.execute("""
                                INSERT INTO recurring_deposits (
                                    rd_number, account_id, monthly_amount,
                                    interest_rate, start_date, maturity_date,
                                    maturity_amount, tenure_months, total_installments,
                                    installments_paid, nominee_name, nominee_relation
                                ) VALUES (?,?,?,?,?,?,?,?,?,1,?,?)
                            """, (
                                rd_number, rd_account_id, monthly_amount,
                                interest_rate, start_date, maturity_date,
                                maturity_amount, tenure, tenure,
                                nominee_name, nominee_relation
                            ))
                            
                            if funding_mode == "SB Transfer (Debit from SB)":
                                new_balance = balance - monthly_amount
                                conn.execute("UPDATE accounts SET balance=? WHERE id=?", (new_balance, acc_id))
                                conn.execute("""
                                    INSERT INTO transactions (
                                        transaction_id, account_id, transaction_type,
                                        amount, balance_after, description,
                                        reference_type, voucher_type, voucher_number,
                                        created_by
                                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                                """, (
                                    generate_id('TXN'), acc_id, 'DEBIT',
                                    monthly_amount, new_balance,
                                    f"RD Transfer to {rd_number}",
                                    'SB_TRANSFER', 'PAYMENT',
                                    generate_voucher_number('PAYMENT'),
                                    st.session_state.user['id']
                                ))
                            
                            conn.execute("""
                                INSERT INTO transactions (
                                    transaction_id, account_id, transaction_type,
                                    amount, balance_after, description,
                                    reference_type, voucher_type, voucher_number,
                                    created_by
                                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                            """, (
                                generate_id('TXN'), rd_account_id, 'CREDIT',
                                monthly_amount, monthly_amount,
                                f"RD Installment 1/{tenure}: {rd_number}",
                                funding_mode, 'RECEIPT',
                                generate_voucher_number('RECEIPT'),
                                st.session_state.user['id']
                            ))
                            
                            conn.commit()
                            conn.close()
                            
                            st.success(f"""
                            ✅ RD Opened Successfully! 🎉
                            
                            📋 **RD Details:**
                            - RD Number: **{rd_number}**
                            - Monthly Amount: **Rs {monthly_amount:,.2f}**
                            - Rate: **{interest_rate}%**
                            - Total Investment: **Rs {total_investment:,.2f}**
                            - Maturity: **{maturity_date.strftime('%d-%m-%Y')}**
                            - Maturity Amount: **Rs {maturity_amount:,.2f}**
                            """)
                            st.balloons()
                            
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
    
    # Tab 2: Active RDs
    with tab2:
        st.markdown("### 📊 Active Recurring Deposits")
        rds = c.execute("""
            SELECT rd.id, rd.rd_number, c.id as customer_id,
                   c.first_name||' '||c.last_name as customer,
                   a.id as sb_account_id, a.account_number as sb_account,
                   rd.monthly_amount, rd.installments_paid, rd.total_installments,
                   rd.maturity_amount, rd.status,
                   round(rd.installments_paid * 100.0 / rd.total_installments, 1) as progress
            FROM recurring_deposits rd
            JOIN accounts a ON rd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            WHERE rd.status='ACTIVE'
            ORDER BY rd.created_at DESC
        """).fetchall()
        
        if rds:
            rd_data = []
            for rd in rds:
                rd_id, rd_number, cust_id, customer, sb_acc_id, sb_acc, monthly, paid, total, maturity, status, progress = rd
                remaining = total - paid
                
                rd_data.append({
                    'ID': rd_id,
                    'RD No': rd_number,
                    'Customer': customer,
                    'SB Account': sb_acc,
                    'Monthly': monthly,
                    'Paid': paid,
                    'Total': total,
                    'Remaining': remaining,
                    'Maturity Amount': maturity,
                    'Progress %': progress,
                    'Status': '🟢 Active'
                })
            
            rd_df = pd.DataFrame(rd_data)
            st.dataframe(
                rd_df.style.format({
                    'Monthly': 'Rs {:,.2f}',
                    'Maturity Amount': 'Rs {:,.2f}'
                }),
                use_container_width=True
            )
            
            for rd in rds:
                progress = rd[11]
                st.progress(progress/100, text=f"RD {rd[1]} - {rd[3]} - {progress}% completed")
            
            total_monthly = rd_df['Monthly'].sum()
            total_maturity = rd_df['Maturity Amount'].sum()
            
            col1, col2 = st.columns(2)
            col1.metric("💰 Total Monthly Investment", f"Rs {total_monthly:,.2f}")
            col2.metric("💎 Total Maturity Value", f"Rs {total_maturity:,.2f}")
        else:
            st.info("No active recurring deposits")
    
    # Tab 3: Pay Installment
    with tab3:
        st.markdown("### 💳 Pay RD Installment")
        
        pending_rds = c.execute("""
            SELECT 
                rd.id, 
                rd.rd_number, 
                c.id as customer_id,
                c.first_name||' '||c.last_name as customer,
                rd.account_id as rd_account_id,
                a.account_number as rd_account_number,
                sb.id as sb_account_id,
                sb.account_number as sb_account,
                COALESCE(sb.balance, 0) as sb_balance,
                rd.monthly_amount, 
                rd.installments_paid, 
                rd.total_installments, 
                rd.interest_rate,
                rd.start_date, 
                rd.maturity_date,
                rd.maturity_amount
            FROM recurring_deposits rd
            JOIN accounts a ON rd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            LEFT JOIN accounts sb ON c.id = sb.customer_id AND sb.account_type = 'SB' AND sb.status = 'ACTIVE'
            WHERE rd.status='ACTIVE' AND rd.installments_paid < rd.total_installments
            ORDER BY rd.created_at
        """).fetchall()
        
        if not pending_rds:
            st.success("🎉 All RDs are up to date with installments!")
            c.close()
            return
        
        rd_options = []
        for rd in pending_rds:
            rd_id, rd_number, cust_id, customer, rd_account_id, rd_account_number, sb_acc_id, sb_acc, sb_balance, monthly, paid, total, rate, start, maturity, maturity_amount = rd
            
            remaining = total - paid
            has_sb = sb_acc_id is not None
            is_last = (paid + 1) == total
            
            rd_options.append({
                'display': f"{rd_number} - {customer} | {'✅' if has_sb else '❌'} SB: {sb_acc if sb_acc else 'No SB'} | Balance: Rs{sb_balance:,.2f} | {paid}/{total} paid | {'⭐ LAST' if is_last else f'Next: Rs{monthly:,.2f}'}",
                'rd_id': rd_id,
                'rd_number': rd_number,
                'customer_id': cust_id,
                'customer': customer,
                'rd_account_id': rd_account_id,
                'rd_account_number': rd_account_number,
                'sb_account_id': sb_acc_id,
                'sb_account': sb_acc if sb_acc else 'No SB Account',
                'sb_balance': sb_balance if sb_acc_id else 0,
                'monthly_amount': monthly,
                'installments_paid': paid,
                'total_installments': total,
                'remaining_installments': remaining,
                'interest_rate': rate,
                'start_date': start,
                'maturity_date': maturity,
                'maturity_amount': maturity_amount,
                'has_sb': has_sb,
                'is_last_installment': is_last
            })
        
        selected_rd = st.selectbox(
            "📋 Select RD for Payment",
            rd_options,
            format_func=lambda x: x['display']
        )
        
        if selected_rd:
            st.markdown("---")
            
            if selected_rd['has_sb']:
                st.success(f"✅ SB Account Found: {selected_rd['sb_account']} (Balance: Rs {selected_rd['sb_balance']:,.2f})")
            else:
                st.error("❌ No active SB account found for this customer!")
            
            st.markdown(f"""
            ### 📋 RD Details
            
            | Field | Value |
            |-------|-------|
            | **RD Number** | {selected_rd['rd_number']} |
            | **Customer** | {selected_rd['customer']} |
            | **RD Account** | {selected_rd['rd_account_number']} |
            | **SB Account** | {selected_rd['sb_account']} |
            | **SB Balance** | Rs {selected_rd['sb_balance']:,.2f} |
            | **Monthly Amount** | Rs {selected_rd['monthly_amount']:,.2f} |
            | **Installments Paid** | {selected_rd['installments_paid']}/{selected_rd['total_installments']} |
            | **Remaining** | {selected_rd['remaining_installments']} installments |
            | **Interest Rate** | {selected_rd['interest_rate']}% |
            | **Start Date** | {selected_rd['start_date']} |
            | **Maturity Date** | {selected_rd['maturity_date']} |
            | **Maturity Amount** | Rs {selected_rd['maturity_amount']:,.2f} |
            """)
            
            if selected_rd['is_last_installment']:
                st.warning("⚠️ **This is the LAST installment!** The RD will mature after this payment.")
                st.info("💰 **Amount will be deposited to Retrieval Account**")
            
            st.info(f"📊 **Next Installment Amount: Rs {selected_rd['monthly_amount']:,.2f}**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                payment_mode = st.selectbox(
                    "💳 Payment Mode",
                    ["SB Transfer (Debit from SB)", "Cash", "Bank Transfer", "Cheque"],
                    key="rd_payment_mode"
                )
                
                if payment_mode == "SB Transfer (Debit from SB)":
                    if selected_rd['has_sb']:
                        if selected_rd['monthly_amount'] > selected_rd['sb_balance']:
                            st.error(f"❌ Insufficient balance! Available: Rs {selected_rd['sb_balance']:,.2f}, Required: Rs {selected_rd['monthly_amount']:,.2f}")
                        else:
                            st.success(f"✅ Sufficient balance: Rs {selected_rd['sb_balance']:,.2f}")
                    else:
                        st.error("❌ No SB account found!")
            
            with col2:
                st.markdown("### 💰 Payment Summary")
                st.markdown(f"""
                - Amount: **Rs {selected_rd['monthly_amount']:,.2f}**
                - Installment: **{selected_rd['installments_paid'] + 1}/{selected_rd['total_installments']}**
                - Remaining after payment: **{selected_rd['remaining_installments'] - 1}**
                """)
            
            can_pay = True
            if payment_mode == "SB Transfer (Debit from SB)":
                if not selected_rd['has_sb']:
                    can_pay = False
                    st.error("❌ Cannot pay: No SB account found!")
                elif selected_rd['monthly_amount'] > selected_rd['sb_balance']:
                    can_pay = False
                    st.error(f"❌ Cannot pay: Insufficient balance! Available: Rs {selected_rd['sb_balance']:,.2f}")
            
            if st.button("💳 Pay Installment", use_container_width=True, type="primary", disabled=not can_pay):
                if not can_pay:
                    st.error("❌ Please fix the issues above before paying!")
                else:
                    conn = get_db()
                    try:
                        new_paid = selected_rd['installments_paid'] + 1
                        is_completed = new_paid >= selected_rd['total_installments']
                        
                        conn.execute("""
                            UPDATE recurring_deposits 
                            SET installments_paid=? 
                            WHERE id=?
                        """, (new_paid, selected_rd['rd_id']))
                        
                        if is_completed:
                            conn.execute("""
                                UPDATE recurring_deposits 
                                SET status='MATURED', 
                                    closed_date=CURRENT_DATE, 
                                    closed_amount=?
                                WHERE id=?
                            """, (selected_rd['maturity_amount'], selected_rd['rd_id']))
                        
                        if payment_mode == "SB Transfer (Debit from SB)":
                            sb_balance_result = conn.execute("""
                                SELECT balance FROM accounts WHERE id=?
                            """, (selected_rd['sb_account_id'],)).fetchone()
                            
                            current_sb_balance = sb_balance_result[0] if sb_balance_result else 0
                            new_sb_balance = current_sb_balance - selected_rd['monthly_amount']
                            
                            conn.execute("UPDATE accounts SET balance=? WHERE id=?", (new_sb_balance, selected_rd['sb_account_id']))
                            
                            conn.execute("""
                                INSERT INTO transactions (
                                    transaction_id, account_id, transaction_type,
                                    amount, balance_after, description,
                                    reference_type, voucher_type, voucher_number,
                                    created_by
                                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                            """, (
                                generate_id('TXN'), selected_rd['sb_account_id'], 'DEBIT',
                                selected_rd['monthly_amount'], new_sb_balance,
                                f"RD Installment {new_paid}/{selected_rd['total_installments']}: {selected_rd['rd_number']}",
                                'SB_TRANSFER', 'PAYMENT',
                                generate_voucher_number('PAYMENT'),
                                st.session_state.user['id']
                            ))
                        
                        rd_balance = selected_rd['monthly_amount'] * new_paid
                        conn.execute("""
                            INSERT INTO transactions (
                                transaction_id, account_id, transaction_type,
                                amount, balance_after, description,
                                reference_type, voucher_type, voucher_number,
                                created_by
                            ) VALUES (?,?,?,?,?,?,?,?,?,?)
                        """, (
                            generate_id('TXN'), selected_rd['rd_account_id'], 'CREDIT',
                            selected_rd['monthly_amount'], rd_balance,
                            f"RD Installment {new_paid}/{selected_rd['total_installments']}: {selected_rd['rd_number']}",
                            payment_mode, 'RECEIPT',
                            generate_voucher_number('RECEIPT'),
                            st.session_state.user['id']
                        ))
                        
                        conn.commit()
                        conn.close()
                        
                        if is_completed:
                            total_investment = selected_rd['monthly_amount'] * selected_rd['total_installments']
                            interest_earned = selected_rd['maturity_amount'] - total_investment
                            
                            ret_acc_number, new_ret_balance = add_to_retrieval_account(
                                selected_rd['customer_id'],
                                'RD',
                                selected_rd['rd_number'],
                                total_investment,
                                interest_earned,
                                selected_rd['maturity_date']
                            )
                            
                            st.success(f"""
                            🎉 **RD COMPLETED!** 
                            
                            ✅ All {selected_rd['total_installments']} installments paid!
                            📋 **RD {selected_rd['rd_number']} is now MATURED!**
                            💰 **Maturity Amount: Rs {selected_rd['maturity_amount']:,.2f}**
                            💰 **Deposited to Retrieval Account: {ret_acc_number}**
                            - Retrieval Balance: **Rs {new_ret_balance:,.2f}**
                            """)
                            st.balloons()
                        else:
                            st.success(f"""
                            ✅ Installment Paid Successfully! 🎉
                            
                            📋 **Payment Details:**
                            - RD Number: **{selected_rd['rd_number']}**
                            - Installment: **{new_paid}/{selected_rd['total_installments']}**
                            - Amount: **Rs {selected_rd['monthly_amount']:,.2f}**
                            - Remaining: **{selected_rd['remaining_installments'] - 1} installments**
                            """)
                        
                        st.rerun()
                        
                    except Exception as e:
                        conn.rollback()
                        conn.close()
                        st.error(f"❌ Error: {str(e)}")
    
    # Tab 4: Closed RDs
    with tab4:
        st.markdown("### 📋 Closed/Completed Recurring Deposits")
        
        try:
            closed_rds = c.execute("""
                SELECT 
                    rd.rd_number,
                    rd.monthly_amount, 
                    rd.installments_paid,
                    rd.total_installments, 
                    rd.interest_rate,
                    rd.start_date, 
                    rd.maturity_date,
                    rd.maturity_amount, 
                    rd.status,
                    rd.closed_date,
                    COALESCE(rd.closed_amount, rd.maturity_amount) as closed_amount,
                    CASE 
                        WHEN rd.status = 'MATURED' THEN '✅ MATURED'
                        WHEN rd.status = 'CLOSED' THEN '🔒 CLOSED'
                        ELSE rd.status
                    END as status_display
                FROM recurring_deposits rd
                WHERE rd.status IN ('MATURED', 'CLOSED')
                ORDER BY rd.closed_date DESC, rd.maturity_date DESC
            """).fetchall()
            
            if closed_rds:
                df = pd.DataFrame(closed_rds, columns=[
                    'RD No', 'Monthly', 'Paid', 'Total',
                    'Rate', 'Start Date', 'Maturity Date', 'Maturity Amount', 
                    'Status', 'Closed Date', 'Closed Amount', 'Status Display'
                ])
                
                total_principal = df['Monthly'].sum()
                total_maturity = df['Maturity Amount'].sum()
                total_closed = df['Closed Amount'].sum()
                total_interest = total_closed - total_principal
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("📊 Total Closed", f"{len(closed_rds)}")
                col2.metric("💰 Total Deposited", f"Rs {total_principal:,.2f}")
                col3.metric("💎 Total Received", f"Rs {total_closed:,.2f}")
                col4.metric("📈 Total Interest", f"Rs {total_interest:,.2f}")
                
                st.markdown("---")
                
                st.dataframe(
                    df.style.format({
                        'Monthly': 'Rs {:,.2f}',
                        'Maturity Amount': 'Rs {:,.2f}',
                        'Closed Amount': 'Rs {:,.2f}',
                        'Rate': '{:.2f}%'
                    }),
                    use_container_width=True
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "📥 Download Closed RDs CSV",
                        df.to_csv(index=False),
                        "closed_recurring_deposits.csv",
                        "text/csv"
                    )
                
                with col2:
                    with st.expander("🗑️ Delete RD Record"):
                        rd_num = st.text_input("Enter RD Number to delete:")
                        if rd_num:
                            if st.button("🗑️ Delete RD", use_container_width=True, type="secondary"):
                                if st.checkbox("☑️ Confirm delete? This cannot be undone!"):
                                    try:
                                        conn = get_db()
                                        rd = conn.execute("SELECT id FROM recurring_deposits WHERE rd_number=?", (rd_num,)).fetchone()
                                        if rd:
                                            conn.execute("DELETE FROM recurring_deposits WHERE rd_number=?", (rd_num,))
                                            conn.commit()
                                            conn.close()
                                            st.success("✅ RD record deleted successfully!")
                                            st.rerun()
                                        else:
                                            st.error("❌ RD not found!")
                                    except Exception as e:
                                        st.error(f"❌ Error: {str(e)}")
            else:
                st.info("No closed recurring deposits found")
                
        except Exception as e:
            st.error(f"❌ Error loading closed RDs: {str(e)}")
    
    c.close()

# ==================== RETRIEVAL ACCOUNT ====================
def retrieval_account():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    tab1, tab2, tab3, tab4 = st.tabs(["💰 Overview", "📊 Matured Deposits", "🏦 Transfer to SB", "💳 Withdraw"])
    
    # Tab 1: Overview
    with tab1:
        st.markdown("### 💰 Retrieval Account Overview")
        
        cust_id, cust_name, acc_id, acc_number, sb_balance = customer_selector(
            "👤 Select Customer",
            "retrieval_customer"
        )
        
        if cust_id:
            try:
                ret_acc_id, ret_acc_number, ret_balance = get_retrieval_account(cust_id)
                
                sb_acc = c.execute("""
                    SELECT id, account_number, balance 
                    FROM accounts 
                    WHERE customer_id = ? AND account_type = 'SB' AND status = 'ACTIVE'
                """, (cust_id,)).fetchone()
                
                st.markdown(f"""
                ### 📋 Account Details
                
                | Field | Value |
                |-------|-------|
                | **Customer** | {cust_name} |
                | **Retrieval Account** | {ret_acc_number} |
                | **Retrieval Balance** | Rs {ret_balance:,.2f} |
                | **SB Account** | {sb_acc[1] if sb_acc else 'No SB Account'} |
                | **SB Balance** | Rs {sb_acc[2]:,.2f} if sb_acc else 'N/A' |
                | **Status** | {'🟢 Active' if ret_balance > 0 else '⚪ Empty'} |
                """)
                
                txns = c.execute("""
                    SELECT transaction_id, transaction_type, amount,
                           balance_after, description, created_at
                    FROM transactions
                    WHERE account_id = ?
                    ORDER BY created_at DESC
                    LIMIT 20
                """, (ret_acc_id,)).fetchall()
                
                if txns:
                    st.markdown("### 📊 Recent Transactions")
                    txn_data = []
                    for txn in txns:
                        txn_data.append({
                            'Txn ID': txn[0],
                            'Type': txn[1],
                            'Amount': f"Rs {float(txn[2]):,.2f}" if txn[2] is not None else "Rs 0.00",
                            'Balance': f"Rs {float(txn[3]):,.2f}" if txn[3] is not None else "Rs 0.00",
                            'Description': txn[4] if txn[4] else 'N/A',
                            'Date': datetime.strptime(txn[5], '%Y-%m-%d %H:%M:%S').strftime('%d-%m-%Y %I:%M %p') if txn[5] else 'N/A'
                        })
                    df = pd.DataFrame(txn_data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No transactions in retrieval account")
            except Exception as e:
                st.error(f"Error loading retrieval account: {str(e)}")
    
    # Tab 2: Matured Deposits
    with tab2:
        st.markdown("### 📊 Matured Deposits")
        
        cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
            "👤 Select Customer",
            "matured_customer"
        )
        
        if cust_id:
            try:
                matured = c.execute("""
                    SELECT 
                        deposit_id,
                        original_deposit_type,
                        original_deposit_number,
                        principal_amount,
                        interest_earned,
                        total_amount,
                        maturity_date,
                        deposited_date,
                        status,
                        withdrawn_date,
                        withdrawn_amount
                    FROM matured_deposits
                    WHERE customer_id = ?
                    ORDER BY deposited_date DESC
                """, (cust_id,)).fetchall()
                
                if matured:
                    matured_data = []
                    total_principal = 0
                    total_interest = 0
                    total_amount = 0
                    active_total = 0
                    withdrawn_total = 0
                    
                    for m in matured:
                        principal = float(m[3]) if m[3] is not None else 0
                        interest = float(m[4]) if m[4] is not None else 0
                        total = float(m[5]) if m[5] is not None else 0
                        status = m[8] if m[8] else 'ACTIVE'
                        
                        total_principal += principal
                        total_interest += interest
                        total_amount += total
                        if status == 'ACTIVE':
                            active_total += total
                        else:
                            withdrawn_total += total
                        
                        matured_data.append({
                            'Deposit ID': m[0],
                            'Type': m[1],
                            'Deposit No': m[2],
                            'Principal': f"Rs {principal:,.2f}",
                            'Interest Earned': f"Rs {interest:,.2f}",
                            'Total Amount': f"Rs {total:,.2f}",
                            'Maturity Date': m[6] if m[6] else 'N/A',
                            'Deposited Date': m[7] if m[7] else 'N/A',
                            'Status': '🟢 Active' if status == 'ACTIVE' else '🔴 Withdrawn',
                            'Withdrawn Date': m[9] if m[9] else 'N/A',
                            'Withdrawn Amount': f"Rs {float(m[10]):,.2f}" if m[10] is not None else "Rs 0.00"
                        })
                    
                    df = pd.DataFrame(matured_data)
                    
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("📊 Total", f"{len(matured)}")
                    col2.metric("💰 Principal", f"Rs {total_principal:,.2f}")
                    col3.metric("📈 Interest", f"Rs {total_interest:,.2f}")
                    col4.metric("🟢 Active", f"Rs {active_total:,.2f}")
                    col5.metric("🔴 Withdrawn", f"Rs {withdrawn_total:,.2f}")
                    
                    st.markdown("---")
                    st.dataframe(df, use_container_width=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        raw_data = []
                        for m in matured:
                            raw_data.append({
                                'Deposit ID': m[0],
                                'Type': m[1],
                                'Deposit No': m[2],
                                'Principal': float(m[3]) if m[3] is not None else 0,
                                'Interest Earned': float(m[4]) if m[4] is not None else 0,
                                'Total Amount': float(m[5]) if m[5] is not None else 0,
                                'Maturity Date': m[6] if m[6] else '',
                                'Deposited Date': m[7] if m[7] else '',
                                'Status': m[8] if m[8] else 'ACTIVE',
                                'Withdrawn Date': m[9] if m[9] else '',
                                'Withdrawn Amount': float(m[10]) if m[10] is not None else 0
                            })
                        raw_df = pd.DataFrame(raw_data)
                        st.download_button(
                            "📥 Download Matured Deposits CSV",
                            raw_df.to_csv(index=False),
                            "matured_deposits.csv",
                            "text/csv"
                        )
                    
                    with col2:
                        with st.expander("🗑️ Delete Matured Deposit"):
                            dep_id = st.text_input("Enter Deposit ID to delete:")
                            if dep_id:
                                if st.button("🗑️ Delete Deposit", use_container_width=True, type="secondary"):
                                    if st.checkbox("☑️ Confirm delete? This cannot be undone!"):
                                        try:
                                            conn = get_db()
                                            dep = conn.execute("SELECT id FROM matured_deposits WHERE deposit_id=?", (dep_id,)).fetchone()
                                            if dep:
                                                conn.execute("DELETE FROM matured_deposits WHERE deposit_id=?", (dep_id,))
                                                conn.commit()
                                                conn.close()
                                                st.success("✅ Deposit record deleted successfully!")
                                                st.rerun()
                                            else:
                                                st.error("❌ Deposit not found!")
                                        except Exception as e:
                                            st.error(f"❌ Error: {str(e)}")
                else:
                    st.info("No matured deposits found for this customer")
            except Exception as e:
                st.error(f"Error loading matured deposits: {str(e)}")
    
    # Tab 3: Transfer to SB
    with tab3:
        st.markdown("### 🏦 Transfer to SB Account")
        
        cust_id, cust_name, acc_id, acc_number, sb_balance = customer_selector(
            "👤 Select Customer",
            "transfer_customer"
        )
        
        if cust_id and acc_id:
            try:
                ret_acc_id, ret_acc_number, ret_balance = get_retrieval_account(cust_id)
                
                st.markdown(f"""
                ✅ **Account Details:**
                - Customer: **{cust_name}**
                - Retrieval Account: **{ret_acc_number}**
                - Retrieval Balance: **Rs {ret_balance:,.2f}**
                - SB Account: **{acc_number}**
                - SB Balance: **Rs {sb_balance:,.2f}**
                """)
                
                if ret_balance <= 0:
                    st.warning("⚠️ No balance available in retrieval account!")
                else:
                    with st.form("transfer_to_sb_form"):
                        amount = st.number_input(
                            "💰 Amount to Transfer (Rs)",
                            min_value=1.0,
                            max_value=float(ret_balance),
                            step=100.0,
                            value=min(1000.0, float(ret_balance))
                        )
                        
                        if st.form_submit_button("🏦 Transfer to SB", use_container_width=True, type="primary"):
                            try:
                                new_ret_balance, new_sb_balance = transfer_to_sb(cust_id, amount, acc_id)
                                
                                st.success(f"""
                                ✅ Transfer Successful! 🎉
                                
                                📋 **Details:**
                                - Amount: **Rs {amount:,.2f}**
                                - From: **Retrieval Account ({ret_acc_number})**
                                - To: **SB Account ({acc_number})**
                                - New Retrieval Balance: **Rs {new_ret_balance:,.2f}**
                                - New SB Balance: **Rs {new_sb_balance:,.2f}**
                                """)
                                st.balloons()
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"❌ Error during transfer: {str(e)}")
            except Exception as e:
                st.error(f"Error loading retrieval account: {str(e)}")
    
    # Tab 4: Withdraw
    with tab4:
        st.markdown("### 💳 Withdraw from Retrieval Account")
        
        cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
            "👤 Select Customer",
            "withdraw_customer"
        )
        
        if cust_id:
            try:
                ret_acc_id, ret_acc_number, ret_balance = get_retrieval_account(cust_id)
                
                st.markdown(f"""
                ✅ **Retrieval Account:**
                - Customer: **{cust_name}**
                - Account: **{ret_acc_number}**
                - Balance: **Rs {ret_balance:,.2f}**
                """)
                
                if ret_balance <= 0:
                    st.warning("⚠️ No balance available for withdrawal!")
                else:
                    with st.form("withdraw_form"):
                        amount = st.number_input(
                            "💰 Amount to Withdraw (Rs)",
                            min_value=1.0,
                            max_value=float(ret_balance),
                            step=100.0,
                            value=min(1000.0, float(ret_balance))
                        )
                        
                        mode = st.selectbox(
                            "💳 Withdrawal Mode",
                            ["CASH", "BANK TRANSFER", "CHEQUE", "ONLINE"]
                        )
                        
                        if st.form_submit_button("💳 Withdraw", use_container_width=True, type="primary"):
                            try:
                                conn = get_db()
                                new_balance = ret_balance - amount
                                conn.execute("""
                                    UPDATE retrieval_accounts 
                                    SET balance = ? 
                                    WHERE id = ?
                                """, (new_balance, ret_acc_id))
                                
                                conn.execute("""
                                    INSERT INTO transactions (
                                        transaction_id, account_id, transaction_type,
                                        amount, balance_after, description,
                                        reference_type, voucher_type, voucher_number,
                                        created_by
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    generate_id('TXN'), ret_acc_id, 'DEBIT',
                                    amount, new_balance,
                                    f"Withdrawal from Retrieval Account ({mode})",
                                    mode, 'PAYMENT',
                                    generate_voucher_number('PAYMENT'),
                                    st.session_state.user['id']
                                ))
                                
                                conn.commit()
                                conn.close()
                                
                                st.success(f"""
                                ✅ Withdrawal Successful! 🎉
                                
                                📋 **Details:**
                                - Amount: **Rs {amount:,.2f}**
                                - Account: **{ret_acc_number}**
                                - New Balance: **Rs {new_balance:,.2f}**
                                - Mode: **{mode}**
                                """)
                                st.balloons()
                                st.rerun()
                                
                            except Exception as e:
                                conn.rollback()
                                conn.close()
                                st.error(f"❌ Error during withdrawal: {str(e)}")
            except Exception as e:
                st.error(f"Error loading retrieval account: {str(e)}")
    
    c.close()

# ==================== CHART OF ACCOUNTS ====================
def chart_of_accounts():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    tab1, tab2 = st.tabs(["📊 View Accounts", "➕ Add New Account"])
    
    with tab1:
        st.markdown("### 📊 Chart of Accounts")
        
        accounts = c.execute("""
            SELECT id, account_code, account_name, account_type, category, is_active
            FROM chart_of_accounts
            ORDER BY account_type, account_name
        """).fetchall()
        
        if accounts:
            df = pd.DataFrame(accounts, columns=['ID', 'Code', 'Account Name', 'Type', 'Category', 'Active'])
            
            col1, col2 = st.columns(2)
            with col1:
                type_filter = st.multiselect(
                    "Filter by Type",
                    options=df['Type'].unique(),
                    default=df['Type'].unique()
                )
            with col2:
                category_filter = st.multiselect(
                    "Filter by Category",
                    options=df['Category'].unique(),
                    default=df['Category'].unique()
                )
            
            filtered_df = df[df['Type'].isin(type_filter) & df['Category'].isin(category_filter)]
            
            st.dataframe(filtered_df, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📥 Download CSV",
                    filtered_df.to_csv(index=False),
                    "chart_of_accounts.csv",
                    "text/csv"
                )
            
            with col2:
                with st.expander("🗑️ Delete Account"):
                    acc_code = st.text_input("Enter Account Code to delete:")
                    if acc_code:
                        if st.button("🗑️ Delete Account", use_container_width=True, type="secondary"):
                            if st.checkbox("☑️ Confirm delete? This cannot be undone!"):
                                try:
                                    conn = get_db()
                                    acc = conn.execute("SELECT id FROM chart_of_accounts WHERE account_code=?", (acc_code,)).fetchone()
                                    if acc:
                                        used_in_income = conn.execute("SELECT id FROM income WHERE chart_of_accounts_id=?", (acc[0],)).fetchone()
                                        used_in_expense = conn.execute("SELECT id FROM expenses WHERE chart_of_accounts_id=?", (acc[0],)).fetchone()
                                        if used_in_income or used_in_expense:
                                            st.error("❌ This account is in use and cannot be deleted!")
                                        else:
                                            conn.execute("DELETE FROM chart_of_accounts WHERE account_code=?", (acc_code,))
                                            conn.commit()
                                            conn.close()
                                            st.success("✅ Account deleted successfully!")
                                            st.rerun()
                                    else:
                                        st.error("❌ Account not found!")
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")
        else:
            st.info("No accounts found")
    
    with tab2:
        st.markdown("### ➕ Add New Account")
        
        with st.form("add_account_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                account_code = st.text_input("Account Code*", placeholder="e.g., EXP016")
                account_name = st.text_input("Account Name*", placeholder="e.g., Office Rent")
            
            with col2:
                account_type = st.selectbox(
                    "Account Type*",
                    ["Income", "Expense", "Asset", "Liability", "Equity"]
                )
                category = st.selectbox(
                    "Category*",
                    ["Banking Income", "Other Income", "Operating Expenses", 
                     "Administrative Expenses", "Other Expenses", "Current Assets",
                     "Fixed Assets", "Current Liabilities", "Long Term Liabilities"]
                )
            
            description = st.text_area("Description (Optional)")
            
            if st.form_submit_button("✅ Add Account", use_container_width=True, type="primary"):
                if account_code and account_name:
                    conn = get_db()
                    try:
                        conn.execute("""
                            INSERT INTO chart_of_accounts (account_code, account_name, account_type, category)
                            VALUES (?, ?, ?, ?)
                        """, (account_code.upper(), account_name, account_type, category))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Account '{account_name}' added successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                else:
                    st.error("❌ Please fill all required fields (*)")
    
    c.close()

# ==================== INTEREST RATE SETTINGS ====================
def interest_rate_settings():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    st.markdown("### 📊 Interest Rate Settings")
    
    current_rate = c.execute("""
        SELECT value FROM system_settings WHERE key = 'SB_INTEREST_RATE'
    """).fetchone()
    
    if not current_rate:
        c.execute("""
            INSERT INTO system_settings (key, value, description)
            VALUES ('SB_INTEREST_RATE', '3.5', 'SB Account Interest Rate (%)')
        """)
        c.commit()
        current_rate = (3.5,)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Current SB Interest Rate")
        st.markdown(f"""
        <div style="background: #d4edda; padding: 1.5rem; border-radius: 12px; text-align: center;">
            <h2 style="font-size: 3rem; margin: 0; color: #155724;">{current_rate[0]}%</h2>
            <p style="margin: 0; color: #155724;">per annum</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("💡 This rate is used for calculating interest on SB accounts")
    
    with col2:
        st.markdown("### ✏️ Update Interest Rate")
        
        new_rate = st.number_input(
            "📊 New Interest Rate (%)",
            min_value=0.0,
            max_value=10.0,
            value=float(current_rate[0]),
            step=0.25,
            help="Enter the new interest rate for SB accounts"
        )
        
        effective_from = st.date_input(
            "📅 Effective From",
            date.today(),
            help="Date from which this rate will be applied"
        )
        
        if st.button("💾 Update Interest Rate", use_container_width=True, type="primary"):
            if new_rate != float(current_rate[0]):
                c.execute("""
                    UPDATE system_settings 
                    SET value = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE key = 'SB_INTEREST_RATE'
                """, (str(new_rate),))
                
                c.execute("""
                    INSERT INTO interest_rate_history (
                        rate, effective_from, changed_by, notes
                    ) VALUES (?, ?, ?, ?)
                """, (new_rate, effective_from, st.session_state.user['id'], 
                       f"Rate changed from {current_rate[0]}% to {new_rate}%"))
                
                c.commit()
                c.close()
                
                st.success(f"""
                ✅ Interest Rate Updated Successfully! 🎉
                
                📋 **Details:**
                - Old Rate: **{current_rate[0]}%**
                - New Rate: **{new_rate}%**
                - Effective From: **{effective_from.strftime('%d-%m-%Y')}**
                """)
                st.balloons()
                st.rerun()
            else:
                st.warning("⚠️ New rate is same as current rate. No changes made.")
    
    st.markdown("### 📋 Rate Change History")
    
    history = c.execute("""
        SELECT 
            id,
            rate,
            effective_from,
            u.username as changed_by,
            notes,
            created_at
        FROM interest_rate_history h
        LEFT JOIN users u ON h.changed_by = u.id
        ORDER BY created_at DESC
        LIMIT 20
    """).fetchall()
    
    if history:
        df = pd.DataFrame(history, columns=['ID', 'Rate', 'Effective From', 'Changed By', 'Notes', 'Changed At'])
        st.dataframe(
            df.style.format({
                'Rate': '{:.2f}%'
            }),
            use_container_width=True
        )
    else:
        st.info("No rate change history available")
    
    c.close()

# ==================== JOURNAL VOUCHERS ====================
def journal_vouchers():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    tab1, tab2 = st.tabs(["📝 Create JV", "📋 Manage JVs"])
    
    with tab1:
        st.markdown("### 📝 Create Journal Voucher")
        
        cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
            "👤 Link Customer (Optional)",
            "jv_customer"
        )
        
        if cust_id and acc_id:
            st.info(f"📌 Linking JV to: **{cust_name}** (Account: {acc_number})")
        
        with st.form("jv_form"):
            voucher_date = st.date_input("📅 Voucher Date", date.today())
            description = st.text_area("📝 Narration", placeholder="Describe the transaction")
            
            num_entries = st.number_input("📊 Number of Entries", min_value=2, max_value=10, value=2)
            
            st.markdown("### 📊 Journal Entries")
            st.info("💡 **Note:** Each entry should have either Debit OR Credit amount")
            
            entries = []
            total_dr = 0
            total_cr = 0
            
            coa_list = c.execute("""
                SELECT id, account_code, account_name, account_type 
                FROM chart_of_accounts 
                WHERE is_active = 1
                ORDER BY account_type, account_name
            """).fetchall()
            
            coa_options = {f"{acc[1]} - {acc[2]}": acc[0] for acc in coa_list}
            coa_list_options = list(coa_options.keys())
            
            for i in range(int(num_entries)):
                st.markdown(f"**Entry {i+1}**")
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    if coa_list_options:
                        selected_coa = st.selectbox(
                            f"Account", 
                            coa_list_options, 
                            key=f"jv_coa_{i}",
                            index=0
                        )
                        head = selected_coa
                    else:
                        head = st.text_input(
                            f"Account Head", 
                            key=f"jh_{i}", 
                            placeholder="e.g., Cash A/c, Bank A/c"
                        )
                with col2:
                    dr = st.number_input(f"Debit", min_value=0.0, step=100.0, key=f"jd_{i}")
                with col3:
                    cr = st.number_input(f"Credit", min_value=0.0, step=100.0, key=f"jc_{i}")
                
                total_dr += dr
                total_cr += cr
                entries.append({
                    'head': head,
                    'dr': dr,
                    'cr': cr
                })
            
            st.markdown("---")
            st.info(f"💰 **Total Debit: Rs {total_dr:,.2f} | Total Credit: Rs {total_cr:,.2f}**")
            
            if abs(total_dr - total_cr) > 0.01:
                st.error(f"❌ Difference: Rs {abs(total_dr - total_cr):,.2f} - Must balance!")
            
            status = st.radio(
                "📌 Voucher Status",
                ["DRAFT", "POSTED"],
                horizontal=True,
                help="DRAFT: Can be edited later, POSTED: Will appear in Trial Balance"
            )
            
            if st.form_submit_button("✅ Create JV", use_container_width=True, type="primary"):
                if abs(total_dr - total_cr) > 0.01:
                    st.error("❌ Journal must be balanced!")
                else:
                    conn = get_db()
                    try:
                        voucher_number = generate_voucher_number('JOURNAL')
                        
                        conn.execute("""
                            INSERT INTO journal_vouchers (
                                voucher_number, voucher_date, description,
                                total_amount, created_by, customer_id, status
                            ) VALUES (?,?,?,?,?,?,?)
                        """, (voucher_number, voucher_date, description, total_dr, 
                              st.session_state.user['id'], cust_id, status))
                        
                        voucher_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                        
                        for entry in entries:
                            if (entry['dr'] > 0 or entry['cr'] > 0) and entry['head'].strip():
                                conn.execute("""
                                    INSERT INTO journal_entries (
                                        voucher_id, account_head,
                                        debit_amount, credit_amount
                                    ) VALUES (?,?,?,?)
                                """, (voucher_id, entry['head'].strip(), entry['dr'], entry['cr']))
                        
                        conn.commit()
                        conn.close()
                        
                        if status == "POSTED":
                            st.success(f"""
                            ✅ Journal Voucher Created & POSTED! 🎉
                            
                            📋 **JV Details:**
                            - Voucher Number: **{voucher_number}**
                            - Total Amount: **Rs {total_dr:,.2f}**
                            - Entries: **{num_entries}**
                            - Status: **POSTED** ✅
                            
                            💡 **This JV will appear in Trial Balance & Balance Sheet**
                            """)
                        else:
                            st.success(f"""
                            ✅ Journal Voucher Created! 📝
                            
                            📋 **JV Details:**
                            - Voucher Number: **{voucher_number}**
                            - Total Amount: **Rs {total_dr:,.2f}**
                            - Entries: **{num_entries}**
                            - Status: **DRAFT** ⏳
                            
                            💡 **Post this JV from 'Manage JVs' tab to appear in financial statements**
                            """)
                        st.balloons()
                        
                    except Exception as e:
                        conn.rollback()
                        conn.close()
                        st.error(f"❌ Error: {str(e)}")
    
    with tab2:
        st.markdown("### 📋 Manage Journal Vouchers")
        
        vouchers = c.execute("""
            SELECT jv.id, jv.voucher_number, jv.voucher_date,
                   jv.description, jv.total_amount, jv.status,
                   u.username as created_by, jv.created_at,
                   COALESCE(c.first_name||' '||c.last_name, 'N/A') as customer
            FROM journal_vouchers jv
            LEFT JOIN users u ON jv.created_by = u.id
            LEFT JOIN customers c ON jv.customer_id = c.id
            ORDER BY jv.created_at DESC
        """).fetchall()
        
        if vouchers:
            for v in vouchers:
                status_color = "🟢" if v[5] == 'POSTED' else "🟡" if v[5] == 'DRAFT' else "🔴"
                
                with st.expander(f"{status_color} {v[1]} | {v[2]} | Rs {v[4]:,.2f} | {v[5]}"):
                    st.markdown(f"""
                    **📋 Voucher Details:**
                    - Number: **{v[1]}**
                    - Date: **{v[2]}**
                    - Description: {v[3] or 'N/A'}
                    - Total: **Rs {v[4]:,.2f}**
                    - Status: **{v[5]}**
                    - Created By: {v[6]}
                    - Customer: {v[8]}
                    """)
                    
                    entries = c.execute("""
                        SELECT id, account_head, debit_amount, credit_amount
                        FROM journal_entries
                        WHERE voucher_id=?
                    """, (v[0],)).fetchall()
                    
                    if entries:
                        df = pd.DataFrame(entries, columns=['ID', 'Account Head', 'Debit', 'Credit'])
                        st.dataframe(
                            df.style.format({
                                'Debit': 'Rs {:,.2f}',
                                'Credit': 'Rs {:,.2f}'
                            }),
                            use_container_width=True
                        )
                        
                        total_debit = df['Debit'].sum()
                        total_credit = df['Credit'].sum()
                        st.info(f"📊 Total Debit: Rs {total_debit:,.2f} | Total Credit: Rs {total_credit:,.2f}")
                        
                        with st.expander("🗑️ Delete Entry"):
                            entry_id = st.text_input("Enter Entry ID to delete:", key=f"del_entry_{v[0]}")
                            if entry_id:
                                if st.button("🗑️ Delete Entry", key=f"del_btn_{v[0]}", use_container_width=True, type="secondary"):
                                    if st.checkbox("☑️ Confirm delete?", key=f"confirm_entry_{v[0]}"):
                                        try:
                                            conn = get_db()
                                            conn.execute("DELETE FROM journal_entries WHERE id=?", (entry_id,))
                                            conn.commit()
                                            conn.close()
                                            st.success("✅ Entry deleted successfully!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ Error: {str(e)}")
                    
                    if v[5] == 'DRAFT':
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("✅ Post JV", key=f"post_{v[0]}", use_container_width=True):
                                conn = get_db()
                                conn.execute("""
                                    UPDATE journal_vouchers 
                                    SET status='POSTED', posted_by=?, posted_at=CURRENT_TIMESTAMP
                                    WHERE id=?
                                """, (st.session_state.user['id'], v[0]))
                                conn.commit()
                                conn.close()
                                st.success("✅ JV Posted! It will now appear in Trial Balance & Balance Sheet")
                                st.balloons()
                                st.rerun()
                        
                        with col2:
                            if st.button("❌ Cancel JV", key=f"cancel_{v[0]}", use_container_width=True):
                                conn = get_db()
                                conn.execute("UPDATE journal_vouchers SET status='CANCELLED' WHERE id=?", (v[0],))
                                conn.commit()
                                conn.close()
                                st.warning("❌ JV Cancelled")
                                st.rerun()
                        
                        with col3:
                            if st.button("🗑️ Delete JV", key=f"delete_jv_{v[0]}", use_container_width=True, type="secondary"):
                                if st.checkbox("☑️ Confirm delete?", key=f"confirm_jv_{v[0]}"):
                                    try:
                                        conn = get_db()
                                        conn.execute("DELETE FROM journal_entries WHERE voucher_id=?", (v[0],))
                                        conn.execute("DELETE FROM journal_vouchers WHERE id=?", (v[0],))
                                        conn.commit()
                                        conn.close()
                                        st.success("✅ JV deleted successfully!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Error: {str(e)}")
                    else:
                        st.success("✅ This JV is POSTED and appears in Trial Balance & Balance Sheet")
        else:
            st.info("No journal vouchers found")
    
    c.close()

# ==================== TRANSACTIONS ====================
def transactions():
    c = get_db()
    
    st.markdown("### 💳 All Transactions")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        txn_type = st.selectbox("📊 Type", ["All", "CREDIT", "DEBIT"])
    with col2:
        from_date = st.date_input("📅 From", date.today() - timedelta(days=30))
    with col3:
        to_date = st.date_input("📅 To", date.today())
    
    query = """
        SELECT t.id, t.transaction_id, 
               COALESCE(c.first_name||' '||c.last_name, 'System') as customer,
               COALESCE(a.account_type, 'GEN') as acc_type,
               a.account_number,
               t.transaction_type, t.amount, 
               t.reference_type, t.description, t.created_at,
               t.balance_after
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.id
        LEFT JOIN customers c ON a.customer_id = c.id
        WHERE DATE(t.created_at) BETWEEN ? AND ?
    """
    params = [from_date, to_date]
    
    if txn_type != "All":
        query += " AND t.transaction_type = ?"
        params.append(txn_type)
    
    query += " ORDER BY t.created_at DESC LIMIT 200"
    
    txns = c.execute(query, params).fetchall()
    c.close()
    
    if txns:
        df = pd.DataFrame(txns, columns=['ID', 'Txn ID', 'Customer', 'Account Type', 'Account', 'Type', 'Amount', 'Mode', 'Description', 'Time', 'Balance'])
        df['Time'] = pd.to_datetime(df['Time']).dt.strftime('%d-%m-%Y %I:%M %p')
        
        st.dataframe(
            df.style.format({
                'Amount': 'Rs {:,.2f}',
                'Balance': 'Rs {:,.2f}'
            }),
            use_container_width=True,
            height=500
        )
        
        total_credit = df[df['Type'] == 'CREDIT']['Amount'].sum()
        total_debit = df[df['Type'] == 'DEBIT']['Amount'].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Total Credits", f"Rs {total_credit:,.2f}")
        col2.metric("💳 Total Debits", f"Rs {total_debit:,.2f}")
        col3.metric("📊 Net Balance", f"Rs {(total_credit - total_debit):,.2f}")
        
        st.download_button(
            "📥 Download Transactions CSV",
            df.to_csv(index=False),
            f"transactions_{from_date}_{to_date}.csv",
            "text/csv"
        )
        
        with st.expander("🗑️ Delete Transaction"):
            txn_id = st.text_input("Enter Transaction ID to delete:")
            if txn_id:
                if st.button("🗑️ Delete Transaction", use_container_width=True, type="secondary"):
                    if st.checkbox("☑️ Confirm delete? This cannot be undone!"):
                        try:
                            conn = get_db()
                            txn = conn.execute("SELECT id FROM transactions WHERE transaction_id=?", (txn_id,)).fetchone()
                            if txn:
                                conn.execute("DELETE FROM transactions WHERE transaction_id=?", (txn_id,))
                                conn.commit()
                                conn.close()
                                st.success("✅ Transaction deleted successfully!")
                                st.rerun()
                            else:
                                st.error("❌ Transaction not found!")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
        
        if st.button("📄 Print/PDF Transactions", use_container_width=True):
            content = [
                "📊 TRANSACTIONS REPORT",
                "=" * 50,
                f"Period: {from_date.strftime('%d-%m-%Y')} to {to_date.strftime('%d-%m-%Y')}",
                f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
                "",
                f"Total Credits: Rs {total_credit:,.2f}",
                f"Total Debits: Rs {total_debit:,.2f}",
                f"Net Balance: Rs {(total_credit - total_debit):,.2f}",
                "",
                "DETAILED TRANSACTIONS:",
                "-" * 50
            ]
            
            for txn in txns:
                content.append(f"{txn[1]} | {txn[2]} | {txn[5]} | Rs {txn[6]:,.2f} | {txn[8]} | {txn[9]}")
            
            pdf_file = create_pdf("Transactions Report", content, "transactions")
            if pdf_file:
                create_download_button(pdf_file, "transactions_report", "📥 Download PDF Report")
    else:
        st.info("No transactions in this period")

# ==================== INCOME & EXPENSES ====================
def income_expenses():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    tab1, tab2, tab3, tab4 = st.tabs(["💰 Income", "💸 Expense", "📊 View Income", "📊 View Expenses"])
    
    income_accounts = c.execute("""
        SELECT id, account_code, account_name 
        FROM chart_of_accounts 
        WHERE account_type = 'Income' AND is_active = 1
        ORDER BY account_name
    """).fetchall()
    
    expense_accounts = c.execute("""
        SELECT id, account_code, account_name 
        FROM chart_of_accounts 
        WHERE account_type = 'Expense' AND is_active = 1
        ORDER BY account_name
    """).fetchall()
    
    with tab1:
        st.markdown("### 💰 Record Income")
        
        cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
            "👤 Select Customer (Optional)",
            "income_customer"
        )
        
        with st.form("income_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                income_type = st.selectbox(
                    "📊 Income Type",
                    ["Interest Earned", "Fees & Charges", "Commission Income", "Other Income"]
                )
                
                if income_accounts:
                    coa_options = {f"{acc[1]} - {acc[2]}": acc[0] for acc in income_accounts}
                    selected_coa = st.selectbox(
                        "📋 Chart of Account",
                        options=list(coa_options.keys()),
                        index=0
                    )
                    chart_of_accounts_id = coa_options[selected_coa]
                else:
                    chart_of_accounts_id = None
                    st.info("No income accounts found in Chart of Accounts. Please add some first.")
                
                amount = st.number_input("💰 Amount (Rs)", min_value=1.0, step=100.0)
            
            with col2:
                mode = st.selectbox("💳 Mode", ["CASH", "BANK", "CHEQUE", "ONLINE"])
                date_recorded = st.date_input("📅 Date", date.today())
            
            description = st.text_area("📝 Description")
            
            if cust_id:
                st.info(f"👤 This income is linked to customer: {cust_name}")
            
            if st.form_submit_button("✅ Record Income", use_container_width=True, type="primary"):
                if amount > 0:
                    conn = get_db()
                    try:
                        conn.execute("""
                            INSERT INTO income (
                                income_id, income_type, chart_of_accounts_id,
                                amount, description, date, customer_id, created_by
                            ) VALUES (?,?,?,?,?,?,?,?)
                        """, (
                            generate_id('INC'), income_type, chart_of_accounts_id,
                            amount, description, date_recorded, 
                            cust_id if cust_id else None,
                            st.session_state.user['id']
                        ))
                        
                        conn.execute("""
                            INSERT INTO transactions (
                                transaction_id, account_id, transaction_type,
                                amount, balance_after, description,
                                reference_type, voucher_type, voucher_number,
                                created_by
                            ) VALUES (?,?,?,?,?,?,?,?,?,?)
                        """, (
                            generate_id('TXN'), 0, 'CREDIT',
                            amount, amount,
                            f"Income: {income_type}",
                            mode, 'RECEIPT',
                            generate_voucher_number('RECEIPT'),
                            st.session_state.user['id']
                        ))
                        
                        conn.commit()
                        conn.close()
                        
                        st.success(f"✅ Income recorded: Rs {amount:,.2f}")
                        if cust_id:
                            st.success(f"👤 Linked to customer: {cust_name}")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                else:
                    st.error("❌ Please enter a valid amount")
    
    with tab2:
        st.markdown("### 💸 Record Expense")
        
        cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
            "👤 Select Customer (Optional)",
            "expense_customer"
        )
        
        with st.form("expense_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                expense_type = st.selectbox(
                    "📊 Expense Type",
                    ["Salary & Wages", "Rent & Utilities", "Operating Expenses", 
                     "Administrative Expenses", "Other Expenses"]
                )
                
                if expense_accounts:
                    coa_options = {f"{acc[1]} - {acc[2]}": acc[0] for acc in expense_accounts}
                    selected_coa = st.selectbox(
                        "📋 Chart of Account",
                        options=list(coa_options.keys()),
                        index=0
                    )
                    chart_of_accounts_id = coa_options[selected_coa]
                else:
                    chart_of_accounts_id = None
                    st.info("No expense accounts found in Chart of Accounts. Please add some first.")
                
                amount = st.number_input("💰 Amount (Rs)", min_value=1.0, step=100.0)
            
            with col2:
                mode = st.selectbox("💳 Mode", ["CASH", "BANK", "CHEQUE", "ONLINE"])
                date_recorded = st.date_input("📅 Date", date.today())
            
            description = st.text_area("📝 Description")
            
            if cust_id:
                st.info(f"👤 This expense is linked to customer: {cust_name}")
            
            if st.form_submit_button("✅ Record Expense", use_container_width=True, type="primary"):
                if amount > 0:
                    conn = get_db()
                    try:
                        conn.execute("""
                            INSERT INTO expenses (
                                expense_id, expense_type, chart_of_accounts_id,
                                amount, description, date, customer_id, created_by
                            ) VALUES (?,?,?,?,?,?,?,?)
                        """, (
                            generate_id('EXP'), expense_type, chart_of_accounts_id,
                            amount, description, date_recorded,
                            cust_id if cust_id else None,
                            st.session_state.user['id']
                        ))
                        
                        conn.execute("""
                            INSERT INTO transactions (
                                transaction_id, account_id, transaction_type,
                                amount, balance_after, description,
                                reference_type, voucher_type, voucher_number,
                                created_by
                            ) VALUES (?,?,?,?,?,?,?,?,?,?)
                        """, (
                            generate_id('TXN'), 0, 'DEBIT',
                            amount, -amount,
                            f"Expense: {expense_type}",
                            mode, 'PAYMENT',
                            generate_voucher_number('PAYMENT'),
                            st.session_state.user['id']
                        ))
                        
                        conn.commit()
                        conn.close()
                        
                        st.success(f"✅ Expense recorded: Rs {amount:,.2f}")
                        if cust_id:
                            st.success(f"👤 Linked to customer: {cust_name}")
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                else:
                    st.error("❌ Please enter a valid amount")
    
    with tab3:
        st.markdown("### 📊 Income Summary")
        
        cust_filter = st.selectbox(
            "👤 Filter by Customer",
            ["All Customers"] + [f"{c[0]} - {c[1]}" for c in c.execute("SELECT id, first_name || ' ' || last_name FROM customers ORDER BY first_name").fetchall()],
            key="income_filter"
        )
        
        if cust_filter != "All Customers":
            customer_id = int(cust_filter.split(" - ")[0])
            income_data = c.execute("""
                SELECT i.id, i.income_id, i.income_type, 
                       c.account_name as chart_account, i.amount, 
                       i.description, i.date, i.created_at,
                       cu.first_name || ' ' || cu.last_name as customer
                FROM income i
                LEFT JOIN chart_of_accounts c ON i.chart_of_accounts_id = c.id
                LEFT JOIN customers cu ON i.customer_id = cu.id
                WHERE i.customer_id = ?
                ORDER BY i.created_at DESC
            """, (customer_id,)).fetchall()
        else:
            income_data = c.execute("""
                SELECT i.id, i.income_id, i.income_type, 
                       c.account_name as chart_account, i.amount, 
                       i.description, i.date, i.created_at,
                       cu.first_name || ' ' || cu.last_name as customer
                FROM income i
                LEFT JOIN chart_of_accounts c ON i.chart_of_accounts_id = c.id
                LEFT JOIN customers cu ON i.customer_id = cu.id
                ORDER BY i.created_at DESC
            """).fetchall()
        
        if income_data:
            df = pd.DataFrame(income_data, columns=['ID', 'Income ID', 'Type', 'Chart Account', 'Amount', 'Description', 'Date', 'Created', 'Customer'])
            st.dataframe(
                df.style.format({
                    'Amount': 'Rs {:,.2f}'
                }),
                use_container_width=True
            )
            
            total_income = df['Amount'].sum()
            st.info(f"💰 Total Income: Rs {total_income:,.2f}")
            
            if 'Chart Account' in df.columns:
                chart_summary = df.groupby('Chart Account')['Amount'].sum().reset_index()
                if not chart_summary.empty:
                    st.markdown("### 📊 Income by Chart Account")
                    st.dataframe(
                        chart_summary.style.format({
                            'Amount': 'Rs {:,.2f}'
                        }),
                        use_container_width=True
                    )
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📥 Download Income CSV",
                    df.to_csv(index=False),
                    "income.csv",
                    "text/csv"
                )
            
            with col2:
                with st.expander("🗑️ Delete Income Record"):
                    inc_id = st.text_input("Enter Income ID to delete:")
                    if inc_id:
                        if st.button("🗑️ Delete Income", use_container_width=True, type="secondary"):
                            if st.checkbox("☑️ Confirm delete? This cannot be undone!"):
                                try:
                                    conn = get_db()
                                    inc = conn.execute("SELECT id FROM income WHERE income_id=?", (inc_id,)).fetchone()
                                    if inc:
                                        conn.execute("DELETE FROM income WHERE income_id=?", (inc_id,))
                                        conn.commit()
                                        conn.close()
                                        st.success("✅ Income record deleted successfully!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Income record not found!")
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")
        else:
            st.info("No income recorded")
    
    with tab4:
        st.markdown("### 📊 Expense Summary")
        
        cust_filter = st.selectbox(
            "👤 Filter by Customer",
            ["All Customers"] + [f"{c[0]} - {c[1]}" for c in c.execute("SELECT id, first_name || ' ' || last_name FROM customers ORDER BY first_name").fetchall()],
            key="expense_filter"
        )
        
        if cust_filter != "All Customers":
            customer_id = int(cust_filter.split(" - ")[0])
            expense_data = c.execute("""
                SELECT e.id, e.expense_id, e.expense_type, 
                       c.account_name as chart_account, e.amount, 
                       e.description, e.date, e.created_at,
                       cu.first_name || ' ' || cu.last_name as customer
                FROM expenses e
                LEFT JOIN chart_of_accounts c ON e.chart_of_accounts_id = c.id
                LEFT JOIN customers cu ON e.customer_id = cu.id
                WHERE e.customer_id = ?
                ORDER BY e.created_at DESC
            """, (customer_id,)).fetchall()
        else:
            expense_data = c.execute("""
                SELECT e.id, e.expense_id, e.expense_type, 
                       c.account_name as chart_account, e.amount, 
                       e.description, e.date, e.created_at,
                       cu.first_name || ' ' || cu.last_name as customer
                FROM expenses e
                LEFT JOIN chart_of_accounts c ON e.chart_of_accounts_id = c.id
                LEFT JOIN customers cu ON e.customer_id = cu.id
                ORDER BY e.created_at DESC
            """).fetchall()
        
        if expense_data:
            df = pd.DataFrame(expense_data, columns=['ID', 'Expense ID', 'Type', 'Chart Account', 'Amount', 'Description', 'Date', 'Created', 'Customer'])
            st.dataframe(
                df.style.format({
                    'Amount': 'Rs {:,.2f}'
                }),
                use_container_width=True
            )
            
            total_expense = df['Amount'].sum()
            st.info(f"💸 Total Expenses: Rs {total_expense:,.2f}")
            
            if 'Chart Account' in df.columns:
                chart_summary = df.groupby('Chart Account')['Amount'].sum().reset_index()
                if not chart_summary.empty:
                    st.markdown("### 📊 Expenses by Chart Account")
                    st.dataframe(
                        chart_summary.style.format({
                            'Amount': 'Rs {:,.2f}'
                        }),
                        use_container_width=True
                    )
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📥 Download Expense CSV",
                    df.to_csv(index=False),
                    "expenses.csv",
                    "text/csv"
                )
            
            with col2:
                with st.expander("🗑️ Delete Expense Record"):
                    exp_id = st.text_input("Enter Expense ID to delete:")
                    if exp_id:
                        if st.button("🗑️ Delete Expense", use_container_width=True, type="secondary"):
                            if st.checkbox("☑️ Confirm delete? This cannot be undone!"):
                                try:
                                    conn = get_db()
                                    exp = conn.execute("SELECT id FROM expenses WHERE expense_id=?", (exp_id,)).fetchone()
                                    if exp:
                                        conn.execute("DELETE FROM expenses WHERE expense_id=?", (exp_id,))
                                        conn.commit()
                                        conn.close()
                                        st.success("✅ Expense record deleted successfully!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Expense record not found!")
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")
        else:
            st.info("No expenses recorded")
    
    c.close()

# ==================== INTEREST CALCULATION ====================
def interest_calculation():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    st.markdown("### 📊 Interest Calculation")
    
    c = get_db()
    
    current_rate = get_current_sb_interest_rate()
    st.info(f"📈 Current SB Interest Rate: **{current_rate}%** per annum")
    
    col1, col2 = st.columns(2)
    with col1:
        from_date = st.date_input("📅 From Date", date.today().replace(day=1))
    with col2:
        to_date = st.date_input("📅 To Date", date.today())
    
    cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
        "👤 Calculate for specific customer (Optional)",
        "int_customer"
    )
    
    use_custom_rate = st.checkbox("🔧 Use custom rate for this calculation")
    custom_rate = None
    if use_custom_rate:
        custom_rate = st.number_input(
            "📊 Custom Rate (%)",
            min_value=0.0,
            max_value=10.0,
            value=current_rate,
            step=0.25
        )
    
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
                st.warning("No SB accounts found for interest calculation")
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
                        'Balance': 'Rs {:,.2f}',
                        'Interest': 'Rs {:,.2f}',
                        'Rate': '{:.2f}%'
                    }),
                    use_container_width=True
                )
                
                st.success(f"✅ Interest Posted: Rs {total_interest:,.2f}")
                st.balloons()
            else:
                st.info("No interest calculated for this period")
                
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
        df = pd.DataFrame(recent, columns=['ID', 'Date', 'Customer', 'Principal', 'Rate', 'Interest', 'Days'])
        st.dataframe(
            df.style.format({
                'Principal': 'Rs {:,.2f}',
                'Interest': 'Rs {:,.2f}',
                'Rate': '{:.2f}%'
            }),
            use_container_width=True
        )
        
        with st.expander("🗑️ Delete Interest Record"):
            int_id = st.text_input("Enter Interest Calculation ID to delete:")
            if int_id:
                if st.button("🗑️ Delete Interest Record", use_container_width=True, type="secondary"):
                    if st.checkbox("☑️ Confirm delete? This cannot be undone!"):
                        try:
                            conn = get_db()
                            conn.execute("DELETE FROM interest_calculations WHERE id=?", (int_id,))
                            conn.commit()
                            conn.close()
                            st.success("✅ Interest record deleted successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")

# ==================== TRIAL BALANCE ====================
def trial_balance():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    st.markdown("### ⚖️ Trial Balance")
    
    if st.button("🔄 Generate Trial Balance", use_container_width=True, type="primary"):
        trial = []
        
        # === REGULAR ASSETS ===
        for mode, name in [('CASH', 'Cash in Hand'), ('BANK', 'Cash in Bank'), ('CHEQUE', 'Cash (Cheque)')]:
            bal = c.execute("""
                SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END), 0)
                FROM transactions WHERE reference_type=?
            """, (mode,)).fetchone()[0]
            if abs(bal) > 0:
                trial.append({'head': name, 'cat': 'Asset', 'dr': max(bal, 0), 'cr': max(-bal, 0)})
        
        fd_total = c.execute("SELECT COALESCE(SUM(principal_amount), 0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        if fd_total > 0:
            trial.append({'head': 'FD Deposits Held', 'cat': 'Asset', 'dr': fd_total, 'cr': 0})
        
        rd_total = c.execute("""
            SELECT COALESCE(SUM(monthly_amount * installments_paid), 0) 
            FROM recurring_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if rd_total > 0:
            trial.append({'head': 'RD Deposits Held', 'cat': 'Asset', 'dr': rd_total, 'cr': 0})
        
        ret_total = c.execute("SELECT COALESCE(SUM(balance), 0) FROM retrieval_accounts WHERE status='ACTIVE'").fetchone()[0]
        if ret_total > 0:
            trial.append({'head': 'Retrieval Account Balance', 'cat': 'Asset', 'dr': ret_total, 'cr': 0})
        
        # === JOURNAL VOUCHER DEBIT ENTRIES (POSTED ONLY) ===
        jv_dr = c.execute("""
            SELECT je.account_head, SUM(je.debit_amount) as total
            FROM journal_entries je 
            JOIN journal_vouchers jv ON je.voucher_id = jv.id 
            WHERE jv.status='POSTED' AND je.debit_amount > 0 
            GROUP BY je.account_head
            ORDER BY total DESC
        """).fetchall()
        
        for e in jv_dr:
            if e[1] > 0:
                trial.append({'head': f"JV: {e[0]}", 'cat': 'JV Debit', 'dr': e[1], 'cr': 0})
        
        # === JOURNAL VOUCHER CREDIT ENTRIES (POSTED ONLY) ===
        jv_cr = c.execute("""
            SELECT je.account_head, SUM(je.credit_amount) as total
            FROM journal_entries je 
            JOIN journal_vouchers jv ON je.voucher_id = jv.id 
            WHERE jv.status='POSTED' AND je.credit_amount > 0 
            GROUP BY je.account_head
            ORDER BY total DESC
        """).fetchall()
        
        for e in jv_cr:
            if e[1] > 0:
                trial.append({'head': f"JV: {e[0]}", 'cat': 'JV Credit', 'dr': 0, 'cr': e[1]})
        
        # === REGULAR LIABILITIES ===
        sb_total = c.execute("SELECT COALESCE(SUM(balance), 0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb_total > 0:
            trial.append({'head': 'SB Deposits', 'cat': 'Liability', 'dr': 0, 'cr': sb_total})
        
        sb_int = c.execute("SELECT COALESCE(SUM(total_interest_earned), 0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb_int > 0:
            trial.append({'head': 'SB Interest Payable', 'cat': 'Liability', 'dr': 0, 'cr': sb_int})
        
        # === INCOME ===
        income_data = c.execute("""
            SELECT 
                COALESCE(c.account_name, i.income_type) as income_name,
                SUM(i.amount) as total
            FROM income i
            LEFT JOIN chart_of_accounts c ON i.chart_of_accounts_id = c.id
            GROUP BY income_name
            ORDER BY total DESC
        """).fetchall()
        
        for item in income_data:
            if item[1] > 0:
                trial.append({'head': item[0], 'cat': 'Income', 'dr': 0, 'cr': item[1]})
        
        # === EXPENSES ===
        expense_data = c.execute("""
            SELECT 
                COALESCE(c.account_name, e.expense_type) as expense_name,
                SUM(e.amount) as total
            FROM expenses e
            LEFT JOIN chart_of_accounts c ON e.chart_of_accounts_id = c.id
            GROUP BY expense_name
            ORDER BY total DESC
        """).fetchall()
        
        for item in expense_data:
            if item[1] > 0:
                trial.append({'head': item[0], 'cat': 'Expense', 'dr': item[1], 'cr': 0})
        
        # === CAPITAL ===
        tdr = sum(i['dr'] for i in trial)
        tcr = sum(i['cr'] for i in trial)
        
        if abs(tdr - tcr) > 0.01:
            diff = tdr - tcr
            if diff > 0:
                trial.append({'head': 'Capital/Equity', 'cat': 'Capital', 'dr': 0, 'cr': diff})
            else:
                trial.append({'head': 'Capital/Equity', 'cat': 'Capital', 'dr': -diff, 'cr': 0})
        
        # === DISPLAY ===
        if trial:
            df = pd.DataFrame(trial)
            final_tdr = sum(i['dr'] for i in trial)
            final_tcr = sum(i['cr'] for i in trial)
            
            asset_total = sum(i['dr'] for i in trial if i['cat'] == 'Asset')
            liability_total = sum(i['cr'] for i in trial if i['cat'] == 'Liability')
            income_total = sum(i['cr'] for i in trial if i['cat'] == 'Income')
            expense_total = sum(i['dr'] for i in trial if i['cat'] == 'Expense')
            jv_total_dr = sum(i['dr'] for i in trial if i['cat'] == 'JV Debit')
            jv_total_cr = sum(i['cr'] for i in trial if i['cat'] == 'JV Credit')
            capital = next((i['cr'] for i in trial if i['cat'] == 'Capital' and i['cr'] > 0), 
                          next((i['dr'] for i in trial if i['cat'] == 'Capital' and i['dr'] > 0), 0))
            
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("📊 Assets (Dr)", f"Rs {asset_total:,.2f}")
            col2.metric("📊 Liabilities (Cr)", f"Rs {liability_total:,.2f}")
            col3.metric("💰 Income (Cr)", f"Rs {income_total:,.2f}")
            col4.metric("💸 Expenses (Dr)", f"Rs {expense_total:,.2f}")
            col5.metric("📝 JV Total", f"Dr: Rs {jv_total_dr:,.2f} / Cr: Rs {jv_total_cr:,.2f}")
            
            st.info(f"💰 **Capital/Equity: Rs {capital:,.2f}**")
            
            display_df = df[['head', 'cat', 'dr', 'cr']].rename(columns={
                'head': 'Account Head',
                'cat': 'Category',
                'dr': 'Debit (Dr)',
                'cr': 'Credit (Cr)'
            })
            
            st.dataframe(
                display_df.style.format({
                    'Debit (Dr)': 'Rs {:,.2f}',
                    'Credit (Cr)': 'Rs {:,.2f}'
                }),
                use_container_width=True,
                height=500
            )
            
            st.markdown(f"**Total Debit: Rs {final_tdr:,.2f} | Total Credit: Rs {final_tcr:,.2f}**")
            
            if abs(final_tdr - final_tcr) < 0.01:
                st.success("✅ **PERFECTLY BALANCED!** 🎉")
                st.markdown(f"""
                ### 📊 Balance Sheet Equation:
                **Assets (Rs {asset_total:,.2f}) = Liabilities (Rs {liability_total:,.2f}) + Capital (Rs {capital:,.2f})**
                """)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "📥 Download CSV",
                        df.to_csv(index=False),
                        "trial_balance.csv",
                        "text/csv"
                    )
                with col2:
                    if st.button("📄 Print/PDF Trial Balance", use_container_width=True):
                        content = [
                            "⚖️ TRIAL BALANCE",
                            "=" * 50,
                            f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
                            "",
                            f"Total Debit: Rs {final_tdr:,.2f}",
                            f"Total Credit: Rs {final_tcr:,.2f}",
                            "",
                            f"Journal Vouchers - Debit: Rs {jv_total_dr:,.2f}",
                            f"Journal Vouchers - Credit: Rs {jv_total_cr:,.2f}",
                            "",
                            "DETAILED TRIAL BALANCE:",
                            "-" * 50
                        ]
                        
                        for item in trial:
                            content.append(f"{item['head']} | {item['cat']} | Rs {item['dr']:,.2f} | Rs {item['cr']:,.2f}")
                        
                        content.append("")
                        content.append(f"Assets (Dr): Rs {asset_total:,.2f}")
                        content.append(f"Liabilities (Cr): Rs {liability_total:,.2f}")
                        content.append(f"Income (Cr): Rs {income_total:,.2f}")
                        content.append(f"Expenses (Dr): Rs {expense_total:,.2f}")
                        content.append(f"Capital/Equity: Rs {capital:,.2f}")
                        
                        pdf_file = create_pdf("Trial Balance Report", content, "trial_balance")
                        if pdf_file:
                            create_download_button(pdf_file, "trial_balance", "📥 Download PDF Report")
            else:
                st.error(f"❌ Difference: Rs {abs(final_tdr - final_tcr):,.2f}")
    
    c.close()

# ==================== BALANCE SHEET ====================
def balance_sheet():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    st.markdown("### 📋 Balance Sheet")
    
    if st.button("🔄 Generate Balance Sheet", use_container_width=True, type="primary"):
        assets = []
        liabilities = []
        ta = 0
        tl = 0
        
        # === REGULAR ASSETS ===
        for mode, name in [('CASH', 'Cash in Hand'), ('BANK', 'Cash in Bank'), ('CHEQUE', 'Cash (Cheque)')]:
            bal = c.execute("""
                SELECT COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE -amount END), 0)
                FROM transactions WHERE reference_type=?
            """, (mode,)).fetchone()[0]
            if bal > 0:
                assets.append({'name': name, 'amount': bal})
                ta += bal
        
        fd_total = c.execute("SELECT COALESCE(SUM(principal_amount), 0) FROM fixed_deposits WHERE status='ACTIVE'").fetchone()[0]
        if fd_total > 0:
            assets.append({'name': 'FD Deposits Held', 'amount': fd_total})
            ta += fd_total
        
        rd_total = c.execute("""
            SELECT COALESCE(SUM(monthly_amount * installments_paid), 0) 
            FROM recurring_deposits WHERE status='ACTIVE'
        """).fetchone()[0]
        if rd_total > 0:
            assets.append({'name': 'RD Deposits Held', 'amount': rd_total})
            ta += rd_total
        
        ret_total = c.execute("SELECT COALESCE(SUM(balance), 0) FROM retrieval_accounts WHERE status='ACTIVE'").fetchone()[0]
        if ret_total > 0:
            assets.append({'name': 'Retrieval Account Balance', 'amount': ret_total})
            ta += ret_total
        
        # === JV ASSETS (POSTED JV DEBIT ENTRIES) ===
        jv_assets = c.execute("""
            SELECT je.account_head, SUM(je.debit_amount) as total
            FROM journal_entries je 
            JOIN journal_vouchers jv ON je.voucher_id = jv.id 
            WHERE jv.status='POSTED' AND je.debit_amount > 0 
            GROUP BY je.account_head
            ORDER BY total DESC
        """).fetchall()
        
        for e in jv_assets:
            if e[1] > 0:
                assets.append({'name': f"JV: {e[0]}", 'amount': e[1]})
                ta += e[1]
        
        # === REGULAR LIABILITIES ===
        sb_total = c.execute("SELECT COALESCE(SUM(balance), 0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb_total > 0:
            liabilities.append({'name': 'SB Deposits', 'amount': sb_total})
            tl += sb_total
        
        sb_int = c.execute("SELECT COALESCE(SUM(total_interest_earned), 0) FROM accounts WHERE account_type='SB' AND status='ACTIVE'").fetchone()[0]
        if sb_int > 0:
            liabilities.append({'name': 'SB Interest Payable', 'amount': sb_int})
            tl += sb_int
        
        # === JV LIABILITIES (POSTED JV CREDIT ENTRIES) ===
        jv_liabilities = c.execute("""
            SELECT je.account_head, SUM(je.credit_amount) as total
            FROM journal_entries je 
            JOIN journal_vouchers jv ON je.voucher_id = jv.id 
            WHERE jv.status='POSTED' AND je.credit_amount > 0 
            GROUP BY je.account_head
            ORDER BY total DESC
        """).fetchall()
        
        for e in jv_liabilities:
            if e[1] > 0:
                liabilities.append({'name': f"JV: {e[0]}", 'amount': e[1]})
                tl += e[1]
        
        # === INCOME & EXPENSES ===
        income_total = c.execute("SELECT COALESCE(SUM(amount), 0) FROM income").fetchone()[0]
        expense_total = c.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses").fetchone()[0]
        
        # === CAPITAL ===
        capital = ta - tl
        
        # Calculate net profit/loss
        net_profit = income_total - expense_total
        
        # Total equity
        total_equity = capital + net_profit
        
        # === DISPLAY ===
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📈 ASSETS (What Bank Owns)")
            st.markdown("---")
            for item in assets:
                st.markdown(f"💰 **{item['name']}**: Rs {item['amount']:,.2f}")
            st.markdown("---")
            st.markdown(f"### **Total Assets: Rs {ta:,.2f}**")
        
        with col2:
            st.markdown("### 📉 LIABILITIES (What Bank Owes)")
            st.markdown("---")
            for item in liabilities:
                st.markdown(f"💳 **{item['name']}**: Rs {item['amount']:,.2f}")
            st.markdown("---")
            st.markdown(f"### **Total Liabilities: Rs {tl:,.2f}**")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 💰 EQUITY")
            st.markdown("---")
            st.markdown(f"**Capital**: Rs {capital:,.2f}")
            if net_profit > 0:
                st.markdown(f"**Add: Net Profit**: Rs {net_profit:,.2f}")
            elif net_profit < 0:
                st.markdown(f"**Less: Net Loss**: Rs {abs(net_profit):,.2f}")
            st.markdown("---")
            st.markdown(f"### **Total Equity: Rs {total_equity:,.2f}**")
        
        with col2:
            st.markdown("### 📊 Income & Expenses")
            st.markdown("---")
            st.markdown(f"💰 **Total Income**: Rs {income_total:,.2f}")
            st.markdown(f"💸 **Total Expenses**: Rs {expense_total:,.2f}")
            st.markdown("---")
            if net_profit >= 0:
                st.success(f"### 🎉 Net Profit: Rs {net_profit:,.2f}")
            else:
                st.error(f"### 📉 Net Loss: Rs {abs(net_profit):,.2f}")
        
        st.markdown("---")
        
        if abs(ta - (tl + total_equity)) < 0.01:
            st.success(f"""
            ### ✅ PERFECTLY BALANCED! 🎉
            
            **Assets (Rs {ta:,.2f}) = Liabilities (Rs {tl:,.2f}) + Equity (Rs {total_equity:,.2f})**
            """)
            
            col1, col2 = st.columns(2)
            with col1:
                bs_data = []
                for item in assets:
                    bs_data.append({'Category': 'Asset', 'Name': item['name'], 'Amount': item['amount']})
                for item in liabilities:
                    bs_data.append({'Category': 'Liability', 'Name': item['name'], 'Amount': item['amount']})
                bs_data.append({'Category': 'Equity', 'Name': 'Total Equity', 'Amount': total_equity})
                
                df_bs = pd.DataFrame(bs_data)
                st.download_button(
                    "📥 Download CSV",
                    df_bs.to_csv(index=False),
                    "balance_sheet.csv",
                    "text/csv"
                )
            
            with col2:
                if st.button("📄 Print/PDF Balance Sheet", use_container_width=True):
                    content = [
                        "📋 BALANCE SHEET",
                        "=" * 50,
                        f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
                        "",
                        "ASSETS:",
                        "-" * 30
                    ]
                    for item in assets:
                        content.append(f"{item['name']}: Rs {item['amount']:,.2f}")
                    content.append(f"Total Assets: Rs {ta:,.2f}")
                    content.append("")
                    content.append("LIABILITIES:")
                    content.append("-" * 30)
                    for item in liabilities:
                        content.append(f"{item['name']}: Rs {item['amount']:,.2f}")
                    content.append(f"Total Liabilities: Rs {tl:,.2f}")
                    content.append("")
                    content.append("EQUITY:")
                    content.append("-" * 30)
                    content.append(f"Capital: Rs {capital:,.2f}")
                    if net_profit > 0:
                        content.append(f"Net Profit: Rs {net_profit:,.2f}")
                    elif net_profit < 0:
                        content.append(f"Net Loss: Rs {abs(net_profit):,.2f}")
                    content.append(f"Total Equity: Rs {total_equity:,.2f}")
                    content.append("")
                    content.append(f"CHECK: Assets (Rs {ta:,.2f}) = Liabilities (Rs {tl:,.2f}) + Equity (Rs {total_equity:,.2f})")
                    content.append("")
                    content.append("✅ PERFECTLY BALANCED!")
                    
                    pdf_file = create_pdf("Balance Sheet Report", content, "balance_sheet")
                    if pdf_file:
                        create_download_button(pdf_file, "balance_sheet", "📥 Download PDF Report")
        else:
            st.error(f"❌ Difference: Rs {abs(ta - (tl + total_equity)):,.2f}")
    
    c.close()

# ==================== PROFIT & LOSS ====================
def profit_loss():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    st.markdown("### 📈 Profit & Loss Statement")
    
    col1, col2 = st.columns(2)
    with col1:
        from_date = st.date_input("📅 From Date", date.today().replace(month=1, day=1))
    with col2:
        to_date = st.date_input("📅 To Date", date.today())
    
    if st.button("🔄 Generate P&L", use_container_width=True, type="primary"):
        income_data = c.execute("""
            SELECT 
                COALESCE(c.account_name, i.income_type) as income_name,
                SUM(i.amount) as total
            FROM income i
            LEFT JOIN chart_of_accounts c ON i.chart_of_accounts_id = c.id
            WHERE DATE(i.date) BETWEEN ? AND ?
            GROUP BY income_name
            ORDER BY total DESC
        """, (from_date, to_date)).fetchall()
        
        expense_data = c.execute("""
            SELECT 
                COALESCE(c.account_name, e.expense_type) as expense_name,
                SUM(e.amount) as total
            FROM expenses e
            LEFT JOIN chart_of_accounts c ON e.chart_of_accounts_id = c.id
            WHERE DATE(e.date) BETWEEN ? AND ?
            GROUP BY expense_name
            ORDER BY total DESC
        """, (from_date, to_date)).fetchall()
        
        total_income = sum(i[1] for i in income_data)
        total_expense = sum(e[1] for e in expense_data)
        net_profit = total_income - total_expense
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 💰 INCOME")
            st.markdown("---")
            if income_data:
                for item in income_data:
                    st.markdown(f"📊 **{item[0]}**: Rs {item[1]:,.2f}")
                st.markdown("---")
                st.markdown(f"### **Total Income: Rs {total_income:,.2f}**")
            else:
                st.info("No income in this period")
        
        with col2:
            st.markdown("### 💸 EXPENSES")
            st.markdown("---")
            if expense_data:
                for item in expense_data:
                    st.markdown(f"📊 **{item[0]}**: Rs {item[1]:,.2f}")
                st.markdown("---")
                st.markdown(f"### **Total Expenses: Rs {total_expense:,.2f}**")
            else:
                st.info("No expenses in this period")
        
        st.markdown("---")
        
        if net_profit >= 0:
            st.success(f"### 🎉 Net Profit: Rs {net_profit:,.2f}")
            st.balloons()
        else:
            st.error(f"### 📉 Net Loss: Rs {abs(net_profit):,.2f}")
        
        if total_income > 0:
            profit_margin = (net_profit / total_income) * 100
            st.info(f"📊 Profit Margin: {profit_margin:.1f}%")
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📥 Download CSV",
                pd.DataFrame({
                    'Type': ['Income', 'Expense', 'Net'],
                    'Amount': [total_income, total_expense, net_profit]
                }).to_csv(index=False),
                "profit_loss.csv",
                "text/csv"
            )
        
        with col2:
            if st.button("📄 Print/PDF P&L", use_container_width=True):
                content = [
                    "📈 PROFIT & LOSS STATEMENT",
                    "=" * 50,
                    f"Period: {from_date.strftime('%d-%m-%Y')} to {to_date.strftime('%d-%m-%Y')}",
                    f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
                    "",
                    "INCOME:",
                    "-" * 30
                ]
                for item in income_data:
                    content.append(f"{item[0]}: Rs {item[1]:,.2f}")
                content.append(f"Total Income: Rs {total_income:,.2f}")
                content.append("")
                content.append("EXPENSES:")
                content.append("-" * 30)
                for item in expense_data:
                    content.append(f"{item[0]}: Rs {item[1]:,.2f}")
                content.append(f"Total Expenses: Rs {total_expense:,.2f}")
                content.append("")
                if net_profit >= 0:
                    content.append(f"NET PROFIT: Rs {net_profit:,.2f}")
                    content.append(f"Profit Margin: {(net_profit/total_income*100):.1f}%")
                else:
                    content.append(f"NET LOSS: Rs {abs(net_profit):,.2f}")
                
                pdf_file = create_pdf("Profit & Loss Statement", content, "profit_loss")
                if pdf_file:
                    create_download_button(pdf_file, "profit_loss", "📥 Download PDF Report")
    
    c.close()

# ==================== REPORTS ====================
def reports():
    if st.session_state.user['role'] not in ['admin', 'staff']:
        st.error("❌ Unauthorized access!")
        return
    
    c = get_db()
    st.markdown("### 📄 Reports")
    
    report_type = st.selectbox(
        "📊 Select Report",
        ["Customer List", "Daily Transactions", "Account Statement", "Interest Summary", 
         "FD Summary", "RD Summary", "Retrieval Summary", "Income by Customer", "Expense by Customer"]
    )
    
    if report_type == "Customer List":
        st.markdown("### 👥 Customer List")
        customers = c.execute("""
            SELECT customer_id, first_name, last_name, email, phone, kyc_status, created_at
            FROM customers
            ORDER BY created_at DESC
        """).fetchall()
        
        if customers:
            df = pd.DataFrame(customers, columns=['ID', 'First', 'Last', 'Email', 'Phone', 'KYC', 'Joined'])
            st.dataframe(df, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button("📥 Download CSV", df.to_csv(index=False), "customers_list.csv", "text/csv")
            with col2:
                if st.button("📄 Print/PDF Customer List", use_container_width=True):
                    content = ["👥 CUSTOMER LIST", "=" * 50]
                    content.append(f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}")
                    content.append(f"Total Customers: {len(customers)}")
                    content.append("")
                    for cust in customers:
                        content.append(f"ID: {cust[0]} | Name: {cust[1]} {cust[2]} | Email: {cust[3]} | Phone: {cust[4]} | KYC: {cust[5]}")
                    
                    pdf_file = create_pdf("Customer List Report", content, "customer_list")
                    if pdf_file:
                        create_download_button(pdf_file, "customer_list", "📥 Download PDF Report")
        else:
            st.info("No customers found")
    
    elif report_type == "Daily Transactions":
        report_date = st.date_input("📅 Date", date.today())
        
        transactions = c.execute("""
            SELECT t.transaction_id, 
                   COALESCE(c.first_name||' '||c.last_name, 'System') as customer,
                   t.transaction_type, t.amount, t.reference_type,
                   t.description, t.created_at
            FROM transactions t
            LEFT JOIN accounts a ON t.account_id = a.id
            LEFT JOIN customers c ON a.customer_id = c.id
            WHERE DATE(t.created_at) = ?
            ORDER BY t.created_at DESC
        """, (report_date,)).fetchall()
        
        if transactions:
            df = pd.DataFrame(transactions, columns=['Txn ID', 'Customer', 'Type', 'Amount', 'Mode', 'Description', 'Time'])
            df['Time'] = pd.to_datetime(df['Time']).dt.strftime('%I:%M %p')
            st.dataframe(df.style.format({'Amount': 'Rs {:,.2f}'}), use_container_width=True)
            
            total_credit = df[df['Type'] == 'CREDIT']['Amount'].sum()
            total_debit = df[df['Type'] == 'DEBIT']['Amount'].sum()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("💰 Credits", f"Rs {total_credit:,.2f}")
            col2.metric("💳 Debits", f"Rs {total_debit:,.2f}")
            col3.metric("📊 Net", f"Rs {(total_credit - total_debit):,.2f}")
            
            if st.button("📄 Print/PDF Daily Transactions", use_container_width=True):
                content = [
                    f"📊 DAILY TRANSACTIONS REPORT - {report_date.strftime('%d-%m-%Y')}",
                    "=" * 50,
                    f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
                    f"Total Transactions: {len(transactions)}",
                    f"Total Credits: Rs {total_credit:,.2f}",
                    f"Total Debits: Rs {total_debit:,.2f}",
                    f"Net: Rs {(total_credit - total_debit):,.2f}",
                    "",
                    "TRANSACTION DETAILS:",
                    "-" * 50
                ]
                for txn in transactions:
                    content.append(f"{txn[0]} | {txn[1]} | {txn[2]} | Rs {txn[3]:,.2f} | {txn[4]} | {txn[6]}")
                
                pdf_file = create_pdf("Daily Transactions Report", content, "daily_transactions")
                if pdf_file:
                    create_download_button(pdf_file, "daily_transactions", "📥 Download PDF Report")
        else:
            st.info("No transactions on this date")
    
    elif report_type == "Account Statement":
        cust_id, cust_name, acc_id, acc_number, balance = customer_selector(
            "👤 Select Customer",
            "report_customer"
        )
        
        if cust_id and acc_id:
            col1, col2 = st.columns(2)
            with col1:
                from_date = st.date_input("📅 From", date.today() - timedelta(days=30))
            with col2:
                to_date = st.date_input("📅 To", date.today())
            
            if st.button("📊 Generate Statement"):
                txns = c.execute("""
                    SELECT transaction_id, transaction_type, amount,
                           balance_after, description, reference_type,
                           created_at
                    FROM transactions
                    WHERE account_id=? AND DATE(created_at) BETWEEN ? AND ?
                    ORDER BY created_at DESC
                """, (acc_id, from_date, to_date)).fetchall()
                
                if txns:
                    df = pd.DataFrame(txns, columns=['ID', 'Type', 'Amount', 'Balance', 'Description', 'Mode', 'Date'])
                    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%d-%m-%Y %I:%M %p')
                    st.dataframe(
                        df.style.format({
                            'Amount': 'Rs {:,.2f}',
                            'Balance': 'Rs {:,.2f}'
                        }),
                        use_container_width=True
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            "📥 Download Statement CSV",
                            df.to_csv(index=False),
                            f"statement_{acc_number}_{from_date}_{to_date}.csv",
                            "text/csv"
                        )
                    with col2:
                        if st.button("📄 Print/PDF Statement", use_container_width=True):
                            content = [
                                f"📋 ACCOUNT STATEMENT - {acc_number}",
                                "=" * 50,
                                f"Customer: {cust_name}",
                                f"Period: {from_date.strftime('%d-%m-%Y')} to {to_date.strftime('%d-%m-%Y')}",
                                f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
                                "",
                                "TRANSACTION DETAILS:",
                                "-" * 50
                            ]
                            for txn in txns:
                                content.append(f"{txn[0]} | {txn[1]} | Rs {txn[2]:,.2f} | Rs {txn[3]:,.2f} | {txn[4]} | {txn[6]}")
                            
                            content.append("")
                            content.append(f"Opening Balance: Rs {balance:,.2f}")
                            content.append(f"Closing Balance: Rs {txns[0][3] if txns else balance:,.2f}")
                            
                            pdf_file = create_pdf(f"Account Statement - {acc_number}", content, f"statement_{acc_number}")
                            if pdf_file:
                                create_download_button(pdf_file, f"statement_{acc_number}", "📥 Download PDF Report")
                else:
                    st.info("No transactions in this period")
    
    elif report_type == "Interest Summary":
        st.markdown("### 📊 Interest Summary")
        interest_data = c.execute("""
            SELECT c.first_name||' '||c.last_name as customer,
                   a.account_number,
                   COALESCE(a.total_interest_earned, 0) as interest_earned,
                   a.interest_rate
            FROM customers c
            JOIN accounts a ON c.id = a.customer_id
            WHERE a.account_type='SB' AND a.status='ACTIVE'
            ORDER BY interest_earned DESC
        """).fetchall()
        
        if interest_data:
            df = pd.DataFrame(interest_data, columns=['Customer', 'Account', 'Interest Earned', 'Rate'])
            st.dataframe(
                df.style.format({
                    'Interest Earned': 'Rs {:,.2f}',
                    'Rate': '{:.2f}%'
                }),
                use_container_width=True
            )
            total_interest = df['Interest Earned'].sum()
            st.info(f"💰 Total Interest Earned: Rs {total_interest:,.2f}")
            
            if st.button("📄 Print/PDF Interest Summary", use_container_width=True):
                content = [
                    "📊 INTEREST SUMMARY REPORT",
                    "=" * 50,
                    f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
                    f"Total Interest Earned: Rs {total_interest:,.2f}",
                    "",
                    "DETAILED SUMMARY:",
                    "-" * 50
                ]
                for item in interest_data:
                    content.append(f"{item[0]} | {item[1]} | Rs {item[2]:,.2f} | {item[3]}%")
                
                pdf_file = create_pdf("Interest Summary Report", content, "interest_summary")
                if pdf_file:
                    create_download_button(pdf_file, "interest_summary", "📥 Download PDF Report")
        else:
            st.info("No interest data available")
    
    elif report_type == "FD Summary":
        st.markdown("### 📊 FD Summary Report")
        
        fds = c.execute("""
            SELECT fd.fd_number, c.first_name||' '||c.last_name as customer,
                   fd.principal_amount, fd.interest_rate,
                   fd.start_date, fd.maturity_date,
                   fd.maturity_amount, fd.status
            FROM fixed_deposits fd
            JOIN accounts a ON fd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            ORDER BY fd.status, fd.maturity_date
        """).fetchall()
        
        if fds:
            df = pd.DataFrame(fds, columns=['FD No', 'Customer', 'Principal', 'Rate', 'Start Date', 'Maturity Date', 'Maturity Amount', 'Status'])
            st.dataframe(
                df.style.format({
                    'Principal': 'Rs {:,.2f}',
                    'Maturity Amount': 'Rs {:,.2f}',
                    'Rate': '{:.2f}%'
                }),
                use_container_width=True
            )
            
            active_fd = df[df['Status'] == 'ACTIVE']['Principal'].sum()
            closed_fd = df[df['Status'] == 'CLOSED']['Principal'].sum()
            total_fd = df['Principal'].sum()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("🟢 Active FD", f"Rs {active_fd:,.2f}")
            col2.metric("🔴 Closed FD", f"Rs {closed_fd:,.2f}")
            col3.metric("💰 Total FD", f"Rs {total_fd:,.2f}")
            
            if st.button("📄 Print/PDF FD Summary", use_container_width=True):
                content = [
                    "📊 FIXED DEPOSITS SUMMARY REPORT",
                    "=" * 50,
                    f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
                    f"Total FDs: {len(fds)}",
                    f"Active FD Amount: Rs {active_fd:,.2f}",
                    f"Closed FD Amount: Rs {closed_fd:,.2f}",
                    f"Total FD Amount: Rs {total_fd:,.2f}",
                    "",
                    "FD DETAILS:",
                    "-" * 50
                ]
                for fd in fds:
                    content.append(f"{fd[0]} | {fd[1]} | Rs {fd[2]:,.2f} | {fd[3]}% | {fd[4]} | {fd[5]} | {fd[7]}")
                
                pdf_file = create_pdf("FD Summary Report", content, "fd_summary")
                if pdf_file:
                    create_download_button(pdf_file, "fd_summary", "📥 Download PDF Report")
        else:
            st.info("No fixed deposits found")
    
    elif report_type == "RD Summary":
        st.markdown("### 📊 RD Summary Report")
        
        rds = c.execute("""
            SELECT rd.rd_number, c.first_name||' '||c.last_name as customer,
                   rd.monthly_amount, rd.installments_paid,
                   rd.total_installments, rd.interest_rate,
                   rd.start_date, rd.maturity_date,
                   rd.maturity_amount, rd.status
            FROM recurring_deposits rd
            JOIN accounts a ON rd.account_id = a.id
            JOIN customers c ON a.customer_id = c.id
            ORDER BY rd.status, rd.maturity_date
        """).fetchall()
        
        if rds:
            df = pd.DataFrame(rds, columns=['RD No', 'Customer', 'Monthly', 'Paid', 'Total', 'Rate', 'Start Date', 'Maturity Date', 'Maturity Amount', 'Status'])
            st.dataframe(
                df.style.format({
                    'Monthly': 'Rs {:,.2f}',
                    'Maturity Amount': 'Rs {:,.2f}',
                    'Rate': '{:.2f}%'
                }),
                use_container_width=True
            )
            
            active_rd = df[df['Status'] == 'ACTIVE']['Monthly'].sum()
            matured_rd = df[df['Status'] == 'MATURED']['Monthly'].sum()
            total_rd = df['Monthly'].sum()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("🟢 Active RD", f"Rs {active_rd:,.2f}")
            col2.metric("🔴 Matured RD", f"Rs {matured_rd:,.2f}")
            col3.metric("💰 Total RD", f"Rs {total_rd:,.2f}")
            
            if st.button("📄 Print/PDF RD Summary", use_container_width=True):
                content = [
                    "📊 RECURRING DEPOSITS SUMMARY REPORT",
                    "=" * 50,
                    f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
                    f"Total RDs: {len(rds)}",
                    f"Active RD Amount: Rs {active_rd:,.2f}",
                    f"Matured RD Amount: Rs {matured_rd:,.2f}",
                    f"Total RD Amount: Rs {total_rd:,.2f}",
                    "",
                    "RD DETAILS:",
                    "-" * 50
                ]
                for rd in rds:
                    content.append(f"{rd[0]} | {rd[1]} | Rs {rd[2]:,.2f} | {rd[3]}/{rd[4]} | {rd[5]}% | {rd[6]} | {rd[7]} | {rd[9]}")
                
                pdf_file = create_pdf("RD Summary Report", content, "rd_summary")
                if pdf_file:
                    create_download_button(pdf_file, "rd_summary", "📥 Download PDF Report")
        else:
            st.info("No recurring deposits found")
    
    elif report_type == "Retrieval Summary":
        st.markdown("### 📊 Retrieval Account Summary")
        
        retrieval_data = c.execute("""
            SELECT 
                c.first_name||' '||c.last_name as customer,
                ra.account_number,
                ra.balance,
                COUNT(md.id) as matured_count,
                COALESCE(SUM(md.total_amount), 0) as total_matured
            FROM customers c
            LEFT JOIN retrieval_accounts ra ON c.id = ra.customer_id AND ra.status = 'ACTIVE'
            LEFT JOIN matured_deposits md ON c.id = md.customer_id AND md.status = 'ACTIVE'
            GROUP BY c.id
            HAVING ra.balance > 0 OR COUNT(md.id) > 0
            ORDER BY ra.balance DESC
        """).fetchall()
        
        if retrieval_data:
            df = pd.DataFrame(retrieval_data, columns=['Customer', 'Account', 'Balance', 'Matured Count', 'Total Matured'])
            st.dataframe(
                df.style.format({
                    'Balance': 'Rs {:,.2f}',
                    'Total Matured': 'Rs {:,.2f}'
                }),
                use_container_width=True
            )
            
            total_balance = df['Balance'].sum()
            total_matured = df['Total Matured'].sum()
            
            col1, col2 = st.columns(2)
            col1.metric("💰 Total Retrieval Balance", f"Rs {total_balance:,.2f}")
            col2.metric("📊 Total Matured Amount", f"Rs {total_matured:,.2f}")
            
            if st.button("📄 Print/PDF Retrieval Summary", use_container_width=True):
                content = [
                    "📊 RETRIEVAL ACCOUNT SUMMARY REPORT",
                    "=" * 50,
                    f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
                    f"Total Retrieval Balance: Rs {total_balance:,.2f}",
                    f"Total Matured Amount: Rs {total_matured:,.2f}",
                    "",
                    "DETAILED SUMMARY:",
                    "-" * 50
                ]
                for item in retrieval_data:
                    content.append(f"{item[0]} | {item[1]} | Rs {item[2]:,.2f} | {item[3]} deposits")
                
                pdf_file = create_pdf("Retrieval Account Summary Report", content, "retrieval_summary")
                if pdf_file:
                    create_download_button(pdf_file, "retrieval_summary", "📥 Download PDF Report")
        else:
            st.info("No retrieval account data found")
    
    elif report_type == "Income by Customer":
        st.markdown("### 📊 Income by Customer")
        
        income_by_customer = c.execute("""
            SELECT 
                cu.first_name || ' ' || cu.last_name as customer,
                COALESCE(c.account_name, i.income_type) as income_type,
                SUM(i.amount) as total
            FROM income i
            LEFT JOIN chart_of_accounts c ON i.chart_of_accounts_id = c.id
            LEFT JOIN customers cu ON i.customer_id = cu.id
            WHERE i.customer_id IS NOT NULL
            GROUP BY cu.id, income_type
            ORDER BY total DESC
        """).fetchall()
        
        if income_by_customer:
            df = pd.DataFrame(income_by_customer, columns=['Customer', 'Income Type', 'Total'])
            st.dataframe(
                df.style.format({
                    'Total': 'Rs {:,.2f}'
                }),
                use_container_width=True
            )
            
            pivot_df = df.pivot_table(index='Customer', columns='Income Type', values='Total', aggfunc='sum', fill_value=0)
            st.markdown("### 📊 Income by Customer - Pivot View")
            st.dataframe(
                pivot_df.style.format({
                    col: 'Rs {:,.2f}' for col in pivot_df.columns
                }),
                use_container_width=True
            )
            
            st.download_button(
                "📥 Download CSV",
                df.to_csv(index=False),
                "income_by_customer.csv",
                "text/csv"
            )
        else:
            st.info("No customer-linked income found")
    
    elif report_type == "Expense by Customer":
        st.markdown("### 📊 Expense by Customer")
        
        expense_by_customer = c.execute("""
            SELECT 
                cu.first_name || ' ' || cu.last_name as customer,
                COALESCE(c.account_name, e.expense_type) as expense_type,
                SUM(e.amount) as total
            FROM expenses e
            LEFT JOIN chart_of_accounts c ON e.chart_of_accounts_id = c.id
            LEFT JOIN customers cu ON e.customer_id = cu.id
            WHERE e.customer_id IS NOT NULL
            GROUP BY cu.id, expense_type
            ORDER BY total DESC
        """).fetchall()
        
        if expense_by_customer:
            df = pd.DataFrame(expense_by_customer, columns=['Customer', 'Expense Type', 'Total'])
            st.dataframe(
                df.style.format({
                    'Total': 'Rs {:,.2f}'
                }),
                use_container_width=True
            )
            
            pivot_df = df.pivot_table(index='Customer', columns='Expense Type', values='Total', aggfunc='sum', fill_value=0)
            st.markdown("### 📊 Expense by Customer - Pivot View")
            st.dataframe(
                pivot_df.style.format({
                    col: 'Rs {:,.2f}' for col in pivot_df.columns
                }),
                use_container_width=True
            )
            
            st.download_button(
                "📥 Download CSV",
                df.to_csv(index=False),
                "expense_by_customer.csv",
                "text/csv"
            )
        else:
            st.info("No customer-linked expenses found")
    
    c.close()

# ==================== MY ACCOUNTS ====================
def my_accounts():
    c = get_db()
    uid = st.session_state.user['id']
    
    customer = c.execute("SELECT * FROM customers WHERE user_id=?", (uid,)).fetchone()
    
    if not customer:
        st.warning("⚠️ No customer profile linked to your account. Please contact bank staff.")
        c.close()
        return
    
    st.markdown(f"### 👋 Welcome, {customer[3]} {customer[4]}!")
    
    accounts = c.execute("""
        SELECT account_number, account_type, balance,
               COALESCE(total_interest_earned, 0) as interest,
               interest_rate, status
        FROM accounts
        WHERE customer_id=? AND status='ACTIVE'
    """, (customer[0],)).fetchall()
    
    if accounts:
        for acc in accounts:
            with st.expander(f"🏦 {acc[1]} Account - {acc[0]}"):
                col1, col2, col3 = st.columns(3)
                col1.metric("💰 Balance", f"Rs {acc[2]:,.2f}")
                col2.metric("📈 Interest Earned", f"Rs {acc[3]:,.2f}")
                col3.metric("📊 Interest Rate", f"{acc[4]}%")
        
        total_balance = sum(acc[2] for acc in accounts)
        total_interest = sum(acc[3] for acc in accounts)
        
        st.info(f"💰 **Total Portfolio: Rs {total_balance + total_interest:,.2f}**")
    else:
        st.info("No active accounts found")
    
    c.close()

# ==================== MY TRANSACTIONS ====================
def my_transactions():
    c = get_db()
    uid = st.session_state.user['id']
    
    customer = c.execute("SELECT id FROM customers WHERE user_id=?", (uid,)).fetchone()
    
    if not customer:
        st.warning("⚠️ No customer profile found.")
        c.close()
        return
    
    st.markdown("### 💳 Your Transactions")
    
    txns = c.execute("""
        SELECT t.transaction_id, a.account_number, t.transaction_type,
               t.amount, t.balance_after, t.description,
               t.reference_type, t.created_at
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        WHERE a.customer_id=?
        ORDER BY t.created_at DESC
        LIMIT 100
    """, (customer[0],)).fetchall()
    
    if txns:
        df = pd.DataFrame(txns, columns=['Txn ID', 'Account', 'Type', 'Amount', 'Balance', 'Description', 'Mode', 'Date'])
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%d-%m-%Y %I:%M %p')
        st.dataframe(
            df.style.format({
                'Amount': 'Rs {:,.2f}',
                'Balance': 'Rs {:,.2f}'
            }),
            use_container_width=True
        )
        
        total_credit = df[df['Type'] == 'CREDIT']['Amount'].sum()
        total_debit = df[df['Type'] == 'DEBIT']['Amount'].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Total Credits", f"Rs {total_credit:,.2f}")
        col2.metric("💳 Total Debits", f"Rs {total_debit:,.2f}")
        col3.metric("📊 Net Change", f"Rs {(total_credit - total_debit):,.2f}")
    else:
        st.info("No transactions found")
    
    c.close()

# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    main()
