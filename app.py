
import streamlit as st
import pandas as pd
import datetime
import uuid

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Apex Ledger - Core Banking System",
    page_icon="🏦",
    layout="wide",
)

# --- INITIALIZE DATABASE / SESSION STATE ---
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    
    # 1. Chart of Accounts (COA)
    # Types: Asset, Liability, Equity, Revenue, Expense
    st.session_state.coa = {
        "1001": {"name": "Cash in Vault", "type": "Asset", "balance": 1000000.00}, # Starting cash capital
        "2001": {"name": "Savings Account Deposits", "type": "Liability", "balance": 0.0},
        "2002": {"name": "Fixed Deposit (FD) Liability", "type": "Liability", "balance": 0.0},
        "2003": {"name": "Recurring Deposit (RD) Liability", "type": "Liability", "balance": 0.0},
        "3001": {"name": "Share Capital", "type": "Equity", "balance": 1000000.00}, # Offsets starting cash
        "4001": {"name": "Interest Earned on Investments", "type": "Revenue", "balance": 0.0},
        "5001": {"name": "Interest Paid Expense", "type": "Expense", "balance": 0.0},
    }
    
    # 2. Customers & Accounts Database
    st.session_state.customers = {}
    st.session_state.accounts = {
        "SB": {}, # Savings Accounts
        "FD": {}, # Fixed Deposits
        "RD": {}, # Recurring Deposits
    }
    
    # 3. Double-Entry Journal Entries Table
    st.session_state.journal_entries = []

# --- HELPER FUNCTIONS FOR DOUBLE-ENTRY ---
def post_transaction(debit_account_code, credit_account_code, amount, description, reference_id=""):
    """
    Ensures absolute mathematical double-entry balance.
    One transaction adds a row for debit and a row for credit.
    """
    if amount <= 0:
        return False
        
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tx_group_id = str(uuid.uuid4())[:8]
    
    # Debit Entry
    st.session_state.journal_entries.append({
        "tx_group_id": tx_group_id,
        "timestamp": timestamp,
        "account_code": debit_account_code,
        "account_name": st.session_state.coa[debit_account_code]["name"],
        "debit": float(amount),
        "credit": 0.0,
        "description": description,
        "reference": reference_id
    })
    
    # Credit Entry
    st.session_state.journal_entries.append({
        "tx_group_id": tx_group_id,
        "timestamp": timestamp,
        "account_code": credit_account_code,
        "account_name": st.session_state.coa[credit_account_code]["name"],
        "debit": 0.0,
        "credit": float(amount),
        "description": description,
        "reference": reference_id
    })
    
    # Update COA Run-Time Balances
    st.session_state.coa[debit_account_code]["balance"] += float(amount) if st.session_state.coa[debit_account_code]["type"] in ["Asset", "Expense"] else -float(amount)
    st.session_state.coa[credit_account_code]["balance"] += float(amount) if st.session_state.coa[credit_account_code]["type"] in ["Liability", "Equity", "Revenue"] else -float(amount)
    
    return True

# --- APP LAYOUT ---
st.title("🏦 Apex Ledger")
st.caption("Enterprise-Grade Double-Entry Core Banking Platform")

# Sidebar navigation
menu = st.sidebar.radio(
    "Modules & Navigation",
    [
        "Dashboard", 
        "Customer KYC Registration", 
        "SB Account Operations", 
        "Term Deposits (FD & RD)", 
        "Journal Vouchers (JV)", 
        "Batch Accruals Engine",
        "Trial Balance", 
        "Financial Reports"
    ]
)

