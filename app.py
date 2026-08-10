with st.expander("🛠️ Automatic Depreciation Calculator & Poster", expanded=True):
    st.info("""
    💡 **How Depreciation Works:**
    - Enter the **Book Value** of the asset (e.g., ₹50,000)
    - The system will automatically calculate: Book Value × Depreciation Rate%
    - Example: ₹50,000 × 18% = ₹9,000 depreciation expense
    - The asset value on the Balance Sheet will be reduced by this amount
    """)
    
    dep_coa_list = run_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Expense' AND account_name LIKE '%Depreciation%'")
    dep_dict = {f"{c[0]} - {c[1]}": c[0] for c in dep_coa_list} if dep_coa_list else {}
    
    asset_coa_list = run_query("SELECT account_code, account_name FROM chart_of_accounts WHERE account_type = 'Asset' AND (category = 'Non Current Assets' OR account_name LIKE '%Building%' OR account_name LIKE '%Fixed Asset%')")
    asset_dict = {f"{c[0]} - {c[1]}": c[0] for c in asset_coa_list} if asset_coa_list else {}
    
    if dep_dict and asset_dict:
        col_dep1, col_dep2, col_dep3 = st.columns(3)
        
        with col_dep1:
            selected_dep_acc = st.selectbox("Select Depreciation Expense Head", list(dep_dict.keys()), key="auto_dep_acc")
        with col_dep2:
            selected_asset_acc = st.selectbox("Select Asset Head (e.g., Building)", list(asset_dict.keys()), key="auto_dep_asset")
        with col_dep3:
            asset_val = st.number_input(
                "Asset Book Value (₹)", 
                min_value=0.0, 
                value=50000.0, 
                step=1000.0,
                key="auto_dep_value",
                help="Enter the total book value/cost of the asset"
            )
        
        # Extract percentage from account name
        dep_name = selected_dep_acc.split(" - ")[1]
        rate = 18.0
        if "15%" in dep_name:
            rate = 15.0
        elif "18%" in dep_name:
            rate = 18.0
        else:
            numbers = re.findall(r'\d+(?:\.\d+)?', dep_name)
            if numbers:
                rate = float(numbers[0])
        
        calculated_dep_amt = round(asset_val * (rate / 100), 2)
        
        st.success(f"📊 **Calculated Depreciation:** {rate}% of ₹{asset_val:,.2f} = **₹{calculated_dep_amt:,.2f}**")
        
        dep_narration = st.text_input("Depreciation Narration", value=f"Depreciation @ {rate}% on {selected_asset_acc.split(' - ')[1]}")
        dep_date = st.date_input("Depreciation Date", value=date.today(), key="auto_dep_date")
        
        if st.button("Post Calculated Depreciation JV", type="primary"):
            if calculated_dep_amt > 0:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO journal_vouchers (voucher_date, narration, status) VALUES (?, ?, 'POSTED')", (str(dep_date), dep_narration))
                jv_id = cursor.lastrowid
                # Debit Depreciation Expense
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, ?, 0)", (jv_id, dep_dict[selected_dep_acc], calculated_dep_amt))
                # Credit Asset Account (reducing asset value)
                cursor.execute("INSERT INTO jv_entries (jv_id, account_code, debit, credit) VALUES (?, ?, 0, ?)", (jv_id, asset_dict[selected_asset_acc], calculated_dep_amt))
                conn.commit()
                conn.close()
                st.success(f"✅ Successfully posted depreciation of ₹{calculated_dep_amt:,.2f} ({rate}%)!")
                st.balloons()
                st.rerun()
            else:
                st.error("Calculated depreciation amount must be greater than zero.")
    else:
        st.warning("Depreciation or Asset accounts not found in Chart of Accounts.")

