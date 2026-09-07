import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import io
import os
import time
import re
import plotly.express as px
import plotly.graph_objects as go
import pytz

# Import database layer
from database import (
    IST, DB_NAME, USING_SUPABASE, run_query, save_uploaded_file, 
    get_account_balance_from_jv, get_cash_balance, get_bank_balance,
    generate_cash_voucher_no, generate_bank_voucher_no, post_automated_jv,
    get_account_name, fetch_cb_voucher, fetch_bb_voucher, fetch_jv_voucher,
    get_connection, release_connection, sync_db_sequences
)
import pdf_generator

# Define IST timezone
IST = pytz.timezone('Asia/Kolkata')

def format_df_dates(df):
    """Automatically formats any date-like columns in a DataFrame to DD-MM-YYYY format for display"""
    if df is None or df.empty:
        return df
    df_copy = df.copy()
    date_cols = ["Date", "Created Date", "Registered Date", "date", "created_date", "registered_date", "Joined", "Registered", "Created"]
    for col in df_copy.columns:
        if col in date_cols:
            try:
                # Convert to datetime and then format
                series_dt = pd.to_datetime(df_copy[col], errors='coerce')
                # Only format rows that were successfully parsed
                formatted = series_dt.dt.strftime('%d-%m-%Y')
                # Fallback to original string if parsing failed
                df_copy[col] = formatted.fillna(df_copy[col])
            except Exception:
                pass
    return df_copy

# --- CORE VIEWS ---

def render_dashboard():
    st.title("📊 Executive Dashboard & Active Deposits")
    
    # Combined query to fetch all dashboard metrics in a single network roundtrip
    dashboard_metrics = run_query("""
        SELECT 
            (SELECT COUNT(*) FROM customers) as total_cust,
            (SELECT COUNT(*) FROM sb_accounts) as total_sb,
            (SELECT COUNT(*) FROM fixed_deposits WHERE status='ACTIVE') as total_fds,
            (SELECT COUNT(*) FROM recurring_deposits WHERE status='ACTIVE') as total_rds,
            (SELECT COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) FROM jv_entries WHERE account_code='AST-101') as cash_bal,
            (SELECT COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) FROM jv_entries WHERE account_code='AST-102') as union_bal,
            (SELECT COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) FROM jv_entries WHERE account_code='AST-103') as sbi_bal,
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
        st.plotly_chart(fig, use_container_width=True)
    
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
        st.plotly_chart(fig, use_container_width=True)
    
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
            initial_balance = col_b1.number_input("Opening SB Deposit Balance (₹)", min_value=0.0, value=0.0, step=500.0)
            
            street = col1.text_input("Street Address")
            city = col2.text_input("City")
            state = col1.text_input("State")
            pincode = col2.text_input("Pincode")
            pan = col1.text_input("PAN Number")
            
            st.markdown("---")
            adhar_upload = st.file_uploader("Upload Aadhaar Document", type=["pdf", "png", "jpg", "jpeg"], key="reg_adhar")
            pan_upload = st.file_uploader("Upload PAN Card Document", type=["pdf", "png", "jpg", "jpeg"], key="reg_pan")
            sig_upload = st.file_uploader("Upload Signature", type=["png", "jpg", "jpeg"], key="reg_sig")
            
            submitted = st.form_submit_button("🚀 Register Customer & Auto-Create Account", use_container_width=True)
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
                            
                            today_str = datetime.now(IST).strftime("%Y-%m-%d")
                            now_str = datetime.now(IST).strftime("%Y-%m-%d %H:%M")
                            
                            # 1. Insert into customers
                            run_query("""
                                INSERT INTO customers (name, account_no, dob, gender, email, phone, street, city, state, pincode, pan, adhar, adhar_file, adhar_data, pan_file, pan_data, signature_file, signature_data, kyc_status, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'VERIFIED', ?)
                            """, (name.strip(), final_acc_no, str(dob), gender, email, phone, street, city, state, pincode, pan, "[Redacted]", adh_name, adh_param, pan_name, pan_param, sig_name, sig_param, now_str), fetch=False)
                            
                            # 2. Get new customer ID
                            new_cust_id_row = run_query("SELECT id FROM customers WHERE account_no = ? ORDER BY id DESC LIMIT 1", (final_acc_no,))
                            if not new_cust_id_row:
                                new_cust_id_row = run_query("SELECT id FROM customers WHERE name = ? ORDER BY id DESC LIMIT 1", (name.strip(),))
                                
                            if new_cust_id_row:
                                new_c_id = new_cust_id_row[0][0]
                                
                                # 3. Automatically create Account in accounts table
                                db_acc_type = 'Savings Account'
                                run_query("""
                                    INSERT INTO accounts (account_number, account_type, customer_id, balance, created_at)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (final_acc_no, db_acc_type, new_c_id, initial_balance, today_str), fetch=False)
                                
                                acc_id_row = run_query("SELECT id FROM accounts WHERE customer_id = ? ORDER BY id DESC LIMIT 1", (new_c_id,))
                                if acc_id_row:
                                    acc_pk = acc_id_row[0][0]
                                    # 4. Log Opening Transaction if balance > 0
                                    if initial_balance > 0:
                                        tx_type = 'SB OPENING DEPOSIT (CREDIT)'
                                        run_query("""
                                            INSERT INTO transactions (account_id, type, amount, balance_after, date)
                                            VALUES (?, ?, ?, ?, ?)
                                        """, (acc_pk, tx_type, initial_balance, initial_balance, today_str), fetch=False)
                                        
                                # 5. Also insert into sb_accounts for standard SB tracking
                                run_query("INSERT INTO sb_accounts (account_no, customer_id, balance, interest_rate, created_at) VALUES (?, ?, ?, 3.5, ?)", 
                                          (final_acc_no, new_c_id, initial_balance, today_str), fetch=False)
                                          
                                st.success(f"🎉 Customer **{name}** (Acc: `{final_acc_no}`, ID: {new_c_id}) registered successfully! SB Account created automatically with initial balance ₹{initial_balance:,.2f}.")
                                time.sleep(1.0)
                                st.rerun()
                            else:
                                st.error("❌ Failed to create customer record. Please check inputs or database connectivity.")
                        except Exception as ex:
                            st.error(f"❌ Error during registration: {str(ex)}")

    with tab2:
        st.subheader("Customer Directory & Document Viewer")
        customers = run_query("SELECT id, COALESCE(account_no, 'N/A') as account_no, name, phone, email, kyc_status, pan, created_at FROM customers ORDER BY id ASC")
        if customers:
            df_cust = pd.DataFrame(customers, columns=["ID", "Account No", "Name", "Phone", "Email", "KYC Status", "PAN", "Joined"])
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
        all_cust_list = run_query("SELECT id, name, COALESCE(account_no, 'N/A'), phone FROM customers ORDER BY id DESC")
        if all_cust_list:
            c_dict = {f"#{r[0]} - {r[1]} (Acc: {r[2]} | Ph: {r[3]})": r[0] for r in all_cust_list}
            sel_c_label = st.selectbox("Select Customer to Edit / Manage / Delete", list(c_dict.keys()), key="edit_cust_sel")
            cust_id_edit = c_dict[sel_c_label]
            
            cust_data = run_query("SELECT name, COALESCE(account_no, ''), email, phone, street, city, state, pincode, adhar_file, pan_file, signature_file FROM customers WHERE id=?", (cust_id_edit,))
            if cust_data:
                c = cust_data[0]
                with st.form(f"edit_profile_form_{cust_id_edit}"):
                    new_name = st.text_input("Name", value=c[0])
                    new_acc_no = st.text_input("Account Number", value=c[1])
                    new_email = st.text_input("Email", value=c[2])
                    new_phone = st.text_input("Phone", value=c[3])
                    new_street = st.text_input("Street", value=c[4])
                    new_city = st.text_input("City", value=c[5])
                    new_state = st.text_input("State", value=c[6])
                    new_pincode = st.text_input("Pincode", value=c[7])
                    
                    if st.form_submit_button("💾 Save Profile Details", use_container_width=True):
                        run_query("""
                            UPDATE customers 
                            SET name=?, account_no=?, email=?, phone=?, street=?, city=?, state=?, pincode=? 
                            WHERE id=?
                        """, (new_name, new_acc_no, new_email, new_phone, new_street, new_city, new_state, new_pincode, cust_id_edit), fetch=False)
                        st.success("Profile details updated successfully!")
                        time.sleep(0.1)
                        st.rerun()

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
                        st.success("Aadhaar document deleted successfully!")
                        time.sleep(0.1)
                        st.rerun()
                else:
                    st.warning("No Aadhaar document uploaded.")
                    new_adh = st.file_uploader("Upload Aadhaar Document (PDF or Image)", type=["pdf", "jpg", "jpeg", "png"], key=f"edit_upload_adh_{cust_id_edit}")
                    if new_adh:
                        if st.button("📤 Upload Aadhaar", key=f"up_edit_adh_btn_{cust_id_edit}", type="primary", use_container_width=True):
                            saved_name, saved_bytes = save_uploaded_file(new_adh)
                            param = psycopg2.Binary(saved_bytes) if (USING_SUPABASE and saved_bytes) else saved_bytes
                            run_query("UPDATE customers SET adhar_file = ?, adhar_data = ? WHERE id = ?", (saved_name, param, cust_id_edit), fetch=False)
                            st.success("Aadhaar document saved directly into database!")
                            time.sleep(0.1)
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
                        st.success("PAN document deleted successfully!")
                        time.sleep(0.1)
                        st.rerun()
                else:
                    st.warning("No PAN document uploaded.")
                    new_pan = st.file_uploader("Upload PAN Card Document (PDF or Image)", type=["pdf", "jpg", "jpeg", "png"], key=f"edit_upload_pan_{cust_id_edit}")
                    if new_pan:
                        if st.button("📤 Upload PAN", key=f"up_edit_pan_btn_{cust_id_edit}", type="primary", use_container_width=True):
                            saved_name, saved_bytes = save_uploaded_file(new_pan)
                            param = psycopg2.Binary(saved_bytes) if (USING_SUPABASE and saved_bytes) else saved_bytes
                            run_query("UPDATE customers SET pan_file = ?, pan_data = ? WHERE id = ?", (saved_name, param, cust_id_edit), fetch=False)
                            st.success("PAN document saved directly into database!")
                            time.sleep(0.1)
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
                        st.success("Signature document deleted successfully!")
                        time.sleep(0.1)
                        st.rerun()
                else:
                    st.warning("No Signature document uploaded.")
                    new_sig = st.file_uploader("Upload Signature Document (PDF or Image)", type=["pdf", "jpg", "jpeg", "png"], key=f"edit_upload_sig_{cust_id_edit}")
                    if new_sig:
                        if st.button("📤 Upload Signature", key=f"up_edit_sig_btn_{cust_id_edit}", type="primary", use_container_width=True):
                            saved_name, saved_bytes = save_uploaded_file(new_sig)
                            param = psycopg2.Binary(saved_bytes) if (USING_SUPABASE and saved_bytes) else saved_bytes
                            run_query("UPDATE customers SET signature_file = ?, signature_data = ? WHERE id = ?", (saved_name, param, cust_id_edit), fetch=False)
                            st.success("Signature document saved directly into database!")
                            time.sleep(0.1)
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
                                st.success(f"✅ {msg}")
                                time.sleep(1.0)
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
                    st.success(f"KYC Approved for ID {p[0]}")
                    time.sleep(0.1)
                    st.rerun()
                if col2.button(f"❌ Reject KYC #{p[0]}", key=f"rej_{p[0]}", use_container_width=True):
                    run_query("UPDATE customers SET kyc_status='REJECTED' WHERE id=?", (p[0],), fetch=False)
                    st.error(f"KYC Rejected for ID {p[0]}")
                    time.sleep(0.1)
                    st.rerun()
    else:
        st.info("No pending KYC verification requests.")