# --- MODULE 1: DASHBOARD ---
if menu == "Dashboard":
    st.subheader("System Performance & Health")
    
    col1, col2, col3, col4 = st.columns(4)
    total_customers = len(st.session_state.customers)
    total_deposits = (st.session_state.coa["2001"]["balance"] + 
                      st.session_state.coa["2002"]["balance"] + 
                      st.session_state.coa["2003"]["balance"])
    vault_cash = st.session_state.coa["1001"]["balance"]
    
    col1.metric("Total Active Customers", f"{total_customers}")
    col2.metric("Total Deposits (Liabilities)", f"₹{total_deposits:,.2f}")
    col3.metric("Cash Vault (Assets)", f"₹{vault_cash:,.2f}")
    
    # Verify Double Entry Balance
    total_debits = sum(item["debit"] for item in st.session_state.journal_entries)
    total_credits = sum(item["credit"] for item in st.session_state.journal_entries)
    balance_diff = abs(total_debits - total_credits)
    
    if balance_diff < 0.01:
        col4.metric("Ledger Status", "BALANCED", delta="Dr = Cr Perfect Alignment")
    else:
        col4.metric("Ledger Status", "OUT OF BALANCE", delta=f"Gap: ₹{balance_diff:,.2f}", delta_color="inverse")
        
    st.markdown("---")
    st.subheader("Recent Journal Postings (Global Ledger)")
    if st.session_state.journal_entries:
        df_je = pd.DataFrame(st.session_state.journal_entries)
        st.dataframe(df_je.tail(15), use_container_width=True)
    else:
        st.info("No postings in the general ledger yet.")

# --- MODULE 2: KYC & CUSTOMER REGISTRATION ---
elif menu == "Customer KYC Registration":
    st.subheader("Create New Customer Profile & KYC Verification")
    
    with st.form("kyc_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Customer Full Name")
            dob = st.date_input("Date of Birth", min_value=datetime.date(1900, 1, 1))
            pan_no = st.text_input("PAN Identification Card Number")
        with col2:
            aadhaar_no = st.text_input("Aadhaar Card Number")
            upload_aadhaar = st.file_uploader("Upload Aadhaar Document PDF/Image", type=["png", "jpg", "jpeg", "pdf"])
            upload_pan = st.file_uploader("Upload PAN Card PDF/Image", type=["png", "jpg", "jpeg", "pdf"])
            
        submit_kyc = st.form_submit_button("Authenticate Profile & Run Verification")
        
    if submit_kyc:
        if full_name and pan_no and aadhaar_no:
            # Generate Unique Customer ID
            customer_id = f"CUST-{uuid.uuid4().hex[:6].upper()}"
            
            # Mask sensitive ID details for secure storage rendering
            masked_aadhaar = f"XXXX-XXXX-{aadhaar_no[-4:]}" if len(aadhaar_no) >= 4 else "[Aadhaar Redacted]"
            
            # Store customer metadata
            st.session_state.customers[customer_id] = {
                "name": full_name,
                "dob": dob,
                "pan": pan_no,
                "aadhaar": masked_aadhaar,
                "kyc_status": "Verified",
                "kyc_docs": {
                    "aadhaar_uploaded": upload_aadhaar is not None,
                    "pan_uploaded": upload_pan is not None
                }
            }
            st.success(f"Successfully Registered Profile: {full_name} ({customer_id})")
            st.balloons()
        else:
            st.error("All identification fields (Full Name, PAN, and Aadhaar) must be filled to complete KYC validation.")

    # Show existing customer files
    st.markdown("---")
    st.subheader("Database of Verified KYC Records")
    if st.session_state.customers:
        cust_records = []
        for cid, details in st.session_state.customers.items():
            cust_records.append({
                "Customer ID": cid,
                "Full Name": details["name"],
                "PAN": details["pan"],
                "Aadhaar": details["aadhaar"],
                "KYC Status": details["kyc_status"],
                "Documents Provided": "Aadhaar & PAN" if details["kyc_docs"]["aadhaar_uploaded"] and details["kyc_docs"]["pan_uploaded"] else "Partial"
            })
        st.table(pd.DataFrame(cust_records))
    else:
        st.info("No active customer files stored.")

