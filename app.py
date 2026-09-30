import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import streamlit as st
st.set_page_config(
    page_title="Aarsha Nidhi Limited",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

import pandas as pd
from datetime import datetime, date, timedelta
import calendar
import io
import os
import time
import re
import base64
import hmac
import hashlib
import psycopg2
import plotly.express as px
import plotly.graph_objects as go
import pytz
import streamlit.components.v1 as components

@st.cache_data
def get_vsquare_logo_b64():
    for fname in ["vsquare_logo_opt.png", "vsquare_logo.png"]:
        p = os.path.join(os.path.dirname(__file__), "assets", fname)
        if os.path.exists(p):
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
    return ""

@st.cache_data
def get_vsquare_sidebar_logo_b64():
    for fname in ["vsquare_logo_user_clean.png", "vsquare_logo_exact_font.png", "vsquare_logo_flat_trans.png", "vsquare_logo_opt.png", "vsquare_logo.png"]:
        p = os.path.join(os.path.dirname(__file__), "assets", fname)
        if os.path.exists(p):
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
    return get_vsquare_logo_b64()

@st.cache_data
def get_vsquare_favicon_b64():
    for fname in ["favicon_opt.png", "favicon.png"]:
        p = os.path.join(os.path.dirname(__file__), "assets", fname)
        if os.path.exists(p):
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
    return ""

# Import database layer
from database import (
    IST, DB_NAME, USING_SUPABASE, run_query, cached_query, clear_db_cache, save_uploaded_file, 
    get_account_balance_from_jv, get_cash_balance, get_bank_balance,
    generate_cash_voucher_no, generate_bank_voucher_no, post_automated_jv,
    post_compound_jv, get_account_name, fetch_cb_voucher, fetch_bb_voucher, fetch_jv_voucher,
    get_connection, release_connection, sync_db_sequences,
    get_all_gold_loans_bundle, get_all_personal_loans_bundle,
    delete_customer_cascade, delete_personal_loan_entry, delete_gold_loan_entry,
    delete_fd_entry, delete_rd_entry, delete_jv_entry, delete_transaction_entry,
    delete_sb_account_entry, delete_cash_book_entry, delete_bank_book_entry,
    resequence_customers, resequence_cash_book, resequence_bank_book, resequence_entire_database,
    update_sb_account_details, create_or_link_sb_opening,
    update_personal_loan_details, update_gold_loan_details,
    create_or_link_personal_loan_opening, create_or_link_gold_loan_opening,
    update_fd_account_details, create_or_link_fd_opening,
    update_rd_account_details, create_or_link_rd_opening,
    get_document_data, delete_document, record_sb_transaction,
    resequence_all_accounts, reconcile_books, get_all_balances,
    record_cash_book_transaction, update_cash_book_transaction, record_bank_book_transaction,
    calculate_rd_maturity, calculate_rd_accrued_value, get_rd_ledger_rows, record_rd_installment,
    ensure_rd_installments_populated, update_rd_installment, delete_rd_installment, add_custom_rd_installment, recalculate_rd_installments_balances,
    resequence_rd_installments, pay_rd_installment, record_personal_loan_repayment, record_gold_loan_repayment
)

try:
    from database import calculate_rd_maturity, calculate_rd_accrued_value
except ImportError:
    import importlib
    import database
    try:
        importlib.reload(database)
        from database import calculate_rd_maturity, calculate_rd_accrued_value
    except ImportError:
        def calculate_rd_maturity(monthly_amount: float, interest_rate: float, tenure_months: int):
            try:
                monthly_amount = float(monthly_amount)
                interest_rate = float(interest_rate)
                tenure_months = int(tenure_months)
            except (ValueError, TypeError):
                return 0.0, 0.0, 0.0
            if monthly_amount <= 0 or tenure_months <= 0:
                return 0.0, 0.0, 0.0
            total_deposit = round(monthly_amount * tenure_months, 2)
            if interest_rate <= 0:
                return total_deposit, total_deposit, 0.0
            i = interest_rate / 400.0
            maturity_amount = sum(monthly_amount * ((1.0 + i) ** ((tenure_months - k + 1) / 3.0)) for k in range(1, tenure_months + 1))
            maturity_amount = round(maturity_amount, 2)
            return total_deposit, maturity_amount, round(maturity_amount - total_deposit, 2)

        def calculate_rd_accrued_value(monthly_amount: float, interest_rate: float, installments_paid: int):
            try:
                monthly_amount = float(monthly_amount)
                interest_rate = float(interest_rate)
                installments_paid = int(installments_paid)
            except (ValueError, TypeError):
                return 0.0, 0.0, 0.0
            if monthly_amount <= 0 or installments_paid <= 0:
                return 0.0, 0.0, 0.0
            total_paid = round(monthly_amount * installments_paid, 2)
            if interest_rate <= 0:
                return total_paid, total_paid, 0.0
            i = interest_rate / 400.0
            accrued_amount = sum(monthly_amount * ((1.0 + i) ** ((installments_paid - k + 1) / 3.0)) for k in range(1, installments_paid + 1))
            accrued_amount = round(accrued_amount, 2)
            return total_paid, accrued_amount, round(accrued_amount - total_paid, 2)

import pdf_generator

# Define IST timezone
IST = pytz.timezone('Asia/Kolkata')

# Configure Pandas global display options to prevent truncation
pd.set_option('display.max_colwidth', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)


# ----------------------------------------------------
# GLOBAL PERSISTENT FLASH & NOTIFICATION SYSTEM
# ----------------------------------------------------
def _clean_notification_msg(msg):
    """Strips leading emojis (ticks, checkmarks, warning, error icons) to ensure clean single-icon display."""
    if not msg:
        return ""
    return re.sub(r'^[\s\u2705\u2714\u2713\u2611\U0001F197\u274C\u274E\u2716\u2715\u26A0\uFE0F?]+', '', str(msg)).strip()

def flash_success(msg):
    """Saves success notification into session state with a single clean green checkmark banner."""
    clean_msg = _clean_notification_msg(msg)
    st.session_state["flash_success_msg"] = clean_msg

def flash_error(msg):
    """Saves error notification into session state with a single clean alert."""
    clean_msg = _clean_notification_msg(msg)
    st.session_state["flash_error_msg"] = clean_msg

def flash_warning(msg):
    """Saves warning notification into session state with a single clean alert."""
    clean_msg = _clean_notification_msg(msg)
    st.session_state["flash_warning_msg"] = clean_msg

def display_flash_messages():
    """Renders prominent top-level alert banners with a single clean checkmark/icon across Streamlit reruns."""
    if "flash_success_msg" in st.session_state and st.session_state["flash_success_msg"]:
        msg = st.session_state.pop("flash_success_msg")
        clean_msg = _clean_notification_msg(msg)
        st.success(clean_msg)
    if "flash_warning_msg" in st.session_state and st.session_state["flash_warning_msg"]:
        msg = st.session_state.pop("flash_warning_msg")
        clean_msg = _clean_notification_msg(msg)
        st.warning(clean_msg)
    if "flash_error_msg" in st.session_state and st.session_state["flash_error_msg"]:
        msg = st.session_state.pop("flash_error_msg")
        clean_msg = _clean_notification_msg(msg)
        st.error(clean_msg)

def format_df_dates(df):
    """Automatically formats date-like columns to DD-MM-YYYY format for display"""
    if df is None or df.empty:
        return df
    df_copy = df.copy()
    
    date_cols = [
        "Date", "Created Date", "Registered Date", "date", "created_date", "registered_date", 
        "Joined", "Registered", "Created", "Voucher Date", "voucher_date", "Payment Date", 
        "Sanction Date", "Maturity Date", "Closed Date", "Opening Date", "FROM DATE", 
        "TO DATE", "DUE DATE", "from_date", "to_date", "due_date", "Opened Date", 
        "DOB", "Date of Birth", "Appraisal Date", "Renewal Date", "Last Renewal Date",
        "Transaction Date", "Tx Date", "Opening Balance Date", "Sanction / Opening Date"
    ]
    for col in df_copy.columns:
        is_date_col = (col in date_cols) or ("date" in str(col).lower() and "update" not in str(col).lower())
        if not is_date_col and df_copy[col].dtype == 'object':
            valid_vals = df_copy[col].dropna()
            if not valid_vals.empty:
                first_val = str(valid_vals.iloc[0]).strip()
                if re.match(r'^\d{4}-\d{2}-\d{2}', first_val):
                    is_date_col = True
                    
        if is_date_col:
            try:
                series_dt = pd.to_datetime(df_copy[col], errors='coerce')
                formatted = series_dt.dt.strftime('%d-%m-%Y')
                df_copy[col] = formatted.fillna(df_copy[col])
            except Exception:
                pass

    return df_copy


def generate_loan_schedule(start_date, principal, total_interest, tenure_months=12, loan_type='PERSONAL', loan_id=None, loan_no=None):
    """
    Generates exact sequential monthly EMI schedule matching VAISAKH.xlsx blueprint:
    - 12 Installment rows with accurate calendar boundaries (from_date, to_date, due_date)
    - Equal principal split (principal / tenure_months)
    - Equal interest split (total_interest / tenure_months)
    - Equal total EMI (total_repayable / tenure_months)
    """
    import calendar
    if isinstance(start_date, str):
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        except Exception:
            start_date = date.today()
    elif isinstance(start_date, datetime):
        start_date = start_date.date()
        
    tenure_months = max(1, int(tenure_months))
    total_repayable = round(float(principal) + float(total_interest), 2)
    p_emi = round(float(principal) / float(tenure_months), 2)
    i_emi = round(float(total_interest) / float(tenure_months), 2)
    t_emi = round(float(total_repayable) / float(tenure_months), 2)
    
    rows = []
    current_from = start_date
    for i in range(1, tenure_months + 1):
        year = start_date.year + (start_date.month - 1 + i) // 12
        month = (start_date.month - 1 + i) % 12 + 1
        day = start_date.day
        max_days = calendar.monthrange(year, month)[1]
        target_day = min(day, max_days)
        next_start = date(year, month, target_day)
        to_date_val = next_start - timedelta(days=1)
        due_date_val = to_date_val
        
        rows.append({
            'emi_number': i,
            'from_date': current_from.strftime('%Y-%m-%d'),
            'to_date': to_date_val.strftime('%Y-%m-%d'),
            'due_date': due_date_val.strftime('%Y-%m-%d'),
            'principal_component': p_emi,
            'interest_component': i_emi,
            'emi_amount': t_emi,
            'paid_amount': 0.0,
            'paid_date': None,
            'status': 'PENDING'
        })
        current_from = next_start
    return rows


def batch_insert_loan_schedules(loan_type, loan_id, loan_no, schedule_list, created_at_str):
    """
    Inserts all EMI schedule rows in a single batch query for maximum speed and sub-second disbursals.
    """
    if not schedule_list:
        return
    placeholders = []
    flat_params = []
    for s in schedule_list:
        placeholders.append("(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'PENDING', ?)")
        flat_params.extend([
            loan_type, loan_id, loan_no, s['emi_number'],
            str(s['from_date']), str(s['to_date']), str(s['due_date']),
            float(s.get('principal_component', 0.0) or 0.0),
            float(s.get('interest_component', 0.0) or 0.0),
            float(s.get('emi_amount', 0.0) or 0.0),
            str(created_at_str)
        ])
    query = f"""
        INSERT INTO loan_emi_schedules (
            loan_type, loan_id, loan_no, emi_number, from_date, to_date, due_date,
            principal_component, interest_component, emi_amount, paid_amount, status, created_at
        ) VALUES {', '.join(placeholders)}
    """
    run_query(query, tuple(flat_params), fetch=False)


# --- CORE VIEWS ---

def render_dashboard():
    st.title("📊 Executive Dashboard & Active Deposits")
    
    # Combined query to fetch all dashboard metrics in a single network roundtrip
    dashboard_metrics = cached_query("""
        SELECT 
            (SELECT COUNT(*) FROM customers) as total_cust,
            (SELECT COUNT(*) FROM sb_accounts) as total_sb,
            (SELECT COUNT(*) FROM fixed_deposits WHERE status='ACTIVE') as total_fds,
            (SELECT COUNT(*) FROM recurring_deposits WHERE status='ACTIVE') as total_rds,
            COALESCE((SELECT balance FROM cash_book ORDER BY id DESC LIMIT 1), (SELECT COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) FROM jv_entries WHERE account_code='AST-101'), 0) as cash_bal,
            COALESCE((SELECT balance FROM bank_book WHERE bank_name = 'Union Bank of India' ORDER BY id DESC LIMIT 1), (SELECT COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) FROM jv_entries WHERE account_code='AST-102'), 0) as union_bal,
            COALESCE((SELECT balance FROM bank_book WHERE bank_name = 'State Bank of India' ORDER BY id DESC LIMIT 1), (SELECT COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) FROM jv_entries WHERE account_code='AST-103'), 0) as sbi_bal,
            (SELECT COALESCE(SUM(credit), 0) - COALESCE(SUM(debit), 0) FROM jv_entries WHERE account_code='LIA-101') as sb_dep_bal,
            (SELECT COALESCE(SUM(credit), 0) - COALESCE(SUM(debit), 0) FROM jv_entries WHERE account_code='LIA-102') as fd_dep_bal,
            (SELECT COALESCE(SUM(credit), 0) - COALESCE(SUM(debit), 0) FROM jv_entries WHERE account_code='LIA-103') as rd_dep_bal
    """)
    
    if dashboard_metrics and len(dashboard_metrics) > 0:
        row = dashboard_metrics[0]
        total_cust = row[0] or 0
        total_sb = row[1] or 0
        total_fds = row[2] or 0
        rd_active = row[3] or 0
        cash_bal = float(row[4] or 0.0)
        union_bal = float(row[5] or 0.0)
        sbi_bal = float(row[6] or 0.0)
        sb_dep_bal = float(row[7] or 0.0)
        fd_dep_bal = float(row[8] or 0.0)
        rd_dep_bal = float(row[9] or 0.0)
    else:
        total_cust, total_sb, total_fds, rd_active = 0, 0, 0, 0
        cash_bal, union_bal, sbi_bal = 0.0, 0.0, 0.0
        sb_dep_bal, fd_dep_bal, rd_dep_bal = 0.0, 0.0, 0.0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 Total Customers", total_cust, delta=None)
    col2.metric("💰 Active SB Accounts", total_sb, delta=None)
    col3.metric("📈 Active FDs", total_fds, delta=None)
    col4.metric("🔄 Active RDs", rd_active, delta=None)
    
    col5, col6, col7 = st.columns(3)
    col5.metric("💵 Cash Balance", f"₹{cash_bal:,.2f}")
    col6.metric("🏦 Union Bank Balance", f"₹{union_bal:,.2f}")
    col7.metric("🏦 SBI Balance", f"₹{sbi_bal:,.2f}")
    
    st.markdown("---")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("📊 Account Distribution")
        account_data = {
            "Account Type": ["SB Accounts", "Fixed Deposits", "Recurring Deposits"],
            "Count": [total_sb, total_fds, rd_active]
        }
        df_chart = pd.DataFrame(account_data)
        fig = px.pie(df_chart, values='Count', names='Account Type', 
                     title="Active Accounts Distribution",
                     color_discrete_sequence=px.colors.sequential.Blues_r,
                     hole=0.4)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, config={'displayModeBar': False, 'responsive': False})
    
    with col_chart2:
        st.subheader("📊 Balance Overview")
        balance_data = {
            "Category": ["Cash", "Union Bank", "SBI", "SB Deposits", "FD Deposits", "RD Deposits"],
            "Amount": [
                cash_bal, union_bal, sbi_bal,
                sb_dep_bal,
                fd_dep_bal,
                rd_dep_bal
            ]
        }
        df_balance = pd.DataFrame(balance_data)
        colors = ['#2ecc71', '#3498db', '#2980b9', '#f39c12', '#e67e22', '#e74c3c']
        fig = px.bar(df_balance, x='Category', y='Amount', 
                     title="Balance Overview",
                     color='Category',
                     color_discrete_sequence=colors)
        fig.update_layout(height=350, xaxis_tickangle=-45, margin=dict(l=20, r=20, t=40, b=20))
        fig.update_traces(texttemplate='₹%{value:,.0f}', textposition='outside')
        st.plotly_chart(fig, config={'displayModeBar': False, 'responsive': False})
    
    st.markdown("---")
    st.subheader("📋 Active Recurring Deposits (RD) Directory")
    rd_query = """
        SELECT r.rd_id, c.name, r.monthly_amount, r.tenure_months, r.interest_rate, r.installments_paid, r.status, r.created_at
        FROM recurring_deposits r
        JOIN customers c ON r.customer_id = c.id
        WHERE r.status = 'ACTIVE'
    """
    rd_data = cached_query(rd_query)
    if rd_data:
        df_rd = pd.DataFrame(rd_data, columns=["RD ID", "Customer Name", "Monthly Amount", "Tenure (Months)", "Interest Rate (%)", "Installments Paid", "Status", "Created Date"])
        st.dataframe(format_df_dates(df_rd), use_container_width=True)
    else:
        st.info("No active Recurring Deposit accounts found.")

def render_customer_management():
    st.title("👥 Customer Management Module")
    tab1, tab2, tab3 = st.tabs(["Register Customer", "View / Manage Customers", "✏️ Edit / Delete Customer"])
    
    with tab1:
        st.subheader("New Customer Registration")
        st.info("ℹ️ All mandatory fields (*), unique Phone and PAN, valid DOB (1900 to present), and mandatory file uploads are required.")
        with st.form("reg_form"):
            col1, col2 = st.columns(2)
            name = col1.text_input("Full Name *")
            acc_no = col2.text_input("Account Number *")
            dob = col1.date_input("Date of Birth", value=date(1995, 1, 1), min_value=date(1900, 1, 1), max_value=date.today(), format="DD-MM-YYYY")
            gender = col2.selectbox("Gender", ["Male", "Female", "Other"])
            email = col1.text_input("Email Address")
            phone = col2.text_input("Phone Number")
            
            col_b1, col_b2 = st.columns(2)
            acc_type = col_b1.selectbox(
                "Primary Account Type *", 
                [
                    "Savings Bank (SB) & Member Account", 
                    "Personal / Micro Loan Account",
                    "Gold Loan Account (Jewel / Pawn Loan)",
                    "Fixed Deposit (FD) Account",
                    "Recurring Deposit (RD) Account"
                ]
            )
            reg_date = col_b2.date_input("Customer Registration / Joining Date *", value=date.today(), format="DD-MM-YYYY", key="cust_reg_date_input")
            
            street = col1.text_input("Street Address")
            city = col2.text_input("City")
            state = col1.text_input("State")
            pincode = col2.text_input("Pincode")
            pan = col1.text_input("PAN Number")
            
            st.markdown("---")
            adhar_upload = st.file_uploader("Upload Aadhaar Document", type=["pdf", "png", "jpg", "jpeg"], key="reg_adhar")
            pan_upload = st.file_uploader("Upload PAN Card Document", type=["pdf", "png", "jpg", "jpeg"], key="reg_pan")
            sig_upload = st.file_uploader("Upload Signature", type=["png", "jpg", "jpeg"], key="reg_sig")
            
            submitted = st.form_submit_button("🚀 Register Customer Profile", use_container_width=True, type="primary")
            if submitted:
                if not name or not name.strip():
                    st.error("❌ Please enter the customer's Full Name.")
                else:
                    final_acc_no = acc_no.strip() if acc_no and acc_no.strip() else f"0128{datetime.now(IST).strftime('%m%d%H%M')}"
                    
                    # Check for duplicate account number in accounts table
                    existing_acc = run_query("SELECT id FROM accounts WHERE account_number = ?", (final_acc_no,))
                    if existing_acc:
                        st.error(f"❌ Account number `{final_acc_no}` is already registered in the system. Please specify a unique Account Number.")
                    else:
                        try:
                            adh_name, adh_bytes = save_uploaded_file(adhar_upload) if adhar_upload else (None, None)
                            pan_name, pan_bytes = save_uploaded_file(pan_upload) if pan_upload else (None, None)
                            sig_name, sig_bytes = save_uploaded_file(sig_upload) if sig_upload else (None, None)
                            
                            import psycopg2
                            adh_param = psycopg2.Binary(adh_bytes) if (USING_SUPABASE and adh_bytes) else adh_bytes
                            pan_param = psycopg2.Binary(pan_bytes) if (USING_SUPABASE and pan_bytes) else pan_bytes
                            sig_param = psycopg2.Binary(sig_bytes) if (USING_SUPABASE and sig_bytes) else sig_bytes
                            
                            today_str = reg_date.strftime("%Y-%m-%d")
                            now_str = f"{today_str} {datetime.now(IST).strftime('%H:%M')}"
                            
                            # 1. Insert into customers
                            run_query("""
                                INSERT INTO customers (name, account_no, dob, gender, email, phone, account_type, street, city, state, pincode, pan, adhar, adhar_file, adhar_data, pan_file, pan_data, signature_file, signature_data, kyc_status, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'VERIFIED', ?)
                            """, (name.strip(), final_acc_no, str(dob), gender, email, phone, acc_type, street, city, state, pincode, pan, "[Redacted]", adh_name, adh_param, pan_name, pan_param, sig_name, sig_param, now_str), fetch=False)
                            
                            # 2. Get new customer ID
                            new_cust_id_row = run_query("SELECT id FROM customers WHERE account_no = ? ORDER BY id DESC LIMIT 1", (final_acc_no,))
                            if not new_cust_id_row:
                                new_cust_id_row = run_query("SELECT id FROM customers WHERE name = ? ORDER BY id DESC LIMIT 1", (name.strip(),))
                                
                            if new_cust_id_row:
                                new_c_id = new_cust_id_row[0][0]
                                
                                # 3. Automatically create Account in accounts table
                                if 'Gold' in acc_type:
                                    db_acc_type = 'Gold Loan'
                                elif 'Personal' in acc_type or 'Loan' in acc_type:
                                    db_acc_type = 'Personal Loan'
                                elif 'Fixed' in acc_type or 'FD' in acc_type:
                                    db_acc_type = 'Fixed Deposit'
                                elif 'Recurring' in acc_type or 'RD' in acc_type:
                                    db_acc_type = 'Recurring Deposit'
                                else:
                                    db_acc_type = 'Savings Account'

                                run_query("""
                                    INSERT INTO accounts (account_number, account_type, customer_id, balance, created_at)
                                    VALUES (?, ?, ?, 0.0, ?)
                                """, (final_acc_no, db_acc_type, new_c_id, today_str), fetch=False)
                                
                                # 4. Insert into sb_accounts ONLY if customer is registering for Savings Bank
                                if 'Savings' in acc_type or 'SB' in acc_type:
                                    run_query("INSERT INTO sb_accounts (account_no, customer_id, balance, interest_rate, created_at) VALUES (?, ?, 0.0, 3.5, ?)", 
                                              (final_acc_no, new_c_id, today_str), fetch=False)
                                
                                clear_db_cache()
                                flash_success(f"🎉 Customer **{name}** (Acc: `{final_acc_no}`, ID: #{new_c_id}) registered successfully for **{acc_type}**! Opening balance and account operations can now be managed directly in the **{acc_type}** module.")
                                st.rerun()
                            else:
                                st.error("❌ Failed to create customer record. Please check inputs or database connectivity.")
                        except Exception as ex:
                            st.error(f"❌ Error during registration: {str(ex)}")

    with tab2:
        st.subheader("Customer Directory & Document Viewer")
        customers = cached_query("SELECT id, COALESCE(account_no, 'N/A') as account_no, name, phone, email, kyc_status, pan, COALESCE(account_type, 'Savings Bank (SB)') as account_type, created_at FROM customers ORDER BY id ASC")
        if customers:
            df_cust = pd.DataFrame(customers, columns=["ID", "Account No", "Name", "Phone", "Email", "KYC Status", "PAN", "Account Type", "Joined"])
            df_cust_formatted = format_df_dates(df_cust)
            st.dataframe(df_cust_formatted, use_container_width=True)
            
            col_csv, col_pdf = st.columns(2)
            col_csv.download_button("📥 Download CSV Report", df_cust_formatted.to_csv(index=False).encode('utf-8'), "customers_report.csv", "text/csv", use_container_width=True)
            col_pdf.download_button("📥 Download PDF Report", pdf_generator.create_pdf_report("Customer Directory Report", df_cust_formatted), "customers_report.pdf", "application/pdf", use_container_width=True)
            
            with st.expander("🛡️ Document Storage Architecture (Admin)"):
                st.write("**Document Engine:** `Direct PostgreSQL BYTEA Binary Storage`")
                st.write("**Storage Region:** `Singapore (ap-southeast-1)` 🇸🇬")
                st.write("**External S3 Dependencies:** `None (100% Contained in Database)`")
                st.write("**Portability:** `1-Click SQL Backup includes all documents`")

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
                    
                    with d_col1:
                        st.markdown("**Aadhaar Document**")
                        if a_file:
                            st.write(f"File: `{os.path.basename(a_file)}`")
                            try:
                                from database import get_document_data
                                file_bytes, filename = get_document_data(a_file, doc_type='adhar', customer_id=selected_cust_id)
                                if file_bytes:
                                    if filename.lower().endswith((".jpg", ".jpeg", ".png")):
                                        st.image(file_bytes, use_container_width=True)
                                    st.download_button("📥 Download Aadhaar", file_bytes, file_name=filename, key=f"dl_adh_{selected_cust_id}", use_container_width=True)
                                else:
                                    st.info("Document not found.")
                            except Exception:
                                st.info("Document not found.")
                        else:
                            st.info("No file uploaded.")
                            
                    with d_col2:
                        st.markdown("**PAN Card Document**")
                        if p_file:
                            st.write(f"File: `{os.path.basename(p_file)}`")
                            try:
                                from database import get_document_data
                                file_bytes, filename = get_document_data(p_file, doc_type='pan', customer_id=selected_cust_id)
                                if file_bytes:
                                    if filename.lower().endswith((".jpg", ".jpeg", ".png")):
                                        st.image(file_bytes, use_container_width=True)
                                    st.download_button("📥 Download PAN", file_bytes, file_name=filename, key=f"dl_pan_{selected_cust_id}", use_container_width=True)
                                else:
                                    st.info("Document not found.")
                            except Exception:
                                st.info("Document not found.")
                        else:
                            st.info("No file uploaded.")
                            
                    with d_col3:
                        st.markdown("**Signature**")
                        if s_file:
                            st.write(f"File: `{os.path.basename(s_file)}`")
                            try:
                                from database import get_document_data
                                file_bytes, filename = get_document_data(s_file, doc_type='signature', customer_id=selected_cust_id)
                                if file_bytes:
                                    if filename.lower().endswith((".jpg", ".jpeg", ".png")):
                                        st.image(file_bytes, use_container_width=True)
                                    st.download_button("📥 Download Signature", file_bytes, file_name=filename, key=f"dl_sig_{selected_cust_id}", use_container_width=True)
                                else:
                                    st.info("Document not found.")
                            except Exception:
                                st.info("Document not found.")
                        else:
                            st.info("No file uploaded.")
        else:
            st.info("No customers found.")

    with tab3:
        st.subheader("✏️ Edit / Delete Customer Information")
        all_cust_list = cached_query("SELECT id, name, COALESCE(account_no, 'N/A'), phone FROM customers ORDER BY id DESC")
        if all_cust_list:
            c_dict = {f"#{r[0]} - {r[1]} (Acc: {r[2]} | Ph: {r[3]})": r[0] for r in all_cust_list}
            sel_c_label = st.selectbox("Select Customer to Edit / Manage / Delete", list(c_dict.keys()), key="edit_cust_sel")
            cust_id_edit = c_dict[sel_c_label]
            
            cust_data = run_query("SELECT name, COALESCE(account_no, ''), email, phone, street, city, state, pincode, adhar_file, pan_file, signature_file, created_at, COALESCE(account_type, 'Savings Bank (SB) & Member Account') FROM customers WHERE id=?", (cust_id_edit,))
            if cust_data:
                c = cust_data[0]
                # SECTION 1: Personal Profile
                with st.expander("👤 1. Edit Customer Profile & Contact Details", expanded=True):
                    with st.form(f"edit_profile_form_{cust_id_edit}"):
                        col_prof_1, col_prof_2 = st.columns(2)
                        with col_prof_1:
                            new_name = st.text_input("Name", value=c[0])
                            new_acc_no = st.text_input("Account Number", value=c[1])
                            new_email = st.text_input("Email", value=c[2])
                            new_phone = st.text_input("Phone", value=c[3])
                            
                            acc_types_list = [
                                "Savings Bank (SB) & Member Account", 
                                "Personal / Micro Loan Account",
                                "Gold Loan Account (Jewel / Pawn Loan)",
                                "Fixed Deposit (FD) Account",
                                "Recurring Deposit (RD) Account"
                            ]
                            curr_type = c[12]
                            type_idx = acc_types_list.index(curr_type) if curr_type in acc_types_list else 0
                            new_acc_type = st.selectbox("Primary Account Type", acc_types_list, index=type_idx)
                        with col_prof_2:
                            try:
                                cust_reg_dt = datetime.strptime(str(c[11])[:10], "%Y-%m-%d").date() if c[11] else date.today()
                            except Exception:
                                cust_reg_dt = date.today()
                            new_reg_date = st.date_input("Customer Registration / Joining Date", value=cust_reg_dt, format="DD-MM-YYYY")
                            new_street = st.text_input("Street", value=c[4])
                            new_city = st.text_input("City", value=c[5])
                            col_st_pin1, col_st_pin2 = st.columns(2)
                            new_state = col_st_pin1.text_input("State", value=c[6])
                            new_pincode = col_st_pin2.text_input("Pincode", value=c[7])
                        
                        if st.form_submit_button("💾 Save Profile Details", use_container_width=True):
                            new_reg_date_str = f"{new_reg_date.strftime('%Y-%m-%d')} 00:00"
                            run_query("""
                                UPDATE customers 
                                SET name=?, account_no=?, email=?, phone=?, account_type=?, street=?, city=?, state=?, pincode=?, created_at=? 
                                WHERE id=?
                            """, (new_name, new_acc_no, new_email, new_phone, new_acc_type, new_street, new_city, new_state, new_pincode, new_reg_date_str, cust_id_edit), fetch=False)
                            
                            # Sync accounts table account_number & account_type
                            if 'Gold' in new_acc_type:
                                db_acc_type = 'Gold Loan'
                            elif 'Personal' in new_acc_type or 'Loan' in new_acc_type:
                                db_acc_type = 'Personal Loan'
                            elif 'Fixed' in new_acc_type or 'FD' in new_acc_type:
                                db_acc_type = 'Fixed Deposit'
                            elif 'Recurring' in new_acc_type or 'RD' in new_acc_type:
                                db_acc_type = 'Recurring Deposit'
                            else:
                                db_acc_type = 'Savings Account'
                                
                            run_query("UPDATE accounts SET account_number=?, account_type=? WHERE customer_id=?", (new_acc_no, db_acc_type, cust_id_edit), fetch=False)
                            clear_db_cache()
                            flash_success("Profile details updated successfully!")
                            st.rerun()

                st.info("💡 **Product Account & Opening Balance Management:** To view, sanction, or edit opening balances, deposit amounts, sanction dates, and opening balance dates for Savings Bank, Fixed Deposits, Recurring Deposits, Personal Loans, or Gold Loans, please use the **✏️ Edit / Update** tab inside their respective product modules in the sidebar navigation.")

                st.markdown("---")
                st.markdown("### 📄 Manage Customer Documents (Aadhaar, PAN & Signature)")
                
                from database import save_uploaded_file, delete_document, get_document_data
                import psycopg2
                
                # --- 1. AADHAAR CARD ---
                st.write("---")
                st.markdown("**1. Aadhaar Card Document**")
                if c[8]:
                    st.info(f"Existing Aadhaar: `{os.path.basename(c[8])}`")
                    col1, col2 = st.columns(2)
                    try:
                        file_bytes, filename = get_document_data(c[8], doc_type='adhar', customer_id=cust_id_edit)
                        if file_bytes:
                            col1.download_button("📥 Download Aadhaar", file_bytes, file_name=filename, key=f"dl_edit_adh_{cust_id_edit}", use_container_width=True)
                    except Exception:
                        pass
                    if col2.button("🗑️ Delete & Clear Aadhaar", key=f"del_edit_adh_btn_{cust_id_edit}", type="secondary", use_container_width=True):
                        delete_document(c[8], doc_type='adhar', customer_id=cust_id_edit)
                        run_query("UPDATE customers SET adhar_file = NULL, adhar_data = NULL WHERE id = ?", (cust_id_edit,), fetch=False)
                        clear_db_cache()
                        flash_success("Aadhaar document deleted successfully!")
                        st.rerun()
                else:
                    st.warning("No Aadhaar document uploaded.")
                    new_adh = st.file_uploader("Upload Aadhaar Document (PDF or Image)", type=["pdf", "jpg", "jpeg", "png"], key=f"edit_upload_adh_{cust_id_edit}")
                    if new_adh:
                        if st.button("📤 Upload Aadhaar", key=f"up_edit_adh_btn_{cust_id_edit}", type="primary", use_container_width=True):
                            saved_name, saved_bytes = save_uploaded_file(new_adh)
                            param = psycopg2.Binary(saved_bytes) if (USING_SUPABASE and saved_bytes) else saved_bytes
                            run_query("UPDATE customers SET adhar_file = ?, adhar_data = ? WHERE id = ?", (saved_name, param, cust_id_edit), fetch=False)
                            clear_db_cache()
                            flash_success("Aadhaar document saved directly into database!")
                            st.rerun()

                # --- 2. PAN CARD ---
                st.write("---")
                st.markdown("**2. PAN Card Document**")
                if c[9]:
                    st.info(f"Existing PAN Card: `{os.path.basename(c[9])}`")
                    col1, col2 = st.columns(2)
                    try:
                        file_bytes, filename = get_document_data(c[9], doc_type='pan', customer_id=cust_id_edit)
                        if file_bytes:
                            col1.download_button("📥 Download PAN", file_bytes, file_name=filename, key=f"dl_edit_pan_{cust_id_edit}", use_container_width=True)
                    except Exception:
                        pass
                    if col2.button("🗑️ Delete & Clear PAN", key=f"del_edit_pan_btn_{cust_id_edit}", type="secondary", use_container_width=True):
                        delete_document(c[9], doc_type='pan', customer_id=cust_id_edit)
                        run_query("UPDATE customers SET pan_file = NULL, pan_data = NULL WHERE id = ?", (cust_id_edit,), fetch=False)
                        clear_db_cache()
                        flash_success("PAN document deleted successfully!")
                        st.rerun()
                else:
                    st.warning("No PAN document uploaded.")
                    new_pan = st.file_uploader("Upload PAN Card Document (PDF or Image)", type=["pdf", "jpg", "jpeg", "png"], key=f"edit_upload_pan_{cust_id_edit}")
                    if new_pan:
                        if st.button("📤 Upload PAN", key=f"up_edit_pan_btn_{cust_id_edit}", type="primary", use_container_width=True):
                            saved_name, saved_bytes = save_uploaded_file(new_pan)
                            param = psycopg2.Binary(saved_bytes) if (USING_SUPABASE and saved_bytes) else saved_bytes
                            run_query("UPDATE customers SET pan_file = ?, pan_data = ? WHERE id = ?", (saved_name, param, cust_id_edit), fetch=False)
                            clear_db_cache()
                            flash_success("PAN document saved directly into database!")
                            st.rerun()

                # --- 3. SIGNATURE ---
                st.write("---")
                st.markdown("**3. Signature Document**")
                if c[10]:
                    st.info(f"Existing Signature: `{os.path.basename(c[10])}`")
                    col1, col2 = st.columns(2)
                    try:
                        file_bytes, filename = get_document_data(c[10], doc_type='signature', customer_id=cust_id_edit)
                        if file_bytes:
                            col1.download_button("📥 Download Signature", file_bytes, file_name=filename, key=f"dl_edit_sig_{cust_id_edit}", use_container_width=True)
                    except Exception:
                        pass
                    if col2.button("🗑️ Delete & Clear Signature", key=f"del_edit_sig_btn_{cust_id_edit}", type="secondary", use_container_width=True):
                        delete_document(c[10], doc_type='signature', customer_id=cust_id_edit)
                        run_query("UPDATE customers SET signature_file = NULL, signature_data = NULL WHERE id = ?", (cust_id_edit,), fetch=False)
                        clear_db_cache()
                        flash_success("Signature document deleted successfully!")
                        st.rerun()
                else:
                    st.warning("No Signature document uploaded.")
                    new_sig = st.file_uploader("Upload Signature Document (PDF or Image)", type=["pdf", "jpg", "jpeg", "png"], key=f"edit_upload_sig_{cust_id_edit}")
                    if new_sig:
                        if st.button("📤 Upload Signature", key=f"up_edit_sig_btn_{cust_id_edit}", type="primary", use_container_width=True):
                            saved_name, saved_bytes = save_uploaded_file(new_sig)
                            param = psycopg2.Binary(saved_bytes) if (USING_SUPABASE and saved_bytes) else saved_bytes
                            run_query("UPDATE customers SET signature_file = ?, signature_data = ? WHERE id = ?", (saved_name, param, cust_id_edit), fetch=False)
                            clear_db_cache()
                            flash_success("Signature document saved directly into database!")
                            st.rerun()

                # --- 4. DANGER ZONE: DELETE CUSTOMER ---
                st.write("---")
                with st.expander("🚨 Danger Zone: Delete Customer Record", expanded=False):
                    st.error(f"⚠️ **Warning**: Permanently delete customer **{c[0]}** (Customer ID: `#{cust_id_edit}`). This will permanently delete this customer profile along with their linked accounts, savings balances, loans, deposits, and documents.")
                    confirm_del = st.checkbox(f"Yes, I confirm I want to permanently delete customer #{cust_id_edit} - {c[0]}", key=f"confirm_del_cust_{cust_id_edit}")
                    if confirm_del:
                        if st.button(f"🗑️ Permanently Delete Customer #{cust_id_edit}", type="primary", use_container_width=True, key=f"btn_delete_cust_{cust_id_edit}"):
                            from database import delete_customer_cascade
                            success, msg = delete_customer_cascade(cust_id_edit)
                            if success:
                                clear_db_cache()
                                flash_success(f"✅ {msg}")
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to delete customer: {msg}")
        else:
            st.info("No customers found.")


def render_kyc():
    st.title("✅ KYC Verification Panel")
    pending = run_query("SELECT id, name, phone, pan, adhar_file, pan_file, signature_file, created_at FROM customers WHERE kyc_status='PENDING'")
    if pending:
        for p in pending:
            with st.expander(f"Customer: {p[1]} (ID: {p[0]}) - Phone: {p[2]}"):
                col1, col2 = st.columns(2)
                if col1.button(f"✅ Approve KYC #{p[0]}", key=f"app_{p[0]}", use_container_width=True):
                    run_query("UPDATE customers SET kyc_status='APPROVED' WHERE id=?", (p[0],), fetch=False)
                    clear_db_cache()
                    flash_success(f"KYC Approved for ID {p[0]}")
                    st.rerun()
                if col2.button(f"❌ Reject KYC #{p[0]}", key=f"rej_{p[0]}", use_container_width=True):
                    run_query("UPDATE customers SET kyc_status='REJECTED' WHERE id=?", (p[0],), fetch=False)
                    clear_db_cache()
                    flash_error(f"KYC Rejected for ID {p[0]}")
                    st.rerun()
    else:
        st.info("No pending KYC verification requests.")

def render_daily_collection_sheet():
    st.title("📅 Daily Report & Collection Sheet")
    col_d1, col_d2 = st.columns([2, 1])
    report_date = col_d1.date_input("Daily Report Date", value=date.today(), format="DD-MM-YYYY", key="daily_rep_date")
    
    cur_cash = get_cash_balance()
    cur_bank = get_account_balance_from_jv("AST-102")
    tot_due_res = cached_query("SELECT SUM(outstanding_due) FROM personal_loans WHERE status != 'CLOSED'")
    tot_due_val = float(tot_due_res[0][0]) if (tot_due_res and tot_due_res[0][0]) else 1458104.00
    
    m1, m2, m3 = st.columns(3)
    m1.metric("💵 Cash in Office", f"₹{cur_cash:,.2f}")
    m2.metric("🏦 Union Bank Balance", f"₹{cur_bank:,.2f}")
    m3.metric("📈 Total Outstanding Due Portfolio", f"₹{tot_due_val:,.2f}")
    
    tab1, tab2 = st.tabs(["📝 Quick Collection Entry", "📊 Full Daily Member Register & Export"])
    
    with tab1:
        st.subheader("⚡ Record Member Daily Collection")
        pl_active = cached_query("""
            SELECT pl.id, pl.loan_no, c.name, COALESCE(c.account_no, 'N/A'), pl.outstanding_due, pl.installment_amount, pl.customer_id
            FROM personal_loans pl
            JOIN customers c ON pl.customer_id = c.id
            WHERE pl.outstanding_due > 0
            ORDER BY pl.id ASC
        """)
        if pl_active:
            pl_dict = {f"{r[0]}. {r[2]} (Acc: {r[3]} | Due: ₹{float(r[4]):,.2f})": r for r in pl_active}
            sel_key = st.selectbox("Select Customer / Loan Account", list(pl_dict.keys()), key="dc_sel_loan")
            selected_row = pl_dict[sel_key]
            l_id, l_no, l_name, l_acc, l_due, l_inst, l_cid = selected_row
            
            with st.form("quick_daily_collection_form"):
                c_amt, c_mode = st.columns(2)
                coll_amt = c_amt.number_input("Collection Amount (₹)", min_value=1.0, value=float(l_inst) if l_inst > 0 else 500.0, step=100.0)
                coll_mode = c_mode.selectbox("Collection Payment Mode", ["Union Bank of India (UPI / Bank)", "Cash in Hand (Office Drawer)"])
                
                c_notes = st.text_input("Narration / Reference", value=f"Daily Collection {l_name} ({l_no})")
                
                if st.form_submit_button("💾 Save & Post Collection to Ledger", use_container_width=True):
                    rep_voucher = f"DC{report_date.strftime('%Y%m%d')}{l_id:03d}"
                    new_due = max(0.0, float(l_due) - float(coll_amt))
                    new_status = 'CLOSED' if new_due <= 0 else 'ACTIVE'
                    
                    # Compute proportional interest and principal split for active term
                    p_info = run_query("SELECT principal_amount, total_repayable FROM personal_loans WHERE id = ?", (l_id,))
                    l_princ = float(p_info[0][0]) if p_info else float(coll_amt)
                    l_tot_rep = float(p_info[0][1]) if p_info else float(coll_amt)
                    tot_loan_int = max(0.0, round(l_tot_rep - l_princ, 2))
                    
                    cycle_paid_so_far = max(0.0, round(l_tot_rep - float(l_due), 2))
                    if l_tot_rep > 0 and tot_loan_int > 0:
                        cycle_int_rec = round(cycle_paid_so_far * (tot_loan_int / l_tot_rep), 2)
                    else:
                        cycle_int_rec = 0.0
                    rem_int_to_rec = max(0.0, round(tot_loan_int - cycle_int_rec, 2))
                    
                    if l_tot_rep > 0 and tot_loan_int > 0:
                        prop_int = round(float(coll_amt) * (tot_loan_int / l_tot_rep), 2)
                        if new_due <= 0:
                            int_portion = rem_int_to_rec
                        else:
                            int_portion = min(prop_int, rem_int_to_rec)
                        princ_portion = round(float(coll_amt) - int_portion, 2)
                    else:
                        int_portion = 0.0
                        princ_portion = float(coll_amt)
                    
                    # 1. Update personal_loans
                    run_query("UPDATE personal_loans SET outstanding_due = ?, status = ? WHERE id = ?", (new_due, new_status, l_id), fetch=False)
                    
                    # 2. Record in loan_repayments
                    run_query("""
                        INSERT INTO loan_repayments (loan_type, loan_id, customer_id, payment_date, amount_paid, principal_component, interest_component, payment_mode, voucher_no, narration)
                        VALUES ('PERSONAL', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (l_id, l_cid, str(report_date), coll_amt, princ_portion, int_portion, coll_mode, rep_voucher, c_notes), fetch=False)
                    
                    # 3. Post to Bank Book or Cash Book & Double-Entry JVs
                    part_text = f"Daily Collection: {l_name} (Acc: {l_acc}) [{l_no}]"
                    bank_or_cash_code = 'AST-102' if "Union Bank" in coll_mode else 'AST-101'
                    
                    if "Union Bank" in coll_mode:
                        last_bb = run_query("SELECT balance FROM bank_book WHERE bank_name = 'Union Bank of India' ORDER BY id DESC LIMIT 1")
                        prev_b = float(last_bb[0][0]) if (last_bb and last_bb[0][0] is not None) else 0.0
                        new_b = prev_b + coll_amt
                        run_query("""
                            INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, narration, account_code)
                            VALUES (?, ?, ?, ?, 0, ?, 'Union Bank of India', ?, 'AST-108')
                        """, (str(report_date), rep_voucher, part_text, coll_amt, new_b, c_notes), fetch=False)
                    else:
                        last_cb = run_query("SELECT balance FROM cash_book ORDER BY id DESC LIMIT 1")
                        prev_c = float(last_cb[0][0]) if (last_cb and last_cb[0][0] is not None) else 0.0
                        new_c = prev_c + coll_amt
                        run_query("""
                            INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, narration, account_code)
                            VALUES (?, ?, ?, ?, 0, ?, ?, 'AST-108')
                        """, (str(report_date), rep_voucher, part_text, coll_amt, new_c, c_notes), fetch=False)
                        
                    # Voucher 1: Receipt JV (Bank/Cash Dr, AST-108 Cr)
                    post_automated_jv(
                        f"Daily Collection [{rep_voucher}]: {part_text}",
                        bank_or_cash_code,
                        'AST-108',
                        coll_amt,
                        voucher_date=report_date
                    )
                    
                    # Voucher 2: Interest Realization JV (LIA-104 Dr, INC-101 Cr)
                    if int_portion > 0:
                        post_automated_jv(
                            f"Interest Realization [{l_no}]: {l_name} - ₹{int_portion:,.2f} earned interest recognized",
                            'LIA-104',
                            'INC-101',
                            int_portion,
                            voucher_date=report_date
                        )
                        
                    # 4. Update Customer Passbook
                    acc_r = run_query("SELECT id, balance FROM accounts WHERE customer_id = ?", (l_cid,))
                    if acc_r:
                        a_id, a_bal = acc_r[0]
                        pass_bal = max(0.0, float(a_bal) - float(coll_amt))
                        run_query("UPDATE accounts SET balance = ? WHERE id = ?", (pass_bal, a_id), fetch=False)
                        run_query("INSERT INTO transactions (account_id, type, amount, balance_after, date) VALUES (?, ?, ?, ?, ?)", (a_id, f"DAILY COLLECTION [{l_no}] (CREDIT)", coll_amt, pass_bal, str(report_date)), fetch=False)
                        
                    clear_db_cache()
                    flash_success(f"🎉 Received ₹{coll_amt:,.2f} from {l_name}! Posted to Bank Book ({rep_voucher}) and Customer Passbook.")
                    st.rerun()
        else:
            st.info("No active loans found.")

    with tab2:
        st.subheader("📊 Master Daily Report Register (All 39 Members)")
        daily_query = """
            SELECT 
                c.id as sl_no,
                c.name as customer_name,
                COALESCE(c.account_no, 'N/A') as account_no,
                COALESCE(c.phone, 'N/A') as contact_no,
                COALESCE(pl.principal_amount, 0.0) as loan_amount,
                COALESCE(pl.outstanding_due, 0.0) as due_amount,
                COALESCE(pl.status, 'ACTIVE') as status,
                COALESCE(pl.remarks, '') as remarks
            FROM customers c
            LEFT JOIN personal_loans pl ON c.id = pl.customer_id
            ORDER BY c.id ASC
        """
        d_rows = cached_query(daily_query)
        if d_rows:
            df_daily = pd.DataFrame(d_rows, columns=["Sl", "Customer Name", "Account No", "Contact No", "Loan Amount (₹)", "Due Amount (₹)", "Status", "Remarks / Legal Status"])
            st.dataframe(format_df_dates(df_daily), use_container_width=True)
            
            c_x, c_c, c_p = st.columns(3)
            with c_x:
                st.download_button("📊 Download Daily Report (.xlsx)", pdf_generator.create_excel_report(f"Daily Report - {report_date}", df_daily), f"daily_report_{report_date}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            with c_c:
                st.download_button("📥 Download Daily Report (.csv)", pdf_generator.create_csv_report(f"Daily Report - {report_date}", df_daily), f"daily_report_{report_date}.csv", "text/csv", use_container_width=True)
            with c_p:
                    st.download_button("📄 Download Daily Report PDF", pdf_generator.create_pdf_report(f"Daily Report - {report_date}", df_daily), f"daily_report_{report_date}.pdf", "application/pdf", use_container_width=True)


def render_personal_loans():
    st.title("💼 Personal & Micro Loan Management")
    
    # ⚡ FAST SINGLE UNIFIED QUERY: Fetches all personal loans, schedules, and repayments in 1 instant bundle
    all_pl_data, pl_sched_map, pl_rep_map = get_all_personal_loans_bundle()
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📝 Sanction & Opening Balance Loan", 
        "💳 Collect Repayment / Installment", 
        "🔄 Loan Renewal & Interest Rollover",
        "✏️ Edit / Delete Personal Loan & Opening Balance",
        "📋 Active Loan Register & Legal Tracker", 
        "🖨️ Loan Statement & Passbook"
    ])
    
    with tab1:
        st.subheader("📝 Sanction New Personal Loan / Add Opening Balance Loan")
        cust_raw = cached_query("""
            SELECT c.id, c.name, COALESCE(c.account_no, 'N/A'), c.phone, c.street, c.city, c.state, c.pincode 
            FROM customers c 
            ORDER BY c.name ASC, c.id ASC
        """) or []
        if not cust_raw:
            st.warning("Please register a customer first.")
            return
            
        cust_list = []
        for c in cust_raw:
            c_id, c_name, c_acc, c_phone, c_str, c_city, c_state, c_pin = c
            addr_parts = [p for p in [c_str, c_city, c_state, c_pin] if p and str(p).strip()]
            c_addr = ", ".join(addr_parts) if addr_parts else "Balaramapuram, Trivandrum"
            cust_list.append((c_id, c_name, c_acc, c_phone, c_addr))
            
        cust_dict = {f"#{c[0]} - {c[1]} (Acc: {c[2]} | Ph: {c[3]})": c for c in cust_list}
        
        selected_cust_label = st.selectbox("1️⃣ Select Member / Borrower", list(cust_dict.keys()), key="pl_cust_sel")
        
        st.markdown("### 2️⃣ Loan Financial Terms & Amortization")
        col1, col2, col3, col4, col5 = st.columns(5)
        sanction_date = col1.date_input("Sanction Date", value=date.today(), format="DD-MM-YYYY", key="pl_sanc_date")
        op_bal_date = col2.date_input("Opening / Disbursal Date", value=sanction_date, format="DD-MM-YYYY", key="pl_op_bal_date")
        principal = col3.number_input("Sanctioned Principal Amount (₹)", min_value=1000.0, value=50000.0, step=1000.0, help="The original principal amount sanctioned to the borrower", key="pl_princ_inp")
        int_rate = col4.number_input("Interest Rate (% p.a.)", min_value=0.0, value=12.0, step=0.5, help="Annual flat interest rate percentage (default 12%)", key="pl_rate_inp")
        tenure_days = col5.number_input("Tenure (Days)", min_value=1, value=100, step=5, help="Total loan tenure in days (e.g., 100 days micro loan, 180 days, 365 days)", key="pl_ten_days")
        
        tenure_months = max(1, int(round(tenure_days / 30.0)))
        loan_scheme_name = f"{tenure_days}-Day Loan ({tenure_months}M EMI)" if tenure_days != 100 else "Daily 100-Day Micro Loan"
        tot_interest = round(principal * (int_rate / 100.0) * (tenure_days / 365.0), 2)
        tot_repayable = round(principal + tot_interest, 2)
        p_emi = round(principal / float(tenure_months), 2)
        i_emi = round(tot_interest / float(tenure_months), 2)
        installment = round(tot_repayable / float(tenure_months), 2)
        
        with st.container(border=True):
            st.markdown("#### 📊 Live Personal Loan Breakdown & EMI Structure")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💵 Principal", f"₹{principal:,.2f}")
            m2.metric(f"📈 Interest ({int_rate}%)", f"₹{tot_interest:,.2f}")
            m3.metric("💳 Total Due (Repayable)", f"₹{tot_repayable:,.2f}")
            m4.metric("📅 Monthly EMI", f"₹{installment:,.2f}")
            st.caption(f"📌 **Monthly Breakdown:** Principal EMI: **₹{p_emi:,.2f}** + Interest EMI: **₹{i_emi:,.2f}** = Total EMI: **₹{installment:,.2f}** per month for {tenure_days} days ({tenure_months} months).")

        preview_schedule = generate_loan_schedule(sanction_date, principal, tot_interest, tenure_months=tenure_months)
        with st.expander(f"📅 Preview {len(preview_schedule)}-Month EMI Amortization Schedule Table", expanded=False):
            df_prev = pd.DataFrame(preview_schedule)
            df_prev_display = df_prev.rename(columns={
                "emi_number": "EMI NOS", "from_date": "FROM DATE", "to_date": "TO DATE",
                "due_date": "DUE DATE", "principal_component": "PRINCIPAL (₹)",
                "interest_component": "INTEREST (₹)", "emi_amount": "EMI AMOUNT (₹)"
            })[["EMI NOS", "FROM DATE", "TO DATE", "DUE DATE", "PRINCIPAL (₹)", "INTEREST (₹)", "EMI AMOUNT (₹)"]]
            st.dataframe(format_df_dates(df_prev_display), use_container_width=True)

        st.markdown("### 3️⃣ Disbursal Account, Opening Balance & Guarantor Details")
        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
        disb_mode = col_d1.selectbox("Disburse Funds From:", ["Union Bank of India (NEFT / UPI)", "Cash in Hand (Office Drawer)"], key="pl_disb_mode")
        opening_balance = col_d2.number_input("Opening Balance (₹)", min_value=0.0, value=float(principal), step=500.0, key="pl_op_bal_amt", help="Starting opening ledger balance at account creation (defaults to Principal Amount).")
        outstanding_due = col_d3.number_input("Initial Outstanding Due (₹)", min_value=0.0, value=float(tot_repayable), step=500.0, key="pl_init_due_amt", help="Initial unpaid amount due to be repaid by borrower (defaults to Total Repayable).")
        custom_loan_no = col_d4.text_input("Custom Loan Number (Optional)", key="pl_cust_lno")
        
        g_col1, g_col2 = st.columns(2)
        guarantor_name = g_col1.text_input("Guarantor / Surety Member Name", value="SARITHA", key="pl_g_name")
        guarantor_relation = g_col2.text_input("Guarantor Relationship with Borrower", value="Wife", key="pl_g_rel")
        
        g_col3, g_col4 = st.columns(2)
        guarantor_phone = g_col3.text_input("Guarantor Mobile Number", value="999888444", key="pl_g_ph")
        guarantor_address = g_col4.text_input("Guarantor Residential Address", value="Balaramapuram, Trivandrum", key="pl_g_addr")
        
        col_p1, col_p2 = st.columns(2)
        purpose = col_p1.text_input("Loan Purpose", value="Business Working Capital / Personal", key="pl_purp")
        remarks = col_p2.text_input("Remarks / Notes", value="New Personal Loan Disbursed", key="pl_rem")
        
        if st.button("🚀 Confirm & 1-Click Disburse Loan", use_container_width=True, type="primary", key="btn_confirm_pl_disb"):
            selected_cust = cust_dict[selected_cust_label]
            selected_cust_id, selected_cust_name, selected_cust_acc, selected_cust_phone, selected_cust_addr = selected_cust
            
            cur_count = len(all_pl_data) + 1
            loan_no = custom_loan_no.strip() if custom_loan_no and custom_loan_no.strip() else f"PL-2026-{cur_count:04d}"
            voucher_no = f"PLV{sanction_date.strftime('%Y%m%d')}{cur_count:03d}"
            
            final_initial_due = float(outstanding_due) if float(outstanding_due or 0) > 0 else float(tot_repayable)
            
            if "Cash" in disb_mode:
                cur_cash = get_cash_balance()
                if cur_cash < principal:
                    st.warning(f"⚠️ Cash balance alert: Available ₹{cur_cash:,.2f}. Disbursing ₹{principal:,.2f}.")
            
            preview_schedule = generate_loan_schedule(sanction_date, principal, tot_interest, tenure_months=tenure_months)
            loan_from_date = preview_schedule[0]["from_date"] if preview_schedule else str(sanction_date)
            loan_to_date = preview_schedule[-1]["to_date"] if preview_schedule else str(sanction_date)
            first_emi_due = preview_schedule[0]["due_date"] if preview_schedule else str(sanction_date)
            last_emi_due = preview_schedule[-1]["due_date"] if preview_schedule else str(sanction_date)
            
            new_pl_row = run_query("""
                INSERT INTO personal_loans (
                    loan_no, customer_id, sanction_date, principal_amount, opening_balance, interest_rate,
                    interest_type, tenure_days, tenure_months, total_interest, total_repayable,
                    installment_amount, outstanding_due, disbursal_mode, voucher_no,
                    guarantor_name, guarantor_relation, guarantor_phone, guarantor_address,
                    loan_from_date, loan_to_date, first_emi_due, last_emi_due,
                    monthly_principal_emi, monthly_interest_emi,
                    purpose, status, remarks, renewal_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, 0)
                RETURNING id
            """, (
                loan_no, selected_cust_id, str(sanction_date), principal, float(opening_balance), int_rate,
                loan_scheme_name, tenure_days, tenure_months, tot_interest, tot_repayable,
                installment, final_initial_due, disb_mode, voucher_no,
                guarantor_name, guarantor_relation, guarantor_phone, guarantor_address,
                loan_from_date, loan_to_date, first_emi_due, last_emi_due,
                p_emi, i_emi,
                purpose, remarks
            ))
            
            if new_pl_row and new_pl_row[0]:
                new_pl_id = new_pl_row[0][0]
            else:
                pl_lookup = run_query("SELECT id FROM personal_loans WHERE loan_no = ?", (loan_no,))
                if pl_lookup and pl_lookup[0]:
                    new_pl_id = pl_lookup[0][0]
                else:
                    st.error(f"❌ Failed to disburse Personal Loan **{loan_no}**.")
                    st.stop()
            
            batch_insert_loan_schedules('PERSONAL', new_pl_id, loan_no, preview_schedule, sanction_date)
                
            part_text = f"Personal Loan Disbursal: {selected_cust_name} (Acc: {selected_cust_acc}) [{loan_no}]"
        
            bank_or_cash_code = 'AST-102' if "Union Bank" in disb_mode else 'AST-101'
            if "Union Bank" in disb_mode:
                last_bb = run_query("SELECT balance FROM bank_book WHERE bank_name = 'Union Bank of India' ORDER BY id DESC LIMIT 1")
                prev_b = float(last_bb[0][0]) if (last_bb and last_bb[0][0] is not None) else 0.0
                new_b = prev_b - principal
                run_query("""
                    INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, narration, account_code)
                    VALUES (?, ?, ?, 0, ?, ?, 'Union Bank of India', ?, 'AST-108')
                """, (str(op_bal_date), voucher_no, part_text, principal, new_b, remarks), fetch=False)
            else:
                last_cb = run_query("SELECT balance FROM cash_book ORDER BY id DESC LIMIT 1")
                prev_c = float(last_cb[0][0]) if (last_cb and last_cb[0][0] is not None) else 0.0
                new_c = prev_c - principal
                run_query("""
                    INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, narration, account_code)
                    VALUES (?, ?, ?, 0, ?, ?, ?, 'AST-108')
                """, (str(op_bal_date), voucher_no, part_text, principal, new_c, remarks), fetch=False)
            
            cr_entries = [(bank_or_cash_code, principal)]
            if tot_interest > 0:
                cr_entries.append(('LIA-104', tot_interest))
            post_compound_jv(
                f"Loan Disbursal [{voucher_no}]: {part_text} (Principal: ₹{principal:,.2f} + Planned Interest: ₹{tot_interest:,.2f} = Total Due: ₹{tot_repayable:,.2f})",
                [('AST-108', tot_repayable)],
                cr_entries,
                voucher_date=str(op_bal_date)
            )
                
            acc_row = run_query("SELECT id, balance FROM accounts WHERE customer_id = ?", (selected_cust_id,))
            if acc_row:
                acc_id, old_bal = acc_row[0]
                new_bal = float(old_bal) + float(final_initial_due)
                run_query("UPDATE accounts SET balance = ? WHERE id = ?", (new_bal, acc_id), fetch=False)
                run_query("INSERT INTO transactions (account_id, type, amount, balance_after, date) VALUES (?, ?, ?, ?, ?)", (acc_id, f"LOAN DISBURSAL [{loan_no}] (DEBIT)", final_initial_due, new_bal, str(sanction_date)), fetch=False)
            else:
                run_query("INSERT INTO accounts (account_number, account_type, customer_id, balance, created_at) VALUES (?, 'Loan Account', ?, ?, ?)", (selected_cust_acc, selected_cust_id, final_initial_due, str(sanction_date)), fetch=False)
                acc_lookup = run_query("SELECT id FROM accounts WHERE customer_id = ?", (selected_cust_id,))
                acc_id = acc_lookup[0][0] if acc_lookup and acc_lookup[0] else None
                if acc_id:
                    run_query("INSERT INTO transactions (account_id, type, amount, balance_after, date) VALUES (?, ?, ?, ?, ?)", (acc_id, f"LOAN DISBURSAL [{loan_no}] (DEBIT)", final_initial_due, final_initial_due, str(sanction_date)), fetch=False)
                
            clear_db_cache()
            flash_success(f"🎉 Loan **{loan_no}** Disbursed Successfully! Total Repayable Due: **₹{tot_repayable:,.2f}** | Outstanding Opening Balance: **₹{final_initial_due:,.2f}**.")
            st.rerun()

    with tab2:
        st.subheader("💳 Record Loan Repayment / Collect Installment")
        active_loans = [
            r for r in all_pl_data 
            if r[29] not in ('CLOSED', 'SETTLED') and (float(r[21] or 0) > 0 or float(r[13] or r[7] or 0) > 0)
        ]
        if active_loans:
            loan_dict = {}
            for r in active_loans:
                inst_str = f"₹{float(r[14]):,.2f}/inst" if float(r[14] or 0) > 0 else "Flexible"
                eff_due = float(r[21]) if float(r[21] or 0) > 0 else float(r[13] or r[7] or 0.0)
                label = f"#{r[1]} - {r[3]} (Acc: {r[4]} | Due: ₹{eff_due:,.2f} | Plan: {inst_str})"
                loan_dict[label] = r
                
            sel_l_key = st.selectbox("1️⃣ Select Active Loan to Record Payment", list(loan_dict.keys()), key="rep_loan_sel")
            sel_loan = loan_dict[sel_l_key]
            (l_id, l_no, l_cid, l_cname, l_cacc, l_cphone, l_sdate, l_princ, l_rate, l_scheme,
             l_tdays, l_tmonths, l_tot_int, l_tot_rep, l_inst, l_p_emi, l_i_emi, l_from, l_to,
             l_fdue, l_ldue, l_due, l_dmode, l_vno, l_gname, l_gphone, l_grel, l_gaddr,
             l_purp, l_stat, l_rem, l_ren_cnt, l_last_ren, l_str, l_city, l_state, l_pin, l_op_bal) = sel_loan
            
            l_due = float(l_due) if float(l_due or 0) > 0 else float(l_tot_rep or l_princ or 0.0)
            already_paid = max(0.0, float(l_tot_rep or l_princ) - float(l_due))
            
            with st.container(border=True):
                st.markdown(f"#### 👤 Borrower: **{l_cname}** (Loan: `{l_no}`, Acc: `{l_cacc}`)")
                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.metric("💵 Principal", f"₹{float(l_princ):,.2f}")
                sc2.metric("💳 Total Repayable", f"₹{float(l_tot_rep or l_princ):,.2f}")
                sc3.metric("🟢 Repaid So Far", f"₹{already_paid:,.2f}")
                sc4.metric("🔴 Outstanding Due", f"₹{float(l_due):,.2f}")
                st.caption(f"📌 **Loan Term:** {l_scheme} | **Monthly Installment:** {'₹{:,.2f}'.format(float(l_inst or 0)) if float(l_inst or 0) > 0 else '₹0.00'}")
            
            sched_status_rows = pl_sched_map.get(l_id, [])
            if sched_status_rows:
                with st.expander("📋 View Installment Amortization Schedule & Payment Status", expanded=False):
                    df_sched_st = pd.DataFrame(sched_status_rows, columns=["EMI #", "From Date", "To Date", "Due Date", "Principal (₹)", "Interest (₹)", "EMI Amount (₹)", "Paid (₹)", "Status"])
                    st.dataframe(format_df_dates(df_sched_st[["EMI #", "From Date", "To Date", "Due Date", "EMI Amount (₹)", "Paid (₹)", "Status"]]), use_container_width=True, hide_index=True, height=240)

            with st.form(f"loan_repayment_form_{l_id}"):
                st.markdown("### 2️⃣ Payment Details")
                col_r1, col_r2, col_r3 = st.columns(3)
                pay_date = col_r1.date_input("Payment Date", value=date.today(), format="DD-MM-YYYY", key=f"pl_rep_pdate_{l_id}")
                default_amt = float(l_inst) if float(l_inst or 0) > 0 else (min(float(l_due), 1000.0) if float(l_due) > 0 else 500.0)
                amt_paid = col_r2.number_input("Amount Collected (₹)", min_value=1.0, max_value=float(l_due), value=min(default_amt, float(l_due)), step=100.0, help="Enter any amount paid by the borrower today", key=f"pl_rep_amt_{l_id}")
                pay_mode = col_r3.selectbox("Payment Mode", ["Cash in Hand (Office Drawer)", "Union Bank of India (UPI / NEFT)"], key=f"pl_rep_mode_{l_id}")
                
                rep_narration = st.text_input("Narration / Remarks / UTR", value=f"Repayment {l_cname} ({l_no})", key=f"pl_rep_narr_{l_id}")
                
                st.info(f"ℹ️ **Payment Preview:** Paying **₹{amt_paid:,.2f}** will reduce the borrower's remaining due from **₹{float(l_due):,.2f}** ➔ **₹{max(0.0, float(l_due) - amt_paid):,.2f}**.")
                
                if st.form_submit_button("💾 Confirm & Post Repayment Receipt", use_container_width=True, type="primary"):
                    rep_voucher = f"RPL{pay_date.strftime('%Y%m%d')}{l_id:03d}"
                    new_due = max(0.0, round(float(l_due) - float(amt_paid), 2))
                    new_status = 'CLOSED' if new_due <= 0 else 'ACTIVE'
                    
                    tot_loan_int = max(0.0, round(float(l_tot_rep or l_princ) - float(l_princ), 2))
                    tot_rep_val = float(l_tot_rep or l_princ)
                    cur_due_val = float(l_due)
                    
                    cycle_paid_so_far = max(0.0, round(tot_rep_val - cur_due_val, 2))
                    if tot_rep_val > 0 and tot_loan_int > 0:
                        cycle_int_rec = round(cycle_paid_so_far * (tot_loan_int / tot_rep_val), 2)
                    else:
                        cycle_int_rec = 0.0
                    rem_int_to_rec = max(0.0, round(tot_loan_int - cycle_int_rec, 2))
                    
                    if tot_rep_val > 0 and tot_loan_int > 0:
                        prop_int = round(float(amt_paid) * (tot_loan_int / tot_rep_val), 2)
                        if new_due <= 0:
                            int_portion = rem_int_to_rec
                        else:
                            int_portion = min(prop_int, rem_int_to_rec)
                        princ_portion = round(float(amt_paid) - int_portion, 2)
                    else:
                        int_portion = 0.0
                        princ_portion = float(amt_paid)
                    
                    success, msg = record_personal_loan_repayment(
                        l_id, l_cid, l_cname, l_cacc, l_no, str(pay_date), amt_paid, pay_mode, rep_voucher, rep_narration, new_due, new_status, princ_portion, int_portion
                    )
                    if success:
                        flash_success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
        else:
            st.info("No active personal loans pending repayment.")

    with tab3:
        st.subheader("🔄 Loan Renewal & Interest Reset / Rollover")
        all_ren_loans = [
            r for r in all_pl_data 
            if r[29] not in ('CLOSED', 'SETTLED') and (float(r[21] or 0) > 0 or float(r[13] or r[7] or 0) > 0)
        ]
        
        if all_ren_loans:
            r_loan_dict = {}
            for r in all_ren_loans:
                ren_str = f" [Cycle #{r[31]}]" if int(r[31] or 0) > 0 else ""
                eff_due = float(r[21]) if float(r[21] or 0) > 0 else float(r[13] or r[7] or 0.0)
                label = f"#{r[1]} - {r[3]} (Acc: {r[4]} | Due: ₹{eff_due:,.2f}{ren_str})"
                r_loan_dict[label] = r
                
            sel_ren_key = st.selectbox("1️⃣ Select Active Loan to Renew / Rollover", list(r_loan_dict.keys()), key="pl_ren_sel")
            sel_r_data = r_loan_dict[sel_ren_key]
            (cur_pl_id, cur_l_no, cur_cid, cur_cname, cur_cacc, cur_cphone, cur_sdate, cur_princ, cur_irate, cur_itype,
             cur_tdays, cur_tmonths, cur_tot_int, cur_tot_rep, cur_inst, cur_p_emi, cur_i_emi, cur_from, cur_to,
             cur_fdue, cur_ldue, cur_due, cur_dmode, cur_vno, cur_gname, cur_gphone, cur_grel, cur_gaddr,
             cur_purp, cur_stat, cur_rem, cur_ren_cnt, cur_last_ren, cur_str, cur_city, cur_state, cur_pin, cur_op_bal) = sel_r_data
             
            cur_due = float(cur_due) if float(cur_due or 0) > 0 else float(cur_tot_rep or cur_princ or 0.0)
            tot_orig_int = float(cur_tot_int or 0.0)
            tot_orig_rep = float(cur_tot_rep or (float(cur_princ) + tot_orig_int))
            cur_due_val = float(cur_due)
            
            cycle_paid_so_far = max(0.0, round(tot_orig_rep - cur_due_val, 2))
            if tot_orig_rep > 0 and tot_orig_int > 0:
                cycle_int_rec = round(cycle_paid_so_far * (tot_orig_int / tot_orig_rep), 2)
            else:
                cycle_int_rec = 0.0
                
            unearned_int_rem = max(0.0, round(tot_orig_int - cycle_int_rec, 2))
            net_princ_rem = max(0.0, round(cur_due_val - unearned_int_rem, 2))
            if net_princ_rem <= 0 and cur_due_val > 0:
                net_princ_rem = cur_due_val
            
            with st.container(border=True):
                st.markdown(f"#### 👤 Borrower: **{cur_cname}** (Loan: `{cur_l_no}`, Acc: `{cur_cacc}`)")
                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.metric("💵 Carried-Forward Principal", f"₹{net_princ_rem:,.2f}")
                sc2.metric("💳 Current Outstanding Due", f"₹{cur_due_val:,.2f}")
                sc3.metric("📈 Unearned Interest", f"₹{unearned_int_rem:,.2f}")
                sc4.metric("🔄 Renewal History", f"Cycle #{cur_ren_cnt + 1}" if cur_ren_cnt > 0 else "Cycle #1 (Initial)")
                st.caption(f"📌 **Sanctioned:** {cur_sdate} | **Last Renewed:** {cur_last_ren or 'Never'} | **Status:** `{cur_stat}`")

            st.markdown("### 2️⃣ Renewal Terms & New 12-Month Schedule")
            col_rn1, col_rn2, col_rn3, col_rn4 = st.columns(4)
            ren_date = col_rn1.date_input("Renewal Date (From)", value=date.today(), format="DD-MM-YYYY", key=f"pl_rnw_date_{cur_pl_id}")
            default_ren_princ = float(net_princ_rem if net_princ_rem > 0 else cur_due_val)
            renewed_principal = col_rn2.number_input("Renewed Principal Balance (₹)", min_value=0.0, value=default_ren_princ, step=500.0, help="Carried-forward principal balance to renew", key=f"pl_rnw_p_{cur_pl_id}")
            new_int_rate = col_rn3.number_input("Annual Interest Rate (%)", min_value=0.0, value=12.0, step=0.5, key=f"pl_rnw_r_{cur_pl_id}")
            new_tenure_days = col_rn4.number_input("New Tenure (Days)", min_value=1, value=100, step=5, help="Carried-forward loan tenure in days", key=f"pl_rnw_d_{cur_pl_id}")
            
            new_tenure_months = max(1, int(round(new_tenure_days / 30.0)))
            new_scheme_name = f"{new_tenure_days}-Day Loan (Renewed)"
            new_planned_interest = round(renewed_principal * (new_int_rate / 100.0) * (new_tenure_days / 365.0), 2)
            new_tot_repayable = round(renewed_principal + new_planned_interest, 2)
            new_p_emi = round(renewed_principal / float(new_tenure_months), 2)
            new_i_emi = round(new_planned_interest / float(new_tenure_months), 2)
            new_installment = round(new_tot_repayable / float(new_tenure_months), 2)
            
            with st.container(border=True):
                st.markdown("#### 📊 Live Loan Renewal Breakdown")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("💵 Renewed Principal", f"₹{renewed_principal:,.2f}")
                m2.metric(f"📈 New Interest ({new_int_rate}%)", f"₹{new_planned_interest:,.2f}")
                m3.metric("💳 Total Due (Repayable)", f"₹{new_tot_repayable:,.2f}")
                m4.metric("📅 New Monthly EMI", f"₹{new_installment:,.2f}")
                st.caption(f"📌 **Monthly Breakdown:** Principal EMI: **₹{new_p_emi:,.2f}** + Interest EMI: **₹{new_i_emi:,.2f}** = Total EMI: **₹{new_installment:,.2f}** per month for {new_tenure_days} days ({new_tenure_months} months).")
                
            ren_remarks = st.text_input("Renewal Remarks / Notes", value=f"Loan Rollover & Term Renewal - Cycle #{cur_ren_cnt+1}", key=f"pl_rnw_rem_{cur_pl_id}")
            
            if st.button("🔄 Confirm & Execute Loan Renewal", use_container_width=True, type="primary", key=f"btn_rnw_pl_{cur_pl_id}"):
                if renewed_principal <= 0:
                    st.error("❌ Cannot renew a loan with ₹0.00 balance! The loan is already fully settled.")
                    st.stop()
                    
                ren_voucher = f"RNW{ren_date.strftime('%Y%m%d')}{cur_pl_id:03d}"
                
                if new_planned_interest > 0:
                    post_automated_jv(
                        f"Loan Renewal Interest Booking [{ren_voucher}]: {cur_l_no} - {cur_cname} (New Term Planned Interest: ₹{new_planned_interest:,.2f})",
                        'AST-108',
                        'LIA-104',
                        new_planned_interest,
                        voucher_date=ren_date
                    )

                ren_schedule = generate_loan_schedule(ren_date, renewed_principal, new_planned_interest, tenure_months=new_tenure_months)
                ren_loan_from = ren_schedule[0]["from_date"] if ren_schedule else str(ren_date)
                ren_loan_to = ren_schedule[-1]["to_date"] if ren_schedule else str(ren_date)
                ren_first_due = ren_schedule[0]["due_date"] if ren_schedule else str(ren_date)
                ren_last_due = ren_schedule[-1]["due_date"] if ren_schedule else str(ren_date)

                run_query("DELETE FROM loan_emi_schedules WHERE loan_id = ? AND loan_type = 'PERSONAL' AND status = 'PENDING'", (cur_pl_id,), fetch=False)
                batch_insert_loan_schedules('PERSONAL', cur_pl_id, cur_l_no, ren_schedule, ren_date)

                new_ren_cnt = int(cur_ren_cnt or 0) + 1
                updated_remarks = f"{cur_rem or ''} | [Renewed Cycle #{new_ren_cnt} on {ren_date} (P: ₹{renewed_principal:,.2f}, I: ₹{new_planned_interest:,.2f})]".strip(" | ")
                
                run_query("""
                    UPDATE personal_loans
                    SET principal_amount = ?,
                        interest_rate = ?,
                        interest_type = ?,
                        tenure_days = ?,
                        tenure_months = ?,
                        total_interest = ?,
                        total_repayable = ?,
                        installment_amount = ?,
                        outstanding_due = ?,
                        sanction_date = ?,
                        loan_from_date = ?,
                        loan_to_date = ?,
                        first_emi_due = ?,
                        last_emi_due = ?,
                        monthly_principal_emi = ?,
                        monthly_interest_emi = ?,
                        renewal_count = ?,
                        last_renewal_date = ?,
                        status = 'ACTIVE',
                        remarks = ?
                    WHERE id = ?
                """, (
                    renewed_principal,
                    new_int_rate,
                    new_scheme_name,
                    new_tenure_days,
                    new_tenure_months,
                    new_planned_interest,
                    new_tot_repayable,
                    new_installment,
                    new_tot_repayable,
                    str(ren_date),
                    ren_loan_from,
                    ren_loan_to,
                    ren_first_due,
                    ren_last_due,
                    new_p_emi,
                    new_i_emi,
                    new_ren_cnt,
                    str(ren_date),
                    updated_remarks,
                    cur_pl_id
                ), fetch=False)

                acc_r = run_query("SELECT id FROM accounts WHERE customer_id = ?", (cur_cid,))
                if acc_r:
                    a_id = acc_r[0][0]
                    run_query("UPDATE accounts SET balance = ? WHERE id = ?", (new_tot_repayable, a_id), fetch=False)
                    run_query("INSERT INTO transactions (account_id, type, amount, balance_after, date) VALUES (?, ?, ?, ?, ?)", (a_id, f"LOAN RENEWAL [{cur_l_no}]", new_tot_repayable, new_tot_repayable, str(ren_date)), fetch=False)
                    
                clear_db_cache()
                flash_success(f"🎉 Loan **#{cur_l_no}** for **{cur_cname}** successfully renewed! (Cycle #{new_ren_cnt}) | New Repayable Due: **₹{new_tot_repayable:,.2f}** | Monthly EMI: **₹{new_installment:,.2f}/mo**")
                st.rerun()
        else:
            st.info("ℹ️ No active loans with an outstanding balance pending renewal. (Fully repaid or closed loans do not require rollover renewal).")

    with tab4:
        st.subheader("✏️ Edit / Delete Personal Loan & Opening Balance")
        all_edit_loans = all_pl_data
        if all_edit_loans:
            e_opts = {f"#{r[1]} - {r[3]} (Acc: {r[4]} | Due: ₹{float(r[21]):,.2f} | Stat: {r[29]})": r for r in all_edit_loans}
            sel_pl_label = st.selectbox("Select Personal Loan to Edit or Manage", list(e_opts.keys()), key="pl_edit_sel")
            row = e_opts[sel_pl_label]
            (sel_pl_id, l_no, c_id, c_name, c_acc, c_phone, s_date, princ, rate, i_type,
             t_days, t_months, t_int, t_rep, inst_amt, p_emi_val, i_emi_val, from_d, to_d,
             fdue_d, ldue_d, out_due, d_mode, v_no, g_name, g_phone, g_rel, g_addr,
             purp, stat, rem, ren_cnt, last_ren, c_str, c_city, c_state, c_pin, op_bal_val) = row
            
            try:
                s_date_obj = datetime.strptime(str(s_date)[:10], "%Y-%m-%d").date()
            except Exception:
                s_date_obj = date.today()

            pl_op_bal_res = cached_query("SELECT voucher_date FROM journal_vouchers WHERE (narration LIKE ? OR narration LIKE ?) ORDER BY jv_id ASC LIMIT 1", (f"%[{l_no}]%", f"%Personal Loan%{l_no}%"))
            try:
                pl_op_bal_dt = pd.to_datetime(pl_op_bal_res[0][0]).date() if pl_op_bal_res and pl_op_bal_res[0] and pl_op_bal_res[0][0] else s_date_obj
            except Exception:
                pl_op_bal_dt = s_date_obj
            
            is_closed = (stat in ["CLOSED"])
            
            with st.container(border=True):
                st.markdown(f"#### 👤 Borrower: **{c_name}** (Acc: `{c_acc}` | ID: `#{c_id}` | Renewals: `Cycle #{ren_cnt}`)")
                
                if is_closed:
                    st.warning(f"🔒 **Personal Loan #{l_no} is currently CLOSED.** All fields are locked from editing to protect finalized loan records.")
                    col_reopen, _ = st.columns([1, 2])
                    if col_reopen.button(f"🔓 Reopen / Reactivate Personal Loan #{l_no}", key=f"reopen_pl_{sel_pl_id}", type="secondary"):
                        run_query("UPDATE personal_loans SET status = 'ACTIVE' WHERE id = ?", (sel_pl_id,), fetch=False)
                        clear_db_cache()
                        flash_success(f"✅ Personal Loan #{l_no} has been reopened to ACTIVE status. Editing fields are now unlocked.")
                        st.rerun()
                
                st.markdown("### 1️⃣ Financial Terms & Repayment Calculation")
                col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                new_princ = col_f1.number_input("Sanctioned Principal Amount (₹) *", min_value=100.0, value=float(princ), step=1000.0, disabled=is_closed, help="Original principal amount sanctioned to the borrower", key=f"pl_ed_p_{sel_pl_id}")
                new_op_bal = col_f2.number_input("Opening Balance (₹) *", min_value=0.0, value=float(op_bal_val or princ), step=500.0, disabled=is_closed, help="Initial opening ledger balance at loan creation", key=f"pl_ed_opbal_{sel_pl_id}")
                new_rate = col_f3.number_input("Annual Interest Rate (%) *", min_value=0.0, value=float(rate or 12.0), step=0.5, disabled=is_closed, key=f"pl_ed_r_{sel_pl_id}")
                new_t_days = col_f4.number_input("Loan Period / Tenure (Days) *", min_value=1, value=int(t_days or (t_months * 30 if t_months else 100)), step=5, disabled=is_closed, key=f"pl_ed_d_{sel_pl_id}")
                
                new_t_months = max(1, int(round(new_t_days / 30.0)))
                calc_tot_interest = round(new_princ * (new_rate / 100.0) * (new_t_days / 365.0), 2)
                calc_tot_repayable = round(new_princ + calc_tot_interest, 2)
                calc_p_emi = round(new_princ / float(new_t_months), 2)
                calc_i_emi = round(calc_tot_interest / float(new_t_months), 2)
                calc_installment = round(calc_tot_repayable / float(new_t_months), 2)
                
                with st.container(border=True):
                    st.markdown("#### 📊 Live Updated Loan Breakdown")
                    pem1, pem2, pem3, pem4 = st.columns(4)
                    pem1.metric("💵 Principal", f"₹{new_princ:,.2f}")
                    pem2.metric(f"📈 Total Interest ({new_rate}%)", f"₹{calc_tot_interest:,.2f}")
                    pem3.metric("💳 Total Repayable", f"₹{calc_tot_repayable:,.2f}")
                    pem4.metric("📅 Monthly EMI", f"₹{calc_installment:,.2f}")
                    st.caption(f"📌 **Monthly Breakdown:** Principal EMI: **₹{calc_p_emi:,.2f}** + Interest EMI: **₹{calc_i_emi:,.2f}** = Total EMI: **₹{calc_installment:,.2f}** per month for {new_t_days} days ({new_t_months} months).")

                st.markdown("### 2️⃣ Loan Administrative & Legal Details")
                col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                new_l_no = col_a1.text_input("Loan Number *", value=str(l_no), disabled=is_closed, key=f"pl_ed_lno_{sel_pl_id}")
                new_s_date = col_a2.date_input("Sanction Date", value=s_date_obj, format="DD-MM-YYYY", disabled=is_closed, key=f"pl_ed_sdate_{sel_pl_id}")
                new_op_bal_date = col_a3.date_input("Opening / Disbursal Date (Opening Balance Date)", value=pl_op_bal_dt, format="DD-MM-YYYY", disabled=is_closed, key=f"pl_ed_op_date_{sel_pl_id}")
                new_status = col_a4.selectbox(
                    "Loan Status",
                    ["ACTIVE", "CLOSED", "COURT_CASE", "POLICE_COMPLAINT", "NOT_REMITTING"],
                    index=["ACTIVE", "CLOSED", "COURT_CASE", "POLICE_COMPLAINT", "NOT_REMITTING"].index(stat) if stat in ["ACTIVE", "CLOSED", "COURT_CASE", "POLICE_COMPLAINT", "NOT_REMITTING"] else 0,
                    disabled=is_closed,
                    key=f"pl_ed_stat_{sel_pl_id}"
                )
                
                col_g1, col_g2, col_g3 = st.columns(3)
                new_g_name = col_g1.text_input("Guarantor / Surety Name", value=str(g_name or ""), disabled=is_closed, key=f"pl_ed_gname_{sel_pl_id}")
                new_g_phone = col_g2.text_input("Guarantor Phone", value=str(g_phone or ""), disabled=is_closed, key=f"pl_ed_gphone_{sel_pl_id}")
                new_g_rel = col_g3.text_input("Guarantor Relationship", value=str(g_rel or "Surety"), disabled=is_closed, key=f"pl_ed_grel_{sel_pl_id}")
                
                col_g4, col_g5 = st.columns(2)
                new_g_addr = col_g4.text_input("Guarantor Address", value=str(g_addr or ""), disabled=is_closed, key=f"pl_ed_gaddr_{sel_pl_id}")
                new_d_mode = col_g5.selectbox("Disbursal Mode", ["Union Bank of India", "Cash in Hand (Office Drawer)"], index=0 if "Union Bank" in str(d_mode or "") else 1, disabled=is_closed, key=f"pl_ed_dmode_{sel_pl_id}")
                
                col_n1, col_n2 = st.columns(2)
                new_purp = col_n1.text_input("Loan Purpose", value=str(purp or "Personal / Household Finance"), disabled=is_closed, key=f"pl_ed_purp_{sel_pl_id}")
                new_rem = col_n2.text_input("Remarks / Notes", value=str(rem or ""), disabled=is_closed, key=f"pl_ed_rem_{sel_pl_id}")
                
                st.markdown("### 3️⃣ Current Outstanding Due Balance")
                col_pldue1, col_pldue2 = st.columns(2)
                recalc_pl_due = col_pldue1.checkbox(f"🔄 Reset Outstanding Due to Total Repayable (₹{calc_tot_repayable:,.2f})", value=(float(out_due or 0) == float(t_rep or 0)), disabled=is_closed, key=f"pl_recalc_due_{sel_pl_id}")
                if recalc_pl_due:
                    new_out_due = calc_tot_repayable
                    col_pldue2.info(f"Outstanding Due set to **₹{new_out_due:,.2f}**")
                else:
                    new_out_due = col_pldue2.number_input("Outstanding Due Balance (₹) *", min_value=0.0, value=float(out_due or calc_tot_repayable), step=100.0, disabled=is_closed, help="Current unpaid balance owed by the borrower on this loan.", key=f"pl_ed_due_{sel_pl_id}")
                
                ed_sched = generate_loan_schedule(new_s_date, new_princ, calc_tot_interest, tenure_months=new_t_months)
                with st.expander(f"📅 View Updated {len(ed_sched)}-Month EMI Amortization Schedule Preview", expanded=False):
                    df_ed_pl_prev = pd.DataFrame(ed_sched).rename(columns={
                        "emi_number": "EMI NOS", "from_date": "FROM DATE", "to_date": "TO DATE",
                        "due_date": "DUE DATE", "principal_component": "PRINCIPAL (₹)",
                        "interest_component": "INTEREST (₹)", "emi_amount": "EMI AMOUNT (₹)"
                    })[["EMI NOS", "FROM DATE", "TO DATE", "DUE DATE", "PRINCIPAL (₹)", "INTEREST (₹)", "EMI AMOUNT (₹)"]]
                    st.dataframe(format_df_dates(df_ed_pl_prev), use_container_width=True, hide_index=True, height=220)

                if is_closed:
                    st.info("ℹ️ *This loan is **CLOSED**. To modify terms and save updates, click the **'🔓 Reopen / Reactivate Personal Loan'** button above.*")
                else:
                    if st.button("💾 Save & Apply Updated Loan Terms", type="primary", use_container_width=True, key=f"btn_save_pl_{sel_pl_id}"):
                        new_op_str = new_op_bal_date.strftime("%Y-%m-%d")
                        success, msg = update_personal_loan_details(
                            sel_pl_id, new_l_no, new_s_date, new_princ, new_rate, new_t_days,
                            new_out_due, new_d_mode, new_g_name, new_g_phone, new_g_rel,
                            new_g_addr, new_purp, new_status, new_rem,
                            new_op_bal_date=new_op_str,
                            new_op_bal=new_op_bal
                        )
                        clear_db_cache()
                        if success:
                            flash_success(f"🎉 Loan **#{new_l_no}** updated successfully! New Total Repayable: **₹{calc_tot_repayable:,.2f}** | Monthly EMI: **₹{calc_installment:,.2f}/mo**")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to update loan: {msg}")

            st.write("---")
            with st.expander(f"🚨 Danger Zone: Delete Loan #{l_no}", expanded=False):
                st.error(f"⚠️ **Warning:** Permanently deleting Loan **#{l_no}** for **{c_name}** will remove this loan sanction record, its repayment transactions, and its schedule rows from the database.")
                conf_del = st.checkbox(f"Yes, I confirm I want to permanently delete Loan #{l_no} (Borrower: {c_name})", key=f"conf_del_pl_{sel_pl_id}")
                if conf_del:
                    if st.button(f"🗑️ Permanently Delete Loan #{l_no}", type="primary", use_container_width=True, key=f"btn_del_pl_{sel_pl_id}"):
                        success, msg = delete_personal_loan_entry(sel_pl_id)
                        rem_loans = run_query("SELECT SUM(outstanding_due) FROM personal_loans WHERE customer_id = ?", (c_id,))
                        new_acc_bal = float(rem_loans[0][0]) if rem_loans and rem_loans[0][0] is not None else 0.0
                        run_query("UPDATE accounts SET balance = ? WHERE customer_id = ?", (new_acc_bal, c_id), fetch=False)
                        
                        clear_db_cache()
                        if success:
                            flash_success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to delete loan: {msg}")
        else:
            st.info("No personal loan records found to edit or manage.")

    with tab5:
        st.subheader("📋 Active Personal Loans & Legal Tracker")
        status_filter = st.selectbox("Filter by Loan Status", ["ALL", "ACTIVE", "COURT_CASE", "POLICE_COMPLAINT", "CLOSED", "NOT_REMITTING"], key="pl_filter_st")
        
        filtered_pl = [r for r in reversed(all_pl_data) if status_filter == "ALL" or r[29] == status_filter]
        if filtered_pl:
            pl_rows = [
                (r[0], r[1], r[3], r[4], float(r[7] or 0), float(r[14] or 0), float(r[21] or 0), int(r[31] or 0), r[29], r[30])
                for r in filtered_pl
            ]
            df_pl = pd.DataFrame(pl_rows, columns=["ID", "Loan No", "Customer Name", "Account No", "Principal (₹)", "Daily/Monthly Inst (₹)", "Outstanding Due (₹)", "Renewal Cycle", "Status", "Legal Remarks / Notes"])
            
            tot_p = df_pl["Principal (₹)"].sum()
            tot_d = df_pl["Outstanding Due (₹)"].sum()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Sanctioned Principal", f"₹{tot_p:,.2f}")
            m2.metric("Total Outstanding Due Portfolio", f"₹{tot_d:,.2f}")
            m3.metric("Total Loan Count", len(df_pl))
            
            st.dataframe(format_df_dates(df_pl), use_container_width=True, hide_index=True, height=320)
            
            col_x, col_c, col_p = st.columns(3)
            with col_x:
                if st.button("📊 Prepare Register (.xlsx)", key="btn_prep_pl_reg_xl", use_container_width=True):
                    st.session_state.pl_reg_xl_bytes = pdf_generator.create_excel_report("Personal Loan Register", df_pl)
                if "pl_reg_xl_bytes" in st.session_state and st.session_state.pl_reg_xl_bytes:
                    st.download_button("📥 Click to Download (.xlsx)", st.session_state.pl_reg_xl_bytes, "personal_loans.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_pl_reg_xl")
            with col_c:
                st.download_button("📥 Download Register (.csv)", df_pl.to_csv(index=False).encode('utf-8'), "personal_loans.csv", "text/csv", use_container_width=True, key="dl_pl_reg_csv")
            with col_p:
                if st.button("📄 Prepare Register PDF", key="btn_prep_pl_reg_pdf", use_container_width=True):
                    st.session_state.pl_reg_pdf_bytes = pdf_generator.create_pdf_report("Personal Loan Register", df_pl)
                if "pl_reg_pdf_bytes" in st.session_state and st.session_state.pl_reg_pdf_bytes:
                    st.download_button("📥 Click to Download PDF", st.session_state.pl_reg_pdf_bytes, "personal_loans.pdf", "application/pdf", use_container_width=True, key="dl_pl_reg_pdf")
        else:
            st.info("No personal loan records found matching this filter.")

    with tab6:
        st.subheader("🖨️ Loan Statement & Passbook (Matching VAISAKH.xlsx)")
        if all_pl_data:
            pl_opts = {f"#{r[1]} - {r[3]} (Acc: {r[4]})": r for r in all_pl_data}
            sel_pr_label = st.selectbox("Select Loan to View Passbook & Export Statement", list(pl_opts.keys()), key="pl_print_sel")
            p = pl_opts[sel_pr_label]
            (sel_pr_id, p_lno, p_cid, p_cname, p_cacc, p_cphone, p_sdate, p_princ, p_rate, p_scheme,
             p_tdays, p_ten_mo, p_tot_int, p_tot_rep, p_inst, p_p_emi, p_i_emi, p_from, p_to,
             p_fdue, p_ldue, p_out_due, p_dmode, p_vno, p_gname, p_gphone, p_grel, p_gaddr,
             p_purp, p_stat, p_rem, p_ren_cnt, p_last_ren, p_cstr, p_ccity, p_cstate, p_cpin, p_op_bal) = p
            
            addr_parts = [part for part in [p_cstr, p_ccity, p_cstate, p_cpin] if part and str(part).strip()]
            p_caddr = ", ".join(addr_parts) if addr_parts else "Balaramapuram, Trivandrum"
            
            sched_rows = pl_sched_map.get(sel_pr_id, [])
            if not sched_rows:
                gen_s = generate_loan_schedule(p_sdate, float(p_princ or 0), float(p_tot_int or 0), tenure_months=int(p_ten_mo or 12))
                sched_rows = [(s['emi_number'], s['from_date'], s['to_date'], s['due_date'], s['principal_component'], s['interest_component'], s['emi_amount'], 0.0, 'PENDING') for s in gen_s]

            df_sched = pd.DataFrame(sched_rows, columns=["EMI NOS", "FROM DATE", "TO DATE", "DUE DATE", "PRINCIPAL (Rs.)", "INTEREST (Rs.)", "EMI AMOUNT (Rs.)", "PAID (Rs.)", "STATUS"])
            
            loan_status_label = "RENEWED" if int(p_ren_cnt or 0) > 0 else "NEW LOAN"
            p_p_emi_val = float(p_p_emi or (float(p_princ or 0) / 12.0))
            p_i_emi_val = float(p_i_emi or (float(p_tot_int or 0) / 12.0))
            p_tot_emi_val = float(p_inst or (p_p_emi_val + p_i_emi_val))
            
            loan_data_dict = {
                "loan_no": p_lno,
                "status": loan_status_label,
                "party_name": p_cname,
                "account_no": p_cacc,
                "address": p_caddr,
                "mobile": p_cphone,
                "guarantor_name": p_gname,
                "guarantor_relation": p_grel,
                "guarantor_address": p_gaddr,
                "guarantor_phone": p_gphone,
                "loan_amount": float(p_princ or 0),
                "interest_rate": float(p_rate or 12.0),
                "total_interest": float(p_tot_int or 0),
                "total_amount": float(p_tot_rep or 0),
                "principal_emi": p_p_emi_val,
                "interest_emi": p_i_emi_val,
                "total_emi": p_tot_emi_val,
                "loan_date": p_sdate,
                "duration": f"{p_tdays} DAYS ({p_ten_mo or 12} Months)" if p_tdays else f"{p_ten_mo or 12} MONTHS",
                "loan_from": str(p_from) if p_from else str(p_sdate),
                "loan_to": str(p_to) if p_to else (df_sched.iloc[-1]["TO DATE"] if not df_sched.empty else ""),
                "first_emi_due": str(p_fdue) if p_fdue else (df_sched.iloc[0]["DUE DATE"] if not df_sched.empty else ""),
                "last_emi_due": str(p_ldue) if p_ldue else (df_sched.iloc[-1]["DUE DATE"] if not df_sched.empty else ""),
                "renewal_count": int(p_ren_cnt or 0)
            }

            with st.container(border=True):
                st.markdown("### 📖 **LOAN PASSBOOK / LOAN STATEMENT OF ACCOUNT**")
                st.caption("AARSHA NIDHI LIMITED | 6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram")
                st.divider()
                
                hb1, hb2 = st.columns(2)
                hb1.markdown(f"**LOAN ACCOUNT NO:** `{p_lno}`  \n**STATUS:** `{loan_status_label}` {'(Cycle #' + str(p_ren_cnt) + ')' if int(p_ren_cnt or 0) > 0 else ''}  \n**LOAN PARTY NAME:** **{p_cname}**  \n**ADDRESS:** {p_caddr}  \n**MOBILE NUMBER:** {p_cphone}")
                hb2.markdown(f"**MEMBER ACC NO:** `{p_cacc}`  \n**GUARANTOR NAME:** {p_gname} ({p_grel})  \n**GUARANTOR ADDRESS:** {p_gaddr}  \n**GUARANTOR MOBILE NO:** {p_gphone}")
                
                st.divider()
                fb1, fb2, fb3 = st.columns(3)
                fb1.metric("LOAN AMOUNT", f"₹{float(p_princ):,.2f}", f"Principal EMI: ₹{p_p_emi_val:,.2f}")
                fb2.metric(f"INTEREST ({p_rate}%)", f"₹{float(p_tot_int):,.2f}", f"Interest EMI: ₹{p_i_emi_val:,.2f}")
                fb3.metric("TOTAL AMOUNT", f"₹{float(p_tot_rep):,.2f}", f"Total Monthly EMI: ₹{p_tot_emi_val:,.2f}")
                
                db1, db2, db3 = st.columns(3)
                dur_label = f"{p_tdays} Days ({p_ten_mo or 12} Months)" if p_tdays else f"{p_ten_mo or 12} Months"
                db1.caption(f"🗓️ **Loan Date:** {p_sdate} | **Duration:** {dur_label}")
                db2.caption(f"📅 **Loan Period:** {p_from} to {p_to}")
                db3.caption(f"⏰ **First Due:** {p_fdue} | **Last Due:** {p_ldue}")

            # Repayment ledger from in-memory pl_rep_map
            rep_txs = pl_rep_map.get(sel_pr_id, [])
            ledger_rows = []
            running_bal = float(p_tot_rep or 0)
            ledger_rows.append({
                "Date": str(p_sdate),
                "Voucher No": str(p_lno),
                "Particulars": f"Loan Disbursal (Principal ₹{float(p_princ):,.2f} + Int ₹{float(p_tot_int):,.2f})",
                "Payment Mode": "Disbursal",
                "Debit (₹)": float(p_tot_rep or 0),
                "Credit (₹)": 0.0,
                "Balance (₹)": running_bal
            })
            if rep_txs:
                for rx in rep_txs:
                    p_date, v_no, amt, mode, narr = rx
                    c_amt = float(amt or 0)
                    running_bal = round(running_bal - c_amt, 2)
                    ledger_rows.append({
                        "Date": str(p_date),
                        "Voucher No": str(v_no or ""),
                        "Particulars": str(narr or "EMI Installment Repayment"),
                        "Payment Mode": str(mode or "Cash"),
                        "Debit (₹)": 0.0,
                        "Credit (₹)": c_amt,
                        "Balance (₹)": running_bal
                    })
            df_rep_ledger = pd.DataFrame(ledger_rows)

            st.markdown("#### 📜 **CUSTOMER REPAYMENT LEDGER & STATEMENT (DEBIT / CREDIT)**")
            st.dataframe(format_df_dates(df_rep_ledger), use_container_width=True, hide_index=True, height=260)

            st.markdown("#### 📅 **12-MONTH EMI AMORTIZATION TABLE**")
            st.dataframe(format_df_dates(df_sched), use_container_width=True, hide_index=True, height=260)

            exp_col1, exp_col2, exp_col3 = st.columns(3)
            with exp_col1:
                if st.button("📊 Prepare Passbook (.xlsx)", key=f"btn_prep_pl_xl_{sel_pr_id}", use_container_width=True):
                    st.session_state[f"pl_xl_bytes_{sel_pr_id}"] = pdf_generator.create_loan_passbook_excel(loan_data_dict, df_sched, df_rep_ledger)
                if f"pl_xl_bytes_{sel_pr_id}" in st.session_state:
                    st.download_button(
                        "📥 Click to Download Passbook (.xlsx)",
                        data=st.session_state[f"pl_xl_bytes_{sel_pr_id}"],
                        file_name=f"Loan_Passbook_{p_lno}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key=f"pl_tab6_xl_{sel_pr_id}"
                    )
            with exp_col2:
                if st.button("📄 Prepare Passbook PDF", key=f"btn_prep_pl_pdf_{sel_pr_id}", use_container_width=True):
                    st.session_state[f"pl_pdf_bytes_{sel_pr_id}"] = pdf_generator.create_loan_passbook_pdf(loan_data_dict, df_sched, df_rep_ledger)
                if f"pl_pdf_bytes_{sel_pr_id}" in st.session_state:
                    st.download_button(
                        "📥 Click to Download Passbook PDF",
                        data=st.session_state[f"pl_pdf_bytes_{sel_pr_id}"],
                        file_name=f"Loan_Passbook_{p_lno}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"pl_tab6_pdf_{sel_pr_id}"
                    )
            with exp_col3:
                if st.button("📑 Prepare Loan Agreement PDF", key=f"btn_prep_pl_agree_{sel_pr_id}", use_container_width=True):
                    st.session_state[f"pl_agree_bytes_{sel_pr_id}"] = pdf_generator.create_loan_agreement_pdf(loan_data_dict, df_sched)
                if f"pl_agree_bytes_{sel_pr_id}" in st.session_state:
                    st.download_button(
                        "📥 Click to Download Agreement PDF",
                        data=st.session_state[f"pl_agree_bytes_{sel_pr_id}"],
                        file_name=f"Loan_Agreement_{p_lno}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"pl_tab6_agree_{sel_pr_id}"
                    )
        else:
            st.info("No personal loan records found to view statement or passbook.")

@st.cache_data(ttl=600, show_spinner=False)
def get_cached_gl_photo(loan_id):
    """Fetches and caches pledged gold ornament image bytes on-demand."""
    r = run_query("SELECT gold_image_file, gold_image_data FROM gold_loans WHERE id = ?", (loan_id,))
    if r and r[0] and r[0][1]:
        return r[0][0], bytes(r[0][1])
    return None, None


def render_gold_loans():
    st.title("🪙 Gold & Jewel Loan Management")
    
    # ⚡ FAST SINGLE UNIFIED QUERY: Fetches all gold loans, schedules, and repayments in 1 instant bundle
    all_gl_data, gl_sched_map, gl_rep_map = get_all_gold_loans_bundle()
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🪙 Appraisal, Sanction & Opening Balance", 
        "💳 Collect Repayment / Installment", 
        "🔄 Jewel Loan Renewal & Pledge Rollover",
        "✏️ Edit / Delete Gold Loan & Opening Balance",
        "🏷️ Gold Vault Register & Safe Custody", 
        "🖨️ Loan Statement & Passbook"
    ])
    
    with tab1:
        st.subheader("🪙 Gold Appraisal, Jewel Loan Sanction & Opening Balance")
        cust_raw = cached_query("""
            SELECT c.id, c.name, COALESCE(c.account_no, 'N/A'), c.phone, c.street, c.city, c.state, c.pincode 
            FROM customers c 
            ORDER BY c.name ASC, c.id ASC
        """) or []
        if not cust_raw:
            st.warning("Please register a customer with Gold Loan account type first.")
            return
            
        cust_list = []
        for c in cust_raw:
            c_id, c_name, c_acc, c_phone, c_str, c_city, c_state, c_pin = c
            addr_parts = [p for p in [c_str, c_city, c_state, c_pin] if p and str(p).strip()]
            c_addr = ", ".join(addr_parts) if addr_parts else "Balaramapuram, Trivandrum"
            cust_list.append((c_id, c_name, c_acc, c_phone, c_addr))
            
        cust_dict = {f"#{c[0]} - {c[1]} (Acc: {c[2]} | Ph: {c[3]})": c for c in cust_list}
        
        selected_cust_label = st.selectbox("1️⃣ Select Customer / Borrower", list(cust_dict.keys()), key="gl_cust_sel")
        selected_cust = cust_dict[selected_cust_label]
        selected_cust_id, selected_cust_name, selected_cust_acc, selected_cust_phone, selected_cust_addr = selected_cust
        
        st.markdown("### 2️⃣ Jewel Appraisal & Safe Custody Details")
        col_a1, col_a2, col_a3 = st.columns(3)
        sanction_date = col_a1.date_input("Appraisal / Sanction Date", value=date.today(), format="DD-MM-YYYY", key="gl_sanc_date")
        op_bal_date = col_a2.date_input("Opening / Disbursal Date", value=sanction_date, format="DD-MM-YYYY", key="gl_op_bal_date")
        gold_rate = col_a3.number_input("Today's 22K Gold Market Rate (₹ / gram)", min_value=1000.0, value=6500.0, step=50.0, key="gl_gold_rate")
        
        ornament_desc = st.text_input("Ornaments Description", value="2 Gold Bangles, 1 Chain 22K Hallmarked", key="gl_orn_desc")
        
        col_w1, col_w2, col_w3, col_w4 = st.columns(4)
        item_count = col_w1.number_input("Item Count", min_value=1, value=2, step=1, key="gl_item_cnt")
        gross_weight = col_w2.number_input("Gross Weight (g)", min_value=0.1, value=15.500, step=0.1, format="%.3f", key="gl_gross_wt")
        stone_ded = col_w3.number_input("Stone / Dross Deduction (g)", min_value=0.0, value=0.500, step=0.05, format="%.3f", key="gl_stone_ded")
        net_weight = max(0.01, round(float(gross_weight) - float(stone_ded), 3))
        col_w4.metric("Net Gold Weight", f"{net_weight:.3f} g")
        
        # Auto Market Valuation & 75% LTV
        market_val = round(net_weight * gold_rate, 2)
        max_eligible = round(market_val * 0.75, 2)
        
        col_v1, col_v2 = st.columns(2)
        col_v1.info(f"💎 **Market Value:** ₹{market_val:,.2f}")
        col_v2.success(f"🎯 **Max Eligible Loan (75% LTV):** ₹{max_eligible:,.2f}")
        
        col_s1, col_s2, col_s3 = st.columns(3)
        cur_gl_cnt = len(all_gl_data) + 1
        packet_no = col_s1.text_input("Safe Vault Packet No", value=f"PKT-{cur_gl_cnt:03d}", key="gl_pkt_no")
        locker_no = col_s2.text_input("Locker Number", value="LOCKER-01", key="gl_locker_no")
        appraiser_name = col_s3.text_input("Certified Appraiser Name", value="Approved Nidhi Appraiser", key="gl_appr_name")
        
        st.markdown("### 📸 Pledged Gold / Jewel Ornament Photo")
        gl_disb_photo = st.file_uploader("Upload Gold / Ornament Photo (Optional - JPG, PNG, JPEG)", type=["jpg", "jpeg", "png"], key="gl_disb_photo_uploader")
        if gl_disb_photo:
            st.image(gl_disb_photo, caption="📸 Pledged Gold Ornaments Preview", width=350)
            
        st.markdown("### 3️⃣ Loan Financial Terms & Amortization")
        col_p1, col_p2, col_p3 = st.columns(3)
        default_gl_p = float(min(max_eligible, 50000.0)) if max_eligible >= 100.0 else float(max_eligible)
        principal = col_p1.number_input("Sanctioned Principal Amount (₹)", min_value=100.0, value=default_gl_p, step=1000.0, help="Original principal amount sanctioned / disbursed", key="gl_princ_inp")
        int_rate = col_p2.number_input("Annual Interest Rate (%)", min_value=0.0, value=12.0, step=0.5, key="gl_int_rate")
        tenure_days = col_p3.number_input("Loan Period / Tenure (Days)", min_value=1, value=365, step=10, help="Loan tenure in days (e.g., 90, 180, 365 days)", key="gl_tenure_days")
        
        tenure_months = max(1, int(round(tenure_days / 30.0)))
        loan_scheme_name = f"{tenure_days}-Day Gold Loan"
        tot_interest = round(principal * (int_rate / 100.0) * (tenure_days / 365.0), 2)
        tot_repayable = round(principal + tot_interest, 2)
        p_emi = round(principal / float(tenure_months), 2)
        i_emi = round(tot_interest / float(tenure_months), 2)
        installment = round(tot_repayable / float(tenure_months), 2)
        
        with st.container(border=True):
            st.markdown("#### 📊 Live Gold Loan Breakdown & EMI Structure")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💵 Principal", f"₹{principal:,.2f}")
            m1.metric(f"📈 Interest ({int_rate}%)", f"₹{tot_interest:,.2f}")
            m3.metric("💳 Total Due (Repayable)", f"₹{tot_repayable:,.2f}")
            m4.metric("📅 Monthly EMI", f"₹{installment:,.2f}")
            st.caption(f"📌 **Monthly Breakdown:** Principal EMI: **₹{p_emi:,.2f}** + Interest EMI: **₹{i_emi:,.2f}** = Total EMI: **₹{installment:,.2f}** per month for {tenure_days} days ({tenure_months} months).")

        preview_schedule = generate_loan_schedule(sanction_date, principal, tot_interest, tenure_months=tenure_months, loan_type='GOLD')
        with st.expander(f"📅 Preview {len(preview_schedule)}-Month EMI Amortization Schedule Table", expanded=False):
            df_prev = pd.DataFrame(preview_schedule)
            df_prev_display = df_prev.rename(columns={
                "emi_number": "EMI NOS", "from_date": "FROM DATE", "to_date": "TO DATE",
                "due_date": "DUE DATE", "principal_component": "PRINCIPAL (₹)",
                "interest_component": "INTEREST (₹)", "emi_amount": "EMI AMOUNT (₹)"
            })[["EMI NOS", "FROM DATE", "TO DATE", "DUE DATE", "PRINCIPAL (₹)", "INTEREST (₹)", "EMI AMOUNT (₹)"]]
            st.dataframe(format_df_dates(df_prev_display), use_container_width=True)

        st.markdown("### 4️⃣ Disbursal Mode, Opening Balance & Outstanding Due")
        col_dm1, col_dm2, col_dm3, col_dm4 = st.columns(4)
        disb_mode = col_dm1.selectbox("Disburse Funds From:", ["Union Bank of India (NEFT / UPI)", "Cash in Hand (Office Drawer)"], index=0, key="gl_disb_mode")
        opening_balance = col_dm2.number_input("Opening Balance (₹)", min_value=0.0, value=float(principal), step=500.0, key="gl_op_bal_amt", help="Starting opening ledger balance at account creation (defaults to Principal Amount).")
        outstanding_due = col_dm3.number_input("Initial Outstanding Due (₹)", min_value=0.0, value=float(tot_repayable), step=500.0, key="gl_init_due_amt", help="Initial unpaid amount due to be repaid by borrower (defaults to Total Repayable).")
        custom_gl_no = col_dm4.text_input("Custom Gold Loan Number (Optional - leave blank to auto-generate)", key="gl_cust_lno")
        remarks = st.text_input("Remarks / Condition Notes", value="Gold Pledged in Safe Vault", key="gl_remarks_input")
        
        if st.button("🪙 Confirm Appraisal & Disburse Gold Loan", use_container_width=True, type="primary", key="btn_confirm_gl_disb"):
            loan_no = custom_gl_no.strip() if custom_gl_no and custom_gl_no.strip() else f"GL-2026-{cur_gl_cnt:04d}"
            voucher_no = f"GLV{sanction_date.strftime('%Y%m%d')}{cur_gl_cnt:03d}"
            
            final_initial_due = float(outstanding_due) if float(outstanding_due or 0) > 0 else float(tot_repayable)
            
            if "Cash" in disb_mode:
                cur_cash = get_cash_balance()
                if cur_cash < principal:
                    st.warning(f"⚠️ Cash balance alert: Available ₹{cur_cash:,.2f}. Disbursing ₹{principal:,.2f}.")
                    
            gl_schedule = generate_loan_schedule(sanction_date, principal, tot_interest, tenure_months=tenure_months, loan_type='GOLD')
            loan_from = gl_schedule[0]["from_date"] if gl_schedule else str(sanction_date)
            loan_to = gl_schedule[-1]["to_date"] if gl_schedule else str(sanction_date)
            first_due = gl_schedule[0]["due_date"] if gl_schedule else str(sanction_date)
            last_due = gl_schedule[-1]["due_date"] if gl_schedule else str(sanction_date)
            
            # Process uploaded image
            img_name, img_bytes = save_uploaded_file(gl_disb_photo) if gl_disb_photo else (None, None)
            import psycopg2
            img_param = psycopg2.Binary(img_bytes) if (USING_SUPABASE and img_bytes) else img_bytes
            
            new_gl_row = run_query("""
                INSERT INTO gold_loans (
                    loan_no, customer_id, sanction_date, gold_rate_per_gram, ornament_details,
                    item_count, gross_weight, stone_deduction, net_weight, purity,
                    market_value, ltv_percent, principal_amount, opening_balance, interest_rate,
                    interest_rate_monthly, tenure_days, tenure_months, total_interest, total_repayable,
                    installment_amount, monthly_principal_emi, monthly_interest_emi, monthly_interest_due,
                    loan_from_date, loan_to_date, first_emi_due, last_emi_due,
                    outstanding_due, vault_packet_no, locker_no, appraiser_name,
                    disbursal_mode, voucher_no, status, remarks, renewal_count,
                    gold_image_file, gold_image_data
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, '22K',
                    ?, 75.00, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, 'ACTIVE', ?, 0,
                    ?, ?
                ) RETURNING id
            """, (
                loan_no, selected_cust_id, str(sanction_date), gold_rate, ornament_desc,
                item_count, gross_weight, stone_ded, net_weight,
                market_val, principal, float(opening_balance), int_rate,
                round(int_rate / 12.0, 2), tenure_days, tenure_months, tot_interest, tot_repayable,
                installment, p_emi, i_emi, i_emi,
                loan_from, loan_to, first_due, last_due,
                final_initial_due, packet_no, locker_no, appraiser_name,
                disb_mode, voucher_no, remarks,
                img_name, img_param
            ))
            
            if new_gl_row and new_gl_row[0]:
                new_gl_id = new_gl_row[0][0]
            else:
                gl_lookup = run_query("SELECT id FROM gold_loans WHERE loan_no = ?", (loan_no,))
                if gl_lookup and gl_lookup[0]:
                    new_gl_id = gl_lookup[0][0]
                else:
                    st.error(f"❌ Failed to disburse Gold Loan **{loan_no}**. Please check database connection.")
                    st.stop()
            
            batch_insert_loan_schedules('GOLD', new_gl_id, loan_no, gl_schedule, sanction_date)
                
            part_text = f"Gold Loan Disbursal: {selected_cust_name} (Acc: {selected_cust_acc}) [{loan_no} | {packet_no}]"
        
            bank_or_cash_code = 'AST-102' if "Union Bank" in disb_mode else 'AST-101'
            if "Union Bank" in disb_mode:
                last_bb = run_query("SELECT balance FROM bank_book WHERE bank_name = 'Union Bank of India' ORDER BY id DESC LIMIT 1")
                prev_b = float(last_bb[0][0]) if (last_bb and last_bb[0][0] is not None) else 0.0
                new_b = prev_b - principal
                run_query("""
                    INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, narration, account_code)
                    VALUES (?, ?, ?, 0, ?, ?, 'Union Bank of India', ?, 'AST-110')
                """, (str(op_bal_date), voucher_no, part_text, principal, new_b, remarks), fetch=False)
            else:
                last_cb = run_query("SELECT balance FROM cash_book ORDER BY id DESC LIMIT 1")
                prev_c = float(last_cb[0][0]) if (last_cb and last_cb[0][0] is not None) else 0.0
                new_c = prev_c - principal
                run_query("""
                    INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, narration, account_code)
                    VALUES (?, ?, ?, 0, ?, ?, ?, 'AST-110')
                """, (str(op_bal_date), voucher_no, part_text, principal, new_c, remarks), fetch=False)
            
            cr_entries = [(bank_or_cash_code, principal)]
            if tot_interest > 0:
                cr_entries.append(('LIA-104', tot_interest))
            post_compound_jv(
                f"Gold Loan Disbursal [{voucher_no}]: {part_text} (Principal: ₹{principal:,.2f} + Planned Interest: ₹{tot_interest:,.2f} = Total Due: ₹{tot_repayable:,.2f})",
                [('AST-110', tot_repayable)],
                cr_entries,
                voucher_date=str(op_bal_date)
            )
                
            acc_row = run_query("SELECT id, balance FROM accounts WHERE customer_id = ?", (selected_cust_id,))
            if acc_row:
                acc_id, old_bal = acc_row[0]
                new_bal = float(old_bal) + float(final_initial_due)
                run_query("UPDATE accounts SET balance = ? WHERE id = ?", (new_bal, acc_id), fetch=False)
                run_query("INSERT INTO transactions (account_id, type, amount, balance_after, date) VALUES (?, ?, ?, ?, ?)", (acc_id, f"GOLD LOAN DISBURSAL [{loan_no}] (DEBIT)", final_initial_due, new_bal, str(sanction_date)), fetch=False)
            else:
                run_query("INSERT INTO accounts (account_number, account_type, customer_id, balance, created_at) VALUES (?, 'Loan Account', ?, ?, ?)", (f"GL-{selected_cust_id}", selected_cust_id, final_initial_due, str(sanction_date)), fetch=False)
                
            clear_db_cache()
            flash_success(f"🎉 Gold Loan **{loan_no}** sanctioned & disbursed for **{selected_cust_name}**! Voucher: `{voucher_no}` | Total Repayable: **₹{tot_repayable:,.2f}** | Outstanding Opening Balance: **₹{final_initial_due:,.2f}**.")
            st.rerun()

    with tab2:
        st.subheader("💳 Collect Gold Loan Installment / Repayment")
        active_gl_loans = [
            r for r in all_gl_data 
            if r[37] not in ('CLOSED', 'CLOSED_RELEASED') and (float(r[31] or 0) > 0 or float(r[22] or r[16] or 0) > 0)
        ]
        
        if active_gl_loans:
            gl_loan_dict = {}
            for r in active_gl_loans:
                eff_due = float(r[31]) if float(r[31] or 0) > 0 else float(r[22] or r[16] or 0.0)
                label = f"#{r[1]} - {r[3]} (Packet: {r[32]} | Due: ₹{eff_due:,.2f} | Gold: {float(r[12]):.3f}g)"
                gl_loan_dict[label] = r
            sel_gl_label = st.selectbox("1️⃣ Select Active Gold Loan Account", list(gl_loan_dict.keys()), key="gl_rep_sel")
            sel_gl_row = gl_loan_dict[sel_gl_label]
            (gl_id, gl_no, gl_cid, gl_cname, gl_cacc, gl_cphone, gl_sdate, gl_grate, gl_orn, gl_cnt,
             gl_gross, gl_stone, gl_net, gl_pur, gl_mval, gl_ltv, gl_princ, gl_rate, gl_mrate,
             gl_tdays, gl_tmonths, gl_tot_int, gl_tot_rep, gl_inst, gl_p_emi, gl_i_emi, gl_i_due,
             gl_from, gl_to, gl_fdue, gl_ldue, gl_due, gl_pkt, gl_lock, gl_appr, gl_dmode,
             gl_vno, gl_stat, gl_rem, gl_ren_cnt, gl_last_ren, gl_str, gl_city, gl_state,
             gl_pin, gl_img_file, gl_has_photo, gl_op_bal) = sel_gl_row
             
            gl_due = float(gl_due) if float(gl_due or 0) > 0 else float(gl_tot_rep or gl_princ or 0.0)
            already_paid_gl = max(0.0, float(gl_tot_rep or gl_princ) - float(gl_due))
            
            with st.container(border=True):
                st.markdown(f"#### 🪙 Borrower: **{gl_cname}** (Loan: `{gl_no}`, Packet: `{gl_pkt}`, Locker: `{gl_lock}`)")
                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.metric("💵 Principal Loan", f"₹{float(gl_princ):,.2f}")
                sc2.metric("💳 Total Repayable", f"₹{float(gl_tot_rep or gl_princ):,.2f}")
                sc3.metric("🟢 Repaid So Far", f"₹{already_paid_gl:,.2f}")
                sc4.metric("🔴 Outstanding Due", f"₹{float(gl_due):,.2f}")
                st.caption(f"📌 **Pledged Jewels:** {gl_orn} ({float(gl_net):.3f}g net) | **Monthly EMI:** {'₹{:,.2f}'.format(float(gl_inst or 0)) if float(gl_inst or 0) > 0 else '₹0.00'}")

            sched_status_rows = gl_sched_map.get(gl_id, [])
            if sched_status_rows:
                with st.expander("📋 View 12-Month Gold Loan EMI Schedule & Status", expanded=False):
                    df_sched_st = pd.DataFrame(sched_status_rows, columns=["EMI #", "From Date", "To Date", "Due Date", "Principal (₹)", "Interest (₹)", "EMI Amount (₹)", "Paid (₹)", "Status"])
                    st.dataframe(format_df_dates(df_sched_st[["EMI #", "From Date", "To Date", "Due Date", "EMI Amount (₹)", "Paid (₹)", "Status"]]), use_container_width=True, hide_index=True, height=240)

            with st.form(f"gold_loan_repayment_form_{gl_id}"):
                st.markdown("### 2️⃣ Payment Collection Details")
                col_r1, col_r2, col_r3 = st.columns(3)
                pay_date = col_r1.date_input("Payment Date", value=date.today(), format="DD-MM-YYYY", key=f"gl_rep_pdate_{gl_id}")
                default_amt = float(gl_inst) if float(gl_inst or 0) > 0 else (min(float(gl_due), 1000.0) if float(gl_due) > 0 else 500.0)
                amt_paid = col_r2.number_input("Amount Collected (₹)", min_value=1.0, value=min(default_amt, float(gl_due)), step=100.0, key=f"gl_rep_amt_{gl_id}")
                if amt_paid > float(gl_due):
                    col_r2.caption(f"⚠️ *Amount exceeds outstanding balance (₹{float(gl_due):,.2f})*")
                pay_mode = col_r3.selectbox("Payment Mode", ["Cash in Hand (Office Drawer)", "Union Bank of India (UPI / NEFT)"], key=f"gl_rep_mode_{gl_id}")
                
                rep_narration = st.text_input("Narration / Remarks / UTR", value=f"Gold Loan Repayment {gl_cname} ({gl_no} - {gl_pkt})", key=f"gl_rep_narr_{gl_id}")
                
                st.info(f"ℹ️ **Payment Preview:** Paying **₹{amt_paid:,.2f}** will reduce remaining due from **₹{float(gl_due):,.2f}** ➔ **₹{max(0.0, float(gl_due) - amt_paid):,.2f}**.")
                
                if st.form_submit_button("💾 Confirm & Post Gold Loan Repayment", use_container_width=True, type="primary"):
                    rep_voucher = f"RGL{pay_date.strftime('%Y%m%d')}{gl_id:03d}"
                    new_due = max(0.0, round(float(gl_due) - float(amt_paid), 2))
                    new_status = 'CLOSED_RELEASED' if new_due <= 0 else 'ACTIVE'
                    
                    tot_gl_int = max(0.0, round(float(gl_tot_rep or gl_princ) - float(gl_princ), 2))
                    tot_rep_val = float(gl_tot_rep or gl_princ)
                    cur_due_val = float(gl_due)
                    
                    cycle_paid_so_far = max(0.0, round(tot_rep_val - cur_due_val, 2))
                    if tot_rep_val > 0 and tot_gl_int > 0:
                        cycle_int_rec = round(cycle_paid_so_far * (tot_gl_int / tot_rep_val), 2)
                    else:
                        cycle_int_rec = 0.0
                    rem_int_to_rec = max(0.0, round(tot_gl_int - cycle_int_rec, 2))
                    
                    if tot_rep_val > 0 and tot_gl_int > 0:
                        prop_int = round(float(amt_paid) * (tot_gl_int / tot_rep_val), 2)
                        if new_due <= 0:
                            int_portion = rem_int_to_rec
                        else:
                            int_portion = min(prop_int, rem_int_to_rec)
                        princ_portion = round(float(amt_paid) - int_portion, 2)
                    else:
                        int_portion = 0.0
                        princ_portion = float(amt_paid)
                    
                    success, msg = record_gold_loan_repayment(
                        gl_id, gl_cid, gl_cname, gl_cacc, gl_no, gl_pkt, str(pay_date), amt_paid, pay_mode, rep_voucher, rep_narration, new_due, new_status, princ_portion, int_portion
                    )
                    if success:
                        flash_success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
        else:
            st.info("No active gold loans pending repayment.")

    with tab3:
        st.subheader("🔄 Gold / Jewel Loan Renewal & Pledge Rollover")
        all_renewable_gl = [
            r for r in all_gl_data 
            if r[37] not in ('CLOSED', 'CLOSED_RELEASED') and (float(r[31] or 0) > 0 or float(r[22] or r[16] or 0) > 0)
        ]
        
        if all_renewable_gl:
            gl_ren_dict = {}
            for g in all_renewable_gl:
                ren_tag = f" [Cycle #{g[39]}]" if int(g[39] or 0) > 0 else ""
                eff_due = float(g[31]) if float(g[31] or 0) > 0 else float(g[22] or g[16] or 0.0)
                label = f"#{g[1]} - {g[3]} (Packet: {g[32]} | Due: ₹{eff_due:,.2f} | Gold: {float(g[12]):.3f}g{ren_tag})"
                gl_ren_dict[label] = g
                
            sel_gl_ren_key = st.selectbox("1️⃣ Select Active Gold Loan to Renew / Rollover", list(gl_ren_dict.keys()), key="gl_ren_sel")
            sel_gl_data = gl_ren_dict[sel_gl_ren_key]
            (c_gl_id, c_gl_no, c_gl_cid, c_gl_cname, c_gl_cacc, c_gl_cphone, c_gl_sdate, c_gl_grate, c_gl_orn, c_gl_cnt,
             c_gl_gross, c_gl_stone, c_gl_net, c_gl_pur, c_gl_mval, c_gl_ltv, c_gl_princ, c_gl_rate, c_gl_mrate,
             c_gl_tdays, c_gl_tmonths, c_gl_tot_int, c_gl_tot_rep, c_gl_inst, c_gl_p_emi, c_gl_i_emi, c_gl_i_due,
             c_gl_from, c_gl_to, c_gl_fdue, c_gl_ldue, c_gl_due, c_gl_pkt, c_gl_lock, c_gl_appr, c_gl_dmode,
             c_gl_vno, c_gl_stat, c_gl_rem, c_gl_ren_cnt, c_gl_last_ren, c_gl_str, c_gl_city, c_gl_state,
             c_gl_pin, c_gl_img_file, c_gl_has_photo, c_gl_op_bal) = sel_gl_data
             
            c_gl_due = float(c_gl_due) if float(c_gl_due or 0) > 0 else float(c_gl_tot_rep or c_gl_princ or 0.0)
            tot_orig_int = float(c_gl_tot_int or 0.0)
            tot_orig_rep = float(c_gl_tot_rep or (float(c_gl_princ) + tot_orig_int))
            cur_due_val = float(c_gl_due)
            
            cycle_paid_so_far = max(0.0, round(tot_orig_rep - cur_due_val, 2))
            if tot_orig_rep > 0 and tot_orig_int > 0:
                cycle_int_rec = round(cycle_paid_so_far * (tot_orig_int / tot_orig_rep), 2)
            else:
                cycle_int_rec = 0.0
                
            unearned_int_rem = max(0.0, round(tot_orig_int - cycle_int_rec, 2))
            net_princ_rem = max(0.0, round(cur_due_val - unearned_int_rem, 2))
            if net_princ_rem <= 0 and cur_due_val > 0:
                net_princ_rem = cur_due_val
            
            with st.container(border=True):
                st.markdown(f"#### 🪙 Borrower: **{c_gl_cname}** (Loan: `{c_gl_no}`, Packet: `{c_gl_pkt}`, Locker: `{c_gl_lock}`)")
                gc1, gc2, gc3, gc4 = st.columns(4)
                gc1.metric("💵 Carried-Forward Principal", f"₹{net_princ_rem:,.2f}")
                gc2.metric("💳 Current Outstanding Due", f"₹{cur_due_val:,.2f}")
                gc3.metric("🔒 Pledged Net Gold", f"{float(c_gl_net):.3f} g")
                gc4.metric("🔄 Renewal History", f"Cycle #{c_gl_ren_cnt + 1}" if c_gl_ren_cnt > 0 else "Cycle #1 (Initial)")
                st.caption(f"📌 **Ornaments:** {c_gl_orn} | **Sanction Date:** {c_gl_sdate} | **Last Renewed:** {c_gl_last_ren or 'Original Appraisal'}")

            st.markdown("### 2️⃣ Jewel Re-Appraisal & Today's Market Rate")
            col_gr1, col_gr2, col_gr3 = st.columns(3)
            gl_ren_date = col_gr1.date_input("Renewal / Re-Appraisal Date", value=date.today(), format="DD-MM-YYYY", key=f"gl_rnw_date_{c_gl_id}")
            today_gold_rate = col_gr2.number_input("Today's 22K Gold Rate (₹ / gram)", min_value=1000.0, value=float(c_gl_grate or 6500.0), step=50.0, key=f"gl_rnw_rate_{c_gl_id}")
            re_appraiser = col_gr3.text_input("Re-Appraiser Name", value=str(c_gl_appr or "Approved Nidhi Appraiser"), key=f"gl_rnw_appr_{c_gl_id}")
            
            # Dynamic re-appraisal
            updated_market_val = round(float(c_gl_net) * float(today_gold_rate), 2)
            max_eligible_ren = round(updated_market_val * 0.75, 2)
            
            col_vm1, col_vm2 = st.columns(2)
            col_vm1.info(f"💎 **Re-Appraised Market Value:** ₹{updated_market_val:,.2f}")
            col_vm2.success(f"🎯 **Max Eligible Limit (75% LTV):** ₹{max_eligible_ren:,.2f}")

            st.markdown("### 3️⃣ Renewal Terms & New Amortization Schedule")
            col_rp1, col_rp2, col_rp3 = st.columns(3)
            default_ren_gl_princ = float(min(net_princ_rem if net_princ_rem > 0 else cur_due_val, max_eligible_ren))
            renewed_gl_principal = col_rp1.number_input("Renewed Principal Balance (₹)", min_value=0.0, value=default_ren_gl_princ, step=500.0, help="Carried-forward principal balance to renew", key=f"gl_ren_princ_{c_gl_id}")
            if renewed_gl_principal > max_eligible_ren:
                col_rp1.caption(f"⚠️ *Amount exceeds 75% LTV ceiling (₹{max_eligible_ren:,.2f})*")
            new_gl_int_rate = col_rp2.number_input("Annual Interest Rate (%)", min_value=0.0, value=12.0, step=0.5, key=f"gl_ren_rate_{c_gl_id}")
            new_gl_tenure_days = col_rp3.number_input("New Tenure (Days)", min_value=1, value=365, step=10, key=f"gl_ren_tday_{c_gl_id}")

            new_gl_tenure_months = max(1, int(round(new_gl_tenure_days / 30.0)))
            new_gl_planned_interest = round(renewed_gl_principal * (new_gl_int_rate / 100.0) * (new_gl_tenure_days / 365.0), 2)
            new_gl_tot_repayable = round(renewed_gl_principal + new_gl_planned_interest, 2)
            new_gl_p_emi = round(renewed_gl_principal / float(new_gl_tenure_months), 2)
            new_gl_i_emi = round(new_gl_planned_interest / float(new_gl_tenure_months), 2)
            new_gl_installment = round(new_gl_tot_repayable / float(new_gl_tenure_months), 2)
            
            with st.container(border=True):
                st.markdown("#### 📊 Live Gold Loan Renewal Breakdown")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("💵 Renewed Principal", f"₹{renewed_gl_principal:,.2f}")
                m1.metric(f"📈 New Interest ({new_gl_int_rate}%)", f"₹{new_gl_planned_interest:,.2f}")
                m3.metric("💳 Total Due (Repayable)", f"₹{new_gl_tot_repayable:,.2f}")
                m4.metric("📅 New Monthly EMI", f"₹{new_gl_installment:,.2f}")
                st.caption(f"📌 **Monthly Breakdown:** Principal EMI: **₹{new_gl_p_emi:,.2f}** + Interest EMI: **₹{new_gl_i_emi:,.2f}** = Total EMI: **₹{new_gl_installment:,.2f}** per month for {new_gl_tenure_days} days ({new_gl_tenure_months} months).")

            gl_ren_remarks = st.text_input("Renewal Remarks / Notes", value=f"Gold Loan Pledge Rollover & Term Renewal - Cycle #{c_gl_ren_cnt+1}", key=f"gl_ren_rem_{c_gl_id}")

            if st.button("🔄 Confirm & Renew Gold Loan Pledge", use_container_width=True, type="primary", key=f"btn_rnw_gl_{c_gl_id}"):
                if renewed_gl_principal <= 0:
                    st.error("❌ Cannot renew a loan with ₹0.00 balance! The loan is already fully settled.")
                    st.stop()
                    
                gl_ren_voucher = f"RNWGL{gl_ren_date.strftime('%Y%m%d')}{c_gl_id:03d}"

                if new_gl_planned_interest > 0:
                    post_automated_jv(
                        f"Gold Loan Renewal Interest Booking [{gl_ren_voucher}]: {c_gl_no} - {c_gl_cname} (New Term Planned Interest: ₹{new_gl_planned_interest:,.2f})",
                        'AST-110',
                        'LIA-104',
                        new_gl_planned_interest,
                        voucher_date=gl_ren_date
                    )

                ren_schedule = generate_loan_schedule(gl_ren_date, renewed_gl_principal, new_gl_planned_interest, tenure_months=new_gl_tenure_months, loan_type='GOLD')
                ren_loan_from = ren_schedule[0]["from_date"] if ren_schedule else str(gl_ren_date)
                ren_loan_to = ren_schedule[-1]["to_date"] if ren_schedule else str(gl_ren_date)
                ren_first_due = ren_schedule[0]["due_date"] if ren_schedule else str(gl_ren_date)
                ren_last_due = ren_schedule[-1]["due_date"] if ren_schedule else str(gl_ren_date)

                run_query("DELETE FROM loan_emi_schedules WHERE loan_id = ? AND loan_type = 'GOLD' AND status = 'PENDING'", (c_gl_id,), fetch=False)
                batch_insert_loan_schedules('GOLD', c_gl_id, c_gl_no, ren_schedule, gl_ren_date)

                new_gl_ren_cnt = int(c_gl_ren_cnt or 0) + 1
                updated_gl_remarks = f"{c_gl_rem or ''} | [Renewed Cycle #{new_gl_ren_cnt} on {gl_ren_date} (Val: ₹{updated_market_val:,.2f}, P: ₹{renewed_gl_principal:,.2f}, I: ₹{new_gl_planned_interest:,.2f})]".strip(" | ")

                run_query("""
                    UPDATE gold_loans
                    SET gold_rate_per_gram = ?,
                        market_value = ?,
                        principal_amount = ?,
                        interest_rate = ?,
                        interest_rate_monthly = ?,
                        tenure_days = ?,
                        tenure_months = ?,
                        total_interest = ?,
                        total_repayable = ?,
                        installment_amount = ?,
                        monthly_principal_emi = ?,
                        monthly_interest_emi = ?,
                        monthly_interest_due = ?,
                        outstanding_due = ?,
                        sanction_date = ?,
                        loan_from_date = ?,
                        loan_to_date = ?,
                        first_emi_due = ?,
                        last_emi_due = ?,
                        appraiser_name = ?,
                        renewal_count = ?,
                        last_renewal_date = ?,
                        status = 'ACTIVE',
                        remarks = ?
                    WHERE id = ?
                """, (
                    today_gold_rate,
                    updated_market_val,
                    renewed_gl_principal,
                    new_gl_int_rate,
                    round(new_gl_int_rate / 12.0, 2),
                    new_gl_tenure_days,
                    new_gl_tenure_months,
                    new_gl_planned_interest,
                    new_gl_tot_repayable,
                    new_gl_installment,
                    new_gl_p_emi,
                    new_gl_i_emi,
                    new_gl_i_emi,
                    new_gl_tot_repayable,
                    str(gl_ren_date),
                    ren_loan_from,
                    ren_loan_to,
                    ren_first_due,
                    ren_last_due,
                    re_appraiser,
                    new_gl_ren_cnt,
                    str(gl_ren_date),
                    updated_gl_remarks,
                    c_gl_id
                ), fetch=False)

                acc_r = run_query("SELECT id FROM accounts WHERE customer_id = ?", (c_gl_cid,))
                if acc_r:
                    a_id = acc_r[0][0]
                    run_query("UPDATE accounts SET balance = ? WHERE id = ?", (new_gl_tot_repayable, a_id), fetch=False)
                    run_query("INSERT INTO transactions (account_id, type, amount, balance_after, date) VALUES (?, ?, ?, ?, ?)", (a_id, f"GOLD LOAN RENEWAL [{c_gl_no}]", new_gl_tot_repayable, new_gl_tot_repayable, str(gl_ren_date)), fetch=False)

                clear_db_cache()
                flash_success(f"🎉 Gold Loan **#{c_gl_no}** for **{c_gl_cname}** successfully renewed! (Cycle #{new_gl_ren_cnt}) | New Valuation: **₹{updated_market_val:,.2f}** | New Repayable Due: **₹{new_gl_tot_repayable:,.2f}** | Monthly EMI: **₹{new_gl_installment:,.2f}/mo**")
                st.rerun()
        else:
            st.info("ℹ️ No active gold loans pending renewal. (Fully repaid or released loans do not require rollover renewal).")

    with tab4:
        st.subheader("✏️ Edit / Delete Gold Loan & Opening Balance")
        all_edit_gl = all_gl_data
        if all_edit_gl:
            egl_opts = {f"#{r[1]} - {r[3]} (Pkt: {r[32]} | Due: ₹{float(r[31]):,.2f} | Gold: {float(r[12]):.3f}g | Stat: {r[37]})": r for r in all_edit_gl}
            sel_egl_label = st.selectbox("Select Gold Loan to Edit or Manage", list(egl_opts.keys()), key="gl_edit_sel")
            grow = egl_opts[sel_egl_label]
            (sel_egl_id, eg_lno, eg_cid, eg_cname, eg_cacc, eg_cphone, eg_sdate, eg_grate, eg_orn,
             eg_cnt, eg_gross, eg_stone, eg_net, eg_pur, eg_mval, eg_ltv, eg_princ, eg_rate,
             eg_mrate, eg_tdays, eg_tmonths, eg_tot_int, eg_tot_rep, eg_inst, eg_p_emi, eg_i_emi, eg_i_due,
             eg_from, eg_to, eg_fdue, eg_ldue, eg_out_due, eg_pkt, eg_lock, eg_appr, eg_dmode,
             eg_vno, eg_stat, eg_rem, eg_ren_cnt, eg_last_ren, eg_str, eg_city, eg_state,
             eg_pin, eg_img_file, eg_has_photo, eg_op_bal) = grow
             
            try:
                eg_sdate_obj = datetime.strptime(str(eg_sdate)[:10], "%Y-%m-%d").date()
            except Exception:
                eg_sdate_obj = date.today()

            gl_op_bal_res = cached_query("SELECT voucher_date FROM journal_vouchers WHERE (narration LIKE ? OR narration LIKE ?) ORDER BY jv_id ASC LIMIT 1", (f"%[{eg_lno}%", f"%Gold Loan%{eg_lno}%"))
            try:
                gl_op_bal_dt = pd.to_datetime(gl_op_bal_res[0][0]).date() if gl_op_bal_res and gl_op_bal_res[0] and gl_op_bal_res[0][0] else eg_sdate_obj
            except Exception:
                gl_op_bal_dt = eg_sdate_obj
                
            is_closed_gl = (eg_stat in ["CLOSED", "CLOSED_RELEASED"])
                
            with st.container(border=True):
                st.markdown(f"#### 🪙 Borrower: **{eg_cname}** (Acc: `{eg_cacc}` | Packet: `{eg_pkt}` | Renewals: `Cycle #{eg_ren_cnt}`)")
                
                if is_closed_gl:
                    st.warning(f"🔒 **Gold Loan #{eg_lno} is currently CLOSED.** All appraisal details and financial fields are locked from editing to protect finalized loan records.")
                    col_reopen_gl, _ = st.columns([1, 2])
                    if col_reopen_gl.button(f"🔓 Reopen / Reactivate Gold Loan #{eg_lno}", key=f"reopen_gl_{sel_egl_id}", type="secondary"):
                        run_query("UPDATE gold_loans SET status = 'ACTIVE', closure_date = NULL WHERE id = ?", (sel_egl_id,), fetch=False)
                        clear_db_cache()
                        flash_success(f"✅ Gold Loan #{eg_lno} has been reopened to ACTIVE status. Editing fields are now unlocked.")
                        st.rerun()
                
                if eg_has_photo:
                    with st.expander("📸 View / Download Pledged Ornament Photo", expanded=False):
                        _, existing_raw_img = get_cached_gl_photo(sel_egl_id)
                        if existing_raw_img:
                            st.image(existing_raw_img, caption=f"📸 Current Pledged Ornaments ({eg_img_file or 'Jewel Photo'})", width=300)
                            
                            btn_col1, btn_col2 = st.columns(2)
                            btn_col1.download_button(
                                "📥 Download Photo",
                                data=existing_raw_img,
                                file_name=f"Gold_Photo_{eg_lno}.jpg",
                                mime="image/jpeg",
                                use_container_width=True,
                                key=f"dl_gl_img_{sel_egl_id}"
                            )
                            if not is_closed_gl and btn_col2.button("🗑️ Remove Photo", key=f"del_gl_img_{sel_egl_id}", use_container_width=True):
                                run_query("UPDATE gold_loans SET gold_image_file = NULL, gold_image_data = NULL WHERE id = ?", (sel_egl_id,), fetch=False)
                                clear_db_cache()
                                st.success("Gold ornament image cleared.")
                                sensible_rerun = True
                                st.rerun()
                        else:
                            st.info("No gold ornament photo attached to this loan.")
                
                st.markdown("### 1️⃣ Collateral Appraisal & Live Market Valuation")
                col_ea1, col_ea2 = st.columns(2)
                ed_gold_rate = col_ea1.number_input("22K Gold Market Rate (₹ / gram)", min_value=1000.0, value=float(eg_grate or 6500.0), step=50.0, disabled=is_closed_gl, key=f"gl_ed_grate_{sel_egl_id}")
                ed_orn_desc = col_ea2.text_input("Ornaments Description", value=str(eg_orn or ""), disabled=is_closed_gl, key=f"gl_ed_orn_{sel_egl_id}")
                
                col_ew1, col_ew2, col_ew3, col_ew4 = st.columns(4)
                ed_item_cnt = col_ew1.number_input("Item Count", min_value=1, value=int(eg_cnt or 1), step=1, disabled=is_closed_gl, key=f"gl_ed_cnt_{sel_egl_id}")
                ed_gross_wt = col_ew2.number_input("Gross Weight (g)", min_value=0.1, value=float(eg_gross or 10.0), step=0.1, format="%.3f", disabled=is_closed_gl, key=f"gl_ed_gross_{sel_egl_id}")
                ed_stone_ded = col_ew3.number_input("Stone Deduction (g)", min_value=0.0, value=float(eg_stone or 0.0), step=0.05, format="%.3f", disabled=is_closed_gl, key=f"gl_ed_stone_{sel_egl_id}")
                ed_net_wt = max(0.01, round(float(ed_gross_wt) - float(ed_stone_ded), 3))
                col_ew4.metric("Net Gold Weight", f"{ed_net_wt:.3f} g")
                
                ed_market_val = round(ed_net_wt * float(ed_gold_rate), 2)
                ed_max_eligible = round(ed_market_val * 0.75, 2)
                col_ev1, col_ev2 = st.columns(2)
                col_ev1.info(f"💎 **Recomputed Market Value:** ₹{ed_market_val:,.2f}")
                col_ev2.success(f"🎯 **Max Eligible Limit (75% LTV):** ₹{ed_max_eligible:,.2f}")
                
                st.markdown("### 2️⃣ Dynamic Loan Terms & Repayment")
                col_ef1, col_ef2, col_ef3, col_ef4 = st.columns(4)
                ed_princ = col_ef1.number_input("Sanctioned Principal Amount (₹) *", min_value=100.0, value=float(eg_princ or 1000.0), step=1000.0, disabled=is_closed_gl, help="Original loan principal amount sanctioned against pledged ornaments", key=f"gl_ed_princ_{sel_egl_id}")
                ed_op_bal = col_ef2.number_input("Opening Balance (₹) *", min_value=0.0, value=float(eg_op_bal or eg_princ), step=500.0, disabled=is_closed_gl, help="Initial opening ledger balance at loan creation", key=f"gl_ed_opbal_{sel_egl_id}")
                ed_int_rate = col_ef3.number_input("Annual Interest Rate (%) *", min_value=0.0, value=float(eg_rate or 12.0), step=0.5, disabled=is_closed_gl, key=f"gl_ed_rate_{sel_egl_id}")
                ed_tenure_days = col_ef4.number_input("Loan Period / Tenure (Days) *", min_value=1, value=int(eg_tdays or (eg_tmonths * 30 if eg_tmonths else 365)), step=10, disabled=is_closed_gl, key=f"gl_ed_tday_{sel_egl_id}")
                
                ed_tenure_mo = max(1, int(round(ed_tenure_days / 30.0)))
                calc_gl_interest = round(ed_princ * (ed_int_rate / 100.0) * (ed_tenure_days / 365.0), 2)
                calc_gl_repayable = round(ed_princ + calc_gl_interest, 2)
                calc_gl_p_emi = round(ed_princ / float(ed_tenure_mo), 2)
                calc_gl_i_emi = round(calc_gl_interest / float(ed_tenure_mo), 2)
                calc_gl_installment = round(calc_gl_repayable / float(ed_tenure_mo), 2)
                
                with st.container(border=True):
                    st.markdown("#### 📊 Live Updated Loan Breakdown")
                    em1, em2, em3, em4 = st.columns(4)
                    em1.metric("💵 Principal", f"₹{ed_princ:,.2f}")
                    em2.metric(f"📈 Total Interest ({ed_int_rate}%)", f"₹{calc_gl_interest:,.2f}")
                    em3.metric("💳 Total Repayable", f"₹{calc_gl_repayable:,.2f}")
                    em4.metric("📅 Monthly EMI", f"₹{calc_gl_installment:,.2f}")
                    st.caption(f"📌 **Monthly Breakdown:** Principal EMI: **₹{calc_gl_p_emi:,.2f}** + Interest EMI: **₹{calc_gl_i_emi:,.2f}** = Total EMI: **₹{calc_gl_installment:,.2f}** per month for {ed_tenure_days} days ({ed_tenure_mo} months).")
                
                st.markdown("### 3️⃣ Pledged Gold Ornament Photo Upload / Replacement")
                new_gl_photo = st.file_uploader("Upload / Replace Gold Photo (JPG, PNG)", type=["jpg", "jpeg", "png"], disabled=is_closed_gl, key=f"up_gl_photo_{sel_egl_id}")
                
                st.markdown("### 4️⃣ Vault Custody & Loan Management")
                col_vc1, col_vc2, col_vc3 = st.columns(3)
                new_pkt_no = col_vc1.text_input("Safe Vault Packet No *", value=str(eg_pkt or ""), disabled=is_closed_gl, key=f"gl_ed_pkt_{sel_egl_id}")
                new_locker_no = col_vc2.text_input("Locker Number *", value=str(eg_lock or "LOCKER-01"), disabled=is_closed_gl, key=f"gl_ed_lock_{sel_egl_id}")
                new_appr_name = col_vc3.text_input("Certified Appraiser Name", value=str(eg_appr or "Approved Nidhi Appraiser"), disabled=is_closed_gl, key=f"gl_ed_appr_{sel_egl_id}")
                
                col_ad1, col_ad2, col_ad3, col_ad4 = st.columns(4)
                new_gl_lno = col_ad1.text_input("Loan Number *", value=str(eg_lno), disabled=is_closed_gl, key=f"gl_ed_lno_{sel_egl_id}")
                new_gl_sdate = col_ad2.date_input("Sanction Date", value=eg_sdate_obj, format="DD-MM-YYYY", disabled=is_closed_gl, key=f"gl_ed_sdate_{sel_egl_id}")
                new_gl_op_date = col_ad3.date_input("Opening / Disbursal Date (Opening Balance Date)", value=gl_op_bal_dt, format="DD-MM-YYYY", disabled=is_closed_gl, key=f"gl_ed_op_date_{sel_egl_id}")
                new_gl_status = col_ad4.selectbox(
                    "Loan Status",
                    ["ACTIVE", "CLOSED", "CLOSED_RELEASED", "COURT_CASE", "AUCTION_PROCEEDING", "NOT_REMITTING"],
                    index=["ACTIVE", "CLOSED", "CLOSED_RELEASED", "COURT_CASE", "AUCTION_PROCEEDING", "NOT_REMITTING"].index(eg_stat) if eg_stat in ["ACTIVE", "CLOSED", "CLOSED_RELEASED", "COURT_CASE", "AUCTION_PROCEEDING", "NOT_REMITTING"] else 0,
                    disabled=is_closed_gl,
                    key=f"gl_ed_stat_{sel_egl_id}"
                )
                
                col_adm1, col_adm2 = st.columns(2)
                new_gl_dmode = col_adm1.selectbox("Disbursal Mode", ["Union Bank of India (NEFT / UPI)", "Cash in Hand (Office Drawer)"], index=0 if "Union Bank" in str(eg_dmode or "") else 1, disabled=is_closed_gl, key=f"gl_ed_dmode_{sel_egl_id}")
                new_gl_remarks = col_adm2.text_input("Remarks / Condition Notes", value=str(eg_rem or ""), disabled=is_closed_gl, key=f"gl_ed_rem_{sel_egl_id}")
                
                st.markdown("### 5️⃣ Current Outstanding Due Balance")
                col_gldue1, col_gldue2 = st.columns(2)
                recalc_gl_due = col_gldue1.checkbox(f"🔄 Reset Outstanding Due to Total Repayable (₹{calc_gl_repayable:,.2f})", value=(float(eg_out_due or 0) == float(eg_tot_rep or 0)), disabled=is_closed_gl, key=f"gl_recalc_due_{sel_egl_id}")
                if recalc_gl_due:
                    new_gl_out_due = calc_gl_repayable
                    col_gldue2.info(f"Outstanding Due set to **₹{new_gl_out_due:,.2f}**")
                else:
                    new_gl_out_due = col_gldue2.number_input("Outstanding Due Balance (₹) *", min_value=0.0, value=float(eg_out_due or calc_gl_repayable), step=100.0, disabled=is_closed_gl, help="Current unpaid balance owed by the borrower on this gold loan.", key=f"gl_ed_due_{sel_egl_id}")
                    
                ed_gl_sched = generate_loan_schedule(new_gl_sdate, ed_princ, calc_gl_interest, tenure_months=ed_tenure_mo, loan_type='GOLD')
                with st.expander(f"📅 View Updated {len(ed_gl_sched)}-Month EMI Amortization Schedule Preview", expanded=False):
                    df_ed_gl_prev = pd.DataFrame(ed_gl_sched).rename(columns={
                        "emi_number": "EMI NOS", "from_date": "FROM DATE", "to_date": "TO DATE",
                        "due_date": "DUE DATE", "principal_component": "PRINCIPAL (₹)",
                        "interest_component": "INTEREST (₹)", "emi_amount": "EMI AMOUNT (₹)"
                    })[["EMI NOS", "FROM DATE", "TO DATE", "DUE DATE", "PRINCIPAL (₹)", "INTEREST (₹)", "EMI AMOUNT (₹)"]]
                    st.dataframe(format_df_dates(df_ed_gl_prev), use_container_width=True, hide_index=True, height=220)

                if is_closed_gl:
                    st.info("ℹ️ *This gold loan is **CLOSED**. To modify terms and save updates, click the **'🔓 Reopen / Reactivate Gold Loan'** button above.*")
                else:
                    if st.button("💾 Save & Apply Updated Gold Loan Details", type="primary", use_container_width=True, key=f"btn_save_gl_{sel_egl_id}"):
                        u_photo_bytes, u_photo_name = None, None
                        if new_gl_photo:
                            u_photo_name, u_photo_bytes = save_uploaded_file(new_gl_photo)
                            
                        new_gl_op_str = new_gl_op_date.strftime("%Y-%m-%d")
                        success, msg = update_gold_loan_details(
                            sel_egl_id, new_gl_lno, new_gl_sdate, ed_princ, ed_int_rate, ed_tenure_days,
                            new_gl_out_due, new_gl_dmode, ed_gold_rate, ed_orn_desc, ed_item_cnt,
                            ed_gross_wt, ed_stone_ded, new_pkt_no, new_locker_no, new_appr_name,
                            new_gl_status, new_gl_remarks, new_photo_bytes=u_photo_bytes, new_photo_name=u_photo_name,
                            new_op_bal_date=new_gl_op_str,
                            new_op_bal=ed_op_bal
                        )
                        clear_db_cache()
                        if success:
                            flash_success(f"🎉 Gold Loan **#{new_gl_lno}** updated successfully! New Total Repayable: **₹{calc_gl_repayable:,.2f}** | Monthly EMI: **₹{calc_gl_installment:,.2f}/mo**")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to update Gold Loan: {msg}")

            st.write("---")
            with st.expander(f"🚨 Danger Zone: Delete Gold Loan #{eg_lno}", expanded=False):
                st.error(f"⚠️ **Warning:** Permanently deleting Gold Loan **#{eg_lno}** (Packet: `{eg_pkt}`) for **{eg_cname}** will remove this loan sanction, its repayment transactions, schedule rows, and custody record from the database.")
                conf_del_gl = st.checkbox(f"Yes, I confirm I want to permanently delete Gold Loan #{eg_lno} (Borrower: {eg_cname})", key=f"conf_del_gl_{sel_egl_id}")
                if conf_del_gl:
                    if st.button(f"🗑️ Permanently Delete Gold Loan #{eg_lno}", type="primary", use_container_width=True, key=f"btn_del_gl_{sel_egl_id}"):
                        success, msg = delete_gold_loan_entry(sel_egl_id)
                        rem_gl = run_query("SELECT SUM(outstanding_due) FROM gold_loans WHERE customer_id = ?", (eg_cid,))
                        new_acc_bal = float(rem_gl[0][0]) if rem_gl and rem_gl[0][0] is not None else 0.0
                        run_query("UPDATE accounts SET balance = ? WHERE customer_id = ?", (new_acc_bal, eg_cid), fetch=False)
                        
                        clear_db_cache()
                        if success:
                            flash_success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to delete gold loan: {msg}")
        else:
            st.info("No gold loan records found to edit or manage.")

    with tab5:
        st.subheader("🏷️ Gold Safe Vault & Packet Register")
        gl_rows = [
            (r[0], r[1], r[32], r[33], r[3], r[8], float(r[12] or 0), float(r[14] or 0), float(r[16] or 0), float(r[31] or 0), int(r[39] or 0), r[37])
            for r in reversed(all_gl_data)
        ]
        if gl_rows:
            df_gl = pd.DataFrame(gl_rows, columns=["ID", "Loan No", "Packet No", "Locker", "Customer Name", "Ornaments", "Net Wt (g)", "Market Value (₹)", "Principal (₹)", "Outstanding Due (₹)", "Renewal Cycle", "Status"])
            
            tot_wt = df_gl[df_gl["Status"] == "ACTIVE"]["Net Wt (g)"].sum()
            tot_gl_due = df_gl[df_gl["Status"] == "ACTIVE"]["Outstanding Due (₹)"].sum()
            
            vm1, vm2, vm3 = st.columns(3)
            vm1.metric("🔒 Active Gold Weight in Vault", f"{tot_wt:.3f} grams")
            vm2.metric("💰 Active Gold Loan Portfolio", f"₹{tot_gl_due:,.2f}")
            vm3.metric("📦 Total Packets", len(df_gl))
            
            st.dataframe(format_df_dates(df_gl), use_container_width=True, hide_index=True, height=320)
            
            col_x, col_c, col_p = st.columns(3)
            with col_x:
                if st.button("📊 Prepare Vault Register (.xlsx)", key="btn_prep_gl_reg_xl", use_container_width=True):
                    st.session_state.gl_reg_xl_bytes = pdf_generator.create_excel_report("Gold Vault Register", df_gl)
                if "gl_reg_xl_bytes" in st.session_state and st.session_state.gl_reg_xl_bytes:
                    st.download_button("📥 Click to Download (.xlsx)", st.session_state.gl_reg_xl_bytes, "gold_vault_register.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_gl_reg_xl")
            with col_c:
                st.download_button("📥 Download Vault Register (.csv)", df_gl.to_csv(index=False).encode('utf-8'), "gold_vault_register.csv", "text/csv", use_container_width=True, key="dl_gl_reg_csv")
            with col_p:
                if st.button("📄 Prepare Vault Register PDF", key="btn_prep_gl_reg_pdf", use_container_width=True):
                    st.session_state.gl_reg_pdf_bytes = pdf_generator.create_pdf_report("Gold Vault Register", df_gl)
                if "gl_reg_pdf_bytes" in st.session_state and st.session_state.gl_reg_pdf_bytes:
                    st.download_button("📥 Click to Download PDF", st.session_state.gl_reg_pdf_bytes, "gold_vault_register.pdf", "application/pdf", use_container_width=True, key="dl_gl_reg_pdf")
        else:
            st.info("No gold loan records found in safe vault register.")

    with tab6:
        st.subheader("🖨️ Gold Loan Statement & Passbook (Matching VAISAKH.xlsx)")
        if all_gl_data:
            gl_opts = {f"#{r[1]} - {r[3]} (Packet: {r[32]} | Acc: {r[4]})": r for r in all_gl_data}
            sel_gl_pr_label = st.selectbox("Select Gold Loan to View Passbook & Export Statement", list(gl_opts.keys()), key="gl_pawn_sel")
            g = gl_opts[sel_gl_pr_label]
            (sel_gl_pr_id, g_lno, g_cid, g_cname, g_cacc, g_cphone, g_sdate, g_grate, g_orn,
             g_cnt, g_gross, g_stone, g_net, g_pur, g_mval, g_ltv, g_princ, g_rate,
             g_mrate, g_tdays, g_ten_mo, g_tot_int, g_tot_rep, g_inst, g_p_emi, g_i_emi, g_i_due,
             g_from, g_to, g_fdue, g_ldue, g_out_due, g_pkt, g_lock, g_appr, g_dmode,
             g_vno, g_stat, g_rem, g_ren_cnt, g_last_ren, g_str, g_city, g_state,
             g_pin, g_img_file, g_has_photo, g_op_bal) = g
            
            addr_parts = [part for part in [g_str, g_city, g_state, g_pin] if part and str(part).strip()]
            g_caddr = ", ".join(addr_parts) if addr_parts else "Balaramapuram, Trivandrum"
            
            sched_rows = gl_sched_map.get(sel_gl_pr_id, [])
            
            if not sched_rows:
                gen_s = generate_loan_schedule(g_sdate, float(g_princ or 0), float(g_tot_int or 0), tenure_months=int(g_ten_mo or 12), loan_type='GOLD')
                sched_rows = [(s['emi_number'], s['from_date'], s['to_date'], s['due_date'], s['principal_component'], s['interest_component'], s['emi_amount'], 0.0, 'PENDING') for s in gen_s]

            df_sched = pd.DataFrame(sched_rows, columns=["EMI NOS", "FROM DATE", "TO DATE", "DUE DATE", "PRINCIPAL (Rs.)", "INTEREST (Rs.)", "EMI AMOUNT (Rs.)", "PAID (Rs.)", "STATUS"])
            
            loan_status_label = "RENEWED" if int(g_ren_cnt or 0) > 0 else "NEW LOAN"
            g_p_emi_val = float(g_p_emi or (float(g_princ or 0) / float(g_ten_mo or 12)))
            g_i_emi_val = float(g_i_emi or (float(g_tot_int or 0) / float(g_ten_mo or 12)))
            g_tot_emi_val = float(g_inst or (g_p_emi_val + g_i_emi_val))
            
            loan_data_dict = {
                "loan_no": g_lno,
                "party_name": g_cname,
                "customer_name": g_cname,
                "account_no": g_cacc,
                "phone": g_cphone,
                "mobile": g_cphone,
                "address": g_caddr,
                "status": loan_status_label,
                "vault_packet_no": g_pkt,
                "locker_no": g_lock,
                "appraiser_name": g_appr,
                "ornament_details": g_orn,
                "item_count": g_cnt,
                "gross_weight": float(g_gross or 0),
                "stone_deduction": max(0.0, float(g_gross or 0) - float(g_net or 0)),
                "net_weight": float(g_net or 0),
                "gold_rate_per_gram": float(g_grate or 6500),
                "market_value": float(g_mval or 0),
                "loan_amount": float(g_princ or 0),
                "principal_amount": float(g_princ or 0),
                "interest_rate": float(g_rate or 12.0),
                "total_interest": float(g_tot_int or 0),
                "total_amount": float(g_tot_rep or 0),
                "total_repayable": float(g_tot_rep or 0),
                "principal_emi": g_p_emi_val,
                "interest_emi": g_i_emi_val,
                "total_emi": g_tot_emi_val,
                "installment_amount": g_tot_emi_val,
                "outstanding_due": float(g_out_due or 0),
                "loan_date": g_sdate,
                "sanction_date": str(g_sdate),
                "duration": f"{g_tdays} DAYS ({g_ten_mo or 12} Months)" if g_tdays else f"{g_ten_mo or 12} MONTHS",
                "tenure_months": int(g_ten_mo or 12),
                "loan_from": str(g_from) if g_from else str(g_sdate),
                "loan_to": str(g_to) if g_to else (df_sched.iloc[-1]["TO DATE"] if not df_sched.empty else ""),
                "first_emi_due": str(g_fdue) if g_fdue else (df_sched.iloc[0]["DUE DATE"] if not df_sched.empty else ""),
                "last_emi_due": str(g_ldue) if g_ldue else (df_sched.iloc[-1]["DUE DATE"] if not df_sched.empty else ""),
                "renewal_count": int(g_ren_cnt or 0)
            }

            with st.container(border=True):
                st.markdown("### 📖 **GOLD LOAN STATEMENT OF ACCOUNT & PAWN PASSBOOK**")
                st.caption("AARSHA NIDHI LIMITED | 6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram")
                st.divider()
                
                gb1, gb2 = st.columns(2)
                ren_tag = f" (Cycle #{g_ren_cnt})" if int(g_ren_cnt or 0) > 0 else ""
                gb1.markdown(f"**LOAN ACCOUNT NO:** `{g_lno}`  \n**STATUS:** `{loan_status_label}`{ren_tag}  \n**LOAN PARTY NAME:** **{g_cname}**  \n**MEMBER ACC NO:** `{g_cacc}`  \n**ADDRESS:** {g_caddr}  \n**MOBILE NUMBER:** {g_cphone}")
                gb2.markdown(f"**SAFE VAULT PACKET NO:** `{g_pkt}`  \n**LOCKER NO:** `{g_lock}`  \n**PLEDGED ORNAMENTS:** {g_orn} (Items: {g_cnt})  \n**NET GOLD WEIGHT:** **{float(g_net):.3f} g** (Gross: {float(g_gross):.3f}g)  \n**MARKET VALUATION:** ₹{float(g_mval):,.2f} (@ ₹{float(g_grate):,.2f}/g)  \n**APPRAISER:** {g_appr}")
                
                if g_has_photo:
                    with st.expander("📸 View Pledged Gold Ornaments Photo", expanded=False):
                        _, raw_pb_img = get_cached_gl_photo(sel_gl_pr_id)
                        if raw_pb_img:
                            st.image(raw_pb_img, caption=f"📸 Pledged Gold Ornaments for #{g_lno} ({g_pkt})", width=320)
                
                st.divider()
                fb1, fb2, fb3 = st.columns(3)
                fb1.metric("LOAN AMOUNT", f"₹{float(g_princ):,.2f}", f"Principal EMI: ₹{g_p_emi_val:,.2f}")
                fb2.metric(f"INTEREST ({g_rate}%)", f"₹{float(g_tot_int):,.2f}", f"Interest EMI: ₹{g_i_emi_val:,.2f}")
                fb3.metric("TOTAL AMOUNT", f"₹{float(g_tot_rep):,.2f}", f"Total Monthly EMI: ₹{g_tot_emi_val:,.2f}")
                
                db1, db2, db3 = st.columns(3)
                dur_gl_disp = f"{g_tdays} Days ({g_ten_mo or 12} Months)" if g_tdays else f"{g_ten_mo or 12} Months"
                db1.caption(f"🗓️ **Loan Date:** {g_sdate} | **Duration:** {dur_gl_disp}")
                db2.caption(f"📅 **Loan Period:** {g_from or g_sdate} to {g_to}")
                db3.caption(f"⏰ **First Due:** {g_fdue} | **Last Due:** {g_ldue}")

            # Build Gold Loan Repayment Ledger (Debit / Credit transactions)
            gl_rep_txs = gl_rep_map.get(sel_gl_pr_id, [])
            gl_ledger_rows = []
            gl_running_bal = float(g_tot_rep or 0)
            gl_ledger_rows.append({
                "Date": str(g_sdate),
                "Voucher No": str(g_lno),
                "Particulars": f"Gold Loan Disbursal (Principal ₹{float(g_princ):,.2f} + Int ₹{float(g_tot_int):,.2f})",
                "Payment Mode": "Disbursal",
                "Debit (₹)": float(g_tot_rep or 0),
                "Credit (₹)": 0.0,
                "Balance (₹)": gl_running_bal
            })
            if gl_rep_txs:
                for rx in gl_rep_txs:
                    p_date, v_no, amt, mode, narr = rx
                    c_amt = float(amt or 0)
                    gl_running_bal = round(gl_running_bal - c_amt, 2)
                    gl_ledger_rows.append({
                        "Date": str(p_date),
                        "Voucher No": str(v_no or ""),
                        "Particulars": str(narr or "Gold Loan Repayment"),
                        "Payment Mode": str(mode or "Cash"),
                        "Debit (₹)": 0.0,
                        "Credit (₹)": c_amt,
                        "Balance (₹)": gl_running_bal
                    })
            df_gl_ledger = pd.DataFrame(gl_ledger_rows)

            st.markdown("#### 📜 **GOLD LOAN REPAYMENT LEDGER & STATEMENT (DEBIT / CREDIT)**")
            st.dataframe(format_df_dates(df_gl_ledger), use_container_width=True, hide_index=True, height=260)

            st.markdown("#### 📅 **12-MONTH EMI AMORTIZATION TABLE**")
            st.dataframe(format_df_dates(df_sched), use_container_width=True, hide_index=True, height=260)

            exp_col1, exp_col2, exp_col3 = st.columns(3)
            with exp_col1:
                if st.button("📊 Prepare Passbook (.xlsx)", key=f"btn_prep_gl_xl_{sel_gl_pr_id}", use_container_width=True):
                    st.session_state[f"gl_xl_bytes_{sel_gl_pr_id}"] = pdf_generator.create_gold_loan_passbook_excel(loan_data_dict, df_sched, df_gl_ledger)
                if f"gl_xl_bytes_{sel_gl_pr_id}" in st.session_state:
                    st.download_button(
                        "📥 Click to Download Passbook (.xlsx)",
                        data=st.session_state[f"gl_xl_bytes_{sel_gl_pr_id}"],
                        file_name=f"Gold_Loan_Passbook_{g_lno}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key=f"gl_tab5_xl_{sel_gl_pr_id}"
                    )
            with exp_col2:
                if st.button("📄 Prepare Passbook PDF", key=f"btn_prep_gl_pdf_{sel_gl_pr_id}", use_container_width=True):
                    st.session_state[f"gl_pdf_bytes_{sel_gl_pr_id}"] = pdf_generator.create_gold_loan_passbook_pdf(loan_data_dict, df_sched, df_gl_ledger)
                if f"gl_pdf_bytes_{sel_gl_pr_id}" in st.session_state:
                    st.download_button(
                        "📥 Click to Download Passbook PDF",
                        data=st.session_state[f"gl_pdf_bytes_{sel_gl_pr_id}"],
                        file_name=f"Gold_Loan_Passbook_{g_lno}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"gl_tab5_pdf_{sel_gl_pr_id}"
                    )
            with exp_col3:
                if st.button("📑 Prepare Gold Loan Agreement PDF", key=f"btn_prep_gl_agree_{sel_gl_pr_id}", use_container_width=True):
                    st.session_state[f"gl_agree_bytes_{sel_gl_pr_id}"] = pdf_generator.create_gold_loan_agreement_pdf(loan_data_dict, df_sched)
                if f"gl_agree_bytes_{sel_gl_pr_id}" in st.session_state:
                    st.download_button(
                        "📥 Click to Download Agreement PDF",
                        data=st.session_state[f"gl_agree_bytes_{sel_gl_pr_id}"],
                        file_name=f"Gold_Loan_Agreement_{g_lno}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"gl_tab5_agree_{sel_gl_pr_id}"
                    )
        else:
            st.info("No gold loan records found to view statement or passbook.")


def render_sb_accounts():
    st.title("💰 Savings Bank (SB) Management")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["➕ Open SB Account & Opening Balance", "💳 Transact", "📖 SB Account Passbook", "📋 View Accounts", "✏️ Edit / Delete SB Account & Opening Balance"])
    
    with tab1:
        customers = cached_query("""
            SELECT c.id, c.name, COALESCE(c.account_no, '') 
            FROM customers c 
            ORDER BY c.name ASC, c.id ASC
        """)
        if customers:
            cust_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers}
            col_sb1, col_sb2 = st.columns(2)
            with col_sb1:
                selected_cust = st.selectbox("Select Customer Name", list(cust_dict.keys()), key="sb_open_cust")
                cust_id = cust_dict[selected_cust]
                init_bal = st.number_input("Opening Balance (₹)", min_value=0.0, value=500.0, step=100.0, key="sb_open_bal")
                sb_int_rate = st.number_input("Interest Rate (% p.a.)", min_value=0.0, max_value=20.0, value=3.5, step=0.25, key="sb_open_rate")
            with col_sb2:
                sb_open_date = st.date_input("A/c Opening Date", value=date.today(), format="DD-MM-YYYY", key="sb_open_date_input")
                sb_op_bal_date = st.date_input("Opening Balance Date", value=date.today(), format="DD-MM-YYYY", key="sb_op_bal_date_input")
            
            asset_accounts = cached_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset'")
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
            
            if st.button("Create SB Account", use_container_width=True, type="primary"):
                op_date_str = sb_open_date.strftime("%Y-%m-%d")
                op_bal_date_str = sb_op_bal_date.strftime("%Y-%m-%d")
                acc_no = f"SB{datetime.now(IST).strftime('%Y%m%d%H%M%S')}"
                run_query("INSERT INTO sb_accounts (account_no, customer_id, balance, opening_balance, interest_rate, created_at) VALUES (?, ?, ?, ?, ?, ?)", 
                          (acc_no, cust_id, init_bal, init_bal, sb_int_rate, op_date_str), fetch=False)
                
                if init_bal > 0:
                    run_query("INSERT INTO transactions (tx_id, account_no, type, amount, mode, narration, date) VALUES (?, ?, 'CREDIT', ?, ?, 'Opening Balance Deposit', ?)",
                              (f"TX{datetime.now(IST).strftime('%M%S%f')}", acc_no, init_bal, mode, op_bal_date_str), fetch=False)
                    
                    jv_result = post_automated_jv(f"SB Opening Balance - Account {acc_no}", chosen_asset_code, "LIA-101", init_bal, voucher_date=op_bal_date_str)
                    
                    if jv_result:
                        new_asset_balance = get_account_balance_from_jv(chosen_asset_code)
                        today_code = op_bal_date_str.replace("-", "")
                        today_time = f"{op_bal_date_str} {datetime.now(IST).strftime('%H:%M')}"
                        
                        if chosen_asset_code == 'AST-101':
                            voucher_no = generate_cash_voucher_no()
                            run_query("""
                                INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                                VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?)
                            """, (op_bal_date_str, voucher_no, f"SB Opening Deposit: {acc_no}", init_bal, new_asset_balance, chosen_asset_code, f"SB Opening Balance - {acc_no}", today_time), fetch=False)
                        elif chosen_asset_code in ['AST-102', 'AST-103']:
                            bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
                            voucher_no = generate_bank_voucher_no()
                            run_query("""
                                INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                                VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
                            """, (op_bal_date_str, voucher_no, f"SB Opening Deposit: {acc_no}", init_bal, new_asset_balance, bank_name, chosen_asset_code, f"SB Opening Balance - {acc_no}", today_time), fetch=False)

                clear_db_cache()
                flash_success(f"🎉 SB Account created successfully on {op_date_str}! Account No: **{acc_no}** (Opening balance recorded on {op_bal_date_str})")
                st.rerun()
        else:
            st.warning("Please register a customer first.")

    with tab2:
        st.subheader("Process Deposit / Withdrawal")
        sb_accounts = cached_query("""
            SELECT s.account_no, c.name, s.balance 
            FROM sb_accounts s JOIN customers c ON s.customer_id = c.id
            ORDER BY c.name ASC, s.account_no ASC
        """)
        if sb_accounts:
            sb_dict = {f"👤 {a[1]} | A/c No: {a[0]} (Balance: ₹{a[2]:,.2f})": a for a in sb_accounts}
            col_tx1, col_tx2 = st.columns(2)
            with col_tx1:
                acc_choice_label = st.selectbox("Select Customer & SB Account", list(sb_dict.keys()), key="sb_tx_select")
                selected_acc = sb_dict[acc_choice_label]
                acc_choice = selected_acc[0]
                cust_name = selected_acc[1]
                curr_balance = float(selected_acc[2] or 0.0)
                tx_type = st.selectbox("Transaction Type", ["DEPOSIT", "WITHDRAWAL"], key="sb_tx_type")
            with col_tx2:
                sb_tx_date = st.date_input("Transaction Date", value=date.today(), format="DD-MM-YYYY", key="sb_tx_date_input")
                amount = st.number_input("Amount (₹)", min_value=1.0, value=500.0, step=100.0, key="sb_tx_amt")
            
            st.info(f"👤 **Selected Customer:** **{cust_name}** &nbsp;|&nbsp; 💳 **SB A/c No:** `{acc_choice}` &nbsp;|&nbsp; 💰 **Current Balance:** **₹{curr_balance:,.2f}**")
            
            asset_accounts = cached_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset' AND account_code IN ('AST-101', 'AST-102', 'AST-103')")
            if not asset_accounts:
                asset_accounts = cached_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset'")
            
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
            
            narration = st.text_input("Narration / Remarks", value="Counter transaction", key="sb_tx_narr")
            
            if st.button("Execute Transaction", use_container_width=True, type="primary"):
                if tx_type == "WITHDRAWAL" and amount > curr_balance:
                    st.error(f"❌ Insufficient SB balance for {cust_name}! Available: ₹{curr_balance:,.2f}, Requested Withdrawal: ₹{amount:,.2f}")
                    st.stop()
                    
                from database import record_sb_transaction
                tx_date_str = sb_tx_date.strftime("%Y-%m-%d")
                success, res_val = record_sb_transaction(acc_choice, tx_type, amount, pay_mode, chosen_asset_code, narration, tx_date=tx_date_str)
                if success:
                    clear_db_cache()
                    flash_success(f"✅ {tx_type.capitalize()} of ₹{amount:,.2f} for **{cust_name}** (A/c: `{acc_choice}`) on {tx_date_str} successful! New Balance: ₹{res_val:,.2f}")
                    st.rerun()
                else:
                    st.error(f"❌ Transaction failed: {res_val}")
        else:
            st.info("No active SB accounts found.")

    with tab3:
        st.subheader("📖 Savings Bank (SB) Account Passbook & Statement")
        all_sb_pb = cached_query("""
            SELECT s.account_no, c.name, s.balance, s.interest_rate, s.created_at, c.phone, 
                   c.street, c.city, c.state, c.pincode, c.id as cust_id
            FROM sb_accounts s 
            JOIN customers c ON s.customer_id = c.id
            ORDER BY c.name ASC, s.account_no ASC
        """)
        if all_sb_pb:
            sb_pb_dict = {f"👤 {r[1]} | A/c: {r[0]} (Bal: ₹{r[2]:,.2f})": r for r in all_sb_pb}
            sel_pb_label = st.selectbox("Select Customer & SB Account", list(sb_pb_dict.keys()), key="sb_pb_select_acc")
            sel_sb = sb_pb_dict[sel_pb_label]
            pb_acc_no, pb_cust_name, pb_balance, pb_rate, pb_created, pb_phone, pb_street, pb_city, pb_state, pb_pincode, pb_cust_id = sel_sb

            pb_addr_parts = [p.strip() for p in [pb_street, pb_city, pb_state] if p and str(p).strip()]
            pb_address = ", ".join(pb_addr_parts)
            if pb_pincode and str(pb_pincode).strip():
                pb_address = f"{pb_address} - {pb_pincode}" if pb_address else str(pb_pincode)
            if not pb_address:
                pb_address = "Balaramapuram, Trivandrum"

            # Fetch transaction history
            tx_data = run_query("""
                SELECT date, tx_id, narration, mode, type, amount
                FROM transactions
                WHERE account_no = ?
                ORDER BY date ASC, id ASC
            """, (pb_acc_no,))

            # Build ledger & calculate running balances
            ledger_rows = []
            running_bal = 0.0
            tot_deposits = 0.0
            tot_withdrawals = 0.0
            op_balance = 0.0

            if tx_data:
                for tx in tx_data:
                    t_date, t_id, t_narr, t_mode, t_type, t_amt = tx[:6]
                    t_amt = float(t_amt or 0.0)
                    t_type_str = str(t_type or "").upper()
                    is_opening = "opening" in str(t_narr or "").lower()

                    if t_type_str in ["CREDIT", "DEPOSIT"]:
                        dr = 0.0
                        cr = t_amt
                        running_bal = round(running_bal + t_amt, 2)
                        if is_opening:
                            op_balance = t_amt
                        else:
                            tot_deposits = round(tot_deposits + t_amt, 2)
                    else: # DEBIT / WITHDRAWAL
                        dr = t_amt
                        cr = 0.0
                        running_bal = round(running_bal - t_amt, 2)
                        tot_withdrawals = round(tot_withdrawals + t_amt, 2)

                    ledger_rows.append({
                        "Date": str(t_date),
                        "Tx ID": str(t_id or "-"),
                        "Particulars": str(t_narr or "-"),
                        "Mode": str(t_mode or "CASH"),
                        "Debit (₹)": dr,
                        "Credit (₹)": cr,
                        "Balance (₹)": running_bal
                    })
            else:
                # If no transactions in DB, show opening balance row
                op_balance = float(pb_balance or 0.0)
                running_bal = op_balance
                ledger_rows.append({
                    "Date": str(pb_created or date.today()),
                    "Tx ID": "OP-BAL",
                    "Particulars": "Opening Balance Deposit",
                    "Mode": "CASH",
                    "Debit (₹)": 0.0,
                    "Credit (₹)": op_balance,
                    "Balance (₹)": op_balance
                })

            df_tx_ledger = pd.DataFrame(ledger_rows)

            # Prepare data dict for export functions
            sb_data_dict = {
                "acc_no": pb_acc_no,
                "cust_name": pb_cust_name,
                "phone": pb_phone or "N/A",
                "created_at": str(pb_created or date.today()),
                "rate": float(pb_rate or 3.5),
                "balance": float(pb_balance or running_bal),
                "opening_balance": op_balance,
                "total_deposits": tot_deposits,
                "total_withdrawals": tot_withdrawals,
                "street": pb_street or "",
                "city": pb_city or "Balaramapuram",
                "state": pb_state or "Kerala",
                "pincode": pb_pincode or "",
                "address": pb_address
            }

            # Summary Cards
            st.markdown(f"""
            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 16px; font-weight: bold; color: #1e293b;">👤 {pb_cust_name} &nbsp;|&nbsp; 💳 A/c No: <code style="color: #0369a1;">{pb_acc_no}</code></span>
                    <span style="background-color: #e0f2fe; color: #0369a1; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;">Savings Bank (SB)</span>
                </div>
                <div style="color: #64748b; font-size: 13px;">
                    📞 <b>Contact:</b> {pb_phone or 'N/A'} &nbsp;|&nbsp; 📅 <b>Opened:</b> {pb_created} &nbsp;|&nbsp; 📈 <b>Interest Rate:</b> {pb_rate}% p.a. &nbsp;|&nbsp; 🏠 <b>Address:</b> {pb_address}
                </div>
            </div>
            """, unsafe_allow_html=True)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 Opening Balance", f"₹{op_balance:,.2f}")
            m2.metric("📥 Total Deposits", f"₹{tot_deposits:,.2f}")
            m3.metric("📤 Total Withdrawals", f"₹{tot_withdrawals:,.2f}")
            m4.metric("💳 Available Balance", f"₹{float(pb_balance or running_bal):,.2f}")

            st.markdown("#### 📜 **TRANSACTION HISTORY & PASSBOOK ENTRIES**")
            st.dataframe(format_df_dates(df_tx_ledger), use_container_width=True, hide_index=True, height=280)

            # Export actions
            exp_col1, exp_col2, exp_col3 = st.columns(3)
            with exp_col1:
                if st.button("📊 Prepare Passbook (.xlsx)", key=f"btn_prep_sb_xl_{pb_acc_no}", use_container_width=True):
                    st.session_state[f"sb_xl_bytes_{pb_acc_no}"] = pdf_generator.create_sb_passbook_excel(sb_data_dict, df_tx_ledger)
                if f"sb_xl_bytes_{pb_acc_no}" in st.session_state:
                    st.download_button(
                        "📥 Click to Download Passbook (.xlsx)",
                        data=st.session_state[f"sb_xl_bytes_{pb_acc_no}"],
                        file_name=f"SB_Passbook_{pb_acc_no}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key=f"sb_tab_xl_dl_{pb_acc_no}"
                    )
            with exp_col2:
                if st.button("📄 Prepare Passbook PDF", key=f"btn_prep_sb_pdf_{pb_acc_no}", use_container_width=True):
                    st.session_state[f"sb_pdf_bytes_{pb_acc_no}"] = pdf_generator.create_sb_passbook_pdf(sb_data_dict, df_tx_ledger)
                if f"sb_pdf_bytes_{pb_acc_no}" in st.session_state:
                    st.download_button(
                        "📥 Click to Download Passbook PDF",
                        data=st.session_state[f"sb_pdf_bytes_{pb_acc_no}"],
                        file_name=f"SB_Passbook_{pb_acc_no}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"sb_tab_pdf_dl_{pb_acc_no}"
                    )
            with exp_col3:
                csv_bytes = df_tx_ledger.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download Statement CSV",
                    data=csv_bytes,
                    file_name=f"SB_Statement_{pb_acc_no}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key=f"sb_tab_csv_dl_{pb_acc_no}"
                )
        else:
            st.info("No active SB accounts found to generate passbook.")

    with tab4:
        accounts = cached_query("""
            SELECT s.account_no, c.name, s.balance, s.interest_rate, s.created_at 
            FROM sb_accounts s JOIN customers c ON s.customer_id = c.id
            ORDER BY s.account_no DESC
        """)
        if accounts:
            df_sb = pd.DataFrame(accounts, columns=["Account No", "Customer Name", "Balance (₹)", "Interest Rate (%)", "Created"])
            df_sb_formatted = format_df_dates(df_sb)
            st.dataframe(df_sb_formatted, use_container_width=True)
            
            # Key SB Metrics
            m1, m2, m3 = st.columns(3)
            tot_sb_dep = sum(row[2] for row in accounts)
            avg_sb_bal = tot_sb_dep / len(accounts) if accounts else 0
            m1.metric("👥 Total SB Accounts", len(accounts))
            m2.metric("💰 Total SB Deposits", f"₹{tot_sb_dep:,.2f}")
            m3.metric("📊 Average SB Balance", f"₹{avg_sb_bal:,.2f}")
            
            col_csv, col_pdf = st.columns(2)
            col_csv.download_button("📥 Download CSV Report", df_sb_formatted.to_csv(index=False).encode('utf-8'), "sb_accounts_report.csv", "text/csv", use_container_width=True)
            col_pdf.download_button("📥 Download PDF Report", pdf_generator.create_pdf_report("SB Accounts Report", df_sb_formatted), "sb_accounts_report.pdf", "application/pdf", use_container_width=True)
        else:
            st.info("No active SB accounts found.")

    with tab5:
        st.subheader("✏️ Edit & Correct Savings Bank (SB) Account & Opening Balance")
        all_sb_edit = cached_query("""
            SELECT s.account_no, c.name, s.balance, s.interest_rate, s.created_at, s.customer_id,
                   COALESCE(s.opening_balance, s.balance) as opening_balance
            FROM sb_accounts s 
            JOIN customers c ON s.customer_id = c.id
            ORDER BY s.account_no DESC
        """)
        if all_sb_edit:
            sb_edit_dict = {f"👤 {r[1]} | A/c: {r[0]} (Balance: ₹{r[2]:,.2f} | Opened: {r[4]})": r for r in all_sb_edit}
            selected_sb_label = st.selectbox("Select SB Account to Edit", list(sb_edit_dict.keys()), key="sb_edit_select")
            curr_sb = sb_edit_dict[selected_sb_label]
            c_acc_no, c_name, c_bal, c_rate, c_created, c_cust_id, c_op_bal = curr_sb
            
            customers_all = cached_query("""
                SELECT c.id, c.name, COALESCE(c.account_no, '') 
                FROM customers c 
                ORDER BY c.name ASC, c.id ASC
            """)
            cust_all_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers_all}
            cust_idx = list(cust_all_dict.values()).index(c_cust_id) if c_cust_id in cust_all_dict.values() else 0
            
            try:
                c_created_dt = pd.to_datetime(c_created).date() if c_created else date.today()
            except Exception:
                c_created_dt = date.today()

            sb_op_bal_res = cached_query("SELECT date FROM transactions WHERE account_no = ? AND (narration LIKE ? OR narration LIKE ?) ORDER BY id ASC LIMIT 1", (c_acc_no, "%Opening%", "%Deposit%"))
            try:
                sb_op_bal_dt = pd.to_datetime(sb_op_bal_res[0][0]).date() if sb_op_bal_res and len(sb_op_bal_res) > 0 and len(sb_op_bal_res[0]) > 0 and sb_op_bal_res[0][0] else c_created_dt
            except Exception:
                sb_op_bal_dt = c_created_dt
            
            st.markdown("---")
            col_sb_e1, col_sb_e2 = st.columns(2)
            with col_sb_e1:
                edit_sb_acc_no = st.text_input("SB Account Number", value=str(c_acc_no), key=f"edit_sb_acc_{c_acc_no}")
                edit_sb_cust_label = st.selectbox("Assigned Customer", list(cust_all_dict.keys()), index=cust_idx, key=f"edit_sb_cust_{c_acc_no}")
                edit_sb_cust_id = cust_all_dict[edit_sb_cust_label]
                edit_sb_op_bal = st.number_input("Opening Balance (₹)", min_value=0.0, value=float(c_op_bal or 0.0), step=100.0, key=f"edit_sb_opbal_{c_acc_no}", help="Initial ledger opening balance when the SB account was created.")
                edit_sb_bal = st.number_input("Current SB Balance (₹)", min_value=0.0, value=float(c_bal or 0.0), step=100.0, key=f"edit_sb_bal_{c_acc_no}", help="Current available balance in this SB account.")
            with col_sb_e2:
                edit_sb_rate = st.number_input("Interest Rate (% p.a.)", min_value=0.0, max_value=20.0, value=float(c_rate or 3.5), step=0.25, key=f"edit_sb_rate_{c_acc_no}")
                edit_sb_created = st.date_input("A/c Opening Date", value=c_created_dt, format="DD-MM-YYYY", key=f"edit_sb_created_{c_acc_no}")
                edit_sb_op_date = st.date_input("Opening Balance Date", value=sb_op_bal_dt, format="DD-MM-YYYY", key=f"edit_sb_op_date_{c_acc_no}")
                
                edit_asset_accounts = cached_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset' AND account_code IN ('AST-101', 'AST-102', 'AST-103')")
                if not edit_asset_accounts:
                    edit_asset_accounts = cached_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset'")
                edit_asset_dict = {f"{a[0]} - {a[1]}": a[0] for a in edit_asset_accounts} if edit_asset_accounts else {}
                
                existing_asset_idx = 0
                if edit_asset_dict:
                    asset_codes_list = list(edit_asset_dict.values())
                    if "AST-102" in asset_codes_list:
                        existing_asset_idx = asset_codes_list.index("AST-102")
                
                edit_chosen_asset_label = st.selectbox(
                    "Funding / Settlement Account",
                    list(edit_asset_dict.keys()),
                    index=existing_asset_idx,
                    key=f"edit_sb_asset_{c_acc_no}"
                )
                edit_chosen_asset = edit_asset_dict[edit_chosen_asset_label] if edit_asset_dict else "AST-102"
            
            st.markdown("<br>", unsafe_allow_html=True)
            btn_sb1, btn_sb2 = st.columns([3, 1])
            with btn_sb1:
                if st.button("💾 Save & Update SB Account Details", key=f"btn_save_sb_{c_acc_no}", type="primary", use_container_width=True):
                    edit_created_str = edit_sb_created.strftime("%Y-%m-%d")
                    edit_op_bal_str = edit_sb_op_date.strftime("%Y-%m-%d")
                    success, msg = update_sb_account_details(
                        c_acc_no, edit_sb_acc_no, edit_sb_cust_id, edit_sb_bal, edit_sb_rate, edit_created_str, edit_chosen_asset, new_op_bal_date=edit_op_bal_str, new_op_bal=edit_sb_op_bal
                    )
                    clear_db_cache()
                    if success:
                        flash_success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to update SB Account: {msg}")
            
            with btn_sb2:
                with st.popover("🗑️ Delete SB Account"):
                    st.error(f"⚠️ Are you sure you want to permanently delete SB Account `{c_acc_no}`?")
                    st.caption("This will delete the account and its transaction history.")
                    if st.button("Confirm Delete Permanently", key=f"btn_del_sb_{c_acc_no}", type="primary", use_container_width=True):
                        success, msg = delete_sb_account_entry(c_acc_no)
                        clear_db_cache()
                        if success:
                            flash_success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to delete SB Account: {msg}")
        else:
            st.info("No SB accounts available to edit.")

def render_fixed_deposits():
    st.title("📈 Fixed Deposits Management")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Open FD", "Active FDs", "Print Certificate / Ledger", "Close FD", "✏️ Edit / Update FD"])
    
    with tab1:
        customers = cached_query("""
            SELECT c.id, c.name, c.street, c.city, c.state, c.pincode 
            FROM customers c 
            ORDER BY c.name ASC, c.id ASC
        """)
        if customers:
            cust_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers}
            next_fd_res = cached_query("SELECT COALESCE(MAX(fd_id), 0) + 1 FROM fixed_deposits")
            next_fd_id = next_fd_res[0][0] if next_fd_res and next_fd_res[0] else 1

            col_fd_id1, col_fd_id2 = st.columns(2)
            with col_fd_id1:
                custom_fd_no = st.text_input("FDR No / FD Account Number", value=f"FD-{next_fd_id:05d}", key="open_fd_no", help="Enter FDR Certificate No or Account No, e.g., 01540001 or FD-00001")
            with col_fd_id2:
                custom_fd_id = st.number_input("Numeric FD ID", min_value=1, value=int(next_fd_id), step=1, key="open_fd_id", help="Internal unique ID for this Fixed Deposit")

            col_fd1, col_fd2 = st.columns(2)
            with col_fd1:
                selected_cust = st.selectbox("Select Customer Name for FD", list(cust_dict.keys()), key="fd_cust")
                principal = st.number_input("Principal Amount (Contracted) (₹)", min_value=100.0, value=10000.0, step=500.0, key="fd_prin")
                opening_balance = st.number_input("Opening Balance (₹)", min_value=0.0, value=float(principal), step=500.0, key="fd_open_bal", help="Initial opening ledger balance at account creation (defaults to Principal Amount).")
                
                tenure_mode = st.radio("Tenure Unit", ["📅 Days", "🗓️ Months"], horizontal=True, key="fd_tenure_mode")
                if "Days" in tenure_mode:
                    tenure_days = st.number_input("Tenure (Days)", min_value=1, max_value=3650, value=365, step=10, key="fd_tenure_days", help="Total deposit duration in days, e.g. 100 days, 365 days, 400 days, 730 days")
                    tenure = max(1, int(round(tenure_days / 30.0)))
                    st.caption(f"🗓️ Equivalent Tenure: ~**{tenure} Months** ({tenure_days} Days)")
                else:
                    tenure = st.number_input("Tenure (Months)", min_value=1, max_value=360, value=12, step=1, key="fd_tenure_months", help="Deposit duration in months")
                    tenure_days = int(tenure * 30)
                    st.caption(f"📅 Equivalent Tenure: ~**{tenure_days} Days** ({tenure} Months)")
            with col_fd2:
                fd_open_date = st.date_input("A/c Opening Date", value=date.today(), format="DD-MM-YYYY", key="fd_open_date_input")
                fd_op_bal_date = st.date_input("Opening Balance Date", value=date.today(), format="DD-MM-YYYY", key="fd_op_bal_date_input")
                interest_rate = st.number_input("Interest Rate (% p.a.)", value=6.5, step=0.25, key="fd_rate")
                nominee = st.text_input("Nominee Name", key="fd_nom")
            
            asset_accounts = cached_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset' AND account_code IN ('AST-101', 'AST-102', 'AST-103')")
            if not asset_accounts:
                asset_accounts = cached_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset'")
            
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
            
            if "Days" in tenure_mode:
                interest_calc = principal * interest_rate * (tenure_days / 365.0) / 100.0
            else:
                interest_calc = principal * interest_rate * (tenure / 12.0) / 100.0
            maturity_amount = round(principal + interest_calc, 2)
            mat_date_val = fd_open_date + timedelta(days=int(tenure_days))
            mat_date_str = mat_date_val.strftime("%d-%m-%Y")
            mat_db_str = mat_date_val.strftime("%Y-%m-%d")
            
            st.info(f"Estimated Maturity Amount: **₹{maturity_amount:,.2f}** (Interest: ₹{interest_calc:,.2f}) | Maturity Date: **{mat_date_str}** ({tenure_days} Days / ~{tenure}M)")
            
            if st.button("Open FD Account", use_container_width=True, type="primary"):
                open_date_str = fd_open_date.strftime("%Y-%m-%d")
                op_bal_date_str = fd_op_bal_date.strftime("%Y-%m-%d")
                success, msg = create_or_link_fd_opening(
                    cust_id=cust_dict[selected_cust],
                    principal=principal,
                    open_date=open_date_str,
                    tenure_months=tenure,
                    interest_rate=interest_rate,
                    nominee=nominee,
                    payment_mode=payment_mode,
                    chosen_asset_code=chosen_asset_code,
                    op_bal_date=op_bal_date_str,
                    custom_fd_no=custom_fd_no,
                    custom_fd_id=custom_fd_id,
                    tenure_days=tenure_days,
                    maturity_date=mat_db_str
                )
                clear_db_cache()
                if success:
                    flash_success(f"🎉 {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ Failed to open FD: {msg}")
        else:
            st.warning("Register a customer first.")

    with tab2:
        fds = cached_query("""
            SELECT f.fd_id, COALESCE(f.fd_no, 'FD-' || LPAD(CAST(f.fd_id AS TEXT), 5, '0')) as fd_no,
                   c.name, f.principal, COALESCE(f.tenure_days, f.tenure_months * 30) as tenure_days,
                   f.tenure_months, f.interest_rate, f.maturity_amount, f.status, f.created_at, f.payment_mode
            FROM fixed_deposits f JOIN customers c ON f.customer_id = c.id
            WHERE f.status = 'ACTIVE'
            ORDER BY f.fd_id DESC
        """)
        if fds:
            formatted_fds = []
            for r in fds:
                t_display = f"{r[4]} Days ({r[5]}M)" if r[4] else f"{r[5]} Months"
                formatted_fds.append((r[0], r[1], r[2], r[3], t_display, r[6], r[7], r[8], r[9], r[10]))
            df_fds = pd.DataFrame(formatted_fds, columns=["FD ID", "FDR No / A/c No", "Customer", "Principal (₹)", "Tenure", "Rate (%)", "Maturity (₹)", "Status", "Opened Date", "Payment Mode"])
            df_fds_formatted = format_df_dates(df_fds)
            st.dataframe(df_fds_formatted, use_container_width=True)
        else:
            st.info("No active fixed deposits found.")

    with tab3:
        st.subheader("🖨️ Printable FD Certificate & Ledger")
        all_fds = cached_query("""
            SELECT f.fd_id, c.name, c.street, c.city, c.state, c.pincode, 
                   f.principal, f.tenure_months, f.interest_rate, f.maturity_amount, 
                   f.nominee, f.created_at, f.status, f.closed_date,
                   f.customer_id, COALESCE(f.fd_no, 'FD-' || LPAD(CAST(f.fd_id AS TEXT), 5, '0')) as fd_no,
                   COALESCE(f.tenure_days, f.tenure_months * 30) as tenure_days,
                   f.maturity_date
            FROM fixed_deposits f JOIN customers c ON f.customer_id = c.id
            ORDER BY f.fd_id DESC
        """)
        if all_fds:
            fd_print_dict = {}
            for r in all_fds:
                status_display = "🔴 CLOSED" if r[12] == 'CLOSED' else "🟢 ACTIVE"
                label = f"FD ID: {r[0]} | FDR No: {r[15]} - {r[1]} (Principal: ₹{r[6]:,.2f}) - {status_display}"
                fd_print_dict[label] = r
            
            selected_print_str = st.selectbox("Select FD Account for Printing/View", list(fd_print_dict.keys()), key="fd_print_select")
            fd_data = fd_print_dict[selected_print_str]
            
            fd_id, c_name, street, city, state, pincode, principal, tenure, rate, maturity, nominee, created_at, status, closed_date, cust_id, fd_no, tenure_days, maturity_date = fd_data
            
            fd_op_res = cached_query("SELECT voucher_date FROM journal_vouchers WHERE (narration LIKE ? OR narration LIKE ? OR narration LIKE ?) ORDER BY jv_id ASC LIMIT 1", (f"%FD #{fd_id}%", f"%{fd_no}%", f"%FD Opening%Customer {cust_id}%"))
            fd_op_bal = fd_op_res[0][0] if (fd_op_res and fd_op_res[0] and fd_op_res[0][0]) else created_at
            
            try:
                created_at_dt = pd.to_datetime(created_at).strftime('%d-%m-%Y')
            except Exception:
                created_at_dt = created_at
                
            try:
                fd_op_bal_dt = pd.to_datetime(fd_op_bal).strftime('%d-%m-%Y')
            except Exception:
                fd_op_bal_dt = fd_op_bal
                
            try:
                closed_date_dt = pd.to_datetime(closed_date).strftime('%d-%m-%Y') if closed_date else ""
            except Exception:
                closed_date_dt = closed_date

            try:
                mat_date_dt = pd.to_datetime(maturity_date).strftime('%d-%m-%Y') if maturity_date else ""
            except Exception:
                mat_date_dt = maturity_date or ""
            
            full_address = f"{street}, {city}, {state} - {pincode}" if street else f"{city}, {state} - {pincode}"
            status_text = "CLOSED" if status == 'CLOSED' else "ACTIVE"
            status_color = "#e74c3c" if status == 'CLOSED' else "#27ae60"
            tenure_display_str = f"{tenure_days} Days ({tenure} Months)" if tenure_days else f"{tenure} Months"
            repay_period_str = f"{tenure_days} days ({tenure} months)" if tenure_days else f"{tenure} months"
            
            receipt_html = f"""
            <style>
              .fd-receipt {{
                border: 2px solid #e67e22;
                padding: 25px;
                background-color: #fffdf9;
                font-family: Arial, sans-serif;
                color: #000;
                border-radius: 6px;
              }}
              .header {{ text-align: center; border-bottom: 2px solid #e67e22; padding-bottom: 10px; margin-bottom: 15px; }}
              .header h2 {{ color: #b94a00; margin: 0; font-size: 22px; }}
              .header p {{ margin: 2px; font-size: 11px; color: #555; }}
              .badge {{ background: #e67e22; color: white; padding: 4px 12px; font-weight: bold; font-size: 14px; display: inline-block; margin-bottom: 15px; }}
              .status-badge {{ background: {status_color}; color: white; padding: 4px 12px; font-weight: bold; font-size: 14px; display: inline-block; margin-bottom: 15px; margin-left: 10px; }}
              .grid-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; }}
              .box {{ border: 1px solid #ccc; padding: 10px; margin-top: 15px; background: #fff; }}
              table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 12px; }}
              th, td {{ border: 1px solid #999; padding: 6px; text-align: center; }}
              th {{ background-color: #fcebd9; }}
              .signatures {{ display: flex; justify-content: space-between; margin-top: 50px; font-size: 12px; font-weight: bold; text-align: center; }}
              .closed-info {{ background: #fde8e8; padding: 10px; border-radius: 5px; margin-top: 10px; color: #c0392b; }}
            </style>
            
            <div class="fd-receipt">
              <div class="header">
                <h2>AARSHA NIDHI LIMITED</h2>
                <p>6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501</p>
                <p>CIN: U65990KL2021PLN069978 | Ph: 0471-2994535</p>
              </div>
              <div style="text-align:center;">
                <span class="badge">FIXED DEPOSIT RECEIPT / LEDGER</span>
                <span class="status-badge">{status_text}</span>
              </div>
              
              <div class="grid-row">
                <div><b>FDR No. / A/c No:</b> {fd_no}</div>
                <div><b>A/c Opening Date:</b> {created_at_dt}</div>
              </div>
              <div class="grid-row">
                <div><b>Name:</b> {c_name}</div>
                <div><b>Opening Balance Date:</b> {fd_op_bal_dt}</div>
              </div>
              <div class="grid-row">
                <div><b>Address:</b> {full_address}</div>
                <div><b>Principal Amount:</b> ₹{principal:,.2f}</div>
              </div>
              <div class="grid-row">
                <div><b>Tenure:</b> {tenure_display_str}</div>
                <div><b>Interest Rate:</b> {rate}% p.a.</div>
              </div>
              <div class="grid-row">
                <div><b>Nominee:</b> {nominee if nominee else 'N/A'}</div>
                <div><b>Maturity Amount:</b> ₹{maturity:,.2f}</div>
              </div>
              <div class="grid-row">
                <div><b>Status:</b> {status_text}</div>
                <div>{f'<b>Closed Date:</b> {closed_date_dt}' if status == 'CLOSED' else (f'<b>Maturity Date:</b> {mat_date_dt}' if mat_date_dt else '')}</div>
              </div>
              
              <div class="box">
                <b>Deposit Repayable:</b> Principal sum of <b>₹{principal:,.2f}</b> repayable after {repay_period_str} with interest at {rate}% p.a.{f' (Maturity Date: {mat_date_dt})' if mat_date_dt else ''}
              </div>

              <table>
                <tr>
                  <th>Date</th>
                  <th>Particulars</th>
                  <th>Payment / Debit</th>
                  <th>Receipt / Credit</th>
                  <th>Balance</th>
                  <th>Int Paid</th>
                  <th>TDS</th>
                </tr>
                <tr>
                  <td>{fd_op_bal_dt}</td>
                  <td>Opening Balance Deposit</td>
                  <td>-</td>
                  <td>₹{principal:,.2f}</td>
                  <td>₹{principal:,.2f}</td>
                  <td>0</td>
                  <td>0</td>
                </tr>
                {f'<tr><td>{closed_date_dt}</td><td>FD Closed / Maturity Payment</td><td>₹{maturity:,.2f}</td><td>-</td><td>₹0.00</td><td>₹{maturity - principal:,.2f}</td><td>0</td></tr>' if status == 'CLOSED' else ''}
              </table>

              <div class="signatures">
                <div>Manager</div>
                <div>Accountant</div>
                <div>Chairman / MD</div>
              </div>
              {f'<div class="closed-info">⚠️ This Fixed Deposit has been CLOSED on {closed_date_dt}</div>' if status == 'CLOSED' else ''}
            </div>
            """
            clean_fd_html = "\n".join([line.strip() for line in receipt_html.strip().split("\n")])
            st.markdown(clean_fd_html, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            fd_data_pdf = list(fd_data[:14])
            fd_data_pdf.append(fd_op_bal)
            fd_data_pdf.append(fd_no)
            fd_data_pdf.append(tenure_days)
            fd_data_pdf.append(maturity_date)
            fd_pdf_data = pdf_generator.generate_fd_pdf(fd_data_pdf)
            st.download_button(
                label=f"📥 Download FD Certificate {fd_no} (PDF)",
                data=fd_pdf_data,
                file_name=f"FD_Certificate_{fd_no}.pdf",
                mime="application/pdf",
                key=f"download_fd_pdf_{fd_id}",
                use_container_width=True
            )
        else:
            st.info("No Fixed Deposits available to print.")

    with tab4:
        st.subheader("Close Fixed Deposit")
        active_fds = cached_query("""
            SELECT f.fd_id, COALESCE(f.fd_no, 'FD-' || LPAD(CAST(f.fd_id AS TEXT), 5, '0')) as fd_no,
                   c.name, f.principal, f.maturity_amount, f.interest_rate, f.tenure_months,
                   COALESCE(f.tenure_days, f.tenure_months * 30) as tenure_days
            FROM fixed_deposits f JOIN customers c ON f.customer_id = c.id
            WHERE f.status = 'ACTIVE'
            ORDER BY f.fd_id ASC
        """)
        
        if active_fds:
            fd_dict = {f"FD ID: {r[0]} | FDR No: {r[1]} - {r[2]} (Principal: ₹{r[3]:,.2f}, Tenure: {r[7]} Days [{r[6]}M], Maturity: ₹{r[4]:,.2f})": r for r in active_fds}
            col_fc1, col_fc2 = st.columns(2)
            with col_fc1:
                selected_fd_str = st.selectbox("Select FD to Close", list(fd_dict.keys()), key="fd_close_select")
            with col_fc2:
                fd_close_date = st.date_input("Closing Date", value=date.today(), format="DD-MM-YYYY", key="fd_close_date_input")
                
            selected_fd = fd_dict[selected_fd_str]
            fd_id, fd_no, cust_name, principal, maturity_amount, interest_rate, tenure, tenure_days = selected_fd
            
            interest_earned = maturity_amount - principal
            st.info(f"Interest Earned: ₹{interest_earned:,.2f}")
            st.info(f"Total Maturity Amount (Principal + Interest): ₹{maturity_amount:,.2f}")
            
            if st.button("Close FD", type="primary", use_container_width=True):
                close_date_str = fd_close_date.strftime("%Y-%m-%d")
                run_query("""
                    UPDATE fixed_deposits 
                    SET status = 'CLOSED', closed_date = ?
                    WHERE fd_id = ?
                """, (close_date_str, fd_id), fetch=False)
                
                if interest_earned > 0:
                    post_automated_jv(f"Fixed Deposit [{fd_no}] Interest Accrued", "EXP-102", "LIA-102", interest_earned, voucher_date=close_date_str)
                
                post_automated_jv(f"Fixed Deposit [{fd_no}] Maturity - Transfer to SB", "LIA-102", "LIA-101", maturity_amount, voucher_date=close_date_str)
                
                clear_db_cache()
                st.success(f"Fixed Deposit {fd_no} closed successfully on {close_date_str}!")
                st.info(f"₹{maturity_amount:,.2f} transferred from FD Deposits Control to SB Deposits Control")
                st.rerun()
        else:
            st.info("No active FDs available to close.")

    with tab5:
        st.subheader("✏️ Edit & Correct Fixed Deposit (FD) Account")
        all_fds_edit = cached_query("""
            SELECT f.fd_id, c.name, f.principal, f.tenure_months, f.interest_rate, 
                   f.maturity_amount, f.nominee, f.status, f.created_at, f.closed_date, 
                   f.payment_mode, f.customer_id,
                   COALESCE(f.fd_no, 'FD-' || LPAD(CAST(f.fd_id AS TEXT), 5, '0')) as fd_no,
                   COALESCE(f.tenure_days, f.tenure_months * 30) as tenure_days,
                   f.maturity_date
            FROM fixed_deposits f JOIN customers c ON f.customer_id = c.id
            ORDER BY f.fd_id DESC
        """)
        if all_fds_edit:
            fd_edit_dict = {}
            for r in all_fds_edit:
                status_icon = "🔴 CLOSED" if r[7] == 'CLOSED' else "🟢 ACTIVE"
                t_str = f"{r[13]} Days ({r[3]}M)" if r[13] else f"{r[3]}M"
                label = f"FD ID: {r[0]} | FDR No: {r[12]} - {r[1]} (Principal: ₹{r[2]:,.2f} | Tenure: {t_str} | Opened: {r[8]}) - {status_icon}"
                fd_edit_dict[label] = r
                
            selected_edit_label = st.selectbox("Select FD Account to Edit", list(fd_edit_dict.keys()), key="fd_edit_select")
            curr_fd = fd_edit_dict[selected_edit_label]
            c_fd_id, c_name, c_principal, c_tenure, c_rate, c_maturity, c_nominee, c_status, c_created, c_closed, c_pay_mode, c_cust_id, c_fd_no, c_tenure_days, c_maturity_date = curr_fd
            
            customers_all = cached_query("""
                SELECT c.id, c.name, COALESCE(c.account_no, '') 
                FROM customers c 
                ORDER BY c.name ASC, c.id ASC
            """)
            cust_all_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers_all}
            cust_idx = list(cust_all_dict.values()).index(c_cust_id) if c_cust_id in cust_all_dict.values() else 0
            
            try:
                c_created_dt = pd.to_datetime(c_created).date() if c_created else date.today()
            except Exception:
                c_created_dt = date.today()
                
            try:
                c_closed_dt = pd.to_datetime(c_closed).date() if c_closed else date.today()
            except Exception:
                c_closed_dt = date.today()

            fd_op_bal_res = cached_query("SELECT voucher_date FROM journal_vouchers WHERE (narration LIKE ? OR narration LIKE ? OR narration LIKE ?) ORDER BY jv_id ASC LIMIT 1", (f"%FD #{c_fd_id}%", f"%{c_fd_no}%", f"%FD Opening%Customer {c_cust_id}%"))
            try:
                fd_op_bal_dt = pd.to_datetime(fd_op_bal_res[0][0]).date() if fd_op_bal_res and fd_op_bal_res[0][0] else c_created_dt
            except Exception:
                fd_op_bal_dt = c_created_dt

            st.markdown("---")
            col_fe0_1, col_fe0_2 = st.columns(2)
            with col_fe0_1:
                edit_fd_no = st.text_input("FDR No / FD Account Number", value=str(c_fd_no), key=f"edit_fd_no_{c_fd_id}", help="Enter FDR certificate number or custom account number, e.g. 01540001 or FD-00002")
            with col_fe0_2:
                edit_fd_id_num = st.number_input("Numeric FD ID", min_value=1, value=int(c_fd_id), step=1, key=f"edit_fd_id_num_{c_fd_id}", help="You can change the internal numeric FD ID.")

            col_fe1, col_fe2 = st.columns(2)
            with col_fe1:
                edit_fd_cust_label = st.selectbox("Assigned Customer", list(cust_all_dict.keys()), index=cust_idx, key=f"edit_fd_cust_{c_fd_id}")
                edit_fd_cust_id = cust_all_dict[edit_fd_cust_label]
                edit_fd_principal = st.number_input("Principal Amount (₹)", min_value=100.0, value=float(c_principal or 10000.0), step=500.0, key=f"edit_fd_prin_{c_fd_id}")
                
                edit_fd_tenure_days = st.number_input("Tenure (Days)", min_value=1, max_value=3650, value=int(c_tenure_days or (c_tenure * 30 if c_tenure else 365)), step=10, key=f"edit_fd_tenure_days_{c_fd_id}", help="Enter tenure in days")
                edit_fd_tenure = max(1, int(round(edit_fd_tenure_days / 30.0)))
                st.caption(f"🗓️ Equivalent Tenure: ~**{edit_fd_tenure} Months** ({edit_fd_tenure_days} Days)")
                
                edit_fd_rate = st.number_input("Interest Rate (% p.a.)", min_value=0.0, max_value=30.0, value=float(c_rate or 6.5), step=0.25, key=f"edit_fd_rate_{c_fd_id}")
            with col_fe2:
                edit_fd_nominee = st.text_input("Nominee Name", value=str(c_nominee) if c_nominee else "", key=f"edit_fd_nom_{c_fd_id}")
                edit_fd_status = st.selectbox("Status", ["ACTIVE", "CLOSED"], index=0 if c_status == "ACTIVE" else 1, key=f"edit_fd_status_{c_fd_id}")
                edit_fd_created = st.date_input("A/c Opening Date", value=c_created_dt, format="DD-MM-YYYY", key=f"edit_fd_created_{c_fd_id}")
                edit_fd_op_date = st.date_input("Opening Balance Date", value=fd_op_bal_dt, format="DD-MM-YYYY", key=f"edit_fd_op_{c_fd_id}")
                if edit_fd_status == "CLOSED":
                    edit_fd_closed = st.date_input("Closed Date", value=c_closed_dt, format="DD-MM-YYYY", key=f"edit_fd_closed_{c_fd_id}")
                else:
                    edit_fd_closed = None
                edit_fd_pay_mode = st.selectbox("Payment Mode", ["Union Bank of India", "Cash", "State Bank of India"], index=1 if (c_pay_mode or "").lower() == "cash" else (2 if "state" in (c_pay_mode or "").lower() else 0), key=f"edit_fd_pm_{c_fd_id}")

            # Live recalculation
            calc_fd_maturity = edit_fd_principal + (edit_fd_principal * edit_fd_rate * (edit_fd_tenure_days / 365.0) / 100.0)
            calc_fd_interest = calc_fd_maturity - edit_fd_principal
            
            st.markdown("---")
            st.markdown("#### ⚡ Maturity Amount & Recalculation")
            mat_mode = st.radio(
                "Maturity Amount Option",
                [f"🔄 Calculated Standard Maturity: ₹{calc_fd_maturity:,.2f} (Interest: ₹{calc_fd_interest:,.2f})",
                 f"📄 Keep Currently Stored Amount: ₹{float(c_maturity or 0.0):,.2f}",
                 "✍️ Enter Custom Maturity Amount"],
                key=f"mat_mode_{c_fd_id}"
            )
            if "Standard Maturity" in mat_mode:
                final_fd_mat = round(calc_fd_maturity, 2)
            elif "Keep Currently" in mat_mode:
                final_fd_mat = float(c_maturity or 0.0)
            else:
                final_fd_mat = st.number_input("Custom Maturity Amount (₹)", min_value=0.0, value=float(c_maturity or calc_fd_maturity), step=500.0, key=f"custom_fd_mat_{c_fd_id}")
                
            m_c1, m_c2, m_c3 = st.columns(3)
            m_c1.metric("Principal Amount", f"₹{edit_fd_principal:,.2f}")
            m_c2.metric("Interest Component", f"₹{max(0.0, final_fd_mat - edit_fd_principal):,.2f}")
            m_c3.metric("Total Maturity Amount", f"₹{final_fd_mat:,.2f}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            btn_f1, btn_f2 = st.columns([3, 1])
            with btn_f1:
                if st.button("💾 Save & Update FD Details", key=f"btn_save_fd_{c_fd_id}", type="primary", use_container_width=True):
                    created_str = edit_fd_created.strftime("%Y-%m-%d")
                    op_bal_str = edit_fd_op_date.strftime("%Y-%m-%d")
                    closed_str = edit_fd_closed.strftime("%Y-%m-%d") if edit_fd_closed else None
                    
                    if "cash" in edit_fd_pay_mode.lower():
                        chosen_asset = "AST-101"
                    elif "state" in edit_fd_pay_mode.lower() or "sbi" in edit_fd_pay_mode.lower():
                        chosen_asset = "AST-103"
                    else:
                        chosen_asset = "AST-102"
                        
                    success, msg = update_fd_account_details(
                        c_fd_id, edit_fd_cust_id, edit_fd_principal, edit_fd_tenure, edit_fd_rate,
                        edit_fd_nominee, edit_fd_status, created_str, closed_str,
                        edit_fd_pay_mode, chosen_asset_code=chosen_asset, new_op_bal_date=op_bal_str,
                        new_maturity_amount=final_fd_mat,
                        new_fd_no=edit_fd_no, new_fd_id=edit_fd_id_num,
                        new_tenure_days=edit_fd_tenure_days
                    )
                    clear_db_cache()
                    if success:
                        flash_success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to update FD: {msg}")
            with btn_f2:
                with st.popover("🗑️ Delete FD"):
                    st.error(f"⚠️ Are you sure you want to permanently delete FD #{c_fd_id}?")
                    st.caption("This will delete the FD and re-sequence without gaps.")
                    if st.button("Confirm Delete Permanently", key=f"btn_del_fd_{c_fd_id}", type="primary", use_container_width=True):
                        success, msg = delete_fd_entry(c_fd_id)
                        clear_db_cache()
                        if success:
                            flash_success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to delete FD: {msg}")
        else:
            st.info("No Fixed Deposits available to edit.")

def render_recurring_deposits():
    st.title("🔄 Recurring Deposits Management")
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Open RD", "Pay Installment", "Active RDs", "Print Certificate / Ledger", "Close RD", "✏️ Edit / Update RD"])
    
    with tab1:
        customers = cached_query("""
            SELECT c.id, c.name, c.street, c.city, c.state, c.pincode 
            FROM customers c 
            ORDER BY c.name ASC, c.id ASC
        """)
        if customers:
            cust_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers}
            col_rd1, col_rd2 = st.columns(2)
            with col_rd1:
                selected_cust = st.selectbox("Select Customer Name for RD", list(cust_dict.keys()), key="rd_cust")
                monthly_amt = st.number_input("Monthly Installment Amount (Contracted) (₹)", min_value=100.0, value=1000.0, step=100.0, key="rd_monthly_inp")
                opening_balance = st.number_input("Opening Balance (₹)", min_value=0.0, value=float(monthly_amt), step=500.0, key="rd_open_bal_inp", help="Initial opening ledger balance at account creation.")
                calc_default_inst = max(1, int(round(opening_balance / monthly_amt))) if monthly_amt > 0 else 1
                opening_paid_inst = st.number_input("Installments Paid at Opening", min_value=1, max_value=10000, value=min(10000, max(1, int(calc_default_inst))), step=1, key="rd_open_paid_inst_inp")
                tenure_days = st.number_input("Tenure (Days)", min_value=1, max_value=3650, value=365, step=10, key="rd_tenure_days", help="e.g. 100 days, 365 days, 400 days, 730 days")
                tenure = max(1, int(round(tenure_days / 30.0)))
                st.caption(f"🗓️ Equivalent Tenure: ~**{tenure} Months** ({tenure_days} Days)")
            with col_rd2:
                custom_rd_no = st.text_input("Custom RD Account No (Optional)", placeholder="e.g. RD-00001", key="rd_custom_no_inp")
                scheme_name = st.text_input("Scheme Name", value="SWAYAMVARA KSHEMANIDHI", key="rd_scheme_name_inp")
                rd_open_date = st.date_input("A/c Opening Date", value=date.today(), format="DD-MM-YYYY", key="rd_open_date_input")
                rd_op_bal_date = st.date_input("Opening Balance Date", value=date.today(), format="DD-MM-YYYY", key="rd_op_bal_date_input")
                interest_rate = st.number_input("Interest Rate (% p.a.)", value=6.0, step=0.25, key="rd_rate")
                nominee = st.text_input("Nominee Name", key="rd_nom")
            
            asset_accounts = cached_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset' AND account_code IN ('AST-101', 'AST-102', 'AST-103')")
            if not asset_accounts:
                asset_accounts = cached_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset'")
            
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
            
            total_deposits, approx_maturity, approx_interest = calculate_rd_maturity(monthly_amt, interest_rate, tenure)
            mat_date_calc = (rd_open_date + timedelta(days=int(tenure_days))).strftime("%Y-%m-%d")
            
            st.info(f"**Estimated Maturity (Quarterly Compounded):** Total Deposits ₹{total_deposits:,.2f} + Interest ₹{approx_interest:,.2f} = ₹{approx_maturity:,.2f} | Maturity Date: **{pdf_generator.format_date_str(mat_date_calc)}** ({tenure_days} Days)")
            
            if st.button("Open RD Account", use_container_width=True, type="primary"):
                open_date_str = rd_open_date.strftime("%Y-%m-%d")
                op_bal_date_str = rd_op_bal_date.strftime("%Y-%m-%d")
                mat_date_str = (rd_open_date + timedelta(days=int(tenure_days))).strftime("%Y-%m-%d")
                
                cur_rd_cnt = run_query("SELECT COUNT(*) FROM recurring_deposits")
                rd_seq = (cur_rd_cnt[0][0] + 1) if cur_rd_cnt and cur_rd_cnt[0] else 1
                final_rd_no = custom_rd_no.strip() if custom_rd_no and custom_rd_no.strip() else f"RD-{rd_seq:05d}"
                
                new_rd_res = run_query("""
                    INSERT INTO recurring_deposits (customer_id, monthly_amount, opening_balance, tenure_months, tenure_days, interest_rate, installments_paid, nominee, status, created_at, payment_mode, maturity_amount, collected_balance, scheme_name, rd_no, maturity_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, ?, ?, ?)
                    RETURNING rd_id
                """, (cust_dict[selected_cust], monthly_amt, float(opening_balance), tenure, tenure_days, interest_rate, opening_paid_inst, nominee, 
                      open_date_str, payment_mode, approx_maturity, opening_balance, scheme_name, final_rd_no, mat_date_str))
                
                if new_rd_res and new_rd_res[0]:
                    rd_id = new_rd_res[0][0]
                else:
                    rd_lookup = run_query("SELECT rd_id FROM recurring_deposits WHERE rd_no = ? ORDER BY rd_id DESC LIMIT 1", (final_rd_no,))
                    rd_id = rd_lookup[0][0] if rd_lookup and rd_lookup[0] else rd_seq
                
                jv_result = post_automated_jv(f"RD Opening [{final_rd_no}] - Total Deposited ₹{opening_balance} via {payment_mode}", chosen_asset_code, "LIA-103", opening_balance, voucher_date=op_bal_date_str)
                
                if jv_result:
                    today_time = f"{op_bal_date_str} 10:00"
                    new_balance = get_account_balance_from_jv(chosen_asset_code)
                    
                    if chosen_asset_code == 'AST-101':
                        voucher_no = generate_cash_voucher_no()
                        run_query("""
                            INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (op_bal_date_str, voucher_no, f"RD Opening: {final_rd_no} - Customer {cust_dict[selected_cust]}", 0, opening_balance, new_balance, chosen_asset_code, f"RD Opening via {payment_mode}", today_time), fetch=False)
                    elif chosen_asset_code in ['AST-102', 'AST-103']:
                        bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
                        voucher_no = generate_bank_voucher_no()
                        run_query("""
                            INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (op_bal_date_str, voucher_no, f"RD Opening: {final_rd_no} - Customer {cust_dict[selected_cust]}", 0, opening_balance, new_balance, bank_name, chosen_asset_code, f"RD Opening via {payment_mode}", today_time), fetch=False)
                
                try:
                    op_v_no = voucher_no if 'voucher_no' in locals() else f"OP-{final_rd_no}"
                    inst_lbl = f"1 to {opening_paid_inst}" if opening_paid_inst > 1 else "1"
                    part_lbl = f"RD Opening Balance ({opening_paid_inst} Installments)" if opening_paid_inst > 1 else "RD Opening Balance"
                    run_query("""
                        INSERT INTO rd_installments (rd_id, installment_no, payment_date, particulars, debit_amount, credit_amount, balance, payment_mode, voucher_no, narration, created_at)
                        VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
                    """, (rd_id, inst_lbl, op_bal_date_str, part_lbl, opening_balance, opening_balance, payment_mode, op_v_no, f"RD Opening via {payment_mode}", today_time), fetch=False)
                except Exception:
                    pass
                
                clear_db_cache()
                flash_success(f"🎉 Recurring Deposit **{final_rd_no}** opened & recorded successfully (Opened: {open_date_str} | Op Bal Date: {op_bal_date_str} | Tenure: {tenure_days} Days [{tenure}M] | Monthly: ₹{monthly_amt:,.2f} | Opening Bal: ₹{opening_balance:,.2f} [{opening_paid_inst} Inst.]) via {payment_mode}!")
                st.rerun()
        else:
            st.warning("Register customers first.")

    with tab2:
        active_rds = cached_query("""
            SELECT r.rd_id, c.name, r.monthly_amount, r.tenure_months, r.installments_paid, r.maturity_amount, COALESCE(r.tenure_days, r.tenure_months * 30) as tenure_days
            FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id 
            WHERE r.status='ACTIVE'
            ORDER BY r.rd_id ASC
        """)
        if active_rds:
            rd_dict = {f"RD ID: {r[0]} - {r[1]} (Monthly: ₹{r[2]:,.2f}, Paid: {r[4]}/{r[3]} [{r[6]} Days])": r for r in active_rds}
            col_rp1, col_rp2 = st.columns(2)
            with col_rp1:
                chosen_rd_str = st.selectbox("Select Active RD Account", list(rd_dict.keys()), key="rd_pay_select")
            with col_rp2:
                rd_pay_date = st.date_input("Installment Payment Date", value=date.today(), format="DD-MM-YYYY", key="rd_pay_date_input")
                
            selected_rd = rd_dict[chosen_rd_str]
            rd_id, cust_name, monthly_amt, tenure_m, paid_inst, maturity_amt, t_days = selected_rd
            
            asset_accounts = cached_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset' AND account_code IN ('AST-101', 'AST-102', 'AST-103')")
            if not asset_accounts:
                asset_accounts = cached_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset'")
            
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
            
            if st.button("Confirm & Pay Installment", use_container_width=True, type="primary"):
                if paid_inst < tenure_m:
                    success, msg = pay_rd_installment(rd_id, rd_pay_date, chosen_asset_code, monthly_amt)
                    if success:
                        flash_success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
                else:
                    st.info("All installments for this RD have already been paid.")
                    
            st.markdown("---")
            with st.expander("✏️ Correct / Edit / Delete Previously Entered Installments"):
                st.caption(f"Fix wrong payment dates, amounts, or remove installments for **{chosen_rd_str}**:")
                t2_inst_list = ensure_rd_installments_populated(rd_id)
                if t2_inst_list:
                    col_t2_res1, col_t2_res2 = st.columns([3, 1])
                    with col_t2_res1:
                        if st.button("🔄 Resequence All Installments Chronologically (Opening First, Latest Last)", key=f"t2_btn_reseq_{rd_id}", use_container_width=True):
                            success, msg = resequence_rd_installments(rd_id)
                            clear_db_cache()
                            if success:
                                flash_success(f"✅ {msg}")
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")
                    st.markdown("<br>", unsafe_allow_html=True)
                    t2_inst_dict = {f"Inst #{r[1]} | {pdf_generator.format_date_str(r[2])} | ₹{r[5]:,.2f} | {r[7]} (ID: {r[0]})": r for r in t2_inst_list}
                    t2_chosen_lbl = st.selectbox("Choose Installment to Modify", list(t2_inst_dict.keys()), key=f"t2_sel_inst_{rd_id}")
                    t2_row = t2_inst_dict[t2_chosen_lbl]
                    t2_iid, t2_ino, t2_pdate, t2_part, t2_dr, t2_cr, t2_bal, t2_pm, t2_vno, t2_narr = t2_row
                    
                    try:
                        t2_pdate_dt = pd.to_datetime(t2_pdate).date() if t2_pdate else date.today()
                    except Exception:
                        t2_pdate_dt = date.today()
                        
                    col_t2_1, col_t2_2 = st.columns(2)
                    with col_t2_1:
                        t2_edit_date = st.date_input("Correct Payment Date", value=t2_pdate_dt, format="DD-MM-YYYY", key=f"t2_pdate_{t2_iid}")
                        t2_edit_ino = st.text_input("Installment No / Reference", value=str(t2_ino), key=f"t2_ino_{t2_iid}")
                        t2_edit_cr = st.number_input("Correct Amount (₹)", min_value=0.0, value=float(t2_cr), step=500.0, key=f"t2_cr_{t2_iid}")
                    with col_t2_2:
                        t2_pm_opts = ["Union Bank of India (NEFT / UPI)", "Cash in Hand (Office Drawer)", "State Bank of India"]
                        t2_pm_idx = 0 if "union" in str(t2_pm).lower() else (1 if "cash" in str(t2_pm).lower() else 2)
                        t2_edit_pm = st.selectbox("Payment Mode", t2_pm_opts, index=t2_pm_idx, key=f"t2_pm_{t2_iid}")
                        t2_edit_part = st.text_input("Particulars", value=str(t2_part), key=f"t2_part_{t2_iid}")
                        t2_edit_narr = st.text_input("Narration / Remarks", value=str(t2_narr), key=f"t2_narr_{t2_iid}")
                    
                    col_t2_b1, col_t2_b2 = st.columns([3, 1])
                    with col_t2_b1:
                        if st.button("💾 Save Installment Date & Details", key=f"t2_save_{t2_iid}", type="primary", use_container_width=True):
                            pm_str = "Union Bank of India" if "Union" in t2_edit_pm else ("Cash" if "Cash" in t2_edit_pm else "State Bank of India")
                            success, msg = update_rd_installment(t2_iid, rd_id, t2_edit_date, t2_edit_cr, pm_str, t2_edit_part, str(t2_edit_narr), installment_no=t2_edit_ino)
                            clear_db_cache()
                            if success:
                                flash_success("✅ Installment corrected & synced with all books successfully!")
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")
                    with col_t2_b2:
                        with st.popover("🗑️ Delete"):
                            st.error(f"Delete Inst #{t2_ino} ({t2_pdate})?")
                            st.caption("Will reverse voucher and adjust balances.")
                            if st.button("Confirm Delete", key=f"t2_del_{t2_iid}", type="primary", use_container_width=True):
                                success, msg = delete_rd_installment(t2_iid, rd_id)
                                clear_db_cache()
                                if success:
                                    flash_success(f"✅ {msg}")
                                    st.rerun()
                                else:
                                    st.error(f"❌ {msg}")
                else:
                    st.info("No installments recorded for this RD account yet.")
        else:
            st.info("No active recurring deposits found.")

    with tab3:
        rds = cached_query("""
            SELECT COALESCE(r.rd_no, 'RD-' || CAST(r.rd_id AS TEXT)) as acc_no, 
                   c.name, COALESCE(r.scheme_name, 'SWAYAMVARA KSHEMANIDHI') as scheme,
                   r.monthly_amount, COALESCE(r.tenure_days, r.tenure_months * 30) as tenure_days,
                   r.tenure_months, r.interest_rate, 
                   r.installments_paid, COALESCE(r.collected_balance, r.monthly_amount * r.installments_paid) as col_bal,
                   r.created_at,
                   COALESCE(r.maturity_date, '2026-12-20') as mat_date,
                   r.maturity_amount, r.nominee, r.status
            FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id
            WHERE r.status = 'ACTIVE'
            ORDER BY r.rd_id DESC
        """)
        if rds:
            df_rds = pd.DataFrame(rds, columns=["A/C No", "Customer Name", "Scheme", "Monthly (₹)", "Tenure (Days)", "Tenure (Months)", "Rate (%)", "Paid Inst.", "Total Deposited (₹)", "Opened Date", "Maturity Date", "Maturity Amount (₹)", "Nominee", "Status"])
            df_rds_formatted = format_df_dates(df_rds)
            st.dataframe(df_rds_formatted, use_container_width=True)
        else:
            st.info("No active recurring deposits found.")

    with tab4:
        st.subheader("🖨️ Printable RD Certificate & Ledger")
        all_rds = cached_query("""
            SELECT r.rd_id, c.name, c.street, c.city, c.state, c.pincode, 
                   r.monthly_amount, r.tenure_months, r.interest_rate, 
                   r.installments_paid, r.maturity_amount, r.nominee, 
                   r.created_at, r.status, r.closed_date,
                   COALESCE(r.rd_no, 'RD-' || CAST(r.rd_id AS TEXT)) as acc_no,
                   COALESCE(r.collected_balance, r.monthly_amount * r.installments_paid) as col_bal,
                   COALESCE(r.scheme_name, 'SWAYAMVARA KSHEMANIDHI') as scheme_name,
                   COALESCE(r.maturity_date, '2026-12-20') as maturity_date,
                   r.customer_id,
                   COALESCE(r.tenure_days, r.tenure_months * 30) as tenure_days
            FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id
            ORDER BY r.rd_id DESC
        """)
        if all_rds:
            rd_print_dict = {}
            for r in all_rds:
                status_display = "🔴 CLOSED" if r[13] == 'CLOSED' else "🟢 ACTIVE"
                label = f"A/C: {r[15]} - {r[1]} ({r[17]} | Paid: {r[9]}/{r[7]} [{r[20]} Days] | Balance: ₹{r[16]:,.2f}) - {status_display}"
                rd_print_dict[label] = r
            
            selected_rd_print = st.selectbox("Select RD Account for Printing/View", list(rd_print_dict.keys()), key="rd_print_select")
            rd_data = rd_print_dict[selected_rd_print]
            
            rd_id, c_name, street, city, state, pincode, monthly_amt, tenure, rate, paid_inst, maturity, nominee, created_at, status, closed_date, rd_acc_no, col_balance, scheme_name, maturity_date, cust_id, tenure_days = rd_data
            
            rd_op_res = cached_query("SELECT voucher_date FROM journal_vouchers WHERE (narration LIKE ? OR narration LIKE ? OR narration LIKE ?) ORDER BY jv_id ASC LIMIT 1", (f"%RD #{rd_id}%", f"%{rd_acc_no}%", f"%RD Opening%Customer {cust_id}%"))
            op_bal_date = rd_op_res[0][0] if (rd_op_res and rd_op_res[0] and rd_op_res[0][0]) else created_at
            
            full_address = f"{street}, {city}, {state} - {pincode}" if street else f"{city}, {state} - {pincode}"
            total_deposited = col_balance
            status_text = "CLOSED" if status == 'CLOSED' else "ACTIVE"
            status_color = "#e74c3c" if status == 'CLOSED' else "#2980b9"
            
            created_at_dt = pdf_generator.format_date_str(created_at)
            op_bal_date_dt = pdf_generator.format_date_str(op_bal_date)
            maturity_date_dt = pdf_generator.format_date_str(maturity_date)
            closed_date_dt = pdf_generator.format_date_str(closed_date) if closed_date else ""
            
            if status == 'CLOSED' or int(paid_inst or 0) < int(tenure or 1):
                try:
                    _, accrued_mat, _ = calculate_rd_accrued_value(float(monthly_amt or 0), float(rate or 0), int(paid_inst or 0))
                    display_maturity = accrued_mat if (status == 'CLOSED' or int(paid_inst or 0) < int(tenure or 1)) else float(maturity)
                except Exception:
                    display_maturity = float(maturity)
            else:
                display_maturity = float(maturity)
            
            tenure_display_str = f"{tenure_days} DAYS ({tenure} Months)"

            ledger_rows = get_rd_ledger_rows(rd_id)
            
            ledger_html_rows = ""
            if ledger_rows:
                for lr in ledger_rows:
                    p_date_fmt = pdf_generator.format_date_str(lr.get("payment_date", created_at))
                    part_txt = lr.get("particulars", "")
                    dr_txt = f"₹{lr['debit_amount']:,.2f}" if lr.get("debit_amount", 0) > 0 else "-"
                    cr_txt = f"₹{lr['credit_amount']:,.2f}" if lr.get("credit_amount", 0) > 0 else "-"
                    bal_txt = f"₹{lr.get('balance', 0):,.2f}"
                    inst_txt = str(lr.get("installment_no", ""))
                    ledger_html_rows += f"<tr><td>{p_date_fmt}</td><td style='text-align:left; padding-left:10px;'>{part_txt}</td><td style='text-align:right; padding-right:10px;'>{dr_txt}</td><td style='text-align:right; padding-right:10px; font-weight:bold; color:#1b4f72;'>{cr_txt}</td><td style='text-align:right; padding-right:10px; font-weight:bold;'>{bal_txt}</td><td><b>{inst_txt}</b></td></tr>\n"
            else:
                ledger_html_rows = f"<tr><td>{op_bal_date_dt}</td><td style='text-align:left; padding-left:10px;'>RD Account Opening Balance</td><td>-</td><td style='text-align:right; padding-right:10px; font-weight:bold; color:#1b4f72;'>₹{col_balance:,.2f}</td><td style='text-align:right; padding-right:10px; font-weight:bold;'>₹{col_balance:,.2f}</td><td><b>{paid_inst}</b></td></tr>\n"
                
            if status == 'CLOSED':
                ledger_html_rows += f"<tr style='background-color:#fde8e8;'><td>{closed_date_dt}</td><td style='text-align:left; padding-left:10px; font-weight:bold; color:#c0392b;'>RD Closed / Maturity Payment</td><td style='text-align:right; padding-right:10px; font-weight:bold; color:#c0392b;'>₹{display_maturity:,.2f}</td><td style='text-align:right; padding-right:10px;'>-</td><td style='text-align:right; padding-right:10px; font-weight:bold;'>₹0.00</td><td><b>{paid_inst}</b></td></tr>\n"

            rd_receipt_html = f"""
<style>
.rd-receipt {{
  border: 2px solid #2980b9;
  padding: 25px;
  background-color: #f4f9fd;
  font-family: Arial, sans-serif;
  color: #000;
  border-radius: 6px;
}}
.header {{ text-align: center; border-bottom: 2px solid #2980b9; padding-bottom: 10px; margin-bottom: 15px; }}
.header h2 {{ color: #1b4f72; margin: 0; font-size: 22px; }}
.header p {{ margin: 2px; font-size: 11px; color: #555; }}
.badge {{ background: #2980b9; color: white; padding: 4px 12px; font-weight: bold; font-size: 14px; display: inline-block; margin-bottom: 15px; }}
.status-badge {{ background: {status_color}; color: white; padding: 4px 12px; font-weight: bold; font-size: 14px; display: inline-block; margin-bottom: 15px; margin-left: 10px; }}
.grid-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; }}
.box {{ border: 1px solid #ccc; padding: 10px; margin-top: 15px; background: #fff; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 12px; }}
th, td {{ border: 1px solid #999; padding: 6px; text-align: center; }}
th {{ background-color: #ebf5fb; }}
.signatures {{ display: flex; justify-content: space-between; margin-top: 50px; font-size: 12px; font-weight: bold; text-align: center; }}
.closed-info {{ background: #fde8e8; padding: 10px; border-radius: 5px; margin-top: 10px; color: #c0392b; }}
</style>

<div class="rd-receipt">
  <div class="header">
    <h2>AARSHA NIDHI LIMITED</h2>
    <p>6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501</p>
    <p>CIN: U65990KL2021PLN069978 | Ph: 0471-2994535</p>
  </div>
  <div style="text-align:center;">
    <span class="badge">RECURRING DEPOSIT RECEIPT / LEDGER</span>
    <span class="status-badge">{status_text}</span>
  </div>
  
  <div class="grid-row">
    <div><b>RDR No. / A/c No:</b> {rd_acc_no}</div>
    <div><b>Scheme:</b> <span style="color:#1b4f72;font-weight:bold;">{scheme_name}</span></div>
  </div>
  <div class="grid-row">
    <div><b>A/c Opening Date:</b> {created_at_dt}</div>
    <div><b>Maturity Date:</b> <span style="color:#27ae60;font-weight:bold;">{maturity_date_dt}</span></div>
  </div>
  <div class="grid-row">
    <div><b>Name:</b> {c_name}</div>
    <div><b>Opening Balance Date:</b> {op_bal_date_dt}</div>
  </div>
  <div class="grid-row">
    <div><b>Address:</b> {full_address}</div>
    <div><b>Interest Rate:</b> {rate}% p.a.</div>
  </div>
  <div class="grid-row">
    <div><b>Monthly Installment:</b> ₹{monthly_amt:,.2f}</div>
    <div><b>Nominee:</b> {nominee if nominee else 'N/A'}</div>
  </div>
  <div class="grid-row">
    <div><b>Tenure:</b> {tenure_display_str}</div>
    <div><b>Installments Paid:</b> {paid_inst} / {tenure}</div>
  </div>
  <div class="grid-row">
    <div><b>Total Balance Deposited:</b> ₹{col_balance:,.2f}</div>
    <div><b>Maturity Amount:</b> <span style="color:#1b4f72;font-weight:bold;">₹{display_maturity:,.2f}</span></div>
  </div>
  <div class="grid-row">
    <div><b>Status:</b> {status_text}</div>
    <div>{f'<b>Closed Date:</b> {closed_date_dt}' if status == 'CLOSED' else ''}</div>
  </div>
  
  <div class="box">
    <b>Deposit Repayable:</b> Recurring Deposit of <b>₹{monthly_amt:,.2f}</b> monthly for {tenure_display_str}. Total balance accumulated: <b>₹{col_balance:,.2f}</b>.
  </div>

  <table>
    <tr>
      <th>Date</th>
      <th>Particulars</th>
      <th>Payment / Debit</th>
      <th>Receipt / Credit</th>
      <th>Balance</th>
      <th>Installment No</th>
    </tr>
{ledger_html_rows}
  </table>

  <div class="signatures">
    <div>Manager</div>
    <div>Accountant</div>
    <div>Chairman / MD</div>
  </div>
  {f'<div class="closed-info">⚠️ This Recurring Deposit has been CLOSED on {closed_date_dt}</div>' if status == 'CLOSED' else ''}
</div>
"""
            clean_rd_html = "\n".join([line.strip() for line in rd_receipt_html.strip().split("\n")])
            st.markdown(clean_rd_html, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            rd_data_pdf = list(rd_data[:19])
            rd_data_pdf[10] = display_maturity
            rd_data_pdf.append(op_bal_date)
            rd_data_pdf.append(tenure_days)
            rd_pdf_data = pdf_generator.generate_rd_pdf(rd_data_pdf, ledger_rows=ledger_rows)
            st.download_button(
                label=f"📥 Download RD Certificate {rd_acc_no} (PDF)",
                data=rd_pdf_data,
                file_name=f"RD_Certificate_{rd_acc_no}.pdf",
                mime="application/pdf",
                key=f"download_rd_pdf_{rd_id}",
                use_container_width=True
            )
        else:
            st.info("No Recurring Deposits available to print.")

    with tab5:
        st.subheader("Close Recurring Deposit")
        active_rds_close = cached_query("""
            SELECT r.rd_id, c.name, r.monthly_amount, r.tenure_months, r.installments_paid, r.maturity_amount, r.interest_rate
            FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id
            WHERE r.status = 'ACTIVE'
            ORDER BY r.rd_id ASC
        """)
        
        if active_rds_close:
            rd_close_dict = {f"RD ID: {r[0]} - {r[1]} (Paid: {r[4]}/{r[3]}, Est. Maturity: ₹{r[5]:,.2f})": r for r in active_rds_close}
            col_rc1, col_rc2 = st.columns(2)
            with col_rc1:
                selected_rd_str = st.selectbox("Select RD to Close", list(rd_close_dict.keys()), key="rd_close_select")
            with col_rc2:
                rd_close_date = st.date_input("Closing Date", value=date.today(), format="DD-MM-YYYY", key="rd_close_date_input")
                
            selected_rd = rd_close_dict[selected_rd_str]
            rd_id, cust_name, monthly_amt, tenure_m, paid_inst, maturity_amt, interest_rate = selected_rd
            
            if paid_inst < tenure_m:
                st.warning(f"⚠️ Only {paid_inst} out of {tenure_m} installments paid. Early closure will calculate quarterly compounded interest on installments paid so far.")
                total_paid, prorated_maturity, prorated_interest = calculate_rd_accrued_value(monthly_amt, interest_rate, paid_inst)
                st.info(f"**Prorated Maturity Amount (Quarterly Compounded):** ₹{prorated_maturity:,.2f} (Principal: ₹{total_paid:,.2f} + Interest: ₹{prorated_interest:,.2f})")
                maturity_amount_to_pay = prorated_maturity
            else:
                maturity_amount_to_pay = maturity_amt
                st.success(f"All installments paid. Full maturity amount: ₹{maturity_amt:,.2f}")
            
            total_paid = monthly_amt * paid_inst
            interest_earned = maturity_amount_to_pay - total_paid
            st.info(f"Interest Earned: ₹{interest_earned:,.2f}")
            
            if st.button("Close RD", type="primary", use_container_width=True):
                close_date_str = rd_close_date.strftime("%Y-%m-%d")
                run_query("""
                    UPDATE recurring_deposits 
                    SET status = 'CLOSED', closed_date = ?, maturity_amount = ?
                    WHERE rd_id = ?
                """, (close_date_str, maturity_amount_to_pay, rd_id), fetch=False)
                
                post_automated_jv(f"RD #{rd_id} Maturity - Transfer to SB Deposits Control", "LIA-103", "LIA-101", maturity_amount_to_pay, voucher_date=close_date_str)
                
                if interest_earned > 0:
                    post_automated_jv(f"RD #{rd_id} Interest Expense", "EXP-103", "LIA-103", interest_earned, voucher_date=close_date_str)
                
                clear_db_cache()
                flash_success(f"RD #{rd_id} closed successfully on {close_date_str}! Amount transferred to SB Deposits Control")
                st.rerun()
        else:
            st.info("No active RDs available to close.")

    with tab6:
        st.subheader("✏️ Edit & Correct Recurring Deposit Account")
        st.caption("Enter the exact amount paid/deposited, tenure in days, and interest rate — maturity amount recalculates live on whatever amount you enter.")
        
        all_rds_edit = cached_query("""
            SELECT r.rd_id, c.name, r.monthly_amount, r.tenure_months, r.interest_rate, 
                   r.installments_paid, r.nominee, r.status, r.created_at, r.maturity_amount,
                   COALESCE(r.rd_no, 'RD-' || CAST(r.rd_id AS TEXT)) as rd_no,
                   COALESCE(r.scheme_name, 'SWAYAMVARA KSHEMANIDHI') as scheme_name,
                   COALESCE(r.maturity_date, '2026-12-20') as maturity_date,
                   COALESCE(r.collected_balance, r.monthly_amount * r.installments_paid) as collected_balance,
                   r.customer_id, r.closed_date, COALESCE(r.payment_mode, 'Union Bank of India') as payment_mode,
                   COALESCE(r.tenure_days, r.tenure_months * 30) as tenure_days
            FROM recurring_deposits r 
            JOIN customers c ON r.customer_id = c.id
            ORDER BY r.rd_id DESC
        """)
        
        if all_rds_edit:
            rd_edit_dict = {}
            for r in all_rds_edit:
                status_icon = "🔴 CLOSED" if r[7] == 'CLOSED' else "🟢 ACTIVE"
                label = f"A/C: {r[10]} - {r[1]} ({r[11]} | Amount Paid: ₹{r[13]:,.2f} | Tenure: {r[17]} Days [{r[3]}M]) - {status_icon}"
                rd_edit_dict[label] = r
            
            selected_edit_label = st.selectbox("Select RD Account to Edit", list(rd_edit_dict.keys()), key="rd_edit_select")
            curr_rd = rd_edit_dict[selected_edit_label]
            
            c_rd_id, c_name, c_monthly, c_tenure, c_rate, c_paid, c_nominee, c_status, c_created, c_maturity, c_rd_no, c_scheme, c_mat_date, c_col_bal, c_cust_id, c_closed, c_pm, c_tenure_days = curr_rd
            
            customers_all = cached_query("""
                SELECT c.id, c.name, COALESCE(c.account_no, '') 
                FROM customers c 
                ORDER BY c.name ASC, c.id ASC
            """)
            cust_all_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers_all}
            cust_idx = list(cust_all_dict.values()).index(c_cust_id) if c_cust_id in cust_all_dict.values() else 0
            
            try:
                c_created_dt = pd.to_datetime(c_created).date() if c_created else date.today()
            except Exception:
                c_created_dt = date.today()
                
            try:
                c_mat_dt = pd.to_datetime(c_mat_date).date() if c_mat_date else (c_created_dt + timedelta(days=int(c_tenure_days or (c_tenure * 30))))
            except Exception:
                c_mat_dt = date.today() + timedelta(days=365)
                
            try:
                c_closed_dt = pd.to_datetime(c_closed).date() if c_closed else date.today()
            except Exception:
                c_closed_dt = date.today()

            rd_op_bal_res = cached_query("SELECT voucher_date FROM journal_vouchers WHERE (narration LIKE ? OR narration LIKE ? OR narration LIKE ?) ORDER BY jv_id ASC LIMIT 1", (f"%RD #{c_rd_id}%", f"%{c_rd_no}%", f"%RD Opening%Customer {c_cust_id}%"))
            try:
                rd_op_bal_dt = pd.to_datetime(rd_op_bal_res[0][0]).date() if rd_op_bal_res and rd_op_bal_res[0][0] else c_created_dt
            except Exception:
                rd_op_bal_dt = c_created_dt

            st.markdown("---")
            subtab_rd1, subtab_rd2 = st.tabs(["⚙️ RD Master Account Details", "📋 Edit / Delete Individual Installments"])
            
            with subtab_rd1:
                col_e1, col_e2 = st.columns(2)
                
                with col_e1:
                    edit_rd_no = st.text_input("RD Account Number", value=str(c_rd_no), key=f"edit_rd_no_{c_rd_id}")
                    edit_rd_cust_label = st.selectbox("Assigned Customer", list(cust_all_dict.keys()), index=cust_idx, key=f"edit_rd_cust_{c_rd_id}")
                    edit_rd_cust_id = cust_all_dict[edit_rd_cust_label]
                    edit_scheme = st.text_input("Scheme Name", value=str(c_scheme), key=f"edit_scheme_{c_rd_id}")
                    edit_col_balance = st.number_input(
                        "💰 Total Amount Paid / Deposited (₹)", 
                        min_value=0.0, 
                        value=float(c_col_bal) if c_col_bal is not None else float(c_monthly * c_paid), 
                        step=1000.0, 
                        key=f"edit_col_bal_{c_rd_id}",
                        help="Enter whatever total amount the customer has paid (e.g. ₹12,25,000.00)"
                    )
                    edit_monthly = st.number_input("Monthly Installment (₹)", min_value=0.0, value=float(c_monthly), step=500.0, key=f"edit_monthly_{c_rd_id}")
                
                with col_e2:
                    edit_tenure_days = st.number_input("Tenure (Days)", min_value=1, max_value=3650, value=int(c_tenure_days or (c_tenure * 30)), step=10, key=f"edit_tenure_days_{c_rd_id}")
                    edit_tenure = max(1, int(round(edit_tenure_days / 30.0)))
                    st.caption(f"🗓️ Equivalent Tenure: ~**{edit_tenure} Months** ({edit_tenure_days} Days)")
                    edit_rate = st.number_input("Interest Rate (% p.a.)", min_value=0.0, max_value=30.0, value=float(c_rate), step=0.25, key=f"edit_rate_{c_rd_id}")
                    edit_paid = st.number_input("Installments Paid Count", min_value=0, max_value=max(10000, int(c_paid) + 500), value=int(c_paid), step=1, key=f"edit_paid_{c_rd_id}")
                    edit_nominee = st.text_input("Nominee Name", value=str(c_nominee) if c_nominee else "", key=f"edit_nominee_{c_rd_id}")
                
                col_e3, col_e4 = st.columns(2)
                with col_e3:
                    edit_status = st.selectbox("Account Status", ["ACTIVE", "CLOSED"], index=0 if c_status == 'ACTIVE' else 1, key=f"edit_status_{c_rd_id}")
                    edit_created = st.date_input("A/c Opening Date", value=c_created_dt, format="DD-MM-YYYY", key=f"edit_created_{c_rd_id}")
                    edit_op_bal_date = st.date_input("Opening Balance Date", value=rd_op_bal_dt, format="DD-MM-YYYY", key=f"edit_op_bal_{c_rd_id}")
                    
                    rd_asset_opts = {"AST-102 - Union Bank of India": "AST-102", "AST-101 - Cash in Hand": "AST-101", "AST-103 - State Bank of India": "AST-103"}
                    rd_pm_idx = 0
                    if "cash" in str(c_pm).lower(): rd_pm_idx = 1
                    elif "sbi" in str(c_pm).lower() or "state bank" in str(c_pm).lower(): rd_pm_idx = 2
                    edit_rd_asset_lbl = st.selectbox("Funding / Settlement Asset Mode", list(rd_asset_opts.keys()), index=rd_pm_idx, key=f"edit_rd_asset_{c_rd_id}")
                    edit_rd_asset_code = rd_asset_opts[edit_rd_asset_lbl]
                    edit_rd_pay_mode = edit_rd_asset_lbl.split(" - ")[1]
                with col_e4:
                    edit_mat_date = st.date_input("Maturity Date", value=c_mat_dt, format="DD-MM-YYYY", key=f"edit_mat_date_{c_rd_id}")
                    if edit_status == 'CLOSED':
                        edit_closed_date = st.date_input("Closed Date", value=c_closed_dt, format="DD-MM-YYYY", key=f"edit_closed_date_{c_rd_id}")
                    else:
                        edit_closed_date = None

                # --- Live Automatic Recalculation Engine ---
                calc_full_dep, calc_full_maturity, calc_full_interest = calculate_rd_maturity(edit_monthly, edit_rate, int(edit_tenure))
                calc_acc_paid, calc_acc_maturity, calc_acc_interest = calculate_rd_accrued_value(edit_monthly, edit_rate, int(edit_paid))
                
                st.markdown("---")
                st.markdown("#### ⚡ Live Maturity Amount Selection")
                
                calc_options = []
                calc_options.append(f"🏦 Full Tenure Banking Maturity: ₹{calc_full_maturity:,.2f} (Deposits: ₹{calc_full_dep:,.2f} + Interest: ₹{calc_full_interest:,.2f})")
                if edit_paid < edit_tenure and edit_paid > 0:
                    calc_options.append(f"📊 Accrued Value for {int(edit_paid)} Paid Installments: ₹{calc_acc_maturity:,.2f} (Paid: ₹{calc_acc_paid:,.2f} + Interest: ₹{calc_acc_interest:,.2f})")
                if c_maturity and float(c_maturity) > 0 and round(float(c_maturity), 2) != calc_full_maturity:
                    calc_options.append(f"📄 Keep Currently Stored Amount: ₹{float(c_maturity):,.2f}")
                calc_options.append("✍️ Enter Custom Manual Maturity Amount")
                
                calc_method = st.radio(
                    "Select Maturity Amount Calculation",
                    calc_options,
                    index=1 if (edit_status == 'CLOSED' or edit_paid < edit_tenure) else 0,
                    key=f"calc_method_{c_rd_id}"
                )
                
                if "Full Tenure Banking Maturity" in calc_method:
                    final_maturity_amt = calc_full_maturity
                    final_interest = calc_full_interest
                    disp_principal = calc_full_dep
                elif "Accrued Value" in calc_method:
                    final_maturity_amt = calc_acc_maturity
                    final_interest = calc_acc_interest
                    disp_principal = calc_acc_paid
                elif "Keep Currently Stored" in calc_method:
                    final_maturity_amt = float(c_maturity)
                    final_interest = max(0.0, final_maturity_amt - edit_col_balance)
                    disp_principal = edit_col_balance
                else:
                    final_maturity_amt = st.number_input(
                        "Enter Custom Maturity Amount (₹)",
                        min_value=0.0,
                        value=float(c_maturity) if c_maturity else calc_full_maturity,
                        step=1000.0,
                        key=f"custom_mat_amt_{c_rd_id}"
                    )
                    final_interest = max(0.0, final_maturity_amt - edit_col_balance)
                    disp_principal = edit_col_balance
                
                m_col1, m_col2, m_col3 = st.columns(3)
                m_col1.metric("💰 Expected / Paid Principal", f"₹{disp_principal:,.2f}")
                m_col2.metric("📈 Calculated Interest", f"₹{final_interest:,.2f}")
                m_col3.metric("🎯 Total Maturity Amount", f"₹{final_maturity_amt:,.2f}")
                
                st.markdown("<br>", unsafe_allow_html=True)
                btn_col1, btn_col2, btn_col3 = st.columns([2.5, 1.5, 1])
                
                with btn_col1:
                    if st.button("💾 Save & Sync RD Account (Update Ledgers, JVs & Books)", key=f"btn_save_rd_{c_rd_id}", use_container_width=True, type="primary"):
                        edit_created_str = edit_created.strftime("%Y-%m-%d")
                        edit_op_bal_str = edit_op_bal_date.strftime("%Y-%m-%d")
                        edit_mat_str = edit_mat_date.strftime("%Y-%m-%d")
                        closed_date_val = edit_closed_date.strftime("%Y-%m-%d") if (edit_status == 'CLOSED' and edit_closed_date) else (datetime.now(IST).strftime("%Y-%m-%d") if edit_status == 'CLOSED' else None)
                        
                        success, msg = update_rd_account_details(
                            c_rd_id, edit_rd_cust_id, edit_rd_no, edit_monthly, edit_tenure, edit_rate,
                            edit_paid, edit_col_balance, edit_nominee, edit_status,
                            edit_created_str, closed_date_val, edit_rd_pay_mode, edit_rd_asset_code,
                            new_op_bal_date=edit_op_bal_str, new_tenure_days=edit_tenure_days
                        )
                        
                        run_query("""
                            UPDATE recurring_deposits 
                            SET scheme_name = ?,
                                maturity_date = ?,
                                maturity_amount = ?,
                                tenure_days = ?,
                                tenure_months = ?
                            WHERE rd_id = ?
                        """, (edit_scheme, edit_mat_str, final_maturity_amt, edit_tenure_days, edit_tenure, c_rd_id), fetch=False)
                        
                        clear_db_cache()
                        if success:
                            flash_success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to update RD: {msg}")
                
                with btn_col2:
                    if st.button("🔄 Resequence This RD Account", key=f"btn_reseq_rd_master_{c_rd_id}", use_container_width=True):
                        success, msg = resequence_rd_installments(c_rd_id)
                        clear_db_cache()
                        if success:
                            flash_success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to resequence: {msg}")

                with btn_col3:
                    with st.popover("🗑️ Delete RD"):
                        st.error(f"Are you sure you want to delete RD #{edit_rd_no}?")
                        st.caption("This will delete the RD and resequence without gaps.")
                        if st.button("Confirm Delete Permanently", key=f"btn_del_rd_{c_rd_id}", type="primary", use_container_width=True):
                            success, msg = delete_rd_entry(c_rd_id)
                            clear_db_cache()
                            if success:
                                flash_success(f"✅ {msg}")
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to delete RD: {msg}")

            with subtab_rd2:
                st.markdown("### 📋 Manage & Correct Individual RD Installments")
                st.caption(f"View, correct wrong dates/amounts, or delete installments specifically for Account **{c_rd_no}** ({c_name}):")
                
                res_col1, res_col2 = st.columns(2)
                with res_col1:
                    if st.button("🔄 Resequence Current RD Installments (Opening First, Latest Last)", key=f"btn_reseq_rd_inst_{c_rd_id}", use_container_width=True):
                        success, msg = resequence_rd_installments(c_rd_id)
                        clear_db_cache()
                        if success:
                            flash_success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to resequence: {msg}")
                with res_col2:
                    if st.button("🌐 Resequence ALL RDs Globally (All Accounts)", key=f"btn_reseq_all_rds_inst_{c_rd_id}", use_container_width=True):
                        success, msg = resequence_rd_installments(None)
                        clear_db_cache()
                        if success:
                            flash_success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to resequence: {msg}")
                
                st.markdown("<br>", unsafe_allow_html=True)
                inst_list = ensure_rd_installments_populated(c_rd_id)
                if inst_list:
                    df_inst = pd.DataFrame(inst_list, columns=["ID", "Inst No", "Payment Date", "Particulars", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Mode", "Voucher No", "Narration"])
                    df_inst_formatted = format_df_dates(df_inst)
                    st.dataframe(df_inst_formatted, use_container_width=True)
                    
                    st.markdown("---")
                    st.markdown("#### ✏️ Select Installment to Edit or Delete")
                    
                    inst_dict = {}
                    for row in inst_list:
                        i_id, i_no, i_pdate, i_part, i_dr, i_cr, i_bal, i_pmode, i_vno, i_narr = row
                        i_lbl = f"Inst #{i_no} | Date: {pdf_generator.format_date_str(i_pdate)} | ₹{i_cr:,.2f} | {i_pmode} (Voucher: {i_vno} | ID: {i_id})"
                        inst_dict[i_lbl] = row
                        
                    chosen_inst_lbl = st.selectbox("Choose Installment", list(inst_dict.keys()), key=f"sel_inst_edit_{c_rd_id}")
                    chosen_inst_row = inst_dict[chosen_inst_lbl]
                    
                    c_inst_id, c_inst_no, c_pdate, c_part, c_dr, c_cr, c_bal, c_pmode, c_vno, c_narr = chosen_inst_row
                    
                    try:
                        c_pdate_dt = pd.to_datetime(c_pdate).date() if c_pdate else date.today()
                    except Exception:
                        c_pdate_dt = date.today()
                        
                    col_ie1, col_ie2 = st.columns(2)
                    with col_ie1:
                        new_inst_date = st.date_input("Correct Payment Date", value=c_pdate_dt, format="DD-MM-YYYY", key=f"edit_pdate_{c_inst_id}")
                        new_inst_no = st.text_input("Installment No / Reference", value=str(c_inst_no), key=f"edit_instno_{c_inst_id}")
                        new_inst_cr = st.number_input("Credit / Deposit Amount (₹)", min_value=0.0, value=float(c_cr), step=500.0, key=f"edit_cr_{c_inst_id}")
                    with col_ie2:
                        pmode_opts = ["Union Bank of India (NEFT / UPI)", "Cash in Hand (Office Drawer)", "State Bank of India"]
                        pmode_idx = 0
                        if "cash" in str(c_pmode).lower(): pmode_idx = 1
                        elif "sbi" in str(c_pmode).lower() or "state bank" in str(c_pmode).lower(): pmode_idx = 2
                        new_inst_pmode = st.selectbox("Payment Mode", pmode_opts, index=pmode_idx, key=f"edit_pmode_{c_inst_id}")
                        new_inst_part = st.text_input("Particulars", value=str(c_part), key=f"edit_part_{c_inst_id}")
                        new_inst_narr = st.text_input("Narration / Remarks", value=str(c_narr), key=f"edit_narr_{c_inst_id}")
                        
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_ib1, col_ib2 = st.columns([3, 1])
                    with col_ib1:
                        if st.button("💾 Save Installment Changes", key=f"btn_save_inst_{c_inst_id}", type="primary", use_container_width=True):
                            pmode_name = "Union Bank of India" if "Union" in new_inst_pmode else ("Cash" if "Cash" in new_inst_pmode else "State Bank of India")
                            success, msg = update_rd_installment(
                                c_inst_id, c_rd_id, new_inst_date, new_inst_cr, pmode_name, new_inst_part, new_inst_narr, installment_no=new_inst_no
                            )
                            clear_db_cache()
                            if success:
                                flash_success(f"✅ Installment {new_inst_no} updated successfully on {new_inst_date.strftime('%d-%m-%Y')}!")
                                st.rerun()
                            else:
                                st.error(f"❌ Error updating installment: {msg}")
                    with col_ib2:
                        with st.popover("🗑️ Delete Installment"):
                            st.error(f"Delete Installment #{c_inst_no} ({pdf_generator.format_date_str(c_pdate)} - ₹{c_cr:,.2f})?")
                            st.caption("This will remove the installment row, reverse cash/bank vouchers, and update running balances.")
                            if st.button("Confirm Delete", key=f"btn_del_inst_{c_inst_id}", type="primary", use_container_width=True):
                                success, msg = delete_rd_installment(c_inst_id, c_rd_id)
                                clear_db_cache()
                                if success:
                                    flash_success(f"✅ {msg}")
                                    st.rerun()
                                else:
                                    st.error(f"❌ Error deleting installment: {msg}")
                else:
                    st.info("No installments recorded for this RD account yet.")
                    
                st.markdown("---")
                with st.expander("➕ Add Past / Missed Installment Entry"):
                    st.caption("Manually insert a missed installment or missed opening balance for a past date with automatic voucher and chronological ledger generation.")
                    entry_kind = st.radio(
                        "Entry Category",
                        ["Regular Monthly Installment", "Opening Balance Deposit", "Prior Installments"],
                        horizontal=True,
                        key=f"add_entry_kind_{c_rd_id}"
                    )
                    
                    col_ai1, col_ai2 = st.columns(2)
                    if entry_kind == "Regular Monthly Installment":
                        with col_ai1:
                            add_inst_no = st.text_input("Installment No", value=str(int(c_paid) + 1), key=f"add_inst_no_{c_rd_id}")
                            add_inst_date = st.date_input("Installment Date", value=date.today(), format="DD-MM-YYYY", key=f"add_inst_date_{c_rd_id}")
                            add_inst_amt = st.number_input("Amount (₹)", min_value=0.0, value=float(c_monthly), step=500.0, key=f"add_inst_amt_{c_rd_id}")
                        with col_ai2:
                            add_inst_pmode = st.selectbox("Payment Mode", ["Union Bank of India (NEFT / UPI)", "Cash in Hand (Office Drawer)", "State Bank of India"], key=f"add_inst_pmode_{c_rd_id}")
                            add_inst_part = st.text_input("Particulars", value=f"Installment #{add_inst_no} Deposit", key=f"add_inst_part_{c_rd_id}")
                            add_inst_narr = st.text_input("Narration", value=f"RD Installment #{add_inst_no}", key=f"add_inst_narr_{c_rd_id}")
                    else:
                        with col_ai1:
                            try:
                                default_op_date = pd.to_datetime(c_created).date() if c_created else date.today()
                            except Exception:
                                default_op_date = date.today()
                            add_inst_date = st.date_input("Opening Balance Date", value=default_op_date, format="DD-MM-YYYY", key=f"add_op_date_{c_rd_id}")
                            op_inst_covered = st.number_input("Number of Prior Installments Covered", min_value=1, max_value=10000, value=1, step=1, key=f"add_op_covered_{c_rd_id}")
                            def_op_amt = float(op_inst_covered * c_monthly)
                            add_inst_amt = st.number_input("Opening Balance Amount (₹)", min_value=0.0, value=def_op_amt, step=500.0, key=f"add_op_amt_{c_rd_id}")
                            def_op_ino = f"1 to {op_inst_covered}" if op_inst_covered > 1 else "1"
                            add_inst_no = st.text_input("Installment Reference", value=def_op_ino, key=f"add_op_ino_{c_rd_id}")
                        with col_ai2:
                            add_inst_pmode = st.selectbox("Payment Mode", ["Union Bank of India (NEFT / UPI)", "Cash in Hand (Office Drawer)", "State Bank of India"], key=f"add_op_pmode_{c_rd_id}")
                            def_op_part = f"RD Opening Balance ({op_inst_covered} Installments)" if op_inst_covered > 1 else "RD Opening Balance"
                            add_inst_part = st.text_input("Particulars", value=def_op_part, key=f"add_op_part_{c_rd_id}")
                            add_inst_narr = st.text_input("Narration", value=f"RD Opening Balance - {op_inst_covered} Inst.", key=f"add_op_narr_{c_rd_id}")
                        
                    if st.button("➕ Record Missed Entry", key=f"btn_add_missed_inst_{c_rd_id}", type="primary", use_container_width=True):
                        pm_str = "Union Bank of India" if "Union" in add_inst_pmode else ("Cash" if "Cash" in add_inst_pmode else "State Bank of India")
                        success, msg = add_custom_rd_installment(
                            c_rd_id, add_inst_no, add_inst_date, add_inst_amt, pm_str, add_inst_part, add_inst_narr
                        )
                        clear_db_cache()
                        if success:
                            flash_success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ Error adding entry: {msg}")
        else:
            st.info("No Recurring Deposits available to edit.")


def get_next_account_code(account_type):
    prefix_map = {
        "Asset": "AST",
        "Liability": "LIA",
        "Income": "INC",
        "Expense": "EXP",
        "Equity": "EQT"
    }
    prefix = prefix_map.get(account_type, "ACC")
    
    # Query all account codes starting with prefix
    result = run_query("SELECT account_code FROM chart_of_accounts WHERE account_code LIKE ? ORDER BY account_code DESC", (f"{prefix}-%",))
    
    if not result:
        return f"{prefix}-101"
        
    # We find the highest numeric suffix
    max_num = 100
    for row in result:
        code = row[0]
        try:
            parts = code.split("-")
            if len(parts) == 2:
                num = int(parts[1])
                if num > max_num:
                    max_num = num
        except ValueError:
            continue
            
    return f"{prefix}-{max_num + 1}"


def render_chart_of_accounts():
    st.title("🗂️ Chart of Accounts Management")
    tab_coa1, tab_coa2 = st.tabs(["📋 View & Delete Accounts", "➕ Add / Edit Account Head"])

    with tab_coa1:
        st.subheader("Existing Accounts Directory")
        accounts = cached_query("SELECT account_code, account_name, account_type, category FROM chart_of_accounts ORDER BY account_code")
        if accounts:
            df_coa = pd.DataFrame(accounts, columns=["Account Code", "Account Name", "Account Type", "Category"])
            st.dataframe(df_coa, use_container_width=True)

            # Option to manually trigger resequencing of all accounts to resolve gaps
            st.markdown('<div class="resequence-btn-container">', unsafe_allow_html=True)
            if st.button("🛠️ Force Resequence Database & Accounts (Enforce strict gapless order)", use_container_width=True):
                try:
                    success, msg = resequence_entire_database()
                    if success:
                        flash_success("Resequenced Chart of Accounts, Customers, Loans, Deposits, Cash & Bank Books successfully! All IDs and account codes are in strict sequential order.")
                    else:
                        flash_error(f"Resequencing error: {msg}")
                    st.rerun()
                except Exception as ex:
                    st.error(f"❌ Resequencing error: {str(ex)}")
            st.markdown('</div>', unsafe_allow_html=True)

            st.divider()
            st.subheader("🗑️ Delete Account Head")
            del_code = st.selectbox("Select Account Code to Delete", df_coa["Account Code"].tolist())
            if st.button("Delete Account Head", type="primary", use_container_width=True):
                try:
                    from database import resequence_all_accounts, reconcile_books
                    run_query("DELETE FROM chart_of_accounts WHERE account_code = ?", (del_code,), fetch=False)
                    resequence_all_accounts()
                    reconcile_books()
                    clear_db_cache()
                    flash_success(f"✅ Successfully deleted account code: {del_code} and resequenced accounts!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Could not delete account. Error: {e}")
        else:
            st.info("No records found in the Chart of Accounts.")

    with tab_coa2:
        st.subheader("Create or Update Account Head")
        
        # Render Account Type selection outside the form to compute next suggested code dynamically
        input_type = st.selectbox("Account Type", ["Income", "Expense", "Asset", "Liability", "Equity"], key="coa_input_type")
        suggested_code = get_next_account_code(input_type)
        
        with st.form("coa_upsert_form"):
            col1, col2 = st.columns(2)
            input_code = col1.text_input("Account Code (Suggested/Custom)", value=suggested_code, help="Auto-assigned based on selection. You can override if needed.").upper().strip()
            input_name = col2.text_input("Account Name (e.g., Special Service Income)")
            input_category = col2.text_input("Category (e.g., Operating Expenses, Current Assets)")
            
            submitted = st.form_submit_button("Save / Update Account Head", use_container_width=True)
            if submitted:
                if not input_code or not input_name or not input_category:
                    st.warning("Please fill out all fields.")
                else:
                    try:
                        if USING_SUPABASE:
                            run_query(
                                """
                                INSERT INTO chart_of_accounts (account_code, account_name, account_type, category) 
                                VALUES (?, ?, ?, ?)
                                ON CONFLICT (account_code) DO UPDATE 
                                SET account_name = EXCLUDED.account_name, account_type = EXCLUDED.account_type, category = EXCLUDED.category
                                """,
                                (input_code, input_name, input_type, input_category),
                                fetch=False
                            )
                        else:
                            run_query(
                                "INSERT OR REPLACE INTO chart_of_accounts (account_code, account_name, account_type, category) VALUES (?, ?, ?, ?)",
                                (input_code, input_name, input_type, input_category),
                                fetch=False
                            )
                        clear_db_cache()
                        flash_success(f"Account head '{input_code} - {input_name}' saved successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving account entry: {e}")

def render_cash_book():
    st.title("💰 Cash Book Entries")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Record Entry", "View / Delete", "Edit Entry", "Print Book", "🖨️ Print CB Vouchers"])
    
    with tab1:
        from database import get_all_balances
        current_cash_balance, current_union_balance, current_sbi_balance = get_all_balances()
        
        st.info(f"💰 **Current Cash Balance:** ₹{current_cash_balance:,.2f}")
        st.info(f"🏦 **Union Bank Balance:** ₹{current_union_balance:,.2f} | **SBI Balance:** ₹{current_sbi_balance:,.2f}")
        
        is_opening = st.checkbox("Is this an Opening Balance?")
        with st.form("cash_entry_form"):
            col1, col2, col3 = st.columns(3)
            tx_date = col2.date_input("Transaction Date", date.today(), format="DD-MM-YYYY")
            amount = col3.number_input("Amount (₹)", min_value=1.0, value=100.0, step=100.0)
            
            if is_opening:
                entry_type = col1.selectbox("Transaction Type", ["DEBIT (Receipt)"], index=0, disabled=True)
                particulars = st.text_input("Particulars / Description", value="Opening Balance")
            else:
                entry_type = col1.selectbox("Transaction Type", ["DEBIT (Receipt)", "CREDIT (Payment)"])
                particulars = st.text_input("Particulars / Description")
                
            coa_list = cached_query("SELECT account_code, account_name FROM chart_of_accounts ORDER BY account_code")
            coa_dict = {f"{c[0]} - {c[1]}": c[0] for c in coa_list}
            
            if is_opening:
                default_coa_head = next((k for k in coa_dict.keys() if k.startswith("EQT-101") or k.startswith("EQT-102")), list(coa_dict.keys())[0])
                account_head = st.selectbox("Corresponding Account Head (Equity/Capital)", [default_coa_head], disabled=True)
            else:
                account_head = st.selectbox("Corresponding Account Head", list(coa_dict.keys()))
                
            narration = st.text_area("Narration", height=68)
            
            if st.form_submit_button("Record Cash Entry", use_container_width=True):
                if amount > 0 and particulars and account_head:
                    account_code = coa_dict[account_head]
                    
                    # Determine full JV narration including text-area narration
                    full_narration = particulars
                    if narration.strip():
                        full_narration += f" ({narration.strip()})"

                    if entry_type == "CREDIT (Payment)":
                        if current_cash_balance < amount:
                            st.warning(f"⚠️ Cash Balance Alert: Current Cash Balance is ₹{current_cash_balance:,.2f}. Recording this payment of ₹{amount:,.2f} will adjust the cash balance.")
                        if account_code == 'AST-101':
                            st.error("❌ Cannot transfer cash to itself!")
                            st.stop()
                    
                    elif entry_type == "DEBIT (Receipt)":
                        if account_code == 'AST-101':
                            st.error("❌ Cannot receipt cash from itself!")
                            st.stop()
                    
                    from database import record_cash_book_transaction
                    success, res_val = record_cash_book_transaction(entry_type, amount, account_code, particulars, narration, tx_date)
                    if success:
                        flash_success(f"✅ Cash entry recorded! Voucher: {res_val}")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to record cash entry: {res_val}")

    with tab2:
        min_cb_d = cached_query("SELECT MIN(date) FROM cash_book")
        max_cb_d = cached_query("SELECT MAX(date) FROM cash_book")
        cb_default_from = datetime.strptime(min_cb_d[0][0], "%Y-%m-%d").date() if (min_cb_d and min_cb_d[0] and min_cb_d[0][0]) else (date.today() - timedelta(days=365))
        cb_default_to = datetime.strptime(max_cb_d[0][0], "%Y-%m-%d").date() if (max_cb_d and max_cb_d[0] and max_cb_d[0][0]) else date.today()
        if cb_default_to < date.today():
            cb_default_to = date.today()
        
        col_date1, col_date2 = st.columns(2)
        from_date = col_date1.date_input("From Date", value=cb_default_from, key="cb_view_from", format="DD-MM-YYYY")
        to_date = col_date2.date_input("To Date", value=cb_default_to, key="cb_view_to", format="DD-MM-YYYY")
        
        entries = cached_query("""
            SELECT cb.id, cb.date, cb.voucher_no, 
                   COALESCE(co.account_code || ' - ' || co.account_name, cb.account_code) as account_head,
                   cb.particulars, cb.debit_amount, cb.credit_amount, cb.balance, cb.narration 
            FROM cash_book cb
            LEFT JOIN chart_of_accounts co ON cb.account_code = co.account_code
            WHERE cb.date BETWEEN ? AND ? 
            ORDER BY cb.date ASC, cb.id ASC
        """, (str(from_date), str(to_date)))
        if entries:
            df_cash = pd.DataFrame(entries, columns=["ID", "Date", "Voucher No", "Account Head", "Particulars", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Narration"])
            df_cash.insert(0, "Sl No", range(1, len(df_cash) + 1))
            
            # Key Financial Metrics (Opening Balance First, Closing Balance Last)
            m1, m2, m3, m4 = st.columns(4)
            first_row = df_cash.iloc[0]
            last_row = df_cash.iloc[-1]
            op_bal = first_row["Balance (₹)"] if "Opening" in str(first_row["Particulars"]) else (first_row["Balance (₹)"] - first_row["Debit (₹)"] + first_row["Credit (₹)"])
            m1.metric("🏁 Opening Balance", f"₹{op_bal:,.2f}")
            m2.metric("📥 Total Receipts (Dr)", f"₹{df_cash['Debit (₹)'].sum():,.2f}")
            m3.metric("📤 Total Payments (Cr)", f"₹{df_cash['Credit (₹)'].sum():,.2f}")
            m4.metric("🏁 Closing Balance", f"₹{last_row['Balance (₹)']:,.2f}")
            
            st.dataframe(format_df_dates(df_cash), use_container_width=True)
            
            c_del1, c_del2 = st.columns([3, 1])
            with c_del1:
                del_id = st.number_input("Enter Cash Entry ID to Delete", min_value=1, step=1, key="del_cash_id")
                if st.button("Delete Cash Entry", use_container_width=True):
                    success, msg = delete_cash_book_entry(del_id)
                    if success:
                        flash_warning(msg)
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
            with c_del2:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("🔄 Resequence All IDs", key="reseq_cb_btn", help="Recalculates all Cash Book IDs sequentially from 1 to N without gaps and updates running balances", use_container_width=True):
                    success, msg = resequence_cash_book()
                    if success:
                        flash_success("✅ Cash Book resequenced and running balances verified!")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
        else:
            st.info("No cash book entries found in this date range.")

    with tab3:
        st.subheader("Edit Existing Cash Entry")
        edit_id = st.number_input("Enter Cash Entry ID to Edit", min_value=1, step=1, key="edit_cash_id_input")
        entry_to_edit = cached_query("SELECT id, particulars, debit_amount, credit_amount, narration, account_code, voucher_no, date FROM cash_book WHERE id=?", (edit_id,))
        
        if entry_to_edit:
            row = entry_to_edit[0]
            # row = (id, particulars, debit_amount, credit_amount, narration, account_code, voucher_no, date)
            coa_list = cached_query("SELECT account_code, account_name FROM chart_of_accounts ORDER BY account_code")
            coa_dict = {f"{c[0]} - {c[1]}": c[0] for c in coa_list}
            coa_keys = list(coa_dict.keys())
            
            curr_acc = row[5]
            default_index = 0
            for idx, k in enumerate(coa_keys):
                if coa_dict[k] == curr_acc:
                    default_index = idx
                    break
                    
            with st.form("edit_cash_form"):
                col_d, col_t, col_a = st.columns(3)
                edit_date = col_d.date_input("Date", value=datetime.strptime(row[7], "%Y-%m-%d").date() if row[7] else date.today(), format="DD-MM-YYYY")
                curr_dr = row[2] if row[2] > 0 else row[3]
                is_debit = row[2] > 0
                new_type = col_t.selectbox("Type", ["DEBIT (Receipt)", "CREDIT (Payment)"], index=0 if is_debit else 1)
                new_amt = col_a.number_input("Amount (₹)", min_value=1.0, value=float(curr_dr))
                
                new_part = st.text_input("Particulars", value=row[1])
                new_acc_head = st.selectbox("Corresponding Account Head", coa_keys, index=default_index)
                new_narration = st.text_area("Narration", value=row[4] if row[4] else "")
                
                if st.form_submit_button("Update Cash Entry", use_container_width=True):
                    new_acc_code = coa_dict[new_acc_head]
                    voucher_no = row[6]
                    
                    from database import update_cash_book_transaction
                    success, res_val = update_cash_book_transaction(edit_id, new_type, new_amt, new_acc_code, new_part, new_narration, voucher_no, tx_date=edit_date)
                    if success:
                        flash_success("✅ Cash Entry and Ledger updated successfully!")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to update entry: {res_val}")

    with tab4:
        min_cb_d = cached_query("SELECT MIN(date) FROM cash_book")
        max_cb_d = cached_query("SELECT MAX(date) FROM cash_book")
        cb_default_from = datetime.strptime(min_cb_d[0][0], "%Y-%m-%d").date() if (min_cb_d and min_cb_d[0] and min_cb_d[0][0]) else (date.today() - timedelta(days=365))
        cb_default_to = datetime.strptime(max_cb_d[0][0], "%Y-%m-%d").date() if (max_cb_d and max_cb_d[0] and max_cb_d[0][0]) else date.today()
        if cb_default_to < date.today():
            cb_default_to = date.today()

        col_date1, col_date2 = st.columns(2)
        from_date = col_date1.date_input("From Date", value=cb_default_from, key="cb_print_from", format="DD-MM-YYYY")
        to_date = col_date2.date_input("To Date", value=cb_default_to, key="cb_print_to", format="DD-MM-YYYY")
        
        entries = cached_query("""
            SELECT cb.date, cb.voucher_no, 
                   COALESCE(co.account_code || ' - ' || co.account_name, cb.account_code) as account_head,
                   cb.particulars, cb.debit_amount, cb.credit_amount, cb.balance, cb.narration 
            FROM cash_book cb
            LEFT JOIN chart_of_accounts co ON cb.account_code = co.account_code
            WHERE cb.date BETWEEN ? AND ? 
            ORDER BY cb.date ASC, cb.id ASC
        """, (str(from_date), str(to_date)))
        if entries:
            df_print = pd.DataFrame(entries, columns=["Date", "Voucher No", "Account Head", "Particulars", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Narration"])
            df_print.insert(0, "Sl No", range(1, len(df_print) + 1))
            df_print_formatted = format_df_dates(df_print)
            st.dataframe(df_print_formatted, use_container_width=True)
            
            col_dl1, col_dl2, col_dl3 = st.columns(3)
            with col_dl1:
                excel_bytes = pdf_generator.create_excel_report("Cash Book Report", df_print, from_date, to_date)
                st.download_button(
                    "📊 Download Excel (.xlsx)",
                    data=excel_bytes,
                    file_name=f"cash_book_{from_date}_{to_date}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="btn_cb_excel"
                )
            with col_dl2:
                csv_bytes = pdf_generator.create_csv_report("Cash Book Report", df_print_formatted, from_date, to_date)
                st.download_button(
                    "📥 Download CSV (.csv)",
                    data=csv_bytes,
                    file_name=f"cash_book_{from_date}_{to_date}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="btn_cb_csv"
                )
            with col_dl3:
                if st.button("📄 Prepare PDF", key="btn_prep_cb_pdf", use_container_width=True):
                    with st.spinner("Generating PDF report..."):
                        st.session_state.cb_pdf_bytes = pdf_generator.create_pdf_report("Cash Book Report", df_print_formatted)
                if "cb_pdf_bytes" in st.session_state and st.session_state.cb_pdf_bytes:
                    st.download_button("📥 Click to Download PDF", st.session_state.cb_pdf_bytes, f"cash_book_{from_date}_{to_date}.pdf", "application/pdf", use_container_width=True, key="btn_cb_pdf")
        else:
            st.info("No cash book entries found in this date range.")

    with tab5:
        st.subheader("🖨️ Cash Book Voucher (CB) Print")
        col_date1, col_date2 = st.columns(2)
        from_date = col_date1.date_input("From Date", value=date.today() - timedelta(days=30), key="cb_v_from", format="DD-MM-YYYY")
        to_date = col_date2.date_input("To Date", value=date.today(), key="cb_v_to", format="DD-MM-YYYY")
        
        cb_records = cached_query("""
            SELECT voucher_no, particulars, date 
            FROM cash_book 
            WHERE date BETWEEN ? AND ? 
            ORDER BY id DESC
        """, (str(from_date), str(to_date)))
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
                    
                    try:
                        date_display = pd.to_datetime(date_val).strftime('%d-%m-%Y')
                    except Exception:
                        date_display = date_val
                        
                    with st.container(border=True):
                        col1, col2 = st.columns(2)
                        col1.markdown("### **CASH VOUCHER (CB)**")
                        col1.write(f"**Voucher No:** {v_num}")
                        col2.write(f"**Date:** {date_display}")
                        st.divider()
                        st.write(f"**Particulars:** {part}")
                        st.write(f"**Account Head:** {account_display}")
                        if dr > 0:
                            st.write(f"**Debit Amount (Receipt):** ₹{dr:,.2f}")
                        else:
                            st.write(f"**Credit Amount (Payment):** ₹{cr:,.2f}")
                        st.write(f"**Narration:** {narr if narr else 'N/A'}")
                        st.markdown("---")
                        st.caption("Authorized Signature")
                    
                    if st.button(f"🖨️ Prepare Cash Voucher PDF ({v_num})", key=f"btn_prep_cb_{v_num}", use_container_width=True):
                        with st.spinner("Generating Voucher PDF..."):
                            st.session_state[f"cb_v_pdf_{v_num}"] = pdf_generator.generate_voucher_pdf('CB', v_data)
                            
                    if f"cb_v_pdf_{v_num}" in st.session_state:
                        st.download_button(
                            label=f"📥 Download Cash Voucher {v_num} (PDF)",
                            data=st.session_state[f"cb_v_pdf_{v_num}"],
                            file_name=f"Cash_Voucher_{v_num}.pdf",
                            mime="application/pdf",
                            key=f"download_cb_{v_num}",
                            use_container_width=True
                        )

def extract_party_details(particulars, acc_code, acc_name, cust_list):
    if not particulars:
        return 'N/A'
    p = str(particulars).strip()
    
    # 1. Staff Salary & Benefits (EXP-104 or staff withdrawal names)
    staff_names = ['SREEKALA J', 'SASIKUMARAN A', 'BINU B', 'KEERTHI R', 'SREEJITH RADHAKRISHNAN', 'LEKSHMI SK', 'SREEKALA', 'SASIKUMARAN', 'SREEJITH', 'BINU', 'KEERTHI', 'LEKSHMI']
    if acc_code == 'EXP-104' or any(k in p.lower() for k in ['salary', 'salaries', 'staff']):
        for sn in staff_names:
            if re.search(r'\b' + re.escape(sn) + r'\b', p, re.IGNORECASE):
                return f"Staff Salary: {sn}"
        return "Staff Salaries & Benefits"

    # 2. Professional Charges / CA Fees
    if acc_code == 'EXP-106' or 'ca fees' in p.lower() or 'professional' in p.lower() or 'audit' in p.lower():
        m_ca = re.search(r'([A-Za-z\.\s]+?)\s*[-:]\s*CA\s*Fees', p, re.IGNORECASE)
        if m_ca:
            return f"CA Professional Charges: {m_ca.group(1).strip()}"
        return "CA / Professional Charges"

    # 3. Cash Contra / Drawer
    if 'cash' in p.lower() or 'contra' in p.lower() or acc_code == 'AST-101':
        return "Cash Drawer (Office Contra)"
        
    # 4. Bank Charges & Taxes
    if any(k in p.lower() for k in ['sms charge', 'sms charges', 'bank charge', 'bank charges', 'pord', 'gst', 'consolidated chg', 'atm charge', 'transaction charge']):
        return "Union Bank Processing / Service Charges"

    # 5. Office Rent
    if acc_code == 'EXP-105' or 'rent' in p.lower():
        return "Office Rent"

    # 6. Opening Balance
    if 'opening' in p.lower():
        return "Opening Balance"
        
    # 7. Exact Customer Account Number Match (100% certainty)
    for cid, cname, cacc in cust_list:
        if cacc and len(str(cacc).strip()) >= 4 and str(cacc).strip() in p:
            return f"{cname} (Acc: {cacc})"
            
    # 8. Full Customer Name Matching (Strict - NO single-word loose matching)
    sorted_cust = sorted(cust_list, key=lambda c: len(c[1]), reverse=True)
    for cid, cname, cacc in sorted_cust:
        if not cname:
            continue
        c_clean = re.sub(r'\s+', ' ', cname).strip()
        core_words = [w for w in re.split(r'[\s\.]+', c_clean) if len(w) > 1]
        
        # Exact full name match (e.g. "RANJITH R", "PRASAD U")
        if len(c_clean) >= 4 and re.search(r'\b' + re.escape(c_clean) + r'\b', p, re.IGNORECASE):
            acc_label = f" (Acc: {cacc})" if cacc else ""
            return f"{cname}{acc_label}"
            
        # Core full name match with at least 2 full words (e.g. "AJAYA KUMAR")
        if len(core_words) >= 2:
            core_phrase = " ".join(core_words)
            if len(core_phrase) >= 6 and re.search(r'\b' + re.escape(core_phrase) + r'\b', p, re.IGNORECASE):
                acc_label = f" (Acc: {cacc})" if cacc else ""
                return f"{cname}{acc_label}"

    # 9. Clean Literal Party Extraction from Particulars (e.g. Deposit Santhosh Kumar -> Santhosh Kumar)
    m_dep = re.search(r'(?:Saving(?:s)?\s*Deposit(?:\s*&\s*Processing\s*Charge)?|Deposit\s+Suspended|Deposit)\s*[-:\s]+([A-Za-z\s\.]+?)(?:\s*[-:]|\s*$)', p, re.IGNORECASE)
    if m_dep:
        extracted = m_dep.group(1).strip()
        if len(extracted) >= 3 and extracted.lower() not in ['cash', 'liquid', 'savings deposit', 'bank charge', 'office rent', 'opening balance']:
            return extracted

    m_tail = re.search(r'[-:]\s*([A-Za-z\s\.]+)$', p)
    if m_tail:
        extracted = m_tail.group(1).strip()
        if len(extracted) >= 3 and extracted.lower() not in ['savings deposit', 'bank charge', 'office rent', 'professional charges']:
            return extracted

    # 10. UPI Member Name
    upi_match = re.search(r'/CR/([^/]+)/', p, re.IGNORECASE)
    if upi_match:
        name_clean = upi_match.group(1).strip()
        if name_clean and len(name_clean) > 1:
            return f"Member: {name_clean}"
            
    # 11. NEFT Party Name
    neft_match = re.search(r'NEFT(?:O|-|:)?\s*([A-Za-z\s\.]+?)(?:\s+\d+|\s+HDFC|\s+SBIN|\s+CNRB|$)', p, re.IGNORECASE)
    if neft_match:
        n_clean = neft_match.group(1).strip()
        if n_clean and len(n_clean) > 2:
            return f"Party: {n_clean}"
            
    return p


def render_bank_book():
    st.title("🏦 Bank Book Entries")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Record Entry", "View / Delete", "Edit Entry", "Print Book", "🖨️ Print BB Vouchers"])
    
    with tab1:
        bank_code, bank_name = "AST-102", "Union Bank of India"
        current_balance = get_account_balance_from_jv(bank_code)
        st.info(f"🏦 **{bank_name} Current Balance:** ₹{current_balance:,.2f}")
        
        is_opening = st.checkbox("Is this an Opening Balance?", key="bank_is_opening")
        with st.form("bank_entry_form"):
            col1, col2, col3 = st.columns(3)
            tx_date = col2.date_input("Transaction Date", date.today(), format="DD-MM-YYYY")
            amount = col3.number_input("Amount (₹)", min_value=1.0, value=100.0, step=100.0)
            
            if is_opening:
                entry_type = col1.selectbox("Transaction Type", ["DEBIT (Deposit)"], index=0, disabled=True)
                particulars = st.text_input("Particulars / Description", value="Opening Balance")
            else:
                entry_type = col1.selectbox("Transaction Type", ["DEBIT (Deposit)", "CREDIT (Withdrawal)"])
                particulars = st.text_input("Particulars / Description")
                
            coa_list = cached_query("SELECT account_code, account_name FROM chart_of_accounts ORDER BY account_code")
            coa_dict = {f"{c[0]} - {c[1]}": c[0] for c in coa_list}
            
            if is_opening:
                default_coa_head = next((k for k in coa_dict.keys() if k.startswith("EQT-101") or k.startswith("EQT-102")), list(coa_dict.keys())[0])
                account_head = st.selectbox("Corresponding Account Head (Equity/Capital)", [default_coa_head], disabled=True)
            else:
                account_head = st.selectbox("Corresponding Account Head", list(coa_dict.keys()))
                
            narration = st.text_area("Narration", height=68)
            
            if st.form_submit_button("Record Bank Entry", use_container_width=True):
                if amount > 0 and particulars and account_head:
                    account_code = coa_dict[account_head]
                    
                    if account_code == bank_code:
                        st.error("❌ Source and destination bank accounts cannot be the same!")
                        st.stop()
                    
                    # Determine full JV narration including text-area narration
                    full_narration = particulars
                    if narration.strip():
                        full_narration += f" ({narration.strip()})"
                    
                    voucher_no = generate_bank_voucher_no()
                    if entry_type == "DEBIT (Deposit)":
                        # This increases selected bank; warn if recorded cash is lower
                        if account_code == 'AST-101':
                            current_cash = get_cash_balance()
                            if current_cash < amount:
                                st.warning(f"⚠️ Cash Balance Alert: Recorded Cash in Hand is ₹{current_cash:,.2f}, which is less than the deposit amount ₹{amount:,.2f}. Cash balance will adjust accordingly.")
                        elif account_code == 'AST-102':
                            current_union = get_bank_balance("Union Bank of India")
                            if current_union < amount:
                                st.warning(f"⚠️ Union Bank Balance Alert: Available balance is ₹{current_union:,.2f}.")
                                
                    from database import record_bank_book_transaction
                    success, res_val = record_bank_book_transaction(entry_type, amount, bank_name, bank_code, account_code, particulars, narration, tx_date)
                    if success:
                        flash_success(f"✅ Bank entry successfully recorded! Voucher: {res_val}")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to record bank entry: {res_val}")

    with tab2:
        min_bb_d = cached_query("SELECT MIN(date) FROM bank_book")
        max_bb_d = cached_query("SELECT MAX(date) FROM bank_book")
        bb_default_from = datetime.strptime(min_bb_d[0][0], "%Y-%m-%d").date() if (min_bb_d and min_bb_d[0] and min_bb_d[0][0]) else (date.today() - timedelta(days=365))
        bb_default_to = datetime.strptime(max_bb_d[0][0], "%Y-%m-%d").date() if (max_bb_d and max_bb_d[0] and max_bb_d[0][0]) else date.today()
        if bb_default_to < date.today():
            bb_default_to = date.today()

        col_date1, col_date2 = st.columns(2)
        from_date = col_date1.date_input("From Date", value=bb_default_from, key="bb_view_from", format="DD-MM-YYYY")
        to_date = col_date2.date_input("To Date", value=bb_default_to, key="bb_view_to", format="DD-MM-YYYY")
        
        bb_query = """
            SELECT bb.id, bb.date, bb.voucher_no, 
                   CASE 
                       WHEN bb.debit_amount > 0 THEN bb.bank_name
                       ELSE 'Aarsha Nidhi - ' || COALESCE(co.account_name, bb.account_code)
                   END as debit_side,
                   CASE 
                       WHEN bb.debit_amount > 0 THEN 'Aarsha Nidhi - ' || COALESCE(co.account_name, bb.account_code)
                       ELSE bb.bank_name
                   END as credit_side,
                   bb.particulars, bb.debit_amount, bb.credit_amount, bb.balance, bb.bank_name, bb.narration,
                   bb.account_code, co.account_name 
            FROM bank_book bb
            LEFT JOIN chart_of_accounts co ON bb.account_code = co.account_code
            WHERE bb.date BETWEEN ? AND ?
            ORDER BY bb.date ASC, bb.id ASC
        """
        entries = cached_query(bb_query, (str(from_date), str(to_date)))
        if entries:
            cust_list = cached_query("SELECT id, name, COALESCE(account_no, '') FROM customers") or []
            formatted_entries = []
            for r in entries:
                party = extract_party_details(r[5], r[11], r[12], cust_list)
                formatted_entries.append((r[0], r[1], r[2], r[3], r[4], party, r[5], r[6], r[7], r[8], r[9], r[10]))
            df_bank = pd.DataFrame(formatted_entries, columns=["ID", "Date", "Voucher No", "Debit Side (Inflow)", "Credit Side (Outflow)", "Customer / Party Details", "Particulars", "Deposit (₹)", "Withdrawal (₹)", "Balance (₹)", "Bank", "Narration"])
            df_bank.insert(0, "Sl No", range(1, len(df_bank) + 1))
            
            # Key Financial Metrics (Opening Balance First, Closing Balance Last)
            m1, m2, m3, m4 = st.columns(4)
            first_row = df_bank.iloc[0]
            last_row = df_bank.iloc[-1]
            op_bal = first_row["Balance (₹)"] if "Opening" in str(first_row["Particulars"]) else (first_row["Balance (₹)"] - first_row["Deposit (₹)"] + first_row["Withdrawal (₹)"])
            m1.metric("🏁 Opening Balance", f"₹{op_bal:,.2f}")
            m2.metric("📥 Total Deposits (Dr)", f"₹{df_bank['Deposit (₹)'].sum():,.2f}")
            m3.metric("📤 Total Withdrawals (Cr)", f"₹{df_bank['Withdrawal (₹)'].sum():,.2f}")
            m4.metric("🏁 Closing Balance", f"₹{last_row['Balance (₹)']:,.2f}")

            st.dataframe(format_df_dates(df_bank), use_container_width=True)
            
            b_del1, b_del2 = st.columns([3, 1])
            with b_del1:
                del_id = st.number_input("Enter Bank Entry ID to Delete", min_value=1, step=1, key="del_bank_id")
                if st.button("Delete Bank Entry", use_container_width=True):
                    success, msg = delete_bank_book_entry(del_id)
                    if success:
                        flash_warning(msg)
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
            with b_del2:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("🔄 Resequence All IDs", key="reseq_bb_btn", help="Recalculates all Bank Book IDs sequentially from 1 to N without gaps", use_container_width=True):
                    success, msg = resequence_bank_book()
                    if success:
                        flash_success("✅ Bank Book resequenced successfully!")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
        else:
            st.info("No bank entries found in this date range.")

    with tab3:
        st.subheader("Edit Existing Bank Entry")
        edit_bank_id = st.number_input("Enter Bank Entry ID to Edit", min_value=1, step=1, key="edit_bank_id_input")
        bank_row = cached_query("SELECT id, particulars, debit_amount, credit_amount, bank_name, narration, account_code, voucher_no, date FROM bank_book WHERE id=?", (edit_bank_id,))
        
        if bank_row:
            row = bank_row[0]
            # row = (id, particulars, debit_amount, credit_amount, bank_name, narration, account_code, voucher_no, date)
            coa_list = cached_query("SELECT account_code, account_name FROM chart_of_accounts ORDER BY account_code")
            coa_dict = {f"{c[0]} - {c[1]}": c[0] for c in coa_list}
            
            # Find current key
            current_head_key = next((k for k, v in coa_dict.items() if v == row[6]), list(coa_dict.keys())[0])
            
            with st.form("edit_bank_form"):
                col_d, col_t, col_a = st.columns(3)
                edit_date = col_d.date_input("Date", value=datetime.strptime(row[8], "%Y-%m-%d").date() if row[8] else date.today(), format="DD-MM-YYYY")
                current_type = "DEBIT (Deposit)" if row[2] > 0 else "CREDIT (Withdrawal)"
                new_type = col_t.selectbox("Type", ["DEBIT (Deposit)", "CREDIT (Withdrawal)"], index=0 if "DEBIT" in current_type else 1)
                current_val = float(row[2]) if row[2] > 0 else float(row[3])
                new_amt = col_a.number_input("Amount (₹)", min_value=1.0, value=current_val, step=100.0)
                
                col_b1, col_b2 = st.columns(2)
                bank_opts = ["Union Bank of India", "State Bank of India"]
                bank_idx = 0 if "union" in str(row[4]).lower() else 1
                new_bank_name = col_b1.selectbox("Operating Bank Account", bank_opts, index=bank_idx)
                new_head = col_b2.selectbox("Corresponding Account Head", list(coa_dict.keys()), index=list(coa_dict.keys()).index(current_head_key) if current_head_key in coa_dict else 0)
                
                new_part = st.text_input("Particulars", value=row[1])
                new_narration = st.text_area("Narration", value=row[5] or "")
                
                if st.form_submit_button("Save Changes", use_container_width=True):
                    new_acc_code = coa_dict[new_head]
                    d_amt = new_amt if "DEBIT" in new_type else 0.0
                    c_amt = new_amt if "CREDIT" in new_type else 0.0
                    voucher_no = row[7]
                    bank_name = new_bank_name
                    bank_code = "AST-102" if "Union" in bank_name else "AST-103"
                    
                    # 1. Check Cash Balance if adjusting deposit from Cash
                    if new_acc_code == 'AST-101' and "DEBIT" in new_type:
                        cur_cash = get_cash_balance()
                        if cur_cash < new_amt:
                            st.warning(f"⚠️ Cash Balance Alert: Recorded Cash in Hand is ₹{cur_cash:,.2f}, which is less than the deposit amount ₹{new_amt:,.2f}. Balance will adjust accordingly.")
                    
                    # 2. Update the bank_book entry (including date and bank_name!)
                    run_query("""
                        UPDATE bank_book 
                        SET date = ?, particulars = ?, debit_amount = ?, credit_amount = ?, bank_name = ?, account_code = ?, narration = ? 
                        WHERE id = ?
                    """, (str(edit_date), new_part, d_amt, c_amt, bank_name, new_acc_code, new_narration, edit_bank_id), fetch=False)
                    
                    # 3. Locate and update the related Journal Voucher
                    jv_row = run_query("SELECT jv_id FROM journal_vouchers WHERE narration LIKE ?", (f"%{voucher_no}%",))
                    if jv_row:
                        jv_id = jv_row[0][0]
                        full_narration = new_part
                        if new_narration.strip():
                            full_narration += f" ({new_narration.strip()})"
                        
                        # Update JV header (including voucher_date!)
                        jv_prefix = "Bank Deposit" if "DEBIT" in new_type else "Bank Withdrawal"
                        run_query("UPDATE journal_vouchers SET voucher_date = ?, narration = ? WHERE jv_id = ?", (str(edit_date), f"{jv_prefix} [{voucher_no}]: {full_narration} - {bank_name}", jv_id), fetch=False)
                        
                        # Update JV entries (delete old ones and recreate to ensure perfect balance and account mapping)
                        run_query("DELETE FROM jv_entries WHERE jv_id = ?", (jv_id,), fetch=False)
                        if "DEBIT" in new_type:
                            run_query("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, bank_code, new_amt), fetch=False)
                            run_query("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, new_acc_code, new_amt), fetch=False)
                        else:
                            run_query("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, new_acc_code, new_amt), fetch=False)
                            run_query("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, bank_code, new_amt), fetch=False)
                    
                    from database import resequence_bank_book
                    resequence_bank_book()
                    clear_db_cache()
                    flash_success("✅ Bank Entry and Ledger updated successfully!")
                    st.rerun()

    with tab4:
        min_bb_d = cached_query("SELECT MIN(date) FROM bank_book")
        max_bb_d = cached_query("SELECT MAX(date) FROM bank_book")
        bb_default_from = datetime.strptime(min_bb_d[0][0], "%Y-%m-%d").date() if (min_bb_d and min_bb_d[0] and min_bb_d[0][0]) else (date.today() - timedelta(days=365))
        bb_default_to = datetime.strptime(max_bb_d[0][0], "%Y-%m-%d").date() if (max_bb_d and max_bb_d[0] and max_bb_d[0][0]) else date.today()
        if bb_default_to < date.today():
            bb_default_to = date.today()

        col_date1, col_date2 = st.columns(2)
        from_date = col_date1.date_input("From Date", value=bb_default_from, key="bb_print_from", format="DD-MM-YYYY")
        to_date = col_date2.date_input("To Date", value=bb_default_to, key="bb_print_to", format="DD-MM-YYYY")
        
        bb_print_query = """
            SELECT bb.date, bb.voucher_no, 
                   CASE 
                       WHEN bb.debit_amount > 0 THEN bb.bank_name
                       ELSE 'Aarsha Nidhi - ' || COALESCE(co.account_name, bb.account_code)
                   END as debit_side,
                   CASE 
                       WHEN bb.debit_amount > 0 THEN 'Aarsha Nidhi - ' || COALESCE(co.account_name, bb.account_code)
                       ELSE bb.bank_name
                   END as credit_side,
                   bb.particulars, bb.debit_amount, bb.credit_amount, bb.balance, bb.bank_name, bb.narration,
                   bb.account_code, co.account_name 
            FROM bank_book bb
            LEFT JOIN chart_of_accounts co ON bb.account_code = co.account_code
            WHERE bb.date BETWEEN ? AND ?
            ORDER BY bb.date ASC, bb.id ASC
        """
        entries = cached_query(bb_print_query, (str(from_date), str(to_date)))
        if entries:
            cust_list = cached_query("SELECT id, name, COALESCE(account_no, '') FROM customers") or []
            formatted_print = []
            for r in entries:
                party = extract_party_details(r[4], r[10], r[11], cust_list)
                formatted_print.append((r[0], r[1], r[2], r[3], party, r[4], r[5], r[6], r[7], r[8], r[9]))
            df_print = pd.DataFrame(formatted_print, columns=["Date", "Voucher No", "Debit Side (Inflow)", "Credit Side (Outflow)", "Customer / Party Details", "Particulars", "Deposit (₹)", "Withdrawal (₹)", "Balance (₹)", "Bank", "Narration"])
            df_print.insert(0, "Sl No", range(1, len(df_print) + 1))
            df_print_formatted = format_df_dates(df_print)
            st.dataframe(df_print_formatted, use_container_width=True)
            
            col_dl1, col_dl2, col_dl3 = st.columns(3)
            with col_dl1:
                excel_bytes = pdf_generator.create_excel_report("Bank Book Report", df_print, from_date, to_date)
                st.download_button(
                    "📊 Download Excel (.xlsx)",
                    data=excel_bytes,
                    file_name=f"bank_book_{from_date}_{to_date}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="btn_bb_excel"
                )
            with col_dl2:
                csv_bytes = pdf_generator.create_csv_report("Bank Book Report", df_print_formatted, from_date, to_date)
                st.download_button(
                    "📥 Download CSV (.csv)",
                    data=csv_bytes,
                    file_name=f"bank_book_{from_date}_{to_date}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="btn_bb_csv"
                )
            with col_dl3:
                if st.button("📄 Prepare PDF", key="btn_prep_bb_pdf", use_container_width=True):
                    with st.spinner("Generating PDF report..."):
                        st.session_state.bb_pdf_bytes = pdf_generator.create_pdf_report("Bank Book Report", df_print_formatted)
                if "bb_pdf_bytes" in st.session_state and st.session_state.bb_pdf_bytes:
                    st.download_button("📥 Click to Download PDF", st.session_state.bb_pdf_bytes, f"bank_book_{from_date}_{to_date}.pdf", "application/pdf", use_container_width=True, key="btn_bb_pdf")
        else:
            st.info("No bank entries found in this date range.")

    with tab5:
        st.subheader("🖨️ Bank Book Voucher (BB) Print")
        col_date1, col_date2 = st.columns(2)
        from_date = col_date1.date_input("From Date", value=date.today() - timedelta(days=30), key="bb_v_from", format="DD-MM-YYYY")
        to_date = col_date2.date_input("To Date", value=date.today(), key="bb_v_to", format="DD-MM-YYYY")
        
        bb_records = cached_query("""
            SELECT voucher_no, bank_name, particulars, date 
            FROM bank_book 
            WHERE date BETWEEN ? AND ? 
            ORDER BY id DESC
        """, (str(from_date), str(to_date)))
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
                    
                    try:
                        date_display = pd.to_datetime(date_val).strftime('%d-%m-%Y')
                    except Exception:
                        date_display = date_val
                        
                    with st.container(border=True):
                        col1, col2 = st.columns(2)
                        col1.markdown("### **BANK VOUCHER (BB)**")
                        col1.write(f"**Voucher No:** {v_num}")
                        col1.write(f"**Bank:** {bank_n}")
                        col2.write(f"**Date:** {date_display}")
                        st.divider()
                        st.write(f"**Particulars:** {part}")
                        st.write(f"**Account:** {account_display}")
                        if dr > 0:
                            st.write(f"**Debit (Deposit):** ₹{dr:,.2f}")
                        else:
                            st.write(f"**Credit (Withdrawal):** ₹{cr:,.2f}")
                        st.write(f"**Narration:** {narr if narr else 'N/A'}")
                        st.markdown("---")
                        st.caption("Authorized Signature")
                    
                    if st.button(f"🖨️ Prepare Bank Voucher PDF ({v_num})", key=f"btn_prep_bb_{v_num}", use_container_width=True):
                        with st.spinner("Generating Voucher PDF..."):
                            st.session_state[f"bb_v_pdf_{v_num}"] = pdf_generator.generate_voucher_pdf('BB', v_data)
                            
                    if f"bb_v_pdf_{v_num}" in st.session_state:
                        st.download_button(
                            label=f"📥 Download Bank Voucher {v_num} (PDF)",
                            data=st.session_state[f"bb_v_pdf_{v_num}"],
                            file_name=f"Bank_Voucher_{v_num}.pdf",
                            mime="application/pdf",
                            key=f"download_bb_{v_num}",
                            use_container_width=True
                        )

def render_journal_vouchers():
    st.title("📝 Journal Vouchers Management")
    tab1, tab2, tab3 = st.tabs(["Create Journal Voucher", "View Vouchers", "🖨️ Print JV Vouchers"])
    
    with tab1:
        st.subheader("Create Journal Voucher")
        st.info("💡 **Asset Depreciation Calculator:** Expense accounts like EXP-107 to EXP-110 will automatically compute depreciation values based on a selected Asset Base Value.")
        
        coa_list = cached_query("SELECT account_code, account_name, account_type FROM chart_of_accounts ORDER BY account_code")
        coa_dict = {f"{c[0]} - {c[1]}": c[0] for c in coa_list}
        coa_names = {c[0]: c[1] for c in coa_list}
        
        dep_rate_map = {
            "EXP-107": 5.0, "EXP-108": 10.0, "EXP-109": 15.0, "EXP-110": 40.0
        }

        with st.form("unified_jv_form"):
            v_date = st.date_input("Voucher Date", value=date.today(), format="DD-MM-YYYY")
            narration = st.text_input("Narration", value="Journal entry")
            
            st.markdown("#### **Debit Entry (Expense / Asset)**")
            col_acc1, col_dummy = st.columns([2, 1])
            acc1 = col_acc1.selectbox("Debit Account Head", list(coa_dict.keys()), key="jv_acc1")
            acc1_code = coa_dict[acc1]
            acc1_name = coa_names.get(acc1_code, "")
            
            is_depreciation = acc1_code in dep_rate_map or "depreciation" in acc1_name.lower()
            
            if is_depreciation:
                default_rate = dep_rate_map.get(acc1_code, 15.0)
                st.markdown("##### ⚙️ Asset Depreciation Calculator")
                col_p1, col_p2 = st.columns(2)
                dep_percentage = col_p1.number_input("Depreciation Percentage (%)", min_value=0.0, max_value=100.0, value=default_rate)
                base_amount = col_p2.number_input("Enter Asset Base Value (₹)", min_value=0.0, value=0.0)
                calculated_dep = round(base_amount * (dep_percentage / 100.0), 2)
                st.write(f"**Calculated Expense:** **₹{calculated_dep:,.2f}**")
                dr1 = calculated_dep
            else:
                dr1 = st.number_input("Debit Amount (₹)", min_value=0.0, value=0.0, key="jv_dr1")
            
            st.markdown("#### **Credit Entry**")
            col_acc2, col_dummy2 = st.columns([2, 1])
            acc2 = col_acc2.selectbox("Credit Account Head", list(coa_dict.keys()), key="jv_acc2")
            acc2_code = coa_dict[acc2]
            
            if is_depreciation:
                st.write(f"**Credit Amount (Auto-balanced):** ₹{calculated_dep:,.2f}")
                cr2 = calculated_dep
            else:
                cr2 = st.number_input("Credit Amount (₹)", min_value=0.0, value=0.0, key="jv_cr2")
            
            if st.form_submit_button("Post Journal Voucher", use_container_width=True):
                if dr1 <= 0 or cr2 <= 0:
                    st.error("❌ Amounts must be greater than zero!")
                elif dr1 != cr2:
                    st.error("❌ Journal Voucher unbalanced! Total Debits must equal Credits.")
                elif acc1_code == acc2_code:
                    st.error("❌ Debit and Credit accounts cannot be the same!")
                else:
                    jv_id = post_automated_jv(narration, acc1_code, acc2_code, dr1)
                    if jv_id:
                        flash_success(f"✅ Journal Voucher JV-{jv_id} posted successfully!")
                        st.rerun()

    with tab2:
        col_date1, col_date2 = st.columns(2)
        from_date = col_date1.date_input("From Date", value=date.today() - timedelta(days=30), key="jv_view_from", format="DD-MM-YYYY")
        to_date = col_date2.date_input("To Date", value=date.today(), key="jv_view_to", format="DD-MM-YYYY")
        
        jvs = cached_query("""
            SELECT jv_id, voucher_date, narration, status 
            FROM journal_vouchers 
            WHERE voucher_date BETWEEN ? AND ? 
            ORDER BY jv_id DESC
        """, (str(from_date), str(to_date)))
        if jvs:
            df_jvs = pd.DataFrame(jvs, columns=["JV ID", "Date", "Narration", "Status"])
            st.dataframe(format_df_dates(df_jvs), use_container_width=True)
            
            with st.expander("🗑️ Delete Journal Voucher", expanded=False):
                del_jv_id = st.number_input("Enter JV ID to Delete", min_value=1, step=1, key="del_jv_input_id")
                if st.button("Delete Journal Voucher", type="primary", use_container_width=True, key="del_jv_btn"):
                    success, msg = delete_jv_entry(del_jv_id)
                    clear_db_cache()
                    if success:
                        flash_success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
        else:
            st.info("No journal vouchers found in this date range.")

    with tab3:
        st.subheader("🖨️ Journal Voucher (JV) Drill-Down Print")
        col_date1, col_date2 = st.columns(2)
        from_date = col_date1.date_input("From Date", value=date.today() - timedelta(days=30), key="jv_print_from", format="DD-MM-YYYY")
        to_date = col_date2.date_input("To Date", value=date.today(), key="jv_print_to", format="DD-MM-YYYY")
        
        jv_records = cached_query("""
            SELECT jv_id, voucher_date, narration 
            FROM journal_vouchers 
            WHERE voucher_date BETWEEN ? AND ? 
            ORDER BY jv_id DESC
        """, (str(from_date), str(to_date)))
        if jv_records:
            jv_dict = {f"JV-{r[0]} - {r[2]} ({r[1]})": r[0] for r in jv_records}
            selected_jv = st.selectbox("Select Journal Voucher to Print", list(jv_dict.keys()), key="jv_drilldown")
            if selected_jv:
                jv_id = jv_dict[selected_jv]
                v_data = fetch_jv_voucher(jv_id)
                if v_data:
                    try:
                        date_display = pd.to_datetime(v_data[0][0]).strftime('%d-%m-%Y')
                    except Exception:
                        date_display = v_data[0][0]
                        
                    with st.container(border=True):
                        col1, col2 = st.columns(2)
                        col1.markdown("### **JOURNAL VOUCHER (JV)**")
                        col1.write(f"**Voucher ID:** JV-{jv_id}")
                        col2.write(f"**Date:** {date_display}")
                        st.divider()
                        
                        rows_list = []
                        total_dr = 0.0
                        total_cr = 0.0
                        for row in v_data:
                            _, _, acc_code, acc_name, dr, cr = row
                            rows_list.append([f"{acc_code} - {acc_name}", f"₹{dr:,.2f}" if dr > 0 else "-", f"₹{cr:,.2f}" if cr > 0 else "-"])
                            total_dr += dr
                            total_cr += cr
                        
                        df_jv_print = pd.DataFrame(rows_list, columns=["Account Head", "Debit", "Credit"])
                        st.dataframe(df_jv_print, use_container_width=True, hide_index=True)
                        st.write(f"**Narration:** {v_data[0][1]}")
                        st.divider()
                    if st.button(f"🖨️ Prepare JV Voucher PDF (JV-{jv_id})", key=f"btn_prep_jv_{jv_id}", use_container_width=True):
                        with st.spinner("Generating JV Voucher PDF..."):
                            st.session_state[f"jv_v_pdf_{jv_id}"] = pdf_generator.generate_voucher_pdf('JV', v_data, jv_id)
                            
                    if f"jv_v_pdf_{jv_id}" in st.session_state:
                        st.download_button(
                            label=f"📥 Download Journal Voucher JV-{jv_id} (PDF)",
                            data=st.session_state[f"jv_v_pdf_{jv_id}"],
                            file_name=f"Journal_Voucher_JV-{jv_id}.pdf",
                            mime="application/pdf",
                            key=f"download_jv_{jv_id}",
                            use_container_width=True
                        )

def render_admin_editor():
    st.title("🛠️ Universal Database Record Editor")
    if USING_SUPABASE:
        tables_res = cached_query("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name NOT LIKE 'pg_%' AND table_name NOT LIKE '_schema_%' ORDER BY table_name")
    else:
        tables_res = cached_query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_schema_%' ORDER BY name")
    
    table_list = [t[0] for t in tables_res] if tables_res else []
    selected_table = st.selectbox("Select Database Table to Manage", table_list)
    
    if selected_table:
        if USING_SUPABASE:
            cols = cached_query("SELECT column_name FROM information_schema.columns WHERE table_name = ? AND table_schema = 'public' ORDER BY ordinal_position", (selected_table,))
            col_names = [c[0] for c in cols] if cols else []
            pk_res = cached_query("""
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_name = ? AND tc.table_schema = 'public'
            """, (selected_table,))
            pk_col = pk_res[0][0] if pk_res else (col_names[0] if col_names else None)
        else:
            pk_info = cached_query(f"PRAGMA table_info({selected_table})")
            pk_col = next((col[1] for col in pk_info if col[5] == 1), pk_info[0][1] if pk_info else None)
            col_names = [col[1] for col in pk_info] if pk_info else []
        
        binary_cols = {'adhar_data', 'pan_data', 'signature_data', 'gold_image_data'}
        preview_cols = []
        for c in col_names:
            if c in binary_cols:
                preview_cols.append(f"CASE WHEN {c} IS NOT NULL THEN '<Binary Document>' ELSE NULL END AS {c}")
            else:
                preview_cols.append(c)
        preview_sql = f"SELECT {', '.join(preview_cols)} FROM {selected_table}" if preview_cols else f"SELECT * FROM {selected_table}"
        rows = cached_query(preview_sql)
        
        if rows:
            # Clean display for dataframe
            clean_rows = []
            for r in rows:
                clean_r = []
                for val in r:
                    if isinstance(val, (bytes, memoryview, bytearray)):
                        clean_r.append(f"<Binary Data ({len(val)} bytes)>")
                    else:
                        clean_r.append(val)
                clean_rows.append(clean_r)
                
            df_table = pd.DataFrame(clean_rows, columns=col_names[:len(clean_rows[0])] if clean_rows else col_names)
            st.dataframe(df_table, use_container_width=True)
            
            action = st.radio("Select Action", ["Delete Record", "Edit Record"], horizontal=True)
            if action == "Delete Record":
                record_id_to_del = st.text_input(f"Enter value for primary identifier (`{pk_col}`) to delete")
                if st.button("Delete Record", type="primary", use_container_width=True):
                    try:
                        val = int(record_id_to_del)
                    except ValueError:
                        val = record_id_to_del
                    
                    if selected_table == 'customers' and isinstance(val, int):
                        success, msg = delete_customer_cascade(val)
                    elif selected_table == 'personal_loans' and isinstance(val, int):
                        success, msg = delete_personal_loan_entry(val)
                    elif selected_table == 'gold_loans' and isinstance(val, int):
                        success, msg = delete_gold_loan_entry(val)
                    elif selected_table == 'fixed_deposits' and isinstance(val, int):
                        success, msg = delete_fd_entry(val)
                    elif selected_table == 'recurring_deposits' and isinstance(val, int):
                        success, msg = delete_rd_entry(val)
                    elif selected_table == 'journal_vouchers' and isinstance(val, int):
                        success, msg = delete_jv_entry(val)
                    elif selected_table == 'transactions' and isinstance(val, int):
                        success, msg = delete_transaction_entry(val)
                    elif selected_table == 'cash_book' and isinstance(val, int):
                        success, msg = delete_cash_book_entry(val)
                    elif selected_table == 'bank_book' and isinstance(val, int):
                        success, msg = delete_bank_book_entry(val)
                    else:
                        run_query(f"DELETE FROM {selected_table} WHERE {pk_col} = ?", (val,), fetch=False)
                        resequence_entire_database()
                        success, msg = True, f"Record deleted from {selected_table} and entire database resequenced successfully."
                    
                    clear_db_cache()
                    if success:
                        flash_success(msg)
                    else:
                        flash_error(msg)
                    st.rerun()
            elif action == "Edit Record":
                record_id_to_edit = st.text_input(f"Enter value for primary identifier (`{pk_col}`) to edit")
                if record_id_to_edit:
                    try:
                        edit_val = int(record_id_to_edit)
                    except ValueError:
                        edit_val = record_id_to_edit
                    target_row = run_query(f"SELECT * FROM {selected_table} WHERE {pk_col} = ?", (edit_val,))
                    if target_row and len(target_row) > 0:
                        row_data = target_row[0]
                        with st.form("admin_edit_form"):
                            updated_values = []
                            max_idx = min(len(col_names), len(row_data))
                            for idx in range(max_idx):
                                col_name = col_names[idx]
                                current_val = row_data[idx]
                                if col_name == pk_col:
                                    st.text(f"{col_name} (Primary Key - Read Only): {current_val}")
                                    updated_values.append(current_val)
                                elif isinstance(current_val, (bytes, memoryview, bytearray)):
                                    st.info(f"📄 {col_name} (Binary Document/Photo): {len(current_val)} bytes stored")
                                    updated_values.append(current_val)
                                else:
                                    new_input = st.text_input(f"Field: {col_name}", value="" if current_val is None else str(current_val))
                                    updated_values.append(new_input)
                            
                            if st.form_submit_button("Save Changes", use_container_width=True):
                                valid_cols = []
                                valid_vals = []
                                for i in range(len(updated_values)):
                                    if col_names[i] != pk_col:
                                        valid_cols.append(f"{col_names[i]} = ?")
                                        v = updated_values[i]
                                        if isinstance(v, (bytes, memoryview, bytearray)) and USING_SUPABASE:
                                            import psycopg2
                                            v = psycopg2.Binary(bytes(v))
                                        valid_vals.append(v)
                                valid_vals.append(edit_val)
                                run_query(f"UPDATE {selected_table} SET {', '.join(valid_cols)} WHERE {pk_col} = ?", tuple(valid_vals), fetch=False)
                                sync_db_sequences()
                                flash_success("Record updated successfully!")
                                st.rerun()
                    else:
                        st.info(f"No record found with {pk_col} = {edit_val}")

def render_financial_statements():
    st.title("⚖️ Financial Statements")
    tab1, tab2, tab3, tab4 = st.tabs(["Trial Balance", "Balance Sheet", "Profit & Loss Statement", "Ledger Print"])
    
    with tab1:
        st.subheader("Trial Balance Summary")
        col_tb_d1, col_tb_d2 = st.columns(2)
        tb_from = col_tb_d1.date_input("From Date", value=date(date.today().year if date.today().month >= 4 else date.today().year - 1, 4, 1), format="DD-MM-YYYY", key="tb_from_date")
        tb_to = col_tb_d2.date_input("To Date", value=date.today(), format="DD-MM-YYYY", key="tb_to_date")
        
        from_str = str(tb_from)
        to_str = str(tb_to)
        
        entries = cached_query("""
            SELECT CO.account_code, CO.account_name, CO.account_type, 
                   COALESCE(SUM(JE.debit), 0) as total_debit, COALESCE(SUM(JE.credit), 0) as total_credit
            FROM chart_of_accounts CO
            JOIN jv_entries JE ON CO.account_code = JE.account_code
            JOIN journal_vouchers JV ON JE.jv_id = JV.jv_id
            WHERE JV.voucher_date BETWEEN ? AND ?
            GROUP BY CO.account_code, CO.account_name, CO.account_type
            HAVING COALESCE(SUM(JE.debit), 0) > 0 OR COALESCE(SUM(JE.credit), 0) > 0
            ORDER BY CO.account_type, CO.account_code
        """, (from_str, to_str))
        
        if entries:
            df_tb = pd.DataFrame(entries, columns=["Account Code", "Account Name", "Account Type", "Total Debit", "Total Credit"])
            st.dataframe(df_tb, use_container_width=True)
            total_debits = sum(row[3] for row in entries)
            total_credits = sum(row[4] for row in entries)
            diff = abs(total_debits - total_credits)
            diff_str = f" | Difference: ₹{diff:,.2f}" if diff > 0.01 else " | Balanced ✅"
            st.metric("Total Debits / Credits Balance", f"Dr. ₹{total_debits:,.2f} | Cr. ₹{total_credits:,.2f}{diff_str}")
            
            report_title = f"Trial Balance ({tb_from.strftime('%d-%m-%Y')} to {tb_to.strftime('%d-%m-%Y')})"
            col_tb_csv, col_tb_pdf = st.columns(2)
            col_tb_csv.download_button("📥 Download Trial Balance CSV", df_tb.to_csv(index=False).encode('utf-8'), f"trial_balance_{from_str}_{to_str}.csv", "text/csv", use_container_width=True)
            col_tb_pdf.download_button("📥 Download Trial Balance PDF", pdf_generator.create_pdf_report(report_title, df_tb), f"trial_balance_{from_str}_{to_str}.pdf", "application/pdf", use_container_width=True)
        else:
            st.info(f"No transactions found for the period {tb_from.strftime('%d-%m-%Y')} to {tb_to.strftime('%d-%m-%Y')}.")
            
    with tab2:
        st.subheader("Balance Sheet (Assets, Liabilities & Equity)")
        col_bs_d1, col_bs_d2 = st.columns(2)
        bs_from = col_bs_d1.date_input("P&L Period Start (From Date)", value=date(date.today().year if date.today().month >= 4 else date.today().year - 1, 4, 1), format="DD-MM-YYYY", key="bs_from_date")
        bs_to = col_bs_d2.date_input("As on Date / Closing (To Date)", value=date.today(), format="DD-MM-YYYY", key="bs_to_date")
        
        bs_from_str = str(bs_from)
        bs_to_str = str(bs_to)
        
        # Fetch account balances up to bs_to_str
        raw_balances = cached_query("""
            SELECT 
                CO.account_code, 
                CO.account_name, 
                CO.account_type, 
                CO.category,
                COALESCE(SUM(JE.debit), 0) as total_debit,
                COALESCE(SUM(JE.credit), 0) as total_credit
            FROM chart_of_accounts CO 
            LEFT JOIN (
                jv_entries JE 
                JOIN journal_vouchers JV ON JE.jv_id = JV.jv_id AND JV.voucher_date <= ?
            ) ON CO.account_code = JE.account_code
            GROUP BY CO.account_code, CO.account_name, CO.account_type, CO.category
        """, (bs_to_str,))

        # Process balances locally in Python memory
        balance_dict = {}
        if raw_balances:
            for row in raw_balances:
                code = row[0]
                name = row[1]
                acc_type = row[2]
                cat = row[3]
                dr = float(row[4] or 0.0)
                cr = float(row[5] or 0.0)
                balance_dict[code] = {
                    "name": name,
                    "type": acc_type,
                    "category": cat,
                    "debit": dr,
                    "credit": cr,
                    "net_asset_exp": dr - cr,
                    "net_lia_eq_inc": cr - dr
                }
        
        cash_bal = balance_dict.get('AST-101', {}).get('net_asset_exp', 0.0)
        union_bank_bal = balance_dict.get('AST-102', {}).get('net_asset_exp', 0.0)
        sbi_bal = balance_dict.get('AST-103', {}).get('net_asset_exp', 0.0)
        
        sb_liability = balance_dict.get('LIA-101', {}).get('net_lia_eq_inc', 0.0)
        fd_liability = balance_dict.get('LIA-102', {}).get('net_lia_eq_inc', 0.0)
        rd_liability = balance_dict.get('LIA-103', {}).get('net_lia_eq_inc', 0.0)
        
        other_asset_balances = []
        for code, info in balance_dict.items():
            if info.get("type") == "Asset" and code not in ('AST-101', 'AST-102', 'AST-103'):
                other_asset_balances.append([code, info.get("name"), info.get("net_asset_exp")])
                
        depreciation_balances = []
        for code, info in balance_dict.items():
            if info.get("type") == "Expense" and (code in ('EXP-107', 'EXP-108', 'EXP-109', 'EXP-110') or 'depreciation' in info.get("name", "").lower()):
                net = info.get("net_asset_exp", 0.0)
                if net != 0:
                    depreciation_balances.append([code, info.get("name"), net])
                    
        # Calculate Period Net Profit / Loss for [bs_from_str, bs_to_str]
        pnl_inc_row = cached_query("""
            SELECT COALESCE(SUM(JE.credit - JE.debit), 0)
            FROM chart_of_accounts CO 
            JOIN jv_entries JE ON CO.account_code = JE.account_code
            JOIN journal_vouchers JV ON JE.jv_id = JV.jv_id
            WHERE CO.account_type = 'Income' AND JV.voucher_date BETWEEN ? AND ?
        """, (bs_from_str, bs_to_str))
        pnl_exp_row = cached_query("""
            SELECT COALESCE(SUM(JE.debit - JE.credit), 0)
            FROM chart_of_accounts CO 
            JOIN jv_entries JE ON CO.account_code = JE.account_code
            JOIN journal_vouchers JV ON JE.jv_id = JV.jv_id
            WHERE CO.account_type = 'Expense' AND JV.voucher_date BETWEEN ? AND ?
        """, (bs_from_str, bs_to_str))
        
        period_inc = pnl_inc_row[0][0] if pnl_inc_row else 0.0
        period_exp = pnl_exp_row[0][0] if pnl_exp_row else 0.0
        net_profit_loss = period_inc - period_exp

        col_bs1, col_bs2 = st.columns(2)
        with col_bs1:
            st.markdown(f"### Assets (As on {bs_to.strftime('%d-%m-%Y')})")
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
                    if row[2] != 0:
                        asset_rows.append([f"{row[0]} - {row[1]}", f"₹{row[2]:,.2f}"])
                        total_assets += row[2]
            
            if depreciation_balances:
                for row in depreciation_balances:
                    if row[2] != 0:
                        asset_rows.append([f"Less: {row[0]} - {row[1]}", f"₹{row[2]:,.2f}"])
                        total_assets -= row[2]
            
            if asset_rows:
                df_assets = pd.DataFrame(asset_rows, columns=["Account Description", "Amount (₹)"])
                st.dataframe(df_assets, use_container_width=True, hide_index=True)
                st.metric("Total Assets", f"₹{total_assets:,.2f}")

        with col_bs2:
            st.markdown(f"### Liabilities & Equity (As on {bs_to.strftime('%d-%m-%Y')})")
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
                
            # Other Liabilities (e.g. LIA-104 Unearned Interest Suspense Account)
            for code, info in balance_dict.items():
                if info.get("type") == "Liability" and code not in ('LIA-101', 'LIA-102', 'LIA-103'):
                    net = info.get("net_lia_eq_inc", 0.0)
                    if net != 0:
                        lia_data.append([f"{info.get('name')} ({code})", f"₹{net:,.2f}"])
                        total_lia += net
                
            equity_details = cached_query("""
                SELECT 
                    CO.account_name, 
                    COALESCE(JV.narration, CO.account_name) as narration_label,
                    COALESCE(SUM(JE.credit - JE.debit), 0) as net_balance
                FROM jv_entries JE 
                JOIN chart_of_accounts CO ON JE.account_code = CO.account_code
                JOIN journal_vouchers JV ON JE.jv_id = JV.jv_id
                WHERE CO.account_type = 'Equity' AND JV.voucher_date <= ?
                GROUP BY CO.account_code, CO.account_name, JV.narration
                HAVING COALESCE(SUM(JE.credit - JE.debit), 0) != 0
            """, (bs_to_str,))

            if equity_details:
                for row in equity_details:
                    acc_name, narration_label, net_balance = row
                    
                    display_label = narration_label
                    for prefix in ["Bank Deposit: ", "Cash Receipt: ", "Bank Withdrawal: ", "Cash Payment: "]:
                        if display_label.startswith(prefix):
                            display_label = display_label[len(prefix):]
                    
                    if display_label == acc_name or not display_label:
                        label = acc_name
                    else:
                        label = f"{acc_name} ({display_label})"
                        
                    lia_data.append([label, f"₹{net_balance:,.2f}"])
                    total_lia += net_balance
            
            if net_profit_loss != 0:
                label_pnl = f"Profit / Loss ({bs_from.strftime('%d-%m-%Y')} to {bs_to.strftime('%d-%m-%Y')})"
                lia_data.append([label_pnl, f"₹{net_profit_loss:,.2f}"])
                total_lia += net_profit_loss
                
            if lia_data:
                df_lia = pd.DataFrame(lia_data, columns=["Account", "Amount"])
                st.dataframe(df_lia, use_container_width=True, hide_index=True)
                st.metric("Total Liabilities & Equity", f"₹{total_lia:,.2f}")

    with tab3:
        st.subheader("Profit and Loss Account")
        col_pl_d1, col_pl_d2 = st.columns(2)
        pl_from = col_pl_d1.date_input("From Date", value=date(date.today().year if date.today().month >= 4 else date.today().year - 1, 4, 1), format="DD-MM-YYYY", key="pl_from_date")
        pl_to = col_pl_d2.date_input("To Date", value=date.today(), format="DD-MM-YYYY", key="pl_to_date")
        
        pl_from_str = str(pl_from)
        pl_to_str = str(pl_to)
        
        income_details = cached_query("""
            SELECT CO.account_code, CO.account_name, COALESCE(SUM(JE.credit - JE.debit), 0) as balance
            FROM chart_of_accounts CO 
            JOIN jv_entries JE ON CO.account_code = JE.account_code
            JOIN journal_vouchers JV ON JE.jv_id = JV.jv_id
            WHERE CO.account_type = 'Income' AND JV.voucher_date BETWEEN ? AND ?
            GROUP BY CO.account_code, CO.account_name 
            HAVING COALESCE(SUM(JE.credit - JE.debit), 0) != 0
            ORDER BY CO.account_code ASC
        """, (pl_from_str, pl_to_str))
        
        expense_details = cached_query("""
            SELECT CO.account_code, CO.account_name, COALESCE(SUM(JE.debit - JE.credit), 0) as balance
            FROM chart_of_accounts CO 
            JOIN jv_entries JE ON CO.account_code = JE.account_code
            JOIN journal_vouchers JV ON JE.jv_id = JV.jv_id
            WHERE CO.account_type = 'Expense' AND JV.voucher_date BETWEEN ? AND ?
            GROUP BY CO.account_code, CO.account_name 
            HAVING COALESCE(SUM(JE.debit - JE.credit), 0) != 0
            ORDER BY CO.account_code ASC
        """, (pl_from_str, pl_to_str))
        
        col_pl1, col_pl2 = st.columns(2)
        with col_pl1:
            st.markdown(f"### Expenditure ({pl_from.strftime('%d-%m-%Y')} to {pl_to.strftime('%d-%m-%Y')})")
            exp_rows = [[f"{row[0]} - {row[1]}", f"₹{row[2]:,.2f}"] for row in expense_details] if expense_details else []
            total_exp_v = sum(row[2] for row in expense_details) if expense_details else 0.0
            if exp_rows:
                st.dataframe(pd.DataFrame(exp_rows, columns=["Expense Account", "Amount"]), use_container_width=True, hide_index=True)
            st.metric("Total Expenditure", f"₹{total_exp_v:,.2f}")
            
        with col_pl2:
            st.markdown(f"### Income ({pl_from.strftime('%d-%m-%Y')} to {pl_to.strftime('%d-%m-%Y')})")
            inc_rows = [[f"{row[0]} - {row[1]}", f"₹{row[2]:,.2f}"] for row in income_details] if income_details else []
            total_inc_v = sum(row[2] for row in income_details) if income_details else 0.0
            if inc_rows:
                st.dataframe(pd.DataFrame(inc_rows, columns=["Income Account", "Amount"]), use_container_width=True, hide_index=True)
            st.metric("Total Income", f"₹{total_inc_v:,.2f}")
            
        st.divider()
        net_result = total_inc_v - total_exp_v
        if net_result > 0:
            st.success(f"**Net Profit for the Period ({pl_from.strftime('%d-%m-%Y')} to {pl_to.strftime('%d-%m-%Y')}):** ₹{net_result:,.2f}")
        elif net_result < 0:
            st.error(f"**Net Loss for the Period ({pl_from.strftime('%d-%m-%Y')} to {pl_to.strftime('%d-%m-%Y')}):** ₹{abs(net_result):,.2f}")
        else:
            st.info(f"**Break-even (Net Profit / Loss = ₹0.00) for the Period ({pl_from.strftime('%d-%m-%Y')} to {pl_to.strftime('%d-%m-%Y')})**")

    with tab4:
        st.subheader("🖨️ General Ledger Statement Print")
        
        # Date filter selection
        col_date1, col_date2 = st.columns(2)
        from_date = col_date1.date_input("From Date", value=date.today() - timedelta(days=30), format="DD-MM-YYYY")
        to_date = col_date2.date_input("To Date", value=date.today(), format="DD-MM-YYYY")
        
        # Load account heads for select box
        coa_list = cached_query("SELECT account_code, account_name, account_type FROM chart_of_accounts ORDER BY account_code")
        coa_dict = {f"{c[0]} - {c[1]} ({c[2]})": (c[0], c[1], c[2]) for c in coa_list}
        
        selected_head = st.selectbox("Select Account Head for Ledger", list(coa_dict.keys()))
        
        if selected_head:
            acc_code, acc_name, acc_type = coa_dict[selected_head]
            
            # 1. Calculate Opening Balance before from_date
            if acc_type in ['Asset', 'Expense']:
                # Balance = Debit - Credit
                op_bal_row = cached_query("""
                    SELECT COALESCE(SUM(JE.debit - JE.credit), 0)
                    FROM jv_entries JE 
                    JOIN journal_vouchers JV ON JE.jv_id = JV.jv_id
                    WHERE JE.account_code = ? AND JV.voucher_date < ?
                """, (acc_code, str(from_date)))
            else:
                # Balance = Credit - Debit (Liability, Equity, Income)
                op_bal_row = cached_query("""
                    SELECT COALESCE(SUM(JE.credit - JE.debit), 0)
                    FROM jv_entries JE 
                    JOIN journal_vouchers JV ON JE.jv_id = JV.jv_id
                    WHERE JE.account_code = ? AND JV.voucher_date < ?
                """, (acc_code, str(from_date)))
                
            opening_bal = op_bal_row[0][0] if op_bal_row else 0.0
            
            # Display Opening Balance label (Dr / Cr)
            if acc_type in ['Asset', 'Expense']:
                op_label = "Dr" if opening_bal >= 0 else "Cr"
            else:
                op_label = "Cr" if opening_bal >= 0 else "Dr"
            abs_op_bal = abs(opening_bal)
            
            # 2. Fetch JV entries within date range
            ledger_rows = cached_query("""
                SELECT JV.voucher_date, JV.jv_id, JV.narration, JE.debit, JE.credit
                FROM jv_entries JE 
                JOIN journal_vouchers JV ON JE.jv_id = JV.jv_id
                WHERE JE.account_code = ? AND JV.voucher_date BETWEEN ? AND ?
                ORDER BY JV.voucher_date ASC, JV.jv_id ASC
            """, (acc_code, str(from_date), str(to_date)))
            
            # 3. Calculate running balance and compile table rows
            display_rows = []
            
            # Add opening balance row
            display_rows.append([
                str(from_date), 
                "-", 
                "Opening Balance B/F", 
                0.0, 
                0.0, 
                abs_op_bal, 
                op_label
            ])
            
            running_bal = opening_bal
            for entry in ledger_rows:
                v_date, jv_id, narration, debit, credit = entry
                
                # Update running balance
                if acc_type in ['Asset', 'Expense']:
                    running_bal += (debit - credit)
                    bal_label = "Dr" if running_bal >= 0 else "Cr"
                else:
                    running_bal += (credit - debit)
                    bal_label = "Cr" if running_bal >= 0 else "Dr"
                    
                display_rows.append([
                    v_date,
                    f"JV-{jv_id}",
                    narration,
                    debit,
                    credit,
                    abs(running_bal),
                    bal_label
                ])
                
            # Compile into DataFrame
            df_ledger = pd.DataFrame(
                display_rows, 
                columns=["Date", "Voucher ID", "Particulars/Narration", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Type"]
            )
            
            # Format display data
            df_display = format_df_dates(df_ledger.copy())
            def _fmt_money(v):
                if pd.isnull(v) or v == "" or v == "-":
                    return "-"
                try:
                    val = float(str(v).replace("₹", "").replace(",", ""))
                    return f"₹{val:,.2f}" if val > 0 else "-"
                except (ValueError, TypeError):
                    return str(v)
            def _fmt_bal(v):
                if pd.isnull(v) or v == "" or v == "-":
                    return "-"
                try:
                    val = float(str(v).replace("₹", "").replace(",", ""))
                    return f"₹{val:,.2f}"
                except (ValueError, TypeError):
                    return str(v)
                    
            df_display["Debit (₹)"] = df_display["Debit (₹)"].apply(_fmt_money)
            df_display["Credit (₹)"] = df_display["Credit (₹)"].apply(_fmt_money)
            df_display["Balance (₹)"] = df_display["Balance (₹)"].apply(_fmt_bal)
            df_display["Balance (₹)"] = df_display["Balance (₹)"] + " (" + df_display["Type"] + ")"
            df_display.drop(columns=["Type"], inplace=True)
            
            # Show table
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Export to PDF
            df_pdf = format_df_dates(df_ledger.copy())
            df_pdf["Debit (₹)"] = df_pdf["Debit (₹)"].apply(_fmt_money)
            df_pdf["Credit (₹)"] = df_pdf["Credit (₹)"].apply(_fmt_money)
            df_pdf["Balance (₹)"] = df_pdf["Balance (₹)"].apply(_fmt_bal)
            df_pdf["Balance (₹)"] = df_pdf["Balance (₹)"] + " (" + df_pdf["Type"] + ")"
            df_pdf.drop(columns=["Type"], inplace=True)
            
            pdf_data = pdf_generator.create_pdf_report(f"General Ledger: {acc_code} - {acc_name}", df_pdf)
            st.download_button(
                label=f"📥 Download Ledger Statement for {acc_code} (PDF)",
                data=pdf_data,
                file_name=f"Ledger_Statement_{acc_code}_{from_date}_to_{to_date}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

def render_reports():
    st.title("📄 Comprehensive Bank Reports Center")
    report_tabs = st.tabs(["📋 Reports", "📊 Charts"])
    
    with report_tabs[0]:
        report_type = st.selectbox("Select Report to Generate", [
            "Customer List Report", "Daily Transactions Report", "SB Accounts Report",
            "FD Accounts Report", "RD Accounts Report", "Cash Book Report",
            "Bank Book Report", "Trial Balance Report", "Journal Vouchers Report"
        ])
        
        col_rep1, col_rep2 = st.columns([1, 4])
        generate_btn = col_rep1.button("📄 Generate Report", use_container_width=True, type="primary")
        
        if generate_btn:
            if report_type == "Customer List Report":
                data = cached_query("SELECT id, name, phone, email, kyc_status, created_at FROM customers")
                columns = ["ID", "Name", "Phone", "Email", "KYC Status", "Registered Date"]
            elif report_type == "Daily Transactions Report":
                data = cached_query("SELECT tx_id, account_no, type, amount, mode, narration, date FROM transactions ORDER BY date ASC, tx_id ASC")
                columns = ["Tx ID", "Account No", "Type", "Amount (₹)", "Mode", "Narration", "Date"]
            elif report_type == "SB Accounts Report":
                data = cached_query("SELECT s.account_no, c.name, s.balance, s.interest_rate, s.created_at FROM sb_accounts s JOIN customers c ON s.customer_id = c.id")
                columns = ["Account No", "Customer Name", "Balance (₹)", "Interest Rate (%)", "Created Date"]
            elif report_type == "FD Accounts Report":
                data_raw = cached_query("SELECT f.fd_id, COALESCE(f.fd_no, 'FD-' || LPAD(CAST(f.fd_id AS TEXT), 5, '0')) as fd_no, c.name, f.principal, COALESCE(f.tenure_days, f.tenure_months * 30) as tenure_days, f.tenure_months, f.interest_rate, f.maturity_amount, f.status, f.created_at FROM fixed_deposits f JOIN customers c ON f.customer_id = c.id ORDER BY f.fd_id DESC")
                data = []
                for r in (data_raw or []):
                    t_str = f"{r[4]} Days ({r[5]}M)" if r[4] else f"{r[5]} Months"
                    data.append((r[0], r[1], r[2], r[3], t_str, r[6], r[7], r[8], r[9]))
                columns = ["FD ID", "FDR No / A/c No", "Customer Name", "Principal (₹)", "Tenure", "Rate (%)", "Maturity (₹)", "Status", "Created Date"]
            elif report_type == "RD Accounts Report":
                data = cached_query("SELECT r.rd_id, c.name, r.monthly_amount, r.tenure_months, r.interest_rate, r.installments_paid, r.status, r.created_at FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id")
                columns = ["RD ID", "Customer Name", "Monthly (₹)", "Tenure (M)", "Rate (%)", "Inst. Paid", "Status", "Created Date"]
            elif report_type == "Cash Book Report":
                data = cached_query("SELECT date, voucher_no, particulars, debit_amount, credit_amount, balance, narration FROM cash_book ORDER BY date ASC, id ASC")
                columns = ["Date", "Voucher No", "Particulars", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Narration"]
            elif report_type == "Bank Book Report":
                data = cached_query("SELECT date, voucher_no, bank_name, particulars, debit_amount, credit_amount, balance, narration FROM bank_book ORDER BY date ASC, id ASC")
                columns = ["Date", "Voucher No", "Bank", "Particulars", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Narration"]
            elif report_type == "Trial Balance Report":
                if USING_SUPABASE:
                    data = cached_query("""
                        SELECT CO.account_code, CO.account_name, CO.account_type, 
                               COALESCE(SUM(JE.debit), 0) as total_debit, COALESCE(SUM(JE.credit), 0) as total_credit
                        FROM chart_of_accounts CO 
                        LEFT JOIN jv_entries JE ON CO.account_code = JE.account_code 
                        GROUP BY CO.account_code, CO.account_name, CO.account_type 
                        HAVING COALESCE(SUM(JE.debit), 0) > 0 OR COALESCE(SUM(JE.credit), 0) > 0
                    """)
                else:
                    data = cached_query("""
                        SELECT CO.account_code, CO.account_name, CO.account_type, COALESCE(SUM(JE.debit), 0) as total_debit, COALESCE(SUM(JE.credit), 0) as total_credit
                        FROM chart_of_accounts CO LEFT JOIN jv_entries JE ON CO.account_code = JE.account_code GROUP BY CO.account_code HAVING total_debit > 0 OR total_credit > 0
                    """)
                columns = ["Account Code", "Account Name", "Account Type", "Total Debit (₹)", "Total Credit (₹)"]
            elif report_type == "Journal Vouchers Report":
                data = cached_query("SELECT jv_id, voucher_date, narration, status FROM journal_vouchers ORDER BY voucher_date ASC, jv_id ASC")
                columns = ["JV ID", "Date", "Narration", "Status"]
                
            if data:
                df_rep = pd.DataFrame(data, columns=columns)
                df_rep.insert(0, "Sl No", range(1, len(df_rep) + 1))
                df_rep_formatted = format_df_dates(df_rep)
                st.dataframe(df_rep_formatted, use_container_width=True)
                st.download_button("📥 Download PDF Report", pdf_generator.create_pdf_report(report_type, df_rep_formatted), f"{report_type.replace(' ', '_').lower()}.pdf", "application/pdf", use_container_width=True)
            else:
                st.info("No records found.")
    
    with report_tabs[1]:
        st.subheader("📊 Report Charts")
        chart_type = st.selectbox("Select Chart Type", [
            "Customer Registration Trend", "Account Distribution", "SB Account Balances",
            "FD Maturity Distribution", "RD Installment Progress"
        ])
        
        if chart_type == "Customer Registration Trend":
            cust_trends = cached_query("SELECT substr(created_at, 1, 10) as reg_date, COUNT(*) as count FROM customers GROUP BY reg_date ORDER BY reg_date ASC")
            if cust_trends:
                df_trend = pd.DataFrame(cust_trends, columns=["Date", "Registrations"])
                fig = px.line(df_trend, x="Date", y="Registrations", title="Customer Registration Trend", markers=True)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No customer registration data available.")
        elif chart_type == "Account Distribution":
            sb_row = cached_query("SELECT COUNT(*) FROM sb_accounts")
            fd_row = cached_query("SELECT COUNT(*) FROM fixed_deposits WHERE status='ACTIVE'")
            rd_row = cached_query("SELECT COUNT(*) FROM recurring_deposits WHERE status='ACTIVE'")
            sb_count = sb_row[0][0] if sb_row and sb_row[0] else 0
            fd_count = fd_row[0][0] if fd_row and fd_row[0] else 0
            rd_count = rd_row[0][0] if rd_row and rd_row[0] else 0
            df_dist = pd.DataFrame({
                "Account Type": ["SB Accounts", "Fixed Deposits (FD)", "Recurring Deposits (RD)"],
                "Count": [sb_count, fd_count, rd_count]
            })
            fig = px.pie(df_dist, values="Count", names="Account Type", title="Accounts Share Ratio", hole=0.3)
            st.plotly_chart(fig, use_container_width=True)
        elif chart_type == "SB Account Balances":
            sb_bals = cached_query("SELECT account_no, balance FROM sb_accounts")
            if sb_bals:
                df_sb_bal = pd.DataFrame(sb_bals, columns=["Account No", "Balance (₹)"])
                fig = px.bar(df_sb_bal, x="Account No", y="Balance (₹)", title="SB Account Balances Summary")
                st.plotly_chart(fig, use_container_width=True)
        elif chart_type == "FD Maturity Distribution":
            fd_mats = cached_query("SELECT fd_id, maturity_amount, principal FROM fixed_deposits WHERE status='ACTIVE'")
            if fd_mats:
                df_fd_mat = pd.DataFrame(fd_mats, columns=["FD ID", "Maturity Amount (₹)", "Principal (₹)"])
                df_fd_mat["FD ID"] = df_fd_mat["FD ID"].apply(lambda x: f"FD-{x:05d}")
                fig = px.bar(df_fd_mat, x="FD ID", y="Maturity Amount (₹)", title="FD Maturity Distribution Details", hover_data=["Principal (₹)"])
                st.plotly_chart(fig, use_container_width=True)
        elif chart_type == "RD Installment Progress":
            rd_prog = cached_query("SELECT rd_id, installments_paid, tenure_months FROM recurring_deposits WHERE status='ACTIVE'")
            if rd_prog:
                df_rd_prog = pd.DataFrame(rd_prog, columns=["RD ID", "Paid", "Total"])
                df_rd_prog["RD ID"] = df_rd_prog["RD ID"].apply(lambda x: f"RD-{x:05d}")
                fig = go.Figure()
                fig.add_trace(go.Bar(name="Paid", x=df_rd_prog["RD ID"], y=df_rd_prog["Paid"], marker_color="green"))
                fig.add_trace(go.Bar(name="Remaining", x=df_rd_prog["RD ID"], y=df_rd_prog["Total"] - df_rd_prog["Paid"], marker_color="lightgrey"))
                fig.update_layout(barmode='stack', title="RD Installment Stack Progress")
                st.plotly_chart(fig, use_container_width=True)

def render_sb_interest_calculation():
    st.title("💸 Savings Bank (SB) Interest Calculation")
    st.info("💡 Interest credit values are computed as: `Balance * (Rate / 100) * (Period Days / 365)`.")
    
    sb_accs = cached_query("SELECT s.account_no, c.name, s.balance, s.interest_rate FROM sb_accounts s JOIN customers c ON s.customer_id = c.id")
    if sb_accs:
        col1, col2 = st.columns(2)
        calc_period = col1.selectbox("Calculation Period", ["Quarterly (90 Days)", "Half-Yearly (182 Days)", "Annually (365 Days)", "Custom Days"])
        days = col2.number_input("Period in Days", min_value=1, max_value=365, value=90 if "Quarterly" in calc_period else (182 if "Half-Yearly" in calc_period else 365))
        calc_date = st.date_input("Interest Posting Date", value=date.today(), format="DD-MM-YYYY")
        
        preview_rows = []
        total_interest_to_post = 0.0
        for acc_no, cust_name, balance, rate in sb_accs:
            calculated_interest = round(balance * (rate / 100.0) * (days / 365.0), 2)
            preview_rows.append([acc_no, cust_name, f"₹{balance:,.2f}", f"{rate}%", calculated_interest])
            total_interest_to_post += calculated_interest
            
        df_preview = pd.DataFrame(preview_rows, columns=["Account No", "Customer Name", "Current Balance", "Rate", "Calculated Interest (₹)"])
        st.subheader("Interest Payout Preview Sheet")
        st.dataframe(df_preview, use_container_width=True)
        st.metric("Total Outgoing Payout", f"₹{total_interest_to_post:,.2f}")
        
        if total_interest_to_post > 0:
            if st.button("Confirm and Post Interest Credits to All Accounts", type="primary", use_container_width=True):
                jv_id = post_automated_jv(
                    f"SB Interest Credit for {days} days on {calc_date}", 
                    "EXP-101", 
                    "LIA-101", 
                    total_interest_to_post
                )
                if jv_id:
                    db_conn = None
                    try:
                        db_conn = get_connection()
                        cursor = db_conn.cursor()
                        ph = "%s" if USING_SUPABASE else "?"
                        for row in preview_rows:
                            acc_no, _, _, _, interest = row
                            if interest > 0:
                                cursor.execute(f"UPDATE sb_accounts SET balance = balance + {ph} WHERE account_no = {ph}", (interest, acc_no))
                                tx_id = f"INT{datetime.now(IST).strftime('%M%S%f')}"
                                cursor.execute(f"""
                                    INSERT INTO transactions (tx_id, account_no, type, amount, mode, narration, date)
                                    VALUES ({ph}, {ph}, 'CREDIT', {ph}, 'INTEREST', {ph}, {ph})
                                """, (tx_id, acc_no, interest, f"SB Interest Credit for {days} days", str(calc_date)))
                        db_conn.commit()
                        flash_success(f"Interest credited successfully! Journal Reference: JV-{jv_id}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating interest: {str(e)}")
                    finally:
                        release_connection(db_conn)

# --- MAIN RUNNING ENTRY POINT ---

AUTH_SECRET_KEY = os.environ.get("AUTH_SECRET_KEY", "aarsha_nidhi_auth_secret_key_2026")

def generate_auth_token(username: str, validity_days: int = 14) -> str:
    """Generates a secure HMAC-signed auth token valid for validity_days."""
    try:
        expiry_ts = int(time.time()) + (validity_days * 86400)
        payload = f"{username}:{expiry_ts}"
        sig = hmac.new(AUTH_SECRET_KEY.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
        token_str = f"{payload}:{sig}"
        return base64.urlsafe_b64encode(token_str.encode('utf-8')).decode('utf-8')
    except Exception:
        return ""

def verify_auth_token(token: str):
    """Verifies HMAC signature and expiration timestamp of the token."""
    try:
        if not token:
            return None
        token_bytes = base64.urlsafe_b64decode(token.encode('utf-8'))
        token_str = token_bytes.decode('utf-8')
        parts = token_str.split(":")
        if len(parts) != 3:
            return None
        username, expiry_str, sig = parts
        expiry_ts = int(expiry_str)
        if time.time() > expiry_ts:
            return None
        expected_sig = hmac.new(AUTH_SECRET_KEY.encode('utf-8'), f"{username}:{expiry_str}".encode('utf-8'), hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig, expected_sig):
            return username
    except Exception:
        return None
    return None

def get_login_status():
    if st.session_state.get('logged_in'):
        if "auth" not in st.query_params:
            auth_token = generate_auth_token(st.session_state.get('username', 'admin'))
            if auth_token:
                st.query_params["auth"] = auth_token
        return True
    
    # Check URL query params for persistent session across browser refresh
    token = st.query_params.get("auth")
    if token:
        valid_user = verify_auth_token(token)
        if valid_user:
            st.session_state.logged_in = True
            st.session_state.username = valid_user
            return True
        else:
            try:
                del st.query_params["auth"]
            except Exception:
                pass

    st.session_state.logged_in = False
    st.session_state.username = ""
    return False

if not get_login_status():
    # Hide sidebar completely on login page
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="stSidebarNav"] {
            display: none !important;
        }
        section[data-testid="stSidebar"] {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2.2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; background: linear-gradient(135deg, #1f4e78 0%, #2c5e8a 100%); padding: 30px 25px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.12); box-shadow: 0 4px 16px rgba(0,0,0,0.15); margin-bottom: 20px; color: white;">
            <h1 style="color: white !important; font-size: 26px; margin: 5px 0; font-weight: 800; letter-spacing: 0.8px; display: flex; align-items: center; justify-content: center; gap: 10px;">🏦 AARSHA NIDHI LIMITED</h1>
            <p style="color: #dbeafe !important; font-size: 11px; margin: 8px 0 5px 0; font-weight: 500; opacity: 0.95;">📍 6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501</p>
            <p style="color: #dbeafe !important; font-size: 10px; margin: 5px 0; opacity: 0.85;">📄 CIN: U65990KL2021PLN069978 | 📞 Ph: 0471-2994535</p>
        </div>
        <div style="text-align: center; margin-bottom: 15px;">
            <h2 style="color: #1f4e78; font-size: 20px; margin: 5px 0; font-weight: 700;">🔐 Banking Software Login</h2>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("👤 Username", placeholder="Enter your username", key="login_user")
            password = st.text_input("🔑 Password", type="password", placeholder="Enter your password", key="login_pass")
            login_btn = st.form_submit_button("🔐 Login", use_container_width=True, type="primary")
            
            if login_btn:
                if username == "admin" and password == "admin123":
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    auth_token = generate_auth_token(username)
                    if auth_token:
                        st.query_params["auth"] = auth_token
                    flash_success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials.")
                    
        vs_logo_b64 = get_vsquare_logo_b64()
        if vs_logo_b64:
            logo_img_login = f'<img src="data:image/png;base64,{vs_logo_b64}" alt="VSquareInfotech" style="max-width: 215px; width: auto; height: 52px; display: block; margin: 0 auto; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.08));">'
        else:
            logo_img_login = '<div style="font-size: 15px; font-weight: 800; color: #0284c7;">🚀 VSQUARE INFOTECH</div>'

        st.markdown(f"""<div style="margin-top: 14px; padding: 12px 10px; background: rgba(255, 255, 255, 0.95); border: 1px solid #cbd5e1; border-radius: 12px; text-align: center; box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);">
<div style="font-size: 9.5px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 5px;">Designed, Hosted & Managed by</div>
<a href="https://vsquareinfotech.co.in" target="_blank" rel="noopener noreferrer" style="display: block; text-decoration: none; padding: 2px 0;">
{logo_img_login}
</a>
<div style="margin-top: 5px; font-size: 11.5px; font-weight: 800;">
<a href="https://vsquareinfotech.co.in" target="_blank" rel="noopener noreferrer" style="color: #0284c7; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; gap: 4px;">
🌐 vsquareinfotech.co.in
</a>
</div>
<div style="margin-top: 6px; font-size: 11px; display: flex; align-items: center; justify-content: center; gap: 8px;">
<a href="tel:+918547469165" style="color: #475569; text-decoration: none; font-weight: 600;">📞 8547469165</a>
<span style="color: #cbd5e1;">|</span>
<a href="https://wa.me/918547469165" target="_blank" rel="noopener noreferrer" style="color: #16a34a; text-decoration: none; font-weight: 700; display: inline-flex; align-items: center; gap: 3px;">
<svg viewBox="0 0 24 24" width="12" height="12" fill="#16a34a"><path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/></svg>
WhatsApp
</a>
</div>
</div>""", unsafe_allow_html=True)
        st.stop()

# --- SIDEBAR STYLING ---
st.sidebar.markdown("""
<style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f2b4a 0%, #1a4a7a 100%) !important;
    }
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] span, [data-testid="stSidebar"] p {
        color: white !important;
    }
    [data-testid="stSidebar"] .stRadio > label {
        color: white !important;
        font-weight: bold;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        color: white !important;
        background: transparent !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"] input:checked + div {
        background: linear-gradient(90deg, #2c6b9e, #4a8bc2) !important;
    }
    .sidebar-header {
        text-align: center !important;
        padding: 12px 4px 8px 4px !important;
        border-bottom: 1px solid rgba(255,255,255,0.15) !important;
        margin-bottom: 10px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
    }
    .sidebar-header h2 {
        color: #ffffff !important;
        font-size: 18px !important;
        font-weight: 800 !important;
        letter-spacing: 0.8px !important;
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.2 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 6px !important;
        white-space: nowrap !important;
        text-align: center !important;
    }
    .sidebar-header p {
        color: #b8d4f0 !important;
        font-size: 10px !important;
        font-weight: 500 !important;
        letter-spacing: 0.5px !important;
        margin: 4px 0 0 0 !important;
        padding: 0 !important;
        text-align: center !important;
        white-space: nowrap !important;
    }
    .sidebar-divider {
        border-top: 1px solid rgba(255,255,255,0.1); margin: 8px 0;
    }
    .user-info {
        color: #b8d4f0 !important; font-size: 12px; padding: 5px 0; text-align: center;
    }
    
    /* Lock only sidebar file uploader to black, leave main page default */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section:hover,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section:active,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section:focus {
        background-color: #000000 !important;
        background: #000000 !important;
        border: 1px solid #333333 !important;
        border-radius: 8px !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button:hover {
        background-color: #000000 !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] label,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] p,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] span,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] div {
        color: #ffffff !important;
    }

    /* Lock sidebar download button to black background and white text */
    [data-testid="stSidebar"] [data-testid="stDownloadButton"] button,
    [data-testid="stSidebar"] [data-testid="stDownloadButton"] button:hover,
    [data-testid="stSidebar"] [data-testid="stDownloadButton"] button:active,
    [data-testid="stSidebar"] [data-testid="stDownloadButton"] button:focus {
        background-color: #000000 !important;
        background: #000000 !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    /* Clean sidebar expander */
    [data-testid="stSidebar"] [data-testid="stExpander"],
    [data-testid="stSidebar"] .streamlit-expander {
        background: rgba(0, 0, 0, 0.15) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 8px !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] details {
        background: transparent !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] summary {
        background: transparent !important;
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] div[data-testid="stExpanderDetails"] {
        background: transparent !important;
        border-top: 1px solid rgba(255, 255, 255, 0.1) !important;
    }

    /* Style for tech provider container card in sidebar (Option 1: Deep Midnight & Cyan Glow) */
    [data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"]:last-of-type {
        background: linear-gradient(145deg, #07192f 0%, #0d2744 50%, #113359 100%) !important;
        border: 1px solid rgba(56, 189, 248, 0.45) !important;
        border-radius: 14px !important;
        box-shadow: 0 6px 22px rgba(0, 0, 0, 0.5), 0 0 12px rgba(56, 189, 248, 0.15) !important;
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
<div class="sidebar-header">
    <h2>🏦 AARSHA NIDHI</h2>
    <p>Financial Banking Software</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"""
<div class="user-info">
    👤 Logged in as: <b style="color:white;">{st.session_state.get('username', 'Admin')}</b>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<hr class='sidebar-divider'>", unsafe_allow_html=True)
with st.sidebar:
    components.html("""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body {
        background: transparent;
        overflow: hidden;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        user-select: none;
      }
      .clock-card {
        text-align: center;
        background: linear-gradient(135deg, rgba(8, 24, 48, 0.88) 0%, rgba(15, 38, 70, 0.78) 100%);
        padding: 14px 12px 13px 12px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.16);
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.28), inset 0 1px 1px rgba(255, 255, 255, 0.1);
        width: 100%;
      }
      @keyframes pulse-dot {
        0% {
          opacity: 1;
          transform: scale(1);
          box-shadow: 0 0 0 0 rgba(56, 189, 248, 0.7);
        }
        50% {
          opacity: 0.3;
          transform: scale(0.85);
          box-shadow: 0 0 8px 3px rgba(56, 189, 248, 0.9);
        }
        100% {
          opacity: 1;
          transform: scale(1);
          box-shadow: 0 0 0 0 rgba(56, 189, 248, 0.7);
        }
      }
      .clock-title {
        color: #cbd5e1;
        font-size: 10.5px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.4px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 7px;
        margin-bottom: 7px;
      }
      .live-dot {
        width: 7px;
        height: 7px;
        background: #38bdf8;
        border-radius: 50%;
        display: inline-block;
        animation: pulse-dot 1.5s infinite ease-in-out;
      }
      .clock-time {
        color: #ffffff;
        font-size: 21px;
        font-weight: 800;
        font-family: 'Consolas', 'Courier New', monospace;
        letter-spacing: 1.2px;
        margin: 0 0 6px 0;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
        line-height: 1.2;
      }
      .clock-date {
        color: #94a3b8;
        font-size: 11.5px;
        font-weight: 500;
        opacity: 0.95;
        letter-spacing: 0.3px;
        line-height: 1.2;
      }
    </style>
    </head>
    <body>
      <div class="clock-card">
        <div class="clock-title">
          <span class="live-dot"></span>
          IST Live Clock
        </div>
        <div id="ist-time" class="clock-time">--:--:-- --</div>
        <div id="ist-date" class="clock-date">-- --- ----</div>
      </div>

      <script>
        function updateClock() {
          try {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('en-US', {
              timeZone: 'Asia/Kolkata',
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
              hour12: true
            });
            const dateStr = now.toLocaleDateString('en-GB', {
              timeZone: 'Asia/Kolkata',
              day: '2-digit',
              month: 'short',
              year: 'numeric'
            });
            const timeEl = document.getElementById('ist-time');
            const dateEl = document.getElementById('ist-date');
            if (timeEl) timeEl.innerText = timeStr;
            if (dateEl) dateEl.innerText = dateStr;
          } catch (e) {}
        }
        updateClock();
        setInterval(updateClock, 1000);
      </script>
    </body>
    </html>
    """, height=106)
st.sidebar.markdown("<hr class='sidebar-divider'>", unsafe_allow_html=True)

menu_options = [
    "📊 Dashboard",
    "👥 Customer Management",
    "🔍 KYC Verification",
    "📅 Daily Collection Sheet",
    "💼 Personal Loans",
    "🪙 Gold Loans",
    "💰 SB Accounts",
    "📈 Fixed Deposits (FD)",
    "⏳ Recurring Deposits (RD)",
    "🗂️ Chart of Accounts",
    "💵 Cash Book",
    "🏦 Bank Book",
    "📝 Journal Vouchers",
    "⚙️ Admin Record Editor",
    "📊 Financial Statements",
    "📋 Reports",
    "🧮 SB Interest Calculation",
]

if "main_menu" not in st.session_state:
    st.session_state.main_menu = "📊 Dashboard"

menu = st.sidebar.radio(
    "📋 MENU",
    menu_options,
    key="main_menu"
)

st.sidebar.markdown("<hr class='sidebar-divider'>", unsafe_allow_html=True)

def generate_sql_backup():
    """Generate a single SQL script containing all database tables and rows"""
    tables = [
        'customers', 'sb_accounts', 'fixed_deposits', 'recurring_deposits', 
        'personal_loans', 'gold_loans', 'loan_repayments',
        'chart_of_accounts', 'journal_vouchers', 'jv_entries', 'cash_book', 
        'bank_book', 'transactions'
    ]
    sql_lines = []
    
    # Disable foreign key checks for clean insertions
    if USING_SUPABASE:
        sql_lines.append("SET session_replication_role = 'replica';\n")
    else:
        sql_lines.append("PRAGMA foreign_keys = OFF;\n")
        
    for table in tables:
        # Get column names
        if USING_SUPABASE:
            col_rows = run_query(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' ORDER BY ordinal_position")
            columns = [r[0] for r in col_rows] if col_rows else []
        else:
            col_rows = run_query(f"PRAGMA table_info({table})")
            columns = [r[1] for r in col_rows] if col_rows else []
            
        if not columns:
            continue
            
        # Get rows
        rows = run_query(f"SELECT * FROM {table}")
        
        # Clear existing rows first (safeguard)
        sql_lines.append(f"TRUNCATE TABLE {table} CASCADE;" if USING_SUPABASE else f"DELETE FROM {table};")
        
        if rows:
            col_list_str = ", ".join(columns)
            for row in rows:
                val_list = []
                for val in row:
                    if val is None:
                        val_list.append("NULL")
                    elif isinstance(val, (int, float)):
                        val_list.append(str(val))
                    elif isinstance(val, (bytes, memoryview, bytearray)):
                        raw_bytes = bytes(val)
                        if USING_SUPABASE:
                            val_list.append(f"'\\x{raw_bytes.hex()}'")
                        else:
                            val_list.append(f"X'{raw_bytes.hex()}'")
                    else:
                        # Escape single quotes for SQL insertion
                        escaped_val = str(val).replace("'", "''")
                        val_list.append(f"'{escaped_val}'")
                val_list_str = ", ".join(val_list)
                sql_lines.append(f"INSERT INTO {table} ({col_list_str}) VALUES ({val_list_str});")
        sql_lines.append("\n")
        
    # Re-enable foreign keys
    if USING_SUPABASE:
        sql_lines.append("SET session_replication_role = 'origin';\n")
    else:
        sql_lines.append("PRAGMA foreign_keys = ON;\n")
        
    return "\n".join(sql_lines).encode("utf-8")

with st.sidebar.expander("💾 System Backup & Restore"):
    with st.container(border=True):
        st.markdown("<div style='font-size: 11px; font-weight: 700; color: #b8d4f0; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.8px;'>📦 SQL Backup Export</div>", unsafe_allow_html=True)
        if USING_SUPABASE:
            if st.button("🔄 Prepare SQL Backup", key="prep_sql_bkp", use_container_width=True):
                with st.spinner("Generating database backup..."):
                    try:
                        sql_backup_bytes = generate_sql_backup()
                        st.session_state.sql_backup_bytes = sql_backup_bytes
                        st.success("Backup prepared!")
                    except Exception as e:
                        st.error(f"⚠️ Failed to generate backup: {str(e)}")
                        
            if "sql_backup_bytes" in st.session_state and st.session_state.sql_backup_bytes:
                st.download_button(
                    label="📥 Download Backup (.sql)",
                    data=st.session_state.sql_backup_bytes,
                    file_name=f"aarsha_nidhi_backup_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.sql",
                    mime="text/plain",
                    use_container_width=True
                )
        else:
            if os.path.exists(DB_NAME):
                with open(DB_NAME, "rb") as f:
                    db_bytes = f.read()
                st.download_button(
                    label="📥 Download Backup (.db)",
                    data=db_bytes,
                    file_name=f"aarsha_nidhi_backup_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.db",
                    mime="application/octet-stream",
                    use_container_width=True
                )

    with st.container(border=True):
        st.markdown("<div style='font-size: 11px; font-weight: 700; color: #b8d4f0; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.8px;'>📥 Database Import</div>", unsafe_allow_html=True)
        uploaded_dbs = st.file_uploader("Upload Backup File", type=["db", "sqlite", "sqlite3", "sql"], accept_multiple_files=True)
if uploaded_dbs:
    # If there's only one file and it's a local .db file
    if len(uploaded_dbs) == 1 and uploaded_dbs[0].name.split(".")[-1].lower() in ["db", "sqlite", "sqlite3"]:
        db_file = uploaded_dbs[0]
        if st.sidebar.button("⚠️ Confirm Restore (.db)", type="primary", use_container_width=True):
            try:
                with open(DB_NAME, "wb") as f:
                    f.write(db_file.getbuffer())
                
                # Import and trigger resequencing & reconciliation dynamically
                from database import init_db, resequence_all_accounts, reconcile_books
                init_db()
                resequence_all_accounts()
                reconcile_books()
                
                st.sidebar.success("✅ Database restored! Please refresh.")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"❌ Error: {str(e)}")
    else:
        # Filter for SQL script files
        sql_files = [f for f in uploaded_dbs if f.name.split(".")[-1].lower() == "sql"]
        if sql_files:
            if st.sidebar.button(f"⚠️ Confirm Restore ({len(sql_files)} SQL files)", type="primary", use_container_width=True):
                conn = None
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    # Temporarily disable foreign key constraints
                    try:
                        if USING_SUPABASE:
                            cursor.execute("SET session_replication_role = 'replica';")
                        else:
                            cursor.execute("PRAGMA foreign_keys = OFF;")
                    except Exception:
                        pass
                    
                    # Execute each SQL script sequentially
                    for sql_file in sql_files:
                        sql_script = sql_file.read().decode("utf-8")
                        if USING_SUPABASE:
                            cursor.execute(sql_script)
                        else:
                            cursor.executescript(sql_script)
                    
                    # Re-enable foreign key constraints
                    try:
                        if USING_SUPABASE:
                            cursor.execute("SET session_replication_role = 'origin';")
                        else:
                            cursor.execute("PRAGMA foreign_keys = ON;")
                    except Exception:
                        pass
                    
                    conn.commit()
                    
                    # Force resequence and reconcile
                    try:
                        resequence_entire_database()
                    except Exception as ex:
                        print(f"Resequence error: {str(ex)}")
                    
                    st.sidebar.success(f"✅ Successfully restored from {len(sql_files)} SQL files! Please refresh.")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"❌ Restore error: {str(e)}")
                finally:
                    release_connection(conn)


# Styling specifically targeting all buttons inside the sidebar
st.sidebar.markdown("""
<style>
    section[data-testid="stSidebar"] button,
    div[data-testid="stSidebar"] button,
    .stSidebar button,
    [data-testid="stSidebar"] [data-testid^="stBaseButton"] {
        background-color: #000000 !important;
        color: #ffffff !important;
        border: 1px solid #000000 !important;
    }
    section[data-testid="stSidebar"] button:hover,
    div[data-testid="stSidebar"] button:hover,
    .stSidebar button:hover,
    [data-testid="stSidebar"] [data-testid^="stBaseButton"]:hover {
        background-color: #333333 !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
    }
</style>
""", unsafe_allow_html=True)

if st.sidebar.button("🚪 Log Out", key="logout_btn", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.username = ""
    if "auth" in st.query_params:
        try:
            del st.query_params["auth"]
        except Exception:
            pass
    st.rerun()

vs_logo_b64 = get_vsquare_sidebar_logo_b64()
if vs_logo_b64:
    logo_img_sidebar = f'''<img src="data:image/png;base64,{vs_logo_b64}" alt="VSquareInfotech" style="max-width: 195px; width: 90%; height: auto; max-height: 52px; display: block; margin: 2px auto;">'''
else:
    logo_img_sidebar = '<div style="font-size: 14px; font-weight: 800; color: #38bdf8 !important;">🚀 VSQUARE INFOTECH</div>'

st.sidebar.markdown(f"""<div style="margin-top: 14px; padding: 12px 10px; background: linear-gradient(145deg, #1b4977 0%, #245e9a 50%, #2f74bd 100%); border: 1px solid rgba(186, 230, 253, 0.45); border-radius: 12px; text-align: center; box-shadow: 0 4px 18px rgba(0, 0, 0, 0.2), inset 0 1px 1px rgba(255, 255, 255, 0.25);">
<div style="font-size: 9.5px; font-weight: 700; color: #e0f2fe !important; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 5px;">Designed, Hosted &amp; Managed by</div>
<a href="https://vsquareinfotech.co.in" target="_blank" rel="noopener noreferrer" style="display: block; text-decoration: none; padding: 2px 0;">
{logo_img_sidebar}
</a>
<div style="margin-top: 5px; font-size: 11.5px; font-weight: 800;">
<a href="https://vsquareinfotech.co.in" target="_blank" rel="noopener noreferrer" style="color: #dbeafe !important; text-decoration: underline !important; display: inline-flex; align-items: center; justify-content: center; gap: 4px;">
🌐 vsquareinfotech.co.in
</a>
</div>
<div style="margin-top: 6px; font-size: 11px; display: flex; align-items: center; justify-content: center; gap: 8px;">
<a href="tel:+918547469165" style="color: #ffffff !important; text-decoration: none !important; font-weight: 600;">📞 8547469165</a>
<span style="color: rgba(255, 255, 255, 0.4);">|</span>
<a href="https://wa.me/918547469165" target="_blank" rel="noopener noreferrer" style="color: #4ade80 !important; text-decoration: none !important; font-weight: 700; display: inline-flex; align-items: center; gap: 3px;">
<svg viewBox="0 0 24 24" width="12" height="12" fill="#4ade80"><path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/></svg>
WhatsApp
</a>
</div>
</div>""", unsafe_allow_html=True)

# Header banner & Anti-truncation styles
st.markdown("""
<style>
    .company-header {
        background: linear-gradient(135deg, #163d63 0%, #1f4e78 50%, #2c6b9e 100%) !important;
        padding: 18px 26px !important;
        border-radius: 14px !important;
        margin-bottom: 22px !important;
        color: #ffffff !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        flex-wrap: wrap !important;
        gap: 16px !important;
        border: 1px solid rgba(255, 255, 255, 0.16) !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.14), inset 0 1px 1px rgba(255, 255, 255, 0.18) !important;
        transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1) !important;
        cursor: default !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }
    .company-header:hover {
        transform: translateY(-2px) scale(1.002) !important;
        box-shadow: 0 10px 32px rgba(15, 78, 120, 0.35), 0 2px 8px rgba(0, 0, 0, 0.12), inset 0 1px 1px rgba(255, 255, 255, 0.28) !important;
        border-color: rgba(255, 255, 255, 0.28) !important;
    }
    .company-header .brand {
        display: flex !important;
        align-items: center !important;
        gap: 16px !important;
        flex: 1 1 auto !important;
        min-width: 260px !important;
    }
    .company-header .brand-icon {
        font-size: 34px !important;
        line-height: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        flex-shrink: 0 !important;
        transition: transform 0.35s ease !important;
        filter: drop-shadow(0 2px 6px rgba(0,0,0,0.25)) !important;
    }
    .company-header:hover .brand-icon {
        transform: scale(1.12) rotate(-3deg) !important;
    }
    .company-header .brand-text {
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
    }
    .company-header .brand h1 {
        font-size: 23px !important;
        font-weight: 800 !important;
        letter-spacing: 0.9px !important;
        color: #ffffff !important;
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.2 !important;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
    }
    .company-header .brand .sub {
        font-size: 11.5px !important;
        color: #dbeafe !important;
        opacity: 0.95 !important;
        margin: 4px 0 0 0 !important;
        padding: 0 !important;
        font-weight: 500 !important;
        line-height: 1.3 !important;
        letter-spacing: 0.2px !important;
    }
    .company-header .contact-badge {
        background: rgba(255, 255, 255, 0.08) !important;
        backdrop-filter: blur(8px) !important;
        padding: 8px 16px !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: flex-end !important;
        gap: 3px !important;
        transition: all 0.3s ease !important;
        flex-shrink: 0 !important;
    }
    .company-header:hover .contact-badge {
        background: rgba(255, 255, 255, 0.15) !important;
        border-color: rgba(255, 255, 255, 0.25) !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.15) !important;
    }
    .company-header .contact-badge .cin {
        font-size: 11px !important;
        font-weight: 700 !important;
        color: #ffffff !important;
        letter-spacing: 0.5px !important;
    }
    .company-header .contact-badge .phone {
        font-size: 11.5px !important;
        color: #dbeafe !important;
        font-weight: 500 !important;
    }

    /* ======================================================== */
    /* ANTI-TRUNCATION & BORDER CONTAINMENT DISPLAY FIXES       */
    /* ======================================================== */
    /* 1. Prevent border overflow and enforce clean container containment */
    [data-testid="stVerticalBlockBorderWrapper"] {
        overflow: hidden !important;
        box-sizing: border-box !important;
        max-width: 100% !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] > div {
        overflow: hidden !important;
        box-sizing: border-box !important;
        max-width: 100% !important;
    }
    [data-testid="stMetric"] {
        overflow: hidden !important;
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
    }
    [data-testid="stMetricValue"] {
        font-size: clamp(1.05rem, 1.6vw, 1.25rem) !important;
        white-space: normal !important;
        overflow-wrap: break-word !important;
        word-wrap: break-word !important;
        word-break: break-word !important;
        line-height: 1.25 !important;
        max-width: 100% !important;
    }
    [data-testid="stMetricValue"] > div {
        white-space: normal !important;
        overflow-wrap: break-word !important;
        word-wrap: break-word !important;
        word-break: break-word !important;
        max-width: 100% !important;
    }
    [data-testid="stMetricLabel"] {
        white-space: normal !important;
        overflow-wrap: break-word !important;
        word-wrap: break-word !important;
        word-break: break-word !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        line-height: 1.2 !important;
        max-width: 100% !important;
    }
    
    /* 2. Prevent Selectbox / Dropdown option truncation */
    div[data-baseweb="select"] span {
        white-space: normal !important;
        text-overflow: clip !important;
        overflow: visible !important;
    }
    div[role="listbox"] li {
        white-space: normal !important;
        word-break: break-word !important;
    }
    
    /* 3. Ensure Dataframe tables show full contents cleanly without cutoff */
    [data-testid="stDataFrame"] {
        width: 100% !important;
    }
    [data-testid="stDataFrame"] div[data-testid="glide-data-grid"] {
        width: 100% !important;
    }
    
    /* 4. Table cell word wrapping and visibility */
    div[data-testid="stTable"] td, div[data-testid="stTable"] th {
        white-space: normal !important;
        word-break: break-word !important;
    }
</style>
<div class="company-header">
    <div class="brand">
        <div class="brand-icon">🏦</div>
        <div class="brand-text">
            <h1>AARSHA NIDHI LIMITED</h1>
            <div class="sub">📍 6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501</div>
        </div>
    </div>
    <div class="contact-badge">
        <div class="cin">CIN: U65990KL22021PLN069978</div>
        <div class="phone">📞 0471-2994535</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Navigation routing
if menu == "📊 Dashboard":
    render_dashboard()
elif menu == "👥 Customer Management":
    render_customer_management()
elif menu == "🔍 KYC Verification":
    render_kyc()
elif menu == "📅 Daily Collection Sheet":
    render_daily_collection_sheet()
elif menu == "💼 Personal Loans":
    render_personal_loans()
elif menu == "🪙 Gold Loans":
    render_gold_loans()
elif menu == "💰 SB Accounts":
    render_sb_accounts()
elif menu == "📈 Fixed Deposits (FD)":
    render_fixed_deposits()
elif menu == "⏳ Recurring Deposits (RD)":
    render_recurring_deposits()
elif menu == "🗂️ Chart of Accounts":
    render_chart_of_accounts()
elif menu == "💵 Cash Book":
    render_cash_book()
elif menu == "🏦 Bank Book":
    render_bank_book()
elif menu == "📝 Journal Vouchers":
    render_journal_vouchers()
elif menu == "⚙️ Admin Record Editor":
    render_admin_editor()
elif menu == "📊 Financial Statements":
    render_financial_statements()
elif menu == "📋 Reports":
    render_reports()
elif menu == "🧮 SB Interest Calculation":
    render_sb_interest_calculation()