def render_sb_accounts():
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
            
            if st.button("Create SB Account", use_container_width=True):
                acc_no = f"SB{datetime.now(IST).strftime('%Y%m%d%H%M%S')}"
                run_query("INSERT INTO sb_accounts VALUES (?, ?, ?, 3.5, ?)", 
                          (acc_no, cust_id, init_bal, datetime.now(IST).strftime("%Y-%m-%d")), fetch=False)
                
                if init_bal > 0:
                    run_query("INSERT INTO transactions (tx_id, account_no, type, amount, mode, narration, date) VALUES (?, ?, 'CREDIT', ?, ?, 'Opening Balance Deposit', ?)",
                              (f"TX{datetime.now(IST).strftime('%M%S%f')}", acc_no, init_bal, mode, datetime.now(IST).strftime("%Y-%m-%d")), fetch=False)
                    
                    jv_result = post_automated_jv(f"SB Opening Balance - Account {acc_no}", chosen_asset_code, "LIA-101", init_bal)
                    
                    if jv_result:
                        today = datetime.now(IST).strftime("%Y-%m-%d")
                        new_asset_balance = get_account_balance_from_jv(chosen_asset_code)
                        
                        if chosen_asset_code == 'AST-101':
                            voucher_no = generate_cash_voucher_no()
                            run_query("""
                                INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (today, voucher_no, f"SB Opening Deposit: {acc_no}", init_bal, 0, new_asset_balance, chosen_asset_code, f"SB Opening Balance - {acc_no}", datetime.now(IST).strftime("%Y-%m-%d %H:%M")), fetch=False)
                        elif chosen_asset_code in ['AST-102', 'AST-103']:
                            bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
                            voucher_no = generate_bank_voucher_no()
                            run_query("""
                                INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (today, voucher_no, f"SB Opening Deposit: {acc_no}", init_bal, 0, new_asset_balance, bank_name, chosen_asset_code, f"SB Opening Balance - {acc_no}", datetime.now(IST).strftime("%Y-%m-%d %H:%M")), fetch=False)

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
            
            if st.button("Execute Transaction", use_container_width=True):
                from database import record_sb_transaction
                success, res_val = record_sb_transaction(acc_choice, tx_type, amount, pay_mode, chosen_asset_code, narration)
                if success:
                    st.success(f"✅ {tx_type.capitalize()} successful! New Balance: ₹{res_val:,.2f}")
                    time.sleep(0.1)
                    st.rerun()
                else:
                    st.error(f"❌ Transaction failed: {res_val}")

    with tab3:
        accounts = run_query("""
            SELECT s.account_no, c.name, s.balance, s.interest_rate, s.created_at 
            FROM sb_accounts s JOIN customers c ON s.customer_id = c.id
        """)
        if accounts:
            df_sb = pd.DataFrame(accounts, columns=["Account No", "Customer Name", "Balance (₹)", "Interest Rate (%)", "Created"])
            df_sb_formatted = format_df_dates(df_sb)
            st.dataframe(df_sb_formatted, use_container_width=True)
            st.download_button("📥 Download SB Accounts PDF", pdf_generator.create_pdf_report("Savings Bank Accounts Report", df_sb_formatted), "sb_accounts.pdf", "application/pdf", use_container_width=True)
        else:
            st.info("No active SB accounts found.")