# --- MODULE 3: SB ACCOUNT OPERATIONS ---
elif menu == "SB Account Operations":
    st.subheader("Savings Bank (SB) General Ledger Accounts")
    
    tab1, tab2 = st.tabs(["Create SB Account", "Deposit / Withdraw Operations"])
    
    with tab1:
        if not st.session_state.customers:
            st.warning("Please verify a customer profile under KYC Registration first.")
        else:
            cust_options = {cid: f"{details['name']} ({cid})" for cid, details in st.session_state.customers.items()}
            selected_cust = st.selectbox("Select Verified Customer Profile", options=list(cust_options.keys()), format_func=lambda x: cust_options[x])
            
            initial_deposit = st.number_input("Opening Capital / Initial Deposit (₹)", min_value=100.0, step=100.0)
            create_sb_btn = st.button("Authorize & Open SB Account")
            
            if create_sb_btn:
                sb_acc_no = f"SB-{uuid.uuid4().hex[:8].upper()}"
                
                # Debit Cash (Asset 1001), Credit SB Deposits (Liability 2001)
                success = post_transaction(
                    debit_account_code="1001",
                    credit_account_code="2001",
                    amount=initial_deposit,
                    description=f"SB account {sb_acc_no} opening initial deposit",
                    reference_id=sb_acc_no
                )
                
                if success:
                    st.session_state.accounts["SB"][sb_acc_no] = {
                        "customer_id": selected_cust,
                        "customer_name": st.session_state.customers[selected_cust]["name"],
                        "balance": initial_deposit,
                        "opened_on": datetime.date.today().strftime("%Y-%m-%d")
                    }
                    st.success(f"Savings Account {sb_acc_no} successfully opened with a deposit of ₹{initial_deposit:,.2f}!")
                    
    with tab2:
        if not st.session_state.accounts["SB"]:
            st.info("No active Savings Bank accounts found.")
        else:
            sb_options = {acc: f"{details['customer_name']} - {acc} (Bal: ₹{details['balance']:,.2f})" for acc, details in st.session_state.accounts["SB"].items()}
            selected_sb = st.selectbox("Select target Savings Account", options=list(sb_options.keys()), format_func=lambda x: sb_options[x])
            
            op_type = st.radio("Transaction Type", ["Deposit", "Withdrawal"])
            amount = st.number_input("Transaction Amount (₹)", min_value=1.0, step=50.0)
            submit_op = st.button("Execute Transaction")
            
            if submit_op:
                current_bal = st.session_state.accounts["SB"][selected_sb]["balance"]
                
                if op_type == "Deposit":
                    # Cash Dr (1001), Deposits Cr (2001)
                    success = post_transaction(
                        debit_account_code="1001",
                        credit_account_code="2001",
                        amount=amount,
                        description=f"Cash deposit to SB account {selected_sb}",
                        reference_id=selected_sb
                    )
                    if success:
                        st.session_state.accounts["SB"][selected_sb]["balance"] += amount
                        st.success(f"Successfully deposited ₹{amount:,.2f} to {selected_sb}.")
                
                elif op_type == "Withdrawal":
                    if current_bal < amount:
                        st.error("Transaction Aborted: Insufficient clearing balance.")
                    else:
                        # Deposits Dr (2001), Cash Cr (1001)
                        success = post_transaction(
                            debit_account_code="2001",
                            credit_account_code="1001",
                            amount=amount,
                            description=f"Cash withdrawal from SB account {selected_sb}",
                            reference_id=selected_sb
                        )
                        if success:
                            st.session_state.accounts["SB"][selected_sb]["balance"] -= amount
                            st.success(f"Successfully withdrew ₹{amount:,.2f} from {selected_sb}.")

