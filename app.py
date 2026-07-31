
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import pytz
import io

# --- 1. CONFIGURATION & TIMEZONE (IST) ---
st.set_page_config(page_title="Banking & Financial Management Software", layout="wide")

IST = pytz.timezone('Asia/Kolkata')

def get_current_ist_time():
    return datetime.now(IST)

def get_current_ist_date():
    return get_current_ist_time().date()

# --- 2. DATABASE SETUP ---
def get_connection():
    conn = sqlite3.connect('banking_software.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Core Tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS customers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        name TEXT, email TEXT, phone TEXT, address TEXT, created_date TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (
                        account_number TEXT PRIMARY KEY, 
                        customer_id INTEGER, 
                        account_type TEXT, 
                        balance REAL, 
                        opening_date TEXT,
                        maturity_date TEXT,
                        interest_rate REAL)''')
                        
    cursor.execute('''CREATE TABLE IF NOT EXISTS chart_of_accounts (
                        account_code TEXT PRIMARY KEY, 
                        account_name TEXT, 
                        account_type TEXT)''')
                        
    cursor.execute('''CREATE TABLE IF NOT EXISTS operational_finances (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        type TEXT,
                        customer_id INTEGER,
                        account_code TEXT,
                        amount REAL,
                        mode TEXT,
                        date TEXT,
                        narration TEXT)''')
                        
    cursor.execute('''CREATE TABLE IF NOT EXISTS journal_vouchers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        voucher_date TEXT,
                        narration TEXT,
                        status TEXT)''')
                        
    cursor.execute('''CREATE TABLE IF NOT EXISTS jv_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        jv_id INTEGER,
                        account_code TEXT,
                        debit REAL,
                        credit REAL)''')
                        
    # Seed default Chart of Accounts if empty
    cursor.execute("SELECT COUNT(*) FROM chart_of_accounts")
    if cursor.fetchone()[0] == 0:
        default_coas = [
            ("1001", "Cash-in-Hand", "Asset"),
            ("1002", "Bank Current Account", "Asset"),
            ("2001", "Accounts Payable", "Liability"),
            ("3001", "Owner's Capital", "Equity"),
            ("4001", "Operating Income / Fees", "Income"),
            ("5001", "General Expenses", "Expense")
        ]
        cursor.executemany("INSERT INTO chart_of_accounts VALUES (?, ?, ?)", default_coas)
        conn.commit()
        
    conn.close()

init_db()

def run_query(query, params=(), fetch=True):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    if fetch:
        res = cursor.fetchall()
        conn.close()
        return res
    else:
        conn.commit()
        conn.close()

# --- 3. UNIVERSAL PDF GENERATOR ---
def create_pdf_report(title, df):
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#1f4e78'), spaceAfter=6)
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#555555'), spaceAfter=12)
    
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(f"Generated on (IST): {get_current_ist_time().strftime('%Y-%m-%d %H:%M:%S')}", sub_style))
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

# --- 4. SIDEBAR NAVIGATION & UI STYLING ---
st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        .stButton>button { border-radius: 6px; font-weight: 600; }
        .metric-card { background: #ffffff; padding: 16px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

st.sidebar.title("🏦 Bank Admin Suite")
st.sidebar.markdown(f"**IST Time:** `{get_current_ist_time().strftime('%d-%m-%Y %H:%M')}`")
st.sidebar.markdown("---")

menu = st.sidebar.radio("Navigation", [
    "Dashboard", 
    "Customer Management", 
    "Accounts (SB / FD / RD)", 
    "Income & Expenses", 
    "Journal Vouchers", 
    "Trial Balance", 
    "Chart of Accounts"
])

# --- 5. DASHBOARD MODULE ---
if menu == "Dashboard":
    st.title("📊 Executive Dashboard & SB Portfolio")
    st.markdown("Overview of customer assets, bank accounts breakdown, and operational standing.")
    
    # Fetch metrics
    cust_count = run_query("SELECT COUNT(*) FROM customers")[0][0]
    total_bal = run_query("SELECT SUM(balance) FROM accounts")[0][0] or 0.0
    
    # Account type breakdown for Circular / Donut representation
    acct_types = run_query("SELECT account_type, SUM(balance), COUNT(*) FROM accounts GROUP BY account_type")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Customers", f"{cust_count:,}")
    with col2:
        st.metric("Total Portfolio Balance", f"₹ {total_bal:,.2f}")
    with col3:
        st.metric("Current IST Date", get_current_ist_date().strftime("%d %b %Y"))
        
    st.markdown("---")
    
    col_chart, col_details = st.columns([1, 1])
    
    with col_chart:
        st.subheader("🍩 SB, FD & RD Portfolio Distribution")
        if acct_types:
            df_pie = pd.DataFrame(acct_types, columns=["Account Type", "Total Balance", "Count"])
            st.altair_chart(
                __import__('altair').Chart(df_pie).mark_arc(innerRadius=60).encode(
                    theta=__import__('altair').Theta(field="Total Balance", type="quantitative"),
                    color=__import__('altair').Color(field="Account Type", type="nominal"),
                    tooltip=["Account Type", "Total Balance", "Count"]
                ).properties(height=300),
                use_container_width=True
            )
        else:
            st.info("No account data available for distribution chart.")
            
    with col_details:
        st.subheader("💼 Savings & Deposit Portfolio Summary")
        if acct_types:
            df_portfolio = pd.DataFrame(acct_types, columns=["Account Type", "Total Balance (₹)", "Total Accounts"])
            st.dataframe(df_portfolio, use_container_width=True)
            st.download_button("📥 Download Portfolio PDF", create_pdf_report("SB-FD-RD Portfolio Breakdown", df_portfolio), "portfolio_report.pdf", "application/pdf")
        else:
            st.info("No accounts registered yet.")

# --- 6. CUSTOMER MANAGEMENT ---
elif menu == "Customer Management":
    st.title("👥 Customer Directory")
    tab1, tab2 = st.tabs(["Add Customer", "View & Export Directory"])
    
    with tab1:
        with st.form("cust_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email Address")
            phone = st.text_input("Phone Number")
            address = st.text_area("Residential Address")
            submitted = st.form_submit_button("Register Customer")
            if submitted:
                if name:
                    run_query("INSERT INTO customers (name, email, phone, address, created_date) VALUES (?, ?, ?, ?, ?)",
                              (name, email, phone, address, str(get_current_ist_date())), fetch=False)
                    st.success(f"Customer {name} registered successfully!")
                else:
                    st.error("Customer name is required.")
                    
    with tab2:
        customers = run_query("SELECT id, name, email, phone, address, created_date FROM customers")
        if customers:
            df_cust = pd.DataFrame(customers, columns=["ID", "Name", "Email", "Phone", "Address", "Registered Date"])
            st.dataframe(df_cust, use_container_width=True)
            st.download_button("Download Customer PDF", create_pdf_report("Customer Directory", df_cust), "customers.pdf", "application/pdf")
        else:
            st.info("No customers found.")

# --- 7. ACCOUNTS (SB / FD / RD) MODULE ---
elif menu == "Accounts (SB / FD / RD)":
    st.title("💳 Bank Accounts Management (SB / FD / RD)")
    tab1, tab2 = st.tabs(["Open New Account", "View & Export Accounts"])
    
    with tab1:
        with st.form("account_form"):
            customers = run_query("SELECT id, name FROM customers")
            if not customers:
                st.warning("Please register a customer first.")
            cust_dict = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers} if customers else {}
            
            selected_cust = st.selectbox("Select Customer", list(cust_dict.keys()) if cust_dict else ["No Customers"])
            account_number = st.text_input("Account Number (Unique)")
            account_type = st.selectbox("Account Type", ["SB (Savings Bank)", "FD (Fixed Deposit)", "RD (Recurring Deposit)"])
            
            col_a, col_b = st.columns(2)
            balance = col_a.number_input("Initial Amount / Deposit (₹)", min_value=0.0, value=1000.0)
            interest_rate = col_b.number_input("Interest Rate (%)", min_value=0.0, value=4.5)
            
            col_d1, col_d2 = st.columns(2)
            opening_date = col_d1.date_input("Opening Date", value=get_current_ist_date())
            maturity_date = col_d2.date_input("Maturity Date (For FD/RD)", value=get_current_ist_date())
            
            submitted = st.form_submit_button("Create Account")
            if submitted and customers:
                cid = cust_dict[selected_cust]
                try:
                    run_query("""
                        INSERT INTO accounts (account_number, customer_id, account_type, balance, opening_date, maturity_date, interest_rate)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (account_number, cid, account_type, balance, str(opening_date), str(maturity_date), interest_rate), fetch=False)
                    st.success(f"Account {account_number} ({account_type}) opened successfully!")
                except Exception as e:
                    st.error(f"Error creating account: {e}")
                    
    with tab2:
        st.subheader("All Active Bank Accounts")
        accounts = run_query("""
            SELECT a.account_number, c.name, a.account_type, a.balance, a.opening_date, a.maturity_date, a.interest_rate 
            FROM accounts a JOIN customers c ON a.customer_id = c.id
        """)
        if accounts:
            df_accts = pd.DataFrame(accounts, columns=["Account No", "Customer Name", "Type", "Balance (₹)", "Opening Date", "Maturity Date", "Interest Rate (%)"])
            st.dataframe(df_accts, use_container_width=True)
            st.download_button("📥 Download Accounts PDF", create_pdf_report("SB, FD & RD Account Portfolio", df_accts), "accounts_report.pdf", "application/pdf")
        else:
            st.info("No bank accounts registered.")

# --- 8. INCOME & EXPENSES ---
elif menu == "Income & Expenses":
    st.title("💰 Operational Income, Expenses, Assets & Liabilities")
    tab1, tab2, tab3, tab4 = st.tabs(["Record Entry", "Edit / Delete Entry", "View All Entries", "Cash Book Report & Print"])
    
    with tab1:
        st.subheader("Record New Financial Entry")
        with st.form("income_expense_form"):
            col1, col2 = st.columns(2)
            entry_type = col1.selectbox("Entry Classification", ["INCOME", "EXPENSE", "ASSET", "LIABILITY"])
            
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
                """, (entry_type, customer_id, account_code, amount, pay_mode, str(get_current_ist_date()), narration), fetch=False)
                
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", 
                               (str(get_current_ist_date()), f"{entry_type}: {narration}"))
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
                    e_type = st.selectbox("Update Classification", ["INCOME", "EXPENSE", "ASSET", "LIABILITY"], index=["INCOME", "EXPENSE", "ASSET", "LIABILITY"].index(curr_type) if curr_type in ["INCOME", "EXPENSE", "ASSET", "LIABILITY"] else 0)
                    
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

# --- 9. JOURNAL VOUCHERS ---
elif menu == "Journal Vouchers":
    st.title("📝 Journal Vouchers & General Ledger")
    vouchers = run_query("SELECT id, voucher_date, narration, status FROM journal_vouchers ORDER BY id DESC")
    if vouchers:
        df_jv = pd.DataFrame(vouchers, columns=["JV ID", "Voucher Date", "Narration", "Status"])
        st.dataframe(df_jv, use_container_width=True)
        st.download_button("Download Journal Vouchers PDF", create_pdf_report("Journal Vouchers Report", df_jv), "jv_report.pdf", "application/pdf")
    else:
        st.info("No journal vouchers posted.")

# --- 10. TRIAL BALANCE ---
elif menu == "Trial Balance":
    st.title("⚖️ Trial Balance Report")
    tb_data = run_query("""
        c.account_code, c.account_name, c.account_type,
        COALESCE(SUM(j.debit), 0.0) AS total_debit,
        COALESCE(SUM(j.credit), 0.0) AS total_credit
        FROM chart_of_accounts c
        LEFT JOIN jv_entries j ON c.account_code = j.account_code
        GROUP BY c.account_code, c.account_name, c.account_type
    """)
    if tb_data:
        df_tb = pd.DataFrame(tb_data, columns=["Account Code", "Account Name", "Account Type", "Total Debit (₹)", "Total Credit (₹)"])
        st.dataframe(df_tb, use_container_width=True)
        st.download_button("Download Trial Balance PDF", create_pdf_report("Trial Balance Statement", df_tb), "trial_balance.pdf", "application/pdf")
    else:
        st.info("No accounts or entries found for Trial Balance.")

# --- 11. CHART OF ACCOUNTS ---
elif menu == "Chart of Accounts":
    st.title("🗂️ Chart of Accounts")
    coas = run_query("SELECT account_code, account_name, account_type FROM chart_of_accounts")
    if coas:
        df_coas = pd.DataFrame(coas, columns=["Account Code", "Account Name", "Account Type"])
        st.dataframe(df_coas, use_container_width=True)
        st.download_button("Download COA PDF", create_pdf_report("Chart of Accounts Report", df_coas), "chart_of_accounts.pdf", "application/pdf")
    else:
        st.info("Chart of accounts is empty.")