def render_fixed_deposits():
    st.title("📈 Fixed Deposits Management")
    tab1, tab2, tab3, tab4 = st.tabs(["Open FD", "Active FDs", "Print Certificate / Ledger", "Close FD"])
    
    with tab1:
        customers = run_query("SELECT id, name, street, city, state, pincode FROM customers")
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
            
            if st.button("Open FD Account", use_container_width=True):
                available_balance = get_account_balance_from_jv(chosen_asset_code)
                if principal > available_balance:
                    st.error(f"❌ Insufficient balance in {payment_mode}! Available: ₹{available_balance:,.2f}, Required: ₹{principal:,.2f}")
                    st.stop()
                
                run_query("""
                    INSERT INTO fixed_deposits (customer_id, principal, tenure_months, interest_rate, maturity_amount, nominee, status, created_at, payment_mode)
                    VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                """, (cust_dict[selected_cust], principal, tenure, interest_rate, maturity_amount, nominee, datetime.now(IST).strftime("%Y-%m-%d"), payment_mode), fetch=False)
                
                jv_result = post_automated_jv(f"Fixed Deposit Opening - Principal ₹{principal} via {payment_mode}", chosen_asset_code, "LIA-102", principal)
                
                if jv_result:
                    today = datetime.now(IST).strftime("%Y-%m-%d")
                    new_balance = get_account_balance_from_jv(chosen_asset_code)
                    
                    if chosen_asset_code == 'AST-101':
                        voucher_no = generate_cash_voucher_no()
                        run_query("""
                            INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (today, voucher_no, f"FD Opening - Customer {cust_dict[selected_cust]}", 0, principal, new_balance, chosen_asset_code, f"FD Opening via {payment_mode}", datetime.now(IST).strftime("%Y-%m-%d %H:%M")), fetch=False)
                    elif chosen_asset_code in ['AST-102', 'AST-103']:
                        bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
                        voucher_no = generate_bank_voucher_no()
                        run_query("""
                            INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (today, voucher_no, f"FD Opening - Customer {cust_dict[selected_cust]}", 0, principal, new_balance, bank_name, chosen_asset_code, f"FD Opening via {payment_mode}", datetime.now(IST).strftime("%Y-%m-%d %H:%M")), fetch=False)
                
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
        st.subheader("🖨️ Printable FD Certificate & Ledger")
        all_fds = run_query("""
            SELECT f.fd_id, c.name, c.street, c.city, c.state, c.pincode, 
                   f.principal, f.tenure_months, f.interest_rate, f.maturity_amount, 
                   f.nominee, f.created_at, f.status, f.closed_date
            FROM fixed_deposits f JOIN customers c ON f.customer_id = c.id
            ORDER BY f.fd_id DESC
        """)
        if all_fds:
            fd_print_dict = {}
            for r in all_fds:
                status_display = "🔴 CLOSED" if r[12] == 'CLOSED' else "🟢 ACTIVE"
                label = f"FD ID: {r[0]} - {r[1]} (Principal: ₹{r[6]:,.2f}) - {status_display}"
                fd_print_dict[label] = r
            
            selected_print_str = st.selectbox("Select FD Account for Printing/View", list(fd_print_dict.keys()), key="fd_print_select")
            fd_data = fd_print_dict[selected_print_str]
            
            fd_id, c_name, street, city, state, pincode, principal, tenure, rate, maturity, nominee, created_at, status, closed_date = fd_data
            
            try:
                created_at_dt = pd.to_datetime(created_at).strftime('%d-%m-%Y')
            except Exception:
                created_at_dt = created_at
                
            try:
                closed_date_dt = pd.to_datetime(closed_date).strftime('%d-%m-%Y') if closed_date else ""
            except Exception:
                closed_date_dt = closed_date
            
            full_address = f"{street}, {city}, {state} - {pincode}" if street else f"{city}, {state} - {pincode}"
            status_text = "CLOSED" if status == 'CLOSED' else "ACTIVE"
            status_color = "#e74c3c" if status == 'CLOSED' else "#27ae60"
            
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
              th {{ background-color: #f2f2f2; }}
              .signatures {{ display: flex; justify-content: space-between; margin-top: 50px; font-size: 12px; font-weight: bold; text-align: center; }}
              .closed-info {{ background: #fde8e8; padding: 10px; border-radius: 5px; margin-top: 10px; color: #c0392b; }}
            </style>
            
            <div class="fd-receipt">
              <div class="header">
                <h2>AARSHA NIDHI LIMITED</h2>
                <p>6/814, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501</p>
                <p>CIN: U65990KL22021PLN069978 | Ph: 0471-2994535</p>
              </div>
              <div style="text-align:center;">
                <span class="badge">FIXED DEPOSIT RECEIPT / LEDGER</span>
                <span class="status-badge">{status_text}</span>
              </div>
              
              <div class="grid-row">
                <div><b>FDR No. / A/c No:</b> FD-{fd_id:05d}</div>
                <div><b>A/c Opening Date:</b> {created_at_dt}</div>
              </div>
              <div class="grid-row">
                <div><b>Name:</b> {c_name}</div>
                <div><b>Interest Rate:</b> {rate}% p.a.</div>
              </div>
              <div class="grid-row">
                <div><b>Address:</b> {full_address}</div>
                <div><b>Status:</b> {status_text}</div>
              </div>
              <div class="grid-row">
                <div><b>Mode of Op.:</b> Single</div>
                <div><b>Nominee:</b> {nominee if nominee else 'N/A'}</div>
              </div>
              <div class="grid-row">
                <div><b>Period / Tenure:</b> {tenure} MONTHS</div>
                <div><b>Maturity Amount:</b> ₹{maturity:,.2f}</div>
              </div>
              {f'<div class="grid-row"><div><b>Closed Date:</b> {closed_date_dt}</div><div></div></div>' if status == 'CLOSED' else ''}
              
              <div class="box">
                <b>Deposit Repayable:</b> Principal sum of <b>₹{principal:,.2f}</b> repayable after {tenure} months with interest at {rate}% p.a.
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
                  <td>{created_at}</td>
                  <td>Opening Balance / Principal Deposit</td>
                  <td>-</td>
                  <td>₹{principal:,.2f}</td>
                  <td>₹{principal:,.2f}</td>
                  <td>0</td>
                  <td>0</td>
                </tr>
                {f'<tr><td>{closed_date}</td><td>FD Closed / Maturity Payment</td><td>₹{maturity:,.2f}</td><td>-</td><td>₹0.00</td><td>₹{maturity - principal:,.2f}</td><td>0</td></tr>' if status == 'CLOSED' else ''}
              </table>

              <div class="signatures">
                <div>Manager</div>
                <div>Accountant</div>
                <div>Chairman / MD</div>
              </div>
              {f'<div class="closed-info">⚠️ This Fixed Deposit has been CLOSED on {closed_date}</div>' if status == 'CLOSED' else ''}
            </div>
            """
            st.markdown(receipt_html, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            fd_pdf_data = pdf_generator.generate_fd_pdf(fd_data)
            st.download_button(
                label=f"📥 Download FD Certificate FD-{fd_id:05d} (PDF)",
                data=fd_pdf_data,
                file_name=f"FD_Certificate_FD-{fd_id:05d}.pdf",
                mime="application/pdf",
                key=f"download_fd_pdf_{fd_id}",
                use_container_width=True
            )
        else:
            st.info("No Fixed Deposits available to print.")

    with tab4:
        st.subheader("Close Fixed Deposit")
        active_fds = run_query("""
            SELECT f.fd_id, c.name, f.principal, f.maturity_amount, f.interest_rate, f.tenure_months
            FROM fixed_deposits f JOIN customers c ON f.customer_id = c.id
            WHERE f.status = 'ACTIVE'
        """)
        
        if active_fds:
            fd_dict = {f"FD ID: {r[0]} - {r[1]} (Principal: ₹{r[2]:,.2f}, Maturity: ₹{r[3]:,.2f})": r for r in active_fds}
            selected_fd_str = st.selectbox("Select FD to Close", list(fd_dict.keys()), key="fd_close_select")
            selected_fd = fd_dict[selected_fd_str]
            fd_id, cust_name, principal, maturity_amount, interest_rate, tenure = selected_fd
            
            interest_earned = maturity_amount - principal
            st.info(f"Interest Earned: ₹{interest_earned:,.2f}")
            st.info(f"Total Maturity Amount (Principal + Interest): ₹{maturity_amount:,.2f}")
            
            if st.button("Close FD", type="primary", use_container_width=True):
                run_query("""
                    UPDATE fixed_deposits 
                    SET status = 'CLOSED', closed_date = ?
                    WHERE fd_id = ?
                """, (datetime.now(IST).strftime("%Y-%m-%d"), fd_id), fetch=False)
                
                if interest_earned > 0:
                    post_automated_jv(f"FD #{fd_id} Interest Accrued", "EXP-102", "LIA-102", interest_earned)
                
                post_automated_jv(f"FD #{fd_id} Maturity - Transfer to SB", "LIA-102", "LIA-101", maturity_amount)
                
                st.success(f"FD #{fd_id} closed successfully!")
                st.info(f"₹{maturity_amount:,.2f} transferred from FD Deposits Control to SB Deposits Control")
                time.sleep(0.1)
                st.rerun()
        else:
            st.info("No active FDs available to close.")

def render_recurring_deposits():
    st.title("🔄 Recurring Deposits Management")
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Open RD", "Pay Installment", "Active RDs", "Print Certificate / Ledger", "Close RD", "✏️ Edit / Update RD"])
    
    with tab1:
        customers = run_query("SELECT id, name, street, city, state, pincode FROM customers")
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
            
            total_deposits = monthly_amt * tenure
            approx_interest = total_deposits * (interest_rate / 100) * (tenure / 24)
            approx_maturity = total_deposits + approx_interest
            
            st.info(f"**Estimated Maturity:** Total Deposits ₹{total_deposits:,.2f} + Interest ₹{approx_interest:,.2f} = ₹{approx_maturity:,.2f}")
            
            if st.button("Open RD Account", use_container_width=True):
                available_balance = get_account_balance_from_jv(chosen_asset_code)
                if monthly_amt > available_balance:
                    st.error(f"❌ Insufficient balance in {payment_mode}! Available: ₹{available_balance:,.2f}, Required: ₹{monthly_amt:,.2f}")
                    st.stop()
                
                run_query("""
                    INSERT INTO recurring_deposits (customer_id, monthly_amount, tenure_months, interest_rate, installments_paid, nominee, status, created_at, payment_mode, maturity_amount)
                    VALUES (?, ?, ?, ?, 0, ?, 'ACTIVE', ?, ?, ?)
                """, (cust_dict[selected_cust], monthly_amt, tenure, interest_rate, nominee, 
                      datetime.now(IST).strftime("%Y-%m-%d"), payment_mode, approx_maturity), fetch=False)
                
                jv_result = post_automated_jv(f"RD Opening - First Installment via {payment_mode}", chosen_asset_code, "LIA-103", monthly_amt)
                
                if USING_SUPABASE:
                    rd_id_result = run_query("SELECT LASTVAL()")
                else:
                    rd_id_result = run_query("SELECT last_insert_rowid()")
                if rd_id_result and jv_result:
                    rd_id = rd_id_result[0][0]
                    run_query("UPDATE recurring_deposits SET installments_paid=1 WHERE rd_id=?", (rd_id,), fetch=False)
                    
                    today = datetime.now(IST).strftime("%Y-%m-%d")
                    new_balance = get_account_balance_from_jv(chosen_asset_code)
                    
                    if chosen_asset_code == 'AST-101':
                        voucher_no = generate_cash_voucher_no()
                        run_query("""
                            INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (today, voucher_no, f"RD Opening - Inst 1 - Customer {cust_dict[selected_cust]}", 0, monthly_amt, new_balance, chosen_asset_code, f"RD Opening via {payment_mode}", datetime.now(IST).strftime("%Y-%m-%d %H:%M")), fetch=False)
                    elif chosen_asset_code in ['AST-102', 'AST-103']:
                        bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
                        voucher_no = generate_bank_voucher_no()
                        run_query("""
                            INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (today, voucher_no, f"RD Opening - Inst 1 - Customer {cust_dict[selected_cust]}", 0, monthly_amt, new_balance, bank_name, chosen_asset_code, f"RD Opening via {payment_mode}", datetime.now(IST).strftime("%Y-%m-%d %H:%M")), fetch=False)
                
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
            chosen_rd_str = st.selectbox("Select Active RD Account", list(rd_dict.keys()), key="rd_pay_select")
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
            
            if st.button("Confirm & Pay Installment", use_container_width=True):
                available_balance = get_account_balance_from_jv(chosen_asset_code)
                if monthly_amt > available_balance:
                    st.error(f"❌ Insufficient balance in {payment_mode_pay}! Available: ₹{available_balance:,.2f}, Required: ₹{monthly_amt:,.2f}")
                    st.stop()
                
                if paid_inst < tenure_m:
                    new_paid = paid_inst + 1
                    run_query("UPDATE recurring_deposits SET installments_paid=? WHERE rd_id=?", (new_paid, rd_id), fetch=False)
                    
                    jv_result = post_automated_jv(f"RD Installment Paid - RD #{rd_id} (Inst #{new_paid}) via {payment_mode_pay}", chosen_asset_code, "LIA-103", monthly_amt)
                    
                    if jv_result:
                        today = datetime.now(IST).strftime("%Y-%m-%d")
                        new_balance = get_account_balance_from_jv(chosen_asset_code)
                        
                        if chosen_asset_code == 'AST-101':
                            voucher_no = generate_cash_voucher_no()
                            run_query("""
                                INSERT INTO cash_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, account_code, narration, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (today, voucher_no, f"RD #{rd_id} - Inst #{new_paid}", 0, monthly_amt, new_balance, chosen_asset_code, f"RD Installment #{new_paid}", datetime.now(IST).strftime("%Y-%m-%d %H:%M")), fetch=False)
                        elif chosen_asset_code in ['AST-102', 'AST-103']:
                            bank_name = "Union Bank of India" if chosen_asset_code == 'AST-102' else "State Bank of India"
                            voucher_no = generate_bank_voucher_no()
                            run_query("""
                                INSERT INTO bank_book (date, voucher_no, particulars, debit_amount, credit_amount, balance, bank_name, account_code, narration, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (today, voucher_no, f"RD #{rd_id} - Inst #{new_paid}", 0, monthly_amt, new_balance, bank_name, chosen_asset_code, f"RD Installment #{new_paid}", datetime.now(IST).strftime("%Y-%m-%d %H:%M")), fetch=False)
                    
                    st.success(f"Installment #{new_paid} successfully paid via {payment_mode_pay}!")
                    time.sleep(0.1)
                    st.rerun()
        else:
            st.info("No active recurring deposits found.")

    with tab3:
        rds = run_query("""
            SELECT COALESCE(r.rd_no, 'RD-' || CAST(r.rd_id AS TEXT)) as acc_no, 
                   c.name, COALESCE(r.scheme_name, 'SWAYAMVARA KSHEMANIDHI') as scheme,
                   r.monthly_amount, r.tenure_months, r.interest_rate, 
                   r.installments_paid, COALESCE(r.collected_balance, r.monthly_amount * r.installments_paid) as col_bal,
                   COALESCE(r.maturity_date, '2026-12-20') as mat_date,
                   r.maturity_amount, r.nominee, r.status
            FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id
            WHERE r.status = 'ACTIVE'
        """)
        if rds:
            df_rds = pd.DataFrame(rds, columns=["A/C No", "Customer Name", "Scheme", "Monthly (₹)", "Tenure (M)", "Rate (%)", "Paid Inst.", "Total Deposited (₹)", "Maturity Date", "Maturity Amount (₹)", "Nominee", "Status"])
            st.dataframe(df_rds, use_container_width=True)
        else:
            st.info("No active recurring deposits found.")

    with tab4:
        st.subheader("🖨️ Printable RD Certificate & Ledger")
        all_rds = run_query("""
            SELECT r.rd_id, c.name, c.street, c.city, c.state, c.pincode, 
                   r.monthly_amount, r.tenure_months, r.interest_rate, 
                   r.installments_paid, r.maturity_amount, r.nominee, 
                   r.created_at, r.status, r.closed_date,
                   COALESCE(r.rd_no, 'RD-' || CAST(r.rd_id AS TEXT)) as acc_no,
                   COALESCE(r.collected_balance, r.monthly_amount * r.installments_paid) as col_bal,
                   COALESCE(r.scheme_name, 'SWAYAMVARA KSHEMANIDHI') as scheme_name,
                   COALESCE(r.maturity_date, '2026-12-20') as maturity_date
            FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id
            ORDER BY r.rd_id DESC
        """)
        if all_rds:
            rd_print_dict = {}
            for r in all_rds:
                status_display = "🔴 CLOSED" if r[13] == 'CLOSED' else "🟢 ACTIVE"
                label = f"A/C: {r[15]} - {r[1]} ({r[17]} | Paid: {r[9]}/{r[7]} | Balance: ₹{r[16]:,.2f}) - {status_display}"
                rd_print_dict[label] = r
            
            selected_rd_print = st.selectbox("Select RD Account for Printing/View", list(rd_print_dict.keys()), key="rd_print_select")
            rd_data = rd_print_dict[selected_rd_print]
            
            rd_id, c_name, street, city, state, pincode, monthly_amt, tenure, rate, paid_inst, maturity, nominee, created_at, status, closed_date, rd_acc_no, col_balance, scheme_name, maturity_date = rd_data
            
            full_address = f"{street}, {city}, {state} - {pincode}" if street else f"{city}, {state} - {pincode}"
            total_deposited = col_balance
            status_text = "CLOSED" if status == 'CLOSED' else "ACTIVE"
            status_color = "#e74c3c" if status == 'CLOSED' else "#2980b9"
            
            years = int(tenure) // 12
            months = int(tenure) % 12
            if years > 0 and months > 0:
                tenure_display_str = f"{tenure} MONTHS ({years} Years {months} Months)"
            elif years > 0:
                tenure_display_str = f"{tenure} MONTHS ({years} Years)"
            else:
                tenure_display_str = f"{tenure} MONTHS"

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
                <p>6/814, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501</p>
                <p>CIN: U65990KL22021PLN069978 | Ph: 0471-2994535</p>
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
                <div><b>A/c Opening Date:</b> {created_at}</div>
                <div><b>Maturity Date:</b> <span style="color:#27ae60;font-weight:bold;">{maturity_date}</span></div>
              </div>
              <div class="grid-row">
                <div><b>Name:</b> {c_name}</div>
                <div><b>Interest Rate:</b> {rate}% p.a.</div>
              </div>
              <div class="grid-row">
                <div><b>Address:</b> {full_address}</div>
                <div><b>Status:</b> {status_text}</div>
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
                <div><b>Maturity Amount:</b> <span style="color:#1b4f72;font-weight:bold;">₹{maturity:,.2f}</span></div>
              </div>
              {f'<div class="grid-row"><div><b>Closed Date:</b> {closed_date}</div><div></div></div>' if status == 'CLOSED' else ''}
              
              <div class="box">
                <b>Deposit Repayable:</b> Recurring Deposit of <b>₹{monthly_amt:,.2f}</b> monthly for {tenure} months. Total balance accumulated: <b>₹{col_balance:,.2f}</b>.
              </div>

              <table>
                <tr>
                  <th>Date</th>
                  <th>Particulars</th>
                  <th>Payment / Debit</th>
                  <th>Receipt / Credit</th>
                  <th>Balance</th>
                  <th>Installments Paid</th>
                </tr>
                <tr>
                  <td>{created_at}</td>
                  <td>RD Account Opening & Installments</td>
                  <td>-</td>
                  <td>₹{col_balance:,.2f}</td>
                  <td>₹{col_balance:,.2f}</td>
                  <td>{paid_inst}</td>
                </tr>
                {f'<tr><td>{closed_date}</td><td>RD Closed / Maturity Payment</td><td>₹{maturity:,.2f}</td><td>-</td><td>₹0.00</td><td>{paid_inst}</td></tr>' if status == 'CLOSED' else ''}
              </table>

              <div class="signatures">
                <div>Manager</div>
                <div>Accountant</div>
                <div>Chairman / MD</div>
              </div>
              {f'<div class="closed-info">⚠️ This Recurring Deposit has been CLOSED on {closed_date}</div>' if status == 'CLOSED' else ''}
            </div>
            """
            st.markdown(rd_receipt_html, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            rd_pdf_data = pdf_generator.generate_rd_pdf(rd_data)
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
        active_rds_close = run_query("""
            SELECT r.rd_id, c.name, r.monthly_amount, r.tenure_months, r.installments_paid, r.maturity_amount, r.interest_rate
            FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id
            WHERE r.status = 'ACTIVE'
        """)
        
        if active_rds_close:
            rd_close_dict = {f"RD ID: {r[0]} - {r[1]} (Paid: {r[4]}/{r[3]}, Est. Maturity: ₹{r[5]:,.2f})": r for r in active_rds_close}
            selected_rd_str = st.selectbox("Select RD to Close", list(rd_close_dict.keys()), key="rd_close_select")
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
            
            if st.button("Close RD", type="primary", use_container_width=True):
                run_query("""
                    UPDATE recurring_deposits 
                    SET status = 'CLOSED', closed_date = ?
                    WHERE rd_id = ?
                """, (datetime.now(IST).strftime("%Y-%m-%d"), rd_id), fetch=False)
                
                post_automated_jv(f"RD #{rd_id} Maturity - Transfer to SB Deposits Control", "LIA-103", "LIA-101", maturity_amount_to_pay)
                
                if interest_earned > 0:
                    post_automated_jv(f"RD #{rd_id} Interest Expense", "EXP-103", "LIA-103", interest_earned)
                
                st.success(f"RD #{rd_id} closed successfully! Amount transferred to SB Deposits Control")
                time.sleep(0.1)
                st.rerun()
        else:
            st.info("No active RDs available to close.")

    with tab6:
        st.subheader("✏️ Edit & Correct Recurring Deposit Account")
        st.caption("Enter the exact amount paid/deposited, tenure, and interest rate — maturity amount recalculates live on whatever amount you enter.")
        
        all_rds_edit = run_query("""
            SELECT r.rd_id, c.name, r.monthly_amount, r.tenure_months, r.interest_rate, 
                   r.installments_paid, r.nominee, r.status, r.created_at, r.maturity_amount,
                   COALESCE(r.rd_no, 'RD-' || CAST(r.rd_id AS TEXT)) as rd_no,
                   COALESCE(r.scheme_name, 'SWAYAMVARA KSHEMANIDHI') as scheme_name,
                   COALESCE(r.maturity_date, '2026-12-20') as maturity_date,
                   COALESCE(r.collected_balance, r.monthly_amount * r.installments_paid) as collected_balance,
                   r.customer_id
            FROM recurring_deposits r 
            JOIN customers c ON r.customer_id = c.id
            ORDER BY r.rd_id DESC
        """)
        
        if all_rds_edit:
            rd_edit_dict = {}
            for r in all_rds_edit:
                status_icon = "🔴 CLOSED" if r[7] == 'CLOSED' else "🟢 ACTIVE"
                label = f"A/C: {r[10]} - {r[1]} ({r[11]} | Amount Paid: ₹{r[13]:,.2f} | Tenure: {r[3]}M) - {status_icon}"
                rd_edit_dict[label] = r
            
            selected_edit_label = st.selectbox("Select RD Account to Edit", list(rd_edit_dict.keys()), key="rd_edit_select")
            curr_rd = rd_edit_dict[selected_edit_label]
            
            c_rd_id, c_name, c_monthly, c_tenure, c_rate, c_paid, c_nominee, c_status, c_created, c_maturity, c_rd_no, c_scheme, c_mat_date, c_col_bal, c_cust_id = curr_rd
            
            st.markdown("---")
            col_e1, col_e2 = st.columns(2)
            
            with col_e1:
                edit_rd_no = st.text_input("RD Account Number", value=str(c_rd_no), key=f"edit_rd_no_{c_rd_id}")
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
                edit_tenure = st.number_input("Tenure (Months)", min_value=1, max_value=120, value=int(c_tenure), step=1, key=f"edit_tenure_{c_rd_id}")
                edit_rate = st.number_input("Interest Rate (% p.a.)", min_value=0.0, max_value=30.0, value=float(c_rate), step=0.25, key=f"edit_rate_{c_rd_id}")
                edit_paid = st.number_input("Installments Paid Count", min_value=0, max_value=120, value=int(c_paid), step=1, key=f"edit_paid_{c_rd_id}")
                edit_nominee = st.text_input("Nominee Name", value=str(c_nominee) if c_nominee else "", key=f"edit_nominee_{c_rd_id}")
            
            col_e3, col_e4 = st.columns(2)
            with col_e3:
                edit_status = st.selectbox("Account Status", ["ACTIVE", "CLOSED"], index=0 if c_status == 'ACTIVE' else 1, key=f"edit_status_{c_rd_id}")
                edit_created = st.text_input("A/c Opening Date (YYYY-MM-DD)", value=str(c_created) if c_created else datetime.now(IST).strftime("%Y-%m-%d"), key=f"edit_created_{c_rd_id}")
            with col_e4:
                edit_mat_date = st.text_input("Maturity Date (YYYY-MM-DD)", value=str(c_mat_date) if c_mat_date else "2026-12-20", key=f"edit_mat_date_{c_rd_id}")

            # --- Live Automatic Recalculation Engine based on Amount Paid ---
            # 1. Quarterly Compounded Formula (Banking / RBI Standard):
            calc_qc_maturity = 0.0
            if edit_col_balance > 0 and edit_tenure > 0 and edit_rate > 0:
                i_qc = edit_rate / 400.0
                p_slice = edit_col_balance / float(edit_tenure)
                for k in range(1, int(edit_tenure) + 1):
                    q_rem = (edit_tenure - k + 1) / 3.0
                    calc_qc_maturity += p_slice * ((1.0 + i_qc) ** q_rem)
                calc_qc_maturity = round(calc_qc_maturity, 2)
            else:
                calc_qc_maturity = float(edit_col_balance)
            calc_qc_interest = max(0.0, calc_qc_maturity - edit_col_balance)

            # 2. Standard RD Cumulative Formula: Amount Paid * (Rate / 100) * ((Tenure + 1) / 24)
            calc_rd_interest = float(edit_col_balance * (edit_rate / 100.0) * ((edit_tenure + 1) / 24.0))
            calc_rd_maturity = float(edit_col_balance + calc_rd_interest)
            
            st.markdown("---")
            st.markdown("#### ⚡ Live Maturity Amount Selection")
            
            # Formulate options including existing stored certificate amount if available
            calc_options = []
            if c_maturity and float(c_maturity) > 0:
                calc_options.append(f"📄 Keep Stored Certificate Amount: ₹{float(c_maturity):,.2f}")
            calc_options.append(f"🏦 Quarterly Compounded Banking Formula (Maturity: ₹{calc_qc_maturity:,.2f} | Interest: ₹{calc_qc_interest:,.2f})")
            calc_options.append(f"⚡ Standard Cumulative RD Formula (Maturity: ₹{calc_rd_maturity:,.2f} | Interest: ₹{calc_rd_interest:,.2f})")
            calc_options.append("✍️ Enter Custom Manual Maturity Amount")
            
            calc_method = st.radio(
                "Select Maturity Amount Calculation",
                calc_options,
                index=0,
                key=f"calc_method_{c_rd_id}"
            )
            
            if "Keep Stored Certificate" in calc_method:
                final_maturity_amt = float(c_maturity)
                final_interest = max(0.0, final_maturity_amt - edit_col_balance)
            elif "Quarterly Compounded" in calc_method:
                final_interest = calc_qc_interest
                final_maturity_amt = calc_qc_maturity
            elif "Standard Cumulative" in calc_method:
                final_interest = calc_rd_interest
                final_maturity_amt = calc_rd_maturity
            else:
                final_maturity_amt = st.number_input(
                    "Enter Custom Maturity Amount (₹)",
                    min_value=0.0,
                    value=float(c_maturity) if c_maturity else calc_qc_maturity,
                    step=1000.0,
                    key=f"custom_mat_amt_{c_rd_id}"
                )
                final_interest = max(0.0, final_maturity_amt - edit_col_balance)
            
            m_col1, m_col2, m_col3 = st.columns(3)
            m_col1.metric("💰 Amount Paid / Deposited", f"₹{edit_col_balance:,.2f}")
            m_col2.metric("📈 Calculated Interest", f"₹{final_interest:,.2f}")
            m_col3.metric("🎯 Total Maturity Amount", f"₹{final_maturity_amt:,.2f}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            btn_col1, btn_col2 = st.columns([3, 1])
            
            with btn_col1:
                if st.button("💾 Save & Update RD Account Changes", key=f"btn_save_rd_{c_rd_id}", use_container_width=True, type="primary"):
                    run_query("""
                        UPDATE recurring_deposits 
                        SET monthly_amount = ?,
                            tenure_months = ?,
                            interest_rate = ?,
                            installments_paid = ?,
                            nominee = ?,
                            status = ?,
                            created_at = ?,
                            maturity_amount = ?,
                            rd_no = ?,
                            scheme_name = ?,
                            maturity_date = ?,
                            collected_balance = ?
                        WHERE rd_id = ?
                    """, (edit_monthly, edit_tenure, edit_rate, edit_paid, edit_nominee, 
                          edit_status, edit_created, final_maturity_amt, edit_rd_no, 
                          edit_scheme, edit_mat_date, edit_col_balance, c_rd_id), fetch=False)
                    
                    st.success(f"✅ Recurring Deposit #{edit_rd_no} updated successfully! Amount Paid: ₹{edit_col_balance:,.2f} | Maturity: ₹{final_maturity_amt:,.2f}")
                    time.sleep(0.1)
                    st.rerun()
            
            with btn_col2:
                with st.popover("🗑️ Delete RD"):
                    st.error(f"Are you sure you want to delete RD #{edit_rd_no}?")
                    if st.button("Confirm Delete Permanently", key=f"btn_del_rd_{c_rd_id}", type="primary", use_container_width=True):
                        run_query("DELETE FROM recurring_deposits WHERE rd_id = ?", (c_rd_id,), fetch=False)
                        st.success(f"🗑️ Recurring Deposit #{edit_rd_no} deleted successfully!")
                        time.sleep(0.1)
                        st.rerun()
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
        accounts = run_query("SELECT account_code, account_name, account_type, category FROM chart_of_accounts ORDER BY account_code")
        if accounts:
            df_coa = pd.DataFrame(accounts, columns=["Account Code", "Account Name", "Account Type", "Category"])
            st.dataframe(df_coa, use_container_width=True)

            # Option to manually trigger resequencing of all accounts to resolve gaps
            st.markdown('<div class="resequence-btn-container">', unsafe_allow_html=True)
            if st.button("🛠️ Force Resequence Account Codes (Enforce strict 101+ order)", use_container_width=True):
                from database import resequence_all_accounts, reconcile_books
                try:
                    resequence_all_accounts()
                    reconcile_books()
                    st.success("✅ Resequenced and reconciled Chart of Accounts successfully! All account codes are now in order.")
                    time.sleep(0.1)
                    st.rerun()
                except Exception as ex:
                    st.error(f"❌ Resequencing error: {str(ex)}")
            st.markdown('</div>', unsafe_allow_html=True)

            st.divider()
            st.subheader("🗑️ Delete Account Head")
            del_code = st.selectbox("Select Account Code to Delete", df_coa["Account Code"].tolist())
            if st.button("Delete Account Head", type="primary", use_container_width=True):
                try:
                    run_query("DELETE FROM chart_of_accounts WHERE account_code = ?", (del_code,), fetch=False)
                    st.success(f"Successfully deleted account code: {del_code}")
                    time.sleep(0.1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not delete account. Error: {e}")
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
                        st.success(f"Account head '{input_code} - {input_name}' saved successfully!")
                        time.sleep(0.1)
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
                
            coa_list = run_query("SELECT account_code, account_name FROM chart_of_accounts ORDER BY account_code")
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
                            st.error(f"❌ Insufficient Cash Balance! Available: ₹{current_cash_balance:,.2f}")
                            st.stop()
                        if account_code == 'AST-101':
                            st.error("❌ Cannot transfer cash to itself!")
                            st.stop()
                    
                    elif entry_type == "DEBIT (Receipt)":
                        if account_code == 'AST-102' and current_union_balance < amount:
                            st.error(f"❌ Insufficient Union Bank Balance! Available: ₹{current_union_balance:,.2f}")
                            st.stop()
                        elif account_code == 'AST-103' and current_sbi_balance < amount:
                            st.error(f"❌ Insufficient SBI Balance! Available: ₹{current_sbi_balance:,.2f}")
                            st.stop()
                        elif account_code == 'AST-101':
                            st.error("❌ Cannot receipt cash from itself!")
                            st.stop()
                    
                    from database import record_cash_book_transaction
                    success, res_val = record_cash_book_transaction(entry_type, amount, account_code, particulars, narration, tx_date)
                    if success:
                        st.success(f"✅ Cash entry recorded! Voucher: {res_val}")
                        time.sleep(0.1)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to record cash entry: {res_val}")

    with tab2:
        col_date1, col_date2 = st.columns(2)
        from_date = col_date1.date_input("From Date", value=date.today() - timedelta(days=30), key="cb_view_from", format="DD-MM-YYYY")
        to_date = col_date2.date_input("To Date", value=date.today(), key="cb_view_to", format="DD-MM-YYYY")
        
        entries = run_query("""
            SELECT cb.id, cb.date, cb.voucher_no, 
                   COALESCE(co.account_code || ' - ' || co.account_name, cb.account_code) as account_head,
                   cb.particulars, cb.debit_amount, cb.credit_amount, cb.balance, cb.narration 
            FROM cash_book cb
            LEFT JOIN chart_of_accounts co ON cb.account_code = co.account_code
            WHERE cb.date BETWEEN ? AND ? 
            ORDER BY cb.id DESC
        """, (str(from_date), str(to_date)))
        if entries:
            df_cash = pd.DataFrame(entries, columns=["ID", "Date", "Voucher No", "Account Head", "Particulars", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Narration"])
            st.dataframe(format_df_dates(df_cash), use_container_width=True)
            
            del_id = st.number_input("Enter Cash Entry ID to Delete", min_value=1, step=1, key="del_cash_id")
            if st.button("Delete Cash Entry", use_container_width=True):
                # Fetch voucher no before deleting
                c_row = run_query("SELECT voucher_no FROM cash_book WHERE id=?", (del_id,))
                if c_row:
                    voucher_no = c_row[0][0]
                    # Delete the related JV (cascades to jv_entries automatically!)
                    jv_row = run_query("SELECT jv_id FROM journal_vouchers WHERE narration LIKE ?", (f"%{voucher_no}%",))
                    if jv_row:
                        run_query("DELETE FROM journal_vouchers WHERE jv_id=?", (jv_row[0][0],), fetch=False)
                
                run_query("DELETE FROM cash_book WHERE id=?", (del_id,), fetch=False)
                sync_db_sequences()
                st.warning(f"Cash Entry ID {del_id} and related ledger entries deleted successfully.")
                time.sleep(0.1)
                st.rerun()
        else:
            st.info("No cash book entries found in this date range.")

    with tab3:
        st.subheader("Edit Existing Cash Entry")
        edit_id = st.number_input("Enter Cash Entry ID to Edit", min_value=1, step=1, key="edit_cash_id_input")
        entry_to_edit = run_query("SELECT id, particulars, debit_amount, credit_amount, narration, account_code, voucher_no, date FROM cash_book WHERE id=?", (edit_id,))
        
        if entry_to_edit:
            row = entry_to_edit[0]
            # row = (id, particulars, debit_amount, credit_amount, narration, account_code, voucher_no, date)
            coa_list = run_query("SELECT account_code, account_name FROM chart_of_accounts ORDER BY account_code")
            coa_dict = {f"{c[0]} - {c[1]}": c[0] for c in coa_list}
            coa_keys = list(coa_dict.keys())
            
            curr_acc = row[5]
            default_index = 0
            for idx, k in enumerate(coa_keys):
                if coa_dict[k] == curr_acc:
                    default_index = idx
                    break
                    
            with st.form("edit_cash_form"):
                new_part = st.text_input("Particulars", value=row[1])
                curr_dr = row[2] if row[2] > 0 else row[3]
                is_debit = row[2] > 0
                new_type = st.selectbox("Type", ["DEBIT (Receipt)", "CREDIT (Payment)"], index=0 if is_debit else 1)
                new_amt = st.number_input("Amount (₹)", min_value=1.0, value=float(curr_dr))
                new_acc_head = st.selectbox("Corresponding Account Head", coa_keys, index=default_index)
                new_narration = st.text_area("Narration", value=row[4] if row[4] else "")
                
                if st.form_submit_button("Update Cash Entry", use_container_width=True):
                    new_acc_code = coa_dict[new_acc_head]
                    voucher_no = row[6]
                    
                    from database import update_cash_book_transaction
                    success, res_val = update_cash_book_transaction(edit_id, new_type, new_amt, new_acc_code, new_part, new_narration, voucher_no)
                    if success:
                        st.success("✅ Cash Entry and Ledger updated successfully!")
                        time.sleep(0.1)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to update entry: {res_val}")

    with tab4:
        col_date1, col_date2 = st.columns(2)
        from_date = col_date1.date_input("From Date", value=date.today() - timedelta(days=30), key="cb_print_from", format="DD-MM-YYYY")
        to_date = col_date2.date_input("To Date", value=date.today(), key="cb_print_to", format="DD-MM-YYYY")
        
        entries = run_query("""
            SELECT cb.date, cb.voucher_no, 
                   COALESCE(co.account_code || ' - ' || co.account_name, cb.account_code) as account_head,
                   cb.particulars, cb.debit_amount, cb.credit_amount, cb.balance, cb.narration 
            FROM cash_book cb
            LEFT JOIN chart_of_accounts co ON cb.account_code = co.account_code
            WHERE cb.date BETWEEN ? AND ? 
            ORDER BY cb.id ASC
        """, (str(from_date), str(to_date)))
        if entries:
            df_print = pd.DataFrame(entries, columns=["Date", "Voucher No", "Account Head", "Particulars", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Narration"])
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
        
        cb_records = run_query("""
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
    staff_names = ['SREEKALA J', 'SASIKUMARAN A', 'BINU B', 'KEERTHI R', 'SREEJITH RADHAKRISHNAN', 'LEKSHMI SK', 'SREEKALA', 'SASIKUMARAN', 'SREEJITH', 'BINU', 'KEERTHI']
    if acc_code == 'EXP-104' or any(k in p.lower() for k in ['salary', 'salaries', 'staff']):
        for sn in staff_names:
            if re.search(r'\b' + re.escape(sn) + r'\b', p, re.IGNORECASE):
                return f"Staff Salary: {sn}"
        return "Staff Salaries & Benefits"
        
    # 2. Match Registered Customers
    for cid, cname, cacc in cust_list:
        if cacc and len(str(cacc)) >= 4 and str(cacc) in p:
            return f"{cname} (Acc: {cacc})"
        c_parts = [part.strip() for part in re.split(r'[\s\.]+', cname) if len(part.strip()) >= 3 and part.upper() not in ('THE', 'AND', 'DOCTOR', 'FOR')]
        for cp in c_parts:
            if re.search(r'\b' + re.escape(cp) + r'\b', p, re.IGNORECASE):
                acc_label = f" (Acc: {cacc})" if cacc else ""
                return f"{cname}{acc_label}"
                
    # 3. Staff Field Collections / Staff UPI Deposits
    for sn in staff_names:
        if re.search(r'\b' + re.escape(sn) + r'\b', p, re.IGNORECASE):
            return f"Staff Field Agent: {sn}"
            
    # 4. Bank Charges / Processing
    if any(k in p.lower() for k in ['charge', 'sms', 'pord', 'gst', 'consolidated chg', 'atm']):
        return "Union Bank Processing / Service Charges"
        
    # 5. Cash Contra
    if 'cash' in p.lower() or 'contra' in p.lower() or acc_code == 'AST-101':
        return "Cash Drawer (Office Contra)"
        
    # 6. Extract UPI Member Name
    upi_match = re.search(r'/CR/([^/]+)/', p, re.IGNORECASE)
    if upi_match:
        name_clean = upi_match.group(1).strip()
        if name_clean and len(name_clean) > 1:
            return f"Member: {name_clean}"
            
    # 7. Extract NEFT Party Name
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
                
            coa_list = run_query("SELECT account_code, account_name FROM chart_of_accounts ORDER BY account_code")
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
                        # This increases selected bank, but we must check if the funding source has enough balance
                        if account_code == 'AST-101':
                            current_cash = get_cash_balance()
                            if current_cash < amount:
                                st.error(f"❌ Insufficient Cash Balance to deposit! Available: ₹{current_cash:,.2f}")
                                st.stop()
                        elif account_code == 'AST-102':
                            current_union = get_bank_balance("Union Bank of India")
                            if current_union < amount:
                                st.error(f"❌ Insufficient Union Bank Balance to transfer! Available: ₹{current_union:,.2f}")
                                st.stop()
                                
                    from database import record_bank_book_transaction
                    success, res_val = record_bank_book_transaction(entry_type, amount, bank_name, bank_code, account_code, particulars, narration, tx_date)
                    if success:
                        st.success(f"✅ Bank entry successfully recorded! Voucher: {res_val}")
                        time.sleep(0.1)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to record bank entry: {res_val}")

    with tab2:
        col_date1, col_date2 = st.columns(2)
        from_date = col_date1.date_input("From Date", value=date.today() - timedelta(days=30), key="bb_view_from", format="DD-MM-YYYY")
        to_date = col_date2.date_input("To Date", value=date.today(), key="bb_view_to", format="DD-MM-YYYY")
        
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
            ORDER BY bb.id DESC
        """
        entries = run_query(bb_query, (str(from_date), str(to_date)))
        if entries:
            cust_list = run_query("SELECT id, name, COALESCE(account_no, '') FROM customers") or []
            formatted_entries = []
            for r in entries:
                party = extract_party_details(r[5], r[11], r[12], cust_list)
                formatted_entries.append((r[0], r[1], r[2], r[3], r[4], party, r[5], r[6], r[7], r[8], r[9], r[10]))
            df_bank = pd.DataFrame(formatted_entries, columns=["ID", "Date", "Voucher No", "Debit Side (Inflow)", "Credit Side (Outflow)", "Customer / Party Details", "Particulars", "Deposit (₹)", "Withdrawal (₹)", "Balance (₹)", "Bank", "Narration"])
            st.dataframe(format_df_dates(df_bank), use_container_width=True)
            
            del_id = st.number_input("Enter Bank Entry ID to Delete", min_value=1, step=1, key="del_bank_id")
            if st.button("Delete Bank Entry", use_container_width=True):
                # Fetch voucher no before deleting
                b_row = run_query("SELECT voucher_no FROM bank_book WHERE id=?", (del_id,))
                if b_row:
                    voucher_no = b_row[0][0]
                    # Delete the related JV (cascades to jv_entries automatically!)
                    jv_row = run_query("SELECT jv_id FROM journal_vouchers WHERE narration LIKE ?", (f"%{voucher_no}%",))
                    if jv_row:
                        run_query("DELETE FROM journal_vouchers WHERE jv_id=?", (jv_row[0][0],), fetch=False)
                
                run_query("DELETE FROM bank_book WHERE id=?", (del_id,), fetch=False)
                sync_db_sequences()
                st.warning(f"Bank Entry ID {del_id} and related ledger entries deleted successfully.")
                time.sleep(0.1)
                st.rerun()
        else:
            st.info("No bank entries found in this date range.")

    with tab3:
        st.subheader("Edit Existing Bank Entry")
        edit_bank_id = st.number_input("Enter Bank Entry ID to Edit", min_value=1, step=1, key="edit_bank_id_input")
        bank_row = run_query("SELECT id, particulars, debit_amount, credit_amount, bank_name, narration, account_code, voucher_no, date FROM bank_book WHERE id=?", (edit_bank_id,))
        
        if bank_row:
            row = bank_row[0]
            # row = (id, particulars, debit_amount, credit_amount, bank_name, narration, account_code, voucher_no, date)
            coa_list = run_query("SELECT account_code, account_name FROM chart_of_accounts ORDER BY account_code")
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
                
                new_head = st.selectbox("Account Head", list(coa_dict.keys()), index=list(coa_dict.keys()).index(current_head_key) if current_head_key in coa_dict else 0)
                new_part = st.text_input("Particulars", value=row[1])
                new_narration = st.text_area("Narration", value=row[5] or "")
                
                if st.form_submit_button("Save Changes", use_container_width=True):
                    new_acc_code = coa_dict[new_head]
                    d_amt = new_amt if "DEBIT" in new_type else 0.0
                    c_amt = new_amt if "CREDIT" in new_type else 0.0
                    voucher_no = row[7]
                    bank_name = row[4]
                    bank_code = "AST-102"
                    
                    # 1. Check Cash Balance if adjusting deposit from Cash
                    if new_acc_code == 'AST-101' and "DEBIT" in new_type:
                        cur_cash = get_cash_balance()
                        if cur_cash < new_amt:
                            st.error(f"❌ Insufficient Cash Balance! Available: ₹{cur_cash:,.2f}")
                            st.stop()
                    
                    # 2. Update the bank_book entry
                    run_query("""
                        UPDATE bank_book 
                        SET particulars = ?, debit_amount = ?, credit_amount = ?, account_code = ?, narration = ? 
                        WHERE id = ?
                    """, (new_part, d_amt, c_amt, new_acc_code, new_narration, edit_bank_id), fetch=False)
                    
                    # 3. Locate and update the related Journal Voucher
                    jv_row = run_query("SELECT jv_id FROM journal_vouchers WHERE narration LIKE ?", (f"%{voucher_no}%",))
                    if jv_row:
                        jv_id = jv_row[0][0]
                        full_narration = new_part
                        if new_narration.strip():
                            full_narration += f" ({new_narration.strip()})"
                        
                        # Update JV header
                        jv_prefix = "Bank Deposit" if "DEBIT" in new_type else "Bank Withdrawal"
                        run_query("UPDATE journal_vouchers SET narration = ? WHERE jv_id = ?", (f"{jv_prefix} [{voucher_no}]: {full_narration} - {bank_name}", jv_id), fetch=False)
                        
                        # Update JV entries (delete old ones and recreate to ensure perfect balance and account mapping)
                        run_query("DELETE FROM jv_entries WHERE jv_id = ?", (jv_id,), fetch=False)
                        if "DEBIT" in new_type:
                            run_query("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, bank_code, new_amt), fetch=False)
                            run_query("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, new_acc_code, new_amt), fetch=False)
                        else:
                            run_query("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, new_acc_code, new_amt), fetch=False)
                            run_query("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, bank_code, new_amt), fetch=False)
                            
                    st.success("Bank Entry and Ledger updated successfully!")
                    time.sleep(0.1)
                    st.rerun()

    with tab4:
        col_date1, col_date2 = st.columns(2)
        from_date = col_date1.date_input("From Date", value=date.today() - timedelta(days=30), key="bb_print_from", format="DD-MM-YYYY")
        to_date = col_date2.date_input("To Date", value=date.today(), key="bb_print_to", format="DD-MM-YYYY")
        
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
            ORDER BY bb.id ASC
        """
        entries = run_query(bb_print_query, (str(from_date), str(to_date)))
        if entries:
            cust_list = run_query("SELECT id, name, COALESCE(account_no, '') FROM customers") or []
            formatted_print = []
            for r in entries:
                party = extract_party_details(r[4], r[10], r[11], cust_list)
                formatted_print.append((r[0], r[1], r[2], r[3], party, r[4], r[5], r[6], r[7], r[8], r[9]))
            df_print = pd.DataFrame(formatted_print, columns=["Date", "Voucher No", "Debit Side (Inflow)", "Credit Side (Outflow)", "Customer / Party Details", "Particulars", "Deposit (₹)", "Withdrawal (₹)", "Balance (₹)", "Bank", "Narration"])
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
        
        bb_records = run_query("""
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
        
        coa_list = run_query("SELECT account_code, account_name, account_type FROM chart_of_accounts ORDER BY account_code")
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
                elif acc2_code in ['AST-101', 'AST-102', 'AST-103'] and get_account_balance_from_jv(acc2_code) < dr1:
                    avail_bal = get_account_balance_from_jv(acc2_code)
                    st.error(f"❌ Insufficient balance in credit account {acc2_code}! Available: ₹{avail_bal:,.2f}, Required: ₹{dr1:,.2f}")
                else:
                    jv_id = post_automated_jv(narration, acc1_code, acc2_code, dr1)
                    if jv_id:
                        st.success(f"✅ Journal Voucher JV-{jv_id} posted successfully!")
                        time.sleep(0.1)
                        st.rerun()

    with tab2:
        col_date1, col_date2 = st.columns(2)
        from_date = col_date1.date_input("From Date", value=date.today() - timedelta(days=30), key="jv_view_from", format="DD-MM-YYYY")
        to_date = col_date2.date_input("To Date", value=date.today(), key="jv_view_to", format="DD-MM-YYYY")
        
        jvs = run_query("""
            SELECT jv_id, voucher_date, narration, status 
            FROM journal_vouchers 
            WHERE voucher_date BETWEEN ? AND ? 
            ORDER BY jv_id DESC
        """, (str(from_date), str(to_date)))
        if jvs:
            df_jvs = pd.DataFrame(jvs, columns=["JV ID", "Date", "Narration", "Status"])
            st.dataframe(format_df_dates(df_jvs), use_container_width=True)
        else:
            st.info("No journal vouchers found in this date range.")

    with tab3:
        st.subheader("🖨️ Journal Voucher (JV) Drill-Down Print")
        col_date1, col_date2 = st.columns(2)
        from_date = col_date1.date_input("From Date", value=date.today() - timedelta(days=30), key="jv_print_from", format="DD-MM-YYYY")
        to_date = col_date2.date_input("To Date", value=date.today(), key="jv_print_to", format="DD-MM-YYYY")
        
        jv_records = run_query("""
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
        tables_res = run_query("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name NOT LIKE 'pg_%' ORDER BY table_name")
    else:
        tables_res = run_query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    
    table_list = [t[0] for t in tables_res] if tables_res else []
    selected_table = st.selectbox("Select Database Table to Manage", table_list)
    
    if selected_table:
        if USING_SUPABASE:
            cols = run_query("SELECT column_name FROM information_schema.columns WHERE table_name = ? AND table_schema = 'public' ORDER BY ordinal_position", (selected_table,))
            col_names = [c[0] for c in cols] if cols else []
            pk_res = run_query("""
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_name = ? AND tc.table_schema = 'public'
            """, (selected_table,))
            pk_col = pk_res[0][0] if pk_res else (col_names[0] if col_names else None)
        else:
            pk_info = run_query(f"PRAGMA table_info({selected_table})")
            pk_col = next((col[1] for col in pk_info if col[5] == 1), pk_info[0][1] if pk_info else None)
            col_names = [col[1] for col in pk_info] if pk_info else []
        
        rows = run_query(f"SELECT * FROM {selected_table}")
        
        if rows:
            # Clean display for dataframe (format binary data nicely)
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
                    run_query(f"DELETE FROM {selected_table} WHERE {pk_col} = ?", (val,), fetch=False)
                    sync_db_sequences()
                    st.success("Record deleted and sequences synced!")
                    time.sleep(0.1)
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
                                st.success("Record updated successfully!")
                                time.sleep(0.1)
                                st.rerun()
                    else:
                        st.info(f"No record found with {pk_col} = {edit_val}")

def render_financial_statements():
    st.title("⚖️ Financial Statements")
    tab1, tab2, tab3, tab4 = st.tabs(["Trial Balance", "Balance Sheet", "Profit & Loss Statement", "Ledger Print"])
    
    with tab1:
        st.subheader("Trial Balance Summary")
        if USING_SUPABASE:
            entries = run_query("""
                SELECT CO.account_code, CO.account_name, CO.account_type, 
                       COALESCE(SUM(JE.debit), 0) as total_debit, COALESCE(SUM(JE.credit), 0) as total_credit
                FROM chart_of_accounts CO
                LEFT JOIN jv_entries JE ON CO.account_code = JE.account_code
                GROUP BY CO.account_code, CO.account_name, CO.account_type
                HAVING COALESCE(SUM(JE.debit), 0) > 0 OR COALESCE(SUM(JE.credit), 0) > 0
                ORDER BY CO.account_type, CO.account_code
            """)
        else:
            entries = run_query("""
                SELECT CO.account_code, CO.account_name, CO.account_type, 
                       COALESCE(SUM(JE.debit), 0) as total_debit, COALESCE(SUM(JE.credit), 0) as total_credit
                FROM chart_of_accounts CO
                LEFT JOIN jv_entries JE ON CO.account_code = JE.account_code
                GROUP BY CO.account_code
                HAVING total_debit > 0 OR total_credit > 0
                ORDER BY CO.account_type, CO.account_code
            """)
        if entries:
            df_tb = pd.DataFrame(entries, columns=["Account Code", "Account Name", "Account Type", "Total Debit", "Total Credit"])
            st.dataframe(df_tb, use_container_width=True)
            total_debits = sum(row[3] for row in entries)
            total_credits = sum(row[4] for row in entries)
            st.metric("Total Debits / Credits Balance", f"Dr. ₹{total_debits:,.2f} | Cr. ₹{total_credits:,.2f}")
            st.download_button("📥 Download Trial Balance PDF", pdf_generator.create_pdf_report("Trial Balance Statement", df_tb), "trial_balance.pdf", "application/pdf", use_container_width=True)
            
    with tab2:
        st.subheader("Balance Sheet (Assets, Liabilities & Equity)")
        # Fetch all account balances in a single database roundtrip
        if USING_SUPABASE:
            raw_balances = run_query("""
                SELECT 
                    CO.account_code, 
                    CO.account_name, 
                    CO.account_type, 
                    CO.category,
                    COALESCE(SUM(JE.debit), 0) as total_debit,
                    COALESCE(SUM(JE.credit), 0) as total_credit
                FROM chart_of_accounts CO 
                LEFT JOIN jv_entries JE ON CO.account_code = JE.account_code
                GROUP BY CO.account_code, CO.account_name, CO.account_type, CO.category
            """)
        else:
            raw_balances = run_query("""
                SELECT 
                    CO.account_code, 
                    CO.account_name, 
                    CO.account_type, 
                    CO.category,
                    COALESCE(SUM(JE.debit), 0) as total_debit,
                    COALESCE(SUM(JE.credit), 0) as total_credit
                FROM chart_of_accounts CO 
                LEFT JOIN jv_entries JE ON CO.account_code = JE.account_code
                GROUP BY CO.account_code
            """)

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
                    
        tot_inc = sum(info.get("net_lia_eq_inc", 0.0) for code, info in balance_dict.items() if info.get("type") == "Income")
        tot_exp = sum(info.get("net_asset_exp", 0.0) for code, info in balance_dict.items() if info.get("type") == "Expense")
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
                
            if USING_SUPABASE:
                equity_details = run_query("""
                    SELECT 
                        CO.account_name, 
                        COALESCE(JV.narration, CO.account_name) as narration_label,
                        COALESCE(SUM(JE.credit - JE.debit), 0) as net_balance
                    FROM jv_entries JE 
                    JOIN chart_of_accounts CO ON JE.account_code = CO.account_code
                    JOIN journal_vouchers JV ON JE.jv_id = JV.jv_id
                    WHERE CO.account_type = 'Equity'
                    GROUP BY CO.account_code, CO.account_name, JV.narration
                    HAVING COALESCE(SUM(JE.credit - JE.debit), 0) != 0
                """)
            else:
                equity_details = run_query("""
                    SELECT 
                        CO.account_name, 
                        COALESCE(JV.narration, CO.account_name) as narration_label,
                        COALESCE(SUM(JE.credit - JE.debit), 0) as net_balance
                    FROM jv_entries JE 
                    JOIN chart_of_accounts CO ON JE.account_code = CO.account_code
                    JOIN journal_vouchers JV ON JE.jv_id = JV.jv_id
                    WHERE CO.account_type = 'Equity'
                    GROUP BY CO.account_code, JV.narration
                    HAVING net_balance != 0
                """)
            if equity_details:
                for row in equity_details:
                    acc_name, narration_label, net_balance = row
                    
                    # Clean up technical prefixes from narration for a professional statement look
                    display_label = narration_label
                    for prefix in ["Bank Deposit: ", "Cash Receipt: ", "Bank Withdrawal: ", "Cash Payment: "]:
                        if display_label.startswith(prefix):
                            display_label = display_label[len(prefix):]
                    
                    # If it's a generic auto-posted entry or same as account name, show account name, else include name detail
                    if display_label == acc_name or not display_label:
                        label = acc_name
                    else:
                        label = f"{acc_name} ({display_label})"
                        
                    lia_data.append([label, f"₹{net_balance:,.2f}"])
                    total_lia += net_balance
            
            if net_profit_loss != 0:
                label_pnl = "Profit / Loss (Current Year)"
                lia_data.append([label_pnl, f"₹{net_profit_loss:,.2f}"])
                total_lia += net_profit_loss
                
            if lia_data:
                df_lia = pd.DataFrame(lia_data, columns=["Account", "Amount"])
                st.dataframe(df_lia, use_container_width=True, hide_index=True)
                st.metric("Total Liabilities & Equity", f"₹{total_lia:,.2f}")
 
    with tab3:
        st.subheader("Profit and Loss Account")
        if USING_SUPABASE:
            income_details = run_query("""
                SELECT CO.account_code, CO.account_name, COALESCE(SUM(JE.credit - JE.debit), 0) as balance
                FROM chart_of_accounts CO JOIN jv_entries JE ON CO.account_code = JE.account_code
                WHERE CO.account_type = 'Income' 
                GROUP BY CO.account_code, CO.account_name 
                HAVING COALESCE(SUM(JE.credit - JE.debit), 0) != 0
            """)
            expense_details = run_query("""
                SELECT CO.account_code, CO.account_name, COALESCE(SUM(JE.debit - JE.credit), 0) as balance
                FROM chart_of_accounts CO JOIN jv_entries JE ON CO.account_code = JE.account_code
                WHERE CO.account_type = 'Expense' 
                GROUP BY CO.account_code, CO.account_name 
                HAVING COALESCE(SUM(JE.debit - JE.credit), 0) != 0
            """)
        else:
            income_details = run_query("""
                SELECT CO.account_code, CO.account_name, COALESCE(SUM(JE.credit - JE.debit), 0) as balance
                FROM chart_of_accounts CO JOIN jv_entries JE ON CO.account_code = JE.account_code
                WHERE CO.account_type = 'Income' GROUP BY CO.account_code HAVING balance != 0
            """)
            expense_details = run_query("""
                SELECT CO.account_code, CO.account_name, COALESCE(SUM(JE.debit - JE.credit), 0) as balance
                FROM chart_of_accounts CO JOIN jv_entries JE ON CO.account_code = JE.account_code
                WHERE CO.account_type = 'Expense' GROUP BY CO.account_code HAVING balance != 0
            """)
        
        col_pl1, col_pl2 = st.columns(2)
        with col_pl1:
            st.markdown("### Expenditure")
            exp_rows = [[f"{row[0]} - {row[1]}", f"₹{row[2]:,.2f}"] for row in expense_details] if expense_details else []
            total_exp_v = sum(row[2] for row in expense_details) if expense_details else 0.0
            if exp_rows:
                st.dataframe(pd.DataFrame(exp_rows, columns=["Expense Account", "Amount"]), use_container_width=True, hide_index=True)
            st.metric("Total Expenditure", f"₹{total_exp_v:,.2f}")
            
        with col_pl2:
            st.markdown("### Income")
            inc_rows = [[f"{row[0]} - {row[1]}", f"₹{row[2]:,.2f}"] for row in income_details] if income_details else []
            total_inc_v = sum(row[2] for row in income_details) if income_details else 0.0
            if inc_rows:
                st.dataframe(pd.DataFrame(inc_rows, columns=["Income Account", "Amount"]), use_container_width=True, hide_index=True)
            st.metric("Total Income", f"₹{total_inc_v:,.2f}")
            
        st.divider()
        net_result = total_inc_v - total_exp_v
        if net_result > 0:
            st.success(f"**Net Profit for the Period:** ₹{net_result:,.2f}")
        elif net_result < 0:
            st.error(f"**Net Loss for the Period:** ₹{abs(net_result):,.2f}")

    with tab4:
        st.subheader("🖨️ General Ledger Statement Print")
        
        # Date filter selection
        col_date1, col_date2 = st.columns(2)
        from_date = col_date1.date_input("From Date", value=date.today() - timedelta(days=30), format="DD-MM-YYYY")
        to_date = col_date2.date_input("To Date", value=date.today(), format="DD-MM-YYYY")
        
        # Load account heads for select box
        coa_list = run_query("SELECT account_code, account_name, account_type FROM chart_of_accounts ORDER BY account_code")
        coa_dict = {f"{c[0]} - {c[1]} ({c[2]})": (c[0], c[1], c[2]) for c in coa_list}
        
        selected_head = st.selectbox("Select Account Head for Ledger", list(coa_dict.keys()))
        
        if selected_head:
            acc_code, acc_name, acc_type = coa_dict[selected_head]
            
            # 1. Calculate Opening Balance before from_date
            if acc_type in ['Asset', 'Expense']:
                # Balance = Debit - Credit
                op_bal_row = run_query("""
                    SELECT COALESCE(SUM(JE.debit - JE.credit), 0)
                    FROM jv_entries JE 
                    JOIN journal_vouchers JV ON JE.jv_id = JV.jv_id
                    WHERE JE.account_code = ? AND JV.voucher_date < ?
                """, (acc_code, str(from_date)))
            else:
                # Balance = Credit - Debit (Liability, Equity, Income)
                op_bal_row = run_query("""
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
            ledger_rows = run_query("""
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
            df_display["Debit (₹)"] = df_display["Debit (₹)"].apply(lambda x: f"₹{x:,.2f}" if x > 0 else "-")
            df_display["Credit (₹)"] = df_display["Credit (₹)"].apply(lambda x: f"₹{x:,.2f}" if x > 0 else "-")
            df_display["Balance (₹)"] = df_display["Balance (₹)"].apply(lambda x: f"₹{x:,.2f}")
            df_display["Balance (₹)"] = df_display["Balance (₹)"] + " (" + df_display["Type"] + ")"
            df_display.drop(columns=["Type"], inplace=True)
            
            # Show table
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Export to PDF
            df_pdf = format_df_dates(df_ledger.copy())
            df_pdf["Debit (₹)"] = df_pdf["Debit (₹)"].apply(lambda x: f"₹{x:,.2f}" if x > 0 else "-")
            df_pdf["Credit (₹)"] = df_pdf["Credit (₹)"].apply(lambda x: f"₹{x:,.2f}" if x > 0 else "-")
            df_pdf["Balance (₹)"] = df_pdf["Balance (₹)"].apply(lambda x: f"₹{x:,.2f}")
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
                data = run_query("SELECT id, name, phone, email, kyc_status, created_at FROM customers")
                columns = ["ID", "Name", "Phone", "Email", "KYC Status", "Registered Date"]
            elif report_type == "Daily Transactions Report":
                data = run_query("SELECT tx_id, account_no, type, amount, mode, narration, date FROM transactions ORDER BY date ASC, tx_id ASC")
                columns = ["Tx ID", "Account No", "Type", "Amount (₹)", "Mode", "Narration", "Date"]
            elif report_type == "SB Accounts Report":
                data = run_query("SELECT s.account_no, c.name, s.balance, s.interest_rate, s.created_at FROM sb_accounts s JOIN customers c ON s.customer_id = c.id")
                columns = ["Account No", "Customer Name", "Balance (₹)", "Interest Rate (%)", "Created Date"]
            elif report_type == "FD Accounts Report":
                data = run_query("SELECT f.fd_id, c.name, f.principal, f.tenure_months, f.interest_rate, f.maturity_amount, f.status, f.created_at FROM fixed_deposits f JOIN customers c ON f.customer_id = c.id")
                columns = ["FD ID", "Customer Name", "Principal (₹)", "Tenure (M)", "Rate (%)", "Maturity (₹)", "Status", "Created Date"]
            elif report_type == "RD Accounts Report":
                data = run_query("SELECT r.rd_id, c.name, r.monthly_amount, r.tenure_months, r.interest_rate, r.installments_paid, r.status, r.created_at FROM recurring_deposits r JOIN customers c ON r.customer_id = c.id")
                columns = ["RD ID", "Customer Name", "Monthly (₹)", "Tenure (M)", "Rate (%)", "Inst. Paid", "Status", "Created Date"]
            elif report_type == "Cash Book Report":
                data = run_query("SELECT date, voucher_no, particulars, debit_amount, credit_amount, balance, narration FROM cash_book ORDER BY date ASC, id ASC")
                columns = ["Date", "Voucher No", "Particulars", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Narration"]
            elif report_type == "Bank Book Report":
                data = run_query("SELECT date, voucher_no, bank_name, particulars, debit_amount, credit_amount, balance, narration FROM bank_book ORDER BY date ASC, id ASC")
                columns = ["Date", "Voucher No", "Bank", "Particulars", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Narration"]
            elif report_type == "Trial Balance Report":
                if USING_SUPABASE:
                    data = run_query("""
                        SELECT CO.account_code, CO.account_name, CO.account_type, 
                               COALESCE(SUM(JE.debit), 0) as total_debit, COALESCE(SUM(JE.credit), 0) as total_credit
                        FROM chart_of_accounts CO 
                        LEFT JOIN jv_entries JE ON CO.account_code = JE.account_code 
                        GROUP BY CO.account_code, CO.account_name, CO.account_type 
                        HAVING COALESCE(SUM(JE.debit), 0) > 0 OR COALESCE(SUM(JE.credit), 0) > 0
                    """)
                else:
                    data = run_query("""
                        SELECT CO.account_code, CO.account_name, CO.account_type, COALESCE(SUM(JE.debit), 0) as total_debit, COALESCE(SUM(JE.credit), 0) as total_credit
                        FROM chart_of_accounts CO LEFT JOIN jv_entries JE ON CO.account_code = JE.account_code GROUP BY CO.account_code HAVING total_debit > 0 OR total_credit > 0
                    """)
                columns = ["Account Code", "Account Name", "Account Type", "Total Debit (₹)", "Total Credit (₹)"]
            elif report_type == "Journal Vouchers Report":
                data = run_query("SELECT jv_id, voucher_date, narration, status FROM journal_vouchers ORDER BY voucher_date ASC, jv_id ASC")
                columns = ["JV ID", "Date", "Narration", "Status"]
                
            if data:
                df_rep = pd.DataFrame(data, columns=columns)
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
            cust_trends = run_query("SELECT substr(created_at, 1, 10) as reg_date, COUNT(*) as count FROM customers GROUP BY reg_date ORDER BY reg_date ASC")
            if cust_trends:
                df_trend = pd.DataFrame(cust_trends, columns=["Date", "Registrations"])
                fig = px.line(df_trend, x="Date", y="Registrations", title="Customer Registration Trend", markers=True)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No customer registration data available.")
        elif chart_type == "Account Distribution":
            sb_count = run_query("SELECT COUNT(*) FROM sb_accounts")[0][0]
            fd_count = run_query("SELECT COUNT(*) FROM fixed_deposits WHERE status='ACTIVE'")[0][0]
            rd_count = run_query("SELECT COUNT(*) FROM recurring_deposits WHERE status='ACTIVE'")[0][0]
            df_dist = pd.DataFrame({
                "Account Type": ["SB Accounts", "Fixed Deposits (FD)", "Recurring Deposits (RD)"],
                "Count": [sb_count, fd_count, rd_count]
            })
            fig = px.pie(df_dist, values="Count", names="Account Type", title="Accounts Share Ratio", hole=0.3)
            st.plotly_chart(fig, use_container_width=True)
        elif chart_type == "SB Account Balances":
            sb_bals = run_query("SELECT account_no, balance FROM sb_accounts")
            if sb_bals:
                df_sb_bal = pd.DataFrame(sb_bals, columns=["Account No", "Balance (₹)"])
                fig = px.bar(df_sb_bal, x="Account No", y="Balance (₹)", title="SB Account Balances Summary")
                st.plotly_chart(fig, use_container_width=True)
        elif chart_type == "FD Maturity Distribution":
            fd_mats = run_query("SELECT fd_id, maturity_amount, principal FROM fixed_deposits WHERE status='ACTIVE'")
            if fd_mats:
                df_fd_mat = pd.DataFrame(fd_mats, columns=["FD ID", "Maturity Amount (₹)", "Principal (₹)"])
                df_fd_mat["FD ID"] = df_fd_mat["FD ID"].apply(lambda x: f"FD-{x:05d}")
                fig = px.bar(df_fd_mat, x="FD ID", y="Maturity Amount (₹)", title="FD Maturity Distribution Details", hover_data=["Principal (₹)"])
                st.plotly_chart(fig, use_container_width=True)
        elif chart_type == "RD Installment Progress":
            rd_prog = run_query("SELECT rd_id, installments_paid, tenure_months FROM recurring_deposits WHERE status='ACTIVE'")
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
    
    sb_accs = run_query("SELECT s.account_no, c.name, s.balance, s.interest_rate FROM sb_accounts s JOIN customers c ON s.customer_id = c.id")
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
                        st.success(f"Interest credited successfully! Journal Reference: JV-{jv_id}")
                        time.sleep(0.1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating interest: {str(e)}")
                    finally:
                        release_connection(db_conn)

# --- MAIN RUNNING ENTRY POINT ---

def get_login_status():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = ""
    return st.session_state.logged_in

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
        <div style="text-align: center; background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%); padding: 30px 25px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.06); box-shadow: 0 8px 24px rgba(0,0,0,0.15); margin-bottom: 20px; color: white;">
            <h1 style="color: white !important; font-size: 26px; margin: 5px 0; font-weight: 800; letter-spacing: 0.8px; text-shadow: 0 2px 4px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; gap: 10px;">🏦 AARSHA NIDHI  LIMITED</h1>
            <p style="color: #cbd5e1 !important; font-size: 11px; margin: 8px 0 5px 0; font-weight: 500; opacity: 0.9;">📍 6/814, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501</p>
            <p style="color: #cbd5e1 !important; font-size: 10px; margin: 5px 0; opacity: 0.8;">📄 CIN: U65990KL22021PLN069978 | 📞 Ph: 0471-2994535</p>
        </div>
        <div style="text-align: center; margin-bottom: 15px;">
            <h2 style="color: #3b82f6; font-size: 20px; margin: 5px 0; font-weight: 700;">🔐 Banking Software Login</h2>
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
                    st.success("✅ Login successful!")
                    time.sleep(0.1)
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials.")
        st.stop()

# --- SIDEBAR STYLING ---
st.sidebar.markdown("""
<style>
    /* Premium Midnight Blue Gradient Sidebar background */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3a8a 0%, #0f172a 100%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    
    /* Clean sidebar headers and texts */
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] span, [data-testid="stSidebar"] p {
        color: #e2e8f0 !important;
    }
    
    /* Navigation Radio Items styled as custom premium tabs */
    [data-testid="stSidebar"] .stRadio > label {
        color: #94a3b8 !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        font-size: 11px !important;
        letter-spacing: 0.8px;
        padding-left: 5px;
        margin-bottom: 8px !important;
    }
    
    /* Hide the radio button circle inputs */
    [data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"] div:first-child {
        display: none !important;
    }
    
    /* Custom menu list items styling */
    [data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"] {
        background: transparent !important;
        padding: 9px 15px !important;
        border-radius: 8px !important;
        margin-bottom: 6px !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border-left: 4px solid transparent !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        box-shadow: none !important;
    }
    
    /* Hover state for menu list items */
    [data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"]:hover {
        background-color: rgba(255, 255, 255, 0.04) !important;
        color: #ffffff !important;
        border-left: 4px solid #3b82f6 !important;
        padding-left: 18px !important; /* Subtle slide-in effect */
    }
    
    /* Selected/Active state for menu list items */
    [data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) {
        background: linear-gradient(90deg, rgba(59, 130, 246, 0.15) 0%, rgba(59, 130, 246, 0.03) 100%) !important;
        color: #ffffff !important;
        border-left: 4px solid #3b82f6 !important;
        font-weight: 600 !important;
        box-shadow: inset 1px 0 0 rgba(255,255,255,0.05) !important;
    }
    
    /* Sidebar Header brand styling */
    .sidebar-header {
        text-align: center;
        padding: 20px 10px 15px 10px;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        margin: 10px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    .sidebar-header h2 {
        color: #ffffff !important;
        font-size: 20px !important;
        font-weight: 800 !important;
        margin: 0 !important;
        letter-spacing: 0.5px;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .sidebar-header p {
        color: #64748b !important;
        font-size: 11px !important;
        font-weight: 500;
        margin: 4px 0 0 0 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .sidebar-divider {
        border-top: 1px solid rgba(255, 255, 255, 0.08);
        margin: 15px 10px;
    }
    
    .user-info {
        color: #94a3b8 !important;
        font-size: 12px;
        padding: 5px 0;
        text-align: center;
        font-weight: 500;
    }
    
    /* Live Pulsating Green Dot animation */
    .pulse-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        background-color: #10b981;
        border-radius: 50%;
        margin-right: 6px;
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
        animation: pulse-live 1.8s infinite;
        vertical-align: middle;
    }
    @keyframes pulse-live {
        0% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
        }
        70% {
            transform: scale(1);
            box-shadow: 0 0 0 6px rgba(16, 185, 129, 0);
        }
        100% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
        }
    }
    
    /* Styled digital clock with Glassmorphism */
    .ist-clock-card {
        text-align: center;
        background: #000000 !important;
        padding: 12px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        margin: 10px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(8px);
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
        border: 1.5px solid #475569 !important;
        border-radius: 4px !important;
        font-weight: 600 !important;
    }

    /* Lock sidebar expander to black background and white text */
    [data-testid="stSidebar"] [data-testid="stExpander"],
    [data-testid="stSidebar"] .streamlit-expander {
        background-color: #000000 !important;
        background: #000000 !important;
        border: 1px solid #333333 !important;
        border-radius: 8px !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] details,
    [data-testid="stSidebar"] details {
        background-color: #000000 !important;
        background: #000000 !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] summary,
    [data-testid="stSidebar"] .streamlit-expanderHeader,
    [data-testid="stSidebar"] summary {
        background-color: #000000 !important;
        background: #000000 !important;
        color: #ffffff !important;
        border-radius: 8px !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
        background-color: #1a1a1a !important;
        color: #00e5ff !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] summary p,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary span,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary svg,
    [data-testid="stSidebar"] [data-testid="stExpander"] p,
    [data-testid="stSidebar"] [data-testid="stExpander"] span {
        color: #ffffff !important;
        fill: #ffffff !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] div[data-testid="stExpanderDetails"] {
        background-color: #000000 !important;
        background: #000000 !important;
        border-top: 1px solid #222222 !important;
    }

    /* Square bordered box for sidebar modules */
    [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] > div {
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 4px !important; /* Clean square border */
        background-color: #050b14 !important;
        padding: 12px 10px !important;
        margin-bottom: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
<div class="sidebar-header">
    <h2>🏦 AARSHA NIDHI</h2>
    <p>Premium Banking Suite</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"""
<div class="user-info">
    👤 Active: <b style="color:white;">{st.session_state.get('username', 'Admin').upper()}</b>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)
current_time_ist = datetime.now(pytz.timezone('Asia/Kolkata'))
st.sidebar.markdown(f"""
<div class="ist-clock-card">
    <div style="color: #94a3b8; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.2px; display: flex; align-items: center; justify-content: center; gap: 4px; margin-bottom: 2px;">
        <span class="pulse-dot"></span> IST Live Clock
    </div>
    <div style="color: #00e5ff; font-size: 20px; font-weight: 800; font-family: 'Courier New', monospace; margin: 6px 0; text-shadow: 0 0 10px rgba(0, 229, 255, 0.4);">{current_time_ist.strftime('%I:%M:%S %p')}</div>
    <div style="color: #cbd5e1; font-size: 11px; font-weight: 500; opacity: 0.85;">{current_time_ist.strftime('%d %b %Y')}</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)

menu = st.sidebar.radio(
    "📋 MENU",
    [
        "📊 Dashboard",
        "👥 Customer Management",
        "🔍 KYC Verification",
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
    ],
    index=0,
    key="main_menu"
)

st.sidebar.markdown("<hr class='sidebar-divider'>", unsafe_allow_html=True)

def generate_sql_backup():
    """Generate a single SQL script containing all database tables and rows"""
    tables = [
        'customers', 'sb_accounts', 'fixed_deposits', 'recurring_deposits', 
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
        st.markdown("<div style='font-size: 11px; font-weight: 700; color: #00e5ff; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.8px;'>📦 SQL Backup Export</div>", unsafe_allow_html=True)
        if USING_SUPABASE:
            if st.button("🔄 Prepare SQL Backup", key="prep_sql_bkp", use_container_width=True):
                with st.spinner("Generating database backup..."):
                    try:
                        sql_backup_bytes = generate_sql_backup()
                        st.session_state.sql_backup_bytes = sql_backup_bytes
                        st.success("✅ Backup prepared!")
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
        st.markdown("<div style='font-size: 11px; font-weight: 700; color: #38bdf8; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.8px;'>📥 Database Import</div>", unsafe_allow_html=True)
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
                time.sleep(0.1)
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
                    from database import resequence_all_accounts, reconcile_books
                    try:
                        resequence_all_accounts()
                    except Exception as ex:
                        print(f"Resequence error: {str(ex)}")
                    try:
                        reconcile_books()
                    except Exception as ex:
                        print(f"Reconcile error: {str(ex)}")
                    
                    st.sidebar.success(f"✅ Successfully restored from {len(sql_files)} SQL files! Please refresh.")
                    time.sleep(0.1)
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
        border: 1.5px solid #475569 !important; /* Visible square border */
        border-radius: 4px !important; /* Clean square corners */
    }
    section[data-testid="stSidebar"] button:hover,
    div[data-testid="stSidebar"] button:hover,
    .stSidebar button:hover,
    [data-testid="stSidebar"] [data-testid^="stBaseButton"]:hover {
        background-color: #0f172a !important;
        color: #00e5ff !important;
        border: 1.5px solid #00e5ff !important;
    }
</style>
""", unsafe_allow_html=True)

if st.sidebar.button("🚪 Log Out", key="logout_btn", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

st.sidebar.markdown("<hr class='sidebar-divider'>", unsafe_allow_html=True)
st.sidebar.caption(f"🏢 AARSHA NIDHI LIMITED\nv1.0 | {datetime.now(IST).strftime('%Y')}")

# Header banner
st.markdown("""
<style>
    .company-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%) !important;
        padding: 20px 25px;
        border-radius: 12px;
        margin-bottom: 25px;
        color: white;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        border: 1px solid rgba(255,255,255,0.06);
        border-left: 5px solid #00e5ff !important; /* neon cyan left indicator */
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
    }
    .company-header .brand { display: flex; align-items: center; gap: 15px; }
    .company-header .brand h1 {
        font-size: 24px;
        margin: 0;
        font-weight: 800;
        letter-spacing: 0.8px;
        color: #ffffff;
        text-shadow: 0 0 10px rgba(0, 229, 255, 0.2);
    }
    .company-header .brand .sub {
        font-size: 11px;
        color: #94a3b8;
        margin-top: 4px;
        font-weight: 500;
    }
    .company-header .contact {
        text-align: right;
        font-size: 12px;
        color: #cbd5e1;
        opacity: 0.9;
        line-height: 1.6;
    }
    .company-header .contact .pulsing-online {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #10b981;
        background: rgba(16, 185, 129, 0.1);
        padding: 4px 10px;
        border-radius: 20px;
        margin-bottom: 6px;
    }
    .company-header .contact .pulsing-dot {
        width: 6px;
        height: 6px;
        background-color: #10b981;
        border-radius: 50%;
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
        animation: pulse-live 1.8s infinite;
    }
    
    /* Resequence button styling */
    .resequence-btn-container button {
        background-color: #000000 !important;
        color: #ffffff !important;
        border: 1px solid #000000 !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
    }
    .resequence-btn-container button:hover {
        background-color: #222222 !important;
        border-color: #222222 !important;
        color: #ffffff !important;
    }
</style>
<div class="company-header">
    <div class="brand">
        <div style="font-size: 32px;">🏦</div>
        <div>
            <h1>AARSHA NIDHI LIMITED</h1>
            <div class="sub">6/814, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501</div>
        </div>
    </div>
    <div class="contact">
        <div class="pulsing-online">
            <span class="pulsing-dot"></span> System Online
        </div>
        <div>CIN: U65990KL22021PLN069978</div>
        <div>📞 0471-2994535</div>
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