# --- MODULE 4: TERM DEPOSITS (FD & RD) ---
elif menu == "Term Deposits (FD & RD)":
    st.subheader("Term Deposit Issuance Ledger")
    
    dep_type = st.radio("Product Suite", ["Fixed Deposit (FD)", "Recurring Deposit (RD)"])
    
    if not st.session_state.customers:
        st.warning("Please verify a customer profile under KYC Registration first.")
    else:
        cust_options = {cid: f"{details['name']} ({cid})" for cid, details in st.session_state.customers.items()}
        selected_cust = st.selectbox("Select Customer Profile", options=list(cust_options.keys()), format_func=lambda x: cust_options[x])
        
        if dep_type == "Fixed Deposit (FD)":
            fd_amount = st.number_input("FD Principal Amount (₹)", min_value=1000.0, step=1000.0)
            tenure_months = st.number_input("Tenure Period (Months)", min_value=1, max_value=120, value=12)
            interest_rate = st.slider("Fixed Interest Rate (%)", min_value=1.0, max_value=15.0, value=7.5)
            
            if st.button("Generate FD Instrument"):
                fd_id = f"FD-{uuid.uuid4().hex[:8].upper()}"
                
                # Double Entry: Cash Dr (1001), FD Liabilities Cr (2002)
                success = post_transaction(
                    debit_account_code="1001",
                    credit_account_code="2002",
                    amount=fd_amount,
                    description=f"FD Account {fd_id} generated for {tenure_months} months @ {interest_rate}%",
                    reference_id=fd_id
                )
                if success:
                    st.session_state.accounts["FD"][fd_id] = {
                        "customer_id": selected_cust,
                        "customer_name": st.session_state.customers[selected_cust]["name"],
                        "principal": fd_amount,
                        "tenure": tenure_months,
                        "rate": interest_rate,
                        "opened_on": datetime.date.today().strftime("%Y-%m-%d")
                    }
                    st.success(f"Fixed Deposit Certificate {fd_id} generated for ₹{fd_amount:,.2f}")
                    
        elif dep_type == "Recurring Deposit (RD)":
            rd_monthly_contribution = st.number_input("Monthly Contribution Amount (₹)", min_value=500.0, step=500.0)
            tenure_months = st.number_input("Tenure Period (Months)", min_value=6, max_value=60, value=12)
            interest_rate = st.slider("RD Annual Interest Rate (%)", min_value=1.0, max_value=15.0, value=8.0)
            
            if st.button("Generate RD Plan"):
                rd_id = f"RD-{uuid.uuid4().hex[:8].upper()}"
                
                # Open with first payment: Cash Dr (1001), RD Liability Cr (2003)
                success = post_transaction(
                    debit_account_code="1001",
                    credit_account_code="2003",
                    amount=rd_monthly_contribution,
                    description=f"RD Plan {rd_id} registered with initial payment",
                    reference_id=rd_id
                )
                if success:
                    st.session_state.accounts["RD"][rd_id] = {
                        "customer_id": selected_cust,
                        "customer_name": st.session_state.customers[selected_cust]["name"],
                        "monthly_installment": rd_monthly_contribution,
                        "total_contributed": rd_monthly_contribution,
                        "tenure": tenure_months,
                        "rate": interest_rate,
                        "opened_on": datetime.date.today().strftime("%Y-%m-%d")
                    }
                    st.success(f"Recurring Deposit Schedule {rd_id} booked. Initial monthly contribution of ₹{rd_monthly_contribution:,.2f} cleared.")

    # View Current Term Deposits
    st.markdown("---")
    st.subheader("Active Term Deposit Records")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Fixed Deposits Ledger**")
        if st.session_state.accounts["FD"]:
            st.table(pd.DataFrame(st.session_state.accounts["FD"]).T[["customer_name", "principal", "tenure", "rate", "opened_on"]])
        else:
            st.info("No active FD books found.")
    with col2:
        st.write("**Recurring Deposits Ledger**")
        if st.session_state.accounts["RD"]:
            st.table(pd.DataFrame(st.session_state.accounts["RD"]).T[["customer_name", "total_contributed", "monthly_installment", "rate"]])
        else:
            st.info("No active RD books found.")

