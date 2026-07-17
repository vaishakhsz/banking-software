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
            # Check if interest_calculations table exists and has data
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