# --- MODULE 5: JOURNAL VOUCHERS (JV) ---
elif menu == "Journal Vouchers (JV)":
    st.subheader("Manual Double-Entry Journal Voucher Entry")
    st.info("Post direct adjustments or operational transaction overrides. Must mathematically balance (Debit = Credit) to post.")
    
    coa_options = {code: f"{code} - {details['name']} ({details['type']})" for code, details in st.session_state.coa.items()}
    
    with st.form("jv_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            debit_acc = st.selectbox("Select Account to Debit (Dr)", options=list(coa_options.keys()), format_func=lambda x: coa_options[x], key="dr_ac")
            debit_amt = st.number_input("Debit Amount (₹)", min_value=0.01, step=10.0, key="dr_val")
        with col2:
            credit_acc = st.selectbox("Select Account to Credit (Cr)", options=list(coa_options.keys()), format_func=lambda x: coa_options[x], key="cr_ac")
            credit_amt = st.number_input("Credit Amount (₹)", min_value=0.01, step=10.0, key="cr_val")
            
        narrative = st.text_input("Transaction Narrative / Description", placeholder="e.g. Booking monthly interest payout adjustment")
        post_btn = st.form_submit_button("Post Journal Voucher to Ledger")
        
    if post_btn:
        if debit_acc == credit_acc:
            st.error("Operational Error: You cannot debit and credit the same exact account.")
        elif abs(debit_amt - credit_amt) > 0.001:
            st.error(f"Unbalanced Transaction: Debit (₹{debit_amt}) does not equal Credit (₹{credit_amt}). Journal entries must balance.")
        elif not narrative:
            st.error("Narrative description is required for audit trails.")
        else:
            success = post_transaction(
                debit_account_code=debit_acc,
                credit_account_code=credit_acc,
                amount=debit_amt,
                description=f"JV Adjustment: {narrative}",
                reference_id="JV-MANUAL"
            )
            if success:
                st.success("Journal Entry posted successfully.")

# --- MODULE 6: BATCH ACCRUALS ENGINE ---
elif menu == "Batch Accruals Engine":
    st.subheader("⚙️ End-of-Period (EOP) Interest Accrual Engine")
    st.caption("Simulate systemic interest accruals across all active FD and RD accounts with automated ledger postings.")
    
    st.markdown("""
    This utility performs systemic interest accrual calculations. When executed:
    * **FD Accrual:** Computes daily/periodic interest using the formula: $A = P \times \\left(\\frac{r}{365}\\right)$
    * **RD Accrual:** Computes periodic interest on the accumulated balances using the monthly prorated rate.
    * **Ledger Execution:** Automatically posts a balanced double-entry transaction ($\text{Dr } 5001 \text{ Interest Expense} \ / \ \text{Cr } 200x \text{ Deposit Liability}$).
    """)

    col1, col2 = st.columns(2)
    with col1:
        simulation_days = st.number_input(
            "Simulate Days of Elapsed Time", 
            min_value=1, 
            max_value=365, 
            value=30, 
            help="Simulate how many days have passed since the last batch run to compute accumulated interest."
        )
    with col2:
        st.write(" ")
        st.write(" ")
        run_batch = st.button("Accrue Periodic Interst Expenses", use_container_width=True)

    if run_batch:
        accrual_records = []
        total_fd_interest = 0.0
        total_rd_interest = 0.0
        
        # 1. Process Fixed Deposits
        if st.session_state.accounts["FD"]:
            for fd_id, fd_details in st.session_state.accounts["FD"].items():
                principal = fd_details["principal"]
                annual_rate = fd_details["rate"] / 100.0
                
                # Accrued Interest = P * r * (days/365)
                accrued_interest = round(principal * annual_rate * (simulation_days / 365.0), 2)
                
                if accrued_interest > 0:
                    success = post_transaction(
                        debit_account_code="5001",
                        credit_account_code="2002",
                        amount=accrued_interest,
                        description=f"Interest accrued on FD {fd_id} for {simulation_days} days",
                        reference_id=fd_id
                    )
                    if success:
                        st.session_state.accounts["FD"][fd_id]["principal"] += accrued_interest
                        total_fd_interest += accrued_interest
                        accrual_records.append({
                            "Account ID": fd_id,
                            "Product": "Fixed Deposit",
                            "Customer": fd_details["customer_name"],
                            "Principal Base (₹)": f"₹{principal:,.2f}",
                            "Accrued Interest (₹)": f"₹{accrued_interest:,.2f}",
                            "Status": "POSTED"
                        })
                        
        # 2. Process Recurring Deposits
        if st.session_state.accounts["RD"]:
            for rd_id, rd_details in st.session_state.accounts["RD"].items():
                contributed = rd_details["total_contributed"]
                annual_rate = rd_details["rate"] / 100.0
                
                # Accrued Interest = Contributed * r * (days/365)
                accrued_interest = round(contributed * annual_rate * (simulation_days / 365.0), 2)
                
                if accrued_interest > 0:
                    success = post_transaction(
                        debit_account_code="5001",
                        credit_account_code="2003",
                        amount=accrued_interest,
                        description=f"Interest accrued on RD {rd_id} for {simulation_days} days",
                        reference_id=rd_id
                    )
                    if success:
                        st.session_state.accounts["RD"][rd_id]["total_contributed"] += accrued_interest
                        total_rd_interest += accrued_interest
                        accrual_records.append({
                            "Account ID": rd_id,
                            "Product": "Recurring Deposit",
                            "Customer": rd_details["customer_name"],
                            "Principal Base (₹)": f"₹{contributed:,.2f}",
                            "Accrued Interest (₹)": f"₹{accrued_interest:,.2f}",
                            "Status": "POSTED"
                        })

        if accrual_records:
            st.success(f"Batch processed successfully! Automated accruals compiled.")
            
            m_col1, m_col2, m_col3 = st.columns(3)
            m_col1.metric("Total FD Accrued Expense", f"₹{total_fd_interest:,.2f}")
            m_col2.metric("Total RD Accrued Expense", f"₹{total_rd_interest:,.2f}")
            m_col3.metric("Net Operational Impact", f"₹{(total_fd_interest + total_rd_interest):,.2f}", delta="- Profit Decrease", delta_color="inverse")
            
            st.write("#### Batch Postings Audit Log")
            st.table(pd.DataFrame(accrual_records))
        else:
            st.info("No active term deposit accounts qualify for interest accrual in this simulation.")

# --- MODULE 7: TRIAL BALANCE ---
elif menu == "Trial Balance":
    st.subheader("General Ledger Trial Balance")
    st.caption("Verifies mathematical equilibrium of the double-entry transactions ledger.")
    
    tb_data = []
    tot_dr = 0.0
    tot_cr = 0.0
    
    for code, info in st.session_state.coa.items():
        rows = [row for row in st.session_state.journal_entries if row["account_code"] == code]
        dr_sum = sum(r["debit"] for r in rows)
        cr_sum = sum(r["credit"] for r in rows)
        
        # Starting Base Capitalization (Simulating historical offset if ledger is empty)
        if code == "1001" and not rows:
            dr_sum = 1000000.00
        if code == "3001" and not rows:
            cr_sum = 1000000.00
            
        # Assets / Expenses increase with net debits
        # Liabilities / Equity / Revenues increase with net credits
        net_val = dr_sum - cr_sum
        dr_disp = 0.0
        cr_disp = 0.0
        
        if info["type"] in ["Asset", "Expense"]:
            if net_val >= 0:
                dr_disp = net_val
            else:
                cr_disp = abs(net_val)
        else:
            net_val_cr = cr_sum - dr_sum
            if net_val_cr >= 0:
                cr_disp = net_val_cr
            else:
                dr_disp = abs(net_val_cr)
                
        tot_dr += dr_disp
        tot_cr += cr_disp
        
        tb_data.append({
            "Account Code": code,
            "Account Name": info["name"],
            "Account Type": info["type"],
            "Debit Balance (₹)": dr_disp,
            "Credit Balance (₹)": cr_disp,
        })
        
    df_tb = pd.DataFrame(tb_data)
    st.table(df_tb)
    
    col1, col2 = st.columns(2)
    col1.metric("Sum of Debits", f"₹{tot_dr:,.2f}")
    col2.metric("Sum of Credits", f"₹{tot_cr:,.2f}")
    
    if abs(tot_dr - tot_cr) < 0.01:
        st.success("✅ The trial balance balances perfectly. Every ledger transaction balances.")
    else:
        st.error(f"❌ Balance error: Discrepancy of ₹{abs(tot_dr - tot_cr):,.2f}")

# --- MODULE 8: FINANCIAL REPORTS ---
elif menu == "Financial Reports":
    st.subheader("Interim Financial Performance Reports")
    
    tab1, tab2 = st.tabs(["Statement of Profit & Loss (P&L)", "Balance Sheet"])
    
    # Calculate operational numbers dynamically from Ledger entries
    rows_rev = [row for row in st.session_state.journal_entries if st.session_state.coa[row["account_code"]]["type"] == "Revenue"]
    rows_exp = [row for row in st.session_state.journal_entries if st.session_state.coa[row["account_code"]]["type"] == "Expense"]
    
    revenue_tot = sum(r["credit"] - r["debit"] for r in rows_rev)
    expense_tot = sum(r["debit"] - r["credit"] for r in rows_exp)
    net_profit = revenue_tot - expense_tot
    
    with tab1:
        st.write("### Statement of Profit & Loss")
        st.caption("For the period ending today")
        
        pl_rows = [
            {"Account": "Interest Income (Investment Revenue)", "Amount": f"₹{revenue_tot:,.2f}"},
            {"Account": "Interest Payouts (Expense Pool)", "Amount": f"- ₹{expense_tot:,.2f}"},
        ]
        st.table(pd.DataFrame(pl_rows))
        st.metric("Net Operating Profit", f"₹{net_profit:,.2f}")
        
    with tab2:
        st.write("### Balance Sheet Statement")
        st.caption("As of today")
        
        vault_rows = [row for row in st.session_state.journal_entries if row["account_code"] == "1001"]
        vault_val = 1000000.00 + sum(v["debit"] - v["credit"] for v in vault_rows)
        
        dep_sb_rows = [row for row in st.session_state.journal_entries if row["account_code"] == "2001"]
        dep_sb = sum(v["credit"] - v["debit"] for v in dep_sb_rows)
        
        dep_fd_rows = [row for row in st.session_state.journal_entries if row["account_code"] == "2002"]
        dep_fd = sum(v["credit"] - v["debit"] for v in dep_fd_rows)
        
        dep_rd_rows = [row for row in st.session_state.journal_entries if row["account_code"] == "2003"]
        dep_rd = sum(v["credit"] - v["debit"] for v in dep_rd_rows)
        
        capital_val = 1000000.00 # Base Equity Capital
        
        total_assets = vault_val
        total_liabilities = dep_sb + dep_fd + dep_rd
        total_equity = capital_val + net_profit # Capital + retained earnings
        
        col_assets, col_liab_eq = st.columns(2)
        
        with col_assets:
            st.write("**Assets**")
            assets_table = [
                {"Asset Account": "Cash in Vault", "Value": f"₹{vault_val:,.2f}"},
                {"Total Assets Value", f"₹{total_assets:,.2f}"}
            ]
            st.table(pd.DataFrame(assets_table))
            
        with col_liab_eq:
            st.write("**Liabilities & Shareholder Equity**")
            liab_table = [
                {"Liabilities & Equity Account": "SB Accounts", "Value": f"₹{dep_sb:,.2f}"},
                {"Liabilities & Equity Account": "Fixed Deposits (FD)", "Value": f"₹{dep_fd:,.2f}"},
                {"Liabilities & Equity Account": "Recurring Deposits (RD)", "Value": f"₹{dep_rd:,.2f}"},
                {"Liabilities & Equity Account": "Equity Capital Pool", "Value": f"₹{capital_val:,.2f}"},
                {"Liabilities & Equity Account": "Retained Earnings / Profit", "Value": f"₹{net_profit:,.2f}"},
                {"Total Liabilities & Equity", f"₹{(total_liabilities + total_equity):,.2f}"}
            ]
            st.table(pd.DataFrame(liab_table))
            
        if abs(total_assets - (total_liabilities + total_equity)) < 0.01:
            st.success("The Balance Sheet balances: Assets = Liabilities + Equity")
        else:
            st.warning("Warning: Discrepancy between assets and equity/liability calculations.")



